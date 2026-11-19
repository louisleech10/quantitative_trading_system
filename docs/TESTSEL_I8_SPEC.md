# TESTSEL I8 慢測試處置 — SPEC

> 狀態：v3（規格審 r3 兩家 proceed；收斂 `handoffs/reconcile/20261119-testseli8-x-review-r3/synth.md`：maxlag 兩條須證據方准 D、multitf 資料依序門檻、numview／ffprod 共用前比對、start_far 探針入驗證段）；v2（規格審 r2 收斂 `handoffs/reconcile/20261119-testseli8-x-review-r2/synth.md`：Task 2.4 補 multitf 與逐條表、§B BUDGET-5、worldquant 不得關閉之約束、Task 2.1 兩條探針步驟）；v1（規格審 r1 收斂 `handoffs/reconcile/20261119-testseli8-x-review-r1/synth.md`：Phase 2 與 Task 1.1 並行、Task 2.3 保留 worldquant 組合守衛、§B 補預算列、stable_start 逐條表；另依使用者「全規模為何不查？」新增 Task 2.4 全規模層與大機器專用檔）。其餘族於 Task 1.1 量測後補 Task 2.x。
> 來源：大綱 `handoffs/20261116-testsel-route-outline.md` 末節 I8 列（判準 Q1「每條 ≥10 秒須具名理由」、S4「只跑需要的」）；事實 `runs/testsel_route/i8/i8_facts.md`；分類底稿 `runs/testsel_route/i8/i8_triage.md`；R 候選逐條查證（唯讀子代理，2026-11-19，摘要併入 i8_facts）。
> 順序：大綱 F 列（全部項目完成後，於最終樹一次跑預設層全量）；I4b 建庫 2026-11-19 中止並移至 F（`runs/testsel_route/i4b/i4b_facts.md` 末節）。本項中途只跑受影響測試，不跑全量。
> 業界出處（判準 P0）：pytest `--durations`（https://docs.pytest.org/en/stable/how-to/usage.html#profiling-test-execution-duration）取逐條耗時；測試金字塔（慢整鏈改小段真實資料＋精確 oracle 單元測試，整鏈只留最少條）。

## §RISK 風險分級
- **大小**：大（改動多個量化正確性測試之規模與 oracle；look-ahead MR 屬 (d)）。
- **命中高風險原則**：(a) 數值／資料品質之測試規模、(d) ML／回測正確性（look-ahead 截斷 MR）。
- RISK-HIT: a,d

## §A 假設與待使用者確認
- 已驗證事實：`runs/testsel_route/i8/i8_facts.md`（D 類逐條覆蓋查核、F 類 icperf、L2 worldquant 覆蓋缺口、慢測試新鮮耗時盤點）。
- 已確認：使用者 2026-11-18「我要睡了，盡可能快速和平行進行，有問題你跟委員共識決定，不要停下來」；2026-11-19「跑這麼久才18%，然後跑幾十小時才要去查為何那麼久看要怎麼修？」。
- 待確認：無。

