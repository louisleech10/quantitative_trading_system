# SPLITUNIFY b9 — review-r26（J1 閉合再驗證 ＋ D-002 v21 重簽）— grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R26`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R26-BRIEF.md`  
**findings-round**: R26  
**brief-kind**: review  
**審查標的**: commit `eac26bfe`；current block＝SPEC `§P Task 9.1` `:187`；TODO §E `SU-RESID-9A-UI` `:892`  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（戳記 append 除外）。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: body sha256 `755f3d53…` | **fact-verified** | `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → 逐字相符；append 戳記後 hash **不變** |
| brief fact-verified: 兩份 `doc_format_precheck` rc=0 | **fact-verified** | SPEC／TODO 各跑一次 → 皆 rc=0 |
| brief fact-verified: 六路回歸 706 passed／1 xfailed | **fact-verified（本家抽樣）** | summary 值相等＋獨立回退＋wiring discarded → **3 passed**；`opposite_sides_must_fail_closed` → **1 xfailed**（未重跑全六路；brief 標 VERIFY-EXEMPT） |
| brief fact-verified: r24／r25 `state=CLOSED`；r26 OPEN | **fact-verified** | `debt_ledger.sh --list \| grep review-r2` → r24／r25 `CLOSED`；r26 `OPEN` |
| brief fact-verified: 主委三 token 全檔逐行判定 | **fact-verified（抽樣對證）** | 見必答 3；本家另立同義詞表後 live 正文無新互斥 |
| brief assumed: metadata／兩層契約到本輪已窮盡（含同義措辭） | **攻過 → 成立** | 見必答 3（同義詞表＋逐段表） |
| brief assumed: `:187` 刪節未引入新自相矛盾；防假綠未失 | **攻過 → 成立** | 見必答 4 |
| brief assumed: `M-SU-D2-01`／`02` 應紅欄未指向已移出當輪測試 | **攻過 → 成立** | 見必答 5 |

---

## 必答 1 — 本家 R25 反例重跑

### (1a)

**CLOSED** — `GROK-R25-P1-01`。

| 修補 | 本家觀測 |
|------|----------|
| SPEC `:187` v21 更正＋整條舊祈使句刪節線 | **修補成立**（前置「不得列入本延伸當輪交付」＋「只驗兩層」；舊「須定義…整鏈」在 `~~…~~` 內） |
| TODO `:892` 括號鏈改兩層＋v21 更正註 | **修補成立**（現行字面＝`build_event_keys` 回傳 ＋ `EventSplitPlan.summary` 鍵；舊三層鏈刪節；與 SPEC `:330` 對齊） |
| 與本家 r25 修法稿對讀 | **逐字採納本家 3b 稿**（commit `eac26bfe` message 亦明寫） |

### (1b)

```text
sed -n '187p' docs/SPLITUNIFY_SPEC.D-002.md
# → 含「v21 更正…不得列入本延伸當輪交付」＋「只驗…兩層」＋整段舊祈使在 ~~ ~~

sed -n '892p' docs/SPLITUNIFY_TODO.md
# → 含「build_event_keys 回傳 ＋ EventSplitPlan.summary 鍵」＋「~~…metadata.split_unify~~」＋「v21 更正（R25」

bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md
# → 755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f

venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; assert "metadata" not in EventPipelineResult.__annotations__'
# → ok（欄位無 metadata）
```

反向：若修補未生效，`:187` 仍會 live 出現「須定義…整鏈測試」且無「不得列入當輪」前置——本輪未觀測到。

---

## 必答 2 — v21 body 重簽

### (2a)

**APPROVED**（body `755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f`）。

戳記已 append（舊行保留）：
`RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f task:20260911-SPLITUNIFY-B9-REVIEW-R26`

### (2b)

N/A（未 REJECTED）。

---

## 必答 3 — 契約面強制掃描（換詞表）

### (3a)

**本家同義詞／同義結構詞表**（🔴 刻意不含主委已窮舉之三 token 作為唯一依據；三 token 僅作交叉對照）：

| 類 | 詞／結構 |
|----|----------|
| 層數同義 | `三段`（交付義）、`第三層`（交付義）、`三層交付`、`三層記帳`、`三層完整`、`三層揭露`、`上述三層`、`鎖定三層`、`移除三層` |
| 鏈／驗收同義 | `整條鏈`、`整鏈測試`、`end-to-end`（交付義）、`資料流交接`、`producer→summary→metadata`、`須定義` |
| 揭露同義 | `揭露層`、`disclosure`、`終端揭露`、`metadata 層`、`Phase 9A 交付` |
| 防假綠／落點 | `手塞鍵`、`手塞`、`孤立欄位`、`孤立單測`、`build_split_unify_disclosure`、`ic_filter_orchestrator`（與 discarded／metadata 共現） |

**掃描命令**（live body＝SPEC `1..HISTORY-BEGIN`＝`:1-336`；TODO 全檔；HISTORY／沿革不列 finding）：

```text
# 詞表掃描（本家）
grep -nE '三段|第三層|揭露層|disclosure|end-to-end|整條鏈|三層交付|三層記帳|三層完整|手塞鍵|孤立欄位|孤立單測|metadata 層|終端揭露|build_split_unify_disclosure|ic_filter_orchestrator|producer→summary→metadata|Phase 9A 交付|須定義|整鏈測試|鎖定三層|上述三層|移除三層|三層揭露|資料流交接|手塞' \
  docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md

