# 事件模式之對齊守衛與期間對齊 — TODO

**SPEC**：`docs/GAP3_EVENT_ALIGNMENT_SPEC.md`　**票**：`EVTALIGN`　**日期**：2026-09-07

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

- **解耦**：`momentum/` 不得 import `api/`（R1）；守衛住 `momentum/core/contracts.py`，
  呼叫端在 `momentum/Analysis/ic_filter_orchestrator.py`。API 層只傳參數，不自寫判準。
- **Logging**：`get_logger(__name__)`；逐列迴圈內**不得** log。
- **Error 分類**：對齊違規＝non-retryable（`AlignmentViolationError`）；
  拿不到 oracle 而處於截短情形＝non-retryable（**明確 raise，不得靜默通過**）。
- 🔴 **本票動的是防未來函數之守衛**。任何「讓原本會擋的情形變成通過」的改動，
  都必須有**對應的替代證明**（見 SPEC Task 1.1 之三層）。
- **防假綠**：不得放寬既有測試斷言。既有紅（非本票造成）：
  `tests/api/test_ichc_event_timestamps.py::…kwarg`（掃原始碼字串之弱測試）。
- **manifest ID**：`[A-1]`＝SPEC §A `ASSUME-1`（**已被 R1 推翻**）；`[A-2]`＝`ASSUME-2`（仍未驗）。

---

## §B 批次執行策略

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B0** | 0.1, 0.2 | 無 | scaffold ＋ **先把 `ASSUME-2` 實跑掉**（三家判「無法接受未驗」；golden 重做版含 fingerprint） | 小 |
| **B1** | 1.1, 2.1 | B0 | **B＋D 同批**（codex：不做 D ＝ 錯誤輸出進條件 IC）；兩者共用 `label_source` | 中 |
| **B2** | 2.2 | B1 | 跨模式不變式，需 B1 定案之呼叫點 | 小 |
| **B3** | 3.1 | B1 | 需要守衛先能接受截短 | 中 |
| **B4** | 4.1 | 無 | 與守衛無耦合，可平行 | 小 |
| **B5** | 5.1 | B1 | 揭露項，需 B1 定案之欄位 | 小 |

- **批次間 Gate**：`bash scripts/evtalign_phase_gate.sh <phase>` rc=0
  （沿用 SCANCUBE 之作法：skip 不算通過、空 golden glob 不算通過、mutation uncovered=0）。

---

## Phase 0 — 前置（完成後：假設已驗、Gate 跑得起來）

### Task 0.1 — 建立被引用但不存在的 artifact（`票 —`）

`票 —`：測試基礎設施。

- SPEC ref：§V　目標：消除「文件引用了不存在的檔案」之可執行性缺口（`COMPOSER-R1-P1-02`）。
- 輸入 / 輸出：無輸入；輸出＝四個 artifact 之骨架。
- 實作要點：
  1. `tests/momentum/test_alignment_tail_nan.py`、`tests/api/test_event_label_alignment.py`：
     建檔，各放 `pytest.skip("Task N.x 尚未實作")`——**skip 不是綠**。
  2. `handoffs/20260907-evtalign-mutate.py`：沿用
     `handoffs/20260906-gap3-disclosure-mutate.py` 之紀律（還原權威＝版控、
     開場檢查 HEAD、逐條還原、對照組 `EXPECT_GREEN`），初版含 `A1`–`A4` 佔位。
  3. `scripts/evtalign_phase_gate.sh`：三項任一失敗即 rc≠0
     （skip 清單／空 golden glob／mutation uncovered）。
- 修改檔案：新建上述四項。既有 caller：新建無。
- 路徑：
  - `tests/momentum/test_alignment_tail_nan.py`
  - `tests/api/test_event_label_alignment.py`
  - `handoffs/20260907-evtalign-mutate.py`
  - `scripts/evtalign_phase_gate.sh`
