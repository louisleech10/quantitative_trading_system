## CODEX-R25-P1-01

**斷言**: Task 2.3 ⑪ 新增的 `resume` 參數目前沒有真正走 CGSA resume；`_path_run` 先以 `force_regenerate=True` 寫出可快取結果，再以 `force_regenerate=False` 重跑同一 `tmp_path`，factory 會在 `_prepare_cgsa_registry` 之前由 `_try_load_cache` 直接返回，因此 `ColumnGroupRegistry.resume_from_manifest` 未被驗證。這使 r24 `CODEX-R24-P1-02` 僅部分閉合。

**碼證**: 目標測試在 `resume` 僅改第二次 `run_stat` 的 `force_regenerate`；生成入口在 cache hit 時於 registry/resume 分支前返回；CGSA resume 實際位於後續 `_prepare_cgsa_registry` 的 manifest 分支。隔離複本 `test_nan_propagation_inventory_complete` 1 passed，故 inventory 結構 gate 綠不代表此 path gate 已命中。
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:549-555
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:392-406
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:4177-4233
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:1191-1199
MUTATION: 在 `ColumnGroupRegistry.resume_from_manifest` 入口改為拋出 `AssertionError`；實作完成後，現有 `resume` 參數的第二次呼叫仍可在 `_try_load_cache` 命中而避開該 mutation。
修法與可行性證據: resume case 應在第二次呼叫明確讓 `_try_load_cache` miss（例如以既有 `monkeypatch` fixture 對該 factory 的 cache probe 加 spy/暫時返回 `None`），並保留 CGSA manifest，再斷言 `resume_from_manifest` 被呼叫及其結果的 stable-start/decisions/fingerprint。`_prepare_cgsa_registry` 已有明確 `resume_allowed` 分支，無需新增旁路或改變輸出 schema。

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py:549-568; momentum/FeatureEngineering/feature_factory.py:392-406,4177-4233; handoffs/reconcile/20260926-ffstatauto-x-review-r24/synth.md:13-15; tests/feature_engineering/test_ffstat_stable_start.py#a6a0a1cb0339

**類別**: code-contract

## CODEX-R25-P1-02

**斷言**: `test_run_ic_first_uses_own_window_not_previous` 以 `expected_hash in str(lease)` 驗證 lease 身分，但 `RunLease` 沒有 `__str__`／`__repr__`，只有 `path` 屬性；因此即使 lease path 的檔名含正確 hash，`str(lease)` 仍是預設 object repr，該 assertion 不可成立也不能辨識錯 hash。隔離 probe 實跑輸出 `LEASE_STR_HAS_HASH False <momentum.FeatureEngineering.run_locks.RunLease object ...>`。

**碼證**: 目標測試在完成 `run_ic_first` 後於 line 638 搜尋 hash；`RunLease.acquire` line 41 才把 hash 寫入 `path`，class line 21-83 沒有 repr/str 實作。上述 probe 以合法 64-hex hash 建立同一 production `RunLease`，結果 rc=0 且明確為 `False`。
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:628-638
CODE-ANCHOR: momentum/FeatureEngineering/run_locks.py:21-61
MUTATION: 將 `RunLease.acquire` 內實際使用的 config hash 改成另一個合法 hash；目前測試的 `str(lease)` 觀測值仍不含任何 hash，無法區分正確與錯誤 lease 身分。
修法與可行性證據: 直接斷言 `lease.path.name` 含 `expected_hash`，或以 spy 記錄 `RunLease.acquire` 收到的 `(symbol, timeframe, config_hash)`；前者使用 class 已公開的 `path` 屬性，後者可在現有測試 fixture 中完成，均不需改變 production lock schema。

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py:615-638; momentum/FeatureEngineering/run_locks.py:21-83; `/tmp/ffstat-r25-work/lease_probe.py` 實跑輸出; momentum/FeatureEngineering/run_locks.py#51e3f55c9a9a

**類別**: code-contract

## CODEX-R25-P1-03

**斷言**: 同一 `run_ic_first` 測試即使修正 hash 觀測，仍會在第二個 `preset=True` 迭代前撞上第一個迭代留下的 exclusive lease。測試將 factory storage 固定在 `tmp_path/gen`，兩次呼叫共用 `.locks`；`lease_sink` 保留第一個 lease，但測試沒有在迭代結尾 release。隔離 probe 實跑同一 lock identity 的第二次 acquire 得到 `RunBusyError`，release 後第三次 acquire 才成功。

