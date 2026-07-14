# IC1CFR-STOPGAP — Delta Concurrence R4 (Composer)

> **TASK_ID**: `IC1CFR-STOPGAP:delta-concur-r4`  
> **審查對象**: `docs/IC1CFR_STOPGAP_SPEC.md` v0.4 r4（r3→r4 delta）  
> **審查者**: Composer | **日期**: 2026-07-14  
> **對照**: r3 `handoffs/20260714-IC1CFR-STOPGAP-R3-composer.md`(APPROVE 0B)、codex r3 REJECT(4B)、RECONCILE r4 裁決 S-F10~S-F13

## Verdict：r4 delta 不推翻 r3 APPROVE；補洞而非改向 → APPROVE

---

## r3→r4 四項 delta 逐條複核

| Delta | r3 我端狀態 / codex 洞 | r4 落點 | 是否破壞 r3 APPROVE | 判定 |
|-------|------------------------|---------|---------------------|------|
| **S-F10** pure-tier=not_run（非佔位） | r3 PASS「tier 排除」但未抓 Task 1.1 邊界③「tier→佔位」內矛盾；codex CX-1 BLOCKING | §C:24 純 intermediate/advanced 不入 run_targets→`not_run`+無節；Task 1.1:44 邊界③改 not_run；M1b/`test_pure_tier_not_run` 釘死 | **否**——強化 S-F9 選項 B，與 r3 定案 default-off=誠實缺席一致 | **CONCUR** |
| **S-F11** ModuleUnavailableError 專屬 except | r3 NB3「summary 寫入者不精」；codex CX-2 BLOCKING（`:1667` 無條件 completed） | §C:25+Task 1.1:42-43 runner raise→父迴圈 `:1665` 區**先於**通用 except 寫 §U union+summary `unavailable`+不入 errors+不計 completed/skipped | **否**——閉合 r3 NB3，不改三態語意 | **CONCUR** |
| **S-F12** force 不跨 deep-off | codex CX-3 BLOCKING（`:1601` 早退在 `:1627` force_set 前） | §C:26 契約收窄：deep 全關→force 亦 `not_run`；Task 1.1 `test_deep_off_not_run` | **否**——fail-close 收窄，無新洩漏 | **CONCUR** |
| **S-F13** §G before 用實凍值 | codex CX-4 BLOCKING（`enabled` 態不存在）；r3 NB1 baseline 仍 MISSING | §G:35 `module_summary.factor_returns`:**改前實凍值(成功 fixture=`completed`)→改後 `not_run`** | **否**——修正 oracle 與 orchestrator 實態(`:1667` completed / `:1696` not_run) | **CONCUR** |

---

## r3 APPROVE 核心是否仍成立

| r3 已 APPROVE 項 | r4 影響 |
|------------------|---------|
| S-F9 選項 B：default-off=`not_run`+無節；顯式開啟=union+unavailable | **維持**；pure-tier 從「誤列顯式」改回 default-off 子集 |
| singular/plural 鍵名、四處 default-off、S-F3 sanitizer、Task 2.2 EquityCurve | **未改** |
| §G 雙 golden（default-off + 顯式開啟） | **精化** before 態來源，結構不變 |
| M1~M4 可證偽 | **M1b 探針語意更精**（pure-tier not_run vs 佔位） |

**結論**：r4 僅解 r3 未閉的 tier/控制流/golden FACT 矛盾，未改下架目標、sanitizer 邊界或前端 scope。

---

## r4 新洞掃描

### R4-NB1 — custom preset `module_overrides` 啟用路徑 **NON-BLOCKING**

- §C:25 顯式開啟僅列 `force_modules` 與 `config_override enabled=true`；`_apply_tier_config` custom 分支(`:3354-3358`)可經 `module_overrides` 設 `factor_return=true`。
- 行為上會入 run_targets→應走 unavailable union（與顯式開啟同），但 SPEC 未具名此第三入口；實作期 `_is_module_enabled` 已足，建議 TODO 補一句或測試覆蓋 custom override。

### R4-NB2 — r3 NB 殘留 **NON-BLOCKING**（未惡化）

- §G Phase 0 baseline 仍無 Task 0.1；`before.json` 仍 MISSING。
- §V 改寫表仍「逐筆列」無草案（RECONCILE 交 TODO）。
- cache 命中 `module_summary` vs sanitizer 一致性（r3 NB4）仍未明示——M2 仍以無有限葉為主。

### R4-NB3 — unavailable 計數桶措辭 **NON-BLOCKING**

- §C:25「新增 unavailable 桶或明確排除」二選一未凍結；不阻斷 Phase 1，completed_count 漂移已由 §G 排除清單覆蓋。

### 已掃、不開 BLOCKING

| 焦點 | r4 判定 |
|------|---------|
| deep-off 早退 vs force（`:1601-1616` vs `:1627`） | **PASS**（實碼支持 S-F12） |
| tier 全 true loop（`:3369-3371`）排除 factor_return | **PASS**（Task 1.1 指定） |
| ModuleUnavailableError 新類型 | **PASS**（repo 尚無，屬預期新增） |
| long_short / net_ic / analyzer 本體不動 | **PASS** |

---

ASSUMPTIONS_VERIFIED: `ic_filter_orchestrator.py:1601-1616,1627,1651-1703,3335-3378`; SPEC r4 §C S-F9/S-F10~13、Task 1.1 邊界表、§G:35；r3 composer APPROVE 核心條款
TESTS_RUN: `sed`/`rg`/`shasum` 上述；`grep ModuleUnavailableError`→僅 SPEC/RECONCILE（預期）；review-only 未跑 pytest
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查）；r4 收窄契約、不引入新有限值路徑
產出檔: `handoffs/20260714-IC1CFR-STOPGAP-R4-composer.md`

DELTA-CONCUR-R4: APPROVE
