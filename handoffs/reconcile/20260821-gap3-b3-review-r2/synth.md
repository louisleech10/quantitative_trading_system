# Reconcile — 20260821-gap3-b3-review-r2

**來源** 20260821-gap3-b3-review-r2-codex.md, 20260821-gap3-b3-review-r2-composer.md, 20260821-gap3-b3-review-r2-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置（主委 Claude 裁決；閉合輪）

**Verdict**: 可合併——R1 九條由原提出方重跑同一反例全數 CLOSED（codex 5/5、composer 2/2、grok 2/2），他家交叉複核 7/7 同意；三家 sentinel 0 新 findings；B3 Gate 四命令三家複驗 rc=0（golden 依 brief 引修後 receipt sha 163c4ce…）；B3 收斂履歷 R1 9→R2 0 ⇒ 進三家 RECONCILE-STAMP（蓋本檔）→ B3 CLOSED。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| Y1 codex R1 五條閉合（逐 label_id 去重／label 角色／control_kind 寫死／契約 deepcopy／Protocol 同步） | CODEX-R1-P1-01, CODEX-R1-P1-02, CODEX-R1-P1-03, CODEX-R1-P2-04, CODEX-R1-P2-05 | **CLOSED**（原提出方重跑 MULTILABEL_C／LABEL_ROLE／OVERRIDE／CONTRACT_CACHE 探針＋RECHECK 各綠）；P2-04 之 `requests.py` 半條維持 B5 follow-up（現值與契約字面相同、無現差分） |
| Y2 三家 sentinel（0 新 findings） | CODEX-R2-P3-00, COMPOSER-R2-P3-00, GROK-R2-P3-00 | **採認**：修補未引入新問題（manifests dict→G6 透傳、`_fold` 不誤拒合法式、label 拒 pit_feature＝D3-1）。grok 殘差觀察 `assert_no_outcome_columns` 大小寫敏感＝同級防呆、非缺陷——主委已於本輪一併補 casefold（見 fix commit） |

composer／grok 之 R1 閉合（COMPOSER-R1-P1-01／P2-02、GROK-R1-P1-01／P2-01）以正文表列 CLOSED（非 heading 形式），附錄逐字保留於各家交件。

**殘留登記（B5 follow-up）**：`api/models/requests.py:50` `allowed_filtering_params` 硬編碼改讀 `condition_engine.allowed_filtering_params()`——`為何現在不做: user-ruling:api/ 路徑只在 B5 白名單（TODO §0-6-⑤）`。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: G2 scenario=C 不得跨 label_id 互刪合法事件。 **碼證**: `generator.py:259-283` 逐 label 建 manifest；`G2_default_scenario_C` → 1 passed；手跑 `MULTILABEL_C 73 ['up1','up5'] ['up1','up5'] ['up1','up5']`。 **來源摘要**: momentum/Analysis/event_samples/generator.py#295ed99e2a88;tests/momentum/event_samples/test_generator_adapters.py#0b971dc2b3a
**處置**: CLOSED；兩 label 均存、各自 dedupe，未見修補引入問題。
## CODEX-R1-P1-02
**斷言**: `label` 角色不得混入 `pit_feature`。 **碼證**: `condition_engine.py:81-95`；手跑 `LABEL_ROLE_REJECTED role_isolation_violation`；`-k label_role` → 2 passed。 **來源摘要**: momentum/Analysis/event_samples/condition_engine.py#7eb07f0c0203;tests/momentum/event_samples/test_condition_engine.py#3197f4ad97b4
**處置**: CLOSED；純 outcome 可過、混合式拒收，符合 D3-1「label 只進結果欄」。
## CODEX-R1-P1-03
**斷言**: 平台產生器不得接受可覆寫的 `control_kind`。 **碼證**: `generator.py:40-42,59-73,127-129,215`；手跑 `OVERRIDE_CONTROL_KIND TypeError`；`-k control_kind_not_overridable` → 1 passed。 **來源摘要**: momentum/Analysis/event_samples/generator.py#295ed99e2a88;momentum/Analysis/event_samples/import_contract.py#58c331ca3d5d
**處置**: CLOSED；輸出固定 `platform_same_trigger_rule`，入口並對契約 accepted 對證。
## CODEX-R1-P2-04
**斷言**: 引擎契約回傳不得污染 module SoT；API 清單殘差須明列 B5。 **碼證**: `condition_engine.py:38-44` deepcopy；手跑 `CONTRACT_CACHE future_ False`；`-k contract_cache_immutable` → 1 passed；`requests.py:46-53` 與契約 `:55-57` 目前同為 `price_change`。 **來源摘要**: momentum/Analysis/event_samples/condition_engine.py#7eb07f0c0203;api/models/requests.py#938ff6900fed;docs/GAP3_EVENT_TODO.md#df04bdabf37d
**處置**: CLOSED（B3/momentum scope）；API hardcode 仍是已登記 B5 follow-up，現值無漂移，不構成本輪新 finding 或 B3 blocker。
## CODEX-R1-P2-05
**斷言**: `IEventFilter` Protocol 必須宣告 keyword-only `condition_spec`。 **碼證**: `event_filter.py:53-63` 與 concrete `:92-99` 同步；`pytest tests/momentum/test_event_filter.py -q` → 17 passed。 **來源摘要**: momentum/Analysis/event_filter.py#fb3e498ea26c;tests/momentum/test_event_filter.py#f704be6d4b41
**處置**: CLOSED；Protocol/runtime adapter 介面一致。
## CODEX-R2-P3-00
**斷言**: 本輪逐項核對後無 finding。 **碼證**: manifests→G6 `generator.py:291-313`，`-k G6_calls_evaluate_all_bars` → 1 passed；`_fold` 合法 `(ret_1 > 0 or 1 > 2) and ret_1 > -1` ACCEPTED、恆真/排中律拒；B3 Gate：gate1 64 passed rc=0、gate2 17 passed rc=0、M6 1 passed rc=0；golden 單次同輪輸出 `CHECK PASS canonical_sha=163c4cecb100... rc=0`（見 composer handoff）。 **來源摘要**: handoffs/20260821-gap3-b3-review-r2-brief.md#523ca8963e20;momentum/Analysis/event_samples/generator.py#295ed99e2a88;momentum/Analysis/event_samples/condition_engine.py#7eb07f0c0203;handoffs/20260821-gap3-b3-review-r2-composer.md#f1f765d6846a
**正文**: 九條 R1 修補未引入可證偽 P0–P2 問題；本輪不捏造 finding。
## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——COMPOSER-R1-P1-01／P2-02 兩條原反例均 CLOSED；修補 diff 未引入可證偽 P0–P2 缺陷；他方七條 R1 複核皆同意 CLOSED。

