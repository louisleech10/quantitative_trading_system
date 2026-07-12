# 票6 轉向:23 個 stale 合成 fixture 測試的處置策略(主委版,交委員)
Task-id: p2debt-t6 | Chair: Claude(Opus 4.8) | Date: 2026-07-12

## 背景轉折
票6 原估「rename label→return_5」(中)。實作揭露這 23 個 main 既有紅有**多層** stale fixture,
逐層撞 fail-closed 資料正確性護欄:(1) label 欄名 (2) timestamp cadence 12h (3) label 值須 horizon 個尾端 NaN…可能更多。
**關鍵**:這些測試用 `rng.normal` 合成噪音,**違反專案鐵律**「數據正確性測試必用真實 kline
`data_cache/feature_klines/kline_cache.h5`;禁合成 fixture;回歸禁 sanitized fixture」。
使用者提問:既然有真實 kline,舊測試是否乾脆刪/改用真實數據重建?委員覺得如何?

## 這 23 測試的性質(主委分類)
多為 **API 層測試**,靠共用 fixture 取得「已完成 IC 任務」當前置,再斷言 API 回應:
- `test_export_api.py`(7):匯出 CSV/HDF5/markdown/AI-json 格式、422 錯誤路徑 ← fixture `export_task`
- `test_ic_analysis_api.py`(9):task status/result/summary/top_features/grouped/refilter/export ← fixture `ic_analysis_task`
- `test_ic_deep_analysis.py`(7):full-analysis/deep-analysis 生命週期 ← fixture `sample_paths`+`completed_ic_task`
真正需要「真實計算結果」的少(full_analysis);多數只需「某個完成的任務」測 API 行為。

## 主委建議(供委員挑戰)
**選項對比**:
- **A 全刪**:失掉匯出/狀態/序列化的 API 層覆蓋(有價值,非冗餘)。過度。
- **B 共用 fixture 改真實 kline(主委傾向)**:把 `export_task`/`ic_analysis_task`/`sample_paths` 的資料源
  從 `rng.normal` 換成真實 kline 切片(參照 tests/test_phase6_end_to_end.py 等既有真 kline 測試),
  一改 fixture→23 一起活;守鐵律、保覆蓋、比逐層修假資料省事。
- **C 分類處理**:純 API 層(匯出格式/狀態/422)可用「真 kline 產一次真結果」共用;
  full_analysis 這種本就該走真管線真資料。B 的細化。

## 交委員(grok+composer 各獨立給建議)
1. A/B/C 哪個對?或有更好第四選項?
2. B 的真實 kline fixture:切片多大/哪 symbol-TF 才能既過所有護欄(cadence/NaN/PIT)又快?
3. 有無測試真的該刪(測過時行為/與其他測試重複)?
4. 這是否已脫離「P2 債清理」變成獨立 test-modernization epic,該不該從票6 拆出?
輸出各自 handoffs/P2DEBT-T6-TESTSTRATEGY-{grok,composer}.md,一句話結論 + 理由。唯讀,禁改碼。
