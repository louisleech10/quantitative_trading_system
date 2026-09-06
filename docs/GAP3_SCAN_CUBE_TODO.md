# 掃描結果瀏覽器（小型帶）— TODO

**SPEC**：`docs/GAP3_SCAN_CUBE_SPEC.md`　**票**：`SCANCUBE`　**日期**：2026-09-07

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

- **解耦**：`momentum/` 不得 import `api/`（R1）；新 API 路由住 `api/routes/ic_analysis.py`，
  service 不得互相 import（R4）。立方體讀寫之純函式住 `momentum/Analysis/scan_cube.py`，
  由 `api/services/ic_analysis_service.py` 呼叫——**不得**讓 `momentum/` 反向依賴 service。
- **Logging**：`get_logger(__name__)`；逐格迴圈內**不得** log（hot loop）。
- **Error 分類**：`task_id` 不存在＝non-retryable（404）；磁碟寫入失敗＝non-retryable（loud）。
- **不可違反原則**：不得改變任何 IC 數值（SPEC §C-1）；不得引入淘汰特徵之機制（§C-2）；
  不得在後端算新指標（§C-5）；上限一律讀契約（§C-6）。
- **防假綠**：不得放寬既有測試斷言。既有紅（非本票造成）：
  `tests/api/test_ichc_event_timestamps.py::…kwarg`（掃原始碼字串之弱測試）、
  `tests/api/…ic_la1…` 2 條（測試間污染，單檔跑全過）——**不得**把它們算成本批結果。
- **manifest ID 引用**：`[A-1]`＝SPEC §A `ASSUME-1`；`[A-2]`＝`ASSUME-2`。

---

## §B 批次執行策略

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B0** | 0.1 | 無 | scaffold：TODO 引用之五個 artifact 目前**全部不存在**（`CODEX-R1-P1-09`／`COMPOSER-R1-P1-03`），不先建 Phase Gate 跑不起來 | 小 |
| **B1** | 1.1 | B0 | 單行旗標＋測試，先把錯的寫停掉 | 小 |
| **B2** | 2.0, 2.1, 2.2, 2.3 | B1 | 同一個新模組 `scan_cube.py`，契約鍵與讀寫一起做才有意義 | 中 |
| **B3** | 3.1 | B2 | 需要 B2 的落檔格式定案 | 中 |
| **B4** | 4.1 | B3 | 需要 B3 的 API 契約 | 中 |
| **B5** | 5.1 | B4 | 白話須描述已完成的畫面 | 小 |

- **批次間 Gate**：前一批之 `pytest`／`vitest` 命令 rc=0，且 mutation 腳本對應條目為紅。

---

## Phase 0 — scaffold（完成後：Phase Gate 的每一條命令都跑得起來）

### Task 0.1 — 建立五個被引用但不存在的 artifact（`票 —`）

`票 —`：測試基礎設施，不對應單一 UAT 票；B26／B27 之 Phase Gate 皆依賴它。

- SPEC ref：§V　目標：消除「文件引用了不存在的檔案」這個可執行性缺口。
- 🔴 **出生事故**：`CODEX-R1-P1-09`／`COMPOSER-R1-P1-03` 實跑
  `for p in scripts/scan_cube_golden.py handoffs/20260907-scancube-mutate.py
  tests/api/test_scan_cube.py tests/api/test_scan_cube_api.py tests/golden/scan_cube;
  do test -e "$p" ...; done` → **五項全部 MISSING**，而 TODO 的 Phase Gate 卻要求它們 rc=0。
  「之後會有」不算通過。
- 輸入 / 輸出：無輸入；輸出＝五個 artifact 之骨架（可跑、但斷言為空或 skip）。
- 實作要點：
  1. `tests/api/test_scan_cube.py`、`tests/api/test_scan_cube_api.py`：
     建檔並各放一條 `test_scaffold_placeholder` 明確 `pytest.skip("Task N.x 尚未實作")`
     ——**skip 不是綠**，Phase Gate 逐 Task 檢查對應測試已從 skip 轉為實測。
  2. `scripts/scan_cube_golden.py`：沿用 `scripts/gap3_label_golden.py` 之 CLI 形狀
     （`--check <glob>`／`--write`），golden 內容鎖**列值、欄序、NaN/null mask、sha256**。
  3. `tests/golden/scan_cube/`：建目錄 ＋ `.gitkeep`。
  4. `handoffs/20260907-scancube-mutate.py`：沿用
     `handoffs/20260906-gap3-disclosure-mutate.py` 之紀律——
     還原權威＝版控（`git checkout --`）、開場檢查目標檔與 HEAD 一致否則 `exit 3`、
     每條跑完立即還原、對照組 `EXPECT_GREEN`。初版含 S1–S12 之**佔位登記**
     （`SKIP` 直到對應生產碼存在），不得為了湊數捏造。
- 修改檔案：新建上述五項。既有 caller：新建無。
- 路徑：
  - `tests/api/test_scan_cube.py`
  - `tests/api/test_scan_cube_api.py`
  - `scripts/scan_cube_golden.py`
  - `tests/golden/scan_cube/.gitkeep`
  - `handoffs/20260907-scancube-mutate.py`
