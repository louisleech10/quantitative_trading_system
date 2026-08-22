# GAP-3 事件型 UAT 缺口修補 SPEC — 對抗審 R4（GROK）

TASK_ID: 20260822-GAP3UX-X-REVIEW-R4  
FAMILY: GROK  
brief-kind: review  
brief: `handoffs/20260822-gap3ux-x-review-r4-brief.md`  
標的: `docs/GAP3_EVENT_UX_SPEC.md`  
sha256（開工第一件事重跑）: `3bc04411cdf2d1663626d0128e7d462c03f3228a9d1d3ee86f0cd3854dea58b9`（與 brief 鎖定值相符；900 行）  
SCOPE: review-only；禁改碼、禁改 SPEC。

## Verdict：需修訂後定版

R3 群集 **A／B CLOSED**（Task 4.1b 文案／Task 1.10–1.12＋2.1b）；**C 僅 Task 層 CLOSED、§D 敘事殘留 OPEN**。  
R3 遺留 **D／E／F／G 四條仍 OPEN**——Task 7.2／§G-2／Phase 7 對 IC×FL／A·B 機械式深度皆未補到可 Frozen 門檻；且檔頭依 §C0 宣示 E「不得具名殘留」，§N 卻仍把 #8／#10 登記為具名殘留——§C0 自相矛盾。  
本輪覆蓋風險改寫大多可執行；**Task 2.2 覆蓋風險把未定義之 G-2 canonical serialization 寫成同步義務**，加重 F。修完 D／E／F／G（含 §C0↔§N）後方可 Frozen。

---

## 0. 標的指紋與 fact 重跑

| 項 | 結果 |
|---|---|
| `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md` | `3bc04411cdf2…dea58b9`＝brief 鎖定值 |
| `wc -l` | 900 |
| `bash handoffs/20260822-gap3ux-x-review-r4-facts.sh` | rc_all=0；與 `facts.out` 僅 HEAD（`4e2871cd`→`01b8e9ef`）差，SPEC 指紋不變 |
| `python3 handoffs/20260822-gap3ux-x-review-r4-dims.py [--counts]` | 六維度三層級；control_kind enum_len=4 accepted_len=3 |
| `grep -c "覆蓋風險：無"` / `^- 覆蓋風險` | **0**／**38** |
| 三支機械閘 | doc_format／ruling_sync／quant_standard 皆 rc=0 |

---

## 1. R3 十八條 CLOSED／OPEN

### 我方 GROK-R3

| R3 ID | 本輪 | 碼證 |
|---|---|---|
| **GROK-R3-P0-01** L1 registry／Task 2.1b | **CLOSED** | Task 1.10／1.11／1.12 已落；Task 2.1b 改讀 registry＋含 drawdown／future72_* |
| **GROK-R3-P0-02** Task 4.1b 寫死 C 文案 | **CLOSED** | Task 4.1b 改動態四段；`grep` 固定「正反例由 t0」僅餘 SYNC-FORBID／禁令句 |
| **GROK-R3-P1-01** future72 單位 | **PARTIAL → 見 GROK-R4-P1-02** | Task 1.10 已改 `lookahead_hours`；§D L116 仍寫 `future72_max_*→72` |
| **GROK-R3-P1-02** A／B 機械深度 | **OPEN** | 見 GROK-R4-P1-01（＝遺留 G） |
| **GROK-R3-P1-03** Task 7.2 弱閘／accepted | **OPEN** | 見 GROK-R4-P0-01（＝遺留 D） |
| **GROK-R3-P1-04** G-2 oracle／serialization | **OPEN** | 見 GROK-R4-P0-02（＝遺留 F） |

### 他家複核

| R3 ID | 複核 | 說明 |
|---|---|---|
| CODEX-R3-P0-01 | **同意 CLOSED** | 與 GROK-P0-01 同根；L1/L2/L3 已有 Task |
| CODEX-R3-P0-02 | **同意 CLOSED** | 與 GROK-P0-02 同根 |
| CODEX-R3-P0-03 | **同意 OPEN** | ＝D；見 GROK-R4-P0-01 |
| CODEX-R3-P1-04 | **同意 OPEN** | ＝F；見 GROK-R4-P0-02 |
| CODEX-R3-P1-05 | **同意 OPEN** | ＝E；見 GROK-R4-P0-03；並加 §C0↔§N 矛盾 |
| COMPOSER-R3-P1-01／P1-02 | **同意 CLOSED** | Task 2.1b＋1.10 已補 |
| COMPOSER-R3-P1-03 | **同意 CLOSED** | 同 4.1b |
| COMPOSER-R3-P1-04 | **同意 OPEN** | 同 D／accepted |
| COMPOSER-R3-P2-01 | **同意 OPEN** | 併入 E（IC 頁不揭露批次契約） |
| COMPOSER-R3-P2-02 | **同意 OPEN** | 同 F |
| COMPOSER-R3-P2-03 | **同意 OPEN** | 併入 G（選 A／B 時 label 來源不變） |

