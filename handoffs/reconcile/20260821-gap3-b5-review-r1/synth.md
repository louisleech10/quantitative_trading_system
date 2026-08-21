# Reconcile — 20260821-gap3-b5-review-r1

**來源** 20260821-gap3-b5-review-r1-codex.md, 20260821-gap3-b5-review-r1-composer.md, 20260821-gap3-b5-review-r1-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置（主委 Claude 裁決；全部寫回，api gap3_import 12 passed、event_samples 232 passed、feature_engineering＋GAP-1 289 passed、vitest gap3 17／全套 160 passed、npm run build rc=0；receipt `handoffs/run_receipts/20260821T230000Z-gap3-b5-r1-fix-gate.log`）

**Verdict**: 需修補後合併——11 條 findings（含 1 P0）全數採納修補（已落檔）；R2 由原提出方重跑同一反例閉合，全 CLOSED 後三家 RECONCILE-STAMP → 交使用者 UAT。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| X1 事件模式 timestamps 未送達後端（**功能斷鏈**） | CODEX-R1-P1-01 | **採納**：①`useICAnalysis` `/analyze` payload 加 `event_timestamps`（事件模式且非空）；②`ic_analysis_service._build_config_override` 在只給 timestamps（無 query）時亦 `event_filter.enabled=True`（否則 orchestrator `mode=none` 靜默丟事件）；測試：`test_gap3_import_ic_timestamps_only_enables_event_filter`（三態：只 timestamps／只 query／皆無）＋vitest 讀 hook payload 區塊斷言 |
| X2 匯出 digest 造假／語意不明 | CODEX-R1-P1-02 | **採納**：移除 FNV 假 hash 退路（`sha256Hex` 無 subtle ⇒ 拋錯）；新增 `canonicalSourceText(cases)` 定義 source canonical bytes，`source_file_digest`＝其真 SHA-256；回傳體加 `source_file_digest`／`source_digest_of` 說明；測試以 `node:crypto` 獨立重算對照＋改值 digest 變 |
| X3 大檔非 bounded／缺 API 路徑 receipt | CODEX-R1-P1-03 | **採納（部分）**：CSV 改分塊解析（`CSV_CHUNK_ROWS=5000`＋`itertuples`，不再 `iterrows` 全表）；`gap3_import_scale.py` 增 **API 路徑實測**（10k 事件經 `/case/import-events/json`：200 OK、0.382s、RSS 記錄）寫入同一 receipt。**不採**「串流上傳／async worker」：W10 明文不設效能門檻、真串流屬未定需求 ⇒ 登記殘留 **G3-R10**（user-ruling）＋`/pending-features` 占位 |
| X4 UAT 未覆蓋「三表＋全 K 線」／匯出缺 label_value | CODEX-R1-P1-04, GROK-R1-P1-02 | **採納**：①`pipeline.analyze_tables` 增 **全 K 線驗證**（呼叫 B2.5 `evaluate_all_bars`，rule＝事件成員 score=1；批內多值 ⇒ `not_computed:batch_not_single_valued`）；②前端 `EventTablesPanel` 增全 K 線區塊（固定分母計數＋`prevalence_full` vs `prevalence_learn` 並排＋lift；不可用顯示原因）；③`/search` 匯出寫 `label_value`（signed；short 取負；缺 `price_change` 則不寫欄）⇒ 條件 IC 不再必然 `missing_label_value`；④UAT B 段增 **B8b 全 K 線**、**B9b 條件 IC** 兩項 |
| X5 plain_docs Gate 紅（**P0**） | GROK-R1-P0-01 | **採納**：`GAP-3事件型討論.md` 觸發字面「批做完」改寫（非移進度——該行本就是計畫敘述、非進度表）；`IC健檢偵察結果.md` 追記 GAP-3 B5＋新殘留並與 registry 同 commit（時序判準即解）。**主委承認 brief 寫「fact-verified plain_docs 綠」為錯**——receipt 尾行原就是 `rc=2`，我在 brief 誤植 |
| X6 pendingFeatures 過期占位 | GROK-R1-P1-01 | **採納**：刪「GAP-3 開發前討論題」條目，改為 **G3-R9**（辨別表接真實分數，blocked-by）＋**G3-R10**（大檔串流，user-ruling）；`docs/IC_QUANT_GAP_REGISTRY.md`「GAP-3 殘留」同步新增 G3-R9／R10／R11（三值理由），vitest `pendingFeatures` 防漂移仍綠 |
| X7 factories 出口字面越權 | CODEX-R1-P2-05, GROK-R1-P1-03 | **採納（收斂為一個出口）**：刪 `create_event_import_contract`／`create_condition_engine_contract`，改為 `EventSamplePipeline.import_contract()`／`.condition_engine_contract()` 唯讀方法；`grep -c '^def create_event_\|^def create_condition_' momentum/factories.py` ⇒ **1**；測試 `test_factories_single_outlet_and_contract_readonly` 機械鎖（含唯讀不污染）。不走 D-延伸（不需改白名單） |
| X8 新 schema 大小寫變體偵測 | CODEX-R1-P2-06 | **採納**：`_canon_cols`（去 BOM／引號／空白＋casefold）供 `looks_legacy`／`looks_new_schema`；測試三變體（`Event_ID,T0,Label`／全引號／BOM＋大寫）投舊端點皆 400 `new_schema_on_legacy_endpoint`；舊三欄大小寫變體投新端點 400 `legacy_schema_detected` |
| X9 測試計數敘事漂移 | GROK-R1-P2-01 | **採納**：brief／commit 寫 13 為錯（實為 9）。修後實測＝`-k gap3_import` **12 passed**、`test_pipeline.py` **5 passed**、vitest gap3 **17**；本 synth 與後續 commit 一律引 receipt 實測值 |
| X10 analyze 回傳單位文案踩雷 | GROK-R1-P2-02 | **採納**：`event_timestamps` description 明寫 **epoch ms（非 IC 秒）**；新增 `event_timestamps_ic_seconds` 欄（秒）供直接消費；測試斷言兩欄關係（`ms // 1000`） |
| X11 composer sentinel（0 findings） | COMPOSER-R1-P3-00 | **採認**：composer 判可進 stamp；其建議之「API 檔不得 import validator」grep gate 本輪一併加入 `test_gap3_import_contract_reasons_passthrough_not_reimplemented` |

