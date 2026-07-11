# 票 3 TODO R3 主委代跑 receipt(codex delegated 反例)
Task-id: p2debt-t3 | Chair: Claude(Opus 4.8) | Date: 2026-07-11

## 背景
Codex 對 R3 的複驗 verdict=BLOCK,**但原因是沙箱 shell 卡死 60s(DELEGATED-TO-ORCHESTRATOR),非發現 R3 缺陷**(見 handoffs/P2DEBT-T3-TODO-REVERIFY-R3-codex.md 末行「could not independently execute」)。依票 4 繞法:編排端代跑其反例並提供 receipt。

## 主委代跑(本機無 60s 限制,2026-07-11)
針對 Codex R2 兩個原 finding 各造反例:

### Finding 1:run_step 讀 unexported parent vars → CLOSED
- 反例:parent 設 `SECRET=parent_only`(未 export),`run_step leak bash -c 'echo $SECRET'`。
- 實跑輸出:`child sees SECRET=[]`(空)+ `STEP_RC[leak]=0`。
- 判定:R3 每步 `bash -c` self-contained,child 讀不到 parent 未 export 變數;修正成立。

### Finding 2:zero-match grep -c 多行非整數 → CLOSED
- 反例 2a(rc=1→0):無 "error TS" 的 log 跑 R3 tsc_zero block → `TSC_ERROR_COUNT=0` + `STEP_RC[tsc_zero]=0`。
- 反例 2b(多檔計數):
  - 舊 `grep -c "error TS" f1 f2`(壞)→ 多行 `f1:2` `f2:1`(非整數,`test -eq` 會炸)。
  - R3 `rg -c ... | awk -F: '{s+=$NF} END{print s}'`(對)→ `3`(單一整數)。
- 判定:R3 rg -c + rc 分支 + awk 合計,消除 multi-line 非整數;修正成立。

## R2→R3 diff 範圍(主委確認)
R3 僅改 acceptance shell blocks(§Final + run_step),Task 1.1-1.5 實作清單零改;template_check todo PASS(主委實跑)。

## 結論
Codex R2 兩 finding 經主委代跑反例**均 CLOSED**;R3 卡死純環境問題非設計缺陷。請 Codex 讀本 receipt + R2→R3 diff(diff 命令不卡)後補 RECONCILE-STAMP。
