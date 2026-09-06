# 掃描結果瀏覽器（小型帶）— SPEC

**票**：`SCANCUBE`　**起草**：Claude　**日期**：2026-09-07
**上游**：`docs/GAP3_EVENT_DISCLOSURE_SPEC.md`（已收案）之 UAT B22；使用者 2026-09-06 裁定。

**使用者原話（逐字，不得改寫）**：
> 「不論IC分析是有幾種參數組合計算出來，不同參數組合計算出來的每個特徵的每個數據，
> 在前端每個數據表格和圖像，都要能讓使用者能看到分析，無法一次呈現所有數據，
> 也要有方式可以讓使者選擇要如何呈現和篩選」

**本票範圍裁定（使用者 2026-09-06）**：「現在的目標就先以**小型帶**可以完整呈現我的要求」
⇒ 目標規模＝**數百特徵內**；超出上限一律 **fail-closed 明講**，不得靜默截斷。

---

## §RISK 風險分級

- RISK-HIT: a,b,d
  - (a) 數值/資料品質：立方體是使用者用來比較參數組合的**唯一**數據來源；錯一格＝錯結論。
  - (b) 跨模組/共用路徑：動 `ICFilterOrchestrator` 之落檔行為與 `ic_analysis_service` 之掃描迴圈。
  - (d) ML/回測正確性：跨 (k,h) 比較 IC 的語意本身有陷阱（見 §C-4），呈現方式必須擋住錯誤解讀。

---

## §A 假設與待使用者確認

- **實跑事實（附 receipt）**
  - `FACT-RECEIPT`：`venv/bin/python handoffs/20260906-probe-scan-overwrite.py` → rc=0；
    4 組不同 `(k,h)` → **相異落檔路徑數＝1**（`data_cache/features/ETHUSDT_12h_filtered.h5`）；
    連寫兩格後檔內只剩 `feat_2_3`，第一格 `feat_0_1` 已被覆蓋。（Claude 實跑 2026-09-06）
  - `FACT-RECEIPT`：`venv/bin/python handoffs/20260907-probe-cube-size.py` → 單列 `summary_table`
    JSON ＝ **553 bytes**（15 欄、特徵名 28 字元）；110 格 × 500 特徵 ＝ **29.0 MB**；
    110 格 × 1000 特徵 ＝ 58.0 MB。（Claude 實跑 2026-09-07）
  - `FACT-RECEIPT`：立方體之指標軸＝`ICFilterOrchestrator._build_summary_table`
    之 14 欄 ＋ `_annotate_root_status_and_pass_class` 補的 `pass_class`
    （`momentum/Analysis/ic_filter_orchestrator.py:3777-3824`）。（Claude 讀碼 2026-09-07）
  - `FACT-RECEIPT`：掃描格逐格 `await`（循序），但逾時之格之 thread **仍會跑完**
    —— `api/services/ic_analysis_service.py:_run_scan_grid` docstring 自陳。（Claude 讀碼 2026-09-07）

  - `FACT-RECEIPT`：`venv/bin/python handoffs/20260907-probe-report-sections.py` → rc=0。
    讀**真實**報告 `data_cache/reports/ic_report_ic_gatekeeper.json`（558,966 bytes／15 特徵）：
    `rolling_ic_series` 298,958 B（53.5%、19,931 B/特徵）、`turnover_analysis` 158,335 B
    （28.3%、10,556 B/特徵）、`quantile_returns` 74,075 B（13.3%、4,938 B/特徵）、
    `summary_table` 6,942 B（1.2%、**463 B/特徵**）、`ic_decay` 6,047 B。
    **per-feature 諸節合計 552,123 B ／ 15 ＝ 36,808 B/特徵**
    ⇒ 全節保存於 110 格 × 300 特徵 ＝ **1,158 MB**。（Claude 實跑 2026-09-07）

