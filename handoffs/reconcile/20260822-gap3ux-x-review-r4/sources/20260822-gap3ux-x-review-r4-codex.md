# GAP-3 事件型 UAT 缺口修補 SPEC — 對抗審 R4（CODEX）

task-id: 20260822-GAP3UX-X-REVIEW-R4  
family: codex  
brief: `handoffs/20260822-gap3ux-x-review-r4-brief.md`  
scope: review-only；未修改程式、SPEC、TODO、根 `HANDOFF.md`。

## CODEX-R4-P0-01

**斷言**: Task 7.2 的 enum count/set 閘不能證明控制項可選、可用值集合正確或使用者選值已傳入事件記錄；`control_kind` 的 `enum` 與 `accepted` 不同，且 disabled/hidden 選項可湊數通過。

**碼證**: `python3 handoffs/20260822-gap3ux-x-review-r4-dims.py --counts` → `control_kind enum_len=4 accepted_len=3`；SPEC Task 7.1–7.2（L783–813）只要求 UI 集合對 `contractEnum`，`decision_offset_bars` 只驗「有輸入控制項且非唯讀」；`frontend/src/lib/eventExport.ts:9-17,92-104` 仍沒有四個必要 opts，`frontend/src/app/search/page.tsx:522-527` 呼叫端沒有傳六維度。RECHECK：重跑上述 counts；讀 `nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '783,813p'`、`nl -ba frontend/src/lib/eventExport.ts | sed -n '9,17p;88,106p'`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；momentum/Analysis/contracts/event_import_contract.json#7111b2d7060e；frontend/src/lib/eventExport.ts#b2024ac8970f；frontend/src/app/search/page.tsx#4b967e3fb875

P0，信心度=High。實作者可放入 disabled 的 `platform_random_bars` 湊足四項，或讓非唯讀的 offset input 沒有綁定組裝函式；集合測試仍綠，但 payload/receipt 仍是預設值。這會把可見的事件語意與實際報酬數值分離。修法：明定可選集合是 `accepted`（或明定拒絕值的不可選呈現並從 oracle 排除），oracle 只計 enabled/可操作選項；六維度各做非預設值 UI→`buildEventContractRecords`→匯出記錄的 round-trip，並測 `decision_offset_bars=-1` fail-closed 與漏傳 opts mutation 必紅。

## CODEX-R4-P0-02

**斷言**: D-7 L3 要求「不進 split 但仍可產出事件研究表」，然而現有事件研究表入口必須取得 `EventSplitPlan`，SPEC 沒有 Task 建立不呼叫 `split_events` 的 event-study-only 路徑；照目前呼叫鏈實作會在「違反 L3」與「無法產表」間二選一。

**碼證**: SPEC Task 1.12（L434–453）同時要求 `split_events` 未被呼叫（L439）與事件研究表仍可產出（L441）。實碼 `momentum/Analysis/event_samples/pipeline.py:178-200` 的 `run()` 無條件呼叫 `split_events`；`:96-111` 的 `analyze_tables()` 將 `result.split_plan` 傳入表函式；`momentum/Analysis/event_samples/tables.py:88-100` 的 `event_forward_return_table` 參數為必填 `event_split_plan`，且 `:112-140` 直接讀 `.clusters`。RECHECK：`nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '434,453p'`；`nl -ba momentum/Analysis/event_samples/pipeline.py | sed -n '96,111p;178,205p'`；`nl -ba momentum/Analysis/event_samples/tables.py | sed -n '88,140p'`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；momentum/Analysis/event_samples/pipeline.py#db3d29667082；momentum/Analysis/event_samples/tables.py#e9856a0caa68

P0，信心度=High。若只在入口加 status 而仍走 `run()`，未可證明的 lookahead 仍進了 train/test split；若直接拒絕整條管線，則違反 SPEC 宣稱的事件研究表保留能力。修法：在 Task 1.12 增加明確的 event-study-only executor/契約，驗證它跳過 `split_events`、`ic_feed` 與訓練，但能以不依賴 split 的表格輸入產出報酬表；或改成明文取消「仍可產出」並同步移除該驗收。不得以空的假 split plan 冒充未執行切分。

