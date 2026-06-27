# FF 深稽 — Claude 獨立腿(P0-FF-1 / P0-FF-2 / P0-FF-4)

> 依 [[feedback-claude-own-version]]:Claude 先實讀碼自產獨立版,再交 GPT-5.5(Codex)+Composer 2.5 雙家族 adversarial。本文**未經委員審**,委員須挑戰前提。
> Scoping 已 reconcile 雙家戳記 APPROVED(`20260627-FF-AUDIT-RECONCILE.md`)。本腿是**深稽實作**階段的 Claude 起手測試設計 + 讀碼揪出的可疑點。

## §A 已驗證事實(實際 grep/讀碼,非推論)

**A1. TA-Lib 系 atomic 測試 = 純 smoke**
- `tests/test_atomic_indicators.py`(74 行,5 個 test):唯一斷言形如 `assert "close_trend_EMA_21" in result.columns`、`assert any("ATR_14" in col ...)`。**零數值 oracle**——RSI/ATR/EMA/OBV/CDLHAMMER 回傳全 NaN 或全錯值仍綠燈。
- `tests/test_talib_wrapper.py`(75 行):驗命名/結構,非值。
- 涵蓋模組:trend/momentum/volatility/volume/pattern/cycle/statistics(皆走 `TALibWrapper.compute`)。

**A2. 手刻模組測試 = property/邊界,非 reference 差分**
- `tests/momentum/test_entropy_indicators.py`(15 特徵)、`test_tail_risk_indicators.py`(26)、`test_microstructure_indicators.py`(25):斷言為 count/prefix/「資料不足→NaN」/「constant→0」/「單邊上界」/「MDD 單調」。
- 這些是**有用的 sanity 不變量**,但**沒有任何一條驗「值 == scipy/手算 canonical」**。例:CVaR_1pct 的實際數值是否等於真正的 1% CVaR、permutation entropy 值是否等於 scipy/手算——未驗。公式打錯成「看似合理的數」會全綠。

**A3. 衍生(手刻、無 TA-Lib 背書)指標幾乎無專測**
- `volume_indicators.py` 內 `_compute_vwap`/`_compute_volume_ma_ratio`/`_compute_force_index`/`_compute_klinger`/`_compute_eom`:`test_atomic_indicators.py` 對 volume 只有 `assert any("OBV" in col ...)`——這 5 個手刻全無值驗證。

**A4. `requires_kline` 機制不存在**
- `grep -rn requires_kline tests/ momentum/` = **0 命中**。HANDOFF/reconcile 的 P0-FF-4 `requires_kline` 是**待新建**,非現有。
- 現況:`test_ff_causal_golden.py`、`test_failopen_matrix.py`、`test_mtf_align_golden.py`、`test_atomic_indicators.py` 等 10+ 處在缺 kline 時 `pytest.skip("missing ...")`。**缺資料 = 靜默跳過 = CI 綠燈但零正確性覆蓋**。correctness job 不該 skip,該 FAIL。

**A5. 全鏈因果現有測試 = 窄**
- `tests/feature_engineering/preprocessing/test_ff_causal_golden.py::test_rolling_quantile_oracle_on_real_baseline`:`perturbed.iloc[-2:,:] *= -1000 → result.iloc[:-2]` float32 相等——但作用在**單一 numeric frame 的 rolling-quantile 算子**,非全鏈。
- `test_real_generate_e2e_causal_preprocessing_no_persist` 有呼叫 `factory.generate_features(...)`,但(reconcile A5)測「縮短 end」非 **bar 級尾端截斷/擾動**跨 L1–L6.5+CGSA+multi-TF。
- 鏈入口確認:`momentum/FeatureEngineering/feature_factory.py:237 generate_features()`。

## §B 讀碼揪出的可疑點(深稽不只缺測,可能真 bug — 待委員驗)

> 這些是 Claude 讀碼的**假設**,標「待驗」——須真 run 確認,不得當已證(接驗證保真度鐵律)。

**B1.（待驗,中)`TALibWrapper._resolve_input_type` 預設陷阱**(`talib_wrapper.py:354-360`):未列入 `_INPUT_TYPE_MAP` 且非 `CDL*` 的指標一律回 `"single"`,吃 `data_source`(預設 close)。若某需 hlc/hlcv 的指標漏登錄→**靜默餵 close 單欄**而非報錯。需測:對 registry 每個指標斷言 input_type 與 TA-Lib `abstract.Function(name).input_names` 一致(differential 防錯配)。

**B2.（待驗,中)`statistics` 的 BETA/CORREL 被歸 `close_volume`**(`talib_wrapper.py:206`):BETA/CORREL 在 TA-Lib 取 (real0, real1),此處餵 (close, volume)。語義上 BETA(close, volume) 可疑(通常 BETA(high, low) 或兩資產)。需委員判定是否 intended;若否=錯特徵。

