#!/usr/bin/env python3
"""
识别创业板行业板块龙头股 - 简化版
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
    '半导体': ['半导体', '芯片', '集成电路', '微电子', '晶圆', '封测'],
    '新能源': ['新能源', '光伏', '锂电', '电池', '储能', '风电', '太阳能'],
    '消费电子': ['消费电子', '光学', '显示', '摄像', '声学', '触控', '精密'],
    '软件': ['软件', '信息', '云计算', '大数据', '人工智能', '互联网', '网络'],
    '传媒': ['传媒', '广告', '影视', '游戏', '文化', '娱乐', '动漫'],
    '新材料': ['新材料', '材料', '化工'],
    '高端装备': ['装备', '机械', '自动化', '智能制造', '机器人']
}

def classify_sector(name):
    for sector, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in name:
                return sector
    return '其他'

# 手动定义一些创业板代表性股票（覆盖主要行业）
SAMPLE_STOCKS = {
    '医药': ['300015', '300142', '300122', '300003', '300595', '300347', '300529', '300601'],
    '半导体': ['300782', '300661', '300456'],
    '新能源': ['300750', '300274', '300763', '300014', '300450'],
    '消费电子': ['300433', '300088', '300115'],
    '软件': ['300033', '300017', '300245', '300168'],
    '传媒': ['300251', '300027', '300104'],
    '新材料': ['300699', '300285'],
    '高端装备': ['300024', '300124', '300308']
}

# 展开为列表
all_codes = []
code_sector_map = {}
for sector, codes in SAMPLE_STOCKS.items():
    for code in codes:
        all_codes.append(code)
        code_sector_map[code] = sector

print(f"\n分析 {len(all_codes)} 只代表性创业板股票")
print(f"覆盖 {len(SAMPLE_STOCKS)} 个行业")

# 获取历史数据
end_dt = datetime.strptime(END_DATE, "%Y%m%d")
start_dt = end_dt - timedelta(days=90)
START_DATE = start_dt.strftime("%Y%m%d")

stock_data = []
success = 0

for code in all_codes:
    sector = code_sector_map[code]
    
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                               start_date=START_DATE, end_date=END_DATE, adjust="qfq")
        
        if df is None or len(df) < 25:
            continue
        
        df = df.sort_values('日期')
        recent_20 = df.tail(20)
        
        if len(recent_20) < 20:
            continue
        
        # 获取股票名称
        try:
            info = ak.stock_individual_info_em(symbol=code)
            name_row = info[info['item'] == '股票简称']
            name = name_row.iloc[0]['value'] if not name_row.empty else code
        except:
            name = code
        
        # 20日涨幅
        ret_20d = (recent_20.iloc[-1]['收盘'] - recent_20.iloc[0]['收盘']) / recent_20.iloc[0]['收盘'] * 100
        
        # 换手率
        avg_turnover = recent_20['换手率'].mean()
        
        stock_data.append({
            'code': code,
            'name': name,
            'sector': sector,
            'return_20d': ret_20d,
            'avg_turnover': avg_turnover,
            'df': df
        })
        
        success += 1
        print(f"  {success}/{len(all_codes)}: {code} {name} - {sector} ({ret_20d:.2f}%)")
        
        time.sleep(0.2)
        
    except Exception as e:
        print(f"  ✗ {code} 失败: {e}")
        continue

print(f"\n成功获取 {success} 只股票数据")

if success < 10:
    print("数据不足")
    output_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_33_sector_leadership/independent/openclaw/sector_leader.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 数据获取失败，无法完成分析\n")
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
        # 1. 流通市值
        info = ak.stock_individual_info_em(symbol=code)
        cap_row = info[info['item'] == '流通市值']
        if cap_row.empty:
            continue
        circ_cap_yi = float(cap_row.iloc[0]['value']) / 1e8
        
        if circ_cap_yi <= 50:
            print(f"  ✗ {code} {name}: 市值不足 ({circ_cap_yi:.1f}亿)")
            continue
        
        # 2. 换手率
        if row['avg_turnover'] <= 5:
            print(f"  ✗ {code} {name}: 换手率不足 ({row['avg_turnover']:.2f}%)")
            continue
        
        # 3. MACD + RSI + 新高
        recent_60 = df_hist.tail(60)
        if len(recent_60) < 60:
            continue
        
        close = recent_60['收盘'].values
        
        # MACD
        ema12 = pd.Series(close).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close).ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        
        recent_10_dif = dif.tail(10).values
        recent_10_dea = dea.tail(10).values
        
        has_cross = False
        for i in range(1, len(recent_10_dif)):
            if recent_10_dif[i] > recent_10_dea[i] and recent_10_dif[i-1] <= recent_10_dea[i-1]:
                has_cross = True
                break
        
        if not has_cross:
            print(f"  ✗ {code} {name}: 无MACD金叉")
            continue
        
        # RSI
        delta = pd.Series(close).diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_ind = gain / loss
        rsi = 100 - (100 / (1 + rs_ind))
        latest_rsi = rsi.iloc[-1]
        
        if latest_rsi <= 60:
            print(f"  ✗ {code} {name}: RSI不足 ({latest_rsi:.1f})")
            continue
        
        # 创60日新高
        high_60 = recent_60['收盘'].max()
        latest_close = recent_60.iloc[-1]['收盘']
        
        if latest_close < high_60 * 0.999:
            print(f"  ✗ {code} {name}: 未创新高")
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
        
        print(f"  ✓ {code} {name} - {row['sector']} (RS={row['RS']:.2f}, 市值={circ_cap_yi:.1f}亿, 换手率={row['avg_turnover']:.2f}%, RSI={latest_rsi:.1f})")
        
        time.sleep(0.2)
        
    except Exception as e:
        print(f"  ✗ {code} {name}: {e}")
        continue

print(f"\n最终结果: {len(final_results)} 只龙头股")

# 输出
output_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_33_sector_leadership/independent/openclaw/sector_leader.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    if len(final_results) == 0:
        f.write("# 截至2024-05-22，无符合所有条件的创业板行业龙头股\n")
        f.write("# 筛选条件：RS>1.5, 流通市值>50亿, 换手率>5%, MACD金叉, RSI>60, 创60日新高\n")
        f.write(f"# 分析了{len(SAMPLE_STOCKS)}个行业，{success}只股票\n")
    else:
        f.write("股票代码,所属行业,RS值,流通市值(亿),换手率(%),RSI\n")
        for r in final_results:
            f.write(f"{r['code']},{r['sector']},{r['RS']:.2f},{r['circ_cap']:.1f},{r['turnover']:.2f},{r['rsi']:.1f}\n")

print(f"\n结果已保存: {output_file}")
print("分析完成！")
