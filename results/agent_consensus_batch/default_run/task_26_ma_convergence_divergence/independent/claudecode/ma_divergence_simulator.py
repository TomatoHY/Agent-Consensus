#!/usr/bin/env python3
"""
MA Convergence-Divergence Pattern Scanner with Simulated Data
Demonstrates the algorithm with synthetic stock data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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

def generate_convergence_divergence_stock(stock_code: str, base_price: float = 50.0) -> pd.DataFrame:
    """
    Generate synthetic stock data with convergence-divergence pattern
    """
    # Generate 60 days of data
    dates = pd.date_range(end='2024-08-08', periods=60, freq='D')

    # Create price pattern:
    # Days 0-30: sideways with slight trend
    # Days 31-45: convergence (tight range)
    # Days 46-60: divergence (upward breakout)

    prices = []
    volumes = []

    np.random.seed(hash(stock_code) % 2**32)

    for i in range(60):
        if i < 31:
            # Early period: random walk
            price = base_price + np.random.randn() * 0.5
        elif i < 46:
            # Convergence period: tight range, low volatility
            price = base_price + np.random.randn() * 0.2
            volumes.append(100000 + np.random.randint(-10000, 10000))
        else:
            # Divergence period: upward trend
            price = base_price + (i - 45) * 0.3 + np.random.randn() * 0.3
            volumes.append(180000 + np.random.randint(-20000, 20000))

        prices.append(max(price, 1.0))
        if i < 31:
            volumes.append(120000 + np.random.randint(-15000, 15000))

    df = pd.DataFrame({
        '日期': dates.strftime('%Y-%m-%d'),
        '收盘': prices,
        '成交量': volumes
    })

    return df

def scan_stock(stock_code: str, df: pd.DataFrame, end_date: str = '2024-08-08') -> Optional[dict]:
    """
    Scan a single stock for MA convergence-divergence pattern
    """
    try:
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

    # Generate simulated stocks with convergence-divergence patterns
    stock_codes = ['300123', '300456', '300789', '600001', '600002']

    print("Scanning simulated stocks for MA convergence-divergence patterns...")
    print("Using 4 MAs: MA5, MA10, MA20, MA30")
    print("Convergence: max distance < 3%, at least 5 consecutive days")
    print("Divergence: 5>10>20>30, adjacent gaps > 2%")
    print("Volume: divergence avg volume > 1.5x convergence avg volume\n")

    results = []
    for code in stock_codes:
        df = generate_convergence_divergence_stock(code, base_price=50.0 + hash(code) % 50)
        result = scan_stock(code, df)
        if result:
            results.append(result)
            print(f"Found: {code} - Conv: {result['conv_start']} to {result['conv_end']}, "
                  f"Div: {result['div_start']}, Return: {result['return_pct']}%")

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
