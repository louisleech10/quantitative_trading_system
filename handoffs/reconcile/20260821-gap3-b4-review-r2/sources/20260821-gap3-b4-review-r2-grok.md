# GAP-3 B4 review R2 — grok（閉合輪／sentinel）

task-id: 20260821-GAP3-B4-REVIEW-R2
family: grok
brief-kind: review
brief: handoffs/20260821-gap3-b4-review-r2-brief.md
patch: `git diff e9e0257c..HEAD -- momentum/ tests/`（commit 57abce9d「B4 review R1 八條全修」）
R1 裁決: handoffs/reconcile/20260821-gap3-b4-review-r1/synth.md
修後 Gate receipt: handoffs/run_receipts/20260821T153000Z-gap3-b4-r1-fix-gate.log

## Verdict：可進三家 RECONCILE-STAMP（本家 2/2 CLOSED；本輪無新 finding）

### 必答

1. **己方 R1 各條 CLOSED／OPEN（附重跑輸出）**  
   | ID | 處置 | 本輪碼證摘要 |
   |---|---|---|
   | GROK-R1-P1-01 | **CLOSED** | `run_dsr_pbo` 聯集軸 `sorted(key=(entry_at_ms, id))`；`to_return_series` attrs 寫 `entry_at_ms_by_event`；跨候選時間戳衝突 ⇒ ValueError；`observation_axis` 字面＋`observation_axis_first_last_entry_ms`；`-k pbo_observation_axis` → **1 passed**（evt_10 最早列 0；字串序相反仍時間序；spy 擷取 M） |
   | GROK-R1-P2-01 | **CLOSED** | `_assert_return_series` 驗收據 attrs 全齊（t_semantics／entry_semantic／label_definition／64hex hash／span_years>0／entry_at 覆蓋 index）＋n≥2；`-k "disguised or auc_fed"` → **2 passed**（`[0.9,0.85,0.72]`／`name="score"`／單一值皆 MetricTypeError） |

2. **修補是否引入新問題？**  
   **無**（見 sentinel `GROK-R2-P3-00`）。manifest 必填：`extract_event_patterns` 無測試外 caller；`-k manifest_required` 綠且 `n_events_raw=400`。收據 attrs 閘：`test_to_return_series_hand_exact_*` 五語意仍綠（未誤拒真實產出）。候選集全等：子集評估路徑刻意不支援（synth X4／brief 明列）；logged/unlogged 反例 DSR unavailable。

3. **B4 Gate 複驗 rc=0？可進 stamp？**  
   **可以（grok 本輪 APPROVED）**——本輪複驗 `-k "pattern_bridge or candidate_ledger"` → **27 passed** rc=0。前提：同輪 codex／composer 對其原 finding 亦 CLOSED 且無新 BLOCKING。event_samples 全套／GAP-1 272 引修後 receipt（本輪未並行重跑全套，以免與他家族衝突）；本輪另抽驗他家 RECHECK 捆 8 passed。

### R1 閉合逐條（原提出方重跑）

**Closure P1-01（原 ID GROK-R1-P1-01）— CLOSED**
- 碼：`candidate_ledger.py` `to_return_series` L181 寫 `entry_at_ms_by_event`；`run_dsr_pbo` L343–366 依 `(entry_at, id)` 建 union、衝突 fail-closed、揭露 `observation_axis_first_last_entry_ms`。
- 測：`venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k pbo_observation_axis` → **1 passed** rc=0。
- 原反例對碼：ids=`evt_10…evt_1`（時間序≠字串序）⇒ `M[:,0]` 對齊時間序；`first_last_entry_ms=[entry[evt_10], entry[evt_1]]`。

**Closure P2-01（原 ID GROK-R1-P2-01）— CLOSED**
- 碼：`_assert_return_series` L71–98 改驗 `_RECEIPT_ATTRS` 全齊＋n≥2（非僅 metric_kind／name 禁名單）。
- 測：`-k "disguised or auc_fed"` → **2 passed** rc=0。
- 原反例對碼：缺 attrs 之 `[0.9,0.85,0.72]`／`name="score"`／單值 ⇒ `MetricTypeError`（閘層拒，非後段退化）。

### 他家 R1 條目（複核同意／異議）

