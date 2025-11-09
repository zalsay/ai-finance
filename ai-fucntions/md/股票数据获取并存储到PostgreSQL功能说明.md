# 股票数据获取并存储到PostgreSQL功能说明

## 功能概述

本功能扩展了原有的akshare股票数据获取功能，新增了将股票数据直接存储到PostgreSQL数据库的能力。通过调用postgres-handler服务的API接口，实现了数据的自动化存储和管理。

## 新增功能

### 1. PostgreSQLAPIClient 类
- **功能**: 与postgres-handler服务进行交互的API客户端
- **主要方法**:
  - `health_check()`: 检查API服务健康状态
  - `insert_single_stock_data()`: 插入单条股票数据
  - `batch_insert_stock_data()`: 批量插入股票数据
  - `get_stock_data()`: 从数据库获取股票数据

### 2. convert_dataframe_to_api_format() 函数
- **功能**: 将pandas DataFrame转换为API所需的JSON格式
- **特点**: 
  - 自动处理数据类型转换
  - 处理NaN值
  - 支持所有股票数据字段

### 3. fetch_and_store_stock_data() 函数
- **功能**: 主要的数据获取和存储函数
- **特点**:
  - 集成了数据获取、转换和存储的完整流程
  - 支持批量插入和容错机制
  - 提供详细的执行统计信息

## 使用方法

### 基本使用示例

```python
from get_finanial_data import PostgreSQLAPIClient, fetch_and_store_stock_data

# 1. 创建API客户端
api_client = PostgreSQLAPIClient(base_url="http://localhost:8080")

# 2. 获取并存储股票数据
result = fetch_and_store_stock_data(
    symbol="600398",           # 股票代码
    api_client=api_client,     # API客户端
    start_date="20240101",     # 开始日期
    end_date=None,             # 结束日期（None表示到当前）
    stock_type=1,              # 股票类型
    batch_size=1000,           # 批次大小
    max_retries=3              # 最大重试次数
)

# 3. 查看结果
if result["success"]:
    print(f"✅ 数据存储成功:")
    print(f"   - 总记录数: {result['total_records']}")
    print(f"   - 成功存储: {result['stored_records']}")
    print(f"   - 成功率: {result['success_rate']}")
else:
    print(f"❌ 数据存储失败: {result.get('error', '未知错误')}")
```

### 批量处理多个股票

```python
# 批量处理多个股票代码
stock_symbols = ["600398", "000001", "000002", "600000"]
api_client = PostgreSQLAPIClient(base_url="http://localhost:8080")

for symbol in stock_symbols:
    print(f"正在处理股票: {symbol}")
    result = fetch_and_store_stock_data(
        symbol=symbol,
        api_client=api_client,
        start_date="20240101",
        stock_type=1,
        batch_size=500
    )
    
    if result["success"]:
        print(f"✅ {symbol}: {result['stored_records']}/{result['total_records']} 条记录")
    else:
        print(f"❌ {symbol}: {result.get('error')}")
```

### 从数据库获取数据

```python
# 从数据库获取已存储的数据
api_client = PostgreSQLAPIClient(base_url="http://localhost:8080")

# 获取最新100条记录
data = api_client.get_stock_data(
    symbol="600398",
    stock_type=1,
    limit=100,
    offset=0
)

print(f"获取到 {len(data)} 条记录")
for record in data[:5]:  # 显示前5条
    print(f"{record['datetime']} - 收盘价: {record['close']}")
```

## 参数说明

### stock_type 参数
- `1`: 股票
- `2`: 基金（包含ETF）
- `3`: 指数
- `4+`: 其他类型

### batch_size 参数
- 建议值: 500-1000
- 过大可能导致请求超时
- 过小会影响插入效率

### 日期格式
- 输入格式: "YYYYMMDD" (如: "20240101")
- 数据库存储格式: ISO 8601 格式

## 前置条件

1. **PostgreSQL服务运行**: 确保PostgreSQL数据库服务正在运行
2. **postgres-handler API服务运行**: 
   ```bash
   cd /root/workers/finance/postgres-handler
   ./deploy.sh start
   ```
3. **网络连接**: 确保能够访问akshare数据源
4. **Python依赖**: 确保安装了所需的Python包

## 错误处理

### 常见错误及解决方案

1. **API服务不可用**
   - 检查postgres-handler服务是否运行
   - 确认API服务地址是否正确

2. **数据库连接失败**
   - 检查PostgreSQL服务状态
   - 确认数据库连接配置

3. **数据获取失败**
   - 检查网络连接
   - 确认股票代码是否正确
   - 检查日期范围是否合理

4. **批量插入失败**
   - 系统会自动降级为单条插入
   - 检查数据格式是否正确

## 性能优化建议

1. **合理设置批次大小**: 根据网络和服务器性能调整batch_size
2. **分时段获取数据**: 对于历史数据较多的股票，可以分时段获取
3. **并发处理**: 可以使用多线程处理多个股票代码
4. **错误重试**: 利用内置的重试机制处理临时性错误

## 监控和日志

系统提供了详细的日志记录，包括：
- 数据获取进度
- API请求状态
- 错误信息和重试情况
- 存储统计信息

可以通过调整日志级别来控制输出详细程度：

```python
import logging
logging.getLogger().setLevel(logging.INFO)  # 或 DEBUG, WARNING, ERROR
```

## 扩展功能

该功能框架支持进一步扩展：
- 支持更多数据源
- 添加数据验证和清洗
- 实现增量更新机制
- 添加数据质量监控
- 支持实时数据流处理