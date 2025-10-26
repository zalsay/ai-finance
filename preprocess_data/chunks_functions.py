import pandas as pd
from typing import List

# 分块预测相关函数
def create_chunks_from_test_data(df_test: pd.DataFrame, horizon_len: int) -> List[pd.DataFrame]:
    """
    根据horizon_len对测试数据进行分块
    
    Args:
        df_test: 测试数据DataFrame
        horizon_len: 每个分块的长度
        
    Returns:
        List[pd.DataFrame]: 分块后的数据列表
    """
    chunks = []
    total_length = len(df_test)
    
    for i in range(0, total_length, horizon_len):
        end_idx = min(i + horizon_len, total_length)
        chunk = df_test.iloc[i:end_idx].copy()
        
        if len(chunk) > 0:  # 确保分块不为空
            chunks.append(chunk)
    
    print(f"测试数据分块完成: 总长度 {total_length}, 分块数量 {len(chunks)}, 每块长度 {horizon_len}")
    return chunks