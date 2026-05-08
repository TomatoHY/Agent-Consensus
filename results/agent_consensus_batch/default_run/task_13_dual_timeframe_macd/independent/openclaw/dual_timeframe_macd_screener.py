#!/usr/bin/env python3
"""
Dual-timeframe MACD resonance stock screener for ChiNext (创业板)
Screens stocks with both daily and weekly MACD golden crosses
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def calculate_macd(close_prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    ema_fast = close_prices.ewm(span=fast, adjust=False).mean()
    ema_slow = close_prices.ewm(span=slow, adjust=False).mean()
    diff = ema_fast - ema_slow
    dea = diff.ewm(span=signal, adjust=False).mean()
    macd = (diff - dea) * 2
    return diff, dea, macd

def find_golden_cross(diff, dea, lookback_days):
    """Find MACD golden cross (DIFF crosses above DEA) within lookback period"""
    if len(diff) < lookback_days + 1:
        return None, None
    
    recent_diff = diff.iloc[-lookback_days-1:]
    recent_dea = dea.iloc[-lookback_days-1:]
    
    for i in range(1, len(recent_diff)):
        if recent_diff.iloc[i-1] <= recent_dea.iloc[i-1] and recent_diff.iloc[i] > recent_dea.iloc[i]:
            return recent_diff.index[i], True
    
    return None, False

def check_ma5_slope_positive(close_prices):
    """Check if 5-day MA slope is positive (continuously increasing)"""
    if len(close_prices) < 5:
        return False
    
    ma5_values = close_prices.rolling(window=5).mean().iloc[-5:]
    
    if len(ma5_values) < 5 or ma5_values.isna().any():
        return False
    
    # Check if MA5 values are continuously increasing
    for i in range(1, len(ma5_values)):
        if ma5_values.iloc[i] <= ma5_values.iloc[i-1]:
            return False
    
    return True

def calculate_volume_ratio(volumes):
    """Calculate volume ratio: avg(last 5 days) / avg(last 20 days)"""
    if len(volumes) < 20:
        return 0.0
    
    avg_5 = volumes.iloc[-5:].mean()
    avg_20 = volumes.iloc[-20:].mean()
    
    if avg_20 == 0:
        return 0.0
    
    return avg_5 / avg_20

def get_chinext_stocks():
    """Get ChiNext (创业板) stock list"""
    try:
        # Get ChiNext stock list (stocks starting with 300)
        stock_info = ak.stock_info_a_code_name()
        chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]
        return chinext_stocks['code'].tolist()
    except Exception as e:
        print(f"Error getting ChiNext stocks: {e}")
        return []

def get_daily_kline(stock_code, start_date, end_date):
    """Get daily K-line data"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date, adjust="qfq")
        if df is not None and not df.empty:
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期')
            return df
    except Exception as e:
        pass
    return None

def get_weekly_kline(stock_code, start_date, end_date):
    """Get weekly K-line data"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="weekly", 
                                start_date=start_date, end_date=end_date, adjust="qfq")
        if df is not None and not df.empty:
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期')
            return df
    except Exception as e:
        pass
    return None

def screen_stock(stock_code, end_date_str='2024-05-15'):
    """Screen a single stock for dual-timeframe MACD resonance"""
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    # Calculate start dates for daily (90 days) and weekly (26 weeks = ~182 days)
    daily_start = (end_date - timedelta(days=120)).strftime('%Y%m%d')
    weekly_start = (end_date - timedelta(days=200)).strftime('%Y%m%d')
    end_date_fmt = end_date.strftime('%Y%m%d')
    
    # Get daily K-line data
    daily_df = get_daily_kline(stock_code, daily_start, end_date_fmt)
    if daily_df is None or len(daily_df) < 60:
        return None
    
    # Get weekly K-line data
    weekly_df = get_weekly_kline(stock_code, weekly_start, end_date_fmt)
    if weekly_df is None or len(weekly_df) < 26:
        return None
    
    # Filter data up to end_date
    daily_df = daily_df[daily_df.index <= end_date]
    weekly_df = weekly_df[weekly_df.index <= end_date]
    
    if len(daily_df) < 30 or len(weekly_df) < 10:
        return None
    
    # Calculate daily MACD
    daily_close = daily_df['收盘']
    daily_diff, daily_dea, _ = calculate_macd(daily_close)
    
    # Calculate weekly MACD
    weekly_close = weekly_df['收盘']
    weekly_diff, weekly_dea, _ = calculate_macd(weekly_close)
    
    # Check daily MACD golden cross (last 10 trading days)
    daily_cross_date, daily_has_cross = find_golden_cross(daily_diff, daily_dea, 10)
    if not daily_has_cross:
        return None
    
    # Check weekly MACD golden cross (last 4 weeks)
    weekly_cross_date, weekly_has_cross = find_golden_cross(weekly_diff, weekly_dea, 4)
    if not weekly_has_cross:
        return None
    
    # Check 5-day MA slope is positive
    if not check_ma5_slope_positive(daily_close):
        return None
    
    # Calculate volume ratio
    volumes = daily_df['成交量']
    vol_ratio = calculate_volume_ratio(volumes)
    if vol_ratio < 1.2:
        return None
    
    # Calculate MA5 slope (for output)
    ma5_values = daily_close.rolling(window=5).mean().iloc[-5:]
    slope = (ma5_values.iloc[-1] - ma5_values.iloc[0]) / 4  # Simple slope
    
    return {
        'code': stock_code,
        'daily_cross_date': daily_cross_date.strftime('%Y-%m-%d'),
        'weekly_cross_date': weekly_cross_date.strftime('%Y-%m-%d'),
        'ma5_slope': round(slope, 4),
        'volume_ratio': round(vol_ratio, 2)
    }

def main():
    print("Starting dual-timeframe MACD resonance screening...")
    print("Target date: 2024-05-15")
    print("=" * 60)
    
    # Get ChiNext stock list
    chinext_stocks = get_chinext_stocks()
    print(f"Found {len(chinext_stocks)} ChiNext stocks")
    
    results = []
    
    # Screen each stock
    for i, stock_code in enumerate(chinext_stocks, 1):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(chinext_stocks)} stocks screened...")
        
        try:
            result = screen_stock(stock_code)
            if result:
                results.append(result)
                print(f"✓ Found: {stock_code}")
        except Exception as e:
            pass
    
    print("=" * 60)
    print(f"Screening complete. Found {len(results)} stocks meeting all criteria.")
    
    # Write results to file
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_13_dual_timeframe_macd/independent/openclaw/dual_timeframe_macd.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,日线金叉日期,周线金叉日期,5日均线斜率,量比(近5日/近20日)\n')
        
        if results:
            for r in results:
                f.write(f"{r['code']},{r['daily_cross_date']},{r['weekly_cross_date']},{r['ma5_slope']},{r['volume_ratio']}\n")
        else:
            f.write('无符合条件的股票\n')
    
    print(f"Results written to: dual_timeframe_macd.txt")
    
    return results

if __name__ == '__main__':
    results = main()
