# Handoff
**Agent**: Claude | **Time**: 2026-07-03 | **Branch**: main

## ★新 session 從這開始：回 IC Analysis（使用者將先手動生成 FF 測試資料）

### 前置：FF 測試資料生成（使用者手動觸發，等資料好才動 IC 端到端）
- **定案 config（2026-07-03 使用者同意）**：BTC+ETH+ADA × 1h（測跨 TF 邊界再加 4h）；L1–L6.5 全開；base/full 全特徵**不綁 preset**；fracdiff/adf 開啟（吃修後 calibration-derived max_lag=50，舊 d\* cache 因 hash 改變自動重算=預期）。成本 ~20分/symbol-TF。
- 全量 10 symbols×3 TF 定版**不是現在**：留到 IC 正確性紅線完成、真開研究時。

### IC Analysis 現況（做到哪）
- **已完成=Phase 1「1a 第一刀」**（單幣縱向接線，default ON，三方簽核 PASS，見 docs/ROADMAP.md P0 節）：holdout 切分+train-only fit+OOS 報告+purge≥horizon 防前瞻。docs/IC_PHASE1_1a_CUT1_{SPEC,TODO}。
- **下一步（依序）**：①**1a 第二刀=`analyze_cross_sectional` 跨 symbol 防洩漏**（新 FF 測試資料正為此準備，≥2 symbols 才測得到跨界；SplitPlan 須 per-symbol，見 memory ic_phase1_decisions）→ ②1-align → ③1b FDR 接線（幽靈：43 萬檢定≈2.1 萬假陽性）→ ④1c Net IC 量綱 → ⑤1d attribution NaN 繞過 → ⑥1e HAC → ⑦1f 空圖。
- **可插隊：P0.5 grouped_ic 崩潰止血+效能**（使用者實測 analyze 卡死；reconcile 完成、實作未啟動；epic=handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md）。
- 背景：IC 79 單元測試全合成資料，P0 目標=真實 kline 端到端；IC 全覆蓋地圖見 memory ic_analysis_map+ROADMAP P0 節。

## 剛完成（本日兩 commit e6cc51a/6d08556 已 push）：fracdiff max_lag 大 epic ✅
- max_lag 解耦 len(df)（resolver seam=50）+config 顯式欄位（修 pydantic 靜默丟棄）+FFT 卷積改 direct（雙處）。三方值守恆簽核檔載「PASS」（出處:handoffs/20260703-FRACDIFF-MAXLAG-CONSERVATION-{claude,codex,composer}.md）；§G 檔載「passed=true, failures=[]」（出處:run_receipts/20260703T085226Z-fracdiff-maxlag-postfix-compare.json）；code review 檔載「FINAL VERDICT: APPROVED」（出處:handoffs/20260703-FRACDIFF-MAXLAG-REVIEWCLOSE-composer.md）。
- **⚠️ 兩 fracdiff MR=誠實 xfail 未轉綠**：掀出 pre-existing storage codec bug（float16/32 依全窗值域選型；根因見雙戳記檔 handoffs/20260703-FRACDIFF-MAXLAG-R3-RECONCILE.md；ROADMAP 新 P1「FF storage codec 截斷變異」）。對固定窗全量生成無影響（單 run 自洽，出處:CONSERVATION-claude.md §3）。max_lag 護網：3 mutation 檔載「PASSED」（出處:run_receipts/20260703T094044Z-fracdiff-maxlag-convfix-slow.log）+單邊 calibration 控制檔載「1 passed」（出處:run_receipts/20260703T132059Z-fracdiff-maxlag-d2-control-final.log）+P1-FF-6 七 cache mutant（出處:run_receipts/20260703T053419Z-mutation-test_dstar_cache_key_mutation receipt）。
- 新排程：ROADMAP P2「FF preset 移除盤點」（IC 紅線後做，不擋事）。golden 大檔已 gitignore（7.5GB artifacts 留本地）。

## 鐵律（慢測試/執行）
- generate_features ~20分/次;slow 跑後 `./scripts/restore_golden_inventory.sh`;長測試後清 pytest 舊輪次(留 pytest-current)。
- 「已驗/passed」須帶 VERIFY:<receipt-id> 或「檔載『…』(出處:檔名)」;委員會過程檔派工帶 --task-id+--output,產出後 register-output。
- pre-existing 失敗=test_ic_engine(非深稽)。派工執行端可能誤還原根 HANDOFF——commit 前重驗內容。
