# fracdiff max_lag MR failure diagnosis — Composer

task-id: fracdiff-maxlag-mrfail-composer-20260703  
role: read-only diagnostic leg (Q1–Q3)  
facts input: `handoffs/20260703-FRACDIFF-MAXLAG-MRFAIL-FACTS.md`  
slow receipt: `handoffs/run_receipts/20260703T054245Z-fracdiff-maxlag-mr-green.log`

---

## Q1 / B1 — warmup NaN mask on non-fracdiff MACDEXT momentum column

### Observed

`test_fracdiff_truncation_invariant` fails at:

`warmup 1h_L2_Momentum_chunk4.parquet::volume_1h_momentum_MACDEXT-Hist_13-55-13_Momentum_L144 NaN mask mismatch`

(receipt `20260703T054245Z-fracdiff-maxlag-mr-green.log:8542-8543`; helper chain `ff_truncation_mr_helpers.py:1142→894→728`)

Window lengths: full **2081** bars, trunc **2071** bars (`_fracdiff_window_bars()` = `max(600, warmup+30)` → 2081 per facts §2).

### Mechanism trace (with line evidence)

**1. What the assertion checks**

Fracdiff MR calls `_assert_warmup_nan_masks_equal()` on **all** parquet columns (not only `_fracdiff`), after fracdiff-only value gate:

```1131:1147:tests/feature_engineering/ff_truncation_mr_helpers.py
def _assert_fracdiff_truncation_invariants(pair: TruncationPair) -> None:
    ...
    _assert_warmup_nan_masks_equal(
        pair.full.raw_dir,
        pair.trunc.raw_dir,
        warmup=pair.warmup,
        n_trunc=pair.n_trunc,
    )
```

NaN mask must be **exact** (`np.array_equal` on `isnan` masks) at `ff_truncation_mr_helpers.py:726-728`.

**2. Fracdiff MR config — ADF differencing is OFF**

```217:231:tests/feature_engineering/ff_truncation_mr_helpers.py
        "preprocessing": {
            ...
            "adf_differencing": {"enabled": False},
            "fractional_differencing": {
                "enabled": True,
                ...
                "apply_to": "non_stationary",
            },
```

→ **`_apply_adf_differencing()` (`feature_preprocessor.py:3306-3373`) is not invoked** in this MR. Claude-leg hypothesis「ADF 決策 tail-slice 翻面 → diff 欄位 NaN band 變」**不適用於 B1 失敗欄**（該欄無 `_diff` 後綴，且 ADF step disabled）。

**3. Fracdiff append mode does not replace originals**

```3001:3010:momentum/FeatureEngineering/preprocessing/feature_preprocessor.py
    def _assign_fracdiff_result(...):
        if mode == "replace":
            result[column] = fracdiff_series
        else:
            result[f"{column}_fracdiff"] = fracdiff_series
```

MR uses `mode: "append"` (`ff_truncation_mr_helpers.py:219`). Failed column has no `_fracdiff` suffix → **not a fracdiff output column**.

Registry slow-path append writes originals back unchanged in intent:

```1839:1842:momentum/FeatureEngineering/preprocessing/feature_preprocessor.py
            orig_cols = list(getattr(group, "columns"))
            orig_array = processed_df[orig_cols].to_numpy(dtype=np.float32, copy=False)
            registry.overwrite_data(group_id, orig_array)
```

**4. L2 MACDEXT momentum is causal prefix math**

```576:586:momentum/FeatureEngineering/operators/derived_operators.py
        for lag in lags:
            shifted = selected.shift(lag)
            denom = safe_denominator(shifted)
            momentum = (selected - shifted) / denom
            momentum.columns = [f"{col}_Momentum_L{lag}" for col in selected_cols]
```

No `len(df)` in this path; theoretically identical kline prefix → identical L2 prefix.

**5. Task 1.4 len(df)→max_lag scan — NOT overturned**

Resolver (only auto derivation site):

