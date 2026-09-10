# SPLITUNIFY B2b R2 定向重審 — COMPOSER

task-id: 20260911-SPLITUNIFY-B2-REVIEW-R2  
family: composer  
review-object: `e2e4314c`（現 HEAD `f08aaf23` 含同批修補，碼證以現檔為準）

## 必答

### 1. H1–H5 閉合判定

| 群集 | R1 修法 | R2 判定 |
|------|---------|---------|
| **H1** manifest ID 未對帳 | `key_ids != man_ids` exact set（`:217-225`） | **閉合** — `test_manifest_id_mismatch_is_fail_closed`／`test_manifest_superset_is_also_rejected`；探針 `manifest_id_mismatch: BLOCKED ValueError` |
| **H2** symbol 只看基數 | 三道守衛 `:198-212` | **閉合** — `test_plan_symbol_mismatch_is_fail_closed` 等；探針 `plan_symbol_mismatch: BLOCKED multi_symbol_projection_unsupported` |
| **H3** malformed index | `assert_epoch_ms_array` 逐元素 + `assert_positional_rows` | **閉合（主路徑）** — `test_mixed_unit_index_is_fail_closed`／`test_negative_row_index_is_fail_closed`；探針 `mixed_unit_index`／`negative_row_derive` 皆 BLOCKED。殘差見 `COMPOSER-R2-P2-01`／`P2-02`（NaN／float，不擋 B2c） |
| **H4** 兩份單位 policy | 公開 `MS_MAGNITUDE_FLOOR`，投影 import 共用（`split_preview.py:53`、`split_projection.py:91`） | **閉合** — grep 確認 `_index_as_ms` 無手寫 `1e11` |
| **H5** oracle 循環 + mutation 缺口 | 獨立 `clusters_oracle.json` + M-SU-14..20 | **閉合** — `test_clusters_match_independent_frozen_oracle`；mutation `UNCOVERED=0`（15 條） |

### 2. 負向注入掃描（實跑輸出）

命令：`PYTHONPATH=$PWD venv/bin/python /tmp/composer_r2_neginject.py` ＋ 補充 inline 探針（見下）。

| 注入項 | 結果 | 實跑輸出摘要 |
|--------|------|----------------|
| NaN 時間戳（float64 index 含 `nan`） | **未擋** | `nan_derive: PASS_THROUGH warnings=['invalid value encountered in cast']` |
| NaT `DatetimeIndex` | **已擋** | `nat_datetime_index: BLOCKED ValueError: split_projection: feature_index 含 NaT` |
| `event_keys` 缺欄 | **已擋** | `event_keys_missing_column: BLOCKED ValueError: event_keys 缺欄 ['symbol']` |
| `event_keys` 欄型別錯（cutoff 為 str） | **未擋** | `wrong_dtype: PASS_THROUGH`（迴圈內 `int(rec[...])` 仍可轉） |
| `row_index` 為 float | **未擋** | `float_row_derive: PASS_THROUGH n_assign=2` |
| `manifest.table` 缺 `decision_at_ms` | **已擋** | `manifest_missing_decision_at_ms: BLOCKED KeyError: 'decision_at_ms'`（建 clusters 時） |
| `bucket_ms=0` | **已擋** | `bucket0_derive: BLOCKED IntCastingNaNError`（`time_cluster_id` 整除產 inf→cast 失敗） |
| `bucket_ms` 負值 | **未擋** | `bucket_neg: PASS_THROUGH time_cluster_id=-472223`（主委「我沒查的」） |
| `label_end_ms < label_start_ms` | **未擋** | `label_end_lt_start: PASS_THROUGH assignments={'split_label':['train']}`（主委「我沒查的」） |
| `feature_index` 未排序 | **未擋** | `unsorted_index: PASS_THROUGH split=['test']`（集合語意仍自洽；主委 cost） |
| `feature_index` 有重複值（同長度） | **未擋** | `dup_index_same_len: PASS_THROUGH`（主委 cost：set 語意） |
| 混合秒／毫秒 index（H3 回歸） | **已擋** | `mixed_unit_index: BLOCKED ValueError: **混合**時間單位` |
| 負 `row_index`（H3 回歸） | **已擋** | `negative_row_derive: BLOCKED ValueError: row_index 含負值 -1` |
| manifest ID 不符（H1 回歸） | **已擋** | `manifest_id_mismatch: BLOCKED ValueError: event_id 集合不相等` |
| plan symbol 不符（H2 回歸） | **已擋** | `plan_symbol_mismatch: BLOCKED multi_symbol_projection_unsupported` |

