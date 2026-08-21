# Reconcile — 20260821-gap3-b5-review-r2

**來源** 20260821-gap3-b5-review-r2-codex.md, 20260821-gap3-b5-review-r2-composer.md, 20260821-gap3-b5-review-r2-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置（主委 Claude 裁決；閉合輪＋codex 三條 P1／一條 P2、grok 一條 P2 寫回）

**Verdict**: 需修補後合併——R1 十一條由原提出方重跑全數 CLOSED（codex 6/6、grok 6/6、composer 1/1）；codex 本輪另抓 4 條（3×P1＋1×P2）、grok 1×P2，**全數採納修補**；R3 由原提出方重跑同一反例閉合 → 全 CLOSED 後三家 RECONCILE-STAMP → 交使用者 UAT。

**修後實測（receipt `handoffs/run_receipts/20260822T003000Z-gap3-b5-r2-fix-gate.log`）**：`tests/api -k gap3_import` **14 passed**；`tests/momentum/event_samples/` **230 passed**；`tests/momentum/feature_engineering/`＋`Analysis/strategy_validation` **289 passed**；`npx vitest run gap3 pendingFeatures` 4 files／**21 passed**；`npm run build` rc=0；`plain_docs_sync_check` rc=0。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| Y1 全 K 線訊號標錯根（k>0 estimand 壞） | CODEX-R2-P1-01 | **採納**：`evaluate_all_bars` 於觸發根 i 取 `scores[ot[i-k]]`（**決策根**索引），故訊號改標在「t₀ 往前 k 根 open」；批內混合 `decision_offset_bars` ⇒ `not_computed:batch_not_single_valued`（不再取 `.iloc[0]`）；缺決策根之事件記入 `signal_mapping.n_events_unmapped`（不靜默）。測試：k=2 三事件 ⇒ `n_signal_bars=3`／`indexed_at=decision_bar_open_ms`／`manifest.decision_offset_bars=2`；混合 k ⇒ 拒 |
| Y2 label_value 語意錯（觸發根報酬冒充答案窗報酬） | CODEX-R2-P1-02 | **採納**：`/search` 匯出改取 `future_{horizon}bar_return`（與 `label_definition.window.horizon_bars` 對齊；short 取負），**不再用** `price_change`；缺該欄 ⇒ 不寫 `label_value` 並記 `skipped`（條件 IC 會 loud unavailable，不靜默錯值）；回傳體加 `label_value_source`。測試：h=2 取 0.031（非 price_change 0.052）、h=4 隨欄改、short 取負 |
| Y3 digest 驗證語意三方不一致 | CODEX-R2-P1-03 | **採納**：JSON 端點傳 `verify_source_digest=true` ⇒ **400 `verify_unsupported_on_json_endpoint`**（body 位元組 ≠ 契約所指來源檔，比對必然不符）；檔案端點保留但 description 明寫「僅當上傳檔本身即來源檔」；匯出回傳體加 `verify_note`。測試：JSON 端點拒＋不落檔；檔案端點 digest 不符 ⇒ 422 `digest_mismatch`（契約字面）、關閉 verify ⇒ 收 |
| Y4 前端未揭露 all-bars estimand | CODEX-R2-P2-01 | **採納**：`EventTablesPanel` 增 disclosure 區塊，渲染 `rule`／`estimand_note`／`label_threshold_note`／`manifest`（horizon／threshold／direction／entry／k／eligibility）／`signal_mapping`；vitest 逐項斷言可見 |
| Y5 敘事計數再漂（232 vs 229） | GROK-R2-P2-01 | **採納**：確認 R1 修後實為 **229**（我在 brief／synth 寫 232 為錯，同摩擦八十七模式第二次）。本 synth 一律引本輪實測；R1 synth 之 232 已由本檔訂正（不回改凍結附錄）。修後現值 **230**（本輪新增 1 條 pipeline 測試） |
| Y6 兩家 R1 閉合＋sentinel | COMPOSER-R2-P3-00, GROK 正文 6/6, CODEX 正文 6/6 | **採認**：R1 十一條全 CLOSED；composer 0 新 findings |

**主委自陳（第二次同型）**：Y5 是計數敘事第二次漂——第一次 grok 已於 R1 指出（13 vs 9），我在 R1 修補敘事又寫錯（232 vs 229）。**根因＝我從記憶寫數字而非從 receipt 複製**。已改做法：Gate 敘事一律先跑 `grep -E "passed" <receipt>` 再貼。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——COMPOSER-R1-P3-00 閉合；他方 10 條 R1 修補複核皆 CLOSED；修補 diff 五點攻擊均不成立；本輪無 R2 新 P0–P2 缺陷。

**碼證**: B5 Gate 子集本輪複驗：`pytest tests/api/ -q -k gap3_import` → **12 passed** rc=0；`pytest tests/momentum/event_samples/ -q` → **229 passed** rc=0；`bash scripts/plain_docs_sync_check.sh` → rc=0；`cd frontend && npx vitest run gap3` → **17 passed** rc=0；`npx vitest run pendingFeatures` → **4 passed** rc=0。專項：`-k ic_timestamps` 1 passed、`-k all_bars` 1 passed、`-k case_variants` 1 passed、`-k ic_seconds` 1 passed、`-k factories` 1 passed；`grep -c '^def create_event_\|^def create_condition_' momentum/factories.py` → 1；`gap3_import_scale.json` api_path n_records=10000 wall_clock_s=0.382 http_status=200。

**來源摘要**: handoffs/reconcile/20260821-gap3-b5-review-r1/synth.md#8a1f2e3b4c5d；handoffs/run_receipts/20260821T230000Z-gap3-b5-r1-fix-gate.log#f1a2b3c4d5e6；momentum/Analysis/event_samples/pipeline.py#9c8d7e6f5a4b；frontend/src/lib/eventExport.ts#3e4f5a6b7c8d；handoffs/20260821-gap3-b5-review-r2-brief.md

正文：閉合義務本家 1/1 CLOSED；他方 10/10 複核同意；§0 兩條 assumed 攻擊不推翻。禁捏造湊數。

## GROK-R2-P2-01

**斷言**: R2 brief／R1 synth 之 fact-verified 敘事寫 `event_samples` **232** passed，但同一修後 receipt 內 pytest 輸出與本輪 HEAD 重跑皆為 **229** passed——屬「引 receipt 實測」義務未落實的計數漂移（同 GROK-R1-P2-01 失敗模式再犯於修補敘事）。

**碼證**: `handoffs/run_receipts/20260821T230000Z-gap3-b5-r1-fix-gate.log` 段「collected 229 items」／「229 passed」／`rc_event_samples=0`；本輪 `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → **229 passed** rc=0；`pytest … --co -q` → **229 tests collected**。對照 brief L34「232 passed」、synth L8／L22「232」。`RECHECK:` 重跑同上 pytest 計數須與任何 Gate 敘事一致。

**來源摘要**: handoffs/20260821-gap3-b5-review-r2-brief.md#72a1e61f82a6；handoffs/reconcile/20260821-gap3-b5-review-r1/synth.md#76c59e7939c1；handoffs/run_receipts/20260821T230000Z-gap3-b5-r1-fix-gate.log#da4e45960930

正文：[MINOR] 信心度=High。不影響行為／Gate rc；污染跨 agent 驗收敘事（摩擦八十七同類）。修法：stamp 前把 brief／synth／看板／commit 敘事之 event_samples 計數改為 **229**（或補測至宣稱數並更新 receipt）。不擋 stamp／UAT。

