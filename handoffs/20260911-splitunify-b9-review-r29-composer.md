# SPLITUNIFY b9 — review-r29（N1–N4 閉合再驗證 ＋ v23 重簽）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R29`  
**family**: composer  
**findings-round**: R29  
**brief-kind**: review  
**審查標的**: commit `ddcd66f3`；current block＝N1–N4（`handoffs/reconcile/20260911-splitunify-b9-review-r28/synth.md`）  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（戳記 append 除外）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 六路 732 passed | **fact-verified（子集）** | 本輪 `derive`＋`wiring`＋`golden` → **140 passed** rc=0；全六路未重跑（brief VERIFY-EXEMPT） |
| brief fact-verified: doc_format_precheck 雙檔 rc=0 | **fact-verified** | 本輪複驗 rc=0/0 |
| brief fact-verified: 主委四探針 | **fact-verified（本家重跑）** | 見必答 1b 四探針；輸出摘要在 `scratchpad/r29_probe_output.txt` |
| brief fact-verified: r28 `state=CLOSED` | **未驗證** | 本輪未跑 `debt_ledger.sh` |
| brief assumed 1: N1 顯式具名與 codex 原修法等效 | 見必答 3(3a)① | |
| brief assumed 2: N3 第二欄消除共因 | 見必答 3(3a)② | |
| brief assumed 3: N2 SPEC 錨縮小攻擊面 | 見必答 3(3a)③ | |
| brief assumed 4: N4 已窮盡同型 | 見必答 3(3a)④／必答 4 | |

---

## 必答 1 — 重跑 review-r28 反例（§B8）

### (1a)

| 項目 | 判定 |
|------|------|
| `COMPOSER-R27-P2-01`（r28 本家唯一反例；M9 四處 9.2b 前快照） | **CLOSED**（v23 未回退） |
| codex 四探針（N1–N4 閉合驗證；非本家 finding，brief 要求重跑） | **CLOSED** |

### (1b)

**`COMPOSER-R27-P2-01`（M9 仍關）**

```bash
rg -n 'decision_at_ms' momentum/Analysis/event_samples/split_projection.py | wc -l
# → 18

rg -n '現況碼證|現行碼在此案例|現行碼會給' docs/SPLITUNIFY_SPEC.D-002.md
# → :216/:268/:312 命中皆在 v22/v23 刪節線或 mutation 表，非 live 施工句
```

**探针 ①（N1 未具名改值）** — `python scratchpad/r29_composer_probes.py p1`

```text
GOLDEN REFUSE: --write 會改動既有頂層鍵之**值**：['g4_per_symbol_n'] …
PROBE1_RC 1
```

**探针 ②（缺 SPEC 錨）** — `python scratchpad/r29_composer_probes.py p2`

```text
GOLDEN V8 ANCHOR MISSING: SPEC §V 缺（或有多於一個）逐字 `V8_BASELINE_SHA256=…`
PROBE2_RC 1
```

**探针 ③（v8 write-once）** — `python scratchpad/r29_composer_probes.py p3`

```text
GOLDEN V8 REFUSE: splitunify_golden.v8.json 已存在——v8 基準是 write-once …
PROBE3_RC 1
```

**探针 ④（+1 ms 時刻）** — `python scratchpad/r29_composer_probes.py p4`

```text
✗ G-4e（錨點時刻對帳）: tr0: 人手=1700000000000 實際=1700000000001
…（13 筆全紅）
G-4e FAIL：人手錨點時刻與 fixture 實際值不符（整批位移在此擋下）
PROBE4_RC 1
```

---

## 必答 2 — v23 body 重簽

### (2a)

**APPROVED**（body `52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d`）。

### (2b)

N/A。

---

## 必答 3 — 四條 assumed

### (3a)

① **N1「顯式具名」與 codex 原修法「任一值改變即 fail-closed」等效** → **不成立（字面）**；**可實作且機械閘有效（就攻擊向量）**。

