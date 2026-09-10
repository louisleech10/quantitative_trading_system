# SPLITUNIFY consult R1 — grok

TASK_ID: 20260910-SPLITUNIFY-X-CONSULT-R1  
family: grok  
findings-round: R1  
標的：Claude 提案「以時間切分為準，事件切分導出」  
範本：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0＋canonical 四欄（brief 指定全文照做）；finding 形狀見 `templates/COMMITTEE_FINDING_TEMPLATE.md`  
SCOPE: 設計 consult／共識決；**禁改碼**；未跑 `pytest tests/governance`

---

## Verdict

**Verdict: 採「時間切分為準、事件切分為三態投影」——但否決 brief 字面的「只對 `test_timestamps` 做交集」；投影必須用 train∪test 兩 plan 做 train／purged／test 三態，多 symbol 批 fail-closed 直至 `split_per_symbol` 逐標投影，GAP-3 走 D 延伸（UX=`D-002`；EVENT SPEC 開/寫 amendments），票＝大、建議 3 批。**

最小落地步驟（可執行）：
1. 新增純函式（建議名）`project_event_split_from_holdout(manifest, train_plan, test_plan, feature_index) -> EventSplitPlan`：decision 落在 `test_plan` 時間戳 ⇒ `test`；落在 `train_plan` ⇒ `train`；其餘（含 purge／embargo 帶）⇒ `purged`（reason 具名，如 `decision_in_isolation_band`）。**禁止** `in_test else train` 二態。
2. `clusters`／`cluster_weight` 仍由現有 time-cluster 邏輯產出（與邊界正交）；`summary.degraded`／`insufficient_events_in_test` 語意保留。
3. `pipeline.run`：改呼叫投影（或 `split_events` 內改為「先取/建 SplitPlan 再投影」），不再用事件計數 `test_fraction` 自切邊界。
4. 多 symbol：`n_symbols>1` 且無 per-symbol `SplitPlan` 對 ⇒ **raise**（fail-closed）；支援路徑＝`split_per_symbol` 後逐 symbol 投影再 concat。
5. 規格：`docs/GAP3_EVENT_UX_SPEC.D-002.md`（覆寫切分權威）＋ `docs/GAP3_EVENT_SPEC` 之 B1.3 修訂（該檔慣例走 amendments／延伸，**不解凍原檔**）。
6. 測試：成員集合 golden（改前≠改後須明示接受）＋ purge 帶事件不得進 train 的 mutation＋多 symbol fail-closed。

---

## §0 挑戰前提（brief 逐條）

| 宣稱 | 判定 | 本家複驗 |
|---|---|---|
| 消費者 7 生產／6 測試 | **fact-verified** | `grep -rln EventSplitPlan momentum api tests` → 生產 7（`event_split/baseline/ic_feed/pattern_bridge/types/tables/pipeline`）＋測試 6 |
| EVTLABEL 已收、Task 3.4 吃 `test_timestamps` 交集 | **fact-verified** | `ic_filter_orchestrator.py:1298` 寫入；`:3830-3835` selection 交集；purge=`max(H,W)` 於 `:1254-1255` |
| assumed：時間切分隔離**嚴格強於**事件緩衝 | **assumed → 半推翻** | 兩者切軸不同（事件計數尾段 vs K 線列尾段＋bars purge）；合成探針 `event_frac n_test=12` vs `time_proj n_test=18`。EVTLABEL 後 IC 路徑較齊，但「嚴格支配」不成立。採時間準繩的理由＝**單一權威＋與 Task 3.4 已事實權威對齊**，不是隔離強度全序 |
| assumed：統一後多 symbol 數值不變 | **assumed → 已否證** | `/private/tmp/probe_split.py`：合併 80 列、全域 test=12、per-symbol test=8、只在全域=4 → `DISPROVED` rc=1 |
| `baseline` OOS 是否依賴 per-symbol 語意（作者未查） | **讀碼：語意依賴 assignments 成員，非型別** | `baseline.py:105-108` 只取 `split_label=="test"`；成員一變 AUC／PR-AUC／FDR 全變 |
| GAP-3 UAT 是否直接驗事件切分邊界（作者未查） | **fact-verified：清單無直接邊界項** | `docs/GAP3_UAT_CHECKLIST.md` 無 `EventSplit`／切分邊界步驟；間接經 A1 `tests/momentum/event_samples/`（含 split 單測） |

