# GAP-1 B3 實作 code review / grok | task-id=20260818-GAP1-B3-REVIEW-R16

brief-kind=review；家族=GROK；輪次=R16；審查標的 commit `cbd9ec69`；禁改碼／禁 commit。

## Verdict：需修補後進 B4

Task 3.1–3.4 契約本體（MinBTL／DSR／report／reporter＋三鍵投影）**大體成立**；
`venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q`
→ **220 passed rc=0**；phase6／frontend_integration → **9 passed rc=0**。
mutation receipt `handoffs/run_receipts/20260818T090000Z-gap1-b3-mutation.log` 17 條皆 rc=1（本輪**未**重跑探針，遵 brief 鎖／併發指引）。

但主委本輪 assumed／段 B 攻擊中，有兩條被實跑推翻為須修補：

| assumed / 攻擊點 | 本輪結論 |
|---|---|
| `n_source` 自創兩字面可接受 | **部分成立**——無枚舉即無機械違反；但與「禁自創字面／loader 枚舉對映」精神衝突 → P2-02 |
| 對稱序列＋樣本 kurt 忠於「skew=0、kurt=3 ⇒ PSR」字面 | **字面不忠、語意夠用**——skew=0 成立、kurt≈2.68≠3；DSR≡PSR 仍以獨立矩重算鎖住 → P2-03 |
| 頂層 `display_downgrade`／`warning_text_key` 屬 allowlist 原意 | **成立**——A1-8 要求 route 讀頂層兩鍵；⊆ `report_sections`∪`eligibility_keys` |
| route `except IVA ⇒ HTTPException(500)` 再被外層重包仍符「既有 500 路徑」 | **status 成立、語意削弱**——detail 變 `Internal error: 500: …`；且裸 `ValueError→400` 與 A1-16「既有 500」衝突 → P1-01／P2-01 |
| （額外實跑）IVA 5xx 前已寫 pipeline JSON | **推翻「失敗＝無副作用」**——orphan 檔留盤 → P1-02 |

非根本缺陷、不需重作 B3；建議修補後進 B4。

**工作區觀察**：B3 標的檔 clean；另有無關 dirty／untracked（`.claude/gate/audit.log`、`scripts/governance_families.json`、若干 handoffs/scripts）。本輪未改任何產品碼。

---

## 段 A — 契約符合度（Task 3.1–3.4）

### Task 3.1 — **符合**
- 三函式簽名與 A1-5 一致（`assess_eligibility(*, t_years, ledger_result, target_sharpe)`）。
- `InvalidValidationArgument(ValueError)`；三處參數驗證＋`x>700` 皆 raise 之（測試④⑧）。
- `EligibilityResult` 欄位 ⊆ `eligibility_keys`∪{status,reason}；無 `budget_capped`（測試顯式集合斷言）。
- 驗收①–⑨落地：手算值／floor 四點／20 組反函式／N=1／三種 raise／C5 oracle／ledger≠ok／N=1e6／x>700／⑨ 只斷言 20-seed 平均且 `n_obs==3362`。

### Task 3.2 — **符合**
- 簽名完整；分母**只**取 `sr.sr_estimator_variance`（本檔無 kurtosis／skew 重算；`grep` 無命中）。
- `ledger_result`／`n_trials` 互斥；snapshot＝集合成員＋`len(valid_sharpe)<=n_valid_metrics`。
- explicit None vs 非有限兩 reason 分開（⑤c）。
- 驗收①–⑧皆有對應測試；N=1⇒PSR、E[max] 三點、單調、單位不變、adaptive_search。

### Task 3.3 — **符合**
- 五節必填鍵與 A1-13 對齊（經 `validate_against_contract`）。
- `WARNING_TEXT_KEY` 唯一定義於 `report.py:25`（字面 `strategy_validation.downgraded` 僅此處；reporter import）。
- A1-4 `universe_scope=="ledger_recorded_only"` 強制降級；`assumed_not_ledgered`⇒`eligible=None`；dsr/pbo=None⇒`not_computed`/`n_unknown`。
- A1-17：`ast` 實查 `out={...}` 頂層 Constant 鍵＝五節＋`display_downgrade`＋`warning_text_key`；eligibility 九鍵＋status/reason 皆字面。

