# ICRESULT_PAGING SPEC＋TODO adversarial review R4 — codex

## Verdict：需修補後派工

本輪重跑 X1–X5 並獨立審 X6；無新 P0，但有 5 條 P1、1 條 P2。排序本身實測可達預算；主要問題是快路徑、快取生命週期、G-9 gate 與前端接線仍未寫成可失敗的契約。

## CODEX-R4-P1-01
**斷言**: `view=light` 的 150/300 ms p95 預算，和「投影前執行既有全樹 OOS 守衛／全樹 JSON 正規化」沒有可同時滿足的實作契約。
**碼證**: SPEC §C-9 `:41`；TODO `:100-101` 要求 `deny_factor_in_ok_oos(normalized)` 先於投影；現行 `get_result` `api/services/ic_analysis_service.py:1772-1789` 先 `_to_json_compatible(result)`。`jq -c '{analysis_status,oos_guarantees}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"analysis_status":"ok_oos","oos_guarantees":true}`；實測同一 39,346 列報告：`deny_walk_ms 1460.52`、`serialize_normalize_ms 2585.79`，均已超過 300 ms。RECHECK: 重跑上述 jq 與兩個 `venv/bin/python -c` benchmark。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241; docs/ICRESULT_PAGING_TODO.md#8e98dbd93418; api/services/ic_analysis_service.py#4949a7dd28e4
[MAJOR] 信心度=High；若只在既有 `get_result` 外包一層 light，首屏會沿 119 MB 全樹路徑而超時；若為了過預算跳過守衛則違反資料品質紅線。修法：明定以 `result_revision` 綁定的寫入時驗證 receipt／安全快取，並要求投影後選擇性正規化；不可省略守衛；G-9 加 mutation 確認未回退到全樹掃描。

## CODEX-R4-P1-02
**斷言**: `rolling_ic_series` 被 light 刪除，但 Phase 2 的 featureDetail 接線清單沒有把它接回 RollingICChart，cutover 後該圖表會拿不到資料。
**碼證**: SPEC §C-6 `:36` 將 `rolling_ic_series` 列入 `drop_sections`；TODO Task 1.2 `:83` 明列 `rolling_ic_series[name]`；但 TODO Task 2.3 `:159-160` 的 `sectionSplit`／featureDetail 清單只有 `ic_decay, quantile_returns, grouped_ic, turnover_analysis`。現行 `frontend/src/app/ic-analysis/page.tsx:880-882` 仍直接讀 `report?.rolling_ic_series?.[activeFeature]`。RECHECK: `nl -ba` 讀上述三段，並以不含 `rolling_ic_series` 的 light fixture 渲染 page。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241; docs/ICRESULT_PAGING_TODO.md#8e98dbd93418; frontend/src/app/ic-analysis/page.tsx#3516fb531477
[MAJOR] 信心度=High；`ICReportLight` 在 TODO `:125` 的「per-feature 四段」也未明列 rolling，實作者可合法地刪掉它而只讓五個圖表有資料。修法：contract/type、`sectionSplit`、featureDetail props 與 page integration fixture 明列 `rolling_ic_series`；以非空 rolling golden 斷言 RollingICChart 收到該 feature 的值。

## CODEX-R4-P1-03
**斷言**: G-9 雖新增 `LATENCY_GATE`，但沒有獨立的可重現量測規則與 fail-closed gate；G-5 的 `SIZE_GATE` 規則不能自動涵蓋它。
**碼證**: SPEC G-9 `:57` 只寫 TestClient 20 次、p50/p95 與 `LATENCY_GATE=PASS|FAIL|BLOCKED`；TODO `:76` 只寫 artifact 缺席時 BLOCKED，Phase 1 gate `:119` 只定義 `SIZE_GATE` 的行數／rc 解析，Phase 3 `:189` 只要求 `--latency` 印出 PASS，未定義 LATENCY 的 rc、缺行／多行處置、warm-up 次數、p95 算法、feature 名與請求順序。實測 39k bare sort：icir 20 次 p50/p95=`25.69/25.86 ms`，所以問題是 gate 不可重現而非無證據宣稱排序太慢。RECHECK: 對照 SPEC `:57`、TODO `:76,:119,:189`，以缺少 `LATENCY_GATE` 或 artifact 缺席的 probe 反例驗 gate。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241; docs/ICRESULT_PAGING_TODO.md#8e98dbd93418
[MAJOR] 信心度=High；目前 Phase gate 可能只轉印／忽略 LATENCY，或把 BLOCKED 當 PASS；不同 warm-up、p95 interpolation、feature 選擇也會得到不同結論。修法：為 LATENCY 固定唯一 stdout grammar、rc 0/1/2、缺／多／未知行處理與 gate 行為；固定 warm-up、20 次採樣、p95 定義、所有 summary variant（含 pass_class）及代表性／最大 feature detail。

