# GAP-3 事件型 UAT 缺口修補 — SPEC

<!-- SYNC-FORBID: 正反例由 \*\*t0 條件\*\*決定 -->
<!-- SYNC-FORBID: 掃描條件引用之 `future_\{N\}bar_return` 欄 -->
<!-- SYNC-FORBID: lookahead_bars.*=.*72 -->
<!-- SYNC-FORBID: future[0-9]+_[^→]*→[[:space:]]*[0-9] -->
<!-- SYNC-FORBID: contractAccepted -->
<!-- 上列由 `scripts/spec_ruling_task_sync.sh` 機械強制：
     ①每條 `**D-<n>` 裁定須被 §P 至少一個 Task 引用（否則只停在敘述層）
     ②禁用語不得在 §P 殘留。
     出處＝2026-08-22 R3 之三條 P0（Task 4.1b 寫死 scenario 專屬文案／Task 2.1b 未同步 D-7 L1／
     Task 1.10 把 future72 之 72 誤當根數），皆為「改 §D 未同步 §P」之同一病根，
     `feedback_cross_reference_sync` 載此類錯已犯 7 次 ⇒ 改以閘門而非紀律。 -->

出處：使用者 2026-08-22 跑完 UAT B1–B13 後提出的 10 條問題。
本 SPEC 涵蓋**事件型**那批（#0/#1/#2/#3/#4/#5/#6 ＋ #9a 止血閘）。
#7 為回答性問題（已答，見 §N）；**#8/#10 之殘留於 R4 撤回，改為本批 Task 7.7**（見 §N 與下表群集 C）；
#9b 規模防護本體排入 GAP-6。

**版本**：R8-arch（收斂履歷：R1 24 → R2 7 → R3 18 → R4 19 → R5 13 → R6 15 → R7 12 → R8 17 條 findings）。
**狀態：未 FROZEN**（待 R9 對抗審；FROZEN 之四條件見 `docs/GAP3_EVENT_UX_ROLE_CARD.md`，本檔不重述）。

🔴 **本版之產生方式與前五輪不同（使用者 2026-08-22 裁定）**：
R5 之 13 條中**有 5 條為主委 R4 修訂自行引入**（R4 亦有 3 條），共 8 條形態一致——
**改了 §P 之權威定義，未同步 §V 之複述**。出錯的是「主委選擇怎麼修」這一步。
使用者逐字裁定：「乾脆你直接問委員要怎麼修，然後照著做?」
⇒ 開 consult 輪（`handoffs/20260822-gap3ux-x-consult-r2-brief.md`），
三家各交 10–11 條**四欄修法**（改哪裡／改成什麼成品文字／怎麼驗／**必須同步哪些其他位置**），
主委**照抄實作、不自行發揮**；三家 Verdict 一致「照抄後進 R6」。
**A-6′ 已於 R8 經使用者 2026-08-23 逐字裁定確認**（見 §A）；FROZEN 之其餘條件見角色卡。

**R5 十一群集之落點**（reconcile：`handoffs/reconcile/20260822-gap3ux-x-review-r5/synth.md`）：

| 群集 | 內容 | 落點 |
|---|---|---|
| A | §V 複述 §P 之斷言（V-11 等六列雙源） | **§V 書寫規則**＋六列引用化＋Task 7.2 標題與覆蓋風險＋新閘 `spec_v_task_ref_check.sh` |
| B | G-2 無 dict→bytes encoder | **§G S-9** |
| C | 三組報酬表與 S-1 八鍵互斥 | **§G S-1a／S-7a**＋Task 7.5 輸出形狀 |
| D | `horizon_bars→ms` 之 tf 來源未定 | **Task 7.7 ①②**（逐列取事件列 tf；`TIMEFRAME_SECONDS`） |
| E | Task 7.7 左界未扣 `decision_offset_bars` | **Task 7.7 ③**（左界改 `decision_at_ms`） |
| F | 匯出固定取 `future_${h}bar_return` 與宣告不符 | **Phase 7 前言 F-1..F-5**＋Task 7.0 ⑦⑧ |
| G | `counterexample_kind` 為逐列選填欄 | **維度由六改五**＋逐列映射規則 |
| H | `/search` 放行 `two_stage` 但無 producer | **Task 7.1 邊界**＋`pathExclusions` 擴充 |
| I | `mixed_control_kind_in_batch` 未登記契約 | **Task 7.5**（`ic_report_contract.json` 之 `event_return_table`） |
| J | `facts.sh` 未開 pipefail ⇒ 假 rc=0 | 主委直接修（工具 bug，非 SPEC 判斷） |
| K | §A 之 A-6 自相矛盾 | **§A**（A-6 待白話閘；確認前不得 FROZEN）。🔴 **R8 已結案**：A-6 之前提被使用者裁定推翻而整條作廢，取代者 A-6′ 已確認，見 §A |

**三家分歧之裁決點（全部記錄，不隱藏）**：
S-9 尾端 newline 禁用（2:1）／S-9 章節編號（2:1）／`by_label` 鍵名逐鍵取多數
（`positive`／`negative` 2:1、`all` 2:1）／新閘命名採 composer／
群集 K 之嚴格度採 composer。
**唯二不投票者**：①`RunInfo.time_range` 型別依**實碼**裁 `str|None`
（grok 之 `int|None` 與 `_resolve_l7_v2_time_range` 之簽章不符）
②Task 7.7 ④之 ISO 字串 parse 規則為**主委補充**（三家皆未觸及該層），已具名標為待 R6 裁定。

🔴 **主委自承（保留為警示，不得刪）**：R4 19 條中 3 條、R5 13 條中 5 條由主委修訂自行引入，
另 R3→R4 有 1 條不實宣稱。三家能抓到，是因為 brief **事前具名標示「該批改寫未經任何審查」**。

**R4 十九條之落點**（reconcile：`handoffs/reconcile/20260822-gap3ux-x-review-r4/synth.md`）：

| 群集 | 內容 | 落點 |
|---|---|---|
| A（＝R3 遺留 **D**） | Task 7.2 只驗集合、可被 disabled 湊過、無 round-trip；`enum`(4) vs `accepted`(3) 基準不明 | 新增 **Task 7.0**（先擴 `EventExportOptions`）；改寫 **Task 7.1／7.2** 為三層驗證，比對基準＝`selectable(path,dim)`；**V-11 改為純引用**（R5 consult 裁，見 §V 書寫規則） |
| B（＝R3 遺留 **F**） | G-2 canonical serialization 未定義 ⇒ 不可位元組級證偽 | **§G 新增 S-1..S-8**；Task 2.2 改為純引用 |
| C（＝R3 遺留 **E**） | IC 分析頁與 Feature Library `time_range` 對證缺口；且檔頭禁殘留而 §N 仍殘留 | 新增 **Task 7.6／7.7**、**V-14／V-15**；**§N 之 #8／#10 殘留撤回** |
| D（＝R3 遺留 **G**） | A／B 之 label 來源與機械深度未定義 | **Task 7.1「邊界」**加路徑級限制（`/search` 本批只開 C／two_stage）；**深度公式**落 Task 2.1b，由 1.9／V-12 引用 |
| E（**新面**） | D-7 L3 之「不進 split 但仍可產表」與實碼呼叫鏈矛盾 | **Task 1.12** 增 `run_event_study_only()` 契約＋`ci` 標 unavailable |
| F（**新面**） | `control_kind` 未進 manifest ⇒ Task 7.5 分組讀不到 | **Task 7.5** 明定唯一傳遞點＋混值 fail-closed＋`not_computed` schema |
| G（**新面**） | registry 可被改名攻擊繞過 | **Task 1.10** 增信任邊界（系統產生欄 vs 外部上傳欄）＋改名 mutation |
| H（R3 群集 C 之殘段） | R3 版 §D-7 L1 原寫 `future72_max_*→72`（暗示根數＝72），與 Task 1.10 之「存 `lookahead_hours`、12h⇒6 根」矛盾 | **§D-7 L1 已改寫**；新增第 3 條 `SYNC-FORBID` 涵蓋該形態 |
| I（**新面**） | Task 6.0 驗證欄為 `python3 -c "..."` 佔位卻通過機檢 | **Task 6.0 補完整命令**；`doc_format_precheck.sh` 增佔位形態偵測 |

🔴 **主委自承（保留為警示，不得刪）**：R4 十九條中，**2 條由主委 R4 前之改寫直接引入**
（群集 B 之 Task 2.2 對不存在的定義下同步義務；群集 C 之檔頭禁殘留與 §N 殘留互斥），
另 **1 條為主委不實宣稱**——R3 版檔頭寫「C（future72 單位）已修」，而 §D-7 L1 之敘事**未改**。
三家皆據主委事前於 R4 brief 具名標示之「該批改寫未經任何審查」查出。

---

## §RISK 風險分級

RISK-HIT: a,b

- **(a) 數值/資料品質**：Task 1.2 讓使用者指定「哪一欄是 label」。
  **三家 R1 一致指出：`label` 的語意正確性在機械上不可證明**——使用者若對映到另一個
  恰好也是二元的欄，所有 fail-closed 檢查全過，而條件 IC／正反例辨別表**靜默錯誤**。
  ⇒ §D-1 之處置：把它明確定義為 **user assertion（使用者聲明）而非系統保證**，
  並以 provenance／預覽確認／可疑欄警示三層降低誤指機率。
- **(b) 跨模組/共用路徑**：動 `api/routes/case.py`、`frontend/src/`、
  `momentum/Analysis/event_samples/`，跨 api↔momentum↔frontend 三層。
- **非 (c)**：各 Phase 獨立 commit，可逐一 revert。
- **非 (d)**：不動回測與 ML 正確性路徑。

---

## §D R1 六條 P0 之裁定（本版新增；R2 起為 SPEC 的一部分）

**D-1（CODEX-R1-P0-01 ＋ COMPOSER-R1-P1-01 ＋ GROK-R1-P1-01，三家全員）
`label` 正確性不可機械證明 ⇒ 改以 user assertion 定義**
接受。`label` 之語意由使用者聲明，系統**不宣稱**其正確，只保證：
① 照抄使用者指定之欄（V-1）②記錄對映 provenance 使日後可追（Task 1.6）
③ 送出前強制預覽確認（Task 1.5）④對「多個欄都是二元」時出示警示清單（Task 1.7）。
SPEC 與 UI 文案一律用「你聲明的正反例標記」，**禁用「label 正確」字樣**。

**D-2（COMPOSER-R1-P0-02 ＋ GROK-R1-P0-01，兩家獨立命中）
`event_id` 必須與既有匯出一致，不得另發明**
接受，且我的原設計是錯的。現行 `frontend/src/lib/eventExport.ts:88` 為
`` `${symbol}:${timeframe}:${t0}` ``（含 timeframe、不含 label、非 sha256）。
我原寫 `sha256(symbol,t0,label)[:16]` 會使**同一事件經 Excel 回灌後 id 改變**，
直接打斷使用者「匯出→Excel 細篩→CSV 回灌」的閉環，且使我自訂的 V-3 在真實對照下不可達。
⇒ CSV 路徑**沿用同一 canonical**，見 Task 1.3。

**D-3（R8 架構調整；使用者 2026-08-23 提出、三家碼證確認）條件 IC 之答案窗層次裁定**

🔴 **本裁定取代 R1 之 (a) 方案**（原文保留於下方「原裁定與撤回理由」）。

**使用者原話**：「條件 IC 本來就算一種類型的 IC-Analysis，條件給定應該就是要在
IC 分析的頁面，而不是 `/search` 吧」。

**採 (d) 分析時計算**：
- `/search` 匯出**只承載事件事實**——t0、`label`（來自 t0 條件之 `positive_case`）、
  五維度契約設定。
- **不得**在匯出端寫入 `label_value`。
- 答案窗（`horizon_bars`）與報酬語意（`entry_price_semantic`／`label_return_mode`／
  `decision_offset_bars`）於 **IC 分析頁**由使用者給定；
  後端以 `bars_from_kline_cache` ＋ `align_events` **同一公式**於分析時計算。

🔴 **D-3′-a｜匯出端仍須寫 `label_definition.window.horizon_bars`，但其語意改變**

**主委裁決點（兩份補丁包互斥；依角色卡「在具體提案之間裁決並記錄理由」）**：
- `-arch-shift.md` 之 D-3 diff 主張「**不得**在匯出端寫入
  `label_definition.window.horizon_bars`」。
- `-arch-analyze-time-label.md` §3 主張「既有批若帶烤入之 `label_value`／**窗欄**：
  分析端以本次 h 重算並覆蓋**分析用副本**」——其前提是**匯出仍帶窗欄**。

**採後者。理由為實碼 receipt，非偏好**：
`momentum/Analysis/event_samples/import_contract.py:163` 對 `label_definition.window`
強制 `horizon_bars` 為 `int ≥ 1`，缺欄／非法即 `missing_required_field`；
且 `label_definition` 在 `event_import_contract.json` 之 **`required_fields`** 內
（`label_value` 則在 `optional_fields` ⇒ 省略合法）。
⇒ 照 `-arch-shift` 實作，匯出檔**一律無法匯入**，該句不可實作。

**改採之語意（本節為權威，他處只得引用）**：
| 欄 | 屬哪一層 | 誰寫 | 誰讀 |
|---|---|---|---|
| `label_definition.window.horizon_bars`（匯出檔內） | **事件事實層** | `/search` 匯出端 | D-7 之 lookahead 深度宣告 |
| 條件 IC 之答案窗 `h`（`event_label_spec`） | **分析層** | IC 分析頁 | 分析時 label／purge |

- 匯出檔內之 `window.horizon_bars` ＝ **該批 label 定義所引用之最遠未來根數**（D-7 之唯一通則），
  **不是**條件 IC 之答案窗。
- 分析層**禁止**把匯出檔之 `window.horizon_bars` 讀為答案窗；
  答案窗只能來自本次 `event_label_spec`（見 D-3a）。
- `/search` 之 `label` 由 t0 條件判定（`scenario=C`、無品質過濾）⇒ 該欄之值為 **lookahead 深度**，
  依 D-7 由實際引用之欄位導出，**不得**沿用「使用者選的答案窗」當它的值。

📌 **主委補充，具名標「待 R9 裁定」**（三份補丁包皆未觸及此層；依角色卡須具名而非靜默決定）：

**（i）深度 0 與契約下限 1 之衝突**：D-7 明訂 `scenario=C` 且無品質過濾時 lookahead 深度 **＝ 0**
（實查證之既有批 `20260822T011331Z-eb210a16.json` 即此形態），
而 `import_contract.py:163` 之下限為 `int ≥ 1` ⇒ 深度 0 **無法照實寫入**。
處置：深度 0 時寫入**契約最小合法值 `1`**，並於 receipt 同時記錄 `lookahead_bars_declared = 0`。
理由：`1` 使 embargo 隔一根，比實際需要**更嚴**（§C0 允許更嚴、禁更鬆）；
反向（改契約下限為 0）會放寬既有 fail-closed，§C0 禁止。
⚠️ **副作用須揭露**：purge 因此比理論值多一根，屬**保守偏差**，非計算錯誤。

**（ii）purge 下界為兩個約束之聯集**：D-7 要求 `purge ≥ lookahead 深度`；
D-3a 要求 `purge ≥ 本次分析 h 之 label 窗寬`。兩者皆為現行有效裁定且來源不同
（前者防「標籤偷看未來」，後者防「答案窗大於隔離帶」）⇒
```
purge_lower_bound = max(lookahead 深度換算之 ms, 本次 event_label_spec 之 label 窗寬 ms)
```
**不得**只取其一。依 §C0「只能更嚴」取 `max`。此式之驗收落 Task 7.0b。

**碼證（皆可重跑）**：
`eventExport.ts:75-79`（`label` 來自 `positive_case`，**不看答案窗**）／
`ic_feed.py:4-5`（「v1 不重算」為**版本限制非能力限制**）／
`pipeline.py:77-81`（`bars_from_kline_cache` 已是**服務端取 bars 唯一入口**）。

🔴 **D-3a｜embargo 必須由分析時之 h 重新導出（本裁定之不可分割部分）**

出處＝CODEX-R8-P0-02 ＋ GROK-R8-P0-02（**兩家獨立命中**），
推翻主委於 R8 brief 之 assumed「PIT 可由既有 `decision_time_rule`／`feature_cutoff_rule`
保證、不需新機制」。
⚠️ 補丁包 `-arch-shift.md` 之 AUTHORITY 亦持該被推翻之宣稱 ⇒ **該句不採**；
採 `-codex-pit-wiring.md` 之版本。

- IC analyze 之執行順序固定為 3 步且不得顛倒：①檢核 `event_label_spec`（h／mode／entry／k）
  ②**以該次 h 建立 purge／split** ③以同一 spec 產生 labels。
- **禁止**沿用匯入檔烤入之舊 `label_end_ms − label_start_ms` 當 embargo
  ——改大 h 時 purge 會小於實際 label window ⇒ **train/test 洩漏，違反 §C0**。
- 每列 feature sample key 須為 receipt 之 `last_bar_open_ms`／`decision_at_ms`，
  **不是原始 t0**；`decision_offset_bars = k > 0` 之 t0→decision 映射須有 exact receipt
  （CODEX-R8-P0-03）。
- 驗收：`pytest tests/api -q -k event_analysis_horizon_purge`——
  `h=7` **不得**沿用 `h=1` 之 labels／split；`split purge >=` 本次 label end。
  **mutation**：把 purge 改回沿用匯入值 ⇒ 該測試須紅。

**原裁定與撤回理由（保留，不得刪）**：R1 採 grok 之 **(a)**——
「多選只影響匯出檔帶哪些 `future_{h}bar_return` 欄；`label_value` 與 `horizon_bars`
仍綁單一主答案窗」。當時理由為「契約 `window.horizon_bars` 為單一 int，改動超出本批範圍」。
**撤回理由**：該方案把**分析參數烤進資料**——同一批事件事實，想比較 h=3 與 h=7
必須重新匯出兩次（grok：「強迫為換 h 而重匯出未變之事件事實批」）。
且 A-6 因此是在**錯誤的層次**發問（見 §A）。

**D-4（CODEX-R1-P0-05 ＋ GROK-R1-P1-03 ＋ COMPOSER-R1-P2-01）§G 主張過度，需拆 golden**
接受。實查證：`scripts/gap3_freeze_golden.py:28` import `gap2_freeze_golden._run`，
跑的是 `run_analyze`（IC 主線），**未覆蓋事件路徑**；且該 check 對 `summary_table` 用
數值容差而非位元組相等。而 Task 4.2 會改 `analyze_tables` 之預設 `horizons=(1,2,4)`
（`pipeline.py:98`）⇒ **確實動到事件數值輸出**。
⇒ §G 改寫：新增**事件專屬 golden**，逐 horizon 驗 exact return／NaN mask／PIT anchor；
既有 `163c4ce` 只作為「IC 主線未被波及」之守衛，不再宣稱涵蓋事件路徑。

**D-5（CODEX-R1-P0-06 ＋ COMPOSER-R1-P1-03 ＋ GROK-R1-P2-02，三家全員）
記憶體 cap 之量測協定必須可重現**
接受。原 V-8「footprint 增幅 < 0.2GB」無基線、無採樣窗、無 pid 綁定、無硬體記錄
⇒ 可被 `ps rss`（macOS 壓縮下失真）或「在 cap 檢查之後才 sample」假綠。
⇒ 見 Task 6.2／6.4 之量測協定與 V-8 改寫。

**D-6（COMPOSER-R1-P0-01 ＋ CODEX-R1-P1-03 ＋ COMPOSER-R1-P1-04）
新欄位／新 reason 必須先進契約**
接受。`label_definition.filters` 不在契約 `label_definition.fields`（只有 `rule_id`／
`canonical_digest`／`window`／`label_return_mode`）；`feature_count_exceeds_cap` 不在任何契約。
⇒ Task 1.1 擴充為「先改契約」，Task 6.0 新增 IC 錯誤 reason 之登記處。

**D-7（本版新增；出自使用者 2026-08-22 對話，非委員 finding）
答案窗同時決定 purge 寬度 ⇒ 低報即資料洩漏**
`event_split.py:59-61`：`embargo = split_config.embargo_ms 或 int(window.max())`，
且 `embargo < window.max()` 直接 raise。即**答案窗不只餵條件 IC，還決定 train/test 的隔離寬度**。

使用者實際流程：在 Excel 用 `future_1..12bar_return` 複合條件定義正例
（例如「t0 +5% 且 future_1 ≥ +2% 且 future_2 ≥ +2% 且 future_4 ≥ +1%」）。
此時標籤最遠用到 t0 之後**第 4 根**——若匯入時宣告答案窗為 1，purge 只隔 1 根，
train 段末尾事件的答案會落進 test 區間 ⇒ **靜默洩漏，現行無任何機制擋**。

🔴 **偵測不可能**：使用者指出「CSV 本來就有 future_1..12 全欄，我用哪幾欄是在 Excel 決定的」
⇒ 系統無法由「欄位存在與否」推斷實際用到第幾根。此為**與 D-1 同類**的不可驗事實。

**D-7 之修訂（R2；CODEX-R2-P0-01＋GROK-R2-P0-01＋COMPOSER-R2-P1-01 三家全員）**
原處置以「掃描 `future_{N}bar_return` 欄名取 max(N)」為機器可證基礎，**該基礎不成立**：
- 搜尋結果另含 `future_{N}bar_max_drawdown`（同深度）與 `future72_max_return`／
  `future72_max_drawdown`（更深），引用它們**不會**抬高下界（`case_search_engine.py:669-697`）。
  🔴 使用者實際會這樣寫——以 drawdown 排除「漲完就崩」比用 return 更直接。
- CSV 實際欄名為 `Future_NBar_Return_%`／`Future_NBar_Drawdown_%`（大寫＋百分比後綴，
  `search/page.tsx:567-573`），**非契約蛇形**，字串比對全部落空。
- 使用者可刪高 N 欄後上傳以壓低「檔內最大值」。
- 自訂欄／衍生欄（Excel 算完貼回）之前視深度**靜態不可知**。

**修訂後之處置（採 codex「可驗 provenance；不可證則 fail-closed」）**：
- **L1 欄位級 lookahead 標註**：搜尋結果之每個未來欄在契約登記其深度；
  **兩套命名之單位不同，登記形態亦不同**（權威定義見 Task 1.10，本節不得另立版本）：
  - **bar 命名**（`future_4bar_return`／`future_4bar_max_drawdown`）：`N` 即根數 ⇒ 存 `lookahead_bars = 4`
  - **小時命名**（`future72_max_return`／`future72_max_drawdown`／`future{H}_close_return`）：
    `H` 是**小時**，存 `lookahead_hours = 72`，實際根數 ＝ `H ÷ 每根小時數`（12h 線 ⇒ **6 根**、
    1h 線 ⇒ 72 根）⇒ **禁止在任何地方寫死 `bars = 72`**
  掃描改**讀標註**而非猜欄名。辨識須涵蓋大小寫、`Return`／`Drawdown`、蛇形與 `%` 後綴。
- **L2 未知欄 ⇒ 強制宣告**：出現無法解析深度之 `future*` 或自訂欄 ⇒
  **不得靜默採用偏小 max**，改為強制使用者填寫宣告＋不可驗聲明（Task 1.9）。
- **L3 算不出來 ⇒ 擋在切分外**：仍無法證明 lookahead 深度者，該批**禁止進入
  train/test 切分與條件 IC**，只允許看事件研究表（無訓練即無洩漏）。

**🔴 通則化（使用者 2026-08-22 打斷並糾正；本 SPEC 原本把單一 scenario 當成全部）**

主委原寫「使用者的 label 由『事件條件＋品質過濾』兩段組成」——**那只是 `scenario=C` 的形態**，
被我當成系統通則。使用者逐字糾正：「其他情況，像是預測未來幾根會漲或跌也是一種 scenario，
所以你不能將系統寫死，要考量到其他的設想狀況」。

**契約本來就已區分四種**（`event_import_contract.json` 之 `scenario` enum，主委先前未用上）：

| scenario | 事件在哪 | lookahead 來源 | 深度 |
|---|---|---|---|
| **C 確認型** | t0 當根 | 品質過濾（可選） | 0 或過濾引用之最遠根數 |
| **A／B 預測型** | **未來** | 事件定義本身即在未來 | ≥ 事件之時間距離 |
| **two_stage** | 兩段 | 兩段各自 | 取兩段最大 |

