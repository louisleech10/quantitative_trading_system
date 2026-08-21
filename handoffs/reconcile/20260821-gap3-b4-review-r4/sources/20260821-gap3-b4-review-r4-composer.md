# GAP-3 B4 review R4 — composer（閉合輪／CODEX-R3-P1-01 複核＋sentinel）

task-id: 20260821-GAP3-B4-REVIEW-R4  
family: composer  
brief-kind: review  
brief: handoffs/20260821-gap3-b4-review-r4-brief.md  
patch: `git diff fa8ef158..HEAD -- momentum/ tests/`  
R3 裁決: handoffs/reconcile/20260821-gap3-b4-review-r3/synth.md

## Verdict：可進三家 RECONCILE-STAMP（CODEX-R3-P1-01 複核同意 CLOSED；本輪無新 finding）

### 必答

1. **CODEX-R3-P1-01 CLOSED／OPEN（composer 複核）**

   | ID | codex 處置（本輪應 CLOSED） | composer 複核 | RECHECK 摘要 |
   |---|---|---|---|
   | CODEX-R3-P1-01 | **CLOSED**（`provenance_reconcile` 改逐 `(candidate_id, evaluation_id)`；`_read_ledger_pairs`／`_read_provenance_pairs`；`ledger_without_provenance`／`provenance_without_ledger` 值為 `cid:eid`；`complete`＝帳本 pairs 非空且 ⊆ sidecar；`run_dsr_pbo` 任一帳本 evaluation 缺 provenance ⇒ `unavailable:provenance_incomplete`） | **複核同意 CLOSED** | `pytest … -k sidecar_first` → **1 passed** rc=0；孤兒 `a:eval-a` 在 `eval-a-retry` 入帳後仍列出且 `complete=True`；`b:eval-b` 缺 sidecar 時即使 `eval-b2` 齊備仍 `provenance_incomplete` 且 `ledger_without_provenance==["b:eval-b"]`；補 sidecar 後 `capability_status=ok` |

2. **修補是否引入新問題？**

   **無**（見 sentinel `COMPOSER-R4-P3-00`）。專項攻擊 brief assumed：
   - **`_read_ledger_pairs` 直接讀帳本 vs `read_trial_ledger` 唯一讀口**：可接受。`LedgerReadResult` 只暴露 `candidate_ids`（set），對帳需 evaluation 粒度；`_read_ledger_pairs` 沿用 `load_strategy_validation_contract`＋`_row_is_valid`＋ session/dataset 過濾（`:286-296`），與 `ledger.py:250-255` 同判準、只讀不寫、不產 N。`provenance_reconcile` 仍呼叫 `read_trial_ledger` 取 `ledger_status`（`:303`），N 與 capability 路徑不繞過 GAP-1 讀口。
   - **docstring 漂移（R3 MINOR）**：`:200-202` 已改為 sidecar 先、帳本後，與實作一致。
   - **無 flock 直讀**：sidecar 側 `_jsonl_rows` 亦直讀；對帳為診斷路徑、非 append hot path；不升格 P0–P2。

3. **B4 Gate 複驗 rc=0？可進 stamp？**

   **是（composer 本輪 APPROVED）**——`-k "pattern_bridge or candidate_ledger"` **29 passed** rc=0；event_samples 全套 **224 passed**；GAP-1 strategy_validation **272 passed**（見 VERIFY）。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：`_read_ledger_pairs` 直讀帳本可接受——`LedgerReadResult` 不暴露 evaluation_id，對帳需列級 pairs | **成立（攻擊不推翻）** | 逐碼對照 `ledger.py:250-255` 與 `candidate_ledger.py:288-295` 同 `_row_is_valid`＋session 過濾；`run_dsr_pbo` N 仍只經 `read_trial_ledger`（`:356-361`）；測試 ①–③ 覆蓋 orphan／缺 sidecar／補齊路徑 |
| **fact-verified**（brief）：修後 B4 Gate 29 passed、event_samples 224、GAP-1 272 | **本輪複驗一致** | 見 VERIFY；與 `handoffs/run_receipts/20260821T163000Z-gap3-b4-r3-fix-gate.log` 計數對齊 |

## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——CODEX-R3-P1-01 修補逐碼對齊且 RECHECK 全綠；composer 複核同意 CLOSED；R3 修補未引入可證偽 P0–P2 缺陷；brief assumed（`_read_ledger_pairs` 直讀可接受）攻擊不推翻。

**碼證**: B4 Gate：`-k "pattern_bridge or candidate_ledger"` → **29 passed** rc=0；event_samples 全套 → **224 passed** rc=0；strategy_validation → **272 passed** rc=0。R3 RECHECK：`-k sidecar_first` → **1 passed** rc=0。修法落點：`candidate_ledger.py:280-314` `_read_provenance_pairs`／`_read_ledger_pairs`／`provenance_reconcile` 逐 evaluation；`:373-381` `ledger_without_provenance` gate；`:200-202` docstring sidecar-first。`git diff fa8ef158..HEAD --stat -- momentum/ tests/` → 2 files +62/−21（白名單內）。

**來源摘要**: handoffs/reconcile/20260821-gap3-b4-review-r3/synth.md#41283fc7221b；momentum/Analysis/event_samples/candidate_ledger.py#dae0cf45a712；tests/momentum/event_samples/test_candidate_ledger.py#ab83ff44a969；handoffs/20260821-gap3-b4-review-r4-brief.md#3b71ddc12d2c；handoffs/run_receipts/20260821T163000Z-gap3-b4-r3-fix-gate.log

正文：閉合輪義務＝複核 codex R3 finding 是否 CLOSED ＋掃 R3 修補是否引入新問題；兩項皆通過。`_read_ledger_pairs` 與 GAP-1 讀口精神相容（同合法性判準、只讀、不產 N）。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief assumed（對帳直讀帳本）已攻擊（上表）。

## VERIFY（本輪複驗）

```
venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k sidecar_first → 1 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger" → 29 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 224 passed rc=0
venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation -q → 272 passed rc=0
git diff fa8ef158..HEAD --stat -- momentum/ tests/ → candidate_ledger.py +tests 白名單內
```

ASSUMPTIONS_VERIFIED: 上述命令＋`candidate_ledger.py:280-381` 對讀＋`ledger.py:250-255` 判準對照＋`git diff fa8ef158..HEAD`  
TESTS_RUN: 見 VERIFY  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only；禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（`provenance_reconcile` 輸出鍵 `n_ledger_evaluations`／`n_provenance_rows` 與 `cid:eid` 格式為 R3 修補預期；消費端已測）  
OUTPUT: handoffs/20260821-gap3-b4-review-r4-composer.md  
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

STATUS: DONE