## §C 約束
- 不降偵測力：每條 D 須指出涵蓋其全部斷言之既存本機測試（檔:行）；每條 R 須以改壞對照證明新測試仍抓得到原測試所抓之 mutant；F 只用於小規模確實驗不到者並附小規模姊妹。
- 真實資料（`data_cache/feature_klines/kline_cache.h5`），禁合成 fixture；不改產品碼數值。
- look-ahead 類先補逐運算元截斷單元測試，再縮整鏈（i8_facts 高風險第 2 項：L2 worldquant 無逐運算元截斷測試）。
- 中途不跑全量；每批只跑受影響測試（`docs/TEST_SELECTION.md` §4）。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| TESTSEL-I8-BUDGET-1 | 過期耗時重量：`venv/bin/python -m pytest -q -p no:cacheprovider --durations=0 @runs/testsel_route/i8/durations/stale_nodeids.txt`（`scripts/run_watched.py` 背景） | 95 條「ledger 值已過期」之 ≥10 秒候選之現行耗時（決定 I8 處置對象與順序；不改任何檔） | 95 條（`runs/testsel_route/i8/durations/stale_nodeids.txt`） | 舊 ledger 合計 22482 秒為上界；已知多條經 I10 縮小（例 hac45 5170 秒→每格 2 次），實際應遠小於此 | 無 |
| TESTSEL-I8-BUDGET-2 | Task 2.1 處置前後：`pytest --durations=0 tests/feature_engineering/test_ffstat_calibration.py tests/feature_engineering/test_ffstat_stable_start.py`（各一次；同檔 `test_mutation_*`／leak 對照隨檔跑） | 校準決策路徑（前史截斷、d* 快取、L5 隔離、遮罩）改窄前後之 §G 偵測力收據 | 53 條×2 次 | 處置前 3593＋1074＝4667 秒（slow_rerank_local.tsv）；處置後 ≤ 處置前 ⇒ 上界 9334 秒 | 無 |
| TESTSEL-I8-BUDGET-3 | Task 2.2 處置前後：`pytest --durations=0 tests/feature_engineering/test_failopen_correctness.py -k "v6 or v7"`，另以 asof +1 前移與跨標的快取污染兩 mutant 各跑保留條 | as-of 對齊 oracle 與跨標的隔離之刪重前後偵測力 | 處置前 10 條、處置後 7 條；mutant 各一次 | 處置前 1379.5 秒（同檔 v6／v7 10 條）；處置後約 1013 秒；mutant 兩次約 2×1013 ⇒ 上界約 4419 秒 | 無 |
| TESTSEL-I8-BUDGET-4 | Task 2.3：新 worldquant 截斷單元測試（含 `ts_argmax` 窗含 t+1 mutant）；v5_prefix 處置前後各對「L3 center=True」「`_apply_worldquant` L1 欄索引錯位」「ts_rank 窗含 t+1」三 mutant＋無 mutant 各一次 | L1→L2（worldquant）→L3→落盤組合前綴之偵測力 before／after | v5_prefix 4 次×2；單元 < 60 秒 | v5_prefix testmon 316.3 秒×8 ≈ 2530 秒（窄化後實際應較短）＋單元 < 60 秒 | 無 |
| TESTSEL-I8-BUDGET-5 | Task 2.4 處置前後：各 R-speed 對象 `pytest --run-fullscale --durations=0 <nodeid>`（`scripts/run_watched.py` 背景、記峰值 RSS）；HW 兩檔先量本機峰值記憶體；multitf 無 ledger 耗時者實量；trunc 共用前以一次實跑證輸出逐位元相同 | 全規模層與 HW 檔各 nodeid 之獨有路徑（逐條見 `runs/testsel_route/i8/fullscale_table.md`）於處置前後之偵測力與本機可跑性 | R-speed 對象約 12 條×2 次；HW 兩檔 | 處置前合計：fullchain c2_1＋c2_2 3413＋3463、batch2d 2742、preprov verification_03 1282、la1 kmeans 836＋b4 654、numview／ffprod C＋B 格約 1044＋1059＋380＋392、failopen ETH 537 ≈ 15,802 秒（`fullscale_all.tsv` 與 fullscale_table.md）；處置後應較短 ⇒ 上界約 31,604 秒；multitf 未量（uncertain） | 無 |

- 不降驗證之省法：只重量過期者；testmon 11-19 實量 134 條、I10 後 worktree ledger 210 條、未過期 89 條沿用，不重量。
- 小規模驗不到之理由：耗時本身即被量之對象，無法以小規模代替。

## §B 四項平衡實測
- 耗時：每族處置前後同命令 `--durations=0` 對照（處置後之值以受影響測試實跑取得）。
- 記憶體：不涉（不改產品碼）。
- 精度：不涉（不改數值；R 類 oracle 精確比對）。

