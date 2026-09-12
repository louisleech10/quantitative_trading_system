# SPLITUNIFY 第 8 批（b8）審碼 R1 — COMPOSER

task-id: 20260911-SPLITUNIFY-B8-REVIEW-R1  
family: composer  
findings-round: R1  
審查對象: commits `f75454c9`…`8f2c228a`（七筆生產／測試 commit；見 brief 表）  
規格: `docs/SPLITUNIFY_SPEC.D-001.md` Task 8.1／8.2／8.3、`M-SU-D1-01`～`23`

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief `fact-verified`: 三條 `-k per_symbol`／`fingerprint`／`insufficient` 曾 0 selected | **fact-verified** | 本人複驗：`pytest tests/momentum/Analysis/test_splitunify_derive.py -k "per_symbol or fingerprint or insufficient" -q` → **22 passed, 56 deselected** |
| brief `fact-verified`: mutation 22/22 CAUGHT、`M-SU-D1-23` 不可觸發 | **fact-verified** | 讀 `handoffs/run_receipts/20260912-splitunify-b8-mutation-selfcheck.md`；與 `test_splitunify_producer_attest.py` 交錯 fixture 語意一致 |
| brief `assumed`: 指紋時鐘＝各 producer 自己 `time_bounds` 那支 | **fact-verified（本輪否證未成功）** | 見必答 2；`ic_holdout` 探針 `ms0==tb0_ms`；`29582d96` 修掉秒／毫秒混餵自傷 |
| brief `assumed`: `_SYMBOL_SET_MISMATCH` 不進封閉值集不削弱守衛 | **fact-verified** | `grep _SYMBOL_SET_MISMATCH` 僅 `split_projection.py:76,617`；無消費端分支 |
| brief「本批回歸為零」 | **assumption，未重跑 2,200 條** | 成本項；本輪只跑 b8 目標測試面＋golden |
| brief「未跑 IC 端到端真實 run」 | **assumption，未驗** | 本輪同限縮；碼路徑 `ic_filter_orchestrator._build_holdout_split_plan` 已讀＋探針 |

## 必答 1 — 座標語意：三 producer 的 `row_index_local` 是否皆為「該標的依時刻排序後」序號？

**立場：是。** 三處皆先 `sort_values(ts_col, kind="mergesort")` 取得 `positions`（時間序全框位置），再直接取用 splitter／boundary 回傳的**標的內序號**（非 `_local_ordinals_for_symbol` 的 frame 序）。

| Producer | 碼證 |
|----------|------|
| `split_per_symbol` | `contracts.py:741-747` `group_sorted = group.sort_values(ts_col)` → `positions = group_sorted["_split_row_pos"]`；`train_local_arr`／`test_local_arr` 直接寫入 `row_index_local`（`:775,794`）；`attest_row_index_local(..., sorted_positions=positions)`（`:803-808`） |
| `ic_split_adapter` | `ic_split_adapter.py:64-65,129-130` 同上排序；`:232-234` 註解＋`:255,273` 寫入；`:282-287` attest |
| `ic_filter_orchestrator` | 單標的 holdout：`:635-637` `_train_local = np.asarray(train_rows)`（`holdout_boundary` 在已正規化之單標的索引上切）；`:675` `sorted_positions = np.arange(n_rows)`（單標的且 index 單調 ⇒ 時間序＝位置序） |

**反例（frame 序會錯）**：`test_splitunify_producer_attest.py:75-89` 兩標的交錯 fixture 要求 `row_index_local ≠ row_index`；若誤用 frame 序，`attest_row_index_local` 的往返（`contracts.py:599-602`）或投影 membership 會紅（`test_attest_rejects_row_index_from_another_symbol`）。

## 必答 2 — 指紋時鐘與 plan `time_bounds` 是否同一支？

**立場：是（三處各用各自模組既有時鐘，不再新造第二套）。**

