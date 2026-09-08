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

- **R1 裁決（三家 adversarial 之結果，非本人推論）**
  - 🔴 `ASSUME-1`：**已推翻**（`CODEX-R1-P0-01`／`GROK-R1-P0-01`）。
    我原提的 `max(0, lag − 剩餘根數)` **會放行真正的 look-ahead**——
    截短時期望值為 0，而**未 shift 的 target 也是 0** ⇒ 通過。
    tail-NaN 只證「尾端容量」，不證「每個 label 真的是 `t+lag`」。
    ⇒ Task 1.1 整條重寫為三層設計（L0 分派／L1 結構／L2 oracle）。
  - 🔴 **新發現（我沒想到的）**：`excess`／`risk_adjusted` 不在 `ORACLE_RETURN_KINDS`，
    stage2 傳 `close=None` ⇒ 若同時放寬 L1，該組合成為
    「無 L1 辨識 ∪ 無 L2 oracle」＝**零保護**（`COMPOSER-R1-P0-03`／`GROK-R1-P1-01`）。
  - 🔴 **新發現**：若對事件 label 套 forward-return 契約，**同尾**之合法密集 label
    （`tail_nans=0`）會被誤判 ⇒ 用新紅燈換掉舊鷹架（`GROK-R1-P0-02`）。

- **consult 裁決（2026-09-08，三家一致，非數人頭）**
  - 🔴 路線＝**B＋D**。A（重寫守衛）之終點就是 B＋D 但改動面更大（codex 必答 4）；
    C（擋 run 選單）違使用者目標③④。三層設計刪除，守衛**一字不改**。
  - B 之兩條 assumed 已實跑成立：`handoffs/20260908-probe-option-b-trim.py` rc=0
    （裁切把截短化約為同尾：label 逐位元組相同、tail_nan=lag、切分不吃 close）；
    codex 另以真實 `create_label_generator()` 對照 rc=0。
  - 三家共同要求：同尾化涵蓋 **stage0（`:2790`）與 stage2（`:2923`）兩呼叫點**、單一 helper。

- **仍未驗（R3 前須補）**
  - `ASSUME-2`：`effective_horizon`／`purge_gap` 之語意**不因本票改動**。
    否證觀測＝改後某條路徑之 purge 列數與改前不同。
    🔴 探針明文標「沒有測那條路徑」；`CODEX-R1-P1-03` 亦判「無法接受『不受影響』」。
    ⇒ Task 1.1／2.1 之驗收已增「改前／改後逐項對照」，但**尚未實跑**。

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

7. 🔴 **推導，不要相信（R2 之核心裁決）**

   R2 三家開出 **6 個 P0**（R1 為 3 個），六條同一個形狀：
   **我把守衛所需的每個判準都做成「呼叫端傳進來」，
   於是整套保護建立在「呼叫端誠實」之上——而那不是安全性質。**

   | 我做成參數的 | 偽造方式 | 後果 |
   |---|---|---|
   | `label_kind` | 標成 `event_given` | **整段跳過 L1／L2** ⇒ 零保護 |
   | `bars_available_after_last_target_row` | 傳 0 | **L2 不啟動** |
   | `close` | 傳污染版 | L2 對它**自洽 PASS** |

   ⇒ **本票之設計規則**（實作與 review 逐條對照）：
   - **能從既有參數推導的，不准當參數傳。**
     例：剩餘根數＝`close.index` 與 `target.index` 之差 ⇒ **刪掉該參數**。
   - **不能推導的，必須綁到產生者**（producer-set，非 caller-set）。
     例：`label_kind` 由 orchestrator 已在寫的 `info["label_source"]` 導出。
   - **綁不了的，fail-closed。** 缺 `label_source` ⇒ raise，**不得預設成任一種**。
   - **外部資料要綁指紋。** `close` 必須是產生該 label 的同一份，以 fingerprint 比對。

   🔴 **誠實邊界**：指紋只把信任邊界從「呼叫端」推到「label 產生時」，
   **不證明**原始 K 線本身沒問題——那是資料品質的另一條線，本票**明文不宣稱涵蓋**
   （`EA-RESID-4`）。

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

