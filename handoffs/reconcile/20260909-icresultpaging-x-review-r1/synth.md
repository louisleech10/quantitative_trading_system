# Reconcile — 20260909-icresultpaging-x-review-r1

**來源** 20260909-ICRESULTPAGING-X-REVIEW-R1-codex.md, 20260909-ICRESULTPAGING-X-REVIEW-R1-composer.md, 20260909-ICRESULTPAGING-X-REVIEW-R1-grok.md　|　**roster** codex,composer,grok


## 群集 / 處置

三家皆「需修補後派工」；無 P0 未解——composer／grok 之 P0 同一件（G-4∩G-5 互斥），codex 同件列 P1-01。全部為文件層，主委已依下列群集修訂 SPEC（R1 修訂版）與 TODO，R2 複驗。

### Z1 — P0 G-4「逐鍵相等」與 G-5「≤2 MB」互斥（`COMPOSER-R1-P0-01`、`GROK-R1-P0-01`、`CODEX-R1-P1-01`、`GROK-R1-P2-02`）
**處置**：light 投影改為封閉規則住 contract（SPEC §C-6）：`drop_sections` 七段含 `grouped_ic`（單特徵投影由 Task 1.2 供圖）；`filter_log.*`／`metadata.selection_scope` 集合值→`<key>_count`；G-4 改為 (a)–(e) 五條可機檢；G-5 依實測（`handoffs/_light_size_probe.py` → `light_bytes 28019`）收緊為 ≤ 262144 bytes。

### Z2 — P1 `metadata_keep_keys` 由 fixture 推導會漏事件／降級／隔離鍵；`selection_scope` 3.27 MB list（`CODEX-R1-P1-02`、`GROK-R1-P1-01`）
**處置**：白名單改**顯式列舉**＝前端＋後端消費者聯集（SPEC §A 新 receipt：`grep metadata\.` 前端 11 鍵＋service／survivor 讀鍵），禁由 fixture 推導；`selection_scope` 兩 list→計數（survivor 只讀 `scope_id`）；Task 0.1 驗證斷言 keep_keys ⊇ 消費鍵集。

### Z3 — P1 refilter 替換 result 無世代戳，分頁跨代混合（`CODEX-R1-P1-03`、`COMPOSER-R1-P1-02`、`GROK-R1-P2-01`）
**處置**：新增 Task 1.0 `result_revision`（單一 helper `_set_result` 遞增；三寫點改經 helper；源碼守衛計數）；summary／feature 請求帶 `revision`，不符 ⇒ 409；G-2 拆 2a（無篩選）／2b（有篩選＝同參數單次 materialize）；G-7 交錯測試；前端 refilter 後 abort＋重拉。

### Z4 — P1 排序語意與前端不同序、`_finite_or_neg_inf` 單向、G-1 canonical≠raw bytes（`CODEX-R1-P1-04`、`COMPOSER-R1-P1-01`、`GROK-R1-P1-03`）
**處置**：SPEC §C-8 排序契約住 contract `sort_policy`（缺值兩向沉底、並列 `feature_name` 升冪、`feature_name` 字串序），**明文宣告分頁序取代前端本地序＝有意行為變更**；G-6 釘 desc／asc 首 5 列＋並列 fixture 雙向序；G-1 改以 TestClient `response.content` raw sha 為主、canonical 為輔；Task 1.1 禁用 `_finite_or_neg_inf`。

### Z5 — P1 Task 2.3 逐頁匯出重做既有 `/export` 端點（`CODEX-R1-P1-05`、`COMPOSER-R1-P1-03`、`GROK-R1-P1-02`）
**處置**：Task 2.3 改寫——匯出**零改動**，只改 props 型別與 PNG disable 來源；刪「79 次請求」；驗證改為既有匯出測試不改仍 rc=0。

### Z6 — P2 G-5 `pytest.skip` 假通過；200 抽樣不足；B2 一次切換不必要；`IP-RESID-3` 需 precedence 矩陣（`CODEX-R1-P2-01`、`CODEX-R1-P2-02`、`COMPOSER-R1-P2-01`）
**處置**：G-5 artifact 缺席 ⇒ `pytest.fail("blocked-by:artifact")` 非 skip；golden 改 fixture **全部**特徵（14 個）不抽樣；§B 拆 B2a（2.1＋2.2）／B2b（2.3）；Task 1.3 加 v2 flag on／off × view 四格矩陣；`IP-RESID-3` 並存（三家一致）。

### Z7 — 必答 6／7（複雜度與交付順序）
codex：B0 之 200 抽樣＋mutation 骨架＋不可入 repo 尺寸 receipt 為過度 ⇒ 採：全量小 fixture golden＋一個受控真實報告尺寸 probe；mutation 骨架保留（§V 十條，非過度）。三家一致：先後端投影、再 hook＋表格、再圖表／匯出。

Verdict: 需修補後派工——Z1–Z7 皆已落 SPEC（R1 修訂）／TODO；R2 由三家複驗：G-4/G-5 一致性、keep_keys 完整性、revision 契約、sort_policy 雙向 golden、Task 2.3 零改匯出。

---
## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01

**斷言**: 以目前 §G-4 的保留語意，`view=light` 不可能同時滿足 2 MiB 的 G-5 尺寸上限。

**碼證**: SPEC §G G-4 要求 `filter_log`、`grouped_ic` 摘要及 metadata 保留鍵逐鍵相等；同一份實機報告 `jq` 收到 `filter_log=3282724`、`grouped_ic=9745299`、`metadata.selection_scope=3273340` bytes，單一段已超過 `2097152`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[MAJOR] 信心度=High。這不是實作技巧問題，而是不可同時滿足的驗收條件；若照做，G-5 必紅，或 agent 會擅自刪／截斷資料而違反 G-4 與「不改數值」。應在 SPEC/TODO 明確定義 light 的投影（例如只保留 FilterFunnelChart 實際需要的欄位、grouped summary 的摘要形狀，以及 `selection_scope` 是否移至單獨端點），再以投影後真實 bytes 驗收；不能只把段名列為「原樣」。RECHECK: `jq -c '.filter_log,.grouped_ic,.metadata.selection_scope,.grouped_ic' data_cache/reports/ic_report_ic_gatekeeper.json | wc -c` 並重跑 `jq` 各段尺寸 receipt。

## CODEX-R1-P1-02

**斷言**: Task 0.1 以單一 fixture 生成 `metadata_keep_keys`，可能把事件／降級／隔離／期間對齊等實際 run 的 metadata 鍵排除，造成 light 前端顯示退化。

**碼證**: TODO §0.1 實作要點 ②將白名單初值定為 fixture metadata 的非 per-feature 描述子；前端證據：`page.tsx:188-212` 讀 `metadata.n_timestamps/n_symbols/mode`，`DegradedBanner.tsx:17,26` 讀 `event_filter/oos_downgrade`，`IsolationNote.tsx:13` 及 `icIsolation.ts:45` 讀 `isolation/ic_window_disclosure`，`PeriodAlignmentBanner.tsx:13` 讀 `period_alignment`；`rg -n 'task_info["result"]' api/services/ic_analysis_service.py` 亦顯示完成後除 refilter 外有建立／替換結果的路徑，不能把一個 fixture 當全部 schema。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MAJOR] 信心度=High。缺鍵會被既有元件當成未提供而不渲染，形成靜默行為變更；`G-4` 只對該 golden／單一報告比對不足以證明跨 mode 的白名單完整。修法是把保留鍵定義成受版本化 contract 的所有已支援 producer／consumer 聯集，或先明確宣告事件模式各自的 light contract，並用各模式 fixture 驗證；同時說明 `metadata.selection_scope` 的誰讀、是否延後載入。RECHECK: `rg -n 'metadata\.|selection_scope' frontend/src api momentum/Analysis`，並對普通、事件、降級三種 report 做 keep-key 集合對照。

## CODEX-R1-P1-03

**斷言**: 分頁請求沒有 report 版本／snapshot 契約，refilter 在請求中途替換 `task_info["result"]` 時，G-2/G-3 可能把不同結果的頁面拼成一份。

**碼證**: `api/services/ic_analysis_service.py:1772-1794` 只在 lock 內取 result，之後解除鎖再 normalize/project；`refilter:2627-2637` 會在 lock 內 `task_info["result"] = report` 後回完整結果；`api/routes/ic_analysis.py:597-607` 的 refilter 沒有 view／版本參數；TODO Task 2.1 只寫成功後 reset offset，沒有 generation、ETag 或 snapshot id。

**來源摘要**: api/services/ic_analysis_service.py#4949a7dd28e4

[MAJOR] 信心度=High。客戶端可能先抓舊 total/page 1，再在 refilter 後抓新 page 2；結果列數、排序與詳細資料不再是同一集合，且 `offset` 的語意已改變。修法是為 result generation／immutable snapshot 建立明確 response 欄位與 request echo，所有 summary/detail/light 請求要求同一版本；版本不符回 409／重置，而非靜默接受。若產品允許 refilter 取代結果，也要規定 UI 取消舊請求並丟棄舊版本。RECHECK: TestClient 以延遲投影與 refilter 交錯，斷言不會混合 generation。

## CODEX-R1-P1-04

**斷言**: SPEC 宣稱的排序語意與現行前端並非同序，而且 G-1 使用 canonical SHA 不能證明「位元組級」不變。

**碼證**: `ICSummaryTable.tsx:91-105` 把非有限值轉 `-Infinity`；desc 時缺值沉底、asc 時缺值置頂，tie 回 0 且沒有 `feature_name` 次鍵。SPEC §P Task 1.1/§G G-2 又要求 `_finite_or_neg_inf` 加 `feature_name` 次鍵並宣稱 None 沉底；SPEC §G-1 驗的是 `canonical_sha`（TODO §0.1 也寫 `canonical_sha`），不是原始 response bytes 的 hash。

**來源摘要**: frontend/src/components/ic-analysis/ICSummaryTable.tsx#2e94c8c4c522

[MAJOR] 信心度=High。反例：兩列 `icir=null`，asc 時現行前端將它們放在所有有限值前且保留輸入順序；後端若依次鍵排序會把它們按名稱排，且若採 None 沉底則整體位置不同。另有相同 JSON 值但 key 順序／序列化格式改變時 canonical hash 仍可能相等，無法支撐 C-1 的 byte-level claim。修法：在 contract 固定 asc/desc 的 missing policy、tie-breaker 與 comparator，加入有限值／null mask 的順序 golden；G-1 同時保存 raw HTTP body bytes SHA（canonical SHA 只能作輔助）。RECHECK: 用兩個有限值、兩個 `null`、同值不同名的 rows 對照前端 comparator、後端 comparator 與 raw-body digest。

## CODEX-R1-P1-05

**斷言**: Task 2.3 將既有格式匯出改成前端逐頁抓 summary，會重做已存在的後端匯出契約，並可能改變非 summary 匯出內容。

**碼證**: `api/routes/ic_analysis.py:649-687` 已有 `GET /export/{task_id}/{format}`；`api/services/ic_analysis_service.py:1915-1985` 支援 `json`、`ai_json`、`csv_summary`、`csv_detailed`、`markdown`、`hdf5`，而 `ExportButtons.tsx:64` 已組出該後端 endpoint。TODO Task 2.3 又指定 `fetchSummaryPage(limit=limit_max)` 串接 79 頁。

**來源摘要**: api/routes/ic_analysis.py#95216b9ddbf0

[MAJOR] 信心度=High。若只需既有 CSV/JSON/Markdown/HDF5，直接呼叫後端端點保留格式、sanitizer、module 與 freshness 語意；逐頁路徑只適合新增「分頁表格資料」下載，不能默默取代既有 exporter。79 次序列請求在 UI 也不應是預設的完整匯出方案，時間與中途失敗風險均未定量。修法：Task 2.3 先列出每個 format 的權威 endpoint／是否需要新 export API；既有格式維持後端出口，若要新增 summary export，定義 streaming、取消、重試、權限與檔案格式不變的測試。RECHECK: `rg -n 'export|fetchSummaryPage' frontend/src/components/ic-analysis/ExportButtons.tsx api/routes/ic_analysis.py api/services/ic_analysis_service.py`。

## CODEX-R1-P2-01

**斷言**: G-5 尺寸測試在實機報告缺席時 `pytest.skip`，可以讓 CI rc=0 卻沒有測到尺寸；200 特徵抽樣也不足以證明 39,346 特徵的逐特徵映射完整。

**碼證**: TODO Task 1.3 驗證明寫「檔案缺席時 `pytest.skip`」，同時 B1 gate 要求 skip=0；同一 Task 0.1 的 B-2 僅「等距抽 200」per-feature sha，完整集合另行 hash。SPEC §G-5 的實機尺寸資料又禁止進 repo。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MINOR] 信心度=High。此設計在沒有 `data_cache` 的環境是 unsampled pass，不能作為 2 MiB gate。修法：缺少受控 artifact 應 fail/UNCOVERED 而非 skip=0；另以已提交、不可變且不含敏感資料的結構 fixture 驗 shape／所有 key，尺寸則使用實跑 receipt 並由 gate 明確標為 blocked-by artifact，而不是聲稱 PASS。

## CODEX-R1-P2-02

**斷言**: B2 將 hook/store、表格、匯出與所有圖表一次切換不是必要的風險最小化策略；表格可先以 summary endpoint 驗證，且 `IP-RESID-3` 的 coexist 裁決尚未被 API precedence 測試落實。

**碼證**: TODO §B 將 2.1、2.2、2.3 綁成一次切換，理由只有「切一半會出現中間態」；但 Task 2.2 已有獨立的 `page: ICSummaryPage` 與 DOM ≤ limit 驗證。現行 v2 路徑在 `ic_analysis_service.py:1789-1810` 由 `schema_version=2` 選擇，SPEC §C 又要求 `view=light` 與 v2 互斥；§N `IP-RESID-3` 只寫日後 consumer 出現才統一，未定義 config 開啟、同時 query、legacy caller 的完整矩陣。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[MINOR] 信心度=Medium。較小風險的交付順序是先後端投影，再 hook/types，再表格，再其餘圖表／匯出；每步有可回退 gate，避免一次變更掩蓋缺段。`IP-RESID-1/2` 的 `blocked-by` 理由本身成立（改 reporter 會改落檔與既有 golden），但它們不能替 G-5 的矛盾背書；`IP-RESID-3` 目前應 coexist 以保留既有版本化 top-N 契約，不應未經 migration 直接取代，卻必須補 precedence／backward-compat 測試與明確移除觸發條件。

## COMPOSER-R1-P0-01

**斷言**: G-4 要求 light 保留 `filter_log`／完整 `grouped_ic`／`metadata` 非描述子鍵（含 `selection_scope`）與全量**逐鍵相等**，與 G-5「39,346 特徵 light canonical JSON ≤ 2 MB」在實機報告上**互斥**，按現 SPEC 實作 G-5 必永 FAIL。

**碼證**: `jq -c '{filter_log:(.filter_log|tojson|length), grouped_ic:(.grouped_ic|tojson|length), selection_scope:(.metadata.selection_scope|tojson|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"filter_log":3282724,"grouped_ic":9745299,"selection_scope":3273340}`（單三段已 16.3MB）；SPEC §G G-4／G-5；Task 1.3／0.1 `metadata_keep_keys` 演算法。RECHECK: 實作 `project_light_view` 後對 fake task 載入同檔量 canonical bytes。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[BLOCKING] 信心度=High。修法（二選一）：①放寬 G-4——light 只保留 UI 必要段（`filter_log` 摘要、`grouped_ic` 聚合層、`selection_scope` 改 `scope_id` 摘要或移出 light）；②放寬 G-5——改為「首屏可互動」延遲指標（B34）為主、bytes 門檻僅對 `summary_page`+`feature/{name}`。不可雙標逐鍵相等又 ≤2MB。

---

## COMPOSER-R1-P1-01

**斷言**: 後端 `paginate_summary` 次鍵 `feature_name` 與前端 `ICSummaryTable` `getSortValue`（tie 回傳 0、字串欄位全 `-inf`）不同序；UAT 39k 報告 `icir` 全 null 時，**使用者首列必變**，SPEC 未宣告此行為變更亦無 §G 釘選。

**碼證**: `ICSummaryTable.tsx:91-106`；`momentum/Analysis/ic_reporter.py:23-29` `_finite_or_neg_inf`；`jq '[.summary_table[].icir]|map(select(.!=null))|length' data_cache/reports/ic_report_ic_gatekeeper.json` → `0`；SPEC Task 1.1「次鍵 feature_name」。RECHECK: 對同報告比對前端 desc icir 首列 vs `/summary?sort_by=icir&order=desc&limit=1` 首列 `feature_name`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[MAJOR] 信心度=High。修法：§G 增 G-6「icir 全 null 時首列 `feature_name` 等於 paginate 結果」；或 SPEC §C 明訂「分頁序取代前端本地序」並更新 B34 預期。實作時 `sort_by=feature_name` 須用字串比較，不可走 `_finite_or_neg_inf`。

---

## COMPOSER-R1-P1-02

**斷言**: G-2 未定義 `q`／`pass_class` 下「逐頁串接==全量」的基線集合；refilter 替換 `task_info["result"]`（`:2631`）卻無 result 版本戳，summary 分頁 API 無法偵測 stale 頁，與 Task 2.1「refilter 重置 offset」不足以消除 in-flight 競態。

**碼證**: SPEC §G G-2；`api/services/ic_analysis_service.py:2627-2637`；TODO Task 2.1 邊界③。RECHECK: refilter 中途並發兩個 `/summary?offset=0` 與 `offset=50`，比對 `total`／首列是否一致。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MAJOR] 信心度=High。修法：G-2 分兩條——無篩選串接==全量；有篩選串接==同參數單次 materialize。light／summary 回應加 `result_revision`（config_hash 或 refilter 計數）；前端 refilter 後 abort 全部 summary/detail 請求。

---

## COMPOSER-R1-P1-03

**斷言**: Task 2.3 要求 `ExportButtons` 以 `summary?limit=limit_max` 逐頁串接匯出，但現行 JSON／CSV 已走 `/export/{task_id}/{format}` 全量後端路徑；照 SPEC 改逐頁會**降級**匯出且與 §C 不變式 1（匯出走完整 result）精神衝突。

**碼證**: `ExportButtons.tsx:46-66`（`triggerDownload` → `/api/v1/ic/export/...`）；`api/routes/ic_analysis.py:649-656`；`ic_analysis_service.py:1961-1967` `generate_summary_csv` 讀全量 `summary_table`；SPEC Task 2.3／TODO 2.3「逐頁串接」。RECHECK: `rg "summaryTable" frontend/src/components/ic-analysis/ExportButtons.tsx` → 僅 PNG 按鈕用 prop。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MAJOR] 信心度=High。修法：Task 2.3 改寫——`csv_summary`／`json`／`markdown`／`hdf5` **維持**既有 export 端點（讀預設 `/result` 全量，G-1 保護）；light 後僅調整 `module_statuses` prop 來源。刪「79 次請求」驗收，改斷言 export 端點仍 200 且列數==`total_features`。

---

## COMPOSER-R1-P2-01

**斷言**: TODO §B B2 稱 2.1+2.2+2.3 必須一次切換，但 2.3 匯出與後端 export 重疊，可延後；真正中間態風險僅「light 已開但表格仍全量」——**2.1+2.2 同批即可**，不必捆 2.3。

**碼證**: `docs/ICRESULT_PAGING_TODO.md` §B B2 合併理由；`ExportButtons.tsx` 現況（見 P1-03）。RECHECK: 評估 B2 拆為 `{2.1,2.2}` + `{2.3}` 兩 commit 是否仍滿足 B34。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MINOR] 信心度=Medium。修法：§B 表註明 2.3 可跟隨 2.1/2.2 之後獨立合併；合併理由限縮為 hook+表格。

---

## GROK-R1-P0-01

**斷言**: SPEC §G G-4（light 保留全量 `filter_log`／`grouped_ic` 摘要並與全量逐鍵相等）與 G-5（39k 實機 light canonical JSON ≤ 2,097,152 bytes）在 `data_cache/reports/ic_report_ic_gatekeeper.json` 上互斥，照做則 Phase 1 無法同時通過。

**碼證**: FACT-RECEIPT 段位元組 `filter_log 3282725`、`grouped_ic 9745300`、`metadata` 內 `selection_scope 3273340`；venv 投影實測留 filter_log 去 grouped_ic ≈ 3,309,731 > 2,097,152；去二者 ≈ 26,997。SPEC §G G-4／G-5；TODO Task 1.3 實作要點③。`RECHECK:` 重跑本檔「必答 2b」表內三組 dumps 長度。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[BLOCKING] 信心度=High。失敗：agent 實作後 G-5 紅或為過 G-5 私自砍 G-4 段造成漏斗／圖表空白。修法：①G-4 改為「漏斗標量投影」（每 stage 只留計數／理由摘要，不留 39k 名清單）且 `grouped_ic` 不進 light（改走 Task 1.2／featureDetail，與 TODO 2.3 圖表方向一致）；②`metadata_keep_keys` **排除** `selection_scope` 或只留 `scope_id`／`n_tests`／`method`／hash；③G-5 門檻對齊修後實測（可仍 ≤2MB）。

## GROK-R1-P1-01

**斷言**: TODO Task 0.1 以「值為 `{category,layer,name}` 描述子以外皆保留」建 `metadata_keep_keys`，會把 3.27 MB 的 `selection_scope.universe_features`／`evaluated_features` 塞进 light，本身即可單獨打破 G-5。

**碼證**: 實機 `selection_scope` keys＝`scope_id,universe_features,evaluated_features,n_tests,method,base_universe_hash,split_label`；兩 list 各 ~39k、字串化各 ~1.63 MB。`frontend/src` 無 `selection_scope` 讀取；survivor 只取 `scope_id`（`survivor_contract.py:598`）。TODO `:26` 啟發式。`RECHECK:` `jq '.metadata.selection_scope|keys' …`＋`grep -rn selection_scope frontend/src`。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MAJOR] 信心度=High。修法：contract 顯式列出保留鍵（含前端揭露鍵）並 **deny-list／省略** 大 list；或 light 內 `selection_scope` 瘦身為無 list 的摘要物件。

## GROK-R1-P1-02

**斷言**: TODO Task 2.3 規定 `ExportButtons` 改以 `fetchSummaryPage` 逐頁串接匯出，與現行已可用的後端 `GET /api/v1/ic/export/{task_id}/csv_summary`（讀記憶體 result）重複且更差。

**碼證**: `ExportButtons.tsx:47-66` 已呼叫 `/export/${taskId}/${format}`；`summaryTable` 僅 PNG disable（`:201`）。`ic_analysis_service.py:1961-1967` `csv_summary` 路徑。TODO Task 2.3「逐頁拉齊」「79 頁」。`RECHECK:` 讀上述行號；對 completed task `curl` export（若有 task）應一次回 CSV。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#cd1471b99995

[MAJOR] 信心度=High。修法：2.3 改為「匯出繼續走既有 `/export`；只把 props／型別改吃 `ICReportLight`（需 `module_statuses`）；PNG 用 `summaryPage.total>0` 代替全量表」。從 B2 合併理由中移除「匯出必須同批重寫」。

## GROK-R1-P1-03

**斷言**: Task 1.1 排序加 `feature_name` 次鍵後，與現行前端 `getSortValue`（並列 return 0）及 `get_top_features`（無次鍵）不同序，會改變使用者看到的第一列，SPEC 未標為有意行為變更。

**碼證**: `ICSummaryTable.tsx:91-106`；`ic_filter_orchestrator.py:2969-2972`；SPEC Task 1.1「次鍵 feature_name」。反例見必答 3a。`RECHECK:` 四列並列 fixture 比對三實作序。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[MAJOR] 信心度=High。修法：在 §C／Task 1.1 寫明「分頁排序以決定性次鍵為準，允許與舊前端 stable 序不同」；禁止 `sorted(..., reverse=True)` 作用於含次鍵的 tuple；測試鎖定並列序。

## GROK-R1-P2-01

**斷言**: SPEC／TODO 未定義 refilter 置換 result 時分頁／G-2 串接的世代語意，存在跨頁混代競態。

**碼證**: `refilter` `:2627-2631` 覆寫 result；TODO 2.1 只重置 `offset=0`，未 abort 進行中的 summary 請求；SPEC §G G-2 無 generation。`RECHECK:` 讀 refilter 與 TODO 2.1 邊界。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[MINOR] 信心度=Medium。修法：回應加單調 `result_generation`（或 etag=sha 前 12）；或文件規定 refilter 時前端 abort＋丟棄舊頁，G-2 僅適用單一 generation。

## GROK-R1-P2-02

**斷言**: Task 1.3／G-4 所稱 `grouped_ic`「摘要（非 per-feature 部分）」未定義可機檢形狀，而實機 `grouped_ic.by_year`／`by_category`／`by_layer` 皆為每特徵 map（合計約 9.7 MB），agent 極可能整段原樣保留。

**碼證**: `by_year` bytes≈4,862,625、每 year 鍵數=39346；`page.tsx:225`／`GroupedICBarChart` 依 `featureName` 取單特徵——Phase 2 應改吃 `featureDetail`（TODO 2.3）。`RECHECK:` 對 `grouped_ic.by_year` 任一 year `length`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#ee307ca7b037

[MINOR] 信心度=High。修法：明文「light **刪除** `grouped_ic` 全段；單特徵投影由 Task 1.2 回 `{group: value}`」；G-4 刪除對 grouped_ic 的逐鍵相等要求。

---

ASSUMPTIONS_VERIFIED: template_check 兩份 PASS；jq 39346/39398；result 三賦值點；export 端點與 ExportButtons 接線；selection_scope／filter_log／grouped_ic 位元組；前端 metadata 消費者清單；排序三路差異  
TESTS_RUN: template_check spec/todo rc=0；jq 形狀；shasum baseline rc=1（僅 SPEC/TODO 2 檔漂移）；venv 投影尺寸三組；grep／讀碼（未跑 pytest governance／npm build，依 brief）  
FAILURES_SEEN: baseline SPEC/TODO hash 與工作區不一致（唯讀未修）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）  

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R1-grok.md`

STATUS: DONE
