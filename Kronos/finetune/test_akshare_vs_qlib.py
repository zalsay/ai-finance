import os
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataComparator:
    """
    数据对比器：比较akshare和qlib数据预处理结果
    
    功能:
    1. 加载akshare和qlib处理的数据
    2. 对比数据格式和结构
    3. 验证数据一致性
    4. 生成对比报告
    """
    
    def __init__(self):
        """初始化数据对比器"""
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 数据文件路径
        self.akshare_simple_file = os.path.join(self.current_dir, 'processed_data_akshare_simple.pkl')
        self.qlib_simple_file = os.path.join(self.current_dir, 'processed_data_simple.pkl')
        
        # qlib数据集路径
        self.qlib_dataset_path = os.path.join(self.current_dir, 'qlib/processed_datasets')
        self.akshare_dataset_path = os.path.join(self.current_dir, 'akshare/processed_datasets')
        
        logger.info("数据对比器初始化完成")
    
    def load_akshare_data(self):
        """
        加载akshare处理的数据
        
        返回:
            dict: 加载的数据或None
        """
        logger.info("加载akshare数据...")
        
        try:
            if os.path.exists(self.akshare_simple_file):
                with open(self.akshare_simple_file, 'rb') as f:
                    data = pickle.load(f)
                logger.info(f"成功加载akshare数据: {len(data)} 个股票")
                return data
            else:
                logger.warning(f"akshare数据文件不存在: {self.akshare_simple_file}")
                return None
                
        except Exception as e:
            logger.error(f"加载akshare数据失败: {str(e)}")
            return None
    
    def load_qlib_data(self):
        """
        加载qlib处理的数据
        
        返回:
            dict: 加载的数据或None
        """
        logger.info("加载qlib数据...")
        
        try:
            if os.path.exists(self.qlib_simple_file):
                with open(self.qlib_simple_file, 'rb') as f:
                    data = pickle.load(f)
                logger.info(f"成功加载qlib数据: {len(data)} 个股票")
                return data
            else:
                logger.warning(f"qlib数据文件不存在: {self.qlib_simple_file}")
                return None
                
        except Exception as e:
            logger.error(f"加载qlib数据失败: {str(e)}")
            return None
    
    def analyze_data_structure(self, data, data_source):
        """
        分析数据结构
        
        参数:
            data: 数据对象
            data_source (str): 数据源名称
        """
        logger.info(f"=== {data_source} 数据结构分析 ===")
        
        if data is None:
            logger.warning(f"{data_source} 数据为空")
            return
        
        if isinstance(data, list):
            logger.info(f"数据类型: 列表，包含 {len(data)} 个元素")
            
            if data:
                first_item = data[0]
                logger.info(f"列表元素结构: {type(first_item)}")
                
                if isinstance(first_item, dict):
                    logger.info(f"字典键: {list(first_item.keys())}")
                    
                    if 'symbol' in first_item:
                        logger.info(f"股票代码: {first_item['symbol']}")
                    
                    if 'data' in first_item and isinstance(first_item['data'], pd.DataFrame):
                        df = first_item['data']
                        logger.info(f"DataFrame形状: {df.shape}")
                        logger.info(f"列名: {list(df.columns)}")
                        logger.info(f"索引类型: {type(df.index)}")
                        logger.info(f"时间范围: {df.index.min()} 到 {df.index.max()}")
                        
                        # 显示数据样本
                        logger.info("数据样本:")
                        logger.info(f"\n{df.head(3)}")
        
        elif isinstance(data, dict):
            logger.info(f"数据类型: 字典，包含 {len(data)} 个股票")
            logger.info(f"股票代码: {list(data.keys())}")
            
            if data:
                first_symbol = list(data.keys())[0]
                first_df = data[first_symbol]
                
                if isinstance(first_df, pd.DataFrame):
                    logger.info(f"DataFrame形状: {first_df.shape}")
                    logger.info(f"列名: {list(first_df.columns)}")
                    logger.info(f"索引类型: {type(first_df.index)}")
                    logger.info(f"时间范围: {first_df.index.min()} 到 {first_df.index.max()}")
                    
                    # 显示数据样本
                    logger.info(f"股票 {first_symbol} 数据样本:")
                    logger.info(f"\n{first_df.head(3)}")
        
        else:
            logger.info(f"数据类型: {type(data)}")
    
    def compare_data_formats(self, akshare_data, qlib_data):
        """
        对比两种数据格式
        
        参数:
            akshare_data: akshare数据
            qlib_data: qlib数据
        """
        logger.info("=== 数据格式对比 ===")
        
        if akshare_data is None or qlib_data is None:
            logger.warning("无法进行对比：其中一个数据源为空")
            return
        
        # 提取股票代码
        if isinstance(akshare_data, list):
            akshare_symbols = [item['symbol'] for item in akshare_data]
        else:
            akshare_symbols = list(akshare_data.keys())
        
        if isinstance(qlib_data, list):
            qlib_symbols = [item['symbol'] for item in qlib_data]
        else:
            qlib_symbols = list(qlib_data.keys())
        
        logger.info(f"akshare股票数量: {len(akshare_symbols)}")
        logger.info(f"qlib股票数量: {len(qlib_symbols)}")
        
        # 找出共同股票
        common_symbols = set(akshare_symbols) & set(qlib_symbols)
        logger.info(f"共同股票: {len(common_symbols)} 个")
        logger.info(f"共同股票列表: {sorted(common_symbols)}")
        
        if common_symbols:
            # 选择一个共同股票进行详细对比
            symbol = list(common_symbols)[0]
            logger.info(f"\n详细对比股票: {symbol}")
            
            # 获取对应的DataFrame
            if isinstance(akshare_data, list):
                akshare_df = next(item['data'] for item in akshare_data if item['symbol'] == symbol)
            else:
                akshare_df = akshare_data[symbol]
            
            if isinstance(qlib_data, list):
                qlib_df = next(item['data'] for item in qlib_data if item['symbol'] == symbol)
            else:
                qlib_df = qlib_data[symbol]
            
            self.compare_dataframes(akshare_df, qlib_df, symbol)
    
    def compare_dataframes(self, df1, df2, symbol):
        """
        对比两个DataFrame
        
        参数:
            df1 (pd.DataFrame): akshare数据
            df2 (pd.DataFrame): qlib数据
            symbol (str): 股票代码
        """
        logger.info(f"--- 股票 {symbol} DataFrame对比 ---")
        
        # 基本信息对比
        logger.info(f"akshare形状: {df1.shape}, qlib形状: {df2.shape}")
        logger.info(f"akshare列名: {list(df1.columns)}")
        logger.info(f"qlib列名: {list(df2.columns)}")
        
        # 时间范围对比
        logger.info(f"akshare时间范围: {df1.index.min()} 到 {df1.index.max()}")
        logger.info(f"qlib时间范围: {df2.index.min()} 到 {df2.index.max()}")
        
        # 列名对比
        common_cols = set(df1.columns) & set(df2.columns)
        logger.info(f"共同列: {sorted(common_cols)}")
        
        akshare_only = set(df1.columns) - set(df2.columns)
        qlib_only = set(df2.columns) - set(df1.columns)
        
        if akshare_only:
            logger.info(f"akshare独有列: {sorted(akshare_only)}")
        if qlib_only:
            logger.info(f"qlib独有列: {sorted(qlib_only)}")
        
        # 数据值对比（如果有共同的时间和列）
        if common_cols:
            common_times = df1.index.intersection(df2.index)
            if len(common_times) > 0:
                logger.info(f"共同时间点: {len(common_times)} 个")
                
                # 选择一个共同列进行数值对比
                col = list(common_cols)[0]
                sample_times = common_times[:5]  # 取前5个时间点
                
                logger.info(f"\n列 '{col}' 数值对比（前5个共同时间点）:")
                for time in sample_times:
                    val1 = df1.loc[time, col]
                    val2 = df2.loc[time, col]
                    diff = abs(val1 - val2) if pd.notna(val1) and pd.notna(val2) else 'N/A'
                    logger.info(f"  {time}: akshare={val1:.4f}, qlib={val2:.4f}, 差异={diff}")
    
    def generate_comparison_report(self):
        """
        生成完整的对比报告
        """
        logger.info("开始生成数据对比报告...")
        
        # 加载数据
        akshare_data = self.load_akshare_data()
        qlib_data = self.load_qlib_data()
        
        # 分析数据结构
        self.analyze_data_structure(akshare_data, "AkShare")
        self.analyze_data_structure(qlib_data, "Qlib")
        
        # 对比数据格式
        self.compare_data_formats(akshare_data, qlib_data)
        
        logger.info("数据对比报告生成完成")


