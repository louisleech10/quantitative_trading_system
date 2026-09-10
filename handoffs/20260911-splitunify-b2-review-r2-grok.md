# SPLITUNIFY B2b 重審 R2（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-B2-REVIEW-R2  
family: grok  
findings-round: R2  
標的：commit `e2e4314c`（`split_projection.py`／`split_preview.py`／`test_splitunify_derive.py`／`clusters_oracle.json`／`b2b-mutate.py`）  
SCOPE: review-only；禁改碼／禁改 `docs/SPLITUNIFY_*.md`／禁改 reconcile synth  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄

### §0 前提宣告（本輪覆核）

fact-verified: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` → **35 passed**（工作區須對 HEAD 乾淨；並行 mutation 曾把 `if key_ids != man_ids` 改成 `if False`／`assert_positional_rows` 改成 `np.asarray # MUTANT`，污染時會假紅／假結果——本輪以 `/tmp/grok_r2_clean` 快照＋還原後複驗）

fact-verified: H1–H5 修法碼位——`split_projection.py:217-225` exact ID set；`:191-212` 三道 symbol 守衛且註解刪除 `len(symbols)>1`；`:227-233` 呼叫 `assert_epoch_ms_array`／`assert_positional_rows`；`split_preview.py:53-109` 公開 `MS_MAGNITUDE_FLOOR`＋逐元素／positional 守衛；`clusters_oracle.json` 手推凍結；`b2b-mutate.py` 含 M-SU-14..20（共 15+C0）

fact-verified: 負向注入（乾淨快照載入，stdout `/tmp/grok_r2_neginject_v3.out`）——見下方必答 2 表。其中 **未排序 index** 與 **數值 NaN index** 皆 **NO_RAISE** 且可造出錯誤 assignment。

fact-verified: oracle 手算 `1700000000000//3600000=472222`、`1700003600000//3600000=472223`；共桶權重 `1/2=0.5`；錯桶寬 `//3600` 會得到 `472222222`（與凍結 JSON 不同）

assumed: 生產 `feature_index` 由 FF／holdout 路徑產出且單調遞增、無 NaN  
← 否證觀測：必答 2 之反序／NaN 案在純函式入口 **未擋** 且會錯分。／本輪實跑已否證「入口可依賴上游」——公開純函式仍須自守。

---

## Verdict：不可進 B2c：GROK-R2-P1-01／GROK-R2-P1-02

H1–H5 五條 R1 修補均已閉合（身份對帳、symbol 三道守衛、逐元素單位／row 守衛、共用 `MS_MAGNITUDE_FLOOR`、獨立 oracle＋mutation 錨點）。但本輪必答 2 的負向注入證明兩條**新的靜默正確性洞**：①`feature_index` 未排序時 `test_rows[0]`≠最早 test 時刻，答案窗與集合成員錯位且不 raise；②數值 index 含 NaN 時 `assert_epoch_ms_array` 把 NaN **cast 成 0**，可讓 `cutoff=0` 的事件被誤判 train。兩者與 R1 的 H1/H2/H3 同形態（形狀／基數有閘、不變式無閘）。P2 的負 bucket／反轉答案窗不單獨擋，但應與 P1 同批修。

---

## 必答 1–5

### 1. H1–H5 逐條閉合了嗎？

| 群集 | 結論 | 碼證／實跑 |
|---|---|---|
| **H1** manifest ID | **閉合** | `:217-225` `key_ids != man_ids` raise；實跑 mismatch／superset 皆 `ValueError`含「不接受 subset」 |
| **H2** symbol 身份 | **閉合** | `:198-212` 三道有序守衛；ETH 事件×BTC plan、雙 symbol 事件皆 raise；`len(symbols)>1` 僅餘註解 |
| **H3** malformed index | **閉合（就 R1 範圍）** | 混合單位／負 row 皆 raise；`assert_epoch_ms_array` 逐元素、`assert_positional_rows` 拒負值 |
| **H4** 單位 policy | **閉合** | 公開 `MS_MAGNITUDE_FLOOR`；`_index_as_ms` 改呼叫 `assert_epoch_ms_array`；`MS_MAGNITUDE_FLOOR is _MS_MAGNITUDE_FLOOR` |
| **H5** oracle＋mutation | **閉合** | `clusters_oracle.json` 手推、測試不再以 `split_events` 為 oracle；mutate 表含 M-SU-14..20，清潔檔錨點全在 |

