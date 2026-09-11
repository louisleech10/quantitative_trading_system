# SPLITUNIFY_SPEC.md 延伸 D-001

BASE: docs/SPLITUNIFY_SPEC.md @ b095cc754cb9de26bbf2dd35564db329aca3c98f
PREDECESSOR: none
改什麼: 落實 §N 之 `R-1`（per-symbol 投影）與 `docs/SPLITUNIFY_TODO.md` §E 之 `SU-RESID-3`（逐列時刻同源對證），並修正 R-1 解封後才會顯形的 per-symbol 門檻失效。
為什麼: `handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md`（三家 consult，18 條）＋ `handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md`（三家對抗審，11 條；本版為 R5 後修訂）。

**類別判定＝D 延伸**（依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1）。
理由：原檔 `Task 3.2` 自身已寫「**存活至**：per-symbol 投影實作後**改寫**為支援分支（見 §N R-1）」與「**覆蓋風險**：本 Task 之 raise 分支預期被未來的 per-symbol 支援取代——屆時須連同測試一起改，不得只刪 raise」。本延伸即該預告之落地，**不推翻** C-2 的設計意圖（邊界必須 per-symbol、禁全域 scalar 冒充）——相反，它把「per-symbol」從 fail-closed 升級為真的做到。R5 兩家獨立覆核此判定成立。

🔴 **明確不在本延伸範圍**：`D1`（事件掃描端「恆走」event-study-only）之條件化。三家 consult 判其與原檔字面互斥、**須走 R 重開**；`R-5` 亦隨之留待 R 完成後另行處理。

## 觸及面宣告

新增: `D-001-C1`、`D-001-C2`、`Task 8.1`、`Task 8.2`、`Task 8.3`（原檔無對應 heading）
覆寫: `### C-2 🔴 邊界必須 per-symbol，禁全域 scalar 冒充（D2；codex 與 composer **各自標 P0**）`；`**Task 3.2 — 多 symbol fail-closed（C-2）**`；`### C-4 投影是純函式、單一實作；簽名須帶 \`feature_index\` 與 \`manifest\``；`## §N N/A 登記與殘留`
依賴: `## §V 驗證策略與邊界測試目錄`；`## §G Golden / Baseline`
不觸: `### C-0 🔴 接線落點：單一 boundary builder，拿不到 universe 就不得宣稱 OOS（D6）`；`### C-1 canonical 權威＝時間切分（D1）`

> 🔴 **C-4 由「依賴」改列「覆寫」**（R5 `COMPOSER-R5-P1-02`）：BASE C-4 之簽名逐字為 `train_plan: SplitPlan`、`test_plan: SplitPlan`、`feature_index: pd.Index`（單一 plan／單一 index）。Task 8.1 改為 per-symbol `Mapping` 即覆寫該節，不得只列依賴——否則實作端會收到互斥權威。新簽名見 D-001-C1 第 1 點。

## 內容

### D-001-C1 per-symbol 投影之身分不變式（覆寫 C-2 之 fail-closed 落點、覆寫 C-4 之簽名）

C-2 的設計意圖不變：**邊界必須 per-symbol，禁全域 scalar 冒充**。本延伸把「多 symbol 批一律 fail-closed」改為「多 symbol 批以 per-symbol 結構投影」：

1. **投影簽名（覆寫 C-4）**：

```python
def derive_event_split_from_plans(
    plans: Mapping[str, tuple[SplitPlan, SplitPlan]],      # symbol → (train_plan, test_plan)
    event_keys: pd.DataFrame,
    feature_index_by_symbol: Mapping[str, pd.Index],       # symbol → 該 symbol 之 post-trim universe
    *,
    manifest: EventManifest,
    bucket_ms: Optional[int] = None,
    tier_min_test_events: int = 1,
) -> EventSplitPlan
```

   單標的舊呼叫式（`train_plan: SplitPlan`、`test_plan: SplitPlan`、`feature_index: pd.Index`）保留為**薄 wrapper**，內部包成單鍵 Mapping 後轉呼；wrapper **不得**含第二份判定邏輯。呼叫端既未給 Mapping、也未走 wrapper ⇒ 維持 `multi_symbol_projection_unsupported`（字面續住 `split_unify.json`，不新增值）。

