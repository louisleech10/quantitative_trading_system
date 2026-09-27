# FF-STAT TODO 審查 r25 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R25  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R25-BRIEF.md`  
標的：`git show 3761b465`（r24 收斂修補）；唯讀；探針暫存 `/tmp/ffstat-r25-*`（路徑不含家族名）。

## COMPOSER-R25-P1-01

**斷言**: Task 2.3 ⑫ 新增之四支 `run_ic_first` 具名測試向 `FeatureFactory.run_ic_first()` 傳入 `start_date`／`end_date`，但 production 簽名無該參數，六支相關用例（含三參數化結束態）在呼叫 helper 前即 `TypeError`，無法驗收 SPEC v29–v31。

**碼證**: `venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_run_ic_first_requires_start_date_when_stationarizing tests/feature_engineering/test_ffstat_stable_start.py::test_run_ic_first_rejects_config_hash_when_stationarizing tests/feature_engineering/test_ffstat_stable_start.py::test_run_ic_first_uses_own_window_not_previous tests/feature_engineering/test_ffstat_stable_start.py::test_run_ic_first_restores_state_on_all_endings -q --tb=line` → 5 failed，首錯 `TypeError: run_ic_first() got an unexpected keyword argument 'start_date'`（`:595`、`:609`、`:634` 經 `ffstat_helpers.py:232`）。brief「我沒查」①：`RunLease` 無自訂 `__repr__`，`expected_hash in str(lease)` 即使執行到亦無法綁定 lock 檔名中之 hash（應讀 `lease.path.name`）。  
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:2384  
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:595  
MUTATION: 自 `run_ic_first` 簽名刪除任何視窗參數並維持測試仍傳 `start_date=` → 上述 pytest 恆 TypeError，⑫ 映射仍不可執行驗收。

**類別**: code-contract

**來源摘要**: momentum/FeatureEngineering/feature_factory.py#47f362f67de2; tests/feature_engineering/test_ffstat_stable_start.py#a6a0a1cb0339; momentum/FeatureEngineering/run_locks.py#51e3f55c9a9a; docs/manifests/FFSTAT.json#87e6acfe46b5

正文：r24 codex P1-04 要求 A/B 窗、`config_hash` 拒收與 state 還原之具名測試；3761b465 已寫測試但未對齊 API（`run_ic_first` 僅能透過 `_current_output_window` 間接取窗，且 `_run_l1_l6_for_ic_first` 不讀呼叫端 `start_date`）。**修法**：在 `run_ic_first`／`_run_ic_first_impl` 增加與 `generate_features` 同式之 `start_date`／`end_date`，於平穩化路徑先 `resolve_output_window` 再跑 gate／L1–L6；測試改斷言 `lease.path.stem` 含以 A 窗重算之 hash，而非 `str(lease)`。**可行性**：`generate_features` 已有相同 window／hash 鏈（`:376-390`）；補參數屬簽名擴展，不需新旁路機制。

## COMPOSER-R25-P1-02

**斷言**: Task 2.3 ⑪ `test_paths_same_stable_start_and_masks` 以平穩化開啟（預設 `stat_payload`）且 `start_date=None` 跑 frame 基準與 CGSA serial／parallel／resume；觸發 `run_calibration_preflight` 在 `output_start is None` 時拋 `CalibrationError`，三路徑比對從未執行。

**碼證**: `venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_paths_same_stable_start_and_masks -q --tb=line` → 3 failed（`cgsa_serial`／`cgsa_parallel`／`resume`），`feature_factory.py:2169` `field=output_start`。brief「我沒查」②：同一測試內 resume 分支之 `force_regenerate=False` 未觸發（首段 generate 已失敗）。  
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:549  
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:2168  
MUTATION: 維持 `_path_run(..., start_date=None)` 且 payload 仍開 fracdiff／ADF → 任一 parametrized 模式 pytest 紅於校準關卡，⑪ 四路徑同值仍無可執行驗收。

**類別**: code-contract

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#a6a0a1cb0339; momentum/FeatureEngineering/feature_factory.py#47f362f67de2; docs/manifests/FFSTAT.json#87e6acfe46b5

正文：⑪ 應在與 Task 2.3 ③④ 相同之「無起始日＋平穩化」語意下比對，或改為帶 user `start_date` 且四模式皆能完成 generate；現寫法與 `:2168-2171` 關卡矛盾。**修法**：要驗無起始日則須先走 Task 2.3 未填起始日校準路徑（與 `test_no_start_*` 一致之 gate 輸入），再對四模式 parametrize；resume 第二次 run 須在首次成功落盤後才 `force_regenerate=False`。**可行性**：`test_no_start_calibration_rows_masked_from_output` 已證 `start_date=None` 可跑通 generate（同檔 `:238-259`），⑪ 應複用該 env／payload 契約而非預設帶窗 payload。

## COMPOSER-R25-P1-03

**斷言**: Task 2.3 ⑧ `test_multi_tf_mask_applied_before_alignment` 以 `fracdiff=False, adf=False` 關閉平穩化，完成 multi-TF generate 後讀 `metadata["stable_start"]` ⇒ `KeyError`，r24 要求之「對齊後首有效時間＝12h stable 點」精確等式未執行。

