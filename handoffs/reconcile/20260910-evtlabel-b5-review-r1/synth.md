# Reconcile — 20260910-evtlabel-b5-review-r1

**來源** 20260910-evtlabel-b5-review-r1-codex.md, 20260910-evtlabel-b5-review-r1-composer.md, 20260910-evtlabel-b5-review-r1-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

10 條 findings 群集為六個修訂項，**全數採納並已修補**。
三家皆判無 ≥10× 不必要複雜；修補後可收 Phase 3。

我在 brief 自列為可疑的三點（必答 1／2／3）**全部被證實成立**；
另有兩點是我沒想到的（light 視圖吃掉揭露、掃描立方體殘留）。

### C1 — `label_origin_values` 憑空編造來源
- findings：`COMPOSER-R1-P1-01`、`GROK-R1-P1-01`、`CODEX-R1-P1-01`（三家全員，信心 10/10）
- `label_origin` 在匯入契約是**選填**，我在缺席時回退成 `label` 本身
  ⇒ 寫出 `["0","1"]`：一份假裝是來源揭露、實際只是把答案抄一遍的資料。
- 處置：**採納並修補**（`0e54cce1`，派審後我自行查契約時已發現並修）。
  缺席 ⇒ 空 list。測試以碼證釘住不得再回退，另一條釘住「契約確實列為選填」。

### C2 — 空字串 `import_id` 讓明示模式靜默降級
- findings：`GROK-R1-P1-02`、`CODEX-R1-P1-02`（兩家）
- 不變式只擋 `is None`，但 `""` 是 falsy ⇒ model 放行、下游 truthy guard 跳過五階段
  ⇒ 使用者選了「只用匯入的 0/1」，拿到的卻是一般全域分析，報告上看不出來。
- 處置：**採納並修補**。三條不變式一律改判 falsy。測試 +2。

### C3 — 🔴 light 視圖吃掉整個揭露（我沒想到）
- findings：`CODEX-R1-P1-04`（信心 10/10）
- 前端固定請求 `view=light`，而 `metadata_keep_keys` 漏了 `label_mode` 與 `event_label_rule`
  ⇒ 模式 banner 與規則揭露的資料來源被投影掉。**Task 3.9 整段在正常回應中不可見。**
- 處置：**採納並修補**。兩鍵補進白名單；測試同時釘住既有鍵不得被擠掉。

### C4 — 結構性失敗被統計性失敗蓋掉（我 brief 必答 3 之疑點）
- findings：`CODEX-R1-P1-03`（信心 9/10）
- suppressed 早退放在 symbol／timeframe 檢查之前 ⇒ 兩者同時發生時，
  使用者以為「統計沒過」，實際是身分沒解出來；兩種修法完全不同。
- 處置：**採納並修補**。身分檢查前移到最前面。

### C5 — 掃描立方體在匯入標籤模式下殘留（我沒想到）
- findings：`GROK-R1-P2-01`
- 我只藏了掃描控制項並清 config，但 `ScanCubeBrowser` 沒依 `labelMode` 閘控，
  store 裡的舊 `eventScanDisclosure` 仍可能渲染 ⇒ 使用者以為那些格子是這次 0/1 的結果。
- 處置：**採納並修補**。`hasScan` 與 `cube` 兩處都擋。

### C6 — SPEC／TODO 字面未同步
- findings：`GROK-R1-P2-02`
- 文件仍寫 `status="suppressed"`，與實作定案的 `unavailable`＋reason 不一致。
- 處置：**採納並修補**。字面全部同步，並在 SPEC 新增 **§DEV 實作期偏離** 具名記錄理由
  （`capability_status` 是跨報告共用的封閉枚舉）。

### 判為可接受、不改（三家其一明確背書）
- `GROK-R1-P3-01`：banner 單條優先序、NC／identity 早退順序、`isBinaryMode` 第一列判準
  ——grok 明言「屬可接受取捨，無需為湊數升級」。`isBinaryMode` 另有測試釘住
  「不可用的欄也要有主統計鍵」，故第一列必定帶該鍵。

### 我方前提之驗證結果
- `assumed`「records 帶有 `label_origin`」：**被推翻**（契約列為選填）。
- `assumed`「合法 binary run 必有非空 import_id」：**被推翻**（空字串可過 model）。
- `assumed`「第一列必定帶 `rank_biserial`」：**成立**，且本批補測釘住。

