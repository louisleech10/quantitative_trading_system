# SPLITUNIFY SPEC 延伸 D-001 對抗審 R6（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R6  
family: grok  
findings-round: R6  
標的：`docs/SPLITUNIFY_SPEC.D-001.md`（sha256 `9bb033a39a73…`；R5 後修訂版）  
BASE：`docs/SPLITUNIFY_SPEC.md` @ `b095cc754cb9de26bbf2dd35564db329aca3c98f`（content sha256 `3e39458b00e4…`）  
上游：`handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md`（`fcb22c3019b1…`）  
SCOPE: review-only；禁改碼、禁動 tracked 檔、禁 commit／push、禁跑 `tests/governance` 全套  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄  
D001-DIGEST: `docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73`  
BASE-DIGEST: `docs/SPLITUNIFY_SPEC.md#3e39458b00e4`  
PROC-DIGEST: `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md#176c58e0c914`  
R5-SYNTH: `handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md#fcb22c3019b1`

### §0 前提宣告（本輪覆核）

fact-verified: 生產碼 `row_time_fingerprint` 命中 0 → `grep -rn row_time_fingerprint momentum/ --include='*.py'` 無輸出

fact-verified: BASE C-4 簽名仍為單一 `train_plan: SplitPlan`／`test_plan: SplitPlan`／`feature_index: pd.Index` → `git show b095cc75:docs/SPLITUNIFY_SPEC.md` L161-169

fact-verified: §G G-5① 文件稱呼為 `(position, feature_ts_ms, symbol, base_universe_hash)`；`freeze_splitunify_golden.py:152-154` 實作為 **list-of-lists** `[[int(p), int(ms[p]), SYM, "splitunify-golden"], …]`，註解仍寫 `ts_ms`

fact-verified: list-of-lists 與 list-of-dicts 之 `json.dumps(..., sort_keys=True, separators=(",",":"))` sha256 **不同** → `venv/bin/python` 實跑 list=`da52843ab235…`／dict=`3a725986cbe4…`

fact-verified: `pipeline.py:745-752` 仍以舊四位置式呼叫 `derive_event_split_from_plans(train_plan, test_plan, keys, feature_index, …)`

fact-verified: `insufficient = [s for s in per_symbol_n if n_test < …]` 仍用整批 `n_test` → `split_projection.py` 該行（與迴圈變數無關）

fact-verified: AGENTS.md Rule 12 逐字為「**動工前**…不動工」→ `Agents.md:40`；consult-r2 synth 仍缺 `## 戳記`（`reconcile_stamps_check.sh` rc=1）

fact-verified: 觸及面覆寫／依賴／不觸錨點（C-2／Task 3.2／C-4／§N／§V／§G／C-0／C-1）在 BASE 皆有逐字 heading

assumed: 「覆寫整節 C-4」＝該 heading 全文以延伸檔為準 ⇒ 否證觀測：延伸檔無 `### C-4` 替換塊、只在 D-001-C1.1 給新簽名，BASE C-4 其餘約 87 行未重述。／見 P2-02

---

## 必答 1–5

### 1. 本家 R5 findings 逐條閉合重驗

| R5 ID | 本輪 | 重驗碼證 |
|---|---|---|
| GROK-R5-P1-01 | **已閉合** | Task 8.2 檔案清單具名 `split_per_symbol`／`_build_plan_pair`／orchestrator holdout；相容 default＋derive 缺欄 fail-closed；ASSERT「生產路徑建出 plan 必帶指紋」 |
| GROK-R5-P1-02 | **已閉合** | C1.3 三角相等＋專用訊息、禁復用 `multi_symbol_projection_unsupported`；ASSERT 拆「未給 Mapping」與「給了但 symbol 不一致」兩條 |
| GROK-R5-P2-01 | **已閉合** | C2 第 2–5 點：`int(...)`、點名 `_index_as_ms`／`assert_epoch_ms_array`、排除 `_coerce_timestamp_array`、重複 position／NaT fail-closed、空 plan=`sha256("[]")` |
| GROK-R5-P2-02 | **未閉合** | 結構已改（symbol 入四元組＋三角相等分工），但 C1.2 仍寫「指紋不足以分辨」——與 C2.1 payload **含 symbol** 字面互斥；見 GROK-R6-P2-01 |
| GROK-R5-P2-03 | **已閉合** | `M-SU-D1-07`＋Task 8.1 ASSERT「以 A 之 feature_index 解釋 B 之 row_index ⇒ rc!=0」 |

