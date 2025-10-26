import akshare as ak
import pandas as pd
import logging
import time
import random
import requests
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_network_connectivity(test_urls=None, timeout=10):
    """
    检查网络连接状态
    
    Args:
        test_urls: 测试URL列表，默认使用常见的可靠网站
        timeout: 超时时间（秒）
    
    Returns:
        bool: 网络是否可用
    """
    if test_urls is None:
        test_urls = [
            "https://www.baidu.com",
            "https://www.google.com", 
            "https://httpbin.org/get"
        ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                logger.info(f"网络连接正常 (测试URL: {url})")
                return True
        except Exception as e:
            logger.debug(f"测试URL {url} 连接失败: {str(e)}")
            continue
    
    logger.warning("网络连接检测失败，所有测试URL都无法访问")
    return False

def setup_robust_session():
    """设置一个具有重试机制的requests会话"""
    session = requests.Session()
    
    # 配置重试策略
    retry_strategy = Retry(
        total=5,  # 总重试次数
        status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
        allowed_methods=["HEAD", "GET", "OPTIONS"],  # 允许重试的HTTP方法
        backoff_factor=1  # 退避因子
    )
    
    # 配置HTTP适配器
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 设置超时
    session.timeout = 30
    
    return session

def ak_stock_data(symbol, start_date="19900101", end_date=None, years=0, time_step=None, max_retries=5):
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
    
    # 检查网络连接
    if not check_network_connectivity():
        logger.error("网络连接不可用，无法获取股票数据")
        return None
    
    # 设置健壮的会话
    session = setup_robust_session()
    
    for attempt in range(max_retries):
        try:
            # 在重试之间添加指数退避延迟
            if attempt > 0:
                delay = min(2 ** attempt + random.uniform(0, 1), 30)  # 最大延迟30秒
                logger.info(f"等待 {delay:.2f} 秒后进行第 {attempt + 1} 次尝试...")
                time.sleep(delay)
            
            logger.info(f"尝试获取股票 {symbol} 数据 (第 {attempt + 1}/{max_retries} 次)")
            
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
            logger.info(f"成功获取股票 {symbol} 数据，共 {len(stock_data)} 条记录")
            
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
            
        # except requests.exceptions.ConnectionError as e:
        #     logger.error(f"网络连接错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
        #     if "RemoteDisconnected" in str(e):
        #         logger.warning("远程服务器断开连接，可能是服务器负载过高")
        # except requests.exceptions.Timeout as e:
        #     logger.error(f"请求超时 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
        # except requests.exceptions.HTTPError as e:
        #     logger.error(f"HTTP错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
        # except requests.exceptions.RequestException as e:
        #     logger.error(f"请求异常 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
        # except ValueError as e:
        #     logger.error(f"数据格式错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
        #     # 数据格式错误通常不需要重试
        #     if "Invalid symbol" in str(e) or "股票代码" in str(e):
        #         logger.error(f"股票代码 {symbol} 无效，停止重试")
        #         return None
        except Exception as e:
            error_msg = str(e)
            logger.error(f"获取股票 {symbol} 数据失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
            
            # 检查是否是网络相关错误
            network_errors = [
                "Connection aborted", "RemoteDisconnected", "Connection broken",
                "Connection reset", "timeout", "Network is unreachable",
                "Name or service not known", "Temporary failure in name resolution"
            ]
            
            if any(err in error_msg for err in network_errors):
                logger.warning("检测到网络相关错误，将进行重试")
            else:
                logger.warning(f"未知错误类型: {type(e).__name__}")
        
        # 如果是最后一次尝试，记录最终失败
        if attempt == max_retries - 1:
            logger.error(f"股票 {symbol} 数据获取最终失败，已尝试 {max_retries} 次")
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
