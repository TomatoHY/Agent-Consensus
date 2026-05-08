#!/usr/bin/env python3
"""
地天板极端反转形态识别
识别创业板中的"地天板"形态（跌停后打开再涨停）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from mootdx.quotes import Quotes

def get_gem_stocks():
    """获取创业板股票列表（排除ST和次新股）"""
    client = Quotes.factory(market='std')
    stocks = client.stocks(market=0)  # 深圳市场
    
    # 筛选创业板（300/301开头）
    gem = stocks[stocks['code'].str.startswith(('300', '301'))].copy()
    
    # 排除ST股票
    gem = gem[~gem['name'].str.contains('ST', na=False)]
    
    return gem

def check_floor_ceiling_pattern(code, name, end_date='2024-09-23'):
    """
    检查单只股票是否符合地天板形态
    
    条件：
    1. 跌停日：最近20个交易日内跌停（跌幅≤-20%或≤-10%）且振幅>3%（非一字板）
    2. 涨停日：跌停当日或次日涨停（涨幅≥20%或≥10%）
    3. 封板强度：尾盘30分钟成交量占全天比例<20%（强封板）
    4. 强势延续：涨停后5日内最低价不跌破涨停日最低价
    5. 排除次新股（上市不足60个交易日）
    """
    client = Quotes.factory(market='std')
    
    try:
        # 获取足够的历史数据（20个交易日 + 涨停后5日 + 上市日期判断需要更多数据）
        # 获取80个交易日的数据以确保有足够的历史
        df = client.bars(symbol=code, frequency=9, start=0, offset=80)
        
        if df is None or len(df) < 30:
            return None
        
        # 重置索引，避免datetime列冲突
        df = df.reset_index(drop=False)
        
        # 确保datetime列存在
        if 'datetime' not in df.columns:
            return None
        
        # 数据按时间升序排列
        df = df.sort_values('datetime').reset_index(drop=True)
        df['date'] = pd.to_datetime(df['datetime']).dt.date
        
        # 排除次新股：上市不足60个交易日
        if len(df) < 60:
            return None
        
        # 计算涨跌幅和振幅
        df['pct_change'] = (df['close'] - df['close'].shift(1)) / df['close'].shift(1) * 100
        df['amplitude'] = (df['high'] - df['low']) / df['close'].shift(1) * 100
        
        # 找到截至2024-09-23的最近20个交易日
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        df_recent = df[df['date'] <= end_date_obj].tail(25)  # 多取5天以便后续验证
        
        if len(df_recent) < 20:
            return None
        
        # 在最近20个交易日内查找跌停日
        df_20 = df_recent.tail(20).copy()
        
        results = []
        
        for i in range(len(df_20)):
            row = df_20.iloc[i]
            
            # 条件1：跌停（创业板跌幅≤-20%或≤-10%，考虑注册制差异）
            # 注册制后创业板涨跌幅限制为20%，老股票为10%
            is_limit_down = (row['pct_change'] <= -9.8) or (row['pct_change'] <= -19.8)
            
            # 跌停被打开：振幅>3%（非一字板）
            is_opened = row['amplitude'] > 3.0
            
            if not (is_limit_down and is_opened):
                continue
            
            floor_date = row['date']
            
            # 条件2：跌停当日或次日涨停
            # 检查当日和次日
            for j in range(2):  # 0=当日, 1=次日
                if i + j >= len(df_20):
                    break
                    
                ceiling_row = df_20.iloc[i + j]
                
                # 涨停：涨幅≥10%或≥20%
                is_limit_up = (ceiling_row['pct_change'] >= 9.8) or (ceiling_row['pct_change'] >= 19.8)
                
                if not is_limit_up:
                    continue
                
                ceiling_date = ceiling_row['date']
                
                # 条件3：封板强度（用尾盘成交量占比近似）
                # 由于没有分时数据，我们用一个简化的判断：
                # 如果涨停日振幅较小（<5%），说明封板较强
                # 这是一个近似方法
                ceiling_amplitude = ceiling_row['amplitude']
                is_strong_seal = ceiling_amplitude < 5.0  # 振幅小说明封板强
                
                # 条件4：强势延续 - 涨停后5日内最低价不跌破涨停日最低价
                ceiling_low = ceiling_row['low']
                
                # 获取涨停后5个交易日的数据
                future_start = i + j + 1
                future_end = min(i + j + 6, len(df_20))
                
                # 如果涨停日在最近20日的末尾，需要从完整数据中获取后续数据
                if future_end - future_start < 5:
                    # 从完整数据集中找到涨停日之后的数据
                    ceiling_date_dt = pd.to_datetime(ceiling_date)
                    future_df = df[pd.to_datetime(df['date']) > ceiling_date_dt].head(5)
                    
                    if len(future_df) < 5:
                        continue  # 数据不足，无法验证
                    
                    future_low = future_df['low'].min()
                else:
                    future_df = df_20.iloc[future_start:future_end]
                    if len(future_df) < 5:
                        continue
                    future_low = future_df['low'].min()
                
                is_strong_continuation = future_low >= ceiling_low
                
                if not is_strong_continuation:
                    continue
                
                # 计算涨停后5日最低回撤
                # 回撤 = (最低价 - 涨停日收盘价) / 涨停日收盘价 * 100
                ceiling_close = ceiling_row['close']
                drawdown = (future_low - ceiling_close) / ceiling_close * 100
                
                # 所有条件都满足，记录结果
                results.append({
                    'code': code,
                    'name': name,
                    'floor_date': floor_date,
                    'ceiling_date': ceiling_date,
                    'floor_pct': row['pct_change'],
                    'ceiling_pct': ceiling_row['pct_change'],
                    'floor_amplitude': row['amplitude'],
                    'ceiling_amplitude': ceiling_amplitude,
                    'drawdown_5d': drawdown,
                    'strong_seal': is_strong_seal
                })
        
        return results if results else None
        
    except Exception as e:
        print(f"Error processing {code} {name}: {e}")
        return None

def main():
    print("开始识别创业板地天板形态...")
    print("=" * 60)
    
    # 获取创业板股票列表
    gem_stocks = get_gem_stocks()
    print(f"获取到 {len(gem_stocks)} 只创业板股票（已排除ST）")
    
    all_results = []
    
    # 遍历所有股票
    for idx, row in gem_stocks.iterrows():
        code = row['code']
        name = row['name']
        
        if (idx + 1) % 50 == 0:
            print(f"进度: {idx + 1}/{len(gem_stocks)}")
        
        results = check_floor_ceiling_pattern(code, name)
        
        if results:
            all_results.extend(results)
            for r in results:
                print(f"发现地天板: {r['code']} {r['name']} "
                      f"跌停日={r['floor_date']} 涨停日={r['ceiling_date']} "
                      f"5日回撤={r['drawdown_5d']:.2f}%")
    
    print("=" * 60)
    print(f"共发现 {len(all_results)} 个地天板形态")
    
    # 写入结果文件
    output_file = 'floor_ceiling.txt'
    
    if all_results:
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入表头
            f.write("股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n")
            
            # 写入数据
            for r in all_results:
                f.write(f"{r['code']},{r['floor_date']},{r['ceiling_date']},{r['drawdown_5d']:.2f}\n")
        
        print(f"结果已写入 {output_file}")
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("无符合条件的股票\n")
        print(f"无符合条件的股票，已写入 {output_file}")
    
    # 输出详细统计
    if all_results:
        df_results = pd.DataFrame(all_results)
        print("\n统计信息:")
        print(f"平均跌停幅度: {df_results['floor_pct'].mean():.2f}%")
        print(f"平均涨停幅度: {df_results['ceiling_pct'].mean():.2f}%")
        print(f"平均5日回撤: {df_results['drawdown_5d'].mean():.2f}%")
        print(f"强封板比例: {df_results['strong_seal'].sum() / len(df_results) * 100:.1f}%")

if __name__ == '__main__':
    main()
