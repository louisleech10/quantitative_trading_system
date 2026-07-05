# Handoff
**Agent**: Claude | **Time**: 2026-07-04 | **Branch**: main

## ★新 session 從這開始：回 IC Analysis（使用者將先手動生成 FF 測試資料）

### 前置：FF 測試資料生成（使用者手動觸發，等資料好才動 IC 端到端）
- **定案 config（2026-07-03 使用者同意）**：BTC+ETH+ADA × 1h（測跨 TF 邊界再加 4h）；L1–L6.5 全開；base/full 全特徵**不綁 preset**；fracdiff/adf 開啟（吃修後 calibration-derived max_lag=50，舊 d\* cache hash 改變自動重算=預期）。~20分/symbol-TF。全量 10×3 定版留到 IC 紅線完成。

### IC Analysis 現況
- **已完成=Phase 1「1a 第一刀」**（單幣縱向接線，default ON，三方簽核 PASS，見 docs/ROADMAP.md P0 節）。
- **下一步（依序）**：①1a 第二刀=`analyze_cross_sectional` 跨 symbol 防洩漏（SplitPlan 須 per-symbol）→ ②1-align → ③1b FDR → ④1c Net IC 量綱 → ⑤1d attribution NaN → ⑥1e HAC → ⑦1f 空圖。
- **可插隊：P0.5 grouped_ic 崩潰止血+效能**（reconcile 完成、實作未啟動；epic=handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md）。

## 2026-07-04 完成：SPEC/TODO/Adversarial template 四方委員會審查 ✅（審查結論，未實作）
- 委員：Claude+Codex(GPT-5.5)+Composer2.5+Gemini3.1Pro；各自產獨立版→交叉詰問→reconcile。
- **結論檔=handoffs/2026-07-04-template-review-RECONCILE.md**（過程檔同日期前綴 7 份）。
- 要點：V13 設計保留不推翻；**2 BLOCKING 經 Composer 探針實證**——①FACT-RECEIPT 機檢綁「已確認」可被「已驗證事實」繞過（現役 IC_PHASE0_SPEC 即中招）②高風險可 §N 標「§G:N/A」逃 Golden。+per-Task 全域 grep、adversarial 缺實跑反例條款、finding 閉合機制、治理文件 6 處舊錨點 §1.0/§1.4、TODO 生成每次全讀 5,100 行憲法（改 AGENTS.md+按需）。
- **修補=中～大任務（命中 (b) 共用路徑）**，動工須完整管線；RECONCILE-STAMP pending。待使用者決定是否排 epic。

## 前日完成：fracdiff max_lag 大 epic ✅（e6cc51a/6d08556 已 push）
- 三方值守恆簽核 PASS+code review APPROVED（出處:handoffs/20260703-FRACDIFF-MAXLAG-*）。兩 MR=誠實 xfail 未轉綠（pre-existing storage codec bug→ROADMAP P1）。

## 鐵律（慢測試/執行）
- generate_features ~20分/次;slow 跑後 `./scripts/restore_golden_inventory.sh`;長測試後清 pytest 舊輪次(留 pytest-current)。
- 「已驗/passed」須帶 VERIFY:<receipt-id> 或「檔載『…』(出處:檔名)」;委員會過程檔派工帶 --task-id+--output,產出後 register-output。
- pre-existing 失敗=test_ic_engine(非深稽)。派工執行端可能誤還原根 HANDOFF——commit 前重驗內容。