### 本輪實跑

| 命令 | 結果 |
|---|---|
| `grep -rln EventSplitPlan momentum api tests` | 13 檔（7+6） |
| `venv/bin/python /private/tmp/probe_split.py` | DISPROVED；全域 12 vs per-symbol 8；rc=1 |
| 合成事件密度探針（event-fraction vs bar+purge） | n_test 12 vs 18；only_time=[82..87] |
| 讀碼 `event_split.py`／`baseline.py`／`pattern_bridge.py`／`tables.py`／`ic_filter_orchestrator.py`／`contracts.py`／FROZEN 程序 | 如下 findings／必答 |

---

## 必答 1a–6（立場，非選項清單）

### 1a. 統一方向
**以時間切分為準（採提案方向），事件切分改為由其投影。**  
否決「以事件為準」（與 Task 3.4／IC 主線已對立，UAT 兩數字問題無解）。  
否決「另立第三方 canonical」（多一層真相＝B3 教訓重演）。  
**附加硬條件**：投影＝三態（train／purged／test），不是只交 `test_timestamps`。

### 1b. 最小可行落地
見 Verdict 步驟 1–6。  
**改**：`event_split.py`（或旁路新純函式＋pipeline 改呼叫）、`pipeline.py`、必要時 orchestrator／service 把 `train_plan`+`test_plan` 下傳；測試 6 檔＋新投影單測。  
**只讀／保留型別**：`types.EventSplitPlan` 容器形狀（assignments／purged／clusters／summary）暫留，避免一次打穿 B2／B4 簽名；`baseline`／`pattern_bridge`／`tables`／`ic_feed` **簽名可暫不變**，只改 upstream 產出之成員。  
**不動**：`SplitPlan` 契約本體（除非批 2 做 per-symbol 支援時擴充呼叫面）。

### 2a. 多 symbol 統一後是否等價？
**否。** 探針已否證。  
**該擋（fail-closed）**，直到批內實作 per-symbol 投影。不得用全域 scalar 冒充（對齊 `CODEX-R1-P1-02` per-scope 禁令）。

### 2b. 若要支援，`SplitPlan` 是否需 per-symbol 化？
**要支援就必須走既有 `split_per_symbol`（`contracts.py:625`）**，每個 symbol 一對 train/test `SplitPlan`（已有 `symbol` 欄），再逐標投影。  
不必先發明新 dataclass；缺 per-symbol plan 就 raise。單 symbol路徑（現行 `analyze` 取 `next(iter(allowed_symbols))`）可先落地。

### 3a. `baseline`／`pattern_bridge` 對 `EventSplitPlan`：語意 vs 型別
| 依賴 | 類別 | 碼證 |
|---|---|---|
| `assignments.split_label` → test/train 成員 | **語意**（不可只換型別） | `baseline.py:105-108`；`pattern_bridge.py:114-127`；`tables.py:305-306` |
| `clusters`／`cluster_weight` → CI／權重 | **語意** | `tables.py:208+`；`pattern_bridge` → `binary_discrimination_table` |
| `summary.degraded`／`n_symbols`／`loso_status` → AR-3 `common` | **語意** | `tables.py:130-150` `_common_constraint_block` |
| 參數型別名 `EventSplitPlan` | **型別**（可留容器） | 各函式簽名 |
| `ic_feed` 之 `split_summary` 摘錄 | **弱語意**（揭露欄） | `ic_feed.py:116`；IC 分析主鏈註解已說不經本模組 |

### 3b. 誰會因統一而**改數值**（非只改型別）？
**會改（確定方向，幅度依批而異）**：
1. `baseline.single_feature_binary_baseline` — OOS AUC／PR-AUC／p／q（test 成員變）
2. `pattern_bridge.extract_event_patterns` — 擬合集＋test 辨別表＋rules 評分
3. `tables.binary_discrimination_table`／依賴其之報告
4. `tables.event_forward_return_table` 若分 split 揭露（clusters 仍在；assignments 變則分桶變）
5. 任何讀 `insufficient_events_in_test`／loud 旗標的路徑（門檻觸發點變）

**通常不改數值（若只換投影、cluster 公式不變）**：`clusters` 權重和＝1 之約束本身；IC 主線在 Task 3.4 後已用 `test_timestamps` 的 selection 計數（與事件自切脫鉤的那條）。

