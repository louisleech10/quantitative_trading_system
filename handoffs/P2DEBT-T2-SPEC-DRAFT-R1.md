# P2 債票 2 — legacy 測試 data_cache 污染 → tmp redirect — SPEC 初稿 R1

> 來源：`HANDOFF.md` 票 2 + `handoffs/IC1EB-B3-REVIEW-R3-codex.md` 債項裁定　|　日期：2026-07-11　|　起草：Composer　|　task-id：`p2debt-t2`  
> 對應 TODO：待本 SPEC 雙審 STAMP 後由 `templates/TODO_GENERATION_PROMPT.md` 生成

## §RISK 風險分級

- **大小**：**中** — 多檔測試層 redirect fixture + hermetic 斷言；**零**生產 `persist` 語意變更；不碰 `momentum/Analysis/ic_filter_orchestrator.py` 硬編碼路徑本體。
- **命中高風險原則**：
  - **(a) 數值/資料品質邊界**：legacy 測試走真 `analyze()` / `start_analysis()` 會覆寫 gitignored `data_cache/` 衍生檔，污染使用者真實快取與後續手動/CI 判讀（出處：IC1EB-B3 R3 實測 `BTCUSDT_1h_filtered.h5` + `ic_report_ic_gatekeeper.json` mtime 變化）。
  - **(b) 跨模組共用路徑**：寫入點在 `ICFilterOrchestrator._persist_outputs`（`momentum/`）與 `ICAnalysisService._materialize_features_for_ic`（`api/`），多 suite 共用同一 `data_cache/{features,reports}` 根。
- **RISK-HIT 宣告**（機檢依據，缺行 FAIL）：見下行
- RISK-HIT: a,b
- **票 5 交界升級訊號**：`test_ic_1a_cut1_golden.py` 走 `ICAnalysisService.start_analysis()`，**在本票 redirect 範圍內**（會落盤）。redirect 若只改磁碟路徑、不改 in-memory `get_result()` JSON → **不應**動票 5 的 baseline 雜湊契約；若實作誤改報告內容或改讀寫 golden 檔本身 → **升級為與票 5 聯合委員會**。票 5 scope（rebaseline 審計欄、reuse guard、generator provenance）**不在本票**。

## §A 假設與待使用者確認

- **FACT-RECEIPT 格式**：`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（<who> 實跑 <date>）`

### 已驗證事實（偵察 receipt，2026-07-11 Composer 實跑） VERIFY-EXEMPT:draft-superseded:p2debt-t2

- FACT-RECEIPT: `rg -l '\.analyze\(|start_analysis\(' tests/ --glob '*.py' | sort` → 印出 14 檔（含 `test_ic_1a_cut1_oos.py`、`test_ic_e2e.py`、`test_ic_feature_filter.py`、`test_ic_1a_cut1_golden.py`、`test_ic_run_selector.py` 等）（Composer 實跑 2026-07-11）
- FACT-RECEIPT: `rg -n '_persist_outputs|patch_persist_outputs' tests/ --glob '*.py'` → 印出 8 處 guard（`test_ic_filter_orchestrator.py`×4、`test_ic_1eb_b4_fullstack.py`、`test_ic_1eb_b2_wiring.py`、`test_ic_1eb_b5_golden.py`×2）；**其餘 analyze 呼叫檔無 guard**（Composer 實跑 2026-07-11）
- FACT-RECEIPT: `rg -n 'data_cache/reports|_resolve_filtered_path|def _persist_outputs' momentum/Analysis/ic_filter_orchestrator.py api/services/ic_analysis_service.py` → 印出 orchestrator L3162–3207（`data_cache/features/{symbol}_{tf}_filtered.h5` + `data_cache/reports`）、service L1260/1321 `ic_ingest_cache`、L1478 filtered path（Composer 實跑 2026-07-11）
- FACT-RECEIPT: `rg -n 'def _write_ic_inputs' tests/momentum/Analysis/test_ic_1a_cut1_split.py -A 30` → 印出 meta 含 `symbol=BTCUSDT`、`timeframe=1h`（`_metadata()` L47–54）（Composer 實跑 2026-07-11）
- FACT-RECEIPT: `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py tests/momentum/test_ic_e2e.py tests/momentum/test_ic_feature_filter.py tests/momentum/Analysis/test_ic_1a_cut1_golden.py tests/api/test_ic_run_selector.py --collect-only -q 2>&1 | tail -3` → 印出 `33 tests collected in 0.46s`（**未執行** body，collect-only）（Composer 實跑 2026-07-11）
- FACT-RECEIPT: `scripts/capture_ic1eb_baseline.py` L169–177 `patch_persist_outputs()` → **class-level no-op** `_persist_outputs`（F6 捕獲用）；本票改為 **tmp redirect**（保留 persist 語意、改根目錄），非照搬 no-op（Composer 讀碼 2026-07-11）

