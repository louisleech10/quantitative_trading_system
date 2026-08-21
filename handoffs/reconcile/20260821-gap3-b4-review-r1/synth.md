# Reconcile — 20260821-gap3-b4-review-r1

**來源** 20260821-gap3-b4-review-r1-codex.md, 20260821-gap3-b4-review-r1-composer.md, 20260821-gap3-b4-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（主委 Claude 裁決；全部寫回，pattern_bridge＋candidate_ledger 27 passed、event_samples 全套 222、GAP-1 strategy_validation 272；receipt `handoffs/run_receipts/20260821T153000Z-gap3-b4-r1-fix-gate.log`）

**Verdict**: 需修補後合併——8 條 findings 全數採納修補（已落檔）；R2 由原提出方重跑同一反例閉合，全 CLOSED 後三家 RECONCILE-STAMP → B4 CLOSED。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| X1 PBO 觀測軸＝entry 時間序 | CODEX-R1-P1-03, COMPOSER-R1-P2-02, GROK-R1-P1-01 | **採納**：`to_return_series` attrs 增 `entry_at_ms_by_event`（時序收據）；`run_dsr_pbo` 聯集軸 `sorted(key=(entry_at, id))`、跨候選同事件時間戳不一致 ⇒ ValueError；`observation_axis` 字面＋首末 entry ms 揭露；測試：字串序與時間序相反之 event_id、spy 擷取 `returns_matrix` 斷言列序 |
| X2 型別閘不可偽裝 | COMPOSER-R1-P1-01, GROK-R1-P2-01 | **採納（GROK 方案①＋COMPOSER 修法 1）**：`_assert_return_series` 改驗 `to_return_series` 收據 attrs 全齊（t_semantics=trade_level／entry_semantic／label_definition／source_artifact_hash 64hex／span_years>0／entry_at_ms_by_event 覆蓋全 index）＋n≥2；分數數列（無收據／`name=score`／單一值）皆 MetricTypeError。不採值域啟發（COMPOSER 修法 2：0–1 區間會誤拒合法小報酬序列）。誠實邊界：蓄意偽造 attrs 不在受理範圍 |
| X3 B4.1 manifest 必填 | CODEX-R1-P1-01 | **採納（部分）**：`manifest=` 改必填 keyword（缺／table 空／summary 無 n ⇒ ValueError）——AR-3 必需輸入＝split plan＋cluster manifest；**strata 維持選用**（反例分層非 SPEC AR-3 必需輸入，缺 ⇒ 分層空、overall 照算） |
| X4 未記帳候選不得成 champion | CODEX-R1-P1-02 | **採納**：DSR／MinBTL 前要求 `frozenset(input) == ledger.candidate_ids`，否則整體 `unavailable:universe_provenance_unverifiable`＋`candidate_set_mismatch`；測試 logged/unlogged 反例 |
| X5 provenance command／expected 必填 | CODEX-R1-P1-04 | **採納**：寫任何檔前先驗 `command`／`expected∈{pass,fail}` 非空；sidecar 於 `_ledger_lock` 下 append。誠實邊界：帳本與 sidecar 非同一交易（GAP-1 無跨檔交易 API），順序「全驗→帳本→sidecar」、sidecar 失敗 raise |

