# Reconcile — 20260818-gap1-b3-review-r16

**來源** 20260818-gap1-b3-review-codex.md, 20260818-gap1-b3-review-composer.md, 20260818-gap1-b3-review-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18；B3 實作 code review → B3 修補 commit ＋延伸檔 A1-22）

三家共 **12 條** canonical ID（codex 4／composer 2／grok 6）；下列 **六群集 M1–M6 引用全部 12 條，0 掉項**。
三家 Verdict **一致＝「需修補後進 B4」**（無 P0；無 Verdict 分歧）。嚴重度分歧一律**取較嚴版＝本輪修**，不登記殘留。
🔴 主委 brief 四條 assumed 之判定（三家一致）：①`n_source` 自創字面 **部分成立**（無枚舉即無機械違反，但違「禁自創字面／loader 枚舉對映」精神 ⇒ 修）
②對稱序列＋樣本 kurt 忠於「skew=0、kurt=3」字面 **推翻字面**（樣本 kurt≈2.68≠3；不變量仍被鎖 ⇒ 改構造恰 kurt=3 序列雙鎖）
③頂層 `display_downgrade`／`warning_text_key` 屬 allowlist **成立**（三家 AST 實查）
④route 之 IVA→HTTPException(500) 外層重包 **status 成立、語意削弱**（detail 污染）＋ **裸 `ValueError→400` 與 A1-16 衝突**（兩家 MAJOR）⇒ 修。
另：grok／codex 各自實跑抓到 **IVA 5xx 前 pipeline JSON 已落盤（orphan）**——主委 brief 未列、三家中兩家抓到，接受。
段 A 三家皆判 3.1–3.4 契約符合；段 D 手算值／三點／單位不變性三家重算一致。

### M1 — route 例外分類：裸 `ValueError→400`（A1-16 衝突）＋ IVA 之 HTTPException 被外層重包
**引用**: COMPOSER-R16-P1-01, GROK-R16-P1-01, COMPOSER-R16-P2-01, GROK-R16-P2-01

兩家實跑：reporter 冒出裸 `ValueError` ⇒ 400（`except ValueError`）；IVA ⇒ 500 但 detail 變 `Internal error: 500: …`（外層 `except Exception` 重包）。
A1-16 之意圖＝「呼叫方 bug／內部語意錯須 5xx 可觀測」；G1-R1 接線後 ledger／contract 路徑冒出之 `ValueError` 會被 400 誤標為用戶錯。
**處置（修）**：① reporter 呼叫處：`except InvalidValidationArgument ⇒ HTTPException(500)`、**`except ValueError ⇒ HTTPException(500)`**（reporter 路徑之
ValueError 一律 5xx；例外文字只進 log）② 外層在 `except ValueError` **之前**加 `except HTTPException: raise`（消除重包；同端點 get/delete 已有此形）
③ API 測試新增「裸 `ValueError` ⇒ 5xx」與「IVA 之 detail 不含 `Internal error:` 前綴」兩斷言。

### M2 — 5xx 之前 pipeline JSON 已落盤（orphan artifact）
**引用**: CODEX-R16-P2-03, GROK-R16-P1-02

grok 實跑：`t_years=-1.0` ⇒ 500 且 tmp 內 `pipeline_*.json` 長度=1；codex 由 log 順序（saved → exception）同結論。codex P2、grok P1 ⇒ 取較嚴＝修。
**處置（修）**：reporter 呼叫**移到寫檔之前**（reporter 為純讀；失敗即不落盤，無需 cleanup）；API 測試新增「5xx ⇒ 儲存目錄無 json」斷言。

### M3 — 驗收①之「skew=0、kurt=3」oracle 未被固定
**引用**: CODEX-R16-P2-01, GROK-R16-P2-03

