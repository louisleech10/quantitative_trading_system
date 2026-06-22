# FF L0–L7+L6.5 狀態參數審計 — Composer 獨立版
**日期**: 2026-06-22 | **方法**: grep+逐檔讀碼(未照抄 Claude) | **判準**: A擬合/搜 B累積 C peer D因果滾動

## ① gaussian_normalize（高優先，已驗）
| 結論 | **D 安全 rolling，非 fitted** |
|---|---|
| 機制 | `_gaussian_2d`(:3434) `causal=True`→`_rolling_rank_numba`(:3448)→`ndtri`；**無** sklearn `QuantileTransformer`/`.fit()` |
| 釘死 | `causal_preprocessing` 強制 True(:149-157)；非因果分支 `selected.rank(pct=True)`(:3455) 生產不可達 |
| vs Claude | Claude 標「疑似 fitted」→**誤**；實為 rolling rank→Gaussian |

## A 擬合/搜尋（須綁 run/model 留存）
| 項 | 層 | 證據(檔:行) | 現況留存 |
|---|---|---|---|
| fracdiff **d\*** | L6.5 | `_find_min_d`+`_calibration_series`(:3699,:180); ADF 二分搜; `DStarCache` `d_star_*.json`(:331 `_d_star_cache.py`) | ⚠️ config-hash+前500校準，**未綁 run** |
| ADF **integer diff** | L6.5 | `_apply_adf_differencing`(:3301); `chosen_diff`(:3337-3359) 前500 ADF | ❌ **無持久化**；preset `professional_full` 預設開(:1094 `config_manager.py`) |
| non_stationary 分類 | L6.5 | `_get_non_stationary_columns`(:3582); ADF 前500→欄位集合 | 僅 `NonStationaryCache` 記憶體(:14 `_non_stationary_cache.py`) |
| labels winsorized | labels | `ret.quantile` 全樣本(:79 `label_generator.py`) | ❌ 全樣本分位=**A+洩漏** |

## B 路徑累積（須一致起點/burn-in）
| 項 | 層 | 證據 | 備註 |
|---|---|---|---|
| OBV/AD/ADOSC | L1 | talib `volume_indicators`(:40); `warmup_table.yaml`(:367-381) | 純累加/AD→EMA |
| EMA/MACD/Wilder/Hilbert/KAMA | L1 | `warmup_table` `ema_seeded`/`wilder`/`hilbert`(:106-159) | 自 bar0 遞推；warmup 收斂非絕對值可比 |
| Klinger | L1 | `talib.EMA(vf)`(:237-238) | EMA 路徑依賴 |
| **VWAP** | L1 | `rolling(20).sum`(:205 `volume_indicators.py`) | **D rolling**；yaml 寫 cumulative 與實作不符 |
| entropy R/S cumsum | L1 | `np.cumsum(demeaned,axis=1)`(:248 `entropy_indicators.py`) | **窗內 chunk**，非序列 from-start |

## C peer 依賴 | D 安全（摘要）
| 層 | C | D |
|---|---|---|
| L0 | — | 資料載入/PIT 對齊 |
| L1 | — | 多數 rolling/點wise；VPIN/EOM rolling(:256-284 microstructure) |
| L2-L4 | — | 衍生算子/lag/shift |
| L5 | `reference_symbol` 價比+rolling β(:16-29 `relative_strength.py`) | β/殘差=rolling60 |
| L6 | — | consensus/interaction/time 純函數；`rank(axis=1)` 為**同 bar 跨指標**(:76) |
| L6.5 | — | winsor rolling quantile(:2336); zscore(:2376); rank(:3377); gaussian rolling |
| L7 | — | 驗證門檻；`fill_nan mean` 可選(:407) 非預設管線 |
| MTF/native-tf | — | `tf_aligner` PIT(:30); `calibration_bars` TF 縮放(:157 `_native_tf_helpers.py`) |

## 逐層結論
| 層 | 安全(D) | 須留存/規則 |
|---|---|---|
| L0-L4 | 主路徑 | B: L1 talib 遞推族 |
| L5 | rolling 特徵 | C: reference 即時可得 |
| L6-L7 | 全層 | — |
| L6.5 | winsor/rank/zscore/gaussian | **A: d\***(+ADF diff 若開) |
| labels | simple/log/excess/risk_adj | winsorized→A |

## 互補漏項
| Claude 漏/誤 | Composer 漏/補 |
|---|---|
| gaussian 誤標 fitted | VWAP 實作=rolling 非 yaml cumulative |
| EMA/MACD/Wilder 未列 B | `professional_full` 開 ADF diff |
| labels 全樣本 winsor | dead code: `causal=False` 全樣本 winsor(`polars_adapter.py`:426) |
| — | ForceIndex 無 EMA(:225)=D；consensus `rank(axis=1)` 安全 |

HANDOFF_NOT_UPDATED: read-only 審計任務
