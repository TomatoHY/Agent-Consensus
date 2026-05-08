#!/usr/bin/env python3
"""
识别创业板行业板块龙头股 - 优化版
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
start_dt = end_dt - timedelta(days=90)
START_DATE = start_dt.strftime("%Y%m%d")

print(f"分析时间范围: {START_DATE} 至 {END_DATE}")
print("=" * 80)

# 定义行业分类关键词
SECTOR_KEYWORDS = {
    '医药': ['医药', '生物', '制药', '医疗', '药业', '健康', '诊断', '器械'],
    '半导体': ['半导体', '芯片', '集成电路', '微电子', '晶圆', '封测'],
    '新能源': ['新能源', '光伏', '锂电', '电池', '储能', '风电', '太阳能'],
    '消费电子': ['消费电子', '电子', '光学', '显示', '摄像', '声学', '触控'],
    '软件': ['软件', '信息技术', '云计算', '大数据', '人工智能', '互联网', '网络'],
    '传媒': ['传媒', '广告', '影视', '游戏', '文化', '娱乐', '动漫'],
    '新材料': ['新材料', '材料', '化工新材料', '复合材料'],
    '高端装备': ['装备', '机械', '自动化', '智能制造', '机器人']
}

def classify_sector(stock_name):
    """根据股票名称分类行业"""
    for sector, keywords in SECTOR_KEYWORDS.items():
        for keyword in keywords:
            if keyword in stock_name:
                return sector
    return '其他'

# 获取创业板股票列表
print("\n获取创业板股票列表...")
try:
    stock_info = ak.stock_info_a_code_name()
    chinext_stocks = stock_info[stock_info['code'].str.startswith('300')].copy()
    chinext_stocks['sector'] = chinext_stocks['name'].apply(classify_sector)
    print(f"创业板股票总数: {len(chinext_stocks)}")
    
    sector_counts = chinext_stocks['sector'].value_counts()
    print("\n行业分类统计:")
    print(sector_counts.head(10))
    
    # 筛选主要行业
    main_sectors = [s for s in sector_counts.index if s != '其他' and sector_counts[s] >= 5]
    print(f"\n主要行业: {main_sectors}")
    
except Exception as e:
    print(f"获取股票列表失败: {e}")
    exit(1)

# 获取创业板指数成分股（更可靠的方法）
print("\n获取创业板指数成分股...")
try:
    # 尝试获取创业板50或创业板指数成分股
    index_stocks = []
    try:
        cyb50 = ak.index_stock_cons_csindex(symbol="399673")  # 创业板50
        if cyb50 is not None and not cyb50.empty:
            index_stocks.extend(cyb50['成分券代码'].tolist())
    except:
        pass
    
    try:
        cyb_index = ak.index_stock_cons_csindex(symbol="399006")  # 创业板指
        if cyb_index is not None and not cyb_index.empty:
            index_stocks.extend(cyb_index['成分券代码'].tolist())
    except:
        pass
    
    if index_stocks:
        index_stocks = list(set(index_stocks))
        print(f"获取到 {len(index_stocks)} 只指数成分股")
        # 优先分析指数成分股
        priority_stocks = chinext_stocks[chinext_stocks['code'].isin(index_stocks)]
        other_stocks = chinext_stocks[~chinext_stocks['code'].isin(index_stocks)]
        chinext_stocks = pd.concat([priority_stocks, other_stocks])
    
except Exception as e:
    print(f"获取指数成分股失败，使用全部创业板股票: {e}")

# 限制分析数量以加快速度
MAX_STOCKS = 200
chinext_stocks = chinext_stocks.head(MAX_STOCKS)
print(f"\n将分析前 {len(chinext_stocks)} 只股票")

# 批量获取股票数据
print("\n批量获取股票数据...")
stock_data_list = []
success_count = 0
fail_count = 0

for idx, row in chinext_stocks.iterrows():
    code = row['code']
    name = row['name']
    sector = row['sector']
    
    if sector not in main_sectors:
        continue
    
    try:
        # 获取日线数据
        df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                start_date=START_DATE, end_date=END_DATE, adjust="qfq")
        
        if df is None or len(df) < 25:
            fail_count += 1
            continue
        
        df = df.sort_values('日期')
        recent_20 = df.tail(20)
        
        if len(recent_20) < 20:
            fail_count += 1
            continue
        
        # 计算20日涨幅
        start_price = recent_20.iloc[0]['收盘']
        end_price = recent_20.iloc[-1]['收盘']
        return_20d = (end_price - start_price) / start_price * 100
        
        stock_data_list.append({
            'code': code,
            'name': name,
            'sector': sector,
            'return_20d': return_20d,
            'df': df
        })
        
        success_count += 1
        if success_count % 10 == 0:
            print(f"进度: {success_count} 成功, {fail_count} 失败")
        
    except Exception as e:
        fail_count += 1
        continue

print(f"\n数据获取完成: {success_count} 成功, {fail_count} 失败")

if len(stock_data_list) < 10:
    print("获取的数据太少，无法进行有效分析")
    output_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_33_sector_leadership/independent/openclaw/sector_leader.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 数据获取失败，无法完成分析\n")
    exit(1)

# 计算各行业平均涨幅
print("\n计算各行业平均涨幅...")
returns_df = pd.DataFrame(stock_data_list)
sector_avg_returns = returns_df.groupby('sector')['return_20d'].agg(['mean', 'count']).sort_values('mean', ascending=False)

print("\n各行业近20日平均涨幅:")
for sector, row in sector_avg_returns.iterrows():
    print(f"{sector}: {row['mean']:.2f}% (样本数: {int(row['count'])})")

# 选出涨幅前3的强势行业
top3_sectors = sector_avg_returns.head(3).index.tolist()
print(f"\n涨幅前3的强势行业: {top3_sectors}")

# 计算RS并筛选
print("\n计算相对强度RS...")
strong_sector_stocks = returns_df[returns_df['sector'].isin(top3_sectors)].copy()

rs_list = []
for idx, row in strong_sector_stocks.iterrows():
    sector_avg = sector_avg_returns.loc[row['sector'], 'mean']
    rs = row['return_20d'] / sector_avg if sector_avg != 0 else 0
    rs_list.append(rs)

strong_sector_stocks['RS'] = rs_list
leading_stocks = strong_sector_stocks[strong_sector_stocks['RS'] > 1.5].copy()

print(f"RS > 1.5 的领涨个股: {len(leading_stocks)}")

# 进一步筛选
print("\n进行进一步筛选...")
final_leaders = []

for idx, row in leading_stocks.iterrows():
    code = row['code']
    name = row['name']
    df = row['df']
    
    try:
        # 1. 流通市值
        try:
            stock_individual = ak.stock_individual_info_em(symbol=code)
            circ_market_cap_row = stock_individual[stock_individual['item'] == '流通市值']
            if circ_market_cap_row.empty:
                continue
            circ_market_cap = float(circ_market_cap_row.iloc[0]['value']) / 1e8
        except:
            continue
        
        if circ_market_cap <= 50:
            continue
        
        # 2. 换手率
        recent_20 = df.tail(20)
        avg_turnover = recent_20['换手率'].mean()
        if avg_turnover <= 5:
            continue
        
        # 3. MACD金叉
        recent_60 = df.tail(60)
        if len(recent_60) < 60:
            continue
        
        close_prices = recent_60['收盘'].values
        ema12 = pd.Series(close_prices).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close_prices).ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        
        recent_10_dif = dif.tail(10).values
        recent_10_dea = dea.tail(10).values
        
        has_golden_cross = False
        for i in range(1, len(recent_10_dif)):
            if recent_10_dif[i] > recent_10_dea[i] and recent_10_dif[i-1] <= recent_10_dea[i-1]:
                has_golden_cross = True
                break
        
        if not has_golden_cross:
            continue
        
        # 4. RSI
        delta = pd.Series(close_prices).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs_rsi = gain / loss
        rsi = 100 - (100 / (1 + rs_rsi))
        latest_rsi = rsi.iloc[-1]
        
        if latest_rsi <= 60:
            continue
        
        # 5. 创60日新高
        high_60d = recent_60['收盘'].max()
        latest_close = recent_60.iloc[-1]['收盘']
        
        if latest_close < high_60d * 0.999:
            continue
        
        final_leaders.append({
            'code': code,
            'name': name,
            'sector': row['sector'],
            'RS': row['RS'],
            'circ_market_cap': circ_market_cap,
            'avg_turnover': avg_turnover,
            'rsi': latest_rsi
        })
        
        print(f"✓ {code} {name} - {row['sector']} (RS={row['RS']:.2f}, 市值={circ_market_cap:.1f}亿, 换手率={avg_turnover:.2f}%, RSI={latest_rsi:.1f})")
        
    except Exception as e:
        continue

print(f"\n最终符合所有条件的龙头股: {len(final_leaders)}")

# 输出结果
output_file = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_33_sector_leadership/independent/openclaw/sector_leader.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    if len(final_leaders) == 0:
        f.write("# 截至2024-05-22，无符合所有条件的创业板行业龙头股\n")
        f.write("# 筛选条件：RS>1.5, 流通市值>50亿, 换手率>5%, MACD金叉, RSI>60, 创60日新高\n")
        f.write(f"# 分析了{len(main_sectors)}个行业，{success_count}只股票\n")
    else:
        f.write("股票代码,所属行业,RS值,流通市值(亿),换手率(%),RSI\n")
        for leader in final_leaders:
            f.write(f"{leader['code']},{leader['sector']},{leader['RS']:.2f},{leader['circ_market_cap']:.1f},{leader['avg_turnover']:.2f},{leader['rsi']:.1f}\n")

print(f"\n结果已保存到: {output_file}")
print("分析完成！")
