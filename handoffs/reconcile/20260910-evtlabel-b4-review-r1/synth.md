# Reconcile — 20260910-evtlabel-b4-review-r1

**來源** 20260910-evtlabel-b4-review-r1-codex.md, 20260910-evtlabel-b4-review-r1-composer.md, 20260910-evtlabel-b4-review-r1-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

三家一致：**無 ≥10× 不必要複雜**，但**不可直接進第三批**（有 P0／P1 blocker）。
19 條 findings 群集為七個修訂項，**全數採納並已修補**。

我在 brief 自列為可疑的四點（必答 1／2／3／5）**全部被證實成立**；
另有兩點是我沒想到的（稀疏子集套全表遮罩會崩、第三守衛沒用到 owners）。

### C1 — 🔴 P0：區塊依賴保護會被 instance 殘留狀態關掉
- findings：`GROK-R1-P0-01`、`CODEX-R1-P0-01`、`COMPOSER-R1-P1-02`（三家全員）
- `_binary_label_window_bars` 只在 `ic_train_test_split=True` 分支寫入、且 analyze 入口不歸零
  ⇒ 無切分時為 0 ⇒ `block_len=1` ⇒ 等於**逐筆洗牌**、相依保護整個失效；
  跨 run 重用同一 orchestrator 則沿用前值。置換自檢因此過度樂觀 ⇒ **假倖存者可進 consumable**。
- 處置：**採納並修補**。入口與 `_stage_timings` 同批歸零（另含 `_binary_feature_bar_ms`／
  `_survivor_suppressed_reason`／`_binary_oracle_receipt`），寫入點搬到切分分支之外。
- 同群另一條：`GROK-R1-P2-02` 具名指出 `_survivor_suppressed_reason`／`_binary_oracle_receipt`
  亦未在入口清除（Task 3.8 接上後會變成跨 run 幽靈狀態）——同一批修補已一併涵蓋，
  並以碼證測試逐一釘住四個欄位。

### C2 — 一根 K 線多長不得由事件密度猜（我方向也判反了）
- findings：`GROK-R1-P1-01`、`CODEX-R1-P1-01`、`COMPOSER-R1-P1-01`（三家全員）
- 我在 brief 推測此啟發式會**低估** `block_len`；兩家實跑證明相反——會**高估**：
  事件每 3 根、W=12 ⇒ 我算出 L=12（整批假性 unavailable），真值 L=4。
- 處置：**採納並修補**。啟發式刪除，改由 `metadata.timeframe` 經
  `EXPECTED_FREQ_BY_TIMEFRAME` 取；取不到 ⇒ 0 並整批 fail-closed（不猜）。

### C3 — 負對照拿蘋果比橘子
- findings：`CODEX-R1-P1-03`、`COMPOSER-R1-P1-03`、`COMPOSER-R1-P1-04`、`GROK-R1-P1-02`（三家全員）
- `n_observed` 取置換自檢**後**的倖存數，`shuffled_counts` 卻是全表門檻命中數
  （codex 實跑：passed_before_oracle=16、after_oracle=3、q95=16）⇒ 不同義。
  另 `fdr_enabled=False` 時主路徑讀 raw p 而負對照恆讀 q。
- 處置：**採納並修補**。`n_observed` 改為門檻通過數（置換前），與置亂端同一程序；
  置換後另揭露 `n_consumable`；負對照沿用同一 `fdr_enabled`；寫 `comparand` 講明比的是哪一個。

### C4 — 🔴 10% NaN 之負對照超過 SPEC 之 120s 閘
- findings：`GROK-R1-P1-03`、`CODEX-R1-P1-04`、`COMPOSER-R1-P2-02`（三家全員）
- 我首跑 benchmark **只測乾淨資料**（0.5s/次 ⇒ 50 次 26s，過關），故未見此情境。
  兩家各自實測 10% NaN：約 4–4.8s/次 ⇒ 50 次 199–239s。
- 處置：**採納並修補**。先量一次實際成本再決定跑得完幾次，降階一律揭露
  （`n_planned`／`n_effective`／`budget_seconds`／`degraded_by_budget`），下限 5 次；
  新增 `negative_control_budget_seconds`。並依 `COMPOSER-R1-P2-02` 之要求把 benchmark
  **併進 phase gate**（一次性 receipt 擋不住未來欄數膨脹時重犯）。
- 另：置換本身由 feature-major 改 **permutation-major**，K=2000／n_perm=200 由 123s 降到 4s。

### C5 — 🔴 稀疏事件子集套全表遮罩會當場崩潰（我沒想到）
- findings：`CODEX-R1-P1-02`
- codex 實跑 `IndexError: Boolean index has wrong length: 10 instead of 3`。
  我的測試沒抓到，因為 fixture 的遮罩長度剛好等於子集長度。
- 處置：**採納並修補**。`split_context` 改帶 canonical 測試段**時間戳**，
  stage3 以交集取 selection——兩邊都用時間戳表達，長度不匹配結構上不存在。

### C6 — 第三道守衛沒用到 owners（我沒想到）
- findings：`CODEX-R1-P2-01`、`GROK-R1-P2-01`、`COMPOSER-R1-P2-01`（三家全員）
- 只比 `(ts, label)`，`owners` 建了卻沒用（我原本還寫了「保留供未來診斷」的 assert）
  ⇒ 事件 id 被換掉但 (ts, label) 仍對得上時會放行。
  同批：summary 欄名對不上時 `continue`，把接線錯降級成單欄 unavailable。
- 處置：**採納並修補**。以 ts 反查所屬事件、三項全等才算同一份；欄名對不上改 raise。

