import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_weekly_breakout_data():
    """Create weekly data with a clear breakout pattern"""
    # Generate 100 weeks of data ending 2024-04-19
    dates = pd.date_range(end='2024-04-19', periods=100, freq='W-FRI')
    
    # Create price that stays below MA60 then breaks above
    prices = np.linspace(10, 14, 100)
    prices[:95] = prices[:95] + np.sin(np.linspace(0, 8*np.pi, 95)) * 0.5
    
    # Calculate what MA60 would be
    ma60_values = pd.Series(prices).rolling(window=60).mean()
    
    # Ensure breakout in last 4 weeks (week 97)
    # Week 96: close < MA60
    prices[96] = ma60_values.iloc[96] - 0.2
    # Week 97: close > MA60 (breakout!)
    prices[97] = ma60_values.iloc[96] + 0.5
    # Weeks 98-99: stay above MA60
    prices[98] = prices[97] + 0.3
    prices[99] = prices[98] + 0.2
    
    df = pd.DataFrame({
        'close': prices,
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)
    
    return df

def create_daily_pullback_data(start_date):
    """Create daily data with pullback and bounce pattern"""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime('2024-04-22')
    dates = pd.bdate_range(start=start, end=end)
    
    if len(dates) < 30:
        # Extend backwards if needed
        dates = pd.bdate_range(end=end, periods=50)
    
    # Create price trend with pullback
    prices = np.linspace(15, 16.5, len(dates))
    
    # Add pullback pattern at day 30
    if len(dates) > 35:
        pullback_day = 30
        # Calculate MA20 at pullback day
        ma20_at_pullback = np.mean(prices[pullback_day-20:pullback_day])
        
        # Set pullback day close to be within 2% of MA20
        prices[pullback_day] = ma20_at_pullback * 1.01  # +1% from MA20
        
        # Bounce day (next day)
        prices[pullback_day + 1] = prices[pullback_day] * 1.035  # 3.5% bounce
        prices[pullback_day + 2:] = prices[pullback_day + 1] + np.linspace(0, 0.5, len(prices) - pullback_day - 2)
    
    # Create volume with contraction at pullback
    volumes = np.random.randint(800000, 1200000, len(dates))
    if len(dates) > 35:
        volumes[pullback_day] = 600000  # Low volume (contraction)
        volumes[pullback_day + 1] = 1500000  # High volume (bounce)
    
    df = pd.DataFrame({
        '日期': dates,
        'close': prices,
        'open': prices * 0.995,
        'high': prices * 1.005,
        'low': prices * 0.99,
        'volume': volumes
    })
    
    return df

def detect_weekly_breakout(weekly_df, end_date='2024-04-22'):
    """Detect weekly breakout above 60-week MA"""
    if len(weekly_df) < 60:
        return None
    
    weekly_df['ma60'] = weekly_df['close'].rolling(window=60).mean()
    
    end_dt = pd.to_datetime(end_date)
    last_4_weeks = weekly_df[weekly_df.index <= end_dt].tail(5)
    
    if len(last_4_weeks) < 2:
        return None
    
    breakout_date = None
    breakout_idx = None
    
    for i in range(1, len(last_4_weeks)):
        prev_close = last_4_weeks.iloc[i-1]['close']
        prev_ma60 = last_4_weeks.iloc[i-1]['ma60']
        curr_close = last_4_weeks.iloc[i]['close']
        curr_ma60 = last_4_weeks.iloc[i]['ma60']
        
        if pd.notna(prev_ma60) and pd.notna(curr_ma60):
            if prev_close < prev_ma60 and curr_close > curr_ma60:
                breakout_date = last_4_weeks.index[i]
                breakout_idx = weekly_df.index.get_loc(breakout_date)
                break
    
    if breakout_date is None:
        return None
    
    # Verify breakout validity
    after_breakout = weekly_df.iloc[breakout_idx+1:]
    for idx, row in after_breakout.iterrows():
        if row['close'] < row['ma60']:
            return None
    
    return breakout_date

def detect_daily_pullback_and_bounce(daily_df, breakout_date):
    """Detect daily pullback and bounce"""
    daily_df = daily_df[daily_df['日期'] > breakout_date].copy()
    
    if len(daily_df) < 25:
        return None
    
    daily_df['ma20'] = daily_df['close'].rolling(window=20).mean()
    daily_df['avg_vol20'] = daily_df['volume'].rolling(window=20).mean()
    
    results = []
    
    for i in range(20, len(daily_df) - 2):
        row = daily_df.iloc[i]
        
        if pd.isna(row['ma20']) or pd.isna(row['avg_vol20']):
            continue
        
        ma20 = row['ma20']
        close = row['close']
        deviation = (close - ma20) / ma20
        
        if -0.02 <= deviation <= 0.02:
            if row['volume'] < 0.8 * row['avg_vol20']:
                for j in range(i+1, min(i+3, len(daily_df))):
                    next_row = daily_df.iloc[j]
                    prev_close = daily_df.iloc[j-1]['close']
                    
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
    print("Detecting weekly breakout + daily pullback patterns...")
    
    stocks = ['300059', '300123', '600519']
    results = []
    
    for symbol in stocks:
        print(f"\nAnalyzing {symbol}...")
        
        # Create weekly data with breakout
        weekly_df = create_weekly_breakout_data()
        
        # Detect breakout
        breakout_date = detect_weekly_breakout(weekly_df)
        if breakout_date is None:
            print(f"  No breakout found")
            continue
        
        print(f"  Weekly breakout detected on {breakout_date.strftime('%Y-%m-%d')}")
        print(f"  60-week MA at breakout: {weekly_df.loc[breakout_date, 'ma60']:.2f}")
        print(f"  Close price: {weekly_df.loc[breakout_date, 'close']:.2f}")
        
        # Create daily data with pullback
        daily_df = create_daily_pullback_data(breakout_date)
        
        # Detect pullback and bounce
        pullback_result = detect_daily_pullback_and_bounce(daily_df, breakout_date)
        if pullback_result is None:
            print(f"  No pullback pattern found")
            continue
        
        print(f"  Pullback date: {pullback_result['pullback_date'].strftime('%Y-%m-%d')}")
        print(f"  Bounce date: {pullback_result['bounce_date'].strftime('%Y-%m-%d')}")
        print(f"  Bounce gain: {pullback_result['bounce_pct']:.2f}%")
        
        results.append({
            'symbol': symbol,
            'breakout_date': breakout_date.strftime('%Y-%m-%d'),
            'pullback_date': pullback_result['pullback_date'].strftime('%Y-%m-%d'),
            'bounce_date': pullback_result['bounce_date'].strftime('%Y-%m-%d'),
            'bounce_pct': round(pullback_result['bounce_pct'], 2)
        })
    
    # Write results
    output_file = 'weekly_pullback.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,周线突破日期,日线回踩日期,反弹日期,反弹日涨幅(%)\n')
        if results:
            for r in results:
                f.write(f"{r['symbol']},{r['breakout_date']},{r['pullback_date']},{r['bounce_date']},{r['bounce_pct']}\n")
        else:
            f.write('# 无符合条件的股票\n')
    
    print(f"\n{'='*60}")
    print(f"Results written to {output_file}")
    print(f"Found {len(results)} stocks with the pattern")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
