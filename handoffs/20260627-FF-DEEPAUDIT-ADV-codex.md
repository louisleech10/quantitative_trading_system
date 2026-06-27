# FF-DEEPAUDIT Claude Leg Adversarial Review — codex

結論: **須修後再審**。Claude 腿方向正確,但 B2/B3 已可由最小真 run 升級為 BLOCK;C2 warmup/MR 定義與 mutation gate 仍會假綠。

## BLOCK 清單

1. **B2 是真 bug: BETA/CORREL source 與 TA-Lib abstract 不一致**
   - 反例/路徑: `momentum/FeatureEngineering/atomic/talib_wrapper.py` 將 `BETA`,`CORREL` 放在 `_INPUT_TYPE_MAP["close_volume"]`;實測 `abstract.Function("BETA").input_names == {'price0':'high','price1':'low'}`、`CORREL` 同樣是 high/low。`TALibWrapper.compute("BETA", df, {"timeperiod":5})` 與 `talib.BETA(close, volume)` maxdiff=0,但與 `talib.BETA(high, low)` maxdiff=7.331893;`CORREL` 對 high/low maxdiff=1.948082。
   - 建議修法: 先決策語義。若要 TA-Lib canonical,把 BETA/CORREL 改為 `hl` 並改欄名/metadata/golden;若 intended 是 close-volume,不得叫 TA-Lib canonical BETA/CORREL,需 rename/metadata 明示並用獨立 oracle 固定。

2. **B3 是真公式/命名風險: ForceIndex/EOM/Klinger 不是常見 canonical,但 metadata 未標變體**
   - 反例/路徑: `volume_indicators.py` 直接輸出 raw ForceIndex、未平滑;實測 raw vs EMA13 Force Index maxdiff=996.965。EOM 少常見 `*100_000_000` scale,canonical/project median ratio=100000000。Klinger 省略 trend/sign/cumulative measurement VF,與常見 KVO reference maxdiff=35533.337。
   - 建議修法: 對每個手刻指標建立外部 canonical oracle。若保留簡化版,欄名/metadata 必須改成 simplified/raw/scaled-units 明示,並 golden-lock 目前值;不得讓下游以為是標準 Klinger/EOM/ForceIndex。

3. **C2-1 全鏈截斷 MR 目前描述會被 warmup/public trim 掩蓋**
   - 反例/路徑: `warmup_window.py` 有 B6 warmup-then-trim,`feature_factory.py::_trim_for_public_output` 會把公開輸出裁到 `[output_start,end]`。若 C2 只比 `full 前 (N-k-warmup)` vs `trunc`,或只比 public `features_df`,可能把最容易暴露 look-ahead 的截斷邊界/暖機尾列整段排除。
   - 建議修法: 固定同一個 `output_start` 與同一個 `ingest_start`,在共同 timestamp intersection 上比對;只排除每欄由已知 lookback 定義的 leading warmup,不得用「全局 max_warmup + k」大刀裁掉截斷邊界。必須同時比 `values`,`NaN mask`,`columns`,`index timestamps`,`metadata row_count/data_range`。

4. **C1/C2/C4 mutation gate 未定義成可執行 gate,仍可能是假紅線**
   - 反例/路徑: Claude 腿寫「改 source/param/shift(-1)/刪 manifest 必紅」,但沒有指定 mutation 如何注入、跑哪個 test、怎麼 fail closed。若只人工描述,實作端可寫出測試但不跑 mutation,仍通過。
   - 建議修法: TODO/SPEC 必列每個 mutation 的具體 patch 點與驗收命令,例如 monkeypatch `_INPUT_TYPE_MAP["hl"].remove("BETA")` 或臨時 patch source map後跑 `pytest ...::test_talib_registry_matches_abstract`;C2 monkeypatch 某層 `shift(-1)` 後跑全鏈 MR;C4 改 manifest sha 後跑 manifest test。驗收報告需附 fail 摘要。

## RISK 清單

1. **A1 大方向 OK,但「零數值 oracle」表述需收斂**
   - grep/讀碼: `tests/test_atomic_indicators.py`、`tests/test_talib_wrapper.py` 確實只驗欄名/shape/subset,無 TA-Lib source/param differential。另有 `tests/test_feature_factory_batch2b.py` 對 CGSA persistence 用 `assert_allclose`,但那是保存/載入既有 frame,不是 atomic formula oracle。
   - 判定: RISK。不要寫成全 repo 完全無數值斷言;應寫成「atomic TA-Lib wrapper/source/param correctness 無 P0 differential」。

2. **B1 原假設部分誤讀,但 fail-open 風險仍存在**
   - 反例/路徑: 暫時從 `_INPUT_TYPE_MAP["hlcv"]` 移除 `MFI` 後,`_resolve_input_type("MFI") == "single"`;呼叫 `talib.MFI(close)` 會 TypeError,不是靜默算 close。可是各 engine 的 `compute_all()` catch `Exception` 後 warning 並繼續,所以 production 風險是「漏欄/少特徵 fail-open」而非「錯值靜默 close」。
   - 建議修法: registry-vs-abstract 必須 exact ordered signature;engine correctness mode 對 registered indicator 計算失敗不得只 warning。

3. **C1-2 的 registry check 必須包含 price_transform/adapter-only 的明確政策**
   - 反例/路徑: 實測 registry mismatch 7 個: `AVGPRICE` single vs ohlc、`MEDPRICE` single vs hl、`TYPPRICE/WCLPRICE` single vs hlc、`BETA/CORREL` close_volume vs hl、`MAVP` special periods。price_transform 被標 `computed_in_adapter=True`,但 grep 未看到實際 price_transform adapter output tests。
   - 建議修法: C1-2 不要簡單 subset;要 exact ordered signature + allowlist with rationale。adapter-only 指標需有自己的 adapter oracle 或從 registry 排除並證明不會宣稱可算。

