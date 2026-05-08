#!/usr/bin/env python3
"""
ATR Volatility Breakout Detection for ChiNext Stocks
Identifies stocks with expanding volatility and price breakouts as of 2024-09-09
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

    # First ATR is simple average
    atr.iloc[period-1] = tr_series.iloc[:period].mean()

    # Subsequent ATRs use Wilder's smoothing: ATR = (prior_ATR * (n-1) + current_TR) / n
    for i in range(period, len(tr_series)):
        atr.iloc[i] = (atr.iloc[i-1] * (period - 1) + tr_series.iloc[i]) / period

    return atr

def check_breakout_conditions(df, target_date, lookback_atr=60, lookback_price=20, lookback_volume=20):
    """Check if stock meets all breakout conditions on target date"""
    try:
        target_idx = df[df['date'] == target_date].index
        if len(target_idx) == 0:
            return None

        target_idx = target_idx[0]

        # Need enough history
        if target_idx < max(lookback_atr, lookback_price, lookback_volume):
            return None

        # Get ATR at target date
        current_atr = df.loc[target_idx, 'atr']
        if pd.isna(current_atr):
            return None

        # Calculate 80th percentile of previous 60 days ATR
        atr_history = df.loc[target_idx-lookback_atr:target_idx-1, 'atr'].dropna()
        if len(atr_history) < 30:  # Need sufficient data
            return None

        atr_80pct = atr_history.quantile(0.8)

        # Condition 2: ATR > 80th percentile
        if current_atr <= atr_80pct:
            return None

        # Condition 3: Close price breaks 20-day high
        price_history = df.loc[target_idx-lookback_price:target_idx-1, 'high']
        max_20d_high = price_history.max()
        current_close = df.loc[target_idx, 'close']

        if current_close <= max_20d_high:
            return None

        # Condition 4: Volume > 2x 20-day average volume
        volume_history = df.loc[target_idx-lookback_volume:target_idx-1, 'volume']
        avg_volume_20d = volume_history.mean()
        current_volume = df.loc[target_idx, 'volume']

        if current_volume <= avg_volume_20d * 2:
            return None

        # Condition 5: Bullish day with gain > 3%
        current_open = df.loc[target_idx, 'open']
        if current_close <= current_open:  # Not bullish
            return None

        pct_change = ((current_close - current_open) / current_open) * 100
        if pct_change <= 3.0:
            return None

        return {
            'atr': round(current_atr, 2),
            'atr_80pct': round(atr_80pct, 2),
            'date': target_date,
            'pct_change': round(pct_change, 2)
        }

    except Exception as e:
        return None

def get_chinext_stocks():
    """Get list of ChiNext stocks (300XXX)"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except:
        # Fallback: generate common ChiNext codes
        return [f'300{str(i).zfill(3)}' for i in range(1, 1000)]

def main():
    target_date = '2024-09-09'
    end_date = datetime.strptime(target_date, '%Y-%m-%d')
    start_date = end_date - timedelta(days=150)  # Extra buffer for data

    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')

    print(f"Analyzing ChiNext stocks for ATR breakout as of {target_date}")
    print(f"Fetching data from {start_date.date()} to {end_date.date()}")

    chinext_stocks = get_chinext_stocks()
    print(f"Found {len(chinext_stocks)} ChiNext stocks to analyze")

    results = []

    for i, stock_code in enumerate(chinext_stocks[:500], 1):  # Expanded search
        if i % 50 == 0:
            print(f"Progress: {i}/{min(500, len(chinext_stocks))} stocks analyzed...")

        try:
            # Fetch stock data
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                   start_date=start_str, end_date=end_str, adjust="qfq")

            if df is None or len(df) < 80:
                continue

            # Rename columns to English
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'pct_change', 'change', 'turnover_rate']
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

            # Calculate True Range
            df = calculate_true_range(df)

            # Calculate ATR using Wilder's method
            df['atr'] = calculate_atr_wilder(df['tr'], period=14)

            # Check breakout conditions
            result = check_breakout_conditions(df, target_date)

            if result:
                result['code'] = stock_code
                results.append(result)
                print(f"✓ Found: {stock_code} - ATR={result['atr']}, Gain={result['pct_change']}%")

        except Exception as e:
            continue

    # Write results
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_27_atr_volatility_breakout/independent/claudecode/atr_breakout.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("无符合条件的股票\n")
            print("\nNo stocks met all criteria")
        else:
            for r in results:
                line = f"{r['code']},{r['atr']},{r['atr_80pct']},{r['date']},{r['pct_change']}\n"
                f.write(line)
            print(f"\n✓ Found {len(results)} stocks meeting all criteria")
            print(f"✓ Results written to atr_breakout.txt")

if __name__ == '__main__':
    main()
