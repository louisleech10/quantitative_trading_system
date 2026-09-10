# SPLITUNIFY SPEC/TODO adversarial review R1（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R1  
family: grok  
findings-round: R1  
標的：`docs/SPLITUNIFY_SPEC.md`＋`docs/SPLITUNIFY_TODO.md`（commit `08391e4c`）  
SCOPE: review-only；禁改碼／禁改 `docs/SPLITUNIFY_*.md`  
**範本**：照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0–§3 全文；findings 用 canonical 四欄（`templates/COMMITTEE_FINDING_TEMPLATE.md`）。  
SPEC-DIGEST: `docs/SPLITUNIFY_SPEC.md#4e016f8e1d54`  
TODO-DIGEST: `docs/SPLITUNIFY_TODO.md#36b5c6ae5af2`  
ORCH-DIGEST: `momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7`  
CONTRACTS-DIGEST: `momentum/core/contracts.py#642aecf26b32`  
SPLIT-PREVIEW-DIGEST: `momentum/core/split_preview.py#6b6a1d95c5cc`  
EVENT-SPLIT-DIGEST: `momentum/Analysis/event_samples/event_split.py#fde5a520c319`  
PIPELINE-DIGEST: `momentum/Analysis/event_samples/pipeline.py#f78eae8df0f6`  
PATTERN-DIGEST: `momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2`  
BASELINE-DIGEST: `momentum/Analysis/event_samples/baseline.py#38c7ec473653`  
TABLES-DIGEST: `momentum/Analysis/event_samples/tables.py#b80c15cf206d`  
TYPES-DIGEST: `momentum/Analysis/event_samples/types.py#8ba12e1b5204`  
CONSULT-DIGEST: `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`（commit `9f75e4a7`）

### §0 前提宣告（本輪覆核）

- fact-verified: `EventSplitPlan` 生產端恰 7 檔 → `grep -rln EventSplitPlan momentum api`（api 0；七檔為 baseline／event_split／ic_feed／pattern_bridge／pipeline／tables／types）。
- fact-verified: `SplitPlan` 有 `symbol`、無完整 timestamp 陣列 → `contracts.py:378-390`（僅 `row_index`＋首尾 `time_bounds`）。
- fact-verified: 事件 holdout 為單幣 positional → `ic_filter_orchestrator.py:561-603`／`:1256`；`test_timestamps` 由 `features_df.index[test_plan.row_index]` 物化於 `:1298`。
- fact-verified: `split_per_symbol` 只在 cross-sectional 分支 → `:903`；事件 `analyze` 不走它。
- fact-verified: 多 symbol 全域≠per-symbol → receipt `handoffs/run_receipts/20260910T150504Z-splitunify-multisymbol.json` 存在（12 vs 8）。
- fact-verified: 事件路徑仍呼叫舊 producer → `pipeline.py:691` `split_events(...)`。
- fact-verified: binary 鍵與特徵索引單位不同 → `split_preview.py:63-79`（feature_cutoff_ms vs DatetimeIndex，不換算計數恆 0）。
- fact-verified: `pattern_bridge` 不讀 clusters → `:114-127` 只讀 `assignments`；`tables.py:351+` 讀 clusters。
- assumed: `_build_holdout_split_plan` 的 positional `row_index` 可在投影內安全還原成時間戳且與事件時鐘對齊唯一（brief assumed#1）。
- assumed: `baseline.py`／`pattern_bridge.py` 接線後數值不變（brief assumed#2）。
- assumed: TODO B3「failed 數 <= 20」足以擋住本票迴歸（brief assumed#3）。
- assumed: SPEC 稱時間切分隔離「較弱／較強」於事件緩衝 bars 已是可當 fact 的 containment（C-1 理由句）。

---

## Verdict：需修補後派工

有 **2 個 P0**（投影簽名缺 `feature_index`／時鐘契約；B3 驗收寫聚合 `failed<=20`）＋數個 P1（三態邊界未定義、clusters 輸入不足、G-3 把已知差集當長期 golden、消費者處置不清）。D1–D5 方向本輪**不重開**。修補進 SPEC／TODO 後才可進 B1——因為 Task 1.1 之 D-002 會凍結投影契約，簽名錯會寫死。

---

## GROK-R1-P0-01

**斷言**: SPEC C-4／Task 2.1 簽名 `(train_plan, test_plan, event_index) -> EventSplitPlan` 不足以實作「事件時間戳 ∈ train／test 之列」：`SplitPlan.row_index` 是對某一 `features_df` 的 positional 索引，plan 本身不帶完整 timestamp 集合（只有首尾 `time_bounds`）；缺 `feature_index`（或等價已還原之 train／test timestamp Index）時無法與現行 IC 選樣（set membership）對齊，且會踩 ms↔DatetimeIndex 靜默錯位。