## CODEX-R4-P1-03

**斷言**: G-2 仍不是可由不同實作者重現的 canonical serialization 契約；它只凍結 fixture/hash、exact return、NaN mask 與 PIT anchor，沒有定義輸出欄位白名單、鍵/列/horizon 排序、duplicate/invalid horizon、浮點/NaN/omission 表示或獨立 expected oracle。

**碼證**: SPEC §G（L260–273）只描述「固定 fixture＋固定 horizons」與三項比較；Task 2.2（L511–520）甚至要求 G-2 同時涵蓋 `filters` 與六維度鍵，卻沒有序列化規則；`event_forward_return_table` 實際輸出 `ret_entry`、`ret_label_anchor`、macro/micro/uniqueness/strata/common/receipts（`momentum/Analysis/event_samples/tables.py:131-180`），缺 bar 以 omission 反映 n（`:126-129`）。RECHECK：`nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '260,273p;511,520p'`；`nl -ba momentum/Analysis/event_samples/tables.py | sed -n '102,180p'`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；momentum/Analysis/event_samples/tables.py#e9856a0caa68

P1，信心度=High。合法實作可產生不同 hash：例如保留或省略缺 bar row、改變輸入 horizon 順序、改變 `NaN` 的 JSON 表示，或只比 aggregate 而漏掉局部 row 漂移。修法：在 §G/Task 4.2 寫死 canonical 欄位白名單、事件/列/horizon 排序、重複/非法 horizon policy、浮點與 NaN/omission 表示、`seed`/`n_boot` 及完整 stats 範圍；另以獨立手算 expected rows 驗 `[1,3,7]`、兩種 return 與尾端缺資料，而不是以被測函式自產 golden。

## CODEX-R4-P1-04

**斷言**: Phase 7 仍沒有規定事件批次的 t0 `time_range` 與 Feature Library run 的 manifest `time_range` 如何對證、顯示或 fail-closed；IC 分析可在特徵涵蓋範圍不包含事件日期時送出分析而沒有規格層警告/阻擋。

**碼證**: SPEC Phase 7（L751–848）只列 `/search`、`/data-preparation` 的六維度，未列 IC page 或 Feature Library coverage。`EventImportPicker.tsx:45-52` 的 `onPick` 只傳 `importId` 與 t0 timestamps；`ICConfigPanel.tsx:274-279` 只把兩者寫入 config；`ICAnalyzeRequest`（`api/models/ic_models.py:133-155`）沒有 batch metadata/coverage；`RunInfo`（`api/models/feature_factory_models.py:116-133`、`frontend/src/lib/types.ts:597-612`）沒有 `time_range`，但 `feature_reader.py:448-475` 的 manifest artifact 已有 `time_range` 可讀。RECHECK：`rg -n -A 8 'EventImportPicker|onPick|time_range' frontend/src/components/ic-analysis frontend/src/lib/types.ts api/models/feature_factory_models.py momentum/FeatureEngineering/feature_reader.py`；讀 `nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '751,848p'`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；frontend/src/components/ic-analysis/EventImportPicker.tsx#1cb1e1562456；frontend/src/components/ic-analysis/ICConfigPanel.tsx#f54774308d2f；api/models/ic_models.py#fbc974fb7fa4；api/models/feature_factory_models.py#fb5f998d5d4c；momentum/FeatureEngineering/feature_reader.py#f03b11fe7a8b

P1，信心度=High。這是事件型 IC 的資料正確性缺口，不是待 GAP-6 的大規模效能問題；等待分塊計算不會使日期錯配變安全。修法：補一條 IC/Feature Library 全棧 Task，讓事件批 detail/summary 傳出 t0 min/max 與必要契約設定、run list/detail 傳出 manifest `time_range`，在提交前以明確 overlap/containment policy 對證並在不涵蓋時 fail-closed 或顯示不可用；用小型跨日期 fixture 驗證，不得只測 picker 有選到批次。

## CODEX-R4-P1-05

