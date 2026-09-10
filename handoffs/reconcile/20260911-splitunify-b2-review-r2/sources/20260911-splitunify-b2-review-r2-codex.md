不可進 B2c：CODEX-R2-P1-01／CODEX-R2-P1-02／CODEX-R2-P1-03。
審查對象：commit e2e4314c 指定五檔；本輪定向 H1–H5＋malformed 負向注入。
## CODEX-R2-P1-01
**斷言**: H1 未閉合：exact ID set 對帳未拒絕重複 `event_keys.event_id`，會重複計數/輸出 assignment。
**碼證**: `split_projection.py:214-225,244-270` 只比 set 後逐列輸出；實跑 `duplicate_event_id => ACCEPT assignments=3, purged=2, assignment_ids=['e_train_ok','e_test','e_train_ok']`。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#afba86ba4a18;docs/SPLITUNIFY_SPEC.md#3e39458b00e4
P1／High；應在 projection 對帳前要求 `event_keys.event_id` 唯一並 fail-closed，否則 H1 身份完整性仍可被重複列穿透。
## CODEX-R2-P1-02
**斷言**: H3 未閉合：`assert_positional_rows` 先 `dtype=int` 靜默截斷非整數 float，且 feature index 未驗 sorted/unique。
**碼證**: `split_preview.py:89-109`；實跑 `row_index_nonintegral_float => ACCEPT assignments=2,purged=2`、`feature_index_unsorted => ACCEPT assignments=0,purged=1`、`feature_index_duplicate => ACCEPT assignments=1,purged=0`。
**來源摘要**: momentum/core/split_preview.py#9001fe15b4ff;momentum/Analysis/event_samples/split_projection.py#afba86ba4a18
P1／High；先驗原始 dtype/整數性、`feature_index` 單調遞增且唯一，再做 positional/時間投影，避免錯列被當成合法 boundary。
## CODEX-R2-P1-03
**斷言**: event-key timestamp/interval 完整性未 fail-closed；test-side 的 NaT 與 `label_end_ms < label_start_ms` 可產生 assignment。
**碼證**: `split_projection.py:170-172,244-267` 僅檢欄且只在部分分支轉 int；實跑 `label_end_NaT_test_side => ACCEPT assignments=2,purged=2`、`label_start_NaT_test_side => ACCEPT assignments=2,purged=2`、`label_end_before_label_start_test_side => ACCEPT assignments=2,purged=2`。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#afba86ba4a18;docs/SPLITUNIFY_SPEC.md#3e39458b00e4
P1／High；逐事件驗 finite/non-NaT、整數毫秒與 `label_start_ms <= label_end_ms`，不應因事件落 test 而跳過 malformed input。
## CODEX-R2-P2-04
**斷言**: `bucket_ms` 負值未拒絕，cluster 可產生負 ID；此為不擋 B2c 的 P2。
**碼證**: `event_split.py:39-65` 無正值 guard；實跑 `bucket_ms=0 => RAISE IntCastingNaNError`，`bucket_ms=-3600000 => ACCEPT cluster IDs [-472223,-472292,-472297,-472293]`。
**來源摘要**: momentum/Analysis/event_samples/event_split.py#f9dbcfd3c9d6;tests/golden/splitunify/clusters_oracle.json#8a9f3f733edd
P2／Medium；補 `bucket_ms > 0` 的明確 ValueError；不擋 B2c，因零值已 raise 且本輪 oracle/mutation 另有獨立覆蓋。
必答1：H1 未閉合（P1-01）；H2 閉合；H3 未閉合（P1-02）；H4 閉合；H5 閉合。
必答2：已擋：feature_index NaT→ValueError、cutoff NaN→ValueError、缺 event_id→ValueError、錯型→ValueError、manifest 缺 decision_at_ms→KeyError、bucket 0→IntCastingNaNError；未擋：test-side NaT、float row、負 bucket、反向 interval、unsorted/duplicate index（上述碼證為實跑 stdout）。
必答2續：H1/H2/H3 負向身份測試與 `pytest ...test_splitunify_derive.py` 重跑均驗；未擋項即 P1-01..03，非讀碼推定。
必答3：刪掉 `len(symbols)>1` 正確；plan symbol 非空、train/test 相等、event symbol exact-set 相等三道守衛後，無多 symbol 反例；mutation M-SU-2/M-SU-3/M-SU-16 均 rc=1。
必答4：oracle 獨立；JSON 手推 `472222/472223` 與 `1/0.5`，可抓 bucket 換算及權重公式錯；targeted 35 passed，15 mutants `UNCOVERED=0`。
必答5：不可以＋CODEX-R2-P1-01／P1-02／P1-03；非阻擋 P2-04 留後續。
TESTS_RUN: derive 重跑 `35 passed`；mutation 單獨重跑 `UNCOVERED=0`、C0 rc=0；回歸指定集合 `703 passed`；decoupling stdout `R2=1 R3=17 R4=3`（基線值，rc=1）。
FAILURES_SEEN: 首次 derive 曾報 2 failures，立即單獨/完整重跑皆 35 passed；第一次 mutation 與第二支併發造成不可信中間結果，無併發第三次為 UNCOVERED=0；restore script rc=128（sandbox 禁 `.git/index.lock`），inventory 無 diff。
SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: review only，未改碼/測試/規格/schema/output。
Verdict: 不可進 B2c：CODEX-R2-P1-01／CODEX-R2-P1-02／CODEX-R2-P1-03；P2-04 不擋 B2c。
STATUS: DONE
