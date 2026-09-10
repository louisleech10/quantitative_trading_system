# SPLITUNIFY — TODO

**SPEC**：`docs/SPLITUNIFY_SPEC.md`（**v2**）　**票**：`SPLITUNIFY`　**日期**：2026-09-11　**狀態**：v2，待 R2 三家審。
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
| **B2** | 2.1, 2.2, 2.3 | B1 | boundary builder→投影→golden 為同一條因果鏈；**仍不接線** | 大 |
| **B3** | 3.1, 3.2, 3.3 | B2 | 接線／fail-closed／event-study-only 分派同批（分開會有一段時間邊界不唯一） | 大 |
| **B4** | 4.1 | B3 | 報告與畫面（欄名待 B3 定案後才穩定） | 中 |

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
  `set(json["fail_closed_reasons"])` 與 Python 常數 `==`；刪一鍵 ⇒ raise（可證偽）；
  `assert "assignment_states" not in json`。
- **存活至**：全票完工後保留（前端亦讀）。
- **覆蓋風險**：B3 若發現新 fail-closed 情形會**追加** reason 值，不改既有值。

### Task 1.3 — 既有紅基準清單（`票 SPLITUNIFY`）
- SPEC ref：Task 1.3／R1 之 C3　目標：讓 B3 驗收逐條可證偽，取代聚合期望數。
- 輸入 / 輸出：實跑 pytest → `tests/baselines/analysis_known_failures.nodeids`
  ＋ `handoffs/run_receipts/splitunify-analysis-baseline.stdout`。
- 實作要點：一次實跑產出，**不得手抄湊數**：
  `venv/bin/python -m pytest tests/momentum/Analysis --tb=no -q 2>&1 | tee <receipt> |
  awk '/^FAILED /{print $2}' | sort -u > tests/baselines/analysis_known_failures.nodeids`。
- 修改檔案：`tests/baselines/analysis_known_failures.nodeids`（新）；
  `handoffs/run_receipts/splitunify-analysis-baseline.stdout`（新）。既有 caller：無。
- 不可做：不得手寫 nodeid；不得把本票新增之測試檔放進清單。
- 邊界：①清單為空 ⇒ B3 驗收改為直接 rc=0；②清單中任一條變綠 ⇒ 必須主動移出。
- 風險緩解：⊘
- **驗證**：`venv/bin/python -m pytest -q --collect-only $(cat tests/baselines/analysis_known_failures.nodeids)` rc=0；
  `test -s tests/baselines/analysis_known_failures.nodeids`；
  `wc -l` 與 receipt 內 `FAILED ` 行數相同；
  `venv/bin/python -m pytest -q --collect-only $(cat tests/baselines/analysis_known_failures.nodeids)`
  rc=0（清單內有不存在的 nodeid ⇒ rc≠0，可證偽）。
- **存活至**：`REDSWEEP` 票收案後刪除。
- **覆蓋風險**：`REDSWEEP` 會逐條清空；兩票之間以「只准變短」為不變式。

### Task 2.1 — canonical boundary builder（`票 SPLITUNIFY`）
- SPEC ref：C-0　目標：兩端共用之**唯一**邊界算術。
- 輸入 / 輸出：`holdout_boundary(feature_index, *, oos_test_size, purge_gap, embargo)`
  → `(train_row_index, test_row_index, train_end_ms, test_start_ms)`。
- 實作要點：
  1. **以既有函式定義自身**：`holdout_split_point` ＋ `holdout_test_row_index`
     ⇒ 不引入第二份算術（否則 `M-SU-11` 會紅）。
  2. 時間一律 epoch ms；DatetimeIndex 以 `asi8 // 10**6` 換算（同 `split_preview.py:77-78`）。
  3. 純算術、無副作用、不 import `api`。
- 修改檔案：`momentum/core/split_preview.py`（既有檔新增函式）。
  既有 caller：`ic_filter_orchestrator`（B3 接）、`pipeline`（B3 接）。
- 不可做：不得在此讀 config；不得回傳 datetime（統一 ms）；不得自己重寫切點公式。
- 邊界：①`feature_index` 為空 ⇒ raise；②`test_rows` 為空 ⇒ `test_start_ms` 回 `None`
  （**不得**回 `-1` 或 `0`）；③`purge_gap`／`embargo` 為呼叫端算好的最終值。
