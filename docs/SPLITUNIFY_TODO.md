# SPLITUNIFY — TODO

**SPEC**：`docs/SPLITUNIFY_SPEC.md`（**v4**）　**票**：`SPLITUNIFY`　**日期**：2026-09-11　**狀態**：**v5（B1 放行版）**。
**R3 審收斂**：`handoffs/reconcile/20260911-splitunify-x-review-r3/synth.md`（E1–E7）——
🔴 三家分歧（composer／grok 判可進 B1、codex 判不可），依「看碼證不數人頭」採 codex：
v3 的投影**把既有的答案窗 purge 規則弄丟了**（`event_split.py:114`），v4 以兩段式判定修復。
**R2 審收斂**：`handoffs/reconcile/20260911-splitunify-x-review-r2/synth.md`（D1–D11；
三家 verdict 一致「不可直接進 B1」，17 條全數採納）。
**切法來源**：委員會 consult 共識（`handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`，
D1–D8，body-hash `120b4d042d38…`，**三家 RECONCILE-STAMP 全數 APPROVED**）。
**R1 審收斂**：`handoffs/reconcile/20260911-splitunify-x-review-r1/synth.md`（C1–C13）。
使用者 2026-09-10 裁定「切法由你跟委員討論共識」，離線時再次授權 ⇒ **不回頭問使用者**。
**實作端**：Claude 主委自任；review＝codex＋composer＋grok 三家全員。

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

- **解耦**：`momentum/` 不 import `api/`（R1）；services 不互 import（R4）。
  新投影模組 `momentum/Analysis/event_samples/split_projection.py` 只吃 `SplitPlan`、
  `pd.Index` 與 `EventManifest`，**不讀 config、不做 I/O**。
  邊界 builder 住 `momentum/core/split_preview.py`（既有檔，檔頭已載明「同一算術、無副作用」）。
- **Logging**：`get_logger(__name__)`；投影迴圈內**不得** log（10k 事件級）。
- **Error 分類**：多 symbol 未支援、缺 train／test plan、缺 canonical feature universe
  皆為 non-retryable，`ValueError` 明確 raise（reason 字面出自 `split_unify.json`）。
  **禁**以警告放行。
- **不可違反原則**：不弱化任何既有隔離閘；🔴 **containment 未證明前不得刪除任一既有 guard**
  （SPEC C-1 附帶約束①）；全域（非事件）路徑報告逐位元組不變（G-2）；
  golden 比對失敗**不得**自動覆蓋。
- **🔴 本票之三條核心禁令**：
  1. 禁以全域 scalar `test_timestamps` 交集取代事件計畫（SPEC C-2；已有實測 receipt
     `20260910T150504Z-splitunify-multisymbol`：全域 12 列 vs per-symbol 8 列）。
  2. 禁以 `time_bounds` 閉區間取代**集合**成員判定（SPEC C-4）。
  3. 禁在拿不到 canonical feature universe 時按事件數另切並宣稱 OOS（SPEC C-0 決議③；
     實測 receipt `20260910T154323Z-splitunify-universe-gap.log`：裁切 168 根 ⇒ 邊界差 67 小時）。
  4. 🔴 **禁呼叫 `_normalize_ic_time_index`**（R2 之 D7）——它是**「秒」語意**的 normalizer，
     `ic_filter_orchestrator.py:269-271` 明文 raise「looks like milliseconds, expected epoch
     seconds」。本票之時鐘一律 epoch **毫秒**，用 `pd.to_datetime(..., unit="ms")` 或
     `asi8 // 10**6` 自行歸一。
  5. 🔴 **禁只用集合成員判定就決定 train／test**（R3 之 E1）——必須**先**驗答案窗跨界
     （`label_end_ms` 進測試段或 source bars 缺 endpoint ⇒ purged），**再**做集合判定。
     少了第一段等於刪掉 `event_split.py:114` 那道唯一擋標籤窗跨界洩漏的閘，
     直接違反「不得刪除任一既有 guard」。
- **本票之落點裁定（R2 之 D1）**：事件掃描端（`EventImportService`）**恆走** event-study-only，
  本票**不新增** universe 供給路徑（列為殘留 `R-5`）。IC 路徑才傳 canonical boundary。
- **防假綠**：驗收讀 pytest 自己的 summary 行（非 harness rc）；
  🔴 既有紅**逐條** `--deselect`（`tests/baselines/analysis_known_failures.nodeids`），
  **禁**寫「failed <= N」這類聚合期望數（R1 之 C3；grok 與 composer 各標 P0）。
- **每批收尾**：commit → 背景 push → 更新 `白話說明/現在做到哪.md` 與
  `白話說明/SPLITUNIFY施工進度.md`（細項逐條，使用者 2026-09-10 定）。

---

## §B 批次執行策略

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B1** | 1.1, 1.2, 1.3 | consult 三家戳記 rc=0（**已達成**） | 文件、枚舉 SoT、既有紅基準；**不動生產碼**（可獨立審） | 小 |
| **B2a** | 2.1 | B1 | boundary builder 可獨立證偽（同源自證＋ms 同源） | 中 |
| **B2b** | 2.2 | B2a | 投影純函式＋`build_time_clusters` 抽出 | 大 |
| **B2c** | 2.3 | B2b | golden 五組；**仍不接線** | 中 |
| **B3** | 3.1, 3.2, 3.3 | B2c | 接線／fail-closed／event-study-only 分派同批（分開會有一段時間邊界不唯一） | 大 |
| **B4** | 4.1 | B3 | 報告與畫面（欄名待 B3 定案後才穩定） | 中 |
| **B9A** | 9.1 | B4 ＋ `D-002` 三家 `RECONCILE-STAMP` rc=0 | 揭露先行；只動 producer 回傳形狀與 summary 一鍵，可獨立回退 | 中 |
| **B9B** | 9.2, 9.2a | B9A | 🔴 **不得拆批**：全量列在無 `feature_timeframe` 欄時複合鍵碰撞，加欄而不改 merge 則 `MergeError` ⇒ 只改其一皆紅 | 大 |
| **B9C** | 9.2b | B9B | 側別改 `decision_at_ms` 錨定 ＋ `(3.2)` 跨表互斥；鍵不唯一時「同側」無定義，故須在複合鍵已存在後 | 大 |
| **B9D** | 9.3 | B9C | `Task 9.3` 表列**九處**逐處處置（七個下游消費模組——`feature_materialization`／`tables`／`ic_feed`／`counterexample_classifier`／`candidate_ledger`／`dedupe`／`pattern_bridge`——＋ event-level 表／manifest 與前端 `byEventId` 兩個支撐面，共九列；多為**防誤改**回歸測試，非改碼）。🔴 R13 `CODEX-R13-P2-03`：本欄原寫「六個下游消費面」與表列九列不符，已改為與表列一致 | 中 |
| **B9E** | 9.4 | B9C | 記帳鏈與 `baseline` 拆鍵 | 中 |
| **B9F** | 9.5 | B9D ＋ B9E | golden 換錨與前端；須在所有行為面定案後才凍結 | 大 |

🔴 **Phase 9 依賴序（`handoffs/reconcile/20260911-splitunify-b9-consult-r2/synth.md` 裁定；三家＋主委獨立版四方一致）**：
`9.1 → 9.2 → 9.2a → 9.2b → (9.3 ∥ 9.4) → 9.5`。
`9.3` 與 `9.4` 可並行（前者動消費面、後者動計數與 `baseline`），惟 `9.4` 之 `per_symbol_n`／`tier_min` 去重
與 `9.2a` 同檔 ⇒ 並行時須先 rebase 再跑各自驗收。
`9.5` **必須最後**——golden 重凍會把未定側別寫死。

🔴 **R2 之 D11（codex Q8）**：v2 把 B2 標「大」卻只有批末一個 gate，
等於把三個**可獨立證偽**的產出綁成一次審查 ⇒ 拆為 B2a／B2b／B2c，各自 gate 與 review。

Gate：每批該批測試 rc=0 且 skip 數為 0；每批三家 code review 收斂後才進下一批
（`review_quorum_check.sh` 機檢）。

---

## §C Task 細目

### Task 1.1 — GAP-3 延伸檔 `D-002`（`票 SPLITUNIFY`）
- SPEC ref：C-7　目標：記錄切分權威變更與投影契約；**不解凍** GAP-3 原檔。
- 輸入 / 輸出：無 → `docs/GAP3_EVENT_UX_SPEC.D-002.md`。
- 實作要點：
  1. 標題與狀態行標明「延伸檔，原檔 FROZEN 不動」。
  2. 須含 `split_authority == "kline_holdout"` 字面，交叉引用 SPEC 之 C-0／C-1／C-2／C-4。
  3. 🔴 明寫「投影所用 `feature_index` 為 **post-trim**（EVTALIGN 裁頭尾之後）之 universe」
     （`COMPOSER-R1-P2-01`）。
  4. 🔴 明寫**正確的規格入口路徑**——frozen primary 與 UX extension convention 的路徑字面
     目前不一致，不寫清楚會讓派工選錯入口（`CODEX-R1-P2-06`）。
  5. 明列「本延伸檔改變了 GAP-3 之哪一條」：事件切分不再自行決定邊界。
- 修改檔案：`docs/GAP3_EVENT_UX_SPEC.D-002.md`（新）。既有 caller：無。
- 不可做：不動 `docs/GAP3_EVENT_UX_SPEC.D-001.md`；不改 GAP-3 原 SPEC。
- 邊界：①原檔已 FROZEN ⇒ 只新增；②延伸檔本身須過格式檢查。
- 風險緩解：⊘
- **驗證**：`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_SPEC.D-002.md` rc=0；
  `grep -c 'kline_holdout' docs/GAP3_EVENT_UX_SPEC.D-002.md` >= 1；
  `grep -c 'post-trim' docs/GAP3_EVENT_UX_SPEC.D-002.md` >= 1。
- **存活至**：全票完工後保留。
- **覆蓋風險**：B4 之 UAT 項會追加條目，不刪既有段。

### Task 1.2 — 枚舉單一真相源 `split_unify.json`（`票 SPLITUNIFY`）
- SPEC ref：C-8　目標：權威值集與 fail-closed reason 一檔定義。
- 輸入 / 輸出：無 → `momentum/Analysis/contracts/split_unify.json`：
  `split_authority_values=["kline_holdout"]`、
  `fail_closed_reasons=["multi_symbol_projection_unsupported","missing_train_plan",
  "missing_test_plan","canonical_feature_universe_unavailable"]`。
- 實作要點：
  1. `split_projection.py` 之常數由本 JSON 讀取，缺鍵 ⇒ import 期 raise。
  2. 測試以 JSON 對證 Python 常數集合（`==`），兩端不得各自手打。
  3. 🔴 **不得**加 `assignment_states`——三態＝兩容器（`assignments` ＋ `purged`），
     不是三值枚舉；purge reason 沿用 `event_import_contract.json:465-467` 之
     `split_purge_reasons`（字面 `interval_crosses_split_boundary`）。
- 修改檔案：`momentum/Analysis/contracts/split_unify.json`（新）；
  `tests/momentum/Analysis/test_splitunify_contract.py`（新）。既有 caller：無。
