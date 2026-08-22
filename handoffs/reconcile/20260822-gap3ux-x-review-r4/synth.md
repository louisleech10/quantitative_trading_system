# Reconcile — 20260822-gap3ux-x-review-r4

**來源** 20260822-gap3ux-x-review-r4-codex.md, 20260822-gap3ux-x-review-r4-composer.md, 20260822-gap3ux-x-review-r4-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**輪次事實**：三家全員產出，Verdict 三家一致「需修訂後定版」。findings 19 條
（codex 7／composer 7／grok 5）。R3 群集 A／B 三家一致 CLOSED；C 部分殘留；D／E／F／G 三家一致仍 OPEN。

**收斂趨勢**：R1 24 → R2 7 → R3 18 → R4 19。條數未收斂，但**組成改變**：
R4 之 19 條中，9 條為 R3 遺留 D/E/F/G 之同一病灶（三家獨立命中同一處，非新增 scope），
5 條為**前三輪無人觸及之新面**（去錨定 brief 之直接產物），
2 條為**主委本輪 T-1 改寫自行引入**，1 條為 §D 殘段，1 條為空殼驗證欄，1 條為 §C0↔§N 互斥。
⇒ 判定為**涵蓋面擴大**而非 scope accretion；使用者 2026-08-22 裁定續修並派 R5。

### 群集 A — Task 7.2 機械閘不足（＝R3 遺留 **D**）
**ID**：CODEX-R4-P0-01、COMPOSER-R4-P0-01、COMPOSER-R4-P0-02、GROK-R4-P0-01
**共識**：三家獨立命中同一處，且指出同一組四個子缺陷——①比對基準 `enum`(4) vs `accepted`(3) 未定義
②disabled／hidden 選項可湊數 ③無 UI→`buildEventContractRecords`→落檔之 round-trip
④`decision_offset_bars` 只驗「有控制項且非唯讀」，未驗值真的傳出。
**處置＝ACCEPT 全部四項**：改寫 Task 7.1／7.2／V-11——
比對基準改 `accepted`（＝`enum` 減 `rejected_with_reason` 鍵）；恆拒值以 disabled 呈現且**不計入**
可選集合；oracle 只計 enabled 且可操作之選項；六維度各加一條 round-trip 斷言（含巢狀之
`label_definition.label_return_mode`）；`decision_offset_bars` 加 `min=0` fail-closed 與 payload `=== k`；
新增前置 Task 7.0（先擴 `EventExportOptions` 補齊六維度欄位，再接 UI）。
mutation：呼叫端漏傳 opts ⇒ 必紅；把某維度改回寫死 ⇒ 必紅。

### 群集 B — G-2 canonical serialization 未定義（＝R3 遺留 **F**）
**ID**：CODEX-R4-P1-03、COMPOSER-R4-P1-03、GROK-R4-P0-02
**共識**：§G-2 只凍 fixture／hash／exact return／NaN mask／PIT anchor，未定義序列化規則
⇒ 合法實作可產生不同 hash，G-2 失去鑑別力。grok 另指出**主委本輪之 Task 2.2 覆蓋風險把
「G-2 序列化須涵蓋 filters＋六維度」寫成同步義務，等於對一個不存在的定義下義務**，屬加重。
**處置＝ACCEPT，且承認主委本輪加重**：§G 新增「G-2 canonical serialization」小節，寫死
①輸出欄位白名單 ②event／列／horizon 三層排序 ③重複與非法 horizon policy
④缺 bar 之 omission vs explicit NaN 及其 mask oracle ⑤浮點與 NaN 之序列化表示
⑥`seed`／`n_boot`／統計欄範圍。獨立手算 expected rows 為 oracle（**禁以被測函式自產 golden**）。
Task 2.2 之同步義務改為**引用**該小節而非自行宣告。

