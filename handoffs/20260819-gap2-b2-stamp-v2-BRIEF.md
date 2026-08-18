# GAP-2 B2 code review 收斂檔之 RECONCILE-STAMP 核可 v2（**codex 單家重驗**；L2 annotation 一行補正 commit `eb598289`）

> r16：composer／grok APPROVED；codex BLOCKED 於判準 3——`from __future__ import annotations` 下 `params: "MarginalICParams"` 之引號被保留為 `"'MarginalICParams'"`。已改為不加引號（`TYPE_CHECKING` 匯入不求值），`inspect.signature` 現顯示 `params: 'MarginalICParams'`（主委實跑）。其餘判準 1／2／4／5／6 codex r16 已 PASS；本輪只需重驗判準 3＋判準 5 迴歸，並 append 戳記（同 body hash）。

VERIFY-EXEMPT:doc-example:gap2-b2-stamp-brief-criteria

> 本檔為**給委員的核可判準清單**：各判準是「請你實測的項目」，不是主委的 operational 結論。
> 🔴 **所有實驗一律 in-memory（monkeypatch／exec）；禁寫任何 repo 檔**；探針有互斥鎖（rc=3 ⇒ 稍後重試或讀 receipt）。主委派出後不動工作區。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260819-gap2-b2-review-r15/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`9d0650065c052215ade7403008281ed981f548d67d323ffe9029669a3cfea5f2`；請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260819-gap2-b2-review-r15/synth.md` 重跑確認，不一致請 BLOCKED 而非照抄。

## 背景
B2 code review（`20260819-GAP2-B2-REVIEW-R15`）三家 4 findings（codex 2／composer sentinel／grok sentinel）收斂為 L1–L3；修補已落在 commit `127e8e77`（延伸檔 A1-8）＋補正 `eb598289`。本輪戳記**兼任修補驗收**：通過即 B2 CLOSED → B3。

## 核可判準（逐項查；任一不成立即 BLOCKED）
1. **0 掉項**：`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260819-gap2-b2-review-r15/sources.lock` → PASS；三群集引用全部 4 個 canonical ID。
2. **L1（CI 恆含點估）**：`git show 127e8e77 -- momentum/Analysis/factor_combiner.py`——`block_bootstrap_ci` 回傳 `(min(q025, point), max(q975, point))`；**用 codex 上一輪反例重跑**（O2 三因子、`block_len=7`、`seed=1`、`n_bootstrap=1`）⇒ `delta_ci95` 含 `delta_vs_top_train_single`；`marginal_ic.ci95` 同源（`test_o9_bootstrap_seed_determinism` 之 `n_bootstrap=1` 含點估斷言）。主委首版曾試「分佈納入觀測統計量」被 K6 測試打回（內插分位數仍可不含）——請確認 A1-8 定義為包絡而非納入。
3. **L2（typed 簽名）**：`inspect.signature(combine_factors)` → `params: 'MarginalICParams'`、`fit_scope: "Literal['train', 'full_sample']"`；runtime guard（未知 `fit_scope`／`weights_method` raise）仍在。
4. **探針**：`bash scripts/gap2_mutation_probe.sh --batch B2` rc=0（V-7／8／9 RED＋還原綠）；receipt `handoffs/run_receipts/20260818T224246Z-gap2-B2-probe.log`。
5. **未破壞既有**：`venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` → 45 passed；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` → PASS。
6. Verdict 與內文一致；`git diff d026fbed 127e8e77 --stat` 之非 hook 產物只含 `factor_combiner.py`／兩測試檔／AMENDMENTS／handoffs／白話（`.claude/gate/audit.log`、`docs/site/*.html` 為 hook 自動 stage）。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-19 sha256:<你實跑取得的完整 body sha256> task:20260819-GAP2-B2-STAMP-R17
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在你自己的交件檔寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 一行到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict／既有行。
2. **不得**把 findings 或評論 append 進 stamp-target；新缺陷寫在你自己的交件檔並判 BLOCKED。
3. 不得 commit、不得 push；禁就地改檔；探針勿並行。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋判準 1–6 逐項結果。收尾清 /tmp workdir（保留 claude-501）。
