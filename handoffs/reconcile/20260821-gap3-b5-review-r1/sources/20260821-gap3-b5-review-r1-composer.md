# GAP-3 B5 review R1（COMPOSER）

TASK_ID: 20260821-GAP3-B5-REVIEW-R1  
FAMILY: COMPOSER  
SCOPE: brief `handoffs/20260821-gap3-b5-review-brief.md` 指定 B5.1 API 接線＋B5.2 前端三頁；review-only，未改程式碼。

## Verdict：可進 stamp／交使用者 UAT（無 P0/P1；本輪 0 條實質 finding）

B5 Gate 本輪複驗：`tests/api/ -k gap3_import` 9 passed、`tests/momentum/event_samples/` 228 passed、`cd frontend && npx vitest run gap3` 13 passed（主委 receipt 另含 build/plain_docs/golden，brief fact-verified）。R7：`EventImportService` 只 `parse_upload`＋`create_event_sample_pipeline().validate()` 透傳 failures；legacy adapter 三路徑（舊三欄→新端點 400、新 schema→舊端點 400、混合欄 422 逐列 reason）均有測試或探針 fail-closed；前端三欄 wiring（匯出／匯入／事件模式兩表＋ms→秒橋接）與 vitest 鎖一致。W10 receipt 三欄齊（`n_events=10000`、`wall_clock_s=76.377`、`peak_rss_mb=305.1`）。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 摘要 |
|------|------|------|
| factories 三出口不違白名單 | **成立（裁決）** | TODO §0-6-⑦ 寫「一個 `create_event_sample_pipeline()`」；另兩個 `create_event_import_contract`／`create_condition_engine_contract` 為契約 JSON **唯讀**出口，供 `migration_hint`／`allowed_filtering_params`（R3 禁 api 直 import `momentum/Analysis/...`）。`factories.py:834-855` 註解與 SPEC §RISK 末行一致；非第三套 validator。 |
| 辨別表 `not_computed` 為正確揭露 | **成立** | `pipeline.analyze_tables`（`pipeline.py:89-91`）硬編 reason＝`no_model_scores_in_event_pipeline`；UAT C 段＋`gap3_event_tables.test.tsx:42-46` 鎖前端顯示；分數來源屬 B4.1／ML 層，非 UAT 遮蔽。 |
| `/search` 匯出 `horizon_bars` 預設 2 | **成立（文件化）** | `eventExport.ts:58,90`＋`note` 欄；UAT B2 要求使用者匯入前確認；後端 validator 為 SoT。 |
| 事件存 `data_cache/events/<import_id>.json` | **成立** | `case_import_service.py:614,727-735`；不寫 `cases.json`；舊檔不遷移。 |

---

## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對 brief 必答 1–10 與 assumed 四條後，無需阻擋 stamp／使用者 UAT 的 P0/P1 finding；B5.1 legacy/R7/解耦、B5.2 三欄 wiring、W9/W10 均對齊 TODO／Gate receipt。

**碼證**: `venv/bin/python -m pytest tests/api/test_gap3_import.py -q` → 9 passed rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 228 passed rc=0；`cd frontend && npx vitest run gap3` → 13 passed rc=0。程式對讀：`case_import_service.py:608-741`（R7 透傳）、`case.py:87-93,121-129`（legacy 首列偵測 utf-8-sig）、`eventExport.ts:57-100`（匯出形狀）、`EventTablesPanel.tsx:13-18,73-80`（not_computed reason 顯示）、`api.ts:1042-1047`（ms→秒）。探針：BOM CSV `pd.read_csv` 欄名仍為 `event_id`（非 silent coerce）；大小寫變體 `Event_ID/T0/Label` ⇒ `looks_legacy/new_schema` 皆 False → validator `unknown_field`（422），非靜默轉換。`handoffs/run_receipts/gap3_import_scale.json` 含 `n_events`／`wall_clock_s`／`peak_rss_mb`。

**來源摘要**: handoffs/20260821-gap3-b5-review-brief.md#d773c7989a5e；docs/GAP3_UAT_CHECKLIST.md#90d8356bd603

---

## 必答逐項（1–10）

