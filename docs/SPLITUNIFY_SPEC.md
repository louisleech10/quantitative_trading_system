# SPLITUNIFY — SPEC

> **狀態（2026-09-17）**：**v6（R 重開版，對抗審中）**。依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1 之 **R 重開**：
> v5 之 `## 戳記` 失效；`docs/SPLITUNIFY_SPEC.D-001.md`、`docs/SPLITUNIFY_SPEC.D-002.md` **全量失效**，
> 其仍有效之義務逐條併入本檔（識別碼沿用，見 §R0）。本檔檔頭不再有延伸索引行。
> 偵察收斂檔：`handoffs/reconcile/20260911-splitunify-x-consult-r3/synth.md`。

## §R0 R 重開聲明與併入規則

**類別＝R**（主委判定；任一委員可推翻，爭議預設 R）。
理由：v5 之 C-0 決議②「R2 之 D1 裁定：事件掃描端**恆走** event-study-only」與 `Task 3.3` 目標句
（「拿不到 canonical feature universe 的匯入流程」＝事件掃描端全部）被本版推翻——使用者 2026-09-17 開 `R-5`，
事件掃描端改為**可**取得 post-trim feature universe 並走投影。依 §2.2「與原檔互斥 ⇒ 不是 D」。

**效力**：
1. v5 之三家 RECONCILE-STAMP 不再有效；本檔重跑完整對抗審並重新戳記。
2. `D-001`／`D-002` 失效。兩檔**檔案保留**（僅加失效標示，內容不再改動），理由：`scripts/freeze_splitunify_golden.py`、
   `scripts/register_anchor_check.py` 與測試檔仍以路徑讀取其 §V 錨點與 register；讀取者改指本檔列為 `Task 10.1`。
   `Task 10.1` 落地前，兩檔之機讀內容與本檔對應段**逐值相同**為不變式（`Task 10.1` 驗收）。
3. 併入規則：**只收現行態**。各延伸檔中被後續版本改判、刪節線與標為不再適用之字面**一律不收**；
   修訂沿革不重述，見 `handoffs/reconcile/` 收斂檔與 git 歷史（兩檔失效前最後版本 commit＝`d362332d`）。
4. **識別碼沿用**：`D-001-C1`、`D-001-C2` (4.1)–(4.18)、`D-002-C0`／`C3`／`C5`／`C6` 之編號、register `C5-01`～`C5-29`、
   mutation `M-SU-D1-*`／`M-SU-D2-*`、`Task 8.x`／`9.x` 一律原號保留——程式碼與測試之註解以這些識別碼引用規格，改號即斷鏈。
5. 併入後與 v5 本文衝突者，以併入之延伸條文為準（延伸檔本就覆寫 BASE 之對應段）；衝突點已在本檔直接改寫，不另留例外句。

## §A 假設與待使用者確認

**已確認（使用者回覆）**：
1. 2026-09-10：「但要如何切分，你跟委員要討論共識」——切法交委員會定。
2. 2026-09-10：SPLITUNIFY 排 EVTLABEL 之後、UAT 之前（使用者選 B）。
3. 2026-09-12：「不再擴建治理工具；同型缺陷降級為具名殘留」（`SU-RESID-V8-ATTEST` 之理由來源）。
4. 2026-09-13：不接受紀律或記憶當解法——修正只准機械閘或結構改法。
5. 2026-09-17：開 SPLITUNIFY 最後一件 `R-5`（規格 R 重開＋最後一批）；**不得刪除 `Task 3.3` 之分支，只能新增對照路徑**；
   UAT（`R-3`）照舊排最後；GLOBALH 不在本票；規格結論須白話送使用者審閱，放行後才寫施工清單。

FACT-RECEIPT: `grep -n 'features_path\|config_hash\|feature_library' api/services/case_import_service.py` → 除註解外零命中（主委 實跑 2026-09-17）
FACT-RECEIPT: `venv/bin/python scripts/register_anchor_check.py` → 「共 22 個錨點，全數通過」rc=0（主委 實跑 2026-09-17）

**待使用者確認：無**（`R-5` 之技術選擇交委員會；使用者之審閱點為本檔戳記後之白話結論）。

## §A2 目標與問題

平台有兩個入口產切分：

| | 事件掃描入口 | IC 分析入口 |
|---|---|---|
| service | `EventImportService.analyze`（`api/services/case_import_service.py`） | `ICAnalysisService` → `ic_filter_orchestrator.analyze` |
| 型別 | `EventSplitPlan`（`momentum/Analysis/event_samples/types.py`） | `SplitPlan`（`momentum/core/contracts.py`） |
| 產生者 | `split_projection.derive_event_split_from_plans`（投影） | `_build_holdout_split_plan`（呼叫 `split_preview.holdout_boundary`） |

兩者分屬兩個 service、兩個 endpoint，**不存在單一合併點**。
目標：**一個批次只有一條 canonical OOS 邊界**；報告只暴露一個驗證段數字並揭露來源與 sha256；
拿不到 canonical 邊界的路徑明示 `event-study-only`，不給假數字。

v6 新增目標（`R-5`）：事件掃描端在使用者選定 FF run 時，取得**與 IC 分析同一條** canonical 邊界並走投影；
未選定時維持 v5 之 event-study-only 分支（`Task 3.3`）。

## §RISK 風險分級

RISK-HIT: a,b,c,d

**大票**。(a) 切分邊界決定 OOS 數字；(b) 跨 service、跨棧（請求模型、前端、契約）與共用消費面；
(c) 規格 R 重開、多批；(d) 切分與無洩漏正確性。命中 (a)(d) ⇒ §G 必填、adversarial 必跑。

## §C 約束

### C-0 🔴 接線落點：單一 boundary builder，拿不到 universe 就不得宣稱 OOS

1. canonical 邊界由 core 之純函式 `momentum/core/split_preview.py::holdout_boundary` 產生；
   IC 端 `_build_holdout_split_plan` 與事件端**共同呼叫**，事件端不得自行重算邊界算術。
2. 事件 pipeline（`EventSamplePipeline.run`）**選填**接受 canonical 邊界（`train_plan`／`test_plan`／`feature_index`，三者同時給齊，
   給一半 fail-closed）；給定時走投影，未給定時走歷史 `split_events`（生產呼叫點數＝0）。
3. 🔴 **事件掃描端之分派（v6 改寫；取代 v5「恆走 event-study-only」）**——依序判定，先命中者生效：
   - (i) 深度不可證（`lookahead_split_blocked`）⇒ event-study-only，reason＝`split_blocked_capability_reason()`（既有）。
   - (ii) 請求**未帶** FF run 識別 ⇒ event-study-only，reason＝`canonical_feature_universe_unavailable`（`Task 3.3` 分支，**不得刪除**）。
   - (iii) 請求帶 FF run 識別 ⇒ 依 `R5-C1`～`R5-C8` 取得 canonical 邊界並走投影，`capability.split="ok"`。
4. 沒有 canonical feature universe 的路徑**只能**明示 event-study-only，不得按事件數另切並宣稱 OOS；連帶三件事：
   - (a) `run_event_study_only` 之 `summary` **不得**出現 `n_train`／`n_test`／`n_purged` 三鍵（不是填 0）；兩條 reason 共用同一形狀。
   - (b) `event_forward_return_table` 之 `common` 含 `estimand_scope="full_sample_not_oos"`（該表在 `split_plan=None` 時跑全 manifest 事件）。
   - (c) 事件掃描頁渲染 `capability.split` 與 `capability.reason`；`split == "unavailable"` 時不顯示 train/test/purge 計數列；兩條 reason 文案可分辨。

實測支撐（共用 universe 而非共用公式）：探針 `handoffs/20260911-probe-splitunify-universe-gap.py`、
receipt `handoffs/run_receipts/20260910T154323Z-splitunify-universe-gap.log`——EVTALIGN 裁頭尾 5／24／168 根 ⇒ 邊界位移 2／10／67 小時。

### C-1 canonical 權威＝時間切分

K 線 holdout（`SplitPlan`，含 purge／embargo）為**唯一邊界來源**；`EventSplitPlan` 為投影容器，
其 `assignments`／`purged`／`clusters`／`summary` 一律由 canonical 邊界衍生。
附帶約束：① 事件側與時間側兩套隔離之 containment 未證明前，**不得刪除任一既有 guard**；② §G 之 G-5 四項須同時存在。
「兩套都保留但標主從」為反模式，明文否決。

### C-2 🔴 邊界必須 per-symbol，禁全域 scalar 冒充

不得以全域 scalar `SplitPlan.test_timestamps` 交集取代事件計畫（實測 receipt `20260910T150504Z-splitunify-multisymbol`：
全域 12 列 vs per-symbol 8 列）。多 symbol 批以 `D-001-C1` 之 per-symbol 結構投影；
**禁**以第一個 symbol 之 plan 冒充整批。未提供 Mapping 形式之多標的輸入 ⇒ `multi_symbol_projection_unsupported`。

### C-3 三態＝兩個容器

train／test 進 `assignments`（`split_label` ∈ `{train, test}`），被隔離者進**獨立**的 `purged`（`event_id`, `reason`）；
reason 沿用 `momentum/Analysis/contracts/event_import_contract.json` 之 `split_purge_reasons` 字面 `interval_crosses_split_boundary`，
不在 `split_unify.json` 另造。**不得**以擴充 `split_label` 值域（如 `PURGED`）替代兩容器。
兩容器**互斥**：`set(purged.event_id) ∩ set(assignments.event_id) == ∅`（`D-002-C3` (3.2)）。

### C-4 投影是純函式、單一實作

**簽名**＝`D-001-C1` 第 1 點（Mapping 形式＋單標的薄 wrapper）。純函式：無 log、無 I/O、不讀 config、不改輸入。

**`event_keys` 之欄位契約**：欄集＝`EVENT_KEY_COLUMNS`
（`event_id`、`feature_cutoff_ms`、`label_start_ms`、`label_end_ms`、`symbol`、`timeframe`、`feature_timeframe`）；
以 `event_id` 為鍵與 `manifest.table` 對位，**禁 positional zip**；`event_keys` 之粒度為 `(event_id, feature_timeframe)`（稽核層）。

**producer**＝`split_projection.build_event_keys(receipts, *, selected_timeframe: Optional[str] = None) -> (event_keys, discarded)`：
- `selected_timeframe is None` ⇒ 全量，每列一個 `(event_id, feature_timeframe)`，`discarded == {}`；
- 給字串 ⇒ 只取該 feature TF，其餘列逐 feature TF 記入 `discarded`（值為列數），不 raise；
- `feature_timeframe` 取自 `per_tf.timeframe`，**不得**以 `event_level.timeframe`（觸發 TF）冒充；
- 以 `per_tf` 為行粒度接合 `event_level`，`validate="many_to_one"`；
- fail-closed：`per_tf.timeframe` 有缺值；`(event_id, feature_timeframe)` 複合鍵重複；事件缺 `feature_cutoff_ms`；給定之 `selected_timeframe` 無任何列。

**判側（事件級錨定，順序不可調）**——以 `manifest.table.decision_at_ms` 每事件判一次側，再廣播到該事件所有 feature TF 列；
`feature_cutoff_ms` **不參與** `split_label`：
- 步驟 0（前置，全部先於分類）：① `train_rows`、`test_rows`（皆取自 `row_index_local`）**皆非空**，空即 `missing_train_plan`／`missing_test_plan`；
  ② `train_last_ms = index_ms[train_rows[-1]]` 嚴格小於 `test_start_ms = index_ms[test_rows[0]]`，否則 raise；
  ③ `validate_split_pair_integrity` 由**持有 full `ts`／`symbols` 之呼叫端**於進入投影**之前**呼叫（落點見 `Task 9.2b`）；
  ④ `index_ms[0] <= decision_at_ms <= index_ms[-1]`，任一事件不滿足即 raise（訊息含 `event_id`）——界外**不是**第四條分類分支。
- 三段式：`decision_at_ms <= train_last_ms` ⇒ train；`decision_at_ms >= test_start_ms` ⇒ test；兩者之間 ⇒ purged（隔離帶，合法且預期，不得 raise、不得收成 train）。
- 答案窗 purge：判為 train 之事件若 `label_end_ms >= test_start_ms` ⇒ 整事件 purged（`>=` 必須保留）。
  `purge_gap`／`embargo` 為 row 單位且已含在 `test_start_ms` 所對應之 `test_rows[0]` 起點內，**不得**再以毫秒相減。
- 事件級欄一致性：同一 `event_id` 之 `decision_at_ms`（manifest）或 `label_end_ms`（`event_keys`）不唯一 ⇒ `AlignmentViolationError`；
  錨點唯一性檢查排在 `manifest.table` 重複檢查**之前**。

**單位**：本票時鐘一律 epoch **毫秒**。**禁**呼叫 `_normalize_ic_time_index`（秒語意）；正規化一律走
`split_preview.epoch_ms_from_index`／`assert_epoch_ms_array`（逐元素、嚴格遞增）。單位判定失敗 ⇒ raise，不得靜默 0 命中。

