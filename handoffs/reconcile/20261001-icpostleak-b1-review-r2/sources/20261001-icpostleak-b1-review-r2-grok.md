# ICPOSTLEAK B1 審碼 r2 — GROK

task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R2
brief: handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R2-BRIEF.md
family: GROK
brief-kind: review
findings-round: R2

本輪唯讀；標的＝r1 收斂＋修補 `40f863d4`。全面審。實跑在 `/tmp/qts-icpl-b1r2`（先 `isolate()`／`isolate_dstar_cache()`）。指令列與暫存路徑不含家族名。

## 必答（成對）

**(1a) 修法是否正確、無副作用？**

NaT 修法正確、無副作用。`time_order.py` 改相鄰直接比較並把 `isna()` 當違規；`pos` 改為與索引同長之 `bad[0]`（不再 `+1`）。五例現行碼皆在期望位置拋錯；合法嚴格遞增／RangeIndex／長度 0／1 不拋。`transform()` 入口兩 NaT 例同樣擋。改前 `np.diff(asi8)<=0` 為 mutant：r1 原反例（有效→NaT 兩元素）與末列 NaT **接受**；`nat_after_valid`／`nat_first` 測項紅（訊息位置 151／1，對不上 150／0）；`reverse`／`duplicate`／`single_disorder` 仍綠。

Task 1.1 量級收據已交付：`branchdiff` 42 對、shape／NaN 位置不一致 0、`residual_trigger_rel_gt_1e-3=true`。盤點收據 sharded 進入條件已改為 `can_shard_stream` 要求 `not requires_slow`。

**(1b) 實跑輸出**

複本 pytest 9 passed in 0.15s rc=0（rootdir `/private/tmp/qts-icpl-b1r2/repo`）：`test_time_order_non_increasing_raises` 五例、`test_time_order_strictly_increasing_ok`、`test_boundary_06`／`07`、`test_mutation_time_order_check_removed_is_caught`。
`/tmp/qts-icpl-b1r2/probe_mut.py`：`OLD_2ELEM_NAT ACCEPTED`／`NEW_2ELEM_NAT RAISE` 位置 1；`OLD_TRAIL_NAT ACCEPTED`／`NEW_TRAIL_NAT RAISE` 位置 299；`MUTANT_RESULTS` reverse／duplicate／single_disorder GREEN，nat 兩例 RED。

**(2a) assumed ①② 與「我沒查」1–4 是否成立？**

①成立：生產分派下 registry 帶 rank／zscore／gaussian 不可達。
②成立於跨臂同值集合：測試輸入為 float64（`_real_frame` `.astype(np.float64)`；EMA_21 有限值 unique 2980 vs float32 2977）。生產特徵 parquet 為 float16／float32 混用（非一律 float32）；float16 值在 float32 與 float64 皆可精確表示，unique 數相等（547＝547），跨臂 rank 同值差不會由落盤量化單獨產生。否證觀測①未出現；② IC 頁讀入欄非 float64 為預設（見下）。

我沒查 1：成立為生產不可達。`_layer6_5_post_ic` 尊重使用者 zscore 開關且 `_run_layer6_5_preprocessor` 在 registry 非空時走 `transform_registry_groups`；但生產無呼叫者傳 `selected_features`。`run_ic_first` 開頭 `self._cgsa_registry = None`，post-IC 經 `transform_selected`。`multi_tf_generator.py:1430-1435` 把 `_layer6_5_preprocessing` 當 callback 交給 `_execute_l65_with_degradation`，後者 `func(all_features, config)` 兩參 → pre-IC，三項強制關。L7 raw 同。IC 頁 `transform_selected`，`polars_enabled()` 預設開。

我沒查 2：8000×32 價位級 float32、窗 100：`transform_array_fast` zscore 0.0016s／tracemalloc 4.1MB；`_rolling_zscore_2d` 0.0139s／13.4MB（時間 8.8×、記憶體 3.3×）。遮罩後有限格 max_abs 0.0020（合成資料；真實收據 zscore 單步 0.038 為準）。

我沒查 3：Polars 單步 zscore max_abs 4.74e-5、p99 1.22e-5，對 IC 特徵排序足夠；其 max_rel 0.0076 仍 >1e-3，是分母近零而非核心偏差。

我沒查 4：相對差分母＝|legacy|，近零放大。`registry|rank+zscore` 之 max_rel 58.82 落在 row=2843 col=3，legacy=3.46e-8、abs=2.03e-6。該組合 max_abs=0.0953（rank 同值放大，rel 於該格僅 0.032）。N_REL>1e-3＝159，N_ABS>1e-3＝85，N_ABS>0.01＝13。

**(2b) 碼證或輕量實跑**

`feature_factory.py:2625`／`:2730`／`:2971-2982`／`:3106-3116`／`:3136-3151`；`multi_tf_generator.py:1430-1435`；`_execute_l65_with_degradation` `func(all_features, config)`；`ic_analysis_service.py:2921`；`polars_adapter.py:88` 預設 ON、`:115` `use_float64=False`。
探針：`TEST_INPUT_DTYPE ['float64']`；`features/BCHUSDT/1h/…/raw/1h_L1_trend_SMA.parquet` dtypes=['float16']；filtered h5 `float32`。`/tmp/review-7e8d/after.npz` 重算 max_rel 格如上（與收據 `max_rel_diff_overall` 逐字相同）。

**(3a) §N 殘留第一條之處置**