**主委自陳**：X5 是我在 brief 把 `rc_plain_docs_sync=2` 誤寫成綠——grok 直接以 receipt 尾行打穿，屬「fact-verified 欄自我審核不實」，記入摩擦。

白名單檢視：本輪改動限 `momentum/Analysis/event_samples/{pipeline,bars_source}.py`（新檔）、`momentum/factories.py`（**一個**出口）、`api/{models,routes,services}`（§0-6-⑤）、`frontend/src/`（§0-6-⑤）、測試與收尾文件；`ic_analysis_service._build_config_override` 之 elif 分支屬 B5.1「API 接線」範圍（事件入口透傳，非統計邏輯）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: 選批雖在 `ICConfigPanel` 寫入 `event_timestamps`，`useICAnalysis` `/analyze` payload 只送 `event_query`；且 query 空時後端不啟用 event filter，故 B9 不會得到 `mode=timestamps`，picker 也取 raw records 而非對齊成功集。 **碼證**: `frontend/src/components/ic-analysis/ICConfigPanel.tsx:274-278`、`frontend/src/hooks/useICAnalysis.ts:269-283`、`api/services/ic_analysis_service.py:1226-1232`、`momentum/Analysis/ic_filter_orchestrator.py:2820-2822`; `rg -n "event_timestamps|event_query" frontend/src/hooks/useICAnalysis.ts frontend/src/components/ic-analysis/ICConfigPanel.tsx` → 只見 picker 寫入、hook 未序列化。 **來源摘要**: frontend/src/hooks/useICAnalysis.ts#7270767b4c2c [P1；信心 10/10] 修法：送出 timestamps、timestamp-only 時明確啟用 filter，改用 analyze/feed 的 aligned primary timestamps；RECHECK：新增 HTTP payload→metadata `mode=timestamps`/`n_events` 端到端斷言並重跑 `cd frontend && npx vitest run gap3`。
## CODEX-R1-P1-02
**斷言**: `/search` exporter 的 WebCrypto 退路是 FNV-1a 64-bit 重複成 64 hex，且 `source_file_digest` hash 的是 selected case tuple 而非實際來源檔／最終匯出 bytes；因此可通過長度測試卻不符合契約 `sha256_hex64` 的 provenance。 **碼證**: `frontend/src/lib/eventExport.ts:19-34,57-63,94-95`；`momentum/Analysis/contracts/event_import_contract.json:50-51`；`rg -n "FNV-1a|source_file_digest|JSON.stringify\(cases.map" frontend/src/lib/eventExport.ts` → fallback 與 tuple hash 均存在。 **來源摘要**: frontend/src/lib/eventExport.ts#aea0be5ede7f [P1；信心 9/10] 修法：移除假 hash 退路並只用真正 SHA-256，固定 canonical source bytes／export bytes 的 hash 語意，測試 digest 等於 canonical bytes SHA-256 並經 validator POST；RECHECK：WebCrypto 缺失測試環境仍須輸出真 SHA-256，且 digest mismatch negative fixture 必拒。
## CODEX-R1-P1-03
**斷言**: B5.1 的大檔邊界要求分頁／串流，但 `/case/import-events` 先 `await file.read()`，service 再完整 `read_csv`、`iterrows` 建 list、`to_dict` 落檔；async analyze route 亦直接呼叫同步 pipeline。10k receipt 只跑 direct pipeline，不能證明 HTTP 路徑 bounded/OOM-safe。 **碼證**: `api/routes/case.py:147-151,183-195`、`api/services/case_import_service.py:616,649-666,668-696,727-735`；`handoffs/run_receipts/gap3_import_scale.json` 實際含 `n_events=10000`, `wall_clock_s=76.377`, `peak_rss_mb=305.1`，但無 API upload receipt。 **來源摘要**: api/routes/case.py#8a2077c8bc29 [P1；信心 10/10] 修法：以 bounded upload/staging、chunk parse/validate/store 與 async worker 邊界落實要求；不新增效能門檻，補 API path 10k receipt（含 rc、wall clock、RSS）；RECHECK：同一 workload 經 `/case/import-events` 實跑並證明非全檔 materialization。
## CODEX-R1-P1-04
**斷言**: B5.3 要求匯入→對齊→三表→全 K 線→報告，但 checklist B8/B9 只驗兩張 endpoint table 與 IC metadata；`pipeline.analyze_tables` 也只回 forward-return／binary，沒有 conditional-IC 或 all-bars pass/fail 步驟，且本輪 `plain_docs_sync_check` 實跑為 rc=2。 **碼證**: `docs/GAP3_UAT_CHECKLIST.md:21-43`、`docs/GAP3_EVENT_TODO.md:465-476`、`momentum/Analysis/event_samples/pipeline.py:80-92`; `bash scripts/plain_docs_sync_check.sh` → rc=2（5 份白話文件 stale/watch 依賴）。 **來源摘要**: docs/GAP3_UAT_CHECKLIST.md#90d8356bd603 [P1；信心 10/10] 修法：B 段加入真實 kline `evaluate_all_bars` 的固定分母／prevalence／lift／eligible receipt 與 conditional-IC `label_value`／reason／n_events 步驟，或明列 residual 並禁止 stamp；同步 watcher 文件後重跑 plain-docs gate。
## CODEX-R1-P2-05
**斷言**: FROZEN TODO §0-6-⑦ 與 B5.1 修改清單只授權 `create_event_sample_pipeline()` 一個 factory 出口，但 diff 新增三個 `create_*`；「另兩個因 R3 唯讀」是設計理由，不是已核准的白名單變更，屬 scope/governance 越權。 **碼證**: `docs/GAP3_EVENT_TODO.md:16,436-442` 對照 `momentum/factories.py:837-855` 三出口；`api/services/case_import_service.py:619-622` 證明另兩個確有 caller。 **來源摘要**: docs/GAP3_EVENT_TODO.md#df04bdabf37d [P2；信心 10/10] 修法：先取得 SPEC/TODO amendment 後保留三出口，或在核准設計內收斂成一個 sanctioned aggregate factory；不得以 runtime 合理性倒推白名單已放行。RECHECK：白名單 diff／factory symbol count 與 amendment stamp 一致。
## CODEX-R1-P2-06
**斷言**: BOM 與簡單引號由 `_csv_header` 處理，但 `looks_new_schema` 以大小寫敏感 exact set 偵測；`Event_ID,T0,Label` 投舊 `/case/import` 不會走 `new_schema_on_legacy_endpoint` migration 分支，會落入舊 importer 的 generic missing-column/錯誤回應，未達明確新 schema migration 語意。 **碼證**: `api/routes/case.py:121-129`、`api/services/case_import_service.py:630-636`、`282-299`；`rg -n "utf-8-sig|strip\(\).*strip|looks_new_schema|Missing required columns" api/routes/case.py api/services/case_import_service.py` → BOM/quote 處理與 case-sensitive marker、舊 generic error 同時存在。 **來源摘要**: api/routes/case.py#8a2077c8bc29 [P2；信心 9/10] 修法：用 CSV parser canonicalize trim/BOM/quote/lowercase 後先判 new-schema marker，保證所有大小寫變體在舊端點都回 migration 400；RECHECK：新增 BOM／quoted／`Event_ID`／混合欄 CSV 與 JSON old-schema cases，逐一驗 HTTP status/kind/reason。
ASSUMPTIONS_VERIFIED: `48f722b7..HEAD` 變更與 brief/SPEC/TODO 對讀；R1–R7 靜態 import 檢查無 momentum→api 新違規；bars_source 僅讀真實 HDF5 bars，不改事件契約佈局；W10 receipt 三欄存在；`not_computed` 原因由後端提供且前端測試顯示非空；未修改 code、tests、SPEC/TODO、HANDOFF.md 或 data_cache。
TESTS_RUN: `venv/bin/python -m pytest tests/api/ -q -k gap3_import` → 9 passed/477 deselected rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 228 passed rc=0；`cd frontend && npx vitest run gap3` → 3 files/13 passed rc=0；`bash scripts/plain_docs_sync_check.sh` → rc=2；build 未重跑，已讀主委 receipt `handoffs/run_receipts/20260821T213000Z-gap3-b5-gate.log` 所載 build rc=0。
FAILURES_SEEN: plain-docs gate 目前 rc=2；一次唯讀 legacy probe 因匯入 `api.routes.case` 觸發 Binance DNS/network 初始化而 rc=1，未把該 probe 當通過證據；無修碼迭代。
SCOPE_CHANGES: none；只新增 `handoffs/20260821-gap3-b5-review-r1-codex.md`，未改任何程式或測試；產出路徑已列於本檔。
NUMERIC_OR_SCHEMA_IMPACT: none by reviewer；未改數值、API schema、輸出大小或既有斷言，僅指出現行 provenance／wiring／UAT 缺口。
STATUS: DONE
## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對 brief 必答 1–10 與 assumed 四條後，無需阻擋 stamp／使用者 UAT 的 P0/P1 finding；B5.1 legacy/R7/解耦、B5.2 三欄 wiring、W9/W10 均對齊 TODO／Gate receipt。