- 不可做：**不得**讓 placeholder 測試 pass（那是假綠）——一律 `pytest.skip` 且訊息指名待做的 Task。
- 邊界：
  1. `scan_cube_golden.py --check` 對**空** glob ⇒ 明確報「找不到 golden」且 rc≠0
     （不是「0 個案例全過」——那是空迴圈假綠）。
  2. mutate 腳本在生產碼尚未存在時 ⇒ 該條印 `SKIP` 並計入「未涵蓋」，**不計入通過數**。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/api/test_scan_cube.py tests/api/test_scan_cube_api.py -q`
  rc=0（全 skip）；`venv/bin/python scripts/scan_cube_golden.py --check "tests/golden/scan_cube/*.json"`
  對空目錄 rc≠0；`venv/bin/python handoffs/20260907-scancube-mutate.py` rc=0 且輸出含 `SKIP`。
- **存活至**：永久（骨架逐 Task 被真實斷言取代，檔案本身保留）。
- **覆蓋風險**：後續 Task 會**覆寫** placeholder 測試——這是預期。
  Phase Gate 須逐 Task 確認對應測試已非 skip（見下方 Gate 條文）。

---

## Phase 1 — 停掉錯的落檔（完成後：掃描期間共用 h5 不再被動到）

### Task 1.1 — 掃描格 `_suppress_persist=True`（`票 B27`）

- SPEC ref：Task 1.1　目標：掃描格不寫共用 `filtered_features.h5`。
- 輸入 / 輸出：無新輸入；輸出＝掃描期間 `data_cache/features/` 內容與 mtime 不變。
- 實作要點：
  1. `ICAnalysisService._run_scan_cell` 內、`analyzer = analyzer_factory(cell_override)` 之**後**、
     `analyzer.analyze(...)` 之**前**插入：
     ```python
     # 🔴 SPEC Task 1.1：掃描格是研究掃描，不是決策產物 ⇒ 不寫 survivor artifact。
     #    實跑證明（handoffs/20260906-probe-scan-overwrite.py，rc=0）：
     #    `_resolve_filtered_path` 不含 k/h ⇒ N 格覆蓋同一檔、最後一格獲勝；
     #    且逾時之格的 thread 仍會跑完並寫同一路徑（並行寫競態）。
     analyzer._suppress_persist = True
     ```
  2. **不得**改 `ICFilterOrchestrator.__init__` 之預設值（那會影響非掃描路徑）。
  3. 確認 `_suppress_persist=True` 時 `analyze()` 仍**回傳完整 report**
     （讀 `ic_filter_orchestrator.py:3598` 之 else 分支：只跳過 persist，report 照建）。
- 修改檔案：`api/services/ic_analysis_service.py::ICAnalysisService._run_scan_cell`　
  既有 caller：`_run_scan_grid`（唯一），不需改。
- 路徑：
  - `api/services/ic_analysis_service.py`
  - `tests/api/test_scan_cube.py`
- 不可做：不得改 `_resolve_filtered_path`；不得改 `ICFilterOrchestrator` 之任何預設值；
  不得讓主分析（非掃描）跳過 persist。
- 邊界：
  1. **格逾時**：以 `per_cell_timeout` 極小值構造逾時，斷言逾時後 spy `call_count` 仍為 0
     （逾時之 thread 仍會跑完，這條測的是它跑完時也沒寫）。
  2. **掃描後主分析**：斷言主分析跑完後 spy `call_count >= 1` 且 export 端點 200
     （證明沒有誤殺主路徑）。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/api/test_scan_cube.py -q -k no_shared_persist` rc=0。
  🔴 **三重判準**（`CODEX-R1-P1-04`／`COMPOSER-R1-P1-02`／`GROK-R1-P2-02` 三家獨立指出
  「mtime 相等」不足——stale artifact 的 mtime 本來就不會變）：
  1. `monkeypatch` 對 `ICReporter.save_filtered_features` 裝 spy，斷言掃描期間 `call_count == 0`；
  2. 掃描前後該 h5 之 **content sha256** 與 attrs（`filtered_generated_at`／
     `filtered_source_task_id`）皆相同；
  3. 掃描**之後**跑主分析，`GET /api/v1/ic/export/{task_id}` 回 **200** 且
     `assert_filtered_export_fresh`（`momentum/Analysis/ic_reporter.py:271-305`）通過，
     provenance 之 `filtered_source_task_id` 指向**主分析**之 task_id。
  mutation `S1`：改回 `False` ⇒ 該測試紅。
- **存活至**：永久。
- **覆蓋風險**：無——Task 2.1 寫 `data_cache/ic_scan_cubes/`，不同路徑。

---

## Phase 2 — 立方體落檔（完成後：每格數據存在磁碟上，可被查詢）

### Task 2.0 — 契約新增**五個** `analysis_params` 鍵（`票 —`）

`票 —`：契約基線，不對應單一 UAT 票；B26／B27 皆依賴它。

- SPEC ref：§C-6　目標：上限值有單一來源，前後端皆不硬編。
- 輸入 / 輸出：輸入＝`momentum/Analysis/contracts/event_import_contract.json`；
  輸出＝該檔 `analysis_params` 多三鍵。