- 不可做：不得讓 placeholder 測試 pass（假綠）。
- 邊界：①空 golden glob ⇒ rc≠0（不是「0 個案例全過」）；
  ②mutation 對尚未存在之生產碼 ⇒ 印 `SKIP` 並計入 uncovered，不計入通過。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/momentum/test_alignment_tail_nan.py -q` rc=0（全 skip）；
  `bash scripts/evtalign_phase_gate.sh 0` rc≠0（因為還全是 skip）。
- **存活至**：永久。
- **覆蓋風險**：後續 Task 覆寫 placeholder＝預期。

### Task 0.2 — 實跑 `ASSUME-2`：`effective_horizon`／`purge_gap` 之基線（`票 UAT-3`）

- SPEC ref：§A `ASSUME-2`　目標：把「不受影響」從**假設**變成**基線數字**。
- 🔴 **為何排在實作之前**：`CODEX-R1-P1-03` 判「無法接受『不受影響』」——
  既有探針只證最終 label 逐值相同，**明確未測 purge**。
  沒有改前基線，改完就無從證明沒動到切分。
- 輸入 / 輸出：輸入＝固定 fixture（同尾／截短 × h<5／h=5／h>5 × 事件/全域）；
  輸出＝`tests/golden/evtalign/split_baseline.json`（改**前**之值）。
- 實作要點：
  1. 逐組合實跑，收集 `effective_horizon`／`purge_gap`／`embargo`／
     `train_time_bounds`／`test_time_bounds`／**`split_row_fingerprint`**（train/test 列索引集合之 sha256）／
     **`retained_event_ids`**；且須含**事件路徑**之案例（R2 三家：六欄在「端點不變但中段列被刪」時全不變）。
  2. 以 `json.dumps(..., sort_keys=True)` 落檔並記 `sha256`。
  3. **本 Task 不改任何生產碼**——只記錄現況。
- 修改檔案：新建 `handoffs/20260907-probe-split-baseline.py`；
  新建 `tests/golden/evtalign/split_baseline.json`。既有 caller：無。
- 路徑：
  - `handoffs/20260907-probe-split-baseline.py`
  - `tests/golden/evtalign/split_baseline.json`
- 不可做：不得在本 Task 改生產碼（改了基線就不是「改前」）。
- 邊界：①某組合跑不起來（如樣本不足）⇒ 記錄該 reason，**不跳過不記**；
  ②`purge_gap` 與 `embargo` 須**分開記**（SPEC §N 之 C6：兩者來源不同）。
- 風險緩解：⊘
- 驗證：`venv/bin/python handoffs/20260907-probe-split-baseline.py` rc=0，
  且 `tests/golden/evtalign/split_baseline.json` 之組合數 `>= 6`；
  每筆皆含上述六個欄位（缺任一 ⇒ rc≠0）。
- **存活至**：永久（B1–B5 每批收尾都要對照它）。
- **覆蓋風險**：🔴 **首版 golden 已作廢重做**（R2 `CODEX-R2-P1-05`／`COMPOSER-R2-P1-03`／
  `GROK-R2-P1-02` **三家**：六欄位在「端點不變但中段列被刪」時全部不變，
  且未涵蓋事件路徑與保留之 event IDs）。
  **必須增**：`split_row_fingerprint`（train/test 列索引集合之 sha256）、
  `retained_event_ids`、**事件路徑之案例**。
  已跑之 `sha256 = f01550db…` **不得**當基線使用。

---

## Phase 1 — 對齊守衛三層（完成後：截短不再誤擋，且洩漏仍被擋）

### Task 1.1 — **不動守衛**：label 生成前把 `close` 裁到 feature 尾（`票 UAT-3`）

🔴 consult（2026-09-08）三家共識 **B＋D**，三層設計刪除。守衛 `validate_alignment` **一字不改**。

- SPEC ref：Task 1.1（B）　目標：截短不再誤擋，守衛強度完全不變，**不新增任何參數**。
- 輸入 / 輸出：輸入＝`close: pd.Series`、`feature_index: pd.Index`；輸出＝裁切後之 `close`。
- 實作要點：
  1. 新建單一 helper（住 orchestrator，因兩個呼叫點都在該檔）：
     ```python
     def _coterminalize_close(close: pd.Series, feature_index: pd.Index) -> pd.Series:
         if len(feature_index) == 0:
             raise AlignmentViolationError("feature_index is empty; cannot coterminalize close")
         return close.loc[close.index <= feature_index[-1]]
     ```
     🔴 K 線尾**早於** feature 尾（K 線反而比特徵短）⇒ 此式為 no-op，交既有守衛照舊判定；本票不改該情形。
  2. 🔴 **兩個呼叫點都接**（三家獨立命中；composer：防「一點 derive、一點仍信參數」漂移）：
     - `_stage2_label_generation`（`:2902-2929`）：`close = _coterminalize_close(close, feature_index)`
       **在** `generate_returns_by_type` 之前。
     - `_stage0_ingestion` 預載 labels 路徑（`:2776-2796`）：同一支 helper，同一位置語意。
  3. **不得**碰 `momentum/core/contracts.py`。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py::_coterminalize_close`（新建）、
  `::_stage2_label_generation`、`::_stage0_ingestion`。既有 caller：`analyze`（不需改）。
