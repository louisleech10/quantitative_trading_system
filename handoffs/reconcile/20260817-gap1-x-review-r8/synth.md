# Reconcile — 20260817-gap1-x-review-r8

**來源** 20260817-gap1-todoadv-r8-codex.md, 20260817-gap1-todoadv-r8-composer.md, 20260817-gap1-todoadv-r8-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-17；TODO 第一輪 adversarial → TODO R2＋SPEC 延伸檔 A1）

三家共 **22 條** canonical ID（codex 12／grok 7／composer 3）；下列六群集**引用全部 22 條，0 掉項**。
主委自產版 `handoffs/20260817-gap1-todoadv-r8-claude.md`（非鎖來源）另含 3 條 P0，三家皆未提出，列為群集 J1。
Verdict 分歧＝codex「有根本缺陷需重作」／grok・composer「需修補後派工」⇒ **看碼證不數人頭**：
codex 之 P0-02（champion 剔除後索引越界）為可執行反例，屬實作級而非結構級；其 P0-01（ledger 本身可能已是 top-K）
為純統計層不可自證之邊界，處置＝新增可觀測欄位＋具名殘留（見 J3-b）。
⇒ 主委裁定＝**需修補後派工**（不重作 SPEC 架構），但修補涉 SPEC 義務者一律走**延伸檔** A1（凍結文件不就地改）。

### J1 — §G／§V 三處數值 golden 經實跑證偽（主委自產版；三家未發現）
**引用**（非鎖來源，不計入 completeness）: CLAUDE-R8-P0-01, CLAUDE-R8-P0-02, CLAUDE-R8-P0-03
receipt: `handoffs/run_receipts/20260817T143000Z-gap1-todoadv-claude-pbo-probe.{py,log}`

1. **alpha oracle 為假等式**：`mu = 0.01*1.0/sqrt(8760)`（per-period SR≈0.0107）之 PBO 實測 **0.5411／0.6201／0.5487**
   （三種 RNG 變體），非 SPEC §G 宣稱之 `< 0.30`。根因＝IS/OOS 各 600 obs 之 SR 標準誤 ≈0.041 ≫ 0.0107。
   **處置（A1-1）**：alpha 改以 per-period SR 定義 `mu = sigma_per_period * 0.15`（＝3.7 個 IS 標準誤），
   斷言 `pbo < 0.30`（實測 0.0054／0.0000）；原「年化 SR 1.0」案例**保留為第三個 golden**：
   `mu = 0.01*1.0/sqrt(8760)` ⇒ `pbo > 0.40`（弱 alpha 不可偵測之誠實 oracle）。
2. **全噪音 band 不可重現**：`[0.40,0.60]` 於 `default_rng` 為 0.6483／`(50,1200).T` 為 0.6158／legacy `seed` 為 0.5357
   ⇒ 三種合理實作有兩種落在 band 外，golden 依 RNG API 與抽樣順序而變。
   **處置（A1-2）**：golden 檔逐字寫死 `rng = np.random.default_rng(20260817)`、
   `M = rng.standard_normal((n_obs, n_candidates)) * 0.01`（形狀順序即 `(T,N)`）；band 放寬為 `[0.30,0.70]`
   並附理由（924 path 高度相關，有效獨立樣本遠小於 924）；三個 RNG 變體實測值寫入 golden `provenance`。
3. **§V-4 mutation 不可證偽**：CSCV IS/OOS 對調在 `combinations(range(S), S//2)` 之補集封閉性下
   只改 path 順序，PBO 逐位相同（實測 swapped 0.6483／0.6158／0.5357，與原值相等）。
   **處置（A1-3）**：§V-4 改為「champion 改由 **OOS** metric 選（選法失效）⇒ 噪音 band 與 alpha 案例至少一條轉紅」。

### J2 — Task 2.4 wiring 閘：批次落點不可達 ＋ 字面掃描非封閉集合
**引用**: GROK-R8-P0-01, CODEX-R8-P1-08, COMPOSER-R8-P2-01, GROK-R8-P2-01

grok 之 P0-01 為 BLOCKING 且成立：TODO 把 2.4 放 B2、又要求 B2→B3／B3 收尾 `strategy_wiring_check` rc=0，
而 W1／W4 依賴 Task 3.3 之 `report.py`（B3）、W2 依賴 3.2／4.2／4.3 之 6 個 reason 字面（B3／B4）
⇒ B2 出口依文執行必 rc=2、B3 出口必 rc=1。codex／composer 另指出掃描本身非封閉集合
（未 `re.escape`、未限 `build_validation_section` body、W3 漏 dict-key 與 `reason = "x"` 賦值形）。

**處置（TODO R2）**：
1. Task 2.4 **移至 B4 末**（批內順序 4.1→4.2→4.3→2.4，Task 編號不變以保追溯）；
   §B 表 B4 依賴補「B3 Task 3.3（`report.py`）」；B2→B3／B3 收尾 gate **移除** wiring rc=0，只留 B4 收尾。
2. W1／W4 改 **AST**：`ast.parse(report.py)` → 取 `build_validation_section` 之 `Return` 節點所組裝之 dict 鍵集合
   （含其函式 body 內指派給該 dict 之 `ast.Constant` 鍵），與契約 `report_sections`／`eligibility_keys` 做集合比對。
3. W3 改 AST 掃三形：`reason=<Constant>`（keyword／assign）、`{"reason": <Constant>}`（dict key）、
   `<x> == <Constant>` 之比較；非 `Constant` 之動態值 ⇒ 列 `[unresolved]` 並 **rc=1**（fail-closed，不放行）。
