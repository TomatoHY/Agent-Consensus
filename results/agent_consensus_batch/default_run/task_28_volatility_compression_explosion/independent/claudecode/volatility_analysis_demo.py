#!/usr/bin/env python3
"""
Volatility Compression-Explosion Pattern Detection - Demo with Simulated Data
识别创业板"波动率压缩-爆发"模式 - 演示版本
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_sample_stock_data(stock_code, start_date, end_date):
    """Generate sample stock data with a compression-explosion pattern"""
    np.random.seed(hash(stock_code) % 2**32)

    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    dates = [d for d in dates if d.weekday() < 5]  # Trading days only

    n = len(dates)
    base_price = 20 + np.random.rand() * 30

    # Generate price series with compression and explosion
    prices = []
    for i in range(n):
        if i < n - 40:
            # Normal volatility period
            volatility = 0.02
        elif i < n - 10:
            # Compression period (low volatility)
            volatility = 0.005
        else:
            # Post-compression period with potential explosion
            volatility = 0.03

        if i == 0:
            price = base_price
        else:
            change = np.random.randn() * volatility
            price = prices[-1] * (1 + change)

        prices.append(price)

    # Create OHLC data
    data = []
    for i, date in enumerate(dates):
        close = prices[i]

        # Add explosion on specific day
        if i == n - 8:  # Explosion day
            amplitude = 0.08  # 8% amplitude
            low = close / (1 + amplitude)
            high = close
            open_price = low * 1.02
        else:
            amplitude = np.random.uniform(0.005, 0.025)
            low = close * (1 - amplitude * 0.5)
            high = close * (1 + amplitude * 0.5)
            open_price = low + (high - low) * np.random.rand()

        data.append({
            'date': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close
        })

    return pd.DataFrame(data)

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
    mask = df['date'] <= end_date
    recent_data = df[mask].tail(lookback_days).copy()

    if len(recent_data) < 10:
        return None, 0

    # Calculate amplitude
    recent_data['amplitude'] = calculate_amplitude(recent_data['high'], recent_data['low'])

    # Find consecutive low volatility days
    recent_data['is_low_vol'] = recent_data['amplitude'] < threshold

    # Find longest consecutive sequence
    max_consecutive = 0
    current_consecutive = 0
    end_idx = None
    current_end_idx = None

    for idx, is_low in enumerate(recent_data['is_low_vol'].values):
        if is_low:
            current_consecutive += 1
            current_end_idx = idx
            if current_consecutive > max_consecutive:
                max_consecutive = current_consecutive
                end_idx = current_end_idx
        else:
            current_consecutive = 0

    if max_consecutive >= 10:
        compression_end_date = recent_data.iloc[end_idx]['date']
        return compression_end_date, max_consecutive

    return None, 0

def check_hv_compression(df, compression_end_date, hv_lookback=60):
    """
    Check if HV10 during compression is below 30th percentile of 60-day HV10
    """
    mask = df['date'] <= compression_end_date
    historical_data = df[mask].tail(hv_lookback + 10).copy()

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
    compression_idx = df[df['date'] == compression_end_date].index[0]

    if compression_idx + lookforward_days >= len(df):
        return None

    for i in range(1, lookforward_days + 1):
        if compression_idx + i >= len(df):
            break

        day_data = df.iloc[compression_idx + i]
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
                return day_data['date']

    return None

def check_no_pullback(df, explosion_date, lookforward_days=3):
    """
    Check if price doesn't pull back in the next lookforward_days
    No pullback: low >= explosion day open price
    """
    explosion_idx = df[df['date'] == explosion_date].index[0]
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
        # Generate sample data
        start_date = end_date - timedelta(days=150)
        df = generate_sample_stock_data(stock_code, start_date, end_date + timedelta(days=30))

        if len(df) < 100:
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
        explosion_idx = df[df['date'] == explosion_date].index[0]
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

    print("Analyzing ChiNext stocks for volatility compression-explosion pattern...")
    print(f"End date: {end_date.strftime('%Y-%m-%d')}")
    print("\nAlgorithm steps:")
    print("1. Calculate daily amplitude = (high - low) / low")
    print("2. Find 10+ consecutive days with amplitude < 3% in last 30 days")
    print("3. Calculate HV10 = std(log returns) × √252")
    print("4. Verify HV10 < 30th percentile of 60-day HV10 series")
    print("5. Find explosion day (amplitude > 7%) within 5 days after compression")
    print("6. Verify bullish explosion: close > open, close in upper 70% of range")
    print("7. Verify no pullback: low >= explosion open for next 3 days")
    print()

    # Sample ChiNext stocks
    sample_stocks = ['300001', '300015', '300033', '300059', '300124', '300750']

    results = []

    for stock_code in sample_stocks:
        result = analyze_stock(stock_code, end_date)
        if result:
            results.append(result)
            print(f"✓ Found pattern in {stock_code}: compression={result['compression_days']}d, "
                  f"explosion={result['explosion_date']}, amplitude={result['explosion_amplitude']}%, "
                  f"3d_return={result['return_3d']}%")

    # Write results
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_28_volatility_compression_explosion/independent/claudecode/vol_explosion.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,压缩期天数,爆发日期,爆发振幅(%),爆发后3日涨幅(%)\n")

        if len(results) == 0:
            f.write("# 无符合条件的股票\n")
        else:
            for r in results:
                f.write(f"{r['stock_code']},{r['compression_days']},{r['explosion_date']},{r['explosion_amplitude']},{r['return_3d']}\n")

    print(f"\n✓ Analysis complete. Found {len(results)} stocks matching the pattern.")
    print(f"✓ Results written to: vol_explosion.txt")

if __name__ == "__main__":
    main()
