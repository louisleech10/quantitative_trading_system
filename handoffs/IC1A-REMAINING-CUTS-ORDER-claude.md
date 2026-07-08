# IC 1a 剩餘刀施工順序提案 — Claude 獨立版

**Task**: IC Phase 1 剩餘刀(1-align / 1b FDR / 1c Net IC / 1d attribution / 1e HAC / 1f 空圖)排序
**Date**: 2026-07-08
**前提偵察(實查現行 code,非沿用舊結論)**:

## 偵察事實(receipt)

1. **1-align 幽靈**:`momentum/core/contracts.py:764 validate_alignment` + `AlignmentSpec` 存在,但 grep 全 repo 生產路徑零 caller(只有 contracts 本體與測試)。cut1/cut2 已加 OOS holdout+purge+embargo,但無顯式 Feature_t vs Target_t+1 錯位硬閘。
2. **1b FDR 幽靈**:`statistical_validator.py:58 adjust_multiple_comparisons`(含 `_fdr_bh`)存在,orchestrator 從未呼叫;實際選擇路徑=`_apply_thresholds`(orchestrator:1975)用裸 per-feature p≤p_value_max(0.05)。430K 特徵 ≈ 21,500 假陽性。
3. **1c Net IC 量綱錯誤仍在**:`net_ic_analyzer.py:34` `net_ic = gross_ic − (cost/10000)×turnover×2`,相關係數減報酬率。應依 Grinold(IC − Cost×Turnover/截面波動率 類)。
4. **1d attribution NaN 繞過仍在**:`factor_exposure_analyzer.py` :36/:44/:54/:59/:73/:84/:94 全 `fillna(0.0)`;「Neutralized IC」實為轉換 summary 非真 residual IC(名實不符)。
5. **1e HAC 缺**:`statistical_validator.py:119` 對 rolling IC 值(重疊窗、高自相關)跑 1-sample t-test 當 i.i.d. → t/p 顯著性系統性高估;`factor_return_analyzer.py:103` `newey_west_adjusted: False` 硬編。
6. **1f 空圖仍在**:後端 report `quantile_returns` 巢狀(orchestrator:2079),前端 `FactorReturnChart.tsx:19` 只讀 `quantile_returns_summary` → 圖空 summary 有值。純接線/schema 修,無統計正確性風險。
7. **grouped_ic 止血已完成**:Phase 0 commit `11507f5` 已改傳 `grouped_analysis.model_dump()`(orchestrator:1917)。HANDOFF「grouped_ic 止血」過時;殘餘只剩 IC-PERF(P1 向量化,另 epic)。

## 我的順序提案

**核心邏輯:沿數據流上游→下游修(對齊 → 顯著性 → 經濟性 → 歸因 → 顯示),上游錯則下游全白算。**

| 順位 | 刀 | 任務大小 | 理由 |
|---|---|---|---|
| 1 | **1-align 前瞻硬閘** | 中 | Gemini 紅線:差 1 tick IC 就爆;所有下游統計的前提。契約已有 `validate_alignment`,主要是接線+定 AlignmentSpec 語義,scope 可控 |
| 2 | **1e HAC + 1b FDR 合併一刀「顯著性正確化」** | 大 | 兩者同一條 p-value 生產→消費鏈:HAC 改 p 值、FDR 消費 p 值;分兩刀會做兩次 selection 行為變更+兩輪回歸凍結。同檔(statistical_validator+orchestrator threshold 路徑)。命中 (a)(d) |
| 3 | **1c Net IC 量綱修正** | 中 | 獨立模組(net_ic_analyzer),公式替換+scenario 表回歸;不動 selection 主鏈 |
| 4 | **1d attribution 正名/NaN 政策** | 中 | 決策點:接真 residual IC(較大)vs UI 正名 proxy+NaN fail-closed(較小);建議先正名+NaN 政策,真 residual IC 歸 Phase 2B |
| 5 | **1f 空圖 schema 接線** | 小-中 | 純前後端 wiring,無統計風險;放最後或任意插隙(quick win,若使用者要先看到圖可提前) |
| — | grouped_ic 止血 | 已完成 | 從清單移除;IC-PERF 留 P1 |

**替代排序考量(供委員會挑戰)**:
- 1f 可提前到任何位置(正交、便宜、使用者可見)——我不反對排第 1 當 quick win,但它不擋任何正確性刀。
- 1e/1b 若委員會認為合刀過大,可拆:1e 先(p 值先正確)→ 1b 後(FDR 接正確的 p 值)。**反對先 1b 後 1e**:FDR 接在高估的 p 值上=白接一輪、行為兩次跳動。
- 1-align 若偵察後發現 cut1/cut2 的 purge+embargo 已實質涵蓋錯位風險,可降級為「補硬閘測試」的小任務——此判斷需委員會驗證。

## 治理約束(SCAR,適用每刀 SPEC)
- SPEC consumer-map 須含所有對 load/report 結果 reindex/merge 的 consumer + 真路徑 red-on-break 測試。
- 涉 (a)(d):三方數據正確性簽核,至少一腿 explicit adversarial;真實 kline/FF 資料(3sym×1h+12h 已就緒 `data_cache/features/`)。
- 測試設計受審:聲稱驗正確性的測試須 mutation 證偽。
