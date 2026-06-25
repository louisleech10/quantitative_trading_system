# IC Phase 0 實作 — Composer 2.5 Code Review（跨家族複查 Codex diff）

> 2026-06-25 ｜ 審查範圍：`git diff` tracked 11 檔 + untracked `tests/fixtures/ic_phase0/`、`tests/momentum/test_ic_*.py` 新增檔  
> 準則：`docs/IC_PHASE0_SPEC.md`、`docs/IC_PHASE0_TODO.md`、R-1~R-12、T-1~T-12  
> 親驗：`pytest` Phase0 專項 15 passed；`vitest useICAnalysis.test.ts` 4 passed；`load_ic_config()` 實跑 `by_volatility=True`

## Verdict：需修補後合併

核心修法（CRASH / TIMEAXIS / feature_filter / decay log / UX）方向正確，測試多數非 smoke、golden 為結構化 float。但 **預設 grouped 路徑因 `config/ic_config.yaml` 仍 `by_volatility: true` 會在真實 kline 路徑直接 `NotImplementedError`**，與 R-2/B-1 migration 意圖相反，屬 production 回歸。修 yaml（或等效 migration）並補預設 config 整合測試後可合併。

---

## Findings

### [BLOCKING] `config/ic_config.yaml` 未同步 `by_volatility: false`，預設 grouped run 必崩

**證據**
- Schema 已改預設：`momentum/Analysis/ic_config_schema.py:80` `by_volatility: bool = False`
- 但預設 YAML 仍為 true：`config/ic_config.yaml:51` `by_volatility: true`
- 三層合併後實跑：`load_ic_config().ic_calculation.grouped_analysis.by_volatility` → **True**
- `compute_grouped_ic` 顯式 fail-closed：`ic_engine.py:389-392` `if config.get("by_volatility"): raise NotImplementedError(...)`
- 親跑重現（default `model_dump()` + 秒級 kline）：`NotImplementedError by_volatility grouped is not supported in Phase 0`
- API 真路徑：`ic_filter_orchestrator.py:1244-1250` 在 `include_regime_analysis=True`（yaml 預設 `report.include_regime_analysis: true`）且 `kline_reader` 有資料時必進 grouped；`ic_analysis_service.py:206-217` 在 **無 `labels_path`** 時會建立 `kline_reader`

**風險**  
R-2 / Task 2.3 migration 寫「既有預設 grouped run 不再因未顯式要求 volatility 而 raise」——現況是 **從靜默忽略變成預設必 raise**，任何依賴預設 config 的 regime/grouped 分析（含 UI 無 labels_path 路徑）會整 run failed。

**修法**
1. 將 `config/ic_config.yaml`（及若有覆寫的 `user_ic_config.yaml`）`grouped_analysis.by_volatility` 改為 `false`，並加 migration 註解。
2. 新增整合測試：`load_ic_config()` **不 override** + `include_regime_analysis=True` + 秒級 kline fixture → grouped 應成功、不 raise。
3. 可選：在 `load_ic_config` 或文件層明確記錄「yaml 優先於 schema default」。

---

### [MAJOR] 缺預設 config 端到端 grouped 測試 → 擋不住上述 BLOCKING

**證據**
- `test_ic_crash_real_config.py` 手動 `.update({"by_volatility": False})`
- `test_ic_filter_orchestrator.py:test_stage4_ic_calculation_with_kline_reader` 同樣顯式 `by_volatility: False`
- `test_ic_timeaxis.py` 的 by_volatility 測試只驗 **顯式 True raise**，未驗 **default load_ic_config 不 raise**
- 無測試覆蓋「`load_ic_config()` 原樣 + kline + regime on」

**風險**  
假綠：專項測試全綠但 production 預設 config 仍壞。

**修法**  
新增 `test_default_grouped_config_does_not_raise_with_kline()`，禁止在測試內手動關 `by_volatility`（除非測 fail-closed 顯式 True 案例）。

---

### [MAJOR] Task 3.2 / T-9：缺 45k `max_features` 穩定性測試

**證據**
- SPEC/TODO Task 3.2：`pytest factory 造 n=45000` + `max_features=30` + 兩次 sha256 相同
- `tests/momentum/test_ic_feature_filter.py` 僅 5 欄小表測 sorted 子集，無大尺度

