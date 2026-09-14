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

🔴 **本表之「狀態」欄＝批次進度之**唯一權威**（2026-09-14 新增）**。出生事故：主委實作完 B9A／B9B／B9C 三批，卻**一次都沒回來標本表**——狀態只記在 `HANDOFF.md` 與白話看板，於是同一件事有**三份**而本檔是過期的那一份。這正是委員已抓九次的「一個決定多落點、改一處漏一處」，只是這次漏的是 TODO 自己的進度。✅ `HANDOFF.md` 與 `白話說明/` 之批次狀態一律**指向本表**，不得自寫第二份。

| Batch | 含 Task | **狀態** | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|---|
| **B1** | 1.1, 1.2, 1.3 | ✅ 完成 | consult 三家戳記 rc=0（**已達成**） | 文件、枚舉 SoT、既有紅基準；**不動生產碼**（可獨立審） | 小 |
| **B2a** | 2.1 | ✅ 完成 | B1 | boundary builder 可獨立證偽（同源自證＋ms 同源） | 中 |
| **B2b** | 2.2 | ✅ 完成 | B2a | 投影純函式＋`build_time_clusters` 抽出 | 大 |
| **B2c** | 2.3 | ✅ 完成 | B2b | golden 五組；**仍不接線** | 中 |
| **B3** | 3.1, 3.2, 3.3 | ✅ 完成 | B2c | 接線／fail-closed／event-study-only 分派同批（分開會有一段時間邊界不唯一） | 大 |
| **B4** | 4.1 | ✅ 完成 | B3 | 報告與畫面（欄名待 B3 定案後才穩定） | 中 |
| **B9A** | 9.1 | ✅ **完成**（impl `c98acf26`；審碼 r18、閉合 r19） | B4 ＋ `D-002` 三家 `RECONCILE-STAMP` rc=0 | 揭露先行；只動 producer 回傳形狀與 summary 一鍵，可獨立回退 | 中 |
| **B9B** | 9.2, 9.2a | ✅ **完成**（impl `9e87386f`；審碼 r20、閉合 r21／r22） | B9A | 🔴 **不得拆批**：全量列在無 `feature_timeframe` 欄時複合鍵碰撞，加欄而不改 merge 則 `MergeError` ⇒ 只改其一皆紅 | 大 |
| **B9C** | 9.2b | ✅ **完成**（impl `a1e9680e`；審碼 r27，閉合 r28–r35 共九輪＋stamp-r6＋consult-r3/r4/r5；🔴 **consult-r4/r5 三家一致判定方向反轉**（見 `Task 9.3`）；**現待 review 覆核 v32＋重簽**） | B9B | 側別改 `decision_at_ms` 錨定 ＋ `(3.2)` 跨表互斥；鍵不唯一時「同側」無定義，故須在複合鍵已存在後 | 大 |
| **B9D** | 9.3 | ⬜ **未開工**（下一個） | B9C | 🔴 **v35 更正（v32 方向反轉後 §B 未同步）**：現行＝**把 `assignments`／`purged` 退回事件級＋同步計數**（具名 seam；Tier 0 同 commit）；下游表已改為追溯用、多數維持現狀；前端 `byEventId` owner 移 `Task 9.5`。以下原文保留供追溯：~~`Task 9.3` 表列**九處**逐處處置~~（七個下游消費模組——`feature_materialization`／`tables`／`ic_feed`／`counterexample_classifier`／`candidate_ledger`／`dedupe`／`pattern_bridge`——＋ event-level 表／manifest 與前端 `byEventId` 兩個支撐面，共九列；多為**防誤改**回歸測試，非改碼）。🔴 R13 `CODEX-R13-P2-03`：本欄原寫「六個下游消費面」與表列九列不符，已改為與表列一致 | 中 |
| **B9E** | 9.4 | ⬜ 未開工 | B9C ＋ 🔴 **B9D**（v36，`CODEX-R39-P1-05`：報告／baseline 驗收依賴事件級輸出與計數完成） | 記帳鏈與 `baseline` 拆鍵（投影計數已移 `Task 9.3`） | 中 |
| **B9F** | 9.5 | ⬜ 未開工（排最後） | B9D ＋ B9E | golden 多 TF／交錯平行組與前端 `byEventId`；🔴 v36 澄清：decision-anchor 換錨已於 B9C 完成，本批不重做側別換錨；整合後比對舊單 TF 值、依既定允許面凍結新組 | 大 |

🔴 **Phase 9 依賴序（`handoffs/reconcile/20260911-splitunify-b9-consult-r2/synth.md` 裁定；三家＋主委獨立版四方一致）**：
~~`9.1 → 9.2 → 9.2a → 9.2b → (9.3 ∥ 9.4) → 9.5`~~ ⇒ 🔴 **v36（`CODEX-R39-P1-05`）**：`9.1 → 9.2 → 9.2a → 9.2b → 9.3 → 9.4 → 9.5`。
~~`9.3` 與 `9.4` 可並行（前者動消費面、後者動計數與 `baseline`），惟 `9.4` 之 `per_symbol_n`／`tier_min` 去重與 `9.2a` 同檔 ⇒ 並行時須先 rebase 再跑各自驗收。~~
投影計數已移 `9.3` ⇒ 不再以「不同檔」為可並行依據；只有不重疊之 `baseline` 工作可先行，`9.4` 整批驗收在 `9.3` 之後。
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
  🔴 **SUPERSEDED BY `Task 9.2b`（B9C；R27 `GROK-R27-P1-01` 與 `CODEX-R27-P2-07` 兩家撞題抓出本段未標示）**：
  下方要點 1／2 之「以 `feature_cutoff_ms` 集合成員決定 train／test」與要點 4 之「不在 `feature_index`
  集合內 ⇒ purged」**皆已作廢**。現行投影：步驟 0 先驗 train／test 兩段非空且 row set 不重疊；
  事件側**只**由 `manifest.table.decision_at_ms` 依三段式決定——`decision <= train_last_ms` ⇒ train、
  `>= test_start_ms` ⇒ test、介於兩者 ⇒ purged；`decision_at_ms` 落在 `feature_index` 範圍**外**一律
  **raise**（不是 purged、更不是第四條分類分支）；`feature_cutoff_ms` **不參與** `split_label`。
  答案窗 purge 改按**事件側**一次決定並廣播到該事件所有 feature TF 列。
  🔴 刪節線與下方原字面保留供追溯，**不得**據以實作——依本段舊文會把事件級錨定**回退**成
  逐列判側，該回退實測會使 `test_event_level_anchor_broadcasts_side_to_all_feature_tf` 轉紅。
  1. ~~🔴 **兩段式判定，先後不可調（R3 之 E1；式子逐字採 R4 之 F1）**：
     `train_cutoff = feature_cutoff_ms ∈ as_ms(feature_index[train_plan.row_index])`；~~
     `test_plan.row_index` 為空 ⇒ **先 fail-closed**（`missing_test_plan`），禁與 `None` 比較；
     `test_start_ms = as_ms(feature_index[test_plan.row_index[0]])`；
     `train_cutoff and label_end_ms >= test_start_ms` ⇒ **purged**（`>=` 必須保留）。
     🔴 `purge_gap`／`embargo` 是 **row 單位且已含在 test row 起點**，**不得**再以毫秒相減。
     source bars 缺 endpoint 之檢查**不進投影**——明定為上游 alignment 之前置條件，
     G-5.3 用 `AlignmentReceipts` 驗。
     **再**做集合成員判定決定 train／test。
  2. ~~成員判定＝**集合**：`feature_cutoff_ms ∈ feature_index[train_plan.row_index]` ⇒ train；
     `∈ feature_index[test_plan.row_index]` ⇒ test；否則 purged。禁 `time_bounds` 區間。~~
     （🔴 **SUPERSEDED BY `Task 9.2b`**，見本段開頭；現行為事件級 `decision_at_ms` 三段式比較。）
  3. `event_keys` 以 **`event_id` 為鍵**對位，**禁 positional zip**（R3 之 E2）——
     `dedupe.py:46` 會依 `(label_start_ms, event_id)` 重排 manifest。
     🔴 **producer 具名（R4 之 F2）**：B2b 之 `build_event_keys(receipts, *, selected_timeframe)`，
     由 `receipts.event_level` ＋ `receipts.per_tf`（`feature_cutoff_ms` 住這裡）keyed join；
     **B3 只傳遞，不臨時組裝**；~~每事件須恰一個 selected `per_tf` row，否則 raise~~
     （`manifest.table` 只有 trigger `timeframe`、無 cutoff，不可代替）。
     🔴 **SUPERSEDED BY `Task 9.2`／`9.2a`（B9B；R21 `CODEX-R21-P1-02` 抓出本段未標示）**：
     `selected_timeframe` 已由**必填**改為 `Optional[str] = None`（`None`＝**全量**）；
     唯一性判準已由「每事件恰一列」改為 **`(event_id, feature_timeframe)` 複合鍵唯一**。
     刪節線字面保留供追溯，**不得**據以實作——依本段舊文會把已完成的全量行為**回退**。
  2. train／test 進 `assignments`（`split_label` 仍只有兩值）；purged 進**獨立**的
     `purged`，reason ＝ `interval_crosses_split_boundary`（契約既有字面）。
  3. `index_kind != "positional"` ⇒ raise；同時落兩態 ⇒ raise；
     🔴 單位歸一**自己做**（`pd.to_datetime(..., unit="ms")` 或 `asi8 // 10**6`），
     **禁呼叫** `_normalize_ic_time_index`——它是「秒」語意，餵毫秒會 raise
     （`ic_filter_orchestrator.py:269-271`）。v2 寫「復用該 normalizer」是錯的（R2 之 D7）。
  4. `event_keys.feature_cutoff_ms` 語意＝ feature_cutoff（`ic_feed.py:36`），非裸 `decision_at_ms`；
     ~~不在 `feature_index` 集合內 ⇒ purged，**禁 nearest／asof／ffill**。~~
     （🔴 **SUPERSEDED BY `Task 9.2b`**：`feature_cutoff_ms` 已不參與 `split_label`；
     界**外**之 `decision_at_ms` 一律 raise 而非 purged。禁 nearest／asof／ffill 之精神仍在——
     9.2b 用的是**比較**而非查表，本就沒有近似匹配的空間。）
  5. `clusters` 呼叫本 Task 一併抽出的 `build_time_clusters(manifest, bucket_ms)`
     （行為 byte 級不變，**保留** `_cluster_weight` 之 M5 mutation seam）。
  6. `summary` **12 鍵**齊全：`n_symbols`／`per_symbol_n`／`n_time_clusters`／
     `avg_cluster_size`／`degraded`／`loso_status`／`insufficient_events_in_test`／
     `stats_modes`／`n_events_raw`／`n_events_effective`／`n_purged`／`bucket_ms`。
     🔴 **SUPERSEDED（R21 `CODEX-R21-P1-02`）**：`Task 9.1` 加 `discarded_rows_by_feature_tf`、
     `Task 9.2a` 再加 `n_events`／`n_event_tf_rows`／`n_event_tf_rows_purged`
     ⇒ 現行為 **16 鍵**，權威＝`test_summary_has_all_sixteen_keys` 之 exact-set 斷言。
     本段之「12」字面保留供追溯，**不得**據以實作。
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
- 邊界（🔴 **② 已 SUPERSEDED BY `Task 9.2b`（B9C）；R28 `CODEX-R28-P1-04` 抓出本列仍為 live**，
  為「契約改後舊段未同步」之**第八次**發作；逐字採該家修法）：
  ①`event_keys` 為空 ⇒ 三態皆空（不 raise）；
  ②~~事件不在 `feature_index` ⇒ purged~~ ⇒ **現行**：`manifest.table.decision_at_ms` 落在
  `[index_ms[0], index_ms[-1]]` **之外** ⇒ **fail-closed raise**（訊息含 `event_id`），**不是** purged；
  `feature_cutoff_ms` **不參與** `split_label`（照舊文實作會把已修正的 fail-closed 回退成分類分支）；
  ③`train_last_ms < decision_at_ms < test_start_ms`（隔離帶）⇒ `assignments` 空而 `purged` 為全集
  （合法且預期，`tables.py:201` 已明載不得誤擋）。
