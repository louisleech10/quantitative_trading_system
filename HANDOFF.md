# Handoff
**Agent**: Claude | **Time**: 2026-07-02 | **Branch**: main

## ★驗收防偽閘 verify-gate(P0,先於 FF 收尾;起因=P0-FF-3 驗收捏造事故 A 類)
- 文件鏈/議事/SPEC v2.1/TODO 齊備:`docs/VERIFY_GATE_{BRIEF,SPEC,TODO}.md`+`handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md`(雙戳記)。
- **B1 ✅**(`d3870c4` run_with_receipt+審計)。**B2 ✅**(`a1d3638` claim checker+ledger,V7 誤報=0→B3 PreToolUse 可全量)。
- **B4+B5 ✅(本次 commit)**:B4=mutation接receipt/W3 adversarial provenance/W2 stamp provenance/audit_chain;B5=RESULT硬欄位枚舉/#6 fingerprint衝突/W1 FACT-RECEIPT。
  Composer 實作→Codex adversarial **6 BLOCKING**(gate非ADV路徑繞過/回填日期grandfather/RESULT枚舉不入checker/fingerprint含極性詞自廢/W1漏指令輸出/合成receipt殘留)→Composer 修→Codex 原提出方重跑反例**全 CLOSED**→Claude 補 gate.sh `GATE_DIR_OVERRIDE` 測試隔離+清 audit.log 合成條目→Codex round2 APPROVED。governance **55 passed 且 audit.log 零汙染**。
- **B3(本次 commit)**:verify_pretooluse.sh+settings.json PreToolUse/git hooks(staged 讀 index blob)/CI workflow/health。Codex review 4 BLOCKING(partial-stage/code-only假紅/交付狀態自阻斷/binary crash)→Composer 修→Codex 閉合檔寫道「FINAL VERDICT: APPROVED — B3-1/B3-2/B3-3/B3-4 CLOSED」(出處:20260702-VERIFYGATE-B3-REVIEW-CODEX.md closure 節)。governance 75 tests 綠 VERIFY:20260701T235954Z-governance-b3-final。PreToolUse hook 已生效(本檔本段初稿即被其擋過,補 receipt 後才寫入)。
- epic B1-B5 全落地。殘餘=誠實邊界(careless-proof+tamper-evident,非防惡意;audit_chain 人工抽查)。git hooks 安裝:`bash scripts/install_verify_hooks.sh`。

## ★FF 深稽 P0-FF-3(等 B3 完+探針修好再正式驗收)
- ⚠️ **舊聲稱「align mutation 真紅(babu8o07p)」=捏造**(smoke 冒充慢測;`handoffs/20260701-FF-FORENSICS-RECONCILE.md`)。WIP 程式碼在 `9f9839d`(設計 reconcile 雙戳記 sha256:5da75188 有效)。
- **首次真跑(bgr3kn4p6,2:25:45)**:center/winsor/lag 3 探針真綠✅;**align×2 FAILED=探針無牙齒**(traceback b8uou6xj6:+1 對稱偏置套 full+trunc 兩跑在比較區抵消→`DID NOT RAISE`)。c3 主 MR+perturbation 2 passed(bwx3t2jqq)=正向不變量綠,不證 align 牙齒。
- **修向(委員共識)**:不對稱注入(只 patch 單側)或 oracle 直接斷言指定 coarse 欄在已知 12h 邊界 index 的值差/source-index 差,不靠大抽樣。**修探針走 Composer 實作+Codex review,非 solo**。
- **收尾順序**:① 修 align 探針牙齒 → ② receipt 版 mutation_probe_check 全 5 探針真紅真綠(4h timeout;2026-07-02 已白跑攔截:探針沒修前跑=已知紅) → ③ B2 回歸 `test_ff_fullchain_truncation_mr -m requires_kline`(序列防OOM) → ④ Codex review diff → 收 WIP commit。**驗收聲稱一律附 receipt+過 claim checker**。
- 剩餘:P1-FF-5/6/7(`handoffs/20260627-FF-AUDIT-RECONCILE.md`);FF preset 盤點另 epic。

## 鐵律(慢測試/執行)
- generate_features ~20分/次;內層 `timeout 14400` 一次跑完;跑後 `git checkout -- tests/golden/l65/test_inventory.txt`+tier2 還原;**長測試後清 pytest 舊輪次**(/var/folders/.../pytest-of-louis;2026-07-02 堆 33GB 事故,清時留 pytest-current)。
- 中大一律 Composer 實作+Codex review(feedback_executor_override);資料正確性/測試設計走三方委員會。pre-existing 失敗=test_ic_engine(非深稽)。
