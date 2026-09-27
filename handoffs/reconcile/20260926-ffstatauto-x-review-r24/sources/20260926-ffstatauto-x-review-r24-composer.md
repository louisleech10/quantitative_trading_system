# FF-STAT TODO 同步審查 r24 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R24  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R24-BRIEF.md`  
標的：`git show b0cf1d8d`（manifest v44 TODO 同步、Task 2.3／2.4 具名測試、契約 JSON、收據腳本）；SPEC v44。唯讀；探針與 pytest 暫存 `/tmp/ffstat-r24-*`（不含家族名）。

## COMPOSER-R24-P1-01

**斷言**: Task 2.3 ② 之具名驗收 `test_nan_propagation_inventory_complete` 要求盤點收據 JSON 已落於 `handoffs/run_receipts/`，且收據步驟集合須覆蓋 `_ast_step_functions()` 之全集；現況無任何 `*-ffstat-nan-propagation-inventory.json`，`nan_propagation_classes.json` 僅登記 2 步，收據產生器 `inventory` 實跑 rc=1（40+ `unclassified`），故 gate_cmd 內該測試之失敗原因為缺收據／盤點未完成，非 brief fact-verified 所列之 `NotImplementedError` 純函式紅，TODO 對 SPEC Task 2.3 ② 追溯不可放行實作。

**碼證**: `glob handoffs/run_receipts/*-ffstat-nan-propagation-inventory.json` → 0 檔；`venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete -q --tb=line` → `AssertionError: 缺盤點收據（SPEC Task 2.3 檔案段）` rc=1；`venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-r24-inv-out.json` → rc=1，輸出 `"unclassified"` 含 `RollingAggregator.compute_all`、`TimeframeAligner.align_to_primary` 等 40+ 項；`tests/_golden/ffstat/nan_propagation_classes.json` 之 `"steps"` 僅 2 鍵。  
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:173  
MUTATION: 維持 `handoffs/run_receipts/` 無 `*-ffstat-nan-propagation-inventory.json` 且 `nan_propagation_classes.json` 只保留 2 步 → 重跑上述 pytest 必紅。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#7e8c0622c8e5; docs/manifests/FFSTAT.json#b6a07501343c; tests/feature_engineering/test_ffstat_stable_start.py#753f6ed4b3d9; tests/_golden/ffstat/nan_propagation_classes.json#6c1cb63d6261; handoffs/20260926-FFSTATAUTO-X-REVIEW-R24-BRIEF.md#50abab52d33c

正文：Task 2.3 ②（SPEC `:131`）與 §P 清單要求 NaN 傳遞盤點可證偽；manifest `coverage_risk` 已對位 `test_nan_propagation_inventory_complete` 與 `stable_start_receipts.py inventory`，但 b0cf1d8d 未提交盤點收據、分類 JSON 仍為 stub，與「具名測試恰覆蓋一驗證項且實作前紅因正確」不一致。**修法**：依 `_ast_step_functions()` 與 SPEC ② 類別，補齊 `tests/_golden/ffstat/nan_propagation_classes.json` 逐步驟 `propagates_nan`／`class`／`evidence`；執行 `venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out handoffs/run_receipts/<日期>-ffstat-nan-propagation-inventory.json` 直至 rc=0；再跑 `test_nan_propagation_inventory_complete` 應轉為僅因 L1 整合路徑 `NotImplementedError` 而紅（若仍紅）。**可行性**：已用同一 `_ast_step_functions` 產出 `/tmp/ffstat-r24-inv-out.json`，僅因分類缺漏 rc=1；補 JSON 後不需全設定 FF run，屬機械盤點（秒級）。

---

## 必答

1. **(1a)** 本家 r23 無 P0／P1 待閉；`CODEX-R23-P2-01` 為 codex 家族條目。**(1b)** v43／v44 §G⑦ 已逐字寫入 `validate_continuity=False` 與缺口收據（`docs/FFSTAT_SPEC.md:94`）；`ffstat_helpers.dual_start_report` 建 factory 時傳 `validate_continuity=False`（`:397`）；manifest `coverage_risk`／`risk_mitigation` 對位同一參數——r23 synth 採納之操作序列在 TODO 層已閉合。

