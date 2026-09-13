# SPLITUNIFY b9 D-002 v13 補戳記 ＋ §C-9 審查 — grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-STAMP-R1`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-STAMP-R1-BRIEF.md`  
**findings-round**: STAMP  
**stamp-target**: `docs/SPLITUNIFY_SPEC.D-002.md`  
**禁改碼**：本輪只產 stamp 交件＋一行戳記 append；未改 SPEC body／TODO／生產碼。

---

## 必答 1 — SPEC 戳記

**(1a) `docs/SPLITUNIFY_SPEC.D-002.md`（body sha256 `06b2d4cb…`）：`APPROVED`**

實跑 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77`（與 brief 逐字相符）。本輪為 R12 停輪後補簽，非重開規格審查；brief 明示不得以 `V8_BASELINE_SHA256` 缺字面或「TODO 缺 Task 9.x」拒簽（前者屬 Task 9.5 施工面、後者本輪已補）。

**(1b) `Task 9.1` 最可能先紅之條文**

§P／§V `Task 9.1` **返回形狀**：`build_event_keys` 改回 `(keyed, discarded)` 且無丟棄時 `discarded == {}`。現況 caller 僅 `pipeline.py:747` 與 `tests/momentum/Analysis/test_splitunify_derive.py` 多處以單一 `DataFrame` 承接（`keys = build_event_keys(...)`）。若只改 producer 未同批改 unpack／summary 寫入，既有 derive／wiring 測試與 §C-9 之 `test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer` 會先紅。**變紅時改碼**（契約已在 v13 定案，不改規格）。

---

## 必答 2 — 六批切法

**(2a) 接受 `B9A`–`B9F` 六批；不建議併 `B9D`+`B9E`，亦不建議再拆 `B9B`。**

| 批 | 理由（技術耦合，非偏好） |
|---|---|
| `B9A`（9.1） | producer→summary 揭露可獨立回退；與 9B 行為解耦 |
| `B9B`（9.2+9.2a） | §P 第四層：全量多 TF 在無 `feature_timeframe` 欄時 `merge validate="1:1"` 必 `MergeError`；只改其一皆紅 ⇒ **不得拆批** |
| `B9C`（9.2b） | 側別／跨表互斥在複合鍵 guard 之後才有定義 |
| `B9D`／`B9E` 分開 | 同依賴 `B9C` 且可並行，但改動面不同（九處消費面防誤改 vs 計數／baseline／前端）；分 gate 縮小歸因與 rebase 面 |
| `B9F`（9.5） | golden 凍結必須最後（未定側別寫死） |

SPEC §P 僅 Phase 9A／9B 兩層、無批次粒度——六批是施工分解；其邊界由上述技術耦合支撐，不是任意切。

**(2b) 若批數錯，可執行觀測**

- **`B9B` 被拆**：第二批前跑 `test_run_without_selected_timeframe_emits_all_feature_tf_rows` → `MergeError` 或同事件兩列 TF 碰撞（`split_projection.py:291-303`）。
- **`B9D`+`B9E` 錯併且未 rebase**：`test_tier_min_test_events_counts_unique_event_ids` 在 9.2a 去重未落地時可能假綠，合併後才暴露 1 事件×2 TF 繞過 `tier_min`。
- **`B9F` 非最後**：`freeze_splitunify_golden.py` 後 §V 外部錨／側別與未完工行為不一致 → golden 整批紅。

---

## 必答 3 — §V ↔ §C-9 測試對照

**(3a) §V 有、§C-9 無具名承接之 ASSERT（落單）**

| §V ASSERT（摘要） | 處置 |
|---|---|
| `metadata.split_unify["discarded_rows_by_feature_tf"]` 值相等 ＋ `reason` 封閉值集 | **刻意 defer**（§N `SU-RESID-9A-UI`；§C-9 Task 9.1 明示不得宣稱已閉） |
| `(G-4d)② decision_at_ms == feature_cutoff_ms` 零位移 | §C-9 未列具名函式；由 Task 9.2b fixture 前置＋`test_splitunify_golden.py` 施工面承接 |
| `(G-4e) 投影／oracle／expected_side 三者全等` | 無逐字具名函式；由 Task 9.5 施工要點 2＋golden 測試網承接 |
| `train_rows`／`test_rows` 空或 row set 重疊 ⇒ raise | 無逐字具名函式；由 Task 9.2b 具名呼叫 `validate_split_pair_integrity`＋既有 fail-closed 路徑承接 |

其餘活文 §V ASSERT 均可映射到 §C-9 具名測試或 mutation 自證段。

**(3b) §C-9 有、§V 無逐字函式名（主委自創面）**

| 測試函式（代表） | 判斷 |
|---|---|
| `test_build_event_keys_discarded_*`／`test_summary_carries_*`／`test_discarded_layer_is_independently_revertible` | §V Task 9.1 ASSERT 之施工具名化 → **留 TODO 即可** |
| `test_assignments_composite_key_unique` 等 9.2a 系列 | §V Task 9.2a → 留 TODO 即可 |
| `test_event_level_anchor_*`／`test_coordinate_truth_table_four_cases` 等 9.2b 系列 | §V Task 9.2b／`D-002-C3` → 留 TODO 即可 |
| `test_baseline_*`／`test_tier_min_*`／`test_event_count_conservation` | §V Task 9.4 → 留 TODO 即可 |
| `test_v8_*`／`test_spec_anchor_*`／`test_freeze_*` | §V 第 6 條 → 留 TODO 即可 |
| `test_duplicate_event_id_is_fail_closed`（更新 `match=`） | 既有測試施工細節 → 留 TODO 即可 |

無需回寫 §V（§C-9 定位＝施工分解，不複述條文）。

---

## 必答 4 — mutation 認領

**(4a) 機械計數**

```text
# 全形 ID
awk '/^## §C-9/,/^## §D/' docs/SPLITUNIFY_TODO.md | grep -oE 'M-SU-D2-[0-9]+' | sort -u | wc -l
→ 25

