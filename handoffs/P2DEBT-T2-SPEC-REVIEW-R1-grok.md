# P2 債票 2 SPEC 初稿 R1 審查 — grok（xAI）

Task-id: `p2debt-t2` | Date: 2026-07-11 | Role: 雙家族 adversarial  
待審: `handoffs/P2DEBT-T2-SPEC-DRAFT-R1.md`（Composer）  
方法: 靜態 grep + 讀碼 + `--collect-only`；**未**執行會寫 `data_cache/` 的 pytest body。

---

## FACT-RECEIPT（本輪實跑）

1. `rg -l '\.analyze\(|start_analysis\(' tests/ --glob '*.py' | sort`  
   → 14 檔（與初稿一致）。**但此搜尋漏掉** `client.post("/api/v1/ic/analyze")` 路徑（見 R2）。

2. `rg -n 'client.post.*/api/v1/ic/analyze|/api/v1/ic/analyze' tests/ --glob '*.py'`  
   →  
   - `tests/api/test_ic_analysis_api.py:107`  
   - `tests/api/test_export_api.py:102`  
   - `tests/api/test_ic_deep_analysis.py:144`  
   初稿對照表 **零列**。

3. `rg -n 'h5py.File\(filtered_path' tests/api/test_export_api.py`  
   → L135 `with h5py.File(filtered_path, "w")`；`filtered_path` 在 `Path("data_cache/features")` 下（L125–134）。

4. `rg -n '_persist_outputs|patch_persist_outputs' tests/ --glob '*.py'`  
   → 8 處 guard（與初稿一致：orchestrator / 1eb b2/b4/b5）。

5. Production 落盤鏈（讀碼）  
   - `ICFilterOrchestrator._stage7_report` → `_persist_outputs`（`ic_filter_orchestrator.py:2827`）  
   - `_persist_outputs` 硬編碼 `data_cache/features` + `data_cache/reports`（L3173–3188）  
   - `refilter` → `_stage7_report` → 同上 persist（L1501–1575 鏈）  
   - `ICAnalysisService._materialize_features_for_ic` → `data_cache/reports/ic_ingest_cache`（L1260）  
   - `_write_ic_meta_json` → 同 cache_dir（L1321）  
   - `_apply_transforms_sync` → `data_cache/reports/post_ic_transforms_{task_id}.h5`（L976–979）  
   - `_persist_outputs` 回傳 `output_paths` **未**寫入 `report` dict（L2825–2833：先 `generate_json_report` 再 persist 且 discard 回傳）

6. Hermetic / V5 可證偽弱點  
   - `tests/feature_engineering/test_b6_warmup_trim.py:39–48`：`after - before` 只抓 **新檔路徑**，且只掃 `data_cache/features`。  
   - `scripts/agent_postflight.sh:9,28–32`：**只**在檔案數或 KB **縮減**時 FAIL；註解自承「靜默內容竄改無法用此廉價法偵測」；**成長/覆寫 PASS**。

7. Fixture 掛載  
   - `tests/momentum/conftest.py` **不存在**（`ls` 失敗）  
   - `tests/api/conftest.py` **存在**  
   - pytest conftest 不跨 sibling：`tests/momentum/**` fixture **不會**自動進 `tests/api/**`

8. Collect-only（未跑 body）  
   - 初稿 P0 集合 + run_selector + service：`44 tests collected`  
   - `test_export_api` + `test_ic_analysis_api` + `test_ic_deep_analysis`：`32 tests collected`

9. P0 無 guard 之 analyze 呼叫（讀碼）  
   - `test_ic_1a_cut1_oos.py`: `test_fallback_*`、`test_oos_applied_*` 全鏈 analyze（正確列 P0）；stub stage7 / fail-closed 不寫（初稿正確）  
   - `test_ic_e2e.py` class 內 4–5 個 analyze/refilter（正確列 P0）  
   - `test_ic_feature_filter.py` 1 個 analyze（正確）  
   - `test_ic_1a_cut1_golden.py` `start_analysis` 真鏈（正確列 P0；票 5 交界）

---

