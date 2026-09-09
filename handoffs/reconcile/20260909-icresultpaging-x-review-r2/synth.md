# Reconcile — 20260909-icresultpaging-x-review-r2

**來源** 20260909-ICRESULTPAGING-X-REVIEW-R2-codex.md, 20260909-ICRESULTPAGING-X-REVIEW-R2-composer.md, 20260909-ICRESULTPAGING-X-REVIEW-R2-grok.md　|　**roster** codex,composer,grok


## 群集 / 處置

composer「可派工（附 1 P1 一句修）」；codex／grok「需修補後派工」。全部文件層，無 P0。主委已依下列群集修訂為 SPEC（R2 修訂）／TODO，R3 複驗；分歧處採較嚴版。

### Y1 — P1 G-6 四列 asc 期望 SPEC `[A,B,C,D]` vs TODO `[B,A,C,D]` 矛盾（`CODEX-R2-P1-01`、`COMPOSER-R2-P1-01`、`GROK-R2-P1-01`）
**處置**：TODO Task 1.1 改 `asc == [A,B,C,D]`（與 §C-8 偽碼一致；三家手算相同）；3 列 fixture `[B,A,C]`／`[A,B,C]` 兩檔一致。

### Y2 — P1 refilter 回應無 revision handshake；lock 外投影 TOCTOU（`CODEX-R2-P1-02`）
**處置**：§C-7 增「投影對 lock 內 snapshot `(report, revision)`」＋「`POST /refilter?view=light` 回 light（含新 revision），無 `view` 不變」＋前端丟棄 `revision != store` 之回應；Task 1.0 加 `_snapshot_result`；G-7 拆 a／b（投影中途 refilter 不混代）／c；mutation P10。

### Y3 — P1 G-5 `pytest.fail` 與 B1 gate rc=0 不可同時成立（`CODEX-R2-P1-03`）
**處置**：G-5 移出 pytest，改獨立探針三態 `SIZE_GATE=PASS|FAIL|BLOCKED`；phase gate 只轉印三態、BLOCKED 不假綠不紅；B3 收案要求 PASS；pytest 內以 repo 結構 fixture `shape_fixture.json` 驗形狀。

### Y4 — P1 漏斗鍵名錯配是可重現契約缺陷，非 needs-research（`CODEX-R2-P1-04`、`GROK-R2-P2-01`、`COMPOSER-R2-P2-02`）
**處置**：採較嚴版（codex）收回為 Task：contract `funnel_stage_adapter`（input／output 候選鍵序，取第一存在者，list／dict 取 len，皆缺 ⇒ null）；light 加 `filter_log_funnel`；Task 2.3 改 `FilterFunnelChart` 讀之（null ⇒ 不適用）；G-8 golden；mutation P11；§N 原 IP-RESID-4 撤銷。

### Y5 — P1 B2a／B2b 拆批留下「light 已開、圖表讀已刪段」退化中間態（`CODEX-R2-P1-05`）
**處置**：B2 併回單批 cutover（2.1＋2.2＋2.3），page 整合測試（載入中／六圖渲染／漏斗不適用）為 gate；R1 `COMPOSER-R1-P2-01` 之拆分被本輪更嚴證據覆蓋。

### Y6 — P2 `filter_log.*` wildcard 語意未定（`CODEX-R2-P2-06`）；keep_keys 三份清單不一致（`COMPOSER-R2-P2-01`）
**處置**：§C-6 (iii) 改顯式路徑規格：`*` 只匹配該層直接子鍵、一層不遞迴、目標須 dict、缺席／非 dict no-op、深層不動；contract 為 `metadata_keep_keys` 唯一來源，探針改讀 contract（新 `IP-RESID-4`，blocked-by Task 0.1，完成即收）。

Verdict: 需修補後派工——Y1–Y6 已落文件；R3 由三家複驗（G-6 一致、G-7a–c、三態 gate、funnel adapter 與 G-8、B2 單批 page 測試、wildcard 規格）。

---
## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R2-P1-01

**斷言**: SPEC §G G-6 四列並列 fixture 之 `asc` 期望序為 `[A,B,C,D]`，但 TODO Task 1.1 驗證寫 `asc == [B,A,C,D]`，與 contract `sort_policy`（並列次鍵 `feature_name` 升冪）矛盾，實作者必有一邊假綠。

**碼證**: SPEC `docs/ICRESULT_PAGING_SPEC.md` §G G-6「desc 序 == `[A,B,C,D]`、asc 序 == `[A,B,C,D]`」；TODO `docs/ICRESULT_PAGING_TODO.md` Task 1.1 驗證「4 列並列 fixture desc == `[A,B,C,D]`、asc == `[B,A,C,D]`」。手算：A/B 同有限值且 A<B 名序，C/D 為 None、兩向沉底 ⇒ asc 亦為 `[A,B,C,D]`。RECHECK: 對照兩檔 G-6 段＋`sort_policy` 次鍵規則。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#376e43979064

[MAJOR] 信心度=High。B1 gate 會因 SPEC/TODO 各寫各的而 rc=1 或 agent 猜錯。修法：TODO Task 1.1 驗證改 `asc == [A,B,C,D]` 與 SPEC 對齊（3 列 fixture `[A,B,C]` 已一致）。

---

## COMPOSER-R2-P2-01

**斷言**: `metadata_keep_keys` 三份來源清單不一致——§A receipt、TODO 0.1 檔案欄、`_light_size_probe.py` KEEP_META 互為超集／子集，G-5 receipt（28019 bytes）依最寬 probe 清單，contract 若只實作 TODO 驗證子集則 bytes 更小但與 receipt 不可對證。

