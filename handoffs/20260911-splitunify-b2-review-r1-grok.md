# SPLITUNIFY B2b code review R1（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-B2-REVIEW-R1  
family: grok  
findings-round: R1  
標的：commit `864efeb9`（`split_projection.py` 新／`event_split.py` 抽出／`test_splitunify_derive.py` 24 條／`b2b-mutate.py`）  
規格：`docs/SPLITUNIFY_SPEC.md`（v5）C-2‥C-5＋Task 2.2；凍結鏈 `docs/GAP3_EVENT_SPEC_AMENDMENTS.md` A-2  
SCOPE: review-only；禁改碼／禁改 `docs/SPLITUNIFY_*.md`／禁改 reconcile synth  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄

### §0 前提宣告（本輪覆核）

fact-verified: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` → **24 passed** rc=0

fact-verified: `venv/bin/python handoffs/20260911-splitunify-b2b-mutate.py` → 9 mutant 全 rc=1、C0 rc=0、**UNCOVERED=0**

fact-verified: 兩段式與 A-2／C-4 對位——`split_projection.py:201-203` 先驗空 `test_rows` raise；`:221` 用 `>=`（非 `>`）；第一段條件含 `in_train`；不減 embargo；`test_start_ms = index_ms[test_rows[0]]`

fact-verified: `build_time_clusters` 為抽出非複製——`event_split.py:51-66` 唯一實作；`split_events:160-161` 與 `derive…:238` 共同呼叫；混 TF＋顯式 `bucket_ms` 時 helper 與 `split_events.clusters` **`.equals` True**

fact-verified: M-SU-4 hole fixture 真能分辨——洞在 `time_bounds` 內但∉ train 集合 ⇒ 集合語意 purged、區間語意會誤判 train（實跑 `hole_ms in train_set=False`、`interval would say train=True`、實作 purged=`['e_hole']`）

fact-verified: `_index_as_ms` 門檻字面 `1e11`，**未**引用 `split_preview._MS_MAGNITUDE_FLOOR`；秒級輸入兩邊皆 raise；**零值／混合量級已分歧**（見 P2-01）

fact-verified: `event_level` 重複 `event_id` ⇒ pandas `MergeError: Merge keys are not unique in left dataset`（`validate="1:1"` fail-closed）

assumed: 生產 `SplitPlan.row_index` 由 `holdout_boundary` 產出、遞增排列 ⇒ `test_rows[0]`＝最早 test 列（與 A-2 字面一致）  
← 否證觀測：呼叫端傳入未排序 `row_index` 時 `test_start_ms` 可能不是最小 test 時間戳。／本輪未改契約；B3 接線須沿用 builder 產出。

assumed（brief 前提，本輪打過）: 抽出後空 table／混 TF 可能變 clusters → **未成立於可構造的合法形狀**：混 TF＋`bucket_ms` 逐值相同；無 `bucket_ms` 兩邊同 raise「批內多 TF」。空表缺欄時 helper 先 `KeyError`、`split_events` 先查 symbol——皆非生產 manifest 形狀。

---

## Verdict：可進 B2c

兩段式判定與 A-2／C-4 字面一致（`>=`、只作用 train、空 test 先 raise、不減 embargo）；clusters 已真正抽出共用；24 測＋9 mutation 自證通過。殘留為單位守衛雙份（P2-01）與答案窗 mutation／fixture 粒度缺口（P2-02）——**不擋** golden 五組開工，但 B2c／後續應把 P2-02 的毫秒級 negative case 與 `>=`→`>` mutant 納入（或進 B2c 的 G-5.4 補強）。

---

## 必答 1–7

### 1. 兩段式判定是否忠實於契約？

**是。** 逐項對 A-2 code fence 與 SPEC C-4：

| 契約點 | 碼證 | 結果 |
|---|---|---|
| 空 `test_rows` 在比較前 raise | `split_projection.py:201-203` | 先於 `:207` 的 `test_start_ms` |
| `test_start_ms = as_ms(index[test_rows[0]])` | `:207` | 用 `_index_as_ms` 後索引，**不**用 `time_bounds` |
| `train_cutoff and label_end >= test_start` | `:221` `in_train and … >= test_start_ms` | `>=` 保留；有 `test_answer_window_boundary_is_ge_not_gt` |
| 第一段**只**作用 train | `:221` 含 `in_train`；`test_answer_window_not_applied_to_test_side_events` | test 側不誤 purge |
| 不再減 embargo | 全檔無 `embargo` 毫秒相減 | 與 A-2「已含在 `row_index[0]`」一致 |
| 第二段集合判定 | `:213-214` `cutoff in train_ms/test_ms`；皆不在 → `:234` purge | 禁區間（M-SU-4 紅） |

順序：雙落 raise → 答案窗 purge → 集合成員。與「先後不可調」一致。

### 2. 有沒有第二份算術漏網？`_index_as_ms` vs `_as_ms` 算不算？

**切分／分簇／權重：沒有第二份。**  
`build_time_clusters`／`time_cluster_bucket_ms`／`_cluster_weight`／`_degraded_flags` 皆呼叫 `event_split` 唯一實作；投影不自算 bucket 公式、不自算 holdout 邊界。

**單位守衛：算第二份（門檻副本），不是切分算術副本。**  
立場：`_index_as_ms`（整段 index→ms 陣列）與 `_as_ms`（單點）API 不同、並存合理；但秒級門檻應共用 `_MS_MAGNITUDE_FLOOR`。現況 `_index_as_ms` 手寫 `1e11`，且零值／混合量級語意已與 `_as_ms` 分歧（見 **GROK-R1-P2-01**）。改其中一支門檻，另一支測試不會紅——brief 前提成立。

### 3. `build_event_keys` 的 keyed join 擋得住 positional 錯位嗎？

**擋得住列序錯位；`validate="1:1"` 對重複鍵 fail-closed。**

- 對位：`event_level.merge(selected[…], on="event_id", how="inner", validate="1:1")`（`split_projection.py:130-132`）
- 反序 fixture：`test_build_event_keys_joins_by_event_id_not_position` 釘死 cutoff 不隨列序對調
- 選中 TF 下 `per_tf` 重複 `event_id`：先於 merge 顯式 raise（`:124-128`）
- `event_level` 本身重複 `event_id`：無顯式預檢，但 `validate="1:1"` → `MergeError: Merge keys are not unique in left dataset`（實跑確認）。**夠擋錯分**；訊息是 pandas 內部句，可讀性一般（brief「我沒查」項——屬 UX，不擋 B2c）

### 4. `_build_summary` 的 12 鍵語意？

**12 鍵齊全且與 C-5／舊 `split_events` 鍵名對齊**（`test_summary_has_all_twelve_keys`）。

- **`avg_cluster_size` 分母**：`n_clusters = clusters["time_cluster_id"].nunique()`（空→0），`len(clusters)/max(1,n_clusters)`——與 `event_split.py:169-170` 同形。
- **`insufficient_events_in_test`**：`[s for s in per_symbol_n if n_test < tier_min]`（`:278`），`n_test`＝投影後 test 指派數；`tier_min_test_events` 預設 **1** 且簽名未暴露。  
  對比舊路：`split_events:149-151` **逐 symbol** 計該 symbol 的 test 數。  
  **在現行多 symbol fail-closed 下存活路徑恆 `n_symbols==1`，兩者等價**；SPEC Task 2.2 要點 6 亦明文「改看投影後的 test 數」。若日後打開 per-symbol（R-1），此實作會把「聚合 test 不足」展開成列出**所有** symbol——須重寫。屬已知殘留語意，**不是本輪實作違約**。  
  `single_symbol` 恆亮＝預期（C-5／Task 2.2 要點 6）。

### 5. `event_split.py` 抽出有沒有改到行為？bucket 算兩次？

**未改到可觀測行為。** `split_events:160-161` 先算 `bucket` 寫 summary，再呼叫 `build_time_clusters`（內部 `:59` 再算一次）。`time_cluster_bucket_ms` 純函式＋相同引數 ⇒ 兩次結果必同（實跑 `b1==b2==H1`）。10k 事件級多一次 dict 查找／TF set，可忽略；分簇本身仍是向量化 `// bucket`。