- 風險緩解：mutation `M-SU-11`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/core/test_splitunify_boundary.py` rc=0：
  回傳之 `test_row_index` 與 `holdout_test_row_index(...)` 逐值相同（`np.array_equal`）；
  空 index ⇒ raise；`pd.to_datetime(train_end_ms, unit="ms").year` ∈ [2015, 2035]（防 1970 坑）。
- **存活至**：全票完工後保留（唯一邊界實作）。
- **覆蓋風險**：B3 只增加 caller，不改簽名。

### Task 2.2 — `derive_event_split_from_plans` 純函式（`票 SPLITUNIFY`）
- SPEC ref：C-3、C-4、C-5　目標：由 canonical 邊界導出**完整**的 `EventSplitPlan`。
- 輸入 / 輸出：
  `(train_plan, test_plan, event_index, feature_index, *, manifest)` → `EventSplitPlan`。
- 實作要點：
  1. 成員判定＝**集合**：`ts ∈ feature_index[train_plan.row_index]` ⇒ train；
     `∈ feature_index[test_plan.row_index]` ⇒ test；否則 purged。禁 `time_bounds` 區間。
  2. train／test 進 `assignments`（`split_label` 仍只有兩值）；purged 進**獨立**的
     `purged`，reason ＝ `interval_crosses_split_boundary`（契約既有字面）。
  3. `index_kind != "positional"` ⇒ raise；單位未歸一 ⇒ raise（復用
     `_normalize_ic_time_index` ＋ `asi8`，不另寫第二套）；同時落兩態 ⇒ raise。
  4. `event_index` 語意＝ feature_cutoff（`ic_feed.py:36`），非裸 `decision_at_ms`；
     不在 `feature_index` 集合內 ⇒ purged，**禁 nearest／asof／ffill**。
  5. `clusters` 呼叫本 Task 一併抽出的 `build_time_clusters(manifest, bucket_ms)`
     （行為 byte 級不變，**保留** `_cluster_weight` 之 M5 mutation seam）。
  6. `summary` **12 鍵**齊全：`n_symbols`／`per_symbol_n`／`n_time_clusters`／
     `avg_cluster_size`／`degraded`／`loso_status`／`insufficient_events_in_test`／
     `stats_modes`／`n_events_raw`／`n_events_effective`／`n_purged`／`bucket_ms`。
     `insufficient_events_in_test` 改看**投影後**的 test 數。
  7. `EventSplitConfig.embargo_ms` 與 `embargo_ms_by_symbol` 於本路徑須為 `None`，
     否則 raise（不得靜默忽略）。
  8. 純函式：無 log、無 I/O、不讀 config、不改輸入。
- 修改檔案：`momentum/Analysis/event_samples/split_projection.py`（新）；
  `momentum/Analysis/event_samples/event_split.py`（抽出 `build_time_clusters`）。
  既有 caller：無（B3 接）。
- 不可做：不得讀 config；不得自算 purge／embargo；不得回退成二態；
  不得把 purged 併進 `assignments`；不得產出空 plan 冒充未切分。
- 邊界：①`event_index` 為空 ⇒ 三態皆空（不 raise）；②事件不在 `feature_index` ⇒ purged；
  ③全部落隔離區 ⇒ `assignments` 空而 `purged` 為全集（合法，`tables.py:201` 已明載不得誤擋）。
- 風險緩解：mutation `M-SU-1`..`M-SU-7`、`M-SU-12`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` rc=0：
  `len(assignments) + len(purged) == len(event_index)` 且兩者 event_id 交集為空；
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
  4. **G-5**：逐 row test fingerprint、逐 event `assignments`／`purged` IDs、
     answer-window 完整性、leakage negative case 四項。
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
  (B) 既有紅之 FAILED nodeid 集合與該清單**集合相等**（`==`，多或少皆判紅）；
  (C) `venv/bin/python scripts/freeze_evtlabel_survivor_golden.py`（G-2 之 sha256 未漂移）。
  另加：釘選測試斷言生產路徑對 `split_events` 之呼叫次數 `== 0`。
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
  2. `summary` **不得**出現 `n_train`／`n_test`／`n_purged`。
  3. **沿用既有機制**（`pipeline.run_event_study_only`、
     `case_import_service.py:1618-1619` 之 capability 形態），不新造第二套。
- 修改檔案：`api/services/case_import_service.py`、`momentum/Analysis/event_samples/pipeline.py`。
  既有 caller：前端事件掃描頁（只讀 `capability`，型別不變）。
- 不可做：不得以 `test_fraction` 自行切分後宣稱 OOS；不得填 0 冒充。
- 邊界：①既有 `lookahead_split_blocked` 分派路徑不變（兩條 unavailable 原因並存、reason 不同）；
  ②有 canonical universe 時行為不變。
- 風險緩解：mutation `M-SU-10`。
- **驗證**：`venv/bin/python -m pytest -q tests/api/test_splitunify_event_study_only.py` rc=0：
  `capability["split"] == "unavailable"` 且
  `capability["reason"] == "canonical_feature_universe_unavailable"`；
  `assert "n_test" not in summary`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：per-symbol 支援（R-1）不影響本分支。

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
| `M-SU-11` | boundary builder 改用自己的算術（不呼叫既有兩支） | `test_splitunify_boundary.py -k same_source` | B2 |
| `M-SU-12` | 事件 ms 與 feature index 單位未歸一（秒／毫秒混用） | `test_splitunify_derive.py -k unit_normalize` | B2 |
| `C0` | 只改註解（對照組） | 必須仍綠 | 全批 |

---

## §E 具名殘留（每條帶「為何現在不做」，只准 blocked-by／user-ruling／needs-research）

| ID | 項目 | 理由類別 | 為何現在不做 |
|---|---|---|---|
| `R-1` | per-symbol 投影（讓多標的批能跑） | needs-research | `base_universe_hash` 在多標的下之唯一性語意未定；先 fail-closed 比先算錯好 |
| `R-2` | `baseline`／`tables`／`pattern_bridge` 之 OOS 數值變動量 | blocked-by | 待 B2 之 G-3a 遷移報告實跑才有數字 |
| `R-3` | UAT 項目更新 | user-ruling | 使用者已裁定 UAT 一律最後 |
| `R-4` | `extract_event_patterns` 無 caller（未接線） | blocked-by | 本票只保證其消費之 `assignments` 語意不變；接線屬另一票 |
| `SU-RESID-1` | attribution checker 擋不住歸屬錯置 | needs-research | 需「決議項 ↔ finding 語意對應」之機械判準，屬治理工具研究 |
