# PA-CUMSUM 修補收斂檔 RECONCILE-STAMP（三家）——PASS 即收案

VERIFY-EXEMPT:doc-example:pacumsum-stamp-criteria

> 本檔為給委員的核可判準清單（實測項目），非主委之 operational 結論。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-pacumsum-x-review-r23/synth.md

## 背景
- 你們三家 R23 對 PA-CUMSUM（單利／複利兩條都算、前端切換）之 review 共 7 條（codex 3／composer 1／grok 3）；codex「需修補後合併」（2 MAJOR）vs composer／grok「可合併」⇒ 取較嚴，全部本輪修，修補 commit `d20f0627`（已 push）。
- 三群集：Q1 多標的改逐 timestamp 等權組合（`n_symbols`／`aggregation` 可觀測）；Q2 `y_pred_proba` NaN／inf fail-closed（引擎 ValueError、route 400）；Q3 API 契約封閉（`EquityFinalReturnPct` 四必填＋Field description＋`aggregation` Literal）＋ROADMAP:72-74 改寫；另 tab a11y＋4 條元件測試。
- 🔴 主委已 commit＋push；本輪主委**不動任何檔**。`scripts/governance_families.json` 既有 no-op dirty 請忽略。自建探針加 timeout；產出檔尾 `STATUS: DONE`。

## 任務
對 `stamp-target` append `RECONCILE-STAMP`（`## 戳記` 區段）。body sha256 ＝ `73ca7d3a70dde4fb098bce7fc854a891d3ea66dc2e36e97e6b569258e21ccb93`（`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-pacumsum-x-review-r23/synth.md`；請自行重跑確認）。

## 核可判準
1. `bash scripts/completeness_check.sh --synth handoffs/reconcile/20260818-pacumsum-x-review-r23/synth.md --lock handoffs/reconcile/20260818-pacumsum-x-review-r23/sources.lock` ⇒ rc=0；你的每一條 ID 被群集引用且處置對得上你的修法。
2. `git show d20f0627 --stat` 含 `prediction_analyzer.py`／`pattern_analysis_models.py`／`pattern_analysis.py`／`patternTypes.ts`／`NaiveStrategyEquityChart.tsx`＋`.test.tsx`／`test_prediction_analyzer_equity.py`。
3. `venv/bin/python -m pytest tests/momentum/Analysis/test_prediction_analyzer_equity.py -q` ⇒ **10 passed**；其中 `test_multi_symbol_uses_equal_weight_by_timestamp_not_single_account_compounding`（[+10%,−10%] ⇒ 0% 非 −1%）、`test_proba_nan_or_inf_raises_not_silent_flat`、`test_api_model_final_return_pct_is_closed_four_keys` 對應 Q1／Q2／Q3。
4. `npm --prefix frontend run test -- src/components/pattern/details/charts/NaiveStrategyEquityChart.test.tsx` ⇒ 4 passed（可選；build 已由主委跑過）。
5. codex：實跑 RECHECK——同一 timestamp 兩 symbol `[+0.10,−0.10]` 經 `calculate_strategy_equity_curve(..., symbols=[...])` 之 compound 首值＝0.0（非 −0.01）；`y_pred_proba=[0.9,nan]` ⇒ ValueError。
6. Verdict 與內文一致；殘餘（`actual_return.fillna(0)` route 既有行為、`API_SPECIFICATION.md` 格式快閘不可編輯）是否誠實具名。

## 戳記格式（逐字，單行；FAMILY ∈ codex／composer／grok）
```
RECONCILE-STAMP: <FAMILY> APPROVED 2026-08-18 sha256:<你實跑取得的完整 sha256> task:20260818-PACUMSUM-X-STAMP-R24
```
不核可就寫 `BLOCKED` 並具名理由。**只** append 到 `## 戳記` 區段；不得改碼／SPEC／TODO；不 commit／push。

## 產出
判定＋實跑 body_sha256＋判準 3／5 之 rc 與計數＋一句 Verdict 理由。檔尾最後一行 `STATUS: DONE`。收尾清 /tmp workdir（保留 claude-501）。
