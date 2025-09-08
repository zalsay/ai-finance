# pred_eval 图形化验证方法使用指南

## 概述

`pred_eval` 模块为 TimesFM 预测结果提供了完整的图形化验证方法，包括预测对比图、残差分析、评估指标表格等多种可视化工具。

## 文件说明

- `pred_eval.py` - 核心模块，包含所有图形化验证函数
- `pred_eval_demo.py` - 演示脚本，展示模块的使用方法
- `notebook_integration_code.py` - 集成代码，可直接复制到 Jupyter Notebook 中使用

## 主要功能

### 1. 预测对比图 (`fig_plot`)
- 显示实际值与预测值的对比
- 包含多个分位数预测区间
- 交互式 Plotly 图表
- 置信区间可视化

### 2. 残差分析 (`plot_residuals`)
- 残差散点图
- 残差直方图
- Q-Q 正态性检验图
- 残差时序图

### 3. 评估指标计算 (`calculate_metrics`)
- MSE (均方误差)
- MAE (平均绝对误差)
- RMSE (均方根误差)
- MAPE (平均绝对百分比误差)
- R² (决定系数)

### 4. 指标表格 (`create_metrics_table`)
- 美观的评估指标表格
- 交互式表格显示

### 5. 综合评估 (`comprehensive_evaluation`)
- 一键生成所有分析图表
- 返回完整的评估结果
- 包含所有图表和指标

## 快速开始

### 1. 安装依赖

```bash
pip install plotly pandas numpy matplotlib seaborn scipy
```

### 2. 基础使用

```python
import pred_eval
import pandas as pd

# 准备数据 (包含 x, close, timesfm-q-0.1 到 timesfm-q-0.9 列)
result_df = your_forecast_data
stock_code = "AAPL"

# 生成预测对比图
fig = pred_eval.fig_plot(result_df, stock_code, "预测结果")
fig.show()

# 综合评估
evaluation = pred_eval.comprehensive_evaluation(result_df, stock_code)
evaluation['prediction_plot'].show()
evaluation['residuals_plot'].show()
evaluation['metrics_table'].show()

# 查看评估指标
metrics = evaluation['metrics']
print(f"RMSE: {metrics['rmse']:.4f}")
print(f"R²: {metrics['r2']:.4f}")
```

### 3. 在 Jupyter Notebook 中集成

将 `notebook_integration_code.py` 中的代码复制到你的 notebook 中，替换原有的预测结果处理代码。

## 数据格式要求

输入的 DataFrame 需要包含以下列：

- `x`: 时间戳 (datetime 格式)
- `close`: 实际股价值
- `timesfm-q-0.1` 到 `timesfm-q-0.9`: TimesFM 预测的各分位数值

示例数据格式：

```python
           x      close  timesfm-q-0.1  timesfm-q-0.5  timesfm-q-0.9
0 2024-01-01     100.5          98.2         100.1         102.3
1 2024-01-02     101.2          99.1         101.0         103.1
...
```

## 输出说明

### 图表类型

1. **预测对比图**
   - 实际值线条（蓝色）
   - 预测中位数线条（红色）
   - 置信区间填充（灰色阴影）
   - 各分位数线条

2. **残差分析图**
   - 2x2 子图布局
   - 残差散点图、直方图、Q-Q图、时序图

3. **评估指标表**
   - 交互式表格
   - 包含所有统计指标

### 评估指标解释

- **MSE**: 均方误差，越小越好
- **MAE**: 平均绝对误差，越小越好
- **RMSE**: 均方根误差，越小越好
- **MAPE**: 平均绝对百分比误差，越小越好
- **R²**: 决定系数，越接近1越好

### 性能评价标准

- R² > 0.8: 优秀 🌟
- R² > 0.6: 良好 👍
- R² > 0.4: 一般 ⚠️
- R² ≤ 0.4: 需要改进 ❌

## 示例运行

```bash
# 运行演示脚本
cd /root/workers/finance/timesfm
python pred_eval_demo.py
```

## 注意事项

1. **环境要求**: 建议在 Jupyter Notebook 环境中使用，图表显示效果最佳
2. **数据质量**: 确保输入数据没有缺失值或异常值
3. **性能**: 大数据量时图表渲染可能需要时间
4. **交互性**: 所有图表都支持缩放、平移、悬停等交互操作

## 错误处理

模块包含完善的错误处理机制：
- 数据验证
- 异常捕获
- 回退机制
- 详细错误信息

## 扩展功能

可以根据需要扩展以下功能：
- 自定义图表样式
- 添加更多评估指标
- 支持批量股票对比
- 导出图表和报告

## 技术栈

- **Plotly**: 交互式图表
- **Pandas**: 数据处理
- **NumPy**: 数值计算
- **Matplotlib/Seaborn**: 统计图表
- **SciPy**: 统计分析

---

**作者**: AI Assistant  
**版本**: 1.0  
**更新时间**: 2024年