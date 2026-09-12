# SPLITUNIFY b9 consult R1 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-CONSULT-R1  
family: COMPOSER  
brief: `handoffs/20260911-SPLITUNIFY-B9-CONSULT-BRIEF.md`

## 被當成事實的未驗證假設（§0）

| 假設 | 判定 | 理由 |
|---|---|---|
| D-001 六檔即全部單鍵消費面 | **未成立** | 另至少 3 個 `event_samples/` 模組＋`event_split.build_time_clusters`＋前端 batch_facts 仍以 `event_id` 唯一；見必答 1 |
| 複合鍵可不動 `EventSplitPlan.assignments` schema | **未成立** | 投影端 `:545-556` 只寫 `event_id`/`symbol`/`split_label`；複合鍵必加 `timeframe`（或改 index 語意） |
| 現行 fail-closed 擋得住「多 TF 同批」 | **半成立** | 同一 **selected TF** 下重複 `per_tf` 列 ⇒ 在 `build_event_keys` raise；**不同 TF 各一列**（現行合法）⇒ 通過，不是 SU-RESID-2 目標態 |
| fail-closed 在合理位置（非下游意外 validate） | **fact-verified** | 閘在 producer `build_event_keys:284-288`，早於 derive／物化；見必答 5 VERIFY |

---

## 必答 1 — 消費面盤點

**立場**：D-001 六處是**主鏈**下游，但不是全部。至少再 7 類依賴 `event_id` 唯一（或等價單鍵索引）。

**掃描範圍**（本輪實跑）：`rg 'set_index\("event_id"\)|on="event_id".*validate=' momentum/Analysis/event_samples/`；延伸 `rg 'set_index\("event_id"\)' momentum/`；`rg 'event_id' api/ frontend/src/`；`tests/golden/splitunify/`。

| # | 檔案:行 | 依賴形態 | D-001 已列？ |
|---|---|---|---|
| 1 | `feature_materialization.py:53,132` | merge `many_to_one`；輸出 `set_index("event_id")` | ✓ |
| 2 | `baseline.py:105-108` | test 段以 `event_id` 交集 index | ✓ |
| 3 | `pattern_bridge.py:125` | `assign.set_index("event_id")["split_label"]` | ✓ |
| 4 | `tables.py:214,229,372-373` | receipts/clusters/assignments 皆 `set_index("event_id")` | ✓ |
| 5 | `ic_feed.py:108-141` | `events`/`per_tf` 雙 `set_index("event_id")` + `.loc[eid]` | ✓ |
| 6 | `dedupe.py:120,124-127` | merge `one_to_one`；`cluster_first` 按 cluster 留一列 | ✓ |
| 7 | `counterexample_classifier.py:52,62` | `ev_receipt.set_index` + `.loc[eid]` 純量 | ✗ |
| 8 | `candidate_ledger.py:139,155,160` | `events`/`receipts` 雙 `set_index` + `.loc[eid]` | ✗ |
| 9 | `event_split.py:70-74` | `build_time_clusters` 一 manifest 列 → 一 `event_id` 列 | ✗ |
| 10 | `split_projection.py:545-556,292` | assignments/purged 僅 `event_id`；keys merge `validate="1:1"` | producer（非 D-001 列名） |
| 11 | `ic_feed.py:56-60` `event_context_from_windows` | survivor 六鍵以排序後 `event_id` 列哈希 | ✗（IC 分析鏈） |
| 12 | `frontend/src/lib/types.ts:2932-2933` | batch_facts `t0`/`label` 陣列按 `event_id` 升冪，隱含唯一 | ✗ |
| 13 | `tests/golden/splitunify/splitunify_golden.json:3-41` | `g1_membership`/`g3b_oracle` 以 event_id 列舉 | ✗ |

**結論**：六檔是表格鏈核心，但 b9 SPEC 須把 7–13 列入觸及面或明示「仍 fail-closed／不在 b9」；否則複合鍵放行後會在 classifier／ledger／前端披露靜默錯。

---

## 必答 2 — 失效形態（會報錯 vs 靜默錯）

