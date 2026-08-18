# GAP-1 SPEC — Amendments A1（延伸決策檔）

> 母 SPEC：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（R8，2026-08-17，定版）。
> **母 SPEC 不就地改寫**（凍結文件修訂走延伸檔；使用者 2026-08-01 定死）。本檔為延伸層：
> 記錄 TODO 第一輪 adversarial（`20260817-GAP1-X-REVIEW-R8`，三家 22 findings ＋主委自產 3 條 P0）
> 之收斂處置中**屬 SPEC 義務**者。實作端讀 TODO 即可；本檔用於 SPEC↔TODO 對證與後續輪次審查。
> 收斂檔：`handoffs/reconcile/20260817-gap1-x-review-r8/synth.md`（群集 J1–J6）。
> **義務效力**：本檔條目**取代**母 SPEC 對應行之義務；衝突時以本檔為準（逐條註明母 SPEC 行號）。

| 項 | 值 |
|---|---|
| 生效條件 | 三家 `RECONCILE-STAMP` 於 r8 收斂檔 ＋ R9 受限複驗 closure ⇒ TODO Frozen |
| 修訂類別 | D 延伸（`whole-body` 模式；母 SPEC 無 `STAMP-MODE` 標記＝legacy） |
| 觸發 finding | 詳見各條「來源」欄（canonical ID 可回查 r8 收斂檔附錄） |

---

## A1-1 — §G 第 3 類 alpha oracle 改以 per-period SR 定義（母 SPEC §G:110-119）

- **來源**：`CLAUDE-R8-P0-01`（主委自產版；實跑 receipt
  `handoffs/run_receipts/20260817T143000Z-gap1-todoadv-claude-pbo-probe.{py,log}`）。
- **被推翻之母 SPEC 宣稱**：`mu = 0.01 * 1.0 / sqrt(8760)` ＝ `1.068434607926721e-04` ⇒ `PBO < 0.30`。
  實測 PBO ＝ **0.5411**（`default_rng(T,N)`）／**0.6201**（`(N,T).T`）／**0.5487**（legacy `seed`）。
  根因＝per-period SR≈0.0107 遠小於 IS/OOS 各 600 obs 之 SR 標準誤 ≈0.0408 ⇒ alpha 候選不穩定當 champion。
  **推導式本身無誤，錯的是「該 alpha 可被 CSCV 偵測」這個未驗證假設。**
- **修訂**：§G 第 3 類 alpha 案例改為 **三個** golden 案例（皆住 `gap1_reference_cases.json`）：
  1. `noise`：無 alpha ⇒ 見 A1-2 之 band。
  2. `alpha_detectable`：`mu = sigma_per_period * 0.15`（`= 0.01 * 0.15 = 1.5e-03`；provenance＝
     「per-period SR 0.15 ＝ 3.68 個 IS 標準誤，設計上可被 CSCV 偵測」）⇒ **`pbo < 0.30`**
     （主委實跑：legacy seed 0.0054、`default_rng` 0.0000）。
  3. `alpha_undetectable`：`mu = 0.01 * 1.0 / sqrt(8760)`（原案例，語意改為誠實反例：
     年化 SR 1.0 之 alpha 在 T=1200 之 1h 資料上**不可**偵測）⇒ **`pbo > 0.40`**（實測 0.5411／0.6201／0.5487）。
- **不可做**：不得為使 `alpha_undetectable` 通過而縮小 band 或改 `sigma`；不得刪除該案例
  （它是「PBO 不會把弱 alpha 誤判為穩健」之唯一 oracle）。

## A1-2 — §G 全噪音 band 與 RNG 逐字寫死（母 SPEC §G:108-110、§V 之 golden 條）

- **來源**：`CLAUDE-R8-P0-02`。
- **被推翻之母 SPEC 宣稱**：`seed=20260817`、`N=50`、`T=1200`、`S=12`、σ=0.01 ⇒ `PBO ∈ [0.40, 0.60]`。
  實測三種合理實作有兩種落在 band 外（0.6483／0.6158／0.5357）⇒ 未指定 RNG API 與抽樣形狀順序 ⇒ golden 不可重現。
- **修訂**：
  1. golden 檔與 TODO 逐字寫死生成式：
     `rng = np.random.default_rng(20260817)`；`M = rng.standard_normal((n_obs, n_candidates)) * 0.01`
     （形狀即 `(T, N) = (1200, 50)`，`S=12`，dtype `float64`）。
  2. band 由 `[0.40, 0.60]` 放寬為 **`[0.30, 0.70]`**。理由（可證偽）：924 個 CSCV path 共用同一組觀測，
     path 間高度相關 ⇒ 有效獨立樣本遠小於 924，單 seed 之 PBO 抽樣散布遠大於 `sqrt(0.25/924)=0.016`；
     主委三變體實測極差 0.113（0.5357–0.6483）已逼近原 band 全寬 0.20。
  3. golden `provenance` 須記錄三變體實測值（0.6483／0.6158／0.5357）與本條理由，供未來收緊時對照。
- **誠實邊界**：band 放寬降低該 oracle 之鑑別力；鑑別力由 A1-1 之 `alpha_detectable`（`<0.30`）與
  `alpha_undetectable`（`>0.40`）承接，三案例合起來才構成 PBO 行為 oracle。

## A1-3 — §V-4 mutation 改為可證偽形式（母 SPEC §V:626 第 4 條）

- **來源**：`CLAUDE-R8-P0-03`。
- **被推翻之母 SPEC 宣稱**：「CSCV 之 IS/OOS 對調 ⇒ Task 4.2 斷言①② 至少一條轉紅」。
  `itertools.combinations(range(S), S//2)` 之枚舉對補集封閉 ⇒ 對調只重排 path 順序，PBO **逐位相同**
  （實測 swapped 0.6483／0.6158／0.5357，與原值相等）⇒ 該 mutation 永不轉紅，B4 gate「13 條全部貼 rc」不可達。
- **修訂**：§V-4 改為「**champion 改由 OOS metric 選**（`argmax(oos_metrics)` 取代 `argmax(is_metrics)`）
  ⇒ `alpha_detectable` 與 `noise` 兩案例至少一條轉紅」。理由：此 mutation 直接破壞 PBO 之
  「IS 選、OOS 評」語意，PBO 會趨近 0（選法看起來永遠正確）。

## A1-4 — Task 4.3／4.2：新增 `universe_scope` 可觀測欄位（母 SPEC:583-599、:556-560）

- **來源**：`CODEX-R8-P0-01`（BLOCKING）。
- **成立之攻擊**：三項守衛（集合相等／count 三方／canonical hash）證明「PBO 之候選集合＝ledger 記錄之集合」，
  **不**證明「ledger 記錄了全部試過的候選」。若生產者只把事後挑出的 top-K 寫入 ledger，三項全符仍回 `ok`。
- **不採之兩案**：① 不可偽造之 exhaustive proof——純統計層無外部候選宇宙 SoT，本層不可能；
  ② 一律回非 `ok`——會使 PBO 在任何情況皆不可用，違使用者裁決之交付範圍 A。
- **修訂（第三案，較嚴且可觀測）**：
  1. `PBOResult` 新增欄位 `universe_scope: str`；值集合住 Task 2.1 之**新增頂層鍵** `universe_scope_values`
     ＝`["ledger_recorded_only"]`（今日唯一合法值；G1-R4 落地後可加 `producer_conformance_verified`）。
     ⇒ Task 2.1 頂層鍵 **15 → 16**。
  2. `report.py` 之 `pbo` 節 required 鍵含 `universe_scope`；`build_validation_section` 於
     `pbo.universe_scope == "ledger_recorded_only"` 時**強制** `display_downgrade=True`，
     即使 eligibility 為 `True` 且三關皆 `ok`（機械上不得被讀成「已證明無選擇偏誤」）。
  3. 新增驗收：`test_pbo_universe_guard.py` ⑤d（三項全符 ⇒ `status=="ok"` 且
     `universe_scope=="ledger_recorded_only"`）；`test_report_section.py` ⑤（三關皆 ok ＋
     `universe_scope=="ledger_recorded_only"` ⇒ `display_downgrade is True`）。
  4. §N／registry 新增殘留 **G1-R9**：「ledger 完整性（無事後 top-K 寫入）之生產者側證明」，
     `為何現在不做: blocked-by:G1-R1（無生產者即無寫入面可證；純統計層無外部候選宇宙 SoT）`，
     觸發＝G1-R1 落地，驗收錨點＝`universe_scope` 可升為 `producer_conformance_verified`。
