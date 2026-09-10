# SPLITUNIFY — SPEC

> **狀態（2026-09-11 凌晨）**：**v5（B1 放行版）**。R4 定向確認輪收斂檔：
> `handoffs/reconcile/20260911-splitunify-x-review-r4/synth.md`（F1–F4）——三家對「哪裡還沒
> 寫清楚」一致，只在「是否擋 B1」分歧；主委兩者都採：**先修（codex 立場）但不再開一輪
> （另兩家對嚴重度的判斷）**，因為 codex 已把三條的修法寫成可直接落地的式子。
> 收斂趨勢 R1 13(3 P0) → R2 11(3 P0) → R3 7(0 P0) → R4 4(0 P0)，套用 v5 後**進 B1**。
> R3 三家審收斂檔：
> `handoffs/reconcile/20260911-splitunify-x-review-r3/synth.md`（**E1–E7**）。
> 🔴 R3 三家分歧（composer／grok 判「可進 B1」、codex 判「不可」），
> 依「看碼證不數人頭」採 codex——其 `CODEX-R3-P1-02` 指出 v3 的投影
> **把既有的答案窗 purge 規則整個弄丟了**（`event_split.py:114`），
> 那是事件側唯一擋標籤窗跨界洩漏的閘，且違反 C-1 附帶約束①「不得刪除任一既有 guard」。
> v4 以**兩段式判定**修復（見 C-4）。
> R2 三家審收斂檔：
> `handoffs/reconcile/20260911-splitunify-x-review-r2/synth.md`（**D1–D11**，三家 verdict
> 一致「不可直接進 B1」，17 條 findings 全數採納）；主委自產 R2 審查
> `handoffs/20260911-splitunify-claude-selfreview-r2.md`。
> 切法已由**委員會 consult 定共識**
> （使用者 2026-09-10 裁定「切法由你跟委員討論共識」，並於離線時再次指示
> 「有問題找委員會討論共識」）⇒ 本 SPEC 直接依共識撰寫，**不再回頭問使用者**。
> consult 收斂檔：`handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`
> （**D1–D8**；body-hash `120b4d042d38…`；**三家 RECONCILE-STAMP 全數 APPROVED**，
> `scripts/reconcile_stamps_check.sh` rc=0）。
> R1 三家審收斂檔：`handoffs/reconcile/20260911-splitunify-x-review-r1/synth.md`（C1–C13）。
> 主委自產審查：`handoffs/20260911-splitunify-claude-selfreview.md`（`CLAUDE-R1-*` 8 條）。
> 前置票 `EVTLABEL` 已收（三 Phase、17 Task、四批三家審全收斂、四個 gate 全 PASS）。

## §A 假設與待使用者確認

**已確認（使用者回覆 2026-09-10）**：
1. 「但要如何切分，你跟委員要討論共識」——**切法交委員會定，不回頭問使用者**。
2. 「SPLITUNIFY 排 EVTLABEL 之後、UAT 之前」（使用者選 B）。
3. 「我要睡了，你繼續做完，有問題找委員會討論共識，做完前不要停下來」（2026-09-10 深夜離線授權）。

**待使用者確認：無。** 本票之唯一設計決策（切法）已由使用者明示授權委員會定案。
UAT 項目之最終確認屬 B4，且使用者已裁定 UAT 一律最後。

## §A2 目標與問題

問題：平台現在有**兩個入口各自產切分**，同一批事件會得到**兩個互相矛盾的驗證段數字**。

| | 事件掃描入口 | IC 分析入口 |
|---|---|---|
| service | `EventImportService`（`api/services/case_import_service.py:1610`） | `ICAnalysisService` → `ic_filter_orchestrator.analyze` |
| 切什麼 | **事件**（每 symbol 各自按時間切，緩衝 ≥ 答案窗） | **特徵列**（chronological holdout） |
| 隔離 | 毫秒 `embargo`（`event_split.py:104-117`） | `purge` ＋ `embargo` 列數（EVTLABEL Task 2.2 後 purge 吃答案窗） |
| 型別 | `EventSplitPlan`（`momentum/Analysis/event_samples/types.py`） | `SplitPlan`（`momentum/core/contracts.py:378`） |
| 產生者 | `event_split.py::split_events`（唯一呼叫點 `pipeline.py:691`） | `_build_holdout_split_plan`（`ic_filter_orchestrator.py:561`，呼叫點 `:1256`） |
| 使用者看到的數字 | `summary.split` 之 `n_train`／`n_test`／`n_purged`（`pipeline.py:696-699`） | `split_context["test_events"]`（`ic_filter_orchestrator.py:3594`） |

🔴 兩者**不存在單一合併點**——分屬兩個 service、兩個 endpoint。
所以問題的精確描述是：**同一批事件、同一次 UAT 會看到兩個互相矛盾的驗證段數字**，
而不是「同一份報告裡有兩個欄位」（`CLAUDE-R1-P2-08`）。
（`template_check` 之空殼偵測把行首 `**` 當 bullet ⇒ 本段刻意不以粗體起首。）

目標：**一個批次只有一條 canonical OOS 邊界**；報告只暴露一個「驗證段」數字，
並揭露它的來源與 sha256；拿不到 canonical 邊界的路徑**明示 `event-study-only`**，不給假數字。

## §RISK 風險分級

RISK-HIT: a,b,c,d

**大票**，命中四項高風險原則（三家一致）：
(a) 數值／資料品質——切分邊界直接決定 OOS 數字，且 D8 已證數值**必變**；
(b) 跨模組／共用路徑——7 個生產檔＋6 個測試檔在用 `EventSplitPlan`，跨兩個 service；
(c) 多 phase／難回退——動到 GAP-3 已 FROZEN 之規格（走延伸檔）；
(d) 切分正確性——本票的全部內容就是切分。

## §C 約束（逐條可追溯到 consult 之 D 項或 R1 審之 C 群集）

### C-0 🔴 接線落點：單一 boundary builder，拿不到 universe 就不得宣稱 OOS（D6）

來源：`CODEX-R1-P1-04`＋`COMPOSER-R1-P2-02`＋主委自產之 `CLAUDE-R1-P0-01`。
這是本票的**先決條件**。v1 把投影寫在一個拿不到 `SplitPlan` 的地方，等於沒有落點。

碼證：`split_events` 唯一呼叫點 `pipeline.py:691`，輸入只有 `EventManifest`＋`EventSplitConfig`
（`types.py`），兩者皆無 `SplitPlan` 欄；唯一生產 caller `case_import_service.py:1610` 之
`run_with_params` 參數只有 `test_fraction`／`embargo_ms`／`tier_min_test_events`
（`pipeline.py:507-517`），且不帶 `feature_config` ⇒ `_materialize` 回 `None`（`pipeline.py:654-657`）。
IC 側 `SplitPlan` 在另一個 service 建立，R1／R4 解耦規則擋住直接傳遞。

決議：
1. canonical 邊界由 **core 之 pure temporal-boundary builder** 產生，住
   `momentum/core/split_preview.py`（該檔已有 `holdout_split_point`／`holdout_test_row_index`
   兩支被兩端共用之先例，且檔頭已載明「同一算術、無副作用」之定位）。
2. `orchestrator` 與 `pipeline` **共同呼叫**它；`pipeline` **接受（選填）** canonical boundary
   與其所依之 feature universe，**不得自行重算**。
   🔴 **R2 之 D1 裁定**：IC 路徑會傳；**事件掃描路徑本票不傳**——`EventImportService`
   目前完全不碰 FF run（`case_import_service.py:1588-1613` 只有 bars 與切分參數），
   要讓它拿到 universe 得新增 `features_run_id` 之跨棧參數（請求模型、前端、契約、UAT 全動），
   **超出本票範圍**。⇒ 事件掃描端**恆走**決議③之 event-study-only；
   「新增 universe 供給路徑」列為具名殘留 `R-5`。