- 實作要點：
  1. 🔴 **必須沿用既有 schema** `{type, min, example_default, doc}`——
     `momentum/Analysis/event_samples/pipeline.py:412-431` 對**非 dict** 之 spec 直接 `continue`，
     寫成 `"scan_cube_max_rows": 60000` 這種裸整數會被**靜默略過**，
     隨後 `params["scan_cube_max_rows"]` KeyError（`CODEX-R1-P1-03` 實證）。範例：
     ```json
     "scan_cube_max_rows": {
       "type": "int", "min": 1, "example_default": 120000,
       "doc": "Tier A 立方體之總列數上限。依實測 463 bytes/列（handoffs/20260907-probe-report-sections.py）⇒ ≒55 MB。超過即整層 fail-closed 不寫。"
     }
     ```
  2. 五個新鍵：`scan_cube_max_rows`(120000)、`scan_cube_max_rows_per_cell`(5000)、
     `scan_cube_chart_max_bytes`(209715200)、`scan_cube_keep_tasks`(20)、`scan_cube_page_max`(500)。
  3. `analysis_params()` 之白名單同步；前端經**後端揭露**取值，不新增第二份常數。
  4. 載入時 fail-closed 驗 `int` 且 `> 0`（`min` 欄不會自動生效——需在 validator 內明確檢查）。
- 修改檔案：`momentum/Analysis/contracts/event_import_contract.json::analysis_params`；
  `api/services/ic_analysis_service.py::_event_analysis_params_disclosure`（若存在）。
  既有 caller：`create_event_sample_pipeline().analysis_params()`。
- 路徑：
  - `momentum/Analysis/contracts/event_import_contract.json`
  - `momentum/Analysis/event_samples/import_contract.py`
  - `tests/api/test_scan_cube.py`
