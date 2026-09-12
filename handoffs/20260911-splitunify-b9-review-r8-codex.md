## CODEX-R8-P1-01
**斷言**: G-4a 的「重凍後只准因換錨改側」目前不可機械歸因，會讓錯誤實作與合法換錨差異一起被新 golden 接受。
**碼證**: `freeze_splitunify_golden.py:373-382` 的 `--write` 直接覆寫 golden；現行 `_manifest` 把 decision_at_ms 設成 feature_cutoff_ms，oracle 也沿用 cutoff，沒有 immutable v8 baseline、獨立 expected delta 或 decision!=cutoff fixture。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c; scripts/freeze_splitunify_golden.py#e331623163d2
[MAJOR] 信心度=High；重凍可同時掩蓋 membership/fingerprint 錯誤，commit message 不是 gate。保留 v8 baseline，另以獨立 old/new anchor 計算逐事件 expected side-flip，僅允許該集合變更且其餘 payload/NaN-mask/hash exact，並加入 decision_at_ms != feature_cutoff_ms fixture。
## CODEX-R8-P1-02
**斷言**: Task 9.1 將終端可見性延期後，Phase 9A 的「使用者看得到」與實際交付互斥；`blocked-by` 是呼叫圖事實但不是完成理由，且 §V 的舊 API/UI mutation 仍不可達。
**碼證**: `api/services/case_import_service.py:1592-1609` 實跑對 `build_event_keys` 為 0 個呼叫、只走 `run_event_study_only_with_params`；D-002 卻同時保留 terminal-visibility objective、producer-only delivery 與 API/UI mutation 02/03。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c; api/services/case_import_service.py#d2571793953f; tests/api/test_splitunify_event_study_only.py#c00ff1c14753
[MAJOR] 信心度=High；只完成 producer/summary 會讓實際使用者仍看不到丟棄列，驗收不能通過。要麼把 Phase 9A 留 blocked 並在 TODO §E 登記具名 residual/觸發依賴，要麼擴大本票到真實 producer route；不可用僅列 §N 的敘述冒充完成。
## CODEX-R8-P1-03
**斷言**: D-002 要求 `metadata.split_unify` 新增 `discarded_rows_by_feature_tf`，但既有封閉 contract、producer 與 orchestrator/test/UI shape 仍是精確五鍵，Task 9.1 未列出同步施工面。
**碼證**: `build_split_unify_disclosure` (`split_projection.py:123-180`) 只回五鍵且唯一 caller `ic_filter_orchestrator.py:1530-1534` 不傳 discarded；`tests/api/test_splitunify_disclosure.py:149-151,270-277` 對 `split_unify` 做 exact-key assertion。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c; momentum/Analysis/event_samples/split_projection.py#99bfddace904; momentum/Analysis/contracts/split_unify.json#5aaf5f8efa15; tests/api/test_splitunify_disclosure.py#f1bd211204f7
[MAJOR] 信心度=High；只改 summary/metadata 會被現行 contract gate 擋，改 contract 又需明定 Dict[str,int] schema、producer、caller、Python/TS tests。把這些檔案與 exact-key migration 納入 Task 9.1，並明確保留 reason 封閉值集。
## CODEX-R8-P1-04
**斷言**: Task 9.2b 的時間域四條規則有重疊且順序宣稱不得調換，故索引界外 decision 可能先被判 train/test 而非 fail-closed raise。
**碼證**: `decision<=train_last_ms ⇒ train` 與 `decision>=test_start_ms ⇒ test` 排在「早於 index_ms[0]／晚於末列 ⇒ raise」之前；例如 index=[100,200,300,400]、train_last=200、test_start=300 時 decision=50 同時命中 train 與 outside，decision=450 同時命中 test 與 outside。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c; momentum/Analysis/event_samples/split_projection.py#99bfddace904
[MAJOR] 信心度=High；實作者可合法選先分類，造成越界事件進 train/test。先以 `index_ms[0] <= decision <= index_ms[-1]` 作 precondition 並補 early/late tests，再套三段式側別規則。
## 必答1-5: R7-P1-01/02/04/06 依 D-002 逐文與現碼重核已閉合；R7-P1-03/05 的原矛盾已被文字決策取代但其落地仍分別重開為本輪 P1-02/P1-01。G-4a 不等於可驗回歸，替代方案見 P1-01；Task9.1 的 blocked-by 呼叫圖判斷正確但延期使 9A 名存實亡。M-SU-D2-04→多TF materialization value/count；06→tables event-level lookup；07→ic_feed survivor value；08→counterexample receipt binding；09→candidate ledger binding；10→dedupe「兩TF存活、簇一列」；11→export extras lookup；現行 repo 沒有這七條具名 mutation harness/多TF fixture，故均未實跑，M10 更因 dedupe 只吃 event_level 而在現 seam 無法生成、屬未封可測性。J1/J2/J6/J7 多已同步，J3/J8 與 terminal/schema 衝突，J4 有本輪優先序衝突，J5 與 golden 需雙基準；D-001 事件級物化與 C6 量詞不能被複合列數改寫，既有 golden 只證換錨前行為。
ASSUMPTIONS_VERIFIED: R7 synth 15條/8群全採納、gap1/gap2 purged、cutoff<decision、api 無實際 EventSamplePipeline.run caller、現行 contract exact 五鍵；G4a causal diff、七 mutation 實紅性、dedupe 權重未驗證。
TESTS_RUN: `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0（C 靜默丟列）；`venv/bin/python scripts/freeze_splitunify_golden.py` rc=0/GOLDEN OK；兩組 pytest 分別 115 passed、85 passed；doc_format、obligation、synth-xref rc=0；指定 completeness 命令 rc=0（4 IDs）。
FAILURES_SEEN: 曾用過時 `spec_xref_check.sh --synth` 形式 rc=2，改用正確形式後 rc=0；第一次 completeness 被 PreToolUse debt gate 擋、`gate.sh dispatch` 因本輪 OPEN debt rc=1，隨後指定 completeness 命令 rc=0；未改碼、未改測試斷言。
SCOPE_CHANGES: 僅新增 `handoffs/20260911-splitunify-b9-review-r8-codex.md`；未改 SPEC/TODO/code/data_cache；NUMERIC_OR_SCHEMA_IMPACT=未改輸出，指出 split_unify schema/anchor baseline 缺口；TMP_CLEANUP=未發現非 claude-501 的 workdir，`/private/tmp/claude-501` 保留。
VERDICT: blocked
BLOCKED-BY: CODEX-R8-P1-01,CODEX-R8-P1-02,CODEX-R8-P1-03,CODEX-R8-P1-04
CLOSED:
STATUS: DONE
