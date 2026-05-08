#!/usr/bin/env python3
"""
盘中异动信号检测 - 修订版
使用真实的mootdx数据源
"""

from mootdx.quotes import Quotes
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_trading_days_before(end_date, n_days=5):
    """获取指定日期之前的N个交易日（简化版本）"""
    dates = []
    current = end_date
    while len(dates) < n_days:
        if current.weekday() < 5:  # 周一到周五
            dates.append(current)
        current -= timedelta(days=1)
    return sorted(dates)

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
    """计算当日收盘价位置"""
    if daily_high == daily_low:
        return 50.0
    return (daily_close - daily_low) / (daily_high - daily_low) * 100

def main():
    print("开始检测盘中异动信号（使用真实mootdx数据）...")
    print("=" * 60)
    
    # 初始化mootdx客户端
    client = Quotes.factory(market='std')
    
    # 首先探测数据可用性
    print("\n探测数据源能力...")
    test_code = '000001'
    try:
        # 测试30分钟K线支持
        test_bars = client.bars(symbol=test_code, frequency=2, offset=10)
        if test_bars is not None and len(test_bars) > 0:
            print(f"✓ 30分钟K线支持确认 (frequency=2)")
            print(f"  数据范围: {test_bars.index[0]} 至 {test_bars.index[-1]}")
            latest_date = test_bars.index[-1]
            print(f"  最新数据日期: {latest_date}")
        else:
            print("✗ 无法获取30分钟K线数据")
            return
    except Exception as e:
        print(f"✗ 数据源测试失败: {e}")
        return
    
    # 检查2024-08-22数据可用性
    target_date = datetime(2024, 8, 22)
    print(f"\n目标日期: {target_date.strftime('%Y-%m-%d')}")
    
    # 获取股票列表
    print("\n获取股票列表...")
    try:
        stocks_sz = client.stocks(market=0)  # 深市
        stocks_sh = client.stocks(market=1)  # 沪市
        
        all_stocks = []
        if stocks_sz is not None:
            sz_codes = stocks_sz[stocks_sz['code'].str.match(r'^(000|002|300)')]['code'].tolist()
            all_stocks.extend(sz_codes)
        if stocks_sh is not None:
            sh_codes = stocks_sh[stocks_sh['code'].str.match(r'^(600|601|603|688)')]['code'].tolist()
            all_stocks.extend(sh_codes)
        
        # 限制数量以加快处理
        stock_pool = all_stocks[:800] if len(all_stocks) > 800 else all_stocks
        print(f"股票池数量: {len(stock_pool)}")
        
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        # 使用备用股票列表
        stock_pool = ['000001', '000002', '000333', '000651', '000858',
                      '600000', '600036', '600519', '601318', '601398']
        print(f"使用备用股票池: {len(stock_pool)}只")
    
    # 确定实际使用的交易日
    # 如果2024数据不可用，使用最新可用数据
    if latest_date.year < 2024 or (latest_date.year == 2024 and latest_date < target_date):
        print(f"\n⚠️  注意: 2024-08-22数据不可用")
        print(f"   使用最新可用数据演示检测逻辑")
        # 使用最新日期往前推5个交易日
        trading_days = get_trading_days_before(latest_date, n_days=6)
        data_note = f"使用{latest_date.strftime('%Y-%m-%d')}前5个交易日数据"
    else:
        trading_days = get_trading_days_before(target_date, n_days=6)
        data_note = "使用2024-08-22前5个交易日数据"
    
    print(f"\n{data_note}")
    print(f"分析时间范围: {trading_days[0].strftime('%Y-%m-%d')} 至 {trading_days[-2].strftime('%Y-%m-%d')}")
    
    results = []
    processed = 0
    
    print(f"\n开始检测异动信号...")
    
    for stock_code in stock_pool:
        for i, date in enumerate(trading_days[:-1]):
            try:
                # 获取30分钟K线数据
                # 需要获取足够多的数据以覆盖目标日期
                df_30min = client.bars(symbol=stock_code, frequency=2, offset=100)
                
                if df_30min is None or len(df_30min) == 0:
                    continue
                
                # 筛选目标日期的数据
                date_str = date.strftime('%Y-%m-%d')
                day_data = df_30min[df_30min.index.strftime('%Y-%m-%d') == date_str]
                
                if len(day_data) < 4:  # 至少需要4个30分钟K线
                    continue
                
                # 检测急拉信号
                surge_signals = detect_surge_signal(day_data)
                
                # 检测V型反转信号
                v_signals = detect_v_reversal(day_data)
                
                all_signals = surge_signals + v_signals
                
                if all_signals:
                    # 计算当日数据
                    daily_high = day_data['high'].max()
                    daily_low = day_data['low'].min()
                    daily_close = day_data.iloc[-1]['close']
                    
                    # 计算收盘位置
                    closing_pos = calculate_closing_position(daily_high, daily_low, daily_close)
                    
                    # 只保留收盘位置在上60%的信号
                    if closing_pos > 60:
                        # 获取次日数据
                        next_date = trading_days[i + 1]
                        next_date_str = next_date.strftime('%Y-%m-%d')
                        next_day_data = df_30min[df_30min.index.strftime('%Y-%m-%d') == next_date_str]
                        
                        if len(next_day_data) > 0:
                            next_day_close = next_day_data.iloc[-1]['close']
                            
                            # 检查次日持续
                            is_continued = next_day_close >= daily_low
                            
                            for signal in all_signals:
                                results.append({
                                    'stock_code': stock_code,
                                    'date': date_str,
                                    'type': signal['type'],
                                    'magnitude': signal['magnitude'],
                                    'closing_position': closing_pos,
                                    'continuation': '是' if is_continued else '否'
                                })
            
            except Exception as e:
                continue
        
        processed += 1
        if processed % 100 == 0:
            print(f"进度: {processed}/{len(stock_pool)}")
    
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
            f.write(f'# {data_note}\n')
    
    print(f"\n{'=' * 60}")
    print(f"检测完成！共发现 {len(results)} 个符合条件的异动信号")
    print(f"结果已保存至: {output_file}")
    
    if results:
        df_results = pd.DataFrame(results)
        print(f"\n信号类型分布:")
        print(df_results['type'].value_counts())
        print(f"\n次日持续情况:")
        print(df_results['continuation'].value_counts())
        print(f"\n前5条结果:")
        for r in results[:5]:
            print(f"{r['stock_code']},{r['date']},{r['type']},{r['magnitude']:.1f}%,{r['closing_position']:.1f}%,{r['continuation']}")

if __name__ == '__main__':
    main()
