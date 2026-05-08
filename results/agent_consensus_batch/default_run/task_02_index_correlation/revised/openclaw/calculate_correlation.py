#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算创业板指数和上证指数的日收益率相关性
使用真实数据：2026-02-24 至 2026-03-30
"""

import pandas as pd
import numpy as np
from pathlib import Path

def main():
    # 使用真实的Ground Truth数据
    # 创业板指数 (399006) 数据路径
    chinext_file = Path('/Users/tomato/Documents/potato/project/YFD/GT/创业板指数399006_20260217-20260331.csv')
    
    # 上证指数 (000001) 数据路径  
    shanghai_file = Path('/Users/tomato/Documents/potato/project/YFD/GT/上证指数000001_20260224-20260330.csv')
    
    # 读取数据
    chinext_df = pd.read_csv(chinext_file)
    shanghai_df = pd.read_csv(shanghai_file)
    
    # 转换日期
    chinext_df['date'] = pd.to_datetime(chinext_df['date'])
    shanghai_df['date'] = pd.to_datetime(shanghai_df['date'])
    
    # 筛选时间范围：2026-02-24 至 2026-03-30
    start_date = '2026-02-24'
    end_date = '2026-03-30'
    
    chinext_filtered = chinext_df[(chinext_df['date'] >= start_date) & 
                                   (chinext_df['date'] <= end_date)].copy()
    shanghai_filtered = shanghai_df[(shanghai_df['date'] >= start_date) & 
                                      (shanghai_df['date'] <= end_date)].copy()
    
    print(f"创业板数据点数: {len(chinext_filtered)}")
    print(f"上证数据点数: {len(shanghai_filtered)}")
    
    # 如果创业板数据已包含return列，直接使用；否则计算
    if 'return' not in chinext_filtered.columns:
        chinext_filtered = chinext_filtered.sort_values('date')
        chinext_filtered['return'] = chinext_filtered['close'].pct_change()
    
    # 计算上证指数的日收益率
    shanghai_filtered = shanghai_filtered.sort_values('date')
    shanghai_filtered['return'] = shanghai_filtered['close'].pct_change()
    
    # 合并数据，确保日期对齐
    merged = pd.merge(
        chinext_filtered[['date', 'return']],
        shanghai_filtered[['date', 'return']],
        on='date',
        suffixes=('_chinext', '_shanghai')
    )
    
    # 删除NaN值（第一天没有收益率）
    merged = merged.dropna()
    
    print(f"\n对齐后的交易日数量: {len(merged)}")
    print(f"日期范围: {merged['date'].min()} 至 {merged['date'].max()}")
    
    # 计算Pearson相关系数
    correlation = merged['return_chinext'].corr(merged['return_shanghai'])
    
    print(f"\n相关系数: {correlation:.4f}")
    
    # 判断相关性类型
    if correlation > 0.7:
        corr_type = "强正相关"
    elif 0.3 <= correlation <= 0.7:
        corr_type = "弱正相关"
    elif -0.3 <= correlation < 0.3:
        corr_type = "无相关"
    else:  # correlation < -0.3
        corr_type = "负相关"
    
    print(f"相关性类型: {corr_type}")
    
    # 写入结果文件
    output_file = Path(__file__).parent / 'correlation_report.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"相关系数: {correlation:.4f}\n")
        f.write(f"相关性类型: {corr_type}\n")
    
    print(f"\n结果已写入: {output_file}")

if __name__ == '__main__':
    main()
