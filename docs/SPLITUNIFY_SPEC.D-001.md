# SPLITUNIFY_SPEC.md 延伸 D-001

BASE: docs/SPLITUNIFY_SPEC.md @ b095cc754cb9de26bbf2dd35564db329aca3c98f
PREDECESSOR: none
改什麼: 落實 §N 之 `R-1`（per-symbol 投影）與 `docs/SPLITUNIFY_TODO.md` §E 之 `SU-RESID-3`（逐列時刻同源對證），並修正 R-1 解封後才會顯形的 per-symbol 門檻失效。
為什麼: `handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md`（consult 18 條）＋ `handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md`（R5 11 條）＋ `handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md`（R6 6 條；本版為 R6 後修訂）。

**類別判定＝D 延伸**（依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1）。
理由：原檔 `Task 3.2` 自身已寫「**存活至**：per-symbol 投影實作後**改寫**為支援分支（見 §N R-1）」與「**覆蓋風險**：本 Task 之 raise 分支預期被未來的 per-symbol 支援取代——屆時須連同測試一起改，不得只刪 raise」。本延伸即該預告之落地，**不推翻** C-2 的設計意圖。R5 兩家、R6 三家獨立覆核此判定成立。

🔴 **明確不在本延伸範圍**：`D1`（事件掃描端「恆走」event-study-only）之條件化，須走 **R 重開**；`R-5` 待其完成後另行處理；`SU-RESID-2`（多 TF 複合鍵）排於下一批，未完成前多 TF 同批維持 fail-closed。

## 觸及面宣告

新增: `D-001-C1`、`D-001-C2`、`Task 8.1`、`Task 8.2`、`Task 8.3`（原檔無對應 heading）
覆寫: `### C-2 🔴 邊界必須 per-symbol，禁全域 scalar 冒充（D2；codex 與 composer **各自標 P0**）`；`**Task 3.2 — 多 symbol fail-closed（C-2）**`；`### C-4 投影是純函式、單一實作；簽名須帶 \`feature_index\` 與 \`manifest\`` **之簽名段（僅該函式簽名，見下方限定句）**；`## §N N/A 登記與殘留`
依賴: `## §V 驗證策略與邊界測試目錄`；`## §G Golden / Baseline`
不觸: `### C-0 🔴 接線落點：單一 boundary builder，拿不到 universe 就不得宣稱 OOS（D6）`；`### C-1 canonical 權威＝時間切分（D1）`

> 🔴 **C-4 覆寫範圍之限定（R6 `GROK-R6-P2-02`）**：本延伸**只覆寫 C-4 的函式簽名段**（單一 plan／單一 index → per-symbol Mapping）。**BASE C-4 其餘段落全部原文仍有效**——包含 `event_keys` 之 keyed 輸入契約、禁 positional zip、兩段式判定（答案窗 purge 先、集合成員判定後）、`build_event_keys` 具名為 producer 等。**未在本延伸重述 ≠ 已廢止**；實作與後續 refactor 不得以「延伸檔沒寫」為由刪除該節任一既有義務。

## 內容

### D-001-C1 per-symbol 投影之身分不變式（覆寫 C-2 之 fail-closed 落點、覆寫 C-4 簽名段）

C-2 的設計意圖不變：**邊界必須 per-symbol，禁全域 scalar 冒充**。本延伸把「多 symbol 批一律 fail-closed」改為「多 symbol 批以 per-symbol 結構投影」：

1. **投影簽名（覆寫 C-4 簽名段）**：

