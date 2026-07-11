# 1a cut1 舊路徑 baseline 重生歸檔(2026-07-11,R4 版)

## A. 目錄內可驗主張(每條有本目錄產物支撐)
1. **雙 commit 重生件**:`baseline_old_regen_854d444.json`/`baseline_old_regen_c0b29ac.json`+各自 meta;file sha 與 `regen_receipts.json` 逐字吻合(codex R3 已獨立驗)。
2. **交叉相等**:兩件 normalized sha(規則見 receipts `normalized_sha_rule`)相同=`2f3617b9…`→兩 commit 舊碼對同輸入產出相同內容(豁免 generated_at)。
3. **override 已記錄**:兩 meta `request.config_override.ic_train_test_split=false`。
4. **重生腳本快照**:`freeze_baseline_used_for_regen.py`(sha 在 receipts)——含顯式 override+inputs 重用;**原 commit 之腳本無 override,直接執行 meta 內 command 不能重產**;正確重生程序=receipts `reproduction` 欄(把本快照複製入 worktree 再跑)。
5. **inputs 身分**:receipts `inputs` 欄記兩輸入檔 sha(主樹 tests/golden/ic_phase1_1a_cut1/inputs/,2026-06-27 產)。

## B. 外部指標(pointer,證據在所指位置,非本目錄)
- 原件滅失+越界重凍經過:`handoffs/ic1a_cut1_refreeze_quarantine/README.md`+`handoffs/IC1EB-B2-REVIEW-codex.md` FINDING#11。
- 「schema 預設自 d3b2dff 即 True/yaml 未設」考證:codex `handoffs/IC1EB-B5-REVIEW-R2-codex.md` F5c 節(git show 反證)。
- 「原凍結者必然套用未記錄 override」推論依據:854d444 當時 golden 測試綠(該 commit 訊息)+flag-off 測試=顯式 False 語意(git show 該 commit 測試檔)。此為**推論**,原始執行紀錄已不可得。
- Grok 首次重生(無 override)記錄:`handoffs/IC1EB-B5-IMPL-RESULT.md`。
- 現行 tests/golden/ic_phase1_1a_cut1/ 兩態重凍與測試綠:`handoffs/IC1EB-B5-REVIEW-R2-codex.md` F5b(codex 實跑 2 passed)。
- 新舊選型正式對照:`handoffs/IC1EB-GOLDEN-DIFF.md`。
