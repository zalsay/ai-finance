#!/usr/bin/env python3
"""
测试分位数评估功能
"""
import sys
import os
import pandas as pd
import numpy as np

# 添加timesfm路径
timesfm_dir = os.path.join(os.path.dirname(__file__), 'timesfm')
sys.path.append(timesfm_dir)

from predict_chunked_functinos import predict_single_chunk_mode1

def create_mock_tfm():
    """创建模拟的TimesFM模型"""
    class MockTFM:
        def forecast_on_df(self, inputs, freq, value_name, num_jobs):
            # 创建模拟的预测结果
            horizon_len = len(inputs)
            dates = pd.date_range(start='2024-01-01', periods=horizon_len, freq='D')
            
            # 生成模拟的分位数预测
            base_values = np.random.normal(6.5, 0.5, horizon_len)
            
            forecast_data = {
                'ds': dates,
                'timesfm-q-0.1': base_values - 0.4,
                'timesfm-q-0.2': base_values - 0.3,
                'timesfm-q-0.3': base_values - 0.2,
                'timesfm-q-0.4': base_values - 0.1,
                'timesfm-q-0.5': base_values,
                'timesfm-q-0.6': base_values + 0.1,
                'timesfm-q-0.7': base_values + 0.2,
                'timesfm-q-0.8': base_values + 0.3,
                'timesfm-q-0.9': base_values + 0.4,
            }
            
            return pd.DataFrame(forecast_data)
    
    return MockTFM()

def create_mock_chunk():
    """创建模拟的数据分块"""
    horizon_len = 5
    dates = pd.date_range(start='2024-01-01', periods=horizon_len, freq='D')
    
    # 创建模拟的实际股价数据
    actual_prices = [6.8, 6.67, 6.58, 6.61, 6.75]
    
    chunk_data = {
        'ds': dates,
        'close': actual_prices,
        'stock_code': ['600398'] * horizon_len
    }
    
    return pd.DataFrame(chunk_data)

def test_quantile_evaluation():
    """测试分位数评估功能"""
    print("🧪 开始测试分位数评估功能...")
    
    # 创建模拟数据和模型
    mock_tfm = create_mock_tfm()
    mock_chunk = create_mock_chunk()
    
    print(f"📋 测试数据:")
    print(f"  分块大小: {len(mock_chunk)}")
    print(f"  实际价格: {mock_chunk['close'].tolist()}")
    
    try:
        # 执行预测
        result = predict_single_chunk_mode1(
            chunk=mock_chunk,
            tfm=mock_tfm,
            chunk_index=0
        )
        
        print(f"\n✅ 预测成功!")
        print(f"📊 评估结果:")
        print(f"  最优分位数: {result.metrics['best_quantile']}")
        print(f"  最优综合得分: {result.metrics['best_combined_score']:.6f}")
        print(f"  最优MSE: {result.metrics['mse']:.6f}")
        print(f"  最优MAE: {result.metrics['mae']:.6f}")
        
        print(f"\n📈 所有分位数评估:")
        for quantile, metrics in result.metrics['all_quantile_metrics'].items():
            print(f"  {quantile}: MSE={metrics['mse']:.6f}, MAE={metrics['mae']:.6f}, 综合得分={metrics['combined_score']:.6f}")
        
        print(f"\n🎯 预测值 (最优分位数 {result.metrics['best_quantile']}):")
        best_predictions = result.predictions[result.metrics['best_quantile']]
        for i, (actual, pred) in enumerate(zip(result.actual_values, best_predictions)):
            print(f"  第{i+1}天: 实际={actual}, 预测={pred:.4f}, 误差={abs(actual-pred):.4f}")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_quantile_evaluation()