---
id: task_01_macd_rsi_filter
name: 多指标共振选股（创业板）
category: technical_filter
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.5
  llm_judge: 0.5
workspace_files: []
---

## Prompt

固定时间基准：分析截止日统一设为 2026-03-31；若题目涉及 5 / 10 / 15 / 20 / 30 / 60 / 252 个交易日、4 周或 2 个月窗口，均按该截止日向前回看对应长度，停牌样本按可得交易日顺延补足。

在创业板（300开头）中，找出 2026-03-04 至 2026-03-31 这 20 个交易日窗口内同时满足以下条件的股票代码：
1) 出现过MACD金叉（DIFF上穿DEA）；
2) RSI从超卖区（<30）反弹到50以上；
3) 成交量至少有2天超过5日均量的2倍；
4) 5日均线上穿8日均线。

请将符合条件的股票代码列表写入文件 `result.txt`（每行一个股票代码，如果超过10只，返回前10只）。

## Expected Behavior

Agent应该：

1. 获取创业板全部股票列表（300开头的股票）
2. 对每只股票拉取 2026-03-04 至 2026-03-31 的K线数据（至少包含收盘价、成交量）
3. 计算MACD（EMA12, EMA26, DEA9）并检测金叉
4. 计算 RSI（14日），并检测"从 RSI < 30 到首次 RSI > 50"的反弹信号：当某只股票的 RSI14 跌破 30 后，标记该时刻为周期起点；从该起点开始，当 RSI14 首次由 ≤ 50 严格上穿至 > 50 时，记录为有效信号；如果在上穿 50 之前再次跌破 30，则重置周期起点；信号触发后，只有再次跌破 30 才能开启新周期。
5. 计算5日均量，统计成交量超过均量2倍的天数
6. 计算5日和8日均线，检测上穿
7. 筛选创业板中在同一交易日同时满足以下三个条件的股票：RSI14在跌破30后对应恢复周期内首次上穿50，当前成交量大于前5日平均成交量的2倍（不含当天），且5日均线上穿8日均线。
8. 将结果写入 `result.txt`，每行一个代码，最多10只

## Grading Criteria

- [ ] 文件 `result.txt` 已创建
- [ ] 文件内容为合法的创业板股票代码格式（300开头的6位数字）
- [ ] 代码数量不超过10个
- [ ] agent在执行过程中正确调用了数据获取工具
- [ ] agent在执行过程中计算了MACD指标
- [ ] agent在执行过程中计算了RSI指标
- [ ] agent在执行过程中计算了均线指标

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "result.txt"
    if not result_file.exists():
        for alt in ["results.txt", "output.txt", "stocks.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_codes"] = 0.0
        scores["count_limit"] = 0.0
        scores["data_fetched"] = 0.0
        scores["macd_computed"] = 0.0
        scores["rsi_computed"] = 0.0
        scores["ma_computed"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()
    lines = [l.strip() for l in content.splitlines() if l.strip()]

    # Check valid GEM codes (6-digit starting with 300)
    valid_codes = [l for l in lines if re.match(r'^3\d{5}$', l)]
    scores["valid_codes"] = 1.0 if len(valid_codes) > 0 else 0.0

    # Check count limit <= 10
    scores["count_limit"] = 1.0 if len(lines) <= 10 else 0.5

    # Check transcript for data fetching, MACD, RSI, MA
    transcript_str = str(transcript).lower()
    scores["data_fetched"] = 1.0 if any(kw in transcript_str for kw in ["kline", "k线", "get_kline", "history", "candle", "ohlcv"]) else 0.0
    scores["macd_computed"] = 1.0 if "macd" in transcript_str else 0.0
    scores["rsi_computed"] = 1.0 if "rsi" in transcript_str else 0.0
    scores["ma_computed"] = 1.0 if any(kw in transcript_str for kw in ["ma5", "ma20", "均线", "moving_average", "sma", "ema"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 数据获取与遍历完整性（Weight: 30%）

**Score 1.0**: Agent正确遍历了创业板全部或大量股票，每只股票获取了足够长度（≥20日）的K线数据，无明显遗漏。
**Score 0.75**: Agent遍历了大部分股票，但有少量股票未覆盖或数据获取有轻微错误。
**Score 0.5**: Agent仅遍历了部分股票（如抽样），或数据长度不足，可能导致结果不准确。
**Score 0.25**: Agent尝试了数据获取但存在明显错误，仅处理了极少数股票。
**Score 0.0**: Agent未尝试获取股票数据，或完全没有遍历行为。

### Criterion 2: 指标计算正确性（Weight: 40%）

**Score 1.0**: MACD（EMA12/26/DEA9）、RSI（14日）、均量、均线均按照标准公式正确计算，金叉/超卖/均线交叉的判断逻辑准确。
**Score 0.75**: 大部分指标计算正确，存在1-2个小错误（如RSI窗口用了错误天数）。
**Score 0.5**: 计算了部分指标，但有明显公式错误或条件判断有误。
**Score 0.25**: 指标计算存在多处重大错误，结果可信度低。
**Score 0.0**: 未进行任何指标计算，或完全用错误方法替代。

### Criterion 3: 结果格式与完整性（Weight: 30%）

**Score 1.0**: `result.txt` 格式规范，每行一个6位股票代码，数量≤10，内容符合创业板代码规则。
**Score 0.75**: 文件存在且有内容，但格式略有瑕疵（如多余空行、带名称等）。
**Score 0.5**: 文件存在但格式混乱，需要额外解析才能提取代码。
**Score 0.25**: 文件存在但内容不可用（空文件或乱码）。
**Score 0.0**: 未创建结果文件。
