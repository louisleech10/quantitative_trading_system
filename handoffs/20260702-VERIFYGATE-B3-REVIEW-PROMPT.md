# B3 Codex adversarial code review 指派

Composer 2.5 已實作 B3（TODO Task 3.1-3.4,enforcement 三層+health）。另 Claude（編排端）自改兩處小項一併受審（編排端不可自我認證）。目標=獵繞過面。

## 範圍（未 commit 工作樹）
- B3 新檔:`scripts/verify_pretooluse.sh`、`scripts/git_hooks/{pre-commit,commit-msg}`、`scripts/install_verify_hooks.sh`、`scripts/verify_hooks_health.sh`、`.github/workflows/verify_claim.yml`、`tests/governance/test_verify_gate_b3.py`
- B3 修改:`.claude/settings.json`(增一條 PreToolUse)、`scripts/agent_{pre,post}flight.sh`(health 接線)、`scripts/verification_claim_check.py`(diff,--stdin-operational 等)
- **Claude 自改**:`scripts/verify_task_provenance.py`——① STAMP_TASK_RE 加連字號(原 `[a-z0-9]+` 把 task:p0ff3-r2 靜默截成 p0ff3);② LEGACY_STAMP_ALLOWLIST 加 20260630-FF-P0FF3-RECONCILE 兩戳記(provenance 制度前真戳記,依據 07-01 forensics 三方裁定設計 reconcile 有效)。**特別盯:regex 放寬有無新繞過面;allowlist 增項是否正當、hash 是否真對應現檔**。
- 規格:`docs/VERIFY_GATE_TODO.md` Phase 3;實作端收尾 `handoffs/20260702-VERIFYGATE-B3-composer.md`。

## 必審攻擊面（每項 BLOCKING/NON-BLOCKING/PASS + 反例）
1. **3.1 hook 判定**:operational 新增行偵測會不會漏(Write 全檔 diff 邏輯/fenced/quote 邊界)?非 HANDOFF 檔真的零觸發?hook JSON parse 失敗是 fail-open 還是 fail-closed,與設計(V7誤報=0 才全量)一致?settings.json 併存既有 gate_check 無互相覆蓋?
2. **3.2 git hooks**:pre-commit --staged 能否用部分 stage/rename/binary 繞過?commit-msg 漏 body?install script 冪等+uninstall 乾淨?
3. **3.3 CI**:range 計算(force-push/first-push/PR)漏洞?依賴缺失真紅?無 || true/continue-on-error?
4. **3.4 health**:偵測面完整(hooksPath/檔存在/可執行/含 checker 調用/依賴)?可被空殼 hook 檔騙過嗎?
5. **測試牙齒**:b3 測試可證偽?mutation 探針真的注壞會紅?測試隔離(真實 audit/config/receipts 零觸碰)?
6. **回歸**:Claude 已親驗 67 passed+audit.log 前後行數不變+真實 repo hooksPath 未設;複核覆蓋是否足夠。

## 輸出
寫 `handoffs/20260702-VERIFYGATE-B3-REVIEW-CODEX.md`:每 finding 檔:行號+反例+修法,分 BLOCKING/NON-BLOCKING;結尾 `VERDICT: APPROVED` 或 `CHANGES_REQUIRED`;最後一行 STATUS: DONE。
