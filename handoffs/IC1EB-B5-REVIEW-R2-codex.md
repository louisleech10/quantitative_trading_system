# IC 1e+1b B5 R2 複驗 — Codex

前置：`reconcile_body_hash.sh handoffs/IC1EB-RECONCILE.md`=`b77932d8…`，與 codex/composer APPROVED 雙戳一致。

1. **F1 — CLOSED**：`run_xsec` 現只 catch `(FileNotFoundError, OSError)`；反例把 reader 路徑改丟 `ValueError("logic bug")`、premat 設為一被呼叫即失敗，實跑結果 `ValueError` 原樣上拋且 `fallback_calls=0`。任意邏輯 Exception 不再被 fallback 吞掉。

2. **F3 — CLOSED**：三種 kernel NaN（樣本不足/全 NaN/std=0）都經 `_assert_nan_p_fails_stage5_gate` 斷言 `_passes_threshold=False`，並以 `_apply_thresholds` 證 feature 落入 `removed_features.p_value`；`pytest ... -k g3 -q`=`4 passed in 10.21s`。另以缺空 `expected_raise_runs` 直接重打，得到 `_pytest.outcomes.Failed`，訊息含 artifact missing，非 SKIP。

3. **F5a 現行 freeze 腳本 — CLOSED**：讀碼確認 old/new request 與 meta request 分別寫死 `ic_train_test_split=False/True`；兩者先重用既有 h5+meta inputs；new reproduction command 指向 `freeze_baseline_new.py`。現行 meta 的 baseline SHA 實算相符（old `fd932a6e…`、new `35e15ce9…`），request/repro 亦各自正確。

4. **F5b 現行兩態可重產 — CLOSED**：`pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q` 實跑 `2 passed in 40.64s`；old scope=null、new scope=test，均與顯式旗標及現行 golden 深比較一致。

5. **F5c README/歷史 provenance — STILL-OPEN（BLOCKING）**：撤回「預設漂移」正確；`git show d3b2dff:...ic_config_schema.py` 證預設自引入即 `True`，854d444 測試也確實以 `split_on=False` 深比 old baseline，故 old artifact 的 flag-off 語意有碼證。quarantine README 的 SKIP/B5 待辦也已更新為已處置。
   但 `original_regen/README.md` 仍宣稱 854d444 與 c0b29ac 各重生且 normalized 內容相等，目錄仍只有單一 artifact，沒有兩次 run 的 commit→hash/normalized-hash receipt；其歸檔 `baseline_meta.json.request` 與 `reproduction_command` 亦仍未記 `config_override=False`，和 README 所稱重生程序互相矛盾。`f4046d33…` 單一 SHA 不能證明兩 commit 相等。故「含 provenance／雙 commit 交叉已證」仍是不受現存 artifact 支撐的 claim。

6. **其餘 PASS 抽查 — CLOSED**：G-1 快顆+13-run coverage 實跑 `2 passed in 16.08s`；baseline manifest 仍含 13 runs 與 expected-raise receipt。R1 的 G-2 數值與 newpath manifest hash 鏈本輪未發現碼變更；完整 newpath 逐檔重 hash 超過 60 秒後終止，未新增通過 claim。

ASSUMPTIONS_VERIFIED: reconcile 雙戳；F1 非前置 Exception 不 fallback；F3 NaN 接真 p 閘且缺 receipt 轉紅；現行 freeze flags/inputs/repro/meta SHA；1a 兩態 golden；歷史 README 可驗證性。
TESTS_RUN: F1 ad-hoc counterexample PASS；G-3 4p；missing-receipt mutation red；G-1 fast+coverage 2p；1a golden 2p；static SHA/flag/repro probe PASS。
FAILURES_SEEN: newpath 13-report 完整逐檔 hash probe >60s 終止；未據此宣稱重驗通過。
SCOPE_CHANGES: 新增本檔；測試流程另覆寫 gitignored `data_cache/reports/ic_{report,filter_log,summary}_ic_gatekeeper` 三輸出，無可用 tracked 版本可 restore；tracked l65 inventory 未變。
NUMERIC_OR_SCHEMA_IMPACT: 審查未改生產數值/schema；上述 report 是測試副作用。

VERDICT: BLOCK
