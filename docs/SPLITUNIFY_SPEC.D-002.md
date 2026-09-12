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

新增: `D-002-C0`（術語）、`D-002-C3`（同側約束）、`D-002-C4`（對 D-001 之更正）、`D-002-C5`（單鍵消費面）、`D-002-C6`（量詞分離）、`Task 9.1`～`Task 9.5`（含 `Task 9.2a` schema 與 `Task 9.2b` 側別判定）
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

**(5.1) 清單效力與分類準則**：本清單取代 D-001 第 189 行之六處。來源＝四家偵察合併盤點 ＋ 三家找碴補列。🔴 **本清單之分類已於 R6 全面更正**：前版以「有無 `set_index("event_id")` 之形狀」列入，違反本延伸自己在 `Task 9.3` 寫下的「不得用形狀規則」，導致多處誤列。**現行判準＝逐處問「這張表的一列代表什麼」**，三分類如下：**(甲) 事件級——維持不動**（一列＝一事件：`receipts.event_level`、`manifest.table`、`clusters`、`feature_materialization` 之輸出、`dedupe` 之保留集、`ic_feed` 之單一 TF 過濾後表與 survivor 六鍵、`counterexample_classifier`、`candidate_ledger`、`tables` 之 `.loc[eid]`、前端 `batch_facts`、前端搜尋頁匯出 Map、`clusters_oracle.json`、`report_int_keys.json`）；**(乙) 複合鍵——須改**（一列＝一個 `(event_id, feature_timeframe)`：`build_event_keys` 輸出、`assignments`／`purged` 組裝、golden 之 `g1_membership`、`test_splitunify_wiring.py:103-104` 之 `dict(zip(...))` 映射）；**(丙) 事件級但需去重取唯一值**（消費複合鍵表卻只要事件級答案：`pattern_bridge` 之 `assign.set_index("event_id")["split_label"]` ⇒ 須去重取唯一側、**不唯一即 fail-closed**，不得改成複合鍵索引；`ic_feed` 之 survivor 餵入端須先去重，否則重複三元組會改變雜湊）。實作前須再掃一次並更新本表（見 §N 誠實邊界）。

**(5.2) 第一層｜producer 與投影本體**：🔴 本項描述的是**本延伸落地後**之契約（改前形狀見 `D-002-C4` 與各 Task 之「現況碼證」，不在此重述）：`split_projection.build_event_keys` 預設輸出全量、以 `(event_id, feature_timeframe)` 唯一（`merge validate="1:1"` 之判準與輸出欄改法見 `Task 9.2`，具體落點 `split_projection.py:291-303`）；`split_projection` 之 `assignments`／`purged` 兩表**皆含** `feature_timeframe` 欄；`event_split.build_time_clusters` **維持事件級**（一 manifest 列對一 `event_id` 列，同事件各 feature TF 共用該列，定案見 `Task 9.2a`）；側別判定以事件級 `decision_at_ms` 為錨（見 `Task 9.2b`）。

**(5.3) 第二層｜表格鏈（D-001 原列六處）**：🔴 **本項為現況描述；每處之處置一律以 `(5.1)` 三分類為準**（v7 以前此處寫的「靜默／須改」是**改判前**之判定，已作廢）。`feature_materialization` 之 `merge validate="many_to_one"`（複合鍵後仍成立、**不需改**）與 `groupby("event_id")+row_vals.update`（**設計上的橫向合併**，(5.1) 甲類維持）與輸出 `set_index("event_id")`（同屬甲類，只需斷言多列輸入不靜默覆蓋）；`baseline`（繼承上游事件級索引，甲類）；`pattern_bridge` 之 `set_index("event_id")["split_label"]`（複合鍵後取到 Series ⇒ **(5.1) 丙類**，去重取唯一側）；`tables` 兩處 `set_index`（甲類）；`ic_feed` 兩處 `set_index` ＋ `.loc[keep["event_id"]]`（先過濾單一 TF，索引本就唯一，甲類）；`dedupe` 之 `merge validate="one_to_one"`（對事件級 `events`，仍成立）與 `cluster_first` 保留集（甲類，保留之 `event_id` 廣播到 per-TF 列）。

**(5.4) 第三層｜偵察補列**：🔴 **同上，處置以 `(5.1)` 為準**。`counterexample_classifier` 之 `.loc[eid]`（迴圈迭代事件級匯入表，甲類）；`candidate_ledger` 雙 `set_index` ＋ `.loc[eid]`（迴圈迭代 `set(...)` 本身去重，甲類）；`ic_feed.event_context_from_windows` survivor 六鍵（以排序後 `event_id` 列雜湊，**不含任何 TF 欄**，甲類；🔴 但**餵入端須先去重**，否則同事件多列會產生重複三元組而改變雜湊）；`frontend/src/lib/types.ts` batch_facts（批次級彙總，甲類）／ `frontend/src/app/search/page.tsx` 之 `byEventId` Map（鍵由 `canonicalEventId(symbol, timeframe, t0)` 建立、來源為 CSV 原始列，甲類；`Task 9.5` 明文**排除**於複合鍵遷移之外）；`tests/golden/splitunify/{splitunify_golden,clusters_oracle}.json`（前者之 `g1_membership` 為 **(5.1) 乙類**、確需擴維；後者維持事件級、不動）。

**(5.5) 第四層｜記帳與報告鏈**：🔴 凡直接讀取或顯示 split count 者——`pipeline` 產出之 `n_train`／`n_test`／`n_purged`、其 API 模型、前端事件批面板、以及既有 wiring 測試中以 `dict(zip(event_id, …))` 建映射之處——具體為 `test_splitunify_wiring.py:103-104`（同 `event_id` 多 feature TF 時**後者覆蓋前者**）。

<!-- OBLIGATIONS-END -->

### D-002-C6 事件數與列數是兩個量

<!-- OBLIGATIONS-BEGIN id=D-002-C6 -->

**(6.1) 三個量之定義**：複合鍵落地後，以下三個量**各自定義、不得互相代用**：`n_events`＝去重後之 `event_id` 數；`n_event_tf_rows`＝`(event_id, feature_timeframe)` 列數；既有之 `n_train`／`n_test`／`n_purged`。

**(6.2) 三量之粒度逐消費者定義**：🔴 **不得一刀切**。`split_projection` 之 `summary` 與報告分母、前端顯示、既有 wiring 斷言之 `n_train`／`n_test`／`n_purged` 維持**事件數**（`n_events` 粒度）語意；🔴 **`baseline` 之例外句於 v9 更正（R8 兩家）**：`Task 9.3` 已定 `feature_materialization` **維持事件級橫向合併** ⇒ `baseline` 吃的是**事件級**特徵向量，一事件只得一個樣本，故其 `n_test`＝**樣本數＝事件數**，兩者在本延伸落地後**等價**；原「複合鍵後即 `(event_id, feature_timeframe)` 列數、**不得**改判為事件數」之寫法**作廢**（它與 `Task 9.3` 定案互斥，實作者依任一側都可自稱合規）。若未來另立 per-TF 模型輸入 adapter，屆時再改本義務。實作須逐消費者標明其粒度，列數另以 `n_event_tf_rows_train` 等新名承載。

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
- 🔴 **(G-4c) v9：區分「因換錨改側」與「實作寫錯」之機械閘＝同步改寫獨立 oracle**（R8 三家共同指出 (G-4a) 之「commit 訊息逐筆說明」不是閘）。`scripts/freeze_splitunify_golden.py:133-138` 之 `_oracle_membership` docstring 逐字「直接由 `feature_index[row_index]` 投影出成員集合——**與被測函式無因果關係**」「🔴 刻意**逐行重寫**兩段式規則（**不 import 投影**）：oracle 的價值就在於它是**第二份推導**，共用實作就退化成同義反覆」（該 docstring 另引一則 B2b 審查裁決為據，編號見沿革），而它**目前也以 `feature_cutoff_ms` 判側**。⇒ **`Task 9.2b` 落地時，須同步以 decision-anchor 逐行重寫該 oracle（維持「不 import 投影」）**；如此 `main()` 中每次都驗的 **G-3b**（`g1_membership != g3b_oracle` 即 FAIL）**自動成為區分閘**——因換錨而改側者兩邊同步、實作寫錯者只有投影那邊改而立即紅。**不新造** `allowed_reanchor_diff` 檔，**不保留** cutoff-anchor 平行鍵。
- 🔴 **(G-4d) 三項硬性附帶條件**：①**保留 v8 baseline 不覆寫**（重凍寫新鍵，舊鍵留為換錨前之回歸錨；`--write` 不得直接覆蓋，R8 codex）；②`decision_at_ms == feature_cutoff_ms` 之事件**必須零位移**（硬斷言）；③`decision != cutoff`（即 `decision_at_ms != feature_cutoff_ms`）之單 TF 邊界 fixture **須進 §V 與 mutation**，不得只寫在 §G 散文。
- 🔴 **(G-4) 換錨與 exact 的本質衝突，須二擇一寫死（R7 codex）**：`alignment.py:87-93` 之 `feature_cutoff_ms = max{close_ms <= decision_at_ms}` **允許 `cutoff < decision`** ⇒ 即使不碰隔離帶，單純把判側依據由 `feature_cutoff_ms` 換成 `decision_at_ms`，**邊界事件就會改側**（碼證：`test_start=1000, decision=1000, cutoff=900`，即 `test_start_ms=1000`、`decision_at_ms=1000`、`feature_cutoff_ms=900` ⇒ 舊路徑判 train、新路徑判 test）。⇒ 本延伸**採 (G-4a)**：`(3.1)` 之事件級錨定為**正確語意**（舊路徑以 cutoff 判側才是缺陷——它讓同事件各 TF 可落不同側），故 **§G 之 exact 基準隨之更新**：單 TF golden 於 `Task 9.2b` 落地後**重凍一次**，重凍前後之差異**須逐筆列出並在 commit 訊息說明**，且僅允許「因換錨而改側」這一種差異；任何其他位移仍為 FAIL。**不採 (G-4b)**（維持 cutoff 判側以保 exact）——那等於放棄 `(3.1)`，而 `(3.1)` 是本延伸消除「同事件異側」的唯一手段。🔴 驗收須含 `decision != cutoff`（即 `decision_at_ms != feature_cutoff_ms`）之單 TF 邊界 fixture，否則此差異不會被任何測試看到。

