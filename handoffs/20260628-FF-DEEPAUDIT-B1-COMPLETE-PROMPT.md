# 派工:FF 深稽 B1 完成批(Composer)— BUG-2 canonical + correctness-mode 補全 + 補探針

接續 B1。讀 SPEC/TODO Task 1.0/1.3/1.4 + **新章程 `docs/TEST_DESIGN_CHARTER.md` §B1.1/B1.2/B1.3(可執行自證 mutation 探針 + oracle 獨立 + 注入須重置快取)**。
**新硬門檻**:本批所有正確性測試**必過 `bash scripts/mutation_probe_check.sh tests/feature_engineering/atomic/`**(每檔有 test_mutation_* 或明示 N/A,且探針真跑過)。

## 1. BUG-2 改走 canonical(使用者定:正確性優先,不保留簡化版)
- `momentum/FeatureEngineering/atomic/volume_indicators.py`:**Klinger、ForceIndex 改成文獻標準 canonical 公式**(Klinger:用 trend-aware VF 累積 + 標準 EMA(34,55);ForceIndex:標準 = EMA13 平滑的 (close-prev_close)*volume)。**EOM 已 corr 0.9999 等同,可不動**(若僅 scale 差,記錄即可)。
- **oracle 必獨立**(§B1.2):`tests/references/volume_indicators_ref.py` 改成**獨立實作 canonical 公式**(照文獻,不得 import 被測 volume_indicators)。test_handcoded_reference 改驗「impl == canonical reference」。
- **驗因果無 look-ahead**:截斷尾段→前段值不變的小不變量(或確認只用 trailing/EMA、無 center/shift(-1))。
- 移除 `variant=simplified` 標記(現在是 canonical 了);若決定保留任何簡化欄須改名+標記,但預設不留。
- **§G**:Klinger/ForceIndex 值會變→列入 Affected Column Closure + 新舊差異表(供三方簽核)。
- mutation 探針:Klinger 公式注入錯誤(如 VF 符號翻轉)→ test 必紅(test_mutation_*)。

## 2. correctness-mode 補全(Codex 指:現只測 MFI 一路)
- `tests/feature_engineering/atomic/test_correctness_mode.py`:加**參數化 fault-injection 涵蓋全部 8 engine**(每 engine 刪一個已登錄指標 from map + clear registry + reinit → compute_all 在 correctness mode 必 raise)。
- 補 `def test_mutation_*` 探針(§B1.1):自證「correctness mode off→warning 不 raise(基線)、on→raise(變異)」可證偽。

## 3. 補 test_bug1_beta_correl 缺的探針
- `test_bug1_beta_correl.py` 加 `def test_mutation_*`:把 BETA input_type 還原成 close_volume(回歸成舊 bug)+ clear registry → 雙 oracle 測試必紅。

## 收尾
- **自驗**:`bash scripts/mutation_probe_check.sh tests/feature_engineering/atomic/` 須 PASS;附輸出。
- 更新 `handoffs/20260627-FF-DEEPAUDIT-B1-RESULT.md`(BUG-2 canonical 差異表、correctness-mode 覆蓋、探針證據)。
- 跑會寫 tests/golden 的測試後 git checkout 還原。完成 STATUS: DONE/BLOCKED。兩輪解不了→BLOCKED 不 solo。