**碼證**: 測試 line 625 設定 factory storage，line 629-634 在同一 factory 以兩個 preset 呼叫 `run_ic_first`；production line 2428 以 `self._storage.base_path/.locks` acquire，line 2442-2449 在有 `lease_sink` 時刻意保留 lease。`RunLease.release` 雖然 idempotent，但測試沒有呼叫它，因此第二個 preset 的 A/B state assertion 不會被執行。
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:625-638
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:2428-2449
CODE-ANCHOR: momentum/FeatureEngineering/run_locks.py:41-77
MUTATION: 維持 `RunLease.acquire` 的 exclusive lock 行為，依序對同一 locks directory／symbol／timeframe／hash acquire；`/tmp/ffstat-r25-work/lease_probe.py` 輸出 `SECOND_ACQUIRE RunBusyError`，重現第二迭代被擋。
修法與可行性證據: 將每一迭代的 assertions 放在 `try`，並於 `finally` 對 `leases` 中每個 lease 呼叫 `release()`；或改用 acquire spy 驗證 hash 而不把 lease 留在 factory 的 lock directory。`RunLease.release()` 已提供重複安全釋放，修法不涉及資料或輸出大小。

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py:615-638; momentum/FeatureEngineering/feature_factory.py:2428-2449; momentum/FeatureEngineering/run_locks.py:41-77; `/tmp/ffstat-r25-work/lease_probe.py` rc=0; momentum/FeatureEngineering/feature_factory.py#47f362f67de2

**類別**: code-contract

## CODEX-R25-P1-04

**斷言**: brief 要求 `not_a_data_step` 類別中的函式確實不產生 feature value，但本輪真實 BTCUSDT 切片否證此假設至少三例：`TimeFeatureEngine.compute_all` 回傳 4 欄、`RollingAggregator.compute_all` 回傳 rolling 欄、`DerivedOperatorEngine.compute_all` 回傳 derived 欄；三者都已列在 27 筆 `not_a_data_step`。目前 inventory test 只驗列存在、boolean/evidence 與允許的 class，沒有驗分類語義，因此 92-step 的分類正確性仍未成立。

**碼證**: golden/receipt 將三個函式列為 `not_a_data_step`；production source 分別明確建立時間欄、rolling output、concat derived frames，且 feature factory 將它們接到 L2/L3/L6 生產路徑。真實切片 probe（1h 300 rows、12h 40 rows）輸出：`NOT_DATA time_shape (300, 4) time_finite 300`、`NOT_DATA rolling_shape (300, 1) rolling_first 2024-01-01 04:00:00+00:00`、`NOT_DATA derived_shape (300, 2) derived_first 2024-01-01 00:00:00+00:00`。
CODE-ANCHOR: tests/_golden/ffstat/nan_propagation_classes.json:45-52
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:171-185
CODE-ANCHOR: momentum/FeatureEngineering/meta_features/time_features.py:41-57
CODE-ANCHOR: momentum/FeatureEngineering/operators/rolling_aggregator.py:107-152
CODE-ANCHOR: momentum/FeatureEngineering/operators/derived_operators.py:62-87
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:1618-1627
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:1799-1818
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:2114-2120
MUTATION: 將上述三列維持 `not_a_data_step` 而把任一 output-producing function 的實際輸出改成空 frame；`test_nan_propagation_inventory_complete` 仍只檢查 schema/class/evidence，無法檢出 output contract 或分類錯誤。
修法與可行性證據: 將「dispatch wrapper／index-derived output／真正非值轉換 helper」拆成明確類別或新增 `produces_feature_values` 欄位；對實際產生欄位的函式以真實切片斷言 output columns 與 NaN 起點，並讓 inventory gate 驗證分類與碼證對位。現有 production call sites 與測試的 real-kline helper 已可直接承載此檢查，不需 full-setting FF run。

**來源摘要**: tests/_golden/ffstat/nan_propagation_classes.json:45-52; handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json; tests/feature_engineering/test_ffstat_stable_start.py:171-207; momentum/FeatureEngineering/meta_features/time_features.py:41-57; momentum/FeatureEngineering/operators/rolling_aggregator.py:107-152; momentum/FeatureEngineering/operators/derived_operators.py:62-87; `/tmp/ffstat-r25-work/probe.py` rc=0; tests/_golden/ffstat/nan_propagation_classes.json#02be9f6c111c

**類別**: code-contract

必答：

(1a) r24 逐項結果：`CODEX-R24-P1-01` 的 AST/private call-path 擴展與 92-row inventory 結構已閉合；`CODEX-R24-P1-02` 的 frame/CGSA serial/parallel 測試已加入，但 `resume` 被 factory cache short-circuit，未閉合；`CODEX-R24-P1-03` 的精確等式已加入，真實切片同一 `TimeframeAligner.align_to_primary` 呼叫形式可重現，閉合；`CODEX-R24-P1-04` 四個具名測試已加入，但 hash assertion 與 lease retention 使核心 A/B 驗收未閉合；`CODEX-R24-P2-05` 重複 boundary 已移除且 manifest 指向既有 canonical test，閉合。Composer r24 的原始 inventory finding 以同一 inventory command rc=0、`test_nan_propagation_inventory_complete` 1 passed 複核，但不列入本家 `CLOSED`。

(1b) 本家 r24 只有 `CODEX-R24-P1-01`、`CODEX-R24-P1-03`、`CODEX-R24-P2-05` 可列 closed；P1-02/P1-04 分別由本輪 P1-01、P1-02/P1-03 阻塞。

