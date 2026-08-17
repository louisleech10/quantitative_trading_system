# GAP-1 TODO adversarial R8 — COMPOSER

**task-id**: `20260817-GAP1-X-REVIEW-R8` | **family**: composer | **brief**: `handoffs/20260817-gap1-todoadv-r8-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_TODO.md` @ sha256 前 12＝`0acea23cd9c5`（DRAFT）；對照 `docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ `502c93cae402`
**上一輪收斂**：`handoffs/reconcile/20260817-gap1-x-review-r7/synth.md`（R7 `candidate_ids` 欄位修補）

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → `TEMPLATE PASS` rc=0
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_TODO.md docs/GAP1_STRATEGY_OVERFIT_SPEC.md docs/IC_QUANT_GAP_REGISTRY.md` → 前 12 如上
- `test -f scripts/plain_docs_sync_check.sh && bash -n scripts/plain_docs_sync_check.sh` → rc=0（Task 2.4 治理連動腳本存在且語法 OK）
- `grep -r "from api\." momentum/` → 0 行（R1 現況）
- `rg -n "CreatePipelineResponse|strategy_validation" tests/` → 無對回應 schema 之硬斷言（integration 只查 `pipeline_id`／`pipeline_summary`）

---

## Verdict：需修補後派工

R8 三項收回之核心（2.4 封閉集合、4.3 守衛、§N 殘留）整體可機械落地；**Task 3.4** 存在兩處會讓執行端在 G1-R1 落地後仍無法產出契約意圖之 eligibility，且 API 回應形狀與 SPEC 漂移——修補 TODO（不必重作 SPEC）後可派工。其餘 13 Task 深度足、批次拓撲正確。

---

## 段 B — R8 delta 三項逐項 Verdict

| 項 | Verdict | 摘要 |
|---|---|---|
| **B1 Task 2.4 wiring 閘** | **可派工（附 P2 修補）** | W1–W4 可由 Task 2.1 契約 JSON 機械導出；rc 0/1/2 語意完備；兩條 mutation 可證偽。`plain_docs_sync_check.sh` 存在（`bash -n` rc=0），治理連動屬實。TODO 將 W1 降級為 `re.search(rf'["\']{name}["\']')` 字面掃描，與 SPEC:358「AST／字面掃描」不一致，且註解／字串常量可假綠——見 **COMPOSER-R8-P2-01**。 |
| **B2 Task 3.4 ml_pipeline** | **需修補** | 解耦 R3（factory）／R1／R7 設計成立；`dataset_key=f"trial:{n}"` 與 Task 2.2 路徑公式自洽；今日 `n_unknown`→恆降級屬 **[A-裁決-降級] 明知取捨**（非缺陷）。但 `for_study_trial` 未指定 `target_sharpe`／`t_years`／`provenance` 來源，且回應未依 SPEC 限三鍵——見 **COMPOSER-R8-P1-01**、**P1-02**。`CreatePipelineResponse` 加 optional 欄位不會破壞既有測試（未驗 exact schema）。`computation_failed` 吞例外為使用者裁決之非硬擋路徑，**MINOR** 備註：可能掩蓋 reporter 邏輯 bug，但不違「不弱化 gate」（統計 gate 在 momentum 層 typed reason）。 |
| **B3 Task 4.3 UniverseProvenance** | **可派工** | 五欄位與 SPEC:583–585 逐字一致；三項驗證（集合相等／count 三方／canonical hash）＋⑤b/⑤b2 反例可執行，top-K 污染不可繞過。`full_grid`／`external_declared` 永遠 `universe_provenance_unverifiable` 為 **明知取捨**（純統計層無外部 SoT）；PBO 在 G1-R1+G1-R2 落地前無 `ok` 路徑屬預期，非 TODO 缺陷。 |

---

## 段 C — §N 八項殘留逐條（對 registry G1-R1..R8）

