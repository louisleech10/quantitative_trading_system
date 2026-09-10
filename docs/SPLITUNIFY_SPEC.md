# SPLITUNIFY — SPEC

> **狀態（2026-09-10 深夜）**：v1 草案。切法已由**委員會 consult 定共識**
> （使用者 2026-09-10 裁定「切法由你跟委員討論共識」，並於離線時再次指示
> 「有問題找委員會討論共識」）⇒ 本 SPEC 直接依共識撰寫，**不再回頭問使用者**。
> consult 收斂檔：`handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`（commit `9f75e4a7`）。
> 前置票 `EVTLABEL` 已收（三 Phase、17 Task、四批三家審全收斂、四個 gate 全 PASS）。

## §A 假設與待使用者確認

**已確認（使用者回覆 2026-09-10）**：
1. 「但要如何切分，你跟委員要討論共識」——**切法交委員會定，不回頭問使用者**。
2. 「SPLITUNIFY 排 EVTLABEL 之後、UAT 之前」（使用者選 B）。
3. 「我要睡了，你繼續做完，有問題找委員會討論共識，做完前不要停下來」（2026-09-10 深夜離線授權）。

**待使用者確認：無。** 本票之唯一設計決策（切法）已由使用者明示授權委員會定案，
共識已收斂於 `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`。
UAT 項目之最終確認屬 B4，且使用者已裁定 UAT 一律最後。

## §A2 目標與問題

**問題**：平台現在有**兩套切分**，同一批事件會得到**兩個不同的驗證段**（實測 31 vs 33）。

| | 事件切分（GAP-3） | 時間切分（IC 主線） |
|---|---|---|
| 切什麼 | **事件**分訓練／驗證（每 symbol 各自按時間切，緩衝 ≥ 答案窗） | **K 線列**分訓練／驗證 |
| 隔離 | 緩衝 bars | `purge` ＋ `embargo`（EVTLABEL Task 2.2 後 purge 吃答案窗） |
| 型別 | `EventSplitPlan`（`momentum/Analysis/event_samples/types.py:87`） | `SplitPlan`（`momentum/core/contracts.py:378`） |
| 產生者 | `event_samples/event_split.py::split_events` | `ic_filter_orchestrator._build_holdout_split_plan` |

為什麼非統一不可：使用者 UAT 時會在同一份報告看到兩個 OOS 段數字，無法判斷哪一個
才是結論的依據；下游（倖存者檔、`pattern_bridge`）也可能各自綁到不同那一套。
（`template_check` 之空殼偵測把行首 `**` 當 bullet ⇒ 本段刻意不以粗體起首。）

目標：**一個批次只有一條 OOS 邊界**，報告只暴露那一個數字，並揭露它的來源與 sha256。

## §RISK 風險分級

RISK-HIT: a,b,c,d

**大票**，命中四項高風險原則（三家一致）：
(a) 數值／資料品質——切分邊界直接決定 OOS 數字；
(b) 跨模組／共用路徑——7 個生產檔＋6 個測試檔在用 `EventSplitPlan`；
(c) 多 phase／難回退——動到 GAP-3 已 FROZEN 之規格（走延伸檔）；
(d) 切分正確性——本票的全部內容就是切分。

## §C 約束（委員會共識，逐條可追溯到 consult finding）

### C-1 canonical 權威＝時間切分（D1；三家一致）
K 線 holdout（`SplitPlan`，含 purge／embargo）為**唯一邊界來源**；
`EventSplitPlan` 降為**投影容器**，其 `assignments`／`purged`／`clusters`／`summary`
一律由 canonical 邊界衍生，**不再自行決定邊界**。

理由：隔離語意（purge／embargo）住在時間切分那一側；事件側只有「緩衝 bars」，較弱。

### C-2 🔴 邊界必須 per-symbol，禁全域 scalar 冒充（D2；codex 與 composer **各自標 P0**）
**不得**以全域 scalar `SplitPlan.test_timestamps` 交集取代事件計畫。

**實測證據**（`handoffs/20260910-probe-splitunify-multisymbol.py`，
receipt `20260910T150504Z-splitunify-multisymbol`）：兩 symbol 交錯之 80 列批次，
全域切法測試段 **12 列**、per-symbol 切法 **8 列**，**4 列只在全域**
⇒ 兩者**不等價**。這是我在 consult brief 自列為 `assumed`／「沒跑」的假設，
派審後自跑即被推翻。