4. Task 2.4「不可做」新增誠實邊界具名：不追跨檔常數別名與 f-string（若出現 ⇒ rc=1，不假綠）。
5. 治理連動路徑具名（codex）：`plain_docs_sync_check.sh` 於 `gov_check`／pre-push 硬擋，`--staged` 只提醒 ⇒
   TODO 改寫「本 Task commit 後須跑 `bash scripts/gov_check.sh --fast`（非 `--staged`）」。

### J3 — Task 4.x 統計核心：champion 剔除索引 ＋ ledger 完整性不可自證
**引用**: CODEX-R8-P0-02, CODEX-R8-P0-01

**J3-a（codex P0-02，BLOCKING，可執行反例，主委複驗成立）**：TODO 3 步驟 2 先固定 IS champion 之
**原始欄索引**，再對 path 有效候選之**壓縮陣列**取 `rankdata(...)[champion]` ⇒ champion 於 OOS 退化被剔除時
越界或誤取他人名次（codex 實跑反例：3 候選、IS champion=2、`rankdata([0.1,0.2])[2]` → IndexError rc=1）。
**處置（TODO R2）**：
1. path 有效集合以 `pos = {col_index: compressed_pos}` 建映射；rank 一律經 `pos[champion]` 取值，禁用原始索引。
2. **champion 於 OOS 非有限 ⇒ 跳過該 path**（計入 `n_paths_skipped`，並 `n_path_exclusions += 1`）；
   **不**重選 champion（重選會改 IS 選法語意）。
3. 新增驗收 ④d（上述三候選反例 ⇒ 該 path skipped、不 raise、PBO 分母為 `n_paths_used`）
   ＋ **§V-14 mutation**（改回原始索引 ⇒ ④d 轉紅／IndexError）。

**J3-b（codex P0-01，BLOCKING；主委裁定為層界限制，處置＝可觀測＋具名殘留）**：
三項守衛證明「候選集合＝ledger 記錄之集合」，**不**證明「ledger 記錄了全部試過的候選」——後者只能由生產者側
（`append_trial_attempt` 唯一寫入口＋G1-R4 六條繞過）保證，純統計層無 SoT。
codex 建議二擇一：不可偽造之 exhaustive proof（本層不可能）或一律非 ok（會使 PBO 永無可用路徑，違交付範圍 A）。
**主委採第三條且較嚴之可觀測版（TODO R2＋A1-4）**：
1. `PBOResult` 新增 `universe_scope: str`，值集合＝契約新增頂層鍵 `universe_scope_values`＝
   `["ledger_recorded_only"]`（今日唯一值；未來 G1-R4 落地後可加 `producer_conformance_verified`）。
2. `report.py` 之 `pbo` 節必帶 `universe_scope`；`build_validation_section` 於
   `pbo.universe_scope == "ledger_recorded_only"` ⇒ **強制** `display_downgrade=True`（即使三關皆 ok）。
   ⇒ PBO 可算、可顯示，但**機械地**不得被當作「已證明無選擇偏誤」。
3. 新增驗收：`test_pbo_universe_guard.py` ⑤d「三項全符 ⇒ status ok 且 `universe_scope=="ledger_recorded_only"`」；
   `test_report_section.py` ⑤「三關皆 ok 但 `universe_scope=="ledger_recorded_only"` ⇒ `display_downgrade is True`」。
4. registry 新增 **G1-R9**「ledger 完整性（無事後 top-K 寫入）之生產者側證明」
   `為何現在不做: blocked-by:G1-R1（無生產者即無寫入面可證；純統計層無外部候選宇宙 SoT）`；
   觸發＝G1-R1 落地；驗收錨點＝`universe_scope` 可升為 `producer_conformance_verified`。
   **不得宣稱本票已關閉 top-K 污染面**（僅關閉「呼叫方挑子集」一半）。

### J4 — Task 3.4 reporter：輸入鏈不完整、回應形狀漂移、例外政策過寬
**引用**: CODEX-R8-P1-04, GROK-R8-P1-02, COMPOSER-R8-P1-01, COMPOSER-R8-P1-02, CODEX-R8-P1-05, GROK-R8-P2-02

四家一致（含主委自產 P1-02／03／04）：`for_study_trial(study_name, trial_number)` 缺 `t_years`／`target_sharpe`／
`provenance` 來源，而 `assess_eligibility` 對 `t_years<=0` raise ⇒ 恆走 except ⇒ 回應**恆** `computation_failed`，
連 SPEC 明言之「誠實 `eligible=None`＋降級」都產不出；`dataset_key=f"trial:{n}"` 為 TODO 自創且與 Task 2.2
之 dataset 級語意衝突（per-trial 會使 `n_candidates_considered≡1`）；例外全吞會掩蓋真 bug。
**處置（TODO R2）**：
1. 簽名改 `for_study_trial(study_name: str, trial_number: int, *, dataset_key: str | None = None,
   t_years: float | None = None, target_sharpe: float | None = None) -> dict`。
2. `dataset_key is None` 或 `t_years is None` 或 `target_sharpe is None` ⇒ **不呼叫** `read_trial_ledger`／
   `assess_eligibility`，直接組 typed `EligibilityResult(eligible=None, status="unavailable", reason="n_unknown", …)`
   → `build_validation_section(dsr=None, pbo=None, …)`。route 今日三者皆傳 None（無 study metadata）。
   **禁** per-trial `dataset_key` 公式；未來由 G1-R1 生產者契約提供 dataset 級鍵。
3. 回應**投影三鍵**（SPEC 逐字，關 composer P1-02）：`strategy_validation = {"eligibility": …,
   "display_downgrade": …, "warning_text_key": …}`；其餘節不進 API（前端契約待 G1-R3）。
