# IC1EB-B4 Code Review — Composer（委員，非實作者）

**Task**: IC 1e+1b Batch B4（Task 4.1–4.3）全棧接通  
**實作者**: Grok 4.5（自報 `handoffs/IC1EB-B4-IMPL-RESULT.md` — 未採信，獨立驗證）  
**審查範圍**: 工作樹未 commit diff — `ic_config_schema.py`、`ic_filter_orchestrator.py`（`_apply_tier_config` 段）、`frontend/src/{store,types,ICSummaryTable,FeatureTierPanel}`、`tests/momentum/test_ic_1eb_b4_fullstack.py`  
**規格**: `docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` Phase 4 + SPEC D-F/D-G  
**審查時間**: 2026-07-11

---

## 獨立驗證命令（實跑）

| 命令 | 結果 |
|------|------|
| `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_1eb_b4_fullstack.py -q --tb=short` | **7 passed** in 1.77s |
| `rg -n "resolveTStat\|resolveConfidenceInterval\|1\.96" frontend/src/components/ic-analysis/ICSummaryTable.tsx \| wc -l` | **0** |
| `cd frontend && npx tsc --noEmit` | exit 2（**既有** feature-factory 測試型別錯誤 11 處；**B4 改檔無新增錯誤**；編排端已驗 `npm run build` 綠） |〔REF:handoffs/IC1EB-B4-IMPL-RESULT-FIX1.md〕
| `git status --short tests/golden/l65/test_inventory.txt` | 空（l65 inventory **未**被覆寫，無需 restore） |

---

## (1) T-4.1 每跳接點 `significance.fdr.enabled` 鏈 — **PASS**

| 跳接點 | 實作 | 靜默丟失風險 |
|--------|------|--------------|
| Store JSON | `getEffectiveConfig()` → `custom_overrides.stage_overrides.fdr_correction`（`icAnalysisStore.ts:298-299`） | 僅 `featureTier==='custom'` 時送出；toggle 會強制 custom（`:285`） |
| API model | `FeatureTierRequest` → `ICAnalyzeRequest.feature_tiers` → `_build_config_override` deep-merge（`ic_analysis_service.py:1092-1096`） | PASS：結構原樣透傳 |
| `_apply_tier_config` | `STAGE_OVERRIDE_PATHS["fdr_correction"]→("significance","fdr","enabled")` + `_set_nested_bool`（`ic_filter_orchestrator.py:89,3292-3298`） | 若中途巢狀節非 dict 會**靜默跳過**（`:93-106`）；現行 `ICConfig.model_dump` 恆含 `significance.fdr` 預設節，實測 hop 測試已過 |
| stage5 消費 | `_resolve_fdr_enabled(config)` 讀 `config.significance.fdr.enabled`（`:2645-2661`）；`_apply_thresholds(..., fdr_enabled=...)` | PASS |
| report metadata | `significance_meta["fdr"]["enabled"]` + `threshold_log["fdr_enabled"]` 鏡像（`:2562-2601`）；reporter 保留 canonical 節（`ic_reporter.py:477-495`） | PASS；`test_t41_hop_chain_fdr_false_to_report_metadata` 端到 reporter JSON |

**可證偽反例**: 在 `_apply_tier_config` 將 `STAGE_OVERRIDE_PATHS["fdr_correction"]` 改回平鋪 `("significance","fdr_enabled")` 或刪除映射 → `test_t41_hop_chain_fdr_false_*` / `test_t43_mg_*` 應轉紅（store false 但 stage5 仍 ON）。

**備註（非 BLOCK）**: 非 custom preset 路徑不送 `stage_overrides`，FDR 依 schema 預設 ON；三 preset 前端皆 `fdr_correction: true`，與預設一致。關閉 FDR 必須經 toggle→custom，已覆蓋 e2e。

---

## (2) 禁第四種 fdr 命名 — **PASS**

全 repo grep（`fdr:disabled` / `fdr_disabled` / `fdrDisabled` / `enable_fdr` / `use_fdr`）→ **0 命中**。

允許命名（與 SPEC D-G v2.1 一致）：
- **canonical**: `significance.fdr.enabled`（schema + report metadata）
- **UI 邊界**: `fdr_correction`（store / `STAGE_OVERRIDE_PATHS` 鍵）
- **鏡像**: `threshold_log.fdr_enabled`、stage5 回傳頂層 `fdr_enabled`（內部/日誌，非 config 第四命名）

`SignificanceSchema` 無平鋪 `fdr_enabled`（`test_t41_no_flat_fdr_enabled_alias`）。

**可證偽反例**: 在 `SignificanceSchema` 加 `fdr_enabled: bool` 平鋪欄 → `test_t41_no_flat_fdr_enabled_alias` 轉紅。

---

## (3) 兩態 e2e 真路徑 + OFF 判據 — **PASS**

