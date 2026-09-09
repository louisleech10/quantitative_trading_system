# CODEX R3 review — ICRESULT_PAGING

## Verdict：需修補後派工（本輪無 P0；5 個 P1）
R3 對照：Y1 已閉合；Y2、Y3、Y4、Y5 各有下列新契約／驗收缺口；Y6 已閉合。

## CODEX-R3-P1-01
**斷言**: Task 1.0 的源碼守衛同時要求 `task_info["result"] = ` 出現 0 次，又要求 helper 內保留 1 次，正確實作無法通過。
**碼證**: SPEC `:60` 與 TODO `:49` 都寫 regex 計數 `== 0`，但同段明定 helper 內唯一賦值；現行碼三寫點為 `api/services/ic_analysis_service.py:1623,2339,2631`（`rg -n 'task_info\["result"\]' ...`）。
**來源摘要**: docs/ICRESULT_PAGING_TODO.md#054e03748587
修法：守衛應驗 helper 區段恰 1 次、helper 外 0 次，並以 AST／明確區段而非「註記排除」機檢。

## CODEX-R3-P1-02
**斷言**: G-5 三態的機檢 token 不唯一，`SIZE`、`SIZE_GATE`、`BLOCKED(artifact missing)` 與 rc=2 的混用可令 phase gate 誤判或繞過 B3。
**碼證**: SPEC `:50` 同時寫 `SIZE_GATE=...` 與 gate 輸出 `SIZE=BLOCKED`；TODO `:18` 寫 `SIZE=...`，`:111` 又要求 `SIZE_GATE=PASS`／artifact 缺席 rc=2；`scripts/icresult_paging_phase_gate.sh` 尚不存在（B0 才建立）。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#c4f915ce880b
修法：固定一個 stdout grammar（例如僅 `SIZE_GATE=PASS|FAIL|BLOCKED`），gate 嚴格解析；B1 對 BLOCKED 保持非紅但非 PASS，B3 明確只接受 PASS。

## CODEX-R3-P1-03
**斷言**: funnel adapter 對實機 `stage5_thresholds.output_features` 取 dict 長度會把 0 個輸出特徵報成 2 個。
**碼證**: 實跑 `jq -c '.filter_log.stage5_thresholds.output_features' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"count":0,"pass_class":"oos"}`；SPEC §C-6 `:36`／G-8 `:53` 卻規定 dict 一律 `len(dict)`，結果為 2，且 `FilterFunnelChart` 直接畫 `values.output`（`frontend/src/components/ic-analysis/FilterFunnelChart.tsx:18-23`）。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#c4f915ce880b
修法：contract 先定義 feature-count dict 的 `count` 欄語意（再對無 count 的集合明定 len），G-8 golden 應鎖定實值 0 與 P11 反例。

## CODEX-R3-P1-04
**斷言**: G-7b 只驗回應的 `result_revision`，不能證明投影資料仍來自 lock 內的舊 snapshot。
**碼證**: SPEC G-7b `:52`／TODO `:58` 只斷言 revision==舊值；若實作者回傳新 rows 但把舊 revision 貼上，該測試仍綠，違反 §C-7 `:37` 的「不混代」。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#c4f915ce880b
修法：old/new report 使用不同 sentinel 的 row／feature 值，G-7b 同時斷言 rows、total、result_revision 全部屬於舊世代；另測 feature projection。

## CODEX-R3-P1-05
**斷言**: B2 三案例沒有驗證 summary table 真的改吃 `summaryPage.rows`，因此可在 light 已開時表格仍讀被刪的 `report.summary_table` 而通過 page gate。
**碼證**: §C-6 `:36`／TODO `:99` 刪 `summary_table`；現行 page 仍在 `frontend/src/app/ic-analysis/page.tsx:140,689` 讀 `report.summary_table`。TODO Task 2.3 `:160`／`:169` 的三案例只驗六圖 loading/render 與 funnel null，沒有 `total=39346, rows=50`、51 個 `<tr>`、active row→detail 的 page assertion。
**來源摘要**: docs/ICRESULT_PAGING_TODO.md#054e03748587
修法：同批 page integration fixture 必須含不帶 `summary_table` 的 light、50-row summary page，並斷言 table DOM、排序／offset callback 與 detail request；否則 Y5 未閉合。

## 必答 1–7
1a. 預設 `/result` 仍可因 route 加 response model、欄位重建、或移動 `deny_factor_in_ok_oos`／序列化順序而變 raw bytes；1b. G-1 的 `response.content` raw SHA 可抓到，canonical SHA 只能輔助。
2a. 實查未找到前端仍讀而會被刪的鍵：`metadata.mode`、`n_timestamps`、`n_symbols`、事件／隔離／對齊鍵均列入顯式 keep union；2b. 現行 artifact 沒有另一個可證明超 2 MiB 且漏列的段，已知大段均由七段 drop 或兩條 count path 覆蓋，不能捏造 `deep_analysis_report`。
3a. 後端契約與舊前端不同：`[0.5,0.9,None]` asc 後端 `[A,B,C]`，舊 `-Infinity` comparator 會 `[C,A,B]`；3b. 缺值兩向沉底＋名稱次鍵是正確且已寫入新契約的語意。
4a. G-2/G-3 必須同一 revision；refilter 後舊 revision 409、無 revision 用新世代，投影使用 lock snapshot；4b. 無 revision 會把舊 total／offset 與新 detail 混成錯誤頁面。
5a. 既有 `/export/{task_id}/{format}` 是正確全量出口（route `:649-687`、service 支援 json/csv/markdown/hdf5），不應逐頁取代；5b. 39,346/500=79 次請求的 UI 時間未定量，不能宣稱可接受。
6. 沒有 ≥10× 過度工程新 finding；目前 SPEC 是 14-feature fixture 全量段 hash，contract JSON 是封閉 SoT，非 brief 所稱 200 抽樣。
7. 單批 cutover 對 light/drop 與圖表一致性較安全，但必補上 P1-05 的 table gate；IP-RESID-1/2 的 blocked-by 落檔邊界成立，IP-RESID-3 應 coexist＋四格 precedence matrix，不取代。

## §1 檢查摘要／§N
矛盾與不可測由 P1-01/02/04/05；quant、OOM、cache、輸出落檔未新增問題；各 Task 的永久存活聲稱無短命白工；§N 三值理由成立。未驗證假設：無新增（result 三寫點、metadata consumer、selection_scope scope_id、export route 均已查）。

ASSUMPTIONS_VERIFIED: `template_check.sh spec|todo` 各 rc=0；`jq -c '{st,meta_keys}'` → `{"st":39346,"meta_keys":39398}`；`shasum -a 256 -c handoffs/20260909-icresult-r3-baseline.sha` rc=0；實機 filter_log 六 stage、stage5 count dict、survivor scope_id 已實查。
TESTS_RUN: `venv/bin/python handoffs/_light_size_probe.py` rc=0 → `light_bytes 28019`；多個 `rg`／`nl`／`jq` receipt；未跑 `pytest tests/governance`、`npm run build`（brief 禁止）。
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查；未改碼／SPEC／TODO／根 HANDOFF.md）
NUMERIC_OR_SCHEMA_IMPACT: 未修改輸出；指出 proposed light funnel schema、revision gate、B2 acceptance 缺口。
HANDOFF_OUTPUT: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R3-codex.md`
STATUS: DONE
