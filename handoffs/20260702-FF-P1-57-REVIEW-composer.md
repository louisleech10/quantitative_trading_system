# P1-FF-5/7 Adversarial Code Review — Composer 2.5

**Role**: 跨家族複查（非實作者）  
**Basis**: `handoffs/20260702-FF-P1-57-RECONCILE.md` §1–§4、`IMPL-PROMPT.md`、`IMPL-codex.md`  
**Scope**: `test_ff_cross_symbol_value_isolation.py`、`test_ff_wrapper_path_correctness.py`、`ff_artifact_compare_helpers.py`  
**Reviewer verification**: `pytest -m "not slow"` 25 passed / 1 deselected；5× `test_mutation_*` passed；`mutation_probe_static.py` exit 0

---

## Executive summary

骨架正確（快測可跑、多數探針 v2 shape 合格、V7.1 registry 語意與 L2/L3/L6.5 sentinel 有落地），但對照 reconcile v2 仍有**多項可證偽缺口**：快測三序未實作 `[B,A]`、V5.3/slow 工件斷言缺失、污染面 8+ 表多面未映射、M5.2 偽探針、V5.4/V7.4 過淺。改壞 production 對應行為時，部分關鍵 regressions **不會**紅。

---

## Findings

### BLOCKING-1 — V5.1 快測三序未落地 `[B,A]`，`[A,B]` 腿名實不符

**規格**: reconcile §1 fast tier — 同 factory 三序 `[A]/[A,B]/[B,A]`；Composer §D1 明確 `[B,A]` 需 B 先跑再 A。  
**實作**: `test_v5_1_fast_order_permutation_keeps_hash_and_sampled_values` 實際序列为 `A → A → B → B → A`；`a_then_b` 在**任何 B 之前**擷取（第二次 A），並非 `[A,B]` 端點。  
**可證偽反例**: 若污染僅在「factory 上從未跑過 A、先跑 B 再跑 A」時出現（`[B,A]`），現測試永遠先跑兩次 A，不會 FAIL。  
**修法**: 同 factory 補 `[B,A]`（先 B 後 A，與 solo `[A]` 比）；`[A,B]` 應在跑 B **之後**再擷取 A（或明確第三次 A 對應 `[A,B]` 端點）；刪除冗餘雙 B 或註明用途。

---

### BLOCKING-2 — V5.3 manifest 不變量未實作（docstring 假宣稱）

**規格**: reconcile §2 V5.3 — A manifest 行數/欄集/schema 一致。  
**實作**: `test_v5_1` docstring 寫 `V5.3`，但只比 `canonical_frame_digest` + 20 欄值；helpers 無 `feature_manifest.json` 讀取/比對。  
**可證偽反例**: production 若讓 batch 後 A 的 `row_count`/`artifacts.*.total_features`/schema hash 漂移而 in-memory DataFrame 仍同，測試綠燈。  
**修法**: 在 fast/slow 加入 manifest 語意比對（行數、欄集、schema 鍵；排除 `created_at` 等非語義欄，沿 B2 gate）。

---

### BLOCKING-3 — Slow tier 未比對 d* / manifest 工件

**規格**: reconcile §1 slow — `solo(A)` vs `batch[B,A]` 比 **工件**（值 / d* / manifest）；IMPL-PROMPT 亦要求 slow artifact comparison。  
**實作**: `test_v5_slow_solo_a_equals_batch_b_then_a_artifacts` 設 `persist=True` 但只比 in-memory `features_df` digest/抽樣值。  
**可證偽反例**: 磁碟 d* path 串檔或 manifest `context.symbol` 含 B，而內存 frame 仍一致 → 慢測綠燈。  
**修法**: 沿用 `ff_truncation_mr_helpers` / B2 的 `read_d_star_json` + manifest allowlist 比對 solo vs batch 的 A run_dir。

---

### BLOCKING-4 — M5.2 偽探針：字串替換自證，不接 runtime

**規格**: reconcile §4 M5.2 — reference cache 毒化（A 拿到 B 的 ref）應讓 **V5.5 紅**；探針須 falsify 真實路徑。  
**實作**: `test_mutation_m5_2_reference_cache_static_key_drop_is_detected` 只 `inspect.getsource` 後做字串 `replace`，再 assert 原 pattern 不在變異字串中 — **未 monkeypatch factory / 未跑 generate_features**。  
**可證偽反例**: runtime 改為 `cache[tf]=B_data` 但原始碼字串仍含 `(ref_symbol, tf)`（或相反），M5.2 綠燈而 V5.5 可能紅/不紅與探針無關。  
**修法**: monkeypatch `_load_reference_if_available` 或 `_reference_data_cache` 注入 B ref，assert `assert_sampled_values_equal` / cross-sectional 欄位 FAIL；正向 V5.5 在 raises 外保留。

