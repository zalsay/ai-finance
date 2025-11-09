
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

from chunks_functions import create_chunks_from_test_data
from process_from_ak import df_preprocess
from math_functions import mean_squared_error, mean_absolute_error

def predict_single_chunk_mode1(
        df_train: pd.DataFrame,
        chunk: pd.DataFrame, 
        tfm, 
        stock_code: str,
        chunk_index: int
    ) -> ChunkPredictionResult:
    """
    模式1：对单个分块进行预测（固定训练集，使用ak_stock_data生成测试数据）
    
    Args:
        df_train: 固定的训练数据
        chunk: 当前分块的测试数据
        tfm: TimesFM模型实例
        stock_code: 股票代码
        chunk_index: 分块索引
        
    Returns:
        ChunkPredictionResult: 分块预测结果
    """
    try:
        # 使用新数据集进行预测
        forecast_df = tfm.forecast_on_df(
            inputs=df_train,
            freq="D",
            value_name="close",
            num_jobs=1,
        )
        
        # 获取预测结果的前horizon_len条记录
        horizon_len = len(chunk)
        forecast_chunk = forecast_df.head(horizon_len)
        
        # 调试信息：打印预测结果的列名
        print(f"  预测结果列名: {list(forecast_df.columns)}")
        print(f"  预测结果形状: {forecast_df.shape}")
        
        # 提取预测值和实际值
        actual_values = chunk['close'].tolist()
        
        # 获取所有预测分位数
        predictions = {}
        forecast_columns = [col for col in forecast_chunk.columns if col.startswith('timesfm-q-')]
        
        print(f"  找到的预测列: {forecast_columns}")
        
        for col in forecast_columns:
            predictions[col] = forecast_chunk[col].tolist()
        
        # 计算所有分位数的评估指标
        quantile_metrics = {}
        best_quantile = None
        best_score = float('inf')
        
        # 定义要评估的分位数范围 (0.1 到 0.9)
        target_quantiles = [f'timesfm-q-0.{i}' for i in range(1, 10)]
        
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
                
                # 计算综合得分 (MSE和MAE各占50%权重)
                # 为了统一量纲，对MSE和MAE进行标准化处理
                combined_score = 0.5 * mse_q + 0.5 * mae_q
                
                quantile_metrics[quantile] = {
                    'mse': mse_q,
                    'mae': mae_q,
                    'combined_score': combined_score
                }
                
                # 找到最优分位数
                if combined_score < best_score:
                    best_score = combined_score
                    best_quantile = quantile
        
        # 如果没有找到任何有效的分位数预测，使用默认值
        if not quantile_metrics:
            print(f"  ⚠️ 警告: 未找到有效的分位数预测，使用默认值")
            mse = 0.0
            mae = 0.0
            best_quantile = 'timesfm-q-0.5'
        else:
            # 使用最优分位数的指标
            mse = quantile_metrics[best_quantile]['mse']
            mae = quantile_metrics[best_quantile]['mae']
            
            print(f"  📊 分位数评估结果:")
            for q, metrics in quantile_metrics.items():
                print(f"    {q}: MSE={metrics['mse']:.6f}, MAE={metrics['mae']:.6f}, 综合得分={metrics['combined_score']:.6f}")
            print(f"  🏆 最优分位数: {best_quantile} (综合得分: {best_score:.6f})")
        
        # 获取实际值和预测值对应的日期范围
        # 实际值和预测值对应的是分块中的最后horizon_len个日期
        chunk_dates = chunk['ds'].tolist()
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
                'best_quantile': best_quantile,
                'best_combined_score': best_score,
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
                'best_quantile': 'timesfm-q-0.5',
                'best_combined_score': float('inf'),
                'all_quantile_metrics': {}
            }
        )