**碼證**: B3 Gate 四命令本輪複驗：`pytest … -k "condition_engine or generator_adapters"` → **64 passed** rc=0；`pytest …/feature_engineering/ -k state_counters` → **17 passed** rc=0；`pytest …/test_mutation_guard.py -k M6` → **1 passed** rc=0；`python scripts/gap3_freeze_golden.py --check` → CHECK PASS canonical_sha=163c4cecb1006dc42dea0804acc365d83fe7cdbaf05ba64b1d794168dd67e463 rc=0。修補引入檢：`manifests.get(r.label_id)` 逐 label G6 透傳；`_fold` 合法常數子式仍過；label 角色 pit 拒收與 D3-1 一致。

**來源摘要**: handoffs/reconcile/20260821-gap3-b3-review-r1/synth.md#21f38377459f；momentum/Analysis/event_samples/condition_engine.py#7eb07f0c0203；momentum/Analysis/event_samples/generator.py#295ed99e2a88；docs/GAP3_EVENT_TODO.md#df04bdabf37d；handoffs/20260821-gap3-b3-review-r2-brief.md

正文：閉合義務本家 2/2 CLOSED；他方 7/7 複核同意；§0 assumed 攻擊不推翻 B5 follow-up 裁決。禁捏造湊數。

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——GROK-R1-P1-01／P2-01 兩條原反例均 CLOSED；九條 R1 修補未引入可證偽 P0–P2 新缺陷；brief assumed（requests.py→B5）攻擊不推翻。

**碼證**: `pytest … -k "condition_engine or generator_adapters"` → **64 passed** rc=0；`… -k state_counters` → **17 passed**；`… -k M6` → **1 passed**；`-k G6_calls_evaluate_all_bars`／`case_insensitive` 各 1 passed；他家 RECHECK 捆 `-k "G2_default…|label_role|control_kind…|contract_cache…|logical_tautology|non_tautology|short_with_raw|case_insensitive"` → **16 passed**；`test_event_filter.py` → **17 passed**；手跑 prevalence diff=0＋`Future_Return` 拒＋`_fold` 合法式過／恆真拒＋MULTILABEL_C 雙 label 存；`git diff 5074bc04..HEAD --stat -- momentum/ tests/` → 5 files +201/−23；golden 引 receipt rc_golden=0／sha 163c4ce…。殘差觀察（不列 finding）：`assert_no_outcome_columns` 仍大小寫敏感——parse 路徑已 casefold 且 FF 欄小寫，屬同一防呆級、非本輪修補引入之實質缺陷。

**來源摘要**: handoffs/reconcile/20260821-gap3-b3-review-r1/synth.md#21f38377459f；handoffs/20260821-gap3-b3-review-r1-grok.md#60305ab0c6bd；handoffs/20260821-gap3-b3-review-r2-brief.md#523ca8963e20；momentum/Analysis/event_samples/generator.py#295ed99e2a88；momentum/Analysis/event_samples/condition_engine.py#7eb07f0c0203；momentum/Analysis/event_filter.py#fb3e498ea26c；tests/momentum/event_samples/test_generator_adapters.py#0b971dc2b3ad；tests/momentum/event_samples/test_condition_engine.py#3197f4ad97b4；api/models/requests.py#938ff6900fed；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；handoffs/run_receipts/20260821T140500Z-gap3-b3-r1-fix-gate.log#98d738f0ea78

正文：閉合義務兩條全 CLOSED；§0 assumed 已攻；不受理 SPEC/TODO 重審／B4–B5／R1 已裁成立前提再議。禁捏造湊數。



## 戳記

（三家 RECONCILE-STAMP 蓋此區；body hash＝本區之前全文——reconcile_body_hash.sh）