---

### BLOCKING-5 — 污染面 8+ 表多項掉項（reconcile §2 聯集未映射）

| 污染面 | 規格錨點 | 現況 | 風險 |
|--------|----------|------|------|
| `_d_star_cache_shared` 跨 TF | Composer §D3 #4 | **無測試** | 同 factory 跨 TF chunk 共享 d* 可污染 A |
| `FFACT_CGSA_WORK_DIR` 固定目錄 | reconcile §2 / Codex §D3 | **無測試** | 多 symbol 共用 CGSA root |
| batch checkpoint / `RunLease` | reconcile §2 | **無測試** | resume 錯 symbol 污染 |
| CGSA work_dir/shard **runtime** | V5.4/V5.6 | 僅 `features_run_dir`/`cgsa_work_dir` helper 單元測 | 真 run 串路不紅 |
| L7 artifact metadata path map | reconcile §2 | **無測試** | A parquet path 含 B context |
| d* **cross-context miss** | V5.2 語義 map | `assert_dstar_symbol_isolated` 各寫各檔，未 assert A cache **不得 hit** B payload | 共享檔名/錯 path 可假綠 |

**可證偽反例（代表）**: 設 `FFACT_CGSA_WORK_DIR=/tmp/shared`，先 B 後 A CGSA persist → 現套件無斷言會 FAIL。  
**修法**: 至少為表中每面映射一個 V* 或 M*（fast/medium/slow 分層）；cross-context 在 helper 加「A context 讀 B 檔必 miss」。

---

### BLOCKING-6 — V5.4 路徑隔離僅測 helper，未測真實 run artifact

**規格**: reconcile §2 V5.4 — A run dir/CGSA shard/d-star/L7 metadata 不得含 B context（合法 batch symbols 除外）。  
**實作**: `test_v5_4_run_and_cgsa_paths_are_symbol_scoped` 只調 `run_paths.features_run_dir` / `cgsa_work_dir`；快測 `FFACT_USE_CGSA=0` 不碰 CGSA runtime。  
**可證偽反例**: `generate_features` 寫入錯誤 leaf 但 helper 純函式仍過 → V5.4 綠燈。  
**修法**: requires_kline 跑短窗 persist，assert A `run_dir`/`feature_manifest` paths 無 `OTHER_SYMBOL` token（允許 manifest batch 欄位白名單）。

---

### BLOCKING-7 — V7.4 未綁 FeatureStorage / manifest codec 真路徑

**規格**: reconcile §3 V7.4 — float16/codec 誤差上界 + manifest `l7_encoding_registry` 明示。  
**實作**: `test_v7_4_float16_error_bound_contract_is_explicit` 只做 `float32→float16→float32` numpy 比對常數 `FeatureStorage.FLOAT16_MAX_REL_ERROR`，**未** `FeatureStorage` 讀寫、未讀 manifest。  
**可證偽反例**: storage 實際 roundtrip 超界或 manifest 未標 lossy → 測試仍綠。  
**修法**: 小 registry group 寫入/讀回 parquet（可沿用 `test_l7_raw_streaming` 模式），assert 誤差與 manifest 欄位。

---

### NON-BLOCKING-1 — L6.5 sentinel 未具名 `numba_fast` / `_apply_fractional_differencing_serial`

**規格**: reconcile §3 — fracdiff on 走 serial 分支且 polars 互斥。  
**實作**: patch `_apply_fractional_differencing`（父函式）與 `_transform_single_optimized_df`；功能上 fracdiff 分支有計數、polars==0。  
**建議**: 改 patch `_apply_fractional_differencing_serial` 與 reconcile 字面對齊；加 `numba_fast` counter 互斥斷言。

---

### NON-BLOCKING-2 — L3 矩陣縮水（設計允許小矩陣，但低於 Codex 設計密度）

**實作**: 合成 80×3 frame；aggregators 無 rank/slope/skew/kurt；無 persist_callback / M7.4 numba-fallback 探針。  
**風險**: L3 streaming callback 分歧、moment gate 不一致可能漏。  
**建議**: 補 M7.4 + callback collector（不必全鏈）。