1. **B5.1／B5.2／B5.3 對 TODO**：B5.1 API＋legacy＋W10 receipt＋B3 follow-up（`requests.py:49-51` 讀契約）均落地；B5.2 三頁＋3 vitest 檔 13 條；B5.3 `GAP3_UAT_CHECKLIST.md` A/B/C 段齊。TODO 邊界②「分頁/串流」未實作，但 W10 驗收形＝receipt 三欄（記錄型）已滿足，不私定門檻。**三 factories 出口**：見 §0 裁決，不判越權。
2. **R7／契約 SoT**：`import_records` 只呼叫 `_pipeline.validate`（`case_import_service.py:712`）；`looks_legacy`／`looks_new_schema` 只看鍵名集合（`630-636`）。`test_gap3_import_contract_reasons_passthrough_not_reimplemented` 以字串掃描 gap3 段＋reason 子集断言——**單獨偏弱**，但搭配本輪全文對讀＋9 條 API 測試＋`import_contract.py` 唯一 reason 字面，可接受；建議後續可加「API 檔不得 import `validate_event_import`」grep gate（非本輪 BLOCKING）。
3. **legacy adapter**：測試覆蓋 CSV/JSON 舊三欄、新 schema 投舊端點、混合欄 422；探針無 silent coerce（BOM／大小寫均 fail-closed）。JSON 舊三欄物件列表同拒（`test_gap3_import_legacy_three_columns` L83-84）。
4. **`source_file_digest`**：`verify_source_digest=False` 預設（`case_import_service.py:701-704,729`）與契約 `_doc`「digest 對證需 source_bytes」一致；欄位語意＝使用者原始來源 sha256，API 另記 `upload_sha256`。匯出端 `sourceDigest`＝cases 內容 hash（`eventExport.ts:62-64`），非 upload 自指——合理。
5. **R1–R7**：B5 新增 api 路徑均經 `create_event_sample_pipeline()`／契約 factories（brief fact-verified baseline rc=0）。`bars_source.py` 綁 kline HDF5 為 **bars 來源**，非事件契約欄位（SPEC §C-7「事件契約不綁 HDF5 佈局」）——可接受。
6. **分析端點**：`/case/events/{id}/analyze` → `run_with_params`＋`event_forward_return_table`（`test_gap3_import_analyze_tables_real_kline`）；辨別表 `not_computed` reason 非契約 `capability_unavailable_reasons` 枚舉——屬管線能力揭露（非 import 契約），UAT C 已登記；前端 vitest 鎖 `no_model_scores_in_event_pipeline` 非空白。
7. **前端 wiring 三欄**：`/search` 匯出 passes validator（探針：含 `search_rule_summary`／非 hex `data_snapshot_digest` 合法；**單一 label 類別整批** ⇒ `missing_control_group` 批次拒收——fail-closed，非 silent；典型兩階段搜尋含 0/1 兩類）。jsdom FNV 64-hex 仍過 `_is_hex64`（契約只驗格式）；瀏覽器走 `crypto.subtle` 真 sha256。IC 橋接 `Math.floor(ms/1000)`（`api.ts:1042-1047`）＋ vitest 鎖。兩表僅 event 模式；unavailable/not_computed 三態齊。
8. **W10 receipt**：`gap3_import_scale.json` 三欄齊；73s 對齊純 Python 逐事件；UAT C 已登記殘留。
9. **UAT checklist**：A 段命令可跑（本輪複驗子集 rc=0）。B 段 11 項覆蓋匯入→對齊→兩表→IC→Global。**缺口（非 BLOCKING）**：B 段未顯式逐步驗「第三表 conditional_ic」獨立 UI（B5 事件模式只掛兩表；conditional_ic 在 B9 IC 報告內）；「全 K 線」由 B9（event_filter.mode=timestamps）＋ B10 Global 回切間接覆蓋，建議使用者 UAT 時 B9 加查 IC 報告 `statistic_kind=conditional_ic` 段——不阻 stamp。
10. **進 stamp？**：是——無 P0/P1；待使用者 B 段簽字後 epic 收案。

---

## VERIFY（本輪複驗）

```
venv/bin/python -m pytest tests/api/test_gap3_import.py -q → 9 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 228 passed rc=0
cd frontend && npx vitest run gap3 → 3 files 13 passed rc=0
inline：EventImportService BOM/大小寫探針 → fail-closed（422/unknown_field），無 coerce
inline：buildEventContractRecords 形狀 + mixed label → validate rc=0
read：git diff 48f722b7..HEAD → 24 files +1967/-13（與 brief 標的一致）
```

ASSUMPTIONS_VERIFIED: 上述命令＋`case_import_service.py` EventImport 段／`pipeline.py`／`eventExport.ts`／`EventTablesPanel.tsx`／`GAP3_UAT_CHECKLIST.md` 全文對讀。  
TESTS_RUN: 見 VERIFY。  
FAILURES_SEEN: none。  
SCOPE_CHANGES: none（review-only）。  
NUMERIC_OR_SCHEMA_IMPACT: none。

OUTPUT_PATH: handoffs/20260821-gap3-b5-review-r1-composer.md

STATUS: DONE
