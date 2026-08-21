# Reconcile — 20260821-gap3-b4-review-r3

**來源** 20260821-gap3-b4-review-r3-codex.md, 20260821-gap3-b4-review-r3-composer.md, 20260821-gap3-b4-review-r3-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（主委 Claude 裁決；R3 閉合輪＋codex 一條修補引入缺口寫回）

**Verdict**: 需修補後合併——CODEX-R2-P1-01／P1-02 由 codex 重跑 CLOSED、composer／grok 複核同意；codex 本輪抓一條 R2 修補引入之對帳缺口（P1）已採納修補；R4 由 codex 重跑同一反例閉合（composer／grok sentinel）→ 全 CLOSED 後三家 RECONCILE-STAMP → B4 CLOSED。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| Z1 逐 evaluation 對帳 | CODEX-R3-P1-01 | **採納**：`provenance_reconcile` 改以 `(candidate_id, evaluation_id)` 逐列對帳（帳本側讀 schema-valid 列、與 `read_trial_ledger` 同判準；sidecar 側讀 pairs）；`ledger_without_provenance`／`provenance_without_ledger` 值為 `cid:eid`；`complete`＝帳本 pairs 非空且 ⊆ sidecar pairs；`run_dsr_pbo` 任一帳本 evaluation 缺 provenance ⇒ `unavailable:provenance_incomplete`。測試：同 candidate 重試入帳後孤兒 `a:eval-a` 仍列出；帳本 `b:eval-b` 缺 provenance 時即使 `b:eval-b2` 齊備仍 unavailable；補 sidecar 後 ok |
| Z2 兩家 sentinel＋docstring 漂移 | COMPOSER-R3-P3-00, GROK-R3-P3-00 | **採認**：0 新 findings；兩家觀察 `record_candidate` docstring 寫入順序與實作不一致（MINOR）——主委已同輪改正 docstring（sidecar 先、帳本後） |

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P1-01

**斷言**: `provenance_reconcile` 以 candidate_id 而非 evaluation_id 對帳；同 candidate 的 orphan evaluation 可被吞掉，進而讓 DSR/PBO 錯報 complete/ok。

**碼證**: `candidate_ledger.py:262-292` 將 sidecar 聚合為 candidate 集合並只做集合差；`ledger.py:344-350` 明定同 candidate 可有不同 evaluation_id。反例命令輸出：sidecar `eval-first` orphan、ledger `eval-retry` 後 `reconcile={'ledger_without_provenance': [], 'provenance_without_ledger': [], 'complete': True}`；兩候選 `capability='ok' dsr_status='ok' pbo_status='ok'`。
RECHECK: 重現「ledger append 失敗→同 candidate 新 evaluation_id 入帳→run_dsr_pbo」並要求 reconcile 列出 orphan evaluation 或回 unavailable。

**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#f4120b45d535；momentum/Analysis/strategy_validation/ledger.py#0322a1804784；handoffs/20260821-gap3-b4-review-r3-brief.md#3c0220b28f0c；docs/GAP3_EVENT_TODO.md#df04bdabf37d

[P1] 信心度=High；R2 的 sidecar-first 修補確實使 N 不受 orphan 影響，但目前 reconcile 無法履行「可列出 orphan」承諾。應以 `(candidate_id, evaluation_id)`（及必要的有效 provenance 對應）逐列對帳；任一 ledger evaluation 缺 provenance 時，DSR/PBO/eligibility 應 fail-closed。此為本輪修補引入的 consumer 對帳缺口。

ASSUMPTIONS_VERIFIED: R2 diff 僅 candidate_ledger.py＋其測試；兩條反例與 B4 Gate 均實跑；未重跑 golden。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k sidecar_first` → 1 passed, rc=0；`-k stale_receipt` → 1 passed, rc=0。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k 'pattern_bridge or candidate_ledger'` → 29 passed/195 deselected, rc=0。
FAILURES_SEEN: 初次 inline probe quoting 失敗（SyntaxError），未改碼；修正命令後反例重現如上。
SCOPE_CHANGES: 僅新增本交件檔；未改程式、測試、SPEC/TODO、HANDOFF.md；/tmp 未新增 workdir，保留 claude-501。
NUMERIC_OR_SCHEMA_IMPACT: none。
STATUS: DONE
## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——CODEX-R2-P1-01／P1-02 修補逐碼對齊且 RECHECK 全綠；composer 複核同意兩條 CLOSED；修補未引入可證偽 P0–P2 缺陷；brief assumed（provenance 孤兒邊界）攻擊不推翻。

**碼證**: B4 Gate：`-k "pattern_bridge or candidate_ledger"` → **29 passed** rc=0；event_samples 全套 → **224 passed** rc=0；strategy_validation → **272 passed** rc=0。R2 RECHECK：`-k "sidecar_first or stale_receipt"` → **2 passed** rc=0。修法落點：`candidate_ledger.py:238-254` sidecar 先寫；`:281-295` `provenance_reconcile`；`:350-358` `ledger_without_provenance` gate；`:99-112` `receipt_digest`＋stale 比對；`:190` `to_return_series` 綁 digest。`git diff 57abce9d..HEAD --stat -- momentum/ tests/` → 2 files +117/−10（白名單內）。

**來源摘要**: handoffs/reconcile/20260821-gap3-b4-review-r2/synth.md#Y2Y3；momentum/Analysis/event_samples/candidate_ledger.py#f4120b45d535；tests/momentum/event_samples/test_candidate_ledger.py#209e433c；handoffs/20260821-gap3-b4-review-r3-brief.md；handoffs/run_receipts/20260821T160000Z-gap3-b4-r2-fix-gate.log

正文：閉合輪義務＝複核 codex 兩條 R2 finding 是否 CLOSED ＋掃修補是否引入新問題；兩項皆通過。`record_candidate` docstring 與實作寫入順序不一致為 MINOR 文檔漂移，不升格 finding。禁捏造湊數。

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——CODEX-R2-P1-01／P1-02 複核同意 CLOSED；R2 修補（sidecar-first＋receipt_digest 重算）未引入可證偽 P0–P2 新缺陷；brief assumed（provenance 孤兒不影響 N）攻擊不推翻。

**碼證**: `pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k "sidecar_first or stale_receipt"` → **2 passed** rc=0；`-k hand_exact` → **5 passed**；`pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` → **29 passed** rc=0；手跑 orphan ⇒ `n_for_dsr=0`／`provenance_without_ledger` 可列；`receipt_digest` roundtrip 穩定；`git diff 57abce9d..HEAD --stat -- momentum/ tests/` → 2 files +129/−13（白名單內）。全套 224／GAP-1 272 引 `handoffs/run_receipts/20260821T160000Z-gap3-b4-r2-fix-gate.log`。

**來源摘要**: handoffs/20260821-gap3-b4-review-r3-brief.md#3c0220b28f0c；handoffs/reconcile/20260821-gap3-b4-review-r2/synth.md#6ad894ac71a8；momentum/Analysis/event_samples/candidate_ledger.py#f4120b45d535；tests/momentum/event_samples/test_candidate_ledger.py#3ca3a00e1a69；docs/GAP3_EVENT_TODO.md#df04bdabf37d；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；handoffs/run_receipts/20260821T160000Z-gap3-b4-r2-fix-gate.log#88e34b6dbd13

正文：複核義務兩條全同意 CLOSED；§0 assumed 已攻；不受理 SPEC/TODO 重審／B5／GAP-1 本體／R1／R2 已裁 CLOSED 再議。禁捏造湊數。docstring L200–201 與實作順序不一致僅記觀察、不升 finding。

