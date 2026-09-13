# Reconcile — 20260911-splitunify-b9-review-r22

**來源** 20260911-splitunify-b9-review-r22-codex.md, 20260911-splitunify-b9-review-r22-composer.md, 20260911-splitunify-b9-review-r22-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **F1 `SU-RESID-2` 只能標「部分關閉」**——「TODO§E將`SU-RESID-2`宣」 | P1 | CODEX-R22-P1-01 | 採納（🔴 **主委在 brief assumed 第 2 條自問「該標已關閉還是部分關閉」，該家判後者**：producer／schema 面確由 B9B 關閉，但該殘留原文寫的「複合鍵要連 `EventSplitPlan` 之**下游**一起改」，下游＝`Task 9.3` 九處消費面與 `Task 9.2b` 側別錨定，**皆未實作** ⇒ 只完成一半。TODO §E 該列改為 **部分關閉**、理由類別回 `blocked-by`，阻擋者為 `Task 9.2b` 與 `Task 9.3` 尚未實作；SPEC §N 同名條目同步改寫） |
| **F2 `Task 2.3` 之 golden 仍寫「只比 `event_id` 集合」，未標 superseded**——「TODOTask2.3仍要求golden」 | P1 | CODEX-R22-P1-02 | 採納（🔴 **主委在 brief assumed 第 1 條自問「其他舊 Task 段是否也有互斥描述」，該家掃出這一處**：`Task 9.2a` 後行粒度已升為複合鍵，只比 `event_id` 集合會**吃掉多 feature TF 維度**——mutation `M-SU-D2-16`「golden 仍以 event_id 清單比對」正是在打這一句。已標 SUPERSEDED 並指向 `Task 9.5`。🔴 **同時註明這是跨批過渡而非現行缺陷**：B9B 刻意未動 golden、凍結腳本維持單一 feature TF，故該句在單 TF 下仍成立） |
| **F3 SPEC 之 metadata 交付句與 §N 條目仍舊（同病第四次發作）**——「SPEC現行正文同時要求9A交付`met」 | P1 | CODEX-R22-P1-03 | 採納（🔴 **主委在 brief 攻擊面第 4 列自問「SPEC 是否也有同型舊段——若有即第四次」，該家證實有**：①`§P Task 9.1` 之「本延伸交付」bullet 仍含「於 `metadata.split_unify` 擴充回傳結構承載該鍵」，與**同一 Task** 已於 v18 改成「producer → summary **兩層**」的目標句互斥——v18 改了目標句與跨邊界傳遞句，**唯獨漏了這一句**；②§N 之 `SU-RESID-2` 條目仍寫「TODO 該列現仍為 `needs-research`…須於 `Task 9.1` 動工前同步」，該同步已於 B9B 完成。兩處皆已改，字面保留供追溯。SPEC 進 **v19**） |
| **F4 composer 零 findings、判可收斂**——「本輪逐項核對後無需阻擋收斂之findin」 | P3 | COMPOSER-R22-P3-00 | 採納（判 proceed） |
| **F5 grok 零 findings、E1／E2 已閉**——「本輪逐項核對後無finding；E1／E」 | P3 | GROK-R22-P3-00 | 採納（判 proceed） |

### 本輪裁定
1. **review-r21 之 E1／E2 由原提出方 CLOSED**（codex 兩條）。
2. **F1–F3 已修**；回歸 **706 passed、1 xfailed**。SPEC 進 v19，新 body sha256 為 1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7，v18 戳記失效須重簽。
3. 🔴 **本輪三條**全部是主委在 brief 裡**自標的疑慮**（assumed ×2 ＋ 攻擊面 ×1）**被逐一證實**。這已是連續第三輪如此（R18、R21、R22）⇒ **把沒把握的面寫進 brief 交出去攻，命中率極高**，應維持。
4. 🔴 **同病第四次**：「改了新段落、沒回頭標舊段落」——R19 兩次（SPEC `§P` vs `§V`）、R21 一次（TODO `Task 2.2`）、本輪兩處（SPEC metadata 句、SPEC §N 條目）＋一處（TODO `Task 2.3`）。**已改的機制**：凡改動契約面須全檔掃舊描述；**本輪起另加一條**——契約面改動之後，**下一輪 brief 必須明列「請掃 SPEC 與 TODO 的其他舊段」為必答**，不靠主委自己記得。
5. **下一步**：派 `review-r23` 做 F1–F3 閉合再驗證 ＋ 對 v19 新 body 重簽；三家確認後進 `Task 9.2b`（批次 **B9C**）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R22-P1-01
**斷言**: TODO §E 將 `SU-RESID-2` 宣稱全數關閉，但多 TF `EventSplitPlan` 下游仍在 `Task 9.3`，只能部分關閉。
**碼證**: `pattern_bridge.py:125-127` 仍 raw `set_index("event_id")` 取側別；`tables.py:372` 仍 raw `set_index("event_id")` 消費 assignments；TODO Task 9.3 仍列兩處及 named tests。
CODE-ANCHOR: momentum/Analysis/event_samples/pattern_bridge.py:125
MUTATION: 以同一 `event_id` 的兩個 `feature_timeframe` assignment 列餵入 `lab_by_id[e]`；現行 raw lookup 產生非唯一結果，未完成唯一側去重／衝突 fail-closed 便不能宣稱下游閉合。
**來源摘要**: `docs/SPLITUNIFY_TODO.md#c65295978e06`; `momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2`; `momentum/Analysis/event_samples/tables.py#843ba7f68172`。**修法/可行性**: §E 改「部分關閉／blocked-by；B9B 完成 producer/schema、assignments／purged 欄與 guards；下游待 Task 9.3，named tests＋M-SU-D2-37/40 通過前不得關閉」；Task 9.3 已具名落點與 mutation。
## CODEX-R22-P1-02
**斷言**: TODO Task 2.3 仍要求 golden 只比 `event_id` 集合，未標 superseded，與 SPEC §G 多 TF parent key 及 Task 9.5 複合鍵契約互斥。
**碼證**: TODO Task 2.3 lines 277、281-289 仍指示 event-ID diff/oracle；`freeze_splitunify_golden.py:181-187` 的 g1/g3b 實際只保存 event IDs。
CODE-ANCHOR: scripts/freeze_splitunify_golden.py:181
MUTATION: 對同一事件新增／移除一個 feature-timeframe row 而維持 `event_id`；sorted event-ID lists 不變，錯誤 TF 漏列可使 g1/g3b 綠燈。
**來源摘要**: `docs/SPLITUNIFY_TODO.md#c65295978e06`; `docs/SPLITUNIFY_SPEC.D-002.md#eb23b548de08`; `scripts/freeze_splitunify_golden.py#98358e0b8eb1`。**修法/可行性**: Task 2.3 三處加 `SUPERSEDED BY Task 9.5`，改比 `(event_id, feature_timeframe)` 或 `*_multi_tf` 平行組；單 TF v8 保留，SPEC §G 165/TODO Task 9.5 已定義落點，無需重開 9.2b 設計。
## CODEX-R22-P1-03
**斷言**: SPEC 現行正文同時要求 9A 交付 `metadata.split_unify`、又把 metadata 移入殘留；§N 的 SU-RESID-2 亦仍寫成 TODO 尚未同步，與 B9B／實際 schema 互斥。
**碼證**: SPEC §P Task 9.1 lines 185-187、§N 326/329 將 metadata 寫成交付；§V 177/257 與 TODO Task 9.1 line 463 將其移出本批；`EventPipelineResult` 只有 `summary`、`split_plan` 等欄。
CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:52
MUTATION: 依 SPEC §P 185-187 從現行 `EventPipelineResult` 讀 `result.metadata.split_unify`；dataclass 沒有 `metadata` 欄，執行時失敗。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#eb23b548de08`; `docs/SPLITUNIFY_TODO.md#c65295978e06`; `momentum/Analysis/event_samples/pipeline.py#83011e0913c7`。**修法/可行性**: §P/§N 統一 producer→`EventSplitPlan.summary`，metadata/終端可見性留 SU-RESID-9A-UI，SU-RESID-2 改 B9B producer/schema 完成、下游待 Task 9.3；現行 dataclass/TODO line 463 已提供一致落點。
(1a/1b) `CODEX-R21-P1-01=CLOSED`：`venv/bin/python -m pytest -rxX --runxfail tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed` → rc=1、`DID NOT RAISE AlignmentViolationError`；正常命令 → `1 xfailed`。`CODEX-R21-P1-02=CLOSED`：Task 2.2 三處均 SUPERSEDED／16-key 指向；scoped pytest → `105 passed, 1 xfailed`。 (2a/2b) 其他互斥僅 Task 2.3 G-3a/G-3b/G-5②；貼入 `SUPERSEDED BY Task 9.5：多 TF golden 以 (event_id, feature_timeframe) 或 *_multi_tf 平行組，比對 event_id-only 僅保留單 TF 舊錨。`
(3a/3b) `SU-RESID-2` 判「部分關閉、餘下 Task 9.3」，可貼入字面見 P1-01。 (4a) 阻擋段為 §P 185-187、§N 326、§N 329；§P Task 9.2 line 196 的 unconditional `str(selected_timeframe)` 是 stale snapshot，但 199-201 已修正且現行 code conditional，non-blocking doc-literal-only。
(4b) §P/§N 統一 producer→summary、metadata 留 SU-RESID-9A-UI、§N SU-RESID-2 改 partial/Task 9.3 pending（P1-03）。(5a/5b) 不可進 B9C；最小集合=`CODEX-R22-P1-01,CODEX-R22-P1-02,CODEX-R22-P1-03`；不重開 9.2b–9.5 設計，保留 xfail。
§0/§1/§2/§3/必要性：上述三條否證未驗證假設；矛盾三條 P1，漏項為 Task 9.3 下游與多 TF golden，測試可測性現有 xfail/回歸足夠但下游 named tests 待做；quant、OOM、cache、API/型別與不必要工作無新增 finding。
ASSUMPTIONS_VERIFIED: R21 兩條修補、RECONCILE-STAMP v18 rc=0、`--runxfail` 確為 `DID NOT RAISE`、scoped regression `105 passed/1 xfailed`。
TESTS_RUN: normal target=`1 xfailed` rc=0；`--runxfail` rc=1 expected；two-file pytest rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0。FAILURES_SEEN: 僅預期紅燈 `DID NOT RAISE AlignmentViolationError`。
SCOPE_CHANGES: 僅新增本 review artifact，未改 code、SPEC、TODO、HISTORY、data_cache。 NUMERIC_OR_SCHEMA_IMPACT: 未改數值／schema／檔案大小。 OUTPUT_PATH: `handoffs/20260911-splitunify-b9-review-r22-codex.md`
VERDICT: blocked
BLOCKED-BY: CODEX-R22-P1-01,CODEX-R22-P1-02,CODEX-R22-P1-03
CLOSED: CODEX-R21-P1-01,CODEX-R21-P1-02
STATUS: DONE
## COMPOSER-R22-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂之 finding；E1／E2 修補已閉合，可進 `Task 9.2b`。