- 路徑：
  - `momentum/Analysis/ic_filter_orchestrator.py`
  - `tests/momentum/test_close_coterminalize.py`
  - `tests/golden/evtalign/`
- 不可做：**不得改 `validate_alignment` 任何一行**；不得新增參數；不得做成 mode 分支；
  不得只改 stage2。
- 邊界：①同尾 ⇒ no-op，label 逐位元組不變；②截短 ⇒ 化約為同尾；
  ③`feature_index` 空 ⇒ raise；④K 線尾早於 feature 尾 ⇒ no-op、守衛照舊。
- 風險緩解：Task 0.2（重做版）之 golden 改前／改後逐值對照。
- 驗證：`venv/bin/python -m pytest tests/momentum/test_close_coterminalize.py -q` rc=0。通過條件：
  - 截短案例之 label 與同尾案例 **逐值 `==`**（NaN 位置與數值皆同）；主委探針
    `handoffs/20260908-probe-option-b-trim.py` rc=0 為前導證據。
  - `inspect.getsource(validate_alignment)` 之 sha256 與改前 **相同**（守衛未動）。
  - spy 斷言 stage0 與 stage2 各恰呼叫 `_coterminalize_close` 一次。
  - `effective_horizon`／`purge_gap`／`embargo`／`split_row_fingerprint`／`retained_event_ids`
    與 golden 逐值 `==`。
  - mutation `B1`：helper 改 no-op ⇒ 截短案例紅；`B2`：只改 stage2 ⇒ spy 測試紅；
    `B3`：動 `validate_alignment` 任一字 ⇒ sha256 測試紅。
- **存活至**：永久。
- **覆蓋風險**：無。

---

## Phase 2 — 驗證對象＝被消費的那條（完成後：不再驗鷹架，也不誤判事件 label）

### Task 2.1 — 呼叫點移到覆寫之後；`event_given` 契約（`票 UAT-2`）