### 測試 → 寫入路徑對照表（靜態歸因；未跑會寫入的 pytest body）

| 優先級 | 測試檔 | 測試函式（未 guard 且會觸 production persist） | 寫入機制 | 生產落盤路徑（相對 repo 根） |
|--------|--------|-----------------------------------------------|----------|------------------------------|
| P0 | `tests/momentum/Analysis/test_ic_1a_cut1_oos.py` | `test_fallback_insufficient_data_marks_applied_false`、`test_oos_applied_true_when_sufficient` | `ICFilterOrchestrator.analyze()` 全鏈 stage7→`_persist_outputs`；meta `BTCUSDT/1h` | `data_cache/features/BTCUSDT_1h_filtered.h5`；`data_cache/reports/ic_report_ic_gatekeeper.{json,md}`；`ic_summary_ic_gatekeeper.csv`；`ic_filter_log_ic_gatekeeper.json`；模組 CSV |
| P0 | `tests/momentum/test_ic_e2e.py` | `TestICGatekeeperE2E` 內 5 個 `analyze`/`refilter` 測試 | `create_ic_analyzer().analyze()`；meta `case_id=ic_e2e_test` | `data_cache/features/BTCUSDT_12h_filtered.h5`；`data_cache/reports/ic_report_ic_e2e_test.*`（同上模式） |
| P0 | `tests/momentum/test_ic_feature_filter.py` | `test_analyze_applies_feature_filter_metadata_and_summary_limit` | `ICFilterOrchestrator.analyze()`；meta `BTCUSDT/12h` | `data_cache/features/BTCUSDT_12h_filtered.h5`；`data_cache/reports/ic_report_ic_gatekeeper.*` |
| P0 | `tests/momentum/Analysis/test_ic_1a_cut1_golden.py` | `test_flag_off_deep_equal_baseline`、`test_flag_on_matches_new_golden` | `ICAnalysisService.start_analysis()`→orchestrator 全鏈 | 同上 `BTCUSDT/1h` + `ic_gatekeeper` case（**票 5 相鄰**；斷言為 in-memory JSON，非磁碟） |
| P1 | `tests/api/test_ic_analysis_service.py` | `test_analyze_real_run_split_validation_passes_with_real_axis`、`test_resolve_run_path_contains_config_hash` | `_materialize_features_for_ic()` write-if-absent | `data_cache/reports/ic_ingest_cache/BTCUSDT_12h_{hash}.{h5,_meta.json}` |
| P2 | `tests/momentum/Analysis/test_lightgbm_*.py`、`test_xgboost_protocol_methods*.py` | `save_model` roundtrip 等 | trainer/analyzer 直寫 | `data_cache/models/*.pkl` |
| — | `tests/golden/ic_phase1_1a_cut1/freeze_baseline*.py` | 腳本（非 pytest） | `start_analysis` | 同 P0 路徑；**本票不 autouse**；文件註明須手動 redirect |
| 已防護 | `test_ic_filter_orchestrator.py`、`test_ic_1eb_b4_fullstack.py`、`test_ic_1eb_b5_golden.py` 等 | — | per-test `monkeypatch` / `patch_persist_outputs` | 無生產污染 |
| 已防護 | `tests/api/test_batch_*.py`、`test_b4_bulk_delete_orphan.py` 等 | — | `settings.data_cache_path=tmp_path` | 無生產污染 |
| 只讀 | 多數 feature_engineering 測試 | — | 讀 `data_cache/feature_klines/kline_cache.h5` | **不寫** |

