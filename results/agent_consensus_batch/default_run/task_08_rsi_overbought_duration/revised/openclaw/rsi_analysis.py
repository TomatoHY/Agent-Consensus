#!/usr/bin/env python3
"""
RSI超买持续时间分析
计算创业板中以 2024-10-31 为截止交易日的前20个交易日内，RSI指标在超买区（>70）停留时间最长的3只股票
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def calculate_rsi(prices, period=14):
    """
    计算RSI指标（Wilder平滑法）
    RS = 平均上涨幅度 / 平均下跌幅度（14日）
    RSI = 100 - 100 / (1 + RS)
    """
    if len(prices) < period + 1:
        return pd.Series([np.nan] * len(prices), index=prices.index)
    
    # 计算价格变化
    delta = prices.diff()
    
    # 分离上涨和下跌
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Wilder平滑法：第一个值用简单平均，后续用指数平滑
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    # 计算RS和RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def get_chinext_stocks():
    """获取创业板股票列表（300开头）"""
    try:
        # 获取A股实时行情数据
        stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
        # 筛选创业板股票（代码以300开头）
        chinext_stocks = stock_zh_a_spot_em_df[
            stock_zh_a_spot_em_df['代码'].str.startswith('300')
        ]['代码'].tolist()
        print(f"获取到 {len(chinext_stocks)} 只创业板股票")
        return chinext_stocks
    except Exception as e:
        print(f"获取创业板股票列表失败: {e}")
        return []

def get_stock_data(stock_code, end_date='20241031', days=50):
    """
    获取股票历史数据
    需要约34个交易日数据（14日预热 + 20日分析）
    实际获取更多以应对节假日
    """
    try:
        # 计算开始日期（往前推更多天数以确保有足够交易日）
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        start_dt = end_dt - timedelta(days=days)
        start_date = start_dt.strftime('%Y%m%d')
        
        # 获取历史行情数据
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        
        if df is None or len(df) == 0:
            return None
        
        # 确保日期列为datetime类型
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        
        return df
    except Exception as e:
        # print(f"获取股票 {stock_code} 数据失败: {e}")
        return None

def analyze_rsi_overbought(stock_code, end_date='20241031'):
    """
    分析单只股票的RSI超买情况
    返回：(股票代码, 超买天数)
    """
    # 获取历史数据
    df = get_stock_data(stock_code, end_date)
    
    if df is None or len(df) < 34:  # 至少需要34个交易日
        return (stock_code, 0)
    
    # 计算RSI
    df['RSI'] = calculate_rsi(df['收盘'], period=14)
    
    # 去除NaN值
    df = df.dropna(subset=['RSI'])
    
    if len(df) < 20:
        return (stock_code, 0)
    
    # 取最近20个交易日
    recent_20 = df.tail(20)
    
    # 统计RSI > 70的天数
    overbought_days = (recent_20['RSI'] > 70).sum()
    
    return (stock_code, overbought_days)

def main():
    print("=" * 60)
    print("RSI超买持续时间分析")
    print("=" * 60)
    
    # 1. 获取创业板股票列表
    print("\n[1/4] 获取创业板股票列表...")
    chinext_stocks = get_chinext_stocks()
    
    if not chinext_stocks:
        print("未能获取创业板股票列表，退出")
        return
    
    # 2. 分析每只股票的RSI超买情况
    print(f"\n[2/4] 分析 {len(chinext_stocks)} 只股票的RSI超买情况...")
    results = []
    
    for i, stock_code in enumerate(chinext_stocks):
        if (i + 1) % 50 == 0:
            print(f"  进度: {i+1}/{len(chinext_stocks)}")
        
        code, days = analyze_rsi_overbought(stock_code)
        if days > 0:  # 只保留有超买天数的股票
            results.append((code, days))
    
    print(f"  完成分析，找到 {len(results)} 只有超买记录的股票")
    
    # 3. 排序并取前3名
    print("\n[3/4] 排序并选取前3名...")
    results.sort(key=lambda x: x[1], reverse=True)
    top3 = results[:3]
    
    print("\n超买天数最多的前3只股票:")
    for code, days in top3:
        print(f"  {code}: {days}天")
    
    # 4. 写入结果文件
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