| Producer | `time_bounds` 時鐘 | 指紋時鐘 | 一致性碼證 |
|----------|-------------------|----------|------------|
| `split_per_symbol` | `_time_bounds_for_indices(ts, rows)` → `_coerce_timestamp_array(ts)`（`contracts.py:700-706,768`） | `_ts_dt_index = DatetimeIndex(_coerce_timestamp_array(ts))` → `epoch_ms_from_index(_ts_idx[rows])`（`:732,757-762`） | 同一 `ts` 陣列、同一 `_coerce_timestamp_array` |
| `ic_split_adapter` | `_time_bounds(ts, rows)`，`ts` 已在 `_with_row_positions` 內 `_coerce_timestamp_array`（`:186-187,249,310-311`） | `epoch_ms_from_index(pd.Index(ts)[rows])`（`:238-243`） | 同一 `full_ts` |
| `ic_filter_orchestrator` | `_time_bounds_for_rows(features_df.index, rows)` → `_coerce_timestamp_array`（`:559-564,651`） | `_feature_dt_index = _normalize_ic_time_index(...)` → `epoch_ms_from_index(_feature_dt_index[rows])`（`:603,642-646`） | 整數 epoch 秒兩路皆 `unit="s"`（`_coerce_timestamp_array:451`、`_normalize_ic_time_index:275-278`） |

**實跑（否證觀測）**：

```
# holdout 路徑，epoch 秒索引 [1700000000, 1700003600, 1700007200]
holdout ms0 1700000000000 tb0_ms 1700000000000 match True
```

若把 epoch 秒直接餵毫秒正規化器（`29582d96` 前之缺陷），`assert_epoch_ms_array` 指名 `looks like epoch seconds`——`tests/golden/ic_phase1_contract/test_split_leakage_golden.py::test_split_per_symbol_golden` 與 `tests/api/test_splitunify_disclosure` 曾全紅（brief／HANDOFF 已記）。

## 必答 3 — 指紋閘與遞增閘是否真為合取？

**立場：是；兩閘互不涵蓋。** 規格與碼：`split_preview.py:162-163`（指紋對重排不敏感）＋`split_projection.py:470-471`（合取明示）＋`assert_positional_rows` 嚴格遞增（`split_preview.py:179+`）。

| 僅該閘能擋的輸入 | 實跑結果 |
|------------------|----------|
| **遞增閘**：同集合重排 `[loc[0],loc[1]]` 交換 | `derive_event_split_from_plans` → `ValueError: row_index 非嚴格遞增`（探針 `/tmp/composer_b8_guard_probe.py`） |
| **指紋閘**：末元素 `+1` 仍嚴格遞增（`loc[-1]+1`） | → `ValueError: 逐列時刻指紋不符——plan 指紋 3faf55cd9765 vs 重算指紋 7f7f0ecc4451` |

對照測試：`test_fingerprint_reordered_rows_are_caught_by_monotonic_gate`（`match="非嚴格遞增"`）、`test_fingerprint_tampered_rows_are_caught_at_entry`（`match="指紋不符"`）。

## 必答 4 — 建構後竄改 `row_index_local` 是否全在投影入口被擋？

**立場：經 `derive_event_split_from_plans` 入口者會被擋；`pickle`／`deepcopy` 可保留竄改值但無法通過入口重驗。**

| 攻擊 | 結果 |
|------|------|
| `object.__setattr__(plan, "row_index_local", tampered)` 後直接 derive | **擋**（指紋重驗，`split_projection.py:477-495`） |
| `copy.deepcopy`／`pickle.loads(dumps)` 往返 | 竄改值**保留**（探針 `deepcopy preserves tamper: True`），但 derive 仍 **擋**（同上） |
| 繞過 derive、直接讀 `row_index_local` | **誠實邊界**（HANDOFF：`SplitPlan.__post_init__` 防禦性 copy＋唯讀 buffer 挡不住 pickle 還原後寫）——不在 b8 投影路徑 |

未構造出「經 derive 入口仍放行」的反例。

## 必答 5 — 測試鑑別力（任挑 3 條本批新增／強化測試）