| 消費點 | 複合鍵後「會報錯」 | 「會靜默取錯值」 |
|---|---|---|
| `build_event_keys` | 同 selected TF 雙列仍 raise（現行） | 若改為輸出多列同 `event_id`、下游未改 ⇒ 後段全靜默 |
| `feature_materialization:132` | `groupby event_id` 合併多 TF 欄位時欄名衝突可 loud（`:28-29`） | **`set_index("event_id")` 重複 index 只留最後一列**（VERIFY 見 P1-02） |
| `pattern_bridge:125` | 交集空 ⇒ raise | **`lab_by_id[e]` 取到純量 split_label，不知哪個 TF** |
| `tables:214,229` | `ev.loc[eid]` 非唯一 index 時 pandas 可能 raise KeyError（版本依賴） | **`cl.loc[eid,"time_cluster_id"]` 非唯一時回 Series，`:257` 轉 int 行為未定** |
| `ic_feed:109,129` | 缺 per_tf 列 ⇒ raise | **同 TF 雙列 `set_index` 後 `.loc[eid]` 回 DataFrame；`:129` `int(...)` 可能抛或取錯列** |
| `dedupe:120` | events 表同 `event_id` 雙列 ⇒ **`validate="one_to_one"` MergeError**（VERIFY） | **`cluster_first` 同 cluster 內多 TF 只留 idxmin 一列**（VERIFY 見 P1-03） |
| `baseline:108` | 非有限值 loud | index 交集仍按 event_id，**多 TF 特徵列被折成一行** |
| `counterexample_classifier:62` | — | **`.loc[eid]` 非唯一時分類結果綁錯 receipt 列** |

**具體反例（靜默）**：兩列 `{event_id:a, feat:1}` 與 `{event_id:a, feat:2}` → `set_index("event_id")` ⇒ `{'feat': {'a': 2.0}}`（後者覆蓋）。

---

## 必答 3 — schema 影響

**立場**：

| 結構 | 是否必改 | 理由 |
|---|---|---|
| `receipts.per_tf` | **否（已支援多列）** | 契約本就是 `(event_id, timeframe)` 粒度；`build_event_keys:279` 先 filter selected TF |
| `EventSplitPlan.assignments` | **是** | 現欄 `["event_id","symbol","split_label"]`（`:555`）；複合鍵須加 `timeframe` 或改 MultiIndex |
| `EventSplitPlan.purged` | **是（同 assignments）** | 僅 `event_id`+`reason`（`:556`） |
| `EventSplitPlan.clusters` | **是** | `build_time_clusters:70-74` 一 manifest 列一 `event_id`；多 TF 同 event 會產生重複 `event_id` 列 |
| `receipts.event_level` | **視產品** | 現一事件一列；若 event 語意跨 TF 不變可維持，但 manifest merge `one_to_one` 會擋 |

**Golden 位移**：

- **`g5_row_fingerprint_*`**：不受 SU-RESID-2（payload 無 timeframe）。
- **`g1_membership` / `g3b_oracle`**：若 assignments 加 timeframe 或同 event_id 多列，**須擴維或新增 `g6_multi_tf_*`**；不必重算全部五組（單 TF fixture 可保留）。
- **`tests/golden/splitunify/clusters_oracle.json`**：每 event_id 一列；複合鍵後須對照更新或加 multi-TF fixture。

---

## 必答 4 — cluster 折疊語意

**立場**：**時間簇仍按事件級 interval 合併（同一 calendar 事件不同 TF 應在同一 `dedupe_cluster_id`）**；但 **`cluster_first` 保留集必改為 `(event_id, timeframe)` 粒度，不得僅按 `dedupe_cluster_id` 留一列。**

**理由**：

1. 簇語意來自 `label_start/end` overlap（`dedupe.py:67-75`），與 TF 無關——同一事件在不同 TF 的窗通常重疊，應同簇。
2. 現行 `retained("cluster_first")`（`:124-127`）在 cluster 內只留 `observation_interval_start_ms` 最早**一列**；若 manifest 含同 `event_id` 的 1h/12h 兩列且同簇，**會折掉一個 TF**（與 SU-RESID-2「每 TF 各自記帳」衝突）。
3. `all_with_uniqueness` 路徑全留，問題較小；scenario C 的 primary policy 才是硬衝突。

**反面**：若產品定義「一事件只選一個 anchor TF」，則 dedupe 折疊合理——但那就不是 SU-RESID-2 的複合鍵，而是維持 selected_timeframe 單鍵；與 b9 目標矛盾。

