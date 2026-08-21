# GAP-3 B5 review R2 — grok（閉合輪）

task-id: 20260821-GAP3-B5-REVIEW-R2
family: grok
brief-kind: review
brief: handoffs/20260821-gap3-b5-review-r2-brief.md
R1 修補 diff: `git diff eb3f9b4e..HEAD`
R1 收斂: handoffs/reconcile/20260821-gap3-b5-review-r1/synth.md
修後 receipt: handoffs/run_receipts/20260821T230000Z-gap3-b5-r1-fix-gate.log
規模: handoffs/run_receipts/gap3_import_scale.json

## Verdict：可進三家 RECONCILE-STAMP／交使用者 UAT（本家 R1 6/6 CLOSED；本輪 1 條 P2 敘事計數，不擋 Gate）

### 必答

1. **己方 R1 各條 CLOSED／OPEN（附重跑輸出）**  
   | ID | 處置 | 本輪碼證摘要 |
   |---|---|---|
   | GROK-R1-P0-01 | **CLOSED** | `bash scripts/plain_docs_sync_check.sh` → **rc=0**（受管 10 檔全數同步） |
   | GROK-R1-P1-01 | **CLOSED** | `grep -n 'GAP-3 開發前' frontend/src/lib/pendingFeatures.ts` → 無命中；改為 G3-R9／G3-R10；registry 殘留表有 G3-R9／R10／R11；`npx vitest run gap3 pendingFeatures` → 4 files／21 passed |
   | GROK-R1-P1-02 | **CLOSED** | UAT B8b／B9b 在場；`pipeline.analyze_tables` 回 `all_bars_evaluation`（rule＝事件成員）；`eventExport` 寫 signed `label_value`；`-k all_bars` pipeline＋api 皆 passed；vitest gap3 綠 |
   | GROK-R1-P1-03 | **CLOSED** | `grep -c '^def create_event_\|^def create_condition_' momentum/factories.py` → **1**；契約改 `EventSamplePipeline.import_contract()`／`.condition_engine_contract()`；`test_factories_single_outlet_and_contract_readonly` passed |
   | GROK-R1-P2-01 | **CLOSED**（原 13→9 計數漂移已修） | 本輪 `-k gap3_import` → **12 passed**；`test_pipeline.py` collect **5**；vitest gap3＝17（與 pendingFeatures 合跑 21）。**另見本輪 GROK-R2-P2-01**：brief／synth 把 event_samples 寫成 232，receipt／HEAD 實為 **229** |
   | GROK-R1-P2-02 | **CLOSED** | `EventAnalyzeResponse.event_timestamps` description＝epoch ms；新增 `event_timestamps_ic_seconds`；`test_gap3_import_analyze_all_bars_and_ic_seconds` 斷言 `ms//1000` 關係 passed |

2. **修補是否引入新問題（brief Q2 五點）？**  
   - ①全 K 線 estimand：後端 `rule`＋`label_threshold_note` 寫入回應；前端標題硬編碼「rule＝事件成員」。此 estimand＝「事件成員根之報酬閾值表現」而非模型預測力；與 D4-3 並排 `prevalence_full`／`prevalence_learn` 一致。UI 未動態渲染 `label_threshold_note` 字面，但標題＋API 欄已揭露；**不另開 P0/P1**（見 §0）。  
   - ②`label_value`：`price_change` 來自搜尋引擎小數報酬（`pct_change`／`(close-open)/open`，非百分比）；short 取 `-pcRaw`、long 取原值 → signed PnL 方向正確。  
   - ③CSV chunk：`chunksize=5000`＋既有 `_csv_rows_to_records`（`dtype=str`／`keep_default_na=False`）——欄位語意未改，只改 materialization 邊界。  
   - ④`_canon_cols` casefold：探針 `Event_ID,T0,Label`／BOM＋`event_id` ⇒ `looks_new_schema` True；legacy 三欄大小寫仍 `looks_legacy` True；不會把無關欄誤當 marker（需三鍵齊備）。`case_variants` 測試綠。  
   - ⑤`elif event_timestamps`：僅在無 `event_query` 時啟用 `enabled=True`；只給 query／皆無路徑不變（三態測試綠）。  
   - 本輪唯一新 finding＝敘事計數 P2（下）。