4. 例外分類（關 codex P1-05／grok P2-02）：只捕 `(OSError, json.JSONDecodeError, ContractViolation, ValueError)`
   ⇒ 回契約合法之降級結構、`reason="reporter_failed"`（契約 `reasons` 新增第 12 值，`reason_conditions` 同步）；
   **其他例外一律往上拋**（由 route 既有 500 路徑處理）；捕獲路徑必 `logger.error(..., exc_info=True)`，
   例外文字**只進 log 不進回應**（關「自創 reason 字面」與 W3 衝突）。
5. 新增驗收 ⑥「reporter 內部 `TypeError` ⇒ HTTP 5xx（**不**吞）」＋ ⑦「`OSError` ⇒ 2xx 且 `reason=="reporter_failed"`」。

### J5 — SPEC↔TODO 抄寫漂移與契約未定項（七處）
**引用**: GROK-R8-P1-01, CODEX-R8-P1-03, CODEX-R8-P1-06, CODEX-R8-P1-07, CODEX-R8-P1-09

主委裁定：**以較嚴／較可 fail-closed 之一方為準，並回寫 SPEC 延伸檔 A1**（TODO 不得私自修正 SPEC）。
1. `assess_eligibility` 簽名（grok P1-01／codex P1-03）：採 **TODO 版** `ledger_result: LedgerReadResult`
   （優於裸 `n_trials`：status 可傳遞）；SPEC 驗收⑤ 之 `n_trials=100` 改 `ledger_result=<n_for_dsr=100 fixture>`。
   **刪** TODO 自創之 `budget_capped` 與 `x>700 ⇒ 10**18` cap（codex 舉反例：`t_years=1500,SR=1` ⇒ `x=750`，
   `floor(exp(750))` 遠大於 cap，§G 不變式失效）⇒ 改 `x > 700 ⇒ raise ValueError`（fail-closed；
   `math.exp(710)` 本身即 OverflowError，該輸入無物理意義），`EligibilityResult` 欄位不新增。
2. Task 1.4 `t_semantics`（codex P1-06）：採 **TODO 版**（必填參數，呼叫方選語意）；A1 補寫 SPEC 簽名
   `extract_period_returns(backtest_result, *, timeframe, t_semantics)` 與「DSR 只接 `trade_level`／
   `nonzero_return_bars`」之選定規則。
3. B4 依賴（codex P1-09）：SPEC:499 只列 B2 Task 2.1，實則需 2.2 之 `LedgerReadResult` ⇒ A1 改為
   「B4 依賴 B1 1.1／1.2／1.4、B2 2.1／2.2、B3 3.3（因 2.4 移入 B4 末）」。
4. ledger 計數不變式（codex P1-07，真 bug）：現行文字使「schema-valid 但 `metric_valid=False`」之列
   落不進任何計數 ⇒ `n_evaluated == n_valid_metrics + n_failed_or_pruned` 失敗。**處置**：
   `n_evaluated`＝schema-valid 列數；`n_valid_metrics`＝schema-valid ∧ `metric_valid=True`；
   `n_failed_or_pruned`＝schema-valid ∧ `metric_valid=False`（不變式由構造成立）；
   schema-invalid 列改計入**新增** `n_rows_rejected`（契約 `n_fields` 五值→**六值**）＋`reason=ledger_row_invalid`。
   SPEC 2.2 驗收② 之「`n_failed_or_pruned==1`」改 `n_rows_rejected==1`，另加「合法列但 `metric_valid=False`
   ⇒ `n_failed_or_pruned==1` 且不變式成立」之 fixture。
5. DSR 分母重複定義（主委 P1-06）：TODO 3.2 自算 `den`，與 SPEC「分母恆取 Task 1.2 之 `sr_estimator_variance`」
   衝突，且使 §V-10 mutation 無法如 SPEC 所稱使 3.2 斷言① 轉紅 ⇒ TODO 改
   `stat = (SR_obs - SR0) / sqrt(sr.sr_estimator_variance)`，刪 `den`（代數等價，單一定義處）。
6. `report_sections` 逐節 `required_keys` 未列（主委 P1-08，空殼）＋`variance_source="explicit"` 缺值之 reason
   漂移（主委 P1-07）＋Task 3.3 誤寫 `provenance.n_source`（應屬 `eligibility`）：A1 逐字定義五節必填鍵：
   `eligibility`＝`eligibility_keys` 九鍵＋`status`／`reason`；
   `min_btl`＝`status`／`reason`／`required_years_upper_bound`／`available_years`／`trials_budget`／`trials_used`／`target_sharpe`；
   `dsr`＝`status`／`reason`／`value`／`sr0`／`sr_obs_per_period`／`n_trials_used`／`variance_source`／`n_independence`；
   `pbo`＝`status`／`reason`／`value`／`n_paths_used`／`n_paths_skipped`／`n_candidates_invalid`／`universe_scope`；
   `provenance`＝`status`／`reason`／`n_semantics`／`t_semantics`／`annualization_source`／`n_independence`。
   `variance_source="explicit"` 而值為 `None`／缺 ⇒ `cross_trial_variance_unavailable`；
   有值但非有限或 `<=0` ⇒ `degenerate_returns`（兩情形各一測試）。
7. 反向測試 vacuous（主委 P1-09）：Task 1.1 新增 `available_years(*, n_bars, timeframe) -> float`（唯一推導處），
   §V 反向測試改以真實 kline 長度（1h=20352／4h=5088／12h=1696）三 timeframe 對照 `2.3232876712328765`
   （`atol=1e-6`）；mutation §V-15「`available_years` 回 `n_bars`」⇒ 轉紅。

