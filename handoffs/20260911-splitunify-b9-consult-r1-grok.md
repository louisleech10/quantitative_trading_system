# SPLITUNIFY b9 偵察 consult R1 / grok

brief-kind=consult；家族=grok；findings-round=R1；task-id=`20260911-SPLITUNIFY-B9-CONSULT-R1`
read-only：禁改碼、禁提交規格草案。標的＝`SU-RESID-2` 多 TF 複合鍵＋D-001 六處下游單鍵面。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| # | 陳述 | 判定 | 本輪覆核 |
|---|---|---|---|
| F1 | `SU-RESID-2` 現況＝「每事件恰一個 selected per_tf row，否則 raise」 | **fact-verified** | `docs/SPLITUNIFY_TODO.md:470`；`split_projection.py:284-289`；pytest `-k rejects_duplicate_per_tf` PASS |
| F2 | D-001 明列六個下游單鍵面須一併處理 | **fact-verified** | `docs/SPLITUNIFY_SPEC.D-001.md:11,189` |
| F3 | 主委 grep 五檔單鍵假設落點 | **fact-verified（落點仍在）** | `feature_materialization.py:53,132`；`pattern_bridge.py:125`；`tables.py:214,229,372-373`；`ic_feed.py:108-109,118`；`dedupe.py:120` |
| A1 | 六個檔就是**全部**單鍵消費面 | **assumed → 本輪否證** | 見必答 1／`GROK-R1-P1-02`：至少另有 `candidate_ledger`／`counterexample_classifier`／`event_split`／`split_projection` 唯一性閘／`import_contract` |
| A2 | 複合鍵可在不動 `EventSplitPlan.assignments` schema 的前提下落地 | **assumed → 本輪否證** | 見必答 3／`GROK-R1-P1-01`：assignments／clusters 欄位契約＝`event_id` 單鍵；複合鍵必改 schema |
| A3 | 「多 TF 同批維持 fail-closed」＝任何多 TF 批都會被擋 | **assumed → 本輪部分否證** | 見必答 5／`GROK-R1-P1-03`：異 TF 多列（1h+12h）經 `selected_timeframe` **放行**；擋的是「被選 TF 下 event_id 重複」與 derive 入口 `event_id` 重複 |

---

## 必答（立場＋碼證）

### 1. 消費面盤點（六處之外還有誰？）

**立場：D-001 六處不是全部；至少還有五類單鍵依賴。**

掃描範圍：`momentum/Analysis/event_samples/**/*.py`（全目錄）、`api/`（`set_index("event_id")`／`on="event_id"`／`validate=` → **0 命中**）、`frontend/src`（無 pandas `set_index`；`event_id` 當列身分／模板，假設批內唯一）、`tests/golden/splitunify/`、`tests/momentum/**/test_*event*`。

| 類 | 檔:行 | 單鍵形態 |
|---|---|---|
| D-001 六處 | `feature_materialization.py:53,93,132`；`baseline.py:106-109`；`pattern_bridge.py:122-127`；`tables.py:214,229,372-373`；`ic_feed.py:108-109,118,126-132`；`dedupe.py:120` | merge／set_index／groupby／loc |
| 第七＋ | `candidate_ledger.py:139,155` | `events`／`event_level`.set_index("event_id") |
| 第七＋ | `counterexample_classifier.py:52` | `receipts.event_level.set_index("event_id")` |
| 投影／切分本體 | `split_projection.py:284-292,441-447,555`；`event_split.py:71,151-161` | 唯一性閘＋assignments／clusters 列契約 |
| 匯入閘 | `import_contract.py:861-865` | 批內 `duplicate_event_id` |
| 契約／前端 | `event_import_contract.json` 之 `event_id_template="{symbol}:{timeframe}:{t0}"`；`frontend/src/lib/eventId.ts` | 觸發 TF 已編進 id 字串；**不是** `(event_id, feature_tf)` 複合鍵 |
| golden | `tests/golden/splitunify/splitunify_golden.json` 之 `g1_membership`／`g3b_oracle`／`g5_answer_window` | event_id **字串清單**（無 TF 維） |

若只改六處而漏 `candidate_ledger`／`counterexample_classifier`／投影唯一性閘，複合鍵一開就會在未改路徑上 raise 或靜默錯位。

### 2. 失效形態（會報錯 vs 會靜默取錯）

**立場：現行有硬閘的路徑多數會報錯；真正危險的是「閘被拿掉／繞過」後的 set_index／groupby 塌縮，以及 materialize 本就按 event_id 折多 TF。**