- **R1 裁決（三家 adversarial 之結果，非本人推論）**
  - 🔴 `ASSUME-2`：**已推翻**（`CODEX-R1-P0-01`／`COMPOSER-R1-P0-01`／`GROK-R1-P0-01` 三家獨立命中）。
    `summary_table` 只是投影；使用者原話含「表格**和圖像**」，而 IC 頁圖表讀的是
    `quantile_returns`／`rolling_ic_series`／`ic_decay`（`page.tsx:792-833`）。
    **裁決＝納入既有節之原樣切片，但依實測分兩層**（見 §C-7）。
  - 🔴 `ASSUME-1`：**已推翻**（`CODEX-R1-P1-04`／`COMPOSER-R1-P1-02`／`GROK-R1-P2-02` 三家獨立命中）。
    `filtered_features.h5` **有**下游消費者：`ic_analysis_service.py:1538-1579` 之 export 解析
    穩定路徑並以 `assert_filtered_export_fresh`（`ic_reporter.py:271-305`）比對
    `filtered_generated_at`／`filtered_source_task_id`。
    **但修法方向不變且更被強化**：掃描格寫進去會讓 export 拿到某一格的殘骸並冒充主分析產物
    ⇒ 停寫是正確的；驗證判準隨之升級（見 Task 1.1）。

- **仍未驗（請 R2 攻）**
  - `ASSUME-3`：`correlation_matrix` 之 O(N²) 縮放。本次量到的該節只有 **27 bytes**（該 run 為空）
    ⇒ **沒有**真實縮放數據；排除它的理由是讀碼（per-pair 非 per-feature）與 GAP-6 之既有登記。
    否證觀測＝存在一份 `correlation_matrix` 非空的真實報告，其大小與 N² 不符。

- **待使用者確認**：無（範圍已由 2026-09-06 裁定；技術決策依 CLAUDE.md 走委員會不問使用者）。

---

## §C 約束

1. **不得改變任何 IC 數值**。本票只做「保存 ＋ 呈現」，不新增、不重算任何統計量。
   引用：`CLAUDE.md` §Data Truth、`docs/TEST_DESIGN_CHARTER.md`。
2. **漏斗（粗篩/細篩）不在本票**。使用者 2026-07-16 裁定「IC Analysis 完善之後才定義」。
   本票**不得**引入任何自動淘汰特徵的機制。
3. **GAP-6（430K 規模）不在本票**。本票之上限是 fail-closed 的閘，不是規模解法。
4. 🔴 **跨 (k,h) 比較之語意限制**（本票之呈現規則，非建議）：
   - 不同 `h` ＝ **不同的問題**（答案窗長度不同）⇒ 其 IC **不可直接比大小**。
   - 跨格取 max（如「最強的那格」）是**向上偏誤估計量**，偏誤隨格數增加。
   ⇒ 介面**不得**提供「自動選最佳格」或任何跨格排名的預設視圖；
     跨 `h` 的並列必須在畫面上標示該限制。
5. **不得為了呈現而在後端算新指標**（例如跨格平均、排名分數）——那是第二份真相源。
6. 上限值一律住**契約**（`event_import_contract.json` 之 `analysis_params`），前端與後端皆不硬編。
   🔴 既有 schema 為 `{type, min, example_default, doc}`；`pipeline.py:412-431` 對**非 dict** 之 spec
   直接 `continue` ⇒ 新鍵必須照該 schema 寫，否則 loader 靜默略過（`CODEX-R1-P1-03`）。
7. 🔴 **兩層保存（R1 P0 之裁決）**：
   - **Tier A（恆存）**＝`summary_table`。463 B/特徵 ⇒ 110 格 × 500 特徵 ≒ **25 MB**。
   - **Tier B（圖表節，預算內才存）**＝`ic_decay`／`quantile_returns`／`rolling_ic_series`／
     `grouped_ic`／`turnover_analysis`／`coverage_analysis`／`marginal_ic`。36,808 B/特徵。
     以位元組預算 fail-closed；超出 ⇒ **一格都不存 Tier B**（Tier A 不受影響），
     畫面明講原因並列出實際數字與「縮小到幾格 × 幾特徵就存得下」。
   - **`correlation_matrix` 具名排除**：per-**pair** 非 per-feature，GAP-6 已登記其無 cap。
     畫面須明講「這一節不在瀏覽器內」，不得靜默省略。
