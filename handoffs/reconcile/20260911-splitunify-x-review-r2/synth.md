# Reconcile — 20260911-splitunify-x-review-r2

**來源** 20260911-splitunify-x-review-r2-codex.md, 20260911-splitunify-x-review-r2-composer.md, 20260911-splitunify-x-review-r2-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併——**三家 verdict 一致「不可直接進 B1」**；SPEC 改 v3、TODO 改 v3 後才可進 B1。

主委自產版另存 `handoffs/20260911-splitunify-claude-selfreview-r2.md`（`CLAUDE-R2-*` 4 條）。
本輪三家共 17 條（codex 6／composer 5／grok 6），與主委 4 條合併為 **11 個群集**。

🔴 **先記主委自己被推翻的一條**：`CLAUDE-R2-P1-01` 我斷言「event-study-only 不是退回全樣本」——
**錯了一半**。`tables.py:211-238` 之迴圈確實跑**全 manifest 事件**、無 `split_label=="test"` 過濾
（`COMPOSER-R2-P1-01` 指出）。正確表述是：它**是**全樣本統計，只有 `ci` 與
`formal_pooled_inference_allowed` 兩個旗標被保守降級，**表身數字沒有任何「非 OOS」標籤**。
⇒ 我原本要拿這條去覆核三家的答案，結果是我自己的碼證讀得不夠深。記在這裡，不淡化。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **D1 C-0 仍未閉合：沒有可執行的 universe 供給路徑** | **P0** | CODEX-R2-P0-01 | **採納**。v2 只寫「pipeline 必須接收 boundary＋feature_index」，但**沒寫誰給、怎麼給**。`case_import_service.py:1588-1613` 只有 bars 與切分參數；`SplitPlan` 須由另一端建立（`contracts.py:378-403`）。⇒ v3 須明寫**二選一並定案**：①事件掃描端**永遠**走 event-study-only（本票不新增 universe 供給路徑），②新增 `features_run_id` 參數之跨棧改動（超出本票）。主委裁定採 **①**，理由見下「D1 之裁定」。 |
| **D2 Task 3.3 自相矛盾：既有實作正寫 `n_test=0`** | **P0** | GROK-R2-P0-01（COMPOSER-R2-P1-01 同指） | **採納 grok 之修法①**。`pipeline.py:728-734` 之 `run_event_study_only` 正把 `n_train/n_test/n_purged` 寫成 `0`，與 Task 3.3 之「不得出現這三鍵」＋「沿用既有機制」互斥。且前端 `EventTablesPanel.tsx:352` 今日對 L3 顯示「train 0／test 0／purge 0」——**正是 C-0 要禁的假 OOS 數字**。⇒ v3：**刪除**這三鍵（L3 之 `lookahead_split_blocked` 與新 reason 共用新形狀），附回歸測試「兩 reason 皆 `"n_test" not in summary`」。 |
| **D3 §G G-5 是空殼** | **P0** | COMPOSER-R2-P0-01、CODEX-R2-P1-04、GROK-R2-P1-04（主委補 CLAUDE-R2-P3-04） | **採納，取三家聯集之最嚴版**。四項各自的 oracle 逐條寫進 §G 與 Task 2.3：①row fingerprint＝canonical `(position, feature_ts_ms, symbol, universe_hash)` 之 exact sha256，失敗須指名**首個** mismatch 的 position；②assignments／purged＝由 `feature_index[plan.row_index]` 直接產生之集合，斷言互斥、覆蓋、purge reason 字面，失敗輸出 diff event_id；③answer-window＝逐事件 label 起訖對 source bars **完整覆蓋**，缺 endpoint 或跨界必產 purge＋event_id；④leakage-negative＝注入跨 boundary 之 answer interval，必 reject 或 purge，且 mutation rc=1。 |
| **D4 事件掃描端的 study-only 數字沒有「非 OOS」標籤** | P1 | COMPOSER-R2-P1-01、CODEX-R2-P1-02 | **採納**。`tables.py:166-172` 允許 `split_plan=None`；`:211-238` 跑全 manifest 事件、無 test 過濾；`:251` 只把 `ci` 設 `"unavailable"`。⇒ v3 Task 3.3 增④：`event_forward_return_table` 之 `common` 須含 `estimand_scope="full_sample_not_oos"`（沿用 `tables.py:598-599` 之 `estimand_note` 模式），並由 `test_splitunify_event_study_only.py` 斷言。 |
| **D5 前端不渲染 `capability.split`／`reason`** | P1 | GROK-R2-P1-01、COMPOSER-R2-P1-02、CODEX-R2-P1-02 | **採納**。`EventTablesPanel.tsx:302` 收回應、`:352` 只渲 summary 計數，全文無 `resp.capability`（`grep 'canonical_feature_universe' frontend/` ⇒ 0）。兩條 reason（`split_blocked_unverifiable_lookahead` vs `canonical_feature_universe_unavailable`）使用者無從分辨。⇒ v3 把「事件掃描頁必顯 `capability.split`＋`reason`、`split=="unavailable"` 時**禁再顯示 train/test/purge 計數列**」寫進 Task 3.3，並要求兩 reason 各一條 vitest。 |
| **D6 `holdout_boundary` 之 ms 未定義導出方式** | P1 | GROK-R2-P1-02、CODEX-R2-P1-03 | **採納 grok 之寫死版**。`train_end_ms = as_ms(feature_index[train_rows[-1]])`（空 ⇒ `None`）、`test_start_ms = as_ms(feature_index[test_rows[0]])`（空 ⇒ `None`）；**ms 僅供揭露與 hash，禁回流做 ∈ 判定**；驗證加 `assert ms == derived_from_rows`；`M-SU-11` 由「不呼叫既有兩支」擴為「rows 與 ms 同源」。codex 之反例（`test_start_ms=feature_index[split_point]` 略過 purge 仍能過 `-k same_source`）即現行判準的漏洞。 |
| **D7 🔴 C-4 引用的 normalizer 拒收我允許的輸入** | P1 | CODEX-R2-P1-03 | **採納**。C-4 寫「`event_index`：int64 ms 或 DatetimeIndex」並要求復用 `_normalize_ic_time_index`，但該函式 `ic_filter_orchestrator.py:269-271` **明文 raise**「looks like milliseconds, expected epoch seconds」。⇒ 介面不可執行。v3 修法：投影內部一律先把 ms 除以 1000 或直接以 `pd.to_datetime(unit="ms")` 物化後再比對 `asi8`，**不呼叫** `_normalize_ic_time_index`（它是「秒」語意的 normalizer）；並在 C-4 明寫「本票之時鐘一律 epoch **毫秒**，與 IC orchestrator 之秒語意 normalizer 不同源，不得混用」。主委實跑複驗：`sed -n '259,277p' momentum/Analysis/ic_filter_orchestrator.py` 逐行確認 codex 所述屬實。 |
| **D8 C-5 要求 raise 的欄位不在投影簽名上** | P1 | CODEX-R2-P1-03 | **採納**。C-5 要求「`EventSplitConfig.embargo_ms`／`embargo_ms_by_symbol` 須為 `None` 否則 raise」、Task 2.2 要求 `build_time_clusters(manifest, bucket_ms)`，但 C-4 之投影簽名**沒有** config 也沒有 `bucket_ms`（`types.py:63-83`）。⇒ v3 修法：簽名補 `bucket_ms: Optional[int] = None`；`EventSplitConfig` 之檢查**移到呼叫端**（Task 3.1 接線處）而非投影內，並在 C-5 明寫該檢查的落點。 |
| **D9 既有紅清單之維護協議缺失** | P1 | GROK-R2-P1-03、COMPOSER-R2-P1-03、CODEX-R2-P1-05（主委補 CLAUDE-R2-P2-03） | **採納，四方一致**。Task 3.1 驗收 (B) 由「集合相等」改為**方向性**：實際 FAILED ⊆ 清單（**只准變短**）為綠、變長為紅。變短時須同一 PR 更新 `analysis_known_failures.nodeids` 與 receipt，commit 訊息標 `splitunify-baseline-sync` 並具名哪一條變綠。另採 codex 兩點：①凍結管線須捕獲 pytest **自己的** rc（`set -o pipefail` 或 `PIPESTATUS`），否則 collection failure 會偽裝成空基準；②「空清單合法」與 `test -s` 互斥 ⇒ 改為「清單可為空，但 receipt 必須存在且其 rc 已捕獲」。 |
| **D10 SPEC↔TODO 不一致：呼叫點釘 0 只寫在 TODO** | P2 | COMPOSER-R2-P2-01 | **採納**。SPEC Task 3.1 驗收 (A)(B)(C) 無此項，TODO 有。⇒ v3 SPEC 補 (D)：釘選測試斷言生產路徑對 `split_events` 呼叫次數 `== 0`，與 TODO 對齊。 |
| **D11 `single_symbol` 恆亮須聲明為預期** | P2 | GROK-R2-P2-05、CODEX-R2-P2-06（主委補 CLAUDE-R2-P2-02） | **採納**。三方一致判為**正確且應保留的探索性揭露**，非誤導；效果保守（`formal_pooled_inference_allowed` 恆 False）。⇒ v3 Task 2.2 補一句：「fail-closed 期間 `single_symbol` 恆亮為預期；不得為讓 `formal_pooled_inference_allowed=True` 而清空 `degraded`。」 |