**風險**  
大 run 截斷的效能/記憶體與確定性未在 CI 覆蓋；回歸時可能 OOM 或排序邏輯被改壞而不自知。

**修法**  
補 factory 測試（可 parametrize 較小 N 做 CI 快測 + 標記 slow 的 45k 版），斷言欄名 sha256 兩次一致、`feature_count_filtered==30`。

---

### [MAJOR] Task F-7：缺 orchestrator 主流程「實際 IC 特徵數 == 篩後數」整合測試

**證據**
- `_apply_feature_filter` 單元測試充分（`test_ic_feature_filter.py`）
- 無測試走 `analyze()` / `_stage4_ic_calculation` 驗證 `metadata.feature_count_filtered` 與實際 `features_df.shape[1]`、IC 結果鍵數一致
- Golden `test_feature_filter_baseline` 亦只測 helper

**風險**  
filter 與 stage4 之間若有遺漏接線（或未來重構），單元測試仍綠。

**修法**  
精簡整合測試：小 HDF5 + `config_override.feature_filter.max_features=N` → 斷言 report metadata 與 summary_table 特徵數 ≤ N。

---

### [MAJOR] Decay 摘要 log 與 SPEC Task 4.1 邊界不完全一致

**證據**
- SPEC/TODO：`結尾 logger.info("Decay: %d/%d 特徵 fit 異常 ...")` **一行**；邊界「全部 fit 成功 → 摘要顯示 0 低品質」
- 實作：`ic_engine.py:367-371` 僅在 `if warning_counts:` 時 log；格式為 `"Decay: fit warnings summarized (reason=count)"`
- `test_ic_decay_log.py` 只在有 warning 場景斷言「恰一行」，未測全成功無 log

**風險**  
低（不影響數值）；但偏離 D-1/D-2 契約，運維無法依「總是有一行」做 log 監控。

**修法**  
改為每次 `compute_ic_decay` 結尾固定一行（含 `0/total`）；補 caplog 全成功案例。

---

### [MINOR] TIMEAXIS：NaN timestamp 有處理無單測

**證據**
- `ic_engine.py:1026-1027` `if values.isna().any(): raise ValueError(...)`
- `test_ic_timeaxis.py` 測 1970/2100/1e16，**無 NaN 列**

**風險**  
邊界回歸無 CI 護欄。

**修法**  
`pytest.raises(ValueError, match="NaN")` 一條即可。

---

### [MINOR] TIMEAXIS：毫秒路徑與 R-12 邊界 `1e15` 未單獨覆蓋

**證據**
- 單位判斷 `unit = "ms" if max_abs >= 1e12 else "s"`（`ic_engine.py:1033`）
- 非法門檻 `>= 1e15`（`:1029`）；測試用 `1e16`（`test_ic_timeaxis.py:48`），無 ms 樣本、無恰 `1e15`

**風險**  
邊界 off-by-one 或未來改門檻時假綠。

**修法**  
各加一條：`1704067200000`（ms）→ 2024；`1e15` → raise。

---

### [MINOR] `_get_time_index` 回傳 index 未對齊 `raw_data.index`（依賴 caller 重綁）

**證據**
- `parsed = pd.DatetimeIndex(pd.to_datetime(values.to_numpy(), ...))` 預設 RangeIndex 0..n-1
- SPEC Task 2.1：「index 與 raw_data 對齊」
- `_iter_time_groups` 以 `pd.Series(time_index, index=raw_data.index)` 補齊（`ic_engine.py:1012`），目前唯一 caller 安全

**風險**  
未來若他處直接消費 `_get_time_index` 回傳值可能錯位。

**修法**  
可選：`return pd.DatetimeIndex(parsed, index=raw_data.index)` 或 docstring 標明須用 raw_data.index 對齊。

---

### [MINOR] Decay golden 無法單獨證明「僅移 log 前後數值不變」

**證據**
- `baseline_decay.json` 與現程式一致即 pass；無 pre-change artifact 或雙版本比對
- 讀碼：`_fit_exponential_decay` 僅刪 `logger.warning`，回傳 dict 結構未改（`ic_engine.py:918-968`）

