---
id: task_35_low_drawdown_growth
name: 低回撤稳健成长股筛选
category: risk_adjusted_return
grading_type: automated
timeout_seconds: 360
workspace_files: []
---

## Prompt

筛选低回撤稳健成长股，条件：
1. 截至 2024-07-22 的近60个交易日收益率 > 20%（成长性）；
2. 最大回撤 < 12%（回撤控制）：最大回撤 = (峰值 - 谷值) / 峰值；
3. Calmar比率 > 2：Calmar = 年化收益率 / 最大回撤（年化收益率 = 60日收益率 * (252/60)）；
4. 连续下跌天数不超过5天（无持续下跌）；
5. 单日最大跌幅 < 6%（无极端风险）；
6. 近20日上涨天数占比 > 55%（胜率高）。

按Calmar比率排序，取前10只，写入 `calmar_top10.txt`，格式：
```
股票代码,60日收益率(%),最大回撤(%),年化收益率(%),Calmar比率,近20日胜率(%)
300XXX,25.3,8.5,106.3,12.5,65.0
```

## Expected Behavior

Agent应该：
1. 获取创业板近62个交易日的收盘价（预留缓冲）
2. 计算60日总收益率
3. 计算最大回撤（用滚动最大值计算水位线）
4. 计算Calmar比率
5. 检查连续下跌天数（滑动窗口，无超过5天的连续下跌）
6. 检查单日最大跌幅（<6%）
7. 统计近20日上涨天数占比
8. 综合筛选后按Calmar排序取前10

## Grading Criteria

- [ ] 文件 `calmar_top10.txt` 已创建
- [ ] 最多10条记录
- [ ] 60日收益率 > 20%
- [ ] 最大回撤 < 12%
- [ ] Calmar比率 > 2
- [ ] agent计算了最大回撤

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "calmar_top10.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "top10.txt", "calmar.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["count_limit"] = 0.0
        scores["return_valid"] = 0.0
        scores["drawdown_valid"] = 0.0
        scores["calmar_valid"] = 0.0
        scores["max_drawdown_computed"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["count_limit"] = 1.0
        scores["return_valid"] = 1.0
        scores["drawdown_valid"] = 1.0
        scores["calmar_valid"] = 1.0
        transcript_str = str(transcript).lower()
        scores["max_drawdown_computed"] = 1.0 if any(kw in transcript_str for kw in
            ["drawdown", "回撤", "max.*drawdown", "calmar"]) else 0.0
        return scores

    lines = [l.strip() for l in content.splitlines()
             if l.strip() and not l.startswith("#") and "代码" not in l]
    scores["count_limit"] = 1.0 if len(lines) <= 10 else 0.5

    records = []
    for line in lines:
        parts = re.split(r'[,\s\t]+', line)
        if len(parts) >= 6:
            try:
                ret60 = float(parts[1].replace('%', ''))
                drawdown = float(parts[2].replace('%', ''))
                calmar = float(parts[4])
                records.append((ret60, drawdown, calmar))
            except:
                pass

    valid_ret = [r for r in records if r[0] > 20]
    scores["return_valid"] = 1.0 if len(valid_ret) == len(records) and len(records) > 0 else (0.5 if len(valid_ret) > 0 else 0.0)

    valid_dd = [r for r in records if r[1] < 12]
    scores["drawdown_valid"] = 1.0 if len(valid_dd) == len(records) and len(records) > 0 else (0.5 if len(valid_dd) > 0 else 0.0)

    valid_calmar = [r for r in records if r[2] > 2]
    scores["calmar_valid"] = 1.0 if len(valid_calmar) == len(records) and len(records) > 0 else (0.5 if len(valid_calmar) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    scores["max_drawdown_computed"] = 1.0 if any(kw in transcript_str for kw in
        ["drawdown", "回撤", "max.*drawdown", "cummax", "rolling.*max"]) else 0.0

    return scores
```
