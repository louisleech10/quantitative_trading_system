# IC-API-TEST-MODERNIZATION Phase1 資料正確性簽核 — 主委獨立版
Task-id: ic-api-testmodern | Chair: Claude(Opus 4.8) | Date: 2026-07-12

## 簽核標的
tests/fixtures/ic_api_real_kline.py 的 build_real_kline_frames 產出的 IC 輸入資料(features/labels)是否 PIT 無洩漏、可用於 IC。觸鐵律 a → 三方獨立簽。

## 主委讀碼實測(receipt)
- **Label PIT 正確**:`labels = close.shift(-HORIZON)/close - 1.0`(=close[t+5]/close[t]-1,simple 前瞻報酬);
  `labels.iloc[-5:]=NaN`(最新 5 根無前瞻值);RETURN_TYPE="simple" 與 config_override.labels.return_type="simple" 同源。
- **Feature PIT 正確**:log_return_1/3=shift(+k)、rvol_20/zscore_20/close_sma_ratio_20=rolling 右端 t、hl_range/oc_return 同期;**無 shift(-\*)**;warmup MAX_FEATURE_LOOKBACK=21 → 512 全 finite(主委探診修正 off-by-2)。
- **Tier-2 值 oracle**:validate_alignment 傳 close+return_kind="simple"+sample_size=16 → 前瞻值逐點對照。
- **可證偽(主委實跑)**:test_ic_api_real_kline_pit.py 2 passed——feature shift(-1)→"feature PIT oracle mismatch" FAIL;backward label→"label mismatch" FAIL。
- **無合成**:builder grep 零 rng.normal/np.arange;真 ETHUSDT/12h 衍生。**生產零 diff**。29 API passed。

## 主委簽核
**DATA-CORRECT: PASS**(features ≤t 無 future peek、labels 正確前瞻 simple+尾 NaN、與 config 同源、可證偽守衛有效、真 kline 衍生無合成)。

## 交三方(grok+composer 各獨立簽,codex=實作者迴避)(VERIFY-EXEMPT:doc-example:icatm-dc-chair;三方簽核見 DATACORRECT-{grok,composer}.md 各自 receipt)
請各自**獨立**驗(可自跑):
1. label 是否真前瞻 simple(非 backward、非 log)、尾 5 NaN;
2. features 是否全 ≤t 無 future peek(逐欄查公式);
3. Tier-2 值 oracle 是否真跑(close 有傳)、mutation 是否真可證偽(自跑 feature shift(-1)/backward label 證 FAIL);
4. 有無殘留合成潛入 IC 輸入面;R2-7 stub 是否只在 API 輸出面且 clone/restore。
輸出 handoffs/IC-API-TESTMODERN-DATACORRECT-{grok,composer}.md,一行 DATA-CORRECT: PASS 或 FAIL+反例。
**任一方有疑→不通過**(三方鐵律)。並附實作 review:dedup 忠實/生產零 diff/29 綠。
