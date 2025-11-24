#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TimesFM FastAPI 推理服务 - 简化版本
用于测试容器构建和基本功能
"""

import os
import json
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 环境变量
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
    include_technical_indicators: bool = Field(default=True, description="是否包含技术指标")

class BatchPredictionRequest(BaseModel):
    """批量预测请求模型"""
    stock_codes: List[str] = Field(..., description="股票代码列表")
    stock_type: str = Field(default="stock", description="股票类型")
    time_step: int = Field(default=0, description="时间步长")
    years: int = Field(default=10, description="历史数据年数")
    horizon_len: int = Field(default=5, description="预测长度")
    context_len: int = Field(default=2048, description="上下文长度")
    include_technical_indicators: bool = Field(default=True, description="是否包含技术指标")

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

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    gpu_id: str
    model_loaded: bool
    timestamp: str
    service_type: str

# FastAPI 应用初始化
app = FastAPI(
    title="TimesFM 股票预测服务 - 简化版",
    description="基于TimesFM模型的股票价格预测API服务（测试版本）",
    version="1.0.0-simple",
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

def generate_mock_prediction(stock_code: str, horizon_len: int = 5) -> Dict[str, Any]:
    """生成模拟预测数据"""
    # 模拟历史价格数据
    base_price = 100.0
    dates = pd.date_range(start='2024-01-01', periods=horizon_len, freq='D')
    
    # 生成随机预测数据
    np.random.seed(hash(stock_code) % 2**32)  # 基于股票代码生成一致的随机数
    predictions = base_price + np.random.normal(0, 5, horizon_len)
    
    # 构建预测结果
    forecast_data = []
    for i, (date, pred) in enumerate(zip(dates, predictions)):
        forecast_data.append({
            'ds': date.strftime('%Y-%m-%d'),
            'ds_plot': date.strftime('%Y-%m-%d'),
            'timesfm-q-0.1': pred * 0.95,
            'timesfm-q-0.5': pred,
            'timesfm-q-0.9': pred * 1.05,
            'unique_id': stock_code
        })
    
    # 模拟实际数据
    actual_data = []
    actual_prices = base_price + np.random.normal(0, 3, horizon_len)
    for i, (date, actual) in enumerate(zip(dates, actual_prices)):
        actual_data.append({
            'ds': date.strftime('%Y-%m-%d'),
            'close': actual,
            'stock_code': stock_code
        })
    
    # 计算模拟指标
    mse = np.mean((predictions - actual_prices) ** 2)
    mae = np.mean(np.abs(predictions - actual_prices))
    combined_score = 0.5 * mse + 0.5 * mae
    
    return {
        'stock_code': stock_code,
        'gpu_id': GPU_ID,
        'prediction_length': horizon_len,
        'best_prediction_column': 'timesfm-q-0.5',
        'best_combined_score': float(combined_score),
        'all_metrics': {
            'timesfm-q-0.5': {
                'mse': float(mse),
                'mae': float(mae),
                'combined_score': float(combined_score)
            }
        },
        'forecast_data': forecast_data,
        'actual_data': actual_data,
        'is_mock_data': True
    }

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"启动TimesFM推理服务（简化版），GPU ID: {GPU_ID}, 端口: {SERVICE_PORT}")
    logger.info("服务启动完成，使用模拟数据模式")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="healthy",
        gpu_id=GPU_ID,
        model_loaded=True,  # 简化版本总是返回True
        timestamp=datetime.now().isoformat(),
        service_type="simple_mock"
    )

@app.post("/predict", response_model=PredictionResponse)
async def predict_stock(request: StockPredictionRequest):
    """单个股票预测接口"""
    start_time = time.time()
    
    try:
        # 模拟处理时间
        await asyncio.sleep(0.5)  # 模拟计算时间
        
        # 生成模拟预测结果
        result = generate_mock_prediction(request.stock_code, request.horizon_len)
        processing_time = time.time() - start_time
        result['processing_time'] = processing_time
        
        logger.info(f"模拟预测完成: {request.stock_code}, 耗时: {processing_time:.2f}秒")
        
        return PredictionResponse(
            success=True,
            stock_code=request.stock_code,
            gpu_id=GPU_ID,
            message="模拟预测成功",
            data=result,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)
        
        logger.error(f"模拟预测失败: {error_msg}")
        
        return PredictionResponse(
            success=False,
            stock_code=request.stock_code,
            gpu_id=GPU_ID,
            message="模拟预测失败",
            error=error_msg,
            processing_time=processing_time
        )

@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_stocks_batch(request: BatchPredictionRequest):
    """批量股票预测接口"""
    start_time = time.time()
    
    results = []
    successful_count = 0
    failed_count = 0
    
    for stock_code in request.stock_codes:
        try:
            # 模拟处理时间
            await asyncio.sleep(0.2)  # 批量处理时每个股票用时更短
            
            # 生成模拟预测结果
            result = generate_mock_prediction(stock_code, request.horizon_len)
            
            results.append(PredictionResponse(
                success=True,
                stock_code=stock_code,
                gpu_id=GPU_ID,
                message="模拟预测成功",
                data=result
            ))
            
            successful_count += 1
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"批量模拟预测中股票 {stock_code} 失败: {error_msg}")
            
            results.append(PredictionResponse(
                success=False,
                stock_code=stock_code,
                gpu_id=GPU_ID,
                message="模拟预测失败",
                error=error_msg
            ))
            
            failed_count += 1
    
    total_processing_time = time.time() - start_time
    
    logger.info(f"批量模拟预测完成: {successful_count}/{len(request.stock_codes)} 成功")
    
    return BatchPredictionResponse(
        success=successful_count > 0,
        gpu_id=GPU_ID,
        total_stocks=len(request.stock_codes),
        successful_predictions=successful_count,
        failed_predictions=failed_count,
        total_processing_time=total_processing_time,
        results=results
    )

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "TimesFM 股票预测服务 - 简化版",
        "gpu_id": GPU_ID,
        "model_loaded": True,
        "service_type": "simple_mock",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import asyncio
    uvicorn.run(
        "fastapi_service_simple:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=False,
        workers=1
    )