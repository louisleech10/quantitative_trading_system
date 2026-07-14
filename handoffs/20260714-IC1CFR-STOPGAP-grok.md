# IC1CFR-STOPGAP SPEC adversarial — Grok(2026-07-14)

**task-id**: IC1CFR-STOPGAP:adversarial  
**角色**: 審查委員(grok)  
**對象**: `docs/IC1CFR_STOPGAP_SPEC.md` v0.1 draft  
**模式**: 唯讀(僅本檔寫入)  
**背景**: necessity 委員會 grok 曾記「deep FR 錯位有限值」隱憂;本票止血。

---

## 方法(可重現)

| 步 | 證據 |
|----|------|
| 讀 SPEC+NECESSITY-RECONCILE+自寫 necessity | 文件 |
| 全棧 rg | `factor_return`/`long_short_mean_return`/`ls_cumulative`/`FactorReturnChart` |
| 讀碼 | `factor_return_analyzer.py`、`long_short_analyzer.py`、`ic_reporter.py`、`ic_filter_orchestrator._run_factor_return`/`force_modules`、`api/models/ic_models.py`、`ic_analysis_service._build_deep_module_override`、前端 chart/store/types |
| 核對 FACT 行號 | `sed -n '170,195p' ic_config_schema.py` |

---

## ① 下架面完整性(獨立 consumer-map)

### 確認有毒/活輸出(錯位 LS 路徑)

| # | 消費者 | 路徑/行(本輪) | SPEC §C? | 註 |
|---|--------|---------------|----------|-----|
| C1 | 計算源 | `factor_return_analyzer.py:70-101` `reset_index` 後 LS | 不動本體✓ | 有限 `long_short_mean_return`/`risk_metrics`/`ls_cumulative_sampled` |
| C2 | deep runner | `ic_filter_orchestrator.py:1779-1785` `_run_factor_return`→`compute_batch` | 有(佔位) | 止血主閘應在此 |
| C3 | schema 預設 | `FactorReturnConfig.enabled=True` **:173** | 有但誤標:193 | 見 B1 |
| C4 | reporter deep summary | `ic_reporter.py:139-141,579-591` 三欄 | 有 | `sharpe` 鍵名與 analyzer `sharpe_ratio` 已錯位→sharpe 欄可能本來就空;ls_mean/max_drawdown 仍可活 |
| C5 | detailed CSV / export_all | `generate_detailed_csv`+`export_all` flatten 全樹 | **缺** | 有限值整包進 CSV/JSON |
| C6 | AI JSON | `generate_ai_json`→`_build_module_summaries(deep_payload)` | **缺**(名面) | 現為 keys/size 摘要;佔位後可接受,但須明列「禁再把 LS 有限值塞進 module_summaries」 |
| C7 | 全量 report JSON | `_serialize_deep_analysis` inject `factor_returns` | **缺** | API/WS 主載體 |
| C8 | 前端圖 | `page.tsx:800` `FactorReturnChart`←`deepAnalysisReport.factor_returns` | 有 | **圖資料主鍵= `quantile_returns_summary`**,非 LS mean(見 B3) |
| C9 | types | `types.ts:2231-2240` | 有 | 缺 unavailable 聯合型 |
| C10 | API 模組預設 | `api/models/ic_models.py:22` `DeepAnalysisModules.factor_return=True` | **缺** | 與「預設關閉」衝突 |
| C11 | 前端 preset/default | `icAnalysisStore.ts:107,133,150-151` intermediate/advanced/`defaultDeepAnalysisModules` 皆 true | **缺** | 同上 |
| C12 | service 組 override | `ic_analysis_service.py:1141` typed `factor_return.enabled←modules.factor_return` | **缺** | 把 C10/C11 打進 config |
| C13 | 測試/fixture 有限值 | `test_export_formats.py`/`test_export_api.py`/`phase26` | §V 有 grep 表 | 須改寫表 |
| C14 | factory 直呼 | `factories.create_factor_return_analyzer` | 界外可接受 | 單元仍可產錯值;止血流應在 deep 出口 |

### 誤標/非本毒

| 項 | 裁定 |
|----|------|
| SPEC FACT `:193`「預設模組清單」 | **假**。`:193`=`TrendAnalysisConfig.dimensions` 含字串 `"factor_return"`(維度名),**不是** deep 模組 enabled 清單。真正 `enabled=True` 在 **:173**。 |
| `FactorEquityCurveChart`(:791) | 吃 `report.quantile_returns`(主鏈 monotonicity 分位曲線),**不是** deep `factor_returns`。與 LS 錯位不同源;不應當 FR 下架唯一目標,也勿誤刪。 |
| `long_short_spread`(主篩/CSV base) | 來自 quantile 主鏈,非 Module1 LS series。 |