2. 🔴 **hash 不變式**：
   - 同一 symbol 之 `train_plan.base_universe_hash == test_plan.base_universe_hash`（既有 `validate_split_pair_integrity` 已驗，不放寬）。
   - **跨 symbol 允許共用同一字面 hash**——`ICSplitAdapter._base_universe_hash(frame, …)` 對整框算一份 joint hash 並打進每個 symbol 的 plan，是**合法且現行已發生**的 hash scope（`momentum/Analysis/ic_split_adapter.py:189-199`；`momentum/Analysis/ic_filter_orchestrator.py:907`）。
   - 🔴 **禁**把「跨 symbol hash 必互異」寫成閘——那會拒收現行 IC 多標的計畫。
   - 🔴 **身分保證之分工（R5 `GROK-R5-P2-02`；原文「改由同源對證承擔」為過歸）**：D-001-C2 之指紋證明的是**該 universe 的列時刻**；**symbol 身分**由本節第 3 點之三角相等承擔——同曆同切分的兩個 symbol 可得到相同的時刻序列，指紋不足以分辨，故兩者缺一不可。
3. **symbol 三角相等**：`plans` 的 Mapping key、該 plan 的 `plan.symbol`、以及事件集合之 symbol，三者必須相等；任一不等 ⇒ fail-closed，訊息**須指名是哪一組不一致**。🔴 **不得**復用 `multi_symbol_projection_unsupported` 字面（那是「未提供 Mapping」專用），否則「沒給結構」與「給了但 symbol 錯」無法分辨、reason 契約會漂。
4. **跨 symbol 禁共用 row_index 數字空間**：每個 symbol 各自以自己的 `feature_index` 解釋 `row_index`；合併僅發生在 `assignments`／`purged`／`clusters` 的**縱向串接**，不得跨 symbol 比較 row 位置。

### D-001-C2 逐列時刻同源對證（落實 TODO §E 之 SU-RESID-3）

現行同源對證只比每段**首尾**兩列，殘留＝「首尾相同、中間間距不同」仍會被放行。本延伸改為 producer-attested 的**完整有序**指紋：

1. **指紋 payload（對齊 §G G-5①，R5 `COMPOSER-R5-P2-01`）**：逐列四元組 `(position, feature_ts_ms, symbol, base_universe_hash)`，與 §G G-5① 及 `scripts/freeze_splitunify_golden.py` 之 canonical 序列化**同一形狀**，避免兩套 hash 與雙重維護。序列化＝依 `position` 遞增排序後 `json.dumps(rows, sort_keys=True, separators=(",",":"))`，取 `sha256`。🔴 **欄名採 §G 之 `position`／`feature_ts_ms`，不得使用舊稱 `row_pos`／`ts_ms`**——兩套欄名會讓 golden 與 plan 指紋各凍一份。
2. 🔴 **型別強制**：`position` 與 `feature_ts_ms` 必須是 Python `int(...)`——`numpy.int64` 會使 `json.dumps` 丟 `TypeError`（R5 `GROK-R5-P2-01` 已實跑），兩端若一端轉一端不轉即永遠不一致。
3. 🔴 **正規化函式點名（不得換別支）**：時刻一律走投影側之 `_index_as_ms` ／ `assert_epoch_ms_array`（epoch 毫秒、逐元素、嚴格遞增）；**明文排除** `contracts._coerce_timestamp_array`——它對純數字預設 `unit="s"`，混進指紋路徑會使秒／毫秒歧異重新出現。
4. 🔴 **取數來源**：指紋必從**該 symbol 的 post-trim `feature_index`** 取 ts，且 `row_index` 為該 index 內之 positional ordinals；**禁**以全框 ts 建指紋（producer 用全框、投影用裁切 index 時，同一 `position` 會對到不同 ts，指紋永遠紅或被硬對齊）。
5. **邊界定義**：重複 `position` ⇒ fail-closed；`NaT` ⇒ fail-closed；空 `row_index`（train 可為空）⇒ 指紋定義為 `sha256("[]")`，**不得**以缺欄代替。
6. **比對點**：投影端對傳入之 `feature_index_by_symbol[symbol]` 以同一規則重算，與 plan 攜帶之指紋逐值比對；不符 ⇒ fail-closed，訊息須指名「plan 指紋 vs 重算指紋」兩值之前 12 字元。
7. **誠實邊界（明示接受）**：本改動會使既有 IC golden digest 位移。依原檔 §G 之規矩，golden 變動須經 review；b8 收案前須把受影響的 golden 以「改前／改後逐值對照」重凍，**不得**只更新 hash。另加**獨立 oracle**（由同一 fixture 的 `row_index` 與 universe 依本節規則重算 sha256，與 plan 欄逐值相等），不單靠舊 digest 比對。
8. **首尾對證不刪**：完整指紋為**新增**層，既有首尾對證保留（承 C-1 附帶約束①「不得刪除任一既有 guard」）。