**碼證**: `contracts.py:378-390`（欄位集）；`ic_filter_orchestrator.py:603-620`（`index_kind="positional"`）；同檔 `:1298` 已必須用 `features_df.index[test_plan.row_index]` 物化 `test_timestamps`；`split_preview.py:63-79` 明文：binary 鍵是 epoch ms、特徵索引常為 DatetimeIndex，不換算則計數恆 0 且不 raise。RECHECK：只傳兩個 `SplitPlan`＋`event_index`、不傳 universe index ⇒ 無法從 `row_index` 還原集合；若改用 `time_bounds` 閉區間，與 `:1298`／`count_binary_classes_in_rows` 的**集合**語意分歧。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

[BLOCKING] 信心度=High。會怎麼失敗：Agent 用 `time_bounds` 區間或錯誤單位做 ∈ 判定 → 驗證段成員漂、與 selection_preview／OOS 事件數不一致；或接線時臨時讀 `features_df` 破壞「純函式／單一算術」。  
**確定簽名（本輪立場）**：

```text
derive_event_split_from_plans(
    train_plan: SplitPlan,
    test_plan: SplitPlan,
    event_index: pd.Index,          # 與 feature 同一時鐘；鍵語意＝feature_cutoff（非裸 decision_at）
    feature_index: pd.Index,        # 即 SplitPlan.row_index 所索引之同一 universe
) -> EventSplitPlan
```

成員判定：`ts ∈ feature_index[train_plan.row_index]` → train；`∈ feature_index[test_plan.row_index]` → test；否則 purged。`index_kind != "positional"` ⇒ fail-closed。單位：若 `feature_index` 為 DatetimeIndex，event 鍵須與 `split_preview.py:77-78` 同一換算（asi8//10**6）。等價替代：呼叫端先物化 `train_timestamps`／`test_timestamps`（與 orchestrator `:1298` 同形）再傳入——仍須在 SPEC 寫死，不得只留三參數。

---

## GROK-R1-P0-02

**斷言**: TODO Task 3.1 驗收「`tests/momentum/Analysis` failed 數 **<= 20**」是聚合期望數，無法證偽「本票未新增失敗」——本票改壞 A、既有紅 B 偶然變綠時總數仍 ≤20 會假綠；且觸碰 brief／範本紅線（禁聚合期望數）。

**碼證**: TODO Task 3.1 驗證段原文「failed 數 **<= 20**」；`templates/BRIEF_REVIEW_TEMPLATE.md` §4「禁寫聚合期望數」；brief 必答 5 與 assumed 否證觀測同型。RECHECK：人為讓一條新測試紅、同時 skip／修好一條既有紅 ⇒ 聚合計數可不變。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

[BLOCKING] 信心度=High。  
**替代判準（可執行）**：

1. B2／B3 開工前凍結 nodeid 清單（一次實跑產出，不得手抄凑 20）：
   ```bash
   venv/bin/python -m pytest -q tests/momentum/Analysis --tb=no \
     | tee handoffs/run_receipts/splitunify-analysis-baseline.stdout
   # 由 stdout 之 FAILED 行寫入：
   # tests/golden/splitunify/known_analysis_failures.txt   # 每行一個 nodeid
   ```
2. B3 驗收（非事件路徑另跑 G-2）：
   ```bash
   # A) 扣除既有紅後必須全綠
   venv/bin/python -m pytest -q tests/momentum/Analysis tests/momentum/event_samples \
     $(awk '{printf "--deselect %s ", $0}' tests/golden/splitunify/known_analysis_failures.txt)
   # 期望：rc=0（逐條 deselect，不是「failed<=N」）

   # B) 既有紅集合不得默默消失或被替換（集合相等，不是計數）
   venv/bin/python -m pytest -q --collect-only $(cat tests/golden/splitunify/known_analysis_failures.txt) >/dev/null
   venv/bin/python -m pytest -q --tb=no $(cat tests/golden/splitunify/known_analysis_failures.txt) \
     | tee /tmp/splitunify-known-red.stdout
   # 解析 FAILED nodeid 集合 == known_analysis_failures.txt 集合；多或少皆 rc=1
   ```
3. 本票**新增**測試檔（`test_splitunify_*.py`）不得出現在 known 清單，且必須 rc=0。

---

## GROK-R1-P1-01

