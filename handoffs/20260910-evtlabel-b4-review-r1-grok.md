# EVTLABEL B4（Phase 3 第二批：Task 3.4–3.7）code review R1（grok）

brief-kind: review  
task-id: 20260910-EVTLABEL-B4-REVIEW-R1  
family: grok  
findings-round: R1  
標的 diff：`git diff 34381156..06ccb917 -- momentum tests handoffs`  
SCOPE: review-only；禁改碼／禁改文件  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0／§1（審查對象＝碼）＋`templates/COMMITTEE_FINDING_TEMPLATE.md`

SOURCE-DIGESTS:
- `momentum/Analysis/ic_filter_orchestrator.py#a969eda9ca6e`
- `momentum/Analysis/binary_discrimination.py#28e741139299`
- `docs/EVTLABEL_SPEC.md#4edf088480ca`
- `handoffs/20260910-EVTLABEL-B4-REVIEW-R1-BRIEF.md#1cbd900e7239`
- `momentum/Analysis/ic_config_schema.py#9f91c8745261`

---

## Verdict：需修補後派工（不可直接進 Task 3.8／3.9）

Task 3.4–3.6 主路徑（mode 決策、MW 向量化、三守衛、binary 門檻分流）結構清楚，與 SPEC 對得上。  
**阻塞在 Task 3.7 依賴建模與負對照校準**：① `feature_bar_ms` 啟發式在稀疏事件下扭曲 `block_len`；② `_binary_label_window_bars` 未在 `analyze` 入口歸零且只在 `ic_train_test_split=True` 分支寫入 ⇒ 全樣本／跨 run 可變成 `W=0`⇒`L=1`（區塊保護消失）；③ `n_observed`（置換後）與 `shuffled_counts`（只跑門檻）不同義；④ 真實規模 10% NaN 之負對照估時 **~207s > 120s**（SPEC 閘會紅）。  
**P0=1／P1=3／P2=2／P3=0**。修完 P0／P1 再進倖存者輸出與前端。

---

## 驗收／探針實跑

| 命令／探針 | 結果 |
|---|---|
| `mann_whitney_table` 39373×31 clean | **MW_once=0.090s** ⇒ NC×50 估 **4.5s** |
| `mann_whitney_table` 39373×31 10% NaN | **MW_once=4.140s** ⇒ NC×50 估 **207.0s**（>120） |
| `block_ids_for_events` 啟發式 vs 真 bar（事件每 3 根、W=12） | `bar_wrong=10800000`→**L=12,n_blocks=1**；`bar_true=3600000`→**L=4,n_blocks=3** |
| 2000 欄 probe（5 次 NC） | 31 clean 0.23s／31 nan10 1.34s／165 clean 0.26s／165 nan10 1.49s |
| `analyze` 入口是否清空 `_binary_label_window_bars` | **否**（只清 `_stage_timings`） |
| 掃描格是否重用 orchestrator | **否**（`analyzer_factory` 每格新建；`ic_analysis_service.py` 註解 CODEX-R1-P1-01） |

VERIFY 摘要命令（本輪）：
```text
venv/bin/python -c '…mann_whitney_table 39373×31 clean/nan10…'
# clean MW_once=0.090s NC50_est=4.5s
# nan10 MW_once=4.140s NC50_est=207.0s
```

---

### §0 前提宣告

fact-verified: `_binary_feature_bar_ms`＝相鄰事件最小正間距；稀疏（每 3 根一事件）⇒ **L 被高估**（12 vs 真 4），不是作者所稱「低估」。  
fact-verified: `_binary_label_window_bars` 只在 `ic_train_test_split` 真分支賦值；`analyze` 入口不歸零。  
fact-verified: 負對照內聯判準在 `fdr_enabled=True`（預設）時與 `_apply_thresholds(binary_mode=True)` 之 status／\|rb\|／q≤α **同義**；但函式未複用，且 **未傳 `fdr_enabled`**（FDR off 時會分叉）。  
fact-verified: `n_observed=len(survivors)` 在置換自檢**之後**；`shuffled_counts` **不含**置換自檢。  
fact-verified: 39373×31 nan10 NC×50 估時 **207s > 120s**。  
fact-verified: 掃描格每格独立 analyzer（不重用實例）。  
fact-verified: B4 diff 未改 `tests/golden`／既有紅具名檔；只動 evtlabel 新測與 orchestrator／binary_discrimination。  

