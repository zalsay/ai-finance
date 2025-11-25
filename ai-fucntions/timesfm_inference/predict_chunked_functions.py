
from req_res_types import *
import os
import sys
import pandas as pd
import numpy as np
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
finance_dir = parent_dir
pre_data_dir = os.path.join(parent_dir, 'preprocess_data')
sys.path.append(pre_data_dir)

# 导入其他模块
from chunks_functions import create_chunks_from_test_data
from processor import df_preprocess
from math_functions import mean_squared_error, mean_absolute_error

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

def predict_single_chunk_mode1(
        df_train: pd.DataFrame,
        df_test: pd.DataFrame, 
        tfm, 
        chunk_index: int,
        timesfm_version: str = "2.0",
        symbol: str = ""
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
        if timesfm_version == "2.0":
            # 使用新数据集进行预测
            print(f"正在使用TimesFM-2.0模型对测试集分块 {chunk_index} 进行预测...")
            forecast_df = tfm.forecast_on_df(
                inputs=df_train,
                freq="D",
                value_name="close",
                num_jobs=1,
            )
            rename_dict = {c: f"tsf-{c.split('timesfm-q-')[1]}" for c in forecast_df.columns if c.startswith('timesfm-q-')}
            rename_dict["timesfm"] = "tsf"
            if rename_dict:
                forecast_df = forecast_df.rename(columns=rename_dict)
        elif timesfm_version == "2.5":
            print(f"正在使用TimesFM-2.5模型对测试集分块 {chunk_index} 进行预测...")
            predict_2p5_func = import_predict_2p5()
            forecast_df = predict_2p5_func(df_train, pred_horizon=len(df_test), unique_id=symbol)

        
        # 获取预测结果的前horizon_len条记录
        horizon_len = len(df_test)
        forecast_chunk = forecast_df.head(horizon_len)
        
        # 调试信息：打印预测结果的列名
        # print(f"  预测结果列名: {list(forecast_df.columns)}")
        # print(f"  预测结果形状: {forecast_df.shape}")
        # print(f"  预测结果前{horizon_len}行: ")
        # print(forecast_chunk.head(horizon_len))
        # print(f"  测试数据前{horizon_len}行: ")
        # print(df_test.head(horizon_len))

        # 提取预测值和实际值
        actual_values = df_test['close'].tolist()
        actual_dates = df_test['ds'].tolist()
        # print(f"  实际日期前7行: {actual_dates[:7]}")
        # 获取所有预测分位数
        predictions = {}
        forecast_columns = [col for col in forecast_chunk.columns if col.startswith('tsf-')]
        
        # print(f"找到的预测列: {forecast_columns}")
        
        for col in forecast_columns:
            predictions[col] = forecast_chunk[col].tolist()
        
        # 计算所有分位数的评估指标
        quantile_metrics = {}
        best_quantile_colname = None
        best_quantile_colname_pct = None
        best_score = float('inf')
        best_diff_pct = float('inf') # 最优涨跌幅百分比差
        # 定义要评估的分位数范围 (0.1 到 0.9)
        target_quantiles = [f'tsf-0.{i}' for i in range(1, 10)]
        
        for quantile in target_quantiles:
            if quantile in predictions:
                pred_values = predictions[quantile]
                
                # 确保预测值和实际值长度一致
                min_len = min(len(pred_values), len(actual_values))
                pred_values_trimmed = pred_values[:min_len]
                actual_values_trimmed = actual_values[:min_len]
                
                # 计算MSE和MAE
                mse_q = mean_squared_error(np.array(pred_values_trimmed), np.array(actual_values_trimmed))
                mae_q = mean_absolute_error(np.array(pred_values_trimmed), np.array(actual_values_trimmed))
                pct_q = (pred_values_trimmed[-1] / actual_values_trimmed[0] - 1) * 100
                actual_pct = (actual_values_trimmed[-1] / actual_values_trimmed[0] - 1) * 100
                diff_pct = abs(pct_q - actual_pct) / actual_pct # 预测涨跌幅与实际涨跌幅的百分比差
                # 计算综合得分 (MSE和MAE各占50%权重)
                # 为了统一量纲，对MSE和MAE进行标准化处理
                combined_score = 0.5 * mse_q + 0.5 * mae_q
                
                quantile_metrics[quantile] = {
                    'mse': mse_q,
                    'mae': mae_q,
                    'combined_score': combined_score,
                    'pred_pct': pct_q,
                    'actual_pct': actual_pct,
                    'diff_pct': diff_pct,
                    'pred_values': pred_values_trimmed,
                    'actual_values': actual_values_trimmed
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
            best_quantile_colname = 'tsf-0.5'
        else:
            # 使用最优分位数的指标
            mse = quantile_metrics[best_quantile_colname]['mse']
            mae = quantile_metrics[best_quantile_colname]['mae']
            
            # print(f"  📊 分位数评估结果:")
            # for q, metrics in quantile_metrics.items():
            #     print(f"    {q}: MSE={metrics['mse']:.2f}, MAE={metrics['mae']:.2f}, 综合得分={metrics['combined_score']:.2f}, 预测涨跌幅={metrics['pred_pct']:.2f}, 实际涨跌幅={metrics['actual_pct']:.2f}, 百分比差={metrics['diff_pct']:.2f}")
            print(f"  🏆 最优分位数: {best_quantile_colname} (综合得分: {best_score:.6f})")
            print(f"  🏆 最优分位数(涨跌幅): {best_quantile_colname_pct} (百分比差: {best_diff_pct:.2f})")
            print(f"  最优(涨跌幅)预测值: {quantile_metrics[best_quantile_colname_pct]['pred_values']}")
            print(f"  最优(涨跌幅)实际值: {quantile_metrics[best_quantile_colname_pct]['actual_values']}")
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
            # try:
            #     payload = []
            #     for _, row in forecast_chunk.iterrows():
            #         item = {
            #             "symbol": row.get("symbol"),
            #             "ds": str(row.get("ds")),
            #             "tsf": float(row.get("tsf")) if row.get("tsf") is not None else 0.0,
            #             "tsf_01": float(row.get("tsf-0.1")) if row.get("tsf-0.1") is not None else 0.0,
            #             "tsf_02": float(row.get("tsf-0.2")) if row.get("tsf-0.2") is not None else 0.0,
            #             "tsf_03": float(row.get("tsf-0.3")) if row.get("tsf-0.3") is not None else 0.0,
            #             "tsf_04": float(row.get("tsf-0.4")) if row.get("tsf-0.4") is not None else 0.0,
            #             "tsf_05": float(row.get("tsf-0.5")) if row.get("tsf-0.5") is not None else 0.0,
            #             "tsf_06": float(row.get("tsf-0.6")) if row.get("tsf-0.6") is not None else 0.0,
            #             "tsf_07": float(row.get("tsf-0.7")) if row.get("tsf-0.7") is not None else 0.0,
            #             "tsf_08": float(row.get("tsf-0.8")) if row.get("tsf-0.8") is not None else 0.0,
            #             "tsf_09": float(row.get("tsf-0.9")) if row.get("tsf-0.9") is not None else 0.0,
            #             "chunk_index": chunk_index,
            #             "best_quantile": str(best_quantile_colname),
            #             "best_quantile_pct": str(best_quantile_colname_pct),
            #             "best_pred_pct": float(quantile_metrics[best_quantile_colname_pct]['pred_pct']),
            #             "actual_pct": float(quantile_metrics[best_quantile_colname_pct]['actual_pct']),
            #             "diff_pct": float(quantile_metrics[best_quantile_colname_pct]['diff_pct']),
            #             "mse": float(quantile_metrics[best_quantile_colname_pct]['mse']),
            #             "mae": float(quantile_metrics[best_quantile_colname_pct]['mae']),
            #             "combined_score": float(quantile_metrics[best_quantile_colname_pct]['combined_score']),
            #         }
            #         payload.append(item)

            #     import requests
            #     base_url = os.environ.get("GO_API_BASE_URL", "http://localhost:8080")
            #     token = os.environ.get("API_TOKEN", "fintrack-dev-token")
            #     url = f"{base_url.rstrip('/')}/api/v1/timesfm/forecast/batch"
            #     headers = {"Content-Type": "application/json", "X-Token": token}
            #     resp = requests.post(url, json=payload, headers=headers, timeout=3)
            #     if resp.status_code != 200:
            #         print(f"⚠️ 写入PG失败: HTTP {resp.status_code} {resp.text[:256]}")
            #     else:
            #         print(f"✅ 已写入PG预测结果: {len(payload)} 条, chunk={chunk_index}")
            # except Exception as e:
            #     print(f"⚠️ 写入PG异常: {e}")
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
                'best_quantile_colname': best_quantile_colname,
                'best_quantile_colname_pct': best_quantile_colname_pct,
                'best_combined_score': best_score,
                'best_diff_pct': best_diff_pct,
                'all_quantile_metrics': quantile_metrics
            }
        )
        
    except Exception as e:
        print(f"分块 {chunk_index} 预测失败: {str(e)}")
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
                'best_quantile_colname': 'tsf',
                'best_quantile_colname_pct': 'tsf',
                'best_combined_score': float('inf'),
                'best_diff_pct': float('inf'),
                'all_quantile_metrics': {}
            }
        )

