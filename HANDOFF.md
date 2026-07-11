# Handoff
**Agent**: Claude | **Time**: 2026-07-11 | **Branch**: main

## ✅ 1e+1b epic 閉合:B1-B5 入版+三方數據正確性簽核全 PASS
- 簽核:Claude+Composer+Codex(R4)全 DATA-CORRECT PASS SIGNOFF:IC1EB-SIGNOFF-claude.md:IC1EB-SIGNOFF-composer.md:IC1EB-SIGNOFF-R4-codex.md;簽核輪 Codex 三輪抓 FDR method 契約縫→signfix×2(Grok)+signfix3(Composer 斷路器換手)修畢。
- 最終驗收:`venv/bin/python -m pytest tests/momentum/ -q`(含 tests/momentum/Analysis/test_ic_1eb_b5_golden.py)=1067 passed+3 skipped VERIFY:ic1eb-epic-final-gate。
- 成果:假陽率 0.43→0.06(M-A);xsec p 誠實化;fdr toggle 全棧真接通;G-1 13 顆五hash 不變;G-2 diff=handoffs/IC1EB-GOLDEN-DIFF.md。
- 治理:規則四條使用者採納 2026-07-11(handoffs/RULE-PROPOSAL-RECONCILE.md)+SCAR 三連環登記(docs/SCAR_LEDGER.md 末列);RULEIMPL 初稿 grok R3 判 PASS SIGNOFF:RULEIMPL-REVIEW-R3-grok.md,codex 補審待排。

## ★★ Session 排程(使用者 2026-07-11 裁定:P2 債與 1c 拆開,先債後刀)

### 下一個 session = P2 債四項(獨立票,逐項閉合)
1. governance 9 紅:tests/governance b4×3+b5×5+redteam r7——7/5 制度強化(template_check 3edfa6c 等)後測試 fixture 過期斷言舊行為;修法方向=遷移 fixture 至現行檢查器語意,禁放鬆檢查器換綠;歸屬驗證=git log 3edfa6c+worktree 對照。
2. legacy 測試寫 data_cache:1a cut1 等舊測試走真 service 路徑覆寫 data_cache 衍生檔;修法方向=測試輸出 tmp redirect(參考 1e+1b capture 的 persist patch 模式);出處=handoffs/IC1EB-B3-REVIEW-R3-codex.md 歸屬裁定。
3. tsc 既存 10 errors(frontend npx tsc --noEmit,全在 feature-factory 測試檔;非 1e+1b 引入〔REF:handoffs/IC1EB-B4-REVIEW-codex.md〕);本票目標=修掉這 10 個既存型別錯誤。
4. codex 沙箱間歇卡死(觀察債):CLI 0.144.1 重運算命令偶發停滯;本票蒐證(復現條件/頻率)後決定回報 OpenAI 或固化繞法入 ORCH。
- 分工=四調現行行(ORCH §1);Grok 記分照跑。
- 併行可選:RULEIMPL 正式化(見下)可併本 session 或另排,由使用者屆時定。

### 之後的 session = ROADMAP ③ 1c Net IC 量綱(大,完整管線)
- 病灶:momentum/Analysis/net_ic_analyzer.py:34 把交易成本(報酬率量綱)直接從 IC(相關係數,無量綱)裡減——量綱不合,淨 IC 數字無數學意義(ROADMAP L42 ③)。
- 前置:P2 債 session 完成(乾淨基線);SPEC/TODO 走完整管線後才動工。
- **facts-asked 預登記(使用者 2026-07-11 預留,SPEC 偵察時必問使用者)**:①交易成本來源=使用者輸入/固定預設/按 symbol 費率表?②要不要「不計成本直接算 Net IC(=原始 IC)」模式與對照欄?③成本率的 UI 入口與預設值。使用者明示「到 1c 時再討論」,禁提前替使用者假設。

### RULEIMPL(park 於 R5,2026-07-11)
定稿=handoffs/RULEIMPL-SPEC-DRAFT-R5.md;grok R5 判 PASS SIGNOFF:RULEIMPL-REVIEW-R5-grok.md;codex R5 殘 4 條(handoffs/RULEIMPL-REVIEW-R5-codex.md)=正式化時綁定項(cutoff full-SHA 開票填/base fallback 字面/digest exclusion set/sidecar 自參照排除)。正式化(gate artifact+範本)時逐項落值→codex 終驗→再派工。

### Grok 記分素材(加密驗收期,裁決留使用者)
B1-B5 交付均一輪修復閉合;審查腿多次高品質 findings;停手紀律好(BLOCKED-1A);弱項=橫切面不變量/測試嚴謹捷徑/一次越權重凍 1a(記檔 handoffs/ic1a_cut1_refreeze_quarantine)。

## 鐵律(不變)+本 epic 新教訓
- 審查用 --risk low --template "n/a:";實作用 --risk high 附三件;codex exec 必接 < /dev/null;register-output;10 分鐘回報;執行端產物不可信;baseline 唯讀。
- 新:背景長任務雙層監看(log+PID);codex 命令一次一條/venv 顯式/60s 棄;禁 -m "test" 探測 commit;mutation 紅燈行 SUPERSEDED 註記;RESULT 檔 VERIFY 零豁免;golden 產物須入版或外部雜湊否則滅失無解。
- 未 commit 殘留:.claude/settings.json(使用者本機)。