- 風險緩解：mutation `M-SU-1`..`M-SU-7`、`M-SU-12`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` rc=0：
  🔴 **v33 自掃補漏**：~~`len(assignments) + len(purged) == len(event_keys)`~~ 於 v32 退回後**不再成立**（左邊已是事件數、右邊仍是複合鍵列數）⇒ 現行為 `len(assignments) + len(purged) == event_keys["event_id"].nunique()`，且兩者 `event_id` 交集為空；
  `set(summary.keys()) == {12 鍵}`（逐鍵斷言）🔴 **SUPERSEDED ⇒ 現行 16 鍵，見上第 6 點**；
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
     🔴 **SUPERSEDED BY `Task 9.5`（R22 `CODEX-R22-P1-02`）**：`Task 9.2a` 後行粒度已升為
     `(event_id, feature_timeframe)`，只比 `event_id` **集合**會吃掉多 feature TF 維度
     （同事件兩列縮成一個 id，換言之 mutation `M-SU-D2-16`「golden 仍以 event_id 清單比對」
     正是在打這一句）。⇒ 🔴 **v33 自掃補漏**：~~`Task 9.5` 擴維時須改為**複合鍵集合**比對~~ 作廢（`C5-22` 已改判甲類、維持事件級不擴維）⇒ `Task 9.5` 維持**事件級集合**比對，只新增交錯平行組。
     本句字面保留供追溯；🔴 **本批（B9B）刻意未改 golden**——凍結腳本維持單一 feature TF、
     既有值逐值不變，故本句在單 TF 下仍成立，是**跨批的過渡狀態**而非現行缺陷。
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

### Task 9.1 ✅ **已完成（B9A）** —— 丟棄列數之完整資料流契約（`票 SPLITUNIFY`）
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
- **覆蓋風險**：~~`Task 9.2` 會再改 `selected_timeframe` 之預設值~~（🔴 v26 更正（R31 `CODEX-R31-P2-05`）：`Task 9.2` 已於 **B9B 完成**，該預設值已改為 `None`＝全量）；本 Task 只改回傳形狀，兩者不衝突——**已實證**（B9B 落地後 `Task 9.1` 之回歸全綠）。

---

### Task 9.2 ✅ **已完成（B9B）** —— producer 停止單選，輸出全量 keyed rows（`票 SPLITUNIFY`）
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
  - `test_run_without_selected_timeframe_emits_all_feature_tf_rows`（🔴 **v36 更正（`CODEX-R39-P1-03`＝`COMPOSER-R39-P2-01`；SPEC §V `Task 9.2` 已於 v32 反轉）**：~~經 `EventSamplePipeline.run` 不傳 `selected_timeframe` ⇒ `len(assignments) == len(per_tf)` 且兩個 feature TF 皆在~~ ⇒ 現行：經 `EventSamplePipeline.run` 不傳
    `selected_timeframe` ⇒ `len(assignments)+len(purged) == per_tf.event_id.nunique()`，兩表各自 `event_id` 唯一且互斥、欄集為事件級；`event_keys` 與有效 `per_tf` 之 `(event_id, feature_timeframe)` 集合及列數相等、兩個 feature TF 皆仍在 `event_keys`。該測試之舊斷言由 `Task 9.3` 同批改寫）
  - `test_partial_boundary_gate_accepts_none_selected_timeframe`
    （🔴 **替換**既有把 `selected_timeframe=None` 視為必 raise 之參數化案例，**不得**只新增而留著舊的）
  - `test_feature_timeframe_column_sourced_from_per_tf_not_event_level`（同事件兩列須為**不同** TF 值）
  mutation 自證：`M-SU-D2-20`（保留預設單選 ⇒ 第 1 條紅）、`M-SU-D2-21`（門檻改回四鍵 ⇒ 第 2 條紅）、
  `M-SU-D2-23`（`validate="1:1"` ⇒ 第 1 條紅，`MergeError`）、`M-SU-D2-26`（冒充 ⇒ 第 3 條紅）。
- **存活至**：全票完工後保留（唯一 producer 實作）。
- **覆蓋風險**（🔴 v33 自掃補漏：`Task 9.2a` 之「兩表加欄」已由 v32 退回，其 `event_keys` 層之唯一性 guard 仍在）：`Task 9.2a` 會在同一函式再加 `feature_timeframe` 之唯一性 guard、`Task 9.2b` 會改其下游判側；
  兩者**只增不改**本 Task 之簽章與門檻，若日後有人把門檻改回四鍵即 `M-SU-D2-21` 轉紅。

---

### Task 9.2a ✅ **已完成（B9B）；🔴 v32 判其「兩表加欄」那一半為做過頭，由 `Task 9.3` 退回** —— schema 加 `feature_timeframe`（`票 SPLITUNIFY`）
- SPEC ref：§P Phase 9B `Task 9.2a`；§V `Task 9.2a`、`D-002-C3` purge 面
- 實作要點：
  1. 🔴 **v32 作廢（`GROK-R36-P1-02`／`COMPOSER-R36-P1-07`）**：~~`assignments`／`purged` 兩表各加 `feature_timeframe` 欄~~——`consult-r4`／`r5` 三家一致判定該外推為實作做過頭（R1 規格輪本就寫明對外之 `EventSplitPlan` 維持事件級，見 SPEC `(0.4)` 適用層限制）⇒ **兩表不加該欄**，由 `Task 9.3` 退回並同步計數；`receipts.per_tf` **不改形狀**（此半仍有效）。
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
    （🔴 **SUPERSEDED BY `Task 9.2b`（B9C）；R29 `CODEX-R29-P1-05`**：9.2b 已落地，該 xfail **已解除**，
    現行輸出為 `1 passed`。下方所有要求 `xfailed` 的字面僅適用於 **9.2b 之前**，不得據以驗收。）
    不得 `--deselect` 藏起來。
    🔴 **機械驗收（缺此則刪掉該測試也不會紅）**：node id 逐字為
    `tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed`；
    驗收命令須**逐字指定該 node id**（見下方 §驗證第 6 條）；~~且輸出須為 `xfailed`——
    `passed`（＝XPASS，`strict=True` 下會轉 fail）~~ 與 `no tests ran`（＝被刪或被改名）皆判**不通過**。
    （🔴 **v24 更正（R29 `CODEX-R29-P1-05`）**：9.2b 落地後現行判準為 `1 passed`；`xfailed` 字面僅適用 9.2b 之前。）
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
    ⇒ ~~輸出須含 `1 xfailed`；出現 `1 passed`（XPASS）…即**不通過**~~ 🔴 **v24 更正（R29 `CODEX-R29-P1-05`）**：
    `Task 9.2b` 完成後之現行判準為**輸出須含 `1 passed`**；`no tests ran`（被刪／改名）仍**不通過**
    （node id 是逐字錨點）。舊字面僅適用於 9.2b 之前。
  - 🔴 **R20 三家撞題補一條**：`test_multi_symbol_branch_summary_counts_are_named`——多 symbol
    （Mapping）分支之 `n_events`／`n_event_tf_rows`／`n_event_tf_rows_purged` 逐值斷言，
    並**明文擋 0 值**（0 正是「三個 kwargs 被省略」時的樣子）。缺此條時省略那三個 kwargs
    會讓 summary 靜默變 0 而 scoped 回歸仍全綠。
  mutation 自證：`M-SU-D2-25`（同側檢查移到複合鍵 guard 之前 ⇒ 第 4 條紅）；
  ~~`M-SU-D2-35`（`assignments` 組裝不寫 `feature_timeframe` 欄）~~；
  ~~`M-SU-D2-36`（`purged` 組裝不寫該欄）~~ 🔴 **兩條 v32 撤下、v35 補標（`CODEX-R38-P2-01`）**——退回自身改由 `M-SU-D2-41`..`44` 覆蓋（見 `Task 9.3`）；
  **多 symbol 三計數**：分派器省略該三 kwargs ⇒ `test_multi_symbol_branch_summary_counts_are_named` 轉紅。
  🔴 **v35 作廢（`CODEX-R38-P2-01`）：自本句起至「`C5-21` 由主委同型自查補上）」止僅供追溯，不得據以實作**——上列 `M-SU-D2-35`／`36` 已撤下，退回後 `assignments`／`purged` **不得**含 `feature_timeframe` 欄。原文：🔴 **v15 強化（R14 codex／grok 撞題）**：上列兩條之應紅測試**不得**只靠 `duplicated(subset=[...])` 的 `KeyError`——
  實作者若寫成 `if "feature_timeframe" in df.columns` 軟包，欄缺就靜默略過而不紅。
  兩個測試各須**先** `assert "feature_timeframe" in <表>.columns`、**再**做複合鍵唯一性斷言；
  且 fixture 須為**多 feature TF**。驗收時「刪欄」與「以 `in df.columns` 包住 guard」**兩種破壞都要實跑轉紅**。
  🔴 兩者為 v14 新增——`C5-20`／`C5-21` 原本分別指向 `M-SU-D2-20`／`M-SU-D2-24`，而那兩條破壞的是
  producer 預設與答案窗判定，**不是欄位本身**（R13 `CODEX-R13-P1-01` 提 `C5-20`，`C5-21` 由主委同型自查補上）。
- **存活至**：🔴 **v35 更正（`CODEX-R38-P2-01`）**：~~全票完工後保留（複合鍵 schema 為 Phase 9 之最終形態）~~ ⇒ 只保留 `event_keys` 之複合鍵稽核 schema；`assignments`／`purged` 之事件級退回由 `Task 9.3` 完成。
- **覆蓋風險**：`Task 9.2b` 會在本 Task 之 guard **之後**插入同側檢查與跨表互斥；插入位置若被調到 guard 之前
  即 `M-SU-D2-25` 轉紅。`Task 9.4` 會讀本 Task 新增之 `n_event_tf_rows*`，不改其定義。

---

### Task 9.2b ✅ **已完成（B9C；碼面自 r27 起未再變動；🔴 **其 `Task 9.2a` 之「`assignments` 加 `feature_timeframe` 欄」已由 v32 判為做過頭，將由 `Task 9.3` 退回**（不影響 9.2b 之事件級錨定））** —— 側別判定改為事件級錨定（`票 SPLITUNIFY`）
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

### Task 9.3 — 🔴 **v32 全面改寫：切分歸屬表退回事件級（`票 SPLITUNIFY`）**

🔴 **本 Task 之目標於 v32 反轉**。原目標「把下游改成能消費複合鍵表」已**作廢**；現目標是**把 `assignments`／`purged` 退回一事件一列**，下游因此多半不必改。

**為何反轉**（`consult-r4`／`consult-r5`，**三家一致**；起因為使用者提出之設計質疑）：
- 側別由事件級 `decision_at_ms` 判一次後**廣播**（`Task 9.2b` 已落地）⇒ `assignments` 之 `feature_timeframe` 欄**不承載任何判定資訊**，同事件各列恆同值。
- 三家各自窮盡掃描：該欄**無任何消費者**（下游只讀 `event_id`／`split_label`／`symbol`／列數；golden JSON 無此欄；前端型別無此欄）。
- 🔴 **R1 規格輪本就寫明**「內部邊界投影可用 `(event_id, timeframe)`；**對外之 `EventSplitPlan` 維持事件級**」⇒ 把複合鍵外推到 `assignments`／`purged` 是**實作做過頭**，本 Task 是**把實作拉回原規格**。
- 三家判現行方案為**過度工程**、且「切分語意無增益」；最小正確修法＝**「切分走事件級 ＋ per-TF 稽核獨立保留」**。

**保留不動**（不得順手退掉）：`Task 9.1` 之 `discarded_rows_by_feature_tf` 記帳；`Task 9.2` 之 `selected_timeframe=None` 預設全量；`Task 9.2b` 之事件級錨定＋廣播＋異側／跨表混態 fail-closed；`receipts.per_tf` 維持一事件×一週期一列之 PIT 稽核與 `_assert_event_keys_wellformed`；`build_event_keys` 之複合鍵中間態不動。

🔴 **退回之形狀（逐字採 `CODEX-R5-P1-01`）**：
> 內部稽核保留複合列 → **輸出前以 `event_id` 聚合並驗證欄值** → 最後**恰一列**進 `assignments` 或 `purged`。

**明禁**：以 `drop_duplicates`／`set` 去重——那會把「同事件欄值衝突」這種實作缺陷**靜默吞掉**，正是本 epic 一路在打的形態。聚合點必須是**具名的 seam**並逐欄驗值。

🔴 **不得半退（`CODEX-R4-P1-01`／三家撞題之 `COMPOSER-R5-P1-01`＋`GROK-R5-P1-01`＋`CODEX-R5-P1-02`）**：
組列與**計數**必須同一次改完。只改組列而不改計數，`tier_min_test_events` **門檻仍可被 1 事件×N TF 膨脹繞過**——那是**門檻失效**（測試段事件數不足卻放行），不是帳面問題。

- SPEC ref：§P Phase 9B `Task 9.3`；`D-002-C5` (5.1)(5.6) register
- 🔴 **動工前置（consult-r2 之 A6；stamp-r1 codex 要求機械化）**：先重掃 `D-002-C5` register，逐條複驗
  `C5-01`..`C5-29` 因 `feature_timeframe` 欄而是否改變分類（甲／乙／丙）。
  **產出物為必要條件，不是筆記**：重掃結果須寫成
  `handoffs/run_receipts/<UTC時戳>-splitunify-task-9.3-register-rescan.txt`，內容逐條為
  `C5-NN <改前分類> -> <改後分類> <碼證 path:line>`，且**檔案存在**列入下方驗收；
  缺檔即本 Task 不得宣告完成（沒有這一條，省略重掃在現行檔案級 rc=0 下完全看不出來）。
- 🔴 **v32 逐落點退回清單（逐字採 `COMPOSER-R5-P1-01` 必答 2a 表 A／B；Tier 0 者須同一次 commit）**：

| 檔 | 行 | 改什麼 |
|---|---|---|
| `split_projection.py` | `:783-798` | 組列改為逐 `event_id` 從 `event_state` 寫**一列**；移除 `feature_timeframe` 欄 |
| 同上 | `:804-808` | `assignments` 欄→`["event_id","symbol","split_label"]`；`purged`→`["event_id","reason"]` |
| 同上 | `:811-813` | `per_symbol_n` 改每 symbol 之 `event_id.nunique()`（**非列數**） |
| 同上 | `:814-821` | `n_test`／`per_symbol_test_n` 改 `assignments` 之 `event_id` 去重計數 |
| 同上 | `:826-828` | `n_event_tf_rows` 仍 `len(event_keys)`；🔴 `n_event_tf_rows_purged` 改為 **`event_keys` 中 purged 側之列數**（不再是 `len(purged)`——退回後那是事件數，名實不符） |
| 同上 | `:907-911` | 空批 DataFrame 欄位同步移除 `feature_timeframe` |
| 同上 | `:392-425` | **保留** `_assert_event_level_side_consistency`；另加輸出表 `event_id` 唯一之 pre-check |
| 同上 | `:566-576` | **保留** `event_keys` 複合鍵 guard（per_tf 稽核） |
| 同上 | `:328-343` | **`build_event_keys` 不動**（複合鍵中間態＋`discarded` 記帳保留） |
| `pipeline.py` | `:825-827` | 確認 `n_train`／`n_test`／`n_purged` 在事件級 `assignments` 下語意正確；須加**去重斷言**防回歸 |
| `split_projection.py` | `:899-901` | 🔴 **v32 補（`CODEX-R36-P1-03`：原表只覆蓋單標的主路徑）**：**多標的**分支之 `per_symbol_test_n` 同步改 `event_id` 去重 |
| 同上 | `:914-916` | 🔴 **v32 補**：**多標的**分支之 `per_symbol_n` 同步改 `event_id` 去重 |
| 同上 | `:917-932` | 🔴 **v32 補**：多標的之 global summary／count 同步；`n_purged` 仍為 unique event count |

🔴 **聚合 seam 之具名簽名（逐字採 `CODEX-R36-P1-03`；不得只寫「具名」而不給名，否則實作者可用 inline `drop_duplicates` 自稱 seam）**：
```python
_aggregate_event_level_split_rows(
    event_keys: pd.DataFrame, event_state: Mapping[Any, str]
) -> tuple[list[dict], list[dict]]
```
按 `event_id` 分組；🔴 **v36 更正（`CODEX-R39-P1-04`）**：~~`symbol`／`split_label` 非單值即 raise~~ ⇒ `event_keys` 同事件之 `symbol` 非單值即 raise `AlignmentViolationError`（訊息含 `event_id`）；`split_label` 一律取自 `event_state[eid]`（輸入無 `split_label` 欄、`event_state` 每 eid 單值）；異側／跨表混態由既有 `_assert_event_level_side_consistency` 承接；
輸出固定兩個事件級 schema；🔴 **明禁** `drop_duplicates`／`set`／take-first。

🔴 **v34 補：seam 之定義處與呼叫面（`CODEX-R37-P1-04`：v33 只給簽名、沒說放哪、誰呼叫、多標的怎麼合併）**
| 面向 | 規定 |
|---|---|
| 定義處 | `momentum/Analysis/event_samples/split_projection.py` 模組級私有函式（與 `_assert_event_level_side_consistency` 同層），**不得**定義在 `_derive_single_symbol` 內部 |
| 單標的呼叫面 | `_derive_single_symbol` 於算出 `event_state` 後**唯一一次**呼叫它取得兩個列表，取代現行 `:783-798` 之逐列 append |
| 多標的呼叫面 | **每個 symbol 各自呼叫一次**（各有自己的 `event_state`），再把回傳之兩個列表**串接**；🔴 **不得**先把各 symbol 之 `event_state` 合併成一個 dict 再呼叫——`event_id` 已含 symbol 語意，合併只會遮蔽跨 symbol 之鍵碰撞 |
| 合併後之唯一性 | 串接完成後**再驗一次** `assignments`／`purged` 之 `event_id` 全域唯一，違反即 raise（擋跨 symbol 碰撞） |
| 輸出 schema | 單標的與多標的**共用同兩個事件級 schema**，不得分歧 |

🔴 **Tier 0 之界線（`CODEX-R37-P1-04`）**：seam 之定義與呼叫面、單／多標的輸出 schema、`per_symbol_n`／`per_symbol_test_n`／tier 門檻之去重、`n_event_tf_rows_purged` 之新公式、空批分支——**以上必須同一次 commit**；分開改必留計數錯配。🔴 **v35 補（`review-r38` 兩家必答 5b 一致）**：同批另含 `C5-21` ANCHOR 以 `./venv/bin/python scripts/register_anchor_check.py --emit <path>:<line>` 重出（見下方 ANCHOR 子句），並使 `test_d002_register_anchors_all_valid` 通過——否則 schema 已退回而 register 仍驗退回前之行，落地當下即轉紅。

🔴 **purge 稽核計數之逐字公式（同上來源；單標的與多標的共用）**：
```python
purged_event_ids = {eid for eid, side in event_state.items() if side == "purged"}
n_event_tf_rows_purged = int(event_keys["event_id"].isin(purged_event_ids).sum())
```
`n_purged` 仍是 **unique event count**；**不得**再以 `len(purged)` 計。

🔴 **`C5-21` 之 ANCHOR 子句**：現指向退回**前**之碼，須於退回落地之**同一次 commit** 以 `--emit` 重出（`CODEX-R36-P1-03` 明示此為同 commit 相依，不另列 finding）。

**測試（Tier 0，與上表同 commit）**：
`test_assignments_composite_key_unique`／`test_purged_composite_key_unique` → 改寫為 `event_id` 唯一且**無** `feature_timeframe` 欄；
`test_summary_has_n_events_and_n_event_tf_rows` → `n_event_tf_rows_purged` 改對 `event_keys` purged 列數；
🔴 `test_event_level_anchor_broadcasts_side_to_all_feature_tf`（`:1742-1743`）→ **不得只刪、也不得只改成 `len==1`**（會失去 `M-SU-D2-14` 防 cutoff 判側回歸之鑑別力）⇒ `assignments` 端改驗「**恰一列且側別正確**」，並**另增**「兩 TF 仍在 `event_keys`」之稽核層斷言；
`test_duplicate_composite_key_error_message_names_key_not_side` → 改測 `event_keys` 之複合鍵重複訊息（非 `assignments`）；
`test_multi_symbol_branch_summary_counts_are_named` → 更新期望值；
`test_splitunify_wiring.py:110-111` → **保留**（退回後恢復正確）；`:152` 刪 `feature_timeframe in assignments.columns`；`:234-259` 改為 `len(assign)+len(purged)==n_events`。

🔴 **v35 補：新 mutation 之具名測試尚未入庫（`CODEX-R38` 必答 4a／4b）**——`test_event_level_aggregation_rejects_conflicting_values`（`M-SU-D2-42`）與 `test_tier_min_test_events_counts_unique_event_ids`（`M-SU-D2-43`）實查皆**不存在** ⇒ 兩者建立前**不得宣稱** `M-SU-D2-41`..`44` 之覆蓋已閉。建立順序（與上列 Tier 0 測試同 commit）：
1. 共用兩 TF fixture：同 `event_id`、同 `symbol`、`event_keys` 兩列之 `feature_timeframe` 不同；`event_state={eid: "test"}` 與 `{eid: "purged"}` 兩版。只造稽核層輸入，輸出期望**不含**複合欄。
2. `M-SU-D2-42`：直接呼叫 `_aggregate_event_level_split_rows`，對真實 `event_keys` 造同 `event_id` 兩 TF 列之 **`symbol` 衝突**（assigned／purged 兩路各一）⇒ 斷言 `AlignmentViolationError` 且訊息含該 `event_id`。🔴 **v36 更正（`CODEX-R39-P1-04`）**：~~symbol 或 split_label 給兩個不同值~~——`split_label` 取自單值 `event_state`，此 seam 無從表達異側；異側與跨表混態改由既有 `_assert_event_level_side_consistency` 之直接 rows 反例驗（拔掉該 guard 之異側 raise 須紅），**不得**在 `event_keys` 塞假 `split_label` 欄。
3. `M-SU-D2-41`：改寫 `test_assignments_composite_key_unique`／`test_purged_composite_key_unique`——合法兩 TF fixture 下兩表各恰一列、`event_id` 唯一、無 `feature_timeframe` 欄。
4. `M-SU-D2-43`：新增 `test_tier_min_test_events_counts_unique_event_ids`——同一事件×2 TF 之 test 批、`tier_min_test_events=2` ⇒ public `insufficient_events_in_test` 含該 symbol；另斷言 `summary["per_symbol_n"]` 為 unique event 數。🔴 **v36（`CODEX-R39-P1-05`）**：`per_symbol_test_n` 是內部門檻參數、**不是 summary 鍵**，不得斷言 `summary["per_symbol_test_n"]`、不得為此新增鍵（`test_summary_has_all_sixteen_keys` 之 exact-set 不變）；分別破壞 `per_symbol_n` 與門檻輸入計數皆須紅。本測試之唯一 owner＝本 Task，`Task 9.4` 只重跑作回歸。
5. `M-SU-D2-44`：改寫 `test_summary_has_n_events_and_n_event_tf_rows`——一 purged 事件×2 TF ⇒ `n_event_tf_rows_purged=2`、`n_purged=1`。
6. 最後才更新多標的、wiring 與錨點閘回歸。

🔴 **`per_symbol_test_n` 是 TODO 的過時字面、不是現行 `_build_summary` 的 schema**（`CODEX-R5-P1-02` 實查）⇒ 驗收改測 **unique-event 門檻**，**不得**為了對齊文件而新增欄位。

🔴 **退回後之 mutation 覆蓋缺口（具名，主委不自行補）**：`M-SU-D2-05`／`35`／`36`／`37`／`40` 已依 `CODEX-R5-P1-03` **撤下**（它們只為複合 `assignments` 服務，退回後皆空殼），但退回**自身**的可壞面——①輸出多列 ②聚合時靜默吞掉欄值衝突 ③計數被列數膨脹——**目前無 mutation 覆蓋**。🔴 **v32 已由 `CODEX-R36-P1-02` 填上，主委未自創**：新增 **`M-SU-D2-41`**（output multiplicity：聚合改回逐 `event_keys` 列 append ⇒ `assignments`／`purged` 之 `event_id` 唯一斷言轉紅）、**`M-SU-D2-42`**（reducer 以 `drop_duplicates`／`set`／take-first 吞掉 `symbol` 衝突 ⇒ `test_event_level_aggregation_rejects_conflicting_values` 轉紅；v36：衝突面限 `symbol`，見 SPEC 同條）、**`M-SU-D2-43`**（`per_symbol_n`／tier 改以 TF 列數計 ⇒ unique-event 門檻測試轉紅）、**`M-SU-D2-44`**（`n_event_tf_rows_purged` 改回 `len(purged)` ⇒ 一 purged 事件帶兩 TF 時得 1 而非 2，轉紅）。mutation 條數 40 → **44**。🔴 **可達性**：四條皆落在退回後之**合法**產出路徑上，不是 `consult-r3` 所指之結構不可達型。

- 🔴 **下表為 v32 前之「下游改法」清單，多數已因退回而不必做**，保留供追溯；逐列之現行處置以上方退回清單與 SPEC register 之 v32 改判為準：

| 消費面 | 處置 | 應紅之 mutation | 測試檔 |
|---|---|---|---|
| `feature_materialization` | **維持事件級橫向合併**（不得改複合鍵） | `M-SU-D2-04` | `tests/momentum/event_samples/test_feature_materialization.py` |
| `tables` | 🔴 **v35 作廢（`CODEX-R38-P1-01`／`COMPOSER-R38-P1-01`）**：~~另 `tables.py:372` 之 `assignments.set_index("event_id")["symbol"].reindex(idx)` 要改——重複索引下 `reindex` 會直接 `ValueError`，須加顯式去重 reducer：同 `event_id` 之 `symbol` 相同則取該值、衝突則 fail-closed raise~~ ⇒ 現行＝**維持事件級 `.loc[eid]`（`:214`／`:229`／`:373`）以及 `:372` 之 `assignments` `event_id` lookup，不改碼、不新增 reducer**（`C5-29` v32 改判甲類；退回後 `assignments` 一事件一列，`reindex` 直接成立） | `M-SU-D2-06`（維持面）；~~`M-SU-D2-40`（移除 `:372` 之去重 reducer）~~ **v32 撤下** | `tests/momentum/event_samples/test_tables.py`（維持面回歸；~~須成對兩條：同值去重／衝突值 raise~~ v35 作廢） |
| `ic_feed` | 維持六鍵事件級（不加 TF 欄）；🔴 另 **`event_context_from_windows` 之餵入須先按 `event_id` 去重**——🔴 **v16 更正（實讀 `ic_feed.py:109`）**：v15 原寫「多 TF 下重複三元組」**不可達**（該處以 `per_tf["timeframe"] == timeframe` 單一 TF 過濾，且 `WindowRow` 只有事件級欄位）⇒ 可達 seam 是 `event_context_from_windows` **本身**：餵入含重複 `event_id` 之 windows 會使 `event_manifest_hash` 漂移 | `M-SU-D2-07`、`M-SU-D2-19`（維持面）＋`M-SU-D2-38`（餵入未去重） | `tests/momentum/event_samples/test_gap3_conditional_ic.py`（`ic_feed` 無專屬測試檔）；測試須**直接呼叫** `event_context_from_windows` 驗雜湊不變性 |
| `counterexample_classifier` | 維持事件級 | `M-SU-D2-08` | `tests/momentum/event_samples/test_counterexample_classifier.py` |
| `candidate_ledger` | 維持事件級 | `M-SU-D2-09` | `tests/momentum/event_samples/test_candidate_ledger.py` |
| `dedupe` | 保留集事件級決定 ＋ 廣播到該事件所有 per-TF 列 | `M-SU-D2-10` | `tests/momentum/event_samples/test_dedupe.py` |
| `pattern_bridge` | 🔴 **v32 撤下**：~~丙類，要改：`assign.set_index("event_id")` 先去重取唯一側，不唯一即 fail-closed~~——`assignments` 退回一事件一列後索引本就唯一，該 reducer 只為複合輸出服務且其 fail-closed 已被 `consult-r3` 判結構不可達（空殼）。現行＝**維持現狀＋防誤改回歸** | ~~`M-SU-D2-05`（改複合鍵索引）＋`M-SU-D2-37`（略過去重／不 fail-closed）~~ **v32 撤下**（🔴 v35 補標，`CODEX-R38-P1-02`／`COMPOSER-R38-P1-02`）；防誤改由現行事件級回歸守住，不另掛 mutation | `tests/momentum/event_samples/test_pattern_bridge.py` |
| event-level 表／manifest | 粒度不變 | `M-SU-D2-18` | `tests/momentum/Analysis/test_splitunify_derive.py` |
| 前端 `byEventId` | 維持 `canonicalEventId` 鍵，排除於本次複合鍵遷移之外；🔴 **v35 更正（`review-r38` codex 落點清單）**：owner＝**`Task 9.5`**（`C5-18` register 之 owner 欄，v32 已定單一 owner） | `M-SU-D2-11`（於 `Task 9.5` 建立之測試上驗） | ~~🔴 須新建 `frontend/src/app/search/eventExportByEventId.test.tsx`~~ ⇒ 移至 `Task 9.5` 建立 |

- 不可做（v32 仍適用）：不得用形狀規則（凡 `set_index("event_id")` 一律改）批次套用；
  不得把 event-level 表複製成多列以「配合」複合鍵；
  不得把 `M-SU-D2-11` 之前端面以「等 UAT 再做」延後——🔴 **v35 更正**：~~它是本 Task 的交付面之一~~ ⇒ 它是 **`Task 9.5`** 的交付面（`C5-18` owner），本 Task 不建該測試。
- 邊界：①單 feature TF 批下，上表九處行為須與改前**逐值相同**；
  ②🔴 **v34 作廢（`GROK-R37-P1-05`：v33 只改了後段 reducer 型別句，本句仍 live）**：~~`pattern_bridge` 去重後若同一 `event_id` 出現兩個不同 `split_label` ⇒ fail-closed raise，不得靜默取第一個~~ ⇒ `C5-24` 已改判甲類、**不改碼**，該 fail-closed 經 `consult-r3` 判結構不可達；**同語意之要求已移到聚合 seam**（見下）；③前端 `byEventId` 在 `feature_timeframe` 存在時仍以 `canonicalEventId` 建鍵，
  匯出附帶欄位不得變空（🔴 v35：前端面 owner 移 `Task 9.5`，本條隨之在該 Task 驗）。
- 🔴 **v31 新增：fail-closed 之錯誤型別釘死（逐字採 `CODEX-R6-P1-02`）**——
  邊界②原只寫「fail-closed raise」而**未釘死例外型別**，實作者可用裸 `ValueError` 或把測試放寬成
  `pytest.raises(Exception)`，alignment 契約漂移就抓不到。**現行**：
  🔴 **v32 反轉（`COMPOSER-R36-P1-06`／`GROK-R36-P1-04`）**：~~「`C5-24` 與 `C5-29` 之 reducer，遇同一 `event_id` 的欄值不唯一或衝突時，一律 raise
  `momentum.core.contracts.AlignmentViolationError`，訊息含 `event_id`；同值多列只取唯一值；
  測試一律 `pytest.raises(AlignmentViolationError, match=...)`，不得以 `Exception`／`ValueError` 寬比。」~~ **作廢**——
  `C5-24`／`C5-29` 已於 v32 改判甲類、**不改碼**，其 fail-closed 經 `consult-r3` 判結構不可達。
  **要求移到聚合 seam**：「`_aggregate_event_level_split_rows` 在同一 `event_id` 之 `symbol`／`split_label`
  非單值時，一律 raise `momentum.core.contracts.AlignmentViolationError`，訊息含 `event_id`；
  測試一律 `pytest.raises(AlignmentViolationError, match=...)`，不得以 `Exception`／`ValueError` 寬比。」
  （該型別已存在且為 `ValueError` 子類，`Task 9.2b` 之 side guard 已採用，故新舊行為對既有 caller 相容。）
- 🔴 **v31 新增：`C5-25` 去重之 hash 相容性與 golden 連動（逐字採 `CODEX-R6-P1-03`）**——
  該家實跑證明**去重與否會改變** `event_manifest_hash`（`UNIQUE_HASH` vs `DUPLICATE_HASH` 不相等）
  ⇒ 原條文只寫「先去重再算雜湊」而**沒寫既有 golden 會不會被連動**。**現行**：
  「先按 `event_id` 穩定去重；同 ID 之 `label_start_ms`／`label_end_ms` 不完全相同即 raise
  `AlignmentViolationError`，完全相同只留一列。既有單 TF 且 ID 唯一輸入之 `event_manifest_hash`
  **必須逐字不變**；`Task 9.3` 只跑比對，**不得自動 `--write`**，任一既有 golden digest 改變
  即停止並轉 `Task 9.5`。`(丙)` 任一列重掃分類需改動時，當輪補
  `TARGETS: <repo-relative-path>:<start>-<end>`、更新 register 與 receipt 的分類／碼證，
  未完成前 `Task 9.3` 必須 blocked。」
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/event_samples/test_feature_materialization.py tests/momentum/event_samples/test_tables.py tests/momentum/event_samples/test_gap3_conditional_ic.py tests/momentum/event_samples/test_counterexample_classifier.py tests/momentum/event_samples/test_candidate_ledger.py tests/momentum/event_samples/test_dedupe.py tests/momentum/event_samples/test_pattern_bridge.py tests/momentum/Analysis/test_splitunify_derive.py` rc=0；
  ~~前端 `cd frontend && node_modules/.bin/vitest run src/app/search/eventExportByEventId.test.tsx` rc=0~~（🔴 v35：移至 `Task 9.5` 驗證）。
  上表 **owner＝`Task 9.3` 之後端列**各一條「改壞就變紅」測試（🔴 v36，`CODEX-R39-P2-01`：前端 `byEventId`／`M-SU-D2-11` 之測試歸 `Task 9.5`，本 Task 完成不以其預先存在為條件）；🔴 靜默面須斷言取到的**值**正確，不得只斷言「不報錯」。
  🔴 **register 重掃 receipt 之機械驗收（逐字；R13 `CODEX-R13-P1-02` 指出「只比行數」可被「同一 ID 重複 29 次」繞過，故改為 exact ID set ＋ 當輪綁定）**：
  1. **唯一且當輪**：receipt 檔名須為 `handoffs/run_receipts/<UTC時戳>-splitunify-task-9.3-register-rescan.txt`，
     且其**首行**逐字為 `TASK: <本 Task 之 impl task-id>`、**次行**逐字為 `COMMIT: <本 Task 開工時的 HEAD sha>`。
     🔴 **v26 更正（R31 三家撞題 `CODEX-R31-P1-04`／`COMPOSER-R31-P1-01`／`GROK-R31-P1-01`）**：v15 寫的
     「`COMMIT:` 須等於 audit 所記之 round-start HEAD」**當時不可執行**——`impl_token_issued`／`committee_dispatch`／
     `ticket_commit` 三種事件的 schema **都沒有 HEAD 欄**（權威＝`scripts/audit_events.json`），
     驗收只能退化成「有這一行就算過」，正是 v15 想擋的那件事。
     **修法＝把欄位補上，而不是改寫判準**（逐字採 `CODEX-R31-P1-04`）：`gate.sh --impl-self` 發 token 時
     已記錄 `round_start_head=$(git rev-parse HEAD)`（`scripts/gate.sh` impl token 區塊＋`scripts/audit_events.json`
     之 `impl_token_issued.fields` 與 `required_fields_per_event.impl_token_issued`；取不到或非 40-hex 即**拒發 token**）。
     **現行可執行判準（任一條失敗即 FAIL；不得只檢查「有 COMMIT 行」）**：
     ```bash
     RECEIPT=<本列所述之 receipt 檔>; TASK_ID=<本 Task 之 impl task-id>
     COMMIT=$(sed -n '2p' "$RECEIPT" | sed 's/^COMMIT: //')
     test "${#COMMIT}" = "40"                                   # 全長 object name，禁短 sha
     git cat-file -e "${COMMIT}^{commit}"                        # 須為真實 commit
     HEAD_IN_AUDIT=$(grep -F '"event": "impl_token_issued"' .claude/gate/audit.log \
       | grep -F "\"task_id\": \"${TASK_ID}\"" | tail -1 \
       | sed -n 's/.*"round_start_head": "\([0-9a-f]\{40\}\)".*/\1/p')
     test -n "$HEAD_IN_AUDIT"                                    # 缺欄即 FAIL
     test "$COMMIT" = "$HEAD_IN_AUDIT"                           # 逐字相等
     ```
     🔴 **明禁替代讀法**（逐字採 `GROK-R31-P1-01`）：不得改用「該 token `ts` 之前最近一筆 `ticket_commit.sha`」——
     `ticket_commit` 是 post-commit 事件，時序不代表開工 HEAD。
     🔴 **誠實邊界**：本綁定擋的是「事後補寫 receipt、把 `COMMIT` 填成已含本批改動的 sha」；
     它**不**擋「同一人在同一 commit 內同時改 receipt 與生產碼」——該面與 `SU-RESID-V8-ATTEST` 同類，不在此重複登記。
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
     - 🔴 **v29 現行：碼證錨點閘＝`scripts/register_anchor_check.py`**
       （單一精確行 ＋ **整行**相等 ＋ **唯一性** ＋ **路徑不得越界**；逐字採 R33／R34 共七條修法）
       **本閘的五代沿革就是「弱閘會被打穿」的完整紀錄，逐條寫明是因為每一代都曾被當成已閉合**：
       ① v15「行號 ≤ 該檔總行數」→ 四列全指註解仍綠（R31 三家撞題）。
       ② R31 委員修法「statement／AST overlap」→ 主委實跑量測，只殺掉四處中的**兩處**。
       ③ v26「行**範圍** ＋ 單一 token **子字串**」→ R32 打穿（`:341` 是 `raise` 的訊息字串）。
       ④ v27「單一行 ＋ token **子序列**」→ R33 三條打穿（子序列可跳 token 之語義替身、
       重疊命中計數錯誤、`.tsx` 不驗檔內唯一性）。
       ⑤ v28「整行 token 序列相等 ＋ 單檔唯一」→ R34 三條打穿（**跨行 token** 中間行、
       `.tsx` **只驗單檔**故整行搬檔即看不出、`REPO_ROOT / <絕對路徑>` 丟掉前綴故錨可指 repo 外）。
       **現行判準（五項，全為合取）**：
       1. 每個錨點是**單一精確行**（非範圍）。
       2. **路徑守衛**：register 所載路徑須為 repo 相對、不得含 `..`，`resolve()` 後須仍在 repo 內。
       3. `.py`：該行不得被**跨行 token**（多行字串等）覆蓋——覆蓋即 fail-closed；
          其**正規化完整 token 序列**（只收起訖都在該行的 token）須與 register 所載**逐一相等**；
          該序列在**整個檔案**中須恰好出現在**一行**上；並以 AST 確認該行落在非純字串常數之 statement 上。
       4. `.tsx`／`.ts`：無 AST ⇒ **正規化整行之 sha256 相等**，且該行在**全 repo 之 `.ts`／`.tsx`**
          中恰好出現一次（不是只驗同檔——整行搬到另一個檔也要抓得到）。
       5. 任何「0 次或多於 1 次」皆拒絕。
       **register 側之機器可讀語法**（寫在該列消費面欄，可多個）：
       `〔ANCHOR` + 反引號包住的 `<path>:<line>` + `TOKENS` + 該行**全部** token（各以反引號包住）+ `〕`；
       非 `.py` 改用 `LINESHA256` + 反引號包住的 64-hex（因該行含 template-literal 反引號，塞不進 TOKENS）。
       **驗收命令**：
       ```bash
       ./venv/bin/python scripts/register_anchor_check.py            # 全表；rc=0 才算過
       ./venv/bin/python scripts/register_anchor_check.py <path> <line> <tok...>   # 單點複核
       ./venv/bin/python scripts/register_anchor_check.py --emit <path>:<line>     # 產生子句內容，禁手抄
       ```
       🔴 **不是一次性驗收**：`tests/momentum/Analysis/test_splitunify_contract.py` 已把它接進**六路回歸**，
       四條測試逐條對應一種壞法——
       `test_d002_register_anchors_all_valid`（🔴 **v29 起改為逐列精確計數**
       `{C5-13:3, C5-14:1, C5-19:3, C5-21:2, C5-23:2, C5-25:3, C5-26:3, C5-27:3, C5-28:1, C5-29:1}`，
       R34 兩家撞題證明舊的 `len >= 16` 可被「剝掉某列再從別列複製補回總數」繞過）、
       `test_d002_register_anchor_gate_rejects_known_false_greens`（v15／v26 兩代之 must-fail）、
       `test_d002_register_anchor_gate_rejects_r33_r34_decoys`（v27／v28 兩代之六個 decoy
       ＋ 絕對路徑與 `..` 路徑）、
       `test_d002_register_anchor_gate_accepts_the_real_lines`（**反向**：閘若被改成永遠回 False 也會紅）。
       另 `_load_anchor_checker` 對 checker 檔缺席會直接 assert 失敗，不是靜默 collect error。
       🔴 **具名誠實邊界（三條）**：
       ①`C5-28` 之落點是 `.tsx`，AST 不適用，只比正規化整行之 sha256
       （代價＝人讀 SPEC 看不出該行內容，須用 `--emit` 重算；換得的是不可用子字串或片段繞過）；
       ②`.ts`／`.tsx` 之全域唯一性掃描**跳過** `node_modules`／`.next`／`dist`／`build`／`coverage`
       ——把 decoy 藏進建置產物目錄，本閘看不到（那些目錄不是本專案原始碼，不納入）；
       ③本閘保證「那一行的碼逐字就是 register 所載的那一行，且在其語言範圍內唯一」，
       **不**保證「那行就是語意上對的設計點」，也**不**保證「該列的錨點涵蓋已經完整」——
       後兩者仍靠 register 同列描述與審碼輪（R34 `CODEX-R34-P1-04` 即為涵蓋不足之實例，已補七個錨點）。
       🔴 **v26／v27／v28 之舊敘述皆已整段刪除**，不留半截——它們各自被 R32／R33／R34 實跑打穿，
       留著就是下一個「照舊段做」的陷阱；沿革見 SPEC v27／v28／v29 條目。
     - 🔴 **v16 之 keyed 對證已於 v17 收窄（R16 `CODEX-R16-P1-01`；主委實測確認其碼證成立）**：
       v16 寫「碼證檔路徑須與 register 同列所載之落點檔相同」，但**實測 29 列中有 20 列的消費面欄
       根本沒有 `path:line`**（`C5-01`..`08`／`09`..`12`／`15`..`18`／`20`／`22`／`24`／`25`）
       ⇒ 該檢查在 **69% 的列上不可執行**，屬**假閘**（寫了跑不動，比沒有更糟）。
       **現行（可執行）判準——三段式，29 列逐列歸屬且互斥窮盡（r17 三家獨立算出之 15 列與主委機械掃描完全一致）**：
       - **(甲) 有 `path:line` 之 10 列**（`C5-13`／`14`／`19`／`21`／`23`／`25`／`26`／`27`／`28`／`29`）：
         🔴 **v29 現行**：碼證之 `path:line` 須**逐字等於**該列某個 ANCHOR 子句之 `<path>:<line>`
         （單一精確行；`scripts/register_anchor_check.py` 為唯一判準）。
         ~~碼證之檔路徑須與該列所載落點檔**相同**、行號須落在該列所列範圍內。~~（範圍式判準已於 v27 作廢——它正是被 R32 打穿的那個形狀）
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
       `momentum/Analysis/event_samples/ic_feed.py:56-65`）。**現在不做的理由**：那要動 **19** 列已戳記
       （🔴 **v20 更正（R24 `CODEX-R24-P2-02`）**：原寫「~~20 列~~」，與本殘留上方已更正之 19 列**同段不一致**；
       `C5-25` 補錨這一個動作至此第三度打翻同一個數字——前兩次在驗收第 5 點與殘留首句）
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
- 🔴 **在上表 owner＝`Task 9.3` 之後端測試實際存在之前，不得宣稱本 Task 之 mutation 網已閉**（§V；🔴 v36 依 owner 分開，`CODEX-R39-P2-01`——`M-SU-D2-11` 歸 `Task 9.5`，整票閉網仍涵蓋兩個 owner）。
- **存活至**：全票完工後保留（下游表之防誤改回歸測試是唯一擋「未來有人用形狀規則批改」的東西；v36：~~九處~~ 前端列 owner 已移 `Task 9.5`）。
- **覆蓋風險**：🔴 **v36 更正（`CODEX-R39-P1-05`）**：~~`Task 9.4` 會改 `split_projection` 之計數段與 `baseline`，與本 Task 之消費面不同檔；兩者並行時須先 rebase~~ ⇒ 投影計數已由本 Task 承接，`Task 9.4` 不再改 `split_projection` 計數段；`Task 9.4` 之整批驗收在本 Task 之後。`Task 9.5` 之 golden 會覆蓋 `dedupe`／`clusters` 的期望值。