**其餘 fail-closed**：`index_kind != "positional"`；`event_keys` 與 `manifest.table` 之 `event_id` 集合不相等（不接受 subset）；
`manifest.table` 之 `event_id` 重複；`event_keys` 複合鍵重複；plan 缺 `symbol`、train/test plan 之 `symbol` 或 `base_universe_hash` 不同；
`plan.time_bounds` 與傳入 `feature_index` 在該 plan 首尾列上不等（首尾同源對證，承 C-1 附帶約束①保留）；
`label_start_ms > label_end_ms`。

### C-5 投影須產出**完整**的 `EventSplitPlan`

- `assignments` 欄＝`["event_id","symbol","split_label"]`、`purged` 欄＝`["event_id","reason"]`，皆**事件級、一事件恰一列**；
  空批之欄集與非空批逐字相同。
- 稽核層複合列經具名 seam `_aggregate_event_level_split_rows(event_keys, event_state) -> (assign_rows, purge_rows)` 逐事件聚合：
  `event_id` 須為非空 `str`（值級判定，不得先 `astype(str)`）；同事件 `symbol` 非單值 ⇒ `AlignmentViolationError`；
  `split_label` 取自單值之 `event_state`；**明禁** `drop_duplicates`／`set`／take-first。
- 寫入兩容器前呼叫 `_assert_event_level_side_consistency`（同事件異側、跨表混態皆 `AlignmentViolationError`，訊息含 `event_id`，不取一側、不改判 purged）；
  建表後（多標的於串接後）以 `_assert_concat_event_level_unique` 驗兩表各自 `event_id` 唯一且互斥。
- `clusters`＝`event_split.build_time_clusters(manifest, bucket_ms)`（事件級，與切分無關；保留 `_cluster_weight` mutation seam）。
- `summary` **16 鍵 exact-set**：`n_symbols`／`per_symbol_n`／`n_time_clusters`／`avg_cluster_size`／`degraded`／`loso_status`／
  `insufficient_events_in_test`／`stats_modes`／`n_events_raw`／`n_events_effective`／`n_purged`／`bucket_ms`／
  `discarded_rows_by_feature_tf`／`n_events`／`n_event_tf_rows`／`n_event_tf_rows_purged`。
- `insufficient_events_in_test` 逐 symbol 判定，test 事件數以 `event_id` 去重；`per_symbol_n` 以 `event_id` 去重；
  `per_symbol_test_n` 為內部門檻參數，**不是** summary 鍵。
- `degraded` 之 `single_symbol` 僅在 `n_symbols == 1` 時出現（唯一產生點 `event_split._degraded_flags`）；
  **不得**為使 `formal_pooled_inference_allowed` 為真而以其他方式清空 `degraded`。
- 空 plan 不得冒充未切分。
- 投影路徑下 `config.split.embargo_ms` 與 `config.split.embargo_ms_by_symbol` 必須為 `None`，否則 raise；該檢查住**呼叫端**
  （`EventSamplePipeline.run`），不在投影內。

### C-6 報告只暴露一個驗證段數字

`metadata.split_unify` 之鍵集＝`split_unify.json` 之 `split_unify_keys`（`n_test`／`split_authority`／`boundary_hash`／`per_symbol_counts`／`reason`），
唯一產生點 `split_projection.build_split_unify_disclosure`。`split_authority` 固定 `"kline_holdout"`；
`boundary_hash`＝canonical 測試段時間戳（sorted、int64 ms、無空白 JSON）之 sha256；fail-closed 時 `n_test` 為 `null` 而非 `0`，
其餘數值清為 `None`／`{}`。整份報告中「驗證段計數」語意之鍵依 `split_unify.json` 之 `test_segment_count_keys`
deny-by-default 登記：canonical 恰一個，其餘同語意鍵必須逐值等於 canonical。

### C-7 GAP-3 延伸檔

切分權威之變更與投影契約記於 `docs/GAP3_EVENT_UX_SPEC.D-002.md`（B1 交付）；GAP-3 原檔不解凍。
該延伸檔須寫明投影所用 `feature_index` 為 **post-trim** universe。`R-5` 之事件掃描端行為變更**追加**條目至該延伸檔（`Task 10.3`）。

### C-8 新資料結構走 JSON 單一真相源

`split_authority` 值集、fail-closed reason、`estimand_scope` 值集、`split_unify_keys`、`test_segment_count_keys`
集中於 `momentum/Analysis/contracts/split_unify.json`；Python 與前端各自對證，禁散文複列。不含 purge reason（見 C-3）、不含 `assignment_states`。
fail-closed reason 封閉集合（現行）＝`multi_symbol_projection_unsupported`、`missing_train_plan`、`missing_test_plan`、`canonical_feature_universe_unavailable`；`Task 10.3` 追加 `canonical_holdout_disabled`、`canonical_holdout_insufficient_rows`（R5-C3 5.）；`Task 10.2` 新增鍵 `event_disposition_values`（R5-C8 2.）；
新增值須同步本節與前端對證測試。

### C-9 統一會改變數值

影響面：`baseline.py`（`n_test_events`／`n_test_samples`、prevalence、AUC／PR-AUC、permutation band、BH-FDR）、
`tables.py`（OOS metrics、macro／micro AUC、cluster CI）、`pattern_bridge.py`（fit rows、rules、scores、lift、receipt hash）、
`ic_filter_orchestrator.py`（test intersection 之 `n_pos`／`n_neg` ⇒ `label_mode`）。
驗收對改前後做逐 event ID 集合、逐列 train／test fingerprint、報告 numeric keys 與 capability reason 之 exact／tolerance diff；
不得以「型別不變」宣稱數值不變，不得以舊 golden 擋投影。`R-5` 使事件掃描端由「無切分」變為「有切分」，數值變動同受本節約束。

### D-001-C1 per-symbol 投影之身分不變式

1. **投影簽名**：

```python
def derive_event_split_from_plans(
    plans: Mapping[str, tuple[SplitPlan, SplitPlan]],      # symbol → (train_plan, test_plan)
    event_keys: pd.DataFrame,
    feature_index_by_symbol: Mapping[str, pd.Index],       # symbol → 該 symbol 之 post-trim universe（短索引）
    *,
    manifest: EventManifest,
    bucket_ms: Optional[int] = None,
    tier_min_test_events: int = 1,
    discarded_rows_by_feature_tf: Optional[Dict[str, int]] = None,
) -> EventSplitPlan
```

   單標的舊呼叫式（`train_plan, test_plan, event_keys, feature_index, …`）保留為**薄 wrapper**，不得含第二份判定邏輯（purge／判側／指紋比對只有 `_derive_single_symbol` 一份）。
   給 `plans` Mapping 而未給 `feature_index_by_symbol` Mapping ⇒ `multi_symbol_projection_unsupported`。
   `feature_index_by_symbol[symbol]` 一律是**該 symbol 自己的 post-trim 索引**，長度＝該 symbol 列數，**不可**被全框 `SplitPlan.row_index` 直接索引；
   本簽名**不收任何全框輸入**，symbol-local 座標由 plan 自帶之 `row_index_local` 提供（`D-001-C2` 第 4 點）。
   多標的路徑逐 symbol 以 `_manifest_subset` 切 manifest 後走 `_derive_single_symbol`，各自聚合後**縱向串接**，串接後再驗唯一與互斥；
   `discarded_rows_by_feature_tf` 為批次級，**原樣**寫入 summary，不得逐 symbol 相加。
2. **hash 不變式**：同一 symbol 之 `train_plan.base_universe_hash == test_plan.base_universe_hash`（`validate_split_pair_integrity` 已驗，不放寬）；
   **跨 symbol 允許共用同一字面 hash**（`ICSplitAdapter._base_universe_hash` 對整框算一份 joint hash 為合法 scope）；**禁**把「跨 symbol hash 必互異」寫成閘。
   指紋含 `symbol` 欄，但第 3 點之三角相等仍**獨立必查**（指紋證列未被動過，三角相等證事件屬於該 plan）。
3. **symbol 三角相等**：`plans` 之鍵、plan 之 `symbol`、事件集合之 symbol 三者相等；任一不等 ⇒ fail-closed，訊息指名哪一組不一致，
   且不得復用 `multi_symbol_projection_unsupported` 字面（該字面專指「未提供 Mapping」）。
4. **跨 symbol 禁共用 row 數字空間**：每個 symbol 以自己的 `feature_index` 解釋自己的 `row_index_local`；合併只發生在
   `assignments`／`purged`／`clusters` 之縱向串接，不得跨 symbol 比較 row 位置。

### D-001-C2 逐列時刻同源對證

1. **指紋 payload**：`rows` 為 `list[list]`，每列元素順序固定為 `[int(position), int(feature_ts_ms), str(symbol), str(base_universe_hash)]`；
   依 `position` 遞增排序後 `json.dumps(rows, sort_keys=True, separators=(",",":"))` 取 `sha256`。唯一實作＝`split_preview.build_row_time_fingerprint`。
   **禁** `list[dict]`（兩形 sha256 不同）；舊稱 `row_pos`／`ts_ms` 不得再用。
2. **型別強制**：`position` 與 `feature_ts_ms` 必須是 Python `int(...)`（`numpy.int64` 會使 `json.dumps` 丟 `TypeError`）。
3. **正規化函式點名**：時刻一律走 `split_preview.epoch_ms_from_index`／`assert_epoch_ms_array`；**明文排除** `contracts._coerce_timestamp_array`（對純數字預設 `unit="s"`）。
4. **`position` 之語意與 producer attest**：

<!-- OBLIGATIONS-BEGIN id=D-001-C2-4 -->
   **(4.1) 座標語意**：`position` 一律為**該 symbol 之 post-trim `feature_index` 內的序號**（symbol-local ordinal），取數亦必從該 index。
   **(4.2) 不動既有欄**：不改 `SplitPlan.row_index` 既有全框語意（IC 主線之全框驗證與既有 golden 依賴）。
   **(4.3) 新欄**：`SplitPlan.row_index_local`，型別同 `row_index`，內容為該 plan 之列在該 symbol 自己的 post-trim universe 內之序號，遞增且與 `row_index` 逐位對應。
   **(4.4) 三個 producer 之取值**：直接取用其已有之 local ordinal（`split_per_symbol` 與 `ICSplitAdapter._build_plan_pair` 之 `train_local`／`test_local`；orchestrator holdout 路徑因單標的而等同 `row_index`），不得在 producer 端重新反推。
   **(4.5) attest 為必做，判準＝時間序往返**：取該 symbol 之列、依時刻排序後得 `sorted_positions`，驗 `sorted_positions[row_index_local]` 與 `row_index` 逐值相等；不等 ⇒ fail-closed。唯一實作＝`contracts.attest_row_index_local`。
   **(4.6) 禁用之判準**：禁以 `symbol_positions` 或 `_local_ordinals_for_symbol` 之結果逐值相等作 attest 判準（frame 序，亂序輸入下誤擋正確資料）。
   **(4.7) 前置合法性閘（先於往返比對）**：`row_index_local` 為整數、值落在 `sorted_positions` 長度範圍內、無重複、嚴格遞增；複用 `split_preview.assert_positional_rows`，不得關閉其 `require_sorted`。
   **(4.8) helper 未覆蓋之兩面**：①dtype 須為 numpy 整數型（整數值之浮點、布林、物件、數字字串皆擋，不靠轉型救）；②先驗 `len(row_index_local) == len(row_index)`，逐值比對用 `np.array_equal`，禁 `zip`；空序號僅在 `row_index` 亦為空時合法。
   **(4.9) 映不到即 fail-closed**：映不到者不得丟棄或近似。
   **(4.10) 投影端只消費 `row_index_local`**：`derive_event_split_from_plans` 內部一律不得索引 `row_index`；新增消費點亦同。
   **(4.11) 受 (4.10) 覆蓋之消費點為封閉清單**（皆在 `_derive_single_symbol`）：①`assert_positional_rows` 長度與遞增閘 ②入口指紋重算比對 ③`time_bounds` 首尾同源對證 ④`train_last_ms`／`test_start_ms` 之取值。docstring 以「以 `row_index_local` 索引該 symbol 之 `feature_index`」描述座標。
   **(4.12) 缺欄即 fail-closed**：`derive` 入口收到之 plan 缺 `row_index_local` 或 `row_time_fingerprint` ⇒ 報錯並指名欄位，不得以 `row_index` 回退；非 `derive` 之呼叫點給相容 default。
   **(4.13) 權威守衛＝入口重驗**：投影入口以傳入之 `feature_index_by_symbol[symbol]` 重算指紋並與 plan 攜帶值逐值比對；建構後竄改 `row_index_local` 若改變成員集合必被擋下；不得移除或弱化該比對點。
   **(4.14) 指紋與遞增閘為合取**：指紋先排序再雜湊，擋不住同集合重排；重排由 (4.7) 之嚴格遞增擋。兩者缺一不可；投影入口之 `assert_positional_rows` 不得改為 `require_sorted=False`。
   **(4.15) 不可變性為縱深防禦**：`SplitPlan.__post_init__` 對兩個 row 欄各自複製並以不可變 buffer 為底設唯讀（擋直接寫入與 `setflags(write=True)`）；序列化往返（`pickle`／`deepcopy`）仍還原為可寫，規格不得宣稱兩欄「不可變」。
   **(4.16) 竄改 `row_index` 之殘留**：投影端不讀 `row_index`；IC 全框消費端讀到被改值之面登記為 `SU-RESID-5`。
   **(4.17) 面板順序之立場**：以寫入 `train_local` 為準（對齊投影端所用之時間序 `feature_index`）；不得為湊過 attest 改寫 `train_local`；無「frame 序非時間序即 fail-closed」之條款。
   **(4.18) 交錯多標的 fixture 為必測**：兩 symbol 之列在全框交錯時，各自之 `row_index_local` 仍為連續遞增。
