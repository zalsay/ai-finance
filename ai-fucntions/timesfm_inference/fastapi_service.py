#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TimesFM FastAPI 推理服务
提供基于TimesFM模型的股票预测API服务
"""

import os
import sys
import asyncio
import logging
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib import request


from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from predict_chunked_functions import predict_chunked_mode_for_best
from exchange_server import run_backtest
from req_res_types import ChunkedPredictionRequest
# 设置环境变量
os.environ['XLA_PYTHON_CLIENT_PREALLOCATE'] = 'false'
os.environ['JAX_PMAP_USE_TENSORSTORE'] = 'false'

# 添加项目路径
finance_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
akshare_dir = os.path.join(finance_dir, 'akshare-tools')
sys.path.append(akshare_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 全局变量
from dotenv import load_dotenv
load_dotenv()

GPU_ID = os.environ.get('GPU_ID', '0')
SERVICE_PORT = int(os.environ.get('SERVICE_PORT', '8000'))

# Pydantic 模型定义
class StockPredictionRequest(BaseModel):
    """股票预测请求模型"""
    stock_code: str = Field(..., description="股票代码，如600398")
    stock_type: str = Field(default="stock", description="股票类型")
    time_step: int = Field(default=0, description="时间步长")
    years: int = Field(default=10, description="历史数据年数")
    horizon_len: int = Field(default=5, description="预测长度")
    context_len: int = Field(default=2048, description="上下文长度")

class BatchPredictionRequest(BaseModel):
    """批量预测请求模型"""
    stock_codes: List[str] = Field(..., description="股票代码列表")
    stock_type: str = Field(default="stock", description="股票类型")
    time_step: int = Field(default=0, description="时间步长")
    years: int = Field(default=10, description="历史数据年数")
    horizon_len: int = Field(default=5, description="预测长度")
    context_len: int = Field(default=2048, description="上下文长度")

class PredictionResponse(BaseModel):
    """预测响应模型"""
    success: bool
    stock_code: str
    gpu_id: str
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

class BatchPredictionResponse(BaseModel):
    """批量预测响应模型"""
    success: bool
    gpu_id: str
    total_stocks: int
    successful_predictions: int
    failed_predictions: int
    total_processing_time: float
    results: List[PredictionResponse]



class RunBacktestRequest(BaseModel):
    """运行回测的请求模型（包含预测与策略参数）"""
    # 预测基础参数
    stock_code: str
    stock_type: str = "stock"
    time_step: int = 0
    years: int = 10
    horizon_len: int = 7
    context_len: int = 2048
    include_technical_indicators: bool = True
    fixed_end_date: Optional[str] = None
    prediction_mode: int = 1
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    timesfm_version: str = "2.0"
    user_id: Optional[int] = None

    # 回测策略参数
    buy_threshold_pct: float = 3.0
    sell_threshold_pct: float = -1.0
    initial_cash: float = 100000.0
    enable_rebalance: bool = True
    max_position_pct: float = 1.0
    min_position_pct: float = 0.2
    slope_position_per_pct: float = 0.1
    rebalance_tolerance_pct: float = 0.05
    trade_fee_rate: float = 0.006
    take_profit_threshold_pct: Optional[float] = None
    take_profit_sell_frac: Optional[float] = None

class ChunkPredictionResult(BaseModel):
    """单个分块预测结果"""
    chunk_index: int
    chunk_start_date: str
    chunk_end_date: str
    success: bool
    prediction_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: float

class ChunkedPredictionResponse(BaseModel):
    """分块预测响应模型"""
    success: bool
    stock_code: str
    gpu_id: str
    prediction_mode: int
    total_chunks: int
    successful_chunks: int
    failed_chunks: int
    total_processing_time: float
    chunk_results: List[ChunkPredictionResult]
    summary: Dict[str, Any]

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    gpu_id: str
    model_loaded: bool
    timestamp: str

# FastAPI 应用初始化
app = FastAPI(
    title="TimesFM 股票预测服务",
    description="基于TimesFM模型的股票价格预测API服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"启动TimesFM推理服务，GPU ID: {GPU_ID}, 端口: {SERVICE_PORT}")
    

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="healthy" if TIMESFM_MODEL is not None else "unhealthy",
        gpu_id=GPU_ID,
        model_loaded=TIMESFM_MODEL is not None,
        timestamp=datetime.now().isoformat()
    )

@app.post("/predict_for_best")
async def predict_stock(data: Dict, background_tasks: BackgroundTasks):
    """单个股票预测接口"""    
    try:
        req_stock_code = str(data.get("stock_code", ""))
        request = ChunkedPredictionRequest(**data)
        req_stock_code = request.stock_code
        logger.info(f"predict_for_best received: {request}")
        background_tasks.add_task(predict_chunked_mode_for_best, request)
        return JSONResponse(
            status_code=200,
            content={
            "success": True,
            "stock_code": req_stock_code,
            "gpu_id": GPU_ID,
            "message": "开始推理",
        })
        
    except Exception as e:
        logger.error(f"预测失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
            "success": False,
            "stock_code": str(data.get("stock_code", "")),
            "gpu_id": GPU_ID,
            "message": "预测失败",
            "error": str(e),
        })


@app.post("/backtest/run")
async def run_backtest_api(req: RunBacktestRequest):
    """交易策略回测接口：基于 TimesFM 分块预测并执行策略回测"""
    try:
        # 构造 exchange_server 需要的 dataclass 请求体
        from req_res_types import ChunkedPredictionRequest as TfmRequest
        tfm_req = TfmRequest(
            stock_code=req.stock_code,
            years=req.years,
            horizon_len=req.horizon_len,
            start_date=req.start_date,
            end_date=req.end_date,
            context_len=req.context_len,
            time_step=req.time_step,
            stock_type=req.stock_type,
            timesfm_version=req.timesfm_version,
            user_id=req.user_id,
        )

        result = await run_backtest(
            tfm_req,
            buy_threshold_pct=req.buy_threshold_pct,
            sell_threshold_pct=req.sell_threshold_pct,
            initial_cash=req.initial_cash,
            enable_rebalance=req.enable_rebalance,
            max_position_pct=req.max_position_pct,
            min_position_pct=req.min_position_pct,
            slope_position_per_pct=req.slope_position_per_pct,
            rebalance_tolerance_pct=req.rebalance_tolerance_pct,
            trade_fee_rate=req.trade_fee_rate,
            take_profit_threshold_pct=req.take_profit_threshold_pct,
            take_profit_sell_frac=req.take_profit_sell_frac,
        )

        backtest = result.get("backtest", {})
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "stock_code": req.stock_code,
                "gpu_id": GPU_ID,
                "message": "回测完成",
                "backtest": backtest,
            },
        )
    except Exception as e:
        logger.error(f"回测失败: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "stock_code": req.stock_code,
                "gpu_id": GPU_ID,
                "message": "回测失败",
                "error": str(e),
            },
        )



@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "TimesFM 股票预测服务",
        "gpu_id": GPU_ID,
        "model_loaded": TIMESFM_MODEL is not None,
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_service:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=False,
        workers=1
    )
