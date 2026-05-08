#!/usr/bin/env python3
"""
ETF成分股滞涨套利机会识别
分析截至2024-06-24的ETF与成分股价格背离情况
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_etf_data(etf_code, end_date='2024-06-24', days=30):
    """获取ETF历史数据"""
    try:
        # 使用akshare获取ETF数据
        df = ak.fund_etf_hist_em(symbol=etf_code, period="daily", start_date="20240520", end_date="20240624", adjust="qfq")
        if df is not None and len(df) > 0:
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期')
            return df
    except Exception as e:
        print(f"获取ETF {etf_code} 数据失败: {e}")
    return None

def calculate_etf_trend(df):
    """计算ETF趋势指标"""
    if df is None or len(df) < 20:
        return None

    # 取最近20个交易日
    df_recent = df.tail(20).copy()

    # 计算20日涨幅
    start_price = df_recent.iloc[0]['收盘']
    end_price = df_recent.iloc[-1]['收盘']
    return_20d = (end_price - start_price) / start_price * 100

    # 计算5日和20日均线
    df_recent['ma5'] = df_recent['收盘'].rolling(window=5).mean()
    df_recent['ma20'] = df_recent['收盘'].rolling(window=20).mean()

    latest_ma5 = df_recent.iloc[-1]['ma5']
    latest_ma20 = df_recent.iloc[-1]['ma20']

    return {
        'return_20d': return_20d,
        'ma5': latest_ma5,
        'ma20': latest_ma20,
        'is_uptrend': return_20d > 8 and latest_ma5 > latest_ma20
    }

def get_stock_data(stock_code, end_date='2024-06-24'):
    """获取个股历史数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date="20240520", end_date="20240624", adjust="qfq")
        if df is not None and len(df) > 0:
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期')
            return df
    except Exception as e:
        print(f"获取股票 {stock_code} 数据失败: {e}")
    return None

def calculate_stock_return(df):
    """计算个股20日涨幅"""
    if df is None or len(df) < 20:
        return None

    df_recent = df.tail(20)
    start_price = df_recent.iloc[0]['收盘']
    end_price = df_recent.iloc[-1]['收盘']
    return_20d = (end_price - start_price) / start_price * 100

    return return_20d

def get_stock_fundamentals(stock_code):
    """获取个股基本面数据"""
    try:
        # 获取个股信息
        df = ak.stock_individual_info_em(symbol=stock_code)
        if df is not None and len(df) > 0:
            info_dict = dict(zip(df['item'], df['value']))

            pe = None
            roe = None

            # 提取PE
            if '市盈率-动态' in info_dict:
                try:
                    pe = float(info_dict['市盈率-动态'])
                except:
                    pass

            # 获取ROE - 需要从财务数据获取
            try:
                finance_df = ak.stock_financial_analysis_indicator(symbol=stock_code)
                if finance_df is not None and len(finance_df) > 0:
                    # 取最新一期数据
                    latest = finance_df.iloc[0]
                    if '净资产收益率' in latest:
                        roe = float(latest['净资产收益率'])
            except:
                pass

            return {'pe': pe, 'roe': roe}
    except Exception as e:
        print(f"获取股票 {stock_code} 基本面失败: {e}")

    return {'pe': None, 'roe': None}

def calculate_macd(df):
    """计算MACD指标"""
    if df is None or len(df) < 26:
        return None, None, None

    close = df['收盘']

    # 计算EMA
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    # DIFF = EMA12 - EMA26
    diff = ema12 - ema26

    # DEA = DIFF的9日EMA
    dea = diff.ewm(span=9, adjust=False).mean()

    # MACD = (DIFF - DEA) * 2
    macd = (diff - dea) * 2

    return diff.iloc[-1], dea.iloc[-1], macd.iloc[-1]

def calculate_kdj(df, n=9):
    """计算KDJ指标"""
    if df is None or len(df) < n:
        return None, None, None

    df_calc = df.tail(n+10).copy()

    low_list = df_calc['低'].rolling(window=n).min()
    high_list = df_calc['高'].rolling(window=n).max()

    rsv = (df_calc['收盘'] - low_list) / (high_list - low_list) * 100

    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d

    return k.iloc[-1], d.iloc[-1], j.iloc[-1]

def check_technical_signals(stock_code):
    """检查技术面启动信号"""
    df = get_stock_data(stock_code)
    if df is None or len(df) < 30:
        return False, {}

    # 计算MACD
    diff, dea, macd = calculate_macd(df)

    # 计算KDJ
    k, d, j = calculate_kdj(df)

    if diff is None or dea is None or k is None:
        return False, {}

    # MACD将金叉或刚金叉：DIFF上穿DEA或距离缩小到0.05以内
    macd_signal = (diff > dea and abs(diff - dea) < 0.5) or (diff > dea and macd > 0)

    # KDJ < 50（低位）
    kdj_signal = j < 50

    signals = {
        'diff': diff,
        'dea': dea,
        'macd': macd,
        'k': k,
        'd': d,
        'j': j,
        'macd_golden': macd_signal,
        'kdj_low': kdj_signal
    }

    return macd_signal and kdj_signal, signals