<!-- OBLIGATIONS-END -->

5. **邊界定義**：重複 `position` ⇒ fail-closed；`NaT` ⇒ fail-closed；空 `row_index` ⇒ 指紋＝`sha256("[]")`，不得以缺欄代替。
6. **比對點**：投影端以傳入之 `feature_index_by_symbol[symbol]` 同規則重算，與 plan 攜帶指紋逐值比對；不符 ⇒ fail-closed，訊息含「plan 指紋 vs 重算指紋」兩值之前 12 字元。
7. **golden 與獨立 oracle**：指紋 oracle 由同一 fixture 之 `row_index_local` 與該 symbol 之 universe 依本節規則重算，並與 **producer 實際寫入 plan 之指紋欄**逐值相等。
8. **首尾對證不刪**：完整指紋為新增層，既有首尾同源對證保留（C-1 附帶約束①）。

### D-002-C0 術語：兩種 timeframe 必須分名

<!-- OBLIGATIONS-BEGIN id=D-002-C0 -->
**(0.1) 分名義務**：`timeframe` 一詞承載兩種語意，新增之欄位／summary 鍵／API 欄名一律分名，不得用裸 `timeframe`。
**(0.2) 觸發 TF**：`trigger_timeframe`＝事件觸發所在 TF；為 `canonical_event_id(symbol, timeframe, t0)` 之第二引數，已編進 `event_id`。
**(0.3) 特徵 TF**：`feature_timeframe`＝分析特徵所在 TF，即 `receipts.per_tf.timeframe` 與 `selected_timeframe` 所指者；同一事件可有多個。
**(0.4) 複合鍵之維度與適用層**：複合鍵為 `(event_id, feature_timeframe)`，只適用於稽核／中間層（`receipts.per_tf`、`event_keys`），不得外洩到 `EventSplitPlan`（`assignments`／`purged` 維持事件級、一事件恰一列）。
**(0.5) 用語適用範圍**：凡本檔提及「多 TF」「同簇」「同側」「per_tf 多列」，一律指 feature TF。
**(0.6) 既有欄位保留、新增欄位分名**：既有 wire 欄位（含 `per_tf.timeframe`、契約檔既有鍵）原樣保留，不改名、不加 alias；新增者逐字採 (0.2)／(0.3) 之名。
<!-- OBLIGATIONS-END -->

### D-002-C3 同事件多 feature TF 必須落在同一 split 側

<!-- OBLIGATIONS-BEGIN id=D-002-C3 -->
**(3.1) 事件級錨定**：事件之 split 側一律由事件級 `decision_at_ms` 決定，不由各 feature TF 之 `feature_cutoff_ms` 各自判定；各 feature TF 之 cutoff 只用於取特徵值。同一 `event_id` 之所有 feature TF 列恆同側，為結構性保證。
**(3.2) 異側之處置＝fail-closed**：同一事件異側或跨表混態不可能由合法資料產生，出現即擲 `AlignmentViolationError`（訊息含 `event_id`）；不得靜默取一側，不得當成資料問題 purge。`interval_crosses_split_boundary` 維持原義（標籤區間跨越 split 邊界），不新增亦不改寫 reason 字面。
**(3.3) 同簇不等於同側**：同簇只表示統計相關，不保證同側，不得以同簇代替 (3.1)–(3.2)。
**(3.4) 檢查落點**：(3.1)–(3.3) 之檢查在投影端（`derive_event_split_from_plans`）完成，不得下放給各消費端。
<!-- OBLIGATIONS-END -->

### D-002-C5 單鍵消費面

<!-- OBLIGATIONS-BEGIN id=D-002-C5 -->
**(5.1) 分類準則**：判準＝逐處問「這張表的一列代表什麼」，不得用形狀規則（如「凡 `set_index("event_id")` 一律改」）。(甲) 事件級——維持不動；(乙) 複合鍵——須改；(丙) 事件級但需去重取唯一值。乙類現僅 `build_event_keys` 輸出一列；丙類為 `ic_feed` survivor 餵入端與事件數計數面。
**(5.2) 第一層｜producer 與投影本體**：`build_event_keys` 輸出以 `(event_id, feature_timeframe)` 唯一；`assignments`／`purged` 不含 `feature_timeframe` 欄、事件級一事件一列；`build_time_clusters` 事件級；判側以事件級 `decision_at_ms` 為錨。
**(5.3) 第二層｜表格鏈**：`feature_materialization`（`merge validate="many_to_one"`、`groupby("event_id")+row_vals.update` 橫向合併、輸出 `set_index("event_id")`）、`baseline`、`pattern_bridge`、`tables`（四處 `set_index`）、`ic_feed`、`dedupe` 之處置一律以 (5.6) register 為準。
**(5.4) 第三層｜偵察補列**：`counterexample_classifier`、`candidate_ledger`、`ic_feed.event_context_from_windows`、前端 `batch_facts`、前端搜尋頁 `byEventId` Map、`tests/golden/splitunify/{splitunify_golden,clusters_oracle}.json` 之處置以 (5.6) register 為準。`frontend/src/app/search/page.tsx` 之 `byEventId` Map 鍵由 `canonicalEventId(symbol, timeframe, t0)` 建立、來源為上傳 CSV 原始列，排除於複合鍵遷移之外。
**(5.5) 第四層｜記帳與報告鏈**：直接讀取或顯示 split count 者（`pipeline` 之 `n_train`／`n_test`／`n_purged`、事件批面板、wiring 測試之映射）一律以事件數為粒度（`D-002-C6`）。
**(5.6) register 為唯一計數依據與唯一施工清單**：條數以下表列數為準，(5.1) 之分類逐條落在「分類」欄；每條必須有 Task 欄與 mutation 欄；mutation 欄為 `—` 者屬具名缺口，不得當作已覆蓋。
**(5.7) register 之維護義務**：新發現之消費面必須在下表新增列並同步標題條數；只改敘述不改表即為缺陷。改動任一 ANCHOR 所指之碼行者，同一 commit 以 `venv/bin/python scripts/register_anchor_check.py --emit <path>:<line>` 重出該子句。
<!-- OBLIGATIONS-END -->

#### D-002-C5 register 表（(5.6) 之唯一計數依據，共 29 條）

| ID | 消費面（逐字位置） | 分類 | 處置 | Task | mutation |
|---|---|---|---|---|---|
| `C5-01` | `receipts.event_level` | 甲 | 粒度不變，不得改複合鍵 | `Task 9.3` | `M-SU-D2-18` |
| `C5-02` | `manifest.table` | 甲 | 粒度不變 | `Task 9.3` | `M-SU-D2-18` |
| `C5-03` | `clusters`（`event_split.build_time_clusters` 輸出） | 甲 | 事件級，一 manifest 列對一 `event_id` 列 | `Task 9.2a` | `M-SU-D2-18` |
| `C5-04` | `feature_materialization` 輸出之 `set_index("event_id")` | 甲 | 不改；多列輸入不靜默覆蓋之值斷言 | `Task 9.3` | `M-SU-D2-04` |
| `C5-05` | `feature_materialization` 之 `merge validate="many_to_one"` | 甲 | 不需改 | `Task 9.3` | `M-SU-D2-04` |
| `C5-06` | `feature_materialization` 之 `groupby("event_id")+row_vals.update` | 甲 | 設計上的橫向合併，不得改為每 TF 一列 | `Task 9.3` | `M-SU-D2-04` |
| `C5-07` | `dedupe` 之 `merge validate="one_to_one"` | 甲 | 對事件級 `events`，仍成立 | `Task 9.3` | `M-SU-D2-10` |
| `C5-08` | `dedupe` 之 `cluster_first` 保留集 | 甲 | 事件級保留＋把保留之 `event_id` 廣播到 per-TF 列 | `Task 9.3` | `M-SU-D2-10` |
| `C5-09` | `ic_feed` 之單一 TF 過濾後 `set_index` | 甲 | 索引本就唯一，不改 | `Task 9.3` | `M-SU-D2-07` |
| `C5-10` | `ic_feed.event_context_from_windows` survivor 六鍵雜湊 | 甲 | 事件級，不得加入 TF 欄 | `Task 9.3` | `M-SU-D2-19` |
| `C5-11` | `counterexample_classifier` 之 `.loc[eid]` | 甲 | 事件級＋防誤改回歸 | `Task 9.3` | `M-SU-D2-08` |
| `C5-12` | `candidate_ledger` 雙 `set_index` ＋ `.loc[eid]` | 甲 | 事件級＋防誤改回歸 | `Task 9.3` | `M-SU-D2-09` |
| `C5-13` | `tables` 之 `set_index` ＋ `.loc[eid]` 三處〔ANCHOR `momentum/Analysis/event_samples/tables.py:214` TOKENS `ev` `=` `receipts` `.` `event_level` `.` `set_index` `(` `"event_id"` `)`〕〔ANCHOR `momentum/Analysis/event_samples/tables.py:229` TOKENS `cl` `=` `event_split_plan` `.` `clusters` `.` `set_index` `(` `"event_id"` `)` `if` `event_split_plan` `is` `not` `None` `else` `None`〕〔ANCHOR `momentum/Analysis/event_samples/tables.py:373` TOKENS `clus` `=` `event_split_plan` `.` `clusters` `.` `set_index` `(` `"event_id"` `)` `[` `"time_cluster_id"` `]` `.` `reindex` `(` `idx` `)` `if` `not` `event_split_plan` `.` `clusters` `.` `empty` `else` `pd` `.` `Series` `(` `range` `(` `len` `(` `idx` `)` `)` `,` `index` `=` `idx` `)`〕 | 甲 | 事件級＋防誤改回歸 | `Task 9.3` | `M-SU-D2-06` |
| `C5-14` | `baseline` 之事件級索引〔ANCHOR `momentum/Analysis/event_samples/baseline.py:123` TOKENS `"n_test_samples"` `:` `int` `(` `len` `(` `idx` `)` `)` `,`〕 | 甲 | 隨上游同步；依 `D-002-C6` (6.2) 拆 `n_test_events`／`n_test_samples` 並刪舊鍵 | `Task 9.4` | `M-SU-D2-31`／`M-SU-D2-32` |
| `C5-15` | 前端 `frontend/src/lib/types.ts` 之 `batch_facts` | 甲 | 批次級彙總，不動 | `Task 9.5` | — |
| `C5-16` | `tests/golden/splitunify/clusters_oracle.json` | 甲 | 事件級，不動 | `Task 9.5` | — |
| `C5-17` | `report_int_keys.json` | 甲 | 事件級，不動 | `Task 9.5` | — |
| `C5-18` | 前端 `frontend/src/app/search/page.tsx` 之 `byEventId` Map | 甲 | 排除於複合鍵遷移之外（(5.4)） | `Task 9.5` | `M-SU-D2-11` |
| `C5-19` | `split_projection.build_event_keys` 輸出〔ANCHOR `momentum/Analysis/event_samples/split_projection.py:329` TOKENS `columns` `=` `{` `"timeframe"` `:` `"feature_timeframe"` `}`〕〔ANCHOR `momentum/Analysis/event_samples/split_projection.py:351` TOKENS `on` `=` `"event_id"` `,` `how` `=` `"inner"` `,` `validate` `=` `"many_to_one"` `,`〕〔ANCHOR `momentum/Analysis/event_samples/split_projection.py:362` TOKENS `"timeframe"` `,` `"feature_timeframe"` `]`〕 | 乙 | 以 `per_tf` 為行粒度接合、新建 `feature_timeframe` 欄 | `Task 9.2` | `M-SU-D2-23`／`M-SU-D2-26` |
| `C5-20` | `split_projection` 之 `assignments` 組裝（聚合 seam `_aggregate_event_level_split_rows`） | 甲 | 事件級一事件恰一列，欄 `["event_id","symbol","split_label"]`；經具名 seam 逐欄驗值，不得以 `drop_duplicates`／`set` 靜默吞掉異常 | `Task 9.3` | `M-SU-D2-41`／`M-SU-D2-42`／`M-SU-D2-43` |
| `C5-21` | `split_projection` 之 `purged` 組裝〔ANCHOR `momentum/Analysis/event_samples/split_projection.py:875` TOKENS `purged` `=` `pd` `.` `DataFrame` `(` `purge_rows` `,` `columns` `=` `list` `(` `_PURGED_COLUMNS` `)` `)`〕〔ANCHOR `momentum/Analysis/event_samples/split_projection.py:477` TOKENS `purge_rows` `.` `append` `(` `{` `"event_id"` `:` `eid` `,` `"reason"` `:` `_PURGE_REASON` `}` `)`〕 | 甲 | 事件級一事件恰一列，欄 `["event_id","reason"]`；跨表互斥斷言保留 | `Task 9.3` | `M-SU-D2-41`／`M-SU-D2-44` |
| `C5-22` | golden 之 `g1_membership` | 甲 | 事件級，不擴維；多週期涵蓋由 `receipts.per_tf` 列數守恆守 | `Task 9.5` | `M-SU-D2-16`／`M-SU-D2-17` |
| `C5-23` | `test_splitunify_wiring.py` 之 `dict(zip(...))` 映射〔ANCHOR `tests/momentum/event_samples/test_splitunify_wiring.py:110` TOKENS `cutoffs` `=` `dict` `(` `zip` `(` `res` `.` `receipts` `.` `per_tf` `[` `"event_id"` `]` `,` `res` `.` `receipts` `.` `per_tf` `[` `"feature_cutoff_ms"` `]` `)` `)`〕〔ANCHOR `tests/momentum/event_samples/test_splitunify_wiring.py:111` TOKENS `labels` `=` `dict` `(` `zip` `(` `res` `.` `split_plan` `.` `assignments` `[` `"event_id"` `]` `,` `res` `.` `split_plan` `.` `assignments` `[` `"split_label"` `]` `)` `)`〕 | 甲 | 維持單鍵映射；對 `receipts.per_tf` 為 lossy seam ⇒ 逐事件比對決策錨點與標籤，不得只比集合成員 | `Task 9.4` | `M-SU-D2-12` |
| `C5-24` | `pattern_bridge` 之 `assign.set_index("event_id")["split_label"]` | 甲 | 不改碼；防誤改為複合鍵索引之回歸 | `Task 9.3` | — |
| `C5-25` | `ic_feed` survivor 餵入端：雜湊 seam＝`event_context_from_windows` 之 `rows` 組裝，呼叫端＝`pipeline.event_context_for_analysis`〔ANCHOR `momentum/Analysis/event_samples/ic_feed.py:65` TOKENS `manifest_hash` `=` `hashlib` `.` `sha256` `(` `json` `.` `dumps` `(` `rows` `,` `sort_keys` `=` `True` `,` `separators` `=` `(` `","` `,` `":"` `)` `)` `.` `encode` `(` `"utf-8"` `)` `)` `.` `hexdigest` `(` `)`〕〔ANCHOR `momentum/Analysis/event_samples/ic_feed.py:57` TOKENS `(` `{` `"event_id"` `:` `str` `(` `w` `.` `event_id` `)` `,` `"label_start_ms"` `:` `int` `(` `w` `.` `label_start_ms` `)` `,` `"label_end_ms"` `:` `int` `(` `w` `.` `label_end_ms` `)` `}`〕〔ANCHOR `momentum/Analysis/event_samples/pipeline.py:409` TOKENS `return` `event_context_from_windows` `(`〕 | 丙 | 去重發生在 seam 內（任一呼叫端皆受保護）；同 ID 之 `label_start_ms`／`label_end_ms` 不完全相同即 raise | `Task 9.3` | `M-SU-D2-38` |
| `C5-26` | `pipeline` 之 summary counts（`n_train`／`n_test`／`n_purged`）〔ANCHOR `momentum/Analysis/event_samples/pipeline.py:825` TOKENS `"n_train"` `:` `int` `(` `plan` `.` `assignments` `.` `loc` `[` `plan` `.` `assignments` `[` `"split_label"` `]` `==` `"train"` `,` `"event_id"` `]` `.` `nunique` `(` `)` `)` `if` `not` `plan` `.` `assignments` `.` `empty` `else` `0` `,`〕〔ANCHOR `momentum/Analysis/event_samples/pipeline.py:826` TOKENS `"n_test"` `:` `int` `(` `plan` `.` `assignments` `.` `loc` `[` `plan` `.` `assignments` `[` `"split_label"` `]` `==` `"test"` `,` `"event_id"` `]` `.` `nunique` `(` `)` `)` `if` `not` `plan` `.` `assignments` `.` `empty` `else` `0` `,`〕〔ANCHOR `momentum/Analysis/event_samples/pipeline.py:827` TOKENS `"n_purged"` `:` `int` `(` `plan` `.` `purged` `[` `"event_id"` `]` `.` `nunique` `(` `)` `)` `if` `not` `plan` `.` `purged` `.` `empty` `else` `0` `,`〕 | 丙 | 以 `event_id` 去重計數；列數另立新名 | `Task 9.4` | `M-SU-D2-13` |
| `C5-27` | `split_projection` 之 `per_symbol_n`／`per_symbol_test_n` 與 `tier_min_test_events` 門檻〔ANCHOR `momentum/Analysis/event_samples/split_projection.py:881` TOKENS `per_symbol_n` `:` `Dict` `[` `str` `,` `int` `]` `=` `{`〕〔ANCHOR `momentum/Analysis/event_samples/split_projection.py:893` TOKENS `per_symbol_test_n` `=` `{` `s` `:` `n_test` `for` `s` `in` `per_symbol_n` `}` `,`〕〔ANCHOR `momentum/Analysis/event_samples/split_projection.py:1077` TOKENS `if` `int` `(` `per_symbol_test_n` `.` `get` `(` `s` `,` `0` `)` `)` `<` `int` `(` `tier_min_test_events` `)`〕 | 丙 | 以 `event_id` 去重計數；`per_symbol_test_n` 為內部門檻參數、不是 summary 鍵 | `Task 9.3` | `M-SU-D2-43` |
| `C5-28` | 前端 `EventTablesPanel.tsx` 之 `train／test／purge` 計數顯示〔ANCHOR `frontend/src/components/ic-analysis/EventTablesPanel.tsx:361` LINESHA256 `2ba4a3f753f56049873446217a6e9c0be22a81235b075ab2c8c819634598ce16`〕〔非 `.py`：以正規化整行 sha256 相等＋該行在全 repo 之 `.ts`／`.tsx` 中恰好一次判定；掃描跳過 `node_modules`／`.next`／`dist`／`build`／`coverage`〕 | 丙 | 顯示值須為事件數；`R-5` 使本列首次有生產資料流，改由 `Task 10.4` 交付 | `Task 10.4` | `M-SU-R5-07` |
| `C5-29` | `tables.py` 之 `assignments.set_index("event_id")["symbol"].reindex(idx)`〔ANCHOR `momentum/Analysis/event_samples/tables.py:372` TOKENS `sym` `=` `event_split_plan` `.` `assignments` `.` `set_index` `(` `"event_id"` `)` `[` `"symbol"` `]` `.` `reindex` `(` `idx` `)`〕 | 甲 | 不改碼；防誤改回歸 | `Task 9.3` | — |

