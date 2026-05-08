---
id: task_09_price_volume_divergence
name: 量价背离信号检测
category: divergence_detection
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

在创业板中找出以 2024-11-29 为截止交易日的前30个交易日内"量价背离"的股票：
- 价格创新高：最后5个交易日的最高价 > 前25个交易日的最高价；
- 成交量萎缩：最后5个交易日的平均成交量 < 前25个交易日平均成交量的80%。

将结果写入 `divergence.txt`，格式：
```
股票代码,价格涨幅(%),成交量变化(%),背离度(%)
300XXX,X.XX,-XX.XX,XX.XX
```

其中：
- 价格涨幅 = (近5天最高价 / 前25天最高价 - 1) * 100
- 成交量变化 = (近5天均量 / 前25天均量 - 1) * 100（负值表示萎缩）
- 背离度 = 价格涨幅 - 成交量变化（两者差的绝对值）

## Expected Behavior

Agent应该：

1. 获取创业板股票列表
2. 对每只股票获取近30个交易日的K线数据（含最高价、成交量）
3. 将30天分为前25天和近5天两段
4. 分别计算两段的最高价和平均成交量
5. 判断是否满足价格新高且量能萎缩
6. 计算三个指标数值
7. 写入 `divergence.txt`

## Grading Criteria

- [ ] 文件 `divergence.txt` 已创建
- [ ] 文件包含代码和数值，格式正确
- [ ] 价格涨幅为正数（否则不满足创新高条件）
- [ ] 成交量变化为负数（否则不满足萎缩条件）
- [ ] 背离度为正数
- [ ] agent在过程中正确区分了两个时间段

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "divergence.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "stocks.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["price_positive"] = 0.0
        scores["vol_negative"] = 0.0
        scores["divergence_positive"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "no stock", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["price_positive"] = 1.0
        scores["vol_negative"] = 1.0
        scores["divergence_positive"] = 1.0
        return scores

    lines = [l.strip() for l in content.splitlines()
             if l.strip() and not l.startswith("#") and "代码" not in l]

    records = []
    for line in lines:
        parts = re.split(r'[,\s\t]+', line)
        if len(parts) >= 4:
            code = parts[0].strip()
            try:
                price_chg = float(parts[1].replace('%', ''))
                vol_chg = float(parts[2].replace('%', ''))
                divergence = float(parts[3].replace('%', ''))
                records.append((code, price_chg, vol_chg, divergence))
            except:
                pass

    scores["valid_format"] = 1.0 if len(records) > 0 else 0.0

    if records:
        scores["price_positive"] = 1.0 if all(r[1] > 0 for r in records) else 0.5
        scores["vol_negative"] = 1.0 if all(r[2] < 0 for r in records) else 0.5
        scores["divergence_positive"] = 1.0 if all(r[3] > 0 for r in records) else 0.5
    else:
        scores["price_positive"] = 0.0
        scores["vol_negative"] = 0.0
        scores["divergence_positive"] = 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 背离条件判断逻辑（Weight: 40%）

**Score 1.0**: 正确按照"前25天"和"近5天"划分数据，价格新高用最高价（非收盘价）比较，成交量萎缩用均量的80%阈值，逻辑严密。
**Score 0.75**: 逻辑基本正确，但用了收盘价代替最高价，或阈值略有偏差。
**Score 0.5**: 仅实现了两个条件中的一个，或时间段划分有误。
**Score 0.25**: 背离判断逻辑存在根本性错误（如价格和成交量方向判断反了）。
**Score 0.0**: 未实现背离检测。

### Criterion 2: 三项指标计算准确性（Weight: 30%）

**Score 1.0**: 价格涨幅、成交量变化、背离度三个指标均按公式正确计算，精度保留2位小数。
**Score 0.75**: 两个指标计算正确，一个指标有小错误（如背离度用加法而非差）。
**Score 0.5**: 仅正确计算了1-2个指标。
**Score 0.25**: 指标计算有多处错误但有尝试。
**Score 0.0**: 未计算任何指标。

### Criterion 3: 结果输出完整性（Weight: 30%）

**Score 1.0**: 结果格式完整，包含代码和三个数值，无结果时明确说明。
**Score 0.75**: 结果基本完整但格式略有不规范。
**Score 0.5**: 只输出了代码，缺少数值指标。
**Score 0.25**: 文件存在但内容残缺。
**Score 0.0**: 未创建结果文件。