### 群集 C — IC 分析頁與 Feature Library `time_range` 對證（＝R3 遺留 **E**；含 §C0↔§N 互斥）
**ID**：CODEX-R4-P1-04、COMPOSER-R4-P1-01、COMPOSER-R4-P1-02、GROK-R4-P0-03
**共識**：三家獨立判定此為**資料正確性缺口**（特徵 run 未涵蓋事件日期仍可送 IC），
**非** GAP-6 之規模效能問題——codex 原話「等待分塊計算不會使日期錯配變安全」。
grok 另指出主委本輪在檔頭寫「E 依 §C0 不得登記為具名殘留」，而 §N 仍將 #8／#10 登記為
`blocked-by` 殘留 ⇒ 同一份 SPEC 自己禁止又自己執行。
**處置＝ACCEPT，本批做，不排 GAP-6**（依 §C0 條文 2：資料正確性類不得降為殘留）：
Phase 7 新增 Task 7.6（IC 頁選批後唯讀揭露該批六維度契約設定，模板同匯出面板）
＋Task 7.7（`RunInfo` 暴露 manifest `time_range`；事件 t0 min/max 與 run 區間以明確
containment policy 對證，不涵蓋 ⇒ fail-closed）。§N 之 #8／#10「未答部分」殘留**撤回**，
改為指向 Task 7.7。小型跨日期 fixture 即可驗，不需等 GAP-6。

### 群集 D — A／B 之 label 來源與機械深度（＝R3 遺留 **G**）
**ID**：CODEX-R4-P1-05、COMPOSER-R4-P1-04、GROK-R4-P1-01
**共識**：`/search` 之 `buildEventContractRecords` 對所有 scenario 都以 t0 `positive_case` 產 `label`、
以 `future_{h}bar_return` 產 `label_value`；接出 A／B 之後契約 scenario 與實際 label 語意漂移，
且 A／B 之機械深度公式未落任何 Task／V-12。
**處置＝ACCEPT，採三家中最嚴之組合**：
①Task 7.1「邊界」明寫：**`/search` 匯出路徑本批只可選 `C`／`two_stage`**，A／B 於該路徑 disabled
並顯示理由「此路徑之 label 由 t0 條件產生，A／B 需獨立 label producer，本批未交付」——
此為**路徑級限制**，非把系統寫死於單一 scenario（CSV 匯入路徑四種全開，使用者自帶 label）。
②機械深度公式 `depth = max(window.horizon_bars, max(lookahead_bars(所有實際引用欄)))`
寫入 Task 1.9／2.1b 與 V-12，並加 A／B／two_stage 之 fixture。

### 群集 E — D-7 L3 與實碼呼叫鏈矛盾（**新面**，前三輪無人觸及）
**ID**：CODEX-R4-P0-02
**內容**：Task 1.12 同時要求「`split_events` 未被呼叫」與「事件研究表仍可產出」，
但 `tables.py:88` 之 `event_forward_return_table` 之 `event_split_plan` 為**必填**、
`pipeline.py:178` 之 `run()` **無條件**呼叫 `split_events` ⇒ 照現有呼叫鏈只能二選一。
**處置＝ACCEPT，採 codex 之第一方案（保住事件研究表）**：Task 1.12 增訂 event-study-only 執行路徑之
契約——不呼叫 `split_events`／`ic_feed`／不進訓練，但能以不依賴 split 之輸入產出報酬表；
驗證須斷言 `split_events` 未被呼叫且表格列數 `== len(horizons)`。
**明文禁止**以空的假 `split_plan` 冒充未執行切分（codex 具名之假綠形態）。

### 群集 F — `control_kind` 未進 manifest（**新面**；全棧接線）
**ID**：CODEX-R4-P1-06
**內容**：Task 7.5 依 `control_kind` 決定全體組可否混算，但 `dedupe.py:112-115` 之 manifest context
只 merge `event_id,symbol,timeframe,label,scenario,direction`，**無 `control_kind`**；
`tables.py:88-100` 亦無原始事件表輸入 ⇒ 實作者只能寫死或讀成 `None`。
**處置＝ACCEPT**：Task 7.5 明定 `control_kind` 之**唯一傳遞點**（manifest context 加欄）、
批內單值／混值規則、`not_computed` 之 schema；以兩種 `control_kind` 之 table golden 驗
正／反／全體三組之 n 與狀態。

