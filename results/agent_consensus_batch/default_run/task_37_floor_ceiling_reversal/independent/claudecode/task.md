---
id: task_37_floor_ceiling_reversal
name: 地天板极端反转形态识别
category: extreme_reversal
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.5
  llm_judge: 0.5
workspace_files: []
---

## Prompt

识别创业板中的"地天板"形态（跌停后打开再涨停），条件：

1. **跌停日**：在截至 2024-09-23 的最近20个交易日内出现跌停（创业板跌幅 ≤ -20%，或跌幅 ≤ -10%；以实际涨跌幅判断）且当天跌停被打开（振幅 > 3%，即非一字跌停板）；

2. **涨停日**：跌停当日或次日出现涨停（涨幅 ≥ 20%，或涨幅 ≥ 10%）；

3. **封板强度**：涨停封单量 > 流通股本的1%（若无封单数据，用涨停日尾盘30分钟成交量占全天比例 < 20% 来近似判断强封板）；

4. **强势延续**：涨停后5日内最低价不跌破涨停日最低价；

5. **排除限制**：排除ST股票和次新股（上市不足60个交易日）。

将结果写入 `floor_ceiling.txt`，格式：
```
股票代码,跌停日期,涨停日期,涨停后5日最低回撤(%)
300XXX,2024-01-08,2024-01-09,-2.3
```

## Expected Behavior

Agent应该：
1. 获取近20个交易日的涨跌幅数据
2. 检测跌停（注意创业板有20%的限制而非科创板的更宽限制）
3. 验证跌停被打开（振幅>3%，非一字板）
4. 检测随后的涨停日期
5. 验证强势延续条件
6. 排除ST和次新股

## Grading Criteria

- [ ] 文件 `floor_ceiling.txt` 已创建
- [ ] 包含跌停和涨停两个日期字段
- [ ] 涨停日期在跌停日期之后（当天或次日）
- [ ] agent检查了振幅条件（非一字板）
- [ ] agent排除了ST股票

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re
    from datetime import datetime

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "floor_ceiling.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "reversal.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["two_dates"] = 0.0
        scores["date_order"] = 0.0
        scores["amplitude_checked"] = 0.0
        scores["st_excluded"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["two_dates"] = 1.0
        scores["date_order"] = 1.0
    else:
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', content)
        scores["two_dates"] = 1.0 if len(dates) >= 2 else (0.5 if len(dates) >= 1 else 0.0)

        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        valid_order = True
        for line in lines:
            ds = re.findall(r'\d{4}-\d{2}-\d{2}', line)
            if len(ds) >= 2:
                try:
                    d1 = datetime.strptime(ds[0], "%Y-%m-%d")
                    d2 = datetime.strptime(ds[1], "%Y-%m-%d")
                    if d2 < d1:
                        valid_order = False
                except:
                    pass
        scores["date_order"] = 1.0 if valid_order else 0.0

    transcript_str = str(transcript).lower()
    scores["amplitude_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["振幅", "amplitude", "一字板", "3%", "high.*low"]) else 0.0
    scores["st_excluded"] = 1.0 if "st" in transcript_str else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 跌停/涨停识别准确性（Weight: 35%）

**Score 1.0**: 正确识别创业板的跌停/涨停幅度（10%或20%，需考虑注册制下的差异），跌停打开的振幅判断正确（>3%），涨停日在跌停后的时间范围（当天或次日）检测准确。
**Score 0.75**: 涨跌停识别基本正确，但对创业板的限制幅度（注册制股票±20%）处理有轻微偏差。
**Score 0.5**: 涨跌停识别正确但未验证跌停是否被打开（一字板判断缺失）。
**Score 0.25**: 涨跌停识别有根本性错误。
**Score 0.0**: 未实现涨跌停识别。

### Criterion 2: 封板强度与强势延续验证（Weight: 35%）

**Score 1.0**: 封板强度验证实现（封单量/流通股本>1%，或合理的尾盘成交量代理），涨停后5日最低价不跌破涨停日最低价的条件正确实现，两个条件均有处理。
**Score 0.75**: 强势延续验证正确，封板强度用了合理近似但未说明局限性。
**Score 0.5**: 只实现了其中一个条件的验证。
**Score 0.25**: 两个条件均有尝试但实现有明显错误。
**Score 0.0**: 未实现强度和延续验证。

### Criterion 3: 排除条件与结果质量（Weight: 30%）

**Score 1.0**: 正确排除了ST（名称含ST的股票）和次新股（上市不足60个交易日），涨停后回撤计算准确，输出格式规范。
**Score 0.75**: 排除了ST但次新股判断有偏差（如用30天替代60天），回撤计算基本正确。
**Score 0.5**: 只排除了ST，次新股未排除，其他输出正确。
**Score 0.25**: 排除条件基本缺失。
**Score 0.0**: 未创建结果文件。
