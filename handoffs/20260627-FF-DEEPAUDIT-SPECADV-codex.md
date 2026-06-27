# FF-DEEPAUDIT SPEC/TODO adversarial review — Codex

結論: **須修後再派實作**。SPEC/TODO 已忠實搬進 reconcile 主軸,但仍有會讓冷啟動執行端改錯檔、漏下游同步、或 golden 假綠的 blocking gap。

## BLOCK

1. **[BLOCKING][High] BUG-1/BUG-2 實作檔案路徑錯誤,TODO 又聲稱冷啟動端不需回讀其他檔**
   - 證據: TODO line 4「冷啟動執行端逐 Task 寫碼,不需回讀其他檔」; SPEC line 24/65/72 與 TODO line 56/62 都寫 `talib_wrapper.py` / `volume_indicators.py`。
   - 真實程式路徑: `momentum/FeatureEngineering/atomic/talib_wrapper.py` line 187-207 定義 `_INPUT_TYPE_MAP`; `momentum/FeatureEngineering/atomic/volume_indicators.py` 才是手刻 volume 指標。
   - 會怎麼失敗: 執行端按 TODO 找頂層 `talib_wrapper.py` 會找不到或自行搜尋後改對,但這違反「不需回讀其他檔」的冷啟動合約;更糟是只改測試或新增錯位置 wrapper,造成假修。
   - 修法: SPEC/TODO 所有 task 的允許改檔改成完整路徑: `momentum/FeatureEngineering/atomic/talib_wrapper.py`, `momentum/FeatureEngineering/atomic/volume_indicators.py`, 以及需要同步的具體下游檔案。

2. **[BLOCKING][High] BUG-1「列所有舊欄名消費者」仍是空話,且已能 grep 到至少一個真實同步點未列**
   - 證據: SPEC line 65 只寫「下游同步點(feature_storage metadata、IC/ML 消費者)」; TODO line 56 同樣只寫「feature_storage metadata、IC/ML」,沒有檔案/函式/grep query。
   - 真實程式路徑反例: `momentum/FeatureEngineering/utils/adf_safe_skip.py` line 55 whitelist `_CORREL_`, line 16 明確把 `BETA` 排除; `tests/feature_engineering/test_adf_safe_skip.py` line 48/164 硬編舊欄名 `close-volume_12h_statistics_CORREL_5` / `...BETA_5`。`api/services/feature_factory_service.py` 也有 BETA/CORREL 顯示映射。
   - 會怎麼失敗: 改成 canonical `hl_statistics_BETA_*` 並新增 `BetaCloseVolume` 後,ADF safe-skip 與相關測試可能仍按舊 close-volume 命名判斷;IC/ML 可能沒有硬編舊名,但 SPEC 沒要求證明。這會造成下游語義漂移或測試假綠。
   - 修法: Task 1.3 必須先產 `rg` 清單並逐項分類: source generation、metadata/catalog、storage manifests/goldens、ADF/L6.5 preprocessing、IC feature selection、ML `feature_columns`、frontend display/docs/tests。TODO 中列具體檔案與處置,至少包含 `adf_safe_skip.py` 與其測試。

3. **[BLOCKING][High] §G golden 不足以保證「未受影響欄 byte 不變」,受影響範圍也未定義**
   - 證據: SPEC line 28 baseline 只有 mean/std/nan_ratio +「抽樣 value hash」+ NaN mask hash; line 30 說「未受影響欄仍須 byte 不變」但沒有定義 affected columns。
   - 可證偽反例: 一個非 BETA/CORREL 欄在 1000 列中只漂一列,若未抽中 value hash,mean/std 在容差內且 NaN mask 不變,§G 仍可能 PASS。另一個反例: BUG-1 改欄名後,L2/L3/L4 衍生欄名含 `statistics_BETA/CORREL` 或 `BetaCloseVolume` 的整個派生族是否「受影響」未定義,執行端可把大範圍 drift 都歸到 exception。
   - 會怎麼失敗: 正確性任務會在「改特徵集」例外下掩蓋旁路污染,尤其 production preset 全欄有大量派生欄。
   - 修法: golden 必須有全量 per-column value bytes/hash + dtype + index hash + NaN mask hash。Task 1.3 先輸出 affected-column predicate: canonical BETA/CORREL 新欄、舊 close-volume rename 欄、以及由這些欄派生的 L2/L3/L4/L6.5 欄;其餘欄 full value hash 必須 exact equal,不是抽樣/均值。