### 群集 G — registry 可被改名攻擊繞過（**新面**）
**ID**：CODEX-R4-P1-07
**內容**：L1 registry 以欄名及變體匹配為接受條件；使用者可把實際引用 20 根之自訂欄改名為
已登記之 `future_4bar_return`，使 L2 不觸發而低估 purge。
**處置＝ACCEPT**：Task 1.10 增訂**信任邊界**——系統產生欄（有 producer／manifest provenance）
方可由 L1 直接解析；**外部上傳之 CSV 欄一律不得僅憑欄名進入可切分路徑**，須帶
producer/schema/digest 綁定，否則走 L2 宣告並依 L3 禁 split。
mutation：以改名 CSV（欄名 `future_4bar_return`、實際 20 根）測試 ⇒ 須被擋。

### 群集 H — §D-7 L1 敘事仍寫 `future72_max_*→72`（＝R3 群集 C 之殘段；裁定未同步）
**ID**：GROK-R4-P1-02
**內容**：SPEC L116 仍寫 `future72_max_*→72`（暗示根數＝72），與 Task 1.10「小時命名存
`lookahead_hours`、禁存固定 bar 數；12h⇒6 根、1h⇒72 根」直接矛盾。
主委於檔頭宣稱「C（future72 單位）已修」**不實**。
**處置＝ACCEPT，並同時修工具**：①§D L116 改寫為與 Task 1.10 對齊之敘述
②`spec_ruling_task_sync.sh` 之兩個漏洞一併修——(a) SYNC-FORBID 正規式
`lookahead_bars.*=.*72` 抓不到 `future72_max_*→72`（不含 `lookahead_bars` 字樣）
(b) 該閘**只掃 §P**，§D 內之矛盾完全不在掃描面。
⇒ 擴掃描面至 §D，並改用「小時命名欄後面不得直接接純數字根數」之封閉式規則。

### 群集 I — Task 6.0 驗證欄為空殼 placeholder（**新面**；機檢漏洞）
**ID**：COMPOSER-R4-P2-01
**內容**：Task 6.0 驗證欄字面即 `python3 -c "..."`，無可執行內容；卻因該行含 `==` 與 `.py`
而**通過** `doc_format_precheck.sh` 之「須含具體 token」檢查。
**處置＝ACCEPT，並同時修工具**：①補完整可跑命令（含登記檔路徑與 assert）
②`doc_format_precheck.sh` 增一條：驗證欄不得出現 `-c "..."`／`（略）`／`TODO` 等佔位形態。

---

### 未採納 / 降級
無。19 條全數 ACCEPT，0 條 REJECT、0 條降級為具名殘留（§C0 條文 2 之約束）。

### 主委自承
本輪 19 條中 **2 條由主委 T-1 改寫直接引入**（群集 B 之 Task 2.2 同步義務、群集 C 之檔頭
§C0 宣示與 §N 殘留互斥），另 **1 條為主委不實宣稱**（群集 H 之檔頭「C 已修」）。
主委已於 R4 brief 事前具名標示「該批改寫未經任何審查、與 SPEC 其餘部分同等受審」，
三家皆據以查出——此處紀錄以供日後判斷該作法是否應制度化。

Verdict：需修補後合併（19 條全數 ACCEPT；修補後派 R5 複審，不得逕行 FROZEN）

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R4-P0-01

**斷言**: Task 7.1 與 Task 7.2 要求「UI 選項數 `==` 契約 `enum` 元素數」，但 `control_kind` 契約 `enum` 含 4 值、`accepted` 僅 3 值（`platform_random_bars` 恆拒）；照字面實作要麼 UI 暴露必拒值、要麼 enum 數不一致而機械閘必紅，斷言基準未定義。