#### 會報錯（實跑）

| 點 | 反例 | 觀測 |
|---|---|---|
| `build_event_keys` | 同一 event 在 selected TF 兩列 | `ValueError: …多列 per_tf：['a']——本票要求每事件恰一列（殘留 SU-RESID-2）` |
| `derive_event_split_from_plans` | event_keys 兩列同 `event_id`、異 timeframe | `ValueError: event_keys 之 event_id 重複 ['a']——集合相等吃不掉重複` |
| `dedupe.merge(..., validate="one_to_one")` | events 側 event_id 重複 | `MergeError: …not a one-to-one merge` |
| `feature_materialization.merge(..., validate="many_to_one")` | events 側 event_id 不唯一 | `MergeError: …not a many-to-one merge` |
| `ic_feed` `int(per_tf.loc[eid, …])` | per_tf index 重複 | `TypeError: cannot convert the series to int` |
| `pattern_bridge` `if lab_by_id[e] == "train"` | assignments 同 eid 兩 label | `ValueError: The truth value of a Series is ambiguous` |

#### 會靜默取到錯的值／錯語意（具體例子）

1. **`feature_materialization` 現行設計＝按 `event_id` groupby 後 `row_vals.update(...)`（`:93-130`）**：同一事件的 1h／12h 特徵欄**合併成一列**。複合鍵若語意是「每 (event_id, tf) 各自一列特徵／各自進 split」，這條路徑**不會 raise**，會靜默產出單列寬表——驗收若只看「有出 features」會假綠。
2. **`tables.py:214` `ev.loc[eid]`**：若 `event_level` 同 eid 兩列，`loc` 回 DataFrame；後續 `int(r["entry_price_source_bar_open_ms"])` 在本輪實跑為 raise。但若改寫成 `.iloc[0]`／`.values[0]` 取「第一列」⇒ **靜默用錯 TF／錯 entry 欄**（典型假修法）。
3. **`baseline.py:106-109`**：`test_ids = assignments.loc[split_label=="test","event_id"]` 後與 features.index 做 intersection。若複合鍵世界讓同一 eid 同時有 train／test 兩列（異 tf），`test_ids` 仍含該 eid 字串一次，features 若仍是單鍵 index ⇒ **整事件被當 test**，train 列被吃掉——不 raise，數值錯。
4. **golden `g1`／`g3b`**：比對的是 event_id 字串集合。複合鍵落地後若 freeze 腳本仍只 dump `event_id`，兩 TF 同 eid 會被 set 去重 ⇒ **假綠**（舊集合仍相等，新洞不紅）。

### 3. schema 影響

**立場：必須改 `EventSplitPlan.assignments` 與 `clusters` 的鍵契約；`receipts.per_tf` 已是 `(event_id, timeframe)` 形狀、不一定改欄位，但唯一性／join 契約要從「event_id 唯一」改成「(event_id, timeframe) 唯一」。**

| 物件 | 現況 | 複合鍵是否必須改 |
|---|---|---|
| `EventSplitPlan.assignments` | 欄＝`event_id, symbol, split_label`（`split_projection.py:555`；`event_split.py:161`） | **必須**加 `timeframe`（或等價複合鍵欄），否則無法表達「同事件異 TF 不同 split_label」 |
| `EventSplitPlan.clusters` | 欄＝`event_id, time_cluster_id, cluster_weight`（`event_split.py:70-74`） | **必須**決定：簇鍵留 event 級還是升成 (event_id, tf)；升則 schema 加 `timeframe` |
| `EventSplitPlan.purged` | `event_id, reason` | 若 purge 可 per-TF，**要**加 tf；若 purge 仍事件級可暫不動 |
| `receipts.per_tf` | 已有 `event_id`＋`timeframe` | 欄位可不動；唯一性語意從「selected TF 下 event_id 唯一」放寬／改寫 |
| `receipts.event_level`／manifest.table | 一事件一列（觸發 TF） | 若複合鍵只服務 **feature TF** 記帳，event_level 可維持單列；若把觸發×特徵都當獨立觀測，manifest 也要擴 |

**golden 位移**：