---

### Task 9.4 — 記帳與報告鏈（`票 SPLITUNIFY`）
- SPEC ref：§P Phase 9B `Task 9.4`；§V `Task 9.4`；`D-002-C6`
- 實作要點：
  1. `n_train`／`n_test`／`n_purged` 明確定為**事件數**；新增列數欄（`n_event_tf_rows*`）。
  2. 🔴 **v36 移出（`CODEX-R39-P1-05`：同一計數修法派給兩個 batch 會互相覆寫）**：~~事件數門檻路徑：`split_projection.py` 之 `n_test`／`per_symbol_test_n`／`per_symbol_n` 皆改以 `event_id` 去重計數~~ ⇒ 投影之 unique-event 計數由 **`Task 9.3`** 同批完成（`M-SU-D2-43`）；本 Task 視其為輸入契約，只驗事件數與樣本數分離及 baseline／報告鏈，**不新增** `per_symbol_test_n` 輸出鍵。
  3. 🔴 **v34 作廢（`COMPOSER-R37-P1-03`）**：~~`dict(zip(...))` 之單鍵映射改複合鍵映射~~ ⇒ **維持單鍵映射**（`C5-23` 已改判甲類）；改為補「逐事件值比對」以擋 `M-SU-D2-12` 之新破壞面（以集合相等冒充逐列相等）。
  4. 🔴 **`baseline` 拆鍵**：舊鍵 `n_test` **刪除**（不得保留、不得當 alias），改輸出
     `n_test_events`（`unique(test_ids)`）與 `n_test_samples`（`len(idx)`）；回傳 dict 鍵集為 **exact 契約**。
  5. 🔴 `insufficient_events_in_test` **只修正計數**；終端可見性屬 `SU-RESID-9A-UI` 殘留，
     **不列入本批完成條件**。驗收時不得宣稱「樣本不足已能被使用者看到」。