**碼證**: Task 7.1 L787-788、Task 7.2 L799-803；`python3 handoffs/20260822-gap3ux-x-review-r4-dims.py --counts` → `control_kind enum_len=4 accepted_len=3`；契約 `event_import_contract.json` L43-48。RECHECK：比對 SPEC Task 7.1/7.2 驗收句 vs dims.py 輸出。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2

[BLOCKING] 信心度=High。失敗：Agent 實作 7.2 時在 enum 全集與 accepted 子集間無法同時滿足 SPEC 與契約。修法：7.1/7.2 明寫比對 `accepted`（或 `enum` 減 `rejected_with_reason` 鍵），UI 對恆拒值顯示 disabled＋契約 doc，且**不計入**可選集合。

---

## COMPOSER-R4-P0-02

**斷言**: Task 7.2／V-11 只驗「契約 enum 集合＝UI 選項集合」，不驗選值綁定到 `buildEventContractRecords` 產出；`EventExportOptions` 缺 `controlKind`／`labelReturnMode`／`decisionOffsetBars`／`counterexampleKind`，現碼仍寫死四欄；disabled 選項可湊齊集合而 payload 未變——重現 B5「介面有、沒傳」病因。

**碼證**: Task 7.2 L799-813；V-11 L870；`eventExport.ts:9-17,92-104`；`page.tsx:522-527`；facts.sh F-06/F-07。RECHECK：`npx vitest run contractEnumWiring` 設計審計——若無「選非預設 ⇒ records[0].<field>===選值」則不足。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；frontend/src/lib/eventExport.ts#b2024ac8970f

[BLOCKING] 信心度=High。失敗：機械閘全綠但匯出仍走寫死預設。修法：每維度一條 round-trip vitest；`EventExportOptions` 補齊六維度；mutation 呼叫端漏傳 opts ⇒ 紅。

---

## COMPOSER-R4-P1-01

**斷言**: Phase 7 全棧接線僅涵蓋 `/search` 與 `/data-preparation`，未要求 IC 分析頁在事件模式下選匯入批後揭露該批契約設定（`scenario`／`control_kind`／`label_return_mode` 等）；`EventImportPicker` 只回傳 t0 秒戳，使用者在不知批次語意下跑條件 IC。

**碼證**: Phase 7 前言 L751-777 盤點表未列 ic-analysis；`EventImportPicker.tsx:9,52` `onPick(importId, icTimestamps)`；`ICConfigPanel.tsx:274-278` 只更新 `event_import_id`／`event_timestamps`；`EventTablesPanel.tsx:118-120` 僅顯示 analyze 回傳 manifest 之 entry/k（非匯入契約全六維度）。RECHECK：讀上述三檔；檔頭遺留項 **E**。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；frontend/src/components/ic-analysis/EventImportPicker.tsx#1cb1e1562456

[MAJOR] 信心度=High。修法：新增 Task 7.6 或擴 Task 7.3 至 ic-analysis（選批後唯讀揭露與匯出面板同模板）。

---

## COMPOSER-R4-P1-02

**斷言**: Feature Library 之 `list_runs`／前端 `RunInfo` 未暴露 manifest `time_range`，IC 分析頁選 Feature run 時無法機械驗證「事件 t0 區間 ⊆ 特徵 run 覆蓋區間」，與 §N #8/#10 未答部分及檔頭遺留 **E** 同型。

**碼證**: `api/models/feature_factory_models.py` L116-133 `RunInfo` 無 `time_range`；`feature_reader.py` L455-472 manifest 含 `time_range`；`ICConfigPanel.tsx:199-226` 選 run 僅 symbol/tf/hash；facts.sh F-13 `grep time_range` 未命中 ic-analysis。RECHECK：`rg time_range frontend/src/components/ic-analysis` → 0。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；api/models/feature_factory_models.py#de451ac20681

[MAJOR] 信心度=High。修法：API 暴露 run `time_range`；事件模式選批後計算 t0 min/max 與 run 區間交集，不覆蓋則 fail-closed 或強警示（不需等大矩陣 GAP-6）。

---

## COMPOSER-R4-P1-03

