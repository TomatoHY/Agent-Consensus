---
id: task_23_gentle_volume_rise
name: 温和放量上涨线性回归筛选
category: volume_trend
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.5
  llm_judge: 0.5
workspace_files: []
---

## Prompt

找出创业板中呈现"温和放量"上涨的股票，条件：
1. 以 2024-05-08 为截止交易日的前10个交易日连续上涨（每日涨幅在0.5%-4%之间，无暴涨）；
2. 成交量呈梯度放大趋势：用**线性回归**检验成交量序列，要求斜率为正且R² > 0.6；
3. 10日累计涨幅在8%-20%之间（稳健上涨）；
4. 换手率（=成交量/流通股本）在3%-8%之间（不过热）。

将结果写入 `gentle_rise.txt`，格式：
```
股票代码,10日涨幅(%),成交量线性回归斜率,R²,平均换手率(%)
300XXX,14.5,1250000,0.78,5.2
```

## Expected Behavior

Agent应该：
1. 获取近10个交易日的K线数据和换手率（或流通股本）
2. 检查每日涨幅是否在0.5%-4%之间且连续10天
3. 对10天成交量序列做线性回归（用Python的numpy.polyfit或scipy.stats.linregress），获取斜率和R²
4. 计算累计涨幅和平均换手率
5. 输出满足所有条件的股票

## Grading Criteria

- [ ] 文件 `gentle_rise.txt` 已创建
- [ ] 包含代码、涨幅、斜率、R²、换手率五个字段
- [ ] R²值在0-1之间
- [ ] 涨幅在8%-20%范围内
- [ ] agent使用了线性回归方法
- [ ] 换手率在3%-8%范围内

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    from pathlib import Path
    import re

    scores = {}
    workspace = Path(workspace_path)

    result_file = workspace / "gentle_rise.txt"
    if not result_file.exists():
        for alt in ["result.txt", "output.txt", "rise.txt"]:
            alt_path = workspace / alt
            if alt_path.exists():
                result_file = alt_path
                break

    if not result_file.exists():
        scores["file_created"] = 0.0
        scores["valid_return"] = 0.0
        scores["r_squared_valid"] = 0.0
        scores["turnover_valid"] = 0.0
        scores["regression_used"] = 0.0
        return scores

    scores["file_created"] = 1.0
    content = result_file.read_text().strip()

    no_result_phrases = ["无符合", "没有", "none"]
    if any(p in content.lower() for p in no_result_phrases):
        scores["valid_return"] = 1.0
        scores["r_squared_valid"] = 1.0
        scores["turnover_valid"] = 1.0
        transcript_str = str(transcript).lower()
        scores["regression_used"] = 1.0 if any(kw in transcript_str for kw in
            ["linear.*regress", "线性回归", "polyfit", "linregress", "r.*squared", "r²"]) else 0.0
        return scores

    lines = [l.strip() for l in content.splitlines()
             if l.strip() and not l.startswith("#") and "代码" not in l]

    records = []
    for line in lines:
        parts = re.split(r'[,\s\t]+', line)
        if len(parts) >= 5:
            try:
                ret = float(parts[1].replace('%', ''))
                r2 = float(parts[3])
                turnover = float(parts[4].replace('%', ''))
                records.append((ret, r2, turnover))
            except:
                pass

    valid_return = [r for r in records if 8 <= r[0] <= 20]
    scores["valid_return"] = 1.0 if len(valid_return) == len(records) and len(records) > 0 else (0.5 if len(valid_return) > 0 else 0.0)

    valid_r2 = [r for r in records if 0 < r[1] <= 1.0]
    scores["r_squared_valid"] = 1.0 if len(valid_r2) == len(records) and len(records) > 0 else (0.5 if len(valid_r2) > 0 else 0.0)

    valid_turnover = [r for r in records if 3 <= r[2] <= 8]
    scores["turnover_valid"] = 1.0 if len(valid_turnover) == len(records) and len(records) > 0 else (0.5 if len(valid_turnover) > 0 else 0.0)

    transcript_str = str(transcript).lower()
    scores["regression_used"] = 1.0 if any(kw in transcript_str for kw in
        ["linear.*regress", "线性回归", "polyfit", "linregress", "r.*squared", "r_squared", "r²"]) else 0.0

    return scores
```

---

## LLM Judge Rubric

### Criterion 1: 连续上涨条件检测（Weight: 30%）

**Score 1.0**: 正确检测10天连续上涨（每天均高于前一天），每日涨幅严格在0.5%-4%区间（不包含端点或包含均可，需说明），无任何一天涨幅超范围。
**Score 0.75**: 连续性和涨幅范围检测基本正确，边界处理略有差异。
**Score 0.5**: 只检查了整体10日涨幅，未检查每天的日涨幅范围。
**Score 0.25**: 连续上涨判断有明显漏洞（如允许某天收平）。
**Score 0.0**: 未实现连续上涨判断。

### Criterion 2: 线性回归实现（Weight: 35%）

**Score 1.0**: 正确使用线性回归对10天成交量序列拟合（x=时间序号，y=成交量），计算斜率（正斜率代表放量）和R²（拟合优度），R²>0.6的筛选条件正确应用。
**Score 0.75**: 线性回归实现基本正确，R²计算有轻微偏差（如用皮尔逊相关系数平方代替）。
**Score 0.5**: 用了其他方法替代线性回归（如手动计算斜率但未算R²）。
**Score 0.25**: 未用线性回归，只判断了成交量是否递增。
**Score 0.0**: 未进行成交量趋势分析。

### Criterion 3: 换手率与综合筛选（Weight: 35%）

**Score 1.0**: 正确获取或计算换手率，平均换手率3%-8%的筛选条件准确应用，10日累计涨幅8%-20%条件也正确实现，四个条件全部AND关系正确。
**Score 0.75**: 换手率计算基本正确，但来源可能不准确（如用成交量/总股本而非流通股本）。
**Score 0.5**: 换手率条件有实现但计算方法有误，或四个条件的AND关系有误（用OR）。
**Score 0.25**: 换手率条件未实现或严重错误。
**Score 0.0**: 未进行换手率筛选。
