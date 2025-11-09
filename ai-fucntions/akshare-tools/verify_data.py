#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证数据库中存储的股票数据
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from get_finanial_data import PostgreSQLAPIClient

def verify_stored_data():
    """验证数据库中存储的数据"""
    print("=== 验证数据库中存储的股票数据 ===\n")
    
    try:
        client = PostgreSQLAPIClient()
        print("✅ API客户端初始化成功")
        
        # 检查API服务状态
        if not client.health_check():
            print("❌ API服务不可用")
            return
        
        print("✅ API服务正常")
        
        # 查询股票数据
        symbol = "600398"
        print(f"\n正在查询股票 {symbol} 的最新数据...")
        
        data = client.get_stock_data(symbol, limit=5)
        
        if data and len(data) > 0:
            print(f"✅ 成功获取 {len(data)} 条记录")
            
            for i, record in enumerate(data):
                print(f"\n记录 {i+1}:")
                print(f"  日期: {record.get('datetime', 'N/A')}")
                print(f"  开盘价: {record.get('open', 'N/A')}")
                print(f"  收盘价: {record.get('close', 'N/A')}")
                print(f"  最高价: {record.get('high', 'N/A')}")
                print(f"  最低价: {record.get('low', 'N/A')}")
                print(f"  成交量: {record.get('volume', 'N/A')}")
                print(f"  成交额: {record.get('amount', 'N/A')}")
                print(f"  振幅: {record.get('amplitude', 'N/A')}%")
                print(f"  涨跌幅: {record.get('percentage_change', 'N/A')}%")
                print(f"  涨跌额: {record.get('amount_change', 'N/A')}")
                print(f"  换手率: {record.get('turnover_rate', 'N/A')}%")
            
            # 检查数据质量
            print(f"\n=== 数据质量检查 ===")
            
            # 检查日期格式
            first_record = data[0]
            datetime_value = first_record.get('datetime', '')
            if '1970-01-01' in str(datetime_value):
                print("❌ 日期转换仍有问题")
            else:
                print("✅ 日期转换正常")
            
            # 检查数值字段
            numeric_fields = ['amount', 'amplitude', 'percentage_change', 'amount_change', 'turnover_rate']
            for field in numeric_fields:
                value = first_record.get(field, 0)
                if value == 0.0:
                    print(f"⚠️  {field} 为 0.0")
                else:
                    print(f"✅ {field} 有数值: {value}")
                    
        else:
            print("❌ 未获取到数据或数据为空")
            
    except Exception as e:
        print(f"❌ 验证过程出错: {str(e)}")

if __name__ == "__main__":
    verify_stored_data()