```python
def derive_event_split_from_plans(
    plans: Mapping[str, tuple[SplitPlan, SplitPlan]],      # symbol → (train_plan, test_plan)
    event_keys: pd.DataFrame,
    feature_index_by_symbol: Mapping[str, pd.Index],       # symbol → 該 symbol 之 post-trim universe（短索引；見下方數字空間限定）
    *,
    manifest: EventManifest,
    bucket_ms: Optional[int] = None,
    tier_min_test_events: int = 1,
) -> EventSplitPlan
```

   單標的舊呼叫式（`train_plan: SplitPlan`、`test_plan: SplitPlan`、`feature_index: pd.Index`）保留為**薄 wrapper**，內部包成單鍵 Mapping 後轉呼；wrapper **不得**含第二份判定邏輯（不得有 purge／成員判定／指紋比對之獨立分支）。呼叫端既未給 Mapping、也未走 wrapper ⇒ 維持 `multi_symbol_projection_unsupported`（字面續住 `split_unify.json`，不新增值）。

   🔴 **`feature_index_by_symbol` 之數字空間限定（R7 `CODEX-R7-P1-01`；R7 兩家對本句讀法相反 ⇒ 證明本句原有歧義，此處釘死）**：`feature_index_by_symbol[symbol]` 一律是**該 symbol 自己的 post-trim 索引**，長度＝該 symbol 之列數；它**不是**全框 universe，因此**不可**被 `SplitPlan.row_index`（全框列號）直接索引——兩者屬不同數字空間。R7 中一家讀為「須是能被全框 `row_index` 合法索引之同一 universe」，該讀法與本延伸 D-001-C2 第 4 點「`position` ＝ symbol-local ordinal」互斥，**不採**。🔴 **本簽名不收任何全框輸入**（R8 `CODEX-R8-P1-01`）：symbol-local 座標改由 plan 自帶之 `row_index_local` 提供（見 C2 第 4 點），**不**另傳全框 symbol 向量——傳全框向量等於在剛釘死本段之後又送回一份全框輸入，歧義會復發。**禁**以傳入全框索引冒充 per-symbol 索引（那會使 `position` 實際變成全框序號，並使指紋在單標的與多標的兩條路徑下不一致）。

2. 🔴 **hash 不變式**：
   - 同一 symbol 之 `train_plan.base_universe_hash == test_plan.base_universe_hash`（既有 `validate_split_pair_integrity` 已驗，不放寬）。
   - **跨 symbol 允許共用同一字面 hash**——`ICSplitAdapter._base_universe_hash(frame, …)` 對整框算一份 joint hash 並打進每個 symbol 的 plan，是**合法且現行已發生**的 hash scope（`momentum/Analysis/ic_split_adapter.py:189-199`；`momentum/Analysis/ic_filter_orchestrator.py:907`）。
   - 🔴 **禁**把「跨 symbol hash 必互異」寫成閘——那會拒收現行 IC 多標的計畫。
   - 🔴 **身分保證之分工（R6 `GROK-R6-P2-01` 修正 R5 之殘留敘述）**：D-001-C2 之指紋**已含 `symbol` 欄**，故可區分列所屬標的；但本節第 3 點之三角相等仍是**獨立必查**，不得只靠指紋——指紋證的是「這些列屬於這個 universe 且未被動過」，三角相等證的是「這批事件確實屬於這個 plan」。兩者目的不同，缺一不可。
3. **symbol 三角相等**：`plans` 的 Mapping key、該 plan 的 `plan.symbol`、以及事件集合之 symbol，三者必須相等；任一不等 ⇒ fail-closed，訊息**須指名是哪一組不一致**。🔴 **不得**復用 `multi_symbol_projection_unsupported` 字面（那是「未提供 Mapping」專用）。
4. **跨 symbol 禁共用 row_index 數字空間**：每個 symbol 各自以自己的 `feature_index` 解釋 `row_index`；合併僅發生在 `assignments`／`purged`／`clusters` 的**縱向串接**，不得跨 symbol 比較 row 位置。

### D-001-C2 逐列時刻同源對證（落實 TODO §E 之 SU-RESID-3）

現行同源對證只比每段**首尾**兩列，殘留＝「首尾相同、中間間距不同」仍會被放行。本延伸改為 producer-attested 的**完整有序**指紋：

