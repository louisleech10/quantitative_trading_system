# SPLITUNIFY 第 8 批（b8）閉合輪 R3 — COMPOSER

task-id: 20260911-SPLITUNIFY-B8-REVIEW-R3  
family: composer  
findings-round: R3  
審查對象: R2 修補（`ic_split_adapter.py` 匯入 `AlignmentViolationError`＋adapter 路徑 NaT 測試兩條）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief `fact-verified`: R2 三家一致之 `NameError` 缺陷已修補 | **fact-verified（本輪複驗一致）** | `ic_split_adapter.py:13-14` 已自 `momentum.core.contracts` 匯入 `AlignmentViolationError`；探針含未選 `NaT` → `AlignmentViolationError` 且訊息含 `NaT`，非 `NameError` |
| brief `assumed`: adapter 與 `split_per_symbol` NaT 閘語意等價（例外型別不同） | **assumption，本輪未否證** | 同輸入：adapter → `AlignmentViolationError`（`ValueError` 子類）；`split_per_symbol` → `ValueError`（`contracts.py:751-755`）。兩者皆 fail-closed、訊息皆含 `NaT`；**未**在同一 caller 下比對 `except` 分支差異 |
| brief `assumed`: 無第三個同型缺陷（未匯入符號／閘只覆蓋單一路徑） | **fact-verified（本輪攻擊未成功）** | b8 五個 producer 檔 AST `raise` 掃描 0 真陽性；三 producer 皆接 `attest_row_index_local`＋dtype／NaT 閘（見下） |
| brief `assumed`: 修補未改變既有數值輸出 | **fact-verified** | `python scripts/freeze_splitunify_golden.py` → **GOLDEN OK** |

### R2 finding 閉合複驗（COMPOSER-R2-P2-01）

**① 修補對位**：`ic_split_adapter.py:13-14` imports 含 `AlignmentViolationError`；`:195-198` 仍 raise 該型別。

**② 反例重跑**（本人探針 `/tmp/composer_b8_r3_probe.py`）：
- 含未選第 8 列 `NaT` 之 frame 經 `ICSplitAdapter._with_row_positions` → `adapter_nat: AlignmentViolationError has_nat=True msg=ic_split_adapter: 時間軸含 1 個 NaT——…`
- 乾淨時間軸正例 → `adapter_clean: rows=12 has_pos=True`

**③ 回歸測**：
- `test_adapter_path_nat_raises_the_contract_exception_not_nameerror` **PASSED**
- `test_adapter_path_accepts_a_clean_time_axis` **PASSED**
- 對照 `split_per_symbol` 路徑 `test_producer_rejects_nat_anywhere_on_the_time_axis` **PASSED**

修補完全對位本家 R2 finding；`NameError` 不再出現。

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無需阻擋收案之新 P0／P1／P2 finding——`COMPOSER-R2-P2-01` 已閉合，且主動攻「第三個同型缺陷」未構造出實質漏洞。

**碼證**: ① R2 反例重跑（上節探針＋三條 NaT pytest）全符合預期。② AST `raise` 掃描 `ic_split_adapter.py`／`contracts.py`／`ic_filter_orchestrator.py`／`split_projection.py`／`split_preview.py`：唯一命中為 `ic_filter_orchestrator.py:3697` 之 `raise pending`（`pending` 為已捕獲之 `AlignmentViolationError` 實例，非未匯入類別）。③ 三 producer 閘對照：`split_per_symbol` NaT `:751-755`＋dtype `_assert_integer_ordinals`；adapter NaT `:194-198`＋dtype `:71-72,248-249`；orchestrator NaT `_normalize_ic_time_index :285-286`、plan 組裝 `:677` `attest_row_index_local`、labels NaT `:822-823`。④ 目標測試面 175 passed＋golden OK。

**來源摘要**: momentum/Analysis/ic_split_adapter.py#b05b0f73e417;handoffs/20260911-SPLITUNIFY-B8-REVIEW-R3-BRIEF.md#e8ac368e3762

P3 sentinel；信心度=High。誠實邊界：IC 端到端真實 run 未跑；adapter／`split_per_symbol` 例外型別差異為既有設計，非本輪新引入。

## 主動攻擊面（停輪②）

除 `COMPOSER-R2-P2-01` 閉合複驗外，另攻：

1. **未匯入符號**：五檔 AST `raise` 掃描（見 sentinel）；手動核對 `EmbargoRelaxedError` 為同檔 `:30` 定義之本地類別。
2. **閘只覆蓋單一路徑**：NaT／dtype／`attest_row_index_local` 三 producer 對照（見 sentinel ③）；R2 漏網根因（只測 `split_per_symbol`）已由 `test_adapter_path_nat_*` 兩條補上。
3. **合法輸入誤擋**：探針乾淨時間軸 **NO_RAISE**（12 行＋`_split_row_pos`）。
4. **golden 位移**：`freeze_splitunify_golden.py` → **GOLDEN OK**。
5. **修補引入新回歸**：splitunify 相關 8 檔測試面 **175 passed**。

未構造出需開新 finding 之第三同型缺陷。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `pytest tests/momentum/core/test_splitunify_producer_attest.py::test_adapter_path_nat_raises_the_contract_exception_not_nameerror tests/momentum/core/test_splitunify_producer_attest.py::test_adapter_path_accepts_a_clean_time_axis tests/momentum/core/test_splitunify_producer_attest.py::test_producer_rejects_nat_anywhere_on_the_time_axis -q` | **3 passed** |
| `pytest tests/momentum/core/test_splitunify_producer_attest.py -q` | **24 passed** |
| `pytest tests/momentum/core/test_splitunify_producer_attest.py tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/momentum/core/test_splitunify_boundary.py tests/momentum/event_samples/test_splitunify_wiring.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py -q` | **175 passed** |
| `PYTHONPATH=. python /tmp/composer_b8_r3_probe.py` | adapter NaT→`AlignmentViolationError`+NaT；clean OK；static_raise_scan 1 false positive |
| `python scripts/freeze_splitunify_golden.py` | **GOLDEN OK** rc=0 |

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R2-P2-01

ASSUMPTIONS_VERIFIED: R2 反例重跑＋AST raise 掃描＋三 producer 閘對照＋175 pytest＋golden OK  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b8-review-r3-composer.md --family composer`  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（仅审查）

STATUS: DONE