- 不可做：不在 Python 端手打第二份值集；不加 `assignment_states`；不另造 purge reason。
- 邊界：①JSON 缺鍵 ⇒ raise；②值集為空 ⇒ raise。
- 風險緩解：⊘
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_contract.py` rc=0：
  值集與**第二來源**逐值相等；刪一鍵 ⇒ 該測試紅（可證偽）；
  🔴 B1 之第二來源是 **SPEC 文件字面**（B1 不動生產碼，`split_projection.py` 尚未存在）——
  這是**弱形式**對證（同一人同一批寫成，共同模式失效風險真實）；
  B2b 建模組後才補「JSON ↔ Python 常數集合相等」（測試檔尾已具名 `TODO(B2b)`）。
  `assert "assignment_states" not in json`。
- **存活至**：全票完工後保留（前端亦讀）。
- **覆蓋風險**：B3 若發現新 fail-closed 情形會**追加** reason 值，不改既有值。

### Task 1.3 — 既有紅基準清單（`票 SPLITUNIFY`）
- SPEC ref：Task 1.3／R1 之 C3　目標：讓 B3 驗收逐條可證偽，取代聚合期望數。
  🔴 基準以 B1 凍結之 receipt 為準＝**19 條 / 1103 passed**；`HANDOFF.md` 舊記的「20 條 / 1615 passed」
  是**不同收集面**的舊量測（grok 以 passed 基數 1615 vs 1103 證明那不是漏抓，`GROK-R1-P3-01`），**不再引用**。
- 輸入 / 輸出：實跑 pytest → `tests/baselines/analysis_known_failures.nodeids`
  ＋ `handoffs/run_receipts/splitunify-analysis-baseline.stdout`。
- 實作要點：一次實跑產出，**不得手抄湊數**；🔴 **須捕獲 pytest 自己的 rc**（R2 之 D9）——
  管線經 `tee`／`awk` 會把 rc 吃掉，collection failure 會偽裝成空基準
  （即 `CLAUDE.md` Gotchas 的「`cmd | tail; echo rc=$?` 讀到的是 tail 的 rc」）：
  先 `pytest … > <receipt> 2>&1`、把 `pytest_rc=$?` 追寫進 receipt，
  再 `awk '/^FAILED /{print $2}' <receipt> | grep '::' | sort -u > <清單>`。
  🔴 **`grep '::'` 不可省**（B1 實跑抓到）：`-q` 模式下 pytest 的進度條殘片會讓
  `^FAILED ` 多命中 11 行，`$2` 取出 `[`、`[100%]` 這種非 nodeid；不過濾就會把它們
  凍進基準，`--deselect` 時直接壞掉。實測 30 行 `^FAILED ` 中只有 19 行是真 nodeid。

- 🔴 **維護協議（R2 之 D9，四方一致）**：清單在 B1 凍結、B3 才用。
  B3 驗收 (B) 為**方向性**：實際 FAILED **⊆** 清單（只准變短）為綠、變長判紅。
  變短時允許**同一 PR** 更新清單與 receipt，commit 訊息標 `splitunify-baseline-sync`
  並具名哪一條變綠。B2 期間 `REDSWEEP` 修好某條亦走此協議。
- 修改檔案：`tests/baselines/analysis_known_failures.nodeids`（新）；
  `handoffs/run_receipts/splitunify-analysis-baseline.stdout`（新）。既有 caller：無。
- 不可做：不得手寫 nodeid；不得把本票新增之測試檔放進清單；
  不得在驗收紅時直接改驗收條件（只能依維護協議改清單並具名）。
- 邊界：①清單**可以為空**（既有紅已清）⇒ B3 驗收改為直接 rc=0；此時**不得**用 `test -s`
  當閘（會把合法空清單判成失敗），改驗「receipt 存在且 `pytest_rc` 已記錄」；
  ②清單中任一條變綠 ⇒ 依維護協議移出。
- 風險緩解：⊘
- **驗證**：`venv/bin/python -m pytest -q --collect-only $(cat tests/baselines/analysis_known_failures.nodeids)`
  rc=0（清單內有不存在的 nodeid ⇒ rc≠0，可證偽）；
  `grep -c '^pytest_rc=' handoffs/run_receipts/splitunify-analysis-baseline.stdout` == 1；
  清單行數 == receipt 內 `^FAILED ` **且含 `::`** 的行數
  （🔴 B1 review `CODEX-R1-P1-02`：不加 `::` 過濾就是 19 ≠ 30，條件永遠不成立——
  我在補萃取過濾時沒同步改驗證條件，是「改裁決必同步所有引用」那條的形態）。
- **存活至**：`REDSWEEP` 票收案後刪除。
- **覆蓋風險**：`REDSWEEP` 會逐條清空；兩票之間以「只准變短」為不變式。

### Task 2.1 — canonical boundary builder（`票 SPLITUNIFY`）
- SPEC ref：C-0　目標：兩端共用之**唯一**邊界算術。
- 輸入 / 輸出：`holdout_boundary(feature_index, *, oos_test_size, purge_gap, embargo)`
  → `Dict[str, Any]`，鍵為 `train_row_index`／`test_row_index`／`train_end_ms`／`test_start_ms`
  （B1 review `GROK-R1-P3-02`：v5 原寫元組、實作回 dict；回 dict 是為了讓 B3 呼叫端
  不必記順序，較不易錯 ⇒ 改文件對齊實作）。
- 實作要點：
  1. **以既有函式定義自身**：`holdout_split_point` ＋ `holdout_test_row_index`
     ⇒ 不引入第二份算術（否則 `M-SU-11` 會紅）。
  2. 🔴 **ms 導出寫死（R2 之 D6）**：`train_end_ms = as_ms(feature_index[train_rows[-1]])`
     （空 ⇒ `None`）、`test_start_ms = as_ms(feature_index[test_rows[0]])`（空 ⇒ `None`）。
     **ms 僅供揭露與 `boundary_hash`，禁回流做 ∈ 判定**。
     反例（codex）：寫成 `test_start_ms = feature_index[split_point]`（略過 purge／embargo）
     也能過原本的 `-k same_source` ⇒ 舊判準擋不住，故新增 `-k ms_same_source`。
  3. 時間一律 epoch ms；DatetimeIndex 以 `asi8 // 10**6` 換算（同 `split_preview.py:77-78`）。
  4. 純算術、無副作用、不 import `api`。
- 修改檔案：`momentum/core/split_preview.py`（既有檔新增函式）。
  既有 caller：`ic_filter_orchestrator`（B3 接）、`pipeline`（B3 接）。
- 不可做：不得在此讀 config；不得回傳 datetime（統一 ms）；不得自己重寫切點公式。
- 邊界：①`feature_index` 為空 ⇒ raise；②`test_rows` 為空 ⇒ `test_start_ms` 回 `None`
  （**不得**回 `-1` 或 `0`）；③`purge_gap`／`embargo` 為呼叫端算好的最終值。
- 風險緩解：mutation `M-SU-11`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/core/test_splitunify_boundary.py` rc=0：
  回傳之 `test_row_index` 與 `holdout_test_row_index(...)` 逐值相同（`np.array_equal`）；
  🔴 `-k ms_same_source`：`train_end_ms == as_ms(feature_index[train_rows[-1]])` 且
  `test_start_ms == as_ms(feature_index[test_rows[0]])`；
  空 index ⇒ raise；`pd.to_datetime(train_end_ms, unit="ms").year` ∈ [2015, 2035]（防 1970 坑）。
- **存活至**：全票完工後保留（唯一邊界實作）。
- **覆蓋風險**：B3 只增加 caller，不改簽名。

### Task 2.2 — `derive_event_split_from_plans` 純函式（`票 SPLITUNIFY`）
- SPEC ref：C-3、C-4、C-5　目標：由 canonical 邊界導出**完整**的 `EventSplitPlan`。
- 輸入 / 輸出：
  `(train_plan, test_plan, event_keys, feature_index, *, manifest, bucket_ms=None)`
  → `EventSplitPlan`。🔴 `event_keys` 是 **DataFrame 不是 Index**（R3 之 E2；R4 之 F4：
  v4 的本欄仍寫 `event_index`，與 SPEC C-4 互斥 ⇒ 只讀本檔的實作端會建錯簽名）。
  🔴 `bucket_ms` 是 R2 之 D8 補上的——v2 要求投影產 `clusters` 卻沒給桶寬參數。
- 實作要點：
  1. 🔴 **兩段式判定，先後不可調（R3 之 E1；式子逐字採 R4 之 F1）**：
     `train_cutoff = feature_cutoff_ms ∈ as_ms(feature_index[train_plan.row_index])`；
     `test_plan.row_index` 為空 ⇒ **先 fail-closed**（`missing_test_plan`），禁與 `None` 比較；
     `test_start_ms = as_ms(feature_index[test_plan.row_index[0]])`；
     `train_cutoff and label_end_ms >= test_start_ms` ⇒ **purged**（`>=` 必須保留）。
     🔴 `purge_gap`／`embargo` 是 **row 單位且已含在 test row 起點**，**不得**再以毫秒相減。
     source bars 缺 endpoint 之檢查**不進投影**——明定為上游 alignment 之前置條件，
     G-5.3 用 `AlignmentReceipts` 驗。
     **再**做集合成員判定決定 train／test。
  2. 成員判定＝**集合**：`feature_cutoff_ms ∈ feature_index[train_plan.row_index]` ⇒ train；
     `∈ feature_index[test_plan.row_index]` ⇒ test；否則 purged。禁 `time_bounds` 區間。
  3. `event_keys` 以 **`event_id` 為鍵**對位，**禁 positional zip**（R3 之 E2）——
     `dedupe.py:46` 會依 `(label_start_ms, event_id)` 重排 manifest。
     🔴 **producer 具名（R4 之 F2）**：B2b 之 `build_event_keys(receipts, *, selected_timeframe)`，
     由 `receipts.event_level` ＋ `receipts.per_tf`（`feature_cutoff_ms` 住這裡）keyed join；
     **B3 只傳遞，不臨時組裝**；每事件須恰一個 selected `per_tf` row，否則 raise
     （`manifest.table` 只有 trigger `timeframe`、無 cutoff，不可代替）。
  2. train／test 進 `assignments`（`split_label` 仍只有兩值）；purged 進**獨立**的
     `purged`，reason ＝ `interval_crosses_split_boundary`（契約既有字面）。
  3. `index_kind != "positional"` ⇒ raise；同時落兩態 ⇒ raise；
     🔴 單位歸一**自己做**（`pd.to_datetime(..., unit="ms")` 或 `asi8 // 10**6`），
     **禁呼叫** `_normalize_ic_time_index`——它是「秒」語意，餵毫秒會 raise
     （`ic_filter_orchestrator.py:269-271`）。v2 寫「復用該 normalizer」是錯的（R2 之 D7）。
  4. `event_keys.feature_cutoff_ms` 語意＝ feature_cutoff（`ic_feed.py:36`），非裸 `decision_at_ms`；
     不在 `feature_index` 集合內 ⇒ purged，**禁 nearest／asof／ffill**。
  5. `clusters` 呼叫本 Task 一併抽出的 `build_time_clusters(manifest, bucket_ms)`
     （行為 byte 級不變，**保留** `_cluster_weight` 之 M5 mutation seam）。
  6. `summary` **12 鍵**齊全：`n_symbols`／`per_symbol_n`／`n_time_clusters`／
     `avg_cluster_size`／`degraded`／`loso_status`／`insufficient_events_in_test`／
     `stats_modes`／`n_events_raw`／`n_events_effective`／`n_purged`／`bucket_ms`。
     `insufficient_events_in_test` 改看**投影後**的 test 數。
     🔴 `single_symbol` **恆亮是預期的**（R2 之 D11，四方一致）：Task 3.2 之多 symbol
     fail-closed 使存活路徑恆 `n_symbols == 1` ⇒ `_degraded_flags`（`event_split.py:22-33`）
     恆 append `single_symbol` ⇒ `tables.py:138` 之 `formal_pooled_inference_allowed` 恆 `False`。
     方向保守、是正確揭露；**不得**為了讓它變 `True` 而清空 `degraded`。
  7. `EventSplitConfig.embargo_ms` 與 `embargo_ms_by_symbol` 須為 `None` 否則 raise，
     但 🔴 **該檢查住呼叫端（Task 3.1 接線處），不在投影內**——投影是純函式、不吃 config
     （R2 之 D8：v2 把「投影須 raise」與「投影不吃 config」寫在一起，介面不可執行）。
  8. 純函式：無 log、無 I/O、不讀 config、不改輸入。
- 修改檔案：`momentum/Analysis/event_samples/split_projection.py`（新）；
  `momentum/Analysis/event_samples/event_split.py`（抽出 `build_time_clusters`）。
  既有 caller：無（B3 接）。
- 不可做：不得讀 config；不得自算 purge／embargo；不得回退成二態；
  不得把 purged 併進 `assignments`；不得產出空 plan 冒充未切分。
- 邊界：①`event_keys` 為空 ⇒ 三態皆空（不 raise）；②事件不在 `feature_index` ⇒ purged；
  ③全部落隔離區 ⇒ `assignments` 空而 `purged` 為全集（合法，`tables.py:201` 已明載不得誤擋）。
- 風險緩解：mutation `M-SU-1`..`M-SU-7`、`M-SU-12`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` rc=0：
  `len(assignments) + len(purged) == len(event_keys)` 且兩者 event_id 交集為空；
  `set(summary.keys()) == {12 鍵}`（逐鍵斷言）；
  `clusters` 與舊 `split_events` 之 `clusters` 逐值相同（`pd.testing.assert_frame_equal`）；
  五個邊界各一條（空 index／單事件／全 purged／未匹配時間戳／秒 vs 毫秒單位錯）。
- **存活至**：全票完工後保留（唯一投影實作）。
- **覆蓋風險**：B3 只增加 caller，不改簽名。

### Task 2.3 — golden 凍結（G-1／G-3a／G-3b／G-4／G-5）（`票 SPLITUNIFY`）
- SPEC ref：§G　目標：成員集合、遷移報告、獨立 oracle、per-symbol counts、containment 四項。
- 輸入 / 輸出：既有事件批 → `tests/golden/splitunify/*.json`
  ＋ `handoffs/run_receipts/` 之 G-3a 遷移報告。
- 實作要點：
  1. `scripts/freeze_splitunify_golden.py`：`--write` 凍結、預設比對；
     比對失敗 rc=1 並**指名差集之 event_id**。
  2. **G-3a**（一次性遷移報告）：舊 `split_events` vs 新投影之差集，
     附 `diff_event_ids` 之 sha256 與基數，寫 `handoffs/run_receipts/`；
     🔴 **不進**預設比對綠徑（凍結「預期有差」的 golden 會把已知錯誤合法化）。
  3. **G-3b**（長期 golden）：新投影 vs **獨立 oracle**——直接由
     `feature_index[plan.row_index]` 投影出的 event_id 集合，要求集合相等。
  4. 🔴 **G-5 四項，逐項 oracle（R2 之 D3；v2 只列名，三家一致判 BLOCKING 空殼）**：
     ①**row fingerprint**＝canonical `(position, feature_ts_ms, symbol, base_universe_hash)`
     之 exact `sha256`（sorted、int64、無空白 JSON），與 IC orchestrator 同批輸出逐值相等；
     失敗須**指名第一個 mismatch 的 position**。
     ②**assignments／purged IDs**＝由 `feature_index[plan.row_index]` 直接產生之集合為 oracle
     （與被測函式獨立），斷言互斥、涵蓋全集、`purged.reason` 字面
     == `interval_crosses_split_boundary`；失敗輸出 diff 之 event_id 清單。
     ③**answer-window 完整性**＝對每個 test 段事件斷言 `label_start_ms`／`label_end_ms`
     在 source bars 上兩端 endpoint 皆存在；缺 endpoint 或跨界者**必產 purge** 並輸出 event_id。
     ④**leakage negative case**＝合成 fixture 把一筆 train 事件的 `label_end_ms` 推進 test 區，
     斷言它進 `purged`（不得留在 `assignments`）；拿掉該斷言 ⇒ mutation rc=1。
     每項須有對應 nodeid（`tests/momentum/Analysis/test_splitunify_golden.py -k <name>`）
     或 freeze 腳本子模式，缺一即視為未實作。
- 修改檔案：`tests/golden/splitunify/*.json`（新）；`scripts/freeze_splitunify_golden.py`（新）。
  既有 caller：無。
- 不可做：比對失敗時不得自動 `--write` 覆蓋；不得以舊 producer 當長期正確性參考。
- 邊界：①首次凍結（檔不存在）⇒ 只有 `--write` 可建；②比對模式缺檔 ⇒ rc=1。
- 風險緩解：mutation `M-SU-8`。
- **驗證**：`venv/bin/python scripts/freeze_splitunify_golden.py` rc=0；
  手改 golden 內一個成員 ⇒ rc=1 且輸出含該成員 event_id（可證偽自證，同
  `scripts/freeze_evtlabel_survivor_golden.py` 之作法）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：B3 接線後 G-1 之值**預期改變** ⇒ 以 `--write` 重凍並在 commit 訊息逐項記錄
  差異來源；不得靜默覆蓋。

### Task 3.1 — 接線：邊界唯一化（`票 SPLITUNIFY`）
- SPEC ref：C-0、C-1　目標：兩端共用 boundary builder；`split_events` 退出生產呼叫圖。
- 輸入 / 輸出：canonical boundary ＋ `feature_index` → `EventSplitPlan`（投影）。
- 實作要點：
  1. `orchestrator._build_holdout_split_plan` 改由 `holdout_boundary` 取得列計畫。
  2. `pipeline.run` 簽名新增 canonical boundary 與 `feature_index`（選填）；
     給定 ⇒ 走投影；未給定 ⇒ 走 Task 3.3。
  3. `split_events` 保留為歷史路徑／G-3a 對照，生產呼叫點數釘為 **0**。
  4. 🔴 **事件 pipeline caller 呼叫投影前 assert**
     `config.split.embargo_ms is None and config.split.embargo_ms_by_symbol is None`
     （R3 之 E5＋R4 之 F3）。欄位層級是 `config.**split**.…`——v4 寫 `config.embargo_ms`
     會直接 `AttributeError`（`pipeline.py:31-45` 之 `EventPipelineConfig` 只有 `split`）。
     **只套事件 pipeline caller**，IC orchestrator 收 `ICConfig`，不得套。
- 修改檔案：`momentum/Analysis/event_samples/pipeline.py`、
  `momentum/Analysis/ic_filter_orchestrator.py`、`momentum/core/split_preview.py`。
  既有 caller：`ic_feed.py`、`tables.py`、`baseline.py`、`pattern_bridge.py`
  （皆為**成員消費者**，型別不變）。
- 不可做：不改投影函式簽名；不在 caller 端補算切分；
  🔴 **不刪任何既有 guard**（containment 未證明）。
- 邊界：①非事件 run 不走投影（G-2）；②缺 train 或 test plan ⇒ fail-closed。
- 風險緩解：G-2、G-5、mutation `M-SU-9`。
- **驗證**：三條命令皆 rc=0（`pytest` ×2 ＋ `freeze_evtlabel_survivor_golden.py` 之 sha256）——
  (A) `venv/bin/python -m pytest -q tests/momentum/Analysis tests/momentum/event_samples`
  逐條 `--deselect` `tests/baselines/analysis_known_failures.nodeids` 後 rc=0；
  (B) 🔴 **方向性**（R2 之 D9，**不是**集合相等）：實際 FAILED **⊆** 該清單，
  只准變短、變長判紅；變短時依 Task 1.3 維護協議同 PR 更新清單並具名；
  (C) `venv/bin/python scripts/freeze_evtlabel_survivor_golden.py`（G-2 之 sha256 未漂移）；
  (D) `venv/bin/python -m pytest -q tests/momentum/event_samples -k split_events_production_call_count`
  ——釘選生產路徑對 `split_events` 之呼叫次數 `== 0`（R2 之 D10：v2 只寫在本檔、SPEC 漏了，已補齊）；
  (E) `venv/bin/python -m pytest -q tests/momentum/event_samples -k embargo_must_be_none` rc=0（R3 之 E5）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：B4 只加 metadata 欄位，不改接線。

### Task 3.2 — 多 symbol fail-closed（`票 SPLITUNIFY`）
- SPEC ref：C-2　目標：per-symbol 投影未支援前，多 symbol 批一律 raise。
- 輸入 / 輸出：多 symbol 批 → `ValueError`。
- 實作要點：
  1. 批內 symbol 數 > 1 ⇒ `raise ValueError("multi_symbol_projection_unsupported: …")`。
  2. reason 字面自 `split_unify.json` 讀，不手打。
- 修改檔案：`momentum/Analysis/event_samples/split_projection.py`、
  `tests/momentum/Analysis/test_splitunify_derive.py`。既有 caller：無。
- 不可做：不得以警告放行；不得以第一個 symbol 之 plan 冒充整批
  （`ic_filter_orchestrator.py:1248` 之 `next(iter(allowed_symbols))` 形態）。
- 邊界：①單 symbol 批不受影響；②`symbol` 為 None ⇒ 視為單標的（既有語意）。
- 風險緩解：mutation `M-SU-2`、`M-SU-3`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k multi_symbol`
  rc=0：兩 symbol 批 ⇒ raise 且訊息含 `multi_symbol_projection_unsupported`；
  單 symbol 批 ⇒ 不 raise。
- **存活至**：per-symbol 投影實作後**改寫**為支援分支（SPEC §N R-1）。
- **覆蓋風險**：本 Task 之 raise 分支預期被未來的 per-symbol 支援取代——屆時須連測試一起改，
  不得只刪 raise。

### Task 3.3 — 無 canonical universe ⇒ 明示 event-study-only（`票 SPLITUNIFY`）
- SPEC ref：C-0 決議③　目標：拿不到 universe 時不得宣稱 OOS。
- 輸入 / 輸出：無 universe 之批 →
  `capability={"split":"unavailable","reason":"canonical_feature_universe_unavailable"}`。
- 實作要點：
  1. `case_import_service` 在無 feature universe 時走既有
     `run_event_study_only_with_params`；reason 字面自 `split_unify.json`。
     依 R2 之 D1 裁定，事件掃描端**恆走**此分支。
  2. 🔴 **刪除** `run_event_study_only` 現行寫死的 `n_train`／`n_test`／`n_purged`
     （`pipeline.py:728-734` 目前全寫 `0`）。既有 `lookahead_split_blocked`（L3）與新 reason
     **共用同一個新形狀**——不刪就與「不得出現這三鍵」直接矛盾（R2 之 D2）。
     前端 `EventTablesPanel.tsx:352` 今日對 L3 顯示「train 0／test 0／purge 0」，
     正是 C-0 要禁的假 OOS 數字。
  3. 🔴 `event_forward_return_table` 之 `common` 增 `estimand_scope="full_sample_not_oos"`
     （沿用 `pipeline.py:598-599` 之揭露欄位模式；欄位寫進 `tables.py:130-151` 之 `_common_constraint_block`，該區塊於 `:279` 掛上 `common`）。理由：該表在 `split_plan=None` 時
     **確實跑全 manifest 事件**（`tables.py:211-238`，無 `split_label=="test"` 過濾），
     只有 `ci` 與 `formal_pooled_inference_allowed` 被降級（R2 之 D4）。
  4. 🔴 前端事件掃描頁**必須**渲染 `capability.split` 與 `capability.reason`；
     `split == "unavailable"` 時**禁再顯示** train/test/purge 計數列。
     兩條 reason（`split_blocked_unverifiable_lookahead` vs
     `canonical_feature_universe_unavailable`）須有可分辨文案（R2 之 D5）。
  5. **沿用既有分派機制**，不新造第二套。
- 修改檔案：`api/services/case_import_service.py`、`momentum/Analysis/event_samples/pipeline.py`、
  `momentum/Analysis/event_samples/tables.py`、
  `frontend/src/components/ic-analysis/EventTablesPanel.tsx`、`frontend/src/components/ic-analysis/eventTablesPanelCapability.test.tsx`（**新**）、`frontend/src/lib/types.ts`。
  既有 caller：前端事件掃描頁（**本 Task 要改它**，不再是「型別不變」）。
- 不可做：不得以 `test_fraction` 自行切分後宣稱 OOS；不得填 0 冒充；
  不得只改後端 reason 而不改畫面。
- 邊界：①既有 `lookahead_split_blocked` 分派**路徑**不變，但其 summary 形狀**會一起改**；
  ②有 canonical universe 時行為不變（本票中事件掃描端不會有）。
- 風險緩解：mutation `M-SU-10`。
- **驗證**：`venv/bin/python -m pytest -q tests/api/test_splitunify_event_study_only.py` rc=0：
  `capability["split"] == "unavailable"` 且
  `capability["reason"] == "canonical_feature_universe_unavailable"`；
  **兩條 reason 皆** `assert "n_test" not in summary`（含既有 L3 之回歸）；
  `event_forward_return_table["common"]["estimand_scope"] == "full_sample_not_oos"`；
  `cd frontend && node_modules/.bin/vitest run src/components/ic-analysis/eventTablesPanelCapability.test.tsx`
  rc=0（兩條 reason 各一 mock payload，斷言文案不同且無 train/test/purge 計數列）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：per-symbol 支援（R-1）不影響本分支；`R-5` 若日後實作，
  只能新增「有 universe」的對照路徑，**不得**刪除本分支。

### Task 4.1 — 報告與前端只暴露一個驗證段（`票 SPLITUNIFY`）
- SPEC ref：C-6　目標：`metadata` 只寫 canonical `n_test` 與其來源揭露。
- 輸入 / 輸出：投影結果 → `metadata.split_unify = {n_test, split_authority, boundary_hash,
  per_symbol_counts, reason}`。
- 實作要點：
  1. `boundary_hash` ＝ canonical 測試段時間戳之 `sha256`（sorted、int64 ms、無空白 JSON）。
  2. fail-closed 時 `n_test` 為 `null` 而非 `0`（不顯示假數字）。
  3. 前端顯示單一數字＋來源標籤；`splitAuthority.test.ts` 對證值集。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py`、
  `frontend/src/lib/types.ts`、`frontend/src/components/ic-analysis/`。
  既有 caller：前端 IC 分析頁。
- 不可做：不同時暴露兩個驗證段數字；fail-closed 時不填 0 冒充。
- 邊界：①全域 run 不寫這些鍵（G-2）；②fail-closed ⇒ `n_test` 為 null。
- 風險緩解：mutation `M-SU-9`。
- **驗證**：`venv/bin/python -m pytest -q tests/api/test_splitunify_disclosure.py` rc=0：
  報告中含「驗證段列數」語意之鍵**恰 1 個**；`split_authority == "kline_holdout"`；
  `cd frontend && node_modules/.bin/vitest run src/lib/splitAuthority.test.ts` rc=0。
- **存活至**：全票完工後保留（UAT 交付物）。
- **覆蓋風險**：無後續 Phase。

---

## §C-9 Phase 9 Task 細目（`D-002` 延伸）

**裁定來源**：`handoffs/reconcile/20260911-splitunify-b9-consult-r2/synth.md`（三家 consult，本節 Task 9.1–9.5
之依賴序與驗收命令出自其裁定段；該收斂之「修訂標的」逐字即本檔 `docs/SPLITUNIFY_TODO.md`）。
SPEC 權威＝`docs/SPLITUNIFY_SPEC.D-002.md` §P／§V／mutation 表，
**本節不複述 SPEC 條文**，只寫施工面與驗收命令。

🔴 **動工前置（缺任一即不得領 impl token）**：
1. `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0（三家 `RECONCILE-STAMP` APPROVED）。
2. 前批未 commit 生產碼已依裁定 `REVERT`——四檔 ＋ `handoffs/20260911-splitunify-b9-probe-multitf.py:47`
   之 tuple unpack 皆已還原至 HEAD（2026-09-13 已執行，驗收＝兩測試檔重跑無 failed）。
3. 🔴 **程序先例**：`AGENTS.md:40`（Rule 12「動工前若所依 reconcile/SPEC 的 `RECONCILE-STAMP` 未全數
   APPROVED → 不動工」）**適用於動工、不適用於唯讀審查輪**——同情境之既有裁定見
   `handoffs/reconcile/20260911-splitunify-b9-review-r4/synth.md` 之駁回段。本節動工受其約束。

🔴 **驗收命令之三條紀律**（本節逐 Task 遵守）：
- **逐檔明列路徑**，禁無路徑之 `pytest -k`（`-k` 只過濾執行、**不減少收集** ⇒ 會從 rootdir 收全套，小時級）。
- **禁聚合期望數**（不得寫「應 N passed」「failed <= N」）；寫**具名測試函式名**與 mutation 轉紅判準。
- 既有紅**逐條** `--deselect`（`tests/baselines/analysis_known_failures.nodeids`）。

---

### Task 9.1 — 丟棄列數之完整資料流契約（`票 SPLITUNIFY`）
- SPEC ref：§P Phase 9A `Task 9.1`；§V `Task 9.1`；`D-002-C0` (0.6)
- 目標：消除「靜默丟棄」之誠實性缺陷，**交付至 producer → `EventSplitPlan.summary` 兩層**。
- 輸入 / 輸出：`build_event_keys(receipts, *, selected_timeframe=None)`
  → `(keyed: pd.DataFrame, discarded: Dict[str, int])`。
  🔴 `discarded` 無丟棄時為 `{}`，**不得**省略、不得回 `None`。
- 實作要點：
  1. `build_event_keys` 改為回傳 tuple；`discarded` 鍵＝被丟棄之 **feature** TF 字面、值＝列數。
  2. `_derive_single_symbol` 新增 keyword-only 參數 `discarded_rows_by_feature_tf`，**原樣**寫入
     `EventSplitPlan.summary["discarded_rows_by_feature_tf"]`（🔴 鍵名依 `D-002-C0` (0.6) 不得含裸 `timeframe`）。
     🔴 **多 symbol 分派器：原樣傳遞，不得相加**（R18 `CODEX-R18-P2-01` 裁定；三家撞題）。
     原條文寫「逐 symbol **相加**（同鍵值相加，非後者覆蓋前者）」，與實際呼叫圖**互斥**——
     `build_event_keys` 對整批 `receipts.per_tf` **只呼叫一次**（`pipeline.py` 單一呼叫點），
     `discarded` 是**批次級**字典、**不存在逐 symbol 分量**；照字面相加會把同一批計數
     按 symbol **重複放大**（兩 symbol 即兩倍）。⇒ 分派器**原樣傳遞**，並以
     `test_multi_symbol_branch_carries_discarded_rows_verbatim` 之值相等斷言鎖住
     （該測試另含防放大斷言：值被乘倍即紅）。
  3. 🔴 **`metadata.split_unify` 層不在本 Task 交付面**——依 v13 之 O1 已整段移入 §N `SU-RESID-9A-UI`。
     **不得**在本 Task 改 `build_split_unify_disclosure` 五鍵、`momentum/Analysis/contracts/split_unify.json`
     之 `split_unify_keys`、或 `tests/api/test_splitunify_disclosure.py` 之 exact-key 斷言。
  4. 獨立回退：移除 (1)(2) 後行為須與 9A 前**逐值**相同 ⇒ 須有一條可證偽測試，不是註解宣稱。
- 修改檔案：`momentum/Analysis/event_samples/split_projection.py`；
  既有 caller `momentum/Analysis/event_samples/pipeline.py`（簽章改 tuple 後**必須**同批改，否則 unpack 失敗）。
- 不可做：不得以揭露取代複合鍵；不得在丟棄時 raise（會擋掉目前合法的單 feature TF 用法）；
  不得為了讓 9A 有終端揭露面而新增 API。
- 邊界：①`per_tf` 只有一個 TF 且 `selected_timeframe=None` ⇒ `discarded == {}`；
  ②`selected_timeframe` 指定之 TF 不存在 ⇒ 維持現行 `ValueError`（不得改成回空表）。
- 風險緩解：mutation `M-SU-D2-01`、`M-SU-D2-02`。🔴 `M-SU-D2-03` 屬 metadata 層、**隨殘留延後**，
  本 Task **不得**宣稱其已閉。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` rc=0，且須含下列具名測試皆 pass：
  - `test_build_event_keys_discarded_counts_dropped_feature_tf`（`per_tf` 含兩個 feature TF、`selected` 取其一
    ⇒ `discarded` 之值等於 fixture 中另一 TF 之**實際列數**，由 fixture 逐筆算出，**不得寫死常數**）
  - `test_build_event_keys_discarded_empty_when_single_feature_tf`
  - `test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer`（**值相等**，非只驗鍵存在）
  - `test_discarded_layer_is_independently_revertible`（移除該欄後 summary 其餘鍵逐值不變）
  - 🔴 **R18 補三條（缺任一條即有可靜默失效的面）**：
    - `tests/momentum/event_samples/test_splitunify_wiring.py::test_splitunify_wiring_discarded_rows_reaches_summary`
      ——掛在 `EventSamplePipeline.run` 之**生產**呼叫點；上列四條全在 `derive_*` 層，
      caller 若省略 `discarded_rows_by_feature_tf=` 它們**全部仍綠**（`CODEX-R18-P1-01`）。
    - `test_multi_symbol_branch_carries_discarded_rows_verbatim`——多 symbol（Mapping）分支之
      值相等＋防放大（`COMPOSER-R18-P2-01`／`GROK-R18-P2-01`）。
    - `test_build_event_keys_rejects_nan_timeframe_in_dropped_rows`——被丟棄列之 `timeframe`
      為缺值時 fail-closed，不得記成名為 `nan` 的假 TF（`CODEX-R18-P1-03`／`GROK-R18-P1-01`）。
  mutation 自證（實跑並貼 rc）：
  - `M-SU-D2-01`：刪掉寫入 summary 那行 ⇒ 第 3 條轉紅
  - `M-SU-D2-02`：producer 回傳 `discarded` 但 `_derive_single_symbol` 改傳 `{}` ⇒ 第 3 條轉紅
  - **生產接線**：`pipeline.py` 省略 `discarded_rows_by_feature_tf=` ⇒ wiring 那條轉紅
  - **多 symbol 分支**：分派器改傳 `{}` ⇒ 多 symbol 那條轉紅
- **存活至**：全票完工後保留。
- **覆蓋風險**：`Task 9.2` 會再改 `selected_timeframe` 之預設值；本 Task 只改回傳形狀，兩者不衝突。

---

### Task 9.2 — producer 停止單選，輸出全量 keyed rows（`票 SPLITUNIFY`）
- SPEC ref：§P Phase 9B `Task 9.2`；§V `Task 9.2`
- 🔴 **本 Task 是第 9 批核心**；沒有它，下游全改完 `SU-RESID-2` 仍不會解決。
- 實作要點（四層，缺任一層本 Task 白做）：
  1. **producer**：`selected_timeframe` 由必填改為 `Optional[str] = None`；`None` ⇒ 全量。
  2. **caller**：`pipeline.py` 之 `build_event_keys(receipts, selected_timeframe=str(selected_timeframe))`
     🔴 **一併移除 `str()` 強制轉型**——留著會把 `None` 變字面 `"None"`，產空表而非全量。
  3. **投影門檻**：`projection_args` 由四鍵改三鍵（`train_plan`／`test_plan`／`feature_index`），
     `selected_timeframe` 移出必填集合；`pipeline.py` docstring 之「四者同時」同步改寫。
  4. **merge 與輸出欄**：改以 `per_tf` 為行粒度與 `event_level` 接合，`validate` 由 `1:1` 改為複合鍵語意；
     🔴 **新建**輸出欄 `feature_timeframe` 取自 `per_tf.timeframe`，**不得**以 `event_level.timeframe`（觸發 TF）冒充。
  5. `split_projection.py` 之 `build_event_keys` docstring 舊語意「每事件恰一列」須一併改寫。
- 修改檔案：`momentum/Analysis/event_samples/split_projection.py`、`momentum/Analysis/event_samples/pipeline.py`。
- 不可做：不得保留「預設只取一個 TF」之行為；不得在 producer 內靜默丟列。
- 邊界：①`per_tf` 只有一個 feature TF ⇒ 全量輸出與單選輸出列數相同（非退化，須有測試釘住）；
  ②`selected_timeframe` 給字串且該 TF 不存在 ⇒ 維持 `ValueError`；
  ③`event_level` 自身 `event_id` 重複 ⇒ `many_to_one` 仍須擋下（放寬 `validate` 不得順手放掉這一面）。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/event_samples/test_splitunify_wiring.py tests/momentum/Analysis/test_splitunify_derive.py` rc=0（🔴 **端到端，schema 斷言不算**；斷言標的逐字為 `split_plan.assignments`，不是 `features`），須含：
  - `test_run_without_selected_timeframe_emits_all_feature_tf_rows`（經 `EventSamplePipeline.run` 不傳
    `selected_timeframe` ⇒ `len(assignments) == len(per_tf)` 且兩個 feature TF 皆在）
  - `test_partial_boundary_gate_accepts_none_selected_timeframe`
    （🔴 **替換**既有把 `selected_timeframe=None` 視為必 raise 之參數化案例，**不得**只新增而留著舊的）
  - `test_feature_timeframe_column_sourced_from_per_tf_not_event_level`（同事件兩列須為**不同** TF 值）
  mutation 自證：`M-SU-D2-20`（保留預設單選 ⇒ 第 1 條紅）、`M-SU-D2-21`（門檻改回四鍵 ⇒ 第 2 條紅）、
  `M-SU-D2-23`（`validate="1:1"` ⇒ 第 1 條紅，`MergeError`）、`M-SU-D2-26`（冒充 ⇒ 第 3 條紅）。
- **存活至**：全票完工後保留（唯一 producer 實作）。
- **覆蓋風險**：`Task 9.2a` 會在同一函式再加 `feature_timeframe` 之唯一性 guard、`Task 9.2b` 會改其下游判側；
  兩者**只增不改**本 Task 之簽章與門檻，若日後有人把門檻改回四鍵即 `M-SU-D2-21` 轉紅。

---

### Task 9.2a — schema 加 `feature_timeframe`（`票 SPLITUNIFY`）
- SPEC ref：§P Phase 9B `Task 9.2a`；§V `Task 9.2a`、`D-002-C3` purge 面
- 實作要點：
  1. `assignments`／`purged` 兩表各加 `feature_timeframe` 欄；`receipts.per_tf` **不改形狀**。
  2. 🔴 `build_time_clusters` 之 `clusters` **不加該欄、維持事件級**（簇由 `label_start_ms`／`label_end_ms` 決定）。
  3. 兩道既有 guard 之判準改為 `(event_id, feature_timeframe)` 複合鍵唯一；**錯誤型別維持現狀**。
  4. 🔴 **先後**：複合鍵唯一 guard 必須在 `D-002-C3` 同側檢查**之前**執行。
  5. `summary` 依 `D-002-C6` 同時提供 `n_events` 與 `n_event_tf_rows`；purge 面另提供 `n_event_tf_rows_purged`。
- 🔴 **既有兩條紅測試之處置（consult-r2 已裁定，直接照做，不得再自行改判）**：
  - `test_duplicate_event_id_is_fail_closed`＝**測試過時**。行為仍 fail-closed，只是訊息由「event_id 重複」
    改為「複合鍵重複」；授權＝§V／`Task 9.2a` 現行條文。改法＝更新該測試之 `match=` 字面，**不得**改實作。
  - `test_multi_feature_tf_opposite_sides_must_fail_closed`＝**三重問題**，非二選一：
    ①`_manifest(keys)` 把兩列同 `event_id` 寫進事件級 `manifest.table`（fixture 錯，本 Task 修）；
    ②`(3.2)` 異側 `AlignmentViolationError` 碼上不存在（屬 `Task 9.2b`）；
    ③判側仍 `feature_cutoff_ms`（屬 `Task 9.2b`）。
    ⇒ 本 Task **只**修 ①，該測試在 `Task 9.2b` 完成前**預期仍紅**，須以 `xfail(strict=True)` 明示、
    不得 `--deselect` 藏起來。
    🔴 **機械驗收（缺此則刪掉該測試也不會紅）**：node id 逐字為
    `tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed`；
    驗收命令須**逐字指定該 node id**（見下方 §驗證第 6 條），且輸出須為 `xfailed`——
    `passed`（＝XPASS，`strict=True` 下會轉 fail）與 `no tests ran`（＝被刪或被改名）皆判**不通過**。
- 不可做：不得把 `clusters` 複製成多列（`w=1/n` 權重、簇計數與 golden 語意會失去定義）；
  不得為了統一而改兩道 guard 之**錯誤型別**（前端與既有測試有依賴）；
  不得把 `test_multi_feature_tf_opposite_sides_must_fail_closed` 用 `--deselect` 藏起來換綠。
- 邊界：①單 feature TF 時複合鍵退化為 `event_id`，兩道 guard 行為須與改前**逐值相同**；
  ②`assignments` 為空時 `duplicated(subset=...)` 不得拋錯；
  ③`purged` 為空時 `n_event_tf_rows_purged == 0`（不是缺鍵）。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` rc=0，須含：
  - `test_assignments_composite_key_unique`
  - `test_purged_composite_key_unique`
  - `test_summary_has_n_events_and_n_event_tf_rows`
  - `test_duplicate_composite_key_error_message_names_key_not_side`（鍵重複時訊息須指鍵重複，**不得**誤報異側）
  - `test_clusters_remain_event_level_when_multi_feature_tf`
  - 🔴 第 6 條（xfail 機械驗收，**逐字**）：
    `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"`
    ⇒ 輸出須含 `1 xfailed`；出現 `1 passed`（XPASS）或 `no tests ran`（被刪／改名）即**不通過**。
  mutation 自證：`M-SU-D2-25`（同側檢查移到複合鍵 guard 之前 ⇒ 第 4 條紅）；
  `M-SU-D2-35`（`assignments` 組裝不寫 `feature_timeframe` 欄）；
  `M-SU-D2-36`（`purged` 組裝不寫該欄）。
  🔴 **v15 強化（R14 codex／grok 撞題）**：上列兩條之應紅測試**不得**只靠 `duplicated(subset=[...])` 的 `KeyError`——
  實作者若寫成 `if "feature_timeframe" in df.columns` 軟包，欄缺就靜默略過而不紅。
  兩個測試各須**先** `assert "feature_timeframe" in <表>.columns`、**再**做複合鍵唯一性斷言；
  且 fixture 須為**多 feature TF**。驗收時「刪欄」與「以 `in df.columns` 包住 guard」**兩種破壞都要實跑轉紅**。
  🔴 兩者為 v14 新增——`C5-20`／`C5-21` 原本分別指向 `M-SU-D2-20`／`M-SU-D2-24`，而那兩條破壞的是
  producer 預設與答案窗判定，**不是欄位本身**（R13 `CODEX-R13-P1-01` 提 `C5-20`，`C5-21` 由主委同型自查補上）。
- **存活至**：全票完工後保留（複合鍵 schema 為 Phase 9 之最終形態）。
- **覆蓋風險**：`Task 9.2b` 會在本 Task 之 guard **之後**插入同側檢查與跨表互斥；插入位置若被調到 guard 之前
  即 `M-SU-D2-25` 轉紅。`Task 9.4` 會讀本 Task 新增之 `n_event_tf_rows*`，不改其定義。

---

### Task 9.2b — 側別判定改為事件級錨定（`票 SPLITUNIFY`）
- SPEC ref：§P Phase 9B `Task 9.2b`；§V `Task 9.2b` 及其前置；`D-002-C3` (3.1)(3.2)
- 實作要點：
  1. **前置（步驟 0）**：`train_rows`／`test_rows` 皆非空、row set 不重疊；
     🔴 `validate_split_pair_integrity` 由 **`EventSamplePipeline.run`**（具名，非泛稱「producer／adapter 層」）
     在呼叫 `derive_event_split_from_plans` **之前**呼叫：以 `feature_index` 時刻序列作 `ts`、
     `train_plan.symbol` 廣播成等長陣列作 `symbols`（單標的）；多標的由呼叫端提供 full `symbols`。缺驗即 fail-closed。
     投影端維持**只讀** `row_index_local`，**不得**索引 `row_index`（`D-001-C2` (4.10)）。
     `index_ms[0] <= decision_at_ms <= index_ms[-1]`，任一不滿足即 raise（訊息含 `event_id`）。
  2. **三段式判準**（順序不得調換，且**不得**寫成第四條界外分支）：
     `decision_at_ms <= train_last_ms` ⇒ train；`>= test_start_ms` ⇒ test；介於兩者之間 ⇒ `purged`。
     `train_last_ms = int(index_ms[train_rows[-1]])`（新增）、`test_start_ms = int(index_ms[test_rows[0]])`（現有）。
  3. 側別判完**廣播**到該 `event_id` 之所有 feature TF 列；`feature_cutoff_ms` **不參與** `split_label`。
  4. 答案窗 purge 按**事件側**一次決定並廣播（不再逐列 `in_train`）。
  5. `(3.2)` fail-closed：複合鍵唯一 guard **之後**、寫入 `assignments` **之前**，按 `event_id` 分組檢查
     `split_label` 唯一 ⇒ 異側即 `raise AlignmentViolationError`（訊息含 `event_id`）。
  6. 🔴 **跨表互斥**：`purged` 無 `split_label` ⇒ 分組檢查結構上抓不到混態。須另斷言
     `set(purged["event_id"]) & set(assignments["event_id"]) == ∅`，違反即 `AlignmentViolationError`。
     **不得**以擴充 `split_label` 值域替代。
- 前置工作：`scripts/freeze_splitunify_golden.py` 之 fixture 須**先**新增
  `decision_at_ms != feature_cutoff_ms` 之單 TF 邊界事件（否則 (G-4d)②③ 為空心通過）。
- 不可做：不得保留任何以 `feature_cutoff_ms` 決定 `split_label` 的分支；
  不得把界外 raise 寫成第四條分類分支（寫成分支即恢復重疊，越界事件可被合法分到 train／test）；
  不得在 `(3.2)` fail-closed 上線前保留 per-cutoff 判側（否則合法多 TF 輸入會開始 raise）；
  不得在 `derive_event_split_from_plans` 內呼叫 `validate_split_pair_integrity`（座標系不符，見 `D-001-C2` (4.10)）。
- 邊界：①事件落在隔離帶 ⇒ `purged`，**合法且預期**，不得 raise
  （`scripts/freeze_splitunify_golden.py` 之 `gap1`／`gap2` 在 golden 之 `g1_membership.purged` 中）；
  ②`decision_at_ms == train_last_ms` ⇒ train（邊界取閉區間）；`== test_start_ms` ⇒ test；
  ③單 feature TF 時廣播退化為一列，行為須與改前逐值相同。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/Analysis/test_splitunify_golden.py` rc=0，須含：
  - `test_event_level_anchor_broadcasts_side_to_all_feature_tf`
  - `test_gap_band_event_is_purged_not_train`
  - `test_decision_before_index_start_raises` ／ `test_decision_after_index_end_raises`
  - `test_opposite_sides_raise_alignment_violation`（須一併驗**不是**靜默取一側、**不是**改判 purged）
  - `test_purged_and_assignments_event_id_disjoint`
  - `test_coordinate_truth_table_four_cases`（全域+全域 不 raise／全域+局部 `IndexError`／
    局部+局部 不 raise／局部+全域 `CrossSymbolLeakageError`）
  - `test_derive_never_indexes_row_index`（對 `derive_event_split_from_plans` 原始碼做 AST／字面掃描）
  - `test_multi_feature_tf_opposite_sides_must_fail_closed` 之 `xfail(strict=True)` **於本 Task 解除**
  mutation 自證：`M-SU-D2-14`／`M-SU-D2-15`／`M-SU-D2-22`／`M-SU-D2-24`／`M-SU-D2-30`。
- **存活至**：全票完工後保留（事件級錨定為 `(3.1)` 之唯一落地處）。
- **覆蓋風險**：`Task 9.5` 會以 golden 把本 Task 之側別結果凍結；若本 Task 之判準日後被改，
  golden 之 `g1_membership_v9`／`g3b_oracle_v9` 會同時轉紅（`M-SU-D2-27`／`M-SU-D2-28` 即覆蓋此面）。

---

### Task 9.3 — 消費面逐處列名改法（`票 SPLITUNIFY`）
- SPEC ref：§P Phase 9B `Task 9.3`；`D-002-C5` (5.1)(5.6) register
- 🔴 **動工前置（consult-r2 之 A6；stamp-r1 codex 要求機械化）**：先重掃 `D-002-C5` register，逐條複驗
  `C5-01`..`C5-29` 因 `feature_timeframe` 欄而是否改變分類（甲／乙／丙）。
  **產出物為必要條件，不是筆記**：重掃結果須寫成
  `handoffs/run_receipts/<UTC時戳>-splitunify-task-9.3-register-rescan.txt`，內容逐條為
  `C5-NN <改前分類> -> <改後分類> <碼證 path:line>`，且**檔案存在**列入下方驗收；
  缺檔即本 Task 不得宣告完成（沒有這一條，省略重掃在現行檔案級 rc=0 下完全看不出來）。
- 🔴 **不得**用「凡 `set_index("event_id")` 一律改」這種形狀規則。逐處處置如下，
  **多數是「維持現狀 ＋ 加防誤改回歸測試」，不是改碼**：

| 消費面 | 處置 | 應紅之 mutation | 測試檔 |
|---|---|---|---|
| `feature_materialization` | **維持事件級橫向合併**（不得改複合鍵） | `M-SU-D2-04` | `tests/momentum/event_samples/test_feature_materialization.py` |
| `tables` | 維持事件級 `.loc[eid]`（`:214`／`:229`／`:373`）；🔴 另 **`tables.py:372` 之 `assignments.set_index("event_id")["symbol"].reindex(idx)` 要改**——🔴 **v16 更正（實跑 pandas）**：重複索引下 `reindex` 會直接 `ValueError: cannot reindex on an axis with duplicate labels`，**不是**靜默取錯值（v15 原文寫「靜默取錯 symbol」是錯的）⇒ 須加顯式去重 reducer：同 `event_id` 之 `symbol` 相同則取該值、衝突則 fail-closed raise | `M-SU-D2-06`（維持面）＋`M-SU-D2-40`（移除 `:372` 之去重 reducer） | `tests/momentum/event_samples/test_tables.py`，須**成對**兩條：同值去重成功取到正確值／衝突值 fail-closed raise |
| `ic_feed` | 維持六鍵事件級（不加 TF 欄）；🔴 另 **`event_context_from_windows` 之餵入須先按 `event_id` 去重**——🔴 **v16 更正（實讀 `ic_feed.py:109`）**：v15 原寫「多 TF 下重複三元組」**不可達**（該處以 `per_tf["timeframe"] == timeframe` 單一 TF 過濾，且 `WindowRow` 只有事件級欄位）⇒ 可達 seam 是 `event_context_from_windows` **本身**：餵入含重複 `event_id` 之 windows 會使 `event_manifest_hash` 漂移 | `M-SU-D2-07`、`M-SU-D2-19`（維持面）＋`M-SU-D2-38`（餵入未去重） | `tests/momentum/event_samples/test_gap3_conditional_ic.py`（`ic_feed` 無專屬測試檔）；測試須**直接呼叫** `event_context_from_windows` 驗雜湊不變性 |
| `counterexample_classifier` | 維持事件級 | `M-SU-D2-08` | `tests/momentum/event_samples/test_counterexample_classifier.py` |
| `candidate_ledger` | 維持事件級 | `M-SU-D2-09` | `tests/momentum/event_samples/test_candidate_ledger.py` |
| `dedupe` | 保留集事件級決定 ＋ 廣播到該事件所有 per-TF 列 | `M-SU-D2-10` | `tests/momentum/event_samples/test_dedupe.py` |
| `pattern_bridge` | **丙類，要改**：`assign.set_index("event_id")` 先去重取唯一側，不唯一即 fail-closed | `M-SU-D2-05`（改複合鍵索引）＋`M-SU-D2-37`（略過去重／不 fail-closed） | `tests/momentum/event_samples/test_pattern_bridge.py` |
| event-level 表／manifest | 粒度不變 | `M-SU-D2-18` | `tests/momentum/Analysis/test_splitunify_derive.py` |
| 前端 `byEventId` | 維持 `canonicalEventId` 鍵 | `M-SU-D2-11` | 🔴 **須新建** `frontend/src/app/search/eventExportByEventId.test.tsx`（同目錄已有四支 `eventExport*.test.tsx` 可循） |

- 不可做：不得用形狀規則（凡 `set_index("event_id")` 一律改）批次套用；
  不得把 event-level 表複製成多列以「配合」複合鍵；
  不得把 `M-SU-D2-11` 之前端面以「等 UAT 再做」延後——它是本 Task 的交付面之一。
- 邊界：①單 feature TF 批下，上表九處行為須與改前**逐值相同**；
  ②`pattern_bridge` 去重後若同一 `event_id` 出現兩個不同 `split_label` ⇒ fail-closed raise，
  不得靜默取第一個；③前端 `byEventId` 在 `feature_timeframe` 存在時仍以 `canonicalEventId` 建鍵，
  匯出附帶欄位不得變空。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/event_samples/test_feature_materialization.py tests/momentum/event_samples/test_tables.py tests/momentum/event_samples/test_gap3_conditional_ic.py tests/momentum/event_samples/test_counterexample_classifier.py tests/momentum/event_samples/test_candidate_ledger.py tests/momentum/event_samples/test_dedupe.py tests/momentum/event_samples/test_pattern_bridge.py tests/momentum/Analysis/test_splitunify_derive.py` rc=0；
  前端 `cd frontend && node_modules/.bin/vitest run src/app/search/eventExportByEventId.test.tsx` rc=0。
  上表每列各一條「改壞就變紅」測試；🔴 靜默面須斷言取到的**值**正確，不得只斷言「不報錯」。
  🔴 **register 重掃 receipt 之機械驗收（逐字；R13 `CODEX-R13-P1-02` 指出「只比行數」可被「同一 ID 重複 29 次」繞過，故改為 exact ID set ＋ 當輪綁定）**：
  1. **唯一且當輪**：receipt 檔名須為 `handoffs/run_receipts/<UTC時戳>-splitunify-task-9.3-register-rescan.txt`，
     且其**首行**逐字為 `TASK: <本 Task 之 impl task-id>`、**次行**逐字為 `COMMIT: <本 Task 開工時的 HEAD sha>`。
     🔴 **v15 強化（R14 三家撞題：`COMMIT: deadbeef` 也能過）**：`COMMIT:` 之值須**等於**該 impl task-id 之
     `committee_dispatch`／impl token 事件在 `.claude/gate/audit.log` 中所記的 round-start HEAD；
     驗收命令須實際取出該欄比對，不得只檢查「有這一行」。
  2. **exact ID set，不是計數**：
     `sed -n '3,$p' <receipt> | grep -oE '^C5-[0-9]+' | sort -u` 之輸出，須**逐字等於**
     `grep -oE '^\| .C5-[0-9]+.' docs/SPLITUNIFY_SPEC.D-002.md | grep -oE 'C5-[0-9]+' | sort -u`
     （`diff <(…) <(…)` rc=0）。🔴 **不得**改用 `wc -l` 比數量——同一 ID 重複 29 次也會過。
  3. 每列格式逐字為 `C5-NN <改前分類> -> <改後分類> <碼證 path:line>`；分類值域封閉為 `甲|乙|丙`。
  4. 🔴 **v15 強化（R14 三家撞題：ID 集合正確但分類全填 `甲 -> 甲`、碼證填占位路徑也能過）**——再加兩條內容對證：
     - **改前分類須與 SPEC 現況相符**：逐列取該 `C5-NN` 在 `docs/SPLITUNIFY_SPEC.D-002.md` register 表中的第 3 欄，
       須**逐字等於** receipt 的 `<改前分類>`。任一列不符即 FAIL（這一條直接殺掉「全填同一值」）。
     - **碼證須指向真實存在的行**：逐列把 `<碼證 path:line>` 拆成檔與行號，該檔須存在、且行號須 ≤ 該檔總行數。
       任一列指向不存在的檔或超出範圍的行即 FAIL（這一條殺掉占位路徑）。
     - 🔴 **v16 之 keyed 對證已於 v17 收窄（R16 `CODEX-R16-P1-01`；主委實測確認其碼證成立）**：
       v16 寫「碼證檔路徑須與 register 同列所載之落點檔相同」，但**實測 29 列中有 20 列的消費面欄
       根本沒有 `path:line`**（`C5-01`..`08`／`09`..`12`／`15`..`18`／`20`／`22`／`24`／`25`）
       ⇒ 該檢查在 **69% 的列上不可執行**，屬**假閘**（寫了跑不動，比沒有更糟）。
       **現行（可執行）判準——三段式，29 列逐列歸屬且互斥窮盡（r17 三家獨立算出之 15 列與主委機械掃描完全一致）**：
       - **(甲) 有 `path:line` 之 10 列**（`C5-13`／`14`／`19`／`21`／`23`／`25`／`26`／`27`／`28`／`29`）：
         碼證之檔路徑須與該列所載落點檔**相同**、行號須落在該列所列範圍內。
       - **(乙) 有檔名但無行號之 4 列**——逐字為 `C5-15`／`C5-16`／`C5-17`／`C5-18`（🔴 v18 具名，
         由 `CODEX-R2-P2-01` 必答 2b 給出；原只寫「29 − 10 − 15」之算式）：`<碼證 path:line>` 之**檔名（basename）**須出現在
         該列消費面欄的文字中（封閉判準：`basename` 之字面 `grep -qF` 該列文字）。仍禁止任意真實路徑。
       - 🔴 **(丙) 消費面欄完全沒有任何檔名之 15 列**——逐字為
         `C5-01`／`C5-02`／`C5-03`／`C5-04`／`C5-05`／`C5-06`／`C5-07`／`C5-08`／`C5-09`／`C5-10`／`C5-11`／`C5-12`／`C5-20`／`C5-22`／`C5-24`
         ——**明文排除於碼證對證之外**，該欄改填 `NO-ANCHOR`（封閉字面）。
         **為何要明文排除而不是硬套 basename**（r17 三家撞題，codex／composer／grok 各自獨立算出同一組 15 列）：
         這 15 列的消費面欄只有模組名或中文敘述，basename 判準在其上**無從執行** ⇒ 硬套的結果只有兩種，
         **要嘛驗收永久紅，要嘛實作者靜默跳過檢查而造成假綠**——兩者都比明文排除更糟。
         🔴 排除**不等於**免驗：這 15 列的重掃結論仍須逐列寫在 receipt（分類欄照常對證 SPEC 現況），
         只是**碼證欄**不參與對證；其精確錨點歸 `SU-RESID-C5-TARGETS` 殘留。
       🔴 **具名殘留 `SU-RESID-C5-TARGETS`**（理由類別 **`blocked-by`**）：要讓全 29 列都走精確
       keyed 對證，須先為**缺精確 `path:line` 之 19 列**（＝29 − keyed 10；含 (乙) 4 列與 (丙) 15 列）
       補 `TARGETS: <repo-relative-path>:<start>-<end>` 欄位（🔴 v18 更正：原寫「那 20 列」，
       係 `C5-25` 補錨前之舊值，由 `CODEX-R2-P2-01` 抓出）
       （codex 於 `CODEX-R16-P1-01` 給出逐字修法，並指出 `C5-25` 至少應錨
       `momentum/Analysis/event_samples/ic_feed.py:56-65`）。**現在不做的理由**：那要動 20 列已戳記
       之 register 並再走一輪三家重簽，屬「為驗收收據的閘再補一層腳手架」，而 `Task 9.1`
       之產品實作尚未開始；依 2026-09-12「不再擴建治理工具、同型缺陷降級為具名殘留」裁定，
       **降級為本殘留**。
       🔴 **觸發條件（v18 改寫為可執行；r17 三家撞題指出前版之「basename 判準出現誤判」無人、無時、無命令可判，等於無限期擱置）**——
       改為**兩條客觀事件，任一成立即升級**，判定人＝`Task 9.3` 之實作者，判定時機＝該 Task 驗收當下：
       1. `awk -F'|' '/^\| \`C5-[0-9]+\`/ { if ($3 !~ /[A-Za-z0-9_]+\.(py|ts|tsx|json)/) n++ } END {print n}' docs/SPLITUNIFY_SPEC.D-002.md`
          之輸出 **≠ 15**（代表 (丙) 組成員變動，排除清單已過期，必須重算並補錨）。
       2. `Task 9.3` 之 register 重掃**實際發現** (丙) 那 15 列中任一列的分類需改動
          （即該列並非「維持現狀」）——此時該列已有實質改動落點，**必須**在同一次變更把
          `TARGETS: <repo-relative-path>:<start>-<end>` 補進該 register 列。
       **owner**：SPLITUNIFY epic 主委。**誠實邊界**：在本殘留解除前，(丙) 那 15 列的 receipt 碼證欄
       **不受機械對證保護**，只靠分類欄對證 SPEC 現況——此為**已知且具名**之覆蓋缺口，不得宣稱已閉。
- 🔴 **在上表測試實際存在之前，不得宣稱 mutation 網已閉**（§V 逐字）。
- **存活至**：全票完工後保留（九處之防誤改回歸測試是唯一擋「未來有人用形狀規則批改」的東西）。
- **覆蓋風險**：`Task 9.4` 會改 `split_projection` 之計數段與 `baseline`，與本 Task 之消費面不同檔；
  兩者並行時須先 rebase。`Task 9.5` 之 golden 會覆蓋 `dedupe`／`clusters` 的期望值。

---

### Task 9.4 — 記帳與報告鏈（`票 SPLITUNIFY`）
- SPEC ref：§P Phase 9B `Task 9.4`；§V `Task 9.4`；`D-002-C6`
- 實作要點：
  1. `n_train`／`n_test`／`n_purged` 明確定為**事件數**；新增列數欄（`n_event_tf_rows*`）。
  2. 🔴 **事件數門檻路徑**：`split_projection.py` 之 `n_test`／`per_symbol_test_n`／`per_symbol_n`
     皆改以 `event_id` **去重**計數——否則 1 事件 × 2 TF 使 `n_test=2 ≥ tier_min=2` 而**靜默繞過**
     測試段事件數下限（命中 §RISK (d)）。
  3. `dict(zip(...))` 之單鍵映射改複合鍵映射。
  4. 🔴 **`baseline` 拆鍵**：舊鍵 `n_test` **刪除**（不得保留、不得當 alias），改輸出
     `n_test_events`（`unique(test_ids)`）與 `n_test_samples`（`len(idx)`）；回傳 dict 鍵集為 **exact 契約**。
  5. 🔴 `insufficient_events_in_test` **只修正計數**；終端可見性屬 `SU-RESID-9A-UI` 殘留，
     **不列入本批完成條件**。驗收時不得宣稱「樣本不足已能被使用者看到」。
- 修改檔案（🔴 已具名到檔:行）：
  - `momentum/Analysis/event_samples/split_projection.py`（計數段）
  - `momentum/Analysis/event_samples/baseline.py`（`n_test` 拆鍵）
  - 🔴 **前端型別：事件路徑現在沒有 typed `n_train` 欄，本 Task 不動 `frontend/src/lib/types.ts` 之既有介面。**
    碼證（stamp-r1 codex／grok 兩家撞題、主委複驗）：`types.ts:1582` 屬 `CPCVPathResult`、`:2257` 屬
    `MarginalICSection`，**兩者與事件批無關**；事件批之 `EventAnalyzeResponse`（`types.ts:3174`）之
    `summary` 為 `Record<string, unknown>`，**沒有欄位可改**。⇒ 若本 Task 決定要 typed 面，須**新增**
    事件摘要型別並在此具名；在那之前**不得**去改 `CPCVPathResult`／`MarginalICSection`（改了就是動錯介面）。
  - 前端顯示 `frontend/src/components/ic-analysis/EventTablesPanel.tsx:361`
  - 既有前端測試（改欄名即紅，須同批改）：`eventTableTooltips.test.tsx:27`、
    `eventTableTooltips.failclosed.test.tsx:30`、`eventTablesPanelByLabel.test.tsx:28`、
    `eventTablesPanelCapability.test.tsx:29,101`、`eventTablesHorizonWiring.test.tsx:24`、
    `gap3_event_tables.test.tsx:14`
  - `tests/momentum/event_samples/test_splitunify_wiring.py`（`dict(zip(...))` 映射）
  - 🔴 **API 端無獨立 model**：`grep -rn "n_train" api/ --include='*.py'` 對事件批 summary **零命中**
    （命中之 `lstm_task_service.py` 之 `n_train_samples` 屬 LSTM 路徑）⇒ summary 為 dict 直通、無 pydantic 欄位要改。
    **此為實查結論，非「未查」。**
- 不可做：不得保留 `baseline` 舊鍵 `n_test`、不得把它當任一新鍵之 alias；
  不得為了湊複合鍵列數而把特徵向量複製成多列（會產生重複或稀疏向量）；
  不得宣稱 `n_test_events` 與 `n_test_samples` 恆等（物化失敗 fixture 即反例）。
- 邊界：①無物化失敗時 `n_test_events == n_test_samples`，但仍須**兩鍵並存**；
  ②`tier_min_test_events` 之比較在去重後進行，1 事件 × 2 TF 不得被當成 2；
  ③前端收到舊回應（無新欄）時不得崩潰——顯示端須容忍缺鍵。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/event_samples/test_baseline_oracle.py tests/momentum/event_samples/test_metrics_glossary.py tests/momentum/event_samples/test_splitunify_wiring.py tests/momentum/Analysis/test_splitunify_derive.py` rc=0，須含：
  - `test_baseline_splits_n_test_into_events_and_samples`（**物化失敗 fixture**：test 含 `e1` 且物化
    `failures` 含 `e1` ⇒ `n_test_events=1` AND `n_test_samples=0`）
  - `test_baseline_dict_has_no_legacy_n_test_key`
  - `test_tier_min_test_events_counts_unique_event_ids`（1 事件 × 2 TF、`tier_min=2` ⇒ 仍判樣本不足）。
    🔴 **v16 補足（R15 `CODEX-R15-P1-03`）**：該測試須**另**斷言 `summary["per_symbol_n"]` 與
    `summary["per_symbol_test_n"]` 皆等於各自之 `event_id` 去重計數——只驗門檻的話，
    「只把 `per_symbol_n` 弄錯而保持門檻去重」仍會綠，`M-SU-D2-39` 等於半條無鑑別力。
  - `test_event_count_conservation`（`n_train+n_test+n_purged == n_events`，事件數非列數）
  前端 `cd frontend && npm run build` rc=0（型別改動同批驗）。
  mutation 自證：`M-SU-D2-13`、`M-SU-D2-31`、`M-SU-D2-32`、`M-SU-D2-12`、
  `M-SU-D2-39`（v15 新增：`per_symbol_n`／`tier_min_test_events` 未以 `event_id` 去重
  ⇒ `test_tier_min_test_events_counts_unique_event_ids` 轉紅）。
- **存活至**：全票完工後保留（`n_test_events`／`n_test_samples` 兩量分離為最終契約）。
- **覆蓋風險**：`SU-RESID-9A-UI` 殘留解除時會再加終端揭露欄，屬**只增不改**；
  本 Task 之鍵名與語意不得在那時被改寫。

---

### Task 9.5 — golden 與前端（`票 SPLITUNIFY`）
- SPEC ref：§P Phase 9B `Task 9.5`；§V `Task 9.5` 及第 6 條；§G (G-4d)(G-4e)
- 實作要點：
  1. `scripts/freeze_splitunify_golden.py` 之 `_plans()`／`_event_keys()`／`_build_actual()` 擴維，
     新增**交錯平行組**；`main()` 寫檔**只增鍵不覆蓋**（舊鍵＝§G 回歸錨）。
  2. 🔴 **(G-4e) 第三份判準**：`_event_keys()` 內**人手逐筆填入**字面 `expected_side` 欄，
     且**不得** import／呼叫投影、`_oracle_membership` 或兩者之共用 helper。
  3. 🔴 **v8 baseline 換錨（write-once ＋ 外部錨）**：
     - `tests/golden/splitunify/splitunify_golden.v8.json` 以 `O_EXCL` **write-once** 建立；已存在即 raise。
     - 同批寫 `splitunify_golden.v8.sha256`；`--write` 指向 `.v8.json` 即 raise。
     - 🔴 **同一次變更**必須把該檔 `sha256` 之 **64-hex 字面**寫入 `docs/SPLITUNIFY_SPEC.D-002.md` §V 第 6 條
       之逐字錨點行 `V8_BASELINE_SHA256=<64-hex>`，且該行**不得**由 `freeze_splitunify_golden.py` 改寫。
     - 主檔 `splitunify_golden.json` 既有 **11 個頂層鍵逐值不變**；新成員集只落在 `g1_membership_v9`／`g3b_oracle_v9`。
  4. 前端 `byEventId` Map **排除於複合鍵遷移之外**（見 `Task 9.3` 表末列）。
- 不可做：不得覆蓋 `splitunify_golden.json` 既有 11 個頂層鍵任一值；
  不得讓 `freeze_splitunify_golden.py` 產生或改寫 SPEC §V 之 `V8_BASELINE_SHA256=` 錨點行（helper 只讀）；
  不得以「比對後更新」取代 `O_EXCL` write-once；
  不得讓 (G-4e) 第三份判準 import／呼叫投影或 `_oracle_membership`（同一次錯誤解讀寫進三份會全綠）。
- 邊界：①`splitunify_golden.v8.json` 不存在時首次建立成功、其後任何一次再建即 raise；
  ②golden 比對失敗**不得**自動覆蓋（§0 全域規則）；
  ③交錯平行組與單標的組之 `g5` 各自穩定、互不影響。
- **驗證**：`venv/bin/python scripts/freeze_splitunify_golden.py` rc=0，再
  `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_golden.py` rc=0，須含：
  - `test_single_tf_golden_values_unchanged`
  - `test_interleaved_parallel_group_g5_differs_and_is_stable`
  - `test_v8_baseline_is_write_once`
  - `test_freeze_write_flag_refuses_v8_target`
  - `test_v8_sha256_matches_spec_anchor_line`（**外部錨**；🔴 只比旁檔 `.v8.sha256` 會綠，故此條不可省）
  - `test_spec_anchor_line_exists_and_is_64hex`
  - `test_freeze_script_does_not_write_spec_anchor`
  - `test_main_json_eleven_top_keys_unchanged`
  mutation 自證：`M-SU-D2-16`／`M-SU-D2-17`／`M-SU-D2-27`／`M-SU-D2-28`／`M-SU-D2-29`／`M-SU-D2-33`／`M-SU-D2-34`。
- 🔴 **錨點字面寫入前**，(G-4d)①(vi) 之外部錨 ASSERT 標為「凍結當下才生效」，**不得宣稱已閉合**。
- **存活至**：全票完工後保留（`splitunify_golden.v8.json` 與 §V 之 `V8_BASELINE_SHA256=` 錨點是回歸錨本體）。
- **覆蓋風險**：本 Task 是 Phase 9 最後一步，無後續 Phase 覆蓋；風險反向——
  任何日後改動 `Task 9.2b` 判準者都會使本 Task 之 golden 轉紅，那是**設計意圖**，不得以重凍 golden 消音。

---

## §D mutation 對照表（12 條；自證，每批收案前跑，紅只認 rc=1）

| ID | 改壞什麼 | 應紅之測試 | 所屬批 |
|---|---|---|---|
| `M-SU-1` | 投影二態化（purged 併入 `assignments`） | `test_splitunify_derive.py -k three_state` | B2 |
| `M-SU-2` | 多 symbol fail-closed 拿掉 | `test_splitunify_derive.py -k multi_symbol` | B3 |
| `M-SU-3` | 以第一個 symbol 之 plan 冒充整批 | `test_splitunify_derive.py -k multi_symbol` | B3 |
| `M-SU-4` | 成員改用 `time_bounds` 閉區間而非集合 | `test_splitunify_derive.py -k membership_set` | B2 |
| `M-SU-5` | 未匹配時間戳預設歸 `train`（非 purged） | `test_splitunify_derive.py -k unmatched_timestamp` | B2 |
| `M-SU-6` | 同時落兩態時靜默取 train | `test_splitunify_derive.py -k dual_membership` | B2 |
| `M-SU-7` | `clusters` 抄舊 plan 而非由 manifest 重算 | `test_splitunify_derive.py -k clusters` ＋ `test_tables.py` | B2 |
| `M-SU-8` | freeze 腳本比對失敗自動 `--write` | freeze 腳本自證（改一員仍須 rc=1） | B2 |
| `M-SU-9` | metadata 同時寫舊事件 `n_test` 與 canonical `n_test` | `test_splitunify_disclosure.py` | B4 |
| `M-SU-10` | 無 universe 時仍按事件數切並宣稱 OOS | `test_splitunify_event_study_only.py` | B3 |
| `M-SU-11` | boundary builder 之 rows 或 **ms** 任一不同源（含 `test_start_ms` 略過 purge） | `test_splitunify_boundary.py -k same_source` ＋ `-k ms_same_source` | B2a |
| `M-SU-12` | 事件 ms 與 feature index 單位未歸一（秒／毫秒混用） | `test_splitunify_derive.py -k unit_normalize` | B2 |
| `M-SU-13` | 拿掉第一段答案窗 purge（只留集合成員判定） | `test_splitunify_golden.py -k leakage_negative` ＋ `test_splitunify_derive.py -k answer_window` | B2b |
| `C0` | 只改註解（對照組） | 必須仍綠 | 全批 |

🔴 **B3 追加九條（接線之錯法不是「算錯」而是「接到別的地方去了」）**——腳本
`handoffs/20260911-splitunify-b3-mutate.py`，判定同上（紅只認 rc=1；`C0` 必綠）：

| ID | 改壞什麼 | 應紅之測試 |
|---|---|---|
| `M-SU-B3-1` | 給齊 canonical 邊界時仍走歷史 `split_events` | `test_splitunify_wiring.py -k canonical_boundary` |
| `M-SU-B3-2` | 只給一半邊界參數時不再擋（靜默退回歷史切分） | `test_splitunify_wiring.py -k partial_boundary` |
| `M-SU-B3-3` | 投影路徑不再檢查毫秒 embargo | `test_splitunify_wiring.py -k embargo_must_be_none` |
| `M-SU-B3-5` | service 走回 `run_with_params`（無 universe 仍切） | `test_splitunify_event_study_only.py -k production_call_count` |
| `M-SU-B3-6` | 兩條 capability reason 合一 | `test_splitunify_event_study_only.py -k capability_reason_is_no_universe` |
| `M-SU-B3-7` | `estimand_scope` 不再揭露 | `test_splitunify_event_study_only.py -k full_sample_estimand` |
| `M-SU-B3-8` | orchestrator 不走 canonical boundary builder | `test_holdout_test_row_index.py -k orchestrator_uses_this_function` |
| `M-SU-B3-9` | 畫面在 unavailable 時仍印 train／test／purge | vitest `eventTablesPanelCapability.test.tsx` |

（`M-SU-10` 之錨點落在 `pipeline.run_event_study_only` 的 summary 上，一併由該腳本跑。）

🔴 **B4 追加九條（揭露之錯法是「講錯」：同一個問題兩個答案，或把「沒得算」講成「算出來是零」）**——
腳本 `handoffs/20260911-splitunify-b4-mutate.py`：

| ID | 改壞什麼 | 應紅之測試 |
|---|---|---|
| `M-SU-9` | 同時暴露兩個驗證段事件數 | `test_splitunify_disclosure.py -k exactly_one_test_count_key` |
| `M-SU-B4-2` | fail-closed 時 `n_test` 填 0 而非 null | `-k fail_closed_is_null_not_zero` |
| `M-SU-B4-3` | `per_symbol_counts` 與 `n_test` 矛盾不再擋 | `-k contradicting_per_symbol_counts` |
| `M-SU-B4-4` | reason 不再對證契約封閉集合 | `-k unregistered_reason` |
| `M-SU-B4-5` | `boundary_hash` 不再排序 | `-k boundary_hash_is_order_insensitive` |
| `M-SU-B4-6` | `boundary_hash` 只吃筆數不吃時刻 | `-k boundary_hash_changes_with_membership` |
| `M-SU-B4-7` | 全域 run 也寫 `split_unify`（破 G-2） | `-k absent_on_global_run` |
| `M-SU-B4-8` | 前端把 null 顯示成 0 | vitest `splitAuthority.test.ts` |
| `M-SU-B4-9` | 前端值集改成手打第二份 | vitest `splitAuthority.test.ts` |

🔴 **實測記錄（Task 4.1 的關鍵事實）**：同一個 canonical 測試段裡 `ic_train_test_split.test_rows=335`、
`split_unify.n_test=13`——335 根 K 線、其中 13 根上有事件。**兩個數字都對，但只有一個是
「驗證段事件數」**。⇒ `test_segment_count_keys` 把它們分成兩種語意，測試釘的是
`0 < n_test <= test_rows`（事件是列的子集），**不是**硬要兩者相等。

---

## §E 具名殘留（每條帶「為何現在不做」，只准 blocked-by／user-ruling／needs-research）

| ID | 項目 | 理由類別 | 為何現在不做 |
|---|---|---|---|
| `R-1` | per-symbol 投影（讓多標的批能跑） | needs-research | `base_universe_hash` 在多標的下之唯一性語意未定；先 fail-closed 比先算錯好 |
| ~~`R-2`~~ **已關閉（2026-09-11）** | `baseline`／`tables`／`pattern_bridge` 之 OOS 數值變動量 | — | 🔴 **原本就不該是殘留**：SPEC C-9 把「改前後逐項差異」列為**驗收條件**，而阻塞它的 G-3a 遷移報告在 B2c 就已跑出（`only_in_new_test=['te0']`）。⇒ 以 `scripts/splitunify_c9_diff.py` 實跑，receipt `handoffs/run_receipts/splitunify-c9-diff.json`：**IC 端**四組參數（含真實規模 20352 列）列計畫**逐列相同**；**事件掃描端**差異全部是預期的降級揭露（`cluster_adjusted` 轉 False、`estimand_scope` 標全樣本、`reason` 標沒切分、CI 收斂為 `"unavailable"`）。🔴 **實跑同時挖出一個假數字並當場修掉**：沒切分時 `common.n_symbols` 從空 summary 取 ⇒ 單標的批寫成「**0 個標的**」，且 `degraded=[]` 與 `cluster_adjusted=False` 互相矛盾；改由 manifest 導出並共用 `_degraded_flags`，mutation `M-SU-B3-11`／`-12` 覆蓋 |
| `R-3` | UAT 項目更新 | user-ruling | 使用者已裁定 UAT 一律最後 |
| `R-4` | `extract_event_patterns` 無 **production** caller（測試 caller 8 處） | blocked-by | 本票只保證其消費之 `assignments` 語意不變；接線屬另一票 |
| `R-5` | 事件掃描端取得 post-trim feature universe | needs-research | 要新增 `features_run_id` 跨棧參數（請求模型／前端／契約／UAT 全動），且 `EventImportService` 目前完全不碰 FF run ⇒ 超出本票；R2 之 D1 裁定事件掃描端恆走 event-study-only。日後實作**不得**刪除 Task 3.3 分支 |
| `SU-RESID-2` | 多 TF 之 `(event_id, timeframe)` 複合鍵 | needs-research | 本票以「每事件恰一個 selected per_tf row，否則 raise」fail-closed；複合鍵要連 `EventSplitPlan` 之下游一起改 |
| `SU-RESID-9A-UI` | 丟棄列數之**終端可見性**（API 回應欄位與前端顯示） | blocked-by | **為何現在不做**：`blocked-by:投影路徑無 EventSamplePipeline.run 生產接線（api/ 呼叫點=0）`——`D-002` Phase 9A 交付至 producer 層（producer 回傳 → `EventSplitPlan.summary` → `metadata.split_unify`），終端可見性須待投影路徑有生產接線後另票。**觸發條件（可執行）**：`grep -rc "EventSamplePipeline()\.run(\|create_event_sample_pipeline()\.run(" api --include='*.py'` 之命中數 **> 0**（現為 0）——🔴 **v11 作廢為唯一判準（R10 codex：該 regex 只匹配 inline constructor，漏掉 `pipeline = create_event_sample_pipeline(); pipeline.run(...)` 這種兩段式呼叫，真接上線也不會報；字面保留供追溯）**。**觸發條件（v11 可執行）**：以 AST 走訪 `api/` 全部 `.py`（排除 `tests/`）之 `Call` 節點，命中「method 名為 `run` 且 receiver 可追溯至 `EventSamplePipeline` 或 `create_event_sample_pipeline`、且實參含 canonical 邊界 `train_plan`／`test_plan`／`feature_index`」者，命中數 **> 0**。**recheck 命令**：`grep -rn "\.run(" api --include='*.py'`（廣掃全部 `.run(` 呼叫點為 AST 之超集，再逐筆判讀 receiver 與實參；**不得**用窄 regex 的零命中當「不存在」之證據）；**owner**：SPLITUNIFY epic 主委。🔴 **誠實邊界**：在本殘留解除前，「靜默丟棄」對終端使用者**仍然看不見**，`Task 9.1` 驗收不得宣稱該缺陷已消除。詳見 `docs/SPLITUNIFY_SPEC.D-002.md` §N 同名條目 |
| `SU-RESID-1` | attribution checker 擋不住歸屬錯置 | 🔴 **2026-09-11 重判：不合格，現在做** | 原理由「需語意對應、屬研究」只對一半——**完整語意比對**做不到，但「收尾模式有未引用編號就擋」與「決議須逐字引用 finding 斷言」**做得到**。🔴 **回溯稽核實證其必要性**（`handoffs/run_receipts/splitunify-attribution-audit-20260911.txt`，本票 8 輪程式碼審查、57 條意見）：**3 條委員意見實質被主委弄丟，兩道檢查都沒響**——①`CODEX-R3-P3-04`（裸 KeyError）沒被任何決議引用、從沒修；②`GROK-R1-P2-02`（答案窗差 1 毫秒的 mutation 缺口）掛對決議但從沒補；③B2b R1 之 H6（`tier_min_test_events`）寫「列入 B3 Task 3.1」延後、之後消失——**投影路徑把使用者設定靜默換成 1**。三條已於同日修掉並各配 mutation（`M-SU-30`／`31`／`32`、`M-SU-B3-13`）。另查出兩個工具缺陷：`reconcile_cluster_attribution_check.sh` 在中文上 `cut -c` 截斷壞掉（大量「附錄斷言：（找不到）」）；`completeness_check` 只驗編號是否在收斂檔，而附錄本來就逐字保留全部原文 ⇒ **永遠不會失敗**。GROK-R1-P2-02 之另一半（改讀 `time_bounds[0]`）已被 B3 之同源對證變成**等價 mutant**（兩者被強制相等），不另加 |
| `SU-RESID-3`（**B3 review R1 後大幅收窄**） | 同源對證只比**每段的首尾**時刻，不比中間每一列 | needs-research | 🔴 三家實跑證明的兩種攻擊（plan 建在較短網格＋長 index、index 同長度平移）**已於 B3 收斂時擋下**：以 `plan.time_bounds` 與傳入 `feature_index` 在該 plan 首尾列上逐值對證（型別驅動的單位分派，不猜；mutation `M-SU-B3-10`）。**殘留的是**：兩份網格若首尾時刻相同、僅中間間距不同，仍會通過——plan 身上只有 `time_bounds` 兩個端點，沒有逐列時刻可比。要關掉它需要 producer 隨 plan 傳完整時刻指紋（新欄位，動 IC 契約），屬 R-5／B4 之後 |
| ~~`SU-RESID-3`（原文，保留供對照）~~ | 投影未對證「plan 之 universe ＝ 傳入之 `feature_index`」 | needs-research | B3 自查發現。已補的是**兩 plan 之間**的 `base_universe_hash` 必須相同；與 `feature_index` 對證需兩側共用同一種 hash 表示法，而現行 `base_universe_hash` 是**秒**語意（`contracts._coerce_timestamp_array` 對數字一律 `unit="s"`）、事件側時鐘是毫秒 ⇒ 改 hash 輸入會移動既有 IC golden digest。該新 fail-closed 情形**刻意未登記**進 `split_unify.json`（登記會動到已戳記 SPEC 之封閉值集與前端枚舉面），改以明文 `ValueError` 擋；是否升格為具名 reason 交 B3 code review 裁定 |
