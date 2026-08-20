# GAP-3 SPEC R4 codex review
task-id: `20260820-GAP3-X-REVIEW-R4` ｜ target: `docs/GAP3_EVENT_SPEC.md` sha256 `d65745d4962b`
## 閉合表
Z1: **NOT-CLOSED**；事件級 receipt 已補，但 `next_open` 與預設 `close_to_close` 的 label_start 關係未定義。
Z2: **CLOSED**；`drop_threshold=null` 時 c 不啟用，未命中 a/b 即 `unclassifiable`；x 值保留白話閘裁決，不列新 finding。
Z3: **CLOSED**；D4 與 B1.0/B2.2 一律使用 `counterexample_kind_effective`，並列 `n_unclassifiable`。
Z4: **CLOSED**；B1.4 與 M8 已同時要求非退化、非 identity、經驗分位三道硬檢。
R1 final: P0-01 **NOT-CLOSED via Z1**；P1-03 **CLOSED via Z2+Z3**；P1-07 **CLOSED via Y4+Z4**。
## CODEX-R4-P1-01
**斷言**: Z1 尚未形成單一可驗收的時間契約：`next_open` 嚴格晚於 t₀ close，而預設 `close_to_close` 的 label 基準是 t₀ close；D2.1 卻要求 `entry_at ≤ label_start`，SPEC 未定義此組合的 `label_start` 或 fail-closed 條件。
**碼證**: `nl -ba docs/GAP3_EVENT_SPEC.md | sed -n '23,33p;107p'` → D1.2/D1.4 鎖 t₀ close、D1.6 定義 next bar open、D2.1 要求 `entry_at≤label_start`、§G-2 僅要求三形 receipt exact；`git diff --unified=0 c7ac693e..3b254e2f -- docs/GAP3_EVENT_SPEC.md` → Z1 只補 receipt 層，未補該跨欄位語意。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#d65745d4962b; 白話說明/GAP-3事件型討論.md#7c884b1cdb70; handoffs/reconcile/20260820-gap3-x-review-r3/synth.md#fd7610553bcf
[MAJOR, 信心度=High] 以 t₀ bar open < t₀ bar close < next bar open 的實際時間順序，若 `label_start=t₀ close` 則 invariant 失敗；若改成 next-open 又改變 close-to-close label 起點。需明定禁止組合，或拆開 label benchmark 與 actual-holding window，並把 `label_start/label_end` 語意納入 §G-2 exact oracle。
## §1 sweep
1 矛盾=見 P1-01；2–11（端到端、可測、quant、過度工程、OOM、cache、API、測試品質、Agent 可執行性、短命工）無新增 finding。
## Verdict
需修補後才能進三家 RECONCILE-STAMP＋使用者白話閘；Z2–Z4 已閉合，但 Z1 的跨欄位時間語意仍不可驗收。
ASSUMPTIONS_VERIFIED: target sha256 與 brief；template_check PASS rc=0；Z2 覆蓋、Z3 derived routing、Z4 三道硬檢及 R1 三條狀態均完成逐條重跑。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS (spec)`, rc=0；`sha256sum`、`git diff c7ac693e..3b254e2f`、`nl -ba` receipts → 上述摘要。
FAILURES_SEEN: review finding CODEX-R4-P1-01；無命令測試失敗。
SCOPE_CHANGES: review-only；未改 SPEC、程式或既有 dirty files。
NUMERIC_OR_SCHEMA_IMPACT: 未修改輸出；指出 receipt/label 時間欄契約仍需補定義。
HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r4-codex.md`
TMP_CLEANUP: `/tmp` 無 workdir 目錄；`/private/tmp/claude-501` 保留，未刪除其他無關項。
STATUS: DONE