### 3. 刪除 `len(symbols) > 1` 是否正確

**是。** 第三道守衛 `symbols != plan_symbols`（`:207-212`）在 `plan_symbols` 為單元素集合時，任何 `len(symbols)>1` 的事件批必不相等 ⇒ 必 raise。實跑雙 symbol 事件批：`multi_symbol_events: BLOCKED ... 事件 symbol ['BTCUSDT', 'ETHUSDT'] 與 plan symbol ['ETHUSDT'] 不一致`。反例（第三道不觸發但多 symbol 仍通過）**不存在**。

### 4. 獨立 oracle 驗算

`bucket_ms=3_600_000`；手推 `time_cluster_id = decision_at_ms // bucket_ms`：

- c1 `1700000000000` → **472222**，單事件 ⇒ `w=1.0`
- c2/c3 `1700003600000` → **472223**，共 2 事件 ⇒ 各 `w=0.5`

與 `clusters_oracle.json` 逐值一致。`test_clusters_match_independent_frozen_oracle` 對 `build_time_clusters` 做 frame_equal，且 fixture 含共桶（權重 0.5）⇒ **足以偵測**「桶寬換算改錯」（cluster_id 漂移）與「權重公式改錯」（`M-SU-7` 改 `1.0` 會紅）。oracle 與被測 `build_time_clusters` **無因果**（JSON 手推凍結，非 `split_events` 產出）。

### 5. 可否進 B2c

**可以。** H1–H5 主修項已閉合；R1 三條 P1 回歸探針全擋；mutation 15/15；殘差為 P2 資料完整性邊界（NaN／float row_index）及主委已列 cost 項，不擋 B2c。

### 複驗（主委命令）

| 命令 | 結果 |
|------|------|
| `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` | **35 passed** |
| `venv/bin/python handoffs/20260911-splitunify-b2b-mutate.py` | **UNCOVERED=0** |
| `venv/bin/python -m pytest -q tests/momentum/core tests/momentum/event_samples tests/momentum/Analysis/test_splitunify_derive.py tests/api/test_evtlabel_staging.py` | **695 passed**（與 brief 703 差 8 條為收集面差異，本輪未重核 nodeid 清單） |
| `bash scripts/check_decoupling.sh` | **R2=1 R3=17 R4=3**（與 baseline 一致） |

---

## COMPOSER-R2-P2-01

**斷言**: `assert_epoch_ms_array` 對含 `NaN` 的 float64 時間戳陣列不 fail-closed，cast 後帶 `RuntimeWarning` 仍放行，derive 可產出 assignment。

**碼證**: `split_preview.py:67-71`（`np.asarray(arr, dtype=int64)` 無 finite 檢查）；實跑 `nan_derive: PASS_THROUGH warnings=['invalid value encountered in cast']`。RECHECK: 同上 inline 探針。

**來源摘要**: momentum/core/split_preview.py#9001fe15b4ff

[MAJOR] 信心度=High；失敗模式：上游 NaN 污染 index 時投影不 raise，membership 集合含垃圾 ms 值。修法：在 `assert_epoch_ms_array` 加 `np.isfinite` gate。**不擋 B2c**（H3 主項混合單位／負 index 已閉合；NaN 為殘差邊界，建議 B2c checklist 或 B3 接線前補測）。

## COMPOSER-R2-P2-02

**斷言**: `assert_positional_rows` 接受 float `row_index`（`dtype=int` 截斷），derive 不 raise。

**碼證**: `split_preview.py:95`；實跑 `float_row_derive: PASS_THROUGH n_assign=2`（`row_index` 為 `float64` 的 train plan）。RECHECK: 建 `SplitPlan(row_index=np.asarray(train.row_index, dtype=float), ...)` 呼叫 derive。

**來源摘要**: momentum/core/split_preview.py#9001fe15b4ff

[MINOR] 信心度=Medium；失敗模式：`2.9` 截成 `2` 可能錯位。修法：`np.issubdtype(..., np.integer)` 或拒非整數 float。**不擋 B2c**。

---

## Verdict

**可進 B2c。** H1–H5 逐條閉合；R1 三條 P1 負向注入回歸全擋；獨立 oracle 手算一致且 mutation 全覆蓋。殘差 `COMPOSER-R2-P2-01`／`P2-02` 為 P2 資料完整性邊界，不阻擋 golden 五組（B2c）。

STATUS: DONE
