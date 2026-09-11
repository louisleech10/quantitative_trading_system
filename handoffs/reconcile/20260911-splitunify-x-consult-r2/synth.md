# Reconcile — 20260911-splitunify-x-consult-r2

**來源** 20260911-splitunify-x-consult-r2-codex.md, 20260911-splitunify-x-consult-r2-composer.md, 20260911-splitunify-x-consult-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.md

**Verdict**：需修補後合併——18 條（codex 8 全 P1／composer 6／grok 4 含 1 BLOCKING）：**15 採納、1 部分採納、2 駁回**。三家對 D1 程序類別分歧（codex＝R、grok＝爭議預設 R、composer＝D）⇒ 依凍結程序明文「爭議一律預設 R」採 **R 重開**。主委初判有兩處被三家共同否證（見 U1、U6），已更正。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **U1 R-1 hash scope 只答一半**——「R-1不能以「`_base_univer」 | P1 | CODEX-R1-P1-01 | 採納（主委初判被否證：生產路徑實際用整框 joint hash） |
| U1 同題——「R-1的needs-research理由」 | P1 | COMPOSER-R2-P1-01 | 採納（needs-research 收回，改列為實作項） |
| U1 同題——「主委「`_base_universe_h」 | P2 | GROK-R1-P2-01 | 採納（不變式改寫：同 symbol 之 train/test hash 一致；跨 symbol 允許共用 joint hash；事件 symbol 必匹配 plan.symbol；逐 symbol 各自同源對證。禁把「跨 symbol hash 必互異」寫成閘，否則拒收現行 IC 多標的計畫） |
| **U2 R-5 scalar ref 不足以指定 universe**——「R-5的選填scalar`feature」 | P1 | CODEX-R1-P1-02 | 採納（改為 per-symbol／per-TF ref manifest：path＋config_hash＋post-trim row-time digest；缺任一對應即 fail-closed 並保留 event-study-only） |
| U2 同題——「R-5收窄為選填`features_re」 | P1 | COMPOSER-R2-P1-02 | 採納（capability 增 `split=ok` 分支與前端對稱處理，否則有 universe 仍顯示「沒切分」） |
| U2 同題——「「`features_ref`選填、前端」 | P2 | GROK-R1-P2-03 | 採納（scope 寫死：本票交付 API 能力＋前端最小入口；**禁 auto-discover**，唯顯式 ref 才走 OOS） |
| **U3 SU-RESID-3 採完整逐列指紋**——「SU-RESID-3應採producer」 | P1 | CODEX-R1-P1-03 | 採納（producer-attested、固定排序、epoch-ms、含 symbol scope 與 provenance；negative case 須證明改中間一列會紅） |
| U3 反面立場——「SU-RESID-3在b9應採「首尾對證」 | P1 | COMPOSER-R2-P1-03 | 駁回（2 比 1；理由：R-5 接通後「同端點、中間間距不同」是具體錯分面而非理論。既有 golden digest 位移屬可記錄、可重凍之數值影響，不足以把已知身分缺口永久合理化） |
| **U4 SU-RESID-2 走 additive 加欄**——「SU-RESID-2的複合鍵不會必然使既」 | P1 | CODEX-R1-P1-04 | 採納（保留 `event_id` 事件身分、加 `timeframe` 欄；既有五組 golden 不重凍，另加多 TF 組） |
| U4 同題——「SU-RESID-2收案時若只改鍵、不新」 | P2 | COMPOSER-R2-P2-03 | 採納（不新增多 TF golden ⇒ 舊組仍綠但新路徑假綠） |
| **U5 SU-RESID-2 下游單鍵面**——「SU-RESID-2不能只改produc」 | P1 | CODEX-R1-P1-08 | 採納（`feature_materialization`／`baseline`／`pattern_bridge`／`tables`／`ic_feed` 逐處處理；未全面改前，多 TF 同批一律 fail-closed） |
| **U6 D1 須走 R 重開**——「D1從事件掃描端「恆走event-stu」 | P1 | CODEX-R1-P1-05 | 採納（主委初判「不推翻、可 D」被否證） |
| U6 同題 BLOCKING——「將D1「事件掃描端恆走event-stu」 | P1 | GROK-R1-P1-01 | 採納（「恆」字與條件式字面互斥；先完成 R 重審重戳才有合法的 R-5 基線） |
| U6 反面立場——「D1條件式重寫應走**D延伸**（`SP」 | P2 | COMPOSER-R2-P2-01 | 駁回（凍結程序明文：與原檔互斥者非 D、爭議一律預設 R。D1 裁定住在已三家戳記之共識檔，hash 已凍） |
| **U7 批次依賴**——「主委批次依賴不完整；R-5除R-1／SU」 | P1 | CODEX-R1-P1-06 | 採納（採保守序：b8＝R-1＋SU-RESID-3；b9＝SU-RESID-2＋下游；D1 走 R 重開重戳；b10＝R-5。R-5 不得與未完成之 D1 同批上線） |
| U7 同題——「主委批次`b9=SU-RESID-2＋S」 | P2 | GROK-R1-P2-02 | 採納（SU-RESID-2 不在 R-5 的 fail-closed 依賴鏈上，移出前置） |
| U7 反面——「批次依賴應為**b8（R-1＋SU-RE」 | P2 | COMPOSER-R2-P2-02 | 部分採納（採其「R-5 依賴 R-1＋SU-RESID-3」之判斷；不採其把 SU-RESID-2 併入 b8） |
| **U8 per-symbol 門檻失效**——「R-1接通多symbol後，projec」 | P1 | CODEX-R1-P1-07 | 採納（與主委自查同題；`split_projection.py:569` 之條件與迴圈變數無關，用整批 `n_test`。須由 assignments 導出 per-symbol test counts，並配「一標的低於門檻但總數高於門檻」之負例） |