---

## 必答 5 — 現行 fail-closed 真實性（VERIFY）

**命令 1**（同 selected TF 雙列 ⇒ 必須擋）：

```bash
source venv/bin/activate && python -m pytest -q \
  tests/momentum/Analysis/test_splitunify_derive.py::test_build_event_keys_rejects_duplicate_per_tf_rows
```

**stdout 摘要**：`1 passed`；exception match `多列 per_tf`。

**命令 2**（producer 層直接呼叫）：

```bash
source venv/bin/activate && python - <<'PY'
from tests.momentum.Analysis.test_splitunify_derive import _receipts, SYM
from momentum.Analysis.event_samples.split_projection import build_event_keys
ev=[{"event_id":"a","symbol":SYM,"timeframe":"1h","label_start_ms":10,"label_end_ms":20}]
per_tf=[{"event_id":"a","timeframe":"1h","feature_cutoff_ms":1000},
        {"event_id":"a","timeframe":"1h","feature_cutoff_ms":2000}]
try:
    build_event_keys(_receipts(ev,per_tf), selected_timeframe="1h")
except ValueError as e:
    print("BLOCKED:", str(e)[:90])
PY
```

**stdout 摘要**：`BLOCKED: build_event_keys: timeframe='1h' 下事件有多列 per_tf：['a']——本票要求每事件恰一列（殘留 SU-RESID-2）`

**命令 3**（多 TF **不同** timeframe 各一列 ⇒ 現行**允許**，非 SU-RESID-2 目標）：

```bash
# 同上腳本，per_tf 為 1h+12h 各一列，selected_timeframe="12h" ⇒ cutoff=[9000]
```

**立場**：fail-closed **真**且位置合理（`build_event_keys`，在 `pipeline.py:747` 進 derive 之前）；但只擋「同 TF 重複」，不擋「同 event 多 TF 同批共存」——後者需 SU-RESID-2 實作後才處理，目前靠 selected_timeframe 過濾成單鍵。

---

## COMPOSER-R1-P1-01

**斷言**: D-001 所列六檔不是 `event_id` 單鍵消費面的全集；至少 `counterexample_classifier`、`candidate_ledger`、`build_time_clusters`、IC `event_context_from_windows`、前端 batch_facts、splitunify golden 仍假設唯一。

**碼證**: `rg 'set_index\("event_id"\)' momentum/Analysis/event_samples/` ⇒ 10 檔；D-001 只列 6。`counterexample_classifier.py:52`；`candidate_ledger.py:139,155`；`event_split.py:70-74`；`ic_feed.py:56-60`；`frontend/src/lib/types.ts:2932-2933`。RECHECK: 同上 rg + 讀行號。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f

[BLOCKING] 信心度=High。b9 SPEC 若只列六檔，複合鍵放行後 classifier／ledger／前端會靜默錯或 MergeError，測試未覆蓋。**修法**：延伸檔觸及面增列 7–13，或 b9 維持 fail-closed 直到全部改完。

---

## COMPOSER-R1-P1-02

**斷言**: `feature_materialization` 在複合鍵下會**靜默**丟列——`pd.DataFrame(out_rows).set_index("event_id")` 對重複 `event_id` 只保留最後一列，不 raise。

**碼證**: `feature_materialization.py:93-132`（按 event_id groupby 多 TF 後仍單 index）；VERIFY: 兩列同 event_id → `set_index` 後 `{'feat_x': {'a': 2.0}}`（後者勝）。RECHECK: 跑 brief 必答 2 反例腳本。

**來源摘要**: momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2

[BLOCKING] 信心度=High。SU-RESID-2 若只改 `build_event_keys` 不改物化，特徵表會少 TF 且記帳守恆 `:138-140` 可能仍 pass（failures 少算）。**修法**：index 改 `(event_id, timeframe)` 或 MultiIndex；assert index 唯一。

---

## COMPOSER-R1-P1-03

**斷言**: `dedupe` 的 `cluster_first` 會在複合鍵下**靜默折掉**同 event 的不同 TF——與 SU-RESID-2「各 TF 記帳」直接衝突；且 events context merge `validate="one_to_one"` 對重複 event_id 會 MergeError。

