# Reconcile — 20260911-splitunify-b9-review-r19

**來源** 20260911-splitunify-b9-review-r19-codex.md, 20260911-splitunify-b9-review-r19-composer.md, 20260911-splitunify-b9-review-r19-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **B1 SPEC 之 `§P Task 9.1` 落後於自己的 §V 與實作（兩處互斥字面）**——「SPEC現行§PTask9.1仍要求多s」 | P1 | CODEX-R19-P1-01 | 採納（🔴 **這是「SPEC 落後於自己的 §V 與實作」的第一個實例**，主委複驗兩處皆成立：①`§P Task 9.1` 仍寫「producer → summary → `metadata.split_unify` **三層**完整記帳」，而 v13 之 O1 早已把 metadata 層移入 §N 殘留、§V 亦同步——**只有 §P 這一段沒改**；②仍寫「多 symbol 時**逐 symbol 相加**」，而 R18 三家撞題並實跑證實照字面相加會按 symbol 放大，TODO／實作／測試皆已定案為原樣傳遞。**SPEC 是權威** ⇒ 下一輪實作者依 §P 會引入 double-count 或錯把 metadata 當本批交付。兩處已同步至現況並逐字註明原文；SPEC 進 **v18**，v17 之三家戳記因 body 變更而失效、須重簽） |
| **B2 composer 零 findings、判可收斂**——「本輪逐項核對後無需阻擋收斂之findin」 | P3 | COMPOSER-R19-P3-00 | 採納（該家 CLOSED 自提之 `COMPOSER-R18-P2-01`／`P2-02`／`P3-01` 三條，判 proceed） |
| **B3 grok 零 findings、五條自提全 CLOSED**——「本輪逐項核對後無finding；本家R1」 | P3 | GROK-R19-P3-00 | 採納（該家 CLOSED 自提之 `GROK-R18-P1-01`／`P2-01`／`P2-02`／`P3-01`／`P3-02` 五條，判 proceed） |

### 本輪裁定
1. 🔴 **review-r18 之十三條 finding 全數由原提出方 CLOSED**（codex 五、composer 三、grok 五；章程 §B8 之閉合再驗證已滿足）。
2. **主委在 brief 自標的兩條 assumed 皆由 codex 實跑否證為「無問題」**：①`Categorical`／`StringDtype` 下 `discarded` **不會**混入值為 0 之偽項（unordered／ordered Categorical 與 StringDtype 皆得 `{'4h': 1}`；`Categorical` 含 `pd.NA` 則走本輪新加的缺值 fail-closed）；②**無第二條生產路徑**——全 repo 掃 `build_event_keys` 呼叫點只有 `pipeline.py` 一處，另三處在 `scripts/freeze_splitunify_golden.py` 屬 golden 工具、非 runtime caller。
3. **B1 已修**（SPEC 進 v18，新 body sha256 為 76006a764a8c1d12437cc71c8ed38bbdaddbc65637a523cd52792d2ee3ef9433，須重簽）。
4. **下一步**：對新 body 取三家 APPROVED、`reconcile_stamps_check` rc=0 後，進 `Task 9.2`（批次 **B9B**＝`9.2`＋`9.2a`，**不得拆批**）。