**完整性結論**:出口止血若 **runner 恒佔位** 可覆蓋 C2→C8 主路徑;但 §C 漏 C5/C7/C10–C12,且 FACT/Task1.1 指向錯誤行號——執行端極易改 dimensions 而非 enabled(見 B1)。

---

## ② 預設關閉 vs 顯式開啟 — 語意漏洞

### 實際開啟圖(現況)

```
UI preset / defaultDeepAnalysisModules.factor_return=true
  → API DeepAnalysisModules.factor_return=True (model default)
    → _build_deep_module_override → factor_return.enabled=true
      → _is_module_enabled("factor_returns") 
        → _run_factor_return → compute_batch → 有限錯值
```

另路:`request.config_override` / `deep_analysis_config.config_override` deep_merge;**無**類似 net_ic 的 `factor_return` 整節 reject。  
`force_modules`:runner 鍵名是 **`factor_returns`(複數)**;若傳 `factor_return` 可能不命中——SPEC 寫 force_modules 未釘鍵名。

### SPEC 雙閘意圖

- 預設 `enabled=False`+清單移除  
- **顯式開仍佔位**(Task 1.1 邊界①②)

→ 若 **runner 閘必做**,則 config_override / API true **無法**繞回舊有限 LS 輸出。語意正確。

### 漏洞(SPEC 內)

1. **「預設關閉」寫不全**:只動 schema、不動 API/前端 default → 執行後 UI 仍勾選、模組仍跑(只是佔位)。非數值洞,但是產品語意「預設關閉」假象+浪費算力;consumer-map 應列 C10–C12 並裁決:要改 default 還是接受「仍跑、只佔位」。  
2. **M1 與雙閘矛盾**(B2):若顯式 enabled 仍佔位,「恢復預設 enabled」**不應**使 stopgap 測試變紅。  
3. Analyzer 本體未閘:測試/腳本直呼仍可得有限錯值——可接受(1c-FR-FULL),但 RESULT 須聲明 **deep 出口契約** 為止血邊界,非「全樹無有限 LS」。

**裁定**:雙閘設計方向正確;洞在 mutation 定義與 default 面清單,非「override 一定能繞過」——**前提是 runner 佔位為硬需求且有 red-on-break**。

---

## ③ §G 隔離 golden

### 優點

- 真 kline fixture 路徑存在(`tests/fixtures/ic_api_real_kline.py`)  
- 語意「只下架該下架」正確  
- 禁合成

### 抓不住 / 假紅風險

| 問題 | 嚴重度 |
|------|--------|
| 「其他模組 byte 級等值」未排除 `total_execution_time_s`、`generated_at`、可能的 progress/meta | **必假紅**或逼假綠(放寬無文件) |
| `module_summary`/`completed_count` 在 FR 由 completed→unavailable/skipped 時會變——屬 scope 副作用,應 allowlist 說明,勿塞進「非 scope 漂移=FAIL」 | 假紅 |
| §G 禁值只列 `long_short_mean_return`/`sharpe`/`ls_cumulative` | **漏網**:`quantile_returns_summary`、`risk_metrics.*`(`sharpe_ratio`/`sortino`/`annualized_return`…)、`cumulative_returns_sampled`、`ls_cumulative_sampled` 命名變體。前端 **FactorReturnChart 只畫 Q summary**——即使 LS 三欄沒了仍可畫有限 Q 收益 |
| 與 Task1.1「整模組佔位」不一致:佔位應使 **任意有限數值葉** 失敗,而非三鍵黑名單 | 假綠 |
| mutation 綁「恢復預設 enabled→②必紅」同 B2 不可證偽 | 假綠 |

**裁定**:§G 方向對,但比較範圍+denylist 未釘死 → **不能**宣稱「非 scope 漂移可證偽抓穩」。

---

## ④ long_short_analysis 同病裁定(讀碼)

**檔**:`momentum/Analysis/long_short_analyzer.py`

- 先 `concat(feature, future_returns).dropna()` 對齊時間(L33-36)。  
- long/short 用 **同一 index 上的 mask** 取子集(L60-65),**無** `reset_index(drop=True)` 後跨組位置相減。  
- 輸出=兩側各自 mean/IC/hit/sharpe + asymmetry/recommendation,是 **分側不對稱診斷**,不是 high[i]-low[i] 假 L-S 組合序列。

**裁決:不同病(NOT same disease)。**  
不納入本 STOPGAP scope。若日後要審「分位組合可交易語意」屬另一物件,勿與錯位 LS 混票。

---

## ⑤ mutation M1–M3 可證偽性

