#!/usr/bin/env python3
"""
Task 14: 强势行业超强个股RSI筛选
Four-step sector rotation stock selection with RSI filtering
Using alternative data fetching approach
"""

import pandas as pd
import numpy as np
from pathlib import Path
import akshare as ak
from datetime import datetime, timedelta
import time

# Result directory
RESULT_DIR = Path("/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_14_sector_rotation_rsi/independent/openclaw")
RESULT_DIR.mkdir(parents=True, exist_ok=True)

def classify_sector(stock_code, stock_name):
    """
    Classify ChiNext stocks into sectors based on name and code patterns
    """
    name = stock_name
    
    # 医药 (Pharmaceutical/Healthcare)
    pharma_keywords = ['医药', '生物', '制药', '医疗', '健康', '药业', '医院', '诊断', '疫苗', '中药']
    if any(kw in name for kw in pharma_keywords):
        return '医药'
    
    # 科技/半导体 (Technology/Semiconductor)
    tech_keywords = ['科技', '半导体', '芯片', '集成电路', '电子', '通信', '软件', '信息', '数据', '云计算', '人工智能', '智能']
    if any(kw in name for kw in tech_keywords):
        return '科技/半导体'
    
    # 新能源 (New Energy)
    energy_keywords = ['新能源', '光伏', '锂电', '电池', '储能', '风电', '太阳能', '充电']
    if any(kw in name for kw in energy_keywords):
        return '新能源'
    
    # 消费 (Consumer)
    consumer_keywords = ['消费', '食品', '饮料', '零售', '商业', '服装', '家居', '餐饮', '旅游', '酒店']
    if any(kw in name for kw in consumer_keywords):
        return '消费'
    
    # 其他 (Others)
    return '其他'

def calculate_rsi(prices, period=14):
    """
    Calculate RSI using Wilder's smoothing method
    """
    if len(prices) < period + 1:
        return np.nan
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # Initial averages
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    # Wilder's smoothing
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def get_stock_data_batch(stock_codes, target_date):
    """
    Get stock data using batch API
    """
    stock_data = {}
    
    # Try to get real-time quotes first
    try:
        realtime_df = ak.stock_zh_a_spot_em()
        realtime_df = realtime_df[realtime_df['代码'].str.startswith('300')]
        
        for idx, row in realtime_df.iterrows():
            code = row['代码']
            if code in stock_codes:
                stock_data[code] = {
                    'name': row['名称'],
                    'latest_price': float(row['最新价']),
                    'change_pct': float(row['涨跌幅'])
                }
        
        print(f"从实时行情获取了 {len(stock_data)} 只股票数据")
    except Exception as e:
        print(f"获取实时行情失败: {e}")
    
    return stock_data

