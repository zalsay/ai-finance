import os
import pickle
import pandas as pd
import  as ak
from datetime import datetime, timedelta
from tqdm import trange
import logging
import warnings
warnings.filterwarnings('ignore')

# 简化的日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleAkshareDataPreprocessor:
    """
    简化版akshare数据预处理器
    
    功能:
    1. 快速获取少量股票的历史数据
    2. 基础数据清洗和特征计算
    3. 数据保存为pickle格式
    
    适用场景:
    - 快速测试和原型开发
    - 小规模数据处理
    - 学习和演示用途
    """
    
    def __init__(self):
        """初始化简化版预处理器"""
        logger.info("初始化SimpleAkshareDataPreprocessor...")
        
        # 基础路径配置
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 简化配置 - 只使用3个股票进行快速测试
        self.instrument = ['600000', '600009', '600010']  # 浦发银行、上海机场、包钢股份
        
        # 缩短时间范围以加快处理速度
        self.dataset_begin_time = '2020-01-01'
        self.dataset_end_time = '2020-03-31'  # 只使用3个月数据
        
        # 简化的窗口参数
        self.lookback_window = 30  # 30天历史数据
        self.predict_window = 5    # 5天预测窗口
        
        # 数据字段定义
        self.data_fields = ['open', 'close', 'high', 'low', 'volume']
        self.feature_list = ['open', 'close', 'high', 'low', 'vol', 'amt']
        
        logger.info(f"配置完成 - 股票: {self.instrument}, 时间: {self.dataset_begin_time} 到 {self.dataset_end_time}")
    
    def get_single_stock_data(self, symbol, start_date, end_date):
        """
        获取单个股票的历史数据（简化版）
        
        参数:
            symbol (str): 股票代码，如'600000'
            start_date (str): 开始日期 'YYYY-MM-DD'
            end_date (str): 结束日期 'YYYY-MM-DD'
            
        返回:
            pandas.DataFrame: 股票数据或None
        """
        logger.info(f"获取股票 {symbol} 数据...")
        
        try:
            # 使用akshare获取A股历史数据
            # adjust="qfq": 前复权，消除除权除息影响
            stock_data = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",  # 日线数据
                start_date=start_date.replace('-', ''),  # 转换为YYYYMMDD格式
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # 前复权处理
            )
            
            if stock_data is None or stock_data.empty:
                logger.warning(f"股票 {symbol} 无数据")
                return None
            
            # akshare返回的列名映射
            # 原始列名: ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', ...]
            column_mapping = {
                '日期': 'datetime',
                '开盘': 'open',     # 开盘价
                '收盘': 'close',    # 收盘价
                '最高': 'high',     # 最高价
                '最低': 'low',      # 最低价
                '成交量': 'volume', # 成交量（手）
                '成交额': 'amount'  # 成交额（元）
            }
            
            # 选择需要的列
            required_cols = ['日期', '开盘', '收盘', '最高', '最低', '成交量']
            if '成交额' in stock_data.columns:
                required_cols.append('成交额')
            
            # 检查必要列是否存在
            missing_cols = [col for col in required_cols if col not in stock_data.columns]
            if missing_cols:
                logger.error(f"股票 {symbol} 缺少必要列: {missing_cols}")
                return None
            
            # 提取和重命名列
            stock_data = stock_data[required_cols].copy()
            stock_data.rename(columns=column_mapping, inplace=True)
            
            # 日期处理
            stock_data['datetime'] = pd.to_datetime(stock_data['datetime'])
            stock_data.set_index('datetime', inplace=True)
            
            # 数据类型转换
            numeric_cols = ['open', 'close', 'high', 'low', 'volume']
            if 'amount' in stock_data.columns:
                numeric_cols.append('amount')
            
            for col in numeric_cols:
                stock_data[col] = pd.to_numeric(stock_data[col], errors='coerce')
            
            # 排序
            stock_data.sort_index(inplace=True)
            
            logger.info(f"股票 {symbol} 获取成功，{len(stock_data)} 条记录")
            return stock_data
            
        except Exception as e:
            logger.error(f"获取股票 {symbol} 失败: {str(e)}")
            return None
    
    def process_stock_features(self, df):
        """
        处理股票特征（简化版）
        
        参数:
            df (pandas.DataFrame): 原始股票数据
            
        返回:
            pandas.DataFrame: 处理后的特征数据
        """
        try:
            result_df = df.copy()
            
            # 计算vol特征：成交量
            result_df['vol'] = result_df['volume']
            
            # 计算amt特征：成交额
            if 'amount' in result_df.columns and not result_df['amount'].isna().all():
                # 直接使用akshare提供的成交额
                result_df['amt'] = result_df['amount']
            else:
                # 使用OHLC均价估算成交额
                # 计算方式：(开盘价+最高价+最低价+收盘价)/4 * 成交量
                avg_price = (result_df['open'] + result_df['high'] + 
                           result_df['low'] + result_df['close']) / 4
                result_df['amt'] = avg_price * result_df['vol']
            
            # 选择最终特征
            result_df = result_df[self.feature_list]
            
            return result_df
            
        except Exception as e:
            logger.error(f"特征处理失败: {str(e)}")
            raise
    
    def load_and_process_data(self):
        """
        加载和处理所有股票数据
        
        返回:
            list: 处理后的股票数据列表
        """
        logger.info("开始加载和处理数据...")
        
        # 计算实际时间范围（包含缓冲）
        start_date = pd.to_datetime(self.dataset_begin_time)
        end_date = pd.to_datetime(self.dataset_end_time)
        
        # 添加缓冲时间
        buffer_start = start_date - timedelta(days=self.lookback_window + 10)
        buffer_end = end_date + timedelta(days=self.predict_window + 10)
        
        actual_start = buffer_start.strftime('%Y-%m-%d')
        actual_end = buffer_end.strftime('%Y-%m-%d')
        
        logger.info(f"实际获取时间范围: {actual_start} 到 {actual_end}")
        
        processed_data = []
        
        # 处理每个股票
        for i in trange(len(self.instrument), desc="处理股票"):
            symbol = self.instrument[i]
            
            try:
                # 获取股票数据
                stock_df = self.get_single_stock_data(symbol, actual_start, actual_end)
                
                if stock_df is None or stock_df.empty:
                    logger.warning(f"跳过股票 {symbol}：无数据")
                    continue
                
                # 数据清洗
                original_len = len(stock_df)
                stock_df = stock_df.dropna()
                cleaned_len = len(stock_df)
                
                if original_len != cleaned_len:
                    logger.info(f"股票 {symbol} 清洗了 {original_len - cleaned_len} 条缺失数据")
                
                # 检查数据长度
                min_length = self.lookback_window + self.predict_window + 1
                if len(stock_df) < min_length:
                    logger.warning(f"股票 {symbol} 数据不足: {len(stock_df)} < {min_length}")
                    continue
                
                # 特征处理
                stock_df = self.process_stock_features(stock_df)
                
                # 最终检查
                stock_df = stock_df.dropna()
                if len(stock_df) < min_length:
                    logger.warning(f"股票 {symbol} 特征处理后数据不足")
                    continue
                
                # 添加到结果列表
                processed_data.append({
                    'symbol': f'SH{symbol}',  # 添加SH前缀保持一致性
                    'data': stock_df
                })
                
                logger.info(f"股票 {symbol} 处理完成，最终数据长度: {len(stock_df)}")
                
            except Exception as e:
                logger.error(f"处理股票 {symbol} 时出错: {str(e)}")
                continue
        
        logger.info(f"数据处理完成，成功处理 {len(processed_data)} 个股票")
        
        if not processed_data:
            raise ValueError("没有成功处理任何股票数据")
        
        return processed_data
    
    def save_processed_data(self, processed_data):
        """
        保存处理后的数据
        
        参数:
            processed_data (list): 处理后的股票数据列表
        """
        logger.info("保存处理后的数据...")
        
        try:
            # 保存文件路径
            output_file = os.path.join(self.current_dir, 'processed_data_akshare_simple.pkl')
            
            # 使用pickle保存数据
            with open(output_file, 'wb') as f:
                pickle.dump(processed_data, f)
            
            logger.info(f"数据已保存到: {output_file}")
            
            # 输出数据统计
            total_records = sum(len(item['data']) for item in processed_data)
            avg_records = total_records / len(processed_data)
            
            logger.info(f"保存统计: {len(processed_data)} 个股票, 总计 {total_records} 条记录")
            logger.info(f"平均每股: {avg_records:.1f} 条记录")
            
            # 显示每个股票的详细信息
            for item in processed_data:
                symbol = item['symbol']
                data_len = len(item['data'])
                start_date = item['data'].index.min().strftime('%Y-%m-%d')
                end_date = item['data'].index.max().strftime('%Y-%m-%d')
                logger.info(f"  {symbol}: {data_len} 条记录 ({start_date} 到 {end_date})")
            
        except Exception as e:
            logger.error(f"保存数据失败: {str(e)}")
            raise
    
    def run_simple_pipeline(self):
        """
        运行简化的数据处理流水线
        
        返回:
            list: 处理后的数据
        """
        logger.info("开始运行简化数据处理流水线...")
        
        try:
            # 加载和处理数据
            processed_data = self.load_and_process_data()
            
            # 保存数据
            self.save_processed_data(processed_data)
            
            logger.info("简化流水线执行完成！")
            return processed_data
            
        except Exception as e:
            logger.error(f"简化流水线执行失败: {str(e)}")
            raise