**碼證**: `venv/bin/python -m pytest tests/api/test_gap3_import.py -q` → 9 passed rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 228 passed rc=0；`cd frontend && npx vitest run gap3` → 13 passed rc=0。程式對讀：`case_import_service.py:608-741`（R7 透傳）、`case.py:87-93,121-129`（legacy 首列偵測 utf-8-sig）、`eventExport.ts:57-100`（匯出形狀）、`EventTablesPanel.tsx:13-18,73-80`（not_computed reason 顯示）、`api.ts:1042-1047`（ms→秒）。探針：BOM CSV `pd.read_csv` 欄名仍為 `event_id`（非 silent coerce）；大小寫變體 `Event_ID/T0/Label` ⇒ `looks_legacy/new_schema` 皆 False → validator `unknown_field`（422），非靜默轉換。`handoffs/run_receipts/gap3_import_scale.json` 含 `n_events`／`wall_clock_s`／`peak_rss_mb`。

**來源摘要**: handoffs/20260821-gap3-b5-review-brief.md#d773c7989a5e；docs/GAP3_UAT_CHECKLIST.md#90d8356bd603

---

## GROK-R1-P0-01

**斷言**: HEAD 上 B5 Gate 命令 `bash scripts/plain_docs_sync_check.sh` 仍 rc≠0，與 brief fact-verified「plain_docs 綠」及「可依 Gate 收斂」矛盾；在修好前不得 stamp。