## §G Golden / Baseline
- 本項不改產品碼，產品數值不變；被改動者為驗證測試本身。基準＝原測試之偵測力：每條 R／D 處置前，以原測試對其 docstring 所列 mutant（或 `ff_truncation_mr_helpers.py` 之既有變異注入）實跑紅、處置後新測試對同一 mutant 實跑紅，兩者皆附收據；R 類 oracle 對真實 kline（`data_cache/feature_klines/kline_cache.h5`）小段逐值比對（`np.testing.assert_array_equal` 或 float32 `atol` 具名）。
- 凍結時機：每族處置前於同一提交跑原測試取收據（路徑 `runs/testsel_route/i8/<族>/before.log`）。
- 通過條件：原測試抓到之 mutant 集合 ⊆ 新測試抓到之集合；任一 mutant 新測試未抓到 ⇒ FAIL，該條不得處置。

## §P Phase 與依賴

### Phase 1（依賴：無）
**Task 1.1 — 過期耗時重量**
- 改法：不改檔；跑 `TESTSEL-I8-BUDGET-1`。
- **驗證**：收據 `runs/testsel_route/i8/durations/stale_measure.log` 之 pytest `--durations=0` 列出 95 條逐條耗時、passed＋failed＋skipped == 95；併入 `slow_rerank.tsv` 後重排。
- **邊界**：失敗者逐條記錄，不在本 Task 修（歸 I1 收尾）。
- **存活至**：Task 2.x 排序完成。
- **覆蓋風險**：無（只量測）。
- 不可做：不改 tests／產品碼。

**Task 1.2 — TESTREG V19 接受 §G 前後收據（使用者 2026-11-19 裁定）**
- 依據：使用者於 AskUserQuestion 選「§G 前後收據代替（建議）」——I8 改窄之測試以 §G mutant 前後收據為證，免做 V19 逐斷言 rewrite 收據（`scripts/testreg.py:2249` `_rewrite_ok` → `:1764` `_rewrite_receipt_errors` 只認 `types.receipt_mutation`，須乾淨 HEAD 樹逐斷言 mutant；全 repo 現僅 1 份，`handoffs/run_receipts/testreg-rewrite/test_timeout_registry-rewrite.json`）。
- 改法：`_rewrite_receipt_errors` 讀到收據 `kind == "g_before_after"` 時改走新驗證 `_g_receipt_errors`；`tests/registry/testreg_schema.json` 新增 `types.receipt_g_before_after`：`kind`、`spec_ref`（須為 `docs/TESTSEL_I8_SPEC.md`）、`user_ruling`（字串）、`head`（40-hex）、`targets`（函式層 nodeid 陣列）、`narrow_patch_path`、`narrow_patch_sha256`（改窄補丁：只含被改之測試檔）、`mutants`（≥1；每項 `id`、`plugin_path`、`plugin_sha256`、`before_session_id`、`after_session_id`、`before_outcomes`、`after_outcomes`）。驗證規則（v2，依規格審 r4 收斂）：
  ① `set(targets)`＝catalog 該檔 `rewrite_targets`；每個 mutant 之 `set(before_outcomes)`＝`set(after_outcomes)`＝`set(targets)`。
  ② plugin 檔存在且 sha256 相符；plugin 源碼（AST）須 import `receipts.E0.production_roots` 下之模組，且對其屬性有寫入（Attribute Store 或 `setattr`）——只 `pass`、只 `pytest.fail`、只改測試或 fixture 者不成立；且模組層 `pytest_*` hook 只准 `pytest_configure` 一個（禁以 setup／call 等 hook 造假失敗）。
  ③ session 綁定：before ≠ after 且 before 之 `started` 早於 after；兩者 `head`＝收據 `head`，且 `head` 為受驗 HEAD 之祖先或相等；before 之 `diff_digest`＝`clean`（乾淨 HEAD 樹，`runs/testsel_route/clean_head` worktree）；after 之 `diff_digest`＝`_digest_with(ctx, head, [narrow_patch_path])`（`scripts/testreg.py:1573`，記錄器同算法）；narrow_patch 套於 head 後之該測試檔＝受驗之樹之該檔（逐位元）；`argv_raw` 中 `-p` 之下一 token 恰為 plugin 模組名；每個 target 對 before、after 各呼叫既有 `session_scope_errors`（`scripts/testreg.py:3631`；須跑全部參數案例、無 `-k` 等篩選）皆空。
  ④ `before_outcomes`／`after_outcomes` 逐 nodeid 等於 ledger 紀錄。
  ⑤ 逐 mutant 逐 target 單調：「抓到」＝ledger 紀錄 outcome ∈ {failed, error}、`phase_failed`＝`call`，且 `fail_frames` 至少一個落在該 target 函式本體行範圍（改前取 head 之檔、改後取 head＋改窄補丁之檔；外掛於 pytest_configure 內動態註冊 hook 造假之失敗 frame 不在 target 函式內，不計）；before 抓到 ⇒ after 須抓到。本條證「收據所列 mutant」之前後偵測力不降；mutant 集合是否充分（是否涵蓋被刪斷言所守之行為）由每批審碼委員判，同 `receipts.mutation` 之「mutant 集合之充分性由每子批審碼委員判」。
  ⑥ 至少一個 mutant 於 before 依⑤之定義抓到至少一個 target。