- 不可做：不得改任何既有鍵之值（那會改變既有行為）。
- 邊界：
  1. 舊 report／舊事件批不帶新鍵 ⇒ 讀取端以契約值為準，不因缺鍵而炸。
  2. 三鍵之值為 0 或負 ⇒ 契約載入時即 raise（fail-closed，不是靜默當成無限）。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/api/test_scan_cube.py -q -k contract_params` rc=0。
  🔴 **跑真實 loader，不檢 JSON 字面**（`CODEX-R1-P1-03`）：
  斷言 `create_event_sample_pipeline().analysis_params()["scan_cube_max_rows"] == 120000`，
  五鍵皆存在、皆 `int`、皆 `> 0`；
  另以隔離之臨時契約放 `example_default=0` 與負值 ⇒ 斷言載入時 **raise**（非靜默通過）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.1 — 立方體寫入模組（`票 B26`）

- SPEC ref：Task 2.1　目標：每格之 Tier A（指標）與 Tier B（圖表節）逐列/逐節原樣落檔。
- 輸入 / 輸出：
  輸入＝`cells: list[dict]`（每筆含 `k, h, capability, reason, n_events, report`）、`task_id`、`root`、
  三個上限（`max_rows`／`max_rows_per_cell`／`chart_max_bytes`）。
  輸出＝`data_cache/ic_scan_cubes/<task_id>/{manifest.json, cell_k*.json, charts_k*.json}`；
  回傳 `manifest` dict。
- 實作要點：
  1. 純函式模組 `momentum/Analysis/scan_cube.py`，**不 import `api/`**：
     ```python
     CHART_SECTIONS = ("ic_decay", "quantile_returns", "rolling_ic_series",
                       "grouped_ic", "turnover_analysis", "coverage_analysis", "marginal_ic")

     def build_cube(task_id: str, symbol: str|None, timeframe: str|None,
                    cells: list[dict], *, max_rows: int, max_rows_per_cell: int,
                    chart_max_bytes: int,
                    root: Path = Path("data_cache/ic_scan_cubes")) -> dict:
         """回傳 manifest；已寫檔。兩層各自 fail-closed，Tier B 超限不影響 Tier A。"""
     ```
  2. **先算再決定寫不寫**（兩段式；Tier A 與 Tier B 各判各的）：
     ```python
     rows_per_cell = [len(c["report"].get("summary_table") or [])
                      if c.get("capability") == "available" else 0 for c in cells]
     total = sum(rows_per_cell)
     tier_a_ok = total <= max_rows and max(rows_per_cell or [0]) <= max_rows_per_cell
     # 🔴 Tier B：估計只作**預檢**與 fits_hint，判定一律看**實測累加**
     #    （`COMPOSER-R2-P1-02`／`GROK-R2-P1-02`／`CODEX-R2-P1-01` 三家獨立命中：
     #     composer 實測三份真實報告之 rolling_ic_series 為 3,225／19,931／26,637 B/特徵，
     #     差 8 倍——`_sample_rolling_series` 依序列長度抽樣，隨 h 與事件數變動。
     #     首格偏小 ⇒ 放行超量落盤；偏大 ⇒ 誤擋合法帶。）
     written_bytes = 0
     for c, n in zip(cells, rows_per_cell):
         if not n:
             continue
         payload = json.dumps({"k": c["k"], "h": c["h"],
                               "sections": {x: c["report"][x]
                                            for x in CHART_SECTIONS if x in c["report"]}},
                              ensure_ascii=False, sort_keys=False, separators=(",", ":"))
         written_bytes += len(payload.encode("utf-8"))   # ← 真正的 bytes，不是估計
         if written_bytes > chart_max_bytes:
             _remove_tier_b_temp(tmp)                    # 刪掉已寫的，一格都不留
             tier_b = {"stored": False, "truncated": True,
                       "reason": "scan_cube_chart_bytes_exceeded",
                       "requested_bytes": None,          # 已知「至少超過」，不謊報精確值
                       "max_bytes": chart_max_bytes,
                       "fits_hint": _fits_hint(written_bytes, n, chart_max_bytes)}
             break
         (tmp / f"charts_k{c['k']}_h{c['h']}.json").write_text(payload, encoding="utf-8")
     ```
     🔴 **RAM 上界＝一格**：逐格序列化、逐格累加，**不得**把全部格同時序列化
     （110 格 × 300 特徵 ＝ 1,158 MB）。
     🔴 Tier A 不 ok ⇒ **零個 `cell_*.json`**；Tier B 不 ok ⇒ **零個 `charts_*.json`**，
     且 `tier_b.fits_hint` 給出「幾格 × 幾特徵存得下」之具體數字。**兩者互不影響**。
     🔴 **路徑不變式**（`CODEX-R2-P1-02`／`COMPOSER-R2-P1-03`／`GROK-R2-P1-03` 三家獨立命中）：
     ```python
     # 路徑「只在該檔已成功提交之後」才填；未存之層一律 None
     assert tier_a["stored"] or all(c["path"] is None for c in manifest["cells"])
     assert tier_b["stored"] or all(c["chart_path"] is None for c in manifest["cells"])
     ```
     否則會出現「manifest 宣稱有圖、磁碟無檔」⇒ 前端照 `chart_path` 請求得 404，
     與 `stored=false` 雙重訊號矛盾。**前端與 API 一律只信 `stored`**。
  3. `metrics` 軸＝第一個 `available` 且 `rows` 非空之格的欄集**減去** `feature_name`；
     全部格皆空 ⇒ `metrics: []`（不發明欄名）。
     `chart_sections` 軸＝該格 report 中**實際存在**的 `CHART_SECTIONS` 子集（不列不存在的節）。
  4. 序列化一律 `json.dumps(..., ensure_ascii=False, sort_keys=False, separators=(",", ":"))`
     ——`sort_keys=False` 是為了保留原欄序（Golden-3／Golden-4 逐位元組）。
  5. 🔴 **`correlation_matrix` 不進 `CHART_SECTIONS`**（SPEC §C-7／`SC-RESID-2`）：
     它是 per-**pair** 非 per-feature。manifest 須帶 `excluded_sections: ["correlation_matrix"]`
     供前端明講，**不得靜默省略**。
- 修改檔案：新建 `momentum/Analysis/scan_cube.py::build_cube`／`::cell_filename`；
  `momentum/factories.py` 若採 factory 慣例則加 `create_scan_cube_writer()`。
  既有 caller：新建無（Task 2.3 接線）。
- 路徑：
  - `momentum/Analysis/scan_cube.py`
  - `tests/api/test_scan_cube.py`
  - `tests/golden/scan_cube/`
- 不可做：不得排序 `rows`；不得計算任何新統計量；不得對 `rows` 之值做任何轉換
  （NaN 已由上游 `_jsonable_scalar` 轉成 `null`）。
- 邊界：
  1. `capability != "available"` ⇒ 不寫該格 cell 檔，manifest 該筆 `rows=0` ＋ `reason` 原樣帶。
  2. `summary_table == []` 而 `capability == "available"` ⇒ **寫**一個 `rows: []` 的 cell 檔
     （與邊界 1 的「沒有檔」語意不同，測試須同時斷言兩者）。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/api/test_scan_cube.py -q` rc=0。通過條件：
  - Tier A 逐列原樣：`json.load(cell)["rows"][i] == report["summary_table"][i]`（dict 全等）。
  - Tier B 逐節原樣：`json.load(charts)["sections"][s] == report[s]` 對每個 `s` 全等。
  - Tier A 上限：`total = max_rows + 1` ⇒ `len(list(d.glob("cell_*.json"))) == 0` 且
    `tier_a["truncated"] is True`。
  - **per-cell 上限**：單格 `rows = max_rows_per_cell + 1` ⇒ 同樣零個 Tier A 檔。
  - **Tier B 獨立性**：Tier B 超限而 Tier A 未超 ⇒ `cell_*.json` **照寫**、`charts_*.json` 零個，
    且 `tier_b["fits_hint"]` 非空。
  - Golden-3／4：`venv/bin/python scripts/scan_cube_golden.py --check "tests/golden/scan_cube/*.json"` rc=0。
  - mutation `S2`：`rows` 只留 3 欄 ⇒ 原樣測試紅；`S3`：上限改成部分保存 ⇒ 上限測試紅；
    `S11`：Tier B 超限時連 Tier A 一起不寫 ⇒ 獨立性測試紅。
