# TimesFM 2.5 使用文档（中文）

## 概述
TimesFM 2.5 是一个面向时间序列预测的模型与工具集，提供：
- 框架无关的模型结构定义与预处理工具
- PyTorch 与 Flax/JAX 的两套实现
- 基于外生协变量的线性回归融合（XReg），支持两种组合模式
- 简洁的公共 API 与检查点加载/编译/推理流程

核心文件与模块：
- 抽象基类：`timesfm/src/timesfm/timesfm_2p5/timesfm_2p5_base.py`
- PyTorch 实现：`timesfm/src/timesfm/timesfm_2p5/timesfm_2p5_torch.py`
- Flax/JAX 实现：`timesfm/src/timesfm/timesfm_2p5/timesfm_2p5_flax.py`
- 配置定义：`timesfm/src/timesfm/configs.py`
- 协变量工具：`timesfm/src/timesfm/utils/xreg_lib.py`
- 包入口：`timesfm/src/timesfm/__init__.py`

---

## 安装
建议使用 `uv` 或 `pip` 安装依赖，根据你选择的后端：

- 仅使用 Torch（推荐）：
  - `uv pip install torch numpy`
- 使用 Flax/JAX（需要 JAX 生态，适合 TPU/GPU 研究型环境）：
  - `uv pip install jax jaxlib numpy`
- 使用外生协变量（XReg）工具：
  - `uv pip install scikit-learn`

如不使用 `uv`，将命令中的 `uv pip` 替换为 `pip` 即可。

---

## 快速开始（PyTorch）
```python
from timesfm import ForecastConfig
from timesfm import TimesFM_2p5_200M_torch  # 依赖已安装时自动导出

# 1) 创建模型实例（200M 参数版本）
model = TimesFM_2p5_200M_torch()

# 2) 从本地或 Hugging Face Hub 加载权重
#   - 本地 safetensors 路径
# model.load_checkpoint("/path/to/model.safetensors")
#   - 或从 HF 仓库加载
model = TimesFM_2p5_200M_torch.from_pretrained("your-org/timesfm-2p5-200m")

# 3) 编译：配置可控的推理参数
fc = ForecastConfig(
    max_context=16384,       # 上下文最大长度（会按 patch 对齐）
    max_horizon=256,         # 预测步长（会按 patch 对齐且受上限约束）
    per_core_batch_size=8,   # 每设备批量大小（影响 global_batch_size）
    return_backcast=False    # 如需 XReg，必须设置为 True
)
model.compile(fc)

# 4) 推理：输入为 list[np.ndarray]，每条为一个时间序列上下文
inputs = [
    # 示例：一条长度为 100 的上下文
    # 缺失值（NaN）会在内部预处理（见下文）
    # 注意：每条数据类型必须可转为 np.ndarray
    np.random.randn(100).astype("float32")
]

# 预测 horizon=128 步
point_outputs, quantile_outputs = model.forecast(horizon=128, inputs=inputs)

# 结果：
# - point_outputs: 形如 [batch, horizon]
# - quantile_outputs: 形如 [batch, horizon, num_quantiles]（由模型配置决定）
```

---

## 快速开始（Flax/JAX）
```python
from timesfm import ForecastConfig
from timesfm import TimesFM_2p5_200M_flax  # 依赖已安装时自动导出
import numpy as np

model = TimesFM_2p5_200M_flax()
model = TimesFM_2p5_200M_flax.from_pretrained("your-org/timesfm-2p5-200m")

fc = ForecastConfig(
    max_context=16384,
    max_horizon=256,
    per_core_batch_size=8,
    return_backcast=False,
)
model.compile(fc)

inputs = [np.random.randn(100).astype("float32")]
point_outputs, quantile_outputs = model.forecast(horizon=128, inputs=inputs)
```

---

## 编译与配置
`ForecastConfig` 是推理编译的关键参数，常用字段：
- `max_context`：最大上下文长度，超过时会自动截断；不足时会左侧零填充并生成掩码
- `max_horizon`：最大可预测步长；超出或不对齐时会被约束/对齐
- `per_core_batch_size`：每设备批量大小；用于推导 `global_batch_size`
- `return_backcast`：是否返回反向回放（backcast）；如需 XReg，必须打开

对齐与上限：
- 编译时会对 `max_context` 和 `max_horizon` 进行 patch 对齐（由 `input_patch_len`、`output_patch_len` 决定）
- `TimesFM_2p5_200M_Definition` 指定了默认结构参数（20 层 Transformer、维度配置、量化头等）

---

## 预测接口
- `forecast(horizon: int, inputs: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]`
  - 需先 `compile()`，否则报错
  - 自动补齐批次到 `global_batch_size` 的倍数（内部对齐，不影响最终输出截取）
  - 缺失值处理与掩码生成在内部进行（见下文）
  - 返回：
    - 点预测 `point_outputs`：形如 `[batch, horizon]`
    - 分位数预测 `quantile_outputs`：形如 `[batch, horizon, num_quantiles]`