### D1 之裁定（主委，依離線授權以委員共識收斂）

codex 說得對：v2 的 C-0 只是把 C10 **重述**成一條約束，沒有閉合。二選一裡——

- 方案②（新增 `features_run_id` 跨棧參數）會把請求模型、前端、契約、UAT 一起拖進本票，
  且 `EventImportService` 目前完全不碰 FF run；這是 R1 就評估過「超出本票範圍」的那條。
- 方案①（事件掃描端**永遠**走 event-study-only）之代價已被 D4／D5 量清楚：
  表身仍是全樣本，但會被明確標成 `full_sample_not_oos`，畫面不再顯示 train/test/purge 計數。
  使用者因此只會在 **IC 分析報告**看到「驗證段」三個字——這正是本票的目標。

⇒ **採方案①**。C-0 決議②之措辭由「pipeline 必須接收 boundary／feature universe」
改為「pipeline **接受**（選填）canonical boundary＋feature_index；IC 路徑會傳，
事件掃描路徑本票不傳，故恆走 event-study-only」，並把
「本票不新增 universe 供給路徑」寫成**具名殘留** `R-5（needs-research）`。

### 三家 verdict（逐字要點）

- codex：「C-0/C10 的 production 落點、study-only 誠實呈現、projection/golden/baseline
  可執行性仍有 P0/P1 缺口；先修 SPEC/TODO 與驗收契約，再開始 B1。」
