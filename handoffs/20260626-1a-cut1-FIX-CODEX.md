# 20260626-1a-cut1-FIX-CODEX

## 正在做
- 已完成 LEAK-1 / LEAK-2 / FIX-embargo 修補與驗收。

## 待辦
- 等 Claude/Composer 重簽三方數據正確性；本次未凍 G-NEW、未切 default ON。

## 阻塞
- 無。

## 本次決策
- rolling IC flag-on 輸入改為 `train_mask | test_mask` allowed rows，purge hole 不進 rolling window。
- winsorize type-feature 分支改用 `_select_fit_series(series, fit_mask)` 判斷。
- holdout test start 改為 `split_point + purge + embargo`。
- OOS 測試 helper 改用真實 `_build_holdout_split_plan()` mask，補 purge label 不變、type branch train-slice、embargo 起點測試。

## 踩坑提醒
- Python 3.9 不支援 `ICConfig | None` 測試型別語法，已用 `Optional[ICConfig]`。
- type-feature 測試 train slice 不可全常數，否則既有 remove_constant 會正確刪欄。
- 驗收 PASS：`pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py tests/momentum/test_factories.py -q` → 30 passed；`grep -rE "from api\\." momentum/` → 無輸出。
