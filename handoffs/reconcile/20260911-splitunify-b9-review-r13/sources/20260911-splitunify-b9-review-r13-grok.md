# SPLITUNIFY b9 — stamp-r1 五條 finding 閉合再驗證（DOCROT 成效量測 R13）— grok

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R13`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R13-BRIEF.md`  
**findings-round**: R13  
**brief-kind**: review  
**審查標的**: `docs/SPLITUNIFY_TODO.md` §C-9 ＋ §B `B9A`–`B9F`；diff `87d38dd9`  
**禁改碼／禁改 SPEC／禁改 TODO**：本輪只產 review 檔。

---

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: SPEC 戳記已閉 → `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → PASS，三家 APPROVED，body sha256 `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77`，rc=0。

fact-verified: §C-9 mutation 完整 ID → `awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md | grep -oE 'M-SU-D2-[0-9]{2}' | sort -u | wc -l` ＝ **34**；`01`..`34` 逐號無缺。

fact-verified: 本家 stamp-r1 反例 `GROK-R1-P2-01` 已修 → Task 9.4「修改檔案」不再要求改 `types.ts:1582`／`:2257`；改寫為「事件路徑現無 typed `n_train` 欄；要 typed 面須新增事件摘要型別並具名」。`types.ts:1582` 仍屬 `CPCVPathResult`、`:2257` 仍屬 `MarginalICSection`、`EventAnalyzeResponse.summary`（`:3176`）仍為 `Record<string, unknown>`。

fact-verified: 家數活文（不含排除條件）→ `grep -nE '雙家族|兩家族|2 個正式' CLAUDE.md AGENTS.md .cursorrules docs/MULTI_AGENT_ORCHESTRATION.md docs/DEVELOPMENT_GUIDE.md docs/ROADMAP.md` 唯一命中＝ORCH:195 之**更正註記**（「本行原寫…兩家族…」），活文派工句（:194／:196）已改指向 §1。已關閉 epic 文件內「雙家族」屬歷史紀錄，forward-only 劃界成立。

fact-verified: `1 xfailed` 字面可機械判讀 → 實跑既有 xfail  
`venv/bin/python -m pytest -rxX -q tests/test_feature_factory_operators.py::test_rolling_aggregator_handles_duplicate_columns`  
→ summary 行 `======================== 1 xfailed, 1 warning in 3.33s =========================`（pytest 8.4.2）；僅 `-q` 同現該字面。

fact-verified: C5 register 計數 grep → `grep -cE '^\| `C5-[0-9]+`' docs/SPLITUNIFY_SPEC.D-002.md` ＝ **29**。TODO:630 內嵌之 markdown 跳脫形（`^\| \`C5-...`）在本機 BSD grep ERE 下亦回 29——跳脫層不阻機械驗收。

fact-verified: 刪／改名 node 之實測字面 ≠ TODO 所舉 `no tests ran` → 對尚不存在之  
`tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed`  
實跑得 `ERROR: not found`、`collected 0 items`、**rc=4**。正向門檻「輸出須含 `1 xfailed`」仍足以擋刪測；負向舉例字面不完整但**不使門檻失效** ⇒ 不另開 finding。

assumed（brief 指定攻）: Task 9.2a 之 `-rxX`＋`1 xfailed` 可機械判讀 → **成立**（見上 fact-verified）。  
assumed（brief 指定攻）: Task 9.3 之 C5 grep 跳脫後仍可複製執行 → **成立**（見上）。

---

## 必答

### (1a)(1b) 逐條重跑 stamp-r1 反例

