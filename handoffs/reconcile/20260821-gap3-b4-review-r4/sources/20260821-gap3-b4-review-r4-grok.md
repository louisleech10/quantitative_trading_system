# GAP-3 B4 review R4 — grok（閉合輪／CODEX-R3-P1-01 複核＋sentinel）

task-id: 20260821-GAP3-B4-REVIEW-R4
family: grok
brief-kind: review
brief: handoffs/20260821-gap3-b4-review-r4-brief.md
R3 修補: `git diff fa8ef158..HEAD -- momentum/ tests/`（commit 39223d62；2 files +61/−24）
R3 裁決: handoffs/reconcile/20260821-gap3-b4-review-r3/synth.md
修後 Gate receipt: handoffs/run_receipts/20260821T163000Z-gap3-b4-r3-fix-gate.log

## Verdict：可進三家 RECONCILE-STAMP（CODEX-R3-P1-01 複核同意 CLOSED；本輪無新 finding）

### 必答

1. **CODEX-R3-P1-01 複核（grok）**

   | ID | 複核 | 本輪碼證摘要 |
   |---|---|---|
   | CODEX-R3-P1-01 | **同意 CLOSED** | `provenance_reconcile` L299–314 改逐 `(candidate_id, evaluation_id)`：`_read_ledger_pairs`／`_read_provenance_pairs`；差集值為 `cid:eid`；`complete`＝`lr.status=="ok"` 且帳本 pairs 非空且 ⊆ sidecar。`run_dsr_pbo` L373–381：任一帳本 evaluation 缺 provenance ⇒ `unavailable:provenance_incomplete`。`-k sidecar_first` → **1 passed** rc=0。手跑：orphan 後 `provenance_without_ledger=['a:eval-a']`；`eval-a-retry` 入帳後孤兒仍列、`complete=True`、`n_for_dsr=1`、`capability_status=ok`；`b:eval-b` 缺 sidecar 時即使 `eval-b2` 齊備仍 `ledger_without_provenance=['b:eval-b']`／`reason=provenance_incomplete`。 |

2. **修補是否引入新問題？**

   **無（P0–P2）**。逐項：
   - **`_read_ledger_pairs` vs「`read_trial_ledger` 唯一讀口」精神（brief assumed）**：攻擊不推翻——見下表。`LedgerReadResult` 只暴露 `candidate_ids`，對帳必須列級 pairs；`_read_ledger_pairs` 沿用 `load_strategy_validation_contract`＋`_row_is_valid`＋ session/dataset 過濾（L286–296；對照 `ledger.py:250-255`），只讀不寫、不產 N。`run_dsr_pbo` 的 N／capability 仍只經 `read_trial_ledger`（L356–361）；`provenance_reconcile` 亦仍取 `lr.status`（L303）。
   - **無 flock 直讀**：`_jsonl_rows` 與 sidecar 同路徑直讀；對帳為診斷／閘門讀，非 append hot path；並行半列風險與舊 sidecar 讀法同級——不升格 finding。
   - **docstring（R3 MINOR）**：L200–202 已改 sidecar-first，與實作／註解 L239 一致。
   - **觀察（非 finding）**：L240 行內註仍寫 `_provenance_complete`（函式名已不存在，實為 `provenance_reconcile`）——文檔漂移，禁湊數不升格。

3. **B4 Gate 複驗 rc=0？可進 stamp？**

   **可以（grok 本輪 APPROVED）**——本輪複驗 `-k "pattern_bridge or candidate_ledger"` → **29 passed** rc=0；`-k sidecar_first` → **1 passed** rc=0。前提：同輪 codex 原提出方標 CLOSED、composer 複核同意、三家無新 BLOCKING。event_samples 全套 224／GAP-1 272 引修後 receipt（本輪未並行重跑全套）。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：對帳讀帳本檔（非經 `read_trial_ledger`）可接受——`LedgerReadResult` 不暴露 evaluation_id；不改 GAP-1 簽名 | **成立（攻擊不推翻）** | 手跑：`n_for_dsr` 仍＝unique candidates（retry 後 N=1；加 b 後 N=2），pairs＝`a:eval-a-retry`／`b:eval-b`／`b:eval-b2`——N 路徑與對帳路徑分離。碼證：`_read_ledger_pairs` 與 `read_trial_ledger` 同 `_row_is_valid`；DSR/PBO 入口仍只呼叫 `read_trial_ledger`。若不允許直讀 pairs，則必須擴 `LedgerReadResult`（改 GAP-1 簽名）——brief 明確不受理。 |