**唯一通則（取代原本的分段描述）**：

> **lookahead 深度 ＝ 該批 label 定義所引用之最遠未來根數**
> ——不論該條件在語意上是「事件本身」還是「品質過濾」。
> **purge 必須 ≥ 此深度。**

⇒ 系統的職責是**確定或要求宣告此深度**，**不得假設它從哪一段來**。
一條規則涵蓋 A／B／C／two_stage 全部，無須為預測型另寫一套。

使用者確認：以「選 t0 漲跌 ＋ 自行篩 future 1-12」即可構成預測型事件（label 由未來條件決定）
⇒ **機制相同、僅語意不同**，現有工具已足以表達，缺的是前端沒把 `scenario` 接出來（見 Phase 7）。

**UI 揭露須動態**：顯示「本批 scenario＝X、lookahead 深度＝N、來源＝<引用之欄位清單>」，
**禁寫死任何固定文案**（主委原擬之「正反例由 t0 條件決定、不看未來」僅對 C 成立，對 A/B 全錯）。

**處置（三層）**：
1. **CSV 上傳路徑**：答案窗**預設取檔內最大可用 horizon**（保守）；使用者可往下調，
   但須明確勾選「我的篩選條件未用到超過第 N 根」之聲明，UI 明示此為**無法驗證的聲明**。
2. **系統內篩選路徑（Phase 2）**：系統確知使用者用了哪些欄 ⇒ **自動導出 `max(N)` 並鎖定**，
   使用者不得調低。**這使 Phase 2 的定位從「方便」升級為「把不可驗聲明轉成機器可證事實」**
   （原 SPEC 把 Phase 2 當錦上添花，定位錯誤，本版改正）。
3. 答案窗欄位接受**任意正整數**，不限 1..12（使用者：「12 根也是我自己訂的，沒有理論根據，
   會不會用到 12 根以外也有可能」）。

🔴 **D-7 之 R8 增訂｜分析時答案窗（出處＝`-arch-analyze-time-label.md` §3；不削弱既有 L1／L2／L3）**

架構變更後條件 IC 之 h 在 IC 頁給定（D-3′）⇒ D-7 之 purge 約束須同時涵蓋**分析層**：
- purge／embargo 之下界須取 **D-3′-a（ii）之 `max` 式**（該式之權威定義在 D-3′-a，本節不重述）。
- **不得**沿用匯入檔內過期之 `horizon_bars`／`label_end_ms` 而使 embargo 偏小。
- 既有批帶烤入之 `label_value`／窗欄者：分析端**以本次 `event_label_spec` 重算並覆蓋
  分析用副本**（in-memory；不回寫匯出檔）；**不得**靜默混用「舊窗＋新 h」。
- 覆蓋之欄恰為 `align_events` 之四個輸入：`label_definition.window.horizon_bars`／
  `label_definition.label_return_mode`／`entry_price_semantic`／`decision_offset_bars`
  （receipt：`alignment.py:152-168` 逐欄取用處）。

**🔴 主委對使用者既有批次之判斷已兩度修正，此為最終版（實查證，非推論）**：
實讀 `data_cache/events/20260822T011331Z-eb210a16.json`：780 筆、`label` 分布 0:520／1:260、
`control_kind` 全為 `user_labeled_same_trigger`、`scenario=C`、`decision_offset_bars=0`、
`label_definition.window.horizon_bars=3`。
使用者 2026-08-22 明言該批**未做任何篩選**（「單純跑出來就匯出」），
且案例搜尋之正反例**僅依 t0 條件**判定（「沒在管後面 30 個欄位」）。
⇒ 該批 label 之 lookahead **＝ 0**，D-7 之洩漏情境**不適用**。
⇒ 原寫「其 IC／分類結果應視為可能偏樂觀」**撤回**——那是把使用者舉例的假設條件
套到一批實際未篩選的資料上，屬推論過頭。
⇒ 該批 `purge 2` 係為 `horizon_bars=3` 之**條件 IC** 而付，與其分類任務無關。

**PIT 已驗證無洩漏**：`ic_feed.py:76` 之 `feature_cutoff_rule = "max_close_ms_le_decision_at"`
＋`decision_time_rule = "t0_open_minus_k_bars"`，`decision_offset_bars=0`
⇒ 特徵最晚僅取至 **t0−1 收盤**，**未偷看 t0 那根**。使用者「用 t0 之前資訊抓 t0 事件」之設定成立。

---

## §A 假設與待使用者確認

| # | 假設 | 狀態 |
|---|---|---|
| A-1 | #0 採 (c)：匯出前篩選 **與** 上傳自篩 CSV 兩者都做，先做上傳 | 已確認 |
| A-2 | #9a 止血閘採「直接擋下」而非「警告後容許硬跑」 | 已確認 |
| A-3 | #9b 排入 GAP-6 | 已確認 |
| A-4' | `label` 為**使用者聲明**，系統不推斷、不預設、不宣稱其正確；未指定 ⇒ fail-closed | R1 三家一致，已改寫（§D-1） |
| A-5' | 批次層預設值對整批一致；**異質列須顯式拒收**（非靜默取第一列） | R1 codex 指出原 A-5 不足，已補（Task 1.8） |
| ~~A-6~~ | D-3 之 (a) 方案（多選只影響匯出欄，label 仍綁單一主答案窗）符合使用者訴求 | ⛔ **R8 作廢**：該問句建立在「條件 IC 之答案窗屬匯出層」之前提上，**前提已被使用者 2026-08-23 裁定推翻**（見 §D-3 撤回理由）⇒ 整條作廢，非「仍待確認」 |
| A-6′ | 條件 IC 之答案窗與連續 `label_value` 於 **IC 分析頁分析時計算**；`/search` 事件批次只固化事實（t0＋二元 `label`＋五維度契約設定） | ✅ **已確認**——使用者 2026-08-23 逐字裁定即取代裁定本身（見下） |
| A-4'／A-5' 之狀態語 | — | 二者為**技術裁定（委員）**，不屬「待使用者確認」 |

**已確認**（使用者 2026-08-22 回覆逐字）：
- A-1：「#0選(c)」
- A-2：「看你怎麼設計都可以」
- A-3：「將#9排在Gap-4(Pooled IC), Gap-5(容量接線)，併入Gap-6規模防護之後」
  ＋「這樣我就等Gap-6之後再針對整個IC-Analysis做測試就好。先把事件型做完」

**A-6′ 之確認 receipt（R8；取代 R5 群集 K 之待確認狀態）**

- **A-4'／A-5'**：純技術主張，依「技術決策委派委員會」由委員裁決，**不列入**本區塊。
- **A-6′ 已確認之依據**：白話閘之目的＝取得使用者對「改變其可見行為」之逐字同意。
  本項之改變**由使用者自己提出**——2026-08-23 逐字：「條件 IC 本來就算一種類型的
  IC-Analysis，條件給定應該就是要在 IC 分析的頁面，而不是 `/search` 吧」，
  三家以碼證確認該架構成立（見 §D-3 碼證）⇒ **使用者原話即取代裁定本身**，
  不存在「還要再問使用者一次他自己提的事」之空間。
  使用者 2026-08-23 就 FROZEN 條件另逐字裁定：該條件視為滿足。
- **可見行為之變更清單（本項之實質內容，供日後追溯）**：
  ① `/search` 匯出面板**移除**「主答案窗」單選；
  ② `/search` 匯出檔**不再**含 `label_value`；
  ③ IC 分析頁**新增**答案窗與報酬語意之分析參數（見 Task 7.6）；
  ④ 比較 h=3 與 h=7 **不需**重新匯出事件批。
- 🔴 **仍為 user assertion、系統不宣稱其正確者**＝ D-1 之 `label` 語意，與本項無關，狀態不變。

### 已驗證事實（FACT-RECEIPT；14 條，皆可由 repo 內命令重現）

- FACT-RECEIPT: `python3 -c "import json;c=json.load(open('momentum/Analysis/contracts/event_import_contract.json'));print(len(c['required_fields']),len(c['import_failure_reasons']))"` → 印出 `13 15`（Claude 實跑 2026-08-22）
- FACT-RECEIPT: `python3 -c "import json,re;raw=open('momentum/Analysis/contracts/event_import_contract.json').read();print(re.search(r'\"scenario\"\s*:\s*\{[^}]*\}',raw).group(0))"` → 印出含 `\"enum\": [\"A\", \"B\", \"C\", \"two_stage\"]` 與 doc「A/B 預測型（事件在未來、不進特徵）／C 確認型／兩段式」（Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -n "_POLICY_BY_SCENARIO" momentum/Analysis/event_samples/dedupe.py` → 印出 `20:_POLICY_BY_SCENARIO = {"C": "cluster_first", "A": "all_with_uniqueness", "B": "all_with_uniqueness", "two_stage": "all_with_uniqueness"}`（**四種 scenario 後端皆已分流**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -nE "scenario:|control_kind:|entry_price_semantic|label_return_mode|decision_offset_bars" frontend/src/lib/eventExport.ts` → 印出 `92: decision_offset_bars: 0,`／`93: entry_price_semantic: opts.entryPriceSemantic ?? 'trigger_open',`／`95: scenario: opts.scenario ?? 'C',`／`102: label_return_mode: 'close_to_close',`／`104: control_kind: 'user_labeled_same_trigger',`（**五處寫死**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -c "counterexample_kind" frontend/src/lib/eventExport.ts` → 印出 `0`（**第五維度完全未送**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `for f in scenario controlKind entryPriceSemantic labelReturnMode decisionOffset counterexample; do echo -n "$f:"; grep -rl "$f" frontend/src/app frontend/src/components 2>/dev/null | wc -l; done` → 印出 `scenario:2`、其餘五項皆 `0`（**UI 未接出**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `sed -n 88p frontend/src/lib/eventExport.ts` → 印出 ``event_id: `${c.symbol}:${c.timeframe || opts.timeframe}:${t0}`,``（**event_id canonical；含 timeframe、不含 label、非 sha256**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `sed -n 59,61p momentum/Analysis/event_samples/event_split.py` → 印出 `embargo = split_config.embargo_ms if split_config.embargo_ms is not None else int(window.max())` 與 `if embargo < int(window.max()): raise ValueError(...)`（**答案窗決定 purge 寬度**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `sed -n 76,77p momentum/Analysis/event_samples/ic_feed.py` → 印出 `"feature_cutoff_rule": "max_close_ms_le_decision_at",`／`"label_window_rule": ...`；同檔 `:75` 印出 `"decision_time_rule": "t0_open_minus_k_bars",`（**特徵最晚取至決策前已收盤 bar，PIT 無洩漏**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -n "def event_forward_return_table" -A 7 momentum/Analysis/event_samples/tables.py` → 簽章為 `(manifest, receipts, bars_by_tf, event_split_plan, table_config)`，**無 `labels` 參數**，docstring 含「不需反例」（**報酬表全批混算、不看 control_kind**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -n "horizons" momentum/Analysis/event_samples/pipeline.py | head -1` → 印出 `98: horizons: Tuple[int, ...] = (1, 2, 4), seed: int = 20260820, n_boot: int = 300,`（**事件報酬表預設只算三個 horizon**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `sed -n 1385,1387p momentum/DataExtraction/case_search_engine.py` → 印出 `df['future24_close_return'] = (df['close'].shift(-periods_24h) - df['close']) / df['close']` 等三行（**`future{H}_*` 之 H 為小時、非根數；根數＝`H // hours_per_candle`**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -noE "future_?[0-9]*[a-z_]*(return|drawdown)[a-z_]*" momentum/DataExtraction/case_search_engine.py | cut -d: -f2 | sort -u | head -3` → 印出 `future1_close_return`／`future24_close_return`／`future2_close_return`（**bar 命名與小時命名兩套並存**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `python3 -c "import json,collections;d=json.load(open('data_cache/events/20260822T011331Z-eb210a16.json'));r=d if isinstance(d,list) else d.get('records',[]);print(len(r),collections.Counter(x.get('label') for x in r),r[0]['control_kind'],r[0]['scenario'],r[0]['label_definition']['window']['horizon_bars'])"` → 印出 `780 Counter({0: 520, 1: 260}) user_labeled_same_trigger C 3`（**使用者實際批次**；Claude 實跑 2026-08-22）

---

## §C0 收斂標準（使用者 2026-08-22 定死，最高位階，覆蓋一切其他規則）

🔴 **「95% 解法就收、殘留具名記錄不當阻塞」在本 SPEC 與整條量化主線一律不適用。**

使用者逐字：
> 「95% 解法就收、殘留具名記錄不當阻塞這是在針對治理 epic 中會有散文化和文字問題，
> **在量化主線完全不接受，數據/品質一定是要 100% 正確，只能更嚴但不能放水**。」
> 「你要絕對保證在量化正確性不能用治理那套『95% 就收』這點，
> **絕對不能犯或不小心有任何一條或引用到，要整條刪除都可以**。」

**適用範圍**：本 SPEC 全部 Phase／Task／§V 各條目，以及其衍生之 TODO、實作、review、蓋章各輪。

**具體禁止**（任一出現即為違規，須停下重做，不得以殘留登記帶過）：
1. 不得以「95%／夠好了／先收再說」為由結束任一輪審查。
2. 不得把**數值正確性**或**資料洩漏**類 finding 降級為具名殘留而放行
   （殘留只適用於「已證明不影響正確性」之工程增強，且須帶三值理由）。
3. 不得以「委員已同意可合併」替代「該條 finding 已實際修復並經 mutation 證偽」。
4. 主委不得援引治理 epic 之收斂慣例（含 P1-6 無限迴圈教訓）來收窄量化正確性之審查範圍。

**主委違規紀錄（保留為警示，不得刪）**：2026-08-22 SPEC R3 輪，主委因 findings 由 7 條反彈至 18 條，
援引「95% 就收」建議收斂並停止加固——**該建議被使用者當場駁回**。
援引錯誤在於：該規則出自治理散文之對抗審無限迴圈，而本 SPEC 之標的是
**lookahead 深度、purge 寬度、資料洩漏**，屬不可妥協之數值正確性。

**與 §V 之關係**：§V 全部條目為**必達**（rc=0 或斷言 `==` 成立），非「盡量達成」；
任一條未通過即不得進入下一 Phase，亦不得定版。

---

## §C 約束（引用，不重抄）

- **契約唯一真相源**：`momentum/Analysis/contracts/event_import_contract.json`——欄位名與
  `import_failure_reasons` 字面值一律由該檔取，程式與前端**禁複列**；
  **新增欄位／reason 一律先改契約再實作**（D-6）。
- **`event_id` canonical 唯一**：`` `${symbol}:${timeframe}:${t0}` ``，
  由 `eventExport.ts` 與 CSV 路徑**共用同一實作**（D-2）。
- **解耦七規則**：R1／R3／R7；驗收 `python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` rc=0。
- **PIT 不變式**：`t0` 為決策根、`decision_offset_bars` 語意不得因本批改動而變。
- **既有事件型測試 230 條為回歸底線**，不得降級。
- 使用者定死「驗過就別預設關閉」：本批新功能通過 §V 全部項目後即預設開啟，不藏 flag 後。

---

## §G Golden / Baseline

R1 推翻了原版「本批不動任何數值路徑」之主張（§D-4），本版拆為**兩條互不替代**的守衛：

**G-1 IC 主線未被波及**：`python3 scripts/gap3_freeze_golden.py --check` 須維持通過。
誠實邊界：該 check 委派 `gap2_freeze_golden._run`（跑 `run_analyze`），
**只守 IC 主線、不涵蓋事件路徑**，且 `summary_table` 用數值容差非位元組相等。
故 G-1 **不得**被引用為「事件輸出未變」之證據。

**G-2 事件路徑專屬 golden（本批新建）**：固定 fixture（真實 kline 切片）＋固定 horizons，
凍結 `event_forward_return_table` 之輸出為 sha256——**該 sha256 之計算規則唯一定義於 S-9**
（`sha256 = S-9(輸出 dict)`），凍結與比對腳本只准 import S-9 之參考實作；逐 horizon 驗
① exact return 值（`atol=0`，位元組相等）②NaN／缺 bar mask 位置 ③PIT anchor（t0 對應根）。
Task 4.2 若改預設 horizons，**必須同步更新 G-2 並在 commit message 說明改了什麼、為什麼**
（合法變更），而非靜默重凍。

**G-3 analysis-label golden（R8 新建；`-codex-pit-wiring.md` ＋ `-arch-analyze-time-label.md` §6）**

§D-3′ 把 `label_value` 由**匯出時**移到**分析時**產生 ⇒ G-2（事件報酬表）**涵蓋不到**這條新路徑：
G-2 凍的是 `event_forward_return_table` 之輸出，而分析時 label 走的是
`align_events` → `resolve_label_value_at_analyze` → `ic_feed`。**兩者不可互相替代。**

**固定輸入（全部寫死於 fixture，缺一即 bytes 不可重現）**：
真實 kline 切片（`data_cache/feature_klines/kline_cache.h5`，禁合成 fixture）、
t0 清單、`decision_offset_bars = k`、`horizon_bars = h`、`label_return_mode = mode`、
`entry_price_semantic`、`direction`、`timeframe`。

**凍結對象（逐項 exact，`atol=0`）**：
① 每 event 之 `label_value`
② 每 event 之 label window（`label_start_ms`／`label_end_ms`）
③ feature timestamp map（`event_id → decision_at_ms`；即餵給 `ic_feed` 之 sample key）
④ **purge boundary**（該次分析實際採用之 embargo ms）
⑤ NaN／尾端不足之 mask（哪些 event_id 之 `label_value` 為 `None`）

**覆蓋面（最小集；不足即不得宣稱本 golden 有效）**：
`direction ∈ {long, short}` × `timeframe ∈ {1h, 12h}` × `h ∈ {1, 7}`，
外加一組「尾端不足」之邊界 fixture。

**可證偽條（五條，皆須可獨立跑）**：
1. 特徵截止仍為 `feature_cutoff_rule = max_close_ms_le_decision_at`（不變；受本 golden 之③保護）。
2. `label_value` 與**獨立手算** `(close[t0+h] − close[t0]) / close[t0]`（long）相等，`atol=0`；
   short 取其相反數。🔴 **oracle 獨立性同 S-8**：expected 值須另寫直算腳本產生，
   **禁以 `resolve_label_value_at_analyze` 自產 golden 後回頭比自己**。
3. 尾端不足 ⇒ `label_value is None` 且該 event **不進** `ic_feed`（loud），**禁填 0**。
4. **同批 h=3 與 h=7 兩次分析**：事件事實 id 集合**相同**；`label_value` 集合**不同**；
   ②④各自對應自己的 h。
5. **mutation（兩條，皆須紅）**：分析改 h 卻不重算 window／embargo ⇒ ④紅；
   以匯出檔烤入之舊 `label_value` 覆蓋分析結果 ⇒ ①紅。

**序列化**：本 golden 之 dict → bytes **沿用 S-9 之同一參考實作**
（`canonical_serialize.py::canonical_event_table_bytes`），**不得**另寫第二個 encoder。

**驗收命令**：`pytest tests/momentum/event_samples/ -q -k analysis_label_golden`。

#### G-2 canonical serialization（R4 群集 B；三家全員判「未定義即不可位元組級證偽」）

主委 R2 曾裁「留實作階段」，被三家推翻；R3 未補；R4 三家再次全員命中。本節即該定義，
**為 sha256 之唯一計算規則**，實作不得另行約定。取材＝`momentum/Analysis/event_samples/tables.py:88-180`
之實際回傳結構（非推測）。

**S-1 欄位白名單（頂層八鍵，固定此順序，不得增減）**：
`statistic_kind`／`horizons`／`primary_macro`／`sensitivity_micro`／`uniqueness_weighted`／
`strata`／`common`／`receipts`。新增鍵即為輸出契約變更，須改本節並重凍。
🔴 Task 7.5 之正／反／全體**三組不得新增第九頂層鍵**——唯一掛載點為 `strata.by_label`
（見 S-1a，R5 consult 三家全員裁）。`strata` 之**內容**擴充不改變頂層八鍵集合。

**S-1a 三組之掛載點（R5 consult；三家獨立皆選 `strata.by_label`）**：
Task 7.5 之三組統計掛於既有頂層鍵 `strata` 之下，鍵集**固定恰為**
`positive`／`negative`／`all` 三者，不多不少。
🔴 鍵名為三家分歧之裁決點，**逐鍵取多數**：`positive`／`negative` 採 codex＋composer
（grok 提 `"1"`／`"0"`）；`all` 採 codex＋grok（composer 提 `aggregate`）。理由僅為多數。
- `positive`／`negative`：各為一個 S-7 之 horizon map。
- `all`：**可計算時**亦為 S-7 之 horizon map；**不可計算時**改為 S-7a 之狀態塊。
- 序列化順序依 **S-2 之通則**（未列名巢狀物件按鍵之 UTF-8 升冪）⇒ `all`／`negative`／`positive`，
  **不得**依執行期 dict 插入序。本鍵集無須另立排序特例。
- **不得**以三次 `event_forward_return_table` 呼叫各產一表代替本結構——那會產生三份可能各自
  漂移的 hash，且把分組踢出表格契約。API／UI 可垂直排列，但**序列化與 G-2 只認這一棵樹**。

**S-2 三層排序**：
- 物件鍵：一律依上列固定順序；未列名之巢狀物件依鍵之 UTF-8 code point 升冪。
- **horizon 鍵須以 `int` 值升冪，禁用字典序**——`primary_macro` 等之鍵為 `str(h)`，
  字典序會把 `"10"` 排在 `"2"` 之前 ⇒ 同一組 horizons 依輸入順序不同得到不同 bytes。
- `horizons` 陣列**原樣保留輸入順序**（它是 `table_config` 之透傳）；因此
  **golden fixture 之 `horizons` 規定為升冪、無重複之整數清單**，避免順序成為隱藏輸入。
- `strata.by_symbol`／`by_direction`／`by_period` 之鍵依 UTF-8 升冪。

**S-3 重複與非法 horizon**：現碼只擋 `h < 1` 與空清單（`:104-105`），**不擋重複**——
重複 h 會產生重複列並在 `block()` 之 `out[str(h)]` 互相覆寫。
⇒ 本批明定：`horizons` 出現重複值即 `raise ValueError`，與 `h < 1` 同級 fail-closed。

**S-4 缺 bar ＝ omission，不是 NaN**：`:129-130` 之 `exit_idx >= len(bars)` 走 `continue`
⇒ 該 (event_id, h) **整列不存在**，由 `n` 反映排除，不灌 0、不產生 NaN 列。
mask oracle ＝ 「(event_id × horizon) 之布林出現矩陣」，須與 golden 一併凍結；
只比 aggregate 會漏掉局部列漂移。

**S-5 NaN 與浮點之表示**：`_weighted_stats` 於空集合回 `float("nan")`（`:47`），
`macro` 亦可能為 `nan`（`:161`）。JSON 無 NaN 字面 ⇒ **一律序列化為 `null`**，
禁用 `NaN`／`Infinity` 非標準字面。浮點以 `repr()`（Python 之 round-trip 最短表示）輸出，
禁用固定小數位（會吞掉最低位漂移）。

**S-6 隨機性輸入**：`ci` 由 `_cluster_bootstrap_ci` 產生，受 `seed`／`n_boot` 決定
（預設 `20260820`／`500`，`:106-107`）⇒ golden fixture 之 `table_config` **必須顯式寫死**
兩者，且其值一併進 `receipts` 與 sha256；未寫死時 bytes 不可重現。

**S-7 統計欄範圍**：每個 horizon 區塊之鍵集固定為
`mean`／`median`／`win_rate`／`n`／`n_effective`（`_weighted_stats`，`:52-58`）
＋`label_anchor_mean`＋`ci`；`primary_macro` 之鍵集為 `mean`／`n_symbols`。
`by_scenario` 之鍵由 `str(sc)` 產生且 `dropna=False` ⇒ 缺值會成為字串 `"nan"`；
本批明定**golden fixture 之 `scenario` 不得有缺值**，避免該字串進入 hash。

