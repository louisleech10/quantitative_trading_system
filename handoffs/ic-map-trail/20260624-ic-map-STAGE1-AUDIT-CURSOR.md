`VERDICT: CHANGES`

綜合對型 1 / 4 / 6 的主裁決方向正確（讀碼可佐證），但有多處事實錯置、結論過樂觀、以及四家原文重要點未併入。以下逐條附證據與改法。

---

### 1. 型 1「✅ 全棧連通（功能層）+ 幽靈 feature_filter」——**準確**

| 主張 | 證據 | 改法 |
|------|------|------|
| global→longitudinal wiring | `useICAnalysis.ts:164-165` 非 cross_sectional 時送 `mode: 'longitudinal'` | 無需改 |
| 後端單標 pipeline 存在 | `ic_analysis_service.py:209-216` 呼叫 `analyzer.analyze()` | 無需改 |
| feature_filter 幽靈 | API merge：`ic_analysis_service.py:967-970`；`ICConfig` 無此欄：`ic_config_schema.py:319-353`；`momentum/Analysis/` 內 **0** 處消費 `feature_filter` | 無需改 |
| 主 analyze 阻塞 event loop | `_run_analysis` 為 `async` 但 `:209` 直接同步 `analyzer.analyze()`，無 `to_thread`（deep 才有 `:544`） | 無需改 |
| 無 train/test | 主路徑 stage4 全樣本算 IC（orchestrator `:1105-1108`） | 建議標註雙層：**✅ 功能層 / ⚠️ 選因子正確性未過**（見下條） |

**建議改（回應綜合自問 #2）**：型 1 維持 ✅ 但加紅字副標「功能連通 ≠ 選因子可信」，避免讀者以為「沒事」。

---

### 2. 型 4「🔌/⛓️‍💥 + consistency_score 做 sign 一致性」——**大體準確，UI 連結描述需補強**

| 主張 | 證據 | 改法 |
|------|------|------|
| `_build_cross_symbol_validation` 存在且算 sign | `ic_filter_orchestrator.py:379-424`：`sign_array = np.sign(...)`；正負並存→`sign_conflict_features`；`:426-429` `sign_agreement` 進 `feature_scores`；`:441` `consistency_score = mean(feature_scores)` | 無需改 |
| 僅 cross-sectional 路徑產出 | `analyze_cross_sectional` `:298-304` 呼叫；longitudinal 無此呼叫 | 無需改 |
| 單幣模式無一致性視圖 | 單 symbol `analyze()` 不走 `analyze_cross_sectional` | 無需改 |
| XGB `CrossSymbolValidator` 孤立 | cursor 版已述；IC 主 `/analyze` 未整合 | 可保留 |
| **UI 連結比綜合寫的更斷** | `cross_symbol_validation` 會進主 report（`page.tsx:216-218`），但 `CrossSymbolValidationPanel` **只在** `deepTabVisible` 內渲染（`:750-761`）；`deepTabVisible` 需 `report.deep_analysis_enabled`（`:193`），一般 cross-sectional 主分析**不會**設此旗標 | **改**：型 4 連結欄寫明「資料在 cross-sectional report 有，但 panel 被 `deep_analysis_enabled` 門閂擋住，多數使用者看不到」——比只寫「在深度 Tab」更精準 |

Gemini 標 ✅ 全棧——綜合裁決 🔌/⛓️‍💥 **正確**。

---

### 3. 型 6「⛓️‍💥 + ❌ + event_query 語義錯位」——**準確，但漏一個靜默失效**

| 主張 | 證據 | 改法 |
|------|------|------|
| Event 模式 = query 子集 IC，非 case-control | 前端只送 `event_query`（`useICAnalysis.ts:177`）；後端轉 `event_filter`（`ic_analysis_service.py:956-961`）；stage3 在 kline 上 mask 後跑標準 IC（`ic_filter_orchestrator.py:1057-1090`） | 無需改 |
| 無顯式事件清單 / timestamps 死線 | `event_timestamps` 只 warning（`ic_analysis_service.py:964-965`）；orchestrator 硬編 `timestamps=None`（`:1070`） | 無需改 |
| 真 case-control 在別處 | `SignalDensityAnalyzer` 存在（`signal_density_analyzer.py`），IC 管線未調用 | 無需改 |
| **漏：樣本不足 fallback 全樣本** | `tier == "insufficient"` 時 `:1085-1087` `fallback=True` 並 **return 全量** `features_df` | **補入** 型 6 🛡️/🔧：「事件不足時靜默退回全樣本 IC」——Codex/Cursor 有寫，綜合漏了 |

---

### 4. 九欄錯置 / 遺漏（對照程式碼）