- **驗證**：`pytest tests/registry/test_testreg_g_receipt.py`（新檔）一正例與反例：targets 不等、outcomes 缺 target、plugin sha 不符、plugin 未改產品碼（只 `pytest.fail`／`pass`）、session 不存在、before 與 after 同 session、after 早於 before、before 非乾淨樹、after 之 diff_digest 非改窄補丁所得、narrow_patch 與受驗檔不符、argv 之 `-p` 下一 token 非該 plugin、session 以 `-k` 篩選、outcome 與 ledger 不符、逐 target 偵測力下降（含「改前 T1 紅、改後只 T2 紅」）、全部 mutant 改前皆綠、head 不符、spec_ref 不符；改壞對照：刪除規則⑤之檢查 ⇒「改前紅改後綠」反例轉綠（測試須紅）；既有 `tests/registry/test_testreg_validate.py` 全綠（mutation 收據路徑不變）。
- **邊界**：只放行 `rewrite_targets` 內之 nodeid；`kind` 缺或為其他值時行為與現行逐位元相同。
- **存活至**：永久。
- **覆蓋風險**：無（mutation 收據路徑不變；新類型只放寬「乾淨樹逐斷言」為「收據所列 mutant 前後偵測力不降」；mutant 集合之充分性由審碼委員判，與 `receipts.mutation` 同）。
- 不可做：不改 V19 判定本身（斷言多重集合計算不變）；不改既有 mutation 收據規則。

