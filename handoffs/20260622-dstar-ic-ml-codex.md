# 20260622 d* calibration vs B6 byte parity — Codex read-only view

## Position
同意 Option A 作為近期產品決策：接受 date-windowed 與 full-range 在 fracdiff d* 上不 byte 一致，d* 仍用該 run 序列前 500+ bars 校準。

## Verified facts
- `feature_preprocessor.py` `_calibration_series()` 使用 `series.iloc[:bars]`；`bars=max(adf sample_size, preprocessing.calibration_bars, 500)`。
- `feature_factory.py` `_compute_config_hash()` 明確加入 `_start_date`/`_end_date`，date-windowed 與 full-range 是不同 run hash。
- `DStarCache` 檔名不含 config_hash，但 payload 檢查 `time_range`/`row_count`，entry 又用整欄 strong value fingerprint；不同切片不應互相污染。

## Claude 5-point argument audit
- ① cache 隔離：基本成立；補充 caveat 是「run hash 隔離」保護 feature output，d* cache 真正防污染靠 time_range/row_count/value_fp，不是 config_hash。
- ② 500-bar 穩健：通常成立，但不是數學保證；金融序列 regime shift、短窗、低 liquidity/上市早期、結構性缺失會放大變動。
- ③ IC rank robustness：對單調縮放穩健，但 fracdiff d 改變不是純單調轉換；會改變記憶長度、NaN warmup、局部排序，尤其 trend/MA/volume 類 I(1) 特徵。
- ④ ML post-IC rank/zscore：能洗掉 scale/location，不會洗掉 temporal filter 差異、缺失 pattern、feature selection 邊界差異。
- ⑤ run 內自洽：成立；這是 Option A 的核心正當性，但它犧牲的是 cross-window byte parity，不是資料正確性。

## Quant impact
- 一般情況：d* 小幅差異對 Spearman IC/rolling IC 與 ML 訓練多半是二階影響；排名、zscore、模型 ensemble 會降低敏感度。
- 放大情境：d* 接近 ADF 門檻、bisection precision 粗、樣本前 500 非代表性、切片起點落在 crash/bubble/上市 warmup、row 數短、特徵本身高度 persistent 或 borderline I(0)/I(1)。
- 實質風險：IC 穩定性排序在邊界特徵上可能翻轉；ML feature importance/selection 可能受缺失起點與記憶長度影響。

## Option tradeoff
- A first-500 per run：最 causal、最快、cache 自洽、實作風險最低；缺點是 B6「全範圍切片 byte parity」對 fracdiff 例外。
- B load-to-dataset-start：最接近 full-range parity；但成本大，違背使用者選短日期時的資源預期，且用很久以前 regime 校準未必更好。
- D stable calibration window：較可重現，可選固定 anchor/history policy；但需新語義、cache key、UI/文件與回歸驗證，且選窗本身會引入主觀假設。

## Better windows
- 全序列：不建議作為預設，會用到未來資訊校準 d*；研究回測可標明 non-causal 才可用。
- 最近 500：對預測當下 regime 更貼近，但在歷史 feature generation 中會造成每個切片依 end date 漂移，且可能 look-ahead 式使用切片後段。
- 固定歷史 anchor 500/1000 或 train-start 前 rolling calibration：量化上較乾淨，但 scope 明顯大於 B6。

## Risk note
Option A 應把 fracdiff d* parity 明確列為 B6 例外：date-windowed/full-range 不保證 byte 一致，但不構成 cache 污染或資料洩漏；建議後續用真實 kline 抽樣量化 d* delta、IC delta、selected feature overlap。