- `forecast_with_covariates(...)`
  - 需 `forecast_config.return_backcast == True`，否则报错
  - 支持两种模式：
    - `"timesfm + xreg"`：先 TimesFM 预测，再对残差拟合线性模型并融合
    - `"xreg + timesfm"`：先在线性模型上拟合目标，再对残差进行 TimesFM 预测并融合
  - 输入：
    - `inputs`: 基础时间序列上下文列表
    - `dynamic_numerical_covariates` / `dynamic_categorical_covariates`: 动态协变量
    - `static_numerical_covariates` / `static_categorical_covariates`: 静态协变量
  - 自动将协变量按 train/test 切分，并进行可选归一化与反归一化
  - 返回：
    - `new_point_outputs, new_quantile_outputs`：已融合协变量后的结果

---

## 输入与预处理
`timesfm_2p5_base.py` 提供两个关键预处理工具：
- `strip_leading_nans(arr)`：去除序列前部连续的 `NaN`
- `linear_interpolation(arr)`：对 1D 数组内的 `NaN` 进行线性插值；如插值失败，使用均值或 0 替换

在 `forecast()` 中：
- 对每条输入先应用上述预处理
- 若长度超过 `context`（由 `forecast_config.max_context` 定义），截取末尾 `context` 长度
- 若长度不足，左侧零填充，并生成 `mask` 指示填充段（`True`）与真实段（`False`）

---

## 协变量（XReg）
`utils/xreg_lib.py` 提供批量情境线性回归：
- 模式：
  - `"timesfm + xreg"`：对 TimesFM 残差做线性回归，回写至点/分位数输出
  - `"xreg + timesfm"`：先拟合目标再对残差做 TimesFM 预测
- 归一化：
  - `normalize_xreg_target_per_input=True` 时，对每条输入单独归一化，返回时自动反归一化
- 依赖：
  - 需要 `scikit-learn`、`numpy`；Flax/JAX 环境下某些工具使用 JAX

示例（TimesFM + XReg）：
```python
from timesfm import ForecastConfig, TimesFM_2p5_200M_torch
import numpy as np

model = TimesFM_2p5_200M_torch.from_pretrained("your-org/timesfm-2p5-200m")
fc = ForecastConfig(max_context=16384, max_horizon=256, per_core_batch_size=8, return_backcast=True)
model.compile(fc)

inputs = [np.random.randn(300).astype("float32")]
dynamic_numerical_covariates = {"temp": [np.random.randn(300 + 128).astype("float32")]}

new_point, new_quantiles = model.forecast_with_covariates(
    inputs=inputs,
    dynamic_numerical_covariates=dynamic_numerical_covariates,
    xreg_mode="timesfm + xreg",
    normalize_xreg_target_per_input=True,
    ridge=0.0,
)
```

---

## 检查点与模型仓库
- 本地加载：
  - `model.load_checkpoint("/path/to/model.safetensors")`
- Hugging Face Hub：
  - `model = TimesFM_2p5_200M_torch.from_pretrained("org/repo")`
- 保存：
  - `model.save_pretrained("./export-dir")`（如类集成了 Hub Mixin）

---

## 性能与设备
- `global_batch_size`：由 `per_core_batch_size` 与设备数量推导（编译时计算）
- 设备：
  - Torch：`model.to(device)`；可选 `torch.compile(...)` 加速
  - Flax/JAX：使用 NNX、Orbax 管理设备与检查点
- Patch 对齐：
  - `input_patch_len=32`、`output_patch_len=128`，编译时会对齐 `max_context`、`max_horizon`

---

## 常见问题
- 报错 “Model is not compiled”：请先调用 `model.compile(forecast_config)`
- 协变量模式报错：
  - “return_backcast must be set to True”：请将 `ForecastConfig.return_backcast=True`
  - 动态协变量长度需覆盖 `input_len + horizon`，否则会触发长度检查错误
- 超出 `max_horizon` 或未对齐：
  - 编译时已做约束与对齐；请调整 `horizon` 或 `ForecastConfig.max_horizon`
- 依赖缺失：
  - Torch 版：`torch`、`numpy`
  - Flax/JAX 版：`jax`、`jaxlib`、`numpy`
  - XReg：`scikit-learn`

---

## 参考路径
- 抽象基类与预处理：`timesfm/src/timesfm/timesfm_2p5/timesfm_2p5_base.py`
- 配置定义：`timesfm/src/timesfm/configs.py`
- Torch 实现：`timesfm/src/timesfm/timesfm_2p5/timesfm_2p5_torch.py`
- Flax/JAX 实现：`timesfm/src/timesfm/timesfm_2p5/timesfm_2p5_flax.py`
- 协变量工具：`timesfm/src/timesfm/utils/xreg_lib.py`
- 公共 API：`timesfm/src/timesfm/__init__.py`
- 2.5 总览文档：`timesfm/README.md`

---

## 附：与 `timesfm_2p5_base.py` 直接相关的要点
- 模型定义：`TimesFM_2p5_200M_Definition` 指定上下文限制、patch 长度、量化分位等
- 预处理：`strip_leading_nans` 与 `linear_interpolation` 保障输入的可用性
- 掩码与填充：短序列左侧零填充，并自动生成掩码以指示填充位
- 编译前置：`forecast`/`forecast_with_covariates` 调用前必须完成 `compile`
- XReg 前置：`forecast_with_covariates` 需开启 `return_backcast`，并至少提供一种协变量类型