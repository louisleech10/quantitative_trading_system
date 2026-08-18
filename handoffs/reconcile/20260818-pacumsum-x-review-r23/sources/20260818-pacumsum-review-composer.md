# PA-CUMSUM 小票 code review R23（COMPOSER）

**審查者**：COMPOSER | **task-id**：`20260818-PACUMSUM-X-REVIEW-R23` | **標的 commit**：`7d516540` | **日期**：2026-08-18

---

## Verdict：可合併

單利／複利公式、標籤、前後端契約與 5 條後端測試對齊使用者 2026-08-18 裁定；舊鍵在 runtime 路徑無殘留消費者。合併前建議補一處文件化（P2-01：`y_pred_proba` NaN 與 `actual_returns` NaN 政策不對稱），非阻擋。

---

## 被當成事實的未驗證假設（§0）

| 假設 | 判定 | 說明 |
|---|---|---|
| 5 條 pytest 全綠 | **fact-verified** | `venv/bin/python -m pytest tests/momentum/Analysis/test_prediction_analyzer_equity.py -q` → 5 passed |
| 舊鍵無其他消費者 | **fact-verified（本輪攻）** | `rg` 限 `*.{py,ts,tsx}`：runtime 僅新四序列鍵；舊 `strategy_returns`／`benchmark_returns`／`final_return_pct.strategy` 僅 archived docs／註解（`docs/Archived/*`、`docs/IC1D_ATTRIBUTION_SPEC.md` 敘述性引用） |
| 預設複利合理 | **fact-verified（使用者裁決）** | BRIEF／commit message／`NaiveStrategyEquityChart` `defaultMode='compound'` 一致 |
| `y_pred_proba` NaN 視為空手可接受 | **部分推翻** | 數學上保守合理，但與 `actual_returns` 嚴格 `ValueError` 不對稱 → P2-01 |
| mutation 可證偽 | **fact-verified（模擬）** | 將 compound 分支 `cumprod`→`cumsum` 之 oracle 模擬：hand_case／generic／threshold 三條皆會紅（見段 C） |

---

## 段 A — 正確性

| # | 項目 | 結論 |
|---|---|---|
| A① | 單利 `cumsum`／複利 `cumprod(1+r)-1` 與標籤 | **PASS** — `prediction_analyzer.py:173-178` 實装；`EquityCurveData`／API model／`patternTypes.ts`／`MODE_LABEL` 皆標 `simple`／`compound`；前端 tab 與 legend 帶模式名 |
| A② | 閾值持倉在複利下語意 | **PASS** — `strategy_positions=(proba>threshold)`；空手期 `strategy_returns=0` ⇒ `1+0` 不變，符合全倉／空手切換之複利淨值語意；`test_threshold_gates_positions_and_benchmark_ignores_it` 手算對照 |
| A③ | `final_return_pct` 百分比 | **PASS** — `_final_pct` 取曲線末值（小數累積報酬）×100；圖表 Y 軸 `pct(v)=v*100` 與 footer 直接用 `final_return_pct.*`（已是 %）一致 |
| A④ | 舊鍵其他消費者 | **PASS（runtime 無）** — `frontend/`、`tests/`、`api/`、`momentum/` 無舊 schema 讀取；`test_phase2_integration.py::test_invalid_strategy_returns_404` 為 HTTP 404 語意，非欄位名 |

---

## 段 B — 攻主委決定

| # | 項目 | 結論 |
|---|---|---|
| B① | 預設複利 | **接受** — 使用者明確裁定；複利＝帳戶淨值變化，作為預設展示合理；舊圖為無標籤單利 cumsum，屬契約修正非回歸 |
| B② | `ValueError` on NaN／route 行為 | **見 P2-01** — route `actual_return.fillna(0)`（`:1050`）故既有路徑不因新 gate 爆；`y_pred_proba` 未 `fillna`，NaN⇒`nan>thr` 為 False⇒靜默空手 |
| B③ | 前端 a11y／樣式／export | **PASS（小缺可選）** — `role="tablist"`／`role="tab"`／`aria-selected`／`aria-label` 已有；tab 在 `MonitoringTab` 之 `glass-panel` 內與同頁 `RollingAUCChart` 一致；`ChartExportButton` filename=`strategy_equity_${mode}` ✓；可選補 `aria-controls`＋panel `id`（非阻擋） |
| B④ | API `Field(description=...)` | **MINOR 建議** — 語意已在 class docstring＋TS JSDoc；OpenAPI 自動生成缺 per-field 說明，可後續小補，不阻擋本票 |
| B⑤ | `API_SPECIFICATION.md` 不可編輯 | **可接受** — ROADMAP 追記＋三處 model docstring／TS 註解已足本小票；registry 級 API 文件債另開 |