- 修改檔案（🔴 已具名到檔:行）：
  - ~~`momentum/Analysis/event_samples/split_projection.py`（計數段）~~（🔴 v36：移 `Task 9.3`）
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
  - `test_tier_min_test_events_counts_unique_event_ids`——🔴 **v36（`CODEX-R39-P1-05`）**：本測試由 **`Task 9.3` 建立**（見該 Task 建立順序第 4 步），本 Task **只重跑作回歸**；~~須另斷言 `summary["per_symbol_test_n"]`~~——該鍵不在 summary（16 鍵 exact-set），斷言之即 `KeyError`、為之新增鍵即破 exact-set。原字面（v16，僅供追溯）：1 事件 × 2 TF、`tier_min=2` ⇒ 仍判樣本不足；另斷言 `per_symbol_n` 與 `per_symbol_test_n` 皆等於各自之 `event_id` 去重計數。
  - `test_event_count_conservation`（`n_train+n_test+n_purged == n_events`，事件數非列數）
  前端 `cd frontend && npm run build` rc=0（型別改動同批驗）。
  mutation 自證：`M-SU-D2-13`、`M-SU-D2-31`、`M-SU-D2-32`、`M-SU-D2-12`；
  ~~`M-SU-D2-39`（v15 新增：`per_symbol_n`／`tier_min_test_events` 未以 `event_id` 去重 ⇒ `test_tier_min_test_events_counts_unique_event_ids` 轉紅）~~（🔴 v36 併入 `M-SU-D2-43`，歸 `Task 9.3`）。
