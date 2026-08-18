# Reconcile — 20260818-pacumsum-x-review-r23

**來源** 20260818-pacumsum-review-codex.md, 20260818-pacumsum-review-composer.md, 20260818-pacumsum-review-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18；PA-CUMSUM 小票 code review → 修補 commit）

三家共 **7 條** canonical ID（codex 3／composer 1／grok 3）；下列 **三群集 Q1–Q3 引用全部 7 條，0 掉項**。
Verdict：codex「需修補後合併」（兩條 MAJOR）vs composer／grok「可合併」⇒ **取較嚴＝需修補後合併**，全部本輪修。
主委 brief 三條 assumed：①「舊鍵無其他消費者」**部分推翻**（runtime 無，但 ROADMAP:72-74／IC1D_ATTRIBUTION_SPEC:281 文字仍寫舊鍵）；
②「預設複利合理」三家未反對；③「proba NaN 視為空手可接受」**推翻**（三家皆指與 actual_returns fail-closed 不對稱）。

### Q1 — 多標的批次被當同一帳戶連乘（無定義之組合）
**引用**: CODEX-R23-P1-01

codex 實查：`xgboost_batch_service` 支援多 symbol 且 route 把整欄送入 ⇒ `cumprod` 跨 symbol 連乘（同一 timestamp 兩 symbol `[+10%,−10%]` 得 −1%）；預設複利放大此病；「不可只在前端改標籤」。
**處置（修）**：`calculate_strategy_equity_curve` 新增 `symbols` 參數；>1 相異 symbol ⇒ **逐 timestamp 等權組合**（各 symbol 之持倉×報酬取平均、基準取平均，再單利／複利），
輸出 timestamps 去重升冪，`n_symbols`／`aggregation="equal_weight_by_timestamp"` 可觀測；單一序列 `"single_series"`。route 傳 `symbol` 欄；API model／TS 型別同步；前端多標的顯示註記「N 個標的，逐時間點等權組合（非單一帳戶連乘）」。
回歸鎖：`test_multi_symbol_uses_equal_weight_by_timestamp_not_single_account_compounding`（[+10%,−10%] ⇒ 0%，非 −1%）、`test_multi_symbol_positions_are_per_row_before_aggregation`、`test_single_symbol_column_keeps_row_series`。
誠實邊界：等權逐時間點再平衡是**一種**明確定義之組合，非唯一；權重／分組契約若日後另定，本欄位 `aggregation` 即擴充點。

### Q2 — `y_pred_proba` NaN／inf 靜默當空手（與 actual_returns fail-closed 不對稱）
**引用**: CODEX-R23-P1-02, COMPOSER-R23-P2-01, GROK-R23-P3-01

**處置（修）**：引擎對 `y_pred_proba` 同樣 `isfinite` gate ⇒ `ValueError`；route 先驗 `predicted_proba.isna().any()` ⇒ 400，並包 `except ValueError ⇒ 400`（資料錯誤明確 4xx，不吞）。
`actual_return.fillna(0)` 維持既有（route 層既有行為；ROADMAP 殘餘具名）。回歸鎖：`test_proba_nan_or_inf_raises_not_silent_flat`。

### Q3 — 公開契約不完整：`final_return_pct` 裸 Dict、無 Field description、active docs 仍寫舊鍵、commit subject 與 diff 不符
**引用**: CODEX-R23-P2-03, GROK-R23-P2-01, GROK-R23-P3-02

**處置（修）**：`EquityFinalReturnPct(BaseModel)` 四必填 float 子模型；`EquityCurveData` 每欄 `Field(description=…)`、`aggregation` 為 `Literal` 封閉；
ROADMAP:72-74 改寫為已完成＋殘餘；`docs/API_SPECIFICATION.md` 因格式快閘不可編輯（摩擦六十七）— 欄位契約以 pydantic schema 為準；`docs/IC1D_ATTRIBUTION_SPEC.md:281` 為歷史紀錄（v0.1 更正段）不動；
commit `7d516540` subject「API_SPECIFICATION 10.8 補欄位」與 diff 不符（該檔 amend 時撤回）— 具名承認，後續 commit 訊息更正。
回歸鎖：`test_api_model_final_return_pct_is_closed_four_keys`（缺鍵／舊鍵／非法 aggregation ⇒ ValidationError；每欄有 description）。
另（codex 建議、非 finding）：tab a11y 補 `aria-controls`／`tabpanel`／方向鍵；新增 `NaiveStrategyEquityChart.test.tsx`（預設複利終值 −25%、點單利 0%、方向鍵、多標的註記）4 passed。

