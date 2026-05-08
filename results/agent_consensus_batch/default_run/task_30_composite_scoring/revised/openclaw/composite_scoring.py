#!/usr/bin/env python3
"""
量价综合评分模型选股 - OpenClaw修订版
Composite scoring model for ChiNext stock selection
"""

import pandas as pd
import numpy as np
from scipy.stats import rankdata
from mootdx.quotes import Quotes

def calculate_adx(high, low, close, period=14):
    """
    Calculate ADX (Average Directional Index) using Wilder's method
    Includes DI+ and DI- calculation
    """
    if len(high) < period + 1:
        return 0
    
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
    plus_di_smooth = np.zeros(len(tr))
    minus_di_smooth = np.zeros(len(tr))

    if len(tr) >= period:
        atr[period-1] = np.mean(tr[:period])
        plus_di_smooth[period-1] = np.mean(plus_dm[:period])
        minus_di_smooth[period-1] = np.mean(minus_dm[:period])

        for i in range(period, len(tr)):
            atr[i] = atr[i-1] * (1 - alpha) + tr[i] * alpha
            plus_di_smooth[i] = plus_di_smooth[i-1] * (1 - alpha) + plus_dm[i] * alpha
            minus_di_smooth[i] = minus_di_smooth[i-1] * (1 - alpha) + minus_dm[i] * alpha

        # Calculate DI+ and DI-
        plus_di = 100 * plus_di_smooth / (atr + 1e-10)
        minus_di = 100 * minus_di_smooth / (atr + 1e-10)

        # Calculate DX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)

        # Calculate ADX (smooth DX)
        adx = np.zeros(len(dx))
        adx[period-1] = np.mean(dx[period-1:min(period+period-1, len(dx))])

        for i in range(period, len(dx)):
            adx[i] = adx[i-1] * (1 - alpha) + dx[i] * alpha

        return adx[-1] if len(adx) > 0 else 0

    return 0

def get_chinext_stocks():
    """Get ChiNext stock list by iterating through 300xxx codes"""
    client = Quotes.factory(market='std')
    chinext_codes = []
    
    print("扫描创业板股票代码...")
    # Scan 300001-301999
    for i in range(1, 2000):
        if i < 1000:
            code = f"300{i:03d}"
        else:
            code = f"30{i:04d}"
        
        try:
            # Try to fetch minimal data to check if stock exists
            bars = client.bars(symbol=code, frequency=9, offset=5)
            if bars is not None and len(bars) > 0:
                chinext_codes.append(code)
                if len(chinext_codes) % 100 == 0:
                    print(f"已找到 {len(chinext_codes)} 只股票...", end='\r')
        except:
            pass
    
    print(f"\n共找到 {len(chinext_codes)} 只创业板股票")
    return chinext_codes

def calculate_stock_metrics(code, client, end_date='2024-12-09'):
    """Calculate metrics for a single stock"""
    try:
        # Fetch 120 days of data (to ensure we have 60+ trading days)
        bars = client.bars(symbol=code, frequency=9, offset=120)
        
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
        price_return_20d = (recent_20['close'].iloc[-1] / recent_20['close'].iloc[0] - 1) * 100
        
        # 2. Volume strength: turnover ratio (use volume as proxy)
        turnover_20d = recent_20['vol'].mean()
        turnover_60d = recent_60['vol'].mean()
        volume_ratio = turnover_20d / (turnover_60d + 1e-10)
        
        # 3. Trend strength: ADX indicator
        high = recent_60['high'].values
        low = recent_60['low'].values
        close = recent_60['close'].values
        adx_value = calculate_adx(high, low, close, period=14)
        
        # 4. Capital strength: 5-day volume change (proxy for capital flow)
        vol_change_5d = (recent_5['vol'].iloc[-1] / recent_5['vol'].iloc[0] - 1) * 100
        
        return {
            'code': code,
            'price_return_20d': price_return_20d,
            'volume_ratio': volume_ratio,
            'adx': adx_value,
            'capital_proxy': vol_change_5d
        }
    except Exception as e:
        return None

def get_stock_pe(code, client):
    """Get PE ratio for a stock"""
    try:
        finance = client.financial(symbol=code)
        if finance is not None and len(finance) > 0 and 'pe' in finance.columns:
            return finance['pe'].iloc[0]
    except:
        pass
    return None

def get_stock_name(code, client):
    """Get stock name"""
    try:
        stocks = client.stocks(market=1)
        stock_info = stocks[stocks['code'] == code]
        if len(stock_info) > 0:
            return stock_info['name'].iloc[0]
    except:
        pass
    return f"股票{code}"

def main():
    print("=" * 70)
    print("量价综合评分模型选股 - 创业板")
    print("截至日期: 2024-12-09")
    print("=" * 70)
    
    client = Quotes.factory(market='std')
    
    # Get ChiNext stock list
    chinext_codes = get_chinext_stocks()
    
    if len(chinext_codes) == 0:
        print("未找到创业板股票")
        return
    
    # Calculate metrics for all stocks
    print("\n计算各股票指标...")
    results = []
    
    for idx, code in enumerate(chinext_codes):
        if (idx + 1) % 50 == 0:
            print(f"进度: {idx+1}/{len(chinext_codes)}", end='\r')
        
        # Get stock name
        name = get_stock_name(code, client)
        
        # Filter ST stocks
        if 'ST' in name or '*ST' in name:
            continue
        
        # Calculate metrics
        metrics = calculate_stock_metrics(code, client)
        if metrics is None:
            continue
        
        # Get PE
        pe = get_stock_pe(code, client)
        if pe is None or pe <= 0 or pe >= 60:
            continue
        
        metrics['name'] = name
        metrics['pe'] = pe
        results.append(metrics)
    
    print(f"\n成功计算 {len(results)} 只股票的指标")
    
    if len(results) == 0:
        print("没有符合PE条件的股票")
        with open('composite_score.txt', 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Calculate percentile rankings for each dimension
    print("\n计算百分位排名...")
    df['price_score'] = rankdata(df['price_return_20d'], method='average') / len(df) * 40
    df['turnover_score'] = rankdata(df['volume_ratio'], method='average') / len(df) * 30
    df['trend_score'] = (df['adx'] / 100) * 20  # ADX/100 * 20
    df['fund_score'] = rankdata(df['capital_proxy'], method='average') / len(df) * 10
    
    # Calculate total score
    df['total_score'] = df['price_score'] + df['turnover_score'] + df['trend_score'] + df['fund_score']
    
    # Filter by total score > 75
    df = df[df['total_score'] > 75]
    
    print(f"总分>75筛选后剩余 {len(df)} 只股票")
    
    if len(df) == 0:
        print("没有总分>75的股票")
        with open('composite_score.txt', 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票（总分>75）\n")
        return
    
    # Sort by total score and take top 15
    df = df.sort_values('total_score', ascending=False).head(15)
    
    # Save results
    output_path = 'composite_score.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,价格强度分,量能强度分,趋势强度分,资金强度分,总分,PE\n")
        for _, row in df.iterrows():
            f.write(f"{row['code']},{row['price_score']:.1f},{row['turnover_score']:.1f},"
                   f"{row['trend_score']:.1f},{row['fund_score']:.1f},{row['total_score']:.1f},{row['pe']:.1f}\n")
    
    print(f"\n结果已保存到 {output_path}")
    print("\n前15只股票:")
    print(df[['code', 'name', 'price_score', 'turnover_score', 'trend_score', 'fund_score', 'total_score', 'pe']])

if __name__ == '__main__':
    main()
