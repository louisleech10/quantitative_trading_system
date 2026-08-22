# GAP-3 事件型 UAT 缺口修補 SPEC — 對抗審 R4（COMPOSER）

task-id: 20260822-GAP3UX-X-REVIEW-R4  
brief: `handoffs/20260822-gap3ux-x-review-r4-brief.md`  
標的: `docs/GAP3_EVENT_UX_SPEC.md`（sha256 `3bc04411cdf2…`，900 行；**尚未實作**）  
家族: COMPOSER | 輪次: R4

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 分類 | 本輪覆核 |
|---|---|---|
| SPEC sha256／行數與 brief 鎖定一致 | **fact-verified** | `shasum -a 256` → `3bc04411cdf2…`；`wc -l` → 900 |
| Phase 7 六維度三層巢狀路徑 | **fact-verified** | `python3 handoffs/20260822-gap3ux-x-review-r4-dims.py` 與 `facts.out` 逐字一致（除 HEAD） |
| `control_kind` enum=4／accepted=3 | **fact-verified** | `dims.py --counts`；契約 L43-48 |
| `eventExport.ts` 五處寫死／`counterexample_kind` 未送 | **fact-verified** | facts.sh F-06；`EventExportOptions` 僅 `scenario?`／`entryPriceSemantic?` |
| `/search` 呼叫端未傳六維度 opts | **fact-verified** | facts.sh F-07；`page.tsx:522-527` |
| D-7 L1/L2/L3 已落到 Task 1.10/1.11/1.12＋2.1b | **fact-verified（SPEC 層）** | Task 2.1b L495-509 改讀 registry；**實作尚未存在** |
| Task 7.2 集合相等即可擋接線漂移 | **assumption，不成立** | 見 **COMPOSER-R4-P0-02** |
| Phase 7 六維度盤點＝全棧殘留完整清單 | **assumption，不成立** | IC 頁／Feature Library `time_range` 仍漏；見 **COMPOSER-R4-P1-01/02** |
| G-2「sha256＋三項」已足 Frozen | **assumption，不成立** | Task 2.2 已要求 serialization 涵蓋 `filters`＋六維度，但無定義 Task；見 **COMPOSER-R4-P1-03** |
| `/search` 選 scenario A/B 時 label 語意仍 t0 正反例 | **fact-verified（現碼）** | `eventExport.ts:75-77,95`；SPEC 未寫邊界；見 **COMPOSER-R4-P1-04** |

---

## R3 十八條之 CLOSED／OPEN（本輪逐條標）

| R3 ID | 本輪 | 碼證摘要 |
|---|---|---|
| CODEX-R3-P0-01 | **CLOSED** | Task 1.10/1.11/1.12 建立 registry＋L2/L3；Task 2.1b L495-509 改讀 `lookahead_bars` 標註（含 drawdown／future72） |
| CODEX-R3-P0-02 | **CLOSED** | Task 4.1b L591-606 改為動態導出；刪固定「t0／不看未來」句；與 Task 7.3 L815-826 對齊 |
| CODEX-R3-P0-03 | **OPEN** | Task 7.1 L787-788／7.2 L802-803 仍 `length === contractEnum.length`；無 round-trip；見 **COMPOSER-R4-P0-01/02** |
| CODEX-R3-P1-04 | **OPEN** | §G L269-273 仍無 serialization 契約；見 **COMPOSER-R4-P1-03** |
| CODEX-R3-P1-05 | **OPEN** | Phase 7 未列 ic-analysis；`RunInfo` 無 `time_range`；見 **COMPOSER-R4-P1-01/02** |
| COMPOSER-R3-P1-01 | **CLOSED** | 同 CODEX-P0-01 |
| COMPOSER-R3-P1-02 | **CLOSED** | Task 1.10 建立 `future_column_lookahead.json` |
| COMPOSER-R3-P1-03 | **CLOSED** | 同 CODEX-P0-02 |
| COMPOSER-R3-P1-04 | **OPEN** | `control_kind` enum(4)≠accepted(3)；見 **COMPOSER-R4-P0-01** |
| COMPOSER-R3-P2-01 | **OPEN** | `EventImportPicker` 只傳 t0 秒戳；見 **COMPOSER-R4-P1-01** |
| COMPOSER-R3-P2-02 | **OPEN** | 同 CODEX-P1-04 |
| COMPOSER-R3-P2-03 | **OPEN** | `/search` label 仍 `positive_case`；見 **COMPOSER-R4-P1-04** |
| GROK-R3-P0-01 | **CLOSED** | 同 CODEX-P0-01 |
| GROK-R3-P0-02 | **CLOSED** | 同 CODEX-P0-02 |
| GROK-R3-P1-01 | **CLOSED** | Task 1.10 L388-392 小時命名改 `lookahead_hours`＋TF 換算，禁寫死 72 |
| GROK-R3-P1-02 | **部分 CLOSED** | 深度公式：Task 2.1b 統一 `max(lookahead_bars)`；**A/B label 語意／禁止邊界仍 OPEN** → **COMPOSER-R4-P1-04** |
| GROK-R3-P1-03 | **OPEN** | 同 COMPOSER-R4-P0-02 |
| GROK-R3-P1-04 | **OPEN** | 同 COMPOSER-R4-P1-03 |

