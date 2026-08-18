# GAP-1 B3 實作 code review（R16）— COMPOSER

**task-id**: `20260818-GAP1-B3-REVIEW-R16` | **family**: composer | **brief**: `handoffs/20260818-gap1-b3-review-BRIEF.md`
**審查標的**: commit `cbd9ec69`（B3 Task 3.1–3.4）
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` → **220 passed** rc=0
- mutation receipt（唯讀）`handoffs/run_receipts/20260818T090000Z-gap1-b3-mutation.log` → baseline/post-restore rc=0、17 條 mutant rc=1
- `venv/bin/python -m pytest tests/test_phase6_end_to_end.py tests/test_frontend_integration.py -q` → **9 passed** rc=0（`git diff cbd9ec69^..cbd9ec69` 對兩檔 0 行）
- `python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` → BASELINE OK；`grep -r "from api\." momentum/` → 0
- 數值重算（probe）：`ub(100,1.0)=9.210340371976184`；`budget(T,1.5/1.0/2.0/2.5)=13/3/104/1422`；`E[maxSR]` 三點 1.574598／2.530603／3.255122（atol<1e-4）
- A1-17 AST：`build_validation_section` 頂層 `out={...}` 含五節＋`display_downgrade`／`warning_text_key`；`eligibility` 九鍵＋`status`／`reason` 共 11 字面鍵
- route 探針：IVA `t_years=-1` → HTTP **500**，detail=`Internal error: 500: strategy_validation reporter argument error`（外層 `except Exception` 重包）；裸 `ValueError` → HTTP **400**

**工作區備註**：主委宣稱不動工作區；`git status` 見 `.claude/gate/audit.log`、`scripts/governance_families.json` 等與 B3 標的無關 dirty；本委員新增之 `scripts/_composer_b3_*_probe.py` 為審查探針，收尾刪除。

---

## Verdict：需修補後進 B4

段 A 契約條文與段 D 數值**達標**；段 B 兩項 route 例外語意（`ValueError→400`、`HTTPException` 外層重包）與 A1-16「接線 bug 須 5xx 可觀測」有落差，**修補成本低**（調整 `except` 順序／收窄 `ValueError` 處理），非根本重作。其餘主委假設（`n_source` 自創字面、對稱序列 PSR、頂層 allowlist、24 例矩陣人造態、`_finite_or_none`）本輪**不列 blocking**。

**BLOCKING**：0。**MAJOR**：1（P1-01）。**MINOR**：1（P2-01）。

---

## 段 A — 契約符合度（Task 3.1–3.4）

| Task | 結論 | 要點 |
|------|------|------|
| **3.1** | **符合** | 三函式簽名與 A1-5 一致；`InvalidValidationArgument⊂ValueError` 且 `n_trials<1`／`target_sharpe<=0`／`t_years<=0`／`x>700` 皆 raise；`EligibilityResult` 欄位 ⊆ `eligibility_keys∪{status,reason}`（無 `budget_capped`）；驗收①–⑨ 落地，⑨ `n_obs==3362`、20 seed 平均斷言。 |
| **3.2** | **符合** | `deflated_sharpe` 簽名與互斥語意正確；分母僅 `sr.sr_estimator_variance`（`deflated_sharpe.py` 無 `kurtosis`／`skew`）；snapshot 集合成員＋`len(valid_sharpe_values)<=n_valid_metrics`；explicit None vs 非有限兩 reason；驗收①–⑧ 有對應測試。 |
| **3.3** | **符合** | 五節必填鍵與 A1-13 一致；`WARNING_TEXT_KEY` 唯一定義於 `report.py`（`grep strategy_validation.downgraded` 僅一處）；`universe_scope=="ledger_recorded_only"` 強制降級；`assumed_not_ledgered⇒eligible=None`；`dsr`/`pbo=None⇒not_computed`/`n_unknown`；A1-17 AST 頂層字面組裝通過。 |
| **3.4** | **符合（route 例外見 P1-01／P2-01）** | 入口二分：None 不呼叫 `read_trial_ledger`／`assess_eligibility`；`<=0` 上拋 `InvalidValidationArgument`；捕獲集合恰為 `(OSError, json.JSONDecodeError, ContractViolation)`；route 三鍵投影；`grep from api. momentum/`==0；`test_phase6`／`test_frontend_integration` 未動。 |

---

## 段 B — 攻主委實作決定

| # | 議題 | 結論 |
|---|------|------|
| **1** `n_source` 自創 `"ledger"`／`"ledger_unavailable"` | **可接受，建議延伸檔補枚舉**。契約 `n_source` 型別為 `str`、無 `n_source_values`；`assumed_not_ledgered` 為 TODO 明寫。前兩字面不違反機械契約，但 loader 無法防 typo——B4 前可加 `n_source_values` 至延伸檔（非本輪 blocking）。 |
| **2** 帳本非 ok 仍算 `trials_budget` | **合理**。N 不可知時 `eligible`／`required`／`trials_used` 皆 None，但 T／SR* 預算仍可展示；測試⑥ 明確斷言 `trials_budget==3`。 |
| **3** DSR `_fail` status 選值 | **與 IC `capability_status` 一致**。`cross_trial_variance_unavailable`／`ledger_snapshot_mismatch`→`unavailable`；`degenerate_returns`→`not_computed`；皆經 `_validated_status`。 |
| **4** 驗收①「skew=0、kurt=3」 | **實作忠於統計語意、偏離 TODO 字面**。對稱序列樣本 skew=0（實測），樣本 excess kurt≈2.68≠3；測試以 scipy 矩**獨立重算** PSR，不引用 `sharpe.py` 變異數——數值正確。若嚴格字面需構造 population kurt=3 序列或改 TODO 為「樣本矩」。 |
| **5** 頂層 `display_downgrade`／`warning_text_key` | **符合 allowlist 原意**。兩鍵屬 `eligibility_keys`，頂層集合 `{五節}∪{display_downgrade,warning_text_key}` ⊆ `report_sections∪eligibility_keys`；測試 `test_downgrade_matrix_24_cases` 斷言通過。 |
| **6** `_finite_or_none` helper | **不觸 A1-17**。A1-17 禁 helper **組裝鍵**；值層 NaN→None 不改字面鍵集合；`trials_budget` 等 int 不套用（保持 int）。 |
| **7** route 5xx 路徑 | **部分可接受、有洞**（見 P1-01／P2-01）。`InvalidValidationArgument` 內層捕獲後仍 5xx，但 detail 被外層重包；裸 `ValueError`（非 IVA）→400，與 A1-16 精神不符。 |
| **8** 24 例矩陣人造 `eligible=True,status=unavailable` | **可接受邊界測試**。`assess_eligibility` 不產生此態，但用於驗證降級布林邏輯覆蓋；矩陣仍 24 例、恰 1 例不降級。 |
| **9** provenance 內容 | **合理**。None 路徑 `unavailable`/`n_unknown`；帳本路徑傳遞 `status`/`reason`/`n_semantics`；TODO 未細寫，現行誠實且不膨脹鍵集合。 |

---

## 段 C — 測試品質

- **mutation 17 條**（receipt 唯讀）：§V-1／2／3／11／12 設計對應 TODO 字面；§V-11 mutant 在 `ledger_result` 有 ≥2 `valid_sharpe_values` 時改分母，能抓「誤用跨 trial 變異數」——非假紅。未見「語法改但語意等價」之假紅跡象。
- **`_ledger` fixture `n_evaluated=max(n_valid,n_for_dsr)`**：不變式 `n_evaluated==n_valid+n_failed` 在 fixture 內可不成立，但受測斷言聚焦 snapshot／DSR 值／status，**未**依賴 `n_evaluated` 語意——列觀察、非 finding。
- **API 測試**：`TestClient(app)` 走真實 `api.main.app` route；monkeypatch 僅替 `MLPipelineConfig`／`PIPELINE_STORAGE_PATH`／reporter 工廠——屬合理隔離。⑧ 5xx 由 `InvalidValidationArgument`（`t_years=-1`）觸發，非其他錯誤（log 見 `InvalidValidationArgument: t_years 須為有限正數`）。

---

## 段 D — 數值／契約正確性

- **3.1 手算**：`(100,1.0)=9.210340371976184`；`T=2.3232876712328765` 下 budget 13／3／104／1422——本輪重算一致。
- **3.2**：`E[maxSR]/√V` 三點 1.5746／2.5306／3.2551 與 `(1-γ)Φ⁻¹(1-1/N)+γΦ⁻¹(1-1/(Ne))` 一致；單位不變性⑦ `atol 1e-12`；N=1 PSR 等式有測。
- **3.3**：`_finite_or_none` 不套用 int 欄；`validate_against_contract` 對 `trials_budget` 等 int 型別仍過（`test_downgrade_matrix` 含 int 值且無 raise）。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| 220 passed | fact-verified | **覆核 rc=0** |
| mutation 17 條 rc=0 | fact-verified（receipt） | **唯讀覆核** |
| phase6/frontend 9 passed | fact-verified | **覆核 rc=0** |
| decoupling baseline OK | fact-verified | **覆核** |
| `n_source` 自創字面可接受 | assumed→**verified（有保留）** | 不違契約；建議延伸檔加枚舉 |
| 對稱序列＋樣本 kurt 忠於 PSR | assumed→**部分推翻字面** | skew=0 成立；kurt≠3 但測試獨立重算正確 |
| 頂層鍵 allowlist 原意 | assumed→**verified** | AST＋測試通過 |
| IVA→5xx 外層重包可接受 | assumed→**部分推翻** | 仍 5xx 但 detail 污染（P2-01） |

---

## Findings（canonical）

## COMPOSER-R16-P1-01

**斷言**: `create_ml_pipeline` 外層 `except ValueError` 會把 reporter 冒出的裸 `ValueError`（非 `InvalidValidationArgument`）映射為 HTTP 400，與 A1-16「接線／內部語意錯誤應 5xx 可觀測」精神衝突，且現有 API 測試未覆蓋此路徑。

**碼證**: `api/routes/ml_pipeline.py:279-281` `except ValueError as e: raise HTTPException(status_code=400, ...)`；`reporter.py:12` 明寫「其他例外（含 `ValueError`／`InvalidValidationArgument`）一律上拋」。RECHECK：`venv/bin/python scripts/_composer_b3_ve_probe.py`（timeout 60s）→ `VE status= 400`，`detail= bare value error from reporter`。對照 `test_ml_pipeline_strategy_validation.py` 僅測 `TypeError`／`InvalidValidationArgument` 5xx，無裸 `ValueError` 案例。

**來源摘要**: api/routes/ml_pipeline.py#c169afcbdb97

[MAJOR] 信心度=High。B4 wiring 後 `read_trial_ledger`／`_validated_status` 等 `ValueError` 會被客戶端 400 掩蓋，與 IVA 5xx 語意不一致。修法：外層 `except ValueError` 排除 reporter 路徑（或改捕 `InvalidValidationArgument` 後加 `except HTTPException: raise` 再收窄 `ValueError`）；補 API 測試斷言裸 `ValueError` 為 5xx。

---

## COMPOSER-R16-P2-01

**斷言**: 內層 `except InvalidValidationArgument` 所 raise 的 `HTTPException(500, detail="strategy_validation reporter argument error")` 會被外層 `except Exception` 重包，使回應 detail 變為 `Internal error: 500: strategy_validation reporter argument error`，削弱 A1-16 可觀測性。

**碼證**: `api/routes/ml_pipeline.py:255-258` 內層 raise；`:282-284` 外層 `except Exception`。RECHECK：`pytest tests/api/test_ml_pipeline_strategy_validation.py::test_wiring_error_negative_t_years_is_5xx_not_reporter_failed -s` → log `HTTP 500: Internal error: 500: strategy_validation reporter argument error`；狀態碼仍 500，測試只斷言 5xx 且無 `reporter_failed`。

**來源摘要**: api/routes/ml_pipeline.py#c169afcbdb97

[MINOR] 信心度=High。仍為 5xx、未吞成 `reporter_failed`，但專用 detail 被污染。修法：外層加 `except HTTPException: raise`（置於 `except Exception` 之前），或將 IVA 處理移出外層 try。

---

STATUS: DONE
