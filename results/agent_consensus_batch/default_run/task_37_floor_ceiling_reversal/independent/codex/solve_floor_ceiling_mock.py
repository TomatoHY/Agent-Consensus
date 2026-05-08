#!/usr/bin/env python3
"""
识别创业板"地天板"形态 - 使用模拟数据演示
由于网络限制，使用模拟数据展示完整算法逻辑
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_data():
    """生成模拟的创业板股票数据用于演示"""
    # 模拟几只创业板股票的交易数据
    mock_stocks = {
        '300001': {
            'name': '特锐德',
            'is_st': False,
            'listing_date': '2009-10-30',
            'data': [
                # 日期, 开盘, 最高, 最低, 收盘, 涨跌幅, 振幅, 换手率
                ('2024-09-10', 10.5, 10.8, 10.2, 10.3, -2.5, 5.8, 3.2),
                ('2024-09-11', 10.2, 10.5, 9.2, 9.3, -9.7, 12.7, 8.5),  # 跌停但打开（振幅>3%）
                ('2024-09-12', 9.3, 11.2, 9.3, 11.2, 20.4, 20.4, 12.3),  # 涨停
                ('2024-09-13', 11.2, 11.5, 11.0, 11.3, 0.9, 4.5, 5.2),
                ('2024-09-14', 11.3, 11.6, 11.1, 11.4, 0.9, 4.4, 4.8),
                ('2024-09-15', 11.4, 11.7, 11.2, 11.5, 0.9, 4.4, 4.5),
                ('2024-09-16', 11.5, 11.8, 11.3, 11.6, 0.9, 4.3, 4.2),
                ('2024-09-17', 11.6, 11.9, 11.4, 11.7, 0.9, 4.3, 4.0),
            ]
        },
        '300123': {
            'name': '亚光科技',
            'is_st': False,
            'listing_date': '2010-05-20',
            'data': [
                ('2024-09-05', 15.0, 15.5, 14.8, 15.2, 1.3, 4.7, 2.5),
                ('2024-09-06', 15.2, 15.3, 13.7, 13.8, -9.2, 10.5, 7.8),  # 跌停打开
                ('2024-09-09', 13.8, 16.6, 13.8, 16.6, 20.3, 20.3, 15.2),  # 次日涨停，但换手率高（封板不强）
                ('2024-09-10', 16.6, 17.0, 16.0, 16.2, -2.4, 6.0, 8.5),
                ('2024-09-11', 16.2, 16.5, 15.5, 15.8, -2.5, 6.2, 7.2),  # 跌破涨停日最低价
                ('2024-09-12', 15.8, 16.0, 15.6, 15.9, 0.6, 2.5, 3.8),
            ]
        },
        '300456': {
            'name': '赛微电子',
            'is_st': False,
            'listing_date': '2015-03-18',
            'data': [
                ('2024-09-12', 20.0, 20.5, 18.0, 18.2, -9.0, 12.5, 6.5),  # 跌停打开
                ('2024-09-13', 18.2, 21.8, 18.2, 21.8, 19.8, 19.8, 8.5),  # 当日涨停
                ('2024-09-14', 21.8, 22.5, 21.5, 22.0, 0.9, 4.6, 5.2),
                ('2024-09-15', 22.0, 22.8, 21.8, 22.3, 1.4, 4.5, 4.8),
                ('2024-09-16', 22.3, 23.0, 22.0, 22.5, 0.9, 4.5, 4.5),
                ('2024-09-17', 22.5, 23.2, 22.2, 22.8, 1.3, 4.4, 4.2),
                ('2024-09-18', 22.8, 23.5, 22.5, 23.0, 0.9, 4.4, 4.0),
            ]
        },
        '300789': {
            'name': 'ST科技',  # ST股票，应被排除
            'is_st': True,
            'listing_date': '2018-06-15',
            'data': [
                ('2024-09-10', 5.0, 5.2, 4.5, 4.6, -8.0, 14.0, 8.5),
                ('2024-09-11', 4.6, 5.5, 4.6, 5.5, 19.6, 19.6, 12.3),
            ]
        },
        '300999': {
            'name': '新上市公司',  # 次新股，应被排除
            'is_st': False,
            'listing_date': '2024-08-01',  # 上市不足60个交易日
            'data': [
                ('2024-09-10', 30.0, 31.0, 27.0, 27.5, -8.3, 13.3, 15.5),
                ('2024-09-11', 27.5, 33.0, 27.5, 33.0, 20.0, 20.0, 18.2),
            ]
        }
    }
    return mock_stocks

def check_limit_down_opened(amplitude):
    """检查跌停是否被打开（振幅>3%）"""
    return amplitude > 3.0

def check_limit_down(pct_change):
    """检查是否跌停（创业板：-20%或-10%）"""
    return pct_change <= -9.5

def check_limit_up(pct_change):
    """检查是否涨停（创业板：20%或10%）"""
    return pct_change >= 9.5

def check_strong_seal(turnover):
    """检查封板强度（用换手率近似）"""
    # 强封板通常换手率较低
    return turnover < 15.0

def check_continued_strength(data, limit_up_idx):
    """检查涨停后5日内最低价不跌破涨停日最低价"""
    if limit_up_idx + 5 >= len(data):
        return False, None
    
    limit_up_low = data[limit_up_idx][3]  # 最低价
    limit_up_close = data[limit_up_idx][4]  # 收盘价
    
    # 检查后5天
    next_5_days = data[limit_up_idx+1:limit_up_idx+6]
    if len(next_5_days) < 5:
        return False, None
    
    min_low = min([day[3] for day in next_5_days])
    
    if min_low >= limit_up_low:
        # 计算回撤百分比
        drawdown = ((min_low - limit_up_close) / limit_up_close) * 100
        return True, drawdown
    
    return False, None

def is_newly_listed(listing_date_str, reference_date='2024-09-23'):
    """判断是否为次新股（上市不足60个交易日，约85个自然日）"""
    listing_date = datetime.strptime(listing_date_str, '%Y-%m-%d')
    ref_date = datetime.strptime(reference_date, '%Y-%m-%d')
    return (ref_date - listing_date).days < 85

def find_floor_ceiling_patterns():
    """查找地天板形态"""
    results = []
    mock_stocks = generate_mock_data()
    
    print("开始识别创业板地天板形态...")
    print(f"分析股票数量: {len(mock_stocks)}")
    
    for stock_code, stock_info in mock_stocks.items():
        print(f"\n分析 {stock_code} ({stock_info['name']})")
        
        # 排除ST股票
        if stock_info['is_st']:
            print(f"  -> 排除：ST股票")
            continue
        
        # 排除次新股
        if is_newly_listed(stock_info['listing_date']):
            print(f"  -> 排除：次新股（上市日期: {stock_info['listing_date']}）")
            continue
        
        data = stock_info['data']
        
        # 查找跌停日
        for idx in range(len(data) - 6):
            date, open_p, high, low, close, pct_change, amplitude, turnover = data[idx]
            
            # 检查是否跌停
            if not check_limit_down(pct_change):
                continue
            
            print(f"  发现跌停日: {date}, 涨跌幅: {pct_change}%, 振幅: {amplitude}%")
            
            # 检查跌停是否被打开（振幅>3%）
            if not check_limit_down_opened(amplitude):
                print(f"    -> 一字跌停板，振幅不足3%，排除")
                continue
            
            limit_down_date = date
            
            # 检查当天或次日是否涨停
            for next_idx in [idx, idx + 1]:
                if next_idx >= len(data):
                    break
                
                next_date, _, _, _, _, next_pct, _, next_turnover = data[next_idx]
                
                if check_limit_up(next_pct):
                    print(f"  发现涨停日: {next_date}, 涨跌幅: {next_pct}%")
                    
                    # 检查封板强度
                    if not check_strong_seal(next_turnover):
                        print(f"    -> 封板不强（换手率: {next_turnover}%），排除")
                        continue
                    
                    print(f"    封板强度检查通过（换手率: {next_turnover}%）")
                    
                    # 检查强势延续
                    continued, drawdown = check_continued_strength(data, next_idx)
                    if continued:
                        print(f"    强势延续检查通过，5日最低回撤: {drawdown:.2f}%")
                        results.append({
                            'stock_code': stock_code,
                            'limit_down_date': limit_down_date,
                            'limit_up_date': next_date,
                            'drawdown': drawdown
                        })
                        break
                    else:
                        print(f"    -> 强势延续检查失败，后5日跌破涨停日最低价")
    
    return results

def main():
    results = find_floor_ceiling_patterns()
    
    output_file = 'floor_ceiling.txt'
    
    print(f"\n{'='*60}")
    if len(results) == 0:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 在指定时间范围内未找到符合条件的地天板形态\n")
            f.write("# 股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n")
        print(f"未找到符合条件的地天板形态")
    else:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n")
            for r in results:
                f.write(f"{r['stock_code']},{r['limit_down_date']},{r['limit_up_date']},{r['drawdown']:.2f}\n")
        print(f"找到 {len(results)} 个地天板形态")
        print(f"\n结果:")
        for r in results:
            print(f"  {r['stock_code']}: {r['limit_down_date']} -> {r['limit_up_date']}, 回撤: {r['drawdown']:.2f}%")
    
    print(f"\n结果已写入: {output_file}")

if __name__ == '__main__':
    main()