🔴 **優先序依使用者 2026-09-07 之裁定重排**（原順序把「鷹架」排第一是錯的）：
實測 `handoffs/20260907-probe-guard-vs-scaffold.py`（rc=0）證明
**沒有鷹架的全域模式，在「特徵期間比 K 線短」時照樣被守衛擋死**
⇒ 期間守衛打到的是**已經在用的模式**，比只在事件模式的鷹架急迫。

| Phase | 內容 | 依賴 | 為何是這個順序 |
|---|---|---|---|
| **P1** | **B**：不動守衛，label 生成前把 close 裁到 feature 尾（兩呼叫點、單一 helper） | 無 | 全域模式**今天就有地雷**（探針 rc=0）；三家共識 |
| **P2** | **D**：驗實際被消費的 label，`label_source` 綁定＋三元組 | P1 | **B 之必要配套**（codex：不做 D ＝ 錯誤輸出進條件 IC） |
| **P3** | 期間自動對齊 ＋ **丟失事件之揭露** | P1 | 使用者原話④「太蠢了，是缺陷吧」 |
| **P4** | 進度可見 ＋ **記憶體 WARN（非阻擋）** | 無 | 使用者原話①「可以跑的話，幹嘛擋?」 |
| **P5** | purge／embargo 之**揭露** | P1 | 由 R1 之 C6 降級而來——不是安全項 |

---

## 逐項 Task 明細

### Task 1.1 — **不動守衛**：label 生成前把 `close` 裁到 feature 尾（`票 UAT-3`）

🔴 **本 Task 於 consult（2026-09-08）依三家共識 B＋D 整條重寫。**
R1 打穿「放寬 tail-NaN」；R2 打穿「三層＋呼叫端參數」（6 個 P0 同一形狀＝可偽造）。
codex 必答 4：「若 A 為堵洞而改成 producer binding、index 推導、close provenance、event receipt，
**它實質收斂成 B＋D 的較大改動面**」⇒ A 的終點就是 B＋D。三層設計**刪除**。

- **目標**：`K 線比特徵多`（常態）不再被誤判為違規，**守衛一字不改、強度完全不變**。
- **修法（B）**：守衛假設「target 與 close 同尾」是個**好的不變式**——與其放寬守衛遷就資料，
  在算 label **之前**把 `close` 裁到 feature 期間：
  ```python
  def _coterminalize_close(close: pd.Series, feature_index: pd.Index) -> pd.Series:
      """把 close 裁到 feature 尾，使守衛之「同尾」不變式成立。不新增任何參數。"""
      return close.loc[close.index <= feature_index[-1]]
  ```
  之後 `generate_returns(close, horizon)` 之尾端 `lag` 個 NaN 自然出現，`validate_alignment` **不改**。
- 🔴 **兩個呼叫點、單一 helper**（三家獨立命中）：
  `_stage2_label_generation`（`:2923`）**與** `_stage0_ingestion` 之預載 labels 路徑（`:2790`）
  皆對 `close` 呼叫 `validate_alignment`；只改 stage2 ⇒ 預載＋截短路徑仍紅。
  兩處**必須呼叫同一支 `_coterminalize_close`**（composer：防「一點 derive、一點仍信參數」漂移）。
  composer 誠實註記：UAT 當次 `labels_df=None`，stage0 不在 hot path——但不涵蓋就是下一個 60 天鷹架。
- **§C-7「推導，不要相信」在此的體現**：裁切依據是 `feature_index[-1]`，**從既有參數推導**，
  **不新增任何可偽造之參數** ⇒ R2 六個 P0 之形狀在本設計下**無從產生**。