- **存活至**：永久。
- **覆蓋風險**：無覆蓋。`start_analysis` 每次 `uuid.uuid4()`
  （`api/services/ic_analysis_service.py:1046`）⇒ **每次分析都是新目錄**，
  不存在「重跑同 id 覆蓋」路徑（`GROK-R1-P2-03` 更正原敘述）。累積由 Task 2.2 處理。

### Task 2.2 — 目錄保留上限（`票 B26`）

- SPEC ref：Task 2.2　目標：`ic_scan_cubes/` 不無限長大。
- 輸入 / 輸出：輸入＝`root`、`keep`；輸出＝刪除超出之最舊 task 目錄。
- 實作要點：
  1. `def prune_cubes(root: Path, keep: int) -> list[str]`，回傳被刪的 task_id。
     🔴 **修剪到 `keep - 1`**，語意＝「寫完之後恰為 `keep`」。
     `CODEX-R1-P1-06`：原寫「目錄數 > keep 才刪」在恰好 20 個時不刪、寫完變 21，
     與驗收「寫第 21 個後只剩 20」直接矛盾。
     刪除用 `shutil.rmtree`（整個 task 目錄），**不是** `os.remove`。
  2. 🔴 **publish 之前置條件（Darwin 實測）**：`CODEX-R2-P1-04` 本輪實測
     `os.replace(src, dst)` 對**非空**目標 ⇒ `OSError: [Errno 66] Directory not empty`；
     empty/absent ⇒ succeeded。故偽碼必須是：
     ```python
     if final.exists():
         shutil.rmtree(final)      # ← 少這行在 Darwin 直接拋錯
     os.replace(tmp, final)        # tmp 與 final 須同一 filesystem
     ```
  3. 🔴 **prune + publish 須在同一把 root-level 檔案鎖內**：
     兩個並行 `build_cube` 各讀同一快照、各刪一個、各寫一個 ⇒ 最終 **21** 個目錄
     （`keep` 不變式被打破）。鎖用 `fcntl.flock` 於 `<root>/.lock`。
  2. 排序依據＝各目錄 `manifest.json` 之 `created_at`；**缺 manifest 或無法解析者排最舊**
     （壞掉的目錄優先清掉，且不因它而中止）。
  3. 於 `build_cube` **寫入前**呼叫；`OSError` 一律 `logger.warning` 後繼續（不擋分析）。
- 修改檔案：`momentum/Analysis/scan_cube.py::prune_cubes`（並由 `build_cube` 呼叫）。
  既有 caller：`build_cube`。
- 路徑：
  - `momentum/Analysis/scan_cube.py`
  - `tests/api/test_scan_cube.py`
- 不可做：不得刪 `data_cache/` 底下任何非 `ic_scan_cubes/` 之物；不得刪目錄內單檔（只刪整個 task 目錄）。
- 邊界：
  1. 某目錄缺 `manifest.json` ⇒ 視為最舊、優先刪，且不 raise。
  2. `shutil.rmtree` 失敗（權限）⇒ warning 後繼續寫新 cube，`build_cube` 仍回正常 manifest。
  3. **並行**兩個 `build_cube` ⇒ 各自寫 temp dir 再 `os.replace`，
     讀取端不得看到半寫入之目錄（`CODEX-R1-P1-06` 之原子性要求）。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/api/test_scan_cube.py -q -k prune` rc=0。通過條件：
  - 已有 **20** 個目錄（`created_at` 遞增）⇒ `build_cube` 寫第 21 個之後
    `len(list(root.iterdir())) == 20`，且**被刪的恰是 `task_00`**（逐名對照，不是只比數量）。
  - 缺 `manifest.json` 之目錄排最舊、優先被刪，且不 raise。
  - `shutil.rmtree` 拋 `OSError` ⇒ `build_cube` 仍回正常 manifest（不擋寫入）。
  mutation `S12`：把 `keep - 1` 改回 `keep` ⇒ 上述第一條紅。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.3 — 掃描迴圈接線（`票 B26`）

- SPEC ref：Task 2.1（接線部分）　目標：`_run_scan_grid` 跑完後真的寫出立方體。
- 輸入 / 輸出：輸入＝`_run_scan_cell` 之 `report`；輸出＝`scan` dict 多 `cube` 節。
- 實作要點：
  1. `_run_scan_cell` 之回傳值加 `"report": report`（**只在行程內傳遞，不進 HTTP 回應**）。
  2. `_run_scan_grid` 結尾**依序**做三件事，順序不可調換：
     ```python
     manifest = build_cube(...)                     # ① 寫檔（此時還需要 report）
     for c in results:                              # ② 🔴 立刻剝除
         c.pop("report", None)
     scan["cube"] = {k: manifest[k] for k in        # ③ 只放摘要
                     ("tier_a", "tier_b", "metrics", "chart_sections", "created_at")}
     ```
     🔴 `CODEX-R1-P1-02`／`GROK-R1-P1-01`（兩家獨立命中）：`_run_analysis` 把 `scan` 整包放進
     `info["event_label_scan"]`，而 `get_task_status`（`ic_analysis_service.py:1395-1404`）
     逐鍵放進 HTTP payload ⇒ **不剝除就會把 GB 級 report 推進 status API**。
     我原本只寫「不得進 HTTP」而沒寫剝除步驟，實作者照做必洩。
     🔴 `scan["cube"]` **不含 rows、不含 sections**（走 Task 3.1 的端點）。
  3. `build_cube` 拋例外 ⇒ `logger.error` ＋ `scan["cube"] = {"status":"failed","reason":str(exc)[:200]}`
     ——**掃描結果本身不因落檔失敗而消失**。
- 修改檔案：`api/services/ic_analysis_service.py::_run_scan_cell`（加 `report` 鍵）、
  `::_run_scan_grid`（結尾接線）。既有 caller：`_run_analysis`（讀 `scan`，不需改）。
- 路徑：
  - `api/services/ic_analysis_service.py`
  - `tests/api/test_scan_cube.py`
- 不可做：**不得**把 `report` 或 `rows` 放進 `task_info` 或 HTTP 回應（記憶體與頻寬）。
- 邊界：
  1. 所有格皆 `unavailable` ⇒ 仍寫 manifest（`cells` 皆 `rows=0`），不寫任何 cell 檔。
  2. `build_cube` 拋例外 ⇒ `scan["scan_results"]` 仍完整回傳（斷言格數不變）。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/api/test_scan_cube.py -q -k wiring` rc=0。通過條件：
  1. 2 格掃描後 `data_cache/ic_scan_cubes/<task_id>/` 有 1 個 manifest ＋ 2 個 Tier A cell 檔；
  2. 🔴 **負向斷言（遞迴）**：以 sentinel 值放進 report，呼叫 `GET /api/v1/ic/task/{task_id}`，
     遞迴走訪整個 response 斷言**不存在** `report`／`rows`／`sections` 鍵，且 sentinel 不出現；
  3. `scan["cube"]` 之鍵集恰為 `{tier_a, tier_b, metrics, chart_sections, created_at}`。
  mutation `S4`：刪掉 `scan["cube"]` 接線 ⇒ wiring 紅（防「元件做了沒接上」——本 epic 已踩三次）；
  `S10`：刪掉 `c.pop("report", None)` ⇒ 負向斷言紅。
