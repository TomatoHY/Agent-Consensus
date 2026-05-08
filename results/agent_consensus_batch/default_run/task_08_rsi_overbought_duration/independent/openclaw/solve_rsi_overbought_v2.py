#!/usr/bin/env python3
"""
RSI超买持续时间分析 - 无代理版本
计算创业板股票在2024-10-31前20个交易日内RSI>70的天数
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import os

# 禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
if 'HTTP_PROXY' in os.environ:
    del os.environ['HTTP_PROXY']
if 'HTTPS_PROXY' in os.environ:
    del os.environ['HTTPS_PROXY']
if 'http_proxy' in os.environ:
    del os.environ['http_proxy']
if 'https_proxy' in os.environ:
    del os.environ['https_proxy']

def calculate_rsi(prices, period=14):
    """
    计算RSI指标（Wilder平滑法）
    
    Args:
        prices: 收盘价序列
        period: RSI周期，默认14
    
    Returns:
        RSI值序列
    """
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # 初始平均值
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    rsi_values = []
    
    # 第一个RSI值
    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100 - 100 / (1 + rs))
    
    # 后续RSI值使用Wilder平滑
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - 100 / (1 + rs))
    
    # 返回完整的RSI序列（前period个值为NaN）
    result = [np.nan] * period + rsi_values
    return np.array(result)


def get_chinext_stocks():
    """获取创业板股票列表"""
    try:
        # 获取创业板股票
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"获取创业板股票列表失败: {e}")
        return []


def get_stock_data(stock_code, end_date, days=40):
    """
    获取股票历史数据
    
    Args:
        stock_code: 股票代码
        end_date: 截止日期
        days: 需要的交易日数量
    """
    try:
        # 计算开始日期（多取一些以确保有足够的交易日）
        start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=days*2)).strftime('%Y%m%d')
        
        # 获取历史数据
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df is None or len(df) == 0:
            return None
        
        # 确保按日期排序
        df = df.sort_values('日期')
        
        # 只取最近的days个交易日
        df = df.tail(days)
        
        return df
    except Exception as e:
        # 静默失败，不打印错误
        return None


def analyze_rsi_overbought(end_date='20241031', analysis_days=20, rsi_period=14):
    """
    分析RSI超买持续时间
    
    Args:
        end_date: 截止日期
        analysis_days: 分析的交易日数量
        rsi_period: RSI周期
    """
    print(f"开始分析RSI超买持续时间...")
    print(f"截止日期: {end_date}")
    print(f"分析周期: 最近{analysis_days}个交易日")
    print(f"RSI周期: {rsi_period}日")
    print()
    
    # 获取创业板股票列表
    chinext_stocks = get_chinext_stocks()
    print(f"获取到 {len(chinext_stocks)} 只创业板股票")
    
    if len(chinext_stocks) == 0:
        print("未获取到创业板股票，退出")
        return []
    
    results = []
    total = len(chinext_stocks)
    success_count = 0
    
    # 需要获取的总交易日数：分析期 + RSI预热期
    required_days = analysis_days + rsi_period
    
    for idx, stock_code in enumerate(chinext_stocks, 1):
        if idx % 100 == 0:
            print(f"处理进度: {idx}/{total}, 成功: {success_count}")
        
        # 获取股票数据
        df = get_stock_data(stock_code, end_date, days=required_days)
        
        if df is None or len(df) < required_days:
            continue
        
        success_count += 1
        
        # 提取收盘价
        close_prices = df['收盘'].values
        
        # 计算RSI
        rsi_values = calculate_rsi(close_prices, period=rsi_period)
        
        # 取最近analysis_days个交易日的RSI
        recent_rsi = rsi_values[-analysis_days:]
        
        # 统计RSI > 70的天数
        overbought_days = np.sum(recent_rsi > 70)
        
        if overbought_days > 0:
            results.append({
                'code': stock_code,
                'overbought_days': int(overbought_days)
            })
    
    print(f"\n分析完成，成功获取 {success_count} 只股票数据")
    print(f"共 {len(results)} 只股票有超买记录")
    
    # 按超买天数降序排序
    results.sort(key=lambda x: x['overbought_days'], reverse=True)
    
    return results


def main():
    """主函数"""
    # 分析RSI超买
    results = analyze_rsi_overbought(end_date='20241031', analysis_days=20, rsi_period=14)
    
    if len(results) == 0:
        print("\n警告：未找到任何超买股票")
        return
    
    # 取前3名
    top3 = results[:3]
    
    print("\n=== RSI超买持续时间 TOP 3 ===")
    for item in top3:
        print(f"{item['code']}: {item['overbought_days']}天")
    
    # 写入结果文件
    output_file = Path(__file__).parent / "rsi_overbought_top3.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in top3:
            f.write(f"{item['code']},{item['overbought_days']}\n")
    
    print(f"\n结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
