#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pred_eval图形化验证方法演示脚本
用于TimesFM预测结果的可视化分析
"""

import pandas as pd
import numpy as np
import pred_eval
from datetime import datetime, timedelta

def demo_pred_eval_usage():
    """
    演示pred_eval模块的使用方法
    """
    print("=== pred_eval 图形化验证方法演示 ===")
    
    # 创建示例数据
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    np.random.seed(42)
    
    # 模拟真实股价数据
    true_prices = 100 + np.cumsum(np.random.randn(30) * 0.5)
    
    # 模拟预测数据（不同分位数）
    noise = np.random.randn(30) * 2
    pred_median = true_prices + noise
    
    # 创建结果DataFrame
    result_df = pd.DataFrame({
        'x': dates,
        'close': true_prices,
        'timesfm-q-0.1': pred_median - 3,
        'timesfm-q-0.2': pred_median - 2,
        'timesfm-q-0.3': pred_median - 1,
        'timesfm-q-0.4': pred_median - 0.5,
        'timesfm-q-0.5': pred_median,  # 中位数
        'timesfm-q-0.6': pred_median + 0.5,
        'timesfm-q-0.7': pred_median + 1,
        'timesfm-q-0.8': pred_median + 2,
        'timesfm-q-0.9': pred_median + 3
    })
    
    stock_code = "DEMO001"
    
    print(f"\n1. 基础预测对比图")
    print("   - 显示实际值与预测值的对比")
    print("   - 包含置信区间和多个分位数")
    fig1 = pred_eval.fig_plot(result_df, stock_code, "基础对比")
    # fig1.show()  # 在Jupyter中取消注释
    print("   ✓ 预测对比图已生成")
    
    print(f"\n2. 综合评估分析")
    print("   - 预测对比图")
    print("   - 残差分析图")
    print("   - 评估指标表")
    print("   - 详细数值指标")
    
    evaluation_results = pred_eval.comprehensive_evaluation(result_df, stock_code)
    
    # 显示评估指标
    metrics = evaluation_results['metrics']
    print(f"\n   评估指标结果:")
    print(f"   MSE (均方误差): {metrics['mse']:.6f}")
    print(f"   MAE (平均绝对误差): {metrics['mae']:.6f}")
    print(f"   RMSE (均方根误差): {metrics['rmse']:.6f}")
    print(f"   MAPE (平均绝对百分比误差): {metrics['mape']:.2f}%")
    print(f"   R² (决定系数): {metrics['r2']:.4f}")
    
    # 在Jupyter环境中，可以显示图表
    # evaluation_results['prediction_plot'].show()
    # evaluation_results['residuals_plot'].show()
    # evaluation_results['metrics_table'].show()
    
    print("   ✓ 综合评估分析已完成")
    
    print(f"\n3. 单独的残差分析")
    y_true = result_df['close'].values
    y_pred = result_df['timesfm-q-0.5'].values
    
    residuals_fig = pred_eval.plot_residuals(y_true, y_pred, stock_code)
    # residuals_fig.show()  # 在Jupyter中取消注释
    print("   ✓ 残差分析图已生成")
    
    print(f"\n4. 评估指标表格")
    metrics_table = pred_eval.create_metrics_table(metrics, stock_code)
    # metrics_table.show()  # 在Jupyter中取消注释
    print("   ✓ 评估指标表格已生成")
    
    return evaluation_results

def integrate_with_timesfm_forecast(forecast_df, df_test, stock_code_list):
    """
    与TimesFM预测结果集成的示例代码
    
    参数:
        forecast_df: TimesFM预测结果DataFrame
        df_test: 测试数据DataFrame
        stock_code_list: 股票代码列表
    """
    print("\n=== 与TimesFM预测结果集成 ===")
    
    # 处理预测结果
    forecast_df["stock_code"] = forecast_df["unique_id"].str.split("_", expand=True)[0]
    
    for stock_code in stock_code_list:
        print(f"\n处理股票: {stock_code}")
        
        # 提取预测数据
        forecast_data = forecast_df[forecast_df['stock_code'] == stock_code].copy()
        forecast_data.drop(columns=['stock_code', 'ds'], inplace=True)
        
        # 提取实际数据
        original_data = df_test[df_test['stock_code'] == stock_code]
        original_data = original_data[['stock_code', 'ds', 'close']].copy()
        
        # 合并数据
        forecast_data["stock_code"] = stock_code
        forecast_data["ds"] = original_data["ds"].values
        forecast_data["close"] = original_data["close"].values
        forecast_data["x"] = pd.to_datetime(forecast_data["ds"], unit='ms')
        
        # 准备结果数据
        result = forecast_data[[
            "x", "close", 
            "timesfm-q-0.1", "timesfm-q-0.2", "timesfm-q-0.3", "timesfm-q-0.4", "timesfm-q-0.5", 
            "timesfm-q-0.6", "timesfm-q-0.7", "timesfm-q-0.8", "timesfm-q-0.9"
        ]].copy()
        
        # 使用pred_eval进行综合评估
        evaluation_results = pred_eval.comprehensive_evaluation(result, stock_code)
        
        # 显示结果（在Jupyter环境中）
        print(f"   ✓ 预测对比图已生成")
        # evaluation_results['prediction_plot'].show()
        
        print(f"   ✓ 残差分析图已生成")
        # evaluation_results['residuals_plot'].show()
        
        print(f"   ✓ 评估指标表已生成")
        # evaluation_results['metrics_table'].show()
        
        # 打印数值指标
        metrics = evaluation_results['metrics']
        print(f"\n   股票 {stock_code} 详细评估指标:")
        print(f"   MSE (均方误差): {metrics['mse']:.6f}")
        print(f"   MAE (平均绝对误差): {metrics['mae']:.6f}")
        print(f"   RMSE (均方根误差): {metrics['rmse']:.6f}")
        print(f"   MAPE (平均绝对百分比误差): {metrics['mape']:.2f}%")
        print(f"   R² (决定系数): {metrics['r2']:.4f}")
        print("   " + "-" * 50)

if __name__ == "__main__":
    # 运行演示
    demo_results = demo_pred_eval_usage()
    
    print("\n=== 使用说明 ===")
    print("1. 在Jupyter Notebook中，取消注释 .show() 方法来显示图表")
    print("2. 将 integrate_with_timesfm_forecast() 函数的代码复制到你的notebook中")
    print("3. 替换原有的pred_eval调用代码")
    print("4. 运行单元格查看完整的图形化验证结果")
    
    print("\n=== 功能特性 ===")
    print("✓ 预测值与实际值对比图")
    print("✓ 多分位数预测区间显示")
    print("✓ 置信区间可视化")
    print("✓ 残差分析（散点图、直方图、Q-Q图、时序图）")
    print("✓ 完整的评估指标（MSE、MAE、RMSE、MAPE、R²）")
    print("✓ 美观的指标表格显示")
    print("✓ 交互式Plotly图表")