- **存活至**：永久。
- **覆蓋風險**：無。

---

## Phase 3 — 查詢 API（完成後：前端能分頁取到任一切片）

### Task 3.1 — `scan-cube` 三個端點（`票 B26`）

- SPEC ref：Task 3.1　目標：分頁／篩選／排序，且 `total` 誠實；另供 Tier B 圖表節。
- 🔴 **prefix ＝ `/api/v1/ic`**（現有 router `api/routes/ic_analysis.py:33`、
  前端 base `frontend/src/lib/api.ts:7`）。`CODEX-R1-P1-07`：SPEC 原寫
  `/api/ic-analysis/...` 會 **404**，照它開發等於交付不了。三個端點：
  - `GET /api/v1/ic/scan-cube/{task_id}/manifest`
  - `GET /api/v1/ic/scan-cube/{task_id}/rows`（Tier A 分頁）
  - `GET /api/v1/ic/scan-cube/{task_id}/charts?k=&h=&feature=`（Tier B 單格單特徵，不分頁）
- 輸入 / 輸出：輸入＝query params；輸出＝`{total, offset, limit, rows}`
  ／`{k, h, feature_name, sections}`。
- 實作要點：
  1. 讀取層純函式住 `momentum/Analysis/scan_cube.py`：
     ```python
     def query_cube(root: Path, task_id: str, *, k: list[int]|None, h: list[int]|None,
                    feature: str|None, metrics: list[str]|None,
                    sort: tuple[str, str]|None, offset: int, limit: int) -> dict:
     ```
  2. 排序 tie-breaker **固定為** `(k, h, feature_name)`，否則跨頁會重複／漏（SPEC 驗證明列）。
     `None` 值一律排在末尾（升冪降冪皆然），因為「沒有值」不是「最小值」。
  3. 路由層只做參數驗證與錯誤碼映射：
     `metric` 不在 manifest.metrics ⇒ 400；`limit > page_max` ⇒ 400；
     找不到 task ⇒ 404；`tier_a.truncated` ⇒ rows 端點 409；
     `tier_b.truncated` ⇒ charts 端點 409（**rows 端點不受影響**，兩層獨立）。
- 修改檔案：`momentum/Analysis/scan_cube.py::query_cube`；
  `api/routes/ic_analysis.py::get_scan_cube_manifest`／`::get_scan_cube_rows`；
  `frontend/src/lib/api.ts::getScanCubeManifest`／`::getScanCubeRows`（Task 4.1 消費）。
  既有 caller：新建無。
- 路徑：
  - `momentum/Analysis/scan_cube.py`
  - `api/routes/ic_analysis.py`
  - `tests/api/test_scan_cube_api.py`