- **驗證（可證偽）** — `tests/momentum/test_close_coterminalize.py`：
  - `ASSERT venv/bin/python -m pytest tests/momentum/test_close_coterminalize.py -q THEN rc=0`
  - **同尾**：裁切為 no-op，label 逐位元組不變（Baseline-2）。
  - **截短**：裁切後之 label 與「同一 feature 期間之同尾資料」算出之 label **逐值 `==`**
    （NaN 位置與數值皆同；主委探針 `20260908-probe-option-b-trim.py` rc=0，
    codex 另以真實 `create_label_generator()` 對照 rc=0）。
  - **守衛不改**：`git diff` 之 `momentum/core/contracts.py::validate_alignment` **為空**
    （測試以 `inspect.getsource` sha256 對照改前）。
  - **兩呼叫點**：以 spy 斷言 stage0 與 stage2 各恰呼叫 `_coterminalize_close` 一次。
  - **切分不受影響**：`effective_horizon`／`purge_gap`／`embargo`／`split_row_fingerprint`／
    `retained_event_ids` 與 Task 0.2（重做版）之 golden **逐值 `==`**。
  - mutation `B1`：裁切改為 no-op ⇒ 截短案例紅；`B2`：只改 stage2 不改 stage0 ⇒ 兩呼叫點測試紅；
    `B3`：動了 `validate_alignment` 任一字 ⇒ sha256 測試紅。
- **邊界**：①同尾 ⇒ no-op；②截短 ⇒ 化約為同尾；③`feature_index` 空 ⇒ fail-closed raise；
  ④`close` 尾早於 feature 尾（K 線反而比特徵短）⇒ **不裁切**，交由既有守衛照舊判定（本票不改該情形）。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：**不得改 `validate_alignment` 任何一行**；不得新增參數；不得把裁切做成 mode 分支
  （裁切在 label 生成前，與 mode 無關）。

### Task 2.1 — （D，**B 之必要配套**）驗證對象＝實際被消費的那條；契約由 `label_source` 綁定（`票 UAT-2`）

🔴 **consult 升級**：codex 必答 5：「不做 D…現行 timestamp→value 三檢查容許事件值旋轉或 event_id 錯配，
**錯誤 label 會進條件 IC。這是錯誤輸出，不只是『不乾淨』**」⇒ D 與 B 同批，不是可延後的衛生項。

🔴 **R1 修訂**：初稿寫「對最終 label 呼叫同一個 `validate_alignment`」——
`GROK-R1-P0-02` 指出那會**用新紅燈換掉舊鷹架**：事件 label 是逐事件給定值，
天生 `tail_nans=0`，套 forward-return 契約在**同尾**時會被誤判違規。

- **目標**：不再讓一個**不影響輸出數字**的中間值擋死分析（探針 rc=0 已證），
  **也不製造新的誤判**。
- **修法**：
  1. 引入 `label_kind`：`forward_return`（往後看 h 根的報酬）／
     `event_given`（逐事件給定之 label，**沒有**尾端 NaN 語意）。
  2. `validate_alignment` 依 `label_kind` **分派契約**，
     🔴 **不是**依 mode 分支（§C-6 判準：分派依「資料是什麼」，不是「誰在跑」）。
  3. `event_given` 之契約＝「每個選中 timestamp 有值／值有限／index 與 features 相符」
     ——該檢查**已存在**於 `ic_filter_orchestrator.py:3033-3041`（`missing` 清單 ＋
     `np.isfinite(vals).all()`），本 Task 是把它**提升為正式契約並移到驗證層**，不是新寫一套。
  4. 驗證的呼叫點必須在**覆寫之後**（`COMPOSER-R1-P0-02`：現況 stage2 `:2923` 與
     stage0 `:2790` 都在 stage3 覆寫 `:3042` 之前，覆寫後無再驗）。
  5. 🔴 **鷹架違規延後裁定**（R3 三家一致，2026-09-08）：覆寫前之 stage0／stage2 驗證在
     `event_label_values` 提供時**不直接 raise 而暫存**，由 stage3 依「該序列是否真被消費」裁定——
     被覆寫 ⇒ 降為診斷揭露；未被覆寫（事件不足 fallback／filter 未啟用）⇒ 原樣 raise。
     判準＝「資料是否將被替換」（§C-6 合法），非 mode 字串。細節見 TODO Task 2.1 要點 3。