### C7 — binary 下游仍用報酬統計
- findings：`CODEX-R1-P1-05`
- 處置：**採納並修補**（本批已補完，非留待下一批）：冗餘分數改 `abs(rank_biserial)`、
  報告揭露 `primary_statistic`／`secondary_statistic`／`effect_gate`／`imported_binary_label.used`、
  置換與負對照收據進 `event_label_rule`。
- 🔴 **具名殘留**：`stage6b` 之 `role="diagnostic"` 標記**尚未實作**（TODO 要點 5 之最後一項），
  留待第三批（Task 3.8／3.9）與倖存者輸出一起做。理由＝blocked-by：該節之語意欄位
  與 survivor payload 同批定案較不易分歧。

### 我方前提之驗證結果
- `assumed`「最小正間距＝一根」：**被推翻**，且我連方向都判反（見 C2）。
- `assumed`「負對照與主篩選同義」：**被推翻**（見 C3）。
- `assumed`「真實規模不會變成小時級」：**部分被推翻**——乾淨資料成立，NaN 路徑不成立（見 C4）。
- `assumed`「instance 狀態不會跨 run 殘留」：**被推翻**，且升為 P0（見 C1）。

**Verdict**: 需修補後合併——七項修補完成後可合併並進第三批（Task 3.8／3.9）。
修補已落地：`--phase 3b` **8/8 RED**、對照組綠、UNCOVERED=0；`gate 3b` PASS
（含新併入之 benchmark 關卡）；`--phase 2`／`3a` 未回歸；G-6 survivor golden 未漂移。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01
**斷言**: _binary_label_window_bars 是跨 run 的 instance state，且只在 split 分支寫入；無切分 binary 會沿用前值或 0，0 會關掉依賴保護。**碼證**: target ic_filter_orchestrator.py:1065,1211-1215,4764-4767,2387-2410；最小修法是在每次 analyze/refilter 建立 run-local 尺度，無法取得時 fail-closed。**來源摘要**: source_digest: 47eb852bf0aa; TODO:0921c74ab73a
## CODEX-R1-P1-01
**斷言**: 事件最小正間距不是特徵 K 線長度；目標碼在事件每 3 根、W=12 時推 bar=10,800,000、L=12,n_blocks=2，真值 bar=3,600,000、L=4,n_blocks=5，會過度綁定並假性 unavailable。**碼證**: target ic_filter_orchestrator.py:4764-4767,4844-4855；target probe 實得上述 stdout；最小修法由 metadata timeframe_seconds/feature timeframe 注入 authoritative bar，未知即 fail-closed。**來源摘要**: source_digest: 47eb852bf0aa
## CODEX-R1-P1-02
**斷言**: stage3 對 sparse filtered_features 套用 full-frame split_context test_mask，selection scope 不成立且會直接中斷。**碼證**: target ic_filter_orchestrator.py:3651-3656,3759-3767；target probe 實得 IndexError: Boolean index has wrong length: 10 instead of 3；最小修法以 test_plan.row_index/timestamp intersection 產生唯一 selection index，stage3/stage5 共用。**來源摘要**: source_digest: 47eb852bf0aa
## CODEX-R1-P1-03
**斷言**: 負對照不是同一套 selector：target 永遠重算 BH q（未接 fdr_enabled），主路徑可讀 raw p；且 observed 是 oracle 後 3 個、null 是 full-table 16 個。**碼證**: target ic_filter_orchestrator.py:4736-4745,4783-4828,4993-4996；target probe 實得 passed_before_oracle=16 survivors_after_oracle=3、n_observed=3、q95=16；最小修法抽共用 binary threshold selector，observed/null 使用同 universe、同 stage。**來源摘要**: source_digest: 47eb852bf0aa
## CODEX-R1-P1-04
**斷言**: 39,373×165 之 10% NaN 全表 MW 約 4.79s/次，target 固定 50 次即約 239s，違反 TODO 每道小於 120s；clean 約 0.56×50=28s 不代表通過。**碼證**: target loop ic_filter_orchestrator.py:4806-4828、negative_control_n=50；probe 20260910-probe-oracle-bench.py stdout 含 c 239s；最小修法是可證明的批次/快取設計，或有上限且揭露 n_planned/n_effective/budget 的降階，不得靜默砍 N。**來源摘要**: source_digest: 47eb852bf0aa; TODO:0921c74ab73a
## CODEX-R1-P1-05
**斷言**: binary downstream 仍用報酬統計：redundancy_scores 對 imported binary 取 ic_mean，且 stage6b 未標 diagnostic；service/event-rule 也未交付 primary/effect disclosure，可能移除有效 binary feature 或誤讀報告。**碼證**: target ic_filter_orchestrator.py:3476-3488,5202-5272、api/services/ic_analysis_service.py:275-306、event_label_mode.py:156-180；probe 得 scores={binary_strong:0.01,binary_weak:0.9}；最小修法 binary redundancy 用 abs(rank_biserial)，stage6b 固定 diagnostic/no removal，並同步契約揭露。**來源摘要**: source_digest: 47eb852bf0aa; TODO:0921c74ab73a; API:067a48dd6645
## CODEX-R1-P2-01
**斷言**: stage5 第三道 guard 沒驗 owner,ts,label：owners 建了但未使用，只比 ts,label；summary row 對不上也 continue，會變成 silent binary_unavailable 而非接線錯誤。**碼證**: target ic_filter_orchestrator.py:4902-4912,4921-4935,4980-4983；owner probe 在非預期 event IDs 下仍 merge_returned=True,binary_status=ok；最小修法以 owner map 驗完整 triple，欄名集合 mismatch 直接 raise。**來源摘要**: source_digest: 47eb852bf0aa; contract:de3ee1a17b87
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

