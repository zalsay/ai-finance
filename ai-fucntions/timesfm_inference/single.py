import os, sys, asyncio
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import json
import matplotlib.pyplot as plt
    
current_dir = os.path.dirname(os.path.abspath(__file__))
finance_dir = os.path.dirname(current_dir)
akshare_dir = os.path.join(finance_dir, 'akshare-tools')
sys.path.append(akshare_dir)
from get_finanial_data import talib_tools
pre_data_dir = os.path.join(finance_dir, 'preprocess_data')
sys.path.append(pre_data_dir)
from process_from_ak import df_preprocess
from math_functions import *
from datetime import datetime
debug_info = {
    "execution_time": datetime.now().isoformat(),
    "parameters": {},
    "data_processing": {},
    "prediction_results": {},
    "errors": []
}

def integrate_with_timesfm_forecast(forecast_df, df_test, stock_code_list):
    """
    将TimesFM预测结果与实际数据集成
    
    Args:
        forecast_df: 预测数据框
        df_test: 测试数据框
        stock_code_list: 股票代码列表
    """
    print("\n=== 开始执行integrate_with_timesfm_forecast函数 ===")
    results = {}
    figures = []
    
    # 首先处理所有股票的日期修正，然后再绘图
    corrected_forecast_df = forecast_df.copy()
    
    for stock_code in stock_code_list:
        # 过滤特定股票的数据
        stock_forecast = forecast_df[forecast_df['unique_id'] == stock_code].copy()
        stock_test = df_test[df_test['stock_code'] == stock_code].copy()
        
        # 将日期转换为pandas datetime以便比较
        stock_forecast['ds'] = pd.to_datetime(stock_forecast['ds'])
        stock_test['ds'] = pd.to_datetime(stock_test['ds'])
        
        print(f"\n=== 处理股票 {stock_code} ===\n")
        
        # 直接使用原始数据，不进行交易日过滤
        stock_forecast_filtered = stock_forecast.copy()
        stock_test_filtered = stock_test.copy()
        
        # 确保两个数据集长度一致
        min_length = min(len(stock_forecast_filtered), len(stock_test_filtered))
        stock_forecast_filtered = stock_forecast_filtered.head(min_length)
        stock_test_filtered = stock_test_filtered.head(min_length)
        
        # 按日期排序
        stock_forecast_filtered = stock_forecast_filtered.sort_values('ds')
        stock_test_filtered = stock_test_filtered.sort_values('ds')
        
        
        # 计算所有预测列的误差，选择最佳组合
        actual_values = stock_test_filtered['close'].values
        
        # 获取所有timesfm预测列
        forecast_columns = [col for col in stock_forecast_filtered.columns if col.startswith('timesfm-q-')]
        
        best_mse = float('inf')
        best_mae = float('inf')
        best_column = 'timesfm-q-0.5'  # 默认值
        best_combined_score = float('inf')
        
        # 计算每个预测列的MSE和MAE
        for col in forecast_columns:
            forecast_values = stock_forecast_filtered[col].values
            mse = mean_squared_error(forecast_values, actual_values)
            mae = mean_absolute_error(forecast_values, actual_values)
            
            # 使用MSE和MAE的加权组合作为综合评分（可以调整权重）
            combined_score = 0.5 * mse + 0.5 * mae
                        
            # 选择综合评分最低的列
            if combined_score < best_combined_score:
                best_combined_score = combined_score
                best_mse = mse
                best_mae = mae
                best_column = col
        
        print(f"\n最佳预测列: {best_column}, 最佳MSE: {best_mse:.4f}, 最佳MAE: {best_mae:.4f}, 综合评分: {best_combined_score:.4f}")
        
        # 使用最佳列的值
        mse = best_mse
        mae = best_mae
        best_forecast_values = stock_forecast_filtered[best_column].values
        
        # 创建plot_df数据，使用最佳预测列
        min_len = min(len(stock_forecast_filtered), len(stock_test_filtered))
        plot_df = pd.DataFrame({
            'index': range(min_len),
            'actual': stock_test_filtered['close'].values[:min_len],
            'forecast': best_forecast_values[:min_len],
            'forecast_lower': stock_forecast_filtered['timesfm-q-0.1'].values[:min_len] if 'timesfm-q-0.1' in stock_forecast_filtered.columns else best_forecast_values[:min_len] * 0.95,
            'forecast_upper': stock_forecast_filtered['timesfm-q-0.9'].values[:min_len] if 'timesfm-q-0.9' in stock_forecast_filtered.columns else best_forecast_values[:min_len] * 1.05
        })
        
        results[stock_code] = {
            'mse': mse,
            'mae': mae,
            'best_column': best_column,
            'best_combined_score': best_combined_score,
            'forecast_data': stock_forecast_filtered,
            'actual_data': stock_test_filtered,
            'plot_df': plot_df
        }
    
    # 创建只包含horizon_len长度的绘图数据
    print("\n=== 创建horizon_len长度的绘图数据 ===")
    horizon_len = len(corrected_forecast_df[corrected_forecast_df['unique_id'] == stock_code_list[0]])
    print(f"horizon_len: {horizon_len}")
    
    for stock_code in stock_code_list:
        # 获取预测数据（已经是horizon_len长度）
        forecast_data = corrected_forecast_df[corrected_forecast_df['unique_id'] == stock_code].copy().reset_index(drop=True)
        
        # 获取测试数据的前horizon_len条记录
        test_data = df_test[df_test['unique_id'] == stock_code].head(horizon_len).copy().reset_index(drop=True)
        
        # 直接按顺序创建绘图DataFrame，不进行日期验证
        min_len = min(len(forecast_data), len(test_data))
        
        # 为当前股票选择最佳预测列
        actual_values_plot = test_data['close'].values[:min_len]
        forecast_columns = [col for col in forecast_data.columns if col.startswith('timesfm-q-')]
        
        best_column = 'timesfm-q-0.5'  # 默认值
        best_combined_score = float('inf')
        
        # print(f"为股票 {stock_code} 选择最佳预测列:")
        for col in forecast_columns:
            forecast_values_plot = forecast_data[col].values[:min_len]
            mse_plot = mean_squared_error(forecast_values_plot, actual_values_plot)
            mae_plot = mean_absolute_error(forecast_values_plot, actual_values_plot)
            combined_score_plot = 0.5 * mse_plot + 0.5 * mae_plot
            
            # print(f"  {col}: MSE={mse_plot:.4f}, MAE={mae_plot:.4f}, 综合评分={combined_score_plot:.4f}")
            
            if combined_score_plot < best_combined_score:
                best_combined_score = combined_score_plot
                best_column = col
        
        print(f"选择的最佳预测列: {best_column}, 综合评分: {best_combined_score:.4f}")
        
        # 创建绘图DataFrame，使用最佳预测列
        plot_df = pd.DataFrame({
            'index': range(min_len),
            'actual': test_data['close'].values[:min_len],
            'forecast': forecast_data[best_column].values[:min_len],
            'forecast_lower': forecast_data['timesfm-q-0.1'].values[:min_len],
            'forecast_upper': forecast_data['timesfm-q-0.9'].values[:min_len]
        })
        
        print(f"绘图数据长度: {len(plot_df)}")
        
        # 更新results中的信息，包含最佳列信息
        if stock_code in results:
            results[stock_code]['plot_df'] = plot_df
            results[stock_code]['best_column_plot'] = best_column
            results[stock_code]['best_combined_score_plot'] = best_combined_score
        
        # 保存为CSV
        csv_filename = os.path.join(finance_dir, f"forecast-results/{stock_code}_horizon_plot_data.csv")
        plot_df.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"绘图数据已保存: {csv_filename}")
        
        # 使用绘图数据进行绘图
        # fig = plot_forecast_vs_actual_simple(plot_df, stock_code)
        # if fig is not None:
        #     figures.append(fig)
    
    return results, figures

