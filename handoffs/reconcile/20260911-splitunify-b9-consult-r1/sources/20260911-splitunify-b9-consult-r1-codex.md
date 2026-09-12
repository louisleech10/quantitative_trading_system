# SPLITUNIFY b9 偵察 consult R1 — CODEX

task-id: 20260911-SPLITUNIFY-B9-CONSULT-R1
family: codex
brief: `handoffs/20260911-SPLITUNIFY-B9-CONSULT-BRIEF.md`
scope: 只讀偵察；未改程式、SPEC、TODO、測試、golden、`data_cache/` 或根 `HANDOFF.md`

## §0 被當成事實的前提：逐一重判

| 前提 | 判定 | 證據 |
|---|---|---|
| D-001 六檔就是全部單鍵消費面 | **不成立** | `pipeline.py:760-762` 以 assignment row 數產出 API summary；`EventTablesPanel.tsx:356-362` 顯示該 summary；golden/freeze 仍只驗單 TF event-id 集合。 |
| `(event_id,timeframe)` 可不改 `EventSplitPlan` 的外部語意而落地 | **不成立** | 現行 `assignments`/`purged` 只產生 event-level 欄位；物化、baseline、pattern、tables 主要輸入也都是 `index=event_id`。混合 TF 可能一事件同時落 train/test，沒有既定 fold policy。 |
| 現行 fail-closed 已擋住多 TF 同批 | **不成立（跨 TF）** | `build_event_keys` 先 filter selected TF，實跑 2 事件×2 TF 只輸出 selected 的 2 列、靜默丟 2 列；直接把 pair rows 餵給 projection 的未來形狀則在 `event_id` guard raise。 |
| R13 reconcile 依賴戳記已核可 | **成立** | `handoffs/reconcile/20260911-splitunify-x-review-r13/synth.md` 現讀到 codex/grok/composer 三條 `APPROVED` stamp，且 `VERDICT: proceed`。 |

## CODEX-R1-P1-01

**斷言**: 現行 `receipts.per_tf → build_event_keys` 路徑沒有對「同一批含不同 timeframe」fail-closed；它會在 selected-timeframe filter 後靜默遺失未選 TF，故 D-001 所述的多 TF fail-closed 並未在實際 producer 邊界成立。

**碼證**: `split_projection.py:256-303` 先以 `per_tf["timeframe"] == selected_timeframe` 篩選，再對篩後資料做 duplicate check 與 merge。實跑探針 stdout：`input_per_tf_rows 4 output_rows 2 output_timeframes ['1h'] output_ids ['e1', 'e2']`、`UNSELECTED_ROWS_DROPPED 2`。同一檔未來 pair rows 直接進 derive 則 stdout：`ValueError: ... event_keys 之 event_id 重複 ['ev-mtf']...`，顯示目前是 producer 靜默丟列、projection 只接受 event-level 唯一性的兩段形狀。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#99bfddace904; docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f; docs/SPLITUNIFY_TODO.md#e44da6448b01

[BLOCKING] 信心度=High。失敗是使用者餵入多 TF 後只得到 selected TF 的分析，且沒有 receipt/summary 說明被丟掉的列；這不是可接受的「多 TF 已被擋下」。修法需二選一並寫入 b9 契約：在 pair-aware 實作完成前，producer 於 filter 前明確拒絕並列出未選 TF；或定義 pair-keyed event input 後一路完成 fold/consumer 遷移。不能只移除 duplicate guard。RECHECK: 重跑同一 producer probe，並加上「未選 TF 存在時必須 raise 或完整輸出 pair rows」的執行期斷言。

## CODEX-R1-P1-02

**斷言**: b9 若把 split 結果直接展開成每 `(event_id,timeframe)` 一列，會與目前 event-level 特徵／標籤／統計鏈衝突；若事件的不同 TF 落在不同 split，現有下游沒有可證明安全的單一事件歸屬，pipeline/API/frontend 還會把 pair row 數誤報成事件數。