### 2. 實質審查（八項）

① **類別判定 D vs R**：**D 成立**。Task 3.2 自寫「存活至…改寫為支援分支」「不得只刪 raise」（BASE ~L573-575）；本延伸落地該預告，不推翻 C-2「邊界必須 per-symbol」意圖。R5 兩家＋本輪同意。反面（升 R）＝把「一律 fail-closed」讀成無期限字面；不採——限定語「投影完成前」＋存活至已授權。

② **觸及面四欄錨點**：已宣告之覆寫／依賴／不觸 heading 在 BASE **逐字存在**（C-2 L131、Task 3.2 L559、C-4 L157、§N L675、§V L638、§G L296、C-0 L72、C-1 L116）。新增 D-001-C*／Task 8.* 正確標「原檔無」。缺口：C-4 整節標覆寫但正文只換簽名 → P2-02（非「錨點找不到」）。

③ **hash 不變式**：**正確**。跨 symbol 允許 joint hash 有碼證（`ic_split_adapter.py:189-199`；orchestrator `:907`）；禁「必互異」閘正確。同 symbol train/test 仍須相等（既有 `validate_split_pair_integrity`）。

④ **指紋可重算性**：**骨架已封閉 int／空 plan／重複 position／函式點名／取數來源**，但 **rows 容器形狀未釘死**（list-of-lists vs list-of-dicts）→ 兩端可各自「合法」卻 sha256 永異；見 P1-01。其餘（post-trim `feature_index`、禁全框 ts、欄位順序對齊 G-5）足夠。

⑤ **golden 重凍與獨立 oracle**：**必要且足夠作為收案門**。C2.7 要求改前／改後逐值對照＋獨立 oracle（由 row_index＋universe 重算 vs plan 欄）——可防「只改 hash」。前提＝P1-01 先釘死與 freeze 同一形狀，否則 oracle／G-5／plan 欄會各凍一份。

⑥ **ASSERT 可證偽性**：**8.1／8.2／8.3 固定文法 ASSERT 改壞會紅**（含 Mapping 缺失、symbol 不一致專訊、joint hash 放行、row 空間混用、指紋中列漂移、缺欄、空指紋、門檻 per-symbol、`single_symbol` 僅 n==1）。未發現新的字面互斥（R5 P1-02 已修）。

⑦ **mutation 對照**：**`M-SU-D1-01`～`07` 皆能對到 `-k` 軸**；`M-SU-D1-07` 補上 C1.4。無新缺列。

⑧ **範圍切割**：**排除 D1／R-5／SU-RESID-2 不留 b8 一上線即不自洽之中間態**。b8＝R-1＋SU-RESID-3＋門檻後，單 TF 多 symbol 可自洽；多 TF 續 fail-closed、D1 續 event-study-only——皆既有保守態。

### 3. 駁回之重驗（V0／CODEX-R5-P0-01）

① **接受駁回**。Rule 12（`Agents.md:40`）規範對象是「**動工前**…**不動工**」——本輪為唯讀規格審查，不是實作動工。R5 synth 第 5 點先例（同家先前三輪上游無戳記仍照審）成立；consult-r2 為諮詢層、本票慣例不對每份收斂檔蓋章。

② **反面**：若仍主張須先蓋章，請指出「唯讀規格審查」落在規則哪一字——**落不到**。「動工／不動工」無涵蓋 read-only review 之字面；把 Rule 12 擴到審查＝自行加嚴，且與自身先例不一致。

### 4. C-4 覆寫後之薄 wrapper