### 🔴 本輪最值得記的一件事
v13 那次把 `metadata.split_unify` 移入殘留時，**改了 §V 卻沒改 §P**——與本檔一路在打的「一個決定散在多區段而漏同步」**完全同型**，只是這次隔了五輪、直到實作完成才被逼出來。⇒ **文件層的自證掃描抓不到「§P 與 §V 互斥」這種跨區段矛盾，實作才抓得到**；這也反證 r12 停輪判準當時「殘餘規格缺陷交由實作期 pytest 暴露」之判斷是對的。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R19-P1-01
**斷言**: SPEC 現行 §P Task 9.1 仍要求多 symbol 相加與 `metadata.split_unify` 三層交付，但 TODO、程式與測試已定案為批次字典原樣傳遞、producer→summary 兩層，契約仍互相矛盾。
**碼證**: VERIFY: `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '176,186p'` 顯示舊字面；`nl -ba docs/SPLITUNIFY_TODO.md | sed -n '438,457p'` 顯示新字面；94-test 與 multi-symbol assertion 均通過。
CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:754
MUTATION: 暫存副本把 `split_projection.py:693-696` 的 forwarding 改為按 symbol 對同一字典加總，重跑 `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py::test_multi_symbol_branch_carries_discarded_rows_verbatim` 應紅。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#8c40a92f3556
[BLOCKING] 信心度=High；SPEC 是權威來源，下一輪實作者可依 §P 引入 double-count 或錯把 metadata 當本批交付。最小修法是把 SPEC 現行 §P Task 9.1 同步至 TODO／現行 code，保留 metadata 為 §N 殘留；可行性由上述 94 passed、multi-symbol 值相等與防放大測試證明。
1a: `CODEX-R18-P1-01`、`P1-02`、`P1-03`、`P2-01`、`P3-02` 全部 CLOSED。
1b: `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → rc=0；A/B/C/D 分別 NO_RAISE、RAISED、NO_RAISE、RAISED，C=`discarded={'4h': 2}`。指定 pytest → 94 passed。r18 的 Wiring、NaN、Mapping、防 stale docstring 反例均由此重跑閉合。
2a: 無第二條 production path；全 repo 呼叫掃描只有 `pipeline.py:750`，另三處為 `scripts/freeze_splitunify_golden.py:163,252,268` 的 golden 工具，不是 runtime caller。
2b: N/A；無第二 production path 阻擋。工具路徑不接 `build_event_keys` producer，optional discarded 預設 `{}` 不改本輪契約。
3a: 不會混入值 0 偽項。`venv/bin/python /tmp/splitunify_r19_categorical_probe.py` → unordered/ordered Categorical 均 `{'4h': 1}`，StringDtype `{'4h': 1}`，Categorical `pd.NA` → ValueError 缺值。
3b: 最小修法不需要；已試 Categorical ordered=False/True（含未使用 `12h`）、StringDtype，並以既有 object/None 測試確認缺值 fail-closed。
4a: 不能進 B9B；唯一 blocking 是 SPEC §P 與 TODO/code 的契約漂移，不是程式行為或測試缺口。
4b: 最小閉合集合：同步 SPEC 現行 Task 9.1 的 multi-symbol 原樣傳遞、兩層交付字面；不重開 9.2–9.5。
ASSUMPTIONS_VERIFIED: SPEC stamp check rc=0；runtime caller 掃描、Categorical 邊界、兩種 TF 順序均實跑；順序探針兩次均 `discarded={'4h': 4}`。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 94 passed/0 failed/rc=0；probe rc=0；Categorical probe rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0。
FAILURES_SEEN: none in closure checks；新增 finding 是現行 SPEC/TODO 字面衝突。
SCOPE_CHANGES: none；只新增本交件檔，未改 production code、測試、SPEC、TODO、HANDOFF.md 或 data_cache/。
NUMERIC_OR_SCHEMA_IMPACT: 審查未改輸出；確認現行 discarded tuple、13-key summary 與 batch-level verbatim semantics。
OUTPUT_ARTIFACT: handoffs/20260911-splitunify-b9-review-r19-codex.md
VERDICT: blocked
BLOCKED-BY: CODEX-R19-P1-01
CLOSED: CODEX-R18-P1-01,CODEX-R18-P1-02,CODEX-R18-P1-03,CODEX-R18-P2-01,CODEX-R18-P3-02
## COMPOSER-R19-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂之 finding；本家 R18 三條反例均已 CLOSED，brief 兩條 assumed（Categorical 零值偽項、雙 TF wiring）經實跑不成立。

**碼證**: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → **94 passed** rc=0；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → 四案 A/B/C/D 如 FACT-RECEIPT；`/tmp/r19-composer-verify.py` → Categorical／object／str 無 `zero_keys`、NaN fail-closed；`rg -n 'derive_event_split_from_plans' momentum/ --glob '*.py'` → 生產僅 `pipeline.py:750`。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R19-BRIEF.md#7943abe3b5a7

[P3] 信心度=High。閉合輪 sentinel；六群修補已由本家原反例重跑驗證。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R18-P2-01,COMPOSER-R18-P2-02,COMPOSER-R18-P3-01

ASSUMPTIONS_VERIFIED: 94 passed；探針四案；Categorical/object/str 三 dtype；NaN fail-closed；雙 mutation 轉紅；derive 生產單呼叫點；SPEC「相加」字面漂移已具名
TESTS_RUN: `pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 94 passed；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0；`/tmp/r19-composer-verify.py` rc=0；multi-symbol／pipeline wiring mutation 各 1 failed（已還原）
FAILURES_SEEN: none（mutation 預期失敗已還原）
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r19-composer.md

STATUS: DONE
## GROK-R19-P3-00

**斷言**: 本輪逐項核對後無 finding；本家 R18 五條反例均 CLOSED，brief 兩條 assumed（Categorical 零值偽項、雙 TF／順序影響 wiring）經實跑不成立，可進 B9B。

**碼證**: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → **94 passed** rc=0；省略 `pipeline.py:754` discarded kwarg ⇒ wiring **1 failed**（已還原）；Mapping 改傳 `{}` ⇒ multi-symbol **1 failed**（已還原）；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → A/B/C/D 四案且 C 之 `discarded={'4h': 2}`；`/tmp/r19-grok-workdir/probe_categorical.py` → Categorical 無零值鍵、NaN fail-closed；TF 順序兩向皆 `discarded={'4h': 4}`；`grep -rn 'build_event_keys\|derive_event_split_from_plans' momentum api --include='*.py'` → 生產僅 `pipeline.py:747`／`:750`。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R19-BRIEF.md#7943abe3b5a7

[P3] 信心度=High。閉合輪 sentinel；六群修補由本家原反例重跑驗證。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R18-P1-01,GROK-R18-P2-01,GROK-R18-P2-02,GROK-R18-P3-01,GROK-R18-P3-02

ASSUMPTIONS_VERIFIED: 94 passed；P1-01／P2-02 mutation 轉紅後還原；探針四案；Categorical／object／string+NA；TF 順序兩向；生產呼叫點單一；SPEC「相加」漂移具名但不阻
TESTS_RUN: `pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 94 passed；`pytest …::test_splitunify_wiring_discarded_rows_reaches_summary` 於 pipeline mutation 下 1 failed／還原後 1 passed；`pytest …::test_multi_symbol_branch_carries_discarded_rows_verbatim` 於 Mapping `{}` mutation 下 1 failed／還原後 1 passed；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0；categorical／TF-order 探針 rc=0
FAILURES_SEEN: none（mutation 預期失敗已還原；`git status` 生產檔乾淨）
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r19-grok.md

STATUS: DONE
