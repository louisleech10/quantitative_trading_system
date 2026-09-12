REVIEW_COVERAGE: 1) 11 類逐項掃描；2) L1=部分(CODEX-R10-P1-01), L2=部分(-05), L3=閉, L4=閉, L5=閉, L6=閉, L7=未閉(-02), L8=部分(-04), L9=部分(-03), L10=部分(-07), L11=閉；3) G-4e 同錯反例見 -01；4) L8/L9 實跑反例見 -04/-03；5) D-001、golden、TODO §E 衝突見 -03/-05/-07。
## CODEX-R10-P1-01
**斷言**: G-4e 的「第三份純函式」沒有要求與投影、oracle 及共享 helper 實作獨立，不能阻止三者同錯。
**碼證**: VERIFY `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '128,130p;264,268p'`：G-4e 僅要求三者全等、M-SU-D2-28 僅改投影+oracle；反例 `decision=250, cutoff=200, train_last=200, test_start=300`，共享錯誤 helper 以 cutoff 判 train 時三者全等，G-3b/G-4e 均綠。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; scripts/freeze_splitunify_golden.py#e331623163d2。G4e 可抓不對稱錯誤但放過相關性錯誤；修法是第三判準禁止 import/call 兩邊及其 helper，另以 fixture literal expected-side 與 mutation 驗證；信心度=High。
## CODEX-R10-P1-02
**斷言**: Task 9.1 雖寫 producer→summary→metadata handoff，現有唯一 metadata caller 仍無 `EventSplitPlan`/`discarded`，整鏈並未被指定到可執行入口。
**碼證**: VERIFY `nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '648,691p;1530,1534p'`：caller 只傳 `n_test/test_timestamps_ms/per_symbol_counts`；`rg -n 'EventSamplePipeline\(\)\.run|create_event_sample_pipeline\(\)\.run' api --glob '*.py'` stdout 為空、rc=1。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293; momentum/Analysis/event_samples/split_projection.py#99bfddace904。孤立 builder 單測可綠而真實 producer 計數遺失；修法是指名同一 caller/context 的來源物件與值相等 E2E，或移除不可達層；L7 未閉，信心度=High。
## CODEX-R10-P1-03
**斷言**: Task 9.2b 要求 derive 呼叫既有 validator，卻未定義 D-001 `row_index_local` 與 validator 全域 `row_index`/`ts` 的 adapter，合法交錯 multi-symbol 路徑可被錯誤拒絕。
**碼證**: VERIFY 實跑 `venv/bin/python` 交錯 A/B fixture stdout：`A row_index=[0] [2] row_index_local=[0] [1]`; `validator(local universe)= IndexError plan.row_index contains positions outside base universe`；SPEC `nl -ba ... | sed -n '184p;587,589p;634,637p'` 分別要求 validator、宣告 local index、傳入 local index。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; momentum/core/contracts.py#1471cef968a3。L9 的非空/不重疊補強成立，但座標契約未閉；修法是明定 full-universe inputs 或 local rebase adapter，並加非連續 global positions fixture；信心度=High。
## CODEX-R10-P1-04
**斷言**: L8 新增 `n_test_events`/`n_test_samples` 仍未定義既有 baseline `n_test` 的退役、alias 或唯一語意，物化失敗時下游可讀到歧義。
**碼證**: VERIFY `nl -ba momentum/Analysis/event_samples/baseline.py | sed -n '105,121p'` 顯示 `n_test=len(idx)`；實跑缺一個 test event 的 fixture stdout：`n_test=1 ... test_event_ids=['e2','e3'] ... intersection=['e2']`，故事件數=2、樣本數=1。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; momentum/Analysis/event_samples/baseline.py#38c7ec473653。L8 只部分閉合；修法是定義 baseline exact schema、明確移除/保留 `n_test` 並更新 consumer/test，固定 failure fixture 斷言兩量；信心度=High。
## CODEX-R10-P1-05
**斷言**: G-4d 的「保留 v8 baseline、重凍寫新鍵」沒有指定 immutable key/file/hash 或 allowed-diff schema，現行 `--write` 仍可直接覆寫同一 golden。
**碼證**: VERIFY `nl -ba scripts/freeze_splitunify_golden.py | sed -n '373,386p'` stdout 顯示 `golden_path.write_text(...)`；`sed -n '1,28p' tests/golden/splitunify/splitunify_golden.json` 只有 `g1_membership/g3b_oracle/g4...`，無名為 v8 的舊鍵；default freeze 實跑 stdout `GOLDEN OK` 只證目前單檔相等。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; scripts/freeze_splitunify_golden.py#e331623163d2; tests/golden/splitunify/splitunify_golden.json#f270e007ca98。M-SU-D2-29 沒有指定不可變物件與測試落點；修法是 separate v8 baseline/hash + versioned new key，先驗舊 hash 不變再允許列舉差異；L2 未完全閉，信心度=High。
## CODEX-R10-P1-06
**斷言**: D-002-C5 標題宣稱 16 處，但自身四層 named entries 可機械計為 20，沒有 canonical register 會讓逐處 mutation coverage 不可驗。
**碼證**: VERIFY `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '70,82p'` 並計算 stdout `C5-layer-counts: 4+6+6+4=20`；標題原文為 `單鍵消費面（16 處，分四層）`。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab。實作者可按 16 或按 20 漏改/漏測；修法是公布唯一編號 register，逐列映射 Task 9.3/9.4/9.5、mutation 與測試，並修正回退文字；信心度=High。
## CODEX-R10-P2-07
**斷言**: `SU-RESID-9A-UI` 的 trigger/recheck 只匹配 inline constructor call，會漏掉合法的 factory assignment 後 `.run()` 生產接線。
**碼證**: VERIFY `rg -n 'EventSamplePipeline\(\)\.run|create_event_sample_pipeline\(\)\.run' api --glob '*.py'` stdout 空、rc=1；TODO/SPEC 皆把此 regex 當觸發。反例 `pipeline=create_event_sample_pipeline(); pipeline.run(...)` 不命中，殘留可錯誤維持。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; docs/SPLITUNIFY_TODO.md#b3a646c0e1cc; momentum/factories.py#未取摘要。這是 governance trigger 漏報；修法是 AST/更廣的 production call-site 掃描並排除 tests、要求 canonical args；信心度=High。
ASSUMPTIONS_VERIFIED: R9 synth 21 findings/11 groups；D-002 mutation table 01–31 set 連續（實跑 rows=31,result=PASS）；golden default rc=0；obligation/format/xref rc=0；API inline trigger 當前 0。
TESTS_RUN: `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0（A/C 2 rows、B/D expected raise）；`venv/bin/python scripts/freeze_splitunify_golden.py` rc=0/GOLDEN OK；validator/baseline counterexample commands above；`bash scripts/obligation_block_check.sh ...`, `doc_format_precheck.sh ...`, `spec_xref_check.sh --synth ...` 皆 rc=0。
FAILURES_SEEN: 僅 review counterexamples：baseline missing-materialization n_test=1；local-universe validator IndexError；均為規格缺口證據，未修改程式。
SCOPE_CHANGES: none；只新增 `handoffs/20260911-splitunify-b9-review-r10-codex.md`，未改 code、SPEC、TODO、data_cache 或既有 dirty files。
NUMERIC_OR_SCHEMA_IMPACT: 未修改執行輸出；本報告指出 D-002 metadata/baseline/golden schema 與 C5 coverage 需補契約。
VERDICT: blocked
BLOCKED-BY: CODEX-R10-P1-01,CODEX-R10-P1-02,CODEX-R10-P1-03,CODEX-R10-P1-04,CODEX-R10-P1-05,CODEX-R10-P1-06
CLOSED:
STATUS: DONE