codex／grok 實跑：對稱序列樣本 Pearson kurt=2.6835≠3；測試以樣本矩重算 PSR（不變量仍鎖），但 TODO 字面「skew=0、kurt=3」未被覆蓋。
**處置（修，雙鎖）**：構造 **恰** skew=0、kurt=3 之序列（`m ± s` 各 n₁ 個＋ 4n₁ 個 `m`：population kurt ＝ N/(2n₁) ＝ 3、skew ＝ 0，均值位移不改中央矩）
⇒ 測試先斷言 `sps.skew==0`、`sps.kurtosis(fisher=False)==3`（atol 1e-12），再斷言 DSR ＝ **閉式** PSR `Φ(SR√(T-1)/√(1+SR²/2))`（atol 1e-10）；
原「樣本矩獨立重算」案例保留為第二鎖（更強之不變量）。

### M4 — `test_deflated_sharpe._ledger` fixture 違反帳本不變式
**引用**: CODEX-R16-P2-02, GROK-R16-P2-04

`n_evaluated=max(n_valid, n_for_dsr)`、`n_failed_or_pruned=0` ⇒ `n_evaluated≠n_valid+n_failed`（read 路徑不可達）。DSR 斷言未倚賴該等式（無核心假綠），但不應建立在不可能狀態上。
**處置（修）**：fixture 改為 `n_failed_or_pruned = n_evaluated - n_valid_metrics`（不變式由構造成立），並加 fixture 自檢斷言；snapshot 上限案例以顯式 `n_valid` 覆蓋。

### M5 — `n_source` 兩字面為契約外自創（無 `n_source_values` 可機械對映）
**引用**: GROK-R16-P2-02

composer 段 B1 同建議「B4 前加 `n_source_values`」；grok 判 MINOR 修法＝延伸檔新增三值枚舉。與本 epic「禁自創字面、枚舉住契約、loader 機械對映」一致 ⇒ 修。
**處置（修＋延伸檔 A1-22）**：契約新增頂層 `n_source_values = ["ledger","ledger_unavailable","assumed_not_ledgered"]`（頂層鍵 **16 → 17**；A1-22 覆寫 Task 2.1「恰 16」與 A1-4 之「16」）；
`_EXPECTED_TOP_LEVEL_KEYS`／`test_exactly_sixteen_top_level_keys` 同步 17；`validate_against_contract` 之 `{k}_values` 機械對映**自動**涵蓋 `eligibility.n_source`（無需改碼）；
`min_btl.py`／`reporter.py` 之三字面改由契約枚舉讀取並於構造時檢查（`_validated_n_source`）。

### M6 — `factories.py:564` 多出一行未使用之 runtime import（主委 sed 誤傷）
**引用**: CODEX-R16-P3-04

主委以 `sed` 在 `TYPE_CHECKING` 區塊加 import 時，同一模式亦命中 `create_adversarial_validator()` 內之 lazy import 行 ⇒ 多插一行無用 import（啟動耦合）。
**處置（修）**：刪除該行；保留 `:28`（TYPE_CHECKING）與 `:769`（專用 lazy factory）。教訓：對多處同型行做 `sed` 前先 `grep -c` 命中數（本 epic 第二次同型：K4 亦曾 sed 過寬）。