**計數**：18 條中 **11 CLOSED**、**7 OPEN**（聚類為檔頭 D／E／F／G 四項）。

---

## R3 遺留四條（D／E／F／G）現行處置是否足夠

| 代號 | 足夠？ | 判定 |
|---|---|---|
| **D**（7.2 disabled／enum≠accepted） | **否** | Task 7.1/7.2 字面仍比對 `contractEnum.length`；`platform_random_bars` 恆拒使基準未定義；缺 UI→payload round-trip（§C0：正確性類不得殘留放行） |
| **E**（IC 頁＋FL `time_range`） | **否** | Phase 7 僅 `/search`＋`/data-preparation`；IC 事件模式選批後不揭露契約六維度；`list_runs`／`RunInfo` 無 `time_range` 無法對證事件 t0 覆蓋 |
| **F**（G-2 serialization） | **否** | §G 仍只有 sha256＋三項；Task 2.2 L518-520 已**依賴**未定義之 serialization ⇒ 實作會各自發明 bytes |
| **G**（A/B 深度＋label 漂移） | **否** | 深度側 Task 2.1b 已統一；**語意側** Task 7.1 接 scenario UI 但未界定 `/search` 路徑 A/B 之 label 來源／是否禁選 |

---

## 必查涵蓋面（brief 六項）

**1. 全棧三欄稽核**（獨立盤點，不限事件型）

| 能力 | 後端 | 前端 UI | wiring | 判定 |
|---|---|---|---|---|
| 六維度契約（Phase 7） | ✅ 契約＋validator | ❌ 無控制項 | ❌ `page.tsx` 未傳 opts | Phase 7 Task 已列；**閘不足**（P0-02） |
| IC 分析頁事件批設定揭露 | ✅ 匯入列有欄位 | ⚠️ `EventTablesPanel` 只顯示 analyze manifest 之 entry/k | ❌ picker 不傳 metadata | **缺口**（P1-01） |
| Feature Library run 日期覆蓋 | ✅ manifest 有 `time_range` | ❌ `RunInfo` 無欄位 | ❌ IC 選 run 無交集檢查 | **缺口**（P1-02） |
| 案例搜尋 `/search` 匯出 | ✅ `buildEventContractRecords` | ⚠️ opts 介面部分 | ❌ 呼叫端未傳 | Phase 7 已列 |
| D-7 lookahead registry | ❌ 未實作 | — | — | Task 1.10 已寫（待做） |

**2–3. R3 十八條／D–G** — 見上表。

**4. §C0 遵守** — 檔頭四條遺留**正確**標為 R4 裁定、未降級 §N；§C0 L229-234 禁止數值正確性殘留放行。**違規點**：Task 6.0 驗證為空殼 placeholder（P2-01），與「每 Task 可執行驗證」衝突。

**5. §P 38 Task 五欄** — `grep -c "^- 覆蓋風險"`＝38＝Task 數；`覆蓋風險：無`＝0（主委改寫已入 SPEC）。抽樣 Task 1.10／2.2／7.1 之覆蓋風險欄含實質同步義務，**非形式填空**。殘留空殼：**Task 6.0 驗證 `python3 -c "..."`**（P2-01）。

**6. Verdict** — 見文末。

---

## §1 必查十一類摘要

| # | 結果 |
|---|---|
| 1 矛盾/互斥 | Task 7.1/7.2 vs `control_kind` accepted 子集（P0-01）；Task 2.2 依賴未定義 G-2 serialization（P1-03） |
| 2 漏項/E2E | IC 頁／FL time_range（P1-01/02）；六維度 round-trip（P0-02） |
| 3 不可測驗收 | G-2 oracle 未定（P1-03）；Task 6.0 驗證 placeholder（P2-01） |
| 4 quant 假設 | scenario A/B label 語意漂移（P1-04） |
| 5–11 | 其餘無新增 BLOCKING |