---

## 2. 全棧三欄稽核（涵蓋面 1；事件型＋IC＋FL）

| 能力 | 後端 code | 前端 UI | wiring（呼叫端真傳） | 判定 |
|---|---|---|---|---|
| 六維度→事件匯出 | ✅ 契約＋validator | ❌ 無選項（寫死） | ❌ `page.tsx:522-527` 未傳 opts；`EventExportOptions` 僅有 `scenario?`／`entryPriceSemantic?`，缺另四維 | Phase 7 已盤；閘仍弱（D） |
| `counterexample_kind` | ✅ optional_fields | ❌ | ❌ `eventExport.ts` 字面 **0** 命中 | 同上 |
| CSV 匯入新端點 | ❌ 待 Task 1.2 | ❌ 待 1.5 | — | Phase 1 規劃完整 |
| 事件批次刪除 | ❌ 待 3.1 | ❌ 待 3.2 | — | Phase 3 規劃完整 |
| IC 止血閘 feature_count | ❌ 待 6.1 | 部分（進度 UI 待 6.3） | — | Phase 6 規劃完整 |
| IC 分析頁×事件批 metadata | 後端批次有契約欄；`ic_models` 無 coverage／六維度 payload | `EventImportPicker` 只 `onPick(importId, timestamps[])` | ❌ 只傳 t0 時間戳，不傳 scenario／entry／lookahead | **E OPEN** |
| Feature Library `time_range` vs 事件 t0 | ✅ `feature_reader.py` manifest 含 `time_range` | result／charts 顯示 metadata | ❌ **無**「run.time_range ∩ 事件 t0」對證／阻擋 Task | **E OPEN**；§N 卻當具名殘留 |

assumed「Phase 7 六維度已是完整清單」：**事件匯出主線成立**；**IC×FL 日期涵蓋同型漏接仍在**（與 R3 CODEX-P1-05／COMPOSER-P2-01 一致）。

---

## 3. R3 遺留 D／E／F／G 是否足夠（§C0 門檻＝正確性不得降殘留）

| 代號 | 現行處置 | 足夠？ |
|---|---|---|
| **D** | 檔頭列未決；Task 7.2／V-11 正文**未改**（仍 `uiOptions.length === contractEnum.length`＋Set 相等；offset＝「有輸入且非唯讀」） | **不足** → P0 |
| **E** | 檔頭列未決且宣示不得殘留；§N #8／#10 仍 `blocked-by` GAP-6 具名殘留；Phase 7 無 IC／FL Task | **不足＋§C0 自相矛盾** → P0 |
| **F** | §G-2 仍只有 sha256＋三項；無 canonical serialization；Task 2.2 覆蓋風險卻要求 G-2 定義之 | **不足** → P0 |
| **G** | 通則敘事在；無 `depth = max(...)` 入 Task／V-12；選 A／B 不改 label 來源無 Task | **不足** → P1 |

---

## 4. §C0 遵守稽核

- 正面：`quant_standard_check.sh` rc=0；檔頭誠實列 D–G 未決；禁止「95% 就收」有明文。
- 違規／空洞：
  1. **E 一邊說不得殘留、一邊在 §N 殘留**（GROK-R4-P0-03）。
  2. **F 實質仍是「序列化留實作」**——§G 未補 oracle 形狀；僅在檔頭承認未決，Task／§V 無對應補丁（GROK-R4-P0-02）。
  3. 放水同義語掃描通過 ≠ 結構性繞過已消除。

---

## 5. §P 38 Task／覆蓋風險改寫（抽樣＋風險點）