**碼證**: `types.py:87-92` 的 `EventSplitPlan` 只有 DataFrame 容器；`split_projection.py:545-556` 產出 `assignments=[event_id,symbol,split_label]`、`purged=[event_id,reason]`，且 `:438-445` 以 event_id duplicate 為 hard guard。另一方面，`feature_materialization.py:93-132` 按 event_id 合併多 TF 取列並輸出 `index=event_id`（同名 feature 欄衝突在 `:22-31` 已 loud）；`baseline.py:105-110`、`pattern_bridge.py:122-127`、`tables.py:326,372-373` 都以 event_id 交集／索引。具體反例 stdout：`baseline_intersection ['e'] test_rows 2 reported_sample_count 1`；`pattern_lookup_type Series`、`pattern_boolean_type Series`；tables 的 duplicate reindex 為 `ValueError: cannot reindex on an axis with duplicate labels`。額外第七個消費面是 `pipeline.py:760-762` 直接 count assignment rows；前端 `EventTablesPanel.tsx:356-362` 把 `n_train/n_test/n_purged` 以未標註單位顯示，API `EventAnalyzeResponse.summary` 仍是 `Dict[str, Any]`。

**來源摘要**: momentum/Analysis/event_samples/types.py#8ba12e1b5204; momentum/Analysis/event_samples/split_projection.py#99bfddace904; momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2; momentum/Analysis/event_samples/baseline.py#38c7ec473653; momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2; momentum/Analysis/event_samples/tables.py#843ba7f68172; momentum/Analysis/event_samples/pipeline.py#55ca7327764f; api/models/event_import_models.py#82c83da611f5; frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

[BLOCKING] 信心度=High。若一事件的 1h cutoff 在 train、12h cutoff 在 test，pair assignments 不能直接餵給 event-level features；選 first/any 會靜默把混合時序當成一個 OOS 樣本，選 all/any 的實作也未在現行契約定義。若保留現有 event-level chain，保守修法是先以 `(event_id,timeframe)` 做內部邊界投影，再要求同一事件所有生效 TF 同側；混側、跨界或任一不可證者整事件 purge/拒絕並使用明確 reason，`EventSplitPlan` 對既有 consumer 仍維持 event-level。若產品要 per-TF sample，則必須另定 pair-index features/labels、assignments/purged schema、tables/bridge/model API，並把 summary 明確拆成 event counts 與 pair counts。RECHECK: 用一事件兩 TF 分別落 train/test 的 fixture，驗證不得產生未標示的 event-level OOS 值。

## CODEX-R1-P2-03

**斷言**: 同一經濟事件的不同 feature TF 應共享一個事件級 time cluster；把現有 event-level manifest／cluster／dedupe 直接展開成每 TF，會使去重與 cluster lookup 變成非唯一，或在改為每 TF 留樣時把同一事件當成多個獨立觀測。

**碼證**: `event_split.py:40-75` 的 `build_time_clusters` 依 manifest 的 `decision_at_ms` 每事件產一列；`tables.py:214,229,257` 以 event_id 對 receipts/clusters 做 scalar lookup；`dedupe.py:39-49,101-127` 是 event-level interval 去重，context merge 使用 `validate="one_to_one"`，`cluster_first` 依 cluster 只保留一筆。具體 pandas probe stdout：`dedupe_merge MergeError: Merge keys are not unique in right dataset; not a one-to-one merge`；duplicate cluster index 在 tables 的 scalar reindex 為 `ValueError: cannot reindex on an axis with duplicate labels`。

**來源摘要**: momentum/Analysis/event_samples/event_split.py#943d0721b059; momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2; momentum/Analysis/event_samples/tables.py#843ba7f68172

[MAJOR] 信心度=High。cluster 的統計單位是事件的 decision/label interval，不是描述該事件的 feature TF；按 TF 分簇會改變簇內樣本語意與 CI 分母，直接複製 cluster rows 也會使現有 scalar join 不可證。修法是 dedupe/manifest 先保留 event-level，所有同事件 TF fold 到同一 cluster；若另開 per-TF sample mode，建立獨立且有權重定義的 pair-level cluster relation，不覆寫既有 `clusters` 語意。RECHECK: 加入同 event 兩 TF、同 decision/label interval 的 fixture，逐值驗 cluster id、保留集與 cluster CI 的觀測單位。

## CODEX-R1-P2-04

**斷言**: 現有 splitunify golden 與 wiring tests 只覆蓋單一 timeframe、event_id 集合與 event-count 語意；b9 若新增 pair rows 或 event-level fold，沒有新增 multi-TF golden 就能讓單 TF 綠測試掩蓋多 TF 回歸。