`test_t43_mg_two_state_fdr_gate_separable`：
- 路徑：`store JSON → FeatureTierRequest → ICAnalysisService._build_config_override → ICConfig → _apply_tier_config → _stage5_statistical_validation`（**未 mock** 映射鏈）
- OFF 判據：`significance.fdr.enabled=false` + `threshold_log.fdr_enabled` 恆等鏡像（`:274-282`）
- 兩態 `passed_features` 可分離（主 seed 或 seed sweep `:321-348`）
- p 閘語意：off 態 passed 特徵 raw `p_value≤α`；on 態用 `p_value_adj`（q）（`:308-317`）

**可證偽反例**: 在 `_resolve_fdr_enabled` 硬編 `return True` → 兩態 metadata 相同、`passed_features` 可能相同 → `test_t43` 轉紅。

---

## (4) 前端：nullability / formatter / q / CI / tooltip — **PASS**

| 項 | 證據 |
|----|------|
| 刪 i.i.d. 推導 | `resolveTStat`/`resolveConfidenceInterval` 已移除；grep ICSummaryTable **0** |
| `formatFinite` | 非有限 → `'--'`（`:49-58`）；`p_value`/`p_value_adj`/`t_stat` 皆經此 formatter |
| q 欄 | longitudinal + cross_sectional 表頭皆有 `q`（`:334-343`） |
| CI | cross_sectional 固定 `'--'` + 註解誠實披露（`:393-395`） |
| ic_mean tooltip | `title="描述性 rolling 均值,非檢定量"`（`:318,376`） |
| types nullability | `p_value?: number\|null`、`p_value_adj?`、`t_stat?`（`types.ts`） |
| 舊 report | 後端 `test_t43_legacy_report_null_p_compat_fields_present`；前端 `formatFinite(null)`→`'--'`（讀碼，無元件測試） |

**可證偽反例**: 在 `ICSummaryTable` 恢復 `item.p_value.toFixed(4)` 且 `p_value: null` → runtime throw；或恢復 `1.96*ic_std` CI 推導 → grep 非 0。

**FINDING（低，非 BLOCK）**: `FeatureTierPanel` tip 寫「p 閘用 q」適用 longitudinal 門檻；xsec 路徑無 p 閘（D-H），但 q 欄仍正確顯示。文案略偏 longitudinal，不構成幽靈開關。

---

## (5) `ic_config_schema` 其他欄預設未動 — **PASS**

diff 僅新增 `SignificanceFdrSchema` / `SignificanceSchema` + `ICConfig.significance` 欄；既有欄位預設值 diff 無改動。`test_t41_schema_default_fdr_on` 驗舊 JSON 無 significance 節 → 預設 ON。

---

## (6) xsec 路徑消費 schema（Task 4.1③）— **PASS（讀碼；無專項測試）**

`analyze_cross_sectional`：
- `maxlags=_config_significance_maxlags(config)` → `_compute_hac_on_ic_series`（`:1225-1228`）
- `fdr_enabled = self._resolve_fdr_enabled(config)`；`apply_fdr` 填 `p_value_adj`；metadata `significance.fdr.enabled`（`:1262-1320`）

**FINDING（低，非 BLOCK）**: B4 測試僅 stage5 hop + maxlags；**無** xsec `fdr_correction=false` e2e。行為已由讀碼確認，建議 B5 前可補一條 xsec metadata 斷言（非本刀阻塞）。

**可證偽反例**: 移除 xsec 的 `_config_significance_maxlags` 傳遞 → xsec `significance.maxlags` 與 schema 脫鉤（現無回歸測試會紅，屬覆蓋缺口非實作錯誤）。

---

## 其他觀察

- `_set_nested_bool` 靜默跳過語意與舊 `isinstance(data.get(section), dict)` 同型；在 schema 預設嵌套存在下實測安全。
- `test_t43` 內 `_gate_features` 輔助函式邏輯冗餘（最終仍讀 `passed_features`），不影響斷言有效性。
- 工作樹另有 `.claude/gate/*`、`.claude/settings.json` 變更 — **非 B4 審查範圍**。

---

## 結構化摘要

```
ASSUMPTIONS_VERIFIED: hop 鏈經 pytest 7/7；ICSummaryTable iid grep=0；xsec schema 消費讀碼確認；l65 inventory 未動
TESTS_RUN: pytest tests/momentum/test_ic_1eb_b4_fullstack.py -q → 7 passed；tsc --noEmit → 既有 feature-factory 錯誤（B4 檔無新增）
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅產出本 review 檔）
NUMERIC_OR_SCHEMA_IMPACT: 與實作者聲明一致——新增 significance schema 節、前端 q 欄與 nullability；未發現未聲明之數值改動
FINDINGS_NON_BLOCK: (a) xsec fdr hop 無專項測試 (b) 非 custom preset 依 schema 預設 ON 而非顯式 override (c) FeatureTierPanel tip 略偏 longitudinal
```

VERDICT: PASS