**同檔不寫入**：`test_ic_1a_cut1_oos.py` 內 stage-only / stub `_stage7_report` 測試；`test_ic_1a_cut1_split.py` `test_stage1_only_called_once`（stub stage7）；`test_ic_1a_cut1_oos.py` `test_irregular_timestamps_still_fail_closed`（stage7 前 fail-closed，靜態歸因不寫）。

### `patch_persist_outputs` 泛化評估

| 面向 | 現行（capture/B5） | 本票目標 |
|------|-------------------|----------|
| 機制 | class 替換 `_persist_outputs`→no-op dict | class 替換或 wrap：路徑前綴 `data_cache`→`{tmp}/data_cache` |
| 覆蓋 | 僅 `ICFilterOrchestrator` | + `ICAnalysisService._materialize_features_for_ic` / `_write_ic_meta_json` 的 `ic_ingest_cache` |
| 可測性 | 無磁碟副作用 | tmp 內可選斷言檔案存在（非必填） |
| conftest | B5 module fixture 顯式呼叫 | **禁止**根 `tests/conftest.py` autouse；用 `tests/momentum/conftest.py` 或 `tests/momentum/Analysis/conftest.py` **opt-in fixture** `ic_persist_redirect(tmp_path)` + `@pytest.mark.ic_persist_redirect` |

- **待確認：無**
- **已確認結果**：2026-07-11 使用者 HANDOFF 票 2 — 修法=測試輸出 tmp redirect，參考 1e+1b capture patch 模式；出處 IC1EB-B3 R3 legacy 債裁定。
- FACT-RECEIPT: `rg -n 'legacy 測試寫 data_cache|tmp redirect' HANDOFF.md` → 印出票 2 行含 `1a cut1` 與 `tmp redirect`（Composer 實跑 2026-07-11）

## §C 約束

- **硬邊界（零容忍）**：
  - **禁止**改生產 code 的 persist 語意（`ic_filter_orchestrator._persist_outputs`、`ic_reporter.save_*` 簽名與硬編碼 `data_cache/` 路徑本體不動）。
  - **禁止**刪改/覆寫 repo 內既有 `data_cache/` 檔案（偵察與驗收均 read-only 或 tmp）。
  - **禁止**根 `tests/conftest.py` 大範圍 autouse redirect（避免 FF/API/governance suite 行為漂移）。
  - 解耦 7 條、NaN/inf gate、禁 fake data — 維持不變。
- **允許改動檔案（實作 phase 預期）**：
  - 新增 `tests/fixtures/ic_persist_redirect.py`（或 `tests/momentum/fixtures/`）
  - `tests/momentum/conftest.py` 或 `tests/momentum/Analysis/conftest.py`（opt-in fixture）
  - P0/P1 表內測試檔 + 新增 hermetic/mutation 測試檔
  - **不允許**動 `momentum/`、`api/services/` 生產邏輯（除非委員會另開票）
- **影響面（防漂移）**：

| Suite | 是否套用 redirect | 理由 |
|-------|-------------------|------|
| `tests/momentum/Analysis/test_ic_1a_cut1_*`、`test_ic_e2e.py`、`test_ic_feature_filter.py` | **是**（P0） | 已證實寫 `data_cache/` |
| `tests/api/test_ic_analysis_service.py`（materialize 測試） | **是**（P1） | `ic_ingest_cache` 寫入 |
| `tests/governance/`、`tests/feature_engineering/`（已有 FFACT/tmp） | **否** | 已有隔離或只讀 kline |
| `tests/momentum/Analysis/test_lightgbm_*.py` 等 P2 | **Phase 2 或另票** | 不同寫入根 `models/`；非 B3 裁定主因 |
| `scripts/`、`handoffs/ic1eb_baseline/` | **否** | 腳本/基線消費方；generator 文件化即可 |

