# GAP-3 B5 Review R3 — codex
TASK_ID: 20260822-GAP3-B5-REVIEW-R3
SCOPE: 依 brief 審查 c062dcda..HEAD；review-only，禁改產品碼、測試、data_cache、root HANDOFF.md。
VERDICT: NOT READY FOR RECONCILE-STAMP/UAT；CODEX-R2-P1-03 OPEN；R3 新 findings 3（P1=2，P2=1）。
R2_CLOSURE: CODEX-R2-P1-01 CLOSED、P1-02 CLOSED、P2-01 CLOSED；GROK-R2-P2-01 複核同意 CLOSED；COMPOSER-R2-P3-00 複核同意 CLOSED。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k decision_bar`→1 passed/rc0；`npx vitest run gap3`→3 files/17 passed/rc0；`venv/bin/python -m pytest tests/api -q -k 'gap3_import and verify'`→2 passed/rc0；`npm run build`→rc0；`pytest tests/api/ -q -k gap3_import`→14 passed/rc0；`pytest tests/momentum/event_samples/ -q`→230 passed/rc0。
GATE_CROSSCHECK: `npm run build`、vitest、API gap3_import、event_samples 均 rc0；`bash scripts/plain_docs_sync_check.sh` fresh→rc1（GAP-3施工進度.md 過期），故不可 stamp/UAT。
ASSUMPTIONS_VERIFIED: decision-root 與 entry semantic 自洽；disclosure 只渲染 rule/note/選定 manifest 欄；realtime 可缺 future 欄且 conditional IC 會 missing_label_value unavailable；未改碼。
## CODEX-R2-P1-01
**斷言**: k>0 訊號改標 decision bar、mixed-k 拒收已 CLOSED。 **碼證**: `pipeline.py:122-166` 以 `vals[i-k]` 建 score；`test_pipeline.py -k decision_bar`→1 passed，n_signal_bars=3、k=2、mixed-k=batch_not_single_valued。 **來源摘要**: momentum/Analysis/event_samples/pipeline.py#db3d29667082；tests/momentum/event_samples/test_pipeline.py#fc12718ec299；CLOSED。
## CODEX-R2-P1-02
**斷言**: label_value 改取同 horizon future_Nbar_return、short 取負、缺欄不寫並記 skipped 已 CLOSED。 **碼證**: `eventExport.ts:81-120`；`npx vitest run gap3`→17 passed，覆蓋 h=2/h=4/short/缺欄。 **來源摘要**: frontend/src/lib/eventExport.ts#8966db1df2a1；CLOSED。
## CODEX-R2-P1-03
**斷言**: JSON verify 拒收已落地，但 `/search` export 仍沒有可成功走 verify 的檔案路徑，原 finding OPEN。 **碼證**: exporter `eventExport.ts:27-37,65-66,117-120` hash canonical source cases；file route `case.py:151-155` 傳整個 upload bytes；contract 要求檔內 `source_file_digest`（event_import_contract.json:5-10,50）；verify 測試只有 `test_gap3_import.py:207-220` mismatch，fresh verify→2 passed。 **來源摘要**: frontend/src/lib/eventExport.ts#8966db1df2a1；api/routes/case.py#03a4cf0c2baa；momentum/Analysis/contracts/event_import_contract.json#7111b2d7060e；OPEN：需提供可驗證的 canonical/source bytes 對證設計。
## CODEX-R2-P2-01
**斷言**: all-bars estimand disclosure 已 CLOSED，未見過量內部欄位外洩。 **碼證**: `EventTablesPanel.tsx:106-123` 僅渲染 rule/note、horizon/threshold/direction/entry/k/eligibility、signal counts；`npx vitest run gap3`→17 passed。 **來源摘要**: frontend/src/components/ic-analysis/EventTablesPanel.tsx#5e3cffae61e9；CLOSED。
## CODEX-R3-P1-01
**斷言**: R2 修補後 B5 Gate 的 plain-docs 關卡實際為 rc1，receipt/brief 的 rc0 敘事與 HEAD 不一致，阻擋 stamp/UAT。 **碼證**: `bash scripts/plain_docs_sync_check.sh` stdout→`GAP-3施工進度.md` last update bcabb668 落後 watched 1c54049b，`rc=1`；腳本 `plain_docs_sync_check.sh:199-215` 對此返回 1。 **來源摘要**: scripts/plain_docs_sync_check.sh#1d127ae13f1a；白話說明/GAP-3施工進度.md#91cce3238294；[P1] confidence=10/10；同步看板後重跑同命令。
## CODEX-R3-P1-02
**斷言**: realtime `/search` 匯出未先提示缺 horizon 欄時，整批可無 label_value，使用者後續 conditional IC 只能 loud unavailable。 **碼證**: `search/page.tsx:520-524` 未傳 horizon/未檢查缺欄；`case_search_engine.py:1527-1532` realtime 保留尾端；`eventExport.ts:61,83-86` 預設 h=2 且缺欄省略；`ic_feed.py:44-46`→missing_label_value。 **來源摘要**: frontend/src/app/search/page.tsx#04ac28eca77b；frontend/src/lib/eventExport.ts#8966db1df2a；momentum/Analysis/event_samples/ic_feed.py#5710f3436654；[P1] confidence=9/10；匯出前統計缺欄並提示/阻擋或明選 horizon。
## CODEX-R3-P2-03
**斷言**: 新增 decision-root regression test 沒有驗 score 實際落在 t0-k，因 `spy` 未 monkeypatch 且 `captured` 只斷言非 None，舊錯位可通過。 **碼證**: `test_pipeline.py:101-110` 定義 spy 但直接呼叫 `p.analyze_tables`；`112-115` 只驗 counts/config，`captured` 未被使用；該測試 fresh→1 passed。 **來源摘要**: tests/momentum/event_samples/test_pipeline.py#fc12718ec299；[P2] confidence=10/10；patch evaluator 或直接斷言 decision-bar score=1、t0 score=0。
FAILURES_SEEN: `plain_docs_sync_check.sh` fresh rc1；R2 receipt 內記錄的 rc0 與目前 HEAD 不符；其餘本輪 Gate 命令通過。
SCOPE_CHANGES: none；未改產品碼、測試、data_cache、root HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: review-only；未修改輸出；標記 digest verify closure、label_value availability、plain-doc Gate 與 regression coverage。
HANDOFF_OUTPUT: handoffs/20260822-gap3-b5-review-r3-codex.md
HANDOFF_NOT_UPDATED: root HANDOFF.md 由 Claude 維護；本檔為本任務唯一產出。
STATUS: DONE