⇒ 邊界以 `split_per_symbol`（`momentum/core/contracts.py` 既有）逐標的產生；
多 symbol 批在 per-symbol 投影完成前**一律 fail-closed**（grok），
**禁**以第一個 symbol 之 holdout（`next(iter(allowed_symbols))`）冒充整批。

### C-3 投影是**三態**不是二態（D3；grok）
投影須用 **train 與 test 兩個 plan** 導出 **train／purged／test 三態**。

理由：落在隔離區（purged）的事件**既不屬訓練也不屬驗證**；二態（在／不在測試段）
會把它們錯誤地歸進其中一邊，等於把被隔離的樣本偷偷放回訓練集。

### C-4 投影是純函式、單一實作
`derive_event_split_from_plans(train_plan, test_plan, event_index) -> EventSplitPlan`
為**唯一**實作；純函式、無 I/O、不讀 config。**禁**任何第二份切分算術
（EVTLABEL B3 review 之教訓：兩份算術必漂）。

### C-5 報告只暴露一個驗證段數字（D5；codex）
`metadata` 只寫 canonical 之 `n_test`，並附：
`split_authority`（固定 `"kline_holdout"`）、`boundary_hash`、`per_symbol_counts`、
以及 fail-closed 時的 `reason`。**禁**同時暴露兩個數字。

### C-6 GAP-3 走延伸檔，不解凍原檔（D4；三家一致）
新增 `docs/GAP3_EVENT_UX_SPEC.D-002.md` 記錄切分權威之變更與投影契約。

### C-7 新資料結構走 JSON 單一真相源
投影之三態值集、`split_authority` 值集、fail-closed reason 枚舉集中於
`momentum/Analysis/contracts/split_unify.json`；Python 與前端各自對證，禁散文複列。

## §G Golden / Baseline

- **G-1 成員集合 golden**：改前／改後之 `assignments` 成員集合逐一凍結。
  🔴 **預期會變**（C-2 已證不等價）⇒ 改後不同時**必須明示接受**並記錄差異來源，
  不得靜默覆蓋（grok 要求）。
- **G-2 全域路徑逐位元組不變**：非事件 run 之報告 canonical bytes 之 **sha256** 不得改變
  （比對方式同 `scripts/freeze_evtlabel_survivor_golden.py`：去 `generated_at` 後 `sha256`）。
- **G-3 雙 producer golden**：同一批分別走「舊事件切分」與「新投影」，
  逐欄比對並記錄差集（codex 要求）。
- **G-4 per-symbol counts golden**：多 symbol 批之逐標的計數（整數逐值相等，非 atol 比較）。
- **數值比較規約**：計數類一律**整數逐值相等**；若未來出現浮點欄位，
  以 `atol=1e-12`／`rtol=1e-9` 比較（同 `test_binary_discrimination.py` 之既有規約）。

## §P Phase 與依賴（四批；三家一致「大」，批數取較保守者）

| 批 | Task | 依賴 | 產出 |
|---|---|---|---|
| **B1** | Task 1.1、1.2 | consult 收斂 | 文件與枚舉 SoT；**不動生產碼** |
| **B2** | Task 2.1、2.2 | B1 | 純函式與 golden；**仍不接線** |
| **B3** | Task 3.1、3.2 | B2 | 邊界唯一化 |
| **B4** | Task 4.1 | B3 | 報告與畫面 |

每批三家 code review、commit+push、更新白話看板。

**Task 1.1 — GAP-3 延伸檔 `D-002`**
- 目標：記錄切分權威之變更與投影契約；**不解凍** GAP-3 原檔（C-6）。
- 修改檔案：`docs/GAP3_EVENT_UX_SPEC.D-002.md`（新）。既有 caller：無。
- 不可做：不動 `docs/GAP3_EVENT_UX_SPEC.D-001.md`。
- **驗證**：`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_SPEC.D-002.md` rc=0；
  延伸檔須含 `split_authority == "kline_holdout"` 之字面與本 SPEC 之 C-1／C-2／C-3 交叉引用。
