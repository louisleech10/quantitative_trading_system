# GAP-1 TODO DRAFT adversarial R8 — Claude 主委獨立版（非鎖來源）

> 標的：`docs/GAP1_STRATEGY_OVERFIT_TODO.md`（sha256 `0acea23cd9c5`）＋ SPEC R8（`502c93cae402`）。
> 方法：逐 Task 對照 SPEC 抄寫漂移；對 §G 數值 golden **實跑探針**（`handoffs/run_receipts/20260817T143000Z-gap1-todoadv-claude-pbo-probe.{py,log}`）。
> 本檔為主委自產版，供 reconcile 與三家互審；主委不自審自己的 TODO ⇒ 本檔只列反證，不作 Verdict 之唯一依據。

## Verdict：需修補後派工（P0 三條皆為 §G／§V 數值級：golden 如寫即紅或不可證偽）

## CLAUDE-R8-P0-01

**斷言**: §G／Task 4.2 驗證② 之 alpha oracle 為假等式——`mu = 0.01*1.0/sqrt(8760)`（per-period SR≈0.0107）下 PBO **≈0.54–0.62**，非 `< 0.30`。

**碼證**: SPEC §G 第 3 類「alpha 案例…⇒ PBO < 0.30」；TODO Task 4.2 驗證②。RECHECK：`venv/bin/python handoffs/run_receipts/20260817T143000Z-gap1-todoadv-claude-pbo-probe.py` → `alpha(mu=1.0684e-4) pbo=0.5411 / 0.6201 / 0.5487`（三種 RNG 變體）。原因：IS／OOS 各 600 obs，SR 標準誤 ≈ 1/√600 ≈ 0.041 ≫ 0.0107，alpha 候選在 924 path 中不穩定當冠軍。掃描：per-period SR 0.05→0.39、0.10→0.11／0.016、0.15→0.005／0.000。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[BLOCKING] 信心度=High（實跑）。會怎麼失敗：Task 4.2 驗證② 永紅 ⇒ 實作者被逼「調到綠」（違禁取巧）。修法：alpha 改以 **per-period SR** 定義（與 [A-單位] 一致）：`mu = sigma_per_period * 0.15`（provenance：alpha＝3.7 個 IS 標準誤），斷言 `pbo < 0.30`（實測 0.0054／0.0000）；SPEC §G 走延伸檔修訂，`1.068434607926721e-04` 之推導式刪除或降為「年化 SR 1.0 於 T=1200 不可偵測」之**反例**（可加為第三個 golden：`pbo > 0.40`，證明 PBO 不會把弱 alpha 誤判為穩健）。

## CLAUDE-R8-P0-02

**斷言**: §G 全噪音 band `[0.40,0.60]` 在 seed=20260817 下**依 RNG API 與抽樣順序而異**，且三種合理實作有兩種落在 band 外 ⇒ golden 不可重現。

**碼證**: 同一探針：`np.random.default_rng(20260817).normal(0,0.01,(1200,50))` → 0.6483；`(50,1200).T` → 0.6158；`np.random.seed(20260817)` legacy → 0.5357。SPEC §G／TODO 4.2 只寫「seed=20260817…i.i.d. 常態 σ=0.01」，未寫 RNG API／形狀順序／dtype。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[BLOCKING] 信心度=High（實跑）。會怎麼失敗：實作者選 `default_rng`（現代慣例）⇒ 驗證① 紅；換 legacy 才綠＝靠試錯選 RNG＝取巧。修法：golden 檔與 TODO 4.2 **逐字寫死** `rng = np.random.default_rng(20260817); M = rng.standard_normal((n_obs, n_candidates)) * 0.01`；band 依 CSCV path 高度相關（924 path 有效獨立數遠小於 924）之事實放寬為 `[0.30, 0.70]` 並附理由；或改為 5 個 seed 之平均 ∈ `[0.40,0.60]`（成本 ×5，我不建議）。同時把探針三值寫入 golden `provenance`。

## CLAUDE-R8-P0-03

**斷言**: §V mutation 4「CSCV 之 IS/OOS 對調 ⇒ Task 4.2 斷言①② 至少一條轉紅」**不可證偽**：`combinations(range(S), S//2)` 之補集仍在枚舉內，對調只改 path 順序、PBO 值逐位相同。

**碼證**: 探針 `swap=True` 分支：三組矩陣 `swapped` 皆與原值相等（0.6483／0.6158／0.5357）。SPEC §V-4；TODO Task 4.2「mutation §V-4 轉紅」。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[BLOCKING] 信心度=High（數學＋實跑）。會怎麼失敗：B4 Gate「13 條 mutation 全部貼 rc」中此條永遠貼不出轉紅 rc ⇒ 要嘛造假 receipt 要嘛 gate 卡死。修法：§V-4 改為可證偽者，二選一：(a) champion 改由 **OOS** metric 選（IS 選法失效）⇒ PBO 趨近 0，alpha 案例／噪音 band 轉紅；(b) `r` 改 `1-r`（ω 符號反轉）⇒ 噪音 band 可能仍綠但 alpha 案例（修 P0-01 後）轉紅。建議 (a)。

## CLAUDE-R8-P1-01

**斷言**: Task 2.4 wiring 閘於 B2→B3 gate 要求 `rc=0` **不可能成立**：`report.py` 於 B3 Task 3.3 才存在（⇒ rc=2），且 W2 要求契約 `reasons` 每值被 `strategy_validation/*.py` 引用，而 `insufficient_candidates`／`all_paths_degenerate`／`universe_*`／`cross_trial_variance_unavailable`／`ledger_snapshot_mismatch` 六值於 B3／B4 才出現（⇒ rc=1）；B3 Gate 亦要求 rc=0 但 B4 之 reasons 仍未引用。

**碼證**: TODO §B「B2→B3／B4：…`bash scripts/strategy_wiring_check.sh` rc=0」；Task 2.4 實作要點 W1／W2；Phase B3 Gate「`bash scripts/strategy_wiring_check.sh` rc=0」；B4 與 B3 互不依賴（§B 表）。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 信心度=High。修法：Task 2.4 移為**最後一個 Task**（B4 末，且明定 B4 於 B3 完工後執行；§R 之「B3／B4 可獨立 revert」對統計核心仍成立，wiring 腳本 revert 為零成本）；B2／B3 gate 刪除 rc=0 要求；只在 B4 收尾 gate 要求 rc=0。或保留於 B2 但 W1／W4 在 `report.py` 缺失時**明示 SKIP**（不建議：把 rc=2 語意弄髒）。

## CLAUDE-R8-P1-02

**斷言**: Task 3.4 之 `for_study_trial(study_name, trial_number)` 依 TODO 步驟必呼叫 `assess_eligibility`，但 route 只有 `study_name`／`trial_number`（無 `t_years`／`target_sharpe`），而 Task 3.1 對 `t_years<=0`／`target_sharpe<=0` **raise** ⇒ 每次都走 except ⇒ 回應**恆為** `computation_failed`，永遠產不出 SPEC 明言之「誠實展示 `eligible=None`＋降級」。

**碼證**: TODO 3.4 步驟 1「→ `assess_eligibility`（`t_years` 由呼叫方傳入或無 ⇒ `eligible=None`）」但簽名 `for_study_trial(study_name:str, trial_number:int)` 無此參數；TODO 3.1 步驟 1「`t_years<=0` ⇒ `ValueError`」；`api/routes/ml_pipeline.py:61-62`（request 只有 study_name／trial_number）；SPEC 3.4 驗證①「`display_downgrade is True`（今日無帳本）」預期的是 `eligible=None` 路徑。

**來源摘要**: api/routes/ml_pipeline.py#df139c6a0fae

[MAJOR] 信心度=High。修法：`for_study_trial(study_name, trial_number, *, dataset_key: str|None=None, t_years: float|None=None, target_sharpe: float|None=None)`；`dataset_key is None` ⇒ **不讀 ledger**、直接組 `EligibilityResult(eligible=None, status="unavailable", reason="n_unknown", trials_used=None, …)`；`t_years`／`target_sharpe` 任一 None ⇒ 同上（不呼叫 assess_eligibility）；只有三者齊備才走 `read_trial_ledger → assess_eligibility`。測試 ① 改斷言 `eligibility.eligible is None` 且 `status!="computation_failed"`。

## CLAUDE-R8-P1-03

**斷言**: Task 3.4 之 `dataset_key=f"trial:{trial_number}"` 語意錯：Task 2.2 之 `dataset_key` 是**資料切片鍵**（同一 study 之全部候選共用一本帳），trial 是候選；以 trial 為 dataset_key 則未來生產者落地後 reporter 仍讀不到帳本（永遠 `n_unknown`），且每 trial 一檔會使 `n_candidates_considered≡1`。

**碼證**: TODO 2.2 路徑 `f"{research_session_id}__{dataset_key}.jsonl"`、`n_candidates_considered=len(set(candidate_id))`；TODO 3.4 步驟 1。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 信心度=High。修法：同 P1-02——`dataset_key` 由呼叫方顯式提供（本票 route 無此資訊 ⇒ 傳 None ⇒ 誠實 `n_unknown`）；TODO 3.4 明寫「route 今日傳 `dataset_key=None`；registry G1-R1 落地時由 study metadata 提供」。

## CLAUDE-R8-P1-04

**斷言**: Task 3.4 之例外 fallback `{"status":"computation_failed","reason":str(exc)[:200],…}` 三處違約：① `reason` 為自創動態字串（違反「`reasons` 唯一來源；程式不得自創字面值」，且 W3 靜態掃描抓不到動態值）② 形狀（頂層 status/reason）與 `report_sections` 五節契約不符 ⇒ 成功／失敗兩種回應 schema 不同 ③ `"strategy_validation.downgraded"` 字面在 `report.py` 與 `reporter.py` 兩處定義。

**碼證**: TODO 3.4 步驟 1 末句；TODO 2.1「`reasons`…唯一 reason 字串來源；程式與測試不得自創字面值」；TODO 3.3 步驟 2 之 `warning_text_key` 字面。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 信心度=High。修法：契約 `reasons` 新增第 12 值 `reporter_failed`（`reason_conditions` 同步；SPEC 2.1 走延伸檔修訂 11→12）；fallback 由 `report.py` 提供 `build_failed_section(reason="reporter_failed")` 產出**契約合法之五節**（各節 `status="computation_failed"`）＋`display_downgrade=True`＋唯一定義之 `warning_text_key` 常數（住 `report.py`）；例外文字只進 log（`get_logger`），不進回應。

## CLAUDE-R8-P1-05

**斷言**: Task 3.1 之 `EligibilityResult.budget_capped` 與 `max_trials_budget` 之 `x>700 ⇒ 10**18` 皆為 TODO 自創：`budget_capped` 不在契約 `eligibility_keys`（9 鍵，`additional_properties:false`）⇒ Task 3.3 輸出時要嘛違約要嘛靜默丟欄；`10**18` 為無依據常數。

**碼證**: TODO 3.1 步驟 2、輸入/輸出欄位列；TODO 2.1 `eligibility_keys` 九鍵；SPEC 3.1 回傳欄位無 `budget_capped`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 信心度=High。修法：`x > 700` ⇒ `raise ValueError("trials budget overflow: t_years*target_sharpe**2 > 1400")`（fail-closed；該輸入無物理意義），刪 `budget_capped`；邊界 ⑥ `N=10**6` 屬 `min_btl_years_upper_bound` 之 `ln` 側，不受影響。

## CLAUDE-R8-P1-06

**斷言**: Task 3.2 步驟 2 自行重算分母 `den=sqrt(1-g3*SR+(g4-1)/4*SR²)`，而非取 Task 1.2 之 `sr_estimator_variance` ⇒ Mertens 變異數有**兩個定義處**；§V-10（係數改錯）只會使 Task 1.2 對照轉紅，**不會**使 Task 3.2 斷言① 轉紅——與 SPEC §V-10「⇒ Task 1.2 … 與 Task 3.2 斷言① 轉紅」不符。

**碼證**: TODO 3.2 步驟 2／5；SPEC 3.2「分母之 `Var(SR_hat)` **恆**取自 Task 1.2 之 `sr_estimator_variance`」；SPEC §V-10。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 信心度=High。修法：`stat = (SR_obs - SR0) / math.sqrt(sr.sr_estimator_variance)`；`value = norm.cdf(stat)`；刪 `den`。（等價：`(SR-SR0)*sqrt(T-1)/den` ＝ `(SR-SR0)/sqrt(Var)`。）

## CLAUDE-R8-P1-07

**斷言**: Task 3.2 `variance_source="explicit"` 且 `cross_trial_sr_variance=None` 之 reason：TODO 給 `degenerate_returns`，SPEC 給 `cross_trial_variance_unavailable`（「`n_trials>1` 且兩者皆缺」）⇒ 抄寫漂移，驗證⑥ 會依 SPEC 字面失敗。

**碼證**: TODO 3.2 步驟 3「`explicit` ⇒ `cross_trial_sr_variance`（須有限且 >0，否則 `degenerate_returns`）」；SPEC 3.2「變異數須為有限且 `>0`，否則 `reason=degenerate_returns`；…`n_trials > 1` 且兩者皆缺 ⇒ `reason=cross_trial_variance_unavailable`」。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 信心度=High。修法：`None`／缺 ⇒ `cross_trial_variance_unavailable`；有值但非有限或 `<=0` ⇒ `degenerate_returns`。兩情形各一測試。

## CLAUDE-R8-P1-08

**斷言**: `report_sections` 五節之 `required_keys` 內容在 SPEC／TODO 皆未列（只有每節 `status`／`reason` 與 provenance 四鍵）；`eligibility_keys` 九鍵住哪一節、`min_btl`／`dsr`／`pbo` 節各帶哪些欄位未定 ⇒ 執行端須自創 schema；Task 3.3 驗證④「24 案例通過 `validate_against_contract`」與 W1／W4 無明確標的。另 TODO 3.3 步驟 4 寫 `provenance.n_source`，但 `n_source` 屬 `eligibility_keys`。

**碼證**: TODO 2.1 步驟 1「`report_sections` 五節各含 `required_keys`／…」但無內容；SPEC 2.1 同；TODO 3.3 步驟 4。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 信心度=High（空殼：有欄位標籤無內容）。修法（提案，供收斂定案）：`eligibility` 節 required ＝ `eligibility_keys` 九鍵 ＋ `status`／`reason`；`min_btl` ＝ `status`／`reason`／`required_years_upper_bound`／`available_years`／`trials_budget`／`trials_used`／`target_sharpe`；`dsr` ＝ `status`／`reason`／`value`／`sr0`／`sr_obs_per_period`／`n_trials_used`／`variance_source`／`n_independence`；`pbo` ＝ `status`／`reason`／`value`／`n_paths_used`／`n_paths_skipped`／`n_candidates_invalid`；`provenance` ＝ `status`／`reason`／`n_semantics`／`t_semantics`／`annualization_source`／`n_independence`。TODO 2.1 逐字列出；3.3 第 4 點改 `eligibility.n_source`。

## CLAUDE-R8-P1-09

**斷言**: Task 3.1 驗證⑧／§V 反向測試 vacuous：`assess_eligibility` 直接吃 `t_years`，「1h/4h/12h 三 fixture」若各自傳同一 `t_years` 必相等，抓不到「bar 數當年數」；TODO 未寫三 fixture 之 `t_years` 如何由 bar 數推導。

**碼證**: TODO 3.1 簽名 `assess_eligibility(*, t_years:float, …)`、驗證⑧；SPEC §V「若實作把 bar 數當年數則轉紅」。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MAJOR] 信心度=High。修法：Task 1.1 新增 `available_years(*, n_bars: int, timeframe: str) -> float = n_bars / resolve_periods_per_year(timeframe)`（唯一推導處）；Task 1.4 `trade_level` 之 `available_years` 改呼叫之；反向測試以真實 kline 長度（§A receipt：1h=20352／4h=5088／12h=1696）三 timeframe 對照 `2.3232876712328765`（`atol=1e-6`：5088/2190=2.32329、1696/730=2.32329）；mutation「回 `n_bars`」⇒ 轉紅。

## CLAUDE-R8-P1-10

**斷言**: §N／registry 之 G1-R7、G1-R8 觸發條件寫「排程即可做」＝變相「之後再說」；G1-R8 之 `blocked-by: 不在策略路徑` 非依賴而是 scope 裁決（三值形式不合）；G1-R7 之「Monte Carlo 量化上界誤差」至少**保守性驗證**現在就能做（一個統計 oracle 測試）。

**碼證**: `docs/IC_QUANT_GAP_REGISTRY.md` G1-R7／G1-R8 列「排程即可做」；SPEC §N 末兩條。使用者規則（2026-08-17）：殘留不得是偷懶，三值必帶成立理由。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#d226fa453504

[MAJOR] 信心度=Medium（分類判斷）。修法：G1-R8 改標 `user-ruling:<待使用者>` 或直接排為 GAP-1 收尾後之 **小任務**（Claude 自做，具體日期）；G1-R7 **部分收回**為 Task 3.1 驗證⑨（統計 oracle：`N=100`、`SR=1.0` ⇒ `T=9.2103` 年之日頻 iid 噪音 100 策略、`default_rng(20260817)`、20 seeds ⇒ `mean(max annualized SR) <= 1.0`，證上界保守；秒級），「誤差帶量化」仍 needs-research。其餘六項殘留（G1-R1..R6）理由成立：R1／R2 依賴使用者成熟度地圖之事實、R3 依賴 R1／R2、R4 依賴 R1、R5 使用者裁決逐字、R6 確無公認方法。

## CLAUDE-R8-P2-01

**斷言**: 簽名層抄寫偏離未在 TODO 標示：① Task 1.4 加 `t_semantics: str` 參數（SPEC 無）② Task 3.1 `assess_eligibility` 之 `n_trials` 改 `ledger_result`（SPEC 寫 `n_trials`）③ golden 建檔時機 SPEC「Task 3.1 動工前」vs TODO「由 Task 4.2 產出」④ Task 3.3 `dsr=None`／`pbo=None` 時各節 status／reason 未定。

**碼證**: TODO 1.4／3.1／階段 3 自檢第 3 點／3.3；SPEC 1.4／3.1／§G。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#0acea23cd9c5

[MINOR] 信心度=High。①② 皆為合理收緊（呼叫方選語意；N 只能來自 ledger），但須在 TODO 該 Task 標「SPEC 偏離＋理由」；③ 統一為 Task 3.1 建檔（含 PBO 參數與 band，Task 4.2 只讀）；④ 定為 `status="not_computed"`、`reason="n_unknown"`（本票唯一觸發情境＝無帳本）。

## 段 B 三項 delta 逐項 Verdict
| 項 | Verdict | 依據 |
|---|---|---|
| Task 2.4 wiring 閘 | 需修補（P1-01 批次位置） | 規則本身可機械導出；rc 語意完備；mutation 兩條可證偽 |
| Task 3.4 ml_pipeline 警語 | 需修補（P1-02／03／04） | 恆 `computation_failed`；dataset_key 語意；fallback 違約 |
| Task 4.3 欄位逐字 | 通過 | 五欄與 SPEC:583 逐字一致；三項驗證封閉 top-K 兩反例；`full_grid` 永不 ok 為明知取捨（SPEC 已附理由） |

## 被當成事實的未驗證假設（§0）
- 「§G 統計性質 oracle 之 band 與 alpha 推導式成立」——SPEC 七輪從未實跑，實跑證偽（P0-01／02）。
- 「§V 13 條 mutation 皆可轉紅」——§V-4 數學上不可能（P0-03）。

STATUS: DONE