- 與 codex 逐字修法**不等價**：正當重凍（例如新增 `bnd_shift` 連帶改既有鍵值）仍須 `--accept-value-changes` 逐一具名——這是 r28 主委具名偏離，理由成立（「永遠不得改」會讓正當重凍不可能）。
- **brief 直接攻擊面（習慣性列全鍵）**：`python scratchpad/r29_composer_probes.py n1` → 列全 15 鍵時 `GOLDEN REFUSE: --accept-value-changes 列了未實際改變的鍵 [...]`、`N1_BYPASS_RC 1`。**寬鬆授權繞法不成立**；`:627-632` 之 `_stale_allow` 閘有效。
- 靜默改值：探针 ① 已擋。

② **N3 第二欄人手判準已消除共因** → **部分成立**。

- **已消除**：`decision_at_ms` 整批 +1 ms 而 `expected_side` 不變 ⇒ 探针 ④ 轉紅（r28 攻擊向量已關）。
- **殘餘共因（誠實邊界）**：`_hand_decision` 與 `_feature_index()` 仍共用 `BASE`／`H1`（`:57-58`、`:145-151`）。`python scratchpad/r29_composer_probes.py n3` → 兩者同移時 G-4e 仍綠，但 `GOLDEN MISMATCH: 29 處`、`N3_SHIFT_RC 1`——**意圖性 fixture 大修仍須走 `--write` 且逐鍵具名**，非靜默漂移。碼中 `:139-144` 已具名此限。

③ **N2 錨點移入 SPEC 後攻擊面縮小** → **部分成立**。

- **改善**：`grep V8_BASELINE_SHA256 scripts/freeze_splitunify_golden.py` 僅 regex／註解；`test_v8_anchor_lives_in_spec_not_in_helper` PASS；缺錨探针 ② 轉紅；write-once 探针 ③ 轉紅。
- **未消除**：同一 commit 仍可同時改 SPEC 錨行與 helper——與 r27「改 helper 常數」同型的人為審查面，但**多了一層**（SPEC diff 可見 64-hex、v8 不可 `O_EXCL` 重建、三層 digest 比對）。判定：**比 r27 小、非零**；不足以阻擋 B9D。

④ **N4 修補已窮盡該類** → **成立（審查範圍內）**。必答 4 掃描無第九處 live 互斥。

### (3b)

無需新修法。① 之偏離已有 `_stale_allow` 補強；②③ 殘餘已碼內具名，屬散文紀律／審查面，非 B9D 阻擋項。

---

## 必答 4 — 契約面改動後強制掃描（同型第九次）

### (4a)

**本輪詞表**（避開 r26 metadata、r27 decision、r28 per-cutoff、codex r24 大表）：

`train_cutoff|per-cutoff|第四條分支|界外.*train|界外.*test|asof|ffill|nearest|row_index_local.*決定|集合判定.*cutoff|split_label.*cutoff|cutoff.*split_label|不在.*index.*purged`

**命令**：

```bash
WORDLIST='train_cutoff|per-cutoff|第四條分支|界外.*train|界外.*test|asof|ffill|nearest|row_index_local.*決定|集合判定.*cutoff|split_label.*cutoff|cutoff.*split_label|不在.*index.*purged'
for f in docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md; do
  echo "=== $f ==="
  awk '/^## 沿革與追溯索引$/{exit} /HISTORY-BEGIN/{skip=1} /HISTORY-END/{skip=0;next} skip{next} {print NR":"$0}' "$f" | grep -nE "$WORDLIST" || echo "(no hits)"
done
```

**SPEC 逐段**（命中 5 處）：