| ID | SPEC 定義 | 可證偽? | 問題 |
|----|-----------|---------|------|
| M1 | 恢復模組預設 enabled→`test_factor_return_stopgap_unavailable` 紅 | **否** | 與 Task1.1「顯式開仍佔位」互斥;預設 true 仍應綠 |
| M2 | reporter 恢復直讀→export 紅 | **條件可** | 僅當 probe **注入**有限 `factor_returns` fixture 且規格要求 reporter  fortify;若只 runner 閘、payload 已無有限值,恢復直讀仍綠(假安全)。應寫:「fixture 含有限 LS + reporter 未 scrub→紅」或「runner 恢復 compute_batch→e2e 紅」 |
| M3 | 前端畫 legacy 有限值→vitest 紅 | **是** | 與 Task2.1「缺 status=legacy→警示不畫」對得上;建議明示資料形=無 status 但有 `quantile_returns_summary`/`long_short_mean_return` 有限值 |

**正確 M1 建議**(供修 SPEC,非命令):  
`_run_factor_return` 改回 `compute_batch` 直出 / 去掉佔位 → `test_factor_return_stopgap_unavailable` 紅。

---

## BLOCKING findings

### B1 — FACT/Task1.1 錯誤編輯目標 `:193`
- **證據**:`ic_config_schema.py:172-173` `FactorReturnConfig.enabled=True`;`:192-194` 是 trend `dimensions` 含 `"factor_return"` 字串。  
- **危害**:執行端「依 SPEC 改 :193」會動 trend 維度、**不**關 FR 模組。  
- **修法**:FACT 改指 `:173`;Task1.1 刪「:193 預設清單移除」或改為可選:trend dimensions 是否剔除 FR 維度=另決策(且須證明 trend runner 真吃該維度資料源)。

### B2 — M1 與「顯式開啟仍佔位」邏輯互斥
- **危害**:mutation probe 無法證偽 runner 閘;假綠或誤導。  
- **修法**:M1=恢復 runner 計算出口(或繞過佔位呼叫 analyzer)必紅;另加 **M1b**(建議):`config_override.factor_return.enabled=true` + API modules true → 仍無有限葉。

### B3 — §G denylist 窄於 UI 實畫路徑 + 非整模組佔位
- **證據**:`FactorReturnChart.tsx:16-20` 只讀 `quantile_returns_summary`。  
- **危害**:只 null 三 LS 欄仍可對使用者展示有限 Q 收益圖;與「錯位因子報酬輸出止血/整模組 unavailable」不一致。  
- **修法**:§G②=佔位形狀 **且** 遞迴無有限 numeric leaf(allowlist 僅 status/reason 字串);或明確降級 scope=「僅 LS 有限值」並改 Task2.1 圖行為——二者擇一寫死。

### B4 — §G「他模組 byte 等值」未排除時間/計數 meta
- **危害**:`total_execution_time_s` 等必漂→閘失效或被迫人工放行。  
- **修法**:比對鍵集合=各 `results[module]` 本體(排序 dump);排除 `total_execution_time_s`/`generated_at`/壁鐘;`module_summary.factor_returns` 狀態變化列 scope-expected。

---

## NON-BLOCKING

- N1: §C 漏 AI JSON/export_all/report inject——若 B3 整模組佔位+runner 閘落地可吸收;仍應補 map 防漏測。  
- N2: reporter `risk_metrics.sharpe` vs `sharpe_ratio` 鍵漂移——止血後仍建議對齊或測 null 契約。  
- N3: `force_modules` 鍵名 `factor_returns` vs `factor_return` 文件化。  
- N4: long_short_analysis **不同病**,維持 scope 外(本輪裁定)。  
- N5: FactorEquityCurveChart 非 deep FR 消費者,SPEC 觸點表述易誤導,改寫即可。

---

## 總評

止血方向與 necessity/使用者定案一致;雙閘(關預設+顯式仍佔位)是對的 fail-close 形。  
**不可 APPROVE**:錯誤行號會導致改錯碼;mutation/§G 現寫法抓不住「runner 仍出有限值」與「圖仍畫 Q summary」,也抓不穩非 scope 漂移。

```
ASSUMPTIONS_VERIFIED: FR reset_index LS 錯位;schema enabled@173 非193;API/前端 default true;runner 直 compute_batch;reporter 三欄;FactorReturnChart 吃 quantile_returns_summary;L/S analyzer 無位置相減;AI JSON module_summaries 間接
TESTS_RUN: 靜態讀碼+rg+sed 行號核對(未跑 pytest;審查票)
FAILURES_SEEN: none
SCOPE_CHANGES: none(唯讀+本產出)
NUMERIC_OR_SCHEMA_IMPACT: none
```

SPEC-REVIEW: REJECT(4 BLOCKING)