| finding | 提出方 | 判定 | 重跑命令與觀測 |
|---|---|---|---|
| `CODEX-R1-P1-01` | codex | **CLOSED** | `grep -nE '雙家族|兩家族|2 個正式' CLAUDE.md AGENTS.md .cursorrules docs/MULTI_AGENT_ORCHESTRATION.md docs/DEVELOPMENT_GUIDE.md docs/ROADMAP.md` → 活文無「兩家族／雙家族」派工句；ORCH:194 已改「§1 現行分工行所列之全部審查家族」；唯一命中 :195＝更正註記。`DEVELOPMENT_GUIDE.md:59` 已改 pointer。 |
| `CODEX-R1-P1-02` | codex | **CLOSED** | `awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md \| grep -oE 'M-SU-D2-[0-9]{2}' \| sort -u \| wc -l` → **34**；無裸數字縮寫殘留於 mutation 自證段（`M-SU-D2-14`／`15`／`22` 等皆完整字面）。 |
| `CODEX-R1-P1-03` ／ `GROK-R1-P2-01` | codex／**grok** | **CLOSED** | `sed -n '1578,1586p;2239,2260p;3170,3180p' frontend/src/lib/types.ts` → 1582∈`CPCVPathResult`、2257∈`MarginalICSection`、3176=`summary: Record<string, unknown>`；`awk '/^### Task 9\.4/,/^### Task 9\.5/' docs/SPLITUNIFY_TODO.md` → 明示「本 Task 不動 `types.ts` 之既有介面」「不得去改 CPCV／MarginalIC」。錯錨已自「修改檔案」清單移除。 |
| `CODEX-R1-P1-04` | codex | **CLOSED** | Task 9.2a 驗證第 6 條逐字含 node id 與  
`venv/bin/python -m pytest -rxX "…::test_multi_feature_tf_opposite_sides_must_fail_closed"`  
⇒ `1 xfailed`；Task 9.3 指定 `handoffs/run_receipts/*-splitunify-task-9.3-register-rescan.txt` 且計數相等判準。既有 xfail 實跑確認 `1 xfailed` 字面（見 §0）。 |

### (2a)(2b) 批數

**(2a) 選 `B9A`–`B9F` 六批**（維持 stamp-r1 本家立場；不併 `B9D`+`B9E`）。

技術耦合：`B9B`（9.2+9.2a）不得拆；`B9D`（消費面防誤改）與 `B9E`（記帳／baseline／前端顯示）改動面不同、可並行但分 gate 縮小歸因；`B9F` 必須最後。

**(2b) 若選錯（併成五批）的可執行發現方式**

- 錯在 **`B9B` 被拆**：第二批前跑 `test_run_without_selected_timeframe_emits_all_feature_tf_rows` → `MergeError` 或同事件兩列 TF 碰撞。  
- 錯在 **`B9D`+`B9E` 併且未 rebase**：`test_tier_min_test_events_counts_unique_event_ids` 在 9.2a 去重未落地時可能假綠，合併後才暴露 1 事件×2 TF 繞過 `tier_min`。  
- 錯在 **`B9F` 非最後**：`python scripts/freeze_splitunify_golden.py` 後 §V 外部錨／側別與未完工行為不一致 → golden 整批紅。

### (3a)(3b) 是否重開已蓋章 SPEC 補 §V 三條

**(3a) 不值得。**

**(3b)** §C-9 已具名承接、足以「改壞會紅」：

| codex 主張 | §C-9 承接 |
|---|---|
| clusters remain event-level | Task 9.2a：`test_clusters_remain_event_level_when_multi_feature_tf` |
| purged／assignments 互斥 | Task 9.2b：`test_purged_and_assignments_event_id_disjoint`＋實作要點 6 |
| composite-key error message | Task 9.2a：`test_duplicate_composite_key_error_message_names_key_not_side`＋`test_duplicate_event_id_is_fail_closed` 之 `match=` 更新 |

重開 SPEC＝重新三家蓋章＋provenance／register-output 成本；上述測試網已在施工面擋住，無需為 §V 逐字複述付該成本。

### (4a)(4b) 可否領 impl token 進 Task 9.1

**(4a) 可以。**

**(4b) 本輪檢查**：