### 本輪程序記錄（含主委自查與摩擦）

1. **主委初判被否證兩處**：①R-1「唯一性已定義、只差傳遞」——三家一致指出 `ICSplitAdapter._base_universe_hash(frame,…)`（`ic_split_adapter.py:189-199`）對整框算一份 hash 並打進每個 symbol 的 plan（`ic_filter_orchestrator.py:907`），**跨 symbol 共用同一字面 hash 是合法且已發生**；②D1 改條件式可走 D 延伸——兩家判 R。
2. **主委自查三條**（`RECON-claude.md §6b`，非委員提出）：`dedupe.py:124-127` 之 `cluster_first` 以 `dedupe_cluster_id` 取最早一列，多 TF 複合鍵下同事件不同 TF 若落同簇會被折疊（併入 U5 處理）；`test_splitunify_derive.py:537` 之「`single_symbol` 恆亮是預期的」在 R-1 後變假前提，解除條件須寫死為「僅 `n_symbols > 1` 才解除」並配 mutation；`insufficient_events_in_test` 之 bug 與 U8 同題。
3. **摩擦（本輪實測，供白話摩擦記錄）**：①brief 前提行寫成全形冒號 ⇒ 產出端 `doc_format_precheck` 當場擋下，訊息直接給出正確格式，一次修好（成本低、擋得對）。②grok 把 findings 寫成 `###` 三級標題，而 `reconcile_build` 抽取器只認 `##` ⇒ 抽到 0 條、硬閘擋在 `GROK-R1-P1-01`；**委員端沒有產出端 hook，要到主委收斂才炸**，且修正後因 sources 複本 sha 變動需整個 session 重建（`--rebuild` 只升級 mode、不重算 sha；`rm` 被拒 ⇒ 改以改名保留舊骨架）。③主委對 `docs/*.md` 直接跑 `reconcile_stamps_check` 得 rc=1 就誤判「治理真空」——本 repo 戳記一律外置於 reconcile synth，對 synth 跑才是正確用法（rc=0）。④主委把 `echo rc=$?` 放在 pipe 之後，讀到的是 `tail` 的 rc，CLAUDE.md 已具名之坑再犯一次。
4. **查證但不開新殘留**：`lgb_cv_universe`／`xgb_cv_universe`（`lightgbm_analyzer.py:377`／`xgboost_analyzer.py:1162`）未流入 `derive_event_split_from_plans`（三家與主委各自 grep 一致）；R-5 接線時須明文拒絕模型 CV hash 充當事件 canonical universe provenance。
5. **`FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` 檔頭仍寫「狀態：草案，尚未生效」**，但其戳記檔 rc=0、三家 APPROVED，且 commit `d45f29be` 標題為「v2.0 定案生效」⇒ 檔頭為過期行。本輪不改（它自身是程序檔，改它須依其程序），登記於此供下一張治理票處理。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01

**斷言**: R-1 不能以「`_base_universe_hash` 含 symbol，所以 per-symbol 唯一性已定義」結案；現行 `split_per_symbol` 的實際 caller 會把同一個全 frame hash 寫進各 symbol plan。

**碼證**: `ic_split_adapter.py:195-199` 對整個 frame 的 `symbol/time/row_pos` hash；`ic_filter_orchestrator.py:905-933` 先算一次 `base_hash` 再傳給 `split_per_symbol`；`contracts.py:635,671,683` 的單一參數被原樣寫入每個 symbol 的 train/test plan。`_normalize_symbol_value`（`contracts.py:430-454`）只 trim／解碼／拒絕 sentinel，不做 uppercase。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#4b1b8bc9f22a；momentum/Analysis/ic_split_adapter.py#c2dd93482826；momentum/core/contracts.py#642aecf26b32

[P1] 信心度=High。`_base_universe_hash(index, symbol)`（`ic_filter_orchestrator.py:517-530`）確實對單一 symbol 的 index 含 symbol、timestamp、row position；但 `ICSplitAdapter._base_universe_hash(frame, ...)` 是全 frame identity，故跨 symbol 共用同一字面 hash 是合法且目前已發生的 hash scope，不是碰撞。另有 trim／bytes 解碼後的別名會被視為同一 canonical symbol；這不是兩個真正標的的碰撞。R-1 實作前須明定 hash 是全 frame identity 還是每 symbol identity，並讓 per-symbol map 另帶可驗證的 symbol-local row-time identity；不可只用「hash 不同」作前提。若不修，後續 map 可能把合法 shared hash 誤當 collision，或把同字面不同網格誤當同源。

## CODEX-R1-P1-02