def test_data_loading():
    """
    测试数据加载功能
    """
    logger.info("=== 数据加载测试 ===")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 测试文件列表
    test_files = [
        ('akshare简化数据', os.path.join(current_dir, 'processed_data_akshare_simple.pkl')),
        ('qlib简化数据', os.path.join(current_dir, 'processed_data_simple.pkl')),
    ]
    
    for name, filepath in test_files:
        logger.info(f"\n测试 {name}:")
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    data = pickle.load(f)
                
                logger.info(f"  ✓ 文件加载成功")
                logger.info(f"  ✓ 数据类型: {type(data)}")
                
                if isinstance(data, list):
                    logger.info(f"  ✓ 数据长度: {len(data)}")
                    if data:
                        logger.info(f"  ✓ 第一个元素类型: {type(data[0])}")
                elif isinstance(data, dict):
                    logger.info(f"  ✓ 字典键数量: {len(data)}")
                    logger.info(f"  ✓ 键列表: {list(data.keys())[:3]}...")  # 显示前3个键
                
            except Exception as e:
                logger.error(f"  ✗ 加载失败: {str(e)}")
        else:
            logger.warning(f"  ✗ 文件不存在: {filepath}")


def check_data_consistency():
    """
    检查数据一致性
    """
    logger.info("=== 数据一致性检查 ===")
    
    try:
        comparator = DataComparator()
        
        # 加载数据
        akshare_data = comparator.load_akshare_data()
        qlib_data = comparator.load_qlib_data()
        
        if akshare_data and qlib_data:
            logger.info("✓ 两种数据都加载成功")
            
            # 检查数据格式一致性
            logger.info("\n检查数据格式一致性...")
            
            # 检查特征列是否一致
            expected_features = ['open', 'high', 'low', 'close', 'vol', 'amt']
            
            # 从akshare数据中提取特征
            if isinstance(akshare_data, list) and akshare_data:
                akshare_features = list(akshare_data[0]['data'].columns)
            else:
                akshare_features = []
            
            # 从qlib数据中提取特征
            if isinstance(qlib_data, list) and qlib_data:
                qlib_features = list(qlib_data[0]['data'].columns)
            else:
                qlib_features = []
            
            logger.info(f"期望特征: {expected_features}")
            logger.info(f"akshare特征: {akshare_features}")
            logger.info(f"qlib特征: {qlib_features}")
            
            # 检查特征一致性
            akshare_match = set(akshare_features) == set(expected_features)
            qlib_match = set(qlib_features) == set(expected_features)
            
            logger.info(f"akshare特征匹配: {'✓' if akshare_match else '✗'}")
            logger.info(f"qlib特征匹配: {'✓' if qlib_match else '✗'}")
            
            if akshare_match and qlib_match:
                logger.info("✓ 数据格式一致性检查通过")
            else:
                logger.warning("✗ 数据格式存在差异")
        
        else:
            logger.warning("无法进行一致性检查：数据加载不完整")
            
    except Exception as e:
        logger.error(f"数据一致性检查失败: {str(e)}")


if __name__ == '__main__':
    """
    主程序：运行数据对比测试
    
    使用方法:
        python test_akshare_vs_qlib.py
    """
    try:
        logger.info("启动akshare vs qlib数据对比测试...")
        
        # 1. 测试数据加载
        test_data_loading()
        
        # 2. 检查数据一致性
        check_data_consistency()
        
        # 3. 生成详细对比报告
        comparator = DataComparator()
        comparator.generate_comparison_report()
        
        logger.info("\n=== 测试完成 ===")
        logger.info("如果要运行数据预处理，请先执行:")
        logger.info("  python akshare_data_preprocess_simple.py")
        logger.info("  python qlib_data_preprocess_simple.py")
        
    except Exception as e:
        logger.error(f"测试执行失败: {str(e)}")
        import traceback
        traceback.print_exc()