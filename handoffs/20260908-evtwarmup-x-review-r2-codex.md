## Verdict：需修補後派工；本輪 4 P1／1 P2，無新 P0。
## CODEX-R2-P1-01
**斷言**: Task 2.1 未列 `ICFilterOrchestrator.get_top_features` 這個 ICIR 消費端；事件路徑混有 `None` 時 production `/top-features` 會排序崩潰。
**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:2895-2908` 仍 `key=lambda item: item.get(sort_by, -inf)`；`api/routes/ic_analysis.py:496-513` 直接呼叫；實跑 `venv/bin/python -c '...get_top_features()'` → `TypeError: '<' not supported between instances of 'float' and 'NoneType'`。
**來源摘要**: docs/EVTWARMUP_TODO.md#b60b4a88a8cf;momentum/Analysis/ic_filter_orchestrator.py#644bd066457d;api/routes/ic_analysis.py#95216b9ddbf0；正文：[MAJOR] 信心度=10/10；補入 TODO 檔案、finite fallback 與事件／混合 None 測試，並涵蓋 API caller。
## CODEX-R2-P1-02
**斷言**: SPEC/TODO 把 `ic_reporter.py:864 allow_nan=False` 當成 `save_report` 事實，但實際 `save_report` 未禁 NaN，非有限 ICIR 可落成非標準 JSON `NaN`。
**碼證**: `momentum/Analysis/ic_reporter.py:812-837` 的 `save_report` 用 `json.dump` 未傳 `allow_nan=False`；`_sanitize_summary_table_for_json:920-934` 不處理 `icir`；實跑 save_report probe stdout=`..."icir":NaN`，而 `frontend/src/hooks/useICAnalysis.ts:37` 直接 `response.json()`。
**來源摘要**: docs/EVTWARMUP_SPEC.md#c880b0f33f13;docs/EVTWARMUP_TODO.md#b60b4a88a8cf;momentum/Analysis/ic_reporter.py#73006e6bb658；正文：[MAJOR] 信心度=10/10；TODO 須明定 producer/serializer 將非有限 icir 轉 JSON null，並以 raw `json.loads`＋`allow_nan=False` gate 驗收，不能以「不 raise」代替。
## CODEX-R2-P1-03
**斷言**: TFWINDOW §G 同時要求 12h 整份 canonical sha256／逐鍵不變，又要求新增 `ic_window_disclosure` 鍵並重凍；兩個 acceptance oracle 互斥。
**碼證**: `docs/TFWINDOW_SPEC.md:26,29,31` 分別寫「整份報告 sha256 逐位元組不變」「全域報告新增鍵」「12h run 逐鍵不變」；TODO `:58,60` 又要求新增鍵後重凍。正文：[MAJOR] 信心度=10/10；改成「數值／既有欄位 projection 不變＋canonical 新 hash」或排除揭露鍵，並只保留一套可執行 gate。
**來源摘要**: docs/TFWINDOW_SPEC.md#27b6720e2177;docs/EVTWARMUP_TODO.md#b60b4a88a8cf；
## CODEX-R2-P1-04
**斷言**: 方案 B 的 `degraded_full_sample`＋`pass_class` 仍有未列消費端會把「holdout 已套用但事件不足」誤說成 full-sample fallback。
**碼證**: `frontend/src/components/ic-analysis/MarginalICTable.tsx:48-63` 直接顯示 `Full-sample research-only`；`momentum/Analysis/ic_reporter.py:586-604,624-638` 對任一 degraded 無條件輸出 `full-sample fallback`；實跑 `generate_ai_json` with reason=`insufficient_test_events` → 第一條 warning 仍為該字面。
**來源摘要**: docs/EVTWARMUP_SPEC.md#c880b0f33f13;docs/EVTWARMUP_TODO.md#b60b4a88a8cf;frontend/src/components/ic-analysis/MarginalICTable.tsx#c8a4bd68ad04;momentum/Analysis/ic_reporter.py#73006e6bb658；正文：[MAJOR] 信心度=10/10；最小修法仍在本票：補 reason-aware 文案／notes、列出上述 export／marginal consumer 與測試，不擴 status 枚舉。
## CODEX-R2-P2-01
**斷言**: 事件 summary 的 `icir=None` 與前端承諾不一致：`ICSummaryTable` runtime 已安全顯示 `--`，但 `ICFeatureInfo.icir` 仍宣告為 non-null `number`，且無該 component 的 null regression test。
**碼證**: `frontend/src/lib/types.ts:2039-2045` 為 `icir: number`；`ICSummaryTable.tsx:49-59,91-105,386-388` 以 finite guard 顯示 `--`；`frontend/src/components/ic-analysis` 無 `ICSummaryTable` test。正文：[MINOR] 信心度=9/10；把 API type 改為 `number|null` 並釘 null／NaN 顯示與排序測試；目前 runtime 顯示本身已驗證不炸。
**來源摘要**: docs/EVTWARMUP_TODO.md#b60b4a88a8cf;frontend/src/lib/types.ts#7612e6b1d329;frontend/src/components/ic-analysis/ICSummaryTable.tsx#2e94c8c4c522；
R1 disposition（原提出方 CODEX）：`CODEX-R1-P1-01` CLOSED；`P1-02` 僅 status 枚舉 CLOSED、消費語意殘留見本輪 P1-04；`P1-03` OPEN（top-features／export 漏列）；`P1-04` OPEN（TFWINDOW §G 仍矛盾）。1b 新矛盾＝P1-02 false receipt、P1-03 golden oracle、P1-04 consumer、P2-01 type。
必答：2a 有，P1-01/P1-02/P1-04；2b 文案、serializer gate、consumer notes/test，仍不擴枚舉。3a 兩段 truth table 對 `{}`、disabled、`n_events<min_events` 均 fail-closed；3b fallback rerun／scan cube 每格判定不誤擋（文件已明定）。4a 未列全；4b 有限 ICIR 下 reporter 相對順序不變，但 endpoint/export 仍需釘。5 無 ≥10× 複雜；6 不可進 B1。
類別(1–11)：1=P1-03/04；2=P1-01/04；3=P1-02/03；4=無公式疑慮；5=無；6=無；7=無；8=P1-02/P2-01；9=P1-01/02/P2-01；10=P1-01/03；11=無。
§0：fact-verified＝三 template PASS、baseline probe rc=0 且 `與既有 golden 相同？ True`、top-features TypeError、save_report raw `NaN`、pass_class grep 命中 MarginalICTable；assumed＝未實作後的新增 artifact／測試尚未存在。
TESTS_RUN：三個 `bash scripts/template_check.sh ...` rc=0；`venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` rc=0／sha256 `af73d325e0c4`／True；兩個最小 Python probes 分別實證 TypeError 與 raw `NaN`。
FAILURES_SEEN：none（未跑 `pytest tests/governance`）。
SCOPE_CHANGES：唯讀審查；未改碼／文件／data_cache；產出=`handoffs/20260908-evtwarmup-x-review-r2-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT：本次未修改；指出預定 JSON null、TS nullable、golden hash oracle 之契約影響。
STATUS: DONE
