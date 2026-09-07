# 事件模式之對齊守衛與期間對齊 — SPEC

**票**：`EVTALIGN`　**起草**：Claude　**日期**：2026-09-07
**上游**：UAT 實機（2026-09-07）。使用者為了拿回 OOS 保證改用 ETHUSDT 1h 的 feature run，
分析在 stage2 被 `AlignmentViolationError` 擋死。

**使用者原話（逐字，不得改寫）**：
> 「2.為什麼是往後看5根的報酬，那IC設定那些h是假的?」
> 「3.什麼是K 線資料比特徵多出結尾 503 根是什麼意思，K線比特徵多也很合理吧」
> 「4.選了一個時間區間的事件或是什麼，然後還要手動重新生成特徵，手動K線對齊，這太蠢了，是缺陷吧」
> 「1.可以跑的話，幹嘛檔? 但我只是不知確切的狀態進行式是什麼」

---

## §RISK 風險分級

- RISK-HIT: a,d
  - (a) 數值/資料品質：本票要動的是**防未來函數（look-ahead）之結構守衛**。改錯＝洩漏無人擋。
  - (d) ML/回測正確性：同上；且涉及 `effective_horizon`／`purge_gap`（切分隔離區）之語意。

🔴 **本票不得由實作者自審**；守衛之任何放寬須有三家 adversarial 明確簽字。

---

## §A 假設與待使用者確認

- **實跑事實（附 receipt）**
  - `FACT-RECEIPT`：`venv/bin/python handoffs/20260907-probe-event-scaffold-label.py` → rc=0。
    同一批事件、只改全域 horizon（3 vs 5），事件模式下**最終 label 逐值相同**
    ⇒ 使用者設的 `h` **不是假的**；stage2 用全域 horizon 造的 label 是**鷹架**，
    在 `_apply_event_filter` 被 `event_label_values` **整條換掉**
    （`label_source` 標為 `event_label_value`）。（Claude 實跑 2026-09-07）
  - `FACT-RECEIPT`：實機失敗訊息
    `AlignmentViolationError: target trailing NaN count must equal lag: expected 5, got 0`
    （`momentum/core/contracts.py:960`，`tail_nans != spec.lag` 之硬相等）。
  - `FACT-RECEIPT`：期間差額**逐根對得上**——feature run `c32097ad` 之
    `time_range = {start: 1707350400, end: 1775520000}`、`row_count = 18937`；
    orchestrator 實讀 kline 20,352 根。
    起頭多 `(1707350400-1704067200)/3600 = 912` 根、結尾多 `(1777330800-1775520000)/3600 = 503` 根，
    `912 + 503 = 1415 = 20352 - 18937`。（Claude 實跑 2026-09-07）
  - `FACT-RECEIPT`：`_resolve_effective_label_horizon(config, None)` 在 `labels_df is None` 時
    回 `config.global_settings.default_horizon`（`config/ic_config.yaml` 之 **5**），
    **完全不讀事件之 `event_label_spec.horizon_bars`**。（Claude 讀碼 2026-09-07）
  - `FACT-RECEIPT`：實機 preprocessing 22:05:52→22:11:51（**11 分鐘**），
    後端常駐 **17 GB**／實體 8 GB、swap 用 15.6 GB、瞬時 CPU 3.3%
    ⇒ 該階段靠 swap 撐過，非正常狀態。（Claude 實測 2026-09-07）

- **假設（未驗，請 adversarial 攻）**
  - `ASSUME-1`：把守衛之期望值改為「依剩餘 K 線根數推導」後，**同尾情形下強度完全不變**。
    否證觀測＝存在一組同尾資料，改法後 tail_nans 檢查放過了原本會擋的洩漏。
  - `ASSUME-2`：`effective_horizon`／`purge_gap` 之語意**不因本票改動**。
    否證觀測＝改後某條路徑之 purge 列數與改前不同。
    🔴 探針已明文標「本支沒有測那條路徑」——這是本票最需要被攻的地方。

- **待使用者確認**：無（技術決策依 CLAUDE.md 走委員會）。

---

## §C 約束

