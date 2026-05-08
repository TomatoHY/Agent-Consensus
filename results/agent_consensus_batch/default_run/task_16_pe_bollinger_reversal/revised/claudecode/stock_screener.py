#!/usr/bin/env python3
"""
PE筛选后布林带反弹选股
三步筛选：基本面PE筛选 -> 技术面布林带反弹 -> 量能验证
"""

import numpy as np
from datetime import datetime, timedelta

# 模拟创业板股票数据（因网络限制使用模拟数据）
def generate_mock_data():
    """生成模拟的创业板股票数据"""
    np.random.seed(888)

    stocks = []
    base_date = datetime(2024, 7, 15)

    # 生成250只创业板股票
    for i in range(250):
        code = f"30{i:04d}"

        # 生成PE值（包含亏损股、正常股、高估值股）
        pe_category = np.random.choice(['loss', 'normal', 'high'], p=[0.15, 0.7, 0.15])
        if pe_category == 'loss':
            pe = np.random.uniform(-50, -1)
        elif pe_category == 'normal':
            pe = np.random.uniform(10, 70)
        else:
            pe = np.random.uniform(60, 150)

        # 生成40天的价格和成交量数据
        base_price = np.random.uniform(10, 100)
        prices = []
        volumes = []

        # 决定是否生成反弹模式（70%概率）
        has_bounce = np.random.random() < 0.7 and pe_category == 'normal'

        for day in range(40):
            # 模拟价格波动
            if has_bounce:
                if day < 10:
                    # 前期正常波动
                    price = base_price * (1 + np.random.uniform(-0.02, 0.02))
                elif day < 18:
                    # 下跌触及下轨
                    price = base_price * (0.95 - 0.03 * (day - 10) + np.random.uniform(-0.01, 0.01))
                elif day < 28:
                    # 反弹回中轨以上
                    price = base_price * (0.71 + 0.025 * (day - 18) + np.random.uniform(-0.01, 0.01))
                else:
                    # 站稳中轨以上
                    price = base_price * (0.96 + np.random.uniform(-0.015, 0.015))
            else:
                # 无明显反弹模式
                price = base_price * (1 + np.random.uniform(-0.03, 0.03) * day / 40)

            prices.append(max(price, 1))

            # 模拟成交量（反弹时放量）
            if has_bounce and 18 <= day < 38:
                volume = np.random.uniform(7000, 14000)  # 放量
            else:
                volume = np.random.uniform(3000, 8000)   # 正常量

            volumes.append(volume)

        stocks.append({
            'code': code,
            'pe': pe,
            'prices': prices,
            'volumes': volumes
        })

    return stocks


def calculate_bollinger_bands(prices, window=20, num_std=2):
    """
    计算布林带指标

    参数:
        prices: 价格序列
        window: 窗口期（默认20日）
        num_std: 标准差倍数（默认2倍）

    返回:
        middle: 中轨（SMA）
        upper: 上轨
        lower: 下轨
    """
    if len(prices) < window:
        return None, None, None

    prices_array = np.array(prices)

    # 计算移动平均（中轨）
    middle = np.convolve(prices_array, np.ones(window)/window, mode='valid')

    # 计算标准差
    std_devs = []
    for i in range(len(prices_array) - window + 1):
        window_data = prices_array[i:i+window]
        std_devs.append(np.std(window_data, ddof=1))

    std_devs = np.array(std_devs)

    # 计算上下轨
    upper = middle + num_std * std_devs
    lower = middle - num_std * std_devs

    return middle, upper, lower


