# Reconcile — 20260926-ffstat-b6-review-r1

**來源** 20260926-ffstat-b6-review-r1-codex.md, 20260926-ffstat-b6-review-r1-composer.md, 20260926-ffstat-b6-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/FFSTAT_SPEC.md

codex 三條 P1 經主委讀碼核實皆成立，且**既有兩檔之同名控制同樣受影響**（非縮小版引入）：①fracdiff 長度耦合 mutant 之 `min(len//10, 252)` 於現行必要窗（fracdiff 3,342 根）兩邊皆飽和為 252，未注入差異；②校準擾動仍改起始日之後之公開域前 500 根，FF-STAT 後校準只讀起始日之前之前史（codex 實證校準域零列被擾動）；③生成與準備檢查包在 `pytest.raises(AssertionError)` 內，缺 L4／抽樣設計錯誤可冒充「抓到」。修法（SPEC v60）：負控制之函式本體移入 `ff_truncation_mr_helpers.py`（`MRScope`＋`run_control_*`），既有兩檔與縮小版兩檔共用同一本體、只差設定；生成與準備證據（可比後綴、共同欄、抽樣層覆蓋、seam 呼叫次數）一律在捕獲區外，捕獲區只收因果 gate 前綴之 AssertionError；長度耦合 mutant 去上限（實得 334／333）並記實際 max_lag；校準擾動改為 full 側起始日之前之前史並以 d\* 差異為證。另主委實跑新增之分母尺度 mutant：基線 c2_1 綠（506 秒）、mutant **存活**（DID NOT RAISE；trunc 只少 10 根，全欄中位數穩健幾不變，近零遮罩不變）⇒ 截斷 MR 結構上看不到此類「穩健全域統計量」洩漏；該缺陷已由 `tests/feature_engineering/test_ffstat_stable_start.py::test_mutation_denominator_full_column_median_is_caught`（起算點相依）承接 ⇒ 自 Task 4.2 撤除並記收據。composer P1（未跑 mutant、收據未產）＝本 Task 之驗收條本身，於修補後實跑產出；composer P2（縮小版不含 12h 對齊）與 SPEC 誠實邊界一致，明示於 Task 4.2 與 RM-FULLSCALE ⑤。fracdiff 兩基線（既有 strict xfail）於縮小設定之結果實跑中，用以決定 fracdiff 控制能否以 MR 判別（若基線仍 XFAIL，fracdiff 值 gate 與 codec 既有失敗混淆，控制改以 d\* 與 seam 證據判定）。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 長度耦合：縮小版三個fracdiff長度耦合控制仍 | P1 | CODEX-R1-P1-01 | 採納（去上限、記實際 max_lag；共用本體；既有檔同修） | code-contract |
| 校準擾動：縮小版「calibrationpertu | P1 | CODEX-R1-P1-02 | 採納（改擾動起始日之前之前史；d\* 差異為證；既有檔同修） | code-contract |
| 寬捕獲：新分母尺度控制把`_build_trun | P1 | CODEX-R1-P1-03 | 採納（準備證據移出捕獲區、只收因果 gate；全部控制同修；分母 mutant 實跑存活後撤除改由起算點測試承接） | code-contract |
| 驗收條：SPECv59Task4.2要求兩新檔* | P1 | COMPOSER-R1-P1-01 | 採納（屬本 Task 驗收條，修補後全跑產收據） | code-contract |
| 12h 對齊：多週期縮小版將`ALIGN_COARSE | P2 | COMPOSER-R1-P2-01 | 採納（誠實邊界已明示；完整版登大機器清單） | code-contract |
| 放行：本輪逐項核對後無finding；Task | P3 | GROK-R1-P3-00 | 部分採納（proceed 不採：codex 三條 P1 有實證反例） | other |

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01

**斷言**: 縮小版三個 fracdiff 長度耦合控制仍沿用飽和的 `min(len(df)//10,252)`，在實際 full／trunc 窗長下兩邊皆為 252；即使控制測試綠，也不能證明抓到長度耦合，尤其兩個正常 fracdiff 基線仍預登記 codec xfail。

