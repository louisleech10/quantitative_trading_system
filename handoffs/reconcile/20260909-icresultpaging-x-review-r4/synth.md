# Reconcile — 20260909-icresultpaging-x-review-r4

**來源** 20260909-ICRESULTPAGING-X-REVIEW-R4-codex.md, 20260909-ICRESULTPAGING-X-REVIEW-R4-composer.md, 20260909-ICRESULTPAGING-X-REVIEW-R4-grok.md　|　**roster** codex,composer,grok


## 群集 / 處置

composer「可派工」（2 P2）；codex 5 P1＋1 P2；grok 1 P1＋1 P2。皆文件層，已修訂為 SPEC（R4 修訂）／TODO；R5 複驗。

### W1 — P1 light 每請求走全樹正規化＋守衛（實測 2586＋1461 ms）⇒ §C-9 不可達（`CODEX-R4-P1-01`）
**處置**：§C-7 增「寫入時一次正規化＋守衛」：`_set_result` 存 `result_normalized`，投影只讀之，守衛不省（raise ⇒ 不寫入）；預設 `/result` 不變；單元測試 spy 兩函式於投影請求呼叫 == 0；mutation P15。

### W2 — P1 `rolling_ic_series` 被 light 刪但 Phase 2 未接回 `RollingICChart`（`CODEX-R4-P1-02`）
**處置**：§C-6 (i) 明文六段全由 Task 1.2 供圖；Task 2.3 `sectionSplit`／`ICFeatureDetail` 明列 `rolling_ic_series`；page 案例⑤斷言 `RollingICChart` 收到序列。

### W3 — P1 `LATENCY_GATE` 無唯一文法／量測規則（`CODEX-R4-P1-03`）
**處置**：G-9 固定 warm-up 3＋20 次、p95＝nearest-rank 第 19 小、固定請求集（light、summary 五組、feature 兩組）、恰一行 `LATENCY_GATE=`＋逐項 p50／p95、rc 0／1／2；gate 解析與 `SIZE_GATE` 同規則。

### W4 — P1 快取只限每 task 8 組，無 process-wide 上限；`_tasks` 無界（`CODEX-R4-P1-04`）
**處置**：索引改 `numpy.int32`（157 KB／組）、process-wide 32 task LRU（≈40 MB 上限）、`cache_bytes()` 測試；`_tasks` 無界為既有 ⇒ `IP-RESID-5`（blocked-by 另票）；mutation P16。

### W5 — P1／P2 TODO `:143` 殘留 `order`；去抖 150 vs 300 ms（`CODEX-R4-P1-05`、`GROK-R4-P1-01`、`COMPOSER-R4-P2-01`、`CODEX-R4-P2-01`）
**處置**：統一 `sort_order`（typed `SummaryPageParams`）；去抖統一 300 ms。

### W6 — P2 UX「切換保留舊圖＋遮罩」「失敗重試」無 vitest（`GROK-R4-P2-01`、`COMPOSER-R4-P2-02`）
**處置**：page 案例④拆「初始 null」與「切換保留舊 detail＋overlay」，加⑧「mock reject ⇒ 重試按鈕」；§C-10 明文禁止切換時清空。

Verdict: 需修補後派工——W1–W6 已落文件；R5 三家複驗（寫入時正規化契約、rolling 接線、LATENCY 文法、快取容量、UX 測試）。

---
## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R4-P2-01

**斷言**: TODO Task 2.2 仍寫 `onParamsChange({sort_by, order, offset:0})`，與 §C 參數命名對齊 Feature Factory（`sort_order`）及同檔 `:144`／Task 2.3 `:160` 之 `{sort_by, sort_order, offset:0}` 矛盾，Agent 可能實作錯誤 query 鍵。

**碼證**: `docs/ICRESULT_PAGING_TODO.md:143` `SortButton ⇒ onParamsChange({sort_by, order, offset:0})`；同檔 `:144` URL query 用 `sort_order`；FF `api/routes/feature_factory.py:659-660` `sort_by`／`sort_order`；`grep -n 'sort_by, order' docs/ICRESULT_PAGING_TODO.md` → 1 命中；`grep -E '\?(q=|order=)' docs/ICRESULT_PAGING*.md` → 0。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#8e98dbd93418

[MINOR] 信心度=High。失敗：前端送 `order=desc` 而後端只收 `sort_order` ⇒ 排序無效或 400。修法：Task 2.2 `:143` 改 `sort_order`；加 vitest 斷言 callback 鍵名。

---

