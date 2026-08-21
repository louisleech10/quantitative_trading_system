# GAP-3 B5 Review R2 — Codex
TASK_ID: 20260821-GAP3-B5-REVIEW-R2
SCOPE: 依 brief 審查 eb3f9b4e..HEAD；禁改產品碼、測試與 data_cache。
VERDICT: NOT READY FOR RECONCILE-STAMP/UAT；4 findings（P1=3，P2=1）。
R1_CLOSURE: CODEX-R1-P1-01/02/03/04、P2-05/06 均就原始斷言 CLOSED；本輪新 finding 不回填舊 ID。R1_RECHECK: api gap3=12 passed/rc0；pipeline factories+all_bars=2 passed,3 deselected/rc0；Vitest gap3=3 files,17 passed/rc0；plain_docs_sync=rc0；CSV streaming/worker 仍屬 brief 明列之 G3-R10 殘留。
## CODEX-R2-P1-01
**斷言**: all-bars 將 event membership score 標在 t0，但 evaluator 以 decision_at=t0-k 取 score；k>0 時事件訊號被移到錯誤 target，且批內混合 k 仍取第一筆，rule/note 不能修正 estimand。
**碼證**: `pipeline.py:132-149` 建 MultiIndex(t0) 並取 `ev["decision_offset_bars"].iloc[0]`；`all_bars_eval.py:170-179` 用 ot[i-k] 取 score/entry；現有 pipeline test 未覆蓋 k>0。
**來源摘要**: source_digest: 5f09bf10b76a；`momentum/Analysis/event_samples/pipeline.py`、`all_bars_eval.py`；契約允許 decision_offset_bars，需以 decision_at 對齊或拒絕 mixed-k。
## CODEX-R2-P1-02
**斷言**: `label_value` 的 short 取負與 fraction 單位正確，但其來源 `case.price_change` 是 trigger bar 的 close.pct_change/open-to-close，不是 label_definition horizon 的未來答案窗報酬；條件 IC 因而測錯 label 語意。
**碼證**: `eventExport.ts:81-100` 以 price_change 寫 label_value、只把 horizon 放進 metadata；`case_search_engine.py:1229-1241,1293-1297` 分離計算 price_change 與 future_Nbar_return；`GAP3_EVENT_SPEC.md` D1.3 要求不靜默使用不同語意。
**來源摘要**: source_digest: 242b0a6d13aa；前端 export 與 `momentum/DataExtraction/case_search_engine.py` 的實跑靜態核對；應改用對應 future horizon 欄或明確要求 user label source。
## CODEX-R2-P1-03
**斷言**: export 的 `source_file_digest` hash canonical source cases，但 JSON API `verify_source_digest=true` hash sorted serialized request.records；將 export records 送該 verifier 會在未篡改時 `digest_mismatch`，違反 contract 的 source-file verification。
**碼證**: `eventExport.ts:27-37,65-66,102-115`；`api/routes/case.py:161-165` 將完整 records JSON 作 upload_bytes；`event_import_contract.json:50` 定義 source_file_digest 為匯入來源檔 sha256。
**來源摘要**: source_digest: 8a2077c8bc29；API route、export canonicalization、contract 三方語意不一致；需統一 verifier bytes 或拆分 source/provenance digest。
## CODEX-R2-P2-01
**斷言**: API 已產生 `rule` 與 `label_threshold_note`，但 `EventTablesPanel` 只顯示固定 rule 標題及 metrics，未渲染 threshold=0、signed-return label 語意或 manifest；使用者看不到 all-bars estimand 的完整 disclosure。
**碼證**: `pipeline.py:147-149` 產生欄位；`EventTablesPanel.tsx:97-133,214-215` 僅讀 counts/overall 並寫固定標題；`rg` 未找到前端讀取 `label_threshold_note`/manifest。
**來源摘要**: source_digest: 89a4c4e44b47；`docs/GAP3_UAT_CHECKLIST.md:B8b` 要求固定分母與 prevalence/lift 可見；應在表面呈現 note 或等價 manifest。
FOCUS_REVIEW: CSV chunksize/itertuples 未發現新的語意錯誤（仍是 records materialization，G3-R10 明列殘留）；_canon_cols 僅用於 schema detection，變體測試通過；event_timestamps 的 elif 保留 event_query 分支，timestamps-only API 測試通過；無 perf threshold，不以 RSS receipt 重開 G3-R10。
GATE_CROSSCHECK: R1 fix-gate receipt 記錄 build/vitest/event/api/doc gate rc=0；本輪 fresh API/pipeline/Vitest/plain-docs 均 rc=0；因上述 P1 findings，不能宣稱可 stamp/UAT close。
ASSUMPTIONS_VERIFIED: 實讀 brief、HANDOFF、CLAUDE、R1 synth/source/receipts；實讀並核對上述程式行號與 contract/spec；未改產品碼、測試、data_cache 或 root HANDOFF.md。
TESTS_RUN: `venv/bin/python -m pytest tests/api/ -q -k gap3_import`→12 passed,477 deselected,rc0；`venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k 'factories or all_bars'`→2 passed,3 deselected,rc0；`frontend:npx vitest run gap3`→3 files/17 passed,rc0；`bash scripts/plain_docs_sync_check.sh`→rc0；completeness single check→rc0。
FAILURES_SEEN: completeness 首次 rc1 因 P1 digest 僅 11 位 hex，已補至 12 位並重跑 rc0；R2 實跑無失敗；brief 指定既有 7 個 API red 為 G3-R11，不納入本輪 finding。
SCOPE_CHANGES: none。
NUMERIC_OR_SCHEMA_IMPACT: 未修改輸出；finding 涉及 all-bars estimand、label_value 語意、digest provenance 與 UI disclosure。HANDOFF_OUTPUT: handoffs/20260821-gap3-b5-review-r2-codex.md
STATUS: DONE