**碼證**: 本輪執行 `bash scripts/plain_docs_sync_check.sh` → **rc=2**；stdout：`ERROR: 白話說明/GAP-3事件型討論.md 含批次進度，但其 WATCHED 不含 scripts/`；`[plain_docs_sync] ✗ 過期: 白話說明/IC健檢偵察結果.md`。cited receipt `handoffs/run_receipts/20260821T213000Z-gap3-b5-gate.log` 末行亦 `rc_plain_docs_sync=2`（與「綠」宣稱直接衝突）。`RECHECK: bash scripts/plain_docs_sync_check.sh` 須 rc=0。

**來源摘要**: handoffs/20260821-gap3-b5-review-brief.md#d773c7989a5e；handoffs/run_receipts/20260821T213000Z-gap3-b5-gate.log#5edd3eda64c1；docs/GAP3_EVENT_TODO.md#df04bdabf37d

正文：[BLOCKING] 信心度=High。Gate 清單含 plain_docs；紅則整批 Gate 未過。修法：①從 `GAP-3事件型討論.md` 移出批次進度（或納入 scripts/ WATCHED）；②同步 `IC健檢偵察結果.md` 或調整 WATCHED；③重跑 Gate 並更新 receipt 後再派 stamp。IC 健檢檔可能為既有債，但仍擋本批 Gate 宣稱。

