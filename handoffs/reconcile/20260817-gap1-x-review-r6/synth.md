# Reconcile — 20260817-gap1-x-review-r6

**來源** 20260817-gap1-specadv-r6-codex.md, 20260817-gap1-specadv-r6-composer.md, 20260817-gap1-specadv-r6-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-17；SPEC R5→R6，宣告為最終 SPEC 輪）

三家共 **6 條** canonical ID（codex 4 條 FATAL／grok 1 個 zero-findings sentinel／composer 1 個 sentinel）。
下列兩群集**引用全部 6 條，0 掉項**。
VERIFY: 逐 ID `grep -c <ID> docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 4/4 皆 ≥1（Claude 實跑 2026-08-17）；
`bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → TEMPLATE PASS；
`grep -c "13 個頂層" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → 0（三家共同指出之殘字已清）。

### 家族 Verdict（本輪採 FATAL／RESIDUAL-OK 二分制）
- **composer：可進 TODO，FATAL 無**（G1–G3 逐條複驗全 CLOSED；四項殘留全判 RESIDUAL-OK）。
- **grok：可進 TODO，FATAL 無**（零 findings sentinel；殘留全判 RESIDUAL-OK，明言「不重開修訂輪」）。
- **codex：4 條 FATAL**（PBO per-path rank 分母／snapshot membership 不可實作／
  universe 守衛缺 candidate_ids 與 ledger 輸入／ledger Sharpe 單位未釘）。
**主委裁決＝四條全採並修**（不以「另兩家判無 FATAL」壓過）：主委逐條複核後認定 codex 之
FATAL 標籤成立——四者皆**會改變數值或使守衛不可實作**，且修補各為 SPEC 內一處寫死。
此為「看碼證不數人頭」之直接適用。

### H1 — 四條 FATAL（全採，逐條修補）
**引用**: CODEX-R5-P0-01, CODEX-R5-P0-02, CODEX-R5-P0-03, CODEX-R5-P0-04

1. **PBO rank 分母（P0-01）**：R5 加了 path 級剔除（步驟 3b），但 `r = rank/(N_valid+1)` 仍用**全域**
   有效候選數 ⇒ 同一 path 實際候選數不同時，兩合規實作得到不同 `ω`，甚至翻轉 PBO 之負值判定。
   **處置**：改 `r = rank/(N_valid_on_path + 1)`，並明示平均排名等價於
   `scipy.stats.rankdata(method="average")`；新增驗收 ④c（構造 5 vs 3 有效候選之雙 path fixture，
   以「champion 名次相同而 `ω` 不同」證明分母生效）。
2. **snapshot membership 不可實作（P0-02）**：主委前版要求「驗 `period_returns` 之 artifact 屬
   `snapshot_hash` 涵蓋集合」，但 `snapshot_hash` 是**單一 digest**，數學上無法做集合成員測試；
   且 `PeriodReturns` 未帶來源 hash。**處置**：`LedgerReadResult` 新增
   `artifact_hashes: frozenset[str]`（保留集合本身）；`PeriodReturns` 新增必填
   `source_artifact_hash`；membership 改為集合成員測試。
3. **universe 守衛缺輸入（P0-03）**：Task 4.3 文字要求驗 ledger candidate 集合，但 Task 4.2 之簽名
   **沒有** `candidate_ids` 或 `ledger_result` ⇒ 守衛只能比對呼叫方自算之 hash，top-K 污染仍可通關。
   **處置**：簽名新增 `candidate_ids`（與矩陣欄一一對應）與 `ledger_result`；守衛改驗
   **集合相等**（`set(candidate_ids)` == ledger candidate_id 集合）＋count 三方相等＋
   canonical hash（**唯一定義＝`sha256(",".join(sorted(candidate_ids)))`**，同時關閉 R5 之
   「hash 演算法未逐字」殘留）；新增驗收 ⑤b＝codex 原始 top-K 反例（50 選 10 且自算 hash 正確 ⇒ 仍拒）。
4. **ledger Sharpe 單位未釘（P0-04）**：`metric_value` 無單位契約 ⇒ per-period 與 annualized 混入時
   跨 trial variance 尺度不同 ⇒ SR0/DSR 不同。**處置**：`ledger_record_keys` 新增必填
   `metric_unit`（值集合住新頂層鍵 `metric_unit_values` ＝ `per_period`／`annualized`）；
   `valid_sharpe_values` **只**收 `per_period`，混入 `annualized` ⇒ 該 row 記 `ledger_row_invalid`
   且不入樣本；頂層鍵 14→**15**。

### H2 — 三家共同殘字與 sentinel 記錄
**引用**: GROK-R5-P3-00, COMPOSER-R6-P3-00

三家（含兩個 sentinel 之 body）皆指出 Task 2.1 驗收⑤ 仍寫「13 個頂層鍵齊備」而正文已 14
⇒ 併同 H1-4 一次更正為 **15**，並新增驗收⑥（`metric_unit_values` 內容＋`reason_conditions`
與 `reasons` 雙向相等）。兩 sentinel 之複驗結論（G1–G3 全 CLOSED、無 FATAL）一併記錄。

### 未採納 / 部分採納
- **無整條否決**。composer／grok 之「四項/多項 RESIDUAL-OK」判斷**部分未採用**：其中
  「`candidate_set_hash` canonical 演算法未逐字」與「OOS 平均排名 partial tie 未寫代數式」
  已於本輪一併寫死（因與 H1-1／H1-3 之修補同處，順手關閉成本為零），
  不留待 TODO。其餘 RESIDUAL-OK 判斷採用（見下）。

### 進 TODO 時攜帶之具名殘留（主委彙整，非阻擋）
1. §N 既有五項待接線（Optuna 生產者／output service 矩陣／`ml_pipeline` 掛載／前端面板／策略 wiring 閘門）。
2. C1 六條生產 bypass（生產者未接線前無法機器阻止；契約層已 fail-closed）。
3. `api/routes/ml_pipeline.py` 可消費不合格冠軍（**使用者裁決**降級展示不硬擋所致）。
4. adaptive search 之 effective independent N 不做換算（`n_independence="unverified"`）。
5. MinBTL 上界之近似誤差未量化（需獨立 Monte Carlo）。
6. `universe_provenance` dataclass 之欄位逐字列舉留待 TODO Task 4.3（composer 判 RESIDUAL-OK）。

**Verdict**: 需修補後合併 → **已於 SPEC R6 逐條修補完成**（4/4 FATAL 具名引用、殘字已清、`template_check` PASS）。
收斂軌跡：R1 23 → R2 7 → R3 11 → R4 7 → R5 4（全部為同一批 codex 細節族且皆一行級修補）。
**下一輪為範圍受限之閉合複驗**（僅複驗本輪四條 FATAL，不受理新一般性 SPEC 議題）；
該輪通過即進 TODO；若 codex 於受限輪再產同型新項，主委依「95% 解法就收」具名殘留後進 TODO。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R6-P3-00

**斷言**: 本輪逐項核對 R5 closure（本家 sentinel、reconcile G1–G3 共 7 條引用修補）與 brief 四條 assumed 攻擊後，無達 **FATAL** 門檻之新缺陷。

**碼證**: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS；μ 重算與 §G:108-109 一致；6 條 R4 finding ID grep≥1；G1 `SPEC:230-268`、G2 `SPEC:290-303,376-395`、G3 `SPEC:475-527` 對照；`cross_trial_sr_values` 僅註解殘留。RECHECK：同上命令＋`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '230,278p;290,303p;375,395p;475,527p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#e0e426ca5389

