import pandas as pd
import numpy as np
from mootdx.quotes import Quotes
import warnings
warnings.filterwarnings('ignore')

def calculate_adx(df, period=14):
    """Calculate ADX (Average Directional Index) indicator"""
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    if len(df) < period + 1:
        return 0

    # Calculate True Range
    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    # Calculate directional movement
    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # Wilder smoothing
    def wilder_smooth(data, period):
        if len(data) < period:
            return np.zeros(len(data))
        smoothed = np.zeros(len(data))
        smoothed[period-1] = np.sum(data[:period])
        for i in range(period, len(data)):
            smoothed[i] = smoothed[i-1] - smoothed[i-1]/period + data[i]
        return smoothed

    atr = wilder_smooth(tr, period)
    plus_di_smooth = wilder_smooth(plus_dm, period)
    minus_di_smooth = wilder_smooth(minus_dm, period)

    # Calculate DI+ and DI-
    plus_di = 100 * plus_di_smooth / (atr + 1e-10)
    minus_di = 100 * minus_di_smooth / (atr + 1e-10)

    # Calculate DX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)

    # Calculate ADX (smoothed DX)
    adx = wilder_smooth(dx, period)

    return adx[-1] if len(adx) > 0 and adx[-1] > 0 else 0

def get_chinext_stocks():
    """Get ChiNext stock list (codes starting with 300)"""
    client = Quotes.factory(market='std')
    stocks = client.stocks(market=1)  # Shenzhen market

    # ChiNext stocks start with 300
    chinext = stocks[stocks['code'].str.startswith('300')].copy()

    # If no stocks found, try constructing list manually
    if len(chinext) == 0:
        print("Constructing ChiNext stock list manually...")
        codes = []
        for i in range(1, 2000):
            code = f"300{i:03d}" if i < 1000 else f"30{i:04d}"
            try:
                bars = client.bars(symbol=code, frequency=9, offset=5)
                if bars is not None and len(bars) > 0:
                    codes.append(code)
                    if len(codes) % 100 == 0:
                        print(f"Found {len(codes)} stocks...")
            except:
                pass

        chinext = pd.DataFrame({'code': codes})

    return chinext

def calculate_metrics(code, end_date='2024-12-09'):
    """Calculate metrics for a single stock"""
    client = Quotes.factory(market='std')

    try:
        # Get historical data (need at least 80 trading days)
        bars = client.bars(symbol=code, frequency=9, offset=150)

        if bars is None or len(bars) < 60:
            return None

        # Sort by date
        bars = bars.sort_index()

        # Filter to end_date
        bars = bars[bars.index <= end_date]

        if len(bars) < 60:
            return None

        # Get recent periods
        recent_60 = bars.tail(60)
        recent_20 = bars.tail(20)
        recent_5 = bars.tail(5)

        # 1. Price strength: 20-day return
        price_change_20d = (recent_20['close'].iloc[-1] / recent_20['close'].iloc[0] - 1) * 100

        # 2. Volume strength: turnover ratio (20d avg / 60d avg)
        turnover_20d = recent_20['vol'].mean()
        turnover_60d = recent_60['vol'].mean()
        turnover_ratio = turnover_20d / (turnover_60d + 1e-10)

        # 3. Trend strength: ADX(14)
        adx_value = calculate_adx(recent_60, period=14)

        # 4. Fund strength: 5-day volume change rate (proxy)
        vol_change_5d = (recent_5['vol'].mean() / recent_5['vol'].iloc[0] - 1) * 100 if recent_5['vol'].iloc[0] > 0 else 0

        return {
            'code': code,
            'price_change_20d': price_change_20d,
            'turnover_ratio': turnover_ratio,
            'adx': adx_value,
            'vol_change_5d': vol_change_5d
        }
    except Exception as e:
        return None

def get_pe(code):
    """Get PE ratio for a stock"""
    client = Quotes.factory(market='std')
    try:
        finance = client.financial(symbol=code)
        if finance is not None and len(finance) > 0 and 'pe' in finance.columns:
            return finance['pe'].iloc[0]
    except:
        pass
    return None

def main():
    print("Getting ChiNext stock list...")
    chinext_stocks = get_chinext_stocks()
    print(f"Found {len(chinext_stocks)} ChiNext stocks")

    # Calculate metrics for all stocks
    print("\nCalculating metrics...")
    results = []

    for idx, row in chinext_stocks.iterrows():
        code = row['code']

        # Get stock name if available
        name = row.get('name', '')

        # Skip ST stocks
        if 'ST' in str(name) or '*ST' in str(name):
            continue

        print(f"Processing {code}...", end='\r')

        metrics = calculate_metrics(code)
        if metrics is None:
            continue

        # Get PE ratio
        pe = get_pe(code)
        if pe is None or pe <= 0 or pe >= 60:
            continue

        metrics['name'] = name
        metrics['pe'] = pe
        results.append(metrics)

    print(f"\nCalculated metrics for {len(results)} stocks")

    if len(results) == 0:
        print("No stocks meet the criteria")
        return []

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Calculate percentile scores
    df['price_score'] = df['price_change_20d'].rank(pct=True) * 40
    df['turnover_score'] = df['turnover_ratio'].rank(pct=True) * 30
    df['trend_score'] = (df['adx'] / 100) * 20
    df['fund_score'] = df['vol_change_5d'].rank(pct=True) * 10

    # Calculate total score
    df['total_score'] = df['price_score'] + df['turnover_score'] + df['trend_score'] + df['fund_score']

    # Filter: total score > 75
    df = df[df['total_score'] > 75]

    print(f"After filtering (score > 75): {len(df)} stocks")

    if len(df) == 0:
        return []

    # Sort by total score and take top 15
    df = df.sort_values('total_score', ascending=False).head(15)

    return df

if __name__ == '__main__':
    result_df = main()

    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_30_composite_scoring/revised/claudecode/composite_score.txt'

    if len(result_df) == 0:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        print(f"\nNo qualifying stocks found. Result saved to {output_path}")
    else:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("股票代码,价格强度分,量能强度分,趋势强度分,资金强度分,总分,PE\n")
            for _, row in result_df.iterrows():
                f.write(f"{row['code']},{row['price_score']:.1f},{row['turnover_score']:.1f},"
                       f"{row['trend_score']:.1f},{row['fund_score']:.1f},{row['total_score']:.1f},{row['pe']:.1f}\n")

        print(f"\nTop 15 stocks saved to {output_path}")
        print("\nResults:")
        print(result_df[['code', 'name', 'price_score', 'turnover_score', 'trend_score', 'fund_score', 'total_score', 'pe']])