### D-002-C6 事件數與列數是兩個量

<!-- OBLIGATIONS-BEGIN id=D-002-C6 -->
**(6.1) 三個量之定義**：`n_events`＝`event_keys` 去重後之 `event_id` 數；`n_event_tf_rows`＝`event_keys`（稽核層）之 `(event_id, feature_timeframe)` 列數；`n_train`／`n_test`／`n_purged`＝`assignments`／`purged`（事件級）以 `event_id` 去重之計數。三者不得互相代用；`n_event_tf_rows` 不得由 `len(assignments)+len(purged)` 推得。
**(6.2) 逐消費者定義粒度**：`split_projection` 之 `summary`、報告分母、前端顯示、wiring 斷言之 `n_train`／`n_test`／`n_purged` 維持事件數。`baseline` 回傳 schema 為 exact：刪除舊鍵 `n_test`，同時輸出 `n_test_events`（test 指派之去重事件數）與 `n_test_samples`（`len(idx)`）；物化允許事件進 `failures` 而不進 `features`，故兩量不恆等。
**(6.3) 缺陷判準**：任一消費面把列數當事件數顯示或斷言即為缺陷。
**(6.4) 稽核計數之公式**：`n_event_tf_rows_purged == int(event_keys["event_id"].isin(set(purged["event_id"])).sum())`，單標的與多標的共用此定義；不得以 `len(purged)` 計。
**(6.5) 守恆**：`n_train + n_test + n_purged == n_events`（事件數守恆，非列數）。
<!-- OBLIGATIONS-END -->

### R5-C1 事件掃描端之 canonical 邊界必須與 IC 分析端逐值相同

「同一條邊界」之定義：同一事件批、同一 FF run、同一 IC 設定下，事件掃描端所得之 `train_plan`／`test_plan`（`row_index`、`row_index_local`、
`time_bounds`、`row_time_fingerprint`、`purge_gap`、`embargo`、`base_universe_hash`）與 post-trim `feature_index`，
與 IC 分析端 `ic_filter_orchestrator.analyze` 切分分支所建者**逐值相等**。

決定邊界（1–4）與進入投影之事件集合（5）之輸入為封閉清單，缺一即兩端可能不同（偵察實跑：`purge_gap` 少算事件答案窗成分即差 7 小時；切分參數不同可差 2040 小時）：
1. FF run 識別 `(symbol, timeframe, config_hash)`；
2. post-trim universe＝FF run 特徵索引 ∩ K 線期間（`_intersect_features_with_kline_period`，K 線來源＝`data_cache/feature_klines`）；
   事件對齊所用之 bars 須載入 `trigger_timeframes ∪ {feature_run.timeframe}`，使 `receipts.per_tf` 含 run feature TF 之列（只載觸發 TF 時 `build_event_keys(selected_timeframe=feature_run.timeframe)` 必 fail-closed）；
3. 生效 `ICConfig`（`load_ic_config(api_override=config_override)` 後經 orchestrator 之 `_apply_config_override`／`_apply_tier_config`）之
   `ic_train_test_split`、`oos_test_size`、`min_test_rows`、`embargo` 與 label horizon 來源；
4. 事件隔離列數：`event_isolation.label_window_rows`（抬高 `purge_gap`）與 look-ahead 深度列數（抬高 `embargo`，只升不降）；
5. 事件集合：coverage 剔除（run 期間外）與 run symbol 過濾後之事件。

### R5-C2 單一實作：邊界解析住 momentum，兩端共同呼叫

1. 輸入 3–5 之解析與 plan 建立抽成 momentum 內**單一**入口（經 `momentum/factories.py` 出口供 service 取用），
   IC service 之事件路徑與 `EventImportService` **共同呼叫**；**禁**事件端複製 IC service 之解析段落。
2. `check_feature_run_coverage`（現住 `api/services/ic_analysis_service.py`）與「look-ahead 深度列數抬高 `embargo`」之規則移入 momentum，
   IC service 改呼叫移入後之版本；Rule 4（services 不互 import）與 Rule 1（`momentum/` 不 import `api/`）不得破。
3. plan 之建立沿用 `_build_holdout_split_plan`（不得另寫第二份 plan 建構）；其 `SkippedResult`（列數低於 `min_test_rows`）
   於事件掃描端依 R5-C3 5. 回 `unavailable` 與具名原因，不得以事件數另切。
4. 下沉本身為行為不變型重構：非事件 run 報告逐位元組不變（G-2）；IC 事件 run 之報告數值於 `Task 10.2` 前後逐值不變。
   本票不改 IC 事件路徑之事件歸屬規則（R5-C7）。

### R5-C3 請求與回應契約

1. `EventAnalyzeRequest` 新增選填 `feature_run`（`symbol`、`timeframe`、`config_hash` 三欄皆必填、非空字串）與選填 `config_override`
   （語意同 IC 請求之同名欄）。**無「取最新 run」之 fallback**：`config_hash` 缺即 422，不得回退 `find_latest_materialized`。
2. `feature_run` 缺席 ⇒ C-0 3.(ii) 既有分支，回應形狀逐位元組同 v5（`Task 3.3` 回歸）。
3. `feature_run` 存在且解析成功 ⇒ `capability={"split":"ok"}`；`summary` 含 `n_train`／`n_test`／`n_purged`（事件數）與 `summary.split`（C-5 之 16 鍵扣 `per_symbol_n`）；
   回應新增 `split_unify`（鍵集＝`split_unify_keys`，唯一產生點 `build_split_unify_disclosure`）、`period_alignment`（被 coverage 剔除之事件 ID 與計數）與 `excluded_by_symbol`（R5-C4 2.）。
   三個新欄須宣告於 `api/models/event_import_models.py` 之 `EventAnalyzeResponse`（該 route 以 `response_model` 序列化，未宣告之頂層鍵會被丟棄），並以 route 層測試驗其經 HTTP 回應仍在。
4. `feature_run` 存在但**輸入錯誤**（run 不存在、`symbol`／`timeframe` 與 registry 條目不符、post-trim 交集為空、coverage 與 run symbol 過濾後零事件）⇒
   HTTP 4xx 具名錯誤，**不得**改走 event-study-only 冒充成功。
5. `feature_run` 存在、輸入正確但**依 IC 設定沒有 canonical 邊界**（生效 `ic_train_test_split` 為關；或列數低於 `min_test_rows`，即 `_build_holdout_split_plan` 回 `SkippedResult`）⇒
   與 IC 端之全樣本 fallback 對應：`capability={"split":"unavailable","reason":<具名原因>}`，回應形狀同 C-0 4.(a)–(c)。
   新增原因字面 `canonical_holdout_disabled`、`canonical_holdout_insufficient_rows` 登記於 `split_unify.json` 之 `fail_closed_reasons`（C-8），前端文案與既有兩條可分辨。
