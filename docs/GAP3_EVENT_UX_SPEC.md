# GAP-3 事件型 UAT 缺口修補 — SPEC

出處：使用者 2026-08-22 跑完 UAT B1–B13 後提出的 10 條問題。
本 SPEC 涵蓋**事件型**那批（#0/#1/#2/#3/#4/#5/#6 ＋ #9a 止血閘）。
#7 為回答性問題（已答，見 §N）；#8/#10 列具名殘留（見 §N）；#9b 規模防護本體排入 GAP-6。

**版本**：R2（依 R1 三家 24 條 findings 全面改寫；R1 六條 P0 之處置見 §D）

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

**D-3（GROK-R1-P0-02）Phase 4 多 horizon 之語意先裁定**
採 grok 所列之 **(a)**：多選**只影響匯出檔帶哪些 `future_{h}bar_return` 欄**（供 Excel 分析）；
`label_value` 與 `label_definition.window.horizon_bars` **仍綁單一「主答案窗」**（另一個單選）。
理由：①契約 `window.horizon_bars` 為單一 int，(b)/(c) 都要改契約與 230 條底線測試，
超出本批範圍 ②grok 查證 `/search` 之 CSV **早已輸出 `future_1..12bar_return` 全欄**
⇒ 使用者「看整條曲線」的需求在 CSV 端已滿足，缺的是**事件匯出檔**帶不帶這些欄。
⇒ 契約不變、label 語意不變、只是匯出檔多帶欄位。

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

**處置（三層）**：
1. **CSV 上傳路徑**：答案窗**預設取檔內最大可用 horizon**（保守）；使用者可往下調，
   但須明確勾選「我的篩選條件未用到超過第 N 根」之聲明，UI 明示此為**無法驗證的聲明**。
2. **系統內篩選路徑（Phase 2）**：系統確知使用者用了哪些欄 ⇒ **自動導出 `max(N)` 並鎖定**，
   使用者不得調低。**這使 Phase 2 的定位從「方便」升級為「把不可驗聲明轉成機器可證事實」**
   （原 SPEC 把 Phase 2 當錦上添花，定位錯誤，本版改正）。
3. 答案窗欄位接受**任意正整數**，不限 1..12（使用者：「12 根也是我自己訂的，沒有理論根據，
   會不會用到 12 根以外也有可能」）。

**已知影響（須告知使用者，不隱瞞）**：使用者既有批次 `20260822T011331Z-eb210a16`
以 `purge 2` 產出（780 筆：train 542／test 236／purge 2）。若其篩選條件實際用到 future_4，
該批隔離不足 ⇒ **其 IC／分類結果應視為可能偏樂觀**；修補後重匯即乾淨。

---

## §A 假設與待使用者確認

| # | 假設 | 狀態 |
|---|---|---|
| A-1 | #0 採 (c)：匯出前篩選 **與** 上傳自篩 CSV 兩者都做，先做上傳 | 已確認 |
| A-2 | #9a 止血閘採「直接擋下」而非「警告後容許硬跑」 | 已確認 |
| A-3 | #9b 排入 GAP-6 | 已確認 |
| A-4' | `label` 為**使用者聲明**，系統不推斷、不預設、不宣稱其正確；未指定 ⇒ fail-closed | R1 三家一致，已改寫（§D-1） |
| A-5' | 批次層預設值對整批一致；**異質列須顯式拒收**（非靜默取第一列） | R1 codex 指出原 A-5 不足，已補（Task 1.8） |
| A-6 | D-3 之 (a) 方案（多選只影響匯出欄，label 仍單一主答案窗）符合使用者「答案窗不夠用」之真實訴求 | ⚠️ **主委裁定**，請委員複核；亦請使用者於白話閘確認 |

**已確認**（使用者 2026-08-22 回覆逐字）：
- A-1：「#0選(c)」
- A-2：「看你怎麼設計都可以」
- A-3：「將#9排在Gap-4(Pooled IC), Gap-5(容量接線)，併入Gap-6規模防護之後」
  ＋「這樣我就等Gap-6之後再針對整個IC-Analysis做測試就好。先把事件型做完」

**待使用者確認：無**（A-4'／A-5'／A-6 為技術主張，依「技術決策委派委員會」由委員裁決；
A-6 因改變使用者可見行為，另於白話閘向使用者說明）。

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
凍結 `event_forward_return_table` 之輸出為 sha256；逐 horizon 驗
① exact return 值（`atol=0`，位元組相等）②NaN／缺 bar mask 位置 ③PIT anchor（t0 對應根）。
Task 4.2 若改預設 horizons，**必須同步更新 G-2 並在 commit message 說明改了什麼、為什麼**
（合法變更），而非靜默重凍。

