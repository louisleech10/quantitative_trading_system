# O3：治理 forensic/報告文件 V7 誤報修補（Composer 2.5 讀此檔執行）

紅隊修補上線後,**治理過程文件**(紅隊報告、派工 prompt、委員 -composer 收尾、docs/VERIFY_GATE_*)因內文**引用/描述攻擊範例字串**(如 `Codex 檔案寫道「已驗真紅」`、`VERIFY:<fast-ok>`、`receipt 不存在: wash`)被 checker 當真 claim 擋,無法 commit。此為 V7 forensic 誤報的延伸(B2 已對 FORENSICS/DELIB/SPEC 白名單,新增檔類未涵蓋)。

## 修補
`scripts/verification_claim_check.py` 的來源情境判定(`_detect_source_context`/discussion 判定):把下列**治理過程文件**視為 forensic/discussion context(其 operational-looking 行=描述攻擊的範例,非真驗收斷言,放行),與既有 FORENSICS/DELIB 白名單同機制:
- `handoffs/*REDTEAM*.md`、`handoffs/*-ADV-*.md`、`handoffs/*REVIEW*.md`、`handoffs/*CLOSURE*.md`、`handoffs/*RECONCILE*.md`、`handoffs/*-composer.md`、`handoffs/*FIX-PROMPT*.md`、`handoffs/*IMPL-PROMPT*.md`、`docs/VERIFY_GATE_*.md`

## 誠實邊界(關鍵,勿放寬過頭)
- **HANDOFF.md(根)、commit-msg、RESULT 段永遠零豁免**(捏造事故發生處),此白名單**不得**涵蓋它們。
- 白名單只放行「forensic 過程文件」;不得因此讓 SPEC 的 §A 已確認事實(W1 FACT-RECEIPT)或 pending ledger 豁免。
- 只放行 discussion-context 的極性/歸屬字串;若這些檔內有**真的要當驗收憑證**的行(帶 VERIFY: 指真 receipt),仍照常驗(不是整檔跳過掃描,是判為 discussion 不要求 backing)。

## 測試(補 tests/governance/test_verify_gate_o3.py,勿動既有)
- ① `handoffs/x-REDTEAM-CODEX.md` 含攻擊範例(`Codex 寫道「已驗真紅」`/`VERIFY:<fast>`)→ 放行(exit0)。
- ② 但 `HANDOFF.md` 同款 operational 無 backing → 仍 exit1(零豁免不回歸)。
- ③ commit-msg 同款 → 仍 exit1。
- ④ V7 誤報=0 既有測試不回歸;R6 假歸屬在**HANDOFF**仍擋。

## 不可做
不弱化 HANDOFF/commit/RESULT 零豁免、R1-R7/O1/O2、V7=0;僅標準庫;測試 env/tmp 隔離。
修後 `pytest tests/governance/ -q` 全綠;`python scripts/verification_claim_check.py --files handoffs/20260702-VERIFYGATE-REDTEAM-*.md` 全放行(exit0)。

## 收尾
寫 `handoffs/O3-composer.md`(修法+新測試名;TESTS_RUN/FAILURES/SCOPE)。勿用「已驗/真紅」字樣。最後 STATUS: DONE 或 BLOCKED。