**風險**  
若 baseline 與實作同次生成，理論上擋不住「順手改公式」；本次讀碼風險低。

**修法**  
建議 commit 訊息/手冊註明 baseline 凍結時機；長期可用獨立 reference script 重算。

---

### [MINOR] `test_stage4_ic_calculation_with_kline_reader` kline 仍用 DatetimeIndex index

**證據**
- `test_ic_filter_orchestrator.py` DummyReader 回 `index=pd.date_range(...)`，非 RangeIndex+秒級欄
- 該測試 grouped 全關，主要測 decay；不構成 s/ms 假綠，但與 T-3 byte-faithful 精神不一致

**風險**  
低；已有 `test_ic_timeaxis.py` + golden 補洞。

---

### [MINOR] 前端 poll 狀態機：`retryCountRef` 僅在 `startAnalysis` 重置

**證據**
- `useICAnalysis.ts:288` `retryCountRef.current = 0` 在 start 時
- `connectProgress` 單獨呼叫時不重置

**風險**  
極端場景（手動 reconnect 同一 hook）可能少於 3 次 WS 重試即 poll。

**修法**  
`connectProgress` 開頭在 `terminalRef.current = false` 旁重置 retry（若產品允許重入）。

---

## 正確性 / 防假綠 專項結論（逐項 1–5）

### 1. TIMEAXIS / grouped 時間軸

| 子項 | 結論 |
|------|------|
| (a) `_get_time_index` → DatetimeIndex + 單位實測 + fail-closed | **基本正確**：回 `pd.DatetimeIndex`、秒/ms 量級判斷、年份 sanity、NaN/`>=1e15` raise（`ic_engine.py:1019-1046`）。秒級 fixture 親測 2024。 |
| (b) `_iter_time_groups` `.dt.year` | **正確**：`time_series.dt.year` / quarter（`:1013-1016`），group index 為 `raw_data.index` labels。 |
| 對齊 raw_data.index | **間接正確**：經 `Series(time_index, index=raw_data.index)`；`_get_time_index` 本身 index 未綁定。 |
| 邊界 NaN/1e15/年份 | **實作有、測試部分缺**：1970/2100/1e16 有測；NaN、ms、恰 1e15 無測。 |
| 防假綠 | **改善**：`test_ic_timeaxis.py` + `kline_seconds.csv` RangeIndex+秒；`test_ic_engine.py` 玩具 `[0,1000,2000]` 已改真秒級。**未**用 DatetimeIndex index 假綠 grouped。 |

### 2. BYVOL fail-closed + 預設 False

| 子項 | 結論 |
|------|------|
| 顯式 True → raise | **正確**，訊息含 `not supported`（`ic_engine.py:389-392`）。 |
| Schema 預設 False | **程式碼正確**，**執行時錯誤**：yaml 覆寫為 True → **BLOCKING**。 |
| 預設 grouped 不 raise | **失敗**（見 BLOCKING）。 |

### 3. `_apply_feature_filter`

| 子項 | 結論 |
|------|------|
| 預設不截斷 | **正確**（`feature_filter is None` / 空 dump；前端 `max_features: undefined`）。 |
| sorted 截斷 | **正確**（`:804-807`）；雙向欄序測試通過。 |
| 零特徵 raise | **正確** `InvalidInputError`（`:809-810`）。 |
| truncation_mode | **正確**：max 生效 → `preview`；category 篩 → `none`+`applied=True`（測試覆蓋）。 |
| 7 欄 schema + load_ic_config | **正確**（`FeatureFilterSchema` + `test_load_ic_config_keeps_feature_filter_override`）。 |
| API 串接 | **正確**（`ic_analysis_service.py:969-972` → override → orchestrator `config.feature_filter`）。 |

### 4. Decay log / 數值不變

| 子項 | 結論 |
|------|------|
| 熱迴圈 4 warning 移除 | **正確**（insufficient / low_variance / low_r2 / fit_exception 皆無 `logger.warning`）。 |
| 結尾一行摘要 | **部分正確**：有 warning 時一行；全成功無 log；格式非 SPEC `N/total`。 |
| 數值不變 | **讀碼 + golden 支持**：回傳欄位未改；`test_decay_baseline` 結構化 `np.isclose` + NaN mask。非獨立 pre/post 對照。 |

