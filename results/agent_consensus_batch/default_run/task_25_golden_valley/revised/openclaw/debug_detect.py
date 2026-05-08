#!/usr/bin/env python3
"""
银山谷金山谷均线形态识别 - 调试版本
"""

import sys
import subprocess

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "akshare", "pandas", "numpy"], check=False)

import pandas as pd
import numpy as np
import akshare as ak
import time
from datetime import datetime

OUTPUT_DIR = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_25_golden_valley/revised/openclaw'
OUTPUT_FILE = f'{OUTPUT_DIR}/golden_valley.txt'

def get_chinext_stocks():
    """获取创业板股票列表"""
    df = ak.stock_info_a_code_name()
    return df[df['code'].str.startswith('300')]['code'].tolist()

def get_kline(code, period=120):
    """获取K线数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        df = df.tail(period).reset_index(drop=True)
        rename_map = {'日期': 'date', '开盘': 'open', '最高': 'high',
                      '最低': 'low', '收盘': 'close', '成交量': 'volume'}
        df = df.rename(columns=rename_map)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        return None

def calculate_ma(prices, window):
    """计算移动平均线"""
    return prices.rolling(window=window, min_periods=window).mean()

def main():
    print("开始调试检测...")
    
    # 获取创业板股票列表
    stocks = get_chinext_stocks()
    print(f"股票总数: {len(stocks)}")
    
    # 截止日期 2024-07-08
    end_date = datetime(2024, 7, 8)
    
    # 统计信息
    stats = {
        'total': 0,
        'has_data': 0,
        'has_ma': 0,
        'silver_found': 0,
        'golden_found': 0,
        'broke_ma20': 0
    }
    
    results = []
    
    # 只检查前100只股票进行调试
    for idx, code in enumerate(stocks[:100], 1):
        stats['total'] += 1
        
        # 获取120个交易日的数据
        df = get_kline(code, period=120)
        
        if df is None or len(df) < 60:
            continue
        
        stats['has_data'] += 1
        
        # 过滤到截止日期
        df = df[df['date'] <= end_date].copy()
        
        if len(df) < 60:
            continue
        
        try:
            # 计算均线
            df['MA5'] = calculate_ma(df['close'], 5)
            df['MA10'] = calculate_ma(df['close'], 10)
            df['MA20'] = calculate_ma(df['close'], 20)
            
            # 删除均线计算不完整的行
            df = df.dropna(subset=['MA5', 'MA10', 'MA20']).reset_index(drop=True)
            
            if len(df) < 60:
                continue
            
            stats['has_ma'] += 1
            
            # 在最近60个交易日内搜索银山谷
            search_start_idx = max(0, len(df) - 60)
            search_end_idx = len(df)
            
            # 检测银山谷 - 放宽条件：不要求前一日不满足
            silver_idx = None
            silver_ma10 = None
            
            for i in range(search_start_idx, search_end_idx):
                # 检查多头排列
                if not ((df.loc[i, 'MA5'] > df.loc[i, 'MA10']) and 
                        (df.loc[i, 'MA10'] > df.loc[i, 'MA20'])):
                    continue
                
                # 检查三线间距
                spacing = (df.loc[i, 'MA5'] - df.loc[i, 'MA20']) / df.loc[i, 'MA20']
                if spacing >= 0.08:
                    continue
                
                # 检查是否是首次形成（前一日不满足）
                if i > 0:
                    prev_bullish = ((df.loc[i-1, 'MA5'] > df.loc[i-1, 'MA10']) and 
                                   (df.loc[i-1, 'MA10'] > df.loc[i-1, 'MA20']))
                    if prev_bullish:
                        continue
                
                # 找到银山谷
                silver_idx = i
                silver_ma10 = df.loc[i, 'MA10']
                stats['silver_found'] += 1
                break
            
            if silver_idx is None:
                continue
            
            # 检测金山谷
            search_start = silver_idx + 10
            search_end = min(silver_idx + 31, len(df))
            
            if search_start >= len(df):
                continue
            
            # 检查回调期间是否跌破20日均线
            broke_ma20 = False
            for i in range(silver_idx + 1, search_end):
                if df.loc[i, 'close'] < df.loc[i, 'MA20']:
                    broke_ma20 = True
                    stats['broke_ma20'] += 1
                    break
            
            if broke_ma20:
                continue
            
            # 在允许的范围内搜索金山谷
            golden_idx = None
            interval_days = None
            
            for i in range(search_start, search_end):
                # 检查多头排列
                if not ((df.loc[i, 'MA5'] > df.loc[i, 'MA10']) and 
                        (df.loc[i, 'MA10'] > df.loc[i, 'MA20'])):
                    continue
                
                # 检查三线间距
                spacing = (df.loc[i, 'MA5'] - df.loc[i, 'MA20']) / df.loc[i, 'MA20']
                if spacing >= 0.08:
                    continue
                
                # 检查10日均线值是否高于银山谷
                if df.loc[i, 'MA10'] <= silver_ma10:
                    continue
                
                # 检查是否是再次形成（前一日不满足）
                if i > silver_idx:
                    prev_bullish = ((df.loc[i-1, 'MA5'] > df.loc[i-1, 'MA10']) and 
                                   (df.loc[i-1, 'MA10'] > df.loc[i-1, 'MA20']))
                    if prev_bullish:
                        continue
                
                # 找到金山谷
                golden_idx = i
                interval_days = i - silver_idx
                stats['golden_found'] += 1
                break
            
            if golden_idx is None:
                continue
            
            # 记录结果
            silver_date = df.loc[silver_idx, 'date'].strftime('%Y-%m-%d')
            golden_date = df.loc[golden_idx, 'date'].strftime('%Y-%m-%d')
            
            results.append({
                'code': code,
                'silver_date': silver_date,
                'golden_date': golden_date,
                'interval': interval_days
            })
            
            print(f"✓ {code}: 银山谷={silver_date}, 金山谷={golden_date}, 间隔={interval_days}天")
            
        except Exception as e:
            print(f"Error processing {code}: {e}")
            continue
        
        time.sleep(0.05)
    
    # 打印统计信息
    print("\n=== 统计信息 ===")
    print(f"检查股票数: {stats['total']}")
    print(f"有数据: {stats['has_data']}")
    print(f"均线计算完成: {stats['has_ma']}")
    print(f"找到银山谷: {stats['silver_found']}")
    print(f"跌破MA20: {stats['broke_ma20']}")
    print(f"找到金山谷: {stats['golden_found']}")
    
    # 输出结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("# 无符合条件的股票\n")
            print("\n未找到符合条件的股票")
        else:
            f.write("股票代码,银山谷日期,金山谷日期,间隔天数\n")
            for r in results:
                f.write(f"{r['code']},{r['silver_date']},{r['golden_date']},{r['interval']}\n")
            print(f"\n共找到 {len(results)} 只股票符合条件")
    
    print(f"结果已保存到: {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
