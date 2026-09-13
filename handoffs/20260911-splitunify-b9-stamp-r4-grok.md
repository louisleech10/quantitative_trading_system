# SPLITUNIFY b9 — D-002 v18 重簽 — grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-STAMP-R4`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-STAMP-R4-BRIEF.md`  
**findings-round**: R4  
**stamp-target**: `docs/SPLITUNIFY_SPEC.D-002.md`  
**禁改碼**：本輪只產 stamp 交件＋一行戳記 append；未改 SPEC 正文／TODO／生產碼。

---

## 必答 1 — body 重簽

**(1a) 對 body `76006a764a8c1d12437cc71c8ed38bbdaddbc65637a523cd52792d2ee3ef9433`：`APPROVED`**

實跑 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `76006a764a8c1d12437cc71c8ed38bbdaddbc65637a523cd52792d2ee3ef9433`（與 brief 逐字相符）。v18 diff（`git show 8327d60c -- docs/SPLITUNIFY_SPEC.D-002.md`）僅同步 §P `Task 9.1` 目標／跨邊界兩處至 §V／TODO／實作既定現況，mutation／register 未動。

**(1b) `N/A`（未 REJECTED）**

---

## 必答 2 — §P Task 9.1 與 §V Task 9.1 逐句對讀（攻 assumed）

**(2a) 無第三處互斥。** 在 brief 指定之 current block（§P `Task 9.1` 前三 bullet）對 §V `Task 9.1` 逐句對讀後，除已修之 metadata 層數與多 symbol 相加兩點外，無新的語意差。

**(2b) 對讀方式與對照表**（現行段落；排除 `HISTORY-BEGIN..END`／「## 沿革與追溯索引」）：

| 序 | §P `Task 9.1`（`:177-182`） | §V `Task 9.1`（`:257`） | 結論 |
|---|---|---|---|
| 1 目標 | 交付至 `producer → EventSplitPlan.summary` **兩層**；終端可見性與 `metadata.split_unify` 見 §N `SU-RESID-9A-UI` | 「只保留 producer → `EventSplitPlan.summary` 兩層」；metadata 兩條 ASSERT 移出當輪、併入殘留 | 一致 |
| 2 返回形狀 | `discarded: Dict[str, int]`；無丟棄時為 `{}`；**不得**省略或回 `None` | `ASSERT … discarded == {"4h": 2}`；`ASSERT WHEN 單一 feature TF THEN discarded == {}` | 一致（§V 以 ASSERT 編碼同一契約；`{}` vs `None` 無差） |
| 3 跨邊界 | 原樣寫入 `summary["discarded_rows_by_feature_tf"]`；多 symbol **原樣傳遞、不得相加** | `ASSERT EventSplitPlan.summary 帶 discarded_rows_by_feature_tf 且值與 producer 回傳相同` | 一致（值相等涵蓋 verbatim；多 symbol 防放大由 §P 具名＋R18 測試鎖住，§V 未另開矛盾字面） |

觀測（**不列 finding**）：§P `:189` 與 §V 尾段仍寫「移除上述**三層**」——屬獨立回退／殘留語境之既有字面，**不在**前三 bullet 審查邊界，且兩段彼此一致，非 v18 diff 新引入之 §P↔§V 互斥。

---

## 必答 3 — Task 9.2–9.5 是否引用被改掉的舊字面（攻 assumed）

**(3a) 無。**

**(3b) 掃描範圍與結果**：

- `docs/SPLITUNIFY_SPEC.D-002.md` §P `Task 9.2`（`:194-202`）、`9.2a`（`:204-212`）、`9.2b`（`:214-230`）、`9.3`（`:232-240`）、`9.4`（`:242-247`）、`9.5`（`:249-253`）
- 同檔 §V `Task 9.2`–`9.5`（`:258-274`）
- `docs/SPLITUNIFY_TODO.md` §C-9 `Task 9.2`–`9.5`（自 `:491` 起）
- `grep -n '逐 symbol 相加\|三層完整記帳' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` 後排除「原寫／原文／v18／更正／作廢」註記行 → **零命中**
- `Task 9.2:199` 僅寫「過濾掉的列數仍須依 `Task 9.1` 揭露」；`Task 9.4:246` 僅寫「隨 `Task 9.1` 之殘留一併延後」——皆未引用已作廢之「三層」或「逐 symbol 相加」字面

---

## 必答 4 — 可否進 Task 9.2（批次 B9B）

**(4a) 可以**（待三家 R4 戳記收齊且 `reconcile_stamps_check` rc=0 後）。

**(4b) 本家已檢查**：① body hash 實跑＝`76006a76…`；② `doc_format_precheck` rc=0；③ v18 diff 只觸及 §P `Task 9.1` 前三 bullet＋沿革；④ §P↔§V 前三契約面無互斥；⑤ `Task 9.2`–`9.5` 無舊字面殘留；⑥ B9A（`Task 9.1`）已實作、R18／R19 十三條已閉合，本輪不重開。批次＝`B9B`＝`9.2`＋`9.2a`，**不得拆批**。

---

## §0 被當成事實的未驗證假設

無。brief 兩條 assumed（§P↔§V 完全一致；修補不影響 9.2–9.5）均已以逐句對讀／範圍掃描否證為「無第三處互斥／無舊字面引用」。

---

## §1 必查（11 類）

本輪輸入邊界＝v18 diff 之 §P `Task 9.1` 前三 bullet。歷史段／`Task 9.2`–`9.5` 設計／register mutation 不在範圍。1–11 皆 **無**（狹義重簽輪，無新契約面）。

---

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；v18 對 §P `Task 9.1` 兩處修補已與 §V／TODO／實作對齊，可對 body `76006a76…` 重簽並進 `Task 9.2`（B9B）前置。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `76006a764a8c1d12437cc71c8ed38bbdaddbc65637a523cd52792d2ee3ef9433`；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`grep -n '逐 symbol 相加\|三層完整記帳' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` 排除「原寫／原文／v18／更正／作廢」→ 零命中；`git show 8327d60c -- docs/SPLITUNIFY_SPEC.D-002.md` → 僅目標句「三層→兩層」與跨邊界「相加→原樣傳遞」兩處活文同步；逐句對讀 §P `:177-182` vs §V `:257` 三面一致。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#76006a764a8c

[P3] 信心度=High。攻 assumed「§P↔§V 是否仍有第三處互斥」→ 前三 bullet 無；攻 assumed「9.2–9.5 是否引用舊字面」→ 無。

---

## 戳記

已 append 至 `docs/SPLITUNIFY_SPEC.D-002.md` `## 戳記` 區（舊戳記行保留）：

```text
RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:76006a764a8c1d12437cc71c8ed38bbdaddbc65637a523cd52792d2ee3ef9433 task:20260911-SPLITUNIFY-B9-STAMP-R4
```

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body hash 76006a76…；doc_format_precheck rc=0；舊字面 grep 零命中（排除註記）；§P↔§V 前三 bullet 逐句對讀無互斥；Task 9.2–9.5 無舊字面引用
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → 76006a76…；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`grep -n '逐 symbol 相加\|三層完整記帳' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md`（排除註記）→ 零命中；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-stamp-r4-grok.md --family grok` → COMPLETENESS PASS rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（戳記 append ＋本交件檔）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-stamp-r4-grok.md
TMP_CLEANUP: /tmp 與 /private/tmp 無 `*workdir*` 可清；`claude-501` 保留

STATUS: DONE
