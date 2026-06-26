# IC Phase 1 B3 leak signoff fix

## 正在做
- B3 三方簽核回修：L1-L6 leakage adversarial findings 已修補。

## 待辦
- Claude/Composer 重新做 B3 數據正確性簽核與 code review。

## 阻塞
- none

## 本次決策
- `validate_split_integrity` 在 `purge_semantic=="rows"` 時要求 `expected_freq`。
- 新增 `validate_split_pair_integrity` 與 `SplitPairLeakageError`，adapter 建立 pair 後必檢。
- WF embargo 採「支援並 fail-closed」：後續 fold train 不得含先前 fold `[test_end,test_end+embargo_len)`。
- CPCV strict check 先依 config 重建 expected test group boundaries，再檢 train purge/embargo。

## 踩坑提醒
- 空 `row_index` 不代表 valid；仍需先檢 symbol、base length、symbol dtype。
- symbol bytes 只允許 UTF-8 decode 成 str；NaN/None/pd.NA fail-closed。
- 驗證：`pytest tests/momentum/core/test_split_contract.py tests/momentum/Analysis/test_ic_split_adapter.py -q` → 20 passed。
- 解耦：`grep -rE 'from api\.' momentum/` → 0 matches。
