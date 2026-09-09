# CODEX R5 adversarial review — ICRESULT_PAGING SPEC/TODO

## Verdict：需修補後派工（0 P0／4 P1／2 P2）；W2、W5、W6 已閉合

## CODEX-R5-P1-01
**斷言**: §C-7 同時保留 `result` 與完整 `result_normalized`，會把每個完成 task 的 119 MB 報告至少保留兩棵樹；只留 normalized 可行，但目前 export、task status、apply-transforms 仍直接讀 `task_info["result"]`，不是無條件替換。
**碼證**: SPEC:37,41／TODO:47-49；`ls -la data_cache/reports/ic_report_ic_gatekeeper.json`=118894891、`jq`=`{"st":39346,"meta_keys":39398}`；`_to_json_compatible` 會遞迴新建 dict/list（`api/services/ic_analysis_service.py:2819-2880`），既有 result 寫點 `:1623,:2339,:2631`，export 讀 `:1896`、apply-transforms 讀 `:2532`。RECHECK: `rg -n 'task_info\["result"\]|task_info.get\("result"\)' api/services/ic_analysis_service.py`。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238; api/services/ic_analysis_service.py#4949a7dd28e4
P1 信心度=9/10；這直接違反跨 tier／多 task OOM 優先序，且 `IP-RESID-5` 不能替新造的第二棵樹背書。修法：選一個 canonical normalized storage（或明確 accessor），把所有 direct consumer 遷移後刪 duplicate；G-1 raw-body sha、export、status、apply-transforms 回歸須同過，並補多 task memory receipt。

## CODEX-R5-P1-02
**斷言**: 守衛 raise 的 task 狀態語意與現行行為不一致且 refilter 沒有失敗轉態；現行讀取時 raise 回 500 但 task 仍可見為 completed，現行 refilter 還會先寫入壞 report 再在 `get_result` raise。
**碼證**: 初次完成在 `api/services/ic_analysis_service.py:1618-1623` 設 completed，例外轉 failed 只在 `:1676-1685` 的背景 try；讀取守衛在 `:1772-1791`，route `:346-358` 只轉 500；refilter `:2621-2637` 先 `task_info["result"] = report` 再 `get_result`。TODO:48,56,100,111 卻要求 guard raise「不寫、revision 不變、task failed」且宣稱與現行等價。RECHECK: 以 guard 注入分別跑初次完成與 refilter，查 `/task/{id}`、舊 result、revision。
**來源摘要**: docs/ICRESULT_PAGING_TODO.md#54626e187238; api/services/ic_analysis_service.py#4949a7dd28e4; api/routes/ic_analysis.py#95216b9ddbf0
P1 信心度=10/10；需在 SPEC 固定每個 write path 的 failed/old-result/revision 組合，並加兩條 TestClient 斷言；否則實作會在「保留舊 completed」與「標 failed」間分叉。

## CODEX-R5-P1-03
**斷言**: G-9 的 warm-up、20 次、nearest-rank 第 19 小與固定請求集已可重現，但 LATENCY_GATE 尚未被批次 gate 的收案路徑 fail-closed 消費。
**碼證**: SPEC:57 宣稱 phase gate 與 SIZE_GATE 同規則；TODO:18、119 的 Phase 1/B1 gate 只寫 SIZE_GATE，TODO:189 只要求 `--latency` 印 PASS；`test -e scripts/icresult_paging_phase_gate.sh`→absent，repo 目前沒有 LATENCY_GATE parser。RECHECK: `rg -n 'icresult_paging_phase_gate|LATENCY_GATE|SIZE_GATE' scripts handoffs`，再餵缺行／多行／未知 LATENCY_GATE 的 probe output。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238
P1 信心度=9/10；若 B3 只看 probe rc 或人工 stdout，150/300、100/200、50/100 ms 預算可被跳過。修法：明列 `--latency` 的 gate invocation、唯一行數與 rc 0/1/2 轉換，並以 receipt/negative parser tests 鎖死。

## CODEX-R5-P1-04
**斷言**: 文件稱 snapshot 不可變，但 `_snapshot_result` 回傳可變 `dict`，而 `project_light_view` 偽碼明寫對 report `pop`；未要求 copy-on-write 或 source-unchanged 測試，第一次 light 請求可能破壞後續 summary/feature 投影。
**碼證**: SPEC:37「不可變 snapshot」；TODO:49 型別為 `tuple[dict,int]`，TODO:100 寫 `drop_sections` 各段 `pop`；Phase 1 測試清單 TODO:115-119 沒有「投影後 source 未變／連續兩次 light 相同／light 後 feature 仍可取」斷言。RECHECK: 對同一 fake task 連呼兩次 light，再呼 summary、feature，檢查 normalized snapshot 的七段仍在。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238
P1 信心度=8/10；修法：明定 immutable mapping 或 top-level/deep copy-on-write，並把 source immutability、重複請求、light→feature 順序列入 G-4/G-7 測試。

## CODEX-R5-P2-01
**斷言**: 搜尋 300 ms debounce 同時被分派給 hook (`TODO:125`) 與表格 (`TODO:144`)，責任未定義；兩層都做會變 600 ms，任一層漏做又會使另一條規格失真。
**碼證**: `docs/ICRESULT_PAGING_TODO.md:125` 寫 `fetchSummaryPage` 搜尋去抖 300 ms，`:144` 又寫搜尋框 300 ms；SPEC:42 只定數值未定 owner。RECHECK: `rg -n '去抖|300 ms' docs/ICRESULT_PAGING_SPEC.md docs/ICRESULT_PAGING_TODO.md`。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238
P2 信心度=9/10；修法：指定唯一 debounce 層，另一層只傳值；測試 fake timer 只允許一次 300 ms 延遲與一次 API call。

## CODEX-R5-P2-02
**斷言**: 32-task／8-key LRU 的 `cache_bytes()` 可測性仍不足以證明 process-wide memory cap：未定義是否計入 dict/key overhead，也未鎖定每 task 第 9 組 key 的淘汰策略；`IP-RESID-5` 的 blocked-by 理由只涵蓋既有 `_tasks` lifecycle，不涵蓋本票新增 normalized/cache amplification。
**碼證**: SPEC:41、TODO:65,76 只給 `32×8×index_bytes(n)` 與 33 task case，未定義 `cache_bytes()` accounting 或 9th-key case；現行 `_tasks` 是無界 `api/services/ic_analysis_service.py:432-436`。RECHECK: 33 task×8 key、單 task 9 key、兩個 service instance 分別建立 cache，逐項驗 oldest eviction、`cache_bytes()` 與 process-wide scope。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#6dac04a9a1bd; docs/ICRESULT_PAGING_TODO.md#54626e187238; api/services/ic_analysis_service.py#4949a7dd28e4
P2 信心度=8/10；修法：定義 bytes accounting（至少 array.nbytes＋明確 metadata policy）、每 task eviction、module/process scope，並將三態理由改成「既有 task lifecycle 可另票；本票新增記憶體不得以此豁免」。

### 必答 1–7
1a/1b：一種可變 raw body 的實作是給 `/result` 加 response_model／讓 Pydantic 過濾或重排欄位；G-1 `response.content` sha 能抓到該 fixture 的變化，但不能代替多形狀 coverage。2a：現行 `page.tsx:880-882` 仍讀會被 light 刪的 `rolling_ic_series`；metadata 的 `n_timestamps`、`n_symbols`、`mode`、`event_filter`、`oos_downgrade` 都在 keep 聯集。2b：無；39k artifact 所有 >2 MB 段均在 drop_sections 或經 metadata/filter_log 投影處理，raw metadata 8.4 MB 不是保留 raw 證據。
3a/3b：現行 `ICSummaryTable.tsx:91-106` 把非有限值映成 `-Infinity`、並列回 0，故全 null 時保留輸入序且 asc 會置頂；新 backend contract 的兩向沉底＋feature_name 次鍵才是正確契約，前端舊序應被移除。4a/4b：refilter 後舊 revision 請求 409、無 revision 取新世代；不做戳會把舊 page 與新 total/feature 混在一個 UI，或讓舊 detail 覆蓋新 detail。
5a/5b：既有 `/api/v1/ic/export/{task_id}/{format}`（`ExportButtons.tsx:64-66`→`api/routes/ic_analysis.py:649-687`）是正確出口，Task 2.3 不應逐頁匯出；39k 逐頁在 UI 組裝不可接受且無必要。6：無明顯 ≥10× 不必要複雜；14-feature fixture 的全特徵 sha、contract JSON、mutation 是本票共享出口的合理固定成本。7：B2 一次切換風險較小；IP-RESID-1/2/3/4 三值理由成立，IP-RESID-5 對既有 lifecycle 成立但不能豁免 P1-01 的雙樹。

CHECKLIST: 矛盾/端到端/不可測＝P1-02/03/04；quant＝無；≥10×＝無；OOM/cache＝P1-01＋P2-02；API/型別＝無新 finding；測試＝P1-03/04、P2-01/02；必要性/短命工＝無。
ASSUMPTIONS_VERIFIED: `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` rc=0；todo 同命令 rc=0；`jq -c '{st:(.summary_table|length),meta_keys:(.metadata|keys|length)}' data_cache/reports/ic_report_ic_gatekeeper.json`→`{"st":39346,"meta_keys":39398}`；`shasum -a 256 -c handoffs/20260909-icresult-r5-baseline.sha` rc=0；order/150ms grep 無 stale query key；rolling、export、selection_scope、result writes 已逐碼對照。
TESTS_RUN: `bash scripts/template_check.sh ...`×2；jq；baseline sha；`grep -n 'task_info["result"] =' api/services/ic_analysis_service.py`→1623/2339/2631；`rg -n 'Object.keys(report|Object.entries(report' frontend/src`→僅 pattern comparison；未跑 `pytest tests/governance`、`npm run build`（brief 禁止）。
FAILURES_SEEN: 唯讀複合搜尋曾被 PreToolUse gate 誤判 dispatch；拆成窄命令後完成，無審查驗證失敗。
SCOPE_CHANGES: none（唯讀；只新增本交件檔）。
NUMERIC_OR_SCHEMA_IMPACT: 未改實作；提出結果儲存、task failure semantics、gate/test contract 修補建議。
HANDOFF_OUTPUT: handoffs/20260909-ICRESULTPAGING-X-REVIEW-R5-codex.md
NEXT_BEFORE_B0: 關閉四個 P1，尤其先定 single normalized storage、refilter guard 狀態、LATENCY gate 收案接線、snapshot immutability；再重跑 brief 三條驗收與 baseline。
STATUS: DONE