3. 🔴 **沒有 canonical feature universe 的獨立匯入流程，只能明示 `event-study-only`，
   不得按事件數另切並宣稱 OOS**。沿用現行 `pipeline.run_event_study_only()` 與
   `case_import_service.py:1618-1619` 之 `capability={"split":"unavailable", "reason": …}` 形態，
   但**必須連帶做三件事**（R2 之 D2／D4／D5，缺一即等於留下假 OOS 數字）：
   - (a) **刪除** `run_event_study_only` 現行寫死的 `n_train`／`n_test`／`n_purged`
     （`pipeline.py:728-734` 目前全寫 `0`）；既有 `lookahead_split_blocked` 路徑與新 reason
     **共用同一個新形狀**。不刪就與「summary 不得出現這三鍵」直接矛盾。
   - (b) `event_forward_return_table` 之 `common` 須含
     `estimand_scope="full_sample_not_oos"`——該表在 `split_plan=None` 時
     **確實跑全 manifest 事件**（`tables.py:211-238`，無 `split_label=="test"` 過濾），
     只有 `ci` 與 `formal_pooled_inference_allowed` 被降級，**表身數字沒有任何非 OOS 標籤**。
   - (c) 事件掃描頁**必須**渲染 `capability.split` 與 `capability.reason`
     （現行 `EventTablesPanel.tsx:302` 收回應、`:352` 只渲 summary 計數，全文無
     `resp.capability`）；`split == "unavailable"` 時**禁再顯示** train/test/purge 計數列。

實測支撐（否證了「兩端各自用同一公式算」這條看似合理的捷徑）：
探針 `handoffs/20260911-probe-splitunify-universe-gap.py`、
receipt `handoffs/run_receipts/20260910T154323Z-splitunify-universe-gap.log`（rc=1）——
真實 ETHUSDT 1h（FF run `4a8a0b3726cc906ab3534994605e77f5`，20352 列）未裁切時
features 與 bars 兩 universe 逐值相同；EVTALIGN 裁頭尾後邊界位移：
5 根 → 2 小時、24 根 → 10 小時、168 根 → 67 小時。⇒ 必須共用 universe，不是共用公式。

### C-1 canonical 權威＝時間切分（D1）
K 線 holdout（`SplitPlan`，含 purge／embargo）為**唯一邊界來源**；
`EventSplitPlan` 降為**投影容器**，其 `assignments`／`purged`／`clusters`／`summary`
一律由 canonical 邊界衍生，**不再自行決定邊界**。

理由：**所有 row／event projection 共用同一 canonical boundary**——單一邊界來源本身就是目的。

🔴 **明確不採用**的理由：「時間切分之 purge／embargo 嚴格強於事件側緩衝 bars」。
`CODEX-R1-P1-02` 正面反駁：兩套隔離**不是同一個集合**，**containment 未被證明**。
附帶約束：① 未證明 containment 前**不得刪除任一既有 guard**；
② §G 須同時 golden 四項（見 G-5）。

「兩套都保留但標主從」已由 `GROK-R1-P2-03` 判為**反模式**，明文否決：
標主從不刪除第二份算術，兩個數字仍會分歧。

### C-2 🔴 邊界必須 per-symbol，禁全域 scalar 冒充（D2；codex 與 composer **各自標 P0**）
**不得**以全域 scalar `SplitPlan.test_timestamps` 交集取代事件計畫。

實測證據（`handoffs/20260910-probe-splitunify-multisymbol.py`，
receipt `20260910T150504Z-splitunify-multisymbol`）：兩 symbol 交錯之 80 列批次，
全域切法測試段 **12 列**、per-symbol 切法 **8 列**，**4 列只在全域** ⇒ 兩者**不等價**。

⇒ 邊界以 `split_per_symbol`（`momentum/core/contracts.py:625` 既有）逐標的產生；
多 symbol 批在 per-symbol 投影完成前**一律 fail-closed**，
**禁**以第一個 symbol 之 holdout（`ic_filter_orchestrator.py:1248` 之
`next(iter(allowed_symbols))`）冒充整批。

### C-3 三態＝**兩個容器**，不是三值枚舉（D3；`CLAUDE-R1-P0-02`）
投影須用 **train 與 test 兩個 plan** 導出 **train／purged／test 三態**：
落在隔離區的事件**既不屬訓練也不屬驗證**，二態會把它們錯誤地歸進其中一邊。

🔴 但三態**已經是既有結構**，不是本票新引入的：`EventSplitPlan` 之
`assignments`（`split_label` ∈ `{train, test}`）＋**獨立**的 `purged`（`event_id`, `reason`）。
只認兩值的消費者：`pipeline.py:697-698`、`baseline.py:106`、`tables.py:305`、
`pattern_bridge.py:115,125-127`——多出第三值時這些位置**不報錯，只靜默少算**。

⇒ 投影**必須維持既有容器形狀**：train／test 進 `assignments`，被隔離者進 `purged`，
reason 沿用契約既有字面 `interval_crosses_split_boundary`
（`momentum/Analysis/contracts/event_import_contract.json:465-467` 之 `split_purge_reasons`），
**不得**在 `split_unify.json` 另造 purge reason。

### C-4 投影是純函式、單一實作；簽名須帶 `feature_index` 與 `manifest`
來源：R1 之 C2／C5 群集（grok 與 composer 各自給出同形簽名）。

```python
def derive_event_split_from_plans(
    train_plan: SplitPlan,
    test_plan: SplitPlan,
    event_keys: pd.DataFrame,   # 🔴 keyed 輸入，見下；**不是**裸 pd.Index
    feature_index: pd.Index,    # SplitPlan.row_index 所索引之同一 universe（post-trim）
    *,
    manifest: EventManifest,    # clusters／summary 之來源（decision_at_ms、timeframe）
    bucket_ms: Optional[int] = None,   # time-cluster 桶寬；None ⇒ 觸發 TF 一根（既有語意）
) -> EventSplitPlan
```

🔴 **`event_keys` 之欄位契約（R3 之 E2；`CODEX-R3-P1-01`）**：
必含 `event_id`、`feature_cutoff_ms`、`label_start_ms`、`label_end_ms`、`symbol`、`timeframe`，
且以 **`event_id` 為鍵**與 `manifest.table` 對位——**禁 positional zip**。
理由：`dedupe.py:46` 會依 `(label_start_ms, event_id)` **重排** manifest、
`alignment.py:197-213` 之 feature cutoff 按輸入事件順序且可有多個 `per_tf`
⇒ 用位置對位會**靜默錯分**，連 G-3b 的 oracle 都可能對錯 event。
v3 的 `event_index: pd.Index`（只有時間、無身份）不足以做這件事。

🔴 **producer 具名（R4 之 F2；`CODEX-R4-P1-02`）**：`event_keys` 由 **B2b 的具名 helper**
`build_event_keys(receipts: AlignmentReceipts, *, selected_timeframe: str) -> pd.DataFrame`
產生——以 `receipts.event_level`（id／label／symbol／trigger context）與 `receipts.per_tf`
（`feature_cutoff_ms` 住這裡）依 **`event_id` ＋ 明示的 selected feature timeframe** keyed join。
**B3 只傳遞，不在接線處臨時組裝。**
🔴 保留 `event_id` 單鍵，但**必須要求每事件恰一個 selected `per_tf` row，否則 raise**——
`receipts.per_tf` 每個 `(event_id, sub_tf)` 可有多列；而 `manifest.table` 只 merge trigger
`timeframe`、**沒有** cutoff（`dedupe.py:39-49,101-120`、`types.py:37-40,55-60`）
⇒ **不能**用 manifest 的 timeframe 代替 per-TF cutoff 的 timeframe。
多 TF 之 `(event_id, timeframe)` 複合鍵列為殘留 `SU-RESID-2`。