### J6 — §N／registry 殘留分類：三條「為何現在不做」不成立
**引用**: GROK-R8-P1-03, GROK-R8-P1-04, CODEX-R8-P1-10, CODEX-R8-P1-11, CODEX-R8-P1-12

三家與主委獨立指向同三條（G1-R3／R7／R8），其餘五條（G1-R1／R2／R4／R5／R6）四方一致**成立**。
**處置（A1＋registry）**：
1. **G1-R3 前端降級面板**：`blocked-by:G1-R1／R2（後端無資料）`**不成立**——Task 3.4 已把
   `display_downgrade`／`warning_text_key` 送到 API，空/降級面板現在就能做。改
   `為何現在不做: user-ruling:2026-08-17 交付範圍 A 不含 frontend（成熟度地圖：frontend 屬不完整層）`；
   觸發改「使用者要求 UI，或 G1-R1／R2 任一落地」。
2. **G1-R7 MinBTL 上界誤差量化**：`needs-research` 之**誤差帶量化**部分維持（無公認可驗方法即無法定義通過條件），
   但「排程即可做」不是可判定觸發（codex P1-11）且**保守性驗證現在就能做**（主委 P1-10）⇒ **部分收回**：
   Task 3.1 新增驗收⑨ 統計 oracle——`default_rng(20260817+k)`（k=0..19）、100 條 iid 噪音策略、
   `T=9.210340371976184` 年日頻（`n_obs=3362`）⇒ `mean(max annualized SR) <= 1.0` 且與解析值
   `0.833943` 之 `rtol<0.05`（主委實跑：mean=0.843077，receipt
   `handoffs/run_receipts/20260817T150000Z-gap1-minbtl-conservatism-probe.{py,log}`；
   **注意** per-seed 上界不成立（max=1.216377）⇒ 斷言只可下在 20 seed 平均，禁寫成逐 seed）。
   殘留只留「誤差帶精確量化」，觸發改「具名票 `GAP-1-R7-MC`（owner＝Claude 主委）建立且排入 ROADMAP 時」。
3. **G1-R8 `prediction_analyzer.py:155` cumsum**：`blocked-by:不在策略路徑` 為 **scope 裁決非依賴**（三值不成立）
   ⇒ **收回為獨立小票**（不再是殘留）：`docs/ROADMAP.md` 新增小票「PA-CUMSUM 單利權益改正」，
   排在 GAP-1 B4 完工後，由 Claude 自做（小任務流程）；自 registry 殘留表移除該列。

### 收斂結論（主委）
- 22 條委員 ID 全數處置（0 掉項）＋主委自產 3 條 P0；共 **6 群集**。
- 兩條 BLOCKING（grok P0-01 拓撲、codex P0-02 索引）已修；codex P0-01 轉為可觀測欄位＋G1-R9 具名殘留。
- 修補分兩處落地：**SPEC 延伸檔** `docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md`（A1-1..A1-15；
  凍結文件不就地改）＋ **TODO R2**（DRAFT 就地改）。
- 契約（Task 2.1）淨變動：頂層鍵 15→**16**（新增 `universe_scope_values`）；`n_fields` 5→**6**；
  `reasons` 11→**12**（`reporter_failed`）；`report_sections` 五節 `required_keys` 逐字補齊。
- §V mutation 13→**15**（新增 §V-14 champion 索引、§V-15 `available_years`）；§V-4 改為可證偽形式。
- **下一輪＝R9 受限複驗**：範圍＝① 22 條 closure ② J1 三條數值修補之新 golden 是否可重現（要求實跑）
  ③ 新增機制（AST wiring／`universe_scope`／例外分類／`n_rows_rejected`）之攻擊面。
  不受理新一般性議題，除非附可執行反例且會使 B1–B4 數值錯誤或不可重現。

**Verdict**: 需修補後合併 → 修補於 SPEC 延伸檔 A1 與 TODO R2 落地，交 R9 受限複驗後方可 Frozen。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R8-P0-01

**斷言**: Task 4.3 的三項守衛仍可讓一個 ledger 本身只記錄事後挑出的 top-K 宇宙回傳 `ok`，因為沒有 exhaustive/unselected coverage proof。

**碼證**: SPEC:295-311/TODO:156-161 將 `n_is_lower_bound` 固定為 `True`，但 SPEC:583-599/TODO:313-317 只比 `candidate_ids` 集合、三方 count、呼叫方 hash。已實跑 `venv/bin/python -c '...'`：`selection_free=True source=ledger_all_candidates n_is_lower_bound=True`、`set_count_hash_checks=(True, True, True) status_if_guard_is_literal=ok`，其中 10 個 `top-*` ID 可同時被假想為「已選後才寫入 ledger」。RECHECK：同 probe 置換任意 top-K ID 集合即可重跑。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[BLOCKING] 這不是 R6 已修的「同數量異集合」問題，而是 ledger 內容本身不具全宇宙證明；PBO 會在污染的候選宇宙上正常產值。需新增不可偽造的 exhaustive/selection-free provenance（或明確把 `n_is_lower_bound` 非 `ok`），並增加「ledger 自己只含 top-K 但三項皆自洽」反例。

## CODEX-R8-P0-02

**斷言**: Task 4.2 在 path 級剔除 OOS 非有限候選後，仍直接用原始 IS champion 索引取 rank，champion 被剔除時結果可錯算或拋 IndexError。

