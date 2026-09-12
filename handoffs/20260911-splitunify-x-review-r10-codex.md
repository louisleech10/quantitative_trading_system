# CODEX R10 closure review
task-id: 20260911-SPLITUNIFY-X-REVIEW-R10
findings-round: R10
## CODEX-R10-P1-01
**斷言**: D-001:72 的 defensive copy＋`setflags(write=False)` 仍不足以維持 attest 後兩欄不可變。
**碼證**: `venv/bin/python -c 'import numpy as np,pickle; x=np.array([1,2]); x.setflags(write=False); y=np.asarray(x); y.setflags(write=True); y[0]=99; z=pickle.loads(pickle.dumps(x)); print("same",y is x,"after_reenable",x.tolist(),"pickle_writeable",z.flags.writeable)'` → `same True after_reenable [99, 2] pickle_writeable True`; deepcopy probe → `deepcopy_writeable True`; D-001:72,125-126。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#84942a34e86c
必答1：`CODEX-R9-P1-01` 規格層已閉合；body hash 實跑為 `84942a34e86cb6234d9fe7d11602a600541dba683d8ed74398afd0c161a1409c`，且 D-001:72、125-126 已納入兩條原回歸。
必答2：未完全封住；`np.asarray` 同物件、slice、`deepcopy`、`pickle.loads` 均可取得可寫路徑。`replace`／consumer `.copy()` 不會回寫原 plan，但不能抵銷上述 bypass；需補不可重新開寫的 backing 或完整 copy/pickle/deepcopy lifecycle guard。
## CODEX-R10-P1-02
**斷言**: `timedelta` producer 路徑未保證每個 symbol 的輸入 frame 按時間排序；新增 fail-closed 會改變現有亂序輸入的行為。
**碼證**: `ic_filter_orchestrator.py:1966-69` 只驗 MultiIndex，`:861-64` 保留輸入順序，`:923-930` 走 `split_per_symbol(..., purge_semantic="timedelta")`，而 `contracts.py:656-661` 另行按時間排序；亂序 probe → `True False {'BTCUSDT': False, 'ETHUSDT': False} 2`（現行 path 通過）。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#84942a34e86c
必答3：正常 factory ingestion 在 `feature_factory.py:795-796` 排序、service `ic_analysis_service.py:1787-1792` 保留各 symbol 排序；但 direct/legacy caller 未受保證，具體會被新擋的是 `analyze_cross_sectional`→`_build_cross_sectional_global_split`→`:930`。
必答4：接受主委更正；本家 R9 是 blocked 方，非「proceed」方；因此本家裁決不因該事實更正而改變。
必答5：`VERDICT: blocked`；若不補，attest 後可由可寫/反序列化 plan 造成兩欄漂移，且未排序既有 caller 會在 b8 被新閘擋下。
ASSUMPTIONS_VERIFIED: D-001／TODO／R9 synth 已讀；D-001 hash、格式、template、attribution、synth-xref 均實跑通；numpy re-enable/deepcopy/pickle 與 timedelta 亂序 producer probe 已實跑。
TESTS_RUN: `bash scripts/agent_preflight.sh` rc=0；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` rc=0；doc_format/template/attribution/synth-xref rc=0；兩組 `venv/bin/python -c` probe 如上。
FAILURES_SEEN: `spec_xref_check.sh --synth` 首次少傳 target rc=2，補正為 `... synth.md docs/SPLITUNIFY_SPEC.D-001.md` rc=0；未跑 governance 全套。
SCOPE_CHANGES: 僅新增本交件檔；未改 tracked code/data，未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none；review only，未改產品數值、schema、golden 或輸出大小。
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r10-codex.md
TMP_CLEANUP: `/private/tmp` 無 `*workdir*` 目錄可清；保留 `/private/tmp/claude-501`。
RECONCILE-STAMP: codex APPROVED 2026-09-12 sha256:84942a34e86cb6234d9fe7d11602a600541dba683d8ed74398afd0c161a1409c task:20260911-SPLITUNIFY-X-REVIEW-R10
VERDICT: blocked
BLOCKED-BY: CODEX-R10-P1-01,CODEX-R10-P1-02
CLOSED: CODEX-R9-P1-01
STATUS: DONE