- composer：「需修補後派工。」
- grok：「需修補後派工（不可直接進 B1）。」

### 批次調整（codex Q8）

codex 建議 B2 拆為 B2a（Task 2.1）→ B2b（Task 2.2）→ B2c（Task 2.3），各自 gate／review。
**採納**——v2 把 B2 標為「大」卻只有批末一個 gate，等於把三個可獨立證偽的產出綁成一次審查。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P0-01
**斷言**: Q1／C10：v2 雖要求 pipeline 接收 canonical boundary＋feature_index，卻沒有把現行只拿 bars 的 production caller 接到 SplitPlan pair／event_index 的可執行 adapter；除非另增未寫的 universe 供給路徑，C-0 仍未閉合。
**碼證**: SPEC:61-76、130-137、Task2.1:287-302、Task3.1:360-375；`case_import_service.py:1588-1613` 只有 bars/切分參數，`pipeline.py:653-657` 無 feature_config 即回 None，`SplitPlan` 欄位在 `contracts.py:378-403` 仍須由另一端建立。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b, docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90, api/services/case_import_service.py#f06b46eb685d, momentum/Analysis/event_samples/pipeline.py#f78eae8df0f6
## CODEX-R2-P1-02
**斷言**: Q1／Q4：若按 C-0／Task3.3 走 event-study-only，`event_forward_return_table` 會計算全 manifest 事件而非 OOS test；`tables.py:305` 實為需 plan 的 binary 表，pipeline 反而回 not_computed。後端 lookahead reason 可區分，但前端缺 status 時預設 ok 且不讀 `resp.capability`，v2 未足夠防止把 study-only 數值誤讀為 OOS。
**碼證**: `pipeline.py:540-546,708-740`、`tables.py:157-177,210-252,279`；`EventTablesPanel.tsx:33-38,63-110,346-365`；既有 lookahead 字面在 `lookahead_gate.py:26-30`，SPEC:73-76、Task3.3:412-432 只定分派/reason，未定表格與畫面呈現。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b, momentum/Analysis/event_samples/tables.py#b80c15cf206d, momentum/Analysis/event_samples/pipeline.py#f78eae8df0f6, frontend/src/components/ic-analysis/EventTablesPanel.tsx#979163953945
## CODEX-R2-P1-03
**斷言**: Q2：ms 邊界若只是對既有 row index 在同一個 normalized feature index 上做精確索引，不是第二份 split arithmetic；但 M-SU-11 只擋「不呼叫兩支 helper」且同源自證，擋不住 train_end/test_start 漂移。另 C-4 允許 int64 ms，引用的 `_normalize_ic_time_index` 卻拒絕 ms；C-5 要求 bucket_ms／embargo raise，而投影簽名沒有 config/bucket 參數，介面不可執行。
**碼證**: `split_preview.py:19-46,63-79` 兩支只回 row/point；SPEC:126-155、163-174、Task2.1:289-306、Task2.2:310-338；`EventSplitConfig` 的 bucket/embargo 在 `types.py:63-83`，cluster 取值在 `event_split.py:126-157`，normalizer 在 `ic_filter_orchestrator.py:259-277`。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b, docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90, momentum/core/split_preview.py#6b6a1d95c5cc, momentum/Analysis/event_samples/types.py#8ba12e1b5204, momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7
## CODEX-R2-P1-04
**斷言**: Q6：G-5 只有名稱，需補可偽證 oracle：①row fingerprint＝canonical `(position, feature_ts_ms, symbol, universe_hash)` 的 exact SHA，首個 row mismatch；②assignments/purged＝直接由 `feature_index[train/test_plan.row_index]` 產生之集合，斷言互斥、覆蓋、purge reason，輸出 diff event_id；③answer-window＝逐事件 label 起訖對 source bars 完整覆蓋，缺 endpoint 或跨界必產 purge＋event_id；④leakage-negative＝注入跨 boundary answer interval／future train feature，必 reject 或 purge、mutation rc=1。
**碼證**: SPEC:G-5:218-221、TODO:178-199 只列四項與 G-3b 集合 oracle，沒有 fingerprint 序列化、answer-window bar predicate、負例 fixture、失敗輸出或命令；故目前不可重現也不可判定漏洩。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b, docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90
## CODEX-R2-P1-05
**斷言**: Q5：B1→B3 的 FAILED nodeid 集合相等是應保留的 fail-closed 特性，不是施工阻塞；但必須規定「集合變動即停、以新 pytest receipt 重凍、只移除已變綠 nodeid」。目前產生管線未保留 pytest rc，且 TODO:109 的合法空清單與 :111-113 的 `test -s` 互斥，collection failure 可能偽裝空基準、乾淨基準又無法通過。
**碼證**: TODO:101-117 的 `pytest | tee | awk` 無 pipefail/PIPESTATUS、空清單與 `test -s` 矛盾；SPEC:376-387 只定集合相等與 deselect，未定 rc 捕獲及漂移處置。
**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90, docs/SPLITUNIFY_SPEC.md#84ab732b021b
## CODEX-R2-P2-06
**斷言**: Q3：`n_symbols=1` 時 `_degraded_flags(..., cluster_adjusted=True)` 的 `single_symbol` 是正確且應保留的探索性揭露，不是誤導；Q7：R1 C1–C13 均在 v2 有落點，但 C10 只是被 C-0 重述、未閉合（見 P0-01）；Q8：B2 應拆成 B2a Task2.1 → B2b Task2.2 → B2c Task2.3，各自 gate/review 後才進 B3。
**碼證**: `event_split.py:21-30` 與 `tests/momentum/event_samples/test_tables.py:42-60` 支持 single_symbol 語意；R1 synth:19-31 與 brief:24-42 逐列對應 C1-C13；TODO:39-49／SPEC:223-232 雖標 B2「大」仍只有批末 gate。
**來源摘要**: momentum/Analysis/event_samples/event_split.py#fde5a520c319, handoffs/reconcile/20260911-splitunify-x-review-r1/synth.md#c3a4bff5573b, handoffs/20260911-SPLITUNIFY-SPECTODO-REVIEW-R2-BRIEF.md#1b8db7f6ca56, docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90
## COMPOSER-R2-P0-01

