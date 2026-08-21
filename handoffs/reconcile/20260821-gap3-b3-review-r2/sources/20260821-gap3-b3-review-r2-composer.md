# GAP-3 B3 review R2 — composer（closure／sentinel）

task-id: 20260821-GAP3-B3-REVIEW-R2  
family: composer  
brief-kind: review  
brief: handoffs/20260821-gap3-b3-review-r2-brief.md  
patch: `git diff 5074bc04..HEAD -- momentum/ tests/`  
R1 裁決: handoffs/reconcile/20260821-gap3-b3-review-r1/synth.md

## Verdict：可進三家 RECONCILE-STAMP（本家 2/2 CLOSED；本輪無新 finding）

### 必答

1. **原提出方逐條 CLOSED？**  
   | ID | 處置 | 本輪碼證摘要 |
   |---|---|---|
   | COMPOSER-R1-P1-01 | **CLOSED** | `condition_engine.py:212-271` `_fold` 三值常數摺疊＋`parse_condition` 在 folded≠None 時 `constant_expression`；`-k "logical_tautology or non_tautology"` → **9 passed** rc=0；原探針四式（`True or feat>0` 等）皆拒 |
   | COMPOSER-R1-P2-02 | **CLOSED** | `generator.py:285-289` provenance `outcome_columns_are_raw_unsigned`／`label_value_is_signed`＋short 選樣 `logger.warning`；`-k short_with_raw_outcome` → **1 passed** rc=0 |

2. **修補新引入問題？**  
   **無**（見 sentinel `COMPOSER-R2-P3-00`）。逐 label_id `manifests{}` 透傳 G6（`generator.py:313 manifest=manifests.get(r.label_id)`）與 `test_G2_default_scenario_C_dedupes_per_label_id`／`test_G6_calls_evaluate_all_bars_not_parallel` 一致；`_fold` 未誤拒 `(rsi_14 > 0 or 1 > 2) and ema_gap > 0`（`test_non_tautology_with_constant_subterm_accepted` 綠＋手跑 probe ACCEPT digest=67a9ebe1…）；CODEX label 分支拒 `pit_feature` 與 SPEC D3-1「label 只進結果欄」一致（`test_label_role_rejects_mixed_feature_and_outcome` 綠）。

3. **B3 Gate 四命令 rc=0？可進 stamp？**  
   **是（composer 本輪 APPROVED）**——四命令本輪複驗全 rc=0（見 VERIFY）；前提同輪 codex／grok 原 finding 亦 CLOSED 且無新 BLOCKING。

### 他方 R1 複核（非原提出方）

| ID | 複核 | RECHECK 摘要 |
|---|---|---|
| CODEX-R1-P1-01 | **複核同意 CLOSED** | `-k G2_default_scenario_C` → up1＋up5 皆存、`manifests`/`dedupe` 逐 label_id |
| CODEX-R1-P1-02 | **複核同意 CLOSED** | `-k label_role` → 混合 pit+outcome 於 `label` 角色拒 |
| CODEX-R1-P1-03 | **複核同意 CLOSED** | `-k control_kind_not_overridable` → TypeError |
| CODEX-R1-P2-04 | **複核同意 CLOSED（momentum 半條）** | `-k contract_cache_immutable` → mutation 不污染 prefix；`requests.py` 仍 B5 follow-up（R1 已裁，本輪不重議） |
| CODEX-R1-P2-05 | **複核同意 CLOSED** | `pytest tests/momentum/test_event_filter.py -q` → 17 passed |
| GROK-R1-P1-01 | **複核同意 CLOSED** | `-k G6_calls_evaluate_all_bars` → `prevalence_learn_scope=primary_after_dedupe`、`abs=1e-12` |
| GROK-R1-P2-01 | **複核同意 CLOSED** | `-k case_insensitive` → `Future_Return` 等拒 |

### R1 閉合逐條（原提出方重跑）

**Closure P1-01（原 ID COMPOSER-R1-P1-01）— CLOSED**