- **禁宣稱**：本票**未**關閉 top-K 污染面全部；僅關閉「呼叫方對已完整之 ledger 挑子集」一半。

## A1-5 — Task 3.1 簽名與 overflow 處置（母 SPEC:378-380、:390-398）

- **來源**：`GROK-R8-P1-01`、`CODEX-R8-P1-03`。
- **修訂**：
  1. `assess_eligibility(*, t_years: float, ledger_result: LedgerReadResult, target_sharpe: float)`
     ——取代母 SPEC 之 `n_trials: int`（理由：N 只能來自 Task 2.2，且 status 須可傳遞使 `eligible=None`）。
     驗收⑤ 之 `n_trials=100` 改為 `ledger_result=<n_for_dsr=100 fixture>`。
  2. `max_trials_budget`：`x = t_years*target_sharpe**2/2`；**`x > 700` ⇒ `raise ValueError`**
     （fail-closed；`math.exp(710)` 本身即 OverflowError，且該輸入無物理意義）。
     **禁**任何 cap 常數（codex 反例：`t_years=1500, SR=1.0` ⇒ `x=750`，`floor(exp(750))` 遠大於 `10**18`，
     以 cap 取代會使 §G 之 `ub(budget) <= T < ub(budget+1)` 不變式失效）。
  3. `EligibilityResult` 欄位**不得**新增契約 `eligibility_keys` 九鍵以外之欄（`additional_properties:false`）
     ——特別是 TODO DRAFT 曾自創之 `budget_capped` 一律刪除。
  4. **新增驗收⑨（G1-R7 部分收回；見 A1-9）**：MinBTL 上界保守性統計 oracle。

## A1-6 — Task 1.4 簽名補 `t_semantics`（母 SPEC:165-167）

- **來源**：`CODEX-R8-P1-06`。
- **修訂**：`extract_period_returns(backtest_result, *, timeframe: str, t_semantics: str) -> PeriodReturns`
  （`t_semantics` 為**必填**，由呼叫方選；值集合住 Task 2.1）。選定規則（唯一定義處）：
  DSR 只接 `trade_level` 與 `nonzero_return_bars`；`bar_count` 一律 `status="not_applicable"`、
  `reason="t_semantics_inflates_significance"`（值仍回傳供診斷）。**無**預設值、**不**自動挑選。

## A1-7 — Task 2.2 計數語意與 `n_rows_rejected`（母 SPEC:295-311、驗收②⑧）

- **來源**：`CODEX-R8-P1-07`（真 bug：現行文字使 Task 2.3 之不變式 `n_evaluated == n_valid_metrics +
  n_failed_or_pruned` 對「schema-valid 但 `metric_valid=False`」之列失敗——該列落不進任何計數）。
- **修訂**：
  1. `n_evaluated` ＝ schema-valid 列數；
     `n_valid_metrics` ＝ schema-valid ∧ `metric_valid=True`；
     `n_failed_or_pruned` ＝ schema-valid ∧ `metric_valid=False`（不變式由構造成立）。
  2. schema-invalid 列（缺鍵／型別錯／額外鍵／JSON 語法錯／`metric_unit` 非法）計入**新增**欄位
     **`n_rows_rejected`**，並記 `reason="ledger_row_invalid"`；**不得靜默丟棄**。
     ⇒ Task 2.1 之 `n_fields` **五值 → 六值**（新增 `n_rows_rejected`）。
  3. 驗收②「3 合法列＋1 非法列 ⇒ `n_evaluated==3` 且 `n_failed_or_pruned==1`」改為
     「⇒ `n_evaluated==3` 且 **`n_rows_rejected==1`** 且 `n_failed_or_pruned==0`」；
     **新增驗收②b**「4 合法列其中 1 列 `metric_valid=False` ⇒ `n_evaluated==4`、`n_valid_metrics==3`、
     `n_failed_or_pruned==1`、`n_rows_rejected==0`，且不變式成立」。

## A1-8 — Task 3.4 reporter 介面、回應投影與例外分類（母 SPEC:476-492）

- **來源**：`CODEX-R8-P1-04`、`CODEX-R8-P1-05`、`GROK-R8-P1-02`、`COMPOSER-R8-P1-01`、
  `COMPOSER-R8-P1-02`、`GROK-R8-P2-02`。
- **修訂**：
  1. `StrategyValidationReporter.for_study_trial(study_name: str, trial_number: int, *,
     dataset_key: str | None = None, t_years: float | None = None, target_sharpe: float | None = None) -> dict`。
  2. 三個 optional 任一為 `None` ⇒ **不呼叫** `read_trial_ledger`／`assess_eligibility`，
     直接組 `EligibilityResult(eligible=None, status="unavailable", reason="n_unknown", trials_used=None, …)`
     → `build_validation_section(dsr=None, pbo=None, …)`。`api/routes/ml_pipeline.py` 今日三者皆傳 `None`
     （request 只有 `study_name`／`trial_number`）。**禁** `dataset_key=f"trial:{n}"` 之自創公式
     （per-trial 鍵會使 `n_candidates_considered ≡ 1`，與 DSR 之 dataset 級 N 語意衝突）；
     dataset 級鍵由 G1-R1 生產者契約提供。
  3. API 回應 `strategy_validation` **只投影三鍵**（母 SPEC 逐字）：`eligibility`／`display_downgrade`／
     `warning_text_key`；其餘節不進 API（前端契約待 G1-R3）。
  4. 例外分類（取代母 SPEC 之「任何例外 ⇒ `computation_failed`」）：
     - 只捕 `(OSError, json.JSONDecodeError, ContractViolation, ValueError)` ⇒ 回契約合法之降級結構、
       `reason="reporter_failed"`（Task 2.1 之 `reasons` **11 → 12** 值，`reason_conditions` 同步）；
     - **其他例外（含 `TypeError`／`AttributeError`／`KeyError`）一律往上拋**，由 route 既有 500 路徑處理；
     - 捕獲路徑必 `logger.error(..., exc_info=True)`；例外文字**只進 log 不進回應**
       （動態字串進 `reason` 會違反「`reasons` 唯一來源」並使 Task 2.4 之 W3 掃描不可判定）。
  5. 新增驗收⑥「reporter 內部 `TypeError` ⇒ HTTP 5xx（**不**吞）」、⑦「`OSError` ⇒ 2xx 且
     `strategy_validation` 之 reason ＝`reporter_failed`」。

## A1-9 — Task 3.1 驗收⑨：MinBTL 上界保守性統計 oracle（G1-R7 部分收回）

- **來源**：`GROK-R8-P1-04`、`CODEX-R8-P1-11`、`CLAUDE-R8-P1-10`。
- **修訂**：新增驗收⑨（可證偽，秒級）：
  `default_rng(20260817 + k)`，k=0..19；每 seed 100 條 iid 常態噪音策略（σ=0.01）、
  `t_years = min_btl_years_upper_bound(n_trials=100, target_sharpe=1.0) = 9.210340371976184`、
  日頻（`periods_per_year=365`、`n_obs=3362`）⇒ `mean(max annualized SR) <= 1.0`
  **且**與解析值 `0.833943`（＝`E[maxSR]/sqrt(n_obs-1)*sqrt(365)`）之 `rtol < 0.05`。
  主委實跑：`mean=0.843077`（receipt
  `handoffs/run_receipts/20260817T150000Z-gap1-minbtl-conservatism-probe.{py,log}`）。
- 🔴 **斷言只可下在 20 seed 之平均**：per-seed 上界**不**成立（實跑 `max=1.216377`）。
  把它寫成逐 seed 斷言即為不可達 oracle（本輪 J1 之同類錯誤）。
- **殘留剩餘部分**：誤差帶之精確量化仍為 `needs-research`（見 A1-10 第 2 項）。

## A1-10 — §N 殘留分類修正（母 SPEC:660-694；registry「GAP-1 待補完登記」）