6. 深度不可證（C-0 3.(i)）優先於本節全部。
7. 新增之欄名依 `D-002-C0` (0.6) 分名，不得用裸 `timeframe` 新造欄；請求既有之 `test_fraction`／`embargo_ms`／`tier_min_test_events` 與表用 `horizons`
   **不得**作為 canonical 邊界之輸入（同名異義：`test_fraction` 預設 0.3 而 `ICConfig.oos_test_size` 預設 0.2；`embargo_ms` 為毫秒而 IC `embargo` 為列）。

### R5-C4 事件集合之處置

1. 投影對 `decision_at_ms` 落在 post-trim `feature_index` 之 `[index_ms[0], index_ms[-1]]` 外之事件 raise（C-4 步驟 0④），
   而現行 `check_feature_run_coverage` 以 run manifest 之時間區間判定（裁頭尾前）⇒ 事件掃描端於呼叫投影**之前**依序：
   (a) R5-C2 之 coverage 剔除；(b) 以 post-trim `feature_index` 首尾剔除 `decision_at_ms` 界外事件。
   兩步被剔除之 `event_id` 與原因寫入 R5-C8 之處置帳並揭露於回應；剔除後零事件 ⇒ fail-closed。
2. **run symbol 過濾與 IC 端同形**（IC 事件路徑之既有規則：只餵 `symbol == run symbol` 之事件，他 symbol 具名排除）：
   批內他 symbol 之事件於投影前排除，回應揭露「被排除之 symbol 與各自事件數及 `event_id`」；過濾後零事件 ⇒ R5-C3 4. 之 4xx。
   投影入口維持單標的，不以單一 run 之 plan 解釋他 symbol 之事件。
3. 事件之 feature TF 列：對齊時載入 `trigger_timeframes ∪ {feature_run.timeframe}`（R5-C1 2.），`build_event_keys` 以 `selected_timeframe=feature_run.timeframe` 取用；其餘 feature TF 列數進 `discarded_rows_by_feature_tf` 並揭露。
4. coverage 剔除與 run symbol 過濾共用 IC 端之同一實作（R5-C2 2.），順序與 IC 端相同。

### R5-C5 `SU-RESID-9A-UI` 隨本批交付

`R-5` 使 `api/` 出現帶 canonical 邊界之 `EventSamplePipeline.run` 生產呼叫，觸發 `SU-RESID-9A-UI`。本批交付：
`summary.split.discarded_rows_by_feature_tf` 與 `insufficient_events_in_test` 於 API 回應可得，事件掃描面板顯示之；
`metadata.split_unify` 之 `discarded` 層維持不適用（IC 路徑不呼叫 `build_event_keys`，`M-SU-D2-03` ID 不回收）。

### R5-C6 `Task 3.3` 分支保留與對照

事件掃描端之 event-study-only 分支（C-0 3.(i)(ii)）**不得刪除**；有 FF run 之投影路徑為**新增**之對照路徑。
同一事件批「無 FF run」與「有 FF run」兩次呼叫之 `tables` 差異屬 C-9 之預期數值變動，驗收以逐鍵 diff 揭露，不以相等斷言。

### R5-C7 🔴 兩端驗證段事件集合之對證（IC 事件歸屬規則不改）

兩端判定測試段事件之規則不同：IC 事件路徑以 stage3 保留之事件列（列時刻＝`feature_cutoff_ms`）落在 `test_plan.time_bounds` 閉區間者為測試段
（`ic_filter_orchestrator._derive_stage_masks`；`metadata.split_unify.n_test = test_mask.sum()`）；投影 `derive_event_split_from_plans` 以 `decision_at_ms` 三段式判側（C-4；`D-002-C3` (3.1)），test 事件進 `assignments`。
結構性質：`feature_cutoff_ms = max{close_ms ≤ decision_at_ms}`（`alignment._select_cutoff_idx`）且與 post-trim `feature_index` 同一 K 線網格時，
`decision_at_ms ≥ test_start_ms ⇔ feature_cutoff_ms ≥ test_start_ms`；test 側事件不受答案窗 purge ⇒ 兩規則之測試段事件集合在 IC stage3 保留之事件內相等。

決議：
1. IC 事件路徑之事件歸屬規則與 `metadata.split_unify.n_test` 之算法**不改**（非事件 run 與 IC 事件 run 之數值於本票皆不變）；`split_unify.json` 之 `test_segment_count_keys` 登記不變。
2. 兩端差集之唯一合法來源＝IC 端未進入測試段遮罩之事件；每個差集 `event_id` 之原因**只能**取自 R5-C8 處置帳中 IC 端之原因欄，
   對證腳本不得自行產生、補填或改寫原因。處置帳缺該 `event_id` 或原因不在封閉值集 ⇒ fail。
   其他任何差異＝接線缺陷（K 線網格不同、cutoff 取法不同、參數不同），fail。
3. 隔離帶內 `decision_at_ms > train_last_ms` 而 `feature_cutoff_ms ≤ train_last_ms` 之事件：投影判 purged、IC 判訓練段——兩端之訓練段／隔離之歸屬可不同，
   不影響測試段與 `n_test`；本票不對齊，列為誠實邊界（改 IC 訓練段成員屬 C-9 數值變動，無 `n_test` 對齊收益）。
4. 驗收：同一事件批、同一 FF run、同一 `config_override` 下，`IC 測試段 event_id 集合 == 投影 test 集合 − 處置帳記為 IC 端未消費之事件`（真實資料，`Task 10.5`）。
   IC 測試段 `event_id` 集合取自 IC 分析實際產出（測試段遮罩命中之事件列時刻經 `event_label_owners` 回綁 `event_id`），**不得**由處置帳推導——處置帳為預測、IC 產出為觀測，兩者獨立。

### R5-C8 逐事件處置帳（兩端差集與剔除揭露之唯一來源）

1. 產生者＝`Task 10.2` 之單一入口；對輸入批中每個通過匯入驗證之 `event_id` 恰一列，欄＝`event_id`、`symbol`、`scan_disposition`、`ic_disposition`。
2. 值集封閉，登記於 `momentum/Analysis/contracts/split_unify.json` 新鍵 `event_disposition_values`（C-8）：
   - `scan_disposition` ∈ {`projected`, `align_failed`, `symbol_not_run_symbol`, `outside_feature_run_coverage`, `outside_post_trim_index`}；
   - `ic_disposition` ∈ {`ic_consumed`, `align_failed`, `symbol_not_run_symbol`, `outside_feature_run_coverage`, `label_value_unavailable`, `cutoff_row_not_in_feature_index`}。
3. 判定順序與 IC service 事件路徑相同（對齊 → run symbol → coverage → label 值 → 特徵列）；事件掃描端另於 coverage 之後判 `outside_post_trim_index`（R5-C4 1.(b)）。
4. 事件掃描回應之 `period_alignment` 與 `excluded_by_symbol` 由處置帳導出，不另算。
5. 處置帳本身不得作為「兩端相等」之證據：`Task 10.5` 以 IC 實際產出對證（R5-C7 4.）。

## §G Golden / Baseline

**成員與全域**：
- **G-1 成員集合 golden**：`tests/golden/splitunify/splitunify_golden.json` 之 `assignments`／`purged` 成員集合逐一凍結；成員集合**維持事件級、不擴維為 event×TF**（`C5-22`）。
- **G-2 全域路徑逐位元組不變**：非事件 run 之報告 canonical bytes 之 sha256 不得改變（比對方式同 `scripts/freeze_evtlabel_survivor_golden.py`：去 `generated_at` 後 sha256）。`R-5` 之共用解析下沉（`Task 10.2`）同受本條約束。
- **G-3a 一次性遷移報告**：新舊 producer 差集寫入 `handoffs/run_receipts/`，附 `diff_event_ids` 之 sha256 與基數，**不進**預設比對綠徑。
- **G-3b 長期 golden**：投影 vs **獨立 oracle** `_oracle_membership`（`scripts/freeze_splitunify_golden.py`）——以事件級 `decision_at_ms` 三段式逐行重寫、**不 import 投影**；`g1_membership != g3b_oracle` 即 FAIL。
- **G-4 per-symbol counts golden**：多 symbol 批之逐標的計數整數逐值相等。
- **G-5 containment 四項**：① 逐 row test fingerprint（`(position, feature_ts_ms, symbol, base_universe_hash)` 之 exact sha256，失敗指名第一個 mismatch position）；② 逐 event `assignments`／`purged` IDs 互斥、涵蓋全集、reason 字面相符，失敗輸出 diff 之 event_id；③ answer-window 完整性；④ leakage negative case（train 事件之 `label_end_ms` 推進 test ⇒ 必進 `purged`）。
- **數值比較規約**：計數整數逐值相等；浮點 `atol=1e-12`／`rtol=1e-9`。

**多 feature TF 與交錯組**：
- **D-002 (G-1)**：`build_row_time_fingerprint` 之 payload 不含 TF 欄 ⇒ 複合鍵本身不移動 g5。
- **D-002 (G-2)**：兩標的交錯、每事件兩 feature TF 之 fixture 以**平行新鍵**（`g2_interleaved_*`）承載；單標的舊鍵保留為回歸錨、不得刪除或覆寫。
- **D-002 (G-3)**：多 TF 組中 `feature_timeframe` 只作分組鍵，不進 g5 payload；成員集合事件級、不擴維；多週期涵蓋由 `receipts.per_tf` 列數守恆驗。
- **D-002 (G-4)**：事件級 `decision_at_ms` 錨定為正確語意（`feature_cutoff_ms <= decision_at_ms` 允許 `cutoff < decision`，以 cutoff 判側之舊路徑會讓邊界事件改側）；單 TF golden 已依錨定重凍於版本化新鍵 `g1_membership_v9`／`g3b_oracle_v9`，換錨前之值保留。
- **D-002 (G-4c)**：`_oracle_membership` 以 decision-anchor 逐行重寫且不 import 投影 ⇒ G-3b 抓「只改一邊」之不對稱錯誤。
- **D-002 (G-4d) v8 不可變基準**：
  1. `tests/golden/splitunify/splitunify_golden.v8.json` 與 `.v8.sha256` 為 **write-once**（`O_CREAT|O_EXCL` 建立，已存在即拒）；`--write` 對 v8 一律 `raise`。
  2. 每次執行（比對與重凍兩模式）驗「本檔 §V 錨點 ＝ 旁檔 ＝ 檔案實際 digest」三者相等；錨點只認本檔 §V 區段（`HISTORY` 區無效），由 helper 只讀、不得改寫。
  3. 主檔既有頂層鍵之值改動須逐鍵授權 `<key>=<old8>:<new8>`（各取該值 canonical JSON sha256 前 8 碼）；只列鍵名不算授權；授權列了未實際改變之鍵即 raise。
  4. `decision_at_ms == feature_cutoff_ms` 之事件相對 v8 零位移（硬斷言）；fixture 含 `decision_at_ms != feature_cutoff_ms` 之單 TF 邊界事件（`bnd_shift`），其側別等於三段式期望側。
  5. 允許差異集合＝`g1_membership_v9` 與 v8 之逐 `event_id` diff，且其中每筆須同時被 `_oracle_membership` 與 fixture 之 `expected_side` 認可。
- **D-002 (G-4e) 第三份判準**：`_event_keys()` 逐筆帶人手填入之字面 `expected_side` 與 `expected_decision_at_ms`（不可變字面，不得由 fixture 常數推導、不讀 `feature_index`、不經 `holdout_boundary`）；`main()` 先逐筆時刻對帳，再 `ASSERT 投影側 == oracle 側 == expected_side`。第三份**不得** import／呼叫投影、`_oracle_membership` 或兩者之共用 helper。誠實邊界：填值者照錯誤理解填時三份仍一致——屬 `SU-RESID-V8-ATTEST` 面 b，非機械保證。

**`R-5`（`Task 10.5`）**：新增「IC 分析端與事件掃描端對同一 FF run／同一事件批之 canonical 邊界逐值相等、驗證段事件集合依 R5-C7 4. 對證」之真實資料 golden（`test_plan.row_time_fingerprint`、`test_start_ms`、`train_row_index` 逐值相等；測試段 `event_id` 差集只准為 R5-C8 處置帳記為 IC 端未消費之事件），fixture 必用 `data_cache/` 真實 FF run 與 kline，禁合成。

## §P Phase 與依賴

### 既有批次之存續義務

批次狀態之唯一權威＝`scripts/fact_keys.json` 之 `splitunify-batch-status`（生成於 `docs/SPLITUNIFY_TODO.md` §B）；施工細目見 TODO §C。下表只列**仍有效**之義務與其承重測試：

