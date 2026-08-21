# GAP-3 B3 review R2 — codex
task-id: 20260821-GAP3-B3-REVIEW-R2；brief-kind: review；patch: `git diff 5074bc04..HEAD -- momentum/ tests/`
## Verdict：本家 5/5 CLOSED；本輪無新 finding；B3 Gate 可進三家 RECONCILE-STAMP
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
## 被當成事實的未驗證假設（§0）
無新增；已攻擊 `requests.py`→B5 follow-up 前提，確認現值與契約相同且 B5 scope 成立。
ASSUMPTIONS_VERIFIED: R1 五條逐條反例、逐 label manifest/G6 透傳、label role、control override、deepcopy、Protocol、`_fold` 合法/恆真邊界；Gate 1–3 rc=0；golden 同輪單次 receipt rc=0。
TESTS_RUN: `...event_samples -q -k "condition_engine or generator_adapters"` 64 passed；`...feature_engineering -q -k state_counters` 17 passed；`...test_mutation_guard.py -q -k M6` 1 passed；R1 rechecks 1/2/1/1/17 passed；`logical_tautology or non_tautology` 9 passed；G6 1 passed。
FAILURES_SEEN: 初次 `/tmp` probe 缺 `PYTHONPATH`，改以 `PYTHONPATH=. venv/bin/python` 重跑 rc=0；產品測試無失敗。
SCOPE_CHANGES: none；review-only，未改碼；根 `HANDOFF.md` 未改。
NUMERIC_OR_SCHEMA_IMPACT: none；僅觀察 B5 hardcode 殘差，未改輸出。
OUTPUT: handoffs/20260821-gap3-b3-review-r2-codex.md；/tmp/workdir 不存在，無可清理目標；保留 claude-501（未見於當前 `/tmp`）。
STATUS: DONE