**斷言**: SPEC／TODO Task 2.1 寫「∈ train／test 之列，皆不在 ⇒ purged」，但未定義事件時間戳**不落在任何特徵列**（兩根 bar 之間、或單位錯位）時的契約；亦未指名 `event_index` 應為 `feature_cutoff` 還是裸 `decision_at_ms`——上游**不保證** decision 落在 bar 上。

**碼證**: SPEC Task 2.1 實作要點／邊界①②③無「非 bar 對齊」條；`ic_feed.py:36` `FEATURE_CUTOFF_RULE = "max_close_ms_le_decision_at"`；`split_preview.py:63-64` 鍵＝feature_cutoff_ms；EVTALIGN 裁頭尾後特徵 universe 可變（`ic_filter_orchestrator.py:362+`／`:1209-1213`）。RECHECK：餵 `decision_at` 落在兩 bar 之間的 ms ⇒ 集合 ∈ 判定進 purged；若 Agent 用 nearest／asof 會改成員且無測試擋。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

[MAJOR] 信心度=High。修法：Task 2.1 邊界加④——`event_index` 語意＝與 IC 相同之 feature_cutoff 時鐘；**不在** `feature_index` 集合內 ⇒ **purged**（第三態），禁止 nearest／ffill；單位錯（未換算）⇒ fail-closed raise（對齊 `split_preview` 已踩過的靜默 0 命中坑）。不是「上游保證不會發生」。

---

## GROK-R1-P1-02

**斷言**: Task 2.1 要求產出完整 `EventSplitPlan`（含 `clusters`／`summary`），但公開簽名只有 plans＋`event_index`，不足以重算 `event_split.py` 的 time-cluster（需要 `decision_at_ms`、`timeframe`／`bucket_ms` 與整表事件列）。

**碼證**: SPEC Task 2.1「`clusters`…沿用既有 `event_split.py` 之連通分量，只換輸入」；實際 clusters 建於 `event_split.py:126-140`（讀 table 之 `decision_at_ms`／`timeframe`）；`tables.py:351-359` 消費 `clusters` 做 macro／micro／CI。RECHECK：只給 `event_index`（無 symbol／tf／decision 欄）⇒ 無法得到與現行相同之 `time_cluster_id`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

[MAJOR] 信心度=High。修法：簽名再加 `manifest: EventManifest`（或 `events: pd.DataFrame` 最小欄位集）；clusters／summary.degraded 由同一 helper 重算，**只把 split 邊界來源換成投影**；並在 Task 3.1 寫明 `tables.py` 路徑不得因 clusters 空殼而假 `ci.status=ok`（既有 guard `:194-205` 須仍紅）。

---

## GROK-R1-P1-03

**斷言**: G-3「凍結新舊兩套 producer 的差集」若成為長期 CI golden（可比對通過），是把 C-2 已宣告的**已知不等價**合法化成可 `--write` 吸收的基線，無法區分「差集與遷移報告一致」與「投影又漂了一次」。

**碼證**: SPEC §G G-3；TODO Task 2.2 要點 2「**預期有差**…本 golden 記錄的是『差在哪』」；C-2 已證全域≠per-symbol。RECHECK：接線後成員再漂但差集檔同步 `--write` ⇒ 比對模式仍 rc=0。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

[MAJOR] 信心度=High。替代：  
- **G-3a（一次性遷移報告）**：舊 `split_events` vs 新投影之差集寫入 `handoffs/run_receipts/`，**不**進預設比對綠徑。  
- **G-3b（長期 golden）**：新投影 vs **獨立 oracle**——`feature_index[train_plan.row_index]`／`[test_plan.row_index]` 集合投影出的 event_id 成員（整數／集合相等）。舊 producer 退出生產後不得再當正確性參考。

---

## GROK-R1-P1-04

**斷言**: 7 個生產端中，SPEC／TODO 對 `pattern_bridge.py` 與 `event_split.py` 的處置不夠可執行：前者是 assignments 消費者（會吃到投影後的 train／test 成員變化），後者仍是 `pipeline.py:691` 的現行邊界 producer；「保留歷史路徑、生產呼叫點＝0」只寫在 TODO 要點，未進 SPEC Task 3.1 修改檔／驗證釘選。

**碼證**: `pattern_bridge.py:114-127` 只讀 `assignments`；`baseline.py:105-107` 同；`tables.py` 另讀 `clusters`；`pipeline.py:691` `plan = split_events(...)`；TODO 3.1 要點 2「呼叫點數＝0」、SPEC Task 3.1 修改檔未列 `event_split.py`／`pattern_bridge.py`。`grep -rln EventSplitPlan momentum api` ⇒ 仍 7 檔，無第 8 個生產消費者。RECHECK：接線後若漏改 `pipeline.py:691` ⇒ 雙邊界仍在；若只改 pipeline 但未測 pattern_bridge 數值差 ⇒ UAT 看到的 pattern OOS  silently 變。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

