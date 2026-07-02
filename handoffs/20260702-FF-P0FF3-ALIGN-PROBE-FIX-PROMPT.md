# P0-FF-3 align mutation 探針修牙指派（Composer 2.5 讀此檔執行）

## 背景（事實,附出處）
- P0-FF-3 多 TF 全鏈截斷 MR:`tests/feature_engineering/test_ff_multitf_truncation_mr.py`(WIP commit `9f9839d`;設計 reconcile `handoffs/20260630-FF-P0FF3-RECONCILE.md` 雙戳記有效)。
- 首次真跑全 mutation(bgr3kn4p6,2:25:45):center/winsor/lag 3 探針過;**`test_mutation_align_lookahead_fails` 與 `test_mutation_align_lookahead_with_tail_perturb_fails` 兩探針 FAILED——`DID NOT RAISE AssertionError`**。
- 根因(traceback b8uou6xj6 定性):探針 patch `build_asof_index_map` 注入 +1 forward as-of 偏置,但**對稱套在 full 與 truncated 兩跑**→兩邊同樣偏移→比較區 `[warmup:n_trunc)` 內 MR 斷言(`_assert_truncation_invariants`)差異抵消→注入的 look-ahead 完全測不到=探針無牙齒。
- 委員共識修向(HANDOFF 2026-07-01):**(A) 不對稱注入**——只 patch 單側(如只 truncated 跑帶偏置),讓 MR 比較真的看到差異;或 **(B) oracle 直斷**——不靠大抽樣 MR,直接斷言指定 coarse(4h/12h)欄在**已知 12h 邊界 index**上的值/source-index:注入 +1 偏置後該欄必須拿到「未來一根」的值,斷言其與正確值不同(可證偽、失敗訊息可讀)。

## 任務
1. 逐字讀上述兩探針現實作 + `ff_truncation_mr_helpers.py` 對齊路徑(`build_asof_index_map` 的用法),確認根因描述與程式碼一致;不一致→STATUS: BLOCKED 附證據,不硬改。
2. 依修向 A 或 B(可併用;選擇附一句理由)重寫兩個 align 探針,使:**無注入=綠(基線不誤殺)、有注入=紅(AssertionError,訊息指出哪欄哪 index)**。
3. 探針仍須過 `scripts/mutation_probe_static.py` 靜態檢查(非空心/非偽自證);不得改 production 程式碼、不得改其他探針/主 MR/perturbation 測試、不得放寬任何既有斷言。
4. **驗證邊界(鐵律:改完即交,勿硬撐自驗)**:generate_features 全鏈 ~25分/次,你**不要跑全鏈慢測**。只做:py_compile/pytest --collect-only、`mutation_probe_static.py` 過、以及若能構造**小型合成快徑**(僅驗探針注入邏輯方向,明標「smoke,非驗收證據」)可跑。真驗收(receipt 版 mutation_probe_check 全 5 探針)由編排端跑。

## 收尾
寫 `handoffs/20260702-FF-P0FF3-ALIGN-PROBE-FIX-composer.md`:修向選擇+理由、改動摘要、TESTS_RUN(貼原文,明標哪些是 smoke)、FAILURES_SEEN、SCOPE_CHANGES。**報告禁用「已驗/真紅」字樣**(你沒跑慢測,無權聲稱)。最後一行 STATUS: DONE 或 STATUS: BLOCKED — <原因>。