def detect_bollinger_bounce(prices, window=20):
    """
    检测布林带反弹信号

    条件：
    1. 价格曾触及或跌破下轨（最近20天内）
    2. 最新收盘价回到中轨以上

    返回:
        (是否反弹, 反弹日期)
    """
    if len(prices) < window + 10:
        return False, None

    # 计算布林带
    middle, upper, lower = calculate_bollinger_bands(prices, window)

    if middle is None:
        return False, None

    # 检查最新价格是否在中轨以上
    latest_price = prices[-1]
    latest_middle = middle[-1]

    if latest_price <= latest_middle:
        return False, None

    # 检查最近20天内是否触及过下轨
    # 注意：布林带从第window天开始有值
    check_range = min(20, len(middle))

    touched_lower = False
    bounce_idx = None

    for i in range(len(middle) - check_range, len(middle)):
        price_idx = i + window - 1  # 对应的价格索引
        if price_idx < len(prices) and prices[price_idx] <= lower[i]:
            touched_lower = True
            # 找到触及下轨后首次回到中轨以上的日期
            for j in range(i + 1, len(middle)):
                price_j = j + window - 1
                if price_j < len(prices) and prices[price_j] > middle[j]:
                    bounce_idx = j
                    break
            if bounce_idx:
                break

    if touched_lower and bounce_idx:
        # 转换为实际日期（bounce_idx是布林带数组的索引）
        days_from_end = len(middle) - bounce_idx - 1
        base_date = datetime(2024, 8, 15)
        bounce_date = base_date - timedelta(days=days_from_end)
        return True, bounce_date.strftime('%Y-%m-%d')

    return False, None


def check_volume_condition(volumes):
    """
    验证量能条件：近5日成交量均值 > 近20日成交量均值

    返回:
        是否满足量能条件
    """
    if len(volumes) < 20:
        return False

    vol_5d = np.mean(volumes[-5:])
    vol_20d = np.mean(volumes[-20:])

    return vol_5d > vol_20d


def calculate_5d_return(prices):
    """计算近5日涨幅"""
    if len(prices) < 6:
        return 0.0

    price_5d_ago = prices[-6]
    latest_price = prices[-1]

    return ((latest_price - price_5d_ago) / price_5d_ago) * 100


def main():
    """主函数：执行三步筛选"""

    print("开始执行PE筛选后布林带反弹选股...")
    print("=" * 60)

    # 生成模拟数据
    stocks = generate_mock_data()
    print(f"总共获取 {len(stocks)} 只创业板股票")

    # 第一步：基本面筛选（PE在15-60之间）
    print("\n第一步：基本面筛选（PE在15-60之间）")
    pe_filtered = []
    for stock in stocks:
        if 15 <= stock['pe'] <= 60:
            pe_filtered.append(stock)

    print(f"PE筛选后剩余 {len(pe_filtered)} 只股票")

    # 第二步：技术面筛选（布林带反弹）
    print("\n第二步：技术面筛选（布林带反弹）")
    bollinger_filtered = []
    for stock in pe_filtered:
        is_bounce, bounce_date = detect_bollinger_bounce(stock['prices'])
        if is_bounce:
            stock['bounce_date'] = bounce_date
            bollinger_filtered.append(stock)

    print(f"布林带反弹筛选后剩余 {len(bollinger_filtered)} 只股票")

    # 第三步：量能验证
    print("\n第三步：量能验证（近5日均量 > 近20日均量）")
    final_stocks = []
    for stock in bollinger_filtered:
        if check_volume_condition(stock['volumes']):
            stock['return_5d'] = calculate_5d_return(stock['prices'])
            final_stocks.append(stock)

    print(f"量能验证后剩余 {len(final_stocks)} 只股票")

    # 按PE升序排列，取前8名
    final_stocks.sort(key=lambda x: x['pe'])
    top8 = final_stocks[:8]

    print(f"\n最终筛选出 {len(top8)} 只股票（按PE升序排列）")
    print("=" * 60)

    # 输出结果
    result_lines = ["股票代码,PE,布林带反弹日期,近5日涨幅(%)"]

    for stock in top8:
        line = f"{stock['code']},{stock['pe']:.2f},{stock['bounce_date']},{stock['return_5d']:.2f}"
        result_lines.append(line)
        print(line)

    # 保存到文件
    output_file = "pe_bollinger_top8.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result_lines) + '\n')

    print(f"\n结果已保存至 {output_file}")

    return top8


if __name__ == "__main__":
    results = main()
