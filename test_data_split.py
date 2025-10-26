#!/usr/bin/env python3
"""
测试数据切分逻辑
"""
import sys
import os

# 添加preprocess_data路径
preprocess_dir = os.path.join(os.path.dirname(__file__), 'preprocess_data')
sys.path.append(preprocess_dir)

from process_from_ak import df_preprocess

def test_data_split():
    """测试数据切分功能"""
    print("🧪 开始测试数据切分逻辑...")
    
    # 测试参数
    stock_code = "sh600439"  # 工商银行
    stock_type = "stock"
    time_step = 0
    years = 2  # 使用较短时间以便快速测试
    horizon_len = 7
    
    print(f"📋 测试参数: stock_code={stock_code}, horizon_len={horizon_len}")
    
    try:
        df_train, df_test, stock_info = df_preprocess(
            stock_code=stock_code,
            stock_type=stock_type, 
            time_step=time_step,
            years=years,
            horizon_len=horizon_len
        )
        
        if df_train is not None and df_test is not None:
            print(f"✅ 数据切分成功!")
            print(f"📊 训练集长度: {len(df_train)} (应该是{horizon_len}的整数倍: {len(df_train) % horizon_len == 0})")
            print(f"📊 测试集长度: {len(df_test)} (应该是{horizon_len}的整数倍: {len(df_test) % horizon_len == 0})")
            
            # 验证是否为整数倍
            if len(df_train) % horizon_len == 0 and len(df_test) % horizon_len == 0:
                print("🎉 数据切分逻辑验证成功！训练集和测试集都是horizon_len的整数倍")
            else:
                print("❌ 数据切分逻辑有问题！")
        else:
            print("❌ 数据获取失败")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_data_split()