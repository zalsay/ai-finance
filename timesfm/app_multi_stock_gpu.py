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
akshare_dir = os.path.join(os.path.dirname(os.getcwd()), 'akshare-tools')
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
    print(df.head(1))
    
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


def integrate_with_timesfm_forecast(forecast_df, df_test, stock_code_list, df_train=None):
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
        
        print(f"\n=== 处理股票 {stock_code} ===\n交易日过滤已禁用，直接使用原始数据")
        
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
        
        print(f"预测数据长度: {len(stock_forecast_filtered)}")
        print(f"实际数据长度: {len(stock_test_filtered)}")
        
        # 计算所有预测列的误差，选择最佳组合
        actual_values = stock_test_filtered['close'].values
        
        # 获取所有timesfm预测列
        forecast_columns = [col for col in stock_forecast_filtered.columns if col.startswith('timesfm-q-')]
        print(f"可用的预测列: {forecast_columns}")
        
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
            
            print(f"列 {col}: MSE={mse:.4f}, MAE={mae:.4f}, 综合评分={combined_score:.4f}")
            
            # 选择综合评分最低的列
            if combined_score < best_combined_score:
                best_combined_score = combined_score
                best_mse = mse
                best_mae = mae
                best_column = col
        
        print(f"\n最佳预测列: {best_column}")
        print(f"最佳MSE: {best_mse:.4f}")
        print(f"最佳MAE: {best_mae:.4f}")
        print(f"最佳综合评分: {best_combined_score:.4f}")
        
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
        
        print(f"\n股票 {stock_code}:")
        print(f"预测数据长度: {len(forecast_data)}")
        print(f"测试数据长度: {len(test_data)}")
        
        # 直接按顺序创建绘图DataFrame，不进行日期验证
        min_len = min(len(forecast_data), len(test_data))
        
        # 为当前股票选择最佳预测列
        actual_values_plot = test_data['close'].values[:min_len]
        forecast_columns = [col for col in forecast_data.columns if col.startswith('timesfm-q-')]
        
        best_column = 'timesfm-q-0.5'  # 默认值
        best_combined_score = float('inf')
        
        print(f"为股票 {stock_code} 选择最佳预测列:")
        for col in forecast_columns:
            forecast_values_plot = forecast_data[col].values[:min_len]
            mse_plot = mean_squared_error(forecast_values_plot, actual_values_plot)
            mae_plot = mean_absolute_error(forecast_values_plot, actual_values_plot)
            combined_score_plot = 0.5 * mse_plot + 0.5 * mae_plot
            
            print(f"  {col}: MSE={mse_plot:.4f}, MAE={mae_plot:.4f}, 综合评分={combined_score_plot:.4f}")
            
            if combined_score_plot < best_combined_score:
                best_combined_score = combined_score_plot
                best_column = col
        
        print(f"选择的最佳预测列: {best_column}")
        
        # 创建绘图DataFrame，使用最佳预测列
        plot_df = pd.DataFrame({
            'index': range(min_len),
            'actual': test_data['close'].values[:min_len],
            'forecast': forecast_data[best_column].values[:min_len],
            'forecast_lower': forecast_data['timesfm-q-0.1'].values[:min_len],
            'forecast_upper': forecast_data['timesfm-q-0.9'].values[:min_len]
        })
        
        print(f"绘图数据长度: {len(plot_df)}")
        print(f"实际数据前5个值: {plot_df['actual'].head().tolist()}")
        print(f"预测数据前5个值: {plot_df['forecast'].head().tolist()}")
        
        # 更新results中的信息，包含最佳列信息
        if stock_code in results:
            results[stock_code]['plot_df'] = plot_df
            results[stock_code]['best_column_plot'] = best_column
            results[stock_code]['best_combined_score_plot'] = best_combined_score
        
        # 保存为CSV
        csv_filename = f"{stock_code}_horizon_plot_data.csv"
        plot_df.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"绘图数据已保存: {csv_filename}")
        print(f"使用的最佳预测列: {best_column}")
        print(f"最佳综合评分: {best_combined_score:.4f}")
        
        # 使用绘图数据进行绘图
        # fig = plot_forecast_vs_actual_simple(plot_df, stock_code)
        # if fig is not None:
        #     figures.append(fig)
    
    return results, figures


