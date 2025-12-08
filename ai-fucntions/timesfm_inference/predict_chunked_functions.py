
from req_res_types import *
from typing import List, Optional, Dict, Any
import os
import sys
import pandas as pd
import numpy as np
import json
from tqdm import tqdm
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
finance_dir = parent_dir
pre_data_dir = os.path.join(parent_dir, 'preprocess_data')
sys.path.append(pre_data_dir)
ak_tools_dir = os.path.join(parent_dir, 'akshare-tools')
sys.path.append(ak_tools_dir)

from dotenv import load_dotenv

load_dotenv()

def _round_obj(o):
    import numpy as _np
    if isinstance(o, (float, _np.floating)):
        return round(float(o), 4)
    if isinstance(o, list):
        return [_round_obj(v) for v in o]
    if isinstance(o, dict):
        return {k: _round_obj(v) for k, v in o.items()}
    return o
# 导入其他模块
from chunks_functions import create_chunks_from_test_data
from processor import df_preprocess
from trading_date_processor import get_trading_date_range
from math_functions import mean_squared_error, mean_absolute_error
from postgres import PostgresHandler
from timesfm_init import init_timesfm
# 在需要时才导入timesfm-2.5版本的inference模块
def import_predict_2p5():
    # 保存原始sys.path
    original_sys_path = sys.path.copy()
    
    # 添加timesfm-2p5-functions路径和timesfm-2.5源码路径
    timesfm_2P5_dir = os.path.join(current_dir, "timesfm-2p5-functions")
    timesfm_src = os.path.join(timesfm_2P5_dir, "timesfm-2.5", "src")
    
    # 只添加必要的路径，而不是完全替换sys.path
    sys.path.insert(0, timesfm_src)
    sys.path.insert(0, timesfm_2P5_dir)
    
    try:
        from inference import predict_2p5
        return predict_2p5
    finally:
        # 恢复原始sys.path
        sys.path = original_sys_path

def _parse_unique_key(unique_key: str) -> Optional[Dict[str, Any]]:
    """
    解析 unique_key，格式约定：
    "{symbol}_best_hlen_{horizon_len}_clen_{context_len}_v_{timesfm_version}"

    返回 dict：{
        'symbol': str,
        'horizon_len': int,
        'context_len': int,
        'timesfm_version': str,
    }
    """
    try:
        s = str(unique_key).strip()
        parts = s.split("_best_hlen_")
        if len(parts) != 2:
            return None
        symbol = parts[0]
        rest = parts[1]
        # rest is like: "{hlen}_clen_{clen}_v_{ver}"
        if "_clen_" not in rest:
            return None
        hlen_str, rest2 = rest.split("_clen_", 1)
        if "_v_" not in rest2:
            return None
        clen_str, ver = rest2.split("_v_", 1)
        return {
            "symbol": symbol,
            "horizon_len": int(hlen_str),
            "context_len": int(clen_str),
            "timesfm_version": ver,
        }
    except Exception:
        return None

