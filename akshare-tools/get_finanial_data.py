import akshare as ak
import pandas as pd
import logging
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ak_stock_data(symbol, start_date="19900101", end_date=None, years=0, time_step=None, max_retries=3):
    """
    从akshare获取单个股票的历史数据
    
    参数:
        symbol (str): 股票代码，如'600000'
        start_date (str): 开始日期，格式'YYYYMMDD'，默认'19900101'
        end_date (str): 结束日期，格式'YYYYMMDD'，默认为当前日期
        time_step (int): 时间步长，用于日期时间平移，单位为天
        max_retries (int): 最大重试次数
        
    返回:
        pandas.DataFrame: 包含OHLCV数据的DataFrame，索引为日期
        
    异常处理:
        - 网络连接异常
        - 数据获取失败
        - 数据格式异常
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    if years > 0:
        start_date = (datetime.now() - pd.Timedelta(days=years*365)).strftime('%Y%m%d')
    logger.info(f"正在获取股票 {symbol} 的数据，时间范围: {start_date} 到 {end_date}")
    
    for attempt in range(max_retries):
        try:
            # 使用akshare的stock_zh_a_hist接口获取A股历史数据
            # period="daily": 日频数据
            # start_date/end_date: 时间范围
            # adjust="qfq": 前复权处理，消除分红送股对价格的影响
            stock_data = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if stock_data is None or stock_data.empty:
                logger.warning(f"股票 {symbol} 返回空数据")
                return None
            
            # 重命名列名以匹配标准格式
            # akshare返回的列名：日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
            column_mapping = {
                '日期': 'datetime',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'percentage_change',
                '涨跌额': 'amount_change',
                '换手率': 'turnover_rate'
            }
            
            # 选择需要的列并重命名
            required_columns = [
                '日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额',
                '振幅', '涨跌幅', '涨跌额', '换手率'
            ]
            available_columns = [col for col in required_columns if col in stock_data.columns]
            
            if len(available_columns) < 6:  # 至少需要OHLCV数据
                logger.error(f"股票 {symbol} 数据列不完整，可用列: {available_columns}")
                return None
            
            stock_data = stock_data[available_columns].copy()
            stock_data.rename(columns=column_mapping, inplace=True)
            
            # 转换日期格式但保留为普通列
            stock_data['datetime'] = pd.to_datetime(stock_data['datetime'])
            
            # 添加时间戳字段
            stock_data['datetime_int'] = stock_data['datetime'].astype('int64') // 10**9
            
            # 数据类型转换，确保数值列为float类型
            numeric_columns = [
                'open', 'close', 'high', 'low', 'volume', 'amount',
                'amplitude', 'percentage_change', 'amount_change', 'turnover_rate'
            ]
            
            for col in numeric_columns:
                if col in stock_data.columns:
                    stock_data[col] = pd.to_numeric(stock_data[col], errors='coerce')
            
            # 按日期排序
            stock_data.sort_values('datetime', inplace=True)
            
            # 如果指定了time_step，进行日期时间平移
            if time_step is not None:
                from datetime import timedelta
                # 将datetime列日期向前或向后平移time_step天
                stock_data['datetime'] = stock_data['datetime'] + timedelta(days=time_step)
                logger.info(f"应用时间步长 {time_step} 天的日期平移")
            
            logger.info(f"成功获取股票 {symbol} 数据，共 {len(stock_data)} 条记录")
            return stock_data
            
        except Exception as e:
            logger.error(f"获取股票 {symbol} 数据失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"股票 {symbol} 数据获取最终失败")
                return None
    
    return None

def get_stock_list():
    """
    获取A股股票列表
    
    返回:
        pandas.DataFrame: 包含股票代码和名称的DataFrame
    """
    try:
        stock_list = ak.stock_zh_a_spot_em()
        return stock_list[['代码', '名称']]
    except Exception as e:
        logger.error(f"获取股票列表失败: {str(e)}")
        return None

def get_index_data(symbol, start_date="19900101", end_date=None):
    """
    获取指数数据
    
    参数:
        symbol (str): 指数代码，如'000001'(上证指数)
        start_date (str): 开始日期，格式'YYYYMMDD'
        end_date (str): 结束日期，格式'YYYYMMDD'
        
    返回:
        pandas.DataFrame: 包含指数OHLCV数据的DataFrame
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    try:
        index_data = ak.index_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date
        )
        
        if index_data is None or index_data.empty:
            logger.warning(f"指数 {symbol} 返回空数据")
            return None
        
        # 重命名列名
        column_mapping = {
            '日期': 'datetime',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount'
        }
        
        index_data.rename(columns=column_mapping, inplace=True)
        index_data['datetime'] = pd.to_datetime(index_data['datetime'])
        index_data.set_index('datetime', inplace=True)
        
        # 数据类型转换
        numeric_columns = ['open', 'close', 'high', 'low', 'volume', 'amount']
        for col in numeric_columns:
            if col in index_data.columns:
                index_data[col] = pd.to_numeric(index_data[col], errors='coerce')
        
        index_data.sort_index(inplace=True)
        
        logger.info(f"成功获取指数 {symbol} 数据，共 {len(index_data)} 条记录")
        return index_data
        
    except Exception as e:
        logger.error(f"获取指数 {symbol} 数据失败: {str(e)}")
        return None

