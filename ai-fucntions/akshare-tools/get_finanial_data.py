import akshare as ak
import pandas as pd
import logging
import time
import random
import requests
import json
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os, sys
current_dir = os.path.dirname(os.path.abspath(__file__))
finance_dir = os.path.dirname(current_dir)
pre_data_dir = os.path.join(finance_dir, 'preprocess_data')
sys.path.append(pre_data_dir)
from trading_date_processor import get_previous_trading_days

# SCF云函数相关导入
# from tencentserverless import scf 
# from tencentserverless.scf import Client
# from tencentserverless.exception import TencentServerlessSDKException
# from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
import numpy as np
# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def scf_invoke(event0, context0=None):
    """
    调用腾讯云SCF云函数获取数据
    """
    from tencentserverless.scf import Client
    from tencentserverless.exception import TencentServerlessSDKException
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    secret_id = os.getenv("TENCENT_SECRET_ID", "")
    secret_key = os.getenv("TENCENT_SECRET_KEY", "")
    region = os.getenv("TENCENT_REGION", "ap-shanghai")
    token = os.getenv("TENCENT_TOKEN", "")
    scf_client = Client(
        secret_id=secret_id,
        secret_key=secret_key,
        region=region,
        token=token
    )
    
    try:
        params = {
            "type": event0["type"],
            "code": event0["code"],
            "start_date": event0["start_date"],
            "end_date": event0["end_date"],
        }
        data = scf_client.invoke(event0["functionName"], data=params, namespace='default')
        return data
    except TencentServerlessSDKException as e:
        logger.error(f"腾讯云SCF SDK异常: {str(e)}")
        raise
    except TencentCloudSDKException as e:
        logger.error(f"腾讯云SDK异常: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"SCF调用异常: {str(e)}")
        raise


def get_stock_data_from_scf(symbol, start_date="19900101", end_date=None, max_retries=3):
    """
    使用SCF云函数获取股票数据
    
    Args:
        symbol (str): 股票代码，如'600000'
        start_date (str): 开始日期，格式'YYYYMMDD'
        end_date (str): 结束日期，格式'YYYYMMDD'，None表示当前日期
        max_retries (int): 最大重试次数
        
    Returns:
        pd.DataFrame: 股票数据DataFrame，包含日期、开盘价、最高价、最低价、收盘价、成交量等
    """
    logger.info(f"使用SCF云函数获取股票数据: {symbol}")
    
    # 处理股票代码格式，确保符合SCF函数要求
    if symbol.startswith('6'):
        scf_symbol = f"sh{symbol}"
    elif symbol.startswith('0') or symbol.startswith('3'):
        scf_symbol = f"sz{symbol}"
    else:
        scf_symbol = symbol
    
    # 处理结束日期
    if end_date is None:
        end_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 调用SCF云函数
            event_params = {
                "functionName": "get_financial_data",
                "type": "stock",
                "code": scf_symbol,
                "start_date": start_date,
                "end_date": end_date
            }
            
            logger.info(f"第 {retry_count + 1} 次尝试调用SCF云函数，参数: {event_params}")
            response_data = scf_invoke(event_params)
            
            # 解析响应数据
            if isinstance(response_data, str):
                data = json.loads(response_data)
            else:
                data = response_data
            
            # 检查响应状态
            if data.get("code", 0) > 0 and "data" in data:
                df = pd.DataFrame(data["data"])
                
                if not df.empty:
                    # 处理日期转换 - 从Unix时间戳(毫秒)转换为datetime
                    if 'date' in df.columns:
                        # 正确处理Unix时间戳转换
                        df['datetime'] = pd.to_datetime(df['date'], unit='ms', utc=True).dt.tz_convert('Asia/Shanghai').dt.tz_localize(None)
                        df = df.drop('date', axis=1)
                    elif 'datetime' in df.columns:
                        df['datetime'] = pd.to_datetime(df['datetime'])
                    
                    # 计算缺失的字段
                    if 'close' in df.columns and 'open' in df.columns:
                        # 计算涨跌幅 (percentage_change)
                        df['percentage_change'] = ((df['close'] - df['close'].shift(1)) / df['close'].shift(1) * 100).fillna(0.0)
                        
                        # 计算涨跌额 (amount_change)
                        df['amount_change'] = (df['close'] - df['close'].shift(1)).fillna(0.0)
                        
                        # 计算振幅 (amplitude)
                        if 'high' in df.columns and 'low' in df.columns:
                            df['amplitude'] = ((df['high'] - df['low']) / df['close'].shift(1) * 100).fillna(0.0)
                        else:
                            df['amplitude'] = 0.0
                    
                    # 计算成交额 (amount) - 如果没有提供，使用成交量*收盘价估算
                    if 'amount' not in df.columns:
                        if 'volume' in df.columns and 'close' in df.columns:
                            df['amount'] = df['volume'] * df['close']
                        else:
                            df['amount'] = 0.0
                    
                    # 计算换手率 (turnover_rate) - 如果没有提供，使用现有的turnover字段或设为0
                    if 'turnover_rate' not in df.columns:
                        if 'turnover' in df.columns:
                            df['turnover_rate'] = df['turnover'] * 100  # 转换为百分比
                        else:
                            df['turnover_rate'] = 0.0
                    
                    # 确保所有数值字段都是float类型
                    numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount', 
                                     'amplitude', 'percentage_change', 'amount_change', 'turnover_rate']
                    for col in numeric_columns:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                    
                    # 清理数据
                    df = df.fillna(0)
                    df = df.dropna()
                    
                    logger.info(f"成功获取股票 {symbol} 数据，共 {len(df)} 条记录")
                    logger.info(f"数据处理完成，最终DataFrame形状: {df.shape}")
                    logger.info(f"列名: {list(df.columns)}")
                    return df
                else:
                    logger.warning(f"SCF返回的数据为空: {symbol}")
                    
            else:
                error_msg = data.get("message", "未知错误")
                logger.error(f"SCF云函数返回错误: {error_msg}")
                
        except Exception as e:
            retry_count += 1
            logger.error(f"第 {retry_count} 次获取数据失败: {str(e)}")
            
            if retry_count < max_retries:
                wait_time = random.uniform(1, 3) * retry_count
                logger.info(f"等待 {wait_time:.2f} 秒后重试...")
                time.sleep(wait_time)
            else:
                logger.error(f"达到最大重试次数 {max_retries}，获取数据失败")
                return None
    
    return None


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
        end_date = get_previous_trading_days(days=56)
    end_date_pd = pd.Timestamp(end_date)
    if years > 0:
        start_date = (end_date_pd - pd.Timedelta(days=years*365)).strftime('%Y%m%d')
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
                adjust="hfq"  # 后复权
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


