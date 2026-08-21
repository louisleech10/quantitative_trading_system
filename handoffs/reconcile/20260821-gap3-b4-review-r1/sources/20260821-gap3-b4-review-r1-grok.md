# GAP-3 B4 review R1 — grok

task-id: 20260821-GAP3-B4-REVIEW-R1
family: grok
brief-kind: review
brief: handoffs/20260821-gap3-b4-review-brief.md
diff: `git diff 3b1350df..HEAD -- momentum/ tests/`（03228628 B4.1／e9e0257c B4.2）

## Verdict：需修補後再進 B5／stamp（無 P0；有 P1＝PBO 觀測軸未按 entry 時間排序，CSCV 時序語意壞；P2＝型別閘可語義洗白）

### 必答（逐條）

1. **逐 Task 對 TODO 驗收**：B4.1／B4.2 之驗證／邊界／不可做與實作＋測試對得上。白名單成立：`git diff --stat 3b1350df..HEAD -- momentum/ tests/`＝只新增 `pattern_bridge.py`＋`candidate_ledger.py`＋兩測試（+893）；`pattern_extractor.py`／`strategy_validation/*`／`xgboost_batch_service` diff 空。`sample_weight` 未接 `fit`；split 缺／train 空／全 test ⇒ `PatternSplitRequiredError`；ledger 空 ⇒ unavailable；AUC 具名閘有測。
2. **B4.1 train/test 隔離**：`XGBClassifier.fit` 只見 train 列（spy 鎖 n／index／無 sample_weight）。第二路徑 `PatternExtractor.extract_decision_rules(X_all,y_all,split=train_plan,oot_split=test_plan)` 內部以 `split.row_index` 切 train 抽規則；`oot_lift` 只寫入規則欄、**不**回饋 `_simplify_rules`／排序（仍用 train `confidence*lift`）。粗篩／fit／規則支持度皆 train-only。假設「fit spy 足夠」對 **XGB fit** 成立；對 extractor 路徑需靠讀碼（本輪已讀，未另見 test 洩漏通道）。
3. **J8 粗篩**：`train_n // rows_per_feature` 上限＋train-only `|corr|`；NaN 以 `isfinite` 剔除；平手 `(-score, name)` 決定性。`test_j8_ic_prescreen_train_only` 把 test 段 f59＝label 仍不入選——對「偷看 test 列值」足夠；非「test 標籤反傳」類（本實作無該路徑）。
4. **AR-3**：報告 `common=_common_constraint_block(...)`；test 段真呼叫 B2.2 `binary_discrimination_table(..., manifest=manifest)`（非平行實作）；置亂 oracle 沿用（`auc_in_band`）。
5. **B4.2 W8 entry×exit**：entry＝收據 `entry_price_source_bar_open_ms`＋`entry_price_source_field`；exit＝`label_end_ms`→bar `close`；五種 semantic 真實 kline 手算 exact（`abs=1e-15`）；semantic／`label_definition` 與 events 不一致拒；缺收據拒（禁自推）。未見自行用 `window` 推時點之路徑。
6. **ledger／N**：`record_candidate` 只經 `append_trial_attempt`；檔名由 `ledger.ledger_path` 推導；provenance sidecar `<ledger>.provenance.jsonl`（閉集 schema 有 extra-key 拒）；`n_trials_source="ledger"`；DSR `variance_source=ledger_cross_trial`＋`source_artifact_hash ∈ artifact_hashes`；`metric_value`＝`compute_sharpe` per-period（本檔不重算公式）。
7. **型別閘（K6/C7）**：具名 `metric_kind∈{auc,pr_auc,...}` 與 `Series.name` 禁名單 ⇒ `MetricTypeError`（ASSERT 綠）。**可繞**：`metric_kind="return_series"`（預設）＋AUC／分數數列且 `name` 不在禁名單 → `_assert_return_series` 放行（見 P2）。
8. **PBO 觀測軸**：設計＝聯集＋未出手 0（對 CSCV 對齊候選可辯）；`s_blocks` 預設 8、`n_obs < s_blocks` ⇒ unavailable；universe guard 有測。**缺陷**：實作 `union = sorted(event_ids)`＝**字串序**，與 docstring「依 entry 時間排序」矛盾；CSCV 塊切在非時間序軸上（見 P1）。零填不觸發 `compute_sharpe` 位元全等守衛（僅全 0 退化）——assumed 成立，但稀疏零會稀釋 SR（設計取捨，非本 finding）。
9. **MinBTL**：`t_years`＝champion `span_years`（entry 最早→label_end 最晚／`_MS_PER_YEAR`）；`target_sharpe` 呼叫參數；不足 ⇒ `eligible=False`＋`loud=return_series_shorter_than_min_btl`。未見為 AUC 自創 MinBTL 或以 bar 數冒充年數。
10. **可進 B5？** **不可直接進**——P1 須先修（PBO 時序軸）；P2 建議同批補強型別閘。B4.1 與 W8／ledger／MinBTL／白名單本輪無 BLOCKING。

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 證據 |
|------|------|------|
| fact-verified: B4 Gate 22＋auc ASSERT＋event_samples 217＋GAP-1 SV＋golden | **本輪複驗前四項成立；golden 引主委 receipt（brief 禁並行重跑）** | 本輪：Gate 22 passed rc=0；`-k auc_fed` 1 passed；event_samples 217 passed；`tests/momentum/Analysis/strategy_validation` 272 passed；receipt `20260821T150000Z-gap3-b4-gate.log` golden CHECK PASS sha 163c4ce… |
| assumed: SplitPlan `row_id`＋universe hash＋`time_bounds=(min_pos,max_pos)` 即足 | **成立（攻擊不推翻）** | `PatternExtractor` 只用 `split_label`／`row_index`／`canonical_split_plan_hash`（hash **不含** `time_bounds`）；切片 `X.iloc[train_idx]` 與 bridge 的 `pos` 對齊 |
| assumed: `_apply_conditions` 私有＝同語意非平行實作 | **成立** | 同模組方法；`extract_decision_rules` 算 `oot_lift` 與 bridge test 命中統計走同一實作 |
| assumed: `ledger_path: LedgerKey`＝GAP-1 身分、不自開帳本檔 | **成立** | `LedgerKey(research_session_id, dataset_key)` → `append_trial_attempt`／`ledger_path(...).with_suffix(".provenance.jsonl")` |
| assumed: provenance sidecar（不改 GAP-1 契約） | **成立** | `ledger_record_keys` 閉集（extra key⇒invalid）；sidecar 含 rule_digest／seed／input_digest／command／expected |
| assumed: 直建 `PeriodReturns(trade_level, ppy=n/span, annualization_source=resolved)` | **成立** | 無 BacktestResult 殼；公式對齊 `extract_period_returns` 之 trade_level 分支（`n/years`）；`status` 在 `ppy>0 ∧ n≥2` 時 ok |
| assumed: 聯集＋0 不使 Sharpe 誤觸位元全等守衛 | **成立** | 手跑：稀疏非全 0 ⇒ `status=ok`；`zeros(40)` ⇒ `degenerate_returns`；與 `sharpe.py` `ptp==0` 守衛一致 |