- **來源**：`GROK-R8-P1-03`、`GROK-R8-P1-04`、`CODEX-R8-P1-10`、`CODEX-R8-P1-11`、`CODEX-R8-P1-12`。
  四方一致：G1-R1／R2／R4／R5／R6 五條理由**成立**，其餘三條需改。
1. **G1-R3 前端降級面板**：`blocked-by:G1-R1／R2（後端無資料可顯示）` **不成立**——Task 3.4 已把
   `display_downgrade`／`warning_text_key` 送進 API 回應，空/降級面板現在就能做。改為
   `為何現在不做: user-ruling:2026-08-17 交付範圍 A 不含 frontend（成熟度地圖：frontend 屬不完整層）`；
   觸發改「使用者要求 UI，或 G1-R1／R2 任一落地」。
2. **G1-R7 MinBTL 上界近似誤差**：`needs-research` 之**誤差帶量化**維持（無公認可驗方法 ⇒ 無法定義通過條件），
   但**保守性驗證部分收回**為 Task 3.1 驗收⑨（見 A1-9）；觸發由不可判定之「排程即可做」改為
   「具名票 `GAP-1-R7-MC`（owner＝Claude 主委）建立且排入 `docs/ROADMAP.md` 時」。
3. **G1-R8 `prediction_analyzer.py:155` `np.cumsum`**：`blocked-by:不在策略路徑` 為 **scope 裁決非依賴**
   ⇒ 三值形式不成立 ⇒ **收回為獨立小票**（不再是殘留）：`docs/ROADMAP.md` 新增「PA-CUMSUM 單利權益改正」，
   排程＝GAP-1 B4 完工後，執行＝Claude 小任務流程；自 registry 殘留表**移除**該列。
4. **新增 G1-R9**（見 A1-4 第 4 項）。⇒ registry 殘留由 8 條變 **8 條**（移除 R8、新增 R9）。

## A1-11 — §P 批次拓撲：Task 2.4 移至 B4 末（母 SPEC:350-371、:499）

- **來源**：`GROK-R8-P0-01`（BLOCKING）、`CODEX-R8-P1-09`、`CODEX-R8-P1-08`、`COMPOSER-R8-P2-01`、
  `GROK-R8-P2-01`。
- **成立之攻擊**：Task 2.4 之 W1／W4 需 Task 3.3 之 `report.py`（B3），W2 需 3.2／4.2／4.3 之 6 個 reason 字面
  （B3／B4）⇒ 若 2.4 落在 B2 且 B2／B3 出口 gate 要求 `strategy_wiring_check` rc=0，該 gate **不可能**通過。
- **修訂**：
  1. Task 2.4 **移至 B4 末**（批內順序 4.1→4.2→4.3→2.4；Task 編號不改以維持追溯表）。
  2. §P 之 B4 依賴改為「B1 Task 1.1／1.2／1.4、B2 Task 2.1／**2.2**、B3 Task 3.3」
     （母 SPEC:499 只列 B2 Task 2.1，與 Task 4.3 需 `LedgerReadResult.candidate_ids` 矛盾）。
  3. B2→B3／B3 收尾 gate **移除** `strategy_wiring_check` rc=0；只在 **B4 收尾** gate 要求 rc=0。
  4. W1／W4 由「字面 `re.search`」改為 **AST**：解析 `report.py`、取 `build_validation_section` 之
     `Return` 及其 body 內組裝該 dict 之 `ast.Constant` 鍵集合，與契約 `report_sections`／`eligibility_keys`
     做集合比對（註解／docstring／dead branch 之字面不再造成假綠）。
  5. W3 由「兩種字面」改為 AST 三形：`reason=<Constant>`（keyword／assign）、`{"reason": <Constant>}`、
     `<x> == <Constant>`；出現非 `Constant` 之動態值 ⇒ 列為 `[unresolved]` 且 **rc=1**（fail-closed）。
  6. **誠實邊界具名**（不得宣稱超出）：不追跨檔常數別名與 f-string 組合；此類一律落入 `[unresolved]` ⇒ rc=1。
  7. 治理連動路徑具名：`plain_docs_sync_check.sh` 於 `gov_check`／pre-push 硬擋，`--staged` 只提醒 ⇒
     本 Task commit 後須跑 `bash scripts/gov_check.sh --fast`（**非** `--staged`）。

## A1-12 — Task 3.2 分母單一定義處與 explicit 變異數之 reason（母 SPEC:412-421、:445-448）

- **來源**：`CLAUDE-R8-P1-06`、`CLAUDE-R8-P1-07`（主委自產）。
- **修訂**：
  1. DSR 檢定統計量**一律**寫成 `stat = (SR_obs - SR0) / sqrt(sr.sr_estimator_variance)`
     （`sr` ＝ Task 1.2 之 `SharpeResult`）；**禁**在 `deflated_sharpe.py` 內重算
     `sqrt(1 - γ3·SR + (γ4-1)/4·SR²)`——兩處定義會使 §V-10（Mertens 係數改錯）無法如母 SPEC 所稱
     使 Task 3.2 斷言① 轉紅。代數等價：`(SR-SR0)*sqrt(T-1)/den ≡ (SR-SR0)/sqrt(Var)`。
  2. `variance_source="explicit"` 而 `cross_trial_sr_variance` 為 `None`／未傳 ⇒ `reason="cross_trial_variance_unavailable"`；
     有值但非有限或 `<= 0` ⇒ `reason="degenerate_returns"`（兩情形各一測試；母 SPEC 兩句易被讀成單一分支）。

## A1-13 — Task 2.1 `report_sections` 逐節必填鍵（母 SPEC:262-270）

- **來源**：`CLAUDE-R8-P1-08`（空殼：母 SPEC 只給欄位標籤未給內容）。
- **修訂**：契約 `report_sections` 五節之 `required_keys` **逐字**如下（各節另含 `additional_properties: false`
  與逐鍵 `type`）：
  - `eligibility` ＝ `eligibility_keys` 九鍵（`eligible`／`required_years_upper_bound`／`available_years`／
    `trials_budget`／`trials_used`／`target_sharpe`／`n_source`／`display_downgrade`／`warning_text_key`）＋`status`／`reason`
  - `min_btl` ＝ `status`／`reason`／`required_years_upper_bound`／`available_years`／`trials_budget`／`trials_used`／`target_sharpe`
  - `dsr` ＝ `status`／`reason`／`value`／`sr0`／`sr_obs_per_period`／`n_trials_used`／`variance_source`／`n_independence`
  - `pbo` ＝ `status`／`reason`／`value`／`n_paths_used`／`n_paths_skipped`／`n_candidates_invalid`／`universe_scope`
  - `provenance` ＝ `status`／`reason`／`n_semantics`／`t_semantics`／`annualization_source`／`n_independence`
- 另：Task 3.3 之「假設 N ⇒ `n_source="assumed_not_ledgered"`」屬 **`eligibility` 節**之鍵（母 SPEC／TODO
  曾誤寫為 `provenance.n_source`）。

## A1-14 — Task 1.1 新增 `available_years` 與 §V 反向測試去 vacuous（母 SPEC §V:645-647）

- **來源**：`CLAUDE-R8-P1-09`。
- **成立之攻擊**：`assess_eligibility` 直接吃 `t_years`，若三個 timeframe fixture 各自傳同一 `t_years`，
  「1h/4h/12h 之 `available_years` 差 `atol=1e-6`」必然成立 ⇒ 抓不到「把 bar 數當年數」之取巧。
- **修訂**：
  1. Task 1.1 新增 `available_years(*, n_bars: int, timeframe: str) -> float`
     ＝ `n_bars / resolve_periods_per_year(timeframe)`（**唯一**推導處；Task 1.4 之 `trade_level` 亦呼叫之）。
  2. §V 反向測試改為：以 §A FACT-RECEIPT 之真實 kline 長度（1h=20352／4h=5088／12h=1696）三 timeframe
     各自呼叫 `available_years`，三值互相 `atol=1e-6`（皆 ＝ `2.3232876712328765`）。
  3. **新增 §V-15 mutation**：`available_years` 改回 `n_bars`（把 bar 數當年數）⇒ 反向測試轉紅。
- **§V 條數**：13 → **15**（另 §V-14 見 A1-15）。

## A1-15 — Task 4.2 champion 索引與 path 級退化（母 SPEC:541-560）

