import exchange_calendars as xcals
import pandas as pd
from datetime import datetime, timedelta


def get_trading_days(start_date, end_date, need_: bool = True):
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
        if start_date.year < 2005:
            start_date = pd.to_datetime('20050101')
            if need_:
                return [start_date.date(), end_date.date()]
            else:
                return [start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d')]
        # 获取交易日
        trading_days = china_calendar.sessions_in_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

        # 转换为日期列表
        if need_:
            trading_dates = [date.date() for date in trading_days]
        else:
            trading_dates = [date.strftime('%Y%m%d') for date in trading_days]
        
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


def get_previous_trading_days(reference_date=None, days=1):
    """
    根据指定天数推算前n天的交易日期
    
    Args:
        reference_date: 参考日期 (datetime, str, 或 None表示今天)
        days: 需要获取的前n天交易日数量
    
    Returns:
        list: 前n天的交易日期列表，按时间倒序排列（最近的在前）
    """
    try:
        # 处理参考日期
        if reference_date is None:
            reference_date = datetime.now()
        elif isinstance(reference_date, str):
            reference_date = pd.to_datetime(reference_date)
        
        # 获取中国股市日历
        china_calendar = xcals.get_calendar('XSHG')  # 上海证券交易所
        
        # 为了确保能获取到足够的交易日，我们向前推算更多的自然日
        # 通常交易日约占自然日的70%，所以我们推算 days * 2 的自然日应该足够
        lookback_days = max(days * 2, 30)  # 至少推算30天
        start_date = reference_date - timedelta(days=lookback_days)
        
        # 获取这个时间段内的所有交易日
        trading_days = china_calendar.sessions_in_range(
            start_date.strftime('%Y-%m-%d'),
            reference_date.strftime('%Y-%m-%d')
        )
        
        # 转换为日期列表并按时间倒序排列
        trading_dates = [date.date() for date in trading_days]
        # trading_dates.sort(reverse=True)  # 最近的日期在前
        
        # 过滤掉参考日期当天（如果它是交易日）
        reference_date_only = reference_date.date()
        if trading_dates and trading_dates[0] == reference_date_only:
            trading_dates = trading_dates[1:]
        
        # 返回前n天的交易日
        result = trading_dates[:days]
        
        print(f"参考日期: {reference_date_only}")
        print(f"请求前 {days} 个交易日")
        print(f"找到的交易日: {result[0]}")
        
        return result[0]
        
    except Exception as e:
        print(f"获取前n天交易日失败: {e}")
        print("回退到简单的工作日计算")
        
        # 回退方案：简单的工作日计算
        if reference_date is None:
            reference_date = datetime.now()
        elif isinstance(reference_date, str):
            reference_date = pd.to_datetime(reference_date)
        
        result = []
        current_date = reference_date.date()
        days_found = 0
        days_back = 1
        
        while days_found < days and days_back <= 365:  # 最多向前查找一年
            check_date = current_date - timedelta(days=days_back)
            # 简单判断：周一到周五为工作日
            if check_date.weekday() < 5:
                result.append(check_date)
                days_found += 1
            days_back += 1
        
        print(f"回退方案找到的工作日: {result}")
        return result


def get_trading_date_range(start_date, days):
    """
    从指定开始日期获取连续的n个交易日
    
    Args:
        start_date: 开始日期 (datetime, str)
        days: 需要获取的交易日数量
    
    Returns:
        list: 连续的n个交易日期列表，按时间正序排列
    """
    try:
        # 处理开始日期
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        
        # 获取中国股市日历
        china_calendar = xcals.get_calendar('XSHG')  # 上海证券交易所
        
        # 为了确保能获取到足够的交易日，我们向后推算更多的自然日
        lookforward_days = max(days * 2, 60)  # 至少推算60天
        end_date = start_date + timedelta(days=lookforward_days)
        
        # 获取这个时间段内的所有交易日
        trading_days = china_calendar.sessions_in_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # 转换为日期列表
        trading_dates = [date.date() for date in trading_days]
        
        # 返回前n天的交易日
        result = trading_dates[:days]
        
        print(f"开始日期: {start_date.date()}")
        print(f"请求连续 {days} 个交易日")
        print(f"找到的交易日范围: {result[0] if result else 'None'} 到 {result[-1] if result else 'None'}")
        
        return result
        
    except Exception as e:
        print(f"获取连续交易日失败: {e}")
        print("回退到简单的工作日计算")
        
        # 回退方案：简单的工作日计算
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        
        result = []
        current_date = start_date.date()
        days_found = 0
        days_forward = 0
        
        while days_found < days and days_forward <= 365:  # 最多向后查找一年
            check_date = current_date + timedelta(days=days_forward)
            # 简单判断：周一到周五为工作日
            if check_date.weekday() < 5:
                result.append(check_date)
                days_found += 1
            days_forward += 1
        
        print(f"回退方案找到的工作日: {result}")
        return result