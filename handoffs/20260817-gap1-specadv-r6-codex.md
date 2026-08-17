# GAP-1 SPEC R6 複審 — CODEX

task-id: `20260817-GAP1-X-REVIEW-R6` ｜ family: `CODEX` ｜ target: `docs/GAP1_STRATEGY_OVERFIT_SPEC.md`
本輪審查 SPEC R5；SPEC sha256 前 12 碼＝`e0e426ca5389`。上一輪本家 findings：`CODEX-R4-P0-01`、`CODEX-R4-P1-01`、`CODEX-R4-P1-02`、`CODEX-R4-P1-03`。未修改 SPEC、程式、測試、golden、data_cache 或根 `HANDOFF.md`。

## Verdict：需修補後才能進 TODO 生成

四條上一輪 finding 均未能宣稱完整 CLOSED；本輪新 FATAL：`CODEX-R5-P0-01`～`CODEX-R5-P0-04`。它們分別可造成 PBO 數值分歧、DSR snapshot 綁定失效、top-K universe 污染通過、以及跨單位 DSR。BLOCKING 清單只列上述四條 FATAL。

## Closure table

| 上一輪 finding | 狀態 | 本輪 closure evidence |
|---|---|---|
| CODEX-R4-P0-01 | **CLOSED（原缺口）** | `SPEC:475-495` 已明定 path 級非有限 metric 剔除、剩餘 `<2` 跳過、全跳過 `all_paths_degenerate`；原本「讓 NaN 排序決定結果」已封。新發現的 rank 分母缺口另列 `CODEX-R5-P0-01`。 |
| CODEX-R4-P1-01 | **PARTIAL** | `SPEC:230-269` 已補 14 鍵、`reason_conditions`、row type/required、additional-properties 與 `ledger_row_invalid`；但 `SPEC:278` 驗收仍寫「13 個頂層鍵」，與 14 鍵 SoT 矛盾，列 RESIDUAL-OK。 |
| CODEX-R4-P1-02 | **PARTIAL / OPEN** | `SPEC:300-304` 已釘 `n_for_dsr == n_candidates_considered` 與 snapshot hash；`SPEC:375-395` 已改用 `ledger_result`。但 `PeriodReturns` 沒有命名 artifact hash，`LedgerReadResult` 只有 digest、沒有涵蓋集合，membership check 無法實作，且 ledger Sharpe 單位未定義；見 `CODEX-R5-P0-02`、`CODEX-R5-P0-04`。 |
| CODEX-R4-P1-03 | **OPEN** | `SPEC:513-527` 已封 `full_grid`／`external_declared`；但 `SPEC:458` PBO signature 沒有 `ledger_result`，`SPEC:286-304` 回傳型別也沒有 candidate-id 集合，故 `ledger_all_candidates` 的重算要求無輸入可執行；見 `CODEX-R5-P0-03`。 |

## 未關項二分（brief 必答 3）

| 未關項 | 判定 | 理由 |
|---|---|---|
| `SPEC:278` 的「13 個頂層鍵」殘字 | **RESIDUAL-OK** | 是契約驗收文字錯誤，可在 TODO Task 2.1 改成 14；不改變 B1–B4 數值。 |
| path exclusion 後仍用全域 `N_valid` 作 rank 分母 | **FATAL** | `rank/(N+1)` 會改變 `omega`，可改變 PBO；見 `CODEX-R5-P0-01`。 |
| snapshot digest 代替 artifact hash 集合 | **FATAL** | DSR 無法驗證 `period_returns` 是否屬於 ledger snapshot，會把不同輸入綁成同一統計物件；見 `CODEX-R5-P0-02`。 |
| `ledger_all_candidates` 無 candidate-id／ledger_result API 輸入 | **FATAL** | 呼叫方仍可只帶 top-K 矩陣與自算 hash，selection-free 守衛無法完成；見 `CODEX-R5-P0-03`。 |
| ledger `metric_value`／`valid_sharpe_values` 的 Sharpe 單位未釘 | **FATAL** | per-period 與 annualized 的跨 trial variance 尺度不同，SR0/DSR 不同；見 `CODEX-R5-P0-04`。 |
| snapshot canonical 序列與 candidate hash 演算法未寫死 | **RESIDUAL-OK** | 可在 TODO/測試一次鎖定 canonical ordering；目前主要風險是 fail-closed 不一致，非新增公式錯誤。 |
| `reason_conditions` 的每條自然語言條件未逐 reason 做行為 oracle | **RESIDUAL-OK** | 屬契約測試細節，可在 Task 2.1/2.2/3.2/4.3 驗收中釘死，不直接改變統計值。 |