### Task 3.4 — **語意符合；route 例外分類有洞（見段 B／findings）**
- 入口二分：None 路徑不呼叫 ledger／assess（測試顯式）；`<=0` 上拋 IVA。
- 捕獲集合恰 `(OSError, json.JSONDecodeError, ContractViolation)`。
- route 只投影三鍵；`grep from api. momentum/`＝0；factories 兩出口在場。
- phase6／frontend_integration 9 passed（斷言未在本 commit 動）。

```
VERIFY: venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q
→ 220 passed, rc=0
VERIFY: venv/bin/python -m pytest tests/test_phase6_end_to_end.py tests/test_frontend_integration.py -q
→ 9 passed, rc=0
```

---

## 段 B — 攻主委實作決定

### B1. `n_source` 字面
- 契約 `n_source: str`（無 `n_source_values`）；TODO 只硬性寫死 `assumed_not_ledgered`。
- `"ledger"`／`"ledger_unavailable"` 為實作自創——**無枚舉即無機械違反**，但無法進 loader 枚舉對映，錯字／漂移不會轉紅。→ P2-02
- 建議延伸檔加 `n_source_values=["ledger","ledger_unavailable","assumed_not_ledgered"]`（或等價）。

### B2. 帳本非 ok 仍算 `trials_budget`
- **合理**：預算只依 T／SR；N 不可知只清空 `trials_used`／`required_*`。
- `x>700` 仍 raise＝呼叫方 bug（與帳本狀態無關）——符合 A1-16 不吞 bug。
- 測試⑥顯式 `trials_budget==3`。不列 finding。

### B3. DSR 檢查順序與 `_fail` status
- 順序：ledger status → period_returns → snapshot → compute_sharpe 退化 → SR0。符合「先傳入語意、再算」。
- `cross_trial_variance_unavailable`／`ledger_snapshot_mismatch` ⇒ `unavailable`（缺輸入／綁定失敗）；`degenerate_returns` ⇒ `not_computed`（輸入在場但無法形成統計量）。
- 與 IC `capability_status` 六值語意一致（二者皆在枚舉內）。不列 finding。

### B4. 驗收①「skew=0、kurt=3」
- 對稱序列 ⇒ 樣本 skew=0（實測）；樣本 kurt（fisher=False）≈**2.6835 ≠ 3**。
- 測試以 scipy 矩**獨立重算** PSR，不斷言 kurt==3——鎖的是 **N=1⇒DSR≡PSR**（正確核心），非 Gaussian 閉式特例。
- 對 TODO 字面「kurt=3」**不忠**；對數值正確性**足夠**。→ P2-03
- 若要恰 kurt=3：可用兩點質量±σ 的離散對稱（或調形狀參數）；或延伸檔改寫為「skew≈0 且以樣本矩重算 PSR」。

### B5. 頂層 `display_downgrade`／`warning_text_key`
- allowlist＝節名 ∪ `eligibility_keys` 鍵名；頂層兩鍵 ∈ `eligibility_keys` ⇒ ⊆ 成立。
- A1-8／route 明確讀 `section["display_downgrade"]`——**屬 TODO 原意**，非誤讀。不列 finding。

### B6. `_finite_or_none` helper
- A1-17 禁的是**鍵／節組裝** helper；值層 NaN→None 不碰字面鍵集合。AST 鍵仍為 Constant。不列 finding。

### B7. route 5xx／ValueError
- **IVA**：內層轉 `HTTPException(500)` 後被外層 `except Exception` 重包 ⇒ detail=`Internal error: 500: strategy_validation reporter argument error`（實跑確認）。status 仍 5xx。→ P2-01
- **裸 ValueError**：走既有 `except ValueError ⇒ 400`（實跑 `enum boom` ⇒ 400）。A1-16 明文「ValueError／IVA 上拋，由 route **既有 500** 路徑處理」——**400 與契約意圖衝突**。→ P1-01
- 修法：`except HTTPException: raise` 置於 ValueError 前；reporter 來源之 ValueError（或一律非 IVA 程式錯）映 5xx；或收窄 400 只涵蓋「請求組態」類。

### B8. 24 案例人造 `eligible=True, status=unavailable`
- `assess_eligibility` 不可達；矩陣測的是 **report 組裝純函式** 之組合邏輯。
- 另有真實路徑測試（None／assumed／universe_scope）。**可接受**邊界測試。不列 finding。

### B9. provenance
- None 路徑 `unavailable/n_unknown`；帳本路徑透傳 status／reason／n_semantics。
- TODO 未細寫——誠實且最小。不列 finding。

