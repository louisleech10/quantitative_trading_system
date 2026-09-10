brief-kind: review
task-id: 20260910-EVTLABEL-B4-REVIEW-R1
family: composer
findings-round: R1
標的 diff：`git diff 34381156..06ccb917 -- momentum tests handoffs`

## Verdict：需修補後派工

Task 3.4–3.7 主線（mode 決策／Mann-Whitney／binary 門檻／置換＋負對照）結構可辨，236 條 B4 測試批與 gate 3b 已過。但 **四條 P1** 會在真實稀疏事件或 full-sample binary 路徑上靜默削弱區塊置換／讓負對照尺度失真：**① `_binary_feature_bar_ms` 把最小事件間距當「一根 K 線」**；**② `_binary_label_window_bars` 只在 split 分支寫入且 analyze 入口不歸零**；**③ 負對照內聯判準在 `fdr_enabled=False` 時與 `_apply_thresholds` 分歧**；**④ `n_observed`（倖存者 post-oracle）與 shuffled counts（全表 inline）不同義**。P1 最小修補後可進 Task 3.8／3.9；真實規模負對照 ~20s（非小時級）但 TODO benchmark 仍應補。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| 最小正事件間距＝一根特徵 K 線（`_binary_feature_bar_ms`） | **推翻** | 必答 1a；3× 稀疏事件 ⇒ `block_len` 12 vs 正確 4、`n_blocks` 2 vs 5 |
| 負對照判準與 `_apply_thresholds` 同義 | **部分推翻** | 必答 3a；`fdr_enabled=True` 一致；`False` 時主路徑多 3 特徵 |
| 39,373 欄 × 50 次負對照非小時級 | **fact-verified（本輪）** | 必答 5a；實跑 NC 環 19.4s、單次 MW 0.75s |
| `_binary_label_window_bars` 不跨 run 殘留 | **部分推翻** | 必答 2a；掃描格每格新 instance OK；split 外路徑不寫／入口不歸零 |
| 置換自檢只跑 `passed` 與 shuffled counts 同義 | **推翻（設計）** | 必答 4a；兩者計數母體不同 |
| 本批加劇 HANDOFF 20 條既有紅 | **維持** | 必答 8；B4 測試批未觸及 persist/golden/inventory 根因 |

---

## 必答（成對）

### 1a／1b `_binary_feature_bar_ms` 啟發式

- **1a**：**是真洞**。函式註解假設「最小正間距即一根」（`:4846-4848`），但稀疏事件下最小間距 = N 根 ⇒ 推得 `bar_ms = N × true_bar`。`block_ids_for_events` 雖用 `gaps/bar` 換算，但因 `bar` 已被放大 N 倍，相鄰事件在「bar 單位」仍變成 1 ⇒ `block_len = ceil(W/1)=W`（事件數），而非正確的 `ceil(W/N)`。VERIFY: `/tmp/evtlabel-b4-review-composer/bar_ms_probe.out` — 事件每 3 根、`W=12` ⇒ inferred `block_len=12, n_blocks=2`；true_bar `block_len=4, n_blocks=5`（後者 `n_blocks<10` 風險更低且區塊更細）。
- **1b（最小修法）**：**禁止**從事件間距反推 bar 寬。應由 **`metadata.timeframe`**（service 已注入 `:1187-1190`）換算 `feature_bar_ms = timeframe_seconds × 1000`（或沿用 `_resolve_expected_freq`），經 `analyze(..., event_isolation=...)` 顯式 kwarg 或 stage5 前寫入 orchestrator；`_binary_feature_bar_ms` 改為讀該常數或刪除。修訂位置：`:4765`、`:4845-4855`、`binary_discrimination.py:198-209`。

### 2a／2b `_binary_label_window_bars` instance 狀態

- **2a**：**掃描格／每 task 新 analyzer 無跨格污染**（`:1565`、`:1632`）。但 **analyze 入口不清 `_binary_label_window_bars`**（對照 `:1150` 清 `_stage_timings`），且 **只在 `config.ic_train_test_split` 分支 `:1212-1215` 賦值**——full-sample 直跑或 `ic_train_test_split=False` 時維持 `__init__` 的 0 或上一輪殘值；fallback 遞迴 `analyze`（`:1640`）在 split 嘗試中可能已寫入 12、第二趟 split off 不再重寫。
- **2b（最小修法）**：`analyze()` 入口 `:1150` 旁加 `self._binary_label_window_bars = int(event_isolation.label_window_rows) if event_isolation else 0`（**脫離** split-only 區塊）；refilter 沿用 cache 時值已正確。一行重置 + 從 `event_isolation` 讀，不新增第二份狀態。

