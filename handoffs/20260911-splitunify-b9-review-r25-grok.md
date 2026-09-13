# SPLITUNIFY b9 — review-r25（H1／H2 閉合再驗證 ＋ D-002 v20 重簽）— grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R25`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R25-BRIEF.md`  
**findings-round**: R25  
**brief-kind**: review  
**審查標的**: commit `69947430`；current block＝SPEC `M-SU-D2-03`／§P Task 9.1／§V Task 9.1 尾句／§R／§N `SU-RESID-9A-UI`；TODO §E `SU-RESID-C5-TARGETS`  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（戳記 append 除外）。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: body sha256 `c12382d3…` | **fact-verified** | `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → 逐字相符 |
| brief fact-verified: 兩份 `doc_format_precheck` rc=0 | **fact-verified** | SPEC／TODO 各跑一次 → 皆 rc=0 |
| brief fact-verified: 六路回歸 706 passed／1 xfailed | **fact-verified（本家抽樣）** | `sixteen_keys`／`discarded_layer_is_independently_revertible`／`wiring_discarded_rows_reaches_summary` → **3 passed**；`opposite_sides_must_fail_closed` → **1 xfailed**（未重跑全六路；brief 標 VERIFY-EXEMPT） |
| brief fact-verified: r23／r24 `state=CLOSED` | **fact-verified** | `debt_ledger.sh --list \| grep review-r2` → 兩 round `state=CLOSED`；r25 `state=OPEN` |
| brief assumed: metadata 舊字面六處已窮盡、TODO 無把該層當本批交付 | **攻過 → 否證** | 見必答 3／`GROK-R25-P1-01`：SPEC `:187` ＋ TODO `:892` 仍 live |
| brief assumed: `M-SU-D2-03` 改標無應紅正確、不傷條數／register | **攻過 → 成立** | 見必答 4 |
| brief assumed: `SU-RESID-C5-TARGETS` 只改數字、無第三處舊「20」 | **攻過 → 成立** | 見必答 5 |

---

## 必答 1 — 本家 R23 sentinel 反例重跑

### (1a)

本家 review-r23 **無實質 finding**（僅 sentinel `GROK-R23-P3-00`）⇒ 無本家可標 `CLOSED` 之反例 ID。  
對照驗收標的（他家 `CODEX-R24-P1-01`＝H1／`CODEX-R24-P2-02`＝H2）本家仍實核六處＋數字修補：

| 修補 | 本家觀測 |
|------|----------|
| H1① `M-SU-D2-03` → 殘留期間無應紅／`blocked-by` | **修補成立**（SPEC `:282`；判準同 `C5-28`） |
| H1② §P「鎖定三層」祈使句 | **修補成立**（`:188` 刪節線＋v20 更正註） |
| H1③ §P 獨立回退「移除上述三層」 | **修補成立**（`:190` 已改「兩層」） |
| H1④ §V Task 9.1 尾句 | **修補成立**（`:258` 已改「兩層」） |
| H1⑤ §R 回退句 | **修補成立**（`:323` 已改「兩層」） |
| H1⑥ §N `SU-RESID-9A-UI` 括號 | **修補成立**（SPEC `:330` metadata 刪節） |
| H2 `SU-RESID-C5-TARGETS` 20→19 | **修補成立**（TODO `:710-711`） |
| H1 閉合完備？ | **不完備** → 見 `GROK-R25-P1-01`（`:187`／TODO `:892` 漏同步） |

### (1b)

- H1 六處：`git show 69947430 -- docs/SPLITUNIFY_SPEC.D-002.md` 可見六處改「兩層」／刪節線；`grep -n '殘留期間無應紅\|鎖定三層\|移除上述\*\*兩層\*\*\|SU-RESID-9A-UI' docs/SPLITUNIFY_SPEC.D-002.md` 於正文命中皆帶 v20 更正或刪節線。
- H2：`grep -n '要動 \*\*19\*\* 列\|~~20 列~~' docs/SPLITUNIFY_TODO.md` → `:710-711`。
- 反向碼證：`venv/bin/python -c '… assert "metadata" in EventPipelineResult.__annotations__'` → **AssertionError**（欄位清單無 `metadata`；`metadata_assert_rc=1`）。
- 抽樣：`pytest` 三綠＋一 xfail（見上）。

---

## 必答 2 — v20 body 重簽

### (2a)

**REJECTED**（body `c12382d397d96beb732e9514a6cb540519a7833c3921cd5d4bcfab66e1dfad05`）。

戳記已 append（舊行保留）：
`RECONCILE-STAMP: grok REJECTED 2026-09-14 sha256:c12382d397d96beb732e9514a6cb540519a7833c3921cd5d4bcfab66e1dfad05 task:20260911-SPLITUNIFY-B9-REVIEW-R25 — BLOCKED-BY: GROK-R25-P1-01`

### (2b)

阻擋項（一次文件修訂可全關）：

1. **`GROK-R25-P1-01`**：SPEC §P Task 9.1 `:187` 仍 live 要求 producer→metadata 資料流交接＋「producer→summary→metadata 整鏈」驗收；TODO §E `SU-RESID-9A-UI` `:892` 仍 live 寫 Phase 9A 交付三層鏈（含 `metadata.split_unify`）。兩處與 v20 已定「本延伸只交兩層、metadata 入殘留」互斥。

---

## 必答 3 — 契約面改動後強制掃描舊段

### (3a)

**掃描命令與範圍**（含非本輪改動處；HISTORY／沿革排除於結論）：

```text
# SPEC 正文（人工排除 HISTORY-BEGIN..END = :337-380）
grep -nE '三層|metadata\.split_unify|本延伸交付|producer→metadata|整鏈|兩層|SU-RESID-|Task 9\.[1-5]|feature_timeframe|selected_timeframe|複合鍵|12 鍵|13 鍵|16 鍵' docs/SPLITUNIFY_SPEC.D-002.md

