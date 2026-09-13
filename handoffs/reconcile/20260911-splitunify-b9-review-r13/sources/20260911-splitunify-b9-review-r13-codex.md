# SPLITUNIFY b9 review-r13 — codex
scope: current TODO §C-9／B9A–B9F + commit 87d38dd9 listed diff；不重審 SPEC 歷史段。

## CODEX-R13-P1-01
**斷言**: C5-20 把 `feature_timeframe` assignments coverage 綁到 M-SU-D2-20，但 M20 實際只破壞 producer 的 `selected_timeframe` 預設；該欄位沒有對應 mutation。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:555
MUTATION: 在 assignments 組裝中刪除 `feature_timeframe` 欄，保留全量 producer 行為，再跑 Task 9.2a named tests；現行 M20 不能指向此破壞。
**來源摘要**: docs/SPLITUNIFY_TODO.md#9cbdedd0a735; docs/SPLITUNIFY_SPEC.D-002.md#60ad8380c73f
修法：為欄位遺失新增專屬 mutation／red test，並把 M20 留給 Task 9.2；可行性依據是 assignments 的明確欄位建構點（上列 anchor）。信心度=High；否則 mutation coverage 可假綠。

## CODEX-R13-P1-02
**斷言**: Task 9.3 receipt gate 只比較 `C5-NN` 行數，重複同一 ID 29 次即可通過，未證明 C5-01..29 逐條重掃，也未綁定當輪 receipt。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/tables.py:372
MUTATION: 保留 C5-29 的單鍵 lookup 不修，receipt 寫 29 行 `C5-01 ...`；現行判準仍輸出 `bad_receipt_count=29 spec_register_count=29 count_gate_equal=yes`。
**來源摘要**: docs/SPLITUNIFY_TODO.md#9cbdedd0a735; docs/SPLITUNIFY_SPEC.D-002.md#60ad8380c73f
修法：驗 sorted unique ID set 恰等於 `C5-01..C5-29`，並以 task／commit 綁定唯一 receipt、移除 `<該檔>` placeholder。RECHECK：對同一 duplicate probe 應 rc!=0；目前 probe 已證明 count-only gate 可被繞過。信心度=High。

## CODEX-R13-P2-03
**斷言**: B9D 寫「六個下游消費面」，但 Task 9.3 表列九列（並在 line 621 寫「九處」），批次 scope 文字不一致，可能漏做 pattern_bridge／event-level／frontend 面。
**碼證**: `docs/SPLITUNIFY_TODO.md:67`、`:606-616`、`:621`；表列計數=9。
**來源摘要**: docs/SPLITUNIFY_TODO.md#9cbdedd0a735
修法：將 B9D 的「六個」改成九處，或明確拆成六個 consumer modules + 三個 supporting surfaces；doc-literal-only，信心度=High。

1a/1b：CODEX-R1-P1-01/02/03/04 均 CLOSED；GROK-R1-P2-01（與 03 同題）CLOSED。實跑 `grep -nE '雙家族|兩家族' CLAUDE.md docs/MULTI_AGENT_ORCHESTRATION.md docs/DEVELOPMENT_GUIDE.md` 僅剩 ORCH:195 明示「本行原寫」之歷史說明；mutation IDs=34 且 01..34 無缺；前端 anchors 361/3174/各列測試行號吻合；`pytest -q -rxX tests/feature_engineering/test_ff_fullchain_truncation_mr.py::test_fracdiff_truncation_invariant` rc=0，`1 xfailed`；C5 count=29，TODO literal 在 629-630。Composer 獨立複驗四項，無新增 finding。
2：選六批 B9A–B9F；若併成五批，風險在 B9D/E 合批，執行兩組各自 named pytest + frontend build 時可見同檔 rebase／named test 遺失，故保留獨立 gate。
3：不值得重開已 APPROVED SPEC；C9 已承接 clusters event-level、purged/assignments disjoint、composite-key error message 三條 named tests，改壞會在對應測試轉紅；重開與三家重蓋章成本不換取本輪足夠風險下降。
4：現在不可領 impl token；最小閉合集合＝修正 C5-20 mutation 對應＋把 9.3 receipt 改為當輪 exact-ID-set gate（P1-01/P1-02）。
VERDICT: blocked
BLOCKED-BY: CODEX-R13-P1-01,CODEX-R13-P1-02
CLOSED: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03,CODEX-R1-P1-04
