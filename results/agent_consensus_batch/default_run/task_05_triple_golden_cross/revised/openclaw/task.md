---
id: task_05_triple_golden_cross
name: 三金叉共振信号检测
category: complex_signal
grading_type: hybrid
timeout_seconds: 360
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

在创业板中找出以 2024-07-31 为截止交易日的前20个交易日内出现"三金叉共振"的股票：
1) MACD金叉（DIFF上穿DEA）；
2) KDJ金叉（K上穿D）；
3) 5日均线上穿10日均线。

要求这三个金叉在5个交易日内先后出现（不要求同一天）。

将结果写入 `triple_cross.txt`，格式：
```
股票代码,MACD金叉日期,KDJ金叉日期,MA金叉日期
300XXX,2024-01-10,2024-01-11,2024-01-12
```

## Expected Behavior

Agent应该：

1. 获取创业板股票列表并遍历
2. 对每只股票获取足够长度的K线数据（建议60日以上用于指标预热）
3. 计算MACD（EMA12/26，信号线EMA9），检测DIFF上穿DEA的日期
4. 计算KDJ（K=9日随机指标，D=K的3日SMA），检测K上穿D的日期
5. 计算5日和10日均线，检测5日上穿10日的日期
6. 判断三次金叉是否在同一个5日窗口内发生
7. 记录每个金叉的具体日期并输出结果

## Grading Criteria

- [ ] 文件 `triple_cross.txt` 已创建
- [ ] 文件格式正确（代码+三个日期）
- [ ] 股票代码为合法创业板代码
- [ ] 日期格式规范（YYYY-MM-DD或类似）
- [ ] 三个日期在5个交易日内（日期差合理）
- [ ] agent计算了KDJ指标

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re
    from datetime import datetime

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "triple_cross.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "cross.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["valid_codes"] = 0.0
        scores["valid_dates"] = 0.0
        scores["kdj_computed"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "no stock", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        # If agent correctly reports no results, give partial credit
        scores["valid_format"] = 1.0
        scores["valid_codes"] = 1.0
        scores["valid_dates"] = 0.5
        transcript_str = str(transcript).lower()
        scores["kdj_computed"] = 1.0 if "kdj" in transcript_str else 0.0
        return scores

    lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#") and "代码" not in l]
    records = []
    for line in lines:
        parts = re.split(r'[,\s\t]+', line)
        if len(parts) >= 4:
            records.append(parts)

    scores["valid_format"] = 1.0 if len(records) > 0 else 0.0

    valid_codes = [r for r in records if re.match(r'^3\d{5}$', r[0])]
    scores["valid_codes"] = 1.0 if len(valid_codes) > 0 else 0.0

    # Check date format and proximity
    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
    valid_date_records = 0
    for r in records:
        dates = [date_pattern.search(d) for d in r[1:4]]
        if all(dates):
            try:
                d_list = [datetime.strptime(d.group(), "%Y-%m-%d") for d in dates]
                max_diff = max((d_list[i] - d_list[j]).days for i in range(3) for j in range(3))
                if abs(max_diff) <= 10:  # 5 trading days ≈ 7-8 calendar days
                    valid_date_records += 1
            except:
                pass
    scores["valid_dates"] = 1.0 if valid_date_records > 0 else (0.5 if len(records) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    scores["kdj_computed"] = 1.0 if "kdj" in transcript_str else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 指标计算准确性（Weight: 35%）

**Score 1.0**: MACD、KDJ、均线均按标准公式计算，金叉检测逻辑正确（上穿判断用前后两日比较），三个指标计算参数符合常规（MACD用12/26/9，KDJ用9/3/3）。
**Score 0.75**: 主要指标计算正确，但参数或公式有1-2处细微偏差。
**Score 0.5**: 计算了2-3个指标，但有明显公式错误或简化了某个指标。
**Score 0.25**: 仅计算了1个指标，或整体计算方法存在根本性错误。
**Score 0.0**: 未进行任何指标计算。

### Criterion 2: 时间窗口判断逻辑（Weight: 30%）

**Score 1.0**: 正确实现了"三个金叉在5个交易日内发生"的窗口检测，使用滑动窗口或日期差判断，逻辑严密。
**Score 0.75**: 时间窗口判断基本正确，但用日历日替代交易日，或边界处理略有问题。
**Score 0.5**: 时间窗口判断逻辑有明显缺陷，如固定检查最后5天而非动态窗口。
**Score 0.25**: 未实现时间窗口判断，仅检查了金叉是否存在。
**Score 0.0**: 完全未考虑时间窗口约束。

### Criterion 3: 结果输出质量（Weight: 35%）

**Score 1.0**: 结果文件格式规范，包含股票代码和三个金叉的具体日期，日期在合理范围（最近20个交易日），无错误代码。
**Score 0.75**: 结果包含股票代码，日期部分有格式瑕疵或缺失某个金叉日期。
**Score 0.5**: 结果有内容但格式较乱，需人工解析。
**Score 0.25**: 结果文件存在但实质内容缺失或不可用。
**Score 0.0**: 未创建结果文件。
