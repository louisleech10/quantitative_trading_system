# GAP-1 B3 實作 code review（三家全員；實作者＝Claude 主委，不自審）

VERIFY-EXEMPT:doc-example:gap1-b3-review-brief-questions

> 本檔為**派給委員的提問清單**：段 A–D 是「請你查證的項目與我的待攻假設」，非主委結論；
> 結論在你們的產出與收斂檔。檔頭 `fact-verified:` 附主委實跑命令。

brief-kind: review

## 審查標的（commit `cbd9ec69`；`git show cbd9ec69 --stat`）
- 程式：`momentum/Analysis/strategy_validation/{min_btl,deflated_sharpe,report,reporter}.py`、
  `momentum/factories.py`（`create_strategy_validation_reporter`／`get_invalid_validation_argument_class`）、
  `api/routes/ml_pipeline.py`（`CreatePipelineResponse.strategy_validation`＋回應組裝處）
- 測試：`tests/momentum/Analysis/strategy_validation/test_{min_btl,deflated_sharpe,report_section}.py`、
  `tests/api/test_ml_pipeline_strategy_validation.py`
- 契約來源：TODO **FROZEN R3** Task 3.1–3.4 ＋延伸檔 **A1-1..A1-21**（衝突以延伸檔為準；重點 A1-4／5／8／9／12／13／16／17）
- 🔴 **B1／B2 之教訓帶進本輪**：前兩批我在 brief 寫的自我描述各有一條被你們實跑推翻（A1-19 靜默 730；B2 annualized 計數）。
  本批段 B 每條「我的決定」都請**優先實跑攻**，不要只核對條文。
- 🔴 **上一輪 composer 之自建多行程探針卡死 7 小時**——本輪自建探針**一律加 timeout**（`subprocess.run(..., timeout=)`／`join(timeout=)`），
  禁無界 barrier／`sleep(600)`。cx_run 已加看門狗（產出 `STATUS: DONE` 逾 5 分鐘不退即殺），請把 `STATUS: DONE` 寫在檔尾最後一行。

## 本輪任務（四段皆必答）
**段 A — 契約符合度（逐 Task）**
- 3.1：三函式簽名與 A1-5 一致？`InvalidValidationArgument` 為 `ValueError` 子類且三處驗證＋`x>700` 皆 raise 之？`EligibilityResult` 欄位 ⊆ `eligibility_keys`∪{status,reason}（無 `budget_capped`）？
  驗收①–⑨ 是否**逐字**落地（特別是⑨只在 20 seed 平均下斷言、且 `n_obs==3362`）？
- 3.2：`deflated_sharpe` 簽名？分母是否**只**取 `sr.sr_estimator_variance`（A1-12；grep 本檔不得有 `kurtosis`／`skew` 重算）？`ledger_result`／`n_trials` 互斥？
  snapshot 綁定＝集合成員測試（`in artifact_hashes`）＋`len(valid_sharpe_values)<=n_valid_metrics`？explicit None vs 非有限之兩 reason（A1-12）？驗收①–⑧ 逐字？
- 3.3：五節必填鍵與 A1-13 逐字？`WARNING_TEXT_KEY` 唯一定義處（`grep -rn "strategy_validation.downgraded"` 應只在 `report.py`）？
  A1-4 `universe_scope=="ledger_recorded_only"` 強制降級？`n_source=="assumed_not_ledgered"` ⇒ `eligible=None`？dsr/pbo=None ⇒ `not_computed`/`n_unknown`？
  🔴 A1-17：`build_validation_section` 是否**在自身函式頂層以字面鍵**組裝（`out = {...}` 五節＋eligibility 九鍵）——請用 `ast` 實查 Return/Assign 之 Constant 鍵集合。
- 3.4：入口語意二分（None＝未提供 ⇒ 不呼叫 `read_trial_ledger`／`assess_eligibility`；`<=0` ⇒ `InvalidValidationArgument` 上拋）？
  捕獲集合恰為 `(OSError, json.JSONDecodeError, ContractViolation)`？route 只投影三鍵？`grep -r "from api\." momentum/`==0？既有 `test_phase6_end_to_end.py`／`test_frontend_integration.py` 斷言未動？

