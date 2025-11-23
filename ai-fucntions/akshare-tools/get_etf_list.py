import os
from datetime import date

import akshare as ak
import pandas as pd
import requests


# Go 服务地址与鉴权配置
GO_API_URL = os.getenv("GO_API_URL", "http://127.0.0.1:8080")
API_TOKEN = os.getenv("API_TOKEN", "fintrack-dev-token")


# 兼容旧脚本：Go 服务会在初始化时自动创建 etf_daily 表，这里不再直连数据库创建表
def ensure_table():
    return


def fetch_etf_df():
    # 从新浪获取全部ETF基金实时数据
    df = ak.fund_etf_category_sina(symbol="ETF基金")
    print(df.head(3))
    return df


def _to_float(val):
    """将值安全转换为 float。若包含百分号或逗号，做清理；失败则返回 0.0。"""
    if val is None:
        return 0.0
    # NaN 处理
    try:
        if isinstance(val, float) and pd.isna(val):
            return 0.0
    except Exception:
        pass
    try:
        s = str(val).strip().replace(",", "")
        if s.endswith("%"):
            s = s[:-1]
        return float(s)
    except Exception:
        return 0.0


def _to_int(val):
    """将值安全转换为 int。失败则返回 0。"""
    if val is None:
        return 0
    try:
        if isinstance(val, float) and pd.isna(val):
            return 0
    except Exception:
        pass
    try:
        s = str(val).strip().replace(",", "")
        # 有些成交额可能是小数，取整
        return int(float(s))
    except Exception:
        return 0


# 通过 Go 服务的 HTTP 接口批量上送数据
def _post_batch_to_go(payload, api_url=None, token=None, timeout=30):
    base = (api_url or GO_API_URL).rstrip("/")
    tk = token or API_TOKEN
    url = f"{base}/api/v1/etf/daily/batch"
    headers = {
        "Content-Type": "application/json",
        "X-Token": tk,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    return resp


def upsert_etf_daily(df: pd.DataFrame, api_url=None, token=None, batch_size=500):
    """改为调用 Golang 服务的批量接口进行 upsert，不再直连数据库。"""
    tdate = date.today().strftime("%Y-%m-%d")
    payload = []

    for _, r in df.iterrows():
        code = str(r.get("代码") or "").strip()
        if not code:
            continue
        payload.append({
            "code": code,
            "trading_date": tdate,
            "name": str(r.get("名称") or "").strip(),
            "latest_price": _to_float(r.get("最新价")),
            "change_amount": _to_float(r.get("涨跌额")),
            "change_percent": _to_float(r.get("涨跌幅")),
            "buy": _to_float(r.get("买入")),
            "sell": _to_float(r.get("卖出")),
            "prev_close": _to_float(r.get("昨收")),
            "open": _to_float(r.get("今开")),
            "high": _to_float(r.get("最高")),
            "low": _to_float(r.get("最低")),
            "volume": _to_int(r.get("成交量")),
            "turnover": _to_int(r.get("成交额")),
        })

    total = 0
    for i in range(0, len(payload), batch_size):
        batch = payload[i:i+batch_size]
        _post_batch_to_go(batch, api_url=api_url, token=token)
        total += len(batch)
    return total


def main():
    df = fetch_etf_df()
    ensure_table()  # 兼容旧逻辑占位
    n = upsert_etf_daily(df)
    print(f"Upserted {n} rows into etf_daily (via Go API) on {date.today()}.")


if __name__ == "__main__":
    main()
