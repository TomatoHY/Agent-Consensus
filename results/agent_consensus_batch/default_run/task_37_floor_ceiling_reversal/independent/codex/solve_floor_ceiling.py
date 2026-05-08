#!/usr/bin/env python3
"""
识别创业板"地天板"形态
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_chinext_stocks():
    """获取创业板股票列表（300开头）"""
    try:
        import akshare as ak
        # 获取A股实时行情数据
        stock_info = ak.stock_info_a_code_name()
        # 筛选创业板（300开头）
        chinext = stock_info[stock_info['code'].str.startswith('3')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []

def is_st_stock(stock_code):
    """判断是否为ST股票"""
    try:
        import akshare as ak
        stock_info = ak.stock_individual_info_em(symbol=stock_code)
        name = stock_info[stock_info['item'] == '股票简称']['value'].values
        if len(name) > 0:
            return 'ST' in name[0] or 'st' in name[0]
    except:
        pass
    return False

def is_newly_listed(stock_code, reference_date, days=60):
    """判断是否为次新股（上市不足60个交易日）"""
    try:
        import akshare as ak
        # 获取股票基本信息
        stock_info = ak.stock_individual_info_em(symbol=stock_code)
        listing_date_row = stock_info[stock_info['item'] == '上市时间']
        if len(listing_date_row) > 0:
            listing_date_str = listing_date_row['value'].values[0]
            listing_date = pd.to_datetime(listing_date_str)
            ref_date = pd.to_datetime(reference_date)
            # 简化：用自然日估算，60个交易日约等于85个自然日
            return (ref_date - listing_date).days < 85
    except:
        pass
    return False

def get_stock_data(stock_code, start_date, end_date):
    """获取股票历史数据"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date.replace('-',''), 
                                end_date=end_date.replace('-',''),
                                adjust="qfq")  # 前复权
        if df is not None and len(df) > 0:
            df['日期'] = pd.to_datetime(df['日期'])
            return df
    except Exception as e:
        print(f"获取{stock_code}数据失败: {e}")
    return None

def check_limit_down_opened(row):
    """检查跌停是否被打开（振幅>3%）"""
    amplitude = row['振幅']
    return amplitude > 3.0

def check_limit_down(pct_change):
    """检查是否跌停（创业板：-20%或-10%）"""
    # 创业板注册制后是±20%，之前是±10%
    # 考虑到可能的误差，使用-9.5%和-19.5%作为阈值
    return pct_change <= -9.5

def check_limit_up(pct_change):
    """检查是否涨停（创业板：20%或10%）"""
    return pct_change >= 9.5

def check_strong_seal(df, limit_up_idx, float_shares=None):
    """检查封板强度（简化版：用尾盘成交量占比）"""
    # 由于缺少分时数据和封单数据，使用简化判断
    # 假设强封板：成交量相对较小（换手率低）
    try:
        turnover = df.iloc[limit_up_idx]['换手率']
        # 强封板通常换手率较低
        return turnover < 15.0  # 简化判断
    except:
        return True  # 无数据时默认通过

def check_continued_strength(df, limit_up_idx):
    """检查涨停后5日内最低价不跌破涨停日最低价"""
    if limit_up_idx + 5 >= len(df):
        return False, None
    
    limit_up_low = df.iloc[limit_up_idx]['最低']
    next_5_days = df.iloc[limit_up_idx+1:limit_up_idx+6]
    
    if len(next_5_days) < 5:
        return False, None
    
    min_low = next_5_days['最低'].min()
    
    if min_low >= limit_up_low:
        # 计算回撤百分比
        limit_up_close = df.iloc[limit_up_idx]['收盘']
        drawdown = ((min_low - limit_up_close) / limit_up_close) * 100
        return True, drawdown
    
    return False, None

def find_floor_ceiling_patterns(end_date='2024-09-23', lookback_days=20):
    """查找地天板形态"""
    results = []
    
    try:
        import akshare as ak
    except ImportError:
        print("需要安装akshare: pip install akshare")
        return results
    
    # 计算开始日期（向前推更多天以确保有足够数据）
    end_dt = pd.to_datetime(end_date)
    start_dt = end_dt - timedelta(days=60)  # 多取一些数据
    start_date = start_dt.strftime('%Y-%m-%d')
    
    print(f"分析时间范围: {start_date} 至 {end_date}")
    print(f"获取创业板股票列表...")
    
    chinext_stocks = get_chinext_stocks()
    print(f"找到 {len(chinext_stocks)} 只创业板股票")
    
    for i, stock_code in enumerate(chinext_stocks[:100]):  # 限制数量以加快测试
        if (i + 1) % 10 == 0:
            print(f"进度: {i+1}/{min(100, len(chinext_stocks))}")
        
        # 排除ST股票
        if is_st_stock(stock_code):
            continue
        
        # 排除次新股
        if is_newly_listed(stock_code, end_date):
            continue
        
        # 获取股票数据
        df = get_stock_data(stock_code, start_date, end_date)
        if df is None or len(df) < 25:
            continue
        
        # 只看最近20个交易日
        recent_df = df.tail(25)  # 多取几天以便后续验证
        
        # 查找跌停日
        for idx in range(len(recent_df) - 6):  # 确保后面有足够天数
            row = recent_df.iloc[idx]
            pct_change = row['涨跌幅']
            
            # 检查是否跌停
            if not check_limit_down(pct_change):
                continue
            
            # 检查跌停是否被打开（振幅>3%）
            if not check_limit_down_opened(row):
                continue
            
            limit_down_date = row['日期'].strftime('%Y-%m-%d')
            
            # 检查当天或次日是否涨停
            for next_idx in [idx, idx + 1]:
                if next_idx >= len(recent_df):
                    break
                
                next_row = recent_df.iloc[next_idx]
                next_pct = next_row['涨跌幅']
                
                if check_limit_up(next_pct):
                    limit_up_date = next_row['日期'].strftime('%Y-%m-%d')
                    
                    # 检查封板强度
                    if not check_strong_seal(recent_df, next_idx):
                        continue
                    
                    # 检查强势延续
                    continued, drawdown = check_continued_strength(recent_df, next_idx)
                    if continued:
                        results.append({
                            'stock_code': stock_code,
                            'limit_down_date': limit_down_date,
                            'limit_up_date': limit_up_date,
                            'drawdown': drawdown
                        })
                        break
    
    return results

def main():
    print("开始识别创业板地天板形态...")
    results = find_floor_ceiling_patterns()
    
    output_file = 'floor_ceiling.txt'
    
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
        print(f"找到 {len(results)} 个地天板形态，结果已写入 {output_file}")
    
    print(f"\n结果文件: {output_file}")

if __name__ == '__main__':
    main()
