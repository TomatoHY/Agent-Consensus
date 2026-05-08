#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Golden Valley (金山谷) Pattern Detector for ChiNext Stocks
Identifies Silver Valley (银山谷) and Golden Valley (金山谷) patterns
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak

def calculate_ma(prices, window):
    """Calculate moving average"""
    return prices.rolling(window=window).mean()

def check_spacing(ma5, ma10, ma20):
    """Check if spacing between MAs is less than 8%"""
    spacing = (ma5 - ma20) / ma20
    return spacing < 0.08

def detect_silver_valley(df, start_idx=0):
    """
    Detect Silver Valley: First occurrence of MA5 > MA10 > MA20
    with spacing < 8%
    Returns: (index, ma10_value) or (None, None)
    """
    for i in range(start_idx + 1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]

        # Check if previous day did NOT satisfy the condition
        prev_satisfied = (prev['ma5'] > prev['ma10'] > prev['ma20'])

        # Check if current day satisfies the condition
        curr_satisfied = (curr['ma5'] > curr['ma10'] > curr['ma20'])

        if not prev_satisfied and curr_satisfied:
            # Check spacing
            if check_spacing(curr['ma5'], curr['ma10'], curr['ma20']):
                return i, curr['ma10']

    return None, None

def detect_golden_valley(df, silver_idx, silver_ma10):
    """
    Detect Golden Valley after Silver Valley
    Requirements:
    - 10-30 trading days after Silver Valley
    - MA5 > MA10 > MA20 again
    - MA10 value higher than Silver Valley MA10
    - Spacing < 8%
    - Price never broke below MA20 (close >= MA20)
    """
    # Check if price broke MA20 after silver valley
    for i in range(silver_idx + 1, len(df)):
        if df.iloc[i]['close'] < df.iloc[i]['ma20']:
            # Price broke below MA20, no valid golden valley possible
            return None, None

    # Search for golden valley 10-30 days after silver valley
    for i in range(silver_idx + 10, min(silver_idx + 31, len(df))):
        curr = df.iloc[i]

        # Check if MA5 > MA10 > MA20
        if curr['ma5'] > curr['ma10'] > curr['ma20']:
            # Check if MA10 is higher than silver valley MA10
            if curr['ma10'] > silver_ma10:
                # Check spacing
                if check_spacing(curr['ma5'], curr['ma10'], curr['ma20']):
                    return i, curr['ma10']

    return None, None

def get_chinext_stocks():
    """Get list of ChiNext stock codes (300XXX)"""
    try:
        # Get ChiNext stock list
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"Error getting ChiNext stocks: {e}")
        # Return a sample list for testing
        return ['300001', '300002', '300003', '300059', '300750']

def analyze_stock(code, end_date='2024-07-08'):
    """
    Analyze a single stock for Golden Valley pattern
    Returns: dict with results or None
    """
    try:
        # Get historical data (120 days for MA calculation + search window)
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date="2024-03-01", end_date=end_date, adjust="qfq")

        if df is None or len(df) < 60:
            return None

        # Rename columns
        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount',
                      'amplitude', 'change_pct', 'change_amount', 'turnover']

        # Calculate moving averages
        df['ma5'] = calculate_ma(df['close'], 5)
        df['ma10'] = calculate_ma(df['close'], 10)
        df['ma20'] = calculate_ma(df['close'], 20)

        # Drop NaN rows
        df = df.dropna()

        if len(df) < 60:
            return None

        # Search in last 60 trading days
        search_start = len(df) - 60
        df_search = df.iloc[search_start:].reset_index(drop=True)

        # Detect Silver Valley
        silver_idx, silver_ma10 = detect_silver_valley(df_search)

        if silver_idx is None:
            return None

        # Detect Golden Valley
        golden_idx, golden_ma10 = detect_golden_valley(df_search, silver_idx, silver_ma10)

        if golden_idx is None:
            return None

        # Calculate interval (trading days)
        interval = golden_idx - silver_idx

        return {
            'code': code,
            'silver_date': df_search.iloc[silver_idx]['date'],
            'golden_date': df_search.iloc[golden_idx]['date'],
            'interval': interval
        }

    except Exception as e:
        print(f"Error analyzing {code}: {e}")
        return None

def main():
    """Main function to detect Golden Valley patterns"""
    print("Starting Golden Valley detection...")

    # Get ChiNext stocks
    chinext_codes = get_chinext_stocks()
    print(f"Found {len(chinext_codes)} ChiNext stocks")

    results = []

    # Analyze each stock
    for i, code in enumerate(chinext_codes):
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1}/{len(chinext_codes)} stocks...")

        result = analyze_stock(code)
        if result:
            results.append(result)
            print(f"Found pattern in {code}: {result}")

    # Write results to file
    output_file = 'golden_valley.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("无符合条件的股票\n")
        else:
            f.write("股票代码,银山谷日期,金山谷日期,间隔天数\n")
            for r in results:
                f.write(f"{r['code']},{r['silver_date']},{r['golden_date']},{r['interval']}\n")

    print(f"\nDetection complete. Found {len(results)} stocks with Golden Valley pattern.")
    print(f"Results written to {output_file}")

    return results

if __name__ == "__main__":
    main()
