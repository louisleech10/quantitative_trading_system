# P2 債票 2 — legacy 測試 data_cache 污染 → tmp redirect — SPEC 修訂 R2

> 來源：R1 `handoffs/P2DEBT-T2-SPEC-DRAFT-R1.md` + 雙家族 BLOCK（grok R1 + codex R1）閉合　|　日期：2026-07-11　|　起草：Composer　|　task-id：`p2debt-t2`  
> 對應 TODO：本 SPEC 雙審 STAMP 後由 `templates/TODO_GENERATION_PROMPT.md` 生成

## 白話簡述（大任務 manifest）

**問題**：多支 pytest 與手動 generator 走真 IC / FF / ML 落盤鏈，會覆寫或新增 gitignored 的 `data_cache/{features,reports,models}`，污染開發者真實快取（IC1EB-B3 已實測 `BTCUSDT_1h_filtered.h5` mtime 變化）。

**做法**：不改生產 persist 語意；在測試層以**可執行、可 spy 的多 seam redirect** 把落盤根目錄改到 `{tmp_path}/data_cache/...`；以**外層 harness 的 per-file digest** 證明 repo 內 `data_cache/` 零變化；mutation 同檔自證「撤 redirect → oracle 必抓 → 還原綠」；golden 加同輸入 A/B normalized hash oracle，確保票 5 邊界。

**不做**：不改 `momentum/` / `api/services/` 生產硬編碼路徑本體；不 root autouse；不把 polluter 改 skip 換綠；不把 models/FF/API 漏網延後 Phase 4。

**雙家族閉合條款（STAMP 必驗）**：
1. §COVERAGE 表與本輪 `rg` 全集一致，無「Phase 4 延後 polluter」。
2. §SEAM 每個 patch 點有 injectable 參數 + per-seam spy + 跨 `tests/momentum` + `tests/api` conftest 掛載。
3. §V 僅 digest oracle；V5 postflight **不得**作零變化主證明；V1/V2 禁 skip-as-green。
4. §G golden 兩 nodeid 須 `passed` + A/B hash receipt。
5. §ISOLATION spy/canary 證明 opt-in / non-opt-in 邊界。

---

## §RISK 風險分級

- **大小**：**大** — 跨 `tests/momentum`、`tests/api`、`tests/` 根 FF e2e、models persist、3 支 API HTTP fixture 鏈、手動 generator 契約；零生產語意變更；票 5 相鄰。
- **命中高風險原則**：
  - **(a) 數值/資料品質邊界**：legacy 測試覆寫 gitignored 衍生檔，污染真實快取與後續判讀。
  - **(b) 跨模組共用路徑**：`ICFilterOrchestrator`、`ICAnalysisService`、`api/routes/ic_analysis`、FF `FeatureStorage`、ML `save_model` 共用 `data_cache/{features,reports,models}` 字面量根。
- **RISK-HIT 宣告**（機檢依據，缺行 FAIL）：
- RISK-HIT: a,b
- **票 5 交界**：redirect 僅改磁碟根、不改 in-memory `get_result()` JSON → **不升級聯合委員會**；須 §G A/B oracle 實證；若誤傷 baseline 雜湊 → 升級票 5 委員會。

---

## §A 假設與已確認事實

- **FACT-RECEIPT 格式**：`FACT-RECEIPT: <命令> → <stdout 摘要>（<who> <date>）`
- **canonical 已確認行**：`- **已確認**：<陳述> — FACT-RECEIPT: ...`

### 偵察 receipt（2026-07-11 Composer 實跑；僅 read-only / collect-only / 讀碼）

