# 特徵管線「上線須留存參數」盤點 — R1 三家合併超集
> Opus+GPT5.5(Codex)+Composer2.5 各自產 R1 → 本檔=合併超集+Opus 審查。日期 2026-06-22。
> 狀態:R1 完成。待 R2 交叉審(每家審另兩家+本超集)→ R3 收斂。判準見下。
> 判準:A=校準樣本搜/擬/全樣本統計(上線無法因果重算,須留存或改causal);A-schema=全run決定欄存在(須pin特徵清單);B=從起點累積(一致reset/burn-in+state);C=peer集依賴;D=固定窗rolling/純函數(安全)。

## A — 擬合/搜尋/全樣本統計（須留存或改 causal）
| # | 項 | 層 | 機制(證據) | 現況留存 | 嚴重度 | 發現者 |
|---|---|---|---|---|---|---|
| A1 | **fracdiff d\*** | L6.5 | ADF二分搜最小平穩d,前500校準,per-feat (`_find_min_d`:3687) | ⚠️共用快取`d_star_*.json`,config-hash鍵,換範圍覆蓋,未綁run/model | **高**(實證漂0.13↔0.81) | 三家 |
| A2 | **ADF integer differencing** | L6.5 | 前500 ADF `chosen_diff` 每欄差分階 (`_apply_adf_differencing`:3301) | ❌**無持久化**;preset `professional_full` **預設開** | **高**(若開) | Codex+Composer |
| A3 | non_stationary 分類 | L6.5 | ADF前500→欄位集合 (`_get_non_stationary_columns`:3582) | 僅記憶體 `NonStationaryCache` | 中 | Composer |
| A4 | **L2 safe_denominator** | L2 | **全欄 median(\|denom\|)×1e-6** threshold (`numeric_guards.py`:48,Opus驗證確認) | 即時算,未留存 | 低(僅噪音級1e-6分母;但輕微look-ahead+train/serve微差) | Codex |
| A5 | labels winsorized | labels | 全樣本 quantile (`label_generator.py`:79) | ❌全樣本=洩漏 | 中(label非serving feature,但研究須記錄) | Codex+Composer |

## A-schema — 全 run schema/drop 決策（上線須 pin「特徵清單」）
| # | 項 | 層 | 機制 | 發現者 |
|---|---|---|---|---|
| S1 | dead/drop feature gates | L3/L7 | 全run `nunique/std/nan_rate/valid_count` 決定欄是否存在 (`dead_feature_filter.py`) | Codex |
| S2 | L3 skew/kurt low-card skip | L3 | 全欄 `nunique` 決定 skew/kurt 是否生成 (`rolling_aggregator.py`) | Codex |
→ 上線:模型期望的欄位集合須與訓練一致(schema pin),否則缺欄/多欄。

## B — 路徑依賴/累積（一致 reset/burn-in + 上線帶 state）
| # | 項 | 層 | 性質 | 發現者 |
|---|---|---|---|---|
| B1 | OBV/AD/ADOSC | L1 | 純累加器,絕對 level 永不收斂,須一致起點/只用相對 | 三家(yaml:367) |
| B2 | EMA/MACD/Wilder/Hilbert/KAMA/Klinger | L1 | bar0 遞推;**warmup 後收斂**(burn-in 足則上線可重算) | Composer |
→ **R2 待釐清**:B2 是「收斂後等同 D(只須足夠 burn-in)」還是真 B(須帶 state)?OBV/AD(B1)確定不收斂。

## C — peer/universe 依賴
| C1 | L5 cross-sectional relative strength | vs `config.cross_sectional.reference_symbol`(固定參考,非fit) | 上線須同 reference 標的即時資料 | 三家 |

## D — 安全（因果可重算,無須留存）★三家交叉確認
- **gaussian_normalize**:rolling rank+`ndtri`,causal釘死,**非 QuantileTransformer/fit**(三家一致;**修正 Opus 初版誤標**)
- **VWAP**:實作 `rolling(20).sum`(`volume_indicators.py`:205),**非 cumulative**(三家一致;**yaml:382 寫 cumulative 與 code 不符=文件 bug 待修**)
- winsor(rolling252)/zscore(rolling100,252)/rank(rolling252)
- entropy R/S `cumsum`:rolling 窗**內**,非 from-start(三家一致,解開放問題)
- L4 lag(純 shift)、L6 meta(逐列 mean/std/rank/sign 固定閾值)、native/multi-TF alignment(deterministic idx_map/searchsorted,版本須一致)、L7 validation(只寫 metadata 不改值)

## R1 修正記錄（作者自審無法抓,交叉審抓到）
1. Opus 把 gaussian 標「疑 fitted」→ Codex+Composer 雙證 D 安全。
2. Opus/yaml 說 VWAP cumulative → Codex+Composer 雙證實作 rolling(20)。
3. Opus 漏 A2/A3/A4/A5/S1/S2(ADF diff/non-stat/safe_denom/labels/schema);Composer 漏 A4/S1/S2;Codex 漏 A3。

## R2 交叉審待解問題
1. B2 遞推族:收斂後=D 還是須帶 state?(分類定性)
2. A4 safe_denominator:改 causal/rolling 還是留存 median?嚴重度再評。
3. S1/S2 schema pin:算獨立類(上線特徵清單)還是 A 子類?
4. **窮舉再掃**:還有沒有其他全樣本 `.median()/.mean()/.std()/.quantile()`(除 A4/A5)?任何 `.fit()`/optimal/threshold 校準?
5. A2 ADF diff:IC-First **預設路徑**到底開不開?(professional_full vs 預設 preset)
6. labels(A5)全樣本 winsor:確認是否 look-ahead 洩漏 + 是否影響 IC/ML 評估真實性(命中回測真實性 (d))。
