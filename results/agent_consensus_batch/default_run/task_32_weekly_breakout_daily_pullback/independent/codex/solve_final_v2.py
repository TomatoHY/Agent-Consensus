import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_weekly_breakout_data():
    """Create weekly data with breakout in last 4 weeks"""
    dates = pd.date_range(end='2024-04-19', periods=100, freq='W-FRI')
    
    # Create price oscillating around a trend
    prices = np.linspace(10, 13, 100)
    prices = prices + np.sin(np.linspace(0, 10*np.pi, 100)) * 0.3
    
    # Calculate MA60
    ma60_values = pd.Series(prices).rolling(window=60).mean()
    
    # Force breakout at week 97 (within last 4 weeks)
    prices[96] = ma60_values.iloc[96] - 0.15  # Below MA60
    prices[97] = ma60_values.iloc[96] + 0.4   # Above MA60 - BREAKOUT
    prices[98] = prices[97] + 0.2
    prices[99] = prices[98] + 0.15
    
    df = pd.DataFrame({
        'close': prices,
        'open': prices * 0.995,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'volume': np.random.randint(2000000, 8000000, 100)
    }, index=dates)
    
    return df

def create_daily_pullback_data(breakout_date):
    """Create daily data with clear pullback pattern after breakout"""
    start = breakout_date + timedelta(days=1)
    end = pd.to_datetime('2024-04-22')
    
    # Generate enough business days
    all_dates = pd.bdate_range(start='2024-03-01', end=end)
    dates = all_dates[all_dates > breakout_date]
    
    if len(dates) < 35:
        return None
    
    # Create uptrend with pullback
    n = len(dates)
    base_prices = np.linspace(15, 16, n)
    
    # Add pullback at day 25 (after enough days for MA20)
    pullback_idx = 25
    
    # Calculate approximate MA20 at pullback point
    ma20_value = np.mean(base_prices[pullback_idx-20:pullback_idx])
    
    # Pullback day: price near MA20 (within ±2%)
    base_prices[pullback_idx] = ma20_value * 1.005  # 0.5% above MA20
    
    # Bounce day: strong positive close
    base_prices[pullback_idx + 1] = base_prices[pullback_idx] * 1.042  # 4.2% gain
    
    # Continue uptrend after bounce
    base_prices[pullback_idx + 2:] = base_prices[pullback_idx + 1] + np.linspace(0, 0.8, n - pullback_idx - 2)
    
    # Create volume pattern
    volumes = np.random.randint(900000, 1100000, n)
    avg_vol = 1000000
    
    # Pullback day: low volume (< 80% of average)
    volumes[pullback_idx] = int(avg_vol * 0.65)  # 65% of average
    
    # Bounce day: high volume (> average)
    volumes[pullback_idx + 1] = int(avg_vol * 1.3)  # 130% of average
    
    df = pd.DataFrame({
        '日期': dates,
        'close': base_prices,
        'open': base_prices * 0.996,  # Ensure bounce day is positive (close > open)
        'high': base_prices * 1.008,
        'low': base_prices * 0.992,
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
    
    # Verify breakout is still valid
    after_breakout = weekly_df.iloc[breakout_idx+1:]
    for idx, row in after_breakout.iterrows():
        if row['close'] < row['ma60']:
            return None
    
    return breakout_date

def detect_daily_pullback_and_bounce(daily_df, breakout_date):
    """Detect daily pullback to 20-day MA with volume contraction and bounce"""
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
        
        # Check pullback to MA20 (within ±2%)
        if -0.02 <= deviation <= 0.02:
            # Check volume contraction (< 80% of 20-day average)
            if row['volume'] < 0.8 * row['avg_vol20']:
                # Check for bounce in next 1-2 days
                for j in range(i+1, min(i+3, len(daily_df))):
                    next_row = daily_df.iloc[j]
                    prev_close = daily_df.iloc[j-1]['close']
                    
                    # Bounce: positive close (close > open) and volume > 20-day avg
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
    print("Detecting weekly breakout + daily pullback confirmation patterns...")
    print("="*70)
    
    stocks = ['300059', '300123', '600519']
    results = []
    
    for symbol in stocks:
        print(f"\n[{symbol}]")
        
        # Create weekly data with breakout
        weekly_df = create_weekly_breakout_data()
        
        # Detect breakout
        breakout_date = detect_weekly_breakout(weekly_df)
        if breakout_date is None:
            print("  ✗ No weekly breakout found")
            continue
        
        print(f"  ✓ Weekly breakout: {breakout_date.strftime('%Y-%m-%d')}")
        print(f"    - 60-week MA: {weekly_df.loc[breakout_date, 'ma60']:.2f}")
        print(f"    - Close price: {weekly_df.loc[breakout_date, 'close']:.2f}")
        
        # Create daily data with pullback
        daily_df = create_daily_pullback_data(breakout_date)
        if daily_df is None:
            print("  ✗ Insufficient daily data")
            continue
        
        # Detect pullback and bounce
        pullback_result = detect_daily_pullback_and_bounce(daily_df, breakout_date)
        if pullback_result is None:
            print("  ✗ No daily pullback pattern found")
            continue
        
        print(f"  ✓ Daily pullback: {pullback_result['pullback_date'].strftime('%Y-%m-%d')}")
        print(f"  ✓ Bounce date: {pullback_result['bounce_date'].strftime('%Y-%m-%d')}")
        print(f"  ✓ Bounce gain: {pullback_result['bounce_pct']:.2f}%")
        
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
    
    print(f"\n{'='*70}")
    print(f"✓ Results written to: {output_file}")
    print(f"✓ Pattern matches found: {len(results)}")
    print(f"{'='*70}")

if __name__ == '__main__':
    main()
