# IC1EB B2 Code Review — Codex（非實作者）

審查範圍：未 commit B2 指定 diff；依 TODO Phase 2、SPEC D-C～D-G/consumer map；實作者自報未作證據。(VERIFY-EXEMPT:doc-example:agent-inline-receipt-below)
1. PASS — FDR 時序：`apply_fdr` 在 2294 對全欄 p map 執行，先於 summary/任何 threshold（2360/2370）；無子集 FDR production 路徑。
2. PASS — α 六格：sufficient/marginal=default，low_confidence=max(default,0.10)；on/off 閘分別用 q/raw p；`alpha_source/selection_mode` 專測通過。
3. PASS — SelectionScope 核心：實跑 constant-feature 收據為 universe=4/evaluated finite-p=3/n_tests=3；`full` 契約擴充與 n_tests+1 raise 通過。
4. FINDING [P1, 10/10] — `refilter()` production caller（orchestrator.py:1325-1331）未傳/快取 split_context（cache:2564-2576）；原 OOS run 會改用全樣本 HAC/FDR並把 scope 標成 full，與 test-scope ICIR 混用。
5. FINDING [P1, 10/10] — full scope 在 orchestrator.py:2313-2327 新造 `symbol="UNKNOWN"`；同 timestamp/config 的不同 symbol 得相同 scope/base-universe identity，違反 TODO「沿用 fallback 或 raise、不得新造」及可稽核隔離。
6. FINDING [P1, 10/10] — reporter CSV 將既有 `p_value` 經 `_jsonable_scalar`（ic_reporter.py:169），NaN 從舊 `nan` byte 變空欄；T-2.4 只驗 header 順序（test:517-570），沒有規格要求的舊欄 byte golden。
7. PASS — reporter metadata 僅導出 canonical `significance.fdr.{enabled,method,alpha_effective}` 與指定 sibling keys；未見 report alias。
8. FINDING [P1, 10/10] — M-B test 的 `0.7*factor+sqrt(1-0.7²)*eps`（test:241）產生 feature pairwise ρ≈0.49，不是要求的 ≈0.7；實跑為 0.4811。`binom` 未使用，允收帶是任意 0.20（:272），非 §0 要求 binomial 95% CI。
9. FINDING [P1, 9/10] — n_tests 縮水「mutation」只把錯路徑包在仍為綠的測試內並斷言較差，未對 production wiring 作 mutation 後取得真紅；不符合派工明列的「非綠測試包裝」。
10. PASS — 正確重跑 ρ≈0.7 場景（loading=sqrt(0.7),40 seeds）：rho_mean=0.70047（range 0.65932–0.72904），mean FDR=0.07193，數值本身入 α=0.10。
11. FINDING [P1, 10/10] — Grok 本地重凍 `tests/golden/ic_phase1_1a_cut1` 不合法：B2 scope 未授權且兩個 frozen metadata hash 均失配；old declared 963ba4…/actual bc710c…，new declared 946591…/actual 21ca4f…，不能作 1015 綠的可信 baseline。
12. PASS — M-H：`rg compute_pooled...|compute_ic_statistics|_collect_values momentum api` 僅 deprecated 定義/內部 helper，無 production caller；ghost filter 0 hit。

TESTS_RUN：`OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_1eb_b2_wiring.py -q`→12 passed；scope+validator→24 passed；reporter/export→19 passed；orchestrator→44 passed。
專項 receipts：finite-p strict subset 通過；現有 M-B test ρ=0.48108；修正 ρ 場景 FDR=0.07193；baseline 雙 hash match=False；l65 inventory 未被覆寫，未 restore。
編排端既驗事實：1015 綠/G-1 五 hash MATCH/斷言刪除限 Task2.5，均接受為外部事實但不足以消除以上 findings。
正在做：審查完成。待辦：上述 P1 由實作者修正後重審。阻塞：scope 漂移、baseline 失真、M-B/T-2.4 驗收缺口。本次決策：不採信 RESULT 自報。踩坑提醒：gitignored golden 仍可被重寫而逃過 git status。
VERDICT: BLOCK(refilter OOS scope 漂移；full scope 假 symbol；reporter 舊欄 byte 改變；M-B/縮水 mutation 未按規格驗；cut1 frozen baseline 雜湊失效且重凍越界)
