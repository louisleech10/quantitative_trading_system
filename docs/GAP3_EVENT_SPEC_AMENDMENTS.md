# GAP3_EVENT_SPEC — 修訂集（AMENDMENTS）

> 本檔是 `docs/GAP3_EVENT_SPEC.md` **檔頭逐字指定**的修訂路徑
> （「後續修訂走延伸檔 `docs/GAP3_EVENT_SPEC_AMENDMENTS.md`，不就地改本檔」）。
> 🔴 **注意**：這條鏈**不走** `D-00N` 慣例——`D-00N` 是**兄弟檔**
> `docs/GAP3_EVENT_UX_SPEC.md` 的修訂慣例。兩份是不同的凍結文件，
> 修訂路徑也不同；把它們搞混正是 SPLITUNIFY B1 review 抓到的錯
> （`CODEX-R1-P1-01`＋`GROK-R1-P2-01`：D-002 宣告了一個在其 BASE 內根本不存在的 heading）。

BASE: docs/GAP3_EVENT_SPEC.md @ e0f3cb52
PREDECESSOR: none

改什麼: `Task B1.3` 之**邊界來源**——per-symbol 時間切分不再自行決定 train／test 邊界，改由 canonical K 線 holdout 投影而得；interval-aware purge 之語意**保留**但改以 canonical `test_start_ms` 表述。

為什麼: 票 `SPLITUNIFY`；規格住 `docs/SPLITUNIFY_SPEC.md`（v5）；consult 收斂 `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`（D1–D8，三家 RECONCILE-STAMP APPROVED）；四輪 adversarial `handoffs/reconcile/20260911-splitunify-x-review-r{1,2,3,4}/synth.md`。

## 觸及面宣告
新增: none
覆寫: **Task B1.3 — per-symbol 時間切分＋interval-aware purge＋跨標的 time-cluster（K4/C6；U12 多標的必要）**（`docs/GAP3_EVENT_SPEC.md:168`）——只覆寫其**邊界來源**與 purge 條件式之表述，clusters／summary 語意不動。
依賴: `momentum/core/split_preview.py::holdout_boundary`（canonical 邊界唯一產生點）；`momentum/Analysis/event_samples/split_projection.py`（投影純函式，B2b）。

## §RISK 風險分級

RISK-HIT: a,b,d

命中 (a) 數值／資料品質——邊界直接決定 OOS 成員與 purge 集合；(b) 跨模組共用路徑——
`momentum/core/split_preview.py`＋`momentum/Analysis/event_samples/`＋`api/services/`；
(d) ML／回測正確性——A-2 若被刪即為 OOS leakage（已實際發生過一次，見 A-2）。

## §A 假設與待使用者確認

**待使用者確認：無。** 切法由使用者 2026-09-10 明示授權委員會定案
（「但要如何切分，你跟委員要討論共識」），consult 已收斂並取得三家 RECONCILE-STAMP。

FACT-RECEIPT: `sed -n '112,118p' momentum/Analysis/event_samples/event_split.py` →
現行 purge 條件式為 `elif int(rec["label_end_ms"]) > test_start - embargo:`（主委實跑 2026-09-11）。

FACT-RECEIPT: `venv/bin/python -m pytest -q tests/momentum/core/test_splitunify_boundary.py`
→ `11 passed`，其中 `-k same_source` 釘住 `test_row_index[0] == split_point + purge_gap + embargo`
（主委實跑 2026-09-11）⇒ A-2「canonical `test_start_ms` 已在緩衝之後」有碼證。

## §C 約束（引用，不重抄）

本修訂之完整約束住 `docs/SPLITUNIFY_SPEC.md`（v5）之 C-0／C-1／C-2／C-4；
本檔只記「`GAP3_EVENT_SPEC.md` 的哪一條被改了」，不重抄。

## §P Phase 與依賴

**Task A.1 — 邊界來源與 purge 表述之覆寫（本修訂之唯一 Task）**
- 目標：把 `Task B1.3` 的邊界來源改為 canonical holdout，並保留 interval-aware purge。
- 輸入 / 輸出：`docs/GAP3_EVENT_SPEC.md:168` 之條文 → 本檔 A-1／A-2／A-3。
- 實作要點：見下方 A-1／A-2／A-3（A-2 附可直接實作的條件式）。
- 修改檔案：本檔（文件）；程式落點在 `SPLITUNIFY` 之 B2b／B3。既有 caller：`pipeline.py:691`。
- 不可做：不得刪除 A-2 之 interval-aware purge；不得就地改 `docs/GAP3_EVENT_SPEC.md`。
- 邊界：①本檔只覆寫邊界來源與 purge 表述，clusters／summary 語意不動；
  ②多 symbol 走 A-3 之 fail-closed。
- 風險緩解：mutation `M-SU-13`（拿掉答案窗 purge ⇒ 必紅）。
- **驗證**：見 §V（兩條 pytest 命令，皆 rc=0）。
- **存活至**：`SPLITUNIFY` 全票完工後保留。
- **覆蓋風險**：per-symbol 支援（`R-1`）日後會改寫 A-3，不影響 A-1／A-2。