---

## 段 C — 測試

| 項目 | 結論 |
|---|---|
| 5 條可證偽性 | **PASS** — 本輪以 in-process oracle 模擬 mutation（`cumprod`→`cumsum` on compound paths）：`test_hand_case_plus50_minus50_*`、`test_compound_equals_cumprod_*`、`test_threshold_gates_*` 必紅；未改工作區檔（沙箱拒絕 PYTHONPATH 覆寫實跑，見 `MUTATION_SIM` 輸出） |
| 前端單元測試 | **不要求阻擋** — `MonitoringTab` 同頁 `RollingAUCChart`／`RegimeRadarChart` 亦無 `.test.tsx`；若補測，最小案例：mock `EquityCurveData` 含 divergent `final_return_pct.strategy_simple` vs `strategy_compound`，click tab 後 footer 數字切換 |

---

## COMPOSER-R23-P2-01

**斷言**：`calculate_strategy_equity_curve` 對 `actual_returns` 含 NaN／inf 嚴格 `ValueError`，但 `y_pred_proba` 含 NaN 時靜默視為空手（`nan > threshold` ⇒ False），route 亦未 `fillna` proba，資料品質政策不對稱且未在 docstring 明示。

**碼證**：
1. 嚴格分支：`prediction_analyzer.py:167-168` `if not np.all(np.isfinite(actual_returns)): raise ValueError(...)`。
2. 寬鬆分支：`strategy_positions = (y_pred_proba > threshold)`（`:170`）；NaN 比較為 False。
3. VERIFY：`venv/bin/python -c "import numpy as np; print((np.array([0.9,float('nan'),0.9])>0.75).astype(float))"` → `[1. 0. 1.]`。
4. Route：`pattern_analysis.py:1049-1050` 僅 `actual_return.fillna(0)`，`predicted_proba` 原樣傳入。
5. RECHECK：對含 NaN proba 的 `predictions_df` 呼叫 endpoint，觀察是否靜默降倉而非 4xx。

**來源摘要**：momentum/Analysis/prediction_analyzer.py#60defe07cff8

[MINOR] 信心度=Medium。失敗模式：上游 proba 缺值被靜默當「不交易」，與報酬缺值 fail-closed 不一致，審計時易誤解。修法（擇一）：docstring 明示 NaN proba⇒空手；或對 `y_pred_proba` 同樣 `isfinite` gate；或 route `fillna`＋文件化。非數值錯誤，不阻擋合併。

---

## §1 必查（11 類）

1. **矛盾/互斥**：有（NaN 政策 — P2-01）；公式／標籤無矛盾
2. **漏項/端到端**：無阻擋性漏項
3. **不可測驗收**：無
4. **可疑 quant 假設**：無（兩種累積假設皆正確標示）
5. **過度工程**：無
6. **OOM/並行**：不適用
7. **Cache 正確性**：不適用
8. **API/型別/相容**：舊鍵破壞性變更已同步唯一前端消費者；無其他 runtime 消費者
9. **測試品質**：後端 PASS；NaN proba 路徑未測（隨 P2-01 可選補）
10. **Agent 可執行性**：N/A（code review）
11. **必要性/短命工**：無

## §2 範本錨點

本輪審實作 commit — **不適用** SPEC/TODO 獵空殼。

---

ASSUMPTIONS_VERIFIED: 公式對照 `prediction_analyzer.py:173-178`；舊鍵 `rg` 全 repo；NaN proba 行為實跑；5 pytest 實跑；mutation oracle 模擬
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/test_prediction_analyzer_equity.py -q` → 5 passed；mutation oracle `venv/bin/python -c "..."` → hand_case_fail=True generic_fail=True threshold_fail=True
FAILURES_SEEN: none（審查未改碼）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）
產出檔: handoffs/20260818-pacumsum-review-composer.md
HANDOFF_NOT_UPDATED: 執行端合約 — 根 HANDOFF.md 由 Claude 維護
/tmp cleanup: 已刪 `pacumsum-composer-review-*`；保留 `claude-501`

STATUS: DONE