| Task | 存續義務 | 承重測試／工具 |
|---|---|---|
| `Task 1.1` | `docs/GAP3_EVENT_UX_SPEC.D-002.md` 含 `kline_holdout`、post-trim 字面與正確規格入口路徑 | `bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_SPEC.D-002.md` |
| `Task 1.2` | `split_unify.json` 為值集唯一真相源；缺鍵或空值集 import 期 raise；不含 `assignment_states`；本檔逐字含每一個 fail-closed reason | `tests/momentum/Analysis/test_splitunify_contract.py` |
| `Task 1.3` | `tests/baselines/analysis_known_failures.nodeids` 由實跑產出、只准變短；變短同 commit 更新清單與 receipt，commit 訊息標 `splitunify-baseline-sync`；不得手寫 nodeid、不得放入本票新測試 | `pytest --collect-only $(cat tests/baselines/analysis_known_failures.nodeids)` rc=0 |
| `Task 2.1` | `holdout_boundary` 為唯一邊界算術，以 `holdout_split_point`＋`holdout_test_row_index` 定義；回 `train_row_index`／`test_row_index`／`train_end_ms`／`test_start_ms`；ms 同源且只供揭露；空 index raise；空段 ms 回 `None` | `tests/momentum/core/test_splitunify_boundary.py` |
| `Task 2.3` | `scripts/freeze_splitunify_golden.py` 預設比對、失敗 rc=1 並指名 event_id；比對失敗不得自動 `--write` | `venv/bin/python scripts/freeze_splitunify_golden.py` rc=0；`tests/momentum/Analysis/test_splitunify_golden.py` |
| `Task 3.1` | orchestrator 經 `holdout_boundary` 取列計畫；`EventSamplePipeline.run` 之 canonical 邊界三參數同時給齊；`split_events` 生產呼叫點數＝0；投影路徑 `config.split` 之兩個 embargo 欄須為 `None` | `tests/momentum/event_samples/test_splitunify_wiring.py` |
| `Task 3.3` | 事件掃描端 event-study-only 分支保留（C-0 3.(ii)）；summary 無三計數鍵；`estimand_scope`；前端兩 reason 文案可分辨 | `tests/api/test_splitunify_event_study_only.py`；`frontend/src/components/ic-analysis/eventTablesPanelCapability.test.tsx` |
| `Task 4.1` | `metadata.split_unify` 鍵集與 fail-closed `null`；驗證段計數 deny-by-default 登記 | `tests/api/test_splitunify_disclosure.py`；`frontend/src/lib/splitAuthority.test.ts` |
| `Task 8.1` | `D-001-C1` 全部 | `tests/momentum/Analysis/test_splitunify_derive.py -k per_symbol` |
| `Task 8.2` | `D-001-C2` 全部 | `test_splitunify_derive.py -k fingerprint`；`tests/momentum/core/test_splitunify_producer_attest.py` |
| `Task 8.3` | `insufficient_events_in_test` 逐 symbol 判定 | `test_splitunify_derive.py -k insufficient` |
| `Task 9.1` | `discarded` 回傳並寫入 `EventSplitPlan.summary["discarded_rows_by_feature_tf"]`；多 symbol 原樣傳遞不相加；丟棄時不 raise；缺 TF 值 fail-closed | `test_splitunify_derive.py`（`discarded` 相關） |
| `Task 9.2` | `build_event_keys` 全量契約（C-4 producer 段）；`EventSamplePipeline.run` 不得對 `selected_timeframe` 做 `str()` 強制轉型 | `test_splitunify_wiring.py` |
| `Task 9.2a` | `clusters` 事件級；複合鍵唯一 guard 先於 (3.2) 同側檢查；兩道重複 guard 之錯誤型別維持 `ValueError` | `test_splitunify_derive.py` |
| `Task 9.2b` | C-4 判側全部；`validate_split_pair_integrity` 之呼叫點＝`EventSamplePipeline.run` 於呼叫投影**之前**（`ts`＝`feature_index` 之時刻、`symbols`＝`train_plan.symbol` 廣播）；座標四案真值表：全域 `row_index`＋全域 `ts`／`symbols` 通過、全域＋局部 `IndexError`、局部＋局部通過、局部＋全域 `CrossSymbolLeakageError` | `test_splitunify_derive.py`；`tests/momentum/event_samples/test_splitunify_m5_coords_probe.py`；`tests/momentum/event_samples/test_splitunify_g4e_triple_probe.py` |
| `Task 9.3` | C-5 聚合 seam 與事件級輸出；(5.6) register 甲類之防誤改回歸；`C5-25` seam 內去重且 `event_manifest_hash` 對唯一輸入不變 | register 所列各測試；`venv/bin/python scripts/register_anchor_check.py` rc=0 |
| `Task 9.4` | `baseline` 回傳 exact 鍵集（`n_test_events`／`n_test_samples`，無 `n_test`）；wiring 逐事件值比對 | `tests/momentum/event_samples/test_baseline_oracle.py`；`test_splitunify_wiring.py` |
| `Task 9.5` | §G 之 D-002 (G-2)(G-4d)(G-4e)；前端 `byEventId` 事件級 | `test_splitunify_golden.py`；`frontend/src/app/search/eventExportByEventId.test.tsx` |

### Phase 10 — `R-5` 事件掃描端取得 post-trim feature universe（依賴：本檔三家戳記、使用者審閱放行、`docs/SPLITUNIFY_TODO.md` 依本版重寫並凍結）

（`Task 10.1`～`Task 10.5` 之細目見下；落點與 fail-closed 以 `R5-C1`～`R5-C8` 為準。）

**Task 10.1 — 規格讀取者改指本檔**
- 目標：以路徑讀取 `docs/SPLITUNIFY_SPEC.D-002.md`／`D-001.md` 之生產腳本與量化測試改讀本檔（§R0 效力 2）。
- 修改檔案：`scripts/freeze_splitunify_golden.py`（`_SPEC_PATH`）、`scripts/register_anchor_check.py`（`SPEC_PATH`）、`tests/momentum/Analysis/test_splitunify_golden.py`、
  `tests/momentum/core/test_splitunify_producer_attest.py`、`tests/momentum/event_samples/test_splitunify_g4e_triple_probe.py`、`tests/momentum/event_samples/test_splitunify_m5_coords_probe.py`。既有 caller：無新增。
- 不可做：不改 `D-001`／`D-002` 之內容；不改 `tests/governance/` 之殘留清單斷言；不改錨點值。
- 邊界：① 本檔 §V 恰一行 `V8_BASELINE_SHA256=`；② register ANCHOR 子句與 `D-002` 逐字相同。
- 風險緩解：改指前後各跑一次 freeze 比對與 register 錨點閘，輸出除路徑字面外逐行相同。
- **驗證**：`venv/bin/python scripts/freeze_splitunify_golden.py` rc=0；`venv/bin/python scripts/register_anchor_check.py` rc=0 且輸出「共 22 個錨點，全數通過」；
  `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/core/test_splitunify_producer_attest.py tests/momentum/event_samples/test_splitunify_g4e_triple_probe.py tests/momentum/event_samples/test_splitunify_m5_coords_probe.py` 之 summary 行無 failed；
  `grep -rn 'SPLITUNIFY_SPEC.D-00' scripts/freeze_splitunify_golden.py scripts/register_anchor_check.py tests/momentum` 零命中。
- **存活至**：全票完工後保留。
- **覆蓋風險**：後續 Task 改動 register ANCHOR 所指碼行時依 (5.7) 重出子句，不回改本 Task 之路徑。

**Task 10.2 — 事件批 canonical 邊界解析下沉 momentum（行為不變型重構）**
- 目標：`R5-C1` 輸入 1–5 之解析與 plan 建立為 momentum 內單一入口，IC service 事件路徑改呼叫之（`R5-C2`）。
- 輸入 / 輸出：FF run 識別、`config_override`、事件批 records 與宣告、K 線讀取器 → post-trim `feature_index`、`train_plan`／`test_plan`、對齊所用 bars（`trigger_timeframes ∪ {feature_run.timeframe}`）、R5-C8 逐事件處置帳、生效之 `oos_test_size`／`purge_gap`／`embargo`、`period_alignment`、無邊界之具名原因。
- 實作要點：① 只讀 FF run 索引，不為切分載入整份特徵矩陣；② K 線讀取器固定 `data_cache/feature_klines`；③ bars 載入 `trigger_timeframes ∪ {feature_run.timeframe}`；④ `check_feature_run_coverage`、run symbol 過濾與 look-ahead 深度抬高 `embargo` 之規則移入 momentum，IC service 改呼叫；
  ⑤ plan 由 `_build_holdout_split_plan` 建立；⑥ 請求之 `test_fraction`／`embargo_ms`／表用 `horizons` 不得餵入（R5-C3 7.）；⑦ 產出 R5-C8 處置帳（含事件掃描端之 post-trim 首尾剔除，R5-C4 1.(b)），值集自 `split_unify.json` 讀。
- 修改檔案：`momentum/Analysis/event_samples/canonical_holdout.py`（新）、`momentum/factories.py`（出口）、`api/services/ic_analysis_service.py`（改呼叫）、`momentum/Analysis/contracts/split_unify.json`（新鍵 `event_disposition_values`）、
  `tests/momentum/Analysis/test_splitunify_canonical_holdout.py`（新）、`scripts/splitunify_ic_event_report_diff.py`（新；IC 事件 run 報告改前後逐鍵比對）。既有 caller：`ICAnalysisService._run_event_label_stages` 與 IC 分析主流程。
- 不可做：`momentum/` 不 import `api/`；service 不互 import；不改 `holdout_boundary` 與投影之簽名；不改 IC 任何輸出數值；不改 IC 事件歸屬規則（R5-C7 1.）。
- 邊界：① `ic_train_test_split` 關閉 ⇒ 具名原因 `canonical_holdout_disabled`；② `SkippedResult` ⇒ `canonical_holdout_insufficient_rows`；③ run 不存在／`symbol` 或 `timeframe` 不符 ⇒ 具名錯誤；④ 交集為空 ⇒ `AlignmentViolationError`（既有語意）；⑤ 事件批觸發 TF 與 run feature TF 不同（例：12h 事件 × 1h run）為合法輸入。
- 風險緩解：G-2；`M-SU-R5-01`～`03`、`M-SU-R5-10`、`M-SU-R5-13`。
- **驗證**：`venv/bin/python scripts/freeze_evtlabel_survivor_golden.py` rc=0；
  `venv/bin/python -m pytest -q tests/api/test_period_auto_align.py tests/momentum/event_samples/test_gap3_conditional_ic.py tests/api/test_splitunify_disclosure.py tests/momentum/Analysis/test_splitunify_canonical_holdout.py` 之 summary 行無 failed；
  `ASSERT canonical_holdout_entry WHEN ff_run=4a8a0b3726cc906ab3534994605e77f5 config_override=none THEN rc=0`（`test_plan.row_index` 與 `row_time_fingerprint` 與 `_build_holdout_split_plan` 逐值相等）；
  `ASSERT canonical_holdout_entry WHEN trigger_timeframe=12h feature_run_timeframe=1h THEN rc=0`（`receipts.per_tf` 含 1h 列，`build_event_keys(selected_timeframe="1h")` 不 raise，且對齊所用 bars 之週期集合 ⊇ {12h, 1h}）；
  `ASSERT canonical_holdout_entry WHEN event_decision_in_manifest_range=true event_decision_outside_post_trim_index=true THEN rc=0`（該事件 `scan_disposition=outside_post_trim_index`，不進投影）；
  `ASSERT canonical_holdout_entry WHEN disposition_value_not_in_contract=true THEN rc!=0`（處置帳值集自契約讀，手打值即紅）；
  `ASSERT splitunify_ic_event_report_diff WHEN baseline=pre_task_10_2 candidate=post_task_10_2 THEN rc=0`（真實事件批之 IC 報告逐鍵 diff 為空；receipt 寫入 `handoffs/run_receipts/`）；
  `ASSERT splitunify_ic_event_report_diff WHEN candidate_embargo_raise_removed=true THEN rc!=0`。
- **存活至**：全票完工後保留（唯一邊界解析入口）。
- **覆蓋風險**：`Task 10.3` 只新增 caller，不改本入口簽名。

**Task 10.3 — 事件掃描端接線**
- 目標：`EventImportService.analyze` 依 C-0 3. 分派；帶 FF run 時經 `Task 10.2` 入口取邊界並呼叫 `EventSamplePipeline.run(train_plan=, test_plan=, feature_index=, selected_timeframe=)`（`R5-C3`～`R5-C6`）。
- 修改檔案：`api/services/case_import_service.py`、`api/models/event_import_models.py`（請求 `feature_run`／`config_override`；回應 `split_unify`／`period_alignment`／`excluded_by_symbol`）、`momentum/Analysis/contracts/split_unify.json`（新增兩個原因值）、
  `tests/momentum/Analysis/test_splitunify_contract.py`（原因集合 exact-set 同步）、`tests/api/test_splitunify_event_scan_projection.py`（新；含 route 層測試）、`docs/GAP3_EVENT_UX_SPEC.D-002.md`（追加條目）。既有 caller：`api/routes/case.py` 之事件 analyze 端點。