# 交叉：主委三 token（僅對照，非本條唯一依據）
grep -nE 'metadata\.split_unify|三層|整鏈' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md
```

逐段結論（與「metadata 層已入 `SU-RESID-9A-UI`、本延伸只交兩層」／B9B 互斥？）：

| 段 | 互斥？ | 說明 |
|----|--------|------|
| SPEC `(5.4) 第三層｜偵察` `:80` | **無** | 消費面分類層級用語，非 Phase 9A 交付層數 |
| SPEC (G-4e)／Task 9.2b「三段式」`:168`／`:219`／`:264-265` | **無** | 側別判準步驟數，非揭露層數 |
| SPEC §P Task 9.1 目標 `:177` | **無** | 已兩層＋v18 更正；三層字面在更正註內 |
| SPEC 交付 bullet `:185-186` | **無** | metadata 半句刪節＋v19 註 |
| SPEC **`:187`** | **無（本輪已閉）** | v21 前置「不得列入當輪」＋舊整鏈祈使全刪節 |
| SPEC exact-key `:188` | **無** | v20 刪節「鎖定三層」；②明寫整段入殘留 |
| SPEC 獨立回退 `:190`／§R `:323` | **無** | 現行「兩層」；舊「三層」刪節 |
| SPEC §V Task 9.1 `:258` | **無** | live 只留兩層值相等；metadata／孤立單測告誡在「移出當輪」段 |
| SPEC `M-SU-D2-03` `:282` | **無** | 殘留期間無應紅／`blocked-by` |
| SPEC §N `SU-RESID-9A-UI` `:330` | **無** | 兩層＋metadata 刪節（v20） |
| SPEC `ic_filter_orchestrator` `:221` | **無** | Task 9.2b 座標／validator 落點，非 discarded→metadata 交付 |
| SPEC `終端揭露` `:247` | **無** | `insufficient_events_in_test` 旗標可見性延後，已掛同一殘留 |
| TODO Task 4.1 `:410` | **無** | IC 路徑既有五鍵揭露（C-6），非 9A discarded 第三層 |
| TODO Task 9.1 `:469-479` | **無** | 明寫 metadata **不在**本 Task；`M-SU-D2-03` 隨殘留 |
| TODO Task 2.2／2.3／9.2–9.5 | **無** | SUPERSEDED／與 B9B 一致；無 live 三層交付 |
| TODO §E `SU-RESID-2` | **無** | 部分關閉；阻擋者 `9.2b`／`9.3` |
| TODO §E **`SU-RESID-9A-UI` `:892`** | **無（本輪已閉）** | 現行兩層字面＋舊三層刪節＋v21 註 |
| TODO `ic_filter_orchestrator` 多處 | **無** | 既有 caller／時鐘／符號路徑敘述 |
| diff 夾帶 | **無超範圍契約改動** | `git show eac26bfe` 契約面＝`:187`＋`:892`（＋沿革／戳記；沿革不在審查範圍） |

### (3b)

**無**新互斥。詞表足以支持「無」的理由：

1. 覆蓋了「層數／鏈／揭露／防假綠／具名 builder・orchestrator」五類替代寫法，正是前六次漏網的類型。  
2. live 命中凡含交付義者，皆已帶 v18–v21 更正、刪節線、或「移出當輪／不得列入／不在本 Task」。  
3. 未帶更正標記的命中（`(5.4) 第三層`、側別「三段式」、Task 4.1 五鍵、`ic_filter` 既有路徑）語意上**不是**「本延伸須交 metadata 第三層」。  
4. 主委三 token 交叉掃描未再發現第三處 live 互斥。

---

## 必答 4 — `:187` 刪節後是否失去必要施工指示

### (4a)

**否。** 被刪節的防假綠告誡（「不得寫直接呼叫 builder 手塞鍵的孤立單測」）之**作用域是 metadata／`build_split_unify_disclosure` 層**，該層本延伸不交付；刪節＋「殘留解除後才生效」與 `:188` ②／§V「移出當輪」同向，未引入自相矛盾。

兩層範圍內之防假綠**仍在**：

- §V live：`ASSERT EventSplitPlan.summary … 且值與 producer 回傳相同`（非只驗鍵）  
- mutation `M-SU-D2-01`／`02` 應紅仍指 summary 鍵／值斷言  
- R18 配線測試 `test_splitunify_wiring_discarded_rows_reaches_summary`（本輪實跑 PASSED）

metadata 層之「手塞 builder」告誡保留在 `:187` 刪節線與 `:258`「移出當輪」段內，殘留解除時仍可讀。

### (4b)

N/A（不需另貼字面）。

---

## 必答 5 — `M-SU-D2-01`／`02` 應紅欄

### (5a)

**否**——兩列皆**未**指向已移出當輪之 metadata 測試。

| ID | 應紅欄（現行） | 判定 |
|----|----------------|------|
| `M-SU-D2-01` | `Task 9.1` 之 summary 鍵斷言 | 屬兩層；仍有效 |
| `M-SU-D2-02` | `Task 9.1` 之 summary 鍵與值斷言（`tests/momentum/Analysis/test_splitunify_derive.py`） | 屬兩層；仍有效 |
| （對照）`M-SU-D2-03` | 殘留期間無應紅／`blocked-by` | 已於 v20 正確改標；非本問標的 |

### (5b)

```text
sed -n '280,282p' docs/SPLITUNIFY_SPEC.D-002.md
# 01/02 應紅欄僅含 summary／derive 測試路徑；無 metadata.split_unify、無 test_splitunify_disclosure exact-key

