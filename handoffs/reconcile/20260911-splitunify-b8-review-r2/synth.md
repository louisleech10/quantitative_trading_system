# Reconcile — 20260911-splitunify-b8-review-r2

**來源** 20260911-splitunify-b8-review-r2-codex.md, 20260911-splitunify-b8-review-r2-composer.md, 20260911-splitunify-b8-review-r2-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

🔴 本輪**不改規格**：唯一 finding 是主委在 R1 修補時引入的實作缺陷，修訂落在實作與測試。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| adapter 的 NaT 閘引用未匯入之例外，觸發時拋 `NameError`——「`ic_split_adapter._with_row_positions` 的 NaT 閘引用 `AlignmentViolationError` 但未 import」／「`ICSplitAdapter._with_row_positions` 的 NaT guard 引用未 import 的 `AlignmentViolationError`」／「R1 修補在 `ICSplitAdapter._with_row_positions` 的整條時間軸 NaT 閘會因未匯入 `AlignmentViolationError` 而在觸發時拋 `NameError`」 | P1 | GROK-R2-P1-01, CODEX-R2-P2-01, COMPOSER-R2-P2-01 | 採納（三家指同一缺陷，為主委修 `CODEX-R1-P1-02` 時自行引入。嚴重度 grok 判 P1、另兩家判 P2，依「分歧採較嚴版」取 P1——理由：`NameError` 不在 `ValueError` 階層，會穿透呼叫端既有的 `except ValueError`／`except AlignmentViolationError`，等於契約例外未交付。修法：自 `momentum.core.contracts` 匯入 `AlignmentViolationError`（與 orchestrator 同源）；補 adapter 路徑回歸測試兩條——NaT 須拋契約例外且訊息含 NaT、乾淨時間軸不得誤擋。探針複驗：修補前 `NameError`、修補後 `AlignmentViolationError`） |

**R1 三條 findings 之閉合**：codex（原提出方）逐條給出 `CLOSED_DETAIL` 並 `CLOSED: CODEX-R1-P1-01, CODEX-R1-P1-02, CODEX-R1-P2-03`；
composer 同樣 `CLOSED` 三條。codex 另複驗了主委未測的型別（nullable `Int64` 正規化為合法 int64、
`np.matrix` 因二維索引 fail-closed、帶 `__index__` 的自訂物件），皆無靜默錯誤 plan。

**主委的查證方法錯誤（記錄，非 finding）**：修 `CODEX-R1-P1-02` 時我曾 grep `AlignmentViolationError`
確認可用，但命中的正是**我自己剛寫的那一行 raise**——把自己的新增當成 import 存在的證據。
教訓：驗證某符號可用，要看 **import 區**或實際執行，不能只看名字在檔案裡出現過。

**交件格式正規化（透明度，責任在主委）**：composer 的裁決塊 `CLOSED:` 欄列了三個
`CODEX-R1-*` ID，而契約要求該欄**只列本家** ID ⇒ `register-output` 拒收。
根因是**我的 R2 brief 格式範例**直接寫了 `CLOSED: CODEX-R1-P1-01, …`——那是給原提出方 codex 的，
composer 照抄。主委依契約將其 `CLOSED:` 清空（它本來就沒有自家 findings 可閉合）；
它對 codex 三條的閉合確認完整保留在該檔正文的「複驗」表與 §0，**語意未變**。
下次 brief 的格式範例須分家族寫明。

**誠實邊界**：IC 端到端真實 run 仍**未跑**，三家皆同此限縮。本輪驗證面為 227 條目標測試面
＋ golden 凍結比對（GOLDEN OK）＋ 四條探針（0/4 成立）。

Verdict: 需修補後合併（唯一 finding 已於本輪修補，待 R3 由三家複驗閉合）

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P2-01
**斷言**: `ICSplitAdapter._with_row_positions` 的 NaT guard 引用未 import 的 `AlignmentViolationError`，NaT 輸入實際拋 `NameError` 而非預期的 typed fail-closed error。
**碼證**: `momentum/Analysis/ic_split_adapter.py:13-22,190-198` 缺該 import 但直接 raise；獨立 probe stdout=`adapter._with_row_positions: NameError name 'AlignmentViolationError' is not defined`。RECHECK：補同一 contracts import，重跑該 probe 與 adapter 測試。
**來源摘要**: momentum/Analysis/ic_split_adapter.py#8517730f1b29; momentum/core/contracts.py#1471cef968a3
[P2/high] 影響限於含 NaT 的 invalid-input 路徑，仍 fail-closed 但會變成內部錯誤；可行性證據：`contracts.py:933` 已有類別，orchestrator `:73` 已用同一 import；只在記憶體補該 binding 的 probe 回 `AlignmentViolationError` 且 `EXPECTED_TYPED_FAIL_CLOSED=True`。

