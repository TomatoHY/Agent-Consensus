---
id: task_32_weekly_breakout_daily_pullback
name: 周线突破后日线回踩确认形态
category: cross_timeframe_pattern
grading_type: hybrid
timeout_seconds: 420
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

识别"周线突破+日线回踩确认"跨周期形态：

**周线层面**：
- 截至 2024-04-22 的近4周内出现周线收盘价从下向上穿越60周均线（前一周收盘 < 60周均线，本周收盘 > 60周均线）；
- 突破后历史数据中周线未再次跌破60周均线（突破有效）。

**日线层面**（在周线突破后）：
- 价格回踩到20日均线附近（收盘价介于20日均线的-2%到+2%之间）；
- 回踩时成交量萎缩（回踩日的日均量 < 20日均量的80%）；
- 回踩后出现反弹日（次日或后天收阳且成交量 > 20日均量）。

将结果写入 `weekly_pullback.txt`，格式：
```
股票代码,周线突破日期,日线回踩日期,反弹日期,反弹日涨幅(%)
300XXX,2023-12-25,2024-01-08,2024-01-10,4.2
```

## Expected Behavior

Agent应该：
1. 获取周线K线（建议80周）计算60周均线，检测近4周内的突破信号
2. 获取日线K线，在周线突破后检测日线回踩
3. 验证回踩期间的成交量萎缩
4. 检测回踩后的反弹日

## Grading Criteria

- [ ] 文件 `weekly_pullback.txt` 已创建
- [ ] 包含周线突破日期、回踩日期、反弹日期三个时间字段
- [ ] agent获取了周线数据
- [ ] agent计算了60周均线
- [ ] 周线突破日期早于回踩日期早于反弹日期

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re
    from datetime import datetime

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "weekly_pullback.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "pullback.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["three_dates"] = 0.0
        scores["date_order"] = 0.0
        scores["weekly_data"] = 0.0
        scores["ma60w_computed"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["three_dates"] = 1.0
        scores["date_order"] = 1.0
    else:
        dates_in_content = re.findall(r'\d{4}-\d{2}-\d{2}', content)
        scores["three_dates"] = 1.0 if len(dates_in_content) >= 3 else (0.5 if len(dates_in_content) >= 2 else 0.0)

        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        valid_order = True
        for line in lines:
            ds = re.findall(r'\d{4}-\d{2}-\d{2}', line)
            if len(ds) >= 3:
                try:
                    d1 = datetime.strptime(ds[0], "%Y-%m-%d")
                    d2 = datetime.strptime(ds[1], "%Y-%m-%d")
                    d3 = datetime.strptime(ds[2], "%Y-%m-%d")
                    if not (d1 <= d2 <= d3):
                        valid_order = False
                except:
                    pass
        scores["date_order"] = 1.0 if valid_order else 0.0

    transcript_str = str(transcript).lower()
    scores["weekly_data"] = 1.0 if any(kw in transcript_str for kw in
        ["weekly", "周线", "week.*kline", "周k"]) else 0.0
    scores["ma60w_computed"] = 1.0 if any(kw in transcript_str for kw in
        ["60.*week", "60周", "ma60.*week", "60w.*ma"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 周线突破检测（Weight: 35%）

**Score 1.0**: 正确用周线收盘价判断突破（前周收盘<60周均线，本周收盘>60周均线），突破有效性验证（突破后未再跌破），60周均线计算准确，近4周时间范围正确。
**Score 0.75**: 突破检测基本正确，有效性验证略简化（如只检查突破后前2周未跌破）。
**Score 0.5**: 检测了突破但未验证有效性，或60周均线计算有偏差。
**Score 0.25**: 突破检测方法有根本性错误（如用日线数据估算周线）。
**Score 0.0**: 未实现周线突破检测。

### Criterion 2: 日线回踩与反弹验证（Weight: 40%）

**Score 1.0**: 回踩日期判断用收盘价与20日均线±2%的范围，回踩期成交量萎缩用<80%均量，反弹日用次日或后天收阳且放量（>均量），三个子条件全部正确。
**Score 0.75**: 三个子条件基本正确，某一条件有轻微偏差（如反弹日只检查次日不检查后天）。
**Score 0.5**: 只实现了2个子条件（如回踩判断和反弹，未检查缩量）。
**Score 0.25**: 日线层面条件有明显错误。
**Score 0.0**: 未实现日线层面验证。

### Criterion 3: 结果输出完整性（Weight: 25%）

**Score 1.0**: 输出包含三个日期和反弹涨幅，日期顺序正确，反弹涨幅>0，格式规范。
**Score 0.75**: 日期字段有2个，缺少其中一个，或涨幅精度不足。
**Score 0.5**: 只有代码，缺少时间字段。
**Score 0.25**: 文件存在但内容不完整。
**Score 0.0**: 未创建结果文件。
