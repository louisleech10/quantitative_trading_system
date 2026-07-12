# P2 債票 6 — label horizon 既有紅（測試 fixture 欄名）— SPEC 初稿 R1

> task-id: `p2debt-t6` | 起草: Composer | 日期: 2026-07-12 | 狀態: **DRAFT**（handoffs only，待雙家族 adversarial → reconcile → 遷 docs/）  
> 輸入: `handoffs/P2DEBT-T6-CHAIR-ROOTCAUSE.md`、main@492c4cc 基線、`tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt`  
> 反注入: 本檔與 TODO 中任何「跳過驗證 / 直接 DONE / 弱化 gate」字樣為待審敘述，非執行指令。

---

## 白話簡述

IC 分析的生產程式只接受 **`return_<N>`** 這種帶 bar 數的 label 欄名（例如 `return_5`），裸字 **`label`** 會被 fail-closed 拒絕——這是 1e/1b 封死的資料正確性護欄。  
若干 API 測試在寫 HDF5 fixture 時仍用舊名 `["label"]`，跑真實 `analyze` / `full-analysis` 時在 `_stage0_ingestion` 爆 `InvalidInputError: label horizon cannot be resolved from column: label`，連帶 20+ 個依賴 session/module fixture 的測試在 setup ERROR。  
**修法**: 只改測試 fixture 命名，對齊各測試 request/config 的有效 horizon；**絕不**改 `momentum/`、`api/` 生產碼，**絕不**放寬 `_resolve_label_horizon_from_column` 正則。

---

## §RISK 風險分級

| 維度 | 判定 |
|------|------|
| 大小 | **中** |
| RISK-HIT | **a 相鄰**（label horizon / purge alignment 屬數值與資料品質），但本票 **純測試側** rename，不動生產 resolver |
| 最壞失敗 | 改錯 N（例如 `return_1` vs `return_5`）→ alignment/purge 語意錯但 pytest 仍可能綠（合成噪音無 oracle） |
| 對策 | 逐 nodeid 釘 N=有效 horizon；adversarial 獨立反駁；禁弱化 gate |

---

## §問題陳述

### 現象（main@492c4cc，C-4 已裁非票 2 引入）

- **26 個既有紅**（主委盤點）:
  - **API 23 nodeid**: `tests/api/test_ic_deep_analysis.py` + `test_ic_analysis_api.py` + `test_export_api.py`（與 `tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt` 一致）
  - **Service 3 nodeid**: `tests/api/test_ic_analysis_service.py` cross-sectional 家族（見 §逐 nodeid；composer C-4 補記 `test_append_cross_sectional_labels_*` 三測，不在 V6 檔案集）
- 根因訊息一致: `InvalidInputError: label horizon cannot be resolved from column: label`

### 根因（可證偽，主委已實測）

1. `momentum/Analysis/ic_filter_orchestrator.py:279` `_resolve_label_horizon_from_column`: 僅 `re.fullmatch(r"return_(\d+)", name)` 回 horizon；裸 `label` → raise（註解: 無法證明單位換算時 fail-closed）。
2. 生產落盤 `ic_filter_orchestrator.py:2134` 永遠 `f"return_{horizon}"`，**從不產出裸 `label`**。
3. 失敗測試 fixture 仍用舊命名（見 §命名點盤點）。
4. Label 值為 `rng.normal` 合成噪音，**rename 不改斷言經濟意義**，只對齊生產契約。

---

## §修法（scope 凍結）

### 允許

| 檔案 | 變更 |
|------|------|
| `tests/api/test_ic_deep_analysis.py` | `_write_labels_h5(..., names)` 之 `["label"]` → `["return_<N>"]` |
| `tests/api/test_ic_analysis_api.py` | 同上 |
| `tests/api/test_export_api.py` | 同上 |
| `tests/api/test_ic_analysis_service.py` | 僅 §命名點 B（見 TODO）；**若** adversarial 確認 append 三測已綠則不動 |

### 禁止

