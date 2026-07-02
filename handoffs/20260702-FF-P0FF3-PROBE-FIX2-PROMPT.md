# P0-FF-3 align 探針 BLOCKING 修補（Composer 2.5 讀此檔執行）

Codex test-design review 抓 1 BLOCKING(handoffs/20260702-FF-P0FF3-PROBE-REVIEW-CODEX.md,逐字讀)。

## BLOCKING（必修）
兩個 align 探針 `test_mutation_align_lookahead_fails`/`..._with_tail_perturb_fails`(test_ff_multitf_truncation_mr.py:156-176/191-212)把 `_assert_align_coarse_boundary_lookahead_detected` 與 `_assert_truncation_invariants` 一起包進**同一個寬 `with pytest.raises(AssertionError)`**。因 oracle 在「找不到 coarse 欄 mismatch」時也 raise AssertionError(ff_truncation_mr_helpers.py:1259-1263),所以若注入失效(monkeypatch 沒生效/side 被移除),pair 退化為 baseline、oracle 報「no mismatch」、探針**仍通過**=無牙齒卻綠(錯誤原因通過)。

## 修法（Codex 指定 shape,照做）
1. 先 build 注入後的 pair。
2. `_assert_align_coarse_boundary_lookahead_detected(pair, ...)` **移出 `pytest.raises`**——它須**正向通過**(=真的偵測到注入造成的 coarse 欄 mismatch);若注入失效→這行直接 fail→探針紅(正確:無牙齒=紅)。
3. 只把 `_assert_truncation_invariants(...)` 包進 `pytest.raises(...)`(或斷言特定 MR 失敗訊息)——look-ahead 應使不變量失敗。
4. 兩個 align 探針都改;不動 baseline 測試(test_c3_*)、不動其他探針(center/winsor/lag)、不放寬既有斷言、不改 production。

## 驗證邊界（勿硬撐慢測,改完即交）
- generate_features 慢測 ~25分/探針,**你不跑全鏈**。只做:py_compile/collect-only/mutation_probe_static.py 過;可構造小型 synthetic smoke 驗「注入失效→探針紅、注入生效→探針綠」的邏輯方向(明標 smoke 非驗收)。真驗收(receipt 版 mutation_probe_check 全5探針)由編排端跑。
- 探針須仍過 mutation_probe_static(非空心/非偽自證)。

## 收尾
寫 handoffs/20260702-FF-P0FF3-PROBE-FIX2-composer.md(修法+TESTS_RUN 明標 smoke/FAILURES/SCOPE)。禁「已驗/真紅」字樣。最後 STATUS: DONE 或 BLOCKED。
