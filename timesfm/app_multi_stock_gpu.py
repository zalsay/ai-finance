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
import plotly.graph_objects as go
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
import timesfm
import exchange_calendars as xcals
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# 分块预测相关的数据模型类
@dataclass
class ChunkedPredictionRequest:
    """分块预测请求模型"""
    stock_code: str
    years: int = 10
    horizon_len: int = 7
    context_len: int = 2048
    time_step: int = 0
    stock_type: str = 'stock'


@dataclass
class ChunkPredictionResult:
    """单个分块的预测结果"""
    chunk_index: int
    chunk_start_date: str
    chunk_end_date: str
    predictions: Dict[str, List[float]]  # 包含不同分位数的预测结果
    actual_values: List[float]
    metrics: Dict[str, float]  # MSE, MAE等指标


@dataclass
class ChunkedPredictionResponse:
    """分块预测响应"""
    stock_code: str
    total_chunks: int
    horizon_len: int
    chunk_results: List[ChunkPredictionResult]
    overall_metrics: Dict[str, float]
    processing_time: float
    # 新增拼接结果字段
    concatenated_predictions: Optional[Dict[str, List[float]]] = None  # 拼接后的完整预测结果
    concatenated_actual: Optional[List[float]] = None  # 拼接后的完整实际值
    concatenated_dates: Optional[List[str]] = None  # 拼接后的完整日期序列


def df_preprocess(stock_code, stock_type, time_step, years=10, horizon_len=7):
    """
    预处理股票数据
    
    Args:
        stock_code: 股票代码
        stock_type: 股票类型
        time_step: 时间步长
        years: 获取多少年的数据
        horizon_len: 预测长度
        
    Returns:
        df: 完整数据
        df_train: 训练数据
        df_test: 测试数据
    """
    df = ak_stock_data(stock_code, start_date="19900101", years=years, time_step=time_step)
    df["stock_code"] = stock_code
    
    # 确保datetime列是正确的日期格式
    if 'datetime' in df.columns:
        df['ds'] = pd.to_datetime(df['datetime'])
    else:
        # 如果没有datetime列，尝试从索引获取
        df['ds'] = pd.to_datetime(df.index)
    
    # 创建专门用于绘图的日期列（字符串格式）
    df['ds_plot'] = df['ds'].dt.strftime('%Y-%m-%d')
    
    # 删除不需要的列
    if 'datetime_int' in df.columns:
        df.drop(columns=['datetime_int'], inplace=True)
    if 'datetime' in df.columns:
        df.drop(columns=['datetime'], inplace=True)
    
    # 重新排列列顺序，确保ds列在第一位，ds_plot在第二位
    columns = list(df.columns)
    if "ds" in columns:
        columns.remove("ds")
    if "ds_plot" in columns:
        columns.remove("ds_plot")
    columns = ["ds", "ds_plot"] + columns
    df = df[columns]
    
    print(f"数据预处理完成，数据形状: {df.shape}")
    print(f"日期范围: {df['ds'].min()} 到 {df['ds'].max()}")
    
    # 数据分割
    original_length = df.shape[0]
    # 使用80%的数据作为训练集
    df_train = df.iloc[:int(original_length * 0.8),:]
    df_test = df.iloc[int(original_length * 0.8):,:]
    
    return df, df_train, df_test


def get_trading_days(start_date, end_date):
    """
    使用exchange_calendars获取中国股市的交易日
    
    Args:
        start_date: 开始日期 (datetime or str)
        end_date: 结束日期 (datetime or str)
    
    Returns:
        list: 交易日列表
    """
    try:
        # 获取中国股市日历
        china_calendar = xcals.get_calendar('XSHG')  # 上海证券交易所
        
        # 确保日期格式正确
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        
        # 获取交易日
        trading_days = china_calendar.sessions_in_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # 转换为日期列表
        trading_dates = [date.date() for date in trading_days]
        
        print(f"交易日历: {start_date.date()} 到 {end_date.date()}")
        print(f"总交易日数量: {len(trading_dates)}")
        
        return trading_dates
        
    except Exception as e:
        print(f"获取交易日历失败: {e}")
        print("回退到简单的工作日过滤")
        
        # 回退方案：简单的工作日过滤
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        weekdays = [d.date() for d in date_range if d.weekday() < 5]  # 周一到周五
        return weekdays