---

## §P Phase 與依賴

### Phase 1 — 使用者自篩 CSV 匯入（依賴：無）　【#0(b) ＋ #5】

**Task 1.1 — 契約先行：新增 reason 與 label_definition.filters**
- 內容：`import_failure_reasons` 增 `column_mapping_missing`／`column_not_found_in_file`／
  `label_column_not_binary`／`heterogeneous_rows_in_batch`（15→19）；
  `label_definition.fields` 增 `filters`（型別＋`_doc`）以承載 Phase 2 之篩選條件（D-6）。
- 驗證：`python3 -c "import json;c=json.load(open('momentum/Analysis/contracts/event_import_contract.json'));assert len(c['import_failure_reasons'])==19;assert 'filters' in c['label_definition']['fields']"` rc=0。
- 存活至：Phase 6。
- 覆蓋風險：無後續 Phase 刪改此四值與 `filters`。
- 邊界：只加，**不動**既有 15 個 reason 之字面與順序。
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
- 驗證：同一批事件「JSON 匯出檔」與「CSV 回灌」之 `event_id` 集合 `==`（集合相等斷言）；
  改 1 byte 重傳 ⇒ `source_file_digest !=` 原值。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：digest 綁**上傳的位元組**，不綁解析後的 DataFrame。
- 不可做：**不得發明新的 event_id 演算法**（R1 兩家獨立指出此為 BLOCKING）。

**Task 1.4 — t0 單位偵測**
- 內容：沿用契約 `ms_magnitude_min`；秒級 ×1000；無法判定 ⇒ `invalid_timestamp_unit`。
- 驗證：三組 fixture（ms／秒／不合法）各 1 測；ms 值精確比對 `== 1704067200000`。
- 存活至：Phase 6。
- 覆蓋風險：無。
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
- 覆蓋風險：無。
- 邊界：只記錄，不參與任何計算。
- 不可做：不得省略 `source_file_digest`（否則無法對證來源）。

**Task 1.7 — 可疑欄警示（D-1）**
- 內容：預覽階段掃描所有欄，列出**其他也是二元（值域 ⊆ {0,1} 或 {true,false}）的欄名**，
  提示「這些欄看起來也像標記，請確認你選的是哪一個」。
- 驗證：fixture 含 3 個二元欄 ⇒ 警示列出另外 2 個（`len == 2` 且集合相等）。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：只警示不阻擋（語意不可機械判定，見 D-1）。
- 不可做：不得因為只有一個二元欄就自動選它（A-4'：不推斷）。

**Task 1.8 — 異質列顯式拒收（A-5'）**
- 內容：若 CSV 各列在 `direction`／`scenario`／`label_definition` 上不一致而
  `batch_defaults` 未涵蓋 ⇒ `heterogeneous_rows_in_batch`，訊息列出前 3 個衝突列號與欄名。
- 驗證：fixture 混 long/short ⇒ 得該 reason 且**落檔數 `== 0`**。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：只拒收並指出衝突；不自動分批。
- 不可做：不得靜默取第一列之值套用全批。

**Task 1.9 — 答案窗宣告與 purge 下界（D-7；本批最高優先）**
- 內容：CSV 上傳時，答案窗**預設取檔內最大可用 horizon**（有 `future_1..12` ⇒ 預設 12）；
  可往下調但須勾選「我的篩選條件未用到超過第 N 根」之聲明，UI 明示**此為無法驗證的聲明**；
  欄位接受**任意正整數**（不限 1..12）。宣告值寫入 `label_definition.window.horizon_bars`，
  由既有 `event_split.py` 之 `embargo = window.max()` 自動決定 purge 寬度。
- 驗證：`pytest tests/api -q -k gap3_horizon_declaration` ≥4 條——
  ①CSV 含 future_1..12 ⇒ 預設值 `== 12`
  ②未勾聲明而調低 ⇒ fail-closed（落檔數 `== 0`）
  ③宣告 `== 4` ⇒ `split_events` 之 embargo `== 4 根之毫秒數`
  ④宣告 20（>12）⇒ 接受（不限 1..12）。
  **mutation**：把預設值改回 1 ⇒ ①須紅。
