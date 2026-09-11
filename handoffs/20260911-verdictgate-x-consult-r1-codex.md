brief-kind: consult; task-id: 20260911-VERDICTGATE-X-CONSULT-R1; findings-round: R1; family: CODEX
## Verdict：需修補後派工；G1方向可採，G3需換 hook 邊界，G2/G4需補強
F1–F5：同意。證據：gate.sh:784-805 僅 impl-b；review_quorum_check.sh:26-55 只數 dispatch 不讀 verdict；SPLITUNIFY audit/逐批表確認每界有不可進；全 handoff review glob 的 rg -l blank Verdict=111 檔、verdict-like=681 檔，F5 比主委所報 14 更嚴重。
F6–F10：同意。證據：rg verdict .claude/gate/audit.log→0；completeness_check.sh:1556-1579 只驗 ID/body；/tmp/att_b1.log 出現中文附錄找不到；git show 539431fc 記錄延後消失及 tier_min_test_events 靜默變 1；B7 才首次原提出方 closure。
1) GAP-3D2 X R1（2026-09-03）以 CODEX-R1-P1-01..05/P2-06/07 判不可進後仍有後續 B3 review；EVTLABEL B3 R1（2026-09-10）以 GROK-R1-P1-01..04/P2-01/P3-01 判不可進 3.4–3.7，仍出現 B4 R1。均為「不可進 yet crossed」實例。
2) printf Ticket-Batch + Governance-Scope | git interpret-trailers --parse 實跑輸出兩個 trailer；同一 final trailer block 可共存，空行則不算 trailer。現行 G-7 只取 Governance-Scope，故 parser 相容；但 G3 應明定 Ticket-Batch 的獨立取值與重複鍵規則。
3) G2 兩個 local trigger 仍漏第三邊界：remote push acceptance；本 repo 無 workflow guard。另有 git push --no-verify、GOVERNANCE_SKIP_PREPUSH=1，而 current hooksPath 只是 local config；「無 commit 的 direct push」不是新內容路徑，但既有 commit／hookless worktree 仍可送出。
4) G4 首 20 字只能作顯示／弱對證，不能證明處置語意；最強可機械化條件是 finding ID + canonical claim digest + 決議列 exact quote，語意是否真正修掉仍須人工 closure，不能宣稱全自動。
5) G3 --impl-self 只有 chair 主動呼叫才生效；cx_run 不做 git commit，只做 completeness/selfcheck 與 audit emit。commit message trailer 應在 commit-msg 解析，pre-commit 只能驗 staged batch token；--no-verify 需另由 remote/CI 或不可繞過的 server boundary 補第二層。
6) 批次順序：B0 G1（schema、audit、per-finding state）→B1 G4+G5（ID/claim mapping、結構化 deferred row；不要只靠 regex）→B2 G6（原提出方逐 finding closure）→B3 G3（commit-msg/pre-commit/pre-push 邊界）→B4 G2（dispatch+commit consumer）→B5 六案整合及 bypass/negative tests；B1–B3 可並行開發但均依賴 B0。
7) 目前沒有整案「完全不可能」；唯一不可全機械化的是 G4 的語意真實性，應列為明示人工 closure 而非 95% 殘留理由。
## CODEX-R1-P0-01
**斷言**：G3 將 commit-message trailer 驗證放在 pre-commit 按字面不可行；cx_run 也沒有委員執行端 commit 可被該檢查相容性驗證。 **碼證**：pre-commit 無 message 參數；commit-msg:18-29 才取得 msg 且 g7 以 || true warn-only；cx_run.sh:154-161、513-524 僅 selfcheck/audit emit，沒有 git commit。 **來源摘要**：scripts/git_hooks/pre-commit#eae29414b4f9；scripts/git_hooks/commit-msg#828326ffb754；scripts/cx_run.sh#d7aa1dc7bf09。正文：改為 commit-msg 解析 Ticket-Batch，pre-commit 驗 staged token；否則 G3 無法 fail-closed。
## CODEX-R1-P1-02
**斷言**：G1/G6 的 VERDICT: closed 是整份輸出級狀態，未綁定逐 finding ID、closure 證據與原提出方重跑結果；可能以一個 closed 釋放多個 blocked。 **碼證**：主委版 G1 僅列 closed/blocked:<ID,ID>，G6 只以 closed 解除 G2；現 audit 無 verdict 欄。 **來源摘要**：handoffs/20260911-VERDICTGATE-RECON-claude.md#126e1684e574；scripts/review_quorum_check.sh#a1c6ced819a。正文：改成每一 finding 的 closed:<ID>、proposer、closure round、evidence digest 四元組，G2 只消費逐項 closed。
## CODEX-R1-P1-03
**斷言**：G2/G3 只加 local dispatch/pre-commit 不能涵蓋 push acceptance；現行 pre-push 明示 --no-verify 與環境逃生口，且無 remote/CI fail-closed 兜底。 **碼證**：pre-push:7-18、46-53；git config --get core.hooksPath→scripts/git_hooks；.github 無 workflow 檔。 **來源摘要**：scripts/git_hooks/pre-push#5c9ec7a78e59；handoffs/20260911-VERDICTGATE-RECON-claude.md#126e1684e574。正文：在 G2 驗收中加入 commit-msg、pre-push、remote/CI 三邊界；若只允許 local 威脅模型，必須把「蓄意 bypass 不防」標為非 fail-closed。
## CODEX-R1-P2-04
**斷言**：G4 的首 20 字引用會碰撞、可引用附錄複製文字或不相關決議，不能單獨證明 finding 已處置。 **碼證**：主委版 G4:46-49 的機械條件只有 ID 所在列與首 20 字 quote；completeness single:1556-1579 仍未驗決議對應。 **來源摘要**：handoffs/20260911-VERDICTGATE-RECON-claude.md#126e1684e574；scripts/completeness_check.sh#c76692e041da。正文：quote 僅保留為人讀索引，機檢再綁 canonical claim digest；語意 closure 維持原提出方人工驗證。
ASSUMPTIONS_VERIFIED: GAP3D2/EVTLABEL review 檔、F1-F10 腳本證據、trailer 共存 parser 均已讀／實跑；未改 code、SPEC、TODO 或 data_cache。
TESTS_RUN: rg 全 review glob blank Verdict=111、verdict-like=681；rg verdict .claude/gate/audit.log→0；git interpret-trailers --parse 同段雙 trailer→各輸出一行；無 full governance/momentum Analysis。
FAILURES_SEEN: none；未宣稱已修 production。
SCOPE_CHANGES: 僅新增本交接檔；未越界，保留既有 dirty worktree。
NUMERIC_OR_SCHEMA_IMPACT: 未改輸出；提案需新增 per-finding verdict/closure 與 Ticket-Batch 欄位，屬後續 schema 變更。
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-x-consult-r1-codex.md
STATUS: DONE
