#!/usr/bin/env python3
"""Test different akshare methods to get ChiNext data"""

import akshare as ak
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

print("Testing different methods to get ChiNext stock data...\n")

# Method 1: Try getting real-time quotes
print("Method 1: Getting real-time ChiNext quotes...")
try:
    df = ak.stock_zh_a_spot_em()
    chinext = df[df['代码'].str.startswith('300')]
    print(f"Found {len(chinext)} ChiNext stocks")
    print("Sample codes:", chinext['代码'].head(10).tolist())
    sample_code = chinext['代码'].iloc[0] if len(chinext) > 0 else None
except Exception as e:
    print(f"Error: {e}")
    sample_code = None

# Method 2: Try getting historical data with different symbol format
if sample_code:
    print(f"\nMethod 2: Testing historical data for {sample_code}...")
    try:
        # Try without prefix
        df = ak.stock_zh_a_hist(symbol=sample_code, period="daily",
                                 start_date="20240201", end_date="20240308", adjust="qfq")
        print(f"Success! Got {len(df)} days of data")
        print(df.head())
    except Exception as e:
        print(f"Error: {e}")

# Method 3: Try a known active stock
print("\nMethod 3: Testing with known active stocks...")
test_codes = ['300750', '300059', '300999', '300896', '300124']
for code in test_codes:
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                 start_date="20240201", end_date="20240308", adjust="qfq")
        if df is not None and len(df) > 0:
            print(f"{code}: ✓ {len(df)} days")
            break
    except Exception as e:
        print(f"{code}: ✗ {str(e)[:50]}")