def get_etf_constituents_approximate(etf_code):
    """获取ETF成分股的近似列表（使用行业股票）"""
    # 医药ETF (159929) - 医药生物行业
    if etf_code == "159929":
        # 获取创业板医药股
        try:
            df = ak.stock_zh_a_spot_em()
            df = df[df['代码'].str.startswith('300')]  # 创业板
            # 筛选医药相关
            medical_keywords = ['医药', '生物', '制药', '医疗', '健康', '药业']
            mask = df['名称'].str.contains('|'.join(medical_keywords), na=False)
            stocks = df[mask]['代码'].tolist()[:30]  # 取前30只
            return stocks
        except:
            return ['300015', '300122', '300142', '300347', '300463', '300595', '300676', '300759']

    # 半导体ETF (159813) - 半导体行业
    elif etf_code == "159813":
        try:
            df = ak.stock_zh_a_spot_em()
            df = df[df['代码'].str.startswith('300')]
            semi_keywords = ['半导体', '芯片', '集成电路', '微电子']
            mask = df['名称'].str.contains('|'.join(semi_keywords), na=False)
            stocks = df[mask]['代码'].tolist()[:30]
            return stocks
        except:
            return ['300223', '300456', '300782', '300661']

    # 新能源ETF (159642) - 新能源行业
    elif etf_code == "159642":
        try:
            df = ak.stock_zh_a_spot_em()
            df = df[df['代码'].str.startswith('300')]
            energy_keywords = ['新能源', '光伏', '锂电', '电池', '储能', '风电']
            mask = df['名称'].str.contains('|'.join(energy_keywords), na=False)
            stocks = df[mask]['代码'].tolist()[:30]
            return stocks
        except:
            return ['300014', '300274', '300750', '300763']

    return []

def main():
    """主函数"""
    print("=" * 60)
    print("ETF成分股滞涨套利机会识别")
    print("分析日期: 2024-06-24")
    print("=" * 60)

    # 第一步：检查ETF上涨趋势
    etf_list = [
        ("159929", "医药ETF"),
        ("159813", "半导体ETF"),
        ("159642", "新能源ETF")
    ]

    uptrend_etfs = []

    print("\n第一步：识别上涨趋势的ETF")
    print("-" * 60)

    for etf_code, etf_name in etf_list:
        print(f"\n检查 {etf_name} ({etf_code})...")
        df = get_etf_data(etf_code)

        if df is not None:
            trend = calculate_etf_trend(df)
            if trend:
                print(f"  20日涨幅: {trend['return_20d']:.2f}%")
                print(f"  5日均线: {trend['ma5']:.2f}")
                print(f"  20日均线: {trend['ma20']:.2f}")
                print(f"  上涨趋势: {'是' if trend['is_uptrend'] else '否'}")

                if trend['is_uptrend']:
                    uptrend_etfs.append({
                        'code': etf_code,
                        'name': etf_name,
                        'return_20d': trend['return_20d']
                    })

    if not uptrend_etfs:
        print("\n未找到符合上涨趋势的ETF")
        with open('/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_34_etf_constituent_arbitrage/independent/claudecode/etf_arbitrage.txt', 'w', encoding='utf-8') as f:
            f.write("股票代码,对应ETF代码,个股涨幅(%),ETF涨幅(%),滞涨率(%),PE,ROE(%)\n")
            f.write("# 无符合条件的滞涨股\n")
        return

    print(f"\n找到 {len(uptrend_etfs)} 个上涨趋势的ETF")

    # 第二步和第三步：分析成分股，找出滞涨股
    print("\n第二步：分析成分股滞涨情况")
    print("-" * 60)

    results = []

    for etf_info in uptrend_etfs:
        etf_code = etf_info['code']
        etf_name = etf_info['name']
        etf_return = etf_info['return_20d']

        print(f"\n分析 {etf_name} 的成分股...")

        constituents = get_etf_constituents_approximate(etf_code)
        print(f"  获取到 {len(constituents)} 只成分股")

        lag_threshold = etf_return * 0.5  # 滞涨阈值：ETF涨幅的50%

        for stock_code in constituents[:15]:  # 检查前15只
            stock_return = calculate_stock_return(get_stock_data(stock_code))

            if stock_return is None:
                continue

            # 检查是否滞涨
            if stock_return < lag_threshold:
                print(f"  发现滞涨股: {stock_code}, 涨幅: {stock_return:.2f}%")

                # 第三步：验证基本面
                fundamentals = get_stock_fundamentals(stock_code)
                pe = fundamentals['pe']
                roe = fundamentals['roe']

                # 基本面健康：PE > 0, ROE > 8%
                if pe is not None and roe is not None and pe > 0 and roe > 8:
                    print(f"    基本面健康: PE={pe:.2f}, ROE={roe:.2f}%")

                    # 第四步：检查技术面启动信号
                    has_signal, signals = check_technical_signals(stock_code)

                    if has_signal:
                        print(f"    技术面启动信号确认!")

                        lag_rate = (etf_return - stock_return) / etf_return * 100

                        results.append({
                            'stock_code': stock_code,
                            'etf_code': etf_code,
                            'stock_return': stock_return,
                            'etf_return': etf_return,
                            'lag_rate': lag_rate,
                            'pe': pe,
                            'roe': roe
                        })

    # 输出结果
    print("\n" + "=" * 60)
    print("分析完成，生成结果文件")
    print("=" * 60)

    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_34_etf_constituent_arbitrage/independent/claudecode/etf_arbitrage.txt'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("股票代码,对应ETF代码,个股涨幅(%),ETF涨幅(%),滞涨率(%),PE,ROE(%)\n")

        if results:
            for r in results:
                f.write(f"{r['stock_code']},{r['etf_code']},{r['stock_return']:.2f},{r['etf_return']:.2f},{r['lag_rate']:.2f},{r['pe']:.2f},{r['roe']:.2f}\n")
            print(f"\n找到 {len(results)} 个符合条件的套利机会")
        else:
            f.write("# 无符合条件的滞涨股\n")
            print("\n未找到符合所有条件的滞涨股")

    print(f"\n结果已保存到: {output_path}")

if __name__ == "__main__":
    main()