class PostgreSQLAPIClient:
    """PostgreSQL API客户端类，用于与postgres-handler服务交互"""
    
    def __init__(self, base_url="http://localhost:8080", timeout=30):
        """
        初始化API客户端
        
        Args:
            base_url (str): API服务的基础URL
            timeout (int): 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = setup_robust_session()
        logger.info(f"PostgreSQL API客户端初始化完成，服务地址: {self.base_url}")
    
    def health_check(self):
        """
        检查API服务健康状态
        
        Returns:
            bool: 服务是否正常
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            is_healthy = result.get('status') == 'ok'
            logger.info(f"API服务健康检查: {'正常' if is_healthy else '异常'}")
            return is_healthy
        except Exception as e:
            logger.error(f"API服务健康检查失败: {str(e)}")
            return False
    
    def insert_single_stock_data(self, stock_data_dict):
        """
        插入单条股票数据
        
        Args:
            stock_data_dict (dict): 股票数据字典
            
        Returns:
            dict: API响应结果
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/stock-data",
                json=stock_data_dict,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"成功插入单条股票数据: {stock_data_dict.get('symbol', 'Unknown')}")
            return result
        except Exception as e:
            logger.error(f"插入单条股票数据失败: {str(e)}")
            raise
    
    def batch_insert_stock_data(self, stock_data_list):
        """
        批量插入股票数据
        
        Args:
            stock_data_list (list): 股票数据列表
            
        Returns:
            dict: API响应结果
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/stock-data/batch",
                json=stock_data_list,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"成功批量插入股票数据: {result.get('count', len(stock_data_list))} 条记录")
            return result
        except Exception as e:
            logger.error(f"批量插入股票数据失败: {str(e)}")
            raise
    
    def get_stock_data(self, symbol, stock_type=1, limit=100, offset=0):
        """
        获取股票数据
        
        Args:
            symbol (str): 股票代码
            stock_type (int): 股票类型 (1=股票, 2=基金, 3=指数, 4+=其他)
            limit (int): 返回记录数限制
            offset (int): 偏移量
            
        Returns:
            list: 股票数据列表
        """
        try:
            params = {
                'type': stock_type,
                'limit': limit,
                'offset': offset
            }
            response = self.session.get(
                f"{self.base_url}/api/v1/stock-data/{symbol}",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"成功获取股票数据: {symbol}, 共 {len(result)} 条记录")
            return result
        except Exception as e:
            logger.error(f"获取股票数据失败: {str(e)}")
            raise


