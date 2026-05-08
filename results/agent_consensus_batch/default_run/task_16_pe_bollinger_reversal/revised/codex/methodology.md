# Revised Methodology

- Target date: `2024-08-15`.
- Revision goal: separate the blocker for PE fundamentals from the blocker for OHLCV history instead of treating all market data as unavailable.
- Real-data probes used hard subprocess timeouts so hanging vendors do not make the run non-deterministic.
- PE sources probed:
  - `akshare.stock_zh_a_spot_em` for market snapshot fields including PE when available.
  - `tushare.daily_basic` for `pe`/`pe_ttm` on `2024-08-15`.
- K-line source probed:
  - `mootdx.bars` for `300750` with a lookback large enough to cover `2024-08-15`.
- This revision still refuses to synthesize PE from price or EPS heuristics because that would break the task's first step.

## Probe Summary

```json
{
  "akshare_pe": {
    "ok": false,
    "source": "local_probe",
    "detail": "ConnectionError: HTTPSConnectionPool(host='82.push2.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f12&fs=m%3A0+t%3A6%2Cm%3A0+t%3A80%2Cm%3A1+t%3A2%2Cm%3A1+t%3A23%2Cm%3A0+t%3A81+s%3A2048&fields=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6%2Cf7%2Cf8%2Cf9%2Cf10%2Cf12%2Cf13%2Cf14%2Cf15%2Cf16%2Cf17%2Cf18%2Cf20%2Cf21%2Cf23%2Cf24%2Cf25%2Cf22%2Cf11%2Cf62%2Cf128%2Cf136%2Cf115%2Cf152 (Caused by NameResolutionError(\"<urllib3.connection.HTTPSConnection object at 0x17fecb110>: Failed to resolve '82.push2.eastmoney.com' ([Errno 8] nodename nor servname provided, or not known)\"))",
    "rows": null,
    "columns": []
  },
  "tushare_pe": {
    "ok": false,
    "source": "local_probe",
    "detail": "ConnectionError: HTTPConnectionPool(host='api.waditu.com', port=80): Max retries exceeded with url: /dataapi/daily_basic (Caused by NameResolutionError(\"<urllib3.connection.HTTPConnection object at 0x126c56ba0>: Failed to resolve 'api.waditu.com' ([Errno 8] nodename nor servname provided, or not known)\"))",
    "rows": null,
    "columns": []
  },
  "mootdx_bars": {
    "ok": false,
    "source": "local_probe",
    "detail": "timeout after 20s",
    "rows": null,
    "columns": []
  }
}
```