8. 🔴 **本票不解決 OOM，且不得被讀成解決了**（`CODEX-R1-P1-05`／`COMPOSER-R1-P1-01`）。
   所有 cap 限制的是**落檔位元組**，不是 `analyzer.analyze()` 的計算峰值記憶體。
   掃描本身仍可能在寫任何檔案之前就 OOM。此為具名殘留，見 §N。

---

## §G Golden / Baseline

- **Baseline-1（行為不變）**：本票**不得**改變單次（非掃描）分析之 `filtered_features` 落檔。
  對照＝非掃描分析之落檔 sha256 與改動前一致。
- **Baseline-2（既有 golden 不動）**：`scripts/gap3_label_golden.py --check` 之 46＋2 案例
  逐位元組不變（本票不碰標籤計算）。
- **Golden-3（新增，Tier A）**：固定一組 `(k,h)×feature×metric` 之 Tier A 立方體 JSON，
  凍結為 golden；任何改動欄集、順序、NaN/null mask、序列化者會使其變動。
- **Golden-4（新增，Tier B）**：同一組之 Tier B 圖表節 JSON 凍結為 golden。
  🔴 **Tier B 之 golden 必鎖「原樣」**：`sections[x] == report[x]` 之全等關係，
  任何抽樣、四捨五入、欄位裁剪都會使其變動（`CODEX-R1-P0-01` 要求以 golden 鎖全量保存形狀）。

---

## §P Phase 與依賴

| Phase | 內容 | 依賴 |
|---|---|---|
| **P1** | 修落檔覆蓋：掃描格 `_suppress_persist=True` | 無 |
| **P2** | 立方體落檔（Task 2.0 契約／2.1 兩層寫入／2.2 保留上限／**2.3 掃描迴圈接線**） | P1 |
| **P3** | 查詢 API：分頁／篩選／排序 ＋ 圖表節端點 | P2 |
| **P4** | 前端瀏覽器：**兩個表格視圖 ＋ 圖表視圖** ＋ 篩選 | P3 |
| **P5** | 白話驗收清單 ＋ 實機驗證步驟 | P4 |

🔴 **P1 必須先於 P2**：若先加 per-cell 落檔而不停掉共用路徑的寫入，
逾時 thread 仍會競寫共用檔，且會多出「兩份都在寫」的中間態。

---

## 逐項 Task 明細

### Task 1.1 — 掃描格不得寫共用落檔（`P1`）

- **目標**：消除 110 格覆蓋同一個 `filtered_features.h5`，以及逾時 thread 之並行寫競態。
- **修法**：`_run_scan_cell` 建立 analyzer 後、呼叫 `analyze()` 前設 `analyzer._suppress_persist = True`。
  🔴 **理由（為何不是「路徑帶 k/h」）**：掃描格是**研究掃描**，不是決策產物；
  `filtered_features.h5` 是 survivor artifact，有 export 等下游消費者。
  寫 110 份競爭性 artifact 比覆蓋更糟（下游無從知道該讀哪一份）。
  停寫同時消滅覆蓋與競態；每格的**數據**改由 Task 2.1 之立方體保存。
- **輸入／輸出**：無新輸入；輸出＝掃描期間 `data_cache/features/` 之檔案內容與 mtime 不變。
- **驗證（可證偽）** — `tests/api/test_scan_cube.py`：
  - `ASSERT venv/bin/python -m pytest tests/api/test_scan_cube.py -q -k no_shared_persist THEN rc=0`
  - 🔴 **三重判準**（`CODEX-R1-P1-04`／`COMPOSER-R1-P1-02`／`GROK-R1-P2-02`：
    mtime 相等**不足**——stale artifact 的 mtime 本來就不會變）：
    1. `ICReporter.save_filtered_features` 之 spy `call_count == 0`（證明「呼叫沒發生」，不是「結果沒變」）；
    2. 掃描前後該 h5 之 **content sha256 與 attrs**（`filtered_generated_at`／
       `filtered_source_task_id`）皆相同；
    3. 掃描**之後**跑主分析，`GET /api/v1/ic/export/{task_id}` 回 200 且
       `assert_filtered_export_fresh` 通過，provenance 指向**主分析**之 task_id。
  - mutation `S1`：把 `_suppress_persist = True` 改回 `False` ⇒ 上述測試必須紅。