### 3a／3b 負對照判準 vs `_apply_thresholds`

- **3a（具體比對）**：VERIFY `/tmp/evtlabel-b4-review-composer/threshold_equiv.out` — 同表 31 欄、`alpha=0.05`：
  - `fdr_enabled=True`：主路徑 `['sig']` == 負對照 inline `['sig']` ✅
  - `fdr_enabled=False`：主路徑 `['f10','f11','f29','sig']` vs inline 仍 `['sig']` ❌
  - 根因：主路徑 `:4994` 讀 `mw_p_value`（raw）；負對照 `:4813-4826` **恆** `apply_fdr` 後比 `q <= alpha`。
- **3b（最小修法）**：抽 `_count_binary_passing(table, config, alpha, fdr_enabled)` 供 `_apply_thresholds` 與 `_run_binary_permutation_and_negative_control` 共用；或負對照改讀 `summary_table` 並呼叫 `_apply_thresholds(..., binary_mode=True)` 計數（shuffled 時先 `mann_whitney_table` 再 merge 成 row dict）。

### 4a／4b 置換自檢只跑 `passed`

- **4a**：**是，不同義**。`n_observed = len(survivors)`（`:4800`）= 過 `_apply_thresholds` **且** 逐特徵 oracle 通過；shuffled counts（`:4817-4828`）= 每輪對**全欄** `mann_whitney_table` 後 inline 門檻命中數，**不跑** oracle。主路徑倖存者 ⊆ 全表命中，但 `n_observed` 通常 **≪** shuffled count ⇒ `n_observed <= q95` 可能過嚴或過鬆，比較的不是同一隨機變量。
- **4b（正確做法）**：二選一並寫進 SPEC：（A）shuffled 也對同一 `passed` 候選集計數；或（B）`n_observed` 改為「全表 inline 門檻命中數（post-oracle 前）」與 shuffled 對齊。最小改法：負對照 loop 內用共用 counter，且 `n_observed` 改為 `_count_binary_passing(summary_table, ...)`（oracle 前）或對 `passed` 子集重算。

### 5a／5b 真實規模耗時

- **5a（實跑）**：`/tmp/evtlabel-b4-review-composer/bench_nc.out` — `39373×165`：`mann_whitney_table` 一次 **0.754s**；`negative_control_n=50` 全表循環 **19.377s**（≈0.388s/次）；stage5 負對照單項合計 **~20.1s**（不含逐倖存者 oracle）。算式：\(T \approx T_{\text{mw}} \times (1 + N_{\text{nc}}) = 0.754 \times 51 \approx 38.5s\) 上界（含一次主表）；實測 20.1s（主表與 shuffle 常數因子略異）。**非小時級**；若 K 倖存者各 200–1000 perm 單欄 oracle，粗估再加 **<10s**。
- **5b**：不必降階設計；應補 Task 3.7 TODO 兩道 benchmark receipt，並在 `metadata` 揭露 `negative_control_seconds`。若未來欄數 ×2 仍 <120s，維持現設計。

### 6a／6b `features_for_stats` vs selection scope

- **6a**：**列 scope 恆等**。stage5 `:4134-4137` `_slice_by_mask(..., test_mask)` 與 stage3 selection（brief：`split_context["test_mask"]`）同源；`_merge_binary_statistics` 守衛 `:4888-4910` 比對 `vb.series` 與 `features_for_stats.index`／`rows_frozenset`——對的是 **selection 列**。stage5 內無列刪減，僅欄向量化統計。
- **6b**：若未來 stage5 前加列過濾而不同步 guard ⇒ 會 raise（`:4888`）而非靜默；目前 **守衛對象正確**。列名 `continue`（`:4923-4924`）是欄名問題，見 P2-01。

### 7a／7b 列名對不上 `continue`

