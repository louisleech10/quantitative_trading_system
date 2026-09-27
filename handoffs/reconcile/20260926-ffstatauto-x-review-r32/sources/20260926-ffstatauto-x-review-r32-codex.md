# FF-STAT SPEC v47 審查 r32：codex

審查標的依 brief 限定於 v47、r31 兩採納項、未提交的穩定遮罩／採用腳本／倍數表／L1 輸出點與量測收據；未審 b4 其餘實作。所有執行測試均在 `/tmp/ffstat-r32-VTjDzP` 複本；未跑全設定 FF run 或新參數量測。

## CODEX-R32-P1-01

**斷言**: `adopt()` 將 `entry.cases` 的所有非週期變體寫入 `variants`，未要求該變體存在已收斂量測；因此一個有嘗試但未收斂、或沒有收據列的非週期變體會通過 v47 的 `check_variant()`，再落入比例公式，未實現「未量測變體 fail-closed」。

**碼證**: 在隔離複本以現有 catalog 與真實量測收據，僅追加未新增收斂列的 `MA(timeperiod=233, matype=4)` case，再執行 `adopt()`：輸出 `MA_VARIANTS ['matype=0', 'matype=4']`、`UNMEASURED_MATYPE4_K 233`。同一複本將現行表的 MA matype=4 直接送入 `instance_k()` 則會擋下，表示缺口位於採用端的 variant 登記。
CODE-ANCHOR: scripts/verify_l1_warmup_requirements.py:526
MUTATION: 在隔離複本對 MA `entry.cases` 追加 `{"timeperiod":233,"matype":4}` 而不追加 converged row，執行 `adopt()` 後呼叫 `k_for_params()`；目前仍得到 `K=233`，未得到 `UnmeasuredVariantError`。

**類別**: code-contract

**來源摘要**: scripts/verify_l1_warmup_requirements.py#f7a6134dabb3; momentum/FeatureEngineering/preprocessing/stable_mask.py#52a48a9fecdc; momentum/FeatureEngineering/atomic/warmup_table.yaml#58a8fa973e58; handoffs/run_receipts/20260928-ffstat-warmup-measure.json#32bdf0d6d0e

正文：v47 的 `variants` 語意是已量測變體，但實作以 `entry.cases` 而非 `converged` rows 建表。若該變體的所有量測都未收斂，`k_by_params` 沒有該鍵；目前 `check_variant()` 卻先放行，`k_for_params()` 再以 `recommended_factor` 估算。對會改變 warmup 的 MA matype、MAMA fastlimit 等參數，這會把沒有穩定收斂證據的組合當成可採用比例值，威脅模型下可提前解除 L1 遮罩。

修法：`variants` 應只由至少一筆 `converged` row 的非週期鍵建立；對存在於 catalog 但沒有已收斂 row 的非週期變體，輸出前仍須走 `UnmeasuredVariantError`，不得以比例公式補值。可行性證據：現行 `test_l1_mask_unmeasured_nonperiod_variant_fails_closed` 已證明只要變體不在表中，既有 `check_variant()` 路徑即可擋下；將採用端的集合來源改為收斂 rows 即可重用該路徑，無需放寬 gate 或改變數值門檻。

## CODEX-R32-P2-02

**斷言**: `l1_output_points._k_from_table()` 對 `period_keys` 為空的條目直接回傳 `entry["k"]`，未執行 v47 的 `check_variant()`；因此 preflight 的 `max_l1_k()` 對未量測的無週期參數組合與實際 L1 mask 路徑不一致。

**碼證**: 在隔離複本呼叫 `_k_from_table("MAMA", {"fastlimit":0.7,"slowlimit":0.05})` 得 `MAMA_VARIANT_K 79`；同一參數送入 `mask_output()` 得 `UnmeasuredVariantError`，且訊息列出已量測唯一變體 `fastlimit=0.5,slowlimit=0.05`。`_collect_l1_warmup_bars()` 每次透過 `max_l1_k()` 使用此 preflight 路徑。

**類別**: code-contract

**來源摘要**: momentum/FeatureEngineering/atomic/l1_output_points.py#b8f1d8bd74f4; momentum/FeatureEngineering/preprocessing/stable_mask.py#52a48a9fecdc; momentum/FeatureEngineering/warmup_window.py#c7939a1893ef

正文：這不會讓目前預設 MAMA 變體誤放行；預設真實 BTC 12h L1 probe 之 `MASK_CALLS=1611` 與 `L1_COLUMNS=1611` 全部通過。但使用者把 MAMA fastlimit 改成未量測值時，preflight 先以 79 計算深度，實際輸出階段才拋契約錯誤，造成同一契約在每次執行的前置檢查與輸出檢查不一致。

修法：無週期鍵分支在回傳 `k` 前呼叫同一個 `check_variant()`，或讓 `_k_from_table()` 委派一個不帶輸出的共同 K 解析函式。預設 probe 與目前 `mask_output()` 的差異輸出已提供可行性邊界；修正後應以同一 MAMA 變體負例使兩條路徑同樣 fail-closed。

## CODEX-R32-P2-03

**斷言**: `canonical_params()` 對 list／sequence 參數只做 `str(list)`，而 `k_for_params()` 隨後對 period key 呼叫 `float()`；TA-Lib MAVP 明確接受 sequence 的 `_prepare_inputs()` 路徑因此會在 L1 stable-mask 解析時得到 raw `TypeError`，不是可診斷的契約錯誤，也不能使用測量鍵或安全的最大週期公式。