---

### NON-BLOCKING-3 — V7.2 缺反路徑 raise sentinel 與 pathological 欄

**規格**: Codex §V7.2 — pandas `compute_all` raise 證明無 silent fallback；NaN/inf/近零 denominator 案例。  
**實作**: 僅 polars counter + 數值等值。  
**建議**: monkeypatch `compute_all` raise + 2–3 列 pathological synthetic 欄。

---

### NON-BLOCKING-4 — Medium tier 未標記

**規格**: reconcile §1 medium — A/B/A + L5 ref cache。  
**實作**: `test_v5_5_*` 內容符合但僅 `@requires_kline`，無 `@medium` / 文檔分層。  
**建議**: 加 marker 便排程與 receipt 綁定。

---

### NON-BLOCKING-5 — `test_v5_1` 連跑兩次 B 無斷言意圖

冗餘 `run_symbol_frame(OTHER_SYMBOL)` ×2 無額外 assert；增加噪音與 runtime。  
**建議**: 刪一次或 assert 累積污染（若為刻意 stress）。

---

## Probe shape audit (§4 v2)

| Probe | 正向斷言在 raises 外？ | 綁真實路徑？ | Verdict |
|-------|------------------------|--------------|---------|
| M5.1 | ✅ `test_v5_2_dstar_*` | ✅ patch `DStarCache._build_path` + helper | OK |
| M5.2 | ⚠️ 靜態 guard 在別測 | ❌ 字串自證 | **FAIL** |
| M5.3 | ✅ `test_v5_2` | ✅ patch `DStarCache.set` | OK |
| M7.1 | ✅ `test_v7_1_full_registry_*` | ✅ patch `_prepare_inputs` | OK |
| M7.2 | ✅ `test_v7_2_*` sentinel 外 | ✅ fake polars 走 pandas | OK |

---

## What passes (credit)

- 快測 25/25 + mutation_probe_static 通過；探針非空心。
- V7.1 全 registry `_prepare_inputs` byte-equal + 9 代表指標 direct-call + price_transform/MAVP。
- L2 polars sentinel + 數值等值；L3 numba multi/single/pandas 三路；L6.5 polars/optimized/fracdiff 互斥有基本證據。
- V5.2 helper 對 path/payload/value_aliases 有單元級隔離；M5.1/M5.3 可證偽（本輪反例驗證 M5.3 確實 AssertionError）。
- V5.5 runtime L5 tuple key + cross_sectional 值穩定；靜態 guard `test_v5_reference_cache_source_*` 有碼面檢查。
- Slow 測試正確 `@pytest.mark.slow` 且本地 deselect；未假稱已跑慢測。

---

## Required fixes before approval (priority)

1. 修正 V5.1 三序（含 `[B,A]`）與命名。  
2. 實作 V5.3 + slow d*/manifest 工件比對。  
3. 重寫 M5.2 為 runtime 毒化探針。  
4. 補齊污染面表缺項（至少 cross-context d*、CGSA runtime path、`_d_star_cache_shared` 或明確 defer 進 ROADMAP 並降 reconcile 宣稱）。  
5. 加深 V5.4 runtime + V7.4 storage/manifest 路徑。

---

## Reviewer runs

```
pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py \
       tests/feature_engineering/test_ff_wrapper_path_correctness.py -m "not slow" -q  → 25 passed, 1 deselected
pytest ...::test_mutation_m5_1_* ...::test_mutation_m7_2_* -q                        → 5 passed
python scripts/mutation_probe_static.py <two test files>                             → exit 0
```

---

FINAL VERDICT: REJECTED — 快測三序缺 `[B,A]`、V5.3/slow 工件與污染面多項未落地、M5.2 偽探針、V5.4/V7.4 過淺；多類 production regressions 可不觸發 FAIL。

HANDOFF_NOT_UPDATED: read-only adversarial review；未改 production/tests。

---

## CLOSURE ROUND 1 — Composer 重跑原反例（Codex FIX ROUND 1 後）

