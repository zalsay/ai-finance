import plotly.graph_objects as go
import os, sys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime
current_dir = os.path.dirname(os.path.abspath(__file__))
finance_dir = os.path.dirname(current_dir)
timesfm_dir = os.path.join(finance_dir, 'timesfm')
sys.path.append(timesfm_dir)
from req_res_types import ChunkedPredictionResponse
pre_data_dir = os.path.join(finance_dir, 'preprocess_data')
from math_functions import *

def plot_forecast_vs_actual_simple(plot_df, stock_code):
    """
    简化的绘图函数，直接使用绘图DataFrame
    """
    try:
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

def plot_chunked_prediction_results(response: ChunkedPredictionResponse, save_path: str = None) -> str:
    """
    绘制分块预测结果图表，显示最佳预测值和英文标签
    
    Args:
        response: 分块预测响应对象
        save_path: 图片保存路径，如果为None则自动生成
        
    Returns:
        str: 保存的图片路径
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
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        plt.title(f'Stock {response.stock_code} Chunked Prediction Results\n'
                 f'Total Chunks: {response.total_chunks}, Horizon Length: {response.horizon_len} days\n'
                 f'Average MSE: {response.overall_metrics.get("avg_mse", 0):.6f}, '
                 f'Average MAE: {response.overall_metrics.get("avg_mae", 0):.6f}\n'
                 f'Generated on: {current_time}', 
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