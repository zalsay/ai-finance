import os
import pickle
import numpy as np
import pandas as pd
import  as ak
from datetime import datetime, timedelta
from tqdm import trange
import logging
import warnings
warnings.filterwarnings('ignore')

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('akshare_data_preprocess.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AkshareDataPreprocessor:
    """
    基于akshare库的金融数据预处理类，实现与qlib相同功能的数据准备方案
    
    主要功能：
    1. 从akshare获取股票历史数据
    2. 数据清洗和格式转换
    3. 计算技术指标和衍生特征
    4. 数据集分割和保存
    """
    
    def __init__(self):
        """初始化数据预处理器，设置配置参数和数据字段"""
        logger.info("初始化AkshareDataPreprocessor...")
        
        # 基础配置参数
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 股票代码列表 - 使用与qlib相同的股票
        self.instrument = ['600000', '600009', '600010', '600015', '600016']  # 去掉SH前缀，akshare使用纯数字代码
        
        # 数据时间范围配置
        self.dataset_begin_time = "2010-01-01"
        self.dataset_end_time = "2025-06-30"
        
        # 滑动窗口参数，用于创建样本
        self.lookback_window = 90  # 输入的历史时间步数
        self.predict_window = 10   # 预测的未来时间步数
        
        # 原始数据字段定义
        self.data_fields = ['open', 'close', 'high', 'low', 'volume']  # akshare返回的基础字段
        
        # 最终特征列表，包含计算得出的衍生特征
        self.feature_list = ['open', 'high', 'low', 'close', 'vol', 'amt']
        
        # 数据集分割时间范围
        self.train_time_range = ["2010-01-01", "2020-04-30"]
        self.val_time_range = ["2020-05-01", "2020-05-31"]
        self.test_time_range = ["2020-06-01", "2020-06-30"]
        
        # 数据保存路径
        self.dataset_path = os.path.join(self.current_dir, "akshare/processed_datasets")
        
        # 存储处理后的数据，字典格式：{股票代码: DataFrame}
        self.data = {}
        
        logger.info(f"配置完成 - 股票列表: {self.instrument}")
        logger.info(f"时间范围: {self.dataset_begin_time} 到 {self.dataset_end_time}")
        logger.info(f"特征字段: {self.feature_list}")
    
    def get_stock_data_from_akshare(self, symbol, start_date, end_date, max_retries=3):
        """
        从akshare获取单个股票的历史数据
        
        参数:
            symbol (str): 股票代码，如'600000'
            start_date (str): 开始日期，格式'YYYY-MM-DD'
            end_date (str): 结束日期，格式'YYYY-MM-DD'
            max_retries (int): 最大重试次数
            
        返回:
            pandas.DataFrame: 包含OHLCV数据的DataFrame，索引为日期
            
        异常处理:
            - 网络连接异常
            - 数据获取失败
            - 数据格式异常
        """
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
                    start_date=start_date.replace('-', ''),  # akshare需要YYYYMMDD格式
                    end_date=end_date.replace('-', ''),
                    adjust="qfq"  # 前复权
                )
                
                if stock_data is None or stock_data.empty:
                    logger.warning(f"股票 {symbol} 返回空数据")
                    return None
                
                # 重命名列名以匹配qlib格式
                # akshare返回的列名：日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
                column_mapping = {
                    '日期': 'datetime',
                    '开盘': 'open',
                    '收盘': 'close', 
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount'
                }
                
                # 选择需要的列并重命名
                required_columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额']
                available_columns = [col for col in required_columns if col in stock_data.columns]
                
                if len(available_columns) < 6:  # 至少需要OHLCV数据
                    logger.error(f"股票 {symbol} 数据列不完整，可用列: {available_columns}")
                    return None
                
                stock_data = stock_data[available_columns].copy()
                stock_data.rename(columns=column_mapping, inplace=True)
                
                # 设置日期为索引
                stock_data['datetime'] = pd.to_datetime(stock_data['datetime'])
                stock_data.set_index('datetime', inplace=True)
                
                # 数据类型转换，确保数值列为float类型
                numeric_columns = ['open', 'close', 'high', 'low', 'volume']
                if 'amount' in stock_data.columns:
                    numeric_columns.append('amount')
                    
                for col in numeric_columns:
                    if col in stock_data.columns:
                        stock_data[col] = pd.to_numeric(stock_data[col], errors='coerce')
                
                # 按日期排序
                stock_data.sort_index(inplace=True)
                
                logger.info(f"成功获取股票 {symbol} 数据，共 {len(stock_data)} 条记录")
                return stock_data
                
            except Exception as e:
                logger.error(f"获取股票 {symbol} 数据失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"等待3秒后重试...")
                    import time
                    time.sleep(3)
                else:
                    logger.error(f"股票 {symbol} 数据获取最终失败")
                    return None
        
        return None
    
    def calculate_derived_features(self, df):
        """
        计算衍生特征，与qlib保持一致的特征工程
        
        参数:
            df (pandas.DataFrame): 包含OHLCV数据的DataFrame
            
        返回:
            pandas.DataFrame: 添加了衍生特征的DataFrame
            
        计算的特征:
            - vol: 成交量 (直接使用volume)
            - amt: 成交额 (如果akshare没有提供，则用均价*成交量估算)
        """
        logger.debug("计算衍生特征...")
        
        try:
            # 复制数据避免修改原始数据
            result_df = df.copy()
            
            # 计算vol特征：直接使用成交量
            result_df['vol'] = result_df['volume']
            
            # 计算amt特征：成交额
            if 'amount' in result_df.columns and not result_df['amount'].isna().all():
                # 如果akshare提供了成交额数据，直接使用
                result_df['amt'] = result_df['amount']
            else:
                # 如果没有成交额数据，使用OHLC均价乘以成交量估算
                # 这与qlib中的计算方式保持一致
                avg_price = (result_df['open'] + result_df['high'] + 
                           result_df['low'] + result_df['close']) / 4
                result_df['amt'] = avg_price * result_df['vol']
                logger.debug("使用OHLC均价计算成交额")
            
            # 选择最终的特征列
            result_df = result_df[self.feature_list]
            
            logger.debug(f"衍生特征计算完成，最终特征: {list(result_df.columns)}")
            return result_df
            
        except Exception as e:
            logger.error(f"计算衍生特征时出错: {str(e)}")
            raise
    
    def load_akshare_data(self):
        """
        从akshare加载原始数据，逐个股票处理并存储到self.data中
        
        处理流程:
        1. 遍历股票列表
        2. 为每个股票获取历史数据
        3. 数据清洗和特征计算
        4. 过滤数据不足的股票
        5. 存储到内存中
        
        异常处理:
        - 单个股票获取失败不影响其他股票
        - 记录详细的错误日志
        """
        logger.info("开始从akshare加载和处理数据...")
        
        # 计算实际需要的数据时间范围
        # 需要考虑lookback_window和predict_window的缓冲
        start_date = pd.to_datetime(self.dataset_begin_time)
        end_date = pd.to_datetime(self.dataset_end_time)
        
        # 向前扩展开始时间以提供足够的历史数据
        buffer_start = start_date - timedelta(days=self.lookback_window + 30)  # 额外30天缓冲
        # 向后扩展结束时间以提供预测窗口
        buffer_end = end_date + timedelta(days=self.predict_window + 30)  # 额外30天缓冲
        
        actual_start = buffer_start.strftime('%Y-%m-%d')
        actual_end = buffer_end.strftime('%Y-%m-%d')
        
        logger.info(f"实际数据获取范围: {actual_start} 到 {actual_end}")
        logger.info(f"处理股票列表: {self.instrument}")
        
        successful_count = 0
        failed_stocks = []
        
        # 遍历股票列表进行数据处理
        for i in trange(len(self.instrument), desc="处理股票数据"):
            symbol = self.instrument[i]
            
            try:
                logger.info(f"正在处理股票: {symbol}")
                
                # 从akshare获取股票数据
                stock_df = self.get_stock_data_from_akshare(symbol, actual_start, actual_end)
                
                if stock_df is None or stock_df.empty:
                    logger.warning(f"股票 {symbol} 数据获取失败或为空")
                    failed_stocks.append(symbol)
                    continue
                
                # 数据清洗：移除缺失值
                original_length = len(stock_df)
                stock_df = stock_df.dropna()
                cleaned_length = len(stock_df)
                
                if original_length != cleaned_length:
                    logger.info(f"股票 {symbol} 清洗了 {original_length - cleaned_length} 条缺失数据")
                
                # 检查数据长度是否满足要求
                min_required_length = self.lookback_window + self.predict_window + 1
                if len(stock_df) < min_required_length:
                    logger.warning(f"股票 {symbol} 数据不足: {len(stock_df)} < {min_required_length}，跳过")
                    failed_stocks.append(symbol)
                    continue
                
                # 计算衍生特征
                stock_df = self.calculate_derived_features(stock_df)
                
                # 最终数据验证
                if stock_df.isnull().any().any():
                    logger.warning(f"股票 {symbol} 计算特征后仍有缺失值，进行最终清洗")
                    stock_df = stock_df.dropna()
                    
                    if len(stock_df) < min_required_length:
                        logger.warning(f"股票 {symbol} 最终清洗后数据不足，跳过")
                        failed_stocks.append(symbol)
                        continue
                
                # 存储处理后的数据，使用带SH前缀的格式以保持与qlib一致
                symbol_key = f"SH{symbol}"
                self.data[symbol_key] = stock_df
                successful_count += 1
                
                logger.info(f"股票 {symbol} 处理完成，数据长度: {len(stock_df)}")
                
            except Exception as e:
                logger.error(f"处理股票 {symbol} 时发生异常: {str(e)}")
                failed_stocks.append(symbol)
                continue
        
        # 处理结果汇总
        logger.info(f"数据加载完成！")
        logger.info(f"成功处理: {successful_count} 个股票")
        logger.info(f"失败股票: {len(failed_stocks)} 个")
        
        if failed_stocks:
            logger.warning(f"失败的股票列表: {failed_stocks}")
        
        if successful_count == 0:
            logger.error("没有成功处理任何股票数据！")
            raise ValueError("数据加载失败：没有可用的股票数据")
        
        logger.info(f"最终可用股票: {list(self.data.keys())}")
    
    def prepare_dataset(self):
        """
        将加载的数据分割为训练集、验证集和测试集，并保存到磁盘
        
        分割策略:
        1. 按时间范围分割数据
        2. 训练集：2010-01-01 到 2020-04-30
        3. 验证集：2020-05-01 到 2020-05-31
        4. 测试集：2020-06-01 到 2020-06-30
        
        保存格式:
        - 使用pickle格式保存
        - 每个数据集保存为字典：{股票代码: DataFrame}
        """
        logger.info("开始准备数据集分割...")
        
        if not self.data:
            raise ValueError("没有可用的数据进行分割，请先运行load_akshare_data()")
        
        # 初始化数据集字典
        train_data, val_data, test_data = {}, {}, {}
        
        # 解析时间范围
        train_start, train_end = self.train_time_range
        val_start, val_end = self.val_time_range
        test_start, test_end = self.test_time_range
        
        logger.info(f"训练集时间范围: {train_start} 到 {train_end}")
        logger.info(f"验证集时间范围: {val_start} 到 {val_end}")
        logger.info(f"测试集时间范围: {test_start} 到 {test_end}")
        
        symbol_list = list(self.data.keys())
        
        # 遍历每个股票进行数据分割
        for i in trange(len(symbol_list), desc="分割数据集"):
            symbol = symbol_list[i]
            symbol_df = self.data[symbol]
            
            try:
                # 创建时间范围的布尔掩码
                train_mask = (symbol_df.index >= train_start) & (symbol_df.index <= train_end)
                val_mask = (symbol_df.index >= val_start) & (symbol_df.index <= val_end)
                test_mask = (symbol_df.index >= test_start) & (symbol_df.index <= test_end)
                
                # 应用掩码创建数据集
                train_subset = symbol_df[train_mask]
                val_subset = symbol_df[val_mask]
                test_subset = symbol_df[test_mask]
                
                # 检查每个子集的数据量
                logger.debug(f"股票 {symbol} - 训练集: {len(train_subset)}, 验证集: {len(val_subset)}, 测试集: {len(test_subset)}")
                
                # 只保存有数据的子集
                if len(train_subset) > 0:
                    train_data[symbol] = train_subset
                if len(val_subset) > 0:
                    val_data[symbol] = val_subset
                if len(test_subset) > 0:
                    test_data[symbol] = test_subset
                    
            except Exception as e:
                logger.error(f"分割股票 {symbol} 数据时出错: {str(e)}")
                continue
        
        # 创建保存目录
        os.makedirs(self.dataset_path, exist_ok=True)
        logger.info(f"数据集保存路径: {self.dataset_path}")
        
        # 保存数据集到pickle文件
        datasets = {
            'train_data.pkl': train_data,
            'val_data.pkl': val_data,
            'test_data.pkl': test_data
        }
        
        for filename, dataset in datasets.items():
            filepath = os.path.join(self.dataset_path, filename)
            try:
                with open(filepath, 'wb') as f:
                    pickle.dump(dataset, f)
                logger.info(f"保存 {filename}: {len(dataset)} 个股票")
            except Exception as e:
                logger.error(f"保存 {filename} 时出错: {str(e)}")
                raise
        
        # 输出数据集统计信息
        logger.info("数据集准备完成！")
        logger.info(f"训练集: {len(train_data)} 个股票")
        logger.info(f"验证集: {len(val_data)} 个股票")
        logger.info(f"测试集: {len(test_data)} 个股票")
        
        # 详细统计每个数据集的数据量
        for dataset_name, dataset in [('训练集', train_data), ('验证集', val_data), ('测试集', test_data)]:
            if dataset:
                total_records = sum(len(df) for df in dataset.values())
                avg_records = total_records / len(dataset) if dataset else 0
                logger.info(f"{dataset_name}详情: 总记录数 {total_records}, 平均每股 {avg_records:.1f} 条")
    
    def run_full_pipeline(self):
        """
        运行完整的数据预处理流水线
        
        流程:
        1. 数据加载和处理
        2. 数据集分割
        3. 保存结果
        
        异常处理:
        - 捕获并记录所有异常
        - 提供详细的错误信息
        """
        logger.info("开始运行完整的数据预处理流水线...")
        
        try:
            # 步骤1: 加载和处理数据
            logger.info("=== 步骤1: 数据加载和处理 ===")
            self.load_akshare_data()
            
            # 步骤2: 数据集分割和保存
            logger.info("=== 步骤2: 数据集分割和保存 ===")
            self.prepare_dataset()
            
            logger.info("=== 数据预处理流水线完成 ===")
            logger.info("所有数据已成功处理并保存！")
            
        except Exception as e:
            logger.error(f"数据预处理流水线执行失败: {str(e)}")
            raise


if __name__ == '__main__':
    """
    主程序入口：运行akshare数据预处理流水线
    
    使用方法:
        python akshare_data_preprocess.py
    
    输出:
        - 处理后的数据集文件 (train_data.pkl, val_data.pkl, test_data.pkl)
        - 详细的日志文件 (akshare_data_preprocess.log)
    """
    try:
        logger.info("启动akshare数据预处理程序...")
        
        # 创建预处理器实例
        preprocessor = AkshareDataPreprocessor()
        
        # 运行完整流水线
        preprocessor.run_full_pipeline()
        
        logger.info("程序执行完成！")
        
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        raise