# Reconcile — 20260911-splitunify-b9-review-r20

**來源** 20260911-splitunify-b9-review-r20-codex.md, 20260911-splitunify-b9-review-r20-composer.md, 20260911-splitunify-b9-review-r20-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_TODO.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **D1 `Task 9.2a` 機械驗收第 6 條之逐字錨點測試整段缺席（三家撞題、三家皆 BLOCKING）**——「`Task9.2a`要求的`test_m」「`Task9.2a`機械驗收第6條要求之」「`Task9.2a`明文要求之機械驗收錨」 | P1 | CODEX-R20-P1-01, COMPOSER-R20-P1-01, GROK-R20-P1-01 | 採納（🔴 **主委真漏**：`test_multi_feature_tf_opposite_sides_must_fail_closed` 在 consult-r2 裁定「整批 REVERT」時隨偷跑碼一起消失，而 `Task 9.2a` 實作時**沒補回**——grok 實跑該條驗收命令得零筆收集，等同「刪測換綠」，且使 `Task 9.2b` **失去可解除之 xfail 標的**。修法：依 consult-r2 之三重問題裁定重建該測試——①fixture 改用**事件級** manifest（9.2a 之責）；②③之異側 fail-closed 屬 9.2b ⇒ 以 `xfail(strict=True)` 明示、**不得** `--deselect` 藏起來。**主委實跑 TODO 第 6 條逐字命令**：以 `-rxX` 對該 node id 實跑 ⇒ 輸出 `1 xfailed`，符合驗收判準） |
| **D2 多 symbol 分支之三個計數無具名測試（三家撞題）**——「多symbolMapping分支的`n_」「多symbol（Mapping）分支之`」 | P2 | CODEX-R20-P2-01, COMPOSER-R20-P2-01, GROK-R20-P2-01 | 採納（grok 實證「省略該分支三 kwargs 後 summary 靜默變 0 且 scoped 回歸仍全綠」。修法：新增 `test_multi_symbol_branch_summary_counts_are_named`，逐值斷言三鍵並**明文擋 0 值**（0 正是三個 kwargs 被省略時的樣子）。**主委實跑驗鑑別力**：刪掉多 symbol 分支之三個 kwargs ⇒ 該測試轉紅，還原後綠） |

### 本輪裁定
1. **D1／D2 已修**；回歸 **706 passed、1 xfailed**（該 xfail 為設計上的——`Task 9.2b` 完成時解除，屬 `Task 9.2a` 條文明定之狀態，非未處理之紅）。
2. 🔴 **D1 之根因值得記**：`Task 9.1` 的 A4（探針檔沒跟著改）與本輪 D1（xfail 錨點測試沒補回）**是同一個根因的兩次發作**——consult-r2 的「整批 REVERT」把東西一起還原了，而後續前進時**沒有逐項檢查「回退掉的哪些東西需要重建」**。⇒ 日後凡執行整批回退，須同時產出「回退清單 vs 前進時需重建清單」之對照，不能只記得改主體。
3. **下一步**：派 `review-r21` 做 D1／D2 閉合再驗證；三家確認後進 `Task 9.2b`（批次 **B9C**）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R20-P1-01

**斷言**: `Task 9.2a` 要求的 `test_multi_feature_tf_opposite_sides_must_fail_closed`（`xfail(strict=True)`）未存在；因此異側／混態的機械驗收可被刪除或從未加入而不會讓測試失敗。

**碼證**: `docs/SPLITUNIFY_TODO.md:539-542` 明定逐字 node id 與 `1 xfailed`；`rg -n 'test_multi_feature_tf_opposite_sides_must_fail_closed' tests` 無命中；`venv/bin/python -m pytest -rxX 'tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed'` → collected 0 items、`no tests ran`、rc=4。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:539
MUTATION: 從 `tests/momentum/Analysis/test_splitunify_derive.py` 移除或不加入該測試函式，再執行指定 node；現況已重現 `no tests ran` rc=4。

**來源摘要**: docs/SPLITUNIFY_TODO.md#3761a7b4a8ac

[P1] 信心度=High。這是驗收閘缺失，不是把尚未實作的 `Task 9.2b` 行為誤判成 B9B 缺陷；混態本身已由 TODO 明列為 9.2b 過渡行為。**修法**：新增同名測試，以事件級 manifest、兩個 feature TF 且不同 cutoff 的 fixture，`@pytest.mark.xfail(strict=True, reason="Task 9.2b: event-level anchor + AlignmentViolationError")`，預期目前版本 xfailed，9.2b 完成後解除 xfail。**可行性證據**：mixed-cutoff probe 已實跑 `rc=0`，輸出同一 `event_id` 的 `1h` 為 `purged`、`4h` 為 `train` assignment；故反例可穩定構造，測試不是空殼。

## CODEX-R20-P2-01

**斷言**: 多 symbol Mapping 分支的 `n_events`、`n_event_tf_rows`、`n_event_tf_rows_purged` 沒有具名測試；三個 summary 值可在直接相關測試全綠時退化。

**碼證**: `momentum/Analysis/event_samples/split_projection.py:767-770` 是多 symbol 三鍵的唯一組裝點；現有 `tests/momentum/Analysis/test_splitunify_derive.py:1451-1474` 只驗 discarded 傳遞，`1573-1581` 的三鍵測試只走單 symbol；runtime mutant 將多 symbol 三鍵置零後，兩個直接相關 test files 仍 `104 passed` rc=0。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#bd27c2f92a20

[P2] 信心度=High；production 計算本輪 probe 正確，問題是覆蓋缺口。**修法**：新增 `test_multi_symbol_summary_has_n_events_and_n_event_tf_rows`，用兩 symbol、每事件兩 feature TF、至少一 symbol 的空 purge 子批，斷言 `n_events == keys.event_id.nunique()`、`n_event_tf_rows == len(keys)`、`n_event_tf_rows_purged == len(plan.purged)`，並驗 `feature_timeframe` 欄集。

### §0 被當成事實的假設核對

brief 的 mixed-cutoff「不會混態」假設已被反例推翻，但依 TODO 屬 `Task 9.2b`，不在本批重開；多 symbol 三計數與空 purge concat 已實跑確認（`5 events / 10 TF rows / 2 purged rows`）；brief 所載六路回歸 `705 passed` 本輪視為既有 receipt，未重跑，另有本輪直接相關基線 `104 passed`。

### §1 必查（11 類）

1 矛盾/互斥：無；2 漏項/端到端：P1-01、P2-01；3 不可測驗收：P1-01；4 quant 假設：無；5 過度工程：無；6 OOM/並行：無；7 cache：無；8 API/型別/相容：無；9 測試品質：P1-01、P2-01；10 Agent 可執行性：P1-01 使指定 node 不可執行；11 必要性/短命工：無。

### §2 範本錨點與空殼

現行 `Task 9.2`／`9.2a` 的欄位、驗證命令、golden 與存活／覆蓋風險均有實質內容；P1 finding 的 anchor 位於現行 TODO 段，不在 HISTORY 區；無新增 quant、cache、OOM 或 schema 數值變更。

### 必答

1a. **會混態**：不同 cutoff 的多 TF probe → `mixed_cutoff_rc=0`、同一事件 `1h=purged`、`4h=train assignment`。1b. **屬 `Task 9.2b`**：TODO 9.2b 明定事件級 `decision_at_ms` 錨定與異側 fail-closed；本批不加第二份判側邏輯，但必須先補 P1-01 的 xfail 機械閘。

2a. **正確**：多 symbol probe → `summary_counts={'n_events': 5, 'n_event_tf_rows': 10, 'n_event_tf_rows_purged': 2}`；purged 欄為 `event_id/reason/feature_timeframe`，其中一個 symbol 子批為空仍正確 concat。2b. **該補**：`test_multi_symbol_summary_has_n_events_and_n_event_tf_rows`，斷言上述三鍵分別等於 `event_id.nunique()`、`len(event_keys)`、`len(purged)`。

3a. production 只有 `split_projection.py:259-360` producer（輸出 `feature_timeframe`）、`pipeline.py:756-759` caller（不自行建表）；golden `scripts/freeze_splitunify_golden.py:108-111` 與測試 helper `tests/momentum/Analysis/test_splitunify_derive.py:116-140` 已含欄。另掃到歷史 negative-injection helper `handoffs/20260911-probe-splitunify-negative-injection.py:48-53` 未含欄；它未被 production/API 引用，`handoffs/20260911-splitunify-b9-probe-multitf.py` 只建 `per_tf` 並呼叫 producer。3b. **不阻擋**：歷史探針若要重用需另行更新，非本輪 current production constructor。

4a. **逐值未變**：`git show 9e87386f^:tests/golden/splitunify/splitunify_golden.json | cmp -s - tests/golden/splitunify/splitunify_golden.json` → rc=0；`jq -S` sorted JSON compare → rc=0；頂層 11 鍵為 `_doc g1_membership g3b_oracle g4_per_symbol_n g5_answer_window g5_row_fingerprint_first_ms g5_row_fingerprint_last_ms g5_row_fingerprint_n g5_row_fingerprint_positions g5_row_fingerprint_sha256 purge_reasons`。4b. **無變動鍵**。

5a. **會 raise**：selected `1h`、未選中 `4h` 的 `timeframe=NaN` probe → rc=1，錯誤為 `build_event_keys: per_tf 之 timeframe 欄有缺值 ... fail-closed`。5b. **預期**：`split_projection.py:298-304` 明定提前到全欄，避免全量模式或 discarded summary 產生假 TF；不修。

6a. **有第六種**：缺失的 strict-xfail node 是可讓異側驗收失效而現有 suite 綠的獨立破壞；直接相關兩檔 runtime mutant 亦以多 symbol 三鍵全置零後 `104 passed` rc=0（P2-01）。6b. **先修 P1-01 再進 `Task 9.2b`**；混態行為本身留給 9.2b，測試錨點不可缺席。

ASSUMPTIONS_VERIFIED: mixed cutoff、multi-symbol 三計數／空子批、NaN 全欄 fail-closed、golden 11 鍵逐值、constructors 掃描、strict-xfail node 缺失均附本檔命令或輸出摘要；705 passed 僅引用 brief receipt。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 104 passed rc=0；缺失 xfail node → no tests ran rc=4；mixed/multi-symbol/NaN runtime probes；golden `cmp` 與 sorted JSON compare 均 rc=0。
FAILURES_SEEN: 初次 probe 誤讀測試 helper 名稱而 ImportError（未改檔），改用 inline receipts 後完成；`scripts/restore_golden_inventory.sh` 因受限環境無法建立 `.git/index.lock`，rc=128，未改 production code。
SCOPE_CHANGES: 僅新增本交件檔；未改程式、SPEC、TODO、data_cache；歷史 handoff constructor 僅列為非阻擋觀察。
NUMERIC_OR_SCHEMA_IMPACT: 未修改數值、schema、golden 或輸出檔；review 僅指出缺失測試與必要測試覆蓋。
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r20-codex.md

VERDICT: blocked
BLOCKED-BY: CODEX-R20-P1-01
CLOSED:
## COMPOSER-R20-P1-01

**斷言**: `Task 9.2a` 機械驗收第 6 條要求之 `test_multi_feature_tf_opposite_sides_must_fail_closed`（`xfail(strict=True)`）未存在，使 opposite-side／混態回歸可被刪除而全套仍綠。

**碼證**: `docs/SPLITUNIFY_TODO.md:539-542` 逐字要求 node id 與 `1 xfailed`；`rg -n test_multi_feature_tf_opposite_sides tests/` → 0；`venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → `no tests ran`。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:539
MUTATION: 刪除（或從未添加）該測試函式 → 現行 `pytest -q tests/momentum/Analysis/test_splitunify_derive.py` 仍 **全綠**（已實測 705 含 derive 子集）

