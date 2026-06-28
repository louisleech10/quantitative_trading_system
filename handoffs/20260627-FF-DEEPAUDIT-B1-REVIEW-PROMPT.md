# 任務:code review B1 diff + 三方數據簽核獨立腿(Codex)

實作=Composer。被審=未 commit B1 diff(`git diff` momentum/atomic/* talib_wrapper/feature_factory/adf_safe_skip + api UI;新檔 compute_guard.py/talib_input_semantics.py/tests/feature_engineering/atomic/*/tests/references/*/tests/_golden/ff_deepaudit/*)。
依 SPEC/TODO Task 1.0~1.4。Claude 簽核腿已驗:`hl_statistics_BETA_5==talib.BETA(high,low)` True、`!=close,volume`、`Beta-CloseVolume==talib.BETA(close,volume)` True。Consumer Sync Checklist=`handoffs/...-B1-CONSUMER-SYNC.md`;差異表=`tests/_golden/ff_deepaudit/*.json`。

## A. code review(每點 PASS/問題+反例)
1. 防假綠:有無放寬/刪既有斷言?correctness mode 8 engine 接線正確(刪 MFI→raise 非 warning)?
2. **mutation 真 FAIL**:實跑驗證 test_atomic_differential/test_prepare_inputs_equivalence/test_handcoded_reference 的 mutation probe 真的會 FAIL(改 source/刪 map entry/EOM */÷)。附證據。
3. BUG-1 完整性:Consumer Sync Checklist 有無遺漏真實消費者(再 grep 一次)?adf_safe_skip 改動正確(hl BETA 排除 ADF、Correl-CloseVolume not-skip)?UI 顯示名?
4. 解耦:momentum 無 import api;logging 用 momentum.core.logging?
5. price_transform/cycle/statistics/custom 覆蓋到?

## B. 三方數據簽核腿(獨立判定「資料正確」與否)
- 獨立驗 BUG-1:標準 BETA/CORREL==talib(high,low)、別名==舊 close-volume。
- BUG-2:Klinger corr 僅 0.18 vs canonical(差異表)——標 variant=simplified + 文件化是否足夠?還是該升級為「需使用者/委員決策是否保留此簡化版」?明確表態。
- §G Affected Column Closure 是否真涵蓋 L2–L7 衍生(provenance)?有無未受影響欄被波及(旁路污染)?
- 結論:**你是否簽「資料正確」**(BUG-1/2 分別)?任一疑慮→不簽並說明。

輸出 `handoffs/20260627-FF-DEEPAUDIT-B1-CODEREVIEW-codex.md`:A 各點 + B 簽核結論(SIGN-OFF: BUG-1 PASS/HOLD、BUG-2 PASS/HOLD + 理由)。只寫 review 檔。完成 STATUS: DONE。