**斷言**: §G G-5「containment 四項 golden」與 Task 2.3 實作要點僅列四個名稱，未給任一項的獨立 oracle、fixture 來源或可執行比對命令，屬 §2 獵空殼之 BLOCKING 空殼；C-1 附帶約束②要求 §G golden 四項，但 G-5 目前不可證偽。

**碼證**: `docs/SPLITUNIFY_SPEC.md:218-219`（「逐 row test fingerprint、逐 event assignments/purged IDs、answer-window 完整性、leakage negative case」——無算法）；`docs/SPLITUNIFY_SPEC.md:340-355` Task 2.3 要點 4 同樣只複述名稱；`docs/SPLITUNIFY_TODO.md:190-191` 同型。RECHECK: `rg -n 'G-5|test fingerprint|leakage negative' docs/SPLITUNIFY_SPEC.md` → 僅標題級提及，無 `freeze_splitunify_golden.py` 子命令或 pytest nodeid。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[BLOCKING] 信心度=High。Agent 實作 Task 2.3 時只能自創 oracle，與 C-1「containment 未證明」目標背離。修法（逐項補進 Task 2.3，示例）：  
① **row test fingerprint**：`sha256(json.dumps(sorted(feature_index[test_plan.row_index].asi8//10**6)))` 與 IC orchestrator 同批輸出逐值相等；  
② **event assignments/purged IDs**：`set(assignments.event_id)`／`set(purged.event_id)` 與 G-3b oracle 集合相等（整數集合 `==`）；  
③ **answer-window 完整性**：對每個 test 事件 assert `label_end_ms <= train_end_ms` 或 purged reason=`interval_crosses_split_boundary`（沿用 `event_split.py:114-115` 語意）；  
④ **leakage negative case**：合成 fixture 一筆 train 事件其 `label_end_ms` 跨入 test 區 ⇒ 必進 `purged`，不得留在 `assignments`。每項須有對應 `tests/momentum/Analysis/test_splitunify_golden.py -k <name>` 或 freeze 腳本子模式。