(2a) 有新 defects：resume cache bypass、lease hash assertion 不可行、lease 未釋放造成第二 preset busy，以及 `not_a_data_step` 分類語義與真實 output 不符。

(2b) 可重現證據為 `_try_load_cache` return 位於 `_prepare_cgsa_registry` 之前；`lease_probe.py` rc=0 輸出 `LEASE_STR_HAS_HASH False`、`SECOND_ACQUIRE RunBusyError`；real-slice probe rc=0 輸出上述三個 `NOT_DATA` output shapes。這些是測試／inventory contract 的反例，未改 production code。

(3a) 92-step assumption 部分成立、部分否證：抽樣的三個 `propagating`（`compute_cross`、`_compute_mean`、`_searchsorted_align`/對齊入口）都在 L1-leading NaN 後才出值；抽樣的三個 `not_a_data_step` 都實際產生 output，故「不產生 feature value」前提為 false，分類需重新定義或補強證據。

(3b) 真實 BTCUSDT 1h 300 rows／12h 40 rows：cross 首值 `2024-01-01 10:00:00+00:00` 等於 masked 首值；rolling mean 首值 `2024-01-01 14:00:00+00:00`；12h align 首值 `2024-01-03 00:00:00+00:00`；`reset_index()` 對齊形式同樣成功。not_a_data 三例結果為 `(300,4)`、`(300,1)`、`(300,2)`。

(4a) brief 指定的三個「I didn’t check」中，(1) lease_sink content string hash 命中 CODEX-R25-P1-02；(2) resume path 命中 CODEX-R25-P1-01；(3) `TimeframeAligner.align_to_primary` source-call correctness 未發現 defect，直接以真實切片及測試同型 `reset_index()` 呼叫驗證。

(4b) (1) `RunLease` source 沒有 repr/str 且 probe 為 `False`；(2) `_try_load_cache` line 392-395 早於 `_prepare_cgsa_registry` line 405-406；(3) `_split_timestamp_index` line 428-436 正確消費 `timestamp` 欄，real probe 的 aligned output 有穩定首值。

(5a) TODO 目前不能 proceed；先修正四個本輪 P1 contract blockers，再重簽 r25 reconcile。

(5b) P1 blockers 僅為 `CODEX-R25-P1-01,CODEX-R25-P1-02,CODEX-R25-P1-03,CODEX-R25-P1-04`。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、r25 brief、SPEC/manifest、r24 reconcile 與兩家 r24 交件；inventory rc=0、target inventory test 1 passed、static mutation probe rc=0、TODOFMT PASS；真實切片已完成三個 propagating 與三個 not_a_data_step 抽樣；resume/cache、lease hash、lease retention 均以 source 或隔離 probe 核對。
TESTS_RUN: `PYTHONDONTWRITEBYTECODE=1 ... stable_start_receipts.py inventory --out /tmp/ffstat-r25-work/inventory.json` → rc=0；`... scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → rc=0；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；`pytest --collect-only -q tests/feature_engineering/test_ffstat_stable_start.py` → 54 collected；`pytest -q ...::test_nan_propagation_inventory_complete` → 1 passed；`PYTHONPATH=... python /tmp/ffstat-r25-work/probe.py` → rc=0；`PYTHONPATH=... python /tmp/ffstat-r25-work/lease_probe.py` → rc=0，輸出 `LEASE_STR_HAS_HASH False`／`SECOND_ACQUIRE RunBusyError`。另有一次 targeted multi-TF integration command 在 30s 初次 yield 後未以其結果作結論，未納入 PASS claim。
FAILURES_SEEN: 初次 mutation probe 路徑誤寫為 `tests/mutation_probe_static.py`（rc=2），改用 repo 實際路徑 `scripts/mutation_probe_static.py` 後 rc=0；real probe 初次未設 `PYTHONPATH`（ModuleNotFoundError），修正後 rc=0；probe 初次以 static method 方式呼叫 `_compute_mean`（TypeError），改以既有 instance method signature 後 rc=0；`ps`/`pgrep` 的 process inspection 受環境限制未取得狀態，未改寫命令繞過；最後 `rm -rf /tmp/ffstat-r25-work` 被安全閘拒絕，未改寫命令或繞過。
SCOPE_CHANGES: none；未修改 momentum、api、scripts、tests、docs、templates、config、SPEC、manifest、data_cache、git history；僅新增本交件檔與 append-only 狀態交接。
NUMERIC_OR_SCHEMA_IMPACT: none；沒有 production 數值、schema 或輸出大小變更；本輪只記錄 real-slice observation 與 test-contract findings。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r25-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R25.md
TMP_CLEANUP: `rm -rf /tmp/ffstat-r25-work` 由安全閘拒絕，`/tmp/ffstat-r25-work` 仍在；`/tmp/claude-501` 已確認存在並保留

VERDICT: blocked
BLOCKED-BY: CODEX-R25-P1-01,CODEX-R25-P1-02,CODEX-R25-P1-03,CODEX-R25-P1-04
CLOSED: CODEX-R24-P1-01,CODEX-R24-P1-03,CODEX-R24-P2-05
STATUS: DONE