## GROK-R1-P1-01

**斷言**: `run_dsr_pbo` 組 PBO `returns_matrix` 時以 `sorted(event_id)` 做觀測軸，並非 docstring／CSCV 所需的 entry 時間序；當 event_id 字串序≠時間序時，CSCV 區塊切割失去時序意義，PBO 數值不可作為過擬合防線。

**碼證**: `candidate_ledger.py` L250 寫「依 entry 時間排序」；L306 `union = sorted({e for ... returns.index})` 為字串排序。手跑反例：時間序 index=`[b_first,a_second,c_third]` → code union=`[a_second,b_first,c_third]`，矩陣列置換且 `matrices_equal=False`。現有測 `_cand` 用 `e{i:03d}`（字串序≡構造序）掩蓋此洞；`assert n_obs==40` 不鎖列序。`RECHECK:` 用反字典序／UUID `event_id` 造兩候選（series 內已按 entry 排），斷言 PBO 軸＝時間序（或修後軸與 `entry_at_ms` 單調）；修前應紅／修後綠。

**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b; tests/momentum/event_samples/test_candidate_ledger.py#a33ef38fd690; momentum/Analysis/strategy_validation/pbo.py#35032307622a; docs/GAP3_EVENT_TODO.md#df04bdabf37d; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

正文：[MAJOR] 信心度=High。失敗模式：真實 `event_id`（非零墊序號）下 PBO 仍 `status=ok` 但 IS/OOS 塊不是時間切分 ⇒ 過擬合檢定假綠。修法清單：① `to_return_series` 在 `attrs` 寫入 `entry_at_ms_by_event: Dict[event_id,int]`（或平行 Series）；② `run_dsr_pbo` 聯集軸＝`sorted(union, key=lambda e: (entry_at[e], e))`，缺時間戳 ⇒ fail-closed；③ 新增測試：反時間字串序 event_id，斷言軸單調＋／或 PBO matrix 列＝時間序；④ 同步 docstring／`observation_axis` 字面。不改 GAP-1 `pbo.py` 簽名。