- **來源**：`CODEX-R8-P0-02`（BLOCKING；codex 實跑 `rankdata([0.1,0.2])[2]` → IndexError rc=1）。
- **成立之攻擊**：母 SPEC 先以**原始欄索引**固定 IS champion，再對 path 有效候選之**壓縮陣列**取名次；
  champion 本身在 OOS 退化被剔除時，索引越界（或誤取他人名次）。
- **修訂**：
  1. 建 `pos = {original_col_index: compressed_position}` 映射；名次一律 `rankdata(oos_metrics,
     method="average")[pos[champion]]`，**禁**用原始索引直接索引壓縮陣列。
  2. **champion 於 IS 或 OOS 非有限 ⇒ 跳過該 path**（`n_paths_skipped += 1`、`n_path_exclusions += 1`）；
     **不**重選 champion（重選會改「IS 選、OOS 評」語意）。
  3. 新增驗收 ④d：3 候選、IS champion＝索引 2、OOS 該候選為常數 ⇒ 該 path 被 skip、**不** raise、
     PBO 分母 ＝ `n_paths_used`。
  4. **新增 §V-14 mutation**：改回以原始索引取名次 ⇒ ④d 轉紅（IndexError 或錯值）。

---

# R9 受限複驗之追加修訂（A1-16..A1-18）

> 來源：`handoffs/reconcile/20260817-gap1-x-review-r9/synth.md`（群集 J7／J8／J9；三家 6 findings，R8 22 → R9 5 實質）。
> 三條皆為文件級修補，不動已定案之統計契約與數值 golden。Verdict 分歧（composer「可 Frozen」vs
> codex／grok「需修補後 Frozen」）⇒ **取較嚴版**。

## A1-16 — reporter 例外集合收窄＋`InvalidValidationArgument`（取代 A1-8 第 4 點之捕獲集合）

- **來源**：`CODEX-R9-P1-02`（MAJOR）、`GROK-R9-P1-01`（MAJOR）、主委自產 `CLAUDE-R9-P1-02`（四方一致）。
- **成立之攻擊**：A1-8 之捕獲集合含裸 `ValueError`，而 A1-5 把「`t_years<=0`／`target_sharpe<=0`／`x>700`」
  定為 `ValueError` ⇒ **呼叫方傳錯參數這種程式錯誤**會被映射成 `reason="reporter_failed"` 的 2xx 降級
  （兩家各自實跑：`negative_t_years='reporter_failed'`），與 A1-8 自身「程式錯誤保留可觀測失敗」矛盾。
- **修訂**：
  1. `min_btl.py` 新增 `class InvalidValidationArgument(ValueError)`；Task 3.1 之三處參數驗證
     與 `max_trials_budget` 之 `x>700` **一律** raise 之（仍為 `ValueError` 子類 ⇒ 呼叫方語意不變，但可精準排除）。
  2. reporter 捕獲集合**收窄為** `(OSError, json.JSONDecodeError, ContractViolation)`；
     `ValueError`／`InvalidValidationArgument` **不捕獲** ⇒ 上拋，由 route 既有 500 路徑處理。
  3. reporter **入口語意二分（🔴 不得混同）**：
     - 三個 optional 任一為 `None` ＝「**未提供**」⇒ 走誠實 `unavailable`／`n_unknown` 路徑
       （**不**呼叫 `assess_eligibility`）⇒ 正常路徑不製造例外；
     - 「**提供了但非法**」（`t_years <= 0`／`target_sharpe <= 0`）＝**呼叫方 bug**，
       **不得**正規化為 unavailable ⇒ 交由 `assess_eligibility` raise `InvalidValidationArgument` 並上拋 ⇒ 5xx。
     兩者混同會使 A1-16 之意圖落空（把 bug 靜默吸收，只是換一種吞法）。
  4. Task 3.4 驗收⑤ 擴為 `TypeError` **與** `InvalidValidationArgument` 各一（皆須 5xx）；
     新增驗收⑧「route 傳入 `t_years=-1.0`（模擬未來 G1-R1 接線錯誤）⇒ 5xx，**不得**回 `reporter_failed`」。

## A1-17 — AST wiring 收窄為「無條件路徑」＋死分支 mutation（取代 A1-11 第 4／5 點之收集範圍）

- **來源**：`CODEX-R9-P1-01`（MAJOR，實跑）、`GROK-R9-P2-01`（MINOR）。
- **成立之攻擊**：A1-11 未定義可達性 ⇒ `if False:` 內寫滿五節名／九個 `eligibility_keys` 可使 W1／W4
  集合齊備而 runtime 缺鍵（codex 實跑：`return_sections` 五節齊、`w4_seen` 九鍵齊、`runtime_eligibility={}`）。
- 🔴 **主委自產探針之誠實邊界（具名）**：`handoffs/run_receipts/20260817T160000Z-gap1-ast-wiring-probe.{py,log}`
  只覆蓋 helper／迴圈／`{**a,**b}`／docstring 四形（結論：無假綠、兩形誤擋），**未測死分支** ⇒ 本條為委員補上之真缺口。
- **修訂**：
  1. W1／W4 之收集範圍**收窄為無條件路徑**：只接受 ① 函式**頂層**（未嵌在 `If`／`For`／`While`／`Try`／`With`
     之 body 內）之 `Return` 之 `ast.Dict` 字面鍵 ② 函式**頂層**之 `out["<literal>"] = …` ③ 頂層 `{**a, **b}`
     且來源 dict 亦於頂層以字面定義。**凡條件／迴圈／try 內之組裝一律不計入** ⇒ 節名不足即 rc=1。
  2. Task 2.4 新增 **mutation ⑥**：`if False:` 內寫滿五節名（或九鍵）而 return dict 缺該節 ⇒ rc=1。
     ⇒ Task 2.4 之 mutation 由 5 條增為 **6 條**。
  3. **配對條款**（主委自產 `CLAUDE-R9-P1-01`；閘門既選「寧誤擋」，被擋方必須有明文可行寫法）：
     Task 3.3「不可做」新增——`build_validation_section` **禁**以 helper 函式、迴圈變數鍵、
     `setattr`／`dict(**kwargs)` 組裝五節；必須在自身函式**頂層以字面鍵**組裝（主委實跑證此三形 `assembled=∅`）。
  4. Task 2.4「誠實邊界」補：本閘只做**語法層無條件路徑**判定，不做 CFG／可達性推導；
     runtime 第二道防線＝Task 3.3 之 `validate_against_contract`（此即 grok 判 MINOR 之理由，予以保留並具名）。

## A1-18 — §R 回退契約覆寫（取代母 SPEC:653-654）

- **來源**：`CODEX-R9-P1-03`（MAJOR）、`GROK-R9-P2-02`（MINOR）、`COMPOSER-R9-P3-00`（記於段 C 結論）、
  主委自產 `CLAUDE-R9-P2-01`。
- **成立之攻擊**：母 SPEC 逐字「B4 …不依賴 B3 ⇒ B3 與 B4 可獨立 revert」，而 A1-11 使 B4 依賴 B3 Task 3.3
  ⇒ 保留 B4 而 revert B3 時 wiring 之 AST 標的消失、B4 gate 不成立。
- **修訂（覆寫 §R 之依賴與回退敘述）**：
  1. 依賴：**B4 ⊃ B3**，且僅因 Task 2.4 之 wiring 閘讀 `report.py`；**統計核心 4.1–4.3 不依賴 B3**。
  2. revert 順序：**先 B4 再 B3**。若須單獨 revert B3，則同時 revert Task 2.4 之兩個 `scripts/` 檔，
     或接受 `strategy_wiring_check` rc=2 並於 receipt 具名。
  3. **不採之替代案**（codex 提及）：把 wiring 拆為 B4 之後的獨立 post-B4 phase——理由＝多一批次與一輪 review，
     而雙向獨立 revert 在本票無實需（新模組無既有 caller；§R 之價值在「壞了能退」而非「任意順序退」）。

---

# B1 實作期之追加修訂（A1-19；🔴 由 B1 code review 複核）

## A1-19 — Task 1.1 之 canonical 實作落在 `momentum/core/frequency.py`（re-export 保持 TODO 路徑）