1. 🔴 **指紋 payload 之精確形狀（R6 `GROK-R6-P1-01`：形狀未釘死會使 plan 指紋、§G G-5 與獨立 oracle 各凍一份）**：`rows` 為 **`list[list]`**，每列元素**順序固定**為
   `[int(position), int(feature_ts_ms), str(symbol), str(base_universe_hash)]`，
   與 `scripts/freeze_splitunify_golden.py` 現行 G-5① 之寫法**逐字同形**。序列化＝依 `position` 遞增排序後 `json.dumps(rows, sort_keys=True, separators=(",",":"))`，取 `sha256`。
   🔴 四個欄位之**文件稱呼**即 §G G-5① 之四元組 `(position, feature_ts_ms, symbol, base_universe_hash)`；該稱呼**僅供閱讀、不進 JSON**（清單形沒有鍵）。**禁**改用 `list[dict]`——實跑證實兩形之 `sha256` 不同。舊稱 `row_pos`／`ts_ms` 一律不得再用（含變數名與註解）。
   🔴 連帶：`scripts/freeze_splitunify_golden.py` 之註解仍寫舊欄名 `ts_ms`，須同步改為 `feature_ts_ms`（僅註解，演算法不動）。
2. 🔴 **型別強制**：`position` 與 `feature_ts_ms` 必須是 Python `int(...)`——`numpy.int64` 會使 `json.dumps` 丟 `TypeError`（R5 實跑），兩端若一端轉一端不轉即永遠不一致。
3. 🔴 **正規化函式點名（不得換別支）**：時刻一律走投影側之 `_index_as_ms` ／ `assert_epoch_ms_array`（epoch 毫秒、逐元素、嚴格遞增）；**明文排除** `contracts._coerce_timestamp_array`——它對純數字預設 `unit="s"`。
4. 🔴 **`position` 之語意與無損轉換層（R6 `CODEX-R6-P1-01`）**：本延伸之 `position` 一律為**該 symbol 之 post-trim `feature_index` 內的序號**（symbol-local ordinal），取數亦必從該 index。
   **但現行三個 producer 寫入 `SplitPlan.row_index` 的座標本來就不一致**（R8 抽驗）：`momentum/core/contracts.py::split_per_symbol`（`:659-661`）與 `momentum/Analysis/ic_split_adapter.py::_build_plan_pair`（`:230-231`）以 `positions[local]` 寫入**全框** row position；而 `momentum/Analysis/ic_filter_orchestrator.py` 之 holdout 路徑（`:631-642`）其 frame 本身即單標的（`symbols` 全為同一值，`:643`），寫入的 `row_index` **本來就已經是 symbol-local**。🔴 **本延伸不改 `row_index` 既有語意**（它同時被 IC 主線之全框驗證與既有 golden 依賴，改動範圍遠超本批），改為**由 producer 直接 attest 一份 symbol-local 座標**：
   - 🔴 **`SplitPlan` 新增欄 `row_index_local`（R8 `CODEX-R8-P1-01`）**：型別同 `row_index`，內容為該 plan 之列在**該 symbol 自己的 post-trim universe** 內之序號，遞增且與 `row_index` **逐位對應**。三個 producer 皆**直接取用其已有之 local ordinal**（`split_per_symbol` 之 `train_local`／`test_local`、`_build_plan_pair` 之 `train_local`／`test_local`、orchestrator 路徑因單標的而等同 `row_index`），**不得**在 producer 端重新反推。
   - 🔴 **為何不採「把全框 symbol 向量傳進投影」**：R8 指出既有 helper `_local_ordinals_for_symbol(row_index, symbol_arr, symbol)`（`contracts.py:504-519`）需要全框 `symbol_arr`，而新簽名與 `SplitPlan`（`:377-390`）皆**無**此向量 ⇒ R7 版所寫之「入口整批轉換」在契約上**不可執行**。若改為把 `symbol_arr` 傳進 `derive`，則等於在 C1 第 1 點剛釘死「投影只收 per-symbol 短索引」之後又送回一份全框輸入，R7 的歧義會復發。改由 producer attest 可同時消除「不可執行」與「歧義復發」。
   - 🔴 **producer 端之 attest 為必做**：建 plan 之處 `symbol_arr` **皆可得**（`contracts.py:690`、`ic_split_adapter.py:258`、`ic_filter_orchestrator.py:643-648` 皆已把 `symbols` 傳給 `validate_split_pair_integrity`），故 producer 必須以**同一支具名 helper** `_local_ordinals_for_symbol` 重算並與寫入之 `row_index_local` **逐值相等**；不等 ⇒ fail-closed。這就是「唯一、可驗證」之落點：**轉換只發生在 producer 一處，投影端不再轉換**。
   - 🔴 **投影端只消費 `row_index_local`**：`derive_event_split_from_plans` 內部**一律不得**索引 `row_index`。
   - 🔴 **缺欄即 fail-closed**：`derive` 入口收到之 plan 缺 `row_index_local` ⇒ 明確報錯並指名欄位，**不得**以 `row_index` 回退（回退正是交錯標的越界之來源）。非 `derive` 之呼叫點給相容 default。
   - 🔴 **兩欄之深層不可變性（R9 `CODEX-R9-P1-01`；主委實跑另加抓一面）**：`@dataclass(frozen=True)` 只擋「整欄改綁」，**擋不住 numpy 陣列原地改寫**——實跑 `p.row_index[0] = 99` 成功、讀回 `[99 2]`、`flags.writeable` 為 `True`；且建構時**無 defensive copy**，呼叫端持有之來源陣列其後之改動會滲入已建好的 plan（實跑：改來源後 plan 讀回 `[77 6]`）。⇒ `SplitPlan.__post_init__` 必須對 `row_index` 與 `row_index_local` **各自複製一份**並 `setflags(write=False)`。不這麼做，attest 只在建構當下成立：其後任一方被改，投影端讀 local 欄、而既有全框消費端（`momentum/Analysis/ic_filter_orchestrator.py:1318`、`:1335`、`:1359-1360`）讀 `row_index`，兩側**靜默分歧**。
   - 🔴 **attest 之前提條件（R9 第二家必答二；主委抽驗為生產可達，非理論形狀）**：producer 端「寫入 `train_local`」與「以 helper 重算並逐值相等」兩項，僅在**該標的之 frame 序等同時間序**時相容。`momentum/core/contracts.py:562-568` 之「標的內時刻嚴格遞增」保證**只在 `purge_semantic == "rows"` 分支內**；而 `momentum/Analysis/ic_filter_orchestrator.py:930` 之路徑以 `purge_semantic="timedelta"` 建 plan ⇒ 該形狀下 helper（frame 序）與 splitter 之 `train_local`（時間序）可分歧。**處置**：一律以「寫入 `train_local`」為準（它對齊投影端所用之時間序 `feature_index`）；attest 遇 frame 序非時間序**不得靜默跳過**，須 fail-closed 並指名 `purge_semantic` 與該標的，交由上游修正排序。🔴 **不得**為湊過 attest 而改寫 `train_local`。
   - 🔴 **受此規則覆蓋之消費點為封閉清單**（`momentum/Analysis/event_samples/split_projection.py`；行號為 R7 抽驗時之現況，實作時以函式內實際位置為準）：①長度閘 `assert_positional_rows(..., n=index_ms.size)`（`:453-458`）②首尾同源對證之 `index_ms[rows[0]]` 與 `index_ms[rows[-1]]`（`:473-484`）③**成員判定**之 train／test 時刻集合 `index_ms[train_rows]`／`index_ms[test_rows]`（`:486-487`）④測試段起點 `test_start_ms`（`:488`）⑤本節之指紋計算與比對。🔴 R6 版文字只涵蓋⑤，①～④漏網——**交錯標的正是在①越界、在②③④取到錯時刻**，不得再遺漏；新增任何消費 `row_index` 之處，一律先轉換再使用。🔴 **連帶（文件面亦屬消費點）**：`derive_event_split_from_plans` 之 docstring 現寫「集合成員判定——`feature_cutoff_ms ∈ feature_index[plan.row_index]` 決定 train／test」（`:351-353`），該句述的是舊座標語意，b8 須同步改寫為「以入口轉換後之 symbol-local ordinal 索引該 symbol 之 `feature_index`」，不得留下與本節互斥之契約敘述。
   - 規則：`row_index_local` 以該 symbol 之 post-trim universe 為序；producer attest 時映不到（該全框位置不屬於此 symbol）⇒ **fail-closed**，不得丟棄或近似。
   - 往返測試為必做：在 producer 端驗 `symbol_positions[row_index_local] == row_index` 逐值成立。
   - 🔴 交錯多標的 fixture 為必測：兩 symbol 之列在全框交錯時，各自之 `row_index_local` 仍須為連續遞增。