def talib_tools(df):
    """
    计算技术指标
    
    参数:
        df (pandas.DataFrame): 包含股票数据的DataFrame
        stock_code_list (list): 股票代码列表
        
    返回:
        pandas.DataFrame: 添加了技术指标的DataFrame
        list: 技术指标列名列表
    """
    try:
        # 确保数据按日期排序，检查日期列名
        date_col = 'ds' if 'ds' in df.columns else 'datetime'
        df = df.sort_values(date_col).copy()
        
        # 计算移动平均线 (MA)
        df['MA5'] = df['close'].rolling(window=5, min_periods=1).mean()
        df['MA15'] = df['close'].rolling(window=15, min_periods=1).mean()
        df['MA20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['MA25'] = df['close'].rolling(window=25, min_periods=1).mean()
        df['MA30'] = df['close'].rolling(window=30, min_periods=1).mean()
        
        # 计算指数移动平均线 (EMA)
        df['EMA5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['EMA15'] = df['close'].ewm(span=15, adjust=False).mean()
        df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['EMA25'] = df['close'].ewm(span=25, adjust=False).mean()
        df['EMA30'] = df['close'].ewm(span=30, adjust=False).mean()
        
        # 计算MACD指标中的DIF
        # DIF = EMA12 - EMA26
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = ema12 - ema26
        
        # 可选：计算DEA和MACD柱状图
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD'] = 2 * (df['DIF'] - df['DEA'])
        
        # 技术指标列名列表
        technical_indicators = [
            'MA5', 'MA15', 'MA20', 'MA25', 'MA30',
            'EMA5', 'EMA15', 'EMA20', 'EMA25', 'EMA30',
            'DIF', 'DEA', 'MACD'
        ]
        
        # 填充NaN值（使用前向填充）
        for indicator in technical_indicators:
            if indicator in df.columns:
                df[indicator] = df[indicator].ffill()
        
        logger.info(f"成功计算技术指标: {technical_indicators}")
        return df, technical_indicators
        
    except Exception as e:
        logger.error(f"计算技术指标失败: {str(e)}")
        return df, []

if __name__ == "__main__":
    df = ak_stock_data("600398")
    print(df.head(10))
    
    # 测试技术指标计算
    if df is not None:
        df_with_indicators, indicators = talib_tools(df, ["600398"])
        print("\n添加技术指标后的数据:")
        # 检查日期列名
        date_col = 'ds' if 'ds' in df_with_indicators.columns else 'datetime'
        display_cols = [date_col, 'close', 'MA5', 'MA20', 'EMA5', 'EMA20', 'DIF']
        # 只显示存在的列
        available_cols = [col for col in display_cols if col in df_with_indicators.columns]
        print(df_with_indicators[available_cols].head(10))
