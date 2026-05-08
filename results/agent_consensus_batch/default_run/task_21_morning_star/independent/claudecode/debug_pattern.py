#!/usr/bin/env python3
"""Debug the pattern detection"""

import pandas as pd
import numpy as np

np.random.seed(42)


def calculate_body_ratio(open_price, close_price, high_price, low_price):
    body = abs(close_price - open_price)
    amplitude = high_price - low_price
    if amplitude == 0:
        return 0
    return body / amplitude


def calculate_pct_change(open_price, close_price):
    if open_price == 0:
        return 0
    return (close_price - open_price) / open_price * 100


# Create simple test data with known pattern
dates = pd.date_range(end='2024-03-08', periods=90, freq='B')
data = []

base_price = 25.0

for i in range(90):
    if i < 60:
        # Build up price for MA60
        price = base_price * 1.5
        open_p = price
        close_p = price * 1.001
        high_p = close_p * 1.005
        low_p = open_p * 0.995
    elif i == 70:
        # Day 1: Big bearish
        open_p = base_price * 1.2
        close_p = open_p * 0.955  # -4.5% drop
        body = abs(close_p - open_p)
        amplitude = body / 0.75
        high_p = open_p + amplitude * 0.1
        low_p = close_p - amplitude * 0.15
    elif i == 71:
        # Day 2: Small
        open_p = data[-1]['close']
        close_p = open_p * 1.008  # +0.8%
        high_p = close_p * 1.003
        low_p = open_p * 0.997
    elif i == 72:
        # Day 3: Big bullish
        open_p = data[-1]['close']
        close_p = open_p * 1.048  # +4.8%
        body = abs(close_p - open_p)
        amplitude = body / 0.75
        high_p = close_p + amplitude * 0.1
        low_p = open_p - amplitude * 0.15
    elif i <= 77:
        # Next 5 days - uptrend
        open_p = data[-1]['close']
        close_p = open_p * 1.02
        high_p = close_p * 1.01
        low_p = open_p * 0.99
    else:
        # Normal
        open_p = data[-1]['close']
        close_p = open_p * 1.001
        high_p = close_p * 1.005
        low_p = open_p * 0.995

    data.append({
        'date': dates[i],
        'open': open_p,
        'close': close_p,
        'high': high_p,
        'low': low_p
    })

df = pd.DataFrame(data)

# Check pattern at index 70
idx = 70
day1 = df.iloc[idx]
day2 = df.iloc[idx + 1]
day3 = df.iloc[idx + 2]

print("Pattern Check at index 70:")
print(f"Day 1 ({day1['date'].strftime('%Y-%m-%d')}):")
day1_pct = calculate_pct_change(day1['open'], day1['close'])
day1_body_ratio = calculate_body_ratio(day1['open'], day1['close'], day1['high'], day1['low'])
print(f"  Open: {day1['open']:.2f}, Close: {day1['close']:.2f}")
print(f"  Pct change: {day1_pct:.2f}% (need < -3%)")
print(f"  Body ratio: {day1_body_ratio:.2f} (need > 0.7)")
print(f"  ✓" if (day1_pct < -3 and day1_body_ratio > 0.7) else "  ✗")

print(f"\nDay 2 ({day2['date'].strftime('%Y-%m-%d')}):")
day2_pct = calculate_pct_change(day2['open'], day2['close'])
print(f"  Open: {day2['open']:.2f}, Close: {day2['close']:.2f}")
print(f"  Pct change: {day2_pct:.2f}% (need |x| < 1.5%)")
print(f"  ✓" if abs(day2_pct) < 1.5 else "  ✗")

print(f"\nDay 3 ({day3['date'].strftime('%Y-%m-%d')}):")
day3_pct = calculate_pct_change(day3['open'], day3['close'])
day3_body_ratio = calculate_body_ratio(day3['open'], day3['close'], day3['high'], day3['low'])
day1_midpoint = (day1['open'] + day1['close']) / 2
print(f"  Open: {day3['open']:.2f}, Close: {day3['close']:.2f}")
print(f"  Pct change: {day3_pct:.2f}% (need > 3%)")
print(f"  Body ratio: {day3_body_ratio:.2f} (need > 0.7)")
print(f"  Day1 midpoint: {day1_midpoint:.2f}")
print(f"  Close > midpoint: {day3['close']:.2f} > {day1_midpoint:.2f} = {day3['close'] > day1_midpoint}")
print(f"  ✓" if (day3_pct > 3 and day3_body_ratio > 0.7 and day3['close'] > day1_midpoint) else "  ✗")

# Check MA60
ma60 = df.iloc[idx-60:idx]['close'].mean()
print(f"\nLow position check:")
print(f"  MA60: {ma60:.2f}")
print(f"  MA60 * 0.9: {ma60 * 0.9:.2f}")
print(f"  Day3 close: {day3['close']:.2f}")
print(f"  Day3 < MA60*0.9: {day3['close'] < ma60 * 0.9}")
print(f"  ✓" if day3['close'] < ma60 * 0.9 else "  ✗")

# Check post validation
pattern_lowest = min(day1['low'], day2['low'], day3['low'])
print(f"\nPost validation:")
print(f"  Pattern lowest: {pattern_lowest:.2f}")
next_5 = df.iloc[idx+3:idx+8]
breaks = []
for i, day in next_5.iterrows():
    if day['low'] < pattern_lowest:
        breaks.append(f"Day {i}: {day['low']:.2f}")
print(f"  Breaks: {breaks if breaks else 'None'}")
print(f"  ✓" if len(breaks) == 0 else "  ✗")

# Calculate return
if idx + 7 < len(df):
    return_5d = (df.iloc[idx+7]['close'] - day3['close']) / day3['close'] * 100
    print(f"\n5-day return: {return_5d:.2f}%")
