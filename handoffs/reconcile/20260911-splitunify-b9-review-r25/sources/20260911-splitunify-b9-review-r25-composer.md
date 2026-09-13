# SPLITUNIFY b9 — review-r25（H1／H2 閉合再驗證 ＋ v20 重簽）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R25`  
**family**: composer  
**findings-round**: R25  
**審查標的**: commit `69947430`；current block＝`docs/SPLITUNIFY_SPEC.D-002.md` 之 `M-SU-D2-03` 列、`§P Task 9.1` 兩處、§V `Task 9.1` 尾句、§R 回退句、§N `SU-RESID-9A-UI`；`docs/SPLITUNIFY_TODO.md` 之 §E `SU-RESID-C5-TARGETS`  
**禁改碼**：review-only（戳記 append 除外）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: body sha256 `c12382d3…` | **fact-verified** | `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `c12382d397d96beb732e9514a6cb540519a7833c3921cd5d4bcfab66e1dfad05` |
| brief fact-verified: 兩份 `doc_format_precheck` rc=0 | **fact-verified** | 本輪重跑 → rc=0／rc=0 |
| brief fact-verified: 六路回歸 706 passed、1 xfailed | **fact-verified** | 六路 `-rxX`（見必答 1b）→ **706 passed, 1 xfailed** rc=0（66.10s） |
| brief assumed: SPEC metadata／三層字面六處已窮盡 | **fact-verified（SPEC 面）** | `grep -n '三層\|metadata\.split_unify.*交付\|移除上述三層' docs/SPLITUNIFY_SPEC.D-002.md` 正文命中皆帶刪節線或 v20 更正註 |
| brief assumed: TODO 面未查 metadata 當本批交付 | **否證成立** | 見 `COMPOSER-R25-P1-01`；TODO §E `SU-RESID-9A-UI` `:892` 仍 live 寫三層交付 |
| brief assumed: `M-SU-D2-03` 改標無應紅是正確處置 | **fact-verified** | `EventPipelineResult` 無 `metadata` 欄；判準同 `C5-28` |
| brief assumed: `SU-RESID-C5-TARGETS` 只改 20→19、同段其餘無需連動 | **fact-verified** | 同段 19／(甲)10／(乙)4／(丙)15 相加 29，與 register 列數一致；無第三處 live「20 列」 |

---

## 必答 1 — 反例重跑（§B8）

### (1a)

| 項目 | 判定 |
|------|------|
| `CODEX-R24-P1-01`（H1：metadata 層六處 SPEC 同步） | **CLOSED** |
| `CODEX-R24-P2-02`（H2：TODO `SU-RESID-C5-TARGETS` 20→19） | **CLOSED** |
| R23 本家 `COMPOSER-R23-P3-00` 必答 3 立場（舊段無 B9B 互斥） | **STILL-OPEN**（R24 已證 SPEC 面有漏；本輪再證 TODO §E 同名殘留仍三層字面） |

### (1b)

- **H1**：`grep -n 'v20 更正（R24' docs/SPLITUNIFY_SPEC.D-002.md` → `:188`（§P 鎖定三層刪節）、`:190`（回退兩層）、`:258`（§V 尾句兩層）、`:282`（`M-SU-D2-03` 無應紅）、`:323`（§R 兩層）、`:330`（§N `SU-RESID-9A-UI` 括號刪 metadata）；`venv/bin/python -c '…assert "metadata" in EventPipelineResult.__annotations__'` → **AssertionError** rc=1（預期）。
- **H2**：`grep -n '要動.*列已戳記' docs/SPLITUNIFY_TODO.md` → `:710` 為 **19** 列；`:706` 缺錨 **19** 列；無 live「要動 20 列」。
- **R23 立場重跑**：`grep -n 'producer 回傳.*summary.*metadata' docs/SPLITUNIFY_TODO.md` → `:892` **live 三層**（無刪節線／無 v20 更正）⇒ 與 SPEC §N `:330` 兩層定義互斥。

---

## 必答 2 — body `c12382d3…` 重簽

### (2a)

**REJECTED**

### (2b)

| ID | 阻擋項 | 一次修訂閉合 |
|----|--------|-------------|
| `COMPOSER-R25-P1-01` | TODO §E `SU-RESID-9A-UI` 仍把 `metadata.split_unify` 列為 Phase 9A 交付第三層 | 將 `:892` 之「`producer 回傳 → EventSplitPlan.summary → metadata.split_unify`」改為與 SPEC §N v20 同名條目一致：「`build_event_keys` 回傳 ＋ `EventSplitPlan.summary` 鍵」，原三層字面以刪節線保留並附 v20 更正註 |

---

## 必答 3 — 其他舊段落 B9B 互斥掃描（契約面強制）

### (3a)

**掃描命令與範圍**：

```bash
grep -nE '三層|metadata\.split_unify|本延伸交付|producer.*summary|12 鍵|13 鍵|16 鍵|單選|四者同時|逐 symbol 相加|feature_timeframe' docs/SPLITUNIFY_SPEC.D-002.md | grep -v HISTORY
grep -nE '三層|metadata\.split_unify|本延伸交付|producer.*summary|12 鍵|13 鍵|16 鍵|單選|四者同時|逐 symbol 相加' docs/SPLITUNIFY_TODO.md
grep -nE '^(### Task (2\.|3\.|4\.|9\.)|## §E)' docs/SPLITUNIFY_TODO.md
```

**SPEC 逐段**（正文，非本輪六處改動亦掃）：

| 段 | 互斥？ | 結論 |
|----|--------|------|
| `(5.4) 第三層｜偵察補列` | **否** | 消費面分類層級用語，非 Phase 9A 交付層數 |
| `§P Task 9.1` 目標句 `:177` | **否** | 已兩層＋v18 更正註 |
| `§P Task 9.1` metadata handoff `:187` | **否（殘留追溯）** | 整段上下文已標「隨 O1 移入 `SU-RESID-9A-UI`／不得列入當輪交付」；`:188` ② 明確 |
| `§P Task 9.2`–`9.5` | **否** | 無 live 三層／metadata 交付宣稱 |
| `§V Task 9.2`–`9.5` | **否** | 複合鍵／側別敘事與 B9B 一致 |
| `§N SU-RESID-2`／其他殘留 | **否** | 部分關閉＋`blocked-by` 與 B9B 現況一致 |
| `§N SU-RESID-9A-UI` `:330` | **否** | v20 已改兩層、metadata 刪節 |
| `§R` `:323` | **否** | v20 已兩層 |

**TODO 逐段**：

| 段 | 互斥？ | 結論 |
|----|--------|------|
| `Task 2.2` | **否** | 三處 `SUPERSEDED` |
| `Task 2.3` | **否** | `SUPERSEDED BY Task 9.5`＋單 TF 過渡註 |
| `Task 3.1`–`3.3` | **否** | 接線／fail-closed／event-study-only |
| `Task 4.1` `:410` | **否** | IC 路徑 `metadata.split_unify` 揭露（C-6），非 Phase 9A producer 交付層 |
| `Task 9.1` `:454`／`:469` | **否** | 明寫兩層交付、metadata 不在本 Task |
| `Task 9.2`–`9.5` | **否** | 與 SPEC §P／§V 對讀一致 |
| `§E SU-RESID-2` | **否** | 部分關閉，阻擋者 `9.2b`／`9.3` |
| `§E SU-RESID-C5-TARGETS` `:705-711` | **否** | 19／10／4／15 自洽（H2 已閉） |
| `§E SU-RESID-9A-UI` `:892` | **是** | live 寫「producer → summary → metadata」三層交付 ⇒ 見 `COMPOSER-R25-P1-01` |

### (3b)

除 `COMPOSER-R25-P1-01` 外無其他 live 互斥。掃描涵蓋 brief 指定之 `Task 2.x`／`3.x`／`4.1`／`9.x` 全段與 §E 全表；SPEC 另掃 `§P`／`§V`／`§N`／`§R` 與 `(5.x)` 關鍵字。歷史段「20 列」僅出現在 v16 敘事（`:688`／`:707` 帶更正註），非 live 判準。

---

## 必答 4 — `M-SU-D2-03` 與 mutation／register 連動

### (4a)

**無不一致**。`M-SU-D2-03` 仍佔 mutation 表第 3 行（條數宣稱 **40** ＝ `rg -c '\| \`M-SU-D2-'` 於 mutation 表區 `:278-319` 實列 40 行）；改標「殘留期間無應紅測試」與 `C5-28` 之 `—`＋`blocked-by` 同型。**C5 register 29 列逐列查 mutation 欄**：無任一列指向 `M-SU-D2-03`（`rg 'M-SU-D2-03' docs/SPLITUNIFY_SPEC.D-002.md` 僅命中 mutation 表 `:282` 與沿革）。

### (4b)

N/A

---

## 必答 5 — `SU-RESID-C5-TARGETS` 數字一致性

### (5a)

**全部一致**：TODO `:692-706`（10／4／15／29／19）；SPEC register 表 29 列（`C5-01`..`C5-29`）；無第三處 live「20 列」。

### (5b)

N/A

---

## 必答 6 — 可否進 `Task 9.2b`（B9C）

### (6a)

**不可以**——`COMPOSER-R25-P1-01` 為 SPEC／TODO 跨檔契約互斥，須先一次文件修訂閉合後重簽 v20 body。

### (6b)

最小閉合集合：`COMPOSER-R25-P1-01`（TODO §E `SU-RESID-9A-UI` `:892` 與 SPEC §N v20 同步為兩層交付字面）。H1／H2 修補已閉合；六路回歸 706+1xfail；`M-SU-D2-03`／register／數字三元組無連動問題。

---

## COMPOSER-R25-P1-01

**斷言**: `docs/SPLITUNIFY_TODO.md` §E `SU-RESID-9A-UI` 仍 live 宣稱 Phase 9A 交付含 `metadata.split_unify` 第三層，與 v20 SPEC §N 同名條目（兩層、metadata 已刪節）及 `Task 9.1` TODO `:454` 互斥，實作者讀 TODO 殘留表會誤把 metadata 層當本延伸已交付。

**碼證**: `grep -n 'SU-RESID-9A-UI' docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.D-002.md` → TODO `:892` 含「`producer 回傳 → EventSplitPlan.summary → metadata.split_unify`」；SPEC §N `:330` 已為「`build_event_keys` 回傳 ＋ `EventSplitPlan.summary` 鍵」且 metadata 刪節。`EventPipelineResult` 無 `metadata` 欄。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:892
MUTATION: venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; assert "metadata" in EventPipelineResult.__annotations__'

**來源摘要**: docs/SPLITUNIFY_TODO.md#b0db3a346d63; docs/SPLITUNIFY_SPEC.D-002.md#c12382d397d9

[BLOCKING] 信心度=High；同型第五次發作之 TODO 面漏同步（R24 已修 SPEC §N 六處、未修 TODO §E 同名條目）。修法：`:892` 改為與 SPEC §N `:330` 逐字對齊之兩層表述＋刪節線追溯；一次修訂可關。

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: composer REJECTED 2026-09-14 sha256:c12382d397d96beb732e9514a6cb540519a7833c3921cd5d4bcfab66e1dfad05 task:20260911-SPLITUNIFY-B9-REVIEW-R25 — BLOCKED-BY: COMPOSER-R25-P1-01
```

（舊戳記行已保留。）

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R25-P1-01
CLOSED: COMPOSER-R20-P1-01,COMPOSER-R20-P2-01

ASSUMPTIONS_VERIFIED: body hash c12382d3…；doc_format_precheck 雙檔 rc=0；706+1xfail；H1/H2 閉合；M-SU-D2-03/register/19-29 數字一致；TODO §E 三層字面為 live 互斥
TESTS_RUN: `reconcile_body_hash.sh` → c12382d3…；`doc_format_precheck` rc=0/0；六路 `pytest -q -rxX` → 706 passed 1 xfailed；metadata 反向 assertion rc=1
FAILURES_SEEN: none（review-only）
SCOPE_CHANGES: stamp append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記（brief 授權）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r25-composer.md

STATUS: DONE