## 覆蓋完整性對照（審查補表）

| 測試檔 | 寫入機制 | 生產路徑（相對 repo 根） | 初稿？ |
|--------|----------|--------------------------|--------|
| `tests/momentum/Analysis/test_ic_1a_cut1_oos.py`（2 測） | `ICFilterOrchestrator.analyze` → stage7 → `_persist_outputs` | `data_cache/features/BTCUSDT_1h_filtered.h5`；`data_cache/reports/ic_report_ic_gatekeeper.*` 等 | 有 P0 |
| `tests/momentum/test_ic_e2e.py` | analyze/refilter 全鏈 | `BTCUSDT_12h_filtered.h5`；`ic_report_ic_e2e_test.*` | 有 P0 |
| `tests/momentum/test_ic_feature_filter.py` | analyze 全鏈 | `BTCUSDT_12h_filtered.h5`；`ic_gatekeeper` reports | 有 P0 |
| `tests/momentum/Analysis/test_ic_1a_cut1_golden.py` | `ICAnalysisService.start_analysis` → orchestrator persist | 同上 BTC 1h + gatekeeper | 有 P0 |
| `tests/api/test_ic_analysis_service.py`（2 測） | `_materialize_features_for_ic` write-if-absent | `data_cache/reports/ic_ingest_cache/*` | 有 P1 |
| **`tests/api/test_ic_analysis_api.py`** | session fixture `POST /api/v1/ic/analyze` 真鏈；refilter 再 stage7 | `TESTUSDT_12h_filtered.h5`；`ic_report_ic_api_test.*` | **漏** |
| **`tests/api/test_export_api.py`** | session fixture 同上 + **直接** `h5py.File(...,"w")` 覆寫 features | 同上 + 強制覆寫 filtered h5 | **漏** |
| **`tests/api/test_ic_deep_analysis.py`** | module fixture `POST /api/v1/ic/analyze`；另 full-analysis 路徑 | 依 meta symbol/tf；reports+filtered | **漏** |
| `test_lightgbm_*` / `test_xgboost_*` | `save_model` → `data_cache/models/` | models/*.pkl | P2 延期（可接受若寫死） |
| 已 guard 之 1eb / filter_orchestrator | no-op `_persist_outputs` | 無生產污染 | 正確 |
| long_short `analyze` | **不同** analyzer，非 IC persist | N/A | 正確未列 |

**漏網 = 實跑 API suite 仍污染 → 票 2 閉合假完成。**

---

## Findings

### BLOCKING-1 — 對照表漏 API 真路徑 polluters（任務 §1 零容忍）

**證據**: FACT-RECEIPT 2–3；`test_ic_analysis_api.py:69–113` session fixture 無 `_persist` guard；`test_export_api.py:66–138` 另含直接 h5py 寫 `data_cache/features`；`test_ic_deep_analysis.py:124–148` module fixture 同 POST analyze。

**根因**: 初稿 inventory 只 `rg analyze(|start_analysis(`，**漏 HTTP 入口**。漏一個 = BLOCKING（任務原文）。

**修法要求**: 對照表補至少 3 檔 + 每個 fixture 的落盤 case_id/symbol；Phase 2 掛 redirect 或等價隔離；export 的 **直接 h5py** 必須獨立處理（見 B-2）。

### BLOCKING-2 — redirect 只 wrap `_persist_outputs` / materialize **攔不住所有落盤**

| 繞過 | 路徑 | wrap `_persist_outputs`？ |
|------|------|---------------------------|
| `test_export_api` 直接 `h5py.File(data_cache/features/..., "w")` | features | **否** |
| `_apply_transforms_sync` `df.to_hdf(data_cache/reports/post_ic_transforms_*.h5)` | reports | **否** |
| `_write_ic_meta_json`（materialize 分支外） | ic_ingest_cache | 初稿有提 materialize，**meta 單獨入口**須寫死 patch |
| `save_model` → models/ | models | 初稿 P2 延期 — 可，但須在對照表標「已知殘留污染」 |
| 類級 no-op 後 **instance 仍呼叫 reporter 直接 save**（若未來測試） | reports | 視 patch 粒度 |

**最小反例（靜態）**:  
`tests/api/test_export_api.py:125–137` 在 fixture 內 `Path("data_cache/features").mkdir` + `h5py.File(...,"w")`——不經過 `ICFilterOrchestrator._persist_outputs`。即使 class-wrap orchestrator persist 全綠，此 fixture 仍污染。

**修法要求**: redirect helper 的「完成定義」= 覆蓋 **所有** 已知 production 字面量寫入點（至少 features/reports/ic_ingest_cache），**或** 測試側禁止直接寫 production path（export fixture 改 `tmp_path`）。不得只寫「wrap one method」。

### BLOCKING-3 — §V hermetic / V5 **不能**機驗「零變化」（可被假綠）

1. **借鑑 b6**（SPEC Task 3.1）: 只 diff **新檔 path set**，且只看 `data_cache/features`。  
   IC1EB 債原貌 = **覆寫既有** `BTCUSDT_1h_filtered.h5` + `ic_report_ic_gatekeeper.json`（mtime 變、path 不變）→ b6 式斷言 **PASS 假綠**。

2. **V5 `agent_preflight`/`postflight`**: postflight **只**抓縮減；檔案數/KB 因測試寫入而**增加**或**同大小覆寫** → 仍印 ✅。  
   用 V5 當「data_cache 零變化」驗收 = **結構性假綠**。

3. **「或 mtime+size」** 未寫死：實作可選弱快照。須 **強制** 至少：  
   `(relpath, size, mtime_ns)` 或 content hash，範圍含 `features/` **與** `reports/`（含 `ic_ingest_cache`），且 before/after 在 **同一 process 同一 suite** 內。

### BLOCKING-4 — Task 3.2 mutation「拿掉 redirect 必 FAIL」設計未閉合

- 現稿：關 redirect → 跑真 analyze → 斷言 production snapshot diff 非空；用 `RUN_IC_PERSIST_MUTATION=1` 才開。  
- 問題：  
  (a) **預設 CI 不跑** → 日常不可證偽；  
  (b) 開啟時 **故意寫生產 data_cache**，與票目標（零污染）衝突；  
  (c) V4 寫「預期 fail 或 xpass」— 機檢不可判定。  
- **建議可證偽形**（不寫生產）:  
  - 將「假想 production root」monkeypatch 成 `tmp_path / "fake_prod_data_cache"`（patch `_resolve_filtered_path` + reporter `output_dir` 字面量來源 / 或 chdir 沙箱），  
  - mutation A：無 redirect helper → 寫入落在 fake_prod；  
  - mutation B：有 redirect → 寫入只在 redirect root，fake_prod 快照空；  
  - **禁止** 對真實 repo `data_cache/` 做污染型 mutation。

### BLOCKING-5 — P1 API 測試的 fixture 掛載方案失效

SPEC: fixture 放 `tests/momentum/conftest.py` 或 `Analysis/conftest.py` + marker opt-in。  
事實: `tests/momentum/conftest.py` 不存在；即使新建，**不會** load 到 `tests/api/test_ic_analysis_service.py`（P1）或漏網 API 檔。  
影響: P1「掛 fixture」若只寫 momentum conftest = **靜默不生效**。  
修法: shared module `tests/fixtures/ic_persist_redirect.py` + **api 與 momentum 兩側** conftest 註冊，或測試檔顯式 import fixture；禁止假設單一 subtree conftest 覆蓋 api。

### MINOR-1 — 大小標「中」vs 任務已升級「大」

派工檔標題：票已升級「大」；SPEC §RISK 仍寫 **中**。  
命中 (a)(b) + 多 suite + 票 5 交界 → 維持「大」較一致；至少改 §RISK 敘事避免 gate/管線假設漂移。

### MINOR-2 — RISK-HIT: a,b 方向正確但 **scope 偏窄**

- (a) 合理：legacy 測試覆寫 gitignored 衍生檔污染真實 cache。  
- (b) 合理：orchestrator + service 共用 `data_cache/{features,reports}`。  
- **過窄**: 未把 API route 測試、export 直接寫、transforms 落盤納入 (b) 共用路徑集合 → 與 B-1/B-2 同源。  
- **未過寬**: 未誤標 feature_kline 只讀、governance 等。

### MINOR-3 — 票 5 交界判定（**不升級聯合委員會**）

- golden 斷言 = in-memory `get_result()` JSON vs 凍結 baseline（豁免 `generated_at`）。  
- `_persist_outputs` 回傳 paths **不併入 report** → 僅改磁碟根 **不應** 改 golden 雜湊契約。  
- **成立條件**: redirect 不得改 `generate_json_report` 輸入、不得改 read path 到錯誤 features、不得改 golden 檔本身。  
- 若實作改為「no-op persist」並有 caller 依賴 side-effect 檔存在（export hdf5 讀 filtered）— 那是 export 測試問題，golden 仍可獨立。  
- **結論**: 劃界目前 **成立**；非 BLOCKING。實作若誤傷 baseline → 再升聯合委員會（初稿已寫，保留）。

### MINOR-4 — opt-in marker 無強制 = 未來回歸仍可漏掛

建議另加（可 Phase 3）: 靜態/測試掃描「全鏈 analyze 且無 redirect marker / 無 persist guard → fail」；否則新測試再污染。

### MINOR-5 — P2 models/ 延期可接受

`data_cache/models` 寫入與 B3 裁定主因（filtered+ic_report）不同根；延期 OK，但閉合報告不得宣稱「全 tests/ 零 data_cache 寫入」。

---

## 任務六點對照摘要

| # | 題 | 判定 |
|---|----|------|
| 1 | 覆蓋完整性 | **FAIL** — 至少漏 3 個 API 真路徑 polluter |
| 2 | redirect 攔全落盤 | **FAIL** — 直接 h5py / transforms / 掛載範圍 |
| 3 | §V 可證偽 | **FAIL** — b6 式 + postflight 假綠；mutation 未閉合 |
| 4 | 票 5 交界 | **PASS**（條件式）— 僅改磁碟路徑不改 report JSON |
| 5 | suite 漂移 | 禁根 autouse **正確**；但 momentum-only conftest **覆蓋不足** api |
| 6 | RISK-HIT a,b | 方向對；inventory 窄 → 執行面 under-scope |

---

## 初稿優點（不阻擋 BLOCK）

- 正確區分 no-op capture patch vs tmp **redirect 保留 save 語意**  
- P0 cut1/e2e/feature_filter/golden 主債路徑對  
- 禁根 `tests/conftest.py` autouse 防 FF/governance 漂移  
- 票 5 劃界與「不改 production persist 語意」邊界清楚  
- 已 guard 清單與 stage-only 不寫歸因大致正確  

---

## 修稿最低閉合條件（給 R2）

1. 對照表 + Phase 2 納入 `test_ic_analysis_api` / `test_export_api` / `test_ic_deep_analysis`（含直接 h5py）。  
2. redirect 完成定義含全部硬編碼寫入點或測試改 tmp；附繞過測試。  
3. Hermetic 快照強制 path+size+mtime（或 hash），含 features+reports；**刪除或降級** V5 postflight 作為零變化證明。  
4. Mutation 在 tmp 假 production root 上可證偽，預設 CI 可跑且不寫真 `data_cache/`。  
5. Fixture 跨 `tests/api` + `tests/momentum` 可載入路徑寫死。  

---

ASSUMPTIONS_VERIFIED: stage7→persist；refilter→stage7；persist 回傳不入 report；export 直接 h5py；postflight 只抓縮減；b6 只抓新 features 檔；api 三檔 POST analyze 無 persist guard；momentum/conftest 不存在  
TESTS_RUN: `pytest ... --collect-only` P0 集合 44 collected；export+api+deep 32 collected；全靜態 rg/讀碼；**0** 寫入 body  
FAILURES_SEEN: none（審查輪）  
SCOPE_CHANGES: none（只寫本審查檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  

Verdict: BLOCK — 對照表漏 API polluters；redirect 有繞過；hermetic/V5/mutation 可假綠