- **存活至**：全票完工後保留（`n_test_events`／`n_test_samples` 兩量分離為最終契約）。
- **覆蓋風險**：`SU-RESID-9A-UI` 殘留解除時會再加終端揭露欄，屬**只增不改**；
  本 Task 之鍵名與語意不得在那時被改寫。

---

### Task 9.5 — golden 與前端（`票 SPLITUNIFY`）
- SPEC ref：§P Phase 9B `Task 9.5`；§V `Task 9.5` 及第 6 條；§G (G-4d)(G-4e)
- 實作要點：
  1. 🔴 **v33 界定（主委自掃補漏）**：`scripts/freeze_splitunify_golden.py` 之 `_plans()`／`_event_keys()`／`_build_actual()` 擴維，
     新增**交錯平行組**；`main()` 寫檔**只增鍵不覆蓋**（舊鍵＝§G 回歸錨）。
     ⚠️ **「擴維」僅指 fixture 之稽核面（`_event_keys()` 產出多 feature TF 列）與 (G-2) 之交錯平行組**；
     **不**含 `g1_membership`／`g3b_oracle` 之成員集——那兩者已於 v32 改判甲類、**維持事件級不擴維**（`C5-22`／§G (G-3) 之 v32 反轉）。
  2. 🔴 **(G-4e) 第三份判準**：`_event_keys()` 內**人手逐筆填入**字面 `expected_side` 欄，
     且**不得** import／呼叫投影、`_oracle_membership` 或兩者之共用 helper。
  3. 🔴 **v8 baseline 換錨（write-once ＋ 外部錨）**：
     - `tests/golden/splitunify/splitunify_golden.v8.json` 以 `O_EXCL` **write-once** 建立；已存在即 raise。
     - 同批寫 `splitunify_golden.v8.sha256`；`--write` 指向 `.v8.json` 即 raise。
     - 🔴 **同一次變更**必須把該檔 `sha256` 之 **64-hex 字面**寫入 `docs/SPLITUNIFY_SPEC.D-002.md` §V 第 6 條
       之逐字錨點行 `V8_BASELINE_SHA256=<64-hex>`，且該行**不得**由 `freeze_splitunify_golden.py` 改寫。
     - 主檔 `splitunify_golden.json` 既有 **11 個頂層鍵逐值不變**；新成員集只落在 `g1_membership_v9`／`g3b_oracle_v9`。
  4. 前端 `byEventId` Map **排除於複合鍵遷移之外**（見 `Task 9.3` 表末列）。🔴 **v35 補（`C5-18` owner＝本 Task）**：新建 `frontend/src/app/search/eventExportByEventId.test.tsx`（同目錄四支 `eventExport*.test.tsx` 可循），斷言以 `canonicalEventId` 建鍵、匯出附帶欄位不為空；`M-SU-D2-11` 在此測試上驗；驗證 `cd frontend && node_modules/.bin/vitest run src/app/search/eventExportByEventId.test.tsx` rc=0。
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