### §P Phase 與依賴

#### Phase 9A — 揭露先行（依賴：無）

**Task 9.1 — 丟棄列數之完整資料流契約**
- 目標：在複合鍵落地**之前**，先消除「靜默丟棄」之誠實性缺陷，且必須讓**終端使用者**看得到。
- **返回形狀**（契約，缺一不可）：`build_event_keys` 回傳之 keyed 事件表外，另回傳
  `discarded: Dict[str, int]`——鍵為被丟棄之 `feature_timeframe`、值為列數；無丟棄時為 `{}`（**不得**省略或回 `None`）。
- **跨邊界傳遞**：`_derive_single_symbol` 與 per-symbol 分派器須將其原樣寫入
  `EventSplitPlan.summary["discarded_rows_by_feature_tf"]`（🔴 依 `D-002-C0` (0.6)，新增鍵名不得含裸 `timeframe`）；多 symbol 時逐 symbol 相加。
- **揭露落點（🔴 v9：本延伸只交付 producer 層；API 與前端隨 §N 殘留延後，**不再**列入 9A 完成條件）**：
  - **route**：`api/routes/case.py:487` `POST /case/events/{import_id}/analyze`；**service**：`api/services/case_import_service.py`（`get_event_import_service()`）。
  - **response field**：`api/models/event_import_models.py:306-308` 之 `EventAnalyzeResponse.summary`。🔴 其型別為 `Dict[str, Any]`（前端對應 `frontend/src/lib/types.ts:3176` 之 `Record<string, unknown>`）⇒ **新鍵會自動穿過、不會被型別擋下，也因此完全沒有型別保證**：驗收**不得**依賴 pydantic 或 TS 型別，須在 route 層寫**明列鍵名**之契約測試。
  - **前端顯示**：`frontend/src/components/ic-analysis/EventTablesPanel.tsx:347` 取 `resp.summary`、`:361` 為現行 `train／test／purge` 顯示行；丟棄列數須顯示於此，文案「本次分析只用了 `<selected>`，丟棄 `<tf>: <n>` 列」。
  - 🔴 **上列四個落點於 R6 全部作廢（保留字面供追溯，不得據以實作）**：`api/routes/case.py:487`／`case_import_service`／`EventAnalyzeResponse.summary`／`EventTablesPanel.tsx:347,361` 這條路徑**在本票設計上永遠不會有 `discarded`**——`case_import_service.py:1592-1626`（關鍵註解位於 `case_import_service.py:1592-1609`）逐字寫著「事件掃描端**恆走** event-study-only」，該 service 呼叫的是 `run_event_study_only_with_params`（即 `run_event_study_only` 路徑）而非 `run`，並註明此為 SPEC C-0 決議③／R2 之 D1 之**既有裁定**（理由：該 service 完全不碰 FF run，拿不到 canonical feature universe），且 capability **刻意不留 `"ok"` 分支**、殘留已具名給 `R-5`。它根本不呼叫 `build_event_keys`。
  - 🔴 **v8 定案：本延伸只交付 producer 層，終端可見性具名為殘留**（v7 曾寫「採 (b)、改掛 IC 主線」，**作廢**——R7 三家獨立指出 `ic_filter_orchestrator` 只呼叫 `holdout_boundary`、**不含** `build_event_keys`，`metadata.split_unify` 亦只寫 `n_test`，兩者不是同一條資料流）。**根本障礙不在本延伸**：`api/` 對 `EventSamplePipeline.run` 之呼叫點為 **0**（`grep` 實證，唯一 `.run(` 帶 canonical 邊界者只在 `tests/momentum/event_samples/test_splitunify_wiring.py`）⇒ **投影路徑本身尚無生產接線**，那是前批「接線」留下的既有狀態。
  - **本延伸交付**：`build_event_keys` 回傳 `discarded` ＋ 寫入 `EventSplitPlan.summary["discarded_rows_by_feature_tf"]` ＋ 於 `metadata.split_unify` **擴充回傳結構**承載該鍵（🔴 **不得**改動其 `reason` 封閉值集——`build_split_unify_disclosure` 對非法字面即 raise，該值集已戳記且前端有枚舉面）。
  - 🔴 **`metadata.split_unify` 是 exact-key 契約，加鍵須同批改五處（R8 codex；前版誤當「順手擴欄」）**：`build_split_unify_disclosure`（`split_projection.py:123-180`）現**恰回五鍵**；契約檔 `momentum/Analysis/contracts/split_unify.json`；唯一 caller `ic_filter_orchestrator.py:1530-1534`（現不傳 `discarded`）；`tests/api/test_splitunify_disclosure.py:149-151,270-277` 對該欄做 **exact-key 斷言**（不同步改即紅）；前端型別面。新鍵型別定為 `Dict[str, int]`（鍵＝被丟棄之 `feature_timeframe`、值＝列數）。**若評估後認為此成本超出 Phase 9A「揭露成本極低」之定位，應改為只交付前兩層並把本層併入 §N 殘留**——不得半套上線。
  - **具名殘留**：終端可見性（API 回應欄位與前端顯示）之落地**待投影路徑有生產接線後補**，理由類別 **`blocked-by`**（碼證＝零呼叫點），登記於 §N。🔴 **不得**在本延伸新增一條 API 只為了讓 9A 有揭露面——那是把別票的缺口塞進本票，且與 Phase 9A「揭露成本極低」之定位互斥。**指名落點不等於該落點走得到**——此缺口我連續兩版指向走不到的地方（v4 指事件掃描端、v7 指 IC 主線），v8 改為誠實具名殘留。
- **獨立回退之判準**：移除上述三層後系統行為須與 9A 前逐值相同（無其他消費者依賴該欄）——此為可證偽斷言，須有測試。
- 不可做：不得以揭露取代複合鍵；不得在丟棄時 raise（會擋掉目前合法的單 feature TF 用法）。

#### Phase 9B — 複合鍵主體（依賴：Phase 9A）

