import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

def fig_plot(result_df, stock_code, title_suffix=""):
    """
    创建预测结果的可视化图表
    
    参数:
        result_df: DataFrame，包含x(时间), close(实际值), timesfm-q-*列(预测分位数)
        stock_code: 股票代码
        title_suffix: 标题后缀
    
    返回:
        plotly图表对象
    """
    fig = go.Figure()
    
    # 添加实际值线
    fig.add_trace(go.Scatter(
        x=result_df['x'],
        y=result_df['close'],
        mode='lines',
        name='实际值',
        line=dict(color='blue', width=2)
    ))
    
    # 添加预测中位数线
    if 'timesfm-q-0.5' in result_df.columns:
        fig.add_trace(go.Scatter(
            x=result_df['x'],
            y=result_df['timesfm-q-0.5'],
            mode='lines',
            name='预测中位数',
            line=dict(color='red', width=2)
        ))
    
    # 添加置信区间
    if 'timesfm-q-0.1' in result_df.columns and 'timesfm-q-0.9' in result_df.columns:
        fig.add_trace(go.Scatter(
            x=result_df['x'],
            y=result_df['timesfm-q-0.9'],
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            name='上界'
        ))
        
        fig.add_trace(go.Scatter(
            x=result_df['x'],
            y=result_df['timesfm-q-0.1'],
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor='rgba(255,0,0,0.2)',
            name='80%置信区间',
            showlegend=True
        ))
    
    # 添加其他分位数线（可选）
    quantiles = ['timesfm-q-0.2', 'timesfm-q-0.3', 'timesfm-q-0.4', 'timesfm-q-0.6', 'timesfm-q-0.7', 'timesfm-q-0.8']
    colors = ['orange', 'green', 'purple', 'brown', 'pink', 'gray']
    
    for i, q in enumerate(quantiles):
        if q in result_df.columns:
            fig.add_trace(go.Scatter(
                x=result_df['x'],
                y=result_df[q],
                mode='lines',
                name=f'分位数{q.split("-")[-1]}',
                line=dict(color=colors[i % len(colors)], width=1, dash='dot'),
                opacity=0.7
            ))
    
    # 设置图表布局
    fig.update_layout(
        title=f'股票{stock_code}预测结果对比{title_suffix}',
        xaxis_title='时间',
        yaxis_title='价格',
        hovermode='x unified',
        width=1000,
        height=600,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    return fig

def calculate_metrics(y_true, y_pred):
    """
    计算预测指标
    
    参数:
        y_true: 实际值
        y_pred: 预测值
    
    返回:
        字典，包含各种评估指标
    """
    # 移除NaN值
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true_clean = y_true[mask]
    y_pred_clean = y_pred[mask]
    
    if len(y_true_clean) == 0:
        return {
            'mse': np.nan,
            'mae': np.nan,
            'rmse': np.nan,
            'mape': np.nan,
            'r2': np.nan
        }
    
    mse = np.mean((y_true_clean - y_pred_clean) ** 2)
    mae = np.mean(np.abs(y_true_clean - y_pred_clean))
    rmse = np.sqrt(mse)
    
    # MAPE (Mean Absolute Percentage Error)
    mape = np.mean(np.abs((y_true_clean - y_pred_clean) / y_true_clean)) * 100
    
    # R²
    ss_res = np.sum((y_true_clean - y_pred_clean) ** 2)
    ss_tot = np.sum((y_true_clean - np.mean(y_true_clean)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else np.nan
    
    return {
        'mse': mse,
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'r2': r2
    }

def plot_residuals(y_true, y_pred, stock_code):
    """
    绘制残差图
    
    参数:
        y_true: 实际值
        y_pred: 预测值
        stock_code: 股票代码
    
    返回:
        plotly图表对象
    """
    residuals = y_true - y_pred
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('残差散点图', '残差直方图', '残差Q-Q图', '残差时间序列'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # 残差散点图
    fig.add_trace(
        go.Scatter(x=y_pred, y=residuals, mode='markers', name='残差'),
        row=1, col=1
    )
    fig.add_hline(y=0, line_dash="dash", line_color="red", row=1, col=1)
    
    # 残差直方图
    fig.add_trace(
        go.Histogram(x=residuals, name='残差分布', nbinsx=30),
        row=1, col=2
    )
    
    # 残差时间序列
    fig.add_trace(
        go.Scatter(y=residuals, mode='lines+markers', name='残差时序'),
        row=2, col=1
    )
    fig.add_hline(y=0, line_dash="dash", line_color="red", row=2, col=1)
    
    # Q-Q图（简化版）
    from scipy import stats
    theoretical_quantiles = stats.norm.ppf(np.linspace(0.01, 0.99, len(residuals)))
    sample_quantiles = np.sort(residuals)
    
    fig.add_trace(
        go.Scatter(x=theoretical_quantiles, y=sample_quantiles, mode='markers', name='Q-Q图'),
        row=2, col=2
    )
    
    # 添加Q-Q图的理论线
    min_val = min(theoretical_quantiles.min(), sample_quantiles.min())
    max_val = max(theoretical_quantiles.max(), sample_quantiles.max())
    fig.add_trace(
        go.Scatter(x=[min_val, max_val], y=[min_val, max_val], 
                  mode='lines', name='理论线', line=dict(color='red', dash='dash')),
        row=2, col=2
    )
    
    fig.update_layout(
        title=f'股票{stock_code}预测残差分析',
        height=800,
        showlegend=False
    )
    
    return fig

def create_metrics_table(metrics_dict, stock_code):
    """
    创建指标表格
    
    参数:
        metrics_dict: 指标字典
        stock_code: 股票代码
    
    返回:
        plotly表格对象
    """
    metrics_df = pd.DataFrame([
        ['MSE', f'{metrics_dict["mse"]:.6f}'],
        ['MAE', f'{metrics_dict["mae"]:.6f}'],
        ['RMSE', f'{metrics_dict["rmse"]:.6f}'],
        ['MAPE (%)', f'{metrics_dict["mape"]:.2f}'],
        ['R²', f'{metrics_dict["r2"]:.4f}']
    ], columns=['指标', '值'])
    
    fig = go.Figure(data=[go.Table(
        header=dict(values=['评估指标', '数值'],
                   fill_color='paleturquoise',
                   align='left'),
        cells=dict(values=[metrics_df['指标'], metrics_df['值']],
                  fill_color='lavender',
                  align='left'))
    ])
    
    fig.update_layout(
        title=f'股票{stock_code}预测评估指标',
        height=300
    )
    
    return fig

def comprehensive_evaluation(result_df, stock_code, pred_column='timesfm-q-0.5'):
    """
    综合评估函数，生成完整的预测评估报告
    
    参数:
        result_df: 结果DataFrame
        stock_code: 股票代码
        pred_column: 预测列名
    
    返回:
        包含多个图表的字典
    """
    if pred_column not in result_df.columns:
        pred_column = 'timesfm-q-0.5'  # 默认使用中位数
    
    y_true = result_df['close'].values
    y_pred = result_df[pred_column].values
    
    # 计算指标
    metrics = calculate_metrics(y_true, y_pred)
    
    # 生成图表
    charts = {
        'prediction_plot': fig_plot(result_df, stock_code),
        'residuals_plot': plot_residuals(y_true, y_pred, stock_code),
        'metrics_table': create_metrics_table(metrics, stock_code),
        'metrics': metrics
    }
    
    return charts