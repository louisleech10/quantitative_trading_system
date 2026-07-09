# IC 1-align 獨立數據正確性簽核 — Composer

**task-id**: `ic1a-align-signoff`  
**agent**: Composer | **date**: 2026-07-09  
**scope**: 1-align 全刀 fd5866f / 854d444 / 78c85bb / e47933d；SPEC v3 Frozen  
**約束**: `data_cache/` 唯讀；未改 production code

---

## 驗證設計（獨立探針，非僅引用執行端 receipt）

| # | 項目 | 方法 | 資料 |
|---|------|------|------|
| 1 | label 逐列 oracle | bar-ordinal 手算 forward return（production `return_type`/`horizon`）vs `stage2` / `label_generator` | golden top50 + `kline_cache.h5` 3sym×12h |
| 2 | purge_gap ↔ horizon 同源 | M7 `return_5`+`default_horizon=1`；`purge_gap<5` fail-closed；`analyze` L753 `purge_gap=effective_horizon` | 真 BTC 1h kline index |
| 3 | D-4 值守恆 | `_numeric_payload_sha256` 寫回前後 + `stage2` in-place features | golden int64 features |
| 4 | golden 重凍合理 | `baseline_old`（flag off）RCA 七特徵 + rolling/summary 計數；`baseline_new`（OOS scope=test）結構 | 重凍 JSON |
| 5 | cut2 未改變 | 18+3 pytest + 3sym `_append_cross_sectional_labels` log oracle | 真 12h kline |

---

## VERIFY receipt（本 session 實跑）

### Probe 1 — label oracle

```text
BTCUSDT/1h  return_type=simple h=5  stage2 maxdiff=5.96e-08  idx=DatetimeIndex
BTCUSDT/12h log h=1  maxdiff=5.92e-08  n=1695
ETHUSDT/12h log h=1  maxdiff=5.93e-08  n=1695
BCHUSDT/12h log h=1  maxdiff=5.88e-08  n=1695
```

**判定**: PASS。golden 縱向路徑用 `config/ic_config.yaml` 的 `return_type=simple`（Tier-2 log oracle 不觸發）；手算 oracle 須與 production return 型別一致。

### Probe 2 — purge_gap 同源（return_5）

```text
_resolve_label_horizon_from_column("return_5")=5
_resolve_effective_label_horizon(labels_df)=5
purge_gap=1 → ValueError (purge_gap must be >= effective label horizon)
purge_gap=5 → train/test plan purge_gap=5
analyze() L753: purge_gap=effective_horizon
```

**判定**: PASS。

### Probe 3 — D-4 sha256

```text
_assign_datetime_index_preserving_values: sha256 match=True
stage2 in-place features: pre/post sha256 match=True, index=DatetimeIndex
kline_cache.h5 sha256 探針前後不變
```

**判定**: PASS。

### Probe 4 — golden vs RCA（`handoffs/IC1A-ALIGN-B2-GOLDEN-RCA-composer.md`）

**baseline_old**（flag off，對應 RCA actual 欄）:

| 計數 | 期望 (RCA) | 實測 |
|------|-----------|------|
| summary `ic_mean` 非空 | 50 | 50 |
| `rolling_ic_series` 有窗 | 50 | 50 |
| removed `ic_mean` | 43 | 43 |
| removed `icir` | 7 | 7 |

七特徵 RCA 抽驗（例）: `None_12h_tail_risk_max_drawdown_21_100_Cross` ic_mean=0.059927 icir=0.2180（RCA 0.059928/0.2180）— 七項全 OK（tol ic_mean±0.001, icir±0.01）。

**baseline_new**（OOS `metadata.scope=test`）: rolling 50/50、removed 43+7；`ic_mean` 非空 49/50（test 子樣本合理）；數值與 RCA 表不同屬預期（非 full-sample）。

**判定**: PASS（結構修復後 rolling 不再全 `{}`；B 類七特徵 icir 閘分類與 RCA 一致）。

### Probe 5 — cut2 cross_sectional

```bash
pytest tests/momentum/test_ic_cross_sectional_cut2.py tests/api/test_ic_analysis_service.py -q
# → 18 passed

pytest tests/momentum/test_ic_filter_orchestrator.py -k cross_sectional -q
# → 3 passed
```

3sym×12h `return_1` oracle maxdiff: BTC 5.92e-08 / ETH 5.93e-08 / BCH 5.88e-08；non_nan=5085/5088。

**判定**: PASS（1-align 未改 cut2 斷言；行為與凍結簽核一致）。

### 端到端回歸

```bash
pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py \
      tests/momentum/Analysis/test_ic_1a_cut1_split.py \
      tests/momentum/core/test_alignment_contract.py \
      tests/momentum/test_ic_cross_sectional_cut2.py \
      tests/api/test_ic_analysis_service.py -q
# → 49 passed
```

含 G-OLD/G-NEW golden deep-equal、M7 purge、alignment kernel M1–M4。

---

## 邊界聲明（不阻擋簽核）

1. **`return_type=log` Tier-2**: `validate_alignment` oracle 用 float64 close，label 生成保留 float32 → 首行可差 ~1.6e-5（> atol 1e-6）。production golden 用 `simple`，Tier-2 跳過；與 B2 review B2-DTYPE-01 同族，非本次縱向 golden 路徑。
2. **Tier-2 抽樣**: 不承諾任意單點值腐化（Claude 腿已記）；全值層由 golden byte-equal 承擔。
3. **baseline_new vs RCA 數值**: OOS test scope 與 full-sample RCA 表不可直接比 ic_mean 絕對值；比對用 `baseline_old` + 計數結構。

---

## 管線正確性結論（label→對齊→gate→split/purge→IC）

| 階段 | 證據 |
|------|------|
| label 生成 | bar-ordinal oracle ≤6e-8（simple/log 各用對應公式） |
| 對齊 / D-4 | int64→DatetimeIndex 寫回 sha256 值守恆 |
| gate | `stage2` 整合路徑通過（golden 49 測試含 G-OLD/G-NEW） |
| split/purge | `effective_horizon` 來自欄名 `return_5`；`purge_gap` 同源 fail-closed |
| IC 無洩漏 | G-NEW `scope=test`；cut2 OOS train pollution hash 不變（18 測試） |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - golden return_type=simple, effective_horizon=5（load_ic_config 實測）
  - RCA 七特徵在 baseline_old（flag off）非 baseline_new（OOS）
  - cut2 18 測試 = test_ic_cross_sectional_cut2.py + test_ic_analysis_service.py
TESTS_RUN:
  - 獨立 5-probe python（本檔 §VERIFY）
  - pytest 49 passed（golden+split+alignment+cut2+api ic）
  - cut2 18 + cross_sectional 3 passed（subset 已含於 49）
FAILURES_SEEN: none（探針初版 log-oracle 誤用 simple 路徑已修正，非 code 缺陷）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀驗證）；重凍 baseline 為已知 B2 正確性修復產物
```

**產出**: `handoffs/IC1A-ALIGN-SIGNOFF-composer.md`；診斷 receipt `/tmp/ic1a_align_signoff_composer_receipt.json`

---

SIGNOFF:composer:DATA-CORRECT
