# SPLITUNIFY — TODO

**SPEC**：`docs/SPLITUNIFY_SPEC.md`　**票**：`SPLITUNIFY`　**日期**：2026-09-10　**狀態**：v1 草案，待三家審。
**切法來源**：委員會 consult 共識（`handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`，commit `9f75e4a7`）——
使用者 2026-09-10 裁定「切法由你跟委員討論共識」，離線時再次授權 ⇒ **不回頭問使用者**。
**實作端**：Claude 主委自任；review＝codex＋composer＋grok 三家全員。

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

- **解耦**：`momentum/` 不 import `api/`（R1）。新投影模組 `momentum/Analysis/event_samples/split_projection.py`
  只吃 `SplitPlan` 與 `pd.Index`，**不讀 config、不做 I/O**；service 不互 import（R4）。
- **Logging**：`get_logger(__name__)`；投影迴圈內**不得** log（10k 事件級）。
- **Error 分類**：多 symbol 未支援＝non-retryable，`ValueError` 明確 raise（reason 字面出自
  `split_unify.json`）；缺 train／test plan 亦 non-retryable。**禁**以警告放行。
- **不可違反原則**：不弱化任何既有隔離閘；全域（非事件）路徑報告逐位元組不變（G-2）；
  golden 比對失敗**不得**自動覆蓋。
- **🔴 本票之核心禁令**：**禁以全域 scalar `test_timestamps` 交集取代事件計畫**
  （SPEC C-2；codex 與 composer 各自標 P0；已有實測 receipt
  `20260910T150504Z-splitunify-multisymbol` 證明兩者不等價）。
- **防假綠**：驗收讀 pytest 自己的 summary 行（非 harness rc）；既有紅基準見
  `HANDOFF.md`「既有紅盤點」（`tests/momentum/Analysis` 20 條），**不得**把它們算進本票。
- **每批收尾**：commit → 背景 push → 更新 `白話說明/現在做到哪.md` 與
  `白話說明/SPLITUNIFY施工進度.md`（細項逐條，使用者 2026-09-10 定）。

---

## §B 批次執行策略

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B1** | 1.1, 1.2 | consult 收斂 | 文件與枚舉 SoT；**不動生產碼**（可獨立審） | 小 |
| **B2** | 2.1, 2.2 | B1 | 純函式＋golden 同批（golden 要有函式才凍得出來）；**仍不接線** | 中 |
| **B3** | 3.1, 3.2 | B2 | 接線與 fail-closed 同批（分開會有一段時間邊界不唯一） | 大 |
| **B4** | 4.1 | B3 | 報告與畫面（欄名待 B3 定案後才穩定） | 中 |

Gate：每批 `venv/bin/python -m pytest -q <該批測試檔>` rc=0 且 skip 數為 0；
每批三家 code review 收斂後才進下一批（`review_quorum_check.sh` 機檢）。

---

## §C Task 細目

### Task 1.1 — GAP-3 延伸檔 `D-002`（`票 SPLITUNIFY`）
- SPEC ref：C-6　目標：記錄切分權威變更與投影契約；**不解凍** GAP-3 原檔。
- 輸入 / 輸出：無 → `docs/GAP3_EVENT_UX_SPEC.D-002.md`。
- 實作要點：
  1. 標題與狀態行標明「延伸檔，原檔 FROZEN 不動」。
  2. 內容須含 `split_authority == "kline_holdout"` 字面，並交叉引用 SPEC 之 C-1／C-2／C-3。
  3. 明列「本延伸檔改變了 GAP-3 之哪一條」：事件切分不再自行決定邊界。
- 修改檔案：`docs/GAP3_EVENT_UX_SPEC.D-002.md`（新）。既有 caller：無。
- 不可做：不動 `docs/GAP3_EVENT_UX_SPEC.D-001.md`；不改 GAP-3 原 SPEC。
- 邊界：①原檔已 FROZEN ⇒ 只新增；②延伸檔本身須過格式檢查。
- 風險緩解：⊘
- **驗證**：`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_SPEC.D-002.md` rc=0；
  `grep -c 'kline_holdout' docs/GAP3_EVENT_UX_SPEC.D-002.md` >= 1。
- **存活至**：全票完工後保留。
- **覆蓋風險**：B4 之 UAT 項會追加條目，不刪既有段。

### Task 1.2 — 枚舉單一真相源 `split_unify.json`（`票 SPLITUNIFY`）
- SPEC ref：C-7　目標：三態值集、權威值集、fail-closed reason 一檔定義。
- 輸入 / 輸出：無 → `momentum/Analysis/contracts/split_unify.json`：
  `assignment_states=["train","purged","test"]`、
  `split_authority_values=["kline_holdout"]`、
  `fail_closed_reasons=["multi_symbol_projection_unsupported","missing_train_plan","missing_test_plan"]`。