- 碼：`condition_engine.py:212-271` `_fold`（and/or/not/cmp＋排中律／矛盾律）；`:269-271` folded 非 None ⇒ `constant_expression`。
- 測：`pytest tests/momentum/event_samples/test_condition_engine.py -q -k "logical_tautology or non_tautology"` → **9 passed** rc=0（含 8 拒收式＋1 合法 `(rsi_14 > 0 or 1 > 2) and ema_gap > 0`）。
- 探針：手跑 `parse_condition("(rsi > 0 or 1 > 2) and ema > 0", …)` → ACCEPTED；`True or feat > 0` 等 → `ConditionError constant_expression`。

**Closure P2-02（原 ID COMPOSER-R1-P2-02）— CLOSED**

- 碼：`generator.py:285-289` provenance 旗標＋short＋`selection_uses_outcome_columns` 時 warning。
- 測：`pytest tests/momentum/event_samples/test_generator_adapters.py -q -k short_with_raw_outcome` → **1 passed** rc=0（assert 旗標＋warning ＋ signed label 手算）。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：CODEX-R1-P2-04 之 `api/models/requests.py` 半條以 B5 follow-up 登記即足 | **成立（攻擊不推翻）** | momentum 層 `deepcopy` 已落地且 `contract_cache_immutable` 綠；`requests.py:46-53` 仍硬編 `{'price_change'}`——屬 api/ B5 白名單，R1 synth 已裁「不於本批動」；brief 不受理範圍禁重議已裁 assumed。誠實邊界：API 路徑仍可能與契約 drift——已登記 follow-up，非 B3 stamp blocker。 |

## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——COMPOSER-R1-P1-01／P2-02 兩條原反例均 CLOSED；修補 diff 未引入可證偽 P0–P2 缺陷；他方七條 R1 複核皆同意 CLOSED。

**碼證**: B3 Gate 四命令本輪複驗：`pytest … -k "condition_engine or generator_adapters"` → **64 passed** rc=0；`pytest …/feature_engineering/ -k state_counters` → **17 passed** rc=0；`pytest …/test_mutation_guard.py -k M6` → **1 passed** rc=0；`python scripts/gap3_freeze_golden.py --check` → CHECK PASS canonical_sha=163c4cecb1006dc42dea0804acc365d83fe7cdbaf05ba64b1d794168dd67e463 rc=0。修補引入檢：`manifests.get(r.label_id)` 逐 label G6 透傳；`_fold` 合法常數子式仍過；label 角色 pit 拒收與 D3-1 一致。

**來源摘要**: handoffs/reconcile/20260821-gap3-b3-review-r1/synth.md#21f38377459f；momentum/Analysis/event_samples/condition_engine.py#7eb07f0c0203；momentum/Analysis/event_samples/generator.py#295ed99e2a88；docs/GAP3_EVENT_TODO.md#df04bdabf37d；handoffs/20260821-gap3-b3-review-r2-brief.md

正文：閉合義務本家 2/2 CLOSED；他方 7/7 複核同意；§0 assumed 攻擊不推翻 B5 follow-up 裁決。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief assumed（requests.py B5 follow-up）已攻擊（上表）。

## VERIFY（本輪複驗）

```
venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "condition_engine or generator_adapters" → 64 passed rc=0
venv/bin/python -m pytest tests/momentum/feature_engineering/ -q -k state_counters → 17 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_mutation_guard.py -q -k M6 → 1 passed rc=0
venv/bin/python scripts/gap3_freeze_golden.py --check → CHECK PASS sha=163c4cec… rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_condition_engine.py -q -k "logical_tautology or non_tautology" → 9 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_generator_adapters.py -q -k short_with_raw_outcome → 1 passed rc=0
```

ASSUMPTIONS_VERIFIED: 上述命令＋`git diff 5074bc04..HEAD -- momentum/ tests/` 對讀 `_fold`／逐 label manifest／provenance 旗標  
TESTS_RUN: 見 VERIFY  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only；禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT: handoffs/20260821-gap3-b3-review-r2-composer.md  
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

STATUS: DONE
