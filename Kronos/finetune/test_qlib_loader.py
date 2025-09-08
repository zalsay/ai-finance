import os
import qlib
from qlib.config import REG_CN
from qlib.data import D
from qlib.data.dataset.loader import QlibDataLoader
import pandas as pd

# 测试QlibDataLoader
class LoaderTest:
    def __init__(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.qlib_data_path = os.path.join(self.current_dir, "qlib_data/cn_data")
        
    def test_qlib_init(self):
        print("Testing Qlib initialization...")
        qlib.init(provider_uri=self.qlib_data_path, region=REG_CN)
        print("Qlib initialized successfully!")
        
    def test_qlib_loader(self):
        print("Testing QlibDataLoader...")
        
        # 使用简单的数据字段
        data_fields = ['$close', '$open', '$high', '$low', '$volume']
        
        # 使用较短的时间范围
        start_time = '2020-01-01'
        end_time = '2020-01-10'
        
        print(f"Loading data from {start_time} to {end_time}...")
        print(f"Data fields: {data_fields}")
        print(f"Instrument: csi300")
        
        try:
            loader = QlibDataLoader(config=data_fields)
            print("QlibDataLoader created successfully")
            
            data_df = loader.load('csi300', start_time, end_time)
            print(f"Data loaded successfully!")
            print(f"Data shape: {data_df.shape}")
            print(f"Data columns: {data_df.columns.tolist()[:10]}...")  # 只显示前10个
            print(f"Data index: {data_df.index[:5]}...")  # 只显示前5个
            
        except Exception as e:
            print(f"Error in QlibDataLoader: {e}")
            import traceback
            traceback.print_exc()
        
if __name__ == '__main__':
    test = LoaderTest()
    test.test_qlib_init()
    test.test_qlib_loader()
    print("Test completed!")