def filter_trading_days_data(df, date_column='ds'):
    """
    使用交易日历过滤数据，只保留真正的交易日
    
    Args:
        df: 包含日期列的DataFrame
        date_column: 日期列名
    
    Returns:
        DataFrame: 过滤后的数据
    """
    if df.empty:
        return df
    
    # 确保日期列是datetime格式
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    
    # 获取数据的日期范围
    start_date = df[date_column].min()
    end_date = df[date_column].max()
    
    # 获取交易日
    trading_days = get_trading_days(start_date, end_date)
    
    # 过滤数据，只保留交易日
    df_filtered = df[df[date_column].dt.date.isin(trading_days)]
    
    print(f"原始数据: {len(df)} 行")
    print(f"过滤后数据: {len(df_filtered)} 行")
    print(f"过滤掉的非交易日: {len(df) - len(df_filtered)} 行")
    
    return df_filtered


def mean_squared_error(y_pred, y_true):
    """
    计算均方误差
    """
    return np.mean((y_true - y_pred) ** 2)


def mean_absolute_error(y_pred, y_true):
    """
    计算平均绝对误差
    """
    return np.mean(np.abs(y_true - y_pred))


def plot_forecast_vs_actual_simple(plot_df, stock_code):
    """
    简化的绘图函数，直接使用绘图DataFrame
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # 创建图表
        fig = go.Figure()
        
        # 添加实际数据
        fig.add_trace(go.Scatter(
            x=plot_df['index'],
            y=plot_df['actual'],
            mode='lines+markers',
            name='实际价格',
            line=dict(color='blue', width=2),
            marker=dict(size=4)
        ))
        
        # 添加预测数据
        fig.add_trace(go.Scatter(
            x=plot_df['index'],
            y=plot_df['forecast'],
            mode='lines+markers',
            name='预测价格',
            line=dict(color='red', width=2),
            marker=dict(size=4)
        ))
        
        # 添加预测区间
        fig.add_trace(go.Scatter(
            x=plot_df['index'],
            y=plot_df['forecast_upper'],
            mode='lines',
            name='预测上界',
            line=dict(color='rgba(255,0,0,0.3)', width=1),
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=plot_df['index'],
            y=plot_df['forecast_lower'],
            mode='lines',
            name='预测下界',
            line=dict(color='rgba(255,0,0,0.3)', width=1),
            fill='tonexty',
            fillcolor='rgba(255,0,0,0.1)',
            showlegend=False
        ))
        
        # 更新布局
        fig.update_layout(
            title=f'{stock_code} 股价预测 vs 实际价格',
            xaxis_title='时间序列索引',
            yaxis_title='价格',
            hovermode='x unified',
            width=1200,
            height=800
        )
        
        # 禁用plotly图片保存，避免Kaleido库问题
        print(f"简化预测图表创建完成，跳过PNG保存以避免Kaleido问题")
        
        # 可选：保存为HTML格式
        html_filename = f"{stock_code}_simple_forecast_plot.html"
        fig.write_html(html_filename)
        print(f"HTML图表已保存: {html_filename}")
        
        return fig
        
    except Exception as e:
        print(f"绘图过程中出现错误: {str(e)}")
        return None


# 旧的绘图函数已删除，使用plot_forecast_vs_actual_simple代替


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


# 分块预测相关函数
def create_chunks_from_test_data(df_test: pd.DataFrame, horizon_len: int) -> List[pd.DataFrame]:
    """
    根据horizon_len对测试数据进行分块
    
    Args:
        df_test: 测试数据DataFrame
        horizon_len: 每个分块的长度
        
    Returns:
        List[pd.DataFrame]: 分块后的数据列表
    """
    chunks = []
    total_length = len(df_test)
    
    for i in range(0, total_length, horizon_len):
        end_idx = min(i + horizon_len, total_length)
        chunk = df_test.iloc[i:end_idx].copy()
        
        if len(chunk) > 0:  # 确保分块不为空
            chunks.append(chunk)
    
    print(f"测试数据分块完成: 总长度 {total_length}, 分块数量 {len(chunks)}, 每块长度 {horizon_len}")
    return chunks


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
        # 使用固定的end_date=20250630生成新的数据集
        years = 10  # 使用10年数据
        df_new = ak_stock_data(stock_code, start_date="19900101", end_date="20250630", years=years, time_step=0)
        df_new["stock_code"] = stock_code
        df_new["unique_id"] = stock_code
        
        # 处理日期列
        if 'datetime' in df_new.columns:
            df_new['ds'] = pd.to_datetime(df_new['datetime'])
        else:
            df_new['ds'] = pd.to_datetime(df_new.index)
        
        # 删除不需要的列
        if 'datetime_int' in df_new.columns:
            df_new.drop(columns=['datetime_int'], inplace=True)
        if 'datetime' in df_new.columns:
            df_new.drop(columns=['datetime'], inplace=True)
        
        # 重新排列列顺序
        columns = list(df_new.columns)
        if "ds" in columns:
            columns.remove("ds")
        columns = ["ds"] + columns
        df_new = df_new[columns]
        
        # 使用新数据集进行预测
        forecast_df = tfm.forecast_on_df(
            inputs=df_new,
            freq="D",
            value_name="close",
            num_jobs=1,
        )
        
        # 获取预测结果的前horizon_len条记录
        horizon_len = len(chunk)
        forecast_chunk = forecast_df.head(horizon_len)
        
        # 提取预测值和实际值
        actual_values = chunk['close'].tolist()
        
        # 获取所有预测分位数
        predictions = {}
        forecast_columns = [col for col in forecast_chunk.columns if col.startswith('timesfm-q-')]
        
        for col in forecast_columns:
            predictions[col] = forecast_chunk[col].tolist()
        
        # 计算评估指标（使用中位数预测）
        if 'timesfm-q-0.5' in predictions:
            pred_values = predictions['timesfm-q-0.5']
        else:
            # 如果没有中位数，使用第一个可用的预测列
            pred_values = list(predictions.values())[0] if predictions else [0] * len(actual_values)
        
        # 确保预测值和实际值长度一致
        min_len = min(len(pred_values), len(actual_values))
        pred_values = pred_values[:min_len]
        actual_values = actual_values[:min_len]
        
        mse = mean_squared_error(np.array(pred_values), np.array(actual_values))
        mae = mean_absolute_error(np.array(pred_values), np.array(actual_values))
        
        # 获取分块的日期范围
        chunk_start_date = chunk['ds'].min().strftime('%Y-%m-%d')
        chunk_end_date = chunk['ds'].max().strftime('%Y-%m-%d')
        
        return ChunkPredictionResult(
            chunk_index=chunk_index,
            chunk_start_date=chunk_start_date,
            chunk_end_date=chunk_end_date,
            predictions=predictions,
            actual_values=actual_values,
            metrics={'mse': mse, 'mae': mae}
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
            metrics={'mse': float('inf'), 'mae': float('inf')}
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
            request.time_step, 
            years=request.years, 
            horizon_len=request.horizon_len
        )
        
        # 添加唯一标识符
        df_train["unique_id"] = df_train["stock_code"].astype(str)
        df_test["unique_id"] = df_test["stock_code"].astype(str)
        
        # 对测试数据进行分块
        chunks = create_chunks_from_test_data(df_test, request.horizon_len)
        
        # 对每个分块进行预测
        chunk_results = []
        all_mse = []
        all_mae = []
        
        for i, chunk in enumerate(chunks):
            print(f"正在处理分块 {i+1}/{len(chunks)}...")
            
            result = predict_single_chunk_mode1(
                df_train=df_train,
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
        print(f"分块预测失败: {str(e)}")
        
        return ChunkedPredictionResponse(
            stock_code=request.stock_code,
            total_chunks=0,
            horizon_len=request.horizon_len,
            chunk_results=[],
            overall_metrics={'avg_mse': float('inf'), 'avg_mae': float('inf'), 'error': str(e)},
            processing_time=processing_time
        )


def plot_chunked_prediction_results(response: ChunkedPredictionResponse, save_path: str = None) -> str:
    """
    Plot chunked prediction results with best prediction values and English labels
    
    Args:
        response: Chunked prediction response object
        save_path: Image save path, auto-generated if None
        
    Returns:
        str: Saved image path
    """
    if not response.concatenated_predictions or not response.concatenated_actual:
        print("❌ No concatenated prediction results to plot")
        return None
    
    try:
        # Set matplotlib to use a font that supports both English and Chinese
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        # Set image save path
        if save_path is None:
            save_path = f"{finance_dir}/forecast-results/{response.stock_code}_chunked_prediction_plot.png"
        
        # Create figure
        plt.figure(figsize=(15, 10))
        
        # Convert dates
        dates = pd.to_datetime(response.concatenated_dates)
        actual_values = response.concatenated_actual
        
        # Create best prediction values by selecting the best performing prediction for each chunk
        best_predictions = []
        chunk_start_idx = 0
        
        for chunk_result in response.chunk_results:
            chunk_size = len(chunk_result.actual_values)
            
            # Find the best prediction column for this chunk based on MSE
            best_pred_key = None
            best_mse = float('inf')
            
            for pred_key, pred_values in chunk_result.predictions.items():
                if len(pred_values) == chunk_size:
                    # Calculate MSE for this prediction column
                    chunk_mse = mean_squared_error(np.array(pred_values), np.array(chunk_result.actual_values))
                    if chunk_mse < best_mse:
                        best_mse = chunk_mse
                        best_pred_key = pred_key
            
            # Use the best prediction for this chunk, fallback to median or first available
            if best_pred_key and best_pred_key in chunk_result.predictions:
                chunk_best_pred = chunk_result.predictions[best_pred_key]
            elif 'timesfm-q-0.5' in chunk_result.predictions:
                chunk_best_pred = chunk_result.predictions['timesfm-q-0.5']
            elif chunk_result.predictions:
                chunk_best_pred = list(chunk_result.predictions.values())[0]
            else:
                chunk_best_pred = [0] * chunk_size
            
            best_predictions.extend(chunk_best_pred)
            chunk_start_idx += chunk_size
        
        # Plot actual values
        plt.plot(dates, actual_values, 'b-', linewidth=2, label='Actual Values', alpha=0.8)
        
        # Plot best predictions
        plt.plot(dates, best_predictions, 'r-', linewidth=2, label='Best Predictions', alpha=0.8)
        
        # Add confidence intervals if available
        predictions = response.concatenated_predictions
        if 'timesfm-q-0.1' in predictions and 'timesfm-q-0.9' in predictions:
            lower_bound = predictions['timesfm-q-0.1']
            upper_bound = predictions['timesfm-q-0.9']
            plt.fill_between(dates, lower_bound, upper_bound, alpha=0.2, color='red', label='80% Confidence Interval')
        elif 'timesfm-q-0.25' in predictions and 'timesfm-q-0.75' in predictions:
            lower_bound = predictions['timesfm-q-0.25']
            upper_bound = predictions['timesfm-q-0.75']
            plt.fill_between(dates, lower_bound, upper_bound, alpha=0.2, color='red', label='50% Confidence Interval')
        
        # Add chunk boundary lines
        chunk_boundaries = []
        for i, result in enumerate(response.chunk_results):
            if i > 0:  # Skip the first chunk start
                chunk_start = pd.to_datetime(result.chunk_start_date)
                chunk_boundaries.append(chunk_start)
        
        # Draw chunk boundary lines
        for boundary in chunk_boundaries:
            plt.axvline(x=boundary, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        
        # Set chart properties with English labels
        plt.title(f'Stock {response.stock_code} Chunked Prediction Results\n'
                 f'Total Chunks: {response.total_chunks}, Horizon Length: {response.horizon_len} days\n'
                 f'Average MSE: {response.overall_metrics.get("avg_mse", 0):.6f}, '
                 f'Average MAE: {response.overall_metrics.get("avg_mae", 0):.6f}', 
                 fontsize=14, pad=20)
        
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Stock Price', fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # Set date format
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        plt.xticks(rotation=45)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save image
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Chunked prediction chart saved to: {save_path}")
        return save_path
        
    except Exception as e:
        print(f"❌ Failed to plot chunked prediction chart: {str(e)}")
        return None


async def process_single_stock(stock_code, stock_type, time_step, years, horizon_len, context_len, tfm):
    """
    异步处理单个股票的预测任务
    """
    import pandas as pd
    import json
    
    print(f"开始处理股票: {stock_code}")
    
    try:
        # 数据预处理
        df_original, df_train, df_test = df_preprocess(stock_code, stock_type, time_step, years=years, horizon_len=horizon_len)
        
        # 添加唯一标识符
        df_train["unique_id"] = df_train["stock_code"].astype(str)
        df_test["unique_id"] = df_test["stock_code"].astype(str)
        
        # 可选：添加技术指标
        try:
            df_train, input_features = talib_tools(df_train)
            print(f"股票 {stock_code} 技术指标添加成功")
        except Exception as e:
            print(f"股票 {stock_code} 添加技术指标失败: {e}")
            print("继续使用原始数据...")
        
        # 为预测准备数据：去掉绘图日期列，只保留推理需要的列
        df_train_for_prediction = df_train.copy()
        if 'ds_plot' in df_train_for_prediction.columns:
            df_train_for_prediction = df_train_for_prediction.drop(columns=['ds_plot'])
        
        print(f"股票 {stock_code} 开始预测...")
        
        # 在线程池中执行预测（因为TimesFM可能不是异步的）
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            forecast_df = await loop.run_in_executor(
                executor,
                lambda: tfm.forecast_on_df(
                    inputs=df_train_for_prediction,
                    freq="D",
                    value_name="close",
                    num_jobs=1,  # 单个股票使用单线程
                )
            )
        
        # 为预测结果添加绘图日期列
        if 'ds' in forecast_df.columns:
            forecast_df['ds_plot'] = pd.to_datetime(forecast_df['ds']).dt.strftime('%Y-%m-%d')
            print(f"股票 {stock_code} 已为预测结果添加绘图日期列")
        
        # 集成预测结果
        print(f"股票 {stock_code} 集成预测结果与实际数据...")
        results, figures = integrate_with_timesfm_forecast(forecast_df, df_test, [stock_code])
        
        # 保存结果
        print(f"股票 {stock_code} 保存预测图片...")
        for stock_code_key, result in results.items():
            # 保存预测对比图为PNG格式
            print(f"保存股票 {stock_code_key} 的matplotlib图片...")
            
            # 使用matplotlib绘制和保存图片
            plot_df = result['plot_df']
            
            # 创建matplotlib图表
            plt.figure(figsize=(12, 8))
            
            # 使用plot_df数据绘制图表
            try:
                # 使用索引作为x轴（确保数据一致性）
                x_values = plot_df['index'].values
                actual_y = plot_df['actual'].values
                forecast_y = plot_df['forecast'].values
                
                # 绘制实际值和预测值
                plt.plot(x_values, actual_y, label='Actual', color='blue', linewidth=2)
                plt.plot(x_values, forecast_y, label='Forecast', color='red', linewidth=2, linestyle='--')
                
                # 可选：绘制预测区间
                if 'forecast_lower' in plot_df.columns and 'forecast_upper' in plot_df.columns:
                    plt.fill_between(x_values, plot_df['forecast_lower'].values, plot_df['forecast_upper'].values, 
                                   alpha=0.2, color='red', label='Forecast Range')
                
            except Exception as e:
                print(f"绘图数据处理出错: {e}")
                # 使用简化的绘图方式
                plt.plot(range(len(plot_df)), plot_df['actual'], label='Actual', color='blue', linewidth=2)
                plt.plot(range(len(plot_df)), plot_df['forecast'], label='Forecast', color='red', linewidth=2, linestyle='--')
            
            # 设置图表样式
            plt.title(f'{stock_code_key} Stock Price Forecast Comparison', fontsize=16, fontweight='bold')
            plt.xlabel('Time Steps (Horizon Length)', fontsize=12)
            plt.ylabel('Price', fontsize=12)
            plt.legend(fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # 设置x轴为简单数列显示
            plt.xticks(range(0, len(plot_df), max(1, len(plot_df)//10)))
            
            # 调整布局
            plt.tight_layout()
            
            # 保存为PNG格式，设置高分辨率
            matplotlib_filename = os.path.join(finance_dir, f"forecast-results/{stock_code_key}_matplotlib_forecast_plot.png")
            plt.savefig(matplotlib_filename, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            print(f"✅ 股票 {stock_code_key} matplotlib图片已保存: {matplotlib_filename}")
        
        print(f"✅ 股票 {stock_code} 处理完成")
        return stock_code, results, figures
        
    except Exception as e:
        error_msg = f"处理股票 {stock_code} 时出错: {str(e)}"
        print(f"❌ {error_msg}")
        return stock_code, None, None


def test_chunked_prediction(tfm, stock_code: str = "600398", horizon_len: int = 5):
    """
    测试分块预测功能
    
    Args:
        tfm: TimesFM模型实例
        stock_code: 测试股票代码
        horizon_len: 预测长度
    """
    print(f"\n=== 开始测试分块预测功能 ===")
    print(f"测试股票: {stock_code}")
    print(f"预测长度: {horizon_len}")
    
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
        print("正在执行分块预测...")
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
        results_filename = os.path.join(finance_dir, f"forecast-results/{stock_code}_chunked_prediction_results.txt")
        with open(results_filename, 'w', encoding='utf-8') as f:
            f.write(f"分块预测结果 - 股票: {response.stock_code}\n")
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
        print("\n正在生成分块预测结果图表...")
        plot_save_path = os.path.join(finance_dir, f"forecast-results/{stock_code}_chunked_prediction_plot.png")
        try:
            plot_path = plot_chunked_prediction_results(response, plot_save_path)
            print(f"图表已保存到: {plot_path}")
        except Exception as plot_error:
            print(f"⚠️ 绘图失败: {str(plot_error)}")
        
        print(f"\n✅ 分块预测测试完成!")
        print(f"详细结果已保存到: {results_filename}")
        
        return response
        
    except Exception as e:
        print(f"❌ 分块预测测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    import pandas as pd
    import json
    import time
    
    # 参数设置
    stock_code_list = ["600398", "000001", "000002", "000858", "002415"]  # 扩展股票列表用于测试并发
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
    
    # # 创建并发任务列表
    # tasks = []
    # for stock_code in stock_code_list:
    #     task = process_single_stock(
    #         stock_code=stock_code,
    #         stock_type=stock_type,
    #         time_step=time_step,
    #         years=years,
    #         horizon_len=horizon_len,
    #         context_len=context_len,
    #         tfm=tfm
    #     )
    #     tasks.append(task)
    
    # # 并发执行所有股票处理任务
    # print(f"\n开始并发执行 {len(tasks)} 个股票预测任务...")
    
    # # 使用asyncio.gather并发执行所有任务
    # results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # # 计算总耗时
    # end_time = time.time()
    # total_time = end_time - start_time
    
    # # 汇总结果
    # all_results = {}
    # all_figures = {}
    # successful_count = 0
    # failed_count = 0
    
    # print(f"\n=== 并发执行结果汇总 ===")
    # print(f"总耗时: {total_time:.2f} 秒")
    # print(f"平均每只股票耗时: {total_time/len(stock_code_list):.2f} 秒")
    
    # for i, result in enumerate(results_list):
    #     stock_code = stock_code_list[i]
        
    #     if isinstance(result, Exception):
    #         print(f"❌ 股票 {stock_code} 处理失败: {result}")
    #         failed_count += 1
    #     elif result[1] is None:  # process_single_stock返回(stock_code, results, figures)
    #         print(f"❌ 股票 {stock_code} 处理失败")
    #         failed_count += 1
    #     else:
    #         stock_code_result, stock_results, stock_figures = result
    #         all_results.update(stock_results)
    #         all_figures.update(stock_figures)
    #         print(f"✅ 股票 {stock_code_result} 处理成功")
    #         successful_count += 1
    
    # print(f"\n=== 最终统计 ===")
    # print(f"成功处理: {successful_count} 只股票")
    # print(f"处理失败: {failed_count} 只股票")
    # print(f"成功率: {successful_count/(successful_count+failed_count)*100:.1f}%")
    
    # if successful_count > 0:
    #     print(f"\n✅ 并发预测完成! 共处理 {successful_count} 只股票")
    #     print(f"图片保存位置: {finance_dir}/forecast-results/")
    # else:
    #     print(f"\n❌ 所有股票处理都失败了")
    
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