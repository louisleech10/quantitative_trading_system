# ICRESULT_PAGING adversarial review R1 — CODEX

## Verdict：需修補後派工

本輪未發現 P0；有 5 個 P1 正確性／契約風險，另有 2 個 P2 驗收與批次風險。審查維持唯讀。

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

## 必答 1–7

1a. 預設 `/result` 仍可能被改變的方式：route 新增 `view` 時若誤把 `view` 傳入 response model、改變 Pydantic 排序／序列化，或在投影前後移動 `deny_factor_in_ok_oos`，raw response 就會變；另一條實際風險是用 canonical SHA 冒充 raw bytes。1b. G-1 只有在 golden 保存 raw HTTP bytes（含序列化順序）時能抓到；目前只比 canonical SHA，抓不到所有 byte-level 改變。

2a. 前端仍讀但 fixture-derived whitelist 可能刪掉的鍵：`metadata.event_filter`（另有 `oos_downgrade`、`isolation`、`ic_window_disclosure`、`period_alignment`、`n_timestamps`、`n_symbols`、`mode`）。2b. 應刪／投影而不是原樣保留的超大段至少是 `filter_log`、`grouped_ic` per-feature map 與 `metadata.selection_scope`；目前尺寸分別約 3.28 MB、9.75 MB、3.27 MB，任一原樣保留都讓 G-5 無法通過。

3a. 不同序：前端 asc 將 `None/NaN/inf` 的 `-Infinity` 置頂且同值保留輸入序；SPEC 後端要求次鍵 `feature_name`，且文字上要求缺值沉底。3b. 應在 contract 固定「None 沉底」作為使用者排序語意，並以 asc/desc 雙向 golden 鎖定；不能讓 `-Infinity` 的偶然數學實作決定 UI。

4a. refilter 後 G-2/G-3 必須限定同一 report generation；以 generation/snapshot id 綁住 page/detail/light，版本不一致回 409 或丟棄舊請求。4b. 不做版本戳會出現舊 total＋新 offset 的混合頁，導致重複／遺漏／詳細圖表不屬於表格列。

5a. 既有格式應走 `GET /export/{task_id}/{format}`；碼證是 `api/routes/ic_analysis.py:649-687` 與 service `1915-1985`，且前端目前已組該 URL。逐頁只應另建明確的 summary-only export。5b. 39k 列的 79 次序列請求在 UI 不應被視為可接受的預設時間；SPEC 沒有 latency budget，應以實測上限、取消／重試策略及 streaming 方案決定，而不是把 request count 當成可接受性證明。

6. ≥10× 不必要複雜之處是 B0 同時生成 39k 投影 golden、200 個 per-feature hash、mutation 骨架、phase gate 與不可入 repo 的實機尺寸 receipt；可縮成固定小 fixture 的全量逐值／null-mask／key-set golden，加一個受控真實報告的尺寸 probe。200 抽樣仍可作補充，但不能代替完整 shape contract；本判斷不放寬任何 quality gate。

7. 先只換表格風險較小；可先驗證 summary API、排序、offset、DOM 與 Set，再切 light/detail 圖表。`IP-RESID-1/2` 的 blocked-by（落檔／既有 golden 影響）成立；`IP-RESID-3` 應暫時 coexist 而非取代，並補 v2/light 同時指定、feature flag on/off、legacy caller 的相容矩陣。

## §1 十一類檢查摘要

矛盾／端到端／不可測驗收／API 相容／測試品質：問題已由 P1-01、03、04、05 與 P2-01 覆蓋。quant 假設、OOM／並行、cache 正確性：本票只做記憶體內投影，未發現新增 quant 或 cache 變更；但 G-5 的實際 payload 尺寸仍須修正契約。過度工程、Agent 可執行性、必要性／短命工：由 P2-02 與必答 6 覆蓋。無額外 P0。

## 被當成事實的未驗證假設（§0）

- `task_info["result"]` 不會在 completed 後被替換：已以 `rg -n 'task_info["result"]' api/services/ic_analysis_service.py` 觀測到建立／更新／refilter 多個寫入點；因此不成立，已列 CODEX-R1-P1-03。
- 前端沒有 per-feature 全量 map 消費者：已以 `rg -n 'Object.keys\(report|Object.entries\(report' frontend/src` 檢查；未命中 IC report 消費者，但不能反推其他 API／新元件永遠不會讀，故仍要求 contract 明確化。
- `metadata.selection_scope` 沒有下游消費者：已以 `rg -n selection_scope momentum api frontend/src` 觀測到 `momentum/Analysis/survivor_contract.py:598,615`；此假設不成立，已納入 P1-01/P1-02。
- 既有匯出端點不存在：已以 `rg -n export api/routes/ic_analysis.py` 並讀 `649-687` 否證；已列 CODEX-R1-P1-05。

ASSUMPTIONS_VERIFIED: 兩份文件模板 PASS；實機報告 `summary_table=39346`、`metadata keys=39398`；各段尺寸與上述路徑／行號已實讀；審查未動碼、未動文件、未跑 governance pytest 或 npm build。
TESTS_RUN: `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` → TEMPLATE PASS；`bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` → TEMPLATE PASS；`jq -c '{st:(.summary_table|length),meta_keys:(.metadata|keys|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"st":39346,"meta_keys":39398}`；多個 `rg`／`nl` 證據探針 → expected matches；未執行程式測試（本票唯讀審查）。
COMPLETENESS_CHECK: `bash scripts/completeness_check.sh --single handoffs/20260909-ICRESULTPAGING-X-REVIEW-R1-codex.md --family codex` 未能執行；PreToolUse 以現有 OPEN committee debt 拒絕，隨後 `bash scripts/gate.sh dispatch` rc=1 明示 `20260909-icresultpaging-x-review-r1` state=OPEN。未使用 bypass／override。
FAILURES_SEEN: baseline `shasum -a 256 -c handoffs/20260909-icresult-r1-baseline.sha` 對 SPEC/TODO 顯示 expected 與 current digest 不同；未修改以掩蓋，視為既有 baseline mismatch。
SCOPE_CHANGES: none；未改碼／SPEC／TODO／根 HANDOFF.md；新增本家族交件檔；暫存清理命令被安全守衛拒絕，未刪除任何暫存檔。
NUMERIC_OR_SCHEMA_IMPACT: 未修改輸出；本報告指出 G-4/G-5 與現有 39,346-run 尺寸證據的契約衝突。
HANDOFF_OUTPUT: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R1-codex.md`
STATUS: DONE