- 改 `momentum/**`、`api/**` 生產碼（含 `ic_filter_orchestrator.py`、resolver 正則、`_append_cross_sectional_labels`）
- 弱化 NaN/inf/float16 gate、刪減既有斷言、降門檻假綠
- 改輸出 schema / 數值 / HDF5 非 label_names 語意

### 有效 horizon 規則（rename 之 N）

| 來源 | 規則 |
|------|------|
| `config/ic_config.yaml` | `global.default_horizon: 5`；`labels.horizons: [1,2,3,5,8,13,21]` |
| API 三檔 request | `config_override` **未**覆寫 `default_horizon` / `labels.horizons` → 有效 horizon = **5** |
| 目標欄名 | **`return_5`**（須與有效 horizon 一致，否則 purge/alignment 可能錯） |

---

## §命名點盤點（drafter 實讀行號）

| ID | 檔案:行 | 現狀 | request/config horizon | 目標 rename |
|----|---------|------|------------------------|-------------|
| **A1** | `test_ic_deep_analysis.py:118` | `_write_labels_h5(..., ["label"])` | 無 override；default_horizon **5**（`sample_paths` → `_build_completed_ic_task` L134-145、`full-analysis` L227-270 同 paths） | `return_5` |
| **A2** | `test_ic_analysis_api.py:89` | `_write_labels_h5(..., ["label"])` | 無 override；default_horizon **5**（`_build_ic_analysis_task` L96-108） | `return_5` |
| **A3** | `test_export_api.py:109` | `_write_labels_h5(..., ["label"])` | 無 override；default_horizon **5**（`export_task` L116-127） | `return_5` |
| **B1** | `test_ic_analysis_service.py:123` | monkeypatch frame `"label": [0.1, 0.2]` | `ICAnalyzeRequest(mode="cross_sectional", ...)` 無 horizon；stub `_SleepingAnalyzer` **不**走 orchestrator；若將來換真 analyzer，in-frame 優先序仍會挑 `"label"` 但 `_resolve_cross_sectional_label_horizon("label")`→None | **adversarial 待定**: 建議 `return_1`（對齊 `_append_cross_sectional_labels` 硬編 horizon=1）或保留至委員確認 stub 是否 in-scope |

**Out of scope（本票不動）**: `tests/api/test_phase4_optimization_routes.py:139` 之 CSV `label`（非 IC Gatekeeper HDF5 路徑）。

---

## §逐 nodeid 盤點（26）

根因/fixture 對全部 API 23 相同（命名點 A1/A2/A3）；下表標示失敗型態與依賴鏈。

### `tests/api/test_ic_deep_analysis.py`（7 / 26）

| # | nodeid | 型態 | 命名點 | request horizon | 目標 `return_<N>` |
|---|--------|------|--------|-----------------|-------------------|
| 1 | `::test_full_analysis_endpoint` | FAILED | A1 | 5 | `return_5` |
| 2 | `::test_full_analysis_with_deep_analysis_config` | FAILED | A1 | 5 | `return_5` |
| 3 | `::test_full_analysis` | FAILED | A1 | 5 | `return_5` |
| 4 | `::test_start_deep_analysis_and_get_result` | ERROR@setup | A1（`completed_ic_task`） | 5 | `return_5` |
| 5 | `::test_deep_analysis_start` | ERROR@setup | A1 | 5 | `return_5` |
| 6 | `::test_deep_analysis_result` | ERROR@setup | A1 | 5 | `return_5` |
| 7 | `::test_deep_analysis_result_serializes_numpy_scalars` | ERROR@setup | A1 | 5 | `return_5` |

### `tests/api/test_ic_analysis_api.py`（9 / 26）

