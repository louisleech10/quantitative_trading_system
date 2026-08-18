# GAP-2 B1 code review 收斂檔之 RECONCILE-STAMP 核可 v2（**codex 單家重驗**；工作區獨占）

VERIFY-EXEMPT:doc-example:gap2-b1-stamp-v2-brief-criteria

> 🔴 為何有 v2：r13 輪 composer／grok APPROVED、codex BLOCKED（判準 5 V-6 未轉紅／判準 9 pytest 1 failed／判準 10 diff 含清單外檔）。
> 主委查證：**codex 量到的是移動中的標的**——(a) 判準 9 之 1 failed＝`test_reason_literals_in_marginal_ic_subset_of_contract` 抓到裸字面 `_DECOY_REASON_LITERAL_FOR_STAMP`，該字面為他家族依 r13 判準 7「可在模組加一個裸字面驗它會紅」就地插入之實驗殘留（grok 交件檔亦記錄看到此殘留）；(b) 判準 5 之 V-6 未轉紅發生於同一時窗（receipt `20260818T154734Z`：post-restore 亦 1 failed＝decoy 仍在），而 composer（`20260818T154539Z`）與 grok（`20260818T155057Z`）之探針**十條全 RED（含 V-6）且 post-restore 46 passed**；主委於三家結束後在乾淨工作區重跑：`git status` 對 momentum/tests 零改動、`grep -c _DECOY marginal_ic.py`＝0、pytest 兩檔 **46 passed**；(c) 判準 10 之 `.claude/gate/audit.log`／`docs/site/*.html` 為 gate 與 plain_docs_render **hook 產物**（每次 commit 自動 stage），r13 brief 檔案清單漏列，屬 brief 措辭疏漏、非 scope 外改碼。
> **本輪只派 codex 一家**：工作區獨占（主委不動檔、無他家並行）；判準 7 改為 **in-memory**（monkeypatch／`ast.parse` 修改字串後 `exec`）**禁寫任何 repo 檔**。composer／grok 之 r13 APPROVED 戳記維持有效（同 body hash、同 commit）。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-gap2-b1-review-r12/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`78efca544667239988a3baf35b4023d6d71a37092539f625fa2bfef8c1c57619`；請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap2-b1-review-r12/synth.md` 重跑確認，不一致請 BLOCKED 而非照抄。

## 背景
本檔為 **B1 實作 code review**（`20260818-GAP2-B1-REVIEW-R12`）之收斂：三家 11 findings（codex 8／grok 2／composer sentinel），收斂為八群集 K1–K8（9 接受／K7 駁回附碼證／K8 sentinel）。修補已落在 commit `ede80b42`（延伸檔 A1-7）。本輪戳記**兼任修補驗收**：通過即 B1 CLOSED → 進 B2（Task 2.1–2.2）。

## 核可判準（逐項查；任一不成立即 BLOCKED）
1. **0 掉項**：`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260818-gap2-b1-review-r12/sources.lock` → PASS；八群集引用全部 11 個 canonical ID。
2. **K1（loader 副本）**：`git show ede80b42 -- momentum/Analysis/survivor_contract.py`；**用 codex 上一輪反例重跑**：`c=load_survivor_contract(); c["version"]=999; load_survivor_contract()["version"]` 應為 `1`。
3. **K3（`view_status_keys`）**：契約 `marginal_ic_section_keys` 含 `view_status_keys={additional_properties:false, keys:{status, reason}}`；**頂層鍵集未變**（`test_load_top_level_keys_exact` 綠）。
4. **K4（節級／視角級 status；本輪重點）**：**用你們的反例重跑**——(a) codex：`df["c"]=1.0` 單一常數 survivor ⇒ 節 `not_computed:no_computable_candidates`、三視角皆非 ok（removed ⇒ `not_applicable:no_removed_candidates`）；(b) grok：`max_survivors_for_loo=2`、survivors 3、extra 含可算之 `z` ⇒ 節 `not_computed:candidate_budget_exceeded`、`views.removed_candidates.status=="ok"`、`per_feature=={}`；(c) codex：test label 常數 ⇒ 候選 `not_computed:label_degenerate`（`marginal_ic.py` `_one` 內 gate 位於任何 `_spearman` 呼叫之前——請讀碼確認順序）。規則逐字見 A1-7。
5. **K5（V-3 窄測）**：`test_marginal_uses_spearman_not_pearson` 於重尾 label 下斷言 marginal 與 Spearman 參考 1e-12、與 Pearson 參考差 >0.05；`scripts/gap2_mutation_probe.sh` V-3 已改對映該測試；**請重跑** `bash scripts/gap2_mutation_probe.sh --batch B1`（約 2 分鐘；🔴 不可並行，鎖被持有 ⇒ rc=3 請稍後重試或讀 receipt `handoffs/run_receipts/20260818T154002Z-gap2-B1-probe.log`）並貼十條 RED／GREEN 與 rc。
6. **K6（O9 非平凡重抽）**：`test_o9_bootstrap_resamples_nontrivially`——**用 codex 之點估 mutant**（`block_bootstrap_ci -> (stat, stat)`）monkeypatch 後該測試應紅。
7. **K2（reason 字面 SoT 遵循方式）**：`test_reason_literals_in_marginal_ic_subset_of_contract` 之 AST 掃描是否真鎖「傳給 `_reason()` 之字串常數 ⊆ 契約組」且「reason 字面不得出現在 `_reason()` 之外」（**只准 in-memory**：讀取模組原始碼字串、以 `ast`／字串插入裸字面後 `exec` 於臨時 namespace 或 monkeypatch 契約 dict；**禁**寫入 repo 任何檔——r13 即因就地實驗污染他家量測）。主委對 codex「零命中不可達」之判斷是否誠實。
8. **K7 駁回是否成立**：`docs/GAP2_MARGINAL_IC_TODO.md` Task 1.0 步驟 4「頂層鍵集 `==` 上列集合否則 raise」與驗證①「頂層鍵集 `==`」——loader allowlist＋測試①逐字鍵集是否確為 TODO 指定；若你認為仍違 §0 JSON SoT ⇒ BLOCKED 並附理由。
9. **未破壞既有**：`venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py -q` → 46 passed；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py` → PASS。
10. Verdict 與內文一致；`git diff 022650ff ede80b42 --stat` 之**非 hook 產物**部分只含 B1 三模組＋兩測試＋探針腳本＋AMENDMENTS＋handoffs＋白話（`.claude/gate/audit.log` 與 `docs/site/*.html` 為 gate／plain_docs_render hook 自動 stage，非改碼）；無既有程式檔改動。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-18 sha256:<你實跑取得的完整 body sha256> task:20260818-GAP2-B1-STAMP-R14
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在你自己的交件檔寫可證偽的阻擋理由（例：反例仍可重現、探針某條未紅）。

## 硬性要求
1. **只** append 一行到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict／既有行。
2. **不得**把 findings 或評論 append 進 stamp-target（本輪產 stamp，不產 finding；新缺陷寫在你自己的交件檔並判 BLOCKED）。
3. 不得 commit、不得 push；跑探針時勿並行。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋判準 1–10 逐項結果（含反例重跑輸出與探針 rc）。收尾清 /tmp workdir（保留 claude-501）。