---

## COMPOSER-R2-P1-01

**斷言**: v2 雖在 C-0／Task 3.3 禁止事件掃描端宣稱 OOS，但未規定 `event_forward_return_table` 在 `split_plan=None`（event-study-only）時的全樣本語意與必要揭露，與 brief 所質疑之「全樣本被誤讀為 OOS」風險仍成立。

**碼證**: `momentum/Analysis/event_samples/tables.py:166-172`（`split_plan=None` 合法）；`:211-238` 迴圈**全 manifest 事件**、無 `split_label=="test"` 過濾；`:251` 僅 `ci="unavailable"`；對照 `binary_discrimination_table:305` 只取 test。`pipeline.py:728-733` `run_event_study_only` 仍寫 `n_test:0`（v2 Task 3.3 要求移除這些鍵）。`case_import_service.py:1614-1615` 現況仍走 `run_with_params`（有切分）而非 Task 3.3 目標路徑。RECHECK: `rg -n 'event_forward_return|oos_only|formal_pooled' docs/SPLITUNIFY_SPEC.md` → 無 Task 3.3 表級契約。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[MAJOR] 信心度=High。失敗模式：B3 後 summary 無 `n_test`，但 `tables.event_forward_return_table` 仍展示全批報酬均值，前端無「非 OOS」標籤（`test_gap3_split_blocked.py:101-107` 只驗「表能產出」）。修法：Task 3.3 增④——`event_forward_return_table` 須含 `common.estimand_scope="full_sample_not_oos"`（或 `capability.split=="unavailable"` 鏡像）；`test_splitunify_event_study_only.py` 斷言該欄位；可選在表 title 沿用 `tables.py:598-599` 之 `estimand_note` 模式。