- **會動／須擴維**：`g1_membership`、`g3b_oracle`、`g5_answer_window`（現為 event_id 字串清單）。多 TF 成員若進同一批，必須改成 `(event_id, timeframe)` 或平行多 TF fixture，否則假綠。
- **可不因複合鍵位移**：`g5_row_fingerprint_*`（feature 列指紋）、`g4_per_symbol_n`（per-symbol 計數）——與 event 複合鍵無直接耦合；除非改 fixture 網格。
- 單 TF fixture 維持「每事件一列」時，舊集合**值**可暫留，但比對器／freeze 腳本的**結構**仍要能接受複合鍵，否則多 TF 路徑永遠沒測試。

### 4. cluster 折疊語意

**立場：dedupe 的答案窗簇應維持「同一 event_id＝同一經濟事件＝折成一個 cluster 成員」；不得讓同一事件的多個 feature TF 各算一次 overlap／uniqueness_weight。time-cluster（切分 CI 用）則應與評分粒度對齊——若分數改 per-(event_id,tf)，time-cluster 列才升格。**

理由：

1. `build_event_manifest`（`dedupe.py`）吃的是 `receipts.event_level`——**一事件一列**，簇＝label 窗 overlap／gap。同一事件多 feature TF **共享**同一 `label_start_ms`／`label_end_ms`；若拆成多列再各自進 overlap set，同一答案窗會被算多次 ⇒ uniqueness_weight／`n_events_effective` 被稀釋，cluster-robust 顯著性失真。
2. `build_time_clusters`（`event_split.py:59-74`）按 `decision_at_ms` 分桶，產出 `clusters.event_id`。現行 decision 來自 event_level（觸發錨）。feature TF 的 cutoff 不同不應自動變成多個獨立經濟簇。
3. 若產品要「每 TF 各自記帳」的是 **IC／baseline 分數** 而非答案窗去重，正確拆法是：manifest／dedupe 留 event 級；`assignments`／評分表帶 `(event_id, timeframe)`；time-cluster 用 event 級 id 做 bootstrap 重抽（同一事件多 TF 分數同簇重抽），避免把相關分數當獨立簇。

反面（未採）：各 TF 獨立 cluster——實作簡單、與複合鍵列一一對應，但會把同一 label 窗複製成多個「事件」，違反 dedupe 的經濟重疊語意。

### 5. 現行 fail-closed 的真實性（實跑）

**立場：fail-closed 真實存在，且擋在合理位置（`build_event_keys`／`derive` 入口），但文件／D-001 所謂「多 TF 同批維持 fail-closed」不可讀成「凡 per_tf 多 TF 就擋」——異 TF 多列是對齊常態且已放行。**

VERIFY 命令與摘要：

```text
# A 異 TF（1h+12h）選 12h → PASS（不擋）
build_event_keys(... selected_timeframe="12h")
→ keys=[{event_id:a, feature_cutoff_ms:9000, timeframe:12h, ...}]

# B 同 selected TF 兩列 → RAISE 於 build_event_keys
ValueError: build_event_keys: timeframe='1h' 下事件有多列 per_tf：['a']——本票要求每事件恰一列（殘留 SU-RESID-2）

# H2 手組複合鍵形 event_keys（同 eid 異 tf）送 derive → RAISE 於 derive 入口唯一性閘
ValueError: derive_event_split_from_plans: event_keys 之 event_id 重複 ['a']——集合相等吃不掉重複，會重複計數（fail-closed）

# 回歸
pytest tests/momentum/Analysis/test_splitunify_derive.py \
  -k 'build_event_keys_rejects_duplicate_per_tf or build_event_keys_picks_selected' -q
→ 2 passed
```

擋點評價：在 **keyed 投影入口**（非下游 `validate=` 偶然爆掉）——合理。缺口＝語意上「要讓異 TF 各自進 assignments」時，這兩道閘會**故意**擋死；那是殘留本身，不是閘失效。

---

## Findings

## GROK-R1-P1-01

**斷言**: 複合鍵無法在「不動 `EventSplitPlan.assignments`／`clusters` schema」的前提下落地；現欄契約以 `event_id` 為唯一身分，缺少 `timeframe` 就無法表達同事件異 TF 的不同 split／簇列。