async def predict_chunked_mode_for_best(request: ChunkedPredictionRequest, tfm = None, timesfm_version = "2.0") -> ChunkedPredictionResponse:
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
                
        for i, chunk in enumerate(active_chunks):
            print(f"正在处理测试集分块 {i+1}/{len(active_chunks)}...")
            history_len = i * request.horizon_len
            if history_len > 0:
                df_train_current = pd.concat([df_train, df_test.iloc[:history_len, :]], axis=0)
            else:
                df_train_current = df_train
                
            result = predict_single_chunk_mode1(
                df_train=df_train_current,
                df_test=chunk,
                tfm=tfm,
                chunk_index=i,
                timesfm_version=timesfm_version,
                symbol=request.stock_code,
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
        
        # 分析最佳预测项 (tsf-0.1 到 tsf-0.9)
        best_prediction_item = None
        best_score = float('inf')
        best_metrics = {}
        
        prediction_items = [f"tsf-0.{i}" for i in range(1, 10)]
        
        for item in prediction_items:
            item_mse = []
            item_mae = []
            item_returns = []  # 涨跌幅
            
            for pred_data in all_predictions:
                if item in pred_data['predictions']:
                    pred_values = pred_data['predictions'][item]
                    actual_values = pred_data['actual_values']
                    
                    # 计算MSE和MAE
                    mse = mean_squared_error(actual_values, pred_values)
                    mae = mean_absolute_error(actual_values, pred_values)
                    item_mse.append(mse)
                    item_mae.append(mae)
                    
                    # 计算涨跌幅
                    if len(pred_values) >= 2 and len(actual_values) >= 2:
                        pred_return = (pred_values[-1] - pred_values[0]) / pred_values[0] * 100
                        actual_return = (actual_values[-1] - actual_values[0]) / actual_values[0] * 100
                        item_returns.append(abs(pred_return - actual_return))
            
            if item_mse:
                avg_mse = np.mean(item_mse)
                avg_mae = np.mean(item_mae)
                avg_return_diff = np.mean(item_returns) if item_returns else float('inf')
                
                # 综合评分 (MSE权重0.3, MAE权重0.3, 涨跌幅差异权重0.4)
                composite_score = 0.3 * avg_mse + 0.3 * avg_mae + 0.4 * avg_return_diff
                
                if composite_score < best_score:
                    best_score = composite_score
                    best_prediction_item = item
                    best_metrics = {
                        'mse': avg_mse,
                        'mae': avg_mae,
                        'return_diff': avg_return_diff,
                        'composite_score': composite_score
                    }
        
        print(f"🎯 最佳预测项: {best_prediction_item}")
        print(f"📊 最佳指标: MSE={best_metrics.get('mse', 'N/A'):.4f}, "
                f"MAE={best_metrics.get('mae', 'N/A'):.4f}, "
                f"涨跌幅差异={best_metrics.get('return_diff', 'N/A'):.2f}%")
        
        # 在验证集上使用最佳预测项进行验证
        validation_results = None
        if best_prediction_item and len(df_val) >= request.horizon_len:
            print(f"🔍 使用最佳预测项 {best_prediction_item} 在验证集上进行验证...")
            
            # 对验证集进行分块
            val_chunks = create_chunks_from_test_data(df_val, request.horizon_len)
            val_results = []
            
            for i, val_chunk in enumerate(val_chunks):
                # 使用与测试集相同的处理方式：随着分块数据平移
                print(f"正在处理验证集分块 {i+1}/{len(val_chunks)}...")
                history_len = i * request.horizon_len
                if history_len > 0:
                    # 使用训练集+测试集+验证集的前history_len行数据
                    cumulative_train_data = pd.concat([df_train, df_test, df_val.iloc[:history_len, :]], axis=0)
                else:
                    # 如果没有历史数据，只使用训练集+测试集
                    cumulative_train_data = pd.concat([df_train, df_test], axis=0)
                
                val_result = predict_single_chunk_mode1(
                    df_train=cumulative_train_data,  # 使用训练集+测试集+之前验证分块
                    df_test=val_chunk,
                    tfm=tfm,
                    chunk_index=i,
                    timesfm_version=timesfm_version,
                    symbol=request.stock_code,
                )
                val_results.append(val_result)
            
            # 计算验证集指标
            val_mse = []
            val_mae = []
            val_returns = []
            
            for result in val_results:
                if best_prediction_item in result.predictions:
                    pred_values = result.predictions[best_prediction_item]
                    actual_values = result.actual_values
                    
                    mse = mean_squared_error(actual_values, pred_values)
                    mae = mean_absolute_error(actual_values, pred_values)
                    val_mse.append(mse)
                    val_mae.append(mae)
                    
                    if len(pred_values) >= 2 and len(actual_values) >= 2:
                        pred_return = (pred_values[-1] - pred_values[0]) / pred_values[0] * 100
                        actual_return = (actual_values[-1] - actual_values[0]) / actual_values[0] * 100
                        val_returns.append(abs(pred_return - actual_return))
            
            validation_results = {
                'best_prediction_item': best_prediction_item,
                'validation_mse': np.mean(val_mse) if val_mse else float('inf'),
                'validation_mae': np.mean(val_mae) if val_mae else float('inf'),
                'validation_return_diff': np.mean(val_returns) if val_returns else float('inf'),
                'validation_chunks': len(val_results),
                'successful_validation_chunks': len(val_mse)
            }
            
            print(f"✅ 验证结果: MSE={validation_results['validation_mse']:.4f}, "
                  f"MAE={validation_results['validation_mae']:.4f}, "
                  f"涨跌幅差异={validation_results['validation_return_diff']:.2f}%")
        
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
        
        return ChunkedPredictionResponse(
            stock_code=request.stock_code,
            total_chunks=len(chunks),
            horizon_len=request.horizon_len,
            chunk_results=chunk_results,
            overall_metrics=overall_metrics,
            processing_time=processing_time,
            concatenated_predictions=concatenated_predictions if concatenated_predictions else None,
            concatenated_actual=concatenated_actual if concatenated_actual else None,
            concatenated_dates=concatenated_dates if concatenated_dates else None
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"分块预测失败: {str(e)} 错误行 {e.__traceback__.tb_lineno}")
        
        return ChunkedPredictionResponse(
            stock_code=request.stock_code,
            total_chunks=0,
            horizon_len=request.horizon_len,
            chunk_results=[],
            overall_metrics={'avg_mse': float('inf'), 'avg_mae': float('inf'), 'error': str(e)},
            processing_time=processing_time
        )

if __name__ == "__main__":
    import asyncio
    from timesfm_init import init_timesfm
    test_request = ChunkedPredictionRequest(
        stock_code="sh600398",
        years=10,
        horizon_len=7,
        start_date="20100101",
        end_date="20251114",
        context_len=2048,
        time_step=0,
        stock_type=1,
        chunk_num=5,
        timesfm_version="2.5",
    )
    if test_request.timesfm_version == "2.0":
        tfm = init_timesfm(horizon_len=test_request.horizon_len, context_len=test_request.context_len)
        response = asyncio.run(predict_chunked_mode_for_best(test_request, tfm, timesfm_version=test_request.timesfm_version))
    else:
        response = asyncio.run(predict_chunked_mode_for_best(test_request, tfm=None, timesfm_version=test_request.timesfm_version))
    # print(response)
    # 输出结果
    print(f"\n=== 分块预测结果 ===")
    print(f"股票代码: {response.stock_code}")
    print(f"总分块数: {response.total_chunks}")
    print(f"预测长度: {response.horizon_len}")
    print(f"处理时间: {response.processing_time:.2f} 秒")
    print(f"处理结果: {response.overall_metrics}")
    # 生成绘图
    from plot_functions import plot_chunked_prediction_results
    print(f"\n正在生成结果图表...")
    plot_save_path = os.path.join(finance_dir, f"forecast-results/{test_request.stock_code}_prediction_plot.png")
    try:
        plot_path = plot_chunked_prediction_results(response, plot_save_path)
        print(f"图表已保存到: {plot_path}")
    except Exception as plot_error:
        print(f"⚠️ 绘图失败: {str(plot_error)}")
    
    