---

## COMPOSER-R2-P1-02

**斷言**: Task 3.3 新增 `canonical_feature_universe_unavailable` 與既有 `lookahead_split_blocked`（`case_import_service.py:1591-1594`）並存，但 v2 未要求前端對兩種 `capability.reason` 做可區分揭露，實作端只能共用「split unavailable」泛稱。

**碼證**: `case_import_service.py:1618-1620` capability 形態；`pipeline.py:204-208` `split_blocked_capability_reason()` 與 Task 3.3 新 reason 字面不同；`frontend/src/lib/types.ts:3189-3190` `reason?: string` 無枚舉；Task 4.1 驗收（SPEC `:446-448`）未含事件掃描頁 reason 分支；`EventBatchDisclosurePanel.tsx:668-670` 僅顯示 `scanResult.reason` 原文。RECHECK: `rg 'canonical_feature_universe' frontend/` → 0。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

[MAJOR] 信心度=Medium。失敗模式：使用者見「切分不可用」無法分辨「深度宣告封鎖」vs「缺 feature universe（本票新路徑）」——支援與 UAT 難以對症。修法：Task 3.3 增前端驗收——`vitest` 對兩種 reason mock payload 斷言不同文案；或 D-002 增 UX 對照表映射 `split_unify.json` fail_closed_reasons。

---

## COMPOSER-R2-P1-03

**斷言**: Task 1.3 之「B1 凍結、B3 集合相等」在 B2 期間若既有紅被 `REDSWEEP` 修復會必然紅 gate，但 v2 未給「誰、何時、如何」更新 nodeid 清單的操作判準，會卡住施工而非僅提醒。

**碼證**: `docs/SPLITUNIFY_SPEC.md:279-280` 邊界②「變綠必移出」；Task 3.1 驗收 B（`:377-387`）集合不等即 rc=1；`HANDOFF.md:45-48` 建議 `REDSWEEP` 另票。無「B2 期間紅清單變動」流程。RECHECK: `rg 'REDSWEEP|主動移出' docs/SPLITUNIFY_TODO.md`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

[MAJOR] 信心度=High。這是**刻意的 fail-closed**（優於聚合假綠），但缺 procedure = Agent 不知該停批還是順手改清單。修法：Task 1.3 增「維護協議」——B3 驗收 B 紅時允許同一 PR 更新 `analysis_known_failures.nodeids`（只准變短）+ `splitunify-analysis-baseline.stdout`；B2 內 `REDSWEEP` 修紅須在 commit message 標 `splitunify-baseline-sync` 並重跑 Task 1.3 命令。

---

## COMPOSER-R2-P2-01

**斷言**: R1 C7 要求生產路徑對 `split_events` 呼叫次數釘 0，TODO Task 3.1 驗收已寫「釘選測試」，但 SPEC Task 3.1 驗收三條命令未包含該斷言，SPEC↔TODO 不一致會讓實作端只跟 SPEC 而漏釘。

**碼證**: `docs/SPLITUNIFY_TODO.md:225`「另加：釘選測試斷言…呼叫次數 == 0」；`docs/SPLITUNIFY_SPEC.md:376-389` 驗收 (A)(B)(C) 無此項；R1 synth C7 採納「測試釘呼叫點＝0」。RECHECK: `diff` 兩檔 Task 3.1 驗收段。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[MINOR] 信心度=High。修法：SPEC Task 3.1 驗收增 (D) `pytest -k split_events_production_call_count`（或 spy 測試 nodeid）rc=0，與 TODO 對齊。

