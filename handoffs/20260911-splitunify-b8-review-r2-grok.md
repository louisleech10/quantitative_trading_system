# SPLITUNIFY b8 審碼 R2（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-B8-REVIEW-R2  
family: grok  
findings-round: R2  
標的：R1 三條修補（commit `5ac5bd8d`）之閉合／回歸核對  
SCOPE: review-only；禁改碼  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄  
探針：`/tmp/grok-b8-review-r2/probe_r2.py`、`probe_r2b.py`（stdout 同目錄；交件後清掉）  
HEAD（本輪起點）：`76312149`（含 `5ac5bd8d`）

### §0 前提宣告（本輪覆核）

fact-verified: `CODEX-R1-P1-01` 之 float64 反例在 `split_per_symbol` 與 `ICSplitAdapter._build_plan_pair` 皆 `RAISE` 且訊息含 `dtype`（探針 A1／adapter_float）。

fact-verified: dtype 閘三個 cast 點皆已呼叫 `_assert_integer_ordinals`——`contracts.py::split_per_symbol` 一處、`ic_split_adapter` 之 CPCV 迴圈與 `_build_plan_pair` 兩處（源碼點名；`ast` 確認 contracts import 清單含該函式）。

fact-verified: `CODEX-R1-P1-02` 之未選 `NaT` 在 `split_per_symbol` 路徑 `RAISE` 且訊息含 `NaT`（探針 B1；`test_producer_rejects_nat_anywhere_on_the_time_axis` 在 attest 22 passed 內）。

fact-verified: `CODEX-R1-P2-03` 之 `_derive_single_symbol` docstring 已改為 `test_plan.row_index_local[0]`；同檔未再找到以 `test_plan.row_index[0]`／`train_plan.row_index[0]` 描述投影起點的殘句。

fact-verified: 合法 int64 序號／無 NaT 時間軸之 `split_per_symbol` 與 `ICSplitAdapter._with_row_positions` 皆 `NO_RAISE`；`freeze_splitunify_golden.py` → `GOLDEN OK`；定向 pytest 25 passed。

fact-verified: **修補引入新缺陷**——`ic_split_adapter._with_row_positions` 在 NaT 分支 `raise AlignmentViolationError(...)`，但該名**未**自 `momentum.core.contracts`（或他處）匯入；含未選 NaT 的 frame 經 adapter 入口得到 `NameError: name 'AlignmentViolationError' is not defined`（見 GROK-R2-P1-01）。

assumed: 「coerce 之後驗整條時間軸」佈局足以涵蓋 coerce 會生成的 NaT  
→ 否證觀測：`_coerce_timestamp_array` 對 `None`／`nan`／`""` 會產出 `NaT`，且 `split_per_symbol`／adapter 檢查皆在 coerce **之後**——佈局成立；adapter 實作卻因缺 import 無法依契約丟出對應例外（見下）。  
assumed: dtype 閘涵蓋 float／bool／object 即足夠  
→ 否證觀測：`pd.array(..., dtype="Int64")` 無 NA 時 `np.asarray`→`int64` 合法放行；含 `pd.NA`→`float64` 被閘擋；`np.matrix` 二維過 dtype 後在索引階段 raise（非靜默錯分）；`uint64` 為 numpy integer 合法放行。**未**找到第四種可靜默產出錯誤 plan 的型別。  
assumed: 修補未改變既有數值輸出  
→ 本輪：`GOLDEN OK`＋合法路徑可產 plan；**未**另跑 IC 端到端真實 run（與 brief 自承邊界一致）。

---

## 三條修補對應核對（非本家 CLOSED 帳；供主委對照）

| R1 ID | 修補是否對上原 finding | 本輪實跑 |
|---|---|---|
| CODEX-R1-P1-01 | **是**——cast 前 `_assert_integer_ordinals`；三 cast 點皆接上 | float／bool／object 皆 dtype raise；合法 int64 放行 |
| CODEX-R1-P1-02 | **部分**——`split_per_symbol` 完整；adapter 有檢查碼但缺 import ⇒ 契約例外未成立 | split_per_symbol：NaT raise；adapter：`NameError`（見 P1-01） |
| CODEX-R1-P2-03 | **是**——docstring 已改 local 座標 | 無其他全框起點殘句 |

orchestrator `:285-286` NaT 閘仍在（探針 B5 `AlignmentViolationError: features_df index contains NaT`）。holdout 路徑之 `np.asarray(..., dtype=int)` 吃的是 `holdout_boundary` 回傳值，不屬 brief 所稱「splitter 回傳序號」三 cast 點；本輪不另開第四 cast 漏接 finding。

---

## 主動攻擊面（停輪條件②／③）

