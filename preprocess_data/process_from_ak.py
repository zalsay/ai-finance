import os
import sys
import numpy as np
import pandas as pd
import warnings
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# 忽略警告
warnings.filterwarnings("ignore")

# 添加akshare工具路径
current_dir = os.path.dirname(os.path.abspath(__file__))
finance_dir = os.path.dirname(current_dir)  # 上级目录
akshare_dir = os.path.join(finance_dir, 'akshare-tools')
sys.path.append(akshare_dir)
from get_finanial_data import ak_stock_data, get_stock_list, get_index_data, talib_tools

def df_preprocess(stock_code, stock_type, time_step, years=10, horizon_len=7):
    """
    预处理股票数据
    
    Args:
        stock_code: 股票代码
        stock_type: 股票类型
        time_step: 时间步长
        years: 获取多少年的数据
        horizon_len: 预测长度
        
    Returns:
        tuple: (df, df_train, df_test) 或 (None, None, None) 如果失败
    """
    try:
        # 获取股票数据
        df = ak_stock_data(stock_code, start_date="19900101", years=years, time_step=time_step)
        
        # 检查数据是否成功获取
        if df is None:
            print(f"❌ 无法获取股票 {stock_code} 的数据")
            return None, None, None
        
        if df.empty:
            print(f"❌ 股票 {stock_code} 返回空数据")
            return None, None, None
        
        # 检查数据质量
        if len(df) < horizon_len * 2:
            print(f"❌ 股票 {stock_code} 数据量不足 (仅有 {len(df)} 条记录，需要至少 {horizon_len * 2} 条)")
            return None, None, None
        
        # 检查必要的列是否存在
        required_columns = ['close']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ 股票 {stock_code} 数据缺少必要列: {missing_columns}")
            return None, None, None
        
        df["stock_code"] = stock_code
    
        # 确保datetime列是正确的日期格式
        try:
            if 'datetime' in df.columns:
                df['ds'] = pd.to_datetime(df['datetime'])
            else:
                # 如果没有datetime列，尝试从索引获取
                df['ds'] = pd.to_datetime(df.index)
        except Exception as e:
            print(f"❌ 股票 {stock_code} 日期格式转换失败: {str(e)}")
            return None, None, None
        
        # 创建专门用于绘图的日期列（字符串格式）
        try:
            df['ds_plot'] = df['ds'].dt.strftime('%Y-%m-%d')
        except Exception as e:
            print(f"❌ 股票 {stock_code} 日期格式化失败: {str(e)}")
            return None, None, None
        
        # 删除不需要的列
        if 'datetime_int' in df.columns:
            df.drop(columns=['datetime_int'], inplace=True)
        if 'datetime' in df.columns:
            df.drop(columns=['datetime'], inplace=True)
        
        # 重新排列列顺序，确保ds列在第一位，ds_plot在第二位
        columns = list(df.columns)
        if "ds" in columns:
            columns.remove("ds")
        if "ds_plot" in columns:
            columns.remove("ds_plot")
        columns = ["ds", "ds_plot"] + columns
        df = df[columns]
        
        print(f"✅ 数据预处理完成，数据形状: {df.shape}")
        print(f"📅 日期范围: {df['ds'].min()} 到 {df['ds'].max()}")
        
        # 数据分割
        original_length = df.shape[0]
        # 使用80%的数据作为训练集
        initial_train_size = int(original_length * 0.8)
        initial_test_size = original_length - initial_train_size
        
        # 确保训练集和测试集都是horizon_len的整数倍
        # 如果不是，则去掉最早的数据来调整
        train_size = (initial_train_size // horizon_len) * horizon_len
        test_size = (initial_test_size // horizon_len) * horizon_len
        
        # 计算需要去掉的最早数据量
        total_usable_size = train_size + test_size
        data_to_remove = original_length - total_usable_size
        if total_usable_size < horizon_len * 100:
            print(f"❌ 股票 {stock_code} 数据量不足 (仅 {total_usable_size} 条记录，需要至少 {horizon_len * 100} 条)")
            return None, None, None
        # 确保训练集和测试集都有足够的数据
        if train_size < horizon_len:
            print(f"❌ 股票 {stock_code} 训练集数据不足 (调整后仅有 {train_size} 条记录，需要至少 {horizon_len} 条)")
            return None, None, None
        
        if test_size < horizon_len:
            print(f"❌ 股票 {stock_code} 测试集数据不足 (调整后仅有 {test_size} 条记录，需要至少 {horizon_len} 条)")
            return None, None, None
        
        print(f"📏 数据调整: 原始长度={original_length}, 去掉最早的{data_to_remove}条数据")
        print(f"📏 调整后: 训练集={train_size}条 (是{horizon_len}的{train_size//horizon_len}倍), 测试集={test_size}条 (是{horizon_len}的{test_size//horizon_len}倍)")
        
        # 从去掉最早数据后的位置开始切分
        start_idx = data_to_remove
        df_train = df.iloc[start_idx:start_idx + train_size, :]
        df_test = df.iloc[start_idx + train_size:start_idx + train_size + test_size, :]
        
        print(f"📊 训练集: {len(df_train)} 条记录, 测试集: {len(df_test)} 条记录")
        
        return df, df_train, df_test
        
    except Exception as e:
        print(f"❌ 股票 {stock_code} 数据预处理失败: {str(e)}")
        return None, None, None