- **驗證（可證偽）** — `tests/api/test_event_label_alignment.py`：
  - `ASSERT venv/bin/python -m pytest tests/api/test_event_label_alignment.py -q THEN rc=0`
  - 事件 label 與 feature index 不對齊 ⇒ **仍 raise**（保護沒被拿掉）。
  - **同尾**事件模式之合法密集 label（`tail_nans=0`）⇒ **通過**（不得誤判）。
  - 鷹架之 tail_nan 不再影響事件模式之通過與否。
  - mutation `A4`：把 `event_given` 也套 forward_return 契約 ⇒ 同尾合法案例紅。
- **邊界**：①`event_label_values` 缺任一 timestamp ⇒ 維持現行 loud raise；
  ②非事件模式 ⇒ 行為逐位元組不變。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得因此改動 `effective_horizon`／`purge_gap`（§C-2）；
  🔴 不得用模式分支把本 Task 縮成單一模式的特例（§C-6 之判準）：
  「要不要驗、驗哪一份」不得因模式而異；「用哪份資料、算什麼統計量」則本來就該不同。

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
| `EA-RESID-2` | **橫截面路徑從未呼叫 `validate_alignment`** | `blocked-by` | 依使用者 2026-08-17 之模組成熟度裁定（只 Feature Factory 完整、IC 進行中、**其餘不完整**），橫截面屬「其餘」⇒ **未完工的模組沒有守衛不是缺陷**。使用者 2026-09-07 當面更正我把它排成「比鷹架更嚴重」是錯的。**該模組實作時必須補**，不進本票 |
| `EA-RESID-6` | 四條**既有**紅測試（B1 之前即紅，`097dae40` worktree A/B 證實）：`test_ichc_p2_golden::test_feature_set_and_config_exact`（receipt 凍於 8/17、`ICConfig` schema 改於 8/27）、`test_ic_1a_cut1_golden`／`test_ic_persist_redirect_golden_ab`（reporter stub 缺 `analysis_status` kwarg，7/16 起）、`test_ichc_event_timestamps…kwarg` | `needs-research` | 屬 ICHC 票之 receipt 重凍與 stub 更新，非本票；🔴 主委 R3 前曾把該批 rc=1 誤報為通過（見 reconcile R3 E4），本票之驗收命令改列**逐檔**狀態 |
| `EA-RESID-3` | `_validate_expected_frequency` 對 **tz-aware** 索引拋 `TypeError` 而非其設計之 `TimestampDiscontinuityError` | `blocked-by` | 🔴 **執行 Task 0.2 時實測撞到**（`ic_filter_orchestrator.py:335`）：`_coerce_timestamp_array` 對 tz-aware 回 **object 陣列** ⇒ `np.diff` 得 object ⇒ `diffs <= np.timedelta64(0,"ns")` 型別不合。**現行資料為 tz-naive**（`_normalize_ic_time_index` 對 int64 epoch 秒走 `to_datetime(unit="s")`）故**未觸發**；但該函式對已是 tz-aware 之 `DatetimeIndex` **原樣保留 tz** ⇒ 一旦上游改存 tz-aware，守衛會以錯誤的例外型別炸掉。**屬潛伏脆弱點，非現行 bug**；不進本票（本票不碰時間索引正規化），待接觸該路徑之票處理 |

### 切分基線之執行 receipt（TODO `Task 0.2`；2026-09-08，實作前先跑）

`venv/bin/python handoffs/20260907-probe-split-baseline.py --write` → rc=0；
重跑對證 `與既有 golden 相同？ **True**`、rc=0。
golden＝`tests/golden/evtalign/split_baseline.json`，
`sha256 = f01550dbedd1547f1eb1d09343f9fcef4890c68dd96b81127d0fa123f2b107ea`。