assumed: 最小正間距＝一根特徵 K 線 → **本輪推翻**（方向＝高估 L／區塊變少）。  
assumed: 負對照計數與主篩選同義 → **部分成立**（門檻閘同；`n_observed` 尺度不同義）。  
assumed: 真實規模 NC <120s → **10% NaN 推翻**；clean 成立。  
assumed: `_binary_label_window_bars` 不跨 run 殘留 → **推翻**（入口未清；split=False 不寫）。

### §0 前提覆核摘要表

| 陳述 | 本輪 verdict | 依據 |
|---|---|---|
| min gap＝1 根 bar | **不成立** | 啟發式 demo L 12 vs 4 |
| NC 判準＝`_apply_thresholds` | **門檻層成立／整包不成立** | 碼比對＋`n_observed` 含置換 |
| NC 39373×50 <120s | **clean 成立／nan10 不成立** | 4.5s vs 207s |
| window_bars 無殘留 | **不成立** | 入口未清；只在 split 分支寫 |
| 掃描格重用 orchestrator | **不成立（已修）** | per-cell factory |
| 本批加重既有 20 紅 | **未見** | diff 檔名＋HANDOFF 歸因 |

---

## 必答（成對）

### 1a. `_binary_feature_bar_ms` 啟發式是否為真洞？

**是真洞。** SPEC Task 3.7 要求 `L=max(1,ceil(W/min_gap),ceil(W/median_gap))`，gap 單位必須是**真實特徵 K 線根數**。現行用「相鄰事件最小正間距」當 `feature_bar_ms`：事件皆相隔 ≥k 根時，會把 1 根誤標成 k 根。  
**失敗方向與 brief 相反**：不是低估 `block_len`，而是**高估**（demo：真 L=4／n_blocks=3 → 錯 L=12／n_blocks=1）。後果＝區塊過少 → 更容易 `unavailable:insufficient_blocks`（過度 fail-closed），或依賴結構被扭曲使置換／負對照校準失真。

### 1b. 正確做法（含應由誰傳入）

由 **`metadata.timeframe` → `EXPECTED_FREQ_BY_TIMEFRAME` → milliseconds** 顯式傳入（orchestrator 已有 `_resolve_expected_freq`）。在 `analyze` 入口（stage0 後）算一次 `self._binary_feature_bar_ms = int(expected_freq.total_seconds()*1000)`，Task 3.7 只讀此欄；**刪除** `_binary_feature_bar_ms(sel_ms)` 啟發式。缺／不支援 timeframe ⇒ fail-closed raise（與 split 路徑同一套），禁再猜。

### 2a. `_binary_label_window_bars` 會不會跨 run／跨格殘留？

**會跨 run 殘留；跨掃描格不會。**  
- 掃描格：每格 `analyzer_factory()` 新建 ⇒ 無跨格污染。  
- 同一 analyzer 連續 `analyze`：入口只清 `_stage_timings`，**不清** `_binary_label_window_bars`。  
- 賦值僅在 `if config.ic_train_test_split:`（`:1214`）。`split=False`（含使用者要求的全樣本、以及 fallback 內層）**不寫** ⇒ 留下一次的值，或停留 `__init__` 的 0。  
- `W=0` ⇒ `block_ids_for_events` 走 `block_len=1`（`:201-202`）⇒ **區塊保護關閉**（低估依賴；置換過度樂觀）。

### 2b. 最小修法

1. `analyze` 入口與 `_stage_timings` 一同：`self._binary_label_window_bars=0`；並清 `_survivor_suppressed_reason`／`_binary_oracle_receipt`。  
2. **不論 split 開關**，只要有 `event_isolation` 就寫：`self._binary_label_window_bars=int(event_isolation.label_window_rows)`（無則 0）。Fallback 外層已寫、內層不清的「碰巧正確」改成顯式每次寫入。  
3. 測試：同一 orchestrator 先 W=12 再全樣本 W=5；斷言第二次 receipt.`block_len` 用 5 而非 12／0。

### 3a. 負對照判準與 `_apply_thresholds` 是否同義？

**門檻三條件在預設 FDR on 時同義；整段流程不同義。**

