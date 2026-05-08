#!/usr/bin/env python3
"""
MACD柱状图正转后连续增长统计
统计创业板中MACD histogram从负转正后连续增长超过5天的股票数量
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import warnings
import time
import os

warnings.filterwarnings('ignore')

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


def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    """计算指数移动平均线"""
    return series.ewm(span=span, adjust=False).mean()


def calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算MACD指标
    DIFF = EMA12 - EMA26
    DEA = EMA9(DIFF)
    histogram = DIFF - DEA
    """
    df = df.copy()
    
    # 计算EMA12和EMA26
    df['ema12'] = calculate_ema(df['close'], 12)
    df['ema26'] = calculate_ema(df['close'], 26)
    
    # 计算DIFF
    df['diff'] = df['ema12'] - df['ema26']
    
    # 计算DEA (DIFF的9日EMA)
    df['dea'] = calculate_ema(df['diff'], 9)
    
    # 计算histogram (柱状图)
    df['histogram'] = df['diff'] - df['dea']
    
    return df


def check_consecutive_increase(histogram_values: np.ndarray, start_idx: int, min_days: int = 5) -> bool:
    """
    检查从start_idx开始，histogram是否连续递增至少min_days天
    
    Args:
        histogram_values: histogram数组
        start_idx: 起始索引（金叉当日）
        min_days: 最少连续递增天数
    
    Returns:
        是否满足连续递增条件
    """
    # 需要检查start_idx之后的min_days天
    if start_idx + min_days >= len(histogram_values):
        return False
    
    # 检查连续min_days天是否严格递增
    for i in range(min_days):
        if histogram_values[start_idx + i + 1] <= histogram_values[start_idx + i]:
            return False
    
    return True


def find_golden_cross_with_consecutive_increase(df: pd.DataFrame, analysis_days: int = 60) -> bool:
    """
    查找MACD histogram从负转正后连续增长超过5天的情况
    
    Args:
        df: 包含histogram的DataFrame
        analysis_days: 分析的天数窗口
    
    Returns:
        是否存在满足条件的情况
    """
    if len(df) < analysis_days + 5:
        return False
    
    # 只分析最近analysis_days天
    df_analysis = df.iloc[-analysis_days:].reset_index(drop=True)
    histogram = df_analysis['histogram'].values
    
    # 查找从负转正的位置
    for i in range(len(histogram) - 6):
        # 检查是否从负转正（前一天<0，当天>=0）
        if i > 0 and histogram[i-1] < 0 and histogram[i] >= 0:
            # 检查从金叉当日开始，后续5天是否连续递增
            if check_consecutive_increase(histogram, i, min_days=5):
                return True
    
    return False


def get_chinext_stocks() -> list:
    """获取创业板股票列表"""
    try:
        # 获取创业板股票
        stock_info = ak.stock_info_a_code_name()
        # 创业板代码以300或301开头
        chinext_stocks = stock_info[
            stock_info['code'].str.startswith('300') | 
            stock_info['code'].str.startswith('301')
        ]['code'].tolist()
        return chinext_stocks
    except Exception as e:
        print(f"获取创业板股票列表失败: {e}")
        return []


def get_stock_data(stock_code: str, end_date: str = '20241231', days: int = 120, max_retries: int = 3) -> Optional[pd.DataFrame]:
    """
    获取股票K线数据，带重试机制
    
    Args:
        stock_code: 股票代码
        end_date: 截止日期
        days: 获取天数
        max_retries: 最大重试次数
    
    Returns:
        DataFrame或None
    """
    for attempt in range(max_retries):
        try:
            # 计算开始日期
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            start_dt = end_dt - timedelta(days=days + 60)
            start_date = start_dt.strftime('%Y%m%d')
            
            # 获取日线数据
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df is None or len(df) == 0:
                return None
            
            # 重命名列
            df.columns = [col.lower() for col in df.columns]
            df = df.rename(columns={'日期': 'date', '收盘': 'close'})
            
            if 'date' not in df.columns or 'close' not in df.columns:
                return None
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)  # 短暂延迟后重试
                continue
            return None
    
    return None


def main():
    """主函数"""
    print("开始统计MACD柱状图正转后连续增长的股票...")
    
    # 获取创业板股票列表
    print("正在获取创业板股票列表...")
    chinext_stocks = get_chinext_stocks()
    print(f"获取到 {len(chinext_stocks)} 只创业板股票")
    
    if len(chinext_stocks) == 0:
        print("未获取到创业板股票，退出")
        return
    
    # 统计符合条件的股票
    qualified_stocks = []
    total_processed = 0
    failed_count = 0
    
    for i, stock_code in enumerate(chinext_stocks):
        if (i + 1) % 50 == 0:
            print(f"处理进度: {i+1}/{len(chinext_stocks)}, 成功: {total_processed}, 失败: {failed_count}")
        
        # 获取股票数据
        df = get_stock_data(stock_code, end_date='20241231', days=120)
        
        if df is None or len(df) < 90:
            failed_count += 1
            continue
        
        total_processed += 1
        
        # 计算MACD
        df = calculate_macd(df)
        
        # 检查是否存在histogram从负转正后连续增长5天的情况
        if find_golden_cross_with_consecutive_increase(df, analysis_days=60):
            qualified_stocks.append(stock_code)
    
    # 输出结果
    count = len(qualified_stocks)
    print(f"\n处理完成！")
    print(f"总共处理: {total_processed} 只股票")
    print(f"失败: {failed_count} 只股票")
    print(f"符合条件的股票总数: {count}")
    
    # 写入结果文件
    result_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_10_macd_histogram_trend/independent/openclaw/macd_strength_count.txt'
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(f"符合条件的股票总数: {count}\n")
    
    print(f"\n结果已写入: {result_path}")
    
    # 输出部分符合条件的股票代码
    if qualified_stocks:
        print(f"\n部分符合条件的股票代码: {qualified_stocks[:10]}")


if __name__ == '__main__':
    main()
