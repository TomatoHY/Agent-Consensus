#!/usr/bin/env python3
"""
深度调试：查看具体股票的数据情况
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

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
        print(f"Error: {e}")
        return None

def analyze_sample(code):
    """分析样本股票"""
    print(f"\n分析股票: {code}")
    print("=" * 80)
    
    df = get_stock_data(code)
    if df is None:
        print("无法获取数据")
        return
    
    print(f"数据行数: {len(df)}")
    print(f"日期范围: {df['date'].min()} 到 {df['date'].max()}")
    
    # 找到截止日期
    cutoff_date = pd.to_datetime('2024-06-07')
    cutoff_idx = df[df['date'] <= cutoff_date].index[-1] if len(df[df['date'] <= cutoff_date]) > 0 else len(df) - 1
    print(f"截止日期索引: {cutoff_idx}, 日期: {df.loc[cutoff_idx, 'date']}")
    
    # 计算60日均量
    if cutoff_idx >= 59:
        avg_vol_60 = df.loc[cutoff_idx-59:cutoff_idx, 'volume'].mean()
        print(f"\n截止日60日均量: {avg_vol_60:,.0f}")
        print(f"50%阈值: {avg_vol_60 * 0.5:,.0f}")
        print(f"300%阈值: {avg_vol_60 * 3.0:,.0f}")
    
    # 查看最近30天的成交量情况
    start_idx = max(60, cutoff_idx - 29)
    print(f"\n最近30天成交量分析 (索引 {start_idx} 到 {cutoff_idx}):")
    print("-" * 80)
    
    recent_data = df.loc[start_idx:cutoff_idx].copy()
    recent_data['avg_vol_60'] = recent_data.index.map(
        lambda i: df.loc[max(0, i-59):i, 'volume'].mean() if i >= 59 else None
    )
    recent_data['vol_ratio'] = recent_data['volume'] / recent_data['avg_vol_60']
    recent_data['is_low'] = recent_data['vol_ratio'] < 0.5
    recent_data['is_high'] = recent_data['vol_ratio'] > 3.0
    
    print(recent_data[['date', 'volume', 'avg_vol_60', 'vol_ratio', 'is_low', 'is_high']].tail(30).to_string())
    
    print(f"\n统计:")
    print(f"  地量日(<50%): {recent_data['is_low'].sum()}")
    print(f"  天量日(>300%): {recent_data['is_high'].sum()}")
    print(f"  平均量比: {recent_data['vol_ratio'].mean():.2f}")
    print(f"  最小量比: {recent_data['vol_ratio'].min():.2f}")
    print(f"  最大量比: {recent_data['vol_ratio'].max():.2f}")

# 测试几只股票
test_codes = ['300001', '300059', '300750', '300760']

for code in test_codes:
    try:
        analyze_sample(code)
    except Exception as e:
        print(f"分析 {code} 失败: {e}")
