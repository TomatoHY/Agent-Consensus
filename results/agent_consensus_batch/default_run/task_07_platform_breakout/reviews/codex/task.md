---
id: task_07_platform_breakout
name: 价格平台突破形态识别
category: breakout_pattern
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files: []
---

## Prompt

在创业板中找出以 2024-09-30 为截止交易日的前15个交易日内"突破平台"的股票，条件：
1) 前10天价格在一个窄幅区间波动（最高价 - 最低价 < 5%，以最低价为基准）；
2) 其中最后5个交易日里至少有3天收盘价突破前10个交易日的最高价；
3) 突破时成交量放大（突破日的成交量超过前10天均量的1.5倍）。

将结果写入 `breakout.txt`，每行一个股票代码：
```
300XXX
300XXX
```

## Expected Behavior

Agent应该：

1. 获取创业板股票列表
2. 对每只股票获取近15个交易日的K线数据（含收盘价、最高价、最低价、成交量）
3. 用前10天数据计算价格区间：range = (max_high - min_low) / min_low
4. 判断前10天是否处于窄幅（range < 5%）
5. 计算前10天最高收盘价作为突破基准
6. 统计后5天中收盘价突破基准的天数（≥3天）
7. 验证突破日成交量 > 前10天均量 * 1.5
8. 输出所有满足条件的股票代码

## Grading Criteria

- [ ] 文件 `breakout.txt` 已创建
- [ ] 文件内容为合法创业板代码或明确无结果
- [ ] agent在过程中正确定义了"前10天"和"最近5天"的时间段
- [ ] agent计算了成交量放大条件
- [ ] agent检查了价格区间（窄幅）条件

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "breakout.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "stocks.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["volume_checked"] = 0.0
        scores["range_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "no stock", "none", "0只", "空"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
    else:
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        valid_codes = [l for l in lines if re.match(r'^3\d{5}$', l)]
        scores["valid_format"] = 1.0 if len(valid_codes) > 0 else (0.5 if len(lines) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    scores["volume_checked"] = 1.0 if any(kw in transcript_str for kw in ["volume", "成交量", "均量", "vol"]) else 0.0
    scores["range_checked"] = 1.0 if any(kw in transcript_str for kw in ["range", "区间", "high.*low", "最高.*最低", "窄幅"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 形态检测逻辑的正确性（Weight: 40%）

**Score 1.0**: 三个条件的判断逻辑均完全正确：窄幅区间用(最高-最低)/最低计算、突破判断用收盘价与前10天最高价比较、成交量用前10天均量作为基准乘以1.5倍。
**Score 0.75**: 主要逻辑正确，但有1个条件的边界或基准略有偏差（如用最高价而非最低价作分母）。
**Score 0.5**: 正确实现了2个条件，第3个条件实现有误或缺失。
**Score 0.25**: 仅正确实现了1个条件。
**Score 0.0**: 三个条件的判断均有根本性错误或未实现。

### Criterion 2: 时间段划分（Weight: 25%）

**Score 1.0**: 正确地将15天数据分为"前10天"和"最近5天"两段，并分别用于不同计算，无时间段混用。
**Score 0.75**: 时间段划分基本正确，但边界有1-2天的偏差。
**Score 0.5**: 时间段划分存在混乱，部分计算用错了时间段。
**Score 0.25**: 未明确区分两个时间段，全部数据混合计算。
**Score 0.0**: 完全未按时间段要求处理数据。

### Criterion 3: 结果输出质量（Weight: 35%）

**Score 1.0**: 结果文件格式规范，股票代码合法，如无符合股票明确说明，整体输出简洁准确。
**Score 0.75**: 结果基本正确但格式略有瑕疵。
**Score 0.5**: 结果有内容但格式较乱或包含无效代码。
**Score 0.25**: 文件存在但内容可信度低。
**Score 0.0**: 未创建结果文件。