| case | purge | embargo | train | test |
|---|---|---|---|---|
| `h2_emb0_n500` | 2 | 0 | 400 | 98 |
| `h2_emb12_n500` | 2 | 12 | 400 | 86 |
| `h5_emb0_n500` | 5 | 0 | 400 | 95 |
| `h5_emb12_n500` | 5 | 12 | 400 | 83 |
| `h12_emb0_n500` | 12 | 0 | 400 | 88 |
| `h12_emb12_n500` | 12 | 12 | 400 | 76 |
| `h5_emb0_n40_insufficient` | — | — | skipped: `train/test rows below min_test_rows` | |

🔴 **這組數字證實 §N 之 C6 更正**：`purge` 隨 h 變（2／5／12），`embargo` 獨立
（0／12），且 `test_rows` 隨兩者**相加**遞減 ⇒ 總隔離＝`purge + embargo`，
事件之 lookahead 經 embargo 進來後隔離只會**偏大**。**不是洩漏**。

🔴 **誠實邊界**：本基線只跑 `_build_holdout_split_plan`（純函式），
**不跑完整 analyze**（8 GB 機器上是十分鐘級）⇒ 只覆蓋切分計畫本身，
不覆蓋 stage1 之後；`embargo` 以參數化涵蓋，不等於跑過真實事件批。

### 🔴 逐模式盤點（Task 2.2 之產出；R1 三家獨立查證，結論一致）

| 模式 | 被驗的 series | 被 IC 消費的 series | 同一份？ | 判定 |
|---|---|---|---|---|
| **global**（`labels_df` 有） | stage0 `label_series`（`:2790-2796`） | stage4 同引用（`:2883-2885`→`:1067`） | ✅ **是** | 無鷹架 |
| **global**（`labels_df` 無） | stage2 `return_{horizon}`（`:2921-2928`） | stage4 同 series（`:2938`→`:1067`） | ✅ **是** | 無鷹架——**那條序列就是最終 label** |
| **event** | stage2 鷹架 或 stage0 預載（`:2923`／`:2790`） | stage3 覆寫後 `filtered_label`（`:3042`→`:1067`） | ❌ **否** | 🔴 **同型缺陷（本票主病灶）** |
| **cross_sectional** | **無**（從未呼叫 `validate_alignment`） | `numeric_df[label_col]` 直接進分組 IC（`:1503-1511`） | ⚠️ N/A | 不是鷹架，是**守衛缺席** ⇒ `EA-RESID-2` |

**同型形態之其他候選（R1 三家主動找出，我原本沒列）**：
- `split_context.effective_horizon` 與事件 label 語意脫鉤 ⇒ 見下方 C6-揭露項。
- stage0 預載 label 後被事件覆寫 ⇒ 與主病灶同型，一併由 Task 2.1 涵蓋。
- `insufficient_events` 退回主線 `return_N`（`:3010-3021`）⇒ **已 loud**
  （`conditional_ic_abandoned`），非靜默，不列缺陷。
- `fit_mode`／`oos_guarantees`、feature_filter ⇒ 三家判**無**同型 bug。

### 🔴 C6 之嚴重度更正（我先前對使用者說錯，在此留底）

我曾對使用者說「`purge` 用全域 h 算，與你設的 h 無關」，**聽起來像會洩漏**。查完**不是**：

| 成分 | 來源 | 碼證 |
|---|---|---|
| `purge_gap` | 全域 `effective_horizon`（YAML 之 5） | `ic_filter_orchestrator.py:957` |
| `embargo` | `max(config.embargo, 事件 purge_rows)` ← **依事件算** | `api/services/ic_analysis_service.py:1345` |
| **總隔離** | `effective_purge + effective_embargo`（**相加**） | `ic_filter_orchestrator.py:378` |

⇒ 事件之 lookahead **有**被涵蓋，隔離只會**偏大（保守）**，不會偏小 ⇒ **不是安全問題**。
**真正的問題是報告誤導**：只給一個 `purge_gap: 5`，使用者會以為它跟自己設的 h 有關。
⇒ 由「🔶 中（安全）」**降為低（揭露）**，交付物＝報告分開列出兩塊來源（Phase P5）。
