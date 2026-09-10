# EVTLABEL B1（Phase 1）＋TIERTOGGLE code review R1

brief-kind: review
task-id: 20260910-EVTLABEL-B1-REVIEW-R1
findings-round: R1
標的 diff：`git diff 0dbe40ff..0c9cd69d -- momentum api tests frontend`（36 檔；文件類不在審查範圍）
規格：`docs/EVTLABEL_SPEC.md` v4＋`docs/EVTLABEL_TODO.md`（三家已 RECONCILE-STAMP APPROVED）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 之 §0／§1（十一類）執行，**但審查對象是碼不是規格**。
findings 用 canonical ID：`## <FAMILY>-R1-P<0-3>-<NN>`。實作者（Claude）不自審。

## 本輪三個 commit（各自獨立，可分別否決）

1. `e18045c7` fix(frontend)：修 `npm run build`（本來就紅，非本批引入）
   - `MarginalICTable.tsx`：`useICAnalysisStore` 原本寫在兩個 early return **之後** ⇒ rules-of-hooks 違規（hook 順序會錯位）。改成函式頂端呼叫。
   - 4 個未使用 import 移除。
2. `e8903c28` fix(ic)：票 TIERTOGGLE——具名 preset 全量消費 `stage_overrides`
   - 病：前端具名 preset 只送 `fdr_correction`／`marginal_ic`；後端具名分支也只讀那兩鍵 ⇒ UI「基礎」之 `ic_decay:false`／`grouped_ic:false` 被丟掉、照跑（2026-09-09 事件 run 實測仍產 `ic_decay` 5,909 特徵×7 horizon）。
   - 修：前端送全部 stage 開關（鍵集由 `STAGE_TOGGLE_KEYS` 單點產生）；後端具名分支改為與 custom 同一迴圈（跳過 `LOCKED_STAGE_KEYS`；缺 `fdr_correction` 仍強制 ON）。
   - 契約：`momentum/Analysis/contracts/ui_stage_toggles.json`（stage／module／locked／ui_only 四類鍵集）；pytest 12 條＋vitest 7 條兩端各自對證。
   - `scripts/decouple_baseline.txt` 補登**既有**債一筆（`ic_analysis_service.py:22` R4，HEAD 即存在、先前未登記）。
3. `0c9cd69d` feat(evtlabel)：B1／Phase 1（Task 1.1／1.2／1.3＋FU-3）
   - Task 1.1：`metadata.event_label_rule`（純函式在 `momentum/Analysis/event_label_mode.py`，經 `pipeline` 出口供 api 呼叫以守 R3）；鍵集不符即 raise；**只在事件路徑寫**。
   - Task 1.2／1.3：隔離區「本次 label 怎麼算」＋h/k 單位文案（`icLabelRule.ts`）。
   - FU-3：9 個 stage 掛 `@_timed_stage` ⇒ `metadata.stage_timings`；`canonical_sha` 之 `_CLOCK_KEYS` 加 `stage_timings`。
   - R-1 預留：`uniqueness{mean,min,n_eff,n_overlapping_pairs}` 只揭露不參與計算。

## 🔴 請優先攻的六點

1. **TIERTOGGLE 是否真的沒有殘餘幽靈**：UI 有 26 個 toggle，我把它們分成 stage／module／locked／ui_only 四類並寫進契約。請自己列舉 UI 全部 toggle，逐個確認分類正確——**特別是我判定「後端無對應旗標」的 7 個 ui_only 鍵**（`ic_method_selection`／`winsorization_method`／`monotonicity_test`／`return_type_selection`／`ic_autocorrelation`／`redundancy_method_selection`／`vif_filter`）：它們是真的沒接線（＝具名殘留），還是接在我沒找到的地方（＝我把幽靈寫成「正常」）？
2. **`_apply_tier_config` 具名分支之行為變更**：`deep_analysis`／`disabled_modules` 之模組控制與新的 stage 迴圈是否有交互作用？有沒有情形使某模組因本次改動由 ON 變 OFF（或反之）而未被測試覆蓋？
3. **FU-3 之 golden 風險**：`stage_timings` 加進 `tests/momentum/helpers/ichc_run.canonical_sha` 的 `_CLOCK_KEYS`（**依鍵名全域排除**）。這會不會把某個**該被比對**的同名鍵一起吃掉？其他 golden helper（`gap2_freeze_golden`、evtalign split baseline、evtwarmup）是否有各自的雜湊路徑會因新 metadata 鍵而紅？
4. **Task 1.1 之正確性**：`label_window_feature_bars` 取自 `label_end_ms − label_start_ms`（不由 h 重算）。請驗：`open_to_horizon_close` 之視窗是否確為 (h+1)×bar、`open_to_close` 是否為 1×bar；mixed timeframe 取 max 是否正確（還是應該 fail-closed）。
5. **`uniqueness_from_windows` 之 O(n²)**：165 事件無感，但匯入上限是多少？請找出實際可能的最大事件數並判斷是否需要改演算法或加上限（這是我沒查的）。
6. **解耦**：`api/services/ic_analysis_service.py` 經 `create_event_sample_pipeline()` 呼叫 `pipeline.build_event_label_rule`（薄委派）——這是規避 R3 的正當做法，還是把違規藏起來？請正面判。