| 測試 | 嘗試的「仍綠但程式壞了」改法 | 結果 |
|------|------------------------------|------|
| `test_fingerprint_reordered_rows_are_caught_by_monotonic_gate` | 把 `assert_positional_rows` 預設 `require_sorted=False`（`M-SU-D1-20`）或只寫 `pytest.raises(ValueError)` 不限訊息 | mutation 自證 **19／20 CAUGHT**；修正 `match="非嚴格遞增"` 後鑑別力恢復（收據 §首輪 4 條） |
| `test_per_symbol_missing_feature_index_entry_is_fail_closed` | `derive` 內缺 symbol 時 `raise`→`continue`（`M-SU-D1-09`） | 補測試前 **0 條紅**；補後 **CAUGHT** |
| `test_interleaved_producer_writes_monotonic_local_ordinals` | `attest_row_index_local` 判準改 frame 序（`M-SU-D1-15`） | **CAUGHT**（`test_splitunify_producer_attest.py` 交錯 fixture 往返不等） |

另：`test_splitunify_producer_attest.py:7-11` 明訂 `CrossSymbolLeakageError` 繼承 `ValueError`，前置閘測試必 `not isinstance(..., CrossSymbolLeakageError)`——避免與往返閘混淆（本批紀律已落實）。

## 主動攻擊面（停輪③）

本輪除必答外，另攻：

1. **秒／毫秒混用回歸**：小值 epoch 探針會被 `assert_epoch_ms_array` 指名（預期）；真實秒級時間戳下 holdout 兩端 ms 一致。
2. **交錯 vs 單標的語意漂移**：`test_interleaved_producer_local_differs_from_full_frame_row_index`＋`test_single_symbol_frame_local_equals_row_index` 成對鎖定。
3. **per-symbol 靜默丟棄**：`test_per_symbol_missing_feature_index_entry_is_fail_closed`。
4. **golden digest 位移**：`python scripts/freeze_splitunify_golden.py` → **GOLDEN OK**。
5. **`_SYMBOL_SET_MISMATCH` 字面逃逸**：僅定義處，無分支消費。
6. **producer attest 前置閘 vs 往返閘**：`test_splitunify_producer_attest.py` 全檔 `not isinstance(..., CrossSymbolLeakageError)` 紀律。

均未構造出需阻擋收案的實質缺陷。

## 已具名殘留 `M-SU-D1-23` — composer 裁定

**立場：`needs-research`，現階段不值得為單一 mutation 重凍 golden。**

理由：單標的 golden 下 `row_index_local` 與 `row_index` 逐值相同是 fixture 設計使然（`freeze_splitunify_golden.py` `_plans`）；**交錯語意**已由 `test_splitunify_producer_attest.py` 與 `test_splitunify_derive.py::_interleaved_case` 覆蓋。重凍會移動既有 digest（成本＞收益）。若未來 golden 自然升級為多標的，可順手補 oracle 分支，非 b8 阻擋項。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `pytest tests/momentum/Analysis/test_splitunify_derive.py -k "per_symbol or fingerprint or insufficient" -q` | **22 passed** |
| `pytest tests/momentum/core/test_splitunify_producer_attest.py tests/momentum/event_samples/test_splitunify_wiring.py -q` | **28 passed** |
| `pytest tests/momentum/Analysis/test_splitunify_golden.py -q` | **8 passed** |
| `python scripts/freeze_splitunify_golden.py` | **GOLDEN OK** rc=0 |

---

## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對 b8 七筆 commit（座標語意、指紋時鐘同源、雙閘合取、入口重驗、測試鑑別力、golden／mutation 收據）後，無需阻擋收案的 P0／P1 finding。

**碼證**: 必答 1–5 碼證行號＋上表複驗命令全綠；守衛合取探針（重排→`非嚴格遞增`、成員篡改→`指紋不符`）；`pickle`／`deepcopy` 保留竄改但 derive 入口擋下；`M-SU-D1-23` 裁定見上（不升格為缺陷重報）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f

P3 sentinel；信心度=High（目標測試面＋探針）；未跑全套 IC 端到端為誠實邊界，不影響本輪 b8 契約收斂判定。

---

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:

ASSUMPTIONS_VERIFIED: 必答 1–5 碼證＋22+28+8 pytest＋GOLDEN OK＋守衛／pickle 探針  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b8-review-r1-composer.md --family composer`  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（仅审查）

STATUS: DONE
