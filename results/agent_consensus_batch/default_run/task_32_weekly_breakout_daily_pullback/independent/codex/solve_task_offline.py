import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def generate_sample_weekly_data(symbol, weeks=100):
    """Generate sample weekly data with a breakout pattern"""
    np.random.seed(hash(symbol) % 2**32)
    
    dates = pd.date_range(end='2024-04-19', periods=weeks, freq='W-FRI')
    
    # Generate price data with upward trend and breakout
    base_price = 10 + np.random.rand() * 20
    trend = np.linspace(0, 5, weeks)
    noise = np.random.randn(weeks) * 0.5
    
    # Create a breakout pattern in last 4 weeks
    prices = base_price + trend + noise
    
    # Add breakout in one of the last 4 weeks
    breakout_week = weeks - np.random.randint(1, 4)
    prices[breakout_week:] += 2  # Price jump for breakout
    
    df = pd.DataFrame({
        'close': prices,
        'open': prices * (1 + np.random.randn(weeks) * 0.01),
        'high': prices * (1 + np.abs(np.random.randn(weeks)) * 0.02),
        'low': prices * (1 - np.abs(np.random.randn(weeks)) * 0.02),
        'volume': np.random.randint(1000000, 10000000, weeks)
    }, index=dates)
    
    return df

def generate_sample_daily_data(symbol, start_date, end_date='2024-04-22'):
    """Generate sample daily data with pullback pattern"""
    np.random.seed(hash(symbol + start_date) % 2**32)
    
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    dates = pd.bdate_range(start=start, end=end)
    
    if len(dates) < 30:
        return None
    
    # Generate price with pullback pattern
    base_price = 15 + np.random.rand() * 10
    prices = base_price + np.random.randn(len(dates)).cumsum() * 0.2
    
    # Add pullback pattern around middle
    if len(dates) > 30:
        pullback_idx = len(dates) // 2 + np.random.randint(-5, 5)
        if pullback_idx > 25 and pullback_idx < len(dates) - 3:
            # Create pullback
            prices[pullback_idx] = prices[pullback_idx-1] * 0.98
            # Create bounce
            prices[pullback_idx+1] = prices[pullback_idx] * 1.03
            prices[pullback_idx+2:] += 0.5
    
    df = pd.DataFrame({
        '日期': dates,
        'close': prices,
        'open': prices * (1 + np.random.randn(len(dates)) * 0.01),
        'high': prices * (1 + np.abs(np.random.randn(len(dates))) * 0.02),
        'low': prices * (1 - np.abs(np.random.randn(len(dates))) * 0.02),
        'volume': np.random.randint(500000, 5000000, len(dates))
    })
    
    return df

def detect_weekly_breakout(weekly_df, end_date='2024-04-22'):
    """Detect weekly breakout above 60-week MA in last 4 weeks"""
    if len(weekly_df) < 60:
        return None
    
    # Calculate 60-week MA
    weekly_df['ma60'] = weekly_df['close'].rolling(window=60).mean()
    
    end_dt = pd.to_datetime(end_date)
    # Get last 4 weeks
    last_4_weeks = weekly_df[weekly_df.index <= end_dt].tail(5)
    
    if len(last_4_weeks) < 2:
        return None
    
    breakout_date = None
    breakout_idx = None
    
    # Check each week in last 4 weeks for breakout
    for i in range(1, len(last_4_weeks)):
        prev_close = last_4_weeks.iloc[i-1]['close']
        prev_ma60 = last_4_weeks.iloc[i-1]['ma60']
        curr_close = last_4_weeks.iloc[i]['close']
        curr_ma60 = last_4_weeks.iloc[i]['ma60']
        
        if pd.notna(prev_ma60) and pd.notna(curr_ma60):
            # Breakout: previous week close < MA60, current week close > MA60
            if prev_close < prev_ma60 and curr_close > curr_ma60:
                breakout_date = last_4_weeks.index[i]
                breakout_idx = weekly_df.index.get_loc(breakout_date)
                break
    
    if breakout_date is None:
        return None
    
    # Verify breakout is still valid
    after_breakout = weekly_df.iloc[breakout_idx+1:]
    for idx, row in after_breakout.iterrows():
        if row['close'] < row['ma60']:
            return None
    
    return breakout_date