**碼證**: SPEC:541-555/TODO:300-302 要求 IS champion 固定後，若候選在 IS 或 OOS 非有限則從該 path 剔除；TODO 又指定 `rankdata(oos_metrics, method="average")[champion]`，未定義 champion 不在 OOS 有效集合時的行為。已實跑最小反例：`venv/bin/python -c 'from scipy.stats import rankdata; candidate_ids=("c0","c1","c2"); champion_index=2; path_valid=(0,1); oos_metrics=rankdata((0.1,0.2), method="average"); print("candidate_ids=%r path_valid=%r champion_index=%d" % (candidate_ids, path_valid, champion_index)); print("oos_rankdata=%r" % (oos_metrics)); print("pseudocode_index_result=%r" % (oos_metrics[champion_index]))'` → `IndexError: index 2 is out of bounds for axis 0 with size 2`、`pbo_counterexample_rc=1`。若以壓縮陣列誤索引則會把別的候選排名當 champion。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[BLOCKING] 必須寫死「champion OOS 退化」是跳 path、重選 champion（會改 IS 語意）或回 typed non-ok；並加 champion-specific mutation/oracle。現有「多數候選常數」測試不覆蓋 champion 被剔除。

## CODEX-R8-P1-03

**斷言**: Task 3.1 的 TODO 新增 `budget_capped` 與 `10**18` cap，同時偏離 SPEC 的 EligibilityResult schema 與精確 `floor(exp(x))` 契約。

**碼證**: SPEC:375-398 的輸出欄沒有 `budget_capped`，且 §G:97-99 要求 `ub(budget)<=T<ub(budget+1)`；TODO:210-214 卻加入 `budget_capped: bool`，於 `x>700` 回未有來源的 `10**18`。Task 2.1 的 `eligibility_keys`（SPEC:266-267）也沒有 `budget_capped`，故將該欄放入 report 會違反 additional-properties gate；不放則又違反 TODO dataclass。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 對 `t_years=1500,target_sharpe=1`，真公式的 `x=750`，`floor(exp(x))` 遠大於 `10**18`，cap 後 `budget+1` 仍遠低於可行邊界，§G 不變式失效。需在 SPEC/TODO 先裁定 overflow-safe 的 exact representation 或明確上限/狀態，不能自行發明 cap 與輸出欄。

## CODEX-R8-P1-04

**斷言**: Task 3.4 的 reporter 介面沒有足夠輸入在 ledger 落地後計算 eligibility；`dataset_key=f"trial:{trial_number}"` 也不是 Task 2.2 的共同語意。

**碼證**: TODO:210 要 `assess_eligibility(..., t_years, ledger_result, target_sharpe)`，但 TODO:259 的 `for_study_trial(study_name, trial_number)` 沒有 `t_years`；TODO:261 只寫「由呼叫方傳入或無」，沒有對應參數/來源。Task 2.2 SPEC:297-311/TODO:156-161 只把 `dataset_key` 定義為讀取鍵，沒有 `trial:<n>` 規約；G1-R1 尚未接 producer。故今日 `n_unknown` 是明知降級取捨，但未來有帳本仍沒有可保證的 key/t_years 接線。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 建議將 `dataset_key` 與可驗證 `t_years`（或 PeriodReturns/artifact）納入 reporter protocol，並在 Task 2.1/2.2 只定義一次；否則 R8 wiring 只是永久 degraded placeholder。

## CODEX-R8-P1-05

**斷言**: Task 3.4 的「任何例外→2xx computation_failed」政策會把程式錯誤與可預期 unavailable 混成同一個附加回應，缺少可觀測的 fail-closed 邊界。

**碼證**: SPEC:476-492/TODO:257-269 明定 reporter 任何例外都回 `computation_failed`，且測試只要求 HTTP 仍 2xx；TODO 回傳 `str(exc)[:200]`，沒有要求 `logger.exception`、例外分類或 contract validation。這會把 TypeError、schema drift、bug 與缺 ledger 同樣降級，既有 route 的外層 Exception（api/routes/ml_pipeline.py:247-258）也不再收到錯誤。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5b

[MAJOR] 使用者裁決只是不硬擋 promote，不是允許吞掉真 bug。只捕捉明確的資料不可用/外部 I/O 例外、以 contract reason 回報並記 `exc_info=True`；對程式錯誤保留可觀測失敗，並加 mutation 令 reporter bug 不得只靠 2xx 測試通過。

## CODEX-R8-P1-06

**斷言**: Task 1.4 的 SPEC API 與 TODO API 不一致，且 SPEC 沒有說明三種 `t_semantics` 如何選定。

**碼證**: SPEC:165-189 定義 `extract_period_returns(backtest_result, *, timeframe)`；TODO:114-126 改成必填 `t_semantics`。SPEC 同時要求產出/驗證 `bar_count`、`nonzero_return_bars`、`trade_level`，但沒有 selection/default 規則；B3 的 DSR 只接 `PeriodReturns`，因此實作者依 SPEC 無法選語意，依 TODO 又會偏離 canonical signature。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 先在 SPEC/TODO 共同 API 決定 `t_semantics` 是 required input、固定 canonical value，或明確拆三個 extractor；同時把呼叫端與反向測試接上，否則 Task 1.4 不可獨立實作/驗收。

## CODEX-R8-P1-07

**斷言**: Task 2.2 的 ledger 計數規則無法滿足 Task 2.3 自己要求的 invariant，因為沒有定義 schema-valid 但 `metric_valid=False` row 如何進 `n_failed_or_pruned`。

**碼證**: TODO:159 只說「非法列」增加 `n_failed_or_pruned`；TODO:160 卻令 `n_evaluated=len(rows_valid_schema)`、`n_valid_metrics=sum(metric_valid)`；TODO:175 要 `n_evaluated == n_valid_metrics + n_failed_or_pruned`。一列合法 JSON、`metric_valid=False` 時，依文字得到 `1 == 0 + 0`，直接失敗；若把它算 failed，又需在 TODO/SPEC 明定 state/metric_valid 的優先規則。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5b

