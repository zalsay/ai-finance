# ValueError修复说明

## 问题描述

在运行 `integrate_with_timesfm_forecast(forecast_df, df_test, stock_code_list)` 时出现以下错误：

```
ValueError: Length of values (1172) does not match length of index (128)
```

## 问题原因

这个错误发生在以下代码行：
```python
forecast_data["ds"] = original_data["ds"].values
```

**根本原因：**
- `forecast_data` 的长度是 128 行（预测数据）
- `original_data` 的长度是 1172 行（实际测试数据）
- 当尝试将长度为 1172 的数组赋值给长度为 128 的DataFrame时，pandas抛出长度不匹配错误

## 解决方案

### 方案1：使用修复后的函数

1. 导入修复后的代码：
```python
from fixed_integration_code import fixed_integrate_with_timesfm_forecast
```

2. 使用修复后的函数：
```python
fixed_integrate_with_timesfm_forecast(forecast_df, df_test, stock_code_list)
```

### 方案2：直接在notebook中替换代码

将原来的代码替换为以下修复后的代码：

```python
import pred_eval
forecast_df["stock_code"] = forecast_df["unique_id"].str.split("_", expand=True)[0]

for stock_code in stock_code_list:
    print(f"\n处理股票: {stock_code}")
    
    # 提取预测数据
    forecast_data = forecast_df[forecast_df['stock_code'] == stock_code].copy()
    print(f"预测数据长度: {len(forecast_data)}")
    
    # 提取实际数据
    original_data = df_test[df_test['stock_code'] == stock_code]
    original_data = original_data[['stock_code', 'ds', 'close']].copy()
    print(f"实际数据长度: {len(original_data)}")
    
    # 确保数据长度匹配 - 取较短的长度
    min_length = min(len(forecast_data), len(original_data))
    print(f"使用数据长度: {min_length}")
    
    if min_length == 0:
        print(f"❌ 股票 {stock_code} 没有匹配的数据，跳过")
        continue
        
    # 截取相同长度的数据
    forecast_data = forecast_data.head(min_length).copy()
    original_data = original_data.head(min_length).copy()
    
    # 重置索引以确保对齐
    forecast_data.reset_index(drop=True, inplace=True)
    original_data.reset_index(drop=True, inplace=True)
    
    # 删除不需要的列
    forecast_data.drop(columns=['stock_code', 'ds'], inplace=True, errors='ignore')
    
    # 合并数据
    forecast_data["stock_code"] = stock_code
    forecast_data["ds"] = original_data["ds"].values
    forecast_data["close"] = original_data["close"].values
    forecast_data["x"] = pd.to_datetime(forecast_data["ds"], unit='ms')

    # 准备结果数据
    result = forecast_data[["x", "close", "timesfm-q-0.1", "timesfm-q-0.2", "timesfm-q-0.3", "timesfm-q-0.4", "timesfm-q-0.5", "timesfm-q-0.6", "timesfm-q-0.7", "timesfm-q-0.8", "timesfm-q-0.9"]].copy()
    
    # 生成图表
    try:
        fig_timesfm = pred_eval.fig_plot(result, stock_code)
        fig_timesfm.show()
        print(f"✓ 成功生成股票 {stock_code} 的预测图表")
    except Exception as e:
        print(f"❌ 生成图表时出错: {str(e)}")
        print(f"结果数据形状: {result.shape}")
        print(f"结果数据列: {result.columns.tolist()}")
```

## 修复要点

1. **长度检查**：在合并数据前检查两个DataFrame的长度
2. **数据截取**：使用 `min_length = min(len(forecast_data), len(original_data))` 取较短的长度
3. **索引重置**：使用 `reset_index(drop=True, inplace=True)` 确保索引对齐
4. **错误处理**：添加try-catch块处理可能的其他错误
5. **调试信息**：添加打印语句帮助调试数据长度问题

## 预期结果

修复后，代码将：
- 显示每个股票的数据长度信息
- 自动处理长度不匹配问题
- 成功生成预测对比图表
- 提供详细的错误信息（如果仍有问题）

## 注意事项

- 修复后的代码会截取较短的数据长度，这意味着可能会丢失一些数据点
- 如果需要保留所有数据，可能需要重新考虑数据对齐策略
- 建议检查预测数据和测试数据的时间范围是否匹配