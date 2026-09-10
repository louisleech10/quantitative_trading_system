# SPLITUNIFY B2b 重審（R2）— Claude 自產獨立審查（與三家平行）

依 `feedback_claude_own_version`。審查對象＝我自己寫的 B2b（commit `e2e4314c`）。
🔴 **本檔之修法一律等三家收斂後才動檔**——他們正在讀這些行號。

我把自己在 R2 brief 必答 2 列給三家的那份負向注入清單**自己先跑了一遍**
（探針 `handoffs/20260911-probe-splitunify-negative-injection.py`，
receipt `20260910T185534Z-splitunify-negative-injection`，rc=1）。
結果：**9 條裡有 4 條未擋**，其中一條是真的會算錯。

---

## CLAUDE-R2-P1-01

**斷言**: `feature_index` **未依時間遞增排序**時，`test_start_ms = index_ms[test_rows[0]]` 不再是測試段最早的時刻 ⇒ 兩段式判定第一段的答案窗比較會用到**錯誤的邊界**，且**不拋任何例外**。

**碼證**: 探針 ⑧「feature_index 反序」→ `**未擋**（無例外）`。
`momentum/Analysis/event_samples/split_projection.py` 之
`test_start_ms = int(index_ms[test_rows[0]])` 假設 index 遞增；
`momentum/core/split_preview.py::holdout_boundary` 之
`test_start_ms = _as_ms(index, int(test_rows[0]))` 同樣假設。
兩處都沒有驗證單調性。receipt：`handoffs/run_receipts/20260910T185534Z-splitunify-negative-injection.log`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#e2e4314c0a11

判定：**真缺口，P1**。修法（三家收斂後套用）：在 `assert_epoch_ms_array` 之後補
**嚴格遞增**檢查（`np.all(np.diff(arr) > 0)`），不成立即 raise——
同時涵蓋探針 ⑨（重複時間戳，`diff == 0`）。這一條放在共用 validator 裡，
`holdout_boundary` 與投影兩端都受惠。

---

## CLAUDE-R2-P2-02

**斷言**: `bucket_ms` 為**負值**時 `build_time_clusters` 不擋，會產出方向相反的 cluster id；`bucket_ms == 0` 則是靠 pandas 的 `IntCastingNaNError` 意外擋下，訊息與本票語意無關。

**碼證**: 探針 ⑤「bucket_ms = 0」→ 已擋但訊息是
`IntCastingNaNError: Cannot convert non-finite values (NA or inf) to integer`（靠除以零產生 inf）；
⑥「bucket_ms = -1」→ `**未擋**（無例外）`。

**來源摘要**: momentum/Analysis/event_samples/event_split.py#e2e4314c0a11

判定：**P2**。修法：`time_cluster_bucket_ms` 出口加 `bucket > 0` 檢查並給本票語意的訊息。
🔴 `bucket_ms == 0` 目前「有擋」是**巧合**，不是設計——靠上游函式庫的例外當閘門，
哪天 pandas 換行為就靜默失效。

---

## CLAUDE-R2-P2-03

**斷言**: `label_end_ms < label_start_ms`（答案窗反轉）不被擋，會被當成正常事件處理。

**碼證**: 探針 ⑦ → `**未擋**（無例外）`。投影只讀 `label_end_ms` 做比較，
從未驗證 `label_start_ms <= label_end_ms`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#e2e4314c0a11

判定：**P2**。上游 `alignment.py:192` 已有
`if not (decision_at <= label_start < label_end): raise` ⇒ 走正常管線不會發生。
但投影是**公開純函式**，B3 之外的 caller（含測試與未來的 per-symbol 版）不受那道閘保護。
修法：`event_keys` 欄位驗證時一併驗 `label_start_ms <= label_end_ms`。

---

## CLAUDE-R2-P3-04

**斷言**: （已裁定不改）`row_index` 為 **float** 時不擋，`np.asarray(..., dtype=int)` 會**截斷**（0.5 → 0）。

**碼證**: 探針 ③ → `**未擋**（無例外）`，與我預期一致（`expect_block=False`）。

**來源摘要**: momentum/core/split_preview.py#e2e4314c0a11

判定：**P3，維持現狀**。`SplitPlan` 之型別註記已是 `np.ndarray` 之 int 語意，
且 `__post_init__` 另有 `purge_gap < len(row_index)` 等檢查；float 列來自呼叫端型別錯誤，
不是資料品質問題。若三家認為該擋，我照辦——但我不主動加，避免把型別檢查散進每個函式。

---

## 已擋的五條（記錄，供三家複驗）

①`feature_index` 含 NaT → 已擋（`split_projection: feature_index 含 NaT`）；
②`event_keys` 缺欄 → 已擋（逐欄指名）；④`manifest` 缺 `decision_at_ms` → 已擋（`KeyError`，
訊息不夠好但確實擋住）；另加 R1 已修的三條（manifest ID 對帳、plan symbol 身份、
混合單位／負 row index）。

---

## Verdict

**不可進 B2c：`CLAUDE-R2-P1-01`。** 索引未排序會讓答案窗判定用到錯的邊界且完全靜默——
與 R1 那三條同一形態（fail-closed 寫在「數量／形狀」上，沒寫在「不變式」上）。
P2-02／P2-03 一併修（都在同一支共用 validator 附近）。P3-04 維持現狀。

🔴 **制度觀察**：我在 R2 brief 裡把這份清單列給三家，然後自己跑了一遍就找到 4 條——
這說明「brief 裡列出負向注入清單」本身就有價值，**不必等委員回來**。
下次應該在**寫完實作的當下**就跑一遍自己列的清單，而不是等派工後才想到。
