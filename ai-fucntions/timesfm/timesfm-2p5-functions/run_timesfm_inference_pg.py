import os
import sys
import asyncio
import argparse
import numpy as np
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
timesfm_src = os.path.join(current_dir, "timesfm", "src")
root_dir = os.path.dirname(os.path.dirname(current_dir))
akshare_tools_dir = os.path.join(root_dir, "akshare-tools")
sys.path.append(timesfm_src)
sys.path.append(akshare_tools_dir)

from preprocess_timesfm_inputs import df_to_timesfm_inputs
from postgres import PostgresHandler

async def fetch_df(symbol: str, start_date: str, end_date: str, stock_type: int) -> pd.DataFrame:
    async with PostgresHandler(base_url="http://8.163.5.7:8000", api_token="fintrack-dev-token") as handler:
        df = await handler.get_by_date_range_df(symbol, start_date, end_date, stock_type=stock_type)
        return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("start_date")
    parser.add_argument("end_date")
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
    parser.add_argument("--no_weights", nargs='?', const=True, type=lambda s: s.lower() in ("1","true","t","y","yes"), default=False)
    args = parser.parse_args()

    if args.use_demo:
        df = pd.DataFrame({"datetime": pd.date_range(args.start_date, periods=512, freq="D"), args.value_col: np.random.randn(512).astype("float32")})
    else:
        df = asyncio.run(fetch_df(args.symbol, args.start_date, args.end_date, args.stock_type))
        if df is None or df.empty:
            raise SystemExit("empty df")

    inputs = df_to_timesfm_inputs(df, value_col=args.value_col, sort_by=["datetime"], max_context=args.max_context)

    if args.no_weights:
        base = inputs[0].astype("float32")
        mu = float(np.nanmean(base)) if np.isnan(base).any() else float(base.mean())
        pf = np.full((args.horizon,), mu, dtype="float32")
        qs = np.stack([pf for _ in range(10)], axis=-1)
        point_outputs = [pf]
        quantile_outputs = [qs]
    else:
        from timesfm import ForecastConfig
        from timesfm.timesfm_2p5.timesfm_2p5_torch import TimesFM_2p5_200M_torch
        model = TimesFM_2p5_200M_torch.from_pretrained("/Users/sisu/Documents/code/ai-finance/ai-fucntions/timesfm/timesfm-2.5-200m-pytorch")
        fc = ForecastConfig(
            max_context=args.max_context,
            max_horizon=args.max_horizon,
            normalize_inputs=args.normalize_inputs,
            per_core_batch_size=args.per_core_batch_size,
            return_backcast=args.return_backcast,
        )
        model.compile(fc)
        point_outputs, quantile_outputs = model.forecast(horizon=args.horizon, inputs=inputs)

    out_df = pd.DataFrame({"t": np.arange(args.horizon)})
    out_df["point"] = point_outputs[0]
    q = quantile_outputs[0]
    for i in range(q.shape[-1]):
        out_df[f"q_{i}"] = q[:, i]
    out_df.to_csv(args.output_csv, index=False)
    print(args.output_csv)

if __name__ == "__main__":
    main()