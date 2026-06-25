使用者可稽核：cat .claude/gate/audit.log
# VERDICT: **CHANGES**

五項查證主張**全部屬實**；綜合版對 Turnover 主流程、schema 嵌套、成本幽靈等核心修正**優於 Claude R1**，且**正確採納 Cursor/Gemini、駁回 Codex 對 EquityCurve 的漏判**。但仍有 **PIT 表述過度**、**cross-sectional 主戰場缺口未升格**、以及 **4 份原始版若干技術債未併入**——建議修完再交委員會簽核。

---

## 逐條查證（附證據 + 改法）

### 1. `turnover.enabled` 假開關 — **屬實 ✅**

**證據**

```1173:1175:momentum/Analysis/ic_filter_orchestrator.py
        quantile_results = self._monotonicity.compute_all(features_df, label_series)
        coverage_results = self._coverage.compute_all(features_df)
        turnover_results = self._turnover.compute_all(features_df)
```

- Config 有 `TurnoverConfig.enabled`（`ic_config_schema.py:138-139`）與 `ic_config.yaml:93-94`，但 Stage 5 **無任何 `if config.turnover.enabled` gate**。
- 綜合版 `:1175 幽靈` 描述正確。

**改法（SYNTHESIS）**：維持；可補一句「`transaction_cost: 0.001` 同在 TurnoverConfig 但亦未接入 Net IC 主路徑」（見 Cursor/Codex，見 #2 延伸）。

---

### 2. Crypto 5bps 偏樂觀 + `slippage_bps` 未讀 — **屬實 ✅**

**證據**

```17:22:momentum/Analysis/net_ic_analyzer.py
class NetICAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._default_cost_bps = float(cfg.get("default_cost_bps", 5.0))
        self._cost_scenarios = list(cfg.get("cost_scenarios", [1, 3, 5, 10, 20]))
```

```181:185:config/ic_config.yaml
net_ic_analysis:
  enabled: true
  default_cost_bps: 5
  slippage_bps: 2
  cost_scenarios: [1, 3, 5, 10, 20]
```

- `slippage_bps` 在 schema/yaml 存在，`NetICAnalyzer.__init__` **只讀 `default_cost_bps` / `cost_scenarios` / `participation_rate`**，公式 `net_ic = gross_ic - (cost_bps/10000)*turnover*2`（`:34`）**不含 slippage**。
- 預設 5bps 單邊 ≈ round-trip 10bps fee-only；對散戶 spot taker ~10bps/leg → **~20bps+ round-trip**，綜合版「偏樂觀」成立（Gemini 的 VIP 5bps  nuance 可 footnote，非主戰場預設）。

**改法（SYNTHESIS）**：維持；**補遺漏**：
- 前端 `NetICChart.tsx:44` 成本下拉硬編 `[1,3,5,10,20]`，不讀後端 `cost_scenarios`（Codex P1）。
- `TurnoverAnalyzer.compute_net_ic_proxy`（`turnover_analyzer.py:125-137`）用 `transaction_cost=0.001` 的**第三套成本 heuristic**，與 NetICAnalyzer 孤島（Cursor）。

---

### 3. `estimate_factor_capacity` 存在但 volume 未餵 → unknown；backtest 孤島 — **屬實 ✅**

**證據**

```913:927:momentum/Analysis/ic_filter_orchestrator.py
    def _run_net_ic(self, selected_features: list[str], config: ICConfig) -> dict:
        ...
        summary = {
            row["feature_name"]: {"ic_mean": row.get("ic_mean")}
            for row in (self._report or {}).get("summary_table", [])
            ...
        }
        ...
        return analyzer.batch_analyze(summary, turnover_data)
```

```97:101:momentum/Analysis/net_ic_analyzer.py
        if avg_daily_volume_usd is None or avg_daily_volume_usd <= 0:
            return {
                "estimated_capacity_usd": np.nan,
                "capacity_tier": "unknown",
            }
```

- `batch_analyze` 讀 `metric.get("avg_daily_volume_usd")`（`:167`），orchestrator **只傳 `ic_mean`** → 實務永遠 `unknown`。
- Backtest：`vectorized_backtest.py:41` `commission=0.001, slippage=0.0005`，與 IC pipeline **無 config 共享**。

**改法（SYNTHESIS）**：維持；**補遺漏**：
- 即使有 volume，`capacity_tier` 仍按 **turnover 門檻**分 high/medium/low（`net_ic_analyzer.py:109-114`），非真正 ADV 容量（Codex）。
- Gemini：`test_no_volume_for_capacity` 證實退讓行為；Feature Factory 有 **Amihud Illiquidity** 因子但**未接入 IC 容量管線**——型 3「散落」應記一筆。

---

### 4. QuantileReturnChart schema 空圖延燒階段四；主 vs deep spread 不一致 — **屬實 ✅**

**證據 — 嵌套 vs 扁平**

後端 `monotonicity_tester.compute_all` 包裝：

```160:164:momentum/Analysis/monotonicity_tester.py
            results[feature] = {
                "quantile_returns": quantile_returns,
                "monotonicity_score": monotonicity_score,
                "long_short": long_short,
            }
```

報告直出 monotonicity dict（`ic_filter_orchestrator.py:1270`）。前端：

```727:728:frontend/src/app/ic-analysis/page.tsx
                    <QuantileReturnChart
                      data={report?.quantile_returns?.[activeFeature || ''] || null}
```

圖表讀頂層欄位：

```13:14:frontend/src/components/ic-analysis/QuantileReturnChart.tsx
  const chartData = data
    ? Object.entries(data.quantile_mean_returns || {}).map(...)
```

```51:51:frontend/src/components/ic-analysis/FactorEquityCurveChart.tsx
    const cumulativeReturns = data?.cumulative_returns;
```