已攻擊且**未**另開洞者：①float／bool／object／nullable Int64／matrix／uint64 能否靜默錯分；②coerce 生成 NaT 是否落在檢查點之前；③合法輸入是否被新閘誤擋；④golden／定向 derive 是否位移；⑤投影 docstring 全框殘句。  
**成功開洞者**：adapter NaT 分支缺 `AlignmentViolationError` import（下條）。

---

## GROK-R2-P1-01

**斷言**: R1 修補在 `ICSplitAdapter._with_row_positions` 的整條時間軸 NaT 閘會因未匯入 `AlignmentViolationError` 而在觸發時拋 `NameError`，使得 CODEX-R1-P1-02 於 adapter 路徑的契約例外（`AlignmentViolationError`＋NaT 訊息）未成立，且 `NameError` 不在 `ValueError` 階層、會穿透既有 `except ValueError`／`AlignmentViolationError` 處理。

**碼證**: `ic_split_adapter.py:13-22` import 無 `AlignmentViolationError`，同檔 `:193-198` 卻 `raise AlignmentViolationError(...)`；實跑含未選 NaT 之 frame 經 `_with_row_positions`／`split_cpcv` → `NameError: name 'AlignmentViolationError' is not defined`；同輸入經 `split_per_symbol` → `ValueError` 且訊息含 `NaT`；`test_producer_rejects_nat_anywhere_on_the_time_axis` 只覆蓋 `split_per_symbol` 故缺 import 全綠漏網。RECHECK：`PYTHONPATH=. python -c "…ICSplitAdapter()._with_row_positions(fr_with_nat,…)"` 預期現況 NameError，修補後應為 AlignmentViolationError 且訊息含 NaT。

**來源摘要**: momentum/Analysis/ic_split_adapter.py#8517730f1b29;handoffs/20260911-splitunify-b8-review-r1-codex.md#c55afb999b4f;handoffs/20260911-SPLITUNIFY-B8-REVIEW-R2-BRIEF.md#e8ac368e3762;tests/momentum/core/test_splitunify_producer_attest.py#e9105a6d7284

[P1/high] 信心度=High。  
會怎麼失敗：含缺時刻之 universe 走進 CPCV／WF adapter 時以未分類 `NameError` 崩潰，監控／caller 無法依 `AlignmentViolationError` 分類；R1 宣稱之 adapter NaT fail-closed 訊息永不出現。資料雖未靜默進 plan，但修補本身未交付所宣稱的契約。  
**修法**：在 `ic_split_adapter.py` 自 `momentum.core.contracts` 匯入 `AlignmentViolationError`（與 orchestrator／contracts 既有型別對齊）。  
**可行性證據**：`AlignmentViolationError` 已定義於 `contracts.py:933` 且為 `ValueError` 子類；同模組已自該處匯入多個符號，加一名字即可；另補一條 adapter 路徑測試（`pytest.raises(AlignmentViolationError, match="NaT")` 呼叫 `_with_row_positions` 或 `split_wf`／`split_cpcv`）以防再漏。本輪禁改碼，僅開 finding。

---

## 被當成事實的未驗證假設（§0）

1. 「三個 cast 點＝全部 splitter 序號入口」——對 brief 所劃之 producer cast 集合 **HOLDS**；orchestrator holdout 另路且吃 boundary 整數回傳，本輪不升級。  
2. 「coerce 後立即檢查即可」——佈局 **HOLDS**；adapter 實作因缺 import **不 HOLDS**（P1-01）。  
3. 「IC e2e 與單元等價」——仍 assumed（本輪未跑 e2e）。

ASSUMPTIONS_VERIFIED: P1-01／P1-02／P2-03 對應關係與 dtype／NaT／docstring／合法路徑實跑如上；adapter NameError 獨立複驗兩次。  
TESTS_RUN: `pytest tests/momentum/core/test_splitunify_producer_attest.py -q` → 22 passed；`pytest …/test_splitunify_derive.py -k 'per_symbol or fingerprint or insufficient or producer_rejects' -q` → 25 passed, 75 deselected；`scripts/freeze_splitunify_golden.py` → GOLDEN OK；探針 A1–A7／B1／B5／adapter float／adapter NaT。  
FAILURES_SEEN: adapter NaT 預期應為 AlignmentViolationError，實得 NameError（升級為本輪 P1）；其餘預期負向皆按設計擋下。  
SCOPE_CHANGES: none（review-only；修法提案不落碼）。  
NUMERIC_OR_SCHEMA_IMPACT: none（本輪無改碼）；golden 未位移。  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b8-review-r2-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R2-P1-01
CLOSED:
STATUS: DONE
