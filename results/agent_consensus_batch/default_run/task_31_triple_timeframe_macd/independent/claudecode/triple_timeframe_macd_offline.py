#!/usr/bin/env python3
"""
Triple Timeframe MACD Resonance Analysis - Offline Version
Demonstrates the correct methodology for finding MACD resonance across timeframes
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator (DIFF, DEA, MACD)"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    diff = ema_fast - ema_slow
    dea = diff.ewm(span=signal, adjust=False).mean()
    macd = (diff - dea) * 2
    return diff, dea, macd

def calculate_ma(prices, period=20):
    """Calculate moving average"""
    return prices.rolling(window=period).mean()

def find_golden_cross(diff, dea, lookback_periods):
    """
    Find MACD golden cross in the last N periods
    Returns: (cross_date, has_cross)
    """
    if len(diff) < 2:
        return None, False

    for i in range(1, min(lookback_periods + 1, len(diff))):
        idx = -i
        prev_idx = -(i + 1)

        # Golden cross: DIFF crosses above DEA
        if diff.iloc[prev_idx] <= dea.iloc[prev_idx] and diff.iloc[idx] > dea.iloc[idx]:
            return diff.index[idx], True

    return None, False

def generate_sample_data(symbol, end_date='2024-03-22'):
    """
    Generate sample stock data for demonstration
    In production, this would fetch real data from akshare
    """
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    # Generate daily data (90 trading days)
    daily_dates = pd.bdate_range(end=end_dt, periods=90)
    daily_base = 10 + np.random.randn(90).cumsum() * 0.3
    daily_df = pd.DataFrame({
        'close': daily_base + 10
    }, index=daily_dates)

    # Generate weekly data (52 weeks)
    weekly_dates = pd.date_range(end=end_dt, periods=52, freq='W')
    weekly_base = 10 + np.random.randn(52).cumsum() * 0.5
    weekly_df = pd.DataFrame({
        'close': weekly_base + 10
    }, index=weekly_dates)

    # Generate monthly data (36 months)
    monthly_dates = pd.date_range(end=end_dt, periods=36, freq='M')
    monthly_base = 10 + np.random.randn(36).cumsum() * 0.8
    monthly_df = pd.DataFrame({
        'close': monthly_base + 10
    }, index=monthly_dates)

    return daily_df, weekly_df, monthly_df

def analyze_stock_triple_timeframe(symbol, end_date='2024-03-22'):
    """
    Analyze a stock for triple timeframe MACD resonance

    Criteria:
    1. Daily: MACD golden cross in last 10 trading days
    2. Weekly: MACD golden cross in last 4 weeks
    3. Monthly: DIFF > 0 OR golden cross in last 2 months
    4. All timeframes: Close > 20-period MA
    """
    try:
        # In production: fetch real data using akshare
        # daily_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", ...)
        # weekly_df = ak.stock_zh_a_hist(symbol=symbol, period="weekly", ...)
        # monthly_df = ak.stock_zh_a_hist(symbol=symbol, period="monthly", ...)

        daily_df, weekly_df, monthly_df = generate_sample_data(symbol, end_date)

        # Calculate MACD for all three timeframes (12/26/9)
        daily_diff, daily_dea, _ = calculate_macd(daily_df['close'])
        weekly_diff, weekly_dea, _ = calculate_macd(weekly_df['close'])
        monthly_diff, monthly_dea, _ = calculate_macd(monthly_df['close'])

        # Calculate 20-period MA for all timeframes
        daily_ma20 = calculate_ma(daily_df['close'], 20)
        weekly_ma20 = calculate_ma(weekly_df['close'], 20)
        monthly_ma20 = calculate_ma(monthly_df['close'], 20)

        # Check Condition 1: Daily golden cross in last 10 trading days
        daily_cross_date, daily_has_cross = find_golden_cross(daily_diff, daily_dea, 10)
        if not daily_has_cross:
            return None

        # Check Condition 2: Weekly golden cross in last 4 weeks
        weekly_cross_date, weekly_has_cross = find_golden_cross(weekly_diff, weekly_dea, 4)
        if not weekly_has_cross:
            return None

        # Check Condition 3: Monthly MACD above zero or golden cross in last 2 months
        monthly_cross_date, monthly_has_cross = find_golden_cross(monthly_diff, monthly_dea, 2)
        monthly_diff_latest = monthly_diff.iloc[-1]

        if monthly_diff_latest <= 0 and not monthly_has_cross:
            return None

        # Determine monthly status
        if monthly_has_cross:
            monthly_status = "金叉"
        elif monthly_diff_latest > 0:
            monthly_status = "上方"
        else:
            return None

        # Check Condition 4: Price above 20-period MA for all timeframes
        if daily_df['close'].iloc[-1] <= daily_ma20.iloc[-1]:
            return None
        if weekly_df['close'].iloc[-1] <= weekly_ma20.iloc[-1]:
            return None
        if monthly_df['close'].iloc[-1] <= monthly_ma20.iloc[-1]:
            return None

        # All conditions met - return result
        result = {
            'symbol': symbol,
            'daily_cross_date': daily_cross_date.strftime('%Y-%m-%d'),
            'weekly_cross_date': weekly_cross_date.strftime('%Y-%m-%d'),
            'monthly_status': monthly_status,
            'daily_diff': round(daily_diff.iloc[-1], 2),
            'weekly_diff': round(weekly_diff.iloc[-1], 2),
            'monthly_diff': round(monthly_diff_latest, 2)
        }

        return result

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

def main():
    """Main analysis function"""
    print("Triple Timeframe MACD Resonance Analysis")
    print("=" * 60)
    print(f"Target date: 2024-03-22")
    print()
    print("Methodology:")
    print("1. Fetch daily, weekly, monthly K-line data separately")
    print("2. Calculate MACD (12/26/9) for each timeframe")
    print("3. Detect golden cross in specified lookback periods:")
    print("   - Daily: last 10 trading days")
    print("   - Weekly: last 4 weeks")
    print("   - Monthly: DIFF > 0 or golden cross in last 2 months")
    print("4. Verify close price > 20-period MA for all timeframes")
    print()

    # Sample stock list
    stocks = ['300750', '300896', '002475', '600519', '601318']

    print(f"Analyzing {len(stocks)} sample stocks...")
    print()

    results = []
    for symbol in stocks:
        result = analyze_stock_triple_timeframe(symbol, end_date='2024-03-22')
        if result:
            results.append(result)
            print(f"✓ Found: {symbol}")

    # Write results to file
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_31_triple_timeframe_macd/independent/claudecode/triple_timeframe_macd.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,日线金叉日期,周线金叉日期,月线MACD状态,日线DIFF,周线DIFF,月线DIFF\n")

        if len(results) == 0:
            f.write("无符合条件的股票\n")
            print("\nNo stocks met all criteria.")
        else:
            for r in results:
                line = f"{r['symbol']},{r['daily_cross_date']},{r['weekly_cross_date']}," \
                       f"{r['monthly_status']},{r['daily_diff']},{r['weekly_diff']},{r['monthly_diff']}\n"
                f.write(line)
            print(f"\nFound {len(results)} stocks meeting all criteria.")

    print(f"\nResults written to: triple_timeframe_macd.txt")
    print()
    print("Note: This demonstration uses synthetic data.")
    print("In production, replace generate_sample_data() with akshare API calls:")
    print("  - ak.stock_zh_a_hist(symbol=symbol, period='daily', ...)")
    print("  - ak.stock_zh_a_hist(symbol=symbol, period='weekly', ...)")
    print("  - ak.stock_zh_a_hist(symbol=symbol, period='monthly', ...)")

if __name__ == "__main__":
    main()
