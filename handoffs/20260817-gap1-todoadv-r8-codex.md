# GAP-1 TODO adversarial review R8 — CODEX

## Verdict：有根本缺陷需重作

實作者不可直接依目前 TODO 開工；先修 P0/P1 findings，重跑三家 adversarial。SPEC/TODO template check 已通過，但這只證錨點與非空殼，不證資料流、拓撲或守衛完備。

## B 三項 delta Verdict

| 項目 | Verdict | 核對結論 |
|---|---|---|
| Task 2.4 | 需修補後派工 | R1/R3/R7 方向正確；目前 regex 未限 `build_validation_section`、未 escape、W3 漏 dict reason，不能稱封閉集合。`plain_docs_sync_check.sh` 存在；正常 check/pre-push 可擋，`--staged` 明載只提醒不擋 commit，故「會擋」須標路徑。 |
| Task 3.4 | 需修補後派工 | factory 的 R1/R3 邊界可成立，optional response 欄位無既有 exact-payload 破壞證據；但 reporter 沒有 `t_years` 或 canonical `dataset_key` 輸入，未來有 ledger 仍會恆 `eligible=None`，且 catch-all 例外政策會掩蓋真 bug。今日 `n_unknown` 是 [A-裁決-降級] 之明知取捨，不是本身 finding。 |
| Task 4.3 | 有根本缺陷需重作 | 五欄位逐字正確；集合相等、三方 count、canonical hash 能擋 top-10 與同數量異集合，但不能證明 ledger 本身不是已被選後的 top-K。`n_is_lower_bound=True` 使 literal guard 仍可回 `ok`。 |

## C §N 八項逐條 Verdict

| 登記 | Verdict | 逐條核對 |
|---|---|---|
| G1-R1 | 成立 | `momentum/Optimization` 有 Optuna/objective，但沒有 ledger 生產者；blocked-by 與「重寫/開工」觸發可判定。 |
| G1-R2 | 成立 | `results/optimization_results/` 不存在且服務沒有可供 PBO 的真實矩陣；回測首次產生真實 optimization 產出是可判定觸發。 |
| G1-R3 | 理由不足 | R1/R2 是真實資料依賴，但 `n_unknown`、`display_downgrade`、`warning_text_key` 本身已是可展示的 API 契約；「無資料」不是阻止 empty/degraded 面板的充分理由，見 CODEX-R8-P1-10。 |
| G1-R4 | 成立 | 六條繞過都需真實生產者/持久化路徑才可驗；目前只能維持契約 fail-closed，不能宣稱已關閉。 |
| G1-R5 | 成立 | `user-ruling:2026-08-17` 明確選降級警語、不做 4xx；觸發為使用者改判或實際誤用。 |
| G1-R6 | 成立 | adaptive-search effective-N 的無偏可驗估計仍是 needs-research；「有文獻或可證偽 Monte Carlo 方法」是可判定觸發。 |
| G1-R7 | 部分成立 | needs-research 類型合理，但 registry 的「排程即可做」不是事件/門檻；沒有 owner、票號或排程狀態，觸發不可機械判定，見 CODEX-R8-P1-11。 |
| G1-R8 | 不成立 | cumsum 位於策略票外確實可另票，但「排程即可做」不是 blocked-by；實際程式與觸發都已存在，應建立獨立小 Task 而非以未來排程作觸發，見 CODEX-R8-P1-12。 |

## A §0/§1/§2/§3 核對摘要

11 類：1 矛盾/型別＝findings 01–09；2 端到端＝03/04/10；3 可測＝01/02/05/07/08；4 quant＝01/02/06/07；5 過度工程＝無；6 OOM/並行＝Task 4.1 守衛方向成立；7 cache＝無新增 finding；8 API/相容＝03/04/05；9 測試品質＝01/02/07/08；10 Agent 可執行＝05/07/08/09；11 短命工＝G1-R3/R8 另見 C。§RISK a,b,d 有 §G 數值 oracle；golden 有 sha256/provenance 要求，但不得把 template PASS 當語意驗收。SPEC §A 的 FACT-RECEIPT 可重跑，使用者裁決與成熟度地圖按 brief 不作爭議對象。

## CODEX-R8-P0-01

**斷言**: Task 4.3 的三項守衛仍可讓一個 ledger 本身只記錄事後挑出的 top-K 宇宙回傳 `ok`，因為沒有 exhaustive/unselected coverage proof。