- **已確認**：`analyze|start_analysis|refilter` caller 在 `tests/**/*.py` 共 **16** 檔（含 long_short / phase26 / generator，非全為 IC persist）。 — FACT-RECEIPT: `rg -l '\.(analyze|start_analysis|refilter)\(' tests/ --glob '*.py' | sort | wc -l` → `16`（Composer 2026-07-11）
- **已確認**：HTTP `POST /api/v1/ic/analyze` 出現在 **3** 檔（R1 漏列）。 — FACT-RECEIPT: `rg -l 'client\.post.*/api/v1/ic/analyze' tests/ --glob '*.py' | sort` → `tests/api/test_export_api.py`、`test_ic_analysis_api.py`、`test_ic_deep_analysis.py`（Composer 2026-07-11）
- **已確認**：`export_api` session fixture **直接** `h5py.File(...,"w")` 寫 `data_cache/features/`（不經 `_persist_outputs`）。 — FACT-RECEIPT: `rg -n 'h5py.File\(filtered_path' tests/api/test_export_api.py` → `L135`；`rg -n 'features_dir = Path' tests/api/test_export_api.py` → `L125`（Composer 2026-07-11）
- **已確認**：`_persist_outputs` 硬編碼 `data_cache/features` + `data_cache/reports`；`_persist_outputs` **僅**在 `_stage7_report` 內呼叫。 — FACT-RECEIPT: `rg -n '_persist_outputs' momentum/Analysis/ic_filter_orchestrator.py` → 定義 `L3162`、呼叫 `L2827`；`sed -n '3172,3207p' momentum/Analysis/ic_filter_orchestrator.py` → `output_dir="data_cache/reports"`、`Path("data_cache/features")`（Composer 讀碼 2026-07-11）
- **已確認**：僅 patch `_resolve_filtered_path` **攔不住** reports（codex R4 靜態鏈）。 — FACT-RECEIPT: `rg -n 'output_dir=\"data_cache/reports\"' momentum/Analysis/ic_filter_orchestrator.py` → `L3182`、`L3188`（Composer 2026-07-11）
- **已確認**：三個 service method **無** output root 注入參數。 — FACT-RECEIPT: `venv/bin/python -c "import inspect; from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator; from api.services.ic_analysis_service import ICAnalysisService; print(inspect.signature(ICFilterOrchestrator._persist_outputs)); print(inspect.signature(ICAnalysisService._materialize_features_for_ic)); print(inspect.signature(ICAnalysisService._write_ic_meta_json))"` → 皆無 root 參數（Composer 2026-07-11）
- **已確認**：`path+size` oracle 對同尺寸覆寫假綠（codex R6）。 — FACT-RECEIPT: `python3 -c "..."` → `path_size_oracle_false_green= True`（4-byte `AAAA`→`BBBB`）（Composer 2026-07-11）
- **已確認**：`agent_postflight.sh` 只 FAIL 於檔案數/KB **縮減**；註解自承無法偵測同尺寸內容竄改。 — FACT-RECEIPT: `sed -n '8,32p' scripts/agent_postflight.sh` → 縮減才 FAIL（Composer 讀碼 2026-07-11）
- **已確認**：`test_b6_warmup_trim._assert_data_cache_unchanged` 只 diff **新增** `data_cache/features` 路徑集合。 — FACT-RECEIPT: `sed -n '39,48p' tests/feature_engineering/test_b6_warmup_trim.py` → `new_files = after - before`（Composer 讀碼 2026-07-11）
- **已確認**：`tests/momentum/conftest.py` **不存在**；`tests/api/conftest.py` **存在**。 — FACT-RECEIPT: `test -f tests/momentum/conftest.py; echo $?` → `1`；`test -f tests/api/conftest.py; echo $?` → `0`（Composer 2026-07-11）
- **已確認**：P0+API+FF+models 污染相關 collect-only **102** tests（未跑 body）。 — FACT-RECEIPT: `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py tests/momentum/test_ic_e2e.py tests/momentum/test_ic_feature_filter.py tests/momentum/Analysis/test_ic_1a_cut1_golden.py tests/api/test_ic_analysis_service.py tests/api/test_ic_analysis_api.py tests/api/test_export_api.py tests/api/test_ic_deep_analysis.py tests/test_feature_factory_e2e.py tests/momentum/Analysis/test_lightgbm_analyzer.py tests/momentum/Analysis/test_xgboost_protocol_methods.py --collect-only -q 2>&1 | tail -1` → `102 tests collected`（Composer 2026-07-11）
- **已確認**：`test_ic_1a_cut1_split::test_pipeline_order_split_before_preprocessing` 與 `test_ic_1a_cut1_oos::test_flag_toggles_path` **stub `_stage7_report`** → **不**觸 `_persist_outputs`（codex B1 靜態歸因修正）。 — FACT-RECEIPT: `rg -n '_stage7_report = lambda' tests/momentum/Analysis/test_ic_1a_cut1_split.py tests/momentum/Analysis/test_ic_1a_cut1_oos.py` → split `L273`、oos `L373,L380`；`rg -n '_persist_outputs' momentum/Analysis/ic_filter_orchestrator.py` → 僅 `L2827`（stage7 內）（Composer 2026-07-11）
- **已確認**：`tests/test_feature_factory_e2e.py` 預設 `generate_features()` **persist=True** → `FeatureStorage('data_cache/features')`（R1 誤列只讀）。 — FACT-RECEIPT: `rg -n 'generate_features\(' tests/test_feature_factory_e2e.py` → 6 處無 `persist=False`；`rg -n 'base_path.*data_cache/features' momentum/FeatureEngineering/feature_storage.py` → `L686`（Composer 2026-07-11）
- **已確認**：`GET /api/v1/ic/export-csv/{task_id}` 落盤 `data_cache/reports/ic_filtered_{task_id}.csv`。 — FACT-RECEIPT: `sed -n '405,408p' api/routes/ic_analysis.py` → `output_dir = Path("data_cache/reports")`（Composer 讀碼 2026-07-11）

