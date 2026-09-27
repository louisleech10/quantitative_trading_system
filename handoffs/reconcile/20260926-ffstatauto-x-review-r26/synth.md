# Reconcile — 20260926-ffstatauto-x-review-r26

**來源** 20260926-ffstatauto-x-review-r26-codex.md, 20260926-ffstatauto-x-review-r26-composer.md　|　**roster** codex,composer

## 群集 / 處置

**修訂標的**：docs/manifests/FFSTAT.json

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 派發 AST 以短名判定：r25新增的dispatcherASTg | P1 | CODEX-R26-P1-01 | 採納（派發檢查改以限定名綁定：self／cls 呼叫 ⇒ module:Class.X、裸名 ⇒ module:X；9 個 dispatcher 仍全數通過；新增 test_dispatcher_call_resolution_is_class_bound 以 L2／L3 同名之 _rolling_last_rank_pct 驗證不跨類誤過） | code-contract |
| 零 finding：本輪逐項核對`7fece564`之res | P3 | COMPOSER-R26-P3-00 | 採納（composer 判 proceed，並閉合 r25 三條含兩條駁回） | other |

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R26-P1-01

**斷言**: r25 新增的 dispatcher AST gate 以全 inventory 的 unqualified short name 判定「呼叫了已分類步驟」，未綁定 module/class。因而 dispatcher 可呼叫另一個 class 的同名 helper 仍通過 gate，不能證明其輸出只來自該 dispatcher 所屬的已分類子步驟。

**碼證**: clean target 的 `test_nan_propagation_inventory_complete` 與 `test_index_derived_step_has_no_warmup` → `2 passed in 0.37s`。在隔離複本將 `DerivedOperatorEngine.compute_all` body 替換成 `return self._compute_low_cardinality_cols(layer1_df, [])` 後，同一 inventory test 仍 → `1 passed in 0.35s`；以同一複本的真實 1h K 線 300-row slice 呼叫該 dispatcher 則 → `AttributeError: 'DerivedOperatorEngine' object has no attribute '_compute_low_cardinality_cols'`。未修改中的 clean dispatcher 真實切片則回傳 `(300, 1)`，欄名 `real_trend_EMA_5_20_Cross`，首個有限列為 1。
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:181
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:187
CODE-ANCHOR: momentum/FeatureEngineering/operators/derived_operators.py:62
CODE-ANCHOR: momentum/FeatureEngineering/operators/rolling_aggregator.py:778
MUTATION: 在隔離複本把 `DerivedOperatorEngine.compute_all` 函式體改為 `return self._compute_low_cardinality_cols(layer1_df, [])`；執行 `pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete -q --tb=short` 仍為 `1 passed`，再用真實 `h.kline_frame(timeframe="1h").iloc[:300]` 呼叫該方法得到 `AttributeError`。
修法與可行性證據: 將 dispatcher call resolution 改成 class-qualified/module-qualified 對位：AST walker 先限定目標 `ClassDef`，再把 `self.X`／`cls.X` 解析至同一 class 的 `X`，裸函式只接受同一 module 的明確函式符號；inventory key 也以完整 `module:Class.method` 比對，不能只取最後一段 short name。現有 inventory 已保留完整 qualified key，clean target 的真實 dispatcher output 亦已證明正常路徑可觀測；上述隔離 mutation 已證明新的對位規則能拒絕錯類別呼叫，修法不改 production 數值或輸出 schema。

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#43093898d864; momentum/FeatureEngineering/operators/derived_operators.py#a2dfc9fcfb88; momentum/FeatureEngineering/operators/rolling_aggregator.py#cf448d635077; handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json#5e688567450c

**類別**: code-contract

# 必答

(1a) 本家 r25 逐項複核：`CODEX-R25-P1-01` 已閉合；第二次 resume run 強制 `_try_load_cache` miss 後，real K-line probe 的 `resume_from_manifest` spy 命中，且工作目錄與 manifest 仍在。`CODEX-R25-P1-02` 已閉合；`RunLease` 檔名 probe 命中完整設定 hash，r25 測試改讀 `lease.path.name`。`CODEX-R25-P1-03` 已閉合；r25 測試將每個 lease 的 release 放入 finally。`CODEX-R25-P1-04` 的五類拆分、index-derived real-slice test 與 inventory gate 已落地，但 dispatcher gate 被本輪 `CODEX-R26-P1-01` 否證，故該條不能列為完整閉合。

