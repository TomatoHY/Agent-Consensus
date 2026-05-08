---
id: task_08_rsi_overbought_duration
name: RSI超买持续时间分析
category: duration_analysis
grading_type: automated
timeout_seconds: 240
workspace_files: []
---

## Prompt

计算创业板中以 2024-10-31 为截止交易日的前20个交易日内，RSI指标在超买区（>70）停留时间最长的3只股票。

将结果写入 `rsi_overbought_top3.txt`，格式（按天数从多到少排序）：
```
股票代码,超买天数
300XXX,X
300XXX,X
300XXX,X
```

## Expected Behavior

Agent应该：

1. 获取创业板全部股票列表
2. 对每只股票获取近34个交易日的收盘价（RSI14需要14日预热）
3. 计算14日RSI指标
4. 统计最近20个交易日内，RSI > 70 的天数
5. 对所有股票按超买天数降序排序
6. 取前3名，写入 `rsi_overbought_top3.txt`

RSI计算公式（Wilder平滑法）：
- RS = 平均上涨幅度 / 平均下跌幅度（14日）
- RSI = 100 - 100 / (1 + RS)

## Grading Criteria

- [ ] 文件 `rsi_overbought_top3.txt` 已创建
- [ ] 文件包含恰好3条记录
- [ ] 股票代码为合法创业板代码（300开头）
- [ ] 超买天数为正整数（0-20之间）
- [ ] 记录按天数降序排列
- [ ] agent在过程中正确计算了RSI

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "rsi_overbought_top3.txt"
    if not result_file.exists():
        for alt in ["top3.txt", "result.txt", "output.txt", "rsi.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["three_records"] = 0.0
        scores["valid_codes"] = 0.0
        scores["valid_days"] = 0.0
        scores["sorted_desc"] = 0.0
        scores["rsi_computed"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()
    lines = [l.strip() for l in content.splitlines()
             if l.strip() and not l.startswith("#") and "代码" not in l and "股票" not in l]

    scores["three_records"] = 1.0 if len(lines) == 3 else (0.5 if 1 <= len(lines) <= 5 else 0.0)

    records = []
    for line in lines:
        parts = re.split(r'[,\s\t]+', line)
        if len(parts) >= 2:
            code = parts[0].strip()
            try:
                days = int(parts[1])
                records.append((code, days))
            except:
                pass

    valid_codes = [r for r in records if re.match(r'^3\d{5}$', r[0])]
    scores["valid_codes"] = 1.0 if len(valid_codes) >= 2 else (0.5 if len(valid_codes) >= 1 else 0.0)

    valid_days = [r for r in records if 0 <= r[1] <= 20]
    scores["valid_days"] = 1.0 if len(valid_days) >= 2 else (0.5 if len(valid_days) >= 1 else 0.0)

    if len(records) >= 2:
        days_list = [r[1] for r in records]
        scores["sorted_desc"] = 1.0 if all(days_list[i] >= days_list[i+1] for i in range(len(days_list)-1)) else 0.0
    else:
        scores["sorted_desc"] = 0.0

    transcript_str = str(transcript).lower()
    scores["rsi_computed"] = 1.0 if "rsi" in transcript_str else 0.0

    return scores
```