**碼證**: SPEC:295-311/TODO:156-161 將 `n_is_lower_bound` 固定為 `True`，但 SPEC:583-599/TODO:313-317 只比 `candidate_ids` 集合、三方 count、呼叫方 hash。已實跑 `venv/bin/python -c '...'`：`selection_free=True source=ledger_all_candidates n_is_lower_bound=True`、`set_count_hash_checks=(True, True, True) status_if_guard_is_literal=ok`，其中 10 個 `top-*` ID 可同時被假想為「已選後才寫入 ledger」。RECHECK：同 probe 置換任意 top-K ID 集合即可重跑。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[BLOCKING] 這不是 R6 已修的「同數量異集合」問題，而是 ledger 內容本身不具全宇宙證明；PBO 會在污染的候選宇宙上正常產值。需新增不可偽造的 exhaustive/selection-free provenance（或明確把 `n_is_lower_bound` 非 `ok`），並增加「ledger 自己只含 top-K 但三項皆自洽」反例。

## CODEX-R8-P0-02

**斷言**: Task 4.2 在 path 級剔除 OOS 非有限候選後，仍直接用原始 IS champion 索引取 rank，champion 被剔除時結果可錯算或拋 IndexError。

**碼證**: SPEC:541-555/TODO:300-302 要求 IS champion 固定後，若候選在 IS 或 OOS 非有限則從該 path 剔除；TODO 又指定 `rankdata(oos_metrics, method="average")[champion]`，未定義 champion 不在 OOS 有效集合時的行為。已實跑最小反例：`venv/bin/python -c 'from scipy.stats import rankdata; candidate_ids=("c0","c1","c2"); champion_index=2; path_valid=(0,1); oos_metrics=rankdata((0.1,0.2), method="average"); print("candidate_ids=%r path_valid=%r champion_index=%d" % (candidate_ids, path_valid, champion_index)); print("oos_rankdata=%r" % (oos_metrics)); print("pseudocode_index_result=%r" % (oos_metrics[champion_index]))'` → `IndexError: index 2 is out of bounds for axis 0 with size 2`、`pbo_counterexample_rc=1`。若以壓縮陣列誤索引則會把別的候選排名當 champion。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[BLOCKING] 必須寫死「champion OOS 退化」是跳 path、重選 champion（會改 IS 語意）或回 typed non-ok；並加 champion-specific mutation/oracle。現有「多數候選常數」測試不覆蓋 champion 被剔除。

## CODEX-R8-P1-03

**斷言**: Task 3.1 的 TODO 新增 `budget_capped` 與 `10**18` cap，同時偏離 SPEC 的 EligibilityResult schema 與精確 `floor(exp(x))` 契約。

**碼證**: SPEC:375-398 的輸出欄沒有 `budget_capped`，且 §G:97-99 要求 `ub(budget)<=T<ub(budget+1)`；TODO:210-214 卻加入 `budget_capped: bool`，於 `x>700` 回未有來源的 `10**18`。Task 2.1 的 `eligibility_keys`（SPEC:266-267）也沒有 `budget_capped`，故將該欄放入 report 會違反 additional-properties gate；不放則又違反 TODO dataclass。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 對 `t_years=1500,target_sharpe=1`，真公式的 `x=750`，`floor(exp(x))` 遠大於 `10**18`，cap 後 `budget+1` 仍遠低於可行邊界，§G 不變式失效。需在 SPEC/TODO 先裁定 overflow-safe 的 exact representation 或明確上限/狀態，不能自行發明 cap 與輸出欄。

## CODEX-R8-P1-04

**斷言**: Task 3.4 的 reporter 介面沒有足夠輸入在 ledger 落地後計算 eligibility；`dataset_key=f"trial:{trial_number}"` 也不是 Task 2.2 的共同語意。

**碼證**: TODO:210 要 `assess_eligibility(..., t_years, ledger_result, target_sharpe)`，但 TODO:259 的 `for_study_trial(study_name, trial_number)` 沒有 `t_years`；TODO:261 只寫「由呼叫方傳入或無」，沒有對應參數/來源。Task 2.2 SPEC:297-311/TODO:156-161 只把 `dataset_key` 定義為讀取鍵，沒有 `trial:<n>` 規約；G1-R1 尚未接 producer。故今日 `n_unknown` 是明知降級取捨，但未來有帳本仍沒有可保證的 key/t_years 接線。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 建議將 `dataset_key` 與可驗證 `t_years`（或 PeriodReturns/artifact）納入 reporter protocol，並在 Task 2.1/2.2 只定義一次；否則 R8 wiring 只是永久 degraded placeholder。

## CODEX-R8-P1-05

