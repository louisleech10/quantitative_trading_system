# IC1EB-B3 Code Review — Composer 2.5（委員，非實作者）

**Date**: 2026-07-11 | **實作者**: Grok 4.5 | **審查對象**: 工作樹未 commit diff  
**Scope**: `momentum/Analysis/ic_filter_orchestrator.py`（`analyze_cross_sectional` 段 + resolver/HAC helper）、`tests/momentum/test_ic_1eb_b3_xsec.py`（新建）、`tests/momentum/Analysis/test_ic_1a_cut1_oos.py`（簽名適配）  
**規格**: `docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` Phase 3 Task 3.1 + SPEC §A D-H(v2)  
**實作者自報**: `handoffs/IC1EB-B3-IMPL-RESULT.md`（未採信，獨立驗證）

---

## 獨立驗證 receipt（委員實跑）

| 命令 | 結果 |
|------|------|
| `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_1eb_b3_xsec.py -q` | **8 passed** in 1.70s |
| `OPENBLAS_NUM_THREADS=1 venv/bin/python scripts/ic1eb_b3_mutation_probe.py` | exit 0；A(iid-swap) red exit=1；B(label-rename) red exit=1；restore sha ok |
| `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py -q` | **13 passed** in 0.62s |
| `git status tests/golden/l65/test_inventory.txt` | clean（mutation probe 未污染 l65 inventory） |

編排端自報（1023 綠 / xsec G-1 五 hash / ICIR 排序 hash / p_value 500/500 / p_value_adj 在）本輪未重跑 full gate；B3 單元 + mutation 已獨立複驗。

---

## 逐項審查（對審查要求 1–7）

### (1) horizon 於 `_label` 改名前對原始欄名解析（labels_path + in-frame 兩分支）

**PASS**

**證據（讀碼）**  
- labels_path 分支（`:1026–1034`）：`_select_label_series` 後、寫入 `working_df["_label"]` **之前**，以 `label_series.name`（或 `labels_df.columns[0]` fallback）賦 `horizon_source_name`，再 `_resolve_cross_sectional_label_horizon(horizon_source_name)` → `sig_horizon`。  
- in-frame 分支（`:1038–1042`）：命中候選欄名（`label`/`return_1`/…）當下即解析，之後才定 `label_col`。  
- 兩分支皆未對改名後的 `"_label"` 做 horizon 解析。

**可證偽反例**  
- 若把 `:1032` 移到 `label_col = "_label"` 之後並改解析 `_label` → `test_t31b_labels_path_return_5_maxlags_floor` 紅（`horizon_unresolved is True`）；mutation probe B 已實跑轉紅（receipt: `assert True is False` @ test:184）。

---

### (2) h=None → p 族全 NaN + metadata `horizon_unresolved`；禁 fallback h=1 假 horizon；禁反保守 p

**PASS**

**證據（讀碼）**  
- 顯著性分支（`:1148–1152`）：`sig_horizon is None` 時 `t_stat`/`p_value` 全 `nan`，不呼叫 HAC。  
- FDR 後 `p_value_adj` 對全 NaN p → `n_tests=0`（`:1189–1196` + T-3.1c）。  
- metadata（`:1238–1240`）：`horizon_unresolved: bool(sig_horizon is None)`、`label_horizon: sig_horizon`。  
- `structural_horizon=1`（`:1058–1060`）**僅**供 coverage/split purge；顯著性路徑用 `sig_horizon`，兩者分離且註解明示。

**可證偽反例**  
- 若 `sig_horizon is None` 時改餵 `_compute_hac_on_ic_series(values, structural_horizon)`（h=1）→ 對不可解析欄名 `label` 會產出有限 p（反保守）；T-3.1c 斷言全非有限 p 會紅。  
- `_resolve_cross_sectional_label_horizon("label")` → `None`（非 1）；單元 `test_t31b_resolve_on_label_renamed_is_none` 已鎖。

---

### (3) t_stat = HAC 取代 :1077 i.i.d.；mutation 換回 iid → 紅 receipt 真實性

**PASS**

**證據（讀碼 + 實跑）**  
- 舊式 `ic_mean / (ic_std / sqrt(n))` 已移除；`:1154–1157` 改呼叫 `_compute_hac_on_ic_series`（NW Bartlett、`L=max(auto_bw,h-1)`、雙尾 t，與 D-A / `statistical_validator._newey_west_bartlett_se` 同源）。  
- T-3.1a：summary `t_stat`/`p_value` 與 helper 直算 allclose；statsmodels HAC oracle rtol=1e-8；HAC t ≠ i.i.d. t（rtol=1e-3）。  
- `scripts/ic1eb_b3_mutation_probe.py` mutation A（iid-swap）**委員實跑**：baseline 綠 → 注入 i.i.d. t → `test_t31a_xsec_p_not_none_matches_kernel_and_separates_iid` **FAILED**（red exit=1）→ restore 後再綠。

**可證偽反例**  
- 保留 i.i.d. t 且維持 T-3.1a 分離斷言 → 在 `ar_rho=0.9` 合成資料上必紅；probe 已證。

---

### (4) `_resolve_cross_sectional_label_horizon` fallback-1 收斂；禁留兩套

**PASS**

**證據（讀碼）**  
- 舊實作（diff 前）：`return_(\d+)` 否則 **return 1**。  
- 新實作（`:375–384`）：委派 `_resolve_label_horizon_from_column`；`InvalidInputError` → `None`（Optional）。  
- 單一 regex/單位規則真相源在 `:250–259`；xsec 不再維護獨立 fallback-1 邏輯。  
- `analyze_cross_sectional` 僅呼叫 `_resolve_cross_sectional_label_horizon`，無第二套 inline 解析。

