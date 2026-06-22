# 20260622 dstar empirical — Composer（第三家獨立）

## 設計（刻意不同於 Codex）
- Symbols: ETH/SOL/LINK/ADA 1h（非 BTC）；窗=列索引 35%–65%（非日曆窗）
- 特徵：factory minimal L1（16 指標）+ 自衍 L2（7 欄，非 Codex 手工 20 欄）
- 路徑：`FeaturePreprocessor.transform()` winsor+fracdiff，rank/zscore off；腳本 `scripts/tmp/dstar_empirical_composer.py`；輸出 `/tmp/dstar_empirical_composer/summary.json`

## ① Option A（各 run 前 500 校準 d*）— 4 symbol 彙總
| 指標 | mean（跨 symbol） | per-symbol d*Δ mean |
|------|------------------|---------------------|
| \|Δd*\| | **0.206** | ETH 0.23 / SOL 0.16 / LINK **0.29** / ADA 0.15 |
| 特徵 Pearson | **0.524** | 0.45 / 0.75 / **0.25** / 0.65 |
| \|ΔIC\| | 0.011 | — |
| selection Jaccard \|IC\|≥0.01 | **0.43** | 0.78 / **0.0** / 0.20 / 0.75 |

極端例：LINK `L1_close_trend_SMA_55` d* 1.0 vs 0.055（Δ0.95），Pearson 0.16；ETH `L2_ema21_over_ema55` Δ0.55 Pearson -0.07。**非 BTC 特例**；SOL selection 完全分歧。

## ② 固定參考（全歷史校準 d*，full/window 共用）
| 指標 | 4-symbol mean |
|------|---------------|
| \|Δd*\| | **0.0**（構造上） |
| 特徵 Pearson | **0.9999** |
| \|ΔIC\| | **0.00087** |
| Jaccard \|IC\|≥0.01 | **1.0**（全 symbol） |

診斷：window Option-A d* vs 全歷史 d* mean\|Δ\|=0.17–0.51（LINK max 0.95）→ **不穩主因是前 500 列 regime-specific 校準**，非 fracdiff 本體。

## 判讀
- **非二階**：與 Claude+Codex 收斂；多 symbol 確認。
- **修法可行**：全歷史固定參考 d*（或跨 run 快取）可恢復 overlap 上特徵/IC/selection 穩定；代價=短窗 run 用遠古 regime 校準（因果/語意 tradeoff，類 Option C）。
- Option A 現狀=run 內自洽但 cross-window **非** byte/IC parity。

## Hermetic
- `data_cache` 544 files SHA256 diff：**empty**；list_hash=`913581bd2b18ef007b49c3f5d010209c7a0741daa2686ab1e91c29cf36f04b84`
