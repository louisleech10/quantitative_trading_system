# Handoff
**Agent**: Claude | **Time**: 2026-07-03 | **Branch**: main

## ★新 session 從這開始：fracdiff max_lag 大 epic（P1-FF-6 已併入）
- **為何**:`max_lag = min(max(2, len(df)//10), 252)` 把總長度洩進 d* 計算 → 截斷不變性破壞(非 look-ahead,量化因果安全,但真缺陷)。詳見 docs/ROADMAP.md「P1 — fracdiff max_lag」節+三腿檔 `handoffs/20260702-FF-DSTAR-GATE-{CLAUDE,CODEX,COMPOSER}.md`。
- **定序(使用者 2026-07-02)**:本 epic 修 max_lag(改 calibration/固定推導;**會改全部 fracdiff 特徵值**,命中 (a)(d))→ 2 個 strict-xfail 截斷測試轉綠 → **重生成 FF 定版給 IC**。
- **管線要求(大任務)**:給使用者的白話簡述/決策文件 → manifest → SPEC/TODO → **雙家族 adversarial(Codex+Composer 各一次)** → Codex 實作+Composer review(2026-07-02 使用者定路由) → 三方值守恆簽核(真實 kline,禁合成 fixture)。
- 相關 memory:project_dstar_first500_optionA(d* 前500校準;固定參考 d* 是未來修法)、project_stateful_param_audit。

## 前一 session 完成(2026-07-03,兩批皆已 commit+push)
- **P1-FF-5/7 ✅**(`41c2df7`):跨symbol值隔離+wrapper路徑測試;4輪 adversarial 閉合;slow 全鏈 receipt 檔載「1 passed in 992.47s」(出處:run_receipts/20260702T203429Z-p1ff57-slow-fullchain-v3.log)。殘餘:B-5 兩污染面 defer(入 ROADMAP)。
- **GOV-O3EXT-R7 ✅**(本次 commit):verify-gate 待修項清零——①R7-emitter:任何帶 --task-id 派工留痕+`gate.sh register-output`(先行 dispatch 強制/拒 legacy-*/json.dumps 防注入);②O3 檔案類豁免:committee audit log+raw bytes sha256 綁定,改一字失效,HANDOFF/docs 不豁免,逃生口 VERIFY_GATE_O3_FILECLASS=0;③11 份委員會過程檔已註冊、checker exit 0、隨本批補 commit。SPEC/TODO adversarial F1-F7 全 CLOSED+code review 檔載「FINAL VERDICT: APPROVED」(出處:20260703-GOV-O3EXT-R7-REVIEW-composer.md)。governance 檔載「124 passed」(本 session pytest;基線106+18新)。
- **路由變更(使用者定)**:中大型=Codex 實作+Composer review(memory 已更新)。
- 跟進(不擋事):code review B1-B5 NON-BLOCKING(register-output 綁 dispatch output_path 硬化等,見 REVIEW-composer.md)。

## 鐵律(慢測試/執行)
- generate_features ~20分/次;slow 跑後 `./scripts/restore_golden_inventory.sh`;長測試後清 pytest 舊輪次(留 pytest-current)。
- HANDOFF/commit 寫「已驗/passed」須帶 VERIFY:<receipt-id> 或引用格式「檔載『…』(出處:檔名)」。委員會過程檔今後派工帶 --task-id+--output,產出後 register-output 即可 commit(不再累積)。
- pre-existing 失敗=test_ic_engine(非深稽)。派工執行端可能誤還原根 HANDOFF——commit 前重驗內容。
