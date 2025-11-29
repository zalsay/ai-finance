from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# 分块预测相关的数据模型类
@dataclass
class ChunkedPredictionRequest:
    """分块预测请求模型"""
    stock_code: str
    years: int = 10
    horizon_len: int = 7
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    context_len: int = 2048
    time_step: int = 0
    stock_type: str = 1
    timesfm_version: str = "2.5"
    user_id: Optional[int] = None


@dataclass
class ChunkPredictionResult:
    """单个分块的预测结果"""
    chunk_index: int
    chunk_start_date: str
    chunk_end_date: str
    predictions: Dict[str, List[float]]  # 包含不同分位数的预测结果
    actual_values: List[float]
    metrics: Dict[str, float]  # MSE, MAE等指标


@dataclass
class ChunkedPredictionResponse:
    """分块预测响应"""
    stock_code: str
    total_chunks: int
    horizon_len: int
    chunk_results: List[ChunkPredictionResult]
    overall_metrics: Dict[str, Any]
    processing_time: float
    # 新增拼接结果字段
    concatenated_predictions: Optional[Dict[str, List[float]]] = None  # 拼接后的完整预测结果
    concatenated_actual: Optional[List[float]] = None  # 拼接后的完整实际值
    concatenated_dates: Optional[List[str]] = None  # 拼接后的完整日期序列
    # 新增验证集分块结果（用于在验证集上进行回测）
    validation_chunk_results: Optional[List[ChunkPredictionResult]] = None
