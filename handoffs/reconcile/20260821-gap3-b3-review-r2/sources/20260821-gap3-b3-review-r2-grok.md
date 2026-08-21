# GAP-3 B3 review R2 — grok（閉合輪／sentinel）

task-id: 20260821-GAP3-B3-REVIEW-R2
family: grok
brief-kind: review
brief: handoffs/20260821-gap3-b3-review-r2-brief.md
patch: `git diff 5074bc04..HEAD -- momentum/ tests/`（commit fe104196「B3 review R1 九條全修」）
R1 裁決: handoffs/reconcile/20260821-gap3-b3-review-r1/synth.md
修後 Gate receipt: handoffs/run_receipts/20260821T140500Z-gap3-b3-r1-fix-gate.log

## Verdict：可進三家 RECONCILE-STAMP（本家 2/2 CLOSED；本輪無新 finding）

### 必答

1. **己方 R1 各條 CLOSED／OPEN（附重跑輸出）**  
   | ID | 處置 | 本輪碼證摘要 |
   |---|---|---|
   | GROK-R1-P1-01 | **CLOSED** | `prevalence_learn`＝去重後 primary 該 label_id `label.mean`；`prevalence_learn_scope=primary_after_dedupe`；`test_G6_calls_evaluate_all_bars_not_parallel` `abs=1e-12` 綠；手跑 ETHUSDT 12h `ret_1<0` C：`pl==mean` diff=0（up1 n=47 pl≈0.383；up5 n=26 pl≈0.115） |
   | GROK-R1-P2-01 | **CLOSED** | `_role_violation` 以 `casefold()` 比對 `future_`；`test_future_prefix_backstop_is_case_insensitive` 綠；手跑 `Future_Return>0`＋pit_feature ⇒ `role_isolation_violation` |

2. **修補是否引入新問題？**  
   **無**（見 sentinel `GROK-R2-P3-00`）。逐 label_id `manifests{lid}` 透傳 G6 `manifest=manifests.get(r.label_id)`；`_fold` 對 `(rsi > 0 or 1 > 2) and ema > 0` 仍 ACCEPTED，對 `True or feat>0`／排中律拒；`label` 拒 `pit_feature` 與 SPEC「label 只進結果欄」一致。

3. **B3 Gate 複驗 rc=0？可進 stamp？**  
   **可以（grok 本輪 APPROVED）**——本輪複驗 gate1/2/3＝0；golden 依 brief「只准跑一次」引修後 receipt `rc_golden=0`／sha `163c4ce…`，未並行重跑。前提：同輪 codex／composer 對其原 finding 亦 CLOSED 且無新 BLOCKING。

### R1 閉合逐條（原提出方重跑）

**Closure P1-01（原 ID GROK-R1-P1-01）— CLOSED**
- 碼：`generator.py` G6 迴圈對 `deduped` 子集算 `prevalence_learn`；報告寫 `prevalence_learn_scope=primary_after_dedupe`。
- 測：`venv/bin/python -m pytest tests/momentum/event_samples/test_generator_adapters.py -q -k G6_calls_evaluate_all_bars` → **1 passed** rc=0（assert 對回傳 `ev` `abs=1e-12`＋scope 字面）。
- 手跑：真實 ETHUSDT 12h 切片 `ret_1<0` scenario=C → `pl` 與 primary `label.mean` 全等（diff=0）。

**Closure P2-01（原 ID GROK-R1-P2-01）— CLOSED**
- 碼：`condition_engine._role_violation`：`column.casefold().startswith(prefix.casefold())`。
- 測：`-k case_insensitive` → **1 passed** rc=0（`Future_Return`／`FUTURE_X`／`fUtUrE_y`）。
- 手跑：`parse_condition("Future_Return>0", {...:"pit_feature"}, "feature")` ⇒ `role_isolation_violation`。

### 他家 R1 條目（複核同意／異議）

