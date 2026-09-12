# SPLITUNIFY_SPEC.md 延伸 D-002

BASE: docs/SPLITUNIFY_SPEC.md @ 1be5be3f
PREDECESSOR: docs/SPLITUNIFY_SPEC.D-001.md
改什麼: 落實 `docs/SPLITUNIFY_TODO.md` §E 之殘留 `SU-RESID-2`（多 feature TF 之複合鍵），並**更正 D-001 兩處與實況不符的陳述**。
為什麼: `handoffs/reconcile/20260911-splitunify-b9-consult-r1/synth.md`（四家偵察 18 條／六群）＋ `handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md`（三家找碴 15 條／七群，**三家全數 blocked、全部採納**；本版為其修訂版）。

**類別判定＝D 延伸**（依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1）。
理由：`SU-RESID-2` 於 BASE 與 D-001 皆已具名登記為殘留並預告「排於下一批」；本延伸即該預告之落地，**不推翻** BASE 任何設計意圖。

## 🔴 明確不在本延伸範圍

`D1`（事件掃描端「恆走」event-study-only）之條件化仍須走 **R 重開**；`R-5` 待其完成後另行處理。本延伸**不動** `row_index`／`row_index_local` 之座標語意（D-001-C2 第 4 點全文繼續有效）。

## 觸及面宣告

新增: `D-002-C0`（術語）、`D-002-C3`（同側約束）、`D-002-C4`（對 D-001 之更正）、`D-002-C5`（單鍵消費面）、`D-002-C6`（量詞分離）、`Task 9.1`～`Task 9.5`
覆寫: D-001 第 11 行與第 189 行之 `SU-RESID-2` 相關句（見 `D-002-C4`）
依賴: `## §V 驗證策略與邊界測試目錄`；`## §G Golden / Baseline`
不觸: D-001 之 `D-001-C1`／`D-001-C2`／`Task 8.1`～`8.3`

## 內容

### D-002-C0 術語：兩種 timeframe 必須分名

<!-- OBLIGATIONS-BEGIN id=D-002-C0 -->

**(0.1) 分名義務**：本 epic 既有的 `timeframe` 一詞承載**兩種不同語意**，本延伸起**一律分名**，全檔與實作不得再用裸 `timeframe`：

**(0.2) 觸發 TF 之定義**：`trigger_timeframe`＝**事件觸發**所在的 TF。它是 `canonical_event_id(symbol, timeframe, t0)` 的第二個引數，決定 `event_id` 本身；同一時刻在不同 trigger TF 下是**不同事件**。

**(0.3) 特徵 TF 之定義**：`feature_timeframe`＝**分析特徵**所在的 TF，即 `per_tf.timeframe`（`receipts.per_tf` 之 `timeframe` 欄）與 `selected_timeframe` 所指者。同一事件可有多個 feature TF，這正是 `SU-RESID-2` 要支援的維度。

**(0.4) 複合鍵之維度**：`SU-RESID-2` 之複合鍵為 `(event_id, feature_timeframe)`，**不是** `(event_id, trigger_timeframe)`——後者不存在多列問題（trigger TF 已編進 `event_id`）。

**(0.5) 用語適用範圍**：凡本延伸提及「多 TF」「同簇」「同側」「per_tf 多列」，一律指 **feature TF**。

**(0.6) 既有欄位保留、新增欄位分名**：**既有** wire 欄位（含 `per_tf.timeframe`、契約檔既有鍵）**一律原樣保留**，不改名、不加 alias——改名會動到已凍結之契約與 golden。**新增**之欄位／summary 鍵／API 欄名則須逐字採用 (0.2)／(0.3) 之名稱，禁用裸 `timeframe`。兩者界線以「本延伸是否新建該欄」判定。

<!-- OBLIGATIONS-END -->

### D-002-C3 同事件多 feature TF 必須落在同一 split 側

<!-- OBLIGATIONS-BEGIN id=D-002-C3 -->