**斷言**: Task 3.4 的「任何例外→2xx computation_failed」政策會把程式錯誤與可預期 unavailable 混成同一個附加回應，缺少可觀測的 fail-closed 邊界。

**碼證**: SPEC:476-492/TODO:257-269 明定 reporter 任何例外都回 `computation_failed`，且測試只要求 HTTP 仍 2xx；TODO 回傳 `str(exc)[:200]`，沒有要求 `logger.exception`、例外分類或 contract validation。這會把 TypeError、schema drift、bug 與缺 ledger 同樣降級，既有 route 的外層 Exception（api/routes/ml_pipeline.py:247-258）也不再收到錯誤。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5b

[MAJOR] 使用者裁決只是不硬擋 promote，不是允許吞掉真 bug。只捕捉明確的資料不可用/外部 I/O 例外、以 contract reason 回報並記 `exc_info=True`；對程式錯誤保留可觀測失敗，並加 mutation 令 reporter bug 不得只靠 2xx 測試通過。

## CODEX-R8-P1-06

**斷言**: Task 1.4 的 SPEC API 與 TODO API 不一致，且 SPEC 沒有說明三種 `t_semantics` 如何選定。

**碼證**: SPEC:165-189 定義 `extract_period_returns(backtest_result, *, timeframe)`；TODO:114-126 改成必填 `t_semantics`。SPEC 同時要求產出/驗證 `bar_count`、`nonzero_return_bars`、`trade_level`，但沒有 selection/default 規則；B3 的 DSR 只接 `PeriodReturns`，因此實作者依 SPEC 無法選語意，依 TODO 又會偏離 canonical signature。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 先在 SPEC/TODO 共同 API 決定 `t_semantics` 是 required input、固定 canonical value，或明確拆三個 extractor；同時把呼叫端與反向測試接上，否則 Task 1.4 不可獨立實作/驗收。

## CODEX-R8-P1-07

**斷言**: Task 2.2 的 ledger 計數規則無法滿足 Task 2.3 自己要求的 invariant，因為沒有定義 schema-valid 但 `metric_valid=False` row 如何進 `n_failed_or_pruned`。

**碼證**: TODO:159 只說「非法列」增加 `n_failed_or_pruned`；TODO:160 卻令 `n_evaluated=len(rows_valid_schema)`、`n_valid_metrics=sum(metric_valid)`；TODO:175 要 `n_evaluated == n_valid_metrics + n_failed_or_pruned`。一列合法 JSON、`metric_valid=False` 時，依文字得到 `1 == 0 + 0`，直接失敗；若把它算 failed，又需在 TODO/SPEC 明定 state/metric_valid 的優先規則。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5b

[MAJOR] 明定 failed/pruned row 的計數與 reason 累積，再加一筆合法 invalid-metric fixture；不要讓 conformance test 依實作者猜測。

## CODEX-R8-P1-08

**斷言**: Task 2.4 的 regex 不是 W1/W4 所宣稱的輸出組裝封閉集合，也不是 W3 的所有 reason literal 掃描。

**碼證**: TODO:188 以 `re.search(rf'["\']{name}["\']')` 掃整個 `report.py`，未 `re.escape(name)`、未限 `build_validation_section` AST；comment/docstring/dead branch 中的 `"eligibility"` 就能假陽性。W3 只掃 `reason="..."`/`reason == "..."`，漏掉 `{"reason": "invented"}`、`reason = "invented"` 等實際輸出。SPEC:357-367 要的是機械封閉比對，現規則可讓幽靈欄位/自創 reason 通過。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5b

[MAJOR] 使用 Python AST/限定函式的字串與 dict-key/assignment 掃描，對 mutation 覆寫 report body、comment、dict reason 與 regex-special section name 各加反例；目前 regex 不能作 wiring gate。

## CODEX-R8-P1-09

**斷言**: SPEC 與 TODO 的 B4 dependency topology 不一致；SPEC 只列 B2 Task 2.1，但 Task 4.3 明確需要 Task 2.2 的 `LedgerReadResult`。

**碼證**: SPEC:499 寫 B4 依賴「B2 Task 2.1」；SPEC:528-531、589-592 又要求 `ledger_result.candidate_ids`/`n_candidates_considered`。TODO:40 已補列 B2 2.1/2.2。TODO 雖較合理，卻代表未 reconcile 的 canonical drift：按 SPEC gate 可在 2.2 尚未存在時開 B4。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 以 Task 2.2 為 B4 硬依賴，並同步修 SPEC/TODO/B4 gate；dependency 不應靠 TODO 私自修正 SPEC。