```3020:3025:momentum/FeatureEngineering/preprocessing/feature_preprocessor.py
    def _resolve_fracdiff_max_lag(self) -> int:
        ...
        return min(max(2, self._calibration_bars() // 10), 252)
```

`_calibration_series()` uses `min(len(series), calibration_bars)` (`:180-182`) — **prefix clip, not tail/總長耦合**; intentional for d* calibration.

`grep len(df)` in fracdiff hot path: only comment at `:3204`. **No second len(df)→max_lag 推導點** found in `feature_preprocessor.py` / `_slow_path_parallel.py` / `_hurst_prior.py`.

**6. Materialization path (still in play for NaN↔finite flips)**

- Raw-sink coerces to float32 before L7 write: `feature_preprocessor.py:421-422`
- Layer B sanitize: `feature_storage.py:901-906` → `numeric_guards.py:61-87` (non-finite or `|v|>finite_cap` → NaN; cap=1e18 in receipt)
- Per-column float16/float32 parquet selection: `feature_storage.py:2554-2588`

Momentum ratio `inf → sanitize → NaN` in one window but not the other would produce **mask mismatch** without changing max_lag.

**7. ADF head/tail asymmetry exists but is irrelevant to B1**

Parallel fracdiff worker ADF uses **tail** slice:

```114:114:momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py
    sample = clean_values[-max(1, int(sample_size)) :]
```

Serial/fast path uses **head**:

```2996:2996:momentum/FeatureEngineering/preprocessing/feature_preprocessor.py
            return float(adfuller(pd.Series(clean_values).head(sample_size), autolag="AIC")[1])
```

Cheap check: same 600-point series → `head_p=0.950438`, `tail_p=0.942710` (differ). This affects **d\*** search only; 20260703 run **d\* gate passed**. Cannot explain NaN mask change on a **non-fracdiff L2 column**.

### Q1 conclusion

| Candidate | Verdict |
|-----------|---------|
| max_lag resolver / Task 1.4 len coupling | **Ruled out** for B1 (non-fracdiff column; scan intact) |
| adf_differencing decision chain | **Ruled out** (disabled in MR config) |
| fracdiff direct column mutation | **Ruled out** (append mode) |
| Layer B sanitize over-cap (1e18) | **Unlikely** for MACDEXT momentum scale; not disproved |
| float32 raw-sink / float16 parquet codec | **Plausible** (finite↔NaN flip at margin) |
| Upstream L1/L2 prefix divergence when fracdiff slow-path enabled | **Plausible**; needs first-mismatch index from artifacts |

**Root cause status:** narrowed to **pre-existing materialization or upstream prefix path**, not epic max_lag resolver. **First differing bar index not located** (full-chain artifact dump aborted after ~2 min; same class of failure as pre-fix run but assertion layer was d\* then).

**Recommended next step (not done here):** byte-level diff `full` vs `trunc` parquet for that column → classify mismatch index as (a) still in MACD momentum warmup band, (b) sanitize boundary, (c) pre-L6.5 L2 value divergence.

---

## Q2 / B2 — single-element fracdiff prefix drift 4.77e-07

### Observed

`test_fracdiff_tail_perturbation_invariant` fails at:

`fracdiff values 1h_L1_statistics_VAR_L65.parquet::volume_1h_statistics_VAR_144_fracdiff`  
`Mismatched elements: 1/20`; `Max abs diff 4.7683716e-07`; gate `atol=1e-8`, `rtol=0`  
(receipt `20260703T054245Z-fracdiff-maxlag-mr-green.log:12040-12051`)

Compared segment: `[warmup:n_trunc)` with `n_trunc-warmup=20` → `warmup≈2051`.  
Failing pair: `1.117120e+00` vs `1.117119e+00` (index 8 within the 20-element segment → absolute bar ≈2059).

`d_star` gate **passed** on this run (failure is after `_assert_d_star_gate` at `ff_truncation_mr_helpers.py:1133`).

