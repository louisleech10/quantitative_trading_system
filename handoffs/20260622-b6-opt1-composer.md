# B6 Option1 設計委員會 — Composer 2.5 (read-only)
task=B6-opt1 | 2026-06-22 | 前提:放棄全範圍 byte parity;fracdiff/ADF/cumulative=Option A 例外;run 內自洽+因果

## ① 可證偽驗證契約(取代 parity)
**A 品質增益(主驗收)**:同 symbol/TF/[start,end],flag-on vs flag-off;對 `POSITION_INDEPENDENT` 欄(見④排除表)量測 start 後 K=min(50,max_warmup/4) 根內 `valid_frac`(非 NaN);assert on≥off+δ(δ=0.05 起,真實 kline 定)。不足歷史→`warmup_insufficient`+前段仍可能 on≈off。
**B 子集 allclose(輔)**:排除表外欄,同窗且 available≥needed 時 date-windowed vs 全範圍同日期 `allclose≤1e-6`+NaN mask 一致;失敗不擋,僅 regression。
**C 因果**:max(ingest_index)<start;特徵/IC 輸出列 index∈[start,end];校準列 assert 取自 ingest 前 min(500,len) 非 start 後。
**D 自洽**:同參數重跑 byte 一致;`row_count==|[start,end]|`;metadata 與列數一致。**更好定義**=flag-on 前段 valid_frac 曲線,非對全史 parity。

## ② cumulative — OK(run-relative)
`burn_in_from_dataset_start` 僅 yaml,FF 未實作;OBV/AD 自 ingest 起累加。文件標 `cumulative_anchor=ingest_start`;ML 用差分/排除絕對量級;不納入 max_warmup 也不納 B 子集。ADOSC 註 EMA settle≈5×slow。

## ③ labels end-side — 維持 start-scope+文件
ingest `[start-warmup,end]`(不延 end+horizon);`shift(-h)` 使尾端 max(horizons)=21 根 label 自然 NaN。metadata:`label_tail_nan_bars=21`,`label_valid_through≈end-21`。不為 label 單獨延 OHLCV(避免特徵路徑混入未 trim 未來 bar);若日後要 end 邊界 label 需獨立 close-only 延伸路徑,非 Option1 最小範圍。

## ④ max_warmup 完整來源(primary TF bars)
`max(` **L1** `get_max_warmup_bars(ind:period)`+CDL `get_pattern_default_bars()`; **L2** max(momentum lags,WQ windows,decay_linear窗); **L3** max(rolling windows); **L4** max(config lags|adaptive seq×ratio); **L6.5** max(winsor窗,rank窗,zscore windows,fracdiff max_lag,ADF max_lag,calibration_bars); **native-tf** 各次 TF `scale_window_for_native(·,src,primary)` 取 max; **multi-TF** 次 TF ingest 起點=對齊後能覆蓋 primary ingest_start 之 source bars; **validator** winsor fallback 窗(僅 L6.5 winsor off)` )`。**排除/不追 parity**:cumulative 族,fracdiff d*,ADF order,post-IC/API rank-zscore,labels horizon。

## ⑤ 多 persist+多TF 最小實作
單一 `OutputWindow(ingest_start,output_start,output_end)` 於 generate 入口算一次。`_layer0` 各 TF 用對應 warmup 載入;multi-TF 次 TF 用 primary `ingest_start` 反推 source 時間跨度(非共用 primary bar 數)。**trim 單 choke**:L7 persist 前 `_trim_to_output_window` 套 features/labels/manifest `row_count`/`time_range`/sidecar;路徑: normal L7、CGSA `_layer7_raw/_validate`、multi-TF 走 primary_raw、IC-first raw+processed。CGSA L3 stream 中間 shard 可暫含 warmup;L7 finalize 裁 manifest;B6 初版可禁 warmup+stream resume 或 resume 後重算 L7 裁切。

## ⑥ 有無更簡方案?
**只 trim 不 warmup**=現 B5 strict,前段降級,最簡但非 Option1。**只 warmup 不 trim**=輸出含前史,違需求。**僅 UI 警示**不解前段 NaN。結論:warmup→trim 是達「輸出=[start,end]+前段可用」最小正確解;實作壓到 `_resolve_output_window`+`_layer0`+L7 單 trim。

## SPEC/TODO 修補
§C 改「品質增益+子集 allclose+因果」;FRACEXC 擴 fracdiff+ADF+cumulative;Task1.1 用④清單;Task2.2 列四 persist 路徑+manifest;labels/end 寫③。

STATUS: DONE