1. **不得放寬 look-ahead 保護**。任何改動須證明「同尾情形下判定逐格不變」。
2. **不得刪掉全域 horizon**：它仍決定 `effective_horizon`／`purge_gap`（探針之誠實邊界）。
3. **不得把系統的責任推給使用者**（使用者原話④）：期間對齊必須由系統處理，
   不得要求使用者手動重生特徵或手動裁切 K 線。
4. 🔴 **不得以「動手前擋下」取代「進度可見」**（使用者原話①：「可以跑的話，幹嘛擋?」）。
   記憶體議題之交付物是**看得到進度與預估**，不是新增阻擋閘。
5. 不得改變任何既有 IC 數值：本票是守衛與可視性，不碰計算。
6. 🔴 **修法一律 mode-agnostic**（使用者 2026-09-07 追加，逐字）：
   > 「除了事件模式，其他模式像是Global和其他也不能被這種鷹架等假架構檔或計算錯誤，
   > 這系統上線的話會是極重大瑕疵影響專案名譽」

   ⇒ 本票之原則是**「驗證與呈現的對象，必須是實際被使用的那份資料」**。
   這條原則**對三種模式一律成立**，不是事件模式的特例。
   Task 1.1 之守衛推導、Task 2.1 之「不驗被丟棄的中間值」，
   **兩者都必須對 global／cross_sectional／event 一致成立**，並各自有測試。

   🔴 **本條禁的是什麼、不禁什麼（精確界定；初稿寫得太寬，會誤導實作端）**

   初稿寫「任何 `if mode == "event"` 形式的修法一律視為錯誤修法」——**那句話是錯的**，
   照字面讀會變成「看到模式分支就刪掉」，而事件模式**本來就該**有自己的分支
   （它算的是**條件 IC**、用的是**事件 label**，那是真實且必要的行為差異；
   刪掉它系統會壞）。使用者當場指出這點，本節據以改寫。

   **✅ 合法的模式分支（不得因本條被移除）**
   - 事件模式用 `event_label_values` 取代主線 label（`label_source="event_label_value"`）
   - 事件模式標 `statistic_kind="conditional_ic"`、`sample_scope_kind="event"`
   - 橫截面走 `mode == "cross_sectional"` 的另一條分析路徑
   —— 這些是**做什麼**的差異，各模式本來就不同。

   **❌ 本條禁止的**：拿模式分支去**繞過**這條原則，例如
   - `if mode == "event": skip validate_alignment(...)`（跳過驗證）
   - `if mode == "event": <只有事件模式驗對的那條，其餘照舊驗鷹架>`（只治一種）
   —— 「**驗證的對象要是被使用的那個**」是**跨模式共通的正確性要求**，
   不是各模式可以各自決定的行為。用分支把它變成單一模式的特例，
   等於把病灶留在另外兩種模式裡。

   **判準（給實作端與 review 用，可機械對照）**：
   模式分支決定「**用哪份資料／算什麼統計量**」＝合法；
   模式分支決定「**要不要驗、驗哪一份**」＝違反本條。

---

## §G Golden / Baseline

- **Baseline-1**：`scripts/gap3_label_golden.py --check` 之 46＋2 案例逐位元組不變。
- **Baseline-2（守衛強度）**：以**同尾**資料構造之既有 `validate_alignment` 測試全部維持通過，
  且「真的洩漏」之反例仍被擋（改前改後各跑一次，逐格對照）。
- **Golden-3（新增）**：凍結「特徵期間短於 K 線」之對齊案例，鎖 tail_nans 期望值之推導結果，
  以檔案 `sha256` 逐位元組對證（禁只比欄名）。
- 🔴 **數值判準**：涉及 IC 值之比對一律 `atol=0`（本票不碰計算 ⇒ 必須**逐位元組相同**，
  不是「近似相同」）；`np.testing.assert_allclose(..., atol=0, rtol=0)` 或直接 `==`。
  守衛之 tail_nan 期望值為整數 ⇒ 一律 `==`，不得用容差。

---

## §P Phase 與依賴

| Phase | 內容 | 依賴 |
|---|---|---|
| **P1** | 守衛期望值改為依剩餘 K 線推導；同尾強度不變之證明 | 無 |
| **P2** | 事件模式不驗即將被丟棄的鷹架（驗真正被用的 label） | P1 |
| **P3** | 期間自動對齊（系統處理，不要使用者手動） | P1 |
| **P4** | 進度可見（stage 內細分＋預估），取代「動手前擋下」 | 無 |