### §COVERAGE — `tests/` 全量寫入路徑對照表（2026-07-11  exhaustive `rg` + 讀碼；無 Phase-4 polluter Defer）

**圖例**：`REDIRECT`＝本票必掛 opt-in redirect；`GUARD`＝已有 no-op/monkeypatch；`STUB`＝stub stage7 靜態證實不寫；`ISOLATED`＝已有 tmp/settings/FFACT 隔離；`MANUAL`＝非 pytest autouse；`READ`＝只讀 kline/registry。

#### A. IC 鏈 — 真 persist（REDIRECT 必掛）

| ID | 測試檔 / nodeid 或 fixture | 寫入機制 | 生產落盤路徑 | R1 |
|----|---------------------------|----------|--------------|-----|
| IC-01 | `tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_fallback_insufficient_data_marks_applied_false` | 全鏈 `analyze()`→stage7→`_persist_outputs`；meta BTCUSDT/1h | `data_cache/features/BTCUSDT_1h_filtered.h5`；`data_cache/reports/ic_report_ic_gatekeeper.{json,md}`；`ic_summary_*.csv`；`ic_filter_log_*.json` | P0 |
| IC-02 | `…/test_ic_1a_cut1_oos.py::test_oos_applied_true_when_sufficient` | 同上 | 同上 | P0 |
| IC-03 | `tests/momentum/test_ic_e2e.py::TestICGatekeeperE2E::test_full_pipeline_global_mode` | `create_ic_analyzer().analyze()`；case `ic_e2e_test` | `data_cache/features/BTCUSDT_12h_filtered.h5`；`data_cache/reports/ic_report_ic_e2e_test.*` | P0 |
| IC-04 | `…/test_ic_e2e.py::…::test_refilter_uses_cache` | analyze + `refilter()`→stage7→persist | 同上（第二次 report 覆寫） | P0 |
| IC-05 | `…/test_ic_e2e.py::…::test_event_mode_with_query` | analyze 全鏈 | 同上 | P0 |
| IC-06 | `…/test_ic_e2e.py::…::test_report_json_structure` | analyze 全鏈 | 同上 | P0 |
| IC-07 | `…/test_ic_e2e.py::…::test_performance_800_features`（`RUN_IC_E2E_PERF=1`） | analyze 全鏈 | 同上 | P0 |
| IC-08 | `tests/momentum/test_ic_feature_filter.py::test_analyze_applies_feature_filter_metadata_and_summary_limit` | `ICFilterOrchestrator.analyze()` BTCUSDT/12h | `BTCUSDT_12h_filtered.h5`；`ic_gatekeeper` reports | P0 |
| IC-09 | `tests/momentum/Analysis/test_ic_1a_cut1_golden.py::test_flag_off_deep_equal_baseline` | `ICAnalysisService.start_analysis()`→orchestrator 全鏈 | BTCUSDT/1h + gatekeeper（**票 5 相鄰**） | P0 |
| IC-10 | `…/test_ic_1a_cut1_golden.py::test_flag_on_matches_new_golden` | 同上 | 同上 | P0 |
| IC-11 | `tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis` | `_materialize_features_for_ic` write-if-absent | `data_cache/reports/ic_ingest_cache/BTCUSDT_12h_{hash}.{h5,_meta.json}` | P1 |
| IC-12 | `…/test_ic_analysis_service.py::test_resolve_run_path_contains_config_hash` | 同上 | 同上 | P1 |

#### B. API HTTP 鏈 — session/module fixture 污染（REDIRECT 必掛；R1 **漏**）