### 2. 負向注入掃描（逐條實跑）

探針：乾淨快照 exec（pretend `__file__`→套件路徑），命令摘要見 `/tmp/grok_r2_neginject_v3.out`。

| 注入 | 結果 | 實跑摘要 |
|---|---|---|
| NaT in DatetimeIndex | **已擋** | `ValueError: split_projection: feature_index 含 NaT` |
| NaN in numeric index | **未擋** | `NO_RAISE`；NaN→`int64` 得 **0**；把 train 列改 NaN 後 `cutoff=0` 事件被標 **train**（對照潔淨 index 則 purged）→ **GROK-R2-P1-02** |
| `event_keys` 缺 `label_end_ms` | **已擋** | `ValueError: …缺欄 ['label_end_ms']` |
| `feature_cutoff_ms` 為數字字串 | **未擋** | `NO_RAISE`；`int(str)` 後仍正確 train（型別鬆，不造錯分；P3 級） |
| `row_index` float `0.5..4.5` | **未擋** | `NO_RAISE`；`dtype=int` 截斷成 `0..4` 後當合法列用（與主委 P3 裁定一致） |
| `manifest.table` 缺 `decision_at_ms` | **已擋** | `KeyError: 'decision_at_ms'`（訊息非本票語意，但有擋） |
| `bucket_ms=0` | **已擋（巧合）** | `IntCastingNaNError`（除零→inf）；非本票語意閘 |
| `bucket_ms=-1` | **未擋** | `NO_RAISE`；`time_cluster_id=-1700000000000` → **GROK-R2-P2-03** |
| `label_end_ms < label_start_ms` | **未擋** | `NO_RAISE`；當正常事件進 assignments → **GROK-R2-P2-04** |
| `feature_index` 反序（同 positional plans） | **未擋＋算錯** | `test_rows0_ms=1700090000000` ≠ `earliest=1700000000000`；`e_train_ok` 被標成 **test** → **GROK-R2-P1-01** |
| `feature_index` 重複時間戳 | **未擋** | `NO_RAISE`；成員 set 仍可對上（嚴格遞增閘可一併擋） |

### 3. 刪掉 `len(symbols) > 1` 是對的嗎？

**是。** 反例搜索：在 guard② 迫使 `plan_symbols` 基數≤1 後，任何 `|symbols|>1` 都不可能 `symbols == plan_symbols`，故 guard③ 已覆蓋「事件批多 symbol」。實跑雙 symbol 事件→raise。

非反例：`symbol` 全為 `None` 時 `symbols=set()`，guard③ 因 `if symbols and …` 被跳過而 `NO_RAISE`——這不是「多 symbol 仍通過」，舊的 `len(symbols)>1` 同樣抓不到；不構成恢復死碼的理由。

### 4. 獨立 oracle 真的獨立嗎？

**是，且足以偵測兩類改錯。**  
手算：`decision//bucket_ms` → `472222`／`472223`；共桶 `w=1/2=0.5`，與 JSON 逐值一致。因果上 JSON 不呼叫 `split_events`／`build_time_clusters`。  
- **桶寬換算改錯**（例誤用 `3600`）：cluster id 變成 `472222222`，`assert_frame_equal` 紅。  
- **權重公式改錯**（例恆 `1.0`）：`set(got["cluster_weight"]) == {1.0, 0.5}` 紅（fixture 刻意含共桶）。

### 5. 可否進 B2c？

**不可以＋GROK-R2-P1-01／GROK-R2-P1-02。**

---

## GROK-R2-P1-01

**斷言**: `feature_index` 非時間遞增時，`test_start_ms = index_ms[test_rows[0]]` 與集合成員所用時間戳一併錯位，答案窗／train·test 歸屬會靜默算錯且不 raise。

**碼證**: `split_projection.py:240` `test_start_ms = int(index_ms[test_rows[0]])`；`:238-239` `train_ms`/`test_ms` 由同一（可能未排序）陣列索引。VERIFY 探針 `Q2_unsorted_chair_reverse`：反序 index＋原 positional plans → `test_rows0_ms=1700090000000`、`earliest_among_test_rows=1700000000000`、`mismatch=True`，且 `e_train_ok` 的 `split_label` 變成 **`test`**。RECHECK: 同上反序注入；修後應在正規化後 `np.all(np.diff(index_ms) > 0)` 失敗即 raise。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#afba86ba4a18

