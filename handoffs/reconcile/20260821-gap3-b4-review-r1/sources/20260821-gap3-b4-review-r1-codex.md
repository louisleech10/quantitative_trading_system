# GAP-3 B4 review R1 — codex；Task-ID: 20260821-GAP3-B4-REVIEW-R1；基線=`git diff 3b1350df..HEAD -- momentum/ tests/`（4 檔、893 insertions）
## Verdict：需修補後派工
## CODEX-R1-P1-01
**斷言**: B4.1 缺 manifest/cluster context 仍可完成並輸出結果，違反 AR-3 必需輸入與 raw/effective-n contract。
**碼證**: `pattern_bridge.py:92-97,182-185,209` 將 `manifest`/`strata` 設 Optional 並缺 strata 造空表；`tables.py:61-82` 缺 manifest 輸出兩個 n=None。實跑 probe → `{'n_events_raw': None, 'n_events_effective': None, ...}`；B4 gate → 22 passed, rc=0。
**來源摘要**: momentum/Analysis/event_samples/pattern_bridge.py#2d4c5b8daf18；docs/GAP3_EVENT_TODO.md#df04bdabf37d
修法：要求有效 EventManifest 與 cluster/strata receipt，缺任一 fail-closed；RECHECK：新增缺 context 反例後重跑 B4 gate。
## CODEX-R1-P1-02
**斷言**: `run_dsr_pbo` 只用 artifact hash membership 綁 DSR，未要求 candidate IDs 等於 ledger；未記帳 candidate 可成 champion 並產生 DSR。
**碼證**: `candidate_ledger.py:254-285` 從輸入候選選 champion；`deflated_sharpe.py:123-132` 只檢查 hash membership；`candidate_ledger.py:301-320` 的 universe guard 只包 PBO。反例 ledger={logged:H}、輸入={unlogged: attrs.hash=H}：預期 DSR unverifiable，實際可選 unlogged 並通過 hash gate。
**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b；momentum/Analysis/strategy_validation/deflated_sharpe.py#4fb291524e3f
修法：DSR/eligibility 前要求候選 ID 與 artifact mapping 全等 ledger snapshot，否則 unavailable；RECHECK：加 logged/unlogged 反例驗 DSR 不產出。
## CODEX-R1-P1-03
**斷言**: PBO 聯集觀測軸按 event_id 字典序而非 entry time 排序，非單調 ID 時 CSCV 分塊使用錯誤時間軸。
**碼證**: `to_return_series:152-153` 只保留 entry-time 排好的 ID；`candidate_ledger.py:306-309` 丟掉原序後 `sorted({event_id})` 建 union/M。反例早進場=`z-early`、晚進場=`a-late`：預期 rows `[z-early,a-late]`，實際 `[a-late,z-early]`，違反 `:247-250` docstring。
**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b；docs/GAP3_EVENT_SPEC.md#544c2922ef2e
修法：CandidateReturns 保留 entry-time/observation-order receipt，PBO 依 canonical 軸排序並拒缺軸；RECHECK：非時間序 ID exact matrix 測試 CSCV 輸入順序。
## CODEX-R1-P1-04
**斷言**: provenance 的 `command`/`expected` 可省略，sidecar 寫入 null，違反每 oracle 必記可重播命令與預期。
**碼證**: `candidate_ledger.py:168-169` 列兩欄選填；`:205-217` 用 `.get()` 寫 sidecar，`meta_without_command_expected` 仍先 append ledger 再產生 null。
**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b；docs/GAP3_EVENT_TODO.md#df04bdabf37d
修法：append 前要求非空 command/expected 且同鎖寫 sidecar；RECHECK：缺任一欄應拒寫且 ledger/sidecar 無半成品。
逐條 verdict：1 train/test fit 隔離、sample_weight、2 split fail-closed、3 J8 train-only deterministic、5 W8 五 semantic exact、7 metric reject、9 MinBTL span/target/loud 均有碼證與 gate pass；4 受 P1-01、6 受 P1-02、8 受 P1-03；10 不可進 B5。
ASSUMPTIONS_VERIFIED: `venv/bin/python -c 'from tests.momentum.event_samples.test_pattern_bridge import synth,cfg; from momentum.Analysis.event_samples.pattern_bridge import extract_event_patterns; X,y,p=synth(); r=extract_event_patterns(X,y,p,None,cfg()); print({k:r["common"][k] for k in ("n_events_raw","n_events_effective","degraded","formal_pooled_inference_allowed")})'` → raw/effective n=None；4 檔白名單、未改碼。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k 'pattern_bridge or candidate_ledger'` → 22 passed/195 deselected/rc=0；`git diff --check 3b1350df..HEAD -- momentum/Analysis/event_samples/pattern_bridge.py momentum/Analysis/event_samples/candidate_ledger.py tests/momentum/event_samples/test_pattern_bridge.py tests/momentum/event_samples/test_candidate_ledger.py` → rc=0。
FAILURES_SEEN: none；SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: review-only，未改輸出。
STATUS: DONE
