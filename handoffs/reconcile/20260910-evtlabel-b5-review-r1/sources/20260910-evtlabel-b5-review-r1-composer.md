brief-kind: review
task-id: 20260910-EVTLABEL-B5-REVIEW-R1
family: composer
findings-round: R1
標的 diff：`git diff a98b3a84..12c334f0 -- momentum api tests frontend`

## Verdict：可派工

Task 3.8／3.9 主線（倖存者 `label_binary` 來源身分、負對照失敗不落檔、前端三選＋binary 表頭＋`LabelModeBanner`）結構清楚，B5 相關測試 **70 passed**（`test_evtlabel_stage3`／`test_gap2_survivor_persist`／`test_evtlabel_staging`）。**一條 P1** 存在於審查標的 commit `12c334f0`（`label_origin_values` 缺席時回退成 `label`），**已在後續 `0e54cce1` 自修**；HEAD 狀態下其餘六項必答取捨均可接受，可進 Task 3.10／3.11。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| records 恆帶 `label_origin` | **推翻** | 必答 1a；契約 `optional_fields`＋165 批 fixture 無該欄 |
| 合法 binary run 必有非空 `import_id` | **fact-verified** | 必答 2a；Task 3.2 不變式＋stage3 fail-closed |
| 第一列恆帶 `rank_biserial` 鍵 | **fact-verified（讀碼）** | 必答 5a；`_merge_binary_statistics` 對每列寫鍵（值可 NaN） |
| `status="suppressed"` 字面 | **刻意偏離、可接受** | 必答 4a；`capability_status` 封閉枚舉＋測試釘住 |
| 本批加劇 HANDOFF 20 條既有紅 | **維持** | 必答 7；B5 diff 未觸 persist／golden／inventory 根因 |

---

## 必答（成對）

### 1a／1b `label_origin_values` 取法

- **1a（實跑＋讀契約）**：**多數真實路徑沒有 `label_origin` 欄**。VERIFY: `python3` 探針 — `make_event()`（scenario=C 舊批）鍵集無 `label_origin`；`test_evtlabel_disclosure._records(136,29)` 亦只含 `label` 不含 `label_origin`。契約 `event_import_contract.json` 將 `label_origin` 列在 `optional_fields`（非 `required_fields`）；`test_evtlabel_staging::test_label_origin_is_optional_in_the_import_contract` 已釘住。
- **1b**：**缺席應回 `[]`，不得回退成 `label`**。審查標的 `12c334f0` 用 `rec.get("label_origin", rec.get("label"))` ⇒ 165 批會得 `["0","1"]`，等於把答案抄進「來源揭露」——假資料。最小修法：`ic_analysis_service.py` staging 改為只收集 `rec.get("label_origin") is not None` 者；**HEAD `0e54cce1` 已實作**並加 `test_label_origin_values_are_not_faked_from_labels`。

### 2a／2b `import_id` fail-closed

- **2a**：**合法 `imported_binary` run 必有非空 `event_import_id`**。`ic_models.py:282-286`：`event_label_mode != "auto"` 且無 `event_import_id` ⇒ 400；`_run_event_label_stages` 只在 `request.event_import_id` 為真時進入（`:769`、`:1880`）；`event_timestamps` 路徑不得帶 `imported_binary`（同檔互斥＋Task 3.2）。`auto` 解析成 binary 仍走 import 批 staging ⇒ `import_id` 來自同一 `request.event_import_id`。
- **2b**：**fail-closed 放在 stage3 正確**（`ic_filter_orchestrator.py:3916-3919` `AlignmentViolationError`）。route 已 400 的第一道閘夠；stage3 是倖存者檔追溯的最後防線，不應下放。

### 3a／3b suppressed 與 identity_missing 優先序

