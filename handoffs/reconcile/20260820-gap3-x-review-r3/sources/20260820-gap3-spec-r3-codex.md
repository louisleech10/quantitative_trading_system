# GAP-3 SPEC R3 codex review | target `docs/GAP3_EVENT_SPEC.md` @ `c7ac693e`
CLOSURE_TABLE: Y1 NOT-CLOSED (D2-4 receipt); Y2 NOT-CLOSED (unsupported drop default); Y3 NOT-CLOSED (D4 raw kind); Y4 CLOSED (per-M command/fixture/baseline/mutation); Y5 NOT-CLOSED (identity permutation); Y6 CLOSED (accepted set + shared validator + §N-7 reject).
R1_FINAL: CODEX-R1-P0-01 NOT-CLOSED via Y1; CODEX-R1-P1-03 NOT-CLOSED via Y2/Y3; CODEX-R1-P1-07 NOT-CLOSED via Y5 (Y4 closes only the metadata gap).
## CODEX-R3-P1-01
**斷言**: Y1 的 entry 映射仍未形成完整 receipt schema；D1-6 要求的 `entry_at_ms`/`entry_price_source` 沒有寫入 D2-4 的 canonical per-TF receipt 欄位。
**碼證**: `nl -ba docs/GAP3_EVENT_SPEC.md | sed -n '27,33p;107p'` → D1-6/G-2 提到兩欄，但 D2-4 仍只列 `{feature_cutoff_ms,last_bar_open_ms,last_bar_close_ms,row_id}`；`git diff --unified=0 21135434 c7ac693e -- docs/GAP3_EVENT_SPEC.md` → 無 D2-4 hunk。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; handoffs/reconcile/20260820-gap3-x-review-r2/synth.md#2618f362f721. [MAJOR, 信心度=High] 缺 canonical receipt 欄位時，agent 可只實作映射而不持久化 entry source，§G-2 無法驗證；需把兩欄及其 anchor TF/field 納入 D2-4／SoT。
## CODEX-R3-P1-02
**斷言**: Y2 把 `drop_threshold=0.05` 當成使用者 §2-4 原例，但原例只寫「跌 x%」，未裁定 x=5%。
**碼證**: `rg -n "drop_threshold|跌 x%|跌 [0-9]+%|漲≥5%|上下 1%" '白話說明/GAP-3事件型討論.md' docs/GAP3_EVENT_SPEC.md` → 使用者檔命中「漲≥5%」「上下 1%」「跌 x%」，5% 的 `drop_threshold` 只出現在 SPEC:184。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; 白話說明/GAP-3事件型討論.md#7c884b1cdb70. [MAJOR, 信心度=High] 這是未驗證假設被寫成 fact，會固定錯誤反向門檻；須移除該預設或取得明確裁決並將來源寫入契約。
## CODEX-R3-P1-03
**斷言**: Y3 的 derived 值集沒有覆蓋所有分層報表；D4 all-bars 仍要求按原始 `counterexample_kind` 分層，與「一律消費 `counterexample_kind_effective`」直接衝突。
**碼證**: `rg -n -C 2 "counterexample_kind|counterexample_kind_effective|unclassifiable" docs/GAP3_EVENT_SPEC.md` → D4:43 為 `counterexample_kind`，B1.0:126 宣告 derived 欄與 `unclassifiable` 分母規則，B2.2:221 才改用 effective 欄。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; handoffs/reconcile/20260820-gap3-x-review-r2/synth.md#2618f362f721. [MAJOR, 信心度=High] B2.5 可遺失平台自動分類或把使用者欄誤當全 K 線分類；D4 必須改用 effective 並列 `n_unclassifiable`。
## CODEX-R3-P1-04
**斷言**: Y5 的 M8 oracle 沒有保證恆等排列 mutation 會失敗；閉區間 `[q.025,q.975]` 在恆等排列下退化為觀測值本身，觀測值仍落帶內。
**碼證**: `nl -ba docs/GAP3_EVENT_SPEC.md | sed -n '173,174p;367p'` → oracle 以 permutation quantile 閉區間判定，M8 僅宣稱 identity mutation「必紅」，未定零變異/非恆等排列 gate。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; handoffs/reconcile/20260820-gap3-x-review-r2/synth.md#2618f362f721. [MAJOR, 信心度=High] 測試可對壞 oracle 報綠，R1 P1-07 仍未閉合；需明定 permutation 非恆等、null variance>0/固定 seed receipt 與量化帶判定。
## Verdict
需修補後才能進三家 RECONCILE-STAMP＋使用者白話閘；本輪有 4 條實質 finding，故不寫 sentinel。
ASSUMPTIONS_VERIFIED: target commit/hash、SPEC sha256、R2 synth 對照；R3 brief 審查標的為 SPEC，對應 TODO 檔目前不存在且未納入本輪標的。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → TEMPLATE PASS rc=0；§A exact sed/grep bundle → cited stdout reproduced；hash/rg/nl/git diff rechecks → summaries above。
FAILURES_SEEN: direct completeness shell invocation was PreToolUse-blocked; the same parameters in scratch passed rc=0；no review-check failure beyond the four SPEC gaps。
SCOPE_CHANGES: 未改碼、SPEC、TODO 或既有 dirty files；新增僅 `handoffs/20260820-gap3-spec-r3-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT: 未修改輸出；審查指出 receipt schema、derived field routing、未獲裁決的 drop default 與 mutation gate 缺口。
HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r3-codex.md`
STATUS: DONE