**Task 9.2 — producer 停止單選，輸出全量 keyed rows**
- 🔴 **本 Task 是第 9 批的核心；沒有它，下游全部改完 `SU-RESID-2` 仍不會被解決**（只加欄位而 producer 照舊單選，丟棄行為原封不動）。
- 檔案：`split_projection.build_event_keys` **與其唯一生產 caller** `pipeline.py:747` ——現行該處逐字為 `build_event_keys(receipts, selected_timeframe=str(selected_timeframe))`（**必傳**，且 `str()` 強制轉型，連 `None` 都會變成字面 `"None"`），以及該參數之設定來源 `config.split` 一路上溯之 `selected_timeframe`。
- 🔴 **投影入口之四參數閘同屬本 Task 範圍**：`pipeline.py:723-732` 以 `given = [k for k, v in projection_args.items() if v is not None]` 要求 `train_plan`／`test_plan`／`feature_index`／`selected_timeframe` **四者同時非 `None`**，否則 raise；`pipeline.py:711-715` 之 docstring 亦逐字寫「四者同時」。⇒ **只把 caller 改成傳 `None` 會在抵達 `build_event_keys` 之前就 fail-closed**。改法：投影門檻改為 `train_plan`／`test_plan`／`feature_index` **三者同時**，`selected_timeframe` 移出必填集合（`None`＝全量、字串＝可選單選過濾），docstring 同步改寫。
- 🔴 **只改被呼叫端不算完成**：本 Task 的驗收是**端到端**——經 `EventSamplePipeline.run` 實際產出全量列才算；只要 caller 仍必傳 `selected_timeframe`、或四參數閘仍擋 `None`，生產路徑的靜默丟棄就原封不動。
- 改法：`build_event_keys` 之 `selected_timeframe` 由**必填改為可選**（預設 `None` ＝ 全量），輸出**全量** `(event_id, feature_timeframe)` keyed rows；caller 改為不傳（或明示傳 `None`），🔴 並**一併移除 `str()` 強制轉型**——留著它會把 `None` 轉成字面 `"None"`，被下游當成一個叫 `None` 的 feature TF，產出空表而非全量（改了 producer 卻沒改這裡＝本 Task 白做）；`selected_timeframe` 僅在呼叫端明確要求單一 TF 時作為**可選**過濾器，且過濾掉的列數仍須依 `Task 9.1` 揭露。
- 🔴 **producer 內部之 merge 與輸出欄同屬本 Task 範圍（第四層；三家 R5 獨立撞題）**：`split_projection.py:291-303` 現行為 `event_level.merge(selected[["event_id","feature_cutoff_ms"]], on="event_id", how="inner", validate="1:1")`，且輸出欄 `timeframe` **取自 `event_level`**（即**觸發** TF，`alignment.py:216`），merge 只帶 `feature_cutoff_ms` 過來。⇒ 只改四參數閘與 caller，全量多 feature TF 會**在此 `MergeError`**；縱使把 `validate` 放寬，兩列也會得到**相同**的 `timeframe` 值而讓複合鍵碰撞。改法：(a) 改以 `per_tf` 為**行粒度**與 `event_level` 接合，`validate` 判準改為複合鍵；(b) **新建**輸出欄 `feature_timeframe` 取自 `per_tf.timeframe`（逐字採 `D-002-C0` (0.3)），**不得**以 `event_level.timeframe` 冒充；(c) 單選過濾路徑仍每事件一列時，可續用 `1:1`。
- 🔴 **`split_projection.py:271` 之 docstring 舊語意須一併改**：現逐字寫「每個事件在 `selected_timeframe` 下必須**恰有一列** `per_tf`」，與本 Task 之全量複合鍵互斥；不改則實作者讀 docstring 會照舊語意寫。
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

**Task 9.2b — 側別判定改為事件級錨定（`D-002-C3` (3.1) 之施工落點）**
- 🔴 **本 Task 是 `(3.1)` 的唯一落地處；沒有它，(3.1) 只是規格層的宣告，行為不變**。現況碼證：`split_projection.py` 全檔 `decision_at_ms` 命中數為 **0**；`split_projection.py:530-553` 逐列取 `cutoff = int(rec["feature_cutoff_ms"])` 後以 `cutoff in train_ms`／`cutoff in test_ms` 定側。
- 檔案：`split_projection._derive_single_symbol` 之集合成員判定迴圈（`:530-553`）。
- 改法：以 `manifest.table` 之 `decision_at_ms`（該欄已存在，`event_split.py:68` 已在使用；`manifest` 已在 `_derive_single_symbol` 作用域內）**每事件判一次側**，再廣播到該 `event_id` 之所有 feature TF 列；`feature_cutoff_ms` 僅供物化與 PIT，**不參與** `split_label`。答案窗 purge（`interval_crosses_split_boundary`）改按**事件側**判定，不再逐列用 `in_train`。
- 🔴 **側別判準（三段式，順序不得調換；R6 三家獨立撞題後定案）**：`decision_at_ms` 與 `feature_index` 未必落在同一網格——當 `feature_index` 之網格**粗於**觸發 TF 時（例：觸發 1h、特徵 4h），`decision_at_ms` 大量不在 `index_ms` 集合中（R5 實證 1h open 非 4h open 者 15,264／20,352）；但**單純改用不等式會把隔離帶收成 train**（R6 實證：gap 上集合成員給 `purged`、不等式給 `train`）。定案如下：
  🔴 **判準以時間域表述，不依賴「`decision_at_ms` 映射到哪個位置」**（R7 兩家指出位置映射未定義——`searchsorted` 的 side、前後列歸屬皆可得出不同答案，同一時刻可合法得到不同位置）。所需兩值皆一行可得且取法對稱：`test_start_ms = int(index_ms[test_rows[0]])`（現有）、`train_last_ms = int(index_ms[train_rows[-1]])`（新增）。
  0. 🔴 **前置條件（R8 codex：四條規則原本彼此重疊）**：先驗 `index_ms[0] <= decision_at_ms <= index_ms[-1]`，**不滿足即 fail-closed raise**（訊息含 `event_id`）。沒有這一步，`index=[100,200,300,400]`、`train_last=200`、`test_start=300`（即 `train_last_ms=200`、`test_start_ms=300`）時 `decision=50`（`decision_at_ms=50`）會**同時命中**下列第 1 條與第 4 條，實作者可合法選先分類而讓**越界事件進 train**；`decision_at_ms=450` 同理進 test。通過本前置後，下列三條才**互斥且窮盡**。
  1. `decision_at_ms <= train_last_ms` ⇒ **train**。
  2. `decision_at_ms >= test_start_ms` ⇒ **test**。
  3. `train_last_ms < decision_at_ms < test_start_ms` ⇒ **隔離帶**，處置為 **`purged`**（沿用既有 `interval_crosses_split_boundary` 字面）。🔴 **不得**收成 train（那是 R6 指出的缺陷），亦**不得** raise——`scripts/freeze_splitunify_golden.py:94` 之 fixture 逐字「固定 12 筆：train 段 5（其中 1 筆答案窗跨界）、**隔離區 2**、test 段 5」，其 `gap1`／`gap2` 在 golden 之 `g1_membership.purged` 中，證明「事件落在隔離帶」是**合法且預期**之情形、處置就是丟棄；改 raise 會讓單標的 golden 整批拋錯而違反 §G。
  4. `decision_at_ms` 早於 `index_ms[0]` 或晚於末列（即落在 `train_plan`／`test_plan` 覆蓋範圍**之外**）⇒ **fail-closed raise**（訊息含 `event_id`）。
  （隔離帶之位置定義供追溯：`split_preview.holdout_test_row_index:41-43` 之 `split_point = floor((1 - oos_test_size) * n)`、`start = split_point + purge_gap + embargo`、`test = arange(start, n)`，train = `arange(0, split_point)`，故隔離帶即位置區間 `[split_point, split_point+purge_gap+embargo)`，亦即前一版所寫之 `[split_point, split_point + purge_gap + embargo)`；本判準以其**時刻端點**表述以避開映射歧義。）
  （主委探針二只覆蓋「特徵網格為觸發 TF 之整數倍」之情形，不足以支撐集合成員判定之一般性；R6 之 gap 反例則證明不等式單用亦不成立——**兩者都要**。）
