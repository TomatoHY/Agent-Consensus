---
id: task_29_momentum_reversal_combo
name: 动量反转组合因子选股
category: multi_factor_momentum_reversal
grading_type: hybrid
timeout_seconds: 360
grading_weights:
  automated: 0.45
  llm_judge: 0.55
workspace_files: []
---

## Prompt

构建动量-反转组合因子选股：

**筛选条件**（AND关系）：
1. 20日动量 > 15%（截至 2024-11-08 的近20日累计收益率，代表中期强势）；
2. 5日短期反转 < -3%（截至 2024-11-08 的近5日收益率为负，代表短期回调）；
3. RSI（14日）在30-50之间（超卖边缘，未过度超卖）；
4. MACD仍在0轴上方（DIFF > 0，代表趋势未坏）；
5. 60日均线向上（近10日的60日均线值单调递增）。

按20日动量从高到低排序，取前10只，写入 `momentum_reversal.txt`，格式：
```
股票代码,20日动量(%),5日反转(%),RSI,MACD_DIFF,60日均线斜率
300XXX,22.5,-4.2,42.3,0.15,0.08
```

## Expected Behavior

Agent应该：
1. 计算全市场20日累计收益率，初筛动量>15%的股票
2. 对初筛股票计算5日收益率，进一步筛选5日<-3%
3. 计算14日RSI，筛选30-50区间
4. 计算MACD，检查DIFF>0
5. 计算60日均线斜率（近10日60日均线序列是否单调递增）
6. 综合所有条件，排序后取前10

## Grading Criteria

- [ ] 文件 `momentum_reversal.txt` 已创建
- [ ] 最多10条记录
- [ ] 20日动量值 > 15%
- [ ] 5日反转值 < -3%（负值）
- [ ] RSI值在30-50之间
- [ ] agent计算了MACD的DIFF线
- [ ] 结果按20日动量降序排列

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "momentum_reversal.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "momentum.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["count_limit"] = 0.0
        scores["momentum_valid"] = 0.0
        scores["reversal_negative"] = 0.0
        scores["rsi_range"] = 0.0
        scores["macd_diff_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["count_limit"] = 1.0
        scores["momentum_valid"] = 1.0
        scores["reversal_negative"] = 1.0
        scores["rsi_range"] = 1.0
        transcript_str = str(transcript).lower()
        scores["macd_diff_checked"] = 1.0 if "diff" in transcript_str or "macd" in transcript_str else 0.0
        return scores

    lines = [l.strip() for l in content.splitlines()
             if l.strip() and not l.startswith("#") and "代码" not in l]

    scores["count_limit"] = 1.0 if len(lines) <= 10 else 0.5

    records = []
    for line in lines:
        parts = re.split(r'[,\s\t]+', line)
        if len(parts) >= 6:
            try:
                momentum = float(parts[1].replace('%', ''))
                reversal = float(parts[2].replace('%', ''))
                rsi = float(parts[3])
                records.append((momentum, reversal, rsi))
            except:
                pass

    valid_mom = [r for r in records if r[0] > 15]
    scores["momentum_valid"] = 1.0 if len(valid_mom) == len(records) and len(records) > 0 else (0.5 if len(valid_mom) > 0 else 0.0)

    valid_rev = [r for r in records if r[1] < -3]
    scores["reversal_negative"] = 1.0 if len(valid_rev) == len(records) and len(records) > 0 else (0.5 if len(valid_rev) > 0 else 0.0)

    valid_rsi = [r for r in records if 30 <= r[2] <= 50]
    scores["rsi_range"] = 1.0 if len(valid_rsi) == len(records) and len(records) > 0 else (0.5 if len(valid_rsi) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    scores["macd_diff_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["diff", "macd.*line", "macd.*0", "diff.*>.*0"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 五个筛选条件的准确实现（Weight: 40%）

**Score 1.0**: 五个条件全部严格实现：20日累计收益率>15%、5日累计收益率<-3%、RSI14在30-50、MACD DIFF>0（非histogram>0）、60日均线近10日单调递增，AND关系正确。
**Score 0.75**: 实现了4个条件，1个有小偏差（如误用MACD histogram而非DIFF判断0轴）。
**Score 0.5**: 实现了3个主要条件，缺少2个次要条件。
**Score 0.25**: 仅实现了1-2个条件。
**Score 0.0**: 未实现多因子筛选。

### Criterion 2: 因子计算技术准确性（Weight: 30%）

**Score 1.0**: 动量用累计收益率（非日收益率均值），RSI用14日Wilder法，MACD DIFF = EMA12 - EMA26，60日均线斜率用序列单调性判断，所有计算有足够预热期。
**Score 0.75**: 主要因子计算正确，1-2个因子有轻微偏差（如动量用期末日收益率代替累计）。
**Score 0.5**: 2-3个因子有明显计算错误，但整体思路正确。
**Score 0.25**: 多数因子计算有根本性错误。
**Score 0.0**: 未进行有效的因子计算。

### Criterion 3: 排序与结果输出（Weight: 30%）

**Score 1.0**: 按20日动量降序正确排列，输出包含6个字段（代码、动量、反转、RSI、DIFF、均线斜率），数值合理，最多10条。
**Score 0.75**: 排序正确，缺少1-2个字段或均线斜率精度不足。
**Score 0.5**: 有结果但排序方向错误，或字段缺失较多。
**Score 0.25**: 只有代码，无具体数值。
**Score 0.0**: 未创建结果文件。