- **來源**：B1 實作時之機器擋點（非委員 finding）。實跑證據：
  `python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` → rc=1，
  `NEW: momentum/Strategy/vectorized_backtest.py|R2|from|momentum.Analysis.strategy_validation.frequency.*`（2 筆）。
- **衝突**：TODO Task 1.1 把 `resolve_periods_per_year`／`available_years` 放
  `momentum/Analysis/strategy_validation/frequency.py`，而 Task 1.3 要求
  `momentum/Strategy/vectorized_backtest.py` 呼叫之 ⇒ `momentum/Strategy/` → `momentum/Analysis/`
  命中 **canonical Rule 2（跨域須經 Protocol）**，`check_decoupling_imports.py` fail-closed。
  TODO §0 只列了 R1／R3／R6／R7，**未預見** R2 之 intra-`momentum` 跨域判定。
- **修訂**：canonical 實作移至 **`momentum/core/frequency.py`**；
  `momentum/Analysis/strategy_validation/frequency.py` 改為 **re-export**（`__all__` 三個名稱）。
  ⇒ TODO 所寫之 import 路徑與 API **逐字仍成立**（`from momentum.Analysis.strategy_validation.frequency
  import resolve_periods_per_year` 可用），三關與測試無須改寫。
- **為何是 core 而非開 manifest allow**：`momentum.core.*` 與 `momentum.factories` 是 scanner 之
  結構性豁免（`_is_exempt_target`）；且本函式是**純常數推導**（其唯一輸入 `TIMEFRAME_SECONDS`
  本就住 `momentum/core/constants.py`），無任何領域邏輯 ⇒ 放 core 是架構上正確，而非為過閘而搬。
  另一方案（改 manifest allowlist ＋ 重蓋 stamp）會把「Strategy 可直接 import Analysis」永久放寬，代價大得多。
- **未變**：函式簽名、行為、錯誤型別、`available_years` 之唯一推導處地位、§V-8／15 mutation 皆不受影響
  （實跑：`handoffs/run_receipts/20260817T170000Z-gap1-b1-mutation.log` 五條全轉紅 rc=1）。
- **Task 1.3 之附帶決定（同屬本條，review 請一併看）**：`StrategyBacktestObjective.evaluate` **只在
  `self.timeframe is not None` 時**才把 `timeframe`／`risk_free_rate` 傳給 engine。
  理由：`IBacktestEngine` 之其他實作（含既有測試替身）簽名未含這兩參 ⇒ 無條件傳會使**未使用 GAP-1 的既有路徑**
  全部 `TypeError`（實跑：18 failed）。給了 `timeframe` 而引擎不支援 ⇒ 仍 `TypeError`（fail-loud），
  **不**靜默退回隱性 730。

## A1-20 — 🔴 A1-19 之一項宣稱被推翻＋B1 code review 四項修補（K1–K4）

- **來源**：B1 實作 code review（`20260817-GAP1-B1-REVIEW-R10`，三家 10 findings，
  收斂檔 `handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md` 群集 K1–K4）。三家 Verdict 一致。
- 🔴 **被推翻之宣稱（A1-19 末段，主委自寫）**：「給了 timeframe 而引擎不支援 ⇒ 仍 `TypeError`（fail-loud），
  **不**靜默退回隱性 730」——**只對「不接受 kwargs」那一類 engine 成立**。
  `CODEX-R10-P1-03`／`GROK-R10-P1-01` 各以可執行反例證明：engine 若 `**kwargs` 吞下 `timeframe`
  但不回填 `annualization`，`annualization.get("periods_per_year", 730)` 會**靜默**以 730 年化
  （codex：`returned == expected_730`、`silent_730=True`）。此即 C2 要關的病。
  **A1-19 該句作廢，以本條為準。**

### K1（修）objective 端 annualization 硬性檢查
`StrategyBacktestObjective._resolve_metrics_periods()`：`self.timeframe is not None` ⇒
`annualization` 必須是 dict、`source == "resolved"`、`periods_per_year` 為正整數，
任一不符 `raise ValueError`（**禁** `.get(..., 730)` 兜底）；`timeframe is None` 之 legacy 路徑
維持 730 但改具名常數 `_LEGACY_PERIODS_PER_YEAR` 並 `logger.warning`。
回歸鎖：`test_objective_fails_loud_when_engine_swallows_timeframe`（參數化兩種反例 engine）
＋`test_objective_legacy_path_keeps_730_without_timeframe`。

### K2（修）mutation 探針之「全綠自檢」曾是空殼
`scripts/gap1_b1_mutation_probe.sh` 之 baseline 與 post-restore 原本只 `echo rc`、無非零分支
（`CODEX-R10-P1-02` MAJOR 信心 10/10）⇒ baseline 本來就紅、或還原失敗留下 mutant，
腳本仍會印「✅ 全部轉紅」。現改為兩處皆 `rc≠0 ⇒ exit 1`（rc 直接取、禁經 pipe），
並保留 `grep MUTANT` 殘留檢查。**與「工具必須自帶強制機制、禁空殼檢查」對齊。**

### K3（修）§V-9 補進探針
探針原缺 TODO Gate 明列之 §V-9（`COMPOSER-R10-P1-01`／`GROK-R10-P2-02`）。
新增 **§V-9a**（`bar_count` 分支改回 `status="ok"`）與 **§V-9b**（拿掉 `source != "resolved"` 守衛）。
⇒ 探針 5 條 → **7 條**（§V-5／8／9a／9b／10／13／15），實跑全部 rc=1 且 FAILED≥1
（receipt：`handoffs/run_receipts/20260818T000000Z-gap1-b1-mutation-v2.log`）。

### K4（修 2／留 1）真實資料 skip、import 路徑漂移、Protocol 漂移
1. **缺 kline 由 `skip` 改 `fail`**（`CODEX-R10-P1-01` MAJOR ／ `GROK-R10-P2-03` MINOR，取較嚴版）：
   §G 明定 receipt 必用真實 kline，「真實資料測試的缺席不能被當成通過」。
   同時把不依賴 kline 之 fail-closed 案例改名為 `test_*_without_kline`（純 stub，非冒充資料），
   使無資料環境仍有實質覆蓋。
2. **re-export 防漂移**（`GROK-R10-P2-01`）：`test_frequency.py` 新增 identity 斷言
   （三個名稱皆 `is` core 之物件）；規定**新碼一律 import `momentum.core.frequency`**，
   `momentum.Analysis.strategy_validation.frequency` 僅為相容 re-export。
3. **`IBacktestEngine` Protocol 未宣告 `timeframe`／`risk_free_rate`**（`CODEX-R10-P2-04` MINOR）
   ⇒ **具名殘留 G1-R10**：`為何現在不做: blocked-by:SPEC §C 白名單（既有測試檔只允許加斷言；
   改 Protocol 須連動所有實作與 test doubles，超出本票允許改動面）`；觸發＝白名單擴充提案或使用者裁決。
   🔴 誠實邊界：**現行相容靠條件分支而非 Protocol 宣告**；K1 已把數值危險面收掉，契約漂移仍在。
4. **A1 範圍字面統一**（`CODEX-R10-P3-05`）：TODO 標頭／§0／追溯表與 package docstring 統一標 `A1-1..A1-20`。

---

## A1-21 — 🔴 B2 code review 十群集修補（L1–L10）：⑥b 字面作廢＋唯一寫入口硬化

- **來源**：B2 實作 code review（`20260818-GAP1-B2-REVIEW-R14`，三家 21 findings：codex 6／composer 5／grok 10；
  收斂檔 `handoffs/reconcile/20260818-gap1-b2-review-r14/synth.md` 群集 L1–L10）。三家 Verdict 一致「需修補後進 B3」；
  嚴重度分歧一律取較嚴版，**全部本輪修，不登記殘留**。