### Phase 2（依賴：無，與 Task 1.1 並行；只剩 ledger_STALE 耗時之族方依賴 Task 1.1 該族 nodeid 之重量結果）
**Task 2.1 — ffstat 校準族改窄設定（`tests/feature_engineering/test_ffstat_calibration.py` 31 條 3593 秒、`test_ffstat_stable_start.py` 22 條 1074 秒；耗時來源 `runs/testsel_route/i8/durations/slow_rerank_local.tsv`）**
- 改法：仍用全設定 `stat_payload`（`tests/feature_engineering/ffstat_helpers.py:92`）且被測行為與 L1 寬度無關者改 `narrow_stat_payload`（:125）；逐條判定見 `runs/testsel_route/i8/i8_facts.md`「R 類逐條查證」節。兩條 leak 測試另建 narrow 基準 run（不再共用全設定 `user_run`）；`test_boundary_08_default_runs_no_column_short[*]` 維持全設定（驗最慢欄，docstring :827-836），具名列 Q1 理由；`test_three_paths_same_n[*-500]` 先以探針確認 narrow 下 `adf_differencing` 路徑仍有欄進候選迴圈，無則維持。stable_start 逐條判定（唯讀子代理讀碼，主委抽驗 :641、:652、:769、:1310、:1394 相符；全表存 `runs/testsel_route/i8/stable_start_table.md`）：
  | nodeid（`tests/feature_engineering/test_ffstat_stable_start.py::`） | 現用 payload（行） | 處置 | 理由 | 秒 |
  |---|---|---|---|---|
  | test_no_start_calibration_rows_masked_from_output | stat_payload()（:652） | 改 narrow＋補斷言 | 斷言只要求校準呼叫、per_column、各基礎欄校準列 NaN，與寬度無關；docstring :641 稱「含衍生欄」但迴圈 :656-661 只走基礎欄 ⇒ 補 `_fracdiff`／`_diff-K` 衍生欄校準列 NaN 斷言（產品 `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:421` `_DERIVED_SUFFIX_RE`、:423 `_mask_no_start_rows`），並斷言至少一欄帶 `calibration_end`（防 :657 `continue` 空轉） | 206.8 |
  | test_multi_tf_mask_applied_before_alignment | stat_payload(["1h","12h"], off)（:1310） | 改 narrow | 主斷言對任一 12h 欄成立（`checked>0`），:1313–1314 一併換 | 73.7 |
  | test_with_start_near_data_start_flags_slow_columns | stat_payload(off)（:1129） | 改 narrow | 窄仍含慢欄 KAMA_233（K=2478）與快欄 EMA_5 | 46.7 |
  | test_boundary_24_reference_symbol_origin | stat_payload(off, cross_sectional=True)（:1432） | 改 narrow＋補斷言（先以 narrow 試跑，斷言 `any(c.startswith("cs_") for c in stable)` 成立才改；不成立則維持並寫 Q1） | 只比 `cs_` 欄；補「`cs_` 欄非空」斷言防空轉 | 44.1 |
  | test_no_start_insufficient_history_column_flagged | stat_payload()（:747） | 改 narrow | 700 列、N=500，窄之 EMA_89（K=389）必被標記 | 30.5 |
  | test_boundary_23_cumulative_listed_start_dependent | stat_payload(off)＋OBV（:1418） | 改 narrow | 只看 OBV | 29.3 |
  | test_dead_filter_shared_by_l3_and_l7 | stat_payload(off)＋L7 drop（:1170） | 改 narrow | 只驗兩呼叫端門檻組合 | 28.8 |
  | test_with_start_far_no_warmup_insufficient | stat_payload(off)（:769） | 探針後定（探針：以 narrow 單跑本條，斷言 :776–784 第二次生成分支確有進入且其斷言實際執行；未進入則維持並寫 Q1） | :776–784 第二次生成分支依資料（docstring 例 MIDPOINT_144 Kurt，窄已無），改窄恐空轉 | 59.3 |
  | test_no_start_stationarity_off_stable_values_unchanged | stat_payload(off)（:608） | 維持 | 逐欄比凍結 nostart 基準（全設定欄集合） | 48.8 |
  | test_every_l1_output_column_passes_output_point_contract | 預設全設定（:1394） | 維持 | 斷言即「預設全設定之每個 L1 輸出欄」 | — |
  其餘：13 個節點已用 narrow，67 個節點不生成特徵（單元／靜態／只 resolve 或算 hash），不適用。
- **驗證**：`pytest --durations=0 tests/feature_engineering/test_ffstat_calibration.py tests/feature_engineering/test_ffstat_stable_start.py` 處置前後對照；§G：每條改窄者以其原 mutant／對照（同檔 `test_mutation_*` 與 leak 對照）實跑仍紅；`test_leak_pre_history_change_changes_some_decision` 改窄後至少一欄 (p, d) 改變（assert 不放寬）；必跑探針：`pytest --durations=0 tests/feature_engineering/test_ffstat_stable_start.py -k with_start_far_no_warmup`（narrow 版）通過條件＝:776–784 第二次 `run_stat` 分支確有進入且 :782–784 斷言實際執行（以 spy 或計數確認），未進入則該條維持；`-k boundary_24_reference_symbol_origin`（narrow 版）通過條件＝`cs_` 欄非空斷言成立。
- **邊界**：12h 欄前史不足分支（`test_second_tf_insufficient_history_column_skipped[*]`）改窄後 1h 仍須有已檢定欄（斷言不變）。
- **存活至**：永久。
- **覆蓋風險**：最慢欄（DEMA／TEMA_233 Cross、MIDPRICE_233 Kurt／Skew）之前史深度只由 `test_boundary_08_*` 守，該條不改。
- 不可做：不放寬任何斷言；不改產品碼。

