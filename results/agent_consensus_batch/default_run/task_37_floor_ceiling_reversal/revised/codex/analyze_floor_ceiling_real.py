#!/usr/bin/env python3
"""
识别创业板"地天板"形态 - 使用真实数据
"""
import warnings
warnings.filterwarnings('ignore')

def main():
    try:
        from mootdx.quotes import Quotes
        import pandas as pd
        from datetime import datetime, timedelta
        
        print("开始使用mootdx获取真实数据...")
        client = Quotes.factory(market='std')
        
        # 截止日期
        end_date = datetime(2024, 9, 23)
        start_date = end_date - timedelta(days=60)  # 多取一些数据
        
        results = []
        checked_count = 0
        valid_count = 0
        
        print(f"扫描创业板股票（300000-300999）...")
        
        # 遍历创业板股票代码
        for code_num in range(300000, 301000):
            code = str(code_num)
            
            try:
                # 获取股票数据
                df = client.bars(symbol=code, frequency=9, offset=100)
                
                if df is None or len(df) == 0:
                    continue
                
                checked_count += 1
                if checked_count % 50 == 0:
                    print(f"已检查 {checked_count} 个有效股票...")
                
                # 转换日期
                df['date'] = pd.to_datetime(df['date'])
                
                # 筛选截止日期前的数据
                df = df[df['date'] <= end_date].copy()
                
                if len(df) < 30:
                    continue
                
                # 检查上市时间（简化：如果有足够历史数据则认为不是次新股）
                if len(df) < 60:
                    continue
                
                valid_count += 1
                if valid_count % 10 == 0:
                    print(f"  其中 {valid_count} 个满足基本条件（上市≥60日）")
                
                # 获取股票名称检查ST
                try:
                    stock_info = client.stocks(market='std')
                    stock_row = stock_info[stock_info['code'] == code]
                    if len(stock_row) > 0:
                        name = stock_row.iloc[0]['name']
                        if 'ST' in name or 'st' in name:
                            continue
                except:
                    pass
                
                # 计算涨跌幅和振幅
                df['pct_change'] = (df['close'] - df['close'].shift(1)) / df['close'].shift(1) * 100
                df['amplitude'] = (df['high'] - df['low']) / df['close'].shift(1) * 100
                
                # 只看最近20个交易日
                recent_df = df.tail(25).reset_index(drop=True)
                
                # 查找跌停日
                for idx in range(len(recent_df) - 6):
                    row = recent_df.iloc[idx]
                    pct_change = row['pct_change']
                    amplitude = row['amplitude']
                    
                    # 检查是否跌停（≤-9.5%）且振幅>3%
                    if pct_change <= -9.5 and amplitude > 3.0:
                        limit_down_date = row['date'].strftime('%Y-%m-%d')
                        
                        # 检查当天或次日是否涨停
                        for next_idx in [idx, idx + 1]:
                            if next_idx >= len(recent_df):
                                break
                            
                            next_row = recent_df.iloc[next_idx]
                            next_pct = next_row['pct_change']
                            
                            # 检查是否涨停（≥9.5%）
                            if next_pct >= 9.5:
                                limit_up_date = next_row['date'].strftime('%Y-%m-%d')
                                
                                # 检查强势延续（涨停后5日最低价≥涨停日最低价）
                                if next_idx + 5 < len(recent_df):
                                    limit_up_low = next_row['low']
                                    next_5_days = recent_df.iloc[next_idx+1:next_idx+6]
                                    
                                    if len(next_5_days) == 5:
                                        min_low = next_5_days['low'].min()
                                        
                                        if min_low >= limit_up_low:
                                            # 计算回撤
                                            limit_up_close = next_row['close']
                                            drawdown = ((min_low - limit_up_close) / limit_up_close) * 100
                                            
                                            results.append({
                                                'code': code,
                                                'limit_down_date': limit_down_date,
                                                'limit_up_date': limit_up_date,
                                                'drawdown': drawdown
                                            })
                                            break
            except Exception as e:
                continue
        
        print(f"\n扫描完成！")
        print(f"检查了 {checked_count} 个有效股票")
        print(f"其中 {valid_count} 个满足基本条件（上市≥60日）")
        print(f"找到 {len(results)} 个符合条件的地天板形态")
        
        # 写入结果
        with open('floor_ceiling.txt', 'w', encoding='utf-8') as f:
            f.write("股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n")
            if len(results) == 0:
                f.write("# 无符合条件的地天板形态\n")
            else:
                for r in results:
                    f.write(f"{r['code']},{r['limit_down_date']},{r['limit_up_date']},{r['drawdown']:.2f}\n")
        
        print(f"结果已保存到: floor_ceiling.txt")
        
    except ImportError:
        print("错误：需要安装mootdx库")
        print("由于无法访问真实数据，创建空结果文件")
        with open('floor_ceiling.txt', 'w', encoding='utf-8') as f:
            f.write("股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n")
            f.write("# 无法访问数据源\n")
    except Exception as e:
        print(f"错误: {e}")
        with open('floor_ceiling.txt', 'w', encoding='utf-8') as f:
            f.write("股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n")
            f.write("# 数据访问失败\n")

if __name__ == '__main__':
    main()
