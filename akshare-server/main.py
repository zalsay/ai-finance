"""
FastAPI 服务：对标 index.py 中的 main_handler 逻辑，提供统一的 HTTP 接口以获取基金、股票、指数数据。

参考 index.py#main_handler 的实现与返回结构：
- 返回结构统一使用 {"code": 200|0, "data"?: any, "msg"?: string}

端点：
- GET /health -> 健康检查
- POST /api/v1/data -> 根据 type 路由到 fund / all_fund / stock / index

请求体示例：
{
  "type": "stock",            # fund | all_fund | stock | index
  "code": "600398",           # 基金/股票/指数代码
  "start_date": "19900101",   # 可选，默认 19700101
  "end_date": "20500101",     # 可选，默认 20500101
  "adjust": "",               # 可选，仅 stock 使用
  "period": "daily"           # 可选，仅 index 使用
}

依赖：需与 index.py 使用的相同函数保持一致。
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import pandas as pd
import os
import sys

# 将 src 目录加入 sys.path，便于直接导入内置于 src 目录的第三方包（如 demjson、py_mini_racer 等）
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# 直接复用 index.py 中定义/引用的函数
# 注意：index.py 依赖的第三方库（如 demjson、py_mini_racer 等）在某些环境可能缺失。
# 为保证服务本身能够启动，我们不在顶层导入，而是在路由处理函数中按需延迟导入，并用统一的错误返回结构兼容缺库情况。


class DataRequest(BaseModel):
    type: str
    code: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    adjust: str | None = None
    period: str | None = None


app = FastAPI(title="AkShare Server", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"]
    ,allow_headers=["*"]
)


@app.get("/health")
def health():
    return {"code": 200, "data": "ok"}


def df_to_json_records(df: pd.DataFrame):
    json_data = df.to_json(orient="records")
    return json.loads(json_data)


@app.post("/api/v1/data")
def get_data(req: DataRequest):
    t = (req.type or "").strip().lower()
    try:
        if t == "fund":
            # 延迟导入，兼容缺库环境
            try:
                from .ak_functions import fund_open_fund_info_em
            except Exception:
                return {"code": 0, "msg": "scf invoke error"}
            if not req.code:
                raise HTTPException(status_code=400, detail="code is required for fund")
            result = fund_open_fund_info_em(req.code, "单位净值+累计净值", "pandas")
            return {"code": 200, "data": df_to_json_records(result)}

        elif t == "all_fund":
            try:
                from .ak_functions import fund_open_fund_daily_em
            except Exception:
                return {"code": 0, "msg": "scf invoke error"}
            result = fund_open_fund_daily_em()
            return {"code": 200, "data": df_to_json_records(result)}

        elif t == "stock":
            try:
                from .ak_functions import stock_zh_a_daily
            except Exception:
                return {"code": 0, "msg": "scf invoke error"}
            start_date = req.start_date or "19700101"
            end_date = req.end_date or "20500101"
            adjust = req.adjust or ""
            if not req.code:
                raise HTTPException(status_code=400, detail="code is required for stock")
            result = stock_zh_a_daily(req.code, start_date, end_date, adjust)
            return {"code": 200, "data": df_to_json_records(result)}

        elif t == "index":
            try:
                from .ak_functions import index_zh_a_hist
            except Exception:
                return {"code": 0, "msg": "scf invoke error"}
            start_date = req.start_date or "19700101"
            end_date = req.end_date or "20500101"
            period = req.period or "daily"
            if not req.code:
                raise HTTPException(status_code=400, detail="code is required for index")
            result = index_zh_a_hist(req.code, period, start_date, end_date)
            return {"code": 200, "data": df_to_json_records(result)}

        else:
            return {"code": 0, "msg": "unsupported type"}
    except HTTPException:
        # 直接抛出由参数校验导致的错误
        raise
    except Exception:
        # 与 index.py 保持一致，统一返回错误
        return {"code": 0, "msg": "scf invoke error"}


# 便于在本地 uvicorn 启动调试
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)