**Basis**: `handoffs/20260702-FF-P1-57-IMPL-codex.md` FIX ROUND 1  
**Role**: 原 review 方閉合驗證（read-only；未改交付檔）  
**Runs**:
```
pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py \
       tests/feature_engineering/test_ff_wrapper_path_correctness.py -m "not slow" -q  → 28 passed, 1 deselected
pytest ...::test_mutation_m5_1_* ...::test_mutation_m5_3_* \
       ...::test_mutation_m7_1_* ...::test_mutation_m7_2_* -q                     → 6 passed
python scripts/mutation_probe_static.py <two test files>                             → exit 0
```
另跑 inline counterexample probes（manifest drift、symbol poison、d* cross-context、path token、V7.4 registry/roundtrip）。

### BLOCKING findings

| ID | Status | 原反例重跑 | 改壞 production 會 FAIL？ | 證據 |
|----|--------|-----------|--------------------------|------|
| BLOCKING-1 | **REOPEN** | `[B,A]` 反例已擋；`[A,B]` 反例仍綠 | `[B,A]` 會；`[A,B]` **不會** | `b_then_a_factory` 先 B 後 A ✅；但 `a_then_b_factory` 只在 B 前擷取 `a_before_b`，跑完 B 後**未再跑 A**——`assert_sampled_values_equal(only_a, a_then_b)` 比的是 pre-B A，非 `[A,B]` 端點。污染若僅在「A 先跑、B 污染 factory、第二次 A」出現仍綠燈。 |
| BLOCKING-2 | **CLOSED** | row_count / feature_names drift | 會 | `assert_manifest_semantics_equal` 拒絕 `row_count`/`feature_names` 漂移；`test_v5_1` 對 solo vs `[A,B]`/`[B,A]` 三腿皆呼叫。 |
| BLOCKING-3 | **REOPEN** | manifest `symbol` 含 B + in-memory 仍同 | **不會** | slow 測已加 `assert_manifest_semantics_equal` + `dstar_files` path token；但 `manifest_semantic_summary` **不含 `symbol`**——probe：`{symbol:BTC}` vs `{symbol:ETH}` 仍綠。且 slow 未用 `read_d_star_json` 比 solo vs batch A 的 d* payload（僅 path 名稱檢查），原反例「path 正確但 payload 錯、內存 frame 同」仍可能綠。未跑 full slow（~1h）；結構審計 + helper probe。 |
| BLOCKING-4 | **CLOSED** | runtime L5 reference 毒化 | 會 | 新增 `test_mutation_m5_2_reference_cache_poisoning_fails_runtime_values` monkeypatch `_layer0_data_ingestion`；`cs_*relative_price` 值不等 → `AssertionError`。靜態 guard 保留。pytest 6/6 mutation passed。 |
| BLOCKING-5 | **CLOSED**（partial） | FFACT_CGSA / d* cross-context / shared cache | 已映射面會 | 4/6 污染面已映射：`test_v5_2_shared_dstar_cache_*`、helper `read_d_star_json(b).get(a_col) is None`、`test_v5_4_runtime_cgsa_paths`（`FFACT_CGSA_WORK_DIR`+真 run）、V7.4 manifest。2 面 Codex 明確 defer（batch checkpoint/RunLease、L7 path-map deep）且未降 reconcile 宣稱——誠實邊界，不單獨 REOPEN。 |
| BLOCKING-6 | **CLOSED** | helper 過、runtime 串路 | 會 | `test_v5_4_runtime_cgsa_paths_are_symbol_scoped`：`FFACT_USE_CGSA=1` + 真 `generate_features`；`assert_path_excludes_symbol` 對含 `ETHUSDT` 的 A manifest/registry path → `AssertionError`。 |
| BLOCKING-7 | **CLOSED** | numpy-only float16 探針 | 會 | `test_v7_4_float16_error_bound_contract_is_explicit` 綁 `FeatureStorage.write_processed` + `FeatureReader.load_columns_v2` + parquet `l7_encoding_registry` + manifest `encoded_column_count`（需 `FFACT_L7_CODEC_UPGRADE=1`）。缺 registry / count 不一致會 FAIL。 |

### NON-BLOCKING findings