混 TF／空表：見 §0——brief「抽出前後可能不同」之否證觀測**未重現**於合法形狀。`test_clusters_byte_identical_to_legacy_split_events` 含共桶權重 0.5，擋「權重寫死 1.0」。

### 6. mutation 表夠不夠？缺哪些？

**現有 9 條對其錨點足夠（UNCOVERED=0）；對答案窗邊界語意仍偏粗。** 建議補：

| ID | 改壞哪一行 | 哪個測試應紅 |
|---|---|---|
| **M-SU-14**（建議） | `:221` 把 `>=` 改成 `>` | 已有 `test_answer_window_boundary_is_ge_not_gt`；請納入 mutate 腳本（現只靠單元測、不在 9 條表內） |
| **M-SU-15**（建議） | `:207` 改成 `int(test_plan.time_bounds[0])` | **現有 fixture 全綠**（`_plans` 令 `time_bounds[0]==index[test_rows[0]]`）。需新測：刻意讓 `time_bounds` 與 `row_index[0]` 錯位，斷言仍以 row 為準 |
| **M-SU-16**（建議） | `:221` 改成 `>= test_start_ms - 1` | **現有 H1 對齊 fixture 全綠**（見下）；需 `label_end_ms = test_start_ms - 1` 的 train 事件斷言**不得** purge |

