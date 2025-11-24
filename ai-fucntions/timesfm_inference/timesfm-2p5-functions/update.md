# 更新记录

日期：2025-11-24

- 修复在 Apple MPS 后端下的 dtype/device 转换顺序问题，避免 `float64` 转换报错。
- 变更位置：`timesfm-2.5/src/timesfm/timesfm_2p5/timesfm_2p5_torch.py:402-404`
- 具体修改：先将 `inputs`/`masks` 在 NumPy 层面强制为 `float32`/`bool`，并在转换为 `torch.Tensor` 后先设定 `dtype` 再迁移到 `device`。这样可保证在将张量移动到 `mps` 设备时不会触发不支持 `float64` 的错误。
- 影响范围：TimesFM 2.5 Torch 推理路径的 `compiled_decode`。

验证：本地环境缺少 Python 依赖（`numpy` 等），无法直接运行脚本验证。建议在装好依赖后运行：

```bash
python3 ai-finance/ai-fucntions/timesfm/timesfm-2p5-functions/run_timesfm_inference_pg.py
```

预期：不再出现 `MPS Tensor to float64` 的类型错误，推理正常返回结果。

——

日期：2025-11-24

- 修复 `inference.py` 导入路径设置在模块导入之后的问题，导致 `ModuleNotFoundError: timesfm.configs`。
- 变更位置：`timesfm-2p5-functions/inference.py`
- 具体修改：将 `sys.path.insert(...)` 的路径注入提前到文件顶部，并在此之后导入 `timesfm.configs` 与 `timesfm.timesfm_2p5.timesfm_2p5_torch`。同时修复主函数中日期变量的定义顺序，避免未定义变量被使用。
- 验证：当前环境缺少 `numpy` 等依赖，无法直接运行。请先安装依赖后再执行：

```bash
python3 -m pip install numpy pandas torch safetensors huggingface_hub
python3 ai-finance/ai-fucntions/timesfm/timesfm-2p5-functions/inference.py
```

——

日期：2025-11-24

- 修复 `timesfm_inference/timesfm_init.py` 使用旧版 `timesfm.TimesFm` 类型注解导致导入失败的问题。
- 替换初始化逻辑为 TimesFM 2.5 PyTorch：基于 `ForecastConfig` 与 `TimesFM_2p5_200M_torch`，按 `horizon_len/context_len` 缓存已编译模型。
- 更新 `timesfm_inference/predict_chunked_functions.py` 的示例运行为 `timesfm_version="2.5"`，并在 2.5 路径下不再依赖旧版 `forecast_on_df` 接口。
- 验证：需要安装 Python 依赖后运行脚本。
