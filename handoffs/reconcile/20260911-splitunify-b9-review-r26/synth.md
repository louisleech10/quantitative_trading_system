# Reconcile — 20260911-splitunify-b9-review-r26

**來源** 20260911-splitunify-b9-review-r26-codex.md, 20260911-splitunify-b9-review-r26-composer.md, 20260911-splitunify-b9-review-r26-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **K1 codex 零 findings、`CODEX-R25-P1-01` 閉合、v21 APPROVED**——「本輪逐項核對後無finding；`COD」 | P3 | CODEX-R26-P3-00 | 採納（判 proceed） |
| **K2 composer 零 findings、v21 APPROVED**——「本輪逐項核對後無需阻擋收斂的findin」 | P3 | COMPOSER-R26-P3-00 | 採納（判 proceed） |
| **K3 grok 零 findings、v21 APPROVED**——「本輪逐項核對後無finding——`GR」 | P3 | GROK-R26-P3-00 | 採納（判 proceed） |

### 本輪裁定

1. **r25 之 J1 由三家原提出方各自 CLOSED**（`CODEX-R25-P1-01`／`COMPOSER-R25-P1-01`／`GROK-R25-P1-01`）。
2. 🏁 **`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0**——v21（body `755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f`）獲三家全數 APPROVED 且雜湊相符。**這是 v18 之後首次重新取得完整有效戳記**（v19／v20 兩版皆在取得前就被新 finding 打掉）。
3. 🔴 **必答 3 之加強版奏效，且三家詞表互不重疊**——本輪明令「不得只重跑主委用過的三 token」，三家各自列出詞表並逐段判定：codex 用「三段／第三層／揭露層／disclosure／end-to-end／three layers／third layer／`build_split_unify_disclosure`／`ic_filter_orchestrator`」等；composer 用「`context handoff`／`完整記帳`／`資料流交接`／`孤立欄位`／`手塞`／`exact-key.*discarded`」等；grok 分四類（層數同義／鏈驗收同義／揭露同義／防假綠落點）。**三家皆判 live 正文無新互斥** ⇒ 同型第七次**未**發作。
4. **三家對其餘必答一致**：`§P Task 9.1` `:187` 整條刪節**未**失去防假綠告誡——該告誡之兩層等價物仍在（§V `:258` 之 producer→summary 值相等 real-entry 斷言、TODO 之 `EventSamplePipeline.run` wiring 測試），原孤立 builder 手塞告誡只約束 deferred 的 metadata 層；`M-SU-D2-01`／`M-SU-D2-02` 之應紅欄皆仍指向當輪 summary 層測試，**未**指向已移出當輪者。
5. **三家一致判可進 `Task 9.2b`（批次 B9C），無 BLOCKING。**
6. **下一步**：領 impl token 進 `Task 9.2b`（B9C）——事件級 `decision_at_ms` 錨定、`EventSamplePipeline.run` 於 `derive_*` 前呼叫 `validate_split_pair_integrity`、三分支側別判定、`(3.2)` 之 `AlignmentViolationError` fail-closed ＋ 跨表互斥。完成後 `test_multi_feature_tf_opposite_sides_must_fail_closed` 之 `xfail(strict=True)` 應解除。

Verdict：可合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R26-P3-00

**斷言**: 本輪逐項核對後無 finding；`CODEX-R25-P1-01` 已 CLOSED，v21 之兩層交付與 `SU-RESID-9A-UI` deferred 邊界一致。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:52；MUTATION: `venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; assert "metadata" in EventPipelineResult.__annotations__'` → `AssertionError`, rc=1；live scan 逐段核對無另一個 live 三層交付要求。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#755f3d53c1f3, docs/SPLITUNIFY_TODO.md#7a18de5a95ff
ANSWER_1: (1a) CLOSED；(1b) 反例命令同上，stdout 為 `AssertionError`，rc=1，證明 `EventPipelineResult` 無 `metadata` 層。
ANSWER_2: (2a) APPROVED；(2b) 無阻擋項。
ANSWER_3: (3a) 詞表＝三段、第三層、揭露層、disclosure、end-to-end、end to end、整鏈、整條鏈、three layers、third layer、producer/summary/metadata、`build_split_unify_disclosure`、`ic_filter_orchestrator`；SPEC live §G／§P／§V／§R／§N 與 TODO §B／Task 4.1／Task 9.1／Task 9.2b／Task 9.3／§E 逐段判定，僅 `Task 4.1` 的五鍵與 B9C 的三段式屬其他契約。
ANSWER_3B: 無；§P:187、TODO:892 的 metadata/整鏈字面均在 deferred 或刪節語境，§V:258 明定 metadata assertions 移出當輪且兩層 real-entry assertion 仍在。
ANSWER_4: 否；兩層防假綠已由 §V:258 的 producer→summary real-entry assertion 與 TODO:488 的 `EventSamplePipeline.run` wiring test 保留，原孤立 builder 手塞告誡只約束 deferred metadata 層。
ANSWER_5: M-SU-D2-01、M-SU-D2-02 均仍指向當輪 summary 鍵／值測試，未指向移出的 metadata 測試；具名 derive 6 tests 與 wiring 1 test 實跑全數 passed。
ANSWER_6: 可以進 Task 9.2b／B9C；已檢查 eac26bfe current block/diff、同義詞掃描、R25 反例、C5 29/10/4/15/19 計數與既有測試，無 BLOCKING。
VERIFY: body hash rc=0，SPEC/TODO `doc_format_precheck` 各 rc=0；R24/R25 debt ledger state=CLOSED。
TESTS_RUN: `pytest ...test_splitunify_derive.py -k 'discarded or summary_has_all_sixteen_keys'` → 6 passed；wiring `-k 'discarded_rows_reaches_summary'` → 1 passed。
FAILURES_SEEN: R25 reverse probe `AssertionError` rc=1（預期反例）；`reconcile_stamps_check` rc=1 僅因三家 R26 stamp provenance pending、待 Claude register-output，非內容/格式失敗。
SCOPE_CHANGES: none；僅新增本交件檔並 append 本家 R26 APPROVED 戳記，未改碼、SPEC 正文或 TODO。
NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r26-codex.md
VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R25-P1-01
STATUS: DONE
## COMPOSER-R26-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂的 finding；J1 修補已閉合、v21 body 可重簽。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f` rc=0；`grep -n 'v21 更正（R25' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` → SPEC `:187`、TODO `:892`；換詞表掃描（必答 3 命令）正文無 live 三層/metadata 交付互斥；`venv/bin/python -c '…EventPipelineResult…metadata…'` → rc=1。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#755f3d53c1f3; docs/SPLITUNIFY_TODO.md#6b825499

