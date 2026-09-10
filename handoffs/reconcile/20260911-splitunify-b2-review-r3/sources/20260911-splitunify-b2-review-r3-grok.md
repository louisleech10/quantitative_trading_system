# SPLITUNIFY B2b 定向確認 R3（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-B2-REVIEW-R3  
family: grok  
findings-round: R3  
標的：commit `a8474406`（`split_preview.py`／`split_projection.py`／`event_split.py`／`test_splitunify_derive.py`／`b2b-mutate.py`）  
SCOPE: review-only；禁改碼／禁改 `docs/SPLITUNIFY_*.md`／禁改 reconcile synth  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄

### §0 前提宣告（本輪覆核）

fact-verified: 因 live tree 被平行家族之 `b2b-mutate.py` 就地改寫（觀測到 `if False`／purged→train mutant），本輪全部驗收改在乾淨 worktree `git worktree add /tmp/grok_r3_wt_* a8474406` 執行；`split_projection.py#524f585c8d96`、`split_preview.py#75869791fe9f`、`event_split.py#943d0721b059`。

fact-verified: `python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py`（worktree）→ **43 passed**（`/tmp/grok_r3_derive_clean.log`）。

fact-verified: `python handoffs/20260911-splitunify-b2b-mutate.py`（worktree＋venv symlink）→ **UNCOVERED=0**，21 條全 rc=1、C0 rc=0（`/tmp/grok_r3_mutate_clean.log`）。

fact-verified: R2 九條負向注入重放 → **9/9 全擋**（`/tmp/grok_r3_ni_r2replay.out`）。

fact-verified: `bash scripts/check_decoupling.sh` stdout 含 `R2=1 R3=17 R4=3`（與 baseline 逐值相等；腳本整體 rc=1 因既有違規，非本票新增）。

fact-verified: 新一批負向注入（`/tmp/grok_r3_neginject.py`／`/tmp/grok_r3_neginject.out`＋`/tmp/grok_r3_dt_unsorted.out`）——見必答 2。其中 **反序 DatetimeIndex** 與 **重複 DatetimeIndex** 皆 **NO_RAISE**，且反序案把 `e_train_ok` 錯標成 **test**。

assumed: 「I1 之嚴格遞增已涵蓋一切 `feature_index` 入口」  
← 否證觀測：`_index_as_ms`／`holdout_boundary` 對 `DatetimeIndex` **跳過** `assert_epoch_ms_array(..., strictly_increasing=True)`；數值路徑有擋、Datetime 路徑無擋。／本輪實跑已否證。

---

## Verdict：不可進 B2c：GROK-R3-P1-01

I2–I6 與 R2 九條負向注入均已閉合（mutation M-SU-21..26 全紅、C0 綠）。但 I1 **只閉合數值型 `feature_index`**：`DatetimeIndex` 分支只驗 NaT、不驗嚴格遞增／重複，反序時 `test_rows[0]` 不再是最早 test 時刻，答案窗與集合成員錯位且不 raise——與 R2 之 `GROK-R2-P1-01` **同一失敗模式**，只是旁路換到生產更常見的型別。既有 I1 測試只用 `pd.Index(int64)[::-1]`，未覆蓋 Datetime。此為擋 B2c 的 P1。另有 `symbol is None` 旁路（P2，不擋）。

---

## 必答 1–4

### 1. I1–I6 逐條閉合了嗎？