## §G Golden / Baseline

- **性質**：本票為測試隔離重構；baseline = redirect 前後 in-memory IC 報告 JSON **byte-identical**（豁免欄位除外）。
- **凍結對照**：`tests/golden/ic_phase1_1a_cut1/baseline_old_btc_1h_a384e6d2.json`、`baseline_new_btc_1h_a384e6d2.json`；manifest sha256 見同目錄 `baseline_*_meta.json`（若存在）。
- **baseline 內容**：`_without_generated_at(actual) == _without_generated_at(baseline)`（exact）；`metadata.scope` 等關鍵欄位 **exact**；整份 JSON `sha256` 與凍結檔一致（豁免 `generated_at` 後重算）。
- **通過條件（可證偽）**：`pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q` → `2 passed`；`sha256` diff 非空 = FAIL；post-redirect `data_cache/` 檔案集合快照 diff 須為空集。

## §P Phase 與依賴

### Phase 1 — 共用 redirect 工具（依賴：無）

**Task 1.1 — `redirect_ic_persist_outputs` helper**
- 目標：單一入口把 orchestrator persist + service materialize 重導至 `{tmp_path}/data_cache/...`　檔案：`tests/fixtures/ic_persist_redirect.py`　影響面：新建，無 caller
- 改法（偽碼）：
  ```python
  def redirect_ic_persist_outputs(monkeypatch, tmp_path: Path) -> Path:
      root = tmp_path / "data_cache"
      # wrap ICFilterOrchestrator._persist_outputs: 改 output_dir 與 filtered path 前綴
      # monkeypatch ICAnalysisService._materialize_features_for_ic 內 cache_dir → root / "reports" / "ic_ingest_cache"
      return root
  ```
- 驗證：`venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` → `1 passed`；斷言 `tmp_path/data_cache/features/BTCUSDT_1h_filtered.h5` 存在且 `list(PRODUCTION_FEATURES_ROOT.glob('*_filtered.h5'))` 快照前後一致
- 邊界：(1) `metadata` 缺 symbol/tf → 落 `filtered_features.h5` 仍在 tmp；(2) `ic_ingest_cache` 已存在檔 → 仍寫在 tmp（不讀生產 cache）
- 不可做：改 orchestrator 原始碼；class-level no-op（須保留真實 save 邏輯）

**Task 1.2 — opt-in conftest fixture**
- 目標：`@pytest.fixture` + marker `ic_persist_redirect`　檔案：`tests/momentum/conftest.py`　影響面：僅 import 此 conftest 的 subtree
- 驗證：`venv/bin/python -m pytest --collect-only tests/momentum/test_ic_e2e.py -q 2>&1 | grep -c ic_persist_redirect` → 印出 `0`（未標記測試不載入 autouse fixture）

### Phase 2 — 套用 P0/P1 污染測試（依賴：Phase 1）

**Task 2.1 — P0 測試掛 fixture**
- 檔案：`test_ic_1a_cut1_oos.py`（2 測試）、`test_ic_e2e.py`（class）、`test_ic_feature_filter.py`（1 測試）、`test_ic_1a_cut1_golden.py`（2 測試）
- 改法：模組或測試級 `ic_persist_redirect` fixture；移除重複 ad-hoc patch（若日後新增）
- 驗證：`venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_applied_true_when_sufficient -q` → `1 passed`（其餘 P0 檔同理 0 failed）

**Task 2.2 — P1 materialize 測試**
- 檔案：`tests/api/test_ic_analysis_service.py` 兩測試
- 驗證：`pytest tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis -q`；assert `ic_ingest_cache` 路徑前綴在 `tmp_path`