doc-literal-only；信心度=High。J1 兩處 v21 更正與 §N／§V 同向；`M-SU-D2-01`／`02` 與 register 條數無連動問題。

---

## GROK-R26-P3-00

**斷言**: 本輪逐項核對後無 finding——`GROK-R25-P1-01` 反例已 CLOSED；另立同義詞表掃描 SPEC live（`:1-336`）與 TODO 全檔後，無與「metadata 層入殘留、本延伸只交兩層」互斥之 live 字面；`:187` 刪節未失去兩層防假綠；`M-SU-D2-01`／`02` 應紅仍指 summary；可進 `Task 9.2b`（B9C）之前提在本家側已滿足。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f`；`sed -n '187p' docs/SPLITUNIFY_SPEC.D-002.md` 含 v21「不得列入當輪」＋刪節線；`sed -n '892p' docs/SPLITUNIFY_TODO.md` 現行兩層＋舊三層刪節；同義詞 `grep -nE '…'` 之 live 互斥命中數＝0（見必答 3 表）；`sed -n '280,281p'` 之 `M-SU-D2-01`／`02` 應紅僅 summary；pytest 三節點 **3 passed**、`opposite_sides` **1 xfailed**；`EventPipelineResult` 無 `metadata` 欄。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R26-BRIEF.md#8c30ebefe12d; docs/SPLITUNIFY_SPEC.D-002.md#8603d7aa8fd7; docs/SPLITUNIFY_TODO.md#7a18de5a95ff

---


## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。
> 本收斂檔為 SPLITUNIFY b9 進入 `Task 9.2b`（批次 B9C）實作之授權依據（`gate.sh dispatch --risk high` 之 `--adversarial` 標的）。

RECONCILE-STAMP: composer APPROVED 2026-09-14 sha256:72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f task:20260911-SPLITUNIFY-B9-STAMP-R5

RECONCILE-STAMP: codex APPROVED 2026-09-14 sha256:72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f task:20260911-SPLITUNIFY-B9-STAMP-R5
RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f task:20260911-SPLITUNIFY-B9-STAMP-R5