- 邊界：①原檔已 FROZEN ⇒ 只新增延伸檔；②延伸檔本身亦須過 `doc_format_precheck`。
- **存活至**：全票完工後保留（GAP-3 之規格鏈）。
- **覆蓋風險**：B4 之 UAT 項會**追加**條目至本延伸檔，不刪既有段。

**Task 1.2 — 枚舉單一真相源 `split_unify.json`**
- 目標：三態值集、`split_authority` 值集、fail-closed reason 枚舉一檔定義（C-7）。
- 輸出：`momentum/Analysis/contracts/split_unify.json`：
  `assignment_states=["train","purged","test"]`、`split_authority_values=["kline_holdout"]`、
  `fail_closed_reasons=["multi_symbol_projection_unsupported","missing_train_plan","missing_test_plan"]`。
- 修改檔案：`momentum/Analysis/contracts/split_unify.json`（新）；
  `tests/momentum/Analysis/test_splitunify_contract.py`（新）。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_contract.py` rc=0：
  JSON 之 `assignment_states` 與 Python 常數集合逐值相等（`==`）；缺鍵 ⇒ raise。
- 不可做：不在 Python 端手打第二份值集；不加第四種 assignment 狀態。
- 邊界：①JSON 缺鍵 ⇒ import 期 raise；②Python 端不得手打第二份值集。
- **存活至**：全票完工後保留（下游前端亦讀）。
- **覆蓋風險**：B3 若發現新的 fail-closed 情形，會**追加** reason 值，不改既有值。

**Task 2.1 — `derive_event_split_from_plans` 純函式**
- 目標：由 train／test 兩 plan 導出三態投影（C-3、C-4）。
- 輸入 / 輸出：`(train_plan: SplitPlan, test_plan: SplitPlan, event_index: pd.Index)`
  → `EventSplitPlan`（`assignments`／`purged`／`clusters`／`summary` 皆由邊界衍生）。
- 實作要點：事件時間戳 ∈ train 之列 ⇒ `train`；∈ test ⇒ `test`；兩者皆不在 ⇒ `purged`。
  三態**互斥且涵蓋全集**。純函式、無 I/O、不讀 config。
- 修改檔案：`momentum/Analysis/event_samples/split_projection.py`（新）。既有 caller：無（B3 接）。
- 不可做：不得在此讀 config、不得自算 purge／embargo。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` rc=0：
  三態集合之交集為空且聯集 == `len(event_index)`；purged 事件不出現在 train／test；
  空 plan ⇒ 全部 `purged`；單事件與全部落隔離區兩個邊界各一條。
- 邊界：①`event_index` 為空 ⇒ 回三態皆空之 `EventSplitPlan`（不 raise）；
  ②事件時間戳同時落在 train 與 test（不應發生）⇒ raise（fail-closed，不靜默取一）；
  ③`clusters` 於三態下之定義沿用既有 `event_split.py` 之連通分量，只換輸入。
- **存活至**：全票完工後保留（唯一投影實作）。
- **覆蓋風險**：B3 只增加 caller，不改本函式簽名。

**Task 2.2 — golden 凍結（G-1／G-3／G-4）**
- 目標：改前／改後成員集合、雙 producer 差集、per-symbol counts 三份 golden。
- 修改檔案：`tests/golden/splitunify/*.json`（新）；`scripts/freeze_splitunify_golden.py`（新）。
- **驗證**：`venv/bin/python scripts/freeze_splitunify_golden.py` rc=0（比對模式）；
  改一個成員 ⇒ rc=1 並指名差集（可證偽自證）。
- 不可做：不得在比對失敗時自動 `--write` 覆蓋（那等於沒有 golden）。
- 邊界：①golden 不存在（首次凍結）⇒ `--write` 模式建立；②比對模式下缺檔 ⇒ rc=1。
- **存活至**：全票完工後保留。
- **覆蓋風險**：B3 接線後 G-1 之值**預期改變**（C-2 已證不等價）⇒ 屆時以 `--write` 重凍並在
  commit 訊息逐項記錄差異來源；不得靜默覆蓋。

