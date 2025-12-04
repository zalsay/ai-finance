import os
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取父目录
parent_dir = os.path.dirname(current_dir)
# 设定finance项目根目录
finance_dir = parent_dir
# 将finance目录添加到系统路径，以便导入模块
sys.path.append(finance_dir)
# 同时将当前目录添加到系统路径，确保本地模块可导入
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 修正导入路径，使用本目录下的timesfm_inference实现
from timesfm_init import init_timesfm
from predict_chunked_functions import predict_chunked_mode_for_best, predict_validation_chunks_only
from req_res_types import ChunkedPredictionRequest, ChunkedPredictionResponse, ChunkPredictionResult
from http_client import get_json, post_gzip_json
import os
import json
ak_tools_dir = os.path.join(finance_dir, 'akshare-tools')
if ak_tools_dir not in sys.path:
    sys.path.append(ak_tools_dir)
from postgres import PostgresHandler

@dataclass
class BacktestTrade:
    """
    回测交易记录类
    记录每一笔交易的详细信息
    """
    date: str          # 交易日期
    action: str        # 交易动作: 'buy' (买入) 或 'sell' (卖出)
    price: float       # 交易价格
    size: float        # 交易数量 (股数)
    chunk_index: int   # 对应的数据分块索引
    reason: str        # 交易原因 (触发交易的条件)
    fee: float = 0.0   # 本次交易手续费（金额）

def _select_closest_pct_quantile(chunk_result: ChunkPredictionResult) -> Optional[str]:
    """
    选择最接近实际走势的百分比分位数预测
    
    通过计算预测值与实际值的平均绝对误差(MAE)来评估哪个分位数的预测最准确。
    这里比较的是百分比变化，而不是绝对价格。
    
    Args:
        chunk_result: 单个分块的预测结果
        
    Returns:
        Optional[str]: 最佳分位数的键名 (例如 "tsf-0.5")，如果没有足够数据则返回 None
    """
    if not chunk_result.actual_values or not chunk_result.predictions:
        return None
    
    # 获取起始实际价格
    start_actual = chunk_result.actual_values[0]
    # 计算实际价格的百分比变化序列
    actual_pct = [((v / start_actual) - 1) * 100 if start_actual != 0 else 0 for v in chunk_result.actual_values]
    
    best_mae = float('inf')
    best_key = None
    
    # 遍历所有分位数 (0.1 到 0.9)
    for i in range(1, 10):
        key = f"tsf-0.{i}"
        if key in chunk_result.predictions:
            pred_values = chunk_result.predictions[key]
            # 确保预测值长度与实际值长度一致
            if len(pred_values) != len(actual_pct):
                continue
            
            # 计算预测值的百分比变化序列
            pred_pct = [((v / start_actual) - 1) * 100 if start_actual != 0 else 0 for v in pred_values]
            
            # 计算MAE (平均绝对误差)
            mae_val = np.mean(np.abs(np.array(pred_pct) - np.array(actual_pct)))
            
            # 更新最佳分位数
            if mae_val < best_mae:
                best_mae = mae_val
                best_key = key
                
    return best_key