| ID | 複核 | 證據摘要 |
|---|---|---|
| CODEX-R1-P1-01 | **同意 CLOSED** | `-k G2_default_scenario_C` 綠；手跑 MULTILABEL_C manifests/dedupe＝`{up1,up5}`，兩 label 皆存 |
| CODEX-R1-P1-02 | **同意 CLOSED** | `-k label_role`；手跑 `f>0 and future_x>0` label ⇒ 拒；純 `future_x>0` label ⇒ 過；與 SPEC D3「label 只進結果欄」一致 |
| CODEX-R1-P1-03 | **同意 CLOSED** | `-k control_kind_not_overridable`；帶 `control_kind=` 建構 ⇒ TypeError；`PLATFORM_CONTROL_KIND` 寫死 |
| CODEX-R1-P2-04 | **同意 momentum 半條 CLOSED**；api 半條見 §0 | `-k contract_cache_immutable`；deepcopy 探針改寫不污染二次載入 |
| CODEX-R1-P2-05 | **同意 CLOSED** | Protocol／concrete 皆有 `*, condition_spec=`；`pytest tests/momentum/test_event_filter.py -q` → 17 passed |
| COMPOSER-R1-P1-01 | **同意 CLOSED** | `-k "logical_tautology or non_tautology"`；手跑四式拒／`(rsi>0 or 1>2) and ema>0` 過 |
| COMPOSER-R1-P2-02 | **同意 CLOSED** | `-k short_with_raw_outcome`；provenance 兩旗標＋short loud warning |

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：CODEX-R1-P2-04 之 `requests.py` 半條以 B5 follow-up 登記即足（api/ 只在 B5 白名單） | **成立（攻擊不推翻）** | 契約 `allowed_filtering_params=['price_change']` 與 `requests.py:50` 硬編碼集合**目前字面相同**（無現差分）；momentum 已有 `allowed_filtering_params()` 契約出口＋deepcopy；B3 路徑無 API 條件引擎匯出（`grep momentum/` 無讀 `api.models.requests`）。殘留＝契約日後擴張時 API 硬編碼會漂——屬 B5 白名單範圍，與 synth／brief 登記一致；不另開 finding。 |
| fact-verified: 修後 64／17／M6／golden／256 | **本輪複驗成立（golden 引 receipt）** | gate1=64 passed；gate2=17；M6=1；others 16；event_filter 17；receipt golden CHECK PASS sha 163c4ce… rc_golden=0（本輪未並行重跑 golden） |

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——GROK-R1-P1-01／P2-01 兩條原反例均 CLOSED；九條 R1 修補未引入可證偽 P0–P2 新缺陷；brief assumed（requests.py→B5）攻擊不推翻。

**碼證**: `pytest … -k "condition_engine or generator_adapters"` → **64 passed** rc=0；`… -k state_counters` → **17 passed**；`… -k M6` → **1 passed**；`-k G6_calls_evaluate_all_bars`／`case_insensitive` 各 1 passed；他家 RECHECK 捆 `-k "G2_default…|label_role|control_kind…|contract_cache…|logical_tautology|non_tautology|short_with_raw|case_insensitive"` → **16 passed**；`test_event_filter.py` → **17 passed**；手跑 prevalence diff=0＋`Future_Return` 拒＋`_fold` 合法式過／恆真拒＋MULTILABEL_C 雙 label 存；`git diff 5074bc04..HEAD --stat -- momentum/ tests/` → 5 files +201/−23；golden 引 receipt rc_golden=0／sha 163c4ce…。殘差觀察（不列 finding）：`assert_no_outcome_columns` 仍大小寫敏感——parse 路徑已 casefold 且 FF 欄小寫，屬同一防呆級、非本輪修補引入之實質缺陷。

**來源摘要**: handoffs/reconcile/20260821-gap3-b3-review-r1/synth.md#21f38377459f；handoffs/20260821-gap3-b3-review-r1-grok.md#60305ab0c6bd；handoffs/20260821-gap3-b3-review-r2-brief.md#523ca8963e20；momentum/Analysis/event_samples/generator.py#295ed99e2a88；momentum/Analysis/event_samples/condition_engine.py#7eb07f0c0203；momentum/Analysis/event_filter.py#fb3e498ea26c；tests/momentum/event_samples/test_generator_adapters.py#0b971dc2b3ad；tests/momentum/event_samples/test_condition_engine.py#3197f4ad97b4；api/models/requests.py#938ff6900fed；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；handoffs/run_receipts/20260821T140500Z-gap3-b3-r1-fix-gate.log#98d738f0ea78

正文：閉合義務兩條全 CLOSED；§0 assumed 已攻；不受理 SPEC/TODO 重審／B4–B5／R1 已裁成立前提再議。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief 一條 assumed 已攻擊（上表）。

ASSUMPTIONS_VERIFIED: GROK 兩條 R1 修補落地（prevalence=primary_after_dedupe；future_ casefold）；逐 label_id manifests→G6 透傳；_fold 不誤拒 `(rsi>0 or 1>2) and ema>0`；label 拒 pit_feature＝SPEC D3；requests.py B5 延後成立；64+17+M6 綠；golden 引 receipt
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "condition_engine or generator_adapters"` → 64 passed rc=0；`…/feature_engineering/ -q -k state_counters` → 17 passed rc=0；`…/test_mutation_guard.py -q -k M6` → 1 passed rc=0；Grok/他家 RECHECK 捆與 `test_event_filter.py` 皆 rc=0；手跑 prevalence／Future_Return／_fold／MULTILABEL_C；golden 未本輪重跑（brief 禁並行），引 `20260821T140500Z-gap3-b3-r1-fix-gate.log` rc_golden=0／sha 163c4ce…
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260821-gap3-b3-review-r2-grok.md
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

## 戳記
RECONCILE-STAMP: grok APPROVED 2026-08-21 sha256:98d738f0ea7810e7e15e272c5e0044356fd3af01f708597a067304795e580406 task:20260821-GAP3-B3-REVIEW-R2

STATUS: DONE
