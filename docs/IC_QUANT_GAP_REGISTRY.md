# IC 量化缺口 Registry（ICHC 健檢 Task 6.4）

> **本檔＝未來票的單一登記處**（原六張；2026-08-18 使用者裁定 #2 拆 2a／2b、#3 重定義）；ROADMAP 狀態表只放 pointer 至此。
> 來源＝2026-08-17 健檢偵察四方 reconcile（`handoffs/reconcile/20260817-ichc-x-consult-r1/synth.md` C 群集）。
> 排序原則（凍結於偵察）：防過擬合 ＞ 名實相符 ＞ 寫實度 ＞ 規模。
> phasing 對照＝`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md` 之 Phase 編號（該檔為委員 CONVERGED 歷史文件，不改內文）。

| # | 缺口票 | 一句定義 | 來源 finding | 觸發條件 | phasing |
|---|---|---|---|---|---|
| 1 | DSR/PBO/MinBTL 策略層防過擬合 | 「試了一千個策略挑最好的，是真本事還是運氣」的三個檢定；因子層已有 FDR、策略層現裸奔 | CODEX-R1-P1-08, GROK-R1-P1-02 | 排程即可做（無硬前置） | Phase 4 |
| 2a | 邊際 IC／多因子組合（純 IC 層） | 「這因子相對已有的帶來多少**新**資訊」；正交化 residual 已在（`factor_orthogonalizer.py`）、真歸因現為誠實 `unavailable`（健檢 C11）；不碰 ML、不碰事件型 | CODEX-R1-P1-09, GROK-R1-P1-06 | 排程即可做；**2026-08-18 使用者點為下一票（新 session 開工，大任務完整管線）** | Phase 4 |
| 2b | IC→ML 橋（倖存者輸出契約＋橋本體） | 序列型／事件型篩出的倖存者走**同一座橋**進 ML；契約須含 `sample_scope`（事件型倖存者只能在事件樣本上訓練）＋provenance | 同上 | **契約先行、橋本體 blocked-by ML 層**（成熟度地圖：ML／回測屬不完整層、可能重寫；接上即隨殼作廢，同 G1-R1 理由）。契約於 2a SPEC 內一併定義 | Phase 4 |
| 3 | 事件型分析（**2026-08-18 使用者重定義**：事件錨定之監督式 pattern 發現，非金融 event study） | 使用者**於外部自行標好**正／反例（標的＋t₀＋標籤）匯入 ⇒ 平台核心＝**事件匯入契約＋PIT 對齊特徵＋去重／切分＋條件 IC／ML**，非事件產生器；事件類型多樣，契約通用不為單一事件寫死。現有雛形＝案例搜尋 cases.json→`xgboost_batch_service`→`pattern_extractor`（ML 孤島）；本票＝按 IC 主線標準重建此線。原「case-control」語意降為反例／對照組設計之一 | CODEX-R1-P1-01, GROK-R1-P0-02 | **開發前先討論**：開工第一步＝唯讀「事件語意 consult」（三家＋主委各完整版），收斂後白話給使用者裁 Q0＋5 題（見下節）再進 SPEC；設計須含 R5 裁決之 A′ 語意（fallback 保留 event_timestamps） | Phase 2A |
| 4 | Pooled/Panel IC | 多標的資料合併估 IC，樣本更多結論更穩 | CLAUDE-R1-P1-04（主委版，roster 外） | 排程即可做 | Phase 4 |
| 5 | 容量 ADV 真資料接線 | 接真實成交量回答「能裝多少錢」；unknown 契約已鎖死（B6 Task 6.1） | CODEX-R1-P1-04, GROK-R1-P1-04 | **條件觸發**：volume 資料源就緒 | Phase 4 |
| 6 | 430K 規模防護（correlation cap 等） | 大候選集運算上限與分批；死配置已移除（B6 Task 6.3），cap 本體歸此票 | CODEX-R1-P1-06, GROK-R1-P2-02 | 併既有 IC-PERF/串流 epic | Phase 3 |

## GAP-3 開發前討論題（2026-08-18 使用者：「需要討論、現在不展開」；consult 輪之輸入）

> **2026-08-20 討論階段收案**：consult R1（r1 synth；composer collection-failed）＋R2（`handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md`；三家齊、26 條九群集）＋使用者兩輪補充（七點）皆收斂於 **`白話說明/GAP-3事件型討論.md`（第 12 版；§7.5＝SPEC 取材唯一地圖）**。
> 使用者 2026-08-20 裁定：**新 session 起草 SPEC**（`docs/GAP3_EVENT_SPEC.md`；HANDOFF 已備開工指令；五項「待 SPEC 對抗審確認」列於 HANDOFF）。本節凍結，後續以 SPEC 為準。
> **2026-08-20 SPEC FROZEN**：六輪對抗審（15→6→4→1→1→0；原提出方逐條閉合）＋三家 RECONCILE-STAMP（`handoffs/reconcile/20260820-gap3-x-review-r6/synth.md` rc=0）＋使用者白話閘三裁決（門檻皆舉例可調／label_return_mode 保留三值／decision_offset_bars＝研究參數非訊號標註）。下一步＝TODO。

### GAP-3 殘留（SPEC §N 八條；三值理由；觸發即轉新票——權威登記處，ROADMAP 只放 pointer）

| # | 項目 | 為何現在不做 | 觸發 |
|---|---|---|---|
| G3-R1 | triple-barrier／出場最佳化 | user-ruling:2026-08-19（第一版時間出場）＋blocked-by:回測層不完整 | 使用者提出且回測層成熟 |
| G3-R2 | long-short 組合 | user-ruling:2026-08-19 §4（一次只研究一向） | 使用者提出 |
| G3-R3 | T4 衍生品/微結構、T6 新聞/鏈上事件 | blocked-by:外部資料源未接（契約欄位已留） | 資料源 epic 落地 |
| G3-R4 | uniqueness/cluster 權重接 GBDT sample_weight | blocked-by:`UNWIRED_MODULES` 含 sample_weight＋成熟度地圖禁改訓練殼 | ML 殼允許接線閘 |
| G3-R5 | 正式 panel IC（cross-sectional/GEE） | blocked-by:registry #4 獨立票（本票只蓋可複用原語） | #4 開票 |
| G3-R6 | CAR/AAR event study、即時 NLP 事件 | user-ruling:2026-08-19/20（非本票定義；使用者確認不需要） | 使用者提出新需求另開票 |
| G3-R7 | `platform_random_bars` 控制組自動抽樣 | needs-research:estimand 與抽樣契約未定義（R1 判時間分離隨機反例＝廢答案設計） | 委員會定出契約 |
| G3-R8 | label 一致性探針 | needs-research:探針族範圍與誤報處置未定義（AR-6 裁 2:1；配套硬規則已入 SPEC D1-3） | 使用者要求或匯入資料品質事故 |
| G3-R9 | `/ic-analysis` 事件模式辨別表接真實模型分數（現回 `not_computed:no_model_scores_in_event_pipeline`，前端顯示原因） | blocked-by:分數來源＝B4.1 pattern 橋／ML 層（成熟度地圖不完整層）；匯入管線不產分數 | ML 層穩定或使用者點名（B5 review R1 登記） |
| G3-R10 | 事件匯入大檔串流／分頁＋背景 worker（現＝MAX_FILE_SIZE 50MB＋CSV 分塊解析，10k 事件同步對齊 ~73s；receipt `handoffs/run_receipts/gap3_import_scale.json`） | user-ruling:W10 記錄型不私定門檻；效能門檻須 SPEC amendment | 萬級以上需求或門檻明確化（B5 review R1 登記） |
| G3-R11 | `tests/api` 既有紅（batch_alias／ic_deep_analysis／ichc_event_timestamps t2-t3／model_enhancement×3；**2026-09-01 補**：`test_progress_rss_fields` 兩條——`RuntimeError: There is no current event loop in thread 'MainThread'`，**只在整包跑時紅、單跑 7 passed** ⇒ 測試間 event-loop 污染，非產品缺陷。實測排除法確認與本批無關：`--ignore` 掉本批新增之 `test_gap3_csv_roundtrip.py` 後**同樣 4 failed**） | blocked-by:非 GAP-3 模組（feature registry／deep cache／model_enhancement／ichc slow）；另開票 | 對應模組開工時（B5.1 receipt 記錄） |
| G3-R12 | 小事件批之 IC 表 `ic_mean`／`icir` 顯示 `--`（2026-09-02 UAT B17 觀察）：`ic_mean`／`icir`／`ic_std`／`ic_hit_rate` 全由**滾動視窗** IC 序列算（`rolling_windows` 21／63／126 日等值，12h 線 ×2 ⇒ 42／126／252 列），60 筆事件列小於最小視窗 ⇒ 序列為空 ⇒ NaN；而 `t_stat`／`p_value` 走 pooled Spearman 故有值。**接線正確、非缺陷**，但畫面對使用者不可解釋（有 t-stat 卻沒 IC）。可行修法＝事件模式且列數＜最小視窗時，`ic_mean` 改報 pooled Spearman ρ 並標 `ic_source=pooled_small_sample`（契約新欄），或 UI 在 `--` 旁顯示原因 | **needs-research**（要決定 pooled IC 是否可與滾動 IC 同欄呈現；涉及 survivor 契約欄位，須 D-6 走契約修訂）；現況以驗收清單 B17 註記說明 |
| G3-R13 | C 確認型之「收盤後決策」語意（`decision_at = t₀ close`、事件已知可進特徵）在 D2-2 單一表示法（`t0 + decision_offset_bars ≥ 0`）**不可表示**；現行 `/search` C 批機械上＝決策於 t₀ open、t₀ 條件為深度 0 之未來事件（即使用者 B 之特徵側）。2026-09-03 consult 四方一致（`handoffs/reconcile/20260903-gap3d2-x-consult-r1/synth.md` 群 2） | user-ruling:2026-09-03 委員共識（使用者離線）G3-D2 不改 D2-2，只把 C 揭露改為誠實描述＋落地 `event_known_at_decision`；是否需要真正的收盤後決策語意待使用者裁定（需 R 重開原 SPEC D2-2；修法候選＝條件引擎 `lag(col,n)` 之 t₀ 重錨） | 使用者裁定「要」 |
| **KLINE-1** | 🔴 **2026-09-02 使用者二次改裁：`/data-preparation` 之舊區塊「導入案例 CSV → 批量 K 線下載」整塊「註解之後移除」；`/search` 與 FF 頁的 K 線下載按現況保留、不合鏈**（取代同日稍早「另開票拆成獨立版面」之裁定）。判準來源＝三方各自獨立的事實：`/search` 自己讀寫 `data_cache/kline_cache.h5`（`MomentumDataLoader`，缺才補下載）；FF 頁寫 `data_cache/feature_klines/`，而 FF／IC／事件分析全數只讀後者（唯讀接線稽核＋真下載 e2e 收據：dtype／attrs 與現有檔相同、重疊 20 根九欄逐 bit 相等）；`/data-preparation` 舊區塊則**兩邊各沾一半**——寫入程式碼同 FF 頁、目標檔同 `/search`，其下游（`pattern_analysis`／`xgboost_batch`／`optuna`／`signal_analysis`）皆屬未跑過。**移除範圍（初盤，SPEC 時定案）**：前端 `CaseImportForm`／`BatchDownloadPanel`／「已導入案例總覽」／「使用說明（Phase 1）」；後端 `routes/case.py` 之 `/case/import`、`/case/list`、`/case/count`、`/case/clear-all`、`/kline/batch-download`、`/kline/download-status`（**同檔之 `/case/import-events*`／`/case/events*`／`lookahead-*` 為 GAP-3，必留**）；`batch_download_service`；`case_storage` 及其消費者去留逐一判。🔴 **前端仍呼叫舊 `/case/list` 的活頁面（唯讀稽核 2026-09-02）**：`hooks/useAvailableSymbols`（被 FF `BatchGenerationPanel` 之「加入已導入案例的 symbol」與 `strategy-test` 用；FF 另有 `/search` 結果與手動輸入兩個來源，故非硬相依）、`chart`／`charts` 頁、`data-preparation` 頁自身之 `/case/clear-all`。移除時這些呼叫者須一併處理，否則變成靜默空清單。FF 頁下載鏈 e2e 收據 VERIFY:20260902T012246Z-ff-kline-download-e2e。原始問題描述如下 → | 🔴 **新票（2026-09-02 使用者裁定「另開票拆成獨立版面」，同日已被上列改裁取代）**：`/data-preparation` 的「導入案例CSV」實為**批量 K 線下載**入口，與事件匯入擠在同一頁 ⇒ 語意混淆（連我都判錯過，先前把它當成舊版事件匯入）。🔴 **實測發現更根本的問題**：K 線下載目前有**兩條各自獨立的鏈**——(a) `batch_download_service` → `data_cache/kline_cache.h5`（849 KB，經案例 CSV 觸發，下游＝`pattern_analysis`／`xgboost_batch_service`／`optimization_task_service`／`signal_analysis_service`／`optuna_optimizer`，後四者依成熟度地圖屬「從未跑過」）；(b) `feature_kline_service`（Feature Factory 頁自己的下載面板，`/api/v1/feature-data/kline/download`）→ `data_cache/feature_klines/kline_cache.h5`（9.9 MB，2026-04-28）。**兩份快取、日期差四個月、互不共用**。⇒ 本票的問題不只是「搬到哪一頁」，而是**這兩條要不要合成一條**。使用者提醒「K 線下載的 K 線 Feature Factory 也會使用」——就現行程式碼而言 (b) 才是 Feature Factory 讀的那份，(a) 它不吃；這個落差本身就是要修的東西 | **user-ruling（另開票，不擋 GAP-3 收案）**。先做止血：把作廢的圖表連結拿掉、區塊改名為「批量 K 線下載」。合鏈設計須先確認 (a) 的下游有哪些是活的 |
| **G3-D1** | 🔴 **缺陷（非殘留）**：匯出前篩選只有**一組**條件、同時套用正例與反例。條件一旦引用 `future_*` 欄，兩類**同時**被結果截斷 ⇒ 反例不再是對照組、三組報酬表三組皆正、條件 IC 建立在照結果挑過的樣本上（range restriction ＋ collider bias，偏誤方向不可預測），且畫面無任何提示。搜尋階段本來就分開（`search_task_service.py:184` 之 `negative_conditions`），是匯出前篩選把它們壓回同一組。**已裁定修法**（使用者 2026-08-31）：①正反例各自獨立條件、絕不共用；②篩選**不再兼差推導答案窗深度**，深度改為直接問使用者「哪個 timeframe 的第幾根 bar 用來區分正反例」；③**purge ＝ 正反例深度取大者**。理由：現行由條件反推（Task 2.1b）自記四種抽不出引用欄之失敗形態，抽不出仍要問使用者；且系統外標記時篩選面板為空 ⇒ 推不出深度、purge 為 0 而無人喊。 | 🔴 **2026-09-02 使用者改裁：整個移除匯出前篩選**（不是改成兩組條件）。理由＝CSV 已可回灌（`G3-D3`），正反例篩選在 Excel 做本來就更強；而深度宣告改為匯入時直接問，篩選就沒有存在理由了。使用者原話：「上傳都有要填答案窗了，那 G3-D1 這在 /search 的新增條件都不用了吧，使用者直接 CSV 篩選就好」 | **user-ruling（2026-09-02：移除）**；🔴 **修訂類別＝R 重開（非 D 延伸）**——三家 consult 一致（`handoffs/reconcile/20260902-gap3ux-x-consult-r1/synth.md`）：推翻 FROZEN A-1 與 Phase 2 定位＝§2.1「既有設計被證偽」；whole-body ⇒ 全檔對抗審，依賴閉包只作必讀 focus；D-001…D-005 全部 `SUPERSEDED-BY-R` 併回；R 本體必含匯出端 `lookahead_bars_declared` 來源設計（現唯一來源＝2.1b state）。**R 完成前不得以 D 開工**（原「D-006」字樣作廢）。連帶：`/search` 之 B2 整區移除、驗收清單 B2 改寫、`export-count-*` 與下界守衛之去留須逐項判定（匯出仍需 `lookahead_bars_declared`）。**進度（2026-09-02）**：R35→R37 三輪審查收斂、三家 `RECONCILE-STAMP` APPROVED（session `20260902-gap3ux-x-stamp-r1`）；R 實作批（Task 1.9′＋Phase 2 退役＋Task 1.11 後端一律宣告＋validator `v<0`＋`preview-columns` 端點）已落地並過 8 條 mutation；三家 code review R1（codex 1 P1＋2 P2、grok 2 P1＋1 P2）→ 修法 `7e0a7a94` → R2 閉合（六條 CLOSED；codex 反向 1 P1）→ 修法 `dd4baa2c` → R3 閉合（CLOSED、三家無新 P0／P1）⇒ **CLOSED（2026-09-02）**。使用者驗收＝清單 B2（改寫）／B5／B10（程式面已結案，UAT 為使用者側確認） |
| **G3-D6** | ✅ **已修（2026-09-02）**：`/search` 契約 CSV 之 `meta.` 欄由**手寫白名單** `META_KEYS`（24 欄）決定 ⇒ `future_*bar_max_drawdown` 整批靜默消失，而使用者正要靠這些欄在 Excel 篩正反例。🔴 與 `G3-D4` **同型第二次**（手寫清單漏項），故兩端都改為可導出規則：`meta.` ＝「該列所有欄 − 契約欄」之補集；唯一排除項 `positive_case`（已由契約 `label` 承載，兩個答案欄必然誤會），且該排除本身有測試釘住 | **CLOSED**（`gap3_export_filter_page.test.tsx` ⑨；含 over 向：契約欄不得被複製進 meta.） |
| **G3-D7** | ✅ **已修（2026-09-02）**：匯入拒收在畫面上顯示 `[object Object]`。成因＝各處寫 `new Error(body.detail \|\| '…')`，而結構化拒收之 `detail` 是**物件**。修法＝新增 `frontend/src/lib/httpError.ts` 之 `httpErrorMessage()`（支援 `{kind,message,failures}`／`{code,message}`／FastAPI 422 陣列／字串四種形狀，並摘要前三筆 failures），**31 個呼叫點全數改用**，不留「呼叫點自己判型別」的第二份實作 | **CLOSED**（`httpError.test.ts` 7 條） |
| **G3-D8** | ✅ **已修（2026-09-02）**：契約欄名之 CSV 丟進「用自己的欄名匯入事件 CSV」區，把下拉全選後送出 ⇒ `99 筆契約違規／列 0／label_definition／missing_required_field`。真因＝對映路徑只保留下拉指定之欄，而下拉只提供契約**頂層**欄，`label_definition.window.horizon_bars` 這種巢狀欄沒得選。**後端拒收是對的**，缺的是在使用者做完那一輪對映**之前**告訴他走錯區。修法＝`contractCsvDetect.ts` 於選檔當下警示並擋住送出；前後端判準以 `tests/api/test_gap3_contract_csv_guard.py` 逐字對證，禁漂移 | **CLOSED**（mutation 實測：停用偵測 ⇒ UI 條紅） |
| **G3-D10** | ✅ **已修（2026-09-02，UAT B15）**：事件模式對**任何註冊 run** 都被 coverage 閘以 `feature_coverage_unknown_legacy_run` 擋掉。根因＝閘只在 `features_path` 附近找 `feature_manifest.json`，而註冊 run 的 `features_path` 是物化暫存檔 `data_cache/reports/ic_ingest_cache/*.h5`，附近沒有 manifest；真正的 manifest（registry 條目 `hdf5_relative_path`）**有** `time_range`。B10 收案時只測了閘本體（結構化 WindowRow），沒跑「註冊 run → 物化 → 閘」這條真路徑（codex R1 brief 早列為「我沒查的」）。修法＝registry 條目之 manifest 路徑作第一候選傳進 `_run_event_label_stages(feature_manifest_path=)`；回歸測試對「物化暫存路徑＋registry manifest」兩候選 | **CLOSED** | — |
| **G3-D11** | ✅ **已修（2026-09-02，UAT B15）**：任務在前端訂閱 WebSocket **之前**就失敗（coverage 閘數十毫秒內拒）⇒ 失敗通知已發過、不會再來，前端既無新訊息也不會退回輪詢，畫面永遠「任務執行中」。修法兩端各一：後端 WS 連上時若任務已 failed／completed **補推快照**；前端 `ws.onopen` 先拉一次 `/task/{id}` 現況（終態即收斂並關 WS）。hook 測試一條 | **CLOSED** | — |
| **G3-D12** | ✅ **已修（2026-09-02，UAT B16）**：分析完成後畫面出現「Failed to fetch」——調門檻觸發 `POST /ic/refilter`，service 直接回 analyzer 原始 dict，內含 NaN／inf（decay 擬合失敗、survivors=0 之統計）⇒ JSONResponse 500「Out of range float values are not JSON compliant」⇒ 無 CORS 標頭 ⇒ 瀏覽器只看到 Failed to fetch。`/result` 走 `get_result()`（非有限值→null＋F2 sanitizer）故沒事。修法＝refilter 改回 `get_result(task_id)` 同一出口；回歸測試以探針 NaN／inf 斷言 200 且為 null、與 `/result` 之 summary_table 逐字相同 | **CLOSED** | — |
| **G3-D13** | ✅ **已修（2026-09-02，UAT B17）**🔴 **正確性缺陷**：事件模式（`event_import_id`）之報告其實是**全樣本 IC**——`_build_config_override` 只對 `event_query`／`event_timestamps` 開 `event_filter.enabled`，B10 把前端改成只送 `event_import_id` 後沒跟著加 ⇒ 五階段算出的 timestamps／label 餵進 analyzer，但 stage3 因 enabled=False 回 `mode=none`；`statistic_kind`／`label_source` 等條件 IC 標記全部不存在，畫面與 `analysis_status=ok_oos` 看不出來（使用者依清單在結果 JSON 找不到才現形）。B10 三輪 review 皆未抓到：測試只驗 transport 層（互斥／400）與 purge 數值，沒有一條斷言 `metadata.event_filter.mode != "none"`。修法一行＋回歸測試（`event_import_id` ⇒ enabled；無事件 ⇒ 不得憑空開）。🔴 **B13–B17 之前的「事件模式」結果全部作廢，須重跑** | **CLOSED** | — |
| **G3-D14** | ✅ **已修（2026-09-02，UAT B17，緊接 D13）**：D13 修好後事件模式真的跑條件 IC，隨即在落檔倖存者輸出 fail-closed「`build_survivor_output: conditional_ic run requires event_context (v2 six keys)`」——B10 五階段路徑繞過 `ic_feed.build_event_ic_inputs`，連同它產生的 survivor v2 六鍵 `event_context` 一起繞掉，`analyzer.analyze(event_context=)` 從未被傳。修法＝`ic_feed.event_context_from_windows`（唯一實作；rule 字面抽成常數與 `build_event_ic_inputs` 共用）→ pipeline 出口 `event_context_for_analysis` → 五階段回傳 `event_context` → `analyze(event_context=)`；10i 測試加六鍵斷言。這條與 D13 是**同一個根因的兩面**：B10 沒有任何 e2e 測試讓事件批真的跑到 survivor 落檔 | **CLOSED** | — |
| **G3-D15** | ✅ **已修（2026-09-02，UAT B15 重跑）**：條件 IC 終於跑完（`degraded_full_sample`），畫面紅字「`'<' not supported between instances of 'NoneType' and 'NoneType'`」——`/ic/summary` 之 `_build_summary` 以 `item.get("icir", -inf)` 排序，degraded run 每列 `icir` **鍵在、值 None** ⇒ `None < None`。修法＝非有限值一律排最後；回歸測試（None／NaN 混有限值） | **CLOSED** | — |
| **G3-D16** | ✅ **已修（2026-09-02，UAT B15 log 觀察）**：`/ic-analysis` 完成後 refilter **無限迴圈**——page 的 effect 把 `report` 放進依賴，`refilter()` 成功即 `setReport` ⇒ 身分改變 ⇒ effect 重跑 ⇒ 每 600ms 再 refilter；後端每次重新落檔（log 每秒兩筆「IC report saved」；當日 104 次 refilter vs 使用者改門檻不到十次）。修法＝抽成 `useAutoRefilter` hook：觸發只看 `thresholdsKey`／`taskId`／`status`，`hasReport` 以 ref 讀、同一組門檻只跑一次；hook 測試（report 身分變 5 次 ⇒ 仍 1 次；門檻變 ⇒ 第 2 次） | **CLOSED** | — |
| **G3-D17** | ✅ **已修（2026-09-02，UAT 自由探索）**🔴 **正確性缺陷**：多 symbol 事件批（BTCUSDT＋ETHUSDT 同 t0）對單一 feature run（ETHUSDT 12h）分析時，五階段只以時間戳映射 feature 列 ⇒ BTC 事件會拿 ETH 的特徵列來算（跨 symbol 污染）；同時戳時才被「映射到同一個 feature 列（請先 dedupe）」擋下——訊息誤導（那不是重複事件）。修法＝只餵 `symbol == request.symbol` 之事件，他 symbol 具名排除（`events_excluded_by_symbol` 進 task_info＋log 警告），一筆不剩 ⇒ loud；撞列訊息標明同 symbol。跨 symbol 合併分析歸 registry #4（Pooled/Panel IC）。回歸測試（同 t0 之 BTC 被排除、ETH 照餵；全批他 symbol ⇒ raise） | **CLOSED** | — |
| **G3-D9** | ✅ **已修（2026-09-02）**：施工票號洩漏到使用者可見層——匯出檔名 `gap3_events_*.csv`、標題「已匯入事件批（GAP-3）」、拒收訊息「偵測到 GAP-3 新 schema」、IC decay 揭露「待 GAP-6 之 IC-Analysis 整體處理」。使用者原話：「以後使用者哪知道什麼是 GAP3？」。修法＝檔名改 `events_*`、UI 文案與後端訊息全部去票號（API 端點路徑改放結構化 `detail.endpoint`），並新增機械閘 `noTicketIdInUi.test.ts` 掃 `frontend/src` 非註解行。🔴 連帶修正一條**釘住錯性質**的既有斷言（`eventIcDecayDisclosure` 原本 `toContain('GAP-6')`，硬性要求畫面出現票號） | **CLOSED**（閘含自我證偽條；豁免僅 `pendingFeatures.ts`，理由具名） |
| **G3-D3** | ✅ **已修（2026-09-01 同批）**：`/search` 匯出之 CSV 用展示欄名（`Timestamp`／`Positive_Case`／`Price_Change_%`）⇒ 使用者在 Excel 標好正反例後**回不去**（要逐欄對映＋手寫含兩個 64 位 hex digest 的批次預設 JSON）。使用者原話：「我根本也看不懂也沒辦法自己寫」。修法＝匯出改契約欄名（巢狀走點路徑、非契約欄放 `meta.`、未標記列也帶著讓使用者補 `label`），零對映可直接上傳。回歸＝`tests/api/test_gap3_csv_roundtrip.py`（後端逐字重現前端規則再打真端點）＋`frontend/src/lib/eventContractCsv.test.ts` | **CLOSED** |
| **G3-D4** | ✅ **已修（2026-09-01 同批）**：後端 CSV dotted 欄還原用**手寫**欄名清單，`lookahead_bars_declared` 加進契約時沒同步 ⇒ `/search` 匯出之 CSV（每列必帶 `lookahead_bars_declared.<tf>`）回灌時整批 `unknown_field` 被拒。修法＝該集合改**從契約導出**（`type == "object"` 之欄），契約新增 object 欄自動跟上。抓到它的是 `scripts/gen_uat_samples.py` 新增的「產出前讓後端自己解析回契約列」檢查 | **CLOSED**（mutation 實測：移除該欄 ⇒ 1 failed；還原 ⇒ 6 passed） |
| **G3-D5** | ✅ **已修（2026-09-01 同批）**：答案窗宣告在「檔內無可解析未來欄」時把後端預設 `0` **直接預填**，而同一支驗證自己拒收 `0`（「須為正整數」）⇒ 使用者既無法「調低」也看不出該填什麼（UAT B10 回報）。修法＝預設 `< 1` 之 tf 留空不預填（走「尚未填寫」訊息），右側提示改寫為「檔內沒有可解析的未來欄；請填你用來區分正反例的最遠 bar 數」 | **CLOSED** |
| **G3-D2** | 🔴 **交付未完成（非殘留）**：`/search` 五維度中三類值**永久灰著**不算交付——(a) `scenario` 之 `A`／`B`／`two_stage`；(b) `control_kind` 之 `platform_random_bars`；(c) `entry_price_semantic` 其餘四值、`label_return_mode` 其餘兩值、`decision_offset_bars > 0`。**完成定義**：該值可選，且分析層算得出對應之 `label_value`（(a) 另需該情境自己的 label producer 與 provenance）。 | **user-ruling（2026-08-31：灰色項目必須完成，不接受永久灰著）**。難度分層：(c) 最近（一組一個 exact golden 即可開，§G G-3 擴充）；(b) 須委員會先定出隨機對照組之抽樣契約與 estimand（§N-7；當年那版被判廢設計）；(a) 須一整個預測型事件 epic。**UAT B3 在三者全部完成前一律記未完成**。🔴 **2026-09-02 深夜使用者裁定順序：(a) → (c) → (b)**；開工交接＝`docs/GAP3D2_KICKOFF_HANDOFF.md`（主委初判 (a) 技術上內含 (c) 子集，consult 必答）。**2026-09-03 consult r1 收斂**（四來源九群集，本機 `handoffs/reconcile/20260903-gap3d2-x-consult-r1/synth.md`）：形式＝D 延伸 `docs/GAP3_EVENT_UX_SPEC.D-001.md`，五 phase D1 B→D2 A→D3 two_stage→D4 (c) 其餘＋k→D5 (b)；P0＝open 語意取價於連續網格別名下靜默取 t₀−1 close（D4.1 修）；C 名實不符列 `G3-R13`；k 契約欄保留必填恆 0（codex 異議具名）。**2026-09-03 D-001 對抗審 r1–r4 收斂＋三家戳記；TODO 延伸 `docs/GAP3_EVENT_UX_TODO.D-006.md` review r1–r5 收斂＋三家戳記 ⇒ 兩份 FROZEN**（stamps check 皆 PASS）。依使用者裁定停下：白話說明＋範例 `白話說明/G3-D2灰色項目說明.md`。**2026-09-03 使用者白話閘四裁定 ⇒ v2**（A 併入預測型／IC 三種報酬選項依深度預設、取價修法提前 D0／k、h 掃描網格／k 註記；9/1 批為測試檔），v2 review r1→r2 收斂＋三家戳記 **2026-09-04 FROZEN**；**2026-09-04 使用者放行實作**（串行 B-D0→B-D1→B-D3→B-D4→B-D5；交接 `docs/GAP3D2_IMPL_HANDOFF.md`） |

使用者原意（逐字義）：例＝12h K 漲≥5% 定該根 open 為 t₀；t₀ 後 24／36／48h 之 close 皆比 t₀ close 高≥3% ⇒ 正例，否則反例；特徵＝t₀ 往前 x 根 1h／4h 指標；目標＝在數千～數萬個 t₀ 中找正例共通 pattern 當策略。**這只是其中一種事件**；正反例將由使用者自外部檔案標好餵入。

| # | 未決題 | 為何影響結果 |
|---|---|---|
| **Q0** | **事件類型盤點**（2026-08-18 使用者追加：不只自己想的那一種）——有哪些事件類型、各自如何定義／標定／陷阱、平台契約要通用到什麼程度、使用者原例屬哪一類 | 決定匯入契約的欄位與內建產生器範圍。主委粗盤點（consult 時三家各出完整版，非定案）：①價格／量行為觸發（大陽線、突破、量能暴增；**使用者原例屬此**）②技術結構形態③波動／regime 切換④微結構／衍生品（資金費率、OI、清算；需外部源）⑤日曆／排程⑥外部新聞（最像 event study）⑦人工標定匯入。第一版建議＝通用匯入契約＋①類一兩個規則型產生器示範；需外部源者登記待資料源 |
| Q1 | 決策時點 vs t₀（PIT） | 「+5%」到收盤才知；進場最早 t₀ close；標籤起算點與特徵截止點若定在 t₀ open 會把觸發根報酬算進績效 |
| Q2 | 反例定義 | 同觸發但未續漲（天然對照組）vs 未觸發任意 bar（模型先學「有無大陽線」廢答案） |
| Q3 | 去重／重疊／切分 | 連續觸發算幾個事件；標籤窗重疊 ⇒ 樣本不獨立；須 per-symbol 時間切＋purge/embargo 事件窗（禁 positional index） |
| Q4 | 標籤嚴格度 | 24∧36∧48 皆≥3%（正例少、不平衡）vs 任一／多數；3% 相對 t₀ close 或進場價 |
| Q5 | 共通 pattern 防運氣 | 條件子樣本 IC（`event_filter`，序列型工具可共用）＋GBDT/SHAP/規則抽取＋OOS／跨標的／FDR；規則挑選須接 GAP-1 DSR/PBO |

序列型／事件型**共用**：資料載入、特徵計算、未來報酬、PIT 守衛、IC 函式、bootstrap。**不共用**：樣本組裝（事件清單＋反例）、主統計量、切分/去重、報告契約、前端。

## IC 主路徑切分現狀（holdout-only）

IC 分析主路徑的 train/test 切分**現況＝單次 holdout**（`ic_train_test_split` 預設 ON；
失敗時 loud fallback 至 full-sample 並紅標 `degraded_full_sample`）。
**未實作**：walk-forward 與 purged CPCV 於 IC 主路徑（相關模組存在於
`momentum/Analysis/model_validation/` 但為 ML 孤島，未接 IC 選因子流程）——
report `metadata.split_method`（枚舉住 `momentum/Analysis/contracts/ic_report_contract.json`）
誠實標示現況，禁在任何輸出宣稱 CPCV/WF 保證。缺口票＝本檔 #1（策略層）與 phasing Phase 4。

> 落點註記（凍結 TODO 之具名偏差）：Task 6.2 原定此節入 `docs/API_SPECIFICATION.md`，
> 因該檔名命中 `docs/*SPEC*.md` 之治理格式快閘（任何編輯即擋 push、無豁免口），
> 改落本檔；grep oracle 同步指向本檔。偏差交最終 code review 複核。

## 不遺忘機制（登記時同步建立）

1. ROADMAP 狀態表六列 pointer 至本檔（commit 同步鐵律守著）。
2. 產品端顯式化：wiring 閘門與 capability status 契約使「未實作」在系統輸出可見（如 `split_method=holdout`、NetIC `unavailable`）——缺口不靠文件記憶。
3. 本檔更動走 commit review；票開工時各自立 SPEC、走完整管線。

## GAP-1 待補完登記（不遺忘機制；2026-08-17 使用者裁決）

> GAP-1 SPEC（`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` §N）之殘留**同步登記於此**，每條附「為何現在不做」與**觸發條件**。
> 規則：`為何現在不做` 只允許 `blocked-by:`／`user-ruling:`／`needs-research:` 三種；觸發條件成立時本表該列即轉為新票或併入當時 epic。
> 本表為權威登記處；ROADMAP 只放 pointer。GAP-1 各批 code review 之 brief 須附本表以供委員複核「觸發是否已成立」。

| # | 待補完項 | 為何現在不做 | 觸發條件 | 落地時之驗收錨點 |
|---|---|---|---|---|
| G1-R1 | Optuna／搜尋器把每次 trial 寫入 N ledger（生產者接線） | blocked-by: `momentum/Optimization` 屬不完整層，接上即於重寫時作廢 | Optuna／搜尋器重寫或開工時 | 須通過 SPEC Task 2.3 `test_ledger_conformance.py`（接不對即紅） |
| G1-R2 | `optimization_output_service` 產出候選×時間報酬矩陣供 PBO | blocked-by: 該服務從未執行（`results/optimization_results/` 不存在） | 回測引擎首次產生真實 optimization 產出 | PBO 以 `ledger_all_candidates` 來源通過 Task 4.3 守衛 |
| G1-R3 | 前端降級展示面板＋警語文案 | **user-ruling: 2026-08-17 交付範圍 A 不含 frontend（成熟度地圖：frontend 屬不完整層）**〔R8 修正：原標 blocked-by 不成立——Task 3.4 已把 `display_downgrade`／`warning_text_key` 送進 API，空/降級面板現在就能做；四方一致，見延伸檔 A1-10〕 | 使用者要求 UI，或 G1-R1／R2 任一落地 | 消費 API 回應之 `strategy_validation` 三鍵（Task 3.4 已送到）；**前端占位殼已上線**（2026-08-19：`/pending-features`＋優化結果頁灰卡，vitest 對本表機檢） |
| G1-R4 | C1 六條 N 繞過路徑之機器阻止（換 study_name／重複送單／registry 淘汰／重啟／直呼引擎／UI-API 上限差） | blocked-by: G1-R1（生產者未接線前無從阻止；契約層已 fail-closed） | 與 G1-R1 同 | 各條各一測試：繞過後 `read_trial_ledger` 之 N 不低報 |
| G1-R5 | API 層硬擋 promote（拒絕不合格冠軍建 pipeline） | user-ruling: 2026-08-17 採「降級展示＋明顯警語」（Task 3.4 已落警語，不拒絕） | 使用者要求，或該路徑上線後產生誤用 | 把 Task 3.4 之附加改為 4xx 拒絕；契約不變 |
| G1-R6 | adaptive 搜尋下有效獨立 N 之估計 | needs-research: 無公認可驗方法；任何折算係數＝自創 | 有文獻或自研 Monte Carlo 可證偽方法時 | DSR `n_independence` 由 `unverified` 轉為具體值並附方法出處 |
| G1-R7 | MinBTL 上界 `2ln(N)/SR²` 之**誤差帶精確量化**（保守性驗證已於 R8 收回為 Task 3.1 驗收⑨） | needs-research: 誤差帶之通過條件無公認可驗方法（保守性可驗、誤差帶不可）〔R8 修正：原「排程即可做」不是可判定觸發〕 | **具名票 `GAP-1-R7-MC`（owner＝Claude 主委）建立且排入 `docs/ROADMAP.md` 時** | 報告可附誤差帶；`upper_bound` 語意可保留或收緊 |
| ~~G1-R8~~ | ~~`prediction_analyzer.py:155` `np.cumsum` 單利權益~~ | **R8 收回：不再是殘留**——`blocked-by:不在策略路徑` 是 scope 裁決非依賴（三值不成立，四方一致）⇒ 改為 `docs/ROADMAP.md` 之獨立小票「PA-CUMSUM 單利權益改正」，排程＝GAP-1 B4 完工後，執行＝Claude 小任務流程 | — | 改 `cumprod` 或改欄名並停用策略敘事 |
| **G1-R11** | ~~`compute_sharpe` 對「浮點上非精確常數」序列不視為退化~~ **已修（2026-08-18；consult r20 三家一致採 `ptp==0` 位元全等併判、反對相對容差；`sharpe.py`＋`pbo._sharpe_pp_1d` 同步；探針 §V-16；三家 review 可合併＋三家戳記 PASS，**關閉**）** | — | — | 業界（empyrical／quantstats／ffn／vectorbt／pyfolio）皆無容差亦無 ptp；本專案較業界嚴且不自創常數。scope＝編碼值相等，不保證跨異源浮點表達式之數學相等（`GROK-R20-P2-03`） |
| **G1-R10** | `IBacktestEngine` Protocol 宣告 `timeframe`／`risk_free_rate`（現行相容靠 objective 之條件分支，非 Protocol 契約） | blocked-by: SPEC §C 白名單——既有測試檔只允許「加斷言」，改 Protocol 須連動所有實作與 test doubles，超出本票允許改動面〔出處＝`CODEX-R10-P2-04`；數值危險面已由 A1-20 K1 之 fail-loud 收掉〕 | 白名單擴充提案，或使用者裁決 | Protocol 宣告兩參後，`objectives/strategy_backtest.py` 之條件式 `extra_kwargs` 可刪除，改為無條件傳遞 |
| **G1-R9** | ledger 完整性（無事後 top-K 寫入）之**生產者側**證明 | blocked-by: G1-R1（無生產者即無寫入面可證；純統計層無外部候選宇宙 SoT）〔出處＝`CODEX-R8-P0-01`；處置見延伸檔 A1-4〕 | G1-R1 落地 | `PBOResult.universe_scope` 可由 `ledger_recorded_only` 升為 `producer_conformance_verified`，且 Task 3.3 之強制降級可解除 |

## GAP-2 待補完登記（不遺忘機制；2026-08-18 使用者白話閘裁決「殘留須確實寫下來確保未來不忘」）

> GAP-2 SPEC（`docs/GAP2_MARGINAL_IC_SPEC.md` §N，R7 FROZEN）之殘留**同步登記於此**，每條附「為何現在不做」（三值）與**觸發條件**；
> 經六輪三家 adversarial 逐條攻「其實現在就能做嗎」皆判成立（收斂檔 `handoffs/reconcile/20260818-gap2-x-review-r{1..6}/synth.md`）。
> 本表為權威登記處；ROADMAP 只放 pointer；GAP-2 各批 code review 之 brief 須附本表供委員複核「觸發是否已成立」。

| # | 待補完項 | 為何現在不做 | 觸發條件 | 落地時之驗收錨點 |
|---|---|---|---|---|
| G2-R1 | IC→ML 橋本體（讀 `ic_survivors_{case_id}.json` 餵 `xgboost_batch_service.selected_features`，強制 `sample_scope`／OOS 四欄） | user-ruling: 2026-08-18 使用者裁定橋本體 blocked-by ML 層（成熟度地圖：ML／回測屬不完整層、可能重寫；接上即隨殼作廢，同 G1-R1） | ML 層重寫或宣告穩定 | 以 `ic_survivor_contract.json`（`version`）為輸入起新票；消費端 conformance test 讀檔→驗四欄→事件型只在事件樣本訓練 |
| G2-R2 | 以邊際 IC 做 forward-stepwise **選擇**（改變倖存者集合） | needs-research: post-FDR 第二次選擇之多重比較政策（候選域、α 分配、train 選／test 報之誠實揭露）無委員會認可方法；四方偵察同判預設不得開 | 委員會定出政策（可待 registry #4 Pooled IC 樣本量增益後再議） | 政策落地前，SPEC D4 禁止用邊際 IC 改動選擇；落地時須通過 F-MC-1..3 與 §V 對應 mutation |
| G2-R3 | cross-sectional（`analyze_cross_sectional`）路徑之邊際 IC | blocked-by: registry #4 Pooled/Panel IC（xsec 主路徑之 IC 估計量／切分尚未按主線標準重建，先接即隨其重建作廢） | #4 完工 | xsec 報告之 `marginal_ic` 節由 `not_applicable:cross_sectional_mode` 轉 `ok`，並過同一套 §G oracle |
| G2-R5 | nested／frozen final test（讓邊際／組合統計可宣稱獨立 OOS 驗證） | blocked-by: IC 主路徑切分現狀 holdout-only（見上「IC 主路徑切分現狀」節；主線 test 同時供 stage4–6 選擇；本票以 `independent_oos_validation=false`＋`selection_sample="test"` 揭露欄誠實標示） | 主線切分升級（WF／CPCV 接入或 nested holdout 契約成立） | `independent_oos_validation_allowed` 契約值由 `[false]` 升版；R5 落地時 §G O 系列 oracle 於 final test 重跑 |

| G2-R6 | 前端 `tsc --noEmit` 8 條既有紅（`FactorReturnChart.test.tsx` 4／`useFeatureFactory.batchDate.test.ts` 4；最後 commit 早於 GAP-2）；TODO Task 5.1 字面 `tsc rc=0` 與實態差 | blocked-by: 白名單外既有測試檔（§C 只准動四檔）；B5 已驗本批檔 0 紅＋`npm run build` rc=0（三家 R24 一致判不擋收案） | 獨立 frontend 型別／測試修票 | 兩檔 tsc 0 紅；TODO 字面同步 |
| G2-R7 | `test_gap2_golden.py::test_budget_bench_receipt`（n=20000×k=200，~2.5 分鐘）內嵌 B4→B5 gate；並行時互搶 CPU（B4 stamp r22 事故） | needs-research: 無核准 wall／RSS 閾值可作 pass 條件（R7 CODEX-R7-P1-03 已裁為觀測）；拆為獨立 receipt 腳本或標 slow 屬 DX／效能治理取捨 | 效能／DX 票（例：pytest marker `slow`＋收案前獨跑一次） | gate 不含 bench 仍 72 passed；bench receipt 另存 |
| G2-R8 | `SectionStatusNotice.REASON_TEXT` 未含 GAP-2 reason 中文文案（顯示契約字面如 `disabled_by_config`） | user-ruling: 契約字面即 SoT、避免第二份文案表（B5 review 段 B-3 三家接受） | 產品要中文友好文案時開 UX 小票（文案表由委員會定） | 文案表 ⊆ 契約 reasons 且機檢一致 |

> G2-R4（前端表格）**不是殘留**：使用者 2026-08-18 白話閘裁定納入 B5（表格＋`marginal_ic` toggle 預設開）。
> 🏁 **GAP-2 收案（2026-08-19）**：B1–B5 各三家 code review＋三家 RECONCILE-STAMP（收斂檔 `handoffs/reconcile/20260818-gap2-b1-review-r12`／`20260819-gap2-b{2,3,4,5}-review-r{15,18,21,24}`）；延伸檔 A1-1..A1-11；§V 24 條 mutation 最終實跑 receipts `20260819T031612Z/031810Z/031911Z/032022Z-gap2-B{1..4}-probe.log`；§G-1 改前==改後 golden PASS（A1-10）；殘留 G2-R1／R2／R3／R5／R6／R7／R8。