---

## GROK-R2-P0-01

**斷言**: Task 3.3 同時要求「沿用既有 `run_event_study_only`」與「`summary` 不得出現 `n_train`／`n_test`／`n_purged`」，但既有實作正把這三鍵寫成 `0`——兩條約束互斥，Agent 無法同時滿足。

**碼證**: `momentum/Analysis/event_samples/pipeline.py:728-734`（`summary.update({"n_train": 0, "n_test": 0, "n_purged": 0, ...})`）；SPEC／TODO Task 3.3 實作要點 2「`summary` 不得出現 `n_train`／`n_test`／`n_purged`」＋要點 3「沿用既有機制…不新造」＋驗證 `assert "n_test" not in summary`；C-0 決議③亦寫「沿用既有機制」。RECHECK：`sed -n '728,734p' momentum/Analysis/event_samples/pipeline.py`；對照 TODO Task 3.3 驗證段。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

[BLOCKING] 信心度=High。會怎麼失敗：實作端 (A) 原樣沿用 ⇒ 驗收 `not in summary` 恆紅；或 (B) 刪三鍵 ⇒ 改變既有 L3（`lookahead_split_blocked`）路徑之 summary 形狀，卻被「不新造／沿用」文案擋嘴，且未規定是否連 L3 一併改。前端 `EventTablesPanel.tsx:352` 今日對 L3 顯示「train 0／test 0／purge 0」——正是 C-0 要禁的假 OOS 數字。  
**修法**：在 Task 3.3（與 C-0）明示三選一並寫進驗證——① 修改 `run_event_study_only` **刪除**三鍵（L3 與新 reason 共用新形狀；附回歸測試：兩 reason 皆 `"n_test" not in summary`）；② 保留三鍵但改為 `null` 且前端不得當計數渲染（較弱，不推薦）；③ 新 reason 走專用 summary 形狀、L3 暫留 0 並登記 §N 殘留。推薦①。同步要求事件掃描 UI 顯示 `capability.reason`（見 P1-01）。

---

## GROK-R2-P1-01

**斷言**: v2 宣稱「前端事件掃描頁只讀 `capability`、兩條 unavailable reason 並存即可區分」，但事件 analyze 的 UI（`EventTablesPanel`）從不渲染 `capability.split`／`reason`；Task 4.1 只覆蓋 IC 報告 metadata，擋不住事件掃描端混淆。

**碼證**: `frontend/src/lib/types.ts:3189-3190`（型別有 reason）；`EventTablesPanel.tsx:302` 收 `analyzeEventImport` 回應、`:352` 只渲 summary 計數、全文無 `resp.capability`；既有 reason 字面 `split_blocked_unverifiable_lookahead` vs 新 `canonical_feature_universe_unavailable`；Task 4.1 修改檔＝`ic_filter_orchestrator.py`＋`frontend/.../ic-analysis/`（disclosure），無事件 analyze 面板。RECHECK：`grep -n capability frontend/src/components/ic-analysis/EventTablesPanel.tsx`（僅 table-level `capability_status`）。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[MAJOR] 信心度=High。會怎麼失敗：Task 3.3 後端測過 reason 字面，使用者畫面仍無法分辨「深度不可證」vs「無 feature universe」；若再疊 P0-01 的 `n_test=0`，更像「切了但測試段為空」。  
**修法**：Task 3.3 或 4.x 增「事件掃描頁必顯 `capability.split`＋`reason`（兩 reason 各一條 vitest）」；`EventTablesPanel` 在 `split==unavailable` 時改標「未執行切分／原因＝…」，禁再顯示 train/test/purge 計數列。

---

## GROK-R2-P1-02

**斷言**: Task 2.1 的 `holdout_boundary` 回傳 `train_end_ms`／`test_start_ms` 未定義由 row index 如何導出；`M-SU-11` 只驗證「呼叫既有兩支／row 逐值相同」，擋不住 ms 第二套算術。