**可證偽反例**  
- 若恢復 `return 1` fallback → `return_5` 經 `_label` 誤解析場景會產 h=1 有限 p；T-3.1b maxlags floor 與 M-J 斷言會偏離。

---

### (5) apply_fdr 對該路徑全 feature

**PASS**

**證據（讀碼 + 單元）**  
- `:1178–1196`：對 `summary_table` **每一列**建 `p_values_map`（含 NaN），`apply_fdr(p_values_map, alpha_for_fdr)` 後寫回 `p_value_adj`。  
- `n_tests` 入 metadata `significance.n_tests`（finite p 計數）。  
- `test_t31_fdr_q_matches_apply_fdr`：逐 feature `p_value_adj` 與直算 `apply_fdr` allclose。

**可證偽反例**  
- 若僅對 finite-p 子集建 map 或跳過 NaN feature → `n_tests` 與 q 保位與 stage5 契約不一致；T-3.1a `n_tests == finite_p` 與 T-3.1c `n_tests==0` 會紅。

---

### (6) 不加門檻、不動排序（讀碼確認無繞過分支）

**PASS**

**證據（讀碼）**  
- `analyze_cross_sectional` 內 **無** `_apply_thresholds` / `passed_features` / feature 淘汰。  
- `summary_table` 排序（`:1198–1206`）仍 sole key = `icir` desc；`total_features_output == len(feature_cols)`。  
- `fdr_enabled`（`:1187`）僅寫 metadata 披露；**不** gate `apply_fdr`、不影響排序（與 stage5「先算 q、閘在別處」一致；xsec 無 p 閘）。  
- `test_t31_sort_still_by_icir_no_threshold`：輸出 2 feature、ICIR 遞減序。

**可證偽反例**  
- 若在 sort 前 `summary_table = [r for r in ... if r["p_value"] < 0.05]` → `len(table)==2` 斷言可過但 feature 數會縮；現碼無此分支。編排端 G-1 五 hash + ICIR 排序 hash MATCH 與讀碼一致。

---

### (7) M-J：labels_path `return_5` → maxlags≥4 可達性；禁擅自加單軸支援

**PASS**

**證據（讀碼 + 單元）**  
- 生產碼仍 **raise** 單軸 labels_path（`:1012–1015`：`cross_sectional labels_path 單軸不支援`）；未放寬。  
- T-3.1b 做法合規：monkeypatch `_load_labels_hdf5` 回傳 **MultiIndex** `labels_df`（欄 `return_5`）；`features` 去掉 in-frame `return_1` 強制走 labels_path；索引 `sort_index` 滿足 `_normalize_cross_sectional_labels_index` monotonic 守衛。  
- 斷言：`label_horizon==5`、`horizon_source_name=="return_5"`、`maxlags>=4` 且 `== max(auto_bw,4)`（n≈48 使 auto_bw<4）。  
- mutation「改名後對 `_label` 解析」探針 B 已實跑轉紅。

**可證偽反例**  
- 若為測試加單軸 labels_path 支援 → `:1012` raise 應刪除；現碼未動。  
- 若仍對 `_label` 解析 horizon → `sig_horizon=None`、`maxlags` 無 h-1 floor；probe B 已證紅。

---

## 附帶 diff：`test_ic_1a_cut1_oos.py`

**PASS（範圍內簽名適配）**  
僅為 `_stage5_statistical_validation(..., metadata={"symbol": "BTCUSDT"})` 補齊 B2 後必要參數；與 B3 xsec 邏輯無耦合。13/13 綠。

---

## 非阻擋觀察（記錄，不升級 FINDING）

| 項 | 說明 |
|----|------|
| O-1 | `_compute_hac_on_ic_series` 為 xsec 專用 z=逐期 IC 的 HAC 薄封裝，與 bar-level `compute_hac_ic_statistics` 分離；符合 D-H「z 序列定義不同」，但長期需防公式漂移（現與 D-A 公式逐行一致）。 |
| O-2 | `_resolve_cross_sectional_label_horizon(..., None)  # type: ignore[arg-type]`：runtime 安全（被調方 `del config`），屬型別噪音。 |
| O-3 | `test_t31a_iid_mutation_would_fail_separation` 為 tautology 守衛；真紅 receipt 以 `ic1eb_b3_mutation_probe.py` 為準（已實跑）。 |〔REF:handoffs/IC1EB-B3-IMPL-RESULT.md〕

---

## 結構化摘要

```
ASSUMPTIONS_VERIFIED: horizon 改名前雙分支解析；sig_horizon 與 structural_horizon 分離；HAC 公式與 D-A 一致；單軸 labels_path 仍 raise
TESTS_RUN: pytest test_ic_1eb_b3_xsec.py → 8 passed; mutation_probe → exit 0 (A/B 皆轉紅); test_ic_1a_cut1_oos.py → 13 passed
FAILURES_SEEN: none（審查輪）
SCOPE_CHANGES: none（僅產出本 review 檔）
NUMERIC_OR_SCHEMA_IMPACT: 與實作者聲明一致——xsec p_value None→HAC float/NaN；增 p_value_adj/t_stat HAC/metadata；ic_mean/icir/排序路徑無門檻分支（讀碼+單元守衛）
```

VERDICT: PASS
