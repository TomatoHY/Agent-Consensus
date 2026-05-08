---
id: task_27_atr_volatility_breakout
name: ATR波动率扩张突破识别
category: volatility_breakout
grading_type: automated
timeout_seconds: 300
workspace_files: []
---

## Prompt

筛选创业板中波动率扩张的股票：

1. 计算14日ATR（Average True Range，真实波动幅度均值）：
   - True Range = max(最高-最低, |最高-前收|, |最低-前收|)
   - ATR = TR的14日指数移动平均（Wilder平滑）

2. 截至 2024-09-09 的ATR值突破此前近60日ATR的80分位数（ATR显著放大）；

3. ATR扩张当日收盘价突破近20日最高价（向上突破）；

4. 突破日成交量 > 20日均量的2倍；

5. 排除暴跌导致的波动率扩张：突破日收阳（收盘>开盘）且涨幅>3%。

将结果写入 `atr_breakout.txt`，格式：
```
股票代码,截至2024-09-09的ATR,ATR的60日80分位数,突破日期,当日涨幅(%)
300XXX,2.35,1.89,2024-01-15,5.2
```

## Expected Behavior

Agent应该：
1. 获取近80日K线（60日分析+14日ATR预热+额外缓冲）
2. 计算True Range序列
3. 用Wilder平滑法计算14日ATR
4. 计算近60日ATR的80分位数
5. 检测ATR>80分位数的日期
6. 验证当日收盘价突破20日最高价、成交量>均量2倍、收阳涨幅>3%

## Grading Criteria

- [ ] 文件 `atr_breakout.txt` 已创建
- [ ] 包含ATR数值和80分位数（ATR > 80分位数）
- [ ] 包含突破日期和涨幅
- [ ] 涨幅值 > 3%
- [ ] ATR > 80分位数（当前ATR > 分位数值）
- [ ] agent计算了ATR指标

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "atr_breakout.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "breakout.txt", "atr.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["atr_comparison_valid"] = 0.0
        scores["breakout_date_present"] = 0.0
        scores["return_positive"] = 0.0
        scores["atr_computed"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["atr_comparison_valid"] = 1.0
        scores["breakout_date_present"] = 1.0
        scores["return_positive"] = 1.0
        transcript_str = str(transcript).lower()
        scores["atr_computed"] = 1.0 if "atr" in transcript_str else 0.0
        return scores

    lines = [l.strip() for l in content.splitlines()
             if l.strip() and not l.startswith("#") and "代码" not in l]

    records = []
    for line in lines:
        parts = re.split(r'[,\s\t]+', line)
        if len(parts) >= 5:
            try:
                atr_curr = float(parts[1])
                atr_80pct = float(parts[2])
                pct = float(parts[4].replace('%', ''))
                records.append((atr_curr, atr_80pct, pct))
            except:
                pass

    valid_comparison = [r for r in records if r[0] > r[1]]
    scores["atr_comparison_valid"] = 1.0 if len(valid_comparison) == len(records) and len(records) > 0 else (0.5 if len(valid_comparison) > 0 else 0.0)

    scores["breakout_date_present"] = 1.0 if bool(re.search(r'\d{4}-\d{2}-\d{2}', content)) else 0.0

    valid_return = [r for r in records if r[2] > 3.0]
    scores["return_positive"] = 1.0 if len(valid_return) == len(records) and len(records) > 0 else (0.5 if len(valid_return) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    scores["atr_computed"] = 1.0 if "atr" in transcript_str or "真实波动" in transcript_str or "true.*range" in transcript_str else 0.0

    return scores
```