| 行 | live 互斥？ | 結論 |
|----|------------|------|
| `:216-218` | 否 | v22 更正＋刪節；現行為事件級 `decision_at_ms` |
| `:221` | 否 | 三段式設計 rationale；步驟 0 ④ 負責界外 raise |
| `:231` | 否 | 「不可做」禁止 per-cutoff，與契約一致 |
| `:268` | 否 | v22 更正刪節內舊敘述 |
| `:308` M-SU-D2-22 | 否 | mutation 目錄，非施工指令 |

**TODO 逐段**（命中 11 處）：

| 行 | live 互斥？ | 結論 |
|----|------------|------|
| `:213` | 否 | Task 2.2 現行段：界外 raise、非第四條分支 |
| `:218-221` | 否 | SUPERSEDED 刪節內舊 per-cutoff |
| `:246-248` | 否 | SUPERSEDED ＋現行 raise 句 |
| `:276-278` | 否 | N4 修法後之 live 正句（~~purged~~ ⇒ raise） |
| `:623-634` | 否 | Task 9.2b 現行；禁止第四條分支 |
| `:910` SU-RESID-2 | 否 | 狀態表；與 9.2b 一致 |

**同型第九次**：**未發作**。

**誠實邊界**：`docs/SPLITUNIFY_SPEC.md:480` 仍有舊句「事件不在 feature_index ⇒ purged」，但 brief 明定**不在審查範圍**（非 D-002／TODO）。

### (4b)

N/A。

---

## 必答 5 — 可否進 `Task 9.3`（B9D）

### (5a)

**可以**——N1–N4 閉合探针全綠；v23 body APPROVED；無 BLOCKING finding。

### (5b)

已檢查：r28 本家反例仍 CLOSED；四探针重跑（必答 1b）；四 assumed 攻擊（必答 3，含 N1 全鍵繞法否證）；換詞表全檔掃（必答 4）；`git show ddcd66f3` 契約面僅 N1–N4（SPEC §V 錨／G-4e、TODO 邊界②、freeze 腳本、golden 測試）；140 pytest + `GOLDEN OK`。**未覆蓋**：v8 首次 `O_EXCL` 建立成功半徑（僅測已存在拒絕，`test_v8_baseline_creation_is_write_once`）——誠實邊界，不阻擋 B9D。

---

## COMPOSER-R29-P3-00

**斷言**: 本輪逐項核對後無 finding；N1–N4 閉合探针全 CLOSED，v23 body 可重簽。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d` rc=0；`pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py tests/momentum/Analysis/test_splitunify_golden.py -q` → **140 passed** rc=0；`python scripts/freeze_splitunify_golden.py` → `GOLDEN OK` rc=0；四探针 `python scratchpad/r29_composer_probes.py all` → PROBE1-4 皆 rc=1、N1 全鍵繞法 rc=1；換詞表 awk+grep（必答 4）無第九處 live 互斥。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#52efba2e077a; handoffs/reconcile/20260911-splitunify-b9-review-r28/synth.md#ddcd66f3

doc-literal-only；信心度=High。assumed ① 與 codex 字面不等價但機械閘可證；②③ 殘餘共因／同 commit 攻擊面已碼內具名，不升級為 P1。

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: composer APPROVED 2026-09-14 sha256:52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d task:20260911-SPLITUNIFY-B9-REVIEW-R29
```

（舊戳記行已保留。）

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R27-P2-01

ASSUMPTIONS_VERIFIED: body hash 52efba2e…；doc_format 0/0；四探针 + N1 全鍵繞法 + N3 BASE/H1 移位；140 pytest + GOLDEN OK；換詞表無第九處；ddcd66f3 無夾帶
TESTS_RUN: `reconcile_body_hash.sh` rc=0；`doc_format_precheck.sh` SPEC/TODO rc=0/0；`pytest …derive+wiring+golden… -q` → 140 passed；`freeze_splitunify_golden.py` → GOLDEN OK；`scratchpad/r29_composer_probes.py all`
FAILURES_SEEN: none
SCOPE_CHANGES: stamp append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記（brief 授權）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r29-composer.md

STATUS: DONE