**Verdict**: 需修補後合併 → 修補於本 commit；三家戳記後收案。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R23-P1-01
**斷言**: 多標的 batch 的所有 symbol 報酬會被當成同一帳戶連乘，compound equity 數字因此可正常回傳但不代表任何有定義的組合。
**碼證**: `xgboost_batch_service.py:223-248,599-658,1005-1008` 明確支援多 symbol 且保留 per-row symbols；`pattern_analysis.py:1047-1051` 將整欄送入；`prediction_analyzer.py:177` 對整欄 `np.cumprod`。RECHECK: 同一 timestamp 兩 symbol `[+10%,-10%]` 的結果會是 `-1%`，但 API 沒有權重/分組契約。
**來源摘要**: momentum/Analysis/prediction_analyzer.py#60defe07cff8
[MAJOR] 信心度=High；跨資產 row 順序和 symbol 邊界被吞掉，預設複利會污染多標的績效。修法是只允許單 symbol，或回傳 per-symbol／明確權重的 portfolio schema；不可只在前端改標籤。
## CODEX-R23-P1-02
**斷言**: `y_pred_proba` 含 NaN 時目前被無聲轉成空手，會把缺失預測當成低於 threshold 並改變績效。
**碼證**: `prediction_analyzer.py:168-170` 只有 `y_pred_proba > threshold`、沒有 finite gate；VERIFY: `venv/bin/python -c ...` → `[0.0, 0.2] [0.0, 0.2]`，NaN row 未 raise。RECHECK: 將第一個 proba 改為 NaN，應先拒絕而非輸出零報酬。
**來源摘要**: momentum/Analysis/prediction_analyzer.py#60defe07cff8
[MAJOR] 信心度=High；這是靜默資料品質錯誤，且新 actual-return gate 並未涵蓋 prediction gate。修法是 `np.isfinite(y_pred_proba)` fail-closed，route 將資料錯誤轉為明確 4xx；另決定 actual-return `fillna(0)` 是否仍允許。
## CODEX-R23-P2-03
**斷言**: 新 API 欄位的公開契約仍不完整且 active roadmap 自相矛盾，消費者可依舊鍵或不明語意實作。
**碼證**: `EquityCurveData` bare annotations 在 `api/models/pattern_analysis_models.py:503-512`；VERIFY schema → 7 個欄位 description 全為 `null`；`docs/ROADMAP.md:72-74`、`docs/IC1D_ATTRIBUTION_SPEC.md:281,288` 仍寫 `strategy_returns`/cumsum，target commit 未改 `docs/API_SPECIFICATION.md`。
**來源摘要**: api/models/pattern_analysis_models.py#8c41e1a2fbc3
[MINOR] 信心度=High；runtime route/frontend 已同步，故非 P1 runtime blocker；修法是 Field descriptions／API response example 及 active docs 同步，Archived 文件須明標歷史版本。
### A11y／測試建議（非另列 finding）: `NaiveStrategyEquityChart.tsx:58-65` 宣告 tablist/tab 但沒有 tabpanel/aria-controls 或箭頭鍵導覽；補 component test：compound 顯示 `strategy_compound` 終值，點 simple 後顯示不同 `strategy_simple` 終值；build 已通過（既有 5 個 hook warnings）。
ASSUMPTIONS_VERIFIED: 公式／百分比／threshold 語意；route fillna；runtime 舊鍵 grep；多 symbol caller；API schema descriptions；mutation 可使 compound 測試變紅。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/test_prediction_analyzer_equity.py -q` → 5 passed；isolated mutation → 4 failed/1 passed；`npm run build` → compiled successfully；decoupling baseline → BASELINE OK。
FAILURES_SEEN: mutation 失敗為預期且已在 isolated `/tmp/codex-pacumsum-review-Eyszgf` 完成；主工作區無 mutation。
SCOPE_CHANGES: none；未改 code、測試、docs、git history 或 data_cache；產出檔：`handoffs/20260818-pacumsum-review-codex.md`。NUMERIC_OR_SCHEMA_IMPACT: 發現多 symbol compound 數值語意與 API 欄位文件風險；本次未修改輸出 schema。
STATUS: DONE
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

## GROK-R23-P2-01

**斷言**: `api.models.pattern_analysis_models.EquityCurveData.final_return_pct` 型別為裸 `Dict[str, float]`，不強制四鍵；舊鍵或空 dict 皆通過 pydantic，前端讀 `strategy_simple` 會在缺鍵時 runtime 爆。

**碼證**: `venv/bin/python` 實例化 `final_return_pct={"strategy": 10.0}` 與 `{}` 皆成功；`model_json_schema()["properties"]["final_return_pct"]`＝`additionalProperties: number`、無 `required` 四鍵。對照 `test_to_dict_matches_api_model_and_has_no_unlabeled_keys` 只鎖 producer `to_dict`，不鎖 API 入模約束。RECHECK: 同上兩行構造＋讀 schema。

**來源摘要**: api/models/pattern_analysis_models.py#8c41e1a2fbc3

[P2/MAJOR] 信心度=High。失敗模式：未來手組 response／部分 mock／過渡客戶端漏鍵 → 200 但 UI `toFixed` TypeError。修法：嵌套 `FinalReturnPct(BaseModel)` 四必填 float，或 `Field(..., json_schema_extra=…)`／validator 檢查 key set；TS 已具名，Python 應對齊。不擋本票 producer 正確路徑，但 breaking rename 後契約應機械封閉。

---

## GROK-R23-P3-01

**斷言**: 引擎對 `actual_returns` 非有限 raise，但 `y_pred_proba` 含 NaN 時靜默空手、含 `+inf` 時靜默視為持倉；與本票「禁靜默當 0」敘事不對稱。

**碼證**: `prediction_analyzer.py:168-170` 只 `isfinite(actual_returns)`；實跑 `proba=[0.9,nan,0.8]` → positions `[1,0,1]`；`[0.9,+inf,0.8]` → `[1,1,1]`。route `:1049` 未 `fillna` proba。RECHECK: 同上三行探針。

**來源摘要**: momentum/Analysis/prediction_analyzer.py#60defe07cff8

[P3/MINOR] 信心度=High（行為）；Medium（是否本票必修）。NaN→空手常可辯「缺訊號不交易」；+inf→滿倉不可辯。修法：`not np.all(np.isfinite(y_pred_proba))` 同樣 ValueError，或 clip／文件化；補一測。route 已 fillna returns，HTTP 主路徑不受益於僅引擎 raise。

---

## GROK-R23-P3-02

**斷言**: EquityCurve 欄位無 `Field(description=…)`，且 `docs/API_SPECIFICATION.md` §10.8 仍僅 HTTP 路徑；commit `7d516540` subject 宣稱「API_SPECIFICATION 10.8 補欄位」但該檔不在 diff。

**碼證**: `EquityCurveData.model_fields[*].description` 全 `None`；`docs/API_SPECIFICATION.md:621-624` 只見 GET 路徑；`git show 7d516540 --name-only` 無 `API_SPECIFICATION.md`。RECHECK: 同上。

**來源摘要**: api/models/pattern_analysis_models.py#8c41e1a2fbc3

[P3/MINOR] 信心度=High。OpenAPI／外部讀者看不到單利／複利語意（只靠 class docstring 一段）。摩擦六十七若禁改 API_SPEC，應：(1) 至少補 `Field(description=…)`；(2) commit message 勿宣稱已補規格檔。不擋合併。

---

ASSUMPTIONS_VERIFIED: 單利 cumsum／複利 cumprod−1 與標籤一致；空手複利乘 1；final_pct×100；舊鍵無 runtime 消費者；mutation 4 紅後還原 5 綠；Dict 四鍵未強制；proba NaN/inf 行為如上
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/test_prediction_analyzer_equity.py -q` → baseline 5 passed；mutation 4 failed／1 passed；restore 5 passed
FAILURES_SEEN: mutation 預期紅（已還原）；none unexpected
SCOPE_CHANGES: none（唯讀＋臨時 mutation 已還原）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）；指出 schema 缺口供後續加固
STATUS: DONE

## 戳記
