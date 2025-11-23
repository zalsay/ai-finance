"""
FastAPI服务器 - 提供股票数据同步接口

接口:
- POST /api/sync-stock - 同步股票数据到PostgreSQL
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import logging

from postgres import PostgresHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FinTrack Stock Sync API", version="1.0.0")

# CORS配置 - 允许frontend访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PostgreSQL Handler配置
PG_BASE_URL = "http://8.163.5.7:8000"
PG_API_TOKEN = "fintrack-dev-token"


class SyncStockRequest(BaseModel):
    symbol: str
    stock_type: int = 1  # 1=沪市, 2=深市
    batch_size: Optional[int] = 1000


class SyncStockResponse(BaseModel):
    success: bool
    message: str
    symbol: str
    stock_type: int
    fetched_records: int = 0
    stored_records: int = 0
    batches: int = 0
    error: Optional[str] = None


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "fintrack-stock-sync"}


@app.post("/api/sync-stock", response_model=SyncStockResponse)
async def sync_stock(request: SyncStockRequest):
    """
    同步股票数据到PostgreSQL
    
    Args:
        symbol: 股票代码 (如: 600000, 000001)
        stock_type: 股票类型 (1=沪市, 2=深市)
        batch_size: 批量写入大小
        
    Returns:
        同步结果统计
    """
    try:
        logger.info(f"收到同步请求: symbol={request.symbol}, stock_type={request.stock_type}")
        
        # 创建PostgresHandler实例并同步
        async with PostgresHandler(base_url=PG_BASE_URL, api_token=PG_API_TOKEN) as handler:
            result = await handler.sync_stock(
                symbol=request.symbol,
                stock_type=request.stock_type,
                batch_size=request.batch_size
            )
            
            logger.info(f"同步结果: {result}")
            
            return SyncStockResponse(
                success=result.get("success", False),
                message="同步成功" if result.get("success") else "同步失败",
                symbol=result.get("symbol", request.symbol),
                stock_type=result.get("stock_type", request.stock_type),
                fetched_records=result.get("fetched_records", 0),
                stored_records=result.get("stored_records", 0),
                batches=result.get("batches", 0),
                error=result.get("error")
            )
            
    except Exception as e:
        logger.error(f"同步过程中发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