① **不會成為第二份判定邏輯入口——若且唯若** wrapper 只做「單鍵 Mapping 包裝＋轉呼」，不含 purge／成員判定／指紋比對分支。D-001-C1.1 已明文「不得含第二份判定邏輯」。風險＝同一函式內用 `isinstance` 分派後又複製一套 fail-closed；那才算第二入口。

② **`pipeline.py:745-752` 現行四位置式**：可**維持舊呼叫式走薄 wrapper**（單標的路徑最小改動），或改成  
`derive_event_split_from_plans({sym: (train_plan, test_plan)}, keys, {sym: feature_index}, manifest=…, bucket_ms=…, tier_min_test_events=…)`。  
兩式不可長期並存兩套判定；Task 8.1 已列 `pipeline.py` 為修改檔——收案時應只剩「Mapping 主路徑＋wrapper 轉呼」一條判定鏈。

### 5. 可否進入實作？

**不可（`VERDICT: blocked`）。** 阻擋：GROK-R6-P1-01（指紋 rows 容器形狀未釘死 ⇒ b8 指紋／G-5／獨立 oracle 可永久對不齊）。P2 建議同修，不單獨擋。

---

## §1 十一類速查

1. 矛盾／互斥：有（P1-01 形狀歧義；P2-01 C1.2 vs C2.1）  
2. 漏項／端到端：輕（P2-02 C-4 覆寫範圍不清）；producer 清單 R5 已補  
3. 不可測驗收：ASSERT／mutation 本輪可證偽  
4. 可疑 quant 假設：無；hash 放寬有碼證  
5. 過度工程：無  
6. OOM／並行：無  
7. Cache：無  
8. API／型別／相容：指紋欄＋wrapper；形狀須先釘  
9. 測試品質：R5 缺口已補；形狀歧義會讓 fingerprint 測各說各話  
10. Agent 可執行性：P1-01  
11. 必要性／短命工：無

## 被當成事實的未驗證假設（§0）

1. 「與 freeze 同一形狀」已被寫成事實，但未釘 `list[list]` vs `list[dict]`——本輪實跑否證「已足夠封閉」（P1-01）。  
2. 「指紋不足以分辨兩 symbol」在 symbol 已入 payload 後仍當事實寫——字面為假（P2-01）。  
3. 「薄 wrapper 不構成第二份判定」——brief assumed／未實作；本輪以規格字面＋呼叫點立場接受，條件見必答 4。

---

## GROK-R6-P1-01

**斷言**: D-001-C2 第 1 點同時要求指紋與 `freeze_splitunify_golden.py`「同一形狀」、又強調「欄名採 `position`／`feature_ts_ms`」，但未釘死 `rows` 是與 freeze 相同的 **list-of-lists** 還是 **list-of-dicts**；兩形之 sha256 不同，b8 會讓 plan 指紋、G-5、獨立 oracle 永久對不齊或各凍一份。

**碼證**: D-001-C2 L56「四元組…同一形狀…`json.dumps(rows, sort_keys=True, …)`…欄名採…`feature_ts_ms`，不得使用舊稱…`ts_ms`」；BASE §G G-5① 文件稱呼含 `feature_ts_ms`；freeze `:152-154` 實作為 `[[int(p), int(ms[p]), SYM, "splitunify-golden"], …]` 且註解寫 `ts_ms`。VERIFY: `venv/bin/python` 對同一邏輯列 list-dumps sha=`da52843ab235…`、dict-dumps sha=`3a725986cbe4…`。RECHECK: 對讀 D-001 L56 與 `sed -n '152,154p' scripts/freeze_splitunify_golden.py`；重跑上述兩形 sha 對照。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73;scripts/freeze_splitunify_golden.py#6fb0c7361dad;docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[BLOCKING] 信心度=High。不改會在 b8 實作／收案失敗：①實作讀「欄名」→用 dict → plan 指紋 ≠ freeze／既有 G-5 演算法；②實作跟 freeze 用 list → 與「欄名／禁 ts_ms」文案衝突，reviewer／第二實作者可改成 dict 而使 ASSERT「同一 index 重算兩次」在不同 helper 間假綠、跨端比對紅。修法：釘死 `rows: list[list]`，元素順序固定為 `[int(position), int(feature_ts_ms), str(symbol), str(base_universe_hash)]`（與 freeze `:153-154` 逐字同形）；「欄名」僅文件稱呼、**不進 JSON**；同步改 freeze 註解之 `ts_ms`→`feature_ts_ms`；Task 8.2 檔案列明 `scripts/freeze_splitunify_golden.py`。

