import os
import qlib
from qlib.config import REG_CN
from qlib.data import D
import pandas as pd

# 更简单的测试脚本
class SimpleTest:
    def __init__(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.qlib_data_path = os.path.join(self.current_dir, "qlib_data/cn_data")
        
    def test_qlib_init(self):
        print("Testing Qlib initialization...")
        qlib.init(provider_uri=self.qlib_data_path, region=REG_CN)
        print("Qlib initialized successfully!")
        
    def test_calendar(self):
        print("Testing calendar...")
        cal = D.calendar()
        print(f"Calendar length: {len(cal)}")
        print(f"First date: {cal[0]}")
        print(f"Last date: {cal[-1]}")
        
    def test_instruments(self):
        print("Testing instruments...")
        instruments = D.instruments('csi300')
        print(f"Instruments type: {type(instruments)}")
        print(f"Number of instruments: {len(instruments)}")
        # 转换为列表来查看前几个
        if hasattr(instruments, 'tolist'):
            inst_list = instruments.tolist()
            print(f"First 5 instruments: {inst_list[:5]}")
        else:
            print(f"Instruments: {instruments}")
        
    def test_single_stock(self):
        print("Testing single stock data...")
        # 测试单个股票的数据
        try:
            data = D.features(['SH600000'], ['$close'], '2020-01-01', '2020-01-10')
            print(f"Single stock data shape: {data.shape}")
            print("Single stock data loaded successfully!")
        except Exception as e:
            print(f"Error loading single stock data: {e}")
        
if __name__ == '__main__':
    test = SimpleTest()
    test.test_qlib_init()
    test.test_calendar()
    test.test_instruments()
    test.test_single_stock()
    print("All tests completed!")