**斷言**: G-2 仍未定義 canonical serialization（鍵序、omission vs NaN、sha256 欄位白名單），但 Task 2.2 L518-520 已要求「G-2 serialization 須涵蓋 `filters` 與六維度」——Agent 實作 Phase 2 與 Phase 7 會產出不同 golden bytes 且無仲裁規則。

**碼證**: §G L269-273 僅 sha256＋三項；Task 2.2 L518-520；§V G-2 L869；檔頭遺留 **F**。RECHECK：`rg -n "canonical serialization" docs/GAP3_EVENT_UX_SPEC.md` → 僅 Task 2.2 提及、無定義 Task。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2

[MAJOR] 信心度=High。修法：§G 增 serialization 小節或 Task 4.2 子項——鍵序、`filters` 空值、缺 bar omission policy、統計欄是否進 hash。

---

## COMPOSER-R4-P1-04

**斷言**: Task 7.1 將在 `/search` 接出 `scenario` UI，但 `buildEventContractRecords` 不因 A/B 改變 label 來源（仍 t0 `positive_case`＋`future_{h}bar_return`）；契約 doc 稱 A/B「事件在未來」，SPEC 未寫「search 路徑 scenario 僅 metadata」或禁止選 A/B，造成契約 scenario 與實際 label 語意漂移。

**碼證**: `eventExport.ts:75-77,95,102-104`；契約 `scenario` doc（facts.sh F-02）；Task 7.1 L783-797 無語意邊界；檔頭遺留 **G**。RECHECK：讀 `buildEventContractRecords`；D-7 表 L131-135。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；frontend/src/lib/eventExport.ts#b2024ac8970f

[MAJOR] 信心度=High。修法：Task 7.1「邊界」明寫 search 路徑僅 C／two_stage 可選，或 A/B 須改 label 組裝並加 vitest。

---

## COMPOSER-R4-P2-01

**斷言**: Task 6.0 之驗證欄寫 `python3 -c "..."` 為不可執行 placeholder，屬 §2 獵空殼——Agent 無機械命令可跑，與 §V「每 Task 可證偽」紀律衝突。

**碼證**: Task 6.0 L696「驗證：`python3 -c "..."` 斷言該 reason 存在於登記檔」；同 Task 其他欄（內容／存活至）有實質。RECHECK：`nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '693,700p'`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2

[MINOR] 信心度=High。修法：替換為完整 `python3 -c "import json;…assert 'feature_count_exceeds_cap' in …"` 與登記檔路徑。

---

## GROK-R4-P0-01

**斷言**: Task 7.2／V-11／Task 7.1 驗收仍以「UI 選項集合 == 契約 enum 集合」為機械閘，可被 disabled／hidden 選項湊過；且 `control_kind` 契約 `enum` 長度 4、`accepted` 長度 3（`platform_random_bars` 恆拒），兩基準不相等使斷言定義不明；另缺 UI→`buildEventContractRecords`→落檔之 round-trip，`decision_offset_bars` 僅驗「有輸入且非唯讀」。

**碼證**: SPEC Task 7.2 L799-813、V-11 L870 仍寫 `uiOptions.length === contractEnum.length` 與 Set 相等，無 enabled-only／accepted／payload 斷言；`python3 handoffs/20260822-gap3ux-x-review-r4-dims.py --counts` → `control_kind enum_len=4 accepted_len=3`；`eventExport.ts:9-17` 之 `EventExportOptions` 無 `controlKind`／`labelReturnMode`／`decisionOffsetBars`／`counterexampleKind`，函式內 `:92/:102/:104` 仍寫死；`search/page.tsx:522-527` 呼叫未傳六維度。RECHECK：重跑 dims.py --counts；`sed -n '799,813p;870p' docs/GAP3_EVENT_UX_SPEC.md`；`sed -n '9,17p;88,109p' frontend/src/lib/eventExport.ts`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；momentum/Analysis/contracts/event_import_contract.json#7111b2d7060e；frontend/src/lib/eventExport.ts#b2024ac8970f；frontend/src/app/search/page.tsx#4b967e3fb875

