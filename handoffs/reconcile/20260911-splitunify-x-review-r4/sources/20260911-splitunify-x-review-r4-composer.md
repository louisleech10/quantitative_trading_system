# SPLITUNIFY — E1／E2 定向確認 R4（composer）

task-id: `20260911-SPLITUNIFY-X-REVIEW-R4`  
family: `COMPOSER`  
findings-round: `R4`  
審查對象: `docs/SPLITUNIFY_SPEC.md`（sha256 `384aa22961d0…`）、`docs/SPLITUNIFY_TODO.md`（sha256 `cd95ee642a9e…`），commit `b6633582`

## 被當成事實的未驗證假設（§0）

| 宣稱 | 類型 | 核對結果 |
|---|---|---|
| `test_start_ms` 已是 purge＋embargo 之後第一根 | **fact-verified** | `holdout_test_row_index` 定義 `test_rows = arange(split_point + purge_gap + embargo, n_rows)`（`split_preview.py:29-30`）；Task 2.1 寫 `test_start_ms = as_ms(feature_index[test_rows[0]])`（SPEC:386-387） |
| v4 第一段 `label_end_ms >= test_start_ms` 可取代 `event_split.py:114` 之 `> test_start - embargo` | **assumed → 架構性成立、字面不等價** | 兩者座標系不同（事件 `decision_at_ms` 分位 vs feature 列 `holdout_boundary`）；投影路徑禁 `EventSplitConfig.embargo_ms`（C-5:226-230），緩衝已 bake 進 `test_start_ms` 之列位移，**不應再減 `embargo_ms`**。見必答 1 |
| `event_keys` 六欄足以做 E2 對位 | **fact-verified** | `manifest.table` 含 `event_id`／`symbol`／`timeframe`／`label_start_ms`／`label_end_ms`；`receipts.per_tf` 含 `feature_cutoff_ms`（`alignment.py:209-210`）；`ic_feed.py:106-109` 已有 `manifest`＋`per_tf` 以 `event_id` join 先例 |
| G-5.3「source bars 缺 endpoint」可在投影內執行 | **assumed → 前置已驗** | `alignment.py:192-195` 與 `dedupe.py:42-44` 在 manifest 前已 fail-closed；投影簽名無 bars 但上游已保證 endpoint——殘差見必答 3 |

## 必答 1–4（明確立場）

**1. E1 閉合了嗎？第一段條件式夠精確嗎？**

**閉合。** v4 兩段式（C-4:175-191、Task 2.2:414-417）恢復 R3 `CODEX-R3-P1-02` 指出的答案窗 purge，且先後不可調。

**可直接實作的式子**（投影路徑；`test_start_ms` 來自 `holdout_boundary` 第四元）：

```python
train_ms = {as_ms(feature_index[i]) for i in train_plan.row_index}
fc_ms = as_ms(row["feature_cutoff_ms"])  # event_keys 列，已 ms 歸一
label_end = int(row["label_end_ms"])

# 第一段（答案窗；優先）
if fc_ms in train_ms and label_end >= test_start_ms:
    purged(event_id, reason="interval_crosses_split_boundary")
    continue
# （可選）缺 endpoint：上游 alignment 已驗；若 B2b 要雙保險，在 assemble 時 assert 非 NaN
# 第二段（集合成員）
elif fc_ms in train_ms:
    assignments(..., split_label="train")
elif fc_ms in {as_ms(feature_index[i]) for i in test_plan.row_index}:
    assignments(..., split_label="test")
else:
    purged(...)
```

**與 `purge_gap`／`embargo` 的關係**：`purge_gap`（列）與 `embargo`（列）僅進 `holdout_test_row_index`（`split_preview.py:39-40`），決定 `test_rows[0]` 位置 ⇒ `test_start_ms`。第一段**不再**套用 `label_end_ms > test_start_ms - embargo_ms`，因為：(a) 投影路徑 `embargo_ms` 必為 `None`（C-5:226-230，檢查在 Task 3.1 caller）；(b) 再減 event 側 ms embargo 會與列級 purge／embargo **雙重計數**；(c) 舊式 `event_split.py:114` 的 `test_start` 是事件 `decision_at_ms` 分位（`:109`），與 `test_start_ms` **非同一變數**，不可逐字移植。

**`>=` vs `>`**：用 `>=`。`label_end_ms == test_start_ms` 表示答案窗觸及測試段起點，應 purge（與 G-5.4 leakage negative 一致）。

**2. E2 閉合了嗎？六欄夠嗎？誰組裝 `event_keys`？**

**閉合（SPEC 層）。** C-4:167-173 之六欄覆蓋身份（`event_id`／`symbol`／`timeframe`）、答案窗（`label_start_ms`／`label_end_ms`）、成員 cutoff（`feature_cutoff_ms`＝`FEATURE_CUTOFF_RULE`，C-4:204-205），足以禁 positional zip 並滿足 E1 第一段。

**組裝立場（B3 接線，B2b 抽 helper）**：

