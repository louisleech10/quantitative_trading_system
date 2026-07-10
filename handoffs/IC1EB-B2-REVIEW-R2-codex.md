# IC1EB B2 R2 複驗 — Codex

範圍：重打 R1 `IC1EB-B2-REVIEW-codex.md` 六條 P1；FIX1 自報僅作線索，結論以本輪讀碼／實跑為準。

1. **CLOSED — refilter OOS scope**：production cache 保存 `split_context`，`refilter()` 傳回 stage5/6/7。Receipt：`OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_1eb_b2_wiring.py::test_t22_refilter_oos_scope_remains_test -q` → `1 passed in 0.70s`；public refilter 後 `split_label/scope=test`、q byte-equal、cache identity 保留。
2. **CLOSED — UNKNOWN→raise**：`_resolve_scope_symbol` 僅取 allowed/split/metadata 真 symbol，缺值 `ValueError`，不同 symbol hash 分離。Receipt：`...pytest tests/momentum/test_ic_1eb_b2_wiring.py::test_t23_full_scope_refuses_fabricated_unknown_symbol -q` → `1 passed in 0.64s`。
3. **CLOSED — reporter 舊欄 byte**：CSV `p_value` 保留 raw float；golden 小樣本舊 14 欄前綴逐 byte 比對，NaN token=`nan`（非空欄），新欄只追加。Receipt：`...pytest tests/momentum/test_ic_1eb_b2_wiring.py::test_t24_reporter_new_columns_and_old_order_byte -q` → `1 passed in 0.58s`。
4. **CLOSED — M-B ρ+95% CI**：碼中 loading=`sqrt(0.7)`，上界=`binom.ppf(0.975,40,0.10)/40`。Receipt：`...pytest tests/momentum/test_ic_1eb_b2_wiring.py::test_t22a_mb_fdr_control_independent_and_correlated -q` → exit 0；同 seed production 數值 probe：independent mean FDR=`0.142708`、correlated=`0.071931`、rho mean=`0.703107`（min/max=`0.592773/0.762066`）、95% upper=`0.20`、各 40 seeds。
5. **CLOSED — n_tests 縮水真紅**：永久 production 守衛 `...pytest tests/momentum/test_ic_1eb_b2_wiring.py::test_t22a_production_fdr_uses_full_universe_n_tests -q` → `1 passed`（const 僅 universe，finite-p 才 evaluated，三者同源）。另以 `inspect.getsource` 僅在記憶體 mutation production stage5：BH/evaluated 同縮至 raw p<0.2；exit 1，M-B 消費未校正列時 `TypeError: np.isfinite(None)`，確為 production mutation 真紅且 workspace 零改檔。FIX1 原 receipt 的完整 shrink 另為 mean FDR=`0.378069` > `0.20`。
6. **CLOSED — 1a 隔離**：原兩 baseline 路徑不存在且 `.gitignore:163-164` 命中；`git cat-file -e c0b29ac:<old baseline>` exit 128，證實無 tracked 原檔可 restore。`...pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q` → `2 skipped in 0.07s`，明示 absent，非 PASS 假綠。quarantine SHA=`bc710c…/21ca4f…`，與 meta 宣告 `963ba4…/946591…` 失配；README 如實記越界重凍、原件滅失、SKIP 與 B5 由 pre-B2 `c0b29ac` 重生/雜湊比對義務，處置合理。

ASSUMPTIONS_VERIFIED: c0b29ac 是 B1 commit、位於 B2 前；quarantine 內容就是 R1 失配兩檔；所有六條均由現碼或本輪命令驗證。
TESTS_RUN: 上列 6 個顯式 pytest 節點（5 passed、2 skipped）＋M-B 固定 seed 數值 probe＋記憶體 production mutation 真紅。
FAILURES_SEEN: mutation probe 第 1 輪腳本縮排錯；第 2 輪成功進 production mutant 並如預期 exit 1；依 debug 上限不追求改成另一種紅訊息。
SCOPE_CHANGES: 僅新增本報告；未改 production/tests/data_cache；測前後 `git status --short` 相同，l65 inventory 未新增差異、無需 restore。
NUMERIC_OR_SCHEMA_IMPACT: 本輪無；審查確認 FIX1 僅修 OOS scope identity、fail-closed symbol 與 legacy CSV NaN byte。
VERDICT: PASS
