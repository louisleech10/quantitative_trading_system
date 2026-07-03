# FRACDIFF_MAXLAG B1+B2 — Adversarial Code Review (Composer)

**task-id**: `fracdiff-maxlag-review-composer-20260703`  
**reviewer**: Composer 2.5（實作者 Codex 不自審）  
**scope**: B1（Task 1.1–1.4）+ B2（Task 2.1–2.4）  
**SPEC**: `docs/FRACDIFF_MAXLAG_SPEC.md`  
**TODO**: `docs/FRACDIFF_MAXLAG_TODO.md`  
**實作交接**: `handoffs/20260703-FRACDIFF-MAXLAG-B1B2-codex.md`  
**方法**: `git diff` 指定檔 + 實碼 grep/Read + 本機 pytest（快測 15/15、`mutation_probe_check.sh` 7/7）

---

## ① 既有斷言 / helper 是否被放寬

| ID | 級別 | 結論 | 碼證 |
|---|---|---|---|
| 1.1 | **PASS** | `ff_truncation_mr_helpers.py` **零 diff**（`git diff` 空；工作樹 clean） | 交接 L7–8；本輪 `git diff tests/feature_engineering/ff_truncation_mr_helpers.py` → 無輸出 |
| 1.2 | **PASS** | `FRACDIFF_ATOL=1e-8`、`_assert_d_star_gate` 精確相等、`_assert_fracdiff_truncation_invariants` 本體未改 | `ff_truncation_mr_helpers.py:44,1109–1147`；diff 僅觸及 `test_ff_fullchain_truncation_mr.py` xfail 刪除 + 新 mutation |
| 1.3 | **PASS** | 兩 fracdiff MR 僅刪 `@pytest.mark.xfail(strict=True)` 與委員會註解塊；測試 docstring/呼叫鏈不變 | `test_ff_fullchain_truncation_mr.py` diff `:107–140`（刪 xfail）；`:110–140` 本體仍 `_assert_fracdiff_truncation_invariants(pair)` |

---

## ② `_resolve_fracdiff_max_lag` 是否 production 唯一推導點、len(df) 旁路

| ID | 級別 | 結論 | 碼證 |
|---|---|---|---|
| 2.1 | **PASS** | 新增 resolver seam；顯式 `max_lag>0` 直通，否則 `min(max(2, _calibration_bars()//10), 252)` | `feature_preprocessor.py:3020–3026` |
| 2.2 | **PASS** | `_apply_fractional_differencing` 唯一取值點改呼叫 resolver；舊 `len(df)//10` 分支已移除 | `feature_preprocessor.py:3204–3205`（註解 + `max_lag = self._resolve_fracdiff_max_lag()`） |
| 2.3 | **PASS** | 全 `momentum/` `len(df)` 與 `max_lag` 共現 **0 命中**；`feature_preprocessor.py` 內 `len(df)` 僅剩註解行 | `grep 'len\(df\).*max_lag\|max_lag.*len\(df\)' momentum/` → 0；`feature_preprocessor.py:3204` 註解 |
| 2.4 | **PASS** | serial 傳 `max_lag` 入 `_find_min_d` / `_frac_diff_convolve`；parallel 經 `column_metadata["max_lag"]`（`:3124`）→ `_slow_path_parallel.py:128,145` | 掃描產物見交接 L8–9 |
| 2.5 | **NON-BLOCKING** | `lag_processor` / `parameter_generator` 的 `max_lag` 為 lag 運算子語意（SPEC §A.9 明示 out-of-scope） | `lag_processor.py:161`；`parameter_generator.py:54–67` |
| 2.6 | **NON-BLOCKING** | `_fast_adf_numba.py:110–111` 的 `max_lag` 為 ADF 統計 lag 上限，與 fracdiff 權重寬度無關 | 已讀 `:110–111` |

---

## ③ B-2 max_lag mutation 探針可證偽性

| ID | 級別 | 結論 | 碼證 |
|---|---|---|---|
| 3.1 | **PASS（設計）** | 三測試 monkeypatch **實例** `_resolve_fracdiff_max_lag → `len(df)//10` 等效；mutant 在 `original_apply` 前注入 | `test_ff_fullchain_truncation_mr.py:158–162,194–198,232–236` |
| 3.2 | **PASS（設計）** | 截斷 MR + 尾端擾動 MR **各一**；皆經 `_assert_fracdiff_truncation_invariants` → `_assert_d_star_gate` | `:143–176` trunc；`:179–213` tail |
| 3.3 | **PASS（設計）** | parallel case：`_resolve_slowpath_n_jobs→2` + spy `_apply_fractional_differencing_parallel`；事後 `max(parallel_calls)>1` | `:239–266` |
| 3.4 | **PASS（設計）** | mutant 互不遮蔽：獨立 `d_star_parent` 子目錄（`dstar_mut_len` / `_tail` / `_parallel`） | `:172,208,261` |
| 3.5 | **BLOCKING** | **slow 整合 mutation 三測未實跑**（檔案 `pytestmark = [slow, requires_kline]`）；交接 L15「NOT RUN slow fracdiff MR」。無 receipt 證明 mutant 在真實全鏈上確實紅 | `test_ff_fullchain_truncation_mr.py:51`；`B1B2-codex.md` L15 |
| 3.6 | **NON-BLOCKING** | 寬 `pytest.raises(AssertionError)` 同時包住 `_build_truncation_pair` + invariants（類 P0FF3 風險）；但 `_build_truncation_pair` 本身不 assert（`:1298–1382` 僅 return pair），實際 AssertionError 來源應為 `_assert_d_star_gate` `:1124` 或 values gate | 建議後續拆成「先 pair、再單獨 assert」與 P0FF3 fix 對齊；非本輪 code defect |

