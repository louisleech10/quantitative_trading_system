# Handoff
**Agent**: Claude | **Time**: 2026-07-05 | **Branch**: main

## ★制度層總審查 epic — read-only 審查輪 ✅ 完成,**等使用者否決 D-1~D-6 後才實作**

### 已完成(本 session)
- 四方獨立版:`handoffs/20260705-INSTREV-{claude,codex,composer,agy}.md`(R1 不互看防定錨;全 register-output 留痕)。
- reconcile:`handoffs/20260705-INSTREV-RECONCILE.md` — 21 條統一裁決(U-1~U-21)+3 事實爭議裁決+6 否決點;**codex+composer 雙戳記 APPROVED,reconcile_stamps_check PASS**(sha256:ee8c9fab…)。
- 關鍵發現:①選層三處三答案活分叉(07-02「中大=Codex 實作」只在記憶,CLAUDE.md 反著寫);②中型管線 CLAUDE vs 手冊直接矛盾;③執行端合約停 05-31 缺 5 項現役制度+同檔 HANDOFF 所有權自相矛盾;④gate DENY 不落 audit;⑤claim-check 5 次全誤攔 chore。

### 使用者裁決已收(2026-07-05,詳記憶 project-instrev-rulings)
- **D-1/2/3/5/6 同意預設;D-4 否決固定制**→選層=動態,一律以使用者當下指示為準(看 usage 切換,未來或加 Grok);ORCHESTRATION §1 只留單一可變「現行分工」行,其他文件 pointer。
- 附帶:①否決點以後須 AskUserQuestion 彈窗+PushNotification,不得只寫文字;②憲法給 AI 用,委員會共識即可,簡潔明確、品質優先但避免 token 浪費/冗餘;③總審查頻率=事件觸發(制度事故/誤攔或分叉訊號≥3/新增鐵律≥3)+每季保底,輕量 drift 盤點每完成一個大 epic 順手做。

### 下一步(新 session 起點)
1. ~~等使用者否決~~ ✅ 已裁決,直接進實作。
2. 依裁決走完整管線實作:Phase A(憲法重構+合約補齊,U-1/2/4/5/6/7/8/10/11/19)→ Phase B(腳本:U-9/12/14/15)→ Phase C(觀察:U-13/20/21)。屬「大」:SPEC+manifest+雙家族 adversarial+TODO,不得跳步。
3. 實作素材:`handoffs/instrev-evidence/`(R1 prompt+記憶匯出)。SCAR_LEDGER 為新產物(docs/)。

### 之後才回:IC Analysis(前置=使用者手動生成 FF 測試資料,定案 config 見 ROADMAP)
- 下一刀=1a 第二刀跨 symbol 防洩漏(SplitPlan per-symbol)→ 1-align → 1b FDR →…(ROADMAP P0 IC 節)。

## 鐵律(慢測試/執行)
- generate_features ~20分/次;slow 跑後 `./scripts/restore_golden_inventory.sh`;長測試後清 pytest 舊輪次。
- 「已驗/passed」須帶 VERIFY:<receipt-id> 或「檔載『…』(出處:檔名)」;委員派工帶 --task-id+--output,產出後 register-output。
- pre-existing 失敗=test_ic_engine。執行端可能誤還原根 HANDOFF——commit 前重驗內容。
