# EVTLABEL B5（Phase 3 第三批：Task 3.8／3.9）code review R1（grok）

brief-kind: review  
task-id: 20260910-EVTLABEL-B5-REVIEW-R1  
family: grok  
findings-round: R1  
標的 diff：`git diff a98b3a84..12c334f0 -- momentum api tests frontend`  
SCOPE: review-only；禁改碼／禁改文件  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0／§1（審查對象＝碼）＋`templates/COMMITTEE_FINDING_TEMPLATE.md`

SOURCE-DIGESTS:
- `api/services/ic_analysis_service.py@12c334f0#bc86fca55905`（HEAD/`0e54cce1` 已改＝`#c451536a0652`）
- `momentum/Analysis/ic_filter_orchestrator.py#9b09e5cf8074`
- `frontend/src/lib/icLabelRule.ts#9187a4b43f1d`
- `frontend/src/components/ic-analysis/ICSummaryTable.tsx#e83069cd3dc4`
- `frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx#16b2aaf0861f`
- `frontend/src/app/ic-analysis/page.tsx#4b406bb606b8`
- `api/models/ic_models.py#562e73247426`
- `momentum/Analysis/contracts/ic_report_contract.json#135bd9329391`
- `momentum/Analysis/contracts/event_label_mode.json#b68f67dc33bd`
- `docs/EVTLABEL_SPEC.md#4edf088480ca`
- `tests/momentum/Analysis/test_gap2_survivor_persist.py#f40af4ce2def`
- `tests/momentum/Analysis/test_evtlabel_stage5.py#9bb31f1c5c87`
- `handoffs/20260910-EVTLABEL-B5-REVIEW-R1-BRIEF.md#b50c411a6bcc`

---

## Verdict：需修補後派工（不可在 SPEC 字面未改寫前直接開 Task 3.10／3.11）

Task 3.8／3.9 主路徑（`label_binary` 寫入、負對照失敗不落檔、模式三選、binary 表頭、`LabelModeBanner` 以 reason 判紅）與產品主目標交接面大致對得上。  
**阻塞級**在兩處：① 標的 tip `12c334f0` 之 `label_origin_values` 回退成 `label` 本身（假 provenance；**HEAD `0e54cce1` 已修**）；② SPEC 仍寫 `survivor_output.status="suppressed"`，實作／B5 測試已改 `unavailable`＋reason——Task 3.11 若照 SPEC 字面釘 `status==suppressed` 會假紅或逼人擴枚舉。  
另有 P2：空字串 `event_import_id=""` 繞過 Task 3.2 之 `is None` 不變式。  
**P0=0／P1=2／P2=2／P3=1**。`label_origin` 已修者可標 ADOPT-ALREADY-FIXED；SPEC 字面必須在開最後一批前改寫。

---

## 驗收／探針實跑

| 探針 | 結果 |
|---|---|
| 真實 `data_cache/events/*.json` 23 檔 | **14 檔有 `label_origin`／9 檔全無**；列計 927 有／723 無 |
| 無 `label_origin` 批（`20260901T125023Z-8342a31d`）套 `12c334f0` 回退寫法 | `label_origin_values → ['0','1']`（假揭露） |
| 同批改只收真有之 `label_origin` | `→ []`（誠實空） |
| 有欄批（`20260909T130533Z-7f73e4c7`） | origins=`['search_positive_case']` |
| 契約 `optional_fields.label_origin` | **在**；`required_fields` **不在** |
| `ICAnalyzeRequest(event_label_mode=imported_binary, event_import_id="")` | **ACCEPTED**（空字串） |
| 同請求 `event_import_id=None` | **REJECTED**（Task 3.2 文案） |
| `capability_status` | `ok/not_applicable/not_computed/computation_failed/disabled/unavailable`；**無 `suppressed`** |
| `_merge_binary_statistics` 對 unavailable 列 | 仍寫 `rank_biserial`（`test_every_row_gets_binary_keys_even_when_unavailable`） |
| B5 diff vs HANDOFF 既有紅檔名 | **未碰** golden／persist 污染／factories 等具名紅檔 |

VERIFY 摘要：
```text
python3 -c '…scan data_cache/events…'
# files=23 files_with_any_lo=14 files_without_lo=9
# no-lo fallback=['0','1']；honest=[]
python3 -c 'ICAnalyzeRequest(..., event_label_mode="imported_binary", event_import_id="")'
# empty ACCEPTED ''
```

---

### §0 前提宣告

fact-verified: `label_origin` 為契約 **optional**；真實落檔 9/23 批完全沒有該欄。  
fact-verified: 標的 tip `12c334f0` 用 `rec.get("label_origin", rec.get("label"))` ⇒ 無欄批得到 `["0","1"]`。  
fact-verified: HEAD `0e54cce1` 已改為只收真有之 `label_origin`，缺席 ⇒ 空 list。  
fact-verified: 合法 API binary 路徑（有非空 `event_import_id` 進 staging）才會產出 binary map；`event_timestamps` legacy **不會**變 binary。  
fact-verified: 空字串 `event_import_id=""`＋`imported_binary` 通過 model，且因 falsy 不進事件 staging ⇒ **靜默非事件 run**。  
fact-verified: `_write_survivor_output` 負對照早退回 `status=unavailable`＋`reason=negative_control_failed`；B5 測試已釘此字面；SPEC 仍寫 `suppressed`。  
fact-verified: `_merge_binary_statistics` 對每一列（含 unavailable）寫 `rank_biserial`；前端 `isBinaryMode` 與 SPEC「有鍵才切版面」一致。  
fact-verified: banner 優先序 NC danger > insufficient_blocks warn > imported_binary info > auto-degraded warn。  
fact-verified: B5 未改 HANDOFF 具名之既有紅測試檔。

assumed: 「records 帶有 `label_origin`」→ **推翻**（契約 optional＋9 檔實證無欄）。  
assumed: 「`event_timestamps` 可走 binary 而無 import_id」→ **推翻**（無 binary map；stage3 raise 只打直呼 orchestrator 缺 meta）。  
assumed: 「unavailable 列不寫 `rank_biserial`」→ **推翻**（merge 全列寫入＋單測釘住）。

### §0 前提覆核摘要表

| 陳述 | 本輪 verdict | 依據 |
|---|---|---|
| records 皆有 `label_origin` | **不成立** | 9/23 檔 0 列有該欄 |
| tip 回退成 label＝假 provenance | **成立（tip）／HEAD 已修** | 實跑 `['0','1']`；`0e54cce1` |
| timestamps 路徑可 binary 無 import_id | **不成立** | staging 只在 truthy import_id |
| 空字串 import_id 被擋 | **不成立** | model 只驗 `is None` |
| unavailable 列缺 `rank_biserial` 鍵 | **不成立** | merge＋stage5 測 |
| status=suppressed 與契約一致 | **不成立** | enum 無 suppressed；碼用 unavailable |
| 本批加重既有 20 紅 | **未見（檔名面）** | diff 未碰具名紅檔 |

---

## 必答（成對）

### 1a. records 有沒有 `label_origin` 欄？

**有些有、有些沒有。** 契約列在 `optional_fields`（非 required）。真實 `data_cache/events/`：**14/23 檔有、9/23 檔全無**（列 927 有／723 無）。舊批鍵集示例無該欄；較新批常見值 `search_positive_case`／`platform_random`。

### 1b. 若沒有，該省略還是改取別的來源？

**省略（空 list），禁止回退成 `label`。** tip `12c334f0` 的回退會讓無欄批寫出 `["0","1"]`——看起來像 provenance、其實只是把答案抄一遍。HEAD `0e54cce1` 已改為只收真有之 `label_origin`。不得改取 `label`／`label_value` 充數。

### 2a. 合法 binary run 是否必有非空 import_id？

**經 API／service 的合法 binary run：是。**  
- Task 3.2：`event_label_mode≠auto` 且 `event_import_id is None` ⇒ 400。  
- staging／binary map 只在 `if request.event_import_id:`（truthy）進入。  
- `auto`→`imported_binary` 也必須先有批才有 0/1 map。  
- `event_timestamps` legacy **不能**變成 binary（作者否證觀測不成立）。  
stage3 缺 `import_id` 的 raise＝直呼 orchestrator 的防禦，不是擋合法 UI 路徑。

### 2b. 若否，fail-closed 該放在哪一層？

