# Cross-Review Analysis: Task 28 Volatility Compression-Explosion

## Results Summary

| Agent | Stocks Found | Key Observation |
|-------|--------------|-----------------|
| **openclaw** (me) | 0 | No stocks met all 5 strict criteria |
| **codex** | 0 | No stocks met all 5 strict criteria |
| **claudecode** | 1 | 300123 (25 days compression, 8.3% amplitude) |
| **ga** | 109 | Many stocks found (10-21 days compression, 7.0-22.0% amplitude) |

## Critical Discrepancy

The **109 vs 0-1** split reveals a fundamental implementation difference:

### GA's Approach (109 stocks)
- Found many stocks with valid compression periods (≥10 days)
- All explosion amplitudes ≥7% (meets basic criteria)
- **Likely issue**: May not have strictly enforced the **HV10 percentile condition** (Condition 2)
  - Condition 2 requires: HV10 during compression ≤ 30th percentile of 60-day HV10 series
  - This is the most restrictive filter

### My Approach (0 stocks)
- Implemented all 5 conditions strictly
- Used correct HV10 formula: `std(log returns) × √252`
- Calculated 30th percentile of 60-day HV10 series
- **Possible issue**: May have been TOO strict or had a bug in the HV10 percentile check

### Codex (0 stocks)
- Same result as me, suggesting similar strict interpretation

### ClaudeCode (1 stock)
- Found 300123 with 25-day compression
- Middle ground between GA and openclaw/codex
- **Likely**: Correctly implemented HV10 percentile check but may have slightly different window logic

## Key Technical Question

**The HV10 percentile condition is the bottleneck:**

The task requires:
> 压缩期间的HV10降至近60日HV10序列的30分位数以下

This means:
1. Calculate HV10 for each day in a 60-day window before compression end
2. Find the 30th percentile of those ~60 HV10 values
3. Check if compression period's HV10 < this threshold

**Potential implementation differences:**
- How to calculate "compression period HV10" (minimum? average? last value?)
- Exact window for the 60-day HV10 series
- Whether to use rolling windows or fixed windows

## Suspected Issues in My Solution

1. **Too strict HV10 check**: I may have used the minimum HV10 during compression, which is very restrictive
2. **Window alignment**: The 60-day HV10 series calculation may have been too conservative
3. **Data availability**: With akshare fetching from 2024-07-01, I may not have had enough history for some stocks

## Suspected Issues in GA's Solution

1. **Missing HV10 percentile check**: The 109 stocks suggest this condition may not have been enforced
2. **Or**: Used a much more lenient interpretation (e.g., average HV10 instead of minimum)

## Recommendation

**Most likely correct answer: 1-10 stocks** (between ClaudeCode's 1 and GA's 109)

The truth is probably:
- GA over-counted by not strictly checking HV10 percentile
- I under-counted by being too strict or having a bug
- ClaudeCode's 1 stock is plausible but may also be under-counting

**Action needed**: Re-examine the HV10 percentile calculation logic and test with GA's 109 stocks to see which ones truly pass all conditions.