**Verdict**: 需修補後合併——六項修補完成後 Phase 3 可收。
`gate 3a`／`3b`／`3c` 皆 PASS；前端 build rc=0、vitest 707 passed；
decoupling 對 baseline 無新增違規。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**：無 `label_origin` 的舊 scenario-C/legacy records 會被 target staging 當成來源字面 `"0"/"1"`，造成倖存者 provenance 假揭露（P1，信心 10/10）。
**碼證**：`api/services/ic_analysis_service.py:1015-1023` 使用 `rec.get("label_origin", rec.get("label"))`；`event_import_models.py` 明示舊 scenario C 可缺欄；實檔掃描 20260901 批為 60/60 無 `label_origin`。
**來源摘要**：契約允許 optional provenance，不能以答案值代填；最小修法只收非 null `label_origin`（缺席即空 list），或明示 binary 拒絕無 provenance 批。source_digest: 12c334f0aa1f
## CODEX-R1-P1-02
**斷言**：`event_label_mode != auto` 且 `event_import_id=""` 時 target model 只檢查 `is None`，route/service 的 truthy guard 會跳過五階段，靜默跑成一般分析而非 fail-closed（P1，信心 10/10）。
**碼證**：`api/models/ic_models.py:282-285`、`api/routes/ic_analysis.py:122-123`、`api/services/ic_analysis_service.py:1876,1960`；target hook 亦以 truthy ID 選事件分支。
**來源摘要**：Task 3.2 要求非 auto 必有批；最小修法在 request boundary 以 `not self.event_import_id` 擋 blank，並加空字串回歸測試。source_digest: 12c334f0aa1f
## CODEX-R1-P1-03
**斷言**：倖存者落檔先處理 `negative_control_failed`、後驗證 symbol/timeframe；兩者同時缺失時會把結構性 `identity_missing` 誤報成統計性負對照失敗（P1，信心 9/10）。
**碼證**：`momentum/Analysis/ic_filter_orchestrator.py:5552-5583`；既有 target tests 只分別覆蓋 `identity_missing` 與 negative-control，沒有 combined case。
**來源摘要**：identity 是輸出身分前置條件；最小修法把 identity validation 移到 suppression early return 前，保留合法身分的 suppression 行為。source_digest: 12c334f0aa1f
## CODEX-R1-P1-04
**斷言**：前端固定請求 `view=light`，但 target metadata 白名單漏 `label_mode` 與 `event_label_rule`，故頁面讀取的模式 banner／規則揭露在正常 light response 中消失（P1，信心 10/10）。
**碼證**：`ic_result_paging_contract.json:17-24` 無兩鍵；`api/services/ic_result_projection.py:241-243` 僅保留白名單；`useICAnalysis.ts:132` 請求 light，`page.tsx:710-713` 讀兩鍵。
**來源摘要**：最小修法把兩個已由 backend 寫出的 metadata key 加入 allowlist，並增 projection→page integration assertion；不改數值計算。source_digest: 12c334f0aa1f
## COMPOSER-R1-P1-01

**斷言**: 審查標的 `12c334f0` 在 staging 以 `rec.get("label_origin", rec.get("label"))` 填 `label_origin_values`，當 records 無 `label_origin`（契約選填、165 批 fixture 常態）時會產出 `["0","1"]`，假裝揭露原始標籤字面、實際複製 0/1 答案。

**碼證**: `git show 12c334f0:api/services/ic_analysis_service.py` `:1019-1022`；VERIFY: `python3` — `make_event()` 無 `label_origin`；`test_evtlabel_disclosure._records` 亦無。契約 `event_import_contract.json#optional_fields.label_origin`。RECHECK: `git show 12c334f0:api/services/ic_analysis_service.py | rg 'label_origin'`.

**來源摘要**: api/services/ic_analysis_service.py#bc86fca55905

[BLOCKING] 信心度=High。失敗模式：倖存者檔 `label_binary.label_origin_values` 看似可追溯、實為答案重複，下游 ML consumer 誤信編碼未變。修法：缺席回 `[]`（`0e54cce1` 已合）；修訂 `:1022-1027`（HEAD）。

---