# 展開 Task 9.2b／9.5 之 `M-SU-D2-14`／`15`／`22`… 簡寫後
→ claimed {1..34} 共 34；missing []
# 其中 M-SU-D2-03 在 Task 9.1 明示「隨殘留延後、本 Task 不得宣稱已閉」——認領＝defer，非漏掛
```

**(4b) 落單者**

無「完全未認領」。`M-SU-D2-03` **不掛 Phase 9 完工條件**——在 `SU-RESID-9A-UI` 解除（投影路徑出現 `EventSamplePipeline.run` 生產 call-site）時由接線票＋`tests/api/test_splitunify_disclosure.py` exact-key 閉合。

---

## 必答 5 — Task 9.2a xfail

**(5a) 接受 `xfail(strict=True)`，至 Task 9.2b 解除。**

三重問題中 9.2a 只修 fixture ①；② `(3.2)` `AlignmentViolationError` 與 ③ `feature_cutoff_ms` 判側屬 9.2b。`--deselect` 藏紅；裸紅擋 9.2a gate。

**(5b) 9.2a 完成後不會意外 XPASS 之碼證**

現況 `split_projection.py` 全檔 `decision_at_ms` 命中數＝0；側別迴圈仍取 `feature_cutoff_ms`（約 `:530-553`）。9.2a 只加複合鍵欄／guard 與修 `_manifest` 事件級 fixture，**不**插入 `(3.2)` raise、**不**改判側 ⇒ 該測試期望之異側 fail-closed **仍 fail**（XFAIL 成立）。`strict=True` 只在意外 pass 時轉 XPASS；9.2b 完成後才解除 xfail。

---

## 必答 6 — 可否動工

**(6a) 無阻擋 `Task 9.1` 之 BLOCKING；三家 stamp 齊後可進 9.1。**  
（本家 P2 僅影響 `Task 9.4` 修改檔具名，見下；不擋 9.1。）

**(6b) 本輪具名檢查**

1. body hash `06b2d4cb…` rc=0（append 戳記後重跑仍同）  
2. `git status --porcelain` 對 revert 五路徑無條目；兩測試檔 pytest **87 passed** rc=0  
3. §C-9 驗收所列既有 pytest 路徑 `ls` 全存在；`eventExportByEventId.test.tsx` 標「須新建」→ 預期 MISSING  
4. mutation 34/34 認領（含 `03` defer）  
5. 前端六 vitest basename 於 `frontend/src/components/ic-analysis/`，行號 27/30/28/29/24/14／capability:101 仍命中 `n_train`／`n_test` fixture  
6. `types.ts:1582`／`:2257` **錯錨**（見 GROK-R1-P2-01）——`EventTablesPanel.tsx:361` 正確  
7. `grep -rn "雙家族\|兩家\|2 個正式" CLAUDE.md AGENTS.md .cursorrules` 零命中；ORCH 三處 quorum 字面已改；`:193-194`「兩家族」為 adversarial 歷史敘述（寫死 GPT-5.5+Composer），非 §1 quorum 家數漂移  
8. Task 9.3「重掃 register」產出＝寫入該 Task 施工紀錄（impl 時同節）；路徑未另建檔名，屬施工慣例非 BLOCKING  

---

## GROK-R1-P2-01

**斷言**: `docs/SPLITUNIFY_TODO.md` Task 9.4 將前端型別修改錨在 `frontend/src/lib/types.ts:1582` 與 `:2257`，但該兩行分屬 `CPCVPathResult.n_train`／`MarginalICSection.n_train`，與事件批 `EventAnalyzeResponse.summary: Record<string, unknown>`（`types.ts:3176`）無關；依原文改碼會動到錯誤介面。

**碼證**: `sed -n '1578,1584p;2239,2258p;3174,3177p' frontend/src/lib/types.ts` → 1582∈`CPCVPathResult`、2257∈`MarginalICSection`、3176=`summary: Record<string, unknown>`；`EventTablesPanel.tsx:361` 仍正確讀 `s.n_train`／`s.n_test`／`s.n_purged`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#94c6aa2eb64c

修法（非本輪執行）：Task 9.4「修改檔案」之 `types.ts` 兩錨改為 (a) 刪除（因 summary 為 `Record` 無欄位可改）或 (b) 具名到真實事件 summary／baseline 消費型別（若後續新增）；**不得**改 CPCV／MarginalIC。可行性：事件路徑現無 typed `n_train` 欄，刪錯錨不會丟交付面；`EventTablesPanel.tsx:361` 與六支 vitest 仍為真消費點。本條不擋 Task 9.1；須在 `B9E`／Task 9.4 動工前關閉。

---

## 戳記

已 append 至 `docs/SPLITUNIFY_SPEC.D-002.md` `## 戳記` 區（單獨一行，非標題）：

```text
RECONCILE-STAMP: grok APPROVED 2026-09-13 sha256:06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77 task:20260911-SPLITUNIFY-B9-STAMP-R1
```

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body hash 06b2d4cb…；HEAD revert 路徑乾淨；兩測試檔 87 passed；mutation 34 認領（03 defer）；六批技術耦合；xfail 後仍 fail 之碼路徑；types.ts:1582/2257 錯錨
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → 06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77 rc=0；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 87 passed rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（戳記 append ＋本交件檔；未改 TODO／SPEC body／生產碼）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-stamp-r1-grok.md
HANDOFF_OUTPUT: handoffs/20260913-20260911-SPLITUNIFY-B9-STAMP-R1.md
TMP_CLEANUP: 本輪未建 /tmp workdir；掃 /tmp 無本 task 具名殘留；`/tmp/claude-501` 保留

STATUS: DONE
