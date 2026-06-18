# 20260618 L65 B3b Codex Signoff

## A 清理結果
- `feature_preprocessor.py`: 移除 winsor sigma/quantile 4 處 `causal_preprocessing else` 死分支；保留 causal rolling 路徑。
- `test_batch2d_dstar_align.py`: 刪除零 caller `_assert_per_column_exact` helper。
- grep: `if self.causal_preprocessing` / `_assert_per_column_exact` 指定殘留 = 0。

## B 獨立資料正確性簽核
- 新增 `scripts/signoff_l65_b3b_codex.py`；只讀 `data_cache/feature_klines/kline_cache.h5`。
- 覆蓋: 10 symbols × 3 TF = 30 datasets；每組 tail 720 rows × 14 generated cols。
- IC-First byte parity: `scripts/build_l65_golden_baseline.py --check` PASS，6 symbol×tf stable。
- causal PIT: 30/30 PASS；外部 False == True；tail 48 bars tamper，過去 624 rows max_abs_diff=0。
- multi-TF merge: native TF L6.5 → 1h ffill；2000 value-conservation comparisons，0 mismatch。
- split no leakage: 10 symbols PASS；train rows total=5760，merged cols=42。
- cross symbol/TF isolation: schema/dtype consistent across 30 datasets；shared instance ADA→BCH == clean BCH。
- NaN/Inf gate: output inf=0；injected NaN preserved；10 injected Inf positions -> 7 finite, 3 NaN, none Inf。
- Codex 簽核: 資料正確。

## 驗證
- PASS: `PYTHONPYCACHEPREFIX=/tmp/codex_pycache ./venv/bin/python -m py_compile ...`
- PASS: `PYTHONPYCACHEPREFIX=/tmp/codex_pycache ./venv/bin/python scripts/signoff_l65_b3b_codex.py --json-out results/l65_b3b_codex_signoff.json`
- PASS: `PYTHONPYCACHEPREFIX=/tmp/codex_pycache ./venv/bin/python scripts/build_l65_golden_baseline.py --check`
- PARTIAL: `PYTHONPYCACHEPREFIX=/tmp/codex_pycache ./venv/bin/python -m pytest tests/feature_engineering/test_batch2d_dstar_align.py tests/feature_engineering/preprocessing/ -q`
- pytest result: 184 passed, 1 skipped, 4 failed in 944.60s。
- pytest failures: 4 joblib/loky slow-path parallel tests failed at `os.sysconf("SC_SEM_NSEMS_MAX")` with sandbox `PermissionError`; unrelated to B3b diff。

## 待辦 / 阻塞 / 踩坑
- 待 Claude 在非受限 sandbox 或有 multiprocessing semaphore 權限環境重跑 4 個 slow-path parallel tests。
- `results/l65_b3b_codex_signoff.json` 為 ignored local artifact，未納入 commit。
- 未修改/提交 `data_cache/`；未納入既存 `tests/golden/l65/fast_adf_gate_report.json` 修改。
