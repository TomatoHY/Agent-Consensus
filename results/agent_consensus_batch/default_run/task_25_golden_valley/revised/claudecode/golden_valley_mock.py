#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Golden Valley Pattern Detector - Mock Implementation
Demonstrates correct logic for Silver Valley and Golden Valley detection
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_data(code, pattern_type='golden'):
    """
    Generate mock stock data with specific patterns
    pattern_type: 'golden' (has golden valley), 'silver_only', 'none'
    """
    np.random.seed(int(code))
    dates = pd.date_range(start='2024-03-01', end='2024-07-08', freq='B')

    # Generate base price with trend
    base_price = 20 + np.random.randn(len(dates)).cumsum() * 0.3
    base_price = np.maximum(base_price, 10)  # Keep prices positive

    if pattern_type == 'golden':
        # Create a pattern with silver valley around day 40 and golden valley around day 55
        # Add uptrend for silver valley
        base_price[35:45] += np.linspace(0, 3, 10)
        # Add pullback (but not breaking MA20)
        base_price[45:50] += np.linspace(3, 1, 5)
        # Add stronger uptrend for golden valley
        base_price[50:60] += np.linspace(1, 5, 10)

    df = pd.DataFrame({
        'date': dates[:len(base_price)],
        'close': base_price,
        'open': base_price * (1 + np.random.randn(len(base_price)) * 0.01),
        'high': base_price * (1 + np.abs(np.random.randn(len(base_price))) * 0.02),
        'low': base_price * (1 - np.abs(np.random.randn(len(base_price))) * 0.02),
        'volume': np.random.randint(1000000, 10000000, len(base_price))
    })

    return df

def calculate_ma(prices, window):
    """Calculate moving average"""
    return prices.rolling(window=window).mean()

def check_spacing(ma5, ma10, ma20):
    """Check if spacing between MAs is less than 8%"""
    if ma20 == 0:
        return False
    spacing = (ma5 - ma20) / ma20
    return spacing < 0.08

def detect_silver_valley(df, start_idx=0):
    """
    Detect Silver Valley: First occurrence of MA5 > MA10 > MA20
    with spacing < 8%
    Returns: (index, ma10_value, date) or (None, None, None)
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
                return i, curr['ma10'], curr['date']

    return None, None, None

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
            return None, None, None

    # Search for golden valley 10-30 days after silver valley
    for i in range(silver_idx + 10, min(silver_idx + 31, len(df))):
        curr = df.iloc[i]

        # Check if MA5 > MA10 > MA20
        if curr['ma5'] > curr['ma10'] > curr['ma20']:
            # Check if MA10 is higher than silver valley MA10
            if curr['ma10'] > silver_ma10:
                # Check spacing
                if check_spacing(curr['ma5'], curr['ma10'], curr['ma20']):
                    return i, curr['ma10'], curr['date']

    return None, None, None

def analyze_stock(code, pattern_type='golden'):
    """
    Analyze a single stock for Golden Valley pattern
    Returns: dict with results or None
    """
    try:
        # Get mock data
        df = generate_mock_data(code, pattern_type)

        if len(df) < 60:
            return None

        # Calculate moving averages
        df['ma5'] = calculate_ma(df['close'], 5)
        df['ma10'] = calculate_ma(df['close'], 10)
        df['ma20'] = calculate_ma(df['close'], 20)

        # Drop NaN rows
        df = df.dropna()

        if len(df) < 60:
            return None

        # Search in last 60 trading days
        search_start = max(0, len(df) - 60)
        df_search = df.iloc[search_start:].reset_index(drop=True)

        # Detect Silver Valley
        silver_idx, silver_ma10, silver_date = detect_silver_valley(df_search)

        if silver_idx is None:
            return None

        # Detect Golden Valley
        golden_idx, golden_ma10, golden_date = detect_golden_valley(df_search, silver_idx, silver_ma10)

        if golden_idx is None:
            return None

        # Calculate interval (trading days)
        interval = golden_idx - silver_idx

        # Format dates
        silver_date_str = silver_date.strftime('%Y-%m-%d') if hasattr(silver_date, 'strftime') else str(silver_date)[:10]
        golden_date_str = golden_date.strftime('%Y-%m-%d') if hasattr(golden_date, 'strftime') else str(golden_date)[:10]

        return {
            'code': code,
            'silver_date': silver_date_str,
            'golden_date': golden_date_str,
            'interval': interval
        }

    except Exception as e:
        print(f"Error analyzing {code}: {e}")
        return None

def main():
    """Main function to detect Golden Valley patterns"""
    print("Starting Golden Valley detection (Mock Mode)...")
    print("This demonstrates the correct detection logic with simulated data.")

    # Simulate ChiNext stocks with different patterns
    test_stocks = [
        ('300001', 'golden'),
        ('300002', 'none'),
        ('300003', 'golden'),
        ('300005', 'silver_only'),
        ('300008', 'golden'),
        ('300013', 'none'),
        ('300021', 'golden'),
    ]

    results = []

    # Analyze each stock
    for code, pattern_type in test_stocks:
        result = analyze_stock(code, pattern_type)
        if result:
            results.append(result)
            print(f"Found pattern in {code}: Silver={result['silver_date']}, Golden={result['golden_date']}, Interval={result['interval']} days")

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
