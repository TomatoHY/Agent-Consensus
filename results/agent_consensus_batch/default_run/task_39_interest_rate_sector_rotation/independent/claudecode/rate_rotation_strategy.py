#!/usr/bin/env python3
"""
利率敏感型行业轮动策略
Interest Rate Sensitive Sector Rotation Strategy
"""

import akshare as ak
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta

def get_interest_rate_data(end_date='2024-11-22'):
    """
    获取利率数据 - 尝试多种数据源
    Try multiple data sources for interest rate
    """
    print("正在获取利率数据...")

    try:
        # 方法1: 尝试获取中国国债收益率数据
        print("尝试获取中国国债收益率数据...")
        bond_yield_df = ak.bond_china_yield()
        if bond_yield_df is not None and not bond_yield_df.empty:
            bond_yield_df['日期'] = pd.to_datetime(bond_yield_df['日期'])
            bond_yield_df = bond_yield_df[bond_yield_df['日期'] <= end_date]
            bond_yield_df = bond_yield_df.sort_values('日期')

            # 获取10年期国债收益率
            if '10年期国债收益率' in bond_yield_df.columns:
                recent_data = bond_yield_df[['日期', '10年期国债收益率']].tail(60)
                recent_data.columns = ['date', 'rate']
                recent_data['rate'] = pd.to_numeric(recent_data['rate'], errors='coerce')
                recent_data = recent_data.dropna()
                if len(recent_data) >= 20:
                    print(f"成功获取国债收益率数据，共{len(recent_data)}条记录")
                    return recent_data, "10年期国债收益率"
    except Exception as e:
        print(f"获取国债收益率失败: {e}")

    try:
        # 方法2: 使用债券ETF 511010 (国债ETF) 价格反推
        print("尝试使用债券ETF 511010数据...")
        etf_df = ak.fund_etf_hist_em(symbol="511010", period="daily", start_date="20240901", end_date="20241122", adjust="qfq")
        if etf_df is not None and not etf_df.empty:
            etf_df['日期'] = pd.to_datetime(etf_df['日期'])
            etf_df = etf_df.sort_values('日期')

            # 使用收盘价的倒数近似利率走势（价格下跌=收益率上升）
            recent_data = etf_df[['日期', '收盘']].tail(60).copy()
            recent_data.columns = ['date', 'price']
            # 反向转换：价格越高，隐含收益率越低
            base_rate = 2.5  # 假设基准利率
            recent_data['rate'] = base_rate * (100 / recent_data['price'])
            recent_data = recent_data[['date', 'rate']]

            if len(recent_data) >= 20:
                print(f"成功使用511010 ETF数据反推利率，共{len(recent_data)}条记录")
                return recent_data, "511010债券ETF反推"
    except Exception as e:
        print(f"获取511010 ETF数据失败: {e}")

    try:
        # 方法3: 使用SHIBOR利率
        print("尝试获取SHIBOR利率数据...")
        shibor_df = ak.rate_interbank(market="上海银行同业拆借市场", symbol="Shibor人民币", indicator="3月")
        if shibor_df is not None and not shibor_df.empty:
            shibor_df['报告日'] = pd.to_datetime(shibor_df['报告日'])
            shibor_df = shibor_df[shibor_df['报告日'] <= end_date]
            shibor_df = shibor_df.sort_values('报告日')

            recent_data = shibor_df[['报告日', '利率']].tail(60).copy()
            recent_data.columns = ['date', 'rate']
            recent_data['rate'] = pd.to_numeric(recent_data['rate'], errors='coerce')
            recent_data = recent_data.dropna()

            if len(recent_data) >= 20:
                print(f"成功获取SHIBOR数据，共{len(recent_data)}条记录")
                return recent_data, "SHIBOR 3月利率"
    except Exception as e:
        print(f"获取SHIBOR数据失败: {e}")

    # 如果所有方法都失败，使用模拟数据
    print("警告：无法获取真实数据，使用模拟数据")
    dates = pd.date_range(end='2024-11-22', periods=60, freq='D')
    # 模拟利率下行趋势
    rates = 2.8 - np.linspace(0, 0.15, 60) + np.random.normal(0, 0.02, 60)
    recent_data = pd.DataFrame({'date': dates, 'rate': rates})
    return recent_data, "模拟数据"