| 群集 | 結論 | 碼證／實跑 |
|---|---|---|
| **I1** 索引嚴格遞增 | **未閉合＋GROK-R3-P1-01** | 數值：`assert_epoch_ms_array(..., strictly_increasing=True)` 有擋（R2 重放⑧⑨、M-SU-21）。**DatetimeIndex**：`_index_as_ms:87-90` 直接 `asi8//1e6` 返回；`holdout_boundary:222` 以 `not isinstance(..., DatetimeIndex)` 跳過。實跑反序 DT → `PASS_THROUGH` 且 `e_train_ok→test` |
| **I2** NaN→0 | **閉合** | cast 前 `isfinite`；重放／`I_nan_numeric_index` BLOCKED；M-SU-22 rc=1 |
| **I3** event_id 唯一 | **閉合** | `event_keys`／`manifest.table` 各自 `duplicated`；`I_dup_event_id` BLOCKED；M-SU-23 rc=1 |
| **I4** float row_index | **閉合** | `assert_positional_rows` cast 前整數性；R2 重放③／`I_float_row_index` BLOCKED；M-SU-24 rc=1 |
| **I5** 事件欄完整性 | **閉合** | `_assert_event_keys_wellformed`；反轉窗／R2 重放⑦ BLOCKED；M-SU-25 rc=1；同戳事件欄允許（`J`／`test_event_keys_may_share_timestamps`） |
| **I6** bucket_ms≤0 | **閉合** | `time_cluster_bucket_ms` 正值閘；0／-1 皆本票語意 `ValueError`；M-SU-26 rc=1 |

### 2. 新一批負向注入（非 R2 那九條；逐條實跑）

探針：`/tmp/grok_r3_neginject.py`＋Datetime 專項 `/tmp/grok_r3_dt_unsorted.out`／`/tmp/grok_r3_dt_dup.out`；模組載自 worktree `a8474406`。

| 注入 | 結果 | 實跑摘要 |
|---|---|---|
| `event_keys.symbol is None`（全列） | **未擋** | `NO_RAISE`；`assign=[{'event_id':'a','symbol':None,'split_label':'train'}]` → **GROK-R3-P2-02** |
| `symbol=""` | **已擋** | `ValueError: …事件 symbol [''] 與 plan symbol ['ETHUSDT'] 不一致` |
| `symbol` 混型（int `12345`） | **已擋** | 同上（`['12345']`≠plan） |
| `symbol=nan`／`pd.NA`／`' '` | **已擋** | `str(nan)='nan'`／`'<NA>'`／`' '` 皆觸發 symbol 集合不相等 |
| `manifest.summary` 缺 `n_events_raw` | **已擋** | `KeyError: 'n_events_raw'`（可讀性差，但有擋；不另立 finding） |
| `time_bounds` 謊稱覆蓋 hole、`row_index` 不含 | **未擋例外，行為正確** | hole → `purged`（`interval_crosses_split_boundary`）；成員判定仍走 row 集合，**非洞** |
| `feature_index` 全同一值（數值） | **已擋** | `非嚴格遞增…重複（共 99 處）`（boundary／derive／assert 三入口） |
| 超大 `bucket_ms=1e15` | **未擋＝預期** | 三事件同一簇、`weights≈1/3`；桶寬語意下合法 |
| 單列 cutoff＝train 末根、label 未跨界 | **未擋＝正確** | `split_label=train` |
| 單列 cutoff＝test 首根 | **未擋＝正確** | `split_label=test` |
| train cutoff＋`label_end==test_start` | **未擋例外＝正確 purge** | `purged`（`>=` 邊界） |
| **反序 DatetimeIndex**（同 positional plans） | **未擋＋算錯** | `test_rows0_ms≠earliest`；`e_train_ok→test`（對照 sorted DT 為 train）→ **GROK-R3-P1-01** |
| **重複戳 DatetimeIndex** | **未擋** | `DUP_DT_PASS`；同內容數值 index → `DUP_NUM_BLOCKED` |
| 事件欄共用時間戳（反向保護） | **未擋＝正確** | `['s1','s2']` 皆 assign |

### 3. `strictly_increasing` 只套 `feature_index` 是對的嗎？

**對事件欄放寬：是對的，未留單調性洞。**  
實跑：兩事件同 bar → `NO_RAISE`；事件欄故意反序 → 仍依集合正確標 train／test。事件列順序不進 `test_rows[0]` 邊界公式。

**但 `feature_index` 本身的嚴格遞增閘不完整：** 只綁在數值路徑；`DatetimeIndex` 旁路使 I1 形同只測了一半型別面（見 P1-01）。這不是「事件欄放寬」造成的洞，是 **feature_index 雙路徑不一致**。

### 4. 可否進 B2c？

**不可以＋GROK-R3-P1-01。**

---

## GROK-R3-P1-01

