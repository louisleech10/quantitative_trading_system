# SPLITUNIFY 第 8 批（b8）閉合輪 R2 — COMPOSER

task-id: 20260911-SPLITUNIFY-B8-REVIEW-R2  
family: composer  
findings-round: R2  
審查對象: commit `5ac5bd8d` 之三條 codex R1 修補（dtype 閘／NaT 閘／投影 docstring）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief `fact-verified`: 修補前 float64／未選 NaT 為 `NO_RAISE`、修補後三條皆 raise | **fact-verified（本輪複驗一致）** | 探針 `/tmp/composer_b8_r2_probe.py`：float64→`ValueError … dtype 為 float64`；未選 NaT→`ValueError … 含 1 個 NaT` |
| brief `assumed`: coerce 後驗整條時間軸足以涵蓋所有 NaT 來源 | **fact-verified（本輪否證未成功）** | `split_per_symbol` 在 `_coerce_timestamp_array` 後、`groupby` 前驗 `_ts_dt_index.hasnans`（`contracts.py:747-755`）；不可解析字串在 coerce 階段即 `DateParseError`（探針 `not-a-date`） |
| brief `assumed`: float／bool／object 三型即足夠 | **assumption，邊界已實跑** | object／bool／float 皆擋；`pd.array(..., dtype="Int64")` 經 `np.asarray` 變 `int64`（合法）；`np.matrix` 過 dtype 閘但在 `positions[train_local_arr]` 因多維索引 raise（仍 fail-closed） |
| brief `assumed`: 修補未改變既有數值輸出 | **fact-verified** | `python scripts/freeze_splitunify_golden.py` → **GOLDEN OK**；22 條 producer attest 全綠 |

### 修補複驗 1 — dtype 閘（對位 codex P1-01）— CLOSED

**① float64 反例**：`pytest …::test_producer_rejects_float_ordinals_before_cast` **PASSED**；探針 `split_per_symbol float64: RAISE ValueError … dtype 為 float64`。

**② 其他型別**：`_assert_integer_ordinals(object_int)`／`(bool)` **RAISE** 且訊息含 `dtype`；`pd.array Int64` 無 NA 時 `np.asarray`→`int64` 屬預期合法輸入；`np.matrix` 過閘後在索引階段 **RAISE** `Multi-dimensional indexing …`（非繞過）。

**③ 三 cast 點**：`grep _assert_integer_ordinals momentum/` → 恰三處——`contracts.py:772-773`（CPCV 迴圈 `:70-71` 與 `_build_plan_pair :247-248` 同函式）、WF 路徑 `:142-143` 產生之 `int64 arange` 仍經 `_build_plan_pair` 二次驗證。`ic_filter_orchestrator` 之 `_train_local = np.asarray(train_rows, dtype=int)`（`:637`）為 **holdout 內部切邊界**，非外來 splitter 回傳——與 codex 原始威脅模型不同，不算第四漏點。

### 修補複驗 2 — NaT 閘（對位 codex P1-02）— CLOSED

**① 原反例**：`pytest …::test_producer_rejects_nat_anywhere_on_the_time_axis` **PASSED**；未選第 8 列 `NaT` → `ValueError: split_per_symbol: 時間軸含 1 個 NaT`。

**② coerce 後路徑**：檢查點在 `_coerce_timestamp_array` **之後**（`:747-755`）；adapter 同型（`ic_split_adapter.py:190-198`）。不可解析 timestamp 在 coerce 即 fail，不會靜默成 plan。

**③ orchestrator**：`_normalize_ic_time_index` `:285-286` `if ts.hasnans: raise AlignmentViolationError`——與 brief 一致。

### 修補複驗 3 — 投影 docstring（對位 codex P2-03）— CLOSED

**碼證**：`split_projection.py:352` 已改 `test_plan.row_index_local[0]`；`:354` 僅保留「原寫全框 `row_index[0]`」之歷史註記；`:589` 明示「不是全框 universe」。`grep row_index\[0\]` 全檔僅上述歷史句，無其他以全框座標描述投影語意之段落。

## COMPOSER-R2-P2-01

**斷言**: `ic_split_adapter._with_row_positions` 的 NaT 閘引用 `AlignmentViolationError` 但未 import，觸發時抛出 `NameError` 而非契約例外——修補引入的實作缺陷（仍 fail-closed，但錯誤型別與 orchestrator／測試預期不一致）。

**碼證**: `ic_split_adapter.py:13-22` imports 無 `AlignmentViolationError`；`:195-198` 使用之。探針 `adapter._with_row_positions(frame_with_nat, …)` → `NameError: name 'AlignmentViolationError' is not defined`。對照 `contracts.py:933` 定義該例外；`split_per_symbol` NaT 路徑用 `ValueError` 且已有回歸測（僅覆蓋 contracts 路徑）。

**來源摘要**: momentum/Analysis/ic_split_adapter.py#8517730f1b29

P2；信心度=High。失效：adapter 路徑含 NaT 時 caller 若只 catch `AlignmentViolationError`／`ValueError` 會漏接；觀測上仍阻擋 bad input。修法：自 `momentum.core.contracts` import `AlignmentViolationError`（或改 raise `ValueError` 與 contracts 對齊）並補 adapter NaT 回歸測。可行性：一行 import + 一條 pytest，局部修補。

## 主動攻擊面（停輪②）

除三條 codex 修補對位複驗外，另攻：

1. **第四 dtype 繞過型別**：object／bool／float／`__index__` 物件／nullable Int64／np.matrix（見 §0 表）。
2. **NaT 在檢查點之後**：coerce 失敗、coerce 後全軸 NaT、adapter 與 orchestrator 對照。
3. **合法 int64 誤擋**：探針 `legal int64 plan: train_local=[0,1,2] test_local=[5,6]` **NO_RAISE**。
4. **golden 位移**：`freeze_splitunify_golden.py` → **GOLDEN OK**。
5. **投影 doc 殘留全框座標**：全檔 grep（見 P2-03）。

除 **COMPOSER-R2-P2-01**（adapter import 漏）外，未構造出需阻擋收案之 P0／P1。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `pytest tests/momentum/core/test_splitunify_producer_attest.py::test_producer_rejects_float_ordinals_before_cast tests/momentum/core/test_splitunify_producer_attest.py::test_producer_rejects_bool_ordinals_by_dtype_gate_not_by_luck tests/momentum/core/test_splitunify_producer_attest.py::test_producer_rejects_nat_anywhere_on_the_time_axis -q` | **3 passed** |
| `pytest tests/momentum/core/test_splitunify_producer_attest.py -q` | **22 passed** |
| `PYTHONPATH=. python /tmp/composer_b8_r2_probe.py` | dtype／NaT／legal 探針輸出見上文 |
| `python scripts/freeze_splitunify_golden.py` | **GOLDEN OK** rc=0 |

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R1-P1-01, CODEX-R1-P1-02, CODEX-R1-P2-03

ASSUMPTIONS_VERIFIED: 三條 codex 修補逐條複驗＋dtype／NaT 邊界探針＋golden OK  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b8-review-r2-composer.md --family composer`  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（仅审查）

STATUS: DONE
