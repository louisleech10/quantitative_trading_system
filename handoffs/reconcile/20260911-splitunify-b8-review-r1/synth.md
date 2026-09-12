# Reconcile — 20260911-splitunify-b8-review-r1

**來源** 20260911-splitunify-b8-review-r1-codex.md, 20260911-splitunify-b8-review-r1-composer.md, 20260911-splitunify-b8-review-r1-grok.md　|　**roster** codex,composer,grok


## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

🔴 本輪**不改規格**：三條 codex findings 皆為「實作未達成已定案規格」，修訂落在實作與測試；
規格條款（§4.8／§5／§4.10–4.11）維持原文，本欄標示的是判準來源。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| dtype 閘被前置 cast 繞過——「D-001-C2 §4.8 要求 producer 對 `row_index_local` 的 numpy integer dtype 先 fail-closed」 | P1 | CODEX-R1-P1-01 | 採納（主委獨立複驗：float64 `[0.,1.,2.]` 確為 NO_RAISE 並產出 `int64[0,1,2]`。新增 `contracts._assert_integer_ordinals` 擋在 `astype(int)` 之前，三個 cast 點全數接上；補三條 producer 路徑回歸測試，其中 bool 那條限定訊息含 `dtype`——修正前它是碰巧被遞增閘攔到，不限定就沒有鑑別力） |
| 未選列 NaT 不擋——「SPEC §5 明定 `NaT` fail-closed；兩 producer 只對被選列呼叫 epoch 正規化」 | P1 | CODEX-R1-P1-02 | 採納（主委獨立複驗確為 NO_RAISE。`split_per_symbol` 與 `ic_split_adapter._with_row_positions` 改對**整條**時間軸驗 NaT，補回歸測試） |
| 投影文件仍用全框座標——「D-001-C2 §4.10–4.11 要求 projection 文件使用 local 座標」 | P2 | CODEX-R1-P2-03 | 採納（`_derive_single_symbol` 第一段判定之 docstring 改寫為 `row_index_local[0]`，並註明會誘導後人把全框列號當標的內序號） |
| 逐項核對後無阻擋收案之缺陷——「本輪逐項核對 b8 七筆 commit（座標語意、指紋時鐘同源」 | P3 | COMPOSER-R1-P3-00 | 採納（sentinel。其 §0 將「本批回歸為零」與「IC 端到端」列為它自己未複驗之項，如實記入收案說明，不當成經過查證的事實） |
| 逐項核對後無 finding——「本輪逐項核對後無 finding——必答 1–5 皆有碼證與實跑」 | P3 | GROK-R1-P3-00 | 採納（sentinel。其指正之 orchestrator「同一支時鐘」措辭不精確已修；float 秒兩路值分叉已記為地雷，目前靠前置閘擋住） |

**M-SU-D1-23**：三家一致維持 `needs-research`（單標的 golden 下 local == row_index，該 mutation 不可觸發；
重凍會移動既有 digest，成本大於收益）。交錯語意已由 producer 契約測試與 derive 交錯 fixture 覆蓋。

**誠實邊界（收案說明必須帶）**：IC 端到端真實 run **未跑**，三家皆同此限縮；
本輪驗證面為 b8 目標測試面（203 passed）＋ golden 凍結比對（GOLDEN OK）＋ mutation 22/22。

Verdict: 需修補後合併（三條 codex findings 已於本輪修補，待原提出方複驗閉合）

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**：D-001-C2 §4.8 要求 producer 對 `row_index_local` 的 numpy integer dtype 先 fail-closed；`split_per_symbol` 與 adapter 卻先轉 `int`，可靜默救活／截斷非法 ordinal。
**碼證**：`contracts.py:741-750`、`ic_split_adapter.py:64-69,232-237` 在 attest (`contracts.py:802-809`、`ic_split_adapter.py:281-288`) 前 cast；實跑 float64 `[0.0,1.0]` 均 `NO_RAISE` 並產出 `int64 [0,1]`。
**來源摘要**: momentum/core/contracts.py#9c81df6c2808; momentum/Analysis/ic_split_adapter.py#a3da0c9b8555; docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f
[P1/high] 失效：錯誤 splitter 可把非整數座標映到錯列而不報錯；修法：原始 `np.asarray` 先獨立 dtype gate，通過後才轉 int/index；可行性：局部 producer 修補並各加 float/bool/object route test。
## CODEX-R1-P1-02
**斷言**：SPEC §5 明定 `NaT` fail-closed；兩 producer 只對被選列呼叫 epoch 正規化，未選 `NaT` 可進入有效 SplitPlan。
**碼證**：`contracts.py:732,758-762`、`ic_split_adapter.py:184-188,239-243` 只驗 selected rows；`validate_split_integrity:625-655` 無全域 NaT guard 且空列可在 guard 前 return；實跑含未選 `NaT` 的 frame 兩 producer 均 `NO_RAISE`。
**來源摘要**: momentum/core/contracts.py#9c81df6c2808; momentum/Analysis/ic_split_adapter.py#a3da0c9b8555; docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f
[P1/high] 失效：含缺時刻的 base universe 可被當成 rows-purge 有效資料；修法：producer 建 plan 前對完整 canonical time axis 做 NaT 檢查（orchestrator 已由 `:285-286` 擋）；可行性：局部前置 gate，不動 schema。
## CODEX-R1-P2-03
**斷言**：D-001-C2 §4.10–4.11 要求 projection 文件使用 local 座標；`_derive_single_symbol` docstring 仍以全框 `test_plan.row_index[0]` 描述測試起點。
**碼證**：`momentum/Analysis/event_samples/split_projection.py:350-355`；實作後續已改讀 `row_index_local`，故此為文件與契約不一致而非目前 runtime 索引。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#a77abd9bf671; docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f
[P2/high] 影響：後續維護可能把全框 row 當 local ordinal；修法：改寫該段為 `time_bounds`／local 座標語意；可行性：文件-only。
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
## GROK-R1-P3-00

**斷言**: 本輪逐項核對後無 finding——必答 1–5 皆有碼證與實跑／反例；主動攻擊之座標／時鐘／合取／pickle／鑑別力面均未找出需阻擋 b8 收案的缺陷；M-SU-D1-23 維持 needs-research 不重報。

**碼證**: `PYTHONPATH=. python /tmp/grok-b8-review-r1/probe_all.py` → EXIT 0（C1 指紋擋、C2 遞增擋、D1–D4 入口擋、D5 協調偽造放行但合 SPEC）；`probe_float_and_adapter.py` → float holdout raise、DatetimeIndex 端點相等、`_SYMBOL_SET_MISMATCH` 無跨層消費；`pytest … -k 'per_symbol or fingerprint or insufficient' -q` → 22 passed；`pytest tests/momentum/core/test_splitunify_producer_attest.py -q` → 19 passed；HEAD=`da4bdc4370b9`。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B8-REVIEW-R1-BRIEF.md#5d03282d463f;docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f;handoffs/run_receipts/20260912-splitunify-b8-mutation-selfcheck.md#fe67c1637668;momentum/core/contracts.py#9c81df6c2808;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293;momentum/Analysis/ic_split_adapter.py#a3da0c9b8555;momentum/Analysis/event_samples/split_projection.py#a77abd9bf671;momentum/core/split_preview.py#95a85ec0de54

[MINOR] 信心度=High。sentinel only；非實質缺陷。

---