### 額外：寫檔順序
- `pipeline_file` 於 reporter **之前**寫入；IVA／5xx 後檔案仍在（實跑 orphan 1 檔）。今日全 None 路徑不觸發；G1-R1 接線後會中招。→ P1-02

---

## 段 C — 測試品質

### Mutation（讀 receipt，未並行重跑）
- §V-1／2／3／11／12 皆 rc=1；baseline／post-restore 219 passed。
- §V-11 mutant：僅當 `ledger_result` 且 `len(valid_sharpe)>=2` 才改用跨 trial 變異數——對應測試① ledger 路徑 `n_for_dsr=1` 但 sharpes 兩值，恰打中「誤用跨 trial」；**非語意等價假紅**。
- §V-1 刪 γ、§V-2 ln→n、§V-3 floor→round、§V-12 年化 SR 入矩——皆對應 TODO 字面。

### `_ledger` fixture 不變式
- `n_evaluated=max(n_valid, n_for_dsr)` 可使 `n_evaluated != n_valid_metrics+n_failed_or_pruned`（例：n_for_dsr=10、sharpes 長度 3）。
- 型別直構、未經 read 路徑——斷言未依賴該不變式通過 DSR；**不致假綠核心**，但案例狀態在生產 read 路徑不可達。→ P2-04

### API 測試路徑
- TestClient 走 `api.main.app`；monkeypatch 的是 route 模組之 `MLPipelineConfig`／`PIPELINE_STORAGE_PATH`——**真實 route 函式**仍執行（含 factories 呼叫與 except 鏈）。
- ⑧ 實跑確認為 IVA 觸發 5xx（非其他錯）；detail 經重包。④ OSError→2xx `reporter_failed` 正確。

---

## 段 D — 數值／契約正確性

### 3.1 手算（本輪重算）
- `(100,1.0)=9.210340371976184` ✓
- `T=2.3232876712328765`：SR 1.5→13、1.0→3、2.0→104、2.5→1422（floor）✓

### 3.2
- `E[maxSR]/√V`：N=10／100／1000 → 1.574598／2.530603／3.255122（對 1.5746／2.5306／3.2551，atol 1e-4）✓
- 單位不變性與 N=1 PSR 由測試鎖；本輪 pytest 全綠。

### 3.3 `_finite_or_none` 與 int
- `trials_budget`／`trials_used` **不**經 helper；型別保持 `int`；`validate_against_contract` 通過（實跑）。

---

## Canonical findings

## GROK-R16-P1-01

**斷言**: A1-16 要求 reporter 上拋之裸 `ValueError` 走 route「既有 500 路徑」，但 `create_ml_pipeline` 的 `except ValueError ⇒ HTTP 400` 會把其標成客戶端組態錯。

**碼證**: `api/routes/ml_pipeline.py:279-281` vs A1-16 第 2 點；VERIFY：monkeypatch reporter `raise ValueError("enum boom")` ⇒ status=400 detail含 `enum boom`；對照 IVA⇒500、TypeError⇒500。RECHECK：同 TestClient 路徑重現。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#bcfa76703d2a

[MAJOR] 信心度=High。今日 create 全 None 不觸發；G1-R1 接線後若 ledger/contract 路徑冒出裸 ValueError，監控會誤判為 400。修法：在 ValueError 分支前加 `except HTTPException: raise`；並將「來自 strategy_validation 的 ValueError」映 5xx，或令 reporter 邊界把應 5xx 之 ValueError 包成 IVA／專用型別。

## GROK-R16-P1-02

**斷言**: route 在呼叫 reporter 之前已把 pipeline JSON 寫入磁碟；IVA／5xx 回應後 orphan 檔仍存在，造成「HTTP 失敗但副作用成功」。

**碼證**: `api/routes/ml_pipeline.py:218-258`（先 `open(pipeline_file,'w')` 再 `for_study_trial`）；VERIFY：tmp 儲存路徑 + subclass 傳 `t_years=-1.0` ⇒ status=500 且 `tmp.glob('*.json')` 長度=1（`pipeline_orphan-probe_trial9_*.json`）。RECHECK：同步驟。

**來源摘要**: api/routes/ml_pipeline.py#c169afcbdb97

[MAJOR] 信心度=High。今日 optional 全 None 不進 IVA；驗收⑧與未來接線路徑會留垃圾／可 list 到「失敗建立」的 pipeline。修法：reporter 改到寫檔前；或 5xx 路徑刪除剛寫的檔；或寫入暫存再 rename。