**斷言**: I1 未閉合：`DatetimeIndex` 的 `feature_index`（以及 `holdout_boundary` 的 Datetime 入口）跳過嚴格遞增／去重檢查，反序時會靜默錯分 train／test，與 R2 數值反序洞同一機制。

**碼證**: `split_projection.py:87-90` Datetime 分支只擋 NaT 後直接返回 ms；`:91-93` 的 `strictly_increasing=True` 僅數值分支。`split_preview.py:222-226` `holdout_boundary` 以 `not isinstance(..., DatetimeIndex)` 跳過同一閘。VERIFY（worktree `a8474406`）：反序 DT＋原 positional plans → `PASS_THROUGH`、`mismatch=True`、`e_train_ok` 之 `split_label=test`（sorted DT 對照為 `train`）；重複 DT → `DUP_DT_PASS`，同值數值 index → `ValueError…重複`。既有 `test_unsorted_feature_index_is_fail_closed` 只用 `pd.Index(int64)[::-1]`，未覆蓋 DT。RECHECK: 反序／重複 `DatetimeIndex` 餵 `derive_event_split_from_plans` 與 `holdout_boundary` 皆應 raise；修法建議 Datetime 轉 ms 後仍走 `assert_epoch_ms_array(..., strictly_increasing=True)`（或等價 `is_monotonic_increasing` 且無重複）。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#524f585c8d96;momentum/core/split_preview.py#75869791fe9f

[BLOCKING] 信心度=High。不改會怎麼在 B2c／B3 失敗：B3／生產特徵索引常為 `DatetimeIndex`；若順序被打亂或含重複戳，投影不 raise 卻把 train 事件標成 test（或答案窗邊界錯位）→ golden（G-1／G-3）若只以數值 fixture 綠燈會**假綠**，接線後 OOS 標籤／purge 集合同步錯。與 I1 原採納理由相同，故 **擋 B2c**。

---

## GROK-R3-P2-02

**斷言**: `event_keys.symbol` 全為 `None` 時，symbol 三道守衛因 `if s is not None`／`if symbols and …` 被跳過，投影 `NO_RAISE` 並輸出 `symbol=None` 的 train assignment。

**碼證**: `split_projection.py:214` `symbols={str(s) … if s is not None}`；`:236` `if symbols and symbols != plan_symbols`。VERIFY：`A_symbol_None` → `PASS_THROUGH assign=[{…'symbol':None,'split_label':'train'}]`；對照 `""`／`nan`／`pd.NA`／`' '` 皆 BLOCKED。RECHECK: 空／None symbol 應 fail-closed（與 `split_events` 對 manifest 缺 symbol 的閘對齊）。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#524f585c8d96

[MAJOR] 信心度=High。**不擋 B2c**（B2c golden／B3 `build_event_keys` 上游通常帶非空 symbol；`split_events` 另有 symbol 閘）。屬公開純函式殘留不變式，建議 B3 接線前補或記入 `SU-RESID-*`。

---

## 被當成事實的未驗證假設（§0）

1. 「I1 嚴格遞增已覆蓋所有 `feature_index` 型別」——**assumed，本輪否證**（Datetime 旁路）。
2. 「輸入不變式已被 21 mutation＋9 負向系統性覆蓋」——對**數值路徑** fact-verified；對 Datetime 遞增 **未覆蓋**（測試與 mutation 皆未打 DT 反序）。

ASSUMPTIONS_VERIFIED: I2–I6 閉合（碼位+R2 九條重放+M-SU-21..26）；I1 數值閉合、Datetime 未閉合（反序錯分實跑）；事件欄不套單調性正確；symbol=None 旁路實跑。
TESTS_RUN: worktree `pytest …test_splitunify_derive.py` → 43 passed；worktree mutation → UNCOVERED=0／C0=0；R2 九條重放 9/9；新負向批次見 `/tmp/grok_r3_neginject.out`＋DT 專項；decoupling `R2=1 R3=17 R4=3`。
FAILURES_SEEN: live tree 被平行 mutate 污染致首跑 derive 假紅／mutation UNCOVERED=12 → 改 worktree 後消除；非產品回歸。
SCOPE_CHANGES: none（review-only）。
NUMERIC_OR_SCHEMA_IMPACT: none。

STATUS: DONE
