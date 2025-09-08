# 修复后的integrate_with_timesfm_forecast代码
# 解决ValueError: Length of values (1172) does not match length of index (128)

import pred_eval
import pandas as pd

def fixed_integrate_with_timesfm_forecast(forecast_df, df_test, stock_code_list):
    """
    修复后的TimesFM预测结果集成函数
    解决数据长度不匹配的问题
    
    参数:
        forecast_df: TimesFM预测结果DataFrame
        df_test: 测试数据DataFrame
        stock_code_list: 股票代码列表
    """
    print("\n=== 与TimesFM预测结果集成（修复版本）===")
    
    # 处理预测结果
    forecast_df["stock_code"] = forecast_df["unique_id"].str.split("_", expand=True)[0]
    
    for stock_code in stock_code_list:
        print(f"\n处理股票: {stock_code}")
        
        # 提取预测数据
        forecast_data = forecast_df[forecast_df['stock_code'] == stock_code].copy()
        print(f"预测数据长度: {len(forecast_data)}")
        
        # 提取实际数据
        original_data = df_test[df_test['stock_code'] == stock_code]
        original_data = original_data[['stock_code', 'ds', 'close']].copy()
        print(f"实际数据长度: {len(original_data)}")
        
        # 确保数据长度匹配 - 取较短的长度
        min_length = min(len(forecast_data), len(original_data))
        print(f"使用数据长度: {min_length}")
        
        if min_length == 0:
            print(f"❌ 股票 {stock_code} 没有匹配的数据，跳过")
            continue
            
        # 截取相同长度的数据
        forecast_data = forecast_data.head(min_length).copy()
        original_data = original_data.head(min_length).copy()
        
        # 重置索引以确保对齐
        forecast_data.reset_index(drop=True, inplace=True)
        original_data.reset_index(drop=True, inplace=True)
        
        # 删除不需要的列
        forecast_data.drop(columns=['stock_code', 'ds'], inplace=True, errors='ignore')
        
        # 合并数据
        forecast_data["stock_code"] = stock_code
        forecast_data["ds"] = original_data["ds"].values
        forecast_data["close"] = original_data["close"].values
        forecast_data["x"] = pd.to_datetime(forecast_data["ds"], unit='ms')
        
        # 准备结果数据
        required_columns = ["x", "close", "timesfm-q-0.1", "timesfm-q-0.2", "timesfm-q-0.3", 
                           "timesfm-q-0.4", "timesfm-q-0.5", "timesfm-q-0.6", "timesfm-q-0.7", 
                           "timesfm-q-0.8", "timesfm-q-0.9"]
        
        # 检查所需列是否存在
        missing_columns = [col for col in required_columns if col not in forecast_data.columns]
        if missing_columns:
            print(f"❌ 缺少列: {missing_columns}")
            print(f"可用列: {forecast_data.columns.tolist()}")
            continue
            
        result = forecast_data[required_columns].copy()
        
        # 生成图表
        try:
            fig_timesfm = pred_eval.fig_plot(result, stock_code)
            fig_timesfm.show()
            print(f"✓ 成功生成股票 {stock_code} 的预测图表")
        except Exception as e:
            print(f"❌ 生成图表时出错: {str(e)}")
            print(f"结果数据形状: {result.shape}")
            print(f"结果数据列: {result.columns.tolist()}")
            print(f"结果数据前5行:")
            print(result.head())

# 简化版本的修复代码（直接在notebook中使用）
def notebook_fix():
    """
    在notebook中直接使用的修复代码
    """
    code = '''
# 修复后的代码 - 直接复制到notebook单元格中
import pred_eval
forecast_df["stock_code"] = forecast_df["unique_id"].str.split("_", expand=True)[0]

for stock_code in stock_code_list:
    print(f"\\n处理股票: {stock_code}")
    
    # 提取预测数据
    forecast_data = forecast_df[forecast_df['stock_code'] == stock_code].copy()
    print(f"预测数据长度: {len(forecast_data)}")
    
    # 提取实际数据
    original_data = df_test[df_test['stock_code'] == stock_code]
    original_data = original_data[['stock_code', 'ds', 'close']].copy()
    print(f"实际数据长度: {len(original_data)}")
    
    # 确保数据长度匹配 - 取较短的长度
    min_length = min(len(forecast_data), len(original_data))
    print(f"使用数据长度: {min_length}")
    
    if min_length == 0:
        print(f"❌ 股票 {stock_code} 没有匹配的数据，跳过")
        continue
        
    # 截取相同长度的数据
    forecast_data = forecast_data.head(min_length).copy()
    original_data = original_data.head(min_length).copy()
    
    # 重置索引以确保对齐
    forecast_data.reset_index(drop=True, inplace=True)
    original_data.reset_index(drop=True, inplace=True)
    
    # 删除不需要的列
    forecast_data.drop(columns=['stock_code', 'ds'], inplace=True, errors='ignore')
    
    # 合并数据
    forecast_data["stock_code"] = stock_code
    forecast_data["ds"] = original_data["ds"].values
    forecast_data["close"] = original_data["close"].values
    forecast_data["x"] = pd.to_datetime(forecast_data["ds"], unit='ms')

    # 准备结果数据
    result = forecast_data[["x", "close", "timesfm-q-0.1", "timesfm-q-0.2", "timesfm-q-0.3", "timesfm-q-0.4", "timesfm-q-0.5", "timesfm-q-0.6", "timesfm-q-0.7", "timesfm-q-0.8", "timesfm-q-0.9"]].copy()
    
    # 生成图表
    try:
        fig_timesfm = pred_eval.fig_plot(result, stock_code)
        fig_timesfm.show()
        print(f"✓ 成功生成股票 {stock_code} 的预测图表")
    except Exception as e:
        print(f"❌ 生成图表时出错: {str(e)}")
        print(f"结果数据形状: {result.shape}")
        print(f"结果数据列: {result.columns.tolist()}")
'''
    return code

if __name__ == "__main__":
    print("修复代码已准备就绪！")
    print("\n使用方法:")
    print("1. 导入此文件: from fixed_integration_code import fixed_integrate_with_timesfm_forecast")
    print("2. 调用修复后的函数: fixed_integrate_with_timesfm_forecast(forecast_df, df_test, stock_code_list)")
    print("\n或者直接复制notebook_fix()函数返回的代码到notebook中使用")