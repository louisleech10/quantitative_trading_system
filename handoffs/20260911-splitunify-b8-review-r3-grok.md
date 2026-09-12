# SPLITUNIFY b8 審碼 R3（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-B8-REVIEW-R3  
family: grok  
findings-round: R3  
標的：R2 finding `GROK-R2-P1-01`（adapter NaT 閘缺 `AlignmentViolationError` import）閉合複驗  
SCOPE: review-only；禁改碼  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄  
探針：`/tmp/grok-b8-review-r3/probe_r3_nat.txt`、`probe_cpcv_nat.txt`、`import_scan2.txt`（交件後清掉）  
HEAD（本輪起點）：`4ca339b4`（含修補 `655d52d4`）

### §0 前提宣告（本輪覆核）

fact-verified: `GROK-R2-P1-01` 反例已關閉——`ICSplitAdapter._with_row_positions` 餵含未選 `NaT` 的 frame 現拋 `AlignmentViolationError`（非 `NameError`），訊息含 `NaT`；`AlignmentViolationError` 為 `ValueError` 子類。探針 A／CPCV 入口同結果。

fact-verified: `ic_split_adapter.py:13-22` 已自 `momentum.core.contracts` 匯入 `AlignmentViolationError`；同檔 `:196` raise 使用該名。修補 commit `655d52d4` 僅加該 import＋兩條 adapter 測試。

fact-verified: 新增回歸測 `test_adapter_path_nat_raises_the_contract_exception_not_nameerror` 與 `test_adapter_path_accepts_a_clean_time_axis` 皆 PASS；同檔 `test_producer_rejects_nat_anywhere_on_the_time_axis`（`split_per_symbol`）仍 PASS。`test_splitunify_producer_attest.py` → **24 passed**。

fact-verified: `freeze_splitunify_golden.py` → `GOLDEN OK`（digest 未位移）。

fact-verified: 五個 b8 相關檔之 `raise <Name>` 靜態掃描——`ic_split_adapter`／`contracts`／`split_preview`／`split_projection` 無 missing import；`ic_filter_orchestrator:3697` 之 `raise pending` 為區域變數（deferred scaffold exception），非未匯入類別名。

assumed: adapter 與 `split_per_symbol` 兩條路徑的 NaT 閘語意等價（例外型別不同）  
→ 本輪實跑：兩者皆 fail-closed 且訊息含 `NaT`；adapter → `AlignmentViolationError`（亦為 `ValueError`）；`split_per_symbol` → 裸 `ValueError`（非 AV 子類）。`except ValueError` 兩路皆接得到；`except AlignmentViolationError` 只接 adapter。此型別不對稱為 brief 已標明的既有契約差，非本修補引入；orchestrator 交叉路徑（`:945-963`）會先跑 adapter 閘，NaT 在進 `split_per_symbol` 前已被 AV 擋下。**未**找到因型別差而讓壞資料進 plan 的活路徑 → 語意等價（fail-closed）**HOLDS**。  
assumed: 這次沒有再引入第三個同型缺陷  
→ 靜態 raise 掃描＋修補 diff 僅一行 import＋測試 → **HOLDS**（見主動攻擊面）。  
assumed: 修補未改變任何既有數值輸出  
→ `GOLDEN OK`＋合法乾淨時間軸 adapter `NO_RAISE` → **HOLDS** 於 golden／單元面；**未**跑 IC 端到端真實 run（與 brief 自承邊界一致）。

---

## 閉合判定（對 GROK-R2-P1-01；章程 §B8 重跑）

| 項目 | R2 觀測 | R3 重跑 |
|---|---|---|
| 例外型別 | `NameError: name 'AlignmentViolationError' is not defined` | `AlignmentViolationError` |
| 訊息含 `NaT` | 否（NameError 無契約訊息） | 是（`時間軸含 1 個 NaT`） |
| `issubclass(AV, ValueError)` | n/a | True |
| CPCV 入口（`split_cpcv`） | 同 NameError | 同 `AlignmentViolationError`＋NaT |
| 乾淨時間軸 | n/a（本輪補正例） | `NO_RAISE` |

