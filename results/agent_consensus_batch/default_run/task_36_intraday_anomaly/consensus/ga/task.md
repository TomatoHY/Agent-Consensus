---
id: task_36_intraday_anomaly
name: 盘中急拉或V型反转异动信号
category: intraday_anomaly
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files: []
---

## Prompt

捕捉盘中异动信号（需要分时或30分钟K线数据），在截至 2024-08-22 的最近5个交易日内：

**类型1：急拉信号**
- 30分钟内涨幅 > 5%（用30分钟K线计算，单个30分钟K线涨幅=(本K收盘-上K收盘)/上K收盘>5%）；
- 异动30分钟成交量 > 当日前几个时段均量的5倍。

**类型2：V型反转**
- 30分钟跌幅 > 3%后，随后连续2个30分钟K线反弹收复失地（收盘价回到跌幅前水平）；
- 异动时段成交量 > 前几个时段均量的5倍。

**后续验证**：
- 当日收盘价位于全日振幅的上60%（(收盘-最低)/(最高-最低) > 0.6）；
- 次日收盘价不跌破异动日最低价（持续强势）。

将结果写入 `intraday_signal.txt`，格式：
```
股票代码,异动日期,异动类型,异动幅度(%),当日收盘位置(%),次日是否持续
300XXX,2024-01-10,急拉,6.2,75.3,是
```

**注意**：若工具不支持分时数据，可使用30分钟K线数据；若30分钟K线也不支持，则说明数据限制并尝试用日K线的开高低收来近似判断盘中大振幅。

## Expected Behavior

Agent应该：
1. 尝试获取分时或30分钟K线数据
2. 检测急拉或V型反转信号
3. 验证成交量放大条件
4. 计算当日收盘价位置
5. 验证次日不跌破最低价

## Grading Criteria

- [ ] 文件 `intraday_signal.txt` 已创建
- [ ] 包含异动类型字段（急拉/V型反转）
- [ ] agent尝试了分时或30分钟K线数据获取
- [ ] 当日收盘位置值在0-100之间
- [ ] 次日持续字段为是/否

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "intraday_signal.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "signal.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["anomaly_type"] = 0.0
        scores["intraday_attempted"] = 0.0
        scores["closing_position"] = 0.0
        scores["continuation_field"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["anomaly_type"] = 1.0
        scores["closing_position"] = 1.0
        scores["continuation_field"] = 1.0
    else:
        has_type = bool(re.search(r'急拉|V型|v型|surge|reversal', content, re.IGNORECASE))
        scores["anomaly_type"] = 1.0 if has_type else 0.0

        positions = re.findall(r'\b([2-9]\d\.\d|100\.0)\b', content)
        valid_pos = [float(p) for p in positions if 0 < float(p) <= 100]
        scores["closing_position"] = 1.0 if len(valid_pos) > 0 else 0.0

        has_yn = bool(re.search(r'\b(是|否|yes|no)\b', content, re.IGNORECASE))
        scores["continuation_field"] = 1.0 if has_yn else 0.0

    transcript_str = str(transcript).lower()
    scores["intraday_attempted"] = 1.0 if any(kw in transcript_str for kw in
        ["分时", "30分钟", "30min", "minute.*kline", "intraday", "tick", "min_kline"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 数据获取与处理（Weight: 25%）

**Score 1.0**: 成功获取了30分钟或分时K线数据，或在无法获取时明确说明了数据限制并提出了合理的日K线近似方案，数据处理方法合理。
**Score 0.75**: 获取了30分钟K线数据但数据范围不足（如只有最近1天），或近似方案较粗糙。
**Score 0.5**: 未能获取分时数据，但用日K线的振幅进行了合理近似，并明确说明了局限性。
**Score 0.25**: 数据获取失败且无任何替代方案。
**Score 0.0**: 未尝试获取任何相关数据。

### Criterion 2: 信号检测逻辑（Weight: 35%）

**Score 1.0**: 急拉信号（单30分钟涨幅>5%）和V型反转（跌>3%后2个K线收复）的检测逻辑正确，成交量放大（>5倍前段均量）的计算方法合理。
**Score 0.75**: 主要信号检测正确，成交量放大的基准选取有轻微偏差（如用全天均量而非前几段均量）。
**Score 0.5**: 只实现了一种异动类型的检测，另一种未实现。
**Score 0.25**: 信号检测逻辑有明显错误。
**Score 0.0**: 未实现信号检测。

### Criterion 3: 后续验证与结果输出（Weight: 40%）

**Score 1.0**: 当日收盘位置公式正确，次日持续验证（收盘不跌破当日最低价）逻辑正确，输出所有字段完整，数值合理。
**Score 0.75**: 后续验证基本正确，次日验证用了略宽松的条件（如允许次日最低价略破）。
**Score 0.5**: 实现了当日收盘位置但未做次日验证，或只做了次日验证。
**Score 0.25**: 后续验证缺失，只有信号日期。
**Score 0.0**: 未创建结果文件。
