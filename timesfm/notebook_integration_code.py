# =============================================================================
# 在 app_multi_stock gpu.ipynb 中添加 pred_eval 图形化验证方法
# 将以下代码替换或添加到你的 notebook 单元格中
# =============================================================================

# 1. 导入pred_eval模块（如果还没有导入）
import pred_eval

# 2. 在处理每个股票的循环中，替换原有的pred_eval.fig_plot调用
# 找到类似这样的代码段并替换：

"""
原始代码（需要替换）:
for stock_code in stock_code_list:
    forecast_data = forecast_df[forecast_df['stock_code'] == stock_code].copy()
    # ... 数据处理 ...
    result = forecast_data[["x", "close", "timesfm-q-0.1", "timesfm-q-0.2", "timesfm-q-0.3", "timesfm-q-0.4", "timesfm-q-0.5", "timesfm-q-0.6", "timesfm-q-0.7", "timesfm-q-0.8", "timesfm-q-0.9"]].copy()
    pred_eval.fig_plot(result, stock_code, "预测结果")
"""

# 替换为以下增强版代码：
for stock_code in stock_code_list:
    print(f"\n{'='*60}")
    print(f"正在处理股票: {stock_code}")
    print(f"{'='*60}")
    
    # 提取并处理预测数据
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
    
    # ========== 使用pred_eval进行综合评估 ==========
    print(f"\n🔍 开始对股票 {stock_code} 进行综合评估...")
    
    try:
        # 执行综合评估
        evaluation_results = pred_eval.comprehensive_evaluation(result, stock_code)
        
        # 1. 显示预测对比图
        print(f"\n📊 预测对比图:")
        evaluation_results['prediction_plot'].show()
        
        # 2. 显示残差分析图
        print(f"\n📈 残差分析图:")
        evaluation_results['residuals_plot'].show()
        
        # 3. 显示评估指标表
        print(f"\n📋 评估指标表:")
        evaluation_results['metrics_table'].show()
        
        # 4. 打印详细数值指标
        metrics = evaluation_results['metrics']
        print(f"\n📊 股票 {stock_code} 详细评估指标:")
        print(f"   MSE (均方误差): {metrics['mse']:.6f}")
        print(f"   MAE (平均绝对误差): {metrics['mae']:.6f}")
        print(f"   RMSE (均方根误差): {metrics['rmse']:.6f}")
        print(f"   MAPE (平均绝对百分比误差): {metrics['mape']:.2f}%")
        print(f"   R² (决定系数): {metrics['r2']:.4f}")
        
        # 5. 模型性能评价
        if metrics['r2'] > 0.8:
            performance = "优秀 🌟"
        elif metrics['r2'] > 0.6:
            performance = "良好 👍"
        elif metrics['r2'] > 0.4:
            performance = "一般 ⚠️"
        else:
            performance = "需要改进 ❌"
        
        print(f"   模型性能评价: {performance}")
        print(f"   {'='*50}")
        
    except Exception as e:
        print(f"❌ 处理股票 {stock_code} 时出现错误: {str(e)}")
        # 如果综合评估失败，回退到基础图表
        print(f"🔄 回退到基础预测图表...")
        try:
            basic_fig = pred_eval.fig_plot(result, stock_code, "基础预测对比")
            basic_fig.show()
        except Exception as e2:
            print(f"❌ 基础图表也失败了: {str(e2)}")

# =============================================================================
# 可选：添加整体评估汇总
# =============================================================================

# 在所有股票处理完成后，可以添加以下代码来生成整体评估报告
print(f"\n\n{'='*80}")
print(f"🎯 整体评估汇总")
print(f"{'='*80}")
print(f"✅ 已完成 {len(stock_code_list)} 只股票的预测评估")
print(f"📊 每只股票都生成了以下分析图表:")
print(f"   • 预测值与实际值对比图（含置信区间）")
print(f"   • 残差分析图（散点图、直方图、Q-Q图、时序图）")
print(f"   • 评估指标表格")
print(f"   • 详细数值指标（MSE、MAE、RMSE、MAPE、R²）")
print(f"\n💡 提示: 所有图表都是交互式的，可以缩放、平移和悬停查看详细信息")
print(f"{'='*80}")

# =============================================================================
# 使用说明
# =============================================================================
"""
使用步骤:
1. 确保已经导入了pred_eval模块
2. 将上述代码复制到你的notebook中
3. 替换原有的股票处理循环
4. 运行单元格
5. 查看生成的交互式图表和详细评估指标

功能特性:
✓ 交互式预测对比图表
✓ 多维度残差分析
✓ 完整的统计评估指标
✓ 美观的表格显示
✓ 自动性能评价
✓ 错误处理和回退机制
✓ 整体评估汇总

注意事项:
- 确保安装了plotly: pip install plotly
- 图表在Jupyter环境中显示效果最佳
- 如果数据量很大，图表渲染可能需要一些时间
"""