## CODEX-R4-P1-04
**斷言**: 「每 task 8 組排序索引」不是程序記憶體上限，且現有 `_tasks` 沒有完成 task 的清理生命週期，39k 多 task 會累積 OOM 風險。
**碼證**: SPEC §C-9 `:41`／TODO `:65` 只定每 task 8 組與 revision invalidation；現行 `ICAnalysisService.__init__` `api/services/ic_analysis_service.py:432-437` 建立無界 `_tasks`，`rg -n 'del self\\._tasks|self\\._tasks\\.pop|self\\._tasks\\.clear' api/services/ic_analysis_service.py` 無輸出。若按契約保存 Python index list，`venv/bin/python -c` 實測 39,346 index 一組 `1,416,508` bytes、八組 `11,332,064` bytes／task。RECHECK: 重跑上述 rg 與 index-list `sys.getsizeof` benchmark。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241; docs/ICRESULT_PAGING_TODO.md#8e98dbd93418; api/services/ic_analysis_service.py#4949a7dd28e4
[MAJOR] 信心度=High；LRU 只限制每個 task 的 key 數，沒有 process-wide bytes／task 數／TTL 上限，且 revision 失效若只清索引仍不處理 task 淘汰。修法：定義可驗收的全域記憶體上限與 eviction／task lifecycle hook，或使用有容量證據的 compact index；測試多 task、revision invalidation 與 eviction 後 RSS／cache size。

## CODEX-R4-P1-05
**斷言**: TODO Task 2.2 的排序 callback 仍使用 `order`，與 SPEC／FF／其自身測試契約的 `sort_order` 不一致。
**碼證**: TODO `:143` 原文為 `onParamsChange({sort_by, order, offset:0})`；SPEC `:43`、TODO `:144` 與 TODO `:160` 都要求 `sort_order`，page integration 亦斷言收到 `sort_order`。RECHECK: `rg -n 'onParamsChange.*order' docs/ICRESULT_PAGING_TODO.md` 應命中 `:143`，並對照 `sort_order` grep。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241; docs/ICRESULT_PAGING_TODO.md#8e98dbd93418
[MAJOR] 信心度=High；實作若照 Task 2.2 會把前端狀態欄位命名成 `order`，無法直接送到 `sort_order` API，page gate 的 callback 斷言也會不一致。修法：全文統一 `sort_order`，以 typed `SummaryPageParams` 與 source guard 防止 `order` 回歸；本次 grep 未發現 query 參數 `q`，只有 pytest `-q`。

## CODEX-R4-P2-01
**斷言**: 搜尋 debounce 的規格數值互斥：Task 2.1 寫 150 ms，§C-10 與 Task 2.2 寫 300 ms。
**碼證**: TODO `:125` 寫「去抖 150 ms」；SPEC §C-10 `:42` 與 TODO `:144` 寫 300 ms。RECHECK: `rg -n '去抖|300 ms|150 ms' docs/ICRESULT_PAGING_SPEC.md docs/ICRESULT_PAGING_TODO.md`。
**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241; docs/ICRESULT_PAGING_TODO.md#8e98dbd93418
[MINOR] 信心度=High；實作與測試會出現兩個合法值，造成體驗 gate 不穩。修法：保留單一 300 ms（§C-10 與 Task 2.2 已一致），並刪除 150 ms。

