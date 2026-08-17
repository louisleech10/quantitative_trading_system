# GAP-1 SPEC R2 closure review — codex

task-id: `20260817-GAP1-X-REVIEW-R2` ｜ family: `CODEX` ｜ target: `docs/GAP1_STRATEGY_OVERFIT_SPEC.md` commit `4f59a010`

## Closure table（逐條重跑 R1 反例）

| R1 finding | verdict | closure evidence |
|---|---|---|
| CODEX-R1-P0-01 | PARTIAL | `SPEC:40-48` 已改成 upper-bound、`E[max_N]`、N=1 特例；但 `n_semantics=adaptive_search` 與 `§N:455-458` 仍沒有 effective-independent-N 的可驗證轉換或 fail-closed 閘。 |
| CODEX-R1-P0-02 | CLOSED | `SPEC:65-70,160-179` 已把三個既有檔與 signature/metadata 變更列入白名單；原先「只能越界或永遠 default」的 scope 矛盾消失。新增的比值 oracle 另見 CODEX-R2-P0-01。 |
| CODEX-R1-P0-03 | PARTIAL | `SPEC:192-206,221-235` 已承載 semantics、variance enum、`valid_sharpe_values`；但 `Task 3.2:292-301` 的 signature 沒有 ledger result/values 輸入，`ledger_cross_trial` 如何取得樣本仍未落地。 |
| CODEX-R1-P0-04 | PARTIAL | `§N:442-450` 已逐項列出六條 bypass、IC/XGBoost 隔離及 `adaptive_search`；同段明寫「未覆蓋、無法機器阻止」，故原 fail-closed 缺口仍存在，只是殘留已誠實具名。 |
| CODEX-R1-P1-05 | PARTIAL | `Task 4.2:366-377` 已鎖 T×N、同步、invalid 分母、平均 tie、rank；但 `§G:95-98` 的 alpha μ 仍只說寫入尚不存在的 golden，重跑 `test -e tests/momentum/Analysis/golden/gap1_reference_cases.json` → absent。 |
| CODEX-R1-P1-06 | PARTIAL | `Task 4.1:346-356` 已鎖 remainder、lazy、20,000 cap；`C(16,8)=12870` 不與 cap 衝突，但 cap 不隨 `n_obs` 變化，單一 path 的 index payload 仍無 tier-aware budget。 |
| CODEX-R1-P1-07 | CLOSED | `Task 3.3:325-330` 明定 3×2³=24 案例，僅 eligible=True 且三關 ok 可不降級，其餘 23 案例均須 warning、無推薦鍵。 |
| CODEX-R1-P1-08 | CLOSED | `Task 2.1:207-216` 已指定唯一 resolver、實際 dereference、缺檔/缺鍵/型別錯 raise、drift test 與 IC 逐值相等。 |
| CODEX-R1-P1-09 | CLOSED | `§RISK:16-17` 明確撤回 factories.py 承諾，`§C:65-70` 也未再要求 factory task；RISK/Task scope 不再互斥。 |

## 數值與 FACT-RECEIPT 複核

`rg --glob '*.py' 'deflated|DSR|PBO|CSCV|MinBTL|min_btl' momentum api` → 0 行（rc=1）；Optuna/results 目錄不存在；兩個 `PerformanceMetrics` 呼叫點仍是 `vectorized_backtest.py:84`、`strategy_backtest.py:113` 且未傳 periods；F-ST-2/F-ST-3 均在 `docs/TEST_DESIGN_CHARTER.md:102`。§A 的 HDF5 receipt 原命令 `f["1h/data"]` → `KeyError`，實際 `BTCUSDT/1h|4h|12h/data` 才得到 `(20352,)`、`(5088,)`、`(1696,)` 與 `T=2.3232876712328765`，故該 FACT 不成立（見 CODEX-R2-P1-01）。

實跑公式輸出：budgets=`[3,13,104,1422]`；`min_btl(13)=2.2799549844 <= T < min_btl(14)=2.3458287374`；`E[max SR]/√V`=`1.5745983, 2.5306029, 3.2551215`；`C(12,6),C(14,7),C(16,8),C(20,10)`=`924,3432,12870,184756`；`V[SR](T=1200,SR=1.5,skew=0,kurt=3)=0.0017723102585`。上述 §G 等式數值成立；receipt 路徑與 Task1.3 oracle 不成立。

## CODEX-R2-P0-01

**斷言**: Task 1.3 要求的 Sharpe 比值 oracle 在既有 `PerformanceMetrics` 預設 risk-free 語意下不成立；照 SPEC 與現有程式同時實作會無法通過驗收。