- 存活至：Phase 6。
- 覆蓋風險：無。
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
- 覆蓋風險：無。
- 邊界：只篩**數值**欄；字串欄不在本 Task。
- 不可做：不得在篩選中改動任何原始欄位值。

**Task 2.1b — 由篩選條件自動導出答案窗下界（D-7 第 2 層）**
- 內容：系統內篩選時，掃描條件引用之 `future_{N}bar_return` 欄，取 `max(N)` 為答案窗**下界並鎖定**，
  使用者**不得調低**（與 CSV 路徑之「可調低但需聲明」不同——此處是機器可證，不需聲明）。
- 驗證：條件用到 `future_2` 與 `future_7` ⇒ 答案窗鎖定 `>= 7`；
  嘗試設 5 ⇒ 前端阻擋且 `fetch` call count `== 0`。
  **mutation**：把 `max()` 改成 `min()` ⇒ 該測試須紅。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：只導出下界；使用者可往上調（保守方向永遠允許）。
- 不可做：不得允許調低於導出值（那等於明知條件用到第 7 根卻只隔 5 根）。

**Task 2.2 — 篩選條件寫入 label_definition.filters**
- 內容：把篩選條件寫進契約已登記之 `label_definition.filters`（Task 1.1 已加）。
- 驗證：匯出檔 `label_definition.filters` 與送出條件深度相等（`==`）；
  且 `filters` 鍵存在於契約 `label_definition.fields`（防漂移斷言）。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：只記錄條件，不改變 `label` 值本身。
- 不可做：不得把篩選條件納入 `event_id` 之輸入（會使同事件跨批 id 不同，違反 D-2）。

**Task 2.3 — 即時筆數顯示**
- 內容：顯示「將匯出 N 筆（原 M 筆）／你聲明的正例 X／反例 Y」。
- 驗證：vitest 斷言 `N + 被濾掉數 == M` 且 `X + Y == N`。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：純顯示。
- 不可做：不得以估算值顯示。

### Phase 3 — 事件批次刪除（依賴：無）　【#4】

**Task 3.1 — DELETE /api/v1/case/events/{import_id}**
- 內容：刪除該批事件與其 artifact。
- 驗證：`pytest tests/api -q -k gap3_event_delete` ≥4 條；刪後 `GET` status_code `== 404`。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：只刪該批；不連帶刪 kline 快取或 Feature Library。
- 不可做：不得提供「刪除全部」端點。

**Task 3.2 — 前端刪除鈕與二次確認**
- 內容：確認框顯示該批筆數與匯入時間。
- 驗證：vitest 斷言未確認時 `fetch` call count `== 0`。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：只在批列表提供。
- 不可做：不得以 `window.confirm` 帶過。

**Task 3.3 — 已被引用批次之警語**
- 內容：仍可刪，確認框明示「引用它的分析結果將無法重現」。
- 驗證：vitest 斷言該字串出現於確認框（`toContain` 斷言）。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：只加警語。
- 不可做：不得靜默刪除被引用批次。

### Phase 4 — 答案窗（依賴：無；**修正 R1 之錯誤相依聲明**）　【#1】

> GROK-R1-P1-05 指出原版標「依賴 Phase 1、覆蓋 Phase 1 單 horizon 邏輯」是**錯的**：
> Phase 1 是 CSV **匯入**對映，不含答案窗／`future_*`／`label_value` 產生；
> 現行單 horizon 邏輯在 `eventExport.ts` 與 `/search`（B5 已落地）。已改正。

**Task 4.1 — 匯出檔可多帶 future_* 欄（D-3 之 (a)）**
- 內容：新增「附帶報酬欄」多選（預設全選 1..12），匯出檔為每個選中 h 帶
  `future_{h}bar_return`；**`label_value` 與 `label_definition.window.horizon_bars`
  仍取自另一個單選之「主答案窗」，語意不變**。
- 驗證：主答案窗 `=4`、附帶選 `[1,3,7]` ⇒ 匯出檔含 `future_{1,3,7}bar_return` 三欄
  且 `label_definition.window.horizon_bars == 4`、`label_value ==` 各列之 `future_4bar_return`。
- 存活至：Phase 6。
- 覆蓋風險：**不覆蓋**任何既有邏輯（純疊加欄位）；契約不變。
- 邊界：h ∈ 1..12；附帶欄只是攜帶，不參與 label 判定。
- 不可做：不得讓多選改變 `label_value` 之來源（那是 (b)/(c) 方案，本批不做）。