**Task 3.1 — 接線：邊界唯一化**
- 目標：`pipeline`／`orchestrator` 改用投影，`split_events` 不再決定邊界（C-1）。
- 修改檔案：`momentum/Analysis/event_samples/pipeline.py`、
  `momentum/Analysis/ic_filter_orchestrator.py`。既有 caller：`ic_feed.py`、`tables.py`、`baseline.py`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis tests/momentum/event_samples` 之
  既有紅**不增加**（基準見 `HANDOFF.md`「既有紅盤點」20 條）；G-2 全域 golden 逐位元組不變。
- 不可做：不改 `derive_event_split_from_plans` 之簽名；不在 caller 端補算切分。
- 邊界：①非事件 run 不走投影（G-2 逐位元組不變）；②缺 train 或 test plan ⇒ fail-closed。
- **存活至**：全票完工後保留。
- **覆蓋風險**：B4 只加 metadata 欄位，不改接線。

**Task 3.2 — 多 symbol fail-closed**
- 目標：per-symbol 投影未支援前，多 symbol 批一律 raise（C-2）。
- 實作要點：`len({p.symbol for p in plans}) > 1` 且未走 per-symbol ⇒
  `raise ValueError("multi_symbol_projection_unsupported: …")`（reason 字面出自 Task 1.2 之 JSON）。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k multi_symbol`
  rc=0：兩 symbol 批 ⇒ raise 且訊息含 `multi_symbol_projection_unsupported`。
- 不可做：不得以警告放行（fail-open）；不得以第一個 symbol 之 plan 冒充整批。
- 邊界：①單 symbol 批不受影響；②`symbol` 欄為 None 之 plan 視為單標的（既有語意）。
- **存活至**：per-symbol 投影實作後**改寫**為支援分支（見 §N R-1）。
- **覆蓋風險**：本 Task 之 raise 分支預期被未來的 per-symbol 支援取代——屆時須連同測試一起改，
  不得只刪 raise。

**Task 4.1 — 報告與前端只暴露一個驗證段**
- 目標：`metadata` 只寫 canonical `n_test`＋`split_authority`＋`boundary_hash`＋
  `per_symbol_counts`＋fail-closed `reason`（C-5）。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py`（metadata 寫入）、
  `frontend/src/components/ic-analysis/`（顯示）、`frontend/src/lib/types.ts`。
- **驗證**：`venv/bin/python -m pytest -q tests/api/test_splitunify_disclosure.py` rc=0：
  報告中「驗證段列數」之鍵**恰一個**；`split_authority == "kline_holdout"`；
  `cd frontend && npx vitest run src/lib/splitAuthority.test.ts` rc=0。
- 不可做：不同時暴露兩個驗證段數字；fail-closed 時不填 0 冒充。
- 邊界：①fail-closed 時 `n_test` 為 null 而非 0（不顯示假數字）；②全域 run 不寫這些鍵。
- **存活至**：全票完工後保留（UAT 交付物）。
- **覆蓋風險**：無後續 Phase。

## §V 驗證策略與邊界測試目錄

- `tests/momentum/Analysis/test_splitunify_derive.py`（B2）：三態互斥且涵蓋全集；
  purged 事件不得出現在 train 或 test；空 plan／單事件／全部落在隔離區三個邊界。
- **mutation**：①投影改成二態（purged 併入 train）⇒ 必紅
  ②多 symbol 之 fail-closed 拿掉 ⇒ 必紅 ③以第一個 symbol 冒充整批 ⇒ 必紅。
- **benchmark**：投影為 O(n log n) 以內；10k 事件 < 2 秒。

## §R 回退

投影函式與接線分屬 B2／B3 兩批 ⇒ B3 回退即可回到雙軌狀態（B2 之純函式無 caller、無副作用）。

## §N N/A 登記與殘留

- **R-1（needs-research）**：per-symbol `SplitPlan` 之 `base_universe_hash` 語意在多標的下
  是否仍唯一——本票先 fail-closed，不在此解。
- **R-2（blocked-by）**：`baseline.py` 之 OOS AUC 是否因投影而改變數值——
  待 B2 之 G-3 雙 producer golden 實跑後才有答案，屆時若變則登記為預期差異。
- **R-3（user-ruling）**：UAT 項目之更新等 B4；使用者已裁定 UAT 一律最後。
