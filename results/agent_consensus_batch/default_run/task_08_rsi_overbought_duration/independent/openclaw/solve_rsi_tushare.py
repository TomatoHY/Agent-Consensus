#!/usr/bin/env python3
"""
RSI超买持续时间分析 - 使用tushare
"""

import pandas as pd
import numpy as np
from pathlib import Path
import tushare as ts

def calculate_rsi(prices, period=14):
    """计算RSI指标（Wilder平滑法）"""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    rsi_values = []
    
    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100 - 100 / (1 + rs))
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - 100 / (1 + rs))
    
    result = [np.nan] * period + rsi_values
    return np.array(result)


def get_chinext_stocks():
    """获取创业板股票列表"""
    try:
        pro = ts.pro_api()
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,market')
        # 创业板股票代码以300开头
        chinext = df[df['symbol'].str.startswith('300')]
        return chinext['ts_code'].tolist()
    except Exception as e:
        print(f"Tushare获取失败: {e}")
        # 如果tushare失败，使用备用方法
        try:
            import akshare as ak
            stock_info = ak.stock_info_a_code_name()
            chinext = stock_info[stock_info['code'].str.startswith('300')]
            # 转换为tushare格式 (300001 -> 300001.SZ)
            return [f"{code}.SZ" for code in chinext['code'].tolist()]
        except Exception as e2:
            print(f"Akshare获取失败: {e2}")
            return []


def get_stock_data_tushare(ts_code, end_date='20241031', days=40):
    """使用tushare获取股票数据"""
    try:
        from datetime import datetime, timedelta
        
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        start_dt = end_dt - timedelta(days=days*2)
        start_date = start_dt.strftime('%Y%m%d')
        
        pro = ts.pro_api()
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if df is None or len(df) == 0:
            return None
        
        # 按日期排序
        df = df.sort_values('trade_date')
        df = df.tail(days)
        
        return df
    except Exception as e:
        return None


def get_stock_data_akshare(stock_code, end_date='20241031', days=40):
    """使用akshare获取股票数据"""
    try:
        import akshare as ak
        from datetime import datetime, timedelta
        
        # 去掉.SZ后缀
        if '.' in stock_code:
            stock_code = stock_code.split('.')[0]
        
        start_dt = datetime.strptime(end_date, '%Y%m%d') - timedelta(days=days*2)
        start_date = start_dt.strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df is None or len(df) == 0:
            return None
        
        df = df.sort_values('日期')
        df = df.tail(days)
        
        # 统一列名
        df = df.rename(columns={'收盘': 'close'})
        
        return df
    except Exception as e:
        return None


def analyze_rsi_overbought(end_date='20241031', analysis_days=20, rsi_period=14):
    """分析RSI超买持续时间"""
    print(f"开始分析RSI超买持续时间...")
    print(f"截止日期: {end_date}")
    print(f"分析周期: 最近{analysis_days}个交易日")
    print(f"RSI周期: {rsi_period}日\n")
    
    chinext_stocks = get_chinext_stocks()
    print(f"获取到 {len(chinext_stocks)} 只创业板股票\n")
    
    if len(chinext_stocks) == 0:
        print("未获取到创业板股票")
        return []
    
    results = []
    total = len(chinext_stocks)
    success_count = 0
    required_days = analysis_days + rsi_period
    
    for idx, stock_code in enumerate(chinext_stocks, 1):
        if idx % 100 == 0:
            print(f"进度: {idx}/{total}, 成功: {success_count}")
        
        # 先尝试tushare
        df = get_stock_data_tushare(stock_code, end_date, days=required_days)
        
        # 如果tushare失败，尝试akshare
        if df is None or len(df) < required_days:
            df = get_stock_data_akshare(stock_code, end_date, days=required_days)
        
        if df is None or len(df) < required_days:
            continue
        
        success_count += 1
        
        # 提取收盘价
        if 'close' in df.columns:
            close_prices = df['close'].values
        else:
            close_prices = df['收盘'].values
        
        rsi_values = calculate_rsi(close_prices, period=rsi_period)
        recent_rsi = rsi_values[-analysis_days:]
        overbought_days = np.sum(recent_rsi > 70)
        
        if overbought_days > 0:
            # 提取纯数字代码
            code = stock_code.split('.')[0] if '.' in stock_code else stock_code
            results.append({
                'code': code,
                'overbought_days': int(overbought_days)
            })
    
    print(f"\n分析完成，成功获取 {success_count} 只股票数据")
    print(f"共 {len(results)} 只股票有超买记录")
    
    results.sort(key=lambda x: x['overbought_days'], reverse=True)
    return results


def main():
    """主函数"""
    results = analyze_rsi_overbought(end_date='20241031', analysis_days=20, rsi_period=14)
    
    if len(results) == 0:
        print("\n警告：未找到任何超买股票")
        output_file = Path(__file__).parent / "rsi_overbought_top3.txt"
        output_file.write_text("")
        return
    
    top3 = results[:3]
    
    print("\n=== RSI超买持续时间 TOP 3 ===")
    for item in top3:
        print(f"{item['code']}: {item['overbought_days']}天")
    
    output_file = Path(__file__).parent / "rsi_overbought_top3.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in top3:
            f.write(f"{item['code']},{item['overbought_days']}\n")
    
    print(f"\n结果已保存到: {output_file}")


if __name__ == "__main__":
    main()

