# Handoff
**Agent**: Claude | **Time**: 2026-07-05 | **Branch**: main

## ★新 session 從這開始：回 IC Analysis（使用者將先手動生成 FF 測試資料）

### 前置：FF 測試資料生成（使用者手動觸發，等資料好才動 IC 端到端）
- **定案 config（2026-07-03 使用者同意）**：BTC+ETH+ADA × 1h（測跨 TF 邊界再加 4h）；L1–L6.5 全開；base/full 全特徵**不綁 preset**；fracdiff/adf 開啟（吃修後 calibration-derived max_lag=50）。~20分/symbol-TF。全量 10×3 定版留到 IC 紅線完成。

### IC Analysis 現況
- **已完成=Phase 1「1a 第一刀」**（三方簽核 PASS，見 docs/ROADMAP.md P0 節）。
- **下一步（依序）**：①1a 第二刀=跨 symbol 防洩漏（SplitPlan per-symbol）→ ②1-align → ③1b FDR → ④1c Net IC → ⑤1d attribution NaN → ⑥1e HAC → ⑦1f 空圖。可插隊：P0.5 grouped_ic 崩潰止血。

## 2026-07-05 完成：TEMPLATE_GATE_FIX epic ✅（派工品質防線修補，全鏈閉合）
- **⚠️ 對所有新 SPEC 的即刻影響**：§RISK 須帶 `RISK-HIT: <a,b,c,d 子集|none>` 宣告行（缺=FAIL）；§A 資料結構事實須附 `FACT-RECEIPT:`（含「已驗證事實」子段）；含 a/d 須真 §G（atol/rtol/sha256，exit/== 不算）；TODO 每 Task 分段驗三欄；RESULT 檔 PASS⇒RECEIPTS 非空、NOT_RUN 禁 DONE 極性（discussion 區有界）。現役舊文件 grandfather（docs/TEMPLATE_GATE_FIX_GRANDFATHER.md，僅新文件適用）。
- **gate 新契約**：`--adversarial`=findings 檔（須 Verdict＋family-scoped ID）、`--reconcile`=戳記 reconcile（每 ID 同行 `→` 處置）；委員派工帶 `--task-id`+`--output`，產出後 `register-output`；戳記格式=`RECONCILE-STAMP: <family> APPROVED <date> sha256:<body-hash> task:<id>`（body hash 用 `scripts/reconcile_body_hash.sh`，戳記區=`## 戳記`）。
- **回歸工具**：`bash scripts/test_template_check.sh`（14 fixture 矩陣，EXPECTED 先驗）＋`--mutate A-1/A-3/A-4/A-5`＋5 個 gate fixture。改 template_check.sh/gate.sh 必跑。
- 驗收鏈：雙家族 adversarial 兩輪（31 findings 全閉）＋Codex 總 review（R1 BLOCKING 修+R2/R3 附證退回+R4 清）＋全部 canonical 戳記 PASS。過程檔=handoffs/2026-07-04-TGF-*、TGF-B*-RESULT、TGF-FINAL-REVIEW-*。
- 事故紀錄：B2 首輪被 --mutate 的 git checkout 還原自毀（未 commit 前提），Claude 獨立驗收攔下→程序改「commit 後才 mutate」＋cp 備份還原；D-1/D-2/檔名/provenance/W3 五項新檢查在真實派工逐一命中並依規補正（防線即刻自證）。

## 前日完成：fracdiff max_lag 大 epic ✅（e6cc51a/6d08556）
- 三方值守恆簽核 PASS+code review APPROVED（出處:handoffs/20260703-FRACDIFF-MAXLAG-*）。storage codec bug→ROADMAP P1。

## 鐵律（慢測試/執行）
- generate_features ~20分/次;slow 跑後 `./scripts/restore_golden_inventory.sh`;長測試後清 pytest 舊輪次(留 pytest-current)。
- 「已驗/passed」須帶 VERIFY:<receipt-id> 或「檔載『…』(出處:檔名)」;委員會過程檔派工帶 --task-id+--output,產出後 register-output。
- pre-existing 失敗=test_ic_engine(非深稽)。派工執行端可能誤還原根 HANDOFF——commit 前重驗內容。