- SPEC ref：Task 2.1　目標：不驗被丟棄的中間值，**也不製造新誤判**。
- 輸入 / 輸出：輸入＝stage3 覆寫後之 `filtered_label`；輸出＝驗證通過或 raise。
- 實作要點：
  1. `_validate_event_given(feature_index, values, spec)`＝
     「每個 timestamp 有值／值有限／index 與 features 逐值相等」
     ——**把 `ic_filter_orchestrator.py:3033-3041` 之既有檢查提升為契約**，不新寫一套。
  2. 呼叫點：stage3 覆寫（`:3042`）**之後**加一次
     `validate_alignment(..., label_kind="event_given")`。
     🔴 `COMPOSER-R1-P0-02`：現況 stage2（`:2923`）與 stage0（`:2790`）都在覆寫之前。
  3. 🔴 **事件模式下，覆寫前那條序列不驗**（R2 `GROK-R2-P0-02` 修正）。
     我 R1 寫「覆寫前照舊跑 forward_return」——那正是 SPEC §C-6 禁的
     「驗一個即將被丟棄的東西」，且在截短＋非 oracle 型別下會**重現原本的擋死**。
     判準由 `label_source` 決定（producer-set）：
     `event_label_value` ⇒ 覆寫前**不驗**、覆寫後以 `event_given` 驗；
     主線 ⇒ 照舊以 `forward_return` 驗（全域模式該序列**就是**最終 label）。
- 修改檔案：`momentum/core/contracts.py::_validate_event_given`；
  `momentum/Analysis/ic_filter_orchestrator.py::_apply_event_filter`（覆寫後加驗證）。
  既有 caller：`_stage3_event_filter`。
- 路徑：
  - `momentum/core/contracts.py`
  - `momentum/Analysis/ic_filter_orchestrator.py`
  - `tests/api/test_event_label_alignment.py`
- 不可做：不得跳過 `validate_alignment` 之呼叫；不得對 `event_given` 套 forward-return
  之尾端契約（`GROK-R1-P0-02`）；不得改動 `effective_horizon`／`purge_gap`（SPEC §C-2）。
- 邊界：
  1. **同尾**事件模式之合法密集 label（`tail_nans=0`）⇒ **通過**（不得誤判——`GROK-R1-P0-02`）。
  2. 事件 label 與 feature index 錯位 ⇒ **仍 raise**。
  3. `event_label_values` 缺任一 timestamp ⇒ 維持現行 loud raise。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/api/test_event_label_alignment.py -q` rc=0；
  三個邊界逐格斷言；mutation `A4`：對 `event_given` 套 forward_return 契約 ⇒ 邊界 1 紅。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.2 — 跨模式不變式：被驗的＝被用的（`票 UAT-2`）

- SPEC ref：Task 2.2　目標：把使用者的擔心（「還有沒有鷹架」）變成**可機械檢出**。
- 輸入 / 輸出：無；輸出＝參數化測試。
- 實作要點：
  1. 以**實際可觸發的情境**參數化，**不是**照後端 enum
     （🔴 後端 `mode` 只有 `longitudinal`／`cross_sectional` 兩值，
     而前端有 global／event／cross_sectional 三種；照 enum 參數化會**整個漏掉事件模式**）。
     情境清單＝`[global_with_labels, global_without_labels, event, cross_sectional]`。
  2. 每個情境斷言「傳給 `validate_alignment` 的 series」與
     「進入 IC 計算的 series」為同一份（以 spy 記錄物件 id 或逐值 `==`）。
  3. `cross_sectional` 目前無守衛 ⇒ 標 `not_applicable` 並**在測試訊息中寫明理由**
     （`EA-RESID-2`：模組未完工），不得靜默跳過。
- 修改檔案：新建 `tests/momentum/test_validated_series_is_used_series.py`。既有 caller：無。
- 路徑：
  - `tests/momentum/test_validated_series_is_used_series.py`
- 不可做：不得只測事件模式就宣稱完成；不得照後端 enum 參數化。
- 邊界：①新增模式時測試須自動涵蓋（情境清單為模組級常數，新增時未列入 ⇒ 測試紅）；
  ②某情境確實無中間序列 ⇒ 標 `not_applicable` ＋ 理由。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/momentum/test_validated_series_is_used_series.py -q` rc=0；
  情境數 `>= 4`；mutation `A6`：在 global 插入一條被丟棄的中間驗證 ⇒ 該情境紅。
