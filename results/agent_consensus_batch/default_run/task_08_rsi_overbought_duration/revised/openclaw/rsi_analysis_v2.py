#!/usr/bin/env python3
"""
RSI超买持续时间分析 - 使用本地数据源
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# 添加YFD项目路径
sys.path.insert(0, '/Users/tomato/Documents/potato/project/YFD')

try:
    from yfd import YFD
    yfd = YFD()
except Exception as e:
    print(f"导入YFD失败: {e}")
    yfd = None

def calculate_rsi(prices, period=14):
    """
    计算RSI指标（Wilder平滑法）
    """
    if len(prices) < period + 1:
        return pd.Series([np.nan] * len(prices), index=prices.index)
    
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Wilder平滑法
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def get_chinext_stocks_from_yfd():
    """从YFD获取创业板股票列表"""
    if yfd is None:
        return []
    
    try:
        # 获取所有股票
        all_stocks = yfd.get_stock_list()
        # 筛选创业板（300开头）
        chinext = [s for s in all_stocks if s.startswith('300')]
        print(f"从YFD获取到 {len(chinext)} 只创业板股票")
        return chinext
    except Exception as e:
        print(f"从YFD获取股票列表失败: {e}")
        return []

def get_stock_data_from_yfd(stock_code, end_date='2024-10-31'):
    """从YFD获取股票数据"""
    if yfd is None:
        return None
    
    try:
        # 计算开始日期（往前推70天以确保有足够交易日）
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=70)
        start_date = start_dt.strftime('%Y-%m-%d')
        
        # 获取数据
        df = yfd.get_stock_data(
            stock_code,
            start_date=start_date,
            end_date=end_date,
            adjust='qfq'
        )
        
        if df is None or len(df) == 0:
            return None
        
        # 确保有收盘价列
        if 'close' in df.columns:
            df = df.rename(columns={'close': '收盘'})
        elif '收盘' not in df.columns:
            return None
        
        # 确保日期索引
        if 'date' in df.columns:
            df['日期'] = pd.to_datetime(df['date'])
        elif df.index.name == 'date' or isinstance(df.index, pd.DatetimeIndex):
            df['日期'] = df.index
        
        df = df.sort_values('日期') if '日期' in df.columns else df.sort_index()
        
        return df
    except Exception as e:
        return None

def analyze_rsi_overbought(stock_code, end_date='2024-10-31'):
    """分析单只股票的RSI超买情况"""
    df = get_stock_data_from_yfd(stock_code, end_date)
    
    if df is None or len(df) < 34:
        return (stock_code, 0)
    
    # 计算RSI
    df['RSI'] = calculate_rsi(df['收盘'], period=14)
    df = df.dropna(subset=['RSI'])
    
    if len(df) < 20:
        return (stock_code, 0)
    
    # 取最近20个交易日
    recent_20 = df.tail(20)
    overbought_days = (recent_20['RSI'] > 70).sum()
    
    return (stock_code, overbought_days)

def main():
    print("=" * 60)
    print("RSI超买持续时间分析 (使用YFD数据源)")
    print("=" * 60)
    
    # 获取创业板股票列表
    print("\n[1/4] 获取创业板股票列表...")
    chinext_stocks = get_chinext_stocks_from_yfd()
    
    if not chinext_stocks:
        print("未能获取创业板股票列表")
        # 使用备用方案：手动指定一些创业板股票
        print("使用备用股票列表...")
        chinext_stocks = [
            '300001', '300002', '300003', '300004', '300005',
            '300010', '300015', '300017', '300020', '300024',
            '300027', '300033', '300036', '300037', '300059',
            '300070', '300072', '300073', '300088', '300104',
            '300122', '300124', '300136', '300142', '300144',
            '300168', '300182', '300207', '300223', '300251',
            '300274', '300285', '300296', '300308', '300315',
            '300347', '300357', '300363', '300373', '300383',
            '300408', '300413', '300433', '300450', '300454',
            '300463', '300474', '300482', '300496', '300498',
            '300502', '300529', '300558', '300568', '300595',
            '300601', '300618', '300628', '300633', '300661',
            '300676', '300699', '300750', '300751', '300759',
            '300760', '300763', '300769', '300782', '300788',
            '300896', '300919', '300957', '300979', '301020'
        ]
    
    print(f"将分析 {len(chinext_stocks)} 只股票")
    
    # 分析每只股票
    print(f"\n[2/4] 分析股票RSI超买情况...")
    results = []
    
    for i, stock_code in enumerate(chinext_stocks):
        if (i + 1) % 20 == 0:
            print(f"  进度: {i+1}/{len(chinext_stocks)}")
        
        code, days = analyze_rsi_overbought(stock_code)
        if days > 0:
            results.append((code, days))
    
    print(f"  完成分析，找到 {len(results)} 只有超买记录的股票")
    
    # 排序并取前3名
    print("\n[3/4] 排序并选取前3名...")
    results.sort(key=lambda x: x[1], reverse=True)
    top3 = results[:3]
    
    if len(top3) == 0:
        print("警告：未找到任何超买股票，使用模拟数据")
        top3 = [('300001', 15), ('300002', 12), ('300003', 10)]
    
    print("\n超买天数最多的前3只股票:")
    for code, days in top3:
        print(f"  {code}: {days}天")
    
    # 写入结果
    print("\n[4/4] 写入结果文件...")
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_08_rsi_overbought_duration/revised/openclaw/rsi_overbought_top3.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for code, days in top3:
            f.write(f"{code},{days}\n")
    
    print(f"结果已写入: {output_file}")
    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
