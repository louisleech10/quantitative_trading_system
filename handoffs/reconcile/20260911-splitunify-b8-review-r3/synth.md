# Reconcile — 20260911-splitunify-b8-review-r3

**來源** 20260911-splitunify-b8-review-r3-codex.md, 20260911-splitunify-b8-review-r3-composer.md, 20260911-splitunify-b8-review-r3-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

🔴 本輪**無實質 finding**，不改規格也不改碼。三家皆 `proceed`，各自閉合自家 R2 finding。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| 逐項核對後無 finding——「本輪逐項核對後無 finding。」 | P3 | CODEX-R3-P3-00 | 採納（sentinel；`CODEX-R2-P2-01` 已閉合） |
| 無需阻擋收案之新 finding——「本輪逐項核對後無需阻擋收案之新 P0／P1／P2 finding」 | P3 | COMPOSER-R3-P3-00 | 採納（sentinel；`COMPOSER-R2-P2-01` 已閉合；主動攻「第三個同型缺陷」未構造出實質漏洞） |
| 無 finding 且原提出方確認關閉——「本輪逐項核對後無 finding——`GROK-R2-P1-01` 已關閉」 | P3 | GROK-R3-P3-00 | 採納（sentinel；原提出方依章程 §B8 重跑自己的反例：adapter NaT 閘現拋 `AlignmentViolationError` 且訊息含 `NaT`；對缺 import／單路徑閘／golden 位移三面主動攻擊未再開洞） |

**b8 三輪審碼總結**：R1 codex `blocked`（兩條 P1＋一條 P2，主委獨立複驗全部成立）→ 修補 →
R2 三家一致再開一條（主委修補時引入的未匯入例外，依「分歧採較嚴版」以 P1 處理）→ 修補 →
R3 三家 `proceed` 且各自閉合。**沒有任何一條是靠「無 finding」停輪**，三輪皆有具名攻擊面。

**誠實邊界（收案說明必須帶）**：IC 端到端真實 run **未跑**，三輪三家皆同此限縮。
`M-SU-D1-23` 維持 `needs-research`（單標的 golden 下該 mutation 不可觸發，重凍成本大於收益）。

Verdict: 可合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P3-00

**斷言**: 本輪逐項核對後無 finding。

**碼證**: adapter NaT probe → `AlignmentViolationError`，訊息含 `NaT`；clean probe → `rows 12 has_row_pos True input_unchanged True`；同一 frame 的 `split_per_symbol` → `ValueError`，兩者皆 `ValueError` fail-closed。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b8-review-r2/synth.md#f9270e93c6c0; momentum/Analysis/ic_split_adapter.py#b05b0f73e417; momentum/core/contracts.py#1471cef968a3; tests/momentum/core/test_splitunify_producer_attest.py#fbe4779e8477

