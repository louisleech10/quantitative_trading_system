# SPLITUNIFY b9 — review-r23（r22 F1／F2／F3 閉合再驗證 ＋ D-002 v19 重簽）— grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R23`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R23-BRIEF.md`  
**findings-round**: R23  
**brief-kind**: review  
**審查標的**: commit `4ee9632b`；current block＝SPEC §P Task 9.1 交付 bullet／§N `SU-RESID-2`；TODO §E `SU-RESID-2`／`Task 2.3` golden  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（戳記 append 除外）。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: body sha256 `1b0890e3…` | **fact-verified** | `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → 逐字相符；append 戳記後 hash **不變** |
| brief fact-verified: 兩份 `doc_format_precheck` rc=0 | **fact-verified** | SPEC／TODO 各跑一次 → 皆 rc=0 |
| brief fact-verified: 六路回歸 706 passed／1 xfailed | **fact-verified（本家抽樣）** | scoped 三節點 → **2 passed, 1 xfailed**（未重跑全六路；brief 標 VERIFY-EXEMPT:doc-example） |
| brief fact-verified: r22 `state=CLOSED` | **fact-verified** | `debt_ledger.sh --list \| grep review-r22` → `state=CLOSED` |
| brief assumed: `SU-RESID-2` 阻擋者恰為 `Task 9.2b`＋`9.3`（非四項） | **攻過 → 成立** | 見必答 4 |
| brief assumed: Task 2.3「單 TF 下仍成立」不會被誤讀成免責 | **攻過 → 成立（不必改條件式）** | 見必答 5 |

---

## 必答 1 — 本家 R22 反例重跑

### (1a)

本家 review-r22 **無實質 finding**（僅 sentinel `GROK-R22-P3-00`）⇒ 無本家可標 `CLOSED` 之反例 ID。  
對照驗收標的（他家 `CODEX-R22-P1-01`／`P1-02`／`P1-03`＝F1／F2／F3）本家仍實核：

| 修補 | 本家觀測 |
|------|----------|
| F1 `SU-RESID-2` → 部分關閉 | **修補成立**（TODO §E 與 SPEC §N 同步；`blocked-by:Task 9.2b／9.3`；`pattern_bridge.py:125` 仍 raw `set_index("event_id")` 佐證下游未關） |
| F2 Task 2.3 SUPERSEDED → Task 9.5 | **修補成立**（G-3b 段已標；凍結腳本仍單一 `feature_timeframe="1h"`） |
| F3 §P metadata 交付句刪節線＋§N 同步 | **修補成立**（交付 bullet 刪節線＋v19 註；§N 改「部分關閉」） |

誠實更正：本家 r22 必答 3 曾判「已關閉」——**該立場被 F1 採納案否決**；本輪依殘留原文「下游一起改」接受「部分關閉」。

### (1b)

- F1：`grep -n 'SU-RESID-2' docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.D-002.md` → TODO:889「部分關閉」＋`blocked-by`；SPEC:327「部分關閉」；`sed -n '125,127p' momentum/Analysis/event_samples/pattern_bridge.py` → 仍 `assign.set_index("event_id")["split_label"]`。
- F2：`grep -n SUPERSEDED docs/SPLITUNIFY_TODO.md` → `:283` 為 `SUPERSEDED BY Task 9.5`；`scripts/freeze_splitunify_golden.py:110` 仍單一 `"feature_timeframe": "1h"`。
- F3：`git show 4ee9632b -- docs/SPLITUNIFY_SPEC.D-002.md` → 交付句刪節線＋v19 註；§N 由「needs-research 同步」改「部分關閉」。
- 抽樣：`venv/bin/python -m pytest -q -rxX` 三節點 → **2 passed, 1 xfailed**。

---

## 必答 2 — v19 body 重簽

### (2a)

**APPROVED**（body `1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7`）。

戳記已 append（舊行保留）：
`RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7 task:20260911-SPLITUNIFY-B9-REVIEW-R23`

### (2b)

N/A（未 REJECTED）。

---

## 必答 3 — 契約面改動後強制掃描舊段

### (3a)

**掃描命令與範圍**（非本輪改動處）：

```text
grep -nE '每事件恰|恰有一列|恰一列|12 鍵|13 鍵|16 鍵|validate=.1:1.|str\(selected_timeframe\)|metadata\.split_unify|SUPERSEDED|feature_timeframe|selected_timeframe' docs/SPLITUNIFY_TODO.md
grep -nE 'metadata\.split_unify|兩層|三層|SU-RESID-|Task 9\.[1-5]|feature_timeframe|selected_timeframe|複合鍵' docs/SPLITUNIFY_SPEC.D-002.md
```

逐段結論：

| 段 | 與 B9B 新契約互斥？ | 說明 |
|----|---------------------|------|
| TODO Task 2.1 | **無** | 邊界算術 |
| TODO Task 2.2 | 已 SUPERSEDED（R21） | 三處 |
| TODO Task 2.3 G-3b | 已 SUPERSEDED（R22） | 本輪 F2 |
| TODO Task 2.3 G-3a／G-5② | **無（不開 finding）** | 仍寫 event_id 集合，但屬歷史／單 TF 過渡；多 TF 權威＝`Task 9.5`；凍結腳本現仍單 TF ⇒ 現行行為正確。codex 原提「三處」實落一處 SUPERSEDED——其餘兩處**不構成 B9C 施工互斥** |
| TODO Task 3.1–3.3／4.1 | **無** | 無回退全量／單選之現行施工令 |
| TODO Task 5.x | **無** | 無此 heading |
| SPEC §P Task 9.1 vs §V Task 9.1 | **無第三處互斥** | 目標句／跨邊界皆「兩層／原樣傳遞」；交付 bullet 已刪節線；metadata 施工字面標「殘留解除時／不得列入當輪」 |
| SPEC §N `SU-RESID-1`／`3` | **無** | 與 B9B 契約無涉 |
| SPEC §N `SU-RESID-9A-UI` | **無（不開 finding）** | 括號仍列 `metadata.split_unify` 為「本延伸交付」字面——屬 O1／v8 舊殘留措辭，**stamp-r4 已對含該句之 v18 蓋章**；不阻 B9C；非本輪 F3 回歸 |
| SPEC／TODO `Task 9.2b` 三段式 | **一致** | 皆 `<=train_last`⇒train／`>=test_start`⇒test／介於⇒purged；跨表互斥；`AlignmentViolationError` |
| diff 夾帶 | **無** | `git show 4ee9632b` 之 SPEC／TODO 差僅 F1–F3 三處 |

### (3b)

**N/A（無須新增 SUPERSEDED／修正字面作為本輪閉合集合）**。  
掃描足以支持「無」：互斥字面要嘛已 SUPERSEDED、要嘛屬已完工 Task 之改前快照／殘留字面保留，且 `Task 9.2b` 施工權威段與 B9B **無互斥**。

---

## 必答 4 — `SU-RESID-2` 阻擋者清單

### (4a)

**應為兩項**：`Task 9.2b`＋`Task 9.3`（**不是**四項）。

理由：殘留原文「複合鍵要連 `EventSplitPlan` 之下游一起改」在 D-002 分工下＝側別錨定（9.2b）＋九處消費面（9.3）。`Task 9.4`＝`D-002-C6` 量詞／記帳可見性；`Task 9.5`＝golden／前端基準——皆受複合鍵**影響**，但**不是**該殘留描述的「下游身份／側別消費」閉合條件。依賴序亦將 9.4∥9.3、9.5 置於更後。

### (4b)

可直接貼入（現行 TODO §E 已等同此清單）：

> **尚未關閉者**＝下游消費面（`Task 9.3` 之九處逐處處置）與側別錨定（`Task 9.2b`）。**為何現在不做**：`blocked-by:Task 9.2b／9.3 尚未實作`——依賴序明定 `9.2a → 9.2b → 9.3`，不得跳。🔴 **不列** `Task 9.4`／`9.5` 為本殘留阻擋者（各屬 `D-002-C6` 記帳與 golden 擴維，另有完成條件）。

---

## 必答 5 — Task 2.3「單 TF 下仍成立」

### (5a)

**不需要**改成條件式寫法。

現行已寫「凍結腳本維持單一 feature TF…故本句在單 TF 下仍成立，是**跨批的過渡狀態**而非現行缺陷」，且上有 `SUPERSEDED BY Task 9.5`。後續實作者讀到的權威擴維指示在 `Task 9.5`／SPEC §G，不會把該註記讀成「9.5 前永遠不必動 golden」之免責——`SUPERSEDED BY` 本身即指向必須改的目標 Task。

### (5b)

N/A（不改）。若主委想更咬字，可選（非必須）：

> 🔴 **僅在** `scripts/freeze_splitunify_golden.py` 之 fixture **仍為單一** `feature_timeframe` 時，event_id-only 比對成立；**一旦**擴多 TF（`Task 9.5`），本句**立刻失效**，須改複合鍵集合／`*_multi_tf` 平行組。

---

## 必答 6 — 可否進 Task 9.2b（B9C）

### (6a)

**可以進 `Task 9.2b`（批次 `B9C`）。** 無本家 P0／P1；F1–F3 修補實核成立；assumed 兩條攻擊後不構成 BLOCKING；v19 body **APPROVED** 並已 append 戳記。

### (6b)

已檢查：`git show 4ee9632b`（SPEC／TODO 僅 F1–F3）；body hash 實跑相符；TODO／SPEC `SU-RESID-2` 部分關閉同步；Task 2.3 SUPERSEDED＋單 TF freeze；§P／§V Task 9.1 無第三處互斥；舊 Task 2.1–4.1 掃無未標 B9B 互斥施工令；SPEC↔TODO `Task 9.2b` 三段式一致；`pattern_bridge.py:125` 仍 raw（佐證部分關閉）；scoped pytest → **2 passed, 1 xfailed**。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：F1–F3 與碼／文件一致；無新增 B9C 阻擋互斥。  
2. 漏項：無（閉合＋重簽輪）。  
3. 不可測：部分關閉可由下游 raw lookup 證偽；xfail 仍在。  
4. 可疑 quant：異側混態仍屬 9.2b——不重開。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：本輪未改生產簽章。  
9. 測試品質：抽樣 16 鍵／`feature_timeframe` 來源／xfail 錨點仍綠／預期 xfail。  
10. Agent 可執行：可進 9.2b。  
11. 必要性／短命工：無本輪新增短命工。

---

## GROK-R23-P3-00

**斷言**: 本輪逐項核對後無 finding；F1／F2／F3 修補成立，v19 body APPROVED，可進 Task 9.2b（B9C）。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7`；`git show 4ee9632b -- docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` 僅 F1–F3；TODO:889／SPEC:327「部分關閉」＋`blocked-by:Task 9.2b／9.3`；`pattern_bridge.py:125` 仍 raw `set_index("event_id")`；TODO:283 `SUPERSEDED BY Task 9.5`；`freeze_splitunify_golden.py:110` 單一 feature TF；§P 交付 bullet 刪節線＋v19 註；§P／§V Task 9.1 逐句對讀無第三處互斥；舊 Task 2.1／2.3／3.1–3.3／4.1 掃無未標 B9B 互斥施工令；SPEC↔TODO Task 9.2b 三段式一致；`venv/bin/python -m pytest -q -rxX` 三節點 → **2 passed, 1 xfailed**；戳記已 append 且 body hash 不變。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R23-BRIEF.md#4fd774eb26af

[P3] 信心度=High。閉合＋重簽輪 sentinel；F1–F3 由 diff／grep／抽樣 pytest 核對；assumed 兩條攻擊後不阻 B9C。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body hash 1b0890e3…；doc_format 兩份 rc=0；r22 CLOSED；F1 部分關閉同步＋下游仍 raw；F2 SUPERSEDED＋單 TF freeze；F3 metadata 刪節線；阻擋者＝兩項非四項；Task 2.3 不必改條件式；§P／§V 無第三處互斥；可進 B9C
TESTS_RUN: `pytest -q -rxX` 三節點（xfail 錨＋sixteen_keys＋feature_timeframe 來源）→ 2 passed, 1 xfailed；`reconcile_body_hash.sh` → 1b0890e3…；`doc_format_precheck` SPEC／TODO → rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only；僅 SPEC 戳記區 append）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r23-grok.md
STAMP_APPENDED: docs/SPLITUNIFY_SPEC.D-002.md（舊戳記保留）

STATUS: DONE