async def predict_next_chunk_by_unique_key(
        unique_key: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[int] = None,
        best_prediction_item: Optional[str] = None,
    ) -> Optional[ChunkPredictionResult]:
    """
    根据 unique_key 解析出 symbol、horizon_len、context_len、timesfm_version，并预测“下一个分块”。

    逻辑：
    - 解析 unique_key（格式："{symbol}_best_hlen_{hlen}_clen_{clen}_v_{ver}"）
    - 依据 processor.df_preprocess 获取数据集（可选 start_date/end_date 约束）
    - 用测试集最后一个分块的历史来推断“下一分块”的训练窗口（训练+测试+验证历史到最新）
    - 创建一个长度为 horizon_len 的未来日期窗口作为“下一个分块”的 df_test（若无法确定日期则回退到验证集末尾后的顺延）
    - 使用 predict_single_chunk_mode1 做一次预测
    - 若 persist，则调用 PostgresHandler 保存到 /save-predictions/mtf-best/val-chunk（沿用唯一键，chunk_index 使用连续下标）
    """
    try:
        info = _parse_unique_key(unique_key)
        if not info:
            print(f"❌ 无法解析 unique_key: {unique_key}")
            return None
        if not best_prediction_item:
            print(f"❌ 未提供最佳预测项: {best_prediction_item}")
            return None
        symbol = info["symbol"]
        horizon_len = int(info["horizon_len"])
        context_len = int(info["context_len"])
        timesfm_version = str(info["timesfm_version"]).strip()

        # 计算下一分块的索引：优先使用后端最新验证分块的 chunk_index+1；否则基于本地数据计算
        pg_tmp = None
        stock_type = 1
        stock_name = ""
        # 统一为 Pandas Timestamp，避免与 datetime.date 的类型不一致导致减法报错
        today = pd.Timestamp.today().normalize()
        last_chunk_index = 0
        trading_dates = []
        next_date = None
        chunks_num = 0
        try:
            base_url = os.environ.get('POSTGRES_URL', 'http://go-api.meetlife.com.cn:8000')
            # base_url = 'http://localhost:58004'
            pg_tmp = PostgresHandler(base_url=base_url, api_token="fintrack-dev-token")
            await pg_tmp.open()
            sc_latest, data_latest, _ = await pg_tmp.get_latest_val_chunk(unique_key)
            if sc_latest == 200 and isinstance(data_latest, dict):
                d = data_latest.get('data') if 'data' in data_latest else data_latest
                if isinstance(d, dict):
                    stock_name = d.get('stock_name', "")
                    stock_type = d.get('stock_type', 1)
                    last_start = d.get('start_date')
                    print(f"name, {stock_name}, type, {stock_type}")
                    # 保持为 Timestamp 类型，后续与 today 做差不会类型冲突
                    next_date = pd.Timestamp(last_start) + pd.DateOffset(days=1)
                    # 根据需要的预测周期分块处理
                    if next_date:
                        need_pred_days = (today - next_date).days
                        print(f"✅ 累计需要预测天数: {need_pred_days}")
                        if need_pred_days <= 0:
                            print(f"⚠️ 今天{today} 大于等于最新验证分块结束日期 {next_date}, 无需预测")
                            return -1
                        chunks_num = need_pred_days // horizon_len + 1
                        print(f"✅ 需分块预测次数: {chunks_num}")

                    trading_dates = get_trading_date_range(next_date, chunks_num*horizon_len)
                    print(f"✅ 预测日期窗口: {trading_dates}")
                    last_end = d.get('end_date')
                    last_chunk_index = d.get('chunk_index', 0)
                    print(f"✅ 最新验证分块索引: {last_chunk_index} 最佳预测项: {best_prediction_item}")
                    if not best_prediction_item:
                        return None
                    # 统一比较为 Timestamp 类型
                    if last_end and pd.Timestamp(last_end) >= today:
                        print(f"⚠️ 今天{today} 小于最新验证分块结束日期 {last_end}, 无需预测")
                        return -1
                # if last_start:
                #     try:
                #         last_start_dt = pd.to_datetime(last_start).date()
                #         # 若用户未显式指定 end_date，则按 horizon_len 推导
                #         end_date = (pd.Timestamp(last_start_dt)).strftime('%Y-%m-%d')
                #         print(f"✅ 基于最新验证分块开始日期 {last_start} 推导end日期窗口 -> {end_date}")
                #     except Exception:
                #         pass
        except Exception as e:
            print(f"❌ 从数据库获取最新验证分块失败: {e}")
            return None


        # 预处理数据（在确定 start_date/end_date 后进行）
        df_original, _, _, _ = await df_preprocess(
            stock_code=symbol,
            stock_type=stock_type,
            start_date=None,
            end_date=today.strftime('%Y%m%d'),
            time_step=0,
            years=15,
            horizon_len=horizon_len,
        )
        if df_original is None:
            print(f"❌ 数据预处理失败: {symbol}")
            return None

        # 构造训练窗口：在确定了 start_date/end_date 后再使用初始获取的 df_original 作为训练历史
        df_hist = df_original
        try:
            df_hist["unique_id"] = df_hist["stock_code"].astype(str)
        except Exception:
            pass
        # 数据分割
        original_length = df_hist.shape[0]
        # 使用7:2:1的比例划分训练集、测试集、验证集
        initial_train_size = int(original_length * 0.7)  # 70% 训练集
        train_size = (initial_train_size // horizon_len) * horizon_len
        data_to_remove = original_length - train_size
        start_idx = data_to_remove
        df_train = df_hist.iloc[start_idx:, :]    
        print(f"✅ 训练集长度: {df_train.shape[0]}")
        print(f"训练集日期: {df_train['ds'].iloc[0]} - {df_train['ds'].iloc[-1]}")


        # 初始化模型（2.0 版本需要、2.5 由内部函数处理）
        tfm = None
        if timesfm_version == "2.0":
            tfm = init_timesfm(horizon_len=horizon_len, context_len=context_len)

        req = ChunkedPredictionRequest(
            stock_code=symbol,
            years=15,
            horizon_len=horizon_len,
            start_date=start_date,
            end_date=end_date,
            context_len=context_len,
            time_step=0,
            stock_type=1,
            timesfm_version=timesfm_version,
            user_id=user_id,
        )
        df_test = pd.DataFrame()
        result = None
        for i in range(chunks_num):
            # 基于 chunks_num 逐步扩展训练集长度；避免 ":-0" 导致空切片
            k = (chunks_num - i - 1) * horizon_len
            end_idx = df_train.shape[0] - k
            # 边界保护：确保 end_idx 至少为 1，至多为训练集长度
            if end_idx <= 0:
                print(f"⚠️ 第{i}个分块训练集长度不足（end_idx={end_idx}），跳过该分块")
                continue
            if end_idx > df_train.shape[0]:
                end_idx = df_train.shape[0]
            df_train_chunk = df_train.iloc[: end_idx, :]
            # 打印训练集日期时做空集保护
            if df_train_chunk.empty:
                print(f"⚠️ 第{i}个分块训练集为空，跳过该分块")
                continue
            print(f"✅ 训练集日期: {df_train_chunk['ds'].iloc[0]} - {df_train_chunk['ds'].iloc[-1]}")
            trading_dates_chunk = trading_dates[i * horizon_len: (i + 1) * horizon_len]
            result = predict_single_chunk_mode1(
                df_train=df_train_chunk,
                df_test=df_test,
                tfm=tfm,
                chunk_index=i,
                request=req,
            )
            if result.predictions:
                final_result = result.predictions[best_prediction_item]
                if final_result is None:
                    return None
                final_result = _round_obj(final_result)
                if trading_dates_chunk:
                    dates_str = [d.strftime('%Y-%m-%d') for d in trading_dates_chunk]
                    payload = {
                        "unique_key": unique_key,
                        "chunk_index": last_chunk_index + 1 + i,
                        "start_date": dates_str[0],
                        "end_date": dates_str[-1],
                        # 服务端期望 predictions 为对象（map），不能是数组
                        "predictions": {str(best_prediction_item): final_result},
                        "dates": dates_str,
                        "symbol": symbol,
                        "is_public": 0,
                        "user_id": user_id,
                        "stock_name": stock_name,
                        "stock_type": stock_type,
                        "horizon_len": horizon_len,
                    }
                    print(f"✅ 下一分块数据: {payload}")
                    status_code, data, body_text = await pg_tmp.save_best_val_chunk(payload)
                    if status_code == 200:
                        print(f"✅ 下一分块已保存: unique_key={unique_key}")
                    else:
                        print(f"⚠️ 下一分块保存失败: status={status_code}, body={body_text}")
                    try:
                        await pg_tmp.close()
                    except Exception:
                        pass
        return result
    except Exception as e:
        try:
            print(f"❌ 预测下一分块失败: {e}")
            pg_tmp.close()
        except Exception:
            pass
        return None
    finally:
        try:
            await pg_tmp.close()
        except Exception:
            pass
        return 1

def predict_single_chunk_mode1(
        df_train: pd.DataFrame,
        df_test: pd.DataFrame, 
        tfm, 
        chunk_index: int,
        request: ChunkedPredictionRequest,
    ) -> ChunkPredictionResult:
    """
    模式1：对单个分块进行预测（固定训练集，使用ak_stock_data生成测试数据）
    
    Args:
        df_train: 固定的训练数据
        df_test: 当前分块的测试数据
        tfm: TimesFM模型实例
        stock_code: 股票代码
        chunk_index: 分块索引
        
    Returns:
        ChunkPredictionResult: 分块预测结果
    """
    try:
        if request.timesfm_version == "2.0":
            # 使用新数据集进行预测
            # print(f"正在使用TimesFM-2.0模型对测试集分块 {chunk_index} 进行预测...")
            forecast_df = tfm.forecast_on_df(
                inputs=df_train,
                freq="D",
                value_name="close",
                num_jobs=1,
            )
            rename_dict = {c: f"mtf-{c.split('timesfm-q-')[1]}" for c in forecast_df.columns if c.startswith('timesfm-q-')}
            rename_dict["timesfm"] = "mtf"
            if rename_dict:
                forecast_df = forecast_df.rename(columns=rename_dict)
        elif request.timesfm_version == "2.5":
            # print(f"正在使用TimesFM-2.5模型对测试集分块 {chunk_index} 进行预测...")
            predict_2p5_func = import_predict_2p5()
            forecast_df = predict_2p5_func(df_train, max_context=request.context_len, pred_horizon=request.horizon_len, unique_id=request.stock_code)

        df_train_last_one = df_train.iloc[-1]
        # 获取预测结果的前horizon_len条记录
        horizon_len = request.horizon_len
        forecast_chunk = forecast_df.head(horizon_len)
        
        # 调试信息：打印预测结果的列名
        # print(f"  预测结果列名: {list(forecast_df.columns)}")
        # print(f"  预测结果形状: {forecast_df.shape}")
        # print(f"  预测结果前{horizon_len}行: ")
        # print(forecast_chunk.head(horizon_len))
        # print(f"  测试数据前{horizon_len}行: ")
        # print(df_test.head(horizon_len))


        # print(f"  实际日期前7行: {actual_dates[:7]}")
        # 获取所有预测分位数
        predictions = {}
        forecast_columns = [col for col in forecast_chunk.columns if col.startswith('mtf-')]
        
        # print(f"找到的预测列: {forecast_columns}")
        
        for col in forecast_columns:
            predictions[col] = forecast_chunk[col].tolist()
        if df_test.empty:
            return ChunkPredictionResult(
                chunk_index=0,
                chunk_start_date="",
                chunk_end_date="",
                predictions=predictions,
                actual_values=[],
                metrics={}
            )
        # 提取预测值和实际值
        actual_values = df_test['close'].tolist()
        # 计算所有分位数的评估指标
        quantile_metrics = {}
        best_quantile_colname = None
        best_quantile_colname_pct = None
        best_score = float('inf')
        best_diff_pct = float('inf') # 最优涨跌幅百分比差
        # 定义要评估的分位数范围 (0.1 到 0.9)
        target_quantiles = [f'mtf-0.{i}' for i in range(1, 10)]
        
        for quantile in target_quantiles:
            if quantile in predictions:
                pred_values = predictions[quantile]
                
                # 确保预测值和实际值长度一致
                min_len = min(len(pred_values), len(actual_values))
                pred_values_trimmed = pred_values[:min_len]
                actual_values_trimmed = actual_values[:min_len]
                # 确保预测值和实际值长度一致
                base_price = float(df_train_last_one['close']) if 'close' in df_train_last_one else actual_values_trimmed[0]
                if not base_price or base_price == 0:
                    base_price = actual_values_trimmed[0]
                # 计算MSE和MAE
                mse_q = mean_squared_error(np.array(pred_values_trimmed), np.array(actual_values_trimmed))
                mae_q = mean_absolute_error(np.array(pred_values_trimmed), np.array(actual_values_trimmed))
                pct_q = (pred_values_trimmed[-1] / base_price - 1) * 100
                actual_pct = (actual_values_trimmed[-1] / base_price - 1) * 100
                if actual_pct > 0:
                    diff_pct = abs(pct_q - actual_pct) / actual_pct # 预测涨跌幅与实际涨跌幅的百分比差
                else:
                    diff_pct = 1 # 实际涨跌幅为0时，设置为无穷大
                # 计算综合得分 (MSE和MAE各占50%权重)
                # 为了统一量纲，对MSE和MAE进行标准化处理
                combined_score = 0.5 * mse_q + 0.5 * mae_q

                # 计算该分位数的MLE与平均负对数似然
                try:
                    # 计算残差：实际值减去预测值
                    residuals_q = np.array(actual_values_trimmed, dtype=float) - np.array(pred_values_trimmed, dtype=float)
                    # 用残差的标准差估计噪声标准差 σ̂
                    sigma_hat_q = float(np.sqrt(np.mean(residuals_q ** 2)))
                    # 若 σ̂ ≤ 0，则加一个极小值防止除零；否则不加
                    eps_q = 1e-8 if sigma_hat_q <= 0 else 0.0
                    sigma_eff_q = sigma_hat_q + eps_q
                    # 计算平均负对数似然（NLL），假设残差服从 N(0, σ²)
                    avg_nll_q = float(0.5 * np.mean(np.log(2 * np.pi * (sigma_eff_q ** 2)) + (residuals_q ** 2) / (sigma_eff_q ** 2)))
                except Exception as e:
                    # 若计算失败，打印错误信息并置空
                    print(f"  计算分位数 {quantile} 的MLE和平均负对数似然时出错: {str(e)} 第{e.__traceback__.tb_lineno}行")
                    sigma_hat_q = None
                    avg_nll_q = None
                
                quantile_metrics[quantile] = {
                    'mse': mse_q,
                    'mae': mae_q,
                    'combined_score': combined_score,
                    'pred_pct': pct_q,
                    'actual_pct': actual_pct,
                    'diff_pct': diff_pct,
                    'pred_values': pred_values_trimmed,
                    'actual_values': actual_values_trimmed,
                    'mle': sigma_hat_q,
                    'avg_nll': avg_nll_q
                }
                
                # 找到最优分位数
                if combined_score < best_score:
                    best_score = combined_score
                    best_quantile_colname = quantile
                if diff_pct < best_diff_pct:
                    best_diff_pct = diff_pct
                    best_quantile_colname_pct = quantile
        # 如果没有找到任何有效的分位数预测，使用默认值
        if not quantile_metrics:
            print(f"  ⚠️ 警告: 未找到有效的分位数预测，使用默认值")
            mse = 0.0
            mae = 0.0
            best_quantile_colname = 'mtf-0.5'
        else:
            # 使用最优分位数的指标
            mse = quantile_metrics[best_quantile_colname]['mse']
            mae = quantile_metrics[best_quantile_colname]['mae']
            
            # print(f"  📊 分位数评估结果:")
            # for q, metrics in quantile_metrics.items():
            #     print(f"    {q}: MSE={metrics['mse']:.2f}, MAE={metrics['mae']:.2f}, 综合得分={metrics['combined_score']:.2f}, 预测涨跌幅={metrics['pred_pct']:.2f}, 实际涨跌幅={metrics['actual_pct']:.2f}, 百分比差={metrics['diff_pct']:.2f}")
            # print(f"  🏆 最优分位数: {best_quantile_colname} (综合得分: {best_score:.6f})")
            # print(f"  🏆 最优分位数(涨跌幅): {best_quantile_colname_pct} (百分比差: {best_diff_pct:.2f})")
            # print(f"  最优(涨跌幅)预测值: {quantile_metrics[best_quantile_colname_pct]['pred_values']}")
            # print(f"  最优(涨跌幅)实际值: {quantile_metrics[best_quantile_colname_pct]['actual_values']}")
            forecast_chunk["best_quantile_colname_pct"] = best_quantile_colname_pct
            forecast_chunk["best_quantile_colname"] = best_quantile_colname
            forecast_chunk["best_diff_pct"] = best_diff_pct
            forecast_chunk["best_score"] = best_score
            forecast_chunk["best_pred_pct"] = quantile_metrics[best_quantile_colname_pct]['pred_pct']
            forecast_chunk["actual_pct"] = quantile_metrics[best_quantile_colname_pct]['actual_pct']
            forecast_chunk["diff_pct"] = quantile_metrics[best_quantile_colname_pct]['diff_pct']
            forecast_chunk["mse"] = quantile_metrics[best_quantile_colname_pct]['mse']
            forecast_chunk["mae"] = quantile_metrics[best_quantile_colname_pct]['mae']
            forecast_chunk["combined_score"] = quantile_metrics[best_quantile_colname_pct]['combined_score']
            forecast_chunk["symbol"] = forecast_chunk["unique_id"]
        
        # 获取实际值和预测值对应的日期范围
        # 实际值和预测值对应的是分块中的最后horizon_len个日期
        chunk_dates = df_test['ds'].tolist()
        prediction_start_date = chunk_dates[-len(actual_values)].strftime('%Y-%m-%d') if len(actual_values) > 0 else chunk['ds'].min().strftime('%Y-%m-%d')
        prediction_end_date = chunk_dates[-1].strftime('%Y-%m-%d')
        
        # 保持原有的分块日期范围作为备用
        chunk_start_date = prediction_start_date
        chunk_end_date = prediction_end_date

        
        return ChunkPredictionResult(
            chunk_index=chunk_index,
            chunk_start_date=chunk_start_date,
            chunk_end_date=chunk_end_date,
            predictions=predictions,
            actual_values=actual_values,
            metrics={
                'mse': mse, 
                'mae': mae,
                'mle': avg_nll_q if avg_nll_q is not None else float('inf'),
                'best_quantile_colname': best_quantile_colname,
                'best_quantile_colname_pct': best_quantile_colname_pct,
                'best_combined_score': best_score,
                'best_diff_pct': best_diff_pct,
                'all_quantile_metrics': quantile_metrics,

            }
        )
        
    except Exception as e:
        print(f"分块 {chunk_index} 预测失败: {str(e)} 第{e.__traceback__.tb_lineno}行")
        # 返回空结果
        return ChunkPredictionResult(
            chunk_index=chunk_index,
            chunk_start_date="",
            chunk_end_date="",
            predictions={},
            actual_values=[],
            metrics={
                'mse': float('inf'), 
                'mae': float('inf'),
                'best_quantile_colname': 'mtf',
                'best_quantile_colname_pct': 'mtf',
                'best_combined_score': float('inf'),
                'best_diff_pct': float('inf'),
                'all_quantile_metrics': {}
            }
        )

async def predict_chunked_mode_for_best(request: ChunkedPredictionRequest) -> ChunkedPredictionResponse:
    """
    模式1分块预测主函数 - 支持分块预测、最佳分数选择和在验证集上验证
    
    Args:
        request: 分块预测请求
        tfm: TimesFM模型实例
        
    Returns:
        ChunkedPredictionResponse: 分块预测响应，包含最佳预测项和验证结果
    """
    import time
    start_time = time.time()
    try:
        # 数据预处理
        df_original, df_train, df_test, df_val = await df_preprocess(
            request.stock_code, 
            request.stock_type, 
            request.start_date,
            request.end_date,
            request.time_step, 
            years=request.years, 
            horizon_len=request.horizon_len
        )
        
        # 检查数据预处理是否成功
        if df_original is None or df_train is None or df_test is None or df_val is None:
            print(f"❌ 股票 {request.stock_code} 数据预处理失败，无法进行预测")
            return ChunkedPredictionResponse(
                stock_code=request.stock_code,
                total_chunks=0,
                horizon_len=request.horizon_len,
                context_len=request.context_len,
                chunk_results=[],
                overall_metrics={
                    'avg_mse': float('inf'),
                    'avg_mae': float('inf'),
                    'error': 'Data preprocessing failed'
                },
                processing_time=time.time() - start_time
            )
        
        print(f"✅ 股票 {request.stock_code} 数据预处理成功")
        print(f"📊 数据集大小: 训练集={len(df_train)}, 测试集={len(df_test)}, 验证集={len(df_val)}")
        
        # 添加唯一标识符
        df_train["unique_id"] = df_train["stock_code"].astype(str)
        df_test["unique_id"] = df_test["stock_code"].astype(str)
        df_val["unique_id"] = df_val["stock_code"].astype(str)
        
        # 对测试数据进行分块（自动计算分块数量，不使用chunk_num限制）
        chunks = create_chunks_from_test_data(df_test, request.horizon_len)
        active_chunks = chunks
        
        # 对每个分块进行预测
        chunk_results = []
        all_mse = []
        all_mae = []
        all_predictions = []  # 存储所有分块的所有预测结果
        
        if len(active_chunks) == 0:
            print(f"❌ 股票 {request.stock_code} 测试集分块为空，无法进行预测")
            return ChunkedPredictionResponse(
                stock_code=request.stock_code,
                total_chunks=0,
                horizon_len=request.horizon_len,
                chunk_results=[],
                overall_metrics={
                    'avg_mse': float('inf'),
                    'avg_mae': float('inf'),
                    'error': 'Empty test chunks'
                },
                processing_time=time.time() - start_time
            )
        if request.timesfm_version == "2.5":
            tfm = None
        if request.timesfm_version == "2.0":
            tfm = init_timesfm(request.horizon_len, request.context_len)
        tqdm_bar = tqdm(total=len(active_chunks), desc="处理测试集分块")
        for i, chunk in enumerate(active_chunks):
            tqdm_bar.update(1)
            tqdm_bar.set_description(f"处理测试集分块 {i+1}/{len(active_chunks)}")
            tqdm_bar.refresh()
            history_len = i * request.horizon_len
            if history_len > 0:
                df_train_current = pd.concat([df_train, df_test.iloc[:history_len, :]], axis=0)
            else:
                df_train_current = df_train
            df_train_last_one = df_train_current.iloc[-1, :]
            print(f"当前分块 {i+1}/{len(active_chunks)} 最后日期: {df_train_last_one['ds'].strftime('%Y-%m-%d')}")
            result = predict_single_chunk_mode1(
                df_train=df_train_current,
                df_test=chunk,
                tfm=tfm,
                chunk_index=i,
                request=request,
            )
            
            chunk_results.append(result)
            
            # 收集指标用于计算总体指标
            if result.metrics['mse'] != float('inf'):
                all_mse.append(result.metrics['mse'])
                all_mae.append(result.metrics['mae'])
                
            # 收集所有预测结果
            if result.predictions:
                all_predictions.append({
                    'chunk_index': i,
                    'predictions': result.predictions,
                    'actual_values': result.actual_values,
                    'dates': pd.date_range(
                        start=pd.to_datetime(result.chunk_start_date),
                        end=pd.to_datetime(result.chunk_end_date),
                        freq='D'
                    )[:len(result.actual_values)]
                })
        
        # 分析最佳预测项 (mtf-0.1 到 mtf-0.9)
        best_prediction_item = None
        best_score = float('inf')
        best_metrics = {}
        
        prediction_items = [f"mtf-0.{i}" for i in range(1, 10)]
        
        for item in prediction_items:
            item_mse = []
            item_mae = []
            item_returns = []  # 涨跌幅
            item_mle = []
            
            for pred_data in all_predictions:
                if item in pred_data['predictions']:
                    pred_values = pred_data['predictions'][item]
                    actual_values = pred_data['actual_values']
                    
                    # 计算MSE和MAE
                    mse = mean_squared_error(actual_values, pred_values)
                    mae = mean_absolute_error(actual_values, pred_values)
                    item_mse.append(mse)
                    item_mae.append(mae)
                    
                    # 计算涨跌幅：统一以 df_train_last_one 的收盘价为起点
                    if len(pred_values) >= 1 and len(actual_values) >= 1:
                        base_price = float(df_train_last_one['close']) if 'close' in df_train_last_one else actual_values[0]
                        if not base_price or base_price == 0:
                            base_price = actual_values[0]
                        pred_return = (pred_values[-1] - base_price) / base_price * 100
                        actual_return = (actual_values[-1] - base_price) / base_price * 100
                        item_returns.append(abs(pred_return - actual_return))

                    try:
                        chunk_idx = pred_data['chunk_index']
                        cr = chunk_results[chunk_idx]
                        qm = (cr.metrics or {}).get('all_quantile_metrics', {})
                        mle_val = None
                        if item in qm:
                            mle_val = qm[item].get('mle')
                        if mle_val is None:
                            min_len_q = min(len(pred_values), len(actual_values))
                            if min_len_q > 0:
                                residuals_q = np.array(actual_values[:min_len_q], dtype=float) - np.array(pred_values[:min_len_q], dtype=float)
                                mle_val = float(np.sqrt(np.mean(residuals_q ** 2)))
                        if mle_val is not None:
                            item_mle.append(mle_val)
                    except Exception:
                        pass
            
            if item_mse:
                avg_mse = np.mean(item_mse)
                avg_mae = np.mean(item_mae)
                avg_return_diff = np.var(item_returns) if item_returns else float('inf')
                avg_mle = np.var(item_mle) if item_mle else float('inf')
                # 综合评分 (MSE权重0.3, MAE权重0.3, 涨跌幅差异权重0.4)
                # composite_score = 0.3 * avg_mse + 0.3 * avg_mae + 0.4 * avg_return_diff
                composite_score = 0.3 * avg_mse + 0.3 * avg_mae + 0.4 * avg_return_diff
                
                if composite_score < best_score:
                    best_score = composite_score
                    best_prediction_item = item
                    best_metrics = {
                        'mse': avg_mse,
                        'mae': avg_mae,
                        'return_diff': avg_return_diff,
                        'mle': avg_mle,
                        'composite_score': composite_score
                    }
        
        print(f"🎯 最佳预测项: {best_prediction_item}")
        print(f"📊 最佳指标: MSE={best_metrics.get('mse', 'N/A'):.4f}, "
                f"MAE={best_metrics.get('mae', 'N/A'):.4f}, "
                f"涨跌幅差异={best_metrics.get('return_diff', 'N/A'):.2f}%, "
                f"MLE={best_metrics.get('mle', 'N/A'):.4f}, "
                f"综合评分={best_metrics.get('composite_score', 'N/A'):.4f}")
        
        # 在验证集上使用最佳预测项进行验证
        saved_best_ok = False
        validation_results = None
        val_results: List[ChunkPredictionResult] = []
        if best_prediction_item and len(df_val) >= request.horizon_len:
            print(f"🔍 使用最佳预测项 {best_prediction_item} 在验证集上进行验证...")
            val_resp = await predict_validation_chunks_only(
                request,
                tfm=tfm,
                timesfm_version=request.timesfm_version,
                fixed_best_prediction_item=best_prediction_item,
                persist_best=False,
                persist_val_chunks=True,
            )
            val_results = val_resp.validation_chunk_results or []
            try:
                vr = val_resp.overall_metrics.get('validation_results') if isinstance(val_resp.overall_metrics, dict) else None
            except Exception:
                vr = None
            validation_results = vr
            if validation_results:
                print(
                    f"✅ 验证结果: MSE={validation_results.get('validation_mse', float('inf')):.4f}, "
                    f"MAE={validation_results.get('validation_mae', float('inf')):.4f}, "
                    f"MLE={validation_results.get('validation_mle', float('inf')):.4f}, "
                    f"涨跌幅差异={validation_results.get('validation_return_diff', float('inf')):.2f}%"
                )
        
        # 计算总体指标
        overall_metrics = {
            'avg_mse': np.mean(all_mse) if all_mse else float('inf'),
            'avg_mae': np.mean(all_mae) if all_mae else float('inf'),
            'total_chunks': len(chunks),
            'successful_chunks': len(all_mse),
            'best_prediction_item': best_prediction_item,
            'best_metrics': best_metrics,
            'validation_results': validation_results
        }

        base_url = os.environ.get('POSTGRES_URL', 'http://go-api.meetlife.com.cn:8000')
        pg = PostgresHandler(base_url=base_url, api_token="fintrack-dev-token")
        await pg.open()

        # 将最佳分位数按股票代码写入 JSON，便于回测直接读取
        try:
            out_dir = os.path.join(finance_dir, "forecast-results")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{request.stock_code}_best_hlen_{request.horizon_len}_clen_{request.context_len}_v_{request.timesfm_version}.json")
            payload = {
                "stock_code": request.stock_code,
                "best_prediction_item": best_prediction_item,
                "timesfm_version": request.timesfm_version,
                "best_metrics": _round_obj(best_metrics),
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(_round_obj(payload), f, ensure_ascii=False, indent=2)
            print(f"✅ 最佳分位数已保存: {out_path} -> {best_prediction_item}")

            try:
                def to_date_str(x):
                    try:
                        return pd.to_datetime(x).strftime('%Y-%m-%d')
                    except Exception:
                        return str(x)

                train_start_date = to_date_str(df_train['ds'].min())
                train_end_date = to_date_str(df_train['ds'].max())
                test_start_date = to_date_str(df_test['ds'].min())
                test_end_date = to_date_str(df_test['ds'].max())
                val_start_date = to_date_str(df_val['ds'].min())
                val_end_date = to_date_str(df_val['ds'].max())

                unique_key = f"{request.stock_code}_best_hlen_{request.horizon_len}_clen_{request.context_len}_v_{request.timesfm_version}"

                go_payload = {
                    "unique_key": unique_key,
                    "symbol": request.stock_code,
                    "timesfm_version": request.timesfm_version,
                    "best_prediction_item": best_prediction_item,
                    "best_metrics": _round_obj(best_metrics),
                    "train_start_date": train_start_date,
                    "train_end_date": train_end_date,
                    "test_start_date": test_start_date,
                    "test_end_date": test_end_date,
                    "val_start_date": val_start_date,
                    "val_end_date": val_end_date,
                    "context_len": int(request.context_len),
                    "horizon_len": int(request.horizon_len),
                    "user_id": request.user_id,
                    "is_public": 1 if request.user_id == 1 else 0,
                    "stock_type": int(request.stock_type),
                }

                status_code, data, body_text = await pg.save_best_prediction(go_payload)
                if status_code == 200:
                    print(f"✅ 已通过Go后端保存到PG: unique_key={unique_key}")
                    saved_best_ok = True
                else:
                    print(f"⚠️ Go后端保存失败: status={status_code}, body={body_text}")
            except Exception as go_err:
                print(f"⚠️ 调用Go后端保存到PG失败: {go_err}")
        except Exception as save_err:
            print(f"⚠️ 保存最佳分位 JSON 失败: {save_err}")

        # 验证分块的持久化由 predict_validation_chunks_only 处理；此处仅在未保存best时提示
        if val_results and not saved_best_ok:
            print("⚠️ 跳过验证分块写入：未成功保存timesfm-best，避免外键冲突")

        try:
            await pg.close()
        except Exception:
            pass
        
        # 拼接所有分块的预测结果
        concatenated_predictions = {}
        concatenated_actual = []
        concatenated_dates = []
        
        if chunk_results:
            # 获取预测列名（从第一个分块结果中获取）
            prediction_columns = list(chunk_results[0].predictions.keys())
            
            # 初始化拼接预测结果字典
            for col in prediction_columns:
                concatenated_predictions[col] = []
            
            # 拼接每个分块的结果
            for result in chunk_results:
                start_date = pd.to_datetime(result.chunk_start_date, errors='coerce')
                end_date = pd.to_datetime(result.chunk_end_date, errors='coerce')
                chunk_size = len(result.actual_values)
                if chunk_size == 0 or pd.isna(start_date) or pd.isna(end_date):
                    continue

                for col in prediction_columns:
                    if col in result.predictions:
                        concatenated_predictions[col].extend(result.predictions[col])
                    else:
                        concatenated_predictions[col].extend([float('nan')] * chunk_size)

                concatenated_actual.extend(result.actual_values)

                chunk_dates = pd.date_range(start=start_date, end=end_date, freq='D')
                concatenated_dates.extend([date.strftime('%Y-%m-%d') for date in chunk_dates[:chunk_size]])
        
        processing_time = time.time() - start_time
        
        resp = ChunkedPredictionResponse(
            stock_code=request.stock_code,
            total_chunks=len(chunks),
            horizon_len=request.horizon_len,
            context_len=request.context_len,
            chunk_results=chunk_results,
            overall_metrics=overall_metrics,
            processing_time=processing_time,
            concatenated_predictions=concatenated_predictions if concatenated_predictions else None,
            concatenated_actual=concatenated_actual if concatenated_actual else None,
            concatenated_dates=concatenated_dates if concatenated_dates else None,
            validation_chunk_results=val_results if val_results else None
        )

        # 将完整的分块响应保存为 JSON，便于后续直接加载并跳过预测
        try:
            out_dir = os.path.join(finance_dir, "forecast-results")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{request.stock_code}_chunked_response.json")

            def _cr_to_dict(cr: ChunkPredictionResult):
                return {
                    "chunk_index": cr.chunk_index,
                    "chunk_start_date": cr.chunk_start_date,
                    "chunk_end_date": cr.chunk_end_date,
                    "predictions": cr.predictions,
                    "actual_values": cr.actual_values,
                    "metrics": cr.metrics,
                }

            payload = {
                "stock_code": resp.stock_code,
                "total_chunks": resp.total_chunks,
                "horizon_len": resp.horizon_len,
                "chunk_results": [ _cr_to_dict(cr) for cr in (resp.chunk_results or []) ],
                "overall_metrics": resp.overall_metrics,
                "processing_time": resp.processing_time,
                "concatenated_predictions": resp.concatenated_predictions,
                "concatenated_actual": resp.concatenated_actual,
                "concatenated_dates": resp.concatenated_dates,
                "validation_chunk_results": [ _cr_to_dict(vcr) for vcr in (resp.validation_chunk_results or []) ] if resp.validation_chunk_results else None,
            }

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(_round_obj(payload), f, ensure_ascii=False, indent=2)
            print(f"✅ 分块响应已保存: {out_path}")
        except Exception as save_err:
            print(f"⚠️ 保存分块响应 JSON 失败: {save_err}")

        return resp
    except Exception as e:
        # 兜底：主流程异常时返回占位响应，并打印错误信息
        processing_time = time.time() - start_time
        try:
            lineno = e.__traceback__.tb_lineno if getattr(e, "__traceback__", None) else -1
        except Exception:
            lineno = -1
        print(f"模式1分块预测主函数失败: {str(e)} 错误行 {lineno}")
        return ChunkedPredictionResponse(
            stock_code=request.stock_code,
            total_chunks=0,
            horizon_len=request.horizon_len,
            context_len=request.context_len,
            chunk_results=[],
            overall_metrics={'avg_mse': float('inf'), 'avg_mae': float('inf'), 'error': str(e)},
            processing_time=processing_time,
            validation_chunk_results=None,
        )

async def predict_validation_chunks_only(
        request: ChunkedPredictionRequest,
        tfm = None,
        timesfm_version: str = "2.0",
        fixed_best_prediction_item: Optional[str] = None,
        persist_best: bool = True,
        persist_val_chunks: bool = True,
    ) -> ChunkedPredictionResponse:
    """
    仅预测验证集分块，并使用已知的最佳分位数（来自JSON或环境变量）。

    用途：当已存在最佳分位数，但没有缓存的分块响应时，仅预测验证集以进行回测，无需对测试集进行预测。

    Returns:
        ChunkedPredictionResponse: chunk_results为空；validation_chunk_results包含验证集分块预测结果；
        overall_metrics中包含best_prediction_item与验证集指标。
    """
    import time
    start_time = time.time()

    try:
        # 数据预处理
        df_original, df_train, df_test, df_val = await df_preprocess(
            request.stock_code,
            request.stock_type,
            request.start_date,
            request.end_date,
            request.time_step,
            years=request.years,
            horizon_len=request.horizon_len,
        )

        if df_original is None or df_train is None or df_test is None or df_val is None:
            print(f"❌ 股票 {request.stock_code} 数据预处理失败，无法进行验证集预测")
            return ChunkedPredictionResponse(
                stock_code=request.stock_code,
                total_chunks=0,
                horizon_len=request.horizon_len,
                chunk_results=[],
                overall_metrics={
                    'avg_mse': float('inf'),
                    'avg_mae': float('inf'),
                    'error': 'Data preprocessing failed'
                },
                processing_time=time.time() - start_time
            )

        print(f"✅ 股票 {request.stock_code} 数据预处理成功（验证集专用模式）")
        print(f"📊 数据集大小: 训练集={len(df_train)}, 测试集={len(df_test)}, 验证集={len(df_val)}")

        # 添加唯一标识符
        df_train["unique_id"] = df_train["stock_code"].astype(str)
        df_test["unique_id"] = df_test["stock_code"].astype(str)
        df_val["unique_id"] = df_val["stock_code"].astype(str)

        # 对验证集进行分块
        val_chunks = create_chunks_from_test_data(df_val, request.horizon_len)
        val_results: List[ChunkPredictionResult] = []
        tqdm_bar = tqdm(total=len(val_chunks), desc="处理验证集分块")
        for i, val_chunk in enumerate(val_chunks):
            tqdm_bar.update(1)
            tqdm_bar.set_description(f"处理验证集分块 {i+1}/{len(val_chunks)}")
            tqdm_bar.refresh()
            history_len = i * request.horizon_len
            if history_len > 0:
                cumulative_train_data = pd.concat([df_train, df_test, df_val.iloc[:history_len, :]], axis=0)
            else:
                cumulative_train_data = pd.concat([df_train, df_test], axis=0)
            cumulative_last_one = cumulative_train_data.iloc[-1, :]
            print(f"当前分块 {i+1}/{len(val_chunks)} 最后日期: {cumulative_last_one['ds'].strftime('%Y-%m-%d')}")
            val_result = predict_single_chunk_mode1(
                df_train=cumulative_train_data,
                df_test=val_chunk,
                tfm=tfm,
                chunk_index=i,
                request=request,
            )
            val_results.append(val_result)

        # 计算验证集指标（使用固定最佳分位数）
        validation_results = None
        if fixed_best_prediction_item:
            val_mse = []
            val_mae = []
            val_returns = []
            val_mle = []

            # 使用训练集最后一条的收盘价作为收益对比的基准，与主流程一致
            try:
                df_train_last_one = df_train.iloc[-1, :]
            except Exception:
                df_train_last_one = None

            for result in val_results:
                if fixed_best_prediction_item in result.predictions:
                    pred_values = result.predictions[fixed_best_prediction_item]
                    actual_values = result.actual_values

                    mse = mean_squared_error(actual_values, pred_values)
                    mae = mean_absolute_error(actual_values, pred_values)
                    val_mse.append(mse)
                    val_mae.append(mae)

                    if len(pred_values) >= 1 and len(actual_values) >= 1:
                        try:
                            base_price = float(df_train_last_one['close']) if (df_train_last_one is not None and 'close' in df_train_last_one) else actual_values[0]
                        except Exception:
                            base_price = actual_values[0]
                        if not base_price or base_price == 0:
                            base_price = actual_values[0]
                        pred_return = (pred_values[-1] - base_price) / base_price * 100
                        actual_return = (actual_values[-1] - base_price) / base_price * 100
                        val_returns.append(abs(pred_return - actual_return))

                    min_len = min(len(pred_values), len(actual_values))
                    if min_len > 0:
                        residuals = np.array(actual_values[:min_len], dtype=float) - np.array(pred_values[:min_len], dtype=float)
                        mle_val = float(np.sqrt(np.mean(residuals ** 2)))
                        val_mle.append(mle_val)

            validation_results = {
                'best_prediction_item': fixed_best_prediction_item,
                'validation_mse': np.mean(val_mse) if val_mse else float('inf'),
                'validation_mae': np.mean(val_mae) if val_mae else float('inf'),
                'validation_return_diff': np.mean(val_returns) if val_returns else float('inf'),
                'validation_mle': np.mean(val_mle) if val_mle else float('inf'),
                'validation_chunks': len(val_results),
                'successful_validation_chunks': len(val_mse),
            }
            print(
                f"✅ 验证结果: MSE={validation_results['validation_mse']:.4f}, "
                f"MAE={validation_results['validation_mae']:.4f}, "
                f"MLE={validation_results['validation_mle']:.4f}, "
                f"涨跌幅差异={validation_results['validation_return_diff']:.2f}%"
            )

        # 仅验证模式下的持久化：预先写入timesfm-best，避免分块外键失败
        pg = None
        saved_best_ok = False
        try:
            base_url = os.environ.get('POSTGRES_URL', 'http://go-api.meetlife.com.cn:8000')
            pg = PostgresHandler(base_url=base_url, api_token="fintrack-dev-token")
            await pg.open()
            if fixed_best_prediction_item and persist_best:
                timesfm_version_str = timesfm_version
                def to_date_str(val):
                    try:
                        dt = pd.to_datetime(val, errors='coerce')
                        return dt.strftime('%Y-%m-%d') if not pd.isna(dt) else str(val)
                    except Exception:
                        return str(val)

                train_start_date = to_date_str(df_train['ds'].min())
                train_end_date = to_date_str(df_train['ds'].max())
                test_start_date = to_date_str(df_test['ds'].min())
                test_end_date = to_date_str(df_test['ds'].max())
                val_start_date = to_date_str(df_val['ds'].min())
                val_end_date = to_date_str(df_val['ds'].max())

                unique_key_best = f"{request.stock_code}_best_hlen_{request.horizon_len}_clen_{request.context_len}_v_{timesfm_version_str}"

                best_metrics_payload = validation_results if validation_results else {
                    'best_prediction_item': fixed_best_prediction_item
                }
                go_payload = {
                    "unique_key": unique_key_best,
                    "symbol": request.stock_code,
                    "timesfm_version": timesfm_version_str,
                    "best_prediction_item": fixed_best_prediction_item,
                    "best_metrics": _round_obj(best_metrics_payload),
                    "train_start_date": train_start_date,
                    "train_end_date": train_end_date,
                    "test_start_date": test_start_date,
                    "test_end_date": test_end_date,
                    "val_start_date": val_start_date,
                    "val_end_date": val_end_date,
                    "context_len": int(request.context_len),
                    "horizon_len": int(request.horizon_len),
                    "user_id": getattr(request, 'user_id', None),
                    "is_public": 1 if getattr(request, 'user_id', None) == 1 else 0,
                }

                status_code, data, body_text = await pg.save_best_prediction(go_payload)
                if status_code == 200:
                    print(f"✅ 已通过Go后端保存timesfm-best(仅验证模式): unique_key={unique_key_best}")
                    saved_best_ok = True
                else:
                    print(f"⚠️ 保存timesfm-best失败(仅验证模式): status={status_code}, body={body_text}")
        except Exception as go_err:
            print(f"⚠️ 仅验证模式调用Go后端保存best失败: {go_err}")

        # 将验证集分块逐块写入后端（仅验证模式也持久化）
        try:
            if val_results and persist_val_chunks and pg is not None:
                base_url = os.environ.get('POSTGRES_URL', 'http://go-api.meetlife.com.cn:8000')
                timesfm_version_str = timesfm_version
                unique_key_val = f"{request.stock_code}_best_hlen_{request.horizon_len}_clen_{request.context_len}_v_{timesfm_version_str}"

                best_confirmed = saved_best_ok
                if not best_confirmed:
                    try:
                        status_code, data, body_text = await pg.get_best_by_unique(unique_key_val)
                        best_confirmed = (status_code == 200)
                    except Exception as chk_err:
                        best_confirmed = False
                if not best_confirmed:
                    try:
                        if fixed_best_prediction_item:
                            def to_date_str(val):
                                try:
                                    dt = pd.to_datetime(val, errors='coerce')
                                    return dt.strftime('%Y-%m-%d') if not pd.isna(dt) else str(val)
                                except Exception:
                                    return str(val)

                            train_start_date = to_date_str(df_train['ds'].min())
                            train_end_date = to_date_str(df_train['ds'].max())
                            test_start_date = to_date_str(df_test['ds'].min())
                            test_end_date = to_date_str(df_test['ds'].max())
                            val_start_date = to_date_str(df_val['ds'].min())
                            val_end_date = to_date_str(df_val['ds'].max())

                            best_metrics_payload = validation_results if validation_results else {
                                'best_prediction_item': fixed_best_prediction_item
                            }
                            go_payload = {
                                "unique_key": unique_key_val,
                                "symbol": request.stock_code,
                                "timesfm_version": timesfm_version_str,
                                "best_prediction_item": fixed_best_prediction_item,
                                "best_metrics": _round_obj(best_metrics_payload),
                                "train_start_date": train_start_date,
                                "train_end_date": train_end_date,
                                "test_start_date": test_start_date,
                                "test_end_date": test_end_date,
                                "val_start_date": val_start_date,
                                "val_end_date": val_end_date,
                                "context_len": int(request.context_len),
                                "horizon_len": int(request.horizon_len),
                                "user_id": getattr(request, 'user_id', None),
                                "is_public": 1 if getattr(request, 'user_id', None) == 1 else 0,
                            }
                            status_code, data, body_text = await pg.save_best_prediction(go_payload)
                            best_confirmed = (status_code == 200)
                            if best_confirmed:
                                print(f"✅ 已补写timesfm-best: unique_key={unique_key_val}")
                            else:
                                print(f"⚠️ 补写timesfm-best失败: status={status_code}, body={body_text}")
                    except Exception as add_err:
                        print(f"⚠️ 尝试补写timesfm-best异常: {add_err}")
                if not best_confirmed:
                    print(f"⚠️ 跳过验证分块写入：未找到timesfm-best(unique_key={unique_key_val})，避免外键冲突")
                    raise Exception("missing_best_record_for_val_chunks")

                for vcr in val_results:
                    try:
                        start_date = str(vcr.chunk_start_date)
                        end_date = str(vcr.chunk_end_date)
                        size = len(vcr.actual_values)
                        if size <= 0:
                            continue

                        chunk_dates = pd.date_range(
                            start=pd.to_datetime(start_date, errors='coerce'),
                            end=pd.to_datetime(end_date, errors='coerce'),
                            freq='D'
                        )[:size]
                        dates_str = [d.strftime('%Y-%m-%d') for d in chunk_dates]

                        def to_float4_list(arr):
                            out = []
                            for x in arr:
                                try:
                                    out.append(round(float(x), 4))
                                except Exception:
                                    out.append(None)
                            return out

                        predictions_clean = {}
                        preds_map = (vcr.predictions or {})
                        best_key = fixed_best_prediction_item
                        if best_key and best_key in preds_map:
                            predictions_clean[best_key] = to_float4_list(preds_map.get(best_key) or [])
                        else:
                            fallback_key = best_key or "mtf-0.5"
                            if fallback_key in preds_map:
                                predictions_clean[fallback_key] = to_float4_list(preds_map.get(fallback_key) or [])
                            else:
                                for k, arr in preds_map.items():
                                    predictions_clean[k] = to_float4_list(arr or [])
                                    break
                        actual_clean = to_float4_list(vcr.actual_values or [])

                        chunk_payload = {
                            "unique_key": unique_key_val,
                            "chunk_index": int(vcr.chunk_index),
                            "start_date": start_date,
                            "end_date": end_date,
                            "predictions": predictions_clean,
                            "actual_values": actual_clean,
                            "dates": dates_str,
                            "symbol": request.stock_code,
                            "is_public": 1 if getattr(request, 'user_id', None) == 1 else 0,
                            "user_id": getattr(request, 'user_id', None),
                            "stock_type": request.stock_type,
                        }

                        status_code, data, body_text = await pg.save_best_val_chunk(_round_obj(chunk_payload))
                        if status_code == 0:
                            print(f"⚠️ 验证分块写入失败(chunk={vcr.chunk_index})，网络异常")
                            continue

                        if status_code == 200:
                            print(f"✅ 验证分块已保存: unique_key={unique_key_val}, chunk_index={vcr.chunk_index}")
                        else:
                            print(f"⚠️ 验证分块保存失败: chunk={vcr.chunk_index}, status={status_code}, body={body_text}")
                    except Exception as e:
                        print(f"⚠️ 处理验证分块写入异常(chunk={getattr(vcr,'chunk_index', '?')}): {e}")
        except Exception as e:
            print(f"⚠️ 验证分块写入后端过程异常: {e}")
        finally:
            try:
                if pg is not None:
                    await pg.close()
            except Exception:
                pass
        if not fixed_best_prediction_item:
            print("⚠️ 未提供固定最佳分位数，验证集指标无法计算，overall_metrics仅包含验证分块数量")

        overall_metrics = {
            'best_prediction_item': fixed_best_prediction_item,
            'validation_results': validation_results,
            'total_chunks': len(val_chunks),
            'successful_chunks': len(val_results),
        }

        processing_time = time.time() - start_time

        resp = ChunkedPredictionResponse(
            stock_code=request.stock_code,
            total_chunks=len(val_chunks),
            horizon_len=request.horizon_len,
            context_len=request.context_len,
            chunk_results=[],
            overall_metrics=overall_metrics,
            processing_time=processing_time,
            concatenated_predictions=None,
            concatenated_actual=None,
            concatenated_dates=None,
            validation_chunk_results=val_results if val_results else None,
        )

        # 保存响应到JSON，便于回测直接加载
        try:
            out_dir = os.path.join(finance_dir, "forecast-results")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{request.stock_code}_chunked_response.json")

            def _cr_to_dict(cr: ChunkPredictionResult):
                return {
                    "chunk_index": cr.chunk_index,
                    "chunk_start_date": cr.chunk_start_date,
                    "chunk_end_date": cr.chunk_end_date,
                    "predictions": cr.predictions,
                    "actual_values": cr.actual_values,
                    "metrics": cr.metrics,
                }

            payload = {
                "stock_code": resp.stock_code,
                "total_chunks": resp.total_chunks,
                "horizon_len": resp.horizon_len,
                "chunk_results": [],
                "overall_metrics": resp.overall_metrics,
                "processing_time": resp.processing_time,
                "concatenated_predictions": resp.concatenated_predictions,
                "concatenated_actual": resp.concatenated_actual,
                "concatenated_dates": resp.concatenated_dates,
                "validation_chunk_results": [ _cr_to_dict(vcr) for vcr in (resp.validation_chunk_results or []) ] if resp.validation_chunk_results else None,
                "is_public": 1,
                "user_id": 1,
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(_round_obj(payload), f, ensure_ascii=False, indent=2)
            print(f"✅ 验证集分块响应已保存: {out_path}")
        except Exception as save_err:
            print(f"⚠️ 保存验证集分块响应 JSON 失败: {save_err}")

        return resp
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"验证集分块预测失败: {str(e)} 错误行 {e.__traceback__.tb_lineno}")
        return ChunkedPredictionResponse(
            stock_code=request.stock_code,
            total_chunks=0,
            horizon_len=request.horizon_len,
            context_len=request.context_len,
            chunk_results=[],
            overall_metrics={'avg_mse': float('inf'), 'avg_mae': float('inf'), 'error': str(e)},
            processing_time=processing_time,
            validation_chunk_results=None,
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"分块预测失败: {str(e)} 错误行 {e.__traceback__.tb_lineno}")
        
        return ChunkedPredictionResponse(
            stock_code=request.stock_code,
            total_chunks=0,
            horizon_len=request.horizon_len,
            context_len=request.context_len,
            chunk_results=[],
            overall_metrics={'avg_mse': float('inf'), 'avg_mae': float('inf'), 'error': str(e)},
            processing_time=processing_time
        )

def main(test_request):
    import asyncio
    if test_request.timesfm_version == "2.0":
        # tfm = init_timesfm(horizon_len=test_request.horizon_len, context_len=test_request.context_len)
        response = asyncio.run(predict_chunked_mode_for_best(test_request))
    else:
        response = asyncio.run(predict_chunked_mode_for_best(test_request))
    # print(response)
    # 输出结果
    print(f"\n=== 分块预测结果 ===")
    print(f"股票代码: {response.stock_code}")
    print(f"总分块数: {response.total_chunks}")
    print(f"预测长度: {response.horizon_len}")
    print(f"上下文长度: {response.context_len}")
    print(f"处理时间: {response.processing_time:.2f} 秒")
    print(f"处理结果: {response.overall_metrics}")
    # 生成绘图
    from plot_functions import plot_chunked_prediction_results
    plot_save_path = os.path.join(finance_dir, f"forecast-results/{test_request.stock_code}_prediction_plot.png")
    try:
        plot_path = plot_chunked_prediction_results(response, plot_save_path)
    except Exception as plot_error:
        print(f"⚠️ 绘图失败: {str(plot_error)}")
    
def test_next_chunked_prediction(unique_key: str, best_prediction_item: str):
    import asyncio
    res = asyncio.run(predict_next_chunk_by_unique_key(
        unique_key=unique_key,
        user_id=1,
        best_prediction_item=best_prediction_item,
    ))
    print(res)

if __name__ == "__main__":
    # from timesfm_init import init_timesfm
    test_request = ChunkedPredictionRequest(
        stock_code="sh510300",
        years=15,
        horizon_len=7,
        start_date="",
        end_date="20251201",
        context_len=2048,
        time_step=0,
        stock_type=2,
        timesfm_version="2.5",
        user_id=1
    )
    main(test_request)
    test_next_chunked_prediction("sh510300_best_hlen_7_clen_256_v_2.5", "mtf-0.4")

    