## §D mutation 對照表（13 條；自證，每批收案前跑，紅只認 rc=1）

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
| `SU-RESID-2` **部分關閉；🔴 v32 改寫「未關閉的那一半」之定義（`COMPOSER-R36-P1-07`）——原文把「複合鍵要連 `EventSplitPlan` 下游一起改」當未竟之工，三家判定那一半本來就不該做；未關閉者改為「把 `assignments`／`purged` 退回事件級並同步計數（`Task 9.3`）」。下方為 v32 前敘述，保留供追溯** | 多 TF 之 `(event_id, feature_timeframe)` 複合鍵 | blocked-by | 🔴 **v35 更正（`CODEX-R38-P1-03`／`COMPOSER-R38-P1-03`）——producer／schema 面已關閉的只有 `event_keys` 稽核層**：`Task 9.2`＋`9.2a` 使 producer 停止單選、於 `event_keys` 輸出全量 `(event_id, feature_timeframe)` 列，guard 判準改複合鍵唯一（退回後 `assignments`／`purged` 端改驗 `event_id` 唯一）；~~`assignments`／`purged` 加 `feature_timeframe` 欄~~ 屬 v32 判定之做過頭，由 `Task 9.3` 退回，**不得據本列保留該欄**。🔴 **側別錨定（`Task 9.2b`）亦已於批次 B9C 關閉**（R27 `GROK-R27-P1-02`：帳面未隨批次前進）——事件級 `decision_at_ms` 三段式已落地、`feature_cutoff_ms` 退出 `split_label`、(3.2) 異側與跨表混態皆 fail-closed。🔴 **尚未關閉者＝`Task 9.3` 之 `assignments`／`purged` 事件級退回與同步計數**（v35 同步本列首句之 v32 定義；~~下游消費面九處逐處處置~~ v32 起多數改判維持現狀，見 `Task 9.3` 下游表）；~~與側別錨定（`Task 9.2b`）~~ ⇒ ~~原文「複合鍵要連 `EventSplitPlan` 之下游一起改」現只剩消費面那一半~~。**為何現在不做**：`blocked-by:Task 9.3 尚未實作`——依賴序明定 `9.2a → 9.2b → 9.3`，不得跳。🔴 **本列狀態自 R22 `CODEX-R22-P1-01` 更正**：主委於 R21 依 `CODEX-R21-P1-02` 之同型掃描曾標「已關閉」（那次只點名 `Task 2.2`），R22 該家實查指出下游仍在 `Task 9.3` ⇒ 只能部分關閉 |
| `SU-RESID-V8-ATTEST` | 倉內沒有獨立信任根：同一 commit 同步替換全部副本擋不住。🔴 **v26 起涵蓋兩面**：(a) v8 不可變基準之錨／基準／helper；(b) **(G-4e) 之三份人手判準副本**（`expected_side`／`expected_decision_at_ms`／`_INDEP_DECISION_MS`，R31 `CODEX-R31-P1-01` 實跑三份同步改錯仍綠） | user-ruling | **已關閉的半**：錨點只認 §V 區段（`HISTORY`／沿革區塞入無效）、旁檔與檔案內容三層比對、`O_EXCL` write-once、首次建立交易式——五個攻擊面皆有實跑探針證明會擋。**未關閉的半（兩面共通）**：同一作者在**單一 commit** 內同步替換全部副本（面 a＝四個檔；面 b＝三份手填字面，或初始就一起填錯），任何**倉內**機制都擋不住；要擋需受保護簽章或不可變 ancestor attestation。🔴 **不再加第四層副本**：委員提的兩種再抬一級形狀皆以**人工核對**為信任根，與「不接受用紀律或記憶當解法」相斥，且只把門檻由三檔抬到四檔、不改變可閉合性。**為何現在不做**：`user-ruling:2026-09-12 使用者裁定「不再擴建治理工具；同型缺陷降級為具名殘留」`——且繞過成本（同 commit 改三到四個檔）**低於**合規成本（導入並維護簽章鏈），依「繞過成本 ≥ 合規成本即收」歸**蓄意等價**。**觸發條件（可執行）**：專案導入 commit 簽章或受保護分支（`git config --get commit.gpgsign` 為 true，或 repo 有 branch protection）。**owner**：SPLITUNIFY epic 主委。🔴 **誠實邊界**：關閉前，「換錨是刻意的」之信任根實際是 **code review 與 git 歷史**，不是這幾道機械閘。詳見 `docs/SPLITUNIFY_SPEC.D-002.md` §N 同名條目 |
| `SU-RESID-9A-UI` | 丟棄列數之**終端可見性**（API 回應欄位與前端顯示） | blocked-by | **為何現在不做**：`blocked-by:投影路徑無 EventSamplePipeline.run 生產接線（api/ 呼叫點=0）`——`D-002` Phase 9A 交付至 producer 層（`build_event_keys` 回傳 ＋ `EventSplitPlan.summary` 鍵；🔴 **v21 更正（R25，三家撞題）**：原寫「~~producer 回傳 → `EventSplitPlan.summary` → `metadata.split_unify`~~」，與 SPEC §N 同名條目之 v20 兩層交付、以及**本殘留自身**「metadata 層延後」之定義自相矛盾——R24 修了 SPEC §N 六處，**沒改本檔同名條目**），終端可見性須待投影路徑有生產接線後另票。**觸發條件（可執行）**：`grep -rc "EventSamplePipeline()\.run(\|create_event_sample_pipeline()\.run(" api --include='*.py'` 之命中數 **> 0**（現為 0）——🔴 **v11 作廢為唯一判準（R10 codex：該 regex 只匹配 inline constructor，漏掉 `pipeline = create_event_sample_pipeline(); pipeline.run(...)` 這種兩段式呼叫，真接上線也不會報；字面保留供追溯）**。**觸發條件（v11 可執行）**：以 AST 走訪 `api/` 全部 `.py`（排除 `tests/`）之 `Call` 節點，命中「method 名為 `run` 且 receiver 可追溯至 `EventSamplePipeline` 或 `create_event_sample_pipeline`、且實參含 canonical 邊界 `train_plan`／`test_plan`／`feature_index`」者，命中數 **> 0**。**recheck 命令**：`grep -rn "\.run(" api --include='*.py'`（廣掃全部 `.run(` 呼叫點為 AST 之超集，再逐筆判讀 receiver 與實參；**不得**用窄 regex 的零命中當「不存在」之證據）；**owner**：SPLITUNIFY epic 主委。🔴 **誠實邊界**：在本殘留解除前，「靜默丟棄」對終端使用者**仍然看不見**，`Task 9.1` 驗收不得宣稱該缺陷已消除。詳見 `docs/SPLITUNIFY_SPEC.D-002.md` §N 同名條目 |
| `SU-RESID-1` | attribution checker 擋不住歸屬錯置 | 🔴 **2026-09-11 重判：不合格，現在做** | 原理由「需語意對應、屬研究」只對一半——**完整語意比對**做不到，但「收尾模式有未引用編號就擋」與「決議須逐字引用 finding 斷言」**做得到**。🔴 **回溯稽核實證其必要性**（`handoffs/run_receipts/splitunify-attribution-audit-20260911.txt`，本票 8 輪程式碼審查、57 條意見）：**3 條委員意見實質被主委弄丟，兩道檢查都沒響**——①`CODEX-R3-P3-04`（裸 KeyError）沒被任何決議引用、從沒修；②`GROK-R1-P2-02`（答案窗差 1 毫秒的 mutation 缺口）掛對決議但從沒補；③B2b R1 之 H6（`tier_min_test_events`）寫「列入 B3 Task 3.1」延後、之後消失——**投影路徑把使用者設定靜默換成 1**。三條已於同日修掉並各配 mutation（`M-SU-30`／`31`／`32`、`M-SU-B3-13`）。另查出兩個工具缺陷：`reconcile_cluster_attribution_check.sh` 在中文上 `cut -c` 截斷壞掉（大量「附錄斷言：（找不到）」）；`completeness_check` 只驗編號是否在收斂檔，而附錄本來就逐字保留全部原文 ⇒ **永遠不會失敗**。GROK-R1-P2-02 之另一半（改讀 `time_bounds[0]`）已被 B3 之同源對證變成**等價 mutant**（兩者被強制相等），不另加 |
| `SU-RESID-3`（**B3 review R1 後大幅收窄**） | 同源對證只比**每段的首尾**時刻，不比中間每一列 | needs-research | 🔴 三家實跑證明的兩種攻擊（plan 建在較短網格＋長 index、index 同長度平移）**已於 B3 收斂時擋下**：以 `plan.time_bounds` 與傳入 `feature_index` 在該 plan 首尾列上逐值對證（型別驅動的單位分派，不猜；mutation `M-SU-B3-10`）。**殘留的是**：兩份網格若首尾時刻相同、僅中間間距不同，仍會通過——plan 身上只有 `time_bounds` 兩個端點，沒有逐列時刻可比。要關掉它需要 producer 隨 plan 傳完整時刻指紋（新欄位，動 IC 契約），屬 R-5／B4 之後 |
| ~~`SU-RESID-3`（原文，保留供對照）~~ | 投影未對證「plan 之 universe ＝ 傳入之 `feature_index`」 | needs-research | B3 自查發現。已補的是**兩 plan 之間**的 `base_universe_hash` 必須相同；與 `feature_index` 對證需兩側共用同一種 hash 表示法，而現行 `base_universe_hash` 是**秒**語意（`contracts._coerce_timestamp_array` 對數字一律 `unit="s"`）、事件側時鐘是毫秒 ⇒ 改 hash 輸入會移動既有 IC golden digest。該新 fail-closed 情形**刻意未登記**進 `split_unify.json`（登記會動到已戳記 SPEC 之封閉值集與前端枚舉面），改以明文 `ValueError` 擋；是否升格為具名 reason 交 B3 code review 裁定 |
