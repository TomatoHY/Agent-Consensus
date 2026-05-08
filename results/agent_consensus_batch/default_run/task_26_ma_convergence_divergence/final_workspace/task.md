---
id: task_26_ma_convergence_divergence
name: 均线粘合发散形态识别
category: ma_convergence_divergence
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.45
  llm_judge: 0.55
workspace_files: []
---

## Prompt

找出均线"粘合-发散"形态的股票，条件：

**粘合期**：以 2024-08-08 为截止交易日的前20日内存在至少5天均线粘合期，5日、10日、20日、30日四条均线间最大距离 < 3%（最大距离 = (最大均线值 - 最小均线值) / 最小均线值）。

**发散期**：粘合期结束后的5日内，均线开始向上发散：5日 > 10日 > 20日 > 30日，且相邻均线间距均 > 2%。

**量能配合**：发散期均量 > 粘合期均量的1.5倍以上。

将结果写入 `ma_divergence.txt`，格式：
```
股票代码,粘合期开始,粘合期结束,发散开始日期,发散后5日涨幅(%)
300XXX,2024-01-02,2024-01-08,2024-01-10,9.5
```

## Expected Behavior

Agent应该：
1. 获取近60日K线（含成交量），用于计算四条均线
2. 在近20日内用滑动窗口检测连续5天均线粘合
3. 在粘合期结束后的5天内检测均线发散条件
4. 验证量能条件（均量比较）
5. 计算发散后5日涨幅

## Grading Criteria

- [ ] 文件 `ma_divergence.txt` 已创建
- [ ] 包含粘合期起止日期和发散开始日期
- [ ] 发散开始日期晚于粘合期结束日期
- [ ] agent计算了四条均线（5/10/20/30日）
- [ ] agent验证了量能条件
- [ ] 发散后涨幅为正数（向上发散）

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re
    from datetime import datetime

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "ma_divergence.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "divergence.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["date_order"] = 0.0
        scores["four_ma_computed"] = 0.0
        scores["volume_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["date_order"] = 1.0
    else:
        has_code = bool(re.search(r'3\d{5}', content))
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', content)
        has_return = bool(re.search(r'\d+\.\d', content))
        scores["valid_format"] = 1.0 if (has_code and len(dates) >= 3 and has_return) else (0.5 if has_code else 0.0)

        # Date order check
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
    has_30ma = any(kw in transcript_str for kw in ["ma30", "30日均线", "30.*ma", "sma.*30"])
    has_ma_set = any(kw in transcript_str for kw in ["ma5", "ma10", "ma20"])
    scores["four_ma_computed"] = 1.0 if (has_30ma and has_ma_set) else (0.5 if has_ma_set else 0.0)
    scores["volume_checked"] = 1.0 if any(kw in transcript_str for kw in
        ["volume", "成交量", "均量", "vol.*ratio"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 粘合期与发散期检测（Weight: 40%）

**Score 1.0**: 粘合期用四条均线最大距离<3%（用最小值作分母），连续≥5天，发散期用5>10>20>30且相邻间距>2%，两者时间关系正确（发散在粘合后5天内）。
**Score 0.75**: 主要逻辑正确，间距计算方法有轻微偏差（如只检查5日和30日均线的距离）。
**Score 0.5**: 实现了粘合或发散其中一个，另一个条件有明显错误。
**Score 0.25**: 粘合和发散的判断均有根本性错误。
**Score 0.0**: 未实现粘合发散检测。

### Criterion 2: 量能配合验证（Weight: 25%）

**Score 1.0**: 正确计算粘合期和发散期各自的均量（不是单天成交量），发散期均量/粘合期均量>1.5的条件正确应用。
**Score 0.75**: 量能比较方向正确，但用单天成交量代替了期间均量。
**Score 0.5**: 验证了成交量放大但未精确计算1.5倍阈值。
**Score 0.25**: 量能条件验证有明显错误。
**Score 0.0**: 未验证量能条件。

### Criterion 3: 结果输出完整性（Weight: 35%）

**Score 1.0**: 输出5个字段完整，三个日期逻辑顺序正确（粘合开始≤粘合结束≤发散开始），涨幅为正值，格式规范。
**Score 0.75**: 日期字段有2个，但粘合期的起止日期只提供了一个，或涨幅计算基准略有偏差。
**Score 0.5**: 缺少2-3个字段，但代码和发散日期存在。
**Score 0.25**: 只有代码，无日期或涨幅。
**Score 0.0**: 未创建结果文件。