1. `reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0（三家 APPROVED）。  
2. 本家 `GROK-R1-P2-01` ＋ codex 四條修補皆重跑反例 → CLOSED。  
3. §C-9／`B9A`–`B9F` 存在；mutation 34/34；xfail／register 機械驗收字面可執行。  
4. `stampable_artifacts.txt` 加列 `docs/SPLITUNIFY_SPEC.D-002.md` 為完整路徑字面、無 `*`／目錄前綴／`..`；其餘 docs/ 受戳記檔不併入之殘留理由（body hash 未查證）成立。  
5. 前端真消費點：`EventTablesPanel.tsx:361` 仍讀 `s.n_train`／`s.n_test`／`s.n_purged`；六 vitest 中 27／30／28／24／14／capability:101 仍命中 fixture；**capability:29 現為「無 n_train」註解行**（非改欄即紅之 fixture）——觀測記入，不升 finding（:101 與另五檔仍構成網）。

---

## 攻擊面補答（brief 表「我沒查」）

| 面向 | 本輪結論 |
|---|---|
| 家數字面 | 活文完備；ORCH:195 註記＋已關閉 epic 歷史字面 → forward-only 成立 |
| Task 9.4 前端型別面 | **本 Task 不該存在 typed `n_train` 修改面**（summary＝`Record`）；修法正確 |
| 六批 vs 五批 | 六批；發現方式見 (2b) |
| §V 三條重開 | 不值得；§C-9 具名測試已承接 |
| stampable 白名單 | 加列合封閉性；殘留理由成立 |

---

## §1 必查（11 類；本輪範圍＝§C-9 修補閉合，非重審 SPEC）

1. 矛盾/互斥：無（批數／xfail／typed 面與 stamp-r1 修法一致）  
2. 漏項：無（五條修補皆落地）  
3. 不可測驗收：無（xfail／register 已機械化；`1 xfailed` 字面已實跑）  
4. 可疑 quant 假設：無（本輪不重審 SPEC 數值契約）  
5. 過度工程：無  
6. OOM/並行：無  
7. Cache：無  
8. API/型別：無新缺口（錯錨已刪）  
9. 測試品質：無阻擋項（capability:29 行號微漂見上，不擋）  
10. Agent 可執行性：無（Task 9.1 可領 token）  
11. 必要性/短命工：無  

## 被當成事實的未驗證假設（§0）

無殘留阻擋項。brief 兩條 assumed 皆已實跑否證風險（判準可執行）。

---

## GROK-R13-P3-00

**斷言**: 本輪逐項核對後無 finding；stamp-r1 本家 `GROK-R1-P2-01` 與同題修補均已關閉，§C-9 可支撐領 impl token 進 Task 9.1。

**碼證**: (1) `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → PASS rc=0，sha256 `06b2d4cb…`；(2) Task 9.4 現行文刪除 `types.ts:1582`／`:2257` 修改指令，改「不動既有介面」——`sed -n '1578,1586p;2250,2260p;3174,3177p' frontend/src/lib/types.ts` 仍證兩舊錨非事件批、`summary: Record<string, unknown>`；(3) `venv/bin/python -m pytest -rxX -q tests/test_feature_factory_operators.py::test_rolling_aggregator_handles_duplicate_columns` → summary 含 `1 xfailed`；(4) `grep -cE '^\| `C5-[0-9]+`' docs/SPLITUNIFY_SPEC.D-002.md` → 29；(5) mutation 完整 ID 計數 34。

**來源摘要**: docs/SPLITUNIFY_TODO.md#9cbdedd0a735

[P3] 信心度=High。sentinel＝零阻擋 finding；非空殼。DOCROT 摩擦候選＝0（無歷史段落點 finding）。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R1-P2-01

ASSUMPTIONS_VERIFIED: stamps rc=0；GROK-R1-P2-01 錯錨已刪且 types.ts 現況仍證舊錨非事件批；`1 xfailed` 字面（pytest 8.4.2）；C5 grep＝29（含 TODO 跳脫形）；mutation 34；家數活文無派工漂移；六批技術耦合
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → PASS rc=0；`venv/bin/python -m pytest -rxX -q tests/test_feature_factory_operators.py::test_rolling_aggregator_handles_duplicate_columns` → `1 xfailed` rc=0；missing-node 同 node id → `ERROR: not found` rc=4；`grep -cE '^\| `C5-[0-9]+`' docs/SPLITUNIFY_SPEC.D-002.md` → 29
FAILURES_SEEN: none（長跑 `test_fracdiff_truncation_invariant` 中途中止，改用輕量 xfail 取字面）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r13-grok.md

STATUS: DONE
