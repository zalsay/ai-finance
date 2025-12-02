# 更新记录

## 2025-11-25

### 主要更新

1. **图表输出功能增强**
   - 文件: `/Users/yingzhang/Documents/dev/ai-finance/ai-fucntions/preprocess_data/plot_functions.py`
   - 修改内容: 更新 `plot_chunked_prediction_results` 函数，支持显示最佳预测项和验证集结果
   - 功能特点:
     - 双面板布局：上部分显示预测结果图表，下部分显示详细指标表格
     - 显示最佳预测项信息（tsf-0.X）及其性能指标
     - 显示验证集验证结果
     - 包含总体指标、最佳预测项指标和验证集指标

2. **预测功能优化**
   - 文件: `/Users/yingzhang/Documents/dev/ai-finance/ai-fucntions/timesfm_inference/predict_chunked_functions.py`
   - 修改内容: 完善 `predict_chunked_mode_for_best` 函数
   - 功能特点:
     - 实现测试集分块预测
     - 移除对 request.chunk_num 的依赖，分块数量根据测试集和验证集长度自动计算
     - 统一验证集和测试集的分块数据处理方式，使用相同的数据平移策略
     - 验证集现在使用训练集+测试集+验证集的前history_len行数据，与测试集处理方式保持一致
     - 收集 tsf-0.1 到 tsf-0.9 所有预测结果
     - 基于综合评分（MSE 0.6, MAE 0.2, 涨跌幅差异 0.2）选择最佳预测项
      - 在验证集上验证最佳预测项性能
      - 拼接结果阶段增加日期校验，跳过无效日期或空分块，避免 `NaT` 导致的异常
      - 打印分块详情时为缺失的 `best_diff_pct` 提供默认值，避免 `KeyError`
      - 绘图阶段对日期与分块边界使用 `errors='coerce'` 并过滤 `NaT`，避免 Matplotlib 轴转换错误

3. **数据预处理优化**
   - 文件: `/Users/yingzhang/Documents/dev/ai-finance/ai-fucntions/preprocess_data/processor.py`
   - 修改内容: 将数据分割比例从 80% 训练改为 7:2:1 的训练/测试/验证集分割
   - 功能特点:
     - 确保所有分割都是 horizon_len 的倍数
     - 添加验证集处理逻辑

### 技术细节

- **最佳预测项选择**: 使用加权综合评分算法，权重分配为 MSE(0.6) + MAE(0.2) + 涨跌幅差异(0.2)
- **验证集验证**: 使用最佳预测项在验证集上进行分块预测验证
- **图表输出**: 生成包含预测曲线和详细指标表格的综合图表
- **错误处理**: 完善异常处理和边界条件检查

### 文件修改

- `plot_functions.py`: 重写图表生成函数，支持双面板布局和详细指标显示
- `predict_chunked_functions.py`: 添加最佳预测项选择和验证集验证逻辑
- `processor.py`: 更新数据分割逻辑，支持验证集
- `req_res_types.py`: 扩展响应数据结构，支持最佳预测项和验证结果信息

### 使用说明

运行预测功能后，系统将自动:
1. 在测试集上进行分块预测
2. 分析所有 tsf-0.X 预测项的性能
3. 选择综合评分最佳的项目
4. 在验证集上验证最佳预测项
5. 生成包含所有结果的综合图表

图表保存路径: `finance_dir/forecast-results/{stock_code}_chunked_prediction_plot.png`

## 2025-12-02

### 主要更新

1. 添加最大似然估计（MLE）参考值
   - 文件: `/Users/yingzhang/Documents/dev/ai-finance/ai-fucntions/timesfm_inference/predict_chunked_functions.py`
   - 位置: `predict_single_chunk_mode1` 函数（`ai-fucntions/timesfm_inference/predict_chunked_functions.py:42`）
   - 修改内容: 在分块预测的 `metrics` 中新增 `mle` 字段
   - 计算方法: 基于预测均值列 `mtf` 与实际值的残差，按正态假设估计 σ 的 MLE（`mle = sqrt(mean((y - mtf)^2))`）

2. 为每个分位数增加似然参考值
   - 文件: `/Users/yingzhang/Documents/dev/ai-finance/ai-fucntions/timesfm_inference/predict_chunked_functions.py`
   - 位置: 分位数评估循环（`ai-fucntions/timesfm_inference/predict_chunked_functions.py:143-165`）
   - 修改内容: 在 `quantile_metrics[q]` 中新增 `mle`（基于该分位数残差的 σ MLE）与 `avg_nll`（平均负对数似然）字段
   - 计算方法: `mle = sqrt(mean((y - q)^2))`；`avg_nll = 0.5 * mean(log(2πσ²) + (residual²)/σ²)`
   - 最佳分位聚合：在总体最佳分位评分处，使用每个分位的 `mle` 取平均作为 `avg_mle`，并将其纳入综合评分，位置 `ai-fucntions/timesfm_inference/predict_chunked_functions.py:444-461`

