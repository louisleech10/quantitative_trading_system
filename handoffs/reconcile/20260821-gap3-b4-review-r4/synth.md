# Reconcile — 20260821-gap3-b4-review-r4

**來源** 20260821-gap3-b4-review-r4-codex.md, 20260821-gap3-b4-review-r4-composer.md, 20260821-gap3-b4-review-r4-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（主委 Claude 裁決；R4 閉合輪）

**Verdict**: 可合併——CODEX-R3-P1-01 由 codex 重跑探針 CLOSED、composer／grok 複核同意；三家 sentinel 0 新 findings；B4 Gate 三家複驗 rc=0（29／224／272 引修後 receipt `handoffs/run_receipts/20260821T163000Z-gap3-b4-r3-fix-gate.log`）；B4 收斂履歷 R1 8→R2 2（R1 漏抓）→R3 1（修補引入）→R4 0 ⇒ 進三家 RECONCILE-STAMP（蓋本檔）→ B4 CLOSED。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| W1 三家 sentinel（0 新 findings） | CODEX-R4-P3-00, COMPOSER-R4-P3-00, GROK-R4-P3-00 | **採認**：CODEX-R3-P1-01 CLOSED（逐 evaluation 對帳；孤兒永遠列出；帳本 evaluation 缺 provenance ⇒ unavailable）；brief assumed「`_read_ledger_pairs` 直讀帳本檔只用於對帳、不產 N、同 GAP-1 合法性判準」三家攻擊不推翻；grok 觀察註解名漂移 `_provenance_complete` 已同輪改正 |

收斂履歷：R1 `handoffs/reconcile/20260821-gap3-b4-review-r1/synth.md`（8 條）→ R2 `…-r2/`（8 CLOSED＋2 新）→ R3 `…-r3/`（2 CLOSED＋1 新）→ R4 本檔（1 CLOSED＋0 新）。實作終版＝R4 stamp 派工時之 HEAD。

**殘留**：無新增；B5 follow-up 沿 B3（`requests.py` allowed_filtering_params 契約出口）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；R3 修補以 `(candidate_id, evaluation_id)` 對帳，孤兒 `a:eval-a` 不被吞，任一帳本 evaluation 缺 provenance 時 `run_dsr_pbo` fail-closed。`_read_ledger_pairs` 僅供對帳、不產 N，且沿用同一 schema 判準，未發現本輪修補引入的實質問題。

**碼證**: `candidate_ledger.py:286-313,372-381`；`venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k sidecar_first` → `1 passed`, rc=0，測試斷言 `a:eval-a` 仍列出、`b:eval-b` 缺 provenance 即 `provenance_incomplete`；B4 Gate → `29 passed, 195 deselected`, rc=0。

**來源摘要**: `momentum/Analysis/event_samples/candidate_ledger.py#dae0cf45a712`; `tests/momentum/event_samples/test_candidate_ledger.py#ab83ff44a969`; `handoffs/20260821-gap3-b4-review-r4-brief.md#3b71ddc12d2c`

正文：信心度=High。直接讀帳本檔的疑慮已逐碼核對：此路徑只產 evaluation pair 對帳資料，N 仍唯一由 `read_trial_ledger` 提供，且 `_row_is_valid`／contract 判準一致；本輪不列 finding。

ASSUMPTIONS_VERIFIED: R3 修補 diff 僅 `candidate_ledger.py` 與其測試；R3 反例與 B4 Gate 實跑 rc=0；未重跑 golden。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k sidecar_first` → 1 passed, rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/ -q -k 'pattern_bridge or candidate_ledger'` → 29 passed, rc=0。
FAILURES_SEEN: none。
SCOPE_CHANGES: 僅新增本交件檔；未改程式、測試、SPEC/TODO、HANDOFF.md；`/tmp` 無 workdir，無 `claude-501` 可保留。
NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT_ARTIFACT: `handoffs/20260821-gap3-b4-review-r4-codex.md`。
STATUS: DONE
## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——CODEX-R3-P1-01 修補逐碼對齊且 RECHECK 全綠；composer 複核同意 CLOSED；R3 修補未引入可證偽 P0–P2 缺陷；brief assumed（`_read_ledger_pairs` 直讀可接受）攻擊不推翻。