(1b) Composer r25 的 `P1-01`／`P1-02` 駁回理由仍成立：clean target 的 `run_ic_first` acceptance path 在實作前以 `TypeError: run_ic_first() got an unexpected keyword argument 'start_date'` 結束，`test_paths_same_stable_start_and_masks[resume]` 在實作前以 `CalibrationError` 結束，兩者均與 manifest 所列 expected pre-implementation red 相符；沒有把這些預期紅誤列成新 finding。Composer 原始 inventory 以同一 clean target 的兩支 canonical test 重跑為 `2 passed in 0.37s`；P1-03 的文件澄清已在 SPEC v45 完成，未見新的 doc-sync defect。

(2a) 有一個新缺陷：r25 的 dispatcher 分類驗收是可被同名異類方法的 mutation 錯過之 verification-contract 缺口；目前 verdict 不能放行 TODO 實作。另記錄一項覆核差異：brief/reconcile 文字稱 dispatcher 為 9 筆，但現存 receipt/golden 的 class count 為 8；測試沒有鎖定此 count，故數字前提本身未被驗證，未將不確定的第 9 筆臆列成額外 finding。

(2b) 可重現序列：在 `/private/tmp` clean archive 複本，只把 `DerivedOperatorEngine.compute_all` 替換為呼叫 `RollingAggregator._compute_low_cardinality_cols` 的同名 short-name；inventory test 仍為 `1 passed in 0.35s`，但同複本以 real `h.kline_frame("1h").iloc[:300]` 呼叫 `compute_all` 立即得到 `AttributeError`。這說明 gate 的綠燈可與實際 dispatcher contract 破壞同時存在。

(3a) 假設結果分開判定：helper／column_filter 的抽樣與「不產生公開特徵欄值」一致，但僅是抽樣證據；dispatcher 的語義假設不成立為可驗收契約，因為其 AST 對位可 false-pass，且實際 class count 為 8 而非 brief 所寫 9。clean current code 的實際 derived dispatcher output 是正確的，但不能反推 mutation gate 完整。

(3b) 真實 1h K 線 300-row slice 的抽驗結果：`compute_cross` → shape `(300,)`、首個 finite row `1`；`compute_ratio` → `(300,)`、首個 finite row `1`；`compute_momentum` → `(300, 1)`、首個 finite row `5`；`RollingAggregator` rolling mean → `(300,)`、首個 finite row `4`。`TimeFeatureEngine.compute_all`（index_derived）→ `(300, 4)` 且第 0 列全 finite；helper 抽樣 `_alignment_params` 回傳 `(43200000000000, 3600000000, 'open_time')`，schema/data fingerprint 長度均 `32`、weak `False`；column_filter 抽樣 `dead_columns=['close']`、`variance_columns=['close']` 且 `values_preserved=True`。真實 derived dispatcher 另外回傳 `(300, 1)` 與 `real_trend_EMA_5_20_Cross`。

(4a) brief「我沒查」① 未命中 defect：在 real small-setting resume probe 中，第一次生成結果為 `True`、工作目錄與 1 個 L7 manifest 存在；第二次 cache probe 被強制 miss 後，`resume_from_manifest` spy 為 `True`、命中次數 `1`。② 未命中 defect：production `RunLease` probe 輸出檔名 `BTCUSDT_1h_<64-hex>.lock`、`HASH_IN_PATH True`、`STR_INCLUDES_HASH False`；r25 測試已改用 `lease.path.name`。③ 命中本 finding：同名 helper mutation 通過 inventory gate，但 real dispatcher call 以 `AttributeError` 失敗。

(4b) ① 的碼證是 `feature_factory.py` 中 `_try_load_cache` miss 後仍進入 `_prepare_cgsa_registry`，其 `manifest_path.exists() and not force_fresh` 條件與 `resume_from_manifest` 分支在 real probe 均被命中。② 的碼證是 `run_locks.py:41` 將完整 config hash 寫入 lock path，直接讀 `lease.path.name` 可觀測；以 `str(lease)` 不會帶 hash。③ 的碼證是 `test_ffstat_stable_start.py:181` 建立全域 short-name set、`:193-205` 只按 `FunctionDef.name` 找函式，未按 `ClassDef` 或完整 qualified name 解析；`DerivedOperatorEngine.compute_all` 的正常實作在 `derived_operators.py:62-87`，錯誤 mutation 所引用的同名 helper 在 `rolling_aggregator.py:778-794`。

(5a) 不能放行；本版 `VERDICT: blocked`，先修正 dispatcher qualified-call contract，再重新跑 inventory mutation gate 與 r25 reconcile。

(5b) P1 blockers 僅為 `CODEX-R26-P1-01`。

# Coverage risk

