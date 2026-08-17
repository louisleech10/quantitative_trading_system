# GAP-1 B2 code review｜task-id=20260818-GAP1-B2-REVIEW-R14｜family=codex
Review target: commit 7f0decc8；範圍為契約、contract.py、ledger.py 與三個 B2 測試檔。
Verdict: 需修補後進 B3；無 P0；六項 canonical findings。
段 A: 16 個機械鍵、6 計數欄、12 reasons、雙向 reason_conditions、scope 與 ref dereference 骨架通過；loader 仍 fail-open unknown key/enum。
段 B: set equality 本身不損失單一 ledger_row_invalid 語意；float/int 不造成已觀測數值失真；cache、append 競態、row context 與 NaN/inf 有問題。
段 C: 90 tests 與 B1 mutation 通過；ledger_path 被 monkeypatch，未覆蓋真實推導，亦缺 duplicate-concurrent、context mismatch、non-finite assertions。
段 D: n_for_dsr=n_candidates_considered 正確；snapshot_hash 有分隔符碰撞；annualized 合法枚舉與 TODO ⑥b「rejected」互斥，需延伸裁決。
FACT-VERIFIED: pytest strategy_validation=90 passed；gap1_b1_mutation_probe rc=0（baseline 99、8 mutants rc=1、post-restore 99）。
TESTS_RUN: stamp check rc=0；反例輸出 INVALID_ONLY=n_unknown、CROSS_CONTEXT=1、NONFINITE=nan、SNAPSHOT_COLLISION=True、UNKNOWN_TOP_LEVEL accepted、ENUM invalid accepted、CACHE_MUTATION=True。
FAILURES_SEEN: duplicate-race python probe 兩次單行語法錯，未將其當 runtime receipt；source-level interleaving 結論保留。SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: findings 涉及 ledger identity/count/hash/reason/schema。
## CODEX-R14-P1-01
**斷言**: append 未綁定 record 的 research_session_id/dataset_key，且 evaluation_id 檢查是讀後寫；可跨帳本污染並讓同 ID 併發重複落列。 **碼證**: ledger.py:210-236 只以參數造 path、未比對 row context；反例 `CROSS_CONTEXT 1`；兩 writer 可同時讀空檔後各 write；RECHECK: two-process same evaluation_id。
**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19；tests/.../test_ledger_conformance.py#164199e6a7dd。P1 信心=10/10；修法是 atomic uniqueness/lock 或 durable unique index，並拒絕 context mismatch。
## CODEX-R14-P1-02
**斷言**: metric_value 的 NaN/inf 會通過 schema gate，且檔案全為非法列時公開 reason 被錯置為 n_unknown。 **碼證**: ledger.py:66-84 未 isfinite、json.dumps 預設 allow_nan；:167-174 強制 n_evaluated==0 時 n_unknown；反例 `NONFINITE ... nan`、`INVALID_ONLY unavailable n_unknown 1 ('ledger_row_invalid',)`。
**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19；BRIEF#5fd6d3654564。P1 信心=10/10；修法是拒絕非有限 metric_value，並保留 ledger_row_invalid；補 invalid-only/inf 測試。
## CODEX-R14-P1-03
**斷言**: annualized 是契約合法 enum，實作把它 schema-valid 且排除 valid_sharpe_values；這符合資料語意但不符合 Frozen TODO ⑥b 的 rejected 字面，B2 gate 無法同時滿足兩者。 **碼證**: contract.json:168-169；ledger.py:81-83,150-153；反例 `ANNUALIZED ok  1 0 () ()`；RECHECK: run annualized row。
**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#3cc06afd3b47；docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#d239583e439c。P1 信心=10/10；不可直接改 frozen 文件，須走延伸裁決：合法 enum 應 schema-valid/filter，或移除 enum 後才 reject。
## CODEX-R14-P1-04
**斷言**: snapshot_hash 的 `|` 未 escape/length-prefix，dataset_key 或 research_session_id 含分隔符即可碰撞不同輸入。 **碼證**: ledger.py:161-165；`{a},b|c,d` 與 `{a},b,c|d` 都串成 `a|b|c|d`，實跑 `SNAPSHOT_COLLISION True`。
**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#3cc06afd3b47；momentum/.../ledger.py#5f914fb8cb19。P1 信心=10/10；修法是 canonical length-prefix/JSON tuple，並新增 delimiter-in-id collision test。
## CODEX-R14-P2-05
**斷言**: 測試 fixture monkeypatch ledger_path，故真實 `MomentumConfig.results_path/strategy_validation/<session>__<dataset>.jsonl` 推導完全未覆蓋。 **碼證**: test_ledger.py:17-25、test_ledger_conformance.py:20-25 以 fake path 取代 ledger_path；ledger.py:56-59 才是 production path；現有 90 tests 仍全綠。
**來源摘要**: tests/.../test_ledger.py#43477bd8daf2；tests/.../test_ledger_conformance.py#164199e6a7dd。P2 信心=10/10；修法是保留隔離 fixture 外，加入 config-backed path test，並覆蓋 process/large-line/duplicate-id/context/non-finite cases。
## CODEX-R14-P2-06
**斷言**: `_contract_cache` 是可被 caller 修改的 mutable global 且無 mtime/version key；loader 亦不拒絕 unknown top-level key 或 report enum，會造成 stale/漂移 fail-open。 **碼證**: contract.py:29,66-88,143-160；反例 `CACHE_MUTATION True True`、`UNKNOWN_TOP_LEVEL accepted True`、`ENUM_VALIDATION accepted invalid universe_scope`。
**來源摘要**: momentum/Analysis/strategy_validation/contract.py#de4d4a4270f0；CLAUDE.md The 7 Decoupling Rules Rule 8。P2 信心=10/10；修法是 immutable/no cache 或 keyed invalidation，並在 load/validate 強制 exact top-level 與各 enum membership。
STATUS: DONE
