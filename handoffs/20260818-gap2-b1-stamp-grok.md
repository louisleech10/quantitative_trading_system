# GAP-2 B1 stamp — grok（20260818-GAP2-B1-STAMP-R13）

**判定**: APPROVED  
**body_sha256**: `78efca544667239988a3baf35b4023d6d71a37092539f625fa2bfef8c1c57619`（`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap2-b1-review-r12/synth.md` 實跑一致；append 戳記後 body 不變）  
**修補 commit**: `ede80b42`  
**stamp-target**: `handoffs/reconcile/20260818-gap2-b1-review-r12/synth.md`（已 append 一行 RECONCILE-STAMP）

## 判準 1–10

| # | 判準 | 結果 |
|---|------|------|
| 1 | completeness 0 掉項 | PASS — `bash scripts/completeness_check.sh --lock …/sources.lock` rc=0；codex 8 + composer 1 + grok 2 = 11/11 |
| 2 | K1 loader 副本 | PASS — `c["version"]=999` 後 `load_survivor_contract()["version"]==1`；`same_object False`；`ede80b42` 回傳 `copy.deepcopy` |
| 3 | K3 view_status_keys | PASS — `view_status_keys={additional_properties:false, keys:{status, reason(nullable)}}`；頂層 24 鍵不變；`test_load_top_level_keys_exact` 綠 |
| 4 | K4 節級／視角級 status | PASS — 反例見下；`_one` 內 `label_degenerate` gate（ptp）位於任何 `_spearman` 之前（源碼序 lab≪marg_sp≪gross_sp） |
| 5 | K5 V-3 窄測 | PASS — V-3 對映 `test_marginal_uses_spearman_not_pearson`；`bash scripts/gap2_mutation_probe.sh --batch B1` **rc=0**，十條 RED+RESTORED GREEN（receipt `20260818T155057Z`） |
| 6 | K6 O9 非平凡重抽 | PASS — monkeypatch `block_bootstrap_ci→(stat,stat)` 後 `test_o9_bootstrap_resamples_nontrivially` **紅**；舊 O9 seed 測在同 mutant 下仍綠（證 K6 補洞成立） |
| 7 | K2 reason SoT | PASS — AST 子集測綠；契約 reason 改名 ⇒ 紅；模組加裸 `"no_survivors"` 字面 ⇒ 紅（測完 `git checkout` 還原）。主委「零命中不可達」判斷誠實：reason 須語意名，子集＋成員檢查已為本票 SoT 遵循方式 |
| 8 | K7 駁回 | 同意駁回 — TODO Task 1.0 步驟 4／驗證① 明文頂層鍵集 `==`；loader `SURVIVOR_CONTRACT_TOP_KEYS`＋測試① 為指定 fail-closed 守衛；A1-7 豁免成立；非 §0 欄位表複列 |
| 9 | 未破壞既有 | PASS — 乾淨樹上 `pytest …test_survivor_contract.py …test_marginal_ic.py -q` → **46 passed**；`mutation_probe_check.sh` → PASS |
| 10 | diff 範圍 | PASS（附註）— `022650ff..ede80b42` 產品面僅 B1 三模組＋兩測試＋探針＋AMENDMENTS；另含 handoffs／白話 md＋`docs/site/*.html`（白話 sync）＋`.claude/gate/audit.log`（hook 留痕），無既有引擎／API 邏輯改動 |

## 判準 4 反例輸出

```
K4(a) constant survivor c=1.0:
  section=not_computed no_computable_candidates
  views.loo/sequential=not_computed:no_computable_candidates
  views.removed_candidates=not_applicable:no_removed_candidates
  per_feature.c=(not_computed, residual_degenerate)

K4(b) max_survivors_for_loo=2, survivors=[s1,s2,f], extra=[z]:
  section=not_computed candidate_budget_exceeded
  views.removed_candidates.status=ok; z.status=ok
  per_feature={}; n_regressions=1

K4(c) test-label 常數:
  features s1/s2=(not_computed, label_degenerate)
  section=not_computed no_computable_candidates
```

## 判準 5 探針摘要

```
bash scripts/gap2_mutation_probe.sh --batch B1 → rc=0
receipt: handoffs/run_receipts/20260818T155057Z-gap2-B1-probe.log
baseline/post: 46 passed
V-1,V-2,V-3(test_marginal_uses_spearman_not_pearson),V-4,V-5,V-6,V-17a,V-18,V-21,V-22a:
  各 RED ✓ + RESTORED GREEN ✓
```

## 並行污染觀察（非產品缺陷）

戳記輪期間他家族探針／K2 反例曾就地 mutate 共用工作區：曾見 `_DECOY_REASON_LITERAL_FOR_STAMP` 殘留、`20260818T154734Z` V-6 未轉紅＋post-restore 1 failed、`20260818T154919Z` baseline 非綠。本家於 `git checkout -- momentum/Analysis/marginal_ic.py` 後獨立重跑：pytest 46／探針 10/10／mpc PASS。codex 之 BLOCKED（V-6／判準 9）對應該污染時窗之 receipt，與乾淨樹實跑不一致。

## Verdict 一致性

收斂檔 Verdict「需修補後進 B2」；`ede80b42` 落地 K1–K6；本輪反例／探針／pytest 於乾淨樹全過 ⇒ 修補驗收成立，B1 可 CLOSED → B2。

TMP_CLEANUP: `/tmp/workdir` 與 `/private/tmp/workdir` 均不存在；`/tmp/claude-501` 保留；本 session `/tmp/gap2-b1-stamp-*.log` 刪除被權限策略擋（非 workdir）。

ASSUMPTIONS_VERIFIED: body hash 實跑=brief 宣告；修補在 ede80b42；A1-7／TODO 1.0 步驟 4／驗證① 已讀；Python 3.9.6 venv；未 commit／push
TESTS_RUN: reconcile_body_hash；completeness_check rc=0；pytest 46；mutation_probe_check PASS；gap2_mutation_probe B1 rc=0（155057Z）；K1/K4 反例；K6 point-estimate mutant RED；K2 decoy+rename 紅後還原
FAILURES_SEEN: 首次 probe 因鎖 rc=3；並行污染導致中間 baseline／V-6 假紅——還原後重跑通過
SCOPE_CHANGES: 僅 append 一行 stamp 至 synth.md；新增本交件檔
NUMERIC_OR_SCHEMA_IMPACT: none（驗收取證 only）

STATUS: DONE