- 🔴 **`D-002-C3` (3.2) 之 fail-closed 檢查在此落地（其唯一施工落點）**：於複合鍵唯一 guard **之後**、寫入 `assignments` **之前**，按 `event_id` 分組檢查 `split_label` 唯一；異側即 `raise AlignmentViolationError`，訊息須含該 `event_id`。函式為 `_derive_single_symbol`（與判側迴圈同檔同函式）。沒有本條，`M-SU-D2-14`／`15` 與 §V 之反例**無碼可紅**，檢查可被整段省略而無人察覺。
- 🔴 **僅驗 `split_label` 唯一並不足夠——須加跨表互斥檢查（R6 三家獨立撞題）**：`purged` 之欄位僅 `["event_id", "reason"]`（`split_projection.py:556`），**沒有** `split_label` ⇒ 同一事件「一列進 `purge_rows`、另一列進 `assign_rows`」時，上述分組檢查**結構上抓不到**。改法：在寫入兩容器**之前**，對所有 pending 列先算出該 `event_id` 之**唯一事件狀態**，並斷言 `set(purged["event_id"]) ∩ set(assignments["event_id"]) == ∅`，違反即 `raise AlignmentViolationError`。🔴 **不得**以擴充 `split_label` 值域（新增 `PURGED` 之類）替代——那會動到已戳記之封閉值集與前端枚舉面。
- 🔴 **答案窗 purge 必須按事件側一次決定並廣播**：現行 `:540-542` 以**逐列** `in_train` 觸發答案窗 purge，正是上一條混態的來源。改法：事件側判定完成後，答案窗跨界與否**對該事件所有 feature TF 列一次決定**，同進 `purged` 或同留 `assignments`。
- 不可做：不得保留任何以 `feature_cutoff_ms` 決定 `split_label` 的分支；不得在 `(3.2)` 之 fail-closed 上線前保留 per-cutoff 判側（否則合法多 TF 輸入會開始 raise）。

**Task 9.3 — 16 處消費面逐處列名改法**
- 🔴 **不得**用「凡 `set_index("event_id")` 一律改」這種形狀規則——那既會誤改本就一事件一列的 event-level 表，又會漏掉真正折疊資料的 `groupby(...)+update`。**逐處列名，每處註明粒度與改法**：
  - 🔴 `feature_materialization`：**維持事件級橫向合併，不得改為複合鍵**（R6 codex／grok 撞題 ＋ 主委自產碼證）。理由：`groupby("event_id")+row_vals.update`（`:93-131`）是**設計上的橫向合併**——同事件各 feature TF 的特徵欄拼成**一個**特徵向量；`_combined_columns:22-32` 逐字「多 TF 特徵欄名合併；**衝突 ⇒ loud 拒**」＝欄名不帶 TF 前綴、要求各 TF 欄名互斥。改成每 TF 一列會讓 ML 輸入變成「多列、每列只有自己 TF 的欄、其餘 NaN」，**破壞特徵矩陣語意**；且 `:138-140` 之記帳不變式 `n_input = per_tf["event_id"].nunique()` 會直接 `AssertionError`，下游 `baseline:105-120`、`pattern_bridge:122-141` 亦以事件級 Index 交集／`.loc[ids]`，改 MultiIndex 後會得空集合。**本處只需**：確認 `merge validate`（`:53`，`per_tf` 對 `events` 之 `many_to_one` 複合鍵後仍成立、**不需改**）與 `set_index("event_id")`（`:132`）在多列輸入下不靜默覆蓋，並補「同名特徵欄跨 TF 衝突」之既有 loud 拒之回歸測試。
  - 🔴 **`tables`／`ic_feed`／`counterexample_classifier`／`candidate_ledger`：維持事件級 `.loc[eid]`，不得改複合鍵**（`D-002-C5` (5.1) 甲類；R7 三家獨立撞題）。理由：四者讀的都是 `receipts.event_level`／`manifest.table`／`clusters`（一列＝一事件），或如 `ic_feed:109` **先過濾單一 TF 再** `set_index` 使索引本就唯一。改複合鍵會在 event-level index 取不到列，或誘使實作者把 event-level 表複製成多列而破壞其粒度契約。**本處只需**：加「誤改為複合鍵即紅」之防誤改回歸測試。
  - 🔴 `pattern_bridge`：屬 `(5.1)` **丙類**——`:125-127` 之 `assign.set_index("event_id")["split_label"]` 在複合鍵後索引重複、取值由純量變 Series ⇒ 改法是**先去重取唯一側、不唯一即 fail-closed**（依 `(3.1)` 同事件恆同側），**不是**改成複合鍵索引。
  - 🔴 `dedupe`：**維持事件級保留集**（甲類）。`:101-110` 之 table 一列一事件、`:122-129` 以 `dedupe_cluster_id` 之 `idxmin` 取保留者，**無** `feature_timeframe` 維度；改複合鍵會在 tie 時只留一個 TF，或讓 `cluster_first` 不再是「每簇一事件」而使 effective count 與權重漂移。改法：保留集仍以事件級決定，再把保留之 `event_id` **廣播**到該事件所有 per-TF 列；驗收配「一事件兩 TF 皆存活而簇仍一列」之值與計數測試。
  - `baseline`：隨上游索引變更同步；本身不新增粒度。
  - **event-level 表（`receipts.event_level`、manifest）粒度不變**——不得一併改為複合鍵。
- 🔴 **cluster 語意**：時間簇仍按**事件級 interval** 合併，同一事件之不同 feature TF **同簇**；但同簇**不等於**同側，同側約束見 `D-002-C3`。

**Task 9.4 — 記帳與報告鏈**（`D-002-C6`；三家全中之缺口）
- 檔案：`pipeline` 之 count 產出、對應 API 模型、前端事件批面板、既有 wiring 測試之 `dict(zip(...))` 映射。
- 改法：依 (6.2) 將 `n_train`／`n_test`／`n_purged` 明確定為事件數；新增列數欄；`dict(zip(...))` 改為複合鍵映射。
- 🔴 **事件數門檻路徑同屬本 Task（R6 grok／composer）**：`split_projection.py:562` 之 `n_test = int((assignments["split_label"] == "test").sum())` → `:569` 之 `per_symbol_test_n` → `:716-719` 比 `tier_min_test_events`，以及 `:559-561` 之 `per_symbol_n`（`event_keys` 行數），複合鍵後**皆會被 TF 維度膨脹**：1 事件 × 2 TF 使 `n_test=2 ≥ tier_min=2` 而真實事件數為 1 ⇒ **靜默繞過測試段事件數下限**（命中 §RISK (d)）。改法：兩者皆改以 `event_id` **去重計數**，列數另立新名。
- 🔴 **該旗標之終端揭露隨 `Task 9.1` 之殘留一併延後（v9 更正；原寫「同批必須補」與具名殘留互斥）**：`insufficient_events_in_test` **不擋任何分析**，只被 `tables.py:162` 原樣放進報告，且**前端完全未顯示**（主委實跑 grep 確認）。⇒ 本延伸**只**修正其計數（改 `event_id` 去重），**終端可見性**與 `Task 9.1` 同屬 §N 之 `SU-RESID-9A-UI` 殘留，**不列入本批完成條件**。🔴 **誠實邊界**：這表示本批交付後，「樣本不足」仍只存在於報告資料裡、使用者看不到——此為**已知且具名**之限制，不得在驗收時當作已解決。
- 🔴 **`baseline` 之語意於 R7 更正（前版寫「一事件兩列、`n_test`＝2」，**作廢**）**：`Task 9.3` 已定 `feature_materialization` **維持事件級橫向合併** ⇒ `baseline.py:105-110` 之 `idx = features_at_decision.index.intersection(...)` 取到的就是**事件級**索引，一事件只會得到**一個**樣本。故 `baseline` 之 `n_test` 在本延伸落地後**仍為事件數**，與 `(6.2)` 之「`baseline` 為樣本數例外」在**事件級物化前提下等價**（樣本＝事件）。🔴 **不得**為了湊「複合鍵列數」而把特徵向量複製成多列——那會產生重複向量或稀疏向量，且與「`baseline` 不新增粒度」互斥。若日後要 per-TF 模型輸入（即以 `(event_id, feature_timeframe)` 為列的模型輸入矩陣），須**另立** adapter 與 features／labels／weights／schema 契約，**不在本延伸**。

