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

if __name__ == "__main__":
    df = ak_stock_data("600398")
    print(df.head(10))
