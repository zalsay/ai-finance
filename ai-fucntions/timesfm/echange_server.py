import os
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
finance_dir = parent_dir
sys.path.append(finance_dir)

from timesfm.timesfm_init import init_timesfm
from timesfm.predict_chunked_functions import predict_chunked_mode1
from timesfm.req_res_types import ChunkedPredictionRequest, ChunkedPredictionResponse, ChunkPredictionResult

@dataclass
class BacktestTrade:
    date: str
    action: str
    price: float
    size: float
    chunk_index: int
    reason: str

def _select_closest_pct_quantile(chunk_result: ChunkPredictionResult) -> Optional[str]:
    if not chunk_result.actual_values or not chunk_result.predictions:
        return None
    start_actual = chunk_result.actual_values[0]
    actual_pct = [((v / start_actual) - 1) * 100 if start_actual != 0 else 0 for v in chunk_result.actual_values]
    best_mae = float('inf')
    best_key = None
    for i in range(1, 10):
        key = f"timesfm-q-0.{i}"
        if key in chunk_result.predictions:
            pred_values = chunk_result.predictions[key]
            if len(pred_values) != len(actual_pct):
                continue
            pred_pct = [((v / start_actual) - 1) * 100 if start_actual != 0 else 0 for v in pred_values]
            mae_val = np.mean(np.abs(np.array(pred_pct) - np.array(actual_pct)))
            if mae_val < best_mae:
                best_mae = mae_val
                best_key = key
    return best_key

def backtest_from_chunked_response(response: ChunkedPredictionResponse, buy_threshold_pct: float = 10.0, sell_threshold_pct: float = -3.0, initial_cash: float = 100000.0) -> Dict[str, Any]:
    cash = initial_cash
    shares = 0.0
    trades: List[BacktestTrade] = []
    last_price = None
    for cr in response.chunk_results:
        if not cr.actual_values:
            continue
        start_price = cr.actual_values[0]
        if start_price is None or np.isnan(start_price):
            continue
        best_key = _select_closest_pct_quantile(cr)
        if not best_key:
            continue
        pred_values = cr.predictions.get(best_key, [])
        if not pred_values:
            continue
        predicted_pct_change = ((pred_values[-1] / start_price) - 1) * 100 if start_price != 0 else 0
        if predicted_pct_change >= buy_threshold_pct and shares == 0.0:
            size = cash / start_price
            shares += size
            cash -= size * start_price
            trades.append(BacktestTrade(date=cr.chunk_start_date, action="buy", price=float(start_price), size=float(size), chunk_index=cr.chunk_index, reason=f"pred_pct>={buy_threshold_pct}"))
        elif predicted_pct_change <= sell_threshold_pct and shares > 0.0:
            cash += shares * start_price
            trades.append(BacktestTrade(date=cr.chunk_start_date, action="sell", price=float(start_price), size=float(shares), chunk_index=cr.chunk_index, reason=f"pred_pct<={sell_threshold_pct}"))
            shares = 0.0
        last_price = cr.actual_values[-1]
    final_value = cash + (shares * last_price if last_price is not None else 0.0)
    total_return = (final_value / initial_cash - 1) * 100
    if response.concatenated_dates and len(response.concatenated_dates) > 1:
        start = pd.to_datetime(response.concatenated_dates[0])
        end = pd.to_datetime(response.concatenated_dates[-1])
    else:
        if response.chunk_results:
            start = pd.to_datetime(response.chunk_results[0].chunk_start_date)
            end = pd.to_datetime(response.chunk_results[-1].chunk_end_date)
        else:
            start = pd.to_datetime("1970-01-01")
            end = pd.to_datetime("1970-01-02")
    days = max((end - start).days, 1)
    annualized = ((final_value / initial_cash) ** (365.0 / days) - 1) * 100
    return {
        "initial_cash": initial_cash,
        "final_value": final_value,
        "total_return_pct": total_return,
        "annualized_return_pct": annualized,
        "trades": [trade.__dict__ for trade in trades],
        "buy_threshold_pct": buy_threshold_pct,
        "sell_threshold_pct": sell_threshold_pct
    }

def run_backtest(request: ChunkedPredictionRequest, buy_threshold_pct: float = 10.0, sell_threshold_pct: float = -3.0, initial_cash: float = 100000.0) -> Dict[str, Any]:
    tfm = init_timesfm(horizon_len=request.horizon_len, context_len=request.context_len)
    response = predict_chunked_mode1(request, tfm)
    result = backtest_from_chunked_response(response, buy_threshold_pct=buy_threshold_pct, sell_threshold_pct=sell_threshold_pct, initial_cash=initial_cash)
    return {
        "response": response,
        "backtest": result
    }