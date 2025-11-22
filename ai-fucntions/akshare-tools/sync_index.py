#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
同步指数基础信息与每日行情到 Go API

依赖：
- akshare
- requests

环境变量：
- GO_API_URL (默认 http://localhost:8080)
- API_TOKEN (默认 fintrack-dev-token)

示例：
python sync_index.py --sync-info --codes 000001,399001
python sync_index.py --sync-daily --codes 000001 --start-date 2025-11-01 --end-date 2025-11-22
"""

import os
import sys
import json
import time
from typing import List, Optional

import requests
import akshare as ak


GO_API_URL = os.environ.get("GO_API_URL", "http://localhost:8080")
API_TOKEN = os.environ.get("API_TOKEN", "fintrack-dev-token")


def _post(path: str, payload):
    url = GO_API_URL.rstrip("/") + path
    headers = {
        "Content-Type": "application/json",
        "X-Token": API_TOKEN,
    }
    resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def normalize_date_str(s: str) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip()
    # 支持 "1991/7/15" 或 "1991-07-15" 或 pandas.Timestamp
    try:
        import pandas as pd
        if isinstance(s, pd.Timestamp):
            return s.strftime("%Y-%m-%d")
    except Exception:
        pass
    s = s.replace("/", "-")
    parts = s.split("-")
    if len(parts) == 3:
        y = parts[0]
        m = parts[1].zfill(2)
        d = parts[2].zfill(2)
        return f"{y}-{m}-{d}"
    return s


def upsert_index_info_by_codes(codes: List[str] = None) -> int:
    """将指定 codes 的指数基础信息写入 Go API"""
    df = ak.index_stock_info()
    if df is None or df.empty:
        print("index_stock_info: empty")
        return 0
    # 兼容列名
    cols = set(df.columns)
    # 常见列名：index_code / code, display_name, publish_date
    code_col = "index_code" if "index_code" in cols else ("code" if "code" in cols else None)
    name_col = "display_name" if "display_name" in cols else ("指数名称" if "指数名称" in cols else None)
    date_col = "publish_date" if "publish_date" in cols else ("发布日期" if "发布日期" in cols else None)
    if not code_col or not name_col or not date_col:
        raise RuntimeError(f"Unexpected columns in index_stock_info: {df.columns.tolist()}")

    df = df[[code_col, name_col, date_col]].copy()
    df[date_col] = df[date_col].apply(normalize_date_str)

    # 过滤 codes
    if codes:
        df = df[df[code_col].astype(str).isin([str(c) for c in codes])]
    if df.empty:
        print("Filtered index info empty for given codes")
        return 0

    payload = []
    for _, row in df.iterrows():
        payload.append({
            "code": str(row[code_col]),
            "display_name": str(row[name_col]),
            "publish_date": row[date_col],
        })
    # 批量写入
    res = _post("/api/v1/index/info/batch", payload)
    affected = int(res.get("data", {}).get("affected", 0)) if isinstance(res, dict) else 0
    print(f"Index info batch upsert affected={affected}")
    return affected


def _to_exchange_prefixed(code: str) -> Optional[str]:
    """将 000001 -> sh000001, 399001 -> sz399001 等"""
    code = str(code)
    if code.startswith("00") and len(code) == 6:
        return "sh" + code
    if code.startswith("399") and len(code) == 6:
        return "sz" + code
    # 常见其它指数代码可按需扩展
    return None


def fetch_index_daily(code: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """使用 akshare 拉取指数日线数据，返回 DataFrame
    尝试使用 stock_zh_index_daily(symbol="sh000001")
    """
    symbol = _to_exchange_prefixed(code)
    if not symbol:
        raise RuntimeError(f"Unsupported index code: {code}")
    df = ak.stock_zh_index_daily(symbol=symbol)
    if df is None or df.empty:
        return df
    # 统一列名
    # 常见列：date, open, close, high, low, volume, amount
    # 涨跌幅可能为 pct_chg 或者涨跌幅
    cols = set(df.columns)
    date_col = "date" if "date" in cols else ("日期" if "日期" in cols else None)
    if not date_col:
        raise RuntimeError(f"Unexpected columns in index daily: {df.columns.tolist()}")
    df[date_col] = df[date_col].apply(normalize_date_str)
    if start_date:
        df = df[df[date_col] >= start_date]
    if end_date:
        df = df[df[date_col] <= end_date]
    return df


def upsert_index_daily(code: str, start_date: Optional[str] = None, end_date: Optional[str] = None, batch_size: int = 500) -> int:
    df = fetch_index_daily(code, start_date, end_date)
    if df is None or df.empty:
        print(f"index daily empty for code={code}")
        return 0
    cols = set(df.columns)
    date_col = "date" if "date" in cols else ("日期" if "日期" in cols else None)
    open_col = "open" if "open" in cols else ("开盘" if "开盘" in cols else None)
    close_col = "close" if "close" in cols else ("收盘" if "收盘" in cols else None)
    high_col = "high" if "high" in cols else ("最高" if "最高" in cols else None)
    low_col = "low" if "low" in cols else ("最低" if "最低" in cols else None)
    vol_col = "volume" if "volume" in cols else ("成交量" if "成交量" in cols else None)
    amt_col = "amount" if "amount" in cols else ("成交额" if "成交额" in cols else None)
    pct_col = None
    for cand in ["pct_chg", "涨跌幅", "change_percent"]:
        if cand in cols:
            pct_col = cand
            break
    if not all([date_col, open_col, close_col, high_col, low_col, vol_col, amt_col]):
        raise RuntimeError(f"Unexpected columns in index daily: {df.columns.tolist()}")

    rows = []
    for _, row in df.iterrows():
        payload = {
            "code": str(code),
            "trading_date": row[date_col],
            "open": float(row[open_col]) if row[open_col] is not None else None,
            "close": float(row[close_col]) if row[close_col] is not None else None,
            "high": float(row[high_col]) if row[high_col] is not None else None,
            "low": float(row[low_col]) if row[low_col] is not None else None,
            "volume": int(float(row[vol_col])) if row[vol_col] is not None else None,
            "amount": float(row[amt_col]) if row[amt_col] is not None else None,
            "change_percent": float(row[pct_col]) if pct_col and row[pct_col] is not None else None,
        }
        rows.append(payload)

    affected = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        res = _post("/api/v1/index/daily/batch", batch)
        n = int(res.get("data", {}).get("affected", 0)) if isinstance(res, dict) else 0
        affected += n
        time.sleep(0.2)
    print(f"Index daily upsert for code={code} affected={affected}")
    return affected


def main(argv: List[str]):
    import argparse
    parser = argparse.ArgumentParser(description="Sync index info & daily to Go API")
    parser.add_argument("--sync-info", action="store_true", help="Sync index basic info")
    parser.add_argument("--sync-daily", action="store_true", help="Sync index daily data for codes")
    parser.add_argument("--codes", type=str, default="", help="Comma separated index codes, e.g. 000001,399001")
    parser.add_argument("--start-date", type=str, default=None, help="Start date YYYY-MM-DD for daily")
    parser.add_argument("--end-date", type=str, default=None, help="End date YYYY-MM-DD for daily")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for daily upsert")
    args = parser.parse_args(argv)

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else []
    if args.sync_info:
        upsert_index_info_by_codes(codes)
    if args.sync_daily:
        if not codes:
            print("--sync-daily requires --codes")
            return
        for code in codes:
            upsert_index_daily(code, start_date=args.start_date, end_date=args.end_date, batch_size=args.batch_size)


if __name__ == "__main__":
    # main(sys.argv[1:])
    # upsert_index_info_by_codes()