**(3.1) 可比時點之定義（事件級錨定）**：事件之 split 側**一律由事件級的 `decision_at_ms` 決定**，**不**由各 feature TF 的 `feature_cutoff_ms` 各自判定。理由：現行資料契約只要求各 feature TF 之 `feature_cutoff_ms <= decision_at_ms`，**未**要求不同 feature TF 之 cutoff 相同或錨定同一時刻——若讓各 TF 各自判側，合法事件會天然散落兩側而被誤殺。各 feature TF 之 cutoff 僅用於**取特徵值**，不參與側別判定。⇒ 同一 `event_id` 之**所有** feature TF 列**恆**落在同一 split 側（同為 train 或同為 test），此為**結構性保證**而非須驗證之約束，誤 purge 之風險由此消除。

**(3.2) 異側之處置＝fail-closed，不是 purge**：(3.1) 落地後，同一事件異側**不可能由合法資料產生**——一旦出現即代表實作退回了「各 feature TF 自行判側」⇒ 投影端須**擲出** `AlignmentViolationError`，🔴 **不得**靜默取一側，亦**不得**當成資料問題 purge（purge 會把實作缺陷偽裝成正常的樣本流失）。**本條為 R2 裁決之修訂**：R2 定「異側整事件 purged、沿用 `interval_crosses_split_boundary` 字面」，其前提是「可比時點未定義、異側屬合法」；(3.1) 消除該前提後，異側改判為缺陷。既有 `interval_crosses_split_boundary` **維持原義**（標籤區間跨越 split 邊界，事件級，與 feature TF 無關），單一真相源仍為事件匯入契約之 `split_purge_reasons`——本延伸**不新增亦不改寫** reason 字面。

**(3.3) 同簇不等於同側**：🔴 **不得以「同簇」代替本條**——同簇只保證它們在統計上被視為相關，**不保證同側**。異側時，仍以事件為單位聚合的下游消費者（`baseline`／`pattern_bridge`／IC feed）會把 train 側的特徵與 test 側的標籤組在一起，**組成非法 OOS 樣本**——這正是本 epic 從頭要擋的洩漏形態，且**完全靜默**。

**(3.4) 檢查落點**：(3.1)–(3.3) 之檢查必須在**投影端**（`derive_event_split_from_plans`）完成，不得下放給各消費端自行判斷。

<!-- OBLIGATIONS-END -->

### D-002-C4 對 D-001 的更正

<!-- OBLIGATIONS-BEGIN id=D-002-C4 -->

**(4.1) 應更正之句**：D-001 第 11 行與第 189 行之句「未完成前多 TF 同批維持 fail-closed」**與實況不符**，以 (4.2) 取代。

**(4.2) 現行實況**：現行 `build_event_keys` 擋下的是**兩種**情形：①選定 feature TF 下同一事件有多列 `per_tf`；②選定 feature TF 下事件缺 `feature_cutoff_ms`。它**不擋**「同一批含多個 feature TF」——未被 `selected_timeframe` 選中的列被**靜默丟棄**，無例外、無警告、report 亦不記。

**(4.3) 清單不完整**：D-001 第 189 行所列之「下游單鍵面六處」**不是完整清單**；觸及面以本檔 (5.x) 為準。

**(4.4) 更正範圍**：(4.1)–(4.3) **不改變** D-001 其餘任何義務；D-001 之 (4.1)–(4.18) 與 `M-SU-D1-01`～`23` 全部繼續有效。

<!-- OBLIGATIONS-END -->

### D-002-C5 單鍵消費面（16 處，分四層）

<!-- OBLIGATIONS-BEGIN id=D-002-C5 -->

**(5.1) 清單效力**：本清單取代 D-001 第 189 行之六處。來源＝四家偵察合併盤點 ＋ 三家找碴補列。實作前須再掃一次並更新本表（見 §N 誠實邊界）。

**(5.2) 第一層｜producer 與投影本體**：`split_projection.build_event_keys`（選定 feature TF 後要求 `event_id` 唯一、`merge validate="1:1"`）；`split_projection` 之 `assignments`／`purged` 組裝（僅以 `event_id` 標識）；`event_split.build_time_clusters`（一 manifest 列對一 `event_id` 列）。

