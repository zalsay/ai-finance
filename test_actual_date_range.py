#!/usr/bin/env python3
"""
测试实际值日期范围显示功能
"""

import sys
import os

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
timesfm_dir = os.path.join(current_dir, 'timesfm')
sys.path.append(timesfm_dir)

# 模拟测试数据
from req_res_types import ChunkPredictionResult

def test_date_range_display():
    """测试日期范围显示功能"""
    
    # 创建模拟的分块预测结果
    mock_chunk_result = ChunkPredictionResult(
        chunk_index=0,
        chunk_start_date="2024-01-01",
        chunk_end_date="2024-01-07",
        predictions={
            'timesfm-q-0.5': [100.1, 101.2, 102.3, 103.4, 104.5, 105.6, 106.7]
        },
        actual_values=[100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
        metrics={
            'mse': 0.1,
            'mae': 0.05,
            'best_quantile': 'timesfm-q-0.5',
            'best_combined_score': 0.075,
            'all_quantile_metrics': {}
        }
    )
    
    print("=== 测试日期范围显示 ===")
    print(f"分块 1:")
    print(f"  索引: {mock_chunk_result.chunk_index}")
    print(f"  预测日期范围: {mock_chunk_result.chunk_start_date} 到 {mock_chunk_result.chunk_end_date}")
    print(f"  实际值日期范围: {mock_chunk_result.chunk_start_date} 到 {mock_chunk_result.chunk_end_date}")
    print(f"  实际值数量: {len(mock_chunk_result.actual_values)}")
    print(f"  预测列数量: {len(mock_chunk_result.predictions)}")
    
    if mock_chunk_result.actual_values and mock_chunk_result.predictions:
        print(f"  前3个实际值: {mock_chunk_result.actual_values[:3]}")
        if 'timesfm-q-0.5' in mock_chunk_result.predictions:
            pred_values = mock_chunk_result.predictions['timesfm-q-0.5']
            print(f"  前3个预测值: {pred_values[:3]}")
    
    print("\n=== 文件输出格式测试 ===")
    print(f"分块 {mock_chunk_result.chunk_index + 1}:")
    print(f"  预测日期范围: {mock_chunk_result.chunk_start_date} 到 {mock_chunk_result.chunk_end_date}")
    print(f"  实际值日期范围: {mock_chunk_result.chunk_start_date} 到 {mock_chunk_result.chunk_end_date}")
    print(f"  指标: {mock_chunk_result.metrics}")
    print(f"  实际值: {mock_chunk_result.actual_values}")
    print(f"  预测值: {mock_chunk_result.predictions}")
    
    print("\n✅ 日期范围显示功能测试完成")

if __name__ == "__main__":
    test_date_range_display()