# IC Phase 0 — Manifest（扁平 ID，coverage_check 比對用）

> 2026-06-25 ｜ 每個 `[X-N]` 都必須落進 SPEC 與 TODO（機器逐 ID 比對）。
> 字母段：M=meta/跨切、C=IC-CRASH、T=IC-TIMEAXIS、B=IC-BYVOL、F=IC-FEATURE-GUARD、D=IC-DECAY-LOG、U=IC-UX-ERR。
> 白話版 brief：`20260625-ic-PHASE0-BRIEF.md`；定義：`20260624-ic-PHASE0-DEFINITION.md`。

## M — 跨切（SPEC 必含段）
- [M-1] 風險分級：大、命中 (b) 跨模組共用路徑 + (d) ML/回測正確性 → §G Golden 必填、adversarial 必跑
- [M-2] §A 已驗證事實（六項，皆附碼證/實跑輸出，見 SPEC §A）
- [M-3] §A 待確認：IC-BYVOL 修法（實作 vs fail-closed）交委員會收斂，非問使用者
- [M-4] §C 約束：解耦 7 條（`grep from api\. momentum/`→0）、不靜默截斷、不弱化 NaN/inf gate、不改 IC 數值語義（除修錯的 T/B）
- [M-5] §G Golden：grouped_ic 真 config 回歸 + feature_filter 落地前後 metadata + timestamp 秒級 byte-faithful fixture
- [M-6] §R 回退：每 epic 獨立 commit 可單獨 revert；FAIL → 不 merge
- [M-7] 不可做：串流重寫/train-test/case-control/decay R2 early-skip/decay·grouped 向量化（皆留後 Phase）

## C — IC-CRASH（崩潰修，最優先）
- [C-1] orchestrator caller（:1139）改傳 `grouped_analysis.model_dump()` 給 compute_grouped_ic（dict 契約）
- [C-2] 確認 compute_grouped_ic 僅單一 caller（已驗）→ 不需改 engine 簽名（不選 A2）
- [C-3] 回歸測試打真實路徑：真 config + `include_regime_analysis=True`，斷言不再 AttributeError 且 grouped_ic 有結果；移除/取代用 SimpleNamespace+dict 繞過的假綠測試

## T — IC-TIMEAXIS（秒/毫秒，正確性）
- [T-1] `_get_time_index`（:1024-1025）numeric timestamp 改實測單位判斷（秒 vs 毫秒，依數值量級），不寫死 ms
- [T-2] fail-closed sanity check：解出年份 <1990 或 >今年+1 → raise（不靜默產錯軸）
- [T-3] 回歸測試 fixture byte-faithful 重現真實秒級 timestamp（如 1704067200→2024）；禁用 ms 構造假綠；斷言 by_year 落在正確年份

## B — IC-BYVOL（契約漂移）★委員會收斂後定
- [B-1] by_volatility schema 預設 True 但 compute_grouped_ic 無分支 → 修法由委員會收斂：(a) 實作波動度分組 或 (b) fail-closed 報錯不支援（Claude 傾向 b）
- [B-2] 依 B-1 結論落實：不靜默忽略；若 fail-closed 則明確 error 訊息指明契約不支援

## F — IC-FEATURE-GUARD（幽靈落地，Phase 2 前置）
- [F-1] ICConfig（momentum/Analysis/ic_config_schema.py）加 feature_filter 欄位（對應 API FeatureFilterConfig 語義）
- [F-2] orchestrator 真消費 feature_filter：include/exclude/pattern/categories/data_sources/families/max_features 全生效
- [F-3] max_features 截斷需確定性排序準則（避免每跑不同）→ SPEC 定明確順序
- [F-4] metadata 記錄：原始特徵數 / 篩後數 / 篩選條件（不靜默截斷，可審計）
- [F-5] 大 run 警示（如 >N 特徵 log 警告，閾值 SPEC 定）
- [F-6] preview_limit 改名 + API schema 版本化（不破壞既有前端）
- [F-7] 回歸測試：feature_filter 落地前後 metadata 計數正確 + 篩選真生效（非全量）

## D — IC-DECAY-LOG（效能/違規）
- [D-1] 移除 `_fit_exponential_decay`（:944）熱迴圈逐特徵 logger.warning
- [D-2] compute_ic_decay（:331）結尾聚合一行摘要，用現成回傳的 r2/fit_warning_reason（如「N 特徵 R2<0.5」）
- [D-3] 回歸測試：跑多特徵 decay，斷言熱迴圈零 warning + 結尾恰一行摘要

## U — IC-UX-ERR（體感/錯誤傳遞）
- [U-1] 主 analyze 改 `asyncio.to_thread`（解 event loop 阻塞，比照 deep analysis）
- [U-2] 前端 WS `failed` 顯真錯誤訊息（非無條件「連線失敗」）
- [U-3] 前端停無限重連（onclose 不無限 retry）
- [U-4] HTTP poll fallback（WS 不可用時拿結果）
- [U-5] 前端回歸/型別：useICAnalysis/store 對應改動，vitest + build PASS
