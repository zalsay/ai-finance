#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的SCF数据转换逻辑
"""

import sys
import os
import pandas as pd
from datetime import datetime

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from get_finanial_data import get_stock_data_from_scf, convert_dataframe_to_api_format
    print("✅ 成功导入修复后的函数")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

def test_fixed_scf_data():
    """测试修复后的SCF数据获取和转换"""
    print("=== 测试修复后的SCF数据转换逻辑 ===\n")
    
    # 测试股票代码
    symbol = "600398"
    start_date = "20240101"
    
    print(f"1. 测试修复后的get_stock_data_from_scf函数")
    print(f"股票代码: {symbol}")
    print(f"开始日期: {start_date}")
    
    # 获取数据
    df = get_stock_data_from_scf(symbol, start_date=start_date, end_date="20241102")
    
    if df is not None and not df.empty:
        print(f"✅ 成功获取数据")
        print(f"DataFrame形状: {df.shape}")
        print(f"列名: {list(df.columns)}")
        
        # 检查日期转换
        print(f"\n2. 检查日期转换结果:")
        if 'datetime' in df.columns:
            print(f"日期列类型: {df['datetime'].dtype}")
            print(f"最早日期: {df['datetime'].min()}")
            print(f"最晚日期: {df['datetime'].max()}")
            print(f"前3条日期样本:")
            for i, dt in enumerate(df['datetime'].head(3)):
                print(f"  {i+1}. {dt}")
        
        # 检查数值字段
        print(f"\n3. 检查数值字段:")
        numeric_fields = ['amount', 'amplitude', 'percentage_change', 'amount_change', 'turnover_rate']
        for field in numeric_fields:
            if field in df.columns:
                non_zero_count = (df[field] != 0.0).sum()
                print(f"  {field}: 非零值数量 = {non_zero_count}/{len(df)}")
                if non_zero_count > 0:
                    print(f"    样本值: {df[field][df[field] != 0.0].head(3).tolist()}")
            else:
                print(f"  {field}: ❌ 字段缺失")
        
        # 显示前5条完整记录
        print(f"\n4. 前5条完整记录:")
        print(df.head().to_string())
        
        # 测试API格式转换
        print(f"\n5. 测试API格式转换:")
        api_data = convert_dataframe_to_api_format(df.head(3), symbol, stock_type=1)
        if api_data:
            print(f"✅ 成功转换为API格式，共 {len(api_data)} 条记录")
            print("第1条API数据样本:")
            for key, value in api_data[0].items():
                print(f"  {key}: {value} ({type(value).__name__})")
        else:
            print("❌ API格式转换失败")
            
    else:
        print("❌ 获取数据失败")

if __name__ == "__main__":
    test_fixed_scf_data()