- **3a**：現行 `_write_survivor_output` 順序：`case_id` → **suppressed 早退** → `symbol/timeframe` 檢查（`:5551-5583`）。兩者同時成立時回 `unavailable`＋`negative_control_failed`，而非 `identity_missing`。
- **3b（建議）**：**suppressed 優先正確**。負對照失敗是「這批倖存者不可餵 ML」的業務結論；`identity_missing` 是基礎設施缺欄。兩者都不落檔，但使用者需先看到分析品質失敗原因。`case_id` 已在兩條路徑回傳，不損追溯。

### 4a／4b `unavailable`＋reason 取代 `suppressed`

- **4a**：**可接受**。`ic_report_contract.json` 之 `capability_status` 封閉枚舉不含 `suppressed`；`test_gap2_survivor_persist::test_status_stays_inside_the_closed_capability_enum` 釘住。語意由 `reason=negative_control_failed` 承載；前端 `labelModeBannerText` 以 **reason** 判紅色（`:253-257`），不靠 status 字面。
- **4b**：若堅持 SPEC 字面，最小修法是擴充 `capability_status` 加 `suppressed`——**代價大於收益**（跨報告共用枚舉）。現行取捨優於擴枚舉。

### 5a／5b `isBinaryMode` 由第一列判

- **5a**：**當前實作風險低、契約未釘**。`_merge_binary_statistics` 對 `summary_table` **每一列**寫入 `row["rank_biserial"]`（`:5082-5083`），即使 `binary_status != ok` 鍵仍存在（值可 NaN）。第一列缺鍵只會在「非 binary 模式」或空表發生——符合 SPEC「由列鍵決定版面」。
- **5b（更穩判準）**：若要釘死，可用 `metadata.label_mode.effective === 'imported_binary'` 或報告級 `event_label_rule.primary_statistic`；但 SPEC Task 3.9 刻意選「有 `rank_biserial` 鍵才切版面」。建議補一條測試：`imported_binary` 報告每列必有 `rank_biserial` 鍵（非僅第一列）——非阻進度。

### 6a／6b banner 優先序

- **6a**：`labelModeBannerText` 單條最嚴重：`negative_control_failed`（danger）> `unavailable:insufficient_blocks`（warn）> `imported_binary` info > `auto` 退回 warn（`:253-278`）。與 `DegradedBanner`（OOS 降級）分開——兩者可同屏，職責不同。
- **6b**：**足夠**。同時 NC 失敗又 auto-degraded 時，紅色「不可餵 ML」優先於琥珀「已退回報酬版」合理；若要改進，可在 danger 文案末附一句「（label 模式：已退回報酬版）」——P3 體驗項，非阻進度。

### 7 複雜度／既有紅／可否進 3.10

- **無 ≥10× 不必要複雜**；B5 為契約＋薄 glue＋前端揭露，合理。
- **既有紅**：HANDOFF「`tests/momentum/Analysis` 20 failed」三類根因本 diff 未觸及；B5 相關 **70 passed**（未跑全套；基線與 HANDOFF 一致）。
- **進 3.10／3.11**：**可**（HEAD 含 `0e54cce1` 後）。

---

## §1 必查摘要

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | SPEC `suppressed` 字面 vs `unavailable`（已具名偏離，可接受，必答 4） |
| 2 | 漏項 | `label_origin` 缺席處理在 `12c334f0` 有洞；HEAD 已修（P1-01） |
| 3 | 不可測 | B5 測試＋vitest 707 passed（brief fact-verified）；e2e 留 3.10 |
| 4 | quant | 假揭露 `["0","1"]` 會误导下游（P1-01）；NC 不落檔 fail-closed 正確 |
| 5 | 過度工程 | 無 |
| 6 | OOM | 無 |
| 7 | cache | 掃描格 `event_label_binary_meta=None` 正確 |
| 8 | API/型別 | `n_pos_selection`／`n_neg_selection` 與契約對齊（vitest 對證） |
| 9 | 測試 | 缺「每列必有 rank_biserial 鍵」回歸（P3 建議） |
| 10 | Agent | 落到檔案／函式，可執行 |
| 11 | 短命工 | 無 |

---

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