5. **邊界定義**：重複 `position` ⇒ fail-closed；`NaT` ⇒ fail-closed；空 `row_index`（train 可為空）⇒ 指紋定義為 `sha256("[]")`，**不得**以缺欄代替。
6. **比對點**：投影端對傳入之 `feature_index_by_symbol[symbol]` 以同一規則重算，與 plan 攜帶之指紋逐值比對；不符 ⇒ fail-closed，訊息須指名「plan 指紋 vs 重算指紋」兩值之前 12 字元。
7. **誠實邊界（明示接受）**：本改動會使既有 IC golden digest 位移。依原檔 §G 之規矩，golden 變動須經 review；b8 收案前須把受影響的 golden 以「改前／改後逐值對照」重凍，**不得**只更新 hash。另加**獨立 oracle**：由同一 fixture 的 `row_index` 與 universe 依本節規則重算 `sha256`，與 **producer 實際寫入 plan 的指紋欄**逐值相等（🔴 R6 `CODEX-R6-P1-02`：oracle 不得只算 fixture 自己的值而不對證 producer 寫入值）。
8. **首尾對證不刪**：完整指紋為**新增**層，既有首尾對證保留（承 C-1 附帶約束①「不得刪除任一既有 guard」）。

### Task 8.1 — per-symbol 投影（覆寫 Task 3.2、覆寫 C-4 簽名段）