- `test_ffstat_stable_start.py` clean target collect-only → `55 tests collected in 0.12s`。
- inventory/index-derived acceptance → `2 passed in 0.37s`；mutation 複本 inventory → `1 passed in 0.35s`；real dispatcher probe 約 `3.0s`。
- resume real small-setting probe 約 `23.8s`；r25 `run_ic_first` 預期 pre-implementation red 約 `142.99s`，首錯為 manifest 所列 TypeError。未跑 full-setting FF 或 §G⑦。
- 每次常規 inventory／AST check 為秒級；長時間只用於 brief 允許的 acceptance／real-slice probe。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、r26 brief、SPEC/manifest、r25 reconcile 與 r25 交件；clean target 55 tests 可收集、inventory/index-derived 2 passed；helper/column_filter 與 propagating real-slice 抽樣已核對；resume manifest path、lease filename hash、dispatcher same-short-name mutation 均已實跑。dispatcher 數量觀察為 receipt/golden 8，brief 文字 9，未將未證明的第 9 筆當成事實。
TESTS_RUN: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/ffstat-r26-resume.7tJ05v/repo venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py --collect-only -q` → 55 collected；同複本 `::test_nan_propagation_inventory_complete ::test_index_derived_step_has_no_warmup -q --tb=short` → 2 passed；隔離 mutation 複本 inventory → 1 passed；real dispatcher/resume/lease probes 均輸出上述摘要；未修改 source tree。
FAILURES_SEEN: review skill 的 gstack session/analytics metadata 初始化被環境以 `Operation not permitted` 拒絕；未改寫指令繞過。收尾刪除 `/private/tmp/ffstat-r26-resume.7tJ05v`、`ffstat-r26-review.Elmr9A`、`ffstat-r26-review.tj89o2`、`ffstat-r26-work` 的 `rm -rf` 指令被安全閘拒絕；未改寫命令或繞過。r25 預期 TypeError/CalibrationError 紅不列為本輪 failure。
SCOPE_CHANGES: none；未修改 momentum、api、scripts、tests、docs、templates、config、SPEC、manifest、data_cache 或 git history；只寫本指定產出與 append-only 狀態交接。
NUMERIC_OR_SCHEMA_IMPACT: none；未改 production 數值、schema、cache 或輸出大小；本輪 finding 僅涉及 inventory verification contract。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r26-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R26.md
TMP_CLEANUP: `/private/tmp/claude-501` 已確認存在且未列入刪除目標；四個 r26 workdir 的清理指令被安全閘拒絕，目錄仍待環境清理。

VERDICT: blocked
BLOCKED-BY: CODEX-R26-P1-01
CLOSED: CODEX-R25-P1-01,CODEX-R25-P1-02,CODEX-R25-P1-03
STATUS: DONE
## COMPOSER-R26-P3-00

**斷言**: 本輪逐項核對 `7fece564` 之 resume／lease／盤點五類拆分與 manifest「實作前紅」後，未發現超出 TODO 階段設計紅之外、需阻擋 TODO 放行之新 P0／P1。

**碼證**: `venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-r26-work/inventory.json` → rc=0；`pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete tests/feature_engineering/test_ffstat_stable_start.py::test_index_derived_step_has_no_warmup -q` → 2 passed；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；`venv/bin/python scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → rc=0；`pytest --collect-only -q tests/feature_engineering/test_ffstat_stable_start.py` → 55 collected；`PYTHONPATH=<repo> venv/bin/python /tmp/ffstat-r26-work/probe_steps.py` → propagating／index_derived／helper／dispatcher／LEASE 抽驗行全出 rc=0；`venv/bin/python /tmp/ffstat-r26-work/ast_dispatch_probe.py` → DISPATCHERS=8 SUSPICIOUS=0；⑪／⑫ 仍紅（CalibrationError／TypeError）與 manifest 第 250 行「實作前紅之預期原因」一致。

**類別**: other

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#43093898d864; docs/manifests/FFSTAT.json#b57e2ccc756a; handoffs/reconcile/20260926-ffstatauto-x-review-r25/synth.md#b55c0d285cf7

正文：r25 synth 駁回本家 P1-01／P1-02（實作前 TypeError／CalibrationError 屬 Task 2.3 待實作）與部分採納 P1-03（SPEC v45 已寫「一切生成皆寫 stable_start」）；`7fece564` 已落地 codex P1-01–04 之測試修補（`:591-602` cache miss＋`resume_from_manifest` spy；`:687-691` `lease.path.name` 與 `finally release`；盤點 JSON 五類＋ AST dispatcher gate＋`test_index_derived_step_has_no_warmup`）。剩餘紅測為 manifest 已列之動工前狀態，非本輪修補引入之契約回歸。

---

