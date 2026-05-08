---
id: task_19_52week_high_followthrough
name: 有量创52周新高且持续上涨识别
category: event_driven_breakout_followthrough
grading_type: hybrid
timeout_seconds: 420
grading_weights:
  automated: 0.45
  llm_judge: 0.55
workspace_files: []
---

## Prompt

在创业板中找出以 2024-11-15 为截止交易日的前30个交易日内股价创52周新高、成交量放大且后续持续上涨的股票：

**条件1（创新高）**：收盘价 > 过去252个交易日的最高收盘价，创新高发生在最近30天内。

**条件2（量能验证）**：创新高当天及前后各2天（共5天窗口）的成交量均值 > 60日均量的1.5倍。

**条件3（持续性）**：新高后5个交易日内，至少3天收盘价高于创新高当天的收盘价（持续上涨）。

将结果写入 `breakout_followthrough.txt`，格式：
```
股票代码,创新高日期,创新高价格,新高后5日涨幅(%)
300XXX,2024-01-10,45.6,8.3
```

## Expected Behavior

Agent应该：
1. 对每只股票获取近282个交易日的收盘价（252+30天）
2. 在近30天窗口内找到收盘价首次突破252日最高收盘价的日期
3. 验证该日期±2天的成交量均值是否超过60日均量的1.5倍
4. 验证新高后5天内的收盘价是否有3天超过新高价
5. 计算新高后5日涨幅 = (第5日收盘 / 创新高日收盘 - 1) * 100

## Grading Criteria

- [ ] 文件 `breakout_followthrough.txt` 已创建
- [ ] 包含代码、日期、价格、涨幅四个字段
- [ ] 价格为正数
- [ ] 日期格式规范
- [ ] agent计算了52周最高价
- [ ] agent验证了量能窗口条件

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "breakout_followthrough.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "breakout.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["52week_high_computed"] = 0.0
        scores["volume_window_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
    else:
        has_code = bool(re.search(r'3\d{5}', content))
        has_date = bool(re.search(r'\d{4}-\d{2}-\d{2}', content))
        has_price = bool(re.search(r'\d+\.\d{1,2}', content))
        scores["valid_format"] = 1.0 if (has_code and has_date and has_price) else (0.5 if has_code else 0.0)

    transcript_str = str(transcript).lower()
    scores["52week_high_computed"] = 1.0 if any(kw in transcript_str for kw in
        ["52.*week", "252", "新高", "year.*high", "52w"]) else 0.0
    scores["volume_window_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["window", "±2", "前后", "5.*day.*vol", "volume.*window"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 52周新高检测逻辑（Weight: 30%）

**Score 1.0**: 正确用过去252个交易日（非日历日）的最高收盘价作为基准，在近30个交易日内检测突破时间点，每只股票只取第一次突破日期。
**Score 0.75**: 52周新高检测基本正确，但用了日历天数（365天）代替交易日（252天），或多次突破取了最后一次。
**Score 0.5**: 用了近似方法（如年度最高价），但基本思路正确。
**Score 0.25**: 52周新高概念理解有误（如只看近30天的最高价）。
**Score 0.0**: 未检测52周新高。

### Criterion 2: 量能窗口与持续性验证（Weight: 40%）

**Score 1.0**: 成交量窗口正确取创新高日±2天共5天的均值，与60日均量比较，阈值1.5倍；持续性判断后5天收盘价，至少3天超过新高价，逻辑严密。
**Score 0.75**: 量能窗口或持续性其中一个有轻微偏差（如±2天计算有边界错误）。
**Score 0.5**: 仅实现了量能验证或持续性验证其中一个条件。
**Score 0.25**: 两个条件均有实现但逻辑有明显错误。
**Score 0.0**: 未实现量能和持续性验证。

### Criterion 3: 结果完整性与准确性（Weight: 30%）

**Score 1.0**: 输出包含代码、创新高日期、创新高价格、新高后5日涨幅，涨幅计算用第5日收盘价（非最高价），数值合理。
**Score 0.75**: 输出基本完整，涨幅计算基准略有偏差（如用5日最高价）。
**Score 0.5**: 缺少价格或涨幅字段。
**Score 0.25**: 只有代码，无具体数值。
**Score 0.0**: 未创建结果文件。