def backtest_from_chunked_response(
    response: ChunkedPredictionResponse,
    buy_threshold_pct: float = 10.0,  # 买入阈值 (百分比)，默认 10.0%
    sell_threshold_pct: float = -3.0,  # 卖出阈值 (百分比)，默认 -3.0%
    initial_cash: float = 100000.0,  # 初始资金，默认 100000.0
    fixed_quantile_key: Optional[str] = None,  # 固定分位数键名，默认 None
    # 仓位控制参数
    enable_rebalance: bool = False,  # 是否启用仓位重新平衡，默认 False
    max_position_pct: float = 1.0,  # 最大持仓比例，默认 1.0 (100%)
    min_position_pct: float = 0.0,  # 最小持仓比例，默认 0.0 (0%)
    slope_position_per_pct: float = 0.0,  # 仓位调整比率 (每1%价格变化增加/减少的仓位比例)，默认 0.0
    rebalance_tolerance_pct: float = 0.05,  # 仓位重新平衡容忍度 (百分比)，默认 0.05%
    trade_fee_rate: float = 0.006,  # 交易手续费率 (每笔交易金额的比例)，默认 0.6%
    actual_total_return_pct: Optional[float] = None,  # 实际总体涨跌幅 (百分比)，默认 None
    # 累计收益止盈参数
    take_profit_threshold_pct: float = 10.0,  # 累计收益止盈阈值 (百分比)，默认 10.0%
    take_profit_sell_frac: float = 0.5,  # 止盈时卖出比例，默认 0.5 (50%)
) -> Dict[str, Any]:
    """
    基于分块预测结果进行回测
    
    策略逻辑:
    1. 遍历每个预测分块。
    2. 找出该分块中最准确的预测分位数。
    3. 如果预测的涨幅超过买入阈值 (buy_threshold_pct) 且当前空仓，则全仓买入。
    4. 如果预测的跌幅超过卖出阈值 (sell_threshold_pct) 且当前持仓，则清仓卖出。
    
    Args:
        response: 分块预测的响应对象
        buy_threshold_pct: 买入阈值 (百分比)，默认 10.0%
        sell_threshold_pct: 卖出阈值 (百分比)，默认 -3.0%
        initial_cash: 初始资金，默认 100000.0
        
    Returns:
        Dict[str, Any]: 回测结果，包括最终价值、收益率、交易记录等
    """
    cash = initial_cash
    shares = 0.0
    trades: List[BacktestTrade] = []
    last_price = None
    total_fees_paid = 0.0
    # 调试与统计信息
    predicted_changes: List[float] = []
    chosen_keys: List[str] = []
    per_chunk_signals: List[Dict[str, Any]] = []
    # 曲线数据（用于绘图）：每个分块结束时的实际价格与组合价值
    equity_curve_values: List[float] = []
    equity_curve_pct: List[float] = []
    equity_curve_pct_gross: List[float] = []
    curve_dates: List[str] = []
    actual_end_prices: List[float] = []
    # 计算实际总体涨跌幅（首末价），安全处理 concatenated_actual 可能为 None 的情况
    actual_total_return_pct_val = 0.0
    try:
        if isinstance(response.concatenated_actual, list) and len(response.concatenated_actual) >= 2:
            start_act = response.concatenated_actual[0]
            end_act = response.concatenated_actual[-1]
            if start_act is not None and end_act is not None and not np.isnan(start_act) and not np.isnan(end_act) and start_act != 0:
                actual_total_return_pct_val = (end_act / start_act - 1) * 100
        else:
            # 回退到通过分块的首末价来计算
            first_price = None
            last_price_tmp = None
            for cr0 in response.chunk_results:
                if cr0.actual_values and cr0.actual_values[0] is not None and not np.isnan(cr0.actual_values[0]):
                    first_price = float(cr0.actual_values[0])
                    break
            for cr1 in reversed(response.chunk_results):
                if cr1.actual_values and cr1.actual_values[-1] is not None and not np.isnan(cr1.actual_values[-1]):
                    last_price_tmp = float(cr1.actual_values[-1])
                    break
            if first_price is not None and last_price_tmp is not None and first_price != 0:
                actual_total_return_pct_val = ((last_price_tmp / first_price) - 1) * 100
    except Exception:
        actual_total_return_pct_val = 0.0
    for cr in response.chunk_results:
        if not cr.actual_values:
            continue
            
        start_price = cr.actual_values[0]
        if start_price is None or np.isnan(start_price):
            continue
            
        # 仅使用固定的最佳预测分位数（来自测试集评估/或环境变量），不再按分块自动选择
        best_key = fixed_quantile_key
        if (not best_key) or (best_key not in (cr.predictions or {})):
            # 若该分块不存在该分位数预测，则跳过
            continue

        pred_values = cr.predictions.get(best_key, [])
        if not pred_values:
            continue
            
        # 计算预测的百分比变化 (基于分块结束时的预测价格相对于分块开始时的实际价格)
        predicted_pct_change = ((pred_values[-1] / start_price) - 1) * 100 if start_price != 0 else 0
        predicted_changes.append(float(predicted_pct_change))
        chosen_keys.append(best_key)
        per_chunk_signals.append({
            "chunk_index": cr.chunk_index,
            "date": cr.chunk_start_date,
            "best_key": best_key,
            "predicted_pct_change": float(predicted_pct_change),
            "start_price": float(start_price),
        })
        
        # 计算当期仓位与目标仓位（用于仓位平衡控制）
        portfolio_value_start = cash + shares * start_price
        current_position_pct = (shares * start_price / portfolio_value_start) if portfolio_value_start > 0 else 0.0

        # 累计收益止盈：当累计收益超过阈值，卖出持仓的 n%
        try:
            tp_th = float(take_profit_threshold_pct)
            tp_frac = max(0.0, min(float(take_profit_sell_frac), 1.0))
        except Exception:
            tp_th = None
            tp_frac = 0.0
        if tp_th is not None and tp_frac > 0.0 and shares > 0 and start_price is not None and not np.isnan(start_price) and portfolio_value_start > 0:
            cum_ret_start_pct = (portfolio_value_start / initial_cash - 1.0) * 100.0
            if cum_ret_start_pct >= tp_th:
                sell_size_tp = shares * tp_frac
                if sell_size_tp > 0:
                    proceeds = sell_size_tp * start_price
                    fee_amt = proceeds * trade_fee_rate
                    shares -= sell_size_tp
                    cash += (proceeds - fee_amt)
                    total_fees_paid += fee_amt
                    trades.append(BacktestTrade(date=cr.chunk_start_date, action="sell", price=float(start_price), size=float(sell_size_tp), chunk_index=cr.chunk_index, reason=f"take_profit>= {tp_th:.2f}", fee=float(fee_amt)))

        if enable_rebalance:
            # 根据信号强度设定目标仓位
            if predicted_pct_change >= buy_threshold_pct:
                extra_strength = max(0.0, predicted_pct_change - buy_threshold_pct)
                target_position_pct = min(max_position_pct, min_position_pct + slope_position_per_pct * extra_strength)
            elif predicted_pct_change <= sell_threshold_pct:
                target_position_pct = 0.0
            else:
                # 无明显信号，保持现有仓位
                target_position_pct = current_position_pct

            # 若差异小于容差，不调整
            delta_pct = target_position_pct - current_position_pct
            if abs(delta_pct) > rebalance_tolerance_pct and portfolio_value_start > 0:
                target_shares = (target_position_pct * portfolio_value_start) / start_price
                if target_shares > shares:
                    # 需要买入以达目标仓位
                    buy_size = target_shares - shares
                    # 考虑手续费后的最大可买数量
                    max_affordable = cash / (start_price * (1.0 + trade_fee_rate)) if start_price > 0 else 0.0
                    buy_size = min(buy_size, max_affordable)
                    if buy_size > 0:
                        buy_cost = buy_size * start_price
                        fee_amt = buy_cost * trade_fee_rate
                        shares += buy_size
                        cash -= (buy_cost + fee_amt)
                        total_fees_paid += fee_amt
                        trades.append(BacktestTrade(date=cr.chunk_start_date, action="buy", price=float(start_price), size=float(buy_size), chunk_index=cr.chunk_index, reason=f"rebalance_up-> {target_position_pct:.2f}", fee=float(fee_amt)))
                else:
                    # 需要卖出以降目标仓位
                    sell_size = shares - target_shares
                    if sell_size > 0:
                        proceeds = sell_size * start_price
                        fee_amt = proceeds * trade_fee_rate
                        shares -= sell_size
                        cash += (proceeds - fee_amt)
                        total_fees_paid += fee_amt
                        trades.append(BacktestTrade(date=cr.chunk_start_date, action="sell", price=float(start_price), size=float(sell_size), chunk_index=cr.chunk_index, reason=f"rebalance_down-> {target_position_pct:.2f}", fee=float(fee_amt)))
        else:
            # 原有的全仓买入/清仓卖出逻辑
            if predicted_pct_change >= buy_threshold_pct:
                # 允许再次买入：用全部可用现金买入（考虑手续费）
                size = cash / (start_price * (1.0 + trade_fee_rate)) if start_price > 0 else 0.0
                if size > 0:
                    shares += size
                    buy_cost = size * start_price
                    fee_amt = buy_cost * trade_fee_rate
                    cash -= (buy_cost + fee_amt)
                    total_fees_paid += fee_amt
                    trades.append(BacktestTrade(date=cr.chunk_start_date, action="buy", price=float(start_price), size=float(size), chunk_index=cr.chunk_index, reason=f"pred_pct>={buy_threshold_pct}", fee=float(fee_amt)))
            elif predicted_pct_change <= sell_threshold_pct and shares > 0.0:
                proceeds = shares * start_price
                fee_amt = proceeds * trade_fee_rate
                cash += (proceeds - fee_amt)
                total_fees_paid += fee_amt
                trades.append(BacktestTrade(date=cr.chunk_start_date, action="sell", price=float(start_price), size=float(shares), chunk_index=cr.chunk_index, reason=f"pred_pct<={sell_threshold_pct}", fee=float(fee_amt)))
                shares = 0.0
            
        # 记录本分块结束时的价值与实际价格，用于绘图
        # 优先使用分块末尾的最后一个有效价格
        end_price = None
        if cr.actual_values:
            for _v in reversed(cr.actual_values):
                if _v is not None and not np.isnan(_v):
                    end_price = float(_v)
                    break
        if end_price is None:
            # 若末尾价格不可用，退回到分块起始价格（避免缺点）
            end_price = float(start_price) if (start_price is not None and not np.isnan(start_price)) else None

        if end_price is not None:
            pv_end = cash + shares * end_price
            equity_curve_values.append(float(pv_end))
            equity_curve_pct.append(float((pv_end / initial_cash - 1) * 100))
            # 毛收益率曲线：在相同交易数量下加回已累计手续费
            pv_end_gross = pv_end + total_fees_paid
            equity_curve_pct_gross.append(float((pv_end_gross / initial_cash - 1) * 100))
            actual_end_prices.append(float(end_price))
            curve_dates.append(cr.chunk_end_date)

        last_price = end_price if end_price is not None else last_price
        
    # 计算最终价值 (现金 + 持仓市值)
    final_value = cash + (shares * last_price if last_price is not None else 0.0)
    # 计算总收益率
    total_return = (final_value / initial_cash - 1) * 100
    
    # 计算回测时间跨度
    if response.concatenated_dates and len(response.concatenated_dates) > 1:
        start = pd.to_datetime(response.concatenated_dates[0])
        end = pd.to_datetime(response.concatenated_dates[-1])
    else:
        if response.chunk_results:
            start = pd.to_datetime(response.chunk_results[0].chunk_start_date)
            end = pd.to_datetime(response.chunk_results[-1].chunk_end_date)
        else:
            start = pd.to_datetime("1970-01-01")
            end = pd.to_datetime("1970-01-02")
            
    days = max((end - start).days, 1)
    # 计算年化收益率
    annualized = ((final_value / initial_cash) ** (365.0 / days) - 1) * 100

    # 为避免用户混淆，提供“费前”对比指标（不含手续费）。
    # 注：由于手续费会影响可买数量，此处的费前指标仅用于对比（在相同交易数量下加回手续费）。
    gross_final_value = final_value + total_fees_paid
    gross_total_return = (gross_final_value / initial_cash - 1) * 100
    gross_annualized = ((gross_final_value / initial_cash) ** (365.0 / days) - 1) * 100
    # 明确利润指标
    net_profit = final_value - initial_cash
    gross_profit = gross_final_value - initial_cash

    # 计算区间买入持有（首末价）基准收益，用于与策略对比
    bh_start_price = None
    bh_end_price = None
    try:
        if response.chunk_results:
            # 首个分块的第一个实际价格作为起点
            for cr0 in response.chunk_results:
                if cr0.actual_values and cr0.actual_values[0] is not None and not np.isnan(cr0.actual_values[0]):
                    bh_start_price = float(cr0.actual_values[0])
                    break
            # 最后一个分块的最后一个实际价格作为终点
            for cr1 in reversed(response.chunk_results):
                if cr1.actual_values and cr1.actual_values[-1] is not None and not np.isnan(cr1.actual_values[-1]):
                    bh_end_price = float(cr1.actual_values[-1])
                    break
    except Exception:
        bh_start_price = None
        bh_end_price = None

    benchmark_return = None
    benchmark_annualized = None
    if bh_start_price and bh_end_price and bh_start_price != 0:
        benchmark_return = ((bh_end_price / bh_start_price) - 1) * 100
        benchmark_annualized = ((bh_end_price / bh_start_price) ** (365.0 / days) - 1) * 100
    
    # 统计预测变化的分布以辅助阈值调参
    stats = {}
    if predicted_changes:
        arr = np.array(predicted_changes)
        stats = {
            "count_chunks": int(arr.size),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "p75": float(np.percentile(arr, 75)),
            "p90": float(np.percentile(arr, 90)),
            "above_buy_count": int(np.sum(arr >= buy_threshold_pct)),
            "below_sell_count": int(np.sum(arr <= sell_threshold_pct)),
        }

    result = {
        "initial_cash": initial_cash,
        "final_value": final_value,
        "total_return_pct": total_return,
        "annualized_return_pct": annualized,
        "final_value_gross": gross_final_value,
        "total_return_pct_gross": gross_total_return,
        "annualized_return_pct_gross": gross_annualized,
        "net_profit": net_profit,
        "gross_profit": gross_profit,
        "trades": [trade.__dict__ for trade in trades],
        "buy_threshold_pct": buy_threshold_pct,
        "sell_threshold_pct": sell_threshold_pct,
        "used_quantile": fixed_quantile_key if fixed_quantile_key else "auto",
        "predicted_change_stats": stats,
        "per_chunk_signals": per_chunk_signals[:50],  # 仅保留前50条，避免输出过大
        "benchmark_return_pct": benchmark_return if benchmark_return is not None else 0.0,
        "benchmark_annualized_return_pct": benchmark_annualized if benchmark_annualized is not None else 0.0,
        "period_days": days,
        "position_control": {
            "enable_rebalance": enable_rebalance,
            "max_position_pct": max_position_pct,
            "min_position_pct": min_position_pct,
            "slope_position_per_pct": slope_position_per_pct,
            "rebalance_tolerance_pct": rebalance_tolerance_pct,
            "take_profit_threshold_pct": take_profit_threshold_pct,
            "take_profit_sell_frac": take_profit_sell_frac,
        },
        "trade_fee_rate": trade_fee_rate,
        "total_fees_paid": float(total_fees_paid),
        "actual_total_return_pct": actual_total_return_pct_val,
        # 曲线数据（用于绘图）
        "equity_curve_values": equity_curve_values,
        "equity_curve_pct": equity_curve_pct,
        "equity_curve_pct_gross": equity_curve_pct_gross,
        "curve_dates": curve_dates,
        "actual_end_prices": actual_end_prices,
    }
    return result

