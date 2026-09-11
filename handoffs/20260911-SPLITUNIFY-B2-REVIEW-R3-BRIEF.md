# SPLITUNIFY B2b 定向確認（R3，收斂輪）

brief-kind: review
task-id: 20260911-SPLITUNIFY-B2-REVIEW-R3
findings-round: R3

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；
findings 用 `## <FAMILY>-R3-P<0-3>-<NN>`，結尾附 **Verdict**。**禁改碼**。
審查對象＝commit `a8474406`（`momentum/core/split_preview.py`、
`momentum/Analysis/event_samples/split_projection.py`、`event_split.py`、
`tests/momentum/Analysis/test_splitunify_derive.py`、`handoffs/20260911-splitunify-b2b-mutate.py`）。

## 🔴 收斂輪：只問「還有沒有沒閉合的 P0／P1」

B2b 已審兩輪：R1 八群集（H0–H7，3 條 P1）、R2 七群集（I0–I6，5 條 P1），
**全部修補完成**。收斂檔：`handoffs/reconcile/20260911-splitunify-b2-review-r{1,2}/synth.md`。

⇒ 本輪請優先判定「可否進 B2c」。P2／P3 照列但**明確標為不擋 B2c**。
🔴 **本行於 2026-09-11 作廢**（使用者當面定死：「95% 就收」是治理票原則，**量化主線絕對禁止**）。本票之停輪判準以 `CLAUDE.md` 三方簽核鐵律為準：**任一方有疑就不通過**；殘留仍須符合 `feedback_residual_not_laziness` 三值理由。

## R2 → 現況（I1–I6 之修法）

| I | 修法 |
|---|---|
| I1 索引不變式 | `assert_epoch_ms_array(..., strictly_increasing=True)`（`diff > 0` 一併涵蓋重複）；**只套 `feature_index`**——事件欄可以重複（兩事件同一根 bar），第一版套上去當場誤擋 |
| I2 NaN 被靜默轉 0 | **cast 之前**驗 finite 與整數性 |
| I3 `event_id` 重複 | `event_keys` 與 `manifest.table` **各自**驗唯一性（集合相等會吃掉重複） |
| I4 float `row_index` | `assert_positional_rows` cast 前驗整數性（**推翻主委原裁定**，依較嚴版） |
| I5 事件欄完整性 | 新增 `_assert_event_keys_wellformed`：三個時間欄 finite／整數／毫秒 ＋ `label_start <= label_end` |
| I6 `bucket_ms <= 0` | `time_cluster_bucket_ms` 加正值檢查（原本 `0` 只是靠 pandas 例外**巧合**擋住） |

## 主委已跑的驗收（請複驗）

- `tests/momentum/Analysis/test_splitunify_derive.py` → **43 passed**。
- `venv/bin/python handoffs/20260911-splitunify-b2b-mutate.py` → **UNCOVERED=0**，
  **21 條**全 rc=1、C0 綠（harness 支援三個目標檔）。
- `venv/bin/python handoffs/20260911-probe-splitunify-negative-injection.py` → **9/9 全擋**
  （VERIFY:20260910T191355Z-splitunify-negative-injection-r2）。
- 回歸 core＋event_samples＋splitunify＋evtlabel_staging → **711 passed**。
- `bash scripts/check_decoupling.sh` → `R2=1 R3=17 R4=3`（逐值等於 baseline）。

## 🔴 必答（只有四題）

1. **I1–I6 逐條閉合了嗎**？逐條回「閉合／未閉合＋ID」。
2. 🔴 **再做一次負向注入，但換一批**——R2 那九條已全擋，請找**我沒想到的**。
   建議方向：`event_keys` 之 `symbol` 為 `None`／空字串／混型別；`manifest.summary` 缺
   `n_events_raw`；`SplitPlan.time_bounds` 與 `row_index` 不一致；
   `feature_index` 全為同一值；超大 `bucket_ms`（所有事件同一簇）；
   `event_keys` 為單列且 `feature_cutoff_ms` 恰在 train／test 邊界上。
   逐條回「已擋／未擋＋**實跑輸出**」。
3. **`strictly_increasing` 只套 `feature_index` 是對的嗎**？事件欄放寬是否留了洞？
4. **可否進 B2c**？直接回「可以」或「不可以＋ID」。

## 停輪條件

① 必答 1–4 皆有明確立場；② 必答 2 每條都有**實跑輸出**；
③ 三家分歧時各自寫判準（看碼證不數人頭）；
④ 禁以「三家零 finding」當停輪——零 finding 須走 sentinel 契約且**必須**附必答 2 的實跑輸出；
⑤ 🔴 標 P0/P1 者須說明「不改會怎麼在 B2c／B3 具體失敗」，否則標 P2/P3。

## 本 brief 之前提（逐條標）

fact-verified: 上方數字皆主委實跑，命令逐字如上。

fact-verified: R2 九條負向注入現已全擋 → VERIFY:20260910T191355Z-splitunify-negative-injection-r2（修前 4 條未擋）。

assumed: 「輸入不變式」這一類已被系統性覆蓋（21 條 mutation ＋ 9 條負向注入 ＋ 兩支共用 validator）
← 否證觀測：必答 2 換一批之後仍有未擋者。／我跑了：**沒跑**那批新的（它是我列給你們的）。請正面打。

## 🔴 我沒查的

| claim | observable_if_false | reason_code |
|---|---|---|
| `SplitPlan.time_bounds` 與 `row_index` 不一致時的行為 | 投影用 row_index、揭露用 time_bounds，兩者可分歧 | cost |
| `manifest.summary` 缺鍵時 `_build_summary` 的錯誤可讀性 | 使用者看到裸 KeyError | cost |

## ⚠️ 前置

- **禁改碼**、禁改 `docs/SPLITUNIFY_*.md` 與任何 reconcile synth。
- 不得跑 `pytest tests/governance`；`tests/momentum/Analysis` 全套 17 分鐘，非必要別跑。
- 跑完測試請 `bash scripts/restore_golden_inventory.sh`。收尾清 /tmp workdir（保留 claude-501）。

## 產出

canonical 四欄 findings ＋ **Verdict**（第一句必須是「可進 B2c」或「不可進 B2c：<ID>」）。