| ID | 複核 | 證據摘要 |
|---|---|---|
| CODEX-R1-P1-01 | **同意 CLOSED** | `-k manifest_required` 綠；手跑 `common.n_events_raw==400`／`effective==400`；缺 keyword／None／空 table／無 n 欄皆拒 |
| CODEX-R1-P1-02 | **同意 CLOSED** | `-k "unlogged_candidate or record_guards"`；logged/unlogged 借 hash ⇒ DSR／eligibility unavailable＋`candidate_set_mismatch` |
| CODEX-R1-P1-03 | **同意 CLOSED** | 與 GROK-R1-P1-01 同修；`-k pbo_observation_axis` 綠 |
| CODEX-R1-P1-04 | **同意 CLOSED** | `-k requires_command_and_expected`；缺 command／expected 拒後帳本目錄空；sidecar 於 `_ledger_lock` append |
| COMPOSER-R1-P1-01 | **同意 CLOSED** | 與 GROK-R1-P2-01 同修；`-k disguised` 綠 |
| COMPOSER-R1-P2-02 | **同意 CLOSED** | 與 GROK-R1-P1-01 同修；`-k pbo_observation_axis` 綠 |

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：帳本與 sidecar 非同一交易；順序「全驗→帳本→sidecar」＋sidecar 失敗 raise 為可接受誠實邊界（不改 GAP-1） | **成立（攻擊不推翻）** | 手跑：ledger append 後毒化 provenance path 為目錄 ⇒ `IsADirectoryError` raise；ledger 已有 orphan 列（`n_for_dsr=2`、candidates=`[a,b]`）、sidecar 僅 a。後續：只餵 `{a}` ⇒ `universe_provenance_unverifiable`（集不等強迫暴露）；餵 `{a,b}` 可 DSR ok（N 含無 sidecar 之 orphan）。B4 已 raise＋集全等；補償刪列／跨檔交易需改 GAP-1（brief 不受理）。殘差＝呼叫端須對帳 `evaluation_id`——已於 docstring 誠實邊界寫明。 |
| **assumed**：收據 attrs 閘擋疏忽／誤標即達 K6/C7「機械拒」；蓄意偽造 attrs 不在受理（95% 解法） | **成立（攻擊不推翻）** | 疏忽路徑：僅 `span_years` 之分數數列 ⇒ `MetricTypeError`（缺收據鍵）。蓄意路徑：手填齊全 `_RECEIPT_ATTRS`＋類 AUC 值 ⇒ `_assert_return_series` **仍 ACCEPTED**（與 R1 synth X2／本 brief 誠實邊界一致）。不另開 finding。 |
| fact-verified: 修後 Gate 27／event_samples 222／GAP-1 272 | **本輪 Gate 複驗成立；後二者引 receipt** | 本輪：`-k "pattern_bridge or candidate_ledger"` 27 passed rc=0；receipt `20260821T153000Z-…` 載 `rc_event_samples_all=0`（222）／`rc_gap1=0`（272） |

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——GROK-R1-P1-01／P2-01 兩條原反例均 CLOSED；八條 R1 修補未引入可證偽 P0–P2 新缺陷；brief 兩條 assumed（非原子 sidecar／蓄意偽造 attrs）攻擊不推翻。

**碼證**: `pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` → **27 passed** rc=0；`-k pbo_observation_axis` → 1 passed；`-k "disguised or auc_fed"` → 2 passed；`-k manifest_required` → 1 passed 且手跑 `n_events_raw=400`；`-k "unlogged_candidate or record_guards or requires_command or hand_exact"` → **8 passed**；手跑疏忽分數拒／偽造 attrs 仍過（誠實邊界）；手跑 sidecar 失敗 orphan＋集不等拒；`git diff e9e0257c..HEAD --stat -- momentum/ tests/` → 4 files +198/−47（白名單內）。全套 222／GAP-1 272 引 receipt，本輪未並行重跑。

**來源摘要**: handoffs/reconcile/20260821-gap3-b4-review-r1/synth.md#dbfe6fe45b91；handoffs/20260821-gap3-b4-review-r1-grok.md#e3cc1be68e18；handoffs/20260821-gap3-b4-review-r2-brief.md#839fc031c057；momentum/Analysis/event_samples/candidate_ledger.py#a825e470d626；momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2；tests/momentum/event_samples/test_candidate_ledger.py#79411209968d；tests/momentum/event_samples/test_pattern_bridge.py#ebe6d74f9965；docs/GAP3_EVENT_TODO.md#df04bdabf37d；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；handoffs/run_receipts/20260821T153000Z-gap3-b4-r1-fix-gate.log#6a2b11e7af20

正文：閉合義務兩條全 CLOSED；§0 assumed 已攻；不受理 SPEC/TODO 重審／B5／GAP-1 本體／R1 已裁成立前提再議。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief 兩條 assumed 已攻擊（上表）。

ASSUMPTIONS_VERIFIED: GROK 兩條 R1 修補落地（PBO entry 時間軸＋收據 attrs 型別閘）；manifest 必填無外 caller；hand_exact 未誤拒；候選集全等 logged/unlogged 拒；command/expected 寫前先驗；兩條 brief assumed 攻擊不推翻；B4 Gate 27 綠
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` → 27 passed rc=0；`-k pbo_observation_axis` → 1 passed；`-k "disguised or auc_fed"` → 2 passed；`-k manifest_required` → 1 passed；`-k "unlogged_candidate or record_guards or requires_command or hand_exact"` → 8 passed；手跑 n_events_raw=400／疏忽拒／偽造過／orphan sidecar；222／272 引 `20260821T153000Z-gap3-b4-r1-fix-gate.log`
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接 append）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260821-gap3-b4-review-r2-grok.md
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護；執行端交接 append 至 `handoffs/20260821-GAP3-B4-REVIEW-R2.md`

STATUS: DONE
