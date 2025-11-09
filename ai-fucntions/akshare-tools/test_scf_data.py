#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SCF云函数返回的原始数据格式
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from get_finanial_data import scf_invoke, get_stock_data_from_scf
import json
import pandas as pd
from datetime import datetime

def test_scf_raw_data():
    """测试SCF返回的原始数据"""
    print("=== 测试SCF云函数原始数据格式 ===")
    
    # 测试参数
    symbol = "600398"
    start_date = "20240101"
    end_date = None
    
    try:
        # 1. 测试SCF原始调用
        print(f"\n1. 测试SCF原始调用 - 股票代码: {symbol}")
        event_params = {
            "functionName": "get_financial_data",
            "type": "stock", 
            "code": f"sh{symbol}",
            "start_date": start_date,
            "end_date": end_date
        }
        
        print(f"调用参数: {event_params}")
        raw_response = scf_invoke(event_params)
        print(f"原始响应类型: {type(raw_response)}")
        print(f"原始响应长度: {len(str(raw_response))}")
        
        # 解析响应
        if isinstance(raw_response, str):
            data = json.loads(raw_response)
        else:
            data = raw_response
            
        print(f"解析后数据类型: {type(data)}")
        print(f"响应状态码: {data.get('code', 'N/A')}")
        print(f"响应消息: {data.get('message', 'N/A')}")
        
        if "data" in data and data["data"]:
            sample_data = data["data"][:3]  # 取前3条数据
            print(f"数据条数: {len(data['data'])}")
            print(f"前3条样本数据:")
            for i, record in enumerate(sample_data, 1):
                print(f"  记录 {i}: {record}")
                print(f"    数据类型: {type(record)}")
                if isinstance(record, dict):
                    print(f"    字段: {list(record.keys())}")
        
        # 2. 测试处理后的DataFrame
        print(f"\n2. 测试get_stock_data_from_scf函数")
        df = get_stock_data_from_scf(symbol, start_date=start_date, end_date=end_date)
        
        if df is not None and not df.empty:
            print(f"DataFrame形状: {df.shape}")
            print(f"DataFrame列名: {list(df.columns)}")
            print(f"DataFrame数据类型:")
            for col in df.columns:
                print(f"  {col}: {df[col].dtype}")
            
            print(f"\n前5行数据:")
            print(df.head())
            
            print(f"\n数据统计:")
            print(df.describe())
            
        else:
            print("❌ 未获取到DataFrame数据")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scf_raw_data()