**S-7a `not_computed` 狀態塊（S-7 之唯一替代形態）**：
當某組不可計算時（現況只有 `strata.by_label.all`，見 Task 7.5 之 `control_kind` 規則），
該組之值改為**恰兩鍵**之物件：`{"status": "not_computed", "reason": <契約登記之字面>}`。
- `status` 之值固定為字串 `"not_computed"`；`reason` 之值須為契約已登記者（見 Task 7.5）。
- 🔴 **不得**回傳 `n=0` 之空統計塊冒充——那會被讀成「算過但沒樣本」，
  與「這組在語意上不該算」是完全不同的兩件事。
- 本塊亦依 S-9 序列化，**無第二 encoder**。

**S-8 oracle 獨立性**：expected rows 須以**獨立手算**產生（另寫一份直算 entry/exit close 之腳本
或試算表數值），**禁以被測函式自產 golden 後回頭比自己**。至少涵蓋：
`horizons=[1,3,7]`、`ret_entry` 與 `ret_label_anchor` 兩種 return、尾端資料不足之 omission。

**S-9 位元組 encoder（G-2 sha256 之唯一計算規則）**

出處＝R5 consult 三家全員（CODEX-R2-P0-01／COMPOSER-R2-P0-01／GROK-R2-P0-02）：
S-1..S-8 定義了**欄位語意與排序**，但未定義 **dict → bytes** 這一步
⇒ 不同實作者選不同 `separators`／escaping／尾端 newline 仍各自「符合 S-1..S-8」卻得到不同 sha256。
本節即該步之唯一規則；**任何實作不得自行約定 `json.dumps` 參數**。

1. **輸入**：已依 S-1..S-7 組好之 Python `dict`（鍵序已符合 S-2，**不得再 sort**）。
2. **型別白名單**：只接受 `bool`／`int`／有限 `float`／`str`／`list`／`dict`／`None`；
   其他型別（`Decimal`、`numpy` 純量、`datetime` 等）**一律先轉為上列型別**，禁依賴 encoder 隱式轉換。
3. **正規化**：`NaN`／`+Inf`／`-Inf` **一律轉 `None`**（與 S-5 一致）；`-0.0` **保留為 `-0.0`**
   （不得正規化為 `0.0`——兩者 JSON lexeme 不同，會使 hash 隨實作漂移）；
   **缺席鍵保持缺席**（不得補 `null`）；`list` 順序原樣保留。
4. **JSON 生成**：
   `json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False, sort_keys=False)`
   - 禁 `indent`；禁 `sort_keys=True`（順序由 S-2 保證，排序會破壞 S-1 固定序與 horizon 之 int 序）。
   - 字串 escaping 依 JSON 規則：只 escape `"`、`\` 與 `U+0000`–`U+001F`；
     非 ASCII 以**字面 UTF-8** 輸出（`ensure_ascii=False`），不得 `\u` 脫逃。
   - 有限 `float` 之 JSON number lexeme 須等於 CPython `repr(float)`（與 S-5 之 round-trip 一致）。
5. **尾端**：**不得**附加尾端 `\n` 或任何 whitespace。
   🔴 **此為三家分歧之裁決點**：composer 與 grok 指定「禁尾端 newline」、codex 指定「加一個 `\n`」
   ⇒ 採 2:1 之「禁」。裁決理由僅為多數，**非**技術優劣——兩者皆自洽，重點是全專案唯一。
6. **編碼與雜湊**：`.encode('utf-8')`（禁 UTF-8 BOM）→ `hashlib.sha256(bytes).hexdigest()`。
7. **參考實作**：`momentum/Analysis/event_samples/canonical_serialize.py::canonical_event_table_bytes`
   （Task 4.2 實作時建）。G-2 之凍結與比對腳本**只准 import 該函式，禁複製邏輯**——
   複製即第二份副本，副本必然漂移（同 §V 書寫規則之理由）。
   🔴 檔名為三家分歧之裁決點（composer `canonical_serialize.py` vs grok `canonical_json.py`）
   ⇒ 採 composer 版；實質無差異。

**S-9 之驗收**（`pytest tests/momentum/event_samples/ -q -k canonical_serialize` ≥7 條）：
① fixture bytes 與 golden 逐位元組相等
② `separators` 改成 `(', ', ': ')` ⇒ hash 變、測試紅
③ 附加尾端 `\n` ⇒ hash 變、測試紅
④ `ensure_ascii=True` ⇒ hash 變、測試紅
⑤ `NaN` 未轉 `None` ⇒ `allow_nan=False` 之 `json.dumps` raise（**非**靜默輸出 `NaN` 字面）
⑥ `-0.0` 被正規化成 `0.0` ⇒ hash 變、測試紅
⑦**重複 horizon**（R6 群集 J）：`horizons=[1,3,3,7]` ⇒ `event_forward_return_table`
  **raise `ValueError`**（S-3 已規定 fail-closed，R5 版卻無對應測試；
  現碼只擋 `h < 1` 與空清單，重複 h 會在 `out[str(h)]` 互相覆寫而靜默通過）
fixture 須同時含：非 ASCII（`é`）、`"`、`\`、控制字元、`NaN`／`±Inf`、`-0.0`、`None`、缺席鍵。
**S-9 之 mutation**：移除重複 h 之守衛 ⇒ ⑦須紅。

---

## §P Phase 與依賴

### Phase 1 — 使用者自篩 CSV 匯入（依賴：無）　【#0(b) ＋ #5】

**Task 1.1 — 契約先行：新增 reason 與 label_definition.filters**
- 內容（**R8 改寫：改為集合差集，不再寫計數字面**）：
  ① `import_failure_reasons` 增 `column_mapping_missing`／`column_not_found_in_file`／
     `label_column_not_binary`／`heterogeneous_rows_in_batch`。
  ② 🔴 **R8 依 §F-2′ 改掛層次**：`label_producer_unsupported_for_declared_semantics`
     **不再**進 `import_failure_reasons`（R6 群集 D 之落點作廢），改進
     `capability_unavailable_reasons`——理由：§D-3′ 後該 reason 之語意由「匯入失敗」
     變為「本次分析之能力不可用」，兩個清單語意不同，放錯清單會使前端在錯誤的
     生命週期顯示它。
  ③ `capability_unavailable_reasons` 因此增兩值：②之 reason
     ＋ Task 1.12 之 `split_blocked_unverifiable_lookahead`。
  ④ `label_definition.fields` 增 `filters`（型別＋`_doc`）以承載 Phase 2 之篩選條件（D-6）。
  🔴 **改前基準以 fixture 凍結**：`tests/momentum/event_samples/fixtures/event_import_contract.pre_gap3.json`
  ＝本批動工前之契約副本（位元組拷貝）。所有增量以**對該 fixture 之差集**表述，
  **不在 SPEC 或測試內重列既有 reason 字面**（重列即第二份副本）。
- 驗證：`pytest tests/api -q -k gap3_contract_reason_registry` ≥5 條——
  ①`set(now['import_failure_reasons']) - set(pre['import_failure_reasons'])` **集合相等**於
    `{'column_mapping_missing','column_not_found_in_file','label_column_not_binary','heterogeneous_rows_in_batch'}`
  ②`set(pre['import_failure_reasons']) - set(now['import_failure_reasons'])` 為**空集**
    且 `now['import_failure_reasons'][:len(pre['import_failure_reasons'])] == pre['import_failure_reasons']`
    （既有字面與**順序**皆不變）
  ③`'label_producer_unsupported_for_declared_semantics' not in now['import_failure_reasons']`
  ④`set(now['capability_unavailable_reasons']) - set(pre['capability_unavailable_reasons'])` **集合相等**於
    `{'split_blocked_unverifiable_lookahead','label_producer_unsupported_for_declared_semantics'}`
  ⑤`'filters' in now['label_definition']['fields']`
  **mutation（兩條，皆須紅）**：把 `label_producer_unsupported_for_declared_semantics`
  放回 `import_failure_reasons` ⇒ ③④；改動既有 reason 之順序 ⇒ ②。
- 存活至：Phase 6。
- 覆蓋風險：契約為**唯讀增量**——新 reason 與 `filters` 鍵在 Phase 2..7 全程只被讀取或填值，
  無任一 Task 刪改其字面與順序。Phase 2 之 Task 2.2 只寫 `filters` 之**值**；Phase 6 之 Task 6.0
  另建 IC 側 reason 檔而**不併入本檔**（D-6）；Phase 7 之五維度動的是 `label_definition` 之其他鍵
  ⇒ 本 Task 產出不被覆蓋。
  🔴 **R8 改寫之理由（本欄自身即事故現場）**：R6／R7 兩輪之自傷各有一條發生在本欄——
  「`15→19`」「`== 19` 改 `== 20`」「`3→4`」皆為**計數字面**，而它所計之物在同一批內又被改了兩次
  （R6 把 §F-2 之 reason 加進本清單、R8 依 §F-2′ 又把它移到另一個清單）。
  ⇒ 本 Task 之驗收已全面改為**對凍結 fixture 之差集**，SPEC 內**不再出現任何 reason 計數**；
  日後任一 Phase 增值，只需更新該 Phase 自己的差集斷言，本 Task 不必跟著改。
  **須同步**：Task 1.12 之 `split_blocked_unverifiable_lookahead` 與 §F-2′ 之
  `label_producer_unsupported_for_declared_semantics` **同進** `capability_unavailable_reasons`
  ⇒ 兩者之差集斷言在本 Task 驗收④**合併驗一次**，Task 1.12 不得另寫第二份。
- 邊界：只加，**不動**既有 reason 之字面與順序（以驗收②機械對證，不靠計數）。
- 不可做：不得在 `api/` 或 `frontend/` 另寫一份 reason 清單。

**Task 1.2 — 新端點 POST /api/v1/case/import-events/csv**
- 內容：multipart 收 CSV ＋ `column_mapping`＋`batch_defaults`；組出契約記錄後
  **呼叫與 `/import-events` 相同的 schema 檢核與落檔函式**（同一 `.py` 函式，由 V-3 之 AST oracle 機械對證）。
- 驗證：`pytest tests/api -q -k gap3_csv_import` ≥8 條全綠；
  共用性以 V-3 之**兩重 oracle**證（見 §V，非單靠 sha256 相等）。
- 存活至：Phase 6。
- 覆蓋風險：Phase 4 疊加 horizon 欄，端點簽章不變。
- 邊界：只新增端點；**不改** `/import-events` 與 `/import-events/json` 之任何行為。
- 不可做：不得為 CSV 路徑另寫一份 schema 檢核邏輯（須共用同一函式）。

**Task 1.3 — event_id 沿用既有 canonical（D-2）**
- 內容：`event_id` ＝ `` `${symbol}:${timeframe}:${t0}` ``，與 `eventExport.ts:88` **同一實作**
  （抽為共用函式，前後端各自呼叫同一定義來源）。
  `source_file_digest` ＝上傳 CSV 位元組之 `hashlib.sha256(raw).hexdigest()`。
  🔴 **`/search` 路徑之 `canonicalSourceText` 須綁完整 `CaseData`（R6 群集 H；R5 群集 H 之未閉合半邊）**：
  現行只取五欄（symbol／timeframe／timestamp／positive_case／price_change，`eventExport.ts:27-37`）
  ⇒ 刪除、改名或改值任一 `future_*` 欄後 digest **不變**，改名攻擊（Task 1.10 之信任邊界）之證據面未閉合。
  改為：**每列完整 `CaseData` 之遞迴 canonical JSON**——保留所有 own keys 與值（含全部 future return／drawdown 欄），
  只做固定 key ordering（依 §G S-2 之 UTF-8 升冪），**不改名、不篩欄、不省略**；
  digest 綁此完整 bytes。
  🔴 **序列化須依 §G S-9**（R7 群集 G；composer 命中）：含**浮點 lexeme 規則**
  （`repr(float)` round-trip）、NaN／±Inf → `null`、`-0.0` 保留、separators、UTF-8 無 BOM。
  未引用該規則時，瀏覽器之 `JSON.stringify` 與 Python 之 `repr(float)` 對**同一數值**
  可產生不同字面 ⇒ 同一批事件跨執行環境之 digest 不同，改名攻擊之證據面反而不穩。
  ⇒ 前端須以與 S-9 等價之浮點格式化實作（或改由後端端點計算 digest；二擇一，須明示選哪個）。
- 驗證：同一批事件「JSON 匯出檔」與「CSV 回灌」之 `event_id` 集合 `==`（集合相等斷言）；
  改 1 byte 重傳 ⇒ `source_file_digest !=` 原值。
  **R6 群集 H 追加**（`npx vitest run canonicalSourceCoverage` ≥3 條）：對同一組 cases，
  ①**刪除**一個 `future_*` 欄 ⇒ digest 改變 ②**改名**一個 `future_*` 欄 ⇒ digest 改變
  ③**改值**一個 `future_*` 欄之數值 ⇒ digest 改變
  ④🔴 **跨環境一致**：同一批 cases 於前端與後端各算一次 digest ⇒ **位元組相等**
    （R7 群集 G：防 `JSON.stringify` 與 `repr(float)` 之浮點字面差異）
  ⑤含 `-0.0`／極大極小浮點之 fixture ⇒ 前後端 digest 仍相等。
  **mutation（兩條，皆須紅）**：把 `canonicalSourceText` 改回五欄子集 ⇒ ①②③；
  前端改用預設 `JSON.stringify`（不套 S-9 浮點規則）⇒ ④⑤。
- 存活至：Phase 6。
- 覆蓋風險：`event_id` 之輸入僅 symbol／timeframe／t0 三者，後續 Phase 皆不改此三者之定義——
  Phase 2 之篩選條件由 Task 2.2「不可做」明令禁止進入 `event_id` 輸入（D-2）；Phase 4 之附帶
  `future_*` 欄只加輸出欄；Phase 7 之五維度屬 `label_definition` 層設定 ⇒ 不被覆蓋。
  **須同步**：Phase 7 之 `decision_offset_bars`／`entry_price_semantic` 若被實作成改動 t0 之取值，
  同一事件將跨批得到不同 `event_id` ⇒ 實作 Task 7.1 時須重跑本 Task 之集合相等斷言
  （JSON 匯出 vs CSV 回灌 `==`），不得只跑 7.1 自身測試。
- 邊界：digest 綁**上傳的位元組**，不綁解析後的 DataFrame。
- 不可做：**不得發明新的 event_id 演算法**（R1 兩家獨立指出此為 BLOCKING）。

**Task 1.4 — t0 單位偵測**
- 內容：沿用契約 `ms_magnitude_min`；秒級 ×1000；無法判定 ⇒ `invalid_timestamp_unit`。
- 驗證：三組 fixture（ms／秒／不合法）各 1 測；ms 值精確比對 `== 1704067200000`。
- 存活至：Phase 6。
- 覆蓋風險：單位偵測位於解析入口，其輸出（毫秒整數）為後續全部 Phase 之唯一時間表示；
  無任一 Task 改寫 `ms_magnitude_min` 或新增第二條單位判定路徑 ⇒ 不被覆蓋。
  **須同步**：Task 1.2 之 CSV 端點與既有 `/import-events` 須共用同一偵測函式
  （Task 1.2「不可做」已要求共用 schema 檢核），否則兩條路徑會各自演化出不同單位判定
  ⇒ V-3 之 AST oracle 涵蓋面須包含此偵測函式，不得只證 schema 檢核共用。
- 邊界：只判單位，不做時區推斷。
- 不可做：不得在判不出單位時猜預設值。

**Task 1.5 — 前端上傳、預覽與對映 UI（含強制確認）**
- 內容：選檔 → 顯示前 5 列預覽與全部欄名 → 逐項下拉對映 → 填批次預設 →
  **顯示「你聲明的正例 X 筆／反例 Y 筆」並要求勾選確認** → 送出。
- 驗證：`npx vitest run gap3_csv` ≥5 條；斷言未勾確認時 `fetch` call count `== 0`；
  `npm run build` rc=0。
- 存活至：Phase 6。
- 覆蓋風險：Phase 4 於同頁加 horizon 多選，屬疊加。
- 邊界：只做上傳與對映；資料篩選在 Phase 2 之 `/search`。
- 不可做：不得預設任何欄位對映（A-4'）；文案禁用「label 正確」字樣（D-1）。

**Task 1.6 — 對映 provenance 落檔（D-1）**
- 內容：把 `column_mapping`、來源檔名、`source_file_digest`、確認時間寫入該批 receipt，
  使日後可追「這批的正反例是依哪一欄、哪個檔宣告的」。
- 驗證：`pytest tests/api -q -k gap3_csv_provenance` ≥2 條；
  斷言 receipt 之 `column_mapping.label ==` 送出值。
- 存活至：Phase 6。
- 覆蓋風險：receipt 為只增欄位之記錄檔，Phase 2..7 只讀不改；Phase 2 之 `filters` 與 Phase 7 之
  五維度均寫入 `label_definition` 而非本 receipt ⇒ 本 Task 之既有欄位不被覆蓋。
  **須同步**：Task 7.1 讓五維度由寫死改為使用者可選之後，「這批依哪一欄、哪個檔宣告」已不足以
  還原全批設定 ⇒ Task 7.1 實作時 receipt 須一併記錄五維度之實際選值；未同步則 provenance 在
  Phase 7 之後對「這批是用什麼語意算出來的」不可追。
- 邊界：只記錄，不參與任何計算。
- 不可做：不得省略 `source_file_digest`（否則無法對證來源）。

**Task 1.7 — 可疑欄警示（D-1）**
- 內容：預覽階段掃描所有欄，列出**其他也是二元（值域 ⊆ {0,1} 或 {true,false}）的欄名**，
  提示「這些欄看起來也像標記，請確認你選的是哪一個」。
- 驗證：fixture 含 3 個二元欄 ⇒ 警示列出另外 2 個（`len == 2` 且集合相等）。
- 存活至：Phase 6。
- 覆蓋風險：警示只在 Phase 1 之預覽階段執行，不寫入任何持久產物，後續 Phase 無讀取者亦無改寫者
  ⇒ 不被覆蓋。**須同步**：Phase 2 之篩選作用於系統內搜尋結果（欄位由系統產生，非使用者上傳），
  **不得**與本掃描合併為同一實作——合併後，凡值域落在 {0,1} 之系統旗標欄都會被列為「可疑標記欄」，
  警示失去鑑別力（Task 1.7 驗證之「`len == 2` 且集合相等」即會鬆脫）。
- 邊界：只警示不阻擋（語意不可機械判定，見 D-1）。
- 不可做：不得因為只有一個二元欄就自動選它（A-4'：不推斷）。

**Task 1.8 — 異質列顯式拒收（A-5'）**
- 內容：若 CSV 各列在 `direction`／`scenario`／`label_definition` 上不一致而
  `batch_defaults` 未涵蓋 ⇒ `heterogeneous_rows_in_batch`，訊息列出前 3 個衝突列號與欄名。
- 驗證：fixture 混 long/short ⇒ 得該 reason 且**落檔數 `== 0`**。
- 存活至：Phase 6。
- 覆蓋風險：拒收判準（列間於 `direction`／`scenario`／`label_definition` 不一致且 `batch_defaults`
  未涵蓋即拒收）本身在後續 Phase 不變 ⇒ 本 Task 之邏輯不被覆蓋。**須同步**：Task 7.1 將 `scenario`
  由寫死 `'C'` 改為四值可選（A／B／C／two_stage），`batch_defaults` 之可能取值面隨之擴大
  ⇒ 本 Task 之 fixture 須加一組「defaults 指定 `scenario='A'` 而列間混 A／B」之案例並斷言落檔數
  `== 0`，否則 Phase 7 擴大出來的取值面沒有對應測試。
- 邊界：只拒收並指出衝突；不自動分批。
- 不可做：不得靜默取第一列之值套用全批。

**Task 1.10 — 欄位級 `lookahead_bars` 契約（D-7 之 L1；Task 1.9／2.1b 之前置）**
- 內容：新建 `momentum/Analysis/contracts/future_column_lookahead.json`，
  登記搜尋結果**每一個**未來欄之 `lookahead_bars`：
  🔴 **兩套命名並存、單位不同**（GROK-R3-P1-01 抓出主委原寫死 72 之錯誤，實查證屬實）：
  - **bar 命名**（`future_{N}bar_return`／`future_{N}bar_max_drawdown`）：`N` **就是根數** ⇒ `lookahead_bars = N`
  - **小時命名**（`future{H}_close_return`／`future72_max_return`／`future72_max_drawdown`，
    H ∈ {1,2,4,6,24,48,72}）：`H` 是**小時**，實際根數 ＝ `H ÷ 每根小時數`
    （`case_search_engine.py:1385-1387` 之 `periods_{H}h`；12h 線 ⇒ `future72_*` 為 **6 根**，
    1h 線 ⇒ **72 根**）⇒ `lookahead_bars` **與 timeframe 相依，不得寫死常數**。
  ⇒ registry 對小時命名欄須存 `lookahead_hours` 並於執行期換算，**禁存固定 bar 數**。
  ⚠️ **另註**：`periods_72h` 亦被用於**過去 3 天 lookback**（`:1028-1046`），
  與未來欄同名不同義，登記時**不得混淆**（主委原將其誤認為未來欄）。
  盤點來源＝`case_search_engine.py:669-697`（CaseData 欄位）＋`:946-947`（擴展欄），不得遺漏。
  **辨識規則**須同時涵蓋：契約蛇形、CSV 標題形（`Future_NBar_Return_%`／`Future_NBar_Drawdown_%`，
  大小寫與 `%` 後綴，見 `search/page.tsx:567-573`）。
  **owner**：新增未來欄之 PR 須同步登記；**未登記即 fail-closed**（見下方②）。
  🔴 **信任邊界（R4 群集 G；CODEX-R4-P1-07）**：registry 之接受條件**不得只是欄名比對**——
  欄名可被改寫，使用者可把實際引用 20 根未來資料之自訂欄**改名**為已登記之 `future_4bar_return`，
  使 L2 不觸發、purge 被低估到 4 根。⇒ 分**兩類來源**，規則不同：
  - **系統產生欄**（`/search` 之搜尋結果，有 producer／manifest provenance）：
    可由 L1 直接依 registry 解析深度。判定依據＝該批之 provenance 記錄
    （`case_search_engine` 產出＋批次 receipt），**非欄名**。
  - **外部上傳欄**（CSV 匯入路徑）：**一律不得僅憑欄名進入可切分路徑**。
    須帶 producer/schema/digest 綁定；未帶者無論欄名是否命中 registry，
    皆走 Task 1.11 之 L2 強制宣告，並依 Task 1.12 之 L3 決定可否進切分。
  ⇒ 「名稱命中 registry」只在**系統產生欄**上成立；外部欄之名稱不具證據力。
- 驗證（`pytest` 與 `python3 -c` 實跑，逐項 `==` 斷言）：
  ①bar 命名：`m['future_4bar_max_drawdown']['lookahead_bars'] == 4`；
    小時命名：`m['future72_max_return']['lookahead_hours'] == 72` **且無 `lookahead_bars` 鍵**
    （防寫死）；換算函式對 `timeframe='12h'` 回 `6`、對 `'1h'` 回 `72`（`==` 精確比對）
  ②**缺標註 validator**：`pytest tests/momentum/event_samples/ -q -k lookahead_registry_complete`——
    掃描 `CaseData` 之所有 `future*` 欄名，**任一未登記即紅**（斷言未登記集合 `== set()`）
  ③辨識三形態：`Future_4Bar_Return_%`／`future_4bar_return`／`FUTURE_4BAR_RETURN` 皆解析為 4
  ④**registry 內容正確性**（R7 群集 F；codex：R6 版只驗「未登記集合 `== set()`」，
    **未驗登記的深度對不對**）：以實跑盤出之全部 `future*` 欄名逐欄對證單位與深度——
    `future_{N}bar_*` ⇒ `lookahead_bars == N`；
    `future{H}_*` ⇒ `lookahead_hours == H` 且**無** `lookahead_bars` 鍵；
    🔴 **無數字之 legacy 欄**（`future_max_return`／`future_max_drawdown` 等）
    ⇒ 其深度**不可由欄名導出** ⇒ registry 須顯式標 `lookahead_unknown: true`，
    並依 D-7 之 L2／L3 走強制宣告與禁進切分，**不得**給任何預設深度。
    盤點命令：`grep -oE "future[_0-9][A-Za-z0-9_]*" momentum/DataExtraction/case_search_engine.py | sort -u`
    ——該清單之每一項須在 registry 有對應且分類正確（三類：bar／hour／unknown）。
  ⑤**改名攻擊**（R4 群集 G）：`pytest tests/api -q -k lookahead_rename_attack` ≥2 條——
    上傳一份 CSV，欄名為 `future_4bar_return` 但**無 producer provenance**
    ⇒ 斷言 `requires_declaration == True`（不得因名稱命中 registry 而直接放行）；
    未填宣告即送出 ⇒ 依 L3 `split_events` 未被呼叫。
    對照組：同一欄名但來自 `/search` 之系統產生批（有 provenance）⇒ 深度直接解析 `== 4`。
  **mutation（三條，皆須紅）**：刪掉 registry 中 `future_4bar_max_drawdown` 一筆 ⇒ ②；
  把 `future_max_return` 改標成 `lookahead_bars: 12`（猜一個深度）⇒ ④；
  把外部上傳欄改成「名稱命中 registry 即直接解析」⇒ ⑤。
