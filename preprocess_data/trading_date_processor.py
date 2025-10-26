import exchange_calendars as xcals


def get_trading_days(start_date, end_date):
    """
    使用exchange_calendars获取中国股市的交易日
    
    Args:
        start_date: 开始日期 (datetime or str)
        end_date: 结束日期 (datetime or str)
    
    Returns:
        list: 交易日列表
    """
    try:
        # 获取中国股市日历
        china_calendar = xcals.get_calendar('XSHG')  # 上海证券交易所
        
        # 确保日期格式正确
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        
        # 获取交易日
        trading_days = china_calendar.sessions_in_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # 转换为日期列表
        trading_dates = [date.date() for date in trading_days]
        
        print(f"交易日历: {start_date.date()} 到 {end_date.date()}")
        print(f"总交易日数量: {len(trading_dates)}")
        
        return trading_dates
        
    except Exception as e:
        print(f"获取交易日历失败: {e}")
        print("回退到简单的工作日过滤")
        
        # 回退方案：简单的工作日过滤
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        weekdays = [d.date() for d in date_range if d.weekday() < 5]  # 周一到周五
        return weekdays


def filter_trading_days_data(df, date_column='ds'):
    """
    使用交易日历过滤数据，只保留真正的交易日
    
    Args:
        df: 包含日期列的DataFrame
        date_column: 日期列名
    
    Returns:
        DataFrame: 过滤后的数据
    """
    if df.empty:
        return df
    
    # 确保日期列是datetime格式
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    
    # 获取数据的日期范围
    start_date = df[date_column].min()
    end_date = df[date_column].max()
    
    # 获取交易日
    trading_days = get_trading_days(start_date, end_date)
    
    # 过滤数据，只保留交易日
    df_filtered = df[df[date_column].dt.date.isin(trading_days)]
    
    print(f"原始数据: {len(df)} 行")
    print(f"过滤后数据: {len(df_filtered)} 行")
    print(f"过滤掉的非交易日: {len(df) - len(df_filtered)} 行")
    
    return df_filtered