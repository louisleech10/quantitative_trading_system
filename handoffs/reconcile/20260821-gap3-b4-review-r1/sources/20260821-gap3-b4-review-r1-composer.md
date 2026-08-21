# GAP-3 B4 review R1（COMPOSER）

TASK_ID: 20260821-GAP3-B4-REVIEW-R1  
FAMILY: COMPOSER  
SCOPE: brief 指定 B4.1/B4.2 實作／測試／diff；review-only，未改程式碼。

## Verdict：需修補後派工（P1 型別閘補強後可進 B5；無 P0）

B4 Gate 22 條＋ASSERT auc 拒＋event_samples 全套 217 本輪複驗 rc=0；白名單 `git diff 3b1350df..HEAD -- momentum/ tests/` 僅新增 `pattern_bridge.py`／`candidate_ledger.py`＋兩測試檔（`pattern_extractor`／`xgboost_batch_service`／`strategy_validation/*` 零 diff）。B4.1 train/test 隔離、J8 train-only 粗篩、AR-3 復用 `tables.py`、B4.2 W8 五語意真實 kline 手算、ledger 唯讀消費 GAP-1、`n_trials` 只從 ledger、universe guard 實測 `universe_provenance_unverifiable` 均成立。**一項 P1**：`metric_kind="return_series"` 可繞過 K6/C7 機械閘餵入 DSR 並得 `status=ok`（見 COMPOSER-R1-P1-01）。**一項 P2**：PBO 觀測軸以 `event_id` 字串排序而非 entry 時間（見 COMPOSER-R1-P2-02）。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 摘要 |
|------|------|------|
| `SplitPlan(index_kind=row_id, base_universe_hash, time_bounds)` 建構足夠 | **成立** | `PatternExtractor.extract_decision_rules` 只用 `split.row_index`／`split_label`／`canonical_split_plan_hash`（`pattern_extractor.py:128-142`）；`time_bounds` 為位置 min/max，不參與規則提取。 |
| test 命中統計復用 `_apply_conditions` 非平行實作 | **成立** | `pattern_bridge.py:189` 同實例 `extractor._apply_conditions(X_test, …)`；與規則提取樹內條件語意同源。 |
| `ledger_path`＝`LedgerKey(research_session_id, dataset_key)` | **成立** | `candidate_ledger.py:48-52`；`record_candidate` 只呼叫 `_ledger.append_trial_attempt`，檔名 `_ledger.ledger_path(…)` 推導。 |
| provenance sidecar 不改 GAP-1 schema | **成立** | `candidate_ledger.py:206-217` 寫 `<ledger>.provenance.jsonl`；ledger record 閉集欄位不變。 |
| `PeriodReturns` 直建（不經 BacktestResult 殼） | **成立** | `_period_returns`（`candidate_ledger.py:225-235`）直填 `t_semantics=trade_level`、`annualization_source=resolved`。 |
| 聯集＋未出手 0 不使 Sharpe 全零退化 | **成立（本輪未攻出退化）** | `compute_sharpe` 全等守衛（`sharpe.py:88-93`）；聯集軸含 0 與非 0 混合時 std>0。 |

---

## COMPOSER-R1-P1-01

**斷言**: K6/C7 型別閘可被 `metric_kind="return_series"`（預設）＋分類指標數值（如 `[0.9, 0.85, 0.72]`）繞過——`run_dsr_pbo`／`record_candidate` 不拋 `MetricTypeError`，且 DSR 可回 `status=ok`、數值語意錯誤（本輪探針 `sr_obs_per_period≈8.86`、`value≈0.999`）。

**碼證**: `_assert_return_series`（`candidate_ledger.py:68-78`）只查 `metric_kind`／`Series.name`∈禁集／有限值，**不**查語意或最小交易數；`test_candidate_ledger.py:134-150` 未覆蓋 disguise 路徑。本輪探針 `venv/bin/python`（inline）→ `CandidateReturns("a", Series([0.9,0.85,0.72], name="hold_return"))` + `span_years=2.0` attrs ⇒ `run_dsr_pbo` **無** `MetricTypeError`，`dsr.status=ok`。對照：同檔 `metric_kind="auc"` 與 `Series.rename("auc")` 皆 `MetricTypeError`（測試已蓋）。

**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b；docs/GAP3_EVENT_TODO.md#df04bdabf37d

[MAJOR] 信心度=High。失敗模式：呼叫方將 AUC/PR 分數誤標或惡意標為 `return_series` 仍可進 ledger＋DSR，違反 TODO B4.2「AUC…機械拒」與 brief 必答 7；單點 AUC（n=1）下游 `annualization_unresolved` 但 **ledger 仍寫入** `metric_valid=False` 行，污染帳本。

**修法**（逐條對碼）:
1. `_assert_return_series` 增機械規則：`len(returns) >= 2`（per-trade series 最小語意）；可選 `returns.name == "hold_return"` 或 attrs 必含 `t_semantics=trade_level`。
2. 可選值域啟發：若全有限且 `max(abs(r)) <= 1` 且 `min(r) >= 0` 且 `std < 0.5` ⇒ `MetricTypeError`（分類分數型態拒絕）；或要求 attrs `source_artifact_hash` 來自 `to_return_series` 簽名 digest。
3. `test_candidate_ledger.py::test_auc_fed_to_dsr_rejected_mechanically` 增 disguise 案例：`metric_kind` 預設 + `[0.9,0.85,0.72]` ⇒ `MetricTypeError`；`record_candidate` 同步拒。