### 5. 跨層 / 相容 / 遺漏

| 子項 | 結論 |
|------|------|
| CRASH model_dump | **正確**（`ic_filter_orchestrator.py:1250`）。 |
| to_thread 兩路徑 | **正確**（longitudinal + cross_sectional）；`test_run_analysis_does_not_block_event_loop` 通過。 |
| 前端 failed / poll | **正確**：WS `payload.message`、poll `status.error`；retry≤3→poll；vitest 覆蓋。 |
| 向後相容 feature_filter None | **正確**。 |
| R/T reconcile 走樣 | **R-2 migration 未完成（yaml）**；其餘 R-1/R-3~R-12 大體落實。 |
| 既有測試放寬 | **未發現**：`test_stage4` 從 SimpleNamespace 改真 `ICConfig` 為**加強**；未刪斷言換綠。 |
| look-ahead | feature_filter 用 `sorted(column_name)`，無 IC 排序；**無新增 look-ahead**。 |

---

## SPEC / Reconcile 對照摘要

| ID | 狀態 | 備註 |
|----|------|------|
| R-1 TIMEAXIS DatetimeIndex | ✅ | 缺部分邊界測 |
| R-2 BYVOL fail-closed + 預設 False | ❌ | yaml 未改 → 預設仍 raise |
| R-3 預設不截斷 + truncation_mode | ✅ | |
| R-4 sorted max_features | ✅ | 缺 45k |
| R-5 ICConfig feature_filter | ✅ | |
| R-6 Golden 結構化 | ✅ | grouped mask hash + decay float |
| R-7 TDD 紅綠 | ⚠️ | 新增測試存在；單 commit 紅綠未在 review 驗 git history |
| R-8 U-1 cross-sectional to_thread | ✅ | |
| R-9 poll 狀態機 | ✅ | |
| R-10 §A 標籤 | N/A 實作 | |
| R-11 preview_limit | ✅ | 未新建幽靈欄 |
| R-12 1e15 | ⚠️ | 實作有；測試用 1e16 |
| T-1 Golden owner | ✅ | `test_ic_phase0_golden.py` |
| T-2 四處 warning | ✅ | |
| T-3 七欄精確名 | ✅ | |
| T-4 WS message / poll error | ✅ | |
| T-5 truncation_mode 判定 | ✅ | |
| T-6 B2/B3 schema 序 | ✅ | |
| T-7 heartbeat 測試檔 | ✅ | |
| T-8 poll 偽碼 | ✅ | |
| T-9 45k fixture | ❌ | 未實作 |
| T-10~T-12 | ✅ | |

---

## 審查者親跑測試

```
pytest tests/momentum/test_ic_timeaxis.py tests/momentum/test_ic_crash_real_config.py \
  tests/momentum/test_ic_feature_filter.py tests/momentum/test_ic_decay_log.py \
  tests/momentum/test_ic_phase0_golden.py \
  tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop -q
→ 15 passed

cd frontend && npm test -- --run src/hooks/useICAnalysis.test.ts
→ 4 passed

python -c "load_ic_config(); grouped model_dump with by_volatility True → NotImplementedError"
```

---

ASSUMPTIONS_VERIFIED: default yaml by_volatility=True; grouped path with default config raises; Phase0 targeted pytest/vitest green; decay return dict unchanged by code inspection; no weakened assertions in test_ic_filter_orchestrator diff.

TESTS_RUN: see above (15 pytest + 4 vitest + manual default-config repro).

FAILURES_SEEN: none in targeted suite; production default-config grouped path fails by design until yaml fix.

SCOPE_CHANGES: none (review-only).

NUMERIC_OR_SCHEMA_IMPACT: schema `by_volatility` default False (overridden by yaml); `FeatureFilterSchema` added; decay logging only; grouped timestamp parsing semantics fixed.

HANDOFF_NOT_UPDATED: review-only task per user instruction; root HANDOFF.md not modified.

STATUS: DONE
