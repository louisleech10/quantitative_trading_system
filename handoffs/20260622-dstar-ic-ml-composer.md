# 20260622 d* calibration vs B6 — Composer read-only quant view

## Position
**同意 Option A**（接受 date-windowed ≠ full-range 的 fracdiff byte 差異；d* 仍用該 run 序列前 `calibration_bars`≈500）。核心理由是 **run 內因果自洽 + cache 隔離**，而非「下游會洗掉差異」。

## Verified（程式）
- `_calibration_series` → `iloc[:bars]`，`bars=max(adf sample_size, calibration_bars, 500)`；`_find_min_d` 僅用此窗決策，`_frac_diff_ffd` 對**全長**因果套用。
- IC-First：**pre_ic** = winsor+fracdiff+ADF（**無** rank/zscore）→ L7 raw → IC gate；**post_ic** 才 rank/zscore（僅入選特徵）。故 d* 差異**直接進 IC**，不經 post_ic 緩衝。
- `config_hash` 含 `_start_date/_end_date`；`DStarCache` 檔名不含 hash，但 payload `time_range/row_count` + per-column `strong_value_fp` 防跨切片污染。

## Claude 論證稽核
| # | 判定 | 補充 |
|---|------|------|
| ① hash 隔離 | ✅ | 保護 feature artifact；d* 檔靠 value_fp/time_range |
| ② 500 穩健 | △ | 常見夠用，非保證；ADF 邊界+persistent 特徵可翻 d* |
| ③ IC 秩穩健 | △ | Spearman 對單調縮放穩，fracdiff **非**單調；改 d→改記憶/NaN 起點→秩可變 |
| ④ ML rank/zscore 洗掉 | ❌ **對 IC 不成立** | 只對 post_ic/ML 特徵；IC 讀 pre_ic raw |
| ⑤ run 內自洽 | ✅ | Option A 主正當性；犧牲 cross-window byte parity |

## 實質影響（IC / ML）
- **常態**：d* 差 0.02 步長內，多數特徵 IC 微動；入選邊界特徵可能翻轉（`|IC|≈threshold`）。
- **放大**：regime shift、切片起點=crash/上市、row<500、I(0)/I(1) 邊界、MA/trend/volume 類；B6 warmup 後前 500 實為**窗口感附近** bars，與全史前 500 **語意不同**（未必更差，但必不 byte 一致）。
- **ML**：post_ic rank/zscore 降 scale 敏感度，**不**消除 temporal filter/缺失 pattern 差；feature importance 二階影響。

## Options A/B/C/D
- **A**（現狀）：最低 scope、因果、cache 自洽；B6 fracdiff 列**明確例外**。
- **B**（載入 dataset start 校準）：parity 最好；成本高、違短窗資源預期、遠古 regime 未必更準。
- **C**（重用全範圍 d*）：可恢復部分 parity；需跨 hash 讀取語義，窗口感失真風險。
- **D**（固定 anchor/rolling）：最可重現；scope 大、窗選擇=新假設；且 walk-forward d* **已三方否決**。

## 前 500 是否次優？
全序列校準 = 非因果（含未來）；最近 500 = 歷史回測每點漂移≈walk-forward（已否決）；隨機 = 不可重現。**固定前 N 是因果預設的合理折衷**，非理論最優。

## PIT / look-ahead
`iloc[:500]` 只用已載入序列**最早** bars；B6 warmup 區為 start 之前歷史 → **無未來洩漏**。風險是**跨 run 可比性/parity**，非 leakage。勿拿 full-range 與 date-slice 的 IC 直接當同一實驗。

## Risks（接受 A 須明示）
1. B6 文件標 fracdiff d* 為 byte-parity 例外；2. 邊界 IC 入選可能分歧；3. 建議真實 kline 抽樣量測 d* Δ / IC Δ / selected overlap（後續，非 B6 阻塞）。