- 存活至：Phase 7（終）。
- 覆蓋風險：registry 為 D-7 三層防線之根（L1），Task 1.11（L2）／1.12（L3）／2.1b 皆只讀它、
  無一改寫它——「存活至 Phase 7（終）」即由此而來 ⇒ 不被覆蓋。**須同步**：Phase 4 之 Task 4.1
  引入附帶 `future_*` 欄、Phase 7 之 Task 7.5 分組報酬表若引入任何新的未來欄，皆須**先**在本
  registry 登記；未登記時 Task 1.10 驗證②之「未登記集合 `== set()`」會紅，該紅為 fail-closed 之
  預期行為，**不得以放寬 validator 或加白名單消紅**。
- 邊界：只登記深度，不改任何欄位之計算。
- 不可做：不得以欄名字串樣式**推測**深度（推測即可被改名偽造，見 L2）；
  不得漏登 `*_max_drawdown` 與 `future72_*`（R2 三家指出之實際繞法）。

**Task 1.11 — 未知欄強制宣告（D-7 之 L2）**
- 內容：解析欄位時若出現**無法由 Task 1.10 registry 解析深度**之 `future*` 欄或自訂欄
  ⇒ **不得靜默採用可解析欄之 max**，改為**強制使用者填寫宣告 ＋ 勾選不可驗聲明**；
  UI 明示「系統無法驗證此深度，錯報將導致資料洩漏」。
- 驗證（`pytest tests/api -q -k lookahead_declaration` ≥2 條）：fixture 含 `my_custom_signal` 欄且被條件引用 ⇒
  ①不得自動放行（斷言 `requires_declaration == True`）
  ②未填宣告即送出 ⇒ fail-closed（落檔數 `== 0`）
  **mutation**：改為「忽略無法解析之欄」⇒ ①須紅。
- 存活至：Phase 7（終）。
- 覆蓋風險：L2 之強制宣告只在「registry 解析不出深度」時觸發；Phase 2 之 Task 2.1b 走的是
  「條件引用之欄位全部可解析」之機器可證路徑，兩者為**互斥分支**而非覆蓋關係 ⇒ 不被覆蓋。
  **須同步**：Task 7.1「邊界」已限定只接出後端既有能力、不新增後端未支援之值，故 Phase 7 不擴大
  本 Task 之觸發面；日後若任一 Phase 允許使用者自訂欄名進入篩選條件，該 Phase 須同批擴充本 Task
  之宣告 UI，否則自訂欄會落入「無人負責宣告深度」之縫隙而被 L3 一律擋死。
- 邊界：只處理「解析不出深度」的情形。
- 不可做：不得因為「其他欄都能解析」就用它們的 max 當全批深度。

**Task 1.12 — 不可證則禁進切分（D-7 之 L3）**
- 內容：若使用者**未填** L2 之宣告、或宣告與 registry 衝突 ⇒ 該批**禁止進入
  train/test 切分與條件 IC**（`split_events` 與 `ic_feed` 皆拒），僅允許事件研究表
  （無訓練即無洩漏）。批次狀態標 `split_blocked_unverifiable_lookahead`（登記處見「須同步」）。
  🔴 **event-study-only 執行路徑（R4 群集 E；CODEX-R4-P0-02）**：R3 版只寫「仍可產出」，
  但實碼**做不到**——`pipeline.py:178` 之 `run()` **無條件**呼叫 `split_events`，
  且 `tables.py:88-93` 之 `event_forward_return_table` 之 `event_split_plan` 為**必填**、
  `:113` 直接 `event_split_plan.clusters.set_index(...)` ⇒ 照現有呼叫鏈只能在
  「違反 L3」與「產不出表」之間二選一。本批補齊該路徑，三項改動：
  ① 新增 executor `run_event_study_only()`——**不呼叫** `split_events`／`ic_feed`／不進訓練。
  ② `event_forward_return_table` 之 `event_split_plan` 改 `Optional`；為 `None` 時
     所有列之 `time_cluster_id` 取 `-1`（現碼 `:140` 對不在 `cl.index` 者已是此值）。
  ③ 🔴 `event_split_plan is None` 時 **`ci` 一律標為 unavailable，不得計算**——
     `_cluster_bootstrap_ci` 依 cluster 重抽樣，全部塞同一個 `-1` 會產生**看似有效但錯誤**的
     信賴區間。`common` 區塊本已 fail-closed（`tables.py:61-69`：無 split plan ⇒
     `formal_pooled_inference_allowed=False`、`reason=no_event_split_plan`），本項與之一致。
  **不得**以空的假 `split_plan` 冒充「未執行切分」（codex 具名之假綠形態）。
- 驗證（`pytest tests/momentum/event_samples/ -q -k split_blocked` ≥6 條）：
  ①該批呼叫 analyze ⇒ 切分**未執行**（斷言 `split_events` 未被呼叫，非只回警告字串）
  ②條件 IC ⇒ `capability_status == "unavailable"`、reason `== "split_blocked_unverifiable_lookahead"`
  ③事件研究表**仍可產出**：走 `run_event_study_only()`，斷言
    `len(result['sensitivity_micro']) == len(horizons)` 且 `receipts['n_rows'] > 0`
  ③b `event_split_plan=None` 時每個 horizon 之 `ci` `== "unavailable"`（**非** 數值區間），
    且 `common['formal_pooled_inference_allowed'] is False`、
    `common['reason'] == "no_event_split_plan"`
  ③c 傳入一個 `clusters` 為空 DataFrame 之假 split plan ⇒ **raise**（不得靜默當成 None 走過去）
  ④reason 字面取自契約：`python3 -c "import json;c=json.load(open('momentum/Analysis/contracts/event_import_contract.json'));assert 'split_blocked_unverifiable_lookahead' in c['capability_unavailable_reasons']"` rc=0
    （🔴 **R8 移除本條之計數斷言**——該清單之增量已由 Task 1.1 驗收④以**對凍結 fixture 之差集**
    一次驗完；此處再寫計數即第二份副本，且 R8 已因 §F-2′ 再增一值而使原 `== 4` 失效），
    且 `grep -rc 'split_blocked_unverifiable_lookahead' api/ frontend/src/ momentum/ --include=*.py --include=*.ts` 之硬編碼字面數 `== 0`
  **mutation（四條，皆須紅）**：把禁令改成僅記 log ⇒ ①；把 reason 硬寫進程式 ⇒ ④；
  讓 `run_event_study_only()` 內部仍呼叫 `split_events` ⇒ ①；
  在 `event_split_plan is None` 時照算 `ci`（而非標 unavailable）⇒ ③b。
- 存活至：Phase 7（終）。
- 覆蓋風險：本禁令作用於 `split_events` 與 `ic_feed` 兩個消費端；Phase 6 之止血閘擋的是 IC 分析
  入口之**特徵數**，兩者為不同拒絕條件、不同 reason 來源（本 Task 走契約之
  `capability_unavailable_reasons`，Task 6.0 走 `ic_report_contract.json` 之 `reasons.analysis_rejected`）
  ⇒ 互不覆蓋，亦不得合併為同一回應
  （合併會使使用者無法分辨「洩漏不可證」與「特徵數過大」兩種完全不同的拒絕）。
  **須同步**：`split_blocked_unverifiable_lookahead` 登記於 `capability_unavailable_reasons`、
  **不進** `import_failure_reasons`；🔴 **R8 改寫**：該清單之增量由 Task 1.1 驗收④
  以對凍結 fixture（`event_import_contract.pre_gap3.json`）之差集統一驗證，本 Task 不再自寫計數
  （原文之「現 3 → 4」與 Task 1.1 之「`== 20`」皆已因 §F-2′ 改掛層次而失效——
  同型錯誤本欄已犯過，故改為機械差集而非人工同步）。
- 邊界：只擋切分與條件 IC，不擋事件研究。
- 不可做：不得以「警告後放行」替代（R2 codex 明指此為 fail-open）。

**Task 1.9 — 答案窗宣告與 purge 下界（D-7 之 L2 使用者介面；依賴 Task 1.10／1.11）**
- 內容：CSV 上傳時，答案窗**預設取檔內最大可用 horizon**（有 `future_1..12` ⇒ 預設 12）；
  可往下調但須勾選「我的篩選條件未用到超過第 N 根」之聲明，UI 明示**此為無法驗證的聲明**；
  欄位接受**任意正整數**（不限 1..12）。宣告值寫入 `label_definition.window.horizon_bars`，
  由既有 `event_split.py` 之 `embargo = window.max()` 自動決定 purge 寬度。
- 驗證：`pytest tests/api -q -k gap3_horizon_declaration` ≥4 條——
  ①CSV 含 future_1..12 ⇒ 預設值 `== 12`
  ②未勾聲明而調低 ⇒ fail-closed（落檔數 `== 0`）
  ③宣告 `== 4` ⇒ `split_events` 之 embargo `== 4 根之毫秒數`
  ④宣告 20（>12）⇒ 接受（不限 1..12）
  ⑤**深度公式一致性**（R4 群集 D）：本 Task 之 purge 寬度須由 **Task 2.1b 之同一式**導出——
    斷言 CSV 路徑與系統內篩選路徑對同一組（宣告 window、引用欄集合）輸入回傳**相同** depth
    （呼叫同一 exported 函式，非各自實作）。兩路徑之差別只在「可否調低」，不在公式。
  **mutation（兩條，皆須紅）**：把預設值改回 1 ⇒ ①；
  讓 CSV 路徑另寫一份深度計算（不呼叫同一函式）⇒ ⑤。
- 存活至：Phase 6。
- 覆蓋風險：本 Task 之宣告值寫入 `label_definition.window.horizon_bars`，與 `/search` 路徑
  （Task 4.1 ③）之深度宣告為**同一欄位、同一寫入點**（R8 改寫：Phase 4 之「主答案窗」已依
  §D-3′ 移除，該欄不再有第二種語意）⇒ 兩路徑須呼叫 Task 2.1b 之同一深度函式；
  Task 4.1「不可做」已明令附帶欄多選不得改變該欄之來源。
  **須同步**：Phase 2 之 Task 2.1b 對系統內篩選路徑**鎖定下界且不可調低**，
  與本 Task 之「可調低但須勾選聲明」為兩條路徑之不同規則 ⇒ 實作須以批次來源（CSV 匯入 vs
  系統內篩選）分派；統一為寬鬆版即 fail-open（機器可證的下界被聲明繞過），統一為嚴格版則 CSV
  路徑無法上傳（CSV 無條件可解析）。
- 邊界：只管「宣告多遠」與其 purge 連動；不改 `event_split.py` 之 purge 演算法。
- 不可做：不得以「檔內有哪些 future_N 欄」推斷實際用到第幾根（D-7：偵測不可能）；
  不得給小於檔內最大 horizon 的預設值。

### Phase 2 — 匯出前篩選（依賴：Task 1.1 之契約欄位定案；**不依賴** Task 1.2 端點）　【#0(a)】

> **定位（D-7 改正）**：Phase 2 不是「方便功能」——它是本批唯一能把
> 「答案窗宣告」從**不可驗的使用者聲明**變成**機器可證事實**的路徑。
> 系統內篩選時，系統確知使用者引用了哪些 `future_N` 欄，可自動導出下界。

**Task 2.1 — /search 匯出前篩選面板**
- 內容：對搜尋結果任一數值欄設 `>=`／`<=`／區間，多條件 AND。
- 驗證：`npx vitest run exportFilter` ≥6 條；含「篩選後筆數 `==` 手算筆數」之數值斷言。
- 存活至：Phase 6。
- 覆蓋風險：面板只讀搜尋結果並產生條件物件，不改任何原始欄位值（「不可做」已鎖）⇒ 後續 Phase
  無改寫者。**須同步**：Phase 4 之附帶欄多選（Task 4.1）與 Phase 7 之五維度選擇（Task 7.1）與本
  面板同處匯出面板，但作用於不同輸出區塊——篩選決定**哪些列**、4.1 決定**哪些欄**、
  7.1 決定**用什麼語意算**，三者疊加不互相覆蓋；三個區塊須共用 Task 2.3 之同一筆數計算函式，
  否則使用者會在同一畫面看到互相矛盾的筆數。
- 邊界：只篩**數值**欄；字串欄不在本 Task。
- 不可做：不得在篩選中改動任何原始欄位值。

**Task 2.1b — 由篩選條件自動導出答案窗下界（D-7 第 2 層）**
- 內容：系統內篩選時，**依 Task 1.10 之欄位級標註**解析條件引用之**所有**欄位
  （含 `*_max_drawdown`／`future72_*`／任何登記欄），取其最大深度為答案窗**下界並鎖定**，
  使用者**不得調低**（與 CSV 路徑之「可調低但需聲明」不同——此處是機器可證，不需聲明）。
  🔴 **深度公式（R4 群集 D；本批唯一權威定義，Task 1.9 與 V-12 一律引用本式）**：
  ```
  depth = max( label_definition.window.horizon_bars ,
               max over 所有實際被引用之欄位 c of  bars_of(c, timeframe) )
  bars_of(c, tf) = c.lookahead_bars                     # bar 命名欄
                 = c.lookahead_hours ÷ hours_per_bar(tf) # 小時命名欄（禁寫死常數）
  ```
  ⇒ 深度**同時**取「宣告的答案窗」與「條件實際引用的最遠欄」之較大者，兩者缺一不可：
  只取前者會漏掉品質過濾欄；只取後者會漏掉「宣告 12 但條件只用 2」之情形。
  **四種 scenario 一律適用同一式**——A／B 之「事件在未來」由其 `window.horizon_bars` 表達，
  不另立公式（R3 之 A／B 敘事「≥ 事件之時間距離」即為本式左項，本批予以機械化）。
- 驗證：條件用到 `future_2` 與 `future_7` ⇒ 答案窗鎖定 `>= 7`；
  嘗試設 5 ⇒ 前端阻擋且 `fetch` call count `== 0`。
  **mutation**：把 `max()` 改成 `min()` ⇒ 該測試須紅。
- 存活至：Phase 6。
- 覆蓋風險：下界導出完全依賴 Task 1.10 之 registry，該 registry 存活至 Phase 7（終）且只增不改
  ⇒ 本 Task 之導出結果不因後續 Phase 失效。**須同步**：Phase 4 之 Task 4.1 讓使用者多選附帶
  `future_*` 欄——附帶欄**不是**篩選條件所引用之欄，**不得**納入 `max(lookahead_bars)`，
  否則答案窗會被與 label 判定無關的攜帶欄推高（過度保守亦屬錯誤：purge 過寬會吃掉訓練樣本）。
  此區分須以測試釘死：條件只引用 `future_2`、附帶欄選 `[1,3,7]` ⇒ 導出下界仍 `== 2`。
- 邊界：只導出下界；使用者可往上調（保守方向永遠允許）。
- 不可做：不得允許調低於導出值（那等於明知條件用到第 7 根卻只隔 5 根）。

**Task 2.2 — 篩選條件寫入 label_definition.filters**
- 內容：把篩選條件寫進契約已登記之 `label_definition.filters`（Task 1.1 已加）。
- 驗證：匯出檔 `label_definition.filters` 與送出條件深度相等（`==`）；
  且 `filters` 鍵存在於契約 `label_definition.fields`（防漂移斷言）。
- 存活至：Phase 6。
- 覆蓋風險：`filters` 為 Task 1.1 已登記之契約欄位，Phase 3..7 無 Task 改寫其 schema；D-2 禁止
  `filters` 進入 `event_id` 之輸入 ⇒ 寫入 `filters` 不回頭改變事件識別。**須同步**：Phase 7 之
  五維度亦寫入 `label_definition`（同一物件之其他鍵）⇒ 兩者須在同一序列化點寫出，並**依 §G 之
  S-1..S-9**處理（S-2 鍵序／S-5 NaN 與浮點／**S-9 位元組 encoder**）；
  本 Task **不自行定義**序列化規則，一律引用該節。
  （R4 群集 B 之修正：R3 版此欄把序列化義務寫成本 Task 自行宣告，而當時 §G 尚無該定義
  ⇒ 等於對一個不存在的規則下義務。§G 之 S-1..S-8 補上後，本欄改為純引用。）
- 邊界：只記錄條件，不改變 `label` 值本身。
- 不可做：不得把篩選條件納入 `event_id` 之輸入（會使同事件跨批 id 不同，違反 D-2）。

**Task 2.3 — 即時筆數顯示**
- 內容：顯示「將匯出 N 筆（原 M 筆）／你聲明的正例 X／反例 Y」。
- 驗證：vitest 斷言 `N + 被濾掉數 == M` 且 `X + Y == N`。
- 存活至：Phase 6。
- 覆蓋風險：本 Task 無持久產物，但其「正例 X／反例 Y」與 Task 1.5 之上傳確認、Task 4.1b／7.3 之
  動態揭露為**同一組事實之多個顯示點** ⇒ 四處須取自同一計算函式，任一 Phase 改變計數口徑時全部
  顯示點同步改變。**須同步**：Task 7.5 把報酬表拆為正／反／全體三組後計數口徑不變
  （`X + Y == N` 仍成立），但 `control_kind == 'user_labeled_other'` 時全體組標為 `not_computed`
  ⇒ 本 Task 之文案不得讓使用者以為全體組必然可算。
- 邊界：純顯示。
- 不可做：不得以估算值顯示。

### Phase 3 — 事件批次刪除（依賴：無）　【#4】

**Task 3.1 — DELETE /api/v1/case/events/{import_id}**
- 內容：刪除該批事件與其 artifact。
- 驗證：`pytest tests/api -q -k gap3_event_delete` ≥4 條；刪後 `GET` status_code `== 404`；
  且斷言該 `import_id` 之所有落檔路徑（事件檔＋Task 1.6 之 receipt＋該批 artifact）殘留檔數 `== 0`
  （防孤兒檔：僅驗 404 無法偵測磁碟殘留）。
- 存活至：Phase 6。
- 覆蓋風險：刪除只作用於已落檔之批次與其 artifact，不改任何契約與計算路徑，後續 Phase 無讀取
  或改寫此端點者 ⇒ 不被覆蓋。**須同步**：Phase 1 之 Task 1.6 receipt 與 Phase 2 寫入之
  `label_definition.filters` 皆屬「該批之 artifact」⇒ 刪除範圍須隨這兩個 Phase 新增之產物同步擴張；
  「刪後 `GET` `== 404`」偵測不到孤兒檔（端點回 404 但 receipt 仍在磁碟），故本 Task 之驗證
  另加落檔路徑清空斷言。
- 邊界：只刪該批；不連帶刪 kline 快取或 Feature Library。
- 不可做：不得提供「刪除全部」端點。

**Task 3.2 — 前端刪除鈕與二次確認**
- 內容：確認框顯示該批筆數與匯入時間。
- 驗證：vitest 斷言未確認時 `fetch` call count `== 0`。
- 存活至：Phase 6。
- 覆蓋風險：本確認框為 Phase 3 專屬元件，與 Task 4.3／5.3 之「缺答案窗欄」確認框為不同元件、
  不同觸發點 ⇒ 不共用亦不覆蓋。**須同步**：Task 3.3 於**同一個**確認框疊加警語 ⇒ 兩者合併實作
  （3.2 先、3.3 後），且 3.3 上線後本 Task 之「未確認時 `fetch` call count `== 0`」斷言須維持
  通過（回歸），不得因加警語而改動確認流程之控制流。
- 邊界：只在批列表提供。
- 不可做：不得以 `window.confirm` 帶過。

**Task 3.3 — 已被引用批次之警語**
- 內容：仍可刪，確認框明示「引用它的分析結果將無法重現」。
- 驗證：vitest 斷言該字串出現於確認框（`toContain` 斷言）。
- 存活至：Phase 6。
- 覆蓋風險：警語疊加於 Task 3.2 之確認框，不改刪除行為本身，後續 Phase 無改寫者 ⇒ 不被覆蓋。
  **須同步**：警語「引用它的分析結果將無法重現」之正確性依賴 Task 3.1 之刪除範圍確實涵蓋該批
  全部產物；若 3.1 未隨 Phase 1／2 新增之 receipt 與 `filters` 擴張刪除範圍，警語與實況不符
  （部分產物仍在、分析其實仍可重現）⇒ 3.1 與 3.3 須同批驗收。
- 邊界：只加警語。
- 不可做：不得靜默刪除被引用批次。

### Phase 4 — 匯出端之報酬欄與揭露（原名「答案窗」；依賴：無；**修正 R1 之錯誤相依聲明**）　【#1】

> 🔴 **R8 更名理由**：§D-3′ 把答案窗移到 IC 分析層 ⇒ 本 Phase 已不含答案窗。
> 保留舊名會使實作者在此尋找答案窗 UI 而找不到，或反過來把它加回匯出面板。
> 答案窗之落點＝Task 7.6（UI）＋ Task 7.0b（計算）。

> GROK-R1-P1-05 指出原版標「依賴 Phase 1、覆蓋 Phase 1 單 horizon 邏輯」是**錯的**：
> Phase 1 是 CSV **匯入**對映，不含答案窗／`future_*`／`label_value` 產生；
> 現行單 horizon 邏輯在 `eventExport.ts` 與 `/search`（B5 已落地）。已改正。

**Task 4.1 — 匯出檔之附帶 `future_*` 欄；並移除匯出端之答案窗與 `label_value`（D-3′）**

🔴 **R8 REOPEN 改寫**：本 Task 原名「可多帶 future_* 欄（D-3 之 (a)）」，
其「主答案窗」單選為 D-3 撤回之 (a) 方案之產物 ⇒ 依 D-3′ 移除。

- 內容（三件事）：
  ① **新增**「附帶報酬欄」多選（預設全選 1..12），匯出檔為每個選中 h 帶
     `future_{h}bar_return`——**純供 Excel 分析攜帶**，不進 `ic_feed`、不決定任何 horizon。
  ② **移除**匯出面板之「主答案窗」單選；匯出端**不再**寫入 `label_value`
     （`label_value` 於契約為 `optional_fields`，省略合法）。
  ③ `label_definition.window.horizon_bars` **仍寫入**，其值＝ **D-7 之 lookahead 深度宣告**
     （語意與寫入規則之權威在 §D-3′-a，本 Task 不重述）。
- 驗證：`npx vitest run eventExportHorizonColumns` ≥5 條——
  ①附帶選 `[1,3,7]` ⇒ 匯出檔含 `future_{1,3,7}bar_return` 三欄
  ②`'label_value' in records[0]` `=== false`（**每一列皆然**，非只驗第一列）
  ③匯出面板**不存在**「主答案窗」控制項（以 testing-library `queryBy*` 斷言為 `null`）
  ④`records[0].label_definition.window.horizon_bars` `===` 執行 Task 1.10／2.1b 之深度導出函式
    對同一輸入之回傳（**呼叫同一 exported 函式比對，非寫死數字**）
  ⑤附帶欄之選擇改變 ⇒ ④之值**不變**（證明附帶欄不參與深度導出）
  **mutation（三條，皆須紅）**：匯出端恢復寫 `label_value` ⇒ ②；
  把「主答案窗」控制項加回 ⇒ ③；`window.horizon_bars` 改讀附帶欄之 `max` ⇒ ④⑤。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task **覆蓋** R1 版之 (a) 方案（刻意，見 §D-3 撤回理由）。
  **須同步**：Task 1.9 之覆蓋風險原寫「本 Task 之宣告值…與 Phase 4 之『主答案窗』為**同一欄位**」
  ——「主答案窗」已移除 ⇒ 該處已改寫為「與 `/search` 路徑之深度宣告為同一欄位、同一寫入點」。
  兩路徑（CSV 宣告 vs `/search` 導出）仍須呼叫 Task 2.1b 之同一深度函式。