| 檢查 | `_apply_thresholds(binary_mode=True)` | 負對照內聯 |
|---|---|---|
| `status==ok` | 有 | 有 |
| `abs(rb)>=rank_biserial_min` | 有 | 有 |
| `q<=alpha_effective` | `mw_p_value_adj`（FDR on）或 `mw_p_value`（off） | **永遠** `apply_fdr` 後的 q（**忽略 `fdr_enabled`**） |
| 報酬六閘 | 記錄不剔除 | 不跑（等同） |
| 之後置換自檢 | 會再刪 | **不跑** |

預設 `significance.fdr.enabled=True` ⇒ 單列通過集合應一致。`fdr_enabled=False` ⇒ 主路徑讀 raw p、NC 仍讀 q ⇒ **分叉**。且 NC **未呼叫** `_apply_thresholds`（兩份邏輯）。

### 3b. 最小修法

抽一個純函式（例如 `_count_binary_threshold_hits(tbl, *, alpha, rb_min, fdr_enabled, fdr_method) -> int`），`_apply_thresholds` 與負對照共用；NC 簽名補上 `fdr_enabled` 並從 stage5 傳入。禁止再手寫第二份 if。

### 4a. 置換只跑 `passed` 是否讓 `n_observed` 與 shuffled counts 不同義？

**是，不同義。**  
- `n_observed`＝門檻通過**且**置換 `in_band==False` 的人數。  
- `shuffled_counts[i]`＝置亂標籤後只跑 MW＋BH＋效應量閘的人數（**無**置換自檢）。  
比較的是兩個不同程序的計數 ⇒ `n_observed <= q95` 的校準意義被削弱（通常讓 `n_observed` 偏小 ⇒ 更容易 `negative_control_failed` 誤殺整批）。

### 4b. 正確做法

與 SPEC「(B) 整批校準 vs (C) 逐特徵放行」對齊的最小修法：  
**`n_observed` 改為門檻通過數（置換前）**，置換自檢只影響 consumable／`removed["permutation_*"]`，不進入 NC 比較。  
（對每個 shuffle 再跑置換＝50×K×n_perm，成本不可接受，不建議。）

### 5a. 真實規模負對照耗時？

| 形狀 | MW×1（實跑） | NC×50（×50 估算） |
|---|---|---|
| 39373×31 clean | 0.090s | **~4.5s** |
| 39373×31 10% NaN | 4.140s | **~207s** |
| 39373×165 clean（brief [A-2]） | ~0.49s | **~25s** |
| 39373×165 10% NaN（brief） | ~4.02s | **~201s** |

算式：`t_NC ≈ 50 × t_MW_once`（未計 FDR／逐欄 hit 迴圈；實際略高）。SPEC Task 3.7 驗證 (b) 要求 39373×31 clean **與** 10% NaN 皆 `<120s` ⇒ **nan10 估時失敗**。

### 5b. 超 120s 該降階還是改設計？

**改設計，不是默默降 N。** 選項（擇一寫進修補＋重跑 gate）：  
1. NaN 路徑避免 scipy 逐欄退化（預先 mask／分塊，或對 NC 用較便宜的 rank-sum 近似並釘 oracle）；  
2. NC 只在 **效應量預篩後的欄子集** 上重算（須證明不偏校準）；  
3. 若產品接受：契約把 nan10 門檻改為「印 receipt＋分 tier」，但須使用者否決——**不可**為過 gate 偷降 `negative_control_n`。

### 6a. `features_for_stats` 是否恆等於 selection scope？

**列層面：是（有切分＝`test_mask` 切片；無切分＝全列）。** `_slice_by_mask` 只切列不切欄。stage5 用同一物件做 MW 與三守衛，內洽。  
注意：`ValidatedBinaryLabel.series` 在 stage3 綁的是**全** `filtered_features.index`，stage5 再 `reindex` 到 selection——守衛走子集路徑，與「統計對象＝selection」一致。

### 6b. 若否，守衛是否比錯對象？

本批**未發現** stage5 在對證前又過濾欄／列而使守衛對象漂移。`summary_table` 用 `features_df.columns` 建、MW 用 `features_for_stats.columns`；列切後欄應相同。殘餘風險見 P2-01（名對不上時 `continue`）。

### 7a. 列名對不上時 `continue` 是否該改 raise？

**應該改成可觀測失敗（raise 或計數断言）。** 正常路徑不該發生；若發生，`continue` 讓該列缺 binary 欄 → 之後被 `binary_unavailable` 剔除（偏 fail-closed），但**不留對齊錯誤訊號**，與三守衛「對不上就 raise」的精神不一致。