ASSUMPTIONS_VERIFIED: label_origin 選填（契約 JSON＋`make_event` 探針）；import_id 雙層閘（ic_models＋stage3）；rank_biserial 每列寫入（orchestrator :5082-5083）；B5 測試批 70 passed
TESTS_RUN: `pytest tests/momentum/Analysis/test_evtlabel_stage3.py tests/momentum/Analysis/test_gap2_survivor_persist.py tests/api/test_evtlabel_staging.py -q` → **70 passed, rc=0**；`python3` 探針 `make_event`／`_records` 鍵集
FAILURES_SEEN: none（審查未改碼）
SCOPE_CHANGES: none（唯讀 review）
NUMERIC_OR_SCHEMA_IMPACT: P1-01 在 12c334f0 會讓 `label_origin_values` 假揭露；HEAD 已改為空 list

產出: `handoffs/20260910-evtlabel-b5-review-r1-composer.md`

TMP_CLEANUP: 清 `/tmp/evtlabel-b5-*`（保留 `claude-501`）

STATUS: DONE
## GROK-R1-P1-01

**斷言**: 標的 tip `12c334f0` 以 `rec.get("label_origin", rec.get("label"))` 填 `label_origin_values`；真實無該欄之事件批會寫出 `["0","1"]`，把答案抄成假 provenance。

**碼證**: `git show 12c334f0:api/services/ic_analysis_service.py` 之 `event_label_binary_meta` 區塊；契約 `optional_fields.label_origin`；實跑 `data_cache/events/20260901T125023Z-8342a31d.json` → fallback `['0','1']`、honest `[]`。`RECHECK:` 對無欄批重算兩種取值；對照 HEAD `0e54cce1` 應為空 list。

**來源摘要**: api/services/ic_analysis_service.py#bc86fca55905；momentum/Analysis/contracts/event_import_contract.json（optional_fields.label_origin）；handoffs/20260910-EVTLABEL-B5-REVIEW-R1-BRIEF.md#b50c411a6bcc

[P1] 信心度=High。會怎麼失敗：倖存者檔看起來「有來源揭露」，下游以為原始字面就是 0/1，實際上批內從未宣告 provenance。  
修法：只收 `rec.get("label_origin") is not None` 之值；缺席 ⇒ `[]`。**HEAD `0e54cce1` 已落地**（本 finding 對標的 tip；reconcile 可 ADOPT-ALREADY-FIXED）。

---

## GROK-R1-P1-02

**斷言**: SPEC Task 3.7／3.8／3.9／3.11 仍要求 `survivor_output.status="suppressed"`，但實作與 B5 測試已定案為 `unavailable`＋`reason=negative_control_failed`（因 `capability_status` 封閉且不含 suppressed）；未改 SPEC 就開 Task 3.11 會按錯字面驗收或被迫擴枚舉。

**碼證**: SPEC Task 3.8「`status:"suppressed"`」／Task 3.11 `WHEN survivor_status=suppressed`；`ic_filter_orchestrator.py` `_write_survivor_output` 早退回 `status: unavailable`；`test_gap2_survivor_persist.py::test_negative_control_failure_suppresses_the_file` 斷言 `unavailable`；`ic_report_contract.json` `capability_status` 無 `suppressed`。`RECHECK:` `jq '.capability_status' momentum/Analysis/contracts/ic_report_contract.json`；`grep -n 'status.*suppressed\|"suppressed"' docs/EVTLABEL_SPEC.md`。

**來源摘要**: docs/EVTLABEL_SPEC.md#4edf088480ca；momentum/Analysis/ic_filter_orchestrator.py#9b09e5cf8074；momentum/Analysis/contracts/ic_report_contract.json#135bd9329391；tests/momentum/Analysis/test_gap2_survivor_persist.py#f40af4ce2def

[P1] 信心度=High。會怎麼失敗：最後一批依 SPEC 寫 `assert status=="suppressed"` ⇒ 恆紅；或有人為過測把 `suppressed` 塞進跨報告枚舉。  
最小修法：**改 SPEC／TODO 字面**為 `unavailable`＋reason；consumer 拒收釘 `reason=="negative_control_failed"` 或 `path is None`。禁止為單一 reason 擴 `capability_status`。

---

## GROK-R1-P2-01