def calculate_rate_slope(rate_data):
    """
    计算利率的20日线性回归斜率
    Calculate 20-day linear regression slope
    """
    # 取最近20天数据
    recent_20 = rate_data.tail(20).copy()

    # 使用时间序号作为x轴（0, 1, 2, ..., 19）
    x = np.arange(len(recent_20))
    y = recent_20['rate'].values

    # 线性回归
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    print(f"\n利率线性回归分析:")
    print(f"  斜率 (slope): {slope:.6f}")
    print(f"  截距 (intercept): {intercept:.6f}")
    print(f"  R²: {r_value**2:.4f}")

    return slope

def determine_rate_trend(slope):
    """
    判断利率趋势
    Determine interest rate trend
    """
    if slope < -0.002:
        return "下行", "高股息"
    elif slope > 0.002:
        return "上行", "低PB成长"
    else:
        return "中性", "高股息"  # 中性时默认使用高股息策略

def get_chinext_stocks():
    """
    获取创业板股票列表
    Get ChiNext (Growth Enterprise Market) stocks
    """
    try:
        print("\n正在获取创业板股票列表...")
        stock_info = ak.stock_info_a_code_name()
        # 创业板代码以300开头
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        print(f"获取到{len(chinext)}只创业板股票")
        return chinext['code'].tolist()
    except Exception as e:
        print(f"获取创业板股票列表失败: {e}")
        return []

def get_stock_dividend_yield(stock_code):
    """获取股息率"""
    try:
        # 获取股票基本面数据
        stock_data = ak.stock_individual_info_em(symbol=stock_code)
        if stock_data is not None and not stock_data.empty:
            dividend_row = stock_data[stock_data['item'] == '股息率']
            if not dividend_row.empty:
                div_yield = float(dividend_row['value'].values[0].replace('%', ''))
                return div_yield
    except:
        pass
    return None

def get_stock_fundamentals(stock_code):
    """获取股票基本面数据（PB, ROE）"""
    try:
        stock_data = ak.stock_individual_info_em(symbol=stock_code)
        if stock_data is not None and not stock_data.empty:
            pb_row = stock_data[stock_data['item'] == '市净率']
            roe_row = stock_data[stock_data['item'] == '净资产收益率']

            pb = None
            roe = None

            if not pb_row.empty:
                pb_val = pb_row['value'].values[0]
                try:
                    pb = float(pb_val)
                except:
                    pass

            if not roe_row.empty:
                roe_val = roe_row['value'].values[0]
                try:
                    roe = float(str(roe_val).replace('%', ''))
                except:
                    pass

            return pb, roe
    except:
        pass
    return None, None

def get_stock_20d_return(stock_code, end_date='2024-11-22'):
    """获取近20日涨幅"""
    try:
        # 获取历史数据
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date="20241001", end_date="20241122", adjust="qfq")
        if df is not None and not df.empty and len(df) >= 20:
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期')
            recent_20 = df.tail(20)

            start_price = recent_20.iloc[0]['收盘']
            end_price = recent_20.iloc[-1]['收盘']
            return_pct = ((end_price - start_price) / start_price) * 100
            return return_pct
    except:
        pass
    return None

def select_high_dividend_stocks(stock_list, min_dividend=3.0):
    """
    高股息策略：筛选股息率>3%且近20日上涨的股票
    """
    print(f"\n执行高股息策略（股息率>{min_dividend}%，近20日上涨）...")
    selected = []

    for i, stock_code in enumerate(stock_list[:100]):  # 增加搜索范围
        if i % 20 == 0:
            print(f"  处理进度: {i}/{min(100, len(stock_list))}")

        try:
            # 先获取涨跌幅，这样可以快速过滤
            return_20d = get_stock_20d_return(stock_code)
            if return_20d is None or return_20d <= 0:
                continue

            div_yield = get_stock_dividend_yield(stock_code)
            if div_yield is None or div_yield < min_dividend:
                continue

            # 获取ROE用于展示
            _, roe = get_stock_fundamentals(stock_code)
            if roe is None:
                roe = 0

            selected.append({
                'code': stock_code,
                'dividend_yield': div_yield,
                'roe': roe,
                'return_20d': return_20d
            })

            print(f"    找到符合条件的股票: {stock_code}, 股息率: {div_yield:.2f}%, 涨幅: {return_20d:.2f}%")
        except Exception as e:
            continue

    return sorted(selected, key=lambda x: x['dividend_yield'], reverse=True)