**碼證**: TODO／SPEC Task 2.1 簽名與驗證（row `np.array_equal`＋年份 ∈[2015,2035]）；`split_preview.py:19-46` 既有兩支無 ms；`M-SU-11`「不呼叫既有兩支」；對照 orchestrator `_time_bounds_for_rows`（`ic_filter_orchestrator.py:553-558`）已有「由 rows＋index 物化」先例卻未被 Task 2.1 引用為唯一公式。RECHECK：假設 rows 正確但 `test_start_ms=feature_index[split_point]`（略過 purge）⇒ `-k same_source` 仍綠。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

[MAJOR] 信心度=High。會怎麼失敗：接線端若誤用 ms 做成員判定（違反 C-4 集合語意）或當 boundary_hash 輸入，會與 row 集合分歧且 mutation 不紅。  
**修法**：寫死 `train_end_ms = as_ms(feature_index[train_rows[-1]])`（空 train⇒`None`）、`test_start_ms = as_ms(feature_index[test_rows[0]])`（空 test⇒`None`）；ms **僅揭露／hash**，禁止回流做 ∈ 判定；驗證加 `assert ms == derived_from_rows`；`M-SU-11` 擴成 rows＋ms 同源。

---

## GROK-R2-P1-03

**斷言**: Task 1.3 凍結之 known-failure 清單與 Task 3.1 驗證 (B)「集合相等」合起來，會把「B1→B3 期間修好一條既有紅」判成與「本票新增失敗」相同的紅——卡住施工並誘導改驗收。

**碼證**: TODO Task 1.3 邊界②；Task 3.1 驗證 (B)「多或少皆 rc=1」；HANDOFF「既有紅盤點」非本票造成且另立 `REDSWEEP`。RECHECK：清單含 A；B2 期間 A 變綠且未改清單 ⇒ (B) 實際 FAILED ⊂ 清單 ⇒ rc=1。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

[MAJOR] 信心度=High。  
**修法**： (B) 改為實際 FAILED ⊆ 清單（只准變短）；變短必須同步改清單＋commit 具名；變長＝fail。Task 1.3「覆蓋風險：只准變短」與驗收指令對齊。

---

## GROK-R2-P1-04

**斷言**: SPEC §G 之 G-5 四項（row fingerprint／event IDs／answer-window／leakage negative）只有名稱，沒有 oracle 與可證偽命令，Agent 無法實作 Task 2.3 之 G-5，亦無法滿足 C-1 附帶約束②。

**碼證**: SPEC §G G-5 全文僅列舉；對照 G-1（成員集合）、G-2（sha256）、G-3b（獨立 oracle 集合相等）皆有比對方式；consult D1／`CODEX-R1-P1-02` 要求此四項。RECHECK：讀 Task 2.3 要點 4——同樣只列名。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[MAJOR] 信心度=High。RISK-HIT 含 a,d ⇒ §G 不可空殼。  
**修法**：把本檔必答 6 之四列表寫進 §G G-5 與 Task 2.3（含負向植入步驟與期望 reason 字面）。

---

## GROK-R2-P2-05

**斷言**: 投影路徑在多 symbol fail-closed 期間 `summary.degraded` 之 `single_symbol` 恆亮；SPEC／TODO 未聲明此為預期，實作端可能誤「修正」而放寬 formal pooled 閘。

**碼證**: `event_split.py:21-30`；Task 3.2 多 symbol⇒raise ⇒ 存活路徑 `n_symbols==1`；`tables.py:138`；Task 2.2 要點 6 只要求 12 鍵齊全與 docstring，未寫恆亮預期。RECHECK：`grep -rn single_symbol momentum/Analysis/event_samples`。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[MINOR] 信心度=High。效果保守（`formal_pooled_inference_allowed` 恆 False）⇒ 非行為 bug。  
**修法**：Task 2.2 補一句「fail-closed 期間 `single_symbol` 恆亮為預期；不得為讓 `formal_pooled_inference_allowed=True` 而清空 degraded」。

---

