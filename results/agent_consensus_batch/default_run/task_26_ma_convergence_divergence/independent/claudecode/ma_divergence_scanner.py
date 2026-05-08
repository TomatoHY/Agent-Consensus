#!/usr/bin/env python3
"""
MA Convergence-Divergence Pattern Scanner
Finds stocks with MA convergence followed by upward divergence
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak
from typing import List, Tuple, Optional

def calculate_ma(prices: pd.Series, period: int) -> pd.Series:
    """Calculate moving average"""
    return prices.rolling(window=period, min_periods=period).mean()

def check_convergence(ma5: float, ma10: float, ma20: float, ma30: float) -> bool:
    """
    Check if 4 MAs are converged (max distance < 3%)
    Max distance = (max_ma - min_ma) / min_ma
    """
    mas = [ma5, ma10, ma20, ma30]
    if any(pd.isna(x) or x <= 0 for x in mas):
        return False

    max_ma = max(mas)
    min_ma = min(mas)
    distance = (max_ma - min_ma) / min_ma
    return distance < 0.03

def check_divergence(ma5: float, ma10: float, ma20: float, ma30: float) -> bool:
    """
    Check if MAs are diverged upward: 5 > 10 > 20 > 30
    And adjacent gaps > 2%
    """
    if any(pd.isna(x) or x <= 0 for x in [ma5, ma10, ma20, ma30]):
        return False

    # Check order
    if not (ma5 > ma10 > ma20 > ma30):
        return False

    # Check adjacent gaps > 2%
    gap1 = (ma5 - ma10) / ma10
    gap2 = (ma10 - ma20) / ma20
    gap3 = (ma20 - ma30) / ma30

    return all(gap > 0.02 for gap in [gap1, gap2, gap3])

def find_convergence_period(df: pd.DataFrame, end_date: str) -> Optional[Tuple[int, int]]:
    """
    Find convergence period: at least 5 consecutive days with MA convergence
    within 20 days before end_date
    Returns (start_idx, end_idx) or None
    """
    end_idx = df[df['日期'] <= end_date].index[-1] if len(df[df['日期'] <= end_date]) > 0 else None
    if end_idx is None:
        return None

    # Look back 20 days
    start_search_idx = max(0, end_idx - 19)

    # Find consecutive convergence days
    convergence_days = []
    for i in range(start_search_idx, end_idx + 1):
        if check_convergence(df.loc[i, 'MA5'], df.loc[i, 'MA10'],
                            df.loc[i, 'MA20'], df.loc[i, 'MA30']):
            convergence_days.append(i)
        else:
            convergence_days = []  # Reset if not consecutive

        if len(convergence_days) >= 5:
            return (convergence_days[0], convergence_days[-1])

    return None

def find_divergence_start(df: pd.DataFrame, convergence_end_idx: int) -> Optional[int]:
    """
    Find divergence start within 5 days after convergence ends
    Returns index or None
    """
    for i in range(convergence_end_idx + 1, min(convergence_end_idx + 6, len(df))):
        if check_divergence(df.loc[i, 'MA5'], df.loc[i, 'MA10'],
                           df.loc[i, 'MA20'], df.loc[i, 'MA30']):
            return i
    return None

def check_volume_condition(df: pd.DataFrame, conv_start: int, conv_end: int,
                          div_start: int) -> bool:
    """
    Check if average volume during divergence > 1.5x average volume during convergence
    Divergence period is 5 days starting from div_start
    """
    div_end = min(div_start + 4, len(df) - 1)

    conv_avg_vol = df.loc[conv_start:conv_end, '成交量'].mean()
    div_avg_vol = df.loc[div_start:div_end, '成交量'].mean()

    if pd.isna(conv_avg_vol) or pd.isna(div_avg_vol) or conv_avg_vol == 0:
        return False

    return div_avg_vol > conv_avg_vol * 1.5

def calculate_return_after_divergence(df: pd.DataFrame, div_start: int) -> float:
    """
    Calculate 5-day return after divergence starts
    """
    div_end = min(div_start + 5, len(df) - 1)
    if div_end <= div_start:
        return 0.0

    start_price = df.loc[div_start, '收盘']
    end_price = df.loc[div_end, '收盘']

    if pd.isna(start_price) or pd.isna(end_price) or start_price == 0:
        return 0.0

    return ((end_price - start_price) / start_price) * 100

def scan_stock(stock_code: str, end_date: str = '2024-08-08') -> Optional[dict]:
    """
    Scan a single stock for MA convergence-divergence pattern
    """
    try:
        # Get stock data (60 days before end_date to ensure enough data for MA30)
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=90)
        start_date = start_dt.strftime('%Y%m%d')
        end_date_fmt = end_dt.strftime('%Y%m%d')

        # Fetch data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_date, end_date=end_date_fmt, adjust="qfq")

        if df is None or len(df) < 40:
            return None

        # Calculate MAs
        df['MA5'] = calculate_ma(df['收盘'], 5)
        df['MA10'] = calculate_ma(df['收盘'], 10)
        df['MA20'] = calculate_ma(df['收盘'], 20)
        df['MA30'] = calculate_ma(df['收盘'], 30)

        # Find convergence period
        conv_period = find_convergence_period(df, end_date)
        if conv_period is None:
            return None

        conv_start_idx, conv_end_idx = conv_period

        # Find divergence start
        div_start_idx = find_divergence_start(df, conv_end_idx)
        if div_start_idx is None:
            return None

        # Check volume condition
        if not check_volume_condition(df, conv_start_idx, conv_end_idx, div_start_idx):
            return None

        # Calculate return
        return_pct = calculate_return_after_divergence(df, div_start_idx)

        # Only include upward divergence (positive return)
        if return_pct <= 0:
            return None

        return {
            'code': stock_code,
            'conv_start': df.loc[conv_start_idx, '日期'],
            'conv_end': df.loc[conv_end_idx, '日期'],
            'div_start': df.loc[div_start_idx, '日期'],
            'return_pct': round(return_pct, 2)
        }

    except Exception as e:
        print(f"Error scanning {stock_code}: {e}")
        return None

def main():
    """Main function to scan stocks and output results"""

    # Get stock list (A-share stocks)
    print("Fetching stock list...")
    try:
        stock_list = ak.stock_zh_a_spot_em()
        # Filter for stocks starting with 300 (ChiNext) and 600/000 (Main board)
        stock_codes = stock_list['代码'].tolist()
        # Limit to reasonable sample for testing
        stock_codes = [code for code in stock_codes if code.startswith(('300', '600', '000'))][:100]
    except Exception as e:
        print(f"Error fetching stock list: {e}")
        # Use sample codes for testing
        stock_codes = ['300750', '300059', '000001', '600519']

    print(f"Scanning {len(stock_codes)} stocks...")

    results = []
    for i, code in enumerate(stock_codes):
        if (i + 1) % 10 == 0:
            print(f"Progress: {i+1}/{len(stock_codes)}")

        result = scan_stock(code)
        if result:
            results.append(result)
            print(f"Found: {code}")

    # Write results
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_26_ma_convergence_divergence/independent/claudecode/ma_divergence.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,粘合期开始,粘合期结束,发散开始日期,发散后5日涨幅(%)\n")

        if results:
            for r in results:
                f.write(f"{r['code']},{r['conv_start']},{r['conv_end']},{r['div_start']},{r['return_pct']}\n")
        else:
            f.write("# 无符合条件的股票\n")

    print(f"\nResults written to ma_divergence.txt")
    print(f"Found {len(results)} stocks matching criteria")

if __name__ == "__main__":
    main()