| ID | Codex 處理 | 閉合判定 | 說明 |
|----|-----------|---------|------|
| NON-BLOCKING-1 | 改 patch `_apply_fractional_differencing_serial` | **成立** | `test_v7_3_l65_*` 計數 serial/polars/optimized 互斥。 |
| NON-BLOCKING-2 | L3 補 rank/skew/kurt；未加 persist_callback / M7.4 | **部分成立** | 矩陣密度提升可接受；callback/numba-fallback 探針仍缺，風險低於原 BLOCKING，維持 NB。 |
| NON-BLOCKING-3 | L2 加 `_forbidden_pandas` raise sentinel | **部分成立** | pandas fallback raise 已落地；pathological NaN/inf/近零分母欄未加，與 Codex「partial」一致。 |
| NON-BLOCKING-4 | docstring 標 `V5.5 medium`；未加 `@pytest.mark.medium` | **成立** | `medium` 未在 pytest.ini 註冊、改 ini 超三檔 scope；docstring 分層足排程識別。 |
| NON-BLOCKING-5 | 刪冗餘雙 B；`[A,B]`/`[B,A]` 分 factory | **部分成立** | 冗餘 B 已除；但見 BLOCKING-1：`[A,B]` 端點仍為 pre-B 擷取。 |

### Probe shape audit（post-fix）

| Probe | 正向斷言在 raises 外？ | 綁真實路徑？ | Verdict |
|-------|------------------------|--------------|---------|
| M5.1 | ✅ | ✅ patch `_build_path` | OK |
| M5.2 | ✅ `test_v5_5` + runtime poisoning | ✅ `_layer0_data_ingestion` monkeypatch | **OK**（靜態 guard 降為輔助） |
| M5.3 | ✅ | ✅ patch `DStarCache.set` | OK |
| M7.1 | ✅ | ✅ patch `_prepare_inputs` | OK |
| M7.2 | ✅ | ✅ fake polars + sentinel | OK |

### Residual gaps（若再開 FIX ROUND 2）

1. `test_v5_1`：`a_then_b_factory` 跑 B 後再跑一次 A，與 solo 比（真 `[A,B]` 端點）。  
2. `manifest_semantic_summary` 納入 `symbol`（或 CGSA manifest `artifacts.*.metadata` 鍵）供 fast/slow V5.3。  
3. slow tier：solo vs batch A 的 d* payload `read_d_star_json` 比對（沿 `ff_truncation_mr_helpers._assert_d_star_gate` 模式）。

---

FINAL VERDICT: REJECTED — BLOCKING-1 `[A,B]` post-B 端點仍缺、BLOCKING-3 slow/manifest symbol+d* payload 反例仍綠；其餘 BLOCKING-2/4/5(partial)/6/7 已 CLOSED。

HANDOFF_NOT_UPDATED: read-only closure verification；未改 production/tests/HANDOFF.md。

---

## CLOSURE ROUND 2 — Composer 重跑原反例（Codex FIX ROUND 2 後）

**Basis**: `handoffs/20260702-FF-P1-57-IMPL-codex.md` FIX ROUND 2（僅 BLOCKING-1 REOPEN + BLOCKING-3 REOPEN）  
**Role**: 原 review 方閉合驗證（read-only；未改交付檔）  
**Runs**:
```
pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py \
       tests/feature_engineering/test_ff_wrapper_path_correctness.py -m "not slow" -q  → 28 passed, 1 deselected
pytest ...::test_mutation_m5_1_* ...::test_mutation_m5_3_* \
       ...::test_mutation_m7_1_* ...::test_mutation_m7_2_* -q                     → 6 passed
python scripts/mutation_probe_static.py <two test files>                             → exit 0
```
另跑 inline counterexample probes（`[A,B]` post-B 端點、manifest symbol 毒化、d* `entries.d_star` payload 毒化）；full slow 未跑（~1h），slow 以源碼結構審計 + helper probe。

### Reopened BLOCKING findings（本輪唯一範圍）

| ID | Status | 原反例重跑 | 改壞 production 會 FAIL？ | 證據 |
|----|--------|-----------|--------------------------|------|
| BLOCKING-1 | **CLOSED** | 「B 污染 factory 後第二次 A 出錯仍綠」 | **會** | `test_v5_1` 序列已為 `A → B → A`：`a_then_b_factory` 先 `run_symbol_result(BASELINE)`，再 `run_symbol_frame(OTHER_SYMBOL)`，再以 `a_after_b_result = run_symbol_result(BASELINE)` 擷取 **post-B** 端點；`assert_sampled_values_equal(only_a, a_after_b)` 比的是 `a_after_b_result.features_df`（非 pre-B）。結構審計 `idx(first_A) < idx(B) < idx(a_after_b_result)` ✅。反例 probe：solo vs pre-B A 仍綠、solo vs post-B 污染值（`col[1]=999`）→ `AssertionError` ✅。 |
| BLOCKING-3 | **CLOSED** | manifest `symbol` 含 B + in-memory 仍同；path 正確但 d* payload 錯 | **會** | `manifest_semantic_summary` 已含 `symbol`（artifact `raw.symbol` / metadata fallback）；probe `{symbol:BTCUSDT}` vs `{symbol:ETHUSDT}` → summaries 不等，`assert_manifest_semantics_equal` → `AssertionError` ✅。slow `test_v5_slow_solo_a_equals_batch_b_then_a_artifacts` 已呼叫 `assert_dstar_payloads_equal(solo_dstar_dir, batch_dstar_dir, BASELINE_SYMBOL)`，底層 `dstar_payload_summary` 經 `read_d_star_json` 讀 `entries.*.d_star`；solo/batch 分離 cache dir ✅。反例 probe：篡改 `entries.L1_close_self.d_star` 0.4→0.99 → `assert_dstar_payloads_equal` FAIL ✅（頂層 key 毒化不被讀取，與 production `read_d_star_json` 語意一致）。 |

