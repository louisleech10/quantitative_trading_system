# 派工:FF 深稽 B2 實作(Composer 2.5)— 全鏈 bar 級截斷 MR

讀 `docs/FF_DEEPAUDIT_P0_SPEC.md` §P Phase 2 + `docs/FF_DEEPAUDIT_P0_TODO.md` Task 2.1/2.2。本批做 Task 2.1+2.2(同檔 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`)。**不碰 B1/B3**。

## §0 鐵律(同 B1)
- momentum logging 用 momentum.core.logging;kline 用 storage manager;禁合成 fixture;mutation TDD-first;不放寬斷言;env 已修。

## Task 2.1 全鏈 bar 級截斷不變量
- 真 kline 跑 `momentum/FeatureEngineering/feature_factory.py::generate_features`,截斷尾 k bars。
- **warmup = `estimate_max_warmup_bars(config, primary_tf, training_tfs)`**(簽名已驗:warmup_window.py:313),禁 data-dependent 首全填列。
- **四段斷言**(照 SPEC):① columns gate;② values gate 共同 index `[warmup:]`(到 trunc 末列止)exact,不在交集後再 `:-k`;③ warmup 區 `[0:warmup)` NaN mask 一致;④ metadata gate 只比 schema/config_hash/symbol/tf,row_count/data_range assert 截斷後預期非 ==full。
- 單 primary-TF + production preset 全欄。**不宣稱取代 P0-FF-3**。

## Task 2.2 尾端擾動 MR(同檔)
- 尾 k bar OHLCV ±1e6 → 截斷點前列不變;warmup 區另 assert。

## mutation(SPEC §B4):3 mutant 必 FAIL — numba_rolling center=True / causal_winsor 全量 fit / L4 lag shift(-1)(若存在)。各附 pytest fail 摘要。

## 收尾:交接寫 `handoffs/20260627-FF-DEEPAUDIT-B2-RESULT.md`。跑後 git checkout 還原 tests/golden artifacts。完成 STATUS: DONE/BLOCKED。

## 補充(2026-06-28 機制硬化後)
- 本批測試須過**硬化** `bash scripts/mutation_probe_check.sh tests/feature_engineering/`(每正確性測試附自證 `test_mutation_*`:基線綠→注入壞改→真紅→還原;非空心/非偽raises;oracle 獨立非從 generate_features 自身衍生)。收尾前自跑須 PASS,附輸出。
- 3 個 C2 mutant(numba_rolling center=True / causal_winsor 全量fit / L4 shift(-1))各做成 in-file test_mutation_* 探針。
- 跑 tests/golden 後 git checkout 還原 artifacts;ff_deepaudit/ 已 gitignore。
