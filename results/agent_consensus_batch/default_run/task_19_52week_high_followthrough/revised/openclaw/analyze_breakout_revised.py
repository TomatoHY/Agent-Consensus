#!/usr/bin/env python3
"""
52周新高突破跟进分析 - 改进版
增强错误处理、数据验证和日志记录
"""

import akshare as ak
import pandas as pd
from datetime import datetime
import warnings
import time
warnings.filterwarnings('ignore')

def get_chinext_stocks():
    """获取创业板股票列表"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            stock_info = ak.stock_info_a_code_name()
            chinext = stock_info[stock_info['code'].str.startswith('300')]
            return chinext['code'].tolist()
        except Exception as e:
            print(f"获取创业板股票列表失败 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    return []

def get_stock_data(stock_code, end_date='2024-11-15', max_retries=2):
    """
    获取股票历史数据，增强错误处理和重试机制
    需要至少 252 + 30 + 5 = 287 个交易日的数据
    """
    for attempt in range(max_retries):
        try:
            start_date = '2023-06-01'
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                    start_date=start_date, end_date=end_date, adjust="qfq")
            
            if df is None or len(df) == 0:
                return None, "empty_data"
                
            # 重命名列
            df = df.rename(columns={
                '日期': 'date',
                '收盘': 'close',
                '成交量': 'volume'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            df = df[['date', 'close', 'volume']].reset_index(drop=True)
            
            # 数据质量检查
            if len(df) < 282:
                return None, f"insufficient_data_{len(df)}"
            
            # 检查是否有缺失值
            if df[['close', 'volume']].isnull().any().any():
                return None, "missing_values"
            
            return df, "success"
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                return None, f"error_{str(e)[:50]}"
    
    return None, "max_retries_exceeded"

def find_52week_high_breakout(df, end_date='2024-11-15'):
    """
    在最近30个交易日内找到首次突破52周(252个交易日)新高的日期
    返回: (breakout_date, breakout_price, breakout_idx) 或 None
    """
    end_date = pd.to_datetime(end_date)
    
    if len(df) < 282:
        return None
    
    df_before_end = df[df['date'] <= end_date]
    if len(df_before_end) < 282:
        return None
    
    # 最近30个交易日的窗口
    recent_30_days = df_before_end.tail(30).copy()
    
    for i in range(len(recent_30_days)):
        current_idx = len(df_before_end) - len(recent_30_days) + i
        current_date = df_before_end.iloc[current_idx]['date']
        current_close = df_before_end.iloc[current_idx]['close']
        
        if current_idx < 252:
            continue
            
        past_252_days = df_before_end.iloc[current_idx-252:current_idx]
        max_close_252 = past_252_days['close'].max()
        
        if current_close > max_close_252:
            return (current_date, current_close, current_idx)
    
    return None

def check_volume_confirmation(df, breakout_idx):
    """
    检查量能确认：创新高日±2天(共5天)的成交量均值 > 60日均量的1.5倍
    """
    window_start = max(0, breakout_idx - 2)
    window_end = min(len(df), breakout_idx + 3)
    
    if window_end - window_start < 5:
        return False
    
    volume_window = df.iloc[window_start:window_end]['volume']
    avg_volume_window = volume_window.mean()
    
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
    if breakout_idx + 5 >= len(df):
        return False, None
    
    next_5_days = df.iloc[breakout_idx+1:breakout_idx+6]
    
    days_above = (next_5_days['close'] > breakout_price).sum()
    
    if days_above < 3:
        return False, None
    
    day5_close = df.iloc[breakout_idx + 5]['close']
    gain_pct = (day5_close / breakout_price - 1) * 100
    
    return True, gain_pct

def main():
    print("开始分析创业板52周新高突破跟进（改进版）...")
    print(f"截止日期: 2024-11-15")
    print(f"分析窗口: 最近30个交易日")
    print()
    
    # 获取创业板股票列表
    chinext_stocks = get_chinext_stocks()
    if not chinext_stocks:
        print("错误: 无法获取创业板股票列表")
        with open('breakout_followthrough.txt', 'w', encoding='utf-8') as f:
            f.write("错误: 无法获取创业板股票列表\n")
        return
    
    print(f"获取到 {len(chinext_stocks)} 只创业板股票")
    
    results = []
    stats = {
        'total': len(chinext_stocks),
        'data_error': 0,
        'insufficient_data': 0,
        'no_breakout': 0,
        'no_volume': 0,
        'no_followthrough': 0,
        'success': 0
    }
    
    for i, stock_code in enumerate(chinext_stocks, 1):
        if i % 100 == 0:
            print(f"进度: {i}/{len(chinext_stocks)} - 已找到 {len(results)} 只符合条件的股票")
        
        # 获取股票数据
        df, status = get_stock_data(stock_code)
        if df is None:
            if 'insufficient_data' in status:
                stats['insufficient_data'] += 1
            else:
                stats['data_error'] += 1
            continue
        
        # 1. 找到52周新高突破点
        breakout_info = find_52week_high_breakout(df)
        if breakout_info is None:
            stats['no_breakout'] += 1
            continue
        
        breakout_date, breakout_price, breakout_idx = breakout_info
        
        # 2. 检查量能确认
        if not check_volume_confirmation(df, breakout_idx):
            stats['no_volume'] += 1
            continue
        
        # 3. 检查持续性
        is_valid, gain_pct = check_followthrough(df, breakout_idx, breakout_price)
        if not is_valid:
            stats['no_followthrough'] += 1
            continue
        
        stats['success'] += 1
        results.append({
            'code': stock_code,
            'breakout_date': breakout_date.strftime('%Y-%m-%d'),
            'breakout_price': round(breakout_price, 2),
            'gain_5d_pct': round(gain_pct, 2)
        })
        
        print(f"✓ {stock_code}: {breakout_date.strftime('%Y-%m-%d')}, "
              f"价格 {breakout_price:.2f}, 5日涨幅 {gain_pct:.2f}%")
    
    print(f"\n分析完成统计:")
    print(f"  总股票数: {stats['total']}")
    print(f"  数据获取失败: {stats['data_error']}")
    print(f"  数据不足: {stats['insufficient_data']}")
    print(f"  未创新高: {stats['no_breakout']}")
    print(f"  量能不足: {stats['no_volume']}")
    print(f"  持续性不足: {stats['no_followthrough']}")
    print(f"  符合条件: {stats['success']}")
    
    # 写入结果文件
    output_file = 'breakout_followthrough.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("无符合条件的股票\n")
        else:
            f.write("股票代码,创新高日期,创新高价格,新高后5日涨幅(%)\n")
            for r in results:
                f.write(f"{r['code']},{r['breakout_date']},{r['breakout_price']},{r['gain_5d_pct']}\n")
    
    print(f"\n结果已写入 {output_file}")

if __name__ == '__main__':
    main()