**(5.3) 第二層｜表格鏈（D-001 原列六處）**：`feature_materialization` 之 `merge validate="many_to_one"`（**會報錯**）與 `groupby("event_id")+row_vals.update` 折疊（🔴 **靜默**，真正的折疊點）與輸出 `set_index("event_id")`（**靜默**只留最後一列）；`baseline`（繼承上游唯一索引）；`pattern_bridge` 之 `set_index("event_id")["split_label"]`（**靜默**取到 Series）；`tables` 兩處 `set_index`（**靜默**）；`ic_feed` 兩處 `set_index` ＋ `.loc[keep["event_id"]]`（**靜默**）；`dedupe` 之 `merge validate="one_to_one"`（**會報錯**）與 `cluster_first` 保留集（**靜默**折掉 TF）。

**(5.4) 第三層｜偵察補列**：`counterexample_classifier` 之 `.loc[eid]`（**靜默**綁錯 receipt 列）；`candidate_ledger` 雙 `set_index` ＋ `.loc[eid]`（**靜默**）；`ic_feed.event_context_from_windows` survivor 六鍵（以排序後 `event_id` 列雜湊）；`frontend/src/lib/types.ts` batch_facts ／ `frontend/src/app/search/page.tsx` 之 `byEventId` Map（**靜默**後者覆蓋前者）；`tests/golden/splitunify/{splitunify_golden,clusters_oracle}.json`（以 `event_id` 清單比對，多 TF 因 set 去重而看不出差異）。

**(5.5) 第四層｜記帳與報告鏈**：🔴 凡直接讀取或顯示 split count 者——`pipeline` 產出之 `n_train`／`n_test`／`n_purged`、其 API 模型、前端事件批面板、以及既有 wiring 測試中以 `dict(zip(event_id, …))` 建映射之處——具體為 `test_splitunify_wiring.py:103-104`（同 `event_id` 多 feature TF 時**後者覆蓋前者**）。

<!-- OBLIGATIONS-END -->

### D-002-C6 事件數與列數是兩個量

<!-- OBLIGATIONS-BEGIN id=D-002-C6 -->

**(6.1) 三個量之定義**：複合鍵落地後，以下三個量**各自定義、不得互相代用**：`n_events`＝去重後之 `event_id` 數；`n_event_tf_rows`＝`(event_id, feature_timeframe)` 列數；既有之 `n_train`／`n_test`／`n_purged`。

**(6.2) 三量之粒度逐消費者定義**：🔴 **不得一刀切**。`split_projection` 之 `summary` 與報告分母、前端顯示、既有 wiring 斷言之 `n_train`／`n_test`／`n_purged` 維持**事件數**（`n_events` 粒度）語意；但 `baseline` 之 `n_test` 語意為**實際模型輸入樣本數**（複合鍵後即 `(event_id, feature_timeframe)` 列數），**不得**改判為事件數。實作須逐消費者標明其粒度，列數另以 `n_event_tf_rows_train` 等新名承載。

**(6.3) 派工義務**：任一消費面把列數當事件數顯示或斷言即為缺陷；`Task 9.4` 須逐處指派修改，**不得**只在本節寫義務而不派工。

<!-- OBLIGATIONS-END -->

### §RISK 風險分級

- **大小**：大（命中 (a)(b)(d)）。
- **命中高風險原則**：(a) 多 TF 記帳影響 IC 樣本數與統計量；(b) 觸及 16 處共用消費面含前端與 golden；(d) 錯誤折疊或異側放行會直接改變 ML／回測輸入之樣本構成。
- **RISK-HIT: a,b,d**
- 命中 (a)(d) ⇒ §G Golden 必填、adversarial review 必跑。

### §A 假設與待使用者確認

