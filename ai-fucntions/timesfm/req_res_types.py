from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# 分块预测相关的数据模型类
@dataclass
class ChunkedPredictionRequest:
    """分块预测请求模型"""
    stock_code: str
    years: int = 10
    horizon_len: int = 7
    start_date: Optional[str] = "2025-06-30"
    end_date: Optional[str] = "2025-06-30"
    context_len: int = 2048
    time_step: int = 0
    stock_type: str = 'stock'
    chunk_num: int = 1


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
    overall_metrics: Dict[str, float]
    processing_time: float
    # 新增拼接结果字段
    concatenated_predictions: Optional[Dict[str, List[float]]] = None  # 拼接后的完整预测结果
    concatenated_actual: Optional[List[float]] = None  # 拼接后的完整实际值
    concatenated_dates: Optional[List[str]] = None  # 拼接后的完整日期序列