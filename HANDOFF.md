# Handoff
**Agent**: Claude | **Time**: 2026-06-25 | **Branch**: main

## ★下一個任務（新 session 開工）：IC 修法 Phase 1 — 正確性 kernel + contract
- **直接讀**：`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`（§Phase 1，四家委員會收斂）。級別：**中（2-4 週，cursor 警告別低估）**，命中 (d) ML 正確性 → 走完整管線。
- **核心排序**：**Contract-First**（先定 RowMask/split、artifact output、FDR scope、candidate set 契約，避免返工）→ 正確性 kernel 落在新契約上（當未來串流的 ground truth）。**不要**硬接舊全 DataFrame 路徑。
- **Phase 1 範圍**：1-contract（split/mask/FDR scope 契約）→ 1a train/test split（index/timestamp 遮罩）→ **1-align 前瞻偏誤硬閘**（Feature_t vs Target_t+1 對齊，差 1 tick IC 爆，Gemini 紅線）→ 1b FDR 接線 → 1c Net IC 量綱（Grinold+turnover/autocorr）→ 1d factor_attribution 真接或正名 proxy → 1e HAC/block bootstrap（rolling IC 自相關+重疊報酬）→ 1f 靜默空圖修。並行軌：薄串流脊骨（direct L7 + chunk iterator，讓 45K 可互動）。
- **三方數據正確性簽核鐵律**（CLAUDE.md）：split/leakage/merge 正確性須 Claude+Codex+Composer 三方獨立簽核，用真實 kline，不靠使用者驗收。
- **起手式**：讀 phasing CONVERGED + Phase 1 各家獨立版（phasing-{CLAUDE,CODEX,CURSOR,GEMINI}）→ 級別宣告 → manifest→SPEC→雙家族 adversarial→TODO→gate→派工→接回。

## ✅ 上一任務：IC Phase 0 — 完成、實機驗證、已 commit+push（`11507f5`）
- **6 epic 全落地**：CRASH(model_dump)/TIMEAXIS(DatetimeIndex+秒實測+fail-closed)/BYVOL(預設 False+yaml+raise)/FEATURE-GUARD(預設不截斷+sorted+truncation_mode)/DECAY-LOG(移4 warning+一行)/UX-ERR(兩路 to_thread + WS run_coroutine_threadsafe + 前端清 stale 錯誤)。
- **驗收**：118 IC pytest + 6 vitest pass；golden 3 baseline；**實機 smoke** 45k run 完成、grouped by_year=2024/25/26（非1970）、feature_filter 45375→50、WS 不再假連線失敗。
- **3 bug 各層攔下**：_stage5 regression(pytest)、yaml by_volatility(Composer review)、WS to_thread(實機 smoke)。
- **全程留痕**：`handoffs/20260625-ic-PHASE0-*`（brief/manifest/SPEC/TODO/雙輪雙家族 adversarial/code review/impl 報告）；SPEC/TODO 在 `docs/IC_PHASE0_{SPEC,TODO}.md`。

## 背景：IC-Analysis 全覆蓋地圖入口 `handoffs/20260624-ic-map-00-INDEX.md`；記憶 [[project_ic_analysis_map]]
## 維運：清理 data_cache 孤兒 scratch（ETHUSDT_1h_e80ce796 4.7GB），11G→5.8G；真實 features/kline 完好。
