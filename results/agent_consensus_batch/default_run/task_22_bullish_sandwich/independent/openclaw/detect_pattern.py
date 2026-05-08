#!/usr/bin/env python3
"""
两阳夹一阴多方炮形态识别
Bullish Sandwich Pattern Detection for ChiNext stocks
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
        # 创业板代码以300开头
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"获取创业板股票列表失败: {e}")
        return []

def get_stock_data(stock_code, end_date='2024-04-08'):
    """获取股票K线数据（近60日）"""
    try:
        # 计算起始日期（往前推90天以确保有足够交易日）
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=90)
        start_date = start_dt.strftime('%Y%m%d')
        end_date_fmt = end_dt.strftime('%Y%m%d')
        
        # 获取日K线数据
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date_fmt, adjust="qfq")
        
        if df is None or len(df) < 60:
            return None
            
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount'
        })
        
        # 确保日期格式
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # 取最近60个交易日
        df = df.tail(60).reset_index(drop=True)
        
        return df
        
    except Exception as e:
        print(f"获取{stock_code}数据失败: {e}")
        return None

def calculate_ma(df, periods=[5, 10, 20]):
    """计算移动平均线"""
    for period in periods:
        df[f'ma{period}'] = df['close'].rolling(window=period).mean()
    return df

def check_bullish_sandwich(df, i):
    """
    检查第i天开始的连续3日是否满足两阳夹一阴形态
    i: 第1天的索引
    返回: (是否满足, 成交量比1, 成交量比2)
    """
    if i + 2 >= len(df):
        return False, None, None
    
    day1 = df.iloc[i]
    day2 = df.iloc[i + 1]
    day3 = df.iloc[i + 2]
    
    # 条件1: 第1日、第3日为阳线且涨幅>2%；第2日为阴线但跌幅<1%
    # 阳线: 收盘价 > 开盘价
    is_day1_bullish = day1['close'] > day1['open']
    is_day3_bullish = day3['close'] > day3['open']
    # 阴线: 收盘价 < 开盘价
    is_day2_bearish = day2['close'] < day2['open']
    
    if not (is_day1_bullish and is_day3_bullish and is_day2_bearish):
        return False, None, None
    
    # 计算涨跌幅（相对于前一日收盘价）
    if i == 0:
        return False, None, None  # 第1天无法计算涨幅
    
    prev_close = df.iloc[i - 1]['close']
    day1_change = (day1['close'] - prev_close) / prev_close * 100
    day2_change = (day2['close'] - day1['close']) / day1['close'] * 100
    day3_change = (day3['close'] - day2['close']) / day2['close'] * 100
    
    if not (day1_change > 2 and day2_change > -1 and day3_change > 2):
        return False, None, None
    
    # 条件2: 第3日阳线实体完全吞没第2日阴线
    # 第3日收盘价 > 第2日开盘价，第3日开盘价 < 第2日收盘价
    engulfing = (day3['close'] > day2['open']) and (day3['open'] < day2['close'])
    
    if not engulfing:
        return False, None, None
    
    # 条件3: 三日成交量逐步放大
    vol_ratio_2_1 = day2['volume'] / day1['volume'] if day1['volume'] > 0 else 0
    vol_ratio_3_2 = day3['volume'] / day2['volume'] if day2['volume'] > 0 else 0
    
    if not (vol_ratio_2_1 > 1.0 and vol_ratio_3_2 > 1.0):
        return False, None, None
    
    # 条件4: 形态出现在上升趋势中（5日均线 > 10日均线 > 20日均线）
    # 在第3天验证均线多头排列
    if pd.isna(day3['ma5']) or pd.isna(day3['ma10']) or pd.isna(day3['ma20']):
        return False, None, None
    
    ma_trend = (day3['ma5'] > day3['ma10']) and (day3['ma10'] > day3['ma20'])
    
    if not ma_trend:
        return False, None, None
    
    return True, vol_ratio_2_1, vol_ratio_3_2

def detect_patterns(end_date='2024-04-08'):
    """检测所有创业板股票的两阳夹一阴形态"""
    results = []
    
    print("正在获取创业板股票列表...")
    stock_list = get_chinext_stocks()
    print(f"共{len(stock_list)}只创业板股票")
    
    for idx, stock_code in enumerate(stock_list):
        if (idx + 1) % 50 == 0:
            print(f"进度: {idx + 1}/{len(stock_list)}")
        
        df = get_stock_data(stock_code, end_date)
        if df is None:
            continue
        
        # 计算均线
        df = calculate_ma(df)
        
        # 遍历近20个交易日（从倒数第20天到倒数第3天）
        # 因为需要连续3天，所以最后一个可检测的起始点是倒数第3天
        total_days = len(df)
        if total_days < 23:  # 至少需要23天（20天均线+3天形态）
            continue
        
        # 检测窗口：最近20个交易日内的任意3日连续窗口
        # 最后一天是end_date，往前数20个交易日
        start_idx = max(20, total_days - 20)  # 确保有足够的均线计算数据
        end_idx = total_days - 2  # 最后一个可作为第1天的索引（需要后续2天）
        
        for i in range(start_idx, end_idx):
            is_pattern, vol_ratio_2_1, vol_ratio_3_2 = check_bullish_sandwich(df, i)
            
            if is_pattern:
                pattern_date = df.iloc[i]['date'].strftime('%Y-%m-%d')
                results.append({
                    'code': stock_code,
                    'date': pattern_date,
                    'vol_ratio_2_1': f"{vol_ratio_2_1:.2f}",
                    'vol_ratio_3_2': f"{vol_ratio_3_2:.2f}"
                })
                print(f"发现形态: {stock_code} {pattern_date}")
    
    return results

def main():
    print("开始检测两阳夹一阴多方炮形态...")
    results = detect_patterns()
    
    output_file = 'bullish_sandwich.txt'
    
    if len(results) == 0:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        print(f"未发现符合条件的形态，结果已写入 {output_file}")
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            for r in results:
                f.write(f"{r['code']},{r['date']},{r['vol_ratio_2_1']},{r['vol_ratio_3_2']}\n")
        print(f"共发现{len(results)}个形态，结果已写入 {output_file}")

if __name__ == '__main__':
    main()