- FACT-RECEIPT: `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → 印出 `A NO_RAISE 產出 2 列` / `B RAISED …多列 per_tf` / `C NO_RAISE 產出 2 列` / `D RAISED …缺 cutoff`（主委 實跑 2026-09-12）
- FACT-RECEIPT: codex 獨立 Probe A → 印出 `input_per_tf_rows 4 output_rows 2 output_timeframes ['1h'] UNSELECTED_ROWS_DROPPED 2`（codex 實跑 2026-09-12）
- FACT-RECEIPT: `grep -n "canonicalEventId" frontend/src/lib/eventId.ts` → 印出 `export function canonicalEventId(symbol, timeframe, t0)`，證實 `event_id` 已含 **trigger** TF（主委 實跑 2026-09-12）
- **待確認：無**
- **已確認結果**：`2026-09-12 使用者裁定——主委自產不進委員收斂之 roster 與 sources，僅以敘述引用`

### §C 約束

- 解耦 7 條不變；本延伸**不得**讓 `momentum/` 反向依賴 `api/`。
- 16 處消費面中，標記**靜默**者驗收不得只看「有沒有報錯」，須斷言取到的**值**正確。
- `D-002-C6` 之量詞分離為硬約束；`D-002-C3` 之同側約束為洩漏紅線。

### §G Golden / Baseline

- **必填理由**：命中 (a)(d)。
- **凍結時機**：Task 9.1 動工前，以現行單 TF fixture 重跑 `scripts/freeze_splitunify_golden.py` 取得 baseline（`GOLDEN OK` 為前置條件）。
- 🔴 **兩件事必須分開敘明**：
  - **(G-1)** 「複合鍵本身不改指紋 payload」為真——`build_row_time_fingerprint` 之 payload 為 `[position, feature_ts_ms, symbol, base_universe_hash]`，不含任何 TF 欄，故 `g5` **不因複合鍵而位移**。
  - **(G-2)** 但「把 fixture 改為兩標的交錯」（順道處置 `M-SU-D1-23`）**會**移動 `g5` 的 positions／feature_ts_ms／sha——那是 **fixture 變更**造成的，與 (G-1) 不衝突。⇒ 交錯 fixture 須**新增為平行組**並重凍其 `g5`，**單標的舊值保留為回歸錨、不得刪除**。
- **(G-3)** 多 TF 平行組中，`feature_timeframe` 為**parent key**（分組鍵），**不進** `g5` 之 fingerprint payload；`g1_membership`／`g3b_oracle` 須擴維為 `(event_id, feature_timeframe)` 或新增 `*_multi_tf` 平行組。
- **通過條件**：單 TF 路徑逐值不變（exact）；多 TF 路徑以新增之平行組比對。任一單 TF 舊值位移即 FAIL。

### §P Phase 與依賴

#### Phase 9A — 揭露先行（依賴：無）

**Task 9.1 — 丟棄列數之完整資料流契約**
- 目標：在複合鍵落地**之前**，先消除「靜默丟棄」之誠實性缺陷，且必須讓**終端使用者**看得到。
- **返回形狀**（契約，缺一不可）：`build_event_keys` 回傳之 keyed 事件表外，另回傳
  `discarded: Dict[str, int]`——鍵為被丟棄之 `feature_timeframe`、值為列數；無丟棄時為 `{}`（**不得**省略或回 `None`）。
- **跨邊界傳遞**：`_derive_single_symbol` 與 per-symbol 分派器須將其原樣寫入
  `EventSplitPlan.summary["discarded_rows_by_feature_tf"]`（🔴 依 `D-002-C0` (0.6)，新增鍵名不得含裸 `timeframe`）；多 symbol 時逐 symbol 相加。
- **API 與前端揭露落點（逐處指名，缺任一層即視為 9A 未完成）**：
  - **route**：`api/routes/case.py:487` `POST /case/events/{import_id}/analyze`；**service**：`api/services/case_import_service.py`（`get_event_import_service()`）。
  - **response field**：`api/models/event_import_models.py:306-308` 之 `EventAnalyzeResponse.summary`。🔴 其型別為 `Dict[str, Any]`（前端對應 `frontend/src/lib/types.ts:3176` 之 `Record<string, unknown>`）⇒ **新鍵會自動穿過、不會被型別擋下，也因此完全沒有型別保證**：驗收**不得**依賴 pydantic 或 TS 型別，須在 route 層寫**明列鍵名**之契約測試。
  - **前端顯示**：`frontend/src/components/ic-analysis/EventTablesPanel.tsx:347` 取 `resp.summary`、`:361` 為現行 `train／test／purge` 顯示行；丟棄列數須顯示於此，文案「本次分析只用了 `<selected>`，丟棄 `<tf>: <n>` 列」。
- **獨立回退之判準**：移除上述三層後系統行為須與 9A 前逐值相同（無其他消費者依賴該欄）——此為可證偽斷言，須有測試。
- 不可做：不得以揭露取代複合鍵；不得在丟棄時 raise（會擋掉目前合法的單 feature TF 用法）。

#### Phase 9B — 複合鍵主體（依賴：Phase 9A）

**Task 9.2 — producer 停止單選，輸出全量 keyed rows**
- 🔴 **本 Task 是第 9 批的核心；沒有它，下游全部改完 `SU-RESID-2` 仍不會被解決**（只加欄位而 producer 照舊單選，丟棄行為原封不動）。
- 檔案：`split_projection.build_event_keys` **與其唯一生產 caller** `pipeline.py:747` ——現行該處逐字為 `build_event_keys(receipts, selected_timeframe=str(selected_timeframe))`（**必傳**，且 `str()` 強制轉型，連 `None` 都會變成字面 `"None"`），以及該參數之設定來源 `config.split` 一路上溯之 `selected_timeframe`。
- 🔴 **只改被呼叫端不算完成**：若 caller 仍必傳 `selected_timeframe`，生產路徑的靜默丟棄原封不動——此為本 Task 的驗收重點。
- 改法：`build_event_keys` 之 `selected_timeframe` 由**必填改為可選**（預設 `None` ＝ 全量），輸出**全量** `(event_id, feature_timeframe)` keyed rows；caller 改為不傳（或明示傳 `None`），🔴 並**一併移除 `str()` 強制轉型**——留著它會把 `None` 轉成字面 `"None"`，被下游當成一個叫 `None` 的 feature TF，產出空表而非全量（改了 producer 卻沒改這裡＝本 Task 白做）；`selected_timeframe` 僅在呼叫端明確要求單一 TF 時作為**可選**過濾器，且過濾掉的列數仍須依 `Task 9.1` 揭露。
- 不可做：不得保留「預設只取一個 TF」之行為；不得在 producer 內靜默丟列。

**Task 9.2a — schema 加 `feature_timeframe`**
- 檔案：`split_projection` 之 `assignments`／`purged`。
- 改法：兩表各加 `feature_timeframe` 欄（逐字採 `D-002-C0` (0.3) 之名）；`receipts.per_tf` **不改形狀**。
- 🔴 **`event_split.build_time_clusters` 之 `clusters` 不加該欄、維持事件級粒度**（定案，二選一取此）：簇由 `label_start_ms`／`label_end_ms` 之 interval 決定，與 feature TF 無關；若把簇複製成多列，`w=1/n` 權重、簇計數與 golden 語意全部失去定義。同事件多 feature TF 之簇歸屬**共用同一列**。
- 🔴 **既有兩道重複 guard 之判準與執行先後**（定案，不得移除、不得放寬為警告）：
  - `split_projection.py:284-289`（選定 feature TF 下同一 `event_id` 有多列 `per_tf` 即 raise）與 `split_projection.py:441-444`（組裝後 `event_id` 重複即 fail-closed）**一律改判準為複合鍵唯一**：`(event_id, feature_timeframe)` 重複才 raise；同事件不同 feature TF 為**合法**，不得再以 `event_id` 重複為由擋下。
  - **先後**：複合鍵唯一 guard 是**結構性前置**，須在 `D-002-C3` 之同側檢查**之前**執行——鍵尚不唯一時，「同一事件的各列是否同側」無從定義，先跑同側檢查會把重複鍵誤報成異側缺陷。
  - 兩道 guard 之**錯誤型別維持現狀**（不得為了統一而改型別，前端與既有測試有依賴）。
- summary 依 `D-002-C6` 同時提供 `n_events` 與 `n_event_tf_rows`。

**Task 9.3 — 16 處消費面逐處列名改法**
- 🔴 **不得**用「凡 `set_index("event_id")` 一律改」這種形狀規則——那既會誤改本就一事件一列的 event-level 表，又會漏掉真正折疊資料的 `groupby(...)+update`。**逐處列名，每處註明粒度與改法**：
  - `feature_materialization`：折疊點在 `groupby("event_id")+row_vals.update`，改為 `groupby(["event_id","feature_timeframe"])`；輸出索引改 MultiIndex 並**斷言索引唯一**；`merge validate` 隨粒度調整。
  - `pattern_bridge`／`tables`／`ic_feed`／`counterexample_classifier`／`candidate_ledger`：`.loc[eid]` 之 scalar lookup 改為複合鍵 lookup，**保留** event-level 表原粒度不動。
  - `dedupe`：`cluster_first` 保留集改 `(event_id, feature_timeframe)` 粒度；context merge 鍵隨之調整。
  - `baseline`：隨上游索引變更同步；本身不新增粒度。
  - **event-level 表（`receipts.event_level`、manifest）粒度不變**——不得一併改為複合鍵。
- 🔴 **cluster 語意**：時間簇仍按**事件級 interval** 合併，同一事件之不同 feature TF **同簇**；但同簇**不等於**同側，同側約束見 `D-002-C3`。

**Task 9.4 — 記帳與報告鏈**（`D-002-C6`；三家全中之缺口）
- 檔案：`pipeline` 之 count 產出、對應 API 模型、前端事件批面板、既有 wiring 測試之 `dict(zip(...))` 映射。
- 改法：依 (6.2) 將 `n_train`／`n_test`／`n_purged` 明確定為事件數；新增列數欄；`dict(zip(...))` 改為複合鍵映射。

**Task 9.5 — golden 與前端**
- 檔案：`tests/golden/splitunify/*`；**平行組之生成入口＝`scripts/freeze_splitunify_golden.py`**（具體為 `_plans()`／`_event_keys()`／`_build_actual()` 三處 fixture 構造函式，寫檔在 `main()`）；`frontend/src/lib/types.ts`；`frontend/src/app/search/page.tsx`。
- 改法：golden 依 §G (G-2)(G-3) 擴維並新增交錯平行組——`_event_keys()` 產出多 feature TF 列、`_build_actual()` 以**新鍵**承載平行組，`main()` 寫檔時**只增鍵不覆蓋**單標的舊鍵（舊鍵即 §G 之回歸錨）；前端 `byEventId` Map 鍵改複合鍵。

### §V 驗證策略與邊界測試目錄

- `Task 9.1`：`ASSERT build_event_keys WHEN per_tf 含 1h 與 4h 而 selected=1h THEN discarded == {"4h": 2}`（summary 鍵為 `discarded_rows_by_feature_tf`）；`ASSERT WHEN 單一 feature TF THEN discarded == {}`；`ASSERT summary／API 回應／前端型別三層皆帶該欄`；`ASSERT 移除該欄後行為與 9A 前逐值相同`（獨立回退之可證偽斷言）。
- `Task 9.2`：`ASSERT assignments THEN 欄含 feature_timeframe 且 (event_id, feature_timeframe) 唯一`。
- `D-002-C3`（成對，缺一即無鑑別力）：`ASSERT WHEN 同 event 之 1h 與 4h 之 feature_cutoff_ms 不同且皆 <= decision_at_ms THEN 兩列同側且皆不 purged`（(3.1) 結構性保證之正例）；`ASSERT WHEN 直接構造 assignments 使同一 event_id 之兩列異側 THEN raise AlignmentViolationError`（(3.2) 之反例；須一併驗其**不是**靜默取一側、**不是**改判 purged）。
- `D-002-C3` purge 面：`ASSERT purged THEN (event_id, feature_timeframe) 唯一`（purge 路徑同樣不得折疊列）；`ASSERT summary THEN 帶 n_event_tf_rows_purged 且其值 == purged 列數`（與事件級 `n_purged` 並存、不得互相代用）。
- `D-002-C6`：`ASSERT summary THEN n_events 與 n_event_tf_rows 並存`；`ASSERT n_train+n_test+n_purged == n_events`（事件數守恆，非列數）。
- `Task 9.3`：**逐處**各一條「改壞就要變紅」測試；🔴 靜默面須斷言取到的**值**正確，不得只斷言「不報錯」。
- `Task 9.5`：`ASSERT golden WHEN 單 TF fixture THEN 舊值逐值不變`；`ASSERT 交錯平行組之 g5 與單標的組不同且各自穩定`。
**mutation 目錄**（🔴 逐處對應，不得以單一 generic mutant 冒充；每列皆須有**完整 ID** 與**應紅之測試**）

| ID | 改壞什麼 | 應紅之測試 |
|---|---|---|
| `M-SU-D2-01` | 9A 之 `discarded` 不寫入 summary | `Task 9.1` 之 summary 鍵斷言 |
| `M-SU-D2-02` | `discarded` 寫入 summary 但不傳到 API 回應 | API 事件切分回應契約測試 |
| `M-SU-D2-03` | API 帶了但前端不顯示 | 前端事件批面板揭露測試 |
| `M-SU-D2-04` | `feature_materialization` 只改 `set_index` 輸出索引、不改 `groupby` 折疊 | 多 feature TF 物化**值**斷言（非「有無報錯」） |
| `M-SU-D2-05` | `pattern_bridge` lookup 退回單鍵 | `pattern_bridge` 之 split_label 值斷言 |
| `M-SU-D2-06` | `tables` lookup 退回單鍵 | `tables` 之簇 lookup 值斷言 |
| `M-SU-D2-07` | `ic_feed` lookup 退回單鍵 | `ic_feed` 之逐列值斷言 |
| `M-SU-D2-08` | `counterexample_classifier` 退回單鍵 | 分類結果與 receipt 列之綁定測試 |
| `M-SU-D2-09` | `candidate_ledger` 退回單鍵 | 帳本列綁定測試 |
| `M-SU-D2-10` | `dedupe` 保留集退回 `dedupe_cluster_id` 粒度 | `dedupe` 保留集粒度測試 |
| `M-SU-D2-11` | 前端 `byEventId` Map 鍵退回 `event_id` | 前端同鍵覆蓋測試 |
| `M-SU-D2-12` | wiring 測試之 `dict(zip(...))` 保持單鍵 | `test_splitunify_wiring.py` 多 feature TF 案例 |
| `M-SU-D2-13` | `n_train` 改取列數 | `D-002-C6` 之事件數守恆斷言 |
| `M-SU-D2-14` | `D-002-C3` 同側檢查整個移除（異側放行） | (3.2) 異側 `AlignmentViolationError` fail-closed 斷言 |
| `M-SU-D2-15` | 同側檢查改為「取第一側」或改判 purged 而非 raise | 同上（須指名 raise，不得取一側、不得吞成 purge） |
| `M-SU-D2-16` | golden 仍以 `event_id` 清單比對 | golden 多 feature TF 平行組 |
| `M-SU-D2-17` | 交錯平行組未新增而直接覆蓋單標的 g5 | golden 單標的回歸錨逐值不變 |
| `M-SU-D2-18` | event-level 表被一併改為複合鍵（過度涵蓋之反向 mutation） | event-level 粒度不變測試 |
| `M-SU-D2-19` | `ic_feed.event_context_from_windows` 之 survivor 六鍵雜湊**被改成含 feature TF**（survivor 本即事件級，改了才是缺陷） | survivor 雜湊維持事件級之測試 |
| `M-SU-D2-20` | producer 保留 `selected_timeframe` 之預設單選 | `Task 9.2` 全量 keyed rows 測試 |

### §R 回退

單 TF 舊值保留為回歸錨；Phase 9A 可獨立回退（移除三層揭露即可，由 §V 之可證偽斷言保證）。Phase 9B 回退需連同 16 處消費面一併還原，故 9B 須在單一批次內完成，**不得部分上線**。

### §N N/A 登記與殘留

- `SU-RESID-2` — **本延伸落實**，理由類別由 `needs-research` 解除。🔴 **狀態 SoT 同步時點**：`docs/SPLITUNIFY_TODO.md` §E 該列現仍為 `needs-research`、理由仍寫「每事件恰一個 selected per_tf row」；須於**本延伸三家戳記通過後、`Task 9.1` 動工前**同步改寫，不得提前（提前會讓 TODO 宣稱一件尚未定案的事）亦不得遺漏（遺漏則兩份治理文件對同一殘留給出相反狀態）。
- `M-SU-D1-23` — 由本延伸 §G (G-2) 順道處置（新增兩標的交錯平行組），`needs-research` 解除。
- `D1`／`R-5` — 不在本延伸；`D1` 須走 R 重開。
- `SU-RESID-4`／`SU-RESID-5` — 不動（觸發條件未到）。
- `R-3`（UAT 最後，user-ruling）、`R-4`（屬 GAP-3，blocked-by）— 不動。
- 🔴 **誠實邊界**：IC 端到端真實 run **未跑**（四家偵察與三家找碴皆同此限縮）；`api/services/` 未逐檔讀、僅型樣 grep，故 (5.4)／(5.5) 可能仍不完整——`Task 9.3` 動工前須再掃一次並更新 `D-002-C5`。

## 沿革與追溯索引

<!-- HISTORY-BEGIN -->
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-consult-r1/synth.md`（四家偵察 18 條／六群）建立本延伸。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md`（三家找碴 15 條／七群，三家全數 blocked）修訂為本版——新增 `D-002-C0`（timeframe 雙語意分名）、`D-002-C3`（同側約束）、`D-002-C6`（量詞分離）、`Task 9.4`；觸及面由 15 處增為 16 處；Task 9.3 改為逐處列名；§G 拆解 (G-1)(G-2)(G-3)；mutation 由 6 條增為 18 條。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r2/synth.md`（三家閉合輪 11 條／九群，codex 與 grok 仍 blocked）第三次修訂——新增 `Task 9.2`（producer 停止 `selected_timeframe` 單選、輸出全量 keyed rows，為本批核心）與 (0.6)（既有欄位保留、新增欄位分名）；(3.1) 補「可比時點」前提使同側判定不再誤殺；(3.2) purge 字面定為沿用既有 `interval_crosses_split_boundary` 不新增值集；(6.2) 量詞改逐消費者定義（`baseline` 之 `n_test` 維持樣本數語意）；`clusters` 定案不加 `feature_timeframe`、維持事件級；summary 新鍵由 `discarded_per_tf_rows_by_timeframe` 改名為 `discarded_rows_by_feature_tf`（原名含裸 `timeframe`，與 (0.6) 互斥）；mutation 由 18 條改為**表格**共 20 條，每列具完整 ID 與應紅之測試。本輪另修正前一版之義務項行型與觸及面宣告——該缺陷由 `scripts/obligation_block_check.sh` 檢出，前一版僅跑格式與 xref 未跑該閘。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r3/synth.md`（三家 15 條／七群，全採納零駁回）第四次修訂——①`Task 9.2` 範圍納入唯一生產 caller `momentum/Analysis/event_samples/pipeline.py` 並標明「只改被呼叫端不算完成」（前兩次修訂都沒補到核心目標）；②`(3.1)` 由「須先定義可比時點」改為**直接給出可操作定義**：split 側一律由事件級 `decision_at_ms` 決定，各 feature TF 之 cutoff 只用於取特徵、不參與判側 ⇒ 同事件各 feature TF **恆**同側為結構性保證；③**連帶修訂 R2 裁決**——(3.2) 之異側處置由「整事件 purged」改為 **fail-closed `AlignmentViolationError`**（(3.1) 消除「異側屬合法」之前提後，異側即為實作缺陷，purge 會把缺陷偽裝成樣本流失），既有 `interval_crosses_split_boundary` 維持原義不動；④`Task 9.2a` 定案兩道既有重複 guard 改為**複合鍵唯一**判準，並定其須在 `D-002-C3` 同側檢查**之前**執行；⑤§V 補 purged 複合鍵唯一與 `n_event_tf_rows_purged` 斷言、`D-002-C3` 成對斷言改寫為正例（不誤 purge）＋反例（raise）；⑥`Task 9.1` 逐處指名 route `api/routes/case.py:487`／service `case_import_service`／response field `EventAnalyzeResponse.summary`（為 `Dict[str, Any]` ⇒ 新鍵自動穿過但**零型別保證**，驗收須明列鍵名之契約測試）／前端 `EventTablesPanel.tsx:347,361`；⑦`Task 9.5` 指名平行組生成入口 `scripts/freeze_splitunify_golden.py` 之 `_plans()`／`_event_keys()`／`_build_actual()`，`main()` 只增鍵不覆蓋舊錨；⑧`M-SU-D2-19` 改為反向 mutation（survivor 六鍵**被改成含 feature TF** 才是缺陷）、`M-SU-D2-14`／`15` 之應紅測試隨 (3.2) 改為 raise；⑨§N 補 `docs/SPLITUNIFY_TODO.md` §E 之狀態同步時點（三家戳記後、`Task 9.1` 動工前）。
<!-- HISTORY-END -->

## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。
