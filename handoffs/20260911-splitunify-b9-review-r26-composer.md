# SPLITUNIFY b9 — review-r26（J1 閉合再驗證 ＋ v21 重簽）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R26`  
**family**: composer  
**findings-round**: R26  
**審查標的**: commit `eac26bfe`；current block＝`docs/SPLITUNIFY_SPEC.D-002.md` 之 `§P Task 9.1` `:187`；`docs/SPLITUNIFY_TODO.md` 之 §E `SU-RESID-9A-UI` `:892`  
**禁改碼**：review-only（戳記 append 除外）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: body sha256 `755f3d53…` | **fact-verified** | `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f` |
| brief fact-verified: 兩份 `doc_format_precheck` rc=0 | **fact-verified** | 本輪重跑 → spec_rc=0／todo_rc=0 |
| brief fact-verified: 六路回歸 706 passed、1 xfailed | **未重跑**（brief VERIFY-EXEMPT:doc-example:brief-dispatch-time-premise；採 brief 前提） |
| brief assumed: 兩層契約已窮盡（主委三 token 掃） | **fact-verified（本輪換詞表複核）** | 見必答 3；無 live 互斥 |
| brief assumed: `:187` 刪節未失去兩層防假綠告誡 | **fact-verified** | 見必答 4；§V／TODO 仍具值相等＋wiring 要求 |
| brief assumed: `M-SU-D2-01`／`02` 應紅欄仍指向當輪測試 | **fact-verified** | 見必答 5；兩列皆指 summary 層、非 metadata |

---

## 必答 1 — 反例重跑（§B8）

### (1a)

| 項目 | 判定 |
|------|------|
| `COMPOSER-R25-P1-01`（TODO §E `SU-RESID-9A-UI` 三層交付字面） | **CLOSED** |

### (1b)

- `grep -n 'SU-RESID-9A-UI' docs/SPLITUNIFY_TODO.md` → `:892` 已為「`build_event_keys` 回傳 ＋ `EventSplitPlan.summary` 鍵」＋ v21 更正註，原三層字面在 `~~…~~` 刪節線內。
- `sed -n '187p' docs/SPLITUNIFY_SPEC.D-002.md` → 行首為 v21 更正（兩層、不得列入當輪交付），原 producer→metadata／整鏈祈使句在 `~~…~~` 內。
- `grep -n 'producer 回傳.*summary.*metadata' docs/SPLITUNIFY_TODO.md` → **零命中**（僅刪節線內容已不含 live 三層鏈）。
- `venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; assert "metadata" in EventPipelineResult.__annotations__'` → **AssertionError** rc=1（預期）。

---

## 必答 2 — body `755f3d53…` 重簽

### (2a)

**APPROVED**

### (2b)

N/A（無阻擋項）。J1 兩處修補與 `git show eac26bfe` 契約面 diff 一致；`§P :187` v21 更正與 `§N :330`／TODO `:892` 逐字對齊；`doc_format_precheck` 雙檔 rc=0。

---

## 必答 3 — 同義詞／同義結構強制掃描

### (3a)

**本輪詞表**（刻意避開主委已掃之 `metadata.split_unify`／`三層`／`整鏈`）：

`producer.*metadata`｜`context handoff`｜`完整記帳`｜`資料流交接`｜`end-to-end`｜`disclosure.*discarded`｜`終端可見.*交付`｜`孤立欄位`｜`手塞`｜`handoff`｜`producer→summary→metadata`｜`producer 回傳.*summary.*metadata`｜`完整資料流`｜`exact-key.*discarded`｜`split_unify.*discarded`

**掃描命令**：

```bash
WORDLIST='producer.*metadata|context handoff|完整記帳|資料流交接|end-to-end|disclosure.*discarded|終端可見.*交付|孤立欄位|手塞|handoff|producer→summary→metadata|producer 回傳.*summary.*metadata|完整資料流|exact-key.*discarded|split_unify.*discarded'
for f in docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md; do
  awk '/^## 沿革與追溯索引$/{exit} /HISTORY-BEGIN/{skip=1} /HISTORY-END/{skip=0;next} skip{next} {print NR":"$0}' "$f" | grep -nE "$WORDLIST"
done
```

**SPEC 逐段判定**（正文，排除沿革）：

| 段 | 互斥？ | 結論 |
|----|--------|------|
| `§P Task 9.1` 標題「完整資料流契約」`:176` | **否** | 任務名，目標句 `:177` 已明寫兩層 |
| `§P :177` 目標句 | **否** | live 兩層；三層／完整記帳在 v18 更正刪節 |
| `§P :187` v21 更正 | **否** | live 為更正註＋刪節；`producer→metadata`／`孤立欄位`／`手塞` 均在 `~~…~~` |
| `§P :188` exact-key 段 | **否** | v20 更正＋「整段移入 `SU-RESID-9A-UI`」；`build_split_unify_disclosure` 為殘留施工面說明 |
| `§P :189` 終端可見性 | **否** | `blocked-by` 殘留，非當輪交付宣稱 |
| `§V Task 9.1` `:258` | **否** | live 斷言為 summary **值相等**；metadata／孤立單測手塞句在「移出當輪驗收」刪節區 |
| `§N SU-RESID-9A-UI` `:330` | **否** | v20 兩層＋metadata 刪節 |
| `(5.4) 第三層` `:80` | **否** | 消費面分類層級，非 Phase 9A 交付層數 |
| `Task 9.2b` 三段式 `:219` 等 | **否** | 側別判準，與 discarded 層數無關 |