- 目標：多 symbol 批以 per-symbol 結構投影，取代「一律 raise」。
- 檔案：`momentum/Analysis/event_samples/split_projection.py`、`momentum/Analysis/event_samples/pipeline.py`（改呼叫新簽名或走 wrapper）、`tests/momentum/Analysis/test_splitunify_derive.py`、`tests/momentum/event_samples/test_splitunify_wiring.py`。
- 實作要點：①簽名依 D-001-C1 第 1 點；②逐 symbol 走現行單標的路徑（含既有 fail-closed 與同源對證）後縱向合併；③`summary.n_symbols` 由實際 symbol 數導出；④`degraded` 之 `single_symbol` **僅在 `n_symbols == 1` 時亮**——解除條件寫死為「`n_symbols > 1`」，🔴 **不得**為讓 `formal_pooled_inference_allowed` 變 `True` 而以其他方式清空 `degraded`（旗標唯一產生點＝`momentum/Analysis/event_samples/event_split.py` 之 `_degraded_flags`）。
- 不可做：不得以第一個 symbol 之 plan 冒充整批；不得刪除 `multi_symbol_projection_unsupported` 字面；wrapper 不得含第二份判定邏輯。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k per_symbol` rc=0 且 `venv/bin/python -m pytest -q tests/momentum/event_samples/test_splitunify_wiring.py` rc=0，固定文法斷言逐條如下：
  `ASSERT derive_event_split_from_plans WHEN plans={A:(trA,teA), B:(trB,teB)} feature_index_by_symbol={A:idxA, B:idxB} THEN rc=0 且 set(assignments.symbol)=={A,B}`
  `ASSERT derive_event_split_from_plans WHEN 未提供 Mapping 結構 THEN rc!=0 且訊息含 multi_symbol_projection_unsupported`
  `ASSERT derive_event_split_from_plans WHEN 已提供 Mapping 但事件 symbol=B 而 plans 僅含 A THEN rc!=0 且訊息指名 symbol 不一致（且不得含 multi_symbol_projection_unsupported）`
  `ASSERT derive_event_split_from_plans WHEN plans={A,B} 且 A.train.base_universe_hash==B.train.base_universe_hash THEN rc=0`
  `ASSERT derive_event_split_from_plans WHEN 以 A 之 feature_index 解釋 B 之 row_index THEN rc!=0`
  `ASSERT derive_event_split_from_plans WHEN A 與 B 之列於全框交錯且 B 之全框 row_index 最大值 >= len(idxB) THEN rc=0 且不得 IndexError（投影只讀 `row_index_local`，從不索引全框列號）`
  `ASSERT derive_event_split_from_plans WHEN 交錯 fixture 之 B 事件 cutoff 恰為 B 自己第 k 列之時刻 THEN 該事件之 train/test 歸屬 == 單獨只跑 B 之結果`
  `ASSERT summary WHEN n_symbols==2 THEN "single_symbol" not in summary["degraded"]`
  `ASSERT summary WHEN n_symbols==1 THEN "single_symbol" in summary["degraded"]`
  `ASSERT test_splitunify_wiring WHEN 走 wrapper 之單標的路徑 THEN spy_split==[] 且 rc=0`

### Task 8.2 — 逐列時刻同源對證（落實 SU-RESID-3）

- 目標：關掉「首尾相同、中間間距不同」之錯分面。
- 檔案（🔴 producer 寫入點與既有綠徑面皆須列入，R5／R6 三條 P1）：
  - `momentum/core/contracts.py`（`SplitPlan` 新增 `row_time_fingerprint` 與 `row_index_local` 兩欄；後者由 producer attest；`__post_init__` 對兩個 row 陣列做 defensive copy 並 `setflags(write=False)`，見 C2 第 4 點）
  - `momentum/core/contracts.py::split_per_symbol`（建 plan 時寫入指紋）
  - `momentum/Analysis/ic_split_adapter.py::_build_plan_pair`（同上）
  - `momentum/Analysis/ic_filter_orchestrator.py`（holdout 路徑建 plan 處，同上）
  - `momentum/Analysis/event_samples/split_projection.py`（比對端＋無損轉換 helper）
  - `scripts/freeze_splitunify_golden.py`（G-5① 與指紋同形；註解舊欄名改為 `feature_ts_ms`）
  - `tests/momentum/Analysis/test_splitunify_derive.py`、`tests/momentum/Analysis/test_splitunify_golden.py`、`tests/momentum/event_samples/test_splitunify_wiring.py`、`tests/golden/splitunify/splitunify_golden.json`
- 🔴 **相容性**：新欄對**非** `derive_event_split_from_plans` 之呼叫點給相容 default；但 **derive 入口缺欄仍 fail-closed**，不得以 default 放行。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k fingerprint` rc=0、`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_golden.py` rc=0、`venv/bin/python scripts/freeze_splitunify_golden.py` 比對 rc=0（**不得**以 `--write` 覆蓋失敗結果）；固定文法斷言逐條如下：
  `ASSERT derive_event_split_from_plans WHEN feature_index 與 plan 首尾相同但中間一列 ts 不同 THEN rc!=0 且訊息含 sha256 前 12 字元`
  `ASSERT derive_event_split_from_plans WHEN feature_index 與 plan 逐列相同 THEN rc=0`
  `ASSERT row_time_fingerprint WHEN 同一 index 重算兩次 THEN sha256 值 == 前次值`
  `ASSERT row_time_fingerprint WHEN 空 row_index THEN sha256 值 == sha256("[]")`
  `ASSERT derive_event_split_from_plans WHEN plan 缺 row_time_fingerprint 欄 THEN rc!=0 且訊息指名缺欄名`
  `ASSERT 獨立 oracle WHEN 由 fixture 重算 THEN 值 == producer 寫入 plan 之 row_time_fingerprint`
  `ASSERT producer attest WHEN 建 plan THEN _local_ordinals_for_symbol(row_index, symbol_arr, symbol) 逐值 == row_index_local`
  `ASSERT producer attest WHEN row_index 含不屬於該 symbol 之全框位置 THEN rc!=0`
  `ASSERT producer attest WHEN 兩 symbol 於全框交錯 THEN 各自 row_index_local 連續遞增`
  `ASSERT derive_event_split_from_plans WHEN plan 缺 row_index_local 欄 THEN rc!=0 且訊息指名缺欄名（不得以 row_index 回退）`
  `ASSERT derive_event_split_from_plans WHEN 單標的 frame（orchestrator 路徑）THEN row_index_local 逐值 == row_index`
  `ASSERT SplitPlan WHEN 建構後對 row_index 或 row_index_local 原地寫入 THEN 丟出例外（兩欄皆唯讀）`
  `ASSERT SplitPlan WHEN 建構後改動呼叫端持有之來源陣列 THEN plan 內兩欄皆不變（已 defensive copy）`
  `ASSERT producer attest WHEN purge_semantic=timedelta 且該標的 frame 序非時間序 THEN rc!=0 且訊息指名 purge_semantic 與該標的`

