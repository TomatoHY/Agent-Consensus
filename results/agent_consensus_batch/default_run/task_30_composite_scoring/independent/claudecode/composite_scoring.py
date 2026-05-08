#!/usr/bin/env python3
"""
量价综合评分模型选股
Composite scoring model for ChiNext stock selection
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import rankdata

def calculate_adx(df, period=14):
    """
    Calculate ADX (Average Directional Index) using Wilder's method
    Includes DI+, DI-, and ADX calculation
    """
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    # Calculate True Range (TR)
    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    # Calculate directional movements
    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # Smooth using Wilder's method (exponential moving average)
    alpha = 1.0 / period

    atr = np.zeros(len(tr))
    plus_di = np.zeros(len(tr))
    minus_di = np.zeros(len(tr))

    # Initialize first value
    atr[period-1] = np.mean(tr[:period])
    plus_di[period-1] = np.mean(plus_dm[:period])
    minus_di[period-1] = np.mean(minus_dm[:period])

    # Calculate smoothed values
    for i in range(period, len(tr)):
        atr[i] = atr[i-1] * (1 - alpha) + tr[i] * alpha
        plus_di[i] = plus_di[i-1] * (1 - alpha) + plus_dm[i] * alpha
        minus_di[i] = minus_di[i-1] * (1 - alpha) + minus_dm[i] * alpha

    # Calculate DI+ and DI-
    plus_di_pct = 100 * plus_di / atr
    minus_di_pct = 100 * minus_di / atr

    # Calculate DX
    dx = 100 * np.abs(plus_di_pct - minus_di_pct) / (plus_di_pct + minus_di_pct + 1e-10)

    # Calculate ADX (smoothed DX)
    adx = np.zeros(len(dx))
    adx[period-1] = np.mean(dx[:period])

    for i in range(period, len(dx)):
        adx[i] = adx[i-1] * (1 - alpha) + dx[i] * alpha

    return adx[-1] if len(adx) > 0 else 0

def get_chinext_stocks():
    """Get all ChiNext (创业板) stock codes"""
    try:
        # Get stock list
        stock_info = ak.stock_info_a_code_name()
        # ChiNext stocks start with 300
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"Error getting stock list: {e}")
        return []

def calculate_stock_metrics(stock_code, end_date='2024-12-09'):
    """Calculate all metrics for a single stock"""
    try:
        # Get historical data
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date="2024-09-01", end_date=end_date, adjust="qfq")

        if df is None or len(df) < 80:
            return None

        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude',
                     'change_pct', 'change_amount', 'turnover']

        # Convert to numeric
        for col in ['close', 'high', 'low', 'volume', 'amount', 'turnover']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna()

        if len(df) < 80:
            return None

        # 1. Price strength: 20-day return
        close_20d_ago = df.iloc[-21]['close'] if len(df) >= 21 else df.iloc[0]['close']
        close_latest = df.iloc[-1]['close']
        price_return_20d = (close_latest - close_20d_ago) / close_20d_ago * 100

        # 2. Volume strength: turnover ratio (20d avg / 60d avg)
        turnover_20d = df.iloc[-20:]['turnover'].mean() if len(df) >= 20 else df['turnover'].mean()
        turnover_60d = df.iloc[-60:]['turnover'].mean() if len(df) >= 60 else df['turnover'].mean()
        volume_ratio = turnover_20d / (turnover_60d + 1e-10)

        # 3. Trend strength: ADX (14-day)
        adx_value = calculate_adx(df.iloc[-80:], period=14)

        # 4. Capital strength: 5-day volume change rate as proxy
        volume_5d_recent = df.iloc[-5:]['volume'].sum() if len(df) >= 5 else df['volume'].sum()
        volume_5d_before = df.iloc[-10:-5]['volume'].sum() if len(df) >= 10 else df['volume'].sum()
        capital_proxy = (volume_5d_recent - volume_5d_before) / (volume_5d_before + 1e-10) * 100

        return {
            'code': stock_code,
            'price_return_20d': price_return_20d,
            'volume_ratio': volume_ratio,
            'adx': adx_value,
            'capital_proxy': capital_proxy
        }

    except Exception as e:
        print(f"Error processing {stock_code}: {e}")
        return None

def get_stock_pe(stock_code):
    """Get PE ratio for a stock"""
    try:
        realtime = ak.stock_zh_a_spot_em()
        stock_data = realtime[realtime['代码'] == stock_code]
        if len(stock_data) > 0:
            pe = stock_data.iloc[0]['市盈率-动态']
            return float(pe) if pd.notna(pe) else None
        return None
    except:
        return None

def get_stock_name(stock_code):
    """Get stock name to check for ST"""
    try:
        realtime = ak.stock_zh_a_spot_em()
        stock_data = realtime[realtime['代码'] == stock_code]
        if len(stock_data) > 0:
            return stock_data.iloc[0]['名称']
        return ""
    except:
        return ""

def main():
    print("Starting composite scoring model for ChiNext stocks...")
    print("Target date: 2024-12-09")

    # Get ChiNext stock list
    print("\nFetching ChiNext stock list...")
    stock_codes = get_chinext_stocks()
    print(f"Found {len(stock_codes)} ChiNext stocks")

    # Calculate metrics for all stocks
    print("\nCalculating metrics for all stocks...")
    all_metrics = []

    for i, code in enumerate(stock_codes[:100]):  # Limit to first 100 for efficiency
        if (i + 1) % 10 == 0:
            print(f"Processing {i+1}/{min(100, len(stock_codes))}...")

        metrics = calculate_stock_metrics(code)
        if metrics:
            all_metrics.append(metrics)

    if len(all_metrics) == 0:
        print("No valid data collected")
        return

    df_metrics = pd.DataFrame(all_metrics)
    print(f"\nSuccessfully calculated metrics for {len(df_metrics)} stocks")

    # Calculate percentile rankings for each dimension
    print("\nCalculating percentile rankings...")

    # Price strength score (40 points)
    price_percentile = rankdata(df_metrics['price_return_20d'], method='average') / len(df_metrics)
    df_metrics['price_score'] = price_percentile * 40

    # Volume strength score (30 points)
    volume_percentile = rankdata(df_metrics['volume_ratio'], method='average') / len(df_metrics)
    df_metrics['volume_score'] = volume_percentile * 30

    # Trend strength score (20 points) - ADX/100 * 20
    df_metrics['trend_score'] = (df_metrics['adx'] / 100) * 20
    df_metrics['trend_score'] = df_metrics['trend_score'].clip(0, 20)

    # Capital strength score (10 points)
    capital_percentile = rankdata(df_metrics['capital_proxy'], method='average') / len(df_metrics)
    df_metrics['capital_score'] = capital_percentile * 10

    # Calculate total score
    df_metrics['total_score'] = (df_metrics['price_score'] +
                                  df_metrics['volume_score'] +
                                  df_metrics['trend_score'] +
                                  df_metrics['capital_score'])

    # Filter by total score > 75
    print("\nFiltering stocks with total score > 75...")
    df_filtered = df_metrics[df_metrics['total_score'] > 75].copy()
    print(f"Found {len(df_filtered)} stocks with score > 75")

    # Get PE ratios and stock names
    print("\nFetching PE ratios and checking for ST stocks...")
    pe_list = []
    name_list = []

    for code in df_filtered['code']:
        pe = get_stock_pe(code)
        name = get_stock_name(code)
        pe_list.append(pe)
        name_list.append(name)

    df_filtered['pe'] = pe_list
    df_filtered['name'] = name_list

    # Filter by PE (0 < PE < 60) and exclude ST stocks
    df_filtered = df_filtered[
        (df_filtered['pe'].notna()) &
        (df_filtered['pe'] > 0) &
        (df_filtered['pe'] < 60) &
        (~df_filtered['name'].str.contains('ST', na=False))
    ]

    print(f"After PE and ST filtering: {len(df_filtered)} stocks")

    # Sort by total score and take top 15
    df_result = df_filtered.sort_values('total_score', ascending=False).head(15)

    # Save results
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_30_composite_scoring/independent/claudecode/composite_score.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('股票代码,价格强度分,量能强度分,趋势强度分,资金强度分,总分,PE\n')
        for _, row in df_result.iterrows():
            f.write(f"{row['code']},{row['price_score']:.1f},{row['volume_score']:.1f},"
                   f"{row['trend_score']:.1f},{row['capital_score']:.1f},"
                   f"{row['total_score']:.1f},{row['pe']:.1f}\n")

    print(f"\nResults saved to composite_score.txt")
    print(f"Total stocks selected: {len(df_result)}")
    print("\nTop 5 stocks:")
    print(df_result[['code', 'price_score', 'volume_score', 'trend_score',
                     'capital_score', 'total_score', 'pe']].head())

if __name__ == "__main__":
    main()