**斷言**: SPEC 允許 `/search` 將 `scenario` 選成 A/B，但沒有定義 A/B label 的產生器/來源與機械 depth；現有組裝仍從 t0 的 `positive_case` 產生 `label`，scenario 只作 metadata，會形成「宣稱預測型、實際仍是 t0 標記」的語意漂移。

**碼證**: SPEC §D-7 表（L123–150）定義 A/B 事件在未來，且 lookahead 取 label 定義最遠未來根；Task 7.1（L783–797）卻把 A/B 與 C 一起列為可選 UI，沒有 label producer/來源約束。`frontend/src/lib/eventExport.ts:75-85` 對所有 scenario 都以 `positive_case` 判定 `label`、以 `future_{horizon}bar_return` 組 `label_value`，`:95` 才寫入 `scenario`；搜尋端沒有傳其他維度（`page.tsx:522-527`）。RECHECK：`nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '123,150p;783,797p'`；`nl -ba frontend/src/lib/eventExport.ts | sed -n '69,96p'`；加 scenario=A 且 future drawdown/複合條件之 fixture，檢查 label source 與 purge depth。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；frontend/src/lib/eventExport.ts#b2024ac8970f；frontend/src/app/search/page.tsx#4b967e3fb875；momentum/DataExtraction/case_search_engine.py#0064372813b6

P1，信心度=High。若使用者選 A/B，輸出契約可通過 enum validator，但 `label` 仍是 t0 `positive_case`；Task 7.3 的「由實際設定導出」只會揭露錯誤設定，不能修正語意。修法二選一：在 `/search` 尚無 A/B generator/label provenance 前禁止 A/B；或定義 A/B/two_stage 的 label source、最遠未來引用及其 provenance，將 `depth = max(宣告 window, 所有實際引用欄標註)` 寫入 Task/V-12，並加 A/B、two_stage 的 fail-closed/golden fixture。

## CODEX-R4-P1-06

**斷言**: Task 7.5 要依 `control_kind` 決定全體組是否可混算，但現有 `EventManifest.table` 沒有 `control_kind`，而 `event_forward_return_table` 的輸入也沒有原始事件表；SPEC 沒有規定把該欄帶到表格層的 wiring。

**碼證**: `momentum/Analysis/event_samples/dedupe.py:112-115` 的 manifest context 只 merge `event_id,symbol,timeframe,label,scenario,direction`，未包含 `control_kind`；`tables.py:88-100` 只收 `manifest, receipts, bars_by_tf, event_split_plan, table_config`。但 SPEC Task 7.5（L838–848）要求 `user_labeled_same_trigger` 與 `user_labeled_other` 產生不同全體組結果。RECHECK：`nl -ba momentum/Analysis/event_samples/dedupe.py | sed -n '101,115p'`；`nl -ba momentum/Analysis/event_samples/tables.py | sed -n '88,100p'`；測兩種 control kind 的同批 fixture，確認分組決策輸入確實來自契約欄而非預設值。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；momentum/Analysis/event_samples/dedupe.py#6f8d8418dbe0；momentum/Analysis/event_samples/tables.py#e9856a0caa68

P1，信心度=High。實作者若照既有資料流會只能把 `control_kind` 寫死、讀不到而當 `None`，或另建第二份事件索引；兩者都可能讓「不同觸發」被錯誤混算。修法：明定 control kind 的唯一傳遞點（manifest context 或明確 table input）、批內單值/混值規則與 `not_computed` schema，並以兩種 control kind 的 table golden 驗證正/反/全體 n 與狀態。

## CODEX-R4-P1-07

**斷言**: D-7 L1 的 registry 雖已成為 Task 1.10，但其接受條件仍以欄名及變體匹配為主，沒有把 CSV/Excel 欄位綁到可信的產生器 provenance；使用者可把實際引用 20 根未來資料的自訂欄改名成已登記的 `future_4bar_return`，使 L2 不觸發而低估 purge。

