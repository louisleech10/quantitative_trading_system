# 派工:修 B2 required-probe 抓 L65 winsor 欄(Composer,targeted)

## 現況(好消息+小缺口)
test_c2_1 用批次讀+抽樣**13 分跑完**(原>40分,perf 成功);**主 values/NaN/columns gate 全過**(收斂設計解 float16/NaN 假紅)。**唯一失敗** = 你寫的 mutation 覆蓋守衛正確盡責:
`AssertionError: mutation layer coverage failed (sampling design error): missing ['L65_winsor'] in sampled set`
即抽樣集沒含 L6.5 winsor 輸出欄 → winsor mutation 探針(`test_mutation_causal_winsor_full_fit_fails`)抓不到自己注入 = 會假綠,守衛擋下。

## 根因待你查證
`_select_required_probe_columns`/`_assert_mutation_layer_coverage` 用 `layer=="L65" and "winsor" in col.lower()` 找 winsor 欄。但 L6.5 append 建 `{group_id}_L65` group(`feature_preprocessor.py:869`),group 內含 winsor/rank/zscore/gaussian 全部輸出。**確認 L65 group 內 winsor 輸出欄的實際命名**(是否含 "winsor" token?還是別的後綴?用小範圍 generate 看實際欄名,或讀 append rename 碼)。

## 修法(對準實際命名)
- 改 `_select_required_probe_columns`：用 L65 winsor 輸出欄的**實際命名規則**偵測(若不含 "winsor",改抓正確 token/後綴),確保至少 1 個 L65 winsor-output 欄進 required-probe → sampled set。
- 對應改 `_assert_mutation_layer_coverage` 的 has_winsor 判定一致。
- **驗證 winsor mutation 仍真紅**:確認 sampled set 含的 L65 winsor 欄,在 full-fit winsor mutation 下值會變(>2e-3)→ 探針 FAIL。

## 收尾(別硬撐全鏈到 timeout)
- 改完 py_compile + 小 helper smoke。**全鏈 test_c2_1 + mutation 留 Claude 長 timeout 驗**。改完即交。
- 更新 `handoffs/20260627-FF-DEEPAUDIT-B2-RESULT.md`。完成 STATUS: DONE/BLOCKED。