**碼證**: `test_ff_fullchain_truncation_small_mr.py:77-96` 直接委派既有基線／控制；既有 `test_ff_fullchain_truncation_mr.py:173-193,210-232,249-292` 注入 capped resolver，僅檢查 `lengths_seen`／parallel 呼叫與任意 AssertionError。`ff_truncation_mr_helpers.py:158-160` 由必要 warmup 算窗。複本命令 `PYTHONDONTWRITEBYTECODE=1 /Users/louis/Desktop/quantitative_trading_system/venv/bin/python probe.py` rc=0：`fracdiff=3342`，trunc=3332，`mutant_maxlags=[252,252]`；去 cap 的算術可行性探針得到 `[334,333]`，不是生成通過聲明。
CODE-ANCHOR: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py:87
MUTATION: 複本內把委派控制之 resolver 換成 `lambda: 252`（與 full/trunc 現有 capped resolver 同值）；原 `lengths_seen`／parallel_calls 仍可滿足，原 codec AssertionError 仍被當作抓到，沒有參數差異守衛。

**來源摘要**: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py#a8a8e2e7cc1e4

**類別**: code-contract

影響：正常 resolver 依 N=500 得 50；兩邊同改 252 可以改變算子，卻不構成這一對輸入的「依總長度改參數」反例。strict codec xfail 的同設定基線不能滿足 SPEC「正常基線綠」；任意 fracdiff AssertionError 不足以區分 codec 既有失敗與 mutant 引入的洩漏。本輪未跑 fracdiff 生成，因此不聲稱這三項實際已假綠或存活；已驗的是其前提退化与現行斷言不能排除假綠。

修法：只在新縮小入口調整此控制的長度耦合注入，使真實 full／trunc 解析出的 max-lag 不同，並記錄實際傳入 serial／parallel 的值；保留必要窗，不為避 cap 縮掉 warmup。例：去掉該 mutant 的 252 cap，在本例得到 334／333，仍小於 500 校準根数，參數計算本身可行；是否造成可辨識的數值差異仍須正常與 mutant 生成實證。控制驗收還需與同設定正常 fracdiff 基線區分 codec 既有失敗；若該基線仍 xfail，不能直接把同一 codec 失敗作 mutant 成功收據。這需要調整新入口及 Task 4.2 的「原控制照搬」限制，不改舊 gate／容差／舊兩檔，不新增機制或慢閘。可行性依據：秒級 resolver 探針與既有 serial／parallel `max_lag` 顯式參數（preprocessor:3464-3466,3555-3560,3701-3742）；完整行為修復未驗證。

## CODEX-R1-P1-02

**斷言**: 縮小版「calibration perturb」控制沿用舊公開域前 500 根擾動，沒有改到 FFSTAT 現行起始日前校準資料；因此其 columns／d-star 失敗不能按測試名稱解讀成校準擾動鑑別力。

**碼證**: 新檔:111-112 委派既有 `test_mutation_fracdiff_calibration_perturb_fails`；舊檔:399-430 用 `_patch_kline_calibration_ohlcv(window_bars=3342, calibration_bars=500)`。helpers:1434-1447 的範圍是 `len(df)-window_bars` 起的 500 列；factory:2408-2420 在全量 fetch 後只取 `index < output_start` 作校準，preprocessor:576-582 只讀封包。複本命令 `PYTHONDONTWRITEBYTECODE=1 /Users/louis/Desktop/quantitative_trading_system/venv/bin/python evidence.py` rc=0，真實 BTCUSDT/1h 20352 列，output_start=`2025-12-09 18:00:00`，`changed_before_start=0`、`changed_at_or_after_start=500`。
CODE-ANCHOR: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py:111
MUTATION: 以現行真實 K 線呼叫 `_patch_kline_calibration_ohlcv(raw, window_bars=3342, calibration_bars=500, delta=PERTURB_DELTA)`，再對 `timestamp < output_start` 比對 close；校準域零列改變，而原控制仍要求 columns 或 d_star 失敗。

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#b0f5f222bd03

**類別**: code-contract

校準域採用的 adapter fetch 與公開域同為完整原始資料（adapter_registry:40-64），其後才按起始日裁切。這個控制所改的是公開域起點後的資料，且全鏈 warmup 已達數千根；它不再是舊合約中的 calibration 窗。`_calibration_series` spy 次數大於零只證校準值有被取用，不證校準值有被擾動。若因欄集合、公開值、codec 而失敗，不能據此聲稱 d-star 校準負控制已實現。

修法：新入口的負控制改為針對 full 側 `output_start` 之前真實列擾動，保留 trunc 側原始資料；具體時間選取由真實 timestamp 与校準封包的 first／last calibration timestamp 決定，收據記錄封包值／指紋確有變化與失敗 gate。不是改 `calibration_bars` 或容差。可行性證據：同 `evidence.py` rc=0，該起點前確有 500 真實列，舊 patch 在這些列完全未改；factory 的 `_load_calibration_klines`／既有 full-only fetch seam 可直接承接按時間的 patch。考慮深指標時可依封包時間擴大擾動區間，不能假設最後 500 原始根覆蓋所有欄的 500 有效校準值。校準／生成結果尚未實跑。

