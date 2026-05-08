#!/usr/bin/env python3
import pandas as pd
import numpy as np

def calculate_ma(prices: pd.Series, period: int) -> pd.Series:
    return prices.rolling(window=period, min_periods=period).mean()

# Create data
dates = pd.date_range(end='2024-08-08', periods=60, freq='D')
prices = []

# Days 0-37: stable
for i in range(38):
    prices.append(50.0)

# Days 38-44: convergence (7 days)
for i in range(7):
    prices.append(50.0 + i * 0.005)

# Days 45-46: sharp breakout
prices.append(52.0)
prices.append(55.0)

# Days 47-59: strong uptrend
for i in range(13):
    prices.append(55.0 + i * 3.0)

volumes = []
for i in range(60):
    if 38 <= i <= 44:
        volumes.append(100000)
    elif i >= 47:
        volumes.append(200000)
    else:
        volumes.append(120000)

df = pd.DataFrame({
    '日期': dates.strftime('%Y-%m-%d'),
    '收盘': prices,
    '成交量': volumes
})

df['MA5'] = calculate_ma(df['收盘'], 5)
df['MA10'] = calculate_ma(df['收盘'], 10)
df['MA20'] = calculate_ma(df['收盘'], 20)
df['MA30'] = calculate_ma(df['收盘'], 30)

print("Last 25 rows:")
print(df[['日期', '收盘', 'MA5', 'MA10', 'MA20', 'MA30', '成交量']].tail(25).to_string())

print("\n\nChecking divergence around day 47-49:")
for i in [47, 48, 49]:
    ma5, ma10, ma20, ma30 = df.loc[i, 'MA5'], df.loc[i, 'MA10'], df.loc[i, 'MA20'], df.loc[i, 'MA30']
    order = ma5 > ma10 > ma20 > ma30
    if order:
        gap1 = (ma5 - ma10) / ma10
        gap2 = (ma10 - ma20) / ma20
        gap3 = (ma20 - ma30) / ma30
        all_gaps_ok = all(g > 0.02 for g in [gap1, gap2, gap3])
        print(f"Day {i} ({df.loc[i, '日期']}): Order={order}, Gaps={gap1:.4f},{gap2:.4f},{gap3:.4f}, AllOK={all_gaps_ok}")
