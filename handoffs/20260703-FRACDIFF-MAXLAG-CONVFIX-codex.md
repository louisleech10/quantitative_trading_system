# fracdiff max_lag convfix — Codex

task-id: fracdiff-maxlag-convfix-codex-20260703
date: 2026-07-03

## 修改檔案清單

- `momentum/FeatureEngineering/preprocessing/_hurst_prior.py`
  - `_convolve_1d()` 移除 SciPy `fftconvolve` 自動分支與 threshold，fracdiff convolution 一律走 `np.convolve(mode="valid")`。
  - 註解標明 MRFAIL-RECONCILE 裁決：FFT tail roundoff leaks into prefix bins。
- `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`
  - `test_fracdiff_truncation_invariant` 掛新的 `pytest.mark.xfail(strict=True)`，reason 指向 B1 materialization 精度路徑、idx508 artifact、storage codec/精度 epic。
  - `test_fracdiff_tail_perturbation_invariant` 未掛 xfail。
  - helper、assertion body、`FRACDIFF_ATOL`、NaN mask gate 未改。

## 五欄收尾

ASSUMPTIONS_VERIFIED:
- `_convolve_1d` repo caller 僅 `fractional_difference_values()`，即 fracdiff 路徑；未發現其他 caller 需要保留 FFT 行為。
- 現行 direct fracdiff tail-perturb experiment prefix drift 精確 `0`；同一實驗 FFT prefix drift 約 `1.3248335761772978e-10`。

TESTS_RUN:
- `source venv/bin/activate && python - <<'PY' ... tail perturb experiment ... PY` PASS；`current_direct_prefix_drift=0`、`current_direct_exact_zero=True`、`fft_prefix_drift=1.3248335761772978e-10`。
- `source venv/bin/activate && pytest tests/feature_engineering/preprocessing/test_hurst_prior.py -q` PASS；5 passed。
- `source venv/bin/activate && pytest tests/feature_engineering/test_fracdiff_maxlag_derivation.py tests/feature_engineering/test_dstar_cache_key_mutation.py -q` PASS；15 passed。
- `git diff --check -- momentum/FeatureEngineering/preprocessing/_hurst_prior.py tests/feature_engineering/test_ff_fullchain_truncation_mr.py` PASS。

FAILURES_SEEN:
- none in this task.

SCOPE_CHANGES:
- none. Slow fullchain MR intentionally not run per instruction.
- Worktree had pre-existing uncommitted changes before this task, including broader max_lag/test changes; this task only added the convfix and updated the B1 xfail reason/placement.

NUMERIC_OR_SCHEMA_IMPACT:
- Numeric impact: fracdiff convolution now uses direct convolution for all sizes, removing FFT roundoff drift in prefix bins. No tolerance/atol relaxation.
- Schema/output-size impact: none.

STATUS: DONE