**碼證**: `tests/golden/splitunify/splitunify_golden.json:3-41,43-108` 的 G1/G4/G5 以 event_id 陣列、per-symbol event count、單一 row fingerprint fixture 保存；`scripts/freeze_splitunify_golden.py:80-118` 固定 `timeframe="1h"` 的 12 筆 fixture；`test_splitunify_wiring.py:113-114` 仍斷言三態計數合計 `len(records)`。目前 `venv/bin/python scripts/freeze_splitunify_golden.py` stdout 為 `GOLDEN OK`，但這只證明單 TF。`EventTablesPanel.tsx` 及 `EventAnalyzeResponse.summary` 沒有 pair-count 型別／顯示單位。

**來源摘要**: tests/golden/splitunify/splitunify_golden.json#f270e007ca98; scripts/freeze_splitunify_golden.py#e331623163d2; tests/momentum/Analysis/test_splitunify_golden.py#006b7bd2d41e; tests/momentum/event_samples/test_splitunify_wiring.py#3d6a16a4d617; frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a; api/models/event_import_models.py#82c83da611f5

[MAJOR] 信心度=High。單 TF golden 本身應保留，作為既有 byte/集合回歸；b9 需新增真正含同 event 多 TF、同側、混側、跨界 purge 的 fixture，並選定輸出語意後固定 pair key 或 event fold 的逐值 oracle。若 summary 同時揭露兩種計數，需更新 API/TS 型別與 report integer-key inventory；不能只重凍既有 golden。RECHECK: 跑新增 multi-TF golden、pair uniqueness、混側 fail-closed 與 summary unit assertions；目前未實作，故未宣稱通過。

## 必答 1 — 消費面盤點

我先以 `rg -n "\.assignments|\.purged|\.clusters|EventSplitPlan|split_plan" momentum api frontend tests scripts docs` 與 `rg -n "build_event_keys|receipts\.per_tf|per_tf\.set_index|event_keys" ...` 掃描，再讀命中行。D-001 六個主鏈檔案之外的實質觸及面如下：

| 類別 | 路徑:行 | 結論 |
|---|---|---|
| pipeline summary | `momentum/Analysis/event_samples/pipeline.py:760-762` | assignment row count 會隨 schema 變成 pair count；需釘單位。 |
| API route/service/model | `api/routes/case.py:487-501`; `api/services/case_import_service.py:1626-1630`; `api/models/event_import_models.py:317-321` | route/service 透傳 summary，Pydantic summary 未細型別化；沒有 pair/event count contract。 |
| frontend | `frontend/src/components/ic-analysis/EventTablesPanel.tsx:356-362`; `frontend/src/lib/types.ts:3174-3200` | 直接顯示 n_train/test/purge，TS summary 是 `Record<string, unknown>`；單位漂移不會被型別捕捉。 |
| all-bars metadata | `momentum/Analysis/event_samples/all_bars_eval.py:253-270` | 主要取 common/cluster metadata；若 cluster 或 summary 單位改變，需維持揭露語意，但非直接 assignments join。 |
| golden/test tooling | `scripts/freeze_splitunify_golden.py:80-118`; `tests/momentum/Analysis/test_splitunify_golden.py:99-157`; `tests/momentum/event_samples/test_splitunify_wiring.py:113-114` | 現行僅單 TF event-level oracle。 |

六個既定 consumer 也逐一覆核：`feature_materialization.py:53,93-138` 已按 `(symbol,timeframe)` 物化、但輸出 event-level；`baseline.py:105-110` event-id intersection 會折疊 pair count；`pattern_bridge.py:122-127` 非唯一 assignments 取回 Series；`tables.py:214,229,326,372-373` 同時有 event-level scalar lookup 與 assignment/cluster reindex；`ic_feed.py:108-141` 先按 requested timeframe 過濾，合法 pair 唯一時目前安全；`dedupe.py:120,124-127` 是 event-level one-to-one／cluster-first。故六檔不是全部，但也不是六檔每一處都已是現行 bug。

## 必答 2 — 各消費面的失效分類與具體例