- 🔴 **被推翻之主委宣稱**（brief 段 D，主委自寫）：「`metric_unit="annualized"` 之列我計入 `n_rows_rejected`」——
  三家實跑皆得 `n_rows_rejected=0`：**實作本來就是 schema-valid、只不入 `valid_sharpe_values`**；是我描述自己的碼描述錯了。
  同時三家一致判定 Frozen TODO:210 ⑥b「annualized ⇒ 計入 `n_rows_rejected`」與母 SPEC:252／:319「記 `reason=ledger_row_invalid`」
  是**把合法枚舉誤判為 schema-invalid**（A1-7 定義 schema-invalid 只含 `metric_unit` **非法**）。
  **TODO ⑥b／母 SPEC:252、:319 之該句作廢，以本條為準**：annualized ⇒ schema-valid、計入 `n_evaluated`（依 `metric_valid` 二分）、
  `n_rows_rejected` **不**增、**不入** `valid_sharpe_values`、reason 為空。
  回歸鎖：`test_valid_sharpe_values_only_per_period` 加 `n_rows_rejected==0`／`n_evaluated==5`／`reason==""` 顯式斷言。

### L1（修）非有限 `metric_value` 拒收（`CODEX-R14-P1-02`／`GROK-R14-P1-02`）
`_row_problems`：`float` 欄位加 `math.isfinite`（NaN／±inf ⇒ schema-invalid）；寫入口 `json.dumps(..., allow_nan=False)`；
讀側計 `n_rows_rejected`、不入 `valid_sharpe_values`。契約 `ledger_row_invalid.condition` 補「數值非有限」。
回歸鎖：`test_non_finite_metric_value_is_schema_invalid`（讀）／`test_non_finite_metric_value_is_rejected_at_write`（寫）；探針 **§V-7b**。

### L2（修）全列非法 ⇒ `reason=ledger_row_invalid`（`CODEX-R14-P1-02`／`GROK-R14-P2-01`；codex P1 vs grok P2 取較嚴）
檔存在但 `n_evaluated==0 ∧ n_rows_rejected>0` ⇒ `status=unavailable`、`reason=ledger_row_invalid`（是「帳本損壞」非「無帳本」）；
`n_unknown` 只留給檔缺／真·零列。契約 `ledger_row_invalid.condition` 同步。
回歸鎖：`test_invalid_rows_rejected_with_named_reason` 加 `got.reason`／`status`／`n_for_dsr==0` 斷言。

### L3（延伸）見上「被推翻之主委宣稱」（`CODEX-R14-P1-03`／`GROK-R14-P1-01`）

### L4（修）`snapshot_hash` 改 JSON 定界（`CODEX-R14-P1-04`／`COMPOSER-R14-P1-01`／`GROK-R14-P1-04`）
`_snapshot_hash(artifact_hashes, dataset_key, research_session_id)` 純函式：
`sha256(json.dumps([sorted(hashes), dataset_key, session], separators=(",",":"), ensure_ascii=False))`；
舊法 `",".join(...)+"|"+...+"|"+...` 對三家反例皆碰撞。今日無既有帳本 ⇒ 無舊 hash 相容問題（面向未來不溯及既往）。
回歸鎖：`test_snapshot_hash_has_no_delimiter_collision`（四組反例）＋讀路徑層級一則；探針 **§V-7c**。

### L5（修）寫入口原子化＋context 綁定（`CODEX-R14-P1-01`／`COMPOSER-R14-P2-02`／`GROK-R14-P1-05`／`GROK-R14-P2-02`；composer P2 取較嚴）
1. 掃描重複 `evaluation_id`＋append 包在 **`fcntl.flock(LOCK_EX)`**（sidecar `<ledger>.lock`；跨執行緒／跨行程互斥）；
   讀側 `LOCK_SH`（不讀到半列）。「單次 write 不交錯（O_APPEND）」註解**作廢**（grok 量到 PIPE_BUF=512 < 典型列 ≈610B）。
2. `record["research_session_id"]／["dataset_key"]` 與參數不等 ⇒ `ContractViolation`（codex `CROSS_CONTEXT`）；
   讀側對 context 不符之列計 `n_rows_rejected`。
3. 測試注入點 `_after_duplicate_scan_hook`（預設 `None`）：把 TOCTOU 視窗放大成**可證偽**測試
   （`test_duplicate_evaluation_id_race_writes_exactly_one_row`：兩執行緒同 id ⇒ 恰 1 成功 1 列；拿掉 flock ⇒ 2 列 ⇒ 紅）；
   `test_multi_process_long_lines_do_not_interleave`（4 行程 × 8KB 列 >PIPE_BUF）；`test_record_context_must_match_target_ledger`；
   探針 **§V-7e**。

### L6（修）`ledger_path` 真實推導回歸鎖（`CODEX-R14-P2-05`／`COMPOSER-R14-P1-02`／`GROK-R14-P1-03`）
抽 `_ledger_filename()` 純函式＋常數 `_LEDGER_DIRNAME`；新檔 `test_ledger_path.py` **不** patch `ledger_path`，改 patch
`MomentumConfig.from_project_root` 之 project_root，斷言 `<results>/strategy_validation/<s>__<d>.jsonl` 全路徑；探針 **§V-7d**。
主委加碼（同群集）：識別字含 `os.sep`／`..`／NUL／空／非 str／**`__`**（檔名內兩識別字之分隔符，放行會使 `("a__b","c")` 與
`("a","b__c")` 落同一檔）⇒ `ValueError`（fail-loud）。

### L7（修）型別精確比對（`COMPOSER-R14-P2-01`／`GROK-R14-P2-03`；取較嚴＝只收純 Python 純量）
`_row_problems` 以 `type(value) in expected` 取代 `isinstance`：`Enum(str)`／`numpy.float64`／`numpy.int64`／bool 冒充 int·float 一律拒；
讀側 JSON 解出的本就是純 Python 型別不受影響；寫側生產者須 `float(x)`／`int(x)`（docstring 明寫）。
回歸鎖：`test_exact_type_check_rejects_lookalikes`（六組）。

### L8（修）契約 loader fail-closed＋快取不可變（`CODEX-R14-P2-06`／`GROK-R14-P3-02`）
1. `_validate_contract_shape`：頂層鍵集合恰為 `_EXPECTED_TOP_LEVEL_KEYS`（16 鍵名；不複列任何枚舉值）、每個 `*_values` 非空 str list、
   `set(reason_conditions)==set(reasons)`——多／少／漂即 raise。
2. `validate_against_contract` 枚舉 membership 改**機械對映**：obj 之鍵 `k` 若契約存在 `f"{k}_values"` ⇒ 非 None 值須屬該枚舉
   （涵蓋 `universe_scope`／`variance_source`／`n_semantics`／`t_semantics`／`annualization_source`／`universe_source`／`selection_metric`；
   ledger `_row_problems` 同一機制涵蓋 `metric_unit`）。
3. 快取以 `(mtime_ns, size)` 鍵控＋回傳 deepcopy；`_row_problems` 改收 `contract` 參數（讀迴圈只 load 一次）。
   🔴 誠實邊界：仍是模組級 memo（不宣稱「無快取」）；不可變、可失效 ⇒ 滿足 Rule 8 之精神。
回歸鎖：`test_loader_rejects_unknown_top_level_key`／`_missing_top_level_key`／`_empty_or_non_str_enum`／`_reason_conditions_drift`、
`test_validate_enforces_enum_membership_mechanically`（五節）、`test_returned_contract_is_not_the_cache`、`test_cache_invalidates_when_default_file_changes`。

### L9（微修）錯誤訊息列 missing／extra／bad_type（`GROK-R14-P3-01`；reason 字面不變）
回歸鎖：`test_error_message_names_missing_and_extra_keys`。

### L10（修）探針 8 → **12** 條（`COMPOSER-R14-P3-01`）
新增 §V-7b（isfinite 拿掉）／7c（snapshot 改回 `|`）／7d（目錄字面改名）／7e（flock 拿掉）；baseline／post-restore 集合含 B2 三檔；
`run_expect_red` 允許多目標。B2 Gate 文字＝「§V-7／7b／7c／7d／7e」。receipt：`handoffs/run_receipts/20260818T080000Z-gap1-b2-fix-mutation.log`。

---

## A1-22 — 🔴 B3 code review 六群集修補（M1–M6）：route 例外分類／落盤順序／`n_source_values`（頂層鍵 16→17）

- **來源**：B3 實作 code review（`20260818-GAP1-B3-REVIEW-R16`，三家 12 findings：codex 4／composer 2／grok 6；
  收斂檔 `handoffs/reconcile/20260818-gap1-b3-review-r16/synth.md` 群集 M1–M6）。三家 Verdict 一致「需修補後進 B4」；嚴重度分歧取較嚴，**全部本輪修、不登記殘留**。
