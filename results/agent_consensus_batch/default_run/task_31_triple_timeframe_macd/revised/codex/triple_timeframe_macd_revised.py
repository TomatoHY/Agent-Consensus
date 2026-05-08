"""
三周期MACD共振选股 - 改进版
使用真实数据API（akshare）获取日线、周线、月线数据
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def calculate_macd(df, fast=12, slow=26, signal=9):
    """
    计算MACD指标
    返回DIFF, DEA, MACD柱
    """
    # 计算EMA
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    
    # DIFF = 快线 - 慢线
    diff = ema_fast - ema_slow
    
    # DEA = DIFF的signal周期EMA
    dea = diff.ewm(span=signal, adjust=False).mean()
    
    # MACD柱 = (DIFF - DEA) * 2
    macd = (diff - dea) * 2
    
    return diff, dea, macd

def find_golden_cross(diff, dea, lookback_periods):
    """
    查找最近lookback_periods内的金叉
    返回金叉日期索引，如果没有返回None
    """
    if len(diff) < lookback_periods + 1:
        return None
    
    # 检查最近lookback_periods个周期
    for i in range(len(diff) - 1, max(0, len(diff) - lookback_periods - 1), -1):
        if i > 0:
            # 金叉：前一个周期DIFF < DEA，当前周期DIFF > DEA
            if diff.iloc[i-1] < dea.iloc[i-1] and diff.iloc[i] > dea.iloc[i]:
                return i
    return None

def calculate_ma(series, period=20):
    """计算移动平均线"""
    return series.rolling(window=period).mean()

def get_stock_data_with_akshare(stock_code, end_date, period='daily'):
    """
    使用akshare获取股票数据
    """
    try:
        import akshare as ak
        
        # 转换股票代码格式
        symbol = stock_code
        
        # 计算开始日期
        if period == 'daily':
            start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=200)).strftime('%Y%m%d')
        elif period == 'weekly':
            start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=400)).strftime('%Y%m%d')
        else:  # monthly
            start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=1200)).strftime('%Y%m%d')
        
        end_date_fmt = end_date.replace('-', '')
        
        # 获取数据
        df = ak.stock_zh_a_hist(symbol=symbol, period=period, start_date=start_date, 
                                end_date=end_date_fmt, adjust="qfq")
        
        if df is None or len(df) == 0:
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
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        return df
        
    except Exception as e:
        print(f"获取{stock_code}的{period}数据失败: {e}")
        return None

def check_stock_conditions(stock_code, end_date='2024-03-22'):
    """
    检查股票是否满足三周期MACD共振条件
    """
    try:
        # 1. 获取三个时间维度的数据
        daily_df = get_stock_data_with_akshare(stock_code, end_date, 'daily')
        weekly_df = get_stock_data_with_akshare(stock_code, end_date, 'weekly')
        monthly_df = get_stock_data_with_akshare(stock_code, end_date, 'monthly')
        
        if daily_df is None or weekly_df is None or monthly_df is None:
            return None
            
        if len(daily_df) < 50 or len(weekly_df) < 30 or len(monthly_df) < 20:
            return None
        
        # 2. 计算三个周期的MACD（参数12/26/9）
        daily_diff, daily_dea, daily_macd = calculate_macd(daily_df)
        weekly_diff, weekly_dea, weekly_macd = calculate_macd(weekly_df)
        monthly_diff, monthly_dea, monthly_macd = calculate_macd(monthly_df)
        
        # 3. 计算三个周期的20均线
        daily_ma20 = calculate_ma(daily_df['close'], 20)
        weekly_ma20 = calculate_ma(weekly_df['close'], 20)
        monthly_ma20 = calculate_ma(monthly_df['close'], 20)
        
        # 4. 检查条件
        
        # 条件1：日线金叉在最后10个交易日内
        daily_cross_idx = find_golden_cross(daily_diff, daily_dea, 10)
        if daily_cross_idx is None:
            return None
        daily_cross_date = daily_df.iloc[daily_cross_idx]['date'].strftime('%Y-%m-%d')
        
        # 条件2：周线金叉在最后4周内
        weekly_cross_idx = find_golden_cross(weekly_diff, weekly_dea, 4)
        if weekly_cross_idx is None:
            return None
        weekly_cross_date = weekly_df.iloc[weekly_cross_idx]['date'].strftime('%Y-%m-%d')
        
        # 条件3：月线MACD在0轴上方或最近2个月内金叉
        monthly_diff_latest = monthly_diff.iloc[-1]
        monthly_cross_idx = find_golden_cross(monthly_diff, monthly_dea, 2)
        
        if monthly_cross_idx is not None:
            monthly_status = "金叉"
        elif monthly_diff_latest > 0:
            monthly_status = "上方"
        else:
            return None
        
        # 条件4：三个周期的收盘价均在各自的20均线上方
        daily_close_latest = daily_df.iloc[-1]['close']
        daily_ma20_latest = daily_ma20.iloc[-1]
        
        weekly_close_latest = weekly_df.iloc[-1]['close']
        weekly_ma20_latest = weekly_ma20.iloc[-1]
        
        monthly_close_latest = monthly_df.iloc[-1]['close']
        monthly_ma20_latest = monthly_ma20.iloc[-1]
        
        if not (daily_close_latest > daily_ma20_latest and 
                weekly_close_latest > weekly_ma20_latest and 
                monthly_close_latest > monthly_ma20_latest):
            return None
        
        # 所有条件满足，返回结果
        return {
            'stock_code': stock_code,
            'daily_cross_date': daily_cross_date,
            'weekly_cross_date': weekly_cross_date,
            'monthly_status': monthly_status,
            'daily_diff': round(daily_diff.iloc[-1], 2),
            'weekly_diff': round(weekly_diff.iloc[-1], 2),
            'monthly_diff': round(monthly_diff.iloc[-1], 2)
        }
        
    except Exception as e:
        print(f"处理股票 {stock_code} 时出错: {e}")
        return None

def get_stock_list():
    """
    获取创业板股票列表
    """
    try:
        import akshare as ak
        # 获取A股列表
        stock_info = ak.stock_zh_a_spot_em()
        # 筛选创业板（代码以300开头）
        gem_stocks = stock_info[stock_info['代码'].str.startswith('300')]['代码'].tolist()
        return gem_stocks[:50]  # 限制数量以加快测试
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        # 返回一些示例代码
        return ['300001', '300002', '300003', '300010', '300015',
                '300020', '300025', '300030', '300035', '300040']

def main():
    """主函数"""
    end_date = '2024-03-22'
    results = []
    
    print(f"开始筛选三周期MACD共振股票，截止日期：{end_date}")
    
    # 获取股票列表
    stock_pool = get_stock_list()
    print(f"检查股票池大小：{len(stock_pool)}")
    
    for i, stock_code in enumerate(stock_pool):
        if i % 10 == 0:
            print(f"进度: {i}/{len(stock_pool)}")
        
        result = check_stock_conditions(stock_code, end_date)
        if result:
            results.append(result)
            print(f"找到符合条件的股票: {stock_code}")
    
    # 写入结果文件
    output_file = 'triple_timeframe_macd.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(results) == 0:
            f.write("无符合条件的股票\n")
            print(f"\n未找到符合条件的股票")
        else:
            # 写入表头
            f.write("股票代码,日线金叉日期,周线金叉日期,月线MACD状态,日线DIFF,周线DIFF,月线DIFF\n")
            
            # 写入数据
            for r in results:
                line = f"{r['stock_code']},{r['daily_cross_date']},{r['weekly_cross_date']},{r['monthly_status']},{r['daily_diff']},{r['weekly_diff']},{r['monthly_diff']}\n"
                f.write(line)
            
            print(f"\n共找到 {len(results)} 只符合条件的股票")
            print(f"结果已写入: {output_file}")

if __name__ == '__main__':
    main()
