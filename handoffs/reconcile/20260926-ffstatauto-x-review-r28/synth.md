# Reconcile — 20260926-ffstatauto-x-review-r28

**來源** 20260926-ffstatauto-x-review-r28-codex.md, 20260926-ffstatauto-x-review-r28-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/manifests/FFSTAT.json

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 盤點只驗單向子集：inventorygate可在AST閉包 | P1 | CODEX-R28-P1-01 | 採納（test_nan_propagation_inventory_complete 改為 AST 閉包、收據、golden 分類表三者完全相等；閉包意外縮小即以缺漏步驟名紅） | code-contract |
| 類別方法 import 解析錯：_called_qualified對fr | P2 | CODEX-R28-P2-02 | 採納（from pkg.mod import Class 後之 Class.X 解析為 pkg.mod:Class.X，模組 import 仍為 pkg.mod:X；補入 TimeframeAligner._timeframe_seconds_keys〔helper，只回週期名清單〕，391 步；閉包測試加該步斷言） | code-contract |
| 零 finding：本輪逐項核對`ca1f9586`對r27 | P3 | COMPOSER-R28-P3-00 | 採納（composer 判 proceed，閉合 r27 條目） | other |

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R28-P1-01

**斷言**: inventory gate 可在 AST 閉包意外漏掉既有 golden step 時保持綠燈，因目前測試只驗 expected <= set(steps)，而 receipt 又由同一個 expected 產生。

**碼證**: tests/feature_engineering/test_ffstat_stable_start.py:171-178 的單向子集斷言；handoffs/run_receipts/ffstat_probes/stable_start_receipts.py:26-37 只迭代 _ast_step_functions()。隔離 mutation 刪除 _winsorize_2d_legacy_equivalent 後，inventory rc=0、test_nan_propagation_inventory_complete 為 1 passed；加入 golden exact-set assertion 後同一 mutation 以該 function missing 失敗。
CODE-ANCHOR: tests/feature_engineering/test_ffstat_stable_start.py:178
MUTATION: isolated copy: replace _ast_step_functions() return with return out - {"momentum.FeatureEngineering.preprocessing.feature_preprocessor:FeaturePreprocessor._winsorize_2d_legacy_equivalent"}; run inventory then pytest -q tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete.

**類別**: code-contract

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#37264a8e234a

修法：將 receipt／test 的步驟集合與 tests/_golden/ffstat/nan_propagation_classes.json 做 exact equality，並保留 AST 與 receipt 的 exact equality；不要只保留目前的單向 subset。可行性證據：隔離複本實加 golden_steps = set(...["steps"]) 與 assert set(steps) == golden_steps，同一 mutation 立即以 missing step 失敗；這是替換現有 gate 的單一契約修正，不需改 production code。影響是目前 receipt 在漏列時不再假綠，沒有數值或輸出 schema 變更。

## CODEX-R28-P2-02

**斷言**: _called_qualified 對 from ... import Class 後的 Class.method 解析格式不正確，造成呼叫鏈閉包漏掉 TimeframeAligner._timeframe_seconds_keys；該 helper 只回傳 timeframe key 名稱，故本輪判為非阻塞 P2。

**碼證**: tests/feature_engineering/test_ffstat_stable_start.py:316-317 將 imported class mapping 以 imports[base].replace(":", ".") + f":{ref.attr}" 組成 module.Class:method，而正確限定名應為 module:Class.method。隔離 AST audit 輸出 defined 420 seeds 213 current 390 corrected 391，唯一差異為 momentum.FeatureEngineering.timeframe.tf_aligner:TimeframeAligner._timeframe_seconds_keys；其呼叫點為 momentum/FeatureEngineering/timeframe/multi_tf_generator.py:1712，實作 tf_aligner.py:515-518 只建立 key list。

**類別**: code-contract

**來源摘要**: momentum/FeatureEngineering/timeframe/tf_aligner.py#3c30c600ffc1

修法建議：import map 保留 (source_module, imported_class) 結構，解析 class attribute 時產生 source_module:imported_class.method；加一個 imported-class closure assertion。此項目前只影響 metadata/tag helper 的盤點涵蓋，不證成 NaN 輸出錯誤，因此不列 BLOCKED-BY。

**(5a)** 不可放行本版 TODO 實作；P1 盤點 gate 能接受漏列步驟，會使 stable-start 分類／後續驗收失去完整性。

**(5b)** 唯一阻擋項為 CODEX-R28-P1-01；P2-02 為非阻塞 coverage debt。

實跑摘要：基線 canonical filter 5 passed, 53 deselected；inventory rc=0、static mutation probe rc=0、TODOFMT PASS；real classification probe rc=0；r27 raw-copy mutation test pass、rolling mutation test fail as expected；未在工作樹改碼、改文檔、改 git，未觸碰 data_cache/。

VERDICT: blocked
BLOCKED-BY: CODEX-R28-P1-01
CLOSED: CODEX-R27-P1-01
## COMPOSER-R28-P3-00

**斷言**: 本輪逐項核對 `ca1f9586` 對 r27 reconcile 部分採納之內聯檢查與盤點閉包後，未發現超出 manifest「實作前紅」之外、需阻擋 TODO 放行之新 P0／P1。

**碼證**: `venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out /tmp/ffstat-r28-work/inventory.json` → `INVENTORY_RC=0`（390 步、`unclassified: []`）；`pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py -k "inventory or class_bound or index_derived or dispatcher_inline or inventory_closure" -q` → 5 passed in 24.60s；`pytest …::test_mutation_dispatcher_inline_rolling_is_caught -q` → 1 passed；`venv/bin/python scripts/mutation_probe_static.py tests/feature_engineering/test_ffstat_stable_start.py` → `MUTATION_STATIC_RC=0`；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；`PYTHONPATH=. venv/bin/python /tmp/ffstat-r28-work/probe_steps.py` → rc=0（真實 BTCUSDT 1h×300：polars `polars_l2_derived_momentum` 前 5 列 null、`first_finite=5`；`causal_preprocessing` 強制 True）。

**類別**: other

**來源摘要**: tests/feature_engineering/test_ffstat_stable_start.py#37264a8e234a; handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json#5e688567450c; docs/manifests/FFSTAT.json#29af82d8ad7c; handoffs/reconcile/20260926-ffstatauto-x-review-r27/synth.md#459083a99bc8

正文：`ca1f9586` 以 `_ast_step_functions`（`:359-379`）做公開函式＋前綴種子與 `_called_qualified` 遞移閉包，`test_inventory_closure_reaches_off_prefix_and_nested_steps`（`:335-346`）鎖 `_winsorize_2d_legacy_equivalent`、`_ts_argmax_2d`、`polars_l2_derived_momentum`、`transform_array_fast` 等漏列修補。r27 `CODEX-R27-P1-01` 之機械修法已落地：`_NO_INLINE_CLASSES`＋`_inline_nan_filling_calls`（`:191-230`）與 `test_mutation_dispatcher_inline_rolling_is_caught`（`:233-249`）——rolling 注入必紅、原樣 `to_numpy` 搬移與 reconcile 理由一致不列紅。盤點 class 計數與 brief assumed 一致（propagating 86、not_in_generation_path 37、incomplete_window 9、dispatcher 37）。manifest `risk_mitigation` 已列縮尾五入口（`:230`）。

---

