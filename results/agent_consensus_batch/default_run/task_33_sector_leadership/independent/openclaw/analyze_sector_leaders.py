#!/usr/bin/env python3
"""
识别创业板行业板块龙头股
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 设置截止日期
END_DATE = "20240522"
end_dt = datetime.strptime(END_DATE, "%Y%m%d")
start_dt = end_dt - timedelta(days=90)  # 获取更多历史数据以确保有足够的交易日

START_DATE = start_dt.strftime("%Y%m%d")

print(f"分析时间范围: {START_DATE} 至 {END_DATE}")
print("=" * 80)

# 第一步：获取创业板股票列表
print("\n第一步：获取创业板股票列表...")
try:
    stock_info = ak.stock_info_a_code_name()
    chinext_stocks = stock_info[stock_info['code'].str.startswith('300')].copy()
    print(f"创业板股票总数: {len(chinext_stocks)}")
except Exception as e:
    print(f"获取股票列表失败: {e}")
    exit(1)

# 定义行业分类（基于创业板主要行业）
SECTOR_KEYWORDS = {
    '医药': ['医药', '生物', '制药', '医疗', '药业', '健康'],
    '半导体': ['半导体', '芯片', '集成电路', '微电子'],
    '新能源': ['新能源', '光伏', '锂电', '电池', '储能', '风电'],
    '消费电子': ['消费电子', '电子', '光学', '显示', '摄像'],
    '软件': ['软件', '信息技术', '云计算', '大数据', '人工智能'],
    '传媒': ['传媒', '广告', '影视', '游戏', '文化'],
    '新材料': ['新材料', '材料', '化工新材料'],
    '高端装备': ['装备', '机械', '自动化', '智能制造']
}

def classify_sector(stock_name):
    """根据股票名称分类行业"""
    for sector, keywords in SECTOR_KEYWORDS.items():
        for keyword in keywords:
            if keyword in stock_name:
                return sector
    return '其他'

# 为股票分类
chinext_stocks['sector'] = chinext_stocks['name'].apply(classify_sector)
print("\n行业分类统计:")
sector_counts = chinext_stocks['sector'].value_counts()
print(sector_counts)

# 筛选主要行业（至少有5只股票）
main_sectors = sector_counts[sector_counts >= 5].index.tolist()
if '其他' in main_sectors:
    main_sectors.remove('其他')
print(f"\n主要行业（至少5只股票）: {main_sectors}")

# 第二步：计算各股票近20日涨幅
print("\n第二步：计算各股票近20日涨幅...")
stock_returns = []

for idx, row in chinext_stocks.iterrows():
    code = row['code']
    sector = row['sector']
    
    if sector not in main_sectors:
        continue
    
    try:
        # 获取日线数据
        df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                start_date=START_DATE, end_date=END_DATE, adjust="qfq")
        
        if df is None or len(df) < 20:
            continue
        
        df = df.sort_values('日期')
        recent_20 = df.tail(20)
        
        if len(recent_20) < 20:
            continue
        
        # 计算20日涨幅
        start_price = recent_20.iloc[0]['收盘']
        end_price = recent_20.iloc[-1]['收盘']
        return_20d = (end_price - start_price) / start_price * 100
        
        # 获取最新数据用于后续筛选
        latest = df.iloc[-1]
        
        stock_returns.append({
            'code': code,
            'name': row['name'],
            'sector': sector,
            'return_20d': return_20d,
            'close_price': end_price,
            'df': df  # 保存完整数据用于后续计算
        })
        
    except Exception as e:
        continue

print(f"成功获取 {len(stock_returns)} 只股票的数据")

# 第三步：计算各行业等权平均涨幅
print("\n第三步：计算各行业等权平均涨幅...")
returns_df = pd.DataFrame(stock_returns)

sector_avg_returns = returns_df.groupby('sector')['return_20d'].mean().sort_values(ascending=False)
print("\n各行业近20日平均涨幅:")
for sector, ret in sector_avg_returns.items():
    print(f"{sector}: {ret:.2f}%")

# 选出涨幅前3的强势行业
top3_sectors = sector_avg_returns.head(3).index.tolist()
print(f"\n涨幅前3的强势行业: {top3_sectors}")

# 第四步：计算个股相对强度RS
print("\n第四步：计算个股相对强度RS...")
strong_sector_stocks = returns_df[returns_df['sector'].isin(top3_sectors)].copy()

# 计算RS
rs_list = []
for idx, row in strong_sector_stocks.iterrows():
    sector_avg = sector_avg_returns[row['sector']]
    rs = row['return_20d'] / sector_avg if sector_avg != 0 else 0
    rs_list.append(rs)

strong_sector_stocks['RS'] = rs_list

# 筛选RS > 1.5
leading_stocks = strong_sector_stocks[strong_sector_stocks['RS'] > 1.5].copy()
print(f"RS > 1.5 的领涨个股数量: {len(leading_stocks)}")

# 第五步：进一步筛选
print("\n第五步：进行进一步筛选...")
final_leaders = []

for idx, row in leading_stocks.iterrows():
    code = row['code']
    df = row['df']
    
    try:
        # 1. 获取流通市值
        stock_individual = ak.stock_individual_info_em(symbol=code)
        if stock_individual is not None and not stock_individual.empty:
            circ_market_cap_row = stock_individual[stock_individual['item'] == '流通市值']
            if not circ_market_cap_row.empty:
                circ_market_cap = float(circ_market_cap_row.iloc[0]['value']) / 1e8  # 转换为亿元
            else:
                continue
        else:
            continue
        
        # 筛选条件1: 流通市值 > 50亿
        if circ_market_cap <= 50:
            continue
        
        # 2. 计算近20日换手率均值
        recent_20 = df.tail(20)
        avg_turnover = recent_20['换手率'].mean()
        
        # 筛选条件2: 换手率 > 5%
        if avg_turnover <= 5:
            continue
        
        # 3. 计算MACD
        recent_60 = df.tail(60)
        if len(recent_60) < 60:
            continue
        
        close_prices = recent_60['收盘'].values
        
        # 计算EMA
        ema12 = pd.Series(close_prices).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close_prices).ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = (dif - dea) * 2
        
        # 检查最近10日内是否有MACD金叉
        recent_10_dif = dif.tail(10).values
        recent_10_dea = dea.tail(10).values
        
        has_golden_cross = False
        for i in range(1, len(recent_10_dif)):
            if recent_10_dif[i] > recent_10_dea[i] and recent_10_dif[i-1] <= recent_10_dea[i-1]:
                has_golden_cross = True
                break
        
        if not has_golden_cross:
            continue
        
        # 4. 计算RSI
        delta = pd.Series(close_prices).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs_rsi = gain / loss
        rsi = 100 - (100 / (1 + rs_rsi))
        latest_rsi = rsi.iloc[-1]
        
        # 筛选条件3: RSI > 60
        if latest_rsi <= 60:
            continue
        
        # 5. 检查是否创60日新高
        high_60d = recent_60['收盘'].max()
        latest_close = recent_60.iloc[-1]['收盘']
        
        # 筛选条件4: 创60日新高
        if latest_close < high_60d * 0.999:  # 允许0.1%的误差
            continue
        
        # 所有条件都满足，加入最终结果
        final_leaders.append({
            'code': code,
            'name': row['name'],
            'sector': row['sector'],
            'RS': row['RS'],
            'circ_market_cap': circ_market_cap,
            'avg_turnover': avg_turnover,
            'rsi': latest_rsi
        })
        
        print(f"✓ {code} {row['name']} - {row['sector']} (RS={row['RS']:.2f}, 市值={circ_market_cap:.1f}亿, 换手率={avg_turnover:.2f}%, RSI={latest_rsi:.1f})")
        
    except Exception as e:
        print(f"✗ {code} 处理失败: {e}")
        continue

print(f"\n最终符合所有条件的龙头股数量: {len(final_leaders)}")

# 第六步：输出结果
print("\n第六步：输出结果到 sector_leader.txt...")
output_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_33_sector_leadership/independent/openclaw/sector_leader.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    if len(final_leaders) == 0:
        f.write("# 截至2024-05-22，无符合所有条件的创业板行业龙头股\n")
        f.write("# 筛选条件：RS>1.5, 流通市值>50亿, 换手率>5%, MACD金叉, RSI>60, 创60日新高\n")
    else:
        f.write("股票代码,所属行业,RS值,流通市值(亿),换手率(%),RSI\n")
        for leader in final_leaders:
            f.write(f"{leader['code']},{leader['sector']},{leader['RS']:.2f},{leader['circ_market_cap']:.1f},{leader['avg_turnover']:.2f},{leader['rsi']:.1f}\n")

print(f"结果已保存到: {output_file}")
print("\n分析完成！")
