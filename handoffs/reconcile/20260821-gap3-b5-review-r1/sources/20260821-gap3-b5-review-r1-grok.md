# GAP-3 B5 review R1 — grok

task-id: 20260821-GAP3-B5-REVIEW-R1
family: grok
brief-kind: review
brief: handoffs/20260821-gap3-b5-review-brief.md
diff: `git diff 48f722b7..HEAD`（B5.1 `4b531036` + B5.2 `eb3f9b4e`）
gate receipt cited: handoffs/run_receipts/20260821T213000Z-gap3-b5-gate.log

## Verdict：需修補後才能 stamp／交使用者 UAT

有 **1×P0 + 3×P1 + 2×P2**。B5.1 核心接線（legacy 拒收、契約透傳、ms→秒橋接、兩表 reason 顯示、規模 receipt 三欄）大多成立；但 brief 宣稱的 B5 Gate「全綠」與 HEAD 實況不符（`plain_docs_sync` 紅），且 B5.2 `pendingFeatures` 防漂移／UAT「三表＋全 K 線」覆蓋／factories 白名單字面均有缺口。**不可進 RECONCILE-STAMP；不可交使用者當完整 UAT。**

### 必答（逐條）

1. **逐 Task 對 TODO**
   - **B5.1**：pipeline 組合殼＋`/case/import-events[+ /json]`＋legacy adapter＋規模 receipt＋`allowed_filtering_params` 改讀契約 —— **大致符合**；白名單⑦「一個出口」被加到三個 `create_*`（見 P1-03）。API 測試實為 **9** 條（非 brief/commit 所稱 13；見 P2-01）。
   - **B5.2**：三頁升級、事件模式 picker、兩表只在事件模式、vitest gap3 3 檔 13 passed（本輪複驗 rc=0）—— **UI 主路徑成立**；`pendingFeatures` 仍掛「開發前討論題」（P1-01）；匯出缺 `label_value` 使條件 IC 端到端空洞（併入 P1-02）。
   - **B5.3**：checklist 已起草；A 段 rc 空白、B 段缺「條件 IC／全 K 線」步驟、C 段三殘留尚未寫入 registry —— **未完成**（預期，但不可假裝可簽字）。

2. **R7／契約單一真相源**：**大致成立**。`EventImportService` 經 `create_event_sample_pipeline().validate` 透傳 failures；`test_gap3_import_contract_reasons_passthrough_not_reimplemented` 掃契約 reason 字面不在 API GAP-3 段＋failures ⊆ 契約集合。字串掃描可被「改寫 reason 但不寫死字面」繞過，但現碼無此路徑；攻擊不升格 finding。`looks_legacy`／`looks_new_schema` 只看鍵名。

3. **legacy adapter**：**成立（測試覆蓋主路徑）**。舊三欄→新端點 400＋`migration_hint`；新 schema CSV→舊端點 400；混合欄 422 逐列 reason；JSON 舊三欄亦拒。`_csv_header` 用 `utf-8-sig`＋去引號。大小寫變體 `Event_ID` 不會被 `looks_new_schema`（大小寫敏感）攔下——舊端點會走缺欄錯誤而非 `new_schema_on_legacy_endpoint`；非 silent coerce，記觀察不升格。

4. **`source_file_digest`**：**裁量與契約一致（攻擊不推翻）**。契約 doc＝來源檔 sha256；`verify_source_digest` 預設 False；另記 `upload_sha256`。上傳檔不可能含自己的 hash——預設關閉對證合理。

5. **解耦 R1–R7**：`api/` 經 factories；brief 稱 baseline 無新增——本輪未重跑 decoupling scanner（引 brief／不受理重審解耦基建）。**`bars_source` 綁 kline h5 佈局＝bars 來源適配器，非事件契約欄位**——裁為不違反「事件契約不綁 HDF5」；事件契約仍只綁 symbol/tf/bar 邊界語意。

6. **分析端點**：`analyze`→`run_with_params`＋`event_forward_return_table`；辨別表 `not_computed`＋`no_model_scores_in_event_pipeline`。reason **非** `capability_unavailable_reasons` 枚舉，但是顯式揭露；vitest 鎖前端顯示 reason。**可接受**（assumed 攻擊不推翻），前提＝殘留入 registry（UAT C 已列、B5.3 尚未寫入）。

