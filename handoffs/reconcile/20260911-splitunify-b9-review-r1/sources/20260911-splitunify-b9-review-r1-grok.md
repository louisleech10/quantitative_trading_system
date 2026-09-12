# SPLITUNIFY D-002 延伸檔找碴 R1 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R1`  
family: grok  
findings-round: R1  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（commit `c4bf6229`）  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r1/`（交件後清除）

## §0 被當成事實的未驗證假設（挑戰前提）

fact-verified: 跨 TF 不 fail-closed；未選 TF 靜默丟棄 → 手動 discard 計數 `input 4 / selected 2 / DISCARD_BY_TF {'4h': 2}`，與 brief／codex Probe A 同形

fact-verified: `g5` 指紋 payload 不含 `timeframe` → 讀 `build_row_time_fingerprint` 源碼；同輸入重算 `G5_SAME True`

fact-verified: 同事件 pair 列（同 `decision_at_ms`）→ 同 `time_cluster_id` → `build_time_clusters` 探針 `E1_CLUSTER_IDS [472222, 472222]`

assumed: 15 處＝全部單鍵消費面 → **否證**：第 16+ 處 `pipeline.py:760-762`、`EventTablesPanel.tsx:361`、`test_splitunify_wiring.py:103-104,113`（見 P1-01）；且 Task 9.3 漏 groupby 折疊（P1-02）

assumed: Phase 9A 可獨立回退、不需連動 9B → **部分成立**：`rg discarded_per_tf` 僅命中 D-002 ⇒ 無硬消費者、技術可回退；但 9A 未規定 API/UI 透傳（P2-03）

assumed: 同事件不同 TF 應同簇 → **支持**（反例構造失敗；分叉 decision 非現行 event_level 模型）

assumed: D-002 已吸收偵察之混側風險 → **否證**：全文無混側／同側契約（P1-03）

assumed: `doc_format_precheck` rc=0 與交叉引用掃描 → **本輪未重跑**（trust brief；不阻 finding）

| 陳述 | 判定 | 本輪覆核 |
|---|---|---|
| 跨 TF 靜默丟棄 | fact-verified | 見上 discard 計數 |
| 15 處完整 | assumed→否證 | P1-01／P1-02 |
| 9A 獨立回退 | assumed→部分成立 | 技術可；UI 缺口 P2-03 |
| 同事件同簇 | assumed→支持 | 反例失敗 |
| g5 不受複合鍵影響 | fact-verified（公式） | P2-02 釐清 fixture |

---

## 必答 1–5（成對立場）

### 1. 觸及面完整性

**立場：15 處不完整。**

掃描範圍與方法：

- `grep -rn 'set_index("event_id")'` → `momentum/Analysis/event_samples/`（生產 7 檔）＋ tests
- `momentum/Analysis/event_samples/*.py` 全目錄：`merge`／`groupby("event_id")`／`validate=`／`.loc[eid]`
- `api/services/`：`event_id` × `dict(`／`len(`／`by_id`（逐模式過濾；**未**逐檔精讀全部服務，與 D-002 §N 誠實邊界一致）
- `frontend/src`：`byEventId`／`n_train`／`n_events`／`Map`
- `tests/golden/splitunify/*`

**第 16+ 處（檔:行）**：

| # | 位置 | 為何算消費／混用面 |
|---|---|---|
| 16 | `pipeline.py:760-762` | `n_train`／`n_test`／`n_purged`＝assignment／purged **列數** |
| 17 | `EventTablesPanel.tsx:361` | 無單位顯示上列三數（當事件數讀） |
| 18 | `test_splitunify_wiring.py:103-104,113` | `dict(zip(event_id,…))` 後蓋前；且 `n_train+n_test+n_purged == len(records)` 假設事件級 |

另：觸及面 #5 雖列 `feature_materialization` 之 `set_index`，但**真正折疊**在 `:93` 的 `groupby("event_id")+row_vals.update`——Task 9.3 改法字面蓋不到（P1-02）。

### 2. 兩階段切分（9A→9B）

**立場：順序正確；9A 技術上可獨立回退；但 9A 規格對「誰看得到揭露」不完整。**

- 9A 先消「靜默丟棄無記帳」再動 15+ 處 schema，成本／風險排序合理。
- 中間態：summary 有 `discarded_per_tf_rows_by_timeframe`、assignments 仍單 TF——屬**刻意**誠實揭露，不是正確性分裂。
- 回退：現無下游硬依賴該鍵 ⇒ 移除 summary 欄可回退。
- 缺口：Task 9.1 檔案清單無 `api/`／`frontend/` ⇒ 9A 合併後 UI 仍可能看不到丟棄（P2-03）。**不**因此主張「必須一次做完 9A+9B」。

### 3. cluster 語意

**立場：支持「同事件不同 TF 同簇」。反例構造失敗。**

嘗試：

1. 同 `e1` 兩 TF、同 `decision_at_ms` → `time_cluster_id` 相同（探針 `E1_CLUSTER_IDS [472222, 472222]`）。
2. 強制 per-TF `decision_at_ms` 差一個 bucket → 會分簇，但現行 alignment 的 `event_level` **一事件一 decision**，此前提不成立；要分簇須先改經濟事件模型，超出 D-002。
3. 以「混側 split（1h=train／4h=test）」當分簇理由 → cluster 仍同；混側是 **split 一致性**問題（P1-03），不是 cluster 反例。

### 4. 事件數與列數分離

**立場：D-002 §C／Task 9.2 有原則，但落地消費點未入觸及面／Task。**

會把列數當事件數（或等價假設）之處：

| 位置 | 形態 |
|---|---|
| `pipeline.py:760-762` | `n_train`／`n_test`／`n_purged`＝列和 |
| `EventTablesPanel.tsx:361` | 顯示上列、無「事件 vs 列」單位 |
| `test_splitunify_wiring.py:113` | 三數之和＝`len(records)` |
| `split_projection._build_summary` 之 `n_test`／`per_symbol_test_n` | 取自 assignment 列（單 TF 時＝事件數；複合鍵後漂移） |
| `baseline.py:120` | `n_test=len(idx)`（交集列） |
| `ic_feed.py:115` | `n_events=len(keep)` |

探針：`records=2`、assignment 4 列 ⇒ `n_train+n_test=4`、`wiring_eq False`。

### 5. §G 與 mutation

1. **`g5` 不受複合鍵影響**：**公式面成立**（payload 無 TF）。若為 `M-SU-D1-23` **改寫**主 fixture 為兩標的交錯，positions／ms／sha **會**動——須與「單 TF 舊值保留為錨」並陳釐清（P2-02）。
2. **`M-SU-D2-01`～`06` 不足**：未覆蓋 pipeline 記帳、wiring `dict(zip)`、`groupby` 折疊、混側 split、#13 survivor hash；`02` 一條「`set_index` 保留單鍵」蓋不住靜默面 5／7／8／9／11／12 的**逐處**失效（P2-01）。

---

## GROK-R1-P1-01

**斷言**: D-002「15 處單鍵消費面」漏列記帳／報告鏈；9B 後 `pipeline` 的 `n_train`／`n_test`／`n_purged` 會變成 (event,TF) 列數，卻仍被前端與 wiring 測試當事件數使用，與 §C「不得混用」衝突且 Task 9.3 未指派修改。

**碼證**: `pipeline.py:760-762` 對 `plan.assignments`／`purged` 列數求和；`EventTablesPanel.tsx:361` 無單位顯示三數；`test_splitunify_wiring.py:113` 斷言三數之和＝`len(records)`。VERIFY 探針：`PIPELINE_MIXUP {'n_train': 2, 'n_test': 2, 'n_events': 2, 'records': 2, 'wiring_eq': False, 'row_sum': 4}`。RECHECK: 讀三處行號＋重跑同形探針。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a;tests/momentum/event_samples/test_splitunify_wiring.py#3d6a16a4d617

[BLOCKING] 信心度=High。實作者若只改 15 處表，摘要與 UI 會把事件數膨脹為 pair 列數且無標註。**修法**：觸及面增「第四層—記帳／報告」列 `pipeline.py:760-762`、`EventTablesPanel.tsx`、`test_splitunify_wiring.py:113`；Task 9.2 讓 pipeline summary **同時**寫事件級計數與 `n_event_tf_rows`（或 `n_train_rows` 後綴），禁止再用裸 `n_train` 表示列數；前端加單位；wiring 斷言改對事件級或明示列級。**可行性**：summary 已是 `Dict`（`EventAnalyzeResponse.summary`），加鍵不破既有 Pydantic；`EventTablesPanel` 已有 `MetricLabel` 可標單位；wiring 測試改一行等式即可。

---

## GROK-R1-P1-02

**斷言**: Task 9.3 改法只寫「凡 `set_index("event_id")` 改 MultiIndex」，但 `feature_materialization` 的多 TF **折疊發生在** `:93` 的 `groupby("event_id")+row_vals.update`；只改 `:132` 的 `set_index` 仍會先併成一列，靜默面 #5 假修。

**碼證**: `feature_materialization.py:93-130` 按 `event_id` groupby 後 `row_vals.update`，`:132` 才 `set_index("event_id")`；D-002 觸及面 #5 與 Task 9.3 改法均只提 `set_index`。VERIFY：兩列同 eid 異 TF → `GROUPBY_FOLD_NROWS 1`；對 raw 直接 `set_index` → `n=2 unique?=False`（證明折疊在 groupby，不在 set_index）。RECHECK: 讀 `:93-132`＋重跑 groupby 探針。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2

[BLOCKING] 信心度=High。Agent 依字面改 `set_index` 並加「索引唯一」斷言時，groupby 已輸出一列／事件 ⇒ 斷言仍綠、多 TF 特徵列仍消失。**修法**：Task 9.3／觸及面 #5 明示必須拆掉（或改寫）`groupby("event_id")` 折疊，改為每 `(event_id, timeframe)` 一列後再 MultiIndex；§V 對 #5 的「改壞就要變紅」測試須斷言 **列數＝pair 數**（不只 index 唯一）。**可行性**：函式已逐 `per_tf` record 取列（`:96-126`），去掉 groupby 外殼改 append `(eid, tf)` 即可；記帳守恆 `:137-139` 改比對 `len(per_tf)` 而非 `nunique(event_id)`。

---

## GROK-R1-P1-03

**斷言**: D-002 只規定「同事件不同 TF **同簇**」，**未**規定同事件多 TF 必須落在**同一 split 側**（或混側整事件 purge／fail-closed）；9B 放行 pair assignments 後，1h=train／4h=test 會讓仍偏事件級的消費者靜默組成非法 OOS 樣本。

**碼證**: D-002 Task 9.3 僅有同簇句（約 L119）；全文無「混側／同側／同一 split_label」約束（本輪 `SPEC_HAS_MIXED_SIDE_RULE False`）。上游偵察 `CODEX-R1-P1-02` 已指出混側不可證，synth 採納時偏重 schema／列數誠實性，**混側契約未寫入 D-002**。探針：同事件異 TF 異 `split_label` 仍同 `time_cluster_id`——同簇**不能**代替同側。RECHECK: `grep -n '混側\|同側\|split_label' docs/SPLITUNIFY_SPEC.D-002.md`；構造 1h train／4h test fixture 餵 baseline／`test_ids` 交集。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;handoffs/reconcile/20260911-splitunify-b9-consult-r1/synth.md#2ac4e7432169;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[BLOCKING] 信心度=High。缺此契約時，實作者可「合法」產出混側 pair 列；`baseline`／`tables` 的 `test_ids = assignments…event_id` 會把該事件當 test，train 側 TF 特徵被吃掉或交錯——不 raise。**修法**：在 D-002-C1／Task 9.2 或 9.3 加硬規則——同一 `event_id` 之所有生效 TF **必須**同一 `split_label`；若 cutoff 落在不同段 ⇒ 整事件 purge（具名 reason）或 fail-closed；並加 §V 斷言＋`M-SU-D2-xx`（混側未擋應紅）。**可行性**：投影迴圈已逐事件看 cutoff∈train_ms／test_ms（`split_projection.py` 成員判定）；改為「同事件多 TF 先收集 label 再一致化／purge」不需新架構；b8 已有 purge reason 字串先例。

---

## GROK-R1-P2-01

**斷言**: `M-SU-D2-01`～`06` 不足以覆蓋 9A／9B 靜默失效面與本輪新列之記帳／groupby／混側缺口；`02` 單條 set_index mutation 無法代替靜默面 5／7／8／9／11／12 的逐處值斷言。

**碼證**: D-002 §V L131 僅列 01–06；靜默面清單在 §C／觸及面；wiring `dict(zip)`（`:103-104`）與 pipeline 記帳無對應 M-SU-D2；無混側、無 groupby 折疊 mutation。RECHECK: 對照 §V 與觸及面靜默項逐條打勾。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;tests/momentum/event_samples/test_splitunify_wiring.py#3d6a16a4d617

[MAJOR] 信心度=High。照表做完 6 條 mutation 自證仍可能假綠。**修法**：至少增——`07` pipeline 用列數填事件級 `n_train` 應紅；`08` wiring `dict(zip(event_id))` 應紅；`09` materialize 保留 groupby 折疊應紅（列數≠pair）；`10` 混側未 purge 應紅；`11` #13 survivor 仍只按 `event_id` 雜湊應紅；並要求 01–06 各**指名**應紅測試。靜默面每項保留 Task 9.3 的值斷言（不得只「不報錯」）。

---

## GROK-R1-P2-02

**斷言**: §G 並陳「`g5` 不受影響」與「順道把 fixture 改為兩標的交錯（`M-SU-D1-23`）」時，未區分「複合鍵不改指紋 payload」與「交錯 fixture 會移動 g5 positions／ms／sha」；Agent 可能誤刪單標的錨或拒絕對 g5 做必要重凍。

**碼證**: D-002 §G L95–97；`freeze_splitunify_golden.py` 現為單標的、`row_index_local` 逐值等於 `row_index`；`build_row_time_fingerprint` 含 `positions`＋`feature_ts_ms`——交錯兩標的必改 positions／ms。本輪 `G5_SAME True` 且源碼無 `timeframe` ⇒ 複合鍵公式面成立。RECHECK: 讀 §G 兩句＋`freeze_splitunify_golden.py` 單標的假設註解。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;momentum/core/split_preview.py#95a85ec0de54;scripts/freeze_splitunify_golden.py#e331623163d2

[MAJOR] 信心度=High。**修法**：§G 改寫為兩句——①複合鍵**不**改 g5 payload 欄位／算法；②`M-SU-D1-23` 之交錯 fixture 為**新增**平行組（或具名重凍），單標的單 TF 之 g5 舊值保留為回歸錨，不得覆蓋刪除。Task 9.4 ASSERT 與此對齊。

---

## GROK-R1-P2-03

**斷言**: Task 9.1 只改 `split_projection`／`EventSplitPlan.summary`，未規定 API／前端如何露出 `discarded_per_tf_rows_by_timeframe`；9A「消除靜默丟棄的誠實性缺陷」對事件批 UI 使用者可能達不成。

**碼證**: D-002 L103-107 檔案清單無 `api/`／`frontend/`；`rg discarded_per_tf` 全 repo 僅 D-002；`EventTablesPanel` 現只渲 `n_train`／`n_test`／`n_purged`。pipeline `:759` 雖會把 plan.summary 鍵拷進 response，但無型別／UI 契約。RECHECK: `rg discarded_per_tf`；讀 Task 9.1。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7b4ef94eed32;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a

[MAJOR] 信心度=Medium（若產品接受「僅 API JSON 即算揭露」可降 NON-BLOCKING；SPEC 自述目標含消除誠實性缺陷）。**修法**：Task 9.1 增 API 透傳＋`types.ts`＋面板一行「未選 TF 丟棄：{…}」；驗收加 API／元件測試。**可行性**：`tests/api/test_splitunify_disclosure.py` 已有揭露測試骨架可平行加 case。

---

## 11 類快掃（§1）

1. 矛盾／互斥：§C 禁混用 vs pipeline 未改（P1-01）；同簇 vs 缺同側（P1-03）；g5 不受影響 vs 交錯 fixture（P2-02）
2. 漏項：記帳鏈、groupby 折疊、混側契約、9A UI（上列 findings）
3. 不可測：混側無 ASSERT；#5 列數無 ASSERT
4. quant 假設：混側 OOS 樣本（P1-03）
5. 過度工程：無（兩階段合理）
6. OOM：無
7. Cache：無本輪新洞
8. API／型別：9A 缺型別（P2-03）；`n_train` 語意漂移（P1-01）
9. 測試：mutation 不足（P2-01）；wiring 假綠風險
10. Agent 可執行：Task 9.3 字面誤導（P1-02）；clusters 加 `timeframe` 而 `build_time_clusters` 吃 event-level manifest——建議實作前在 SPEC 補一句「先按 assignments 展開再簇／或 post-join」，本輪不另開 P1（有同簇探針可依）
11. 短命工：9A summary 欄若 9B 改名／合併需遷移——可接受；無「做了又刪」白工

## 主動攻擊面（停輪③；成功開洞見上）

1. 15 處完整性（set_index＋api.services dict＋frontend＋golden＋groupby）→ P1-01／P1-02  
2. 9A 回退與揭露路徑 → 技術可回退；UI 缺口 P2-03  
3. cluster 反例（同決策／分叉決策／混側）→ 無誠實分簇反例；轉出混側 P1-03  
4. 列數當事件數探針 → P1-01  
5. g5 公式 vs fixture → P2-02  
6. mutation 對靜默面逐項對表 → P2-01  
7. `api/services/` 未逐檔精讀——與 SPEC §N 一致；記帳鏈已用碼證否證「15=全部」

若本輪 finding 不修就進 Task 9.x：①pipeline／UI 事件數膨脹假帳；②materialize 假修仍單列；③混側 pair 污染 OOS。

---

## 複驗（本人）

| 命令／探針 | 結果 |
|---|---|
| discard 計數（4 列→選 1h） | `DISCARD_BY_TF {'4h': 2}` selected 2 |
| pipeline 列數探針 | `row_sum 4` / `records 2` / `wiring_eq False` |
| `build_time_clusters` pair 同決策 | `E1_CLUSTER_IDS [472222, 472222]` |
| groupby 折疊 | `GROUPBY_FOLD_NROWS 1` |
| g5 | `G5_SAME True`；源碼無 `timeframe` |
| `rg discarded_per_tf` | 僅 D-002 |
| D-002 混側詞 | `SPEC_HAS_MIXED_SIDE_RULE False` |

ASSUMPTIONS_VERIFIED: 靜默丟棄計數形；15 處不完整（記帳鏈＋groupby）；同簇反例失敗；g5 payload 無 TF；mutation／混側／9A UI 缺口有碼證  
TESTS_RUN: `/tmp/grok-splitunify-b9-review-r1/probe_*.txt` 探針（review 未改碼）；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r1-grok.md --family grok`  
FAILURES_SEEN: `build_event_keys` 最小 fixture 缺 `event_level.timeframe` → KeyError（改用手動 discard 計數；不影響結論）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r1-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R1-P1-01,GROK-R1-P1-02,GROK-R1-P1-03
CLOSED:

STATUS: DONE
