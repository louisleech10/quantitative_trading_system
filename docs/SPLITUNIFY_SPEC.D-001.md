# SPLITUNIFY_SPEC.md 延伸 D-001

BASE: docs/SPLITUNIFY_SPEC.md @ b095cc754cb9de26bbf2dd35564db329aca3c98f
PREDECESSOR: none
改什麼: 落實 §N 既有殘留 `R-1`（per-symbol 投影）與 `SU-RESID-3`（逐列時刻同源對證），並修正 R-1 解封後才會顯形的 per-symbol 門檻失效。
為什麼: `handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md`（三家 consult，18 條收斂；群集 U1／U3／U7／U8）。

**類別判定＝D 延伸**（依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1）。
理由：原檔 `Task 3.2` 自身已寫「**存活至**：per-symbol 投影實作後**改寫**為支援分支（見 §N R-1）」與「**覆蓋風險**：本 Task 之 raise 分支預期被未來的 per-symbol 支援取代——屆時須連同測試一起改，不得只刪 raise」。本延伸即該預告之落地，**不推翻** C-2 的設計意圖（邊界必須 per-symbol、禁全域 scalar 冒充）——相反，它把「per-symbol」從 fail-closed 升級為真的做到。

🔴 **明確不在本延伸範圍**：`D1`（事件掃描端「恆走」event-study-only）之條件化。三家 consult 判其與原檔字面互斥、**須走 R 重開**（`CODEX-R1-P1-05`／`GROK-R1-P1-01`）；`R-5` 亦隨之留待 R 完成後另行處理。

## 觸及面宣告

新增: `D-001-C1`、`D-001-C2`、`Task 8.1`、`Task 8.2`、`Task 8.3`（原檔無對應 heading）
覆寫: `### C-2 🔴 邊界必須 per-symbol，禁全域 scalar 冒充（D2；codex 與 composer **各自標 P0**）`；`**Task 3.2 — 多 symbol fail-closed（C-2）**`；`## §N N/A 登記與殘留`
依賴: `### C-4 投影是純函式、單一實作；簽名須帶 \`feature_index\` 與 \`manifest\``；`## §V 驗證策略與邊界測試目錄`；`## §G Golden / Baseline`
不觸: `### C-0 🔴 接線落點：單一 boundary builder，拿不到 universe 就不得宣稱 OOS（D6）`；`### C-1 canonical 權威＝時間切分（D1）`

## 內容

### D-001-C1 per-symbol 投影之身分不變式（覆寫 C-2 之 fail-closed 落點）

C-2 的設計意圖不變：**邊界必須 per-symbol，禁全域 scalar 冒充**。本延伸把「多 symbol 批一律 fail-closed」改為「多 symbol 批以 per-symbol 結構投影」，並把身分判定寫成封閉不變式：

1. **投影輸入改為 per-symbol 結構**：`Mapping[symbol, (train_plan, test_plan)]` ＋ `Mapping[symbol, feature_index]`。呼叫端未提供該結構 ⇒ 維持 `multi_symbol_projection_unsupported`（字面續住 `split_unify.json`，不新增值）。
2. 🔴 **hash 不變式（三家共同否證主委初判後之定案）**：
   - 同一 symbol 之 `train_plan.base_universe_hash == test_plan.base_universe_hash`（既有 `validate_split_pair_integrity` 已驗，不放寬）。
   - **跨 symbol 允許共用同一字面 hash**——`ICSplitAdapter._base_universe_hash(frame, …)` 對整框算一份 joint hash 並打進每個 symbol 的 plan，是**合法且現行已發生**的 hash scope（`momentum/Analysis/ic_split_adapter.py:189-199`；`momentum/Analysis/ic_filter_orchestrator.py:907`）。
   - 🔴 **禁**把「跨 symbol hash 必互異」寫成閘——那會拒收現行 IC 多標的計畫（`CODEX-R1-P1-01`／`GROK-R1-P2-01`／`COMPOSER-R2-P1-01` 三家一致）。
   - 身分保證改由**逐 symbol 的同源對證**承擔（見 D-001-C2），不由 hash 字面承擔。
3. **事件 symbol 必匹配其 plan 的 symbol**：事件集合之 symbol 與該 symbol 之 plan `symbol` 欄不一致 ⇒ fail-closed（既有語意保留，改為逐 symbol 判定）。
4. **跨 symbol 禁共用 row_index 數字空間**：每個 symbol 各自以自己的 `feature_index` 解釋 `row_index`；合併僅發生在 `assignments`／`purged`／`clusters` 的**縱向串接**，不得跨 symbol 比較 row 位置。

### D-001-C2 逐列時刻同源對證（落實 SU-RESID-3）

現行同源對證只比每段**首尾**兩列，殘留＝「首尾相同、中間間距不同」仍會被放行。本延伸改為 producer-attested 的**完整有序**指紋：

