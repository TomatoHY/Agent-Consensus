---
id: task_24_doji_to_surge
name: 地量天量突破形态识别
category: volume_breakout
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.45
  llm_judge: 0.55
workspace_files: []
---

## Prompt

在创业板中识别"地量之后天量"形态，条件：
1. **地量期**：在以 2024-06-07 为截止交易日的前30日内出现至少连续3天的地量期（单日成交量 < 60日均量的50%）；
2. **横盘整理**：地量期内价格波动 < 3%（(最高价 - 最低价) / 最低价 < 3%）；
3. **天量突破**：地量期结束后10日内出现天量日（单日成交量 > 60日均量的3倍）；
4. **阳线突破**：天量日当天收阳（收盘>开盘）且涨幅>5%；
5. **价格突破**：天量日收盘价突破近30日最高价。

将结果写入 `doji_surge.txt`，格式：
```
股票代码,地量期天数,天量日期,量比(天量/60日均量),突破涨幅(%)
300XXX,5,2024-01-15,3.8,7.2
```

## Expected Behavior

Agent应该：
1. 计算60日均量作为参考基准
2. 在近30日内检测连续地量期（≥3天，每天<均量50%）
3. 验证地量期内价格横盘
4. 检测地量期结束后10日内的天量日
5. 验证天量日的阳线和突破条件
6. 计算量比和突破涨幅

## Grading Criteria

- [ ] 文件 `doji_surge.txt` 已创建
- [ ] 包含代码、地量天数、天量日期、量比、涨幅字段
- [ ] 量比值 > 3.0
- [ ] 突破涨幅 > 5.0%
- [ ] agent计算了60日均量
- [ ] agent检查了地量期内横盘条件

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "doji_surge.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "surge.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["volume_ratio_valid"] = 0.0
        scores["breakout_pct_valid"] = 0.0
        scores["avg_volume_computed"] = 0.0
        scores["consolidation_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["volume_ratio_valid"] = 1.0
        scores["breakout_pct_valid"] = 1.0
    else:
        has_code = bool(re.search(r'3\d{5}', content))
        has_date = bool(re.search(r'\d{4}-\d{2}-\d{2}', content))
        scores["valid_format"] = 1.0 if (has_code and has_date) else (0.5 if has_code else 0.0)

        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]
        records = []
        for line in lines:
            parts = re.split(r'[,\s\t]+', line)
            if len(parts) >= 5:
                try:
                    vol_ratio = float(parts[3])
                    pct = float(parts[4].replace('%', ''))
                    records.append((vol_ratio, pct))
                except:
                    pass

        valid_ratio = [r for r in records if r[0] > 3.0]
        scores["volume_ratio_valid"] = 1.0 if len(valid_ratio) == len(records) and len(records) > 0 else (0.5 if len(valid_ratio) > 0 else 0.0)

        valid_pct = [r for r in records if r[1] > 5.0]
        scores["breakout_pct_valid"] = 1.0 if len(valid_pct) == len(records) and len(records) > 0 else (0.5 if len(valid_pct) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    scores["avg_volume_computed"] = 1.0 if any(kw in transcript_str for kw in
        ["60.*均量", "60.*mean.*vol", "avg.*vol.*60", "60日均量"]) else 0.0
    scores["consolidation_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["横盘", "consolidat", "price.*range", "3%", "振幅"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 地量期检测逻辑（Weight: 35%）

**Score 1.0**: 正确用滑动窗口在近30日内搜索连续≥3天的地量期（每天<60日均量50%），地量期内价格振幅<3%用最高价和最低价计算，能找到所有满足条件的地量期。
**Score 0.75**: 地量期检测基本正确，但连续天数从3天放宽到2天，或振幅计算用收盘价范围而非最高最低价。
**Score 0.5**: 地量期能被检测，但未验证价格横盘条件。
**Score 0.25**: 地量期判断有根本性错误（如只检查单天地量而非连续地量）。
**Score 0.0**: 未实现地量期检测。

### Criterion 2: 天量突破条件验证（Weight: 35%）

**Score 1.0**: 天量日必须在地量期结束后10天内，量比>3倍，当天收阳（收>开），涨幅>5%，突破近30日最高价，五个子条件全部正确。
**Score 0.75**: 主要条件正确，个别子条件（如突破近30日最高价）有轻微偏差。
**Score 0.5**: 实现了3-4个子条件，缺少价格突破或阳线验证。
**Score 0.25**: 仅验证了量比>3，其他条件未实现。
**Score 0.0**: 未实现天量突破验证。

### Criterion 3: 结果输出准确性（Weight: 30%）

**Score 1.0**: 输出字段完整，地量期天数≥3，天量日期在合理范围，量比>3，突破涨幅>5%，数值自洽。
**Score 0.75**: 输出基本正确，个别字段精度或格式略有问题。
**Score 0.5**: 缺少量比或突破涨幅字段。
**Score 0.25**: 只有代码和日期。
**Score 0.0**: 未创建结果文件。