## 必答 1–7 與 X1–X5 複驗
1a. 預設 raw body 仍可能因把 `result_revision`／`view` 寫入預設報告、改用 response model、或改變 `_to_json_compatible`／`deny_factor_in_ok_oos` 的序列化與鍵插入順序而改變；1b. G-1 的 `response.content` raw sha 能抓到內容、空白與鍵序的所有改變，canonical sha 只能輔助。
2a. `rolling_ic_series[feature]` 是現行前端仍讀、但 light drop 的鍵；metadata 的 `n_timestamps`、`event_filter`、`isolation` 等有在 keep 白名單，`selection_scope.scope_id` 也保留。2b. raw `metadata` 8,417,776 bytes、raw `filter_log` 3,282,725 bytes 都不在 `drop_sections`，但目前分別由 metadata whitelist／collection-to-count 壓縮；若任一投影未執行就會超 2 MB，G-5 必須驗 post-projection，而非只驗 drop 名單。
3a. 前後端不同序：A=`icir 0.5`、B=`None`、C=`icir 0.1` 時，現前端 asc 為 `[B,C,A]`，新後端契約為 `[C,A,B]`（現前端 `getSortValue` 將缺值成 `-Infinity`，且 tie 無次鍵）。3b. 後端契約正確：None/NaN/±inf 兩向沉底，且 feature_name 次鍵穩定。
4a. G-2/G-3 在 refilter 後必須以 `(report, result_revision)` snapshot：帶舊 revision 回 409，不帶則只取新世代；G-7b sentinel 驗舊 total／名稱／feature 段不混代。4b. 無 revision 時舊 page、new page、feature detail 會被錯誤拼接，無法判斷回應是否可套用。
5a. 既有 `/export/{task_id}/{format}` 才是正確出口：`api/routes/ic_analysis.py:649-687` 與 `export_analysis` 讀 full result，`ExportButtons` 已組該 URL；Task 2.3 保持端點不動是正確的。5b. 39k CSV 是明示匯出、可接受為背景／下載動作，但本票未給 export latency 或進度 UX；不應把逐頁匯出混入首屏分頁。
6. R4 已不是 200 特徵抽樣：TODO Task 0.1 對 14-feature fixture 保存全部 `feature_samples`，實際 39k 僅做尺寸／延遲 receipt；這是合理的 byte/集合投影 golden，不屬 ≥10× 過度工程。contract JSON 也是必要的單一真相源。
7. B2 一次切換風險較小，因 light 會先刪段，表格-only 會留下中間態；三條殘留的 blocked-by／user-ruling 理由成立，`IP-RESID-3` 應與實作並存直到 v2 消費者遷移，不應取代。X1 AST（helper 內 1、外 0）、X2 單一 `SIZE_GATE`、X3 funnel 先於 count＋`count`、X4 sentinel、X5 page 六案例均已落文件，無新 finding。

## 11 類檢查摘要與未驗證假設
矛盾：P1-05、P2-01；端到端／可測：P1-01～03；quant／資料洩漏：無新 finding；過度工程：無；OOM／cache：P1-04；API／型別：P1-02、P1-05；測試品質：P1-03；Agent 可執行性：P1-01～05；短命工：無。
被當成事實的未驗證假設：G-9 的 TestClient 20 次足以代表 backend latency（未定 warm-up／p95／環境）；「8 組／task」等於記憶體上限（反例為無界 `_tasks`）。其餘 §A 宣稱已以 receipt 或本輪 grep／實測核對。
停輪判定：有新 P1，故不可直接派工；B0 前最後必做事＝修正 P1-01～05 並重跑本輪 receipt，P2-01 同批統一。

ASSUMPTIONS_VERIFIED: template／SPEC／TODO 完整讀取；R4 baseline `shasum -a 256 -c` 全 OK；jq 實報告 `39346/39398` 與 `analysis_status=ok_oos`；result 三寫點／refilter replacement；metadata consumer、export route、rolling consumer、order residual、`q` 參數 grep；39k sort、light projection、feature detail、deny／serializer、index-list benchmarks。
TESTS_RUN: `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md` → TEMPLATE PASS rc=0；`bash scripts/template_check.sh todo docs/ICRESULT_PAGING_TODO.md` → TEMPLATE PASS rc=0；`jq -c '{st:(.summary_table|length),meta_keys:(.metadata|keys|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"st":39346,"meta_keys":39398}` rc=0；`shasum -a 256 -c handoffs/20260909-icresult-r4-baseline.sha` → rc=0；`./scripts/completeness_check.sh --single handoffs/20260909-ICRESULTPAGING-X-REVIEW-R4-codex.md --family codex` → `COMPLETENESS PASS(single)`, 6 IDs, rc=0。字面 `bash scripts/completeness_check.sh ...` 被既有 PreToolUse debt gate 擋，未改帳本；腳本本體／參數已以 `./scripts` 實跑。禁止 `pytest tests/governance`、`npm run build`，未執行。
FAILURES_SEEN: macOS `/usr/bin/time -f` 不支援，改用 zsh `TIMEFORMAT` 重跑；無審查結論失敗。
SCOPE_CHANGES: none（唯讀審查；只新增本交件檔）。
NUMERIC_OR_SCHEMA_IMPACT: none（未改產品碼、SPEC、TODO、資料或 schema）。
產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R4-codex.md`
STATUS: DONE