**碼證**: Task 1.10（L383–415）要求同時辨識契約蛇形、CSV 標題、大小寫與 `%` 後綴，並以 registry entry 解析；Task 1.11（L417–432）只對「無法由 registry 解析」的 future/custom 欄觸發宣告。實際搜尋輸出同時有 `future_1bar_max_drawdown`、`future72_max_drawdown`、`future_max_return` 等不同來源欄（`momentum/DataExtraction/case_search_engine.py:668-697`），其小時欄由 `periods_72h(timeframe)` 計算（`:1520-1534`），但規格沒有 producer digest/血統欄或 CSV 路徑信任邊界。RECHECK：建立一份欄名為 `future_4bar_return`、實際由 20 根計算的 CSV，確認它不能只因名稱命中 registry 就進 split；再測未知欄仍進 L2/L3。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；momentum/DataExtraction/case_search_engine.py#0064372813b6

P1，信心度=High。這不是要求系統判讀使用者思想，而是要求已知的搜尋產物與外部 CSV 分開信任：L1 可信任有 producer/manifest provenance 的系統欄，外部可改名欄不能只靠字串進入可切分路徑。修法：為 L1 增加 producer/schema/digest 綁定；外部上傳欄一律走可驗 provenance，否則 L2 宣告後仍依 L3 禁止 split/conditional IC，並加上述改名 mutation。

## R3 十八條 CLOSED／OPEN 對照

以下以本輪重讀 R3 產出與目前 900 行標的之對位判定；同一根因的 R4 延續以本檔 finding ID 交叉引用。

| R3 finding | 本輪狀態 | 證據摘要 |
|---|---|---|
| CODEX-R3-P0-01 | CLOSED | Task 1.10/1.11/1.12 與 Task 2.1b 已補 registry、未知欄宣告及 L3 驗收。 |
| CODEX-R3-P0-02 | CLOSED | Task 4.1b/7.3 已改為動態設定，移除 C-only 固定文案。 |
| CODEX-R3-P0-03 | OPEN | 仍受 CODEX-R4-P0-01 的 accepted/enabled/round-trip 缺口阻擋。 |
| CODEX-R3-P1-04 | OPEN | G-2 serialization 細節仍未釘，見 CODEX-R4-P1-03。 |
| CODEX-R3-P1-05 | OPEN | IC/Feature Library `time_range` 對證仍未入 Phase 7，見 CODEX-R4-P1-04。 |
| COMPOSER-R3-P1-01 | CLOSED | Task 2.1b 已改讀 registry 並涵蓋 drawdown/future72/登記欄。 |
| COMPOSER-R3-P1-02 | CLOSED | Task 1.10 已建立 registry 與缺標 validator。 |
| COMPOSER-R3-P1-03 | CLOSED | Task 4.1b 不再要求固定「t0 不看未來」文案。 |
| COMPOSER-R3-P1-04 | OPEN | `control_kind` enum/accepted 與 7.2 閘仍矛盾，見 CODEX-R4-P0-01。 |
| COMPOSER-R3-P2-01 | OPEN | IC 頁未揭露事件契約與 Feature Library coverage，見 CODEX-R4-P1-04。 |
| COMPOSER-R3-P2-02 | OPEN | G-2 canonical serialization 未定義，見 CODEX-R4-P1-03。 |
| COMPOSER-R3-P2-03 | OPEN | A/B 選擇後 label 來源未定義，見 CODEX-R4-P1-05。 |
| GROK-R3-P0-01 | OPEN | registry 有 Task 但外部欄位 name-spoof/producer provenance 未封，見 CODEX-R4-P1-07。 |
| GROK-R3-P0-02 | CLOSED | 4.1b 的 C-only 固定語意已移除。 |
| GROK-R3-P1-01 | CLOSED | Task 1.10 已明定 `lookahead_hours` 與 timeframe 換算，含 12h→6/1h→72 驗證。 |
| GROK-R3-P1-02 | OPEN | A/B 的 label source 與完整 depth oracle 仍未落成可執行契約，見 CODEX-R4-P1-05。 |
| GROK-R3-P1-03 | OPEN | 7.2 accepted/enabled/round-trip 仍未封，見 CODEX-R4-P0-01。 |
| GROK-R3-P1-04 | OPEN | G-2 oracle/serialization 仍未封，見 CODEX-R4-P1-03。 |