**碼證**: `SPEC:167-177` 要求比值精確等於 `sqrt(8760/730)`；`momentum/Strategy/performance_metrics.py:20,77-86` 的預設 `risk_free_rate=0.02` 會使年化轉換含 period-dependent subtraction。對同一 equity sequence 實跑：`pm_ratio=3.4728899102086075`、`expected=3.4641016151377544`（命令：`venv/bin/python -c '...PerformanceMetrics(...periods_per_year=8760/730)...'`）。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[BLOCKING] 信心度=High；修正方式須固定 oracle 的 risk-free（例如明定為 0）或把非零 risk-free 的完整比值列成 expected，且不得為過測而改掉 `PerformanceMetrics` 既有語意。

## CODEX-R2-P1-01

**斷言**: §A FACT-RECEIPT 的 kline 路徑不是目前真實 HDF5 的可重跑路徑，故由它導出的 20352/T 與數值 gate 沒有有效 receipt。

**碼證**: `SPEC:25` 宣稱直讀 `1h/data`；同一 h5py 命令實跑 `KeyError: component not found`。唯讀檢查 root keys → symbols；`BTCUSDT/1h/data`、`BTCUSDT/4h/data`、`BTCUSDT/12h/data` 才輸出 `(20352,)`、`(5088,)`、`(1696,)`。RECHECK: `venv/bin/python -c 'import h5py; f=h5py.File("data_cache/feature_klines/kline_cache.h5"); print(list(f.keys()))'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[MAJOR] 信心度=High；receipt 必須改成存在且記錄 symbol provenance 的 dataset path（或 metadata-derived path），再由該 receipt 重算 T 與 3/13/104/1422。

## CODEX-R2-P1-02

**斷言**: Task 2.1 宣稱 13-key JSON SoT，但 `report_sections`、`eligibility_keys`、`reasons` 沒有內容或型別/枚舉定義，Task 3.3 因而仍可由實作者任意選 schema。

**碼證**: `SPEC:192-206` 只逐項定義 `ledger_record_keys`、`n_fields` 與五個 `*_values`，在 `reasons` 後沒有三個未定義集合的內容；`SPEC:319-330` 只 pointer `report_sections`/`eligibility_keys` 並要求 validator。RECHECK: `nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '192,216p;319,330p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[MAJOR] 信心度=High；需為三個集合補機器可驗證內容，否則空/錯的報告 schema 仍可讓 24-case 測試自洽而非與契約對證。

## CODEX-R2-P1-03

**斷言**: 新 Task 1.4 依賴 Task 1.3 才存在的 `BacktestResult.annualization`，但 B1 宣告無依賴且 Task 1.4 排在 Task 1.3 之前，TODO 順序可先產出不可執行的 canonical extractor。

**碼證**: `SPEC:105` 宣告 B1 無依賴；`SPEC:137-155` 的 Task 1.4 明確讀「新增之 annualization」；`SPEC:160-172` 才由 Task 1.3 新增該欄位。RECHECK: `nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '103,172p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[MAJOR] 信心度=High；需明列 1.4→1.3 依賴或調整 task/契約順序，並指定缺 annualization 時的 fail-closed 行為。

## Verdict

結論：**需修補後再進 TODO**。真正阻擋者：CODEX-R2-P0-01；CODEX-R1-P0-01 的 effective-N/independence 殘缺；CODEX-R1-P0-03 的 ledger variance dataflow；CODEX-R1-P1-05 的未凍結 alpha oracle；CODEX-R1-P1-06 的 `n_obs` 資源上限；CODEX-R2-P1-01～03 的 receipt、contract schema、Task dependency。CODEX-R1-P0-04 的六條生產 bypass 目前由 §N 明確列為未來接線項，對純統計核心不另擴 scope，但它仍不是 CLOSED。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、R2 brief、review template、codex R1、R1 frozen sources.lock/synth、SPEC R2；`git diff 4f59a010 -- docs/GAP1_STRATEGY_OVERFIT_SPEC.md` rc=0；R1 IDs 全部在 R2 SPEC 命中；上述 grep/h5py/公式/程式碼反例均實跑。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`, rc=0；公式與 PM ratio 命令 rc=0；原 HDF5 receipt 命令 rc=1（KeyError，finding 證據）；completeness 指定命令與等價 `bash ./scripts/...` 均在腳本啟動前被 PreToolUse OPEN-debt hook 擋下，未取得 script rc；未跑產品 pytest（本輪只審 SPEC，且禁止改碼）。
FAILURES_SEEN: 原 HDF5 FACT receipt 路徑失敗；Task 1.3 PM ratio oracle 實算不符；completeness 兩次均被既有 OPEN debt 擋在執行前；均未改動以製造假綠。
SCOPE_CHANGES: 只新增 `handoffs/20260817-gap1-specadv-r2-codex.md`；未改 SPEC、程式、tests、data_cache、根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: 未改輸出；確認 §G 數值等式成立，並記錄 receipt、Task1.3 ratio、13-key schema 的缺口。
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r2-codex.md`
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護；本輪未改寫。
STATUS: BLOCKED — completeness_check 未取得 rc，兩次執行均在 PreToolUse OPEN-debt hook 前置擋下。