**斷言**: R-5 的選填 scalar `features_ref{features_path, config_hash}` 只能保留 None 的相容舊路徑，不能避開 API／契約／前端／UAT，也不足以唯一指定多 symbol、多 TF 的 post-trim universe。

**碼證**: `EventAnalyzeRequest` 現在只有 `horizons/n_boot/seed/test_fraction/embargo_ms/tier_min_test_events`（`api/models/event_import_models.py:295-303`）；route 使用該 request（`api/routes/case.py:487-496`），service 目前明示只拿事件與 bars、恆走 event-study-only（`case_import_service.py:1570-1608`）。而 pipeline 的 canonical projection 必須同時給 `train_plan/test_plan/feature_index/selected_timeframe`（`pipeline.py:711-748`），不是只給一個檔案路徑。`analyzeEventImport` 的 body 是 inline shape（`frontend/src/lib/api.ts:1119-1129`），`EventTablesPanel.tsx:301-303` 只送 horizons。真實讀取命令：`venv/bin/python -c "import glob, pandas as pd; ... read_parquet(...)"` → 14 個 timestamps parquet；ETHUSDT 12h 長度為 353/1454/1696，ETHUSDT 1h 為 10441/18937/20352。

**來源摘要**: api/models/event_import_models.py#82c83da611f5；api/services/case_import_service.py#d2571793953f；frontend/src/lib/api.ts#4a54c9918781；frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a；momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2

[P1] 信心度=High。None 分支可維持 backward compatibility，但「可選 ref」要成為可用功能仍需新增 request model／TS request type、契約欄位、精確的 per-symbol/per-TF run binding、canonical boundary 產生與 UAT。scalar path/hash 沒有表達每個 symbol/TF 的 config、post-trim row index、split policy 與 provenance；錯綁時可能產生看似合法但不屬於事件批的 OOS。反面是現有 UI 已能把 None 分支的 unavailable reason 與 full-sample scope 顯示出來（`EventTablesPanel.tsx:348-378`），所以不改 UI 仍可保留舊狀態；但 API-only 的 available 分支不會告訴使用者用了哪個 universe/boundary，故不能宣稱畫面完整可解釋。建議以 per-symbol/timeframe ref manifest（含 path/config_hash/post-trim row-time digest）為輸入；缺任何對應即 fail-closed 並保留 event-study-only。

## CODEX-R1-P1-03

**斷言**: SU-RESID-3 應採 producer-attested 的完整、有序 `row_time_fingerprint`；把首尾對證列為永久誠實邊界會保留可通過而錯分的同端點／中間間距攻擊。

**碼證**: 現行同源對證只比每段首尾（`split_projection.py:464-484`）；TODO §E 也明載「首尾相同、僅中間間距不同仍會通過」（`SPLITUNIFY_TODO.md:472`）。`SplitPlan` 現行欄位只有 `time_bounds`、`row_index`、`base_universe_hash` 等，沒有 row-time fingerprint（`contracts.py:377-403`）。SPEC §G 的 row fingerprint 已把 `(position, feature_ts_ms, symbol, base_universe_hash)` 作為 exact sha256 對證（`SPLITUNIFY_SPEC.md:310-325`）。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#98ee62905643；momentum/core/contracts.py#642aecf26b32；docs/SPLITUNIFY_TODO.md#e44da6448b01；docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[P1] 信心度=High。若不加完整 fingerprint，兩份網格可以共用相同首尾但在中間插洞／變頻，`row_index` 仍會指向不同時刻；R-5 接通後會把錯誤列歸屬當成 canonical OOS。未選方案最強的理由是它會動 `SplitPlan`／IC contract、時間單位正規化與既有 golden digest，成本高且可能使既有 IC digest 位移；但這是可記錄、可重凍的數值影響，不足以把已知資料身分缺口永久合理化。指紋 payload 必須固定排序、epoch ms、symbol scope 與 producer provenance，並由改前後 golden exact 驗證；不可只加一個未定義 hash 欄。

## CODEX-R1-P1-04

**斷言**: SU-RESID-2 的複合鍵不會必然使既有五組 golden 全部重算；正確做法是保持單 TF fixture 的既有 event-ID 結果，另加 multi-TF golden，否則不改 golden 反而會對新情境假綠。

**碼證**: `build_event_keys` 現在只取 `selected_timeframe` 且要求每事件恰一列（`split_projection.py:270-301`）。golden 產生器 fixture 全部固定 `SYM="ETHUSDT"`、`timeframe="1h"`，G-1/G-3b 只擷取 event_id、G-4 是 per-symbol count、G-5 是 row fingerprint（`scripts/freeze_splitunify_golden.py:52-90,140-180`）；測試也明確以 `set(event_id)` 驗三態互斥總集（`tests/momentum/Analysis/test_splitunify_golden.py:146-152`）。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#98ee62905643；scripts/freeze_splitunify_golden.py#6fb0c7361dad；tests/golden/splitunify/splitunify_golden.json#f270e007ca98；tests/momentum/Analysis/test_splitunify_golden.py#006b7bd2d41e