**判定：`CLOSED`。** 契約例外已交付；`NameError` 路徑不再可觸發。

---

## 主動攻擊面（停輪條件②／③）

本輪主動攻且**未**另開洞者：

1. **原反例重跑**（`_with_row_positions`＋未選 NaT）→ 已關。  
2. **公開入口** `split_cpcv` 同輸入 → 同樣 AV＋NaT（閘在 `_with_row_positions` 共用，非只靜態方法測試綠）。  
3. **同型缺 import**：對 adapter／contracts／orchestrator／split_preview／split_projection 做 raise-名 vs import／本地 class 掃描 → 無第三個 missing。  
4. **單路徑閘**：NaT 在 adapter 與 `split_per_symbol` 各有測試；修補 diff 未改閘條件本身。  
5. **誤擋正例**：乾淨時間軸 adapter 放行。  
6. **數值／golden**：`GOLDEN OK`。  
7. **型別不對稱是否活缺陷**：見 §0；無 caller 只 catch AV 卻只走 `split_per_symbol` NaT 而漏接並放行壞資料的路徑。

**成功開洞者：無。**

---

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——`GROK-R2-P1-01` 已關閉（adapter NaT 閘現拋 `AlignmentViolationError` 且訊息含 `NaT`），且對缺 import／單路徑閘／golden 位移三面主動攻擊未再開出新洞。

**碼證**: ①探針 `_with_row_positions(frame_with_nat)` → `AlignmentViolationError: …時間軸含 1 個 NaT…`（非 NameError）；`split_cpcv` 同。②`pytest tests/momentum/core/test_splitunify_producer_attest.py -q` → 24 passed。③`python scripts/freeze_splitunify_golden.py` → GOLDEN OK。④ast raise 掃描五檔無 missing import（orchestrator `raise pending` 為變數）。⑤`git show 655d52d4` 僅 `+ AlignmentViolationError` import＋兩測。RECHECK：重跑上列探針／三測／golden。

**來源摘要**: momentum/Analysis/ic_split_adapter.py#b05b0f73e417;tests/momentum/core/test_splitunify_producer_attest.py#fbe4779e8477;handoffs/20260911-SPLITUNIFY-B8-REVIEW-R3-BRIEF.md#0946a5e7ba12;handoffs/20260911-splitunify-b8-review-r2-grok.md#dddba28f06a2

[P3/sentinel] 信心度=High。零實質 finding；本條為停輪合法 sentinel，非湊數。

---

## 被當成事實的未驗證假設（§0）

1. 「修補後契約例外已交付」——**fact-verified**（本家重跑）。  
2. 「兩路徑 NaT 語意等價」——fail-closed **HOLDS**；型別不對稱為已標明既有差，非新缺陷。  
3. 「無第三同型缺陷」——靜態掃描＋diff 範圍 **HOLDS**。  
4. 「IC e2e ≡ 單元」——仍 assumed（本輪未跑 e2e）。

ASSUMPTIONS_VERIFIED: GROK-R2-P1-01 反例關閉；import 在場；兩條新測＋sps NaT 測綠；golden 未位移；raise 掃描無第三 missing。  
TESTS_RUN: `pytest tests/momentum/core/test_splitunify_producer_attest.py -q` → 24 passed；三條 NaT／正例定向 `-v` → 3 passed；`scripts/freeze_splitunify_golden.py` → GOLDEN OK；探針 `_with_row_positions`／`split_cpcv`／sps 對照／caller catch 模擬。  
FAILURES_SEEN: none（R2 NameError 本輪未再現）。  
SCOPE_CHANGES: none（review-only）。  
NUMERIC_OR_SCHEMA_IMPACT: none（本輪無改碼）；golden 未位移。  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b8-review-r3-grok.md`

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R2-P1-01
STATUS: DONE