**來源摘要**: docs/SPLITUNIFY_TODO.md#3761a7b4a8ac

[P1] 信心度=High。TODO 明文「缺此則刪掉該測試也不會紅」——本輪實證為真。

**修法**: 在 `test_splitunify_derive.py` 新增該測試：fixture 用事件級 `_manifest`（① 已修）、兩 feature TF 不同 `feature_cutoff_ms` 構造異側；`@pytest.mark.xfail(strict=True, reason="Task 9.2b: event-level anchor + AlignmentViolationError")`；預期現行碼不 raise ⇒ xfailed。

**可行性**: 依 probe1／probe1b 反例可穩定構造；`pytest -rxX` 應輸出 `1 xfailed` 後 derive 全套仍 rc=0。

---

## COMPOSER-R20-P2-01

**斷言**: 多 symbol（Mapping）分支之 `n_events`／`n_event_tf_rows`／`n_event_tf_rows_purged` 無具名測試，子批計數錯誤可靜默過 705 綠。

**碼證**: `split_projection.py:767-770` 三鍵以整批 `event_keys` 計算；`/tmp/r20-composer-verify.py` probe2 `counts_match=true`；`rg test_multi_symbol.*n_event_tf tests/` → 0；僅 `test_summary_has_n_events_and_n_event_tf_rows` 走單標的 `_multi_feature_tf_case`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#bd27c2f92a20

