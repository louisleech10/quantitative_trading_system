# IC1EB B3 Code Review — Codex（非作者）

範圍：未 commit 的 `ic_filter_orchestrator.py:analyze_cross_sectional`、B3 xsec 測試、cut1 簽名適配；依 SPEC §A/D-H(v2)、TODO Task 3.1。

1. **FINDING — horizon 原始欄名解析僅 labels_path 完整，in-frame `return_N` 不完整。** labels_path 在 `_label` 前以 `label_series.name` 解析（1026-1035）為 PASS；但 in-frame 候選硬編為 `return_1`（1038），未接受 resolver 本已支援的任意 `return_N`。可證偽反例：MultiIndex frame 僅含 `alpha`+`return_5`、無 labels_path，會在 1045-1046 raise，而非產出 `label_horizon=5`、`maxlags>=4`。這違反 frozen SPEC §ADV CODEX-3「in-frame `return_N`→同」及審查要求兩分支。
2. **PASS — h=None fail-closed。** 1148-1152 令 t/p NaN，1178-1196 令 q NaN，1238 標 `horizon_unresolved`；顯著性未消費 1058-1060 的 structural h=1。可證偽反例 `label` 欄已由 `test_t31c_horizon_unresolved_p_all_nan` 覆蓋：任何有限 p/t/q、非零 n_tests 或 metadata false 都會紅。
3. **PASS — t_stat 已由 HAC 取代 i.i.d.。** 387-420 使用 Bartlett NW、`L=max(auto_bw,h-1)`、Student-t p；現場測試與 statsmodels `use_t=True` oracle 對齊。mutation receipt log 真實顯示 iid 替換後 `test_t31a...` 於 line 110 紅、還原後綠，不是摘要自稱。
4. **PASS — resolver fallback-1 已收斂。** 375-384 僅委派 `_resolve_label_horizon_from_column`，解析失敗回 None；舊 regex+return 1 不存在。可證偽反例 `_label`/`label` 皆由測試斷言 None。
5. **PASS — FDR 覆蓋全 feature。** 1178-1196 在排序/任何門檻前把 summary 全列送 `apply_fdr`；finite p 定義 n_tests，NaN 保位。可證偽反例 `test_t31_fdr_q_matches_apply_fdr` 對全表重算 q 與 n_tests。
6. **PASS — 無新增門檻、排序未漂。** 1198-1206 唯一排序鍵仍為 ICIR；無 `_apply_thresholds`/passed 子集，1234-1235 input=output。可證偽反例測試斷言輸出 feature 數與 ICIR 降序；編排端五 hash/ICIR raw hash MATCH 與讀碼一致。
7. **PASS — M-J labels_path 真路徑可達且未加單軸支援。** 測試 157-199 以符合契約的 MultiIndex labels_df 經 monkeypatched loader 進完整 `analyze_cross_sectional`，`return_5→L>=4`；1011-1015 仍拒單軸。rename mutation receipt 於 line 184 真紅、還原後綠。

簽名適配：`test_ic_1a_cut1_oos.py` 只補既有 stage5 新必需 `metadata.symbol`，未放寬斷言；相關回歸通過。
實跑：`OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_1eb_b3_xsec.py -q` → 8 passed；`... pytest tests/momentum/test_ic_cross_sectional_cut2.py tests/momentum/Analysis/test_ic_1a_cut1_oos.py -q` → 20 passed；`git diff --check -- <兩 tracked 檔>` → clean。未重跑 1023 全套，採編排端既有 receipt。

VERDICT: BLOCK(in-frame 一般 return_N 未被候選辨識，未完成要求(1)的第二分支)