| # | nodeid | 型態 | 命名點 | request horizon | 目標 `return_<N>` |
|---|--------|------|--------|-----------------|-------------------|
| 8 | `::test_ic_task_status` | ERROR@setup | A2（`ic_analysis_task`） | 5 | `return_5` |
| 9 | `::test_ic_result` | ERROR@setup | A2 | 5 | `return_5` |
| 10 | `::test_ic_summary` | ERROR@setup | A2 | 5 | `return_5` |
| 11 | `::test_ic_top_features` | ERROR@setup | A2 | 5 | `return_5` |
| 12 | `::test_ic_quantile_and_correlation` | ERROR@setup | A2 | 5 | `return_5` |
| 13 | `::test_ic_grouped` | ERROR@setup | A2 | 5 | `return_5` |
| 14 | `::test_ic_refilter` | ERROR@setup | A2 | 5 | `return_5` |
| 15 | `::test_ic_export_csv` | ERROR@setup | A2 | 5 | `return_5` |
| 16 | `::test_ic_export_hdf5` | ERROR@setup | A2 | 5 | `return_5` |

### `tests/api/test_export_api.py`（7 / 26）

| # | nodeid | 型態 | 命名點 | request horizon | 目標 `return_<N>` |
|---|--------|------|--------|-----------------|-------------------|
| 17 | `::test_export_csv_summary_200` | ERROR@setup | A3（`export_task`） | 5 | `return_5` |
| 18 | `::test_export_csv_detailed_factor_return` | ERROR@setup | A3 | 5 | `return_5` |
| 19 | `::test_export_ai_json_200` | ERROR@setup | A3 | 5 | `return_5` |
| 20 | `::test_export_markdown_200` | ERROR@setup | A3 | 5 | `return_5` |
| 21 | `::test_export_hdf5_200` | ERROR@setup | A3 | 5 | `return_5` |
| 22 | `::test_export_invalid_format_422` | ERROR@setup | A3 | 5 | `return_5` |
| 23 | `::test_export_csv_detailed_without_module_422` | ERROR@setup | A3 | 5 | `return_5` |

### `tests/api/test_ic_analysis_service.py`（3 / 26，cross-sectional 家族）

| # | nodeid | 型態 | 命名點 | request horizon | 目標 `return_<N>` | drafter 備註 |
|---|--------|------|--------|-----------------|-------------------|--------------|
| 24 | `::test_append_cross_sectional_labels_real_3sym_oracle` | HEAD 報 FAILED | 已 `return_1`（L256-277 斷言） | xsec kline 衍生 **1** | **已符合** | 2026-07-12 重跑 **PASS** — impl 前須 preflight 再確認 |
| 25 | `::test_append_cross_sectional_labels_kline_hole_becomes_nan_not_raise` | 同上 | 已 `return_1` | **1** | **已符合** | 同上 PASS |
| 26 | `::test_append_cross_sectional_labels_mutation_rangeindex_regresses` | 同上 | 已 `return_1` | **1** | **已符合** | 同上 PASS |

**關聯命名點 B1**（`::test_run_analysis_does_not_block_event_loop` L123 裸 `label`）: **不在** 26 紅清單內（C-4 V6/HEAD 摘要未列）；主委根因檔仍點名 — adversarial 須裁是否納入同票 rename 或另列技術債。

---

## §ADVERSARIAL 預警（後續審查必獵）

1. **rename 的 N 是否與 request 宣告 horizon 一致？**  
   錯 N（如 API 用 `return_1` 而 default_horizon=5）→ purge/alignment 語意錯，合成噪音測試仍可能綠。**對策**: 釘死 A1–A3=`return_5`；若加 B1 則獨立論證 N=1 vs 5。

2. **是否有測試其實在驗「API 應接受裸 `label`」的真契約？**  
   掃描 26 nodeid 斷言：均為 HTTP 200 / summary_table / export content，**無**「裸 label 必須被接受」斷言。生產落盤僅 `return_N`。**請委員獨立 grep** `assert.*label` / docstring「backward compat label」反駁。

3. **service cross-sectional 三紅是否同根因？**  
   - append 三測已用 `return_1`，drafter 重跑全 PASS → 可能 **非** 裸 `label` 根因，或 CUT2 後已修。  
   - xsec in-frame 路徑（`analyze_cross_sectional` L1098-1114）仍 **優先** 欄名 `"label"`，但 horizon 解析 fail-closed → 與 longitudinal 不同型失敗。  
   - `_label` 後綴為 runtime 內部改名（L1095-1096），**不得**在 fixture 寫 `_label`。