**Task 2.2 — failopen 重複執行刪除（`tests/feature_engineering/test_failopen_correctness.py`）**
- 改法：①`test_v6_backend_output_matches_independent_oracle`（:1062）與 `test_v6_close_time_oracle_matches_pipeline`（:1080）去掉 `use_searchsorted` 參數化（兩值走同一產品路徑：`momentum/FeatureEngineering/timeframe/tf_aligner.py:168` `build_asof_index_map` 恆用 `np.searchsorted`，`FFACT_USE_SEARCHSORTED` 只在無呼叫者之 `align_to_primary` :72 讀），各留一條、保留兩對齊模式之 oracle；②刪 `test_v7_cross_symbol_isolation`（:1120），其斷言由 `test_v7_symbol_order_permutation_invariant`（:1189）涵蓋（逐條見 i8_facts「D 類逐條覆蓋查核」）。
- **驗證**：處置後 `pytest --durations=0 tests/feature_engineering/test_failopen_correctness.py -k "v6 or v7"` 全綠；testmon 11-19 實量刪除對象合計 91.7＋91.7＋182.7＝366.1 秒（`[False]` 兩條、isolation 一條）；§G：對 `TimeframeAligner.build_asof_index_map` 注入 +1 前移之 mutant，保留之 v6 兩條皆紅；對 factory 模組層快取注入跨標的污染之 mutant，permutation 條紅。
- **邊界**：`FFACT_USE_SEARCHSORTED` 死開關本身之處置另開票（i8_triage 高風險第 3 項），本 Task 不動產品碼。
- **存活至**：永久。
- **覆蓋風險**：無（被刪者之斷言由所指測試承擔）。
- 不可做：不刪 `test_v6_*` 任一對齊模式之最後一條。

**Task 2.3 — L2 worldquant 逐運算元截斷單元測試（補缺口）→ failopen v5_prefix 改窄設定**
- 改法：①新增單元測試：對 `ts_argmax`／`ts_argmin`／`ts_rank`／`decay_linear`／`ts_corr`（`momentum/FeatureEngineering/operators/derived_operators.py:750` `_apply_worldquant`；numba 快路徑 `operators/_worldquant_numba.py:101`、`:110`、`:118`）於真實 kline 收盤價小段（`data_cache/feature_klines/kline_cache.h5`），對每個 t 斷言「以 series[:t+1] 計算之第 t 值 == 全序列計算之第 t 值」（逐位元，NaN 位置相同），窗含預設最大 21，含 NaN 前綴；②①通過且改壞對照成立後，`test_v5_prefix_no_leakage_after_warmup`（`tests/feature_engineering/test_failopen_correctness.py:521`，testmon 316.3 秒，用全寬 `_fast_config_payload()` :538）改用窄 L1（同檔 I10 已用之 `_narrow_atomic_indicators()` :123，EMA_8／SMA_13），整鏈前綴逐位元比對保留以守接線與落盤；`_fast_config_payload()`（:101）不覆寫 operators，預設 `config/scan_config.yaml:543` `worldquant.enabled: true` 照舊生效，窄化設定另**顯式**寫 `operators.worldquant.enabled=True` 且保留 L2 cross／ratio（兩條 trend 欄使 auto 配對有對象），使「L1→L2（含 worldquant）→L3→落盤」組合前綴仍於本機整鏈覆蓋。
- **驗證**：①之改壞對照：對 `ts_argmax` 注入「窗含 t+1」之 mutant，新測試紅；`pytest --durations=0` 新測試每條 < 10 秒；②處置後 v5_prefix 綠，並對 L3 rolling 注入 `center=True` mutant 仍紅（既有 `ff_truncation_mr_helpers.py` 變異注入）；另對 `_apply_worldquant`（`derived_operators.py:750`）注入「L1 欄索引錯位（取下一欄之值）」與「ts_rank 窗含 t+1」兩 mutant，窄 v5_prefix 皆紅（處置前寬 v5_prefix 對同兩 mutant 亦須紅，收據 before／after）。
- **邊界**：`ts_corr` 須帶 `corr_with` 欄（`derived_operators.py` `has_corr` 條件）；窗大於可用長度時之 NaN 行為兩側一致。
- **存活至**：永久。
- **覆蓋風險**：寬 L1（數十指標）之整鏈前綴不再於本機預設層跑；L1→L2（含 worldquant）→L3→落盤之組合由窄 v5_prefix 守（worldquant 顯式開），逐運算元因果由①守、L1 各指標因果由既有小規模 MR 守（`ff_truncation_mr_helpers.py:238` L1 trend／momentum）；寬 L1 整鏈由 Task 2.4 之全規模層承擔。
- 不可做：①未綠前不得縮 v5_prefix；Task 2.4 處置 fullchain／multitf 全設定時不得將 `operators.worldquant.enabled` 設為 False；若 Task 2.4 收據未證 fullchain 全設定 worldquant 仍開且本機可跑，則保留本 Task 之窄 v5_prefix（worldquant 顯式開）為該組合之本機守衛，不得再縮。

