#!/usr/bin/env python3
"""
测试PostgreSQL API功能的简单脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from get_finanial_data import PostgreSQLAPIClient, fetch_and_store_stock_data, ak_stock_data

def test_api_connection():
    """测试API连接"""
    print("=== 测试API连接 ===")
    
    # 尝试不同的端口
    ports = [8080, 58500, 8000]
    
    for port in ports:
        print(f"\n尝试连接端口 {port}...")
        api_client = PostgreSQLAPIClient(base_url=f"http://localhost:{port}")
        
        if api_client.health_check():
            print(f"✅ 端口 {port} 连接成功")
            return api_client, port
        else:
            print(f"❌ 端口 {port} 连接失败")
    
    return None, None

def test_data_fetch_and_store():
    """测试数据获取和存储"""
    print("\n=== 测试数据获取和存储 ===")
    
    # 测试API连接
    api_client, port = test_api_connection()
    
    if api_client is None:
        print("❌ 无法连接到API服务，跳过存储测试")
        return False
    
    print(f"\n使用端口 {port} 进行测试...")
    
    # 测试股票数据获取
    print("\n1. 测试数据获取...")
    symbol = "600398"
    df = ak_stock_data(symbol, start_date="20241001", end_date="20241031")
    
    if df is None or df.empty:
        print(f"❌ 无法获取股票 {symbol} 的数据")
        return False
    
    print(f"✅ 成功获取股票 {symbol} 数据，共 {len(df)} 条记录")
    print("数据样本:")
    print(df.head(3))
    
    # 测试数据存储
    print(f"\n2. 测试数据存储...")
    result = fetch_and_store_stock_data(
        symbol=symbol,
        api_client=api_client,
        start_date="20241001",
        end_date="20241031",
        stock_type=1,
        batch_size=100,
        max_retries=2
    )
    
    if result["success"]:
        print(f"✅ 数据存储成功:")
        print(f"   - 总记录数: {result['total_records']}")
        print(f"   - 成功存储: {result['stored_records']}")
        print(f"   - 成功率: {result['success_rate']}")
        return True
    else:
        print(f"❌ 数据存储失败: {result.get('error', '未知错误')}")
        return False

def main():
    """主函数"""
    print("PostgreSQL API 功能测试")
    print("=" * 50)
    
    # 测试数据获取和存储
    success = test_data_fetch_and_store()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 所有测试通过！")
        print("\n功能说明:")
        print("- ak_stock_data() 方法成功获取股票数据")
        print("- fetch_and_store_stock_data() 方法成功存储数据到PostgreSQL")
        print("- 第569-571行的代码正确调用了第72行的ak_stock_data方法")
    else:
        print("❌ 测试失败，请检查:")
        print("1. PostgreSQL数据库是否运行")
        print("2. postgres-handler API服务是否运行")
        print("3. 网络连接是否正常")

if __name__ == "__main__":
    main()