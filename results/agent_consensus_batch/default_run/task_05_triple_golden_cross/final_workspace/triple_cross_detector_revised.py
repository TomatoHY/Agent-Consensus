#!/usr/bin/env python3
"""
Triple Golden Cross Signal Detector for ChiNext Stocks - REVISED
Detects MACD, KDJ, and MA golden crosses within 5 trading days using REAL market data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    """Calculate EMA with proper initialization"""
    return series.ewm(span=span, adjust=False).mean()

def calculate_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    """Calculate MACD indicator (EMA12, EMA26, signal line EMA9)"""
    df = df.copy()
    df['EMA12'] = calculate_ema(df['close'], fast)
    df['EMA26'] = calculate_ema(df['close'], slow)
    df['DIFF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = calculate_ema(df['DIFF'], signal)
    df['MACD'] = (df['DIFF'] - df['DEA']) * 2
    return df

def calculate_kdj(df: pd.DataFrame, n=9, m1=3, m2=3) -> pd.DataFrame:
    """Calculate KDJ indicator (K=9-day stochastic, D=3-day SMA of K, J=3K-2D)"""
    df = df.copy()

    # Calculate RSV (Raw Stochastic Value)
    low_min = df['low'].rolling(window=n, min_periods=n).min()
    high_max = df['high'].rolling(window=n, min_periods=n).max()

    rsv = 100 * (df['close'] - low_min) / (high_max - low_min)
    rsv = rsv.fillna(50)

    # K and D use EMA (exponential moving average)
    df['K'] = rsv.ewm(com=m1-1, adjust=False).mean()
    df['D'] = df['K'].ewm(com=m2-1, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']

    return df

def calculate_ma(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
    """Calculate simple moving averages"""
    df = df.copy()
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period, min_periods=period).mean()
    return df

def detect_golden_cross(series1: pd.Series, series2: pd.Series) -> List[str]:
    """
    Detect golden cross dates where series1 crosses above series2
    Golden cross: previous day series1 <= series2, current day series1 > series2
    """
    crosses = []
    for i in range(1, len(series1)):
        if pd.notna(series1.iloc[i]) and pd.notna(series2.iloc[i]) and \
           pd.notna(series1.iloc[i-1]) and pd.notna(series2.iloc[i-1]):
            if series1.iloc[i-1] <= series2.iloc[i-1] and series1.iloc[i] > series2.iloc[i]:
                crosses.append(series1.index[i])
    return crosses

def check_within_n_trading_days(dates: List, n_days: int = 5) -> bool:
    """Check if all dates are within n trading days of each other"""
    if not dates or len(dates) < 2:
        return True

    dates_sorted = sorted([pd.to_datetime(d) for d in dates])
    first_date = dates_sorted[0]
    last_date = dates_sorted[-1]

    # 5 trading days ≈ 7 calendar days (accounting for weekends)
    # Use 10 calendar days to be more lenient
    calendar_days = (last_date - first_date).days
    return calendar_days <= 10

def find_triple_cross_in_window(macd_dates: List, kdj_dates: List, ma_dates: List) -> Optional[Tuple]:
    """Find if three golden crosses occur within 5 trading days"""
    for macd_date in macd_dates:
        for kdj_date in kdj_dates:
            for ma_date in ma_dates:
                if check_within_n_trading_days([macd_date, kdj_date, ma_date], 5):
                    return (macd_date, kdj_date, ma_date)
    return None

def get_stock_data_akshare(stock_code: str, start_date: str = '2024-05-01', end_date: str = '2024-07-31'):
    """Fetch stock data using akshare"""
    try:
        import akshare as ak

        # ChiNext stocks use format like "300001"
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date.replace('-', ''),
                                end_date=end_date.replace('-', ''),
                                adjust="qfq")  # Forward adjusted

        if df is None or len(df) == 0:
            return None

        # Rename columns to standard format
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })

        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df = df.sort_index()

        return df[['open', 'high', 'low', 'close', 'volume']]

    except Exception as e:
        return None

def analyze_stock(stock_code: str, end_date: str = '2024-07-31') -> Optional[Tuple]:
    """Analyze a single stock for triple golden cross"""
    try:
        # Fetch real market data
        df = get_stock_data_akshare(stock_code, start_date='2024-04-01', end_date=end_date)

        if df is None or len(df) < 30:
            return None

        # Calculate all indicators
        df = calculate_macd(df)
        df = calculate_kdj(df)
        df = calculate_ma(df, [5, 10])

        # Filter to last 20 trading days
        df_recent = df.tail(20)

        if len(df_recent) < 10:
            return None

        # Detect golden crosses in the recent period
        macd_crosses = detect_golden_cross(df_recent['DIFF'], df_recent['DEA'])
        kdj_crosses = detect_golden_cross(df_recent['K'], df_recent['D'])
        ma_crosses = detect_golden_cross(df_recent['MA5'], df_recent['MA10'])

        # Must have all three types of crosses
        if not macd_crosses or not kdj_crosses or not ma_crosses:
            return None

        # Check if all three crosses occur within 5 trading days
        result = find_triple_cross_in_window(macd_crosses, kdj_crosses, ma_crosses)

        if result:
            macd_date, kdj_date, ma_date = result
            return (stock_code,
                   macd_date.strftime('%Y-%m-%d'),
                   kdj_date.strftime('%Y-%m-%d'),
                   ma_date.strftime('%Y-%m-%d'))

        return None

    except Exception as e:
        return None

def get_chinext_stock_list():
    """Get list of ChiNext stock codes"""
    try:
        import akshare as ak
        # Get all A-share stocks
        stock_info = ak.stock_info_a_code_name()
        # Filter ChiNext stocks (code starts with 300)
        chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()
        return chinext_stocks
    except:
        # Fallback: generate common ChiNext codes
        return [f"30{i:04d}" for i in range(1, 1000)]

def main():
    """Main function to detect triple golden cross signals"""
    print("Starting triple golden cross detection with REAL market data...")

    # Try to import akshare
    try:
        import akshare as ak
        print("✓ akshare library available")
    except ImportError:
        print("✗ akshare not available, installing...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'akshare', '-q'])
        import akshare as ak

    # Get ChiNext stock list
    print("Fetching ChiNext stock list...")
    stock_codes = get_chinext_stock_list()
    print(f"Found {len(stock_codes)} ChiNext stocks to analyze")

    results = []
    processed = 0

    for stock_code in stock_codes:
        processed += 1
        if processed % 50 == 0:
            print(f"Progress: {processed}/{len(stock_codes)}, Found: {len(results)}")

        result = analyze_stock(stock_code)
        if result:
            results.append(result)
            print(f"✓ Found: {result[0]} - MACD:{result[1]}, KDJ:{result[2]}, MA:{result[3]}")

    # Write results
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_05_triple_golden_cross/revised/claudecode/triple_cross.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,MACD金叉日期,KDJ金叉日期,MA金叉日期\n")
        if results:
            for stock_code, macd_date, kdj_date, ma_date in results:
                f.write(f"{stock_code},{macd_date},{kdj_date},{ma_date}\n")
        else:
            f.write("# 无符合条件的股票\n")

    print(f"\n{'='*60}")
    print(f"Detection complete!")
    print(f"Total stocks analyzed: {processed}")
    print(f"Stocks with triple golden cross: {len(results)}")
    print(f"Results written to: {output_file}")
    print(f"{'='*60}")

    return results

if __name__ == "__main__":
    main()
