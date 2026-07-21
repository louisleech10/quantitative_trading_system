# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-21 | **Branch**: **main** | **狀態**: ✅ **1d SPEC v0.5.2 + TODO v0.3 FROZEN;下一步=逐批實作 B0**

## ▶ 立即續作:逐批實作 B0(壓縮後從這裡接)
依 `docs/IC1D_ATTRIBUTION_TODO.md` v0.3 FROZEN,批次 B0-B5(依 Phase 依賴)。**B0 = baseline + comparator**:
1. 新建 `scripts/ic1d_baseline_freeze.py`(類比 `ic1cfr_stopgap_freeze.py`;支援 `--profile {p0,p1,p3}`;輸出 `handoffs/ic1d_baseline/`)。
2. 新建 `scripts/ic1d_compare.py`(CLI subtree 語意;atol=1e-12/rtol=1e-9;NaN↔NaN 相等;禁 brace,15 條字面路徑)。
3. 新建 `tests/momentum/Analysis/test_ic1d_baseline.py`(module_summary!=skipped + **同源斷言**:close carrier 經 production `:2913-2930` 注入非 ad-hoc + analyzer real-OLS oracle → `analyzer_oracle.json`)。
4. dump `p0_before.json`。**close 一律有效**(非 all-NaN;C3 errata:all-NaN raise 屬 production-hardening 另票)。
- **分工**:Grok 實作/Codex+Composer 雙審/Claude 獨立驗(mutation 可證偽)/批間 Gate(pytest exit=0)。**派工 brief task_id 逐字元列死+用 Edit 核對非盲 replace**(本 session 血淚)。

## ✅ 1d SPEC v0.5.2 + TODO v0.3 FROZEN(body sha256:4109a47b;三家戳記+provenance)
- **交付定義**:幽靈契約隔離(explicitly not wired),caller 仍為 0。單標的宇宙 OLS 只識別 position 重疊→接真拆票A/票B(Phase 4/ML epic)。
- **6 批 B0-B5**:B0 baseline/B1 正名(pure analyzer,deep no-op)/B2 fail-closed(NaN+inf+輸出溢位+index)/B3 stub→unavailable+completed_partial 外顯(20 路徑白名單)/B4 測試去固化+**7 支 mutation 探針**(analyzer 5+整合 2,2 檔)/B5 前端(TS+Radar+ExportButtons)。
- **13 §D + §D-MAP**。收斂:SPEC BLOCKING 9→0(6輪 adversarial+多輪戳記);TODO 三家 adversarial(codex+composer v0.1 + Grok v0.2)+ closure。
- **C3 委員分歧 Grok HYBRID 裁決**:不擴 scope 改 production(Composer)+ 須 errata 戳記(Codex)+ 專輪非六輪(中間態)。SPEC v0.5.2 errata:C3/N1/N2/N4 措辭對齊。

## ⚠️ 本 session 血淚(GOV-XREF-SYNC 票要機械化的)
- **交叉引用不同步 11 次**(改決策漏同步引用);戳記卡多輪根因=**我 brief 列死 task_id 從沒更新**(盲 s.replace 全 no-op),codex 一直忠實照抄。記憶:`feedback_dispatch_blocked_investigate_cause`(委員反覆錯先查我的 brief)、`feedback_cross_reference_sync`、`feedback_gate_script_full_attack_surface`。
- **reconcile 舊 task_id 是委員抄錯源**→已脫敏;**改文字用 Edit 核對非盲 replace**;grep/機檢驗證勿截斷(犯 3 次)。
- agy(Gemini 3.5 Flash High)能力測試=半對等(結構審尚可,深度弱+不查證下 finding);記憶 `feedback_gemini_research_only`。

## 📌 pre-existing 債(非本票)
Rule 4 `pattern_management_service.py:78`、`ModuleUnavailableError` 死碼、`prediction_analyzer.py:163` cumsum 命名說謊、`analyze_cross_sectional` 繞過 deep 棧、ROADMAP residual IC 表/敘事不一致。
commit 待決:`handoffs/` 本機排除,審計鏈+含戳記 reconcile 需明確 `git add`(問過未回)。