- 不可做：不得刪除 event-study-only 分支；不得回退「取最新 run」；不得以 `test_fraction`／`embargo_ms` 決定邊界；不得以單一 run 之 plan 解釋他 symbol 之事件。
- 邊界：① 無 `feature_run` ⇒ 回應逐位元組同 v5；② 深度不可證優先；③ 批內 1 筆界外 ⇒ 成功、揭露該 `event_id`、其餘事件切分；④ 過濾後零事件 ⇒ 4xx；⑤ 多 symbol 批 ⇒ 只投影 run symbol 並揭露他 symbol 之排除。
- 風險緩解：`M-SU-R5-04`～`06`、`M-SU-R5-11`；register `C5-26` 之 ANCHOR 若移動依 (5.7) 重出。
- **驗證**：`venv/bin/python -m pytest -q tests/api/test_splitunify_event_study_only.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_event_scan_projection.py` 之 summary 行無 failed；其中逐條：
  `ASSERT EventImportService.analyze WHEN feature_run=absent THEN rc=0`（回應與 v5 相同）；
  `ASSERT EventImportService.analyze WHEN feature_run=valid lookahead_blocked=false THEN rc=0`（`capability.split=ok`，含三計數鍵與 `split_unify`）；
  `ASSERT EventImportService.analyze WHEN feature_run=valid lookahead_blocked=true THEN rc=0`（reason 為深度不可證）；
  `ASSERT EventImportService.analyze WHEN feature_run=unknown_config_hash THEN rc!=0`；
  `ASSERT EventImportService.analyze WHEN feature_run=valid batch_symbols=2 THEN rc=0`（揭露他 symbol 排除）；
  `ASSERT EventImportService.analyze WHEN feature_run=valid one_event_out_of_range=true THEN rc=0`（揭露該 `event_id`）；
  `ASSERT EventImportService.analyze WHEN feature_run=valid ic_train_test_split=false THEN rc=0`（reason＝`canonical_holdout_disabled`，無三計數鍵）；
  `ASSERT POST_case_events_analyze_route WHEN feature_run=valid THEN rc=0`（HTTP 回應 JSON 含 `split_unify`、`period_alignment`、`excluded_by_symbol` 三鍵且值與 service 回傳相同）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`R-3`（UAT）只新增 UAT 條目，不改本接線。

**Task 10.4 — 前端**
- 目標：IC 分析頁把已選之 `(symbol, timeframe, config_hash)` 與 `buildConfigOverride` 之結果傳入事件掃描請求；`capability.split=ok` 時顯示事件數計數、`split_unify` 揭露、被排除事件與 `discarded_rows_by_feature_tf`（`R5-C5`、`C5-28`）。
- 修改檔案：`frontend/src/lib/api.ts`、`frontend/src/lib/types.ts`、`frontend/src/lib/splitCapability.ts`、`frontend/src/components/ic-analysis/EventTablesPanel.tsx`、`frontend/src/app/ic-analysis/page.tsx`、
  `frontend/src/components/ic-analysis/eventTablesPanelSplitOk.test.tsx`（新）。既有 caller：IC 分析頁。
- 不可做：不得自行 auto-discover run；不得在 `unavailable` 時顯示計數；不得手打契約字面。
- 邊界：① 頁面未選 run ⇒ 不送 `feature_run`；② `discarded` 為空 ⇒ 不顯示該列；③ 四條 unavailable reason 文案兩兩可分辨。
- 風險緩解：`M-SU-R5-07`；`C5-28` 之 ANCHOR 行隨本 Task 移動 ⇒ 同 commit 依 (5.7) 重出。
- **驗證**：`cd frontend && node_modules/.bin/vitest run src/components/ic-analysis/eventTablesPanelCapability.test.tsx src/components/ic-analysis/eventTablesPanelSplitOk.test.tsx` rc=0；`cd frontend && npm run build` rc=0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無後續 Phase 改動本畫面。

**Task 10.5 — 真實資料兩端對證與收尾登記**
- 目標：§G 之 `R-5` 對證 golden（邊界逐值、驗證段事件集合依 R5-C7 4.）；UAT 條目登記（不執行）。
- 修改檔案：`scripts/splitunify_r5_parity.py`（新）、`tests/golden/splitunify/r5_parity.json`（新）、`docs/SPLITUNIFY_TODO.md` §E `R-3` 列之 UAT 項目。
- 不可做：禁合成 fixture；不得改既有 golden 鍵值；不執行 UAT；不改 IC 事件歸屬規則。
- 邊界：① 至少一組觸發 TF 與 run feature TF 不同之真實組合（12h 事件 × 1h run）；② 至少一組 FF run 期間與 K 線期間不同而發生裁切之真實組合；③ 對證比對 `test_plan.row_time_fingerprint`、`test_start_ms` 與測試段 `event_id` 集合，不以 `boundary_hash` 代替。
- 風險緩解：`M-SU-R5-08`、`M-SU-R5-09`、`M-SU-R5-12`。
- **驗證**：`venv/bin/python scripts/splitunify_r5_parity.py` rc=0；
  `ASSERT splitunify_r5_parity WHEN one_side_oos_test_size=0.3 THEN rc!=0`（輸出兩側 `test_start_ms`）；
  `ASSERT splitunify_r5_parity WHEN diff_event_without_ic_drop_reason=true THEN rc!=0`（輸出該 `event_id`）；
  `ASSERT splitunify_r5_parity WHEN parity_script_supplies_reason_not_from_disposition_ledger=true THEN rc!=0`（原因只准取自 R5-C8 處置帳）；
  `ASSERT splitunify_r5_parity WHEN ic_test_ids_derived_from_ledger=true THEN rc!=0`（IC 測試段集合須取自 IC 實際產出）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無後續 Phase。

**`R-5` mutation**（接續 §V 目錄）：`M-SU-R5-01` 事件端以 `test_fraction` 當 `oos_test_size`；`M-SU-R5-02` 事件端 `purge_gap` 只取 `effective_horizon`；`M-SU-R5-03` 事件端不抬高 `embargo`；
`M-SU-R5-04` 略過 coverage 剔除；`M-SU-R5-05` `config_hash` 缺時回退最新 run；`M-SU-R5-06` 刪除 event-study-only 分支；`M-SU-R5-07` `unavailable` 時仍顯示計數或 `ok` 時不顯示 `discarded`；
`M-SU-R5-08` 對證腳本只比 `boundary_hash`；`M-SU-R5-09` 對證腳本接受未附 IC 未保留原因之差集；`M-SU-R5-10` canonical 解析只載入觸發 TF 之 bars；`M-SU-R5-11` `EventAnalyzeResponse` 未宣告新欄致 route 序列化丟欄；
`M-SU-R5-12` 對證腳本自行填寫差集原因（不讀處置帳）；`M-SU-R5-13` 事件掃描端只做 manifest 區間 coverage、略過 post-trim 首尾剔除。

## §V 驗證策略與邊界測試目錄

**測試檔目錄**：`tests/momentum/core/test_splitunify_boundary.py`（邊界 builder）、`tests/momentum/core/test_splitunify_producer_attest.py`（producer attest）、
`tests/momentum/Analysis/test_splitunify_contract.py`（契約 SoT）、`tests/momentum/Analysis/test_splitunify_derive.py`（投影）、
`tests/momentum/Analysis/test_splitunify_golden.py`（golden）、`tests/momentum/event_samples/test_splitunify_wiring.py`（接線）、
`tests/api/test_splitunify_event_study_only.py`、`tests/api/test_splitunify_disclosure.py`；`R-5` 新增測試見 Phase 10 各 Task。

**v8 不可變基準之外部錨（本行為唯一權威；helper 只讀）**：

`V8_BASELINE_SHA256=f270e007ca9843a88eff9ca40987b2110646646f52df6a63a3508c9a8dab1217`

**固定文法斷言（併入之現行態）**：
- `ASSERT derive_event_split_from_plans WHEN plans={A:(trA,teA), B:(trB,teB)} feature_index_by_symbol={A:idxA, B:idxB} THEN rc=0`
- `ASSERT derive_event_split_from_plans WHEN mapping=absent symbols=2 THEN rc!=0`（訊息含 `multi_symbol_projection_unsupported`）
- `ASSERT derive_event_split_from_plans WHEN mapping=given event_symbol=B plan_keys=A THEN rc!=0`（訊息指名 symbol 不一致，不含 `multi_symbol_projection_unsupported`）
- `ASSERT derive_event_split_from_plans WHEN plans=A,B shared_base_universe_hash=true THEN rc=0`
- `ASSERT derive_event_split_from_plans WHEN index_of=A rows_of=B THEN rc!=0`
- `ASSERT derive_event_split_from_plans WHEN interleaved=true B_global_row_max_ge_len_idxB=true THEN rc=0`
- `ASSERT derive_event_split_from_plans WHEN plan_mid_row_ts_differs=true THEN rc!=0`（訊息含 sha256 前 12 字元）
- `ASSERT derive_event_split_from_plans WHEN plan_missing=row_time_fingerprint THEN rc!=0`
- `ASSERT derive_event_split_from_plans WHEN plan_missing=row_index_local THEN rc!=0`
- `ASSERT derive_event_split_from_plans WHEN row_index_local_permuted=true THEN rc!=0`
- `ASSERT derive_event_split_from_plans WHEN row_index_local_tampered_after_build=true THEN rc!=0`
- `ASSERT producer_attest WHEN row_index_local_negative=true THEN rc!=0`
- `ASSERT producer_attest WHEN row_index_local_duplicate=true THEN rc!=0`
- `ASSERT producer_attest WHEN len_mismatch=true THEN rc!=0`
- `ASSERT producer_attest WHEN dtype=float THEN rc!=0`
- `ASSERT producer_attest WHEN frame_order=shuffled row_index_local=correct THEN rc=0`
- `ASSERT build_event_keys WHEN per_tf_timeframes=1h,4h selected=1h THEN rc=0`（`discarded == {"4h": <4h 列數>}`）
- `ASSERT build_event_keys WHEN per_tf_timeframe_has_nan=true THEN rc!=0`
- `ASSERT EventSamplePipeline.run WHEN per_tf_timeframes=1h,4h selected_timeframe=None THEN rc=0`（`len(assignments)+len(purged) == per_tf.event_id.nunique()`；`event_keys` 保留兩 TF）
- `ASSERT derive_event_split_from_plans WHEN cutoff_1h=train cutoff_4h=test decision=test THEN rc=0`（`assignments` 恰一筆該事件且 `split_label=test`）
- `ASSERT derive_event_split_from_plans WHEN decision_lt_index_first=true THEN rc!=0`
- `ASSERT derive_event_split_from_plans WHEN decision_gt_index_last=true THEN rc!=0`
- `ASSERT derive_event_split_from_plans WHEN train_rows=empty THEN rc!=0`
- `ASSERT derive_event_split_from_plans WHEN test_start_le_train_last=true THEN rc!=0`
- `ASSERT _assert_event_level_side_consistency WHEN same_event_sides=train,test THEN rc!=0`
- `ASSERT _assert_event_level_side_consistency WHEN same_event_in=assignments,purged THEN rc!=0`
- `ASSERT _aggregate_event_level_split_rows WHEN same_event_symbol_conflict=true THEN rc!=0`
- `ASSERT _aggregate_event_level_split_rows WHEN event_id_type=int THEN rc!=0`
- `ASSERT baseline WHEN test_contains=e1 materialize_failures_contains=e1 THEN rc=0`（`n_test_events=1`、`n_test_samples=0`、無 `n_test` 鍵）
- `ASSERT freeze_splitunify_golden WHEN write_target=v8 THEN rc!=0`
- `ASSERT freeze_splitunify_golden WHEN v8_and_sidecar_rewritten_together=true THEN rc!=0`
- `ASSERT freeze_splitunify_golden WHEN existing_key_changed=true authorization=absent THEN rc!=0`
- `ASSERT freeze_splitunify_golden WHEN authorization_lists_unchanged_key=true THEN rc!=0`
- summary 計數：`n_train+n_test+n_purged == n_events`；`n_event_tf_rows_purged` 依 `D-002-C6` (6.4)；summary 鍵集＝C-5 之 16 鍵。

**mutation 目錄（紅只認 rc=1；每批收批前跑）**：