維持殘留。把「為何現在不做」從 `needs-research` 改寫為 `blocked-by: SPEC Task 1.1 不可做「不得改三項之數值公式」；生產分派關閉 registry 之 rank／zscore／gaussian；§N 觸發指標以 |legacy| 為分母，近零 z 格把 abs 2e-6 放大成 58.8`。不採主委「本批改 registry zscore 核心＋殘留改為已處理」。

**(3b) 依據與主委立場之錯處**

資料品質：registry 單步 zscore 對價位級輸入之 float32 累積核 vs pandas float64，真實收據 max_abs 0.038、p99 0.009，與改前 HEAD `d31c170e` 逐格相同，非本批引入。生產可達性：IC 頁與 `run_ic_first` post-IC 走 Polars／`transform_selected`；registry 帶 zscore 不可達。成本：同上 8.8×／3.3×，registry 路徑原為避免 pandas 放大記憶體而設。

主委立場錯處：①用 max_rel 58.8 當「改 zscore 核心」的證據，該格 abs 僅 2.03e-6，是 |legacy| 近零放大，不是 58 倍核心誤差。②即使改 registry zscore 為 `_rolling_zscore_2d`，rank+zscore 仍有 float32 同值放大（max_abs 0.095），Polars 生產臂 rank+zscore max_rel=1.0、zscore max_rel=0.0076，觸發條件仍成立，殘留不能標「已處理」。③rank 同值差主席已主張不改，卻用 rank+zscore 的相對差當 zscore 核心改動的通過條件。④未量記憶體／耗時。本票 Task 1.1 明文不得改公式。

**(4a) 可否收第 1 批？**

可。NaT 漏擋與量級收據缺項已閉合；未來洩漏／窗未滿公開輸出不因本修補重開。§N 第一條維持殘留並改寫理由，不擋收批。

**(4b) 擋之 P0／P1：** none。

---

## GROK-R2-P2-01

**斷言**: 以「registry zscore 改用 `_rolling_zscore_2d`」把 SPEC §N 殘留第一條標成已處理不成立，因為現行觸發（max_rel>1e-3）由 |legacy| 近零放大與 Polars／rank 同值差共同點燃，該改動清不掉觸發。

**碼證**: `handoffs/run_receipts/20261002-icpostleak-branch-diff.json` summary `max_rel_diff_overall=58.82005852248459` at `registry_parallel_split|rank+zscore`，`max_abs_diff_overall=0.09747552871704102`（polars rank+zscore）；同檔 polars zscore `max_rel_diff=0.007619`、`max_abs_diff=4.74e-5`。`probe_change_report.py:103-104` 相對差分母＝`np.abs(ref[both])`。對 `/tmp/review-7e8d/after.npz` 重算 `registry|rank+zscore` 最大相對差格：row=2843 col=3 legacy=3.456e-8 got=-1.998e-6 abs=2.033e-6 rel=58.82；該組合 max_abs=0.0953。locate 收據 registry 單步 zscore max_abs=0.03847 p99=0.0092，`exact_float64_z` 與 legacy 吻合。

**類別**: doc-sync

**來源摘要**: handoffs/run_receipts/20261002-icpostleak-branch-diff.json#8fcb13eb146f;handoffs/run_receipts/20261002-icpostleak-branch-diff-locate.json#6c037695529b;handoffs/run_receipts/icpostleak_probes/probe_change_report.py#37ee67b52c39;docs/ICPOSTLEAK_SPEC.md#ca7efa80b0f9;handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R2-BRIEF.md#d43e4ce449a6

§N 原文觸發＝量級收據最大相對差 >1e-3。量級已量，`needs-research:差異量級是否超出 float32 精度` 已過期。修法：殘留維持；「為何現在不做」改 `blocked-by`（本票不改公式＋生產 registry 三項關閉＋觸發指標近零放大），附本收據數字。可行性：只改 SPEC §N 一句理由，不改數值核心、不改本批碼。若另開票統一核心，須改用絕對差或相對窗 std，並先量 registry 大群組記憶體。

---

ASSUMPTIONS_VERIFIED: NaT 直接比較＋isna 擋 r1 兩元素反例與末列 NaT；mutant 兩 NaT 例紅、其餘時間序例綠；assumed ①生產 registry 三項不可達；assumed ②跨臂 rank 同值差來自 float64 測試輸入；§N 觸發成立但 58.8＝abs 2e-6；Polars 為 IC 頁預設臂。
TESTS_RUN: 複本 pytest 9 passed in 0.15s rc=0；`/tmp/qts-icpl-b1r2/probe.py` 至 REL_METRIC／KERNEL_COST；`probe2.py` `PROBE2_COMPLETE`；`probe_mut.py` `MUTANT_COMPLETE`。
FAILURES_SEEN: probe.py 末段誤 import `_oracle_rank` 於 RANK_TIE 前已印完全部關鍵觀測，改 probe2 補 unique 數；無產品測試失敗。
SCOPE_CHANGES: none（唯讀；探針僅 `/tmp/qts-icpl-b1r2`）。
NUMERIC_OR_SCHEMA_IMPACT: none（審碼未改碼）。
產出: `handoffs/20261001-icpostleak-b1-review-r2-grok.md`
HANDOFF_NOT_UPDATED: 本輪 brief 唯讀，依 AGENTS 7 不另寫狀態交接；根 HANDOFF 未改。
WORKTREE_CHECK: `git status --short -- momentum api frontend tests templates config` 與開跑快照相同（既有 numba cache／golden l65 dirty 列未增減）。

VERDICT: proceed
BLOCKED-BY:
CLOSED:
