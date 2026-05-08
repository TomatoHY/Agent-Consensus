---
id: task_25_golden_valley
name: 银山谷金山谷均线形态识别
category: moving_average_pattern
grading_type: hybrid
timeout_seconds: 360
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

筛选创业板中出现"金山谷"信号的股票：

**银山谷**（第一次信号）：5日、10日、20日均线首次从下而上依次排列（5日>10日>20日），且三线间距<8%（(5日均线-20日均线)/20日均线 < 8%）。

**金山谷**（第二次更强信号）：价格在银山谷后出现回调，但不跌破20日均线（收盘价始终 ≥ 20日均线），之后再次形成5日>10日>20日的多头排列。

金山谷须满足：
- 距银山谷10-30个交易日；
- 金山谷位置（10日均线值）高于银山谷位置（10日均线值）；
- 三线间距也<8%。

在以 2024-07-08 为截止交易日的前60个交易日内搜索，将结果写入 `golden_valley.txt`，格式：
```
股票代码,银山谷日期,金山谷日期,间隔天数
300XXX,2023-11-10,2023-12-05,25
```

## Expected Behavior

Agent应该：
1. 对每只股票获取近120日的K线数据（用于均线计算和搜索）
2. 计算5日、10日、20日均线序列
3. 在近60日内检测5>10>20的多头排列首次出现（银山谷），验证三线间距<8%
4. 在银山谷后检测回调期（均线不破位但价格未再次形成多头排列）
5. 检测金山谷：再次出现多头排列，且在银山谷后10-30天内，10日均线值更高
6. 记录两个信号的日期和间隔

## Grading Criteria

- [ ] 文件 `golden_valley.txt` 已创建
- [ ] 包含代码、银山谷日期、金山谷日期、间隔天数
- [ ] 间隔天数在10-30天之间
- [ ] agent计算了三条均线（5/10/20日）
- [ ] agent检查了三线间距条件
- [ ] 金山谷日期晚于银山谷日期

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re
    from datetime import datetime

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "golden_valley.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "valley.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["interval_valid"] = 0.0
        scores["three_ma_computed"] = 0.0
        scores["spacing_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["interval_valid"] = 1.0
    else:
        has_code = bool(re.search(r'3\d{5}', content))
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', content)
        scores["valid_format"] = 1.0 if (has_code and len(dates) >= 2) else (0.5 if has_code else 0.0)

        # Check interval (10-30 days)
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        valid_intervals = []
        for line in lines:
            intervals = re.findall(r'\b([1-9]\d?)\b', line)
            for iv in intervals:
                iv_int = int(iv)
                if 10 <= iv_int <= 30:
                    valid_intervals.append(iv_int)
        scores["interval_valid"] = 1.0 if len(valid_intervals) > 0 else 0.0

    transcript_str = str(transcript).lower()
    scores["three_ma_computed"] = 1.0 if all(kw in transcript_str for kw in ["ma5", "ma10", "ma20"]) or \
        all(kw in transcript_str for kw in ["5日均线", "10日均线", "20日均线"]) else \
        (0.5 if any(kw in transcript_str for kw in ["ma5", "ma10", "5日均线"]) else 0.0)
    scores["spacing_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["8%", "0.08", "间距", "spacing", "三线.*间"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 银山谷检测逻辑（Weight: 30%）

**Score 1.0**: 正确检测5>10>20均线首次形成（前一日不满足条件，当日满足），三线间距用(MA5-MA20)/MA20计算，<8%阈值正确，在近60日内搜索。
**Score 0.75**: 银山谷检测基本正确，首次形成判断略有偏差（如未要求前日不满足）。
**Score 0.5**: 检测了5>10>20排列但未检查三线间距，或间距计算方法有误。
**Score 0.25**: 银山谷判断有根本性错误。
**Score 0.0**: 未实现银山谷检测。

### Criterion 2: 金山谷条件验证（Weight: 40%）

**Score 1.0**: 完整验证四个金山谷条件：再次多头排列、间隔10-30天、10日均线值更高、三线间距<8%，且回调期间价格未跌破20日均线的约束也有考虑。
**Score 0.75**: 验证了3个金山谷条件，10日均线值比较或间隔天数范围有轻微偏差。
**Score 0.5**: 只验证了2个条件（再次排列+间隔），忽略了均线值比较或间距条件。
**Score 0.25**: 仅检测了再次出现多头排列，无其他验证。
**Score 0.0**: 未实现金山谷验证。

### Criterion 3: 结果输出与合理性（Weight: 30%）

**Score 1.0**: 输出格式规范，金山谷日期晚于银山谷日期，间隔天数在10-30之间，代码合法，无结果时明确说明。
**Score 0.75**: 输出基本正确，间隔计算用日历日而非交易日（偏差在合理范围内）。
**Score 0.5**: 缺少间隔天数字段，或日期顺序有误。
**Score 0.25**: 输出不完整或格式混乱。
**Score 0.0**: 未创建结果文件。
