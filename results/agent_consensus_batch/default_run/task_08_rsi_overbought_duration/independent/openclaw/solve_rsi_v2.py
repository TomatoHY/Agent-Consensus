#!/usr/bin/env python3
"""
RSI超买持续时间分析 - 使用baostock
"""

import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import time

def calculate_rsi(prices, period=14):
    """
    计算RSI指标（Wilder平滑法）
    """
    if len(prices) < period + 1:
        return pd.Series([np.nan] * len(prices), index=prices.index)
    
    # 计算价格变化
    delta = prices.diff()
    
    # 分离上涨和下跌
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    # Wilder平滑法
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    # 计算RS和RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def get_chinext_stocks():
    """获取创业板股票列表"""
    try:
        lg = bs.login()
        if lg.error_code != '0':
            print(f"登录失败: {lg.error_msg}")
            return []
        
        # 获取创业板股票（sz.300开头）
        rs = bs.query_stock_basic(code_name="sz.300")
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        bs.logout()
        
        # 返回股票代码列表（去掉sz.前缀）
        return [code.replace('sz.', '') for code in df['code'].tolist()]
    except Exception as e:
        print(f"获取创业板股票列表失败: {e}")
        bs.logout()
        return []

def get_stock_data_baostock(stock_code, end_date='2024-10-31', days=50):
    """
    使用baostock获取股票历史数据
    """
    try:
        # 计算开始日期
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=days*2)
        start_date = start_dt.strftime('%Y-%m-%d')
        
        # 登录
        lg = bs.login()
        if lg.error_code != '0':
            return None
        
        # 获取日K线数据
        rs = bs.query_history_k_data_plus(
            f"sz.{stock_code}",
            "date,code,close",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="2"  # 前复权
        )
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        bs.logout()
        
        if len(data_list) == 0:
            return None
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        df['date'] = pd.to_datetime(df['date'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna()
        df = df.sort_values('date')
        
        return df
        
    except Exception as e:
        bs.logout()
        return None

def analyze_rsi_overbought(stock_code, end_date='2024-10-31'):
    """
    分析单只股票的RSI超买情况
    """
    try:
        df = get_stock_data_baostock(stock_code, end_date, days=60)
        
        if df is None or len(df) < 34:
            return (stock_code, 0)
        
        # 计算RSI
        df['RSI'] = calculate_rsi(df['close'], period=14)
        
        # 取最后20个交易日
        last_20 = df.tail(20)
        
        # 统计RSI > 70的天数
        overbought_days = (last_20['RSI'] > 70).sum()
        
        return (stock_code, int(overbought_days))
        
    except Exception as e:
        return (stock_code, 0)

def main():
    """主函数"""
    result_dir = Path('/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_08_rsi_overbought_duration/independent/openclaw')
    result_file = result_dir / 'rsi_overbought_top3.txt'
    
    print("开始分析RSI超买持续时间（使用baostock）...")
    print("=" * 60)
    
    # 1. 获取创业板股票列表
    print("1. 获取创业板股票列表...")
    chinext_stocks = get_chinext_stocks()
    print(f"   找到 {len(chinext_stocks)} 只创业板股票")
    
    if len(chinext_stocks) == 0:
        print("错误：未能获取创业板股票列表")
        return
    
    # 2. 分析每只股票
    print("\n2. 分析每只股票的RSI超买情况...")
    results = []
    
    for i, stock_code in enumerate(chinext_stocks, 1):
        if i % 50 == 0:
            print(f"   进度: {i}/{len(chinext_stocks)}")
        
        code, days = analyze_rsi_overbought(stock_code)
        if days > 0:
            results.append((code, days))
            print(f"   {code}: {days}天")
        
        # 添加小延迟避免请求过快
        time.sleep(0.05)
    
    print(f"\n   完成分析，找到 {len(results)} 只有超买记录的股票")
    
    # 3. 排序并取前3名
    print("\n3. 排序并取前3名...")
    results.sort(key=lambda x: x[1], reverse=True)
    top3 = results[:3]
    
    # 4. 写入结果文件
    print("\n4. 写入结果文件...")
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,超买天数\n")
        for code, days in top3:
            f.write(f"{code},{days}\n")
    
    print(f"\n结果已保存到: {result_file}")
    print("\n前3名股票：")
    print("-" * 30)
    for code, days in top3:
        print(f"{code}: {days}天")
    print("=" * 60)

if __name__ == '__main__':
    main()