---

## 逐項 Task 明細

### Task 1.1 — 對齊守衛之期望值依剩餘 K 線推導（`票 UAT-3`）

- **目標**：`K 線比特徵多`（常態）不再被誤判為違規。
- **修法**：`expected_tail_nan = max(0, lag - bars_available_after_last_target_row)`。
  同尾 ⇒ `bars_available = 0` ⇒ `expected = lag`（**與現行完全相同**）。
- **驗證（可證偽）** — `tests/momentum/test_alignment_tail_nan.py`：
  - `ASSERT venv/bin/python -m pytest tests/momentum/test_alignment_tail_nan.py -q THEN rc=0`
  - **同尾**：期望值仍為 `lag`；把 target 改成未 shift（洩漏）⇒ 仍 raise。
  - **截短**：剩餘 503 根 ⇒ 期望 0，通過；若剩餘 2 根而 lag=5 ⇒ 期望 3。
  - mutation `A1`：把推導改回硬相等 ⇒ 截短案例紅；`A2`：改成永遠回 0 ⇒ 同尾洩漏案例紅。
- **邊界**：①剩餘根數 > lag ⇒ 期望 0；②剩餘根數為 0（同尾）⇒ 期望 lag；
  ③target index 不是 close index 之子集 ⇒ **fail-closed raise**（不猜）。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得移除 tail_nan 檢查本身；不得以「事件模式就跳過」了事（那會讓全域模式失去保護）。

### Task 2.1 — **任何模式**都只驗實際被使用的 label（`票 UAT-2`）

- **目標**：不再讓一個**不影響輸出數字**的中間值擋死分析（探針 rc=0 已證），
  且此原則**不限事件模式**（§C-6）。
- 🔴 **範圍（使用者追加後放大）**：本 Task 不是「事件模式特例」。要建立的是一條
  **跨模式不變式**：`validate_alignment` 的輸入必須是**下游真正消費的那條 series**。
  現況是事件模式先造一條全域 horizon 的鷹架、驗它、然後整條丟掉換成事件 label——
  驗了一個沒人用的東西，還讓它有權否決整個分析。
  **同樣的形態若存在於 global／cross_sectional，一併修**（見 Task 2.2 之盤點）。
- **修法**：`validate_alignment` 對**最終**label 執行；若某模式必須先造中間序列，
  該序列**不得**成為否決依據。
  🔴 **不得直接跳過驗證**——每種模式各自的 label 都需要對齊保證，只是驗對的那條。
  🔴 **不得用模式分支把本 Task 縮成單一模式的特例**（§C-6 之判準）：
  「要不要驗、驗哪一份」不得因模式而異；「用哪份資料、算什麼統計量」則本來就該不同。
  事件模式既有的 `event_label_values` 覆寫、`conditional_ic` 標記等分支**照留**。
- **驗證（可證偽）** — `tests/api/test_event_label_alignment.py`：
  - `ASSERT venv/bin/python -m pytest tests/api/test_event_label_alignment.py -q THEN rc=0`
  - 事件 label 與 feature index 不對齊 ⇒ 仍 raise（保護沒被拿掉）。
  - 鷹架之 tail_nan 不再影響事件模式之通過與否。
- **邊界**：①`event_label_values` 缺任一 timestamp ⇒ 維持現行 loud raise；
  ②非事件模式 ⇒ 行為逐位元組不變。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得因此改動 `effective_horizon`／`purge_gap`（§C-2）。

### Task 2.2 — 盤點**所有模式**是否存在「驗了就丟」的中間值（`票 UAT-2`）

- **目標**：把使用者指出的風險（「其他模式也不能被這種鷹架…影響專案名譽」）變成**可機械檢出**。
- **修法**：
  1. 逐模式（global／cross_sectional／event）追出 `validate_alignment` 的實際輸入，
     與**下游 IC 計算實際消費**的 series，逐一比對是否為同一物件。
  2. 建立**跨模式不變式測試**：對每個模式，斷言「被驗的 series」與「被用的 series」
     為同一份（`is` 或逐值 `==` ＋ 來源標記）。
  3. 盤點結果**逐模式**寫進 SPEC §N（有／無／不適用），不得只寫「已檢查」。
