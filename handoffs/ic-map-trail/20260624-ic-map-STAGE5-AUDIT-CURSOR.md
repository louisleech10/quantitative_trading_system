使用者可稽核：cat .claude/gate/audit.log
## VERDICT: **CHANGES**

五項待查核心主張**讀碼後均屬實**；綜合版整體方向與 codex/cursor 一致，優於 Claude/Gemini Round 1。但仍有**可稽核遺漏**與**一處精度問題**，不宜直接 APPROVE。

---

### 1. 型1：`max_features=200` 死配置、前端 18 列、Stage4 前置 rolling IC

**判定：屬實**

| 子項 | 證據 | 改法 |
|------|------|------|
| `max_features_for_correlation=200` 未接線 | 全 `momentum/` 僅 `ic_config_schema.py:155-156` 定義；`_stage6_redundancy` 直接 `features_df[passed_features]` 全量進 `RedundancyFilter`，無 cap（`ic_filter_orchestrator.py:1224-1229`） | Stage 4/6 讀 `config.performance.max_features_for_correlation` 並在 report 標 `truncated` |
| 前端熱圖硬裁 18 列 | `CorrelationHeatmap.tsx:21` `maxFeatures = 18`；`:25-27` slice | 文件可保留；產品上應標「Top 18 預覽」或接 paginate |
| Stage4 對全欄算 rolling IC | `_stage4_ic_calculation` 對完整 `features_df` 呼叫 `compute_rolling_ic`（`:1105-1108`）；`ic_engine.py:268-302` 對全欄 `rank` + `_rolling_corr_matrix` | 前置 candidate cap / L7 group IC 路徑需寫進型1「前置災難」 |
| API `feature_filter.max_features` 幽靈 | API merge 進 override（`ic_analysis_service.py:967-970`），但 `ICConfig` 無 `feature_filter` 欄（`ic_config_schema.py:319-353`），Pydantic 靜默忽略 | 綜合已寫 ✅；可補：前端 `page.tsx:156-161` 的 max_features **僅 UI 篩選**，非後端防線 |

**430K O(C²) 數字**：430K² ≈ 1.85×10¹¹ floats — 算法描述正確。

---

### 2. 型2：「Neutralized IC」誤稱、ShapleyConfig 死配置

**判定：屬實**

| 子項 | 證據 | 改法 |
|------|------|------|
| 正交化只出 transform summary | `_run_factor_orthogonalization` 回傳 `summary` + `transformed_shape`（`:817-835`）；`factor_orthogonalizer.py:68-75` 為 corr before/after，**無 label 殘差 IC** | 型2標題改「正交化 / Residual IC（缺）」；勿混 net_ic / exposure 中性化 |
| 無真 Neutralized IC 模組 | `grep residual_ic/neutralized.*ic` 在 `momentum/` 無 IC 計算實作 | 新模組規格需獨立 |
| ShapleyConfig 死配置 | `ic_config_schema.py:268-271,352`；`ic_filter_orchestrator.py` 無 `shapley` 引用 | 刪除或接 runner；文件標 P2 未落地 |
| PIT（全樣本 QR/PCA） | deep 用 `_ic_cache["features_df"]` 全窗 fit（`:820-831`） | 綜合描述 ✅ |

---

### 3. 型5：attribution 空、positions 等權、`market_proxy=label`

**判定：屬實（但 positions 描述可更精）**

| 子項 | 證據 | 改法 |
|------|------|------|
| attribution 硬編 NaN | `_run_factor_exposure` `:873-883` 硬填 `alpha/r_squared/attribution` 為 `np.nan`/`{}`；**未呼叫** `calculate_factor_attribution`（`factor_exposure_analyzer.py:104+` 有完整實作） | 接 `portfolio_returns` + 真 `factor_returns` |
| `market_proxy=label` | `:842` `market_proxy = label_series` | UI 標「label proxy 診斷」 |
| positions 非真持倉 | `:843` `1.0/len(factor_values)` — **`len(DataFrame)`=列數 T**，非特徵數 C；每時間點等權 1/T | **綜合遺漏**：應寫「positions 用 `len(rows)` 常數權重，非因子權重也非策略持倉」；Cursor 標 P0，綜合標 P1 偏低 |
| Gemini「實作正確」 | `STAGE5-GEMINI.md:74` 與碼不符 | 綜合已糾正 ✅ |

---