- **存活至**：永久（防同型缺陷再生之閘）。
- **覆蓋風險**：無。

---

## Phase 3 — 期間自動對齊（完成後：使用者不必手動重生特徵）

### Task 3.1 — 期間交集 ＋ **丟失事件之揭露**（`票 UAT-4`）

- SPEC ref：Task 3.1　目標：系統自己處理期間不一致（使用者原話④）。
- 輸入 / 輸出：輸入＝feature run 期間、kline 期間、事件期間；
  輸出＝分析區間 ＋ `metadata.period_alignment`。
- 實作要點：
  1. 分析區間＝三者交集；`metadata.period_alignment` 記
     `{used: {start,end}, trimmed_bars: {head,tail}, dropped_events: {count, ids}}`。
  2. 🔴 **必須揭露丟掉的事件數與 ID**（`COMPOSER-R1-P2-01`／`GROK-R1-P1-02`：
     「禁靜默裁切」與「只報根數」**不等價**——根數不告訴使用者少了哪些事件）。
  3. 交集為空 ⇒ fail-closed，訊息含三者各自的期間。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py::analyze`（交集計算與 metadata）；
  🔴 **`api/services/ic_analysis_service.py` 之 batch-level containment gate**
  （R2 `CODEX-R2-P1-06`：該 gate 會在交集**之前**就 raise ⇒
  「部分事件被丟後成功並揭露 IDs」永遠到不了，需求與控制流互斥）。
  ⇒ 該 gate 須改為在交集**之後**判定，或改為 warn＋揭露。
  既有 caller：`_run_analysis`。
- 路徑：
  - `momentum/Analysis/ic_filter_orchestrator.py`
  - `tests/api/test_period_auto_align.py`
- 不可做：不得靜默裁切；不得只報根數；不得要求使用者手動重生特徵。
- 邊界：①事件全部落在特徵期間外 ⇒ loud raise；
  ②部分事件被丟 ⇒ **成功但 metadata 列出 ID**；③交集為空 ⇒ raise。
- 風險緩解：Task 0.2 基線（保留之 event IDs 逐項對照）。
- 驗證：`venv/bin/python -m pytest tests/api/test_period_auto_align.py -q` rc=0；
  邊界②之斷言須檢查 `dropped_events.ids` **非空且逐值正確**（不是只看 count）；
  mutation `A7`：把 `ids` 改成只回 count ⇒ 該測試紅。
- **存活至**：永久。
- **覆蓋風險**：無。

---

## Phase 4 — 進度可見（完成後：使用者知道現在在做什麼）

### Task 4.1 — 階段內進度 ＋ **記憶體 WARN（非阻擋）**（`票 UAT-1`）

- SPEC ref：Task 4.1　目標：使用者原話「我只是不知確切的狀態進行式是什麼」。
- 輸入 / 輸出：輸入＝處理進度；輸出＝progress callback 之中間回報。
- 實作要點：
  1. preprocessing 等長階段回報「已處理特徵數／總數」與 ETA；
     無法預估時顯示「預估中」，**不得顯示假的 ETA**。
  2. 🔴 **記憶體 WARN（三家一致要求）**：RSS 超過實體記憶體或 swap 增長 ⇒
     progress 通道發 **WARN**（`memory_pressure_observed`），
     **不 raise、不擋**（§C-4：使用者明講「可以跑的話，幹嘛擋?」）。
     實測依據：17 GB／8 GB 實體、swap 15.6 GB、CPU 3.3% ＝ thrash。
  3. 回報頻率**不得進 hot loop**：每 N 個特徵或每 M 秒一次，取較稀疏者。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py::_stage1_preprocessing`（中間回報）；
  `api/services/ic_analysis_service.py`（WARN 透傳）。既有 caller：`progress_callback`。
- 路徑：
  - `momentum/Analysis/ic_filter_orchestrator.py`
  - `api/services/ic_analysis_service.py`
  - `tests/api/test_stage_progress.py`