def test_akshare_connection():
    """
    测试akshare连接和基本功能
    """
    logger.info("测试akshare连接...")
    
    try:
        # 测试获取单个股票数据
        test_data = ak.stock_zh_a_hist(
            symbol="600000",
            period="daily",
            start_date="20200101",
            end_date="20200110",
            adjust="qfq"
        )
        
        if test_data is not None and not test_data.empty:
            logger.info(f"akshare连接正常，测试数据形状: {test_data.shape}")
            logger.info(f"测试数据列名: {list(test_data.columns)}")
            return True
        else:
            logger.error("akshare连接异常：返回空数据")
            return False
            
    except Exception as e:
        logger.error(f"akshare连接测试失败: {str(e)}")
        return False


if __name__ == '__main__':
    """
    简化版主程序
    
    使用方法:
        python akshare_data_preprocess_simple.py
    
    输出:
        - processed_data_akshare_simple.pkl: 处理后的数据文件
    """
    try:
        logger.info("启动简化版akshare数据预处理...")
        
        # 测试akshare连接
        if not test_akshare_connection():
            logger.error("akshare连接测试失败，程序退出")
            exit(1)
        
        # 创建预处理器
        preprocessor = SimpleAkshareDataPreprocessor()
        
        # 运行处理流水线
        data = preprocessor.run_simple_pipeline()
        
        if data:
            logger.info(f"处理完成！成功处理 {len(data)} 个股票")
            
            # 显示处理结果摘要
            logger.info("=== 处理结果摘要 ===")
            for item in data:
                symbol = item['symbol']
                df = item['data']
                logger.info(f"{symbol}: {len(df)} 条记录, 特征: {list(df.columns)}")
        else:
            logger.error("数据处理失败")
            
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        import traceback
        traceback.print_exc()