[MAJOR] 明定 failed/pruned row 的計數與 reason 累積，再加一筆合法 invalid-metric fixture；不要讓 conformance test 依實作者猜測。

## CODEX-R8-P1-08

**斷言**: Task 2.4 的 regex 不是 W1/W4 所宣稱的輸出組裝封閉集合，也不是 W3 的所有 reason literal 掃描。

**碼證**: TODO:188 以 `re.search(rf'["\']{name}["\']')` 掃整個 `report.py`，未 `re.escape(name)`、未限 `build_validation_section` AST；comment/docstring/dead branch 中的 `"eligibility"` 就能假陽性。W3 只掃 `reason="..."`/`reason == "..."`，漏掉 `{"reason": "invented"}`、`reason = "invented"` 等實際輸出。SPEC:357-367 要的是機械封閉比對，現規則可讓幽靈欄位/自創 reason 通過。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5b

[MAJOR] 使用 Python AST/限定函式的字串與 dict-key/assignment 掃描，對 mutation 覆寫 report body、comment、dict reason 與 regex-special section name 各加反例；目前 regex 不能作 wiring gate。

## CODEX-R8-P1-09

**斷言**: SPEC 與 TODO 的 B4 dependency topology 不一致；SPEC 只列 B2 Task 2.1，但 Task 4.3 明確需要 Task 2.2 的 `LedgerReadResult`。

**碼證**: SPEC:499 寫 B4 依賴「B2 Task 2.1」；SPEC:528-531、589-592 又要求 `ledger_result.candidate_ids`/`n_candidates_considered`。TODO:40 已補列 B2 2.1/2.2。TODO 雖較合理，卻代表未 reconcile 的 canonical drift：按 SPEC gate 可在 2.2 尚未存在時開 B4。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 以 Task 2.2 為 B4 硬依賴，並同步修 SPEC/TODO/B4 gate；dependency 不應靠 TODO 私自修正 SPEC。

## CODEX-R8-P1-10

**斷言**: G1-R3 的 `blocked-by:G1-R1/R2（後端無資料可顯示）` 不是充分阻塞理由；本票已定義明確的 unavailable/degraded API state，可先做空/降級消費契約。

**碼證**: SPEC:454-474 定義 `display_downgrade`/`warning_text_key`；SPEC:476-492、TODO:257-269 要 Task 3.4 在無 ledger 時仍回 `eligible=None` 與非空警語；registry:46 卻把前端面板整體延後到真實 producer/matrix。這證明「無真實資料」不等於「無可展示資料」。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#d226fa453504

[MAJOR] 若產品刻意不碰 frontend，blocked-by 應改成可驗證的 frontend scope/maturity 依賴並給 owner/票號；若不刻意排除，G1-R3 應收回為 empty/degraded UI Task。這不是樣式評分，而是殘留是否仍合理。

## CODEX-R8-P1-11

**斷言**: G1-R7 的 registry trigger「排程即可做」不可機械判定，不符合 §N 要求的可判定觸發條件。

**碼證**: SPEC:691-692 及 registry:50 將 MinBTL 誤差列 needs-research，但 registry 的 trigger 只有「排程即可做」，沒有研究完成、票號、owner、日期或 merge gate；任何時間都可聲稱已觸發/未觸發。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#d226fa453504

[MAJOR] 保留 needs-research 可以，但 trigger 至少要指向具名 research ticket/owner/status 或可驗證文獻/Monte Carlo receipt；否則殘留登記不具不遺忘功能。

## CODEX-R8-P1-12

**斷言**: G1-R8 把現存、獨立可修的 `np.cumsum` 以 `blocked-by:不在策略路徑` 留在 §N，理由不成立為本票的 blocked-by。

**碼證**: 實檔 `momentum/Analysis/prediction_analyzer.py:155` 仍是 `cum_strategy = np.cumsum(strategy_returns)`；SPEC:693-694 與 registry:51 都承認位置與語意，但 trigger 只寫「排程即可做（小票）」。它不依賴 G1-R1/R2、沒有外部研究阻塞，且 TODO:123 已明確把它隔離而非修正。

**來源摘要**: momentum/Analysis/prediction_analyzer.py#472c48fe06b6

[MAJOR] 應另開明確的小 Task（改 `cumprod` 或改名/停用策略敘事）並以其 ticket/排程狀態作 trigger；在本票中不得把「不屬本路徑」誤寫成依賴已成立。

## COMPOSER-R8-P1-01

**斷言**: Task 3.4 之 `StrategyValidationReporter.for_study_trial(study_name, trial_number)` 未定義 `assess_eligibility` 必填之 `target_sharpe`／`t_years` 與 `build_validation_section` 必填之 `provenance`，執行端無法依 TODO 寫出唯一實作；G1-R1 落地後 ledger `status=="ok"` 時仍只能得到 `eligible=None`（缺參）而非可審計三態。

**碼證**: `docs/GAP1_STRATEGY_OVERFIT_TODO.md:259-261` — 簽名僅 `(study_name, trial_number)`，內文只寫「`t_years` 由呼叫方傳入或無」但 route `:263` 未傳任何額外參；`assess_eligibility` 簽名 `:210` 要求 `t_years`+`target_sharpe`+`ledger_result`；`build_validation_section` `:243-245` 要求 `provenance` dict。RECHECK：`rg -n "for_study_trial|target_sharpe|provenance" docs/GAP1_STRATEGY_OVERFIT_TODO.md`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 信心度=High。失敗模式＝實作者自行發明 target_sharpe（違 [A-文獻] 語意）或永遠降級；修法＝TODO 增列：① `for_study_trial` 簽名增 optional `target_sharpe`／`t_years`／`timeframe` 或明確寫死「缺則 skip assess、provenance 填 `n_source=n_unknown` 等契約值」；② route 從 request／study metadata 取值之具體欄位名；③ provenance 最小 dict 模板。

