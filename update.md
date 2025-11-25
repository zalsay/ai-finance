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
