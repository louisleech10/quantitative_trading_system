# G1-R11 修補 code review（三家全員；小任務；實作者＝Claude 主委，不自審）

VERIFY-EXEMPT:doc-example:gap1-r11-review-brief-questions

> 本檔為提問清單；結論在你們的產出與收斂檔。

brief-kind: review

## 審查標的（commit `16e5971c`；`git show 16e5971c --stat`）
- `momentum/Analysis/strategy_validation/sharpe.py`（退化條件併判 `float(np.ptp(values)) == 0.0`；註解明示「位元全等、不保證跨異源浮點表達式之數學相等」）
- `momentum/Analysis/strategy_validation/pbo.py::_sharpe_pp_1d`（同步同一判定）
- `tests/momentum/Analysis/strategy_validation/test_sharpe.py::test_non_binary_exact_constant_series_is_degenerate_not_huge_sharpe`（80×0.01 ⇒ NaN＋status；`0.01+1e-9·k` 仍有限且巨大）
- `tests/momentum/Analysis/strategy_validation/test_pbo.py::test_vectorized_sharpe_matches_compute_sharpe`（欄 7 斷言翻轉為 NaN；欄 8 微擾仍巨大有限；逐位 `==`）
- `scripts/gap1_b1_mutation_probe.sh` §V-16（拿掉 ptp 判定 ⇒ 轉紅）；receipt `handoffs/run_receipts/20260818T120000Z-gap1-r11-mutation.log`（21 條全 rc=1）
- 依據：consult r20 收斂檔 `handoffs/reconcile/20260818-gap1-x-consult-r20/synth.md`（三家一致採此方案、判為 SPEC 字面之實作修補、反對相對容差）

## 任務（小任務 review：段 A／B 必答）
**段 A — 是否忠於 consult 結論**：① 判定式是否恰為「`std==0 or not finite or ptp==0`」、無任何 ε／容差；② `sharpe.py` 與 `_sharpe_pp_1d` 是否**逐位等價**（`test_vectorized_sharpe_matches_compute_sharpe` 之 `==`）；③ CODEX-R20-P2-01 之 scope（編碼值相等）是否已寫進註解／測試 docstring；④ golden 三案例是否不受影響（`test_pbo.py` 三案例綠）。
**段 B — 攻**：① `float(np.ptp(values)) == 0.0` 對含 `-0.0`／`+0.0` 混合之序列（`ptp` 為 0.0；`std` 亦 0）⇒ 退化，合理？② 對長度 2 之序列 `[a, a]`（既有 `std==0` 已涵蓋）無回歸？③ 若 `values` 含 `inf`（前一關 `isfinite` 已擋）——`np.ptp` 不會被呼叫到，確認順序；④ 效能：`np.ptp` 於 PBO 924 path×50 候選是否可忽略（探針 baseline 278 passed 12s，前為 11s）；⑤ 有沒有更直接的寫法（`np.all(values == values[0])`，codex 建議）——是否值得換、或維持 `ptp`。
**段 C — 探針**：§V-16 之 mutant 是否對應 consult 建議；🔴 探針只由 codex 跑（互斥鎖），另兩家讀 receipt。自建探針加 timeout；產出檔尾 `STATUS: DONE`。

## 範本
`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` V13 之 §0／§1／§3 與 canonical 四欄。ID＝`## <FAMILY>-R21-P<0-3>-<NN>`，**本輪輪次=R21**（task-id `20260818-GAP1-X-REVIEW-R21`）；零 findings 用 sentinel `## <FAMILY>-R21-P3-00`。

## 本 brief 前提（逐條標）
fact-verified: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` → **281 passed**（Claude 實跑）
fact-verified: `bash scripts/gap1_b1_mutation_probe.sh` → rc=0、21 條皆 rc=1、baseline／post-restore 278 passed（receipt 見上）
fact-verified: `bash scripts/strategy_wiring_check.sh` → rc=0
assumed: `np.ptp` 之效能開銷可忽略 ← 請攻（段 B④）
assumed: `ptp==0` 與 `all(values==values[0])` 在有限值域上等價 ← 請攻（段 B⑤；`-0.0`／`+0.0` 例）

## ⚠️ 前置說明
禁改碼／禁 commit／禁 push；主委本輪不動工作區（`scripts/governance_families.json` 既有 no-op dirty 請忽略）。既有紅 2 條（`test_model_hyperparam_enhanced`）與本輪無關。

## 產出
Verdict（可合併／需修補後合併／不可合併）＋段 A–C 結論＋canonical findings。檔尾最後一行 `STATUS: DONE`。收尾清 /tmp workdir（保留 claude-501）。