- 實作要點：
  1. `momentum/Analysis/event_samples/split_projection.py` 之常數由本 JSON 讀取，缺鍵 ⇒ import 期 raise。
  2. 測試以 JSON 對證 Python 常數集合（`==`），兩端不得各自手打。
- 修改檔案：`momentum/Analysis/contracts/split_unify.json`（新）；
  `tests/momentum/Analysis/test_splitunify_contract.py`（新）。既有 caller：無。
- 不可做：不在 Python 端手打第二份值集；不加第四種 assignment 狀態。
- 邊界：①JSON 缺鍵 ⇒ raise；②值集為空 ⇒ raise。
- 風險緩解：⊘
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_contract.py` rc=0：
  `set(json["assignment_states"]) == {"train","purged","test"}`；刪一個鍵 ⇒ raise（可證偽）。
- **存活至**：全票完工後保留（前端亦讀）。
- **覆蓋風險**：B3 若發現新 fail-closed 情形會**追加** reason 值，不改既有值。

### Task 2.1 — `derive_event_split_from_plans` 純函式（`票 SPLITUNIFY`）
- SPEC ref：C-3、C-4　目標：由 train／test 兩 plan 導出三態投影。
- 輸入 / 輸出：`(train_plan: SplitPlan, test_plan: SplitPlan, event_index: pd.Index)` → `EventSplitPlan`。
- 實作要點：
  1. 事件時間戳 ∈ train 之列 ⇒ `train`；∈ test ⇒ `test`；皆不在 ⇒ `purged`。
  2. 三態**互斥且涵蓋全集**；同時落在 train 與 test（不應發生）⇒ raise（不靜默取一）。
  3. `clusters` 沿用既有 `event_split.py` 之連通分量定義，只換輸入來源。
  4. 純函式：無 log、無 I/O、不讀 config、不改輸入。
- 修改檔案：`momentum/Analysis/event_samples/split_projection.py`（新）。既有 caller：無（B3 接）。
- 不可做：不得在此讀 config；不得自算 purge／embargo；不得回退成二態。
- 邊界：①`event_index` 為空 ⇒ 三態皆空（不 raise）；②同時落兩態 ⇒ raise；
  ③全部落在隔離區 ⇒ `train`／`test` 皆空而 `purged` 為全集。
- 風險緩解：mutation ①（二態化）。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` rc=0：
  三態交集為空且 `len(train)+len(purged)+len(test) == len(event_index)`；
  purged 事件不出現在 train／test；空 index、單事件、全 purged 三個邊界各一條。
- **存活至**：全票完工後保留（唯一投影實作）。
- **覆蓋風險**：B3 只增加 caller，不改本函式簽名。

### Task 2.2 — golden 凍結（G-1／G-3／G-4）（`票 SPLITUNIFY`）
- SPEC ref：§G　目標：成員集合、雙 producer 差集、per-symbol counts 三份 golden。
- 輸入 / 輸出：既有事件批 → `tests/golden/splitunify/*.json`。
- 實作要點：
  1. `scripts/freeze_splitunify_golden.py`：`--write` 凍結、預設比對；比對失敗 rc=1 並**指名差集**。
  2. G-3 雙 producer：同一批分別走 `split_events`（舊）與 `derive_event_split_from_plans`（新），
     逐欄比對並記錄差集——**預期有差**（SPEC C-2 已證不等價），故本 golden 記錄的是「差在哪」。
- 修改檔案：`tests/golden/splitunify/*.json`（新）；`scripts/freeze_splitunify_golden.py`（新）。
- 不可做：比對失敗時不得自動 `--write` 覆蓋（那等於沒有 golden）。
- 邊界：①首次凍結（檔不存在）⇒ 只有 `--write` 可建；②比對模式缺檔 ⇒ rc=1。
- 風險緩解：⊘
- **驗證**：`venv/bin/python scripts/freeze_splitunify_golden.py` rc=0；
  手改 golden 內一個成員 ⇒ rc=1 且輸出含該成員名（可證偽自證，同
  `scripts/freeze_evtlabel_survivor_golden.py` 之作法）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：B3 接線後 G-1 之值**預期改變** ⇒ 以 `--write` 重凍並在 commit 訊息逐項記錄
  差異來源；不得靜默覆蓋。