## COMPOSER-R4-P2-02

**斷言**: §C-10 要求「切換特徵保留舊圖＋loading 遮罩」「請求失敗可重試」「首屏 ≤3s 可互動」，但 Task 2.2／2.3 vitest 只覆 skeleton／URL／跨頁勾選，三項僅 Task 3.1 B34（`blocked-by:使用者`），回歸無機械 gate。

**碼證**: SPEC §C-10 `:42` 列七項 UX；Task 2.2 驗證 `:107`／TODO `:153` 含 skeleton／URL／勾選，**無**遮罩／重試／首屏；Task 3.1 `:121` 首屏＋遮罩靠使用者 UAT；page 六案例 `:114` 不含 chart 遮罩或 retry DOM。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241

[MINOR] 信心度=Medium。失敗：B2 gate 綠但切特徵閃白或失敗空白仍可能過 B3。修法：page 整合加 2 測（切 feature 舊圖仍在＋overlay；mock fetch fail⇒重試按鈕）；首屏 3s 保留 B34 即可。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha rc=0；39k paginate/light/feature 延遲探針；grep order/q；X1–X5 逐段對照 SPEC/TODO；FF browse 參數 `:653-663`
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq`；`shasum -a 256 -c handoffs/20260909-icresult-r4-baseline.sha` rc=0；`venv/bin/python /tmp/icresult_r4_perf_probe.py`；`venv/bin/python /tmp/icresult_r4_light_feature_probe.py`；`venv/bin/python handoffs/_light_size_probe.py`→28019；grep
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查；§C-9 門檻經探針支持可達）

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R4-composer.md`

STATUS: DONE
## GROK-R4-P1-01

**斷言**: TODO Task 2.2 檔案描述仍寫 `onParamsChange({sort_by, order, offset:0})`，與 SPEC／TODO 其餘處及 Task 2.3 驗證期望的 `sort_order`（FF `/browse` 對齊）互斥；agent 依字面實作會送錯鍵。

**碼證**: TODO `:143` 原文含 `{sort_by, order, offset:0}`；同檔 `:144`／`:160`／SPEC `:43`／`:72`／`:114` 皆為 `sort_order`；`grep -n order docs/ICRESULT_PAGING_TODO.md | grep -v sort_order` 僅命中 `:143`；無 `q` 殘留。FF 實碼：`frontend/src/hooks/useFeatureFactory.ts:280-281` 組 `sort_by`／`sort_order`。`RECHECK:` 同上 grep；修後該行不得再含獨立鍵名 `order`。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#8e98dbd93418

[MAJOR] 信心度=High。失敗：SortButton 回呼帶 `order` ⇒ API／store 忽略或 400；或 Task 2.3 vitest 期望 `sort_order` 紅。修法：`:143` 一字改 `sort_order`（與 `:160` 案例②一致）。

---

## GROK-R4-P2-01

**斷言**: SPEC §C-10／Task 3.1 要求「切特徵時保留舊圖＋loading 遮罩」與「請求失敗可重試」，但 Task 2.2／2.3 的 vitest 清單未鎖這兩項；page 案例④以 `featureDetail=null ⇒ 載入中` 反而鼓勵切換時清空，可能通過測試卻違反不閃白。

**碼證**: SPEC `:42`「切換期間保留舊圖並加 loading 遮罩」「請求失敗顯示可重試按鈕」；TODO `:144`⑦ 有重試實作要點，`:153`／`:160` 驗證列無「舊 detail 仍在 DOM」「重試按鈕」斷言；`:160`④＝`featureDetail=null`。`RECHECK:` 對照上述行；修法建議：案例改「切換中 `featureDetail` 仍為舊值且出現遮罩」；另加失敗→重試按鈕一案。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241

[MINOR] 信心度=Medium。失敗：agent 切特徵先 `setFeatureDetail(null)` 通過現有六案例，UAT 仍閃白。修法：補 vitest；案例④改為「初始 null」與「切換保留舊值」分開。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha 全 OK；X1–X5 文件閉合；39k 排序／light／feature 延遲實測；`order` 唯一殘留於 TODO:143；三 result 賦值點；selection_scope／export／FF sort_by|sort_order  
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq` 形狀；`shasum -a 256 -c handoffs/20260909-icresult-r4-baseline.sha` rc=0；venv 39k sort／light／feature 計時；`grep` order／q／AST／SIZE_GATE／NEW__／六案例（未跑 pytest governance／npm build，依 brief）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）  

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R4-grok.md`

STATUS: DONE
