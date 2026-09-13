# SPLITUNIFY b9 — review-r23（F1–F3 閉合再驗證 ＋ v19 重簽）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R23`  
**family**: composer  
**findings-round**: R23  
**審查標的**: commit `4ee9632b`；current block＝`docs/SPLITUNIFY_SPEC.D-002.md` §P `Task 9.1` 交付 bullet 與 §N `SU-RESID-2`；`docs/SPLITUNIFY_TODO.md` §E `SU-RESID-2` 列與 `Task 2.3` golden 段  
**禁改碼**：review-only（戳記 append 除外）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: body sha256 `1b0890e3…` | **fact-verified** | `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7` |
| brief fact-verified: 兩份 `doc_format_precheck` rc=0 | **fact-verified** | 本輪重跑 → rc=0／rc=0 |
| brief fact-verified: 六路回歸 706 passed、1 xfailed | **fact-verified** | 六路 `-rxX`（見必答 1b）→ **706 passed, 1 xfailed** rc=0（66.07s） |
| brief assumed: `SU-RESID-2` 阻擋者恰為 `Task 9.2b`＋`9.3` 兩項 | **fact-verified** | 見必答 4；`Task 9.4`／`9.5` 屬可見性／golden，非該殘留原文之「下游消費」範圍 |
| brief assumed: `Task 2.3`「單 TF 下仍成立」需改條件式 | **fact-verified（否）** | 見必答 5；現行已含 `SUPERSEDED BY Task 9.5`＋B9B 刻意未動 golden＋過渡狀態說明，足夠 |

---

## 必答 1 — 本家 R22 反例重跑（§B8）

### (1a)

| 項目 | 判定 |
|------|------|
| `COMPOSER-R20-P1-01`（xfail 錨點測試存在且機械驗收） | **CLOSED** |
| `COMPOSER-R20-P2-01`（多 symbol 三計數具名測試） | **CLOSED** |
| R22 本家必答 3（`SU-RESID-2` 應標「已關閉」） | **CLOSED**（`CODEX-R22-P1-01` 已改為「部分關閉」；TODO §E 與 SPEC §N 已同步，本家 r22 立場撤回） |
| R22 本家必答 2（`Task 2.3` 無需 SUPERSEDED） | **CLOSED**（`CODEX-R22-P1-02` 已在 `Task 2.3` 三處標 `SUPERSEDED BY Task 9.5`） |
| R22 本家必答 4（SPEC 非第四次同形互斥） | **CLOSED**（`CODEX-R22-P1-03` 已修 §P metadata bullet 與 §N 過期同步句；SPEC 進 v19） |

### (1b)

- **R20-P1-01**：`venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 xfailed** rc=0。
- **R20-P1-01（--runxfail）**：`venv/bin/python -m pytest --runxfail "…::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 failed**，`DID NOT RAISE AlignmentViolationError`（預期；9.2b 未實作）。
- **R20-P2-01**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py::test_multi_symbol_branch_summary_counts_are_named` → **1 passed** rc=0。
- **F1 閉合**：`grep -n "部分關閉" docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.D-002.md` → TODO §E `:889`、SPEC §N `:327` 皆為「部分關閉」且阻擋者具名 `Task 9.2b`／`9.3`。
- **F2 閉合**：`grep -n "SUPERSEDED BY \`Task 9.5\`" docs/SPLITUNIFY_TODO.md` → `:283`（`Task 2.3` G-3b 段）；三處字面含 B9B 單 TF 過渡註記。
- **F3 閉合**：`grep -n "v19 更正（R22 \`CODEX-R22-P1-03\`）" docs/SPLITUNIFY_SPEC.D-002.md` → `:186`（§P metadata bullet 刪節線註記）、`:327`（§N 同步句更正）；`grep -n "metadata.split_unify.*擴充" docs/SPLITUNIFY_SPEC.D-002.md` → 僅 `:185` 刪節線內，附「不得據以實作」。

---

## 必答 2 — body `1b0890e3…` 重簽

### (2a)

**APPROVED**

### (2b)

N/A（無阻擋項）

---

## 必答 3 — 其他舊段落 B9B 互斥掃描（契約面強制）

### (3a)

**掃描範圍與命令**：

```bash
grep -nE '^(### Task (2\.1|2\.3|3\.|4\.|5\.)|SUPERSEDED|12 鍵|13 鍵|16 鍵|單選|必傳|四者同時|逐 symbol 相加|feature_timeframe)' docs/SPLITUNIFY_TODO.md
grep -nE 'metadata\.split_unify|12 鍵|13 鍵|16 鍵|單選|必傳|四者同時|逐 symbol 相加' docs/SPLITUNIFY_SPEC.D-002.md | grep -v HISTORY
```

**逐段結論**（正文，不含 `HISTORY-BEGIN..END`／「沿革」）：

| 段 | B9B 互斥？ | 說明 |
|----|-----------|------|
| `Task 2.1` | **否** | 僅 canonical boundary；不涉及複合鍵／summary 鍵集 |
| `Task 2.2` | **否** | 三處已 `SUPERSEDED`（`:225`／`:242`／`:265`） |
| `Task 2.3` | **否** | G-3b 已 `SUPERSEDED BY Task 9.5`（`:283-288`）；舊字面保留＋過渡註記 |
| `Task 3.1` | **否** | 接線／`split_events` 退場；無 schema 舊契約 |
| `Task 3.2` | **否** | 多 symbol fail-closed 敘事；與 B9B 多 TF 行粒度不衝突 |
| `Task 3.3` | **否** | event-study-only 分支 |
| `Task 4.1` | **否** | `metadata.split_unify` 揭露；不涉及 `assignments` 欄集 |
| SPEC §P `Task 9.2` `:196-203` | **否** | **改前碼證＋施工清單**敘事（B9B 已完工）；非 live 雙真相 |
| SPEC §P `Task 9.1` `:187-190` | **否（殘留追溯）** | metadata 交接段已標「移入 `SU-RESID-9A-UI`／不得列入當輪交付」；`:190`「三層」為回退追溯字面，doc-literal-only |

### (3b)

**無**需再貼 SUPERSEDED 之互斥處。掃描涵蓋 brief 指定之 `Task 2.1`／`2.3`／`3.1`–`3.3`／`4.1` 全段，加上 grep 全檔關鍵字；命中之 `12 鍵`／`單選`／`四者同時` 皆已在 `Task 2.2` SUPERSEDED 或 `Task 9.2` 改前碼證段內，且附「不得據以實作」。

---

## 必答 4 — `SU-RESID-2` 阻擋者清單

### (4a)

**兩項**（非四項）。`Task 9.4`（顯示／計數可見性）與 `Task 9.5`（golden 擴維）雖受複合鍵影響，但屬**終端可見性**與**基準檔**工作，不是 `SU-RESID-2` 原文「複合鍵要連 `EventSplitPlan` **下游一起改**」所指之生產消費面與側別錨定；`9.4` 另列 `SU-RESID-9A-UI` 殘留，`9.5` 在依賴序末端且 brief 明禁重開設計。

### (4b)

可直接貼入之阻擋者清單（與現行 TODO §E／SPEC §N 一致）：

```markdown
**尚未關閉者**＝
1. **側別錨定** — `Task 9.2b`（`D-002-C3` (3.1)(3.2) 之唯一施工落點；現況 `split_projection.py` 仍以 `feature_cutoff_ms` 判側）
2. **下游消費面** — `Task 9.3`（`D-002-C5` register 九處逐處 `(event_id, feature_timeframe)` 處置）

