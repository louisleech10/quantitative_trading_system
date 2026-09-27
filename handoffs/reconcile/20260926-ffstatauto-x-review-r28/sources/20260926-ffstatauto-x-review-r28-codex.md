# FF-STAT TODO r28 審查（CODEX）

審查基準：ca1f9586、handoffs/reconcile/20260926-ffstatauto-x-review-r27/synth.md、docs/FFSTAT_SPEC.md、docs/manifests/FFSTAT.json；未改動 repository code、docs 或 git。所有動態 probe 均在隔離 /tmp 複本，K 線 probe 使用真實 BTCUSDT/1h HDF5 小切片。

**(1a)** CODEX-R27-P1-01 可閉合。原始 provenance mutation 只是把真實 raw_data["close"] 原樣搬到輸出，沒有把 NaN／未滿窗轉為有限值；rolling 變體才是本規則要攔截的失敗模式。

**(1b)** 原值變體在真實 1h×300 slice 產生 shape=[300,1]、finite=300、first_equal=True；inventory test rc=0。加入 rolling(20,min_periods=1).mean() 的同一變體仍產生真實 slice 輸出，但盤點測試以 AssertionError: ... compute_all, ['rolling@74'] rc=1；因此 r27 的 inline guard 對暖機型 mutation 有效，原值搬移不列紅的理由成立。

**(2a)** 有新缺陷：盤點完整性測試只檢查 AST 預期集合是 receipt 集合的子集；若 AST 閉包本身因意外漂移漏掉既有 golden step，receipt 會同步漏列，測試仍可綠燈。另見一個非阻塞的 imported-class resolver 漏列（P2）。

**(2b)** P1 的可重現操作：隔離複本把 _ast_step_functions() 的 return out 改成 return out - {"momentum.FeatureEngineering.preprocessing.feature_preprocessor:FeaturePreprocessor._winsorize_2d_legacy_equivalent"}；執行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out handoffs/run_receipts/2099-ffstat-nan-propagation-inventory.json 得 rc=0，再執行單一 test_nan_propagation_inventory_complete 得 1 passed，但 receipt 已少一個 golden step。隔離複本加入 assert set(steps) == golden_steps 後，同一 mutation 以 missing-step assertion 失敗；修法可達成。

**(3a)** 抽驗到的分類成立，但不能把目前 390 步的全域正確性宣稱為已證實，因 P1 允許閉包漏列。三個 propagating（RelativeStrengthProcessor.compute_relative_price、DerivedOperatorEngine.compute_cross、polars_l2_derived_ratio）在 real 1h×300、index 40 注入 NaN 的複本上均保留 NaN。not_in_generation_path 抽驗則涵蓋 _rolling_count、OperatorRegistry.default_registry、winsorize_array、polars_l65_rank_transform：分別得到 finite-after-warmup 280、registry 20 operators／real cross 300 finite、winsorized 600 finite、Polars rank 首個有限位置 19；這些直接可執行不等於 default pre-IC generation path。

**(3b)** 同一 real probe 的 pre-IC context 為 do_rank=False, do_zscore=False, do_gaussian=False, causal_preprocessing=True；Numba fast output shape [300,2]、finite 600。test_ic_first_pipeline.py 在隔離複本為 15 passed in 4.03s，支持 pre-IC／post-IC routing 的分類依據；未跑全設定 FF 或 §G⑦ 雙起點。

**(4a)** ① 有語法上的間接呼叫：feature_preprocessor.py:2057-2073 透過 transform_context["transform_array_fast"](...)，multi_tf_generator.py 也有 self._factory._layer...。目前未找到因這些間接呼叫而遺漏的特徵產生 public target：transform_array_fast 是公開 seed，_rolling* 子步驟也被 seed／closure 覆蓋；self._factory 目標是 orchestration layer，不在本盤點的特徵來源檔集合。另有 imported-class resolver 的實際漏列，詳 P2。

**(4b)** ② 本輪未命中會使 dispatcher/helper/column_filter 產生不穩定有限值的現行路徑。rg 未找到 np.nancumsum、scipy.signal filter、lfilter；scipy.stats.rankdata 僅見於 polars_adapter.py:459,491 及 rolling aggregator 的 propagating 路徑，Polars L6.5 rank 又由 pre-IC flag 關閉。mean/std/median 的命中是 metadata／scale 或不可達 non-causal 分支，非目前 no-inline 類別的輸出填值。

**(4c)** ③ 未命中。feature_factory.py:2830-2837 先將 rank／adaptive z-score／gaussian 設為 false；feature_preprocessor.py:2886-2898,2907-2921 只有 flag 為 true 才走 Polars rank/z-score，feature_preprocessor.py:1003-1010 將相同 flag 傳入 transform_array_fast。real probe 與 15 項 IC-first tests 均與此一致。

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