| fact-verified: 修後 Gate 29／event_samples 224／GAP-1 272 | **本輪 Gate＋sidecar 複驗成立；後二者引 receipt** | 本輪：29 passed rc=0；sidecar_first 1 passed rc=0；receipt `20260821T163000Z-…` 載 `rc_gate=0`（29）／`rc_event_samples_all=0`（224）／`rc_gap1=0`（272） |

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——CODEX-R3-P1-01 複核同意 CLOSED；R3 修補（逐 evaluation 對帳＋`cid:eid` 差集＋缺 provenance fail-closed）未引入可證偽 P0–P2 新缺陷；brief assumed（`_read_ledger_pairs` 直讀可接受）攻擊不推翻。

**碼證**: `pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k sidecar_first` → **1 passed** rc=0；`pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` → **29 passed** rc=0；手跑 orphan→retry→缺 sidecar→仍遮掩失敗：`provenance_without_ledger=['a:eval-a']`、`ledger_without_provenance=['b:eval-b']`、`n_for_dsr` 不膨脹。修法落點：`candidate_ledger.py:280-314`／`:373-381`／`:200-202`。`git diff fa8ef158..HEAD --stat -- momentum/ tests/` → 2 files +61/−24（白名單內）。全套 224／GAP-1 272 引 `handoffs/run_receipts/20260821T163000Z-gap3-b4-r3-fix-gate.log`。

**來源摘要**: handoffs/20260821-gap3-b4-review-r4-brief.md#3b71ddc12d2c；handoffs/reconcile/20260821-gap3-b4-review-r3/synth.md#41283fc7221b；momentum/Analysis/event_samples/candidate_ledger.py#dae0cf45a712；tests/momentum/event_samples/test_candidate_ledger.py#ab83ff44a969；momentum/Analysis/strategy_validation/ledger.py#0322a1804784；docs/GAP3_EVENT_TODO.md#df04bdabf37d；handoffs/run_receipts/20260821T163000Z-gap3-b4-r3-fix-gate.log#3fca932ec537

正文：閉合輪義務＝複核 CODEX-R3-P1-01 是否 CLOSED ＋掃 R3 修補是否引入新問題；兩項皆通過。不受理 SPEC/TODO 重審／B5／GAP-1 本體／R1–R3 已裁 CLOSED 再議。禁捏造湊數。L240 `_provenance_complete` 註解名漂移僅記觀察。

## 被當成事實的未驗證假設（§0）

無新增；brief 一條 assumed 已攻擊（上表）。

ASSUMPTIONS_VERIFIED: CODEX-R3-P1-01 修補落地（逐 evaluation pairs＋fail-closed）；`_read_ledger_pairs` 與 `read_trial_ledger` 同合法性判準且不產 N；orphan 不膨脹 N；B4 Gate 29 綠
TESTS_RUN: `pytest … -k sidecar_first` → 1 passed rc=0；`-k "pattern_bridge or candidate_ledger"` → 29 passed rc=0；手跑 orphan/retry/缺 sidecar 探針如上；224／272 引 `20260821T163000Z-gap3-b4-r3-fix-gate.log`
FAILURES_SEEN: 初次手跑缺 `t_semantics` attrs（MetricTypeError），未改碼；改用測試 `_cand`／`_meta` 後探針成功
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接 append）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；`n_ledger_evaluations`／`n_provenance_rows`／`cid:eid` 為 R3 修補預期 schema，消費端已測）
OUTPUT: handoffs/20260821-gap3-b4-review-r4-grok.md

STATUS: DONE