**段 B — 🔴 攻我的實作決定（本輪重點）**
1. **`n_source` 之值**：契約對 `n_source` 只給 `str`（無 `*_values` 枚舉）。我用 `"ledger"`（帳本 ok）／`"ledger_unavailable"`（帳本非 ok）／`"assumed_not_ledgered"`（reporter None 路徑，TODO 明寫）。
   前兩個是我**自創字面**——這是否違反「禁自創字面」精神？應否走延伸檔把 `n_source_values` 加進契約（然後 loader 之機械枚舉對映會自動涵蓋）？
2. **`assess_eligibility` 於帳本非 ok 時仍計算 `trials_budget`**（只依 T／SR）並可能因 `x>700` raise。合理，還是 N 不可知時應全部 None？
3. **DSR 檢查順序**：ledger status → period_returns status → snapshot → compute_sharpe 退化 → SR0。ledger 非 ok 時 `n_trials_used=None`、status／reason 傳遞（`n_unknown`）。
   `_fail` 之 status 選值：`cross_trial_variance_unavailable`／`ledger_snapshot_mismatch` ⇒ `"unavailable"`；`degenerate_returns` ⇒ `"not_computed"`。請攻這些 status 選值是否與 IC 契約 `capability_status` 語意一致。
4. **驗收①之「skew=0、kurt=3」**：我用**繞均值對稱序列**使樣本 skew 恰 0，kurt 取**樣本值**（非恰 3），PSR 解析值在測試側以 scipy 矩**獨立重算**（不引用 sharpe.py 之變異數）。
   這是否忠於 TODO 字面「skew=0、kurt=3 ⇒ 等於 PSR 解析值」？若你認為必須恰 kurt=3，請給可構造之序列或改法。
5. **`report.py` 頂層鍵**：我把 `display_downgrade`／`warning_text_key` 同時放在頂層與 `eligibility` 節（route 讀 `section["display_downgrade"]`）。
   頂層鍵集合 `{五節名}∪{display_downgrade,warning_text_key}` ⊆ allowlist（`report_sections` 節名 ∪ `eligibility_keys`）成立——但這是我對 allowlist 的解讀，請判定是否為 TODO 原意。
6. **`_finite_or_none` helper**：值層用 helper 把 NaN 轉 None（契約 `float|null`、JSON 不得含 NaN）；鍵仍是頂層字面。這是否碰到 A1-17 之「禁 helper 組裝」？
7. **route 之 5xx 路徑**：`InvalidValidationArgument` 經 `factories.get_invalid_validation_argument_class()` 取得（R3 守衛當場擋掉直接 import），
   在 route 內 `except InvalidValidationArgument ⇒ HTTPException(500)`；該 HTTPException 會再被外層 `except Exception ⇒ 500` 重包（訊息變 `Internal error: ...`）——仍 5xx，但請判定是否可接受／是否應調整 except 順序。
   另：**裸 `ValueError`（非 InvalidValidationArgument）從 reporter 冒出會被既有 `except ValueError ⇒ 400`**——TODO 只要求 TypeError／IVA 為 5xx；這個 400 是否為洞？
8. **24 案例矩陣之 min_btl 非 ok 構造**：`EligibilityResult(eligible=True, status="unavailable")` 這種狀態 `assess_eligibility` 不會產生（人造）。矩陣仍 24 例、只有 1 例不降級。這是可接受的邊界測試，還是應改為只用真實可達狀態？
9. **reporter 之 provenance**：None 路徑給 `{"status":"unavailable","reason":"n_unknown"}`；帳本路徑給 `{"status": ledger.status, "reason": ledger.reason, "n_semantics": ledger.n_semantics}`（其餘 None）。TODO 對 provenance 內容未細寫——請攻是否合理。

**段 C — 測試品質（禁廉價綠燈）**
- 探針 **17 條**（`bash scripts/gap1_b1_mutation_probe.sh`；🔴 有互斥鎖，**只由 codex 跑**，另兩家讀 receipt
  `handoffs/run_receipts/20260818T090000Z-gap1-b3-mutation.log`）：§V-1／2／3／11／12 之 mutant 設計是否真的對應 TODO 字面（例：§V-11「分母改用跨 trial 變異數」我寫成 ledger 有 ≥2 值時才用）？有無 mutant 是「語法上改了但語意等價」之假紅？
