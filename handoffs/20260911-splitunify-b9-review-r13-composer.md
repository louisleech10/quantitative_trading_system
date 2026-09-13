# SPLITUNIFY b9 — stamp-r1 五條 finding 閉合再驗證（DOCROT 成效量測 R13）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R13`  
**family**: composer  
**findings-round**: R13  
**審查標的**: `docs/SPLITUNIFY_TODO.md` §B `B9A`–`B9F` ＋ §C-9；本輪 diff `87d38dd9`（`SPLITUNIFY_TODO.md`／`ORCH`／`DEVELOPMENT_GUIDE.md`／`CLAUDE.md`／`stampable_artifacts.txt`）  
**禁改碼**：本輪只產 review 檔。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: SPEC 戳記 rc=0 | **fact-verified** | `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → 三家 APPROVED、body sha256 `06b2d4cb…` rc=0 |
| brief fact-verified: §C-9 mutation 34/34 | **fact-verified** | `awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md \| grep -oE 'M-SU-D2-[0-9]{2}' \| sort -u \| wc -l` → **34**；`M-SU-D2-01`..`34` 逐號無缺 |
| brief fact-verified: §C-9 pytest 路徑全存在 | **fact-verified** | 12 條 `test -f` 皆 rc=0（見必答 4b） |
| brief assumed: Task 9.2a `-rxX` 輸出可機械判讀 `1 xfailed` | **fact-verified（格式面）** | `venv/bin/python -m pytest -rxX -q tests/test_feature_factory_operators.py::test_rolling_aggregator_handles_duplicate_columns` → 摘要行 `1 xfailed in 3.00s`（子串 `1 xfailed` 命中）；pytest **8.4.2**。該 node 尚未加 xfail（impl 前預期），故未對目標 node 實跑 |
| brief assumed: Task 9.3 register grep 可複製貼上 | **fact-verified** | 自 TODO 字面複製 `grep -cE '^\| \`C5-[0-9]+\`' docs/SPLITUNIFY_SPEC.D-002.md`（渲染後即 `grep -cE '^\| `C5-[0-9]+`' …`）→ **29** rc=0；receipt 側 `grep -cE '^C5-[0-9]+ '` 探針 → 可計數 |

---

## 必答 1 — stamp-r1 五條修補閉合（composer 獨立複驗）

### (1a) 逐條 verdict

| finding | 提出方 | verdict |
|---------|--------|---------|
| `CODEX-R1-P1-01` | codex | **CLOSED** |
| `CODEX-R1-P1-02` | codex | **CLOSED** |
| `CODEX-R1-P1-03` | codex | **CLOSED** |
| `CODEX-R1-P1-04` | codex | **CLOSED** |
| `GROK-R1-P2-01` | grok（同 `P1-03`） | **CLOSED** |

### (1b) CLOSED 者重跑命令與觀測

**`CODEX-R1-P1-01`** — ORCH／治理活文家數字面  
`grep -n '雙家族\|兩家族\|兩家\|2 個正式' CLAUDE.md AGENTS.md .cursorrules docs/DEVELOPMENT_GUIDE.md docs/MULTI_AGENT_ORCHESTRATION.md`  
→ `CLAUDE.md`／`DEVELOPMENT_GUIDE.md`／`AGENTS.md`／`.cursorrules` **零命中**；`ORCH:193-194` 已改為「§1 現行分工行所列之全部審查家族」；`ORCH:195` 僅剩**歷史註解**（說明舊句「兩家族」為何錯），非現行派工依據。舊 epic（`GOV_*`／`白話說明/` 等）之「雙家族」屬 forward-only 歷史紀錄，不影響現行 `§C-9` 契約。

**`CODEX-R1-P1-02`** — mutation 縮寫  
`awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md | grep -oE 'M-SU-D2-[0-9]{2}' | sort -u | wc -l` → **34**；`grep -E 'M-SU-D2[^-0-9]|M-SU-D2-[0-9]{1}[^0-9]|M-SU-D2-[0-9]{3}' docs/SPLITUNIFY_TODO.md`（§C-9 區）→ **零命中**（無裸數字縮寫）。

**`CODEX-R1-P1-03`／`GROK-R1-P2-01`** — Task 9.4 前端型別錨  
`grep -n 'types\.ts:1582\|types\.ts:2257' docs/SPLITUNIFY_TODO.md` → 僅 `:655` **碼證敘述**（說明兩行屬 `CPCVPathResult`／`MarginalICSection`、**不得**當施工錨）；Task 9.4 施工面改為「事件路徑無 typed `n_train`；要 typed 須新增事件摘要型別」。`frontend/src/lib/types.ts:3174-3176` → `EventAnalyzeResponse.summary: Record<string, unknown>` 實查成立。

**`CODEX-R1-P1-04`** — xfail 與 register 機械驗收  
§C-9 Task 9.2a `:523-541` 已逐字 node id `tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed` ＋ `-rxX` ＋「須含 `1 xfailed`／`passed` 或 `no tests ran` 不通過」。Task 9.3 `:628-631` 已列 receipt 路徑 `handoffs/run_receipts/*-splitunify-task-9.3-register-rescan.txt` 與雙向 `grep -cE` 相等判準（SPEC 側實跑 **29**）。

---

## 必答 2 — 批次切法

### (2a)

**維持 `B9A`–`B9F` 六批**（與 stamp-r1 composer／grok 一致；**不**採 codex 五批＝`9.3∥9.4` 併 gate）。

| 批 | 理由 |
|---|---|
| `B9A` | 9.1 可獨立回退 producer→summary |
| `B9B` | 9.2+9.2a 技術硬耦合（無 `feature_timeframe` 則全量 merge `MergeError`） |
| `B9C` | 9.2b 側別錨定須在複合鍵 guard 之後 |
| `B9D`／`B9E` 分開 | 同依賴 `B9C`、可並行，但失敗面不同（九處消費面 vs 計數／baseline／顯示） |
| `B9F` | golden 必最後 |

### (2b) 若選錯（五批）何時暴露

- **錯併 `B9D`+`B9E`**：單一 gate 紅時難歸因——例如 `test_tier_min_test_events_counts_unique_event_ids`（9.4）與 `test_pattern_bridge` 回歸（9.3）同批失敗，需人工拆 diff；若 9.4 先 merge 而 9.2a 計數未 rebase，**`B9E` 批**跑 `test_tier_min_test_events_counts_unique_event_ids` 會綠過膨脹 `n_test`（1 事件×2 TF 被當 2）。
- **錯拆 `B9B`**：9.2a 單獨完工後跑 `test_run_without_selected_timeframe_emits_all_feature_tf_rows` → `MergeError` 或同 `event_id` 兩列 TF 碰撞。

---

## 必答 3 — codex 主張補進 §V 三條

### (3a)

**不值得**為 clusters 事件級／purged∩assignments 互斥／複合鍵錯誤訊息重開已蓋章 SPEC（`06b2d4cb…` 三家 APPROVED）。重開成本＝新 body hash ＋三家 stamp ＋ provenance ＋ impl 前置全停；收益僅文檔字面與 §C-9 測試名對齊，無新可證偽行為。

### (3b) 不重開時 §C-9 是否足以「改壞會紅」

| codex 主張 | §C-9 承接 | 改壞會紅之測試 |
|------------|-----------|----------------|
| clusters 維持事件級 | Task 9.2a 要點 (2)＋驗收 | `test_clusters_remain_event_level_when_multi_feature_tf` |
| purged／assignments `event_id` 互斥 | Task 9.2b 要點 (6)＋驗收 | `test_purged_and_assignments_event_id_disjoint` |
| 複合鍵錯誤訊息指鍵非側 | Task 9.2a 驗收 | `test_duplicate_composite_key_error_message_names_key_not_side` |

mutation 網：`M-SU-D2-25`（guard 順序）、`M-SU-D2-22`／`24`／`30`（9.2b 側別與互斥）覆蓋施工面。⇒ **不重開 SPEC 仍可 fail-closed**。

---

## 必答 4 — impl token

### (4a)

**可以**領 impl token 進 `Task 9.1`。

### (4b) 檢查項

1. `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0  
2. §C-9 動工前置 (1)(2)：戳記＋REVERT 已執行（brief receipt `20260913T125919Z-splitunify-b9-revert-verify`）  
3. stamp-r1 五條修補本輪獨立複驗皆 **CLOSED**（必答 1）  
4. `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_TODO.md` → rc=0（brief fact-verified）  
5. `bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-b9-stamp-r1/synth.md docs/SPLITUNIFY_TODO.md` → rc=0（brief fact-verified）  
6. §C-9 列舉 12 pytest 路徑 `test -f` 全 OK  
7. `scripts/stampable_artifacts.txt` 僅加 `docs/SPLITUNIFY_SPEC.D-002.md` 完整路徑、無萬用字元／`..`；其餘 `docs/` 受戳記檔未加之列為具名殘留（body hash 未查證）——與檔頭誠實邊界一致  

**最小閉合集合**：無（本輪無 STILL-OPEN）。

---

## 攻擊面複驗摘要

| 面向 | 結論 |
|------|------|
| 家數字面漂移 | 活文治理檔已清；`ORCH:195` 為歷史註解非派工句；舊 epic 歷史「雙家族」不納入現行契約 |
| Task 9.4 前端 | 六支 vitest 行號 27／30／28／29+101／24／14 仍命中 `n_train` fixture；`EventTablesPanel.tsx:361` 為顯示落點；typed 面 correctly deferred |
| 批次分歧 | 六批（見必答 2） |
| §V 三條 | 不重開 SPEC；§C-9 測試＋mutation 足夠 |
| stampable 白名單 | 封閉清單合規；單檔加入理由成立 |

---

## COMPOSER-R13-P3-00

**斷言**: 本輪對 stamp-r1 五條修補與 brief 攻擊面逐項獨立複驗後無需阻擋收斂之 finding；§C-9 機械驗收字面（xfail `1 xfailed`、register `grep -cE`）在本機 pytest 8.4.2／grep 下可執行。

**碼證**: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md | grep -oE 'M-SU-D2-[0-9]{2}' | sort -u | wc -l` → 34；`venv/bin/python -m pytest -rxX -q tests/test_feature_factory_operators.py::test_rolling_aggregator_handles_duplicate_columns` → 摘要含 `1 xfailed`；`grep -cE '^\| `C5-[0-9]+`' docs/SPLITUNIFY_SPEC.D-002.md` → 29。

**來源摘要**: docs/SPLITUNIFY_TODO.md#9cbdedd0a735

[P3] 信心度=High。DOCROT 成效量測第一輪；審查輸入僅 §C-9 current block＋`87d38dd9` diff，未重審 SPEC body。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: SPEC stamp rc=0；34/34 mutation；12/12 pytest 路徑；xfail 摘要字面；register grep 29；六批切法；§V 三條 §C-9 承接足夠  
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`venv/bin/python -m pytest -rxX -q tests/test_feature_factory_operators.py::test_rolling_aggregator_handles_duplicate_columns` → 1 xfailed；family-drift grep（必答 1b）；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r13-composer.md --family composer`（收尾）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀 review）

STATUS: DONE