async def process_single_stock(stock_code, stock_type, time_step, years, horizon_len, tfm):
    """
    异步处理单个股票的预测任务
    """

    print(f"开始处理股票: {stock_code}")
    
    try:
        # 数据预处理
        df_original, df_train, df_test = df_preprocess(stock_code, stock_type, time_step, years=years, horizon_len=horizon_len)
        
        # 添加唯一标识符
        df_train["unique_id"] = df_train["stock_code"].astype(str)
        df_test["unique_id"] = df_test["stock_code"].astype(str)
        
        # 可选：添加技术指标
        try:
            df_train, input_features = talib_tools(df_train)
            print(f"股票 {stock_code} 技术指标添加成功")
        except Exception as e:
            print(f"股票 {stock_code} 添加技术指标失败: {e}")
            print("继续使用原始数据...")
        
        # 为预测准备数据：去掉绘图日期列，只保留推理需要的列
        df_train_for_prediction = df_train.copy()
        if 'ds_plot' in df_train_for_prediction.columns:
            df_train_for_prediction = df_train_for_prediction.drop(columns=['ds_plot'])
        
        print(f"股票 {stock_code} 开始预测...")
        
        # 在线程池中执行预测（因为TimesFM可能不是异步的）
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            forecast_df = await loop.run_in_executor(
                executor,
                lambda: tfm.forecast_on_df(
                    inputs=df_train_for_prediction,
                    freq="D",
                    value_name="close",
                    num_jobs=1,  # 单个股票使用单线程
                )
            )
        
        # 为预测结果添加绘图日期列
        if 'ds' in forecast_df.columns:
            forecast_df['ds_plot'] = pd.to_datetime(forecast_df['ds']).dt.strftime('%Y-%m-%d')
            print("\n已为预测结果添加绘图日期列")
            print(f"预测结果ds_plot列前5个值: {forecast_df['ds_plot'].head().tolist()}")
            print(f"预测结果ds列前5个值: {forecast_df['ds'].head().tolist()}")
            print(f"预测结果ds列类型: {forecast_df['ds'].dtype}")
            print(f"预测结果ds_plot列类型: {forecast_df['ds_plot'].dtype}")
            print(f"股票 {stock_code} 已为预测结果添加绘图日期列")
        
        # debug_info相关代码已删除
        # 集成预测结果
        print(f"股票 {stock_code} 集成预测结果与实际数据...")
        results, figures = integrate_with_timesfm_forecast(forecast_df, df_test, [stock_code])
        
    except Exception as e:
        error_msg = f"预测过程出错: {str(e)}"
        debug_info["errors"].append(error_msg)
        print(f"❌ {error_msg}")
        # 保存调试信息并退出
        with open("main_program_debug.json", 'w', encoding='utf-8') as f:
            json.dump(debug_info, f, ensure_ascii=False, indent=2)
        return
    
    # 集成预测结果
    print("\n集成预测结果与实际数据...")
    print(f"forecast_df shape: {forecast_df.shape}")
    print(f"df_test shape: {df_test.shape}")
    print(f"stock_code_list: {stock_code_list}")
    try:
        results, figures = integrate_with_timesfm_forecast(forecast_df, df_test, stock_code_list, df_train)
        
        # debug_info集成结果记录已删除
        
    except Exception as e:
        error_msg = f"集成结果时出错: {str(e)}"
        print(f"❌ {error_msg}")
    
    # 保存结果
    print("\n保存预测图片...")
    try:
        # for stock_code, result in results.items():
        # 保存结果
        print(f"股票 {stock_code} 保存预测图片...")
        for stock_code_key, result in results.items():
            # 保存预测对比图为PNG格式
            print(f"保存股票 {stock_code} 的matplotlib图片...")
            print(f"保存股票 {stock_code_key} 的matplotlib图片...")
            
            # 使用matplotlib绘制和保存图片
            plot_df = result['plot_df']

            plt.plot(range(len(plot_df)), plot_df['forecast'], label='Forecast', color='red', linewidth=2, linestyle='--')
            
            # 设置图表样式
            plt.title(f'{stock_code} Stock Price Forecast Comparison', fontsize=16, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.title(f'{stock_code_key} Stock Price Forecast Comparison', fontsize=16, fontweight='bold')
            plt.xlabel('Time Steps (Horizon Length)', fontsize=12)
            plt.ylabel('Price', fontsize=12)
            plt.legend(fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # 格式化日期轴
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5))
            plt.xticks(rotation=45)
            # 设置x轴为简单数列显示
            plt.xticks(range(0, len(plot_df), max(1, len(plot_df)//10)))
            
            # 调整布局
            plt.tight_layout()
            
            # 保存为PNG格式，设置高分辨率
            matplotlib_filename = f"{stock_code}_matplotlib_forecast_plot.png"
            matplotlib_filename = os.path.join(finance_dir, f"forecast-results/{stock_code_key}_matplotlib_forecast_plot_single.png")
            plt.savefig(matplotlib_filename, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            print(f"✅ matplotlib图片已保存: {matplotlib_filename}")
            print(f"✅ 股票 {stock_code_key} matplotlib图片已保存: {matplotlib_filename}")
        
        print("✅ 所有matplotlib图片保存完成")
        print(f"✅ 股票 {stock_code} 处理完成")
        return stock_code, results, figures
        
    except Exception as e:
        error_msg = f"保存图片时出错: {str(e)}"
        error_msg = f"处理股票 {stock_code} 时出错: {str(e)}"
        print(f"❌ {error_msg}")
        return stock_code, None, None

if __name__ == "__main__":
    from timesfm_init import init_timesfm
    from req_res_types import ChunkedPredictionRequest

    test_request = ChunkedPredictionRequest(
        stock_code="000002",
        years=10,
        horizon_len=7,
        end_date="20250630",
        context_len=2048,
        time_step=0,
        stock_type='stock',
        chunk_num=1
    )
    tfm = init_timesfm(horizon_len=test_request.horizon_len, context_len=test_request.context_len)
    asyncio.run(process_single_stock(stock_code=test_request.stock_code, stock_type=test_request.stock_type, time_step=test_request.time_step, years=test_request.years, horizon_len=test_request.horizon_len, tfm=tfm))