→ 實際在 `data.quantile_returns.quantile_mean_returns` / `.cumulative_returns` → **basic 分位圖 + deep EquityCurve 皆靜默空圖**；`summary_table.long_short_spread` 仍可能有數（`:1398-1400`）→ **表有數、圖空**。Codex「EquityCurve 未接錯」**被碼駁回**；綜合版正確。

**證據 — spread 定義不一致**

- 主流程：`high_mask == max quantile`, `low_mask == min` → **Qmax − Qmin**（`monotonicity_tester.py:113-126`）。
- Deep：`long_quantiles=[4,5]`, `short_quantiles=[1,2]`，short 取負收益（`long_short_analyzer.py:23-24,60-65`）→ **Q4+Q5 vs Q1+Q2 不對稱組合**。

**改法（SYNTHESIS）**：維持；明確寫 **QuantileReturnChart 在 basic tab**（`page.tsx:727`），EquityCurve 在 deep tab（`:775`）——影響面不同 tab 但同源 bug。

---

### 5. 階段四是否該加第 4 型？ — **不必加；3 型結構足夠**

**依據**

- `STAGE4-brief.md` 明定 **3 型**。
- **Break-even cost** 已在型 2 `NetICAnalyzer.compute_net_ic` `:41` `breakeven_cost_bps`。
- **Capacity-adjusted IC** 應併入型 3 擴展（ADV wiring + UI），非獨立新型。

**改法（SYNTHESIS）**：待委員檢查 #4 可改為**已決**：「3 型不增；型 3 補 ADV→capacity + 型 2 補 slippage 進公式 + breakeven 進 summary table（Gemini 建議）」。

---

### 6. 9 欄業界標準 / 洩漏防禦量化錯誤 + 原始版重要遺漏

| 議題 | 判定 | 證據 | 改法 |
|------|------|------|------|
| 型 1 🛡️「分位邊界 train window」 | **過度/不精確 ⚠️** | 主流程 `pd.qcut` 對**全樣本**分位（`monotonicity_tester.py:104`, `turnover_analyzer.py:31`）；Cursor 指「非 expanding rolling quantile」 | 改為「分位邊界取決於 upstream；現況 full-sample qcut，嚴格 PIT 需 rolling/expanding」 |
| 型 1 📐 Newey-West | **未驗證實作** | grep 無 NW；列為業界標準 OK，但 🗂/📊 應標「平台未實作」 | 在 🔧 加「NW t-stat 未實作，現用普通 t-test」 |
| 型 2 📐「標準組合 turnover」 | **正確對照** | 實作為 top-quantile 0/1 membership flip rate（`turnover_analyzer.py:36-40`） | 維持 |
| Cross-sectional 主戰場 | **綜合版欠突出 ⚠️** | `quantile_returns:{}`, `turnover_analysis:{}`（`ic_filter_orchestrator.py:322,330`）；`long_short_spread: None`（`:274`） | **全棧表加第 4 行或結論首條**：cross-sectional 下階段四**整型 ❌** |
| `compute_net_factor_return` 未餵 | **遺漏** | orchestrator `_run_net_ic` 未傳 `factor_returns`（`:927`） | 型 2 🔧 補「factor return 序列路徑存在但未接」 |
| NetICChart 不展示 capacity | **部分遺漏** | grep NetICChart 無 capacity | 型 3 🧩 已提 types 有欄位；可點名 NetICChart |
| Claude R1「三者皆 deep」 | **綜合版已修正 ✅** | Turnover 主 Stage 5；Monotonicity spread 主流程 | 無需回退 |
| UI 主/deep L-S 命名混淆 | **遺漏（Codex P0）** | 兩套語意並存 | 型 1 🏷️ 加「UI 需分名主 spread vs deep leg analysis」 |

---

## 綜合版相對四家的評價

| 來源 | 綜合版處理 |
|------|-----------|
| **Cursor** | 核心 finding 幾乎全收（schema、ghost toggle、cross-sectional、crypto cost）；**cross-sectional 整型 ❌ 未升格到表/結論** |
| **Gemini** | schema bug、5bps、capacity unknown ✅；**Amihud 散落、breakeven→summary 建議** 未收 |
| **Codex** | Turnover 主流程、slippage 幽靈、backtest 孤島 ✅；Codex 錯判 EquityCurve **未被綜合版繼承（正確）**；**frontend 硬編 cost、transaction_cost 孤島** 未收 |
| **Claude R1** | 正確升級 Turnover/L-S 為雙軌主+deep ✅ |

---

## 建議 SYNTHESIS 最小修補清單

1. **結論首條增**：cross-sectional（使用者主戰場）下階段四三型 **整型 ❌**（`ic_filter_orchestrator.py:322-330`）。
2. **型 1 🛡️**：刪「train window」斷言，改 full-sample qcut + upstream 依賴。
3. **型 2 🔧 增**：`NetICChart.tsx:44` 硬編 cost；`turnover.transaction_cost` + `compute_net_ic_proxy` 第三孤島；`compute_net_factor_return` 未接。
4. **型 3 🔧 增**：Amihud（Feature Factory 微觀流動性因子）散落；`capacity_tier` 邏輯非 ADV-based（`:109-114`）。
5. **待委員 #4 改已決**：3 型不增；子能力併入型 2/3。

---

**ASSUMPTIONS_VERIFIED**: 以上 6 項均經讀碼；crypto fee 數字為市場慣例推論（未跑 live API），標為 industry reference。  
**TESTS_RUN**: read-only；未跑 pytest/UI。  
**FAILURES_SEEN**: none  
**SCOPE_CHANGES**: none  
**NUMERIC_OR_SCHEMA_IMPACT**: none（審查 only）

**STATUS: DONE**
