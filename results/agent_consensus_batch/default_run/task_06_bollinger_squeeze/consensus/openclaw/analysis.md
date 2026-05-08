# Consensus Analysis - Task 06 Bollinger Squeeze

## Results Comparison

| Agent | Count | Ratio | Implied Total | Consistency | Code Files | Has Target File |
|-------|-------|-------|---------------|-------------|------------|-----------------|
| ga | 6 | 0.45% | 1333 | ✓ PASS | 0 | ✓ |
| codex | 251 | 18.00% | 1394 | ✓ PASS | 0 | ✓ |
| claudecode | 2 | 0.15% | 1333 | ✓ PASS | 4 | ✓ |
| openclaw | 209 | 15.00% | 1393 | ✓ PASS | 1 | ✓ |

## Key Observations

1. **All agents produced valid output files** with correct format
2. **All agents pass consistency check** (implied total within 800-2000 range)
3. **Massive variance in results**: 2 to 251 stocks (125x difference)
4. **Two clusters emerge**:
   - Low count: ga (6), claudecode (2)
   - High count: codex (251), openclaw (209)

## Analysis

The 5% threshold for Bollinger Band width is: `(upper - lower) / middle < 0.05`

The extreme variance suggests different interpretations or calculation methods:

- **Low results (2-6)**: Very strict squeeze detection, possibly stricter threshold or different calculation
- **High results (209-251)**: More lenient detection, ~15-18% of ChiNext stocks

Given that:
- Bollinger squeeze is relatively rare (typically <10% of stocks)
- The task explicitly defines the formula and 5% threshold
- Both high-count agents (codex, openclaw) show similar results (~15-18%)
- Both low-count agents show extremely low results (<0.5%)

## Recommendation

**Prefer: codex or openclaw** (high-count cluster)

Reasoning:
1. **Convergence**: codex (251) and openclaw (209) are close (42 stock difference)
2. **Reasonable proportion**: 15-18% is plausible for a 5% bandwidth threshold
3. **Code evidence**: openclaw has executable Python code showing methodology
4. **Consistency**: Both high-count agents independently arrived at similar conclusions

Between codex and openclaw:
- **codex**: 251 stocks (18.00%), no visible code in summary
- **openclaw**: 209 stocks (15.00%), has bollinger_revised.py showing approach

**Final choice: codex** - slightly higher count but both are in the same ballpark. The 18% vs 15% difference could be due to data source or edge cases in calculation.
