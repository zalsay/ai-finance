import os
import qlib
from qlib.config import REG_CN
from qlib.data.dataset.loader import QlibDataLoader
import pandas as pd
from tqdm import trange
import pickle

class SimpleQlibDataPreprocessor:
    def __init__(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.qlib_data_path = os.path.join(self.current_dir, "qlib_data/cn_data")
        
        # 简化的配置
        self.instrument = ['SH600000', 'SH600009', 'SH600010']  # 只使用3个股票
        self.dataset_begin_time = '2020-01-01'
        self.dataset_end_time = '2020-03-31'  # 只使用3个月的数据
        self.lookback_window = 30
        self.predict_window = 5
        self.data_fields = ['open', 'close', 'high', 'low', 'volume']
        self.feature_list = ['open', 'close', 'high', 'low', 'vol', 'amt']
        
    def load_qlib_data(self):
        print("Initializing Qlib...")
        qlib.init(provider_uri=self.qlib_data_path, region=REG_CN)
        
        print("Loading and processing data from Qlib...")
        
        # Prepare data fields for Qlib.
        data_fields_qlib = [f'${field}' for field in self.data_fields] + ['$vwap']
        
        # Get calendar and adjust time range.
        cal = qlib.data.D.calendar()
        start_index = cal.searchsorted(pd.Timestamp(self.dataset_begin_time))
        end_index = cal.searchsorted(pd.Timestamp(self.dataset_end_time))
        
        adjusted_start_index = max(start_index - self.lookback_window, 0)
        real_start_time = cal[adjusted_start_index]
        
        if end_index >= len(cal):
            end_index = len(cal) - 1
        elif cal[end_index] != pd.Timestamp(self.dataset_end_time):
            end_index -= 1
            
        adjusted_end_index = min(end_index + self.predict_window, len(cal) - 1)
        real_end_time = cal[adjusted_end_index]
        
        print(f"Loading data for instruments: {self.instrument}")
        print(f"Time range: {real_start_time} to {real_end_time}")
        print(f"Data fields: {data_fields_qlib}")
        
        # Load data using Qlib's data loader.
        try:
            data_df = QlibDataLoader(config=data_fields_qlib).load(
                self.instrument, real_start_time, real_end_time
            )
            print(f"Data loaded successfully, shape: {data_df.shape}")
            data_df = data_df.stack().unstack(level=1)  # Reshape for easier access.
            print(f"Data reshaped, new shape: {data_df.shape}")
        except Exception as e:
            print(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        symbol_list = list(data_df.columns)
        print(f"Processing {len(symbol_list)} symbols...")
        
        processed_data = []
        
        for i in trange(len(symbol_list), desc="Processing Symbols"):
            symbol = symbol_list[i]
            symbol_df = data_df[symbol]
            
            # Pivot the table to have features as columns and datetime as index.
            symbol_df = symbol_df.reset_index().rename(columns={'level_1': 'field'})
            symbol_df = pd.pivot(symbol_df, index='datetime', columns='field', values=symbol)
            symbol_df = symbol_df.rename(columns={f'${field}': field for field in self.data_fields})
            
            # Calculate amount and select final features.
            symbol_df['vol'] = symbol_df['volume']
            symbol_df['amt'] = (symbol_df['open'] + symbol_df['high'] + symbol_df['low'] + symbol_df['close']) / 4 * symbol_df['vol']
            symbol_df = symbol_df[self.feature_list]
            
            # Filter out symbols with insufficient data.
            symbol_df = symbol_df.dropna()
            if len(symbol_df) < self.lookback_window + self.predict_window + 1:
                print(f"Skipping {symbol} due to insufficient data: {len(symbol_df)} rows")
                continue
                
            processed_data.append({
                'symbol': symbol,
                'data': symbol_df
            })
            
        print(f"Successfully processed {len(processed_data)} symbols")
        
        # Save processed data
        output_file = os.path.join(self.current_dir, 'processed_data_simple.pkl')
        with open(output_file, 'wb') as f:
            pickle.dump(processed_data, f)
        print(f"Data saved to {output_file}")
        
        return processed_data

if __name__ == '__main__':
    preprocessor = SimpleQlibDataPreprocessor()
    data = preprocessor.load_qlib_data()
    if data:
        print(f"Preprocessing completed successfully! Processed {len(data)} symbols.")
    else:
        print("Preprocessing failed.")