- **邊界**：
  1. 掃描格**逾時**：被遺棄之 thread 跑完時亦不得寫（`_suppress_persist` 綁在該格自己的
     analyzer 實例上，且該實例只有那個 thread 持有 ⇒ 天然成立；測試以「逾時後檔案仍未變」釘住）。
  2. 掃描之後**主分析**照常寫（本票不改主分析）——斷言主分析後落檔有變。
- **存活至**：永久（缺陷修復，非階段性鷹架）。
- **覆蓋風險**：無。Task 2.1 寫的是**另一條路徑**（`data_cache/ic_scan_cubes/`），不碰本路徑。
- **不可做**：不得改 `_resolve_filtered_path` 之路徑組成（那會改變非掃描路徑之落檔位置，
  是 Baseline-1 明文禁止的行為變更）。

### Task 2.1 — 每格 `summary_table` 落檔（`P2`）

- **目標**：使用者要看的「每個組合 × 每個特徵 × 每個數據」實際被保存，不再算完就丟。
- **輸入**：`_run_scan_cell` 內的 `report`（真實分析報告）。
- **輸出（兩層；R1 P0 之裁決，見 §C-7）**：`data_cache/ic_scan_cubes/<task_id>/`
  - `manifest.json`：`{task_id, symbol, timeframe, created_at, k_axis, h_axis, metrics,
    chart_sections, cells:[{k,h,capability,reason,n_events,rows,path,chart_path}],
    tier_a:{truncated,reason,requested_rows,max_rows},
    tier_b:{stored,truncated,reason,requested_bytes,max_bytes,fits_hint}}`
  - **Tier A** 每格 `cell_k<k>_h<h>.json`：
    `{k, h, analysis_status, oos_guarantees, n_events, rows:[<summary_table 逐列原樣>]}`
  - **Tier B** 每格 `charts_k<k>_h<h>.json`：
    `{k, h, sections:{<節名>: <report[節名] 原樣>}}`，節名限 §C-7 之七節。
  🔴 **逐列/逐節原樣**：`rows` 之欄集**等於** `summary_table`；`sections[x]` **等於**
  `report[x]`（`==` 全等，不是子集）。一欄不增、一欄不減、不改名、不重算、不重新排序。
- **fail-closed 上限（三個閘，各自獨立）**：契約新增（schema 照 §C-6 之
  `{type,min,example_default,doc}`）
  1. `scan_cube_max_rows`（**120000**；Tier A 總列數。依 §A 之 463 B/列 ⇒ ≒55 MB。
     初值由 60000 上調，因 110×500＝55000 已逼近舊值而誤擋合法小型帶——`GROK-R1-P2-01`）
  2. `scan_cube_max_rows_per_cell`（**5000**；單格列數。防「1 格 × 60000 特徵」之單檔巨大——`COMPOSER-R1-P1-01`）
  3. `scan_cube_chart_max_bytes`（**209715200**＝200 MB；Tier B 之估計位元組總量。
     估計式＝`Σ 每格列數 × chart_bytes_per_feature`，其中 `chart_bytes_per_feature`
     由**本次 run 之第一個非空格實測**得出，不用寫死常數）
  - Tier A 任一閘超過 ⇒ **不寫任何 Tier A 檔**，`tier_a.truncated=true`。
  - Tier B 超過 ⇒ **不寫任何 Tier B 檔**，`tier_b.truncated=true` 且
    `fits_hint` 給出「幾格 × 幾特徵可存下」之具體數字。**Tier A 不受影響**。
  - **禁止部分保存**（部分保存＝使用者不知道少了什麼）。
- **驗證（可證偽）** — `tests/api/test_scan_cube.py`：
  - `ASSERT venv/bin/python -m pytest tests/api/test_scan_cube.py -q THEN rc=0`
  - 逐列原樣：斷言 `rows[i] == report["summary_table"][i]`（逐 dict 相等，不是子集）。
  - 上限：構造 `requested_rows = max_rows + 1` ⇒ 斷言**零個 cell 檔被寫出**且 `truncated is True`。
  - Golden-3：凍結一份立方體，`--check` 逐位元組。
  - mutation：①把 `rows` 改成只留 3 欄 ⇒ 原樣測試紅；②把上限分支改成部分保存 ⇒ 上限測試紅。