| §N 項 | Registry | 為何現在不做 | 判定 |
|---|---|---|---|
| 1 Optuna／ledger 生產者 | G1-R1 | `blocked-by:momentum/Optimization` 不完整 | **成立** — 成熟度地圖屬實；Task 2.3 conformance 已鎖未來義務 |
| 2 optimization_output_service 矩陣 | G1-R2 | `blocked-by:results/optimization_results/` 不存在 | **成立** — §A FACT-RECEIPT 已驗目錄缺席 |
| 3 前端降級面板 | G1-R3 | `blocked-by:G1-R1/R2` 無後端資料 | **成立** — Task 3.4 已送 API 欄位，觸發條件可判定 |
| 4 C1 六條 N 繞過 | G1-R4 | `blocked-by:G1-R1` 生產者未接線 | **成立** — 契約層 fail-closed 已做，機器阻止需生產者 |
| 5 API 硬擋 promote | G1-R5 | `user-ruling:2026-08-17 降級展示` | **成立** — brief 不受理範圍；Task 3.4 已落警語 |
| 6 adaptive effective-N | G1-R6 | `needs-research:無公認可驗方法` | **成立** — Task 3.2 ⑧ 誠實標 `unverified` |
| 7 MinBTL 近似誤差 | G1-R7 | `needs-research:Monte Carlo 另票` | **成立** — `upper_bound` 語意已鎖 |
| 8 prediction_analyzer cumsum | G1-R8 | `blocked-by:不在策略路徑` | **成立** — Task 1.4 已禁消費該路徑 |

八項與 registry 一一對應；無「其實現在就能做」之殘留應收回為 Task。

---

## 段 A — §1 必查 11 類（摘要）

| 類 | 結果 |
|---|---|
| 1 矛盾/互斥 | **有** — Task 3.4 回應形狀 vs SPEC:474-476（見 P1-02）；Task 3.1 `assess_eligibility` 簽名 TODO 用 `ledger_result`、SPEC:380 仍寫 `n_trials`（TODO 為 R7 後正確版，追溯表未標 intentional delta） |
| 2 漏項/端到端 | Task 3.4 reporter 輸入鏈不完整（P1-01）；其餘 14 Task 端到端閉合 |
| 3 不可測驗收 | 各 Task 驗證欄含 rc/atol/字面斷言；§V 13 mutation 有對應 |
| 4–11 | 無額外 BLOCKING（quant/OOM/cache/API 測試/agent 可執行性除 3.4 外足夠；§B 批次 B4⊥B3 正確；無短命白工） |
| §2 锚点/猎空壳 | §0/§B/§N 追溯齊；Task 3.1 `available_years` 計算未寫入實作要點（併入 P1-01 類 agent 風險） |
| §0 挑戰前提 | brief `assumed: TODO 15 Task 抄寫無漂移` → **不成立**（至少 3.4 兩處）；`assumed: R8 delta 不引入解耦違規` → **成立** |

---

## Findings

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

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 |
|---|---|
| brief `assumed: TODO 抄寫無語意漂移` | **不成立**（Task 3.4 回應子集、Task 3.1 簽名 vs SPEC 等） |
| brief `assumed: R8 delta 不引入解耦/測試破壞` | **成立**（factory 路徑合 R3；optional Pydantic 欄位安全） |
| brief `assumed: §N 八項殘留理由全成立` | **成立**（§C 表逐條核對 registry） |
| TODO「執行端讀完即可寫碼不需回讀 SPEC」 | **Task 3.4 不成立**（需 SPEC 或 TODO 修補後才成立） |

---

ASSUMPTIONS_VERIFIED: template_check TODO PASS；sha256 前三檔；plain_docs_sync_check.sh 存在+bash -n；grep api import=0；tests 無 CreatePipelineResponse 硬斷言
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → PASS rc=0；`bash -n scripts/plain_docs_sync_check.sh` → rc=0；`grep -r "from api\." momentum/` → 0；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-todoadv-r8-composer.md --family composer` → `COMPLETENESS PASS(single)` rc=0（3 canonical ID）
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 TODO/SPEC）；finding 指出 Task 3.4 若照現 TODO 實作會擴 API schema
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-todoadv-r8-composer.md`
TMP_CLEANUP: `/tmp/workdir` 不存在；`/tmp/claude-501` 保留
STATUS: DONE