| 消費面 | 會報錯 | 可能靜默錯值／錯語意 |
|---|---|---|
| feature_materialization | 同名跨 TF feature 由 `_combined_columns` loud；缺 row 對證也 raise。 | 若只改 split plan 不改其 event-level output，混側 pair split 無法被一列 event feature 表達；錯誤 fold 若由 caller 任選會變成錯 OOS。 |
| baseline | 非有限 feature loud。 | `Index.intersection` 把同 event 的兩個 test pair 壓成一個 event，`n_test` 少算；混 train/test 沒有衝突策略。 |
| pattern_bridge | 非唯一 `lab_by_id[e]` 是 Series，布林判定歧義而 raise。 | 若後續以 first/any 修補，會在未揭露 TF 的情況下任選 split label。 |
| tables | duplicate assignment/cluster reindex 或 scalar `int(Series)` 可 raise。 | 先轉 set / first 會少算 pair，或將一事件的 cluster／symbol 綁到錯 TF。 |
| ic_feed | requested TF 缺列 raise；同一 pair 重複時 `.loc` 回 Series，轉 `int` 會 fail。 | 合法的不同 TF 因先 filter 不會互相污染；但它輸出仍是 requested timeframe 的 event-level timestamp map，不能宣稱已消費 composite split。 |
| dedupe | expanded event context 觸發 `validate="one_to_one"` MergeError。 | 若改成按 TF 留多列，同事件被當成多觀測，會改變 cluster/dedupe 統計單位。 |
| pipeline/API/frontend/golden | 未定義 schema 時通常不會在 response 型別層 raise。 | `n_*` 由 pair row 數取代事件數，UI 仍顯示為事件數；單 TF golden 仍綠而多 TF 未驗。 |

## 必答 3 — schema impact 與 golden shifts

推薦現行 event-level consumer chain 採「pair-keyed input、event-level fold」：

- `receipts.per_tf`：欄位形狀已有 `event_id,timeframe,feature_cutoff_ms,last_bar_open_ms,last_bar_close_ms,row_id`；不需新增欄，但要把 `(event_id,timeframe)` 唯一性變成明確 invariant，duplicate pair 必須在 producer 邊界拒絕。
- `EventSplitPlan.assignments`／`purged`：若 fold 後仍服務 event-level features，維持目前 event-level 欄位，新增 pair→event fold 的明確規則與 mixed-side purge reason；若產品選 per-TF sample，兩者都至少需帶 `timeframe` 並以 `(event_id,timeframe)` 唯一，不能只改 assignments 而留下 purged 單鍵。
- `EventSplitPlan.clusters`：維持一事件一列，cluster id/weight 是事件級；不要因每 TF assignments 而複製現有 cluster rows。per-TF mode 若真的需要，應是另一路 relation，不是改寫既有 `clusters`。
- golden：既有單 TF G1/G4/G5 保留不動；新增 multi-TF oracle，固定「同側 fold」及「混側 purge／拒絕」的輸出形狀。若選 per-TF assignment，G1 必須保存 pair key；若選 event fold，G1 仍 event_id，但必須額外保存每 pair 的 side/fold receipt。`g5_row_fingerprint` 只有在 feature universe／plan row identity 改變時才位移；`clusters_oracle` 依本報告 stance 維持 event-level。summary 若增加 pair counts，API/TS 與 integer-key inventory 需同步。

## 必答 4 — cluster folding stance

**結論：同一經濟事件的不同 feature timeframe 放在同一事件級 cluster；`cluster_first` 仍對事件去重，不按 TF 把同事件拆成獨立觀測。**

理由是 cluster 的現行來源是 decision time／label interval（`event_split.py:70-74`、`dedupe.py:39-49`），feature TF 只是描述同一事件的不同觀測來源；拆簇會偷偷放大觀測單位並破壞現有 cluster-CI 語意。若不同 TF 邊界落在不同 split，先做保守 event-level fold：所有生效 TF 同側才 assignment，混側進明確 purge/拒絕；若業務要把 TF 當獨立樣本，須另建 pair-level feature/label/cluster/weight contract。

## 必答 5 — 實跑多 TF 與 fail-closed 位置

**Probe A：實際 producer。** 以 `AlignmentReceipts` 放入 `e1/e2 × (1h,4h)` 四筆 `per_tf`，呼叫 `build_event_keys(..., selected_timeframe="1h")`。stdout：

```text
input_per_tf_rows 4 output_rows 2 output_timeframes ['1h'] output_ids ['e1', 'e2']
UNSELECTED_ROWS_DROPPED 2
```

因此目前跨 TF 同批不是 fail-closed，而是 producer 靜默丟掉未選 TF。這是合理上游邊界的失敗，應在 `build_event_keys` filter 前拒絕或進入明確 pair-aware executor。

**Probe B：把真正的兩 TF pair rows 直接交給目前 projection handoff。** `event_keys` 為同一 `ev-mtf` 的 `1h/12h` 兩列，呼叫 `derive_event_split_from_plans`。stdout：