- **驗證（可證偽）** — `tests/momentum/test_validated_series_is_used_series.py`：
  - `ASSERT venv/bin/python -m pytest tests/momentum/test_validated_series_is_used_series.py -q THEN rc=0`
  - 逐模式參數化；把任一模式改成「驗 A 用 B」⇒ 該模式之案例必須紅。
  - mutation `A3`：在 global 模式插入一條被丟棄的中間驗證 ⇒ 測試紅。
- **邊界**：①某模式確實沒有中間序列 ⇒ 測試標 `not_applicable` 並**說明理由**，不得靜默跳過；
  ②新增模式時測試須自動涵蓋（以模式清單參數化，不寫死三個）。
- **存活至**：永久（這是防止同型缺陷再生的閘）。
- **覆蓋風險**：無。
- **不可做**：不得只修事件模式就宣稱本 Task 完成。

### Task 3.1 — 期間自動對齊（`票 UAT-4`）

- **目標**：使用者選了事件批與 feature run 之後，**系統自己**處理期間不一致。
- **修法**：以 `feature run 期間 ∩ kline 期間 ∩ 事件期間` 為分析區間，並在報告中**揭露**
  實際採用的區間與被裁掉的部分（禁靜默裁切）。
- **驗證（可證偽）** — `tests/api/test_period_auto_align.py`：
  - `ASSERT venv/bin/python -m pytest tests/api/test_period_auto_align.py -q THEN rc=0`
  - 三者期間不一致 ⇒ 分析成功且 metadata 明列採用區間與裁掉的根數。
  - 交集為空 ⇒ **fail-closed** 明講（不是回空結果）。
- **邊界**：①事件全部落在特徵期間外 ⇒ loud；②交集小於最小列數 ⇒ 沿用既有 fallback 語意。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得靜默裁切；不得要求使用者手動重生特徵。

### Task 4.1 — 進度可見（`票 UAT-1`）

- **目標**：使用者原話「我只是不知確切的狀態進行式是什麼」。
- **修法**：preprocessing 等長階段回報**階段內進度**（已處理特徵數／總數）與預估剩餘時間。
- **驗證（可證偽）** — `tests/api/test_stage_progress.py`：
  - `ASSERT venv/bin/python -m pytest tests/api/test_stage_progress.py -q THEN rc=0`
  - 長階段須至少回報 N 次中間進度（不是 0.12 卡住 11 分鐘）。
- **邊界**：①無法預估時**不顯示假的 ETA**（顯示「預估中」）；②回報頻率不得進 hot loop。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：🔴 **不得新增任何阻擋閘**（§C-4：使用者明講「可以跑的話，幹嘛擋?」）。

---

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 含 a,d ⇒ **必附 mutation**（`handoffs/20260907-evtalign-mutate.py`）。
- **測試層級**：單元（守衛推導）、整合（事件模式端到端）、Golden 對照、邊界。
- **邊界目錄**：
  - [x] 同尾／截短兩種期間關係 → Task 1.1
  - [x] 事件 label 未對齊 → Task 2.1
  - [x] 期間交集為空 → Task 3.1
  - [ ] 全 NaN / Inf → N/A：本票不算數值
  - [ ] 並發寫 → N/A：本票不寫檔

---

## §R 回退

- 各 Task 皆為獨立 commit，`git revert` 即可；無資料遷移。
- 守衛改動若被證明放寬了保護 ⇒ 立即 revert Task 1.1，其餘不受影響。

---

## §N N/A 登記

- **§A 待使用者確認＝無**：技術決策依 CLAUDE.md 走委員會。
- **§V 之兩項邊界標 N/A**，理由已逐條寫在 §V 內。

### 具名殘留

| 代號 | 內容 | 三值理由 | 接下來 |
|---|---|---|---|
| `EA-RESID-1` | preprocessing 之峰值記憶體（實機 17 GB／8 GB 實體、swap 15.6 GB） | `needs-research` | 需量出「特徵數 × 列數」之記憶體曲線；本票只做**可視性**（§C-4：使用者明講不要擋），真正的分塊處理另開票 |