def backtest_on_results(
    response: ChunkedPredictionResponse,
    chunk_results: List[ChunkPredictionResult],
    fixed_quantile_key: Optional[str],
    buy_threshold_pct: float,
    sell_threshold_pct: float,
    initial_cash: float,
    enable_rebalance: bool,
    max_position_pct: float,
    min_position_pct: float,
    slope_position_per_pct: float,
    rebalance_tolerance_pct: float,
    trade_fee_rate: float,
    take_profit_threshold_pct: float,
    take_profit_sell_frac: float,
) -> Dict[str, Any]:
    """
    将原本在 run_backtest 内部定义的 _backtest_on_results 提取为模块级函数。

    其职责是：基于给定的 chunk_results 构造一个临时的 ChunkedPredictionResponse，
    并调用 backtest_from_chunked_response 复用既有回测逻辑。

    Args:
        response: 完整的预测响应，用于提供元信息（stock_code、horizon_len、overall_metrics、processing_time 等）
        chunk_results: 用于回测的分块结果（可为验证集或测试集）
        fixed_quantile_key: 固定使用的分位数键名（如 "tsf-0.5"），None 则按逻辑自动选择
        buy_threshold_pct: 买入阈值（百分比）
        sell_threshold_pct: 卖出阈值（百分比）
        initial_cash: 初始资金
        enable_rebalance, max_position_pct, min_position_pct, slope_position_per_pct, rebalance_tolerance_pct: 仓位控制参数

    Returns:
        Dict[str, Any]: 回测结果字典
    """
    fake_response = ChunkedPredictionResponse(
        stock_code=response.stock_code,
        total_chunks=len(chunk_results),
        horizon_len=response.horizon_len,
        context_len=response.context_len,
        chunk_results=chunk_results,
        overall_metrics=response.overall_metrics,
        processing_time=response.processing_time,
        concatenated_predictions=None,
        concatenated_actual=None,
        concatenated_dates=None
    )
    return backtest_from_chunked_response(
        fake_response,
        buy_threshold_pct=buy_threshold_pct,
        sell_threshold_pct=sell_threshold_pct,
        initial_cash=initial_cash,
        fixed_quantile_key=fixed_quantile_key,
        enable_rebalance=enable_rebalance,
        max_position_pct=max_position_pct,
        min_position_pct=min_position_pct,
        slope_position_per_pct=slope_position_per_pct,
        rebalance_tolerance_pct=rebalance_tolerance_pct,
        trade_fee_rate=trade_fee_rate,
        take_profit_threshold_pct=take_profit_threshold_pct,
        take_profit_sell_frac=take_profit_sell_frac,
    )