| ID | 測試檔 / 觸發點 | 寫入機制 | 生產路徑 | R1 |
|----|----------------|----------|----------|-----|
| API-01 | `tests/api/test_ic_analysis_api.py` fixture `ic_analysis_task`（L69–113 `POST /api/v1/ic/analyze`） | 真 service 鏈 stage7 persist | `TESTUSDT_12h_filtered.h5`；`ic_report_ic_api_test.*` | **漏** |
| API-02 | 同上 fixture 下游 **10** nodeids + `test_ic_refilter` | 讀 in-memory；refilter 再 persist | 同上 + 覆寫 reports | **漏** |
| API-03 | `test_ic_analysis_api.py::test_ic_export_csv` | `GET /api/v1/ic/export-csv/{task_id}` | `data_cache/reports/ic_filtered_{task_id}.csv` | **漏** |
| API-04 | `tests/api/test_ic_deep_analysis.py` fixture `completed_ic_task`（L124–148 POST analyze） | 真鏈 persist | `TESTUSDT_12h` + `ic_deep_api_test` reports | **漏** |
| API-05 | 同上 fixture 下游 deep-analysis nodeids（≥8） | 依賴已完成 analyze | 同上 | **漏** |
| API-06 | `tests/api/test_export_api.py` fixture `export_task`（L66–138） | POST analyze persist **+** 直接 `h5py.File(filtered_path,"w")` L125–137 | `TESTUSDT_12h_filtered.h5` **強制覆寫** | **漏** |
| API-07 | `export_task` 下游 8 個 export nodeids | 讀已污染 filtered h5 | 間接依賴 features | **漏** |

#### C. ML models/（REDIRECT 必掛；R1 Phase-4 defer **撤銷**）

| ID | nodeid | 寫入 | 路徑 |
|----|--------|------|------|
| ML-01 | `test_lightgbm_analyzer.py::test_save_and_load_roundtrip` | `save_model` | `data_cache/models/test_lightgbm_roundtrip.pkl` |
| ML-02 | `test_lightgbm_analyzer.py`（bad payload 分支） | `save_model` | `data_cache/models/lightgbm_bad_payload.pkl` |
| ML-03 | `test_lightgbm_edge_cases.py::test_s4_type_mismatch_*`（lgb/xgb/retrain） | `save_model` | `data_cache/models/type_mismatch_*.pkl`、`retrain_{engine}.pkl` |
| ML-04 | `test_xgboost_protocol_methods.py::test_xgboost_model_path_safety_and_type_mismatch` | `save_model` | `data_cache/models/xgb_roundtrip_protocol.pkl` |
| ML-05 | `test_lightgbm_analyzer_phase3.py::test_lightgbm_save_load_and_type_mismatch` | `save_model` | `data_cache/models/*.pkl` |
| ML-06 | `test_xgboost_protocol_methods_phase3.py` save 分支 | `save_model` | `data_cache/models/*.pkl` |

#### D. Feature Factory 真 persist（REDIRECT 必掛；R1 誤判只讀）

| ID | 測試檔 | 條件 | 路徑 |
|----|--------|------|------|
| FF-01 | `tests/test_feature_factory_e2e.py`（8 nodeids 中 6 個 `generate_features`） | 預設 `persist=True`；skip 若無 kline | `data_cache/features/{symbol}/{config_hash}/…` |
| FF-02 | `tests/feature_engineering/**` 多數 | **已** `conftest` FFACT + `_isolate_feature_output` | tmp（**ISOLATED**，本票 regression canary 覆蓋） |

#### E. 手動 generator（MANUAL — 不 pytest autouse；須文件化 + 手動 hermetic 契約）

| ID | 腳本 | 寫入 |
|----|------|------|
| GEN-01 | `tests/fixtures/gen_ic_run_selector_baseline.py` | materialize + IC persist + baseline json |
| GEN-02 | `tests/golden/ic_phase1_contract/freeze_baseline.py` | `start_analysis` persist |
| GEN-03 | `tests/golden/ic_phase1_1a_cut1/freeze_baseline.py` | 同上 |
| GEN-04 | `tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py` | 同上 |

#### F. 已防護 / 不寫 / 只讀（無 REDIRECT）

| 類別 | 代表 | 機制 |
|------|------|------|
| GUARD | `test_ic_filter_orchestrator.py`（4× `_persist_outputs` no-op）、`test_ic_1eb_b4_fullstack.py`、`test_ic_1eb_b2_wiring.py`、`test_ic_1eb_b5_golden.py`（`patch_persist_outputs`） | 已有 |
| STUB | `test_ic_1a_cut1_oos.py::test_flag_toggles_path`；`test_ic_1a_cut1_split.py::test_pipeline_order_split_before_preprocessing` | stub `_stage7_report` → 無 persist |
| STUB | `test_ic_1a_cut1_oos.py` 多數 stage-only；`test_irregular_timestamps_still_fail_closed` | fail-closed 於 stage7 前 |
| ISOLATED | `tests/api/test_batch_*.py`、`test_b4_bulk_delete_orphan.py`（`settings.data_cache_path=tmp`） | 已有 |
| ISOLATED | `tests/feature_engineering/conftest.py` autouse FFACT registry | 已有 |
| READ | `data_cache/feature_klines/kline_cache.h5` 讀取類 | 不寫 |
| N/A | `test_long_short_analyzer.py`、`phase25/26` `analyze()` | 非 IC persist 鏈 |