### 7b. 判斷與理由

最小修法：merge 結束後 `assert n_merged == len(tbl)`（或 `missing = set(tbl.index)-merged` ⇒ 非空 raise `AlignmentViolationError`）。信心度 High。

### 8. ≥10× 不必要複雜？可否進 3.8／3.9？

複雜度與 SPEC 三層（MW／門檻／置換+NC）匹配，**無** 10× 過度工程。  
**不可**直接進 Task 3.8／3.9：P0／P1 會讓「倖存者／suppressed」建立在錯的區塊長度或錯的 NC 尺度上，前端只會把錯結論畫得更漂亮。

---

## Findings

## GROK-R1-P0-01

**斷言**: `_binary_label_window_bars` 未在 `analyze` 入口歸零，且僅在 `ic_train_test_split=True` 分支寫入；全樣本起跑或跨 run 重用同一 orchestrator 時可得到 `W=0`⇒`block_len=1`，區塊依賴保護關閉，置換自檢過度樂觀。

**碼證**: `ic_filter_orchestrator.py:1148-1151` 只清 `_stage_timings`；`:1211-1214` 賦值包在 `if config.ic_train_test_split`；`:4766-4767` 讀 instance 狀態；`binary_discrimination.py:201-202` `w==0 ⇒ block_len=1`。掃描格不重用實例（`ic_analysis_service.py` per-cell factory）≠ UI／服務連續 analyze 同實例。  
RECHECK: 同一 `ICFilterOrchestrator` 先 analyze(split+W=12) 再 analyze(split=False, event_isolation W=5, binary)；讀 `_binary_oracle_receipt["block_len"]` 是否仍用 12 或變成 1。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#a969eda9ca6e

[P0] 信心度=High。失敗模式＝該擋的依賴結構沒擋 → 假倖存者可進 consumable（主目標「找出能分開的特徵」變假陽性）。  
修法：入口歸零＋**每次**自 `event_isolation.label_window_rows` 寫入（見必答 2b）；加跨 run 回歸測試。

## GROK-R1-P1-01

**斷言**: `_binary_feature_bar_ms` 以事件最小正間距充當特徵 K 線長度；事件稀疏時會**高估** `block_len`、低估 `n_blocks`，扭曲置換與負對照的依賴模型（SPEC 未授權此啟發式）。

**碼證**: `ic_filter_orchestrator.py:4845-4856`；`binary_discrimination.py:174-210`。實跑 demo：事件每 3×1h、W=12 → 錯 `L=12,n_blocks=1`／真 bar `L=4,n_blocks=3`。  
RECHECK: 同上數值；修後改吃 `EXPECTED_FREQ_BY_TIMEFRAME[metadata.timeframe]`。

**來源摘要**: momentum/Analysis/binary_discrimination.py#28e741139299

[P1] 信心度=High。失敗模式＝過度 fail-closed（`insufficient_blocks`）或校準失真。作者 brief 寫「低估 L」方向有誤，洞仍成立。  
修法：見必答 1b；刪啟發式。

## GROK-R1-P1-02

**斷言**: 負對照的 `n_observed` 取置換自檢**後**的 survivors，而 `shuffled_counts` 只重跑 MW＋BH＋效應量閘；兩者不同義，使 `n_observed <= q95` 失去「同一篩選程序」的校準解釋。

**碼證**: `ic_filter_orchestrator.py:4783-4800`（perm 後 `n_observed=len(survivors)`）；`:4807-4828`（shuffle 只 `mann_whitney_table`+FDR+rb，無 `block_permutation_oracle`）。SPEC Task 3.7 文案亦把 (B) 寫成「Task 3.5＋BH＋效應量閘」，與實作的 `n_observed` 定義不一致。  
RECHECK: 人造資料令 3 特徵過門檻、其中 2 個 `in_band`；斷言現行 `n_observed==1` 但 shuffle 期望尺度≈3。

**來源摘要**: docs/EVTLABEL_SPEC.md#4edf088480ca

[P1] 信心度=High。失敗模式＝整批被錯誤 `negative_control_failed` suppressed（誤殺），或相反場景下校準偏鬆。  
修法：見必答 4b（`n_observed`＝置換前門檻通過數）。

## GROK-R1-P1-03

**斷言**: 39373×31、10% NaN、`negative_control_n=50` 之負對照估時約 **207s**，超過 SPEC Task 3.7 驗證閘 120s；作者承認 TODO benchmark 未跑。