def _load_cached_chunked_response(stock_code: str) -> Optional[ChunkedPredictionResponse]:
    """
    尝试从 forecast-results 目录加载之前保存的分块预测响应（JSON）。
    若存在并格式正确，则返回 ChunkedPredictionResponse；否则返回 None。

    期望JSON结构:
    {
        "stock_code": str,
        "total_chunks": int,
        "horizon_len": int,
        "chunk_results": [
            {
                "chunk_index": int,
                "chunk_start_date": str,
                "chunk_end_date": str,
                "predictions": {str: [float, ...]},
                "actual_values": [float, ...],
                "metrics": {str: float}
            }, ...
        ],
        "overall_metrics": { ... },
        "processing_time": float,
        "concatenated_predictions": {str: [float, ...]} | null,
        "concatenated_actual": [float, ...] | null,
        "concatenated_dates": [str, ...] | null,
        "validation_chunk_results": [ ... ] | null
    }
    """
    try:
        out_dir = os.path.join(finance_dir, "forecast-results")
        out_path = os.path.join(out_dir, f"{stock_code}_chunked_response.json")
        if not os.path.exists(out_path):
            return None
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 基本校验
        if not isinstance(data, dict) or data.get("stock_code") != stock_code:
            return None
        # 构造 ChunkPredictionResult 列表
        def _to_chunk_result(d: Dict[str, Any]) -> ChunkPredictionResult:
            return ChunkPredictionResult(
                chunk_index=int(d.get("chunk_index", 0)),
                chunk_start_date=str(d.get("chunk_start_date", "")),
                chunk_end_date=str(d.get("chunk_end_date", "")),
                predictions=d.get("predictions", {}) or {},
                actual_values=d.get("actual_values", []) or [],
                metrics=d.get("metrics", {}) or {},
            )

        chunk_results = []
        for cr in data.get("chunk_results", []) or []:
            try:
                chunk_results.append(_to_chunk_result(cr))
            except Exception:
                continue

        # 验证集分块（可选）
        val_results = None
        if isinstance(data.get("validation_chunk_results"), list):
            val_results = []
            for vcr in data.get("validation_chunk_results", []) or []:
                try:
                    val_results.append(_to_chunk_result(vcr))
                except Exception:
                    continue

        return ChunkedPredictionResponse(
            stock_code=data.get("stock_code", stock_code),
            total_chunks=int(data.get("total_chunks", len(chunk_results))),
            horizon_len=int(data.get("horizon_len", 0)),
            chunk_results=chunk_results,
            overall_metrics=data.get("overall_metrics", {}) or {},
            processing_time=float(data.get("processing_time", 0.0)),
            concatenated_predictions=data.get("concatenated_predictions"),
            concatenated_actual=data.get("concatenated_actual"),
            concatenated_dates=data.get("concatenated_dates"),
            validation_chunk_results=val_results,
        )
    except Exception as e:
        print(f"⚠️ 加载缓存的分块响应失败: {e}")
        return None

async def fetch_strategy_params(unique_key: str) -> Optional[Dict[str, Any]]:
    status_code, data, text = await get_json(
        "/api/v1/strategy/params/by-unique",
        params={"unique_key": unique_key},
        headers={"Accept-Encoding": "gzip, deflate", "X-Token": "fintrack-dev-token"},
    )
    if status_code == 200 and data:
        if isinstance(data, dict):
            return data.get("Data") or data.get("data") or data
    return None

