---
id: task_13_dual_timeframe_macd
name: 日线周线双周期MACD共振选股
category: multi_timeframe_resonance
grading_type: hybrid
timeout_seconds: 480
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files: []
---

## Prompt

在创业板中找出同时满足日线和周线双周期MACD金叉共振的股票，具体条件：
1) 日线MACD金叉：DIFF上穿DEA，发生在以 2024-05-15 为截止交易日的最后10个交易日内；
2) 周线MACD金叉：用周K线数据（每周收盘价）计算MACD，金叉发生在截至 2024-05-15 的最后4周内；
3) 日线5日均线斜率为正（近5日均线值连续递增）；
4) 近5个交易日成交量均值 > 近20个交易日成交量均值的1.2倍（量能放大）。

将结果写入 `dual_timeframe_macd.txt`，格式：
```
股票代码,日线金叉日期,周线金叉日期,5日均线斜率,量比(近5日/近20日)
300XXX,2024-01-10,2024-01-08,0.12,1.35
```

## Expected Behavior

Agent应该：
1. 获取创业板股票列表
2. 对每只股票分别获取日线K线（建议90日）和周线K线（建议26周以上）
3. 分别在两个时间维度计算MACD，检测金叉及日期
4. 计算近5日均线序列，判断斜率（是否单调递增）
5. 计算量比
6. 筛选同时满足4个条件的股票

## Grading Criteria

- [ ] 文件 `dual_timeframe_macd.txt` 已创建
- [ ] 包含两个金叉日期（日线和周线）
- [ ] agent分别获取了日线和周线数据
- [ ] agent计算了量能比较指标
- [ ] agent检查了均线斜率

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "dual_timeframe_macd.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "macd_dual.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["two_dates"] = 0.0
        scores["weekly_data"] = 0.0
        scores["volume_checked"] = 0.0
        scores["slope_checked"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "no stock", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["two_dates"] = 1.0
    else:
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', content)
        scores["two_dates"] = 1.0 if len(dates) >= 2 else (0.5 if len(dates) >= 1 else 0.0)

    transcript_str = str(transcript).lower()
    scores["weekly_data"] = 1.0 if any(kw in transcript_str for kw in ["weekly", "周线", "week", "周k", "weekly_kline"]) else 0.0
    scores["volume_checked"] = 1.0 if any(kw in transcript_str for kw in ["volume", "成交量", "量比", "vol_ratio"]) else 0.0
    scores["slope_checked"] = 1.0 if any(kw in transcript_str for kw in ["slope", "斜率", "递增", "increasing", "gradient"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 双时间维度数据获取（Weight: 25%）

**Score 1.0**: 正确分别获取日线K线和周线K线数据，使用了不同的数据接口或参数，两个时间维度数据均有足够的历史长度用于MACD预热（日线≥60日，周线≥26周）。
**Score 0.75**: 获取了两种数据，但某一维度数据不够长，可能影响MACD准确性。
**Score 0.5**: 仅获取了一种数据，另一种通过聚合或估算替代（如手动从日线聚合周线）。
**Score 0.25**: 两种数据都不足，或只获取了一种数据类型。
**Score 0.0**: 未获取日线/周线数据。

### Criterion 2: 两个维度MACD金叉检测（Weight: 35%）

**Score 1.0**: 日线MACD和周线MACD分别计算，金叉日期准确，日线检测范围为近10个交易日，周线检测范围为近4周，时间范围均正确。
**Score 0.75**: 两个维度均检测了金叉，但某一维度的时间范围有偏差（如日线用了15天而非10天）。
**Score 0.5**: 仅正确检测了一个维度的金叉，另一维度有较大错误。
**Score 0.25**: 两个维度均有较大错误，但有尝试。
**Score 0.0**: 未完成双维度金叉检测。

### Criterion 3: 均线斜率与量能判断（Weight: 25%）

**Score 1.0**: 均线斜率用连续5日均线值是否单调递增来判断，量比 = 近5日均量 / 近20日均量，阈值1.2正确应用，两个条件均准确。
**Score 0.75**: 斜率或量比其中一个计算略有偏差，但思路正确。
**Score 0.5**: 仅实现了其中一个条件的判断。
**Score 0.25**: 两个条件均有实现但计算方法有误。
**Score 0.0**: 未检查均线斜率和量能条件。

### Criterion 4: 结果输出完整性（Weight: 15%）

**Score 1.0**: 输出包含代码、两个日期、斜率、量比，格式规范，无结果时明确说明。
**Score 0.75**: 输出包含大部分字段，有1-2个字段缺失或格式不规范。
**Score 0.5**: 只输出了代码，缺少具体数值。
**Score 0.25**: 文件存在但内容残缺。
**Score 0.0**: 未创建结果文件。