合成依據：同密度偏斜下 event-fraction test=12 vs time+purge 投影 test=18。

### 4a. GAP-3 FROZEN — 延伸還是解凍？
**走延伸／amendments，不解凍原檔。**  
`GAP3_EVENT_UX_SPEC.md` 為 whole-body FROZEN＋已有 `D-001`（程序 §2.1 D 延伸）。本改是「切分權威改掛」——不推翻 PIT／label 設計本體，屬 D 延伸而非 R 重開（除非委員把「B1.3 per-symbol 事件自切」判為被證偽的核心設計而爭 R；本家預設 D，爭議則依程序預設 R——見 finding）。

### 4b. 延伸編號與範圍
- **`docs/GAP3_EVENT_UX_SPEC.D-002.md`**：宣告「事件分析路徑之 split 邊界權威＝holdout `SplitPlan`；`EventSplitPlan`＝投影；三態算法；多 symbol fail-closed／`split_per_symbol`」。
- **`docs/GAP3_EVENT_SPEC` B1.3**：同步改「不再以事件計數 `test_fraction` 自切」；該檔頭寫修訂走 `GAP3_EVENT_SPEC_AMENDMENTS.md`（檔尚不存在 → 本票建立）或同等 D 延伸，**不就地改 FROZEN 正文**。
- TODO：對應 `GAP3_EVENT_TODO` 延伸／新 SPLITUNIFY SPEC+TODO（產品票本體）。

### 5a. 「兩套保留但標主從」是否優於統一？
**否，對本票目標更差。**  
代價：UAT 仍見兩驗證段數字（主從標籤降噪≠消歧）；下游（survivor／pattern_bridge）仍可能綁從屬那套；文件與測試永遠雙軌。唯一可留的「兩套」是**過渡期讀取相容**（舊 receipt 仍能 parse），不是並行計算兩邊界。

### 5b. 最終建議（一句話）
**時間切分為唯一邊界權威；`EventSplitPlan` 降為三態投影＋保留 cluster／AR-3 容器；多 symbol 先 fail-closed；GAP-3 用 D-002／amendments；接受 baseline／bridge 數值重基線。**

### 6. 票多大？幾批？
**大**（命中 a 數值品質、b 跨 `event_samples`＋orchestrator／contracts 呼叫面、d ML／OOS 正確性）。  
**建議 3 批**：  
- B0：SPEC+D-002+EVENT amendments+TODO＋投影純函式＋單 symbol 單測／mutation（purge 帶不得進 train）  
- B1：pipeline／呼叫鏈改接＋多 symbol fail-closed＋既有 event_samples 測試改寫  
- B2：per-symbol 支援（若本票要一次做完；否則殘留登記觸發條件）＋golden／UAT 基線重錄  

若裁掉 B2 per-symbol 支援、只做單 symbol＋fail-closed → 仍算**大**但可縮為 2 批。

---

## GROK-R1-P1-01

**斷言**: brief 提案若依字面「只以 `SplitPlan.test_timestamps` 交集出驗證段事件、其餘當 train」實作，會把決策時刻落在 purge／embargo 隔離帶的事件標成 train，形成 look-ahead／標籤重疊洩漏。

**碼證**: `momentum/core/split_preview.py` `holdout_test_row_index`：`test_rows = arange(split_point + purge_gap + embargo, n_rows)`，train 為 `arange(0, split_point)`——中間帶不在任一側。`ic_filter_orchestrator.py:1298` 之 `test_timestamps` **只**含 test 側。`event_split.py:114-117` 現行三態含 purge（`interval_crosses_split_boundary`）。合成：`split_point=70,purge=12` ⇒ 帶 70–81；naive `not in test ⇒ train` 會吞下該帶。RECHECK：對投影函式 mutation——強制把隔離帶事件標 train ⇒ 新測試必紅。

**來源摘要**: handoffs/20260910-SPLITUNIFY-CONSULT-BRIEF.md#d45d71164f56; momentum/core/split_preview.py#6b6a1d95c5cc; momentum/Analysis/event_samples/event_split.py#fde5a520c319; momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7

[MAJOR] 信心度=High。會怎麼失敗：OOS 訓練集混入答案窗與測試段重疊之事件 ⇒ AUC／規則偏樂觀。修法：SPEC 寫死三態投影（Verdict 步驟 1）；禁止二態捷徑；mutation 守門。