### Task 8.1 — per-symbol 投影（覆寫 Task 3.2、覆寫 C-4 簽名）

- 目標：多 symbol 批以 per-symbol 結構投影，取代「一律 raise」。
- 檔案：`momentum/Analysis/event_samples/split_projection.py`、`momentum/Analysis/event_samples/pipeline.py`（改呼叫新簽名或 wrapper）、`tests/momentum/Analysis/test_splitunify_derive.py`。
- 實作要點：①簽名依 D-001-C1 第 1 點；②逐 symbol 走現行單標的路徑（含既有 fail-closed 與同源對證）後縱向合併；③`summary.n_symbols` 由實際 symbol 數導出；④`degraded` 之 `single_symbol` **僅在 `n_symbols == 1` 時亮**——解除條件寫死為「`n_symbols > 1`」，🔴 **不得**為讓 `formal_pooled_inference_allowed` 變 `True` 而以其他方式清空 `degraded`（旗標唯一產生點＝`momentum/Analysis/event_samples/event_split.py` 之 `_degraded_flags`）。
- 不可做：不得以第一個 symbol 之 plan 冒充整批；不得刪除 `multi_symbol_projection_unsupported` 字面。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k per_symbol` rc=0，固定文法斷言逐條如下：
  `ASSERT derive_event_split_from_plans WHEN plans={A:(trA,teA), B:(trB,teB)} feature_index_by_symbol={A:idxA, B:idxB} THEN rc=0 且 set(assignments.symbol)=={A,B}`
  `ASSERT derive_event_split_from_plans WHEN 未提供 Mapping 結構 THEN rc!=0 且訊息含 multi_symbol_projection_unsupported`
  `ASSERT derive_event_split_from_plans WHEN 已提供 Mapping 但事件 symbol=B 而 plans 僅含 A THEN rc!=0 且訊息指名 symbol 不一致（且不得含 multi_symbol_projection_unsupported）`
  `ASSERT derive_event_split_from_plans WHEN plans={A,B} 且 A.train.base_universe_hash==B.train.base_universe_hash THEN rc=0`
  `ASSERT derive_event_split_from_plans WHEN 以 A 之 feature_index 解釋 B 之 row_index THEN rc!=0（跨 symbol row 空間混用，D-001-C1 第 4 點）`
  `ASSERT summary WHEN n_symbols==2 THEN "single_symbol" not in summary["degraded"]`
  `ASSERT summary WHEN n_symbols==1 THEN "single_symbol" in summary["degraded"]`

### Task 8.2 — 逐列時刻同源對證（落實 SU-RESID-3）

- 目標：關掉「首尾相同、中間間距不同」之錯分面。
- 檔案（🔴 R5 `COMPOSER-R5-P1-01`／`GROK-R5-P1-01`：**producer 寫入點必須列入**，否則只改比對端會讓生產路徑之 plan 全面缺欄、單標的綠徑全滅）：
  - `momentum/core/contracts.py`（`SplitPlan` 新增 `row_time_fingerprint` 欄）
  - `momentum/core/contracts.py::split_per_symbol`（建 plan 時寫入指紋）
  - `momentum/Analysis/ic_split_adapter.py::_build_plan_pair`（同上）
  - `momentum/Analysis/ic_filter_orchestrator.py`（holdout 路徑建 plan 處，同上）
  - `momentum/Analysis/event_samples/split_projection.py`（比對端）
  - `tests/momentum/Analysis/test_splitunify_derive.py`、`tests/golden/splitunify/splitunify_golden.json`
- 🔴 **相容性**：新欄對**非** `derive_event_split_from_plans` 之呼叫點給相容 default（避免其他建 plan 處全炸）；但 **derive 入口缺欄仍 fail-closed**，不得以 default 放行。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k fingerprint` rc=0，且 `sha256` 逐值相等；固定文法斷言逐條如下：
  `ASSERT derive_event_split_from_plans WHEN feature_index 與 plan 首尾相同但中間一列 ts_ms 不同 THEN rc!=0 且訊息含 sha256 前 12 字元`
  `ASSERT derive_event_split_from_plans WHEN feature_index 與 plan 逐列 ts_ms 相同 THEN rc=0`
  `ASSERT row_time_fingerprint WHEN 同一 index 重算兩次 THEN sha256 值 == 前次值`
  `ASSERT row_time_fingerprint WHEN 空 row_index THEN sha256 值 == sha256("[]")`
  `ASSERT derive_event_split_from_plans WHEN plan 缺 row_time_fingerprint 欄 THEN rc!=0 且訊息指名缺欄名`
  `ASSERT 生產路徑 WHEN split_per_symbol 或 ic_split_adapter 建出 plan THEN plan.row_time_fingerprint 非空`

