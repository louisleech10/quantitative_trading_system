# GAP-3 B4 review R2 — composer（closure／sentinel）

task-id: 20260821-GAP3-B4-REVIEW-R2  
family: composer  
brief-kind: review  
brief: handoffs/20260821-gap3-b4-review-r2-brief.md  
patch: `git diff e9e0257c..HEAD -- momentum/ tests/`  
R1 裁決: handoffs/reconcile/20260821-gap3-b4-review-r1/synth.md

## Verdict：可進三家 RECONCILE-STAMP（本家 2/2 CLOSED；本輪無新 finding）

### 必答

1. **原提出方逐條 CLOSED？**  
   | ID | 處置 | 本輪碼證摘要 |
   |---|---|---|
   | COMPOSER-R1-P1-01 | **CLOSED** | `candidate_ledger.py:68-98` `_assert_return_series` 驗 `_RECEIPT_ATTRS` 全齊＋n≥2；`-k "disguised or auc_fed"` → **2 passed** rc=0；inline 探針 `[0.9,0.85,0.72]`＋僅 `span_years` attrs ⇒ `MetricTypeError`（缺收據鍵） |
   | COMPOSER-R1-P2-02 | **CLOSED** | `candidate_ledger.py:343-366` 聯集軸 `sorted(key=(entry_at[e], e))`＋`observation_axis_first_last_entry_ms`；`-k pbo_observation_axis` → **1 passed** rc=0（evt_10 最早、字串序相反 ⇒ 矩陣列仍時間序；spy 擷取 `returns_matrix` 對齊） |

2. **修補新引入問題？**  
   **無**（見 sentinel `COMPOSER-R2-P3-00`）。`manifest=` 必填未破壞 caller（repo 內 `extract_event_patterns` 僅 B4 測試呼叫，皆帶 manifest）；`test_to_return_series_hand_exact_each_entry_semantic` 五語意仍綠；候選集 `frozenset` 全等為刻意設計（子集評估不支援，synth 明列）。

3. **B4 Gate 複驗 rc=0？可進 stamp？**  
   **是（composer 本輪 APPROVED）**——`-k "pattern_bridge or candidate_ledger"` **27 passed** rc=0；event_samples 全套 **222 passed**；GAP-1 strategy_validation **272 passed**（見 VERIFY）。

### 他方 R1 複核（非原提出方）

| ID | 複核 | RECHECK 摘要 |
|---|---|---|
| CODEX-R1-P1-01 | **複核同意 CLOSED** | `-k manifest_required` → **1 passed**；`n_events_raw=400`／`n_events_effective=400` |
| CODEX-R1-P1-02 | **複核同意 CLOSED** | `-k "unlogged_candidate or record_guards"` → **2 passed**；ledger 只記 a、輸入 a+b ⇒ `universe_provenance_unverifiable`＋`candidate_set_mismatch` |
| CODEX-R1-P1-03 | **複核同意 CLOSED** | 與本家 P2-02 同軸修法；`-k pbo_observation_axis` 綠 |
| CODEX-R1-P1-04 | **複核同意 CLOSED** | `-k requires_command_and_expected` → **1 passed**；拒後帳本目錄空 |
| GROK-R1-P1-01 | **複核同意 CLOSED** | 同 PBO 軸測試；字串序≠時間序反例已覆蓋 |
| GROK-R1-P2-01 | **複核同意 CLOSED** | 與本家 P1-01 同收據閘；`test_disguised_score_series_rejected` 綠 |

### R1 閉合逐條（原提出方重跑）

**Closure P1-01（原 ID COMPOSER-R1-P1-01）— CLOSED**

- 碼：`candidate_ledger.py:68-98` `_assert_return_series` 要求 `t_semantics=trade_level`／`entry_semantic`／`label_definition`／`source_artifact_hash`(64hex)／`span_years>0`／`entry_at_ms_by_event` 覆蓋全 index、n≥2。
- 測：`pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k "disguised or auc_fed"` → **2 passed** rc=0（含 `test_disguised_score_series_rejected`：無 attrs／`name=score`／單值／收據鍵不全各拒）。
- 探針：inline `Series([0.9,0.85,0.72], name=hold_return)`＋`span_years=2.0` only ⇒ `MetricTypeError: returns 缺 to_return_series 收據 attrs [...]`（R1 反例不再得 `dsr.status=ok`）。

**Closure P2-02（原 ID COMPOSER-R1-P2-02）— CLOSED**

