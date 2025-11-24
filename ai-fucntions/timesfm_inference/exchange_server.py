import os
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取父目录
parent_dir = os.path.dirname(current_dir)
# 设定finance项目根目录
finance_dir = parent_dir
# 将finance目录添加到系统路径，以便导入模块
sys.path.append(finance_dir)

from timesfm.timesfm_init import init_timesfm
from timesfm.predict_chunked_functions import predict_chunked_mode1
from timesfm.req_res_types import ChunkedPredictionRequest, ChunkedPredictionResponse, ChunkPredictionResult

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

def backtest_from_chunked_response(response: ChunkedPredictionResponse, buy_threshold_pct: float = 10.0, sell_threshold_pct: float = -3.0, initial_cash: float = 100000.0) -> Dict[str, Any]:
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
    
    for cr in response.chunk_results:
        if not cr.actual_values:
            continue
            
        start_price = cr.actual_values[0]
        if start_price is None or np.isnan(start_price):
            continue
            
        # 选择最佳预测分位数
        best_key = _select_closest_pct_quantile(cr)
        if not best_key:
            continue
            
        pred_values = cr.predictions.get(best_key, [])
        if not pred_values:
            continue
            
        # 计算预测的百分比变化 (基于分块结束时的预测价格相对于分块开始时的实际价格)
        predicted_pct_change = ((pred_values[-1] / start_price) - 1) * 100 if start_price != 0 else 0
        
        # 买入逻辑
        if predicted_pct_change >= buy_threshold_pct and shares == 0.0:
            size = cash / start_price
            shares += size
            cash -= size * start_price
            trades.append(BacktestTrade(date=cr.chunk_start_date, action="buy", price=float(start_price), size=float(size), chunk_index=cr.chunk_index, reason=f"pred_pct>={buy_threshold_pct}"))
        # 卖出逻辑
        elif predicted_pct_change <= sell_threshold_pct and shares > 0.0:
            cash += shares * start_price
            trades.append(BacktestTrade(date=cr.chunk_start_date, action="sell", price=float(start_price), size=float(shares), chunk_index=cr.chunk_index, reason=f"pred_pct<={sell_threshold_pct}"))
            shares = 0.0
            
        last_price = cr.actual_values[-1]
        
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
    
    return {
        "initial_cash": initial_cash,
        "final_value": final_value,
        "total_return_pct": total_return,
        "annualized_return_pct": annualized,
        "trades": [trade.__dict__ for trade in trades],
        "buy_threshold_pct": buy_threshold_pct,
        "sell_threshold_pct": sell_threshold_pct
    }

def run_backtest(request: ChunkedPredictionRequest, buy_threshold_pct: float = 10.0, sell_threshold_pct: float = -3.0, initial_cash: float = 100000.0) -> Dict[str, Any]:
    """
    运行完整的回测流程
    
    1. 初始化 TimesFM 模型。
    2. 执行分块预测 (Mode 1)。
    3. 基于预测结果运行回测策略。
    
    Args:
        request: 分块预测请求对象
        buy_threshold_pct: 买入阈值
        sell_threshold_pct: 卖出阈值
        initial_cash: 初始资金
        
    Returns:
        Dict[str, Any]: 包含预测响应和回测结果的字典
    """
    # 初始化模型
    tfm = init_timesfm(horizon_len=request.horizon_len, context_len=request.context_len)
    # 执行预测
    response = predict_chunked_mode1(request, tfm)
    # 执行回测
    result = backtest_from_chunked_response(response, buy_threshold_pct=buy_threshold_pct, sell_threshold_pct=sell_threshold_pct, initial_cash=initial_cash)
    
    return {
        "response": response,
        "backtest": result
    }

if __name__ == "__main__":
    # 测试代码
    test_request = ChunkedPredictionRequest(
        stock_code="sz000001",
        years=10,
        horizon_len=7,
        start_date="20100101",
        end_date="20251114",
        context_len=2048,
        time_step=0,
        stock_type=1,
        chunk_num=10
    )
    
    print(f"\n=== 开始回测 ===")
    print(f"股票代码: {test_request.stock_code}")
    print(f"回测区间: {test_request.start_date} 到 {test_request.end_date}")
    
    # 运行回测
    result = run_backtest(test_request)
    
    response = result["response"]
    backtest = result["backtest"]
    
    print(f"\n=== 预测结果摘要 ===")
    print(f"总分块数: {response.total_chunks}")
    print(f"处理时间: {response.processing_time:.2f} 秒")
    
    print(f"\n=== 回测结果摘要 ===")
    print(f"初始资金: {backtest['initial_cash']:.2f}")
    print(f"最终价值: {backtest['final_value']:.2f}")
    print(f"总收益率: {backtest['total_return_pct']:.2f}%")
    print(f"年化收益率: {backtest['annualized_return_pct']:.2f}%")
    print(f"交易次数: {len(backtest['trades'])}")
    
    print(f"\n=== 交易明细 ===")
    for trade in backtest['trades']:
        print(f"日期: {trade['date']}, 动作: {trade['action']}, 价格: {trade['price']:.2f}, 数量: {trade['size']:.0f}, 原因: {trade['reason']}")
        
    # 保存结果到文件
    mode_suffix = "backtest"
    results_filename = os.path.join(finance_dir, f"forecast-results/{test_request.stock_code}_{mode_suffix}_results.txt")
    
    with open(results_filename, 'w', encoding='utf-8') as f:
        f.write(f"回测结果 - 股票: {test_request.stock_code}\n")
        f.write(f"回测区间: {test_request.start_date} 到 {test_request.end_date}\n\n")
        
        f.write("=== 预测结果摘要 ===\n")
        f.write(f"总分块数: {response.total_chunks}\n")
        f.write(f"处理时间: {response.processing_time:.2f} 秒\n\n")
        
        f.write("=== 回测结果摘要 ===\n")
        f.write(f"初始资金: {backtest['initial_cash']:.2f}\n")
        f.write(f"最终价值: {backtest['final_value']:.2f}\n")
        f.write(f"总收益率: {backtest['total_return_pct']:.2f}%\n")
        f.write(f"年化收益率: {backtest['annualized_return_pct']:.2f}%\n")
        f.write(f"交易次数: {len(backtest['trades'])}\n\n")
        
        f.write("=== 交易明细 ===\n")
        for trade in backtest['trades']:
            f.write(f"日期: {trade['date']}, 动作: {trade['action']}, 价格: {trade['price']:.2f}, 数量: {trade['size']:.0f}, 原因: {trade['reason']}\n")
            
    print(f"\n详细结果已保存到: {results_filename}")