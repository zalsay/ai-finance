import plotly.graph_objects as go
import os, sys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
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
    Simplified plotting function using plot DataFrame directly
    """
    try:
        # Create chart
        fig = go.Figure()
        
        # Add actual data
        fig.add_trace(go.Scatter(
            x=plot_df['index'],
            y=plot_df['actual'],
            mode='lines+markers',
            name='Actual Price',
            line=dict(color='blue', width=2),
            marker=dict(size=4)
        ))
        
        # Add forecast data
        fig.add_trace(go.Scatter(
            x=plot_df['index'],
            y=plot_df['forecast'],
            mode='lines+markers',
            name='Forecast Price',
            line=dict(color='red', width=2),
            marker=dict(size=4)
        ))
        
        # Add forecast interval
        fig.add_trace(go.Scatter(
            x=plot_df['index'],
            y=plot_df['forecast_upper'],
            mode='lines',
            name='Forecast Upper Bound',
            line=dict(color='rgba(255,0,0,0.3)', width=1),
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=plot_df['index'],
            y=plot_df['forecast_lower'],
            mode='lines',
            name='Forecast Lower Bound',
            line=dict(color='rgba(255,0,0,0.3)', width=1),
            fill='tonexty',
            fillcolor='rgba(255,0,0,0.1)',
            showlegend=False
        ))
        
        # Update layout
        fig.update_layout(
            title=f'{stock_code} Stock Price Forecast vs Actual',
            xaxis_title='Time Series Index',
            yaxis_title='Price',
            hovermode='x unified',
            width=1200,
            height=800
        )
        
        # Disable plotly image saving to avoid Kaleido library issues
        print(f"Simplified forecast chart created, skipping PNG save to avoid Kaleido issues")
        
        # Optional: Save as HTML format
        html_filename = f"{stock_code}_simple_forecast_plot.html"
        fig.write_html(html_filename)
        print(f"HTML chart saved: {html_filename}")
        
        return fig
        
    except Exception as e:
        print(f"Error during plotting: {str(e)}")
        return None

def plot_chunked_prediction_results(response: ChunkedPredictionResponse, save_path: str = None) -> str:
    """
    Plot chunked prediction results, showing best prediction item and validation results
    
    Args:
        response: Chunked prediction response object
        save_path: Image save path, auto-generated if None
        
    Returns:
        str: Saved image path
    """
    if (not response.concatenated_predictions or 
        not response.concatenated_actual or 
        (isinstance(response.concatenated_predictions, dict) and not response.concatenated_predictions) or
        (isinstance(response.concatenated_actual, list) and not response.concatenated_actual)):
        print("❌ No concatenated prediction results to plot")
        return None
    
    try:
        # Set matplotlib to use a font that supports both English and Chinese
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        # Set image save path
        if save_path is None:
            save_path = f"{finance_dir}/forecast-results/{response.stock_code}_chunked_prediction_plot.png"
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
        
        # Convert dates
        dates = pd.to_datetime(response.concatenated_dates)
        actual_values = response.concatenated_actual
        
        # Get best prediction item information
        best_prediction_item = response.overall_metrics.get('best_prediction_item')
        best_metrics = response.overall_metrics.get('best_metrics', {})
        validation_results = response.overall_metrics.get('validation_results', {})
        
        # Build complete prediction sequence for best prediction item
        best_predictions = []
        for chunk_result in response.chunk_results:
            chunk_size = len(chunk_result.actual_values)
            if best_prediction_item and best_prediction_item in chunk_result.predictions:
                best_predictions.extend(chunk_result.predictions[best_prediction_item])
            else:
                # If no best prediction item, use tsf-0.5 as default
                if 'tsf-0.5' in chunk_result.predictions:
                    best_predictions.extend(chunk_result.predictions['tsf-0.5'][:chunk_size])
                elif chunk_result.predictions:
                    best_predictions.extend(list(chunk_result.predictions.values())[0][:chunk_size])
                else:
                    best_predictions.extend([0] * chunk_size)
        
        # Top subplot: Main prediction results
        ax1.plot(dates, actual_values, 'b-', linewidth=2, label='Actual Price', alpha=0.8)
        ax1.plot(dates, best_predictions, 'r-', linewidth=2, label=f'Best Prediction ({best_prediction_item or "tsf-0.5"})', alpha=0.8)
        
        # Confidence interval fill
        predictions = response.concatenated_predictions or {}
        if 'tsf-0.1' in predictions and 'tsf-0.9' in predictions:
            lower_bound = predictions['tsf-0.1']
            upper_bound = predictions['tsf-0.9']
            ax1.fill_between(dates, lower_bound, upper_bound, alpha=0.15, color='red', label='80% Confidence Interval')
        
        # Add chunk boundary lines
        chunk_boundaries = []
        for i, result in enumerate(response.chunk_results):
            if i > 0:  # Skip the first chunk start
                chunk_start = pd.to_datetime(result.chunk_start_date)
                chunk_boundaries.append(chunk_start)
        
        for boundary in chunk_boundaries:
            ax1.axvline(x=boundary, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        
        # Set top subplot properties
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ax1.set_title(f'{response.stock_code} Chunked Prediction Results\n'
                     f'Total Chunks: {response.total_chunks}, Horizon Length: {response.horizon_len} days', 
                     fontsize=14, pad=20)
        
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Stock Price', fontsize=12)
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Set date format
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Bottom subplot: Metrics information table
        ax2.axis('off')  # Hide axes
        
        # Build table data
        table_data = []
        
        # Overall metrics
        table_data.append(['Overall Metrics', ''])
        table_data.append(['Average MSE', f"{response.overall_metrics.get('avg_mse', 0):.6f}"])
        table_data.append(['Average MAE', f"{response.overall_metrics.get('avg_mae', 0):.6f}"])
        table_data.append(['Successful Chunks', f"{response.overall_metrics.get('successful_chunks', 0)}/{response.overall_metrics.get('total_chunks', 0)}"])
        table_data.append(['', ''])
        
        # Best prediction item metrics
        if best_prediction_item:
            table_data.append(['Best Prediction Item Metrics', ''])
            table_data.append(['Best Prediction Item', best_prediction_item])
            table_data.append(['Composite Score', f"{best_metrics.get('composite_score', 0):.4f}"])
            table_data.append(['MSE', f"{best_metrics.get('mse', 0):.4f}"])
            table_data.append(['MAE', f"{best_metrics.get('mae', 0):.4f}"])
            table_data.append(['Return Difference', f"{best_metrics.get('return_diff', 0):.2f}%"])
            table_data.append(['', ''])
        
        # Validation results
        if validation_results:
            table_data.append(['Validation Results', ''])
            table_data.append(['Validation Chunks', f"{validation_results.get('validation_chunks', 0)}"])
            table_data.append(['Successful Validation Chunks', f"{validation_results.get('successful_validation_chunks', 0)}"])
            table_data.append(['Validation MSE', f"{validation_results.get('validation_mse', 0):.4f}"])
            table_data.append(['Validation MAE', f"{validation_results.get('validation_mae', 0):.4f}"])
            table_data.append(['Validation Return Difference', f"{validation_results.get('validation_return_diff', 0):.2f}%"])
        
        # Create table
        if table_data:
            table = ax2.table(cellText=table_data, 
                            cellLoc='left', 
                            loc='center',
                            bbox=[0.1, 0.1, 0.8, 0.8])
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1.2, 1.5)
        
        # Add generation time information
        fig.text(0.02, 0.02, f'Generated at: {current_time}', fontsize=8, alpha=0.7)
        
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