3. **B5 Gate 複驗 rc=0？可進 stamp／交使用者 UAT？**  
   **可以（grok 本輪 APPROVED）**——本輪複驗：`plain_docs` rc=0；`-k gap3_import` 12 passed；`event_samples/` 229 passed；pipeline `all_bars|factories` 2 passed；vitest gap3+pendingFeatures 21 passed。`npm run build` 依 brief「只准一家跑一次」引修後 receipt rc=0，未並行重跑。前提：同輪 codex／composer 對其原 finding 亦 CLOSED 且無新 BLOCKING。

### R1 閉合逐條（原提出方重跑）

**Closure P0-01（GROK-R1-P0-01）— CLOSED**  
- 測：`bash scripts/plain_docs_sync_check.sh` → rc=0；stdout「白話說明 全數同步（受管 10 檔）」。

**Closure P1-01（GROK-R1-P1-01）— CLOSED**  
- 碼：`pendingFeatures.ts` registryId＝G3-R9／G3-R10；`IC_QUANT_GAP_REGISTRY.md`「GAP-3 殘留」三列。  
- 測：`grep 'GAP-3 開發前'` 無命中；vitest pendingFeatures 綠。

**Closure P1-02（GROK-R1-P1-02）— CLOSED**  
- 碼：UAT B8b／B9b；`pipeline.py:99-149` all_bars；`eventExport.ts:81-94` label_value；`EventTablesPanel` 全 K 區塊。  
- 測：`pytest …/test_pipeline.py -q -k all_bars`＋`tests/api -q -k "gap3_import and all_bars"` → passed。

**Closure P1-03（GROK-R1-P1-03）— CLOSED**  
- 碼：factories 唯一 `create_event_sample_pipeline`；契約唯讀方法在 pipeline。  
- 測：grep count＝1；`test_factories_single_outlet_and_contract_readonly` passed。

**Closure P2-01（GROK-R1-P2-01）— CLOSED**  
- 原「13 vs 9」已由修後 12／5／17 敘事取代；api／pipeline／vitest 本輪複驗一致。殘餘「232 vs 229」見本輪新 P2。

**Closure P2-02（GROK-R1-P2-02）— CLOSED**  
- 碼：`event_import_models.py:94-95`；api 測試 ms／秒關係綠。

### 他家 R1 條目（複核同意／異議）

| ID | 複核 | 證據摘要 |
|---|---|---|
| CODEX-R1-P1-01 | **複核同意 CLOSED** | `useICAnalysis.ts:283-286` payload 送 `event_timestamps`；`ic_analysis_service.py:1233-1236` elif 啟用 filter；`test_gap3_import_ic_timestamps_only_enables_event_filter` 三態 passed |
| CODEX-R1-P1-02 | **複核同意 CLOSED** | `sha256Hex` 無 subtle ⇒ throw；`canonicalSourceText`；回傳 `source_file_digest`／`source_digest_of`；vitest gap3 綠（含 crypto 對照） |
| CODEX-R1-P1-03 | **複核同意 CLOSED（部分採納範圍內）** | CSV `chunksize=5000`＋itertuples；`gap3_import_scale.json.api_path`＝10000／200／0.382s；串流殘留 G3-R10＋pendingFeatures——與 synth 部分採納一致 |
| CODEX-R1-P1-04 | **複核同意 CLOSED** | 與 GROK-R1-P1-02 同修；B8b／B9b＋all_bars＋label_value |
| CODEX-R1-P2-05 | **複核同意 CLOSED** | 與 GROK-R1-P1-03 同收斂為 1 出口 |
| CODEX-R1-P2-06 | **複核同意 CLOSED** | `_canon_cols`＋`test_gap3_import_new_schema_case_variants_on_legacy_endpoint`；手探 Event_ID／BOM 命中 |
| COMPOSER-R1-P3-00 | **複核同意**（R1 sentinel；本輪無 composer 原反例需閉） | R1 判可進 stamp 之範圍內項已由修補補強；不另議 |

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：全 K 線以「事件成員」為 rule 是匯入管線唯一可得訊號，`prevalence_full` vs `prevalence_learn` 並排即 D4-3 揭露 | **成立（攻擊不推翻）** | 匯入管線無模型分數（辨別表仍 `not_computed:no_model_scores…`＝G3-R9）；all_bars 用事件 t0 score=1 是唯一可再現 rule；回應帶 `rule`／`label_threshold_note`，UI 標題亦標「事件成員」。殘差：UI 未把 `label_threshold_note` 動態打出——屬可讀性，不把 threshold=0.0 誤當成模型 skill 的契約缺口（標題已定性）。不開 finding。 |
| **assumed**：串流上傳／async worker 以 G3-R10 登記即足 | **成立（攻擊不推翻）** | W10 明文記錄型、不私定門檻；API 路徑 10k 已入 receipt；真串流屬未定需求。chunk 解析降低單次 DF 峰值，未宣稱 OOM-proof 全鏈。不開 finding。 |
| fact-verified: 修後 api 12／event_samples 232／… | **部分不實** | api 12、vitest 17、plain_docs rc=0、build 引 receipt——成立。**event_samples「232」不實**：receipt 內文與本輪重跑皆 **229 passed** → GROK-R2-P2-01。 |