- 邊界：附帶欄 h ∈ 1..12；附帶欄只是攜帶，不參與 label 判定、不參與深度導出。
- 不可做：不得在匯出端以任何形式寫入 `label_value`（含寫 `null`、寫 `0`、
  或另立 `label_value_status` 之類新欄——新欄須先改契約，D-6）；
  不得把附帶欄之 `max` 當成 lookahead 深度（那是 D-7 明禁之「由欄位存在與否推斷」）。

**Task 4.1b — 匯出時揭露每個選項在動什麼（使用者 2026-08-22：「我不知道有什麼東西」；R8 依 §D-3′ 改寫③）**
- 內容：匯出面板明文顯示三件現行完全未告知之事實：
  ① **本批 scenario ＝ {實際值} — {契約 doc 之白話}**（由實際設定導出，**禁寫死**）
  ② **lookahead 深度 ＝ {N} 根，來源＝{引用之欄位清單}**（依 D-7 通則導出；C 無品質過濾時為 0）
  ③ **本批之 purge 下界（事件事實層）＝ {N} 根**，並說明「此深度來自你的 label 定義最遠引用到
    t0 之後第幾根」。🔴 **R8 增訂**：同時明示「條件 IC 分析時之實際 purge 另取本次答案窗，
    取兩者較大者」——公式之權威在 §D-3′-a（ii），本欄只揭露、不重述式子
  ④ 本批 `control_kind` 之值與白話意思（現由 `eventExport.ts:104` 寫死 `user_labeled_same_trigger`，
    使用者從未選過亦不知其存在）。
- 驗證：vitest 斷言四段文字皆出現；`control_kind` 顯示值 `==` 匯出檔實際值（防寫死漂移）。
- 存活至：Phase 6。
- 覆蓋風險：**會被 Phase 7 之 Task 7.3 覆蓋**——7.3 之動態揭露涵蓋 scenario／**control_kind**／
  進場價／報酬算法／決策位移／lookahead 深度／purge，為本 Task 四段揭露之嚴格超集，
  且同樣由實際設定導出、同樣禁寫死。
  🔴 **超集關係須以逐項對照驗證，非口頭宣稱**（R7 群集 D：本欄原宣稱超集，
  而 7.3 之揭露清單當時**漏掉 `control_kind`**，取代後 UI 反而少揭露一項）
  ——移除 4.1b 之獨立實作前，須逐項比對兩邊之揭露項集合並斷言 4.1b ⊆ 7.3。
  ⇒ 實作順序 4.1b 先、7.3 後；**7.3 上線時須移除本 Task 之獨立實作**，否則同一面板出現兩份揭露、
  兩份文案來源，日後改一份漏一份。此為**刻意覆蓋**，非漂移。**須同步**：兩者皆為 UI 文案、
  不進序列化產物 ⇒ 此覆蓋不影響 G-2 golden。
- 邊界：只揭露，不改任何預設值。
- 不可做：不得只寫在文件而不顯示於 UI（使用者原話：「我不知道你 JSON 內怎麼寫」）。

**Task 4.1c — 明文標示本批不提供 IC decay（CODEX-R2-P1-02／GROK-R2-P2-01）**
- 內容（**R8 依 §D-3′ 改寫措辭**）：SPEC §D-3 與 UI 皆須明寫：
  「條件 IC decay **曲線**（一次分析同時得到多個 h 的 IC）**非本批交付**；
  附帶之 `future_*` 欄**不進入 `ic_feed`**；
  要看不同答案窗，請**於 IC 分析頁改答案窗重跑分析**——
  **不需重新匯出事件批**（同一批事件事實可重複分析，見 §D-3′）；
  一次得到整條 decay 曲線待 GAP-6 之 IC-Analysis 整體處理。」
  🔴 舊措辭「需要 decay 則換**主答案窗**重跑」已隨主答案窗移除而作廢，不得殘留。
- 驗證：`grep -c "IC decay" docs/GAP3_EVENT_UX_SPEC.md` `>= 1`；
  vitest 斷言該說明出現於匯出面板；**加兩條驗收**：
  ①選 `[1,3,7]` 附帶欄 ⇒ `label_definition.window.horizon_bars` **不變**
    （證明附帶欄不改深度宣告；`label_value` 已不存在於匯出檔，見 Task 4.1 ②）
  ②文案中**不得**出現「重新匯出」作為換 h 之手段（斷言該字串不出現）。
- 存活至：GAP-6。
- 覆蓋風險：GAP-6 若交付 multi-horizon IC，本說明須撤除。
- 邊界：只是揭露邊界，不改行為。
- 不可做：不得讓使用者以為多選附帶欄就會得到多條 IC。

**Task 4.2 — 事件後報酬表顯示完整曲線**
- 內容：`analyze_tables` 之 `horizons` 由呼叫端傳入（現碼預設 `(1,2,4)`，`pipeline.py:98`），
  前端可選要看的 horizon 集合。
- 驗證：`pytest tests/momentum/event_samples/ -q -k horizon_curve` ≥3 條；列數 `== len(horizons)`；
  **且 G-2 事件 golden 須同步更新並在 commit message 說明**（D-4：這是**合法的數值輸出變更**，
  不得靜默重凍）；重凍**須以 §G S-9 之參考實作重算**
  （`canonical_serialize.py::canonical_event_table_bytes`），禁另寫序列化。
  本 Task 一併建該參考實作並附 S-9 之 6 條驗收（見 §G S-9 驗收）。
- 存活至：Phase 6。
- 覆蓋風險：改變 `analyze_tables` 預設值之呼叫形態（**刻意**，已由 G-2 守）。
- 邊界：只改要算哪些 horizon；**不改**每個 horizon 之計算式。
- 不可做：不得因列數變多而改變 `n_eff` 之定義。

**Task 4.3 — 缺欄確認框逐 horizon 列出**
- 內容（**R8 依 §D-3′ 改寫**）：訊息改為**逐附帶 horizon** 列缺幾筆。
  🔴 原文之「主答案窗與附帶欄**分開列**」已作廢——主答案窗已移除，匯出端不再有
  「答案窗缺欄」這件事（`label_value` 不在匯出檔內）⇒ 只剩附帶欄一類。
  答案窗之可算／缺筆數改於 **IC 分析頁**揭露（落點＝Task 7.6 之分析參數區）。
- 驗證：vitest 斷言訊息含每個缺欄**附帶** horizon 之筆數數字；
  **加一條**：訊息**不得**含「主答案窗」字樣（斷言不出現）。
- 存活至：Phase 7（終）。
- 覆蓋風險：覆蓋現行單一 horizon 之訊息字串（**刻意**）。**須同步**：Task 5.3 原以
  「主答案窗 h：N/M 筆可算」為顯示內容，已隨本 Task 一併改寫（見 Task 5.3）。
- 邊界：只改訊息，不改「缺欄不寫值」之既有行為。
- 不可做：不得因缺欄而阻擋匯出；不得在此處揭露答案窗（那已不屬匯出層）。

### Phase 5 — 錯誤訊息與表頭說明（依賴：Task 5.0）　【#2 ＋ #3 ＋ #6】

**Task 5.0 — 建立指標詞彙 SoT（GROK-R1-P1-04）**
- 內容：R1 查證 `event_import_contract.json` 之頂層 `_doc` 是**整份契約的敘事字串**，
  **不含** `macro mean`／`n_eff`／`lift_threshold`／`prevalence_full` 等表頭鍵
  ⇒ 原 Task 5.2 之「取自契約 `_doc`」不可執行。
  新建 `momentum/Analysis/contracts/event_metrics_glossary.json`：每個指標鍵對應
  `{term, definition, formula_ref}`，作為前後端**唯一**文案來源。
- 驗證：`python3 -c "import json;g=json.load(open('momentum/Analysis/contracts/event_metrics_glossary.json'));assert set(g)>= {'macro_mean','micro_mean','n_eff','lift_threshold','prevalence_full','prevalence_learn','signal_frequency','tail_excluded'}"` rc=0。
- 存活至：Phase 6。
- 覆蓋風險：glossary 為前後端唯一文案來源，Task 5.2 只讀不寫，Phase 6 不動事件型兩表
  ⇒ 本 Task 之既有鍵集不被覆蓋。**須同步**：Task 7.5 把報酬表改為正／反／全體三組後，
  新增之分組標籤與 `not_computed` 狀態文字亦屬表頭文案 ⇒ 須登記進 glossary；未登記則 Task 5.2 之
  「tooltip 文字 `==` glossary `definition`」對新表頭無可比對之來源，前端只能另寫一份定義，
  即本 Task「不可做」所禁之第二份副本。
- 邊界：只放文案與公式指標，不放數值。
- 不可做：不得把定義同時寫在前端（Task 5.2 以 `==` 斷言防漂移）。

**Task 5.1 — .source.json 誤傳之訊息追加正解**
- 內容：判別依據＝內容為 `canonicalSourceText` 形狀
  （symbol/timeframe/timestamp/positive_case/price_change）；
  訊息追加「此為來源對證檔，請改放在 `source_file` 欄並勾選 `verify_source_digest`」。
- 驗證：`pytest tests/api -q -k source_json_hint`；status_code `== 400` 且訊息含 `source_file`。
- 存活至：Phase 6。
- 覆蓋風險：只在既有回應訊息尾端追加提示字串、reason 字面不變 ⇒ 任何依 reason 字面判斷之下游
  （含 Task 1.1 之契約清單）不受影響，後續 Phase 無改寫者。**須同步**：Task 1.2 新增 CSV 端點後，
  誤把 `.source.json` 送到 CSV 端點會走另一條錯誤路徑（副檔名非 `.csv`）⇒ 該路徑須給出同一則
  正解提示，否則使用者在新端點得到的訊息比舊端點更難排除，本 Task 的修補在新路徑上等於沒做。
- 邊界：只追加提示；`legacy_schema_detected` 之 reason 字面**不變**。
- 不可做：不得因判別為 source.json 就自動改走 `source_file` 流程（靜默轉換＝契約禁止）。

**Task 5.2 — 事件型兩表 tooltip（讀 Task 5.0 之 SoT）**
- 內容：兩表所有表頭加 tooltip，文案取自 `event_metrics_glossary.json`。
- 驗證：vitest 斷言每個表頭之 tooltip 文字 `==` glossary 對應 `definition` 值。
- 存活至：Phase 6。
- 覆蓋風險：tooltip 純讀 Task 5.0 之 glossary，不改數值與版面；Phase 6 不動事件型兩表
  ⇒ 本 Task 不被覆蓋。**須同步**：Task 7.5 改變表格結構（單組 → 三組垂直排列）⇒ 三組共用同一組
  表頭鍵，本 Task 之「每個表頭之 tooltip `==` glossary `definition`」斷言須在三組結構下**逐組**
  重跑；實作順序 5.2 先、7.5 後，且 7.5 不得為分組另寫一份表頭文案。
- 邊界：只加 tooltip，不改數值與版面。
- 不可做：不得在前端另寫一份定義。

**Task 5.3 — #2 缺答案窗欄之確認框（GROK-R1-P2-01 指出 #2 原版未交代）**
- 內容：使用者 #2 問「要自己找案例時間點測嗎」——現行確認框只在缺 `future_{h}bar_return`
  時跳。改為：匯出前**主動顯示**「附帶欄 h：N/M 筆可算、K 筆因資料尾端不足而缺」，
  使用者不必自己去湊時間點才知道。
  🔴 **R8 依 §D-3′ 改寫**：原文顯示對象為「主答案窗 h」，該概念已移出匯出層
  ⇒ 匯出前之顯示對象改為**每個附帶 horizon**；答案窗之可算／缺筆數於 IC 分析頁揭露
  （落點＝Task 7.6）。使用者關切之「要自己找案例時間點測嗎」在兩處各自被回答。
- 驗證：fixture 尾端 3 筆不足 ⇒ 訊息含 `3`（數字精確比對）；
  **加一條**：訊息**不得**含「主答案窗」字樣。
- 存活至：Phase 7（終）。
- 覆蓋風險：與 Task 4.3 同一訊息區塊，兩者須合併實作（Task 4.3 先）。
- 邊界：只改顯示時機與內容。
- 不可做：不得阻擋匯出。

### Phase 6 — IC 分析止血閘（依賴：Task 6.0）　【#9a】

**Task 6.0 — IC 錯誤 reason 之登記處（D-6）**
- 內容：`feature_count_exceeds_cap` 不屬 `event_import_contract`（那是匯入契約）。
  **沿用**既有之 IC 側契約 `momentum/Analysis/contracts/ic_report_contract.json`，
  於其 `reasons` 物件新增分類 `analysis_rejected`（現有三類：`net_ic_unavailable`／
  `event_fallback`／`xsec_not_applicable`）並登記該值；程式與前端一律由該檔取字面。
- 驗證：`python3 -c "import json;c=json.load(open('momentum/Analysis/contracts/ic_report_contract.json'));r=c['reasons'];assert 'analysis_rejected' in r;assert 'feature_count_exceeds_cap' in r['analysis_rejected'];assert len(r)==4"` rc=0
  （🔴 **斷言為成員資格而非等值**：Task 7.7 會往**同一個** `analysis_rejected` 再加兩個 reason，
  寫成 `== ['feature_count_exceeds_cap']` 會在 7.7 上線時假紅；該清單之**最終**內容由 Task 7.7 斷言）；
  且 `grep -rn 'feature_count_exceeds_cap' api/ frontend/src/ --include=*.py --include=*.ts --include=*.tsx | grep -v 'ic_report_contract' | wc -l` 之硬編碼數 `== 0`。
  **mutation**：把該字面硬寫進 `api/routes/ic.py` ⇒ 第二條斷言須紅。
- 存活至：GAP-6。
- 覆蓋風險：GAP-6 之規模防護可能新增更多 reason，屬疊加。
- 邊界：只登記 reason 字面。
- 不可做：不得在程式內硬寫該字串。

**Task 6.1 — analyze 前置特徵數檢查**
- 內容：`/api/v1/ic/analyze` 啟動任務**前**檢查特徵數；超過上限 ⇒ 400、
  reason 取自 Task 6.0 之登記檔，訊息含實際數與上限數。
  **碼內須註明本 Task 為過渡止血，GAP-6 之分塊計算上線後取代**。
- 驗證：`pytest tests/api -q -k ic_feature_cap` ≥3 條；以 218369 特徵之 run 呼叫 ⇒
  status_code `== 400` **且任務未被建立**（斷言 task store 筆數不變，非只驗 HTTP 碼）。
- 存活至：GAP-6。
- 覆蓋風險：**會**被 GAP-6 取代。
- 邊界：只擋 IC 分析入口；不擋 Feature Factory 產生大 run。
- 不可做：不得提供「強制略過上限」之開關。

**Task 6.2 — 上限值之量測協定（D-5）**
- 內容：定義**可重跑**之量測協定並產 receipt，每個量測點須記：
  ① 機器 RAM 總量與機型 ②目標 pid（單一，不得混進程）③baseline footprint（發請求前）
  ④peak footprint（採樣至任務結束或被 kill）⑤採樣間隔與總時長 ⑥該 run 之 `feature_count`。
  量測工具固定為 macOS `sample <pid>` 之 **Physical footprint** 欄（**禁用 `ps rss`**——
  R1 三家指出 macOS 壓縮頁面使 RSS 失真：UAT 實測 RSS 96–400MB vs footprint 7.1GB）。
  上限＝最小超標點之 `feature_count` **再乘安全係數 0.5**。
- 驗證：receipt 含 ≥3 個量測點且每點六欄齊全；同一 run 重跑 2 次之 peak 差異 `< 20%`
  （否則量測不穩定，須增加採樣或改協定）；設定值 `<=` 最小超標點 × 0.5。
- 存活至：GAP-6。
- 覆蓋風險：同 Task 6.1。
- 邊界：只量 IC 分析路徑；不量 Feature Factory。
- 不可做：**禁拍腦袋填數字**；無 receipt 不得寫入設定；禁以 `ps rss` 當量測值。

**Task 6.3 — 進度回報與前端狀態區分**
- 內容：進度加 `feature_count` 與細分階段；前端區分「後端無回應」與「任務執行中」。
- 驗證：`pytest tests/api -q -k ic_progress_fields` 斷言 response 含 `feature_count` 鍵；
  vitest 斷言兩種狀態之顯示字串 `!==`。
- 存活至：GAP-6 之後仍保留。
- 覆蓋風險：本 Task「存活至 GAP-6 之後仍保留」——Phase 6 五個 Task 中，6.0／6.1／6.2／6.4 之
  「存活至」皆止於 GAP-6（隨止血閘一併被取代），只有本 Task 為永久產出 ⇒ 本批內不被覆蓋。**須同步**：GAP-6 引入分塊計算後進度階段
  會細分得更多 ⇒ 本 Task 之階段字串須設計為**可擴充集合**，測試不得以固定 enum 之窮舉相等斷言
  鎖死（否則 GAP-6 會被迫改寫本 Task 之測試，而改測試是掩蓋行為變更的常見路徑）。
- 邊界：只加欄位與狀態區分。
- 不可做：不得以固定假進度值填充（UAT 已證實 `progress==0.12` 卡 15 分鐘之誤導性）。

**Task 6.4 — 止血閘之存活驗證（D-5）**
- 內容：以 218369 特徵之 run 呼叫 analyze 後，**在 cap 檢查之後、回應之前與之後各採樣一次**
  footprint，證明「未載入大矩陣」。
- 驗證：V-8 之三項斷言（見 §V）。
- 存活至：GAP-6。
- 覆蓋風險：V-8 三項斷言綁定「cap 檢查**之後**才採樣」之取樣時點，而該時點由 Task 6.1 之前置檢查
  位置決定 ⇒ 6.1 之檢查若被移到任務啟動之後，本 Task 會量到已載入大矩陣之 footprint 而失去意義；
  兩者須同批實作並以同一測試釘住先後順序。**須同步**：GAP-6 之分塊計算取代 6.1 時本 Task 一併作廢
  ⇒ 須在 GAP-6 之 SPEC 明列作廢並刪除，不得留著空跑而成為永遠通過的假綠。
- 邊界：只驗記憶體與存活。
- 不可做：不得在 cap 檢查**之前**採樣就宣稱通過（R1 明列此假綠形態）。

### Phase 7 — 全棧接線：把後端既有能力接出前端（依賴：無）　【使用者 2026-08-22 裁定「全接出來，一次做完整」】

> **病因（使用者問「怎麼又出現前後端無法串聯的情況？」）**：
> B5 之 SPEC 寫的是「API 接線＋前端三頁」、驗收條件是「UAT 能跑通」
> ⇒ 主委做了「能跑通的最小路徑」，六個維度全走預設值。
> 三輪 code review 未抓到，因**委員審的是 SPEC/TODO 有無被正確實作**——
> SPEC 沒要求接，實作沒接就不算違規。**規格層的漏，審查層抓不出來。**
> 主委另有現成規則 `feedback_fullstack_wiring_audit`（全棧三欄稽核）**未執行**，
> 而該規則正是上次「幽靈 feature_filter」事故後所立——同病第二次。

**盤點結果（實查證）**：後端五維度皆已實作，前端**一個都沒接**，全走 `eventExport.ts` 之寫死預設。

| 契約欄位 | 契約內完整路徑 | 後端 enum（元素數） | 前端現況 | UI |
|---|---|---|---|---|
| `scenario` | `/required_fields/scenario` | 4：A／B／C／two_stage | 寫死 `'C'`（`:95`） | ❌ |
| `control_kind` | `/required_fields/control_kind` | enum 4；另有 `accepted` 子集 3（`platform_random_bars` 恆拒） | 寫死 `user_labeled_same_trigger`（`:104`） | ❌ |
| `entry_price_semantic` | `/required_fields/entry_price_semantic` | 5 | 寫死 `trigger_open`（`:93`） | ❌ |
| `label_return_mode` | **`/required_fields/label_definition/fields/label_return_mode`**（唯一巢狀者） | 3 | 寫死 `close_to_close`（`:102`） | ❌ |
| `decision_offset_bars` | `/required_fields/decision_offset_bars` | 無 enum（`int`，`min=0`） | 寫死 `0`（`:92`） | ❌ |
| ~~`counterexample_kind`~~ | `/optional_fields/counterexample_kind` | 3 | **完全未送** | 🔴 **R5 群集 G：移出批次維度** |

🔴 **本表為「批次設定」，共 **五** 個維度**（R5 群集 G；codex＋composer 一致）：
`counterexample_kind` 位於契約之 `optional_fields`、語意為**逐列由使用者填寫**之欄
（`unclassifiable` 不可匯入 ⇒ `counterexample_kind_not_importable`），
**不是**可整批選一個值的第六個 scalar。把它接成批次下拉會污染或誤填反例分類。
⇒ 本批之處置：
- **移除**其批次下拉與 `EventExportOptions` 之 `counterexampleKind` 欄。
- 每列若來源有合法值則**原樣映射**；缺值**保持 omitted**（不寫 `null`、不填預設、不取第一列之值）；
  同批可任意混合 `a_trigger_no_follow`／`b_range`／`c_drop`／omitted。
- `label == 1`（正例）**不得**帶此反例欄；帶入或值非三個 enum ⇒ fail-closed，
  reason `== "counterexample_kind_not_importable"`（契約既有值，不新增）。
- `/search` 無來源值 ⇒ 全部 omitted；`/data-preparation` 之 CSV 路徑才可逐列匯入。
- `tables.py` 之反例分層仍讀 derived 之 `counterexample_kind_effective`，
  **不得**改讀任何批次層 UI 值。
⇒ Task 7.0／7.1／7.2 之「維度」一律指**上表前五列**；Task 7.3／7.6 之揭露亦只揭露五項。

> 路徑欄之 receipt：`python3 handoffs/20260822-gap3ux-x-review-r4-dims.py`（遞迴搜尋，不預設層級）。
> 六者分佈於 `required_fields`／`optional_fields`／`label_definition.fields` **三個不同層級**
> ⇒ Task 7.2 之機械閘不得以單一固定層級讀取 enum。

`buildEventContractRecords` 之 `opts` 介面**已有** `scenario?`／`entryPriceSemantic?` 等參數，
但 `/search` 呼叫端（`page.tsx:522-525`）**一個都沒傳** ⇒ 介面留了、UI 沒做。

**數值影響（須告知使用者）**：`entry_price_semantic`／`decision_offset_bars`／`label_return_mode`
三者**直接改變報酬數字**；若使用者實際策略是「訊號後下一根開盤進場」（`next_open`），
現有數字與其策略不符。

#### `label_value` producer 綁定（R5 群集 F；R8 依 §D-3′ 由匯出層改掛分析層；觸及數值正確性，§C0 不得降殘留）

🔴 **R8 改寫之範圍聲明（先讀本段再讀 F-1..F-5）**：本節原題為「`/search` 之 `label_value`
producer 綁定」，其全部條文都建立在「`/search` 匯出端寫 `label_value`」之前提上。
§D-3′ 已裁定匯出端**不寫** `label_value` ⇒ **前提消失**。
本節改寫為**分析層** producer 之綁定；`/search` 端之對應規則退化為單一條 F-0。

**F-0（`/search` 端；取代原 F-1..F-3 對匯出層之全部要求）**：
`/search` 匯出端**不產生、不寫入 `label_value`**（Task 4.1 ②）
⇒ 匯出層不再有「宣告語意 vs 實際數值不一致」之問題，原 F-2 之整批拒絕匯出
與 reason `label_producer_unsupported_for_declared_semantics` **不掛在匯出層**（改掛分析層，見 F-2′）。
`entry_price_semantic`／`label_return_mode`／`decision_offset_bars` 三者在匯出檔內
之角色 ＝ **該批之預設宣告（批次事實層）**，供 IC 分析頁作為分析參數之初始值；
其**不**決定任何數值，因為匯出檔內已無數值可決定。