**Task 9.5 — golden 與前端**
- 檔案：`tests/golden/splitunify/*`；**平行組之生成入口＝`scripts/freeze_splitunify_golden.py`**（具體為 `_plans()`／`_event_keys()`／`_build_actual()` 三處 fixture 構造函式，寫檔在 `main()`）；`frontend/src/lib/types.ts`；`frontend/src/app/search/page.tsx`。
- 改法：golden 依 §G (G-2)(G-3) 擴維並新增交錯平行組——`_event_keys()` 產出多 feature TF 列、`_build_actual()` 以**新鍵**承載平行組，`main()` 寫檔時**只增鍵不覆蓋**單標的舊鍵（舊鍵即 §G 之回歸錨）。
- 🔴 **前端 `byEventId` Map 於 R6 改判為「排除於複合鍵遷移之外」**（前版要求改複合鍵，**作廢**）：該 Map 之鍵由 `canonicalEventId(symbol, timeframe, t0)` 建立、來源是使用者上傳 CSV 之原始列（一事件一列），而 `eventExport.ts:516-535` 之 record 僅有 `event_id`／`symbol`／`timeframe`／`t0`、**無** `feature_timeframe` ⇒ 改成複合鍵會讓 `byEventId.get(String(rec.event_id))` **全數 miss**，使用者匯出的附帶欄位**靜默變空**，並違反 `D-002-C0` (0.6)「既有 wire 欄位原樣保留」。此為 `D-002-C5` (5.1) 分類 **(甲) 事件級——維持不動**。

### §V 驗證策略與邊界測試目錄

- `Task 9.1`（🔴 **三層標的已隨 v8 之殘留決策更新**；v7 之「API 回應／前端型別」兩層**作廢**，不得再據以寫測試）：`ASSERT build_event_keys WHEN per_tf 含 1h 與 4h 而 selected=1h THEN discarded == {"4h": 2}`；`ASSERT WHEN 單一 feature TF THEN discarded == {}`；`ASSERT EventSplitPlan.summary 帶 discarded_rows_by_feature_tf 且值與 producer 回傳相同`；`ASSERT metadata.split_unify 帶該鍵且其 reason 封閉值集未被改動`；`ASSERT 移除上述三層後行為與 9A 前逐值相同`（獨立回退之可證偽斷言）。終端可見性之斷言待接線後補（見 §N 殘留）。
- `Task 9.2`（🔴 **端到端，不得以 schema 斷言代替**；**斷言標的逐字指定為 `split_plan.assignments`**，不是 `features`）：`ASSERT WHEN per_tf 含 1h 與 4h 且經 EventSamplePipeline.run（不傳 selected_timeframe）THEN assignments 列數 == per_tf 列數 且 兩個 feature TF 皆在`；`ASSERT WHEN 四參數閘收到 selected_timeframe=None THEN 不 raise 且走投影路徑`；`ASSERT build_event_keys 輸出之 feature_timeframe 逐列取自 per_tf 而非 event_level`（否則兩列同值、複合鍵碰撞）。🔴 **既有 `test_splitunify_wiring.py` 之 partial-boundary 參數化案例（現把 `selected_timeframe=None` 視為必須 raise）須\*\*替換\*\***——不得只新增一條而留著舊的與新行為互斥。
- `Task 9.2a`：`ASSERT assignments THEN 欄含 feature_timeframe 且 (event_id, feature_timeframe) 唯一`。
- `Task 9.2b`：`ASSERT WHEN 同 event 之 1h cutoff 落 train 區、4h cutoff 落 test 區 且 decision_at_ms 落 test 區 THEN 兩列 split_label 皆為 test`（事件級錨定之直接反例；現行碼在此案例會給出 1h=test／4h=purged）。
- `D-002-C3`（成對，缺一即無鑑別力）：`ASSERT WHEN 同 event 之 1h 與 4h 之 feature_cutoff_ms 不同且皆 <= decision_at_ms THEN 兩列同側且皆不 purged`（(3.1) 結構性保證之正例）；`ASSERT WHEN 直接構造 assignments 使同一 event_id 之兩列異側 THEN raise AlignmentViolationError`（(3.2) 之反例；須一併驗其**不是**靜默取一側、**不是**改判 purged）。
- `D-002-C3` purge 面：`ASSERT purged THEN (event_id, feature_timeframe) 唯一`（purge 路徑同樣不得折疊列）；`ASSERT summary THEN 帶 n_event_tf_rows_purged 且其值 == purged 列數`（與事件級 `n_purged` 並存、不得互相代用）。
- `D-002-C6`：`ASSERT summary THEN n_events 與 n_event_tf_rows 並存`；`ASSERT n_train+n_test+n_purged == n_events`（事件數守恆，非列數）。
- `Task 9.3`：**逐處**各一條「改壞就要變紅」測試；🔴 靜默面須斷言取到的**值**正確，不得只斷言「不報錯」。🔴 **v9：七條反向 mutation 之應紅測試須落在具名檔（R8 兩家：散文描述不算已具備回歸網）**——`M-SU-D2-04`→`tests/momentum/event_samples/test_feature_materialization.py`；`06`→`test_tables.py`；`08`→`test_counterexample_classifier.py`；`09`→`test_candidate_ledger.py`；`10`→`test_dedupe.py`；`02`／`03`→`tests/momentum/Analysis/test_splitunify_derive.py`（`03` 另加 `tests/api/test_splitunify_disclosure.py`）；`07`（`ic_feed`）**無專屬測試檔**，須擇 `tests/momentum/event_samples/test_gap3_conditional_ic.py` 或新建；`11`（前端 `byEventId`）**無對應 vitest**，須新建。🔴 **在上列測試實際存在之前，不得宣稱 mutation 網已閉**。
- `Task 9.5`：`ASSERT golden WHEN 單 TF fixture THEN 舊值逐值不變`；`ASSERT 交錯平行組之 g5 與單標的組不同且各自穩定`。
**mutation 目錄**（🔴 逐處對應，不得以單一 generic mutant 冒充；每列皆須有**完整 ID** 與**應紅之測試**；共 **26** 條，🔴 本數字須與表列實數相符——前一版寫 23 而實列 22，由 R5 兩家以計數抓出；🔴 **一 mutation 一 defect**：R6 指出 `M-SU-D2-23` 曾以 OR 合併兩個獨立缺陷，已拆為 `23`／`26` 各配自己的應紅測試）