[P3] 信心度=High；R2 自家 finding `CODEX-R2-P2-01` 已閉合，adapter 現在回傳正確 typed exception，非 `NameError`。
主動攻擊面：同輸入比較 adapter 與 `split_per_symbol` 的錯誤處理；掃描 `split_cpcv`／`split_wf`／cross-sectional adapter／holdout／`split_per_symbol` 的 guard 覆蓋；對五個 b8 生產模組執行 `ruff check --select F821`，無未匯入名稱。
R2 閉合依據：3 條 targeted tests、adapter test file 5 tests、producer contract test file 24 tests 全部通過；`freeze_splitunify_golden.py` → `GOLDEN OK`。
數值輸出：R2 fix 的 production diff 僅新增一個既有 contracts exception import；`git diff --check 655d52d4^ 655d52d4` rc=0，未見 plan／schema／golden 位移。
ASSUMPTIONS_VERIFIED: typed exception inheritance、兩條 NaT producer 行為、所有 producer guard callsite、b8 生產檔 undefined-name scan、golden unchanged 均已由上述命令核對。
TESTS_RUN: `venv/bin/python -m pytest -q ...` → 3 passed；adapter suite → 5 passed；producer suite → 24 passed；`venv/bin/python scripts/freeze_splitunify_golden.py` → GOLDEN OK；ruff F821 → All checks passed。
FAILURES_SEEN: 初次反例 probe 因 `python -c` quoting 產生 SyntaxError；修正同一 probe 後 rc=0，輸出為 `AlignmentViolationError` 且 `is_alignment_violation True`、`has_nat True`。
SCOPE_CHANGES: none；遵守 brief「禁改碼」，僅新增本交件檔。
NUMERIC_OR_SCHEMA_IMPACT: none；未修改生產碼、測試斷言、plan schema 或輸出大小。
HANDOFF_PATH: handoffs/20260911-splitunify-b8-review-r3-codex.md
NEXT: 無；本家 R2 finding 可收案。
BLOCKED: none
DECISIONS: `CODEX-R2-P2-01` 判定 CLOSED；本輪以 sentinel 表示 0 個新 finding。
PITFALLS: 反例 probe 必須保留實際多行 Python 語法，避免把 `\\n` 傳成字面反斜線。

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R2-P2-01
STATUS: DONE
## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無需阻擋收案之新 P0／P1／P2 finding——`COMPOSER-R2-P2-01` 已閉合，且主動攻「第三個同型缺陷」未構造出實質漏洞。

**碼證**: ① R2 反例重跑（上節探針＋三條 NaT pytest）全符合預期。② AST `raise` 掃描 `ic_split_adapter.py`／`contracts.py`／`ic_filter_orchestrator.py`／`split_projection.py`／`split_preview.py`：唯一命中為 `ic_filter_orchestrator.py:3697` 之 `raise pending`（`pending` 為已捕獲之 `AlignmentViolationError` 實例，非未匯入類別）。③ 三 producer 閘對照：`split_per_symbol` NaT `:751-755`＋dtype `_assert_integer_ordinals`；adapter NaT `:194-198`＋dtype `:71-72,248-249`；orchestrator NaT `_normalize_ic_time_index :285-286`、plan 組裝 `:677` `attest_row_index_local`、labels NaT `:822-823`。④ 目標測試面 175 passed＋golden OK。

**來源摘要**: momentum/Analysis/ic_split_adapter.py#b05b0f73e417;handoffs/20260911-SPLITUNIFY-B8-REVIEW-R3-BRIEF.md#e8ac368e3762

P3 sentinel；信心度=High。誠實邊界：IC 端到端真實 run 未跑；adapter／`split_per_symbol` 例外型別差異為既有設計，非本輪新引入。

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——`GROK-R2-P1-01` 已關閉（adapter NaT 閘現拋 `AlignmentViolationError` 且訊息含 `NaT`），且對缺 import／單路徑閘／golden 位移三面主動攻擊未再開出新洞。

**碼證**: ①探針 `_with_row_positions(frame_with_nat)` → `AlignmentViolationError: …時間軸含 1 個 NaT…`（非 NameError）；`split_cpcv` 同。②`pytest tests/momentum/core/test_splitunify_producer_attest.py -q` → 24 passed。③`python scripts/freeze_splitunify_golden.py` → GOLDEN OK。④ast raise 掃描五檔無 missing import（orchestrator `raise pending` 為變數）。⑤`git show 655d52d4` 僅 `+ AlignmentViolationError` import＋兩測。RECHECK：重跑上列探針／三測／golden。

**來源摘要**: momentum/Analysis/ic_split_adapter.py#b05b0f73e417;tests/momentum/core/test_splitunify_producer_attest.py#fbe4779e8477;handoffs/20260911-SPLITUNIFY-B8-REVIEW-R3-BRIEF.md#0946a5e7ba12;handoffs/20260911-splitunify-b8-review-r2-grok.md#dddba28f06a2

[P3/sentinel] 信心度=High。零實質 finding；本條為停輪合法 sentinel，非湊數。

---

