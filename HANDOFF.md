# Handoff
**Agent**: Claude | **Time**: 2026-07-11 | **Branch**: main

## ✅ 1e+1b epic 閉合:B1-B5 入版+三方數據正確性簽核全 PASS
- 簽核:Claude+Composer+Codex(R4)全 DATA-CORRECT PASS SIGNOFF:IC1EB-SIGNOFF-claude.md:IC1EB-SIGNOFF-composer.md:IC1EB-SIGNOFF-R4-codex.md;簽核輪 Codex 三輪抓 FDR method 契約縫→signfix×2(Grok)+signfix3(Composer 斷路器換手)修畢。
- 最終驗收:`venv/bin/python -m pytest tests/momentum/ -q`(含 tests/momentum/Analysis/test_ic_1eb_b5_golden.py)=1067 passed+3 skipped VERIFY:ic1eb-epic-final-gate。
- 成果:假陽率 0.43→0.06(M-A);xsec p 誠實化;fdr toggle 全棧真接通;G-1 13 顆五hash 不變;G-2 diff=handoffs/IC1EB-GOLDEN-DIFF.md。
- 治理:規則四條使用者採納 2026-07-11(handoffs/RULE-PROPOSAL-RECONCILE.md)+SCAR 三連環登記(docs/SCAR_LEDGER.md 末列);RULEIMPL 初稿 grok R3 判 PASS SIGNOFF:RULEIMPL-REVIEW-R3-grok.md,codex 補審待排。

## ★下一站
1. RULEIMPL(park 於 R5,2026-07-11):定稿=handoffs/RULEIMPL-SPEC-DRAFT-R5.md;審查鏈=composer 起草×5/grok R5 判 PASS SIGNOFF:RULEIMPL-REVIEW-R5-grok.md/codex R5 殘 4 條(handoffs/RULEIMPL-REVIEW-R5-codex.md)——性質=正式化時綁定項(cutoff full-SHA 開票填/base fallback 演算法字面修/digest exclusion set 枚舉/sidecar 自參照排除)。下一步:正式化 SPEC/TODO(gate artifact+範本)時逐項落值→codex 終驗→派實作。
2. ROADMAP ③ 1c Net IC 量綱(下一刀)。
3. P2 債:governance 既有 9 紅(b4×3+b5×5+r7,先於本 session,歸屬驗證=HANDOFF 前版+git log 3edfa6c)/legacy 測試寫 data_cache tmp redirect/tsc 既存 10 errors/codex 沙箱間歇卡死觀察。
4. Grok 記分素材(加密驗收期,裁決留使用者):B1-B5 交付均一輪修復閉合;審查腿多次高品質 findings;停手紀律好(BLOCKED-1A);弱項=橫切面不變量/測試嚴謹捷徑/一次越權重凍 1a(記檔 handoffs/ic1a_cut1_refreeze_quarantine)。

## 鐵律(不變)+本 epic 新教訓
- 審查用 --risk low --template "n/a:";實作用 --risk high 附三件;codex exec 必接 < /dev/null;register-output;10 分鐘回報;執行端產物不可信;baseline 唯讀。
- 新:背景長任務雙層監看(log+PID);codex 命令一次一條/venv 顯式/60s 棄;禁 -m "test" 探測 commit;mutation 紅燈行 SUPERSEDED 註記;RESULT 檔 VERIFY 零豁免;golden 產物須入版或外部雜湊否則滅失無解。
- 未 commit 殘留:.claude/settings.json(使用者本機)。
