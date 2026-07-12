# IC/API 測試分層與「合成 vs 真 kline」判準

> 出處:IC-API-TEST-MODERNIZATION epic(2026-07-12)。Phase 1 修復 23 個違憲 API 測試(commit 56a9566);
> Phase 2 三方 scope 分類確認其餘 momentum IC 測試多為合法合成(遷移標的=空集);本檔=Phase 3 收尾。
> 目的:讓未來 IC/API 測試一眼可判該用真 kline 還是合成,避免(a)重犯 Phase 1 違憲、(b)誤遷合法 mutation/perf 測。

## 鐵律背景
專案鐵律:**數據正確性測試必用真實 kline `data_cache/feature_klines/kline_cache.h5`;禁合成 fixture;回歸禁 sanitized fixture**。
關鍵是「**數據正確性測試**」的界定——不是所有用合成資料的測試都違憲。

## 三層分類

| 層 | 定義 | 資料策略 | 範例 |
|----|------|----------|------|
| **L0 純邏輯/契約** | 不 ingest 進 IC 管線;測路由/schema/錯誤路徑/元件函式(filter/alignment 規則) | 合成受控或無 fixture,**合法** | 404/422 驗證、`_apply_feature_filter` 直呼、`test_ic_config_update` |
| **L1 API 表面** | 走 IC service ingest,但斷言 HTTP/報告 schema/任務生命週期,**不斷言 IC 數值** | **真 kline 衍生共用 session fixture**(Phase 1 `tests/fixtures/ic_api_real_kline.py`) | 匯出格式、task status、summary、grouped、numpy 序列化 |
| **L2 真管線** | 各自走真 orchestrator 全鏈(`/full-analysis`),需真計算結果 | **真 kline**;可加 PIT falsifiable 斷言 | `test_full_analysis_endpoint`、deep-analysis 生命週期 |

## 「該用真 kline」判準(MIGRATE)
測試命中**任一**即須真 kline:
1. **注入 kline_reader / meta.symbol+timeframe → 觸發 Tier-2 close 值 oracle**,且以合成餵 IC 輸入冒充「可跑契約」(Phase 1 違憲型)。
2. **斷言資料正確性 / IC 數值 / PIT**(label 前瞻正確、feature 無洩漏、IC/IR 值)。
3. 走 stage0 ingest 且宣稱驗證真實 IC 輸入面。

## 「合成合法」判準(LEGIT-SYNTHETIC,禁誤遷)
測試命中**任一**即合成恰當,**遷真 kline 反而破壞其目的**:
1. **受控 adversarial mutation 探針**:故意餵壞資料(錯位 shift/wrong-TF/RangeIndex/單軸 labels)證 fail-closed 護欄會擋——真 kline 無法製造這些壞例,會毀可證偽性。
2. **FDR/顯著性閘邏輯**:植入 latent 信號使 on/off 兩態可分離(真 kline 難保證兩態)。
3. **OOS gap/purge/train 污染 hash 結構測**:需受控 MultiIndex/時間軸。
4. **管線煙測 / 結構驗證 / 效能壓測**:斷言報告 key 齊全、event tier、refilter 快取、大矩陣(800×10k)效能——無 kline_reader、無數值 oracle。

## Phase 2 分類結論(2026-07-12 三方,審計 handoffs/IC-API-TESTMODERN-P2SCOPE-{grok,composer}.md)
5 個 momentum IC 合成測試分類=**全 LEGIT-SYNTHETIC**(遷移標的空集):
- `test_ic_e2e.py`:管線煙測+800×10k perf,無 kline_reader、無數值 oracle → LEGIT(主委實測確認,composer 曾主張 MIGRATE 但無 oracle/perf 需大矩陣故裁 LEGIT)。
- `test_ic_feature_filter.py` / `test_ic_filter_orchestrator.py` / `test_ic_cross_sectional_cut2.py` / `test_ic_1eb_b4_fullstack.py`:護欄 mutation/FDR/OOS 探針 → LEGIT。

## 給未來
新 IC/API 測試落地前,依上表自判層級;L1/L2 一律複用 `tests/fixtures/ic_api_real_kline.py`(或同款真 kline 衍生),
勿新寫 `rng.normal`+`np.arange` timestamp 餵 ingest。真 kline builder 契約:simple 前瞻 return_5+尾5NaN、
feature 全 ≤t 無 future peek、warmup≥最深 feature lookback(rvol=rolling+shift 需 +1)。