def select_low_pb_growth_stocks(stock_list, max_pb=3.0, min_return=10.0, min_roe=15.0):
    """
    低PB成长策略：筛选PB<3，近20日涨幅>10%，ROE>15%的股票
    """
    print(f"\n执行低PB成长策略（PB<{max_pb}，涨幅>{min_return}%，ROE>{min_roe}%）...")
    selected = []

    for i, stock_code in enumerate(stock_list[:100]):  # 增加搜索范围
        if i % 20 == 0:
            print(f"  处理进度: {i}/{min(100, len(stock_list))}")

        try:
            # 先获取涨跌幅，快速过滤
            return_20d = get_stock_20d_return(stock_code)
            if return_20d is None or return_20d < min_return:
                continue

            pb, roe = get_stock_fundamentals(stock_code)
            if pb is None or pb >= max_pb:
                continue
            if roe is None or roe < min_roe:
                continue

            selected.append({
                'code': stock_code,
                'pb': pb,
                'roe': roe,
                'return_20d': return_20d
            })

            print(f"    找到符合条件的股票: {stock_code}, PB: {pb:.2f}, ROE: {roe:.2f}%, 涨幅: {return_20d:.2f}%")
        except Exception as e:
            continue

    return sorted(selected, key=lambda x: x['return_20d'], reverse=True)

def main():
    print("=" * 60)
    print("利率敏感型行业轮动策略分析")
    print("Interest Rate Sensitive Sector Rotation Strategy")
    print("=" * 60)

    # 第一步：获取利率数据并计算斜率
    rate_data, data_source = get_interest_rate_data()
    print(f"\n数据源: {data_source}")
    print(f"数据时间范围: {rate_data['date'].min()} 至 {rate_data['date'].max()}")
    print(f"最新利率: {rate_data['rate'].iloc[-1]:.4f}%")

    slope = calculate_rate_slope(rate_data)

    # 第二步：判断利率趋势并选择策略
    trend, strategy = determine_rate_trend(slope)
    print(f"\n利率趋势判断: {trend}")
    print(f"对应策略: {strategy}")

    # 第三步：获取创业板股票并执行策略
    chinext_stocks = get_chinext_stocks()

    if trend == "下行" or trend == "中性":
        # 高股息策略
        selected_stocks = select_high_dividend_stocks(chinext_stocks)
        result_header = "股票代码,股息率(%),ROE(%),近20日涨幅(%)"
    else:
        # 低PB成长策略
        selected_stocks = select_low_pb_growth_stocks(chinext_stocks)
        result_header = "股票代码,PB,ROE(%),近20日涨幅(%)"

    print(f"\n符合策略的股票数量: {len(selected_stocks)}")

    # 第四步：输出结果
    output_path = "/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_39_interest_rate_sector_rotation/independent/claudecode/rate_strategy.txt"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"当前利率趋势: {trend}\n")
        f.write(f"利率20日斜率: {slope:.6f}\n")
        f.write(f"数据源: {data_source}\n")
        f.write(f"\n策略: {strategy}\n")
        f.write(f"{result_header}\n")

        for stock in selected_stocks[:10]:  # 输出前10只
            if trend == "下行" or trend == "中性":
                f.write(f"{stock['code']},{stock['dividend_yield']:.2f},{stock['roe']:.2f},{stock['return_20d']:.2f}\n")
            else:
                f.write(f"{stock['code']},{stock['pb']:.2f},{stock['roe']:.2f},{stock['return_20d']:.2f}\n")

    print(f"\n结果已保存至: {output_path}")
    print("\n分析完成！")

    return {
        "trend": trend,
        "slope": slope,
        "strategy": strategy,
        "stocks_count": len(selected_stocks),
        "data_source": data_source
    }

if __name__ == "__main__":
    result = main()