[MAJOR] 信心度=High。修法：SPEC Task 3.1 明示 (1) `event_split.split_events` 退出生產呼叫圖（測試釘 `pipeline`／orchestrator 對 `split_events` 呼叫次數＝0）；(2) `pattern_bridge`／`baseline`／`tables`／`ic_feed` 為**成員消費者**，型別不變但 G-1／G-3b 必須覆蓋其 test／train event_id 集合；(3) `event_split.py` 可留作 G-3a 對照或 helper 萃取，但不得再決定邊界。

---

## GROK-R1-P2-01

**斷言**: TODO §D mutation 僅 M-SU-1..3，擋不住「用 time_bounds 區間取代集合」「缺 train 變二態」「golden 自動 --write」「報告雙 n_test」「非事件路徑 bytes 變」等本票真實失敗模式。

**碼證**: TODO §D 表三列；對照 P0-01／P0-02／C-5／G-2。RECHECK：下列改壞應對應測試紅。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

[MINOR] 信心度=High。建議補：

| ID | 改壞哪一行 | 應紅 |
|---|---|---|
| M-SU-4 | 投影只用 `test_plan`（purged∪train 併一側） | `test_splitunify_derive.py -k three_state` |
| M-SU-5 | 成員改 `time_bounds` 閉區間而非 `feature_index[row_index]` 集合 | `test_splitunify_derive.py -k membership_set`（需新增） |
| M-SU-6 | 同時落兩態時靜默取 train | `test_splitunify_derive.py -k dual_membership` |
| M-SU-7 | `freeze_splitunify_golden.py` 比對失敗自動 `--write` | freeze 腳本自證（改一員仍須 rc=1） |
| M-SU-8 | `pipeline.py` 仍呼叫 `split_events` | 呼叫點釘選測試 |
| M-SU-9 | metadata 同時寫舊事件 `n_test` 與 canonical `n_test` | `test_splitunify_disclosure.py` |
| M-SU-10 | 非事件 run 報告 bytes 變 | `freeze_evtlabel_survivor_golden.py`／G-2 |

---

## 被當成事實的未驗證假設（§0）

| ID | 作者陳述 | 本輪 verdict | 依據 |
|---|---|---|---|
| ASSUME-pos→ts | positional 可經 `features_df.index` 安全還原且對齊唯一 | **不成立／簽名不足** | plan 無 feature_index；`:1298` 證明呼叫端必須持有 index；ms↔DatetimeIndex 已有靜默坑（`split_preview.py:73-78`）；EVTALIGN 裁切改變 universe |
| ASSUME-type-only | baseline／pattern_bridge 只型別依賴、數值不變 | **數值不變＝假；讀法＝真** | 只讀 assignments（碼證）；C-2／R-2 已承認成員會變 |
| ASSUME-fail20 | `failed<=20` 擋迴歸 | **否決** | 聚合期望數；見 P0-02 |
| C-1 隔離「較強」 | 時間 purge／embargo 嚴於事件緩衝 | **仍為 assumed（本輪未重跑集合包含）** | consult 已改口「權威來自單一邊界」而非 containment；本票不應再把「較強」當 fact 寫進 D-002 |
| brief 未查：clusters 語意 | pattern_bridge 是否讀 clusters | **fact：不讀** | `pattern_bridge.py:114-127` 只 assignments |
| brief 未查：UAT B26–B34 | 是否直接驗事件切分邊界 | **fact：不直接驗雙邊界** | `白話說明/GAP-3驗收清單.md` B26–B34＝掃描瀏覽器／對齊／進度／label／隔離揭露／暖機／TF／分頁；**無**「兩套 OOS 數字合一」項 ⇒ B4 須**新增** UAT 項，不能假設 B26–B34 會抓到 |
| brief 未查：緩衝 vs purge+embargo 大小 | 投影後隔離變鬆 | **本輪未跑集合比較** | 標 `unverified-未查`；G-3b／isolation golden 應在 B2 補，不得在 D-002 宣稱「必然更嚴」 |

---

## §1 十一類（無問題標「無」）