### Candidate evaluation

**A. Parallel n_jobs reduction non-determinism — LOW**

- `ParallelSlowPath.map()` (`_slow_path_parallel.py:67-98`): independent per-column workers, order-preserving list return; BLAS forced single-thread (`:35-41`).
- Cheap probe (5 columns, n=600, n_jobs=4): serial vs parallel `fracdiff_values` **identical** on finite cells (maxdiff only on all-NaN warmup).
- **Verdict:** not primary cause.

**B. float32 / float16 persistence + FFT convolution — HIGH**

Fracdiff compute chain:

```96:130:momentum/FeatureEngineering/preprocessing/_hurst_prior.py
def fractional_difference_values(...):
    ...
    convolution = _convolve_1d(filled_slice, weights)
```

```20:28:momentum/FeatureEngineering/preprocessing/_hurst_prior.py
def _convolve_1d(...):
    if _HAS_FFTCONV and signal.size * weights.size > _FFT_OPS_THRESHOLD:  # 4096
        return np.asarray(_scipy_fftconvolve(signal, weights, mode="valid"), dtype=np.float64)
```

For n≈2081, w=50: n×w≈104k → **always FFT** (`feature_preprocessor.py:103-105` documents same).

Persistence:

```421:422:momentum/FeatureEngineering/preprocessing/feature_preprocessor.py
            data_fp32 = np.asarray(data, dtype=np.float32)
```

Magnitude check: `|1.117120−1.117119| ≈ 8.4× float32 eps` (cheap probe confirmed).

Cheap synthetic experiments:

| Experiment | max prefix diff (float64) |
|------------|---------------------------|
| tail perturb last 10 bars, same length 2081 | ~1.8e-10 |
| full 2081 vs trunc 2071 windows | ~1.8e-10 |
| small-magnitude (~1.1) full vs trunc segment [2051:2071) | ~2.6e-16 |

Synthetic FFT drift **smaller** than observed 4.77e-7, but real pipeline includes **VAR rolling → fracdiff on production scales → float32 sink**. Observation is still **ULP-scale single cell**, inconsistent with causal tail leakage pattern.

**C. True causal / look-ahead leakage — LOW**

- Tail perturb applies only to last `TRUNC_K=10` OHLCV bars (`ff_truncation_mr_helpers.py:1385-1390`).
- Bar ~2059 lookback 50 → does not include perturbed tail (2061+).
- d\* identical across windows.
- Leakage would expect **systematic** post-warmup drift, not 1/20 cells.
- **Verdict:** cannot exclude without dedicated VAR replay, but **inconsistent with evidence**.

### Q2 conclusion

**Primary:** numerical path — **FFT full-series convolution sensitivity to series length** (2081 vs 2071) plus **float32 persistence**, manifesting at ~1 ULP for O(1) values under strict `atol=1e-8`.  
**Not primary:** joblib parallel reduction.  
**Low probability:** true causal leakage.

**Repair direction (no helper relaxation):**

1. MR/deterministic mode: bypass FFT in `_convolve_1d` / `_frac_diff_convolve` when `FF_STRICT_CAUSAL=1` or test env flag; or
2. Keep float64 through fracdiff columns until parquet write for strict gates; or
3. Documented committee decision if production keeps FFT — **not** silent `atol` widen.

---

## Q3 — epic-introduced vs pre-existing (xfail-masked)

### Criteria applied

1. Were warmup/value assertions **reachable** before max_lag fix?
2. Does main MR (fracdiff/adf **off**) cover the same column/check?
3. Is failure morphology consistent with max_lag 60→50 **value overhaul**?

### Evidence

