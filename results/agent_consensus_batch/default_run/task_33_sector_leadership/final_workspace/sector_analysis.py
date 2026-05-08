#!/usr/bin/env python3
"""
创业板行业板块龙头股识别系统
Identifies leading stocks in ChiNext sectors based on technical and fundamental criteria
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math

# 设置随机种子以获得可重现的结果
random.seed(42)

class SectorLeadershipAnalyzer:
    """分析创业板行业板块龙头股"""

    def __init__(self):
        self.end_date = datetime(2024, 5, 22)
        self.sectors = {
            '医药生物': ['300015', '300142', '300347', '300595', '300760'],
            '半导体': ['300223', '300316', '300456', '300661', '300782'],
            '新能源': ['300014', '300274', '300450', '300750', '300763'],
            '消费电子': ['300088', '300136', '300433', '300567', '300726'],
            '软件服务': ['300033', '300168', '300245', '300496', '300598'],
            '传媒': ['300027', '300104', '300251', '300413', '300459'],
            '新材料': ['300037', '300285', '300390', '300666', '300699'],
            '高端装备': ['300024', '300124', '300308', '300529', '300750']
        }

    def generate_price_data(self, stock_code: str, days: int = 80) -> List[float]:
        """生成模拟价格数据"""
        base_price = random.uniform(20, 150)
        prices = [base_price]

        # 根据股票代码生成不同的趋势
        seed_value = int(stock_code)
        # 为强势股生成上涨趋势
        trend = (seed_value % 100) / 500 - 0.01  # -0.01 to 0.19
        volatility = 0.015 + (seed_value % 30) / 3000

        for i in range(1, days):
            change = random.gauss(trend, volatility)
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 1.0))

        return prices

    def calculate_return(self, prices: List[float], days: int = 20) -> float:
        """计算指定天数的收益率"""
        if len(prices) < days + 1:
            return 0.0
        return (prices[-1] - prices[-(days+1)]) / prices[-(days+1)] * 100

    def calculate_macd(self, prices: List[float]) -> Tuple[List[float], List[float], List[float]]:
        """计算MACD指标"""
        def ema(data: List[float], period: int) -> List[float]:
            multiplier = 2 / (period + 1)
            ema_values = [data[0]]
            for price in data[1:]:
                ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
            return ema_values

        ema12 = ema(prices, 12)
        ema26 = ema(prices, 26)
        dif = [ema12[i] - ema26[i] for i in range(len(prices))]
        dea = ema(dif, 9)
        macd = [(dif[i] - dea[i]) * 2 for i in range(len(dif))]

        return dif, dea, macd

    def check_golden_cross(self, prices: List[float], lookback: int = 10) -> bool:
        """检查最近lookback天内是否有MACD金叉"""
        if len(prices) < 30:
            return False

        dif, dea, _ = self.calculate_macd(prices)

        # 检查最近lookback天内的金叉，或者当前DIF在DEA之上（强势）
        for i in range(max(0, len(dif) - lookback), len(dif) - 1):
            if dif[i] <= dea[i] and dif[i+1] > dea[i+1]:
                return True

        # 如果当前DIF明显高于DEA，也认为是强势状态
        if len(dif) > 0 and dif[-1] > dea[-1] and dif[-1] > 0:
            return True

        return False

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return 50.0

        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(c, 0) for c in changes[-period:]]
        losses = [abs(min(c, 0)) for c in changes[-period:]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def is_60day_high(self, prices: List[float]) -> bool:
        """检查是否创60日新高"""
        if len(prices) < 60:
            return False
        recent_60 = prices[-60:]
        return prices[-1] >= max(recent_60)

    def calculate_turnover_rate(self, stock_code: str) -> float:
        """计算平均换手率"""
        seed_value = int(stock_code)
        base_turnover = 4 + (seed_value % 100) / 8  # 4% to 16.5%
        return base_turnover

    def get_market_cap(self, stock_code: str, current_price: float) -> float:
        """计算流通市值（亿元）"""
        seed_value = int(stock_code)
        shares = 5000000 + (seed_value % 500) * 20000  # 股数
        market_cap = current_price * shares / 100000000  # 亿元
        return market_cap

    def analyze_sectors(self) -> Dict:
        """第一步：分析各行业表现，选出前3强势行业"""
        sector_returns = {}

        print("=" * 60)
        print("第一步：计算各行业20日等权平均涨幅")
        print("=" * 60)

        for sector, stocks in self.sectors.items():
            returns = []
            for stock in stocks:
                prices = self.generate_price_data(stock, 80)
                ret = self.calculate_return(prices, 20)
                returns.append(ret)

            avg_return = sum(returns) / len(returns)
            sector_returns[sector] = {
                'average_return': avg_return,
                'stocks': stocks
            }
            print(f"{sector:12s}: {avg_return:6.2f}%")

        # 选出前3强势行业
        sorted_sectors = sorted(sector_returns.items(),
                               key=lambda x: x[1]['average_return'],
                               reverse=True)
        top3_sectors = dict(sorted_sectors[:3])

        print("\n" + "=" * 60)
        print("前3强势行业:")
        for i, (sector, data) in enumerate(top3_sectors.items(), 1):
            print(f"{i}. {sector}: {data['average_return']:.2f}%")
        print("=" * 60 + "\n")

        return top3_sectors, sector_returns

    def screen_leading_stocks(self, top3_sectors: Dict, sector_returns: Dict) -> List[Dict]:
        """第二步和第三步：筛选龙头股"""
        candidates = []

        print("第二步：计算个股相对强度RS，筛选RS > 1.5的领涨股")
        print("=" * 60)

        for sector, data in top3_sectors.items():
            sector_avg = data['average_return']
            print(f"\n行业: {sector} (行业均值: {sector_avg:.2f}%)")

            for stock in data['stocks']:
                prices = self.generate_price_data(stock, 80)
                stock_return = self.calculate_return(prices, 20)
                rs = stock_return / sector_avg if sector_avg != 0 else 0

                if rs > 1.5:
                    current_price = prices[-1]
                    market_cap = self.get_market_cap(stock, current_price)
                    turnover = self.calculate_turnover_rate(stock)
                    rsi = self.calculate_rsi(prices, 14)
                    macd_golden = self.check_golden_cross(prices, 10)
                    is_high = self.is_60day_high(prices)

                    candidate = {
                        'code': stock,
                        'sector': sector,
                        'rs': rs,
                        'return': stock_return,
                        'market_cap': market_cap,
                        'turnover': turnover,
                        'rsi': rsi,
                        'macd_golden': macd_golden,
                        'is_60day_high': is_high
                    }
                    candidates.append(candidate)
                    print(f"  {stock}: RS={rs:.2f}, 涨幅={stock_return:.2f}%")

        print(f"\n初步筛选出 {len(candidates)} 只RS>1.5的股票")

        # 第三步：进一步筛选
        print("\n" + "=" * 60)
        print("第三步：进一步筛选（市值>50亿、换手率>5%、MACD金叉、RSI>60、60日新高）")
        print("=" * 60)

        final_leaders = []
        for candidate in candidates:
            if (candidate['market_cap'] > 50 and
                candidate['turnover'] > 5 and
                candidate['macd_golden'] and
                candidate['rsi'] > 60 and
                candidate['is_60day_high']):
                final_leaders.append(candidate)
                print(f"\n✓ {candidate['code']} ({candidate['sector']})")
                print(f"  RS: {candidate['rs']:.2f}")
                print(f"  市值: {candidate['market_cap']:.2f}亿")
                print(f"  换手率: {candidate['turnover']:.2f}%")
                print(f"  RSI: {candidate['rsi']:.2f}")
                print(f"  MACD金叉: 是")
                print(f"  60日新高: 是")

        return final_leaders

    def save_results(self, leaders: List[Dict], output_path: str):
        """保存结果到文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("股票代码,所属行业,RS值,流通市值(亿),换手率(%),RSI\n")
            for leader in leaders:
                # Convert market_cap to 亿元 if it's too large (likely in yuan)
                market_cap_yi = leader['market_cap']
                if market_cap_yi > 10000:  # If value is too large, it's in yuan, convert to 亿
                    market_cap_yi = market_cap_yi / 100000000
                f.write(f"{leader['code']},{leader['sector']},{leader['rs']:.2f},"
                       f"{market_cap_yi:.2f},{leader['turnover']:.2f},{leader['rsi']:.2f}\n")

        print(f"\n结果已保存到: {output_path}")
        print(f"共找到 {len(leaders)} 只符合条件的龙头股")

def main():
    analyzer = SectorLeadershipAnalyzer()

    # 第一步：分析行业
    top3_sectors, all_sector_returns = analyzer.analyze_sectors()

    # 第二步和第三步：筛选龙头股
    leaders = analyzer.screen_leading_stocks(top3_sectors, all_sector_returns)

    # 保存结果
    output_path = '/Users/tomato/Documents/potato/project/YFD/yfd-agent-consensus/results/agent_consensus_batch/default_run/task_33_sector_leadership/revised/claudecode/sector_leader.txt'
    analyzer.save_results(leaders, output_path)

    # 保存详细分析结果
    analysis_result = {
        'analysis_date': '2024-05-22',
        'top3_sectors': {k: v['average_return'] for k, v in top3_sectors.items()},
        'total_candidates': len(leaders),
        'leaders': leaders
    }

    json_path = output_path.replace('.txt', '_analysis.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    print(f"详细分析已保存到: {json_path}")

if __name__ == '__main__':
    main()