def main():
    import pandas as pd
    import json
    from datetime import datetime
    
    # debug_info相关代码已删除
    
    # 参数设置
    stock_code_list = ["600398"]
    stock_type = 'stock'
    time_step = 0
    years = 10
    horizon_len = 15
    context_len = 2048
    
    # 数据准备
    df_original, df_train, df_test = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    for stock_code in stock_code_list:
        try:
            df_original0, df_train0, df_test0 = df_preprocess(stock_code, stock_type, time_step, years=years, horizon_len=horizon_len)
            
            # debug_info数据处理记录已删除
            
            df_original = pd.concat([df_original, df_original0])
            df_train = pd.concat([df_train, df_train0])
            df_test = pd.concat([df_test, df_test0])
            
        except Exception as e:
            error_msg = f"处理股票 {stock_code} 时出错: {str(e)}"
            print(f"❌ {error_msg}")
    
    # 添加唯一标识符
    df_train["unique_id"] = df_train["stock_code"].astype(str)
    df_test["unique_id"] = df_test["stock_code"].astype(str)
    
    # 初始化模型
    print("初始化TimesFM模型...")
    tfm = timesfm.TimesFm(
        hparams=timesfm.TimesFmHparams(
            backend="gpu",
            per_core_batch_size=32,
            horizon_len=horizon_len,
            num_layers=50,
            use_positional_embedding=False,
            context_len=context_len,
        ),
        checkpoint=timesfm.TimesFmCheckpoint(
            path=original_model),
    )
    
    # 可选：添加技术指标
    try:
        print("尝试添加技术指标...")
        df_train, input_features = talib_tools(df_train, stock_code_list)
        df_test, input_features = talib_tools(df_test, stock_code_list)
        df_original, _ = talib_tools(df_original, stock_code_list)
        print("技术指标添加成功")
    except Exception as e:
        print(f"添加技术指标失败: {e}")
        print("继续使用原始数据...")
    
    # 进行预测
    print("\n开始预测...")
    print("训练数据示例:")
    print(df_train.head(1))
    
    # 为预测准备数据：去掉绘图日期列，只保留推理需要的列
    df_train_for_prediction = df_train.copy()
    if 'ds_plot' in df_train_for_prediction.columns:
        df_train_for_prediction = df_train_for_prediction.drop(columns=['ds_plot'])
    
    print("\n用于预测的数据列:")
    print(df_train_for_prediction.columns.tolist())
    
    try:
        forecast_df = tfm.forecast_on_df(
            inputs=df_train_for_prediction,
            freq="D",
            value_name="close",
            num_jobs=-1,
        )
        
        print("\n预测结果示例:")
        print(forecast_df.tail(10))
        
        # 为预测结果添加绘图日期列
        if 'ds' in forecast_df.columns:
            forecast_df['ds_plot'] = pd.to_datetime(forecast_df['ds']).dt.strftime('%Y-%m-%d')
            print("\n已为预测结果添加绘图日期列")
            print(f"预测结果ds_plot列前5个值: {forecast_df['ds_plot'].head().tolist()}")
            print(f"预测结果ds列前5个值: {forecast_df['ds'].head().tolist()}")
            print(f"预测结果ds列类型: {forecast_df['ds'].dtype}")
            print(f"预测结果ds_plot列类型: {forecast_df['ds_plot'].dtype}")
        
        # debug_info相关代码已删除
        
    except Exception as e:
        error_msg = f"预测过程出错: {str(e)}"
        debug_info["errors"].append(error_msg)
        print(f"❌ {error_msg}")
        # 保存调试信息并退出
        with open("main_program_debug.json", 'w', encoding='utf-8') as f:
            json.dump(debug_info, f, ensure_ascii=False, indent=2)
        return
    
    # 集成预测结果
    print("\n集成预测结果与实际数据...")
    print(f"forecast_df shape: {forecast_df.shape}")
    print(f"df_test shape: {df_test.shape}")
    print(f"stock_code_list: {stock_code_list}")
    try:
        results, figures = integrate_with_timesfm_forecast(forecast_df, df_test, stock_code_list, df_train)
        
        # debug_info集成结果记录已删除
        
    except Exception as e:
        error_msg = f"集成结果时出错: {str(e)}"
        print(f"❌ {error_msg}")
    
    # 保存结果
    print("\n保存预测图片...")
    try:
        for stock_code, result in results.items():
            # 保存预测对比图为PNG格式
            print(f"保存股票 {stock_code} 的matplotlib图片...")
            
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
            plt.title(f'{stock_code} Stock Price Forecast Comparison', fontsize=16, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Price', fontsize=12)
            plt.legend(fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # 格式化日期轴
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5))
            plt.xticks(rotation=45)
            
            # 调整布局
            plt.tight_layout()
            
            # 保存为PNG格式，设置高分辨率
            matplotlib_filename = f"{stock_code}_matplotlib_forecast_plot.png"
            plt.savefig(matplotlib_filename, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            print(f"✅ matplotlib图片已保存: {matplotlib_filename}")
        
        print("✅ 所有matplotlib图片保存完成")
        
    except Exception as e:
        error_msg = f"保存图片时出错: {str(e)}"
        print(f"❌ {error_msg}")
    
    # 调试信息和JSON保存代码已删除
    
    print("\n预测完成!")
    return results, figures


if __name__ == "__main__":
    main()