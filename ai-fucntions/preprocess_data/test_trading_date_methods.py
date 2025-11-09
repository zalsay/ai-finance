#!/usr/bin/env python3
"""
测试交易日期处理方法
"""

from trading_date_processor import get_previous_trading_days, get_trading_date_range
from datetime import datetime, date

def test_get_previous_trading_days():
    """测试获取前n天交易日的方法"""
    print("=" * 60)
    print("测试 get_previous_trading_days 方法")
    print("=" * 60)
    
    # 测试1: 获取前5个交易日（使用今天作为参考日期）
    print("\n1. 获取前5个交易日（参考日期：今天）")
    result1 = get_previous_trading_days(days=5)
    print(f"结果: {result1}")
    
    # 测试2: 获取前10个交易日（使用指定日期）
    print("\n2. 获取前10个交易日（参考日期：2024-11-01）")
    result2 = get_previous_trading_days(reference_date="2024-11-01", days=10)
    print(f"结果: {result2}")
    
    # 测试3: 获取前3个交易日（使用datetime对象）
    print("\n3. 获取前3个交易日（参考日期：datetime对象）")
    ref_date = datetime(2024, 10, 15)
    result3 = get_previous_trading_days(reference_date=ref_date, days=3)
    print(f"结果: {result3}")

def test_get_trading_date_range():
    """测试获取连续交易日的方法"""
    print("\n" + "=" * 60)
    print("测试 get_trading_date_range 方法")
    print("=" * 60)
    
    # 测试1: 从指定日期开始获取5个交易日
    print("\n1. 从2024-10-01开始获取5个交易日")
    result1 = get_trading_date_range(start_date="2024-10-01", days=5)
    print(f"结果: {result1}")
    
    # 测试2: 从指定日期开始获取15个交易日
    print("\n2. 从2024-09-01开始获取15个交易日")
    result2 = get_trading_date_range(start_date="2024-09-01", days=15)
    print(f"结果: {result2}")
    
    # 测试3: 从datetime对象开始获取7个交易日
    print("\n3. 从datetime对象开始获取7个交易日")
    start_dt = datetime(2024, 8, 1)
    result3 = get_trading_date_range(start_date=start_dt, days=7)
    print(f"结果: {result3}")

def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 60)
    print("测试边界情况")
    print("=" * 60)
    
    # 测试1: 获取1个交易日
    print("\n1. 获取前1个交易日")
    result1 = get_previous_trading_days(days=1)
    print(f"结果: {result1}")
    
    # 测试2: 获取大量交易日
    print("\n2. 获取前50个交易日")
    result2 = get_previous_trading_days(days=50)
    print(f"结果数量: {len(result2)}")
    print(f"第一个: {result2[0] if result2 else 'None'}")
    print(f"最后一个: {result2[-1] if result2 else 'None'}")
    
    # 测试3: 周末日期作为参考
    print("\n3. 使用周末日期作为参考（2024-10-06是周日）")
    result3 = get_previous_trading_days(reference_date="2024-10-06", days=3)
    print(f"结果: {result3}")

if __name__ == "__main__":
    try:
        test_get_previous_trading_days()
        test_get_trading_date_range()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()