4. **[BLOCKING][Medium-High] C2 全鏈 MR 的 metadata 驗收自相矛盾,會讓實作端二選一硬改或忽略**
   - 證據: SPEC line 81 / TODO line 70 要在共同 timestamp 交集比 `full.iloc[warmup:-k]` vs `trunc.iloc[warmup:-k]` 的 values/NaN/index/metadata `row_count/data_range`。
   - 真實路徑: `feature_factory.py::generate_features` line 237 入口帶 `start_date/end_date`;截斷尾端 k bars 後,整體 result metadata 的 `row_count` / `data_range` 合理上應該不同,不是與 full 相等。
   - 會怎麼失敗: 若比整體 metadata,正確截斷也 FAIL;若實作端為了過測不比 metadata,又弱化 reconcile 的 metadata gate。`iloc[warmup:-k]` 在「共同 timestamp 交集」後也容易多扣一次尾端 k,造成假紅或漏比最後共同列。
   - 修法: 明確拆成兩個斷言: (a) 對 aligned common index,比較 `common_index[warmup:]` 到 trunc end 之前的 values/NaN/index exact;不要在共同交集後再 `:-k`。 (b) metadata 比較只檢查應不變欄位,例如 feature schema/config_hash/source symbol/timeframe;row_count/data_range 則 assert 符合截斷後預期,不是 full==trunc。

## RISK / MAJOR

1. **[MAJOR][High] §A 把 kline 形狀與「10 symbol × 3 TF」列為已驗證事實,但 SPEC 沒有實際命令輸出**
   - 證據: SPEC line 13 說「已驗證事實(附驗證方式 grep/實跑 pytest)」; line 15 只說三方鐵律指定,沒有 h5 keys/row_count/sha256 實測輸出。
   - 修法: 補 `python`/h5 inspection 輸出摘要到 SPEC: path exists, symbols, TFs, row_count min/max, columns, sha256/fingerprint。否則降為「依治理要求」而不是 fact-verified。

2. **[MAJOR][Medium] Task 0.1 的「現用 pytest.skip 的 correctness 測試逐一評估」不可執行**
   - 證據: TODO line 30 沒有列清單;實際 `rg "pytest.skip|missing kline|kline_cache"` 命中多個 feature_engineering、momentum/Analysis、api 測試,有些是 correctness,有些是環境/外部依賴。
   - 會怎麼失敗: 執行端可能只改新測試用 marker,保留舊 correctness skip,仍靜默綠。
   - 修法: TODO 加一張表: 必改 marker 的測試檔/函式、保留 skip 的理由、驗證命令。至少納入 `tests/test_atomic_indicators.py`, `tests/test_talib_wrapper.py`, `tests/feature_engineering/test_failopen_correctness.py`, `test_mtf_align_golden.py`, L6.5 real-data tests 的分類。

3. **[MAJOR][Medium] mutation probe patch 點仍不夠具體**
   - 證據: SPEC line 97 / TODO line 11 要每 mutant 列具體 patch 點,但 Task 2.1 只說「某層注入 `shift(-1)`/`center=True` rolling/全量 fit」;Task 1.2 只說「改 wrapper source(close→open)/改一 param」。
   - 修法: 每個 task 加 exact file + symbol/function + one-line patch example。例: `momentum/FeatureEngineering/atomic/talib_wrapper.py::_prepare_inputs` 將 `data["high"]` 改 `data["open"]`; `operators/numba_rolling.py` 或 L3 aggregation 具體 rolling call 改 `center=True`; L6.5 fit 路徑具體改用 full-window fit。

4. **[MAJOR][Medium] TODO 的 Logging 規則會誘導違反解耦**
   - 證據: TODO line 13 寫 `from api.core.logging import get_logger`,但全域規則 line 7 同時要求 `momentum/` 不 import `api/`。
   - 會怎麼失敗: 若執行端在 `momentum/FeatureEngineering/atomic/*` 新增 logging 並照 TODO import api logger,直接違反 7 大解耦規則。
   - 修法: TODO 改成: momentum 內使用 `from momentum.core.logging import get_logger`;api 內才用 `api.core.logging`。

## OK

- `estimate_max_warmup_bars` 真實簽名與 SPEC/TODO 方向相容: `momentum/FeatureEngineering/warmup_window.py` line 313-317 為 `(config, primary_tf, training_tfs=None)`。
- reconcile 的核心 BLOCK 大多已進 SPEC/TODO: warmup config-driven、columns gate、雙 oracle、mutation TDD-first、§B8、三方數據簽核都有文字落點。
- TODO 9/9 task trace 基本覆蓋 SPEC task,但 §G baseline 的落點需要按上方 BLOCK #3 補成可執行 task。

## TODO 具體補強

- T1.3 前新增「consumer audit」子步驟: `rg` 舊欄名/indicator pattern,輸出檔案清單,逐項 migration/alias/test 決策。
- T1.3/T1.4 改完整路徑,並列 metadata 寫入點;不要只寫 `talib_wrapper.py`/`volume_indicators.py`。
- §G/TODO 補 `tests/_golden/ff_deepaudit/` 的全量 hash schema 與 affected-column predicate。
- T2.1 改 C2 MR 對齊算法,將 values gate 與 metadata gate 分離。
- T0.1 補 skip-to-marker 清單;未改者需列「非 correctness」理由。
- 全 TODO 將 momentum logging 指令改成 `momentum.core.logging`。

STATUS: DONE