[P3] 信心度=High。核對依據＝closure 表 §1–§2 逐條狀態＋§5 assumed 表＋§4 RESIDUAL-OK 二分；刻意不捏造 finding 湊數。

---

ASSUMPTIONS_VERIFIED: template_check PASS；μ bit-match；6 ID grep≥1；G1–G3 段落對照；§4 殘留皆 RESIDUAL-OK
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS rc=0；`venv/bin/python -c "import math; ..."` μ 重算；6× `grep -c`；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r6-composer.md --family composer` → `COMPLETENESS PASS(single)` rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC）
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r6-composer.md`
TMP_CLEANUP: `/tmp/workdir` 不存在；`/tmp/claude-501` 保留未動
STATUS: DONE
## GROK-R5-P3-00

**斷言**: 本輪逐項核對 R4 本家 2 條、R5 收斂 G1–G3（含 codex 四條 BLOCKING 之 SPEC R5 修補）與 brief 四條 assumed 攻擊後，**無 FATAL finding**；剩餘不一致皆為可在 TODO 釘死之 RESIDUAL-OK（見 §3），不阻擋 TODO 生成與 B1 開工。

**碼證**: (1) `template_check` PASS；(2) SPEC sha `e0e426ca5389`；(3) 六 ID grep-c 皆 ≥1；(4) L230-268 十四鍵＋reason 雙向＋ledger 物件＋11 reasons；(5) L290-304／L375-395 `n_for_dsr`／`snapshot_hash`／驗收⑤更名；(6) L475-495／L509-527 path 3b＋universe 唯一 ledger 成功；(7) 殘字僅 L278「13 個頂層」與 snapshot 成員語意／N_eff 分母——均未達「不修則數值錯誤或不可重現且無法於 TODO 鎖定」之 FATAL 門檻。RECHECK：`grep -n '14 個頂層\|n_for_dsr\|all_paths_degenerate\|ledger_all_candidates\|13 個頂層' docs/GAP1_STRATEGY_OVERFIT_SPEC.md`；重讀 Task 2.1／2.2／3.2／4.2／4.3。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#e0e426ca5389

[P3] 信心度=High。核對依據＝§1／§1b closure 表＋§2 assumed 表＋§3 二分；刻意不捏造實質 finding 湊數。本輪核對後無 finding（sentinel）。

---


## 戳記

（待三家 append RECONCILE-STAMP）
