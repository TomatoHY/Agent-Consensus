---
id: task_10_macd_histogram_trend
name: MACD柱状图正转后连续增长统计
category: trend_strength
grading_type: automated
timeout_seconds: 360
grading_weights:
  automated: 0.5
  llm_judge: 0.5
workspace_files: []
---

## Prompt

统计创业板中以 2024-12-31 为截止交易日的前60个交易日内，MACD柱状图（histogram = DIFF - DEA）从负转正后连续增长超过5天的股票数量。

要求：
1) histogram从负值变为正值（金叉当日）；
2) 金叉之后连续至少5天histogram持续递增（每天值均大于前一天）；
3) 返回符合条件的股票总数，写入 `macd_strength_count.txt`。

格式：
```
符合条件的股票总数: XXX
```

## Expected Behavior

Agent应该：

1. 获取创业板全部股票列表
2. 对每只股票获取近90个交易日的K线数据（60天分析+30天预热）
3. 计算MACD：EMA12、EMA26，DIFF = EMA12 - EMA26，DEA = 9日EMA(DIFF)，histogram = DIFF - DEA
4. 在60天窗口内搜索histogram从负转正的位置
5. 从该位置起检查连续5天histogram是否递增
6. 统计满足条件的股票数量（注意：一只股票可能有多次，但只计一次）
7. 写入 `macd_strength_count.txt`

## Grading Criteria

- [ ] 文件 `macd_strength_count.txt` 已创建
- [ ] 文件包含数字（正整数）
- [ ] agent在过程中正确计算了MACD的histogram
- [ ] agent检查了连续递增条件（而非仅检查正值）

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "macd_strength_count.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "count.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["has_count"] = 0.0
        scores["histogram_computed"] = 0.0
        scores["consecutive_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text()

    count_match = re.search(r'(\d+)', content)
    if count_match:
        count = int(count_match.group(1))
        scores["has_count"] = 1.0 if count >= 0 else 0.0
    else:
        scores["has_count"] = 0.0

    transcript_str = str(transcript).lower()
    scores["histogram_computed"] = 1.0 if any(kw in transcript_str for kw in
        ["histogram", "柱状图", "diff.*dea", "macd.*bar", "hist"]) else 0.0
    scores["consecutive_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["consecutive", "连续", "递增", "increasing", "monoton"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: MACD柱状图计算准确性（Weight: 35%）

**Score 1.0**: 正确计算MACD三线（EMA12、EMA26、DEA=EMA9(DIFF)），histogram = DIFF - DEA，有足够的预热期（至少26天），使用Wilder平滑或指数平滑均可接受。
**Score 0.75**: MACD计算基本正确，但预热期略短或DEA的平滑参数有小偏差。
**Score 0.5**: histogram计算有错误（如用DIFF代替DIFF-DEA），但尝试了正确思路。
**Score 0.25**: MACD计算存在根本性错误但有尝试。
**Score 0.0**: 未进行MACD计算。

### Criterion 2: 从负转正且连续递增的识别逻辑（Weight: 40%）

**Score 1.0**: 正确检测histogram从负变正的转折点，并从转折点起检查后续5天是否严格递增（每天>前一天），同一只股票多次满足只计一次。
**Score 0.75**: 转折点检测正确，但连续递增检查用了非严格不等式（≥而非>），或未去重。
**Score 0.5**: 仅检测了histogram变正，未验证后续5天连续递增。
**Score 0.25**: 连续递增判断逻辑有明显错误（如只检查5天均值）。
**Score 0.0**: 未实现转折后连续性检测。

### Criterion 3: 遍历覆盖率和计数准确性（Weight: 25%）

**Score 1.0**: 遍历了创业板大部分股票（>80%），计数结果合理（通常在几十到几百之间），统计逻辑无重复计数问题。
**Score 0.75**: 遍历覆盖率>50%，计数基本准确。
**Score 0.5**: 遍历了部分股票（<50%），计数仅供参考。
**Score 0.25**: 遍历了极少股票，结果代表性极差。
**Score 0.0**: 未进行有效遍历。
