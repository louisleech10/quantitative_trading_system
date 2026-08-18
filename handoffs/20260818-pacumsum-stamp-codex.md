# PA-CUMSUM R24 stamp — codex

task-id: `20260818-PACUMSUM-X-STAMP-R24`
判定：APPROVED。

BODY_SHA256: `73ca7d3a70dde4fb098bce7fc854a891d3ea66dc2e36e97e6b569258e21ccb93`

ASSUMPTIONS_VERIFIED: completeness 已確認 3/3、1/1、3/3 IDs 均被 synth 引用且 body/lock 合法；HEAD 為修補 commit `d20f0627`。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-pacumsum-x-review-r23/synth.md` → rc=0、hash 一致；`bash scripts/completeness_check.sh --synth handoffs/reconcile/20260818-pacumsum-x-review-r23/synth.md --lock handoffs/reconcile/20260818-pacumsum-x-review-r23/sources.lock` → rc=0；`git show d20f0627 --stat` → rc=0、含 brief 指定 7 類檔案；`venv/bin/python -m pytest tests/momentum/Analysis/test_prediction_analyzer_equity.py -q` → rc=0、10 passed；`npm --prefix frontend run test -- src/components/pattern/details/charts/NaiveStrategyEquityChart.test.tsx` → rc=0、4 passed；codex recheck → rc=0、compound 首值 0.0、NaN proba ValueError。
FAILURES_SEEN: 初次 codex recheck 因命令換行 quoting 產生 SyntaxError；修正探針 quoting 後同一驗收 rc=0。產品測試無失敗。
SCOPE_CHANGES: 只追加 stamp-target 戳記並建立本交接檔；未改 code／SPEC／TODO／data_cache，未 commit／push。
NUMERIC_OR_SCHEMA_IMPACT: none；本次僅驗收既有修補，未改輸出數值或 schema。
VERDICT: Q1 等權多標的 compound 首值為 0.0（非 -0.01），Q2 proba NaN fail-closed；Q3 封閉契約測試通過，且 synth 殘餘邊界已具名，故核可收案。

STATUS: DONE
