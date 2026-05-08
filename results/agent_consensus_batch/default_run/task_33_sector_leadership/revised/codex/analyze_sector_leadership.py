#!/usr/bin/env python3
"""
创业板行业板块龙头股识别
Identify sector leadership stocks in ChiNext market
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Mock data generator for demonstration
# In production, this would connect to real market data APIs
def generate_mock_chinext_data():
    """Generate mock ChiNext stock data for demonstration"""
    np.random.seed(42)
    
    sectors = ['医药', '半导体', '新能源', '消费电子', '软件', '传媒', '新材料', '生物科技']
    stocks_per_sector = 15
    
    data = []
    stock_id = 300001
    
    for sector in sectors:
        for i in range(stocks_per_sector):
            # Generate 20-day returns with sector bias
            sector_bias = np.random.uniform(-0.1, 0.3)
            stock_return_20d = sector_bias + np.random.uniform(-0.15, 0.25)
            
            # Generate other metrics
            market_cap = np.random.uniform(30, 300)  # 亿元
            turnover_rate = np.random.uniform(2, 15)  # %
            rsi = np.random.uniform(30, 85)
            
            # MACD signal
            macd_golden_cross = np.random.choice([True, False], p=[0.3, 0.7])
            
            # 60-day high
            is_60d_high = np.random.choice([True, False], p=[0.2, 0.8])
            
            data.append({
                'code': f'{stock_id:06d}',
                'sector': sector,
                'return_20d': stock_return_20d,
                'market_cap': market_cap,
                'turnover_rate': turnover_rate,
                'rsi': rsi,
                'macd_golden_cross': macd_golden_cross,
                'is_60d_high': is_60d_high
            })
            stock_id += 1
    
    return pd.DataFrame(data)

def calculate_sector_returns(df):
    """计算各行业等权平均涨幅"""
    sector_returns = df.groupby('sector')['return_20d'].mean().sort_values(ascending=False)
    return sector_returns

def calculate_relative_strength(df, sector_returns):
    """计算个股相对强度 RS = 个股涨幅 / 行业平均涨幅"""
    df['sector_avg_return'] = df['sector'].map(sector_returns)
    df['RS'] = df['return_20d'] / df['sector_avg_return']
    return df

def filter_leaders(df, top_sectors):
    """筛选龙头股"""
    # 只保留强势行业
    df_filtered = df[df['sector'].isin(top_sectors)].copy()
    
    # 第一步：RS > 1.5
    df_filtered = df_filtered[df_filtered['RS'] > 1.5]
    
    # 第二步：市值 > 50亿
    df_filtered = df_filtered[df_filtered['market_cap'] > 50]
    
    # 第三步：换手率 > 5%
    df_filtered = df_filtered[df_filtered['turnover_rate'] > 5]
    
    # 第四步：MACD金叉
    df_filtered = df_filtered[df_filtered['macd_golden_cross'] == True]
    
    # 第五步：RSI > 60
    df_filtered = df_filtered[df_filtered['rsi'] > 60]
    
    # 第六步：创60日新高
    df_filtered = df_filtered[df_filtered['is_60d_high'] == True]
    
    return df_filtered

def main():
    print("=" * 60)
    print("创业板行业板块龙头股识别系统")
    print("ChiNext Sector Leadership Stock Identification")
    print("=" * 60)
    
    # 生成数据
    print("\n[步骤1] 加载创业板股票数据...")
    df = generate_mock_chinext_data()
    print(f"共加载 {len(df)} 只创业板股票，涵盖 {df['sector'].nunique()} 个行业")
    
    # 计算行业平均涨幅
    print("\n[步骤2] 计算各行业近20日等权平均涨幅...")
    sector_returns = calculate_sector_returns(df)
    print("\n行业涨幅排名：")
    for sector, ret in sector_returns.items():
        print(f"  {sector}: {ret*100:.2f}%")
    
    # 选出前3强势行业
    top_3_sectors = sector_returns.head(3).index.tolist()
    print(f"\n前3强势行业：{', '.join(top_3_sectors)}")
    
    # 计算相对强度
    print("\n[步骤3] 计算个股相对强度 RS...")
    df = calculate_relative_strength(df, sector_returns)
    
    # 筛选龙头股
    print("\n[步骤4] 筛选龙头股（RS>1.5, 市值>50亿, 换手率>5%, MACD金叉, RSI>60, 创60日新高）...")
    leaders = filter_leaders(df, top_3_sectors)
    
    print(f"\n共筛选出 {len(leaders)} 只符合条件的龙头股")
    
    # 输出结果
    if len(leaders) > 0:
        output_file = 'sector_leader.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("股票代码,所属行业,RS值,流通市值(亿),换手率(%),RSI\n")
            for _, row in leaders.iterrows():
                f.write(f"{row['code']},{row['sector']},{row['RS']:.2f},{row['market_cap']:.1f},{row['turnover_rate']:.1f},{row['rsi']:.1f}\n")
        
        print(f"\n结果已保存至 {output_file}")
        print("\n龙头股列表：")
        print(leaders[['code', 'sector', 'RS', 'market_cap', 'turnover_rate', 'rsi']].to_string(index=False))
    else:
        output_file = 'sector_leader.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("股票代码,所属行业,RS值,流通市值(亿),换手率(%),RSI\n")
            f.write("# 无符合所有条件的股票\n")
        print(f"\n无符合所有条件的股票，已创建空结果文件 {output_file}")
    
    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
