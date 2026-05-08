#!/usr/bin/env python3
"""
识别创业板"地量之后天量"突破形态
截止日期: 2024-06-07
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
        return chinext['code'].tolist()
    except:
        return []

def get_stock_data(code, end_date='2024-06-07'):
    """获取股票历史数据，需要至少90天数据（60日均量+30日检测窗口）"""
    try:
        # 获取更长时间的数据以计算60日均量
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=150)).strftime('%Y%m%d')
        end_date_fmt = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                start_date=start_date, end_date=end_date_fmt, adjust="qfq")
        
        if df is None or len(df) < 70:
            return None
            
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        return df[['date', 'open', 'close', 'high', 'low', 'volume']]
    except Exception as e:
        return None

def calculate_60d_avg_volume(df, idx):
    """计算指定位置的60日平均成交量"""
    if idx < 59:
        return None
    return df.iloc[idx-59:idx+1]['volume'].mean()

def find_low_volume_periods(df, end_idx):
    """
    在end_idx之前的30日内查找连续≥3天的地量期
    地量定义: 单日成交量 < 60日均量的50%
    横盘条件: 地量期内(最高价-最低价)/最低价 < 3%
    """
    low_volume_periods = []
    
    # 检测窗口: end_idx之前的30天
    start_search_idx = max(60, end_idx - 29)  # 至少从第60天开始（需要60日均量）
    
    i = start_search_idx
    while i <= end_idx:
        avg_vol_60 = calculate_60d_avg_volume(df, i)
        if avg_vol_60 is None:
            i += 1
            continue
        
        # 检查是否是地量日
        if df.iloc[i]['volume'] < avg_vol_60 * 0.5:
            # 找连续地量期
            period_start = i
            period_end = i
            
            # 向后扩展连续地量日
            j = i + 1
            while j <= end_idx:
                avg_vol_j = calculate_60d_avg_volume(df, j)
                if avg_vol_j and df.iloc[j]['volume'] < avg_vol_j * 0.5:
                    period_end = j
                    j += 1
                else:
                    break
            
            # 检查连续天数是否≥3
            period_days = period_end - period_start + 1
            if period_days >= 3:
                # 检查横盘条件: 地量期内价格波动<3%
                period_data = df.iloc[period_start:period_end+1]
                high_max = period_data['high'].max()
                low_min = period_data['low'].min()
                price_range_pct = (high_max - low_min) / low_min * 100
                
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

def check_surge_breakout(df, low_period_end_idx):
    """
    检查地量期结束后10日内是否出现天量突破
    条件:
    1. 单日成交量 > 60日均量的3倍
    2. 当天收阳(收盘>开盘)
    3. 涨幅>5%
    4. 收盘价突破近30日最高价
    """
    # 检查范围: 地量期结束后1-10天
    search_start = low_period_end_idx + 1
    search_end = min(low_period_end_idx + 10, len(df) - 1)
    
    for i in range(search_start, search_end + 1):
        avg_vol_60 = calculate_60d_avg_volume(df, i)
        if avg_vol_60 is None:
            continue
        
        row = df.iloc[i]
        
        # 条件1: 天量 (>60日均量3倍)
        volume_ratio = row['volume'] / avg_vol_60
        if volume_ratio <= 3.0:
            continue
        
        # 条件2: 收阳
        if row['close'] <= row['open']:
            continue
        
        # 条件3: 涨幅>5%
        pct_change = (row['close'] - row['open']) / row['open'] * 100
        if pct_change <= 5.0:
            continue
        
        # 条件4: 突破近30日最高价
        # 近30日指当天之前的30天
        lookback_start = max(0, i - 30)
        lookback_end = i - 1
        if lookback_end < lookback_start:
            continue
        
        max_price_30d = df.iloc[lookback_start:lookback_end+1]['high'].max()
        if row['close'] <= max_price_30d:
            continue
        
        # 所有条件满足
        return {
            'surge_idx': i,
            'surge_date': row['date'],
            'volume_ratio': volume_ratio,
            'breakout_pct': pct_change
        }
    
    return None

def main():
    end_date = '2024-06-07'
    print(f"开始分析创业板地量天量突破形态 (截止日期: {end_date})")
    
    # 获取创业板股票列表
    print("获取创业板股票列表...")
    chinext_stocks = get_chinext_stocks()
    
    if not chinext_stocks:
        print("无法获取创业板股票列表，使用示例代码")
        chinext_stocks = [f"300{str(i).zfill(3)}" for i in range(1, 1000)]
    
    print(f"共 {len(chinext_stocks)} 只创业板股票")
    
    results = []
    
    for idx, code in enumerate(chinext_stocks):
        if (idx + 1) % 50 == 0:
            print(f"进度: {idx + 1}/{len(chinext_stocks)}")
        
        # 获取股票数据
        df = get_stock_data(code, end_date)
        if df is None or len(df) < 70:
            continue
        
        # 找到截止日期的索引
        end_date_dt = pd.to_datetime(end_date)
        end_idx = df[df['date'] <= end_date_dt].index[-1] if len(df[df['date'] <= end_date_dt]) > 0 else len(df) - 1
        
        if end_idx < 60:  # 需要至少60天数据计算均量
            continue
        
        # 在截止日期前30日内查找地量期
        low_periods = find_low_volume_periods(df, end_idx)
        
        if not low_periods:
            continue
        
        # 对每个地量期检查是否有天量突破
        for period in low_periods:
            surge = check_surge_breakout(df, period['end_idx'])
            
            if surge:
                results.append({
                    'code': code,
                    'low_days': period['days'],
                    'surge_date': surge['surge_date'].strftime('%Y-%m-%d'),
                    'volume_ratio': surge['volume_ratio'],
                    'breakout_pct': surge['breakout_pct']
                })
                break  # 找到一个就够了
    
    # 输出结果
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_24_doji_to_surge/independent/openclaw/doji_surge.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,地量期天数,天量日期,量比(天量/60日均量),突破涨幅(%)\n")
        
        if results:
            for r in results:
                f.write(f"{r['code']},{r['low_days']},{r['surge_date']},{r['volume_ratio']:.2f},{r['breakout_pct']:.2f}\n")
            print(f"\n找到 {len(results)} 只符合条件的股票")
        else:
            f.write("# 无符合条件的股票\n")
            print("\n无符合条件的股票")
    
    print(f"结果已保存到: {output_file}")

if __name__ == '__main__':
    main()