[P2] 信心度=High。計數邏輯本輪探針正確，缺口在測試覆蓋。

**修法**: 新增 `test_multi_symbol_summary_has_n_events_and_n_event_tf_rows`：`_interleaved_case`＋雙 TF 擴展，斷言三鍵與 `len(purged)`、`n_symbols==2`。

---

## GROK-R20-P1-01

**斷言**: `Task 9.2a` 明文要求之機械驗收錨點 `tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed`（`xfail(strict=True)`）在測試樹中**整段缺席**，TODO 第 6 條驗收命令得到 `ERROR: not found`／`collected 0`，等同「刪測換綠」且使 `Task 9.2b` 失去可解除之 xfail 標的。

**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:556  
MUTATION: 維持該 node id 缺席（現況＝已發生之破壞）後執行 `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → rc=4、`ERROR: not found`、`collected 0 items`（TODO 原文：此結果＝**不通過**；須為 `1 xfailed`）。對照：`grep -n 'opposite_sides_must_fail' tests/momentum/Analysis/test_splitunify_derive.py` → 0 命中；同檔已有 `_multi_feature_tf_case`／複合鍵測試，惟無此 xfail 殼。

**來源摘要**: docs/SPLITUNIFY_TODO.md#3761a7b4a8ac

[P1] 信心度=High。會怎麼失敗：B9B 看似 705 全綠，但 TODO 自訂之第 6 條閘永遠過不了；9.2b 寫「解除 xfail」時找不到標的，混態契約失去嚴格失敗錨。  
**修法**：在 `tests/momentum/Analysis/test_splitunify_derive.py` **新增**（非改名藏舊）`test_multi_feature_tf_opposite_sides_must_fail_closed`，`@pytest.mark.xfail(strict=True, reason="Task 9.2b: 異側 fail-closed 尚未實作")`；fixture 修 9.2a 要點①（manifest 事件級去重，不得把同 `event_id` 兩列寫進 `manifest.table`）；斷言期望現行碼在不同 cutoff 混態下**尚未** raise `AlignmentViolationError`（故 xfail 等待 9.2b）。  
**可行性證據**：本家 Q1 已實跑出跨表／異標混態，故「預期仍紅／xfail」之行為前提成立；TODO:540-542 已寫死 node id 與驗收字面；`pytest.mark.xfail(strict=True)` 為專案既有模式。驗收：同上第 6 條命令須出現 `1 xfailed`（不得 `1 passed`／`no tests ran`）。

---

## GROK-R20-P2-01

**斷言**: 多 symbol（Mapping）分支之 `n_events`／`n_event_tf_rows`／`n_event_tf_rows_purged` 無具名測試；省略該分支三 kwargs 後 summary 靜默變 0 且 scoped 回歸仍全綠。

**碼證**: `split_projection.py:768-770`（多 symbol `_build_summary` 傳入三計數）；`_build_summary` 以 `int(n_events or 0)` 吞掉缺省（:860-862）。MUTATION 實跑：刪 :767-770 三行 kwargs → `derive` Mapping 路徑 summary `{n_events:0,n_event_tf_rows:0,n_event_tf_rows_purged:0}`（真值 6/6/0 於 interleaved）；`pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → **104 passed**。單標的 `test_summary_has_n_events_and_n_event_tf_rows` 抓不到此分支。已還原，`git diff` 生產檔空白。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#bd27c2f92a20

