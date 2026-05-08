#!/usr/bin/env python3
"""
Multi-indicator stock filter for ChiNext (GEM) stocks
Analyzes stocks from 2026-03-04 to 2026-03-31 (20 trading days)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak

def calculate_ema(data, period):
    """Calculate Exponential Moving Average"""
    return data.ewm(span=period, adjust=False).mean()

def calculate_macd(close_prices):
    """
    Calculate MACD indicator
    Returns: (MACD line/DIF, Signal line/DEA, Histogram)
    """
    ema12 = calculate_ema(close_prices, 12)
    ema26 = calculate_ema(close_prices, 26)
    dif = ema12 - ema26
    dea = calculate_ema(dif, 9)
    macd = (dif - dea) * 2
    return dif, dea, macd

def calculate_rsi(close_prices, period=14):
    """Calculate RSI indicator"""
    delta = close_prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def check_macd_golden_cross(dif, dea):
    """Check if MACD golden cross occurred (DIF crosses above DEA)"""
    for i in range(1, len(dif)):
        if dif.iloc[i-1] <= dea.iloc[i-1] and dif.iloc[i] > dea.iloc[i]:
            return True
    return False

def check_rsi_rebound(rsi):
    """
    Check if RSI rebounded from oversold (<30) to above 50
    Logic: RSI drops below 30, then crosses above 50
    """
    in_cycle = False
    cycle_start = -1

    for i in range(len(rsi)):
        if pd.isna(rsi.iloc[i]):
            continue

        # Start new cycle when RSI drops below 30
        if rsi.iloc[i] < 30:
            in_cycle = True
            cycle_start = i
            continue

        # If in cycle and RSI crosses above 50
        if in_cycle and i > 0:
            if rsi.iloc[i-1] <= 50 and rsi.iloc[i] > 50:
                return True

    return False

def check_volume_spike(volume, threshold=2, min_days=2):
    """
    Check if volume exceeded 5-day average by threshold at least min_days times
    """
    ma5_volume = volume.rolling(window=5).mean()
    spike_count = 0

    for i in range(5, len(volume)):
        if volume.iloc[i] > ma5_volume.iloc[i-1] * threshold:
            spike_count += 1

    return spike_count >= min_days

def check_ma_cross(close_prices):
    """Check if MA5 crosses above MA8"""
    ma5 = close_prices.rolling(window=5).mean()
    ma8 = close_prices.rolling(window=8).mean()

    for i in range(1, len(ma5)):
        if not pd.isna(ma5.iloc[i]) and not pd.isna(ma8.iloc[i]):
            if ma5.iloc[i-1] <= ma8.iloc[i-1] and ma5.iloc[i] > ma8.iloc[i]:
                return True
    return False

def get_chinext_stocks():
    """Get list of ChiNext stocks (starting with 300)"""
    try:
        # Get all A-share stocks
        stock_list = ak.stock_info_a_code_name()
        # Filter for ChiNext (300xxx)
        chinext = stock_list[stock_list['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"Error getting stock list: {e}")
        return []

def get_stock_data(stock_code, start_date, end_date):
    """Get historical kline data for a stock"""
    try:
        # Add buffer days for indicator calculation
        buffer_start = (datetime.strptime(start_date, '%Y%m%d') - timedelta(days=60)).strftime('%Y%m%d')

        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=buffer_start, end_date=end_date, adjust="qfq")

        if df is None or len(df) == 0:
            return None

        # Rename columns to English
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount'
        })

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        return df
    except Exception as e:
        print(f"Error getting data for {stock_code}: {e}")
        return None

def analyze_stock(stock_code, start_date, end_date):
    """Analyze a single stock against all criteria"""
    df = get_stock_data(stock_code, start_date, end_date)

    if df is None or len(df) < 30:
        return False

    # Filter to analysis window
    analysis_start = datetime.strptime(start_date, '%Y%m%d')
    df_window = df[df['date'] >= analysis_start].copy()

    if len(df_window) < 15:
        return False

    # Calculate indicators on full dataset
    close = df['close']
    volume = df['volume']

    # MACD
    dif, dea, macd_hist = calculate_macd(close)
    df['dif'] = dif
    df['dea'] = dea

    # RSI
    rsi = calculate_rsi(close, 14)
    df['rsi'] = rsi

    # MA5 and MA8
    df['ma5'] = close.rolling(window=5).mean()
    df['ma8'] = close.rolling(window=8).mean()

    # Volume MA5
    df['volume_ma5'] = volume.rolling(window=5).mean()

    # Filter to analysis window for checks
    df_check = df[df['date'] >= analysis_start].reset_index(drop=True)

    # Check all conditions
    # 1. MACD golden cross
    macd_cross = check_macd_golden_cross(df_check['dif'], df_check['dea'])

    # 2. RSI rebound from oversold
    rsi_rebound = check_rsi_rebound(df_check['rsi'])

    # 3. Volume spike (at least 2 days > 2x MA5)
    volume_spike = check_volume_spike(df_check['volume'])

    # 4. MA5 crosses above MA8
    ma_cross = check_ma_cross(df_check['close'])

    if macd_cross and rsi_rebound and volume_spike and ma_cross:
        print(f"✓ {stock_code}: All conditions met")
        return True

    return False

def main():
    """Main execution function"""
    print("Starting ChiNext stock filter analysis...")
    print("Analysis period: 2026-03-04 to 2026-03-31")

    start_date = "20260304"
    end_date = "20260331"

    # Get ChiNext stock list
    print("\nFetching ChiNext stock list...")
    stock_list = get_chinext_stocks()
    print(f"Found {len(stock_list)} ChiNext stocks")

    if len(stock_list) == 0:
        print("No stocks found. Exiting.")
        return

    # Analyze each stock
    qualified_stocks = []

    print("\nAnalyzing stocks...")
    for i, stock_code in enumerate(stock_list):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(stock_list)}")

        try:
            if analyze_stock(stock_code, start_date, end_date):
                qualified_stocks.append(stock_code)

                # Limit to 10 stocks
                if len(qualified_stocks) >= 10:
                    break
        except Exception as e:
            print(f"Error analyzing {stock_code}: {e}")
            continue

    print(f"\nFound {len(qualified_stocks)} qualified stocks")

    # Write results
    result_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_01_macd_rsi_filter/independent/claudecode/result.txt"

    with open(result_path, 'w') as f:
        for stock in qualified_stocks[:10]:
            f.write(f"{stock}\n")

    print(f"\nResults written to result.txt")
    print(f"Qualified stocks: {qualified_stocks[:10]}")

if __name__ == "__main__":
    main()