**碼證**: 隔離複本執行 `MAVP`、`params={"periods":[5,8]}`：`canonical_params` 產生 `matype=0,maxperiod=30,minperiod=2,periods=[5, 8]`，`instance_k()` 輸出 `MAVP_LIST_ERROR TypeError float() argument must be a string or a number, not 'list'`。TA-Lib wrapper 的 `_prepare_inputs()` 同時在 `momentum/FeatureEngineering/atomic/talib_wrapper.py:417-420` 專門處理 list／tuple／ndarray。

**類別**: code-contract

**來源摘要**: momentum/FeatureEngineering/preprocessing/stable_mask.py#52a48a9fecdc; momentum/FeatureEngineering/atomic/talib_wrapper.py#de80a8ede445

正文：目前預設 `_resolve_params()` 將 MAVP 展開成 scalar `periods`，所以預設 BTC 12h L1 probe 未命中此缺口；這是 brief 要求核對的 list 正規化邊界。對直接使用 sequence 的合法 MAVP 輸入，現行 v47 鍵既不會命中 `k_by_params`，又不能進入比例公式，最後以未分類 TypeError 中止。修法需定義 sequence 的穩定正規表示，並依實際 sequence 的最大 period 求 K；若契約不允許 sequence，則應在入口明確拋 `StableMaskError`，不可讓 `float(list)` 成為外露錯誤。

**必答成對**

(1a) 本家 r31 兩條均閉合。`CODEX-R31-P1-01`：DX／ADAUSDT／1d／144 之表值已為已收斂量測 K=1138；`CODEX-R31-P1-02`：MA matype=4 不再共用 matype=0，現行表只列 matype=0 且未量測 matype=4 會 fail-closed。

(1b) 在 `/tmp/ffstat-r32-VTjDzP` 執行 `jq -c '.rows[] | select(.indicator=="DX" and .symbol=="ADAUSDT" and .timeframe=="1d" and .params.timeperiod==144)' handoffs/run_receipts/20260928-ffstat-warmup-measure.json` → `k=1138, converged=true, reliable=false`；再執行 `venv/bin/python -c '... sm.instance_k(...) ...'` → `DX_INSTANCE_K 1138 TABLE_K 1138`、MA matype=4 → `UnmeasuredVariantError`。

(2a) 有新缺陷：P1-01 為採用端把未收斂非週期變體加入 `variants`；P2-02 為無週期鍵 preflight 漏驗 variant；P2-03 為 MAVP sequence 正規化／K 計算不完整。當前預設設定沒有因此誤擋：真實 BTC 12h 預設 L1 probe 為 1611 欄、1611 次 `instance_k`，rc=0。

(2b) 可重現反例分別為：追加未收斂 MA matype=4 case 後 `adopt()` 仍允許 K=233；MAMA fastlimit=0.7 之 `_k_from_table()` 回 79 而 `mask_output()` 拋 `UnmeasuredVariantError`；MAVP `periods=[5,8]` 拋 raw `TypeError`。

(3a) assumed 就目前收據／表與已量測參數範圍成立；不能把此結果外推為未量測新參數變體的安全保證。P1-01 是 adoption fail-closed 缺口，不否證目前 20,535 筆收據中已收斂列的逐筆下界結果。

(3b) `venv/bin/pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_warmup_table.py -q --tb=short` → `16 passed in 3.51s`；其中 `test_table_k_ge_every_converged_measurement` 與其 mutation 均通過。量測收據摘要為 `rows=20535, not_converged=0, not_reliable=37`；DX 反例列仍為 K=1138。未另跑新參數量測，故 coverage risk 保留。

(4a) ① 目前預設設定無命中：ConfigManager 合併後真實 BTC 12h L1 probe 全部 mask call 通過；MA 實際 engine resolve 只產生 timeperiod，matype=0 由表 defaults 疊加命中。② 預設 custom／advanced 參數無命中；TR_CVAR alpha=0.01／0.05 已登記，改 alpha=0.10 會 fail-closed，window 仍屬 period key。③ 有命中：MAVP sequence 未被 canonicalized 成可查表鍵，且後續 `float(list)` 失敗。

(4b) ① `venv/bin/python -c '... ConfigManager().get_merged_config(); ... _layer1_atomic_indicators(...) ...'` → `L1_COLUMNS 1611 MASK_CALLS 1611`，並列出 `MAMA {'fastlimit': 0.5, 'slowlimit': 0.05}`、MA 呼叫僅含 `timeperiod`；`venv/bin/pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py -q --tb=short -k every_l1_output_column_passes_output_point_contract` → `1 passed in 0.70s`（均在 tmp 複本）。② `TR_CVAR alpha=0.10, window=21` → `UnmeasuredVariantError`，default alpha=0.05、window=1000 → K=1000。③ `MAVP periods=[5,8]` → `CANONICAL_LIST_KEY ... periods=[5, 8]`、`MAVP_LIST_ERROR TypeError ... list`。

(5a) 不予放行，`VERDICT: blocked`。

(5b) 擋項只有 `CODEX-R32-P1-01`；P2-02、P2-03 為非阻擋改善項。

coverage_risk：本輪使用既有 v47 後全量收據，未跑新參數倍數量測；未跑全設定 FF run。實跑子集時長：warmup table 3.51s、預設 BTC 12h L1 output-point probe 0.70s；所有測試與 probe 均在 `/tmp/ffstat-r32-VTjDzP`。工作樹未改碼、未改 SPEC／manifest、未改 git。

VERDICT: blocked
BLOCKED-BY: CODEX-R32-P1-01
CLOSED: CODEX-R31-P1-01,CODEX-R31-P1-02