**閉合計數（REDIRECT 範圍）**：IC **12** nodeids + API **3** fixture 鏈（含 export 直接 h5py）+ ML **6** 檔 + FF-01 **6** `generate_features`；**不得**宣稱「tests/ 零 data_cache 寫入」直到上表全綠。

---

## §SEAM 可執行 redirect 設計（回應 grok B-2 / codex B2）

### 原則

- **禁止** `chdir(tmp)`（會破 golden 相對 `BASELINE_PATH`）。
- **禁止** class-level no-op（須保留真實 save 語意，只改根）。
- **禁止**僅 wrap `_persist_outputs` 或僅 patch `_resolve_filtered_path`（reports 仍落生產）。
- **必須** injectable `redirect_root: Path` 參數貫穿 helper；測試透過 **marker + `usefixtures`** 請求 fixture（marker 本身不觸發）。

### 共用模組 `tests/fixtures/ic_persist_redirect.py`

```python
PRODUCTION_DATA_CACHE = Path("data_cache")

@dataclass
class RedirectContext:
    redirect_root: Path
    production_spy: ProductionWriteSpy

def install_ic_persist_redirect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    include_models: bool = False,
    include_ff_features: bool = False,
) -> RedirectContext:
    """單一入口：patch 下列 SEAM，並安裝 production prefix spy。"""
```

### 具名 patch 點（實作必全掛；單元測試逐 seam assert）

| Seam ID | Patch target | 作法 |
|---------|--------------|------|
| S1 | `momentum.Analysis.ic_filter_orchestrator.ICFilterOrchestrator._resolve_filtered_path` | wrap：回傳 `{redirect_root}/features/{name}` |
| S2 | `ICFilterOrchestrator._persist_outputs` | wrap 原函式：將傳入 `ICReporter.save_report/save_filter_log` 的 `output_dir` 字面量 `data_cache/reports` 改為 `{redirect_root}/reports` |
| S3 | `api.services.ic_analysis_service.ICAnalysisService._resolve_filtered_path`（L1478） | 同 S1 |
| S4 | `ICAnalysisService._materialize_features_for_ic` | wrap：`cache_dir = redirect_root / "reports" / "ic_ingest_cache"` |
| S5 | `ICAnalysisService._write_ic_meta_json` | 同 S4 |
| S6 | `ICAnalysisService._apply_transforms_sync` | wrap：`output_dir = redirect_root / "reports"` |
| S7 | `api.routes.ic_analysis._resolve_filtered_path` | 同 S1（API export 路徑） |
| S8 | `api.routes.ic_analysis.export_filtered_csv` 內 `output_dir` | wrap 或 monkeypatch `Path` 建構改寫 |
| S9 | `tests/api/test_export_api.py` fixture 內 L125–137 直接 h5py | **測試側**改寫：filtered_path 必須在 `redirect_root/features/`（或刪除直接寫、改讀 redirect 產物） |
| S10 | ML `save_model` 路徑（`include_models=True`） | monkeypatch `Path("data_cache/models").resolve()` 導向 `{redirect_root}/models` **或** wrap analyzer `_validate_model_path` 接受 redirect 前綴 |
| S11 | FF `FeatureStorage`（`include_ff_features=True`） | 同 `test_b6`：`factory._storage = FeatureStorage(redirect_root / "features")` |

### `ProductionWriteSpy`（每 seam 共用）

- 安裝於 `open` / `Path.write_text` / `Path.mkdir` / `h5py.File`（mode 含 `w`/`a`）：
- 若目標路徑 `resolve()` 以 `PRODUCTION_DATA_CACHE.resolve()` 為前綴 → 記錄 violation 並 **raise**（單元測試）或累積（integration）。
- redirect 啟用後跑 P0 最小 analyze → `spy.violations == []`。

### conftest 掛載（回應 grok B-5 / codex B2）

