Verdict: 可合併；無 P0/P1。兩項 P2 為非阻擋文件／效能驗證 follow-up。

段 A：PASS。`sharpe.py` 與 `_sharpe_pp_1d` 均恰為 `std==0.0 or not finite or ptp==0.0`，無 ε；逐位等價測試及 scope＝位元全等說明存在；三個 golden case 綠。
段 B：①②合理且無回歸（signed `-0.0/+0.0`、`[a,a]` 皆退化）；③ finite gate 在 `ptp` 前，含 `inf` 不呼叫 `ptp`；④ `ptp` 有可量測成本；⑤ 有限值域 `ptp==0` 與 `all(values==values[0])` 等價，依 consult 維持 `ptp`。
段 C：§V-16 mutant 確實移除 `ptp` guard；既有 receipt 為 21/21 rc=1，post-restore rc=0；本輪 timed custom probes rc=0。重跑官方 probe 被外層 SIGTERM 於既有 §V-4，最終 targets/lock 已恢復清潔。

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