**RECHECK**: `venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k "auc_fed"` rc=0 且 disguise 子測試通過；`ASSERT` 探針 disguise 路徑 rc≠0。

---

## COMPOSER-R1-P2-02

**斷言**: PBO 觀測軸註解寫「依 entry 時間排序」，實作以 `sorted(event_id)` 字串序建 `returns_matrix` 行軸——當 `event_id` 非零填時間序（如 `evt_10` vs `evt_2`）時，CSCV 區塊順序與時間軸不一致，PBO 數值可能失真。

**碼證**: `run_dsr_pbo`（`candidate_ledger.py:306-309`）`union = sorted({…returns.index})`；`reindex(union)` 行序＝字串序。對照 `to_return_series`（`candidate_ledger.py:152-153`）`rows.sort()` 依 `(entry_at_ms, …)` 建 index 序。字串序探針：`sorted(["evt_10","evt_2","evt_1"])` → `['evt_1','evt_10','evt_2']` ≠ 典型時間序。測試 `test_record_then_n_from_ledger` 用 `e000` 格式 id，未覆蓋非零填命名。

**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b

[MINOR] 信心度=Medium。失敗模式：使用者自訂 `event_id` 字串不保時間單調時，PBO `s_blocks` 切塊沿錯誤軸；不影響 B4.1／W8 entry×exit。

**修法**:
1. 聯集軸改為：取各 candidate `returns` 上 union event_id，排序鍵＝`receipts.event_level.entry_at_ms`（或 `to_return_series` 在 attrs 存 `entry_at_ms_by_event` digest）。
2. `test_candidate_ledger.py` 增：`evt_10`（早）／`evt_2`（晚）兩事件，斷言 `M` 行 0 對應早 entry。
3. 更新 docstring `observation_axis` 與實作一致。

**RECHECK**: `venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k pbo_obs` rc=0。

---

## 必答逐項（摘要）

1. **TODO B4.1/B4.2**：五欄驗證／邊界／不可做逐條對齊；白名單外檔未動。**漏**：型別閘 disguise（P1-01）。
2. **B4.1 隔離**：`model.fit(X_train,y_train)` 無 `sample_weight`（`pattern_bridge.py:163`）；`extract_decision_rules` 以 `train_plan.row_index` 切片（`pattern_extractor.py:137-142`）；`oot_split` 只算 `oot_lift` 不回流選規則；split 缺／train 空／全 test ⇒ `PatternSplitRequiredError`（測試 `test_split_missing_fail_closed_no_fallback`）。
3. **J8**：train-only `abs_point_biserial`（`pattern_bridge.py:143-148`）；test 段篡改 f59 不入選（`test_j8_ic_prescreen_train_only`）；平手 `( -score, name)` 決定性排序。
4. **AR-3**：`_common_constraint_block`＋`binary_discrimination_table(..., manifest=manifest)`（`pattern_bridge.py:183-186,209`）；非平行實作。
5. **W8**：五 `entry_price_semantic` parametrize 真實 kline exact（`test_to_return_series_hand_exact_each_entry_semantic`）；entry／label 不一致拒；無收據拒「自行推導」。
6. **Ledger/N**：`append_trial_attempt` 唯一寫入；`read_trial_ledger` 讀 N；DSR `source_artifact_hash ∈ ledger.artifact_hashes`（`deflated_sharpe.py:125-132`）；provenance sidecar 欄位齊（測試 `:128-131`）；`metric_value` 經 `compute_sharpe`（`candidate_ledger.py:186-197`）。
7. **型別閘**：顯式 auc／name 偷渡已拒；**disguise 可繞**（P1-01）。
8. **PBO 軸**：聯集＋`fillna(0)` 與 GAP-1 `(n_obs,n_candidates)` 一致；`s_blocks` 預設 8、`n_obs<s_blocks` unavailable；ledger≠輸入 ⇒ `universe_provenance_unverifiable`（探針確認）。行序問題見 P2-02。
9. **MinBTL**：`t_years`＝champion `span_years`（entry 最早→label_end 最晚，`to_return_series:154-155`）；`target_sharpe` 呼叫參數；短跨度 `loud`（`test_min_btl_shortfall_loud`）。
10. **進 B5**：P1-01 補強或 committee 裁決後 stamp；無 P0。

---

## VERIFY（本輪複驗）

```
venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger" → 22 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k auc_fed → 1 passed rc=0
git diff 3b1350df..HEAD --stat -- momentum/ tests/ → 4 files +893（僅 B4 白名單）
inline 探針 disguise AUC → run_dsr_pbo 無 MetricTypeError；dsr.status=ok（P1 證據）
inline 探針 ledger 只記 a、輸入 a+b → pbo.reason=universe_provenance_unverifiable
```

ASSUMPTIONS_VERIFIED: 上述命令＋`pattern_bridge.py`／`candidate_ledger.py` 全文對讀＋`pattern_extractor.py:77-174` 隔離路徑。  
TESTS_RUN: 見 VERIFY。  
FAILURES_SEEN: none（gate 全綠；P1/P2 為規格／閘缺口非 pytest 紅）。  
SCOPE_CHANGES: none。  
NUMERIC_OR_SCHEMA_IMPACT: review-only；指出 disguise 可產生錯誤 DSR 數值（語意污染）。

OUTPUT_PATH: handoffs/20260821-gap3-b4-review-r1-composer.md

STATUS: DONE
