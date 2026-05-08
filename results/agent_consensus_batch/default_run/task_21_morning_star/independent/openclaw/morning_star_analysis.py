import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_chinext_stocks():
    """获取创业板股票列表"""
    stock_info = ak.stock_info_a_code_name()
    chinext = stock_info[stock_info['code'].str.startswith('300')]
    return chinext['code'].tolist()

def get_stock_data(stock_code, end_date='2024-03-08', days=90):
    """获取股票历史数据"""
    try:
        # 计算起始日期
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=days+100)  # 多取一些以确保有足够交易日
        start_date = start_dt.strftime('%Y%m%d')
        end_date_fmt = end_dt.strftime('%Y%m%d')
        
        # 获取日线数据
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date_fmt, adjust="qfq")
        
        if df is None or len(df) < 90:
            return None
            
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })
        
        # 确保日期格式
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
    except Exception as e:
        print(f"Error fetching {stock_code}: {e}")
        return None

def calculate_body_ratio(open_price, close_price, high_price, low_price):
    """计算实体占比 = |收盘-开盘| / (最高-最低)"""
    body = abs(close_price - open_price)
    amplitude = high_price - low_price
    if amplitude == 0:
        return 0
    return body / amplitude

def check_morning_star(df, idx):
    """
    检查从idx开始的3天是否构成早晨之星形态
    返回: (is_pattern, pattern_low, day3_close)
    """
    if idx + 2 >= len(df):
        return False, None, None
    
    # 第1天：大阴线
    day1 = df.iloc[idx]
    day1_change = (day1['close'] - day1['open']) / day1['open'] * 100
    day1_body_ratio = calculate_body_ratio(day1['open'], day1['close'], 
                                           day1['high'], day1['low'])
    
    # 条件1：跌幅>3%，实体占比>70%
    if day1_change > -3 or day1_body_ratio < 0.7:
        return False, None, None
    
    # 第2天：小K线
    day2 = df.iloc[idx + 1]
    day2_change = abs((day2['close'] - day2['open']) / day2['open'] * 100)
    
    # 条件2：涨跌幅绝对值<1.5%
    if day2_change >= 1.5:
        return False, None, None
    
    # 第3天：大阳线
    day3 = df.iloc[idx + 2]
    day3_change = (day3['close'] - day3['open']) / day3['open'] * 100
    day3_body_ratio = calculate_body_ratio(day3['open'], day3['close'],
                                           day3['high'], day3['low'])
    
    # 条件3：涨幅>3%，实体占比>70%
    if day3_change <= 3 or day3_body_ratio < 0.7:
        return False, None, None
    
    # 条件4：第3天收盘价高于第1天实体中点
    day1_midpoint = (day1['open'] + day1['close']) / 2
    if day3['close'] <= day1_midpoint:
        return False, None, None
    
    # 计算形态的最低价
    pattern_low = min(day1['low'], day2['low'], day3['low'])
    
    return True, pattern_low, day3['close']

def check_low_position(df, idx, window=60):
    """检查是否处于低位：收盘价 < 60日均价 × 90%"""
    if idx < window:
        return False
    
    # 计算60日均价（使用形态第1天及之前的60天）
    ma60 = df.iloc[idx-window:idx]['close'].mean()
    day1_close = df.iloc[idx]['close']
    
    return day1_close < ma60 * 0.9

def check_no_breakdown(df, idx, pattern_low):
    """检查形态后5个交易日内未跌破形态最低价"""
    # idx+2是第3天，idx+3到idx+7是后5个交易日
    if idx + 7 >= len(df):
        return False
    
    for i in range(idx + 3, idx + 8):
        if df.iloc[i]['low'] < pattern_low:
            return False
    
    return True

def calculate_5day_return(df, idx):
    """计算形态后5日涨幅：第8天收盘相对第3天收盘"""
    day3_close = df.iloc[idx + 2]['close']
    day8_close = df.iloc[idx + 7]['close']
    
    return (day8_close - day3_close) / day3_close * 100

def find_morning_star_patterns(stock_code, end_date='2024-03-08'):
    """查找某只股票的早晨之星形态"""
    df = get_stock_data(stock_code, end_date)
    if df is None:
        return []
    
    results = []
    
    # 找到截止日期的索引
    end_dt = pd.to_datetime(end_date)
    df_before_end = df[df['date'] <= end_dt]
    
    if len(df_before_end) < 30:
        return []
    
    # 在前30个交易日内查找（从倒数第30天到倒数第8天，因为需要后5天验证）
    start_idx = max(60, len(df_before_end) - 30)  # 至少需要60天计算均线
    end_idx = len(df_before_end) - 8  # 需要留出5天验证空间
    
    for idx in range(start_idx, end_idx + 1):
        # 检查早晨之星形态
        is_pattern, pattern_low, day3_close = check_morning_star(df, idx)
        if not is_pattern:
            continue
        
        # 检查低位要求
        if not check_low_position(df, idx):
            continue
        
        # 检查后续5天不跌破
        if not check_no_breakdown(df, idx, pattern_low):
            continue
        
        # 计算5日涨幅
        return_5d = calculate_5day_return(df, idx)
        
        # 记录结果（形态起始日期是第1天的日期）
        pattern_date = df.iloc[idx]['date'].strftime('%Y-%m-%d')
        results.append({
            'code': stock_code,
            'date': pattern_date,
            'return_5d': return_5d
        })
    
    return results

def main():
    print("开始分析创业板早晨之星形态...")
    
    # 获取创业板股票列表
    chinext_stocks = get_chinext_stocks()
    print(f"共找到 {len(chinext_stocks)} 只创业板股票")
    
    all_results = []
    
    # 遍历每只股票
    for i, stock_code in enumerate(chinext_stocks):
        if (i + 1) % 50 == 0:
            print(f"进度: {i+1}/{len(chinext_stocks)}")
        
        patterns = find_morning_star_patterns(stock_code)
        all_results.extend(patterns)
    
    # 保存结果
    output_file = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_21_morning_star/independent/openclaw/morning_star.txt'
    
    if len(all_results) == 0:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("无符合条件的早晨之星形态\n")
        print("未找到符合条件的早晨之星形态")
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            for result in all_results:
                f.write(f"{result['code']},{result['date']},{result['return_5d']:.2f}\n")
        print(f"找到 {len(all_results)} 个符合条件的早晨之星形态")
        print(f"结果已保存到 {output_file}")

if __name__ == "__main__":
    main()