**TODO 逐段判定**：

| 段 | 互斥？ | 結論 |
|----|--------|------|
| `Task 9.1` 標題／`:452-476` | **否** | 明寫兩層；`:469-471` 禁止改 disclosure |
| `Task 9.1` 驗收 `:481-498` | **否** | 值相等＋wiring 測試，非 metadata 整鏈 |
| `§E SU-RESID-9A-UI` `:892` | **否** | v21 已改兩層（J1 閉合） |
| `ic_filter_orchestrator` 其他命中 | **否** | B3／B4 接線敘事，非 9A 三層交付 |

### (3b)

**無 live 互斥**。詞表涵蓋 r24／r25 漏網類型（`資料流交接`／`孤立欄位`／`手塞`／`context handoff`／`producer→summary→metadata` 鏈），且掃描排除沿革段；所有命中皆為 (a) v18–v21 更正註、(b) 刪節線內追溯、(c) 與 B9B／9.2b 無關之他域用語。

---

## 必答 4 — `:187` 刪節後是否失去兩層防假綠告誡

### (4a)

**否**——未失去在兩層交付下仍必要的施工指示。

### (4b)

理由：被刪節的「孤立欄位單測／手塞 builder 鍵」警告針對 **metadata 層**；兩層範圍內之等價防假綠仍由下列 live 條文覆蓋：

- SPEC §V `:258`：`ASSERT EventSplitPlan.summary 帶 discarded_rows_by_feature_tf 且**值與 producer 回傳相同**`（明禁只驗鍵）。
- TODO `Task 9.1` `:485-490`：具名測試 `test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer`（值相等）＋ `test_splitunify_wiring_discarded_rows_reaches_summary`（pipeline 省略 kwargs 即紅）。
- mutation `M-SU-D2-01`／`M-SU-D2-02` 應紅欄仍指向 summary 鍵／值斷言（見必答 5）。

---

## 必答 5 — `M-SU-D2-01`／`M-SU-D2-02` 應紅欄

### (5a)

**兩列皆無問題**——應紅欄仍指向當輪兩層測試，未指向已移出之 metadata 斷言。

### (5b)

查法：`sed -n '280,282p' docs/SPLITUNIFY_SPEC.D-002.md`

| ID | 應紅欄 | 判定 |
|----|--------|------|
| `M-SU-D2-01` | `Task 9.1` 之 summary 鍵斷言 | **當輪有效**（producer→summary 第一層） |
| `M-SU-D2-02` | `Task 9.1` 之 summary 鍵與**值**斷言（`test_splitunify_derive.py`） | **當輪有效**（第二層值相等；非 disclosure exact-key） |

對照 `M-SU-D2-03`：應紅已改「殘留期間無應紅測試」；`01`／`02` 未跟進錯指 metadata，無連動缺陷。

---

## 必答 6 — 可否進 `Task 9.2b`（B9C）

### (6a)

**可以**——無 BLOCKING。

### (6b)

已檢查：J1 兩處閉合（必答 1）；v21 body hash 與 diff 一致（必答 2）；換詞表全檔掃無 live 互斥（必答 3）；兩層防假綠仍由 §V／TODO／mutation 覆蓋（必答 4）；`M-SU-D2-01`／`02` 應紅有效（必答 5）；`SU-RESID-C5-TARGETS` 獨立抽驗——TODO `:691-711` 為 10／4／15／29／19 自洽，與 SPEC register 29 列一致。

---

## COMPOSER-R26-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂的 finding；J1 修補已閉合、v21 body 可重簽。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f` rc=0；`grep -n 'v21 更正（R25' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` → SPEC `:187`、TODO `:892`；換詞表掃描（必答 3 命令）正文無 live 三層/metadata 交付互斥；`venv/bin/python -c '…EventPipelineResult…metadata…'` → rc=1。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#755f3d53c1f3; docs/SPLITUNIFY_TODO.md#6b825499

doc-literal-only；信心度=High。J1 兩處 v21 更正與 §N／§V 同向；`M-SU-D2-01`／`02` 與 register 條數無連動問題。

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: composer APPROVED 2026-09-14 sha256:755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f task:20260911-SPLITUNIFY-B9-REVIEW-R26
```

（舊戳記行已保留。）

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R25-P1-01

ASSUMPTIONS_VERIFIED: body hash 755f3d53…；doc_format_precheck 雙檔 rc=0；COMPOSER-R25-P1-01 閉合；換詞表掃描無 live 互斥；兩層防假綠仍由 §V／TODO 覆蓋；M-SU-D2-01/02 應紅有效；C5-TARGETS 10/4/15/29/19 自洽
TESTS_RUN: `reconcile_body_hash.sh` rc=0；`doc_format_precheck` rc=0/0；metadata 反向 assertion rc=1；換詞表 awk+grep 掃描（必答 3）
FAILURES_SEEN: none
SCOPE_CHANGES: stamp append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記（brief 授權）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r26-composer.md

STATUS: DONE