- **7a**：對不上 = `summary_table` 有列但 `mann_whitney_table` index 無該名（理論上不該；若發生 = 欄名正規化分裂或 table 建構漏欄）。`continue` **靜默**跳過 ⇒ 該列缺 `binary_status`，`_apply_thresholds` 走 `:4981-4982` `binary_unavailable`——fail-closed 但 **不 raise**，難查。
- **7b**：**binary 模式應改 warn+raise 或 assert**（至少 dev/test）；production 可 `AlignmentViolationError` 與前三守衛一致。`:4921-4924` 改 `if name not in tbl.index: raise AlignmentViolationError(...)`。

### 8 複雜度／既有紅／可否進 3.8

- **無 ≥10× 不必要複雜**；Mann-Whitney 向量化、block oracle 抽函式、mutation 8/8 合理。
- **既有紅**：HANDOFF「20 failed / 1615 passed」三類根因（persist 污染／golden／inventory）**不在本 diff**；B4 236 passed 未擴大失敗面。
- **進 3.8／3.9**：**須先收 P1-01–P1-04**（數值核心）；P2 可跟 3.8 並行。

---

## §1 必查摘要

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | 負對照 inline vs `_apply_thresholds` 在 FDR off 時不一致（P1-03）；`n_observed` vs shuffled 母體不同（P1-04） |
| 2 | 漏項 | `feature_bar_ms` 未從 timeframe 注入（P1-01）；full-sample 未寫 window_bars（P1-02） |
| 3 | 不可測 | gate 3b＋236 測試可驗；缺 39373×50 benchmark receipt（必答 5b） |
| 4 | quant | bar 啟發式削弱 block 置換（P1-01）；負對照尺度（P1-03/04） |
| 5 | 過度工程 | 無 |
| 6 | OOM | 39373 欄 MW ~20s/次 analyze，可接受 |
| 7 | cache | 無 |
| 8 | API | 本批未動 frontend |
| 9 | 測試 | mutation 8/8；缺 FDR-off 對照相等、稀疏 bar_ms golden |
| 10 | Agent | 落到檔案／函式 |
| 11 | 短命工 | 無 |

---

## COMPOSER-R1-P1-01

**斷言**: `_binary_feature_bar_ms` 用最小事件時間間距充當特徵 K 線毫秒寬，在事件稀疏（間距 ≥2 根）時把 `feature_bar_ms` 放大 N 倍，使 `block_ids_for_events` 算出過大之 `block_len`（以事件計），區塊數過少甚至 `<10` ⇒ 置換 oracle `unavailable` 或區塊保護不足。

**碼證**: `ic_filter_orchestrator.py:4845-4855` 註解「最小正間距即一根」；`binary_discrimination.py:198-209` `gaps = diff/bar`。VERIFY: `/tmp/evtlabel-b4-review-composer/bar_ms_probe.out` — 每 3 根一事件、`W=12`：inferred `block_len=12,n_blocks=2` vs true_bar `block_len=4,n_blocks=5`。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#a969eda9ca6e

[BLOCKING] 信心度=High。失敗模式：稀疏事件批看起來通過置換／負對照，實則單區塊或 insufficient_blocks。修法見必答 1b；修訂 `:4765`、刪除或改寫 `:4845-4855`，改從 `metadata.timeframe` 傳入。

---

## COMPOSER-R1-P1-02

**斷言**: `_binary_label_window_bars` 僅在 `config.ic_train_test_split` 為真時於 `:1215` 賦值，analyze 入口不歸零；full-sample／split-off 路徑可能以 0 或上一輪殘值跑 Task 3.7，與 `event_isolation.label_window_rows` 脫節。

**碼證**: 入口 `:1150` 只清 `_stage_timings`；`:1212-1215` 在 split 區塊內；`:4766` stage5 讀取。對照 B1「計時沒歸零」同型。RECHECK: full-sample binary run 設 `event_isolation.label_window_rows=12` 且 `ic_train_test_split=False` ⇒ `getattr(...,0)`。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#a969eda9ca6e

