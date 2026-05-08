---
id: task_22_bullish_sandwich
name: 两阳夹一阴多方炮形态识别
category: bullish_pattern
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.45
  llm_judge: 0.55
workspace_files: []
---

## Prompt

筛选创业板中出现"两阳夹一阴"多方炮形态的股票，条件：
1. 连续3个交易日：第1日、第3日为阳线且涨幅>2%；第2日为阴线但跌幅<1%；
2. 第3日阳线实体完全吞没第2日阴线（第3日收盘价 > 第2日开盘价，第3日开盘价 < 第2日收盘价）；
3. 三日成交量逐步放大（第2日成交量 > 第1日，第3日成交量 > 第2日）；
4. 形态出现在上升趋势中（5日均线 > 10日均线 > 20日均线）。

形态可出现在以 2024-04-08 为截止交易日的前20个交易日内任意位置。

将结果写入 `bullish_sandwich.txt`，格式：
```
股票代码,形态日期,三日成交量比(第2/第1,第3/第2)
300XXX,2024-01-10,1.15,1.23
```

## Expected Behavior

Agent应该：
1. 对每只股票获取近60日K线（含开盘、收盘、成交量）
2. 遍历近20日，对每个连续3日窗口检测形态
3. 逐条验证4个条件
4. 记录满足条件的形态日期（取第1天日期）
5. 计算成交量比

## Grading Criteria

- [ ] 文件 `bullish_sandwich.txt` 已创建
- [ ] 包含代码、日期、成交量比字段
- [ ] agent检查了"完全吞没"条件（第3天实体覆盖第2天实体）
- [ ] agent验证了均线多头排列条件
- [ ] 成交量比均大于1.0（放量）

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "bullish_sandwich.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "pattern.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["engulfing_checked"] = 0.0
        scores["ma_trend_checked"] = 0.0
        scores["volume_ratio_valid"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["volume_ratio_valid"] = 1.0
    else:
        has_code = bool(re.search(r'3\d{5}', content))
        has_date = bool(re.search(r'\d{4}-\d{2}-\d{2}', content))
        scores["valid_format"] = 1.0 if (has_code and has_date) else (0.5 if has_code else 0.0)

        ratios = re.findall(r'1\.\d{2}', content)
        valid_ratios = [float(r) for r in ratios if float(r) > 1.0]
        scores["volume_ratio_valid"] = 1.0 if len(valid_ratios) >= 2 else (0.5 if len(valid_ratios) >= 1 else 0.0)

    transcript_str = str(transcript).lower()
    scores["engulfing_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["吞没", "engulf", "完全", "cover", "close.*>.*open", "实体覆盖"]) else 0.0
    scores["ma_trend_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["ma5.*ma10", "5.*10.*20", "多头排列", "golden.*cross.*ma", "均线.*多头"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 形态四个条件的准确实现（Weight: 40%）

**Score 1.0**: 四个条件完全正确实现：阳线/阴线用开收盘比较（非涨跌幅），涨跌幅计算用前日收盘，第3天实体吞没第2天实体用开收价比较，成交量逐步放大用连续比较。
**Score 0.75**: 四个条件基本正确，有1个条件使用了近似方法（如用涨幅代替实体方向）。
**Score 0.5**: 实现了3个条件，"完全吞没"条件未正确实现（最容易出错）。
**Score 0.25**: 仅实现了1-2个条件。
**Score 0.0**: 未实现形态判断。

### Criterion 2: 上升趋势均线排列验证（Weight: 25%）

**Score 1.0**: 正确计算5日、10日、20日均线，验证5>10>20的多头排列，在形态发生当日（或第3天）进行验证，而非全程均需保持。
**Score 0.75**: 均线多头排列验证基本正确，但用的是形态第1天而非第3天，或均线参数略有偏差。
**Score 0.5**: 只检查了部分均线关系（如只验证5>10）。
**Score 0.25**: 上升趋势验证逻辑有明显错误。
**Score 0.0**: 未验证均线趋势。

### Criterion 3: 结果输出完整性（Weight: 35%）

**Score 1.0**: 输出包含代码、形态第1天日期、两个成交量比（第2/第1、第3/第2），数值均>1.0，格式规范。
**Score 0.75**: 输出基本完整，成交量比只给了一个或格式略乱。
**Score 0.5**: 只有代码和日期，无成交量比。
**Score 0.25**: 文件存在但内容不完整。
**Score 0.0**: 未创建结果文件。
