---
id: task_21_morning_star
name: 早晨之星K线形态识别
category: candlestick_pattern
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.45
  llm_judge: 0.55
workspace_files: []
---

## Prompt

在创业板中找出以 2024-03-08 为截止交易日的前30个交易日内出现"早晨之星"形态的股票，条件：
1. **第1天**：大阴线（跌幅>3%，实体占比>70%，实体=|收盘-开盘|，实体占比=实体/振幅）；
2. **第2天**：小K线（涨跌幅绝对值<1.5%）；
3. **第3天**：大阳线（涨幅>3%，实体占比>70%，收盘价高于第1天K线实体中点）；
4. **低位要求**：形态出现时的收盘价低于当时60日均价的90%；
5. **后续验证**：形态出现后的5个交易日内，价格未跌破形态的最低价。

将结果写入 `morning_star.txt`，格式：
```
股票代码,形态起始日期,形态后5日涨幅(%)
300XXX,2024-01-08,12.5
```

## Expected Behavior

Agent应该：
1. 对每只股票获取近90日K线（开盘、收盘、最高、最低）
2. 遍历每3天窗口，检测早晨之星形态
3. 验证低位要求（价格低于60日均价×90%）
4. 验证后续5天不跌破形态最低价
5. 计算形态后5日涨幅

实体中点 = (第1天开盘 + 第1天收盘) / 2（阴线中点）

## Grading Criteria

- [ ] 文件 `morning_star.txt` 已创建
- [ ] 包含代码、日期、涨幅三个字段
- [ ] agent检查了实体占比条件
- [ ] agent验证了第3天收盘价高于第1天实体中点
- [ ] agent检查了低位要求（60日均价90%）

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "morning_star.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "star.txt", "pattern.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["body_ratio_checked"] = 0.0
        scores["midpoint_checked"] = 0.0
        scores["low_position_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
    else:
        has_code = bool(re.search(r'3\d{5}', content))
        has_date = bool(re.search(r'\d{4}-\d{2}-\d{2}', content))
        scores["valid_format"] = 1.0 if (has_code and has_date) else (0.5 if has_code else 0.0)

    transcript_str = str(transcript).lower()
    scores["body_ratio_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["实体", "body", "实体占比", "body.*ratio", "70%", "0.7"]) else 0.0
    scores["midpoint_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["中点", "midpoint", "实体中", "body.*mid", "(open.*close).*0.5"]) else 0.0
    scores["low_position_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["60日", "60.*ma", "均价.*90", "0.9.*ma", "low.*position"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 三根K线形态判断精确性（Weight: 40%）

**Score 1.0**: 三根K线条件均严格实现：阴线大小用实体占比（非涨跌幅）判断，小K线用涨跌幅绝对值，第3天大阳线收盘价与第1天实体中点比较，所有边界条件正确。
**Score 0.75**: 三根K线判断基本正确，实体占比计算略有偏差（如用振幅/价格而非实体/振幅）。
**Score 0.5**: 实现了主要条件但忽略了实体占比（只用涨幅>3%判断大阴/大阳线），第3天与中点比较未实现。
**Score 0.25**: 形态判断方法有根本性错误。
**Score 0.0**: 未实现K线形态判断。

### Criterion 2: 低位要求与后续验证（Weight: 30%）

**Score 1.0**: 60日均价计算正确，形态价格 < 均价×90%的判断准确，后5天不跌破形态最低价（三天中的最低价）的验证逻辑正确。
**Score 0.75**: 低位判断或后续验证其中一个有轻微偏差（如用均线而非均价）。
**Score 0.5**: 仅实现了低位要求或后续验证其中一个。
**Score 0.25**: 两个条件均有错误但有尝试。
**Score 0.0**: 未实现这两个条件。

### Criterion 3: 结果输出准确性（Weight: 30%）

**Score 1.0**: 代码合法，日期为形态第1天的日期，5日涨幅计算准确（形态后第5天相对第3天），数值合理。
**Score 0.75**: 输出基本正确，日期取的是第3天而非第1天，或涨幅计算基准略有偏差。
**Score 0.5**: 有代码和日期但无涨幅，或格式混乱。
**Score 0.25**: 输出存在但内容不可用。
**Score 0.0**: 未创建结果文件。
