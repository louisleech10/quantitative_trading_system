# VERIFY_GATE_SPEC v2.1 — 最終確認（Composer 2.5）

**審查對象**：`docs/VERIFY_GATE_SPEC.md`（使用者標 v2.1；檔首仍寫「SPEC v2」，內容已含 closure 六項補丁）  
**對照基線**：`handoffs/20260701-VERIFYGATE-SPEC-V2-CLOSURE-COMPOSER.md` §E 六項必修  
**方法**：逐項 diff 對照 closure CHANGES-REQUESTED → 現行 SPEC 錨點；查是否仍須實作者腦補才可派工。

---

## 總評

v2.1 已將 closure §E 六項必修**全部寫入 SPEC 可測錨點**；五條件中先前「部分」的 #1/#2/#5 亦因 P3-1 機械規則、EXEMPT 六類表、W4 P0 顯式而閉合。無剩餘 SPEC 級定義缺口阻派工。

**VERDICT: APPROVED** — SPEC v2.1 可派實作。

---

## 六項必修 diff 對照表

| # | closure 必修 | closure 要求摘要 | v2.1 錨點 | 閉合？ | diff 說明 |
|---|--------------|------------------|-----------|--------|-----------|
| 1 | P3-1 operational block | 定義增量掃描機械規則，避免全檔撞牆或只掃一行漏攔 | P3-1 L64–65 | **是** | 新增 `operational result block` 機械規則：Edit→`new_string`、Write→diff 新增 hunks；區段 `## 正在做\|## 待辦\|## 已完成\|STATUS:\|RESULT` + root HANDOFF 狀態段；非 fenced/quote 新增行→operational；歷史行不重掃。較 closure 建議多 `## 已完成`/`RESULT`，為超集。 |
| 2 | claim_fingerprint | 可測公式，#6 與 pending close 同一套 | P2-1 L51；P2-2 L60；P5-2 L78 | **是** | `sha256(normalize(scope_terms + "\|" + runtime_expectation + "\|" + task_id + "\|" + source_line_text))`；明寫 #6 與 ledger open/close 共用。 |
| 3 | EXEMPT 類別表或廢除 | reconcile 六類聯集或明示廢除 | P2-1 L56；V8 L90 | **是** | 採窄類別表（未廢除）：`typo, doc-example, migration-note, template-drift, tooling-blocked, spec-ambiguity`；HANDOFF/commit/RESULT 零豁免；每檔每 issue-id ≤1；CI exempt 率 WARN。與 DELIB reconcile L32 聯集一致。 |
| 4 | W4 命名 P0 | operational pass-fail 自述無 receipt → fail-closed，須可追溯 P0 命名 | P2-1 L52–53 | **是** | `**[W4 P0 顯式]**` 獨立錨點；規則與 operational→須 VERIFY 同型。closure 允「與 P2 重述、須命名 P0」——未強制 Phase 4 P4-0 編號，追溯需求已滿足。 |
| 5 | V17 事故 byte fixture | `7e71fd1` HANDOFF、`9f9839d` commit body、`METAFIX` L6 `也正確紅` | §V L99 | **是** | V17 列三組原文 fixture，operational 且無 VERIFY → 必擋。P2-1 L48 極性段亦註「附事故 regression 原文片斷 fixture」。 |
| 6 | W12 staged+hash | claim 引用 receipt 須與 staged/tracked hash 一致 | P1-3 L40；P2-1 L49–50；§V V18 L100 | **是** | 超出 closure 建議：P1-3 解 `.gitignore *.log` 衝突；P2-1 backing 須 staged/tracked 且 receipt+log+審計 hash 相符；V18 測 untracked 拒、tracked 過。 |

---

## 五條件（closure §A）再驗

| # | 條件 | v2.1 | 閉合？ |
|---|------|------|--------|
| 1 | claim-object 誤報=0 先於 PreToolUse | §RISK L11、§V L82、P3-1 機械規則 | **是** |
| 2 | EXEMPT 窄化 + HANDOFF/commit/RESULT 零豁免 | P2-1 L56、V8 | **是** |
| 3 | #6 僅衝突檢查 | P5-2 | **是**（沿用） |
| 4 | SIGNOFF 結構化 | P2-1 L55 | **是**（沿用） |
| 5 | W2/W3/W4 P0 與 B-FORGE 同批 | P1-2、P4-2 W3、P4-3 W2、P2-1 W4 P0 | **是** |

---

## 非阻派工殘餘（closure §F 已預期；v2.1 §N 已登記）

- `task_id` 抽取規則（檔名 vs 手寫）仍未機械定義——closure 列可放 TODO。
- `scope-hash`（SIGNOFF 第四段）算法未寫——closure 列低於 BLOCK。
- 未知同義詞 WARN 通道、ledger TOCTOU 無鎖、#6 完整 render phase 2——§N L111 已明列。
- 檔首版本字樣仍「SPEC v2」非「v2.1」——文檔標籤 cosmetic，不影響實作錨點。
- **實作注意（非 SPEC 洞）**：`也正確紅` 未列入 P2-1 強極性 regex 閉集，但 V17 要求必擋；實作須以 V17 fixture 驅動補詞或 contextual 規則，不得假綠。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: docs/VERIFY_GATE_SPEC.md 全文已讀；closure §E 六項 grep+行號對照；DELIB reconcile 五條件與 W12 定案已對照
TESTS_RUN: 靜態 SPEC diff 審查（無 pytest）
FAILURES_SEEN: none
SCOPE_CHANGES: none（審查產物 + reconcile stamp append）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**VERDICT: APPROVED** — closure 六項必修均已機械落地；可派實作（仍須 §RISK：claim-object 誤報=0 測試達標後才接 PreToolUse）。

HANDOFF_NOT_UPDATED: 執行合約 — 審查任務不覆寫根 HANDOFF.md；RECONCILE-STAMP 已 append 至 `handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md`。