1. **矛盾／互斥**：C-2 宣告不等價 vs G-3 長期凍結差集當綠徑（P1-03）；Task 3.1「不改簽名」vs 簽名本身不可實作（P0-01）。  
2. **漏項**：clusters／manifest 輸入（P1-02）；UAT 缺「單一驗證段」項；`pattern_bridge`／`event_split` 處置（P1-04）。  
3. **不可測驗收**：`failed<=20`（P0-02）。  
4. **可疑 quant 假設**：以「時間隔離較強」當 fact（§0）；between-bar 未定義（P1-01）。  
5. **過度工程**：無（四批＋fail-closed 與 consult D5 一致）。  
6. **OOM／並行**：無（投影 O(n log n) 宣稱可接受；未要求本輪 bench）。  
7. **Cache**：無。  
8. **API／型別**：B4 metadata 鍵尚可；須與 C-5 單一數字一致。  
9. **測試品質**：mutation 不足（P2-01）；G-3 設計弱（P1-03）。  
10. **Agent 可執行性**：簽名缺參會逼 Agent 自行發明（P0-01／P1-02）。  
11. **必要性／短命工**：Task 3.2 fail-closed 預期被 per-symbol 取代——`存活至`／`覆蓋風險` 已誠實；**保留**。B1 獨立有審查價值（見必答 6）。

---

## 必答（1–8；明確立場＋碼證）

### 1. 投影的索引語意／確定簽名

**立場：現簽名不夠。** 必須同時傳 `feature_index`（或呼叫端已物化的 train／test timestamp Index）。  
確定簽名見 **P0-01**。判準：與 `ic_filter_orchestrator.py:1298`＋`split_preview.count_binary_classes_in_rows` 同一套**集合**成員語意，禁止只靠 `time_bounds` 首尾。

### 2. 三態邊界（事件不落在特徵列）

**立場：漏了，不是上游保證不會發生。**  
上游保證的是 cutoff 規則（`ic_feed.py:36`），不是 `decision_at`∈bar。  
契約：非 `feature_index` 成員 ⇒ **purged**；禁止 nearest。見 **P1-01**。

### 3. fail-closed 是否過嚴

**立場：維持 fail-closed（本票），不在 B3 直接改走 per-symbol 投影。**  
判準：  
- `split_per_symbol` 雖在 `:903` 存在，但事件 `analyze` 仍走單幣 `_build_holdout_split_plan`（`:1248-1256` 的 `next(iter(allowed_symbols))`）。  
- §N R-1（`base_universe_hash` 多標的語意）仍 `needs-research`。  
- 若 B3 直接支援 per-symbol，等於把 R-1＋IC 單幣前提＋事件投影一次做完，審查面與回退面膨脹，且易在 hash／允許集合未定義時假支援。  
代價：多 symbol 事件批短期不可用（loud）——可接受，且與 consult D2／grok 原決議一致。省一次改寫的代價是把未解研究偷做成「支援」。

### 4. golden G-3

**立場：現設計作為長期 CI golden 無效（會合法化已知錯誤）。**  
改 G-3a 遷移報告＋G-3b 對 canonical 集合 oracle。見 **P1-03**。

### 5. B3 驗收判準

**立場：刪除 `failed<=20`；改 known-red nodeid 清單＋`--deselect` 後 rc=0＋failed-set 相等。**  
可執行命令見 **P0-02**。對齊 `templates/BRIEF_REVIEW_TEMPLATE.md` §4。

### 6. 批次切分（B1 是否獨立）

**立場：值得獨立。**  
B1＝D-002＋`split_unify.json`，不動生產碼，可單獨審「契約字面／枚舉／不解凍原檔」。  
若併入 B2：審查者同一輪要同時簽「文件是否把 D1–D5 寫對」與「三態算法／golden 是否算對」——可審性損失＝契約錯誤易被算法討論稀釋，且 B2 回退時易誤傷已核可之枚舉 SoT。consult D5 取四批保守切分，本輪不合併。

### 7. mutation 表

**不夠。** 應補 M-SU-4..10（見 **P2-01** 表）。每條已寫「改壞哪一行 → 哪個測試紅」。

### 8. 漏掉的消費者

**無第 8 個生產消費者**（`grep -rln EventSplitPlan momentum api`＝7）。  
- `pattern_bridge.py`：**assignments 消費者**（不讀 clusters）——處置應＝型別不變＋成員集合納入 G-1／G-3b。  
- `event_split.py`：**現行 producer**（`pipeline.py:691`）——處置應＝退出生產呼叫圖；helper／對照可留。  
SPEC／TODO 對這兩點寫得**不夠明確**（見 **P1-04**）。

---

## 停輪對照（本交件）

① 必答 1–8 皆有明確立場。  
② 必答 1／2／5 含檔案:行號或可執行命令。  
③ 判準已寫（看碼證：集合成員語意、聚合驗收假綠、R-1 未解不擴 scope）。  
④ 非零 finding；未使用「零 finding」停輪。

STATUS: DONE
