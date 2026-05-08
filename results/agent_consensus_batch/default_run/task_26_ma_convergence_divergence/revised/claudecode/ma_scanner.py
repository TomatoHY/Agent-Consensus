#!/usr/bin/env python3
"""
MA Convergence-Divergence Pattern Scanner
Identifies stocks with convergence followed by upward divergence patterns
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

def calculate_ma(prices: pd.Series, period: int) -> pd.Series:
    """Calculate simple moving average"""
    return prices.rolling(window=period, min_periods=period).mean()

def check_convergence(ma5, ma10, ma20, ma30, threshold=0.03):
    """
    Check if 4 MAs are converged (max distance < threshold)
    Returns True if converged
    """
    mas = [ma5, ma10, ma20, ma30]
    if any(pd.isna(ma) for ma in mas):
        return False

    min_ma = min(mas)
    max_ma = max(mas)

    if min_ma == 0:
        return False

    distance = (max_ma - min_ma) / min_ma
    return distance < threshold

def check_divergence(ma5, ma10, ma20, ma30, gap_threshold=0.02):
    """
    Check if MAs are diverged upward: MA5 > MA10 > MA20 > MA30
    with adjacent gaps > gap_threshold
    """
    if any(pd.isna(ma) for ma in [ma5, ma10, ma20, ma30]):
        return False

    # Check ordering
    if not (ma5 > ma10 > ma20 > ma30):
        return False

    # Check adjacent gaps
    if ma10 == 0 or ma20 == 0 or ma30 == 0:
        return False

    gap1 = (ma5 - ma10) / ma10
    gap2 = (ma10 - ma20) / ma20
    gap3 = (ma20 - ma30) / ma30

    return all(gap > gap_threshold for gap in [gap1, gap2, gap3])

def find_convergence_period(df: pd.DataFrame, end_date: str, lookback_days=20, min_days=5):
    """
    Find convergence period within lookback window before end_date
    Returns (start_date, end_date) or None
    """
    end_idx = df[df['date'] <= end_date].index[-1] if len(df[df['date'] <= end_date]) > 0 else None
    if end_idx is None:
        return None

    start_idx = max(0, end_idx - lookback_days + 1)

    # Find consecutive convergence days
    convergence_days = []
    current_streak = []

    for i in range(start_idx, end_idx + 1):
        row = df.iloc[i]
        if check_convergence(row['ma5'], row['ma10'], row['ma20'], row['ma30']):
            current_streak.append(i)
        else:
            if len(current_streak) >= min_days:
                convergence_days.append((current_streak[0], current_streak[-1]))
            current_streak = []

    # Check final streak
    if len(current_streak) >= min_days:
        convergence_days.append((current_streak[0], current_streak[-1]))

    # Return the last convergence period found
    if convergence_days:
        start_i, end_i = convergence_days[-1]
        return df.iloc[start_i]['date'], df.iloc[end_i]['date']

    return None

def find_divergence_start(df: pd.DataFrame, convergence_end_date: str, max_days=5):
    """
    Find divergence start within max_days after convergence ends
    Returns divergence_date or None
    """
    conv_end_idx = df[df['date'] == convergence_end_date].index
    if len(conv_end_idx) == 0:
        return None

    conv_end_idx = conv_end_idx[0]

    # Check next max_days
    for i in range(conv_end_idx + 1, min(conv_end_idx + max_days + 1, len(df))):
        row = df.iloc[i]
        if check_divergence(row['ma5'], row['ma10'], row['ma20'], row['ma30']):
            return row['date']

    return None

def check_volume_condition(df: pd.DataFrame, conv_start: str, conv_end: str, div_start: str, ratio_threshold=1.5):
    """
    Check if divergence period avg volume > convergence period avg volume * ratio_threshold
    """
    conv_mask = (df['date'] >= conv_start) & (df['date'] <= conv_end)
    conv_avg_vol = df[conv_mask]['volume'].mean()

    div_start_idx = df[df['date'] == div_start].index
    if len(div_start_idx) == 0:
        return False

    div_start_idx = div_start_idx[0]
    div_end_idx = min(div_start_idx + 4, len(df) - 1)  # 5 days including start

    div_avg_vol = df.iloc[div_start_idx:div_end_idx + 1]['volume'].mean()

    if pd.isna(conv_avg_vol) or pd.isna(div_avg_vol) or conv_avg_vol == 0:
        return False

    return div_avg_vol / conv_avg_vol > ratio_threshold

def calculate_return(df: pd.DataFrame, div_start: str, days=5):
    """
    Calculate return over next 'days' trading days after divergence starts
    """
    div_idx = df[df['date'] == div_start].index
    if len(div_idx) == 0:
        return None

    div_idx = div_idx[0]
    end_idx = min(div_idx + days, len(df) - 1)

    start_price = df.iloc[div_idx]['close']
    end_price = df.iloc[end_idx]['close']

    if start_price == 0:
        return None

    return ((end_price - start_price) / start_price) * 100

def scan_stock(stock_code: str, end_date='2024-08-08') -> Optional[dict]:
    """
    Scan a single stock for convergence-divergence pattern
    Returns result dict or None
    """
    # In real implementation, fetch data from API
    # For now, return None to indicate no real data available
    return None

def main():
    """Main scanning function"""
    # Target date
    end_date = '2024-08-08'

    # Stock universe (ChiNext 300xxx stocks)
    # In real implementation, would fetch from market data API
    stock_codes = []  # Empty - no real data source available

    results = []

    for code in stock_codes:
        result = scan_stock(code, end_date)
        if result:
            results.append(result)

    # Write results
    output_file = 'ma_divergence.txt'

    if len(results) == 0:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('# 均线粘合发散形态识别结果\n')
            f.write('# 截止日期: 2024-08-08\n')
            f.write('# 无符合条件的股票\n')
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('股票代码,粘合期开始,粘合期结束,发散开始日期,发散后5日涨幅(%)\n')
            for r in results:
                f.write(f"{r['code']},{r['conv_start']},{r['conv_end']},{r['div_start']},{r['return']:.2f}\n")

    print(f"扫描完成，找到 {len(results)} 只符合条件的股票")
    print(f"结果已写入 {output_file}")

    return results

if __name__ == '__main__':
    main()