**碼證**: probe `handoffs/_light_size_probe.py:5` 含 `quality,density_metrics,label_kind,horizon,...`；TODO 0.1 驗證子集僅列 14 鍵＋`fit_mode` 等；39k 報告頂層結構鍵 `jq` → 7 鍵（無 `label_kind`）。RECHECK: diff 三份清單。

**來源摘要**: handoffs/_light_size_probe.py#（probe 腳本）

[MINOR] 信心度=Medium。當下 39k 不爆，但 B0 寫 contract 時應以**單一**顯式清單為準並讓 probe 讀 contract，避免 receipt 漂移。

---

## COMPOSER-R2-P2-02

**斷言**: `IP-RESID-4` 之 `needs-research` 理由成立，但 B34 UAT 若含漏斗互動，在 light `filter_log` 集合→`_count` 後 `FilterFunnelChart`（讀 `values.input`/`values.output`）仍全 undefined——改前即錯、改後不會自動好。

**碼證**: `FilterFunnelChart.tsx:20-21` 讀 `input`/`output`；實機 `jq` 各 stage 鍵集合無 `input`/`output`，有 `input_features`/`output_features`；§N IP-RESID-4 觸發「B34 漏斗空白」。RECHECK: `jq -r '.filter_log|to_entries[].value|keys[]' … | sort -u`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#17e213a6d472

[MINOR] 信心度=High。不阻派工；建議 B34 清單註明漏斗為既有缺陷或 Task 2.3 改讀 `*_count`／`input_features_count`。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；三 result 寫點 grep；filter_log 鍵集合；survivor scope_id；_light_size_probe 28019；ExportButtons export 路徑；G-6 手算四列序
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq -c '{st,meta_keys}'`；`jq` filter_log keys；`grep task_info["result"]`；`venv/bin/python handoffs/_light_size_probe.py`；讀碼 FilterFunnelChart/ExportButtons/route
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R2-composer.md`

STATUS: DONE
## GROK-R2-P1-01

**斷言**: SPEC §G-6 與 TODO Task 1.1 對「四列並列 fixture」的 asc 期望序互相矛盾（SPEC=`[A,B,C,D]`，TODO=`[B,A,C,D]`），且與 §C-8／TODO comparator 偽碼（次鍵 `feature_name` 升冪、缺值兩向沉底）只有 SPEC 一側自洽。

**碼證**: SPEC `:51`「desc 序 == `[A,B,C,D]`、asc 序 == `[A,B,C,D]`」；TODO Task 1.1 驗證 `:75`「desc == `[A,B,C,D]`、asc == `[B,A,C,D]`」。venv 依 TODO 偽碼 `(1,0,name)`／`(0,±value,name)` 重算四列 → desc/asc 皆 `[A,B,C,D]`。`RECHECK:` `grep -n '\[A,B,C,D\]\|\[B,A,C,D\]' docs/ICRESULT_PAGING_SPEC.md docs/ICRESULT_PAGING_TODO.md`＋重跑 comparator。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#376e43979064

[MAJOR] 信心度=High。失敗：agent 依 TODO 寫 `sort_golden`／測断言會與 SPEC G-6 永久對打，或私下改 comparator 讓次鍵在 asc 反序（破壞 §C-8）。修法：把 TODO `:75` 的 asc 改為 `[A,B,C,D]`（與 SPEC／偽碼一致）；勿改 SPEC 去就錯誤的 `[B,A,C,D]`。

---

## GROK-R2-P2-01

**斷言**: §N `IP-RESID-4` 以 `needs-research` 為「為何現在不做」已不成立——FilterFunnelChart／型別期望的 `input`／`output` 與實機 `filter_log` 鍵名錯配可在本輪碼證，無需再研究。

**碼證**: `frontend/src/lib/types.ts:2155-2158` `FilterLogStage{input,output}`；`FilterFunnelChart.tsx:19-22` 讀 `values.input`／`values.output`；實機六 stage **皆無** `input`／`output` 鍵，僅部分有 `input_features`／`output_features`（且常為 int／dict，非圖表假設的成對計數名）。`RECHECK:` 本檔「IP-RESID-4」表＋`jq '.filter_log|to_entries[]|{stage:.key,keys:(.value|keys)}'`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#17e213a6d472

[MINOR] 信心度=High。失敗：殘留登記誤導下一輪以為「還不知道鍵名」；不阻擋本票派工（Task 2.3 已明示不修漏斗鍵名）。修法：將 `為何現在不做` 改為 `blocked-by:out-of-scope`（或 `user-ruling:本票不修改前漏斗；觸發仍為 B34 漏斗空白`），保留殘留、**不**收回為 Task。

---

ASSUMPTIONS_VERIFIED: template_check 兩份 PASS；jq 39346/39398；baseline sha 全 OK；light probe 28019；result 三賦值點；selection_scope／export／module_statuses 消費者；sort_policy 四列／三列重算；filter_log 鍵名 vs FilterFunnelChart；R1 六條閉合對照  
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq` 形狀；`shasum -a 256 -c handoffs/20260909-icresult-r2-baseline.sha` rc=0；`venv/bin/python handoffs/_light_size_probe.py` → 28019；grep／讀碼／venv comparator（未跑 pytest governance／npm build，依 brief）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查，未改碼）  

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R2-grok.md`

STATUS: DONE
