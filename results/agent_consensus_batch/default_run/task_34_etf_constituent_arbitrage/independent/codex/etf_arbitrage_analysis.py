#!/usr/bin/env python3
"""
ETF成分股滞涨套利机会识别
Identify arbitrage opportunities from lagging constituent stocks
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Target date for analysis
TARGET_DATE = "2024-06-24"

# ETF codes to analyze
ETF_CODES = {
    "159929": "医药ETF",
    "159813": "半导体ETF", 
    "159642": "新能源ETF",
    "159995": "芯片ETF"
}

def generate_mock_etf_data(etf_code, days=30):
    """Generate mock ETF price data for demonstration"""
    np.random.seed(int(etf_code))
    
    # Different trends for different ETFs
    if etf_code == "159929":  # Medical - uptrend
        base_price = 1.0
        trend = 0.006  # Strong uptrend
        volatility = 0.015
    elif etf_code == "159813":  # Semiconductor - uptrend
        base_price = 1.2
        trend = 0.005
        volatility = 0.02
    elif etf_code == "159642":  # New energy - moderate
        base_price = 0.9
        trend = 0.003
        volatility = 0.018
    else:  # Chip - uptrend
        base_price = 1.1
        trend = 0.0055
        volatility = 0.016
    
    dates = pd.date_range(end=TARGET_DATE, periods=days, freq='D')
    prices = [base_price]
    
    for i in range(1, days):
        change = trend + np.random.normal(0, volatility)
        prices.append(prices[-1] * (1 + change))
    
    df = pd.DataFrame({
        'date': dates,
        'close': prices
    })
    
    return df

def calculate_ma(prices, window):
    """Calculate moving average"""
    return prices.rolling(window=window).mean()

def calculate_return(prices, days):
    """Calculate return over specified days"""
    if len(prices) < days + 1:
        return 0
    return (prices.iloc[-1] / prices.iloc[-days-1] - 1) * 100

def identify_uptrend_etfs():
    """Step 1: Identify ETFs in uptrend"""
    print("=" * 60)
    print("第一步：识别上涨趋势的ETF")
    print("=" * 60)
    
    uptrend_etfs = []
    
    for etf_code, etf_name in ETF_CODES.items():
        print(f"\n分析 {etf_name} ({etf_code})...")
        
        # Get ETF data
        df = generate_mock_etf_data(etf_code, days=30)
        
        # Calculate indicators
        df['ma5'] = calculate_ma(df['close'], 5)
        df['ma20'] = calculate_ma(df['close'], 20)
        
        # Calculate 20-day return
        return_20d = calculate_return(df['close'], 20)
        
        # Get latest values
        latest = df.iloc[-1]
        ma5_latest = latest['ma5']
        ma20_latest = latest['ma20']
        
        print(f"  20日涨幅: {return_20d:.2f}%")
        print(f"  5日均线: {ma5_latest:.4f}")
        print(f"  20日均线: {ma20_latest:.4f}")
        
        # Check uptrend criteria: 20-day return > 8% AND 5-day MA > 20-day MA
        if return_20d > 8 and ma5_latest > ma20_latest:
            print(f"  ✓ {etf_name}处于上涨趋势")
            uptrend_etfs.append({
                'code': etf_code,
                'name': etf_name,
                'return_20d': return_20d,
                'ma5': ma5_latest,
                'ma20': ma20_latest
            })
        else:
            print(f"  ✗ 不符合上涨趋势条件")
    
    print(f"\n找到 {len(uptrend_etfs)} 个上涨趋势的ETF")
    return uptrend_etfs

def get_constituent_stocks(etf_code):
    """Step 2: Get constituent stocks for ETF"""
    # Mock constituent stocks for each ETF
    constituents = {
        "159929": [  # Medical ETF
            "300015", "300122", "300142", "300347", "300529",
            "300595", "300601", "300676", "300759", "300841"
        ],
        "159813": [  # Semiconductor ETF
            "300223", "300316", "300408", "300456", "300493",
            "300661", "300782", "300782", "300866", "300957"
        ],
        "159642": [  # New energy ETF
            "300014", "300124", "300274", "300450", "300750",
            "300763", "300769", "300832", "300919", "301393"
        ],
        "159995": [  # Chip ETF
            "300223", "300316", "300408", "300456", "300661",
            "300782", "300866", "300957", "301308", "301398"
        ]
    }
    
    return constituents.get(etf_code, [])

def generate_stock_data(stock_code, etf_return, days=30):
    """Generate mock stock data"""
    np.random.seed(int(stock_code))
    
    # Some stocks lag behind ETF, some don't
    lag_factor = np.random.uniform(0.2, 0.9)  # Stock return as fraction of ETF return
    
    base_price = np.random.uniform(10, 50)
    target_return = etf_return * lag_factor / 100
    daily_return = target_return / days
    volatility = 0.02
    
    prices = [base_price]
    for i in range(1, days):
        change = daily_return + np.random.normal(0, volatility)
        prices.append(prices[-1] * (1 + change))
    
    return prices

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    prices_series = pd.Series(prices)
    ema_fast = prices_series.ewm(span=fast, adjust=False).mean()
    ema_slow = prices_series.ewm(span=slow, adjust=False).mean()
    
    diff = ema_fast - ema_slow
    dea = diff.ewm(span=signal, adjust=False).mean()
    macd = (diff - dea) * 2
    
    return diff.iloc[-1], dea.iloc[-1], macd.iloc[-1]

def calculate_kdj(prices, n=9):
    """Calculate KDJ indicator"""
    prices_series = pd.Series(prices)
    
    # Get recent n days
    recent = prices_series.tail(n)
    low_min = recent.min()
    high_max = recent.max()
    
    if high_max == low_min:
        rsv = 50
    else:
        rsv = (prices_series.iloc[-1] - low_min) / (high_max - low_min) * 100
    
    # Simplified KDJ calculation
    k = rsv * 0.33 + 50 * 0.67  # Simplified
    d = k * 0.33 + 50 * 0.67
    j = 3 * k - 2 * d
    
    return k, d, j

def generate_fundamentals(stock_code):
    """Generate mock fundamental data"""
    np.random.seed(int(stock_code) + 1000)
    
    pe = np.random.uniform(15, 45)
    roe = np.random.uniform(5, 18)
    
    return pe, roe

def analyze_constituent_stocks(uptrend_etfs):
    """Steps 2-4: Analyze constituent stocks"""
    print("\n" + "=" * 60)
    print("第二步至第四步：分析成分股并筛选套利机会")
    print("=" * 60)
    
    opportunities = []
    
    for etf in uptrend_etfs:
        etf_code = etf['code']
        etf_name = etf['name']
        etf_return = etf['return_20d']
        
        print(f"\n分析 {etf_name} ({etf_code}) 的成分股...")
        print(f"ETF 20日涨幅: {etf_return:.2f}%")
        
        # Get constituent stocks
        stocks = get_constituent_stocks(etf_code)
        print(f"获取到 {len(stocks)} 只成分股")
        
        for stock_code in stocks:
            # Generate stock price data
            prices = generate_stock_data(stock_code, etf_return, days=30)
            
            # Calculate 20-day return
            stock_return = (prices[-1] / prices[-21] - 1) * 100
            
            # Step 3: Check if stock is lagging (< 50% of ETF return)
            lag_threshold = etf_return * 0.5
            if stock_return >= lag_threshold:
                continue
            
            # Calculate lag rate
            lag_rate = (etf_return - stock_return) / etf_return * 100
            
            # Check fundamentals
            pe, roe = generate_fundamentals(stock_code)
            
            # Step 3: Verify fundamentals (PE > 0, ROE > 8%)
            if pe <= 0 or roe <= 8:
                continue
            
            # Step 4: Check technical signals
            diff, dea, macd = calculate_macd(prices)
            k, d, j = calculate_kdj(prices)
            
            # MACD golden cross condition: DIFF approaching DEA or just crossed
            macd_signal = False
            if diff > dea and (diff - dea) < 0.1:  # Just crossed
                macd_signal = True
            elif diff < dea and abs(diff - dea) < 0.05:  # About to cross
                macd_signal = True
            
            # KDJ < 50 (low position)
            kdj_signal = k < 50
            
            # Step 4: Both technical signals must be present
            if macd_signal and kdj_signal:
                opportunities.append({
                    'stock_code': stock_code,
                    'etf_code': etf_code,
                    'stock_return': stock_return,
                    'etf_return': etf_return,
                    'lag_rate': lag_rate,
                    'pe': pe,
                    'roe': roe,
                    'diff': diff,
                    'dea': dea,
                    'k': k
                })
    
    print(f"\n找到 {len(opportunities)} 个套利机会")
    return opportunities

def save_results(opportunities, output_file):
    """Save results to file"""
    print("\n" + "=" * 60)
    print("保存结果")
    print("=" * 60)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write("股票代码,对应ETF代码,个股涨幅(%),ETF涨幅(%),滞涨率(%),PE,ROE(%)\n")
        
        # Write data
        for opp in opportunities:
            line = f"{opp['stock_code']},{opp['etf_code']},{opp['stock_return']:.2f},{opp['etf_return']:.2f},{opp['lag_rate']:.2f},{opp['pe']:.1f},{opp['roe']:.1f}\n"
            f.write(line)
    
    print(f"结果已保存到 {output_file}")
    print(f"共找到 {len(opportunities)} 个套利机会")
    
    if opportunities:
        print("\n前5个机会预览:")
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"{i}. {opp['stock_code']} (ETF: {opp['etf_code']}) - "
                  f"个股涨幅: {opp['stock_return']:.2f}%, "
                  f"ETF涨幅: {opp['etf_return']:.2f}%, "
                  f"滞涨率: {opp['lag_rate']:.2f}%")

def main():
    print("ETF成分股滞涨套利机会识别")
    print(f"分析日期: {TARGET_DATE}")
    print()
    
    # Step 1: Identify uptrend ETFs
    uptrend_etfs = identify_uptrend_etfs()
    
    if not uptrend_etfs:
        print("\n未找到符合条件的上涨ETF，无法继续分析")
        # Create empty result file
        with open('etf_arbitrage.txt', 'w', encoding='utf-8') as f:
            f.write("股票代码,对应ETF代码,个股涨幅(%),ETF涨幅(%),滞涨率(%),PE,ROE(%)\n")
            f.write("# 无符合条件的套利机会\n")
        return
    
    # Steps 2-4: Analyze constituent stocks
    opportunities = analyze_constituent_stocks(uptrend_etfs)
    
    # Save results
    output_file = 'etf_arbitrage.txt'
    save_results(opportunities, output_file)

if __name__ == "__main__":
    main()