## CODEX-R5-P0-01

**斷言**: PBO 在 path-level exclusion 後仍以全域 `N_valid` 正規化 OOS rank；同一 path 的實際候選數不同時，兩個合規實作可得到不同 `omega`，甚至改變 PBO 的負值判定。

**碼證**: `SPEC:465-479` 先允許候選按 path 剔除並以「剩餘有效候選」判斷跳過；但 `SPEC:472-474` 仍固定 `rank ∈ [1, N_valid]`、`r = rank/(N_valid+1)`，沒有 `N_path_valid` 或更新 `N_valid` 規則。實跑 `venv/bin/python -c 'from math import log; n_valid=3; n_path_valid=2; rank=2; ...'` → 全域分母 `r=0.5, omega=0.0`；path 分母 `r=0.6666666666666666, omega=0.6931471805599452`。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '465,495p'` 與同一 numeric probe。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#e0e426ca5389

[FATAL] 信心度=High；若 path 剔除候選 2 後仍以全域 N=3 計算，rank=2 的 `omega` 為 0；若按 path 剩餘 N=2，則為正值。這會直接改變 `omega < 0` 的 path 比例與 PBO。修法需在 TODO 前明定 path-local 候選數及 `r=rank/(N_path_valid+1)`，並加入 rank=2 的 oracle。

## CODEX-R5-P0-02

**斷言**: DSR 的 snapshot membership check 不可由現行 typed dataflow 實作：`snapshot_hash` 是單一 digest，`PeriodReturns` 未定義來源 artifact hash，`LedgerReadResult` 也未保留 hash 集合或 membership API。

**碼證**: `SPEC:160-174` 的 `PeriodReturns` 欄位沒有 `input_artifact_hash`；`SPEC:284-304` 的 `LedgerReadResult` 只有 `snapshot_hash`，其定義是 row hash 集合等資料的 sha256；`SPEC:375-395` 卻要求判斷 `period_returns` artifact hash 是否「屬於 `snapshot_hash` 所涵蓋集合」。digest 不可反推出集合，且 `period_returns` 沒有可比較欄位。RECHECK：`rg -n 'PeriodReturns|input_artifact_hash|snapshot_hash|涵蓋集合' docs/GAP1_STRATEGY_OVERFIT_SPEC.md`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#e0e426ca5389

[FATAL] 信心度=High；實作者只能省略檢查、重讀未傳入的 ledger，或自行發明 side channel；不同 artifact 的 returns 可在沒有可證偽 mismatch 的情況下進入同一 DSR。這會使 SR0 的跨 trial variance 與 `SR_obs` 不屬同一 snapshot，產出數值錯誤。修法需讓 `PeriodReturns` 帶 artifact identity，且讓 `LedgerReadResult` 保留可驗證的 canonical artifact-hash 集合（或等價不可變 membership proof）；只保存 digest 不足。

## CODEX-R5-P0-03

**斷言**: `ledger_all_candidates` 的 universe guard 文字要求無法由 PBO signature 與 `LedgerReadResult` 提供的欄位執行，故 top-K 子集仍可被呼叫方自我宣告為 ledger universe。

**碼證**: `SPEC:458-460` 的 `probability_of_backtest_overfitting` signature 只有 `returns_matrix`、N/S、metric、`universe_provenance`，沒有 `ledger_result`；`SPEC:286-304` 的 LedgerReadResult 欄位列 n、snapshot、semantics、values，沒有 candidate-id 集合；`SPEC:510-512` 卻要求由 ledger candidate-id 集合重算 hash。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '284,304p;456,460p;501,527p'`；並 `rg -n 'candidate_ids|candidate_id.*集合|ledger_result.*PBO' docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 確認無可傳集合。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#e0e426ca5389

[FATAL] 信心度=High；目前唯一可驗證成功路徑的資料源既不在函式參數，也不在 typed result。實作者若只傳 top-K matrix、`candidate_count` 與對該子集自算的 hash，仍能滿足現有 signature；PBO 會在被選過的 universe 上計算，造成過擬合機率偏誤。修法需把不可變 candidate-id artifact／LedgerReadResult 明列為 PBO 輸入，並明定 hash 的 canonicalization 與 count 對證。

## CODEX-R5-P0-04

**斷言**: ledger 的 `metric_value` 與 `valid_sharpe_values` 沒有 per-period／annualized 單位契約，DSR 的跨 trial variance 因而可被兩個獨立實作以不同尺度計算。

**碼證**: `SPEC:237-243` 只把 ledger `metric_value` 型別定為 float；`SPEC:284-304` 只把 `valid_sharpe_values` 定為 float list；`SPEC:369-384` 明確把 `sr_estimator_variance` 鎖為 per-period，卻沒有把 ledger Sharpe values 鎖到同一單位。`SPEC:384` 的 per-period 限定只列 `SR_obs`／moments／T，未涵蓋 `V[{SR_n}]`。RECHECK：`rg -n 'metric_value|valid_sharpe_values|per-period|annualized' docs/GAP1_STRATEGY_OVERFIT_SPEC.md`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#e0e426ca5389

[FATAL] 信心度=High；同一報酬序列以 `periods_per_year=730` 時 annualized Sharpe 相對 per-period Sharpe 放大 `sqrt(730)`，其跨 trial variance 放大 730，SR0 及 DSR 隨之改變。修法需在 ledger row／`LedgerReadResult.valid_sharpe_values` 明定 per-period 單位，並以 annualized 值誤餵會轉紅的 oracle 鎖住。

## 被當成事實的未驗證假設（§0）

- brief 假設 G1 已唯一實作：**部分成立**；14 鍵與 row metadata 已補，但 `SPEC:278` 仍自相矛盾。
- brief 假設 G2 snapshot 已使兩實作得到相同 DSR：**不成立**；digest 不提供 membership，且 ledger Sharpe 單位未定。
- brief 假設 G3 path／universe 已封閉：**不成立**；path rank 分母未更新，ledger candidate-id artifact 未進 dataflow。
- brief 假設剩餘皆 RESIDUAL-OK：**不成立**；上列四個缺口會改變數值或允許污染結果。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、AGENTS.md、R6 brief、review template、R5 本家產出、R5 synth、SPEC；工作樹既有變更已確認且未觸碰；SPEC digest 已實跑為 `e0e426ca5389...`。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`, rc=0；`sha256sum docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `e0e426ca53892a...`；path numeric probe → global `omega=0.0` vs path-local `omega=0.6931471805599452`, rc=0；未跑產品 pytest（本輪只審 SPEC，且 brief 禁改碼）。
FAILURES_SEEN: none。
SCOPE_CHANGES: 僅新增 `handoffs/20260817-gap1-specadv-r6-codex.md`；無越界，未改 SPEC、程式、測試、golden、data_cache 或根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: 未修改數值或 schema；指出 PBO rank 分母、DSR snapshot/單位與 universe provenance 的規格缺口。
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r6-codex.md`
HANDOFF_NOT_UPDATED: 根 `HANDOFF.md` 由 Claude 維護；本輪按 brief 只寫指定 review artifact。
TMP_CLEANUP: `/tmp/workdir` 目前不存在；`/tmp/claude-501` 已確認存在且保留。
STATUS: DONE