**Task 4.2 — 事件後報酬表顯示完整曲線**
- 內容：`analyze_tables` 之 `horizons` 由呼叫端傳入（現碼預設 `(1,2,4)`，`pipeline.py:98`），
  前端可選要看的 horizon 集合。
- 驗證：`pytest tests/momentum/event_samples/ -q -k horizon_curve` ≥3 條；列數 `== len(horizons)`；
  **且 G-2 事件 golden 須同步更新並在 commit message 說明**（D-4：這是**合法的數值輸出變更**，
  不得靜默重凍）。
- 存活至：Phase 6。
- 覆蓋風險：改變 `analyze_tables` 預設值之呼叫形態（**刻意**，已由 G-2 守）。
- 邊界：只改要算哪些 horizon；**不改**每個 horizon 之計算式。
- 不可做：不得因列數變多而改變 `n_eff` 之定義。

**Task 4.3 — 缺欄確認框逐 horizon 列出**
- 內容：訊息改為逐 horizon 列缺幾筆（主答案窗與附帶欄分開列）。
- 驗證：vitest 斷言訊息含每個缺欄 horizon 之筆數數字。
- 存活至：Phase 6。
- 覆蓋風險：覆蓋現行單一 horizon 之訊息字串（**刻意**）。
- 邊界：只改訊息，不改「缺欄不寫值」之既有行為。
- 不可做：不得因缺欄而阻擋匯出。

### Phase 5 — 錯誤訊息與表頭說明（依賴：Task 5.0）　【#2 ＋ #3 ＋ #6】

**Task 5.0 — 建立指標詞彙 SoT（GROK-R1-P1-04）**
- 內容：R1 查證 `event_import_contract.json` 之頂層 `_doc` 是**整份契約的敘事字串**，
  **不含** `macro mean`／`n_eff`／`lift_threshold`／`prevalence_full` 等表頭鍵
  ⇒ 原 Task 5.2 之「取自契約 `_doc`」不可執行。
  新建 `momentum/Analysis/contracts/event_metrics_glossary.json`：每個指標鍵對應
  `{term, definition, formula_ref}`，作為前後端**唯一**文案來源。
- 驗證：`python3 -c "import json;g=json.load(open('momentum/Analysis/contracts/event_metrics_glossary.json'));assert set(g)>= {'macro_mean','micro_mean','n_eff','lift_threshold','prevalence_full','prevalence_learn','signal_frequency','tail_excluded'}"` rc=0。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：只放文案與公式指標，不放數值。
- 不可做：不得把定義同時寫在前端（Task 5.2 以 `==` 斷言防漂移）。

**Task 5.1 — .source.json 誤傳之訊息追加正解**
- 內容：判別依據＝內容為 `canonicalSourceText` 形狀
  （symbol/timeframe/timestamp/positive_case/price_change）；
  訊息追加「此為來源對證檔，請改放在 `source_file` 欄並勾選 `verify_source_digest`」。
- 驗證：`pytest tests/api -q -k source_json_hint`；status_code `== 400` 且訊息含 `source_file`。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：只追加提示；`legacy_schema_detected` 之 reason 字面**不變**。
- 不可做：不得因判別為 source.json 就自動改走 `source_file` 流程（靜默轉換＝契約禁止）。

**Task 5.2 — 事件型兩表 tooltip（讀 Task 5.0 之 SoT）**
- 內容：兩表所有表頭加 tooltip，文案取自 `event_metrics_glossary.json`。
- 驗證：vitest 斷言每個表頭之 tooltip 文字 `==` glossary 對應 `definition` 值。
- 存活至：Phase 6。
- 覆蓋風險：無。
- 邊界：只加 tooltip，不改數值與版面。
- 不可做：不得在前端另寫一份定義。

**Task 5.3 — #2 缺答案窗欄之確認框（GROK-R1-P2-01 指出 #2 原版未交代）**
- 內容：使用者 #2 問「要自己找案例時間點測嗎」——現行確認框只在缺 `future_{h}bar_return`
  時跳。改為：匯出前**主動顯示**「主答案窗 h：N/M 筆可算、K 筆因資料尾端不足而缺」，
  使用者不必自己去湊時間點才知道。
- 驗證：fixture 尾端 3 筆不足 ⇒ 訊息含 `3`（數字精確比對）。
- 存活至：Phase 6。
- 覆蓋風險：與 Task 4.3 同一訊息區塊，兩者須合併實作（Task 4.3 先）。
- 邊界：只改顯示時機與內容。
- 不可做：不得阻擋匯出。