- 碼：`to_return_series:181` 寫入 `entry_at_ms_by_event`；`run_dsr_pbo:351` 聯集軸依 `(entry_at, id)`；`:365-366` `observation_axis` 字面＋首末 entry ms。
- 測：`pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k pbo_observation_axis` → **1 passed** rc=0；`evt_10`（早）在第 0 列；`observation_axis_first_last_entry_ms`＝`[entry[evt_10], entry[evt_1]]`；跨候選時間戳衝突 ⇒ `ValueError`。
- 對照 R1：`sorted(["evt_10","evt_2","evt_1"])` 字串序仍≠時間序，但矩陣列已依 `entry_at_ms`（spy 斷言 `M[:,0]` 對齊 `a.returns.loc[ids]`）。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：帳本與 sidecar 非同一交易；「全驗→帳本→sidecar」＋ sidecar 失敗 raise 為可接受誠實邊界 | **成立（攻擊不推翻）** | `record_candidate:229-244` 先 `append_trial_attempt` 再 `_ledger_lock` 寫 sidecar；docstring `:191-192` 明列非同一交易。GAP-1 無跨檔 API（synth X5 已裁）；brief 不受理範圍禁重議已裁 assumed。誠實邊界：sidecar 寫失敗時帳本列已存在——與 synth 一致，非 B4 stamp blocker。 |
| **assumed**：收據 attrs 閘擋疏忽／誤標即達 K6/C7「機械拒」；蓄意偽造 attrs 不在受理範圍 | **成立（攻擊確認邊界、非新 finding）** | 疏忽路徑：無／缺收據 attrs ⇒ `MetricTypeError`（上 Closure P1-01）。蓄意偽造：手跑 probe（全 `_RECEIPT_ATTRS`＋`[0.9,0.85,0.72]`＋`record_candidate`）⇒ `dsr.status=ok`、`value≈0.999`——**與 R1 synth X2 誠實邊界一致**（95% 解法）；非本輪修補引入，不重開 R1 已裁項。 |

## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——COMPOSER-R1-P1-01／P2-02 兩條原反例均 CLOSED；修補 diff 未引入可證偽 P0–P2 缺陷；他方六條 R1 複核皆同意 CLOSED；brief assumed 攻擊不推翻已裁誠實邊界。

**碼證**: B4 Gate 本輪複驗：`-k "pattern_bridge or candidate_ledger"` → **27 passed** rc=0；event_samples 全套 → **222 passed** rc=0；strategy_validation → **272 passed** rc=0。本家閉合：`-k "disguised or auc_fed"` **2 passed**；`-k pbo_observation_axis` **1 passed**。修補引入檢：`grep extract_event_patterns momentum/` 無 B4.1 外 caller；`test_to_return_series_hand_exact_each_entry_semantic` 五語意 parametrize 仍綠；manifest 必填反例與 `n_events_raw=400` 一致。

**來源摘要**: handoffs/reconcile/20260821-gap3-b4-review-r1/synth.md#8finding；momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b；momentum/Analysis/event_samples/pattern_bridge.py#2d4c5b8daf18；docs/GAP3_EVENT_TODO.md#df04bdabf37d；handoffs/20260821-gap3-b4-review-r2-brief.md

正文：閉合義務本家 2/2 CLOSED；他方 6/6 複核同意；§0 assumed 兩條攻擊後仍成立（偽造 attrs 路徑為 R1 已登記邊界，非新缺陷）。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief assumed（ledger/sidecar 非交易、偽造 attrs 邊界）已攻擊（上表）。

## VERIFY（本輪複驗）

```
venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger" → 27 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 222 passed rc=0
venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation -q → 272 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k "disguised or auc_fed" → 2 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k pbo_observation_axis → 1 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_pattern_bridge.py -q -k manifest_required → 1 passed rc=0
inline disguise probe → MetricTypeError（缺收據 attrs）
inline forged-full-receipt probe → dsr.status=ok（R1 已裁誠實邊界；非新 finding）
```

ASSUMPTIONS_VERIFIED: 上述命令＋`candidate_ledger.py`／`pattern_bridge.py` R1 修法區段對讀＋`git diff e9e0257c..HEAD -- momentum/ tests/` 白名單檢視  
TESTS_RUN: 見 VERIFY  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only；禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT: handoffs/20260821-gap3-b4-review-r2-composer.md  
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

STATUS: DONE