- 🔴 **被推翻之主委假設**：①「對稱序列＋樣本 kurt 忠於驗收①『skew=0、kurt=3』字面」——樣本 Pearson kurt≈2.68≠3（codex／grok 各自實跑）；
  ②「IVA→HTTPException(500) 再被外層重包仍符『既有 500 路徑』」——status 成立但 detail 被污染，且**裸 `ValueError`→400** 與 A1-16 衝突（composer／grok 皆 MAJOR）；
  ③（brief 未列、兩家實跑抓到）route 於 reporter 5xx **之前**已把 pipeline JSON 落盤 ⇒ orphan artifact。

### M1（修）route 例外分類（`COMPOSER-R16-P1-01`／`GROK-R16-P1-01`／`COMPOSER-R16-P2-01`／`GROK-R16-P2-01`）
`create_ml_pipeline`：reporter 呼叫處 `except InvalidValidationArgument ⇒ HTTPException(500, "strategy_validation reporter argument error")`、
**`except ValueError ⇒ HTTPException(500, "strategy_validation reporter internal error")`**（reporter 路徑之 ValueError 一律內部錯，非用戶 400；例外文字只進 log）；
外層在 `except ValueError` 之前加 **`except HTTPException: raise`**（消除 `Internal error: 500: …` 重包）。
**取代 A1-16 第 2 點「由 route 既有 500 路徑處理」之字面**：既有 500 路徑對 `ValueError` 子類會先命中 400 分支，故須在 reporter 呼叫處顯式分類。
回歸鎖：`test_bare_value_error_from_reporter_is_5xx_not_400`；`test_wiring_error_negative_t_years_is_5xx_not_reporter_failed` 加 detail 字面斷言。

### M2（修）reporter 先於落盤（`CODEX-R16-P2-03`／`GROK-R16-P1-02`）
reporter 為純讀 ⇒ 呼叫移到 `pipeline_file` 寫入之前；5xx 即不落盤，無需 cleanup。回歸鎖：上述兩測試加「儲存目錄無 json」斷言＋`test_success_path_persists_pipeline_after_reporter` 對照。

### M3（修，雙鎖）驗收①「skew=0、kurt=3」（`CODEX-R16-P2-01`／`GROK-R16-P2-03`）
新增 `_kurt3_returns()`：`m±s` 各 n₁ 個＋4n₁ 個 `m` ⇒ population skew=0、Pearson kurt=N/(2n₁)=3（均值位移不改中央矩）；
`test_n_one_equals_psr_closed_form_with_exact_skew0_kurt3` 先斷言矩（atol 1e-12）再斷言 DSR ＝ 閉式 `Φ(SR√(T-1)/√(1+SR²/2))`（atol 1e-10）；
原「樣本矩獨立重算」案例保留為第二鎖（更強不變量）。

### M4（修）`test_deflated_sharpe._ledger` fixture 不變式（`CODEX-R16-P2-02`／`GROK-R16-P2-04`）
`n_failed_or_pruned = n_evaluated - n_valid_metrics` 由構造成立＋fixture 自檢斷言。

### M5（修＋契約）`n_source_values`（`GROK-R16-P2-02`；composer 段 B1 同建議）
契約新增頂層 **`n_source_values = ["ledger","ledger_unavailable","assumed_not_ledgered"]`** ⇒ 頂層鍵 **16 → 17**
（**覆寫** Task 2.1／A1-4 之「恰 16」；`_EXPECTED_TOP_LEVEL_KEYS`／`test_exactly_seventeen_top_level_keys` 同步）。
`validate_against_contract` 之 `{k}_values` 機械對映**自動**涵蓋 `eligibility.n_source`；`min_btl.py`／`reporter.py` 之三字面經 `_validated_n_source` 於構造時檢查。
回歸鎖：`test_n_source_values_are_contract_enum_and_validated`。

### M6（修）`factories.py` 誤插一行 runtime import（`CODEX-R16-P3-04`）
主委 `sed` 之模式同時命中 `create_adversarial_validator()` 內之 lazy import 行 ⇒ 多插一行無用 import；已刪。教訓：多處同型行做 `sed` 前先 `grep -c`。

---

## A1-23 — B4 實作備註（主委自產；**已由 R18 裁定，#1／#2／#6 被 A1-24 覆寫，#3／#4／#5／#7 維持**）

- **來源**：B4 實作（Task 4.1／4.2／4.3／2.4，commit 見 git log `feat(gap1): B4`）；本條為主委**主動揭露**之偏離／解讀，非委員 finding。
  依「凡寫進契約的宣稱先有反例測試」與「禁靜默假設」，逐條列出並附回歸鎖；審查若判不可接受即改回字面。
1. **Task 4.2 選擇指標之向量化**：TODO 字面「`sharpe`→`compute_sharpe(col[idx], periods_per_year=1).value_per_period`」；
   實作 `_metrics_columns()` 以向量化 `mean/std(ddof=1)`（退化 ⇒ NaN）逐欄計算——逐欄呼叫 `compute_sharpe`（scipy 矩）之
   924 path × 50 候選需 **~30s／案例**（三 golden 案例 ~95s，探針每輪再乘 20），向量化後 0.2s。
   等價鎖：`test_pbo.py::test_vectorized_sharpe_matches_compute_sharpe`（含 std=0／NaN／n<2 退化，atol 1e-15）；
   參考實作 `_metric()` 保留（仍呼叫 `compute_sharpe`）。
2. **Task 2.4 W3 之 passthrough 形態**：TODO 字面「非 `Constant` 之動態值（f-string／變數／跨檔常數別名）⇒ `[unresolved]` rc=1」；
   實作對**傳遞既有 reason 值**之封閉形態放行（`x.reason`／`x["reason"]`／`x.get("reason", <Const>)`／`A if c else B` 兩支皆合規／
   `Name` 且同檔所有指派來源皆合規或為參數），其餘（f-string／BinOp／其他 Call／跨檔別名）仍 `[unresolved]` rc=1。
   理由：`report.py`／`reporter.py` 之 `reason=eligibility.reason` 等 passthrough 為契約要求之語意（傳遞 Task 3.1／2.2 之 reason），
   若一律 unresolved 則 B4 gate「`strategy_wiring_check.sh` rc=0」**不可達**（與 A1-11 之「gate 不可達」同型病）。
   回歸鎖：mutation ⑤（`reason=f"x_{i}"`）與 ⑤b（`tmp=f"..."; reason=tmp`，經變數）皆 rc=1；六條 wiring mutation 全部 rc=1。
   誠實邊界：`Name` 之判定只追同檔 Assign／AnnAssign（不做跨函式資料流）；參數（無指派）視為 passthrough。
3. **`ledger.py` 之 `reason = reasons_seen[0] if reasons_seen else ""` 改為 `_REASON_ROW_INVALID if _REASON_ROW_INVALID in reasons_seen else ""`**：
   前者為動態取值（W3 unresolved）；今日 `reasons_seen` 只可能含 `ledger_row_invalid`，改寫後行為逐位相同（`test_ledger.py` 25 passed），
   未來多 reason 須顯式處理（fail-closed 於 wiring 閘）。
4. **Task 4.2「`len(candidate_ids)!=n_candidates ⇒ ValueError`」不可達**：守衛（Task 4.3）先跑且其 count 三方比對已涵蓋
   `n_candidates == len(candidate_ids)` ⇒ 不等時回 `universe_provenance_unverifiable` 而非 raise（`test_pbo.py::test_transpose_raises_and_short_t_ok` 具名記錄）。
   `returns_matrix.shape` 不符仍 raise（轉置案例）。
5. **golden 檔**：`tests/momentum/Analysis/golden/gap1_reference_cases.json`（§G 應於 Task 3.1 前建立，主委於 B4 補建——B3 之解析常數測試已內嵌同值，
   golden 建立後以 `test_pbo.py::test_golden_file_sha256_and_analytic_constants` 對照）；`sha256` 常數住 `test_pbo.py`（改檔須兩處變更）；
   alpha 之 `mu` 由公式重算 `atol=1e-18`（`alpha_undetectable` 之 JSON 字面須為完整 double `0.00010684346079267205`，
   `1.068434607926721e-04` 差 5.4e-20 會使 atol 1e-18 斷言失敗——主委實測）。
