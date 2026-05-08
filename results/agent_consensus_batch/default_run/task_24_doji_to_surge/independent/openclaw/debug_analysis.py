#!/usr/bin/env python3
"""
调试版本：检查每个条件的通过情况
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_chinext_stocks():
    """获取创业板股票列表"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()[:100]  # 先测试100只
    except Exception as e:
        print(f"获取创业板列表失败: {e}")
        return []

def get_stock_data(code, end_date='2024-06-07'):
    """获取股票历史数据"""
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

def analyze_stock_debug(code):
    """调试分析单只股票"""
    df = get_stock_data(code)
    if df is None or len(df) < 90:
        return None
    
    cutoff_date = pd.to_datetime('2024-06-07')
    cutoff_idx = df[df['date'] <= cutoff_date].index[-1] if len(df[df['date'] <= cutoff_date]) > 0 else len(df) - 1
    
    if cutoff_idx < 60:
        return None
    
    stats = {
        'code': code,
        'has_low_volume_days': False,
        'has_consecutive_3days': False,
        'has_consolidation': False,
        'has_surge_volume': False,
        'has_yang_line': False,
        'has_breakout': False
    }
    
    # 检查地量期
    start_search_idx = max(60, cutoff_idx - 29)
    low_volume_count = 0
    consecutive_periods = []
    
    for i in range(start_search_idx, cutoff_idx + 1):
        avg_vol_60 = calculate_60d_avg_volume(df, i)
        if avg_vol_60 and df.loc[i, 'volume'] < avg_vol_60 * 0.5:
            low_volume_count += 1
            stats['has_low_volume_days'] = True
    
    # 查找连续地量期
    i = start_search_idx
    while i <= cutoff_idx:
        avg_vol_60 = calculate_60d_avg_volume(df, i)
        if avg_vol_60 and df.loc[i, 'volume'] < avg_vol_60 * 0.5:
            period_start = i
            period_end = i
            
            j = i + 1
            while j <= cutoff_idx:
                avg_vol_j = calculate_60d_avg_volume(df, j)
                if avg_vol_j and df.loc[j, 'volume'] < avg_vol_j * 0.5:
                    period_end = j
                    j += 1
                else:
                    break
            
            period_days = period_end - period_start + 1
            if period_days >= 3:
                stats['has_consecutive_3days'] = True
                
                # 检查横盘
                period_high = df.loc[period_start:period_end, 'high'].max()
                period_low = df.loc[period_start:period_end, 'low'].min()
                price_range_pct = (period_high - period_low) / period_low * 100
                
                if price_range_pct < 3.0:
                    stats['has_consolidation'] = True
                    consecutive_periods.append((period_start, period_end, period_days))
            
            i = period_end + 1
        else:
            i += 1
    
    # 检查天量突破
    for period_start, period_end, period_days in consecutive_periods:
        search_end = min(period_end + 10, cutoff_idx)
        
        for i in range(period_end + 1, search_end + 1):
            avg_vol_60 = calculate_60d_avg_volume(df, i)
            if avg_vol_60 is None:
                continue
            
            volume_ratio = df.loc[i, 'volume'] / avg_vol_60
            if volume_ratio > 3.0:
                stats['has_surge_volume'] = True
                
                if df.loc[i, 'close'] > df.loc[i, 'open']:
                    stats['has_yang_line'] = True
                    
                    pct_change = (df.loc[i, 'close'] - df.loc[i, 'open']) / df.loc[i, 'open'] * 100
                    if pct_change > 5.0:
                        lookback_start = max(0, i - 29)
                        max_price_30d = df.loc[lookback_start:i-1, 'high'].max() if i > 0 else 0
                        if df.loc[i, 'close'] > max_price_30d:
                            stats['has_breakout'] = True
                            return stats
    
    return stats if any([stats['has_low_volume_days'], stats['has_consecutive_3days']]) else None

def main():
    print("调试分析创业板地量天量突破形态...")
    print("=" * 60)
    
    chinext_stocks = get_chinext_stocks()
    print(f"测试 {len(chinext_stocks)} 只创业板股票")
    
    results = []
    for idx, code in enumerate(chinext_stocks, 1):
        if idx % 20 == 0:
            print(f"进度: {idx}/{len(chinext_stocks)}")
        
        try:
            stats = analyze_stock_debug(code)
            if stats:
                results.append(stats)
        except:
            continue
    
    print("=" * 60)
    print(f"统计结果（共 {len(results)} 只股票有地量迹象）:")
    print(f"  有地量日: {sum(1 for r in results if r['has_low_volume_days'])}")
    print(f"  有连续3天地量: {sum(1 for r in results if r['has_consecutive_3days'])}")
    print(f"  地量期横盘<3%: {sum(1 for r in results if r['has_consolidation'])}")
    print(f"  有天量(>3倍): {sum(1 for r in results if r['has_surge_volume'])}")
    print(f"  天量日收阳: {sum(1 for r in results if r['has_yang_line'])}")
    print(f"  突破30日高点: {sum(1 for r in results if r['has_breakout'])}")
    print(f"  全部条件满足: {sum(1 for r in results if r['has_breakout'])}")
    
    # 显示部分案例
    if results:
        print("\n部分案例:")
        for r in results[:10]:
            print(f"  {r['code']}: 地量日={r['has_low_volume_days']}, 连续3天={r['has_consecutive_3days']}, "
                  f"横盘={r['has_consolidation']}, 天量={r['has_surge_volume']}, "
                  f"阳线={r['has_yang_line']}, 突破={r['has_breakout']}")

if __name__ == '__main__':
    main()