🔴 **實碼查證之既有不一致（三家 R5 命中；主委實測覆核屬實）**：
`/search` 匯出之 `label_value` 固定取 `future_{horizon}bar_return`，而該欄之產生式為
`(close.shift(-h) - close) / close`（`case_search_engine.py:1317-1318`）
⇒ 其真實語意 ＝ **`entry_price_semantic=trigger_close` ∧ `label_return_mode=close_to_close` ∧
`decision_offset_bars=0`**。
但 `eventExport.ts:93` 之現行預設寫 `entry_price_semantic: 'trigger_open'`
⇒ **現行預設宣稱的語意與實際數值本來就不一致**，不是接出 UI 之後才產生的問題。

🔴 **R8 註**：上段之「既有不一致」在 §D-3′ 下**自動消失**——匯出端不寫 `label_value`，
就沒有「宣告 `trigger_open` 卻寫 close→close 數字」這回事。
保留本段為**病因紀錄**（它是 F-1 支援矩陣之由來），不得刪；但其結論已被 F-0 取代。

**F-1′ 分析層支援矩陣（封閉集合；R8 由匯出層改掛分析層）**：
條件 IC 之分析層 producer 本批只支援**唯一**之報酬語意三元組
`(trigger_close, close_to_close, k=0)`；**答案窗 `h` 為任意正整數，不受本矩陣限制**。
落在此三元組內才產生 `label_value`。short 取負之既有規則不變。

🔴 **主委裁決點（兩份補丁包互斥）**：
- `-arch-shift.md` 之 Task 7.6 diff 主張「**允許**在 IC 頁設定分析參數
  （`horizon_bars`、報酬語意三元組）」——即三元組亦可自由設定。
- `-arch-analyze-time-label.md` §6.2 之 golden 只涵蓋「(t0, h, direction, **F-1 三元組**)」，
  `-codex-pit-wiring.md` 之 golden 只涵蓋 long/short × 1h/12h × h=1/7
  ——**兩份補丁包所指定之 exact golden 皆未涵蓋其他三元組**。
- 既有 F-5 明訂「開放更多組合須先有逐組合之 exact golden」（R5 三家）。

**裁決**：三元組之控制項**移到 IC 分析頁**（arch-shift 之「可設定」在**位置**上落實），
但**本批之可操作集合仍鎖 F-1′**，其餘值 disabled ＋顯示 F-5′ 之開放前置理由。
理由：§C0「只能更嚴」；且無 golden 之組合一旦可選，使用者會拿到**沒有任何 oracle 驗過**
之 `label_value` 直接餵條件 IC——這正是 F-2′ 要根除者。
機制**沿用** Task 7.1 之 `EVENT_DIM_PATH_EXCLUSIONS`（路徑鍵新增 `'/ic-analysis'`），
**不另創第四種機制**。

**F-2′ 偏離即 fail-closed（分析層）**：三元組任一偏離 F-1′ ⇒ **該次分析拒絕**，
`capability_status == "unavailable"`，reason `== "label_producer_unsupported_for_declared_semantics"`。
🔴 **登記處隨層次改變**：本 reason 原登記於 `event_import_contract.json` 之
`import_failure_reasons`（匯入失敗）；改掛分析層後，其語意為**分析能力不可用**
⇒ 須改登記於 `event_import_contract.json` 之 **`capability_unavailable_reasons`**
（該鍵既有值＝`missing_label_value`／`missing_prevalence_disclosure`／`one_class_test_segment`；
receipt：`event_import_contract.json` 之同名鍵）。
🔴 **兩處清單之最終內容之權威在 Task 1.1**，本節**不重述計數亦不重述最終集合**。
🔴 **該 reason 須先登記契約**（R6 群集 D；§C／D-6：新增 reason 一律先改契約）：
登記於 `momentum/Analysis/contracts/event_import_contract.json` 之 `import_failure_reasons`；
🔴 **該清單之最終計數與內容之權威在 Task 1.1**，本節**不重述計數**
（R7 群集 B：R6 版此處寫「由 15 增為 16」而 Task 1.1 寫最終 `== 20`，
兩個互斥終態並存，兩家獨立命中；同 §V 書寫規則之理由——複述即第二份副本）。
程式與前端一律由該檔取字面，硬編碼數須 `== 0`。
（R5 版遺漏此項：主委在 Task 7.5 之兩 reason 與 Task 7.7 之四 reason 皆明定登記處，
唯獨此處未寫 ⇒ 同一規則未一致套用，grok 命中。）
🔴 **不得**單列 skip 後假裝成功，**更不得**在宣告 `next_open` 之下仍寫入 close→close 之數字
——那正是本群集要根除的假語意。

**F-3′ 預設值更正（D-4 合法變更；誠實預設）**：`entry_price_semantic` 之寫死預設由
`trigger_open` 改為 **`trigger_close`**，使「使用者完全不動 UI」時三元組落在 F-1′ 內。
⚠️ **R8 下之性質改變**：原文說「改前改後 `label_value` 位元組相同」——匯出端現已無
`label_value` ⇒ 該保證改述為：**本改動不影響任何數值**，只改該批之宣告欄字面，
且使該宣告與分析層之預設分析參數一致。須在 commit message 說明。

**F-4′ 單一公式來源（分析層）**：判定與換算須由**後端唯一函式**承載，
其呼叫點在**條件 IC 分析路徑**（非 `/search` 匯出）；
前端**不得**在 TS 產生、推導或攜帶 `label_value`（第二份副本必漂移）。
函式與 transport 之定義見 **Task 7.0b**（本節不重述簽章與端點）。

**F-5′ 開放更多組合之前置**：`next_open`／`decision_bar_*`／`k > 0`／非 `close_to_close`
於**條件 IC 分析頁**本批不開放（disabled ＋顯示理由）。
要開放，須有**逐組合之 exact golden**（§G G-3 之 analysis-label golden 擴充）；
在那之前產生不匹配之 `label_value` 一律視為 F-2′ fail-closed 之對象。
🔴 **R8 註**：R5 版所列之開放前置「須先有真正的 label producer（重用 `align_events` 之
`decision_at_ms`／`entry_at_ms`／`label_start_ms`／`label_end_ms` 與 bars）」
**已由 §D-3′ 之分析時 producer 滿足**（Task 7.0b）⇒ 剩下之唯一前置是 golden 覆蓋。
CSV 匯入路徑不經本矩陣（使用者自帶 `label_value`），但仍須過既有契約與 D-7 之 L2／L3；
🔴 **自帶 `label_value` 與分析時重算之互斥處置（`-arch-analyze-time-label.md` §5 要求「須寫死一種」）**：
採 **fail-closed** ——CSV 自帶 `label_value` 之批次，若使用者在 IC 頁給定與匯入宣告
不同之答案窗 `h`，該次分析**拒絕**，reason `== "label_producer_unsupported_for_declared_semantics"`。
理由：另一選項（鎖定匯入值、禁改 h）等於把不可驗之使用者數值當 oracle 沿用，
而系統無法證明該值對應哪個 h ⇒ 依 §C0 取嚴版。
📌 **具名標「待 R9 裁定」**：補丁包只要求二擇一、未指定哪一個，本裁決為主委選擇。

**Task 7.0 — 前置：擴 `EventExportOptions` 補齊五維度（R4 群集 A；Task 7.1／7.2 之前置）**
- 內容：`frontend/src/lib/eventExport.ts` 之 `EventExportOptions`（`:9-17`）現缺
  `controlKind`／`labelReturnMode`／`decisionOffsetBars`／`counterexampleKind` 四個欄位，
  而 `buildEventContractRecords` 之 `:92`／`:102`／`:104` 仍為寫死值。
  本 Task **只做型別與參數化**：補齊五個 opts 欄位、把三處寫死改為 `opts.X ?? <現行預設>`、
  🔴 **不含** `counterexample_kind`（R5 群集 G：逐列選填欄，非批次維度）。
  🔴 **預設值之唯一例外**：依 §F-3′ 把 `entry_price_semantic` 之寫死預設由 `trigger_open`
  改為 `trigger_close`（D-4 合法變更；**不影響任何數值**，變的只有宣告欄字面
  ——匯出端於 R8 已不寫 `label_value`，見 Task 4.1 ②）。
  **除此一項外不動任何預設值、不加任何 UI。**
  🔴 `label_return_mode` 之寫入路徑為**巢狀**（`label_definition.fields`，見 Phase 7 前言表格），
  與其餘五者之頂層路徑不同，須各自對應正確路徑。
- 驗證：`npx vitest run eventExportOptions` ≥7 條——
  ①~⑤每維度各一條：傳**非預設值** ⇒ 產出記錄之對應路徑 `===` 傳入值
    （`label_return_mode` 須斷言 `records[0].label_definition.label_return_mode`，非頂層）
  ⑦全部不傳 opts ⇒ 五欄之值 `===` 預設（`'C'`／`user_labeled_same_trigger`／
    **`trigger_close`**／`close_to_close`／`0`），且 `counterexample_kind` **不出現於輸出**
    （逐列選填欄，見 G-1）
    🔴 `entry_price_semantic` 之預設基準已由 `trigger_open` 改為 `trigger_close`（見 F-3′）
    ——本 Task 之「行為不變」指 **G-2 事件 golden byte 級不變**，宣告欄字面刻意改正
  ⑧🔴 **R8 依 §F-0 改寫**：原⑧要求「三元組偏離 F-1 ⇒ 產出 `n_records === 0` 且 reason
    `label_producer_unsupported_for_declared_semantics`」——該 fail-closed 已隨
    §D-3′ 移到**分析層**（§F-2′，驗收落 Task 7.0b ③⑤）。
    匯出端已不寫 `label_value` ⇒ **沒有可假冒的數值**，整批拒絕匯出即無依據。
    改為：傳任一非 F-1′ 之三元組 ⇒ 匯出**照常成功**，
    且每一列皆**不含** `label_value`，`records[0].entry_price_semantic` 忠實等於所傳值
    （宣告即事實，不再有「宣告與數值不符」之可能）
  **mutation（兩條，皆須紅）**：把任一 `opts.X ?? default` 改回寫死 ⇒ 對應那條；
  在任一三元組之下於匯出端寫入 `future_{h}bar_return` 作為 `label_value` ⇒ ⑧。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task 只擴介面不接 UI，其產出被 Task 7.1（接 UI）與 7.2（機械閘）**依賴而非覆蓋**
  ⇒ 三者為 7.0 → 7.1 → 7.2 之嚴格順序。**須同步**：7.0 之⑦「不傳即等於現行預設」是 7.1
  golden byte 回歸之**基準**；若 7.0 順手改了任一預設值，7.1 之回歸就失去意義 ⇒ 兩者須同批驗。
- 邊界：只擴型別與參數化＋§F-3 之單一預設更正；不加 UI；
  **本 Task 範圍內**不改後端（F-4 之後端唯一 producer 由 **Task 7.0b** 承載）。
- 不可做：**除 §F-3 明列之 `entry_price_semantic` 一項外**，不得調整任何其他預設值
  （R6 群集 C：R5 版三處禁令與 F-3 互斥，Agent 可援引禁令拒絕 F-3）；
  不得把 `label_return_mode` 寫到頂層——正確路徑為
  `label_definition.label_return_mode`，寫錯位置會使契約 schema 檢核通過但語意落在錯的物件。

**Task 7.0b — 分析時 `label_value` producer 與其 wiring（R6 群集 E；F-4′ 之承載 Task）**

🔴 **R8 REOPEN 重寫**：R7 才補上之 `POST /api/v1/case/label-values` 落在**匯出**生命週期
（request 帶 `cases`＝`/search` 之結果列、呼叫點為 `buildEventContractRecords`）。
§D-3′ 裁定答案窗屬**分析層** ⇒ 該端點之整個生命週期位置錯誤，**非改參數可補**，故重寫。
原版條文保留於本 Task 末「原版與撤回理由」，不得刪。

- 內容（四件事）：

  **① 後端唯一 producer 函式**
  新建 `momentum/Analysis/event_samples/label_value_from_case.py`，公開單一函式
  ```
  resolve_label_value_at_analyze(records, bars_by_tf, *, event_label_spec)
      -> {"supported": bool,
          "label_values": {event_id: float | None},
          "windows": {event_id: {"label_start_ms": int, "label_end_ms": int,
                                 "decision_at_ms": int, "entry_at_ms": int}},
          "reason": str | None}
  ```
  - `event_label_spec` ＝ `{horizon_bars, entry_price_semantic, label_return_mode,
    decision_offset_bars}`；`supported` 由 §F-1′ 判定，偏離 ⇒ F-2′ 之 reason。
  - **禁止**自行實作報酬公式：`windows` 與 `label_value` 一律由既有 `align_events`
    產生（receipt：`alignment.py:152-172` 已由 `label_definition.window.horizon_bars`／
    `label_return_mode`／`entry_price_semantic`／`decision_offset_bars` 導出四個時間戳）。
  - 呼叫前先建**分析用副本**：把 `event_label_spec` 之四值覆寫到記錄副本之對應欄
    （in-memory；**不回寫**匯出檔／已落檔事件批），覆寫規則之權威在 §D-7 之 R8 增訂。
  - bars 一律經 `bars_from_kline_cache`（服務端取 bars 唯一入口，`pipeline.py:77-81`）；
    取不到 bars ⇒ `supported=False`、reason 走既有 capability unavailable 路徑。
  - 尾端不足 ⇒ 該 event 之 `label_value` 為 `None` 且**不進 IC**（loud），**禁填 0**。

  **② transport：折進既有 IC analyze，不另開端點**
  🔴 **主委裁決點（三份補丁包提出三種 transport，互斥）**：
  - `-arch-shift.md`：`POST /api/v1/ic/event-label-values`（前端先取 `label_values` 再送分析）
  - `-arch-analyze-time-label.md`：`POST /api/v1/event-batches/{id}/conditional-ic`
  - `-codex-analysis-label.md` ＋ `-codex-pit-wiring.md`：**不另開端點**，於
    `ICAnalyzeRequest` 增 `event_import_id` ＋ `event_label_spec`，
    由 `ic_analysis_service._run_analysis` 於服務端呼叫 producer
    （兩份補丁包之 SYNC-LOCI 皆列 `api/models/ic_models.py#ICAnalyzeRequest`
    與 `api/services/ic_analysis_service.py#_run_analysis`）。

  **裁決：採第三種（折進 IC analyze）。理由為正確性，非偏好**：
  前兩種讓 `label_value` 經前端往返一趟 ⇒ 前端可能以 `h=3` 取得 `label_values`
  卻以 `h=7` 送出分析，**purge 與 label 分屬不同 h**，正是 §D-3a 三步順序要根除者；
  且 §D-3a 明訂「①檢核 spec ②以該次 h 建立 purge／split ③以同一 spec 產生 labels」
  必須**在同一次分析內原子完成**，跨請求即無法保證。
  `-arch-shift.md` 自身亦允許「或**同函式之服務端呼叫**」⇒ 本裁決在其容許範圍內。
  ⇒ **不採**任何獨立 `label-values` 端點；前端**不得**持有或傳送 `label_value`。

  **③ 契約欄位（先改契約，D-6）**
  - `ICAnalyzeRequest` 新增 `event_import_id: Optional[str]` 與
    `event_label_spec: Optional[dict]`（欄集恰為 ① 所列四鍵）。
  - `event_label_spec` 存在而 `event_import_id` 缺 ⇒ `400`；反之（只給 import_id）
    ⇒ 以該批之匯出宣告值為分析參數初始值（F-0）。
  - 🔴 現況 `event_import_id` **只存在於前端 config**、從未送到後端
    （receipt：`ICConfigPanel.tsx:275-277` 寫入 config；`useICAnalysis.ts:283-286`
    只送 `event_timestamps`）⇒ 本 Task 一併補此 wiring。

  **④ 執行順序與 purge（§D-3a 三步之落地點）**
  `_run_analysis` 之事件分支固定為：①檢核 `event_label_spec`
  ②以 **§D-3′-a（ii）之 `max` 式**計 purge 下界並建 split
  ③以同一 spec 呼叫 ① 之 producer 產生 labels ④ labels 餵 `ic_feed`。
  **禁止**沿用匯入檔之 `label_end_ms − label_start_ms` 當 embargo。

- 驗證（pytest 兩組 ＋ vitest 兩組，逐條如下）：
  `pytest tests/momentum/event_samples/ -q -k analysis_label_producer` ≥7 條——
  ①F-1′ 內（`trigger_close`／`close_to_close`／`k=0`）⇒ `supported is True` 且
    `label_values[eid] ==` 手算之 `(close[t0+h]-close[t0])/close[t0]`（long，`atol=0`）
  ②同上 short ⇒ 值為①之相反數（`== -x`，`atol=0`）
  ③`entry_price_semantic='next_open'` ⇒ `supported is False`、`label_values == {}`
  ④`decision_offset_bars=3` ⇒ 同③；且 `windows[eid]['decision_at_ms']` `<` `t0`
    （證明 k 之映射確實生效，而非被忽略）
  ⑤`label_return_mode='open_to_close'` ⇒ 同③
  ⑥同一批以 `h=3` 與 `h=7` 各跑一次 ⇒ event id 集合**相同**、
    `label_values` **不相同**、`windows[*]['label_end_ms']` 各自對應自己的 h
  ⑦尾端不足 ⇒ 該 eid 之 `label_value is None` 且**不出現**於餵給 `ic_feed` 之輸入
    （斷言 `ic_feed` 輸入之鍵集不含該 eid；**非**填 0）
  `pytest tests/api -q -k event_analysis_horizon_purge` ≥5 條——
  ⑧`h=7` **不得**沿用 `h=1` 之 labels／split；`split purge >=` 本次 label end
  ⑨purge 下界 `==` §D-3′-a（ii）之 `max(lookahead 深度, 本次 h 窗寬)`：
    以「深度 12、h=3」與「深度 1、h=7」兩組 fixture 各驗一次，證明兩邊都可能是勝者
  ⑩`event_label_spec` 存在而 `event_import_id` 缺 ⇒ `400`
  ⑪`event_import_id` 確實由前端送達後端（`npx vitest run icEventAnalysisRequest` ≥2 條：
    選批後送出之 payload 含 `event_import_id` 與 `event_label_spec`）
  ⑫🔴 **前端不得持有 `label_value`**：斷言
    `grep -cE "label_value" frontend/src/lib/eventExport.ts` `== 0` 且
    `grep -cE "label_value" frontend/src/hooks/useICAnalysis.ts` `== 0`
  **mutation（六條，皆須紅）**：`supported` 恆真 ⇒ ③；short 不取負 ⇒ ②；
  purge 改回沿用匯入值 ⇒ ⑧；`max` 式改成只取本次 h ⇒ ⑨；
  尾端不足改填 0 ⇒ ⑦；在 TS 重寫一份公式 ⇒ ⑫。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task **取代** R7 版之匯出端 producer（刻意；見上「REOPEN」）。
  **須同步**：§F-5′ 若日後開放更多三元組，只需擴充本函式之支援矩陣與 §G G-3 之 golden，
  **不得**在前端或匯出層另開分支；Task 7.6 之分析參數 UI 與本 Task 之 `event_label_spec`
  為**同一組欄位**，欄位增減須同批改。
- 邊界：只在分析時判定與換算 `label_value` 與其 window；不改 `event_id`、
  不回寫任何已落檔之事件批、不改契約其他欄位。
- 不可做：不得在不支援之組合下回傳任何非 `None` 之 `label_value`（§F-2′）；
  不得讓前端持有、推導或傳送 `label_value`（§F-4′）；
  不得為「省一次計算」而快取上一次 h 之 labels 給不同 h 之分析使用。

**原版與撤回理由（R7 版，保留不得刪）**：
R7 版定義 `resolve_label_value(case, *, ...)` 單列函式 ＋ `POST /api/v1/case/label-values`，
request 之 `cases` 為 `/search` 之結果列，前端呼叫點為 `buildEventContractRecords`，
並要求「`buildEventContractRecords` **只得**由本端點取 `label_value`」。
**撤回理由**：該設計把 producer 綁在**匯出**生命週期上，而 §D-3′ 裁定答案窗屬分析層
⇒ 匯出時根本還不知道使用者要用哪個 h，端點的 `horizon_bars` 參數無來源。
R7 版之驗收⑥（reason 取自 `import_failure_reasons`）亦隨 F-2′ 之登記處改變而作廢。

**Task 7.1 — 五維度全部接出前端（依賴 Task 7.0）**
- 內容：`/search` 匯出面板與 `/data-preparation` 匯入表單各提供五個維度之選擇；
  每個選項旁附白話說明（取自契約 `doc` 欄，不另寫）。預設值維持現行以免既有流程改變，
  但**必須可見可改**。
  🔴 **可選集合之定義（R4 群集 A＋D）**：
  `selectable(path, dim) = accepted(dim) − pathExclusions(path, dim)`
  - `accepted(dim)` ＝ 契約之 `accepted` 鍵；無該鍵者取 `enum` 全集。
    （`control_kind`：`enum` 4 值、`accepted` 3 值，`platform_random_bars` 恆拒。）
  - `pathExclusions` ＝ **前端單一具名常數**（如 `EVENT_DIM_PATH_EXCLUSIONS`），
    每筆須帶**非空理由字串**。**本批之封閉內容**（R5 群集 F／H 擴充後）：
    ```
    ('/search',      'scenario',             { A, B, two_stage })   # 皆無獨立 label producer
    ('/search',      'entry_price_semantic', { trigger_open, next_open, decision_bar_open, decision_bar_close })
    ('/search',      'label_return_mode',    { open_to_close, open_to_horizon_close })
    ('/ic-analysis', 'entry_price_semantic', { trigger_open, next_open, decision_bar_open, decision_bar_close })
    ('/ic-analysis', 'label_return_mode',    { open_to_close, open_to_horizon_close })
    ```
    ⇒ `/search` 之 `scenario` 只開 `C`；`entry_price_semantic` 只開 `trigger_close`；
    `label_return_mode` 只開 `close_to_close`——恰為 §F-1′ 之支援矩陣。
    `decision_offset_bars` 非 enum，於 `/search` 與 `/ic-analysis` 之可輸入範圍均鎖定為 `0`（見 §F-1′）。
    🔴 **新增 `/ic-analysis` 列之理由**：§D-3′ 後三元組之控制項移到 IC 分析頁
    （Task 7.6 ③），該處之可操作集合須與 §F-1′ 一致 ⇒ 沿用**同一具名常數**，
    **不另建第二份排除清單**（另建即第二份副本）。
    🔴 **`/search` 各列之理由字串須隨 §F-0 更新**：原理由為「匯出端會寫 `label_value`，
    偏離即假語意」；匯出端已不寫 `label_value` ⇒ 新理由為
    「該值宣告後，分析層本批不支援以其計算 `label_value`（§F-5′）⇒ 該批將無法做條件 IC」。
    依 §C0「只能更嚴」**保留**排除，只改理由字串。
    ⇒ 排除是**封閉可列舉集合**，不是散落在元件裡的 if；新增或移除排除須改該常數並同步本 SPEC。
  - 兩類**不可選**值之 UI 呈現不同、須分別顯示：契約恆拒者顯示契約之 `rejected_with_reason`
    字面；路徑排除者顯示 `pathExclusions` 之理由字串。兩者皆 **disabled 且不計入 selectable**。
- 驗證：`npx vitest run eventContractOptions` ≥10 條——
  ①~⑤每維度各一條，斷言「**可操作**（非 disabled）之 UI 選項集合 `==` `selectable(path, dim)`」
    （`accepted` 由契約導出、排除由具名常數導出，**兩者皆非硬編碼清單**）
  ⑦`control_kind` 之 disabled 選項存在且其 title/aria 含 `not_implemented_platform_random_bars`
  ⑧`/search` 之 `scenario` 之 `A`／`B`／**`two_stage`** 三者皆為 disabled 且顯示排除理由；
    同一維度在 `/data-preparation` 之 selectable `==` 全部 4 值（證明限制**只在該路徑**）
  ⑨`EVENT_DIM_PATH_EXCLUSIONS` 之每個理由字串 `!== ''`，且該常數之內容**集合相等**於
    ```
    {('/search','scenario'):                 {A, B, two_stage},
     ('/search','entry_price_semantic'):     {trigger_open, next_open, decision_bar_open, decision_bar_close},
     ('/search','label_return_mode'):        {open_to_close, open_to_horizon_close},
     ('/ic-analysis','entry_price_semantic'):{trigger_open, next_open, decision_bar_open, decision_bar_close},
     ('/ic-analysis','label_return_mode'):   {open_to_close, open_to_horizon_close}}
    ```
    🔴 **以集合相等斷言，不用計數字面**（理由見本 Task 覆蓋風險）
  ⑩**五維度全部維持預設 ⇒ G-2 事件 golden byte 級不變**（證明接出 UI 本身不動數值）
  ＋`npm run build` rc=0。
  **mutation**：把 `pathExclusions` 清空 ⇒ ⑧須紅；把排除改成寫在元件內的 if ⇒ ⑨須紅。
