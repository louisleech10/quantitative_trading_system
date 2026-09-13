# SPLITUNIFY b9 D-002 v13 補戳記 ＋ §C-9 審查 — composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-STAMP-R1`  
**family**: composer  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-STAMP-R1-BRIEF.md`  
**findings-round**: STAMP  
**stamp-target**: `docs/SPLITUNIFY_SPEC.D-002.md`  
**禁改碼**：本輪只產 stamp 交件＋一行戳記 append。

---

## 必答 1 — SPEC 戳記

**(1a) `docs/SPLITUNIFY_SPEC.D-002.md`（body sha256 `06b2d4cb…`）：`APPROVED`**

R12 停輪已觸發且本輪為補簽非重審；brief 明示不得再以 `V8_BASELINE_SHA256` 缺字面、`Task 9.1–9.5` 缺 TODO 拒簽；§C-9 已補且與 §P／§V／mutation 對齊，無需再改 SPEC body 即可動工 9.1。

**(1b) `Task 9.1` 最可能先紅之條文**

§P `Task 9.1` 之 **返回形狀**句：`build_event_keys` 須回傳 `(keyed, discarded)` 且 `discarded` 無丟棄時為 `{}`（不得省略或 `None`）。若只改 producer 而 `pipeline.py` caller 仍假設單一 `DataFrame` 回傳，或 `_derive_single_symbol` 未原樣寫入 `EventSplitPlan.summary["discarded_rows_by_feature_tf"]`，§V／§C-9 之 `test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer` 會先紅。**變紅時改碼**（非改規格）——契約已在 v13 定案。

---

## 必答 2 — 六批切法

**(2a) 接受 `B9A`–`B9F` 六批；不建議再合併或再拆。**

| 批 | 理由 |
|---|---|
| `B9A`（9.1） | 可獨立回退之 producer→summary 揭露，與 9B 行為解耦 |
| `B9B`（9.2+9.2a） | SPEC 硬依賴：無 `feature_timeframe` 欄時全量 merge 必 `MergeError`（§P `Task 9.2` 第四層） |
| `B9C`（9.2b） | 側別錨定＋跨表互斥；複合鍵 guard 之前無「同側」定義 |
| `B9D`／`B9E` 分開 | 依賴同為 `B9C` 且可並行，但改動面不同（消費面防誤改 vs 計數／baseline／前端型別）；分 gate 可縮小 review 與 rebase 衝突面 |
| `B9F`（9.5） | golden 凍結必須最後（§C-9 依賴序） |

曾評估 brief 所提 `B9D`+`B9E` 併批：可省一輪 review，但會把九處回歸測試＋baseline 拆鍵＋六支 vitest 綁成單一 gate，失敗時難歸因；**六批成本換取可證偽邊界，接受。**

**(2b) 若批數錯，何時以何形式發現**

- 若 **`B9B` 被拆成 9.2／9.2a 兩批**：第二批動工前跑 `test_run_without_selected_timeframe_emits_all_feature_tf_rows` 即 `MergeError` 或同事件兩列 `timeframe` 碰撞（`split_projection.py:291-303`）。
- 若 **`B9D`+`B9E` 錯序且未 rebase**：`Task 9.4` 之 `test_tier_min_test_events_counts_unique_event_ids` 在 9.2a 未去重時綠、合併後才暴露膨脹計數。
- 若 **`B9F` 非最後**：`venv/bin/python scripts/freeze_splitunify_golden.py` 後 §V 外部錨／側別 ASSERT 與未完工行為不一致，golden 整批轉紅。

---

## 必答 3 — §V ↔ §C-9 測試對照

**(3a) §V 有、§C-9 無具名承接之 ASSERT（落單）**

| §V ASSERT（摘要） | 處置 |
|---|---|
| `metadata.split_unify["discarded_rows_by_feature_tf"]` 值相等 ＋ `reason` 封閉值集 | **刻意 defer**——§P O1／§N `SU-RESID-9A-UI`；§C-9 Task 9.1 明示不得宣稱已閉 |
| `(G-4d)② decision_at_ms == feature_cutoff_ms` 零位移 | §C-9 未列具名函式；由 Task 9.2b golden 前置＋`test_splitunify_golden.py` 施工面承接 |
| `train_rows`／`test_rows` 空或 row set 重疊 ⇒ raise | §C-9 未列具名函式；由 Task 9.2b 之 `EventSamplePipeline.run` 呼叫 `validate_split_pair_integrity` ＋既有 `test_empty_test_rows_is_fail_closed` 承接 |

其餘 §V ASSERT 均可映射到 §C-9 具名測試或 mutation 自證段。

**(3b) §C-9 有、§V 無逐字函式名（主委自創面）**

| 測試函式 | 判斷 |
|---|---|
| `test_build_event_keys_discarded_*`／`test_summary_carries_*`／`test_discarded_layer_is_independently_revertible` | 屬 §V Task 9.1 ASSERT 之施工具名化；留 TODO 即可 |
| `test_assignments_composite_key_unique` 等 9.2a 系列 | 屬 §V Task 9.2a；留 TODO 即可 |
| `test_event_level_anchor_*`／`test_coordinate_truth_table_four_cases` 等 9.2b 系列 | 屬 §V Task 9.2b／`D-002-C3`；留 TODO 即可 |
| `test_baseline_splits_n_test_into_events_and_samples` 等 9.4 系列 | 屬 §V Task 9.4；留 TODO 即可 |
| `test_v8_*`／`test_spec_anchor_*` 等 9.5 系列 | 屬 §V 第 6 條／`M-SU-D2-29`/`34`；留 TODO 即可 |
| `test_duplicate_event_id_is_fail_closed` | §C-9 Task 9.2a 引用既有測試更新 `match=`；屬施工細節 |

無需回寫 §V——§C-9 定位即 SPEC 之施工分解，不複述條文。

---

## 必答 4 — mutation 認領

**(4a) 機械計數**

```text
python3 - <<'PY'（解析 §C-9 全角／`M-SU-D2-NN` 簡寫）
→ Found 34 of 34
→ 唯一刻意未認領：M-SU-D2-03（metadata 層，§C-9 Task 9.1 明示隨 SU-RESID-9A-UI defer）
PY
```

**(4b) `M-SU-D2-03` 該掛哪**

不掛 Phase 9 Task——在 `SU-RESID-9A-UI` 殘留解除（投影路徑出現 `EventSamplePipeline.run` 生產 call-site）時，由接線票＋`tests/api/test_splitunify_disclosure.py` exact-key 路徑閉合；與 brief consult-r2 裁定一致。

---

## 必答 5 — Task 9.2a xfail

**(5a) 接受 `xfail(strict=True)` 至 Task 9.2b 解除。**

consult-r2 三重問題裁定：9.2a 只修 fixture ①；② `(3.2)` 異側 guard 與 ③ `feature_cutoff_ms` 判側屬 9.2b。`--deselect` 會藏紅；裸紅會擋 9.2a gate。

**(5b) Task 9.2a 完成後不會 XPASS 之理由**

9.2a 完成後行為預期：manifest fixture 修正使多 TF 列可進 derive，但 `_derive_single_symbol` 仍以 `feature_cutoff_ms` 逐列判側（`split_projection.py:530-553` 現況 `decision_at_ms` 命中數＝0），且 `(3.2)` 之 `AlignmentViolationError` 尚未插入 ⇒ `test_multi_feature_tf_opposite_sides_must_fail_closed` **仍 fail**（非 pass）。`strict=True` 僅在意外 pass 時轉 XPASS；9.2b 實作完成後才解除 xfail 並要求 pass。

---

## 必答 6 — 可否動工

**(6a) 無 BLOCKING；待三家 stamp rc=0 後可進 `Task 9.1`。**

**(6b) 本輪檢查項（具名）**

1. `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `06b2d4cb…` rc=0  
2. `bash scripts/reconcile_stamps_check.sh` → 三家缺戳記（本輪 append 前預期 FAIL）  
3. `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → **87 passed** rc=0  
4. §C-9 列舉之 12 個 pytest 路徑 `ls` 全存在；Task 9.4 六支前端測試以 basename 指向 `frontend/src/components/ic-analysis/`（`eventTableTooltips.test.tsx:27` 等行號仍正確）  
5. 34 mutation 在 §C-9 全數認領（含 `M-SU-D2-03` defer 明示）  
6. `grep` 第四處「雙家族／兩家／2 個正式」——`CLAUDE.md`／ORCH 三處已改；殘留 `ORCH:193-194` 為 adversarial 歷史敘述（非 quorum 家數），不構成 drift  
7. Task 9.3「重掃 register」產出＝Task 9.3 施工紀錄（impl 時寫入同 Task 正文），非缺定義之 BLOCKING  

---

## COMPOSER-R1-P3-00

**斷言**: 本輪對 stamp-target body（sha256 `06b2d4cb…`）與 §B `B9A`–`B9F`＋§C-9 Task 9.1–9.5 逐項核對後無需阻擋收斂之 finding；六批切法、xfail 處置、mutation 認領與 §V  defer 邊界均可接受。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77` rc=0；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 87 passed rc=0；34/34 mutation 機械認領（`M-SU-D2-03` defer）；12/12 §C-9 pytest 路徑存在；前端六測試 basename 於 `frontend/src/components/ic-analysis/` 行號 27/30/28/29/24/14 仍命中。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b；docs/SPLITUNIFY_TODO.md#bcf6e35a

[P3] 信心度=High。本輪 `brief-kind: closure`／stamp 補簽。

---

## 戳記

已 append 至 `docs/SPLITUNIFY_SPEC.D-002.md` `## 戳記` 區：

```text
RECONCILE-STAMP: composer APPROVED 2026-09-13 sha256:06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77 task:20260911-SPLITUNIFY-B9-STAMP-R1
```

---

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:

ASSUMPTIONS_VERIFIED: body hash 06b2d4cb…；HEAD 兩測試檔 87 passed；§C-9 路徑／行號／mutation 34 條機械計數；六批依賴與 SPEC §P 技術耦合一致  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 87 passed rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（戳記 append ＋本交件檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_PATH: handoffs/20260911-splitunify-b9-stamp-r1-composer.md  
TMP_CLEANUP: /tmp 無 `*workdir*` 需清；`/tmp/claude-501` 保留  

STATUS: DONE
