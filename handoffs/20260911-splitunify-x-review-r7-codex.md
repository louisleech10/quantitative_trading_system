# SPLITUNIFY D-001 閉合確認 R7（codex）
task-id: 20260911-SPLITUNIFY-X-REVIEW-R7；brief-kind: closure；findings-round: R7
## CODEX-R7-P1-01
**斷言**: D-001 保留 producer 的全框 `SplitPlan.row_index`，但新入口只收每 symbol 的 post-trim `feature_index_by_symbol`；主成員判定未定義 global→symbol-local 映射，交錯 symbol 會錯分或越界。
**碼證**: D-001:31-34、50、63-70 明定 per-symbol index、轉換只在 fingerprint；`nl -ba momentum/core/contracts.py | sed -n '638,665p'` → `"""逐 symbol 呼叫 splitter，將 local index 轉回全 frame row position。"""`、`row_index=train_rows`；`nl -ba momentum/Analysis/ic_split_adapter.py | sed -n '230,246p'` → `train_rows = positions[train_local]`／`row_index=train_rows`、test 同形。D-001:81-85 的正向 ASSERT 未釘 membership 的 global→local 路徑。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#3fca8643e4c0；momentum/core/contracts.py#642aecf26b32；momentum/Analysis/ic_split_adapter.py#c2dd93482826
影響／修法判定：A/B 交錯時 B 的全框 row 3 對 B-local index 長度 2 會越界，或在較長 index 下取到錯時刻；b8 不能證明 assignment 正確。規格需明定 membership 的 exact global→local 轉換與其 producer-attested 交錯測試，或改採 symbol-local `row_index` 並同步全框消費者。
R6 重驗：`CODEX-R6-P1-01` 未閉合（fingerprint bridge 已補，membership bridge 未補）；`CODEX-R6-P1-02` 已閉合（D-001:77、93-111 已納入 wiring/golden/script、producer 欄與 oracle）；`GROK-R6-P1-01` 已閉合（D-001:56-60）；`GROK-R6-P2-01` 已閉合（D-001:48-49）；`GROK-R6-P2-02` 已閉合（D-001:16-20、28-42）。
必答2①：同一 helper 且只以傳入 symbol index 建立轉換時，不構成第二份 row 語意；但 producer、membership、freeze/oracle 各自重寫映射就會構成第二來源，現行文字未封住 membership 這一處。
必答2②：`SU-RESID-4` 可作後續遷移債，前提是 b8 先釘住上述 membership 映射；以目前文字上線會讓全框與 local 兩套座標在主判定並存，具體結果是交錯資料錯分／IndexError，故尚不能進實作。
必答3：不可進實作；先處理 `CODEX-R7-P1-01`。
ASSUMPTIONS_VERIFIED: D-001、TODO、R6 synth 已讀；D-001 sha256=3fca8643e4c0；producer 全框 row_index 由兩處碼證核對；R5 xref rc=0、D-001 format/template rc=0、consult stamps rc=0、attribution rc=0。
TESTS_RUN: `bash scripts/agent_preflight.sh` rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-001.md` rc=0；`bash scripts/template_check.sh dext docs/SPLITUNIFY_SPEC.D-001.md` rc=0；`bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md docs/SPLITUNIFY_SPEC.D-001.md` rc=0；`bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md docs/SPLITUNIFY_SPEC.D-001.md` rc=0；`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` rc=0；`bash scripts/reconcile_cluster_attribution_check.sh handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md` rc=0。
FAILURES_SEEN: R6 synth stamp check rc=1（缺 `## 戳記`）；R6 xref 以錯誤多檔參數呼叫曾 rc=1，改用正確單一 synth/target 參數後 rc=0。
SCOPE_CHANGES: none；只新增本交件檔，未改 tracked code/data、未 commit/push、未跑 governance 全套。
NUMERIC_OR_SCHEMA_IMPACT: none；本輪只審 D-001，未改數值、schema、golden 或輸出資料。
OUTPUT_ARTIFACT: handoffs/20260911-splitunify-x-review-r7-codex.md
VERDICT: blocked
BLOCKED-BY: CODEX-R7-P1-01
CLOSED: CODEX-R6-P1-02
STATUS: DONE
## 戳記
RECONCILE-STAMP: codex APPROVED 2026-09-12 sha256:79a5e81c82d984c4181e9f6248ebdebc1cc34f2ea4f0be55a9d8f23c02dc2283 task:20260911-SPLITUNIFY-X-REVIEW-R7
