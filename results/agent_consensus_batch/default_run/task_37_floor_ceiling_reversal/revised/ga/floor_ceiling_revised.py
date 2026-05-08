#!/usr/bin/env python3
"""
识别创业板"地天板"形态 - 修订版
使用akshare数据源以确保与peer agents数据一致
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_chinext_stocks():
    """获取创业板股票列表（300开头）"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('3')]
        return chinext['code'].tolist()
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []

def is_st_stock(stock_code):
    """判断是否为ST股票"""
    try:
        stock_info = ak.stock_individual_info_em(symbol=stock_code)
        name = stock_info[stock_info['item'] == '股票简称']['value'].values[0]
        return 'ST' in name or 'st' in name
    except:
        return False

def get_listing_days(stock_code, end_date):
    """获取股票上市天数"""
    try:
        stock_info = ak.stock_individual_info_em(symbol=stock_code)
        listing_date_str = stock_info[stock_info['item'] == '上市时间']['value'].values[0]
        listing_date = pd.to_datetime(listing_date_str)
        days = (pd.to_datetime(end_date) - listing_date).days
        return days
    except:
        return 999  # 假设是老股票

def analyze_floor_ceiling(stock_code, end_date='2024-09-23'):
    """分析单个股票的地天板形态"""
    try:
        # 获取日线数据
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date="20240701", end_date=end_date.replace('-', ''),
                                adjust="qfq")
        
        if df is None or len(df) < 25:
            return None
        
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        df = df.reset_index(drop=True)
        
        # 计算涨跌幅和振幅
        df['涨跌幅'] = df['涨跌幅']  # akshare已经提供了涨跌幅
        df['振幅'] = df['振幅']  # akshare已经提供了振幅
        
        # 取最近25个交易日（20日窗口+5日验证）
        recent = df.tail(25).copy()
        recent = recent.reset_index(drop=True)
        
        if len(recent) < 25:
            return None
        
        # 在前20日内寻找跌停日
        search_window = recent.iloc[:20]
        
        results = []
        
        for i, row in search_window.iterrows():
            pct_change = row['涨跌幅']
            amplitude = row['振幅']
            
            # 判断是否跌停且被打开
            is_limit_down = (pct_change <= -9.5 or pct_change <= -19.5)
            is_opened = amplitude > 3
            
            if not (is_limit_down and is_opened):
                continue
            
            ld_date = row['日期']
            
            # 检查当日或次日是否涨停
            for offset in [0, 1]:
                lu_idx = i + offset
                if lu_idx >= len(recent):
                    continue
                
                lu_row = recent.iloc[lu_idx]
                lu_pct = lu_row['涨跌幅']
                
                # 判断是否涨停
                if lu_pct < 9.5:
                    continue
                
                lu_date = lu_row['日期']
                lu_low = lu_row['最低']
                
                # 检查后5日数据
                if lu_idx + 5 >= len(recent):
                    continue
                
                next_5 = recent.iloc[lu_idx + 1:lu_idx + 6]
                if len(next_5) < 5:
                    continue
                
                next_5_min = next_5['最低'].min()
                
                # 验证强势延续
                if next_5_min >= lu_low:
                    # 计算回撤
                    lu_close = lu_row['收盘']
                    drawdown = (next_5_min - lu_close) / lu_close * 100
                    
                    results.append({
                        'code': stock_code,
                        'ld_date': ld_date.strftime('%Y-%m-%d'),
                        'lu_date': lu_date.strftime('%Y-%m-%d'),
                        'drawdown': round(drawdown, 2)
                    })
                    break
        
        return results if results else None
        
    except Exception as e:
        return None

def main():
    """主函数"""
    end_date = '2024-09-23'
    output_file = 'floor_ceiling.txt'
    
    print("开始扫描创业板股票...")
    
    # 获取创业板股票列表
    stocks = get_chinext_stocks()
    print(f"获取到 {len(stocks)} 个创业板股票")
    
    all_results = []
    checked = 0
    
    for stock_code in stocks:
        checked += 1
        if checked % 100 == 0:
            print(f"已检查 {checked}/{len(stocks)} 个股票...")
        
        # 排除ST股票
        if is_st_stock(stock_code):
            continue
        
        # 排除次新股
        listing_days = get_listing_days(stock_code, end_date)
        if listing_days < 60:
            continue
        
        # 分析地天板形态
        results = analyze_floor_ceiling(stock_code, end_date)
        if results:
            all_results.extend(results)
            for r in results:
                print(f"找到: {r['code']}, 跌停: {r['ld_date']}, 涨停: {r['lu_date']}, 回撤: {r['drawdown']}%")
    
    print(f"\n扫描完成！找到 {len(all_results)} 个符合条件的地天板形态")
    
    # 写入结果
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)\n")
        if len(all_results) == 0:
            f.write("# 无符合条件的地天板形态\n")
        else:
            for r in all_results:
                f.write(f"{r['code']},{r['ld_date']},{r['lu_date']},{r['drawdown']}\n")
    
    print(f"结果已保存到: {output_file}")

if __name__ == "__main__":
    main()