**為何現在不做**：`blocked-by:Task 9.2b／9.3 尚未實作` — 依賴序 `9.2a → 9.2b → 9.3`，不得跳。
```

---

## 必答 5 — `Task 2.3`「單 TF 下仍成立」註記

### (5a)

**不需要**再改成額外條件式寫法。

### (5b)

N/A。現行 `:283-288` 已同時具備：①`SUPERSEDED BY Task 9.5`（擴維後須複合鍵集合比對）②「B9B 刻意未改 golden／凍結腳本維持單一 feature TF」③「跨批過渡狀態而非現行缺陷」。再加「一旦擴維即失效」屬同義重複，無阻擋價值。

---

## 必答 6 — 可否進 `Task 9.2b`（B9C）

### (6a)

**可以進 `Task 9.2b`（批次 B9C）**。無 BLOCKING finding。

### (6b)

已檢查：F1–F3 修補逐條閉合；§P `Task 9.1` 與 §V `Task 9.1` 交付層皆為「producer → summary **兩層**」（`grep` 無第三處 live 互斥）；TODO／SPEC `Task 9.2b` 三段式判準逐句對讀一致；六路回歸 **706 passed、1 xfailed**；`doc_format_precheck` 雙檔 rc=0；body hash 與 brief 一致；commit `4ee9632b` 之契約 diff 僅觸及 F1–F3 三條（另含 `HANDOFF`／`docs/site`／`白話說明` 夾帶，不在審查範圍、不阻擋）。

---

## 攻擊面補充

| 面向 | 結論 |
|------|------|
| §P vs §V `Task 9.1` 第三處互斥 | **無** — v19 已刪節 metadata 交付半句；§V `:258` 與 §P `:177` 皆兩層 |
| §N 其餘殘留（`SU-RESID-9A-UI`／`C5-TARGETS` 等） | **未落後於 B9B** — 狀態與 `blocked-by` 理由仍成立 |
| diff 夾帶 | `4ee9632b` 除 SPEC／TODO 外亦改 `HANDOFF.md`、`docs/site/*`、`白話說明/*`；契約三條僅在允許檔 |

---

## COMPOSER-R23-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂之 finding；F1–F3 修補已閉合，v19 body 可重簽，可進 `Task 9.2b`。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7`；`venv/bin/python -m pytest -q -rxX tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py` → **706 passed, 1 xfailed** rc=0；`grep -n "部分關閉" docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.D-002.md` → TODO `:889`、SPEC `:327` 同步。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#1b0890e367ab

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: composer APPROVED 2026-09-14 sha256:1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7 task:20260911-SPLITUNIFY-B9-REVIEW-R23
```

（舊戳記行已保留。）

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R20-P1-01,COMPOSER-R20-P2-01

ASSUMPTIONS_VERIFIED: body hash 1b0890e3…；doc_format_precheck 雙檔 rc=0；706+1xfail 六路回歸；F1–F3 閉合；SU-RESID-2 阻擋者兩項；Task 2.3 註記不需再加條件式；舊段無 B9B 互斥
TESTS_RUN: `reconcile_body_hash.sh` → 1b0890e3…；`doc_format_precheck` SPEC/TODO rc=0；六路 `pytest -q -rxX` → 706 passed 1 xfailed；xfail 錨點 1 xfailed；--runxfail DID NOT RAISE AlignmentViolationError
FAILURES_SEEN: none（review-only）
SCOPE_CHANGES: stamp append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記（brief 授權）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r23-composer.md

STATUS: DONE