### 4. 型4：SHAP 有實作、IC 主流程無 ML、無 IC→ML 橋

**判定：屬實**

| 子項 | 證據 | 改法 |
|------|------|------|
| SHAP 已實作 | `shap_analyzer.py`；`xgboost_batch_service.py:894-895`；`shap_analysis_service.py:122` | — |
| IC 主流程無 ML/SHAP | `ic_filter_orchestrator.py` 無 xgboost/lightgbm/shap import/呼叫 | — |
| IC 頁無 ML 區塊 | `frontend/src/app/ic-analysis/` grep ML/SHAP → 0 | — |
| **精度問題** | 綜合寫 `max_shap_samples=200`；實際 **多預設**：batch service **200**（`xgboost_batch_service.py:894`），`shap_analyzer.py:103` / `xgboost_analyzer.py:1255` 預設 **100** | 改寫「SHAP 取樣 100–200（路徑依賴）」 |

---

### 5. 型6：IC 加權多因子組合真缺

**判定：屬實**

| 子項 | 證據 | 改法 |
|------|------|------|
| IC 管線無 composite | `ic_weight`/`composite_ic` 在 `momentum/` 無 pipeline | 新增 composite evaluator |
| 鄰近非等同 | `trend_analyzer.py:110` `combined_signal` 為診斷建議；`sample_weight` 為樣本權重 | 綜合已區分 ✅ |
| Gemini「架構選擇非缺口」 | `STAGE5-GEMINI.md:89` | 綜合標 ❌ P0 合理；**建議加一句反駁** Gemini（產品地圖仍缺閉環） |

---

### 6. 階段五 6 型是否該加？

**判定：現有 6 型足夠；綜合未答「是否擴型」**

Claude R1（`:42-44`）與 Cursor（`:128`）建議候選：
- marginal IC increment（加/減因子對組合 IC 的 Δ）
- regime-conditional redundancy

**改法**：在「待委員檢查」或結論加「**不擴表為第 7 型**；上述併入型 1/6 的 🔧 或 P2 backlog」。

---

### 7. 9 欄業界標準 / 洩漏：量化錯誤？

**未見重大量化錯誤**；下列為可補強點：

| 項目 | 評估 |
|------|------|
| 型1 O(C²)/O(C³)、430K corr 記憶體 | ✅ |
| 型3 在 IC 空間非特徵空間 PCA | ✅（`ic_filter_orchestrator.py:758-771`） |
| 型6 walk-forward 權重防洩漏 | ✅（未實作前的正確做法） |
| 型4 purge/embargo「每路徑強制」 | 綜合已標「待驗」— **未驗證** |
| 型1「cross-sectional symbol 隔離」 | Cursor 有寫；綜合略 — **非錯，略簡** |

---

### 8. 綜合相對四家原始版的重要遺漏

| 遺漏 | 來源 | 嚴重度 |
|------|------|--------|
| **deep 無 `selected_features` 時 fallback 至 `_ic_cache["features_df"].columns` 全欄** | Codex `:22-23`；碼 `:589-594` | **高** — 430K deep 風險 |
| positions `len(rows)` 維度 bug 細節 | Cursor `:95,169` | 中 |
| 前端 `max_features` 僅 UI、API 可繞過 | Codex 型1 尺度欄 | 中 |
| 候選擴型（marginal IC、regime redundancy） | Claude R1 / Cursor | 低 |
| Gemini 型5/型6 與碼矛盾之反駁 | Gemini | 低（綜合方向已對，未明示） |
| mermaid 接線圖 | Cursor | 低（可選） |

---

### 總結

| 待查項 | 結果 |
|--------|------|
| 1–6 核心主張 | **全部屬實**（型4 SHAP 取樣數需修正表述） |
| 6 型是否該加 | **不必加第 7 型**；應回覆候選擴展 |
| 9 欄量化 | **無致命錯** |
| 綜合完整性 | **有遺漏** → CHANGES |

**最小修訂清單（給 Claude 改 SYNTHESIS）：**
1. 型1/深模組補 `run_deep_analysis` 全欄 fallback（`:589-594`）。
2. 型5 補 positions `len(rows)` bug；priority 與 Cursor 對齊或註明降級理由。
3. 型4 修正 SHAP sample 100 vs 200。
4. 結論加「不擴第 7 型 + 候選 backlog」。
5. 一句反駁 Gemini「composite IC 為架構選擇」。
