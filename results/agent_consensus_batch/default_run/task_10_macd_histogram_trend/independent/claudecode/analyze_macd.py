import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_ema(data, period):
    """Calculate Exponential Moving Average"""
    return data.ewm(span=period, adjust=False).mean()

def calculate_macd(close_prices):
    """
    Calculate MACD indicator
    Returns: DIFF, DEA, histogram
    """
    ema12 = calculate_ema(close_prices, 12)
    ema26 = calculate_ema(close_prices, 26)
    diff = ema12 - ema26
    dea = calculate_ema(diff, 9)
    histogram = diff - dea
    return diff, dea, histogram

def check_consecutive_increase(histogram_values, start_idx, days=5):
    """
    Check if histogram increases consecutively for 'days' days after start_idx
    """
    if start_idx + days >= len(histogram_values):
        return False

    for i in range(start_idx + 1, start_idx + days + 1):
        if histogram_values[i] <= histogram_values[i - 1]:
            return False
    return True

def find_golden_cross_with_growth(histogram_values, window_days=60):
    """
    Find if histogram turns from negative to positive and then grows consecutively for 5+ days
    Returns True if found at least once in the window
    """
    # We analyze the last 'window_days' of the histogram
    if len(histogram_values) < window_days + 1:
        return False

    analysis_window = histogram_values[-window_days:]

    for i in range(len(analysis_window) - 1):
        # Check if histogram turns from negative to positive
        if analysis_window[i] < 0 and analysis_window[i + 1] > 0:
            # Check if it increases consecutively for 5 days after the golden cross
            if check_consecutive_increase(analysis_window, i + 1, days=5):
                return True

    return False

def main():
    print("开始分析创业板MACD柱状图趋势...")

    # Get ChiNext stock list (创业板代码以300、301开头)
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext_stocks = stock_info[stock_info['code'].str.startswith(('300', '301'))]
        print(f"获取到创业板股票数量: {len(chinext_stocks)}")
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return

    # Target date: 2024-12-31
    end_date = "20241231"

    # We need 90 trading days (60 for analysis + 30 for warmup)
    # Approximate start date (considering weekends and holidays, fetch more days)
    start_date = "20240801"  # About 5 months before

    qualified_stocks = []
    processed_count = 0
    error_count = 0

    for idx, row in chinext_stocks.iterrows():
        stock_code = row['code']
        stock_name = row['name']
        processed_count += 1

        if processed_count % 50 == 0:
            print(f"已处理 {processed_count}/{len(chinext_stocks)} 只股票...")

        try:
            # Get historical data
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                   start_date=start_date, end_date=end_date, adjust="qfq")

            if df is None or len(df) < 90:
                continue

            # Get closing prices
            close_prices = df['收盘'].astype(float)

            # Calculate MACD
            diff, dea, histogram = calculate_macd(close_prices)

            # Check if there's a golden cross with consecutive growth in the last 60 days
            if find_golden_cross_with_growth(histogram.values, window_days=60):
                qualified_stocks.append({
                    'code': stock_code,
                    'name': stock_name
                })
                print(f"✓ {stock_code} {stock_name} 符合条件")

        except Exception as e:
            error_count += 1
            if error_count <= 5:  # Only print first few errors
                print(f"处理 {stock_code} 时出错: {e}")
            continue

    # Count unique stocks (each stock counted only once)
    unique_count = len(qualified_stocks)

    print(f"\n分析完成！")
    print(f"总处理股票数: {processed_count}")
    print(f"符合条件的股票总数: {unique_count}")

    # Write result to file
    result_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_10_macd_histogram_trend/independent/claudecode/macd_strength_count.txt"
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(f"符合条件的股票总数: {unique_count}\n")

    print(f"\n结果已写入: macd_strength_count.txt")

if __name__ == "__main__":
    main()