venv/bin/python -m pytest -q --tb=no \
  tests/momentum/Analysis/test_splitunify_derive.py::test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer \
  tests/momentum/Analysis/test_splitunify_derive.py::test_discarded_layer_is_independently_revertible
# → 2 passed
```

---

## 必答 6 — 可否進 Task 9.2b（B9C）

### (6a)

**可以。** 本家無 BLOCKING；J1 兩處已閉；v21 body 本家 APPROVED。

### (6b)

已檢查：`GROK-R25-P1-01` CLOSED；同義詞表全檔掃描無新互斥；`:187` 刪節未失兩層防假綠；`M-SU-D2-01`／`02` 應紅仍指 summary；C5 數字抽驗 19／10／4／15／29 與 mutation 40／register 29 一致；抽樣 pytest 3 passed＋1 xfailed；`doc_format` 兩份 rc=0；body hash 相符。**不重開** `Task 9.2b`–`9.5` 設計。進 B9C 仍須齊三家 APPROVED 戳記＋領 impl token（本家只完成本家一枚）。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：J1 兩處已閉；同義詞掃描無新互斥。  
2. 漏項：無本輪新增。  
3. 不可測：無。  
4. 可疑 quant：不重開。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：本輪未改生產簽章。  
9. 測試品質：抽樣 3 passed＋1 xfailed。  
10. Agent 可執行：`:187`／`:892` 已不再誤導當輪交付三層。  
11. 必要性／短命工：無本輪新增短命工。

---

## GROK-R26-P3-00

**斷言**: 本輪逐項核對後無 finding——`GROK-R25-P1-01` 反例已 CLOSED；另立同義詞表掃描 SPEC live（`:1-336`）與 TODO 全檔後，無與「metadata 層入殘留、本延伸只交兩層」互斥之 live 字面；`:187` 刪節未失去兩層防假綠；`M-SU-D2-01`／`02` 應紅仍指 summary；可進 `Task 9.2b`（B9C）之前提在本家側已滿足。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f`；`sed -n '187p' docs/SPLITUNIFY_SPEC.D-002.md` 含 v21「不得列入當輪」＋刪節線；`sed -n '892p' docs/SPLITUNIFY_TODO.md` 現行兩層＋舊三層刪節；同義詞 `grep -nE '…'` 之 live 互斥命中數＝0（見必答 3 表）；`sed -n '280,281p'` 之 `M-SU-D2-01`／`02` 應紅僅 summary；pytest 三節點 **3 passed**、`opposite_sides` **1 xfailed**；`EventPipelineResult` 無 `metadata` 欄。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R26-BRIEF.md#8c30ebefe12d; docs/SPLITUNIFY_SPEC.D-002.md#8603d7aa8fd7; docs/SPLITUNIFY_TODO.md#7a18de5a95ff

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f task:20260911-SPLITUNIFY-B9-REVIEW-R26
```

（舊戳記行已保留；composer 本輪 APPROVED 行亦已在檔內。）

---

## C5 數字抽驗（brief：獨立抽驗一次即可）

| 數字 | 觀測 |
|------|------|
| mutation 40 | SPEC live `M-SU-D2-01`..`40` 實列 40；宣稱「共 **40** 條」 |
| register 29 | SPEC live `C5-01`..`29` 實列 29 |
| (甲)/(乙)/(丙)/缺錨 | TODO `:691-710`＝10／4／15／19；無第三處 live「20 列」作現行判準 |

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R25-P1-01

ASSUMPTIONS_VERIFIED: body hash 755f3d53…；doc_format 兩份 rc=0；r24／r25 CLOSED；J1 兩處 CLOSED；assumed1 同義詞窮盡成立；assumed2 防假綠未失；assumed3 M01／M02 應紅仍指 summary；可進 B9C（本家側）
TESTS_RUN: `reconcile_body_hash.sh` → 755f3d53…；`doc_format_precheck` SPEC／TODO → rc=0；pytest summary 值相等＋獨立回退＋wiring discarded → 3 passed；opposite_sides → 1 xfailed；metadata 反向 assert → 欄位無 metadata
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅 SPEC 戳記區 append＋本交件）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r26-grok.md
STAMP_APPENDED: docs/SPLITUNIFY_SPEC.D-002.md（舊戳記保留；APPROVED）

STATUS: DONE