- 不可做：🔴 **不得新增任何阻擋閘**；不得顯示假 ETA；不得在 hot loop 內 log。
- 邊界：①無法預估 ⇒ 顯示「預估中」；②記憶體正常 ⇒ **不發** WARN（不製造噪音）；
  ③回報頻率須可驗（測試斷言呼叫次數在合理區間，不是每列一次）。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/api/test_stage_progress.py -q` rc=0；
  斷言中間回報次數 `>= 3` 且 `<= max(3, ceil(總特徵數 / 100))`
  （🔴 R2 `CODEX-R2-P1-10`：原式在測試資料 < 300 特徵時**無整數解**，驗收不可執行）；
  上界須以 **≥300 特徵之 fixture** 另驗；
  mutation `A8`：把 WARN 改成 raise ⇒ 「不得阻擋」之測試紅。
- **存活至**：永久。
- **覆蓋風險**：無。

---

## Phase 5 — purge／embargo 揭露（完成後：使用者看得懂隔離區怎麼來的）

### Task 5.1 — 隔離區之兩塊來源分開揭露（`票 UAT-2`）

- SPEC ref：§N 之 C6　目標：報告不再讓使用者誤以為 `purge_gap` 跟自己設的 h 有關。
- 🔴 **這是揭露項，不是安全項**（SPEC §N 已留底更正）：
  查證 `embargo` 依事件算、總隔離為**相加** ⇒ 隔離只會偏大（保守），不是洩漏。
- 輸入 / 輸出：輸入＝`effective_purge`／`effective_embargo`；
  輸出＝`metadata.isolation`＝`{purge: {bars, source}, embargo: {bars, source}, total_bars}`。
- 實作要點：
  1. `purge.source = "global_default_horizon"`、`embargo.source = "event_lookahead"`
     （或 `config_embargo`，取實際生效者）。
  2. 前端於降級／切分說明處顯示兩塊來源，不再只給一個數字。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py`（metadata 新增 `isolation`）；
  `frontend/src/components/ic-analysis/DegradedBanner.tsx`（顯示）。
  既有 caller：報告消費端。
- 路徑：
  - `momentum/Analysis/ic_filter_orchestrator.py`
  - `frontend/src/components/ic-analysis/DegradedBanner.tsx`
  - `tests/api/test_isolation_disclosure.py`
- 不可做：不得改變 purge／embargo 之**計算**（只揭露）；不得把兩塊合併成一個數字。
- 邊界：①未切分 ⇒ 不顯示本節（不是顯示 0）；②`embargo` 來自 config 而非事件 ⇒ source 標明。
- 風險緩解：Task 0.2 基線（值不得變動）。
- 驗證：`venv/bin/python -m pytest tests/api/test_isolation_disclosure.py -q` rc=0；
  斷言 `total_bars == purge.bars + embargo.bars` 且兩者 `source` 皆非空；
  與 Task 0.2 基線之 `purge_gap`／`embargo` 逐值 `==`（證明只揭露、沒改算法）。
- **存活至**：永久。
- **覆蓋風險**：無。

---

## Phase 測試與 Gate

- **單元**：`tests/momentum/test_alignment_tail_nan.py`、`test_validated_series_is_used_series.py`
- **整合**：`tests/api/test_event_label_alignment.py`、`test_period_auto_align.py`、
  `test_stage_progress.py`、`test_isolation_disclosure.py`
- **Golden**：`tests/golden/evtalign/split_baseline.json`（Task 0.2 產出）
- **mutation**：`handoffs/20260907-evtalign-mutate.py`（`A1`–`A8` ＋ 對照組）
- **Phase Gate**：`bash scripts/evtalign_phase_gate.sh <phase>` rc=0
  —— skip 清單非空／golden glob 為空／mutation uncovered≠0，**任一即 fail**。
