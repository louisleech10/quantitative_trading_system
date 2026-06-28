# 派工:修 B1 C1-2 假綠(Composer,§B8 原實作者修)

Codex code review 證實 C1-2 differential 測試**假綠**:
- 把 `ATR` 從 `TALibWrapper._INPUT_TYPE_MAP["hlc"]` 移除後,跑 `pytest tests/feature_engineering/atomic/test_prepare_inputs_equivalence.py::test_prepare_inputs_byte_equal_to_semantics_table` → **仍 15 passed(含 ATR)**,該 FAIL 沒 FAIL。
- 根因:`build_talib_input_semantics()` 的 oracle 從 `TALibWrapper.list_indicators()`/`_INPUT_TYPE_MAP` 衍生 → mutation 同時污染待測與 oracle = 自指 tautology。

## 修法(必達)
- `TALIB_INPUT_SEMANTICS` 改成**獨立硬編 mapping**(indicator→input_type→df 欄位 ordered),**不得**從 `_INPUT_TYPE_MAP`/`list_indicators()` 衍生。這是 oracle,須獨立於待測 source。
- 驗收硬門檻:**從 `_INPUT_TYPE_MAP["hlc"]` 移除 ATR(真實 registry mutation)後,`test_prepare_inputs_byte_equal_to_semantics_table` 必 FAIL**(因 wrapper 會餵錯欄,但獨立 oracle 仍期望 hlc)。附 mutation 前後 pytest 輸出證明。
- 不要改 BUG-1/BUG-2/其他 Task;只修 C1-2 oracle 獨立性 + 其 mutation 可證偽。

## 次要:Codex 另指 correctness mode 只有 MFI 路徑有 regression 測試,其他 7 engine 是 code-inspect。若低成本,加一個跨 engine 的 fault-injection 參數化測試(刪任一已登錄指標→raise);若成本高,在 RESULT 說明為何足夠。

收尾:更新 `handoffs/20260627-FF-DEEPAUDIT-B1-RESULT.md` 附 C1-2 mutation FAIL 證明。完成 STATUS: DONE。