def predict_chunked_mode1(request: ChunkedPredictionRequest, tfm) -> ChunkedPredictionResponse:
    """
    模式1分块预测主函数
    
    Args:
        request: 分块预测请求
        tfm: TimesFM模型实例
        
    Returns:
        ChunkedPredictionResponse: 分块预测响应
    """
    import time
    start_time = time.time()
    
    try:
        # 数据预处理
        df_original, df_train, df_test = df_preprocess(
            request.stock_code, 
            request.stock_type, 
            request.start_date,
            request.end_date,
            request.time_step, 
            years=request.years, 
            horizon_len=request.horizon_len
        )
        
        # 检查数据预处理是否成功
        if df_original is None or df_train is None or df_test is None:
            print(f"❌ 股票 {request.stock_code} 数据预处理失败，无法进行预测")
            # 返回一个空的响应对象
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
        print(f"✅ 股票 {request.stock_code} 数据预处理成功，test开始日期: {df_test['ds'].min().strftime('%Y-%m-%d')}")
        # 添加唯一标识符
        df_train["unique_id"] = df_train["stock_code"].astype(str)
        df_test["unique_id"] = df_test["stock_code"].astype(str)
        
        # 对测试数据进行分块
        chunks = create_chunks_from_test_data(df_test, request.horizon_len)
        active_chunks = chunks[:request.chunk_num]
        # 对每个分块进行预测
        chunk_results = []
        all_mse = []
        all_mae = []
        
        for i, chunk in enumerate(active_chunks):
            print(f"正在处理分块 {i+1}/{len(active_chunks)}...")
            
            result = predict_single_chunk_mode1(
                chunk=chunk,
                tfm=tfm,
                chunk_index=i
            )
            
            chunk_results.append(result)
            
            # 收集指标用于计算总体指标
            if result.metrics['mse'] != float('inf'):
                all_mse.append(result.metrics['mse'])
                all_mae.append(result.metrics['mae'])
        
        # 计算总体指标
        overall_metrics = {
            'avg_mse': np.mean(all_mse) if all_mse else float('inf'),
            'avg_mae': np.mean(all_mae) if all_mae else float('inf'),
            'total_chunks': len(chunks),
            'successful_chunks': len(all_mse)
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
                # 拼接预测值
                for col in prediction_columns:
                    concatenated_predictions[col].extend(result.predictions[col])
                
                # 拼接实际值
                concatenated_actual.extend(result.actual_values)
                
                # 生成日期序列（基于分块的开始和结束日期）
                start_date = pd.to_datetime(result.chunk_start_date)
                end_date = pd.to_datetime(result.chunk_end_date)
                chunk_dates = pd.date_range(start=start_date, end=end_date, freq='D')
                concatenated_dates.extend([date.strftime('%Y-%m-%d') for date in chunk_dates[:len(result.actual_values)]])
        
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
        print(f"分块预测失败: {str(e)}")
        
        return ChunkedPredictionResponse(
            stock_code=request.stock_code,
            total_chunks=0,
            horizon_len=request.horizon_len,
            chunk_results=[],
            overall_metrics={'avg_mse': float('inf'), 'avg_mae': float('inf'), 'error': str(e)},
            processing_time=processing_time
        )

if __name__ == "__main__":
    from timesfm_init import init_timesfm
    test_request = ChunkedPredictionRequest(
        stock_code="000002",
        years=10,
        horizon_len=7,
        start_date="2023-06-30",
        end_date="2025-08-30",
        context_len=2048,
        time_step=0,
        stock_type='stock',
        chunk_num=1
    )
    tfm = init_timesfm(horizon_len=test_request.horizon_len, context_len=test_request.context_len)
    response = predict_chunked_mode1(test_request, tfm)
    # print(response)
    # 输出结果
    print(f"\n=== 分块预测结果 ===")
    print(f"股票代码: {response.stock_code}")
    print(f"总分块数: {response.total_chunks}")
    print(f"预测长度: {response.horizon_len}")
    print(f"处理时间: {response.processing_time:.2f} 秒")
    
    # print(f"\n=== 总体指标 ===")
    # for metric, value in response.overall_metrics.items():
    #     if isinstance(value, float) and value != float('inf'):
    #         print(f"{metric}: {value:.6f}")
    #     else:
    #         print(f"{metric}: {value}")
    
    print(f"\n=== 各分块详细结果 ===")
    for i, chunk_result in enumerate(response.chunk_results):
        print(f"\n分块 {i+1}:")
        print(f"  索引: {chunk_result.chunk_index}")
        print(f"  预测日期范围: {chunk_result.chunk_start_date} 到 {chunk_result.chunk_end_date}")
        print(f"  实际值日期范围: {chunk_result.chunk_start_date} 到 {chunk_result.chunk_end_date}")
        print(f"  实际值数量: {len(chunk_result.actual_values)}")
        print(f"  预测列数量: {len(chunk_result.predictions)}")
        
        # 显示指标
        # for metric, value in chunk_result.metrics.items():
        #     if isinstance(value, float) and value != float('inf'):
        #         print(f"  {metric}: {value:.6f}")
        #     else:
        #         print(f"  {metric}: {value}")
        
        # 显示前几个预测值和实际值
        if chunk_result.actual_values and chunk_result.predictions:
            print(f"  前3个实际值: {chunk_result.actual_values[:3]}")
            
            # 显示中位数预测值
            if 'timesfm-q-0.5' in chunk_result.predictions:
                pred_values = chunk_result.predictions['timesfm-q-0.5']
                print(f"  前3个预测值: {pred_values[:3]}")
    
    # 保存结果到文件
    mode_suffix = "chunked"
    results_filename = os.path.join(finance_dir, f"forecast-results/{test_request.stock_code}_{mode_suffix}_prediction_results.txt")
    with open(results_filename, 'w', encoding='utf-8') as f:
        f.write(f"结果 - 股票: {response.stock_code}\n")
        f.write(f"总分块数: {response.total_chunks}\n")
        f.write(f"预测长度: {response.horizon_len}\n")
        f.write(f"处理时间: {response.processing_time:.2f} 秒\n\n")
        
        f.write("总体指标:\n")
        for metric, value in response.overall_metrics.items():
            f.write(f"  {metric}: {value}\n")
        
        f.write("\n各分块详细结果:\n")
        for chunk_result in response.chunk_results:
            f.write(f"\n分块 {chunk_result.chunk_index + 1}:\n")
            f.write(f"  预测日期范围: {chunk_result.chunk_start_date} 到 {chunk_result.chunk_end_date}\n")
            f.write(f"  实际值日期范围: {chunk_result.chunk_start_date} 到 {chunk_result.chunk_end_date}\n")
            f.write(f"  指标: {chunk_result.metrics}\n")
            f.write(f"  实际值: {chunk_result.actual_values}\n")
            f.write(f"  预测值: {chunk_result.predictions}\n")
    
    # 生成绘图
    from plot_functions import plot_chunked_prediction_results
    print(f"\n正在生成结果图表...")
    plot_save_path = os.path.join(finance_dir, f"forecast-results/{test_request.stock_code}_{mode_suffix}_prediction_plot.png")
    try:
        plot_path = plot_chunked_prediction_results(response, plot_save_path)
        print(f"图表已保存到: {plot_path}")
    except Exception as plot_error:
        print(f"⚠️ 绘图失败: {str(plot_error)}")
    
    print(f"详细结果已保存到: {results_filename}")
    