- **邊界**：
  1. 某格 `capability=unavailable`（逾時／不可行）⇒ 該格**不寫 cell 檔**，manifest 之該筆
     `rows=0` 且帶 `reason`。**不得**寫一個空 rows 的檔冒充有資料。
  2. `summary_table` 為空（特徵全被濾掉）⇒ 寫 `rows: []`，與「不可用」**分開**（`capability=available`）。
- **存活至**：永久。
- **覆蓋風險**：無覆蓋。`start_analysis` 每次 `uuid.uuid4()`
  （`api/services/ic_analysis_service.py:1046`）⇒ **每次分析都是新目錄，不存在「重跑同 id」路徑**
  （`GROK-R1-P2-03` 更正我原本的錯誤敘述）。目錄累積由 Task 2.2 之保留上限處理。
- **不可做**：不得在此計算任何新統計量；不得排序（排序是查詢層的事，落檔保持產生順序）。

### Task 2.2 — 立方體目錄之保留上限（`P2`）

- **目標**：不讓 `data_cache/ic_scan_cubes/` 無限長大。
- **修法**：寫入新 task 之前，把既有目錄修剪到 **`keep - 1`** 個
  （語意＝「寫完之後恰為 `keep`」），依 `created_at` 由舊到新刪除超出者；
  刪除以**整個 task 目錄**為單位（`shutil.rmtree`，非 `os.remove`）。
  🔴 `CODEX-R1-P1-06`：原本寫「目錄數 > keep 才刪」，在**恰好 20 個**時不刪、寫完變 21，
  與驗收「寫第 21 個後只剩 20」直接矛盾。
  🔴 **原子性**：先寫 temp dir 再 `os.replace` 成正式名，避免並行時看到半成品。
- **驗證**：`keep=20` 且已有 20 個目錄 ⇒ 寫第 21 個後 `len(list(root.iterdir())) == 20`，
  且**被刪的恰是最舊那一個**（逐名對照，不是只比數量）。
- **邊界**：①目錄含非預期檔案 ⇒ 只刪整個 task 目錄，不逐檔挑；
  ②刪除失敗（`OSError`）⇒ log warning 但**不擋**寫入（清理失敗不該讓分析失敗）；
  ③並行兩個 build ⇒ 各自 temp dir ＋ rename，不得出現半寫入之目錄被讀到。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得刪 `data_cache` 下任何非 `ic_scan_cubes/` 的東西。

### Task 3.1 — 立方體查詢 API（`P3`）

- **端點**（🔴 prefix 為 `/api/v1/ic`——現有 router `api/routes/ic_analysis.py:33`，
  前端 base `frontend/src/lib/api.ts:7` 為 `/api/v1`。`CODEX-R1-P1-07` 指出我原寫的
  `/api/ic-analysis/...` 會 404）：
  - `GET /api/v1/ic/scan-cube/{task_id}/manifest` → manifest 原樣。
  - `GET /api/v1/ic/scan-cube/{task_id}/rows` → Tier A 分頁查詢。
  - `GET /api/v1/ic/scan-cube/{task_id}/charts?k=&h=&feature=` → Tier B **單格單特徵**之
    圖表節原樣（**不分頁**：一個 feature-cell ≒ 36 KB，屬單次可回之量）。
    Tier B 未保存 ⇒ **409** ＋ `tier_b.reason` 與 `fits_hint`。
- **查詢參數**：`k`（可重複）、`h`（可重複）、`feature`（子字串，大小寫不敏感）、
  `metric`（可重複；限定 manifest.metrics 之子集）、`sort`（`<metric>:asc|desc`）、
  `offset`、`limit`（上限 `analysis_params.scan_cube_page_max`，初值 **500**）。