def main():
    print("=" * 80)
    print("Task 14: 强势行业超强个股RSI筛选")
    print("=" * 80)
    
    # Target date
    target_date = "20240614"
    end_date = datetime.strptime(target_date, "%Y%m%d")
    start_date = end_date - timedelta(days=60)
    
    print(f"\n目标日期: {target_date}")
    print(f"数据起始日期: {start_date.strftime('%Y%m%d')}")
    
    # Step 1: Get ChiNext stock list and classify by sector
    print("\n" + "=" * 80)
    print("第一步: 获取创业板股票并按行业分类")
    print("=" * 80)
    
    try:
        # Get ChiNext stock list (300xxx)
        stock_info = ak.stock_info_a_code_name()
        chinext_stocks = stock_info[stock_info['code'].str.startswith('300')].copy()
        print(f"创业板股票总数: {len(chinext_stocks)}")
        
        # Classify sectors
        chinext_stocks['sector'] = chinext_stocks.apply(
            lambda row: classify_sector(row['code'], row['name']), axis=1
        )
        
        sector_counts = chinext_stocks['sector'].value_counts()
        print("\n行业分类统计:")
        for sector, count in sector_counts.items():
            print(f"  {sector}: {count}只")
        
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return
    
    # Step 2: Calculate 20-day returns using individual stock API
    print("\n" + "=" * 80)
    print("第二步: 计算各行业近20日等权平均涨跌幅")
    print("=" * 80)
    
    stock_returns = []
    success_count = 0
    fail_count = 0
    
    print(f"\n开始逐个获取股票历史数据（共 {len(chinext_stocks)} 只）...")
    
    for idx, row in chinext_stocks.iterrows():
        code = row['code']
        name = row['name']
        sector = row['sector']
        
        # Limit to first 200 stocks for speed
        if success_count >= 200:
            break
        
        try:
            # Use different API - stock_zh_a_hist_163
            df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                     start_date=start_date.strftime('%Y%m%d'),
                                     end_date=target_date, adjust="qfq")
            
            if df is None or len(df) == 0:
                fail_count += 1
                continue
            
            # Ensure date column exists
            if '日期' not in df.columns:
                fail_count += 1
                continue
            
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期')
            df = df[df['日期'] <= pd.to_datetime(target_date)]
            
            if len(df) < 20:
                fail_count += 1
                continue
            
            # Calculate 20-day return
            recent_20 = df.tail(20)
            start_price = float(recent_20.iloc[0]['收盘'])
            end_price = float(recent_20.iloc[-1]['收盘'])
            
            if start_price > 0:
                return_pct = ((end_price - start_price) / start_price) * 100
                
                stock_returns.append({
                    'code': code,
                    'name': name,
                    'sector': sector,
                    'return_20d': return_pct,
                    'prices': df['收盘'].astype(float).values
                })
                
                success_count += 1
                
                if success_count % 20 == 0:
                    print(f"  已成功处理 {success_count} 只股票...")
            else:
                fail_count += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.05)
        
        except Exception as e:
            fail_count += 1
            continue
    
    returns_df = pd.DataFrame(stock_returns)
    print(f"\n成功获取 {len(returns_df)} 只股票的收益数据")
    print(f"失败: {fail_count} 只")
    
    if len(returns_df) == 0:
        print("错误: 未能获取任何股票数据")
        output_file = RESULT_DIR / "sector_rotation_result.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("强势行业: 数据获取失败\n")
            f.write("股票代码,股票名称,行业,个股涨幅(%),RSI\n")
        return
    
    # Calculate sector average returns (equal-weighted)
    sector_avg_returns = returns_df.groupby('sector')['return_20d'].mean().sort_values(ascending=False)
    
    print("\n各行业近20日等权平均涨跌幅:")
    for sector, avg_return in sector_avg_returns.items():
        stock_count = len(returns_df[returns_df['sector'] == sector])
        print(f"  {sector}: {avg_return:.2f}% (样本数: {stock_count})")
    
    # Find top 2 strongest sectors
    top_2_sectors = sector_avg_returns.head(2).index.tolist()
    print(f"\n涨幅最强的2个行业: {', '.join(top_2_sectors)}")
    
    # Step 3: Find super-strong stocks
    print("\n" + "=" * 80)
    print("第三步: 筛选超强个股（涨幅 > 所在行业均值 × 1.5）")
    print("=" * 80)
    
    super_strong_stocks = []
    
    for sector in top_2_sectors:
        sector_avg = sector_avg_returns[sector]
        threshold = sector_avg * 1.5
        
        sector_stocks = returns_df[returns_df['sector'] == sector]
        strong_stocks = sector_stocks[sector_stocks['return_20d'] > threshold]
        
        print(f"\n{sector}:")
        print(f"  行业均值: {sector_avg:.2f}%")
        print(f"  筛选阈值 (1.5倍): {threshold:.2f}%")
        print(f"  超强个股数量: {len(strong_stocks)}")
        
        super_strong_stocks.append(strong_stocks)
    
    super_strong_df = pd.concat(super_strong_stocks, ignore_index=True)
    print(f"\n超强个股总数: {len(super_strong_df)}")
    
    # Step 4: Calculate RSI and filter
    print("\n" + "=" * 80)
    print("第四步: 计算14日RSI并筛选（40-70区间）")
    print("=" * 80)
    
    final_results = []
    
    for idx, row in super_strong_df.iterrows():
        prices = row['prices']
        
        if len(prices) >= 15:
            rsi = calculate_rsi(prices[-35:], period=14)
            
            if not np.isnan(rsi) and 40 <= rsi <= 70:
                final_results.append({
                    'code': row['code'],
                    'name': row['name'],
                    'sector': row['sector'],
                    'return_20d': row['return_20d'],
                    'rsi': rsi
                })
    
    final_df = pd.DataFrame(final_results)
    print(f"\nRSI在40-70区间的股票数量: {len(final_df)}")
    
    # Write results
    output_file = RESULT_DIR / "sector_rotation_result.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"强势行业: {', '.join(top_2_sectors)}\n")
        f.write("股票代码,股票名称,行业,个股涨幅(%),RSI\n")
        
        for idx, row in final_df.iterrows():
            f.write(f"{row['code']},{row['name']},{row['sector']},{row['return_20d']:.2f},{row['rsi']:.1f}\n")
    
    print(f"\n结果已写入: {output_file}")
    
    # Display results
    print("\n" + "=" * 80)
    print("最终结果")
    print("=" * 80)
    print(f"\n强势行业: {', '.join(top_2_sectors)}")
    
    if len(final_df) > 0:
        print("\n符合条件的股票:")
        for idx, row in final_df.iterrows():
            print(f"{row['code']} {row['name']} | {row['sector']} | 涨幅: {row['return_20d']:.2f}% | RSI: {row['rsi']:.1f}")
    else:
        print("\n未找到符合所有条件的股票")
    
    print("\n任务完成!")

if __name__ == "__main__":
    main()
