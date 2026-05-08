#!/usr/bin/env python3
"""
Detailed debug to find the exact issue
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_ma(prices: pd.Series, period: int) -> pd.Series:
    return prices.rolling(window=period, min_periods=period).mean()

def check_convergence(ma5, ma10, ma20, ma30):
    mas = [ma5, ma10, ma20, ma30]
    if any(pd.isna(x) or x <= 0 for x in mas):
        return False
    max_ma = max(mas)
    min_ma = min(mas)
    distance = (max_ma - min_ma) / min_ma
    return distance < 0.03

def check_divergence(ma5, ma10, ma20, ma30):
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

# Days 0-38: stable base
for i in range(39):
    prices.append(50.0)

# Days 39-45: convergence (7 days)
for i in range(7):
    prices.append(50.0 + i * 0.01)

# Days 46-48: transition
for i in range(3):
    prices.append(50.1 + i * 0.5)

# Days 49-59: divergence
for i in range(11):
    prices.append(51.1 + i * 2.5)

volumes = []
for i in range(60):
    if 39 <= i <= 45:
        volumes.append(100000)
    elif i >= 49:
        volumes.append(180000)
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

print("Checking for convergence period (need 5+ consecutive days):")
print("=" * 80)

end_date = '2024-08-08'
end_idx = df[df['日期'] <= end_date].index[-1]
start_search_idx = max(0, end_idx - 19)

print(f"Searching from index {start_search_idx} to {end_idx} (last 20 days)")
print()

convergence_days = []
for i in range(start_search_idx, end_idx + 1):
    date = df.loc[i, '日期']
    ma5, ma10, ma20, ma30 = df.loc[i, 'MA5'], df.loc[i, 'MA10'], df.loc[i, 'MA20'], df.loc[i, 'MA30']

    if not pd.isna(ma30):
        is_conv = check_convergence(ma5, ma10, ma20, ma30)
        max_dist = (max([ma5, ma10, ma20, ma30]) - min([ma5, ma10, ma20, ma30])) / min([ma5, ma10, ma20, ma30])

        if is_conv:
            convergence_days.append(i)
            print(f"✓ {date} (idx {i}): CONVERGED - dist={max_dist:.4f}, consecutive={len(convergence_days)}")
        else:
            if convergence_days:
                print(f"✗ {date} (idx {i}): NOT converged - dist={max_dist:.4f}, RESET counter")
            convergence_days = []

        if len(convergence_days) >= 5:
            conv_start_idx = convergence_days[0]
            conv_end_idx = convergence_days[-1]
            print(f"\n>>> FOUND CONVERGENCE PERIOD: idx {conv_start_idx} to {conv_end_idx}")
            print(f">>> Dates: {df.loc[conv_start_idx, '日期']} to {df.loc[conv_end_idx, '日期']}")

            print(f"\n\nChecking for divergence within 5 days after convergence ends (idx {conv_end_idx}):")
            print("=" * 80)

            for j in range(conv_end_idx + 1, min(conv_end_idx + 6, len(df))):
                date_j = df.loc[j, '日期']
                ma5_j, ma10_j, ma20_j, ma30_j = df.loc[j, 'MA5'], df.loc[j, 'MA10'], df.loc[j, 'MA20'], df.loc[j, 'MA30']

                is_div = check_divergence(ma5_j, ma10_j, ma20_j, ma30_j)
                order_ok = ma5_j > ma10_j > ma20_j > ma30_j

                if order_ok:
                    gap1 = (ma5_j - ma10_j) / ma10_j
                    gap2 = (ma10_j - ma20_j) / ma20_j
                    gap3 = (ma20_j - ma30_j) / ma30_j

                    if is_div:
                        print(f"✓ {date_j} (idx {j}): DIVERGED - gaps={gap1:.4f},{gap2:.4f},{gap3:.4f}")

                        # Check volume
                        div_end = min(j + 4, len(df) - 1)
                        conv_avg_vol = df.loc[conv_start_idx:conv_end_idx, '成交量'].mean()
                        div_avg_vol = df.loc[j:div_end, '成交量'].mean()
                        vol_ratio = div_avg_vol / conv_avg_vol

                        print(f"\n>>> Volume check:")
                        print(f"    Convergence avg volume: {conv_avg_vol:.0f}")
                        print(f"    Divergence avg volume: {div_avg_vol:.0f}")
                        print(f"    Ratio: {vol_ratio:.2f}x (need > 1.5x)")

                        if vol_ratio > 1.5:
                            print(f"    ✓ Volume condition MET")

                            # Calculate return
                            div_end_ret = min(j + 5, len(df) - 1)
                            start_price = df.loc[j, '收盘']
                            end_price = df.loc[div_end_ret, '收盘']
                            return_pct = ((end_price - start_price) / start_price) * 100

                            print(f"\n>>> Return calculation:")
                            print(f"    Start price (idx {j}): {start_price:.2f}")
                            print(f"    End price (idx {div_end_ret}): {end_price:.2f}")
                            print(f"    5-day return: {return_pct:.2f}%")

                            if return_pct > 0:
                                print(f"\n✓✓✓ PATTERN FOUND! ✓✓✓")
                            else:
                                print(f"\n✗ Return not positive")
                        else:
                            print(f"    ✗ Volume condition NOT met")

                        break
                    else:
                        print(f"✗ {date_j} (idx {j}): Order OK but gaps too small - {gap1:.4f},{gap2:.4f},{gap3:.4f}")
                else:
                    print(f"✗ {date_j} (idx {j}): Order not satisfied (5>10>20>30)")

            break
