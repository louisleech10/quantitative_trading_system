# Reconcile — 20260911-splitunify-b9-review-r24

**來源** 20260911-splitunify-b9-review-r24-codex.md　|　**roster** codex

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **H1 metadata 層之舊字面散落六處未同步（同型第五次）**——「Task9.1目標句與§V已限定prod」 | P1 | CODEX-R24-P1-01 | 採納（🔴 **該家逐段掃出六處，其中五處是 v18／v19 兩次同步都漏掉的**：①`M-SU-D2-03` 應紅欄仍指 `Task 9.1` 之 metadata 值相等斷言與 `tests/api/test_splitunify_disclosure.py` exact-key 斷言，而 §V 早已把這兩條移出當輪 ⇒ **空殼 mutation**；②`§P` 之「鎖定三層…不得由實作者自選」仍是祈使句；③`§P` 獨立回退判準寫「移除上述三層」；④§V `Task 9.1` 尾句寫「移除上述三層後…」；⑤§R 回退句寫「移除三層揭露即可」；⑥`SU-RESID-9A-UI` 條目**自身**括號把 `metadata.split_unify` 列為「本延伸交付」——該條目正是把此層移出交付的那一條。全部改為**兩層**、原字面刪節線保留；`M-SU-D2-03` 整列改標「殘留期間無應紅測試、理由類別 `blocked-by`」，判準與 `C5-28` 一致。主委另補：**v19 的沿革條目當時漏寫**，本輪一併補上。SPEC 進 **v20**） |
| **H2 殘留同段兩個數字（19 vs 20）**——「TODO§E`SU-RESID-C5-T」 | P2 | CODEX-R24-P2-02 | 採納（`docs/SPLITUNIFY_TODO.md` §E 之 `SU-RESID-C5-TARGETS` 同段同時寫「缺錨 **19** 列」與「要動 **20** 列已戳記之 register」，已改 19。🔴 `C5-25` 補錨這**一個動作**至此**第三度**打翻同一個數字——前兩次在驗收第 5 點與殘留首句） |

### 本輪裁定

1. **r22 三條由原提出方全數 CLOSED**（`CODEX-R22-P1-01`／`P1-02`／`P1-03`），章程 §B8 至此滿足。
2. 🔴 **Rule 12 爭議已關**：該家 (0a) 逐字接受以 `brief-kind` 封閉集合判適用範圍，(0b) 明示不需否證、`reconcile_stamps_check` rc=1 不再是拒審理由。r23 之 G1 駁回成立。
3. **兩條新 finding 全採納並修完**；回歸六路 **706 passed、1 xfailed**；兩份 `doc_format_precheck` rc=0。
4. 🔴 **本輪最值得記的程序事實**：r23 之固定必答第 3 條（契約面改動後強制掃 SPEC 與 TODO 其他舊段）**composer 與 grok 皆答「無」**，該家於本輪逐段掃出**六處** ⇒ **強制掃描機制有效，但只在受派方真的逐段執行時有效**；**三家同答「無」不足以當作「確實沒有」**。此條與「不得以『三家零 finding』當停輪依據」同源。
5. **SPEC 進 v20**，新 body sha256 為 c12382d397d96beb732e9514a6cb540519a7833c3921cd5d4bcfab66e1dfad05 ⇒ v19 之三枚戳記（composer／grok APPROVED、codex REJECTED）全數失效，須重簽。
6. **下一步**：派 `review-r25` 做 H1／H2 閉合再驗證 ＋ 對 v20 新 body 三家重簽；齊備後進 `Task 9.2b`（批次 B9C）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R24-P1-01
**斷言**: Task 9.1 目標句與 §V 已限定 producer → `EventSplitPlan.summary` 兩層，但 live mutation `M-SU-D2-03` 仍要求 metadata 值相等／exact-key，§P 同段仍要求 producer→metadata handoff；這會指示實作者交付現行入口無法產出的欄位。
**碼證**: `EventPipelineResult` 現行欄位含 `summary`、`split_plan`，沒有 `metadata`；反向 assertion 實跑失敗。
CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:52
MUTATION: venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; print(sorted(EventPipelineResult.__annotations__)); assert "metadata" in EventPipelineResult.__annotations__'
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#1b0890e367ab; docs/SPLITUNIFY_TODO.md#f39b30357511；輸出欄位清單無 metadata、`metadata_required_mutation_rc=1`。一次文件修訂即可把 metadata／M-SU-D2-03 改掛 SU-RESID-9A-UI，Task 9.1 僅留兩層。
## CODEX-R24-P2-02
**斷言**: TODO §E `SU-RESID-C5-TARGETS` 同時寫缺錨為 19 列與「要動 20 列 register」，同一殘留的現行數字不唯一。
**碼證**: awk 重掃輸出非 anchor=15；register=29、keyed=10，故缺錨=19；行 707-708 已說 20 是舊值，行 710 卻再寫 20。
**來源摘要**: docs/SPLITUNIFY_TODO.md#f39b30357511；docs/SPLITUNIFY_SPEC.D-002.md#1b0890e367ab；一次修訂將行 710 改為 19 即可。
(2a) `REJECTED`：有一個 P1 可實作性／文件權威阻塞及一個 P2 數字不一致；(2b) 唯一 BLOCKER 是 `CODEX-R24-P1-01`，P2 不列入 BLOCKED-BY。
(3a) §N SU-RESID-1/3 無 B9B 倒退；SU-RESID-9A-UI metadata 句與兩層邊界不一致，併入 P1；Task 2.1、2.2、3.1–3.3、4.1 無新 live 衝突；Task 9.2b SPEC/TODO 三段側別、廣播、purged、disjoint、AlignmentViolationError 一致。兩個 review commit `git diff --check` 均 rc=0；非三項 collateral 依 brief 排除。
(3b) 最小貼入修補：M-SU-D2-03 只驗 producer→summary；metadata exact-key 改掛 SU-RESID-9A-UI；§N／TODO §E 刪 metadata 本延伸承諾；§P／§R「三層」改「兩層」；TODO 行 710 的 20 改 19。
(4a) 不進 B9C，先完成上述一次文件同步；(4b) SU-RESID-2 恰有兩個 blocker：Task 9.2b 與 Task 9.3，Task 9.4／9.5 不加入。
(5a) G-3a（一次性差集）與 G-5②（單 TF assignments／purged oracle）不應 supersede；(5b) G-3b 才移交 Task 9.5，複合鍵集合是跨 TF 長期 golden，B9B 單 TF 過渡不是免驗。
(6a) B9C 入口延後至 P1 關閉；(6b) 最小閉合集合為 `CODEX-R24-P1-01`、`CODEX-R24-P2-02`，不重開 9.2b／9.3 設計。
本輪未發現 API schema、量化數值、NaN/inf、OOM/cache、資料洩漏、跨 symbol、測試獨立性或必要性新缺口；本輪 finding 為 P1 文件／入口矛盾與 P2 19/20 列數矛盾。
VERDICT: blocked；BLOCKED-BY: CODEX-R24-P1-01；CLOSED: CODEX-R22-P1-01,CODEX-R22-P1-02,CODEX-R22-P1-03
ASSUMPTIONS_VERIFIED: `brief-kind: review`；body hash=`1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7`；C5 register=29/keyed=10/missing=19。
TESTS_RUN: 六組 pytest → `706 passed, 1 xfailed` rc=0；metadata mutation rc=1（預期反例）；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；兩個 review commit diff-check rc=0。
FAILURES_SEEN: 僅 brief 明示的 Task 9.2b strict-xfail 與 metadata 反向 mutation rc=1；SCOPE_CHANGES: 僅新增本報告及 SPEC 戳記，未改程式／SPEC 正文／TODO 正文／data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 未改產品數值或 schema；僅記錄文件 19/20 矛盾及現行 result 無 metadata 欄。
STATUS: DONE
