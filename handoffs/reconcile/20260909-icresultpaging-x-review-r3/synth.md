# Reconcile — 20260909-icresultpaging-x-review-r3

**來源** 20260909-ICRESULTPAGING-X-REVIEW-R3-codex.md, 20260909-ICRESULTPAGING-X-REVIEW-R3-composer.md, 20260909-ICRESULTPAGING-X-REVIEW-R3-grok.md　|　**roster** codex,composer,grok


## 群集 / 處置

composer「可派工，無新 P0／P1，進 B0 前最後一件必做＝無」；codex 5 P1；grok 1 P1＋2 P2。皆文件層，主委已修訂為 SPEC（R3 修訂）／TODO；另依使用者 2026-09-09 指示加入效能／體驗預算（§C-9／10、G-9）與參數名對齊 Feature Factory。R4 複驗。

### X1 — P1 Task 1.0 源碼守衛「== 0」與「helper 內 1 處」矛盾（`CODEX-R3-P1-01`）
**處置**：改 AST 守衛：`_set_result` 函式體內恰 1、體外 0；不用註記排除。

### X2 — P1 G-5 三態 token 不唯一（`SIZE`／`SIZE_GATE`／rc 混用）；gate 對 FAIL 未寫死 rc（`CODEX-R3-P1-02`、`GROK-R3-P2-02`）
**處置**：唯一文法：恰一行 `SIZE_GATE=PASS|FAIL|BLOCKED`＋`SIZE_REASON=`；gate 偽碼：計數 ≠1 ⇒ rc=1；FAIL ⇒ rc=1；BLOCKED ⇒ 轉印不改 rc；PASS ⇒ 繼續；B3 要 PASS。

### X3 — P1 funnel 對 `output_features={"count":0,...}` 取 len 得 2；funnel 若在計數後算則 stage5 變 null；G-8 漏 `stage3_event_filter`（`CODEX-R3-P1-03`、`GROK-R3-P1-01`、`GROK-R3-P2-01`）
**處置**：adapter 增 `dict_count_key="count"`（dict 含 count 取之；其他 dict／list 取 len）；明文「funnel 對原始 filter_log 先算、再對 light 計數」；G-8 六 stage 全鎖（stage3 `{null,null}`、stage5 `output=0`）；mutation P12／P13。

### X4 — P1 G-7b 只驗 revision，不證資料來自舊 snapshot（`CODEX-R3-P1-04`）
**處置**：sentinel 新報告（`NEW__` 前綴、不同 total）；斷言 revision／total／全部列名皆舊世代；feature 端點同法。

### X5 — P1 B2 page 測試未驗表格真改吃 `summaryPage.rows`（`CODEX-R3-P1-05`）
**處置**：page fixture 不含 `summary_table`；六案例：`<tr>`==51、排序 callback、點列 ⇒ detail、載入中、六圖渲染、漏斗不適用。

### X6 — 使用者指示（非委員 finding）：效率與體驗預算；參數名對齊 FF
**處置**：§C-9 後端延遲預算（light 150／300、summary 100／200、feature 50／100 ms p50／p95；排序索引 LRU 快取 key 含 revision）；§C-10 前端體驗（skeleton 不閃白、跨頁勾選、URL query 狀態、重試）；G-9 延遲 receipt 三態；`sort_order`／`search` 命名對齊 `/browse/{task}/features`；mutation P14。

Verdict: 需修補後派工——X1–X6 已落文件；R4 三家複驗（守衛 AST、SIZE_GATE 文法、funnel count 語意與順序、G-7b sentinel、page 六案例、§C-9／10 預算可測性）。

---
## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對 Y1–Y6 與必答 1–7 後無新 P0／P1 finding；R2 修訂已閉合，可派工 B0。

**碼證**: `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md`／`todo docs/ICRESULT_PAGING_TODO.md` → TEMPLATE PASS rc=0；`jq -c '{st:(.summary_table|length), meta_keys:(.metadata|keys|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"st":39346,"meta_keys":39398}`；`shasum -a 256 -c handoffs/20260909-icresult-r3-baseline.sha` → 全 OK；G-6 手算四列／三列與 SPEC/TODO 一致；`venv/bin/python handoffs/_light_size_probe.py` → `light_bytes 28019`；漏斗六 stage 手算與 G-8 敘述一致（含 `stage3_event_filter {null,null}`）；`grep task_info\["result"\]` 三寫點 `:1623/:2339/:2631`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#c4f915ce880b

[NONE] 信心度=High；Y1 G-6 SPEC/TODO 已同 `[A,B,C,D]`；Y2 §C-7 handshake＋三寫點含 full-analysis；Y3 G-5 三態與 B1/B3 分工清楚；Y4 funnel 候選鍵序對實機六 stage 可重現、stage1 維持 null；Y5 B2 單批＋page 三案例足擋退化中間態；Y6 wildcard 一層規格對六 stage 唯一、`scope_id` 投影後仍 scalar。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha 全 OK；light probe 28019；三 result 寫點；filter_log 六 stage 鍵＋funnel 手算；selection_scope.scope_id scalar；grep 前端無 IC 全段 map；export 路徑 1889+
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq` 形狀；`shasum -a 256 -c handoffs/20260909-icresult-r3-baseline.sha` rc=0；`venv/bin/python handoffs/_light_size_probe.py`；`jq` filter_log types；grep／讀碼
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R3-composer.md`

