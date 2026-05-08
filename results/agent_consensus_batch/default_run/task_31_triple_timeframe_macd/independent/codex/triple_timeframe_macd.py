"""
三周期MACD共振选股
寻找日线、周线、月线三周期MACD共振的股票
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_macd(df, fast=12, slow=26, signal=9):
    """
    计算MACD指标
    返回DIFF, DEA, MACD柱
    """
    # 计算EMA
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    
    # DIFF = 快线 - 慢线
    diff = ema_fast - ema_slow
    
    # DEA = DIFF的signal周期EMA
    dea = diff.ewm(span=signal, adjust=False).mean()
    
    # MACD柱 = (DIFF - DEA) * 2
    macd = (diff - dea) * 2
    
    return diff, dea, macd

def find_golden_cross(diff, dea, lookback_periods):
    """
    查找最近lookback_periods内的金叉
    返回金叉日期索引，如果没有返回None
    """
    if len(diff) < lookback_periods + 1:
        return None
    
    # 检查最近lookback_periods个周期
    for i in range(len(diff) - 1, max(0, len(diff) - lookback_periods - 1), -1):
        if i > 0:
            # 金叉：前一个周期DIFF < DEA，当前周期DIFF > DEA
            if diff.iloc[i-1] < dea.iloc[i-1] and diff.iloc[i] > dea.iloc[i]:
                return i
    return None

def calculate_ma(series, period=20):
    """计算移动平均线"""
    return series.rolling(window=period).mean()

def get_stock_data_daily(stock_code, end_date, days=90):
    """
    获取日线数据（模拟）
    实际应用中应该调用真实的数据接口
    """
    # 这里使用模拟数据，实际应该调用akshare或tushare等接口
    # 例如: import akshare as ak
    # df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date="20230101", end_date=end_date, adjust="qfq")
    
    # 模拟数据生成
    dates = pd.date_range(end=end_date, periods=days, freq='B')
    np.random.seed(hash(stock_code) % 2**32)
    
    base_price = 10 + np.random.rand() * 20
    prices = base_price + np.cumsum(np.random.randn(days) * 0.5)
    prices = np.maximum(prices, 1)  # 确保价格为正
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.randn(days) * 0.01),
        'high': prices * (1 + np.abs(np.random.randn(days)) * 0.02),
        'low': prices * (1 - np.abs(np.random.randn(days)) * 0.02),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, days)
    })
    
    return df

def get_stock_data_weekly(stock_code, end_date, weeks=52):
    """
    获取周线数据（模拟）
    实际应用中应该调用真实的数据接口
    """
    # 实际应该调用: ak.stock_zh_a_hist(symbol=stock_code, period="weekly", ...)
    dates = pd.date_range(end=end_date, periods=weeks, freq='W-FRI')
    np.random.seed(hash(stock_code + '_w') % 2**32)
    
    base_price = 10 + np.random.rand() * 20
    prices = base_price + np.cumsum(np.random.randn(weeks) * 1.0)
    prices = np.maximum(prices, 1)
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.randn(weeks) * 0.01),
        'high': prices * (1 + np.abs(np.random.randn(weeks)) * 0.03),
        'low': prices * (1 - np.abs(np.random.randn(weeks)) * 0.03),
        'close': prices,
        'volume': np.random.randint(5000000, 50000000, weeks)
    })
    
    return df

def get_stock_data_monthly(stock_code, end_date, months=36):
    """
    获取月线数据（模拟）
    实际应用中应该调用真实的数据接口
    """
    # 实际应该调用: ak.stock_zh_a_hist(symbol=stock_code, period="monthly", ...)
    dates = pd.date_range(end=end_date, periods=months, freq='M')
    np.random.seed(hash(stock_code + '_m') % 2**32)
    
    base_price = 10 + np.random.rand() * 20
    prices = base_price + np.cumsum(np.random.randn(months) * 2.0)
    prices = np.maximum(prices, 1)
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.randn(months) * 0.02),
        'high': prices * (1 + np.abs(np.random.randn(months)) * 0.05),
        'low': prices * (1 - np.abs(np.random.randn(months)) * 0.05),
        'close': prices,
        'volume': np.random.randint(20000000, 200000000, months)
    })
    
    return df

def check_stock_conditions(stock_code, end_date='2024-03-22'):
    """
    检查股票是否满足三周期MACD共振条件
    """
    try:
        # 1. 获取三个时间维度的数据
        daily_df = get_stock_data_daily(stock_code, end_date, days=90)
        weekly_df = get_stock_data_weekly(stock_code, end_date, weeks=52)
        monthly_df = get_stock_data_monthly(stock_code, end_date, months=36)
        
        if len(daily_df) < 50 or len(weekly_df) < 30 or len(monthly_df) < 20:
            return None
        
        # 2. 计算三个周期的MACD（参数12/26/9）
        daily_diff, daily_dea, daily_macd = calculate_macd(daily_df)
        weekly_diff, weekly_dea, weekly_macd = calculate_macd(weekly_df)
        monthly_diff, monthly_dea, monthly_macd = calculate_macd(monthly_df)
        
        # 3. 计算三个周期的20均线
        daily_ma20 = calculate_ma(daily_df['close'], 20)
        weekly_ma20 = calculate_ma(weekly_df['close'], 20)
        monthly_ma20 = calculate_ma(monthly_df['close'], 20)
        
        # 4. 检查条件
        
        # 条件1：日线金叉在最后10个交易日内
        daily_cross_idx = find_golden_cross(daily_diff, daily_dea, 10)
        if daily_cross_idx is None:
            return None
        daily_cross_date = daily_df.iloc[daily_cross_idx]['date'].strftime('%Y-%m-%d')
        
        # 条件2：周线金叉在最后4周内
        weekly_cross_idx = find_golden_cross(weekly_diff, weekly_dea, 4)
        if weekly_cross_idx is None:
            return None
        weekly_cross_date = weekly_df.iloc[weekly_cross_idx]['date'].strftime('%Y-%m-%d')
        
        # 条件3：月线MACD在0轴上方或最近2个月内金叉
        monthly_diff_latest = monthly_diff.iloc[-1]
        monthly_cross_idx = find_golden_cross(monthly_diff, monthly_dea, 2)
        
        if monthly_cross_idx is not None:
            monthly_status = "金叉"
        elif monthly_diff_latest > 0:
            monthly_status = "上方"
        else:
            return None
        
        # 条件4：三个周期的收盘价均在各自的20均线上方
        daily_close_latest = daily_df.iloc[-1]['close']
        daily_ma20_latest = daily_ma20.iloc[-1]
        
        weekly_close_latest = weekly_df.iloc[-1]['close']
        weekly_ma20_latest = weekly_ma20.iloc[-1]
        
        monthly_close_latest = monthly_df.iloc[-1]['close']
        monthly_ma20_latest = monthly_ma20.iloc[-1]
        
        if not (daily_close_latest > daily_ma20_latest and 
                weekly_close_latest > weekly_ma20_latest and 
                monthly_close_latest > monthly_ma20_latest):
            return None
        
        # 所有条件满足，返回结果
        return {
            'stock_code': stock_code,
            'daily_cross_date': daily_cross_date,
            'weekly_cross_date': weekly_cross_date,
            'monthly_status': monthly_status,
            'daily_diff': round(daily_diff.iloc[-1], 2),
            'weekly_diff': round(weekly_diff.iloc[-1], 2),
            'monthly_diff': round(monthly_diff.iloc[-1], 2)
        }
        
    except Exception as e:
        print(f"处理股票 {stock_code} 时出错: {e}")
        return None

def main():
    """主函数"""
    # 模拟股票池（实际应该获取全市场股票列表）
    # 例如使用: import akshare as ak; stock_list = ak.stock_zh_a_spot_em()
    stock_pool = [
        '300001', '300002', '300003', '300010', '300015',
        '300020', '300025', '300030', '300035', '300040',
        '300050', '300060', '300070', '300080', '300090',
        '300100', '300110', '300120', '300130', '300140'
    ]
    
    end_date = '2024-03-22'
    results = []
    
    print(f"开始筛选三周期MACD共振股票，截止日期：{end_date}")
    print(f"检查股票池大小：{len(stock_pool)}")
    
    for stock_code in stock_pool:
        result = check_stock_conditions(stock_code, end_date)
        if result:
            results.append(result)
            print(f"找到符合条件的股票: {stock_code}")
    
    # 写入结果文件
    output_file = 'triple_timeframe_macd.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("无符合条件的股票\n")
            print(f"\n未找到符合条件的股票")
        else:
            # 写入表头
            f.write("股票代码,日线金叉日期,周线金叉日期,月线MACD状态,日线DIFF,周线DIFF,月线DIFF\n")
            
            # 写入数据
            for r in results:
                line = f"{r['stock_code']},{r['daily_cross_date']},{r['weekly_cross_date']},{r['monthly_status']},{r['daily_diff']},{r['weekly_diff']},{r['monthly_diff']}\n"
                f.write(line)
            
            print(f"\n共找到 {len(results)} 只符合条件的股票")
            print(f"结果已写入: {output_file}")

if __name__ == '__main__':
    main()
