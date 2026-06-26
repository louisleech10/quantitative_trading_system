已完成指定修補：

- LEAK-1：flag-on rolling IC 改為只用 `train_mask | test_mask` allowed rows，purge hole 不進 rolling window。[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1494)
- LEAK-2：winsorize type-feature 分支改用 train fit slice 判斷。[data_preprocessor.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/data_preprocessor.py:100)
- embargo：holdout test 起點改為 `split_point + purge + embargo`。[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:156)
- 測試：OOS helper 改用真實 `_build_holdout_split_plan()` mask，補 purge label/type branch/embargo 三個不變量。[test_ic_1a_cut1_oos.py](/Users/louis/Desktop/quantitative_trading_system/tests/momentum/Analysis/test_ic_1a_cut1_oos.py:46)
- 交接：已寫 `handoffs/20260626-1a-cut1-FIX-CODEX.md`。

ASSUMPTIONS_VERIFIED: 真實 split mask 會產生 purge hole；purge label 擾動不再改變 test rolling IC/ICIR；test-only type-like 值不再影響 winsorize 分支或 train 輸出；embargo>0 會推遲 test 起點。  
TESTS_RUN: `pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py tests/momentum/test_factories.py -q` → 30 passed；`grep -rE "from api\\." momentum/` → 0 output。  
FAILURES_SEEN: Python 3.9 不支援 `ICConfig | None`，改 `Optional[ICConfig]`；type-feature 測試 train slice 全常數導致既有 constant-removal 刪欄，改成 `{-100,0,100}` 非常數 type-like train fixture。  
SCOPE_CHANGES: none。未碰 service/frontend/reanalyze/deep analysis；未重寫根 `HANDOFF.md`。  
NUMERIC_OR_SCHEMA_IMPACT: 無 schema/輸出大小改動；flag 預設仍 OFF；flag-on rolling 與 embargo 行為按派工修正。

STATUS: DONE