## CODEX-R1-P1-03

**斷言**: 新分母尺度控制把 `_build_truncation_pair` 放在 `raises(AssertionError)` 內，且 seam 次數僅要求大於零；生成準備／層覆蓋錯誤可以令控制通過，違反 Task 4.2「準備錯誤不算抓到」。

**碼證**: 新檔:132-141 將 builder 与 invariant 一起捕獲；helpers:666-704 的缺 L4／抽樣設計錯誤本身就是 AssertionError。複本 `evidence.py` rc=0：builder 先以真實 volume 呼叫被注入的尺度 seam，再拋 `AssertionError('mutation layer coverage failed (sampling design error): missing L4')`；`test_small_mutation_denominator_scale_full_column_fails` 正常返回，invariant 從未執行。探針不是生成型 node。
CODE-ANCHOR: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py:133
MUTATION: 複本把新模組 `_build_truncation_pair` 換成 `broken_preparation`（附錄原碼）：先呼叫 `numeric_guards.causal_denominator_scale(real_volume)`，再拋缺 L4 AssertionError；直接呼叫新控制函式會正常返回。

**來源摘要**: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py#a8a8e2e7cc1e4

**類別**: code-contract

同設定正常基線先跑也無法排除 mutant 自身造成準備／覆蓋失敗；欄層存在的靜態設定，更不等於 mutant run 的實際 survivor／sample 集合有效。舊 L3／winsor／L4 控制也有相同的寬捕獲，直接委派使新入口承接此風險；本 finding 以新增分母控制為最小可重現例。

修法：新入口先在捕獲區外完成 pair 生成與必要列／層／抽樣／seam 證據確認，捕獲區只包預期因果 values／NaN-mask／columns 等 gate 的失敗；錯誤文字與失敗欄／位置進收據，以排除 preparation/coverage guard。各控制有不同合法失敗種類，判別不必新增共用控制層，也不能放寬原 gate。可行性證據：同秒級反例把 builder 移出 `raises` 後，缺 L4 錯誤直接傳出（`FIX_FEASIBILITY` 輸出），不再假綠；`_build_column_frame_map`／`_build_sampled_columns`／`_assert_mutation_layer_coverage` 已存在且可在預期失敗前呼叫。舊委派 body 若不允許修改，新入口可只承接其 mutant seam 與 gate，將錯誤邊界調整明列於 Task 4.2，維持 gate 與容差不變。

## COMPOSER-R1-P1-01

**斷言**: SPEC v59 Task 4.2 要求兩新檔**全部 node 綠**且產出 `handoffs/run_receipts/<日期>-ffstat-small-mr.json`（逐 node 結果、mutant seam 證據）；目前僅有 baseline 探針 `20261002-ffstat-small-mr-probe-*.json`（**未跑 mutant**），**收案前置驗收條未滿足**。

**碼證**: `docs/FFSTAT_SPEC.md:196` 驗收條文；`ls handoffs/run_receipts/*ffstat-small-mr.json` → **無匹配**（僅 `*-probe-1h.json`／`*-probe-1h4h.json`）；`docs/manifests/FFSTAT.json` `run_receipts` 亦未登記 aggregate 收據；`pytest --collect-only` → 20 node 待實跑。CODE-ANCHOR: docs/FFSTAT_SPEC.md:196  
MUTATION: `test -f handoffs/run_receipts/20261002-ffstat-small-mr.json && jq -e '.nodes | length>=20' handoffs/run_receipts/20261002-ffstat-small-mr.json` → 現狀第一步即失敗（檔不存在）。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#01951d939d34;docs/manifests/FFSTAT.json#7a49a11402d1;handoffs/run_receipts/20261002-ffstat-small-mr-probe-1h.json#2266342a057a

正文：**修法（執行，非再加機制）**：獨占機器串行 `pytest tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py tests/feature_engineering/test_ff_multitf_truncation_small_mr.py -q`，並依 SPEC 寫入 aggregate JSON（每 node pass／xfail／耗時；mutant 附 seam 計數或 `lengths_seen`／`parallel_calls`）；登記 manifest `run_receipts`。**可行性**：探針已證 baseline 一對可完成且 RSS≤4.12GB；全套時間 SPEC 已估（~6.5h）。影響：在收據落地前，Task 4.2 不可視為 FF-STAT 收案前置已完成。

---