---

## ④ `test_dstar_cache_key_mutation.py` 七 mutant vs v3 guard

| ID | 級別 | 結論 | 碼證 |
|---|---|---|---|
| 4.1 | **PASS** | 7 mutant 對準 v3 `_payload_matches` / `get_by_value_fingerprint` guard | production：`_d_star_cache.py:392–447,501–527` |
| 4.2 | **PASS** | path symbol：同 path 寫入錯 symbol payload → `payload.symbol` 不符 → miss；**非** P1-FF-5 V5.2（V5.2 測 path 隔離 / M5.1 測 shared path） | 測試 `:76–83`；對照 `test_ff_cross_symbol_value_isolation.py:235–247`（M5.1 `_build_path` 共用） |
| 4.3 | **PASS** | path timeframe：`:86–93` | `_d_star_cache.py:405–417` |
| 4.4 | **PASS** | fracdiff_hash max_lag 軸：seed `max_lag=60` payload 寫入 `max_lag=50` 期望 hash → `fracdiff_hash` mismatch | 測試 `:96–104`；guard `:399–401` |
| 4.5 | **PASS** | fracdiff_hash calibration_bars 軸：`:107–115` | guard `:439–447` + hash payload `:227` |
| 4.6 | **PASS** | payload `row_count` / `time_range`：`:118–137`；本輪跑測見 stale warning log（證 guard 觸發） | `:421–427` |
| 4.7 | **PASS** | `strong_value_fp`：同 context 換 `VALUES_B` → miss；**值斷言** `_assert_no_stale_hit` 期望 `0.375`、實際 `None` 才紅 | `:71–73,140–146`；guard `:513–520` |
| 4.8 | **NON-BLOCKING** | 與 `test_d_star_col_fingerprint.py::test_col_values_mismatch_miss`（`:116–125`）語意重疊；SPEC 允許標「不重複」但未在檔首引用 | 建議檔首註明 defer 至 col_fingerprint 正向測、本檔負向 mutation 互補 |
| 4.9 | **PASS** | `scripts/mutation_probe_check.sh` exit 0；7 probe 真跑 | 本輪 receipt 語意同 `20260703T053419Z-mutation-test_dstar_cache_key_mutation` |

---

## ⑤ `feature_config.max_lag` 下游影響面

| ID | 級別 | 結論 | 碼證 |
|---|---|---|---|
| 5.1 | **PASS** | 欄位 `max_lag: int = Field(default=0, ge=0)` + 中文註解 | `feature_config.py:190–191` |
| 5.2 | **PASS** | 舊 dict 無 `max_lag` → 0；負值 ValidationError | `test_fracdiff_maxlag_derivation.py:86–95` |
| 5.3 | **PASS** | `warmup_window` 讀 `model_dump().get("max_lag")`；auto 仍 fallback 252 + epic 註解 | `warmup_window.py:292–298` |
| 5.4 | **PASS** | `_native_tf_helpers` 已列 `max_lag` 為 kept（不 scale） | `_native_tf_helpers.py:98–118` |
| 5.5 | **NON-BLOCKING** | `config_hash` 經 `FactoryConfig.model_dump()` 全量序列化（`feature_factory.py:3696`）；新欄位預設 `max_lag:0` 會出現在 dump → **既有 run 的 config_hash 字串可能變**（即使行為上仍為 auto）。與本 epic 數值變更疊加，屬預期級聯失效，但應在 B3 文件註明 | `feature_factory.py:3688–3725` |
| 5.6 | **NON-BLOCKING** | d\* cache **不**吃 `config_hash`，吃 `fracdiff_hash`（含 `max_lag`） | `_d_star_cache.py:206–307,399–401` |
| 5.7 | **BLOCKING（Task 1.2 驗證欄）** | **G2' 交叉驗證未做**：schema 落地後真 config 路徑 `max_lag=50` 重跑 golden、assert G2' digest == G2（SPEC §G D 增強 / TODO Task 1.2 驗證欄） | 交接與 diff 均無 G2' receipt / 測試 |

---

## ⑥ Task 邊界與不可做