6. **PBO 名次分母**：TODO「`r = rank/(len(valid_cols)+1)`」——實作以「該 path **OOS 亦有限**之候選」為名次母體（`rankdata` 對 NaN 會使全體名次為 NaN）；
   champion 於 OOS 非有限 ⇒ 跳過（A1-15）；其他候選 OOS 非有限 ⇒ 自名次母體剔除並計 `n_path_exclusions`。全 OOS 有限時與字面等價（golden 三案例 excl=0）。
7. **PBO 效能／探針**：§V-4（champion 改由 OOS 選）⇒ golden noise band 轉紅；§V-6（守衛移除）⇒ 6 條轉紅；
   §V-14（原始索引取名次）首版**未轉紅**（探針抓到：測試矩陣中原始索引＝壓縮位置）⇒ 新增 `test_rank_uses_compressed_position_not_original_index`
   （欄 0 全 NaN 使 valid_cols=[1,2,3]、champion 原始索引 3）⇒ 轉紅。探針 17 → **20** 條。

---

## A1-24 — 🔴 B4 code review 六群集修補（N1–N6）：W3 白名單收窄／PBO 守字面母體／exclusions 計數／雙冠手算鎖／`compute_sharpe` 逐位等價／golden 單一 loader

- **來源**：B4 實作 code review（`20260818-GAP1-B4-REVIEW-R18`，三家 13 findings：codex 6／composer 2／grok 5；
  收斂檔 `handoffs/reconcile/20260818-gap1-b4-review-r18/synth.md` 群集 N1–N6）。三家 Verdict 一致「需修補後收工」；分歧取較嚴、**全部本輪修**。
- 🔴 **被推翻之主委假設（A1-23 自揭七項之裁定）**：#1 向量化等價鎖**不足**（近常數欄兩邊皆非 NaN 但值不同）⇒ N5；#2 W3 passthrough **有洞**（`reason=data["x"]`／`reason=o.other`／`.get` 首參數不驗／區域遮蔽）⇒ N1；
  #6 OOS 名次母體**改變定義**（codex 引原典 Algorithm 2.3 全 N）⇒ N2 守字面；#3／#4／#5 三家可接受（#5 為過程債入帳）；#7 之 §V-14 補測獲確認；另 ④b 雙冠測試三家皆判廉價綠燈 ⇒ N4。

### N1（修）W3 passthrough 封閉白名單＋W2 死枚舉判定（`CODEX-R18-P1-03`／`GROK-R18-P1-01`／`CODEX-R18-P2-06`）
**覆寫 A1-23 #2**。W3 允許之非 Constant 形態**僅**：① `<x>.reason` ② `<x>["reason"]` ③ `<x>.get("reason", <合規>)` ④ `A if c else B`（兩支合規）
⑤ `Name`＝該函式參數／同**函式作用域**內所有指派來源合規／模組頂層 str 常數（函式內同名指派**遮蔽**）。其餘（任意 Attribute／Subscript／其他 Call／JoinedStr／BinOp／跨檔別名）⇒ `[unresolved]` rc=1。
W2「已接線」＝出現於 reason 位置（三形，逐作用域解析）**或**為被引用之模組 str 常數之值；只在 docstring／未引用常數 ⇒ 死枚舉 rc=1。
回歸鎖：`test_wiring_check.py` 新增 5 條非白名單反例（rc=1）＋白名單正例（rc=0）＋未引用常數死枚舉（rc=1）；六條原 mutation 不變。
連動：`pbo.py` 守衛回傳改 `GuardResult(NamedTuple)`（tuple 相容；`guard.reason` 為白名單形態）。

### N2（修）PBO 名次母體與分母**守 Frozen 字面**（`CODEX-R18-P1-02`／`GROK-R18-P2-03`）
**覆寫 A1-23 #6**：名次母體＝`path_valid`（IS 有限之候選）、`r = rank/(len(path_valid)+1)`；**任一** path 有效候選之 OOS metric 非有限 ⇒ 該 path 跳過
（含 A1-15 之 champion 情形），**不**在縮小母體上取名次（`rankdata` 對 NaN 不可用是實作困難非語意依據；縮小母體會系統性改變 r）。golden 三案例 excl=0 不受影響。
回歸鎖：`test_non_champion_oos_degenerate_skips_path_keeps_denominator`；`test_denominator_is_path_valid_count_plus_one`（④c 改為兩次真實 PBO 呼叫）。

### N3（修）`n_path_exclusions` 每候選每 path 至多 +1（`CODEX-R18-P1-01`／`GROK-R18-P2-02`）
IS 非有限 +1；OOS 非有限 +1（含 champion）；path skip 不再額外 +1。④d 改為精確斷言（fixture 手算＝2）。

### N4（修）④b 雙冠測試改手算可證偽（`CODEX-R18-P2-04`／`COMPOSER-R18-P2-01`／`GROK-R18-P2-01`）
`test_double_champion_takes_smallest_index_hand_computed`：path 0 IS 平手欄 1／3 ⇒ champion 欄 1、OOS 名次 2/4 ⇒ ω=ln(2/3)（誤取欄 3 ⇒ ln 4 即紅）；path 1 ⇒ ω=ln(7/3)；斷言 `logits_min/max` atol 1e-12。

### N5（修＋殘留 G1-R11）`_sharpe_pp_1d` 與 `compute_sharpe` **逐位相同**（`CODEX-R18-P2-05`／`COMPOSER-R18-P2-02`）
**覆寫 A1-23 #1**：`_metrics_columns("sharpe")` 改逐欄 1-D 縮減（同 `values.mean()`／`values.std(ddof=1)` 呼叫序與退化判定），等價鎖改 `==` 並加入 `0.01` 近常數欄與 `1e-9` 微擾欄；仍秒級。
`compute_sharpe` 對浮點非精確常數不視為退化＝B1 已蓋章語意，本批不動 ⇒ **G1-R11**（needs-research：容差判準）登記於 registry。

### N6（修）golden 單一 loader（`GROK-R18-P2-04`）
`tests/momentum/Analysis/strategy_validation/_golden.py`（sha256 常數唯一定義處）；`test_pbo.py`／`test_min_btl.py`／`test_deflated_sharpe.py` 皆經此驗 sha 並對照 golden。
過程債具名：§G「Task 3.1 動工前建立」golden 檔於 B4 補建（B3 之解析常數測試當時內嵌同值；本條後三檔皆讀 golden）。

---

## 淨變動摘要（供 R9 複驗逐項對證）

| 對象 | R8（母 SPEC） | A1 後 |
|---|---|---|
| Task 2.1 頂層鍵 | 15 | **17**（＋`universe_scope_values`；A1-22 ＋`n_source_values`） |
| `n_fields` | 5 | **6**（＋`n_rows_rejected`） |
| `reasons` | 11 | **12**（＋`reporter_failed`） |
| `report_sections` required_keys | 未列（空殼） | **五節逐字**（A1-13） |
| §V mutation | 13 | **15**（＋§V-14／15；§V-4 改為可證偽） |
| §G PBO golden 案例 | 2（noise／alpha） | **3**（noise／alpha_detectable／alpha_undetectable） |
| Task 2.4 落點 | B2 | **B4 末** |
| B4 依賴 | B1 1.1/1.2/1.4＋B2 2.1 | **＋B2 2.2、B3 3.3** |
| §N 殘留 | 8（G1-R1..R8） | **8**（−R8 收回為小票、＋R9） |
| PBOResult 欄位 | 無 `universe_scope` | **＋`universe_scope`** |
| reporter 捕獲例外（A1-16） | 含裸 `ValueError` | **`(OSError, json.JSONDecodeError, ContractViolation)`**；新增 `InvalidValidationArgument` |
| wiring W1/W4 收集範圍（A1-17） | 函式 body 全部 Constant | **僅函式頂層無條件路徑**；mutation 5→**6** |
| Task 3.4 驗收（A1-16） | 7 項 | **8 項**（＋`InvalidValidationArgument` ⇒ 5xx） |
| §R 回退（A1-18） | B3／B4 可獨立 revert | **B4 ⊃ B3；先 revert B4 再 B3** |