2. **(2a)** **不完整**（見 P1-01）。**(2b)** 缺漏：SPEC Task 2.3 ②「盤點收據涵蓋 AST 步驟全集」↔ `test_nan_propagation_inventory_complete`；缺 committed 收據 + 完整 `nan_propagation_classes.json`。非阻擋但須記：manifest 註 ⑦¹⁷／⑦¹⁹ 無獨具名 mutant、Task 2.3 ⑪ 由 ①④⑤ 路徑涵蓋（`FFSTAT.json` `coverage_risk`），屬 SPEC 允許之共享覆蓋，不列 P0／P1。

3. **(3a)** brief 第一條 assumed（每驗證項恰一具名測試）→ **不成立**（P1-01）。第二條 assumed（實作後 mutation 真翻轉）→ **本輪未否證**；三支純函式 mutation（⑦¹¹／⑦¹⁸／⑦¹²）實跑 pytest 為綠，因 `stable_mask.py` 已實作校準列／死欄／hash 純函式而主整合測試仍 NIE，與 brief「實作前無法驗」一致。**(3b)** `pytest …::test_mutation_calibration_rows_not_masked_is_caught` → passed rc=0；inventory／盤點 pytest 見 P1 **碼證**。

4. **(4a)** brief「我沒查」：**①** `_ast_step_functions` 前綴——**部分命中**：`TimeframeAligner.align_to_primary` 已列舉，私有 `_merge_asof_align*` 未列（前綴不符）；是否漏算取決於 SPEC 是否只要求公開入口，不升 P1。**②** 預設全設定 `dual_start_report` 8GB 可行性——**未跑**（brief 排除）。**③** `freeze_baseline_nostart.py` 於 `02350721^` API——**未跑** worktree。**④** metadata 鍵——**未命中**：`contract.json` 含 `stable_start`、`warmup_doubling`、`column_set_reasons`、`start_dependent_columns`。**⑤** `test_every_l1_output_column` 簽名——**未命中**：`:479-480` 使用 `_layer0_data_ingestion`／`_layer1_atomic_indicators`，與他檔 ffstat 測試一致。**(4b)** 見上；① 碼證 `test_ffstat_stable_start.py:187-204` 與 inventory `unclassified` 列表。

5. **(5a)** v44 **`effective_output_start` 事實更正成立**。**(5b)** `momentum/FeatureEngineering/feature_factory.py:4270` 仍寫入 `effective_output_start`；`test_ffstat_calibration.py::test_boundary_11_user_start_source_is_user`（`:375-379`）與 `test_ffstat_stable_start.py::test_boundary_25_user_start_source_user`（`:523-528`）斷言 user 來源與 per_column 不寫鍵（`:250`）；與 v44 條文一致。

6. **(6a)** **`VERDICT: blocked`**（P1-01）。**(6b)** `COMPOSER-R24-P1-01`。

---

ASSUMPTIONS_VERIFIED: 已讀 brief、template、governance_verdicts、v44 SPEC §P／Task 2.3②、manifest b0cf1d8d、r23 synth、contract.json；未改 source  
TESTS_RUN: `bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → PASS rc=0；`pytest …::test_nan_propagation_inventory_complete` → FAIL 缺收據 rc=1；`pytest …::test_no_start_stationarity_off_stable_values_unchanged` → FAIL 缺 baseline_nostart rc=1（預期 impl 前收據步驟）；`pytest …::test_every_entry_has_closed_class_and_period_keys` → FAIL ADX 缺 period_keys rc=1（brief fact）；`stable_start_receipts.py inventory --out /tmp/ffstat-r24-inv-out.json` → rc=1；`venv/bin/python scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → rc=0；`bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r24-composer.md --family composer --round-id 39c1976f-fd83-4260-8fe7-3ad31cf99b0c`（收尾）  
FAILURES_SEEN: none（探針失敗為預期否證）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r24-composer.md  
TMP_CLEANUP: `rm -f /tmp/ffstat-r24-*` 被 PreToolUse 安全閘拒絕（檔可能仍在）；`/tmp/claude-501` 保留

VERDICT: blocked
BLOCKED-BY: COMPOSER-R24-P1-01
CLOSED:

STATUS: DONE
