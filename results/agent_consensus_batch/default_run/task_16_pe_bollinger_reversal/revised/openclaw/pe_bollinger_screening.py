#!/usr/bin/env python3
"""
PE筛选后布林带反弹选股
完成基本面+技术面联合选股任务
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_chinext_stocks_with_pe():
    """获取创业板股票及其PE数据"""
    print("正在获取创业板股票列表...")
    
    # 获取创业板股票列表
    stock_info = ak.stock_info_a_code_name()
    chinext_stocks = stock_info[stock_info['code'].str.startswith('300')]
    
    print(f"创业板股票总数: {len(chinext_stocks)}")
    
    # 获取PE数据
    print("正在获取PE数据...")
    pe_data = []
    
    for idx, row in chinext_stocks.iterrows():
        code = row['code']
        try:
            # 获取个股信息（包含PE）
            stock_individual = ak.stock_individual_info_em(symbol=code)
            pe_value = None
            
            for _, info_row in stock_individual.iterrows():
                if info_row['item'] == '市盈率-动态':
                    pe_str = str(info_row['value'])
                    if pe_str != '-' and pe_str != 'nan':
                        try:
                            pe_value = float(pe_str)
                        except:
                            pass
                    break
            
            if pe_value is not None and 15 <= pe_value <= 60:
                pe_data.append({
                    'code': code,
                    'name': row['name'],
                    'pe': pe_value
                })
                print(f"  {code} {row['name']}: PE={pe_value:.2f}")
        except Exception as e:
            continue
    
    df_pe = pd.DataFrame(pe_data)
    print(f"\nPE在15-60之间的股票数: {len(df_pe)}")
    return df_pe

def calculate_bollinger_bands(prices, window=20, num_std=2):
    """计算布林带"""
    middle = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return middle, upper, lower

def check_bollinger_bounce(code, end_date='2024-08-15'):
    """检查布林带反弹条件"""
    try:
        # 获取历史数据（需要更多天数以计算20日指标）
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=60)
        start_date = start_dt.strftime('%Y%m%d')
        end_date_fmt = end_dt.strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                start_date=start_date, end_date=end_date_fmt, adjust="qfq")
        
        if len(df) < 25:
            return None
        
        df = df.sort_values('日期')
        df['close'] = df['收盘'].astype(float)
        df['volume'] = df['成交量'].astype(float)
        
        # 计算布林带
        middle, upper, lower = calculate_bollinger_bands(df['close'], window=20, num_std=2)
        df['bb_middle'] = middle
        df['bb_upper'] = upper
        df['bb_lower'] = lower
        
        # 获取最近20天的数据
        recent_20 = df.tail(20).copy()
        
        if len(recent_20) < 20:
            return None
        
        # 检查条件1: 最近20天内曾触及或跌破下轨
        touched_lower = (recent_20['close'] <= recent_20['bb_lower']).any()
        
        if not touched_lower:
            return None
        
        # 检查条件2: 最新收盘价回到中轨以上
        latest = df.iloc[-1]
        if pd.isna(latest['bb_middle']) or latest['close'] <= latest['bb_middle']:
            return None
        
        # 找到反弹日期（首次回到中轨以上的日期）
        bounce_date = None
        for i in range(len(recent_20)-1, -1, -1):
            row = recent_20.iloc[i]
            if not pd.isna(row['bb_middle']) and row['close'] > row['bb_middle']:
                bounce_date = row['日期']
            else:
                break
        
        if bounce_date is None:
            bounce_date = latest['日期']
        
        # 检查条件3: 近5日成交量均值 > 近20日成交量均值
        vol_5d = df.tail(5)['volume'].mean()
        vol_20d = df.tail(20)['volume'].mean()
        
        if vol_5d <= vol_20d:
            return None
        
        # 计算近5日涨幅
        if len(df) >= 6:
            price_5d_ago = df.iloc[-6]['close']
            price_latest = latest['close']
            gain_5d = ((price_latest - price_5d_ago) / price_5d_ago) * 100
        else:
            gain_5d = 0.0
        
        return {
            'bounce_date': bounce_date,
            'gain_5d': gain_5d
        }
        
    except Exception as e:
        print(f"  处理 {code} 时出错: {e}")
        return None

def main():
    """主函数"""
    print("="*60)
    print("PE筛选后布林带反弹选股")
    print("="*60)
    
    # 第一步：获取PE在15-60之间的创业板股票
    df_pe = get_chinext_stocks_with_pe()
    
    if len(df_pe) == 0:
        print("未找到符合PE条件的股票")
        with open('pe_bollinger_top8.txt', 'w', encoding='utf-8') as f:
            f.write("# 未找到符合条件的股票\n")
        return
    
    # 第二步和第三步：检查布林带反弹和量能条件
    print("\n正在检查布林带反弹和量能条件...")
    results = []
    
    for idx, row in df_pe.iterrows():
        code = row['code']
        print(f"\n检查 {code} {row['name']} (PE={row['pe']:.2f})...")
        
        bounce_info = check_bollinger_bounce(code)
        
        if bounce_info is not None:
            results.append({
                'code': code,
                'name': row['name'],
                'pe': row['pe'],
                'bounce_date': bounce_info['bounce_date'],
                'gain_5d': bounce_info['gain_5d']
            })
            print(f"  ✓ 符合条件！反弹日期: {bounce_info['bounce_date']}, 近5日涨幅: {bounce_info['gain_5d']:.1f}%")
    
    # 按PE升序排序，取前8名
    if len(results) > 0:
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('pe').head(8)
        
        print(f"\n找到 {len(df_results)} 只符合条件的股票")
        print("\n最终结果（按PE升序）：")
        print(df_results.to_string(index=False))
        
        # 写入文件
        with open('pe_bollinger_top8.txt', 'w', encoding='utf-8') as f:
            f.write("股票代码,PE,布林带反弹日期,近5日涨幅(%)\n")
            for _, row in df_results.iterrows():
                f.write(f"{row['code']},{row['pe']:.1f},{row['bounce_date']},{row['gain_5d']:.1f}\n")
        
        print("\n结果已写入 pe_bollinger_top8.txt")
    else:
        print("\n未找到符合所有条件的股票")
        with open('pe_bollinger_top8.txt', 'w', encoding='utf-8') as f:
            f.write("# 未找到符合条件的股票\n")

if __name__ == "__main__":
    main()