🔴 **「只在 fixture 失效、真實資料仍紅」的改壞法**：  
把 `>= test_start_ms` 改成 `>= test_start_ms - 1`。Fixture 的 `label_end` 不是恰好 `test_start` 就是至少差一整根 `H1`（3.6e6 ms），`-1` ms 擋不住 exact 案、也不會誤傷 `e_train_ok`；真實／毫秒級答案窗若出現 `test_start-1` 會被**過度 purge**，而今日綠徑看不出。對稱地，改用同步的 `time_bounds[0]` 在今日 fixture 上也是假綠。見 **GROK-R1-P2-02**。

### 7. 可否進 B2c？

**可以。** 判準：契約兩段式＋集合語意＋抽出共用已落地並有 mutation 自證；P2 為守衛共用與測試粒度，不否定 golden 凍結前提。B2c 建議把 G-5.4／mutate 補上 M-SU-14‥16 類毫秒級／`time_bounds` 錯位案。

---

## GROK-R1-P2-01

**斷言**: `split_projection._index_as_ms` 與 `split_preview._as_ms` 是兩份獨立的秒級門檻守衛（前者手寫 `1e11`、後者用 `_MS_MAGNITUDE_FLOOR`），且零值／混合量級語意已分歧；改其一不會令另一側測試變紅。

**碼證**: `momentum/core/split_preview.py:51-80`（`_MS_MAGNITUDE_FLOOR=1e11`；`if as_int and abs(as_int) < floor` ⇒ **0 放行**）；`momentum/Analysis/event_samples/split_projection.py:87-91`（字面 `1e11`；`np.all(|v|<1e11)` ⇒ **`[0]` raise**；混合 `[1.7e12, 1.7e9]` **整段放行**）。VERIFY: 本輪探針 stdout 摘要：`as_ms(0)=0`／`index_as_ms([0]) RAISE`／`index_as_ms(mixed)=[1700000000000, 1700000000]`。RECHECK: 同上三案＋確認 `_index_as_ms` 源碼不含 `_MS_MAGNITUDE_FLOOR`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#735445c7ccfc

[MAJOR] 信心度=High。失敗模式：日後只改一邊門檻或放寬混合陣列，B2a 邊界 ms 與 B2b 投影集合用不同單位閘，秒級 FF `timestamps.parquet` 可能一邊 raise 一邊靜默錯 1000 倍。修法：`_index_as_ms` 改 import／共用 `_MS_MAGNITUDE_FLOOR`；混合量級改 fail-closed（任一元素像秒即 raise）；補對測「改 floor ⇒ 兩側同紅」。不擋 B2c，但應進殘留或 B2c checklist。

---

## GROK-R1-P2-02

**斷言**: 現有答案窗 mutation／fixture 擋得住「整段刪除第一段」（M-SU-13）與「`>=`→`>`」（單元測），但擋不住「`>= test_start_ms - 1`」與「改讀已同步的 `time_bounds[0]`」——這兩類在 H1 對齊 fixture 上維持全綠，卻會在毫秒級或 bounds 漂移的真實輸入上錯 purge。

**碼證**: `test_splitunify_derive.py:112-118`／`:152-159`（`label_end`∈{`cutoff+H1`, `test_start`}）；`handoffs/20260911-splitunify-b2b-mutate.py` MUTANTS 無 `>=`→`>`、無 `time_bounds` 替換。VERIFY 探針：`label_end=test_start-1` 時正確碼不 purge、`-1` mutant 會 purge；`_plans` 下 `time_bounds[0]==index[test_rows[0]]` 恆真。RECHECK: 加一筆 `label_end_ms=test_start_ms-1` 的 train 事件斷言仍在 `assignments`；另造 `time_bounds[0]=test_start+H1` 且 `row_index` 不變，斷言仍 purge `label_end==true_test_start`。

**來源摘要**: tests/momentum/Analysis/test_splitunify_derive.py#4d7eacec7fd5

[MAJOR] 信心度=High。失敗模式：實作被改成微偏的答案窗比較或改信 `time_bounds` 時，B2b 綠、B2c golden 若仍用同形 H1 fixture 也綠，直到非對齊真實批才露出 OOS／過度 purge。修法：mutate 表加 M-SU-14‥16（見必答 6）；B2c G-5.4 至少含 `test_start-1` 與 bounds 錯位各一案。不擋開工，擋的是「以為 mutation 已封死答案窗」的過度自信。

---

## 被當成事實的未驗證假設（§0）

1. brief assumed「抽出後空 table／混 TF clusters 可能變」→ 本輪打過，**合法形狀下不成立**（見必答 5）。  
2. brief assumed「兩支秒守衛門檻一致不會漂」→ **門檻數字目前同為 1e11，但已非同一常數、且零／混合語意已漂**（P2-01）。  
3. 「`validate="1:1"` 對 `event_level` 重複鍵的訊息可讀」→ 本輪確認是 pandas `MergeError`；可讀性普通，不另列 blocking。

STATUS: DONE
