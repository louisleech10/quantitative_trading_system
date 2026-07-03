# 委員會 round 3 — conv 修後 slow 驗證輪事實 + 待裁決（Claude 編）

> 2026-07-03 | receipt：`20260703T094044Z-fracdiff-maxlag-convfix-slow.log`（4 passed, 1 xfailed, 2 failed, 2:43:58）
> 前情：MRFAIL-RECONCILE（雙戳記）裁決案 1-4 已執行：conv 修復（`_hurst_prior._convolve_1d` + 孿生 `feature_preprocessor._frac_diff_convolve` 皆改 direct）、B1 xfail、3 mutation 窗長修。

## 實測事實

1. ✅ 截斷 MR：**XFAIL 如預期**（B1 reason 生效）。3 個 max_lag mutation 探針 PASSED。full_fit 控制 PASSED。
2. ❌ 尾擾 MR：敗在 fracdiff 值 gate，`close_1h_trend_BBANDS-Lower_233_fracdiff`，**兩邊 dtype 不同**（x=float32 精度值 -18.84375…；y 明載 `dtype=float16` -18.84…），Max abs diff **0.0078125 = 2^-7 = float16 量化步長**（receipt 內 assert dump）。
   → **B1 根因家族第二次現形且升級為已確認**：per-column parquet codec（float16/32）依全窗值域選型；尾擾改變值域 → codec 翻面 → 前綴儲存精度不同 → atol=1e-8 gate 必炸。同機制回頭解釋 B1 idx508（float16 max=65504，近零分母大值 float16 溢出→inf→sanitize NaN；float32 邊存活）。
3. ❌ calibration_perturb 控制：`DID NOT RAISE`。**差分證據**：
   - 上輪 054245Z（resolver 已修=兩窗 d\* 同 50、FFT 未修）：該控制 PASSED（有 raise）。
   - 本輪（僅多 conv 修復）：DID NOT RAISE。
   → 它上輪能響的路徑=FFT 值抹散（d\* 已同不可能是 d\* gate）；更早（修 max_lag 前）能響=長度耦合。**該控制從未經由設計意圖路徑（校準擾動→d\* 不對稱）觸發**。
   設計檢視：`_patch_kline_calibration_ohlcv`（helpers:1393-1408）把擾動施加在「相對各自窗的 calibration 段」且 patch_fetch 對 full/trunc **兩跑都生效**——若擾動在兩跑座標對齊，則無不對稱可偵測，控制先天無效。
4. conv 修復本身行為正確：direct conv 下 d\* gate 綠、擾動不再假性外洩（這正是控制假響消失的原因）。

## 待裁決

- **D1 尾擾 MR 處置**：codec 翻面是 pre-existing storage 語意（與 B1 同案）。選項：
  (a) xfail(strict) 同 B1 家族 reason、storage epic 一併修（簡單誠實；代價=尾擾值級護網暫停）；
  (b) 測試改比 pre-persistence 層值（改測點，保住護網但動 helper——與「不改 helper」邊界衝突，需明確授權）；
  (c) 其他。
- **D2 calibration_perturb 控制重設計**：改為**只擾動一跑**（如僅 full 的 calibration 段）製造真 d\* 不對稱 → 經由 d\* gate 觸發（設計意圖路徑）。歸類：測試 bug 修（同 Q4 性質）。
- **D3 簽核範圍聲明**：值守恆簽核文件加載「codec 值域依賴（已確認）影響尾擾值級比對與 B1;storage epic 立案」。
- **D4**：storage epic 立案文字升級為「已確認根因：per-column float16/32 codec 依全窗值域選型 → 長度/尾值洩入儲存精度」（不再是假說）。

## Claude 建議票
D1=(a)（xfail 誠實掛、storage epic 修 codec 決定論後轉綠；d\* gate+3 mutation+full_fit 控制仍護住 max_lag 面）；D2=重設計必做（本 epic 內，Codex 實作）；D3/D4=照載。
