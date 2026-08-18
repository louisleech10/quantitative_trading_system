# GAP-2 B1 stamp — composer（20260818-GAP2-B1-STAMP-R13）

**判定**: APPROVED  
**body_sha256**: `78efca544667239988a3baf35b4023d6d71a37092539f625fa2bfef8c1c57619`（`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap2-b1-review-r12/synth.md` 實跑一致）  
**修補 commit**: `ede80b42`  
**stamp-target**: `handoffs/reconcile/20260818-gap2-b1-review-r12/synth.md`（已 append 一行 RECONCILE-STAMP）

## 判準 1–10

| # | 判準 | 結果 |
|---|------|------|
| 1 | completeness 0 掉項 | PASS — `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260818-gap2-b1-review-r12/sources.lock` → 11/11 ID 全在綜合檔 |
| 2 | K1 loader 副本 | PASS — `c=load_survivor_contract(); c["version"]=999; load_survivor_contract()["version"]` → `1`；`git show ede80b42 -- survivor_contract.py` 確認 cache 回傳 `copy.deepcopy` |
| 3 | K3 view_status_keys | PASS — 契約 `marginal_ic_section_keys.view_status_keys={additional_properties:false, keys:{status, reason}}`；`test_load_top_level_keys_exact`＋`test_view_status_keys_match_contract` 綠 |
| 4 | K4 節級／視角級 status | PASS — 反例重跑：(a) `df["c"]=1.0` ⇒ 節 `(not_computed, no_computable_candidates)`、三視角皆非 ok、removed `not_applicable:no_removed_candidates`；(b) `max_survivors_for_loo=2`、survivors 3、extra `z` ⇒ 節 `(not_computed, candidate_budget_exceeded)`、`views.removed_candidates.status==ok`、`per_feature=={}`；(c) label 常數 ⇒ `label_degenerate`；`marginal_ic.py` L479–481 label gate 先於 L498 `_spearman` |
| 5 | K5 V-3 窄測 | PASS — `test_marginal_uses_spearman_not_pearson` 綠；`bash scripts/gap2_mutation_probe.sh --batch B1` rc=0，10/10 RED+RESTORED GREEN（receipt `20260818T154539Z`） |
| 6 | K6 O9 非平凡重抽 | PASS — codex 點估 mutant `block_bootstrap_ci→(s,s)` 重跑 min CI width=0.0（會紅）；`test_o9_bootstrap_resamples_nontrivially` 綠 |
| 7 | K2 reason SoT | PASS — `test_reason_literals_in_marginal_ic_subset_of_contract` 綠（AST 鎖 `_reason()` 第三引數 ⊆ 契約組＋reason 字面不得出現 `_reason()` 外）；主委「零命中不可達」判斷誠實（reason 選擇必須有語意名，測試鎖子集＋fail-closed 成員檢查已足） |
| 8 | K7 駁回 | 同意駁回 — TODO Task 1.0 步驟 4／驗證① 明示頂層鍵集 `==` 守衛；loader allowlist＋測試 ① 為 TODO 指定 fail-closed，非欄位表複列；A1-7 豁免成立 |
| 9 | 未破壞既有 | PASS — `pytest …test_survivor_contract.py …test_marginal_ic.py -q` → 46 passed；`mutation_probe_check.sh` → PASS |
| 10 | diff 範圍 | PASS（附註）— 核心 B1 三模組＋兩測試＋探針＋AMENDMENTS＋handoffs＋白話皆在 `022650ff..ede80b42`；額外 `.claude/gate/audit.log`（hook 留痕）與 `docs/site/*.html`（白話 sync 產物）無產品邏輯改動 |

## 探針摘要（判準 5）

```
bash scripts/gap2_mutation_probe.sh --batch B1 → rc=0
V-1..V-22a 十條：RED ✓ + RESTORED GREEN ✓
baseline/post: 46 passed
receipt: handoffs/run_receipts/20260818T154539Z-gap2-B1-probe.log
```

## K4 反例輸出（判準 4）

```
K4(a) section: not_computed no_computable_candidates
K4(a) views: loo/sequential=not_computed:no_computable_candidates; removed=not_applicable:no_removed_candidates
K4(b) section: not_computed candidate_budget_exceeded; removed view ok; per_feature={}; z status ok
```

## Verdict 一致性

收斂檔 Verdict「需修補後進 B2」；修補 commit `ede80b42` 落地 K1–K6；本輪反例／探針／pytest 全通過 ⇒ B1 可 CLOSED → B2。

TMP_CLEANUP: `/tmp/workdir` 與 `/private/tmp/workdir` 均不存在；`/private/tmp/claude-501` 保留；本 session 探針 log 在 `/tmp/gap2-b1-probe-composer.log`（shell 刪除被權限阻擋，無 workdir 需清）。

ASSUMPTIONS_VERIFIED: body hash 實跑=brief 宣告值；修補在 `ede80b42`；Python 3.9.6 venv；未 commit/push
TESTS_RUN: reconcile_body_hash/completeness_check/pytest 46/mutation_probe_check/gap2_mutation_probe B1 rc=0/K1-K4 反例/K6 mutant
FAILURES_SEEN: none
SCOPE_CHANGES: append 一行 stamp 至 synth.md；新增本交件檔
NUMERIC_OR_SCHEMA_IMPACT: 無（驗收取證 only）

STATUS: DONE