- **回應**：`{total, offset, limit, rows:[{k,h,feature_name,<metrics…>}]}`
- 🔴 **`total` 是篩選後的真實總數**，不是本頁筆數；前端據它顯示「共 N 筆，正在看第 X–Y 筆」。
- **驗證（可證偽）** — `tests/api/test_scan_cube_api.py`：
  - `ASSERT venv/bin/python -m pytest tests/api/test_scan_cube_api.py -q THEN rc=0`
  - 分頁不重不漏：`limit=7` 逐頁取完，斷言聯集 == 全集且**無重複**（以 `(k,h,feature_name)` 為鍵）。
  - 排序穩定：同值列之相對順序跨頁不變（以 `(k,h,feature_name)` 為 tie-breaker）。
  - `metric` 白名單：請求不在 manifest.metrics 的名字 ⇒ **400**，不是靜默忽略。
  - `limit` 超過上限 ⇒ **400**，不是靜默夾住（靜默夾住會讓使用者以為看到全部）。
  - mutation：把 `total` 改成回本頁筆數 ⇒ 分頁測試紅。
- **邊界**：
  1. `task_id` 不存在／目錄被清掉 ⇒ **404** ＋ 明確 reason，不回空陣列
     （空陣列＝「沒有資料」，與「找不到」不同）。
  2. manifest `truncated=true` ⇒ `rows` 端點回 **409** ＋ reason，不回空頁。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得在 API 層做任何跨格聚合（§C-5）。

### Task 4.1 — 前端立方體瀏覽器（`P4`）

- **位置**：`/ic-analysis` 事件模式，掃描矩陣**下方**新區塊「掃描結果瀏覽器」。
- **三種視圖**（切換式，任一時刻只呈現一種）：
  1. **單格明細（含排序）**：選定 `(k,h)` ⇒ 該格的逐特徵表（全部指標欄），欄頭可排序。
     🔴 **只在單格內排序**，不跨格（跨格排名＝§C-4 禁止之偏誤）。
     `GROK-R1-P3-01`：原設計把「單格明細」與「單指標排行」分成兩個視圖，
     但 API 已有 `sort` 參數 ⇒ 合併，減少前端狀態面。
  2. **單特徵跨格**：選定 `feature` ＋ 一個 `metric` ⇒ `k × h` 矩陣。
     🔴 必須顯示 §C-4 之限制文字（不同 h 不可比大小），testid `ic-cube-cross-h-warning`。
  3. 🔴 **單格單特徵圖表**（R1 P0 之交付；使用者原話含「圖像」）：
     選定 `(k,h)` ＋ `feature` ⇒ 該 feature-cell 的圖表節。
     圖表型別**沿用主分析頁既有元件**（`page.tsx:792-833` 讀的同一批節），
     **不新寫圖表邏輯、不新算任何數值**。Tier B 未保存 ⇒ 顯示 `ic-cube-charts-not-stored`
     ＋ `fits_hint`，**不是**空圖。
     `correlation_matrix` 不在此（§C-7）⇒ 畫面須有 `ic-cube-corr-excluded` 明講。
- **篩選**：特徵名子字串、指標欄顯示/隱藏、k/h 多選。
- **規模**：資料一律走 Task 3.1 之分頁；前端**不得**一次抓全部。
- **驗證（可證偽）** — `scanCubeBrowser.test.tsx`：
  - `ASSERT cd frontend && npx vitest run scanCubeBrowser THEN rc=0`
  - 視圖 2 缺少限制文字 ⇒ 測試紅（DOM 斷言 `ic-cube-cross-h-warning`）。
  - `tier_a.truncated=true` ⇒ 顯示 `ic-cube-not-saved` 而**不是**空表。
  - `tier_b.truncated=true` ⇒ 顯示 `ic-cube-charts-not-stored` ＋ `fits_hint` 之數字，
    且**不發** charts 請求（斷言 fetch 未被呼叫）。
  - `correlation_matrix` 排除說明 `ic-cube-corr-excluded` 在場。
  - 分頁：`total=1200`、`limit=500` ⇒ 顯示「共 1200 筆，正在看 1–500」，且有下一頁。
  - mutation `S7`：刪限制文字 ⇒ 紅；`S8`：truncated 分支改 render 空表 ⇒ 紅；
    `S9`：刪 `ic-cube-corr-excluded` ⇒ 紅。