```text
ValueError: derive_event_split_from_plans: event_keys 之 event_id 重複 ['ev-mtf']——集合相等吃不掉重複，會重複計數（fail-closed）
FAIL_CLOSED_STAGE: split_projection.derive_event_split_from_plans duplicate event_id guard
```

這個 guard 位於 split projection 內、早於任何下游 `validate=` surprise；但它證明的是現行 projection 只接受 event-level event_keys，不能被誤解成完整多 TF producer 已安全擋下。

## §1 必查 11 類

1. 矛盾／互斥：**有**，D-001「多 TF 維持 fail-closed」與 producer 實際靜默 filter 不一致；見 `CODEX-R1-P1-01`。
2. 漏項／端到端：**有**，pipeline/API/frontend/golden 未列入 pair row 語意；見 `CODEX-R1-P1-02`、`P2-04`。
3. 不可測驗收：**有**，尚未指定 pair key 或 event fold 的 exact output/golden；見 `CODEX-R1-P2-04`。
4. 可疑 quant 假設：**有**，把同經濟事件的 TF 當獨立 cluster 會改變統計觀測單位；見 `CODEX-R1-P2-03`。
5. 過度工程：無（本輪只提出最小的 pair→event fold 或完整 per-TF mode 二選一，未提出新架構）。
6. OOM／並行：無直接 finding；本輪未改物化或並行策略。
7. Cache 正確性：無直接 finding；本輪未改 cache key 或 artifact。
8. API／型別／相容：**有**，summary 未區分 event/pair count；見 `CODEX-R1-P1-02`。
9. 測試品質：**有**，現行 golden/wiring 只覆蓋單 TF；見 `CODEX-R1-P2-04`。
10. Agent 可執行性：**有**，b9 尚缺 mixed-side fold、purge reason 與 output schema 的可執行裁定；見 `CODEX-R1-P1-02`。
11. 必要性／短命工：無新增 finding；本輪沒有提出會被後續 Phase 刪除的實作 task，且未改 SPEC/TODO。

## §2 範本錨點與空殼檢查

已讀 D-001／TODO 的 C、G、P、R、N 相關段落。現有 G golden 有可執行的單 TF hash／集合檢查，但不覆蓋 SU-RESID-2 的 multi-TF key；N 殘留已明列「下游單鍵面須一併處理、未完成前維持 fail-closed」。本輪沒有把標題或表頭當成驗證；新的 b9 驗收仍需補 pair fixture、mixed-side negative case 與 summary unit assertion。

## VERIFY receipts

- `venv/bin/pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_pipeline.py` → `84 passed in 1.03s`。
- `venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`；此為單 TF baseline，不是 multi-TF 覆核。
- Producer multi-TF probe → `input_per_tf_rows 4 ... output_rows 2 ... UNSELECTED_ROWS_DROPPED 2`。
- Projection pair-row probe → `ValueError ... event_keys 之 event_id 重複 ['ev-mtf'] ... FAIL_CLOSED_STAGE ...`。
- Consumer semantics probe → baseline `reported_sample_count 1`（兩個 pair rows）；pattern lookup/boolean 為 `Series`；tables duplicate reindex `ValueError`；dedupe duplicate context merge `MergeError`。

VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01,CODEX-R1-P1-02
CLOSED:

ASSUMPTIONS_VERIFIED: R13 三家 stamp APPROVED；六個主鏈與 pipeline/API/frontend/golden 額外消費面已掃描；producer 多 TF 靜默丟列與 projection duplicate guard 均實跑；既有 splitunify focused tests 84 passed、單 TF golden GOLDEN OK。
TESTS_RUN: `venv/bin/pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_pipeline.py` → 84 passed；`venv/bin/python scripts/freeze_splitunify_golden.py` → GOLDEN OK；兩個多 TF／consumer semantics Python probes → stdout 如上；completeness 交件檢查於寫檔後執行。
FAILURES_SEEN: producer probe 實際發現跨 TF 未選列靜默遺失；projection pair-row probe 於 event_id guard fail-closed；兩者均保留為本輪 finding，沒有改碼修正。
SCOPE_CHANGES: none；只新增 `handoffs/20260911-splitunify-b9-consult-r1-codex.md`，未越界修改。
NUMERIC_OR_SCHEMA_IMPACT: 本輪未修改產品數值或 schema；報告提出的 assignments/purged/clusters 與 golden 影響是待裁定的設計 impact，不是已落地變更。
OUTPUT_PATH: `handoffs/20260911-splitunify-b9-consult-r1-codex.md`

STATUS: DONE