**碼證**: 本輪實跑 `mann_whitney_table` 39373×31 nan10 **4.140s**；`50×4.140=207s`。clean 同形 **0.090s → 4.5s**（過閘）。brief assumed 列「沒跑」。  
RECHECK: `handoffs/20260910-evtlabel-mutate.py --phase 3b` 內建／或 TODO 兩道 benchmark 實跑秒數。

**來源摘要**: handoffs/20260910-EVTLABEL-B4-REVIEW-R1-BRIEF.md#1cbd900e7239

[P1] 信心度=High（單次 MW 實測；×50 為線性外推，FDR 迴圈只會更慢）。失敗模式＝分析從分鐘級變數分鐘／小時級，或為過閘偷降 N／改 NaN 政策。  
修法：見必答 5b；先實跑官方 benchmark 再定案。

## GROK-R1-P2-01

**斷言**: `_merge_binary_statistics` 在 `summary_table` 列名不在 MW 表時 `continue`，對齊失敗被降成「缺欄 → binary_unavailable」，與三守衛 fail-closed 不一致。

**碼證**: `ic_filter_orchestrator.py:4921-4924` `if name not in tbl.index: continue`。正常列切後欄應齊；一旦上游漂移會靜默少合併。  
RECHECK: 手動從 summary 加幽靈 `feature_name` 或不在 X 的名，觀察是否 raise。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#a969eda9ca6e

[P2] 信心度=Medium。修法：merge 後缺名 ⇒ `AlignmentViolationError`（見必答 7b）。

## GROK-R1-P2-02

**斷言**: `_survivor_suppressed_reason`／`_binary_oracle_receipt` 同樣未在 `analyze` 入口清除；非 binary 或第二次 run 可能讀到上一次的 suppressed／receipt（Task 3.8 接上後會變成跨 run 幽靈狀態）。

**碼證**: `__init__` `:1060-1065`；`analyze` 入口無清除；僅在 `_run_binary_permutation_and_negative_control` 內賦值。同型先例＝B1／FU-3 計時殘留（`:1148-1151` 註解已承認 analyze-scoped 必須入口清空）。  
RECHECK: binary 觸發 `negative_control_failed` 後再跑 `return_rule` analyze，讀 instance 欄是否仍為舊值。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#a969eda9ca6e

[P2] 信心度=High。修法：與 P0-01 同一處入口歸零。

---

### §1 十一類（無則標無）

1. 矛盾/互斥：有——SPEC (B) 計數定義 vs 實作 `n_observed`（P1-02）；brief「低估 L」vs 實測高估（P1-01）。  
2. 漏項/端到端：有——Task 3.7 官方 benchmark 未跑（P1-03）；stage6／6b binary 分數與 metadata 揭露屬作者「我沒查的」殘留（下批，非本批 regress）。  
3. 不可測驗收：有——NC 與 `_apply_thresholds` 無相等測試釘死（brief 自承）。  
4. 可疑 quant 假設：有——bar_ms 啟發式；`W=0⇒L=1` 關閉依賴保護（P0-01／P1-01）。  
5. 過度工程：無（≥10× 無）。  
6. OOM/並行：無新並行；耗時見 P1-03。  
7. Cache 正確性：無新 cache key；instance 狀態殘留見 P0-01／P2-02。  
8. API/型別/相容：return_rule 路徑未寫 binary 欄（與 SPEC G-4 一致）；無前端本批。  
9. 測試品質：mutation 8/8 與 stage 單測覆蓋主路徑；缺 bar_ms 稀疏事件、跨 run window、NC↔thresholds 相等、39373 nan10 bench。  
10. Agent 可執行性：修法已落到函式／入口行級。  
11. 必要性/短命工：無（本批產出為 P3 核心，非短命鷹架）。

---

## 既有紅歸因（必答 8 附）

B4 diff 只動 `binary_discrimination.py`／`ic_filter_orchestrator.py`／evtlabel 測試／mutate 腳本，**未改** HANDOFF 具名之 golden／persist 污染測試檔。未重跑 `tests/momentum/Analysis` 全套（禁治理小時級；brief 亦以既有紅為基準）。**未驗證「更嚴重」之逐條秒數**；就檔名與呼叫面判斷本批**未接入**那 20 條的生產路徑。建議 REDSWEEP 另票。

STATUS: DONE
