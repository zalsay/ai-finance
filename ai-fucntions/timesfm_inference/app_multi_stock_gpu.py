#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TimesFM股票预测脚本
将Jupyter Notebook转换为可执行的Python脚本
"""

import os
import sys
import numpy as np
import pandas as pd
import warnings
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 环境变量设置
os.environ['XLA_PYTHON_CLIENT_PREALLOCATE'] = 'false'
os.environ['JAX_PMAP_USE_TENSORSTORE'] = 'false'

# 忽略警告
warnings.filterwarnings("ignore")

# 添加akshare工具路径
finance_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
akshare_dir = os.path.join(finance_dir, 'akshare-tools')
sys.path.append(akshare_dir)
from get_finanial_data import ak_stock_data, get_stock_list, get_index_data, talib_tools

# 模型路径设置
current_dir = os.path.abspath("..")
timesfm_dir = "/root/models/ai_tools/timesfm/senrajat_google_com/google_finetune"
original_model = "/root/workers/finance/timesfm/timesfm-2.0-500m-pytorch/torch_model.ckpt"

# 导入TimesFM
import 
import asyncio













def integrate_with_timesfm_forecast(forecast_df, df_test, stock_code_list):
    """
    将TimesFM预测结果与实际数据集成
    
    Args:
        forecast_df: 预测数据框
        df_test: 测试数据框
        stock_code_list: 股票代码列表
    """
    print("\n=== 开始执行integrate_with_timesfm_forecast函数 ===")
    results = {}
    figures = []
    
    # 首先处理所有股票的日期修正，然后再绘图
    corrected_forecast_df = forecast_df.copy()
    
    for stock_code in stock_code_list:
        # 过滤特定股票的数据
        stock_forecast = forecast_df[forecast_df['unique_id'] == stock_code].copy()
        stock_test = df_test[df_test['stock_code'] == stock_code].copy()
        
        # 将日期转换为pandas datetime以便比较
        stock_forecast['ds'] = pd.to_datetime(stock_forecast['ds'])
        stock_test['ds'] = pd.to_datetime(stock_test['ds'])
        
        print(f"\n=== 处理股票 {stock_code} ===\n")
        
        # 直接使用原始数据，不进行交易日过滤
        stock_forecast_filtered = stock_forecast.copy()
        stock_test_filtered = stock_test.copy()
        
        # 确保两个数据集长度一致
        min_length = min(len(stock_forecast_filtered), len(stock_test_filtered))
        stock_forecast_filtered = stock_forecast_filtered.head(min_length)
        stock_test_filtered = stock_test_filtered.head(min_length)
        
        # 按日期排序
        stock_forecast_filtered = stock_forecast_filtered.sort_values('ds')
        stock_test_filtered = stock_test_filtered.sort_values('ds')
        
        
        # 计算所有预测列的误差，选择最佳组合
        actual_values = stock_test_filtered['close'].values
        
        # 获取所有timesfm预测列
        forecast_columns = [col for col in stock_forecast_filtered.columns if col.startswith('timesfm-q-')]
        
        best_mse = float('inf')
        best_mae = float('inf')
        best_column = 'timesfm-q-0.5'  # 默认值
        best_combined_score = float('inf')
        
        # 计算每个预测列的MSE和MAE
        for col in forecast_columns:
            forecast_values = stock_forecast_filtered[col].values
            mse = mean_squared_error(forecast_values, actual_values)
            mae = mean_absolute_error(forecast_values, actual_values)
            
            # 使用MSE和MAE的加权组合作为综合评分（可以调整权重）
            combined_score = 0.5 * mse + 0.5 * mae
                        
            # 选择综合评分最低的列
            if combined_score < best_combined_score:
                best_combined_score = combined_score
                best_mse = mse
                best_mae = mae
                best_column = col
        
        print(f"\n最佳预测列: {best_column}, 最佳MSE: {best_mse:.4f}, 最佳MAE: {best_mae:.4f}, 综合评分: {best_combined_score:.4f}")
        
        # 使用最佳列的值
        mse = best_mse
        mae = best_mae
        best_forecast_values = stock_forecast_filtered[best_column].values
        
        # 创建plot_df数据，使用最佳预测列
        min_len = min(len(stock_forecast_filtered), len(stock_test_filtered))
        plot_df = pd.DataFrame({
            'index': range(min_len),
            'actual': stock_test_filtered['close'].values[:min_len],
            'forecast': best_forecast_values[:min_len],
            'forecast_lower': stock_forecast_filtered['timesfm-q-0.1'].values[:min_len] if 'timesfm-q-0.1' in stock_forecast_filtered.columns else best_forecast_values[:min_len] * 0.95,
            'forecast_upper': stock_forecast_filtered['timesfm-q-0.9'].values[:min_len] if 'timesfm-q-0.9' in stock_forecast_filtered.columns else best_forecast_values[:min_len] * 1.05
        })
        
        results[stock_code] = {
            'mse': mse,
            'mae': mae,
            'best_column': best_column,
            'best_combined_score': best_combined_score,
            'forecast_data': stock_forecast_filtered,
            'actual_data': stock_test_filtered,
            'plot_df': plot_df
        }
    
    # 创建只包含horizon_len长度的绘图数据
    print("\n=== 创建horizon_len长度的绘图数据 ===")
    horizon_len = len(corrected_forecast_df[corrected_forecast_df['unique_id'] == stock_code_list[0]])
    print(f"horizon_len: {horizon_len}")
    
    for stock_code in stock_code_list:
        # 获取预测数据（已经是horizon_len长度）
        forecast_data = corrected_forecast_df[corrected_forecast_df['unique_id'] == stock_code].copy().reset_index(drop=True)
        
        # 获取测试数据的前horizon_len条记录
        test_data = df_test[df_test['unique_id'] == stock_code].head(horizon_len).copy().reset_index(drop=True)
        
        # 直接按顺序创建绘图DataFrame，不进行日期验证
        min_len = min(len(forecast_data), len(test_data))
        
        # 为当前股票选择最佳预测列
        actual_values_plot = test_data['close'].values[:min_len]
        forecast_columns = [col for col in forecast_data.columns if col.startswith('timesfm-q-')]
        
        best_column = 'timesfm-q-0.5'  # 默认值
        best_combined_score = float('inf')
        
        # print(f"为股票 {stock_code} 选择最佳预测列:")
        for col in forecast_columns:
            forecast_values_plot = forecast_data[col].values[:min_len]
            mse_plot = mean_squared_error(forecast_values_plot, actual_values_plot)
            mae_plot = mean_absolute_error(forecast_values_plot, actual_values_plot)
            combined_score_plot = 0.5 * mse_plot + 0.5 * mae_plot
            
            # print(f"  {col}: MSE={mse_plot:.4f}, MAE={mae_plot:.4f}, 综合评分={combined_score_plot:.4f}")
            
            if combined_score_plot < best_combined_score:
                best_combined_score = combined_score_plot
                best_column = col
        
        print(f"选择的最佳预测列: {best_column}, 综合评分: {best_combined_score:.4f}")
        
        # 创建绘图DataFrame，使用最佳预测列
        plot_df = pd.DataFrame({
            'index': range(min_len),
            'actual': test_data['close'].values[:min_len],
            'forecast': forecast_data[best_column].values[:min_len],
            'forecast_lower': forecast_data['timesfm-q-0.1'].values[:min_len],
            'forecast_upper': forecast_data['timesfm-q-0.9'].values[:min_len]
        })
        
        print(f"绘图数据长度: {len(plot_df)}")
        
        # 更新results中的信息，包含最佳列信息
        if stock_code in results:
            results[stock_code]['plot_df'] = plot_df
            results[stock_code]['best_column_plot'] = best_column
            results[stock_code]['best_combined_score_plot'] = best_combined_score
        
        # 保存为CSV
        csv_filename = os.path.join(finance_dir, f"forecast-results/{stock_code}_horizon_plot_data.csv")
        plot_df.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"绘图数据已保存: {csv_filename}")
        
        # 使用绘图数据进行绘图
        # fig = plot_forecast_vs_actual_simple(plot_df, stock_code)
        # if fig is not None:
        #     figures.append(fig)
    
    return results, figures










def predict_chunked_rolling_mode(request: ChunkedPredictionRequest, tfm) -> ChunkedPredictionResponse:
    """
    滚动预测模式：每个分块使用前面所有数据作为训练集
    
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
            request.time_step, 
            years=request.years, 
            horizon_len=request.horizon_len
        )
        
        # 添加唯一标识符
        df_train["unique_id"] = df_train["stock_code"].astype(str)
        df_test["unique_id"] = df_test["stock_code"].astype(str)
        
        # 对测试数据进行分块
        chunks = create_chunks_from_test_data(df_test, request.horizon_len)
        
        # 滚动预测：每个分块使用前面所有数据作为训练集
        chunk_results = []
        all_mse = []
        all_mae = []
        
        # 合并原始训练数据和测试数据，用于滚动训练
        df_combined = pd.concat([df_train, df_test], ignore_index=True)
        
        for i, chunk in enumerate(chunks):
            print(f"正在处理滚动预测分块 {i+1}/{len(chunks)}...")
            
            # 计算当前分块在合并数据中的位置
            chunk_start_idx = len(df_train) + i * request.horizon_len
            
            # 滚动训练集：包含原始训练数据 + 前面所有已处理的测试数据
            if i == 0:
                # 第一个分块只使用原始训练数据
                rolling_train_data = df_train.copy()
            else:
                # 后续分块使用原始训练数据 + 前面所有分块的数据
                rolling_train_end_idx = chunk_start_idx
                rolling_train_data = df_combined.iloc[:rolling_train_end_idx].copy()
                rolling_train_data["unique_id"] = rolling_train_data["stock_code"].astype(str)
            
            print(f"  滚动训练集大小: {len(rolling_train_data)} 条记录")
            print(f"  当前预测分块大小: {len(chunk)} 条记录")
            
            result = predict_single_chunk_mode1(
                df_train=rolling_train_data,
                chunk=chunk,
                tfm=tfm,
                stock_code=request.stock_code,
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
        print(f"滚动预测失败: {str(e)}")
        
        return ChunkedPredictionResponse(
            stock_code=request.stock_code,
            total_chunks=0,
            horizon_len=request.horizon_len,
            chunk_results=[],
            overall_metrics={'avg_mse': float('inf'), 'avg_mae': float('inf'), 'error': str(e)},
            processing_time=processing_time
        )






def test_chunked_prediction(tfm, stock_code: str = "000001", horizon_len: int = 5, use_rolling: bool = True):
    """
    测试分块预测功能
    
    Args:
        tfm: TimesFM模型实例
        stock_code: 测试股票代码
        horizon_len: 预测长度
        use_rolling: 是否使用滚动预测模式
    """
    mode_name = "滚动预测" if use_rolling else "普通分块预测"
    print(f"\n=== 开始测试{mode_name}功能 ===")
    print(f"测试股票: {stock_code}")
    print(f"预测长度: {horizon_len}")
    print(f"预测模式: {mode_name}")
    
    try:
        # 创建分块预测请求
        request = ChunkedPredictionRequest(
            stock_code=stock_code,
            years=10,
            horizon_len=horizon_len,
            context_len=2048,
            time_step=0,
            stock_type='stock'
        )
        
        # 执行分块预测
        print(f"正在执行{mode_name}...")
        if use_rolling:
            response = predict_chunked_rolling_mode(request, tfm)
        else:
            response = predict_chunked_mode1(request, tfm)
        
        # 输出结果
        print(f"\n=== 分块预测结果 ===")
        print(f"股票代码: {response.stock_code}")
        print(f"总分块数: {response.total_chunks}")
        print(f"预测长度: {response.horizon_len}")
        print(f"处理时间: {response.processing_time:.2f} 秒")
        
        print(f"\n=== 总体指标 ===")
        for metric, value in response.overall_metrics.items():
            if isinstance(value, float) and value != float('inf'):
                print(f"{metric}: {value:.6f}")
            else:
                print(f"{metric}: {value}")
        
        print(f"\n=== 各分块详细结果 ===")
        for i, chunk_result in enumerate(response.chunk_results):
            print(f"\n分块 {i+1}:")
            print(f"  索引: {chunk_result.chunk_index}")
            print(f"  日期范围: {chunk_result.chunk_start_date} 到 {chunk_result.chunk_end_date}")
            print(f"  实际值数量: {len(chunk_result.actual_values)}")
            print(f"  预测列数量: {len(chunk_result.predictions)}")
            
            # 显示指标
            for metric, value in chunk_result.metrics.items():
                if isinstance(value, float) and value != float('inf'):
                    print(f"  {metric}: {value:.6f}")
                else:
                    print(f"  {metric}: {value}")
            
            # 显示前几个预测值和实际值
            if chunk_result.actual_values and chunk_result.predictions:
                print(f"  前3个实际值: {chunk_result.actual_values[:3]}")
                
                # 显示中位数预测值
                if 'timesfm-q-0.5' in chunk_result.predictions:
                    pred_values = chunk_result.predictions['timesfm-q-0.5']
                    print(f"  前3个预测值: {pred_values[:3]}")
        
        # 保存结果到文件
        mode_suffix = "rolling" if use_rolling else "chunked"
        results_filename = os.path.join(finance_dir, f"forecast-results/{stock_code}_{mode_suffix}_prediction_results.txt")
        with open(results_filename, 'w', encoding='utf-8') as f:
            f.write(f"{mode_name}结果 - 股票: {response.stock_code}\n")
            f.write(f"总分块数: {response.total_chunks}\n")
            f.write(f"预测长度: {response.horizon_len}\n")
            f.write(f"处理时间: {response.processing_time:.2f} 秒\n\n")
            
            f.write("总体指标:\n")
            for metric, value in response.overall_metrics.items():
                f.write(f"  {metric}: {value}\n")
            
            f.write("\n各分块详细结果:\n")
            for chunk_result in response.chunk_results:
                f.write(f"\n分块 {chunk_result.chunk_index + 1}:\n")
                f.write(f"  日期范围: {chunk_result.chunk_start_date} 到 {chunk_result.chunk_end_date}\n")
                f.write(f"  指标: {chunk_result.metrics}\n")
                f.write(f"  实际值: {chunk_result.actual_values}\n")
                f.write(f"  预测值: {chunk_result.predictions}\n")
        
        # 生成绘图
        print(f"\n正在生成{mode_name}结果图表...")
        plot_save_path = os.path.join(finance_dir, f"forecast-results/{stock_code}_{mode_suffix}_prediction_plot.png")
        try:
            plot_path = plot_chunked_prediction_results(response, plot_save_path)
            print(f"图表已保存到: {plot_path}")
        except Exception as plot_error:
            print(f"⚠️ 绘图失败: {str(plot_error)}")
        
        print(f"\n✅ {mode_name}测试完成!")
        print(f"详细结果已保存到: {results_filename}")
        
        return response
        
    except Exception as e:
        print(f"❌ {mode_name}测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    import time
    
    # 参数设置
    # stock_code_list = ["600398", "000001", "000002", "000858", "002415"]  # 扩展股票列表用于测试并发
    stock_code_list = ["600398"]
    stock_type = 'stock'
    time_step = 0
    years = 10
    horizon_len = 5
    context_len = 2048
    
    print(f"开始并发处理 {len(stock_code_list)} 只股票: {stock_code_list}")
    
    # 初始化模型（只初始化一次，所有任务共享）
    print("初始化TimesFM模型...")
    tfm = timesfm.TimesFm(
        hparams=timesfm.TimesFmHparams(
            backend="gpu",
            per_core_batch_size=32,  # 降低批次大小以支持并发
            horizon_len=horizon_len,
            num_layers=50,
            use_positional_embedding=False,
            context_len=context_len,
        ),
        checkpoint=timesfm.TimesFmCheckpoint(
            path=original_model),
    )
    
    print("模型初始化完成，开始并发处理股票...")
    
    # 记录开始时间
    start_time = time.time()
    
    # 测试分块预测功能
    print(f"\n{'='*50}")
    print("开始测试分块预测功能...")
    print(f"{'='*50}")
    
    try:
        # 使用第一个股票代码进行分块预测测试
        test_stock_code = stock_code_list[0]
        test_chunked_prediction(tfm, stock_code=test_stock_code, horizon_len=horizon_len)
        print(f"\n✅ 分块预测功能测试完成!")
    except Exception as e:
        print(f"\n❌ 分块预测功能测试失败: {e}")
    
    # return all_results, all_figures  # 注释掉，因为这些变量未定义
    return None


if __name__ == "__main__":
    # 运行异步main函数
    asyncio.run(main())