### Task 8.3 — per-symbol 測試段門檻修正

- 目標：`insufficient_events_in_test` 改為**逐 symbol** 判定。
- 碼證：`momentum/Analysis/event_samples/split_projection.py` 現行該行條件**與迴圈變數無關**，用的是整批 `n_test`；舊實作 `momentum/Analysis/event_samples/event_split.py` 才是逐 symbol。單標的下看不出，R-1 解封後會變成「要嘛全部標不足、要嘛全部不標」。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k insufficient` rc=0，固定文法斷言逐條如下：
  `ASSERT summary WHEN symbols={A:n_test=1, B:n_test=100} tier_min_test_events=10 THEN insufficient_events_in_test==["A"]`
  `ASSERT summary WHEN symbols={A:n_test=50, B:n_test=100} tier_min_test_events=10 THEN insufficient_events_in_test==[]`

### mutation（接續原檔 §V 之表；前綴不與既有 `M-SU-B3-*`／`M-SU-B4-*` 撞號）

| ID | 改壞什麼 | 應紅之測試 |
|---|---|---|
| `M-SU-D1-01` | per-symbol 合併改成只取第一個 symbol | `test_splitunify_derive.py -k per_symbol` |
| `M-SU-D1-02` | 把「跨 symbol hash 必互異」加成閘 | `test_splitunify_derive.py -k per_symbol` |
| `M-SU-D1-03` | `single_symbol` 解除條件改為無條件解除 | `test_splitunify_derive.py -k per_symbol` |
| `M-SU-D1-04` | 指紋比對只比首尾（退回現況） | `test_splitunify_derive.py -k fingerprint` |
| `M-SU-D1-05` | 缺指紋欄時放行 | `test_splitunify_derive.py -k fingerprint` |
| `M-SU-D1-06` | 門檻判定退回整批 `n_test` | `test_splitunify_derive.py -k insufficient` |
| `M-SU-D1-07` | 跨 symbol 混用 `feature_index`（以 A 之 index 解 B 之 `row_index`） | `test_splitunify_derive.py -k per_symbol` |

### 殘留（承原檔 §N；本延伸覆寫其中一列之狀態，另一列住 TODO §E）

- `R-1`（§N）— **本延伸落實**，理由類別由 `needs-research` 解除。
- `SU-RESID-3`（TODO §E）— **本延伸落實**，理由類別由 `needs-research` 解除；其「動 IC golden digest」之代價改以 §G 重凍程序承擔（見 D-001-C2 第 7 點）。
- `SU-RESID-2`（多 TF 複合鍵）— **不在本延伸**；依 consult 收斂排於下一批，且其下游單鍵面（`feature_materialization`／`baseline`／`pattern_bridge`／`tables`／`ic_feed`／`dedupe` 之 cluster 折疊）須一併處理。未完成前，多 TF 同批維持 fail-closed。
- `R-5`／`D1` — **不在本延伸**；`D1` 須走 R 重開，`R-5` 待其完成後另行處理。
- `R-3`（UAT 最後，user-ruling）、`R-4`（屬 GAP-3，blocked-by）— 不動。

## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。
