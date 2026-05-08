#!/usr/bin/env python3
"""
均线粘合发散形态识别
截止日期: 2024-08-08
"""

from mootdx.quotes import Quotes
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 配置
END_DATE = datetime(2024, 8, 8)
OUTPUT_FILE = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_26_ma_convergence_divergence/revised/openclaw/ma_divergence.txt"

def calculate_ma(df, periods=[5, 10, 20, 30]):
    """计算多条均线"""
    for period in periods:
        df[f'ma{period}'] = df['close'].rolling(window=period).mean()
    return df

def check_convergence(mas):
    """检查均线粘合：四条均线最大距离<3%"""
    if any(pd.isna(mas)):
        return False
    max_ma = max(mas)
    min_ma = min(mas)
    if min_ma == 0:
        return False
    distance = (max_ma - min_ma) / min_ma
    return distance < 0.03

def check_divergence(ma5, ma10, ma20, ma30):
    """检查均线发散：5>10>20>30且相邻间距>2%"""
    if any(pd.isna([ma5, ma10, ma20, ma30])):
        return False
    
    # 检查顺序
    if not (ma5 > ma10 > ma20 > ma30):
        return False
    
    # 检查相邻间距
    gap1 = (ma5 - ma10) / ma10
    gap2 = (ma10 - ma20) / ma20
    gap3 = (ma20 - ma30) / ma30
    
    return all([gap1 > 0.02, gap2 > 0.02, gap3 > 0.02])

def analyze_stock(code):
    """分析单只股票"""
    try:
        client = Quotes.factory(market='std')
        # 获取60日数据
        bars = client.bars(symbol=code, frequency=9, offset=60)
        
        if bars is None or len(bars) < 40:
            return None
        
        df = bars.copy()
        df = df.sort_index()
        
        # 过滤到截止日期之前的数据
        df = df[df.index <= END_DATE]
        
        if len(df) < 40:
            return None
        
        # 计算均线
        df = calculate_ma(df)
        
        # 检测粘合期（在最近20日内）
        recent_20 = df.tail(20).copy()
        
        # 查找连续5天以上的粘合期
        convergence_periods = []
        i = 0
        while i < len(recent_20):
            # 检查从i开始是否有连续5天粘合
            if pd.notna(recent_20.iloc[i]['ma30']):
                mas = [recent_20.iloc[i]['ma5'], recent_20.iloc[i]['ma10'], 
                       recent_20.iloc[i]['ma20'], recent_20.iloc[i]['ma30']]
                if check_convergence(mas):
                    # 找到粘合开始，继续找连续的
                    start_idx = i
                    j = i
                    while j < len(recent_20):
                        mas_j = [recent_20.iloc[j]['ma5'], recent_20.iloc[j]['ma10'],
                                recent_20.iloc[j]['ma20'], recent_20.iloc[j]['ma30']]
                        if check_convergence(mas_j):
                            j += 1
                        else:
                            break
                    
                    # 检查是否连续>=5天
                    if j - start_idx >= 5:
                        conv_start = recent_20.index[start_idx]
                        conv_end = recent_20.index[j - 1]
                        convergence_periods.append((conv_start, conv_end))
                    
                    i = j
                else:
                    i += 1
            else:
                i += 1
        
        if not convergence_periods:
            return None
        
        # 对每个粘合期，检查后续5日内是否发散
        for conv_start, conv_end in convergence_periods:
            conv_end_loc = df.index.get_loc(conv_end)
            
            # 粘合期结束后的5日
            if conv_end_loc + 5 >= len(df):
                continue
            
            next_5_days = df.iloc[conv_end_loc + 1:conv_end_loc + 6]
            
            # 检查是否有发散
            divergence_found = False
            divergence_date = None
            
            for idx in range(len(next_5_days)):
                row = next_5_days.iloc[idx]
                if check_divergence(row['ma5'], row['ma10'], row['ma20'], row['ma30']):
                    divergence_found = True
                    divergence_date = next_5_days.index[idx]
                    break
            
            if not divergence_found:
                continue
            
            # 验证量能条件
            conv_start_loc = df.index.get_loc(conv_start)
            convergence_data = df.iloc[conv_start_loc:conv_end_loc + 1]
            
            divergence_loc = df.index.get_loc(divergence_date)
            divergence_data = df.iloc[divergence_loc:min(divergence_loc + 5, len(df))]
            
            if len(convergence_data) == 0 or len(divergence_data) == 0:
                continue
            
            conv_avg_vol = convergence_data['vol'].mean()
            div_avg_vol = divergence_data['vol'].mean()
            
            if div_avg_vol < conv_avg_vol * 1.5:
                continue
            
            # 计算发散后5日涨幅
            if divergence_loc + 5 >= len(df):
                continue
            
            start_price = df.iloc[divergence_loc]['close']
            end_price = df.iloc[divergence_loc + 5]['close']
            return_pct = (end_price - start_price) / start_price * 100
            
            if return_pct <= 0:
                continue
            
            return {
                'code': code,
                'conv_start': conv_start.strftime('%Y-%m-%d'),
                'conv_end': conv_end.strftime('%Y-%m-%d'),
                'div_start': divergence_date.strftime('%Y-%m-%d'),
                'return_5d': round(return_pct, 2)
            }
        
        return None
        
    except Exception as e:
        return None

def main():
    print("开始分析创业板股票...")
    
    # 构造创业板股票代码列表（300001-300999）
    cyb_stocks = [f"300{str(i).zfill(3)}" for i in range(1, 1000)]
    print(f"准备分析 {len(cyb_stocks)} 只创业板股票代码")
    
    results = []
    for i, code in enumerate(cyb_stocks):
        if i % 100 == 0:
            print(f"进度: {i}/{len(cyb_stocks)}, 已找到 {len(results)} 只符合条件")
        
        result = analyze_stock(code)
        if result:
            results.append(result)
            print(f"✓ 找到符合条件: {code}")
    
    print(f"\n扫描完成，共检查 {len(cyb_stocks)} 只股票")
    print(f"找到 {len(results)} 只符合条件的股票")
    
    # 写入结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("股票代码,粘合期开始,粘合期结束,发散开始日期,发散后5日涨幅(%)\n")
        if results:
            for r in results:
                f.write(f"{r['code']},{r['conv_start']},{r['conv_end']},{r['div_start']},{r['return_5d']}\n")
        else:
            f.write("# 未找到符合条件的股票\n")
    
    print(f"结果已写入: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