## COMPOSER-R2-P2-01

**斷言**: `ic_split_adapter._with_row_positions` 的 NaT 閘引用 `AlignmentViolationError` 但未 import，觸發時抛出 `NameError` 而非契約例外——修補引入的實作缺陷（仍 fail-closed，但錯誤型別與 orchestrator／測試預期不一致）。

**碼證**: `ic_split_adapter.py:13-22` imports 無 `AlignmentViolationError`；`:195-198` 使用之。探針 `adapter._with_row_positions(frame_with_nat, …)` → `NameError: name 'AlignmentViolationError' is not defined`。對照 `contracts.py:933` 定義該例外；`split_per_symbol` NaT 路徑用 `ValueError` 且已有回歸測（僅覆蓋 contracts 路徑）。

**來源摘要**: momentum/Analysis/ic_split_adapter.py#8517730f1b29

P2；信心度=High。失效：adapter 路徑含 NaT 時 caller 若只 catch `AlignmentViolationError`／`ValueError` 會漏接；觀測上仍阻擋 bad input。修法：自 `momentum.core.contracts` import `AlignmentViolationError`（或改 raise `ValueError` 與 contracts 對齊）並補 adapter NaT 回歸測。可行性：一行 import + 一條 pytest，局部修補。

## GROK-R2-P1-01

**斷言**: R1 修補在 `ICSplitAdapter._with_row_positions` 的整條時間軸 NaT 閘會因未匯入 `AlignmentViolationError` 而在觸發時拋 `NameError`，使得 CODEX-R1-P1-02 於 adapter 路徑的契約例外（`AlignmentViolationError`＋NaT 訊息）未成立，且 `NameError` 不在 `ValueError` 階層、會穿透既有 `except ValueError`／`AlignmentViolationError` 處理。

**碼證**: `ic_split_adapter.py:13-22` import 無 `AlignmentViolationError`，同檔 `:193-198` 卻 `raise AlignmentViolationError(...)`；實跑含未選 NaT 之 frame 經 `_with_row_positions`／`split_cpcv` → `NameError: name 'AlignmentViolationError' is not defined`；同輸入經 `split_per_symbol` → `ValueError` 且訊息含 `NaT`；`test_producer_rejects_nat_anywhere_on_the_time_axis` 只覆蓋 `split_per_symbol` 故缺 import 全綠漏網。RECHECK：`PYTHONPATH=. python -c "…ICSplitAdapter()._with_row_positions(fr_with_nat,…)"` 預期現況 NameError，修補後應為 AlignmentViolationError 且訊息含 NaT。

**來源摘要**: momentum/Analysis/ic_split_adapter.py#8517730f1b29;handoffs/20260911-splitunify-b8-review-r1-codex.md#c55afb999b4f;handoffs/20260911-SPLITUNIFY-B8-REVIEW-R2-BRIEF.md#e8ac368e3762;tests/momentum/core/test_splitunify_producer_attest.py#e9105a6d7284

[P1/high] 信心度=High。  
會怎麼失敗：含缺時刻之 universe 走進 CPCV／WF adapter 時以未分類 `NameError` 崩潰，監控／caller 無法依 `AlignmentViolationError` 分類；R1 宣稱之 adapter NaT fail-closed 訊息永不出現。資料雖未靜默進 plan，但修補本身未交付所宣稱的契約。  
**修法**：在 `ic_split_adapter.py` 自 `momentum.core.contracts` 匯入 `AlignmentViolationError`（與 orchestrator／contracts 既有型別對齊）。  
**可行性證據**：`AlignmentViolationError` 已定義於 `contracts.py:933` 且為 `ValueError` 子類；同模組已自該處匯入多個符號，加一名字即可；另補一條 adapter 路徑測試（`pytest.raises(AlignmentViolationError, match="NaT")` 呼叫 `_with_row_positions` 或 `split_wf`／`split_cpcv`）以防再漏。本輪禁改碼，僅開 finding。

---

