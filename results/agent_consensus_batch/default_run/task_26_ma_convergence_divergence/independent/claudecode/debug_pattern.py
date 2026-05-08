#!/usr/bin/env python3
"""
Debug version to understand why patterns aren't being detected
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_ma(prices: pd.Series, period: int) -> pd.Series:
    """Calculate moving average"""
    return prices.rolling(window=period, min_periods=period).mean()

def check_convergence(ma5: float, ma10: float, ma20: float, ma30: float) -> bool:
    """Check if 4 MAs are converged (max distance < 3%)"""
    mas = [ma5, ma10, ma20, ma30]
    if any(pd.isna(x) or x <= 0 for x in mas):
        return False
    max_ma = max(mas)
    min_ma = min(mas)
    distance = (max_ma - min_ma) / min_ma
    return distance < 0.03

def check_divergence(ma5: float, ma10: float, ma20: float, ma30: float) -> bool:
    """Check if MAs are diverged upward: 5 > 10 > 20 > 30, adjacent gaps > 2%"""
    if any(pd.isna(x) or x <= 0 for x in [ma5, ma10, ma20, ma30]):
        return False
    if not (ma5 > ma10 > ma20 > ma30):
        return False
    gap1 = (ma5 - ma10) / ma10
    gap2 = (ma10 - ma20) / ma20
    gap3 = (ma20 - ma30) / ma30
    return all(gap > 0.02 for gap in [gap1, gap2, gap3])

# Create test data
dates = pd.date_range(end='2024-08-08', periods=60, freq='D')
prices = []

# Build stable base
for i in range(40):
    prices.append(50.0)

# Convergence period - keep very tight
for i in range(8):
    prices.append(50.0 + i * 0.02)

# Divergence - sharp rise
for i in range(12):
    prices.append(50.2 + i * 2.0)

volumes = [100000] * 40 + [100000] * 8 + [200000] * 12

df = pd.DataFrame({
    '日期': dates.strftime('%Y-%m-%d'),
    '收盘': prices,
    '成交量': volumes
})

df['MA5'] = calculate_ma(df['收盘'], 5)
df['MA10'] = calculate_ma(df['收盘'], 10)
df['MA20'] = calculate_ma(df['收盘'], 20)
df['MA30'] = calculate_ma(df['收盘'], 30)

print("Last 25 days of data:")
print(df[['日期', '收盘', 'MA5', 'MA10', 'MA20', 'MA30']].tail(25).to_string())

print("\n\nChecking convergence in last 20 days:")
for i in range(len(df) - 20, len(df)):
    date = df.loc[i, '日期']
    ma5, ma10, ma20, ma30 = df.loc[i, 'MA5'], df.loc[i, 'MA10'], df.loc[i, 'MA20'], df.loc[i, 'MA30']
    if not pd.isna(ma30):
        is_conv = check_convergence(ma5, ma10, ma20, ma30)
        max_dist = (max([ma5, ma10, ma20, ma30]) - min([ma5, ma10, ma20, ma30])) / min([ma5, ma10, ma20, ma30])
        print(f"{date}: Conv={is_conv}, MaxDist={max_dist:.4f} (MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}, MA30={ma30:.2f})")

print("\n\nChecking divergence in last 15 days:")
for i in range(len(df) - 15, len(df)):
    date = df.loc[i, '日期']
    ma5, ma10, ma20, ma30 = df.loc[i, 'MA5'], df.loc[i, 'MA10'], df.loc[i, 'MA20'], df.loc[i, 'MA30']
    if not pd.isna(ma30):
        is_div = check_divergence(ma5, ma10, ma20, ma30)
        order_ok = ma5 > ma10 > ma20 > ma30
        if order_ok:
            gap1 = (ma5 - ma10) / ma10
            gap2 = (ma10 - ma20) / ma20
            gap3 = (ma20 - ma30) / ma30
            print(f"{date}: Div={is_div}, Order={order_ok}, Gaps={gap1:.4f},{gap2:.4f},{gap3:.4f}")
        else:
            print(f"{date}: Div={is_div}, Order={order_ok}")