---

## GROK-R1-P1-02

**斷言**: 「時間切分隔離語意嚴格強於事件切分緩衝」在 brief 被當理由，但是未驗證假設；兩者切軸不同，不存在全情境支配關係——採時間準繩應改寫為「單一權威＋與 Task 3.4 對齊」，而非隔離強度全序。

**碼證**: 事件路徑 `event_split.py:106-117` 以**每 symbol 事件計數** `floor(n*(1-test_fraction))` 定 `test_start`，再以 `label_end_ms` vs `test_start-embargo` 做 interval purge。時間路徑 `_build_holdout_split_plan`（`:561-631`）以**K 線列數** `oos_test_size`＋bars `purge/embargo` 切。合成探針：同 40 事件偏斜密度 ⇒ event-fraction test=12、time+purge 投影 test=18（only_time=82..87）。作者自承「沒跑、只讀欄位」。RECHECK：重跑本檔「本輪實跑」表兩探針。

**來源摘要**: handoffs/20260910-SPLITUNIFY-CONSULT-BRIEF.md#d45d71164f56; momentum/Analysis/event_samples/event_split.py#fde5a520c319; momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7

[MAJOR] 信心度=High。會怎麼失敗：SPEC §A 把假設寫成事實 → 實作者誤刪事件側仍較嚴的 interval 檢查、或爭論方向時用錯判準。修法：§A 改寫採納理由；投影仍須覆蓋隔離帶（見 P1-01）。

---

## GROK-R1-P1-03

**斷言**: 多 symbol 批上，「全域時間切分 ∩ 事件」與現行 per-symbol `split_events` **成員不等價**；若統一時用單一 scalar `SplitPlan` 投影全批，違反 per-scope 語意且改變驗證段。

**碼證**: `event_split.py:78` `groupby("symbol")` 各自切。`SplitPlan` 雖有 `symbol` 欄（`contracts.py:390`），但 `analyze` 主路徑 `:1248` `symbol = next(iter(allowed_symbols))` 建**單** plan。`venv/bin/python /private/tmp/probe_split.py` → 合併 80 列、全域 test=12、per-symbol test=8、只在全域=4，stdout `DISPROVED` rc=1。RECHECK：重跑該探針；或對兩 symbol 交錯時鐘事件批比較 assignments。

**來源摘要**: /private/tmp/probe_split.py#ba187c89638d; momentum/Analysis/event_samples/event_split.py#fde5a520c319; momentum/core/contracts.py#642aecf26b32; momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7

[MAJOR] 信心度=High。會怎麼失敗：跨標的批 OOS 集合被另一標的的時間密度拖移；formal pooled 推論基線漂移。修法：`n_symbols>1` 無 per-symbol plans ⇒ fail-closed；支援＝`split_per_symbol`（`:625`）後逐標投影。

---

## GROK-R1-P2-01

**斷言**: 統一後 `baseline`／`pattern_bridge`／`tables` 的 OOS 數值**會變**（不是型別重命名）；SPEC 必須把「接受重基線」寫成顯式驗收，禁止以「行為不變」或舊 golden 擋投影。

**碼證**: `baseline.py:105-108` test_ids←assignments；`pattern_bridge.py:125-127,155-188` train 擬合／test 評分；`tables.py:305-306` 同。成員探針 12 vs 18 ⇒ 同一特徵向量進 OOS 計算的列集合不同。RECHECK：同一 fixture 上舊 `split_events` vs 新投影之 `test` event_id 集合 diff 非空＋AUC 差值記錄進 receipt。

**來源摘要**: momentum/Analysis/event_samples/baseline.py#38c7ec473653; momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2; momentum/Analysis/event_samples/tables.py#b80c15cf206d

[MINOR] 信心度=High。會怎麼失敗：實作者為保舊 golden 而加相容分支 ⇒ 兩套邊界殘留。修法：TODO 列「故意破舊 golden／重錄」；UAT 數字以時間投影為唯一公佈值。

---

## GROK-R1-P2-02

**斷言**: `EventSplitPlan.clusters` 與 `summary`（degraded／loso／stats_modes）是 AR-3 語意依賴，不是可刪的型別附件；「導出」若只產出 assignments 會讓 `formal_pooled_inference_allowed` 與 cluster CI 假綠或假紅。