**斷言**: Task 3.2 不變式只擋 `event_import_id is None`，空字串 `""`＋`imported_binary` 可過 model；因 falsy 不進 staging，請求會靜默跑成非事件分析。

**碼證**: 實跑 `ICAnalyzeRequest(..., event_label_mode="imported_binary", event_import_id="")` → ACCEPTED；`None` → REJECTED。`api/models/ic_models.py` `if self.event_label_mode != "auto" and self.event_import_id is None`；service `if request.event_import_id:` 不進五階段。`RECHECK:` 同上 pydantic 構造；再送一次真實 HTTP 看是否 200 且無 `label_mode.effective=imported_binary`。

**來源摘要**: api/models/ic_models.py#562e73247426；api/services/ic_analysis_service.py#bc86fca55905

[P2] 信心度=High。UI 正常選批不會送 `""`；API／腳本可踩中 ⇒ fail-open。  
修法：非 auto 改 `if not self.event_import_id:`（擋 `""`／空白）；可選 `min_length=1`。

---

## GROK-R1-P2-02

**斷言**: 選 `imported_binary` 時只藏了掃描**控制項**並清 `config.event_label_scan`，但 `ScanCubeBrowser` 未依 `labelMode` 閘控；store 裡舊的 `eventScanDisclosure` 仍可能把上一趟掃描立方體畫出來。

**碼證**: `EventBatchDisclosurePanel.tsx`：控制項有 `labelMode !== 'imported_binary'`，`ScanCubeBrowser`（約 L738）無此閘；`page.tsx` 切模式只 `event_label_scan: undefined`，未清 `eventScanDisclosure`。`RECHECK:` UI 先跑一趟 k／h 掃描，再切「只用匯入的 0/1」，看掃描結果瀏覽器是否仍在。

**來源摘要**: frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx#16b2aaf0861f；frontend/src/app/ic-analysis/page.tsx#4b406bb606b8

[P2] 信心度=Medium。會怎麼失敗：畫面仍顯示與本次 0/1 無關的掃描立方體，違反 brief「選 imported_binary 時掃描區不渲染」。  
修法：`labelMode !== 'imported_binary' && <ScanCubeBrowser …/>`；切模式時一併清 disclosure／或 `hasScan={… && labelMode!=='imported_binary'}`。

---

## GROK-R1-P3-01

**斷言**: banner 單條優先序與 NC／identity 早退順序屬可接受取捨；`isBinaryMode` 第一列判準在現碼＋單測下足夠，無需為湊數升級。

**碼證**: `labelModeBannerText` 先 NC 再 insufficient_blocks；`_write_survivor_output` NC 先於 identity；`test_every_row_gets_binary_keys_even_when_unavailable`。

**來源摘要**: frontend/src/lib/icLabelRule.ts#9187a4b43f1d；momentum/Analysis/ic_filter_orchestrator.py#9b09e5cf8074；tests/momentum/Analysis/test_evtlabel_stage5.py#9bb31f1c5c87

[P3] 信心度=High。建議保留現行為；可選雙信號／堆疊次要 info，非本輪阻擋。

---

### §1 十一類（無則標無）

1. 矛盾/互斥：有——SPEC `suppressed` vs 碼／測 `unavailable`（P1-02）。  
2. 漏項/端到端：有——掃描區在 imported_binary 下結果瀏覽器未完全關掉（P2-02）；Task 3.10／3.11 仍待（brief 已標 needs-research）。  
3. 不可測驗收：無新增空殼；B5 對 NC 不落檔／capability 枚舉有測。  
4. 可疑 quant 假設：無本批新引入（NC／置換屬 B4；本批是交接物）。  
5. 過度工程：無（≥10× 無）；`unavailable`＋reason 優於擴枚舉。  
6. OOM/並行：無。  
7. Cache 正確性：無新 cache key。  
8. API/型別/相容：空字串 import_id 洞（P2-01）；欄名 `n_pos_selection` 已與契約對齊。  
9. 測試品質：有 unavailable 列必帶鍵之釘；缺空字串 import_id 測、ScanCube 切模式測。  
10. Agent 可執行性：修法已落到檔案／條件行級。  
11. 必要性/短命工：無（倖存者來源＋畫面為最終交接面，非鷹架）。

---