## 本 brief 之前提（逐條標；請優先攻 assumed）

fact-verified: 具名 preset 舊版只映射兩鍵 → 讀 `ic_filter_orchestrator.py` 舊分支＋前端 `getEffectiveConfig` 舊 return；且 2026-09-09 受理 run 報告 `ic_decay` 有 5,909 條、`grouped_ic` 有節。
fact-verified: 修法可證偽 → mutation 改回只映射兩鍵 ⇒ `test_tier_toggle_sync.py` 7 failed（實跑）。
fact-verified: `label_window_feature_bars` 之來源 → `handoffs/20260910-probe-label-rule.py` rc=0：h1 c2c 視窗 12 根、h12 o2hc 156 根（mismatch=0）。
fact-verified: 模組開關**非**幽靈 → schema `FeatureTierConfig.presets` 有預設（foundation `deep_analysis=False`），`_apply_tier_config` 讀 `config.model_dump()` 拿得到，不是空 dict。
fact-verified: `ic_analysis_service.py:22` 之 R4 為既有債 → `git show HEAD:...` 該行在本批之前即存在。

assumed: **UI 之 7 個 `ui_only` 鍵真的沒有後端旗標**（我只 grep 了 `STAGE_OVERRIDE_PATHS`／`MODULE_ENABLED_PATHS` 兩張表）
← 否證觀測：其中任一鍵在別處（config schema、route、service）有對應開關 ⇒ 我把幽靈寫成「正常」。／我跑了：只讀那兩張表。**請正面打這條**。
assumed: `stage_timings` 依鍵名全域排除不會誤吃該比對的鍵
← 否證觀測：repo 中另有語意不同的同名鍵。／我跑了：沒 grep 全 repo。
assumed: 事件批規模不會讓 `uniqueness_from_windows` 之 O(n²) 成為問題
← 否證觀測：匯入上限允許數萬事件 ⇒ 分析明顯變慢。／我跑了：沒查匯入上限。
assumed: mixed timeframe 取 `max(視窗)` 是正確處置（而非 fail-closed）
← 否證觀測：混批下某事件之單位換算被此 max 誤述。／我跑了：只寫測試釘住現行選擇，沒有 quant 論證。

## ⚠️ 前置說明
- **禁改碼、禁改文件**（只提出，由 Claude 改）。不得跑 `pytest tests/governance`（小時級）。
- 既有紅：`EA-RESID-6` 四條 golden（本批之前就紅）。
- 前端 `npx tsc --noEmit` 有 8 條**既有**錯誤（皆在我沒動的測試檔）；`npm run build` 已綠。

## 我跑了什麼（可重跑）
```
venv/bin/python -m pytest tests/api/test_evtlabel_disclosure.py tests/momentum/test_stage_timings.py tests/momentum/test_tier_toggle_sync.py -q   # 25 passed
venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py tests/api/test_isolation_disclosure.py -q                                  # 18 passed（含 G-1）
venv/bin/python -m pytest tests/momentum/test_tier_config.py tests/api/test_tier_api.py tests/api/test_ic_deep_analysis.py tests/momentum/test_ic_1eb_b4_fullstack.py -q  # 91 passed
cd frontend && npx vitest run src/components/ic-analysis src/lib/icLabelRule.test.ts src/lib/icIsolation.test.ts src/store                        # 30 檔 255 passed
cd frontend && npm run build                                                                                                                      # rc=0
```
mutation 自證：把 TIERTOGGLE 修法改回「只映射兩鍵」⇒ `test_tier_toggle_sync.py` 7 failed（可證偽）。

## 🔴 我沒查的
| claim | observable_if_false | reason_code |
|---|---|---|
| 匯入事件數上限（影響 `uniqueness_from_windows` O(n²)） | 大批次分析明顯變慢 | cost |
| `stage_timings` 是否會被其他 golden／契約鍵集檢查視為未知鍵 | 某 golden 或 contract 檢查紅 | cost |
| 7 個 ui_only 鍵是否真的沒接線 | 其中某鍵其實有後端旗標 ⇒ 我把幽靈寫成正常 | cost |
| `_stage6b_marginal_ic` 之計時在 fallback 路徑重跑時是否語意正確（累加） | 同名 stage 秒數看起來異常大 | cost |

## 必答（成對）
1a. 有無**資料正確性**問題（Task 1.1 之單位換算、視窗來源、mixed tf 處置）？ 1b. 若有，最小修法。
2a. TIERTOGGLE 是否留有未具名幽靈？ 2b. 若有，逐個列名。
3a. FU-3 是否可能弄紅任何既有 golden／契約？ 3b. 若是，指出哪一個與重現指令。
4a. 有無 ≥10× 不必要複雜？ 4b. 可刪的具名。
5. 可以進 B2（Phase 2 purge 換算）嗎？有 BLOCKING 就明說。

## 停輪條件
① 必答 1a–5 皆有 verdict；② 必答 2a 之 UI toggle 逐個分類判定齊備；③ P0／P1 皆指出對應修訂位置。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