- 不可做：不得在 API 層做跨格聚合；不得靜默夾住 `limit`；不得把 404 與「結果為空」混為一談。
- 邊界：
  1. `offset` 超過 `total` ⇒ 回 `rows: []` 但 `total` 仍是真實總數（不是 404）。
  2. 排序欄位含 `None` ⇒ 該列排末尾，且 `asc`／`desc` 皆然（測試兩個方向）。
- 風險緩解：⊘
- 驗證：`venv/bin/python -m pytest tests/api/test_scan_cube_api.py -q` rc=0。通過條件：
  - 分頁不重不漏：`limit=7` 取完全部頁，`(k,h,feature_name)` 之聯集 == 全集且 `len(set) == len(list)`。
  - `total` 誠實：篩掉一半後 `total` 等於篩選後筆數（不是本頁 7）。
  - 錯誤碼：四種情境各斷言 `status_code` 為 400/400/404/409。
  - mutation `S5`：`total` 改回本頁筆數 ⇒ 分頁測試紅；`S6`：拿掉 tie-breaker ⇒ 不重不漏測試紅。
- **存活至**：永久。
- **覆蓋風險**：無。

---

## Phase 4 — 前端瀏覽器（完成後：使用者看得到每格每特徵每指標）

### Task 4.1 — `ScanCubeBrowser` 元件（`票 B26`）

- SPEC ref：Task 4.1　目標：三種視圖 ＋ 篩選 ＋ 分頁。
- 輸入 / 輸出：輸入＝`taskId`、`cube`（`scan.cube` 之摘要）；輸出＝畫面。
- 實作要點：
  1. `frontend/src/components/ic-analysis/ScanCubeBrowser.tsx`；
     由 `EventBatchDisclosurePanel` 在掃描矩陣**下方** render（`disclosure.event_label_scan.cube` 存在時）。
  2. 🔴 **`taskId` 之來源與傳遞鏈**（`COMPOSER-R1-P2-02`／`CODEX-R1-P1-07`：
     `EventBatchDisclosurePanel` 的 Props **沒有** `taskId`，不寫清楚實作者只能猜）：
     `useICAnalysisStore` 之 `taskId` → `page.tsx` 讀出 → 以新 prop `taskId?: string`
     傳入 `EventBatchDisclosurePanel` → 再傳入 `ScanCubeBrowser`。
     `taskId` 為 `undefined` ⇒ 整個區塊不 render（與「沒有掃描」同一分支）。
  3. 視圖以 `useState<'cell'|'feature'|'charts'>` 切換：
     `cell`（單格明細＋欄頭排序，已合併原「單指標排行」——`GROK-R1-P3-01`）、
     `feature`（單特徵跨格矩陣）、`charts`（單格單特徵圖表）。
     前兩者共用 `getScanCubeRows`，`charts` 走 `getScanCubeCharts`。
  4. 🔴 **圖表沿用主分析頁既有元件**，**不新寫圖表邏輯、不新算任何數值**（SPEC §C-1／§C-5）。
     🔴 **「沿用」不是介面契約**（`CODEX-R2-P2-03`／`COMPOSER-R2-P2-01`／`GROK-R2-P2-02`
     三家獨立命中）——下表是契約，實作端照表接，不得自行猜 adapter：

     | 節名 | 元件 | 期望 props 形狀 | 備註 |
     |---|---|---|---|
     | `ic_decay` | `ICDecayChart` | `decay[featureName]` | 單特徵切片 |
     | `quantile_returns` | `QuantileReturnsChart` | `quantile[featureName]` | 單特徵切片 |
     | `rolling_ic_series` | `RollingICChart` | `series[featureName]` | 單特徵切片；已被上游抽樣 |
     | `grouped_ic` | `GroupedICBarChart` | 🔴 `groupedIC[group][feature]` **巢狀 map** | **不是**扁平單 feature 物件 |
     | `marginal_ic` | 表格（非圖） | 單特徵列 | 主頁即以表格呈現 |
     | `turnover_analysis` | 主頁在 **deep tab**（`page.tsx:858-868`） | 單特徵切片 | 本票**沿用同一元件**，位置改在 cube 內 |
     | `coverage_analysis` | 🔴 **無 UI consumer**（`types.ts:2263-2273`） | — | **具名標「只表不圖」**：以原始鍵值表呈現，本票**不新寫元件** |

     charts 端點回傳**與主分析 report 同形狀之單 feature 切片**——
     即 `{"ic_decay": {<feature>: …}, "grouped_ic": {<group>: {<feature>: …}}, …}`，
     讓上表的元件可直接吃，**不需 adapter**。
     🔴 `page.tsx:208-218` 之 `sectionSplit` 處理 `SectionStatusObject`（節可能是
     `{status, reason}` 而非資料）⇒ cube 端點須**原樣**傳遞該形狀，前端沿用同一支 `sectionSplit`。
  3. 文案一律走 `frontend/src/lib/scanCubeDocs.ts`（沿用 `eventParamDocs` 之單一來源慣例）；
     元件內**不得**寫任何說明字面。
  4. 每個可編輯控制項須帶 `data-doc="<鍵>"`（沿用揭露票 R2 之一對一覆蓋閘）。