**Task 2.4 — 全規模層（`@pytest.mark.fullscale`，23 函式）與大機器專用檔（`tests/hardware_requirements.json` 兩檔）**
- 依據：使用者 2026-11-19「全規模為何不查？」；全規模層於大綱 F 列與收案皆跑，須在本機以可接受時間跑完，本機做得到者不得推給大機器（使用者原則，CLAUDE.md「使用者原則通用量化主線」2026-10-28 條）。耗時 `runs/testsel_route/i8/durations/fullscale_all.tsv`（`venv/bin/python runs/testsel_route/i8/fullscale_durations.py` ⇒ `FS: 17 條 6.1 小時`、`HW: 5 條 4.5 小時`；多為主 ledger 值）。
- 改法：逐條表 `runs/testsel_route/i8/fullscale_table.md`（全規模層 23 函式＋HW 兩檔全部函式；獨有路徑、小規模姊妹檔:行、慢在哪、處置）。處置摘要：
  - D：`test_ff_fullchain_truncation_mr.py` 5 條層 seam／calibration `test_mutation_*`（numba_rolling_center_true、causal_winsor_full_fit、l4_lag_shift_minus_one、fracdiff_calibration_perturb、fracdiff_full_fit_d_star；同本體由 `test_ff_fullchain_truncation_small_mr.py:112–128`、allcat `:92–100` 涵蓋）。maxlag 兩條（`test_mutation_fracdiff_maxlag_len_coupling_{truncation,parallel}_fails`，:176、:187）施工前 REQUIRED 證據其一：①解析 FULL_SCOPE 必要窗長，依 `_resolve_fracdiff_max_lag`（`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:2692`）與 mutant `lag=max(2,len(df)//10)`（helpers:1867）證兩 run 之差異落在權重門檻外；②`scripts/run_watched.py` 試跑兩控制皆 DID NOT RAISE；證據成立方准 D，否則 keep 並寫 Q1；`test_ff_multitf_truncation_mr.py` 3 條層 mutation（:166、:170、:174；姊妹 `test_ff_multitf_truncation_small_mr.py:133`、:137、:141）。
  - R-speed（規模不變）：fullchain c2_2 與 fracdiff tail 兩對之 trunc 與 c2_1／fracdiff_truncation 共用 module fixture（L0 於計算前以 end_date 切片，`momentum/FeatureEngineering/feature_factory.py:949-952`；施工前以一次實跑證 trunc 輸出逐位元相同）；batch2d `TestP4Parity::test_cgsa_baseline_runs_ic_first_not_legacy_frozen` 刪 repeat run（NaN 可重現由 :262 姊妹承擔）；preprov `test_verification_03_*` 與 03a 同 session；la1 kmeans 與 b4 共用 analyze／detect；numview 與 ffprod §G 之 C、B 格共用生成（共用前比對兩檔同一格之 regen 路徑、env 與 config hash，不一致則 ffprod 列維持並寫 Q1；一致則附單次共用 session 收據再施工）；failopen ETH 略過未被斷言之 `l1_direct`。
  - 標記修正：`test_la1_lookahead.py::test_regime_pit[rule]` 移回預設層、`[mid_segment]` 移除 fullscale 標記（只用約 425 根）；numview_acceptance 之 fullscale 只留 B、C 參數。
  - 搬檔：HW 檔內 3 個秒級 smoke（`test_b2_sampling_helper_smoke`、`test_multitf_sampling_helper_smoke`、`test_align_lookahead_oracle_smoke`）因整檔 deselect 本機從未跑，搬至非 HW 檔。
  - 維持＋Q1：failopen v3_multi_tf、ffstat_golden 四週期、icperf freeze_reproducible、numview_core postic、feature_factory_e2e standard preset、fullchain c2_1 與 fracdiff 兩 xfail。
  - HW 本機可跑：fullchain 刪 mutation 後剩 4 條之峰值記憶體實量（原整檔紀錄 4.55 GB＋3.29 GB 兩度 SIGKILL，`test_ff_fullchain_truncation_small_mr.py:3`），超 8 GB 則以分塊／串流或縮非 worldquant 維度處理；multitf 資料缺口（1h 需 ≥34,302 根、本機 20,352 根，`tests/hardware_requirements.json:16`）依序門檻（使用者原則「資料不足就要補齊到可以跑和測試」）：①補下載 BTCUSDT 1h ≥34,302 根真實長歷史並記命令與結果，成功則完整版入 BUDGET-5；②僅①失敗（附原因）時跑 small＋12h 探針並對 :156／:161 對齊 mutant 實跑仍紅、附窗長依據；③僅①②皆不可行且附具體原因時方准維持＋Q1；multitf 函式無 ledger 耗時者由 BUDGET-5 實量。