白名單檢視：改動限 `pattern_bridge.py`／`candidate_ledger.py`（新檔）與兩個測試檔；`pattern_extractor.py`／`strategy_validation/*` 未動。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: B4.1 缺 manifest/cluster context 仍可完成並輸出結果，違反 AR-3 必需輸入與 raw/effective-n contract。
**碼證**: `pattern_bridge.py:92-97,182-185,209` 將 `manifest`/`strata` 設 Optional 並缺 strata 造空表；`tables.py:61-82` 缺 manifest 輸出兩個 n=None。實跑 probe → `{'n_events_raw': None, 'n_events_effective': None, ...}`；B4 gate → 22 passed, rc=0。
**來源摘要**: momentum/Analysis/event_samples/pattern_bridge.py#2d4c5b8daf18；docs/GAP3_EVENT_TODO.md#df04bdabf37d
修法：要求有效 EventManifest 與 cluster/strata receipt，缺任一 fail-closed；RECHECK：新增缺 context 反例後重跑 B4 gate。
## CODEX-R1-P1-02
**斷言**: `run_dsr_pbo` 只用 artifact hash membership 綁 DSR，未要求 candidate IDs 等於 ledger；未記帳 candidate 可成 champion 並產生 DSR。
**碼證**: `candidate_ledger.py:254-285` 從輸入候選選 champion；`deflated_sharpe.py:123-132` 只檢查 hash membership；`candidate_ledger.py:301-320` 的 universe guard 只包 PBO。反例 ledger={logged:H}、輸入={unlogged: attrs.hash=H}：預期 DSR unverifiable，實際可選 unlogged 並通過 hash gate。
**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b；momentum/Analysis/strategy_validation/deflated_sharpe.py#4fb291524e3f
修法：DSR/eligibility 前要求候選 ID 與 artifact mapping 全等 ledger snapshot，否則 unavailable；RECHECK：加 logged/unlogged 反例驗 DSR 不產出。
## CODEX-R1-P1-03
**斷言**: PBO 聯集觀測軸按 event_id 字典序而非 entry time 排序，非單調 ID 時 CSCV 分塊使用錯誤時間軸。
**碼證**: `to_return_series:152-153` 只保留 entry-time 排好的 ID；`candidate_ledger.py:306-309` 丟掉原序後 `sorted({event_id})` 建 union/M。反例早進場=`z-early`、晚進場=`a-late`：預期 rows `[z-early,a-late]`，實際 `[a-late,z-early]`，違反 `:247-250` docstring。
**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b；docs/GAP3_EVENT_SPEC.md#544c2922ef2e
修法：CandidateReturns 保留 entry-time/observation-order receipt，PBO 依 canonical 軸排序並拒缺軸；RECHECK：非時間序 ID exact matrix 測試 CSCV 輸入順序。
## CODEX-R1-P1-04
**斷言**: provenance 的 `command`/`expected` 可省略，sidecar 寫入 null，違反每 oracle 必記可重播命令與預期。
**碼證**: `candidate_ledger.py:168-169` 列兩欄選填；`:205-217` 用 `.get()` 寫 sidecar，`meta_without_command_expected` 仍先 append ledger 再產生 null。
**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b；docs/GAP3_EVENT_TODO.md#df04bdabf37d
修法：append 前要求非空 command/expected 且同鎖寫 sidecar；RECHECK：缺任一欄應拒寫且 ledger/sidecar 無半成品。
逐條 verdict：1 train/test fit 隔離、sample_weight、2 split fail-closed、3 J8 train-only deterministic、5 W8 五 semantic exact、7 metric reject、9 MinBTL span/target/loud 均有碼證與 gate pass；4 受 P1-01、6 受 P1-02、8 受 P1-03；10 不可進 B5。
ASSUMPTIONS_VERIFIED: `venv/bin/python -c 'from tests.momentum.event_samples.test_pattern_bridge import synth,cfg; from momentum.Analysis.event_samples.pattern_bridge import extract_event_patterns; X,y,p=synth(); r=extract_event_patterns(X,y,p,None,cfg()); print({k:r["common"][k] for k in ("n_events_raw","n_events_effective","degraded","formal_pooled_inference_allowed")})'` → raw/effective n=None；4 檔白名單、未改碼。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k 'pattern_bridge or candidate_ledger'` → 22 passed/195 deselected/rc=0；`git diff --check 3b1350df..HEAD -- momentum/Analysis/event_samples/pattern_bridge.py momentum/Analysis/event_samples/candidate_ledger.py tests/momentum/event_samples/test_pattern_bridge.py tests/momentum/event_samples/test_candidate_ledger.py` → rc=0。
FAILURES_SEEN: none；SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: review-only，未改輸出。
STATUS: DONE
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
