REVIEW_COVERAGE: 11 類逐項掃描；L1=部分(-01), L2=部分(-05), L3=閉, L4=閉, L5=閉, L6=閉, L7=未閉(-02), L8=部分(-04), L9=部分(-03), L10=部分(-07), L11=閉；G-4e 同錯、L8/L9 反例與 D-001/golden/TODO §E 衝突均有實證。
## CODEX-R10-P1-01
**斷言**: G-4e 的第三份「純函式」未要求與投影、oracle、共享 helper 獨立，三者仍可同錯；**碼證**: `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '128,130p;264,268p'` 僅見三者全等、M28 僅改投影+oracle；反例 `decision=250, cutoff=200, train_last=200, test_start=300` 以共享錯誤 cutoff helper 判 train 時 G-3b/G-4e 均綠；**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; scripts/freeze_splitunify_golden.py#e331623163d2；失敗是相關性錯誤漏放，修法為禁止第三判準 import/call 兩邊及 helper，並用 fixture literal expected-side/mutation，信心度=High。
## CODEX-R10-P1-02
**斷言**: Task 9.1 雖寫 producer→summary→metadata，現有 metadata caller 仍無 `EventSplitPlan`/`discarded`，整鏈沒有可執行入口；**碼證**: `nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '648,691p;1530,1534p'` 只傳 n_test 等欄；API inline run grep stdout 空、rc=1；**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293; momentum/Analysis/event_samples/split_projection.py#99bfddace904；孤立 builder 單測可綠而 producer 計數遺失，修法是指名同一 context 來源及值相等 E2E 或移除不可達層，L7 未閉，信心度=High。
## CODEX-R10-P1-03
**斷言**: Task 9.2b 要 derive 呼叫 validator，卻未定義 D-001 `row_index_local` 對 validator 全域 `row_index`/`ts` 的 adapter；**碼證**: 交錯 A/B fixture 實跑 stdout=`A row_index=[0] [2] row_index_local=[0] [1]`; `validator(local universe)= IndexError plan.row_index contains positions outside base universe`；SPEC 184/587-589/634-637 同時要求 validator、local index、傳 local index；**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; momentum/core/contracts.py#1471cef968a3；L9 非空/不重疊已補但座標未閉，修法是明定 full-universe inputs 或 local rebase adapter 加非連續位置 fixture，信心度=High。
## CODEX-R10-P1-04
**斷言**: L8 新增 `n_test_events`/`n_test_samples` 仍未定義既有 baseline `n_test` 的退役、alias 或唯一語意；**碼證**: `baseline.py:105-121` 實為 `n_test=len(idx)`；缺一 test event 的實跑 stdout=`n_test=1 ... test_event_ids=['e2','e3'] ... intersection=['e2']`，事件數=2、樣本數=1；**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; momentum/Analysis/event_samples/baseline.py#38c7ec473653；下游可混讀，修法是定 baseline exact schema、明確移除/保留 n_test 並補 failure fixture，L8 部分閉，信心度=High。
## CODEX-R10-P1-05
**斷言**: G-4d 的 v8 baseline 保留沒有 immutable key/file/hash 或 allowed-diff schema，現行 `--write` 可覆寫同一 golden；**碼證**: `freeze_splitunify_golden.py:373-386` 實為 `golden_path.write_text(...)`，現有 JSON 頂層只有 g1/g3b/g4/g5、無 v8 key；default freeze 實跑 `GOLDEN OK` 只驗當前檔；**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; scripts/freeze_splitunify_golden.py#e331623163d2; tests/golden/splitunify/splitunify_golden.json#f270e007ca98；M29 不可驗，修法是 separate v8 hash + versioned new key 並斷言舊 hash 不變，L2 未完全閉，信心度=High。
## CODEX-R10-P1-06
**斷言**: D-002-C5 標題宣稱 16 處，但四層 named entries 可機械計為 20，逐處 mutation coverage 不可驗；**碼證**: `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '70,82p'` 配計數 stdout=`C5-layer-counts: 4+6+6+4=20`，標題為「單鍵消費面（16 處，分四層）」；**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab；實作者可按 16/20 漏改漏測，修法是唯一編號 register 逐列映射 9.3/9.4/9.5、mutation、測試並修回退文字，信心度=High。
## CODEX-R10-P2-07
**斷言**: `SU-RESID-9A-UI` trigger/recheck 只匹配 inline constructor，漏掉 `pipeline=create_event_sample_pipeline(); pipeline.run(...)`；**碼證**: `rg -n 'EventSamplePipeline\(\)\.run|create_event_sample_pipeline\(\)\.run' api --glob '*.py'` stdout 空、rc=1，而 SPEC/TODO 把此 regex 當觸發；**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; docs/SPLITUNIFY_TODO.md#b3a646c0e1cc; momentum/factories.py#ef545e89f580；此 governance trigger 會漏報接線，修法是 AST/廣域 production call-site 掃描並排除 tests、驗 canonical args，信心度=High。
ASSUMPTIONS_VERIFIED: R9 synth 21 findings/11 groups；D-002 mutation table 01–31 set 連續（實跑 rows=31,result=PASS）；golden default rc=0；obligation/format/xref rc=0；API inline trigger 當前 0。
TESTS_RUN: `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0（A/C 2 rows、B/D expected raise）；`venv/bin/python scripts/freeze_splitunify_golden.py` rc=0/GOLDEN OK；validator/baseline counterexample commands above；`bash scripts/obligation_block_check.sh ...`, `doc_format_precheck.sh ...`, `spec_xref_check.sh --synth ...` 皆 rc=0。
FAILURES_SEEN: 僅 review counterexamples：baseline missing-materialization n_test=1；local-universe validator IndexError；均為規格缺口證據，未修改程式。
SCOPE_CHANGES: none；只新增 `handoffs/20260911-splitunify-b9-review-r10-codex.md`，未改 code、SPEC、TODO、data_cache 或既有 dirty files。
NUMERIC_OR_SCHEMA_IMPACT: 未修改執行輸出；本報告指出 D-002 metadata/baseline/golden schema 與 C5 coverage 需補契約。
VERDICT: blocked
BLOCKED-BY: CODEX-R10-P1-01,CODEX-R10-P1-02,CODEX-R10-P1-03,CODEX-R10-P1-04,CODEX-R10-P1-05,CODEX-R10-P1-06
CLOSED:
STATUS: DONE