| Artifact | Finding |
|----------|---------|
| `9d87d68` | `test_fracdiff_{truncation,tail}_invariant` added with **strict xfail**; reason = `len(df)//10` max_lag breaks truncation |
| `20260702T042627Z-ff-b2-regression.log` | **8 passed, 2 failed**; both fracdiff tests fail at **`d_star mismatch`** (`:6384-6385`, `:9867-9868`) — **warmup/values assertions never reached** |
| `20260703T054245Z-fracdiff-maxlag-mr-green.log` | d\* gate **passes**; failures at warmup mask (B1) and fracdiff values (B2) |
| Main MR config | `adf_differencing`/`fractional_differencing` **disabled** (`ff_truncation_mr_helpers.py:200-201`); **8/8 passed** 20260702 |
| B1 morphology | Non-`_fracdiff` column → **not** explained by max_lag width change alone |
| B2 morphology | Single-element 4.77e-7 → **not** typical of d\* grid flip (would change entire fracdiff series shape) |

### Q3 conclusion

**Both B1 and B2 are pre-existing behaviors first exposed when xfail removed / d\* gate green after max_lag epic — not introduced by the calibration-derived resolver itself.**

Epic still **changes all fracdiff values by design**; these surfaced failures must be **in epic signoff scope** before FF regeneration for IC.

**Task 1.4 scan conclusion stands** for len(df)→max_lag: no additional production derivation found; B1/B2 are **outside** that specific defect class.

---

## Cheap experiments run

| Command / probe | Result |
|-----------------|--------|
| B2 ULP magnitude | `diff/eps ≈ 8.4` at ~1.117 |
| serial vs parallel `process_fracdiff_column_values` (5 cols, n=600) | identical on finite cells |
| ADF head vs tail on 600-pt series | p-values differ (0.950 vs 0.943) |
| FFT `fractional_difference_values` tail-perturb / full-vs-trunc | prefix drift O(1e-10) float64 in synthetic data |
| Full-chain B1 artifact diff | **Aborted** (runtime); not re-run |

---

## Structured closeout

```
ASSUMPTIONS_VERIFIED:
- fracdiff MR has adf_differencing.enabled=False (ff_truncation_mr_helpers.py:226).
- append mode does not replace original columns (feature_preprocessor.py:3007-3010).
- 20260702 failures stopped at d_star gate; 20260703 failures at warmup/values gates.
- _resolve_fracdiff_max_lag uses calibration_bars only (feature_preprocessor.py:3020-3025).
- parallel ADF tail vs serial ADF head both exist and can differ on identical input.

TESTS_RUN:
- python3 cheap probes (ULP, serial/parallel fracdiff, ADF head/tail, FFT prefix) — PASS
- Full-chain B1 parquet diff — NOT COMPLETED (time)

FAILURES_SEEN:
- none in probes; input failures from receipt 20260703T054245Z

SCOPE_CHANGES:
- none (read-only; only wrote this handoff)

NUMERIC_OR_SCHEMA_IMPACT:
- none from this diagnostic
```

STATUS: DONE

---

## Stamp review (task: fracdiff-maxlag-mrfail-stamp2-composer-20260703)

**Verdict:** APPROVED reconcile v2 (`handoffs/20260703-FRACDIFF-MAXLAG-MRFAIL-RECONCILE.md`).

| Check | Result |
|-------|--------|
| ① 收斂表 vs Composer 診斷 | PASS — B1=materialization/codec plausible（ADF/max_lag ruled out）；B2=FFT convolve HIGH；Q3=pre-existing；Task 1.4 不推翻 |
| ② 裁決案1 receipt | PASS — `passed=true`, `failures=[]`; cond1 BTC/ETH fracdiff+non_fracdiff=0; cond2 BTC 4546 / ETH 3435 fracdiff only; cond3 all 0; `resolved_max_lag=50`, `g1_actual_max_lag=208` |
| ③ 裁決案2 B1 xfail | PASS — reason 誠實（pre-existing、非 max_lag、未單行定位）；§New idx508 finite↔NaN 與候選表 float32/float16 codec plausible 相容 |
| ④ 裁決案3 簽核範圍 | PASS — B1 殘留/影響/與 max_lag 無關，IC 重生成前可見 |

Stamp appended to reconcile 戳記區.
