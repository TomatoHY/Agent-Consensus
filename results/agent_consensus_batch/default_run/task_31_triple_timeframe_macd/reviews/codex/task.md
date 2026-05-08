---
id: task_31_triple_timeframe_macd
name: 日线周线月线三周期MACD共振
category: multi_timeframe_macd_resonance
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files: []
---

## Prompt

寻找日线、周线、月线三周期MACD共振的股票：

1. **日线**：MACD金叉（DIFF上穿DEA）发生在以 2024-03-22 为截止交易日的最后10个交易日内；
2. **周线**：MACD金叉发生在截至 2024-03-22 的最后4周内（用周K线计算）；
3. **月线**：MACD在0轴上方（月线DIFF > 0），或刚金叉（截至 2024-03-22 的最近2个月内发生金叉）；
4. **均线验证**：三个周期的收盘价均在各自周期的20均线上方（日线收盘 > 20日均线，周线截至 2024-03-22 的收盘 > 20周均线，月线截至 2024-03-22 的收盘 > 20月均线）。

将结果写入 `triple_timeframe_macd.txt`，格式：
```
股票代码,日线金叉日期,周线金叉日期,月线MACD状态,日线DIFF,周线DIFF,月线DIFF
300XXX,2024-01-10,2024-01-08,上方,0.15,0.42,1.23
```

月线MACD状态填写"金叉"（最近2个月内金叉）或"上方"（DIFF>0但未近期金叉）。

## Expected Behavior

Agent应该：
1. 分别获取日线（建议90天）、周线（建议52周）、月线（建议36个月）的K线数据
2. 在三个时间维度分别计算MACD（参数12/26/9均一致）
3. 检测各维度金叉日期和0轴状态
4. 计算三个周期的20均线并验证价格位置
5. 筛选同时满足四个条件的股票

## Grading Criteria

- [ ] 文件 `triple_timeframe_macd.txt` 已创建
- [ ] 包含日线、周线金叉日期和月线状态字段
- [ ] agent分别获取了三种时间维度的K线数据
- [ ] 月线状态字段为"金叉"或"上方"
- [ ] agent计算了三个周期各自的20均线

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "triple_timeframe_macd.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "macd_triple.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_format"] = 0.0
        scores["three_timeframes"] = 0.0
        scores["monthly_status"] = 0.0
        scores["three_ma_verified"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_format"] = 1.0
        scores["monthly_status"] = 1.0
    else:
        has_code = bool(re.search(r'3\d{5}', content))
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', content)
        scores["valid_format"] = 1.0 if (has_code and len(dates) >= 2) else (0.5 if has_code else 0.0)

        has_status = bool(re.search(r'金叉|上方|golden|above', content))
        scores["monthly_status"] = 1.0 if has_status else 0.0

    transcript_str = str(transcript).lower()
    has_daily = any(kw in transcript_str for kw in ["daily", "日线", "day.*kline"])
    has_weekly = any(kw in transcript_str for kw in ["weekly", "周线", "week.*kline"])
    has_monthly = any(kw in transcript_str for kw in ["monthly", "月线", "month.*kline"])
    scores["three_timeframes"] = 1.0 if (has_daily and has_weekly and has_monthly) else (0.5 if (has_weekly or has_monthly) else 0.0)
    scores["three_ma_verified"] = 1.0 if any(kw in transcript_str for kw in
        ["20周均线", "20月均线", "weekly.*ma20", "monthly.*ma", "20.*week"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 三个时间维度的数据处理（Weight: 30%）

**Score 1.0**: 正确分别获取日线、周线、月线K线数据，使用了不同的数据接口参数，三个维度均有足够预热长度，周线/月线数据非手动从日线聚合（或说明了聚合方法）。
**Score 0.75**: 获取了三种数据，但某一维度有聚合偏差或长度不足。
**Score 0.5**: 仅获取了日线和周线，月线用近似方法，或只获取了日线后手动聚合所有维度。
**Score 0.25**: 仅正确获取了一个时间维度的数据。
**Score 0.0**: 未分别获取多时间维度数据。

### Criterion 2: 三维度MACD计算与条件验证（Weight: 40%）

**Score 1.0**: 三个维度MACD参数均为12/26/9，金叉日期检测准确，日线10交易日/周线4周/月线2个月的时间范围条件正确，月线0轴判断（DIFF>0）准确。
**Score 0.75**: 三维度MACD基本正确，某一维度的时间范围有偏差（如月线用了3个月而非2个月）。
**Score 0.5**: 两个维度正确，月线只判断了0轴位置而未区分"金叉"和"上方"。
**Score 0.25**: 只有一个维度的MACD正确计算。
**Score 0.0**: 未完成三维度MACD计算。

### Criterion 3: 均线位置验证与结果输出（Weight: 30%）

**Score 1.0**: 三个周期各自的20均线正确计算，收盘价均在20均线上方的验证准确，输出字段完整，DIFF值精度合理，格式规范。
**Score 0.75**: 均线验证基本正确，但某一周期均线有偏差（如月线用了21月均线）。
**Score 0.5**: 只验证了1-2个周期的均线位置，DIFF值缺失。
**Score 0.25**: 均线验证基本缺失。
**Score 0.0**: 未创建结果文件。
