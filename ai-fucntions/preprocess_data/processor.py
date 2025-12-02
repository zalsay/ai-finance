import os
import sys
import pandas as pd
import warnings
import asyncio

from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)



# 忽略警告
warnings.filterwarnings("ignore")

# 添加akshare工具路径
current_dir = os.path.dirname(os.path.abspath(__file__))
finance_dir = os.path.dirname(current_dir)  # 上级目录
akshare_dir = os.path.join(finance_dir, 'akshare-tools')
sys.path.append(akshare_dir)

from postgres import PostgresHandler
pg_client = PostgresHandler()

def to_symbol(stock_code: str, stock_type: int = 1) -> str:
    s = str(stock_code).lower()
    if s.startswith("sh") or s.startswith("sz"):
        return s
    if stock_type in (1, 2):
        if s.startswith("6") or s.startswith("5"):
            return f"sh{stock_code}"
        if s[0] in ("0", "1", "2", "3"):
            return f"sz{stock_code}"
    return stock_code

async def df_preprocess(stock_code, stock_type, start_date=None, end_date=None, time_step=0, years=12, horizon_len=7):
    """
    预处理股票数据
    
    Args:
        stock_code: 股票代码
        stock_type: 股票类型
        end_date: 结束日期
        time_step: 时间步长
        years: 获取多少年的数据
        horizon_len: 预测长度
        
    Returns:
        tuple: (df, df_train, df_test, df_val) 或 (None, None, None, None) 如果失败
    """
    try:
        # 获取股票数据
        # df = ak_stock_data(stock_code, start_date="19900101", end_date=end_date, years=years, time_step=time_step)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = yesterday
            if years > 0:
                start_date = (datetime.now() - timedelta(days=years*365)).strftime("%Y%m%d")
            else:
                start_date = "20100101"
        
        symbol = to_symbol(stock_code, stock_type)
        logger.info(f"获取股票{symbol} 数据，时间范围：{start_date} 到 {end_date} ，股票类型：{stock_type}")
        df = await pg_client.ensure_date_range_df(symbol=symbol, start_date=start_date, end_date=end_date, stock_type=stock_type)
        print(df.head(1))
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
        
        df.rename(columns={'symbol': 'stock_code'}, inplace=True)
        # 删除多余列
        del_columns = ["type", "symbol", "created_at", "updated_at", "id", "percentage_change", "amount_change", "turnover_rate"]
        df.drop(columns=del_columns, inplace=True)
        
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
        # 使用7:2:1的比例划分训练集、测试集、验证集
        initial_train_size = int(original_length * 0.7)  # 70% 训练集
        initial_test_size = int(original_length * 0.2)   # 20% 测试集
        initial_val_size = original_length - initial_train_size - initial_test_size  # 10% 验证集
        
        # 确保训练集、测试集、验证集都是horizon_len的整数倍
        # 如果不是，则去掉最早的数据来调整
        train_size = (initial_train_size // horizon_len) * horizon_len
        test_size = (initial_test_size // horizon_len) * horizon_len
        val_size = (initial_val_size // horizon_len) * horizon_len
        # train_size = initial_train_size
        # test_size = initial_test_size
        # 计算需要去掉的最早数据量
        total_usable_size = train_size + test_size + val_size
        data_to_remove = original_length - total_usable_size
        if total_usable_size < horizon_len * 100:
            print(f"❌ 股票 {stock_code} 数据量不足 (仅 {total_usable_size} 条记录，需要至少 {horizon_len * 100} 条)")
            return None, None, None, None
        # 确保训练集、测试集和验证集都有足够的数据
        if train_size < horizon_len:
            print(f"❌ 股票 {stock_code} 训练集数据不足 (调整后仅有 {train_size} 条记录，需要至少 {horizon_len} 条)")
            return None, None, None, None
        
        if test_size < horizon_len:
            print(f"❌ 股票 {stock_code} 测试集数据不足 (调整后仅有 {test_size} 条记录，需要至少 {horizon_len} 条)")
            return None, None, None, None
        
        if val_size < horizon_len:
            print(f"❌ 股票 {stock_code} 验证集数据不足 (调整后仅有 {val_size} 条记录，需要至少 {horizon_len} 条)")
            return None, None, None, None
        
        print(f"📏 数据调整: 原始长度={original_length}, 去掉最早的{data_to_remove}条数据")
        print(f"📏 调整后: 训练集={train_size}条 (是{horizon_len}的{train_size//horizon_len}倍), 测试集={test_size}条 (是{horizon_len}的{test_size//horizon_len}倍), 验证集={val_size}条 (是{horizon_len}的{val_size//horizon_len}倍)")
        
        # 从去掉最早数据后的位置开始切分
        start_idx = data_to_remove
        df_train = df.iloc[start_idx:start_idx + train_size, :]
        df_test = df.iloc[start_idx + train_size:start_idx + train_size + test_size, :]
        df_val = df.iloc[start_idx + train_size + test_size:start_idx + train_size + test_size + val_size, :]
        
        print(f"📊 训练集: {len(df_train)} 条记录, 测试集: {len(df_test)} 条记录, 验证集: {len(df_val)} 条记录")
        # print(f"训练集列名: {df_train.columns.tolist()}")
        # print(f"测试集列名: {df_test.columns.tolist()}")
        # print(f"验证集列名: {df_val.columns.tolist()}")

        return df, df_train, df_test, df_val
        
    except Exception as e:
        print(f"❌ 股票 {stock_code} 数据预处理失败: {str(e)}")
        return None, None, None, None