7. **前端 wiring 三欄**：
   - `/search` 匯出：必填欄齊；`source_file_digest` 64 hex（瀏覽器 subtle；jsdom FNV 退路仍 64 hex 過格式閘）；`timeframe` 有 fallback。**會過 validator 格式**（正＋反例齊時）；缺 `label_value` 不擋匯入但擋條件 IC（P1-02）。
   - `/ic-analysis`：`eventT0MsToIcTimestamps`＝`floor(ms/1000)`；vitest 鎖。兩表只在 `mode==='event'`；unavailable／not_computed 顯示 reason；empty/loading/error 三態有。
   - **腳注**：`EventAnalyzeResponse.event_timestamps` 實為 ms，description 卻寫供 IC 帶入（IC 要秒）——picker 路徑正確，API 文案踩雷（P2-02）。

8. **規模 receipt（W10）**：**成立**。`gap3_import_scale.json`：`n_events=10000`、`wall_clock_s=76.377`、`peak_rss_mb=305.1`。73s 對齊為記錄型；UAT C 已列殘留意向——可。

9. **UAT checklist（W9）**：A 段命令可跑；**B 段未覆蓋「第三張表（條件 IC）」與「全 K 線」**（P1-02）。B8 只驗事件獨有兩表；B9 只驗 IC metadata `event_filter.mode`，未點名條件 IC 節／`evaluate_all_bars` 產物。

10. **可進 stamp／交使用者 UAT？**：**否**。先修 P0（plain_docs Gate）＋至少處理 P1-01／P1-02 checklist＋label_value／殘留登記策略；P1-03 以 D-延伸或合併 facade 追認。

### §0 前提攻擊（brief assumed／fact-verified）

| 前提 | 判定 | 證據 |
|---|---|---|
| fact-verified: B5 Gate 全綠（含 plain_docs） | **推翻** | 本輪 `bash scripts/plain_docs_sync_check.sh` → **rc=2**（`GAP-3事件型討論.md` ERROR＋`IC健檢偵察結果.md` 過期）；cited receipt 尾亦 `rc_plain_docs_sync=2`。P0-01。 |
| fact-verified: api gap3_import 13 passed | **推翻（計數）** | 本輪 `-k gap3_import` → **9 passed**；receipt 同為 9 selected。功能綠、數字漂。P2-01。 |
| fact-verified: vitest gap3 13／event_samples 等 | **本輪 vitest 成立**；event_samples 引 receipt 228 passed（brief 寫 232——輕微計數漂，不另開 finding） | `npx vitest run gap3` → 3 files／13 tests rc=0 |
| assumed: factories 三出口不違反「一個出口」 | **字面推翻** | TODO §0-6-⑦／B5.1 修改檔案欄皆寫一個出口；`factories.py:837-855` 三函式。P1-03。 |
| assumed: 辨別表 `not_computed` 正確揭露 | **成立** | pipeline.py:89-91；vitest 鎖 reason；UAT C 列殘留。非以 UAT 遮蔽未驗收——前提是 B5.3 真寫入 registry。 |
| assumed: `horizon_bars` 預設 2 為範本、UAT B2 明示 | **弱成立** | export note＋UAT B2 列欄位；B2 **未**強制核對 horizon 數值＝搜尋答案窗。不升格。 |
| assumed: `data_cache/events/` 不進 cases.json | **成立** | EventImportService docstring＋落檔路徑；TODO 舊檔不遷移。 |

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

## 被當成事實的未驗證假設（§0）

見上表；另：event_samples「232」vs receipt「228」計數輕漂——不另開 finding，建議敘事對齊 receipt。

ASSUMPTIONS_VERIFIED: legacy 拒收主路徑；契約 reason 透傳；ms→秒 vitest；規模 receipt 三欄；辨別表 not_computed 揭露；source_digest 預設不對證上傳；events/ 獨立落檔；plain_docs 於 HEAD 紅（推翻 brief 綠）；gap3_import=9（推翻 13）；factories=3 出口（推翻「一個」字面）；匯出無 label_value；UAT B 缺條件 IC／全 K 線；pendingFeatures 開發前條目仍在
TESTS_RUN: `venv/bin/python -m pytest tests/api/ -q -k gap3_import` → 9 passed rc=0；`cd frontend && npx vitest run gap3` → 3 files／13 tests rc=0；`bash scripts/plain_docs_sync_check.sh` → rc=2（見 P0-01）。event_samples／npm build／golden 本輪未並行重跑（brief：build 只准一家；golden 勿重跑）——引 receipt／commit 敘事並標未複驗全套
FAILURES_SEEN: none（review-only）
SCOPE_CHANGES: none（禁改碼）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260821-gap3-b5-review-r1-grok.md

STATUS: DONE