- 38 條皆有五欄；「覆蓋風險：無」＝0。多數改寫含「為何不被覆蓋」＋「須同步」——可執行。
- **新驗收斷言**：Task 1.12 ④ reason 契約＋禁硬編碼；Task 3.1 落檔殘留 `== 0`；Task 7.1「全預設 ⇒ G-2 byte 不變」——方向正確、可證偽。
- **改寫引入之新洞**：Task 2.2 覆蓋風險要求「G-2 canonical serialization 須同時涵蓋 `filters` 與六維度鍵之排序與空值表示」——但 G-2 **尚未定義**該 serialization ⇒ Agent 無法實作該同步義務（併 F）。
- Task 1.3「decision_offset／entry_price 若改 t0 取值須重跑 event_id 集合相等」——合理防漂。
- Task 編號 1.10–1.12 插在 1.9 之前：可讀性差，非正確性阻塞（Suggestions）。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 |
|---|---|
| fact-verified F-01..F-14（可重跑） | **成立**（本輪重跑 rc=0；指紋相符） |
| assumed：lookahead 通則對四 scenario 皆成立 | **語意成立；機械式仍未入 Task**（G OPEN） |
| assumed：D-7 三層足以擋洩漏 | **方向夠；CSV 改名偽造 L1 仍為已知殘差**（R3 已述；本輪未恶化） |
| assumed：Phase 7 六維度＝完整接線清單 | **不成立**（IC×FL 同型漏） |
| assumed：新三條驗收斷言寫法正確 | **大致成立**；但 7.1 golden 回歸依賴未定義之 G-2 serialization |
| assumed：26 條覆蓋風險與既有條文無矛盾 | **有一處矛盾**（Task 2.2 ↔ 未定義 G-2） |
| assumed：Phase 相依聲明正確 | **抽樣成立**（Phase 2 不依賴 1.2；Phase 4 不依賴 Phase 1） |

---

## §1 十一類摘要

1. 矛盾/互斥：§C0 檔頭 vs §N 對 E；§D L116 vs Task 1.10；Task 2.2 vs 未定義 G-2；Task 7.1/7.2 UI==enum vs accepted(3)  
2. 漏項/E2E：D 缺透傳；E 缺 IC／FL Task；G 缺機械公式與 A／B label 契約  
3. 不可測驗收：G-2；decision_offset 弱閘  
4. 可疑 quant：§D future72→72 敘事殘留；A／B 深度不可執行  
5. 過度工程：無  
6. OOM：Phase 6 規劃足夠（本輪非焦點）  
7. Cache：無新增問題  
8. API/型別：opts 介面仍缺四維；control_kind accepted 未入驗收  
9. 測試品質：7.2 可被 disabled 假綠（已知）  
10. Agent 可執行性：F／G 不足；D 字面可執行但會做出錯的閘  
11. 短命工：4.1b→7.3 刻意覆蓋已標明；6.x→GAP-6 已標明  

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

## Suggestions（非 Blocking）

- Task 編號順序 1.10→1.11→1.12→1.9：建議重排或加「前置依賴」導讀，避免 Agent 漏讀 1.10。
- 檔頭 D 條把 accepted 問題寫成 `counterexample_kind_not_importable` 字樣——實際恆拒的是 `platform_random_bars`；屬文件筆誤，修 D 時一併改。
- `direction` 仍由條件推斷、頁面未傳 `opts.direction`：非六維度，建議 Phase 7 可見（不升 P0）。

---

ASSUMPTIONS_VERIFIED: SPEC sha256＝brief 鎖定值；facts.sh 14 條 rc_all=0；dims 三層級＋control_kind 4/3；覆蓋風險「無」＝0、欄＝38；三機械閘 rc=0；R3 A/B 正文已改、D/E/F/G 正文未足；EventImportPicker 只傳 timestamps；eventExport opts 缺四維；§D L116 與 Task 1.10 矛盾；§C0 檔頭 vs §N #8/#10 矛盾。  
TESTS_RUN: `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md`；`bash handoffs/20260822-gap3ux-x-review-r4-facts.sh` → rc_all=0；`python3 handoffs/20260822-gap3ux-x-review-r4-dims.py{, --counts}` → rc=0；`bash scripts/doc_format_precheck.sh`／`spec_ruling_task_sync.sh`／`quant_standard_check.sh` → rc=0；`grep -c "覆蓋風險：無"`→0、`^- 覆蓋風險`→38；completeness 見收尾。未跑產品 pytest／vitest（review-only）。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（未改產品／SPEC）  
OUTPUT: handoffs/20260822-gap3ux-x-review-r4-grok.md

STATUS: DONE
