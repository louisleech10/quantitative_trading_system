# Handoff
**Agent**: Claude | **Time**: 2026-07-10 | **Branch**: main

## ✅ 剛完成:1e+1b Golden baseline 預產+三家四輪 adversarial 複驗全 PASS
- 產物:`handoffs/ic1eb_baseline/`(v4;13 report+1 labels-raise receipt+inputs/19 檔防偽 sha+manifest;gitignored 同 1a 先例,B5 skip-if-absent)。程序=`scripts/capture_ic1eb_baseline.py`(premat sha500 inputs/persist patch no-op/content 指紋 29GB 前後零 diff)。
- 審計鏈:設計 `IC1EB-BASELINE-DESIGN.md` → R1 三家全 BLOCK → `IC1EB-BASELINE-RECONCILE.md`(F1-F17+R2 節) → v2/v3/v4 迭代 → Grok/Composer PASS+Codex R4 全 CLOSED PASS(`IC1EB-BASELINE-REVERIFY*`)。
- 重大教訓(規則提案 `handoffs/RULE-PROPOSAL-ORCH-SELF-ARTIFACT.md` 待委員詰問+SCAR 登記):編排端自產物先審後跑;逃脫點=gate 不攔編排端 Bash+SPEC 指派單人無審查義務。
- 使用者新規:①一切輸出附白話解釋+專有名詞「中文(English/縮寫)」對照(記憶已更新)②Grok 入委員會審查腿+I/O 觀察(ORCH §1 三調)。

## ★下一站:B1 派 Grok(Task 1.1-1.3 統計 kernel)
1. `bash scripts/agent_preflight.sh` → gate `--risk high --spec docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md --todo docs/IC_PHASE1_1E1B_SIGNIF_TODO.md --adversarial handoffs/IC1EB-RECONCILE.md`(stamps PASS sha256:b77932d8 已重驗)。
2. 派工 prompt 備妥:`handoffs/IC1EB-B1-IMPL-PROMPT.md`;grok 語法見上一則 handoff(--cwd 絕對路徑)。
3. B1 乾淨過才放 B2-B5;同批 ≤2 輪不過→斷路器換 Codex;Codex+Composer 雙審;Claude 批批驗收(golden hash/mutation/防假綠 diff)。
4. 並行:規則提案送三家詰問;Composer 收 baseline v2→v4 delta 通知。

## 鐵律(不變)
- 審查派工 `--risk low --template "n/a:"`;實作派工 `--risk high` 附 spec/todo/adversarial;codex exec 必接 `< /dev/null`;委員產出 register-output;派工進度每 10 分鐘回報。
- 執行端產物不可信;接回讀 diff+測試+摘要;`handoffs/ic1eb_baseline/` 唯讀消費,禁重產(manifest 有 content 指紋+inputs sha 防偽)。
- 背景長任務掛雙層監看(log 關鍵字+PID 存活)。
- 未 commit 殘留:`.claude/settings.json`(使用者本機,留使用者)。