[BLOCKING] 信心度=High。會怎麼失敗：Agent 照字面做——(a) UI 放 4 個 control_kind（含必拒值）或 (b) 只放 accepted 3 個而與 enum Set 斷言衝突；(c) DOM 含 disabled 湊齊 enum 字面但使用者選不到；(d) 有 `<input>` 未綁 opts 仍過閘，匯出繼續寫死。修法：比對基準改 `accepted`／selectable 集合；禁止 disabled 計入；每維度 sentinel round-trip（含 `label_definition.label_return_mode`）；`decision_offset_bars` 驗 min=0 與 payload `=== k`；先擴 `EventExportOptions` 再接 UI。＝R3 遺留 **D**／CODEX-R3-P0-03／COMPOSER-R3-P1-04 未修。

---

## GROK-R4-P0-02

**斷言**: G-2 仍未定義 canonical serialization／獨立 oracle 形狀（列序、horizon 透傳／重複／非法、缺 bar 之 omission vs NaN、統計欄清單、seed／n_boot），不足以位元組級證偽；同時 Task 2.2 新寫之覆蓋風險把「G-2 canonical serialization 須涵蓋 filters＋六維度鍵排序與空值」寫成同步義務，使 Phase 2 Agent 依賴一個尚不存在的定義——屬 §C0 禁止之以「留實作」繞過數值正確性。

**碼證**: §G-2 L269-273 僅「sha256＋exact return／NaN mask／PIT anchor」三項；全文除檔頭 F 與 Task 2.2 L518-520 外無 serialization 規範；`event_forward_return_table`（`tables.py:88+`）產出多於三項之欄位且 docstring 採缺 bar 排除（omission）。RECHECK：`sed -n '269,273p;516,520p' docs/GAP3_EVENT_UX_SPEC.md`；`sed -n '88,100p' momentum/Analysis/event_samples/tables.py`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；momentum/Analysis/event_samples/tables.py#e9856a0caa68

[BLOCKING] 信心度=High。會怎麼失敗：Frozen 後首次凍 golden 時合法實作可產生不同 hash；Phase 2 與 Phase 7 序列化點不一致使 G-2 假紅或假綠。修法：在 §G-2／§V 寫死 normalization（key 序、空值、列／event／horizon 序）、獨立手算 fixture、omission 語意、stats 欄白名單、seed／n_boot；Task 2.2 之同步義務改引用該定義。＝R3 遺留 **F**／GROK-R3-P1-04／CODEX-R3-P1-04／COMPOSER-R3-P2-02；本輪覆蓋風險改寫**加重**而非緩解。

---

## GROK-R4-P0-03

**斷言**: 檔頭依 §C0 宣示遺留 E（IC 分析頁與 Feature Library `time_range` 對證）屬正確性範疇「不得登記為具名殘留放行」，但 §N 仍將使用者問題 #8／#10（事件日期須被 Feature Library 涵蓋）登記為 `blocked-by` GAP-6 之具名殘留；Phase 7 亦無任何 Task 做 IC 頁批次 metadata 揭露或 `run.time_range ∩ 事件 t0` 對證——規格同時禁止殘留又執行殘留。

**碼證**: SPEC L19-24（E 不得殘留）vs L897（#8／#10 具名殘留）；Phase 7 L751-848 僅 `/search`＋`/data-preparation` 六維度，無 IC／FL；`EventImportPicker.tsx:9,47,52` 之 `onPick(importId, icTimestamps)` 只交時間戳；`feature_reader.py` 已暴露 manifest `time_range`；`api/models/ic_models.py` 無 coverage 欄。RECHECK：`sed -n '19,24p;897p' docs/GAP3_EVENT_UX_SPEC.md`；`grep -n 'onPick\|time_range' frontend/src/components/ic-analysis/EventImportPicker.tsx momentum/FeatureEngineering/feature_reader.py | head`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；frontend/src/components/ic-analysis/EventImportPicker.tsx#1cb1e1562456；momentum/FeatureEngineering/feature_reader.py#f03b11fe7a8b；api/models/ic_models.py#fbc974fb7fa4

