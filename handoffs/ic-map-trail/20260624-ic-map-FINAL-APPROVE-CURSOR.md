使用者可稽核：cat .claude/gate/audit.log
**VERDICT: CHANGES**

全圖總覽與五階段 FINAL、程式碼抽查大體一致，A–G 系統性發現與狀態標記可信度高；但有三處**事實錯誤**與兩處**重要遺漏**，未達「全圖核可」門檻。

---

### 1. 分析總數寫錯（28 ≠ 31）

**證據**：漏斗表加總為 `6+5+8+3+6=28`（`WHOLEMAP.md:11-15`），速覽實列 28 條（`:20-28`），標題卻寫「31 種分析」（`:18`）。五份 STAGE FINAL 亦為 28 型，無第 29–31 型定案。

**改法**：標題改為「28 種分析」；若堅持 31，須明列額外 3 型並對應 FINAL，目前無依據。

---

### 2. D 段將 DSR/PBO 誤併入「程式碼都在」

**證據**：`WHOLEMAP.md:49` 寫「walk-forward / purged CV / DSR / PBO … **防偽機制程式碼都在,但孤島**」。  
`STAGE3-FINAL.md:63-64` 明確：`repo無DSR/PBO/MinBTL實作` → `❌ 完全缺`。  
`grep deflated|PBO` 於 `momentum/` 無實作（僅 handoffs/archived）。

**改法**：拆成兩句——「walk-forward / purged CV **有實作但 IC 主流程未接（孤島）**」；「DSR/PBO/MinBTL **repo 完全缺**（階段③型8）」。

---

### 3. 優先級與 STAGE5-FINAL 未對齊

**證據**：
- `STAGE5-FINAL.md:39`：IC→ML 橋 → `🏷️ P0`
- `STAGE5-FINAL.md:51`：多因子組合 → `🏷️ P0`
- `WHOLEMAP.md:65` 將兩者放在「**高**」，低於「絕對優先」五項

**改法**（二選一）：
- **A**：在優先級區加「產品 P0」子段，列入 IC→ML 橋、多因子組合/邊際 IC；或
- **B**：維持現有分層，但加註「絕對優先 = 正確性紅線；產品敘事 P0 見高優先」。

---

### 4. F 段遺漏 case-control「事件不足 fallback 全樣本」（階段①型6 重要發現）

**證據**：`STAGE1-FINAL.md:57` 列為「靜默斷裂(最該警覺)」；`ic_filter_orchestrator.py:1085-1087`：

```1085:1087:momentum/Analysis/ic_filter_orchestrator.py
        if info.get("tier") == "insufficient":
            info["fallback"] = True
            return features_df, label_series, info
```

事件不足時**靜默退回全量 IC**，非 fail-closed。  
`WHOLEMAP.md:57` 只提 `event_timestamps` 死線，未提此 fallback。

**改法**：F 段補一條：「事件不足 → 靜默 fallback 全樣本 IC（主戰場隱性風險）」。

---

### 5. 橫切缺口：cross-sectional 模式大量空殼（多階段 FINAL 結論未入總覽）

**證據**：
- `STAGE2-FINAL.md:51`：分位/decay/grouped 在 cross-sectional **全回空**
- `STAGE4-FINAL.md:40`：階段四多空/turnover 在 cross-sectional **全❌**
- `STAGE1-FINAL.md:50`：橫截面本身 ✅，但其他型在該模式下斷裂

**改法**：在 A–G 加橫切項（如 **H. cross-sectional 模式空殼**），或於誠實邊界註明「除橫截面 IC 外，階段②–④多數分析在 cross-sectional 模式無輸出」。

---

## 已核可部分（抽查通過）

| 主張 | 程式碼佐證 |
|------|-----------|
| FDR 幽靈 | `adjust_multiple_comparisons` 僅 tests 呼叫；Stage5 只用 raw `p_value`（`ic_filter_orchestrator.py:1165-1175`） |
| `feature_filter` 幽靈 | API merge（`ic_analysis_service.py:967`）；`ICConfig` 無此欄（`ic_config_schema.py` grep 0） |
| `turnover.enabled` 不 gate | Stage5 無條件 `compute_all`（`:1175`） |
| `slippage_bps` 未讀 | `NetICAnalyzer` 只讀 `default_cost_bps`（`net_ic_analyzer.py:21-31`） |
| Net IC 量綱錯誤 | `net_ic = gross_ic - (cost/10000)*turnover*2`（`:34`） |
| 分位靜默空圖 | 後端巢狀 `quantile_returns.quantile_returns`；前端讀頂層 `quantile_mean_returns`（`QuantileReturnChart.tsx:13-14`） |
| grouped P0 崩潰 | Pydantic `GroupedConfig` 傳入 `config.get()` API（`ic_engine.py:377`） |
| attribution NaN 繞過 | `_run_factor_exposure` 硬填 NaN（`ic_filter_orchestrator.py:873-878`） |
| timestamp 秒當 ms | `_get_time_index` 固定 `unit="ms"`（`ic_engine.py:1025`） |

28 條狀態標記與各 STAGE FINAL 速覽表**逐型對照一致**（含階段②型5 drift、階段③型8 DSR/PBO 為後期 reconcile 新增）。

A–G 無明顯誇大；`43萬×0.05≈21,500` 為 STAGE3 共識的啟發式數字，誠實邊界已標市場假設未 live 驗證。

---

**結論**：修正上述 5 點（至少 1–3 為必改）後可再送核可。本次 READ-ONLY，未改檔。

`HANDOFF_NOT_UPDATED: 使用者要求 READ-ONLY 最終核可，非執行端派工`
