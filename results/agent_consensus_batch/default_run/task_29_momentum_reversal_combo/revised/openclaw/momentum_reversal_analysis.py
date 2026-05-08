#!/usr/bin/env python3
"""
动量-反转组合因子选股
筛选条件（AND关系）：
1. 20日动量 > 15%
2. 5日短期反转 < -3%
3. RSI(14日) 在 30-50 之间
4. MACD DIFF > 0
5. 60日均线向上（近10日单调递增）
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from pathlib import Path

def get_chinext_stocks():
    """获取创业板股票列表（300开头）"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"获取创业板列表失败: {e}")
        return []

def get_stock_data(stock_code, days=100):
    """获取股票历史数据"""
    try:
        end_date = '20241108'
        start_date = (datetime(2024, 11, 8) - timedelta(days=days)).strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(
            symbol=stock_code, 
            period="daily",
            start_date=start_date, 
            end_date=end_date, 
            adjust="qfq"
        )
        
        if df is None or len(df) < 70:
            return None
            
        return df
    except Exception as e:
        return None

def calculate_momentum(df, period=20):
    """计算累计收益率（动量）"""
    if len(df) < period + 1:
        return None
    
    recent = df.tail(period + 1)
    start_price = recent.iloc[0]['收盘']
    end_price = recent.iloc[-1]['收盘']
    
    return ((end_price - start_price) / start_price) * 100

def calculate_rsi(df, period=14):
    """计算RSI（Wilder方法）"""
    if len(df) < period + 1:
        return None
    
    prices = df['收盘'].values
    deltas = np.diff(prices)
    
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # Wilder平滑
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_macd(df, fast=12, slow=26):
    """计算MACD的DIFF线（EMA12 - EMA26）"""
    if len(df) < slow + 10:
        return None
    
    prices = df['收盘']
    
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    diff = ema_fast - ema_slow
    
    return diff.iloc[-1]

def calculate_ma60_slope(df, ma_period=60, check_days=10):
    """计算60日均线斜率（检查近10日是否单调递增）"""
    if len(df) < ma_period + check_days:
        return None, False
    
    ma60 = df['收盘'].rolling(window=ma_period).mean()
    
    recent_ma60 = ma60.tail(check_days).values
    
    # 检查是否单调递增
    is_increasing = all(recent_ma60[i] < recent_ma60[i+1] for i in range(len(recent_ma60)-1))
    
    if is_increasing:
        x = np.arange(len(recent_ma60))
        slope = np.polyfit(x, recent_ma60, 1)[0]
        return slope, True
    
    return 0, False

def screen_stock(stock_code):
    """筛选单只股票"""
    df = get_stock_data(stock_code, days=120)
    
    if df is None:
        return None
    
    # 1. 计算20日动量
    momentum_20 = calculate_momentum(df, period=20)
    if momentum_20 is None or momentum_20 <= 15:
        return None
    
    # 2. 计算5日反转
    reversal_5 = calculate_momentum(df, period=5)
    if reversal_5 is None or reversal_5 >= -3:
        return None
    
    # 3. 计算RSI
    rsi = calculate_rsi(df, period=14)
    if rsi is None or rsi < 30 or rsi > 50:
        return None
    
    # 4. 计算MACD DIFF
    macd_diff = calculate_macd(df)
    if macd_diff is None or macd_diff <= 0:
        return None
    
    # 5. 检查60日均线斜率
    ma60_slope, is_increasing = calculate_ma60_slope(df)
    if not is_increasing:
        return None
    
    return {
        'code': stock_code,
        'momentum_20': momentum_20,
        'reversal_5': reversal_5,
        'rsi': rsi,
        'macd_diff': macd_diff,
        'ma60_slope': ma60_slope
    }

def main():
    print("开始获取创业板股票列表...")
    stock_codes = get_chinext_stocks()
    
    if not stock_codes:
        print("获取股票列表失败")
        return
    
    print(f"共获取 {len(stock_codes)} 只创业板股票")
    print("\n开始筛选股票（这可能需要几分钟）...")
    
    results = []
    
    for i, stock_code in enumerate(stock_codes):
        if i % 50 == 0:
            print(f"进度: {i}/{len(stock_codes)}")
        
        result = screen_stock(stock_code)
        if result:
            results.append(result)
            print(f"找到符合条件的股票: {stock_code}")
        
        # 避免请求过快
        time.sleep(0.1)
    
    # 按20日动量降序排序，取前10
    results_df = pd.DataFrame(results)
    
    output_file = Path(__file__).parent / "momentum_reversal.txt"
    
    if len(results_df) == 0:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 无符合条件的股票\n")
        print("\n无符合条件的股票")
    else:
        results_df = results_df.sort_values('momentum_20', ascending=False).head(10)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("股票代码,20日动量(%),5日反转(%),RSI,MACD_DIFF,60日均线斜率\n")
            for _, row in results_df.iterrows():
                f.write(f"{row['code']},{row['momentum_20']:.2f},{row['reversal_5']:.2f},"
                       f"{row['rsi']:.2f},{row['macd_diff']:.4f},{row['ma60_slope']:.6f}\n")
        
        print(f"\n筛选完成，共找到 {len(results_df)} 只股票")
        print(f"结果已保存到: {output_file}")
        print("\n结果预览:")
        print(results_df.to_string(index=False))

if __name__ == "__main__":
    main()