| ID | 改壞什麼 | 應紅之測試 |
|---|---|---|
| `M-SU-D2-01` | 9A 之 `discarded` 不寫入 summary | `Task 9.1` 之 summary 鍵斷言 |
| `M-SU-D2-02` | `discarded` 寫入 producer 回傳但**不寫入** `EventSplitPlan.summary` | `Task 9.1` 之 summary 鍵與值斷言（`tests/momentum/Analysis/test_splitunify_derive.py`） |
| `M-SU-D2-03` | summary 帶了但**不傳入** `metadata.split_unify`（或改動了 `reason` 封閉值集） | `Task 9.1` 之 `metadata.split_unify` 鍵斷言 ＋ `tests/api/test_splitunify_disclosure.py` 之 exact-key 斷言 |
| `M-SU-D2-04` | `feature_materialization` **被誤改為每 feature TF 一列／MultiIndex**（正確實作是維持事件級橫向合併，見 `Task 9.3`） | 事件級物化**值**斷言：同事件多 TF 須合併為**一列**且欄為各 TF 聯集；誤改後 `:138-140` 之 `n_input` 記帳不變式亦會 `AssertionError` |
| `M-SU-D2-05` | `pattern_bridge` lookup 退回單鍵 | `pattern_bridge` 之 split_label 值斷言 |
| `M-SU-D2-06` | `tables` 之 `.loc[eid]` **被誤改為複合鍵 lookup**（正確實作是維持事件級，見 `(5.1)` 甲類） | `tables` 之事件級 lookup 值斷言：誤改後在 `receipts.event_level`／`clusters` 索引取不到列 |
| `M-SU-D2-07` | `ic_feed` 之 `set_index` **被誤改為複合鍵**（它已先過濾單一 TF，索引本就唯一） | `ic_feed` 之逐列值斷言：誤改後 `.loc[keep["event_id"]]` 取不到列 |
| `M-SU-D2-08` | `counterexample_classifier` **被誤改為複合鍵**（其迴圈迭代事件級匯入表） | 分類結果與 receipt 列之綁定測試（誤改後綁不到） |
| `M-SU-D2-09` | `candidate_ledger` **被誤改為複合鍵**（其迴圈迭代 `set(...)`、本身已去重） | 帳本列綁定測試（誤改後綁不到） |
| `M-SU-D2-10` | `dedupe` 保留集**被誤改為 `(event_id, feature_timeframe)` 粒度**（正確實作是事件級保留＋廣播） | 「一事件兩 TF 皆存活而簇仍一列」之值與計數測試；誤改後 `cluster_first` 不再是每簇一事件、`w=1/n` 與 effective count 漂移 |
| `M-SU-D2-11` | 前端 `byEventId` Map **被誤改為複合鍵**（正確實作是維持 `event_id`／`canonicalEventId` 鍵，見 `Task 9.5` 排除敘述） | 匯出附帶欄位**值**斷言（誤改後 `byEventId.get(String(rec.event_id))` 全數 miss，extras 靜默變空） |
| `M-SU-D2-12` | wiring 測試之 `dict(zip(...))` 保持單鍵 | `test_splitunify_wiring.py` 多 feature TF 案例 |
| `M-SU-D2-13` | `n_train` 改取列數 | `D-002-C6` 之事件數守恆斷言 |
| `M-SU-D2-14` | `D-002-C3` 同側檢查整個移除（異側放行） | (3.2) 異側 `AlignmentViolationError` fail-closed 斷言 |
| `M-SU-D2-15` | 同側檢查改為「取第一側」或改判 purged 而非 raise | 同上（須指名 raise，不得取一側、不得吞成 purge） |
| `M-SU-D2-16` | golden 仍以 `event_id` 清單比對 | golden 多 feature TF 平行組 |
| `M-SU-D2-17` | 交錯平行組未新增而直接覆蓋單標的 g5 | golden 單標的回歸錨逐值不變 |
| `M-SU-D2-18` | event-level 表被一併改為複合鍵（過度涵蓋之反向 mutation） | event-level 粒度不變測試 |
| `M-SU-D2-19` | `ic_feed.event_context_from_windows` 之 survivor 六鍵雜湊**被改成含 feature TF**（survivor 本即事件級，改了才是缺陷） | survivor 雜湊維持事件級之測試 |
| `M-SU-D2-20` | producer 保留 `selected_timeframe` 之預設單選 | `Task 9.2` 之**端到端**全量列數斷言（經 `EventSamplePipeline.run`；schema 斷言抓不到） |
| `M-SU-D2-21` | `pipeline.py:723-732` 四參數閘未改，仍要求 `selected_timeframe` 非 `None` | `Task 9.2` 之「`selected_timeframe=None` 不 raise 且走投影路徑」斷言 |
| `M-SU-D2-22` | `Task 9.2b` 改完後又把 `split_label` 判定改回 `feature_cutoff_ms` | `Task 9.2b` 之事件級錨定反例（1h／4h cutoff 異側而 `decision_at_ms` 定側） |
| `M-SU-D2-23` | `build_event_keys` 保留 `merge validate="1:1"` | `Task 9.2` 之端到端全量列數斷言（保留 `1:1` 時全量多 TF 會 `MergeError`） |
| `M-SU-D2-26` | `build_event_keys` 輸出欄不寫 `feature_timeframe`，改以 `event_level.timeframe`（觸發 TF）冒充 | `Task 9.2` 之 `feature_timeframe` **值**斷言（同事件兩列須為不同 TF；冒充時兩列同值） |
| `M-SU-D2-24` | 答案窗 purge 仍用**逐列** `in_train`（未改按事件側） | `Task 9.2b` 之 purge 反例（同事件一列 purged、另一列 test 即為缺陷） |
| `M-SU-D2-25` | `D-002-C3` 同側檢查被移到複合鍵唯一 guard **之前** | `Task 9.2a` 之 guard 先後斷言（鍵重複時錯誤訊息須指鍵重複，不得誤報異側） |

### §R 回退

單 TF 舊值保留為回歸錨；Phase 9A 可獨立回退（移除三層揭露即可，由 §V 之可證偽斷言保證）。Phase 9B 回退需連同 16 處消費面一併還原，故 9B 須在單一批次內完成，**不得部分上線**。

### §N N/A 登記與殘留

- `SU-RESID-2` — **本延伸落實**，理由類別由 `needs-research` 解除。🔴 **狀態 SoT 同步時點**：`docs/SPLITUNIFY_TODO.md` §E 該列現仍為 `needs-research`、理由仍寫「每事件恰一個 selected per_tf row」；須於**本延伸三家戳記通過後、`Task 9.1` 動工前**同步改寫，不得提前（提前會讓 TODO 宣稱一件尚未定案的事）亦不得遺漏（遺漏則兩份治理文件對同一殘留給出相反狀態）。
- `M-SU-D1-23` — 由本延伸 §G (G-2) 順道處置（新增兩標的交錯平行組），`needs-research` 解除。
- `D1`／`R-5` — 不在本延伸；`D1` 須走 R 重開。
- `SU-RESID-9A-UI` — **本延伸不交付**「丟棄列數之終端可見性」（API 回應欄位與前端顯示），`blocked-by`（投影路徑**無生產接線**：`api/` 對 `EventSamplePipeline.run` 之呼叫點為 0，唯一帶 canonical 邊界之 `.run(` 只在 `tests/momentum/event_samples/test_splitunify_wiring.py`；此為前批「接線」遺留之架構現況，非本延伸範圍）。**觸發條件**：`api/` 出現走投影分支之生產 `run()` 呼叫點。**本延伸交付至 producer 層**（`build_event_keys` 回傳 ＋ `EventSplitPlan.summary` 鍵 ＋ `metadata.split_unify` 欄位）。🔴 **誠實邊界**：在本殘留解除前，「靜默丟棄」對**終端使用者仍然看不見**——`Task 9.1` 之驗收不得宣稱該缺陷已消除，只能宣稱 producer 層已誠實記錄。（類別依據：`templates/BRIEF_REVIEW_TEMPLATE.md:71` 之 `reason_code` 閉集為 `blocked-by`／`needs-research`／`cost`／`out-of-scope` **四值**，且同檔 `R-BRIEF-1` 之實例即以「現行派工架構」為阻塞對象——`blocked-by` **不限於票號**。本案選 `blocked-by` 而非 `out-of-scope`，因接線本身屬本 epic 範圍、只是不在本延伸批次。）
- `SU-RESID-4`／`SU-RESID-5` — 不動（觸發條件未到）。
- `R-3`（UAT 最後，user-ruling）、`R-4`（屬 GAP-3，blocked-by）— 不動。
- 🔴 **誠實邊界**：IC 端到端真實 run **未跑**（四家偵察與三家找碴皆同此限縮）；`api/services/` 未逐檔讀、僅型樣 grep，故 (5.4)／(5.5) 可能仍不完整——`Task 9.3` 動工前須再掃一次並更新 `D-002-C5`。

## 沿革與追溯索引

