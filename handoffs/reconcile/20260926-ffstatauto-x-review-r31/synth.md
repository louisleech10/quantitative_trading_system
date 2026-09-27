# Reconcile — 20260926-ffstatauto-x-review-r31

**來源** 20260926-ffstatauto-x-review-r31-codex.md, 20260926-ffstatauto-x-review-r31-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/manifests/FFSTAT.json

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 不可信週期補值非安全上界：v46的unreliable-perio | P1 | CODEX-R31-P1-01 | 採納（SPEC v47：k_by_params、係數與無參數 K 皆取已收斂量測〔含前史 < 2K 之不可信者〕之最大，某週期無已收斂量測才以係數補；DX／ADA／1d／144 採用值 1,035→1,138；新增 test_table_k_ge_every_converged_measurement 收據對表逐筆不變量與 mutant test_mutation_adopted_k_below_measurement_is_caught） | code-contract |
| 鍵漏非週期參數：`k_by_params`的鍵只含`pe | P1 | CODEX-R31-P1-02 | 採納（SPEC v47：鍵改全參數正規鍵〔param_defaults 疊上呼叫參數〕；條目登記已量測之 variants，未量測之非週期參數組合〔MA matype=4 等〕輸出前 UnmeasuredVariantError；新增 test_l1_mask_unmeasured_nonperiod_variant_fails_closed） | code-contract |
| 零 finding：本輪逐項核對v46（R10實測根數優先） | P3 | COMPOSER-R31-P3-00 | 採納（composer 判 proceed） | other |

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R31-P1-01

**斷言**: v46 的 unreliable-period fallback 不是安全上界；現有真實 receipt 已觀測到 DX/ADAUSDT/1d/timeperiod=144 收斂 K=1138，但採用表只給 K=1035，故 adoption 可低估實際收斂需求。

**碼證**: receipt、table 與隔離突變測試證據如下。
CODE-ANCHOR: scripts/verify_l1_warmup_requirements.py:494
MUTATION: 在隔離副本把 DX 的 timeperiod=144 表值由 1035 改成 1，再執行 16 個 warmup/stable-mask 選定測試。
`jq` receipt 摘要：`DX/ADAUSDT/1d/144: k=1138, err=0.0010523247, converged=true, reliable=false, gt_history=2086, ratio=7.9027778`；現行表 `DX.k_by_params[timeperiod=144]=1035`，而 1d fallback 是 `ceil(144*6.1429)=885`，故候選最大值仍為 1035。實跑 `--only DX --timeframes 1d --symbols ADAUSDT --eval-window 1000 --no-write` rc=0，產出同一筆 `k=1138`。隔離副本突變後仍為 `16 passed`（14 warmup-table + 2 個 k_by_params/stable-mask 相關選定測試）。

**類別**: code-contract

**來源摘要**: scripts/verify_l1_warmup_requirements.py#9f4ada58a4a6; momentum/FeatureEngineering/atomic/warmup_table.yaml#d6c40571570d; handoffs/run_receipts/20260928-ffstat-warmup-measure.json#6f57491ccb49; tests/feature_engineering/test_ffstat_warmup_table.py#b1812a5a6b29

現行 `_k_by_params()` 對沒有可信量測的 timeframe 使用 `ceil(period * by_tf[tf])`，而 `by_tf` 又只由 reliable rows 建立；它沒有在 unreliable row 的收斂 K 高於候選值時拒絕 adoption。這不是把一筆 unreliable 值冒充可信值：問題是 v46 明確選擇用該 fallback 取代它，卻沒有驗證 fallback 不低於已觀測的 converged K。

修法：對每個 `(indicator, params_key, timeframe)`，若 converged row 的 `k` 高於 fallback/adopted candidate，應令 adoption fail-closed 並要求增加真實前史重跑，或以明確標記的 observed upper floor 提升候選值；不得靜默寫入較小的 `k_by_params`。新增 receipt-to-table invariant，至少拒絕 `adopted_k < any_converged_observed_k`。可行性證據是本輪現有 `DX/144` 實測已直接觸發此條件；把隔離副本的表值突變為 1 後現有測試仍全綠，表示只需補這個可執行 invariant 即能把目前的漏檢轉成紅燈，不需改動資料或放寬 gate。

## CODEX-R31-P1-02

**斷言**: `k_by_params` 的鍵只含 `period_keys`，漏掉會改變收斂性的非 period 參數；scan config 已宣告 MA 的 matype 0–4，但 `MA(timeperiod=233, matype=4)` 仍命中 `timeperiod=233 -> K=233`，真實 1d 資料的最小通過 K 為 258。

**碼證**: config、table、wrapper 與真實 1d 收斂探針證據如下。
CODE-ANCHOR: momentum/FeatureEngineering/preprocessing/stable_mask.py:133
MUTATION: 將 MA 參數由 `{"timeperiod":233,"matype":0}` 改為 `{"timeperiod":233,"matype":4}`，再執行同一個 `instance_k`/真實 1d 收斂探針。
`config/scan_config.yaml:86-89` 宣告 `MA` 的 `matype: [0, 1, 2, 3, 4]`；但 `warmup_table.yaml` 的 MA `period_keys` 只有 `timeperiod`。實跑同一張表的 `instance_k` 給 `233`；BTCUSDT/1d 真實長歷史探針輸出 `error_at_233=0.007208`、`first_K=258`（門檻 0.005）。`TALibWrapper.compute("MA", ..., {"timeperiod":233,"matype":4})` 亦成功，回傳 `close_trend_MA_4-233`，不是不可執行的參數。

**類別**: code-contract

**來源摘要**: momentum/FeatureEngineering/preprocessing/stable_mask.py#65f1546d0967; momentum/FeatureEngineering/atomic/warmup_table.yaml#d6c40571570d; config/scan_config.yaml#0dc95e4f0a10; momentum/FeatureEngineering/atomic/talib_wrapper.py#de80a8ede445; tests/feature_engineering/test_ffstat_stable_start.py#ca8298e12fcb

`params_key()` 只對 `period_keys` 排序及序列化；因此 matype=0、4、6 等會共用同一個 key。只把未知組合導向目前的比例公式也不足以修正 MA：MA 的 `recommended_factor=1.0`，公式仍會給 233，低於 matype=4 的 258。修法應把所有會影響 warmup 的參數納入穩定鍵與量測表（至少對已宣告的 MA matype 維度逐組量測），或在參數未被量測時 fail-closed，而不是把不同遞迴/平滑算法視為同一個 period-only variant。可行性證據是 generic key builder 已能序列化任意傳入 key，且本輪已用同一資料與同一門檻分別量得 matype=4 的 258；增加鍵維度後可直接區分此 case，無需新增 hardcoded period 或資料。

本輪必答核對：

1a. v46 可以低估 K。receipt 中 DX/ADAUSDT/1d/144 為 converged `K=1138`，表為 `1035`；另 MA/233/matype=4 為表 `233`、實測 `258`。  
1b. 具體 counterexample 為上述兩組 indicator/params/period；DX 例被現行可靠性條件標為 unreliable，故它同時證明 fallback 的安全假設未被資料支持，而不把該筆宣稱成 reliable ground truth。

2a. 「unreliable period 使用 period coefficient × period 不會低估」不能作為已驗證 invariant。`eval-window=1000` 的 DX row 仍收斂但 `K=1138 > 1035`；`eval-window=800` 的同一 ADAUSDT/1d probe 變成 reliable `K=856`，顯示可採用值受評估窗與前史條件影響，不能從目前係數宣稱安全上界。  
2b. 實跑命令：`venv/bin/python scripts/verify_l1_warmup_requirements.py --only DX --timeframes 1d --symbols ADAUSDT --eval-window 1000 --no-write --receipt measure-dx.json` → rc=0，DX/144 `k=1138, converged=true, reliable=false`；另 `--eval-window 800 --receipt measure-dx-800.json` → rc=0，DX/144 `k=856, converged=true, reliable=true`。

3a. unchecked ① 無 production-catalog 命中：`build_catalog()` 掃描輸出 `noninteger_period_values []`、`period_key_missing []`；② 命中，MA 的 declared matype 維度未進 key，且實測低估；③ 本輪未發現新的 composite floor 漏項。現有 custom catalog 的 KELTNER/ FORCE_INDEX/ KLINGER 分別有 EMA/ATR 或 EMA floor，其他列出的 custom/advanced entry 是 rolling/window 或由 upstream K 傳遞。  
3b. 證據：`scripts/verify_l1_warmup_requirements.py:64-68` 的 `PERIOD_KEY_NAMES` 不含 matype；`adopt():526-554` 只宣告 KELTNER、FORCE_INDEX、KLINGER 的 component floors；同檔 `build_catalog():358-438` 的 custom/advanced 清單未見另一個遞迴 component。這是 code/catalog 逐項核對結果，不是宣稱已重跑 full FF。

4a. 實跑 `venv/bin/pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py -k 'l1_mask or mutation_k_by_params' -q --tb=short` → `7 passed, 53 deselected`；`venv/bin/pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_warmup_table.py -q --tb=short` → `14 passed`。既有 `test_mutation_k_by_params_ignored_is_caught` 能抓到整體移除 `k_by_params`。  
4b. 實際隔離突變是把 `DX/timeperiod=144` 表值 `1035→1`，再執行兩檔合計 16 個選定測試，仍為 `16 passed`；這證明目前測試沒有把 receipt 的 adopted K 與 converged measurement 做逐組下界比對。MA 的 matype=4 探針也已實跑並顯示 `instance_k=233`、`first_K=258`。

5a. 不予 proceed；兩個 P1 都是會使 L1 mask 早於穩定點放行的可重現契約缺口。  
5b. 阻擋項僅列 `CODEX-R31-P1-01`、`CODEX-R31-P1-02`。

VERDICT: blocked
BLOCKED-BY: CODEX-R31-P1-01,CODEX-R31-P1-02
CLOSED: CODEX-R29-P1-01
## COMPOSER-R31-P3-00

**斷言**: 本輪逐項核對 v46（R10 實測根數優先）之 SPEC／manifest／測試與量測收據後，未發現需阻擋 v46 放行之新 P0／P1；威脅模型＝意外漂移時，忽略 `k_by_params` 之 mutant 與 KAMA_233 實測優先斷言可證偽。

**碼證**: `git show 8e5e55fc --oneline` → v46 §C `k_by_params` 定義、Task 2.3①／2.4 表欄、R10 裁定列；`venv/bin/python /tmp/claude-501/r31_analyze2.py` → `ROW_COUNT=20535 UNRELIABLE=37 UNRELIABLE_1D_233=36`、`MAX_K=2049 ADXR timeperiod=233`、`KAMA233 measured=1400 formula=4660`；`venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_l1_mask_k_by_params_preferred_over_factor tests/feature_engineering/test_ffstat_stable_start.py::test_mutation_k_by_params_ignored_is_caught tests/feature_engineering/test_ffstat_warmup_table.py -q` → 16 passed in 4.74s、`PYTEST_RC=0`；`momentum/FeatureEngineering/preprocessing/stable_mask.py:141-151` 與 `tests/feature_engineering/test_ffstat_stable_start.py:57-64` 同序（先 `k_by_params` 後比例公式）；`scripts/verify_l1_warmup_requirements.py:471-497` 與 SPEC 不可信週期補值敘事一致。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#f4f843c365d4; tests/feature_engineering/test_ffstat_stable_start.py#ca8298e12fcb; handoffs/run_receipts/20260928-ffstat-warmup-measure.json#6f57491ccb49; momentum/FeatureEngineering/preprocessing/stable_mask.py#65f1546d0967; handoffs/20260927-ffstat-b4-redesign-rulings.md#392c39f6bdf5; docs/manifests/FFSTAT.json#17022e5e9c56

正文：v46 解決比例公式對 KAMA／MACDFIX 類指標之**高估**（遮罩過長）；採用值由跨週期 max 與查無走公式之雙軌組成。brief 假設「1d 週期 233 不可信時係數補值不低估」本輪**未否證亦未證實**（未重跑 `--only` 量測；收據顯示 36 筆 unreliable 為 1d＋period 233 型態）。brief「我沒查」① T3 之 `vfactor` 不在 `period_keys`，預設設定僅整數 `timeperiod` 入表鍵；② 表外參數如 STOCH fastk=377 測試已覆蓋走公式；③ 元件下限僅三組 composite，其餘未逐指標反例實跑——屬覆蓋風險非已證低估。

---