[P2] 信心度=High。行為現況正確（本家反例值相符），缺的是鑑別力。  
**修法**：新增 `test_multi_symbol_branch_summary_event_and_tf_row_counts`（多 symbol＋多 feature TF fixture；三鍵值相等斷言）。不阻 9.2b 邏輯，建議與 P1 同批補。

---

VERDICT: blocked
BLOCKED-BY: GROK-R20-P1-01
CLOSED:

ASSUMPTIONS_VERIFIED: 不同 cutoff 三變體皆可混態（屬 9.2b）；多 symbol 三計數值正確但缺測且 omit-kwargs 全綠；生產／golden／測試 helper 之 event_keys 皆含 feature_timeframe；golden 11 鍵逐值未變；NaN 在未選側單選 raise＝R18 同行為（預期）；TODO 第 6 條 xfail node 缺席致驗收 fail
TESTS_RUN: `venv/bin/python /tmp/r20-grok-workdir/probe_r20.py` → q1.any_mixed=true、q2.match=true；NaN 四案（含 pd.NA）→ 三缺值 RAISE／clean OK；`pytest -rxX …::test_multi_feature_tf_opposite_sides_must_fail_closed` → ERROR not found rc=4；omit-counts mutation → 104 passed 後已還原；scoped `test_splitunify_derive.py`＋`test_splitunify_wiring.py` → **104 passed** rc=0；`git diff` split_projection 空白
FAILURES_SEEN: 初版探針誤傳 `AlignmentReceipts(failures=…)`（已改）；非產品缺陷
SCOPE_CHANGES: none（唯讀審碼）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r20-grok.md