- **邊界**：
  1. 該次分析**沒有掃描**（單值模式）⇒ 整個區塊不顯示（不是顯示空表）。
  2. 某格 `capability=unavailable` ⇒ 視圖 1 選到它時顯示該格的 `reason`，不是空表。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得新增任何「推薦/最佳組合」提示（§C-4）。

### Task 5.1 — 白話驗收清單與實機驗證步驟（`P5`）

- **目標**：使用者能自己驗。
- **修改**：`白話說明/GAP-3驗收清單.md` 新增 **B26**（掃描結果瀏覽器）＋**B27**（落檔不再互相覆蓋）。
- **驗證**：`bash scripts/plain_docs_render.sh --check` rc=0。
- **邊界**：①B27 需要使用者能觀察到的現象（檔案 mtime 使用者看不到）⇒ 改以
  「掃描後匯出的檔仍是主分析那份」表述；②不得寫死任何門檻數字（門檻來自契約）。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得把 SPEC 的技術描述複製進白話（文件分層鐵律）。

---

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 含 a,d ⇒ **必附 mutation**。各 Task 之 mutation 已逐條列於上方；
  統一由 `handoffs/20260907-scancube-mutate.py` 執行（沿用揭露票之腳本紀律：
  還原權威＝版控、開場檢查 HEAD、逐條還原、對照組 `EXPECT_GREEN`）。
- **測試層級**：單元（落檔／上限／清理）、整合（掃描端到端不寫共用檔）、
  Golden 對照（Golden-3 立方體）、邊界（下表）。皆可獨立 `pytest tests/api/...` 跑，不需 `run_api.py`。
- **邊界目錄**（本票適用者）：
  - [x] 空 DF（`summary_table` 為 `[]`）→ Task 2.1 邊界 2
  - [x] 並發寫（逾時 thread）→ Task 1.1 邊界 1
  - [x] OOM 降載（列數上限 fail-closed）→ Task 2.1 上限
  - [ ] 全 NaN 列 / Inf / std=0 → N/A：本票不算任何數值，NaN 由上游 `_jsonable_scalar` 已處理
  - [ ] 重複·亂序 timestamp → N/A：本票不碰時間索引
  - [ ] API 重啟 → 立方體在磁碟上，重啟後可讀；「找不到」由 Task 3.1 邊界 1 涵蓋
  - [ ] 大尺度浮點 reduction → N/A：不做 reduction

---

## §R 回退

- Task 1.1／2.1／2.2 皆為新增或單行旗標，回退＝`git revert` 該 commit，無資料遷移。
- `data_cache/ic_scan_cubes/` 為純新增目錄，刪除即回到本票之前的狀態。
- 契約新增三個 `analysis_params` 鍵為**純新增**，舊 report 不受影響。

---

## §N N/A 登記

- **§A 待使用者確認＝無**：範圍已由使用者 2026-09-06 逐字裁定（小型帶），
  且 CLAUDE.md「技術決策委派委員會」明文不問使用者。
- **§V 之四項邊界標 N/A**，理由已逐條寫在 §V 邊界目錄內。

### 具名殘留（R1 之產物）

| 代號 | 內容 | 三值理由 | 接下來 |
|---|---|---|---|
| `SC-RESID-1` | **掃描本身之峰值記憶體（OOM）不在本票** | `blocked-by` | 需 tier-aware（8/16/24/32 GB）之實跑量測；本機只有 8 GB，且 `handoffs/run_receipts/gap3_scan_benchmark.json` 自陳條件 IC `not_measured`。併 GAP-6／IC-PERF |
| `SC-RESID-2` | `correlation_matrix` 不進立方體 | `blocked-by` | per-**pair** 非 per-feature，GAP-6 已登記其無 cap；本次實測該節為空（27 B）故**無真實 N² 數據**。GAP-6 處理後再議 |
| `SC-RESID-3` | Tier B 超預算時無「只存選定幾格」之選項 | `needs-research` | 「讓使用者選哪幾格要圖表」需要一輪互動設計（選格 → 重跑 or 事後補存），本票先做 fail-closed ＋ `fits_hint` |

🔴 三條皆**不得**被讀成「已解決」。`SC-RESID-1` 尤其：本票所有 cap 限制的是**落檔位元組**，
掃描仍可能在寫任何檔案之前就 OOM（§C-8）。
