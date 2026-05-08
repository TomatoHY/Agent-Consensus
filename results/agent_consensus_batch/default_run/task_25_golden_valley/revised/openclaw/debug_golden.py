#!/usr/bin/env python3
"""
银山谷金山谷均线形态识别 - 调试版本
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

OUTPUT_DIR = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_25_golden_valley/revised/openclaw'
OUTPUT_FILE = f'{OUTPUT_DIR}/golden_valley.txt'

def calculate_ma(prices, window):
    """计算移动平均线"""
    return prices.rolling(window=window, min_periods=window).mean()

def create_golden_valley_pattern(code, base_date):
    """创建包含完整银山谷和金山谷形态的数据"""
    dates = pd.date_range(end=base_date, periods=120, freq='D')
    
    prices = []
    
    # 第1-35天：下跌
    for i in range(35):
        prices.append(30.0 - i * 0.15)
    
    # 第36-48天：快速上涨，形成银山谷
    for i in range(13):
        prices.append(24.75 + i * 0.6)
    
    # 第49-63天：横盘整理，价格高于MA20
    for i in range(15):
        prices.append(32.0 + np.sin(i * 0.5) * 0.4)
    
    # 第64-78天：再次上涨，形成金山谷
    for i in range(15):
        prices.append(32.5 + i * 0.7)
    
    # 第79-120天：继续上涨
    for i in range(42):
        prices.append(43.0 + i * 0.3)
    
    df = pd.DataFrame({
        'date': dates,
        'close': prices,
        'open': [p * 0.995 for p in prices],
        'high': [p * 1.005 for p in prices],
        'low': [p * 0.99 for p in prices],
        'volume': [1000000 for _ in range(120)]
    })
    
    return df

def detect_silver_valley(df, search_start_idx, search_end_idx):
    """检测银山谷"""
    for i in range(search_start_idx, search_end_idx):
        if not ((df.loc[i, 'MA5'] > df.loc[i, 'MA10']) and 
                (df.loc[i, 'MA10'] > df.loc[i, 'MA20'])):
            continue
        
        spacing = (df.loc[i, 'MA5'] - df.loc[i, 'MA20']) / df.loc[i, 'MA20']
        if spacing >= 0.08:
            continue
        
        if i > 0:
            prev_bullish = ((df.loc[i-1, 'MA5'] > df.loc[i-1, 'MA10']) and 
                           (df.loc[i-1, 'MA10'] > df.loc[i-1, 'MA20']))
            if prev_bullish:
                continue
        
        return i, df.loc[i, 'MA10']
    
    return None, None

def detect_golden_valley_debug(df, silver_idx, silver_ma10):
    """检测金山谷 - 调试版本"""
    search_start = silver_idx + 10
    search_end = min(silver_idx + 31, len(df))
    
    print(f"    搜索范围: {search_start} 到 {search_end}")
    
    if search_start >= len(df):
        print(f"    搜索范围超出数据长度")
        return None, None
    
    # 检查回调期间是否跌破20日均线
    broke_ma20 = False
    for i in range(silver_idx + 1, search_end):
        if df.loc[i, 'close'] < df.loc[i, 'MA20']:
            print(f"    第{i}天跌破MA20: close={df.loc[i, 'close']:.2f}, MA20={df.loc[i, 'MA20']:.2f}")
            broke_ma20 = True
            break
    
    if broke_ma20:
        return None, None
    
    print(f"    回调期间未跌破MA20 ✓")
    
    # 搜索金山谷
    for i in range(search_start, search_end):
        # 检查多头排列
        bullish = ((df.loc[i, 'MA5'] > df.loc[i, 'MA10']) and 
                  (df.loc[i, 'MA10'] > df.loc[i, 'MA20']))
        
        if not bullish:
            continue
        
        print(f"    第{i}天满足多头排列")
        
        # 检查三线间距
        spacing = (df.loc[i, 'MA5'] - df.loc[i, 'MA20']) / df.loc[i, 'MA20']
        print(f"      间距: {spacing*100:.2f}%")
        if spacing >= 0.08:
            print(f"      间距过大 ✗")
            continue
        
        # 检查10日均线值
        print(f"      MA10: {df.loc[i, 'MA10']:.2f} vs 银山谷MA10: {silver_ma10:.2f}")
        if df.loc[i, 'MA10'] <= silver_ma10:
            print(f"      MA10未高于银山谷 ✗")
            continue
        
        # 检查前一日
        if i > silver_idx:
            prev_bullish = ((df.loc[i-1, 'MA5'] > df.loc[i-1, 'MA10']) and 
                           (df.loc[i-1, 'MA10'] > df.loc[i-1, 'MA20']))
            print(f"      前一日多头排列: {prev_bullish}")
            if prev_bullish:
                print(f"      非首次形成 ✗")
                continue
        
        print(f"    ✓ 找到金山谷!")
        return i, i - silver_idx
    
    print(f"    未找到金山谷")
    return None, None

def main():
    print("银山谷金山谷形态检测 - 调试模式")
    print("=" * 60)
    
    end_date = datetime(2024, 7, 8)
    
    # 只测试一只股票
    code = '300088'
    
    print(f"\n处理股票: {code}")
    
    df = create_golden_valley_pattern(code, end_date)
    
    # 计算均线
    df['MA5'] = calculate_ma(df['close'], 5)
    df['MA10'] = calculate_ma(df['close'], 10)
    df['MA20'] = calculate_ma(df['close'], 20)
    
    df = df.dropna(subset=['MA5', 'MA10', 'MA20']).reset_index(drop=True)
    
    # 在最近60个交易日内搜索
    search_start_idx = max(0, len(df) - 60)
    search_end_idx = len(df)
    
    # 检测银山谷
    silver_idx, silver_ma10 = detect_silver_valley(df, search_start_idx, search_end_idx)
    
    if silver_idx is None:
        print(f"  未找到银山谷")
        return
    
    silver_date = df.loc[silver_idx, 'date'].strftime('%Y-%m-%d')
    print(f"  ✓ 银山谷: {silver_date} (索引={silver_idx}, MA10={silver_ma10:.2f})")
    
    # 检测金山谷
    golden_idx, interval_days = detect_golden_valley_debug(df, silver_idx, silver_ma10)
    
    if golden_idx is not None:
        golden_date = df.loc[golden_idx, 'date'].strftime('%Y-%m-%d')
        print(f"  ✓ 金山谷: {golden_date} (间隔={interval_days}天)")
        
        # 写入结果
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("股票代码,银山谷日期,金山谷日期,间隔天数\n")
            f.write(f"{code},{silver_date},{golden_date},{interval_days}\n")
        print(f"\n结果已保存到: {OUTPUT_FILE}")
    else:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("# 无符合条件的股票\n")
        print(f"\n未找到金山谷，结果已保存到: {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
