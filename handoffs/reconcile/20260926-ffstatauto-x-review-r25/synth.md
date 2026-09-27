# Reconcile — 20260926-ffstatauto-x-review-r25

**來源** 20260926-ffstatauto-x-review-r25-codex.md, 20260926-ffstatauto-x-review-r25-composer.md　|　**roster** codex,composer

## 群集 / 處置

**修訂標的**：docs/manifests/FFSTAT.json

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| resume 未真走續跑：Task2.3⑪新增的`resume`參 | P1 | CODEX-R25-P1-01 | 採納（resume 第二次令快取探測落空並 spy ColumnGroupRegistry.resume_from_manifest，斷言被呼叫） | code-contract |
| lease 以 str 比對不成立：`test_run_ic_first_u | P1 | CODEX-R25-P1-02 | 採納（改以 lease.path.name 含設定 hash） | code-contract |
| 迭代未釋放 lease：同一`run_ic_first`測試即使 | P1 | CODEX-R25-P1-03 | 採納（每迭代 finally 對 lease 呼叫 release） | code-contract |
| 非資料步驟分類過粗：brief要求`not_a_data_s | P1 | CODEX-R25-P1-04 | 採納（拆為 dispatcher 9、index_derived 1、helper 15、column_filter 2、mask 1；inventory 測試以 AST 機械驗每個 dispatcher 呼叫至少一個已列步驟、propagates_nan 與 class 一致；新增 index_derived 之真實切片測試；compute_calibration_domain 改歸 helper〔產生校準值而非公開特徵欄〕） | code-contract |
| run_ic_first 無起訖參數：Task2.3⑫新增之四支`run_ic | P1 | COMPOSER-R25-P1-01 | 駁回（`start_date`／`end_date` 參數正是 Task 2.3〔SPEC v29〕要新增者，TODO 階段實作前 TypeError 即正確之紅；manifest 新增「實作前紅之預期原因」一條明列） | other |
| 無起始日加平穩化被擋：Task2.3⑪`test_paths_ | P1 | COMPOSER-R25-P1-02 | 駁回（現行碼之 run_calibration_preflight 拋錯為動工前行為；SPEC v32 §C「未填起始日」使此路徑合法並由 Task 2.3 實作，實作前紅屬設計；已列入 manifest 預期紅原因） | other |
| 平穩化關閉無 stable_start：Task2.3⑧`test_multi_ | P1 | COMPOSER-R25-P1-03 | 部分採納（stable_start 由 Task 2.3 新增，實作前 KeyError 屬設計；但 SPEC 未明寫平穩化關閉時亦寫入 ⇒ v45 措辭釐清「一切生成之 metadata 與 manifest 皆寫、平穩化開關皆然」，⑧ 維持平穩化關閉以驗 R1 之一切生成遮罩） | doc-sync |

### 類別不一致

- `COMPOSER-R25-P1-01`：委員類別「code-contract」、主委類別「other」——駁回（所指 TypeError 為 SPEC v29 待實作之參數，屬 TODO 階段實作前應紅之設計，非程式契約缺陷）
- `COMPOSER-R25-P1-02`：委員類別「code-contract」、主委類別「other」——駁回（所指 CalibrationError 為動工前之現行行為，v32 起合法路徑由 Task 2.3 實作，實作前紅屬設計）
- `COMPOSER-R25-P1-03`：委員類別「code-contract」、主委類別「doc-sync」——部分採納（實作前 KeyError 屬設計；實質缺口為 SPEC 未明寫平穩化關閉亦寫 stable_start，屬文件措辭，以 v45 釐清）

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

