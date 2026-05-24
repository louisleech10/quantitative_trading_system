# Feature Developer Checklist

> Required pre-flight checks before adding a new L1 atomic engine, L2 operator,
> or modifying L3 / L6.5 aggregation logic. Saves you from the kind of
> ratio-style NaN poisoning documented in
> [NAN_POISONING_INVESTIGATION.md](./NAN_POISONING_INVESTIGATION.md).

## When to use this checklist

| Scenario | Run checklist? |
|---|---|
| New L1 atomic engine (e.g. new TA-Lib indicator group) | **Yes** |
| New L2 derived operator (e.g. `Slope`, `Vol-Adjusted`) | **Yes** |
| New L3 aggregator function | **Yes** |
| New L6.5 preprocessing step | **Yes** |
| New L1 indicator within an existing category (e.g. add EMA-100 to trend) | No |
| Config-only changes in `scan_config.yaml` | No |
| Frontend / API changes | No |

---

## L1: New atomic engine

### 1. Output domain
- [ ] Document the value domain in the engine docstring:
      `discrete {-1, 0, 1}` / `discrete {-100, 0, 100}` / `continuous bounded [0, 1]` / `continuous unbounded`
- [ ] Document expected sparsity: % of bars expected to be exactly zero
- [ ] If sparsity > 80% or output is discrete with ≤ 5 distinct values:
  - [ ] Add the category to `RATIO_UNSAFE_CATEGORIES` in
        `momentum/FeatureEngineering/operators/derived_operators.py`
  - [ ] Update `/memories/repo/ratio_unsafe_categories.md` decision flow

### 2. Naming convention
- [ ] L1 column names must follow `<source>_<category>_<indicator>[_param1[_param2]]`
- [ ] `source` segment must match a key in `raw_data` (close / high / volume / ohlc / etc.)
- [ ] `category` segment must be a single lowercase word (trend / momentum / pattern / cycle / volume / volatility / overlap)
- [ ] Verify `_parse_feature_name` correctly extracts category by running:
      ```python
      DerivedOperatorEngine(None)._parse_feature_name("your_col_name")
      ```

### 3. Quality guards
- [ ] Engine never returns columns with > 90% NaN on healthy input (test on BTCUSDT 1h ≥ 4000 bars)
- [ ] Engine never returns columns with `inf` / `-inf` values
- [ ] Engine never returns constant columns (std = 0) on healthy input
- [ ] If your engine can legitimately produce sparse columns (e.g. event-style
      flags), test what happens when fed through L2 Momentum / Distance /
      WorldQuant — if NaN rate explodes, blacklist your category (see step 1)

---

## L2: New derived operator

### 1. Ratio-style operator (any formula with `/`, `(x - shift) / shift`, etc.)
- [ ] Add `if info.category in RATIO_UNSAFE_CATEGORIES: continue` in BOTH:
  - [ ] Your `_collect_*_specs` method (selection-time guard)
  - [ ] Your `_apply_*` method (computation-time belt-and-suspenders)
- [ ] Choose the divisor protection strategy:
  - For unbounded numerators: `shifted.replace(0, np.nan)`
  - For known-positive numerators: `np.where(shifted > eps, x / shifted, np.nan)` with eps = 1e-12
- [ ] Document the formula in the operator's docstring including the
      degenerate case behavior (division by zero, NaN propagation)

### 2. Diff-style operator (subtraction, `x - shifted`)
- [ ] Generally safe; no guard required for sparsity (subtraction of zeros = 0,
      not NaN), but still avoid if the *interpretation* is meaningless on
      discrete inputs (e.g. "rolling diff of CDLDOJI" is nonsense)
- [ ] Document expected behavior on the unsafe categories

### 3. Naming
- [ ] Output column name pattern: `{l1_col}_{OperatorName}[_param]`
  (e.g. `close_trend_SMA_20_Momentum_L5`)
- [ ] Verify L3 `_select_columns` correctly identifies category from your
      output name by running:
      ```python
      _is_ratio_unsafe_column("your_l2_output_name")
      ```

---

## L3: New aggregator or rolling-config change

### 1. Aggregator function
- [ ] Function operates element-wise within a window; no peeking at future
      values (use `min_periods` correctly)
- [ ] Returns NaN for windows with `effective_n < _VARIANCE_FILTER_MIN_EFFECTIVE_N`
      (= 30); the filter handles this but your aggregator must not crash
- [ ] No `inf` outputs for any valid input (e.g. `zscore` divides by std →
      guard with `np.where(std > 0, ..., np.nan)`)

### 2. New windows
- [ ] Largest window `≤ len(data) / 4` to leave room for downstream
      `min_periods` and avoid all-NaN heads
- [ ] Total `len(windows) × len(aggregators)` stays manageable
      (current default: 10 × 10 = 100; do not exceed 200 without
      benchmarking memory)

### 3. `_select_columns` changes
- [ ] If you change the column-selection logic, preserve the
      `_is_ratio_unsafe_column` filter — it's the only L3 protection against
      pattern-category leakage

---

## L6.5: New preprocessing step

### 1. Entry guard
- [ ] If your step has its own `apply_to` selection, route through the same
      `_is_ratio_unsafe_column` helper as other steps
- [ ] Do NOT bypass the top-level `transform()` guard with a new entry point;
      add your step inside `_transform_single` instead

### 2. Numerical guards
- [ ] Your step never produces `inf` / `-inf` (use `np.where` or explicit clipping)
- [ ] Your step never produces all-NaN columns from non-empty input
- [ ] Your step preserves the input index exactly (no row dropping)

### 3. Reversibility
- [ ] Document whether your step is invertible (`winsorize`: no, `zscore`: yes
      with stored mean/std, `fracdiff`: no, `rank`: no)
- [ ] If non-invertible, log a single INFO line at fit time showing the
      parameters used (e.g. mean / std / clip bounds)

---

## Cross-cutting

### Test data
- [ ] Use real kline from `data_cache/feature_klines/kline_cache.h5`
- [ ] Minimum sample size: 4000 bars (covers L3 window=720 cleanly)
- [ ] Symbols to spot-check: `BTCUSDT`, `ETHUSDT` (high liquidity, clean data)

### Verification script template
```python
# Modeled on scripts/verify_nan_poisoning_fix.py
def test_my_new_engine():
    raw = _load_btcusdt_1h(n=4000)
    out = MyNewEngine(config={}).compute_all(raw)

    assert (out.isna().mean() > 0.9).sum() == 0, "high-NaN output"
    assert not out.isin([np.inf, -np.inf]).any().any(), "inf output"
    assert (out.std() > 0).all(), "constant column"
```

### Decoupling
- [ ] No `from api.*` imports in `momentum/` — use `from momentum.core.logging import get_logger`
- [ ] If your new engine needs cross-domain dependencies, define a Protocol in
      `momentum/core/protocols.py` and inject via `momentum/factories.py`
- [ ] Tests live under `tests/` and run without `run_api.py`

### Code review focus points
1. **Sparsity audit**: For every new L1 engine, ask "what % of outputs are exactly zero on healthy data?" If >50%, this is a `RATIO_UNSAFE_CATEGORIES` candidate.
2. **Naming sanity**: Run `_parse_feature_name` on a few sample output names; assert `category` is what you expect.
3. **L3 leak check**: After your L1/L2 change, run `scripts/verify_nan_poisoning_fix.py` and confirm pattern-leak counts remain 0.
4. **Quality dashboard delta**: Compare `data_cache/features/.../quality_dashboard.json` before/after; high-NaN count must not regress.