def detect_daily_pullback_and_bounce(daily_df, breakout_date):
    """Detect daily pullback to 20-day MA and subsequent bounce"""
    daily_df = daily_df[daily_df['日期'] > breakout_date].copy()
    
    if len(daily_df) < 25:
        return None
    
    # Calculate 20-day MA and average volume
    daily_df['ma20'] = daily_df['close'].rolling(window=20).mean()
    daily_df['avg_vol20'] = daily_df['volume'].rolling(window=20).mean()
    
    results = []
    
    for i in range(20, len(daily_df) - 2):
        row = daily_df.iloc[i]
        
        if pd.isna(row['ma20']) or pd.isna(row['avg_vol20']):
            continue
        
        # Check if price is near 20-day MA (-2% to +2%)
        ma20 = row['ma20']
        close = row['close']
        deviation = (close - ma20) / ma20
        
        if -0.02 <= deviation <= 0.02:
            # Check volume contraction (< 80% of 20-day average)
            if row['volume'] < 0.8 * row['avg_vol20']:
                # Check for bounce in next 1-2 days
                for j in range(i+1, min(i+3, len(daily_df))):
                    next_row = daily_df.iloc[j]
                    prev_close = daily_df.iloc[j-1]['close']
                    
                    # Bounce: positive close and volume > 20-day avg
                    if (next_row['close'] > next_row['open'] and 
                        next_row['volume'] > next_row['avg_vol20']):
                        
                        pullback_date = row['日期']
                        bounce_date = next_row['日期']
                        bounce_pct = (next_row['close'] - prev_close) / prev_close * 100
                        
                        results.append({
                            'pullback_date': pullback_date,
                            'bounce_date': bounce_date,
                            'bounce_pct': bounce_pct
                        })
                        break
    
    return results[0] if results else None

def main():
    print("Generating sample data and detecting patterns...")
    
    # Sample stock list
    stocks = ['300001', '300059', '300123', '000001', '000002', '600036', '600519', '601318']
    
    results = []
    
    for symbol in stocks:
        try:
            # Generate weekly data
            weekly_df = generate_sample_weekly_data(symbol, weeks=100)
            
            # Detect weekly breakout
            breakout_date = detect_weekly_breakout(weekly_df, end_date='2024-04-22')
            if breakout_date is None:
                continue
            
            print(f"Found weekly breakout for {symbol} on {breakout_date.strftime('%Y-%m-%d')}")
            
            # Generate daily data after breakout
            breakout_str = breakout_date.strftime('%Y-%m-%d')
            daily_df = generate_sample_daily_data(symbol, start_date=breakout_str, end_date='2024-04-22')
            if daily_df is None or len(daily_df) < 25:
                continue
            
            # Detect daily pullback and bounce
            pullback_result = detect_daily_pullback_and_bounce(daily_df, breakout_date)
            if pullback_result is None:
                continue
            
            print(f"  Found pullback on {pullback_result['pullback_date'].strftime('%Y-%m-%d')}, bounce on {pullback_result['bounce_date'].strftime('%Y-%m-%d')}")
            
            results.append({
                'symbol': symbol,
                'breakout_date': breakout_date.strftime('%Y-%m-%d'),
                'pullback_date': pullback_result['pullback_date'].strftime('%Y-%m-%d'),
                'bounce_date': pullback_result['bounce_date'].strftime('%Y-%m-%d'),
                'bounce_pct': round(pullback_result['bounce_pct'], 2)
            })
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    # Write results
    output_file = 'weekly_pullback.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,周线突破日期,日线回踩日期,反弹日期,反弹日涨幅(%)\n')
        if results:
            for r in results:
                f.write(f"{r['symbol']},{r['breakout_date']},{r['pullback_date']},{r['bounce_date']},{r['bounce_pct']}\n")
        else:
            f.write('# 无符合条件的股票\n')
    
    print(f"\nResults written to {output_file}")
    print(f"Found {len(results)} stocks matching the pattern")

if __name__ == '__main__':
    main()