**碼證**: `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 xfailed** rc=0；`venv/bin/python -m pytest --runxfail "…::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 failed**，`DID NOT RAISE AlignmentViolationError`；六路 `-rxX`（`test_splitunify_derive.py`＋`event_samples/`＋`test_splitunify_golden.py`＋`test_splitunify_contract.py`＋`test_splitunify_disclosure.py`＋`test_splitunify_event_study_only.py`）→ **706 passed, 1 xfailed** rc=0；`grep -n SUPERSEDED docs/SPLITUNIFY_TODO.md` → :225/:242/:265。

**來源摘要**: docs/SPLITUNIFY_TODO.md#2ba9ad37

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R20-P1-01,COMPOSER-R20-P2-01

ASSUMPTIONS_VERIFIED: xfail 1 xfailed；--runxfail DID NOT RAISE AlignmentViolationError；706+1xfail 六路回歸；Task 2.2 三處 SUPERSEDED；舊 Task 段無 B9B 互斥；SU-RESID-2 已關閉成立；SPEC 無阻擋雙真相
TESTS_RUN: `pytest -rxX …::test_multi_feature_tf_opposite_sides_must_fail_closed` → 1 xfailed；`pytest --runxfail …` → 1 failed DID NOT RAISE；六路 `pytest -q -rxX`（六檔）→ 706 passed 1 xfailed；`pytest -q …::test_multi_symbol_branch_summary_counts_are_named` → 1 passed
FAILURES_SEEN: none（review-only；--runxfail 預期失敗）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r22-composer.md