## COMPOSER-R8-P1-02

**斷言**: TODO Task 3.4 暗示 `strategy_validation` 承載 `build_validation_section` 全輸出，與 SPEC Task 3.4 限定回應僅含 `eligibility`／`display_downgrade`／`warning_text_key` 三鍵子集不一致，會造成 API schema 漂移與前端（G1-R3）消費歧義。

**碼證**: SPEC `docs/GAP1_STRATEGY_OVERFIT_SPEC.md:474-476`「將 … 三者放入回應 `strategy_validation`」；TODO `:261` 呼叫 `build_validation_section(...)`（五節 `:243-245`），`:263` 僅加 `strategy_validation: dict` 未要求子集。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '474,497p'`；`nl -ba docs/GAP1_STRATEGY_OVERFIT_TODO.md | sed -n '257,265p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 信心度=High。修法＝TODO 明寫 route 只投影三鍵（或 SPEC 改允許全節——二擇一，TODO 應與 SPEC 对齐）。

## COMPOSER-R8-P2-01

**斷言**: Task 2.4 TODO 規定 W1 用引號字面 `re.search`，弱於 SPEC 要求之 AST／輸出組裝掃描，且允許在 `report.py` 註解或無關字串常量假綠而不實際組裝契約 `report_sections`。

**碼證**: SPEC `:358`「W1 … 在 `build_validation_section` 之**輸出組裝**中出現（AST／字面掃描）」；TODO `:188` 僅 `re.search(rf'["\']{name}["\']')` 全檔掃描。短節名 `dsr` 雖子串風險低，但「組裝 vs 任意字面」差距可讓幽靈 section 逃逸。RECHECK：對照 `scripts/ic_wiring_check.py` R3 之結構化掃描做法。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 信心度=Medium。修法＝TODO 改 W1 為 AST 解析 `build_validation_section` 回傳 dict 鍵集合，或限定掃描該函式 body；mutation 仍可用 tmp 契約加節 rc=1。

---

## GROK-R8-P0-01

**斷言**: TODO 將 Task 2.4 置於 B2，且 B2→B3／B3 收尾 gate 要求 `strategy_wiring_check` rc=0，但 W1／W4 依賴 Task 3.3 之 `report.py`、W2 依賴 B4 模組才會出現的 reason 字面——B2／B3 出口**不可能**全綠。

**碼證**: TODO §B 表 B2 含 2.4、gate「`bash scripts/strategy_wiring_check.sh` rc=0」在 B2→B3 與 B3 收尾；Task 2.4 W1＝`report_sections` ∈ `report.py` 字面（report 屬 Task 3.3／B3）；W2＝契約 11 個 `reasons` 皆須出現於 `strategy_validation/*.py`。本輪對 intro 映射：`universe_selection_contaminated`／`universe_provenance_unverifiable`／`insufficient_candidates`／`all_paths_degenerate` 僅 4.2／4.3；`cross_trial_variance_unavailable`／`ledger_snapshot_mismatch` 僅 3.2。B2 結束時 `report.py` 亦不存在 ⇒ 依 Task 2.4 改法應 rc=2。RECHECK：對照 TODO:37-44、184-196 與 SPEC:350-371、454-456；列出 11 reasons 與各 Task 首次字面。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[BLOCKING] 信心度=High。會怎麼失敗：執行端做完 B2 跑 gate → wiring 紅 → 無法進 B3；若為過 gate 削弱 W1/W2 則閘門空殼。修法：① 將 Task 2.4 移至 **B4 末**（或「全部 reason 字面＋report.py 皆已存在」之後的獨立 gate 批）；② B2→B3／B3 收尾 **移除** wiring rc=0，只保留 B4 總 gate；③ §B 依賴列明 2.4 → 3.3＋4.2／4.3。

---

## GROK-R8-P1-01

**斷言**: Task 3.1 `assess_eligibility` 之函式簽名與 oracle 驗收，SPEC 與 TODO **不一致**（`n_trials: int` vs `ledger_result: LedgerReadResult`），追溯表「100%」未捕捉此抄寫漂移。

**碼證**: SPEC:380 `assess_eligibility(*, t_years, n_trials, target_sharpe)`；驗收⑤ `n_trials=100`。TODO:210 `assess_eligibility(*, t_years, ledger_result, target_sharpe)`；驗收⑤ `ledger_result=<n_for_dsr=100 fixture>`。TODO 另增 `budget_capped` 與 `x>700→10**18`（SPEC 無此欄／帽）。RECHECK：`grep -n assess_eligibility docs/GAP1_STRATEGY_OVERFIT_{SPEC,TODO}.md`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 信心度=High。TODO 版更利 fail-closed 傳 status（優於裸 `n_trials`），但冷啟動「只讀 TODO」與「SPEC 義務」衝突時 agent／reviewer 會分叉。修法：二選一寫死——建議 **以 TODO 為準回寫 SPEC**（`ledger_result` 必填、`trials_used=n_for_dsr`、status≠ok⇒eligible=None），並把 `budget_capped`／exp 帽寫進 SPEC；同步 oracle ⑤ 字面。

---

## GROK-R8-P1-02

**斷言**: Task 3.4 之 `dataset_key=f"trial:{trial_number}"` 加上 `for_study_trial(study_name, trial_number)` **無 `t_years`**，使該 API 路徑在可預見期間（含 G1-R1 落地後）結構上無法給出非降級的 `eligible` 判定——不止「今日無帳本」的誠實降級。

