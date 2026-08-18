# Reconcile — 20260818-gap1-x-review-r21

**來源** 20260818-gap1-r11-review-codex.md, 20260818-gap1-r11-review-composer.md, 20260818-gap1-r11-review-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18；G1-R11 修補 code review）

三家共 **4 條** canonical ID（codex 2／composer 1 sentinel／grok 1 sentinel）；下列 **兩群集 P1–P2 引用全部 4 條，0 掉項**。
三家 Verdict **一致＝可合併**（無 P0／P1）；段 A 四項（判定式無 ε、兩路徑逐位等價、scope 入註解／測試、golden 三案例綠）三家皆核實；
段 B（signed zero／長度 2／inf 順序／`ptp` vs `all` 等價）三家皆未揭回歸。

### P1 — docstring 未同步 `ptp==0` 語意（`CODEX-R21-P2-01`）
**引用**: CODEX-R21-P2-01, COMPOSER-R21-P3-00, GROK-R21-P3-00

`sharpe.py:74`／`pbo.py:145` 之 Returns／docstring 仍只列 `std==0`。**處置（修，同 commit）**：兩處補「所有元素位元全等（`np.ptp==0`；G1-R11）」與 scope。composer／grok sentinel（無 finding）併入本群集作為「段 A–C 全核實」之紀錄。

### P2 — `np.ptp` 於 PBO 熱路徑之成本非零（`CODEX-R21-P2-02`）
**引用**: CODEX-R21-P2-02

codex 計時：924 path×50 候選之 PBO 由 1.09s → 1.61s（+0.52s／次；`np.all` 對照 1.34s）。brief 無效能門檻，非阻擋。
**處置（記錄，不改）**：PBO 為離線統計（每次數秒級可接受）；SPEC 對效能「不設硬門檻、S=16 wall-time 記錄於 receipt」。若日後需壓低，先以同 workload 立 budget 再決定改 `all` 或只在 `std<tol` 時才算 `ptp`——**不**在本輪引入。主委 brief「開銷可忽略」之 assumed 修正為「+0.5s／PBO（924×50），已量測、可接受」。

**Verdict**: 可合併 → docstring 同 commit 補齊；三家戳記後 G1-R11 關閉。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R21-P2-01
**斷言**: 新增的 `ptp==0` 退化語意未同步到兩個函式 docstring，文件仍只列 `std==0`。
**碼證**: `sharpe.py:74` 與 `pbo.py:145-146` 仍只寫 `std==0`；實作 `sharpe.py:89-93`、`pbo.py:151-153` 已加入 `ptp==0`。
**來源摘要**: momentum/Analysis/strategy_validation/sharpe.py#sha256:11fda76fba6b；momentum/Analysis/strategy_validation/pbo.py#sha256:1c6e80613e02
P2，信心度=High；維護者讀 API 說明會漏知 `80×0.01` 也會退化。合併不阻擋，後續同步 docstring 並保留「位元全等」scope。

## CODEX-R21-P2-02
**斷言**: 「`np.ptp` 於 924 path×50 candidate 開銷可忽略」不是已驗證事實，控制探針顯示非零熱路徑成本。
**碼證**: `timeout 120 venv/bin/python -c '<924-path×50 probe>'`：full PBO current `1.611551s`、去 ptp `1.094057s`；metric slice current `1.551454s`、去 ptp `1.042851s`；`np.all` 對照 `1.339006s`。
**來源摘要**: momentum/Analysis/strategy_validation/pbo.py#sha256:1c6e80613e02；handoffs/20260818-gap1-r11-review-BRIEF.md#sha256:6462c77d8ece
P2，信心度=Medium；絕對增加約 `0.52s/PBO`，但 brief 未給性能門檻，尚不足阻擋。若需壓低成本，先以相同 workload 建 budget，再決定是否改 `all`；本輪不改碼。

