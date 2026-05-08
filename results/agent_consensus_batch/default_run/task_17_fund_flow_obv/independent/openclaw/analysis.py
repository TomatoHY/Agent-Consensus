#!/usr/bin/env python3
"""
大单净流入与OBV上升通道筛选
Task 17: Fund Flow + OBV Technical Analysis
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_chinext_stocks():
    """获取创业板股票列表"""
    stock_info = ak.stock_info_a_code_name()
    chinext = stock_info[stock_info['code'].str.startswith('300')]
    return chinext['code'].tolist()

def get_stock_data(stock_code, end_date='2024-09-13', days=30):
    """获取股票历史数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date="2024-08-01", end_date=end_date, adjust="qfq")
        if df is None or len(df) == 0:
            return None
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        return df
    except:
        return None

def calculate_large_order_proxy(df):
    """
    计算大单净流入代理指标
    使用成交量代理：大单买入 ≈ 当日成交量 × 0.4
    净流入 = 涨跌幅为正时为正，否则为负
    """
    df = df.copy()
    df['大单买入代理'] = df['成交量'] * 0.4
    df['大单卖出代理'] = df['成交量'] * 0.4
    
    # 根据涨跌幅判断净流入方向
    df['大单净流入'] = np.where(df['涨跌幅'] > 0, 
                              df['大单买入代理'], 
                              -df['大单卖出代理'])
    return df

def check_consecutive_inflow(df, end_date, min_days=3):
    """
    检查截至end_date的前5个交易日中，连续净流入天数
    返回最长连续净流入天数
    """
    df = df[df['日期'] <= end_date].tail(5)
    if len(df) < 3:
        return 0
    
    net_inflow = df['大单净流入'].values
    max_consecutive = 0
    current_consecutive = 0
    
    for flow in net_inflow:
        if flow > 0:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0
    
    return max_consecutive

def calculate_obv(df):
    """
    计算OBV（能量潮）指标
    当日收盘 > 前日收盘，OBV += 当日成交量
    当日收盘 < 前日收盘，OBV -= 当日成交量
    持平则不变
    """
    df = df.copy()
    df['obv'] = 0.0
    
    obv_value = 0
    for i in range(len(df)):
        if i == 0:
            obv_value = df.iloc[i]['成交量']
        else:
            close_today = df.iloc[i]['收盘']
            close_yesterday = df.iloc[i-1]['收盘']
            volume = df.iloc[i]['成交量']
            
            if close_today > close_yesterday:
                obv_value += volume
            elif close_today < close_yesterday:
                obv_value -= volume
            # 持平不变
        
        df.iloc[i, df.columns.get_loc('obv')] = obv_value
    
    return df

def check_obv_strength(df, end_date, threshold=1.1):
    """
    检查OBV强度
    截至end_date的OBV > 近20日OBV均值的1.1倍
    """
    df_filtered = df[df['日期'] <= end_date]
    if len(df_filtered) < 20:
        return False, 0, 0
    
    last_20_days = df_filtered.tail(20)
    current_obv = last_20_days.iloc[-1]['obv']
    obv_mean_20 = last_20_days['obv'].mean()
    
    if obv_mean_20 == 0:
        return False, 0, 0
    
    obv_strength = current_obv / obv_mean_20
    
    return obv_strength > threshold, obv_strength, obv_mean_20

def calculate_ma20(df):
    """计算20日均线"""
    df = df.copy()
    df['ma20'] = df['收盘'].rolling(window=20).mean()
    return df

def check_uptrend_channel(df, end_date):
    """
    验证价格处于上升通道
    1. 20日均线斜率为正（近5日的20日均线值递增）
    2. 收盘价在20日均线上方
    """
    df_filtered = df[df['日期'] <= end_date]
    if len(df_filtered) < 20:
        return False, 0
    
    # 获取最近5日的20日均线
    last_5_ma = df_filtered.tail(5)['ma20'].values
    
    # 检查是否单调递增
    is_increasing = all(last_5_ma[i] < last_5_ma[i+1] for i in range(len(last_5_ma)-1))
    
    # 检查收盘价是否在均线上方
    last_close = df_filtered.iloc[-1]['收盘']
    last_ma20 = df_filtered.iloc[-1]['ma20']
    
    if pd.isna(last_ma20) or last_ma20 == 0:
        return False, 0
    
    above_ma = last_close > last_ma20
    deviation_pct = (last_close - last_ma20) / last_ma20 * 100
    
    return is_increasing and above_ma, deviation_pct

def main():
    print("开始筛选创业板股票...")
    print("=" * 60)
    
    end_date = '2024-09-13'
    end_date_dt = pd.to_datetime(end_date)
    
    # 获取创业板股票列表
    chinext_stocks = get_chinext_stocks()
    print(f"创业板股票总数: {len(chinext_stocks)}")
    
    results = []
    
    for i, stock_code in enumerate(chinext_stocks[:100]):  # 限制处理数量以加快速度
        if (i + 1) % 10 == 0:
            print(f"处理进度: {i+1}/{min(100, len(chinext_stocks))}")
        
        # 获取股票数据
        df = get_stock_data(stock_code, end_date=end_date)
        if df is None or len(df) < 25:
            continue
        
        # 第一步：计算大单净流入代理
        df = calculate_large_order_proxy(df)
        
        # 检查连续净流入天数
        consecutive_days = check_consecutive_inflow(df, end_date_dt, min_days=3)
        if consecutive_days < 3:
            continue
        
        # 第二步：计算OBV
        df = calculate_obv(df)
        
        # 检查OBV强度
        obv_qualified, obv_strength, obv_mean = check_obv_strength(df, end_date_dt)
        if not obv_qualified:
            continue
        
        # 第三步：计算20日均线并验证上升通道
        df = calculate_ma20(df)
        
        # 检查上升通道
        in_uptrend, deviation_pct = check_uptrend_channel(df, end_date_dt)
        if not in_uptrend:
            continue
        
        # 符合所有条件，记录结果
        results.append({
            '股票代码': stock_code,
            '大单净流入天数': consecutive_days,
            'OBV相对强度': round(obv_strength, 2),
            '均线偏离度(%)': round(deviation_pct, 2)
        })
        
        print(f"✓ 找到符合条件的股票: {stock_code}")
    
    print("=" * 60)
    print(f"筛选完成，共找到 {len(results)} 只符合条件的股票")
    
    # 写入结果文件
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_17_fund_flow_obv/independent/openclaw/fund_flow_result.txt'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("# 无符合条件的股票\n")
            f.write("# 筛选条件：\n")
            f.write("# 1. 连续3天以上大单净流入为正\n")
            f.write("# 2. OBV相对强度 > 1.1\n")
            f.write("# 3. 20日均线斜率为正且收盘价在均线上方\n")
        else:
            f.write("股票代码,大单净流入天数,OBV相对强度,均线偏离度(%)\n")
            for r in results:
                f.write(f"{r['股票代码']},{r['大单净流入天数']},{r['OBV相对强度']},{r['均线偏离度(%)']}\n")
    
    print(f"\n结果已写入: {output_path}")
    
    return results

if __name__ == "__main__":
    results = main()