---

## COMPOSER-R4-P0-01

**斷言**: Task 7.1 與 Task 7.2 要求「UI 選項數 `==` 契約 `enum` 元素數」，但 `control_kind` 契約 `enum` 含 4 值、`accepted` 僅 3 值（`platform_random_bars` 恆拒）；照字面實作要麼 UI 暴露必拒值、要麼 enum 數不一致而機械閘必紅，斷言基準未定義。

**碼證**: Task 7.1 L787-788、Task 7.2 L799-803；`python3 handoffs/20260822-gap3ux-x-review-r4-dims.py --counts` → `control_kind enum_len=4 accepted_len=3`；契約 `event_import_contract.json` L43-48。RECHECK：比對 SPEC Task 7.1/7.2 驗收句 vs dims.py 輸出。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2

[BLOCKING] 信心度=High。失敗：Agent 實作 7.2 時在 enum 全集與 accepted 子集間無法同時滿足 SPEC 與契約。修法：7.1/7.2 明寫比對 `accepted`（或 `enum` 減 `rejected_with_reason` 鍵），UI 對恆拒值顯示 disabled＋契約 doc，且**不計入**可選集合。

---

## COMPOSER-R4-P0-02

**斷言**: Task 7.2／V-11 只驗「契約 enum 集合＝UI 選項集合」，不驗選值綁定到 `buildEventContractRecords` 產出；`EventExportOptions` 缺 `controlKind`／`labelReturnMode`／`decisionOffsetBars`／`counterexampleKind`，現碼仍寫死四欄；disabled 選項可湊齊集合而 payload 未變——重現 B5「介面有、沒傳」病因。

**碼證**: Task 7.2 L799-813；V-11 L870；`eventExport.ts:9-17,92-104`；`page.tsx:522-527`；facts.sh F-06/F-07。RECHECK：`npx vitest run contractEnumWiring` 設計審計——若無「選非預設 ⇒ records[0].<field>===選值」則不足。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；frontend/src/lib/eventExport.ts#b2024ac8970f

[BLOCKING] 信心度=High。失敗：機械閘全綠但匯出仍走寫死預設。修法：每維度一條 round-trip vitest；`EventExportOptions` 補齊六維度；mutation 呼叫端漏傳 opts ⇒ 紅。

---

## COMPOSER-R4-P1-01

**斷言**: Phase 7 全棧接線僅涵蓋 `/search` 與 `/data-preparation`，未要求 IC 分析頁在事件模式下選匯入批後揭露該批契約設定（`scenario`／`control_kind`／`label_return_mode` 等）；`EventImportPicker` 只回傳 t0 秒戳，使用者在不知批次語意下跑條件 IC。

**碼證**: Phase 7 前言 L751-777 盤點表未列 ic-analysis；`EventImportPicker.tsx:9,52` `onPick(importId, icTimestamps)`；`ICConfigPanel.tsx:274-278` 只更新 `event_import_id`／`event_timestamps`；`EventTablesPanel.tsx:118-120` 僅顯示 analyze 回傳 manifest 之 entry/k（非匯入契約全六維度）。RECHECK：讀上述三檔；檔頭遺留項 **E**。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；frontend/src/components/ic-analysis/EventImportPicker.tsx#1cb1e1562456

[MAJOR] 信心度=High。修法：新增 Task 7.6 或擴 Task 7.3 至 ic-analysis（選批後唯讀揭露與匯出面板同模板）。

---

## COMPOSER-R4-P1-02

**斷言**: Feature Library 之 `list_runs`／前端 `RunInfo` 未暴露 manifest `time_range`，IC 分析頁選 Feature run 時無法機械驗證「事件 t0 區間 ⊆ 特徵 run 覆蓋區間」，與 §N #8/#10 未答部分及檔頭遺留 **E** 同型。

**碼證**: `api/models/feature_factory_models.py` L116-133 `RunInfo` 無 `time_range`；`feature_reader.py` L455-472 manifest 含 `time_range`；`ICConfigPanel.tsx:199-226` 選 run 僅 symbol/tf/hash；facts.sh F-13 `grep time_range` 未命中 ic-analysis。RECHECK：`rg time_range frontend/src/components/ic-analysis` → 0。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；api/models/feature_factory_models.py#de451ac20681