4. **C1-3 canonical oracle 來源不足**
   - 反例/路徑: entropy/tail_risk/microstructure 現測試是 feature count、prefix、constant/zero-volume 邊界;沒有 scipy/manual rolling reference。手刻 volume 若用自身公式當 oracle,改錯但同步 oracle 仍綠。
   - 建議修法: 每類至少一個小型手算 table + 一個外部文獻/庫公式 reference;無 canonical 者只能 golden-lock + metadata 明示變體,不可稱 canonical correctness。

5. **C4 requires_kline 需要分離 correctness job 與 local dev**
   - 反例/路徑: grep 到 `pytest.skip("missing ...")` 覆蓋 atomic、TA-Lib wrapper、E2E、failopen、B6、IC registry 等多處;目前無 `requires_kline`/`DATA_MANIFEST`。
   - 建議修法: correctness marker 缺資料 FAIL;普通本地可顯式 `-m "not requires_kline"`。CI 若無 data_cache,該 job 應顯示 blocked/fail,不能被當綠。

## OK 清單

1. **A2 OK**: `tests/momentum/test_entropy_indicators.py`,`test_tail_risk_indicators.py`,`test_microstructure_indicators.py` 是 sanity/property/邊界,未見 canonical differential。
2. **A3 OK**: VWAP/VolumeMA_Ratio/ForceIndex/Klinger/EOM 由 `VolumeIndicatorEngine.compute_all()` 無條件 append,但 `test_atomic_indicators.py::test_volume_indicator_engine` 只查 OBV 欄存在。
3. **A4 OK**: `rg requires_kline tests momentum` 無現有機制;多處缺資料 skip 屬真風險。
4. **A5 OK with nuance**: 現有 `test_ff_causal_golden.py` 有 L6.5 rolling quantile oracle與一個 generate smoke,但沒有全鏈 bar 級截斷/尾端擾動 MR。B6 warmup tests 驗 trim/row_count/position-independent subset,不是 P0-FF-2 全鏈 oracle。
5. **B4 OK**: `compute_batch` 對非 single 使用 `"close"` 呼叫只是進入 `_prepare_inputs`;實際 source_label 由 input_type 覆蓋為 `hlc/hl/hlcv/close_volume`,metadata keys 與 computed columns 對齊。這不是 BLOCK。
6. **§D 不全重測 OK**: L3 numba rolling、L6.5 causal winsor、既有 MTF as-of golden 可不全重做;但 P0-FF-3 production multi-TF 高頻截斷不能在總計畫中消失,只能明確排到下一批。

## 對 §C 測試設計的具體補強

1. C1-1: 抽樣 differential 不只 RSI/ATR/EMA,必含 `BETA`,`CORREL`,`MFI`,`STOCH`,`BOP`,`OBV`,`AD`,`ADOSC`,`AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE` 的 adapter policy。比對 TA-Lib direct call 的 input tuple、params、output names、NaN mask、index。
2. C1-2: `abstract.Function(name).input_names` 作為 registry exact oracle;special cases only allowlisted with tests (`MAVP periods`,adapter-only price transforms)。任何 registered indicator 計算失敗在 correctness mode 必 FAIL。
3. C1-3: 手刻指標拆三類: canonical exact、simplified variant golden、project-specific invariant。每欄 metadata 必標 oracle class;沒有 external/manual oracle 不得宣稱公式正確。
4. C2-1/C2-2: 使用同一真 kline、同一 config、同一 output window;比較共同 timestamps,不要只用 row position。列出被排除 warmup rows 的規則與數量,並斷言排除數不超過每欄 declared lookback。
5. C2 mutation: 至少三個 executable mutants: L1 source swap、L2/L3 `shift(-1)`、L6.5 full-sample fit/center rolling。每個 mutant 都要在 review report 中附 fail 摘要。
6. C4 mutation: manifest 缺 symbol/TF、sha mismatch、row_count below minimum 三種都要 FAIL;同時測 local opt-out marker 不會被 correctness CI 使用。

## §E 四個前提回答

1. **warmup 對齊**: 不能用全局 warmup 砍掉比較尾段;要按 timestamp intersection + per-column lookback 排除 leading warmup,並保留截斷邊界前最後可比列。
2. **BETA/CORREL**: 以 TA-Lib abstract 判定,目前是 bug 或至少 mislabeled feature;不是無害 intended,除非 rename 並文件化 close-volume 語義。
3. **手刻 canonical**: 由外部公式/手算表/第三方庫定義;實作自身只能當 golden-lock,不能當 correctness oracle。
4. **requires_kline/CI**: correctness job 應 fail closed;無資料環境只能顯式不跑該 marker,不能 skip 後報綠。

## 驗證摘要

- 讀: `HANDOFF.md`,`CLAUDE.md`,`handoffs/20260627-FF-DEEPAUDIT-ADV-PROMPT.md`,`handoffs/20260627-FF-DEEPAUDIT-CLAUDE-LEG.md`,`handoffs/20260627-FF-AUDIT-RECONCILE.md`。
- grep/讀碼: `tests/`, `momentum/FeatureEngineering/atomic/*`, `feature_factory.py`, `warmup_window.py`。
- 最小真 run: `source venv/bin/activate && python - <<'PY' ...` 比對 TA-Lib abstract registry、BETA/CORREL direct call、B1 漏登錄 MFI、ForceIndex/EOM/Klinger canonical variants。