### Round 1 其餘 BLOCKING（本輪未重開）

BLOCKING-2/4/5(partial)/6/7 維持 CLOSURE ROUND 1 判定；本輪範圍外未重跑。

---

FINAL VERDICT: APPROVED — FIX ROUND 2 已閉合 ROUND 1 兩項 REOPEN：`[A,B]` post-B 端點與 manifest symbol + d* payload 語義比對均可證偽 production regressions。

HANDOFF_NOT_UPDATED: read-only closure verification；未改 production/tests/HANDOFF.md。

---

## INCREMENTAL REVIEW — FIX ROUND 3+4 + preset 拆綁 + slow receipt v3

**Basis**: `handoffs/20260702-FF-P1-57-IMPL-codex.md` FIX ROUND 3/4；`handoffs/run_receipts/20260702T203429Z-p1ff57-slow-fullchain-v3.{log,json}`  
**Role**: CLOSURE ROUND 2 已 APPROVED 主體；本輪僅審三筆增量（read-only）  
**Prior verdict**: APPROVED（BLOCKING-1/3 已閉合）

### 增量摘要

| 增量 | 內容 | 判定 |
|------|------|------|
| FIX R3 | slow 從 `fast_config_payload` 改 `slow_full_chain_config_payload` + 全窗 kline + `assert_slow_full_chain_config` / `assert_full_chain_runtime` 骨架 | 方向正確；R3 宣稱 `preset=professional_full` 已被 R4 取代 |
| FIX R4 | L3 416k→53k 欄縮乘數；執行閘升級（逐層 status/cols + L6.5 fracdiff/d* + L7 manifest） | **成立** |
| preset 拆綁 | `_atomic_indicators_all_enabled()` 明確全開、無 `preset` 鍵 | **成立**（優於 preset 黑盒） |
| receipt v3 | `1 passed in 992.47s`；L6.5 93672 cols；solo+batch 三腿全跑 | **成立** |

### Adversarial ① — 縮尺寸是否削弱 reconcile §2 slow 覆蓋？

**結論：縮的是特徵組合乘數，不是 V5 工件比對/污染驗證強度。**

| 維度 | R4 縮了什麼 | reconcile §2 slow 要求 | 影響 |
|------|------------|------------------------|------|
| 資料源 | `trades`/`taker_buy_volume`/多 synthetic → OHLCV+`quote_volume`+`taker_ratio`+`typ-price` | 全鏈執行 + solo≡batch 工件 | 未砍比對斷言；少覆蓋 trades 衍生欄污染面（fast/medium 已覆 L5/d*） |
| L3 | windows `[13,55]`、8 aggregators | 全鏈 L1–L7 + L6.5 fracdiff/d* | 欄數 416k→53k；**層級仍全開** |
| L6.5 | generation 關 rank/zscore/gaussian（IC-First） | fracdiff + d* cache | 與 production IC-First 路徑一致；receipt 有 `d_star_cache_hit` 與 47 chunks |
| 比對不變量 | — | V5.1 hash+20欄 / V5.3 manifest / V5.2 d* payload | `assert_manifest_semantics_equal` + `assert_dstar_payloads_equal` **未弱化** |

誠實邊界：極端污染若僅在 `trades` 欄或更多 L3 window 組合出現，slow 可能不紅——屬覆蓋面縮小、非 gate 弱化；對 reconcile「全鏈 2 跑」語意可接受。

### Adversarial ② — 逐層執行閘可證偽？