- 存活至：Phase 7（終）。
- 覆蓋風險：Phase 7 為最後一個 Phase，本 Task 純新增 UI 控制項且「內容」已鎖預設值維持現行
  ⇒ 無後續 Phase 覆蓋。**須同步**：本 Task 讓 `entry_price_semantic`／`decision_offset_bars`／
  `label_return_mode` 之實際取值面由單一寫死值擴為 enum 全集，而這三者**直接改變報酬數字**
  （見本 Phase 前言「數值影響」）⇒ 驗收須含一條「五維度全部維持預設 ⇒ G-2 事件 golden **byte 級
  不變**」之回歸，證明**接出 UI 這件事本身不動任何數值**；使用者主動改動預設值所導致之 golden
  改變，屬 D-4 之合法數值輸出變更，須在 commit message 說明，不得靜默重凍。
- 覆蓋風險（R6 群集 A 追記）：驗收⑨改以**集合相等**斷言之理由——R4 版寫「該常數之筆數
  `=== 1`」，主委依 consult 群集 F／H 把該常數擴為三筆時**未同步該計數字面**，
  COMPOSER-R6-P1-01 與 GROK-R6-P0-01 兩家獨立命中。**計數字面會隨擴充而漂，集合相等不會**
  ⇒ 本 SPEC 一律優先用集合相等；殘存之計數字面由 `scripts/spec_count_audit.py` 稽核。
- 邊界：只接出既有能力；**不新增**任何後端未支援之值。
  🔴 **`scenario` 之路徑級限制（R4 群集 D；R5 群集 H 收緊）**：
  `/search` 匯出路徑本批**只可選 `C`**；`A`／`B`／**`two_stage`** 於該路徑 disabled 並顯示理由
  （R5 更正：R4 版放行 `two_stage`，但 `two_stage_search.py` 合併後同樣只有 t0 之 `positive_case`、
  **無兩段式 producer 與 provenance**，與 A／B 是同一個問題；三家一致指出，已收緊）
  「此路徑之 `label` 由 t0 條件產生（`eventExport.ts:75-85` 以 `positive_case` 判定），
  A／B 為預測型、事件在未來，需獨立之 label producer 與 provenance，**本批未交付**」。
  `/data-preparation` 之 **CSV 匯入路徑四種全開**（label 由使用者自帶，系統只照抄）。
  ⇒ 這是**路徑級**限制，不是把系統寫死於單一 scenario——後者為使用者 2026-08-22 明令禁止者。
  未加此限制時，使用者選 A／B 可通過 enum validator，但 `label` 仍是 t0 之 `positive_case`
  ⇒ 契約宣稱預測型、實際是確認型（語意漂移），且 Task 7.3 之動態揭露只會忠實顯示這個錯誤設定。
- 不可做：不得在前端硬寫 enum 清單（必須由契約導出，否則下次加值又漂）；
  不得在未交付 A／B label producer 前於 `/search` 開放 A／B（見「邊界」）。

**Task 7.2 — 機械閘：可操作選項集合 ＝ `selectable(path,dim)`，且選值真的傳到落檔（依賴 Task 7.0／7.1）**
- 內容：新增測試，對五個維度逐一驗**三層**（R4 群集 A：R3 版只驗第一層，三家全員判不足）：
  **① 集合層**——「**可操作**（`disabled === false` 且可 focus）之 UI 選項集合」`==`
    `selectable(path, dim)`（定義見 Task 7.1：`accepted` 減 `pathExclusions`）。
    **disabled／hidden 選項一律不計入**，因此無法以放一個 disabled 的 `platform_random_bars`
    湊足元素數，也無法把 `/search` 之 `A`／`B` 改成 enabled 而不動 `pathExclusions`。
  **② round-trip 層**——每維度選一個**非預設值** → 呼叫 `buildEventContractRecords`
    → 斷言落檔記錄之對應路徑 `===` 所選值。這層才是擋住 B5 病因（「介面有、沒傳」）的那一層；
    只有 ① 時 UI 可以全對而 payload 仍是寫死預設。
  **③ 非 enum 欄**——`decision_offset_bars` 無 enum，驗：有可輸入且非唯讀之控制項、
    輸入 `-1` ⇒ fail-closed（契約 `min: 0`）、輸入 `k` ⇒ 落檔 `decision_offset_bars === k`。
  並禁止 `eventExport.ts` 出現無 UI 對應的寫死值。
- 驗證：`npx vitest run contractEnumWiring` ≥14 條（5×①＋5×②＋2×③＋2×路徑對照：
  同一維度在 `/search` 與 `/data-preparation` 之 selectable 各自成立）；
  ①之斷言為 `new Set(uiEnabledOptions)` 等於 `new Set(selectable(path, dim))`
  且長度相等；
  ②之斷言含巢狀路徑 `records[0].label_definition.label_return_mode === '<非預設值>'`；
  ③之斷言 `records[0].decision_offset_bars === 3` 與 `-1` 之 fail-closed。
  **mutation（四條，皆須紅）**：
  (a) 契約新增第 5 個 `scenario` 值而不改 UI ⇒ ①紅
  (b) 把 `platform_random_bars` 或 `/search` 之 `scenario=A` 改成 enabled 湊數 ⇒ ①紅
      （前者不在 `accepted`，後者被 `pathExclusions` 排除）
  (c) 呼叫端 `page.tsx` 漏傳某維度之 opts ⇒ ②紅
  (d) 把某維度改回寫死 ⇒ ②紅
- 存活至：Phase 7（終）。
- 覆蓋風險：本閘為 Task 7.0／7.1 之防漂移守衛，存活至 Phase 7（終）。
  🔴 比對基準為 `selectable(path,dim)`（定義見 Task 7.1），**非**裸契約 `accepted`——
  其中 `accepted(dim)` 導出自契約檔、`pathExclusions` 導出自具名常數，二者皆非人工清單
  ⇒ 後續任一 Phase 於契約增值時本閘自動變紅，該紅為設計意圖，**不得以更新人工清單消紅**。**須同步**：Task 1.1 於契約新增之 reason 與 `filters` 屬非 enum 型欄位，
  **不在本閘涵蓋面內** ⇒ 本閘只保護五個批次維度、不保護契約全部欄位；此邊界須明寫於實作註解與測試名稱，
  避免日後誤以為「有機械閘＝契約全欄受保護」而略過 Task 1.1 之常數同步（見 Task 1.1 覆蓋風險）。
  另：`accepted` 為契約既有鍵，本 Task **不新增**該鍵到其他維度——只在存在時採用。
  🔴 **R8 邊界追記**：§D-3′ 後 IC 分析頁另有一組**分析參數** UI（Task 7.6 ③），其可操作集合
  由 **Task 7.6 驗收⑤** 守、其常數內容由 **Task 7.1 驗收⑨** 之集合相等守
  ⇒ 本閘**不擴及** `/ic-analysis`，避免同一斷言出現兩份。
  若日後把分析參數也納入本閘，須同時刪除 Task 7.6 ⑤，不得兩處並存。
- 邊界：涵蓋五個批次維度之三層；enum 型走①②、`decision_offset_bars`（`int`, `min: 0`）走②③。
  **不驗**「選了之後後端算出來對不對」——那是 G-2 與各 Phase 自身驗收的事。
- 不可做：**不得以人工清單當比對基準**（那就是第三份副本）。

**Task 7.3 — 動態揭露本批設定（取代原擬之固定文案）**
- 內容：匯出前顯示「本批：scenario＝X／**control_kind＝C**／進場價＝Y／報酬算法＝Z／
  決策位移＝K／lookahead 深度＝N（來源：<欄位清單>）／purge 將為 N 根」，
  **全部由實際設定導出**。
  🔴 `control_kind` 為 R7 群集 D 補入：Task 4.1b 之覆蓋風險宣稱本 Task 為其**嚴格超集**
  並要求 7.3 上線時移除 4.1b 之獨立實作，但本清單原**漏掉 4.1b 明列之 `control_kind`**
  ⇒ 取代後 UI 反而不再揭露該批 control kind（codex 命中）。
- 驗證：vitest 改任一維度 ⇒ 顯示字串隨之改變（斷言前後 `!==`）；
  `control_kind` 顯示值 `==` 匯出檔實際值（防寫死漂移）。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task **取代** Phase 4 之 Task 4.1b（後者為其真子集，見 4.1b 之覆蓋風險）；
  Phase 7 為最後一個 Phase ⇒ 本 Task 為本批揭露之終點，無更後續之覆蓋者。**須同步**：本 Task 之
  驗證「改任一維度 ⇒ 顯示字串 `!==` 前值」偵測不到「**新增**維度未被顯示」⇒ 維度涵蓋率由 Task 7.2
  之 enum 對證閘負責；兩者缺一，日後契約新增維度會靜默不揭露，回到 Phase 7 前言所述之病因。
- 邊界：只揭露，不改預設值。
- 不可做：不得寫死任何「正反例由 t0 條件決定」類之 scenario 專屬文案（D-7 通則化）。

**Task 7.4 — 條件 IC decay 之邊界揭露（CODEX-R2-P1-02／GROK-R2-P2-01；R8 依 §D-3′ 改寫措辭）**
- 內容（**R8 依 §D-3′ 改寫措辭；與 Task 4.1c 為同一文案來源，不得各寫一份**）：
  明文標示「條件 IC decay **曲線**（一次分析同時得到多個 h）**非本批交付**；
  附帶之 `future_*` 欄**不進入** `ic_feed`；
  要看不同答案窗，於 **IC 分析頁改答案窗重跑分析**，**不需重新匯出事件批**；
  一次得到整條曲線待 GAP-6。」
- 驗證：`grep -c "IC decay" docs/GAP3_EVENT_UX_SPEC.md` `>= 1`；vitest 斷言該說明現於匯出面板；
  **加驗收**：①選附帶欄 `[1,3,7]` ⇒ `window.horizon_bars` **不變**
  ②本 Task 與 Task 4.1c 之文案來自**同一 exported 常數／formatter**（斷言同一參考）
  ③文案中**不得**出現「重新匯出」作為換 h 之手段。
- 存活至：GAP-6（屆時若交付 multi-horizon IC 則撤除）。
- 覆蓋風險：GAP-6 可能取代。
- 邊界：只揭露邊界。
- 不可做：不得讓使用者以為多選附帶欄就會得到多條 IC。

**Task 7.5 — 事件後報酬表正／反／全體三組（使用者 2026-08-22 指定垂直排列）**
- 內容：報酬表由單一組改為**三組垂直排列**（正例組／反例組／全體組），每組各自跑完所有 horizon。
  🔴 **輸出形狀（R5 群集 C；三家獨立皆選同一掛法）**：回傳頂層仍為 §G S-1 之八鍵；
  三組寫入 `strata.by_label`，鍵集固定恰為 `positive`／`negative`／`all`（定義見 §G S-1a）。
  **不得**新增第九頂層鍵，**不得**以三次呼叫各產一表代替。
  🔴 **`control_kind` 之全體組規則（R5 群集 I；契約 `accepted` 三值全覆蓋）**：
  | `control_kind` | `strata.by_label.all` |
  |---|---|
  | `user_labeled_same_trigger` | **正常計算**（同觸發） |
  | `platform_same_trigger_rule` | **正常計算**（同觸發；R5 前未定義，本批補齊） |
  | `user_labeled_other` | `{"status":"not_computed","reason":"control_kind_not_comparable"}` |
  | 批內 distinct 值 `> 1` | `{"status":"not_computed","reason":"mixed_control_kind_in_batch"}`，**不取多數決** |
  （`platform_random_bars` 由匯入契約先行拒收，不會走到本表。）
  🔴 **兩個 reason 須先登記契約**（R5 群集 I：R4 版新增 `mixed_control_kind_in_batch`
  卻未登記任何 SoT，違反 §C「契約唯一真相源」與 D-6）：於
  `momentum/Analysis/contracts/ic_report_contract.json` 之 `report_sections` 新增
  `event_return_table` 物件，內含
  `not_computed_reasons: ["control_kind_not_comparable","mixed_control_kind_in_batch"]`
  與 `group_status_object_keys: ["status","reason"]`；程式與前端一律由該檔取字面。
  ⚠️ 此為**表格層** reason，**不得**混入 Task 6.0 之 `reasons.analysis_rejected`
  （那是 IC 分析入口之拒絕原因，兩者語意不同）。
  🔴 **`control_kind` 之傳遞點（R4 群集 F；CODEX-R4-P1-06）**：現行資料流**讀不到**該欄——
  `dedupe.py:112-115` 之 manifest context 只 merge
  `event_id,symbol,timeframe,label,scenario,direction`，**無 `control_kind`**；
  `tables.py:88-93` 之 `event_forward_return_table` 亦不收原始事件表。
  ⇒ 本批明定**唯一傳遞點＝`build_event_manifest` 之 manifest context**（於該 merge 清單加入
  `control_kind`），表格層一律由 `manifest.table` 取用。
  **禁止**另建第二份事件索引，也**禁止**在表格層寫死或讀不到時當 `None` 放行。
  **批內多值與 `not_computed` 之形狀**：見上表與 §G **S-7a**（狀態塊恰兩鍵）；
  本 Task **不重述**該形狀（避免第二份副本，同 §V 書寫規則之理由）。
- 驗證：`pytest tests/momentum/event_samples/ -q -k return_table_by_label` ≥10 條——
  ①`set(out.keys())` `==` §G S-1 之八鍵集合（證明三組**沒有**新增第九頂層鍵）
  ②`set(out['strata']['by_label'])` `== {'positive','negative','all'}`（不多不少）
  ③`positive`／`negative` 之列數各 `== len(horizons)`
  ④`control_kind == 'user_labeled_same_trigger'` ⇒ `all` 可算，且
    `positive` n ＋ `negative` n `==` `all` n
  ⑤`control_kind == 'platform_same_trigger_rule'` ⇒ `all` **可算**（本批補齊之第三值）
  ⑥`control_kind == 'user_labeled_other'` ⇒
    `out['strata']['by_label']['all'] == {"status":"not_computed","reason":"control_kind_not_comparable"}`
  ⑦同批混入兩種 `control_kind` ⇒ `all` 之 reason `== 'mixed_control_kind_in_batch'`
  ⑧`control_kind` 確實出現在 `build_event_manifest` 產出之 `manifest.table.columns`
    （斷言 `'control_kind' in manifest.table.columns`）——防「讀不到就當 `None`」
  ⑨兩個 reason 字面取自契約：`python3 -c "import json;c=json.load(open('momentum/Analysis/contracts/ic_report_contract.json'));s=c['report_sections']['event_return_table'];assert s['not_computed_reasons']==['control_kind_not_comparable','mixed_control_kind_in_batch'];assert s['group_status_object_keys']==['status','reason']"` rc=0
  ⑩`positive`／`negative` 兩組之統計值在三種 `control_kind` 下 **byte 級相同**
    （證明 `control_kind` 只影響 `all`）
  ⑪**前端實際顯示三組**（R6 群集 I；全棧三欄稽核產物）：
    `npx vitest run eventTablesPanelByLabel` ≥3 條——`EventTablesPanel` 讀
    `strata.by_label` 之三組並垂直排列；`all` 為 `not_computed` 時顯示其 `reason` 而非空表；
    🔴 現行該元件只讀 `sensitivity_micro` ⇒ 後端通過本 Task 之 pytest 仍會讓前端顯示舊的單一組
    （靜默失效）。**本 Task 之驗收不得只有 backend pytest。**
  **mutation（六條，皆須紅）**：三組提到新頂層鍵 ⇒ ①；`control_kind` 從 manifest merge 清單移除 ⇒ ⑧；
  前端仍讀 `sensitivity_micro` ⇒ ⑪；
  多值時改取多數決 ⇒ ⑦；`not_computed` 改回 `n=0` 空統計塊 ⇒ ⑥；
  把 `platform_same_trigger_rule` 當成 `other` 處理 ⇒ ⑤。
- 存活至：Phase 7（終）。
- 覆蓋風險：與 Task 4.2 同一表格，兩者須合併實作（4.2 先）。**須同步（R5 群集 C 改寫）**：
  本 Task 新增 `strata.by_label` ⇒ 這是**已核准之結構／數值輸出變更（D-4 合法變更）**
  ⇒ **須同一 commit 依 §G S-9 重建 G-2 golden 並在 commit message 說明**，
  且新 golden 須以 §G S-8 之**獨立 oracle** 驗證，不得以被測函式自產。
  ⚠️ 與此**分開**的另一件事：本 Task 於 `dedupe.py` 之 manifest context 加 `control_kind` 欄
  ⇒ 該加欄**不應**改變 G-2 bytes（`manifest` 本身不進輸出）⇒ 仍須保留
  「加欄前後 G-2 byte 級不變」之回歸；若真變了代表加欄意外進了輸出，須查明而非重凍。
  （R4 版只寫了後者、漏了前者，被 GROK-R5-P1-01 指出與 Task 4.2 之 D-4 規則不一致。）
- 邊界：只分組顯示與 `control_kind` 之傳遞；**不改**每組之計算式。
- 不可做：不得因分組而改變 `n_eff` 或 bootstrap 之定義；不得在表格層寫死 `control_kind`。

**Task 7.6 — IC 分析頁：批次事實欄唯讀揭露 ＋ 分析參數可設定（R4 群集 C／遺留 E；R8 依 §D-3′ 改寫）**

🔴 **R8 改寫之衝突與其解**：R7 版之「邊界」寫「**不允許**在 IC 頁修改批次設定」，
與 §D-3′「答案窗與報酬語意於 IC 分析頁由使用者給定」**直接互斥**。
解法＝**把原本混為一談的「批次設定」拆成兩類**（`-arch-shift.md` 之 Task 7.6 diff 即此意）：

| 類別 | 欄 | 在 IC 頁 | 寫回事件批？ |
|---|---|---|---|
| **批次事實欄** | `scenario`／`control_kind`／`direction`／`t0`／`label` | **唯讀揭露** | — |
| **分析參數**（`event_label_spec`） | `horizon_bars`／`entry_price_semantic`／`label_return_mode`／`decision_offset_bars` | **可設定**；初始值＝該批之匯出宣告（F-0） | 🔴 **否**——只作用於本次分析用副本 |

- 內容（三件事）：
  ① 事件批 detail 端點回傳該批之**五維度實際值**（既有需求，不變）。
  ② IC 分析頁選批後：**批次事實欄唯讀揭露**，文案模板與 Task 7.3 之匯出面板揭露
     **共用同一實作**（不另寫第二份）。
  ③ IC 分析頁新增**分析參數區**：`event_label_spec` 之四欄。
     - `horizon_bars`：任意正整數，可自由設定（§F-1′ 不限制 h）。
     - 報酬語意三元組：本批**可操作集合鎖定 F-1′**，其餘值 disabled ＋顯示
       §F-5′ 之開放前置理由。排除集合沿用 Task 7.1 之 `EVENT_DIM_PATH_EXCLUSIONS`
       （新增路徑鍵 `'/ic-analysis'`），**不另建第二份排除清單**。
     - 🔴 同時揭露 **本次答案窗之可算／缺筆數**（Task 4.3／5.3 由匯出層移來之揭露）。
     - 🔴 同時揭露 **本次 purge 下界**，其式之權威在 §D-3′-a（ii），本區只顯示結果。
- 驗證（pytest 一組 ＋ vitest 一組，逐條如下）：
  `pytest tests/api -q -k event_batch_detail_dims` ≥2 條——斷言 detail 回應之維度鍵集
  **集合相等**於 `{scenario, control_kind, entry_price_semantic, label_return_mode,
  decision_offset_bars}`（🔴 **明列鍵名、不用計數字面**；理由見本 Task 覆蓋風險），
  且各值 `==` 該批落檔記錄之實際值（非預設值）；
  `npx vitest run icEventBatchDisclosure` ≥6 條——
  ①批次事實欄之各段文字皆出現，且與 Task 7.3 呼叫**同一 exported formatter**
    （斷言為同一函式參考，非各自複製）
  ②改批次之任一事實欄 ⇒ 顯示字串 `!==` 前值
  ③**批次事實欄不可編輯**：斷言其 DOM 節點無可輸入控制項（`queryByRole('combobox'/'textbox')` 為 `null`）
  ④**分析參數可編輯**：`horizon_bars` 有可輸入控制項；輸入 `7` ⇒ 送出 payload 之
    `event_label_spec.horizon_bars === 7`
  ⑤三元組之**可操作**選項集合 `==` §F-1′ 之唯一三元組；其餘值 disabled 且顯示理由
  ⑥**改分析參數不改事件批**：改 `horizon_bars` 後重查 detail 端點，
    該批落檔記錄之 `label_definition.window.horizon_bars` **不變**（證明不回寫）
  **mutation（四條，皆須紅）**：把揭露文案改成前端寫死 ⇒ ①；
  把批次事實欄改成可編輯 ⇒ ③；三元組開放 F-1′ 以外之值 ⇒ ⑤；
  分析參數回寫事件批 ⇒ ⑥。
- 存活至：Phase 7（終）。
- 覆蓋風險（R6 群集 B 追記）：驗收改以**明列鍵名之集合相等**之理由——R4 版寫「detail 回應
  含六個鍵」，R5 群集 G 把批次維度六改五時該字面未同步，**三家全員命中**；
  且因未列鍵名，Agent 無法唯一決定第六鍵，可能把已移出之 `counterexample_kind` 加回。
  🔴 **R8 追記**：本 Task 由「只讀不寫」改為「讀 ＋ 收分析參數」⇒ **確實改動 IC 計算路徑**
  （分析參數餵 Task 7.0b 之 producer）；原「不改任何 IC 計算路徑 ⇒ 無後續 Phase 覆蓋」
  之理由已不成立，改由 Task 7.0b 之驗收⑧⑨⑪承接該路徑之正確性。
  **須同步**：與 Task 7.3 共用 formatter ⇒ 7.3 之事實欄集合擴充時本頁自動跟進；
  分析參數之欄集與 Task 7.0b 之 `event_label_spec` 為**同一組**，欄位增減須同批改。
- 邊界：批次事實欄**只揭露、不可改**；分析參數**只作用於本次分析**、**不回寫**事件批。
- 不可做：不得只在 tooltip 顯示 `importId` 就算揭露（使用者要的是語意，不是識別碼）；
  不得讓分析參數以任何形式回寫已落檔之事件批（那會使同一批事實隨分析而變，
  §D-3′ 之整個分層即為此而設）。

