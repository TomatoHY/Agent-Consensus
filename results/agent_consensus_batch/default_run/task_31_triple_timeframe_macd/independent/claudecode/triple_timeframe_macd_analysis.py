#!/usr/bin/env python3
"""
Triple Timeframe MACD Resonance Analysis
Finds stocks with MACD golden cross across daily, weekly, and monthly timeframes
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def calculate_macd(df, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    diff = ema_fast - ema_slow
    dea = diff.ewm(span=signal, adjust=False).mean()
    macd = (diff - dea) * 2
    return diff, dea, macd

def calculate_ma(df, period=20):
    """Calculate moving average"""
    return df['close'].rolling(window=period).mean()

def find_golden_cross(diff, dea, lookback_periods):
    """Find MACD golden cross in the last N periods"""
    if len(diff) < 2:
        return None, False

    # Check last lookback_periods for golden cross
    for i in range(1, min(lookback_periods + 1, len(diff))):
        idx = -i
        prev_idx = -(i + 1)

        if diff.iloc[prev_idx] <= dea.iloc[prev_idx] and diff.iloc[idx] > dea.iloc[idx]:
            return diff.index[idx], True

    return None, False

def get_stock_list():
    """Get A-share stock list"""
    # Use a predefined list of common stocks
    stocks = [
        # Shanghai stocks
        '600000', '600016', '600019', '600028', '600030', '600036', '600048', '600050',
        '600104', '600111', '600276', '600309', '600519', '600585', '600690', '600887',
        '600900', '601012', '601088', '601166', '601169', '601288', '601318', '601328',
        '601398', '601601', '601628', '601668', '601688', '601818', '601857', '601888',
        '601899', '601919', '601939', '601988', '601989', '603259', '603288', '603501',
        # Shenzhen stocks
        '000001', '000002', '000063', '000066', '000100', '000333', '000338', '000425',
        '000538', '000568', '000625', '000651', '000661', '000725', '000768', '000858',
        '000876', '000895', '000938', '001979', '002001', '002027', '002049', '002050',
        '002142', '002230', '002236', '002241', '002252', '002304', '002311', '002352',
        '002371', '002415', '002460', '002475', '002493', '002594', '002601', '002714',
        # ChiNext stocks
        '300014', '300015', '300033', '300059', '300122', '300124', '300142', '300144',
        '300274', '300347', '300408', '300413', '300433', '300450', '300496', '300498',
        '300595', '300601', '300628', '300661', '300750', '300759', '300760', '300896'
    ]
    return stocks

def analyze_stock(symbol, end_date='2024-03-22'):
    """Analyze a single stock for triple timeframe MACD resonance"""
    try:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        # Get daily data (90 days)
        daily_start = (end_dt - timedelta(days=150)).strftime('%Y%m%d')
        daily_end = end_dt.strftime('%Y%m%d')
        daily_df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                       start_date=daily_start, end_date=daily_end, adjust="qfq")

        if daily_df is None or len(daily_df) < 50:
            return None

        daily_df['date'] = pd.to_datetime(daily_df['日期'])
        daily_df['close'] = daily_df['收盘'].astype(float)
        daily_df = daily_df.set_index('date')

        # Get weekly data (52 weeks)
        weekly_start = (end_dt - timedelta(days=400)).strftime('%Y%m%d')
        weekly_df = ak.stock_zh_a_hist(symbol=symbol, period="weekly",
                                        start_date=weekly_start, end_date=daily_end, adjust="qfq")

        if weekly_df is None or len(weekly_df) < 30:
            return None

        weekly_df['date'] = pd.to_datetime(weekly_df['日期'])
        weekly_df['close'] = weekly_df['收盘'].astype(float)
        weekly_df = weekly_df.set_index('date')

        # Get monthly data (36 months)
        monthly_start = (end_dt - timedelta(days=1200)).strftime('%Y%m%d')
        monthly_df = ak.stock_zh_a_hist(symbol=symbol, period="monthly",
                                         start_date=monthly_start, end_date=daily_end, adjust="qfq")

        if monthly_df is None or len(monthly_df) < 20:
            return None

        monthly_df['date'] = pd.to_datetime(monthly_df['日期'])
        monthly_df['close'] = monthly_df['收盘'].astype(float)
        monthly_df = monthly_df.set_index('date')

        # Calculate MACD for all three timeframes
        daily_diff, daily_dea, _ = calculate_macd(daily_df)
        weekly_diff, weekly_dea, _ = calculate_macd(weekly_df)
        monthly_diff, monthly_dea, _ = calculate_macd(monthly_df)

        # Calculate 20-period MA for all timeframes
        daily_ma20 = calculate_ma(daily_df, 20)
        weekly_ma20 = calculate_ma(weekly_df, 20)
        monthly_ma20 = calculate_ma(monthly_df, 20)

        # Check conditions
        # 1. Daily golden cross in last 10 trading days
        daily_cross_date, daily_has_cross = find_golden_cross(daily_diff, daily_dea, 10)
        if not daily_has_cross:
            return None

        # 2. Weekly golden cross in last 4 weeks
        weekly_cross_date, weekly_has_cross = find_golden_cross(weekly_diff, weekly_dea, 4)
        if not weekly_has_cross:
            return None

        # 3. Monthly MACD above zero or golden cross in last 2 months
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

        # 4. Price above 20-period MA for all timeframes
        daily_close_latest = daily_df['close'].iloc[-1]
        weekly_close_latest = weekly_df['close'].iloc[-1]
        monthly_close_latest = monthly_df['close'].iloc[-1]

        daily_ma20_latest = daily_ma20.iloc[-1]
        weekly_ma20_latest = weekly_ma20.iloc[-1]
        monthly_ma20_latest = monthly_ma20.iloc[-1]

        if daily_close_latest <= daily_ma20_latest:
            return None
        if weekly_close_latest <= weekly_ma20_latest:
            return None
        if monthly_close_latest <= monthly_ma20_latest:
            return None

        # All conditions met
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
    """Main function"""
    print("Starting triple timeframe MACD resonance analysis...")
    print(f"Target date: 2024-03-22")

    # Get stock list
    stocks = get_stock_list()
    print(f"Analyzing {len(stocks)} stocks...")

    results = []
    for i, symbol in enumerate(stocks):
        if (i + 1) % 10 == 0:
            print(f"Progress: {i + 1}/{len(stocks)}")

        result = analyze_stock(symbol, end_date='2024-03-22')
        if result:
            results.append(result)
            print(f"Found: {symbol}")

    # Write results
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_31_triple_timeframe_macd/independent/claudecode/triple_timeframe_macd.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,日线金叉日期,周线金叉日期,月线MACD状态,日线DIFF,周线DIFF,月线DIFF\n")

        if len(results) == 0:
            f.write("无符合条件的股票\n")
        else:
            for r in results:
                f.write(f"{r['symbol']},{r['daily_cross_date']},{r['weekly_cross_date']},"
                       f"{r['monthly_status']},{r['daily_diff']},{r['weekly_diff']},{r['monthly_diff']}\n")

    print(f"\nAnalysis complete. Found {len(results)} stocks.")
    print(f"Results written to: {output_file}")

if __name__ == "__main__":
    main()
