# IC 1a cut1 FIX2 — 數據正確性最終確認（Composer 非作者腿）

**角色**: 第三方複查（R1 曾漏 2 個洩漏不變量）  
**對象**: FIX2 後 `momentum/Analysis/ic_filter_orchestrator.py` 最終狀態  
**時間**: 2026-06-26

---

## 結論：**PASS**

FIX2 的位置式切片與 raw kline 對齊修復**不改變 train/test row 選取邏輯**；3 個洩漏不變量仍 PASS；G-NEW baseline 具 `metadata.scope=="test"` 且與 G-OLD 明確不同。位置式切片在真實 pipeline（feature index ≠ label index）下屬**修正錯配**，非重開洩漏。

---

## ① FIX2 改動審查（`git diff ic_filter_orchestrator.py`）

### 核心 FIX2（相對 FIX1/整合 bug）

| 函式 | 改動 | 影響 which rows? |
|------|------|------------------|
| `_slice_by_mask` | `features_df.index[mask]` + `.loc` → `np.flatnonzero(mask)` + `.iloc`；label 同長度時亦用 `iloc` | **否** — mask 陣列未變 |
| `_slice_raw_data_by_mask`（新增） | `len(raw)==len(features)` 時 `raw_data.iloc[positions]`，再 `index=sliced_features.index` | **否** — 同一 mask positions |
| stage4 decay/grouped IC | 改用 `raw_data_for_ic`（OOS 位置切片後） | **否** — 僅修 RangeIndex↔timestamp 對齊 |

### 未改動（洩漏邊界仍由這裡決定）

- `_build_holdout_split_plan`: `train_rows=np.arange(0,split_point)`；`test_rows=np.arange(split_point+purge+embargo,n)` — 位置式 row_index
- `_derive_stage_masks`: 由 `SplitPlan.time_bounds` 在當前 stage index 重導布林 mask
- `purge_gap >= effective_horizon` 檢查保留

### FIX2 前根因（dispatch 已證實）

```text
label_series.index ≠ features_df.index（真實 run）
→ label_series.loc[features_df.index[mask]] 全不匹配 raise
→ 單元 fixture 共用 index 故未抓到
```

---

## ② 洩漏不變量測試

```bash
pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_purge_label_mutation_does_not_change_test_rolling_ic \
       tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_winsorize_type_branch_uses_train_slice_only \
       tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_holdout_embargo_delays_test_start -v
```

**結果: 3/3 PASSED**（0.39s）

| 測試 | 不變量 | 意義 |
|------|--------|------|
| `test_purge_label_mutation_*` | purge 區 label 變異不改 test rolling IC | purge gap 未洩漏進 OOS |
| `test_winsorize_type_branch_*` | winsor 只在 train slice fit | train-only 前處理 |
| `test_holdout_embargo_*` | `test_plan.row_index[0] == split_point + horizon + embargo` | embargo 延後 test 起點 |

---

## ③ G-NEW baseline vs G-OLD

**檔案**: `tests/golden/ic_phase1_1a_cut1/baseline_new_btc_1h_a384e6d2.json`

| 檢查項 | G-OLD | G-NEW |
|--------|-------|-------|
| `metadata.scope` | **缺失** | **`"test"`** ✓ |
| `metadata.event_filter.split_mask` | 缺失 | `train_rows=16281, test_rows=4066` ✓ |
| `filter_log.stage6_redundancy.scope` | 缺失 | `"test"` ✓ |
| 檔案相等 | — | `old == new` → **False** ✓ |
| 檔案大小 | 52,211,832 B | 10,597,703 B（OOS 序列較短） |
| sha256 | — | `24d69dc6e74f0478902c96cf3d4f3b5f83c632ce0e8833c7c4a7ab5b9a9fa349`（與 `baseline_new_meta.json` 一致） |
| 凍結方式 | `freeze_baseline.py` flag-off | `freeze_baseline_new.py` `config_override.ic_train_test_split=True` |

**coverage 差異樣本**（證明非同一計算宇宙）:
- G-OLD `None_12h_microstructure_roll_spread_13_55_Cross` coverage ≈ 0.999, `effective_start=12`
- G-NEW 同 feature coverage = 1.0, `effective_start=0`（test-only 統計）

**備註**: G-NEW `metadata.n_samples` 仍為 20352（全宇宙列數）；但 `split_mask` + `scope=test` + 數值差異確認 OOS 路徑已生效。

---

## ④ 位置式切片是否可能改變 row 選取或重開洩漏？

### 判定：**不會**（在 FIX2 scope 內）

**理由**:

1. **Mask 語意不變** — `_slice_by_mask` / `_slice_raw_data_by_mask` 只吃既有 `train_mask`/`test_mask`；which positions 為 True 仍由 `_build_holdout_split_plan` + `_derive_stage_masks` 決定，FIX2 未觸及。

2. **位置式 vs 標籤式在「同序同長」下等價** — 當 `len(label)==len(features)` 且列順序對齊，`iloc[flatnonzero(mask)]` 與 `loc[index[mask]]` 選同一組列。洩漏測試 fixture 與真實 BTC frame 皆滿足此條件。

3. **index 不匹配時 FIX2 修正而非改選** — 真實 run 舊碼直接 raise；新碼依 mask 位置取 label，避免用錯 timestamp 標籤配對。這是**修復 label 對齊**，不是擴大 test 集合。

4. **raw kline 切片** — `len(raw_data)==len(features_df)` 時按同一 positions 取列，僅把 index 設為 OOS feature index 供 grouped IC；不修 mask、不引入未 purge 列。

5. **embargo/purge 邊界** — `test_holdout_embargo_delays_test_start` 直接驗證 `SplitPlan.row_index` 算術，與切片實作無關，仍 PASS。

### 殘餘觀察（非 BLOCKING，非 FIX2 引入）

- `_stage6_redundancy` L1678 仍用 `features_df.loc[features_df.index[mask]]`（標籤式），但只切 features（單一 index），與 FIX2 的 label/raw 錯配場景不同。
- G-NEW `n_samples=20352` 為全資料列數標記，非 test 列數；建議後續文件化，但不影響本次 FIX2 洩漏判定。

---

## 證據摘要

```
ASSUMPTIONS_VERIFIED:
  - FIX2 diff 僅改 _slice_by_mask 切片機制 + _slice_raw_data_by_mask；split/mask 建構未動
  - G-NEW metadata.scope=="test"; G-OLD 無 scope
  - G-OLD/G-NEW 數值與檔案大小不同（非假綠）
  - 真實 pipeline label index ≠ feature index（FIX2-DISPATCH 根因）

TESTS_RUN:
  pytest ...test_purge_label_mutation... test_winsorize_type_branch... test_holdout_embargo... → 3 passed

FAILURES_SEEN: none

SCOPE_CHANGES: none（唯讀確認 + 本 handoff）

NUMERIC_OR_SCHEMA_IMPACT: none（未改程式；僅審查 FIX2 後狀態）
```

---

**複查者判定**: 數據正確性 **PASS** — FIX2「不改 which rows、只修 index 對齊」之宣稱成立；R1 曾漏的 3 個洩漏不變量現均綠燈。

STATUS: DONE
