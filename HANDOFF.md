# Handoff
**Agent**: Claude | **Time**: 2026-06-24 | **Branch**: main

## ★下一個任務(使用者 2026-06-24 定案,待新 session 開工)：IC 修法 Phase 0 止血+正確性硬閘
- **直接讀**:`handoffs/20260624-ic-PHASE0-DEFINITION.md`(完整範圍 + 決策 baked in + 起手式)。照那份走完整 SPEC 管線。
- **範圍**:IC-CRASH(GroupedConfig 崩潰)+ IC-FEATURE-GUARD(feature_filter 幽靈落地,是 Phase 2 前置)+ IC-UX-ERR(to_thread/WS)+ IC-TIMEAXIS(秒當毫秒)+ IC-BYVOL + decay log 聚合。級別:大(b)(d),走完整管線。
- **已定決策**:起點=Phase 0;walk-forward/CPCV **复用 ML 孤島**(非重寫);不碰串流/train-test/case-control(留後 Phase)。
- **狀態**:已定義,**實作未啟動**(使用者另開新 session 做)。

## 背景：IC-Analysis 全覆蓋地圖（四家委員會,2026-06-24,已交付）
- **入口**:`handoffs/20260624-ic-map-00-INDEX.md` → `WHOLEMAP.md`(+ STAGE{1-5}-FINAL;過程留痕在 `ic-map-trail/`)。
- **核心結論**:IC 主流程**幾乎無防偽護網** + 多幽靈/算錯(系統性發現 A-H)。記憶 [[project_ic_analysis_map]]。
- **分階段計畫**:`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`(七 Phase,contract-first+雙軌)。大尺度架構 `ic-optimization-CONVERGED.md`;Agent 顧問層=ROADMAP P2。

## 前一任務：IC Gatekeeper Run 選擇器重做 — 實作完成待使用者驗收

**目標**：ic-analysis 從 Feature Library 選擇無法辨識批次 + 後端 find_latest 靜默挑最新 run（無法選舊批次）。改為「批次分組 Run 選擇器」+ config_hash 端到端精確命中。

**完成範圍（大任務，命中 (b)(d)）**
- 後端：ICAnalyzeRequest 加 config_hash/cross_sectional_runs；ic_analysis_service 用 registry.get + find_latest_materialized；feature_library load/load_multi optional config_hash **fail-closed**（明確 hash 缺失→raise，不靜默 fallback legacy）；list_features_v2 帶 tf；list_runs 補 training_timeframes。
- 前端：ICConfigPanel 批次分組 Run 下拉（global/event 單選、cross_sectional 選同質 batch+tf）；移除貼路徑欄；啟動 gate；page fetchRuns 三態 + 清 stale features。

**流程留痕（可稽核）**：handoffs/20260623-ic-run-selector-{DESIGN,MANIFEST,ADVERSARIAL-RECONCILE,CODEX-REVIEW,IMPL}.md；docs/IC_RUN_SELECTOR_{SPEC,TODO}.md。
規劃委員會(codex+cursor) → 雙家族 adversarial(12 BLOCKING) → Composer 實作 → Codex review(5 BLOCKING 含 fail-closed) → Composer 修補 → Claude 獨立驗收。

**驗收結果（Claude 自驗，非信報告）**
- pytest 全套 **1215 passed**；4 failed 全 pre-existing（batch_alias/worker_logging/optimization e2e·perf，stash 乾淨亦 fail，無關）。
- golden marker gate **11 passed**（同 sym+tf 不同 hash 消歧 + 向後相容 + 真 ML caller）。
- fail-closed 邏輯讀碼確認（feature_library.py:99-183）。前端 vitest 5 passed、build PASS、postflight data_cache 無縮減。

**未做 / 待辦**
- 尚未 commit（待使用者決定）。
- 使用者宜在跑起來的 UI 實際操作驗收（原始需求是 UX）。
- registry 有 orphan 無資料 run（4d26a4/5218729）；materialized resolver 已跳過，未清理。
- Codex 對 fail-closed #1 回審未跑（Claude 已讀碼驗證，視需要可補）。