**結論：可證偽；L1–L6 + L6.5 旗標 + L7 manifest 均有反例。**

**配置閘** `assert_slow_full_chain_config`：inline probe 用 `fast_config_payload()` → `AssertionError(['trend'])`（compact 被拒）。

**執行閘** `assert_full_chain_runtime`（結構審計 + inline probe）：

| 靜默故障 | 會 FAIL？ | 探針 |
|----------|----------|------|
| L3 `status=skipped` | ✅ | `('Layer 3', ..., 'disabled', ...)` |
| L5 `data.empty` | ✅ | `('Layer 5', ...)` |
| `_preprocessing_applied=False` | ✅ | AssertionError |
| `fracdiff.enabled=False` / `cache_d_star=False` | ✅ | AssertionError |
| manifest `feature_count=0` / `run_status=failed` | ✅ | AssertionError |

receipt 佐證真實路徑：L1 3427 → L2 30180 → L3 53408 → L4 6720 → L5 3 → L6 11 → L6.5 93672 → L7 persist 91794；solo `dstar/solo/` 與 batch `dstar/batch/` 分離，ETH 腿後 BTC 腿 `d_star_cache_hit` 遞增。

**殘差（NON-BLOCKING）**：閘未查 `layer_results['Layer 6.5 (IC-First)'].status`；L6.5 只靠 `_preprocessing_applied` + config 旗標，不 assert「fracdiff 實際套用欄數 > 0」。若 production 設旗標卻全 ADF-bypass，理論上可假綠——但 receipt 有大量 `d_star_cache_hit`，本次實跑已否定。

### Adversarial ③ — preset 拆綁 vs FIX R3「全鏈等價」

**結論：與 `professional_full` preset 非 byte 等價，但與 reconcile「全鏈」意圖等價且更可控。**

| 項 | `professional_full` preset | `slow_full_chain_config_payload`（終態） |
|----|---------------------------|------------------------------------------|
| atomic | 10 類全開 | 同（`_ALL_ATOMIC_CATEGORIES`） |
| preset | `apply_preset` 黑盒 | **無 preset 鍵** |
| preprocessing | `mode=append` + rank/zscore/gaussian 全開 | `mode=replace` + IC-First 僅 winsor/ADF/fracdiff |
| L2–L6 / L5 / meta | base 預設（未顯式全開） | 顯式 operators/rolling/lag/cross/meta 全配 |
| L3 乘數 | base 預設（更大） | 明示縮至 `[13,55]`×8 aggs |

FIX R3 handoff 寫 `preset=professional_full` 已被 R4「no-preset principle」取代；程式 docstring 已寫「不綁 preset」。**等價性應理解為「L1–L7 全層 + L6.5 fracdiff/d* 真跑」**，非與 production preset 1:1。拆綁消除 preset 漂移風險，審計上優於 R3。

### Reviewer runs（本輪）

```
pytest tests/feature_engineering/test_ff_cross_symbol_value_isolation.py \
       tests/feature_engineering/test_ff_wrapper_path_correctness.py -m "not slow" -q  → 28 passed, 1 deselected
inline probes: compact config / L3 skip / L65 off / fracdiff off / manifest zero  → 均 AssertionError
receipt audit: handoffs/run_receipts/20260702T203429Z-p1ff57-slow-fullchain-v3.log（未重跑 slow）
```

### Residual gaps（不阻本輪增量）

1. `assert_full_chain_runtime` 可補 `Layer 6.5 (IC-First)` 的 `layer_results.status` 或 `d*` 檔案存在性（現靠旗標 + receipt）。
2. FIX R3 handoff 仍寫 `preset=professional_full`——與終態 code 不一致；建議 Claude 在 IMPL 索引標「R3 已被 R4 supersede」免後人誤讀。
3. slow 未覆蓋 `trades`/`taker_buy_volume` 資料源——列為覆蓋面殘差，非 BLOCKING。

---

FINAL VERDICT: APPROVED — FIX R3/R4 將 slow 從 compact 升至真全鏈（縮乘數不砍 V5 工件比對）；執行閘可證偽且 receipt v3 證實 L6.5 fracdiff/d*+solo/batch 三腿；preset 拆綁優於 R3 宣稱的 professional_full 等價，殘差為文件/ L6.5 深度閘 NON-BLOCKING。

HANDOFF_NOT_UPDATED: read-only incremental review；未改 production/tests/根 HANDOFF.md。