def convert_dataframe_to_api_format(df, symbol, stock_type=1):
    """
    将pandas DataFrame转换为API所需的格式
    
    Args:
        df (pd.DataFrame): 股票数据DataFrame
        symbol (str): 股票代码
        stock_type (int): 股票类型 (1=股票, 2=基金, 3=指数, 4+=其他)
        
    Returns:
        list: 转换后的数据列表
    """
    if df is None or df.empty:
        logger.warning("DataFrame为空，无法转换")
        return []
    
    try:
        # 确保必要的列存在
        required_columns = ['datetime', 'open', 'close', 'high', 'low', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"DataFrame缺少必要的列: {missing_columns}")
            return []
        
        # 转换数据
        api_data_list = []
        for _, row in df.iterrows():
            # 处理datetime字段 - 使用RFC3339格式
            if isinstance(row['datetime'], pd.Timestamp):
                datetime_str = row['datetime'].strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                # 尝试解析字符串日期并转换为RFC3339格式
                try:
                    dt = pd.to_datetime(str(row['datetime']))
                    datetime_str = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                except:
                    datetime_str = str(row['datetime'])
            
            # 构建API数据格式
            api_data = {
                "datetime": datetime_str,
                "open": float(row['open']) if pd.notna(row['open']) else 0.0,
                "close": float(row['close']) if pd.notna(row['close']) else 0.0,
                "high": float(row['high']) if pd.notna(row['high']) else 0.0,
                "low": float(row['low']) if pd.notna(row['low']) else 0.0,
                "volume": int(row['volume']) if pd.notna(row['volume']) else 0,
                "amount": float(row.get('amount', 0.0)) if pd.notna(row.get('amount', 0.0)) else 0.0,
                "amplitude": float(row.get('amplitude', 0.0)) if pd.notna(row.get('amplitude', 0.0)) else 0.0,
                "percentage_change": float(row.get('percentage_change', 0.0)) if pd.notna(row.get('percentage_change', 0.0)) else 0.0,
                "amount_change": float(row.get('amount_change', 0.0)) if pd.notna(row.get('amount_change', 0.0)) else 0.0,
                "turnover_rate": float(row.get('turnover_rate', 0.0)) if pd.notna(row.get('turnover_rate', 0.0)) else 0.0,
                "type": stock_type,
                "symbol": symbol,
                "date_str": datetime_str[:10],
            }
            api_data_list.append(api_data)
        
        logger.info(f"成功转换 {len(api_data_list)} 条数据为API格式")
        return api_data_list
        
    except Exception as e:
        logger.error(f"数据格式转换失败: {str(e)}")
        return []


