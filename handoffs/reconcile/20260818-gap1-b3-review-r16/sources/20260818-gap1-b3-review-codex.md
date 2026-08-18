# GAP-1 B3 code review — family=codex — task-id=20260818-GAP1-B3-REVIEW-R16
Verdict: 需修補後進 B4；無 P0/P1，3 個 P2 與 1 個 P3；輸出即本檔。
## CODEX-R16-P2-01
**斷言**：DSR/PSR 單元測試沒有真正固定規格要求的 skew=0、Pearson kurtosis=3 oracle。
**碼證**：`_symmetric_returns()` 的成對隨機幅度 fixture 實跑 Pearson kurtosis=2.6835207094713915；因此測試可在未覆蓋指定矩特例時通過。
**來源摘要**：`docs/GAP1_STRATEGY_OVERFIT_TODO.md#42a6dce48e47`；`tests/momentum/Analysis/strategy_validation/test_deflated_sharpe.py#8ef47c23d97b`。
[MINOR] 信心度=10/10；失敗模式是 oracle coverage 不足；修補為固定六點對稱序列並在比較 DSR/PSR 前明確斷言 skew=0、kurtosis=3。
## CODEX-R16-P2-02
**斷言**：DSR 測試 `_ledger` fixture 違反 B2 ledger invariant，未證明實際 ledger 狀態下的 DSR 路徑。
**碼證**：fixture 預設 `n_valid_metrics=3,n_for_dsr=10,n_evaluated=10,n_failed_or_pruned=0`；實跑 `n_evaluated == n_valid_metrics + n_failed_or_pruned` 為 `False`。
**來源摘要**：`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#bcfa76703d2a`；`tests/momentum/Analysis/strategy_validation/test_deflated_sharpe.py#8ef47c23d97b`。
[MINOR] 信心度=10/10；失敗模式是 impossible fixture 造成假綠；修補為令 n_evaluated 等於 valid+failed，另以獨立 case 覆蓋 snapshot 上限。
## CODEX-R16-P2-03
**斷言**：reporter 的 `InvalidValidationArgument` 5xx 路徑在 pipeline JSON 已落盤後才執行，失敗請求會留下 ghost artifact。
**碼證**：route 先在 `ml_pipeline.py:218-223` 寫檔，後於 `249-258` 呼叫 reporter 並將負 `t_years` 轉為 500；同一 pytest 實跑 log 先出現 saved path、再出現 exception/HTTP 500。
**來源摘要**：`api/routes/ml_pipeline.py#c169afcbdb97`；`handoffs/20260818-gap1-b3-review-BRIEF.md#8881a9ea1cc5`。
[MINOR] 信心度=9/10；失敗模式是 5xx 後可重試但殘留不完整 pipeline；修補為 reporter 先於 persistence，或在 5xx 上做明確 transactional cleanup。
## CODEX-R16-P3-04
**斷言**：B3 commit 在 `create_adversarial_validator()` 新增未使用的 runtime `StrategyValidationReporter` import，造成無必要耦合與啟動成本。
**碼證**：`momentum/factories.py:564` import 後函式只回傳 `AdversarialValidator(config=config)`；真正 reporter factory 位於 `:767-771`。
**來源摘要**：`momentum/factories.py#f2b0a3d33fa1`；`handoffs/20260818-gap1-b3-review-BRIEF.md#8881a9ea1cc5`。
[TRIVIAL] 信心度=10/10；失敗模式是無功能必要的 import side effect；修補為移除該行，保留專用 lazy factory。
段落結論：A 契約/實作大致符合；B ledger、status、report shape、route 入口可追溯但有 P2-03；C 17/17 mutation 皆轉紅；D hand values/factors/int fields 通過，P2-01 未達 exact moment oracle。
ASSUMPTIONS_VERIFIED: R9 三方 reconcile stamps 均 APPROVED；目標為 cbd9ec69；`n_source` 無 contract enum；warning key 唯一定義；momentum→api import grep=0，baseline checker 通過。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` = 220 passed；回歸 = 9 passed；`bash scripts/gap1_b1_mutation_probe.sh` = rc0、17/17 mutants red；`python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` = BASELINE OK。
FAILURES_SEEN: `scripts/restore_golden_inventory.sh` rc128（sandbox 禁止建立 .git/index.lock，未改 .git）；mutation probe 結尾 tail 缺少暫存 log，但 rc0、mutant restore 後工作樹無新增目標檔變更。
SCOPE_CHANGES: none；僅新增 `handoffs/20260818-gap1-b3-review-codex.md`，未改 code/SPEC/TODO/data_cache，未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none；本檢查未改輸出 schema、數值、檔案大小或既有測試斷言。
HANDOFF_OUTPUT: `handoffs/20260818-gap1-b3-review-codex.md`
STATUS: DONE
