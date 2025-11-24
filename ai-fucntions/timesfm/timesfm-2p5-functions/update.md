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