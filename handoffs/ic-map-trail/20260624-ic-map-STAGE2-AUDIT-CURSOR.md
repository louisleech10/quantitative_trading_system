**VERDICT: CHANGES**

綜合稿在型1 schema、型3 GroupedConfig 崩潰、by_volatility 幽靈欄位、timestamp 歸位、型4 OOS/ICIR 主軸上大致正確，但型2「崩潰」嚴重度歸因錯、預設觸發條件未限定 tier，且漏掉多家原始版共識的跨型靜默斷裂。以下逐條對照程式碼。

---

### 1. 型1 分位圖 schema 不一致 → 靜默空圖 🔌

**判定：屬實，🔌 標法準確。**

後端 `compute_all` 產出巢狀結構：

```160:164:momentum/Analysis/monotonicity_tester.py
            results[feature] = {
                "quantile_returns": quantile_returns,
                "monotonicity_score": monotonicity_score,
                "long_short": long_short,
            }
```

orchestrator 原樣寫入 report（:1270 是 pass-through，非另寫 schema）：

```1270:1270:momentum/Analysis/ic_filter_orchestrator.py
            "quantile_returns": stage5_results.get("monotonicity", {}),
```

前端讀頂層 `quantile_mean_returns`：

```13:17:frontend/src/components/ic-analysis/QuantileReturnChart.tsx
  const chartData = data
    ? Object.entries(data.quantile_mean_returns || {}).map(([quantile, value]) => ({
        quantile,
        value,
      }))
```

summary table 從巢狀路徑取值所以 **有分數、圖空**（:1395–1399）。REST `/quantile/{feature}` 亦回傳巢狀物件（`ic_analysis.py:242`）。

**改法**：綜合稿可補一句——`FactorEquityCurveChart`（deep tab，`page.tsx:776`）同吃錯 shape（期望頂層 `cumulative_returns`）。修法：orchestrator flatten 或前端解包 `data.quantile_returns`。

---

### 2. 型2 decay、型3 grouped「大 run 崩潰」預設觸發？嚴重度對嗎？

**判定：型3 ✅；型2 嚴重度標法需改。**

**型3 — 預設會炸（intermediate/advanced）：**

```84:92:frontend/src/store/icAnalysisStore.ts
  intermediate: {
    ...
    ic_decay: true,
    grouped_ic: true,
```

```1133:1139:momentum/Analysis/ic_filter_orchestrator.py
        if raw_data is not None and config.report.include_regime_analysis:
            grouped_ic = self._ic_engine.compute_grouped_ic(
                ...
                config.ic_calculation.grouped_analysis,  # Pydantic GroupedConfig
```

```377:377:momentum/Analysis/ic_engine.py
        method = config.get("method", self._methods[0])  # GroupedConfig 無 .get → AttributeError
```

**foundation 預設 `grouped_ic: false`（:66）→ 不觸發。** 綜合稿只寫「intermediate 預設」對型3 正確，總表未標 tier 例外。

**型2 — 不會自己 crash：**

- decay 在 grouped **之前**跑（:1122–1131 → :1133–1139），邏輯完整。
- 瓶頸是 **每 feature 低 R² 打 warning**（`ic_engine.py:943–947`），大 run 極慢；14,090 條未在本輪重跑，標 **未驗證數字**，但熱迴圈路徑屬實。
- job 失敗根因是 grouped AttributeError，decay 已算但報告拿不到——應寫「**連帶 job 失敗/白算**」，不宜寫 decay「大 run 崩潰」。

**改法**：總表型2 改 `⚠️ 大 run 極慢（熱迴圈 log）+ grouped 崩潰連帶 job 失敗`；型3 保留 P0；補「foundation tier 不觸發」。

---

### 3. 型3 by_volatility 契約漂移、timestamp 影響範圍

**判定：正確。**

`by_volatility: bool = True`（`ic_config_schema.py:80`），`compute_grouped_ic` 僅分支 `by_year/by_quarter/by_regime/by_category/by_data_source/by_layer`（`ic_engine.py:383–417`），**無 `by_volatility`**。`high_vol/low_vol` 在 `by_regime` rule 路徑（:1072–1077），與 `by_volatility` 開關無關。

`_get_time_index` 數值 timestamp 硬編 `unit="ms"`（:1024–1025），只經 `_iter_time_groups` 影響 **by_year / by_quarter**（:1006–1016）。rule regime 用 `close` index + 全樣本 `nanpercentile`（:1066–1070），是另一條洩漏線，綜合已提。

**改法**：可加一句 `by_volatility` 與 `by_regime` 內建 vol 分組是不同契約，避免讀者以為開關已生效。

---

### 4. 型4 穩定性：✅ 基礎 + 🔌 OOS deep tab、無 train/test → in-sample ICIR

**判定：準確；可微補。**