## GROK-R1-P1-01

**斷言**: B5.2 已上線事件匯入／picker／兩表，但 `frontend/src/lib/pendingFeatures.ts` 仍保留 `registryId: 'GAP-3 開發前討論題'`（「先討論再開工／待 SPEC」），違反本批 pendingFeatures 防漂移義務。

**碼證**: `pendingFeatures.ts:73-80` 仍寫 suggestedPhase＝「SPEC 定版後之前端批」、location＝「待 SPEC」。B5.2 diff **未**改此檔（`git diff 4b531036..eb3f9b4e -- frontend/src/lib/pendingFeatures.ts` 空）。對照 TODO B5.2／U10 前端已落地。`RECHECK: grep -n 'GAP-3 開發前' frontend/src/lib/pendingFeatures.ts` 應無命中（或改為真實殘留 ID＋三值與 registry 一致）；`npx vitest run pendingFeatures` 綠。

**來源摘要**: frontend/src/lib/pendingFeatures.ts#f2a52d8c6c57；docs/GAP3_EVENT_TODO.md#df04bdabf37d；handoffs/20260821-gap3-b5-review-brief.md#d773c7989a5e

正文：[MAJOR] 信心度=High。防漂移 registry 留下過期「開發前」條目＝使用者仍被指引去不存在的待辦。修法：移除或改寫為 B5 後真實殘留（如辨別表分數來源／條件 IC label_value），並與 `IC_QUANT_GAP_REGISTRY.md` 同步。

## GROK-R1-P1-02

**斷言**: UAT 自述流程「匯入→對齊→三表→全 K 線→報告」在 B 段未被逐項覆蓋——缺「條件 IC（第三張表）」與「全 K 線」驗收步驟；且 `/search` 匯出不寫 `label_value`，事件模式跑 IC 時條件 IC 必 `unavailable:missing_label_value`。

**碼證**: `docs/GAP3_UAT_CHECKLIST.md` 開頭流程句 vs B1–B11：B8＝事件獨有兩表、B9＝IC metadata `event_filter.mode=timestamps`，**無**條件 IC 節／`evaluate_all_bars`／全 K 線產物步驟。`frontend/src/lib/eventExport.ts:77-98` 組出的記錄無 `label_value`；`CaseData.price_change` 存在於 `types.ts` 卻未映射。契約／B2.3：缺 `label_value` ⇒ `missing_label_value`。`RECHECK:` 讀 checklist B 段確認無「條件 IC」「全 K／evaluate_all_bars」列；對一筆含正反例之 search 匯出 JSON `jq '.[0].label_value // .records[0].label_value'` 為 null。

**來源摘要**: docs/GAP3_UAT_CHECKLIST.md#90d8356bd603；frontend/src/lib/eventExport.ts#aea0be5ede7f；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；docs/GAP3_EVENT_TODO.md#df04bdabf37d

