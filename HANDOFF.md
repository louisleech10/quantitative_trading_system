# Handoff
**Agent**: Claude | **Time**: 2026-07-10 | **Branch**: main

## ✅ 剛完成:Grok 4.5 資格認證(R1+R2)+執行端分工二調
- Grok 4.5 §8 T-A~T-D 資格認證完成,方法論/結果/receipts 全在 `docs/reviews/grok_4_5_evaluation.md`(唯一合併回 main 的產物;測試 worktree 已依使用者裁定清除)。
- **分工(2026-07-10 使用者指示,ORCH §1 已更新)**:中/大實作=Codex(gpt-5.6-sol high)/Grok 4.5 依額度動態;Composer 2.5 主打 review/adversarial;實作型 SPEC/TODO 初稿=Composer 起草試點(設計/研究型仍全員三版);簽核 quorum=Claude+Codex+Composer 不變;Grok 前 ~5 真實任務加密驗收+記 executor_scorecard。
- VERIFY: `grep model ~/.codex/config.toml` + `codex exec` header → `model: gpt-5.6-sol` / `reasoning effort: high`(2026-07-10 實跑)
- grok 派工語法:`timeout <s> grok -p "<prompt>" -m grok-4.5 --cwd <絕對路徑> --sandbox workspace --always-approve --output-format plain < /dev/null`(⚠️ --cwd 相對路徑會失敗;gate_check 視 grok 為 dispatch 通道)

## ★下一站:IC 1e+1b(FDR/HAC 顯著性正確化)B1-B5 開跑(使用者 2026-07-10 拍板;建議新 session 從此接手)
1. **Claude 預產 Golden baseline**(`handoffs/ic1eb_baseline/`,舊路徑 report+五 hash,SPEC §G 程序;不得由實作者自產,實作端唯讀消費)。
2. gate `--risk high` 附 `--spec docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md --todo docs/IC_PHASE1_1E1B_SIGNIF_TODO.md --adversarial handoffs/IC1EB-RECONCILE.md`。
   - VERIFY: `reconcile_stamps_check.sh handoffs/IC1EB-RECONCILE.md codex,composer` → PASS sha256:b77932d8(2026-07-10 重跑)
3. **B1 先派 Grok**(批次階梯,B1 乾淨過才放 B2-B5,依 TODO §B)→ Codex+Composer 雙審 → Claude 批批驗收(golden 五hash/mutation/防假綠 diff,不採信自報)→ 同批重派 ≤2 輪不過→斷路器換 Codex、Grok 降回 review。
4. 全批完成 → 三方數據正確性簽核(Claude+Codex+Composer,本輪全為非作者)。
- SPEC 凍結軌跡/核心設計(kernel=bar-level Spearman+NW,BH-FDR 先算 q 再進閘,SelectionScope,canonical significance.fdr.*)見 handoffs/IC1EB-* 與 git log 上一則 handoff;Golden=G-1 五hash+G-2 selection-diff+G-3 fail-closed;M-A~M-J mutation。
- 後續刀:③1c Net IC 量綱→④1d attribution→⑤1f 空圖+grouped schema(ROADMAP L42 已同步分工)。

## 鐵律(不變)
- 「已驗/passed」須帶 VERIFY receipt;審查派工 `--risk low --template "n/a:"`;實作派工 `--risk high` 附 spec/todo/adversarial;codex exec 必接 `< /dev/null`;委員產出 register-output。
- 執行端產物不可信;接回只讀 diff+測試+摘要;執行端不得 git checkout/stash tracked 檔(baseline 唯讀消費預產快照)。
- 未 commit 殘留:`.claude/settings.json`(使用者本機權限/模式調整,留使用者決定是否入版)。
