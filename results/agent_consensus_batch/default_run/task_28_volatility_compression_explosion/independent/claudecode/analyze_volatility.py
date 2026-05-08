#!/usr/bin/env python3
"""
Volatility Compression-Explosion Pattern Detection for ChiNext Stocks
识别创业板"波动率压缩-爆发"模式
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak

def calculate_amplitude(high, low):
    """Calculate daily amplitude: (high - low) / low"""
    return (high - low) / low

def calculate_hv10(close_prices):
    """
    Calculate 10-day historical volatility (HV10)
    HV10 = std(log returns over 10 days) × √252
    """
    if len(close_prices) < 2:
        return np.nan
    log_returns = np.log(close_prices / close_prices.shift(1))
    return log_returns.std() * np.sqrt(252)

def find_low_volatility_period(df, end_date, lookback_days=30, threshold=0.03):
    """
    Find low volatility periods in the last lookback_days before end_date
    Returns the longest consecutive period with amplitude < threshold
    """
    mask = df.index <= end_date
    recent_data = df[mask].tail(lookback_days)

    if len(recent_data) < 10:
        return None, 0

    # Calculate amplitude
    recent_data = recent_data.copy()
    recent_data['amplitude'] = calculate_amplitude(recent_data['high'], recent_data['low'])

    # Find consecutive low volatility days
    recent_data['is_low_vol'] = recent_data['amplitude'] < threshold

    # Find longest consecutive sequence
    max_consecutive = 0
    current_consecutive = 0
    end_idx = None
    current_end_idx = None

    for idx, is_low in enumerate(recent_data['is_low_vol']):
        if is_low:
            current_consecutive += 1
            current_end_idx = idx
            if current_consecutive > max_consecutive:
                max_consecutive = current_consecutive
                end_idx = current_end_idx
        else:
            current_consecutive = 0

    if max_consecutive >= 10:
        compression_end_date = recent_data.index[end_idx]
        return compression_end_date, max_consecutive

    return None, 0

def check_hv_compression(df, compression_end_date, hv_lookback=60):
    """
    Check if HV10 during compression is below 30th percentile of 60-day HV10
    """
    mask = df.index <= compression_end_date
    historical_data = df[mask].tail(hv_lookback + 10)

    if len(historical_data) < hv_lookback:
        return False

    # Calculate rolling HV10 for the 60-day period
    hv10_series = []
    for i in range(10, len(historical_data) + 1):
        window_data = historical_data.iloc[i-10:i]
        hv10 = calculate_hv10(window_data['close'])
        hv10_series.append(hv10)

    if len(hv10_series) < hv_lookback:
        return False

    hv10_array = np.array(hv10_series[-hv_lookback:])
    percentile_30 = np.percentile(hv10_array, 30)

    # Check if compression period HV10 is below 30th percentile
    compression_hv10 = hv10_series[-1]

    return compression_hv10 < percentile_30

def find_explosion_day(df, compression_end_date, lookforward_days=5, explosion_threshold=0.07):
    """
    Find explosion day within lookforward_days after compression
    Explosion: amplitude > 7%, bullish candle, close in upper 70% of range
    """
    start_idx = df.index.get_loc(compression_end_date)

    if start_idx + lookforward_days >= len(df):
        return None

    for i in range(1, lookforward_days + 1):
        if start_idx + i >= len(df):
            break

        day_data = df.iloc[start_idx + i]
        amplitude = calculate_amplitude(day_data['high'], day_data['low'])

        # Check explosion conditions
        if amplitude > explosion_threshold:
            # Check bullish (close > open)
            is_bullish = day_data['close'] > day_data['open']

            # Check close in upper 70% of range
            if day_data['high'] != day_data['low']:
                close_position = (day_data['close'] - day_data['low']) / (day_data['high'] - day_data['low'])
            else:
                close_position = 0.5

            is_upper_70 = close_position > 0.7

            if is_bullish and is_upper_70:
                return df.index[start_idx + i]

    return None

def check_no_pullback(df, explosion_date, lookforward_days=3):
    """
    Check if price doesn't pull back in the next lookforward_days
    No pullback: low >= explosion day open price
    """
    explosion_idx = df.index.get_loc(explosion_date)
    explosion_open = df.iloc[explosion_idx]['open']

    if explosion_idx + lookforward_days >= len(df):
        return False, 0.0

    for i in range(1, lookforward_days + 1):
        if explosion_idx + i >= len(df):
            return False, 0.0

        day_low = df.iloc[explosion_idx + i]['low']
        if day_low < explosion_open:
            return False, 0.0

    # Calculate 3-day return
    day3_close = df.iloc[explosion_idx + lookforward_days]['close']
    explosion_close = df.iloc[explosion_idx]['close']
    return_3d = (day3_close - explosion_close) / explosion_close * 100

    return True, return_3d

def analyze_stock(stock_code, end_date):
    """Analyze a single stock for volatility compression-explosion pattern"""
    try:
        # Fetch stock data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")

        if df is None or len(df) == 0:
            return None

        # Rename columns to English
        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df = df.sort_index()

        # Filter data up to end_date + some buffer for explosion detection
        buffer_date = end_date + timedelta(days=30)
        df = df[df.index <= buffer_date]

        if len(df) < 100:  # Need enough historical data
            return None

        # Step 1: Find low volatility period
        compression_end_date, compression_days = find_low_volatility_period(df, end_date)

        if compression_end_date is None or compression_days < 10:
            return None

        # Step 2: Check HV compression
        if not check_hv_compression(df, compression_end_date):
            return None

        # Step 3: Find explosion day
        explosion_date = find_explosion_day(df, compression_end_date)

        if explosion_date is None:
            return None

        # Step 4 & 5: Check no pullback
        no_pullback, return_3d = check_no_pullback(df, explosion_date)

        if not no_pullback:
            return None

        # Calculate explosion amplitude
        explosion_idx = df.index.get_loc(explosion_date)
        explosion_data = df.iloc[explosion_idx]
        explosion_amplitude = calculate_amplitude(explosion_data['high'], explosion_data['low']) * 100

        return {
            'stock_code': stock_code,
            'compression_days': compression_days,
            'explosion_date': explosion_date.strftime('%Y-%m-%d'),
            'explosion_amplitude': round(explosion_amplitude, 1),
            'return_3d': round(return_3d, 1)
        }

    except Exception as e:
        print(f"Error analyzing {stock_code}: {e}")
        return None

def main():
    """Main function to analyze ChiNext stocks"""
    end_date = datetime(2024, 10, 8)

    print("Fetching ChiNext stock list...")

    # Get ChiNext stock list (300XXX codes)
    try:
        stock_list = ak.stock_zh_a_spot_em()
        chinext_stocks = stock_list[stock_list['代码'].str.startswith('300')]['代码'].tolist()
        print(f"Found {len(chinext_stocks)} ChiNext stocks")
    except Exception as e:
        print(f"Error fetching stock list: {e}")
        # Use a sample of ChiNext stocks if API fails
        chinext_stocks = [f"300{str(i).zfill(3)}" for i in range(1, 100)]

    results = []

    print(f"Analyzing stocks for volatility compression-explosion pattern...")
    print(f"End date: {end_date.strftime('%Y-%m-%d')}")

    for i, stock_code in enumerate(chinext_stocks[:50]):  # Limit to first 50 for time
        if (i + 1) % 10 == 0:
            print(f"Progress: {i + 1}/{min(50, len(chinext_stocks))}")

        result = analyze_stock(stock_code, end_date)
        if result:
            results.append(result)
            print(f"Found pattern: {result}")

    # Write results
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_28_volatility_compression_explosion/independent/claudecode/vol_explosion.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,压缩期天数,爆发日期,爆发振幅(%),爆发后3日涨幅(%)\n")

        if len(results) == 0:
            f.write("# 无符合条件的股票\n")
        else:
            for r in results:
                f.write(f"{r['stock_code']},{r['compression_days']},{r['explosion_date']},{r['explosion_amplitude']},{r['return_3d']}\n")

    print(f"\nAnalysis complete. Found {len(results)} stocks matching the pattern.")
    print(f"Results written to: {output_file}")

if __name__ == "__main__":
    main()