**碼證**: assignments 建構欄＝`["event_id","symbol","split_label"]`（`split_projection.py:555`；`event_split.py:161`）；clusters＝`event_id, time_cluster_id, cluster_weight`（`event_split.py:70-74`）。derive 入口對 `event_keys`／`manifest.table` 做 `event_id` 重複 fail-closed（`split_projection.py:441-447`）。RECHECK：在 assignments 不加 tf 的情況下寫一筆「同 eid、兩 tf、兩 split_label」的往返測試——唯一性閘必紅或第二列被 set 語意吃掉。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。失敗模式：SPEC 若寫「只改下游六檔、assignments 相容 default」⇒ 實作無法表達複合鍵或被迫用字串拼接假鍵。修法：b9 SPEC 明示 assignments／clusters／（視需要）purged 的新欄位契約＋遷移／golden 擴維；禁止「schema 不動」假設。可行性：`per_tf` 已有 timeframe 欄可 join；改的是 EventSplitPlan 列契約與所有 `set_index("event_id")` 消費端。

## GROK-R1-P1-02

**斷言**: D-001 列的六個下游單鍵面**不是**完整消費面；至少 `candidate_ledger.py`、`counterexample_classifier.py`、以及投影／切分本體與匯入閘亦依賴 `event_id` 唯一，漏改會在未列路徑上 raise 或錯位。

**碼證**: `candidate_ledger.py:139,155` `set_index("event_id")`；`counterexample_classifier.py:52` 同；`import_contract.py:861-865` `duplicate_event_id`；`split_projection.py:441-447` 唯一性閘。掃描：`api/` 無對應 pandas 單鍵 merge；`frontend` 無 set_index 但 id 模板含觸發 tf。RECHECK：對 `momentum/Analysis/event_samples` 再跑 `set_index\("event_id"\)|on="event_id"|validate=.*one_to`，差集須納入 b9 TODO。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f

[BLOCKING] 信心度=High。失敗模式：只改六檔 ⇒ ledger／反例分類／匯入在多 TF 批上 MergeError 或 Series.loc 爆掉，或更糟用 iloc[0] 假修。修法：b9 消費面清單以本輪差集為準，至少含六處＋ledger＋counterexample＋投影閘改寫＋import 唯一性語意；api／frontend 列為「無 pandas 單鍵、但 id 字串契約要對讀」。

## GROK-R1-P1-03

**斷言**: 「未完成前多 TF 同批維持 fail-closed」若讀成「凡 `per_tf` 出現多個 timeframe 就擋」則為假；異 TF 多列是對齊常態且 `build_event_keys` 放行，真正 fail-closed 的是「selected TF 下 event_id 重複」與 derive 的 `event_id` 重複。

**碼證**: 實跑 CASE A（1h+12h 選 12h）→ PASS；CASE B（1h 兩列）→ `build_event_keys` RAISE（訊息含 SU-RESID-2）；H2 手組同 eid 異 tf 之 event_keys → `derive` RAISE 於唯一性閘。pytest 2 passed（`picks_selected`／`rejects_duplicate_per_tf`）。文件原文：`docs/SPLITUNIFY_SPEC.D-001.md:11,189`；`docs/SPLITUNIFY_SPEC.md:185-189`。RECHECK：重跑本檔必答 5 之 A／B／H2 三命令，結果應同文。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f

[BLOCKING] 信心度=High。失敗模式：b9 SPEC 作者按「多 TF 批現在跑不起來」設計遷移，忽略「多 feature TF + 單一 selected_timeframe」生產路徑已在跑 ⇒ 誤改對齊／materialize 的多 TF 合併行為。修法：文件改寫為「擋的是 selected-TF 歧義列與 event_id 鍵空間衝突；異 TF 多列＋單選 TF 為現行支援路徑」；複合鍵目標態＝允許同 eid 多 selected 列進入 assignments，而不是禁止 per_tf 多 TF。

## GROK-R1-P2-01

**斷言**: 複合鍵落地後若未改 `feature_materialization` 的 `groupby("event_id")`＋`row_vals.update` 折疊語意，多 TF 會**靜默**併成單列寬表，驗收只看「有 features」會假綠。

**碼證**: `feature_materialization.py:93-130` 對每個 eid 遍歷該事件全部 per_tf 列並 `update` 欄位；`:132` `set_index("event_id")`；記帳用 `nunique`（`:138`）。本輪未改碼；靜默性由控制流直接讀出（無 per-tf 唯一性 raise）。RECHECK：造兩 TF 特徵欄名不衝突之 fixture，assert 輸出列數＝事件數而非 (事件×TF) 數——現行必為前者。

**來源摘要**: momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2

[MAJOR] 信心度=High。失敗模式：assignments 已是複合鍵，features 仍單鍵 ⇒ join 丟 TF 或錯對。修法：二選一寫進 SPEC——(A) 維持「決策特徵寬表 per event」並誠實聲明複合鍵不延伸到 materialize；(B) 改 index 為 MultiIndex(event_id, timeframe) 且與 assignments 同鍵。禁止默認「改六檔就自然對」。