## 內容

### A-1 邊界來源改為 canonical K 線 holdout

原 `Task B1.3` 之「每 symbol 各自按時間切＋緩衝 ≥ 答案窗」**不再是邊界來源**。
`split_authority == "kline_holdout"`：邊界由 `holdout_boundary(feature_index, …)` 唯一產生，
`EventSplitPlan` 之 `assignments`／`purged` 由該邊界投影而得。

理由（`CODEX-R1-P1-02`，SPLITUNIFY consult D1）：**不是**「時間切分的隔離比較強」——
兩套隔離不是同一個集合，containment **未被證明**；採用的理由是
「所有 row／event projection **共用同一 canonical boundary**」。

### A-2 🔴 interval-aware purge **保留**，只改表述

原 `event_split.py:114` 之 `label_end_ms > test_start - embargo` ⇒ purge **不得刪除**
（C-1 附帶約束①：containment 未證明前不得刪除任一既有 guard）。
canonical 語意下改寫為——**先**驗答案窗、**再**做集合成員判定：

```python
train_cutoff = feature_cutoff_ms in as_ms(feature_index[train_plan.row_index])
if test_plan.row_index.size == 0:
    raise ValueError("missing_test_plan: …")
test_start_ms = as_ms(feature_index[test_plan.row_index[0]])
if train_cutoff and label_end_ms >= test_start_ms:   # `>=` 必須保留
    purge(event_id, reason="interval_crosses_split_boundary")
```

🔴 **不再減 embargo**：`purge_gap`／`embargo` 是 **row 單位且已包含在
`test_plan.row_index[0]` 這個起點裡**（`holdout_test_row_index` ＝
`arange(split_point + purge_gap + embargo, n)`）；舊式的 `test_start` 是緩衝**之前**的邊界
所以要減，canonical 的是緩衝**之後**的第一根，再減會重複扣。
（SPLITUNIFY R4 之 F1；式子逐字採 `CODEX-R4-P1-01`。）

🔴 **SPLITUNIFY v3 曾把這道 guard 整個刪掉**（投影只做集合成員判定、簽名裡沒有
`label_end_ms`），造成答案窗已跨進測試段的 train 事件留在 train ＝ 真 OOS leakage，
由 `CODEX-R3-P1-02` 抓出。本條之存在就是釘住它不再被刪。

### A-3 多 symbol fail-closed

per-symbol 投影未支援前，多 symbol 批一律 raise `multi_symbol_projection_unsupported`。
實測（receipt `20260910T150504Z-splitunify-multisymbol`）：兩 symbol 交錯之 80 列批次，
全域切法測試段 12 列、per-symbol 8 列，**4 列只在全域** ⇒ 兩者不等價，禁以前者冒充。

## §G Golden / Baseline

本修訂之 golden 不另立，**引用** `docs/SPLITUNIFY_SPEC.md`（v5）§G 之五組：
G-1 成員集合、G-2 全域路徑逐位元組不變（`sha256`）、G-3a 一次性遷移報告、
G-3b 獨立 oracle 集合相等、G-4 per-symbol counts（整數逐值相等）、
G-5 containment 四項（逐 row test fingerprint 之 `sha256`、逐 event `assignments`／`purged` IDs、
answer-window 完整性、leakage negative case）。

🔴 與本檔 A-2 直接相對應的是 **G-5 第 4 項**：把一筆 train 事件的 `label_end_ms`
推進 test 區 ⇒ 必進 `purged`；拿掉該斷言 ⇒ mutation `M-SU-13` rc=1。
數值比較規約：計數類**整數逐值相等**；浮點以 `atol=1e-12`／`rtol=1e-9`。

## §V 驗證策略與邊界

- `venv/bin/python -m pytest -q tests/momentum/core/test_splitunify_boundary.py` rc=0
  （`-k same_source` 釘住 `test_row_index[0] == split_point + purge_gap + embargo`，
  即 A-2「不再減 embargo」之依據）。
- B2b 之 `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k answer_window`
  rc=0：`label_end_ms` 跨進測試段之 train 事件必進 `purged`；拿掉第一段 ⇒ mutation `M-SU-13` 必紅。

## §R 回退

本檔為文件修訂，回退＝刪除本檔並清空 `GAP3_EVENT_SPEC.md` 之修訂指向；
程式面之回退屬 `SPLITUNIFY` 之 B3（接線批）。

## §N 本修訂未解者

- per-symbol 投影（`SPLITUNIFY` 殘留 `R-1`，needs-research）。
- 多 TF 之 `(event_id, timeframe)` 複合鍵（`SU-RESID-2`，needs-research）。

## 戳記

（本區之下由各家族 append 一行 `RECONCILE-STAMP: <family> APPROVED <date> sha256:<body-hash> task:<task-id>`；本區標題以上為本體，body-hash 由 `scripts/reconcile_body_hash.sh` 計算。）