**碼證**: `_common_constraint_block`（`tables.py:130-150`）讀 `summary.degraded`／`loso_status`／`n_symbols`；`event_forward_return_table` 拒空 `clusters` 冒充未切分（`:194-206`）；`split_events` 建 `time_cluster_id`＋`cluster_weight=1/n`（`event_split.py:134-140`）。RECHECK：投影產出缺 clusters 或 summary.degraded ⇒ 既有 AR-3 斷言紅。

**來源摘要**: momentum/Analysis/event_samples/tables.py#b80c15cf206d; momentum/Analysis/event_samples/event_split.py#fde5a520c319; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MINOR] 信心度=High。會怎麼失敗：CI 全標 unavailable 或反向以空 clusters 算出看似有效 CI。修法：投影函式契約＝完整 `EventSplitPlan` 四欄；cluster 邏輯可抽共用，不得省略。

---

## GROK-R1-P2-03

**斷言**: 「兩套都保留但標主從」不能滿足本票 UAT 目標（同一報告兩個驗證段數字），應在 SPEC §N 或 §C 明文否決為反模式。

**碼證**: brief「為什麼非統一不可」＋`白話說明/接下來要做的票.md` SPLITUNIFY 段（31 vs 33）。主從標籤不刪第二條算術 ⇒ 數字仍可分歧。RECHECK：SPEC 合併稿 grep 不得出現並行雙邊界計算路徑。

**來源摘要**: handoffs/20260910-SPLITUNIFY-CONSULT-BRIEF.md#d45d71164f56; 白話說明/接下來要做的票.md#2b5d19cafa75

[MINOR] 信心度=High。修法：§C 禁並行雙切；過渡期只允許舊 artifact 讀取相容。

---

## GROK-R1-P2-04

**斷言**: GAP-3 原檔 FROZEN；本票應出 `GAP3_EVENT_UX_SPEC.D-002`（及 EVENT SPEC amendments），**不解凍／不 R 重開**作為預設路徑——除非委員會把「B1.3 事件自切」裁定為設計被證偽（則程序預設 R）。

**碼證**: `GAP3_EVENT_UX_SPEC.md` 檔頭 `狀態：FROZEN`＋`延伸: D-001 ...`；`FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1 D vs R；`GAP3_EVENT_SPEC.md` 頭註修訂走 amendments、不就地改。`ls docs/GAP3_EVENT_UX_SPEC.D-*.md` ⇒ 僅 D-001 ⇒ 下一號 D-002。RECHECK：合併稿路徑存在且 `template_check.sh dext` 可跑。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#f2da7e1041d5; docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md#176c58e0c914; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MINOR] 信心度=High。會怎麼失敗：就地改 FROZEN ⇒ 戳記／延伸索引機檢紅；或誤開 R 拖垮無關延伸。修法：D-002＋amendments；爭議面再升 R。

---

## 被當成事實的未驗證假設（§0）

1. 「時間隔離嚴格強於事件緩衝」→ 本家標 **assumed／半推翻**（P1-02）。  
2. 「統一後多 symbol 數值不變」→ **已否證**（P1-03）。  
3. 提案字面交集算法已足夠安全 → **不成立**（P1-01）。  
其餘消費者檔數／EVTLABEL Task 3.4／FROZEN 狀態 → fact-verified。

---

ASSUMPTIONS_VERIFIED: 消費者 7+6；Task 3.4 `test_timestamps`；FROZEN+D-001；UAT checklist 無直接切分邊界項；多 symbol 全域≠per-symbol（探針）；event-fraction≠bar+purge 成員；naive 二態會吞隔離帶  
TESTS_RUN: `venv/bin/python /private/tmp/probe_split.py` → DISPROVED rc=1（全域12 vs per-symbol8）；合成密度探針 n_test 12 vs 18；`grep -rln EventSplitPlan` 13 檔；未跑 pytest／governance  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（只寫本產出；禁改碼已遵守）  
NUMERIC_OR_SCHEMA_IMPACT: none（本輪未改碼）；落地後 baseline／bridge／tables OOS 數值必變（P2-01）  
OUTPUT_PATH: handoffs/20260910-splitunify-x-consult-r1-grok.md  
STATUS: DONE