**碼證**: `venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_multi_tf_mask_applied_before_alignment -q --tb=line` → 1 failed，`test_ffstat_stable_start.py:435` `KeyError: 'stable_start'`（約 38s）。brief「我沒查」③：對齊探針使用 `marker.reset_index()`＋`timestamp` 欄，與 `TimeframeAligner._split_timestamp_index`（`:428-436`）一致，**未命中**呼叫形式問題；失敗在 metadata 前置條件。  
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:432  
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:435  
MUTATION: 維持 ⑧ 測試關閉 fracdiff／ADF 而仍斷言 `stable_start` receipt → pytest 恆 KeyError，弱 `>=` 與精確等式修補均不可證偽。

**類別**: code-contract

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#a6a0a1cb0339; momentum/FeatureEngineering/timeframe/tf_aligner.py#3c30c600ffc1; docs/manifests/FFSTAT.json#87e6acfe46b5

正文：`stable_start` 為平穩化／校準 receipt（contract `stable_start_receipt_key`）；關閉 L6.5 差分時 metadata 無該鍵，與 ⑧ 語意（多週期遮罩＋對齊）衝突。**修法**：⑧ 應開啟平穩化並使用能產出 `stable_start` 之無起始日或 user start 路徑（與 ③ 同族），再保留 r24 精確等式＋對齊前全 NaN 斷言。**可行性**：`:442-448` 之 `TimeframeAligner.align_to_primary` 探針已寫好，僅需可讀 `stable` metadata 之前提。

---

## 必答

1. **(1a)** 本家 r24 之 `COMPOSER-R24-P1-01` 已閉合。**(1b)** 依 r24 原反例重跑：`venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-r25-inv.json` → rc=0；`pytest …::test_nan_propagation_inventory_complete` → passed；`tests/_golden/ffstat/nan_propagation_classes.json` 92 步＋收據 `20260927-ffstat-nan-propagation-inventory.json` 對齊 `_ast_step_functions()`。

2. **(2a)** 3761b465 修補引入新缺陷（上列 P1-01–03）。**(2b)** 反例命令見各 finding **碼證**（⑫ TypeError、⑪ CalibrationError、⑧ KeyError）。

3. **(3a)** brief assumed「92 步分類正確」→ **機械完備成立、語意抽驗未全面否證**：inventory 與 JSON 一致；propagating 抽驗 `RelativeStrengthProcessor.compute_relative_price` 對 120 列 NaN 前綴＋真實 1h close 切片（800 列）→ `first_finite=120` 且前 120 全 NaN；`not_a_data_step` 抽驗讀碼 `time_features.py:44`（僅 index 時間欄、無 L1 輸入）與 JSON 分類一致。**(3b)** 未對 50／27 步逐步實跑；上列三點為 composer 抽驗與讀碼依據。

4. **(4a)** brief「我沒查」：**① 命中**（lease 斷言不可行且⑫未跑通，併入 P1-01）；**② 命中**（resume 未達 CGSA 續跑，併入 P1-02）；**③ 未命中**（對齊呼叫形式正確，⑧ 失敗因缺 `stable_start`，見 P1-03）。**(4b)** 見 P1-01–03 **碼證** 與 `tf_aligner.py:428-436`。

5. **(5a)** **`VERDICT: blocked`**（P1-01–03 擋實作放行）。**(5b)** `COMPOSER-R25-P1-01,COMPOSER-R25-P1-02,COMPOSER-R25-P1-03`。

---

ASSUMPTIONS_VERIFIED: 已讀 brief、template、governance_verdicts、3761b465 diff、r24 synth、COMPOSER r24 產出；inventory／盤點 pytest 綠；git scope 未改  
TESTS_RUN: `stable_start_receipts.py inventory --out /tmp/ffstat-r25-inv.json` → rc=0；`pytest …::test_nan_propagation_inventory_complete` → 1 passed；`pytest …::test_run_ic_first_*`（4 項）→ 5 failed TypeError；`pytest …::test_paths_same_stable_start_and_masks` → 3 failed CalibrationError；`pytest …::test_multi_tf_mask_applied_before_alignment` → 1 failed KeyError；`venv/bin/python scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → rc=0；`pytest tests/feature_engineering/test_ffstat_stable_start.py --collect-only -q` → 54 collected；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → PASS；`git diff /tmp/ffstat-r25-git-before.txt /tmp/ffstat-r25-git-after.txt` → 空（scope 未改）  
FAILURES_SEEN: 上述 pytest 失敗為 r25 否證證據，非 debug 迭代目標  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r25-composer.md  
TMP_CLEANUP: 已刪 `/tmp/ffstat-r25-*`（含 inv／git snapshot／探針腳本）；保留 `/tmp/claude-501`

VERDICT: blocked
BLOCKED-BY: COMPOSER-R25-P1-01,COMPOSER-R25-P1-02,COMPOSER-R25-P1-03
CLOSED: COMPOSER-R24-P1-01

STATUS: DONE