🔴 **判定順序是兩段式，且先後不可調（R3 之 E1；`CODEX-R3-P1-02`）**：

**第一段——答案窗 purge（interval-aware，優先於一切）**：

```python
train_cutoff = feature_cutoff_ms in as_ms(feature_index[train_plan.row_index])
if test_plan.row_index.size == 0:
    raise ValueError("missing_test_plan: …")        # 先 fail-closed，禁與 None 比較
test_start_ms = as_ms(feature_index[test_plan.row_index[0]])
if train_cutoff and label_end_ms >= test_start_ms:  # 🔴 `>=` 必須保留
    purge(event_id, reason="interval_crosses_split_boundary")
```

🔴 **`purge_gap`／`embargo` 是 row 單位，且已包含在 `test_plan.row_index[0]` 這個起點裡
（`holdout_test_row_index` ＝ `arange(split_point + purge_gap + embargo, n)`）
⇒ 不得再以毫秒相減**。這是 v4 與既有 `event_split.py:114`
（`label_end_ms > test_start - embargo`）的差異來源：舊式的 `test_start` 是**緩衝之前**的
邊界所以要減 embargo；canonical 的 `test_start_ms` 是**緩衝之後**的第一根，減了會重複扣。
（R4 之 F1；式子逐字採 `CODEX-R4-P1-01`。）

**source bars endpoint 之處置**：`label_start_ms`／`label_end_ms` 在 source bars 上是否
**缺 endpoint**，**不進投影簽名**——投影沒有 bars，硬加會逼實作端發明第三個參數。
明定為**上游 alignment 之可證明前置條件**（`AlignmentReceipts` 已持有，
`alignment.py:197-213`）；G-5.3 改用 receipts 驗，**投影不重做**。

🔴 **為什麼這段非有不可**：現行 `event_split.py:114` 逐字就是
`elif int(rec["label_end_ms"]) > test_start - embargo: → purge`——這是事件側
**唯一**擋標籤窗跨界洩漏的閘。v3 的簽名裡沒有 `label_end_ms`，等於把它整個刪掉，
而 C-1 附帶約束①逐字寫著「未證明 containment 前**不得刪除任一既有 guard**」。
少了這段，答案窗已經跨進測試段的 train 事件會**留在 train**＝直接 OOS leakage，
且 G-5.4 的 negative case 永遠測不出來（改 `label_end_ms` 不改集合成員判定的輸入）。

**第二段——集合成員判定（決定 train／test）**：
`feature_cutoff_ms ∈ feature_index[train_plan.row_index]` ⇒ train；
`∈ feature_index[test_plan.row_index]` ⇒ test；兩者皆不在 ⇒ purged。
🔴 **禁**以 `time_bounds` 閉區間取代集合（與 `ic_filter_orchestrator.py:3594`
／`split_preview.count_binary_classes_in_rows` 之集合語意分歧）。
- `index_kind != "positional"` ⇒ **fail-closed**（`SplitPlan.row_index` 在生產 holdout 為
  positional，見 `ic_filter_orchestrator.py:602`）。
- 🔴 **單位歸一（R2 之 D7 更正）**：本票之時鐘一律 epoch **毫秒**。
  **不得**呼叫 `_normalize_ic_time_index`——該函式是**「秒」語意**的 normalizer，
  `ic_filter_orchestrator.py:269-271` 明文 `raise` 「looks like milliseconds, expected epoch seconds」，
  餵毫秒進去會直接爆（v2 同時寫「允許 int64 ms」與「復用該 normalizer」是自相矛盾的介面）。
  正確作法：`pd.to_datetime(values, unit="ms")` 物化後比對 `asi8`，或一律以
  `asi8 // 10**6` 換算成 int64 毫秒後做集合比較。單位判定失敗 ⇒ raise，
  **不得**靜默 0 命中（`split_preview.py:63-79` 已明載此坑：binary 鍵是 epoch ms、
  特徵索引常為 DatetimeIndex，不換算則計數恆 0 且不拋例外）。
- `event_keys.feature_cutoff_ms` 語意＝與 IC 相同之 **feature_cutoff**（`ic_feed.py:36` 之
  `FEATURE_CUTOFF_RULE = "max_close_ms_le_decision_at"`），**不是**裸 `decision_at_ms`。
- 事件時間戳**不在** `feature_index` 集合內（被 EVTALIGN 裁掉、或落在兩根 bar 之間）
  ⇒ **purged**；🔴 **禁 nearest／asof／ffill**。
- 純函式：無 log、無 I/O、不讀 config、不改輸入。
- 同時落在 train 與 test（不應發生）⇒ raise，不靜默取一。

### C-5 投影須產出**完整**的 `EventSplitPlan`（D7）
來源：`CODEX-R1-P1-03`＋`COMPOSER-R1-P1-02`＋`GROK-R1-P2-02`。
最小落地**不是刪除** `EventSplitPlan`。`assignments`／`purged`／`clusters`／`summary` 皆為
下游仍在消費的事件語意（`baseline.py:105-110`、`pattern_bridge.py:114-175`、
`tables.py:305-367`、`tables.py:130-150` 之 `formal_pooled_inference_allowed`）。

- `summary` 之 **12 個必填鍵**（`event_split.py:141-155`，經 `pipeline.py:696` 整包轉出）：
  `n_symbols`／`per_symbol_n`／`n_time_clusters`／`avg_cluster_size`／`degraded`／
  `loso_status`／`insufficient_events_in_test`／`stats_modes`／`n_events_raw`／
  `n_events_effective`／`n_purged`／`bucket_ms`。少一鍵即報告靜默丟欄。
- `clusters` **與切分無關**（`event_split.py:129-140` 只依 `manifest.table["decision_at_ms"]`
  與 `bucket_ms`）⇒ 抽成獨立純函式 `build_time_clusters(manifest, bucket_ms)`，
  行為不變（改前後 byte 級一致），並**保留** `_cluster_weight` 這個既有 mutation seam
  （`event_split.py:36-39` 註明 M5）。
- **空 plan 不得冒充未切分**。
- 投影路徑下 `EventSplitConfig.embargo_ms` 與 `embargo_ms_by_symbol` **必須為 `None`，
  否則 raise**；靜默忽略會讓上游 `case_import_service.py:1606` 算出的 `embargo_applied`
  退化成沒人用的數字（EVTLABEL `CODEX-R1-P1-02` 已踩過一次的形態）。
  🔴 **落點（R2 之 D8 更正）**：該檢查**住呼叫端**（Task 3.1 之接線處），**不在投影內**——
  投影的簽名沒有也不該有 `EventSplitConfig`（它是純函式，不讀 config）。
  v2 把「投影須 raise」與「投影不吃 config」寫在一起，是不可執行的介面。
  `bucket_ms` 則直接進投影簽名（見 C-4），不經 config。

### C-6 報告只暴露一個驗證段數字（D5；codex）
`metadata` 只寫 canonical 之 `n_test`，並附：
`split_authority`（固定 `"kline_holdout"`）、`boundary_hash`、`per_symbol_counts`、
以及 fail-closed 時的 `reason`。**禁**同時暴露兩個數字。
fail-closed 時 `n_test` 為 `null` 而非 `0`（不顯示假數字）。

