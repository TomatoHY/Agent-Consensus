#!/usr/bin/env python3
"""
最终版本：完全禁用代理
"""

import os
import sys

# 必须在导入任何库之前清除代理
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 再次确保没有代理
import urllib.request
urllib.request.getproxies = lambda: {}

def get_chinext_stocks():
    """获取创业板股票列表"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"获取创业板列表失败: {e}")
        return []

def get_stock_data(code, end_date='2024-06-07'):
    """获取股票历史数据，需要至少90天数据（60日均量+30日检测）"""
    try:
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=150)).strftime('%Y-%m-%d')
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df is None or len(df) < 60:
            return None
            
        df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        }, inplace=True)
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
    except Exception as e:
        return None

def calculate_60d_avg_volume(df, idx):
    """计算指定位置的60日平均成交量"""
    if idx < 59:
        return None
    return df.loc[idx-59:idx, 'volume'].mean()

def find_low_volume_periods(df, end_idx):
    """
    在end_idx之前的30天内查找连续≥3天的地量期
    地量定义: 单日成交量 < 60日均量的50%
    横盘条件: 地量期内(最高价-最低价)/最低价 < 3%
    """
    low_volume_periods = []
    
    start_search_idx = max(60, end_idx - 29)
    
    i = start_search_idx
    while i <= end_idx:
        avg_vol_60 = calculate_60d_avg_volume(df, i)
        if avg_vol_60 is None:
            i += 1
            continue
        
        if df.loc[i, 'volume'] < avg_vol_60 * 0.5:
            period_start = i
            period_end = i
            
            j = i + 1
            while j <= end_idx:
                avg_vol_j = calculate_60d_avg_volume(df, j)
                if avg_vol_j and df.loc[j, 'volume'] < avg_vol_j * 0.5:
                    period_end = j
                    j += 1
                else:
                    break
            
            period_days = period_end - period_start + 1
            if period_days >= 3:
                period_high = df.loc[period_start:period_end, 'high'].max()
                period_low = df.loc[period_start:period_end, 'low'].min()
                price_range_pct = (period_high - period_low) / period_low * 100
                
                if price_range_pct < 3.0:
                    low_volume_periods.append({
                        'start_idx': period_start,
                        'end_idx': period_end,
                        'days': period_days,
                        'price_range_pct': price_range_pct
                    })
            
            i = period_end + 1
        else:
            i += 1
    
    return low_volume_periods

def check_surge_breakout(df, low_period, cutoff_idx):
    """
    检查地量期结束后10日内是否出现天量突破
    """
    period_end_idx = low_period['end_idx']
    search_end = min(period_end_idx + 10, cutoff_idx)
    
    for i in range(period_end_idx + 1, search_end + 1):
        avg_vol_60 = calculate_60d_avg_volume(df, i)
        if avg_vol_60 is None:
            continue
        
        volume_ratio = df.loc[i, 'volume'] / avg_vol_60
        if volume_ratio <= 3.0:
            continue
        
        if df.loc[i, 'close'] <= df.loc[i, 'open']:
            continue
        
        pct_change = (df.loc[i, 'close'] - df.loc[i, 'open']) / df.loc[i, 'open'] * 100
        if pct_change <= 5.0:
            continue
        
        lookback_start = max(0, i - 29)
        max_price_30d = df.loc[lookback_start:i-1, 'high'].max() if i > 0 else 0
        if df.loc[i, 'close'] <= max_price_30d:
            continue
        
        return {
            'surge_idx': i,
            'surge_date': df.loc[i, 'date'].strftime('%Y-%m-%d'),
            'volume_ratio': volume_ratio,
            'breakout_pct': pct_change
        }
    
    return None

def analyze_stock(code):
    """分析单只股票"""
    df = get_stock_data(code)
    if df is None or len(df) < 90:
        return None
    
    cutoff_date = pd.to_datetime('2024-06-07')
    cutoff_idx = df[df['date'] <= cutoff_date].index[-1] if len(df[df['date'] <= cutoff_date]) > 0 else len(df) - 1
    
    if cutoff_idx < 60:
        return None
    
    low_periods = find_low_volume_periods(df, cutoff_idx)
    
    if not low_periods:
        return None
    
    results = []
    for period in low_periods:
        surge = check_surge_breakout(df, period, cutoff_idx)
        if surge:
            results.append({
                'code': code,
                'low_days': period['days'],
                'surge_date': surge['surge_date'],
                'volume_ratio': surge['volume_ratio'],
                'breakout_pct': surge['breakout_pct']
            })
    
    return results if results else None

def main():
    print("开始分析创业板地量天量突破形态...")
    print("截止日期: 2024-06-07")
    print("=" * 60)
    
    chinext_stocks = get_chinext_stocks()
    print(f"获取到 {len(chinext_stocks)} 只创业板股票")
    
    if not chinext_stocks:
        print("未获取到创业板股票列表")
        with open('doji_surge.txt', 'w', encoding='utf-8') as f:
            f.write("# 无符合条件的股票\n")
        return
    
    all_results = []
    
    for idx, code in enumerate(chinext_stocks, 1):
        if idx % 50 == 0:
            print(f"进度: {idx}/{len(chinext_stocks)}")
        
        try:
            results = analyze_stock(code)
            if results:
                all_results.extend(results)
                print(f"✓ {code}: 发现 {len(results)} 个形态")
        except Exception as e:
            continue
    
    print("=" * 60)
    print(f"分析完成，共发现 {len(all_results)} 个符合条件的形态")
    
    with open('doji_surge.txt', 'w', encoding='utf-8') as f:
        if all_results:
            f.write("股票代码,地量期天数,天量日期,量比(天量/60日均量),突破涨幅(%)\n")
            for r in all_results:
                f.write(f"{r['code']},{r['low_days']},{r['surge_date']},{r['volume_ratio']:.2f},{r['breakout_pct']:.2f}\n")
        else:
            f.write("# 无符合条件的股票\n")
    
    print("结果已写入 doji_surge.txt")

if __name__ == '__main__':
    main()