<!-- HISTORY-BEGIN -->
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-consult-r1/synth.md`（四家偵察 18 條／六群）建立本延伸。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md`（三家找碴 15 條／七群，三家全數 blocked）修訂為本版——新增 `D-002-C0`（timeframe 雙語意分名）、`D-002-C3`（同側約束）、`D-002-C6`（量詞分離）、`Task 9.4`；觸及面由 15 處增為 16 處；Task 9.3 改為逐處列名；§G 拆解 (G-1)(G-2)(G-3)；mutation 由 6 條增為 18 條。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r2/synth.md`（三家閉合輪 11 條／九群，codex 與 grok 仍 blocked）第三次修訂——新增 `Task 9.2`（producer 停止 `selected_timeframe` 單選、輸出全量 keyed rows，為本批核心）與 (0.6)（既有欄位保留、新增欄位分名）；(3.1) 補「可比時點」前提使同側判定不再誤殺；(3.2) purge 字面定為沿用既有 `interval_crosses_split_boundary` 不新增值集；(6.2) 量詞改逐消費者定義（`baseline` 之 `n_test` 維持樣本數語意）；`clusters` 定案不加 `feature_timeframe`、維持事件級；summary 新鍵由 `discarded_per_tf_rows_by_timeframe` 改名為 `discarded_rows_by_feature_tf`（原名含裸 `timeframe`，與 (0.6) 互斥）；mutation 由 18 條改為**表格**共 20 條，每列具完整 ID 與應紅之測試。本輪另修正前一版之義務項行型與觸及面宣告——該缺陷由 `scripts/obligation_block_check.sh` 檢出，前一版僅跑格式與 xref 未跑該閘。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r3/synth.md`（三家 15 條／七群，全採納零駁回）第四次修訂——①`Task 9.2` 範圍納入唯一生產 caller `momentum/Analysis/event_samples/pipeline.py` 並標明「只改被呼叫端不算完成」（前兩次修訂都沒補到核心目標）；②`(3.1)` 由「須先定義可比時點」改為**直接給出可操作定義**：split 側一律由事件級 `decision_at_ms` 決定，各 feature TF 之 cutoff 只用於取特徵、不參與判側 ⇒ 同事件各 feature TF **恆**同側為結構性保證；③**連帶修訂 R2 裁決**——(3.2) 之異側處置由「整事件 purged」改為 **fail-closed `AlignmentViolationError`**（(3.1) 消除「異側屬合法」之前提後，異側即為實作缺陷，purge 會把缺陷偽裝成樣本流失），既有 `interval_crosses_split_boundary` 維持原義不動；④`Task 9.2a` 定案兩道既有重複 guard 改為**複合鍵唯一**判準，並定其須在 `D-002-C3` 同側檢查**之前**執行；⑤§V 補 purged 複合鍵唯一與 `n_event_tf_rows_purged` 斷言、`D-002-C3` 成對斷言改寫為正例（不誤 purge）＋反例（raise）；⑥`Task 9.1` 逐處指名 route `api/routes/case.py:487`／service `case_import_service`／response field `EventAnalyzeResponse.summary`（為 `Dict[str, Any]` ⇒ 新鍵自動穿過但**零型別保證**，驗收須明列鍵名之契約測試）／前端 `EventTablesPanel.tsx:347,361`；⑦`Task 9.5` 指名平行組生成入口 `scripts/freeze_splitunify_golden.py` 之 `_plans()`／`_event_keys()`／`_build_actual()`，`main()` 只增鍵不覆蓋舊錨；⑧`M-SU-D2-19` 改為反向 mutation（survivor 六鍵**被改成含 feature TF** 才是缺陷）、`M-SU-D2-14`／`15` 之應紅測試隨 (3.2) 改為 raise；⑨§N 補 `docs/SPLITUNIFY_TODO.md` §E 之狀態同步時點（三家戳記後、`Task 9.1` 動工前）。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r4/synth.md`（8 條歸五群；7 條採納、1 條駁回）第五次修訂——①🔴 **核心目標第三種不可達形態**：`Task 9.2` 範圍再加 `pipeline.py:723-732` 之四參數閘與 `:711-715` docstring，投影門檻改為 `train_plan`／`test_plan`／`feature_index` 三者同時、`selected_timeframe` 降為可選（原文「四者同時」會讓傳 `None` 在抵達 `build_event_keys` **之前**就 fail-closed），驗收改為**端到端**經 `EventSamplePipeline.run`；②🔴 新增 **`Task 9.2b`**——`(3.1)` 的事件級錨定原本**沒有任何施工落點**（`split_projection.py` 全檔 `decision_at_ms` 命中數為 0，`:530-553` 仍逐列以 `feature_cutoff_ms` 定側），現指名改以 `manifest.table` 之 `decision_at_ms` 每事件定側並廣播，答案窗 purge 改按事件側判定；③§V 之 `Task 9.2` 斷言改為端到端全量列數＋`selected_timeframe=None` 不 raise，原 schema 句改掛 `Task 9.2a`，新增 `Task 9.2b` 之錨定反例；④`(5.2)` 由改前形狀改寫為**落地後契約**（全量複合鍵 producer、兩表含 `feature_timeframe`、`clusters` 維持事件級、側別以 `decision_at_ms` 為錨）；⑤mutation 20 → **23 條**（新增 `M-SU-D2-21` 四參數閘未改、`M-SU-D2-22` 判側改回 `feature_cutoff_ms`；`M-SU-D2-20` 應紅測試改指端到端斷言）；⑥觸及面宣告補列 `Task 9.2b`。**駁回一條**：codex 以「上游收斂檔未蓋章」為由拒審，`AGENTS.md` 第 12 條逐字為「動工前…不動工」而本輪為唯讀審查，且本批 R1／R2／R3 收斂檔之 `RECONCILE-STAMP` 數皆為 0、該家在那三輪分別交付 6／8／11 條實質 finding——同情境前後不一致；該家本輪零實質審查，欠一輪，併入下一輪。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r5/synth.md`（11 條歸八群，**全部採納**）第六次修訂——①🔴 **核心目標第四種不可達形態（三家獨立撞題）**：`Task 9.2` 增逐行指名 `split_projection.py:291-303`——現行 `event_level.merge(..., validate="1:1")` 在全量多 feature TF 必 `MergeError`，且輸出欄 `timeframe` 取自 `event_level`（**觸發** TF），縱放寬 `validate` 兩列也會同值而使複合鍵碰撞；改法＝以 `per_tf` 為行粒度接合、`validate` 改複合鍵判準、**新建** `feature_timeframe` 取自 `per_tf`；另指名 `split_projection.py:271` 之 docstring 舊語意（「恰有一列」）須一併改。②`(5.2)` 之 merge 交叉引用由 `Task 9.2a` 改指 `Task 9.2`（原為懸空引用，9.2a 全文未提該 merge）。③🔴 **`(3.2)` 之 fail-closed 原本同樣「有義務無落點」**——`AlignmentViolationError` 只見於義務／§V／mutation，無任一 Task 改法行；現定於 `Task 9.2b`：複合鍵唯一 guard 之後、寫入 `assignments` 之前，按 `event_id` 分組檢查 `split_label` 唯一，異側即 raise 且訊息含 event_id。④`Task 9.2b` 之側別判準改為**不等式**（`decision_at_ms < test_start_ms`）並對界外 fail-closed——集合成員判定只在特徵網格細於或等於觸發 TF 時成立（R5 實證 1h open 非 4h open 者 15,264／20,352）。⑤mutation 修正條數宣稱並補三條：實列 22 而正文寫 23（沿革「20→23（新增 21、22）」本身即 20+2 之算術錯誤），現為 **25 條**，新增 `M-SU-D2-23`（保留 `1:1` merge 或不寫 `feature_timeframe`）、`M-SU-D2-24`（答案窗仍用逐列 `in_train`）、`M-SU-D2-25`（同側檢查被移到複合鍵 guard 之前）。⑥`Task 9.4` 明列 `baseline` 為例外（其 `n_test` 為樣本數，不得改判事件數），配一事件兩列 fixture。⑦🔴 `Task 9.1` 增生產可達性前置——該 route 之 service 現行永遠走 `run_event_study_only`（`case_import_service.py:1592-1626`），拿不到 canonical universe 也就沒有 `discarded` 來源；須先二擇一（改走可取得 universe 之 producer，或把終端揭露移出事件掃描端）。**指名落點不等於該落點走得到**，此為第四次修訂之缺口。⑧§V 之 `Task 9.2` 斷言標的逐字指定為 `split_plan.assignments`（非 `features`），並要求**替換**既有 `test_splitunify_wiring.py` 之 partial-boundary 參數化案例（現把 `selected_timeframe=None` 視為必須 raise，與新行為互斥），不得只新增而留著舊的。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r6/synth.md`（16 條歸八群，**全部採納**）第七次修訂——①🔴 **我第六次修訂的不等式判準自己引入新缺陷（三家獨立撞題）**：`purge_gap`／`embargo` 造成的隔離帶上，集合成員給 `purged` 而不等式給 `train` ⇒ 切分成員集漂移。`Task 9.2b` 之側別判準改為**三段式且順序不得調換**：先驗位置是否落在隔離帶半開區間 `[split_point, split_point + purge_gap + embargo)`（v7 之寫法，落入即 **fail-closed raise**——🔴 **該處置已於 v8 改為 `purged`**，見下一條沿革）→ 再以不等式定側 → 落在 `train_plan`／`test_plan` 覆蓋區之外同樣 fail-closed。區間定義逐字取自 `split_preview.holdout_test_row_index`。②🔴 **`(3.2)` 只驗 `split_label` 唯一結構上抓不到混態（三家獨立撞題）**：`purged` 僅 `["event_id","reason"]` 兩欄、**無** `split_label` ⇒ 同事件「一列 purged、一列 assignments」不會被發現。增跨表互斥斷言 `set(purged) ∩ set(assignments) == ∅`，並要求答案窗 purge **按事件側一次決定並廣播**（現行 `:540-542` 之逐列 `in_train` 正是混態來源）。③🔴 **`Task 9.3` 對 `feature_materialization` 之改法整段改寫為「維持事件級橫向合併」**：`_combined_columns:22-32` 逐字「多 TF 特徵欄名合併；衝突 ⇒ loud 拒」＝各 TF 欄名互斥是**設計**；照前版改 MultiIndex 會破壞特徵矩陣語意、使 `:138-140` 之 `n_input = per_tf["event_id"].nunique()` 記帳直接 `AssertionError`，且 `baseline:105-120`／`pattern_bridge:122-141` 以事件級 Index 交集會得空集合。④🔴 **`D-002-C5` 之 16 處清單全面重新分類**：前版以「有無 `set_index("event_id")` 之形狀」列入，違反本延伸自己寫下的「不得用形狀規則」；現改為逐處問「這張表的一列代表什麼」，三分類＝(甲) 事件級維持／(乙) 複合鍵須改／(丙) 事件級但需去重取唯一值。⑤🔴 **`Task 9.1` 二擇一定案採 (b)**，原指名之 `api/routes/case.py:487`／`case_import_service`／`EventAnalyzeResponse.summary`／`EventTablesPanel.tsx:347,361` **全部作廢**（字面保留供追溯）——`case_import_service.py:1592-1626` 逐字「事件掃描端恆走 event-study-only」為 SPEC C-0 決議③／R2 之 D1 既有裁定，選 (a) 會推翻本票自己的裁定。⑥`Task 9.5` 之前端 `byEventId` Map 改判為**排除於複合鍵遷移之外**（`eventExport.ts:516-535` 之 record 無 `feature_timeframe`，改鍵會讓匯出附帶欄位全數 miss）。⑦`Task 9.4` 增事件數門檻路徑（`split_projection.py:562`／`:569`／`:716-719`／`per_symbol_n` 皆改 `event_id` 去重計數），並要求**同批補 `insufficient_events_in_test` 之終端揭露**（該旗標不擋分析且前端完全未顯示，只改計數等於修了沒人看得到）。⑧mutation 由 25 → **26 條**（`M-SU-D2-23` 原以 OR 合併兩個獨立缺陷，拆為 `23` 保留 `1:1` 與 `26` 不寫 `feature_timeframe`）。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r7/synth.md`（15 條歸八群，**全部採納**）第八次修訂——①🔴 **`(5.1)` 改了分類卻沒同步施工單（三家獨立撞題，四群同源）**：`Task 9.3` 之 `tables`／`ic_feed`／`counterexample_classifier`／`candidate_ledger` 逐條改為**維持事件級**＋加防誤改回歸；`pattern_bridge` 明列為 (丙) 去重取唯一側；`dedupe` 改為事件級保留＋把保留之 `event_id` **廣播**到 per-TF 列；`(5.3)`／`(5.4)` 之「靜默／須改」舊敘事整段改為**現況描述＋以 `(5.1)` 為準**；`M-SU-D2-11` 改為**反向** mutation（誤改為複合鍵致匯出 extras 靜默變空）。②🔴 **我對 I1 的補救方向錯了**：`Task 9.2b` 之隔離帶處置由 v7 之 **raise** 改回 **`purged`**——`scripts/freeze_splitunify_golden.py:94` 之 fixture 逐字「隔離區 2」且 `gap1`／`gap2` 在 golden 之 `purged` 中，證明「事件落在隔離帶」是**合法且預期**之情形；改 raise 會讓單標的 golden 整批拋錯。③判準改以**時間域**表述（`decision_at_ms <= train_last_ms` ⇒ train／`>= test_start_ms` ⇒ test／之間 ⇒ `purged`／索引界外 ⇒ raise），**不再依賴「映射之位置」**——R7 兩家指出位置映射未定義、同一時刻可合法得出不同位置；`train_last_ms = int(index_ms[train_rows[-1]])` 為一行可得。④🔴 **新增 §G (G-4)，處理 codex 揭出的本質衝突**：`alignment.py:87-93` 允許 `cutoff < decision` ⇒ **換錨本身**就會讓邊界事件改側（`test_start=1000`／`decision=1000`／`cutoff=900` ⇒ 舊 train、新 test），與 §G「單 TF 逐值不變」本質互斥；**採 (G-4a)**：承認事件級錨定為正確語意，單 TF golden 於 `Task 9.2b` 落地後**重凍一次**且僅允許「因換錨而改側」這一種差異，並要求 `decision_at_ms != feature_cutoff_ms` 之邊界 fixture。⑤`baseline` 之 `n_test` 更正為**事件數**（物化既維持事件級，一事件只得一個樣本；v7 之「一事件兩列、`n_test`＝2」作廢）。⑥🔴 **`Task 9.1` 改為具名殘留**：`api/` 對 `EventSamplePipeline.run` 之呼叫點為 **0**，投影路徑尚無生產接線（前批遺留、不在本延伸）⇒ 本延伸只交付 producer 回傳 ＋ `EventSplitPlan.summary` 鍵 ＋ `metadata.split_unify` 欄位（**不得**改動其 reason 封閉值集），終端可見性具名為殘留、理由類別 `blocked-by`；§V 之 `Task 9.1` 三層斷言同步更新，v7 之「API 回應／前端型別」兩層作廢。此缺口我連續兩版指向走不到的地方（v4 事件掃描端、v7 IC 主線），v8 改為誠實具名殘留。
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-review-r8/synth.md`（14 條歸八群；七群採納、一群部分採納）第九次修訂——①🔴 **K1 (G-4a) 不可機械歸因（三家獨立撞題）**：新增 **(G-4c)**——`Task 9.2b` 落地時**同步以 decision-anchor 逐行重寫** `_oracle_membership`（`freeze_splitunify_golden.py:133-138`，其 docstring 已明文「與被測函式無因果關係、不 import 投影」），使 `main()` 每次都驗的 **G-3b** 自動成為「換錨 vs 寫錯」之區分閘，**不新造** `allowed_reanchor_diff` 檔；新增 **(G-4d)** 三項硬性附帶：保留 v8 baseline 不覆寫、`decision == cutoff` 事件零位移、`decision != cutoff` 邊界 fixture 須進 §V 與 mutation。②🔴 **K5 我的時間域判準有邏輯漏洞（codex 獨得）**：四條規則彼此重疊——`index=[100,200,300,400]`／`train_last_ms=200`／`test_start_ms=300` 時 `decision_at_ms=50` 同時命中「train」與「界外 raise」⇒ 新增**步驟 0 前置條件** `index_ms[0] <= decision_at_ms <= index_ms[-1]`，不滿足即 raise，通過後三條才互斥且窮盡。③🔴 **K4 `metadata.split_unify` 是 exact-key 契約（codex 獨得）**：前版把它當「順手擴欄」，實際加鍵須同批改五處（`build_split_unify_disclosure` 現恰回五鍵、`contracts/split_unify.json`、唯一 caller `ic_filter_orchestrator.py:1530-1534`、`tests/api/test_splitunify_disclosure.py:149-151,270-277` 之 exact-key 斷言、前端型別），新鍵型別定為 `Dict[str, int]`；若成本超出 9A 定位應改為只交付前兩層並併入殘留，**不得半套上線**。④🔴 **K2 殘留決策未落地（三家獨立撞題）**：`:140` 標題句刪去「缺任一層即視為 9A 未完成」之 API／前端、`Task 9.4` 之「同批必須補終端揭露」改掛同一殘留、`M-SU-D2-02`／`03` 改指 summary 與 `metadata.split_unify`，並**真的在 §N 新增** `SU-RESID-9A-UI`（此為前版寫了「登記於 §N」卻沒登記之處）。⑤**K3 部分採納**：**駁回**「`blocked-by` 須指名具體阻塞票」之前提——`templates/BRIEF_REVIEW_TEMPLATE.md:71` 之 `reason_code` 閉集為四值且 `R-BRIEF-1` 實例以「現行派工架構」為阻塞對象 ⇒ 本案用 `blocked-by` 合規；採納其成立部分（殘留須真的入 §N）。⑥**K6**：`(6.2)` 之 baseline 例外句更正為「事件級物化前提下 `n_test`＝樣本數＝事件數」，原「複合鍵列數、不得改判為事件數」作廢。⑦**K7**：§V `Task 9.3` 把七條反向 mutation 逐一指到**具名檔**（主委實跑 `ls` 盤定；`07` 與 `11` 須擇檔或新建），並明寫「測試存在前不得宣稱 mutation 網已閉」。⑧**K8**：隨 K2 同批改寫，不再留著逼實作者違反殘留去造 API 測試。
<!-- HISTORY-END -->

## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。