- 修改檔案：新建 `ScanCubeBrowser.tsx`、`scanCubeDocs.ts`；
  `EventBatchDisclosurePanel.tsx`（render 一行）；`frontend/src/lib/types.ts`（`ICScanCube` 型別）。
  既有 caller：`EventBatchDisclosurePanel`。
- 路徑：
  - `frontend/src/components/ic-analysis/ScanCubeBrowser.tsx`
  - `frontend/src/components/ic-analysis/scanCubeBrowser.test.tsx`
  - `frontend/src/lib/scanCubeDocs.ts`
  - `frontend/src/lib/types.ts`
  - `frontend/src/lib/api.ts`
  - `frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`
- 不可做：不得一次抓全部資料；不得顯示任何「推薦／最佳組合」；不得跨 h 排名。
- 邊界：
  1. 沒有掃描（`cube` 不存在）⇒ 整個區塊不 render（`queryByTestId('ic-cube') === null`）。
  2. `truncated=true` ⇒ 顯示 `ic-cube-not-saved`，且**不**發 rows 請求（斷言 fetch 未被呼叫）。
- 風險緩解：⊘
- 驗證：`cd frontend && npx vitest run scanCubeBrowser` rc=0。通過條件：
  - 視圖 2 render 時 `getByTestId('ic-cube-cross-h-warning')` 存在。
  - `total=1200, limit=500` ⇒ 畫面含「1200」與「1–500」，且下一頁按鈕 enabled。
  - 覆蓋閘：每個 `input[type=number]`／`select` 皆有 `data-doc` 且對應 doc 在場。
  - mutation `S7`：刪限制文字 ⇒ 紅；`S8`：truncated 分支改 render 空表 ⇒ 紅。
- **存活至**：永久。
- **覆蓋風險**：無。

---

## Phase 5 — 白話與實機驗證（完成後：使用者能自己驗）

### Task 5.1 — 白話驗收清單新增 B26／B27（`票 B26,B27`）

- SPEC ref：Task 5.1　目標：使用者能照著驗。
- 輸入 / 輸出：輸入＝已完成之畫面；輸出＝`白話說明/GAP-3驗收清單.md` 新增兩節 ＋ 簽字表兩列。
- 實作要點：
  1. B26＝掃描結果瀏覽器：在哪裡、做什麼、應該看到什麼、**不是這樣代表什麼**。
  2. B27＝落檔不再互相覆蓋：以使用者**可觀察**的現象表述（掃描後匯出的檔仍是主分析那份）。
  3. 同 commit 跑 `bash scripts/plain_docs_render.sh` 產 `docs/site/*.html`。
- 修改檔案：`白話說明/GAP-3驗收清單.md`、`白話說明/現在做到哪.md`；`docs/site/`（腳本生成）。
  既有 caller：⊘
- 路徑：
  - `白話說明/GAP-3驗收清單.md`
  - `白話說明/現在做到哪.md`
  - `docs/site/`
- 不可做：不得把 SPEC 的技術描述複製進白話（文件分層鐵律）；不得寫死任何門檻數字。
- 邊界：
  1. 上限被觸發時的畫面也要寫進驗收（否則使用者遇到會以為壞了）。
  2. 「不同 h 不可比大小」必須用白話寫一次（這是 §C-4 的使用者面）。
- 風險緩解：⊘
- 驗證：`bash scripts/plain_docs_render.sh --check` rc=0（26+ 檔、死連結 0）；
  `grep -c "B26" 白話說明/GAP-3驗收清單.md` >= 2（正文 ＋ 簽字表）。
- **存活至**：永久。
- **覆蓋風險**：無。

---

## Phase 測試與 Gate

- **單元**：`tests/api/test_scan_cube.py`（落檔／上限／清理／接線）
- **API**：`tests/api/test_scan_cube_api.py`（分頁／篩選／排序／錯誤碼）
- **前端**：`frontend/src/components/ic-analysis/scanCubeBrowser.test.tsx`
- **Golden**：`scripts/scan_cube_golden.py --check "tests/golden/scan_cube/*.json"`
- **mutation**：`handoffs/20260907-scancube-mutate.py`（S1–S12 ＋ 對照組）
- **Phase Gate**：上述五項 rc=0，且 mutation 全部符合預期，才進下一 Phase。
  🔴 **改為機械閘**（`CODEX-R2-P1-05`／`COMPOSER-R2-P2-02`／`GROK-R2-P1-04` 三家獨立命中：
  原本的「人工查 `-rs` 清單」不是可執行的 gate，執行端跑前半即可假綠交件）：
  **`bash scripts/scan_cube_phase_gate.sh <phase>`**，三項任一失敗即 rc≠0：
  ① 該 Phase 對應之 test id 出現在 `pytest -rs` 的 skip 清單 ⇒ FAIL；
  ② `scan_cube_golden.py --check` 之 glob 命中 **0 個檔** ⇒ FAIL（空迴圈假綠）；
  ③ mutation 腳本回報之 `uncovered != 0` ⇒ FAIL（`SKIP` 不計入通過）。
  **Phase Gate 之通過判準＝此腳本 rc=0，不再是裸 `pytest` 的 rc。**
