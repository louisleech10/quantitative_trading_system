# 20260622 MTF direction consultation (Codex)

Scope: read-only quant strategy assessment; no product code/tests changed.

## Position
- Claude's macro view is mostly correct: coarse->fine is the dominant discretionary/systematic MTF pattern; fine->coarse exists, but usually through compressed/aggregated high-frequency descriptors.
- For primary 12h/1d with source 1h/4h, default design should be aggregation-first, not native 1h rolling for every fine feature.
- Current native-tf slow path is valid as an expressiveness backstop, but it should not be treated as the common/default alpha path.

## Why
- Low-frequency decisions need state summaries over the decision interval: realized vol, signed vol, intraday range, drawdown/recovery, VWAP/volume profile, imbalance, liquidity, jump counts, regime persistence.
- Keeping full native rolling transforms is only justified when the alpha depends on path order/shape before aggregation, not just interval totals/extrema.
- Rolling winsor over 20,352 native 1h rows for 12h/1d decisions looks more like preprocessing architecture generality than standard daily/12h alpha construction.

## Fine->coarse use cases needing native-ish high-frequency structure
- Volatility forecasting: HAR/MIDAS-style lag kernels over intraday/daily realized measures.
- Microstructure/order-flow: persistent taker imbalance, VPIN-like toxicity, liquidity droughts, spread/depth proxies.
- Intrabar path dependence: reversal after shock, time-under-water, first-half vs second-half asymmetry, late-session drift, jump clustering.
- Barrier/stop-risk features: whether fine path breached levels that coarse OHLC summary may hide.
- Crypto-specific 24/7 regimes: funding-window behavior, liquidation cascades, Asia/US session decomposition.

## B7 recommendation
- Do not ship B7 as originally scoped "parallelize native-tf slow path" yet.
- First run an alpha-design decision: define a small aggregation feature family and compare IC/ML lift against native-tf features under identical splits.
- Keep native-tf correctness and maybe selective kernels, but demote broad native-tf optimization to P2 unless evidence shows material lift.
- If B7 continues, current microbench says ThreadPool gives ~1.0x until relevant numba kernels use/prove nogil; Scheme B/algorithmic aggregation likely has higher ROI.

ASSUMPTIONS_VERIFIED: Read HANDOFF/CLAUDE and B7/L6.5 profiling handoffs; checked published mixed-frequency/realized-vol framing.
TESTS_RUN: none(read-only consultation).
FAILURES_SEEN: none.
SCOPE_CHANGES: none; added only this handoff file as requested.
NUMERIC_OR_SCHEMA_IMPACT: none.
STATUS: DONE