# TODO 全檔
grep -nE '三層|metadata\.split_unify|本延伸交付|Phase 9A 交付|20 列|19 列|12 鍵|13 鍵|16 鍵|單選|逐 symbol 相加|SU-RESID-|Task 9\.[1-5]|SUPERSEDED' docs/SPLITUNIFY_TODO.md

# 補強：bare「producer→metadata」（不含 .split_unify 字面，會漏掃 :187）
grep -nE 'producer→metadata|producer->metadata|整鏈' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md
```

逐段結論：

| 段 | 與「metadata 層已入 `SU-RESID-9A-UI`、本延伸只交兩層」／B9B 互斥？ | 說明 |
|----|---------------------------------------------------------------------|------|
| SPEC `(5.4) 第三層｜偵察` | **無** | 消費面分類層級用語，非 Phase 9A 交付層數 |
| SPEC §P Task 9.1 目標句 `:177` | **無** | 已兩層＋v18 更正註 |
| SPEC §P 交付 bullet `:185-186` | **無** | metadata 半句刪節＋v19 註 |
| SPEC §P **`:187` producer→metadata handoff** | **是** | live 祈使「須定義…整鏈測試」，**無**刪節線／「殘留解除後才生效」標記；與同節「只交兩層」及 §V「metadata 移出當輪」互斥 → `GROK-R25-P1-01` |
| SPEC §P exact-key `:188` | **無（已標延後）** | v20 刪節「鎖定三層」；②明寫整段入殘留、**不得列入當輪交付** |
| SPEC §P 獨立回退 `:190` | **無** | v20 已兩層 |
| SPEC §P Task 9.2–9.5 | **無** | 無 live 三層／metadata 本批交付宣稱 |
| SPEC §V Task 9.1 `:258` | **無** | metadata 斷言已「移出當輪」；尾句 v20 兩層 |
| SPEC §V Task 9.2–9.5 | **無** | 與 B9B 複合鍵／側別一致 |
| SPEC mutation `M-SU-D2-03` `:282` | **無** | v20 已改無應紅／`blocked-by` |
| SPEC §R `:323` | **無** | v20 已兩層 |
| SPEC §N `SU-RESID-2`／`9A-UI` `:327-330` | **無** | 部分關閉／兩層＋metadata 刪節 |
| TODO Task 2.1 | **無** | 邊界算術 |
| TODO Task 2.2 | **無** | 已 SUPERSEDED（R21） |
| TODO Task 2.3 | **無** | SUPERSEDED BY Task 9.5＋單 TF 過渡 |
| TODO Task 3.1–3.3 | **無** | 無回退全量／單選之現行施工令 |
| TODO Task 4.1 `:410` | **無** | IC 路徑既有 `metadata.split_unify` 五鍵揭露（C-6），非 Phase 9A discarded 交付層 |
| TODO Task 9.1 `:454`／`:469` | **無** | 明寫兩層；metadata **不在**本 Task |
| TODO Task 9.2–9.5 | **無** | 與 SPEC 對讀一致 |
| TODO §E `SU-RESID-2` | **無** | 部分關閉；阻擋者 `9.2b`／`9.3` |
| TODO §E `SU-RESID-C5-TARGETS` | **無** | H2 已閉；19／10／4／15／29 自洽 |
| TODO §E **`SU-RESID-9A-UI` `:892`** | **是** | live「Phase 9A 交付至…→ `metadata.split_unify`」三層鏈 → `GROK-R25-P1-01` |
| diff 夾帶 | **無超範圍契約改動** | `git show 69947430` 之 SPEC／TODO 差＝H1 六處＋H2＋沿革（沿革不在審查範圍） |

### (3b)

有互斥 → 可直接貼入之修正字面（一次修訂兩處）：

**SPEC `:187`**（與 `:188` ② 同型標記）：

> 🔴 **v21 更正（R25）：下句之 producer→metadata 資料流交接與「整鏈」驗收屬 `SU-RESID-9A-UI` 殘留解除後才生效，不得列入本延伸當輪交付**——~~須定義 `discarded` 之 producer→metadata 資料流交接…驗收須為 producer→summary→metadata 整鏈測試~~。本延伸只驗 producer → `EventSplitPlan.summary` 兩層（與目標句／§V 一致）。字面保留供殘留解除時使用。

**TODO `:892` 括號鏈**（對齊 SPEC §N `:330`）：

> …`D-002` Phase 9A 交付至 producer 層（`build_event_keys` 回傳 ＋ `EventSplitPlan.summary` 鍵；🔴 **v21 更正（R25）**：原寫「~~producer 回傳 → `EventSplitPlan.summary` → `metadata.split_unify`~~」，與 SPEC §N 同名條目 v20 兩層交付及本殘留「metadata 層延後」自相矛盾）…

---

## 必答 4 — `M-SU-D2-03` 與 mutation／register 連動

### (4a)

**無不一致。**

- mutation 表實列仍 **40**（`M-SU-D2-01`..`40`）；條數宣稱「共 **40** 條」仍成立——改標「殘留期間無應紅」是**內容**變更，非刪列（同型＝`C5-28` 之 `—`＋`blocked-by`）。
- **C5 register 29 列逐列查 mutation 欄**：無任一列指向 `M-SU-D2-03`（正文命中僅 mutation 表 `:282`；HISTORY 除外）。
- `EventPipelineResult`（`pipeline.py:52-63`）註解欄位無 `metadata` ⇒ 改標「無應紅」為正確處置，非關掉該有的網。

### (4b)

N/A

---

## 必答 5 — `SU-RESID-C5-TARGETS` 數字一致性

### (5a)

**全部一致**（現行判準字面）：

| 數字 | SPEC | TODO |
|------|------|------|
| register 29 | C5-01..29 實列 29 | `:691`／`:705` |
| (甲) keyed 10 | — | `:692` |
| (乙) basename 4 | — | `:694` |
| (丙) NO-ANCHOR 15 | — | `:697` |
| 缺錨 19＝29−10 | — | `:706`／`:710`（H2 已改；刪節線保留舊「20」） |

無第三處 **live**「20 列」作為現行判準。TODO `:688` 之「20 列」屬 **v16 當時實測敘事**（`C5-25` 補錨前），非現行數字。

### (5b)

N/A

---

## 必答 6 — 可否進 Task 9.2b（B9C）

### (6a)

**不可以。** `GROK-R25-P1-01` 為跨檔契約互斥（SPEC §P live 祈使＋TODO §E live 三層鏈），須先一次文件修訂閉合並重簽後，方可領 impl token 進 `Task 9.2b`（B9C）。

### (6b)

最小閉合集合：**僅** `GROK-R25-P1-01`（SPEC `:187` ＋ TODO `:892` 兩處字面；貼入稿見 3b）。  
已檢查：H1 六處／H2 數字修補成立；`M-SU-D2-03`／register／40 條無連動問題；C5 數字 19／10／4／15／29 一致；舊 Task 2.x–4.1／9.2–9.5 無第二類 B9B 互斥；抽樣 pytest 3 passed＋1 xfailed。**不重開** `Task 9.2b`–`9.5` 設計。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：H1／H2 六＋一處已修；**殘留** SPEC `:187`＋TODO `:892` → P1。  
2. 漏項：H1 閉合漏同步（assumed 1 否證）。  
3. 不可測：無新增。  
4. 可疑 quant：不重開。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：本輪未改生產簽章。  
9. 測試品質：抽樣綠／預期 xfail。  
10. Agent 可執行：`:187`／`:892` 會誤導殘留／重讀 Task 9.1 者。  
11. 必要性／短命工：無本輪新增短命工。

---

## GROK-R25-P1-01

**斷言**: H1 六處修補後仍有兩處 live 字面把 `metadata` 層當本延伸交付／驗收義務：SPEC §P Task 9.1 `:187` 要求定義 producer→metadata 資料流交接並做「producer→summary→metadata 整鏈」驗收；TODO §E `SU-RESID-9A-UI` `:892` 寫 Phase 9A 交付鏈含 `metadata.split_unify`——皆與 v20 已定「只交兩層、metadata 入殘留」及 `EventPipelineResult` 無 `metadata` 欄互斥。

**碼證**: `sed -n '187p' docs/SPLITUNIFY_SPEC.D-002.md` 仍含「須定義…producer→metadata…整鏈」且無刪節線；`sed -n '892p' docs/SPLITUNIFY_TODO.md` 仍含「producer 回傳 → `EventSplitPlan.summary` → `metadata.split_unify`」；對照 SPEC `:330`／TODO `:454`／`:469` 已兩層。`venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; print(sorted(EventPipelineResult.__annotations__)); assert "metadata" in EventPipelineResult.__annotations__'` → 欄位無 metadata、**AssertionError**（rc=1）。
CODE-ANCHOR: docs/SPLITUNIFY_SPEC.D-002.md:187
MUTATION: venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; assert "metadata" in EventPipelineResult.__annotations__'

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R25-BRIEF.md#086baa8628f1; docs/SPLITUNIFY_SPEC.D-002.md#c12382d397d9; docs/SPLITUNIFY_TODO.md#b0db3a346d63

