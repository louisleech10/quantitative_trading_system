# 特徵管線「上線須留存參數」盤點 — Claude 自產一版
> 目的:盤點 L0-L7 + L6.5 每個計算,分類為「上線可因果重算(安全)」vs「含擬合/狀態參數(須留存,否則 train/serve 偏移)」。
> 觸發:d* 釐清後,使用者要求系統性盤點 fracdiff/ADF 這類須留存到上線的參數。日期 2026-06-22。
> 狀態:Claude 初版,待 Codex+Composer 雙家族獨立窮舉補漏 → 三方 reconcile。

## 分類框架（判準=「上線對新資料能否因果重算出與訓練時同分布的值」）
- **A 擬合/搜尋參數**:在校準樣本上搜/擬一次→固定→套用。上線無法重算,**必須隨 run/model 留存**。
- **B 路徑依賴/累積**:從序列起點累積。上線須帶 running state 或套**一致 reset/burn-in 規則**(train/test/live 同規則)。
- **C peer/universe 依賴**:值取決於同期參考集。上線須有同一參考集/標的。
- **D 因果滾動/無狀態**:固定窗 rolling 或純函數。上線從近 N 根自算→**安全,無須留存**。

## A — 擬合/搜尋參數（須留存）★上線前置必做
| 項 | 層 | 機制 | 現況留存? | 風險 |
|---|---|---|---|---|
| **fracdiff d\*** | L6.5 | ADF 二分搜最小平穩 d,per-feature,前500校準 | ⚠️ 共用快取 `feature_preprocessing/d_star_*.json`,**config-hash 鍵、換範圍覆蓋、未綁 run/model** | 三方實證確認:換窗 d* 漂(0.13↔0.81)。**必留存** |
| **ADF integer differencing 決策** | L6.5 | `_apply_adf_differencing`(:2504),`do_adf` 預設 off;啟用時 per-feature 差分階數決策 | ❓ **疑無持久化**(待查) | 若啟用=同 d* 類,須留存 |
| **gaussian_normalize** ❗高優先 | L6.5 | `gaussian_config`;QuantileTransformer/常態化常為 **fitted**(學 quantile→gaussian 映射) | ❓ **待查 rolling vs fitted** | 若 fitted→**強須留存**,目前可能漏 |

## B — 路徑依賴/累積（須一致 reset/burn-in + 上線帶 state）
來源:`warmup_table.yaml cumulative_special_cases`(:367)
| 指標 | family | 規則 | 上線注意 |
|---|---|---|---|
| OBV | cumulative | burn_in_from_dataset_start | 純累加,絕對值不可比,須一致起點 |
| AD | cumulative | burn_in_from_dataset_start | 同 OBV |
| ADOSC | cumulative_diff_ema | burn_in + 5x slow | oscillator 收斂,須 burn-in |
| VWAP | cumulative | session_reset_or_burn_in | **註解已明寫:ML 須 train/test/live 一致 reset 規則** |

## C — peer/universe 依賴
| 項 | 層 | 依賴 | 上線注意 |
|---|---|---|---|
| cross-sectional relative strength | L5 | `config.cross_sectional.reference_symbol`(固定參考,非動態 peer) | config 可重現,但上線須有該 reference 標的即時資料 |

## D — 因果滾動/無狀態（安全,無須留存）
winsor(rolling 252)、zscore(rolling 100/252)、rank(rolling 252)、EMA/RSI/ATR/momentum/trend、rolling OLS slope(cumsum 是 rolling 向量化非 from-start)、L4 lag(純 shift)、L1 大部分 talib 指標。**判準:固定窗 + 因果 + 無跨樣本擬合**。

## 開放問題（給委員會窮舉驗證,勿信我已窮舉）
1. **gaussian_normalize 是 fitted 還 rolling?**(高優先,可能漏的 A 類)
2. ADF differencing 決策啟用時是否持久化?
3. 是否還有其他 `.fit()`/optimal search/threshold 校準(除 d*/ADF/gaussian)?
4. 是否有非-rolling 全域統計(full-sample mean/std/quantile)潛藏=既 leakage 又 fit-persist?
5. cumulative_special_cases 是否完整(OBV/AD/ADOSC/VWAP 之外)?entropy R/S 的 cumsum(:248)是窗內還 from-start?
6. native-tf / multi-TF 對齊(idx_map)是否引入 fitted state?
7. L6 meta(consensus/time/interaction)是否引入跨特徵 fitted state?
8. L7 validation/persistence 是否有全域 stat 門檻?

## 初步結論（待三方確認）
- **確定須留存(A)**:fracdiff d*(已證)。**疑似(高優先查)**:gaussian_normalize、ADF differencing。
- **須一致規則(B)**:OBV/AD/ADOSC/VWAP。
- **上線數據依賴(C)**:L5 reference_symbol。
- **上線前置 epic 範圍**=A 全項持久化(綁 run/model)+ B 一致 reset 規則固化 + C reference 可得性。非僅 d*。
