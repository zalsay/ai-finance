#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
akshare数据预处理方案使用示例

本脚本展示如何使用akshare数据预处理方案获取和处理股票数据
包含完整的数据获取、处理、保存和加载流程示例

作者: AI Assistant
创建时间: 2025-01-08
"""

import os
import sys
import logging
import pickle
import pandas as pd
from datetime import datetime, timedelta

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入自定义模块
from akshare_data_preprocess import AkshareDataPreprocessor
from akshare_data_preprocess_simple import SimpleAkshareDataPreprocessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('example_usage.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def example_simple_usage():
    """
    简单使用示例：使用预设参数快速获取数据
    """
    logger.info("=== 简单使用示例 ===")
    
    try:
        # 1. 创建简单预处理器实例
        processor = SimpleAkshareDataPreprocessor()
        
        # 2. 加载和处理数据
        logger.info("开始数据处理...")
        result = processor.load_and_process_data()
        
        # 3. 显示处理结果
        if result:
            logger.info(f"处理成功！共处理 {len(result)} 个股票")
            for item in result:
                symbol = item['symbol']
                data_shape = item['data'].shape
                date_range = f"{item['data'].index[0]} 到 {item['data'].index[-1]}"
                logger.info(f"  {symbol}: {data_shape[0]} 条记录, 时间范围: {date_range}")
        else:
            logger.warning("数据处理失败")
            
    except Exception as e:
        logger.error(f"简单使用示例执行失败: {e}")
        return False
    
    return True

def example_custom_usage():
    """
    自定义使用示例：使用自定义参数获取数据
    """
    logger.info("=== 自定义使用示例 ===")
    
    try:
        # 1. 自定义配置参数
        custom_config = {
            'symbols': ['000001', '000002', '600000', '600036'],  # 自定义股票列表
            'start_date': '2023-01-01',  # 自定义开始日期
            'end_date': '2023-12-31',    # 自定义结束日期
            'features': ['open', 'close', 'high', 'low', 'vol', 'amt'],  # 自定义特征
            'save_path': './custom_data.pkl'  # 自定义保存路径
        }
        
        # 2. 创建完整预处理器实例
        processor = AkshareDataPreprocessor(
            symbols=custom_config['symbols'],
            start_date=custom_config['start_date'],
            end_date=custom_config['end_date'],
            features=custom_config['features']
        )
        
        # 3. 逐步处理数据
        logger.info("开始获取股票数据...")
        raw_data = processor.get_stock_data()
        
        if raw_data:
            logger.info("开始处理数据...")
            processed_data = processor.process_data(raw_data)
            
            if processed_data:
                logger.info("开始保存数据...")
                success = processor.save_data(processed_data, custom_config['save_path'])
                
                if success:
                    logger.info(f"数据已保存到: {custom_config['save_path']}")
                    return True
        
        logger.warning("自定义数据处理失败")
        return False
        
    except Exception as e:
        logger.error(f"自定义使用示例执行失败: {e}")
        return False

def example_data_analysis():
    """
    数据分析示例：加载已处理的数据并进行基本分析
    """
    logger.info("=== 数据分析示例 ===")
    
    try:
        # 1. 加载已处理的数据
        data_file = 'processed_data_akshare_simple.pkl'
        if not os.path.exists(data_file):
            logger.warning(f"数据文件 {data_file} 不存在，请先运行数据处理")
            return False
        
        with open(data_file, 'rb') as f:
            data = pickle.load(f)
        
        logger.info(f"成功加载数据，包含 {len(data)} 个股票")
        
        # 2. 对每个股票进行基本分析
        for item in data:
            symbol = item['symbol']
            df = item['data']
            
            logger.info(f"\n--- 股票 {symbol} 分析 ---")
            logger.info(f"数据形状: {df.shape}")
            logger.info(f"时间范围: {df.index[0]} 到 {df.index[-1]}")
            logger.info(f"列名: {list(df.columns)}")
            
            # 基本统计信息
            logger.info("基本统计信息:")
            for col in df.columns:
                mean_val = df[col].mean()
                std_val = df[col].std()
                min_val = df[col].min()
                max_val = df[col].max()
                logger.info(f"  {col}: 均值={mean_val:.4f}, 标准差={std_val:.4f}, 最小值={min_val:.4f}, 最大值={max_val:.4f}")
            
            # 计算收益率
            if 'close' in df.columns:
                returns = df['close'].pct_change().dropna()
                logger.info(f"收益率统计: 均值={returns.mean():.6f}, 标准差={returns.std():.6f}")
                logger.info(f"最大涨幅: {returns.max():.4f}, 最大跌幅: {returns.min():.4f}")
        
        return True
        
    except Exception as e:
        logger.error(f"数据分析示例执行失败: {e}")
        return False

def example_data_export():
    """
    数据导出示例：将处理后的数据导出为不同格式
    """
    logger.info("=== 数据导出示例 ===")
    
    try:
        # 1. 加载已处理的数据
        data_file = 'processed_data_akshare_simple.pkl'
        if not os.path.exists(data_file):
            logger.warning(f"数据文件 {data_file} 不存在，请先运行数据处理")
            return False
        
        with open(data_file, 'rb') as f:
            data = pickle.load(f)
        
        # 2. 创建导出目录
        export_dir = 'exported_data'
        os.makedirs(export_dir, exist_ok=True)
        
        # 3. 导出为CSV格式
        logger.info("导出为CSV格式...")
        for item in data:
            symbol = item['symbol']
            df = item['data']
            csv_file = os.path.join(export_dir, f"{symbol}.csv")
            df.to_csv(csv_file, encoding='utf-8')
            logger.info(f"  {symbol} 已导出到: {csv_file}")
        
        # 4. 导出为Excel格式（合并所有股票）
        logger.info("导出为Excel格式...")
        excel_file = os.path.join(export_dir, 'all_stocks.xlsx')
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            for item in data:
                symbol = item['symbol']
                df = item['data']
                # Excel工作表名称不能包含特殊字符
                sheet_name = symbol.replace('SH', '').replace('SZ', '')
                df.to_excel(writer, sheet_name=sheet_name)
                logger.info(f"  {symbol} 已添加到Excel工作表: {sheet_name}")
        
        logger.info(f"所有数据已导出到: {excel_file}")
        
        # 5. 导出汇总统计信息
        logger.info("生成汇总统计信息...")
        summary_data = []
        for item in data:
            symbol = item['symbol']
            df = item['data']
            summary = {
                '股票代码': symbol,
                '数据条数': len(df),
                '开始日期': str(df.index[0].date()),
                '结束日期': str(df.index[-1].date()),
                '平均收盘价': df['close'].mean(),
                '最高价': df['high'].max(),
                '最低价': df['low'].min(),
                '平均成交量': df['vol'].mean(),
                '总成交额': df['amt'].sum()
            }
            summary_data.append(summary)
        
        summary_df = pd.DataFrame(summary_data)
        summary_file = os.path.join(export_dir, 'summary.csv')
        summary_df.to_csv(summary_file, index=False, encoding='utf-8')
        logger.info(f"汇总统计信息已保存到: {summary_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"数据导出示例执行失败: {e}")
        return False

def main():
    """
    主函数：运行所有示例
    """
    logger.info("开始运行akshare数据预处理使用示例")
    
    examples = [
        ("简单使用示例", example_simple_usage),
        ("数据分析示例", example_data_analysis),
        ("数据导出示例", example_data_export),
        # ("自定义使用示例", example_custom_usage),  # 可选：需要更长时间
    ]
    
    results = {}
    
    for name, func in examples:
        logger.info(f"\n{'='*50}")
        logger.info(f"运行: {name}")
        logger.info(f"{'='*50}")
        
        try:
            success = func()
            results[name] = success
            if success:
                logger.info(f"{name} 执行成功")
            else:
                logger.warning(f"{name} 执行失败")
        except Exception as e:
            logger.error(f"{name} 执行异常: {e}")
            results[name] = False
    
    # 输出总结
    logger.info(f"\n{'='*50}")
    logger.info("执行结果总结")
    logger.info(f"{'='*50}")
    
    for name, success in results.items():
        status = "✓ 成功" if success else "✗ 失败"
        logger.info(f"{name}: {status}")
    
    success_count = sum(results.values())
    total_count = len(results)
    logger.info(f"\n总计: {success_count}/{total_count} 个示例执行成功")
    
    if success_count == total_count:
        logger.info("所有示例执行成功！akshare数据预处理方案工作正常。")
    else:
        logger.warning("部分示例执行失败，请检查错误日志。")

if __name__ == "__main__":
    main()