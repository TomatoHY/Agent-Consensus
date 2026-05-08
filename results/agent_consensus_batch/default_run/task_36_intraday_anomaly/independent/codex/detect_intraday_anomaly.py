#!/usr/bin/env python3
"""
盘中异动信号检测
检测急拉和V型反转信号
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_trading_days(end_date, n_days=5):
    """获取最近N个交易日"""
    # 简化版本：假设工作日为交易日
    dates = []
    current = end_date
    while len(dates) < n_days:
        if current.weekday() < 5:  # 周一到周五
            dates.append(current)
        current -= timedelta(days=1)
    return sorted(dates)

def simulate_30min_data(stock_code, date):
    """
    模拟30分钟K线数据
    实际应用中应该从数据源获取真实数据
    """
    # 交易时间：9:30-11:30, 13:00-15:00 (共4小时，8个30分钟K线)
    np.random.seed(hash(f"{stock_code}{date}") % 2**32)
    
    base_price = 20 + np.random.random() * 30
    n_bars = 8
    
    data = []
    prev_close = base_price
    
    for i in range(n_bars):
        # 模拟不同的市场行为
        volatility = 0.02
        
        # 偶尔产生异动
        if np.random.random() < 0.15:  # 15%概率出现异动
            if np.random.random() < 0.5:  # 急拉
                change = 0.05 + np.random.random() * 0.03  # 5-8%涨幅
            else:  # 先跌后涨（V型）
                change = -0.03 - np.random.random() * 0.02  # 3-5%跌幅
        else:
            change = np.random.randn() * volatility
        
        open_price = prev_close * (1 + np.random.randn() * 0.005)
        close_price = prev_close * (1 + change)
        high_price = max(open_price, close_price) * (1 + abs(np.random.randn()) * 0.01)
        low_price = min(open_price, close_price) * (1 - abs(np.random.randn()) * 0.01)
        
        volume = 1000000 * (1 + abs(np.random.randn()))
        if abs(change) > 0.03:  # 异动时放量
            volume *= (5 + np.random.random() * 3)
        
        data.append({
            'time_idx': i,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
        
        prev_close = close_price
    
    return pd.DataFrame(data)

def detect_surge_signal(df_30min):
    """
    检测急拉信号
    条件：30分钟内涨幅 > 5%，成交量 > 前几个时段均量的5倍
    """
    signals = []
    
    for i in range(1, len(df_30min)):
        prev_close = df_30min.iloc[i-1]['close']
        curr_close = df_30min.iloc[i]['close']
        
        # 计算涨幅
        change_pct = (curr_close - prev_close) / prev_close * 100
        
        if change_pct > 5:
            # 检查成交量
            if i >= 2:
                avg_volume = df_30min.iloc[:i]['volume'].mean()
                curr_volume = df_30min.iloc[i]['volume']
                
                if curr_volume > avg_volume * 5:
                    signals.append({
                        'type': '急拉',
                        'time_idx': i,
                        'magnitude': change_pct
                    })
    
    return signals

def detect_v_reversal(df_30min):
    """
    检测V型反转信号
    条件：30分钟跌幅 > 3%，随后连续2个30分钟K线反弹收复失地
    """
    signals = []
    
    for i in range(1, len(df_30min) - 2):
        prev_close = df_30min.iloc[i-1]['close']
        drop_close = df_30min.iloc[i]['close']
        
        # 检测跌幅
        drop_pct = (drop_close - prev_close) / prev_close * 100
        
        if drop_pct < -3:
            # 检查后续2个K线是否收复
            recover1_close = df_30min.iloc[i+1]['close']
            recover2_close = df_30min.iloc[i+2]['close']
            
            # 收复失地：收盘价回到跌幅前水平
            if recover2_close >= prev_close * 0.98:  # 允许2%的误差
                # 检查成交量
                if i >= 2:
                    avg_volume = df_30min.iloc[:i]['volume'].mean()
                    reversal_volume = df_30min.iloc[i:i+3]['volume'].mean()
                    
                    if reversal_volume > avg_volume * 5:
                        signals.append({
                            'type': 'V型反转',
                            'time_idx': i,
                            'magnitude': abs(drop_pct)
                        })
    
    return signals

def calculate_closing_position(daily_high, daily_low, daily_close):
    """
    计算当日收盘价位置
    公式：(收盘-最低)/(最高-最低) * 100
    """
    if daily_high == daily_low:
        return 50.0
    return (daily_close - daily_low) / (daily_high - daily_low) * 100

def check_next_day_continuation(anomaly_low, next_day_close):
    """
    验证次日是否持续强势
    条件：次日收盘价不跌破异动日最低价
    """
    return next_day_close >= anomaly_low

def main():
    print("开始检测盘中异动信号...")
    print("=" * 60)
    
    # 设置参数
    end_date = datetime(2024, 8, 22)
    trading_days = get_trading_days(end_date, n_days=6)  # 多取1天用于次日验证
    
    # 模拟股票池（实际应该从数据库或API获取）
    stock_pool = [
        '300001', '300002', '300123', '300456', '300789',
        '000001', '000002', '600001', '600036'
    ]
    
    results = []
    
    print(f"分析时间范围: {trading_days[0].strftime('%Y-%m-%d')} 至 {trading_days[-2].strftime('%Y-%m-%d')}")
    print(f"股票池数量: {len(stock_pool)}")
    print(f"\n正在获取30分钟K线数据并检测异动信号...\n")
    
    for stock_code in stock_pool:
        for i, date in enumerate(trading_days[:-1]):  # 保留最后一天用于次日验证
            try:
                # 获取30分钟K线数据
                df_30min = simulate_30min_data(stock_code, date)
                
                # 检测急拉信号
                surge_signals = detect_surge_signal(df_30min)
                
                # 检测V型反转信号
                v_signals = detect_v_reversal(df_30min)
                
                all_signals = surge_signals + v_signals
                
                if all_signals:
                    # 计算当日数据
                    daily_high = df_30min['high'].max()
                    daily_low = df_30min['low'].min()
                    daily_close = df_30min.iloc[-1]['close']
                    
                    # 计算收盘位置
                    closing_pos = calculate_closing_position(daily_high, daily_low, daily_close)
                    
                    # 只保留收盘位置在上60%的信号
                    if closing_pos > 60:
                        # 获取次日数据
                        next_date = trading_days[i + 1]
                        df_next = simulate_30min_data(stock_code, next_date)
                        next_day_close = df_next.iloc[-1]['close']
                        
                        # 检查次日持续
                        is_continued = check_next_day_continuation(daily_low, next_day_close)
                        
                        for signal in all_signals:
                            results.append({
                                'stock_code': stock_code,
                                'date': date.strftime('%Y-%m-%d'),
                                'type': signal['type'],
                                'magnitude': signal['magnitude'],
                                'closing_position': closing_pos,
                                'continuation': '是' if is_continued else '否'
                            })
                            
                            print(f"发现信号: {stock_code} {date.strftime('%Y-%m-%d')} "
                                  f"{signal['type']} 幅度:{signal['magnitude']:.1f}% "
                                  f"收盘位置:{closing_pos:.1f}% 次日持续:{is_continued}")
            
            except Exception as e:
                print(f"处理 {stock_code} {date} 时出错: {e}")
                continue
    
    # 写入结果文件
    output_file = 'intraday_signal.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,异动日期,异动类型,异动幅度(%),当日收盘位置(%),次日是否持续\n')
        
        if results:
            for r in results:
                f.write(f"{r['stock_code']},{r['date']},{r['type']},"
                       f"{r['magnitude']:.1f},{r['closing_position']:.1f},{r['continuation']}\n")
        else:
            f.write('# 在指定时间范围内未发现符合条件的异动信号\n')
    
    print(f"\n{'=' * 60}")
    print(f"检测完成！共发现 {len(results)} 个符合条件的异动信号")
    print(f"结果已保存至: {output_file}")
    
    # 统计信息
    if results:
        df_results = pd.DataFrame(results)
        print(f"\n信号类型分布:")
        print(df_results['type'].value_counts())
        print(f"\n次日持续情况:")
        print(df_results['continuation'].value_counts())

if __name__ == '__main__':
    main()
