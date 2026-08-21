# GAP-3 B4 review R3 — composer（閉合輪／sentinel 複核）

task-id: 20260821-GAP3-B4-REVIEW-R3  
family: composer  
brief-kind: review  
brief: handoffs/20260821-gap3-b4-review-r3-brief.md  
patch: `git diff 57abce9d..HEAD -- momentum/ tests/`  
R2 裁決: handoffs/reconcile/20260821-gap3-b4-review-r2/synth.md

## Verdict：可進三家 RECONCILE-STAMP（CODEX-R2 兩條複核同意 CLOSED；本輪無新 finding）

### 必答

1. **CODEX-R2 兩條 CLOSED／OPEN（composer 複核）**

   | ID | codex 處置（本輪應 CLOSED） | composer 複核 | RECHECK 摘要 |
   |---|---|---|---|
   | CODEX-R2-P1-01 | **CLOSED**（sidecar 先、帳本後；`provenance_reconcile`；`ledger_without_provenance` ⇒ unavailable） | **複核同意 CLOSED** | `pytest … -k sidecar_first` → **1 passed** rc=0；①帳本 append 失敗 ⇒ 帳本無列、sidecar 孤兒、`ledger.status=unavailable`（N 不變）；②繞過寫帳本無 sidecar ⇒ `provenance_incomplete`；③正常路徑 `complete=True` |
   | CODEX-R2-P1-02 | **CLOSED**（`receipt_digest`；`_assert_return_series` 重算比對 stale receipt） | **複核同意 CLOSED** | `pytest … -k stale_receipt` → **1 passed** rc=0；真實 kline `to_return_series` copy 後 `iloc[0]+=0.123` ⇒ `MetricTypeError(stale)`；改 index 亦拒；未改者通過 |

2. **修補新引入問題？**

   **無**（見 sentinel `COMPOSER-R3-P3-00`）。專項攻擊：
   - **provenance 孤兒（sidecar 有、帳本無）**：`read_trial_ledger` 只讀帳本 ⇒ N 不受影響（測試 ① 斷言 `ledger.status=unavailable`）；`provenance_reconcile` 可列 `provenance_without_ledger`；`run_dsr_pbo` 僅對 `ledger_without_provenance` fail-closed，孤兒不阻擋合法 run——與 brief assumed 一致，攻擊不推翻。
   - **`receipt_digest` `float(v)` 穩定性**：`to_return_series` 產出後 `receipt_digest(out)==source_artifact_hash`（`test_stale_receipt` 首行）；五語意 `test_to_return_series_hand_exact_each_entry_semantic` 全綠。
   - **digest 重算成本**：`_assert_return_series` 多一次 `receipt_digest`（O(n) hash）；候選集規模下可接受，非 perf blocker。
   - **docstring 漂移**：`record_candidate` docstring `:200-201` 仍寫「帳本先、sidecar 後」與實作相反——**MINOR 文檔不一致**，不影響行為，非 P0–P2。

3. **B4 Gate 複驗 rc=0？可進 stamp？**

   **是（composer 本輪 APPROVED）**——`-k "pattern_bridge or candidate_ledger"` **29 passed** rc=0；event_samples 全套 **224 passed**；GAP-1 strategy_validation **272 passed**（見 VERIFY）。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：provenance 孤兒（sidecar 有、帳本無）不需清理——不影響 N，且 `provenance_reconcile` 可列出供人工對帳 | **成立（攻擊不推翻）** | `test_sidecar_first` ①：`append_trial_attempt` 失敗後帳本檔不存在、`provenance_without_ledger==["a"]`、`run_dsr_pbo` 之 `ledger.status=unavailable`；`provenance_reconcile` 回傳三鍵可機械對帳。重試同 `evaluation_id` 只追加 sidecar 列、`_read_provenance` 用 set 去重——不膨脹 N。 |
| **fact-verified**（brief）：修後 B4 Gate 29 passed、event_samples 224、GAP-1 272 | **本輪複驗一致** | 見 VERIFY；與 `handoffs/run_receipts/20260821T160000Z-gap3-b4-r2-fix-gate.log` 計數對齊（27→29 因新增 2 條 R2 RECHECK 測試）。 |

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——CODEX-R2-P1-01／P1-02 修補逐碼對齊且 RECHECK 全綠；composer 複核同意兩條 CLOSED；修補未引入可證偽 P0–P2 缺陷；brief assumed（provenance 孤兒邊界）攻擊不推翻。

**碼證**: B4 Gate：`-k "pattern_bridge or candidate_ledger"` → **29 passed** rc=0；event_samples 全套 → **224 passed** rc=0；strategy_validation → **272 passed** rc=0。R2 RECHECK：`-k "sidecar_first or stale_receipt"` → **2 passed** rc=0。修法落點：`candidate_ledger.py:238-254` sidecar 先寫；`:281-295` `provenance_reconcile`；`:350-358` `ledger_without_provenance` gate；`:99-112` `receipt_digest`＋stale 比對；`:190` `to_return_series` 綁 digest。`git diff 57abce9d..HEAD --stat -- momentum/ tests/` → 2 files +117/−10（白名單內）。

**來源摘要**: handoffs/reconcile/20260821-gap3-b4-review-r2/synth.md#Y2Y3；momentum/Analysis/event_samples/candidate_ledger.py#f4120b45d535；tests/momentum/event_samples/test_candidate_ledger.py#209e433c；handoffs/20260821-gap3-b4-review-r3-brief.md；handoffs/run_receipts/20260821T160000Z-gap3-b4-r2-fix-gate.log

正文：閉合輪義務＝複核 codex 兩條 R2 finding 是否 CLOSED ＋掃修補是否引入新問題；兩項皆通過。`record_candidate` docstring 與實作寫入順序不一致為 MINOR 文檔漂移，不升格 finding。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief assumed（provenance 孤兒邊界）已攻擊（上表）。

## VERIFY（本輪複驗）

```
venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k "sidecar_first or stale_receipt" → 2 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger" → 29 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 224 passed rc=0
venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation -q → 272 passed rc=0
git diff 57abce9d..HEAD --stat -- momentum/ tests/ → candidate_ledger.py +tests 白名單內
```

ASSUMPTIONS_VERIFIED: 上述命令＋`candidate_ledger.py` R2 修法區段對讀＋`git diff 57abce9d..HEAD`  
TESTS_RUN: 見 VERIFY  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only；禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（消費端新增 `provenance_reconcile` 報告欄；既有 schema 不變）  
OUTPUT: handoffs/20260821-gap3-b4-review-r3-composer.md  
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

STATUS: DONE