[MAJOR] 信心度=High。修法：API 暴露 run `time_range`；事件模式選批後計算 t0 min/max 與 run 區間交集，不覆蓋則 fail-closed 或強警示（不需等大矩陣 GAP-6）。

---

## COMPOSER-R4-P1-03

**斷言**: G-2 仍未定義 canonical serialization（鍵序、omission vs NaN、sha256 欄位白名單），但 Task 2.2 L518-520 已要求「G-2 serialization 須涵蓋 `filters` 與六維度」——Agent 實作 Phase 2 與 Phase 7 會產出不同 golden bytes 且無仲裁規則。

**碼證**: §G L269-273 僅 sha256＋三項；Task 2.2 L518-520；§V G-2 L869；檔頭遺留 **F**。RECHECK：`rg -n "canonical serialization" docs/GAP3_EVENT_UX_SPEC.md` → 僅 Task 2.2 提及、無定義 Task。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2

[MAJOR] 信心度=High。修法：§G 增 serialization 小節或 Task 4.2 子項——鍵序、`filters` 空值、缺 bar omission policy、統計欄是否進 hash。

---

## COMPOSER-R4-P1-04

**斷言**: Task 7.1 將在 `/search` 接出 `scenario` UI，但 `buildEventContractRecords` 不因 A/B 改變 label 來源（仍 t0 `positive_case`＋`future_{h}bar_return`）；契約 doc 稱 A/B「事件在未來」，SPEC 未寫「search 路徑 scenario 僅 metadata」或禁止選 A/B，造成契約 scenario 與實際 label 語意漂移。

**碼證**: `eventExport.ts:75-77,95,102-104`；契約 `scenario` doc（facts.sh F-02）；Task 7.1 L783-797 無語意邊界；檔頭遺留 **G**。RECHECK：讀 `buildEventContractRecords`；D-7 表 L131-135。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2；frontend/src/lib/eventExport.ts#b2024ac8970f

[MAJOR] 信心度=High。修法：Task 7.1「邊界」明寫 search 路徑僅 C／two_stage 可選，或 A/B 須改 label 組裝並加 vitest。

---

## COMPOSER-R4-P2-01

**斷言**: Task 6.0 之驗證欄寫 `python3 -c "..."` 為不可執行 placeholder，屬 §2 獵空殼——Agent 無機械命令可跑，與 §V「每 Task 可證偽」紀律衝突。

**碼證**: Task 6.0 L696「驗證：`python3 -c "..."` 斷言該 reason 存在於登記檔」；同 Task 其他欄（內容／存活至）有實質。RECHECK：`nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '693,700p'`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#3bc04411cdf2

[MINOR] 信心度=High。修法：替換為完整 `python3 -c "import json;…assert 'feature_count_exceeds_cap' in …"` 與登記檔路徑。

---

## Verdict：需修訂後定版

R3→R4 修復面：**實質進步**——D-7 三層（Task 1.10/1.11/1.12＋2.1b）、Task 4.1b 動態揭露、future72 TF 換算、38 條覆蓋風險改寫均已入 SPEC；R3 十八條中 **11 條可標 CLOSED**。

**尚不可 FROZEN**（§C0：正確性類不得殘留放行）：**D** Task 7.1/7.2 enum 基準與 round-trip（P0-01/02）；**E** IC 頁＋FL `time_range`（P1-01/02）；**F** G-2 serialization（P1-03）；**G** scenario A/B 語意邊界（P1-04）。P2-01 應同輪補齊但不單獨擋定版。

---

ASSUMPTIONS_VERIFIED: sha256=3bc04411cdf2…/900 行；facts.sh 14 條 rc=0（與 facts.out 除 HEAD 外一致）；dims.py 六維度路徑／計數；契約 reason 長度 15/14/3/1/1/2；eventExport 寫死五處；page.tsx 未傳 opts；RunInfo 無 time_range  
TESTS_RUN: `bash handoffs/20260822-gap3ux-x-review-r4-facts.sh` → rc=0；`python3 handoffs/20260822-gap3ux-x-review-r4-dims.py{,--counts}` → rc=0；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_SPEC.md` → rc=0；`bash scripts/completeness_check.sh --single handoffs/20260822-gap3ux-x-review-r4-composer.md --family composer`（交件前）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none  
產出: handoffs/20260822-gap3ux-x-review-r4-composer.md

STATUS: DONE