**碼證**: TODO:259-261 簽名僅兩參；內部 `read_trial_ledger(research_session_id=study_name, dataset_key=f"trial:{trial_number}")`；`t_years`「由呼叫方傳入或無 ⇒ eligible=None」但簽名無此參 ⇒ 永無。Ledger 路徑語意（TODO:158）以 `research_session_id__dataset_key` 為檔——per-trial key 使 `n_for_dsr=n_candidates_considered` 變成「單一 trial 檔內候選數」，與 DSR 多重檢定 N（session 級）衝突。SPEC:484-486 只釘「今日無生產者 ⇒ 降級」，**未**寫死 `trial:{n}` 公式（TODO 自創）。RECHECK：讀 TODO Task 3.4＋2.2 路徑公式；對照 SPEC Task 3.4 改法段。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 信心度=High。今日恆降級＝[A-裁決-降級] **成立**；但鍵設計＋缺 `t_years` 會讓「未來接上生產者仍永遠降級／N 語意錯」成為靜默缺陷。修法：① `dataset_key` 改 session／dataset 級（與 G1-R1 生產者契約同鍵，**禁止** per-trial 當 N 宇宙）；② `for_study_trial` 增 `t_years: float|None=None`（或從 trial 產出可審計推導）；③ 文件標明「無 t_years／無 ledger ⇒ 降級」為顯式三態，而非簽名漏洞。

---

## GROK-R8-P1-03

**斷言**: §N／G1-R3「前端降級面板」之 `blocked-by: G1-R1／R2` 在 R8 收回 Task 3.4 後**不再成立**——後端已可提供可顯示之 `strategy_validation` 警語欄位。

**碼證**: SPEC:674-676 與 registry G1-R3 皆寫 blocked-by 殘留 1／2；同列落地錨點「消費 API 之 `strategy_validation`（Task 3.4 已送到）」自相矛盾。Task 3.4 驗證①② 保證成功回應含 `display_downgrade is True` 與非空 `warning_text_key`。前端最小橫幅不需 R1／R2 矩陣資料。RECHECK：對讀 SPEC §N 第 3 項、registry 表 G1-R3、TODO Task 3.4。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#d226fa453504

[MAJOR] 信心度=High。不是要求本 TODO 做前端（成熟度地圖可繼續排除），而是 **三值理由寫錯**。修法：改 `user-ruling:2026-08-17 本票範圍 A 不含 frontend`（或等價）；觸發改「產品要 UI 時」；刪「後端無資料」表述。

---

## GROK-R8-P1-04

**斷言**: G1-R7／§N MinBTL 近似誤差之 `needs-research` 不成立——有公認 Monte Carlo 量化路徑；與 registry「觸發：排程即可做」互相矛盾。

**碼證**: SPEC:691-692 `needs-research:Monte Carlo 量化…`；registry G1-R7 觸發「排程即可做」。`needs-research` 範本語意＝無公認方法；MC 誤差帶是標準工程，非待發表方法學。本 finding **不**要求本票計算精確 MinBTL（brief 不受理），只攻分類。RECHECK：讀 SPEC:691-692 與 registry:50。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 信心度=Medium-High。修法：改 `user-ruling:`／`blocked-by: 另票排程（非本 epic 範圍）`；保留 `upper_bound` 誠實語意。勿繼續標 needs-research 以免日後「研究完成」假觸發。

---

## GROK-R8-P2-01

**斷言**: Task 2.4 W3 只掃 `reason="..."`／`reason == "..."` 兩種字面，動態／常數指派之自創 reason 可逃逸（與 IC wiring 同級誠實邊界，但 TODO 未具名）。

**碼證**: TODO:188 `reason="..."`／`reason == "..."`；無 AST Name 載荷追蹤。SPEC:360-361 寫「程式中出現之 reason 字面值」——略寬於 TODO。RECHECK：對照 TODO Task 2.4 要點 1 與 `scripts/ic_wiring_check.py` 字面掃描風格。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MINOR] 信心度=High。修法：在 Task 2.4「不可做／誠實邊界」具名「不追常量別名／f-string」；或 W3 加 `reason = "literal"` 形。不升 BLOCKING（與 IC 閘同級）。

---

## GROK-R8-P2-02

**斷言**: Task 3.4 將例外一律映射 `computation_failed` 會掩蓋 reporter／ledger 程式 bug，使 API 測試仍 2xx 綠燈；與 pure-function 層「不弱化 gate」不在同一層，但 TODO 未要求 error log／計數。

**碼證**: TODO:261「任何例外 ⇒ computation_failed」；:263「失敗不影響原流程」。SPEC:487-488 同。驗證④ 只鎖 status 字面。RECHECK：讀 TODO:257-269。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MINOR] 信心度=Medium。不與使用者「不拒絕」裁決衝突。修法：例外路徑 `logger.error(..., exc_info=True)` 必寫＋可選 metrics counter；禁在 except 內改寫三關 pure 結果。非 BLOCKING。

---


## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。

RECONCILE-STAMP: composer APPROVED 2026-08-17 sha256:f6385eb7ce27d0c9d15ee1d5c558d8160b87ae234e8b3bea5d26885bcd00ac14 task:20260817-GAP1-X-STAMP-R9
RECONCILE-STAMP: codex APPROVED 2026-08-17 sha256:f6385eb7ce27d0c9d15ee1d5c558d8160b87ae234e8b3bea5d26885bcd00ac14 task:20260817-GAP1-X-STAMP-R9

RECONCILE-STAMP: grok APPROVED 2026-08-17 sha256:f6385eb7ce27d0c9d15ee1d5c558d8160b87ae234e8b3bea5d26885bcd00ac14 task:20260817-GAP1-X-STAMP-R9