### Phase 6 — IC 分析止血閘（依賴：Task 6.0）　【#9a】

**Task 6.0 — IC 錯誤 reason 之登記處（D-6）**
- 內容：`feature_count_exceeds_cap` 不屬 `event_import_contract`（那是匯入契約）。
  新建或沿用 IC 側之錯誤 reason 契約檔，登記該值；程式與前端由該檔取字面。
- 驗證：`python3 -c "..."` 斷言該 reason 存在於登記檔；`grep -c 'feature_count_exceeds_cap' api/ frontend/src/ --include=*.py --include=*.ts -r` 之硬編碼數 `== 0`。
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
- 覆蓋風險：無。
- 邊界：只加欄位與狀態區分。
- 不可做：不得以固定假進度值填充（UAT 已證實 `progress==0.12` 卡 15 分鐘之誤導性）。

**Task 6.4 — 止血閘之存活驗證（D-5）**
- 內容：以 218369 特徵之 run 呼叫 analyze 後，**在 cap 檢查之後、回應之前與之後各採樣一次**
  footprint，證明「未載入大矩陣」。
- 驗證：V-8 之三項斷言（見 §V）。
- 存活至：GAP-6。
- 覆蓋風險：無。
- 邊界：只驗記憶體與存活。
- 不可做：不得在 cap 檢查**之前**採樣就宣稱通過（R1 明列此假綠形態）。

---

## §V 驗證策略與邊界測試目錄

| ID | 驗什麼 | 手段 | 通過條件 |
|---|---|---|---|
| V-1 | CSV 對映之 label **照抄正確** | 真實 CSV fixture → 匯入 → 逐列比對 | 每列 `label ==` CSV 指定欄之值。**誠實邊界：本項不證明使用者選對欄**（D-1，語意不可機械證明）；選欄風險由 V-1b/V-1c 降低 |
| V-1b | 可疑欄警示有鑑別力 | fixture 含 3 個二元欄 | 警示列出另外 2 個（`len == 2` 且集合相等） |
| V-1c | provenance 可追 | 匯入後讀 receipt | `column_mapping.label ==` 送出值；`source_file_digest` 存在且 `!=` 空 |
| V-2 | 對映缺失／欄不存在／label 非二元／異質列 各自 fail-closed | 四個反例各一測 | 各得對應 reason；**落檔數 `== 0` 且 task store 筆數不變**（CODEX-R1-P1-04：不只驗落檔，須驗無其他狀態副作用） |
| V-3 | CSV 與 JSON 路徑**共用同一函式** | **兩重 oracle**（R1 三家指出單靠 sha256 相等不成立） | ①靜態：AST 斷言 CSV route 呼叫 `/import-events` 之同名驗證函式 ②行為：mutation——把該共用函式改壞，**兩條路徑之測試須同時轉紅**（只有一條紅 ⇒ 存在平行實作） |
| V-4 | `event_id` 跨路徑一致（D-2） | 同批事件之 JSON 匯出 vs CSV 回灌 | `event_id` 集合 `==`（集合相等，非逐列順序） |
| V-5 | 刪除後該批消失 | 刪除 → 列表／analyze 各查一次 | 列表無該批；analyze status_code `== 404` |
| V-6 | 附帶 horizon 欄與 label 語意分離（D-3） | 主答案窗 `=4`、附帶 `[1,3,7]` → 匯出 | 含 `future_{1,3,7}bar_return`；`window.horizon_bars == 4`；`label_value ==` 各列 `future_4bar_return` |
| V-7 | `.source.json` 誤傳之訊息含正解 | 上傳 `.source.json` 當事件檔 | status_code `== 400` 且訊息含 `source_file` |
| V-8 | 止血閘生效且**未載入大矩陣**（D-5） | 218369 特徵之 run 呼叫 analyze，依 Task 6.4 之採樣點 | ①status_code `== 400` ②**任務未建立**（task store 筆數不變）③cap 檢查後之 footprint 相對 baseline 增幅 `< 0.2GB`，量測用 `sample <pid>` 之 Physical footprint（**禁 `ps rss`**）④進程存活 |
| V-9 | 止血閘不誤擋 | 小 run（15 特徵）呼叫 | status_code `== 200` **且任務確實被建立**（task store 筆數 +1；R1 指出只驗 200 不足） |
| V-10 | tooltip 與 glossary 不漂移 | 逐表頭比對 | tooltip 文字 `==` glossary `definition` |
| G-1 | IC 主線未被波及 | `python3 scripts/gap3_freeze_golden.py --check` | 通過。**誠實邊界：不涵蓋事件路徑**（D-4） |
| G-2 | 事件路徑數值未意外改變 | 本批新建之事件 golden | 逐 horizon exact return（`atol=0`）／NaN mask／PIT anchor 全等；Task 4.2 之合法變更須同 commit 更新並說明 |
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
Phase 4 為純疊加（D-3 之 (a)），回退不影響既有 label 語意。
Phase 6 為純新增之前置檢查，回退即恢復「可按但會吃垮機器」的現況（不建議）。

