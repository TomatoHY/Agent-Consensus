#!/usr/bin/env python3
"""
识别创业板行业板块龙头股 - 使用实时行情数据
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import time
warnings.filterwarnings('ignore')

END_DATE = "20240522"
print(f"分析截止日期: {END_DATE}")
print("=" * 80)

# 定义行业分类
SECTOR_KEYWORDS = {
    '医药': ['医药', '生物', '制药', '医疗', '药业', '健康', '诊断', '器械', '疫苗'],
    '半导体': ['半导体', '芯片', '集成电路', '微电子', '晶圆', '封测', '电子'],
    '新能源': ['新能源', '光伏', '锂电', '电池', '储能', '风电', '太阳能', '能源'],
    '消费电子': ['消费电子', '光学', '显示', '摄像', '声学', '触控', '精密'],
    '软件': ['软件', '信息', '云计算', '大数据', '人工智能', '互联网', '网络', '科技'],
    '传媒': ['传媒', '广告', '影视', '游戏', '文化', '娱乐', '动漫', '出版'],
    '新材料': ['新材料', '材料', '化工', '复合'],
    '高端装备': ['装备', '机械', '自动化', '智能制造', '机器人', '仪器']
}

def classify_sector(stock_name):
    """根据股票名称分类行业"""
    for sector, keywords in SECTOR_KEYWORDS.items():
        for keyword in keywords:
            if keyword in stock_name:
                return sector
    return '其他'

# 获取创业板实时行情
print("\n获取创业板实时行情...")
try:
    # 获取创业板行情
    df_market = ak.stock_zh_a_spot_em()
    df_chinext = df_market[df_market['代码'].str.startswith('300')].copy()
    print(f"创业板股票数: {len(df_chinext)}")
    
    # 分类
    df_chinext['sector'] = df_chinext['名称'].apply(classify_sector)
    
    sector_counts = df_chinext['sector'].value_counts()
    print("\n行业分类:")
    for sector, count in sector_counts.items():
        if sector != '其他':
            print(f"  {sector}: {count}")
    
    main_sectors = [s for s in sector_counts.index if s != '其他' and sector_counts[s] >= 5]
    print(f"\n主要行业: {main_sectors}")
    
except Exception as e:
    print(f"获取行情失败: {e}")
    exit(1)

# 筛选主要行业的股票
df_main = df_chinext[df_chinext['sector'].isin(main_sectors)].copy()
print(f"\n主要行业股票数: {len(df_main)}")

# 获取历史数据计算20日涨幅
print("\n获取历史数据...")
end_dt = datetime.strptime(END_DATE, "%Y%m%d")
start_dt = end_dt - timedelta(days=90)
START_DATE = start_dt.strftime("%Y%m%d")

stock_data = []
success = 0
fail = 0

for idx, row in df_main.iterrows():
    code = row['代码']
    name = row['名称']
    sector = row['sector']
    
    try:
        df_hist = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                     start_date=START_DATE, end_date=END_DATE, adjust="qfq")
        
        if df_hist is None or len(df_hist) < 25:
            fail += 1
            continue
        
        df_hist = df_hist.sort_values('日期')
        recent_20 = df_hist.tail(20)
        
        if len(recent_20) < 20:
            fail += 1
            continue
        
        # 20日涨幅
        ret_20d = (recent_20.iloc[-1]['收盘'] - recent_20.iloc[0]['收盘']) / recent_20.iloc[0]['收盘'] * 100
        
        # 换手率
        avg_turnover = recent_20['换手率'].mean()
        
        # 流通市值（从实时行情）
        circ_cap = row['流通市值'] if '流通市值' in row and pd.notna(row['流通市值']) else 0
        
        stock_data.append({
            'code': code,
            'name': name,
            'sector': sector,
            'return_20d': ret_20d,
            'avg_turnover': avg_turnover,
            'circ_cap': circ_cap,
            'df': df_hist
        })
        
        success += 1
        if success % 20 == 0:
            print(f"  进度: {success}/{len(df_main)}")
        
        time.sleep(0.1)  # 避免请求过快
        
    except Exception as e:
        fail += 1
        continue

print(f"\n数据获取: {success} 成功, {fail} 失败")

if success < 20:
    print("数据不足，无法分析")
    output_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_33_sector_leadership/independent/openclaw/sector_leader.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 数据获取失败\n")
    exit(1)

# 计算行业平均涨幅
print("\n计算行业平均涨幅...")
df_stocks = pd.DataFrame(stock_data)
sector_stats = df_stocks.groupby('sector')['return_20d'].agg(['mean', 'count']).sort_values('mean', ascending=False)

print("\n各行业20日平均涨幅:")
for sector, row in sector_stats.iterrows():
    print(f"  {sector}: {row['mean']:.2f}% (样本: {int(row['count'])})")

# 前3强势行业
top3 = sector_stats.head(3).index.tolist()
print(f"\n前3强势行业: {top3}")

# 计算RS
print("\n计算相对强度...")
df_top3 = df_stocks[df_stocks['sector'].isin(top3)].copy()

rs_values = []
for idx, row in df_top3.iterrows():
    sector_avg = sector_stats.loc[row['sector'], 'mean']
    rs = row['return_20d'] / sector_avg if sector_avg != 0 else 0
    rs_values.append(rs)

df_top3['RS'] = rs_values
df_rs_filtered = df_top3[df_top3['RS'] > 1.5].copy()

print(f"RS > 1.5: {len(df_rs_filtered)} 只")

# 进一步筛选
print("\n进一步筛选...")
final_results = []

for idx, row in df_rs_filtered.iterrows():
    code = row['code']
    name = row['name']
    df_hist = row['df']
    
    try:
        # 1. 流通市值 > 50亿
        circ_cap_yi = row['circ_cap'] / 1e8 if row['circ_cap'] > 0 else 0
        if circ_cap_yi <= 50:
            continue
        
        # 2. 换手率 > 5%
        if row['avg_turnover'] <= 5:
            continue
        
        # 3. MACD金叉 + RSI > 60 + 创60日新高
        recent_60 = df_hist.tail(60)
        if len(recent_60) < 60:
            continue
        
        close = recent_60['收盘'].values
        
        # MACD
        ema12 = pd.Series(close).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close).ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        
        # 检查最近10日金叉
        recent_10_dif = dif.tail(10).values
        recent_10_dea = dea.tail(10).values
        
        has_cross = False
        for i in range(1, len(recent_10_dif)):
            if recent_10_dif[i] > recent_10_dea[i] and recent_10_dif[i-1] <= recent_10_dea[i-1]:
                has_cross = True
                break
        
        if not has_cross:
            continue
        
        # RSI
        delta = pd.Series(close).diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_ind = gain / loss
        rsi = 100 - (100 / (1 + rs_ind))
        latest_rsi = rsi.iloc[-1]
        
        if latest_rsi <= 60:
            continue
        
        # 创60日新高
        high_60 = recent_60['收盘'].max()
        latest_close = recent_60.iloc[-1]['收盘']
        
        if latest_close < high_60 * 0.999:
            continue
        
        final_results.append({
            'code': code,
            'name': name,
            'sector': row['sector'],
            'RS': row['RS'],
            'circ_cap': circ_cap_yi,
            'turnover': row['avg_turnover'],
            'rsi': latest_rsi
        })
        
        print(f"  ✓ {code} {name} - {row['sector']}")
        
    except Exception as e:
        continue

print(f"\n最终结果: {len(final_results)} 只龙头股")

# 输出
output_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_33_sector_leadership/independent/openclaw/sector_leader.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    if len(final_results) == 0:
        f.write("# 截至2024-05-22，无符合所有条件的创业板行业龙头股\n")
        f.write("# 筛选条件：RS>1.5, 流通市值>50亿, 换手率>5%, MACD金叉, RSI>60, 创60日新高\n")
        f.write(f"# 分析了{len(main_sectors)}个行业，{success}只股票\n")
    else:
        f.write("股票代码,所属行业,RS值,流通市值(亿),换手率(%),RSI\n")
        for r in final_results:
            f.write(f"{r['code']},{r['sector']},{r['RS']:.2f},{r['circ_cap']:.1f},{r['turnover']:.2f},{r['rsi']:.1f}\n")

print(f"\n结果已保存: {output_file}")