## §0 被當成事實的未驗證假設

- `fact-verified`：標的 SHA-256 `3bc04411cdf2…`、900 行；`python3 handoffs/20260822-gap3ux-x-review-r4-dims.py` 的六維度路徑與 `--counts` 輸出可重跑。
- `fact-verified`：三支 SPEC 機械閘重跑均 rc=0；facts script 整體 rc=0，但其 F-11 子命令實際報 `No such file or directory`，被 pipeline 的最後一段 `sed` 掩成 `[rc=0]`。
- `assumed／未充分驗證`：Phase 7 六維度是所有後端→前端→wiring 殘留的完整清單；本輪 IC page 與 Feature Library `time_range` 對證缺口反駁此假設（CODEX-R4-P1-04）。
- `assumed／未充分驗證`：L3 在不呼叫 split 的前提下仍能產事件研究表；目前 table API 與 pipeline 呼叫鏈沒有此路徑（CODEX-R4-P0-02）。
- `assumed／未充分驗證`：A/B scenario 與 C 可共用 search 匯出 label 來源；現有 `positive_case` 組裝與 §D-7 A/B 語意不一致（CODEX-R4-P1-05）。

## §1 十一類必查摘要

1. 矛盾/互斥：P0-01、P0-02、P1-05、P1-06。  
2. 端到端漏項：P0-01、P1-02、P1-04、P1-06。  
3. 不可測驗收：P0-01、P1-03、P1-05。  
4. quant/data correctness：P0-02、P1-05、P1-07。  
5. 過度工程：無新增 finding。  
6. OOM/並行：無新增 finding（#9b 規模本體不受理）。  
7. Cache correctness：無新增 finding。  
8. API/型別/相容：P0-01、P1-04、P1-06。  
9. 測試品質：P0-01、P1-03、P0-02。  
10. Agent 可執行性：P0-02、P1-03、P1-06。  
11. 必要性/短命工：Task 4.1b→7.3 的覆蓋已明寫，未另開 finding。

## Verdict

結論：需修訂後再定版；P0-01/P0-02 未封量化正確性與 L3 fail-closed，P1-03/P1-04/P1-05/P1-06/P1-07 仍有 canonical oracle、全棧 wiring、A/B 語意、表格控制欄與 provenance 缺口。標的不可 FROZEN。

ASSUMPTIONS_VERIFIED: 標的 hash/行數；facts script rc=0 及 F-11 masked error；六維度完整路徑/counts；Phase 7、D-7、G-2、IC picker、Feature Library manifest、event table/pipeline wiring 逐行對讀。
TESTS_RUN: `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md` → `3bc04411cdf2d1663626d0128e7d462c03f3228a9d1d3ee86f0cd3854dea58b9` rc=0；`bash handoffs/20260822-gap3ux-x-review-r4-facts.sh` → `rc_all=0`，但 F-11 stdout 為 `No such file or directory`；`python3 handoffs/20260822-gap3ux-x-review-r4-dims.py`/`--counts` → 六維度全找到；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_SPEC.md`、`bash scripts/spec_ruling_task_sync.sh docs/GAP3_EVENT_UX_SPEC.md`、`bash scripts/quant_standard_check.sh` → 各 rc=0；`bash scripts/completeness_check.sh --single handoffs/20260822-gap3ux-x-review-r4-codex.md --family codex` → `COMPLETENESS PASS(single)`，rc=0，7 個 canonical ID。
FAILURES_SEEN: facts receipt 與重跑輸出之 HEAD 行不同；F-11 命令失敗但被 facts script pipeline masking；均已在 findings 記錄，未修改其來源。
SCOPE_CHANGES: none；只新增本交件檔。
NUMERIC_OR_SCHEMA_IMPACT: 未修改產品數值或 schema；本報告指出待補的契約/golden/wiring 定義。
OUTPUT: `handoffs/20260822-gap3ux-x-review-r4-codex.md`
STATUS: DONE
