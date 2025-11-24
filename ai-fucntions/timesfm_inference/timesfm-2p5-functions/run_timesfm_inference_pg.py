import os
import sys
import asyncio
import argparse
import numpy as np
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
timesfm_src = os.path.join(current_dir, "timesfm-2.5", "src")
root_dir = os.path.dirname(os.path.dirname(current_dir))
akshare_tools_dir = os.path.join(root_dir, "akshare-tools")
preprocess_data_dir = os.path.join(root_dir, "preprocess-data")
sys.path.insert(0, timesfm_src)
sys.path.insert(0, akshare_tools_dir)
sys.path.insert(0, preprocess_data_dir)

from preprocess_timesfm_inputs import df_to_timesfm_inputs
from postgres import PostgresHandler
from processor import df_preprocess
from timesfm.configs import ForecastConfig
from timesfm.timesfm_2p5.timesfm_2p5_torch import TimesFM_2p5_200M_torch

async def fetch_df(symbol: str, start_date: str, end_date: str, stock_type: int = 1) -> pd.DataFrame:
    async with PostgresHandler() as handler:
        df = await handler.ensure_date_range_df(symbol, start_date, end_date, stock_type=stock_type)
        return df

def run_timesfm_inference_pg(
        symbol: str,
        start_date: str,
        end_date: str,
        horizon: int,
        value_col: str,
        output_csv: str,
        stock_type: int = 1,
        max_context: int = 2048,
        max_horizon: int = 7,
        per_core_batch_size: int = 8,
        normalize_inputs: bool = False,
        return_backcast: bool = False,
    ) -> pd.DataFrame:
    # 统一日期为服务所需的破折号格式
    start_dash = pd.Timestamp(start_date).strftime("%Y-%m-%d")
    end_dash = pd.Timestamp(end_date).strftime("%Y-%m-%d")
    df = asyncio.run(fetch_df(symbol, start_dash, end_dash, stock_type))
    if df is None or df.empty:
        raise SystemExit("empty df")
    print(df.shape)
    inputs = df_to_timesfm_inputs(df, value_col=value_col, sort_by=["datetime"], max_context=max_context)


    model_dir = os.path.join(root_dir, "timesfm", "timesfm-2.5-200m-pytorch")
    weights_path = os.path.join(model_dir, "model.safetensors")
    if not os.path.exists(weights_path):
        raise SystemExit(f"missing local model weights: {weights_path}")
    model = TimesFM_2p5_200M_torch.from_pretrained(model_dir, local_files_only=True, force_download=False, token=None, torch_compile=True)
    fc = ForecastConfig(
        max_context=max_context,
        max_horizon=max_horizon,
        normalize_inputs=normalize_inputs,
        per_core_batch_size=per_core_batch_size,
        return_backcast=return_backcast,
    )
    model.compile(fc)
    point_outputs, quantile_outputs = model.forecast(horizon=horizon, inputs=inputs)

    out_df = pd.DataFrame({"t": np.arange(horizon)})
    out_df["point"] = point_outputs[0]
    q = quantile_outputs[0]
    for i in range(q.shape[-1]):
        out_df[f"q_{i}"] = q[:, i]

    out_df.to_csv(output_csv, index=False)
    print(output_csv)
    try:
        actual_series = df.sort_values("datetime")[value_col].astype("float32")
        if len(actual_series) >= horizon:
            actual_tail = actual_series.iloc[-horizon:].to_numpy()
            mse_list = []
            mae_list = []
            combined_list = []
            indices = list(range(q.shape[-1]))
            for idx in indices:
                preds = q[:, idx]
                mse = float(np.mean((preds - actual_tail) ** 2))
                mae = float(np.mean(np.abs(preds - actual_tail)))
                mse_list.append(mse)
                mae_list.append(mae)
                combined_list.append(0.5 * mse + 0.5 * mae)
            best_idx = int(np.argmin(combined_list))
            print(f"best_quantile_index={best_idx}")
            print(f"best_mse={mse_list[best_idx]:.6f}")
            print(f"best_mae={mae_list[best_idx]:.6f}")
            print(f"best_combined_score={combined_list[best_idx]:.6f}")
    except Exception:
        pass
    return out_df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", help="股票代码，如 600398 或 sh600398（与服务一致）")
    parser.add_argument("start_date", help="开始日期，如 2024-01-01 或 20240101")
    parser.add_argument("end_date", help="结束日期，如 2024-12-31 或 20241231")
    parser.add_argument("horizon", type=int)
    parser.add_argument("value_col")
    parser.add_argument("output_csv")
    parser.add_argument("--stock_type", type=int, default=1)
    parser.add_argument("--max_context", type=int, default=2048)
    parser.add_argument("--max_horizon", type=int, default=7)
    parser.add_argument("--per_core_batch_size", type=int, default=8)
    parser.add_argument("--normalize_inputs", action="store_true")
    parser.add_argument("--return_backcast", action="store_true")
    parser.add_argument("--use_demo", action="store_true")
    parser.add_argument("--no_weights", nargs='?', const=True, type=lambda s: s.lower() in ("1","true","t","y","yes"), default=True)
    args = parser.parse_args()

    run_timesfm_inference_pg(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        horizon=args.horizon,
        value_col=args.value_col,
        output_csv=args.output_csv,
        stock_type=args.stock_type,
        max_context=args.max_context,
        max_horizon=args.max_horizon,
        per_core_batch_size=args.per_core_batch_size,
        normalize_inputs=args.normalize_inputs,
        return_backcast=args.return_backcast,
    )

def test():
    df = run_timesfm_inference_pg(
        symbol="sh600398",
        start_date="20100101",
        end_date="20220927",
        horizon=7,
        value_col="close",
        output_csv="test.csv",

    )
    print(df)
if __name__ == "__main__":
    test()