### C-7 GAP-3 走延伸檔，不解凍原檔（D4）
新增 `docs/GAP3_EVENT_UX_SPEC.D-002.md` 記錄切分權威之變更與投影契約。
🔴 `CODEX-R1-P2-06` 另指出：frozen primary 與 UX extension convention 的**路徑字面不一致**，
D-002 須明寫正確的規格入口路徑，否則派工會選錯入口。
D-002 亦須寫明「投影所用 `feature_index` 為 **post-trim**（EVTALIGN 裁頭尾之後）之 universe」
（`COMPOSER-R1-P2-01`）。

### C-8 新資料結構走 JSON 單一真相源
`split_authority` 值集、fail-closed reason 枚舉集中於
`momentum/Analysis/contracts/split_unify.json`；Python 與前端各自對證，禁散文複列。
🔴 **不含** purge reason——那沿用 `event_import_contract.json`（見 C-3）。

### C-9 統一**會改變數值**，不是純重構（D8；三家一致）
至少影響：`baseline.py:118-161`（`n_test`、prevalence、AUC／PR-AUC、permutation band、BH-FDR）、
`tables.py:305-370`（OOS metrics、macro／micro AUC、cluster CI）、
`pattern_bridge.py:122-218`（fit rows、rules、scores、lift、receipt hash）、
`ic_filter_orchestrator.py:3830-3863`（test intersection 改 `n_pos`／`n_neg` ⇒ 改 `label_mode`）。

⇒ 驗收**必須**對改前後做逐 event ID 集合、逐列 train／test fingerprint、
報告 numeric keys 與 capability reason 的 exact／tolerance diff；
**不得**以「型別不變」宣稱數值不變，也不得以舊 golden 擋投影（`GROK-R1-P2-01`）。

## §G Golden / Baseline

- **G-1 成員集合 golden**：改前／改後之 `assignments`／`purged` 成員集合逐一凍結。
  🔴 **預期會變**（C-2／C-9）⇒ 改後不同時**必須明示接受**並記錄差異來源，不得靜默覆蓋。
- **G-2 全域路徑逐位元組不變**：非事件 run 之報告 canonical bytes 之 **sha256** 不得改變
  （比對方式同 `scripts/freeze_evtlabel_survivor_golden.py`：去 `generated_at` 後 `sha256`）。
- **G-3a 一次性遷移報告**（取代 v1 之「雙 producer golden」）：同一批分別走舊 `split_events`
  與新投影，差集寫入 `handoffs/run_receipts/`，附 `diff_event_ids` 之 sha256 與基數；
  🔴 **不進**預設比對綠徑——凍結一份「預期有差」的 golden 會把已知錯誤合法化
  （`GROK-R1-P1-03`＋`COMPOSER-R1-P1-03`）。
- **G-3b 長期 golden**：新投影 vs **獨立 oracle**——直接由
  `feature_index[train_plan.row_index]`／`[test_plan.row_index]` 投影出的 event_id 集合，
  要求**集合相等**。舊 producer 退出生產後**不得**再當正確性參考。
- **G-4 per-symbol counts golden**：多 symbol 批之逐標的計數（整數逐值相等，非 atol 比較）。
- **G-5 containment 四項 golden**（`CODEX-R1-P1-02` 之要求；**R2 之 D3 把 v2 的四個名稱
  補成可執行 oracle**——v2 只列名，三家一致判為 BLOCKING 空殼）：
  1. **逐 row test fingerprint**：canonical 序列化 `(position, feature_ts_ms, symbol,
     base_universe_hash)` 之 exact `sha256`（sorted、int64、無空白 JSON），與 IC orchestrator
     對同一批之輸出逐值相等。失敗時**須指名第一個 mismatch 的 position**，不得只回布林。
  2. **逐 event `assignments`／`purged` IDs**：由 `feature_index[train_plan.row_index]`／
     `[test_plan.row_index]` **直接**產生之集合為 oracle（與被測函式獨立），斷言三件事——
     互斥、涵蓋全集、`purged.reason` 字面 == `interval_crosses_split_boundary`。
     失敗時輸出 **diff 的 event_id 清單**。
  3. **answer-window 完整性**：對每個 test 段事件，斷言其 label 起訖（`label_start_ms`、
     `label_end_ms`）在 source bars 上**完整覆蓋**（兩端 endpoint 都存在）；
     缺 endpoint 或跨越邊界者**必產 purge**，並輸出該 event_id。
  4. **leakage negative case**：合成 fixture——把一筆 train 事件的 `label_end_ms`
     推進 test 區間，斷言它**進 `purged`**（不得留在 `assignments`）；
     把該斷言拿掉 ⇒ mutation rc=1。
  每項各有對應 nodeid（`tests/momentum/Analysis/test_splitunify_golden.py -k <name>`）
  或 `freeze_splitunify_golden.py` 之子模式，缺一即視為未實作。
- **數值比較規約**：計數類一律**整數逐值相等**；浮點欄位以 `atol=1e-12`／`rtol=1e-9` 比較
  （同 `test_binary_discrimination.py` 之既有規約）。

## §P Phase 與依賴（四批；三家一致「大」，批數取較保守者）

| 批 | Task | 依賴 | 產出 |
|---|---|---|---|
| **B1** | Task 1.1、1.2、1.3 | consult 三家戳記 rc=0 | 文件、枚舉 SoT、既有紅基準清單；**不動生產碼** |
| **B2a** | Task 2.1 | B1 | canonical boundary builder（core 純函式） |
| **B2b** | Task 2.2 | B2a | 投影純函式＋`build_time_clusters` 抽出 |
| **B2c** | Task 2.3 | B2b | golden 五組（G-1／G-3a／G-3b／G-4／G-5）；**仍不接線** |
| **B3** | Task 3.1、3.2、3.3 | B2c | 邊界唯一化、多 symbol fail-closed、event-study-only 分派＋誠實揭露 |
| **B4** | Task 4.1 | B3 | 報告與畫面 |

🔴 **R2 之 D11／codex Q8**：v2 把 B2 標為「大」卻只有批末一個 gate，等於把三個
**可獨立證偽**的產出綁成一次審查 ⇒ 拆為 B2a／B2b／B2c，各自 gate 與 review 後才進下一段。

每批三家 code review、commit+push、更新白話看板。

**Task 1.1 — GAP-3 延伸檔 `D-002`**
- 目標：記錄切分權威之變更與投影契約；**不解凍** GAP-3 原檔（C-7）。
- 修改檔案：`docs/GAP3_EVENT_UX_SPEC.D-002.md`（新）。既有 caller：無。
- 不可做：不動 `docs/GAP3_EVENT_UX_SPEC.D-001.md`；不改 GAP-3 原 SPEC。
- 邊界：①原檔已 FROZEN ⇒ 只新增延伸檔；②延伸檔本身亦須過 `doc_format_precheck`。
- 風險緩解：⊘
- **驗證**：`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_SPEC.D-002.md` rc=0；
  `grep -c 'kline_holdout' docs/GAP3_EVENT_UX_SPEC.D-002.md` >= 1；
  該檔須含「post-trim」字面與正確之規格入口路徑，並交叉引用本 SPEC 之 C-0／C-1／C-2／C-4。
- **存活至**：全票完工後保留（GAP-3 之規格鏈）。
- **覆蓋風險**：B4 之 UAT 項會**追加**條目至本延伸檔，不刪既有段。