### Task 8.3 — per-symbol 測試段門檻修正

- 目標：`insufficient_events_in_test` 改為**逐 symbol** 判定。
- 碼證：`momentum/Analysis/event_samples/split_projection.py` 現行該行條件**與迴圈變數無關**，用的是整批 `n_test`；舊實作 `momentum/Analysis/event_samples/event_split.py` 才是逐 symbol。
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
| `M-SU-D1-08` | 指紋列改用 `list[dict]`（形狀漂移） | `test_splitunify_golden.py` 與 `-k fingerprint` |
| `M-SU-D1-09` | 無損轉換改為「映不到就丟棄」 | `-k fingerprint`（交錯 fixture） |
| `M-SU-D1-10` | 成員判定改回以全框 `row_index` 直接索引該 symbol 之 `feature_index` | `test_splitunify_derive.py -k per_symbol`（交錯 fixture） |
| `M-SU-D1-11` | producer 之 attest 改為「不等就以寫入值為準」（不 fail-closed） | `test_splitunify_derive.py -k per_symbol` 與 producer 契約測試 |
| `M-SU-D1-12` | `derive` 缺 `row_index_local` 時回退用 `row_index` | `test_splitunify_derive.py -k per_symbol`（交錯 fixture） |
| `M-SU-D1-13` | 建構時不複製 row 陣列（保留呼叫端別名） | producer 契約測試（改來源陣列後 plan 應不變） |
| `M-SU-D1-14` | 不設 `setflags(write=False)`（允許原地改寫） | producer 契約測試（原地寫入應丟例外） |
| `M-SU-D1-15` | frame 序非時間序時 attest 靜默跳過 | producer 契約測試（應 fail-closed 並指名 `purge_semantic`） |