**B3.（待驗,高)手刻 Klinger 簡化**(`volume_indicators.py:231-243`):用 `vf = volume*(2*close-high-low)/(high-low)` 後 `EMA_fast-EMA_slow`。canonical Klinger 的 VF 含 trend(±1)累積與 daily measurement 符號邏輯;此版省略。需 manual reference 差分或明示為「簡化變體」標註於 metadata。同理 ForceIndex(此為 period-1 raw,canonical 常 EMA13 平滑)、EOM(缺 scale 常數)——非 crash,是「叫這名字但非標準公式」風險。

**B4.（待驗,中)`compute_batch` 對 multi-input 指標忽略 `data_sources`**(`talib_wrapper.py:320-327`):非 single 一律 `"close"` source label——正確(hlc 等不該迭代 source),但需確認 metadata 與實算的 source_label 一致(防 A2 類「兩端對不上」幽靈欄)。

## §C 測試設計(Claude 起手版;附章程 §G/Oracle 分級;待雙家族審測試本身)

> 鐵律:聲稱驗正確性的測試須證「改壞會 FAIL」(mutation/可證偽);用真實 kline `data_cache/feature_klines/kline_cache.h5`,禁合成 fixture 代替([[feedback-test-design-rigor-reviewed]]、三方數據簽核鐵律)。

**P0-FF-1 atomic differential**(測有限「算子」非無限「特徵」)
- C1-1（Oracle=GOLDEN/EXACT)TA-Lib 系:對每類抽樣指標(RSI/ATR/EMA/MACD/OBV/AD/STOCH/BBANDS…)在真實 kline 上 `TALibWrapper.compute(...)` vs 直呼 `talib.FUNC(正確 source 欄, **params)`,`np.testing.assert_allclose`(NaN 對齊)。**目的=驗 wrapper 的 source 欄/param 傳遞/輸出對位,非驗 talib 本身**。
- C1-2（Oracle=EXACT,防 B1)對 `INDICATOR_REGISTRY` 每個指標:斷言 `_resolve_input_type(name)` 推得的欄位集合 ⊆ TA-Lib `abstract.Function(name).input_names`(differential 防錯配)。
- C1-3（Oracle=GOLDEN,手刻 A3/B3)VWAP/VolumeMA_Ratio/ForceIndex/Klinger/EOM + entropy/tail_risk/microstructure 抽樣:對「手算 canonical 公式」差分;無單一 canonical 者(Klinger)→鎖 golden byte + metadata 明示「簡化變體」。
- C1-mutation:改 wrapper source 欄(close→open)、改一個 param、把 EOM 的 `*` 改 `/`→上述測試**必紅**(章程 §B 硬門檻)。

**P0-FF-2 全鏈 bar 級未來截斷 MR**(一個不變量蓋全部,測法不爆炸)
- C2-1（Oracle=EXACT 不變量)真實 kline 跑 `generate_features()` 得 `full`;取同資料前 N-k bars 跑得 `trunc`;斷言 `full` 的前 (N-k-warmup) 列之 **feature matrix 值 + NaN mask + columns 順序** 與 `trunc` 對應列 byte/float32 一致。覆蓋 L1–L6.5 + CGSA + multi-TF(粗→細)。
- C2-2(擾動版)把尾端 k 個 bar 的 OHLCV 改 ±1e6→截斷點前列不變(防任何層偷看未來)。
- C2-mutation:人工在某層引入 `shift(-1)`/`center=True` rolling/全量 fit→C2-1 必紅。**這條紅不起來=測試無效**(章程 §B8 閉合再驗證由原提出方重跑)。

**P0-FF-4 缺資料 FAIL 非 skip + DATA_MANIFEST**
- C4-1 建 `requires_kline` 標記(pytest marker 或 fixture):correctness 類測試缺指定 symbol/TF kline 時 **FAIL**(明確訊息),非 `pytest.skip`。逃生口:純環境無資料的本地開發走 `-m "not requires_kline"` 顯式排除,而非靜默綠。
- C4-2 `tests/fixtures/DATA_MANIFEST.json`:列 correctness 測試依賴的 (symbol, TF, 最少列數, sha256/指紋);啟動時校驗,golden 漂移→FAIL(非靜默)。
- C4-3 mutation:刪/改 manifest 一筆指紋→C4-2 必紅。

## §D 邊界 / 不做
- **不全重測**:多TF對齊(V-6)、L6.5 因果(V-5/causal_winsor)、L3 numba_rolling differential 已 P0,不重做。
- 本批 = P0-FF-1/2/4;P0-FF-3(MultiTF 高頻截斷+production 全欄)、P1-FF-5/6/7 隨後另批。
- 衍生指標若委員判定為「intended 簡化變體」,則 C1-3 退為 golden-lock + metadata 標註,不視為 bug。

## §E 待委員(雙家族)挑戰的前提
1. C2-1 的「warmup 對齊」如何不引入假綠?(截斷後 warmup 邊界列本就該 NaN,需確認比對區間排除暖機尾巴而非掩蓋差異)
2. B2(BETA/CORREL close_volume)是 bug 還是 intended?
3. C1-3 手刻指標「canonical」基準由誰定義才可證偽(避免拿實作自身當 oracle)?
4. requires_kline 機制要不要連帶處理 CI(無 data_cache 的 runner)——FAIL 會不會誤傷正當的無資料環境?逃生口設計是否夠?
