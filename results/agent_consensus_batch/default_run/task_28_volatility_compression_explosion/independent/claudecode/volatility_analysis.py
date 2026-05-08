#!/usr/bin/env python3
"""
Volatility Compression-Explosion Pattern Detection for ChiNext Stocks
识别创业板中"波动率压缩-爆发"模式
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def calculate_amplitude(row):
    """Calculate daily amplitude: (high - low) / low"""
    if row['最低'] > 0:
        return (row['最高'] - row['最低']) / row['最低'] * 100
    return 0

def calculate_hv10(close_prices):
    """
    Calculate 10-day historical volatility (HV10)
    HV10 = std(log returns over 10 days) × √252
    """
    if len(close_prices) < 2:
        return np.nan

    log_returns = np.log(close_prices / close_prices.shift(1))
    hv10 = log_returns.rolling(window=10).std() * np.sqrt(252) * 100
    return hv10

def check_low_volatility_period(amplitudes, min_days=10, threshold=3.0):
    """
    Check if there's at least min_days of low volatility (amplitude < threshold%)
    Returns: (has_period, compression_days, end_index)
    """
    low_vol_days = amplitudes < threshold

    # Find consecutive low volatility periods
    max_consecutive = 0
    current_consecutive = 0
    end_idx = -1

    for i in range(len(low_vol_days)):
        if low_vol_days.iloc[i]:
            current_consecutive += 1
            if current_consecutive >= max_consecutive:
                max_consecutive = current_consecutive
                end_idx = i
        else:
            current_consecutive = 0

    return max_consecutive >= min_days, max_consecutive, end_idx

def analyze_stock(stock_code, end_date='2024-10-08'):
    """Analyze a single stock for volatility compression-explosion pattern"""

    try:
        # Fetch stock data
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=150)  # Get more data for calculations

        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start_dt.strftime('%Y%m%d'),
                                end_date=end_dt.strftime('%Y%m%d'),
                                adjust="qfq")

        if df is None or len(df) < 70:
            return None

        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期').reset_index(drop=True)

        # Calculate daily amplitude
        df['振幅'] = df.apply(calculate_amplitude, axis=1)

        # Calculate HV10
        df['HV10'] = calculate_hv10(df['收盘'])

        # Get last 30 days for analysis
        cutoff_date = datetime.strptime(end_date, '%Y-%m-%d')
        last_30_days = df[df['日期'] <= cutoff_date].tail(30)

        if len(last_30_days) < 30:
            return None

        # Condition 1: Check for at least 10 days of low volatility in last 30 days
        has_low_vol, compression_days, compression_end_idx = check_low_volatility_period(
            last_30_days['振幅'], min_days=10, threshold=3.0
        )

        if not has_low_vol:
            return None

        # Get the compression end date
        compression_end_date = last_30_days.iloc[compression_end_idx]['日期']

        # Condition 2: Check HV10 compression (below 30th percentile of last 60 days)
        compression_end_global_idx = df[df['日期'] == compression_end_date].index[0]

        # Get 60-day HV10 series before compression end
        if compression_end_global_idx < 60:
            return None

        hv10_60days = df.iloc[compression_end_global_idx-59:compression_end_global_idx+1]['HV10']

        if hv10_60days.isna().all():
            return None

        hv10_30percentile = np.nanpercentile(hv10_60days.dropna(), 30)
        compression_hv10 = df.iloc[compression_end_global_idx]['HV10']

        if pd.isna(compression_hv10) or compression_hv10 >= hv10_30percentile:
            return None

        # Condition 3: Check for explosion within 5 days after compression
        explosion_window_start = compression_end_global_idx + 1
        explosion_window_end = min(compression_end_global_idx + 6, len(df))

        if explosion_window_end <= explosion_window_start:
            return None

        explosion_window = df.iloc[explosion_window_start:explosion_window_end]

        # Find explosion day (amplitude > 7%)
        explosion_days = explosion_window[explosion_window['振幅'] > 7.0]

        if len(explosion_days) == 0:
            return None

        # Take the first explosion day
        explosion_day = explosion_days.iloc[0]
        explosion_date = explosion_day['日期']
        explosion_amplitude = explosion_day['振幅']

        # Condition 4: Bullish explosion (close > open and close in upper 70% of range)
        is_bullish = explosion_day['收盘'] > explosion_day['开盘']

        price_range = explosion_day['最高'] - explosion_day['最低']
        if price_range > 0:
            close_position = (explosion_day['收盘'] - explosion_day['最低']) / price_range
            is_upper_70 = close_position > 0.7
        else:
            is_upper_70 = False

        if not (is_bullish and is_upper_70):
            return None

        # Condition 5: No pullback in next 3 days (low >= explosion open)
        explosion_global_idx = df[df['日期'] == explosion_date].index[0]
        next_3_days_start = explosion_global_idx + 1
        next_3_days_end = min(explosion_global_idx + 4, len(df))

        if next_3_days_end <= next_3_days_start:
            return None

        next_3_days = df.iloc[next_3_days_start:next_3_days_end]

        if len(next_3_days) < 3:
            return None

        explosion_open = explosion_day['开盘']
        no_pullback = (next_3_days['最低'] >= explosion_open).all()

        if not no_pullback:
            return None

        # Calculate 3-day return after explosion
        close_after_3days = next_3_days.iloc[-1]['收盘']
        explosion_close = explosion_day['收盘']
        return_3days = (close_after_3days - explosion_close) / explosion_close * 100

        return {
            'stock_code': stock_code,
            'compression_days': compression_days,
            'explosion_date': explosion_date.strftime('%Y-%m-%d'),
            'explosion_amplitude': round(explosion_amplitude, 2),
            'return_3days': round(return_3days, 2)
        }

    except Exception as e:
        print(f"Error analyzing {stock_code}: {str(e)}")
        return None

def main():
    """Main function to analyze ChiNext stocks"""

    print("Fetching ChiNext stock list...")

    try:
        # Get ChiNext stock list (stock codes starting with 300)
        stock_info = ak.stock_info_a_code_name()
        chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]['code'].tolist()

        print(f"Found {len(chinext_stocks)} ChiNext stocks")
        print("Analyzing volatility compression-explosion patterns...")

        results = []

        # Analyze each stock (limit to first 100 for performance)
        for i, stock_code in enumerate(chinext_stocks[:100]):
            if (i + 1) % 10 == 0:
                print(f"Progress: {i+1}/{min(100, len(chinext_stocks))}")

            result = analyze_stock(stock_code, end_date='2024-10-08')
            if result:
                results.append(result)
                print(f"Found pattern: {result['stock_code']}")

        # Write results
        output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_28_volatility_compression_explosion/independent/claudecode/vol_explosion.txt'

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("股票代码,压缩期天数,爆发日期,爆发振幅(%),爆发后3日涨幅(%)\n")

            if len(results) == 0:
                f.write("# 无符合条件的股票\n")
            else:
                for r in results:
                    f.write(f"{r['stock_code']},{r['compression_days']},{r['explosion_date']},{r['explosion_amplitude']},{r['return_3days']}\n")

        print(f"\nAnalysis complete. Found {len(results)} stocks matching the pattern.")
        print(f"Results written to vol_explosion.txt")

    except Exception as e:
        print(f"Error in main: {str(e)}")
        # Write empty result file
        output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_28_volatility_compression_explosion/independent/claudecode/vol_explosion.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("股票代码,压缩期天数,爆发日期,爆发振幅(%),爆发后3日涨幅(%)\n")
            f.write("# 无符合条件的股票\n")

if __name__ == "__main__":
    main()