| 檔案 | 動作 |
|------|------|
| **新建** `tests/momentum/conftest.py` | `pytest_plugins = ["tests.fixtures.ic_persist_redirect_plugin"]`；註冊 marker `ic_persist_redirect` |
| `tests/momentum/Analysis/conftest.py` | `from tests.fixtures.ic_persist_redirect import ic_persist_redirect` + re-export（subtree 可見） |
| `tests/api/conftest.py` | 同上 re-export（**API 與 momentum 同 fixture**） |
| `tests/fixtures/ic_persist_redirect_plugin.py` | 定義 `@pytest.fixture def ic_persist_redirect(...)` |

### opt-in 接線範式（必須出現在每個 REDIRECT 檔案頂部）

```python
pytestmark = [pytest.mark.ic_persist_redirect, pytest.mark.usefixtures("ic_persist_redirect")]
```

- Session/module fixture 檔（`test_ic_analysis_api.py`、`test_export_api.py`、`test_ic_deep_analysis.py`）：fixture 函式參數 **顯式** `ic_persist_redirect: RedirectContext`，確保 setup 前已 redirect。
- **禁止**根 `tests/conftest.py` autouse redirect。

---

## §C 約束

- **硬邊界**：不改生產 persist 簽名與硬編碼字面量本體；不刪改 repo `data_cache/`（驗收取 digest）；不 root autouse；不 skip-as-green；不弱化 NaN/inf gate。
- **允許改動**：
  - `tests/fixtures/ic_persist_redirect.py`、`ic_persist_redirect_plugin.py`
  - **新建** `tests/momentum/conftest.py`
  - `tests/momentum/Analysis/conftest.py`、`tests/api/conftest.py`
  - §COVERAGE 全表 `REDIRECT` 列檔案 + `tests/test_feature_factory_e2e.py`
  - 新建：`test_ic_persist_redirect_unit.py`、`test_ic_data_cache_hermetic.py`、`test_ic_persist_redirect_isolation.py`、`test_ic_persist_redirect_golden_ab.py`
  - `docs/` 增補 MANUAL generator 操作（GEN-*）
- **不允許**：`momentum/`、`api/services/` 生產邏輯（除非委員會另開票）

---

## §G Golden / 票 5 邊界（回應 codex B4 / grok MINOR-3）

- **性質**：redirect 為純 path 參數替換；in-memory report JSON **應** byte-identical（豁免欄位除外）。
- **凍結對照**：`tests/golden/ic_phase1_1a_cut1/baseline_old_btc_1h_a384e6d2.json`、`baseline_new_btc_1h_a384e6d2.json`。
- **A/B oracle（新建 `test_ic_persist_redirect_golden_ab.py`）**：
  1. 固定輸入（與 golden 相同 `ICAnalyzeRequest` / paths）。
  2. **Run A**：`redirect_root=tmp_a`，跑 `start_analysis`，取 `get_result()` → `normalize(result)` → `sha256`。
  3. **Run B**：`redirect_root=tmp_b`（不同 tmp），同輸入 → 同 hash。
  4. **Run C**（可選）：無 redirect 但 **僅寫 tmp 內 fake prod**（mutation 替身），hash 仍等於 A/B。
  5. `assert hash_a == hash_b`；`production_spy` 全程空。
- **§G/V 統一 exit（回應 codex M1）**：

| 命令 | 通過條件（機掃，禁 `0 failed` 含糊） |
|------|--------------------------------------|
| `pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q` | stdout 含 **`2 passed`** 且 **不含** `skipped` / `failed` |
| `pytest tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py -q` | **`1 passed`**；stdout 含 `ab_hash=` 32+ hex |
| digest | `sha256(normalize(with_redirect)) == sha256(normalize(without_redirect_on_tmp))` receipt 印出 |

- baseline 檔缺失 → **FAIL**（非 skip）；與票 5 聯合委員會前不得 merge。

---

## §ISOLATION suite 漂移 gate（回應 codex B5 / grok MINOR-4）

**新建 `tests/momentum/Analysis/test_ic_persist_redirect_isolation.py`**：

| Case | 作法 | 預期 |
|------|------|------|
| I1 non-opt-in | 跑固定 canary：`tests/governance/test_verify_gate.py::test_handoff_*`（1 個）+ `tests/feature_engineering/test_failopen_contract.py`（1 個）+ `tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_resolve_expected_freq` | `redirect_install_count==0`；`production_spy` 空 |
| I2 opt-in |  parametrized 覆蓋 **每個 Seam S1–S11** 最小觸發 | 每 seam `redirect_hits>=1`；寫入只在 `redirect_root` |
| I3 靜態回歸 | `test_ic_persist_redirect_inventory.py`：`rg` 比對 §COVERAGE REDIRECT 表 vs repo | 缺 marker/fixture → FAIL |