## GROK-R2-P2-01

**斷言**: R2 brief／R1 synth 之 fact-verified 敘事寫 `event_samples` **232** passed，但同一修後 receipt 內 pytest 輸出與本輪 HEAD 重跑皆為 **229** passed——屬「引 receipt 實測」義務未落實的計數漂移（同 GROK-R1-P2-01 失敗模式再犯於修補敘事）。

**碼證**: `handoffs/run_receipts/20260821T230000Z-gap3-b5-r1-fix-gate.log` 段「collected 229 items」／「229 passed」／`rc_event_samples=0`；本輪 `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → **229 passed** rc=0；`pytest … --co -q` → **229 tests collected**。對照 brief L34「232 passed」、synth L8／L22「232」。`RECHECK:` 重跑同上 pytest 計數須與任何 Gate 敘事一致。

**來源摘要**: handoffs/20260821-gap3-b5-review-r2-brief.md#72a1e61f82a6；handoffs/reconcile/20260821-gap3-b5-review-r1/synth.md#76c59e7939c1；handoffs/run_receipts/20260821T230000Z-gap3-b5-r1-fix-gate.log#da4e45960930

正文：[MINOR] 信心度=High。不影響行為／Gate rc；污染跨 agent 驗收敘事（摩擦八十七同類）。修法：stamp 前把 brief／synth／看板／commit 敘事之 event_samples 計數改為 **229**（或補測至宣稱數並更新 receipt）。不擋 stamp／UAT。

## 被當成事實的未驗證假設（§0）

見上表；新增揭露＝「232」偽 fact-verified（GROK-R2-P2-01）。其餘 assumed 攻擊不推翻。

ASSUMPTIONS_VERIFIED: 己方 R1 六條修補落地（plain_docs 綠、pendingFeatures→G3-R9/R10、all_bars+label_value+UAT B8b/B9b、factories=1、timestamps ms+ic_seconds）；他家 CODEX 六條＋composer sentinel 複核同意 CLOSED；Q2 五點無 P0/P1 回歸；event_samples 實為 229 非 232；G3-R10／事件成員 estimand assumed 攻擊不推翻
TESTS_RUN: `bash scripts/plain_docs_sync_check.sh` → rc=0；`venv/bin/python -m pytest tests/api/ -q -k gap3_import` → 12 passed rc=0；`… -k "gap3_import and (ic_timestamps or all_bars or case_variants or ic_seconds)"` → 3 passed；`venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k "all_bars or factories"` → 2 passed；`venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 229 passed rc=0；`cd frontend && npx vitest run gap3 pendingFeatures` → 4 files／21 passed rc=0；`grep -c '^def create_event_\|^def create_condition_' momentum/factories.py` → 1；`npm run build` 未本輪重跑（brief 禁並行），引 receipt rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260821-gap3-b5-review-r2-grok.md

STATUS: DONE