- `compute_icir` + `ic_hit_rate`（`ic_engine.py:304–327`）；summary 顯示 ICIR 與 Positive Rate（`ICSummaryTable.tsx:377,429`）。
- `rolling_oos` 在 deep tab（`page.tsx:805`），非主 gate threshold 路徑。
- 主路徑無 train/test split；ICIR 來自全段 rolling IC（:288–290 全列 rank 後 rolling）→ in-sample + rank 洩漏疑慮，Codex/Cursor 觀點成立。

**改法**：型4 補「hit_rate 前端已顯示 ✅」，修正 Claude R1 的 🔶 待查；`ic_autocorrelation` 算了不進 report（見 #7）。

---

### 5. 階段二是否加第5型 drift_analyzer？

**判定：不建議加為階段二第5型；歸「鄰接深度模組」或 ML 驗證軸，不併入型2/型4。**

`DriftAnalyzer` 做 **PSI 分佈漂移**（`drift_analyzer.py:4`），工廠在 `pattern_analysis` / `adversarial_validator`，**未接入** `ic_filter_orchestrator`。

| 模組 | 問題 |
|------|------|
| 型2 IC decay | 預測力隨 horizon 衰減 |
| 型4 ICIR | IC 時間序列穩定 |
| drift_analyzer | train vs test **特徵分佈**漂移 |

語意不同。綜合稿只列為待委員問題、未給定案——應明寫：**維持四型；PSI 放 deep/ML 或獨立「模型監控」軸**。

---

### 6. 9 欄業界標準 / 洩漏防禦有無量化錯誤？

**判定：主線無重大量化錯誤；有遺漏與一處表述可更精。**

| 宣稱 | 驗證 |
|------|------|
| 全樣本 `qcut` 洩漏 | ✅ `monotonicity_tester.py:185–186` 整段一次 qcut |
| ICIR>0.5、hit>55% 門檻 | ✅ `ic_config_schema.py:102–104` |
| regime 全樣本 percentile | ✅ `ic_engine.py:1069–1070` |
| rolling Spearman 全段 rank | ✅ `ic_engine.py:288–290` |
| cross-sectional 分位/decay/grouped 空 | ✅ `ic_filter_orchestrator.py:321–323` 硬編 `{}` |

**遺漏（影響「9欄完整性」）**：
- **幽靈 `feature_filter`**：`ICConfig` 無欄位（`ic_config_schema.py` grep 0）；UI `max_features:30`（`icAnalysisStore.ts:187`）後端忽略——Codex/Cursor/Gemini 共識，綜合僅型1 一句帶過。
- **`include_quantile_curves` 死配置**：綜合已提 ✅。
- **事件 `event_timestamps` 未接線**：`ic_analysis_service.py:965` warning。

**改法**：在「階段二結論」加第三條靜默斷裂：**feature_filter 幽靈**（直接放大四型計算量）。

---

### 7. 綜合是否漏掉原始版重要點？

**判定：有明顯遺漏。**

| 遺漏項 | 來源 | 證據 |
|--------|------|------|
| `feature_filter` 跨型幽靈 | Cursor/Codex/Gemini | 見 #6 |
| `ic_autocorrelation` 算了不輸出、toggle 無 STAGE_OVERRIDE | Cursor | 算於 `:1110`；`STAGE_OVERRIDE_PATHS` 無此 key（`:59–65`）；stage7 無輸出 |
| `regime_robust` 永遠 `None` | Cursor | `ic_filter_orchestrator.py:1404` |
| `event_timestamps` API 不通 | Cursor/Codex/Gemini | `ic_analysis_service.py:965` |
| cross_symbol 資料在 cross-sectional 主報告、UI 在 deep tab | Cursor/Codex | `page.tsx:759` |
| 型1 Claude R1 誤標 ✅ 全棧連通 | Claude R1 | 綜合已修正為 🔌 ✅ |
| Gemini 稱 cross-sectional 空因 OOM | Gemini | 程式為硬編空 dict，非 OOM 分支——綜合未糾偏 |

**改法**：增「跨型靜默斷裂」小節（可抄 Cursor 表），或擴充「階段二結論」第4–6點。

---

## 建議修改摘要（給 Claude 改綜合稿）

1. **型1**：保留 🔌；補 `FactorEquityCurveChart`、REST 同病。
2. **型2**：「崩潰」→「極慢 + grouped 連帶 job 失敗」；區分 foundation 不跑 decay。
3. **型3**：維持 P0；補 tier 條件與 `by_volatility` vs `by_regime` 區分。
4. **型4**：補 hit_rate 已顯示；可提 `ic_autocorr` 幽靈。
5. **第5型**：定案不納入四型；PSI 歸 deep/ML。
6. **結論**：加 `feature_filter`、`event_timestamps`、`ic_autocorr`、`regime_robust` 靜默斷裂。
7. **cross-sectional 空**：註明硬編 `{}`，非 OOM 推論。

核心技術判斷（schema 錯位、GroupedConfig crash、洩漏主線）可信；嚴重度歸因與跨型接線遺漏需補齊後再 APPROVE。
