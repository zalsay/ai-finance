import os, sys
import numpy as np
import pandas as pd

# 设置路径，确保可以导入 timesfm 源代码与数据预处理工具
current_dir = os.path.dirname(os.path.abspath(__file__))
timesfm_src = os.path.join(current_dir, "timesfm-2.5", "src")
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
akshare_tools_dir = os.path.join(root_dir, "akshare-tools")
preprocess_data_dir = os.path.join(root_dir, "preprocess-data")
sys.path.insert(0, timesfm_src)
sys.path.insert(0, akshare_tools_dir)
sys.path.insert(0, preprocess_data_dir)

from timesfm_2p5.configs import ForecastConfig
from timesfm_2p5.timesfm_2p5.timesfm_2p5_torch import TimesFM_2p5_200M_torch
from preprocess_timesfm_inputs import df_to_timesfm_inputs
runtime_api = os.environ.get("RUNTIME_API", "local")
model_dir = os.path.join(root_dir, "models", "timesfm-2.5-200m-pytorch")
if runtime_api == "docker":
    model_dir = os.path.join("/app", "timesfm-2.5-200m-pytorch")

weights_path = os.path.join(model_dir, "model.safetensors")
if not os.path.exists(weights_path):
    raise SystemExit(f"missing local model weights: {weights_path}")

initial_model = None
def init_model(
        max_context: int = 2048,
        max_horizon: int = 7,
        per_core_batch_size: int = 16,
        normalize_inputs: bool = False,
        return_backcast: bool = False,
    ):
    global initial_model
    if initial_model is not None:
        return initial_model
    model = TimesFM_2p5_200M_torch.from_pretrained(model_dir, local_files_only=True, force_download=False, token=None, torch_compile=True)
    fc = ForecastConfig(
        max_context=max_context,
        max_horizon=max_horizon,
        normalize_inputs=normalize_inputs,
        per_core_batch_size=per_core_batch_size,
        return_backcast=return_backcast,
    )
    model.compile(fc)
    initial_model = model
    return initial_model

def predict_2p5(
        df_train: pd.DataFrame,
        max_context: int = 2048,
        max_horizon: int = 7,
        pred_horizon: int = 7,
        per_core_batch_size: int = 16,
        normalize_inputs: bool = False,
        return_backcast: bool = False,
        unique_id: str = "",
    ) -> pd.DataFrame:

    model = init_model(
        max_context=max_context,
        max_horizon=max_horizon,
        per_core_batch_size=per_core_batch_size,
        normalize_inputs=normalize_inputs,
        return_backcast=return_backcast,
    )
    value_col = "close"
    inputs = df_to_timesfm_inputs(df_train, value_col=value_col, sort_by=["ds"], max_context=max_context)
    point_outputs, quantile_outputs = model.forecast(horizon=pred_horizon, inputs=inputs)
    out_df = pd.DataFrame({"t": np.arange(pred_horizon)})
    out_df["mtf"] = point_outputs[0]
    q = quantile_outputs[0]
    for i in range(q.shape[-1]):
        out_df[f"mtf-0.{i}"] = q[:, i]
    out_df["unique_id"] = unique_id
    return out_df

if __name__ == "__main__":
    import asyncio
    from run_timesfm_inference_pg import fetch_df

    symbol = "sh600398"
    start_date = "20100101"
    end_date = "20220927"
    pred_horizon = 7

    # 统一日期为服务所需的破折号格式
    start_dash = pd.Timestamp(start_date).strftime("%Y-%m-%d")
    end_dash = pd.Timestamp(end_date).strftime("%Y-%m-%d")

    df = asyncio.run(fetch_df(symbol, start_dash, end_dash))
    predict_2p5(df, pred_horizon=pred_horizon)