## GROK-R6-P2-01

**斷言**: C1.2 經 R5 改寫後仍稱「同曆同切分的兩個 symbol 可得到相同的時刻序列，指紋不足以分辨」，但 C2.1 已把 `symbol` 納入四元組 payload——兩 symbol 指紋必異，該句為假；屬 GROK-R5-P2-02 修訂殘留。

**碼證**: D-001 C1.2 L48「指紋不足以分辨」；C2.1 L56 四元組含 `symbol`。RECHECK: 構思同 `position`／同 `feature_ts_ms`／同 `base_universe_hash`、不同 `symbol` 之兩列 → dumps 字面不等。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73

[MAJOR] 信心度=High。不擋作唯一 P0，但會誤導實作以為可省略 C1.3，或反向以為指紋已足夠而刪三角相等。修法：刪「指紋不足以分辨」；改為「指紋含 symbol 可區分列所屬標的，但 Mapping key／`plan.symbol`／事件 symbol 之三角相等仍為獨立必查，不得只靠指紋」。閉合後可將 GROK-R5-P2-02 標已閉合。

## GROK-R6-P2-02

**斷言**: 觸及面把整節 `### C-4 …` 列為「覆寫」，但延伸檔沒有 `### C-4` 全文替換塊，只在 D-001-C1.1 給新簽名＋薄 wrapper；BASE C-4 其餘義務（`event_keys` 欄位契約、禁 positional zip、兩段式判定、`build_event_keys` 具名等，約 87 行）未重述——merge 讀者可能把未重述段當成已廢止。

**碼證**: D-001 觸及面 L16 覆寫含完整 C-4 heading；L20 註「新簽名見 D-001-C1 第 1 點」；正文僅 L28-42 簽名塊；`grep -n '兩段式\|build_event_keys\|positional zip' docs/SPLITUNIFY_SPEC.D-001.md` → 無（僅簽名參數名 `event_keys`）；BASE C-4 自 L157 起至下一 `###` 約 87 行。RECHECK: 對讀觸及面表與 BASE C-4 全節。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73;docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[MAJOR] 信心度=Medium。b8 若只改簽名、碼內兩段式仍在，短期不一定紅；但 SPEC 權威若丟 E1／E2，後續 refactor／第二 agent 可合法刪「禁 positional zip」而無規格違規訊號。修法：觸及面改「覆寫 C-4 **簽名段**」並把 BASE C-4 其餘段落改列「依賴（仍有效）」；或在內容貼上「C-4 其餘段落原文仍有效」之明示句。

---

ASSUMPTIONS_VERIFIED: R5 本家 5 條中 4 條閉合、P2-02 殘留升 R6；list vs dict sha 實跑不同；Rule 12 字面僅管動工；觸及面錨點逐字存在；pipeline 仍舊簽名；生產碼無指紋欄
TESTS_RUN: `grep -rn row_time_fingerprint momentum/ --include='*.py'` → 0 hits；`venv/bin/python` list/dict sha 對照 → 兩值不同；`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md` → rc=1（缺戳記，作 V0 反證材料）；`bash scripts/debt_ledger.sh --has-open` → rc=1（本輪 OPEN，符合 brief 預期）；completeness 見下
FAILURES_SEEN: none（審查輪）
SCOPE_CHANGES: none（僅新增本產出檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r6-grok.md

VERDICT: blocked
BLOCKED-BY: GROK-R6-P1-01
CLOSED: GROK-R5-P1-01,GROK-R5-P1-02,GROK-R5-P2-01,GROK-R5-P2-03
STATUS: DONE
