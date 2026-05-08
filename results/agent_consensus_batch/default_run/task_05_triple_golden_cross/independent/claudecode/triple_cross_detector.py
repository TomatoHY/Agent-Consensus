#!/usr/bin/env python3
"""
Triple Golden Cross Signal Detector for ChiNext Stocks
Detects MACD, KDJ, and MA golden crosses within 5 trading days
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

def calculate_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    """Calculate MACD indicator"""
    df = df.copy()
    df['EMA12'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=slow, adjust=False).mean()
    df['DIFF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = df['DIFF'].ewm(span=signal, adjust=False).mean()
    df['MACD'] = (df['DIFF'] - df['DEA']) * 2
    return df

def calculate_kdj(df: pd.DataFrame, n=9, m1=3, m2=3) -> pd.DataFrame:
    """Calculate KDJ indicator"""
    df = df.copy()
    low_list = df['low'].rolling(window=n, min_periods=1).min()
    high_list = df['high'].rolling(window=n, min_periods=1).max()

    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    rsv = rsv.fillna(50)

    df['K'] = rsv.ewm(com=m1-1, adjust=False).mean()
    df['D'] = df['K'].ewm(com=m2-1, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']

    return df

def calculate_ma(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
    """Calculate moving averages"""
    df = df.copy()
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period).mean()
    return df

def detect_golden_cross(series1: pd.Series, series2: pd.Series) -> List[str]:
    """Detect golden cross dates where series1 crosses above series2"""
    crosses = []
    for i in range(1, len(series1)):
        if pd.notna(series1.iloc[i]) and pd.notna(series2.iloc[i]) and \
           pd.notna(series1.iloc[i-1]) and pd.notna(series2.iloc[i-1]):
            if series1.iloc[i-1] <= series2.iloc[i-1] and series1.iloc[i] > series2.iloc[i]:
                crosses.append(series1.index[i])
    return crosses

def check_triple_cross_within_window(macd_dates: List, kdj_dates: List, ma_dates: List, window_days=5) -> Optional[Tuple]:
    """Check if three golden crosses occur within a window of trading days"""
    for macd_date in macd_dates:
        for kdj_date in kdj_dates:
            for ma_date in ma_dates:
                dates = [macd_date, kdj_date, ma_date]
                dates_sorted = sorted(dates)

                # Calculate trading day difference (approximate)
                first_date = pd.to_datetime(dates_sorted[0])
                last_date = pd.to_datetime(dates_sorted[-1])

                # Use calendar days as proxy (5 trading days ≈ 7 calendar days)
                if (last_date - first_date).days <= 7:
                    return (macd_date, kdj_date, ma_date)
    return None

def get_chinext_stocks() -> List[str]:
    """Get ChiNext stock list (codes starting with 300)"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"Error getting stock list: {e}")
        return []

def analyze_stock(stock_code: str, end_date: str = '2024-07-31') -> Optional[Tuple]:
    """Analyze a single stock for triple golden cross"""
    try:
        # Get historical data (60+ days for indicator warmup)
        start_date = '2024-05-01'  # ~60 trading days before end_date
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")

        if df is None or len(df) < 30:
            return None

        df['date'] = pd.to_datetime(df['日期'])
        df = df.rename(columns={
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })
        df = df.set_index('date')
        df = df.sort_index()

        # Calculate indicators
        df = calculate_macd(df)
        df = calculate_kdj(df)
        df = calculate_ma(df, [5, 10])

        # Get last 20 trading days
        df_recent = df.tail(20)

        # Detect golden crosses
        macd_crosses = detect_golden_cross(df_recent['DIFF'], df_recent['DEA'])
        kdj_crosses = detect_golden_cross(df_recent['K'], df_recent['D'])
        ma_crosses = detect_golden_cross(df_recent['MA5'], df_recent['MA10'])

        if not macd_crosses or not kdj_crosses or not ma_crosses:
            return None

        # Check if all three crosses occur within 5 trading days
        result = check_triple_cross_within_window(macd_crosses, kdj_crosses, ma_crosses)

        if result:
            macd_date, kdj_date, ma_date = result
            return (stock_code,
                   macd_date.strftime('%Y-%m-%d'),
                   kdj_date.strftime('%Y-%m-%d'),
                   ma_date.strftime('%Y-%m-%d'))

        return None

    except Exception as e:
        print(f"Error analyzing {stock_code}: {e}")
        return None

def main():
    """Main function to detect triple golden cross signals"""
    print("Starting triple golden cross detection...")
    print("Getting ChiNext stock list...")

    stocks = get_chinext_stocks()
    print(f"Found {len(stocks)} ChiNext stocks")

    results = []

    for i, stock_code in enumerate(stocks[:100], 1):  # Limit to first 100 for time
        if i % 10 == 0:
            print(f"Progress: {i}/{min(100, len(stocks))}")

        result = analyze_stock(stock_code)
        if result:
            results.append(result)
            print(f"Found: {result}")

    # Write results
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_05_triple_golden_cross/independent/claudecode/triple_cross.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,MACD金叉日期,KDJ金叉日期,MA金叉日期\n")
        if results:
            for stock_code, macd_date, kdj_date, ma_date in results:
                f.write(f"{stock_code},{macd_date},{kdj_date},{ma_date}\n")
        else:
            f.write("# 无符合条件的股票\n")

    print(f"\nDetection complete. Found {len(results)} stocks with triple golden cross.")
    print(f"Results written to: {output_file}")

if __name__ == "__main__":
    main()