---

## §N N/A 登記

| 段 | 理由 |
|---|---|
| 使用者問題 #7 | 回答性非施工項：B8/B8b 來自 `POST /case/events/{id}/analyze` 當下計算、價格讀 `data_cache/kline_cache.h5`（`pipeline.py:78-82`），**不經 Feature Library**（已答） |
| 使用者問題 #8／#10 | **具名殘留**（CODEX-R1-P1-07 指出原版「已回答」過寬）。已答部分＝事件型兩表不需 Feature Library、IC 分析才需要。**未答部分＝「事件標的/日期只需被 Feature Library 涵蓋即可」未實測**。三值理由＝`blocked-by`：IC 分析在止血閘後對大 run 不可用，需 GAP-6 之分塊計算就緒才能實測。**觸發條件**：GAP-6 Task「分塊計算」驗收通過當日。**owner**：主委。**登記處**：本 §N ＋ `docs/IC_QUANT_GAP_REGISTRY.md`（Task 6.0 一併登記） |
| #9b 規模防護本體 | 排入 GAP-6（registry #6「430K 規模防護」），使用者 2026-08-22 裁定 |
| **純事件研究模式（新模組）** | **具名殘留，另立模組**。使用者 2026-08-22 提出第三種用途：「單純想知道某事件（大漲 10% 後／從高點跌 15% 後）之後 1/5/10/30/60 天或任意天的漲跌數值」。此為 **event study**，與分類、條件 IC 皆不同：**不需 label、不需答案窗、不需 purge**（無訓練即無洩漏）。已查證只需 kline（`pipeline.py:78-82` 之 `bars_from_kline_cache`），**與 IC-Analysis 無關**。<br>現況缺口：契約 `required_fields` 含 `label`／`label_definition`／`control_kind`／`scenario`，且 `scenario` enum 僅 `A/B/C/two_stage`（皆為預測／確認型），**無「純描述」值** ⇒ 使用者為了看報酬分布被迫先編一個假 label。<br>三值理由＝`user-ruling`：使用者 2026-08-22 逐字「這可以未來另做一個模組研究就好」。**排程**：另立模組票，不在本批。<br>**定位**：這是**另一種用途**（想知道某類事件的後續行為分布時使用），**不是分類流程的前置條件**。<br>🔴 **主委原判斷已撤回（使用者 2026-08-22 糾正，糾正成立）**：原寫「研究順序應為事件研究 → 分類，使用者現況是直接跳到分類」。**該判斷錯誤**——它假設「標籤 ＝ 某單一根的報酬」，那種情況才需要先知道訊號在第幾根衰減。使用者的標籤是**複合形狀定義**（例「t0 +5% 且 future_1≥+2% 且 future_2≥+2% 且 future_4≥+1%」＝「漲上去且撐得住」），那是交易意圖之直接指定，**本就不需前置研究**；用「全體事件的平均衰減曲線」去推導「我要抓哪種形狀」方向亦不對。<br>**真正成立的機械約束只有 D-7**（答案窗須 ≥ 標籤最遠觸及之根數），該約束由使用者的定義**直接推導**，與研究順序無關。<br>衰減研究之**可選**用途：回頭優化既有定義（如「卡在第 4 根是否提早收手」「future_4 ≥ +1% 門檻是否過鬆」），屬事後精修而非動手前的必要功課。 |
| **觸發條件需回看歷史（如「從高點跌 15%」）** | **待盤點**。使用者 2026-08-22 提出之事件形態需回看歷史高點；現行案例搜尋是否支援此類回看型觸發條件**尚未查證**。三值理由＝`needs-research`。**owner**：主委。**觸發**：純事件研究模組開票時一併盤點。 |