- **B2b**：新增純函式 `build_event_keys(manifest, receipts, *, anchor_timeframe) -> pd.DataFrame`，邏輯複用 `ic_feed.build_event_ic_inputs` 之 join 形態（`manifest.table[in_primary]` ⨝ `receipts.per_tf[timeframe==anchor]`，鍵 `event_id`；`dedupe.py:46` 之重排不影響鍵 join）。
- **B3 Task 3.1**：`pipeline.run`／`ic_filter_orchestrator` 在呼叫 `derive_event_split_from_plans` 前組好 `event_keys` 並傳入；**不在**投影內讀 `receipts`（保持純函式）。
- **多 TF**：每事件取 **anchor TF**（與 IC `event_label_values` 同源）之一列 `feature_cutoff_ms`；與 `alignment.py:197-213` 之 `per_tf` 多列不衝突——投影一行一事件。

v4 未逐字寫組裝者名稱，但 C-4 簽名＋`ic_feed` 先例使 B2b 可執行；建議 B1 延伸檔或 B2b 開工前順手在 TODO Task 2.2 補一句「組裝＝`build_event_keys`」。

**3. 介面可執行性掃描**

| 檢查項 | 簽名／caller 是否可執行 | 判定 |
|---|---|---|
| 答案窗 purge（E1） | `event_keys` 含 `label_end_ms`；`test_start_ms` 由 `holdout_boundary` 或 `SplitPlan` 同源導出 | ✅ |
| `index_kind != "positional"` raise | `train_plan`／`test_plan` 帶 `index_kind` | ✅ |
| 禁 `_normalize_ic_time_index` | 投影內自做 ms 歸一（C-4:196-203） | ✅ |
| `bucket_ms` 進投影 | C-4:163 | ✅ |
| `embargo_ms is None` raise | **不在投影簽名**；Task 3.1:480-481 caller assert + `-k embargo_must_be_none` | ✅ |
| `event_keys` vs `event_index` | SPEC C-4 已改 `event_keys`；**TODO Task 2.2:178,196 仍寫 `event_index`** | ⚠️ 見 `COMPOSER-R4-P2-01` |
| G-5.3 source bars endpoint | 簽名無 bars；依賴 alignment 前置驗證 | ✅（P3 殘差，不擋 B1） |
| B2a tuple vs B2b `SplitPlan` | B3 路徑 orchestrator 已有 `SplitPlan`；B2 測試自建 plan——可執行 | ✅ |

**4. 可否進 B1？**

**可以。** 判準：B1 僅 Task 1.1–1.3（文件、枚舉、紅基準），**不動生產碼**；E1／E2 為 B2b 實作契約。v4 SPEC C-4 已閉合 R3 兩條 P1（兩段式答案窗 + keyed `event_keys`）。殘留為 TODO 與 SPEC 簽名漂移（P2，可在 B1 文件批或 B2b 開工前同步修正），**不構成 B1 阻擋項**。

---

## COMPOSER-R4-P2-01

**斷言**: TODO Task 2.2 之輸入／輸出仍寫 `event_index`，與 v4 SPEC C-4 之 `event_keys: pd.DataFrame` 及實作要點 3／4 互斥，B2b 實作端若只讀 TODO 會建錯簽名。

**碼證**: SPEC C-4:156-164 簽名為 `event_keys: pd.DataFrame`（六欄契約 `:167-169`）；TODO Task 2.2:178 仍寫 `(train_plan, test_plan, event_index, feature_index, …)`；同段:188-197 混用 `event_keys` 與「`event_index` 語意＝ feature_cutoff」。RECHECK: `rg -n 'event_index|event_keys' docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md | head -30`

**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0, docs/SPLITUNIFY_TODO.md#cd95ee642a9e

[MAJOR] 信心度=High；不擋 B1（SPEC 為準且已正確），但 B2b 開工前須把 TODO:178/196 改為 `event_keys` 並刪除 `event_index` 殘文，否則介面掃描會再紅一輪。修法：TODO Task 2.2 輸入行與 SPEC C-4 簽名逐字對齊。

---

## Verdict：可進 B1

E1 兩段式判定在投影架構下閉合；正確第一段條件為 `feature_cutoff_ms ∈ train_ms_set AND label_end_ms >= test_start_ms`（`test_start_ms` 已含列級 purge_gap＋embargo，勿再減 `embargo_ms`）。E2 六欄契約足夠；`event_keys` 由 B2b 之 `build_event_keys` helper 組裝、B3 caller 傳入。唯一實質殘留為 TODO／SPEC 簽名漂移（`COMPOSER-R4-P2-01`，P2 不擋 B1）。B1 可開工；建議 B1 順手同步 TODO Task 2.2 簽名以免 B2b 誤讀。

---

```
ASSUMPTIONS_VERIFIED: sha256sum docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md → 384aa22961d0…/cd95ee642a9e…；holdout_test_row_index 定義（split_preview.py:29-40）；event_split.py:114 purge 條件；alignment.py:197-213 per_tf cutoff；dedupe.py:46 重排；ic_feed.py:106-109 manifest⨝per_tf
TESTS_RUN: sha256sum docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md rc=0；rg event_index|event_keys docs/SPLITUNIFY_*.md；sed -n '19-46p' momentum/core/split_preview.py；sed -n '106-118p' momentum/Analysis/event_samples/event_split.py；未跑 pytest
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼／禁改 SPEC）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
```

STATUS: DONE