**碼證**: `dedupe.py:120`（one_to_one）；`:124-127`（cluster 內 idxmin 一列）；VERIFY: 同 event_id 雙列同 cluster ⇒ 只留 index 0；events 雙列 merge ⇒ `MergeError`。RECHECK: brief 必答 4 腳本。

**來源摘要**: momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e

[BLOCKING] 信心度=High。投影端若輸出多 TF 列，dedupe 在 scenario C 會先折疊再進 tables/baseline。**修法**：`retained` 分組鍵改 `(dedupe_cluster_id, timeframe)` 或 `(event_id, timeframe)`；manifest 一 event 多 TF 時改 merge 鍵。

---

## COMPOSER-R1-P2-01

**斷言**: 現行 fail-closed 只保證「selected timeframe 下每 event 一列 per_tf」；**不**阻擋「同批多 TF 共存」，故 brief 前提「多 TF 同批維持 fail-closed」對**跨 TF** 尚未成立——僅對**同 TF 重複**成立。

**碼證**: `build_event_keys:279-288`（dup 檢查在 filter 後）；`test_build_event_keys_picks_selected_timeframe_only`（`:933-942`）實跑多 TF 取 12h 成功。VERIFY: pytest + python 腳本（必答 5）。RECHECK: 必答 5 三命令。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#99bfddace904

[MAJOR] 信心度=High。規格若寫「多 TF 同批全擋」會與現碼不符；實際是「每 event 只投影 selected TF 一列」。**修法**：SPEC 區分 (a) 同 TF 重複 (b) 多 TF 同批；b9 目標是 (b) 的複合鍵記帳。

---

## COMPOSER-R1-P2-02

**斷言**: SU-RESID-2 必改 `EventSplitPlan.assignments`/`purged`/`clusters` schema（至少加 `timeframe`）；`receipts.per_tf` 不必改形狀。

**碼證**: `types.py:87-93`（assignments DataFrame 無 timeframe）；`split_projection.py:545-556`（列構造）；`build_time_clusters:70-74`（clusters 一 event_id 一列）。RECHECK: 讀三處 + `splitunify_golden.json` g1。

**來源摘要**: momentum/Analysis/event_samples/types.py#（EventSplitPlan dataclass 同 commit）

[MAJOR] 信心度=High。只改 producer keys 不改 plan 欄位 ⇒ downstream `set_index("event_id")` 全線假綠。**修法**：assignments 加 `timeframe`；clusters 改 `(event_id,timeframe)` 或 duplicate event_id 明示；更新 freeze 腳本。

---

## COMPOSER-R1-P2-03

**斷言**: SU-RESID-2 不必重算全部 splitunify golden，但 **g1/g3b 必擴維或新增 multi-TF 組**；g5 指紋可不動。

**碼證**: `splitunify_golden.json:3-41`（event_id 列表）；`test_splitunify_golden.py` g5 重算不含 timeframe；closeout recon `:63-64` 同判。RECHECK: `pytest tests/momentum/Analysis/test_splitunify_golden.py -q`。

**來源摘要**: tests/golden/splitunify/splitunify_golden.json#f270e007ca98

[MINOR] 信心度=High。若只改碼不增 golden，單 TF 五組仍綠但 multi-TF 路徑無回歸。**修法**：`freeze_splitunify_golden.py` 增 `g6_multi_tf_membership`（或 g1 改 dict[event_id→tf list]）。

---

## COMPOSER-R1-P3-01

**斷言**: `ic_feed.build_event_ic_inputs` 已按 `timeframe` 過濾 `per_tf`（`:109`），表格鏈 IC 消費端在**單一 anchor TF** 下語意正確；SU-RESID-2 主風險在物化／dedupe／assignments，不在 ic_feed 過濾本身。

**碼證**: `ic_feed.py:109,126-132`（按 keep event_id 迭代 + per_tf.loc）；同 TF 雙列才會炸。RECHECK: 讀 `:109-132`。

**來源摘要**: momentum/Analysis/event_samples/ic_feed.py#741f697b3964

[MINOR] 信心度=Medium。複合鍵後若 `keep` manifest 仍一 event 一列而 per_tf 多列，ic_feed 仍 OK；若 manifest 也展開多列，`:118` `ev.loc[keep["event_id"]]` 需改。**修法**：b9 先釘 manifest 是否展開 multi-TF。

---

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:  
STATUS: DONE