## GROK-R1-P2-02

**斷言**: dedupe cluster 折疊在複合鍵下應保持 event 級（同一 event_id 的多 feature TF 不得各算一次 overlap）；若 SPEC 把 cluster 列直接升成 (event_id, tf) 而不重定義 uniqueness，會稀釋 `n_events_effective`／cluster-robust 推論。

**碼證**: `dedupe.py:39-120` 只讀 `event_level` 建簇與 `validate="one_to_one"` merge；overlap 成員是 event_id 字串清單（`:89-94`）。`build_time_clusters` 同樣一列一 event_id（`event_split.py:70-74`）。RECHECK：把同一 label 窗複製成兩列 (eid,1h)/(eid,12h) 丟進現行 `build_event_manifest`——在改 schema 前會先被 `one_to_one` 擋；放寬後若各自進 overlap，weight 必變。

**來源摘要**: momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e

[MAJOR] 信心度=High。失敗模式：複合鍵「圖省事」讓 manifest 變長 ⇒ A/B 情境有效樣本與顯著性全偏。修法：SPEC 分開兩層——dedupe／答案窗簇＝event 級；assignments／評分＝可 (event_id, tf)；time-cluster bootstrap 用 event 級重抽鍵。

## GROK-R1-P2-03

**斷言**: `g1_membership`／`g3b_oracle`／`g5_answer_window` 若在複合鍵落地後仍以 event_id 字串清單比對，多 TF 路徑會因 set 去重而假綠；不必五組全重算，但这三組必須擴維或加平行多 TF golden。

**碼證**: `tests/golden/splitunify/splitunify_golden.json`：`g1`／`g3b` 為 `{train,test,purged: [event_id, …]}`；`g5_answer_window` 同為 id 清單結構。`g5_row_fingerprint_*`／`g4_per_symbol_n` 與 event 複合鍵無直接耦合。RECHECK：freeze 腳本 dump 時對同 eid 兩 tf 只寫 eid ⇒ 與單 TF 集合相等。

**來源摘要**: docs/SPLITUNIFY_TODO.md#e44da6448b01

[MAJOR] 信心度=High。失敗模式：b9 標 done、多 TF 從未打紅。修法：擴 golden 結構為複合鍵或新增 `g1_multi_tf` 平行組；單 TF 舊值可保留作回歸錨。

---

## 11 類必查（對 SU-RESID-2／D-001 殘留面；無則「無」）

1. 矛盾／互斥：見 P1-03（「多 TF 同批 fail-closed」vs 異 TF 放行）
2. 漏項：見 P1-02（六處非完整消費面）
3. 不可測驗收：見 P2-03（golden 結構不足則多 TF 不可證偽）
4. 可疑 quant 假設：見 P2-02（簇升格稀釋有效樣本）
5. 過度工程：無（本輪主張最小 schema 加欄，不新框架）
6. OOM／並行：無
7. Cache：無直接
8. API／型別／相容：assignments 加欄需預設遷移策略；api 層無 set_index 單鍵
9. 測試品質：既有 `rejects_duplicate_per_tf` 只釘單選 TF 歧義；缺「複合鍵目標態」正向／負向對
10. Agent 可執行性：本偵察可當 SPEC 輸入；SPEC 須寫死鍵契約與簇分層
11. 必要性／短命工：無（複合鍵為殘留本體，非暫代）

---

## 對主委／D-001 前提的總表（供 synth）

| 題 | 前提／主委 | 本家 |
|---|---|---|
| 六處＝全部？ | assumed | **否**；＋ledger／counterexample／投影閘／import（P1-02） |
| schema 可不動？ | assumed | **否**；assignments／clusters 必加鍵維（P1-01） |
| 多 TF 同批被擋？ | 文件口吻偏「擋」 | **只擋 selected-TF 歧義與 eid 鍵衝突**；異 TF 放行（P1-03） |
| 靜默錯？ | 要分兩類 | materialize 折疊＋baseline intersection＋golden set 去重（必答 2／P2-01／P2-03） |
| cluster 折疊 | 待裁 | **dedupe 留 event 級**；評分鍵可複合（P2-02） |
| fail-closed 位置 | 待實跑 | **在 build_event_keys／derive 入口**，合理；非下游偶然爆 |

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE
