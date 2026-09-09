# CODEX R2 review — ICRESULT_PAGING

## Verdict：需修補後派工

### 必答對照

1a. G-1 仍可能被 route 加入 `response_model`、或把無 `view` 的 dict 經新投影／重建後改變欄位順序或欄位集合；現行 route 沒有 `response_model`。1b. G-1 使用 TestClient 的 `response.content` SHA，能抓到實際 HTTP body 的上述變化；canonical SHA 單獨不能抓到所有位元組差異。

2a. R2 實查沒有找到「前端仍讀、但 R1 `metadata_keep_keys` 漏列」的鍵：`page.tsx` 的 `metadata.mode` 與 §A receipt 列出的 `n_timestamps`／`n_symbols` 等鍵均在 TODO Task 0.1 的顯式集合；`selection_scope` 也未見前端消費。2b. 實機 receipt 中的已知大段都已列入七段 drop 或 `selection_scope`／`filter_log` 計數規則，沒有另一個可有證據指出的漏列段；目前真正未封閉的是 `filter_log.*` 的路徑／輸出形狀語意（見 CODEX-R2-P1-04）。

3a. 不同序。現行前端把非有限值映成 `-Infinity`，所以 asc 會把缺值置頂且同值不做 `feature_name` 次鍵；SPEC/TODO 的 contract 則要求缺值兩向沉底、並列按名稱升冪。例如 `[A=0.5,B=0.9,C=None]` asc：前端為 `[C,A,B]`，後端契約為 `[A,B,C]`。3b. 後端契約較正確，且文件已明文接受分頁序取代舊前端 stable 序；不得再把舊前端序當 golden。

4a. 帶舊 `revision` 的 summary/feature 請求應 409；不帶 revision 的請求應使用當前世代。refilter 成功後前端應取消舊請求並從 offset 0 重拉。文件尚未定義「讀取 result/revision 後、投影完成前 refilter」的原子 snapshot 語意。4b. 沒有 snapshot/回應世代檢查時，舊報告頁可在 refilter 後才回到 UI，造成跨世代畫面；單純在請求開始時檢查 revision 不能消除 TOCTOU。

5a. 既有 `/export/{task_id}/{format}` 是正確出口：route 支援 json、ai_json、csv_summary、csv_detailed、markdown、hdf5，`ExportButtons` 已直接呼叫它；Task 2.3 R1 修訂為不改匯出是正確的。5b. 因此不應在 UI 逐頁抓 39k 列；若另造逐頁匯出，79 次請求的可接受時間、取消、重試與部分失敗均未定義，不能作預設方案。

6. 沒有發現 ≥10× 的不必要複雜度：14 特徵小 fixture 的完整 feature golden、單一真實 artifact size probe、以及 mutation 骨架分別守集合映射、尺寸與假綠，均對應本票的 byte/schema 風險。不能把受控 artifact 缺席時的 gate 衝突當成可省略測試的理由。

7. `IP-RESID-1/2` 的 reporter/storage 邊界與 `IP-RESID-3` coexist 仍可並存；但 `IP-RESID-3` 必須補 v2 flag × `view` precedence 矩陣。`IP-RESID-4` 的 needs-research 已不成立：實際 artifact 與現有 FilterFunnelChart 已足以證明鍵名／形狀不相容，應收回 Task 2.3 的實作與測試 gate（CODEX-R2-P1-04）。

## CODEX-R2-P1-01

**斷言**: SPEC 與 TODO 對 G-6 的四列 asc 預期互相矛盾，會讓同一實作同時被判定通過與失敗。

**碼證**: SPEC §G G-6（`docs/ICRESULT_PAGING_SPEC.md:51`）明定四列 desc／asc 都是 `[A,B,C,D]`；TODO Task 1.1 驗證（`docs/ICRESULT_PAGING_TODO.md:75`）卻明定 asc 是 `[B,A,C,D]`。同一 TODO `:63-64` 的 comparator 又規定缺值兩向沉底、有限值並列以 `feature_name` 升冪，依此 asc 應為 `[A,B,C,D]`。RECHECK: `nl -ba docs/ICRESULT_PAGING_SPEC.md | sed -n '45,52p'; nl -ba docs/ICRESULT_PAGING_TODO.md | sed -n '61,76p'`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#17e213a6d472

[MAJOR] 信心度=High；這是可機檢的 acceptance contradiction，不是實作者選擇。修法是讓 TODO 與 SPEC 共用 contract 產生的同一 golden，並刪除 `[B,A,C,D]` 的過期期待；同時以三列 fixture `[A,B,C]` 保留 asc 的有限值主鍵驗證。

## CODEX-R2-P1-02

**斷言**: `result_revision` 雖已加入 light／summary／feature 的目標契約，refilter 的成功回應與前端 reload handshake 仍未定義，且 lock 外投影留下跨 refilter 的 TOCTOU。

**碼證**: SPEC §C-7（`docs/ICRESULT_PAGING_SPEC.md:37`）要求所有投影回應帶 revision，TODO Task 2.1（`docs/ICRESULT_PAGING_TODO.md:122-125`）只寫「取回應值」後 abort/reload，沒有定義 `/refilter` response schema 或如何取得新 revision。現行 route/service（`api/routes/ic_analysis.py:597-615`、`api/services/ic_analysis_service.py:2621-2637`）的 refilter 回 `get_result(task_id)`，目前只回報告；`get_result` 在 `api/services/ic_analysis_service.py:1772-1794` 於 lock 內取 result 後，lock 外才 normalize/return。RECHECK: `rg -n 'result_revision|refilter|def get_result' docs/ICRESULT_PAGING_SPEC.md docs/ICRESULT_PAGING_TODO.md api/routes/ic_analysis.py api/services/ic_analysis_service.py frontend/src/hooks/useICAnalysis.ts`；用延遲投影的 TestClient 交錯 refilter 與 summary/feature，檢查舊 revision response 是否可在新 revision 後抵達。

**來源摘要**: api/services/ic_analysis_service.py#4949a7dd28e4

[MAJOR] 信心度=High；前端無法可靠地從目前 refilter response 更新 `resultRevision`，而即使 request 開始時 revision 通過，refilter 也可能在 result 複製後、投影完成前替換結果，讓舊世代 response 晚到。修法：明確定義 refilter 回應至少含 `{result_revision, report/view}`（或明確要求再 GET light），並讓 projection 使用不可變 `(report, revision)` snapshot；response 套用前以 revision 丟棄舊資料。G-7 也要加入「投影中途 refilter」案例，不只測 request 前後的 stale 409。

## CODEX-R2-P1-03

**斷言**: G-5 的 artifact 缺席行為與 B1 gate 的必須 `rc=0`／`UNCOVERED=0` 無法在乾淨 checkout 同時成立，造成尺寸 gate 永遠紅或被繞過。

**碼證**: SPEC §G-5（`docs/ICRESULT_PAGING_SPEC.md:50`）與 TODO Task 1.3（`docs/ICRESULT_PAGING_TODO.md:110`）要求缺 artifact 用 `pytest.fail("blocked-by:artifact")`，不是 skip；但 TODO §B gate（`docs/ICRESULT_PAGING_TODO.md:19`）要求 B1 `pytest tests/api/test_icresult_paging.py` rc=0 且 `UNCOVERED=0`。本工作樹的可追蹤狀態也證實新 contract/projection 尚不存在（`test -e momentum/Analysis/contracts/ic_result_paging_contract.json` rc=1；`test -e api/services/ic_result_projection.py` rc=1），而 `data_cache` 依專案規則不進版本庫。RECHECK: 在沒有 `data_cache/reports/ic_report_ic_gatekeeper.json` 的 checkout 直接跑 B1 gate，記錄 pytest rc、`blocked-by:artifact` 與 UNCOVERED 的轉換規則。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#376e43979064

[MAJOR] 信心度=High；目前設計沒有可接受的「artifact 缺席但 gate 不假綠」狀態。修法二選一：把 artifact size probe 分離成明確的 blocked/receipt gate，B1 只要求可在 repo fixture 完成的 G-1～G-4；或讓 gate 對 `blocked-by:artifact` 產出機器可識別的非 PASS 結果並在 B1 acceptance 明確允許該三態。不能同時把 pytest FAIL 當正常缺席、又宣稱 B1 必須 rc=0。

## CODEX-R2-P1-04

**斷言**: R1 新增的 `filter_log.*` light 投影規則仍不能產出現有 `FilterFunnelChart` 所需的 `input`／`output` 形狀，`IP-RESID-4` 已是可重現的契約缺陷而非 needs-research。

**碼證**: SPEC §C-6（`docs/ICRESULT_PAGING_SPEC.md:36`）與 TODO Task 1.3（`docs/ICRESULT_PAGING_TODO.md:98-100`）只規定 wildcard 路徑中的 list/dict 改成 `<key>_count`、scalar 原樣；`FilterFunnelChart`（`frontend/src/components/ic-analysis/FilterFunnelChart.tsx:18-23`）卻對每一 stage 直接讀 `values.input`、`values.output`。實機 artifact 的 `jq -c '[.filter_log | to_entries[] | {stage:.key, keys:(.value|keys)}]' ...` stdout 顯示六種 stage，鍵是 `input_features`／`output_features`、`feature_count_original`／`feature_count_filtered` 等，沒有 `input`／`output`；例如 stage0 只有 `input_features`、`removed_nan_features`，stage5 的 `output_features` 還是 object。`frontend/src/lib/types.ts:2155-2163` 也只宣告 `input`／`output`。RECHECK: `jq -c '[.filter_log | to_entries[] | {stage:.key, keys:(.value|keys)}]' data_cache/reports/ic_report_ic_gatekeeper.json`；以同一 artifact 經 contract projection 後渲染 `FilterFunnelChart`，斷言不產生 `undefined`／`NaN`。

**來源摘要**: frontend/src/components/ic-analysis/FilterFunnelChart.tsx#290941d096c2

[MAJOR] 信心度=High；照 TODO 實作後漏斗可能仍顯示空白／NaN，或將 stage object 整體誤計數，直接違反「light 不靜默補值」與圖表可用性。修法需在 contract 明定 canonical stage adapter（如何由各實際 stage 的欄位取得 input/output、object 的 count 語意、無法推導時顯示不適用），並把 adapter 與 artifact shape fixture 納入 B1/B2b gate；不能把問題留在 `IP-RESID-4 needs-research`。

## CODEX-R2-P1-05

**斷言**: B2a 的 gate 允許 light fetch／summary table 已切換，但 `page.tsx` 的 per-feature 圖表仍從已被 light drop 的 `report` 讀取，因而形成已可合併但功能退化的中間態。

**碼證**: TODO §B 將 B2a 定為只含 Task 2.1／2.2（`docs/ICRESULT_PAGING_TODO.md:14-19`），而 Task 2.3 才把圖表改成 `featureDetail`（`:106-112`）。目前 page 的 `sectionSplit` 仍從 `report?.ic_decay`／`quantile_returns`／`grouped_ic`／`turnover_analysis` 建立（`frontend/src/app/ic-analysis/page.tsx:216-228`），圖表也仍讀 `sectionSplit...map` 與 `report?.rolling_ic_series`（`:860-901`）；但 light contract 已把這些七段 drop（SPEC `:36`, TODO `:98`）。`useICAnalysis.fetchResult` 目前仍抓無 view 的全量 `ICReport`（`frontend/src/hooks/useICAnalysis.ts:101-108`），正好說明 B2a 需要跨此切換，不能假定現有 page 會自動適配。RECHECK: 只套用 B2a 的 hook/store/table diff 後，以 light response mount `page.tsx`，斷言每個 per-feature panel 不是讀 dropped map，而是明確呈現 loading/detail 狀態；再跑 B2b gate。

**來源摘要**: frontend/src/app/ic-analysis/page.tsx#3516fb531478

[MAJOR] 信心度=High；B2a 的既定測試只覆蓋 hooks/store/table 與 tsc，沒有 page 的缺段渲染 gate；首屏可互動不等於六個 per-feature 圖表不退化。修法：要嘛把 B2b 納入同一個不可分割的 UI cutover，要嘛在 B2a 明確提供 featureDetail loading/empty adapter 並新增 page integration test；同時把 FilterFunnel 的 shape gate（P1-04）納入對應批次。

## CODEX-R2-P2-06

**斷言**: `collection_to_count_paths` 的 `filter_log.*` wildcard 沒有定義 path matcher、遞迴深度、dict target 與 no-match 行為，實作者可能得到不同的 light schema。

**碼證**: SPEC §C-6 只給字串 `filter_log.*`（`docs/ICRESULT_PAGING_SPEC.md:36`）；TODO Task 0.1 只把它寫入 contract（`docs/ICRESULT_PAGING_TODO.md:26`），Task 1.3 的 `_collections_to_counts` 又只說「對每個節點」轉換（`:98-100`），沒有定義 `*` 是 stage key、stage 內 key、還是任意深度；也未定義 stage 不含集合、集合巢狀於 object、或未知 stage 的結果。實機 artifact 同時存在 array、object、scalar 與巢狀 object（上列 P1-04 的 jq receipt）。RECHECK: 對包含 stage0/stage1/stage3/stage5/stage6 的小型 shape fixture，分別驗 literal path、one-level glob、nested glob 與 no-match；要求每種 matcher 只產生一個固定 golden。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#376e43979064

[MINOR] 信心度=High；這是實作不可測的 contract ambiguity，且會令 G-4 filter_log golden 依 agent 解讀漂移。修法：在 contract schema／Task 1.3 明定 glob 僅匹配 stage 名或明定 JSONPath-like one-level traversal，並規定 target type、未知 stage、no-match 的 fail-closed 行為；以現有 artifact shape 固定 golden。

## 被當成事實的未驗證假設（§0）

無新增列為 finding 的未驗證假設。R2 實查已以 SPEC/TODO、現行 route/service/frontend 呼叫鏈、artifact jq receipt 及 SHA receipt 交叉核對；metadata consumer 聯集的結論限於已掃描的 `frontend/src`、`api`、`momentum/Analysis` 範圍，不能外推未掃描的外部 consumer。

STATUS: DONE