**Verdict**: 需修補後合併 → 修補於 B3 修補 commit ＋延伸檔 A1-22；三家戳記後進 B4。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R16-P2-01
**斷言**：DSR/PSR 單元測試沒有真正固定規格要求的 skew=0、Pearson kurtosis=3 oracle。
**碼證**：`_symmetric_returns()` 的成對隨機幅度 fixture 實跑 Pearson kurtosis=2.6835207094713915；因此測試可在未覆蓋指定矩特例時通過。
**來源摘要**：`docs/GAP1_STRATEGY_OVERFIT_TODO.md#42a6dce48e47`；`tests/momentum/Analysis/strategy_validation/test_deflated_sharpe.py#8ef47c23d97b`。
[MINOR] 信心度=10/10；失敗模式是 oracle coverage 不足；修補為固定六點對稱序列並在比較 DSR/PSR 前明確斷言 skew=0、kurtosis=3。
## CODEX-R16-P2-02
**斷言**：DSR 測試 `_ledger` fixture 違反 B2 ledger invariant，未證明實際 ledger 狀態下的 DSR 路徑。
**碼證**：fixture 預設 `n_valid_metrics=3,n_for_dsr=10,n_evaluated=10,n_failed_or_pruned=0`；實跑 `n_evaluated == n_valid_metrics + n_failed_or_pruned` 為 `False`。
**來源摘要**：`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#bcfa76703d2a`；`tests/momentum/Analysis/strategy_validation/test_deflated_sharpe.py#8ef47c23d97b`。
[MINOR] 信心度=10/10；失敗模式是 impossible fixture 造成假綠；修補為令 n_evaluated 等於 valid+failed，另以獨立 case 覆蓋 snapshot 上限。
## CODEX-R16-P2-03
**斷言**：reporter 的 `InvalidValidationArgument` 5xx 路徑在 pipeline JSON 已落盤後才執行，失敗請求會留下 ghost artifact。
**碼證**：route 先在 `ml_pipeline.py:218-223` 寫檔，後於 `249-258` 呼叫 reporter 並將負 `t_years` 轉為 500；同一 pytest 實跑 log 先出現 saved path、再出現 exception/HTTP 500。
**來源摘要**：`api/routes/ml_pipeline.py#c169afcbdb97`；`handoffs/20260818-gap1-b3-review-BRIEF.md#8881a9ea1cc5`。
[MINOR] 信心度=9/10；失敗模式是 5xx 後可重試但殘留不完整 pipeline；修補為 reporter 先於 persistence，或在 5xx 上做明確 transactional cleanup。
## CODEX-R16-P3-04
**斷言**：B3 commit 在 `create_adversarial_validator()` 新增未使用的 runtime `StrategyValidationReporter` import，造成無必要耦合與啟動成本。
**碼證**：`momentum/factories.py:564` import 後函式只回傳 `AdversarialValidator(config=config)`；真正 reporter factory 位於 `:767-771`。
**來源摘要**：`momentum/factories.py#f2b0a3d33fa1`；`handoffs/20260818-gap1-b3-review-BRIEF.md#8881a9ea1cc5`。
[TRIVIAL] 信心度=10/10；失敗模式是無功能必要的 import side effect；修補為移除該行，保留專用 lazy factory。
段落結論：A 契約/實作大致符合；B ledger、status、report shape、route 入口可追溯但有 P2-03；C 17/17 mutation 皆轉紅；D hand values/factors/int fields 通過，P2-01 未達 exact moment oracle。
ASSUMPTIONS_VERIFIED: R9 三方 reconcile stamps 均 APPROVED；目標為 cbd9ec69；`n_source` 無 contract enum；warning key 唯一定義；momentum→api import grep=0，baseline checker 通過。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` = 220 passed；回歸 = 9 passed；`bash scripts/gap1_b1_mutation_probe.sh` = rc0、17/17 mutants red；`python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` = BASELINE OK。
FAILURES_SEEN: `scripts/restore_golden_inventory.sh` rc128（sandbox 禁止建立 .git/index.lock，未改 .git）；mutation probe 結尾 tail 缺少暫存 log，但 rc0、mutant restore 後工作樹無新增目標檔變更。
SCOPE_CHANGES: none；僅新增 `handoffs/20260818-gap1-b3-review-codex.md`，未改 code/SPEC/TODO/data_cache，未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none；本檢查未改輸出 schema、數值、檔案大小或既有測試斷言。
HANDOFF_OUTPUT: `handoffs/20260818-gap1-b3-review-codex.md`
STATUS: DONE
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


## 戳記

RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:b367b5722c772db7902138f4cf38bfe090e6f5b95ed9498e8210bc8d2d4c4774 task:20260818-GAP1-B3-STAMP-R17
RECONCILE-STAMP: grok APPROVED 2026-08-18 sha256:b367b5722c772db7902138f4cf38bfe090e6f5b95ed9498e8210bc8d2d4c4774 task:20260818-GAP1-B3-STAMP-R17
RECONCILE-STAMP: codex APPROVED 2026-08-18 sha256:b367b5722c772db7902138f4cf38bfe090e6f5b95ed9498e8210bc8d2d4c4774 task:20260818-GAP1-B3-STAMP-R17
