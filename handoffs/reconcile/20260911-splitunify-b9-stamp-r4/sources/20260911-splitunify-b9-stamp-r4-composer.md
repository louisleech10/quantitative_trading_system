# SPLITUNIFY b9 — D-002 v18 重簽 — composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-STAMP-R4`  
**family**: composer  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-STAMP-R4-BRIEF.md`  
**findings-round**: R4  
**stamp-target**: `docs/SPLITUNIFY_SPEC.D-002.md`  
**禁改碼**：本輪只產 stamp 交件＋一行戳記 append。

---

## 必答 1 — body 重簽

**(1a) 對 body `76006a764a8c1d12437cc71c8ed38bbdaddbc65637a523cd52792d2ee3ef9433`：`APPROVED`**

**(1b) `N/A`（未 REJECTED）**

---

## 必答 2 — §P Task 9.1 與 §V Task 9.1 逐句對讀

**(2a) 前三 bullet（目標／返回形狀／跨邊界傳遞）無第三處互斥。**

**(2b) 對讀方式（現行段落，排除 HISTORY／沿革）**：

| 序 | §P `Task 9.1`（`:177-182`） | §V `Task 9.1`（`:257`） | 結論 |
|---|---|---|---|
| 1 目標 | 交付 `producer → EventSplitPlan.summary` **兩層**；終端／metadata 見 §N `SU-RESID-9A-UI` | 「只保留 producer → `EventSplitPlan.summary` 兩層」；metadata 斷言移出當輪 | 一致 |
| 2 返回形狀 | `discarded: Dict[str,int]`；無丟棄 `== {}`；**不得** `None` | `ASSERT … discarded == {"4h":2}`／`discarded == {}`（單 TF） | 一致（§V 以 ASSERT 編碼型別契約） |
| 3 跨邊界 | 原樣寫入 `summary["discarded_rows_by_feature_tf"]`；多 symbol **原樣傳遞不得相加** | `ASSERT summary … 值與 producer 回傳相同` | 一致（值相等涵蓋 verbatim；多 symbol 防放大已由 R18 測試具名於 §P） |

補充：§P `:189` 與 §V 尾段「移除上述三層」之「三層」指獨立回退／metadata 殘留語境，**不在** brief 指定之前三 bullet 審查邊界內；兩段彼此一致且為 v13 O1 既有殘留敘事，非 v18 diff 新引入之 §P↔§V 互斥。

---

## 必答 3 — Task 9.2–9.5 舊字面引用

**(3a) 無。** `Task 9.2`–`9.5` 現行條文未引用「三層完整記帳」或「逐 symbol 相加」。

**(3b) 掃描範圍**：

- `docs/SPLITUNIFY_SPEC.D-002.md` §P `Task 9.2`（`:194-202`）、`9.2a`（`:204-212`）、`9.2b`（`:214-230`）、`9.3`（`:232-240`）、`9.4`（`:242-247`）、`9.5`（`:249-253`）
- 同檔 §V `Task 9.2`–`9.5`（`:258-274`）
- `grep -n '逐 symbol 相加\|三層完整記帳' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` 排除「原寫／原文／v18／更正／作廁」註記行 → **零命中**
- `Task 9.2:199` 僅泛稱「依 `Task 9.1` 揭露」，未引用已作廢字面

---

## 必答 4 — 可否進 Task 9.2（B9B）

**(4a) 可以。** `reconcile_stamps_check` 待三家 R4 收齊後即可進批次 **B9B**（`9.2`＋`9.2a`，不得拆批）。

**(4b) 檢查項**：① v18 diff（`git show 8327d60c`）僅觸及 §P `Task 9.1` 前三 bullet 與沿革，mutation 表／register 未動；② body hash 實跑 `76006a76…` 與 brief 一致；③ `doc_format_precheck` rc=0；④ §P↔§V 前三 bullet 無互斥；⑤ `Task 9.2`–`9.5` 無舊字面殘留引用；⑥ `Task 9.1`（B9A）已實作且 R18/R19 十三條已閉合，本輪不重開。

---

## §0 被當成事實的未驗證假設

無（brief 兩條 assumed 均已逐句對讀／掃描否證）。

---

## §1 必查（11 類）

本輪輸入邊界＝v18 diff 之 §P `Task 9.1` 前三 bullet；歷史段／`Task 9.2`–`9.5` 設計／register mutation 不在範圍。各類：1–11 皆 **無**（狹義重簽輪，無新契約面）。

---

## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂之 finding；v18 兩處 §P 修補與 §V／TODO／實作已對齊，可對 body `76006a76…` 重簽。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `76006a764a8c1d12437cc71c8ed38bbdaddbc65637a523cd52792d2ee3ef9433` rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`grep -n '逐 symbol 相加\|三層完整記帳' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md | grep -v '原寫\|原文\|v18\|更正\|作廢'` → 零命中；`git show 8327d60c -- docs/SPLITUNIFY_SPEC.D-002.md` → 僅 §P `Task 9.1` 目標／跨邊界兩處同步。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#76006a764a8c

[P3] 信心度=High。逐句對讀 §P `:177-182` vs §V `:257` 前三契約面；掃描 §P `Task 9.2`–`9.5` 與 §V 對應段無舊字面引用。

---

## 戳記

已 append 至 `docs/SPLITUNIFY_SPEC.D-002.md` `## 戳記` 區（舊戳記行保留）：

```text
RECONCILE-STAMP: composer APPROVED 2026-09-14 sha256:76006a764a8c1d12437cc71c8ed38bbdaddbc65637a523cd52792d2ee3ef9433 task:20260911-SPLITUNIFY-B9-STAMP-R4
```

---

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:

ASSUMPTIONS_VERIFIED: body hash 76006a76…；doc_format_precheck rc=0；舊字面 grep 零命中（排除註記）；§P↔§V 前三 bullet 逐句對讀無互斥；Task 9.2–9.5 無舊字面引用  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`grep -n '逐 symbol 相加\|三層完整記帳' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md`（排除註記）→ 零命中；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-stamp-r4-composer.md --family composer` → rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（戳記 append ＋本交件檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_PATH: handoffs/20260911-splitunify-b9-stamp-r4-composer.md  
TMP_CLEANUP: /tmp 與 /private/tmp 無 `*workdir*`；`claude-501` 保留  

STATUS: DONE