## GROK-R1-P2-01

**斷言**: `_assert_return_series` 只擋 `metric_kind`／`Series.name` 禁名單；`metric_kind="return_series"`（預設）且 `name∉禁名單` 時，可把 AUC／分類分數數列當持有報酬餵進 `run_dsr_pbo`／`record_candidate`（單一 AUC 亦過閘，僅隨後因 n_obs<2 變 DSR unavailable，而非 `MetricTypeError`）。

**碼證**: `candidate_ledger.py` L68–78。本輪探針：`CandidateReturns("a", Series([0.73,0.81,…], name="hold_return"), metric_kind="return_series")` → `_assert_return_series` **ACCEPTED**；`Series([0.73], name="score")` 與 `name="oos_score"` 同樣 ACCEPTED。對照：`metric_kind="auc"`／`name="auc"` 有測拒。`RECHECK:` 同上三探針；修後應於閘層 raise `MetricTypeError`（或等價）而非依賴後段退化。

**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b; tests/momentum/event_samples/test_candidate_ledger.py#a33ef38fd690; docs/GAP3_EVENT_SPEC.md#544c2922ef2e; docs/GAP3_EVENT_TODO.md#df04bdabf37d

正文：[MINOR] 信心度=High（可繞路徑存在）；產品誤用風險 Medium（須手組 `CandidateReturns`）。修法（可機械化，非文件約定）：① `_assert_return_series` 要求 `attrs` 含 `to_return_series` 契約鍵（`t_semantics=="trade_level"`、`entry_semantic`、`label_definition`、`source_artifact_hash` 長度 64、`span_years>0`）；② 加測：`metric_kind=return_series`＋無 attrs／`name="score"`＋類 AUC 值 ⇒ `MetricTypeError`；③ 可選：`record_candidate` 拒絕缺 `to_return_series` 收據鍵之 returns。仍無法防惡意偽造 attrs，但堵住「分數／AUC 當 return series」之疏忽路徑，對齊 K6/C7「機械拒」。

ASSUMPTIONS_VERIFIED: 白名單僅四新檔；fit 只見 train＋extractor oot 不回饋；J8 train-only；AR-3 真復用 tables；W8 五語意 exact；ledger 唯一寫口＋N 從 ledger；MinBTL 用 span_years；SplitPlan／_apply_conditions／LedgerKey／sidecar／PeriodReturns 直建／零填守衛六條 assumed 攻擊後成立；PBO 軸字串序≠時間序（P1）；型別閘可語義洗白（P2）
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` → 22 passed rc=0；`-k auc_fed` → 1 passed rc=0；`tests/momentum/event_samples/ -q` → 217 passed rc=0；`tests/momentum/Analysis/strategy_validation -q` → 272 passed rc=0；golden 本輪未重跑（brief 禁並行），引 `handoffs/run_receipts/20260821T150000Z-gap3-b4-gate.log`；手跑 PBO 軸置換反例＋型別閘三探針＋稀疏／全 0 Sharpe
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；觀察到 PBO 軸序錯誤會改 returns_matrix 列排列，未改產品碼）
OUTPUT: handoffs/20260821-gap3-b4-review-r1-grok.md

STATUS: DONE