[BLOCKING] 信心度=High。同型「改 A 漏 B」：R24 修了 SPEC 六處與 TODO 數字，**未**改 §P `:187`（codex R24 斷言曾點名 handoff）與 TODO §E 同名殘留列。修法見必答 3b；一次文件修訂可關；不重開 9.2b 設計。

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: grok REJECTED 2026-09-14 sha256:c12382d397d96beb732e9514a6cb540519a7833c3921cd5d4bcfab66e1dfad05 task:20260911-SPLITUNIFY-B9-REVIEW-R25 — BLOCKED-BY: GROK-R25-P1-01
```

（舊戳記行已保留。）

---

VERDICT: blocked
BLOCKED-BY: GROK-R25-P1-01
CLOSED:

ASSUMPTIONS_VERIFIED: body hash c12382d3…；doc_format 兩份 rc=0；r23／r24 CLOSED；H1 六處＋H2 數字修補成立；assumed1 否證（:187＋:892）；assumed2／3 成立；不可進 B9C
TESTS_RUN: `reconcile_body_hash.sh` → c12382d3…；`doc_format_precheck` SPEC／TODO → rc=0；pytest 三節點 → 3 passed；opposite_sides → 1 xfailed；metadata reverse assert → rc=1
FAILURES_SEEN: none（review-only；metadata assert rc=1 為預期反例）
SCOPE_CHANGES: none（僅 SPEC 戳記區 append＋本交件）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r25-grok.md
STAMP_APPENDED: docs/SPLITUNIFY_SPEC.D-002.md（舊戳記保留；REJECTED）

STATUS: DONE