def fetch_and_store_stock_data(symbol, api_client, start_date="19900101", end_date=None, 
                              stock_type=1, batch_size=1000, max_retries=3):
    """
    获取股票数据并存储到PostgreSQL数据库 (使用SCF云函数数据源)
    
    Args:
        symbol (str): 股票代码，如'600000'
        api_client (PostgreSQLAPIClient): API客户端实例
        start_date (str): 开始日期，格式'YYYYMMDD'
        end_date (str): 结束日期，格式'YYYYMMDD'
        stock_type (int): 股票类型 (1=股票, 2=基金, 3=指数, 4+=其他)
        batch_size (int): 批量插入的大小
        max_retries (int): 最大重试次数
        
    Returns:
        dict: 执行结果统计
    """
    logger.info(f"开始获取并存储股票数据: {symbol} (使用SCF云函数)")
    
    # 检查API服务状态
    if not api_client.health_check():
        logger.error("API服务不可用，无法存储数据")
        return {"success": False, "error": "API服务不可用"}
    
    try:
        # 使用SCF云函数获取股票数据
        logger.info(f"正在从SCF云函数获取股票 {symbol} 的数据...")
        df = get_stock_data_from_scf(symbol, start_date=start_date, end_date=end_date, max_retries=max_retries)
        
        if df is None or df.empty:
            logger.warning(f"未获取到股票 {symbol} 的数据")
            return {"success": False, "error": "未获取到数据"}
        
        # 转换数据格式
        logger.info(f"正在转换数据格式...")
        api_data_list = convert_dataframe_to_api_format(df, symbol, stock_type)
        
        if not api_data_list:
            logger.error("数据格式转换失败")
            return {"success": False, "error": "数据格式转换失败"}
        
        # 批量存储数据
        total_records = len(api_data_list)
        stored_records = 0
        failed_batches = 0
        
        logger.info(f"开始批量存储数据，总计 {total_records} 条记录，批次大小 {batch_size}")
        
        for i in range(0, total_records, batch_size):
            batch_data = api_data_list[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_records + batch_size - 1) // batch_size
            
            try:
                logger.info(f"正在处理第 {batch_num}/{total_batches} 批次，包含 {len(batch_data)} 条记录")
                result = api_client.batch_insert_stock_data(batch_data)
                stored_records += len(batch_data)
                logger.info(f"第 {batch_num} 批次存储成功")
                
            except Exception as e:
                logger.error(f"第 {batch_num} 批次存储失败: {str(e)}")
                failed_batches += 1
                
                # 如果批量插入失败，尝试单条插入
                logger.info(f"尝试单条插入第 {batch_num} 批次的数据...")
                for record in batch_data:
                    try:
                        api_client.insert_single_stock_data(record)
                        stored_records += 1
                    except Exception as single_error:
                        logger.error(f"单条插入失败: {str(single_error)}")
        
        # 返回执行结果
        success_rate = (stored_records / total_records) * 100 if total_records > 0 else 0
        result = {
            "success": True,
            "symbol": symbol,
            "total_records": total_records,
            "stored_records": stored_records,
            "failed_batches": failed_batches,
            "success_rate": f"{success_rate:.2f}%",
            "start_date": start_date,
            "end_date": end_date,
            "stock_type": stock_type
        }
        
        logger.info(f"股票 {symbol} 数据存储完成: {stored_records}/{total_records} 条记录成功存储 ({success_rate:.2f}%)")
        return result
        
    except Exception as e:
        logger.error(f"获取并存储股票数据失败: {str(e)}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    symbol = "000002"
    # 原有的测试代码
    # print("=== 测试akshare数据获取 ===")
    # df = ak_stock_data("000001")
    # print(df.head(10))
    
    # 测试技术指标计算
    # if df is not None:
    #     df_with_indicators, indicators = talib_tools(df)
    #     print("\n添加技术指标后的数据:")
    #     # 检查日期列名
    #     date_col = 'ds' if 'ds' in df_with_indicators.columns else 'datetime'
    #     display_cols = [date_col, 'close', 'MA5', 'MA20', 'EMA5', 'EMA20', 'DIF']
    #     # 只显示存在的列
    #     available_cols = [col for col in display_cols if col in df_with_indicators.columns]
    #     print(df_with_indicators[available_cols].head(10))
    
    # print("\n" + "="*60)
    # print("=== 测试PostgreSQL API存储功能 ===")
    # res = get_index_data(symbol=symbol)
    # print(res)
    # 创建API客户端（请根据实际情况修改URL）
    api_client = PostgreSQLAPIClient()
    
    # 测试API服务健康状态
    print("\n1. 检查API服务状态...")
    if api_client.health_check():
        print("✅ API服务正常")
        
        # 测试获取并存储股票数据
        print("\n2. 测试获取并存储股票数据...")
        test_symbols = ["600398", "000001"]  # 测试股票代码
        
        for symbol in test_symbols:
            print(f"\n正在处理股票: {symbol}")
            result = fetch_and_store_stock_data(
                symbol=symbol,
                api_client=api_client,
                start_date="19900101",  # 从2024年开始
                end_date=None,  # 到当前日期
                stock_type=1,  # 股票类型
                batch_size=500,  # 批次大小
                max_retries=3
            )
            
            if result["success"]:
                print(f"✅ {symbol} 数据存储成功:")
                print(f"   - 总记录数: {result['total_records']}")
                print(f"   - 成功存储: {result['stored_records']}")
                print(f"   - 成功率: {result['success_rate']}")
                print(f"   - 失败批次: {result['failed_batches']}")
            else:
                print(f"❌ {symbol} 数据存储失败: {result.get('error', '未知错误')}")
        
        # 测试从数据库获取数据
        print("\n3. 测试从数据库获取数据...")
        try:
            stored_data = api_client.get_stock_data("600398", stock_type=1, limit=5)
            if stored_data:
                print(f"✅ 成功从数据库获取 {len(stored_data)} 条记录")
                print("最新5条记录:")
                for i, record in enumerate(stored_data[:5], 1):
                    print(f"   {i}. {record.get('datetime', 'N/A')} - 收盘价: {record.get('close', 'N/A')}")
            else:
                print("⚠️  数据库中暂无数据")
        except Exception as e:
            print(f"❌ 获取数据失败: {str(e)}")
            
    else:
        print("❌ API服务不可用，请确保postgres-handler服务正在运行")
        print("启动命令示例:")
        print("  cd /root/workers/finance/postgres-handler")
        print("  ./deploy.sh start")
        print("  或者")
        print("  make docker-up")
    
    print("\n" + "="*60)
    print("=== 使用说明 ===")
    print("1. 确保PostgreSQL服务和postgres-handler API服务正在运行")
    print("2. 根据实际情况修改API服务地址（默认: http://localhost:8080）")
    print("3. 使用 fetch_and_store_stock_data() 函数获取并存储股票数据")
    print("4. 支持的股票类型: 1=股票, 2=基金, 3=指数, 4+=其他")
    print("5. 支持批量插入和单条插入的容错机制")
    print("\n示例代码:")
    print("""
        # 创建API客户端
        api_client = PostgreSQLAPIClient(base_url="http://localhost:8080")

        # 获取并存储股票数据
        result = fetch_and_store_stock_data(
            symbol="600398",           # 股票代码
            api_client=api_client,     # API客户端
            start_date="20240101",     # 开始日期
            end_date=None,             # 结束日期（None表示到当前）
            stock_type=1,              # 股票类型
            batch_size=1000,           # 批次大小
            max_retries=3              # 最大重试次数
        )

        print(result)
            """)