| ID | 級別 | 結論 | 碼證 |
|---|---|---|---|
| 6.1 | **PASS** | 未改 `_get_weights_ffd` / 卷積本體 / cache 檔格式 | diff 僅 3 production 檔 |
| 6.2 | **PASS** | warmup 未改 252 數值，僅註解 | `warmup_window.py:294–297` |
| 6.3 | **PASS** | 未動 batch checkpoint / RunLease（B-5 defer） | 無相關 diff |
| 6.4 | **PASS** | 未弱化 NaN/inf gate | helper 零改 |
| 6.5 | **BLOCKING** | **B-1 slow receipt 缺失**：xfail 已移除但 `test_fracdiff_truncation_invariant` / `test_fracdiff_tail_perturbation_invariant` 無「2 passed」slow receipt（TODO Task 2.1 / Phase 2 Gate） | `B1B2-codex.md` L15–16 |
| 6.6 | **NON-BLOCKING** | Task 2.4 邊界 `calibration_bars=10 → max_lag=2` 未測；`_calibration_bars()` 硬底 `>=500`（`:175–178`）使該邊界在 production seam 不可達——交接 L18 已記錄 | `feature_preprocessor.py:175–178` |
| 6.7 | **NON-BLOCKING** | Task 1.3 驗證命令 `pytest tests/ -k warmup_window` 本輪 **0 selected**（測試名不含該字串）；實際 warmup 測在 `test_b6_warmup_trim.py`。本輪 `pytest test_b6_warmup_trim.py -k 'not golden'` → **15 passed**（golden 失敗為已知預期變更） | 使用者已知；`test_b6_warmup_trim` golden 待重生 |
| 6.8 | **NON-BLOCKING** | `test_fracdiff_auto_max_lag_is_calibration_derived_not_df_length` 迴圈建 `frame` 但未傳入 resolver（`:74–77`）；覆蓋靠 `:139–161` 整合 spy。建議刪假迴圈或改 spy 路徑 | `test_fracdiff_maxlag_derivation.py:71–77,139–161` |

---

## 本輪獨立驗證

```
pytest tests/feature_engineering/test_fracdiff_maxlag_derivation.py \
       tests/feature_engineering/test_dstar_cache_key_mutation.py -v
→ 15 passed in 0.06s

bash scripts/mutation_probe_check.sh tests/feature_engineering/test_dstar_cache_key_mutation.py
→ MUTATION-PROBE PASS (7 probes)

pytest tests/feature_engineering/test_b6_warmup_trim.py -m 'not slow' -k 'not golden'
→ 15 passed, 1 deselected
```

---

## BLOCKING 摘要（須補證據後方可簽 B1+B2 Gate）

1. **B-1**：slow fracdiff 兩 MR 實跑 receipt（xfail 已撕，無 pass 證明 = 不可合併宣稱 B-1 完成）。
2. **B-2（整合）**：三個 `test_mutation_fracdiff_maxlag_*` 同屬 `slow`，未跑則 serial/parallel mutant 穿透僅停留在 code review。
3. **Task 1.2 / §G D**：G2' config-path pin=50 digest 對照 G2 未做。

## NON-BLOCKING 摘要（建議跟進）

- B-2 mutation 拆窄 `pytest.raises` 範圍（對齊 P0FF3 教訓）。
- `strong_value_fp` mutant 註明與 `test_d_star_col_fingerprint.py` 分工。
- `config_hash` 新增 `max_lag:0` 的碎片化影響寫入 B3 文件。
- 修正 Task 1.3 驗證命令為 `test_b6_warmup_trim.py` 路徑。

---

## FINAL VERDICT: **CHANGES_REQUIRED**

**理由**：production 修復與快測/mutation 靜態護網方向正確、helper 未弱化、resolver seam 與 len(df) 解耦達 SPEC；但 **B-1 轉綠與 B-2 slow mutation 均缺 receipt**，且 **G2' config 路徑交叉驗證未落地**——在 (a)(d) 高風險 epic 下不能僅憑 unit 綠燈簽核整合正確性。

**建議解阻順序**（編排端，非本 review 實作）：
1. 跑 `pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py -k 'test_fracdiff_' -m slow` → 留存 `handoffs/run_receipts/<UTC>-fracdiff-maxlag-mr-green.log`（含 2 invariant + 3 mutation）。
2. 跑 G2'（真 config `max_lag=50`）對照 G2 digest。
3. 三方 §G 條件 1/2 + [B-1] receipt 齊後再進 B3。

---

```
ASSUMPTIONS_VERIFIED: git diff 指定 6 檔；ff_truncation_mr_helpers 零 diff；grep momentum len(df)∧max_lag=0；_d_star_cache guard 行號對讀；快測 15/15 + mutation_probe 7/7 本機重跑
TESTS_RUN: 見上「本輪獨立驗證」；slow MR / G2' 未跑（與交接一致）
FAILURES_SEEN: none（快測）；slow/G2' 缺口為 gate 未滿非 pytest fail
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: 已實作預期變更（auto max_lag 50、schema 新欄位）；config_hash 可能因新欄位出現在 dump 而變（NON-BLOCKING 登記）
```

STATUS: DONE