3. 将PG写入逻辑统一重构到 PostgresHandler
   - 新增类: `/Users/yingzhang/Documents/dev/ai-finance/ai-fucntions/akshare-tools/postgres.py` 中的 `PostgresHandler`
   - 新增方法: `save_best_prediction(payload)` 与 `save_best_val_chunk(payload)`，封装对 Go 后端的写入
   - 引用位置:
     - 最佳分位保存：`ai-fucntions/timesfm_inference/predict_chunked_functions.py:585-638` 重写为使用 `PostgresHandler`
     - 验证分块写入：`ai-fucntions/timesfm_inference/predict_chunked_functions.py:640-719` 重写为使用 `PostgresHandler`
   - 好处: 统一鉴权与基础通信逻辑、便于维护和复用

### 技术细节

- 当存在 `mtf` 列时计算 MLE；若不存在或长度为 0，则 `mle` 为 `None`
- 该值可作为误差尺度的参考，用于与 `MSE/MAE` 一同评估预测质量
 - 分位数的 `mle`/`avg_nll` 与各自的预测值和残差匹配，便于细粒度比较

### 验证

- 已执行 Python 语法检查：`python -m py_compile ai-fucntions/timesfm_inference/predict_chunked_functions.py`
- 结果：通过
4. 绘图表格增加指标
   - 在绘图函数的下方表格中新增展示：`mle` 与 `composite_score`
   - 代码位置：`ai-fucntions/preprocess_data/plot_functions.py:196-203`
   - 来源：最佳分位指标来自 `predict_chunked_functions.py:481-482`
5. 优化PG写入对象生命周期
   - 在 `predict_chunked_mode_for_best` 中，将 `PostgresHandler` 在保存阶段开始时初始化，并在最佳分位保存与验证分块写入间复用，避免在循环中重复创建
   - 代码位置：
     - 初始化与复用：`ai-fucntions/timesfm_inference/predict_chunked_functions.py:572-575`
     - 替换最佳保存调用：`ai-fucntions/timesfm_inference/predict_chunked_functions.py:626-631`
     - 替换验证分块调用：`ai-fucntions/timesfm_inference/predict_chunked_functions.py:698-699`
     - 关闭对象：`ai-fucntions/timesfm_inference/predict_chunked_functions.py:713-716`
6. 验证方法抽取与复用
   - 将验证集计算逻辑在 `predict_validation_chunks_only` 中对齐主流程：收益差基于训练集最后一条收盘价计算，避免与主流程不一致
   - 新增参数：`persist_best`、`persist_val_chunks` 控制仅验证模式下的PG持久化行为，并改为统一使用 `PostgresHandler`
   - 在 `predict_chunked_mode_for_best` 中删除内联验证流程，改为调用 `predict_validation_chunks_only` 完成验证与持久化
   - 代码位置：
     - 验证函数签名与逻辑：`ai-fucntions/timesfm_inference/predict_chunked_functions.py:706-971`
     - 主流程调用替换：`ai-fucntions/timesfm_inference/predict_chunked_functions.py:496-516`
7. 验证集增加MLE指标
   - 在 `validation_results` 中新增 `validation_mle`，计算方法为各验证分块残差的 `sigma_hat` 平均值（`sqrt(mean(residual^2))`）
   - 代码位置：`ai-fucntions/timesfm_inference/predict_chunked_functions.py:900-927`
8. 绘图表格增加验证MLE
   - 在绘图表格的验证结果部分新增 `Validation MLE` 行，展示 `validation_results.validation_mle`
   - 代码位置：`ai-fucntions/preprocess_data/plot_functions.py:205-212`
9. 回测保存合并到 PostgresHandler
   - 新增方法：`save_backtest_result(payload)`，封装回测结果写入 `/api/v1/save-predictions/backtest`
   - 调用替换：`timesfm_inference/exchange_server.py:762` 的 `save_backtest_result_to_pg` 现在使用 `PostgresHandler.save_backtest_result`
   - 引入路径：`exchange_server.py` 顶部增加 `akshare-tools` 路径并导入 `PostgresHandler`
10. 修复回测写库JSON类型不匹配
   - Go端期望 `per_chunk_signals` 为对象(map)，原实现发送数组导致 `Invalid JSON`
   - 将列表转换为以 `chunk_index` 为键的字典后再发送
   - 代码位置：`ai-fucntions/timesfm_inference/exchange_server.py:770-788`
11. 回测写库统一保留四位小数
   - 所有浮点字段与数组元素保留四位小数（不转成字符串），并递归处理字典/数组
   - 代码位置：`ai-fucntions/timesfm_inference/exchange_server.py:779-816`
12. 回测写库的交易明细保留四位小数
   - 将 `trades` 列表递归处理为四位小数，保证价格等字段一致格式
   - 代码位置：`ai-fucntions/timesfm_inference/exchange_server.py:827-829`
