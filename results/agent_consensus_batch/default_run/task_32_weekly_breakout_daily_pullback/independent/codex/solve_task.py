import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_weekly_data(symbol, start_date='2022-01-01', end_date='2024-04-22'):
    """Get weekly K-line data"""
    try:
        # Get daily data first, then resample to weekly
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                start_date=start_date.replace('-',''), 
                                end_date=end_date.replace('-',''),
                                adjust="qfq")
        if df is None or len(df) == 0:
            return None
        
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.set_index('日期')
        
        # Resample to weekly (Friday close)
        weekly = pd.DataFrame()
        weekly['open'] = df['开盘'].resample('W-FRI').first()
        weekly['high'] = df['最高'].resample('W-FRI').max()
        weekly['low'] = df['最低'].resample('W-FRI').min()
        weekly['close'] = df['收盘'].resample('W-FRI').last()
        weekly['volume'] = df['成交量'].resample('W-FRI').sum()
        
        weekly = weekly.dropna()
        return weekly
    except Exception as e:
        print(f"Error getting weekly data for {symbol}: {e}")
        return None

def get_daily_data(symbol, start_date, end_date='2024-04-22'):
    """Get daily K-line data"""
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                start_date=start_date.replace('-',''),
                                end_date=end_date.replace('-',''),
                                adjust="qfq")
        if df is None or len(df) == 0:
            return None
        
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.rename(columns={
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })
        return df
    except Exception as e:
        print(f"Error getting daily data for {symbol}: {e}")
        return None

def detect_weekly_breakout(weekly_df, end_date='2024-04-22'):
    """Detect weekly breakout above 60-week MA in last 4 weeks"""
    if len(weekly_df) < 60:
        return None
    
    # Calculate 60-week MA
    weekly_df['ma60'] = weekly_df['close'].rolling(window=60).mean()
    
    end_dt = pd.to_datetime(end_date)
    # Get last 4 weeks
    last_4_weeks = weekly_df[weekly_df.index <= end_dt].tail(5)  # 5 to check previous week
    
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
    
    # Verify breakout is still valid (hasn't fallen back below MA60)
    after_breakout = weekly_df.iloc[breakout_idx+1:]
    for idx, row in after_breakout.iterrows():
        if row['close'] < row['ma60']:
            return None  # Breakout invalidated
    
    return breakout_date

def detect_daily_pullback_and_bounce(daily_df, breakout_date):
    """Detect daily pullback to 20-day MA and subsequent bounce"""
    # Only look at data after breakout
    daily_df = daily_df[daily_df['日期'] > breakout_date].copy()
    
    if len(daily_df) < 25:  # Need enough data for MA20
        return None
    
    # Calculate 20-day MA and average volume
    daily_df['ma20'] = daily_df['close'].rolling(window=20).mean()
    daily_df['avg_vol20'] = daily_df['volume'].rolling(window=20).mean()
    
    results = []
    
    for i in range(20, len(daily_df) - 2):  # -2 to check next 2 days for bounce
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
    # Get stock list - focus on ChiNext (300xxx) and some main board stocks
    print("Getting stock list...")
    try:
        stock_info = ak.stock_zh_a_spot_em()
        # Filter for active stocks with reasonable volume
        stocks = stock_info[stock_info['代码'].str.match(r'^(000|002|300|600|601|603)')]['代码'].tolist()
        # Limit to reasonable number for testing
        stocks = stocks[:500]  # Test with first 500 stocks
    except Exception as e:
        print(f"Error getting stock list: {e}")
        # Fallback to some known stocks
        stocks = ['000001', '000002', '300001', '300059', '600000', '600036']
    
    print(f"Analyzing {len(stocks)} stocks...")
    
    results = []
    
    for idx, symbol in enumerate(stocks):
        if idx % 50 == 0:
            print(f"Progress: {idx}/{len(stocks)}")
        
        try:
            # Get weekly data
            weekly_df = get_weekly_data(symbol, start_date='2022-01-01', end_date='2024-04-22')
            if weekly_df is None or len(weekly_df) < 60:
                continue
            
            # Detect weekly breakout
            breakout_date = detect_weekly_breakout(weekly_df, end_date='2024-04-22')
            if breakout_date is None:
                continue
            
            print(f"Found weekly breakout for {symbol} on {breakout_date}")
            
            # Get daily data after breakout
            breakout_str = breakout_date.strftime('%Y-%m-%d')
            daily_df = get_daily_data(symbol, start_date=breakout_str, end_date='2024-04-22')
            if daily_df is None or len(daily_df) < 25:
                continue
            
            # Detect daily pullback and bounce
            pullback_result = detect_daily_pullback_and_bounce(daily_df, breakout_date)
            if pullback_result is None:
                continue
            
            print(f"  Found pullback pattern: {pullback_result}")
            
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