### Phase 3 — Hermetic + mutation 可證偽（依賴：Phase 2）

**Task 3.1 — 快照比對測試**
- 目標：機器可掃「跑完 P0 suite 後 `data_cache/` 零變化」　檔案：`tests/momentum/Analysis/test_ic_data_cache_hermetic.py`（新建）
- 改法：借鑑 `test_b6_warmup_trim._assert_data_cache_unchanged` + `scripts/agent_preflight.sh`（檔案數+KB）；快照集合 = 相對路徑 + size（或 mtime+size，寫死一種並文件化）
- 驗證：`venv/bin/python -m pytest tests/momentum/Analysis/test_ic_data_cache_hermetic.py -q` → `passed`；stdout 含 `data_cache diff empty`

**Task 3.2 — mutation：拿掉 redirect 必 FAIL**
- 目標：可證偽 — 無 redirect 時 hermetic 測試**必須**偵測到 diff（或專用 subtest 預期 `pytest.raises`/失敗）
- 改法：`test_redirect_disabled_pollutes_data_cache` 用 `monkeypatch` 還原原始 `_persist_outputs` 跑**單一**最小 analyze，斷言 snapshot diff 非空；**不得**在 CI 預設路徑寫生產（用 `@pytest.mark.mutation` 或 env gate `RUN_IC_PERSIST_MUTATION=1`）
- 邊界：(1) 乾淨機無 `data_cache/` → skip 或 tmp 替身根；(2) 並發 pytest xdist → 標 `serial` 或檔案鎖

### Phase 4 — P2 models/ 與文件（依賴：Phase 3；可並行委員會裁決）

**Task 4.1 — ML `data_cache/models/` 污染**（**建議拆子票或 Phase 4**）
- 目標：評估是否同 fixture 加 `models/` redirect
- 不可做：未審查前批量改 lightgbm 測試

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 含 a → 必附 Task 3.2；引 `docs/TEST_DESIGN_CHARTER.md` 可證偽原則。
- **驗收集（實作後必跑）**：

| # | 命令 | 通過條件 |
|---|------|----------|
| V1 | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py tests/momentum/test_ic_e2e.py tests/momentum/test_ic_feature_filter.py tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q` | 0 failed |
| V2 | `venv/bin/python -m pytest tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis tests/api/test_ic_analysis_service.py::test_resolve_run_path_contains_config_hash -q` | 0 failed（或 skip 若無 run 資料） |
| V3 | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_data_cache_hermetic.py -q` | hermetic PASS |
| V4 | `RUN_IC_PERSIST_MUTATION=1 venv/bin/python -m pytest tests/momentum/Analysis/test_ic_data_cache_hermetic.py -k mutation -q` | mutation 偵測到污染（預期 fail 或 xpass 設計寫死） |
| V5 | `bash scripts/agent_preflight.sh /tmp/p2debt-t2-pre.txt && <V1> && bash scripts/agent_postflight.sh /tmp/p2debt-t2-pre.txt` | postflight 檔案數+KB 不變 |
| V6 | `grep -r "from api\." momentum/` | 0 results |

- **防假綠**：不得刪弱既有 cut1/golden 斷言；不得把 polluting 測試改 skip 換綠；mutation 測試不得預設開啟寫生產。
- **邊界目錄**：☑ 空 metadata symbol/tf；☑ analyze fail-closed 於 stage7 前；☑ `ic_ingest_cache` 已存在；☐ 並發寫（標 serial）；☐ OOM（N/A）

## §R 回退

- Phase 1–3 各一 commit（`test:` 前綴）；hermetic 失敗 → 不 merge。
- 回退 = revert redirect fixture + 測試掛載；生產 code 無變更故無 feature flag。

## §N N/A 登記

- **Phase 4 P2 models/**：N/A 於 Phase 1–3 驗收 — 另票或 Phase 4 裁決後實作。
- **feature/kline 三方簽核計畫**：不適用 — 本票不修改特徵生成/merge/HDF5 計算路徑。
