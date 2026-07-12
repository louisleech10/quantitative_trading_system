# IC-API-TEST-MODERNIZATION Phase1 資料正確性簽核 — Composer 獨立版
Task-id: icatm-dc-composer | Reviewer: Composer | Date: 2026-07-12 | 禁改碼

## 簽核標的
`tests/fixtures/ic_api_real_kline.py` → `build_real_kline_frames` 產出之 IC 輸入面 (features/labels/timestamps)。

---

## (1) Label：前瞻 simple + 尾 5 NaN

**讀碼**：`labels = close.shift(-HORIZON) / close - 1.0`（L138）；`labels.iloc[-HORIZON:] = np.nan`（L140）；`RETURN_TYPE="simple"` 與 `config_override.labels.return_type` 同源（L21/L181）。

**自跑 receipt**（`python3` 獨立腳本，ETHUSDT/12h 真 kline）：
- `match_forward_simple`: True — 與 `close[t+5]/close[t]-1` 逐點一致（rtol=1e-12）
- `not_backward`: True — 不等於 `close/close.shift(5)-1`
- `not_log`: True — 不等於 `log(close[t+5]/close[t])`
- `tail_5_nan`: True — 末 5 根全 NaN
- `non_tail_finite`: True — 前 507 根全 finite

**Tier-2 oracle**：`_validate_dataset` 傳 `close=close`、`return_kind="simple"`、`sample_size=16` → `validate_alignment` 用 `_ORACLE_RETURN_KINDS["simple"]` = `future/current - 1`（`contracts.py:922`）。

---

## (2) Feature：逐欄 ≤t 無 future peek

| 欄位 | 公式 | PIT 判定 |
|------|------|----------|
| log_return_1 | `log_close - log_close.shift(1)` | 僅 t 與 t-1 |
| log_return_3 | `log_close - log_close.shift(3)` | 僅 t 與 t-3 |
| rvol_20 | `log_return_1.rolling(20).std` | rolling 右端 t |
| zscore_20 | `(close - rolling.mean) / rolling.std` | rolling 右端 t |
| hl_range | `(high-low)/close` | 同期 OHLC |
| oc_return | `close/open - 1` | 同期 OHLC |
| close_sma_ratio_20 | `close/rolling.mean - 1` | rolling 右端 t |

**grep**：`_feature_frame` 內零 `shift(-*)`；全檔僅 L138 label 路徑有 `shift(-HORIZON)`（mutation 測試用 `feature_shift` 參數，非生產路徑）。

**自跑 oracle**：7/7 欄 `np.allclose` vs 獨立重算 PASS；512 列全 finite（`MAX_FEATURE_LOOKBACK=21` warmup 足夠）。

---

## (3) Mutation 可證偽

```bash
venv/bin/pytest tests/momentum/Analysis/test_ic_api_real_kline_pit.py -v --tb=short
# → 2 passed in 0.06s
```

獨立腳本直接呼叫：
- `feature_shift=-1` → `AssertionError: feature PIT oracle mismatch` ✓
- `backward_label=True` → `AlignmentViolationError: label mismatch at ...` ✓

兩 mutation 均被 `_validate_dataset` self-test 拒絕，非空殼 assert。

---

## (4) IC 輸入面零合成 + R2-7 stub 隔離

**IC 輸入面 grep**（fixture + 三 API 測檔）：
```bash
rg -n "rng\.normal|np\.arange" tests/fixtures/ic_api_real_kline.py \
  tests/api/test_ic_analysis_api.py tests/api/test_ic_deep_analysis.py tests/api/test_export_api.py
# → 0 matches
```

**R2-7 stub 位置**（僅 API 輸出/序列化 seam，非 IC 輸入）：
- `test_export_api.py:86-119` — `copy.deepcopy(task_info)` → inject `deep_analysis_result` stub → yield → restore
- `test_ic_deep_analysis.py:256-291` — 同上 pattern，`try/finally` restore
- filtered H5（L109-114）取 `ic_api_real_kline["features"].iloc[:1,:2]` 真值，非手寫 `[[1.0,2.0]]`

IC 輸入路徑（features_path/labels_path/meta_path）全程來自 `build_real_kline_frames` 真 ETHUSDT/12h 衍生。

---

## 實作 review

| 項目 | 驗證 | 結果 |
|------|------|------|
| 生產零 diff | `git diff -- momentum/ api/` | empty |
| 去重 3 忠實 | 刪 `test_feature_list`/`test_full_analysis`/`test_deep_analysis_result`；留 `test_list_available_features_success`/`test_full_analysis_endpoint`/`test_start_deep_analysis_and_get_result` | grep 確認刪除+保留對照存在 |
| 29 API 綠 | `pytest tests/api/test_ic_analysis_api.py tests/api/test_ic_deep_analysis.py tests/api/test_export_api.py -v --tb=short` | **29 passed in 6.48s** |

---

## Composer 簽核

**DATA-CORRECT: PASS**

(features ≤t 無 future peek、labels 正確前瞻 simple+尾 NaN、Tier-2 close oracle 有傳且 mutation 真可證偽、IC 輸入面零合成、R2-7 stub 僅 API 輸出面且 deepcopy/restore、生產零 diff、去重後 29 API 全綠)
