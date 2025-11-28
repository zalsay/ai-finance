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


from fastapi import FastAPI, HTTPException, BackgroundTasks, background
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from predict_chunked_functions import predict_chunked_mode_for_best
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
TIMESFM_MODEL = None
MODEL_PATH = "/root/workers/finance/timesfm/timesfm-2.0-500m-pytorch/torch_model.ckpt"
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

class ChunkedPredictionRequest(BaseModel):
    """分块预测请求模型"""
    stock_code: str = Field(..., description="股票代码，如600398")
    stock_type: str = Field(default="stock", description="股票类型")
    time_step: int = Field(default=0, description="时间步长")
    years: int = Field(default=10, description="历史数据年数")
    horizon_len: int = Field(default=5, description="预测长度")
    context_len: int = Field(default=2048, description="上下文长度")
    include_technical_indicators: bool = Field(default=True, description="是否包含技术指标")
    fixed_end_date: str = Field(default="20250630", description="固定结束日期，格式YYYYMMDD")
    prediction_mode: int = Field(default=1, description="预测模式：1=固定训练集，2=滑动窗口（待实现）")

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
async def predict_stock(request: ChunkedPredictionRequest):
    """单个股票预测接口"""
    start_time = datetime.now()
    
    try:
        background_task = asyncio.create_task(predict_chunked_mode_for_best(request))
        BackgroundTasks.add_task(background_task)
        return JSONResponse(
            status_code=200,
            content={
            "success": True,
            "stock_code": request.stock_code,
            "gpu_id": GPU_ID,
            "message": "开始推理",
        })
        
    except Exception as e:
        logger.error(f"预测失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
            "success": False,
            "stock_code": request.stock_code,
            "gpu_id": GPU_ID,
            "message": "预测失败",
            "error": str(e),
        })



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