[BLOCKING] 信心度=High。與 R1 H3 同族：資料完整性閘只擋了單位／負索引，沒擋單調性。修法：在 `assert_epoch_ms_array`（或投影入口）加**嚴格遞增**檢查，一併擋重複時間戳（探針 `Q2_dup_ts` 目前未擋）。`holdout_boundary` 同源假設亦應共用此閘。**擋 B2c。**

---

## GROK-R2-P1-02

**斷言**: 數值型 `feature_index` 含 NaN 時不被 fail-closed；`assert_epoch_ms_array` 以 `astype("int64")` 把 NaN 變成 **0**，可使 `feature_cutoff_ms=0` 的事件被誤判為 train。

**碼證**: `split_preview.py:70-71` 非 integer dtype → `np.asarray(..., dtype="int64")`（RuntimeWarning: invalid value encountered in cast）。VERIFY：train 列位置寫入 NaN 後，`cutoff=0` 事件 → `split_label=train`；同事件在潔淨 index 上 → purged。RECHECK: `feature_index` 含 `np.nan` 必須 raise（建議 `np.isfinite` 全真），不得 cast。

**來源摘要**: momentum/core/split_preview.py#9001fe15b4ff

[BLOCKING] 信心度=High。DatetimeIndex 的 NaT 已擋，但數值 NaN 旁路仍開——同一「時間戳必須是合法 epoch ms」不變式。**擋 B2c。**

---

## GROK-R2-P2-03

**斷言**: `bucket_ms < 0` 時 `build_time_clusters` 不擋，會產出負向 `time_cluster_id`；`bucket_ms == 0` 僅靠 pandas `IntCastingNaNError` 巧合擋住。

**碼證**: `event_split.py:59-60` `decision_at_ms // bucket` 無 `bucket > 0` 檢查。VERIFY：`bucket_ms=-1` → `NO_RAISE`、`time_cluster_id=-1700000000000`；`bucket_ms=0` → `IntCastingNaNError`。RECHECK: `time_cluster_bucket_ms` 出口加 `bucket > 0`。

**來源摘要**: momentum/Analysis/event_samples/event_split.py#f9dbcfd3c9d6

[MAJOR] 信心度=High。不擋 B2c（非 H1–H5 回歸；屬 Q2 新洞），但應與 P1 同批修，避免巧合閘失效。

---

## GROK-R2-P2-04

**斷言**: `label_end_ms < label_start_ms` 的反轉答案窗不被投影擋下，會當正常事件進入 assignments／purged 邏輯。

**碼證**: `split_projection.py:244-267` 只讀 `label_end_ms` 做 `>= test_start_ms`，無 `label_start <= label_end` 檢查。VERIFY：`label_end = cutoff - H1` → `NO_RAISE` 且進 assignments。上游 `alignment.py` 有閘，但本函式為公開純函式。RECHECK: 入口驗證 `label_start_ms <= label_end_ms`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#afba86ba4a18

[MAJOR] 信心度=High。不擋 B2c（可標「不擋 B2c」），建議與 P1 同批加欄位不變式。

---

## GROK-R2-P3-05

**斷言**: `row_index` 為 float 時 `assert_positional_rows` 經 `dtype=int` 截斷（0.5→0）後當合法列使用，不 raise。

**碼證**: `split_preview.py:95` `np.asarray(rows, dtype=int)`；探針 `Q2_float_rows`／`Q2_float_truncation_effect` → `NO_RAISE`，截斷後 `[0,1,2,3,4]`。RECHECK: 若要擋，需 `np.asarray(rows)` 後断言整數值（`np.can_cast`／`arr == arr.astype(int)`）。

**來源摘要**: momentum/core/split_preview.py#9001fe15b4ff

[MINOR] 信心度=High。同意主委「維持現狀」裁定；**不擋 B2c**。呼叫端型別錯誤，非資料品質主路徑。

---

## 被當成事實的未驗證假設（§0）

1. 「`feature_index` 進投影前必單調、無 NaN」——brief／實作隱含假設；本輪 Q2 **已否證**（P1-01／P1-02）。  
2. 「15 條 mutation 已覆蓋身份與完整性主要失敗模式」——對 H1–H5 成立；對單調性／NaN／負 bucket **未覆蓋**（與 brief `assumed` 的否證觀測一致）。
