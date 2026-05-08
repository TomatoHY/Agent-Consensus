#!/usr/bin/env python3
"""
Debug version to understand why no stocks are matching
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def calculate_true_range(df):
    """Calculate True Range for each day"""
    df = df.copy()
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = abs(df['high'] - df['close'].shift(1))
    df['l-pc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    return df

def calculate_atr_wilder(tr_series, period=14):
    """Calculate ATR using Wilder's smoothing method"""
    atr = pd.Series(index=tr_series.index, dtype=float)
    atr.iloc[period-1] = tr_series.iloc[:period].mean()
    for i in range(period, len(tr_series)):
        atr.iloc[i] = (atr.iloc[i-1] * (period - 1) + tr_series.iloc[i]) / period
    return atr

def check_breakout_with_debug(df, target_date):
    """Check conditions with detailed debugging"""
    try:
        target_idx = df[df['date'] == target_date].index
        if len(target_idx) == 0:
            return None, "Target date not found"

        target_idx = target_idx[0]
        if target_idx < 60:
            return None, "Insufficient history"

        current_atr = df.loc[target_idx, 'atr']
        if pd.isna(current_atr):
            return None, "ATR is NaN"

        atr_history = df.loc[target_idx-60:target_idx-1, 'atr'].dropna()
        if len(atr_history) < 30:
            return None, "Insufficient ATR history"

        atr_80pct = atr_history.quantile(0.8)

        # Check each condition
        reasons = []

        # Condition 2: ATR > 80th percentile
        if current_atr <= atr_80pct:
            reasons.append(f"ATR not expanded: {current_atr:.2f} <= {atr_80pct:.2f}")

        # Condition 3: Close breaks 20-day high
        price_history = df.loc[target_idx-20:target_idx-1, 'high']
        max_20d_high = price_history.max()
        current_close = df.loc[target_idx, 'close']

        if current_close <= max_20d_high:
            reasons.append(f"No price breakout: {current_close:.2f} <= {max_20d_high:.2f}")

        # Condition 4: Volume > 2x average
        volume_history = df.loc[target_idx-20:target_idx-1, 'volume']
        avg_volume_20d = volume_history.mean()
        current_volume = df.loc[target_idx, 'volume']

        if current_volume <= avg_volume_20d * 2:
            reasons.append(f"Volume not 2x: {current_volume:.0f} <= {avg_volume_20d*2:.0f}")

        # Condition 5: Bullish with gain > 3%
        current_open = df.loc[target_idx, 'open']
        if current_close <= current_open:
            reasons.append(f"Not bullish: close {current_close:.2f} <= open {current_open:.2f}")
        else:
            pct_change = ((current_close - current_open) / current_open) * 100
            if pct_change <= 3.0:
                reasons.append(f"Gain too small: {pct_change:.2f}% <= 3%")

        if len(reasons) == 0:
            pct_change = ((current_close - current_open) / current_open) * 100
            return {
                'atr': round(current_atr, 2),
                'atr_80pct': round(atr_80pct, 2),
                'date': target_date,
                'pct_change': round(pct_change, 2)
            }, "MATCH"
        else:
            return None, "; ".join(reasons)

    except Exception as e:
        return None, f"Error: {str(e)}"

def main():
    target_date = '2024-09-09'
    end_date = datetime.strptime(target_date, '%Y-%m-%d')
    start_date = end_date - timedelta(days=150)

    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')

    # Test a few stocks with debugging
    test_stocks = ['300001', '300002', '300003', '300059', '300750', '300999']

    print(f"Debug analysis for {target_date}\n")

    for stock_code in test_stocks:
        try:
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                   start_date=start_str, end_date=end_str, adjust="qfq")

            if df is None or len(df) < 80:
                print(f"{stock_code}: Insufficient data")
                continue

            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'pct_change', 'change', 'turnover_rate']
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

            df = calculate_true_range(df)
            df['atr'] = calculate_atr_wilder(df['tr'], period=14)

            result, reason = check_breakout_with_debug(df, target_date)

            if result:
                print(f"✓ {stock_code}: MATCH - {reason}")
            else:
                print(f"✗ {stock_code}: {reason}")

        except Exception as e:
            print(f"✗ {stock_code}: Error - {str(e)}")

    print("\n" + "="*80)
    print("The conditions are very strict. Let me search all stocks systematically...")

if __name__ == '__main__':
    main()