### Task 3.1 — 接線：邊界唯一化（`票 SPLITUNIFY`）
- SPEC ref：C-1　目標：`pipeline`／`orchestrator` 改用投影；`split_events` 不再決定邊界。
- 輸入 / 輸出：`split_context` 之 train／test plan → `EventSplitPlan`（投影）。
- 實作要點：
  1. `pipeline.py` 之事件切分出口改呼叫 `derive_event_split_from_plans`。
  2. `split_events` 保留為**歷史路徑**，但不再被生產路徑呼叫（測試釘住呼叫點數＝0）。
  3. 缺 train 或 test plan ⇒ fail-closed（reason 出自 `split_unify.json`）。
- 修改檔案：`momentum/Analysis/event_samples/pipeline.py`、`momentum/Analysis/ic_filter_orchestrator.py`。
  既有 caller：`ic_feed.py`、`tables.py`、`baseline.py`（只讀 `EventSplitPlan`，型別不變）。
- 不可做：不改 `derive_event_split_from_plans` 之簽名；不在 caller 端補算切分。
- 邊界：①非事件 run 不走投影（G-2）；②缺 plan ⇒ fail-closed。
- 風險緩解：G-2、G-3。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis tests/momentum/event_samples` 之
  failed 數 **<= 20**（既有紅基準，見 `HANDOFF.md`）；
  `venv/bin/python scripts/freeze_evtlabel_survivor_golden.py` rc=0（G-2 未漂移）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：B4 只加 metadata 欄位，不改接線。

### Task 3.2 — 多 symbol fail-closed（`票 SPLITUNIFY`）
- SPEC ref：C-2　目標：per-symbol 投影未支援前，多 symbol 批一律 raise。
- 實作要點：
  1. `len({p.symbol for p in (train_plan, test_plan) if p.symbol}) > 1` 或事件批含多 symbol
     ⇒ `raise ValueError("multi_symbol_projection_unsupported: …")`。
  2. reason 字面自 `split_unify.json` 讀，不手打。
- 修改檔案：`momentum/Analysis/event_samples/split_projection.py`、
  `tests/momentum/Analysis/test_splitunify_derive.py`。
- 不可做：不得以警告放行（fail-open）；不得以第一個 symbol 之 plan 冒充整批。
- 邊界：①單 symbol 批不受影響；②`symbol` 為 None ⇒ 視為單標的（既有語意）。
- 風險緩解：mutation ②③。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k multi_symbol`
  rc=0：兩 symbol 批 ⇒ raise 且訊息含 `multi_symbol_projection_unsupported`；
  單 symbol 批 ⇒ 不 raise。
- **存活至**：per-symbol 投影實作後**改寫**為支援分支（SPEC §N R-1）。
- **覆蓋風險**：本 Task 之 raise 分支預期被未來的 per-symbol 支援取代——屆時須連測試一起改，
  不得只刪 raise。

### Task 4.1 — 報告與前端只暴露一個驗證段（`票 SPLITUNIFY`）
- SPEC ref：C-5　目標：`metadata` 只寫 canonical `n_test` 與其來源揭露。
- 輸入 / 輸出：投影結果 → `metadata.split_unify = {n_test, split_authority, boundary_hash,
  per_symbol_counts, reason}`。
- 實作要點：
  1. `boundary_hash` ＝ canonical 測試段時間戳之 `sha256`（sorted、int64 ms、無空白 JSON）。
  2. fail-closed 時 `n_test` 為 `null` 而非 `0`（不顯示假數字）。
  3. 前端顯示單一數字＋來源標籤；`splitAuthority.test.ts` 對證值集。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py`、
  `frontend/src/lib/types.ts`、`frontend/src/components/ic-analysis/`。
- 不可做：不同時暴露兩個驗證段數字；fail-closed 時不填 0 冒充。
- 邊界：①全域 run 不寫這些鍵（G-2）；②fail-closed ⇒ `n_test` 為 null。
- 風險緩解：⊘
- **驗證**：`venv/bin/python -m pytest -q tests/api/test_splitunify_disclosure.py` rc=0：
  報告中含「驗證段列數」語意之鍵**恰 1 個**；`split_authority == "kline_holdout"`；
  `cd frontend && node_modules/.bin/vitest run src/lib/splitAuthority.test.ts` rc=0。
- **存活至**：全票完工後保留（UAT 交付物）。
- **覆蓋風險**：無後續 Phase。

---

## §D mutation 對照表（自證；每批收案前跑）

| ID | 改壞什麼 | 應紅之測試 |
|---|---|---|
| `M-SU-1` | 投影二態化（`purged` 併入 `train`） | `test_splitunify_derive.py -k three_state` |
| `M-SU-2` | 多 symbol fail-closed 拿掉 | `test_splitunify_derive.py -k multi_symbol` |
| `M-SU-3` | 以第一個 symbol 之 plan 冒充整批 | `test_splitunify_derive.py -k multi_symbol` |
| `C0` | 只改註解（對照組） | 必須仍綠 |
