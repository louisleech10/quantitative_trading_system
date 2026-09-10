# SPLITUNIFY X review R4 — codex | task-id=20260911-SPLITUNIFY-X-REVIEW-R4
範圍：只審 E1/E2 與介面可執行性；SPEC/TODO hash 與 brief 相符（384aa22961d0…／cd95ee642a9e…）。禁改碼。
## CODEX-R4-P1-01
**斷言**: E1 尚未閉合：`label_end_ms >= test_start_ms` 只在 test plan 非空且 source-bar endpoint 已有可驗證輸入時可實作；v4 同時允許 `test_start_ms=None`，又要求投影檢查 source bars，但投影簽名沒有 bars/endpoint universe。
**碼證**: `sed -n '112,118p' momentum/Analysis/event_samples/event_split.py` → 現行 guard 為 `label_end_ms > test_start - embargo`；`sed -n '19,41p' momentum/core/split_preview.py` → test rows 起點為 `split_point + purge_gap + embargo`；SPEC C-4:175-203、TODO:164-185；`types.py:55-60` 的 EventManifest 僅 table/summary/policy，`alignment.py:197-213` 才持有 bars endpoint。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0; docs/SPLITUNIFY_TODO.md#cd95ee642a9e; momentum/core/split_preview.py#6b6a1d95c5cc; momentum/Analysis/event_samples/types.py#8ba12e1b5204; momentum/Analysis/event_samples/alignment.py#0da3c48b2668
[BLOCKING] 信心度=High。可直接實作的 canonical 式子是：`train_cutoff = feature_cutoff_ms ∈ as_ms(feature_index[train_plan.row_index])`；非空 test plan 時，`train_cutoff and label_end_ms >= as_ms(feature_index[test_plan.row_index[0]])` ⇒ purge（`>=` 必須保留）。`purge_gap`/`embargo` 是 row 單位且已包含在 test row 起點，不得再以毫秒相減；test rows 為空應先 fail-closed/轉 event-study-only，不能與 None 比較。另須傳入 source endpoint receipt/index，或明定上游驗證為可證明前置條件。
## CODEX-R4-P1-02
**斷言**: E2 的六欄與 `event_id` 單鍵仍不足以閉合多 TF provenance，且 v4 沒指定 `event_keys` 的產生者與批次；`manifest.table` 的 timeframe 不能代替 per-TF feature cutoff 的 timeframe。
**碼證**: `nl -ba momentum/Analysis/event_samples/alignment.py | sed -n '197,213p;237,242p'` → `receipts.per_tf` 每 `(event_id, sub_tf)` 可多列、`feature_cutoff_ms` 在 per_tf；`nl -ba .../dedupe.py | sed -n '39,49p;101,120p'` → manifest 依 label_start/event_id 重排且只 merge trigger `timeframe`；`types.py:37-40,55-60` → event_level/per_tf 分離、manifest 無 cutoff。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0; docs/SPLITUNIFY_TODO.md#cd95ee642a9e; momentum/Analysis/event_samples/alignment.py#0da3c48b2668; momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e; momentum/Analysis/event_samples/types.py#8ba12e1b5204
[BLOCKING] 信心度=High。B2b 應新增具名 helper 產生 `event_keys`：由 `receipts.event_level`（id/label/symbol/trigger context）與 `receipts.per_tf` 按 `event_id + 明示 selected feature timeframe` keyed join，並帶 endpoint receipt；B3 只傳遞，不在接線處臨時組裝。若保留 `event_id` 單鍵，必須要求每事件恰一個 selected per_tf row；若允許多 TF，鍵與輸出契約須改成 `(event_id, timeframe)`，否則會靜默錯配。
## CODEX-R4-P1-03
**斷言**: Task 3.1 的 embargo raise 指令引用不存在的 config 欄位層級，實作端照字面會漏 guard 或在 pipeline 直接 AttributeError。
**碼證**: `nl -ba momentum/Analysis/event_samples/pipeline.py | sed -n '31,45p'` → `EventPipelineConfig` 只有 `split: EventSplitConfig`；`types.py:64-83` → `embargo_ms`/`embargo_ms_by_symbol` 在 `EventSplitConfig`；SPEC:480、TODO:273 卻寫 `config.embargo_ms`。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0; docs/SPLITUNIFY_TODO.md#cd95ee642a9e; momentum/Analysis/event_samples/pipeline.py#f78eae8df0f6; momentum/Analysis/event_samples/types.py#8ba12e1b5204
[BLOCKING] 信心度=High。Task 3.1 應明寫事件 pipeline caller 的 `config.split.embargo_ms is None and config.split.embargo_ms_by_symbol is None`；IC orchestrator 的 `_build_holdout_split_plan` 收的是 `ICConfig`，不得把同一 assert 無條件套到該 caller。
UNVERIFIED_ASSUMPTIONS: `test_start_ms` 永遠非 None、六欄唯一描述單一 feature TF、上游 endpoint 驗證可由投影推知；均未成立或未被 v4 明定，已由 P1-01/P1-02 覆蓋。
## 必答回覆（R4）
1. E1：不完全閉合；非空 test plan 的直接式如 P1-01，`>=` 保留，不能再減 row embargo；空 test plan 必須 fail-closed。
2. E2：按現文不夠；producer 應是 B2b 的 keyed adapter（event_level＋per_tf＋endpoint provenance），B3 只接線傳遞。
3. 介面掃描：plans/index/bucket/unit 檢查有輸入或可由既有 helper 執行；source endpoint、空 test boundary、多 TF producer 與 Task 3.1 config 層級不閉合，P1-01～03。
4. 不可進 B1：E1/E2 尚非可施工契約；B1 會凍結文件並放行 B2b，故上述 P1 必須先修。
## Verdict
不可進 B1：CODEX-R4-P1-01、CODEX-R4-P1-02、CODEX-R4-P1-03。
ASSUMPTIONS_VERIFIED: brief hashes；event_split.py:114 現行 purge；holdout_test_row_index 之 purge_gap+embargo row 起點；EventPipelineConfig 的 nested split；per_tf 多 TF 欄位與 manifest 缺 endpoint universe。
TESTS_RUN: read-only `shasum -a 256`、`sed`、`nl`、`rg` evidence scans；未跑 pytest（brief 禁 governance，且本輪禁改碼）。
FAILURES_SEEN: none。
SCOPE_CHANGES: none；產出 handoffs/20260911-splitunify-x-review-r4-codex.md。
NUMERIC_OR_SCHEMA_IMPACT: 未改數值、schema、輸出大小；僅提出 E1/E2 contract 修補要求。
STATUS: DONE
