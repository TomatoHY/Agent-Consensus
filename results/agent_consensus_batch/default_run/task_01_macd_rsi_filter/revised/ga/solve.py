import pandas as pd
import numpy as np
from pathlib import Path
import time
from mootdx.quotes import Quotes

client = Quotes.factory(market='std')

def calculate_macd(df, fast=12, slow=26, signal=9):
    """计算MACD指标"""
    df = df.copy()
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    df['DIFF'] = ema_fast - ema_slow
    df['DEA'] = df['DIFF'].ewm(span=signal, adjust=False).mean()
    df['MACD'] = (df['DIFF'] - df['DEA']) * 2
    return df

def calculate_rsi(df, period=14):
    """计算RSI指标"""
    df = df.copy()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def check_stock(code):
    """检查单只股票是否满足条件"""
    try:
        bars = client.bars(symbol=code, frequency=9, offset=100)
        
        if bars is None or len(bars) < 60:
            return None
        
        bars = bars.sort_index()
        bars = calculate_macd(bars)
        bars = calculate_rsi(bars, 14)
        
        bars['MA5'] = bars['close'].rolling(window=5).mean()
        bars['MA8'] = bars['close'].rolling(window=8).mean()
        bars['VOL_MA5'] = bars['volume'].rolling(window=5).mean()
        
        # 目标窗口
        target_start = pd.Timestamp('2026-03-04')
        target_end = pd.Timestamp('2026-03-31')
        
        window_mask = (bars.index >= target_start) & (bars.index <= target_end)
        window_data = bars[window_mask].copy()
        
        if len(window_data) == 0:
            return None
        
        # === 窗口级别条件（独立满足） ===
        
        # 1. 检查窗口内是否有MACD金叉
        window_data['MACD_GOLDEN'] = (window_data['DIFF'] > window_data['DEA']) & \
                                     (window_data['DIFF'].shift(1) <= window_data['DEA'].shift(1))
        if not window_data['MACD_GOLDEN'].any():
            return None
        
        # 2. 检查窗口内成交量超标天数（使用前5日均量，不含当天）
        window_data['VOL_SPIKE'] = window_data['volume'] > (window_data['VOL_MA5'].shift(1) * 2)
        vol_spike_count = window_data['VOL_SPIKE'].sum()
        if vol_spike_count < 2:
            return None
        
        # === 同日共振条件 ===
        # 需要找到某一天同时满足：RSI上穿50 + 成交量超标 + MA5上穿MA8
        
        # 检测RSI从<30恢复后首次上穿50
        window_data['RSI_SIGNAL'] = False
        in_recovery = False
        
        for i in range(len(window_data)):
            current_rsi = window_data['RSI'].iloc[i]
            
            if pd.isna(current_rsi):
                continue
            
            # 检测跌破30，进入恢复周期
            if current_rsi < 30:
                in_recovery = True
            elif in_recovery and current_rsi > 50:
                # 检查是否是上穿（前一天<=50）
                if i > 0:
                    prev_rsi = window_data['RSI'].iloc[i-1]
                    if not pd.isna(prev_rsi) and prev_rsi <= 50:
                        window_data.iloc[i, window_data.columns.get_loc('RSI_SIGNAL')] = True
                        in_recovery = False  # 首次上穿后结束周期
        
        # 检测MA5上穿MA8
        window_data['MA_CROSS'] = (window_data['MA5'] > window_data['MA8']) & \
                                  (window_data['MA5'].shift(1) <= window_data['MA8'].shift(1))
        
        # 检查是否有某天同时满足三个条件
        resonance_days = window_data[
            window_data['RSI_SIGNAL'] & 
            window_data['VOL_SPIKE'] & 
            window_data['MA_CROSS']
        ]
        
        if len(resonance_days) > 0:
            return code
        
        return None
        
    except Exception as e:
        return None

# 获取创业板股票列表
print("正在获取创业板股票列表...")
all_stocks = client.stock_all()
gem_stocks = all_stocks[all_stocks['code'].str.startswith('300')]['code'].tolist()
print(f"找到 {len(gem_stocks)} 只创业板股票\n")

# 筛选符合条件的股票
qualified_stocks = []

for i, code in enumerate(gem_stocks):
    if i % 100 == 0:
        print(f"进度: {i}/{len(gem_stocks)}")
    
    result = check_stock(code)
    if result:
        qualified_stocks.append(result)
        print(f"找到符合条件的股票: {result}")
        
        if len(qualified_stocks) >= 10:
            break
    
    if i % 50 == 0:
        time.sleep(0.5)

print(f"\n筛选完成，共找到 {len(qualified_stocks)} 只符合条件的股票")

# 写入结果文件
result_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_01_macd_rsi_filter/revised/ga/result.txt"

with open(result_path, 'w', encoding='utf-8') as f:
    for code in qualified_stocks[:10]:
        f.write(f"{code}\n")

print(f"结果已写入: {result_path}")

# 输出最终结果JSON
import json

final_result = {
    "answer": "",
    "confidence": 0.85,
    "what_changed": "修正了对'同时满足'的理解：MACD金叉和成交量>=2天超标是窗口级别条件（独立满足），而RSI上穿50、当日成交量超标、MA5上穿MA8需要在同一交易日同时满足（同日共振）。这是根据Expected Behavior第7条的精确要求进行的修正。",
    "final_method": "窗口内必须出现MACD金叉且至少2天成交量超标。同时要求窗口内某一天同时满足：(1)RSI14从<30恢复周期内首次上穿50，(2)当日成交量>前5日均量2倍（不含当天），(3)MA5上穿MA8。",
    "preferred_output": "text",
    "artifacts": [result_path]
}

json_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_01_macd_rsi_filter/revised/ga/revised_result.json"
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(final_result, f, ensure_ascii=False, indent=2)

print(f"\n最终结果JSON已写入: {json_path}")
print(json.dumps(final_result, ensure_ascii=False, indent=2))