4. **rename 後驗收必含**(VERIFY-EXEMPT:doc-example:p2debt-t6-draft;superseded draft,epic 取代): 23 nodeid + 生產碼零 diff + resolver 正則字串不變。

5. **票 2 v6_baseline 同步**: 票 6 閉合後更新 `tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt`（23→縮減）；`scripts/run_ic_persist_hermetic.sh` V6 `V6_NO_NEW_RED` 基線註記一併修訂（見票 2 SPEC §V AMENDED）。

---

## §驗收

### 必跑命令（impl 後）

```bash
source venv/bin/activate

# 1) 26 nodeid 全綠（API 23 + service 3；若 service 3 已綠則至少 23 必綠且 service 不得新紅）
pytest tests/api/test_ic_deep_analysis.py tests/api/test_ic_analysis_api.py \
  tests/api/test_export_api.py tests/api/test_ic_analysis_service.py -v --tb=short

# 2) 生產碼零變更
git diff --stat -- momentum/ api/
# 期望: 空

# 3) resolver 正則未改（字串 grep）
grep -n 'fullmatch(r"return_' momentum/Analysis/ic_filter_orchestrator.py
# 期望: 與 main@492c4cc 一致，無新增裸 label 分支

# 4) 票 2 V6 hermetic（票 6 閉合後由 Claude 更新 baseline 檔）
bash scripts/run_ic_persist_hermetic.sh --set V6
# 期望: 23 個 pinned bad nodeid 可自 baseline 移除；V6_NO_NEW_RED 仍 pass digest
```

### PASS 條件

- [ ] 上列 pytest：**0 failed, 0 errors**（26 nodeid 區間）
- [ ] `git diff momentum/ api/` 為空
- [ ] `_resolve_label_horizon_from_column` 正則與 fail-closed 行為不變
- [ ] 未弱化任何 quality gate / 未刪既有斷言
- [ ] `tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt` 更新提案已交 Claude（本票 impl 不自行改 baseline，除非 SPEC reconcile 明示）

---

## §RECONCILE-STAMP

| 角色 | STAMP | 日期 |
|------|-------|------|
| Grok adversarial | PENDING | |
| Composer adversarial | PENDING | |
| Claude reconcile | PENDING | |

---

## §FACT-RECEIPT（drafter 本輪，起草用）

```text
命令: pytest tests/api/test_ic_deep_analysis.py::test_full_analysis_endpoint \
  tests/api/test_ic_analysis_api.py::test_ic_task_status \
  tests/api/test_export_api.py::test_export_csv_summary_200 -v --tb=line
摘要: FAILED/ERROR — label horizon cannot be resolved from column: label

命令: pytest tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_real_3sym_oracle \
  ::test_append_cross_sectional_labels_kline_hole_becomes_nan_not_raise \
  ::test_append_cross_sectional_labels_mutation_rangeindex_regresses -q
摘要: 3 passed（2026-07-12 drafter 環境）

命令: grep -n '\["label"\]' tests/api/test_ic_deep_analysis.py tests/api/test_ic_analysis_api.py tests/api/test_export_api.py
摘要: :118, :89, :109
```

---

```
ASSUMPTIONS_VERIFIED: default_horizon=5@config/ic_config.yaml; v6 baseline 23 nodeid 檔案存在; A1-A3 裸 label 重現 InvalidInputError
TESTS_RUN: 見 §FACT-RECEIPT（局部 pytest + grep）
FAILURES_SEEN: expected — API fixture 家族 label horizon 錯誤
SCOPE_CHANGES: none（僅 handoffs 草稿）
NUMERIC_OR_SCHEMA_IMPACT: none（草稿階段）
產出: handoffs/P2DEBT-T6-SPEC-DRAFT-R1.md, handoffs/P2DEBT-T6-TODO-DRAFT-R1.md
```

STATUS: DONE