## GROK-R16-P2-01

**斷言**: 內層 `except InvalidValidationArgument ⇒ raise HTTPException(500, detail="strategy_validation reporter argument error")` 會被同函式外層 `except Exception` 重包，使客戶端 detail 變成 `Internal error: 500: strategy_validation reporter argument error`。

**碼證**: `ml_pipeline.py:255-258` 與 `:282-284`；同端點其他 handler 有 `except HTTPException: raise`（如 get/delete），create 沒有；VERIFY 回應 detail 字面如上。RECHECK：IVA 案例讀 `resp.json()["detail"]`。

**來源摘要**: api/routes/ml_pipeline.py#c169afcbdb97

[MINOR] 信心度=High。仍為 5xx，符「可觀測失敗」底線；但訊息雙層污染、與專用 detail 設計矛盾。修法：`except HTTPException: raise` 置於通用 Exception 前（或不要在內層轉 HTTPException，直接讓外層 500 處理並固定 detail）。

## GROK-R16-P2-02

**斷言**: `n_source` 之 `"ledger"`／`"ledger_unavailable"` 為契約外自創字面（僅 `assumed_not_ledgered` 見於 Frozen TODO），且無 `n_source_values` 枚舉可供 loader／測試機械對映。

**碼證**: 契約 `eligibility.types.n_source=["str"]`（無 enum）；`min_btl.py:21-22,121,135` 兩常數；TODO 3.3／3.4 只點名 `assumed_not_ledgered`。RECHECK：`load_strategy_validation_contract()["eligibility_keys"]["n_source"]`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#42a6dce48e47

[MINOR] 信心度=High。非正確性 bug（str 開放）；失敗模式＝錯字／第三值漂移靜默通過。修法：延伸檔新增 `n_source_values` 三值＋契約／測試枚舉對映（與其他 `*_values` 一致）。

## GROK-R16-P2-03

**斷言**: Task 3.2 驗收①字面要求「skew=0、kurt=3 ⇒ 等於 PSR」，但測試對稱序列之樣本 kurtosis（fisher=False）≈2.68≠3；斷言改為與「以樣本矩重算之 PSR」比對。

**碼證**: TODO:282 字面；`test_deflated_sharpe.py:_symmetric_returns`／`_psr_analytic`；VERIFY：`sps.kurtosis(values, fisher=False)≈2.6835`、`skew==0`。RECHECK：同 seed 構造印 kurt。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#42a6dce48e47

[MINOR] 信心度=High。N=1⇒DSR≡PSR 不變量仍被鎖（且比「假設 kurt=3 閉式」更強）；風險是後續 agent 按字面「造 kurt=3 序列」或放寬比對。修法：延伸檔改驗收①措辭為「skew≈0，PSR 以樣本矩獨立重算」；或另造恰 kurt=3 序列並雙鎖。

## GROK-R16-P2-04

**斷言**: `test_deflated_sharpe._ledger` 以 `n_evaluated=max(n_valid, n_for_dsr)` 直構，可違反帳本不變式 `n_evaluated==n_valid_metrics+n_failed_or_pruned`，使部分案例建立在 read 路徑不可達狀態上。

**碼證**: `test_deflated_sharpe.py:51-68`；例 n_for_dsr=10、sharpes 長度 3 ⇒ n_evaluated=10、n_valid=3、n_failed=0。DSR 斷言未依賴該等式 ⇒ 不致核心假綠。RECHECK：印 fixture 三欄。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_deflated_sharpe.py#8ef47c23d97b

[MINOR] 信心度=Medium。建議 fixture 改為滿足不變式（`n_failed_or_pruned=n_evaluated-n_valid` 或對齊 n_for_dsr 與 valid 語意），避免未來測試誤倚不可能狀態。

---

## 被當成事實的未驗證假設（§0）

1. assumed「n_source 自創可接受」→ 本輪改標為**契約缺口**（P2-02），非實作違規。
2. assumed「對稱序列忠於 kurt=3」→ **推翻字面**（P2-03）。
3. assumed「頂層兩鍵＝allowlist 原意」→ **成立**（A1-8）。
4. assumed「IVA HTTPException 重包仍符 500」→ status 成立、detail／ValueError 映射不成立（P1-01／P2-01）。

STATUS: DONE
