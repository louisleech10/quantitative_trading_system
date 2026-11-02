# ICPERF v5.59／v5.60 收案前重型受影響測試（TEST_SELECTION §4）歸因

命令：`runs/icperf/task04/v559/cmd_heavy.txt`（經 `scripts/run_watched.py`，log `heavy.log`）；估時收據
`handoffs/run_receipts/20261102-icperf-v559-heavy-affected-estimate.json`（估 21,000 秒）。

結果：`6 failed, 38 passed, 56 warnings, 1 error in 19512.93s (5:25:12)`；run_watched `exit rc=1（19521 秒）`。

| 節點 | 失敗訊息（heavy.log 行） | 歸因 | 依據 |
|---|---|---|---|
| test_icperf_gate.py::test_boundary_02_frozen_baseline_content_complete | :1384 凍結檔逐特徵欄位結構缺 `ic_autocorr`／`ic_autocorr_reason` | v5.58 (w) summary 增欄，待重凍（HANDOFF 既定「修後重凍受影響 §G 項」） | .testreg 前次 2026-11-01 亦 failed |
| test_icperf_gate.py::test_freeze_reproducible | :1395 現行多出 `/summary_table/ic_autocorr`、`ic_autocorr_reason` 兩鍵 | 同上 | 差異只在兩新鍵（22 項相同） |
| test_la0_lookahead.py::test_after_golden_deep_equal | :1410 golden sha 不符 | 早於 v5.59 即紅（非 v5.59 造成）；確切改值來源未查證——log 只給 sha 不符，須以 golden 逐欄比對才能歸到哪一批，排入重凍前處理 | .testreg 2026-10-30、10-31、11-01 皆 failed |
| test_la0_lookahead.py::test_after_golden_split_off_deep_equal | :1475 同上 | 同上 | 同上 |
| test_failopen_correctness.py::test_v6_independent_asof_oracle_matches_multi_tf_columns | :629 `GenerationMemoryBudgetExceeded`：Calib.group_reduce:1h_L2_WorldQuant 計畫 18,310,052,224 B > 上限 18,191,536,128 B | 他票既存（NUMVIEW 記憶體預算，`memory_budget.py` 首見 e9f59f9a 2026-10-25）；失敗點在 `feature_factory._resolve_public_window` 校準域，ICPERF 對 FF 只改 `labels/label_generator.py` | 前次通過 2026-10-19（早於記憶體預算引入） |
| test_preprov_survivor_identity.py（setup ERROR） | :39 契約 `run_identity_keys` 多 `route_identity`、`algorithm_id` | 他票既存（NUMVIEW e9f59f9a 增身分鍵，測試 oracle 未同步） | .testreg 前次 2026-11-01 亦 error；ICPERF 工作樹未動 run_provenance 契約 |
| test_testreg_write_guard.py::test_boundary_07g_widely_imported_helper_decrease_wall_clock | :1522 牆鐘中位 14.58 秒 > 5.0 | 治理效能斷言既存紅 | .testreg 2026-10-27、11-01 皆 failed |

副作用：la1 b4 測試改寫 `tests/golden/la1/inputs/BTCUSDT_1h_4a8a0b3726cc906ab3534994605e77f5_fallback_tail100.h5`
（還原用之 `git checkout` 被權限擋 ⇒ 提交以 `git commit --only` 明列檔案排除之，待使用者還原）。