- **禁止** Task 1.2 式 `collect-only | grep ic_persist_redirect` 當隔離證明（codex B5：collect 本身寫 inventory）。

---

## §P Phase 與依賴

### Phase 1 — redirect 工具 + seam 單測（無依賴）

**Task 1.1** `tests/fixtures/ic_persist_redirect.py` + plugin + 三處 conftest（見 §SEAM）。

**Task 1.2** `test_ic_persist_redirect_unit.py`：parametrize S1–S11；每 case 斷言 `production_spy` 空 + 預期檔在 `redirect_root`。

**驗證**：`pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` → `≥11 passed`。

### Phase 2 — 掛載 §COVERAGE 全表 REDIRECT（依賴 Phase 1）

- IC-01..12、API-01..07（含 export h5py 改測試側）、ML-01..06、FF-01。
- **無 Phase 4**；models/FF 與 IC 同批 merge。

**驗證**：見 §V V1–V3。

### Phase 3 — Hermetic + mutation + isolation + golden AB（依賴 Phase 2）

見 §V、§ISOLATION、§G。

### Phase 4 — MANUAL generator 文件（依賴 Phase 3）

- GEN-* 腳本頂部註明：須 `IC_PERSIST_REDIRECT_ROOT=/tmp/...` 或等價 env；跑前後 `digest_data_cache` 手動 receipt。
- **不** pytest autouse。

---

## §V 驗證策略（回應 grok B-3/B-4 / codex B3）

### Digest oracle（唯一主證明）

```python
def digest_data_cache(root: Path = Path("data_cache")) -> dict[str, str]:
    """relpath -> sha256(file_bytes)；目錄不存在 → {}。"""
```

- 掃描範圍：`data_cache/features/`、`data_cache/reports/`（含 `ic_ingest_cache/`）、`data_cache/models/`。
- **禁止** path+size、mtime-only、新增檔集合-only（b6 式）、`agent_postflight` 檔案數/KB。

### 外層 harness（`test_ic_data_cache_hermetic.py`）

- **同檔**內順序（非「pytest 內再 pytest V1」空殼）：
  1. `before = digest_data_cache()`
  2. 呼叫 `run_redirect_suite()`（in-process importlib 跑 §V V1 nodeid 子集，已掛 redirect）
  3. `after = digest_data_cache()` → `assert before == after`；stdout `DIGEST_DIFF_EMPTY=1`
- V5 postflight 僅可作 **輔助**；SPEC 驗收 **不以** V5 為 PASS 條件。

### Mutation 協議（同檔 `test_mutation_redirect_disabled_caught`）

1. **Baseline 綠**：完整 redirect + digest 空 diff。
2. **Remove redirect**：對 **fake_prod**（`tmp_path/fake_prod_data_cache`）安裝 spy，跑最小 IC-01 路徑；斷言 `fake_prod` digest 非空、`real data_cache` digest 不變。
3. **Restore redirect**：再跑 → digest 空 diff。
- **禁止**對真實 `data_cache/` 故意污染；**禁止** `RUN_IC_PERSIST_MUTATION=1` 才跑（預設 CI 必跑 mutation case）。
- Exit contract：`pytest …::test_mutation_redirect_disabled_caught -q` → **`1 passed`**（非 xfail、非「expected fail」）。

### 驗收集

| # | 命令 | 通過條件（精確 exit contract） |
|---|------|-------------------------------|
| V1 | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_fallback_insufficient_data_marks_applied_false tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_applied_true_when_sufficient tests/momentum/test_ic_e2e.py tests/momentum/test_ic_feature_filter.py::test_analyze_applies_feature_filter_metadata_and_summary_limit tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q` | **`10 passed, 0 skipped, 0 failed`**（e2e perf 未設 env 時 `1 skipped` 允許且須 **顯式**為 `test_performance_800_features` 單一 skip，其餘 0 skipped） |
| V2 | `venv/bin/python -m pytest tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis tests/api/test_ic_analysis_service.py::test_resolve_run_path_contains_config_hash -q` | **`2 passed, 0 skipped, 0 failed`** |
| V3 | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_data_cache_hermetic.py -q` | **`2 passed`**（hermetic + mutation）；stdout 含 `DIGEST_DIFF_EMPTY=1` |
| V4 | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_isolation.py -q` | **`≥3 passed`** |
| V5 | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q` | golden **`2 passed`** + AB **`1 passed`**；含 `ab_hash=` |
| V6 | `venv/bin/python -m pytest tests/api/test_ic_analysis_api.py tests/api/test_export_api.py tests/api/test_ic_deep_analysis.py -q` | **`≥30 passed, 0 failed`**（API 鏈全綠） | VERIFY-EXEMPT:draft-superseded:p2debt-t2
| V7 | `venv/bin/python -m pytest tests/test_feature_factory_e2e.py tests/momentum/Analysis/test_lightgbm_analyzer.py tests/momentum/Analysis/test_xgboost_protocol_methods.py -q` | FF+ML：**`passed` 數 ≥ collect 數 − 明確 data-missing skip 數**；skip 僅限 `_require_data` / 無 kline；**0 failed** |
| V8 | `grep -r "from api\." momentum/` | **0** results |
| V9（輔助，非主證明） | `bash scripts/agent_preflight.sh /tmp/p2debt-t2-pre.txt && <V1> && bash scripts/agent_postflight.sh /tmp/p2debt-t2-pre.txt` | 不縮減；**不可替代** V3 digest |