**Task 1.2 — 枚舉單一真相源 `split_unify.json`**
- 目標：`split_authority` 值集與 fail-closed reason 枚舉一檔定義（C-8）。
- 輸入 / 輸出：無 → `momentum/Analysis/contracts/split_unify.json`：
  `split_authority_values=["kline_holdout"]`、
  `fail_closed_reasons=["multi_symbol_projection_unsupported","missing_train_plan",
  "missing_test_plan","canonical_feature_universe_unavailable"]`。
- 實作要點：🔴 **不含** `assignment_states`——三態＝兩容器（C-3），不是三值枚舉；
  purge reason 沿用 `event_import_contract.json:465-467`。
- 修改檔案：`momentum/Analysis/contracts/split_unify.json`（新）；
  `tests/momentum/Analysis/test_splitunify_contract.py`（新）。既有 caller：無。
- 不可做：不在 Python 端手打第二份值集；不加 `assignment_states`。
- 邊界：①JSON 缺鍵 ⇒ import 期 raise；②值集為空 ⇒ raise。
- 風險緩解：⊘
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_contract.py` rc=0：
  JSON 之值集與 Python 常數集合逐值相等（`==`）；刪一鍵 ⇒ raise（可證偽）；
  另斷言 `assignment_states` **不存在**於本檔（防退回三值枚舉）。
- **存活至**：全票完工後保留（下游前端亦讀）。
- **覆蓋風險**：B3 若發現新的 fail-closed 情形，**追加** reason 值，不改既有值。

**Task 1.3 — 既有紅基準清單（取代 v1 之「failed <= 20」聚合期望數）**
- 目標：把既有紅落成**逐條 nodeid 清單**（🔴 以 B1 凍結之 receipt 為準＝**19 條 / 1103 passed**；
  `HANDOFF.md` 舊記的「20 條 / 1615 passed」是**不同收集面**的舊量測——grok 以 passed 基數
  1615 vs 1103 證明那不是漏抓，B1 review `GROK-R1-P3-01`——**不再引用**），
  使 B3 驗收可證偽（R1 之 C3 群集；grok 與 composer 各標 P0）。
- 輸入 / 輸出：實跑 pytest → `tests/baselines/analysis_known_failures.nodeids`。
- 實作要點：一次實跑產出，**不得手抄湊數**；🔴 **須捕獲 pytest 自己的 rc**
  （R2 之 D9／codex：管線經 `tee`／`awk` 會把 rc 吃掉，collection failure 會偽裝成空基準——
  這正是 `CLAUDE.md` Gotchas 的「`cmd | tail; echo rc=$?` 讀到的是 tail 的 rc」）：
  ```bash
  set -o pipefail   # 或改用 ${PIPESTATUS[0]}
  venv/bin/python -m pytest tests/momentum/Analysis --tb=no -q \
    > handoffs/run_receipts/splitunify-analysis-baseline.stdout 2>&1
  echo "pytest_rc=$?" >> handoffs/run_receipts/splitunify-analysis-baseline.stdout
  awk '/^FAILED /{print $2}' handoffs/run_receipts/splitunify-analysis-baseline.stdout \
    | grep '::' | sort -u > tests/baselines/analysis_known_failures.nodeids
  ```
     🔴 **`grep '::'` 不可省**（B1 實跑抓到）：`-q` 模式下 pytest 的進度條殘片會讓
     `^FAILED ` 多命中 11 行，`$2` 取出 `[`、`[100%]` 這種非 nodeid；不過濾就會把它們
     凍進基準，`--deselect` 時直接壞掉。實測 30 行 `^FAILED ` 中只有 19 行是真 nodeid。
- 🔴 **維護協議（R2 之 D9，三家＋主委四方一致）**：清單在 B1 凍結、B3 才用。
  B3 驗收 (B) 判準為**方向性**：實際 FAILED **⊆** 清單（只准變短）為綠、變長為紅。
  變短時允許**同一 PR** 更新清單與 receipt，commit 訊息須標 `splitunify-baseline-sync`
  並具名哪一條變綠。B2 期間若 `REDSWEEP` 修好某條，同樣走此協議。
- 修改檔案：`tests/baselines/analysis_known_failures.nodeids`（新）；
  `handoffs/run_receipts/splitunify-analysis-baseline.stdout`（新）。既有 caller：無。
- 不可做：不得手寫 nodeid；不得把本票新增之測試放進清單；
  不得在驗收紅時直接改驗收條件（只能依維護協議改清單並具名）。
- 邊界：①清單**可以為空**（既有紅已清）⇒ B3 驗收改為直接 rc=0；
  此時**不得**用 `test -s` 當閘（會把合法空清單judge成失敗），改驗
  「receipt 存在且其 `pytest_rc` 已記錄」；
  ②清單中任一條變綠 ⇒ 依維護協議移出。
- 風險緩解：⊘
- **驗證**：`grep -c '^pytest_rc=' handoffs/run_receipts/splitunify-analysis-baseline.stdout` == 1；
  清單行數 == receipt 內 `^FAILED ` **且含 `::`** 的行數（B1 review `CODEX-R1-P1-02`：不加過濾是 19 ≠ 30）；
  `venv/bin/python -m pytest -q --collect-only $(cat tests/baselines/analysis_known_failures.nodeids)`
  rc=0（清單內有不存在的 nodeid ⇒ rc≠0，可證偽）。
- **存活至**：`REDSWEEP` 票收案後刪除。
- **覆蓋風險**：`REDSWEEP` 會逐條清空本清單；兩票之間以「只准變短」為不變式。

**Task 2.1 — canonical boundary builder（C-0）**
- 目標：兩端共用之**唯一**邊界算術，住 core。
- 輸入 / 輸出：`holdout_boundary(feature_index, *, oos_test_size, purge_gap, embargo)`
  → `Dict[str, Any]`，鍵為 `train_row_index`／`test_row_index`／`train_end_ms`／`test_start_ms`
  （B1 review `GROK-R1-P3-02`：v5 原寫元組、實作回 dict；回 dict 是為了讓 B3 呼叫端
  不必記順序，較不易錯 ⇒ 改文件對齊實作）。
- 實作要點：
  1. **以既有函式定義自身**：`split_point = holdout_split_point(...)`、
     `test_rows = holdout_test_row_index(...)` ⇒ 不引入第二份算術。
  2. 🔴 **ms 之導出寫死（R2 之 D6）**：`train_end_ms = as_ms(feature_index[train_rows[-1]])`
     （`train_rows` 為空 ⇒ `None`）、`test_start_ms = as_ms(feature_index[test_rows[0]])`
     （`test_rows` 為空 ⇒ `None`）。**ms 僅供揭露與 `boundary_hash`，禁回流做 ∈ 判定**
     （成員判定一律走 C-4 之集合語意）。
     v2 只寫「回傳 ms」沒寫怎麼導出 ⇒ 實作端寫成
     `test_start_ms = feature_index[split_point]`（略過 purge／embargo）也能過原本的
     `-k same_source`，`M-SU-11` 擋不住（codex 之反例）。
  3. 輸入輸出之時間一律 **epoch ms**；`feature_index` 為 DatetimeIndex 時以
     `asi8 // 10**6` 換算（同 `split_preview.py:77-78`）。
  4. 純算術、無副作用、不 import `api`。
- 修改檔案：`momentum/core/split_preview.py`（既有檔新增函式）。
  既有 caller：`ic_filter_orchestrator`（B3 接）、`pipeline`（B3 接）。
- 不可做：不得在此讀 config；不得回傳 datetime（統一 ms）。
- 邊界：①`feature_index` 為空 ⇒ raise（無 universe 即無邊界）；
  ②`test_rows` 為空 ⇒ `test_start_ms` 回 `None`，**不得**回 `-1` 或 `0`；
  ③`purge_gap`／`embargo` 為呼叫端算好的最終值，本函式不猜、不查 config。
- 風險緩解：mutation `M-SU-11`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/core/test_splitunify_boundary.py` rc=0：
  與 `holdout_test_row_index` 逐值相同（同源自證）；🔴 **ms 同源斷言**（`-k ms_same_source`）：
  `train_end_ms == as_ms(feature_index[train_rows[-1]])` 且
  `test_start_ms == as_ms(feature_index[test_rows[0]])`；空 index ⇒ raise；
  單位斷言（回傳 ms 之年份 ∈ [2015, 2035]，防 1970 坑）。
- **存活至**：全票完工後保留（唯一邊界實作）。
- **覆蓋風險**：B3 只增加 caller，不改簽名。

**Task 2.2 — `derive_event_split_from_plans` 純函式（C-3、C-4、C-5）**
- 目標：由 canonical 邊界導出**完整**的 `EventSplitPlan`。
- 輸入 / 輸出：見 C-4 之簽名 → `EventSplitPlan`（四欄齊全）。
- 實作要點：
  1. 🔴 **兩段式判定，先後不可調（R3 之 E1）**：
     **先**驗答案窗——`label_end_ms >= test_start_ms` 而 `feature_cutoff_ms` 仍在 train 側，
     或 `label_start_ms`／`label_end_ms` 在 source bars 上缺 endpoint ⇒ **purged**；
     **再**做集合成員判定（`feature_cutoff_ms ∈ feature_index[row_index]`）決定 train／test。
     少了第一段就等於刪掉 `event_split.py:114` 那道唯一擋標籤窗跨界洩漏的閘。
  2. 成員判定用**集合**（`feature_index[row_index]`），禁 `time_bounds` 區間。
  3. train／test 進 `assignments`；purged 進 `purged` 並帶
     `interval_crosses_split_boundary`（契約既有字面）；🔴 兩段式之 purge 共用同一 reason。
  4. `event_keys` 以 **`event_id` 為鍵**與 manifest 對位，**禁 positional zip**（R3 之 E2）。
  5. `clusters` 呼叫 `build_time_clusters(manifest, bucket_ms)`（本 Task 一併抽出，
     行為 byte 級不變，保留 `_cluster_weight` seam）。
  6. `summary` 12 鍵齊全；`insufficient_events_in_test` 改看**投影後**的 test 數；
     `degraded` 之 `cluster_adjusted` 與 `loso_status="not_evaluated"` 語意寫進 docstring。
     🔴 **`single_symbol` 恆亮是預期的**（R2 之 D11，三家＋主委四方一致）：Task 3.2 的
     多 symbol fail-closed 使存活路徑恆為 `n_symbols == 1`，
     `_degraded_flags`（`event_split.py:22-33`）因此恆 append `single_symbol`，
     連帶使 `tables.py:138` 之 `formal_pooled_inference_allowed` 恆 `False`。
     方向保守、是正確的探索性揭露；**不得**為了讓它變 `True` 而清空 `degraded`。
  7. `index_kind != "positional"`、單位未歸一、同時落兩態 ⇒ 皆 raise。
  8. 純函式：無 log、無 I/O、不讀 config、不改輸入。
- 修改檔案：`momentum/Analysis/event_samples/split_projection.py`（新）；
  `momentum/Analysis/event_samples/event_split.py`（抽出 `build_time_clusters`）。
  既有 caller：無（B3 接）。
- 不可做：不得在此讀 config；不得自算 purge／embargo；不得回退成二態；
  不得把 purged 併進 `assignments`。
- 邊界：①`event_keys` 為空 ⇒ 三態皆空（不 raise）；②事件不在 `feature_index` ⇒ purged
  （禁 nearest）；③全部落在隔離區 ⇒ `assignments` 空而 `purged` 為全集（合法產出，
  `tables.py:201` 已明載不得誤擋）。
- 風險緩解：mutation `M-SU-1`..`M-SU-7`、`M-SU-12`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` rc=0：
  三態互斥且 `len(assignments)+len(purged) == len(event_keys)`；
  purged 事件不出現在 `assignments`；`summary` 12 鍵齊全（逐鍵斷言）；
  `clusters` 與舊 `split_events` 之 clusters 逐值相同（byte 級）；
  🔴 `-k answer_window`：`label_end_ms` 跨進測試段之 train 事件**必進 `purged`**（R3 之 E1）；
  空 index／單事件／全 purged／未匹配時間戳／單位錯（秒 vs 毫秒）五個邊界各一條。
- **存活至**：全票完工後保留（唯一投影實作）。
- **覆蓋風險**：B3 只增加 caller，不改簽名。

**Task 2.3 — golden 凍結（G-1／G-3a／G-3b／G-4／G-5）**
- 目標：成員集合、遷移報告、獨立 oracle、per-symbol counts、containment 四項。
- 輸入 / 輸出：既有事件批 → `tests/golden/splitunify/*.json` 與
  `handoffs/run_receipts/` 之遷移報告。
- 實作要點：
  1. `--write` 凍結、預設比對；比對失敗 rc=1 並**指名差集之 event_id**。
  2. G-3a 之遷移報告寫 `handoffs/run_receipts/`，**不**進比對綠徑。
  3. G-3b 之 oracle 直接由 `feature_index[row_index]` 投影，與被測函式**獨立**。
- 修改檔案：`tests/golden/splitunify/*.json`（新）；`scripts/freeze_splitunify_golden.py`（新）。
  既有 caller：無。
- 不可做：比對失敗時**不得**自動 `--write` 覆蓋（那等於沒有 golden）。
- 邊界：①首次凍結（檔不存在）⇒ 只有 `--write` 可建；②比對模式缺檔 ⇒ rc=1。
- 風險緩解：mutation `M-SU-8`。
- **驗證**：`venv/bin/python scripts/freeze_splitunify_golden.py` rc=0；
  手改 golden 內一個成員 ⇒ rc=1 且輸出含該成員名（可證偽自證，
  同 `scripts/freeze_evtlabel_survivor_golden.py` 之作法）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：B3 接線後 G-1 之值**預期改變** ⇒ 以 `--write` 重凍並在 commit 訊息
  逐項記錄差異來源；不得靜默覆蓋。

**Task 3.1 — 接線：邊界唯一化（C-0、C-1）**
- 目標：`orchestrator` 與 `pipeline` 共同呼叫 boundary builder；`split_events` 退出生產呼叫圖。
- 輸入 / 輸出：canonical boundary＋`feature_index` → `EventSplitPlan`（投影）。
- 實作要點：
  1. `orchestrator._build_holdout_split_plan` 改由 `holdout_boundary` 取得列計畫。
  2. `pipeline.run` 之簽名新增 canonical boundary 與 `feature_index`（選填）；
     給定時走投影，未給定時見 Task 3.3。
  3. `split_events` 保留為**歷史路徑／G-3a 對照**，但生產呼叫點數釘為 **0**。
  4. 🔴 **事件 pipeline caller 呼叫投影前 assert**
     `config.split.embargo_ms is None and config.split.embargo_ms_by_symbol is None`
     （R3 之 E5＋R4 之 F3）。🔴 欄位層級是 `config.**split**.…`——`EventPipelineConfig`
     只有 `split: EventSplitConfig`（`pipeline.py:31-45`），兩個 embargo 欄住
     `EventSplitConfig`（`types.py:64-83`）；v4 寫 `config.embargo_ms` 會直接 `AttributeError`。
     **只套事件 pipeline caller**——IC orchestrator 的 `_build_holdout_split_plan` 收的是
     `ICConfig`，不得套同一個 assert。
- 修改檔案：`momentum/Analysis/event_samples/pipeline.py`、
  `momentum/Analysis/ic_filter_orchestrator.py`、`momentum/core/split_preview.py`。
  既有 caller：`ic_feed.py`、`tables.py`、`baseline.py`、`pattern_bridge.py`
  （皆為**成員消費者**，型別不變）。
- 不可做：不改 `derive_event_split_from_plans` 之簽名；不在 caller 端補算切分；
  不刪任何既有 guard（C-1 附帶約束①）。
- 邊界：①非事件 run 不走投影（G-2 逐位元組不變）；②缺 train 或 test plan ⇒ fail-closed。
- 風險緩解：G-2、G-5、mutation `M-SU-9`。
- **驗證**：四條皆 rc=0——(A) `pytest tests/momentum/Analysis tests/momentum/event_samples`
  逐條 `--deselect` 既有紅後 rc=0；(B) 🔴 **方向性**（R2 之 D9，**不是**集合相等）：
  實際 FAILED **⊆** `tests/baselines/analysis_known_failures.nodeids`，只准變短、變長判紅；
  (C) `venv/bin/python scripts/freeze_evtlabel_survivor_golden.py` rc=0（G-2 之 sha256 未漂移）；
  (D) 釘選測試斷言生產路徑對 `split_events` 之呼叫次數 `== 0`（R2 之 D10）；
  (E) `pytest -k embargo_must_be_none` rc=0（R3 之 E5）。
  ```bash
  # A) 扣除既有紅後必須全綠（逐條 deselect，不是「failed <= N」）
  venv/bin/python -m pytest -q tests/momentum/Analysis tests/momentum/event_samples \
    $(awk '{printf "--deselect %s ", $0}' tests/baselines/analysis_known_failures.nodeids)
  # 期望 rc=0
  # B) 既有紅只准變短（子集，不是集合相等）——「修好一條」是綠、「弄壞一條」是紅
  venv/bin/python -m pytest -q --tb=no $(cat tests/baselines/analysis_known_failures.nodeids)
  # 解析 FAILED nodeid 集合 ⊆ 清單集合；出現清單外的 FAILED ⇒ rc=1
  # 變短時：同 PR 更新清單＋receipt，commit 訊息標 splitunify-baseline-sync 並具名
  # C) G-2 未漂移
  venv/bin/python scripts/freeze_evtlabel_survivor_golden.py    # rc=0
  # D) split_events 生產呼叫點釘 0
  venv/bin/python -m pytest -q tests/momentum/event_samples -k split_events_production_call_count
  ```
- **存活至**：全票完工後保留。
- **覆蓋風險**：B4 只加 metadata 欄位，不改接線。

**Task 3.2 — 多 symbol fail-closed（C-2）**
- 目標：per-symbol 投影未支援前，多 symbol 批一律 raise。
- 輸入 / 輸出：多 symbol 批 → `ValueError`。
- 實作要點：批內 symbol 數 > 1 ⇒
  `raise ValueError("multi_symbol_projection_unsupported: …")`；reason 字面自
  `split_unify.json` 讀，不手打。
- 修改檔案：`momentum/Analysis/event_samples/split_projection.py`、
  `tests/momentum/Analysis/test_splitunify_derive.py`。既有 caller：無。
- 不可做：不得以警告放行（fail-open）；不得以第一個 symbol 之 plan 冒充整批。
- 邊界：①單 symbol 批不受影響；②`symbol` 為 None ⇒ 視為單標的（既有語意）。
- 風險緩解：mutation `M-SU-2`、`M-SU-3`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k multi_symbol`
  rc=0：兩 symbol 批 ⇒ raise 且訊息含 `multi_symbol_projection_unsupported`；
  單 symbol 批 ⇒ 不 raise。
- **存活至**：per-symbol 投影實作後**改寫**為支援分支（見 §N R-1）。
- **覆蓋風險**：本 Task 之 raise 分支預期被未來的 per-symbol 支援取代——屆時須連同測試一起改，
  不得只刪 raise。

**Task 3.3 — 無 canonical universe ⇒ 明示 event-study-only（C-0 決議③）**
- 目標：拿不到 canonical feature universe 的匯入流程，**不得**按事件數另切並宣稱 OOS。
- 輸入 / 輸出：無 universe 之批 → `capability={"split":"unavailable","reason":…}`。
- 實作要點：
  1. `case_import_service` 在無 feature universe 時走既有
     `run_event_study_only_with_params`，reason 為
     `canonical_feature_universe_unavailable`（字面自 `split_unify.json`）。
  2. 🔴 **刪除** `run_event_study_only` 現行寫死的 `n_train`／`n_test`／`n_purged`
     （`pipeline.py:728-734` 目前全寫 `0`）。既有 `lookahead_split_blocked`（L3）路徑與
     新 reason **共用同一個新形狀**——不刪就與「summary 不得出現這三鍵」直接矛盾
     （R2 之 D2；v2 同時寫「沿用既有」與「不得出現」，實作端兩條都滿足不了）。
  3. 🔴 `event_forward_return_table` 之 `common` 增
     `estimand_scope="full_sample_not_oos"`（沿用 `pipeline.py:598-599` 之揭露欄位模式；欄位寫進 `tables.py:130-151` 之 `_common_constraint_block`，該區塊於 `:279` 掛上 `common`）。
     理由：該表在 `split_plan=None` 時**確實跑全 manifest 事件**（`tables.py:211-238`，
     無 `split_label=="test"` 過濾），只有 `ci` 與 `formal_pooled_inference_allowed`
     被降級，表身數字**沒有任何「非 OOS」標籤**（R2 之 D4）。
  4. 🔴 前端事件掃描頁**必須**渲染 `capability.split` 與 `capability.reason`；
     `split == "unavailable"` 時**禁再顯示** train/test/purge 計數列
     （現行 `EventTablesPanel.tsx:302` 收回應、`:352` 只渲 summary 計數，
     全文無 `resp.capability`；`grep 'canonical_feature_universe' frontend/` ⇒ 0）。
     兩條 reason（`split_blocked_unverifiable_lookahead` vs
     `canonical_feature_universe_unavailable`）須有**可分辨**的文案（R2 之 D5）。
  5. **沿用既有分派機制**（`pipeline.run_event_study_only`、
     `case_import_service.py:1618-1619` 之 capability 形態），不新造第二套。
- 修改檔案：`api/services/case_import_service.py`、`momentum/Analysis/event_samples/pipeline.py`、
  `momentum/Analysis/event_samples/tables.py`、
  `frontend/src/components/ic-analysis/EventTablesPanel.tsx`、`frontend/src/components/ic-analysis/eventTablesPanelCapability.test.tsx`（**新**）、`frontend/src/lib/types.ts`。
  既有 caller：前端事件掃描頁（**本 Task 要改它**，不再是「型別不變」）。
- 不可做：不得以 `test_fraction` 自行切分後宣稱 OOS；不得填 0 冒充；
  不得只改後端 reason 而不改畫面（那等於使用者仍分不出兩種 unavailable）。
- 邊界：①既有的 `lookahead_split_blocked` 分派**路徑**不變，但其 summary 形狀**會一起改**
  （兩條 reason 共用新形狀）；②有 canonical universe 時行為不變（本票中事件掃描端不會有）。
- 風險緩解：mutation `M-SU-10`。
- **驗證**：`venv/bin/python -m pytest -q tests/api/test_splitunify_event_study_only.py` rc=0：
  `capability["split"] == "unavailable"` 且 reason 字面相符；
  **兩條 reason 皆** `assert "n_test" not in summary`（含既有 L3 路徑之回歸）；
  `event_forward_return_table["common"]["estimand_scope"] == "full_sample_not_oos"`；
  `cd frontend && node_modules/.bin/vitest run src/components/ic-analysis/eventTablesPanelCapability.test.tsx`
  rc=0（兩條 reason 各一個 mock payload，斷言文案不同且無 train/test/purge 計數列）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：per-symbol 支援（R-1）不影響本分支；`R-5`（新增 universe 供給路徑）
  若日後實作，本分支會多出「有 universe」的對照路徑，屆時**不得**刪除本分支。

**Task 4.1 — 報告與前端只暴露一個驗證段（C-6）**
- 目標：`metadata` 只寫 canonical `n_test`＋`split_authority`＋`boundary_hash`＋
  `per_symbol_counts`＋fail-closed `reason`。
- 輸入 / 輸出：投影結果 → `metadata.split_unify`。
- 實作要點：`boundary_hash` ＝ canonical 測試段時間戳之 `sha256`
  （sorted、int64 ms、無空白 JSON）；前端顯示單一數字＋來源標籤。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py`、
  `frontend/src/lib/types.ts`、`frontend/src/components/ic-analysis/`。
  既有 caller：前端 IC 分析頁。
- 不可做：不同時暴露兩個驗證段數字；fail-closed 時不填 0 冒充。
- 邊界：①fail-closed 時 `n_test` 為 null；②全域 run 不寫這些鍵（G-2）。
- 風險緩解：mutation `M-SU-9`。
- **驗證**：`venv/bin/python -m pytest -q tests/api/test_splitunify_disclosure.py` rc=0：
  報告中含「驗證段列數」語意之鍵**恰 1 個**；`split_authority == "kline_holdout"`；
  `cd frontend && node_modules/.bin/vitest run src/lib/splitAuthority.test.ts` rc=0。
- **存活至**：全票完工後保留（UAT 交付物）。
- **覆蓋風險**：無後續 Phase。

## §V 驗證策略與邊界測試目錄

- `tests/momentum/core/test_splitunify_boundary.py`（B2）：邊界 builder 與既有函式同源；
  空 index raise；單位年份斷言。
- `tests/momentum/Analysis/test_splitunify_derive.py`（B2）：三態互斥且涵蓋全集；
  purged 不出現在 `assignments`；`summary` 12 鍵；`clusters` byte 級相同；
  五個邊界（空／單事件／全 purged／未匹配／單位錯）。
- `tests/api/test_splitunify_event_study_only.py`（B3）：無 universe ⇒ unavailable 且無 `n_test`。
- `tests/api/test_splitunify_disclosure.py`（B4）：驗證段鍵恰 1 個。

mutation 對照表（12 條；每批收案前跑，紅只認 rc=1）：

| ID | 改壞什麼 | 應紅之測試 |
|---|---|---|
| `M-SU-1` | 投影二態化（purged 併入 `assignments`） | `test_splitunify_derive.py -k three_state` |
| `M-SU-2` | 多 symbol fail-closed 拿掉 | `test_splitunify_derive.py -k multi_symbol` |
| `M-SU-3` | 以第一個 symbol 之 plan 冒充整批 | `test_splitunify_derive.py -k multi_symbol` |
| `M-SU-4` | 成員改用 `time_bounds` 閉區間而非集合 | `test_splitunify_derive.py -k membership_set` |
| `M-SU-5` | 未匹配時間戳預設歸 `train`（非 purged） | `test_splitunify_derive.py -k unmatched_timestamp` |
| `M-SU-6` | 同時落兩態時靜默取 train | `test_splitunify_derive.py -k dual_membership` |
| `M-SU-7` | `clusters` 抄舊 plan 而非由 manifest 重算 | `test_splitunify_derive.py -k clusters` ＋ `test_tables.py` cluster CI |
| `M-SU-8` | `freeze_splitunify_golden.py` 比對失敗自動 `--write` | freeze 腳本自證（改一員仍須 rc=1） |
| `M-SU-9` | metadata 同時寫舊事件 `n_test` 與 canonical `n_test` | `test_splitunify_disclosure.py` |
| `M-SU-10` | 無 universe 時仍按事件數切並宣稱 OOS | `test_splitunify_event_study_only.py` |
| `M-SU-11` | boundary builder 之 rows 或 **ms** 任一不同源（含 `test_start_ms` 略過 purge） | `test_splitunify_boundary.py -k same_source` ＋ `-k ms_same_source` |
| `M-SU-12` | 事件 ms 與 feature index 單位未歸一（秒／毫秒混用） | `test_splitunify_derive.py -k unit_normalize` |
| `M-SU-13` | 拿掉第一段答案窗 purge（只留集合成員判定） | `test_splitunify_golden.py -k leakage_negative` ＋ `test_splitunify_derive.py -k answer_window` |
| `C0` | 只改註解（對照組） | 必須仍綠 |

benchmark：投影為 O(n log n) 以內；門檻**先量一次再定**，不寫死未量過的數字
（EVTLABEL B4 之教訓：首跑 benchmark 只測乾淨資料，10% NaN 路徑實測 200s 遠超上限）。

## §R 回退

boundary builder／投影（B2）與接線（B3）分屬兩批 ⇒ B3 回退即可回到雙軌狀態
（B2 之純函式無 caller、無副作用）。B1 之文件與枚舉不需回退。

## §N N/A 登記與殘留

- **R-1（needs-research）**：per-symbol `SplitPlan` 之 `base_universe_hash` 語意在多標的下
  是否仍唯一——本票先 fail-closed（Task 3.2），不在此解。
- **R-2（blocked-by）**：`baseline.py`／`pattern_bridge.py`／`tables.py` 之 OOS 數值**必變**
  （C-9 已定），改變量待 B2 之 G-3a 遷移報告實跑後才有數字，屆時逐項登記為預期差異。
- **R-3（user-ruling）**：UAT 項目之更新等 B4；使用者已裁定 UAT 一律最後。
- **R-4（blocked-by）**：`momentum/Analysis/event_samples/pattern_bridge.py::extract_event_patterns`
  **無 production caller**（測試 caller 有 8 處：`tests/momentum/event_samples/test_pattern_bridge.py:12,47,63,66,71,89,102,112`）——v3 曾誤寫成「無任何 caller」，根因是我引用了 `head -15` 截斷的 grep 輸出（`CLAUDE.md` Gotchas 已具名的「驗 scanner 勿 tail 截斷」，R3 之 `CODEX-R3-P2-04` 抓出）
  ⇒ 又一個「兩端都有、但沒接上」。本票不接線它，只確保其消費之 `assignments` 語意不變。
- **R-5（needs-research）**：本票**不新增** universe 供給路徑——要讓 `EventImportService`
  拿到 post-trim feature universe，須新增 `features_run_id` 之跨棧參數（請求模型、前端、
  契約、UAT 全動），且該 service 目前完全不碰 FF run。R2 之 D1 裁定：事件掃描端恆走
  event-study-only。日後若實作 R-5，**不得**刪除 Task 3.3 之分支，只能新增對照路徑。
- **SU-RESID-1（needs-research）**：`scripts/reconcile_cluster_attribution_check.sh` 只驗
  「finding ID 字串是否出現在檔內」，**不驗是否被正確的決議項引用** ⇒ 本票之 consult 收斂
  兩類失誤（處置段改寫委員立場、finding ID 歸屬錯置）它**都回 rc=0**。
  真正攔下來的是委員逐條對照。修法需要一個「決議項 ↔ finding 語意對應」的機械判準，
  屬治理工具研究，不在本票範圍。