STATUS: DONE
## GROK-R22-P3-00

**斷言**: 本輪逐項核對後無 finding；E1／E2 修補成立，本家 R21 無實質反例可 CLOSED，可進 Task 9.2b（B9C）。

**碼證**: `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 xfailed**；同命令加 `--runxfail` → **FAILED DID NOT RAISE AlignmentViolationError**（非他錯）；`contracts.py:933` 類存在；Task 2.2 三處 SUPERSEDED；舊 Task 2.1／2.3／3.1–3.3／4.1 掃無未標 B9B 互斥；`SU-RESID-2` 依 D-002 範圍維持已關閉；SPEC §P／§N 過期字面具名但不阻；scoped 四節點 → **3 passed, 1 xfailed**。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R22-BRIEF.md#fc626dbb3031

[P3] 信心度=High。閉合輪 sentinel；E1／E2 由實跑＋全文掃核對。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: E1 xfail 仍 1 xfailed 且 --runxfail=DID NOT RAISE AlignmentViolationError；E2 Task 2.2 SUPERSEDED 三處；舊 Task 2.1–4.1 無未標 B9B 互斥；SU-RESID-2 已關閉範圍正確（9.3 另列）；SPEC 過期字面非阻；可進 B9C
TESTS_RUN: `pytest -rxX …::test_multi_feature_tf_opposite_sides_must_fail_closed` → 1 xfailed；`--runxfail` → DID NOT RAISE AlignmentViolationError；scoped 四節點 → 3 passed, 1 xfailed
FAILURES_SEEN: none（--runxfail 預期失敗）
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r22-grok.md

STATUS: DONE