**Task 7.7 — Feature run `time_range` 與事件期之對證（R4 群集 C；R5 群集 D／E 改寫；R8 增訂⑦ picker 之 decision_at 映射）**
- 內容：`RunInfo`（`api/models/feature_factory_models.py:116-133`）**無 `time_range`**，
  而 manifest artifact **已有**（`feature_reader.py:455`；非 legacy 路徑之產生處＝
  `feature_storage._resolve_l7_v2_time_range`）⇒ 資料在後端、前端拿不到，
  IC 分析可在「特徵 run 根本不涵蓋事件期」時照送。
  ① **wiring（本 Task 之一部分，非另開票）**：
     `RunInfo.time_range: Optional[dict]`，形狀與 manifest **同形**：`{"start": str|None, "end": str|None}`。
     🔴 **型別依實碼裁定，非投票**：`_resolve_l7_v2_time_range` 之回傳型別為
     `Dict[str, Optional[str]]` ⇒ **值為字串，不是 epoch 毫秒整數**
     （grok 之修法寫 `int|None`，與實碼不符，不採）。
     ⚠️ **該字串之實際格式見 ④**——`_format_manifest_value` 只對有 `isoformat` 屬性者
     走 ISO，其餘走 `str(value)`；實測現存 manifest 皆為 **epoch 秒數字字串**。
     （R7 群集 C：R6 版此處斷言「是 ISO-8601 字串」而 ④ 已裁定為 epoch 秒字串，
     同一 Task 內兩處互斥，兩家獨立命中——主委修 ④ 未同步 ①。）
     service 端 `_browse_metadata_for_run` 由 manifest **原樣帶出**（禁在此層轉型別）；
     `/features/runs` response 與前端 `types.ts` 之 `RunInfo` 均須含此鍵。
  ② **時間基準之換算（R5 群集 D；三家一致「逐列取事件列之 tf」）**：
     `bar_ms(e) = TIMEFRAME_SECONDS[e.timeframe] * 1000`
     （`TIMEFRAME_SECONDS` 定義於 `momentum/core/constants.py:6`，七值閉集）。
     🔴 **禁止**取 run 之 tf、批內 `max(tf)`／`min(tf)`／平均——**逐列用該列自己的 `timeframe`**；
     批內多 TF **允許**（不整批拒收），但任一列之 `e.timeframe` 不在 `TIMEFRAME_SECONDS`
     ⇒ 整批 fail-closed，reason `== "feature_coverage_unknown_timeframe"`。
     此為與 R3 之 future72 單位錯**同型**之缺口（grok 明指），故單位來源須寫死於本欄。
  ③ **containment policy（唯一；R5 群集 E 修正左界）**：
     優先取 alignment receipt 之既有欄位，**不自行以裸 `horizon_bars` 加時間戳**：
     ```
     required_start(e) = receipt.decision_at_ms(e)      # = t0 往前 decision_offset_bars 根
     required_end(e)   = receipt.label_end_ms(e)        # = 含答案窗之右界
     ```
     無 receipt（如純 fixture 推導）時才以 ② 之 `bar_ms(e)` 計算同義值。
     放行條件（**批內全部列皆須成立**）：
     `run_start_ms <= min_e required_start(e)` 且 `max_e required_end(e) <= run_end_ms`。
     🔴 左界用 `decision_at_ms` **而非** `min(t0)`：IC 之特徵截止規則為
     `max_close_ms <= decision_at`（`ic_feed.py`），`decision_offset_bars = k > 0` 時
     `decision_at < t0` ⇒ 用 `min(t0)` 會放行「run 未涵蓋決策時點」之批次（fail-open 窗口）。
     **不得**在本 Task 任何處殘留 `min(t0)` 之舊字面。
  ④ **`time_range` 字串 → epoch ms 之 parse 規則（R6 群集 G：三家以真實 manifest 推翻 R5 版）**：
     🔴 **實測事實**：現存非 legacy manifest 之 `time_range` 為 **epoch 秒之數字字串**，例
     `data_cache/features/BCHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/feature_manifest.json`
     → `{"start": "1704067200", "end": "1777330800"}`（兩值型別皆 `str`）。
     R5 版指定之 `datetime.fromisoformat(s)` 對此**直接 raise**
     ⇒ 照 R5 版實作會把**全部現存 run** 判為 parse failure。三家全員命中，主委獨立覆核屬實。
     **解析順序（唯一；先數字後 ISO）**：
     1. `s` 去除前後空白後**全為十進位數字**（可含前導 `-`）⇒ 視為 **epoch 秒**，
        `epoch_ms = int(s) * 1000`。
        合理性檢查：`0 < int(s) < 4102444800`（＝2100-01-01）；超出 ⇒ fail-closed。
     2. 否則以 `datetime.fromisoformat(s)` 解析：**tz-aware ⇒ 轉 UTC epoch ms**；
        **tz-naive ⇒ fail-closed**（把 naive 當 UTC 是假設，假設錯誤會使覆蓋判斷整體偏移）。
     3. 兩者皆不成 ⇒ fail-closed。
     1–3 之任何 fail-closed 皆回 reason `== "feature_coverage_unknown_timestamp_format"`
     （取代 R5 版之 `feature_coverage_unknown_timestamp_format`；後者語意過窄，涵蓋不了數字字串路徑）。
     ⚠️ **不得**以「猜一個格式試試看」實作——三條分支之判定須為封閉且可逐條測試。
     📌 **本項之處理過程保留為範例**：R5 版由主委補充並**自行具名標為「待 R6 裁定」**，
     R6 三家即以真實 manifest 打穿之。該「主委補充須具名待裁」之作法有效，予以保留。
  ⑤ **legacy run**：`time_range` 為 `{"start": None, "end": None}`（`feature_reader.py:455`）
     ⇒ **不得**視為「涵蓋全部」而放行，一律 fail-closed，
     reason `== "feature_coverage_unknown_legacy_run"`。
  ⑥ 不滿足 ③ ⇒ fail-closed，`capability_status == "unavailable"`、
     reason `== "feature_coverage_insufficient"`。
  ⑦ 🔴 **IC picker 之 feature timestamp 映射（CODEX-R8-P0-03；R8 新增）**：
     現行 `eventT0MsToIcTimestamps`（`frontend/src/lib/api.ts:1042-1048`）把
     **原始 `t0` ÷1000** 當成 IC 主線之 `event_timestamps`。
     §D-3a 已裁定「每列 feature sample key 須為 receipt 之
     `last_bar_open_ms`／`decision_at_ms`，**不是原始 t0**」
     ⇒ `decision_offset_bars = k > 0` 時，現行映射會把特徵取樣點推到**決策時點之後**，
     與 `ic_feed.py:76` 之 `feature_cutoff_rule = max_close_ms_le_decision_at` 互斥。
     **處置**：映射改由**後端**於分析時依 receipt 產生（隨 Task 7.0b ② 之 `event_import_id`
     入後端後，前端不再需要自算 timestamps）；
     前端之 `eventT0MsToIcTimestamps` **移除**，`useICAnalysis` 不再送 `event_timestamps`。
     映射不合法（該 t0 無對應 bar）⇒ fail-closed，reason 取自契約既有
     `alignment_failure_reasons.missing_bar`；
     兩個事件映射到**同一** decision bar ⇒ fail-closed，reason `duplicate_bar`。
     🔴 **不新增 reason**（D-6：能用契約既有字面就不擴清單）。
  ②④⑤⑥ 所列之 reason 一律登記於 `ic_report_contract.json` 之 `reasons.analysis_rejected`
  （與 Task 6.0 同一處；程式與前端由該檔取字面；**最終集合見下方驗證②，本欄不重述**）。
  ⑦ 所引之 reason 集合恰為 `{missing_bar, duplicate_bar}`，取自
  `event_import_contract.json` 之既有 `alignment_failure_reasons`，
  **不登記於** `analysis_rejected`（層次不同：對齊失敗 vs 分析入口拒絕）。
- 驗證：`pytest tests/api -q -k feature_coverage_gate` ≥9 條——
  ①`assert 'time_range' in RunInfo.model_fields`；且讀一份**真實** manifest 斷言
    `start`／`end` 原樣進 `/api/v1/features/runs`（型別為 `str` 或 `None`，未被轉型）
  ②`analysis_rejected` 之**最終**內容 `== ['feature_count_exceeds_cap',
    'feature_coverage_insufficient', 'feature_coverage_unknown_legacy_run',
    'feature_coverage_unknown_timeframe', 'feature_coverage_unknown_timestamp_format']`
  ③小型跨日期 fixture：事件期全落在 run 區間內 ⇒ 放行（`capability_status != "unavailable"`）
  ④`decision_offset_bars = 3` 且 `run_start` 落在 `decision_at` 與 `t0` **之間**
    ⇒ **fail-closed**，reason `== "feature_coverage_insufficient"`（左界回歸；R5 群集 E）
  ⑤`max(t0)` 在區間內但 `label_end` 超出右界 ⇒ **仍 fail-closed**（右界含答案窗）
  ⑥**1h 與 12h 同 `t0`、同 `horizon_bars` 之對照**：兩者之 `required_end` 相差 12 倍
    ⇒ 12h 之 fixture 須被擋、1h 之須放行（證明未寫死單一 tf）
  ⑦批內混 1h 與 12h ⇒ **逐列各用自己的 tf**，結果與逐列單獨計算一致
  ⑧`e.timeframe` 為 `'3h'`（不在 `TIMEFRAME_SECONDS`）⇒ fail-closed，
    reason `== "feature_coverage_unknown_timeframe"`
  ⑨`time_range == {"start": None, "end": None}` ⇒ fail-closed，
    reason `== "feature_coverage_unknown_legacy_run"`；
    `start` 為 tz-naive ISO 字串 ⇒ fail-closed，reason `== "feature_coverage_unknown_timestamp_format"`
  ⑩**epoch 秒數字字串正例**（現存 run 之實際格式）：`time_range == {"start":"1704067200","end":"1777330800"}`
    ⇒ **解析成功**（`1704067200 * 1000` 得 epoch ms）且覆蓋判斷正常進行——
    此條防「照 R5 版實作而擋下全部現存 run」之回歸
  ⑪`start == "99999999999"`（超出 2100-01-01）⇒ fail-closed，
    reason `== "feature_coverage_unknown_timestamp_format"`
  ⑫🔴 **decision_at 映射（內容⑦；R8 新增）**：`decision_offset_bars = 3` 之批次
    ⇒ 送入 `ic_feed` 之每列 feature sample key `==` receipt 之
    `decision_at_ms`（換算後）且 `!=` 原始 `t0`；`k = 0` 之批次兩者相等（對照組，
    證明本條不是恆真也不是恆假）
  ⑬映射不合法（某 t0 無對應 bar）⇒ fail-closed，reason `== "missing_bar"`；
    兩事件映射到同一 decision bar ⇒ fail-closed，reason `== "duplicate_bar"`
  ＋`npx vitest run icEventPickerNoLocalMapping` ≥2 條——
  ⑭`grep -c "eventT0MsToIcTimestamps" frontend/src/` `== 0`（前端不再自算映射）
  ⑮`useICAnalysis` 送出之 payload **不含** `event_timestamps`、**含** `event_import_id`
  **mutation（八條，皆須紅）**：左界改回 `min(t0)` ⇒ ④；右界不含答案窗 ⇒ ⑤；
  改用 run 之 tf 或批內 `max(tf)` ⇒ ⑥⑦；legacy 之 `None` 改成放行 ⇒ ⑨；
  未知 tf 改成沿用預設 ⇒ ⑧；fail-closed 改成只回警告字串 ⇒ ③；
  把解析改回「只用 `datetime.fromisoformat`」⇒ ⑩須紅（R6 群集 G 之回歸樁）；
  🔴 把 feature sample key 改回原始 `t0` ⇒ ⑫須紅（R8 之回歸樁）。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task 之 gate 位於 IC 分析**入口**，與 Phase 6 之特徵數止血閘（Task 6.1）同在入口
  但為**不同拒絕條件、不同 reason**（覆蓋不足 vs 特徵數過大）⇒ 兩者須各自回應、不得合併。
  **須同步**：Task 6.1 隨 GAP-6 之分塊計算被取代時，本 Task **不隨之作廢**——
  日期錯配與規模無關，分塊計算上線後仍須此對證（codex R4 原話：等待分塊計算不會使日期錯配變安全）。
- 邊界：只驗「特徵覆蓋範圍是否包含事件期」；不驗特徵值本身之品質。
- 不可做：不得以「使用者自己會看」替代機械對證；不得在無法取得 `time_range` 時預設放行。

---

## §V 驗證策略與邊界測試目錄

### §V 書寫規則（R5 consult 裁；三家全員同向）

🔴 **§V 是索引，不是第二份規格。**
出處＝R4／R5 連兩輪之自傷共 8 條，形態一致：**改了 §P 之權威定義，未同步 §V 之複述**
（最嚴重者＝V-11 仍寫 `contractAccepted` 而 Task 7.1／7.2 已改 `selectable(path,dim)`，
照 V-11 實作會強迫 UI 啟用 A／B、推翻路徑級限制）。
**複述即第二份副本，副本必然漂移**——故本節不靠紀律，改以規則＋機械閘消除複述本身。

- 凡 V 列對應某個 Task 者：「手段／通過條件」**只寫**「執行 Task `<id>` 之驗證欄，其命令 rc=0」
  （可加一句路徑對照），**禁止**重寫集合等式、公式、enum 字面清單或 mutation 條文。
- 唯一例外：跨多 Task 之整合列（如 V-M）可列 Task ID **清單**，仍不得另造第二套通過條件。
- 機械強制：`scripts/spec_v_task_ref_check.sh`（掛 `narrow_check_router.sh`）。

| ID | 驗什麼 | 手段 | 通過條件 |
|---|---|---|---|
| V-1 | CSV 對映之 label **照抄正確** | 真實 CSV fixture → 匯入 → 逐列比對 | 每列 `label ==` CSV 指定欄之值。**誠實邊界：本項不證明使用者選對欄**（D-1，語意不可機械證明）；選欄風險由 V-1b/V-1c 降低 |
| V-1b | 可疑欄警示有鑑別力 | fixture 含 3 個二元欄 | 警示列出另外 2 個（`len == 2` 且集合相等） |
| V-1c | provenance 可追 | 匯入後讀 receipt | `column_mapping.label ==` 送出值；`source_file_digest` 存在且 `!=` 空 |
| V-2 | 對映缺失／欄不存在／label 非二元／異質列 各自 fail-closed | 四個反例各一測 | 各得對應 reason；**落檔數 `== 0` 且 task store 筆數不變**（CODEX-R1-P1-04：不只驗落檔，須驗無其他狀態副作用） |
| V-3 | CSV 與 JSON 路徑**共用同一函式** | **兩重 oracle**（R1 三家指出單靠 sha256 相等不成立） | ①靜態：AST 斷言 CSV route 呼叫 `/import-events` 之同名驗證函式 ②行為：mutation——把該共用函式改壞，**兩條路徑之測試須同時轉紅**（只有一條紅 ⇒ 存在平行實作） |
| V-4 | `event_id` 跨路徑一致（D-2） | 同批事件之 JSON 匯出 vs CSV 回灌 | `event_id` 集合 `==`（集合相等，非逐列順序） |
| V-5 | 刪除後該批消失 | 刪除 → 列表／analyze 各查一次 | 列表無該批；analyze status_code `== 404` |
| V-6 | 附帶 `future_*` 欄與**分析層** `label_value` 分離；匯出端不寫 `label_value`；換 h 不需重匯出（D-3′） | **執行 Task 4.1／4.1c 之驗證欄全部條目**；§V 不重述斷言字面 | 兩 Task 之命令皆 rc=0 且條目數 `>=` 各自所列 |
| V-7 | `.source.json` 誤傳之訊息含正解 | 上傳 `.source.json` 當事件檔 | status_code `== 400` 且訊息含 `source_file` |
| V-8 | 止血閘生效且**未載入大矩陣**（D-5） | **執行 Task 6.4 之驗證欄全部條目**（其 V-8 三項斷言與採樣時點）；§V 不重述斷言字面 | `pytest tests/api -q -k ic_stop_gate_alive` rc=0 且條目數 `>=` Task 6.4 所列；量測工具與禁令見 Task 6.2 |
| V-9 | 止血閘不誤擋 | 小 run（15 特徵）呼叫 | status_code `== 200` **且任務確實被建立**（task store 筆數 +1；R1 指出只驗 200 不足） |
| V-10 | tooltip 與 glossary 不漂移 | 逐表頭比對 | tooltip 文字 `==` glossary `definition` |
| G-1 | IC 主線未被波及 | `python3 scripts/gap3_freeze_golden.py --check` | 通過。**誠實邊界：不涵蓋事件路徑**（D-4） |
| G-2 | 事件路徑數值未意外改變 | 本批新建之事件 golden | 逐 horizon exact return（`atol=0`）／NaN mask／PIT anchor 全等；Task 4.2 之合法變更須同 commit 更新並說明 |
| G-3 | **分析時** `label_value`／window／purge／feature timestamp map 未意外改變（D-3′） | 本批新建之 analysis-label golden（§G G-3） | `pytest tests/momentum/event_samples/ -q -k analysis_label_golden` rc=0；覆蓋面與可證偽條之唯一定義見 §G G-3。**誠實邊界：G-2 涵蓋不到此路徑**（兩者不可互相替代） |
| V-16 | 分析時 producer 之支援矩陣、purge 下界與前端不持有 `label_value`（D-3′／D-3a／F-1′／F-2′／F-4′） | **執行 Task 7.0b 之驗證欄全部條目**；§V 不重述支援矩陣與 purge 公式 | Task 7.0b 之命令皆 rc=0 且條目數 `>=` 其所列；purge 下界之唯一定義見 §D-3′-a（ii） |
| V-17 | IC 分析頁：批次事實欄唯讀、分析參數可設定且不回寫（D-3′） | **執行 Task 7.6 之驗證欄全部條目**；§V 不重述斷言字面 | Task 7.6 之命令皆 rc=0 且條目數 `>=` 其所列 |
| V-11 | 五維度全接出、不可漂移、且**選值真的傳到落檔**（Phase 7） | **執行 Task 7.2 之驗證欄全部條目**（三層＋其 mutation）；§V 不重述任何斷言字面 | `npx vitest run contractEnumWiring` rc=0 且用例數 `>=` Task 7.2 所列；集合層之唯一基準 ＝ Task 7.1 定義之 `selectable(path, dim)` |
| V-12 | lookahead 深度由標註導出、未知即擋（D-7 之 L1/L2/L3） | **執行 Task 1.10／1.11／1.12／2.1b 之驗證欄全部條目**；§V 不重述深度公式與 fixture 條文 | 各該 Task 之命令皆 rc=0；深度公式之唯一定義見 Task 2.1b，改名攻擊之判準見 Task 1.10。🔴 **R8 邊界**：本列只管**深度導出**；深度與分析時 h 合成 purge 下界之 `max` 式屬 §D-3′-a（ii），由 **V-16** 承接，兩列不重疊 |
| V-14 | IC 分析頁揭露該批五維度 | **執行 Task 7.6 之驗證欄全部條目**；§V 不重述斷言字面 | `pytest tests/api -q -k event_batch_detail_dims` 與 `npx vitest run icEventBatchDisclosure` 皆 rc=0 且條目數 `>=` Task 7.6 所列 |
| V-15 | 特徵覆蓋對證 fail-closed | **執行 Task 7.7 之驗證欄全部條目**；§V 不重述 containment 邊界公式 | `pytest tests/api -q -k feature_coverage_gate` rc=0 且條目數 `>=` Task 7.7 所列；containment 之唯一定義見 Task 7.7 |
| V-13 | 報酬表正／反／全體三組 | **執行 Task 7.5 之驗證欄全部條目**；§V 不重述斷言字面 | `pytest tests/momentum/event_samples/ -q -k return_table_by_label` rc=0 且條目數 `>=` Task 7.5 所列 |
| V-M | 可證偽性 | **逐 Task** 列出：mutation 內容、命令、預期紅、實際 receipt 路徑 | 逐條紅；還原後全綠。**不得只寫「逐條紅」**（CODEX-R1-P0-06） |

**測試設計紀律**（本 session 已四次交出假綠，逐條套用）：
1. 斷言**中間值與副作用**，不只斷言例外型別或 HTTP 碼（V-2／V-8／V-9 皆已加 store 筆數斷言）。
2. fixture 不得把受測依賴設成 `None` 而使受測路徑整段跳過。
3. 「共用實作」不可只靠輸出相等證明，須有**改壞共用點 ⇒ 兩路同時紅**之 mutation（V-3）。
4. 量測型驗收須定義**口徑、基線、採樣點、工具**，否則必假綠（V-8）。

---

## §R 回退

各 Phase 獨立 commit，可逐一 `git revert`。
Task 1.1（契約）為其他 Task 之前置，回退須連同 Phase 1/2 一併回退。
🔴 **Phase 4 之回退性已於 R8 改變**：原為「純疊加（D-3 之 (a)），回退不影響既有 label 語意」；
§D-3′ 後 Phase 4 **移除**匯出端之答案窗與 `label_value` ⇒ 單獨回退 Phase 4 會使匯出端
恢復寫 `label_value`，而分析層（Task 7.0b）仍會自行計算一份 ⇒ **同一批出現兩份 `label_value`**。
⇒ Phase 4 與 Task 7.0b／7.6 為**同一回退單元**，須一併 revert。
Phase 6 為純新增之前置檢查，回退即恢復「可按但會吃垮機器」的現況（不建議）。

---

## §N N/A 登記

| 段 | 理由 |
|---|---|
| 使用者問題 #7 | 回答性非施工項：B8/B8b 來自 `POST /case/events/{id}/analyze` 當下計算、價格讀 `data_cache/kline_cache.h5`（`pipeline.py:78-82`），**不經 Feature Library**（已答） |
| 使用者問題 #8／#10 | 🔴 **殘留已於 R4 撤回，改為本批 Task 7.7**（R4 群集 C；GROK-R4-P0-03 指出 §C0 與本表互斥）。已答部分＝事件型兩表不需 Feature Library、IC 分析才需要。**原「未答部分」＝「事件標的/日期只需被 Feature Library 涵蓋即可」**，R3 以 `blocked-by` GAP-6 登記為具名殘留——**該登記錯誤**：三家 R4 獨立判定此為**資料正確性**缺口（特徵 run 不涵蓋事件日期仍可送 IC），非規模效能問題，且小型跨日期 fixture 即可驗、不需等 GAP-6 之分塊計算。依 §C0 條文 2（資料正確性類不得降級為具名殘留放行）⇒ **本批做**，落點＝**Task 7.7**（`RunInfo` 暴露 `time_range` ＋ containment 對證 ＋ fail-closed）。本列保留為撤回紀錄，不得刪 |
| #9b 規模防護本體 | 排入 GAP-6（registry #6「430K 規模防護」），使用者 2026-08-22 裁定 |
| **純事件研究模式（新模組）** | **具名殘留，另立模組**。使用者 2026-08-22 提出第三種用途：「單純想知道某事件（大漲 10% 後／從高點跌 15% 後）之後 1/5/10/30/60 天或任意天的漲跌數值」。此為 **event study**，與分類、條件 IC 皆不同：**不需 label、不需答案窗、不需 purge**（無訓練即無洩漏）。已查證只需 kline（`pipeline.py:78-82` 之 `bars_from_kline_cache`），**與 IC-Analysis 無關**。<br>現況缺口：契約 `required_fields` 含 `label`／`label_definition`／`control_kind`／`scenario`，且 `scenario` enum 僅 `A/B/C/two_stage`（皆為預測／確認型），**無「純描述」值** ⇒ 使用者為了看報酬分布被迫先編一個假 label。<br>三值理由＝`user-ruling`：使用者 2026-08-22 逐字「這可以未來另做一個模組研究就好」。**排程**：另立模組票，不在本批。<br>**定位**：這是**另一種用途**（想知道某類事件的後續行為分布時使用），**不是分類流程的前置條件**。<br>🔴 **主委原判斷已撤回（使用者 2026-08-22 糾正，糾正成立）**：原寫「研究順序應為事件研究 → 分類，使用者現況是直接跳到分類」。**該判斷錯誤**——它假設「標籤 ＝ 某單一根的報酬」，那種情況才需要先知道訊號在第幾根衰減。使用者的標籤是**複合形狀定義**（例「t0 +5% 且 future_1≥+2% 且 future_2≥+2% 且 future_4≥+1%」＝「漲上去且撐得住」），那是交易意圖之直接指定，**本就不需前置研究**；用「全體事件的平均衰減曲線」去推導「我要抓哪種形狀」方向亦不對。<br>**真正成立的機械約束只有 D-7**（答案窗須 ≥ 標籤最遠觸及之根數），該約束由使用者的定義**直接推導**，與研究順序無關。<br>衰減研究之**可選**用途：回頭優化既有定義（如「卡在第 4 根是否提早收手」「future_4 ≥ +1% 門檻是否過鬆」），屬事後精修而非動手前的必要功課。 |
| **觸發條件需回看歷史（如「從高點跌 15%」）** | **待盤點**。使用者 2026-08-22 提出之事件形態需回看歷史高點；現行案例搜尋是否支援此類回看型觸發條件**尚未查證**。三值理由＝`needs-research`。**owner**：主委。**觸發**：純事件研究模組開票時一併盤點。 |
