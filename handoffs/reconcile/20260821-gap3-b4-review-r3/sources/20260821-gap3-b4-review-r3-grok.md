# GAP-3 B4 review R3 — grok（閉合輪／複核＋sentinel）

task-id: 20260821-GAP3-B4-REVIEW-R3
family: grok
brief-kind: review
brief: handoffs/20260821-gap3-b4-review-r3-brief.md
R2 修補: `git diff 57abce9d..HEAD -- momentum/ tests/`（commit fa8ef158；2 files +129/−13）
R2 裁決: handoffs/reconcile/20260821-gap3-b4-review-r2/synth.md
修後 Gate receipt: handoffs/run_receipts/20260821T160000Z-gap3-b4-r2-fix-gate.log

## Verdict：可進三家 RECONCILE-STAMP（CODEX-R2 兩條複核同意 CLOSED；本輪無新 finding）

### 必答

1. **CODEX-R2-P1-01／P1-02 複核（grok）**  
   | ID | 複核 | 本輪碼證摘要 |
   |---|---|---|
   | CODEX-R2-P1-01 | **同意 CLOSED** | `record_candidate` L238–254：**sidecar 先、帳本後**；`provenance_reconcile` L281–292 回 `ledger_without_provenance`／`provenance_without_ledger`／`complete`；`run_dsr_pbo` L350–359 於候選集檢查前對帳，帳本候選缺 sidecar ⇒ `unavailable:provenance_incomplete`（dsr/pbo/eligibility 皆 unavailable）且報告附 `provenance_reconcile`。`-k sidecar_first` → **1 passed**：①帳本 append 失敗 ⇒ 帳本檔不存在、provenance 孤兒、`run` ledger unavailable；②帳本有列無 sidecar ⇒ `provenance_incomplete`；③齊備 ⇒ ok。手跑 orphan：`n_for_dsr=0`、`candidate_ids=[]`。 |
   | CODEX-R2-P1-02 | **同意 CLOSED** | `receipt_digest` L107–112＝sha256(index＋values＋entry_semantic＋label_definition)；`to_return_series` L190 寫入；`_assert_return_series` L99–100 重算比對，不符 ⇒ `MetricTypeError(stale receipt)`。`-k stale_receipt` → **1 passed**：真實 kline 產出通過；`copy` 後 `iloc[0]+=0.123`／改 index 皆拒（`record_candidate` 與 `run_dsr_pbo`）。 |

2. **修補是否引入新問題？**  
   **無（P0–P2）**。逐項：  
   - **provenance 孤兒 vs N**：assumed 攻擊後仍成立——`read_trial_ledger` 只讀帳本 JSONL（`ledger.py:202+`）；sidecar 有、帳本無時 `n_for_dsr=0`、capability unavailable；不膨脹 N。`provenance_reconcile` 可列出 `provenance_without_ledger` 供人工對帳。  
   - **`float(v)` 序列化穩定**：`receipt_digest` roundtrip `digest_stable True`；`-k hand_exact` → **5 passed**（五種 entry 語意 exact 仍綠，未誤拒真實產出）。  
   - **digest 重算成本**：僅消費閘（record／run）對整條 series 做一次 json＋sha256；候選數與交易數為事件級，可接受。  
   - **文件滯後（非 finding）**：`record_candidate` docstring L200–201 仍寫舊順序「帳本→sidecar」與舊誠實邊界；實作與 L238 註解已改 sidecar-first。執行期行為與測試正確；本輪不另開 finding（禁湊數；非 runtime 缺陷）。

3. **B4 Gate 複驗 rc=0？可進 stamp？**  
   **可以（grok 本輪 APPROVED）**——本輪複驗 `-k "pattern_bridge or candidate_ledger"` → **29 passed** rc=0。前提：同輪 codex 原提出方標 CLOSED、composer 複核同意、三家無新 BLOCKING。event_samples 全套 224／GAP-1 272 引修後 receipt（本輪未並行重跑全套）。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：provenance 孤兒（sidecar 有、帳本無）不需清理——不影響 N，且 `provenance_reconcile` 可列出供人工對帳 | **成立（攻擊不推翻）** | 手跑：monkeypatch `append_trial_attempt` raise ⇒ sidecar 存在、ledger 檔不存在；`read_trial_ledger` → `status=unavailable`、`n_for_dsr=0`、`candidate_ids=[]`；`provenance_reconcile` → `provenance_without_ledger=['orphan_a']`、`complete=False`；`run_dsr_pbo` → ledger unavailable／`n_unknown`。pytest `-k sidecar_first` 同路徑綠。 |
| fact-verified: 修後 Gate 29／event_samples 224／GAP-1 272 | **本輪 Gate 複驗成立；後二者引 receipt** | 本輪：29 passed rc=0；receipt `20260821T160000Z-…` 載 `rc_gate=0`（29）／`rc_event_samples_all=0`（224）／後段 GAP-1 272 |

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——CODEX-R2-P1-01／P1-02 複核同意 CLOSED；R2 修補（sidecar-first＋receipt_digest 重算）未引入可證偽 P0–P2 新缺陷；brief assumed（provenance 孤兒不影響 N）攻擊不推翻。

**碼證**: `pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k "sidecar_first or stale_receipt"` → **2 passed** rc=0；`-k hand_exact` → **5 passed**；`pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` → **29 passed** rc=0；手跑 orphan ⇒ `n_for_dsr=0`／`provenance_without_ledger` 可列；`receipt_digest` roundtrip 穩定；`git diff 57abce9d..HEAD --stat -- momentum/ tests/` → 2 files +129/−13（白名單內）。全套 224／GAP-1 272 引 `handoffs/run_receipts/20260821T160000Z-gap3-b4-r2-fix-gate.log`。

**來源摘要**: handoffs/20260821-gap3-b4-review-r3-brief.md#3c0220b28f0c；handoffs/reconcile/20260821-gap3-b4-review-r2/synth.md#6ad894ac71a8；momentum/Analysis/event_samples/candidate_ledger.py#f4120b45d535；tests/momentum/event_samples/test_candidate_ledger.py#3ca3a00e1a69；docs/GAP3_EVENT_TODO.md#df04bdabf37d；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；handoffs/run_receipts/20260821T160000Z-gap3-b4-r2-fix-gate.log#88e34b6dbd13

正文：複核義務兩條全同意 CLOSED；§0 assumed 已攻；不受理 SPEC/TODO 重審／B5／GAP-1 本體／R1／R2 已裁 CLOSED 再議。禁捏造湊數。docstring L200–201 與實作順序不一致僅記觀察、不升 finding。

## 被當成事實的未驗證假設（§0）

無新增；brief 一條 assumed 已攻擊（上表）。

ASSUMPTIONS_VERIFIED: CODEX-R2 兩條修補落地（sidecar-first＋provenance_reconcile fail-closed；receipt_digest stale 拒）；孤兒不影響 N；float digest 對真實產出穩定；hand_exact 五語意仍綠；B4 Gate 29 綠
TESTS_RUN: `pytest … -k "sidecar_first or stale_receipt"` → 2 passed rc=0；`-k hand_exact` → 5 passed；`-k "pattern_bridge or candidate_ledger"` → 29 passed rc=0；手跑 orphan N=0／digest roundtrip；224／272 引 `20260821T160000Z-gap3-b4-r2-fix-gate.log`
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接 append）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260821-gap3-b4-review-r3-grok.md

STATUS: DONE