主答案見 2a（合法路徑必有）。**殘洞**：model 只擋 `None`、不擋 `""` ⇒ 見 **GROK-R1-P2-01**。最小修法：Task 3.2 不變式改為對非 auto 要求 **truthy** `event_import_id`（`if self.event_label_mode != "auto" and not self.event_import_id`）。

### 3a. suppressed 早退與 identity_missing 之優先序何者正確？

**現行（NC／suppressed 在 identity 之前）可接受。** 兩者皆不落檔；同時發生極稀（能跑完負對照通常已有 symbol／tf）。NC 失敗是產品結論（不可餵 ML）；identity_missing 是組裝前置缺欄。對使用者，紅 banner 的 NC 文案比 plumbing 缺欄更對準主目標。

### 3b. 建議

維持現序。若要更嚴：identity 檢查可再提前到 `case_id` 之後、NC 之前，並加一測「兩條件同時 ⇒ 仍不落檔＋reason 二擇一有文件」。非阻擋。

### 4a. `unavailable`＋reason 取代 `suppressed` 可接受嗎？

**工程上可接受；SPEC 字面目前不可接受（漂移）。**  
理由：`metadata.survivor_output.status ∈ capability_status`，枚舉無 `suppressed`；擴枚舉會波及全報告。前端／B5 測試已改以 **reason=`negative_control_failed`** 判紅／斷言。語意（不可消費）成立。

### 4b. 若否，最小修法

**不要擴 `capability_status`。** 最小修法＝改 SPEC Task 3.7／3.8／3.9／3.11 字面：`status="unavailable"`＋`reason="negative_control_failed"`；Task 3.11 consumer 拒收條件改釘 `reason` 或 `path is None`，禁再釘 `status=="suppressed"`。見 **GROK-R1-P1-02**。

### 5a. `isBinaryMode` 由第一列判是否為真風險？

**在現行後端下不是真風險。** `_merge_binary_statistics` 對每一列都寫 `rank_biserial`（含 `binary_status!=ok`）；`test_every_row_gets_binary_keys_even_when_unavailable` 已釘。JSON `null`／NaN 在 JS 仍 `!== undefined` ⇒ 仍判 binary。作者「不可用就不寫鍵」之否證觀測被碼推翻。

### 5b. 更穩的判準

可選強化（非必須）：`metadata.label_mode.effective==="imported_binary"` **或** `event_label_rule.primary_statistic==="rank_biserial"` 與「列上有鍵」做 AND／OR 雙信號；缺一則 loud 空態而非默默退回報酬版。SPEC 目前明文「有鍵才切版面」——與現碼一致。

### 6a. banner 只顯示最嚴重那條是否足夠？

**安全上足夠。** NC 失敗時唯一要傳達的是「不可餵 ML」；資訊級「本次是 0/1」被蓋住不致誤餵。`insufficient_blocks` 與 NC failed 在碼上幾乎互斥（區塊不足時 `_survivor_suppressed_reason=None`）。

### 6b. 若否，建議的呈現方式

可選：danger 主條＋一行次要 info（正反數）不升色。非阻擋。

### 7. 有無 ≥10× 不必要複雜？本批可否進最後一批？

**無 ≥10× 複雜。** 可進 Task 3.10／3.11 的條件：① 確認 `0e54cce1` 之 `label_origin` 修在主線；② **先改 SPEC 字面**（P1-02）再寫 3.11 驗收；③ 建議順手修空字串 import_id（P2-01）。

---

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

## 被當成事實的未驗證假設（§0）

1. 「records 帶有 `label_origin`」——作者標 assumed／沒查 → **本輪推翻**（P1-01）。  
2. 「timestamps 路徑可 binary 而無 import_id」——**推翻**。  
3. 「unavailable 列不寫 `rank_biserial`」——**推翻**。  
4. 「合法 binary 必有非空 import_id」——**對 truthy 路徑成立**；空字串另洞（P2-01）。

---

## 既有紅歸因（必答 7／brief 點 7）

B5 改動檔＝service／orchestrator／event_label_mode 契約／前端 Task 3.9／evtlabel 與 survivor persist 測。**未改** HANDOFF 具名之 `test_ic_persist_*`／golden digest／factories inventory 等。未重跑 `tests/momentum/Analysis` 全套（brief 禁治理小時級；既有紅為基準）。就檔名與呼叫面：**未見本批接入那 20 條生產路徑**。建議仍走另票 `REDSWEEP`。

STATUS: DONE