[BLOCKING] 信心度=High。失敗模式：答案窗 12 根卻 `w=0` ⇒ `block_len=1`（`:202-203`），置換假設錯。修法見必答 2b；**:1150` 旁從 `event_isolation` 統一賦值**。

---

## COMPOSER-R1-P1-03

**斷言**: 負對照 shuffled 計數恆用 FDR 調整後 `q<=alpha`，而 `_apply_thresholds(..., binary_mode=True, fdr_enabled=False)` 讀 raw `mw_p_value`，兩者通過集合可不一致，使 `q95` 與 `n_observed` 不在同一尺度。

**碼證**: 主路徑 `:4994-4996`；負對照 `:4813-4826`。VERIFY: `/tmp/evtlabel-b4-review-composer/threshold_equiv.out` — `fdr_off` 主路徑 4 欄 vs inline 1 欄。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#a969eda9ca6e

[BLOCKING] 信心度=High。失敗模式：使用者關 FDR 時負對照仍按 BH 計數 ⇒ 假陽性 suppressed 或漏 suppressed。修法見必答 3b；抽共用 counter 或複用 `_apply_thresholds`。

---

## COMPOSER-R1-P1-04

**斷言**: `n_observed` 為 post-oracle 倖存者數（`:4800`），shuffled counts 為全表 inline 門檻命中數（`:4817-4828`），且 oracle 只對 `passed`（`:4784`）——兩統計量不同義，`n_observed <= q95` 不能解釋為「隨機標籤也能篩出同量倖存者」。

**碼證**: `:4783-4800` vs `:4806-4828`；brief 必答 4 與 `:4748-4756` docstring 意圖衝突。RECHECK: 構造多欄過 p 閘但 oracle 全殺 ⇒ `n_observed=0` 而 shuffled counts 仍高。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#a969eda9ca6e

[BLOCKING] 信心度=High。失敗模式：整批 suppressed 或放行與雜訊基準不可比。修法見必答 4b；對齊計數母體（oracle 前全表或 shuffled 亦限 `passed`）。

---

## COMPOSER-R1-P2-01

**斷言**: `_merge_binary_statistics` 在 `name not in tbl.index` 時 `continue`（`:4923-4924`），不 raise，掩蓋 summary／MW 表欄名不一致，違反前三守衛「fail-loud」精神。

**碼證**: `:4921-4924`；後續 `_apply_thresholds` `:4981-4982` 僅標 `binary_unavailable`。RECHECK: 手改 `summary_table` 列名與 column 不符 ⇒ 靜默缺統計。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#a969eda9ca6e

[MAJOR] 信心度=Medium。修法見必答 7b；**:4923-4924` 改 raise**。

---

## COMPOSER-R1-P2-02

**斷言**: Task 3.7 TODO 要求之 39373×50 benchmark 未附 receipt，僅小 fixture；雖本輪實跑 ~20s 非小時級，缺持久 gate 會讓未來欄數膨脹時重犯 assumed。

**碼證**: brief assumed 表；本輪 `/tmp/evtlabel-b4-review-composer/bench_nc.out`。TODO `docs/EVTLABEL_TODO.md` Task 3.7 benchmark 兩道未勾。

**來源摘要**: docs/EVTLABEL_SPEC.md#4edf088480ca

[MAJOR] 信心度=Medium。補 `tests/momentum/Analysis/test_evtlabel_oracle.py` 或 handoffs receipt 釘住上界；非阻 3.8 但應跟進。

---

ASSUMPTIONS_VERIFIED: bar_ms 稀疏反例（bar_ms_probe）；threshold fdr on/off 對照（threshold_equiv）；39373×165 MW+NC 實跑（bench_nc）；掃描格每格新 analyzer（ic_analysis_service:1565）；stage5 slice 與 test_mask 同源（:4134-4137）
TESTS_RUN: `venv/bin/python` → `/tmp/evtlabel-b4-review-composer/{bar_ms_probe,threshold_equiv,bench_nc}.out` 均 rc=0
FAILURES_SEEN: none（審查未改碼）
SCOPE_CHANGES: none（唯讀 review）
NUMERIC_OR_SCHEMA_IMPACT: P1 不修則 block 置換／負對照結論不可信；不修 code，僅審查

產出: `handoffs/20260910-evtlabel-b4-review-r1-composer.md`

TMP_CLEANUP: 清 `/tmp/evtlabel-b4-review-composer`（保留 `claude-501`）

STATUS: DONE