## COMPOSER-R1-P2-01

**斷言**: 多週期縮小版將 `ALIGN_COARSE_TFS` 從完整檔之 `["4h","12h"]` 縮為 `["4h"]`（`test_ff_multitf_truncation_small_mr.py:35-58`），`_assert_align_coarse_boundary_lookahead_detected` 與 `_assert_mutation_layer_coverage` 之粗週期 oracle **不再涵蓋 12h 欄**；12h 對齊類回歸僅能依 RM-FULLSCALE 完整檔或 §G⑦，縮小版鑑別力弱於完整 multitf MR（與 SPEC 誠實邊界一致，但委員須明示）。

**碼證**: `test_ff_multitf_truncation_mr.py:50` vs `test_ff_multitf_truncation_small_mr.py:35-58`；`ff_truncation_mr_helpers.py:1266-1291` oracle 依 `align_coarse_tfs` 篩欄；窗選取仍用 `_bar_window_dates_at_12h_boundary`（4h 邊界為 12h 邊子集，brief 前提 ③ 未查之殘餘）。

**類別**: code-contract

**來源摘要**: tests/feature_engineering/test_ff_multitf_truncation_small_mr.py#84f7d73fdabe;tests/feature_engineering/test_ff_multitf_truncation_mr.py#3f5403e6490c;docs/FFSTAT_SPEC.md#01951d939d34

正文：非要求恢復 12h（本機 kline 長度不足，SPEC 已記）；屬**已知縮減**，換機 fullscale ⑤ 仍必跑。不阻擋設計合併，但收斂時勿將縮小 multitf 等同完整 9 項之對齊覆蓋。

---

ASSUMPTIONS_VERIFIED: monkeypatch 綁定（probe）；20 collect-only；TODOFMT PASS；探針 JSON 與 brief 事實 1–4 一致。  
TESTS_RUN: `pytest test_ff_*_small_mr.py --collect-only -q` rc=0；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` rc=0；`/tmp/ffstat_b6_r1_probe.py` rc=0。  
FAILURES_SEEN: none（未跑 slow 生成）。  
SCOPE_CHANGES: none（唯讀）  
NUMERIC_OR_SCHEMA_IMPACT: none  
產出: `handoffs/20260926-ffstat-b6-review-r1-composer.md`

VERDICT: blocked  
BLOCKED-BY: COMPOSER-R1-P1-01  
CLOSED:

STATUS: DONE
## GROK-R1-P3-00

**斷言**: 本輪逐項核對後無 finding；Task 4.2 縮小版設計與兩新檔寫法對諮詢 r4 較嚴版與 brief 攻擊面均對得上，不阻擋主委獨占實跑。

**碼證**: `venv/bin/python -m pytest --collect-only -p no:cacheprovider tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py tests/feature_engineering/test_ff_multitf_truncation_small_mr.py -q` → 20 collected rc=0（單週期 13＋多週期 7）。`venv/bin/python /tmp/ffstat_b6_r1_work/probe_scope.py` rc=0：`_resolve_config` 後 L1 只 trend＋momentum、源 close＋volume、L3 窗 [5,13] 且 aggregators 10 全開、L2 ratio／cross／momentum／binary_signal 開、worldquant 關、L4 開、主 MR 縮尾／rank／zscore／gaussian 開；RSI／STOCHRSI／ADXR 在場；窗 3594／12786 與可行性收據相同；kline 20352 ≥ 兩窗；既有測試檔 AST 預設參數綁定 0、helpers 屬性載入 payload 0；`_build_truncation_pair` 之 `window_bars is None` 使用傳入 payload；`causal_near_zero_mask` 行 111 以 Name 取 `causal_denominator_scale`；兩支 small fracdiff xfail 為 strict 且 reason 與既有檔相同。核對依據另見上方必答 (1b)(2a)(3b) 對 consult r4 要點、assumed ①②③、「我沒查」1–5 之逐項結果。未跑生成型 node（brief 禁）。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#01951d939d34

正文：審查標的為 SPEC v59 Task 4.2、manifest 兩新檔與探針收據、helpers `_apply_small_mr_scope`／`_small_*_payload`、兩新測試檔、fact_keys RM-FULLSCALE ④⑤。威脅模型為意外漂移與未來洩漏之漏測。本輪未發現可證偽的漏測路徑；分母尺度 mutant 若在縮小窗內不跨門檻，測試會以 `pytest.raises` 未觸發而紅，屬 fail-closed，交主委實跑收據判定。

VERDICT: proceed
BLOCKED-BY:
CLOSED:
