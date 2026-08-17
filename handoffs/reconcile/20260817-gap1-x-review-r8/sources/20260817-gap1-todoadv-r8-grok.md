# GAP-1 TODO（DRAFT）adversarial 審查 R8 — GROK

**task-id**: `20260817-GAP1-X-REVIEW-R8` | **family**: grok | **brief**: `handoffs/20260817-gap1-todoadv-r8-BRIEF.md`
**審查標的**：
- TODO DRAFT：`docs/GAP1_STRATEGY_OVERFIT_TODO.md` @ sha256 前 12＝`0acea23cd9c5`
- SPEC R8：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ sha256 前 12＝`502c93cae402`
- Registry：`docs/IC_QUANT_GAP_REGISTRY.md`「GAP-1 待補完」@ sha256 前 12＝`d226fa453504`
- 前一輪收斂：`handoffs/reconcile/20260817-gap1-x-review-r7/synth.md`（戳記待補；本輪依 brief 不停工）

**本輪 finding 輪次**：R8（session＝`review-r8`）
**禁改碼／禁改 SPEC／TODO／禁蓋戳記**；只產本檔。

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → `TEMPLATE PASS (todo)` rc=0
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_{SPEC,TODO}.md docs/IC_QUANT_GAP_REGISTRY.md` → `502c93cae402`／`0acea23cd9c5`／`d226fa453504`
- 既有符號存在：`TIMEFRAME_SECONDS`（constants.py:6）、`load_report_contract`／`contract_enum`（ic_config_schema.py:524,539）、`MomentumConfig.results_path`（config.py:326）、`PerformanceMetrics(..., periods_per_year=730)`（performance_metrics.py:20）、`strategy_backtest.py:113` 現況無 periods 傳遞、`CreatePipelineResponse`（ml_pipeline.py:100）無 `strategy_validation` 欄
- `test -f scripts/plain_docs_sync_check.sh` → 存在；`scripts/` 在 `第*批-*.md`／`README.md`／`治理進度日誌.md`／`流程摩擦記錄.md`／`接下來要做什麼.md` 之 WATCHED 內
- `test -d results/optimization_results` → 不存在（G1-R2 依賴成立）
- `prediction_analyzer.py:155` `np.cumsum` 仍在場
- `scripts/strategy_wiring_check.*` → 尚不存在（新 Task，非缺陷）

---

## Verdict：需修補後派工

純統計 Task（1.x／2.1–2.3／3.1–3.3／4.x 核心）深度與可執行性大致達標，R8 三項收回之**欄位字面**與**降級不硬擋**語意大體可實作。  
但 **§B 批次閘把 Task 2.4 wiring 放在 B2／B3 出口，與 W1（需 Task 3.3 `report.py`）＋W2（需 B4 之 PBO reason 字面）不可同時成立**——執行端依 TODO 做完 B2 必在 gate 紅燈，屬 **BLOCKING 拓撲**。  
另有數項 MAJOR（`assess_eligibility` 簽名漂移、Task 3.4 dataset_key／`t_years` 結構性永降級、G1-R3／G1-R7 之「為何現在不做」分類不成立）。  
**不**判「有根本缺陷需重作」：修 §B 閘／Task 2.4 落點＋對齊 3.1 簽名／改殘留理由即可 Frozen。

**BLOCKING 清單**：`GROK-R8-P0-01`（1 條）。  
**MAJOR 清單**：`GROK-R8-P1-01`～`04`（4 條）。  
**MINOR**：`GROK-R8-P2-01`～`02`（2 條）。

---

## 段 B — SPEC R8 三項收回 delta 逐項 Verdict

| # | 項 | Verdict | 摘要 |
|---|---|---|---|
| B1 | Task 2.4 wiring 閘門 | **FAIL（BLOCKING 落點）** | W1–W4 封閉集合**可**機械導出；rc 0/1/2 語意完備；mutation 兩條可證偽；`plain_docs_sync_check.sh` **存在且**會因 `scripts/` 變動擋未同步白話檔。但 TODO 把 2.4 放 B2、且 B2→B3／B3 收尾 gate 要求 wiring rc=0，與 W1 依賴 3.3、`W2` 依賴 4.x reason 字面**互斥**（見 P0-01）。字面 `re.search(rf'["\']{name}["\']')` 對受控 section 名不易子串誤判；W3 只掃兩種賦值形 → 誠實邊界（P2-01）。 |
| B2 | Task 3.4 ml_pipeline 附警語 | **CONDITIONAL-OK（MAJOR 設計洞）** | `create_strategy_validation_reporter()` 懶 import＋route 經 factory ⇒ **符合 R3／R1／R7**（回 dict，不進 `api/models`）。`dataset_key=f"trial:{trial_number}"` 在今日無生產者下必 `n_unknown`＝**[A-裁決-降級] 明知取捨**；但鍵粒度＝per-trial，與 DSR「session 級 N」語意衝突，且 `for_study_trial` **無 `t_years`** ⇒ 即使未來有 ledger 仍結構性 `eligible=None`（P1-02）。`CreatePipelineResponse` 加 optional 預設 `None` 對現有 live 整合測試**低破壞風險**（只讀 `pipeline_id`／`pipeline_summary`）。例外吞為 `computation_failed`＝展示路徑 best-effort，**不**等同弱化三關 pure-function gate；與「附加不打斷主流程」一致（MINOR 備註即可）。 |
| B3 | Task 4.3 UniverseProvenance | **PASS** | 五欄位與 SPEC:583–586 **逐字一致**；`check_universe_provenance` 三項（集合相等／count 三方／canonical hash）＋⑤b／⑤b2 反例寫死。**無**可執行 top-K 繞過（自洽 subset hash 被集合相等擋；同 count 換 1 id 被集合擋）。`full_grid`／`external_declared` 一律 unverifiable ⇒ **生產路徑在 G1-R1 落地前 PBO 無 `ok`**，但測試可用 `ledger_all_candidates` fixture 走 ⑤c；屬 [A-裁決] 嚴守衛，**非缺陷**。 |

---

## 段 C — §N 殘留八項「為何現在不做」逐條

| # | §N 項 | registry | 三值 | 理由是否成立 | 本輪 |
|---|---|---|---|---|---|
| C1 | Optuna／搜尋器寫 ledger | G1-R1 | `blocked-by: Optimization 不完整層` | **成立**——白名單禁接；成熟度地圖＋接上即重寫作廢 | 成立：依賴真存在 |
| C2 | optimization_output 矩陣 | G1-R2 | `blocked-by: 服務從未執行` | **成立**——`results/optimization_results/` 不存在（本輪實查） | 成立 |
| C3 | 前端降級面板＋文案 | G1-R3 | `blocked-by: G1-R1／R2` | **不成立**——Task 3.4 已把 `strategy_validation`（含 `display_downgrade`／`warning_text_key`）送到 API；registry 驗收錨點亦寫「Task 3.4 已送到」。至少警語橫幅**現在就能做**。應改 `user-ruling: 本票範圍不含 frontend`（成熟度地圖），非 blocked-by 資料 | **MAJOR P1-03** |
| C4 | C1 六條 N 繞過機器阻止 | G1-R4 | `blocked-by: G1-R1` | **成立**——無生產者則機器無寫入面可拦；契約層 `n_unknown`／`n_is_lower_bound` 已 fail-closed | 成立 |
| C5 | API 硬擋 promote | G1-R5 | `user-ruling: 降級不硬擋` | **成立**（裁決本身 brief 不受理重審）；Task 3.4 已落警語 | 成立 |
| C6 | adaptive 有效獨立 N | G1-R6 | `needs-research` | **成立**——無公認可驗折算；`n_independence=unverified` 誠實 | 成立 |
| C7 | MinBTL 上界近似誤差量化 | G1-R7 | `needs-research` | **不成立**——誤差帶可用標準 Monte Carlo 工程量化，非「無公認方法」；觸發列「排程即可做」已自打臉。應改 deferred-scope／另票，或收回小 Task（**不**要求本票做精確 MinBTL——brief 不受理精確值） | **MAJOR P1-04** |
| C8 | prediction_analyzer cumsum | G1-R8 | `blocked-by: 不在策略路徑` | **成立**——`prediction_analyzer.py:155`；Task 1.4 禁消費 | 成立 |

Registry G1-R1..R8 **對得上** §N 8 項（含觸發條件欄）。

---

## Findings（canonical）

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

## §0 被當成事實的未驗證假設

| 來源 | 宣稱 | 本輪判定 |
|---|---|---|
| brief fact | `template_check todo` PASS | **成立**（本輪重跑 PASS） |
| brief fact | 既有符號存在 | **成立**（見 VERIFY） |
| brief fact | r7 synth body sha `ad4c5c535461…`、戳記待補 | **未重算 body sha**（accepted as assumed）；依 brief 不停工 |
| brief assumed | TODO 15 Task 對 SPEC 抄寫無語意漂移 | **不成立**——至少 `assess_eligibility` 簽名／`budget_capped`（P1-01）；追溯表只證「有對應」 |
| brief assumed | R8 三項收回不引入解耦違規或測破 | **解耦 OK**；測破風險低；**拓撲／dataset_key 引入可執行性／語意洞**（P0-01、P1-02） |
| brief assumed | §N 8 項為何現在不做全成立 | **不成立**——C3／C7（P1-03、P1-04）；其餘 6 項成立 |
| TODO 自述 | 四份治理白話檔會被 `plain_docs_sync_check` 擋 | **機制成立**（WATCHED 含 `scripts/` 之受管檔 >4；新增 `scripts/*` 會觸發時序檢查） |

---

## §1 十一類速查（無則標無）

| # | 類 | 結論 |
|---|---|---|
| 1 | 矛盾／互斥 | **有** P0-01（批次閘 vs 2.4 依賴）；P1-01（SPEC/TODO 3.1 簽名） |
| 2 | 漏項／E2E | 前端／生產者在 §N；3.4 為唯一 API——OK。G1-R3 理由過時 |
| 3 | 不可測驗收 | 多數 Task 有 atol／rc／字面；2.4 mutation 可測 |
| 4 | 可疑 quant | 4.3 守衛嚴；3.4 per-trial N 鍵可疑（P1-02）；其餘 per-period／MinBTL 上界 OK |
| 5 | 過度工程 | 無 |
| 6 | OOM／並行 | 4.1 雙重預算 OK；2.3 並發 append 有測 |
| 7 | Cache | 無跨 symbol cache 設計；ledger 路徑 per session+key |
| 8 | API／相容 | optional 欄低風險；例外吞 MINOR |
| 9 | 測試品質 | mutation 13 條掛接完整；wiring 落點錯導致 gate 假不可達 |
| 10 | Agent 可執行 | B1–B4 純核心可寫；**B2 含 2.4 依文執行必卡 gate** |
| 11 | 必要性／短命 | 無短命工；1.3／3.4 覆蓋風險已標 |

---

## 段 A 補充（優先序較低；非另開 ID）

- Task 1–4 偽碼／檔案／邊界／驗證整體達「讀完可寫碼」；空殼機械掃描未見「只有表頭」。
- `LedgerReadResult` 在 2.2／3.1／3.2／4.3 欄位引用一致（含 `candidate_ids`／`n_for_dsr`／`artifact_hashes`）。
- §B 拓撲 B3∥B4 不互相依賴——正確；唯 2.4 插入破壞閘。
- Task 3.3 偽碼 `all(s.status=="ok" for s in (min_btl,dsr,pbo))` 中 `min_btl` 非函式參數——執行端可推，建議改「五節 status」以免歧義（未另開 finding，附於此）。

---

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF、R8 brief、V13 範本、TODO DRAFT、SPEC R8 §N:660-694、registry GAP-1 表、r7 grok 格式；template_check todo PASS；三檔 sha 前 12；既有符號與 ml_pipeline 回應模型；plain_docs_sync WATCHED；optimization_results 缺席；cumsum 行號；reasons→batch 映射。
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → PASS rc=0；`shasum -a 256` 三檔＋scripts/api；`test -d results/optimization_results` → 不存在；靜態 grep/讀檔如上（無 pytest 產品套件——本輪禁改碼只審文件）。
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀審查；僅新增本產出檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC／TODO／碼）；結論影響＝TODO Frozen 前須修 P0-01 等
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-todoadv-r8-grok.md`
HANDOFF_NOT_UPDATED: 根 `HANDOFF.md` 由 Claude 維護；本輪 brief 指定產出路徑為本檔
STATUS: DONE