[BLOCKING] 信心度=High。會怎麼失敗：特徵 run 未涵蓋事件日期仍可送 IC；使用者在不知批次 scenario／進場價語意下讀條件 IC；審查層因「§N 已登記」而放行，直接違反 §C0 條文 2。修法：二選一且寫死——(1) 本批 Phase 7 增 Task：IC 頁揭露批次契約欄＋`time_range` 交集顯示／不足則 fail-closed（小 fixture 即可，**不需**等 GAP-6 分塊）；並從 §N 撤回 #8／#10 之「未答部分」或改為本批 Task 引用；(2) 若使用者明示本批不做，則須改檔頭／§C0 適用聲明（不可一邊 C0 禁止殘留一邊 §N 殘留）。＝R3 遺留 **E**／CODEX-R3-P1-05／COMPOSER-R3-P2-01。

---

## GROK-R4-P1-01

**斷言**: A／B 預測型之 lookahead 深度仍只有表格敘事「≥ 事件之時間距離」，SPEC 未把機械式 `depth = max(window.horizon_bars, max(lookahead_bars(引用欄)), 兩段最大)` 寫進任一 Task 或 V-12；且接出 `scenario=A/B` 後 label 來源仍為 `positive_case`＋`future_{h}bar_return`（與 C 相同），無 Task 定義選 A／B 時 UI／payload／dedupe 語意應如何變——「label 來源不變」會與契約 scenario 語意漂移。

**碼證**: SPEC L131-144 通則＋表；V-12 L871 僅 `max(lookahead_bars)` 三組 fixture，無 scenario 分支；Task 7.1／7.3 接 scenario 但不改 label 構造；`eventExport.ts:76-85,95`：`label` 來自 `positive_case`，`label_value` 來自 `future_{horizon}bar_return`，`scenario` 僅 opts 預設 `'C'`。RECHECK：`sed -n '131,144p;871p' docs/GAP3_EVENT_UX_SPEC.md`；`sed -n '76,105p' frontend/src/lib/eventExport.ts`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；frontend/src/lib/eventExport.ts#b2024ac8970f

[MAJOR] 信心度=High。會怎麼失敗：Agent 對 A／B 只改 scenario 字面、purge 仍偏小；或使用者以為選 A／B 改變了「事件在未來」之標籤構造，實際 label 仍是 t0 搜尋之 positive_case。修法：公式入 Task 1.9／2.1b／V-12；明示本批 A／B＝「同一標籤構造＋不同契約／dedupe 路徑」或另寫 A／B 標籤構造變更（若屬本批）。＝R3 遺留 **G**／GROK-R3-P1-02／COMPOSER-R3-P2-03。

---

## GROK-R4-P1-02

**斷言**: 群集 C 宣稱「future72 單位已修」，但 §D-7 L1 範例仍寫 `future72_max_*→72`（暗示根數＝72），與 Task 1.10「小時命名存 `lookahead_hours`、禁存固定 bar 數；12h⇒6 根」直接矛盾；Agent 若以 §D 為意圖來源會重引入 R3 P0 級單位錯。

**碼證**: SPEC L116 `future72_max_*→72` vs Task 1.10 L388-402（`lookahead_hours == 72` 且無 `lookahead_bars` 鍵；12h→6／1h→72）；檔頭 L18-19 稱 C 已修。RECHECK：`sed -n '116p;388,402p' docs/GAP3_EVENT_UX_SPEC.md`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2

[MAJOR] 信心度=High。會怎麼失敗：§D 與 §P 雙源；實作者抄 §D 範例寫死 72 根。修法：§D L116 改為「`future72_max_*`→`lookahead_hours=72`（根數＝hours÷TF，禁止寫死 bars=72）」與 Task 1.10 對齊；必要時擴 SYNC-FORBID 涵蓋 §D。＝GROK-R3-P1-01 殘段。

---

