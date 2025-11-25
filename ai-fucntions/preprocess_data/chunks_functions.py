import pandas as pd
from typing import List

# 分块预测相关函数

# 分块测试数据函数
def create_chunks_from_test_data(df_test: pd.DataFrame, horizon_len: int) -> List[pd.DataFrame]:
    """
    根据horizon_len对测试数据进行分块
    
    Args:
        df_test: 测试数据DataFrame
        horizon_len: 每个分块的长度
        
    Returns:
        List[pd.DataFrame]: 分块后的数据列表（仅包含完整分块，残缺分块舍弃）
    """
    chunks = []
    total_length = len(df_test)
    if horizon_len <= 0:
        print("horizon_len 必须为正数")
        return chunks
    full_chunks = total_length // horizon_len
    for idx in range(full_chunks):
        start_idx = idx * horizon_len
        end_idx = start_idx + horizon_len
        chunk = df_test.iloc[start_idx:end_idx].copy()
        chunks.append(chunk)
    remainder = total_length % horizon_len
    print(f"数据分块完成: 总长度 {total_length}, 分块数量 {len(chunks)}, 每块长度 {horizon_len}, 舍弃残缺长度 {remainder}")
    return chunks

# 分块推理函数
def create_chunks_from_inference_data(df_inference: pd.DataFrame, horizon_len: int) -> List[pd.DataFrame]:
    """
    根据horizon_len对推理数据进行分块
    
    Args:
        df_inference: 推理数据DataFrame
        horizon_len: 每个分块的长度
        
    Returns:
        List[pd.DataFrame]: 分块后的数据列表
    """
    chunks = []
    total_length = len(df_inference)
    
    for i in range(0, total_length, horizon_len):
        end_idx = min(i + horizon_len, total_length)
        chunk = df_inference.iloc[i:end_idx].copy()
        
        if len(chunk) > 0:  # 确保分块不为空
            chunks.append(chunk)
    
    print(f"推理数据分块完成: 总长度 {total_length}, 分块数量 {len(chunks)}, 每块长度 {horizon_len}")
    return chunks