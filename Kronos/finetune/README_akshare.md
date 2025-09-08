# AkShare数据预处理方案

基于akshare库实现的金融数据预处理方案，与qlib数据预处理功能完全兼容。

## 📋 目录

- [功能特性](#功能特性)
- [文件说明](#文件说明)
- [安装依赖](#安装依赖)
- [使用方法](#使用方法)
- [技术细节](#技术细节)
- [数据格式说明](#数据格式说明)
- [异常处理](#异常处理)
- [性能优化](#性能优化)
- [常见问题](#常见问题)

## 🚀 功能特性

### 核心功能
- ✅ **完整数据获取流程**：从akshare获取A股历史数据
- ✅ **数据清洗和预处理**：缺失值处理、数据类型转换
- ✅ **特征工程**：计算技术指标和衍生特征
- ✅ **格式兼容**：与qlib数据格式完全一致
- ✅ **数据集分割**：训练集/验证集/测试集自动分割
- ✅ **异常处理**：完善的错误处理和重试机制
- ✅ **日志记录**：详细的处理日志和进度跟踪

### 技术优势
- 🔄 **与qlib兼容**：输出格式与qlib完全一致
- 📊 **数据质量保证**：多层数据验证和清洗
- ⚡ **高效处理**：批量处理和进度显示
- 🛡️ **稳定可靠**：完善的异常处理机制
- 📝 **详细注释**：每个关键步骤都有中文注释

## 📁 文件说明

### 主要文件

| 文件名 | 功能描述 | 使用场景 |
|--------|----------|----------|
| `akshare_data_preprocess.py` | 完整版数据预处理器 | 生产环境，完整数据处理 |
| `akshare_data_preprocess_simple.py` | 简化版数据预处理器 | 快速测试，原型开发 |
| `test_akshare_vs_qlib.py` | 数据对比测试工具 | 验证数据一致性 |
| `README_akshare.md` | 使用说明文档 | 学习和参考 |

### 输出文件

| 文件名 | 内容描述 | 格式 |
|--------|----------|------|
| `processed_data_akshare_simple.pkl` | 简化版处理结果 | pickle |
| `akshare/processed_datasets/train_data.pkl` | 训练集数据 | pickle |
| `akshare/processed_datasets/val_data.pkl` | 验证集数据 | pickle |
| `akshare/processed_datasets/test_data.pkl` | 测试集数据 | pickle |
| `akshare_data_preprocess.log` | 处理日志 | 文本 |

## 🔧 安装依赖

### 必需依赖

```bash
# 安装akshare
pip install akshare

# 安装其他依赖
pip install pandas numpy tqdm
```

### 可选依赖

```bash
# 如果需要对比qlib数据
pip install qlib
```

### 依赖版本建议

```
akshare >= 1.9.0
pandas >= 1.3.0
numpy >= 1.20.0
tqdm >= 4.60.0
```

## 🎯 使用方法

### 1. 快速开始（简化版）

```bash
# 运行简化版数据预处理
python akshare_data_preprocess_simple.py
```

**输出结果：**
- `processed_data_akshare_simple.pkl`：包含3个股票的处理结果
- 处理时间：约2-5分钟
- 数据范围：2020年1-3月

### 2. 完整数据处理

```bash
# 运行完整版数据预处理
python akshare_data_preprocess.py
```

**输出结果：**
- 训练集、验证集、测试集文件
- 完整的处理日志
- 数据范围：2010-2025年

### 3. 数据验证和对比

```bash
# 运行数据对比测试
python test_akshare_vs_qlib.py
```

**功能：**
- 验证数据格式一致性
- 对比akshare和qlib数据
- 生成详细对比报告

### 4. 自定义配置

#### 修改股票列表

```python
# 在akshare_data_preprocess.py中修改
self.instrument = ['600000', '600036', '600519']  # 自定义股票代码
```

#### 修改时间范围

```python
# 修改数据时间范围
self.dataset_begin_time = "2015-01-01"
self.dataset_end_time = "2023-12-31"
```

#### 修改特征列表

```python
# 修改输出特征
self.feature_list = ['open', 'high', 'low', 'close', 'vol', 'amt', 'vwap']
```

## 🔬 技术细节

### 数据获取流程

```python
# 1. 使用akshare获取股票数据
stock_data = ak.stock_zh_a_hist(
    symbol=symbol,           # 股票代码（如'600000'）
    period="daily",          # 日频数据
    start_date="20200101",   # 开始日期（YYYYMMDD格式）
    end_date="20201231",     # 结束日期（YYYYMMDD格式）
    adjust="qfq"             # 前复权处理
)
```

**akshare接口参数说明：**
- `symbol`: 股票代码，使用6位数字格式（如600000）
- `period`: 数据频率，"daily"表示日线数据
- `start_date/end_date`: 时间范围，必须使用YYYYMMDD格式
- `adjust`: 复权方式
  - `"qfq"`: 前复权，消除分红送股对价格的影响
  - `"hfq"`: 后复权
  - `""`: 不复权

### 数据转换逻辑

#### 1. 列名映射

```python
# akshare返回的中文列名 -> 标准英文列名
column_mapping = {
    '日期': 'datetime',    # 交易日期
    '开盘': 'open',        # 开盘价（元）
    '收盘': 'close',       # 收盘价（元）
    '最高': 'high',        # 最高价（元）
    '最低': 'low',         # 最低价（元）
    '成交量': 'volume',    # 成交量（手，1手=100股）
    '成交额': 'amount'     # 成交额（元）
}
```

#### 2. 衍生特征计算

```python
# vol特征：成交量
result_df['vol'] = result_df['volume']

# amt特征：成交额
if 'amount' in result_df.columns:
    # 直接使用akshare提供的成交额
    result_df['amt'] = result_df['amount']
else:
    # 使用OHLC均价估算成交额
    avg_price = (result_df['open'] + result_df['high'] + 
                result_df['low'] + result_df['close']) / 4
    result_df['amt'] = avg_price * result_df['vol']
```

**计算说明：**
- `vol`: 直接使用成交量数据
- `amt`: 优先使用akshare的成交额，如果没有则用OHLC均价乘以成交量估算
- 这种计算方式与qlib保持一致

#### 3. 数据清洗流程

```python
# 1. 缺失值处理
stock_df = stock_df.dropna()  # 删除包含NaN的行

# 2. 数据类型转换
numeric_columns = ['open', 'close', 'high', 'low', 'volume']
for col in numeric_columns:
    stock_df[col] = pd.to_numeric(stock_df[col], errors='coerce')

# 3. 数据长度验证
min_required_length = lookback_window + predict_window + 1
if len(stock_df) < min_required_length:
    # 跳过数据不足的股票
    continue
```

### 时间处理机制

#### 1. 缓冲时间计算

```python
# 向前扩展：为lookback_window提供足够历史数据
buffer_start = start_date - timedelta(days=lookback_window + 30)

# 向后扩展：为predict_window提供未来数据
buffer_end = end_date + timedelta(days=predict_window + 30)
```

#### 2. 数据集分割

```python
# 时间范围定义
train_time_range = ["2010-01-01", "2020-04-30"]  # 训练集
val_time_range = ["2020-05-01", "2020-05-31"]    # 验证集
test_time_range = ["2020-06-01", "2020-06-30"]   # 测试集

# 创建时间掩码
train_mask = (symbol_df.index >= train_start) & (symbol_df.index <= train_end)
val_mask = (symbol_df.index >= val_start) & (symbol_df.index <= val_end)
test_mask = (symbol_df.index >= test_start) & (symbol_df.index <= test_end)
```

## 📊 数据格式说明

### 输入数据格式（akshare原始数据）

```
列名：['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
数据类型：DataFrame
索引：整数索引
示例：
        日期    开盘    收盘    最高    最低   成交量        成交额
0  2020-01-02  12.20  12.05  12.25  11.98  1234567  1.52e+08
1  2020-01-03  12.05  12.15  12.30  12.00  1345678  1.63e+08
```

### 输出数据格式（处理后）

```
列名：['open', 'high', 'low', 'close', 'vol', 'amt']
数据类型：DataFrame
索引：DatetimeIndex
示例：
            open   high    low  close      vol         amt
datetime                                                  
2020-01-02  12.20  12.25  11.98  12.05  1234567  1.52e+08
2020-01-03  12.05  12.30  12.00  12.15  1345678  1.63e+08
```

### 保存格式

#### 简化版输出

```python
# processed_data_akshare_simple.pkl
[
    {
        'symbol': 'SH600000',
        'data': DataFrame  # 包含处理后的股票数据
    },
    {
        'symbol': 'SH600009', 
        'data': DataFrame
    },
    ...
]
```

#### 完整版输出

```python
# train_data.pkl, val_data.pkl, test_data.pkl
{
    'SH600000': DataFrame,  # 股票代码 -> 对应时间段的数据
    'SH600009': DataFrame,
    'SH600010': DataFrame,
    ...
}
```

## ⚠️ 异常处理

### 网络异常处理

```python
# 重试机制
for attempt in range(max_retries):
    try:
        stock_data = ak.stock_zh_a_hist(...)
        break  # 成功则跳出循环
    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(3)  # 等待3秒后重试
        else:
            logger.error(f"最终失败: {str(e)}")
            return None
```

### 数据质量检查

```python
# 1. 空数据检查
if stock_data is None or stock_data.empty:
    logger.warning(f"股票 {symbol} 返回空数据")
    return None

# 2. 必要列检查
required_columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量']
missing_cols = [col for col in required_columns if col not in stock_data.columns]
if missing_cols:
    logger.error(f"缺少必要列: {missing_cols}")
    return None

# 3. 数据长度检查
min_required_length = lookback_window + predict_window + 1
if len(stock_df) < min_required_length:
    logger.warning(f"数据长度不足: {len(stock_df)} < {min_required_length}")
    continue
```

### 常见错误及解决方案

| 错误类型 | 可能原因 | 解决方案 |
|----------|----------|----------|
| 网络连接超时 | 网络不稳定 | 增加重试次数，检查网络连接 |
| 股票代码无效 | 代码格式错误 | 使用6位数字格式（如600000） |
| 数据为空 | 时间范围无交易日 | 检查时间范围，避开节假日 |
| 内存不足 | 数据量过大 | 减少股票数量或缩短时间范围 |

## ⚡ 性能优化

### 1. 批量处理优化

```python
# 使用tqdm显示进度
for i in trange(len(symbol_list), desc="处理股票数据"):
    # 处理单个股票
    process_single_stock(symbol_list[i])
```

### 2. 内存管理

```python
# 及时释放不需要的数据
stock_df = stock_df.dropna()  # 清理缺失值
del original_data  # 删除原始数据引用
```

### 3. 缓存机制

```python
# 保存中间结果，避免重复计算
with open('intermediate_results.pkl', 'wb') as f:
    pickle.dump(processed_data, f)
```

### 性能基准

| 数据规模 | 处理时间 | 内存使用 |
|----------|----------|----------|
| 3股票×3个月 | 2-5分钟 | <500MB |
| 5股票×1年 | 5-10分钟 | <1GB |
| 10股票×5年 | 15-30分钟 | <2GB |

## ❓ 常见问题

### Q1: akshare数据获取失败怎么办？

**A:** 
1. 检查网络连接
2. 确认股票代码格式（6位数字）
3. 检查时间范围是否合理
4. 尝试减少并发请求

```python
# 测试akshare连接
import akshare as ak
test_data = ak.stock_zh_a_hist(symbol="600000", period="daily", 
                               start_date="20200101", end_date="20200110")
print(test_data.head())
```

### Q2: 数据格式与qlib不一致？

**A:** 
1. 检查特征列名是否正确
2. 确认时间索引格式
3. 验证数据类型转换

```python
# 验证数据格式
print("列名:", list(df.columns))
print("索引类型:", type(df.index))
print("数据类型:", df.dtypes)
```

### Q3: 处理速度太慢？

**A:** 
1. 减少股票数量
2. 缩短时间范围
3. 使用简化版处理器
4. 增加网络重试间隔

### Q4: 内存不足？

**A:** 
1. 分批处理股票
2. 及时释放内存
3. 使用更小的时间窗口

```python
# 分批处理示例
batch_size = 5
for i in range(0, len(symbols), batch_size):
    batch_symbols = symbols[i:i+batch_size]
    process_batch(batch_symbols)
```

### Q5: 如何添加新的技术指标？

**A:** 在`calculate_derived_features`方法中添加：

```python
def calculate_derived_features(self, df):
    result_df = df.copy()
    
    # 现有特征
    result_df['vol'] = result_df['volume']
    result_df['amt'] = ...
    
    # 新增技术指标
    result_df['ma5'] = result_df['close'].rolling(5).mean()  # 5日均线
    result_df['rsi'] = calculate_rsi(result_df['close'])     # RSI指标
    
    # 更新特征列表
    self.feature_list.extend(['ma5', 'rsi'])
    
    return result_df[self.feature_list]
```

## 📞 技术支持

如果遇到问题，请：

1. 查看日志文件：`akshare_data_preprocess.log`
2. 运行测试脚本：`python test_akshare_vs_qlib.py`
3. 检查依赖版本：`pip list | grep akshare`
4. 参考akshare官方文档：https://akshare.akfamily.xyz/

---

**注意事项：**
- akshare数据来源于公开市场，请遵守相关使用条款
- 建议在非交易时间进行大量数据获取
- 数据仅供研究和学习使用，投资有风险