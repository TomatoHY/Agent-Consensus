#!/usr/bin/env python3
"""
缩量整理后放量突破形态识别
"""
import sys
sys.path.append('/Users/tomato/Documents/potato/RealFin/GenericAgent/temp/tools')

from mootdx.quotes import Quotes
import pandas as pd
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 初始化客户端
client = Quotes.factory(market='std')

# 结果输出路径
result_dir = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_15_volume_price_contraction_breakout/revised/openclaw'
output_file = f'{result_dir}/contraction_breakout.txt'

def get_chinext_stocks():
    """获取创业板股票列表（300开头，不含301）"""
    try:
        all_stocks = client.stock_all()
        chinext = all_stocks[all_stocks['code'].str.startswith('300')]['code'].tolist()
        return chinext
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []

def analyze_stock(code):
    """分析单只股票的缩量整理后放量突破形态"""
    try:
        # 获取K线数据，offset=80确保有足够数据
        bars = client.bars(symbol=code, frequency=9, offset=80)
        
        if bars is None or len(bars) < 60:
            return None
        
        # 按日期排序，取最近60个交易日
        bars = bars.sort_index()
        bars = bars.tail(60)
        
        if len(bars) < 60:
            return None
        
        # 计算60日均量
        avg_volume_60 = bars['vol'].mean()
        
        results = []
        
        # 滑动窗口搜索缩量期（至少8天）
        i = 0
        while i < len(bars) - 8:
            # 检查从i开始的连续缩量期
            contraction_start = i
            contraction_end = i
            
            # 寻找连续缩量期的结束位置
            for j in range(i, len(bars)):
                if bars.iloc[j]['vol'] < avg_volume_60 * 0.7:
                    contraction_end = j
                else:
                    break
            
            # 缩量期长度
            contraction_length = contraction_end - contraction_start + 1
            
            # 条件1：连续至少8天缩量
            if contraction_length < 8:
                i += 1
                continue
            
            # 条件2：缩量期内价格波动幅度 < 5%
            contraction_bars = bars.iloc[contraction_start:contraction_end+1]
            price_high = contraction_bars['high'].max()
            price_low = contraction_bars['low'].min()
            price_volatility = (price_high - price_low) / price_low
            
            if price_volatility >= 0.05:
                i = contraction_end + 1
                continue
            
            # 条件3 & 4：缩量期结束后5个交易日内，寻找放量突破
            breakout_found = False
            breakout_idx = None
            
            for k in range(contraction_end + 1, min(contraction_end + 6, len(bars))):
                # 条件3：成交量超过60日均量的2.5倍
                if bars.iloc[k]['vol'] > avg_volume_60 * 2.5:
                    # 条件4：放量当天收盘价突破缩量期最高价
                    if bars.iloc[k]['close'] > price_high:
                        breakout_idx = k
                        breakout_found = True
                        break
            
            if not breakout_found:
                i = contraction_end + 1
                continue
            
            # 条件5：放量突破后，未出现单日跌幅超过5%的回调
            no_drawdown = True
            for m in range(breakout_idx + 1, len(bars)):
                daily_return = (bars.iloc[m]['close'] - bars.iloc[m-1]['close']) / bars.iloc[m-1]['close']
                if daily_return < -0.05:
                    no_drawdown = False
                    break
            
            if not no_drawdown:
                i = contraction_end + 1
                continue
            
            # 计算突破涨幅：(突破日收盘价 - 缩量期最高价) / 缩量期最高价 * 100
            breakout_gain = (bars.iloc[breakout_idx]['close'] - price_high) / price_high * 100
            
            # 记录结果
            result = {
                'code': code,
                'contraction_start': bars.index[contraction_start].strftime('%Y-%m-%d'),
                'contraction_end': bars.index[contraction_end].strftime('%Y-%m-%d'),
                'breakout_date': bars.index[breakout_idx].strftime('%Y-%m-%d'),
                'breakout_gain': round(breakout_gain, 1)
            }
            results.append(result)
            
            # 跳过重叠的缩量期
            i = breakout_idx + 1
        
        return results
    
    except Exception as e:
        # 静默处理错误，避免输出过多
        return None

def main():
    print("获取创业板股票列表...")
    chinext_stocks = get_chinext_stocks()
    print(f"创业板股票数量: {len(chinext_stocks)}")
    
    if not chinext_stocks:
        print("未获取到股票列表")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        return
    
    print("开始批量分析股票...")
    all_results = []
    
    # 使用线程池并发处理，控制并发数避免API限流
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(analyze_stock, code): code for code in chinext_stocks}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 100 == 0:
                print(f"已处理 {completed}/{len(chinext_stocks)} 只股票...")
            
            try:
                result = future.result(timeout=15)
                if result:
                    all_results.extend(result)
            except Exception as e:
                pass
            
            # 添加小延迟避免API限流
            time.sleep(0.01)
    
    print(f"分析完成，找到 {len(all_results)} 个符合条件的形态")
    
    # 写入结果文件
    with open(output_file, 'w', encoding='utf-8') as f:
        if len(all_results) == 0:
            f.write("无符合条件的股票\n")
        else:
            f.write("股票代码,缩量期开始日期,缩量期结束日期,放量突破日期,突破涨幅(%)\n")
            for r in all_results:
                f.write(f"{r['code']},{r['contraction_start']},{r['contraction_end']},{r['breakout_date']},{r['breakout_gain']}\n")
    
    print(f"结果已写入: {output_file}")
    print(f"共找到 {len(all_results)} 个符合条件的形态")

if __name__ == '__main__':
    main()