| ID | 改壞什麼 | 應紅之測試 |
|---|---|---|
| `M-SU-1` | 投影二態化（purged 併入 `assignments`） | `test_splitunify_derive.py -k three_state` |
| `M-SU-2` | 未提供 Mapping 形式之多標的輸入不再 fail-closed | `test_splitunify_derive.py -k multi_symbol` |
| `M-SU-3` | 以第一個 symbol 之 plan 解釋整批事件 | `test_splitunify_derive.py -k multi_symbol` |
| `M-SU-4` | 事件錨點判側改用 `time_bounds` 閉區間 | `test_splitunify_derive.py -k membership_set` |
| `M-SU-5` | 界外事件預設歸 `train`（非 raise） | `test_splitunify_derive.py -k unmatched_timestamp` |
| `M-SU-6` | 同時落兩態時靜默取 train | `test_splitunify_derive.py -k dual_membership` |
| `M-SU-7` | `clusters` 不由 `build_time_clusters(manifest, bucket_ms)` 重算 | `test_splitunify_derive.py -k clusters` ＋ `test_tables.py` cluster CI |
| `M-SU-8` | `freeze_splitunify_golden.py` 比對失敗自動 `--write` | freeze 腳本自證 |
| `M-SU-9` | `metadata` 同時暴露事件側 `n_test` 與 canonical `n_test` 兩個驗證段數字 | `test_splitunify_disclosure.py` |
| `M-SU-10` | event-study-only 分支仍按事件數另切並宣稱 OOS | `test_splitunify_event_study_only.py` |
| `M-SU-11` | boundary builder 之 rows 或 ms 任一不同源 | `test_splitunify_boundary.py -k same_source` ＋ `-k ms_same_source` |
| `M-SU-12` | 事件 ms 與 feature index 單位未歸一 | `test_splitunify_derive.py -k unit_normalize` |
| `M-SU-13` | 拿掉答案窗 purge | `test_splitunify_golden.py -k leakage_negative` ＋ `test_splitunify_derive.py -k answer_window` |
| `C0` | 只改註解（對照組） | 必須仍綠 |
| `M-SU-D1-01` | per-symbol 合併改成只取第一個 symbol | `test_splitunify_derive.py -k per_symbol` |
| `M-SU-D1-02` | 把「跨 symbol hash 必互異」加成閘 | `test_splitunify_derive.py -k per_symbol` |
| `M-SU-D1-03` | `single_symbol` 解除條件改為無條件解除 | `test_splitunify_derive.py -k per_symbol` |
| `M-SU-D1-04` | 指紋比對只比首尾 | `test_splitunify_derive.py -k fingerprint` |
| `M-SU-D1-05` | 缺指紋欄時放行 | `test_splitunify_derive.py -k fingerprint` |
| `M-SU-D1-06` | 門檻判定退回整批 `n_test` | `test_splitunify_derive.py -k insufficient` |
| `M-SU-D1-07` | 以 A 之 `feature_index` 解 B 之 `row_index_local` | `test_splitunify_derive.py -k per_symbol` |
| `M-SU-D1-08` | 指紋列改用 `list[dict]` | `test_splitunify_golden.py` 與 `-k fingerprint` |
| `M-SU-D1-09` | 映不到之列改為丟棄 | `-k fingerprint`（交錯 fixture） |
| `M-SU-D1-10` | 投影改以全框 `row_index` 索引該 symbol 之 `feature_index` | `test_splitunify_derive.py -k per_symbol`（交錯 fixture） |
| `M-SU-D1-11` | producer attest 不等時以寫入值為準 | producer 契約測試 |
| `M-SU-D1-12` | `derive` 缺 `row_index_local` 時回退 `row_index` | `test_splitunify_derive.py -k per_symbol` |
| `M-SU-D1-13` | 建構時不複製 row 陣列 | producer 契約測試 |
| `M-SU-D1-14` | 不設唯讀 | producer 契約測試 |
| `M-SU-D1-15` | attest 判準改回 frame 序 | producer 契約測試（亂序輸入不得被誤擋） |
| `M-SU-D1-16` | 投影入口略過指紋重算比對 | `test_splitunify_derive.py -k fingerprint` |
| `M-SU-D1-17` | 以 `setflags(write=False)` 取代不可變 buffer | producer 契約測試 |
| `M-SU-D1-18` | attest 略過前置合法性閘 | producer 契約測試 |
| `M-SU-D1-19` | 投影入口 `assert_positional_rows` 改 `require_sorted=False` | `test_splitunify_derive.py -k per_symbol` |
| `M-SU-D1-20` | 只留指紋比對、移除遞增閘 | `test_splitunify_derive.py -k fingerprint` |
| `M-SU-D1-21` | 往返比對改以 `zip` 實作 | producer 契約測試 |
| `M-SU-D1-22` | 接受非整數型序號 | producer 契約測試 |
| `M-SU-D1-23` | oracle 改用 `row_index` 重算指紋 | `test_splitunify_golden.py` |
| `M-SU-D2-01` | `discarded` 不寫入 summary | `Task 9.1` 之 summary 鍵斷言 |
| `M-SU-D2-02` | `discarded` 寫入 producer 回傳但不寫入 summary | `test_splitunify_derive.py` 之 summary 鍵與值斷言 |
| `M-SU-D2-04` | `feature_materialization` 被誤改為每 feature TF 一列 | 事件級物化值斷言 |
| `M-SU-D2-06` | `tables` 之 `.loc[eid]` 被誤改為複合鍵 | `test_tables.py` 事件級 lookup 值斷言 |
| `M-SU-D2-07` | `ic_feed` 之 `set_index` 被誤改為複合鍵 | `test_gap3_conditional_ic.py` 逐列值斷言 |
| `M-SU-D2-08` | `counterexample_classifier` 被誤改為複合鍵 | `test_counterexample_classifier.py` |
| `M-SU-D2-09` | `candidate_ledger` 被誤改為複合鍵 | `test_candidate_ledger.py` |
| `M-SU-D2-10` | `dedupe` 保留集被誤改為複合鍵粒度 | `test_dedupe.py`（一事件兩 TF 皆存活而簇仍一列） |
| `M-SU-D2-11` | 前端 `byEventId` 被誤改為複合鍵 | `eventExportByEventId.test.tsx` |
| `M-SU-D2-12` | 以集合相等冒充逐列相等 | `test_splitunify_wiring.py` 多 feature TF 逐事件值比對 |
| `M-SU-D2-13` | `n_train` 改取列數 | `D-002-C6` 事件數守恆斷言 |
| `M-SU-D2-14` | (3.2) 同側檢查整個移除 | (3.2) 異側 `AlignmentViolationError` 斷言 |
| `M-SU-D2-15` | 同側檢查改為取第一側或改判 purged | 同上 |
| `M-SU-D2-16` | golden 成員集被擴成 event×TF | golden 事件級成員集逐值比對 |
| `M-SU-D2-17` | 交錯平行組直接覆蓋單標的 g5 | golden 單標的回歸錨逐值不變 |
| `M-SU-D2-18` | event-level 表被一併改為複合鍵 | event-level 粒度不變測試 |
| `M-SU-D2-19` | survivor 六鍵雜湊被改成含 feature TF | survivor 雜湊事件級測試 |
| `M-SU-D2-20` | producer 保留 `selected_timeframe` 之預設單選 | `Task 9.2` 端到端全量列數斷言 |
| `M-SU-D2-21` | 投影入口閘仍要求 `selected_timeframe` 非 `None` | `selected_timeframe=None` 不 raise 且走投影之斷言 |
| `M-SU-D2-22` | `split_label` 判定改回 `feature_cutoff_ms` | 事件級錨定反例 |
| `M-SU-D2-23` | `build_event_keys` 保留 `merge validate="1:1"` | `Task 9.2` 端到端全量列數斷言 |
| `M-SU-D2-24` | 答案窗 purge 仍用逐列 `in_train` | `Task 9.2b` purge 反例 |
| `M-SU-D2-25` | (3.2) 同側檢查被移到複合鍵唯一 guard 之前 | guard 先後斷言 |
| `M-SU-D2-26` | `build_event_keys` 以 `event_level.timeframe` 冒充 `feature_timeframe` | `feature_timeframe` 值斷言 |
| `M-SU-D2-27` | 只改投影判側、不改 `_oracle_membership` | G-3b |
| `M-SU-D2-28` | 投影與 oracle 同時以 `feature_cutoff_ms` 判側 | (G-4e) 三者全等斷言 |
| `M-SU-D2-29` | v8 基準被刪除、覆寫、與旁檔不同步，或主檔既有鍵被換錨值覆蓋 | (G-4d) 之 sha256 相等、`--write` 對 v8 raise、既有鍵逐值閘 |
| `M-SU-D2-30` | `EventSamplePipeline.run` 略過 `validate_split_pair_integrity`，或空 train 段不 raise | `Task 9.2b` pair 完整性斷言 |
| `M-SU-D2-31` | `baseline` 只輸出單一 `n_test` | 物化失敗 fixture |
| `M-SU-D2-32` | `baseline` 保留舊鍵 `n_test` | exact-key 斷言 |
| `M-SU-D2-33` | v8 以「比對後更新」建立，或期望 digest 只錨在旁檔 | write-once 與外部錨斷言 |
| `M-SU-D2-34` | §V 錨點行缺失或由 helper 改寫 | 錨點行存在且為 64-hex、非 helper 產生 |
| `M-SU-D2-38` | `event_context_from_windows` 餵入未去重 | `test_gap3_conditional_ic.py`（含重複 `event_id` 之 `event_manifest_hash` 與去重後逐字相同） |
| `M-SU-D2-41` | 事件級聚合改回逐列 append | `assignments`／`purged` 之 `event_id` 唯一斷言 |
| `M-SU-D2-42` | 聚合以 `drop_duplicates`／`set`／take-first 吞衝突 | `test_event_level_aggregation_rejects_conflicting_values` |
| `M-SU-D2-43` | `per_symbol_n`／門檻輸入以列數計 | `test_tier_min_test_events_counts_unique_event_ids` |
| `M-SU-D2-44` | `n_event_tf_rows_purged` 改回 `len(purged)` | 一 purge 事件帶兩 TF：`n_event_tf_rows_purged=2`、`n_purged=1` |

ID 不回收：`M-SU-D2-03`（`metadata.split_unify` 之 `discarded` 層，IC 路徑不呼叫 `build_event_keys`）、`M-SU-D2-05`、`M-SU-D2-35`、`M-SU-D2-36`、`M-SU-D2-37`、`M-SU-D2-39`、`M-SU-D2-40` 不在現行應紅網內，不得據以宣稱覆蓋。

benchmark：投影 O(n log n) 以內；門檻先量一次再定，不寫死未量過之數字。

## §R 回退

- 既有批次各自獨立 commit；Phase 9B（`Task 9.2`／`9.2a`）須整批回退，不得部分上線。
- `R-5`：`Task 10.2`（共用解析下沉）與 `Task 10.3`（事件掃描端接線）分屬不同 commit；回退 `10.3` 即回到 v5 之 event-study-only 行為（C-0 3.(ii) 分支始終存在）；`10.2` 回退須連同 G-2 與 IC 事件 run 報告逐鍵比對驗證。

## §N N/A 登記與殘留

**N/A 登記**：本版無省略之必填段。

**殘留**（每條帶 `為何現在不做:`；狀態之唯一權威＝`scripts/fact_keys.json` 之 `splitunify-residual-status`，本節不寫狀態）：
- `R-3` UAT 項目更新 — `為何現在不做: user-ruling:2026-09-10 使用者裁定 UAT 一律最後`；觸發：SPLITUNIFY 與 GLOBALH 之實作批次皆收批；登記處：`docs/SPLITUNIFY_TODO.md` §E。`R-5` 之 UAT 項只登記、不做（`Task 10.5`）。
- `R-4` `pattern_bridge.extract_event_patterns` 無 production caller（測試 caller 8 處） — `為何現在不做: blocked-by:接線屬 GAP-3 另一票`；本票只保證其消費之 `assignments` 語意不變；觸發：該接線票開票。
- `SU-RESID-1` attribution checker 擋不住語意歸屬錯置 — `為何現在不做: needs-research:語意對應無機械判準`；可機械化之半已由 `scripts/_synth_attr.py` 落實；具名限制、實測與觸發條件以 `docs/SPLITUNIFY_TODO.md` §E 同名列為權威。
- `SU-RESID-4` `SplitPlan.row_index`（全框）與 `row_index_local`（標的內）並存 — `為何現在不做: needs-research:是否把 row_index 本身改為 symbol-local 並遷移 IC 主線全框驗證與既有 golden`；完成判準：列出所有依賴全框語意之消費端並給出可證偽之遷移測試；觸發：下一次動 IC 切分契約。
- `SU-RESID-5` `SplitPlan` numpy 欄經序列化往返可還原為可寫；IC 全框消費端讀 `row_index` 無入口重驗 — `為何現在不做: needs-research:IC 全框消費端是否需要等價入口重驗或改以不可變容器承載 row 身分`；完成判準：可證偽之竄改測試且不影響既有 golden；觸發：下一次動 `SplitPlan` 欄位契約。
- `SU-RESID-V8-ATTEST` 倉內無獨立信任根（面 a：v8 錨／基準／旁檔／helper 同 commit 同步替換；面 b：(G-4e) 三份人手判準同步填錯） — `為何現在不做: user-ruling:2026-09-12 使用者裁定「不再擴建治理工具；同型缺陷降級為具名殘留」`；繞過成本低於合規成本，歸蓄意等價；不再加第四層副本；觸發：專案導入 commit 簽章或受保護分支（`git config --get commit.gpgsign` 為 true，或 repo 有 branch protection）；owner：SPLITUNIFY epic 主委。誠實邊界：關閉前「換錨是刻意的」之信任根是 code review 與 git 歷史。
- `SU-RESID-PAUSED-NO-RESULT` 委員該輪完全無結果列時銷帳之暫停缺席出口不適用 — `為何現在不做: blocked-by:缺該次 attempt 已終止且無產出之可信證據`；觸發：audit 出現同 round、同 family 之 `committee_family_result` 且 `result_state=failed`、`output_sha256` 為空、`output_path` 缺失或 0 byte、該輪無同家 `committee_output`；owner：治理主委。
- `SU-RESID-COMMITTEE-MODEL-EVIDENCE` 委員實際模型與 reasoning effort 不入審計 — `為何現在不做: needs-research:兩 CLI 非互動輸出之實際型號／effort 欄位與穩定解析來源尚未實測`；觸發：`committee_family_result` 登記並寫出 `model`、`reasoning_effort`、`cli_receipt_path` 三欄；owner：治理主委。
- `SU-RESID-C5-TARGETS` register 丙類列之 receipt 碼證欄不受機械對證 — `為何現在不做: blocked-by:該列尚無精確 path:line 可對證`；理由、兩條觸發條件與 owner 以 `docs/SPLITUNIFY_TODO.md` `Task 9.3` 驗收段為權威。

## 沿革與追溯索引

<!-- HISTORY-BEGIN -->
- 2026-09-17：v5 → commit `d362332d`
<!-- HISTORY-END -->

## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。
