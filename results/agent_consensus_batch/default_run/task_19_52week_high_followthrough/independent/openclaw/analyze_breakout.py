#!/usr/bin/env python3
"""
52周新高突破跟进分析
找出创业板中创52周新高、量能放大且持续上涨的股票
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_chinext_stocks():
    """获取创业板股票列表"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"获取创业板股票列表失败: {e}")
        return []

def get_stock_data(stock_code, end_date='2024-11-15'):
    """
    获取股票历史数据
    需要至少 252 + 30 + 5 = 287 个交易日的数据
    """
    try:
        # 获取更多数据以确保有足够的交易日
        start_date = '2023-06-01'  # 提前足够时间
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df is None or len(df) == 0:
            return None
            
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '收盘': 'close',
            '成交量': 'volume'
        })
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df = df[['date', 'close', 'volume']].reset_index(drop=True)
        
        return df
    except Exception as e:
        print(f"获取 {stock_code} 数据失败: {e}")
        return None

def find_52week_high_breakout(df, end_date='2024-11-15'):
    """
    在最近30个交易日内找到首次突破52周(252个交易日)新高的日期
    
    返回: (breakout_date, breakout_price, breakout_idx) 或 None
    """
    end_date = pd.to_datetime(end_date)
    
    # 确保有足够数据
    if len(df) < 282:  # 252 + 30
        return None
    
    # 找到截止日期的索引
    df_before_end = df[df['date'] <= end_date]
    if len(df_before_end) < 282:
        return None
    
    # 最近30个交易日的窗口
    recent_30_days = df_before_end.tail(30).copy()
    
    for i in range(len(recent_30_days)):
        current_idx = len(df_before_end) - len(recent_30_days) + i
        current_date = df_before_end.iloc[current_idx]['date']
        current_close = df_before_end.iloc[current_idx]['close']
        
        # 获取过去252个交易日的数据（不包括当天）
        if current_idx < 252:
            continue
            
        past_252_days = df_before_end.iloc[current_idx-252:current_idx]
        max_close_252 = past_252_days['close'].max()
        
        # 检查是否创新高
        if current_close > max_close_252:
            return (current_date, current_close, current_idx)
    
    return None

def check_volume_confirmation(df, breakout_idx):
    """
    检查量能确认：创新高日±2天(共5天)的成交量均值 > 60日均量的1.5倍
    """
    # 5天窗口：breakout_idx-2 到 breakout_idx+2
    window_start = max(0, breakout_idx - 2)
    window_end = min(len(df), breakout_idx + 3)  # +3 因为是左闭右开
    
    if window_end - window_start < 5:
        return False
    
    volume_window = df.iloc[window_start:window_end]['volume']
    avg_volume_window = volume_window.mean()
    
    # 60日均量（在突破日之前）
    if breakout_idx < 60:
        return False
    
    past_60_days = df.iloc[breakout_idx-60:breakout_idx]
    avg_volume_60 = past_60_days['volume'].mean()
    
    return avg_volume_window > (avg_volume_60 * 1.5)

def check_followthrough(df, breakout_idx, breakout_price):
    """
    检查持续性：新高后5个交易日内，至少3天收盘价高于创新高价
    
    返回: (is_valid, gain_pct) 或 (False, None)
    """
    # 需要突破日后至少5个交易日
    if breakout_idx + 5 >= len(df):
        return False, None
    
    next_5_days = df.iloc[breakout_idx+1:breakout_idx+6]
    
    # 统计有多少天收盘价高于突破价
    days_above = (next_5_days['close'] > breakout_price).sum()
    
    if days_above < 3:
        return False, None
    
    # 计算新高后5日涨幅 = (第5日收盘 / 创新高日收盘 - 1) * 100
    day5_close = df.iloc[breakout_idx + 5]['close']
    gain_pct = (day5_close / breakout_price - 1) * 100
    
    return True, gain_pct

def main():
    print("开始分析创业板52周新高突破跟进...")
    print(f"截止日期: 2024-11-15")
    print(f"分析窗口: 最近30个交易日")
    print()
    
    # 获取创业板股票列表
    chinext_stocks = get_chinext_stocks()
    print(f"获取到 {len(chinext_stocks)} 只创业板股票")
    
    results = []
    
    for i, stock_code in enumerate(chinext_stocks, 1):
        if i % 50 == 0:
            print(f"进度: {i}/{len(chinext_stocks)}")
        
        # 获取股票数据
        df = get_stock_data(stock_code)
        if df is None:
            continue
        
        # 1. 找到52周新高突破点
        breakout_info = find_52week_high_breakout(df)
        if breakout_info is None:
            continue
        
        breakout_date, breakout_price, breakout_idx = breakout_info
        
        # 2. 检查量能确认
        if not check_volume_confirmation(df, breakout_idx):
            continue
        
        # 3. 检查持续性
        is_valid, gain_pct = check_followthrough(df, breakout_idx, breakout_price)
        if not is_valid:
            continue
        
        results.append({
            'code': stock_code,
            'breakout_date': breakout_date.strftime('%Y-%m-%d'),
            'breakout_price': round(breakout_price, 2),
            'gain_5d_pct': round(gain_pct, 2)
        })
        
        print(f"✓ {stock_code}: {breakout_date.strftime('%Y-%m-%d')}, "
              f"价格 {breakout_price:.2f}, 5日涨幅 {gain_pct:.2f}%")
    
    print(f"\n分析完成，共找到 {len(results)} 只符合条件的股票")
    
    # 写入结果文件
    output_file = 'breakout_followthrough.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("无符合条件的股票\n")
        else:
            f.write("股票代码,创新高日期,创新高价格,新高后5日涨幅(%)\n")
            for r in results:
                f.write(f"{r['code']},{r['breakout_date']},{r['breakout_price']},{r['gain_5d_pct']}\n")
    
    print(f"结果已写入 {output_file}")

if __name__ == '__main__':
    main()