### 殘留（承原檔 §N；本延伸覆寫其中一列之狀態，另一列住 TODO §E）

- `R-1`（§N）— **本延伸落實**，理由類別由 `needs-research` 解除。
- `SU-RESID-3`（TODO §E）— **本延伸落實**，理由類別由 `needs-research` 解除；其「動 IC golden digest」之代價改以 §G 重凍程序承擔（見 D-001-C2 第 7 點）。
- `SU-RESID-2`（多 TF 複合鍵）— **不在本延伸**；下游單鍵面（`feature_materialization`／`baseline`／`pattern_bridge`／`tables`／`ic_feed`／`dedupe` 之 cluster 折疊）須一併處理。未完成前，多 TF 同批維持 fail-closed。
- `R-5`／`D1` — **不在本延伸**；`D1` 須走 R 重開，`R-5` 待其完成後另行處理。
- `R-3`（UAT 最後，user-ruling）、`R-4`（屬 GAP-3，blocked-by）— 不動。
- 🔴 **新登記 `SU-RESID-4`（needs-research）**：`SplitPlan.row_index` 之全框語意與 per-symbol 投影所需之 local ordinal 並存，本延伸以 producer attest 之並存欄 `row_index_local` 橋接（C2 第 4 點），而非改動 `row_index` 本身。**研究問題**＝「是否應把 `row_index` 本身改為 symbol-local，並同步遷移 IC 主線之全框驗證與既有 golden」；**完成判準**＝列出所有依賴全框語意之消費端並給出可證偽之遷移測試。觸發：下一次動 IC 切分契約時。

## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。