- `test_deflated_sharpe.py` 之 `_ledger` fixture 設 `n_evaluated=max(n_valid, n_for_dsr)`——不變式 `n_evaluated==n_valid_metrics+n_failed_or_pruned` 在 fixture 內**不成立**（fixture 為 typed 直構，未經 read 路徑）。這會不會使某些斷言建立在不可能的帳本狀態上？
- API 測試以 `_FakeMLPipelineConfig` monkeypatch route 之 `MLPipelineConfig` 與 `PIPELINE_STORAGE_PATH`——是否有測到真實 route 路徑（TestClient 走 `api.main.app`）？⑧ 之 5xx 是否確為 `InvalidValidationArgument` 觸發而非其他錯誤（請看 log）？

**段 D — 數值／契約正確性**
- 3.1 手算值：`(100,1.0)=9.210340371976184`；`T=2.3232876712328765`：SR 1.5→13、1.0→3、2.0→104、2.5→1422（floor）——請自行重算。
- 3.2：`E[maxSR]/√V` 三點 1.5746／2.5306／3.2551 是否為 `(1-γ)Φ⁻¹(1-1/N)+γΦ⁻¹(1-1/(Ne))` 之值（請重算）；單位不變性 ⑦ 三值 `atol 1e-12`；`N=1` PSR 等式。
- 3.3：`_finite_or_none` 對 `int` 欄（`trials_budget` 等）**不**套用（保持 int）——`validate_against_contract` 之 `int` 型別是否仍過？

## 範本
`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` V13 之 §0／§1／§3 與 canonical 四欄。
ID＝`## <FAMILY>-R16-P<0-3>-<NN>`，**本輪輪次=R16**。零 findings 用 sentinel `## <FAMILY>-R16-P3-00`。

## ⚠️ 前置說明
- **禁改碼／SPEC／TODO／延伸檔；禁 commit／push**；只產你自己的 review 檔。
- 可自由跑測試；跑完貼 rc。**探針有鎖，只由 codex 跑；探針執行期間 baseline 檔會被就地 mutate**——若你跑測試時剛好看到
  `strategy_validation` 有紅，先看 `.claude/gate/gap1_mutation_probe.lock` 是否存在（有＝codex 正在跑），等鎖消失再重跑，勿列為 finding。
- 既有紅 2 條（`test_model_hyperparam_enhanced`）與本 epic 無關，勿列為 finding。
- 🔴 主委本輪**不動工作區**。若你發現工作區變動，請具名回報。`scripts/governance_families.json` 有既有 no-op dirty，非本輪。

## 本 brief 前提（逐條標）
fact-verified: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` → **220 passed**
fact-verified: `bash scripts/gap1_b1_mutation_probe.sh` → rc=0、17 條皆 rc=1、baseline／post-restore 219 passed（receipt 見段 C）
fact-verified: `venv/bin/python -m pytest tests/test_phase6_end_to_end.py tests/test_frontend_integration.py -q` → 9 passed（斷言未動）
fact-verified: `python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` → BASELINE OK；`grep -r "from api\." momentum/` → 0
assumed: `n_source` 自創兩字面可接受（無枚舉即無違反）← 請攻
assumed: 對稱序列＋樣本 kurt 忠於「skew=0、kurt=3 ⇒ PSR」字面 ← 請攻
assumed: 頂層 `display_downgrade`／`warning_text_key` 屬 allowlist 原意 ← 請攻
assumed: route 之 `except IVA ⇒ HTTPException(500)` 再被外層重包仍符「既有 500 路徑」← 請攻

## Time-box
優先序＝段 B（我的決定）＞ 段 D（數值）＞ 段 C（測試品質）＞ 段 A（條文符合）。
**不受理**：使用者裁決、已 Frozen 之 TODO 契約本身（要改請走延伸檔提案並說明為何非改不可）、B4 尚未實作之部分（PBO／CSCV／wiring 閘）、前端、治理機制。

## 產出
Verdict（可進 B4／需修補後進 B4／有根本缺陷需重作）＋段 A–D 結論＋canonical findings。檔尾最後一行 `STATUS: DONE`。收尾清 /tmp workdir（保留 claude-501）。