正文：[MAJOR] 信心度=High。會怎麼失敗：使用者依 B 段簽字後仍未驗第三張表與 U11 靈魂路徑；匯出→匯入→IC 的條件 IC 恆 unavailable，易被當成「壞了」或被 UAT 靜默跳過。修法：①B 段加步驟：事件模式報告中條件 IC 節之 capability／reason（若故意不接 label_value，改明示殘留＋pendingFeatures）；②加全 K 線步驟（呼叫點／畫面／命令，對齊 B2.5／B3.2 G6 既有能力）；③匯出映射 `label_value: case.price_change`（或文件化不支援並入 registry，禁止空話「三表」）。

## GROK-R1-P1-03

**斷言**: Frozen TODO 白名單 §0-6-⑦／B5.1「修改檔案」只授權 `momentum/factories.py` 新增 **一個** `create_event_sample_pipeline()` 出口；實作另增 `create_event_import_contract`／`create_condition_engine_contract`，字面越權。

**碼證**: `docs/GAP3_EVENT_TODO.md` §0-6-⑦ 原文「一個出口」；B5.1「`momentum/factories.py`（一個出口）」；`momentum/factories.py:837-855` 三個 `def create_event_*`／`create_condition_*`。R3 動機成立（API 不得直 import contract 載入器），但替代作法＝單一 facade／pipeline 附帶 contract 唯讀屬性，仍可維持「一個出口」。`RECHECK: grep -n '^def create_event\|^def create_condition' momentum/factories.py` 應為 1（或 TODO D-延伸改白名單後＝3 並有 stamp 引用）。

**來源摘要**: docs/GAP3_EVENT_TODO.md#df04bdabf37d；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；momentum/factories.py#61898b3fa0a1

正文：[MAJOR] 信心度=High（字面）；正確性風險低。不破壞解耦，但 stamp 若宣稱「遵守白名單」會假綠。修法：D-延伸把⑦改為「pipeline 出口＋契約唯讀出口（R3）」或合併為一個 factory 回傳物件；補進 TODO／SPEC pointer 後再 stamp。

## GROK-R1-P2-01

**斷言**: brief／B5.2 commit message 宣稱 `tests/api` `-k gap3_import` **13** 條，HEAD 實為 **9** 條（功能通過、計數漂移）。

**碼證**: `venv/bin/python -m pytest tests/api/ -q -k gap3_import` → **9 passed**（本輪）；receipt 同「9 selected」；`grep -c '^def test_' tests/api/test_gap3_import.py` → 9。commit `eb3f9b4e` 訊息寫「gap3_import 13」。`RECHECK:` 同上 pytest 計數。

**來源摘要**: tests/api/test_gap3_import.py#a004c2362cf1；handoffs/run_receipts/20260821T213000Z-gap3-b5-gate.log#5edd3eda64c1；handoffs/20260821-gap3-b5-review-brief.md#d773c7989a5e

正文：[MINOR] 信心度=High。不影響行為；污染 Gate 敘事與跨 agent 驗收。修法：更正 brief／看板／後續 commit 敘事為 9（或補測至 13 並更新 receipt）。

## GROK-R1-P2-02

**斷言**: `EventAnalyzeResponse.event_timestamps` 回傳對齊成功事件之 t0 **毫秒**，但 Field description 寫「供 /ic-analysis 事件模式帶入」——IC 主線需要 **秒**；現行前端走 picker 換算故未炸，API 契約文案是踩雷。

**碼證**: `api/models/event_import_models.py:94` description；`case_import_service.py:799` `res.events["t0"]`（契約 t0＝ms）；`frontend/src/lib/api.ts:1043-1047` `Math.floor(ms/1000)` 僅用於 `getEventImport` 路徑。若消費者直接把 analyze 回傳 timestamps 塞進 IC ⇒ 錯 1000 倍。`RECHECK:` 讀 model description；對照 analyze 回應值級距 ≥1e12。

**來源摘要**: api/models/event_import_models.py#7bef541b10cc；api/services/case_import_service.py#a3946367fb97；frontend/src/lib/api.ts#a70a519560b7

正文：[MINOR] 信心度=High。修法：description 改為「t0 epoch ms（非 IC 秒；IC 請經 eventT0MsToIcTimestamps）」或分析端點改回傳秒並改測試／前端一致。

