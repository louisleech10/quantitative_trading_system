# GAP-3 TODO 對抗審 R8 — codex

TASK_ID: 20260820-GAP3-X-REVIEW-R8
SCOPE: `docs/GAP3_EVENT_TODO.md` v0.2 對 `docs/GAP3_EVENT_SPEC.md` FROZEN；只產 review，不改碼／SPEC／TODO。

RECONCILE-STAMP: codex APPROVED 2026-08-20 sha256:9887ae3582171d0a547ef5fc1a8789833a8667045c36f600963649a0656bc03b task:20260820-GAP3-X-REVIEW-R8

## Verdict

可凍結：本輪沒有 BLOCKING／MAJOR／MINOR finding；TODO v0.2 可進 TODO FROZEN＋三家戳記流程。

## R7 closure matrix

| 原 finding | 結果 | 本輪碼證摘要 |
|---|---|---|
| CODEX-R7-P1-01 | CLOSED | W1 明列操作依據／SPEC 語意權威／契約 SoT；B1.0、B2.4 兩處明定為一次性 genesis，建檔後契約檔優先。 |
| CODEX-R7-P1-02 | CLOSED | §0-6 已列 B5.1 factory 與 B5.3 收尾文件例外，並與 B5.1/B5.3 修改清單一致。 |
| CODEX-R7-P1-03 | CLOSED | B1.4 oracle 參數化 `statistic_kind`；B2.3 與 B2 Gate 明列 conditional-IC permutation、固定 seed、N_perm=1000、經驗分位。 |
| CODEX-R7-P1-04 | CLOSED | B1.0 驗證與 B1 Gate 明列兩個 digest 篡改 negative fixture；§G-4 仍要求 fail-closed。 |
| CODEX-R7-P1-05 | CLOSED | B1.6 輸出與函式簽名均為三元 tuple，含 `failures{event_id, reason}`；驗證含記帳守恆。 |
| CODEX-R7-P1-06 | CLOSED | `parse_condition` 接收 typed `expression_role`；同一 future 欄案例分別驗 selection 放行與 feature 拒絕。 |
| CODEX-R7-P1-07 | CLOSED | 五算子已定閉區間、含當前根、嚴格變號、d=0 不計、NaN/零值及 `cross_count` 無事件為 0；每算子要求 exact expected case。 |
| CODEX-R7-P1-08 | CLOSED | `to_return_series` 接收 `label_definition` 與 `AlignmentReceipts`；entry×exit、D1-6、label_end close 均列入 exact 驗證。 |
| CODEX-R7-P2-09 | CLOSED | scenario=C primary 已恢復完整 `ASSERT ... WHEN ... THEN rc=0`；該 ASSERT 是專案既定驗收 DSL，不是散文省略號。 |
| CODEX-R7-P2-10 | CLOSED | B5 Gate 有 `npx vitest run gap3`、`gap3_*.test.{ts,tsx}` 命名規約、≥3 類測試及 `docs/GAP3_UAT_CHECKLIST.md`。 |
| CODEX-R7-P2-11 | CLOSED | B5.1 以 T-3 完成 workload 為前置，並要求 ≥10000 事件 receipt 含 wall clock/RSS；效能門檻保留至偵察後，不捏造。 |

## Full-file sweep

- 11 條原始 CODEX RECHECK 命令均已重跑；每條命令 `RECHECK_RC=0`，且 stdout 命中對應寫回段落。
- `diff <(sed -n '370,382p' docs/GAP3_EVENT_SPEC.md) <(awk '/^- \\*\\*mutation 條件\\*\\*/,/^  - M12/' docs/GAP3_EVENT_TODO.md)`：空輸出，`M_DIFF_RC=0`。
- `bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md`：`DOC_FORMAT_RC=0`。
- TODO 20 個 Task、M1–M12 12 條；SPEC/TODO normalized Task ID 差異為空，`TASK_ID_DIFF_RC=0`。
- v0.1→v0.2 diff 僅 `docs/GAP3_EVENT_TODO.md` 的 47 insertions／31 deletions；改動均對應 W1–W12/W14 裁決。W7 的 d=0 與 `cross_count=0` 定義經獨立語義核對，未見矛盾。
- `rg -n '^ASSERT <命令>|機檢規則一句話' docs/MULTI_AGENT_ORCHESTRATION.md` 命中既定 ASSERT DSL（169、171）。

## Sentinel

## CODEX-R8-P3-00

**斷言**: 本輪逐項核對後無 finding。

**碼證**: R7 CODEX-R7-P1-01..08、P2-09..11 原 RECHECK 全數命中 v0.2 寫回且各 `RECHECK_RC=0`；M1–M12 diff 空輸出且 `M_DIFF_RC=0`；`doc_format_precheck` `DOC_FORMAT_RC=0`；20 Task ID 差異為空且 W1/W7/W10 另行語義核對無矛盾。

**來源摘要**: docs/GAP3_EVENT_TODO.md#b7bbe799d905; docs/GAP3_EVENT_SPEC.md#544c2922ef2e; handoffs/reconcile/20260820-gap3-x-review-r7/synth.md#651ae9db5d00

本輪未新增 finding；R7 的 11 條 CODEX finding 均 CLOSED。W1 的 genesis 例外和優先序宣告已把一次性建檔規格與後續契約 SoT 分開；W10 的記錄型驗收不宣稱效能 PASS，並以 T-3 前置避免私定門檻。

ASSUMPTIONS_VERIFIED: brief 的三項 fact-verified claim 已重驗；v0.2 寫回段落、W1/W7/W10、ASSERT DSL 與 Task/Mutation 對照均有命令證據。
TESTS_RUN: 11 條 R7 RECHECK；`diff` M1–M12（空輸出，rc=0）；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md`（rc=0）；Task ID normalized diff（空輸出，rc=0）。
FAILURES_SEEN: none。
SCOPE_CHANGES: 只新增本 review 與 task handoff；未改 SPEC、TODO、程式、測試或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: none；本檔只記錄 review 結論，未改任何產品數值、schema 或輸出。
HANDOFF_OUTPUT: `handoffs/20260820-gap3-x-review-r8-codex.md`; `handoffs/20260820-20260820-GAP3-X-REVIEW-R8.md`
STATUS: DONE