ASSUMPTIONS_VERIFIED: A–C；signed-zero/pair/inf 順序；finite-domain ptp/all 等價；scope；golden；§V-16 receipt；PBO timing。
TESTS_RUN: `timeout 120 venv/bin/python -m pytest .../test_sharpe.py .../test_pbo.py::{vectorized,golden_noise,golden_alpha_detectable,golden_alpha_undetectable} -q` → 19 passed rc=0；`timeout 180 venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` → 281 passed rc=0；`bash scripts/strategy_wiring_check.sh` → rc=0；custom timed probes → rc=0；`handoffs/run_receipts/20260818T120000Z-gap1-r11-mutation.log` → 21 mutants rc=1、post-restore rc=0。
FAILURES_SEEN: 初次 inline timing probe 語法錯；官方 probe 外層 SIGTERM 於 §V-4；`restore_golden_inventory.sh` rc=128（sandbox 禁建 `.git/index.lock`，inventory 未 dirty）。
SCOPE_CHANGES: 僅新增本產出檔；未改碼、未改測試、未 commit、未 push；既有 dirty files 保留。
NUMERIC_OR_SCHEMA_IMPACT: 未改輸出 schema／數值；review 記錄實測效能差異。
OUTPUT_ARTIFACT: `handoffs/20260818-gap1-r11-review-codex.md`
TMP_CLEANUP: 已移除本輪 `/tmp/codex-gap1-r21-mutation.log`、`/tmp/gap1_mut.log`；無 `/tmp/workdir`；保留 `/tmp/claude-501`。
STATUS: DONE
## COMPOSER-R21-P3-00

**斷言**: 本輪逐項核對段 A①–④、段 B①–⑤、段 C 探針 receipt 與 §0 前提後，修補忠於 consult r20 O1、無需額外 blocking／major finding。

**碼證**: `sharpe.py:88-93` 退化三條件無 ε；`pbo.py:149-153` 同構；`test_sharpe.py:105-117` 80×0.01⇒NaN＋微擾仍巨大有限；`test_pbo.py:120-138` 欄 7/8 與 `==` 鎖；receipt §V-16 1 failed；golden 三案例 pytest 全綠。RECHECK：`pytest tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_noise_band tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_detectable tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_undetectable tests/momentum/Analysis/strategy_validation/test_sharpe.py::test_non_binary_exact_constant_series_is_degenerate_not_huge_sharpe tests/momentum/Analysis/strategy_validation/test_pbo.py::test_vectorized_sharpe_matches_compute_sharpe -q`

**來源摘要**: momentum/Analysis/strategy_validation/sharpe.py#11fda76fba6b

[P3] 信心度=High。核對依據＝段 A–C 表＋本輪邊界探針；`_sharpe_pp_1d` docstring L145 未列 `ptp` 為輕微文檔缺口（L152 行內註解已補），不升格 finding。

---

## GROK-R21-P3-00

**斷言**: 本輪逐項核對後無 finding——段 A①–④ 忠於 consult r20 O1（精確 `std==0 or not finite or ptp==0`、兩路徑逐位等價、編碼值相等 scope 已入註解／測試 docstring、golden 三案例綠）；段 B①–⑤ 與段 C §V-16 receipt 未揭須修補之回歸或容差漏洞。

**碼證**: `sharpe.py:85-93`／`pbo.py:149-153` 判定同構且無 ε；`test_sharpe.py:105-117` 80×0.01⇒NaN＋微擾仍巨大有限；`test_pbo.py:120-138` 欄 7 NaN／欄 8 巨大有限＋`==` 鎖；本輪 pytest 5 passed rc=0；receipt §V-16 → 1 FAILED；B 探針 `-0/+0`／`[0.5,0.5]`／`inf` 順序／ptp↔all_eq 等價見上。RECHECK：同 VERIFY 專測命令＋讀 `handoffs/run_receipts/20260818T120000Z-gap1-r11-mutation.log` 之 §V-16 行。

**來源摘要**: momentum/Analysis/strategy_validation/sharpe.py#11fda76fba6b

[P3] 信心度=High。核對依據＝段 A–C＋本輪邊界／等價探針；`compute_sharpe` Returns 與 `_sharpe_pp_1d` docstring 未列 `ptp` 為文檔輕微缺口（註解＋測試 docstring 已披露 scope），不升格 finding。

---


## 戳記

RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:008b9d2af02af89bf87ef39d106423aec8fb266459c6a6a7fbefc4926930e682 task:20260818-GAP1-X-STAMP-R22
RECONCILE-STAMP: grok APPROVED 2026-08-18 sha256:008b9d2af02af89bf87ef39d106423aec8fb266459c6a6a7fbefc4926930e682 task:20260818-GAP1-X-STAMP-R22
RECONCILE-STAMP: codex APPROVED 2026-08-18 sha256:008b9d2af02af89bf87ef39d106423aec8fb266459c6a6a7fbefc4926930e682 task:20260818-GAP1-X-STAMP-R22