**碼證**: B4 Gate：`-k "pattern_bridge or candidate_ledger"` → **29 passed** rc=0；event_samples 全套 → **224 passed** rc=0；strategy_validation → **272 passed** rc=0。R3 RECHECK：`-k sidecar_first` → **1 passed** rc=0。修法落點：`candidate_ledger.py:280-314` `_read_provenance_pairs`／`_read_ledger_pairs`／`provenance_reconcile` 逐 evaluation；`:373-381` `ledger_without_provenance` gate；`:200-202` docstring sidecar-first。`git diff fa8ef158..HEAD --stat -- momentum/ tests/` → 2 files +62/−21（白名單內）。

**來源摘要**: handoffs/reconcile/20260821-gap3-b4-review-r3/synth.md#41283fc7221b；momentum/Analysis/event_samples/candidate_ledger.py#dae0cf45a712；tests/momentum/event_samples/test_candidate_ledger.py#ab83ff44a969；handoffs/20260821-gap3-b4-review-r4-brief.md#3b71ddc12d2c；handoffs/run_receipts/20260821T163000Z-gap3-b4-r3-fix-gate.log

正文：閉合輪義務＝複核 codex R3 finding 是否 CLOSED ＋掃 R3 修補是否引入新問題；兩項皆通過。`_read_ledger_pairs` 與 GAP-1 讀口精神相容（同合法性判準、只讀、不產 N）。禁捏造湊數。

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——CODEX-R3-P1-01 複核同意 CLOSED；R3 修補（逐 evaluation 對帳＋`cid:eid` 差集＋缺 provenance fail-closed）未引入可證偽 P0–P2 新缺陷；brief assumed（`_read_ledger_pairs` 直讀可接受）攻擊不推翻。

**碼證**: `pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k sidecar_first` → **1 passed** rc=0；`pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` → **29 passed** rc=0；手跑 orphan→retry→缺 sidecar→仍遮掩失敗：`provenance_without_ledger=['a:eval-a']`、`ledger_without_provenance=['b:eval-b']`、`n_for_dsr` 不膨脹。修法落點：`candidate_ledger.py:280-314`／`:373-381`／`:200-202`。`git diff fa8ef158..HEAD --stat -- momentum/ tests/` → 2 files +61/−24（白名單內）。全套 224／GAP-1 272 引 `handoffs/run_receipts/20260821T163000Z-gap3-b4-r3-fix-gate.log`。

**來源摘要**: handoffs/20260821-gap3-b4-review-r4-brief.md#3b71ddc12d2c；handoffs/reconcile/20260821-gap3-b4-review-r3/synth.md#41283fc7221b；momentum/Analysis/event_samples/candidate_ledger.py#dae0cf45a712；tests/momentum/event_samples/test_candidate_ledger.py#ab83ff44a969；momentum/Analysis/strategy_validation/ledger.py#0322a1804784；docs/GAP3_EVENT_TODO.md#df04bdabf37d；handoffs/run_receipts/20260821T163000Z-gap3-b4-r3-fix-gate.log#3fca932ec537

正文：閉合輪義務＝複核 CODEX-R3-P1-01 是否 CLOSED ＋掃 R3 修補是否引入新問題；兩項皆通過。不受理 SPEC/TODO 重審／B5／GAP-1 本體／R1–R3 已裁 CLOSED 再議。禁捏造湊數。L240 `_provenance_complete` 註解名漂移僅記觀察。



## 戳記

（三家 RECONCILE-STAMP 蓋此區；body hash＝本區之前全文——reconcile_body_hash.sh）
RECONCILE-STAMP: grok APPROVED 2026-08-21 sha256:dfc4250e28fa11fec14198484bd15ad6e33c99ca9b26e62bd3c444227ee66723 task:20260821-GAP3-B4-STAMP-R1
RECONCILE-STAMP: composer APPROVED 2026-08-21 sha256:dfc4250e28fa11fec14198484bd15ad6e33c99ca9b26e62bd3c444227ee66723 task:20260821-GAP3-B4-STAMP-R1
RECONCILE-STAMP: codex APPROVED 2026-08-21 sha256:dfc4250e28fa11fec14198484bd15ad6e33c99ca9b26e62bd3c444227ee66723 task:20260821-GAP3-B4-STAMP-R1
