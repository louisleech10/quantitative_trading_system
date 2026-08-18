# PA-CUMSUM 小票 code review（三家全員；實作者＝Claude 主委，不自審）

VERIFY-EXEMPT:doc-example:pacumsum-review-brief-questions

> 本檔為提問清單；結論在你們的產出與收斂檔。

brief-kind: review

## 審查標的（commit `7d516540`；`git show 7d516540 --stat`）
- `momentum/Analysis/prediction_analyzer.py`：`EquityCurveData` 改為四序列（`strategy/benchmark_returns_{simple,compound}`）＋`final_return_pct` 四鍵；`calculate_strategy_equity_curve` 同時算 `cumsum` 與 `cumprod(1+r)-1`；`actual_returns` 含 NaN／inf ⇒ `ValueError`。
- `api/models/pattern_analysis_models.py::EquityCurveData`（pydantic 同步）；route `api/routes/pattern_analysis.py::get_strategy_equity` 未改（`to_dict()` 直入 model；route 已 `fillna(0)`）。
- 前端：`frontend/src/lib/patternTypes.ts`、`frontend/src/components/pattern/details/charts/NaiveStrategyEquityChart.tsx`（單利／複利切換 tab，預設複利；Y 軸／tooltip 改百分比；footer 同時顯示另一種之終值）。
- 測試：`tests/momentum/Analysis/test_prediction_analyzer_equity.py`（5 條：+50%/−50% ⇒ 單利 0%／複利 −25%、cumsum/cumprod 對照＋log 關係、閾值持倉、長度／NaN raise、to_dict 餵 API model 且無舊鍵）。
- 使用者裁決（2026-08-18）：「單利／複利兩條都算都標清楚；前端切換一起做」。出處：ROADMAP「PA-CUMSUM」／`CODEX-R8-P1-12`／`GROK-R8-P1-03`。

## 任務（段 A／B 必答）
**段 A — 正確性**：① 單利＝`cumsum(r)`（固定本金）、複利＝`cumprod(1+r)-1`（全額滾入）之對應與標籤是否正確、無混淆；② 策略持倉語意（`proba > threshold` 持倉、否則報酬 0）在複利下之意義（空手期 `1+0` 不變）是否合理；③ `final_return_pct` 百分比換算；④ 舊鍵移除是否有**其他消費者**（請 grep 全 repo 含 `frontend/`、`tests/`、`docs/`——主委 grep 只見前端一處）。
**段 B — 攻主委決定**：① 預設模式選「複利」是否合理（另一選項：預設單利以維持舊圖行為）；② `ValueError` on NaN 是否會讓既有 route 行為改變（route 已 `fillna(0)`；但 `y_pred_proba` NaN 未擋——`nan > threshold` 為 False ⇒ 空手，是否應同樣 raise？）；③ 前端 tab 之 a11y／樣式是否與同頁其他 glass-panel 一致；`ChartExportButton` filename 帶 mode；④ 是否應把「單利／複利」語意也寫進 API model 之 `Field(description=...)`（現只在 docstring）；⑤ `docs/API_SPECIFICATION.md` 因格式快閘不可編輯（摩擦六十七）——欄位說明只在 model docstring＋ROADMAP，是否足夠。
**段 C — 測試**：5 條是否可證偽（例：把 `cumprod` 改回 `cumsum` 是否至少一條紅——請實跑一次 mutation，**務必還原**）；前端無單元測試（此頁既有元件亦無）——是否要求補 `NaiveStrategyEquityChart.test.tsx`（若要求，請給最小可證偽案例：切換 tab 後顯示之 final 值不同）。

## 範本
`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` V13 之 §0／§1／§3 與 canonical 四欄。ID＝`## <FAMILY>-R23-P<0-3>-<NN>`，**本輪輪次=R23**（task-id `20260818-PACUMSUM-X-REVIEW-R23`）；零 findings 用 sentinel `## <FAMILY>-R23-P3-00`。

## 本 brief 前提（逐條標）
fact-verified: `venv/bin/python -m pytest tests/momentum/Analysis/test_prediction_analyzer_equity.py -q` → 5 passed；`python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` → BASELINE OK
fact-verified: `cd frontend && npm run build` → ✓ Compiled successfully；`npx tsc --noEmit` 8 個既有錯誤皆在無關測試檔（FactorReturnChart.test／useFeatureFactory.batchDate.test），本改動 0 錯
fact-verified: `grep -rn "final_return_pct\|strategy_returns\b" frontend/src tests` → 只剩本次改動之檔
assumed: 舊鍵無其他消費者（含 notebooks／docs 範例）← 請攻（段 A④）
assumed: 預設複利合理 ← 請攻（段 B①）
assumed: `y_pred_proba` NaN 視為空手可接受 ← 請攻（段 B②）

## ⚠️ 前置說明
禁改碼／禁 commit／禁 push；主委本輪不動工作區（`scripts/governance_families.json` 既有 no-op dirty 請忽略）。自建探針加 timeout；產出檔尾最後一行 `STATUS: DONE`。既有紅 2 條（`test_model_hyperparam_enhanced`）與本輪無關。

## 產出
Verdict（可合併／需修補後合併／不可合併）＋段 A–C 結論＋canonical findings。檔尾最後一行 `STATUS: DONE`。收尾清 /tmp workdir（保留 claude-501）。