async def run_backtest(
    request: ChunkedPredictionRequest,
    buy_threshold_pct: float = 3.0,
    sell_threshold_pct: float = -1.0,
    initial_cash: float = 100000.0,
    # 仓位控制参数
    enable_rebalance: bool = True,
    max_position_pct: float = 1.0,
    min_position_pct: float = 0.2,
    slope_position_per_pct: float = 0.1,
    rebalance_tolerance_pct: float = 0.05,
    trade_fee_rate: float = 0.006,
    # 累计收益止盈参数
    take_profit_threshold_pct: Optional[float] = None,
    take_profit_sell_frac: Optional[float] = None,
) -> Dict[str, Any]:
    """
    运行完整的回测流程
    
    1. 如可用，从 JSON 读取最佳分位数（避免重复评估）；
    2. 若存在最佳分位且缓存的分块响应可用，则跳过预测；
       若存在最佳分位但缓存不可用，则仅预测“验证集”分块；
       若不存在最佳分位，则初始化模型并执行“完整分块预测”（含测试集）以选取最佳分位；
    3. 基于预测结果运行回测策略（验证集优先，其次测试集）。
    
    说明：为保证回测所需的分块数据可用，只有在读取到最佳分位数且存在缓存的 chunked_response.json 时才会跳过预测；
    若设置环境变量 FORCE_REPREDICT=1，将强制重新预测以刷新缓存。
    
    Args:
        request: 分块预测请求对象
        buy_threshold_pct: 买入阈值
        sell_threshold_pct: 卖出阈值
        initial_cash: 初始资金
        
    Returns:
        Dict[str, Any]: 包含预测响应和回测结果的字典
    """    
    try:
        _uk = f"{request.stock_code}_best_hlen_{request.horizon_len}_clen_{request.context_len}_v_{request.timesfm_version}"
        _sp = await fetch_strategy_params(_uk)
        if _sp:
            _v = _sp.get("buy_threshold_pct")
            if _v is not None:
                buy_threshold_pct = float(_v)
            _v = _sp.get("sell_threshold_pct")
            if _v is not None:
                sell_threshold_pct = float(_v)
            _v = _sp.get("initial_cash")
            if _v is not None:
                initial_cash = float(_v)
            _v = _sp.get("enable_rebalance")
            if _v is not None:
                enable_rebalance = bool(_v)
            _v = _sp.get("max_position_pct")
            if _v is not None:
                max_position_pct = float(_v)
            _v = _sp.get("min_position_pct")
            if _v is not None:
                min_position_pct = float(_v)
            _v = _sp.get("slope_position_per_pct")
            if _v is not None:
                slope_position_per_pct = float(_v)
            _v = _sp.get("rebalance_tolerance_pct")
            if _v is not None:
                rebalance_tolerance_pct = float(_v)
            _v = _sp.get("trade_fee_rate")
            if _v is not None:
                trade_fee_rate = float(_v)
            _v = _sp.get("take_profit_threshold_pct")
            if _v is not None:
                try:
                    take_profit_threshold_pct = float(_v)
                except Exception:
                    pass
            _v = _sp.get("take_profit_sell_frac")
            if _v is not None:
                try:
                    take_profit_sell_frac = float(_v)
                except Exception:
                    pass
    except Exception:
        pass

    # 选择用于回测的固定分位数：优先读取 Go 后端，其次本地 JSON，然后环境变量，最后回退到响应中的测试集最佳分位
    fixed_quantile_key = None
    # 优先从Go后端查询是否已存在记录：/api/v1/predictions/timesfm-best/by-unique?unique_key=...
    try:
        unique_key = f"{request.stock_code}_best_hlen_{request.horizon_len}_clen_{request.context_len}_v_{request.timesfm_version}"
        status_code, data, text = await get_json(
            "/api/v1/save-predictions/mtf-best/by-unique",
            params={"unique_key": unique_key},
            headers = {
                "Accept-Encoding": "gzip, deflate",
                "X-Token": "fintrack-dev-token",
            }
        )
        if status_code == 200 and data:
            pred = (data or {}).get('prediction') or {}
            fixed_quantile_key = pred.get('best_prediction_item')
            if fixed_quantile_key:
                print(f"从Go后端读取到的固定分位数: {fixed_quantile_key}")
        else:
            print(f"ℹ️ 查询Go后端最佳分位失败，HTTP {status_code}: {str(text)[:200]}")
    except Exception as go_err:
        print(f"ℹ️ 查询Go后端最佳分位异常，回退到本地JSON: {go_err}")

    # 回退：本地JSON缓存
    if not fixed_quantile_key:
        try:
            out_dir = os.path.join(finance_dir, "forecast-results")
            out_path = os.path.join(out_dir, f"{request.stock_code}_best_hlen_{request.horizon_len}_clen_{request.context_len}_v_{request.timesfm_version}.json")
            if os.path.exists(out_path):
                with open(out_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    fixed_quantile_key = data.get("best_prediction_item")
                    print(f"从 JSON 文件读取到的固定分位数: {fixed_quantile_key}")
        except Exception as read_err:
            print(f"⚠️ 读取最佳分位 JSON 失败: {read_err}")
            fixed_quantile_key = None

    # 是否强制重新预测（忽略缓存）
    force_repredict = os.getenv("FORCE_REPREDICT", "0").strip().lower() in ("1", "true", "yes", "y")

    # 如果已存在固定分位数，尝试加载缓存的分块响应，避免重复预测
    response: Optional[ChunkedPredictionResponse] = None
    if fixed_quantile_key and not force_repredict:
        response = _load_cached_chunked_response(request.stock_code)
        if response is not None:
            print(f"✅ 已加载缓存分块响应，跳过预测: {request.stock_code}")
        else:
            print("ℹ️ 未找到缓存分块响应，将进行预测以生成回测所需数据。")

    # 若未能加载缓存响应：
    # - 如果已有固定分位数，则只预测验证集分块；
    # - 如果没有固定分位数，则进行完整分块预测以选取最佳分位。
    if response is None:
        if request.timesfm_version == "2.0":
            tfm = init_timesfm(horizon_len=request.horizon_len, context_len=request.context_len)
        else:
            tfm = None
        if fixed_quantile_key:
            print("➡️ 已有固定分位数但无缓存，开始仅预测验证集数据以供回测...")
            response = await predict_validation_chunks_only(
                request,
                tfm,
                timesfm_version=request.timesfm_version,
                fixed_best_prediction_item=fixed_quantile_key,
            )
        else:
            print("➡️ 未取得固定分位数，开始完整分块预测（含测试集）以选取最佳分位...")
            response = await predict_chunked_mode_for_best(
                request, tfm, timesfm_version=request.timesfm_version
            )

    # 若未从 JSON 获取固定分位数，则尝试从环境变量；再不行则回退到响应中的测试集最佳分位
    if not fixed_quantile_key:
        env_key = os.environ.get("FIXED_QUANTILE", "").strip()
        fixed_quantile_key = env_key if env_key else None
    if not fixed_quantile_key:
        try:
            if isinstance(response.overall_metrics, dict):
                fixed_quantile_key = response.overall_metrics.get('best_prediction_item')
                tr = response.overall_metrics.get('test_results')
                if isinstance(tr, dict):
                    fixed_quantile_key = tr.get('best_prediction_item') or fixed_quantile_key
        except Exception as e:
            print(f"⚠️ 从响应总体指标读取最佳分位失败: {e}")
            fixed_quantile_key = None

    # 执行回测：验证集优先，否则使用测试集
    if getattr(response, 'validation_chunk_results', None):
        result = backtest_on_results(
            response,
            response.validation_chunk_results,
            fixed_quantile_key,
            buy_threshold_pct,
            sell_threshold_pct,
            initial_cash,
            enable_rebalance,
            max_position_pct,
            min_position_pct,
            slope_position_per_pct,
            rebalance_tolerance_pct,
            trade_fee_rate,
            take_profit_threshold_pct if take_profit_threshold_pct is not None else float(os.getenv("TAKE_PROFIT_THRESHOLD_PCT", "10.0")),
            take_profit_sell_frac if take_profit_sell_frac is not None else float(os.getenv("TAKE_PROFIT_SELL_FRAC", "0.5")),
        )
    else:
        result = backtest_on_results(
            response,
            response.chunk_results,
            fixed_quantile_key,
            buy_threshold_pct,
            sell_threshold_pct,
            initial_cash,
            enable_rebalance,
            max_position_pct,
            min_position_pct,
            slope_position_per_pct,
            rebalance_tolerance_pct,
            trade_fee_rate,
            take_profit_threshold_pct if take_profit_threshold_pct is not None else float(os.getenv("TAKE_PROFIT_THRESHOLD_PCT", "10.0")),
            take_profit_sell_frac if take_profit_sell_frac is not None else float(os.getenv("TAKE_PROFIT_SELL_FRAC", "0.5")),
        )
    # 计算验证集首末价涨跌幅（用于对比收益）
    try:
        if getattr(response, 'validation_chunk_results', None):
            val_chunks = response.validation_chunk_results
            val_start_price = None
            val_end_price = None
            # 起点：验证集第一个有效价格
            for vcr0 in val_chunks:
                if vcr0.actual_values and vcr0.actual_values[0] is not None and not np.isnan(vcr0.actual_values[0]):
                    val_start_price = float(vcr0.actual_values[0])
                    break
            # 终点：验证集最后一个有效价格
            for vcr1 in reversed(val_chunks):
                if vcr1.actual_values and vcr1.actual_values[-1] is not None and not np.isnan(vcr1.actual_values[-1]):
                    val_end_price = float(vcr1.actual_values[-1])
                    break
            # 计算验证集时长（天数）
            if val_chunks:
                vs = pd.to_datetime(val_chunks[0].chunk_start_date)
                ve = pd.to_datetime(val_chunks[-1].chunk_end_date)
                val_days = max((ve - vs).days, 1)
                # 记录验证集起始与结束日期（原始字符串）
                result['validation_start_date'] = str(val_chunks[0].chunk_start_date)
                result['validation_end_date'] = str(val_chunks[-1].chunk_end_date)
            else:
                val_days = None

            if val_start_price and val_end_price and val_start_price != 0:
                val_return = ((val_end_price / val_start_price) - 1) * 100
                val_annualized = None
                if val_days:
                    val_annualized = ((val_end_price / val_start_price) ** (365.0 / val_days) - 1) * 100
                result['validation_benchmark_return_pct'] = float(val_return)
                if val_annualized is not None:
                    result['validation_benchmark_annualized_return_pct'] = float(val_annualized)
                result['validation_period_days'] = int(val_days) if val_days is not None else 0
    except Exception:
        
        pass

    try:
        await save_backtest_result_to_pg(request, response, result)
    except Exception:
        pass

    return {
        "response": response,
        "backtest": result
    }

async def save_backtest_result_to_pg(request, response, result):
    try:
        unique_key = f"{request.stock_code}_best_hlen_{request.horizon_len}_clen_{request.context_len}_v_{str(request.timesfm_version)}"

        signals_list = result.get("per_chunk_signals", []) or []
        signals_map = {}
        try:
            for i, item in enumerate(signals_list):
                key = str(item.get("chunk_index", i))
                signals_map[key] = item
        except Exception:
            signals_map = {}

        def _round4(x):
            try:
                return round(float(x), 4)
            except Exception:
                return x

        def _round_obj(o):
            if isinstance(o, float):
                return _round4(o)
            if isinstance(o, list):
                return [_round_obj(v) for v in o]
            if isinstance(o, dict):
                return {k: _round_obj(v) for k, v in o.items()}
            return o

        payload = {
            "unique_key": unique_key,
            "symbol": request.stock_code,
            "timesfm_version": str(request.timesfm_version),
            "context_len": int(request.context_len),
            "horizon_len": int(request.horizon_len),
            "user_id": int(request.user_id),

            "used_quantile": result.get("used_quantile"),
            "buy_threshold_pct": _round4(result.get("buy_threshold_pct", 0.0)),
            "sell_threshold_pct": _round4(result.get("sell_threshold_pct", 0.0)),
            "trade_fee_rate": _round4(result.get("trade_fee_rate", 0.0)),
            "total_fees_paid": _round4(result.get("total_fees_paid", 0.0)),
            "actual_total_return_pct": _round4(result.get("actual_total_return_pct", 0.0)),

            "benchmark_return_pct": _round4(result.get("benchmark_return_pct", 0.0)),
            "benchmark_annualized_return_pct": _round4(result.get("benchmark_annualized_return_pct", 0.0)),
            "period_days": int(result.get("period_days", 0)),

            "validation_start_date": result.get("validation_start_date"),
            "validation_end_date": result.get("validation_end_date"),
            "validation_benchmark_return_pct": _round4(result.get("validation_benchmark_return_pct")),
            "validation_benchmark_annualized_return_pct": _round4(result.get("validation_benchmark_annualized_return_pct")),
            "validation_period_days": int(result.get("validation_period_days", 0)),

            "position_control": _round_obj(result.get("position_control", {})),
            "predicted_change_stats": _round_obj(result.get("predicted_change_stats", {})),
            "per_chunk_signals": _round_obj(signals_map),

            "equity_curve_values": _round_obj(result.get("equity_curve_values", [])),
            "equity_curve_pct": _round_obj(result.get("equity_curve_pct", [])),
            "equity_curve_pct_gross": _round_obj(result.get("equity_curve_pct_gross", [])),
            "curve_dates": result.get("curve_dates", []),
            "actual_end_prices": _round_obj(result.get("actual_end_prices", [])),
            "trades": _round_obj(result.get("trades", [])),
        }

    base_url = os.environ.get('POSTGRES_API', 'http://go-api.meetlife.com.cn:58005')
        async with PostgresHandler(base_url=base_url, api_token="fintrack-dev-token") as pg:
            status_code, data, body_text = await pg.save_backtest_result(payload)
        if status_code == 200:
            print(f"✅ 回测结果已保存: unique_key={unique_key}")
        else:
            print(f"⚠️ 回测结果保存失败: status={status_code}, body={str(body_text)[:200]}")
    except Exception as e:
        try:
            print(f"⚠️ 保存回测结果到PG异常: {e}")
        except Exception:
            pass

if __name__ == "__main__":
    # 测试代码
    test_request = ChunkedPredictionRequest(
        user_id=1,
        stock_code="sh510050",
        years=10,
        horizon_len=7,
        start_date="20100101",
        end_date="20251114",
        context_len=2048,
        time_step=0,
        stock_type=2,
        timesfm_version="2.5",
    )
    
    print(f"\n=== 开始回测 ===")
    print(f"股票代码: {test_request.stock_code}")
    print(f"回测区间: {test_request.start_date} 到 {test_request.end_date}")
    

    # 从环境变量读取阈值与仓位控制参数
    buy_threshold = float(os.getenv("BUY_THRESHOLD_PCT", "0.0"))
    sell_threshold = float(os.getenv("SELL_THRESHOLD_PCT", "-5.0"))
    initial_cash = float(os.getenv("INITIAL_CASH", "100000.0"))
    enable_rebalance = os.getenv("ENABLE_REBALANCE", "1").strip().lower() in ("1", "true", "yes", "y")
    max_position_pct = float(os.getenv("MAX_POSITION_PCT", "1.0"))
    min_position_pct = float(os.getenv("MIN_POSITION_PCT", "0.2"))
    slope_position_per_pct = float(os.getenv("SLOPE_POSITION_PER_PCT", "0.1"))
    rebalance_tolerance_pct = float(os.getenv("REBALANCE_TOLERANCE_PCT", "0.05"))
    trade_fee_rate = float(os.getenv("TRADE_FEE_RATE", "0.006"))
    # 止盈参数
    take_profit_threshold_env = float(os.getenv("TAKE_PROFIT_THRESHOLD_PCT", "10.0"))
    take_profit_sell_frac_env = float(os.getenv("TAKE_PROFIT_SELL_FRAC", "0.8"))

    print(f"使用买入阈值: {buy_threshold:.2f}% , 卖出阈值: {sell_threshold:.2f}% , 初始资金: {initial_cash:.2f}")
    print(f"仓位控制: enable_rebalance={enable_rebalance}, max={max_position_pct:.2f}, min={min_position_pct:.2f}, slope_per_pct={slope_position_per_pct:.2f}, tol={rebalance_tolerance_pct:.2f}")
    print(f"止盈: take_profit_threshold_pct={take_profit_threshold_env:.2f}% , take_profit_sell_frac={take_profit_sell_frac_env:.2f}")
    
    enable_rebalance = False
    # 运行回测
    import asyncio
    result = asyncio.run(run_backtest(
        test_request,
        buy_threshold_pct=buy_threshold,
        sell_threshold_pct=sell_threshold,
        initial_cash=initial_cash,
        enable_rebalance=enable_rebalance,
        max_position_pct=max_position_pct,
        min_position_pct=min_position_pct,
        slope_position_per_pct=slope_position_per_pct,
        rebalance_tolerance_pct=rebalance_tolerance_pct,
        trade_fee_rate=trade_fee_rate,
        take_profit_threshold_pct=take_profit_threshold_env,
        take_profit_sell_frac=take_profit_sell_frac_env,
    ))
    
    response = result["response"]
    backtest = result["backtest"]
    
    print(f"\n=== 预测结果摘要 ===")
    print(f"总分块数: {response.total_chunks}")
    print(f"处理时间: {response.processing_time:.2f} 秒")
    
    print(f"\n=== 回测结果摘要（验证集）===" if getattr(response, 'validation_chunk_results', None) else "\n=== 回测结果摘要（测试集）===")
    print(f"初始资金: {backtest['initial_cash']:.2f}")
    print(f"最终价值（净，含手续费）: {backtest['final_value']:.2f}")
    print(f"总收益率（净，含手续费）: {backtest['total_return_pct']:.2f}%")
    print(f"年化收益率（净，含手续费）: {backtest['annualized_return_pct']:.2f}%")
    # 费前对比指标（不含手续费）
    print(f"最终价值（毛，不含手续费，仅用于对比）: {backtest.get('final_value_gross', backtest['final_value']):.2f}")
    print(f"总收益率（毛，不含手续费）: {backtest.get('total_return_pct_gross', backtest['total_return_pct']):.2f}%")
    print(f"年化收益率（毛，不含手续费）: {backtest.get('annualized_return_pct_gross', backtest['annualized_return_pct']):.2f}%")
    # 明确利润指标
    print(f"净利润（含手续费）: {backtest.get('net_profit', backtest['final_value'] - backtest['initial_cash']):.2f}")
    print(f"毛利润（不含手续费）: {backtest.get('gross_profit', backtest.get('final_value_gross', backtest['final_value']) - backtest['initial_cash']):.2f}")
    print(f"交易次数: {len(backtest['trades'])}")
    print(f"实际总体涨跌幅: {backtest.get('actual_total_return_pct', 0.0):.2f}%")
    print(f"手续费率: {backtest.get('trade_fee_rate', 0.0) * 100:.2f}%")
    print(f"累计手续费支出: {backtest.get('total_fees_paid', 0.0):.2f}")
    # 验证集首末价涨跌幅（若有验证集）
    if backtest.get('validation_benchmark_return_pct') is not None:
        print(f"验证集基准（首末价）总收益率: {backtest.get('validation_benchmark_return_pct', 0.0):.2f}%")
        if backtest.get('validation_benchmark_annualized_return_pct') is not None:
            print(f"验证集基准（首末价）年化收益率: {backtest.get('validation_benchmark_annualized_return_pct', 0.0):.2f}%")
        # 额外打印验证集起始与结束日期（若有）
        vs = backtest.get('validation_start_date')
        ve = backtest.get('validation_end_date')
        if vs and ve:
            print(f"验证集区间: {vs} 到 {ve}（共 {backtest.get('validation_period_days', 0)} 天）")
    else:
        print(f"基准（首末价）总收益率: {backtest.get('benchmark_return_pct', 0.0):.2f}%")
        print(f"基准（首末价）年化收益率: {backtest.get('benchmark_annualized_return_pct', 0.0):.2f}%")

    print(f"使用分位数: {backtest.get('used_quantile', 'auto')}")
    print(f"买入阈值: {backtest['buy_threshold_pct']:.2f}% , 卖出阈值: {backtest['sell_threshold_pct']:.2f}%")
    pc = backtest.get('position_control', {})
    print(f"仓位控制: enable_rebalance={pc.get('enable_rebalance', False)}, max={pc.get('max_position_pct', 0.0):.2f}, min={pc.get('min_position_pct', 0.0):.2f}, slope_per_pct={pc.get('slope_position_per_pct', 0.0):.2f}, tol={pc.get('rebalance_tolerance_pct', 0.0):.2f}")

    # 预测变化分布统计，辅助阈值调参
    stats = backtest.get('predicted_change_stats', {})
    print("\n=== 预测变化分布统计 ===")
    if stats:
        print(f"分块数: {stats.get('count_chunks', 0)}")
        print(f"均值/中位数/75分位/90分位: {stats.get('mean', 0.0):.2f}% / {stats.get('median', 0.0):.2f}% / {stats.get('p75', 0.0):.2f}% / {stats.get('p90', 0.0):.2f}%")
        print(f"高于买入阈值的分块数: {stats.get('above_buy_count', 0)} , 低于卖出阈值的分块数: {stats.get('below_sell_count', 0)}")
    else:
        print("暂无统计数据")
    
    print(f"\n=== 交易明细 ===")
    for trade in backtest['trades']:
        print(f"日期: {trade['date']}, 动作: {trade['action']}, 价格: {trade['price']:.2f}, 数量: {trade['size']:.0f}, 原因: {trade['reason']}")

    # 绘制验证集实际值与回测累计收益于一张图
    try:
        curve_dates = backtest.get('curve_dates', [])
        prices = backtest.get('actual_end_prices', [])
        equity_pct = backtest.get('equity_curve_pct', [])
        if curve_dates and prices and equity_pct and len(curve_dates) == len(prices) == len(equity_pct):
            x = pd.to_datetime(curve_dates)
            fig, ax1 = plt.subplots(figsize=(12, 6))
            dataset_label = 'Validation' if backtest.get('validation_start_date') and backtest.get('validation_end_date') else 'Test'
            ln1 = ax1.plot(x, prices, color='tab:blue', label=f'{dataset_label} actual price (chunk end)', linewidth=2)
            ax1.set_xlabel('Date')
            ax1.set_ylabel('Price', color='tab:blue')
            ax1.tick_params(axis='y', labelcolor='tab:blue')
            ax1.grid(True, alpha=0.3)
            try:
                ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
            except Exception:
                pass

            ax2 = ax1.twinx()
            ln2 = ax2.plot(x, equity_pct, color='tab:red', label='Backtest cumulative return (net, with fees) (%)', linewidth=2, linestyle='--')
            # 增加毛收益率（不含手续费）曲线
            equity_pct_gross = backtest.get('equity_curve_pct_gross', [])
            if equity_pct_gross and len(equity_pct_gross) == len(x):
                ln2_gross = ax2.plot(x, equity_pct_gross, color='tab:orange', label='Backtest cumulative return (gross, no fees) (%)', linewidth=2)
            else:
                ln2_gross = []
            # 计算并绘制验证集基准（首末价）累计收益率曲线（与回测累计收益同轴对比）
            # try:
            #     # 选择第一个有效且非零的价格作为基准
            #     baseline = None
            #     for p in prices:
            #         if p is not None and not np.isnan(p) and p != 0:
            #             baseline = p
            #             break
            #     benchmark_pct_curve = []
            #     if baseline is not None and baseline != 0:
            #         for p in prices:
            #             if p is not None and not np.isnan(p):
            #                 benchmark_pct_curve.append(((p / baseline) - 1) * 100)
            #             else:
            #                 benchmark_pct_curve.append(np.nan)
            #     else:
            #         benchmark_pct_curve = [np.nan] * len(prices)
            #     ln3 = ax2.plot(x, benchmark_pct_curve, color='tab:green', label=f'{dataset_label} benchmark cumulative return (%)', linewidth=1.8)
            # except Exception:
            #     ln3 = []
            ax2.set_ylabel('Cumulative return (%)', color='tab:red')
            ax2.tick_params(axis='y', labelcolor='tab:red')

            # 可选：绘制完整实际价格序列（如果响应中提供了拼接的日期与实际值）
            extra_lines = []
            # try:
            #     full_dates = getattr(response, 'concatenated_dates', None)
            #     full_actual = getattr(response, 'concatenated_actual', None)
            #     vs = backtest.get('validation_start_date')
            #     ve = backtest.get('validation_end_date')
            #     if full_dates and full_actual and len(full_dates) == len(full_actual) and vs and ve:
            #         xd = pd.to_datetime(full_dates)
            #         vs_dt = pd.to_datetime(vs)
            #         ve_dt = pd.to_datetime(ve)
            #         mask = (xd >= vs_dt) & (xd <= ve_dt)
            #         xd_v = xd[mask]
            #         full_actual_v = np.array(full_actual)[mask]
            #         ln4 = ax1.plot(xd_v, full_actual_v, color='dimgray', alpha=0.6, linewidth=1.4, label='Validation actual price (full series)')
            #         extra_lines = ln4
            # except Exception:
            #     extra_lines = []

            lines = ln1 + ln2 + ln2_gross
            labels = [l.get_label() for l in lines]
            ax1.legend(lines, labels, loc='upper left')
            plt.title(f"{test_request.stock_code} {dataset_label} actual price vs backtest cumulative return (net vs gross)")
            plt.tight_layout()
            mode_suffix = "backtest_val" if getattr(response, 'validation_chunk_results', None) else "backtest_test"
            plot_filename = os.path.join(finance_dir, f"forecast-results/{test_request.stock_code}_{mode_suffix}_equity_vs_actual.png")
            plt.savefig(plot_filename, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            print(f"\n✅ 已保存混合图: {plot_filename}")
        else:
            print("\n⚠️ 无法绘制混合图：曲线数据为空或长度不一致")
    except Exception as e:
        print(f"\n⚠️ 绘图失败: {e}")

    # 保存结果到文件
    mode_suffix = "backtest_val" if getattr(response, 'validation_chunk_results', None) else "backtest_test"
    results_filename = os.path.join(finance_dir, f"forecast-results/{test_request.stock_code}_{mode_suffix}_results.txt")
    
    with open(results_filename, 'w', encoding='utf-8') as f:
        f.write(f"回测结果 - 股票: {test_request.stock_code}\n")
        f.write(f"回测区间: {test_request.start_date} 到 {test_request.end_date}\n\n")
        
        f.write("=== 预测结果摘要 ===\n")
        f.write(f"总分块数: {response.total_chunks}\n")
        f.write(f"处理时间: {response.processing_time:.2f} 秒\n\n")
        
        f.write("=== 回测结果摘要（验证集）===\n" if getattr(response, 'validation_chunk_results', None) else "=== 回测结果摘要（测试集）===\n")
        f.write(f"初始资金: {backtest['initial_cash']:.2f}\n")
        f.write(f"最终价值（净，含手续费）: {backtest['final_value']:.2f}\n")
        f.write(f"总收益率（净，含手续费）: {backtest['total_return_pct']:.2f}%\n")
        f.write(f"年化收益率（净，含手续费）: {backtest['annualized_return_pct']:.2f}%\n")
        # 费前对比指标（不含手续费）
        f.write(f"最终价值（毛，不含手续费，仅用于对比）: {backtest.get('final_value_gross', backtest['final_value']):.2f}\n")
        f.write(f"总收益率（毛，不含手续费）: {backtest.get('total_return_pct_gross', backtest['total_return_pct']):.2f}%\n")
        f.write(f"年化收益率（毛，不含手续费）: {backtest.get('annualized_return_pct_gross', backtest['annualized_return_pct']):.2f}%\n")
        # 明确利润指标
        f.write(f"净利润（含手续费）: {backtest.get('net_profit', backtest['final_value'] - backtest['initial_cash']):.2f}\n")
        f.write(f"毛利润（不含手续费）: {backtest.get('gross_profit', backtest.get('final_value_gross', backtest['final_value']) - backtest['initial_cash']):.2f}\n")
        f.write(f"交易次数: {len(backtest['trades'])}\n")
        f.write(f"基准（首末价）总收益率: {backtest.get('benchmark_return_pct', 0.0):.2f}%\n")
        f.write(f"基准（首末价）年化收益率: {backtest.get('benchmark_annualized_return_pct', 0.0):.2f}%\n")
        f.write(f"手续费率: {backtest.get('trade_fee_rate', 0.0) * 100:.2f}%\n")
        f.write(f"累计手续费支出: {backtest.get('total_fees_paid', 0.0):.2f}\n")
        if backtest.get('validation_benchmark_return_pct') is not None:
            f.write(f"验证集基准（首末价）总收益率: {backtest.get('validation_benchmark_return_pct', 0.0):.2f}%\n")
            if backtest.get('validation_benchmark_annualized_return_pct') is not None:
                f.write(f"验证集基准（首末价）年化收益率: {backtest.get('validation_benchmark_annualized_return_pct', 0.0):.2f}%\n")
        f.write(f"使用分位数: {backtest.get('used_quantile', 'auto')}\n")
        f.write(f"买入阈值: {backtest['buy_threshold_pct']:.2f}% , 卖出阈值: {backtest['sell_threshold_pct']:.2f}%\n")
        pc = backtest.get('position_control', {})
        f.write("=== 仓位控制设置 ===\n")
        f.write(f"enable_rebalance: {pc.get('enable_rebalance', False)}\n")
        f.write(f"max_position_pct: {pc.get('max_position_pct', 0.0):.2f}\n")
        f.write(f"min_position_pct: {pc.get('min_position_pct', 0.0):.2f}\n")
        f.write(f"slope_position_per_pct: {pc.get('slope_position_per_pct', 0.0):.2f}\n")
        f.write(f"rebalance_tolerance_pct: {pc.get('rebalance_tolerance_pct', 0.0):.2f}\n")
        # 止盈参数
        f.write(f"take_profit_threshold_pct: {pc.get('take_profit_threshold_pct', 0.0):.2f}%\n")
        f.write(f"take_profit_sell_frac: {pc.get('take_profit_sell_frac', 0.0):.2f}\n\n")

        # 预测变化分布统计
        stats = backtest.get('predicted_change_stats', {})
        f.write("=== 预测变化分布统计 ===\n")
        if stats:
            f.write(f"分块数: {stats.get('count_chunks', 0)}\n")
            f.write(f"均值: {stats.get('mean', 0.0):.2f}%\n")
            f.write(f"中位数: {stats.get('median', 0.0):.2f}%\n")
            f.write(f"75分位数: {stats.get('p75', 0.0):.2f}%\n")
            f.write(f"90分位数: {stats.get('p90', 0.0):.2f}%\n")
            f.write(f"高于买入阈值的分块数: {stats.get('above_buy_count', 0)}\n")
            f.write(f"低于卖出阈值的分块数: {stats.get('below_sell_count', 0)}\n\n")
        else:
            f.write("暂无统计数据\n\n")

        # 图表信息
        curve_dates = backtest.get('curve_dates', [])
        prices = backtest.get('actual_end_prices', [])
        equity_pct = backtest.get('equity_curve_pct', [])
        if curve_dates and prices and equity_pct and len(curve_dates) == len(prices) == len(equity_pct):
            plot_filename = os.path.join(finance_dir, f"forecast-results/{test_request.stock_code}_{mode_suffix}_equity_vs_actual.png")
            f.write("=== Figures ===\n")
            f.write(f"Validation actual price (chunk end) vs backtest cumulative return: {plot_filename}\n\n")
        
        f.write("=== Trade details ===\n")
        for trade in backtest['trades']:
            f.write(f"Date: {trade['date']}, Action: {trade['action']}, Price: {trade['price']:.2f}, Size: {trade['size']:.0f}, Reason: {trade['reason']}\n")
    print(f"\nDetailed results saved to: {results_filename}")