| 型 | 欄 | 問題 | 證據 | 改法 |
|----|-----|------|------|------|
| **2** | 🛡️ | 只寫「窗 left-closed」，**漏全段 rank PIT** | `ic_engine.py:288-291` 先對**全段** `rank(axis=0)` 再 rolling corr；Codex 明確標為 PIT 爭議 | 補：「Spearman rolling 先全樣本 rank，嚴格 PIT 應窗內 rank」 |
| **5** | 🛡️/🔧 | **`_get_time_index` 秒/毫秒 bug 歸錯型** | `_get_time_index` 僅被 `_iter_time_groups` 使用（`ic_engine.py:1007-1025`）→ **grouped IC 的 by_year/by_quarter**；cross-sectional 用 MultiIndex `groupby`（`ic_filter_orchestrator.py:224-228`），**不走** `_get_time_index` | **移至型 1/2**（grouped/regime）；型 5 刪「影響時點分組」 |
| **5** | 🛡️/🔧 | **漏 label horizon 固定** | 無 `labels_path` 時 `_append_cross_sectional_labels` 固定生成 `return_1`（`ic_analysis_service.py:1254-1258`）；與 UI horizon 多選可能不一致（Codex） | 補入型 5 🔧 |
| **5** | 🔧 | `p_value: None` | cross-sectional summary 硬寫 `"p_value": None`（`ic_filter_orchestrator.py:271`） | 可選補入 |
| **2** | 階段一結論 | **「能跑且做對：Rolling IC」過樂觀** | 預設 `include_regime_analysis=True`（`ic_config_schema.py:148`）+ kline 存在 → grouped 分支 `:1133-1139` 傳 `GroupedConfig` 給 `compute_grouped_ic`，後者 `config.get()`（`ic_engine.py:377`）→ **AttributeError**（實測 + `ic-grouped-crash-perf-ANALYSIS.md`）；rolling 雖先算完（`:1106-1108`），task **整體失敗** report 拿不到 | **改結論**：Rolling 改為「後端有實作，但預設路徑常因 grouped 崩潰而白算；且同型 1 無 OOS」 |
| **1–6** | 🛡️ | train/test 缺——綜合有寫 | 各型均有 | 無需改 |

其餘業界標準 / 資料形狀 / pool 前標準化 / case-control matching 等欄位：**未在程式路徑上逐條驗證**，但與 SCOPE-FINAL 定義一致，無明顯錯誤。

---

### 5. 階段一 6 型——有無「四家都漏」的第七型？

對照 `handoffs/20260624-ic-map-STAGE1-brief.md` 與 `SCOPE-FINAL.md`，階段一**明確定為 6 型**；其餘（分位單調、IC 顯著性/FDR、train/test、極端值診斷）在**階段二/三**。

在階段一範疇內，**不建議新增第 7 型**；但綜合應把下列**橫切項**從原文併入（四家其實有、綜合未集中寫）：

- `GroupedConfig` vs `dict` 契約崩潰（Cursor/Codex + crash handoff）
- cross-sectional `p_value: None`、label `return_1` 硬編（Codex）
- event insufficient → 全樣本 fallback（Codex/Cursor）

這些是**漏洞補充**，不是新分析類型。

---

### 6. 綜合遺漏的原始版本重要點

| 來源 | 遺漏點 | 應補位置 |
|------|--------|----------|
| **Codex** | Rolling 全段 rank PIT | 型 2 🛡️ |
| **Codex** | cross-sectional label 固定 `return_1` | 型 5 🔧 |
| **Codex** | event 不足 fallback 全樣本 | 型 6 🛡️/🔧 |
| **Codex** | `deep_analysis_enabled` 門閂導致 consistency panel 不可見 | 型 4 連結 |
| **Cursor** | `GroupedConfig.get()` 崩潰機制與預設觸發條件 | 型 2 🔧 + 階段一結論 |
| **Cursor** | 跨模組基礎設施表（grouped 崩潰、materialize OOM） | 可加「橫切」小節 |
| **Claude** | 橫截面 ✅ 是否過樂觀 | 綜合已用「小規模」處理，可接受 |
| **Gemini** | 型 1/4/6 誤判 | 綜合裁決表已修正，無需再改 |

---

### 7. 建議修改摘要（給 Claude 改綜合）

1. **階段一結論**：刪或降級「能跑且做對：Rolling IC」→ 改「有實作但預設 grouped 崩潰常致整 task 失敗 + 無 OOS」。
2. **型 2**：補全段 rank PIT；補 `GroupedConfig` 崩潰連帶白算 rolling。
3. **型 4**：連結欄補 `deep_analysis_enabled` 門閂（`page.tsx:193,750-761`）。
4. **型 5**：移除 `_get_time_index`；改放到型 1/2 grouped；補 `return_1` 硬編。
5. **型 6**：補 insufficient events fallback 全樣本（`ic_filter_orchestrator.py:1085-1087`）。
6. **型 1**：加「✅ 功能層 / ⚠️ 正確性」雙標，回應自問 #2。

---

**ASSUMPTIONS_VERIFIED（本審查）**：`_build_cross_symbol_validation` sign 邏輯、`feature_filter` 幽靈、`GroupedConfig.get` 崩潰、cross-sectional 不走 `_get_time_index`、`event_query` 語義——均已讀碼或執行 Python 驗證。  
**未驗證**：kline 實際 timestamp 為秒或毫秒（僅 handoff 宣稱 + `_get_time_index` 實作可見，未載真實 HDF5）。
