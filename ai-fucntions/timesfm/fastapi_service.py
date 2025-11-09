#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TimesFM FastAPI 推理服务
提供基于TimesFM模型的股票预测API服务
"""

import os
import sys
import json
import logging
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# 设置环境变量
os.environ['XLA_PYTHON_CLIENT_PREALLOCATE'] = 'false'
os.environ['JAX_PMAP_USE_TENSORSTORE'] = 'false'

# 添加项目路径
finance_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
akshare_dir = os.path.join(finance_dir, 'akshare-tools')
sys.path.append(akshare_dir)

# 导入项目模块
from get_finanial_data import ak_stock_data, get_stock_list, get_index_data, talib_tools

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

def load_timesfm_model():
    """加载TimesFM模型"""
    global TIMESFM_MODEL
    
    try:
        logger.info(f"正在GPU {GPU_ID}上加载TimesFM模型...")
        
        # 设置CUDA设备
        os.environ['CUDA_VISIBLE_DEVICES'] = GPU_ID
        
        TIMESFM_MODEL = timesfm.TimesFm(
            hparams=timesfm.TimesFmHparams(
                backend="gpu",
                per_core_batch_size=16,
                horizon_len=5,  # 默认值，会在预测时动态调整
                num_layers=50,
                use_positional_embedding=False,
                context_len=2048,  # 默认值，会在预测时动态调整
            ),
            checkpoint=timesfm.TimesFmCheckpoint(path=MODEL_PATH),
        )
        
        logger.info(f"TimesFM模型在GPU {GPU_ID}上加载成功")
        return True
        
    except Exception as e:
        logger.error(f"加载TimesFM模型失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def df_preprocess(stock_code: str, stock_type: str, time_step: int, years: int = 10, horizon_len: int = 7):
    """数据预处理函数"""
    try:
        # 获取股票数据
        df_original = ak_stock_data(stock_code, stock_type, time_step, years=years)
        
        if df_original is None or df_original.empty:
            raise ValueError(f"无法获取股票 {stock_code} 的数据")
        
        # 数据预处理
        df_original = df_original.sort_values('ds').reset_index(drop=True)
        
        # 分割训练和测试数据
        split_point = len(df_original) - horizon_len
        df_train = df_original.iloc[:split_point].copy()
        df_test = df_original.iloc[split_point:].copy()
        
        logger.info(f"股票 {stock_code} 数据预处理完成，训练集: {len(df_train)}, 测试集: {len(df_test)}")
        
        return df_original, df_train, df_test
        
    except Exception as e:
        logger.error(f"数据预处理失败: {str(e)}")
        raise

def predict_single_stock(request: StockPredictionRequest) -> Dict[str, Any]:
    """单个股票预测"""
    start_time = datetime.now()
    
    try:
        # 数据预处理
        df_original, df_train, df_test = df_preprocess(
            request.stock_code, 
            request.stock_type, 
            request.time_step, 
            request.years, 
            request.horizon_len
        )
        
        # 添加唯一标识符
        df_train["unique_id"] = df_train["stock_code"].astype(str)
        df_test["unique_id"] = df_test["stock_code"].astype(str)
        
        # 可选：添加技术指标
        if request.include_technical_indicators:
            try:
                df_train, input_features = talib_tools(df_train)
                logger.info(f"股票 {request.stock_code} 技术指标添加成功")
            except Exception as e:
                logger.warning(f"添加技术指标失败: {e}，继续使用原始数据")
        
        # 准备预测数据
        df_train_for_prediction = df_train.copy()
        if 'ds_plot' in df_train_for_prediction.columns:
            df_train_for_prediction = df_train_for_prediction.drop(columns=['ds_plot'])
        
        # 动态调整模型参数
        TIMESFM_MODEL.hparams.horizon_len = request.horizon_len
        TIMESFM_MODEL.hparams.context_len = request.context_len
        
        # 执行预测
        logger.info(f"开始预测股票 {request.stock_code}...")
        forecast_df = TIMESFM_MODEL.forecast_on_df(
            inputs=df_train_for_prediction,
            freq="D",
            value_name="close",
            num_jobs=1,
        )
        
        # 为预测结果添加绘图日期列
        if 'ds' in forecast_df.columns:
            forecast_df['ds_plot'] = pd.to_datetime(forecast_df['ds']).dt.strftime('%Y-%m-%d')
        
        # 计算预测指标
        prediction_columns = [col for col in forecast_df.columns if col.startswith('timesfm-q-')]
        
        # 获取实际值和预测值进行比较
        actual_values = df_test['close'].values[:request.horizon_len]
        
        best_column = None
        best_score = float('inf')
        metrics = {}
        
        for col in prediction_columns:
            if col in forecast_df.columns:
                pred_values = forecast_df[col].values[:request.horizon_len]
                
                # 计算MSE和MAE
                mse = np.mean((pred_values - actual_values) ** 2)
                mae = np.mean(np.abs(pred_values - actual_values))
                
                # 综合评分 (MSE和MAE各占50%权重)
                combined_score = 0.5 * mse + 0.5 * mae
                
                metrics[col] = {
                    'mse': float(mse),
                    'mae': float(mae),
                    'combined_score': float(combined_score)
                }
                
                if combined_score < best_score:
                    best_score = combined_score
                    best_column = col
        
        # 构建返回结果
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            'stock_code': request.stock_code,
            'gpu_id': GPU_ID,
            'prediction_length': request.horizon_len,
            'best_prediction_column': best_column,
            'best_combined_score': float(best_score),
            'all_metrics': metrics,
            'forecast_data': forecast_df.to_dict('records'),
            'actual_data': df_test.to_dict('records'),
            'processing_time': processing_time
        }
        
        logger.info(f"股票 {request.stock_code} 预测完成，最佳列: {best_column}, 评分: {best_score:.4f}")
        
        return result
        
    except Exception as e:
        logger.error(f"预测股票 {request.stock_code} 失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def create_chunks_from_test_data(df_test: pd.DataFrame, horizon_len: int) -> List[pd.DataFrame]:
    """根据horizon_len将df_test分块"""
    chunks = []
    total_rows = len(df_test)
    
    for i in range(0, total_rows, horizon_len):
        chunk = df_test.iloc[i:i+horizon_len].copy()
        if len(chunk) > 0:  # 确保分块不为空
            chunks.append(chunk)
    
    logger.info(f"将测试数据分为 {len(chunks)} 个分块，每块最多 {horizon_len} 行")
    return chunks

def predict_single_chunk_mode1(stock_code: str, stock_type: str, time_step: int, years: int, 
                              horizon_len: int, context_len: int, include_technical_indicators: bool,
                              fixed_end_date: str, chunk_df: pd.DataFrame, chunk_index: int) -> Dict[str, Any]:
    """
    模式1分块预测：固定训练集，使用固定end_date生成训练数据
    
    参数:
        stock_code: 股票代码
        stock_type: 股票类型
        time_step: 时间步长
        years: 历史数据年数
        horizon_len: 预测长度
        context_len: 上下文长度
        include_technical_indicators: 是否包含技术指标
        fixed_end_date: 固定的结束日期
        chunk_df: 当前分块的测试数据
        chunk_index: 分块索引
    
    返回:
        Dict: 预测结果
    """
    start_time = datetime.now()
    
    try:
        # 获取固定训练数据集（使用固定的end_date）
        logger.info(f"分块 {chunk_index}: 获取固定训练数据，end_date={fixed_end_date}, years={years}")
        
        df_train_fixed = ak_stock_data(
            symbol=stock_code,
            end_date=fixed_end_date,
            years=years,
            time_step=time_step
        )
        
        if df_train_fixed is None or df_train_fixed.empty:
            raise ValueError(f"无法获取股票 {stock_code} 的固定训练数据")
        
        # 数据预处理
        df_train_fixed = df_train_fixed.sort_values('ds').reset_index(drop=True)
        df_train_fixed["unique_id"] = df_train_fixed["stock_code"].astype(str)
        
        # 添加技术指标（如果需要）
        if include_technical_indicators:
            try:
                df_train_fixed, input_features = talib_tools(df_train_fixed)
                logger.info(f"分块 {chunk_index}: 技术指标添加成功")
            except Exception as e:
                logger.warning(f"分块 {chunk_index}: 添加技术指标失败: {e}，继续使用原始数据")
        
        # 准备预测数据
        df_train_for_prediction = df_train_fixed.copy()
        if 'ds_plot' in df_train_for_prediction.columns:
            df_train_for_prediction = df_train_for_prediction.drop(columns=['ds_plot'])
        
        # 动态调整模型参数
        TIMESFM_MODEL.hparams.horizon_len = len(chunk_df)  # 使用实际分块大小
        TIMESFM_MODEL.hparams.context_len = context_len
        
        # 执行预测
        logger.info(f"分块 {chunk_index}: 开始预测，预测长度={len(chunk_df)}")
        forecast_df = TIMESFM_MODEL.forecast_on_df(
            inputs=df_train_for_prediction,
            freq="D",
            value_name="close",
            num_jobs=1,
        )
        
        # 为预测结果添加绘图日期列
        if 'ds' in forecast_df.columns:
            forecast_df['ds_plot'] = pd.to_datetime(forecast_df['ds']).dt.strftime('%Y-%m-%d')
        
        # 计算预测指标
        prediction_columns = [col for col in forecast_df.columns if col.startswith('timesfm-q-')]
        
        # 获取实际值和预测值进行比较
        actual_values = chunk_df['close'].values
        chunk_size = len(chunk_df)
        
        best_column = None
        best_score = float('inf')
        metrics = {}
        
        for col in prediction_columns:
            if col in forecast_df.columns:
                pred_values = forecast_df[col].values[:chunk_size]
                
                # 确保预测值和实际值长度一致
                min_len = min(len(pred_values), len(actual_values))
                pred_values = pred_values[:min_len]
                actual_values_trimmed = actual_values[:min_len]
                
                # 计算MSE和MAE
                mse = np.mean((pred_values - actual_values_trimmed) ** 2)
                mae = np.mean(np.abs(pred_values - actual_values_trimmed))
                
                # 综合评分 (MSE和MAE各占50%权重)
                combined_score = 0.5 * mse + 0.5 * mae
                
                metrics[col] = {
                    'mse': float(mse),
                    'mae': float(mae),
                    'combined_score': float(combined_score)
                }
                
                if combined_score < best_score:
                    best_score = combined_score
                    best_column = col
        
        # 构建返回结果
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            'chunk_index': chunk_index,
            'stock_code': stock_code,
            'gpu_id': GPU_ID,
            'prediction_mode': 1,
            'chunk_size': len(chunk_df),
            'chunk_start_date': chunk_df['ds'].iloc[0] if len(chunk_df) > 0 else None,
            'chunk_end_date': chunk_df['ds'].iloc[-1] if len(chunk_df) > 0 else None,
            'fixed_training_end_date': fixed_end_date,
            'training_data_size': len(df_train_fixed),
            'best_prediction_column': best_column,
            'best_combined_score': float(best_score),
            'all_metrics': metrics,
            'forecast_data': forecast_df.to_dict('records'),
            'actual_chunk_data': chunk_df.to_dict('records'),
            'processing_time': processing_time
        }
        
        logger.info(f"分块 {chunk_index} 预测完成，最佳列: {best_column}, 评分: {best_score:.4f}")
        
        return result
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"分块 {chunk_index} 预测失败: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            'chunk_index': chunk_index,
            'error': str(e),
            'processing_time': processing_time
        }

def predict_chunked_mode1(request: ChunkedPredictionRequest) -> Dict[str, Any]:
    """
    模式1分块预测主函数：固定训练集分块预测
    """
    start_time = datetime.now()
    
    try:
        # 首先获取完整的股票数据来生成测试集
        logger.info(f"获取股票 {request.stock_code} 的完整数据用于生成测试集")
        df_original = ak_stock_data(
            symbol=request.stock_code,
            years=request.years + 1,  # 获取更多数据以确保有足够的测试数据
            time_step=request.time_step
        )
        
        if df_original is None or df_original.empty:
            raise ValueError(f"无法获取股票 {request.stock_code} 的数据")
        
        # 数据预处理
        df_original = df_original.sort_values('ds').reset_index(drop=True)
        
        # 生成测试数据：从固定结束日期之后的数据作为测试集
        fixed_end_datetime = pd.to_datetime(request.fixed_end_date, format='%Y%m%d')
        df_original['ds_datetime'] = pd.to_datetime(df_original['ds'])
        
        # 筛选出固定结束日期之后的数据作为测试集
        df_test = df_original[df_original['ds_datetime'] > fixed_end_datetime].copy()
        df_test = df_test.drop(columns=['ds_datetime']).reset_index(drop=True)
        
        if df_test.empty:
            raise ValueError(f"固定结束日期 {request.fixed_end_date} 之后没有测试数据")
        
        logger.info(f"生成测试集，大小: {len(df_test)}, 日期范围: {df_test['ds'].iloc[0]} 到 {df_test['ds'].iloc[-1]}")
        
        # 将测试数据分块
        chunks = create_chunks_from_test_data(df_test, request.horizon_len)
        
        # 对每个分块进行预测
        chunk_results = []
        successful_chunks = 0
        failed_chunks = 0
        
        for i, chunk_df in enumerate(chunks):
            try:
                chunk_result = predict_single_chunk_mode1(
                    stock_code=request.stock_code,
                    stock_type=request.stock_type,
                    time_step=request.time_step,
                    years=request.years,
                    horizon_len=request.horizon_len,
                    context_len=request.context_len,
                    include_technical_indicators=request.include_technical_indicators,
                    fixed_end_date=request.fixed_end_date,
                    chunk_df=chunk_df,
                    chunk_index=i
                )
                
                if 'error' not in chunk_result:
                    successful_chunks += 1
                    chunk_results.append(ChunkPredictionResult(
                        chunk_index=i,
                        chunk_start_date=chunk_result['chunk_start_date'],
                        chunk_end_date=chunk_result['chunk_end_date'],
                        success=True,
                        prediction_data=chunk_result,
                        processing_time=chunk_result['processing_time']
                    ))
                else:
                    failed_chunks += 1
                    chunk_results.append(ChunkPredictionResult(
                        chunk_index=i,
                        chunk_start_date=chunk_df['ds'].iloc[0] if len(chunk_df) > 0 else "unknown",
                        chunk_end_date=chunk_df['ds'].iloc[-1] if len(chunk_df) > 0 else "unknown",
                        success=False,
                        error=chunk_result['error'],
                        processing_time=chunk_result['processing_time']
                    ))
                
            except Exception as e:
                failed_chunks += 1
                logger.error(f"分块 {i} 处理异常: {str(e)}")
                chunk_results.append(ChunkPredictionResult(
                    chunk_index=i,
                    chunk_start_date=chunk_df['ds'].iloc[0] if len(chunk_df) > 0 else "unknown",
                    chunk_end_date=chunk_df['ds'].iloc[-1] if len(chunk_df) > 0 else "unknown",
                    success=False,
                    error=str(e),
                    processing_time=0.0
                ))
        
        # 计算总体统计
        total_processing_time = (datetime.now() - start_time).total_seconds()
        
        # 生成汇总信息
        summary = {
            'test_data_size': len(df_test),
            'test_date_range': {
                'start': df_test['ds'].iloc[0],
                'end': df_test['ds'].iloc[-1]
            },
            'fixed_training_end_date': request.fixed_end_date,
            'chunk_size': request.horizon_len,
            'success_rate': successful_chunks / len(chunks) * 100 if chunks else 0,
            'average_processing_time_per_chunk': total_processing_time / len(chunks) if chunks else 0
        }
        
        # 如果有成功的预测，计算平均指标
        if successful_chunks > 0:
            successful_results = [r.prediction_data for r in chunk_results if r.success and r.prediction_data]
            if successful_results:
                avg_score = np.mean([r['best_combined_score'] for r in successful_results])
                summary['average_best_score'] = float(avg_score)
        
        result = {
            'success': successful_chunks > 0,
            'stock_code': request.stock_code,
            'gpu_id': GPU_ID,
            'prediction_mode': 1,
            'total_chunks': len(chunks),
            'successful_chunks': successful_chunks,
            'failed_chunks': failed_chunks,
            'total_processing_time': total_processing_time,
            'chunk_results': chunk_results,
            'summary': summary
        }
        
        logger.info(f"分块预测完成: {successful_chunks}/{len(chunks)} 成功, 总耗时: {total_processing_time:.2f}秒")
        
        return result
        
    except Exception as e:
        total_processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"分块预测失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"启动TimesFM推理服务，GPU ID: {GPU_ID}, 端口: {SERVICE_PORT}")
    
    # 加载模型
    success = load_timesfm_model()
    if not success:
        logger.error("模型加载失败，服务可能无法正常工作")
    else:
        logger.info("服务启动完成，模型加载成功")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="healthy" if TIMESFM_MODEL is not None else "unhealthy",
        gpu_id=GPU_ID,
        model_loaded=TIMESFM_MODEL is not None,
        timestamp=datetime.now().isoformat()
    )

@app.post("/predict", response_model=PredictionResponse)
async def predict_stock(request: StockPredictionRequest):
    """单个股票预测接口"""
    start_time = datetime.now()
    
    if TIMESFM_MODEL is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    
    try:
        result = predict_single_stock(request)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return PredictionResponse(
            success=True,
            stock_code=request.stock_code,
            gpu_id=GPU_ID,
            message="预测成功",
            data=result,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)
        
        logger.error(f"预测失败: {error_msg}")
        
        return PredictionResponse(
            success=False,
            stock_code=request.stock_code,
            gpu_id=GPU_ID,
            message="预测失败",
            error=error_msg,
            processing_time=processing_time
        )

@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_stocks_batch(request: BatchPredictionRequest):
    """批量股票预测接口"""
    start_time = datetime.now()
    
    if TIMESFM_MODEL is None:
        raise HTTPException(status_code=503, detail="模型未加载")
    
    results = []
    successful_count = 0
    failed_count = 0
    
    for stock_code in request.stock_codes:
        try:
            # 创建单个股票请求
            single_request = StockPredictionRequest(
                stock_code=stock_code,
                stock_type=request.stock_type,
                time_step=request.time_step,
                years=request.years,
                horizon_len=request.horizon_len,
                context_len=request.context_len,
                include_technical_indicators=request.include_technical_indicators
            )
            
            # 执行预测
            result = predict_single_stock(single_request)
            
            results.append(PredictionResponse(
                success=True,
                stock_code=stock_code,
                gpu_id=GPU_ID,
                message="预测成功",
                data=result
            ))
            
            successful_count += 1
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"批量预测中股票 {stock_code} 失败: {error_msg}")
            
            results.append(PredictionResponse(
                success=False,
                stock_code=stock_code,
                gpu_id=GPU_ID,
                message="预测失败",
                error=error_msg
            ))
            
            failed_count += 1
    
    total_processing_time = (datetime.now() - start_time).total_seconds()
    
    return BatchPredictionResponse(
        success=successful_count > 0,
        gpu_id=GPU_ID,
        total_stocks=len(request.stock_codes),
        successful_predictions=successful_count,
        failed_predictions=failed_count,
        total_processing_time=total_processing_time,
        results=results
    )

@app.post("/predict/chunked", response_model=ChunkedPredictionResponse)
async def predict_chunked(request: ChunkedPredictionRequest):
    """分块预测接口 - 模式1：固定训练集分块预测"""
    try:
        logger.info(f"开始分块预测股票 {request.stock_code}，模式1：固定训练集")
        logger.info(f"参数: horizon_len={request.horizon_len}, fixed_end_date={request.fixed_end_date}")
        
        # 执行分块预测
        result = predict_chunked_mode1(request)
        
        return ChunkedPredictionResponse(
            success=result['success'],
            stock_code=result['stock_code'],
            gpu_id=result['gpu_id'],
            prediction_mode=result['prediction_mode'],
            total_chunks=result['total_chunks'],
            successful_chunks=result['successful_chunks'],
            failed_chunks=result['failed_chunks'],
            total_processing_time=result['total_processing_time'],
            chunk_results=result['chunk_results'],
            summary=result['summary']
        )
        
    except Exception as e:
        logger.error(f"分块预测失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"分块预测失败: {str(e)}")

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