## CODEX-R8-P1-10

**斷言**: G1-R3 的 `blocked-by:G1-R1/R2（後端無資料可顯示）` 不是充分阻塞理由；本票已定義明確的 unavailable/degraded API state，可先做空/降級消費契約。

**碼證**: SPEC:454-474 定義 `display_downgrade`/`warning_text_key`；SPEC:476-492、TODO:257-269 要 Task 3.4 在無 ledger 時仍回 `eligible=None` 與非空警語；registry:46 卻把前端面板整體延後到真實 producer/matrix。這證明「無真實資料」不等於「無可展示資料」。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#d226fa453504

[MAJOR] 若產品刻意不碰 frontend，blocked-by 應改成可驗證的 frontend scope/maturity 依賴並給 owner/票號；若不刻意排除，G1-R3 應收回為 empty/degraded UI Task。這不是樣式評分，而是殘留是否仍合理。

## CODEX-R8-P1-11

**斷言**: G1-R7 的 registry trigger「排程即可做」不可機械判定，不符合 §N 要求的可判定觸發條件。

**碼證**: SPEC:691-692 及 registry:50 將 MinBTL 誤差列 needs-research，但 registry 的 trigger 只有「排程即可做」，沒有研究完成、票號、owner、日期或 merge gate；任何時間都可聲稱已觸發/未觸發。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#d226fa453504

[MAJOR] 保留 needs-research 可以，但 trigger 至少要指向具名 research ticket/owner/status 或可驗證文獻/Monte Carlo receipt；否則殘留登記不具不遺忘功能。

## CODEX-R8-P1-12

**斷言**: G1-R8 把現存、獨立可修的 `np.cumsum` 以 `blocked-by:不在策略路徑` 留在 §N，理由不成立為本票的 blocked-by。

**碼證**: 實檔 `momentum/Analysis/prediction_analyzer.py:155` 仍是 `cum_strategy = np.cumsum(strategy_returns)`；SPEC:693-694 與 registry:51 都承認位置與語意，但 trigger 只寫「排程即可做（小票）」。它不依賴 G1-R1/R2、沒有外部研究阻塞，且 TODO:123 已明確把它隔離而非修正。

**來源摘要**: momentum/Analysis/prediction_analyzer.py#472c48fe06b6

[MAJOR] 應另開明確的小 Task（改 `cumprod` 或改名/停用策略敘事）並以其 ticket/排程狀態作 trigger；在本票中不得把「不屬本路徑」誤寫成依賴已成立。

## 被當成事實的未驗證假設（§0）

`template_check todo`、既有符號存在、SPEC/TODO 路徑、`plain_docs_sync_check.sh` 存在與目前 rc 已實跑核實；「今日無 ledger producer」「成熟度地圖」「2026-08-17 使用者裁決」依 brief 視為 fact-verified/user-ruling，不另作 finding。未將文獻/產品裁決本身當作本輪攻擊目標；真正未解的 assumptions 已轉為上述可證偽 findings。

ASSUMPTIONS_VERIFIED: template_check rc=0；plain_docs_sync_check rc=0；Task 4.3 top-K self-consistent probe rc=0；Task 4.2 champion-OOS 排名反例按預期以 IndexError/rc=1 暴露缺陷；SPEC/TODO/registry/既有 route 與 prediction_analyzer 逐段核對；未修改 SPEC/TODO/程式/戳記。
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → TEMPLATE PASS rc=0；`bash scripts/plain_docs_sync_check.sh` → 全數同步 rc=0；top-K `venv/bin/python -c '...'` probe → 三 checks True、literal status_if_guard=ok rc=0；PBO champion-OOS probe → IndexError、rc=1（預期反例）。`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-todoadv-r8-codex.md --family codex` → 未進入腳本，PreToolUse 因 R8 OPEN debt 拒絕 dispatch，故無 completeness rc。
FAILURES_SEEN: 預期的 PBO 反例 probe 以 IndexError/rc=1 暴露缺陷；completeness 命令被外部治理閘門拒絕，非格式檢查結果；本輪未執行產品測試，因 brief 明定只 review 且尚無實作。
SCOPE_CHANGES: none；只新增本交件檔。
NUMERIC_OR_SCHEMA_IMPACT: review-only；未改產品數值/schema；指出 TODO/SPEC schema/topology drift。
STATUS: BLOCKED — completeness_check 未執行；PreToolUse 要求先處理 OPEN round 4f73d876-59a2-4a4c-b187-1228dbec2d1d，不能在本輪自行 abandon 或繞過治理閘門。