- **驗證**：每條處置後於本機 `pytest --run-fullscale --durations=0 <nodeid>` 實跑綠、附峰值 RSS（`scripts/run_watched.py` 紀錄）；HW 檔處置後本機不再 SIGKILL 且 `tests/hardware_requirements.json` 移除該檔；§G 同上（mutant before／after）。
- **邊界**：凍結基準比對類（frozen baseline／bitwise）不得改凍結值，只改執行方式；fullchain／multitf 全設定處置不得將 `operators.worldquant.enabled` 設為 False，省記憶體只准分塊／串流／縮非 worldquant 維度。
- **存活至**：永久。
- **覆蓋風險**：D 類須指出姊妹檔:行。
- 不可做：不以縮小規模取代全規模（全規模層之存在理由即規模）；不改產品數值。

**Task 2.x — 逐族處置**（量測後依耗時由大到小補寫，一族一 Task；每 Task 含 D／R／F 逐條清單、涵蓋證據、改壞對照、前後耗時）
- 改法：依 Task 1.1 重排結果逐族補寫。
- **驗證**：每族 `pytest --durations=0 <該族受影響檔>` 處置後每條 < 10 秒或具名理由（Q1）；§G mutant 收據 before／after 皆紅。
- **邊界**：look-ahead 類先補 L2 worldquant 逐運算元截斷單元測試（`ts_argmax`／`ts_argmin`／`ts_rank`／`decay_linear`／`ts_corr` × 窗 21 × NaN 前綴）再縮整鏈。
- **存活至**：永久。
- **覆蓋風險**：D 類刪除後由所指既存測試承擔，§C 要求逐條檔:行。
- 不可做：不改產品碼；不以合成資料取代真實 kline。

## §V 驗證策略與邊界測試目錄
- 單元：R 類新 oracle 測試＋改壞對照；時間：處置前後 `--durations=0`；量測：§B 收據。
- 收案機械邊界：manifest（Phase 2 定稿後建立）之 `gate_cmd`。

## §R 回退
- 每族一提交，`git revert` 該提交即回到原測試。

## §N N/A 登記
- 無。
