---
id: task_28_volatility_compression_explosion
name: 历史波动率压缩后爆发识别
category: volatility_compression_expansion
grading_type: hybrid
timeout_seconds: 360
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

识别创业板中"波动率压缩-爆发"模式，条件：

1. **低波动期**：在以 2024-10-08 为截止交易日的前30日内有至少10天的低波动期（单日振幅 = (最高-最低)/最低 < 3%）；

2. **波动率极度压缩**：计算10日历史波动率（HV10 = 10日收盘价对数收益率的标准差 × √252），压缩期间的HV10降至近60日HV10序列的30分位数以下；

3. **爆发**：压缩期结束后5日内出现单日振幅 > 7%的爆发日；

4. **阳线爆发**：爆发日收阳（收盘 > 开盘）且收盘价位于当日价格区间的上70%（(收盘-最低)/(最高-最低) > 0.7）；

5. **不回落**：爆发后3日内价格未回到压缩区间（最低价不低于爆发日开盘价）。

将结果写入 `vol_explosion.txt`，格式：
```
股票代码,压缩期天数,爆发日期,爆发振幅(%),爆发后3日涨幅(%)
300XXX,14,2024-01-15,9.2,5.8
```

## Expected Behavior

Agent应该：
1. 计算每日振幅序列，在近30日内检测连续10天低波动期
2. 计算10日HV并找其近60日30分位数，验证压缩期HV低于此阈值
3. 检测压缩期后5天内的爆发日
4. 验证爆发日的阳线和位置条件
5. 验证后续不回落条件
6. 计算爆发后3日涨幅

## Grading Criteria

- [ ] 文件 `vol_explosion.txt` 已创建
- [ ] 包含压缩天数、爆发日期、振幅、后续涨幅字段
- [ ] 爆发振幅 > 7%
- [ ] 压缩天数 >= 10
- [ ] agent计算了历史波动率（HV）
- [ ] agent使用了分位数判断

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "vol_explosion.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "explosion.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_compression_days"] = 0.0
        scores["valid_explosion_amplitude"] = 0.0
        scores["hv_computed"] = 0.0
        scores["percentile_used"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_compression_days"] = 1.0
        scores["valid_explosion_amplitude"] = 1.0
    else:
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.startswith("#") and "代码" not in l]

        records = []
        for line in lines:
            parts = re.split(r'[,\s\t]+', line)
            if len(parts) >= 5:
                try:
                    compression = int(parts[1])
                    amplitude = float(parts[3].replace('%', ''))
                    records.append((compression, amplitude))
                except:
                    pass

        valid_days = [r for r in records if r[0] >= 10]
        scores["valid_compression_days"] = 1.0 if len(valid_days) == len(records) and len(records) > 0 else (0.5 if len(valid_days) > 0 else 0.0)

        valid_amp = [r for r in records if r[1] > 7.0]
        scores["valid_explosion_amplitude"] = 1.0 if len(valid_amp) == len(records) and len(records) > 0 else (0.5 if len(valid_amp) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    scores["hv_computed"] = 1.0 if any(kw in transcript_str for kw in
        ["historical.*vol", "hv10", "历史波动率", "log.*return.*std", "realized.*vol"]) else 0.0
    scores["percentile_used"] = 1.0 if any(kw in transcript_str for kw in
        ["percentile", "分位数", "quantile", "30.*percentile", "np.percentile"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 低波动期与历史波动率计算（Weight: 35%）

**Score 1.0**: 振幅用(最高-最低)/最低计算，连续10天低波动期检测正确，HV10用对数收益率标准差×√252，分位数用近60日HV10序列的30分位数，逻辑严密。
**Score 0.75**: 主要逻辑正确，HV10用算术收益率代替对数收益率，或分位数计算方法略有偏差。
**Score 0.5**: 低波动期检测正确，但未计算HV或用价格波动代替收益率波动。
**Score 0.25**: 波动率压缩检测方法有根本性错误。
**Score 0.0**: 未实现波动率压缩检测。

### Criterion 2: 爆发条件与阳线验证（Weight: 35%）

**Score 1.0**: 爆发日振幅>7%、阳线（收>开）、收盘在区间上70%（位置公式正确），三个条件全部实现且在压缩期后5天内发生。
**Score 0.75**: 三个条件基本正确，收盘价位置计算有轻微错误（如用50%而非70%）。
**Score 0.5**: 只验证了振幅和阳线，未检查收盘价位置。
**Score 0.25**: 爆发条件验证有明显错误。
**Score 0.0**: 未验证爆发条件。

### Criterion 3: 后续不回落与结果输出（Weight: 30%）

**Score 1.0**: 后续3日不回落条件（最低价≥爆发日开盘价）正确实现，涨幅计算准确，输出格式规范，数值自洽。
**Score 0.75**: 后续验证基本正确，不回落条件用了略宽松的标准（如允许收盘跌但最低不跌）。
**Score 0.5**: 未实现后续不回落验证，但其他输出字段正确。
**Score 0.25**: 后续验证有明显错误。
**Score 0.0**: 未创建结果文件。
