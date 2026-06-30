# FF-B2 FracDiff/Gaussian 截斷 MR 委員意見 — Codex

## 實測範圍
- 讀取真 kline: `data_cache/feature_klines/kline_cache.h5`, `BTCUSDT/1h`, 20352 rows。
- full-chain 嘗試: `preset=minimal`, 500/490 bars, fracdiff+gaussian enabled；CGSA no-persist 回傳 `features_df` 空矩陣，不能作為 fracdiff MR 結論。
- 可用實測: 真 kline OHLCV 直接餵 `FeaturePreprocessor` L6.5，`FFACT_FRACDIFF_APPLY_TO_LAYERS=ALL`, `calibration_bars=500`, `max_lag=50`, `cache_d_star=False`，測 500→490、600→590、尾端 10 bars +1e6 擾動。

## 實測結果
- Gaussian: 5/5 欄在 500→490、600→590、尾端擾動前綴皆 byte-equal；程式路徑為 causal rolling rank (`causal_preprocessing` 強制 True)。
- FracDiff 500→490: 5 欄中 4 欄 byte mismatch；`high` d-star 0.2344→0.25, `close` 0.2656→0.2812，最大差約 1965.99。原因是 trunc 只有 490 bars，校準樣本從 500 變 490。
- FracDiff 500 bars 尾端擾動: 5/5 d-star 全變 (`open` 0.2812→0.5312, `volume` 0→0.6562 等)，前綴最大差約 21200；這會抓到「校準使用被擾動尾端」。
- FracDiff 600→590: d-star 全相同（皆用 first 500 bars），但 byte-level 仍有 4/5 欄 mismatch，最大絕對差約 5.64e-11；after row 500 仍有約 3.82e-11。這是浮點卷積/FFT 重算差，不是 d-star 變動。
- FracDiff 600 bars 尾端擾動: d-star 全相同，前綴只剩約 1.16e-10 級差異；Gaussian 仍 byte-equal。

## 設計評估
- 不建議把 fracdiff 直接放進主 byte-equal MR：500→490 會因校準長度假紅；600→590 即使 d-star 相同也會因 1e-10 級浮點重算假紅。
- Gaussian 可納入主 byte-equal MR。它目前是 trailing/causal 且實測 byte-equal。
- 主 MR 應維持「確定性 byte-equal 集」：全開能產出的 deterministic features + gaussian；fracdiff 從主 byte-equal gate 排除，避免把 d-star/FFT 數值性質當 look-ahead。
- Fracdiff 另設專門 MR：
  1. `window >= calibration_bars + trunc_k + post_warmup_rows`，例如 600→590；斷言 full/trunc d-star 完全相同。
  2. 對 fracdiff values 使用嚴格容差，例如 `atol <= 1e-8, rtol=0` 或先按實際 dtype 設門檻；同時 NaN mask 必須 exact。
  3. tail perturb 只擾動 calibration window 之後的尾端；斷言 d-star 不變、前綴容差內不變。
  4. negative control 另做「擾動 first calibration 內」或 monkeypatch d-star/full-fit，必須 fail，證明測試可抓校準 look-ahead。
- Pin d-star 可作第三個輔助 gate：直接固定每欄 d-star 後驗 fracdiff convolution 前綴容差，但不應取代 d-star 校準 MR，否則抓不到校準偷看未來。
- 兩套 config 是必要的：主 byte-equal config 含 gaussian、不含 fracdiff；fracdiff config 單獨跑 d-star/values/negative-control MR。不是「一套有一套沒有」二選一，而是兩層職責不同。

## 對 Claude 初步看法
- 同意「byte-equal 確定性集 + fracdiff 另驗」。
- 修正點：Gaussian 不必另用容差，實測可進 byte-equal 主 MR；fracdiff 另驗必須把 `WINDOW_BARS` 提高到大於 `calibration_bars`，否則 500→490 沒有公平判準。

## 驗證命令摘要
- `source venv/bin/activate && python - <<'PY' ...`：真 kline L6.5 fracdiff/gaussian 500→490、600→590、tail perturb 實測，pass，輸出如上。
- `sed -n`/`rg` 讀取 `test_ff_fullchain_truncation_mr.py`, `feature_preprocessor.py`, `_d_star_cache.py`，確認 d-star 校準與 cache key 行為。

STATUS: DONE