STATUS: DONE
## GROK-R3-P1-01

**斷言**: TODO Task 1.3 將 `_collections_to_counts` 列於 `funnel_from_filter_log(report["filter_log"])` 之前，且 §C-6 (iii) 把 list／dict **改為** `<key>_count`；若實作依此序對同一 `filter_log` 先計數再跑 adapter，實機 `stage5_thresholds.output_features`（dict）消失，G-8 期望的 `output=int(len(dict))` 變成 `null`。

**碼證**: TODO `:100` 元件列序＝counts → summary_page → `funnel_from_filter_log(report["filter_log"])`；SPEC §C-6 (iii)「改為 `<key>_count`」＋(iv) 候選鍵只有 `output_features`／`feature_count_filtered`（無 `output_features_count`）；G-8（SPEC `:53`）`stage5_thresholds {input:int, output:int(len(dict))}`。venv 對實機報告：counts 前 stage5 output=2，counts 後 output=None（鍵變 `output_features_count`）。`RECHECK:` 同上模擬；或實作後跑 G-8。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#054e03748587

[MAJOR] 信心度=High。失敗：agent 依字面順序實作 ⇒ G-8 紅，或私下把 `*_count` 塞進候選鍵／改 G-8 期望造成假綠。修法：§C-6／Task 1.3 明文「funnel 必須吃計數前的 filter_log（建議：先自原 stage 算 `filter_log_funnel`，再對 light 的 filter_log 做 counts）」；G-8／shape fixture 鎖定 stage5 output≠null；mutation 加「顛倒順序 ⇒ G-8 紅」。

---

## GROK-R3-P2-01

**斷言**: G-8 宣稱「六 stage」經 adapter 的 golden，但括號列舉只含五個 stage、漏掉實機存在的 `stage3_event_filter`（候選鍵皆缺 ⇒ `{null,null}`），golden 不完整會讓測試只鎖五段。

**碼證**: SPEC `:53`／TODO `:111` G-8 列 `stage0`／`feature_filter`／`stage1`／`stage5`／`stage6`；實機 `jq` 六 stage 含 `stage3_event_filter`（鍵無 input_features／output_features／feature_count_*）。手算 stage3=`{null,null}`。`RECHECK:` `jq -r '.filter_log|keys[]' data_cache/reports/ic_report_ic_gatekeeper.json`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#c4f915ce880b

[MINOR] 信心度=High。失敗：shape／G-8 漏 stage3 ⇒ 該 stage 投影漂移不被抓。修法：G-8 golden 顯式加 `stage3_event_filter {null,null}`（維持 null、不推導）。

---

## GROK-R3-P2-02

**斷言**: G-5 三態設計對 `BLOCKED` 有明確「不假綠不紅」規則，但 `scripts/icresult_paging_phase_gate.sh`（尚未存在）對 `SIZE_GATE=FAIL` 是否使 B1 gate `rc≠0` 沒有可機檢偽碼；「只轉印三態」可被實作成 FAIL 亦不紅，尺寸回歸拖到 B3 才爆。

**碼證**: SPEC `:50`「對 G-5 **只轉印三態**：`BLOCKED` 不使 B1 gate 假綠亦不使之紅」；TODO §B `:18`／Phase1 Gate `:119` 同只點名 BLOCKED 例外，未寫 `FAIL ⇒ gate rc=1`。腳本 `test -e scripts/icresult_paging_phase_gate.sh` ⇒ 不存在（Task 0.1 建）。`RECHECK:` 對照上述行；B0 實作 gate 時注入 `SIZE_GATE=FAIL` 應使 phase 1 rc≠0。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#c4f915ce880b

[MINOR] 信心度=Medium。失敗：gate 只 `cat` receipt ⇒ FAIL 假綠至 B3。修法：Task 0.1／gate 偽碼寫死「解析一行 `SIZE_GATE=`；`FAIL`⇒rc=1；`BLOCKED`⇒印 `SIZE=BLOCKED` 且不改 rc；`PASS`⇒印並繼續；缺行／未知⇒rc=1」。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha 全 OK；light probe 28019；result 三賦值點（含 :2339=_run_full_analysis）；selection_scope／export／page sectionSplit；G-6 四列／三列重算；funnel adapter before/after counts（stage5 2→None）；wildcard／scope_id；Y1–Y6 對照  
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq` 形狀＋filter_log keys；`shasum -a 256 -c handoffs/20260909-icresult-r3-baseline.sha` rc=0；`venv/bin/python handoffs/_light_size_probe.py` → 28019；venv comparator＋funnel/count 順序模擬（未跑 pytest governance／npm build，依 brief）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）  

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R3-grok.md`

STATUS: DONE