- **防假綠**：不得刪弱 cut1/golden 斷言；不得將 REDIRECT 列改 `skip`；V1/V2 **禁**「0 failed」取代 passed-count。

---

## §R 回退

- Phase 1–3 各一 commit（`test:` 前綴）；V3 digest 失敗 → 不 merge。
- Revert = 移除 fixture + 測試掛載；生產 code 無變更。

---

## §N 不適用 / 範圍外

- **feature/kline 三方簽核**：不適用（不改 FF 計算語意）。
- **long_short / phase25/26 analyzer**：非 IC persist，列 N/A。
- **performance benchmark 腳本**（`tests/performance/`）：非 CI 預設；列 READ/MANUAL。

---

## R2-CLOSURE: finding → 閉合位置

| Finding ID | 來源 | 閉合 |
|------------|------|------|
| grok BLOCKING-1 | API polluters 漏表 | §COVERAGE API-01..07；Phase 2 全掛；V6 |
| grok BLOCKING-2 | redirect 繞過 h5py/transforms | §SEAM S1–S11；S9 export 直接 h5py；S6 transforms |
| grok BLOCKING-3 | hermetic/V5 假綠 | §V digest oracle；V5 降級輔助；禁 b6/postflight 主證明 |
| grok BLOCKING-4 | mutation 未閉合 | §V mutation 三態；fake_prod；預設 CI；exit `1 passed` |
| grok BLOCKING-5 | API fixture 掛載 | §SEAM conftest 三檔 + `usefixtures` + session fixture 顯式參數 |
| grok MINOR-1 | 大小應為大 | §RISK **大** + 白話簡述 + 雙家族閉合條款 |
| grok MINOR-2 | RISK scope 偏窄 | §RISK (b) 擴至 API/FF/models；§COVERAGE 全集 |
| grok MINOR-3 | 票 5 劃界 | §G A/B oracle；V5 `2 passed`；條件式不升級 |
| grok MINOR-4 | opt-in 無強制 | §ISOLATION I3 靜態 inventory 測試 |
| grok MINOR-5 | models defer | §COVERAGE ML-* 入 REDIRECT；撤 Phase 4 defer |
| codex B1 | 覆蓋非全集 | §COVERAGE A–G 全表；修正 split/oos stub 列 STUB |
| codex B2 | redirect 不可執行 | §SEAM 具名 patch + injectable root + spy + conftest |
| codex B3 | §V 可假綠 | §V digest + 外層 harness + mutation + V1/V2 exit |
| codex B4 | golden 僅條件聲稱 | §G A/B oracle；V5 passed-count + ab_hash |
| codex B5 | 隔離 gate 無效 | §ISOLATION I1–I3；禁 collect grep 證明 |
| codex B6 | RISK 大小錯 | §RISK 大 + 白話 + 雙家族條款 |
| codex M1 | §G/V 矛盾 | V1/V5 統一 **`N passed`** + digest/ab_hash receipt |

---

ASSUMPTIONS_VERIFIED: 16 analyze-caller 檔；3 API POST analyze 檔；export h5py L125-137；stage7 內唯一 persist；path+size 假綠；postflight 只擋縮減；b6 只擋新 features 檔；momentum conftest 缺失；102 collect-only；split/oos flag_toggles stub 不寫；FF e2e persist=True  
TESTS_RUN: `rg`/`sed`/`test -f`/collect-only 如上；**未**跑 polluting pytest body  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（僅 R2 檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  

**產出檔**：`handoffs/P2DEBT-T2-SPEC-DRAFT-R2.md`

STATUS: DONE