1. **指紋定義**（封閉、可重算）：對 plan 之**全部** `row_index`，取其在 producer 當時 universe 上的時刻序列，正規化為 **epoch 毫秒整數**、依 `row_index` 遞增排序，payload 為 `[[row_pos, ts_ms], …]` 之 `json.dumps(sort_keys=True, separators=(",",":"))`，取 `sha256`。指紋另帶 `symbol` scope 與 producer provenance（產生者模組名與 `base_universe_hash`）。
2. **比對點**：投影端對傳入之 `feature_index` 以**同一規則**重算，與 plan 攜帶之指紋逐值比對；不符 ⇒ fail-closed，訊息須指名「plan 指紋 vs 重算指紋」兩值之前 12 字元。
3. **不猜單位**：時刻正規化沿用既有型別分派規則，純數字不得預設秒或毫秒；型別無法判定 ⇒ fail-closed。
4. **誠實邊界（明示接受）**：本改動會使既有 IC golden digest 位移。依原檔 §G 之規矩，golden 變動須經 review；本延伸要求 b8 收案前把受影響的 golden 以「改前／改後逐值對照」重凍，**不得**只更新 hash。
5. **首尾對證不刪**：完整指紋為**新增**層，既有首尾對證保留（承 C-1 附帶約束①「不得刪除任一既有 guard」）。

### Task 8.1 — per-symbol 投影（覆寫 Task 3.2）

- 目標：多 symbol 批以 per-symbol 結構投影，取代「一律 raise」。
- 檔案：`momentum/Analysis/event_samples/split_projection.py`、`tests/momentum/Analysis/test_splitunify_derive.py`。
- 實作要點：①投影簽名接受 per-symbol 結構；②逐 symbol 走現行單標的路徑（含既有四道 fail-closed 與同源對證）後縱向合併；③`summary.n_symbols` 由實際 symbol 數導出；④`degraded` 之 `single_symbol` **僅在 `n_symbols == 1` 時亮**——解除條件寫死為「`n_symbols > 1`」，🔴 **不得**為讓 `formal_pooled_inference_allowed` 變 `True` 而以其他方式清空 `degraded`（旗標唯一產生點＝`momentum/Analysis/event_samples/event_split.py` 之 `_degraded_flags`）。
- 不可做：不得以第一個 symbol 之 plan 冒充整批；不得刪除 `multi_symbol_projection_unsupported` 字面（改為「呼叫端未給 per-symbol 結構」時之 reason）。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k per_symbol` rc=0，固定文法斷言逐條如下：
  `ASSERT derive_event_split_from_plans WHEN plans={A:(trA,teA), B:(trB,teB)} indices={A:idxA, B:idxB} THEN rc=0 且 set(assignments.symbol)=={A,B}`
  `ASSERT derive_event_split_from_plans WHEN 事件 symbol=B 但只給 A 之 plan THEN rc!=0 且訊息含 multi_symbol_projection_unsupported`
  `ASSERT derive_event_split_from_plans WHEN plans={A,B} 且 A.train.base_universe_hash==B.train.base_universe_hash THEN rc=0`
  `ASSERT summary WHEN n_symbols==2 THEN "single_symbol" not in summary["degraded"]`
  `ASSERT summary WHEN n_symbols==1 THEN "single_symbol" in summary["degraded"]`

### Task 8.2 — 逐列時刻同源對證（落實 SU-RESID-3）

- 目標：關掉「首尾相同、中間間距不同」之錯分面。
- 檔案：`momentum/core/contracts.py`（plan 攜帶指紋）、`momentum/Analysis/event_samples/split_projection.py`（比對）、`tests/momentum/Analysis/test_splitunify_derive.py`、`tests/golden/splitunify/splitunify_golden.json`。
- **驗證**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k fingerprint` rc=0，且 `sha256` 逐值相等；固定文法斷言逐條如下：
  `ASSERT derive_event_split_from_plans WHEN feature_index 與 plan 首尾相同但中間一列 ts_ms 不同 THEN rc!=0 且訊息含 sha256 前 12 字元`
  `ASSERT derive_event_split_from_plans WHEN feature_index 與 plan 逐列 ts_ms 相同 THEN rc=0`
  `ASSERT row_time_fingerprint WHEN 同一 index 重算兩次 THEN sha256 值 == 前次值`
  `ASSERT derive_event_split_from_plans WHEN plan 缺 row_time_fingerprint 欄 THEN rc!=0 且訊息指名缺欄名`

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

### 殘留（承原檔 §N；本延伸覆寫其中兩列之狀態）

- `R-1` — **本延伸落實**，理由類別由 `needs-research` 解除。
- `SU-RESID-3` — **本延伸落實**，理由類別由 `needs-research` 解除；其「動 IC golden digest」之代價改以 §G 重凍程序承擔（見 D-001-C2 第 4 點）。
- `SU-RESID-2`（多 TF 複合鍵）— **不在本延伸**；依 consult 收斂排於下一批，且其下游單鍵面（`feature_materialization`／`baseline`／`pattern_bridge`／`tables`／`ic_feed`／`dedupe` 之 cluster 折疊）須一併處理。未完成前，多 TF 同批維持 fail-closed。
- `R-5`／`D1` — **不在本延伸**；`D1` 須走 R 重開（三家 consult 裁定），`R-5` 待其完成後另行處理。
- `R-3`（UAT 最後，user-ruling）、`R-4`（屬 GAP-3，blocked-by）— 不動。

## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。
