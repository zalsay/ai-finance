# TimesFM 分块预测功能说明

## 概述

分块预测功能是对TimesFM模型的扩展，允许将测试数据按照指定的horizon_len进行分块，并对每个分块分别进行预测。这种方法特别适用于长期预测和滚动预测场景。

## 功能特点

### 模式1：固定训练集分块预测

- **固定训练数据**：使用固定的end_date（如20250630）生成训练数据集
- **分块测试**：将测试数据按horizon_len分块
- **独立预测**：每个分块使用相同的训练集进行独立预测
- **性能评估**：计算每个分块的MSE、MAE和综合评分

## API接口

### 分块预测接口

**端点**: `POST /predict/chunked`

**请求参数**:
```json
{
    "stock_code": "000001",
    "stock_type": "stock",
    "time_step": 1,
    "years": 3,
    "horizon_len": 30,
    "context_len": 512,
    "include_technical_indicators": true,
    "fixed_end_date": "20250630"
}
```

**响应格式**:
```json
{
    "success": true,
    "stock_code": "000001",
    "gpu_id": 0,
    "prediction_mode": 1,
    "total_chunks": 5,
    "successful_chunks": 5,
    "failed_chunks": 0,
    "total_processing_time": 45.67,
    "chunk_results": [
        {
            "chunk_index": 0,
            "chunk_start_date": "2025-07-01",
            "chunk_end_date": "2025-07-30",
            "success": true,
            "prediction_data": {
                "chunk_index": 0,
                "stock_code": "000001",
                "prediction_mode": 1,
                "chunk_size": 30,
                "best_prediction_column": "timesfm-q-0.5",
                "best_combined_score": 0.1234,
                "all_metrics": {...},
                "forecast_data": [...],
                "actual_chunk_data": [...]
            },
            "processing_time": 9.12
        }
    ],
    "summary": {
        "test_data_size": 150,
        "test_date_range": {
            "start": "2025-07-01",
            "end": "2025-11-30"
        },
        "fixed_training_end_date": "20250630",
        "chunk_size": 30,
        "success_rate": 100.0,
        "average_processing_time_per_chunk": 9.13,
        "average_best_score": 0.1234
    }
}
```

## 核心功能

### 1. 数据分块

```python
def create_chunks_from_test_data(df_test: pd.DataFrame, horizon_len: int) -> List[pd.DataFrame]:
    """根据horizon_len将df_test分块"""
    chunks = []
    total_rows = len(df_test)
    
    for i in range(0, total_rows, horizon_len):
        chunk = df_test.iloc[i:i+horizon_len].copy()
        if len(chunk) > 0:
            chunks.append(chunk)
    
    return chunks
```

### 2. 单分块预测

- 获取固定训练数据集
- 数据预处理和技术指标添加
- 动态调整模型参数
- 执行预测并计算评估指标

### 3. 评估指标

- **MSE (均方误差)**: 衡量预测值与实际值的平方差
- **MAE (平均绝对误差)**: 衡量预测值与实际值的绝对差
- **综合评分**: MSE和MAE的加权平均 (各占50%权重)

## 使用示例

### Python客户端调用

```python
import asyncio
from client_concurrent import TimesFMConcurrentClient

async def test_chunked_prediction():
    client = TimesFMConcurrentClient()
    
    # 等待服务启动
    await client.wait_for_services()
    
    # 执行分块预测
    result = await client.test_chunked_prediction(
        stock_code="000001",
        horizon_len=30,
        fixed_end_date="20250630"
    )
    
    if result:
        print(f"预测成功！总分块数: {result['total_chunks']}")
        print(f"成功率: {result['summary']['success_rate']:.2f}%")

# 运行测试
asyncio.run(test_chunked_prediction())
```

### 直接HTTP请求

```bash
curl -X POST "http://localhost:8000/predict/chunked" \
     -H "Content-Type: application/json" \
     -d '{
       "stock_code": "000001",
       "stock_type": "stock",
       "time_step": 1,
       "years": 3,
       "horizon_len": 30,
       "context_len": 512,
       "include_technical_indicators": true,
       "fixed_end_date": "20250630"
     }'
```

## 优势

1. **灵活性**: 可以根据需要调整分块大小
2. **稳定性**: 使用固定训练集确保预测一致性
3. **可扩展性**: 易于扩展到其他预测模式
4. **详细评估**: 提供每个分块的详细性能指标
5. **错误处理**: 单个分块失败不影响其他分块

## 注意事项

1. **数据要求**: 确保固定结束日期之后有足够的测试数据
2. **计算资源**: 分块数量越多，计算时间越长
3. **内存使用**: 大量分块可能占用较多内存
4. **模型参数**: 每个分块会动态调整模型的horizon_len参数

## 未来扩展

- **模式2**: 滚动训练集分块预测（下一步实现）
- **并行处理**: 多个分块的并行预测
- **自适应分块**: 根据数据特征自动调整分块大小
- **结果可视化**: 分块预测结果的图表展示