[P1] 信心度=High。若 assignments 只增加 `timeframe` 欄、保留 `event_id` 事件身分，既有單 TF golden 的成員、計數、row fingerprint 仍應維持；新增一組 `(event_id,timeframe)` 重複事件 fixture 才能驗新語意。反面是完全不重算／不新增 golden 時，舊測試的 `set(event_id)` 會把兩個 TF 壓成一個事件，無法發現漏列或錯列；若改成直接把 event_id 換成 tuple，則才會擴散到五組 golden 及所有下游，這不是必要且會摧毀現有單 TF 回歸錨點。驗收應保留舊 golden、增加 TF-qualified membership／count oracle，並明確記錄 schema additive change。

## CODEX-R1-P1-05

**斷言**: D1 從事件掃描端「恆走 event-study-only」改成「拿不到 universe 才走」是改變既有設計語意，須走凍結程序 R（重開），不是 D 延伸。

**碼證**: SPEC C-0 決議③把無 canonical universe 的匯入流程鎖為 event-study-only，且 C-0 同時寫事件掃描路徑本票不傳 universe、R-5 留待日後（`SPLITUNIFY_SPEC.md:72-93`）；現行 TODO §E 仍以此作 R-5 理由（`SPLITUNIFY_TODO.md:469`），SPEC §N 也寫事件端恆走 event-study-only（`SPLITUNIFY_SPEC.md:685-688`）。程序 v2 §2.1 明定 D 不推翻設計、R 是既有設計被證偽，爭議預設 R。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#3e39458b00e4；docs/SPLITUNIFY_TODO.md#e44da6448b01；docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md#176c58e0c914

[P1] 信心度=High。條件式確實保留「沒有 universe 就不可宣稱 OOS」這條 C-0 原則，但它仍改變「事件掃描端恆無 available 分支」的既有範圍，並使已戳記的 D1 文字不再逐字成立。反面是若新增的是完全不同 endpoint／明確新模式，而原 endpoint 仍恆 event-study-only，則可論為 D；主委方案是在同一事件分析能力上引入 universe，不能用這個反面包裝成 D。先完成 R 的完整重審與重戳，才有合法的 R-5 實作基線。

## CODEX-R1-P1-06

**斷言**: 主委批次依賴不完整；R-5 除 R-1／SU-RESID-3 外，若要支援多 TF 還依賴 SU-RESID-2，且 D1 的 R 程序必須先於行為實作。

**碼證**: projection 介面要求 `selected_timeframe` 與單一 train/test plan（`pipeline.py:711-748`），`build_event_keys` 對每個 selected TF 只接受一列（`split_projection.py:270-287`）；TODO §E 明載 R-5 會碰 request/frontend/contract/UAT，SU-RESID-2 會牽動 EventSplitPlan 下游（`SPLITUNIFY_TODO.md:469-470`）。程序 v2 §2.1 的 R 路徑會讓原戳記失效，故不能先接行為再補文件程序。

**來源摘要**: docs/SPLITUNIFY_TODO.md#e44da6448b01；docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md#176c58e0c914；momentum/Analysis/event_samples/split_projection.py#98ee62905643

[P1] 信心度=High。R-1＋SU-RESID-3 是安全接通的 identity foundation；若 R-5 僅限單一 selected TF，可把 SU-RESID-2 暫時列為明確拒絕範圍，否則不能忽略它。建議安全順序：b8＝R-1＋SU-RESID-3（定義 hash scope/fingerprint）；b9＝SU-RESID-2＋所有 event_id consumer 與新增 multi-TF golden；完成 D1 的 R 重開／重審／重戳；最後 b10＝R-5。若必須減輪次，可把三條 identity work 合併一批，但須在同一批內保持所有未完成形態 fail-closed，且 R-5 不得與未完成的 D1 R 同批上線。

## CODEX-R1-P1-07

**斷言**: R-1 接通多 symbol 後，projection summary 的 `insufficient_events_in_test` 會以 aggregate `n_test` 檢查每個 symbol，可能讓低於門檻的 symbol 被誤報為合格。

**碼證**: `split_projection.py:568-578` 的 `per_symbol_n` 只含各 symbol 總事件數，但 `insufficient = [s for s in per_symbol_n if n_test < tier_min_test_events]` 使用整批 `n_test`；對照舊 `event_split.py:157-159` 是先按 symbol 計算 `n_test` 再逐 symbol 比門檻。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#98ee62905643；momentum/Analysis/event_samples/event_split.py#943d0721b059

[P1] 信心度=High。多 symbol 後若 A 有 1 個 test、B 有 100 個 test、門檻為 10，aggregate=101 會讓 A 不進 insufficient 清單；下游仍可能把這批當可用 OOS。這不是目前單 symbol fail-closed 的現況 bug，而是 R-1 解除閘門後的具體回歸風險。修法是從 assignments 導出 per-symbol test counts、逐一比較，並加一個一標的低於門檻但總數高於門檻的 negative case。

## CODEX-R1-P1-08

**斷言**: SU-RESID-2 不能只改 producer 的 keyed join；現有物化、baseline、pattern、tables 與 IC feed 多處仍以 `event_id` 單鍵，直接輸出重複 `(event_id,timeframe)` 會造成覆蓋、歧義或錯誤計數。

**碼證**: `feature_materialization.py:93,132,138-140` 以 event_id group、set index 並以 `nunique()` 記帳；`baseline.py:105-110`、`pattern_bridge.py:122-126`、`tables.py:214,229,326,372-373` 以 event_id join/index；`ic_feed.py:108-109` 先按單一 timeframe 才以 event_id index。`dedupe.py:46-49` 又會按 `(label_start_ms,event_id)` 重排，不能靠 positional zip。

**來源摘要**: momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f；momentum/Analysis/event_samples/baseline.py#38c7ec473653；momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2；momentum/Analysis/event_samples/tables.py#843ba7f68172；momentum/Analysis/event_samples/ic_feed.py#741f697b39641；momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e

[P1] 信心度=High。多 TF 同一 event_id 若直接流入目前的 `set_index`／`loc`，後者可能覆蓋前者、回 DataFrame 而非單列，或在 `nunique` 記帳中少算；若只在每次呼叫前嚴格切成一個 TF，現行 `ic_feed` 的單 TF filter 可維持，但那就必須把 multi-TF 同批列為 fail-closed。下游要嘛全面採 `(event_id,timeframe)`，要嘛在邊界明確維持 per-TF 分析並禁止複合批；不可只改 golden 欄位。

# 七題逐題答覆

### 1. R-1 研究問題

立場：只部分回答。`_base_universe_hash(index, symbol)` 的單 symbol helper 已把 normalized symbol、timestamp、row position 放入 hash，所以在該 helper 的非空正常輸入下，兩個不同 canonical symbol 不應合法碰撞；但這不等於實際 `split_per_symbol` 的 plan hash 是 per-symbol hash。

正面碼證：`ic_filter_orchestrator.py:517-530` 明確把 symbol 放入 identity；`contracts.py:625-694` 逐 symbol 建 plan 並逐對跑 `validate_split_pair_integrity`。

反面：`ic_split_adapter.py:195-199` 對整個 frame hash，`ic_filter_orchestrator.py:905-933` 算一次再傳給所有 symbol；因此兩 symbol 合法共用同一 hash 的情形存在。`_normalize_symbol_value` 會把 trim／bytes decode 後的同一 canonical 名稱合併，`BTCUSDT` 與 `btc...` 則不會自動合併。結論是先決定 hash scope，再決定 R-1 map 的身份欄，不能把 shared hash 單純當碰撞。

### 2. R-5 收窄案

立場：None 預設可保留 event-study-only，能降低舊 caller 的立即破壞；但不能說因此避開「請求模型／前端／契約／UAT 全動」。

正面碼證：目前 request 沒有 features_ref（`event_import_models.py:295-303`），route/service 的舊流程可繼續不傳；前端只送 horizons（`api.ts:1119-1129`、`EventTablesPanel.tsx:301-303`），不送 ref 時不需改既有呼叫行為。

反面：想讓使用者真的選到 ref，request shape、TS type、契約、run binding、UAT 都要新增；現有 projection 要四個 canonical inputs，不是只收 path/hash。前端已有 unavailable 文案（`EventTablesPanel.tsx:364-378`），所以 None 狀態可解釋；但 available 狀態沒有 ref、authority、boundary hash 的可見 provenance。真實 parquet 長度也不固定，scalar ref 不能代表 per-symbol/per-TF post-trim universe。結論：收窄可作 API 相容策略，不是完整 R-5 方案。

### 3. SU-RESID-3

立場：選完整 producer-attested `row_time_fingerprint`，並接受 IC contract/golden digest 的明示更新。

正面碼證：現行 `split_projection.py:464-484` 只驗每段首尾；TODO §E 明確承認同首尾、不同中間間距仍可過；SPEC §G 已有 exact row fingerprint 的序列化方向。

反面：加欄會動 `SplitPlan`／IC contract、時間單位規約與既有 digest，且若 producer 沒有可信的完整 row sequence，新增 hash 只會把錯誤再次凍結。未選的永久誠實邊界成本低、可清楚揭露「中間未驗」；但它不能滿足 R-5 需要的同源 OOS 身分，故不足以結案。要求 fingerprint 包含 ordered epoch-ms rows、symbol scope、source/config provenance，並由 negative case 證明改中間一列會 fail。

### 4. SU-RESID-2

立場：複合鍵應是 additive schema change；既有單 TF 的五組 golden 不必全部重算，另增 multi-TF golden／oracle。

正面碼證：freeze fixture `scripts/freeze_splitunify_golden.py:75-90` 全是 ETHUSDT/1h；五組輸出中的 g1/g3b event IDs、g4 count、g5 row fingerprint 在單 TF 下可保持相同。

反面：若既有 golden 完全不變且不新增 TF 維度，`test_event_ids_three_states_are_disjoint_and_total` 的 set(event_id) 會把重複 event_id 壓掉；這會讓新 multi-TF 錯列假綠。若把 event_id 本身換成 tuple，則才會迫使五組及全部下游重算，但這是可避免的過度擴散。保留 event_id 事件身分、加 timeframe 欄或明確 keyed identity，並新增至少一個同 event_id 多 timeframe fixture。

### 5. D1 與修訂程序

立場：條件式 D1 是 R，不是 D。C-0「無 universe 不得宣稱 OOS」可保留，但 D1 的「恆」字與條件式 available 分支互斥。

正面碼證：SPEC C-0 與 TODO §E/§N 把目前事件端恆 event-study-only、R-5 列為日後 universe 路徑；FROZEN v2 §2.1 對推翻既有設計用 R，爭議預設 R。

反面：若另立完全不同 endpoint／模式，原事件 endpoint 仍永遠 event-study-only，才可能以 D 延伸補充；主委提案是在同一路徑加條件，故不符合該反面。應先完整 R 審與重戳，再把 R-5 寫成新有效設計。

### 6. 批次切法與依賴

立場：R-5 依賴 R-1 與 SU-RESID-3 的主張正確但不完整；多 TF R-5 還依賴 SU-RESID-2，且 D1 的 R 程序是先決治理 gate。

正面碼證：projection 目前以 selected timeframe 且每事件單列運作；TODO §E 明確說 SU-RESID-2 會牽動 EventSplitPlan 下游，R-5 會動 request/frontend/contract/UAT。

反面／更省輪次方案：可把 R-1＋SU-RESID-2＋SU-RESID-3 的 identity/schema work 合成一批，並在該批內讓未完成形態全部 fail-closed、保留舊 golden、補 multi-TF negative/golden；這比先後三批更省輪次但整合風險高。無論採合併或分批，均不可把 R-5 與未完成 D1 R 重開同時上線。保守切法是 b8 identity（R-1＋SU3）、b9 SU2＋下游、D1 R 重開／重戳、b10 R-5。

### 7. 主委漏掉的殘留／風險

立場：有，至少兩項不能漏：projection summary 的 per-symbol test-floor bug（CODEX-R1-P1-07），以及 SU2 的 event_id 單鍵 downstream surface（CODEX-R1-P1-08）。真實 cache 的 row length variation 也否證 scalar universe 假設，已列入 CODEX-R1-P1-02。

正面碼證：真實命令讀到 14 個 timestamps parquet，ETH 12h/1h 各有多個不同長度；`_build_summary` 使用 aggregate n_test；物化與 tables/pattern/baseline/ic_feed 均有 event_id 單鍵。

反面：`lgb_cv_universe` 與 `xgb_cv_universe` 的 grep 只命中兩個 analyzer 產生 OOF receipt 的位置，沒有命中 `derive_event_split_from_plans` caller，因此目前不把它升格成現行 finding；但 R-5 接線時應明確拒絕模型 CV hash 作為事件 canonical universe provenance。另已查 dedupe 的 label_start/event_id 排序，故不能用 positional zip 解複合鍵。

# 驗證與收尾

ASSUMPTIONS_VERIFIED: `git status --short` 只作既有工作樹盤點；逐行讀取列名檔；`h5ls -r data_cache/feature_klines/kline_cache.h5` 顯示 10 symbol × 3 TF 的真實 kline dataset；parquet 讀取命令顯示 14 個真實 feature timestamp 檔且長度不固定；`rg -n "lgb_cv_universe|xgb_cv_universe|derive_event_split_from_plans" momentum api tests scripts` 顯示 fake CV hash 未流入 projection caller。
TESTS_RUN: none（consult-only；brief 允許的逐檔測試未指定；未跑 tests/governance 全套）。
FAILURES_SEEN: none；未進行程式修復。
SCOPE_CHANGES: none；只新增本交件檔，未改碼或 tracked 檔。
NUMERIC_OR_SCHEMA_IMPACT: 本輪未改輸出；報告指出 R-5/SU-RESID-2/R-3 之預期 request、key、golden 與 digest 影響，未擅自變更。
OUTPUT_PATH: handoffs/20260911-splitunify-x-consult-r2-codex.md

VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03,CODEX-R1-P1-04,CODEX-R1-P1-05,CODEX-R1-P1-06,CODEX-R1-P1-07,CODEX-R1-P1-08
CLOSED:
STATUS: DONE
## COMPOSER-R2-P1-01

**斷言**: R-1 的 needs-research 理由應收回——`base_universe_hash` 在多標的下之唯一性已由 `_base_universe_hash(...,symbol)` 定義；未做的是 per-symbol `(train,test)` 對的投影 API 與 `split_per_symbol` 逐 symbol 傳 hash。

**碼證**: `ic_filter_orchestrator.py:517-530`；`contracts.py:662-684`（共用字面 hash）；`split_projection.py:400-428`（單 plan 對 + 多 symbol 事件 fail-closed）。VERIFY: `python -c "…ETH vs BTC…"` ⇒ `False`。RECHECK: 同上命令 + 讀三處行號。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#4b1b8bc9f22a

[MAJOR] 信心度=High。若 b8 仍把 R-1 當「hash 語意研究」會再空轉一輪；**不改**則多 symbol 批永遠 `multi_symbol_projection_unsupported`，IC 與事件掃描無法對齊 per-symbol 邊界。修法：投影改收 `Mapping[symbol,(train,test)]` + `feature_index_by_symbol`，每 symbol 各自 hash（`split_per_symbol` 改為逐 symbol 呼叫 `_base_universe_hash` 或傳 `dict[symbol,str]`）。

---

## COMPOSER-R2-P1-02

**斷言**: R-5 收窄為選填 `features_ref` 時，`None` 路徑不必動前端；但 b10 驗收必含 `capability.split=ok` 新分支，否則有 universe 仍顯示「沒切分」。

**碼證**: `case_import_service.py:1620-1623`（恆 unavailable）；`EventTablesPanel.tsx:360-362`（`hasSplit` 才顯計數）；`splitCapability.ts:57`（僅 `split==='ok'` 為 hasSplit）。RECHECK: `grep capability.split case_import_service.py`；讀 `splitCapability.ts:54-74`。

**來源摘要**: api/services/case_import_service.py#d2571793953f

[MAJOR] 信心度=High。若只做後端接線、不改 capability 枚舉與前端 `ok` 分支，R-5 **靜默失敗**——表算了但 UI 永遠 event-study-only 文案。修法：契約 JSON 增 `split=ok` + reason 封閉集；前端僅在 `ok` 時恢復計數列（與現 `unavailable` 對稱）。

---

## COMPOSER-R2-P1-03

**斷言**: SU-RESID-3 在 b9 應採「首尾對證 + 明文誠實邊界」，不在 `SplitPlan` 加 `row_time_fingerprint`；R-5 驗收改加投影端對 plan 全部 `row_index` 的 timestamp 指紋（不動 IC digest）。

**碼證**: `split_projection.py:474-484`（現行首尾）；SPEC TODO §E SU-RESID-3「中間間距」殘留原文；`contracts.py:425-426`（秒語意 hash 動 golden）。RECHECK: 讀 `split_projection.py:464-484` 與 TODO §E 行。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#98ee62905643

[MAJOR] 信心度=Medium。**不改**則中間間距攻擊面仍存在，但 B3 已擋住更高危兩條；若 b10 不做 row 指紋，R-5 錯指 universe 仍可能首尾巧合通過。修法：投影內對 `index_ms[rows]` 全列 sha256 與 plan 建檔時快取比對（快取可只活在 derive 呼叫鏈，不寫回 SplitPlan）。

---

## COMPOSER-R2-P2-01

**斷言**: D1 條件式重寫應走 **D 延伸**（`SPLITUNIFY_SPEC.D-00X`），在延伸檔 `覆寫` 明示取代 §C-0 決議③「恆走」字面；爭議時預設 R 但本案核心設計（C-1 時間切分權威）未被證偽。

**碼證**: `docs/SPLITUNIFY_SPEC.md:89-93`（恆走原文）；`FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md §2.1-2.2`；`b7-review-r1/synth.md:20`（未重審）。RECHECK: 讀 SPEC §C-0 與 v2 §2.2 延伸檔模板。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[MAJOR] 信心度=Medium。若跳過延伸檔直接改 SPEC 正文會 violate 戳記；若誤判為不需程序會在 `reconcile_stamps_check` 被擋。**不改**則 b10 無法合法寫入「有 features_ref 時走對照路徑」。

---

## COMPOSER-R2-P2-02

**斷言**: 批次依賴應為 **b8（R-1＋SU-RESID-2）→ b9（SU-RESID-3 誠實邊界＋row 指紋）→ b10（R-5＋D1 延伸）**；R-5 不得早於 R-1。

**碼證**: `split_projection.py:413-428`（per-symbol 前置）；`case_import_service.py:1592-1602`（R-5 須接 derive）；主委 brief §4 自陳 R-5 依賴 R-1 與 SU-RESID-3。RECHECK: 對照 TODO §E 殘留表與 SPEC Task 3.3。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[MINOR] 信心度=High。若 b10 搶跑，事件掃描端可帶 `features_ref` 但投影仍單 plan ⇒ **跨 symbol 靜默錯分**或 fail-closed 假完成。

---

## COMPOSER-R2-P2-03

**斷言**: SU-RESID-2 收案時若只改鍵、不新增多 TF golden，現有五組不必全重算，但**必**增 §G 多 TF 組，否則複合鍵路徑無回歸。

**碼證**: `tests/golden/splitunify/splitunify_golden.json`（單 TF event_id）；`test_splitunify_golden.py:134-137`（手推锚點）；`freeze_splitunify_golden.py:158-161`。RECHECK: `pytest tests/momentum/Analysis/test_splitunify_golden.py -q`（9 passed 基線）。

**來源摘要**: tests/golden/splitunify/splitunify_golden.json#f270e007ca98

[MINOR] 信心度=High。若誤以「g1 仍綠」當 SU-RESID-2 完成，多 TF 同 event_id 會在生產路徑 raise 或靜默錯分且測試不紅。

---

## GROK-R1-P1-01

**斷言**: 將 D1「事件掃描端恆走 event-study-only」改寫成「有 universe／`features_ref` 才走 OOS、否則才 event-study-only」，與已戳記 SPEC 之「恆走」落點句字面互斥；主委偵察若逕標「不推翻、純改寫」而未走凍結程序之 R（或嚴格限縮觸及面的 D），後續 b10 文件修訂會在戳記／互斥檢查被打回或留下雙源措辭。

**碼證**: SPEC C-0 決議③原則句＝「沒有 canonical feature universe … 只能明示 event-study-only」；同節 R2 D1／§N R-5＝本票事件掃描端**恆走**＋日後 R-5「不得刪 Task 3.3、只能新增對照路徑」（`docs/SPLITUNIFY_SPEC.md` C-0／§N；`docs/SPLITUNIFY_TODO.md` §E R-5）。凍結程序：D＝不推翻；與原檔互斥⇒非 D；爭議預設 R（`docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` §1；v2 §2.1 同語意）。主委偵察 §3 寫「D1 不推翻，改寫為條件式」未處理「恆」字互斥。RECHECK：寫出擬議條文後對讀 C-0 決議③／R2 D1／§N R-5 三句，標「覆寫／新增／不觸」；若任一「恆走」句被改成相反義務且未升 R ⇒ 本 finding 仍開。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[BLOCKING] 信心度=High。不改會在 b10 具體失敗：延伸檔／重開稿無法通過「與原檔不互斥」對讀，或文件仍寫「恆走」而碼已條件化 ⇒ 下一批 agent 依文件實作又砍掉 OOS 路徑。修法：b10 開工前 brief 明示 **R** 或 **D＋觸及面只覆寫本票落點句並保留決議③原則**；爭議未消則 R。

## GROK-R1-P2-01

**斷言**: 主委「`_base_universe_hash` 含 symbol ⇒ 唯一性已有定義」忽略生產路徑 `ICSplitAdapter` 對多標的整框使用**單一 joint hash**並打在每個 symbol 的 plan 上——兩 symbol 合法共用同一 hash 字面；R-1 若把「跨 symbol hash 必互異」寫成閘，會拒收現行 IC 多標的計畫。

**碼證**: `ICSplitAdapter.split_cpcv`／`split_wf` 先 `base_hash = self._base_universe_hash(frame, ...)` 再逐 symbol `_build_plan_pair(..., base_universe_hash=base_hash)`（`ic_split_adapter.py:55-97,118,189-199`）。對照 orchestrator `_base_universe_hash(index, symbol)`（`ic_filter_orchestrator.py:517-530`）同 index 異 symbol 實跑 hash 不同。Adapter 實跑 joint≠per-symbol。RECHECK：多標的 frame 經 `ICSplitAdapter` 產兩對 plan，斷言兩 symbol 之 `base_universe_hash` 字面相等且 `symbol` 欄不同。

**來源摘要**: momentum/Analysis/ic_split_adapter.py#c2dd93482826

[MAJOR] 信心度=High。失敗模式：b8 實作按主委字面加「跨 symbol hash 碰撞 ⇒ fail-closed」⇒ IC 多標的接線紅。修法：R-1 不變式改為「同一 symbol 之 train/test hash 一致；跨 symbol 允許共享 joint-universe hash；事件 symbol 必須匹配 plan.symbol；逐 symbol 做同源對證」。

## GROK-R1-P2-02

**斷言**: 主委批次 `b9=SU-RESID-2＋SU-RESID-3` 把多 TF 複合鍵與逐列指紋綁成 R-5 前置，但 SU-RESID-2 不在 R-5 的 fail-closed 依賴鏈上；綁在一起會無謂串長收尾，或讓 R-5 被無關的 golden／TF 結構爭議擋住。

**碼證**: R-5 風險＝錯 `features_ref`／錯 symbol 邊界（依賴 R-1 逐 symbol 投影＋SU-RESID-3 指紋）。SU-RESID-2 原文＝selected TF 下 event_id 多列 raise（`split_projection.py:270-288`；SPEC §N／TODO §E）。`ic_feed.py:109` 已按 timeframe 過濾。RECHECK：畫依賴圖——刪掉 SU-RESID-2 後 R-5 錯-run 攻擊是否仍被 R-1＋SU-RESID-3 擋住（應為是）。

**來源摘要**: docs/SPLITUNIFY_TODO.md#e44da6448b01

[MAJOR] 信心度=Medium。失敗模式：b9 卡在 golden TF 維度審，b10 R-5 整批空轉。修法：`b8=R-1（±SU-RESID-3）`→`b9=R-5＋D1 程序`→`b10=SU-RESID-2`；或 SU-RESID-3 進 b8、SU-RESID-2 獨立殿後。

## GROK-R1-P2-03

**斷言**: 「`features_ref` 選填、前端不改」只能保證 UI 繼續走 event-study-only 且 capability 文案可解釋；不能等同「避開跨棧後 UI 也能用 OOS」。若收尾驗收以「前端零 diff」為成功條件，會把 R-5 做成僅 API 暗門。

**碼證**: `analyzeEventImport` body 型別無 features 欄（`api.ts:1119-1127`）；`EventTablesPanel` 呼叫不傳（`:303`）；`splitCapabilityView` 在 `hasSplit=true` 時面板顯示 train／test／purge（`EventTablesPanel.tsx:360-361`）。RECHECK：前端零改＋僅 API 帶 `features_ref` 跑通 ≠ 產品驗收通過；若要產品面 OOS，須另開前端選 run 或明示「本殘留只交付 API 能力」。

**來源摘要**: frontend/src/lib/api.ts#4a54c9918781

[MAJOR] 信心度=High。失敗模式：b10 標 done、UI 仍永顯示「取不到特徵宇宙」，使用者以為 R-5 沒做。修法：R-5 scope 一句寫死——(A) API-only＋文件誠實邊界，或 (B) 最小前端 `features_ref` 入口；禁止用「前端不改」同時暗示產品 OOS 已通。

---

