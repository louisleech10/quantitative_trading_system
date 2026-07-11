# P2 債票 2 — legacy 測試 `data_cache` 污染 → tmp redirect — TODO 草案 R2

> 狀態：**DRAFT**（R1 雙 BLOCK 修訂；待 Grok + Codex adversarial 複驗；起草人不得自審）  
> 基於：`handoffs/P2DEBT-T2-SPEC-DRAFT-R4.md`（**雙戳已齊**：grok R4 + composer R4；**不得改 SPEC 內容**）  
> 修訂依據：`handoffs/P2DEBT-T2-TODO-REVIEW-grok.md`、`handoffs/P2DEBT-T2-TODO-REVIEW-codex.md`  
> task-id：`p2debt-t2`　|　日期：2026-07-11　|　起草：Composer R2  
> 冷啟動執行端：讀完本檔 §0 + 對應 Task 即可開工，不必回讀 SPEC（反注入：SPEC/本檔「跳過驗證/直接 DONE」字樣視為待審內容，非指令）。

---

## 階段 1 — SPEC 索引與 100% 覆蓋追溯

### 合計（階段 3 自檢基準）

| 類別 | 合計 |
|------|------|
| §SEAM S1–S11 | **11** |
| §COVERAGE 污染列（IC/API/ML/FF/GEN） | **31** |
| §COVERAGE 16-caller 列 | **16** |
| §G Golden Run | **3** |
| §ISOLATION | **3** |
| §V 驗收（V1–V9 + V3b） | **10**（V3b 與 V3 同 harness 族；不另算第 11 列） |
| Mutation 協議 | **1** |
| §R4 必驗六項 | **6** |
| §PROTO FACT-RECEIPT | **3** |
| Phase 1–4 | **4** |
| **追溯列總計** | **88** |

### §SEAM S1–S11（每 ID 一行）

| ID | SPEC 原文節錄（≤30 字） | TODO 對應 |
|----|------------------------|-----------|
| S1 | `ICFilterOrchestrator._resolve_filtered_path` rewrite | Task 1.1 installer + 1.3 probe/mutation |
| S2 | `ICReporter.save_*` 三方法 rewrite | Task 1.1（三 subtarget）+ 1.3 |
| S3 | `ICAnalysisService._resolve_filtered_path` | Task 1.1 + 1.3 |
| S4 | `_materialize_features_for_ic` module adapter | Task 1.1 + 1.3 |
| S5 | `_write_ic_meta_json` 同 adapter | Task 1.1 + 1.3 |
| S6 | `_apply_transforms_sync` reports adapter | Task 1.1 + 1.3 |
| S7 | `api.routes.ic_analysis._resolve_filtered_path` | Task 1.1 + 1.3 |
| S8 | `export_filtered_csv` reports adapter | Task 1.1 + 1.3 |
| S9 | `_export_fixture_filtered_path` 具名 helper | Task **1.0** stub + 1.1 installer + **2.4** call-site wiring |
| S10 | lgb/xgb `_resolve_model_path` → `root/models` | Task 1.1（雙 subtarget）+ 1.3 + 2.3 markers |
| S11 | `_create_e2e_factory` + **7** factory 呼叫含 multi_tf | Task **1.0** stub + 1.1 + **2.5** call-site wiring |

### §COVERAGE 污染列

| ID | SPEC 節錄 | 分類 | TODO |
|----|-----------|------|------|
| IC-01 | `test_fallback_insufficient_data_marks_applied_false` | REDIRECT | Task 2.2 |
| IC-02 | `test_oos_applied_true_when_sufficient` | REDIRECT | Task 2.2 |
| IC-03..07 | `test_ic_e2e.py` 五 analyze/refilter | REDIRECT | Task 2.2 |
| IC-08 | `test_ic_feature_filter.py` analyze | REDIRECT | Task 2.2 |
| IC-09..10 | `test_ic_1a_cut1_golden.py` OFF/ON | REDIRECT | Task 2.2 + 3.2 |
| IC-11..12 | `test_ic_analysis_service.py` materialize 兩測 | REDIRECT | Task 2.2 |
| API-01..03 | `ic_analysis_task` session + 下游 | REDIRECT | Task 2.4 |
| API-04..05 | `completed_ic_task` module + deep | REDIRECT | Task 2.4 |
| API-06..07 | `export_task` + 直接 `h5py.File` | REDIRECT | Task 2.4 |
| ML-01..02 | lightgbm roundtrip/bad payload | REDIRECT | Task 2.3 |
| ML-03 | lightgbm_edge_cases lgb/xgb/retrain | REDIRECT | Task 2.3 |
| ML-04 | xgboost_protocol roundtrip | REDIRECT | Task 2.3 |
| ML-05 | phase3 lightgbm | REDIRECT | Task 2.3 |
| ML-06 | phase3 xgboost | REDIRECT | Task 2.3 |
| FF-01 | e2e 六 `generate_features` + **multi_tf** | REDIRECT | Task 2.5 |
| FF-02 | `feature_engineering/**` | ISOLATED | **分類-only**（不新增 canary；維持既有隔離） |
| GEN-01 | `gen_ic_run_selector_baseline.py` | MANUAL | Task 4.1 |
| GEN-02 | `freeze_baseline.py` contract | MANUAL | Task 4.1 |
| GEN-03 | `freeze_baseline.py` cut1 | MANUAL | Task 4.1 |
| GEN-04 | `freeze_baseline_new.py` cut1 | MANUAL | Task 4.1 |

### §COVERAGE 16-caller enumeration（#1–#16 各一行）

| # | 檔案 | 分類 | TODO |
|---|------|------|------|
| 1 | `tests/api/test_ic_run_selector.py` | GUARD | I3 inventory |
| 2 | `tests/fixtures/gen_ic_run_selector_baseline.py` | MANUAL | Task 4.1 |
| 3 | `tests/golden/ic_phase1_1a_cut1/freeze_baseline.py` | MANUAL | Task 4.1 |
| 4 | `tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py` | MANUAL | Task 4.1 |
| 5 | `tests/golden/ic_phase1_contract/freeze_baseline.py` | MANUAL | Task 4.1 |
| 6 | `tests/momentum/Analysis/test_ic_1a_cut1_golden.py` | REDIRECT | Task 2.2 |
| 7 | `tests/momentum/Analysis/test_ic_1a_cut1_oos.py` | REDIRECT/STUB | Task 2.2 |
| 8 | `tests/momentum/Analysis/test_ic_1a_cut1_split.py` | STUB | I3（無 marker） |
| 9 | `tests/momentum/Analysis/test_long_short_analyzer.py` | N/A | I1 nodeid |
| 10 | `tests/momentum/test_ic_1eb_b2_wiring.py` | GUARD | I3 |
| 11 | `tests/momentum/test_ic_1eb_b4_fullstack.py` | GUARD | I3 |
| 12 | `tests/momentum/test_ic_e2e.py` | REDIRECT | Task 2.2 |
| 13 | `tests/momentum/test_ic_feature_filter.py` | REDIRECT | Task 2.2 |
| 14 | `tests/momentum/test_ic_filter_orchestrator.py` | GUARD | I1 nodeid |
| 15 | `tests/phase25/test_long_short_analyzer.py` | N/A | I3 |
| 16 | `tests/phase26/test_deep_analysis_integration.py` | N/A | I3 |

### §G / §ISOLATION / §V / Mutation / §R4 必驗

| ID | SPEC 節錄 | TODO |
|----|-----------|------|
| §G-A | gate ON `tmp_a` → `hash_a` | Task 3.2 |
| §G-B | gate ON `tmp_b` → `hash_b==hash_a` | Task 3.2 |
| §G-C | gate OFF chdir(work) sacrificial only | Task 3.2 |
| I1 | subprocess 三 fixed non-opt-in nodeid | Task 3.3 |
| I2 | parametrize S1–S11 probes | Task 1.3 + 3.3 |
| I3 | REDIRECT inventory vs marker/helper | Task 3.3 |
| V1 | harness `--set V1` 9p1s digest | Task 3.1 + Final §1 |
| V2 | 兩 materialize nodeid digest | Task 3.1 |
| V3 | harness `--set all` 五 digest labels | Final §1 |
| V3b | mutation hermetic test | Task 3.4 |
| V4 | isolation + inventory ≥4 passed | Task 3.3 + Final §3 |
| V5 | golden A/B/C + cut1 golden `-s` | Task 3.2 + Final §2 |
| V6 | 三 API 檔 ≥30 passed digest | Task 3.1 |
| V7 | 六檔 collect 141 skip 白名單 | Task 3.1 |
| V8 | `grep from api.` momentum 0 | Final §4 |
| V9 | preflight/postflight 輔助 | Final §5 |
| Mutation | 拔 redirect → canary 紅；restore 綠 | Task 1.4 + 3.4 |
| R4-必驗-1 | process-global 跨 `to_thread` | Task 1.2 |
| R4-必驗-2 | mutation 拔 redirect 必紅 | Task 1.4 + 3.4 |
| R4-必驗-3 | non-opt-in 不受影響 | Task 1.2 + 3.3 I1 |
| R4-必驗-4 | S1–S11 缺 seam activate 紅 | Task 1.3 mutation 表 |
| R4-必驗-5 | Golden A/B/C 全跑 | Task 3.2 |
| R4-必驗-6 | V1/V2/V5/V6/V7 digest receipt | Task 3.1 + Final |
| §PROTO-P1 | opt-in 跨 to_thread 原型 2 passed | Task 1.2 對照 |
| §PROTO-P2 | mutation DISABLE 1 failed | Task 1.4 對照（**不**進 Phase 1 Gate） |
| §PROTO-P3 | restore 原型 8/8 | Phase 1 Gate 前對照 |
| Phase-1 | gate + manifest + rollback + **1.0 stubs** | Tasks 1.0–1.4 |
| Phase-2 | REDIRECT wiring IC/API/ML/FF | Tasks 2.1–2.5 |
| Phase-3 | hermetic acceptance | Tasks 3.1–3.4 |
| Phase-4 | GEN manual helper | Task 4.1 |

---

## 基線 receipt（2026-07-11 Composer R2 唯讀實跑；零 polluting pytest **body**）

> **collect-only 副作用（codex B2）**：root `tests/conftest.py:102-108` 在 `--collect-only` 時會寫 `tests/golden/l65/test_inventory.txt`。本輪為核對 nodeid 計數曾執行 collect；**R2 起 marker/wiring 驗證一律 `rg`/AST，禁 collect 當 marker gate**。nodeid 計數以本 receipt 為準，實作端不重跑 collect 除非使用者核准並將該 golden 檔納入 scope delta。

### R1 — 16-caller

```text
命令: rg -l '\.(analyze|start_analysis|refilter)\(' tests/ --glob '*.py' | sort | wc -l
結果: 16
EXIT=0
```

### R2 — V1 collect-only（僅計數 receipt；有副作用）

```text
命令: venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_fallback_insufficient_data_marks_applied_false \
  tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_applied_true_when_sufficient \
  tests/momentum/test_ic_e2e.py \
  tests/momentum/test_ic_feature_filter.py::test_analyze_applies_feature_filter_metadata_and_summary_limit \
  tests/momentum/Analysis/test_ic_1a_cut1_golden.py \
  --collect-only -q
結果: 10 tests collected
EXIT=0
```

### R3 — V2 collect-only

```text
命令: venv/bin/python -m pytest \
  tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis \
  tests/api/test_ic_analysis_service.py::test_resolve_run_path_contains_config_hash \
  --collect-only -q
結果: 2 tests collected
EXIT=0
```

### R4 — V6 collect-only

```text
命令: venv/bin/python -m pytest \
  tests/api/test_ic_analysis_api.py tests/api/test_ic_deep_analysis.py tests/api/test_export_api.py \
  --collect-only -q
結果: 32 tests collected
EXIT=0
```

### R5 — V7 六檔 collect-only

```text
命令: venv/bin/python -m pytest \
  tests/test_feature_factory_e2e.py \
  tests/momentum/Analysis/test_lightgbm_analyzer.py \
  tests/momentum/Analysis/test_lightgbm_edge_cases.py \
  tests/momentum/Analysis/test_xgboost_protocol_methods.py \
  tests/momentum/test_lightgbm_analyzer_phase3.py \
  tests/momentum/test_xgboost_protocol_methods_phase3.py \
  --collect-only -q
結果: 141 tests collected
EXIT=0
```

### R6 — 解耦、I1、FF、GEN、腳本、git

```text
命令: count=$(grep -r "from api\." momentum/ | wc -l | tr -d ' '); test "$count" -eq 0; echo "count=$count"
結果: count=0
EXIT=0

命令: venv/bin/python -m pytest \
  tests/api/test_ic_run_selector.py::test_disambig_same_tf_different_hash \
  tests/momentum/test_ic_filter_orchestrator.py::test_refilter_without_cache_raises \
  tests/momentum/Analysis/test_long_short_analyzer.py::test_insufficient_ls_samples \
  --collect-only -q
結果: 3 tests collected
EXIT=0

命令: rg -c "create_feature_factory\(" tests/test_feature_factory_e2e.py
結果: 7

命令: rg -c "_create_e2e_factory\(" tests/test_feature_factory_e2e.py || true
結果: 0（pre-impl）

命令: test -f scripts/run_ic_persist_hermetic.sh
結果: NOT YET（EXIT=1，預期）

命令: for f in tests/fixtures/gen_ic_run_selector_baseline.py \
  tests/golden/ic_phase1_contract/freeze_baseline.py \
  tests/golden/ic_phase1_1a_cut1/freeze_baseline.py \
  tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py; do test -f "$f" && echo EXISTS; done
結果: 四檔皆 EXISTS

命令: cd /tmp/p2debt-t2-proto && python3 -m pytest -q
結果: 8 passed
EXIT=0

命令: git rev-parse HEAD
結果: 241ab91030dcc0cc87876e517f98213130dd5f90

命令: git status --porcelain | awk '{print $NF}' | sort -u | wc -l
結果: 25（**勿釘死**；實作前必重存 pre-dirty）
```

### R7 — exit 契約 counterexample（pipefail）

```text
命令: false | tail -1; echo bare_tail_exit=$?
結果: bare_tail_exit=0（tail 掩蓋失敗 — 禁用）

命令: set -o pipefail; false | tail -1; echo pipefail_tail_exit=$?
結果: pipefail_tail_exit=1（正確）
```

---

## §0 全域規則與約束（執行端讀完即可遵守）

- **scope（硬邊界）**：僅 §C + 附錄 A 白名單檔；**禁止**改 `momentum/`、`api/` 生產公開簽名與 persist 邏輯；**禁止**寫/改 `data_cache/`；**禁止** root autouse redirect；**禁止**弱化 NaN/inf/float16 gate 或改輸出 schema/數值/檔案大小。
- **§A manifest 事實**：16-caller `rg` 與 API polluter fixture **分開計數**；V1 collect **10**、body **9 passed, 1 skipped**（唯一 skip `test_performance_800_features`）；V7 六檔 collect **141**；pytest **序列執行**、禁 xdist。
- **collect-only 禁令（marker 驗證）**：禁 `pytest --collect-only` 驗證 `ic_persist_redirect` mark（會寫 `tests/golden/l65/test_inventory.txt`）。改用 `rg -n "ic_persist_redirect"` / AST。若必須 collect 計數，須在 pre-dirty 記錄該檔 hash，完工後 delta 須可解釋。
- **production_prefix（NEW-R4-3）**：`ActiveRedirect.production_prefix` = `Path(git rev-parse --show-toplevel) / "data_cache"` 之 **`.resolve()`**；禁裸 `Path("data_cache")`。
- **ProductionWriteSpy（NEW-R4-2）**：installer rewrite 決策點檢查 `path.resolve().is_relative_to(production_prefix.resolve())`；違規 append `violations`；禁空 violations 假綠。
- **S11 / multi_tf（NEW-R4-1）**：**7** 處 `create_feature_factory()` 全改經 `_create_e2e_factory()`；helper 定義內保留 **1** 次 `create_feature_factory()` 為合法。
- **Completeness 文案（NEW-R4-4）**：「零 patch」僅指 `install_once` resolve 失敗；`install_once` 成功後 pass-through wrapper **可常駐**；`activate` 缺 seam → gate inactive。
- **Phase 1 可執行性（grok B1 修法）**：**Task 1.0** 在 Phase 1 落地 S9/S11 **最小 stub helper**（可 import、可 probe）；**Task 1.1** manifest 註冊 **全 S1–S11**（含 S10 installer）；Phase 1 Gate 要求 **11** seam probe 全綠；Phase 2 只做 call-site wiring + markers，**不得**再「邊 wiring 邊補 manifest」。 VERIFY-EXEMPT:draft-superseded:p2debt-t2
- **防假綠**：禁放寬斷言；禁 skip polluter；正式驗收 = `bash scripts/run_ic_persist_hermetic.sh --set all`。
- **scope gate**：`comm -13` post∖pre；禁 `comm -23`；whitelist 見附錄 A（**完整**，禁「稍後補」）。
- **命令慣例**：
  - pytest：`venv/bin/python -m pytest`
  - bash 退出：`rc=$?; echo "rc=$rc"; exit "$rc"`
  - **禁** bare `cmd | tail -1` 當 gate（用 `set -o pipefail` 或不用 pipe）
  - 解耦 V8：`count=$(grep -r "from api\." momentum/ | wc -l | tr -d ' '); test "$count" -eq 0`（禁 bare `grep | wc -l` 當唯一斷言）
- **條件 scope**：若 FF e2e 需 plugin，允許 `tests/conftest.py` **僅**追加一行 `pytest_plugins = [...]`（列入白名單）。

---

## §B 批次執行策略

| Batch | 含 Task | 依賴 | 規模 |
|-------|---------|------|------|
| **B1** | 1.0–1.4 | 無 | **大** — 含 S9/S11 stub + 全 manifest；**禁** REDIRECT markers |
| **B2** | 2.1–2.5 | B1 Gate | **大** — wiring only |
| **B3** | 3.1–3.4 | B2 Gate | **大** — 唯一 polluting body 驗收批 |
| **B4** | 4.1 | B3 Gate | **小** |

**B1 Gate**

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；全 passed（含 S1–S11 probe + 全 ID mutation + S2/S10 subtarget mutation）
# 不含：Task 1.4 PROTO 外層 env 對照（§PROTO-P2）
```

**B2 Gate**

```bash
venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_persist_redirect_unit.py \
  tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：inventory 0 failed；I3 rg 契約全過
```

**B3 Gate（digest 子集）**

```bash
bash scripts/run_ic_persist_hermetic.sh --set V1
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；DIGEST_DIFF_EMPTY[V1]=1；9 passed, 1 skipped
```

---

## Phase 1 — process-global gate + manifest + atomic rollback

**目標**：`RedirectPatchSet` 可 resolve/install/activate **S1–S11 全 manifest**；inactive 零 I/O；`to_thread` 同 process gate；mutation 可證偽。

### Task 1.0 — S9/S11 最小 stub helper（Phase 1 前置，禁延後 Phase 2）

> **閉合 grok B1**：manifest target 必須 Phase 1 可 import；Phase 2 只改 call-site。

| # | 檔案 | 精確變更 | 驗證（read-only / import） |
|---|------|----------|---------------------------|
| **1.0.1** | `tests/api/test_export_api.py` | 新增 `def _export_fixture_filtered_path(metadata) -> Path:`：gate inactive 回 `Path("data_cache/features")/...`（與現 L125–137 語意同）；**暫**不強制 `export_task` 經 helper | `venv/bin/python -c "from tests.api.test_export_api import _export_fixture_filtered_path; assert callable(_export_fixture_filtered_path)"` → exit 0 |
| **1.0.2** | `tests/test_feature_factory_e2e.py` | 新增 `def _create_e2e_factory(): return create_feature_factory()`（inactive 委派）；**暫**不替換 7 call-site | `venv/bin/python -c "from tests.test_feature_factory_e2e import _create_e2e_factory; assert callable(_create_e2e_factory)"` → exit 0 |

- **不可做**：檔級 `pytestmark`、REDIRECT marker、替換 7 call-site（留 Task 2.4/2.5）

---

### Task 1.1 — 核心模組 `tests/fixtures/ic_persist_redirect.py`

- **SPEC ref**：§SEAM S1–S11 全表　|　**目標**：`RedirectPatchSet` 註冊 **11** seams（非 8）

#### 有序實作清單

| # | 目標 | 精確變更 |
|---|------|----------|
| **1.1.1** | `REQUIRED_SEAM_IDS` | `frozenset S1..S11` |
| **1.1.2** | `digest_data_cache()` | `repo_root/data_cache/{features,reports,models}` → `{rel: sha256}` sorted |
| **1.1.3** | `production_prefix` | 絕對 `repo_root / "data_cache"` `.resolve()` |
| **1.1.4** | `ProductionWriteSpy` | rewrite 決策點 `record(path)` |
| **1.1.5** | `resolve_all` / `_build_manifest` | **S1–S8** 生產符號 + **S9** `_export_fixture_filtered_path` + **S10** `LightGBMAnalyzer._resolve_model_path` + `XGBoostAnalyzer._resolve_model_path` + **S11** `_create_e2e_factory` |
| **1.1.6** | S2 subtargets | 三 installer：`save_report`、`save_filter_log`、`save_filtered_features` |
| **1.1.7** | S10 subtargets | lgb + xgb 各一 installer + probe |
| **1.1.8** | `install_once` 原子 rollback | 全 resolve 成功才 patch；中途 fail → reverse |
| **1.1.9** | process-global gate | `_active` + `RLock`；nested 見 Task 1.3.9 |
| **1.1.10** | inactive pass-through | gate inactive 不 mkdir redirect root |

- **修改檔案**：`tests/fixtures/ic_persist_redirect.py`（新建）
- **驗證**：Task 1.3

---

### Task 1.2 — Plugin 骨架

| # | 目標 | 驗證 |
|---|------|------|
| **1.2.1** | session `redirect_patch_set` → `install_once()` 不 activate | import plugin 模組 exit 0 |
| **1.2.2** | function `ic_persist_redirect` activate/deactivate + own spy | Task 1.3 |
| **1.2.3** | `tests/momentum/conftest.py` pytest_plugins | 檔存在 |
| **1.2.4** | `test_to_thread_polluter_writes_under_redirect` | 單測 passed |

---

### Task 1.3 — Unit + completeness + **全量 mutation 表**

> **閉合 codex B1**：每 S1–S11 缺 target mutation；S2 三 subtarget；S10 雙 subtarget。

| # | 測試名（必須存在） | 覆蓋 |
|---|-------------------|------|
| **1.3.1** | `test_seam_probe_redirect_only[S1..S11]` | 正向 probe |
| **1.3.2** | `test_missing_target_refuses_activate[S1..S11]` | 逐 ID monkeypatch missing import/attr → `activate()` raise；**activation_count==0**；若 `install_once` 未成功則 zero patch |
| **1.3.3** | `test_missing_subtarget_refuses_activate[S2-save_report\|S2-save_filter_log\|S2-save_filtered_features]` | S2 三方法各自 mutation |
| **1.3.4** | `test_missing_subtarget_refuses_activate[S10-lightgbm\|S10-xgboost]` | S10 雙 analyzer |
| **1.3.5** | `test_missing_target_after_install_refuses_activate` | install 成功後 mock 缺 seam → activate raises；pass-through wrappers 可存在；gate inactive（NEW-R4-4） |
| **1.3.6** | `test_installer_mid_fail_rollback` | 第 N installer raise → reverse |
| **1.3.7** | `test_manifest_extra_or_missing_id` | 少/多 ID、空 installer/probe → `RedirectCompletenessError` |
| **1.3.8** | `test_s9_helper_bypass_mutation` | `export_task` 繞過 helper 直寫 `h5py` → probe 紅 |
| **1.3.9** | `test_s11_helper_bypass_mutation` | 測試內直接 `create_feature_factory()` 繞過 helper → probe 紅 |
| **1.3.10** | `test_to_thread_polluter_writes_under_redirect` | `asyncio.to_thread` under redirect |
| **1.3.11** | `test_non_opt_in_not_redirected` | 無 marker 不 activate |
| **1.3.12** | `test_nested_activate_rejected` | 見下 |

**1.3.12 nested 語意（codex B7）**：第一次 `activate()` 成功 → `activation_count==1`；第二次 `activate()` → `RuntimeError`；**activation_count 仍為 1**（第一 context 仍 active）；僅 `deactivate(first_ctx)` 後歸 0。

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q
rc=$?; echo "rc=$rc"; exit "$rc"
```

---

### Task 1.4 — Mutation 契約（unit 層）

| # | 測試 | 驗證 |
|---|------|------|
| **1.4.1** | `test_mutation_disable_redirect_internal` | **測試內** monkeypatch DISABLE getter；assert 寫入落 production/sacrificial；**本測試 PASSED**（非外層 env 常駐 FAILED） |
| **1.4.2** | `test_mutation_disable_redirect_proto_optional` | 可選：外層 `IC_PERSIST_REDIRECT_DISABLE=1` 令既有 opt-in 測紅；**排除於 Phase 1 Gate** |

**Phase 1 Gate**：`test_ic_persist_redirect_unit.py` 全綠，**排除** 1.4.2。 VERIFY-EXEMPT:draft-superseded:p2debt-t2

---

## Phase 2 — REDIRECT wiring（call-site + markers only）

> Phase 2 **不**新增 manifest seam；只接線 Task 1.0 stub。

### Task 2.1 — 確認 S1–S8 installer（已在 1.1）

- **驗證**：`test_seam_probe_redirect_only[S1..S8]` 仍 passed（回歸）

### Task 2.2 — IC momentum REDIRECT markers

| # | 檔案 | 精確變更 |
|---|------|----------|
| **2.2.1** | `test_ic_1a_cut1_oos.py` | **僅** `test_fallback_insufficient_data_marks_applied_false`、`test_oos_applied_true_when_sufficient` 加 **`@pytest.mark.ic_persist_redirect`** + **`@pytest.mark.usefixtures("ic_persist_redirect")`**（**禁**檔級 `pytestmark`，避免 STUB 兄弟被標記 — codex B6） |
| **2.2.2** | `test_ic_e2e.py` | 檔級 `pytestmark` + `usefixtures` |
| **2.2.3** | `test_ic_feature_filter.py` | 同上 |
| **2.2.4** | `test_ic_1a_cut1_golden.py` | 同上 |
| **2.2.5** | `test_ic_analysis_service.py` | 兩 materialize 測試函式級 decorator |

**驗證（read-only rg；禁 collect）**：

```bash
rg -n "ic_persist_redirect" tests/momentum/test_ic_e2e.py
rc=$?; test "$rc" -eq 0
echo "rc=$rc"; exit "$rc"
# 預期：≥1 匹配；rc=0
```

### Task 2.3 — S10 ML markers

- 五檔 `pytestmark`；roundtrip probe models under `redirect_root/models`
- **S10 installer 已在 Task 1.1**（本 task 僅 markers）

### Task 2.4 — S9 API wiring

| # | 變更 |
|---|------|
| **2.4.1** | 三 API 檔 session/module polluter lifecycle |
| **2.4.2** | `export_task` L125–137 **改經** `_export_fixture_filtered_path`；helper active 時回 `root/features` |
| **2.4.3** | `test_export_api.py` 其餘測試 marker |

```bash
rg -n "_export_fixture_filtered_path" tests/api/test_export_api.py
rc=$?; test "$rc" -eq 0
echo "rc=$rc"; exit "$rc"
```

### Task 2.5 — S11 FF e2e + multi_tf

| # | 變更 |
|---|------|
| **2.5.1** | `_create_e2e_factory()`：active 時 `factory._storage = FeatureStorage(redirect_root / "features")` |
| **2.5.2** | 替換 **7** 處 test body 的 `create_feature_factory()` → `_create_e2e_factory()`（含 multi_tf L78） |
| **2.5.3** | 檔級 `pytestmark` + `ic_persist_redirect` |

**驗證（grok B2 / codex B5 修正契約）**：

```bash
# call-site：7 處測試 body 呼叫 helper（不含 def 行）
rg -n "_create_e2e_factory\(\)" tests/test_feature_factory_e2e.py | wc -l | tr -d ' '
# 預期：7

# 直接 factory：全檔僅 helper 定義內 1 次
rg -n "create_feature_factory\(\)" tests/test_feature_factory_e2e.py | wc -l | tr -d ' '
# 預期：1

# 語意加強（可選 inventory 測試內）：唯一匹配行號 == _create_e2e_factory 定義行
```

**Phase 2 Gate**：

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q
rc=$?; echo "rc=$rc"; exit "$rc"
```

---

## Phase 3 — hermetic acceptance

### Task 3.1 — `scripts/run_ic_persist_hermetic.sh`

#### `run_guard` + skip 白名單執法（grok M2）

```bash
#!/usr/bin/env bash
set -euo pipefail

assert_skips_allowed() {
  local label="$1" report_file="$2"
  # 解析 pytest -ra 或 --tb=no 摘要 + 可選 --json-report
  # V1 白名單：唯一允許 skip nodeid 含 test_performance_800_features
  # V7 白名單：僅 tests/test_feature_factory_e2e.py 且 reason 含 _require_data 或 missing kline
  # 其他任何 skip → echo "SKIP_WHITELIST_FAIL[$label]=1"; return 1
  :
}

run_guard() {
  label="$1"; shift
  pre="$(venv/bin/python -c 'from tests.fixtures.ic_persist_redirect import digest_data_cache; import json; print(json.dumps(digest_data_cache(), sort_keys=True))')"
  "$@"
  assert_skips_allowed "$label" "${TMPDIR:-/tmp}/pytest-${label}.log"
  post="$(venv/bin/python -c 'from tests.fixtures.ic_persist_redirect import digest_data_cache; import json; print(json.dumps(digest_data_cache(), sort_keys=True))')"
  if [[ "$pre" != "$post" ]]; then
    echo "DIGEST_DIFF_EMPTY[${label}]=0"
    return 1
  fi
  echo "DIGEST_DIFF_EMPTY[${label}]=1"
}
```

#### 各 set 內層命令（V7 六檔**內嵌** — grok M3）

| Set | pytest 命令 | exit 契約 |
|-----|-------------|-----------|
| **V1** | oos 2 nodeid + `test_ic_e2e.py` + feature-filter 1 + cut1 golden 2 | 9p1s；`assert_skips_allowed` 僅 perf；digest=1 |
| **V2** | 兩 `test_ic_analysis_service.py` nodeid | 2p0s；digest=1 |
| **V5** | `test_ic_persist_redirect_golden_ab.py` + `test_ic_1a_cut1_golden.py` `-s` | 3p0s；`ab_hash=`；digest=1 |
| **V6** | `tests/api/test_ic_analysis_api.py` `test_ic_deep_analysis.py` `test_export_api.py` | ≥30 passed；digest=1 |
| **V7** | 下列六檔 `-q --tb=no` | collected=141；0 failed；skip 白名單；digest=1 |
| **all** | V1→V2→V5→V6→V7 | 五個 `DIGEST_DIFF_EMPTY[Vn]=1` |

**V7 六檔（內嵌，禁回讀 SPEC）**：

```text
tests/test_feature_factory_e2e.py
tests/momentum/Analysis/test_lightgbm_analyzer.py
tests/momentum/Analysis/test_lightgbm_edge_cases.py
tests/momentum/Analysis/test_xgboost_protocol_methods.py
tests/momentum/test_lightgbm_analyzer_phase3.py
tests/momentum/test_xgboost_protocol_methods_phase3.py
```

```bash
bash -n scripts/run_ic_persist_hermetic.sh
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0（腳本存在後）
```

---

### Task 3.2 — Golden A/B/C + `normalize(result)`（grok M1）

**`normalize(result)` 規則（內嵌 SPEC §G，禁自行擴大豁免）**：

- sorted keys；`json.dumps(..., sort_keys=True, default=str)`
- **僅**豁免：`filtered_features_path`、`report_paths`、`artifact_mtime` 等純路徑/mtime
- **不得**豁免：數值、NaN pattern、feature count、selection、schema
- **禁止**新增豁免欄位；stdout 必含 `ab_hash=`

| Run | 斷言 |
|-----|------|
| A | gate ON `tmp_a` → `hash_a` |
| B | gate ON `tmp_b` → `hash_b == hash_a` |
| C | gate OFF + `chdir(work)` sacrificial only → `hash_off == hash_a`；repo digest before/after 相等 |

---

### Task 3.3 — Isolation I1–I3

**I1 固定 nodeids**（不變）。**V4**：

```bash
venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_persist_redirect_isolation.py \
  tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q -s
rc=$?; echo "rc=$rc"; exit "$rc"
```

---

### Task 3.4 — Hermetic mutation

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_data_cache_hermetic.py::test_mutation_redirect_disabled_caught -q -s
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；stdout 含 MUTATION_CANARY=1
```

**Phase 3 Gate**：

```bash
bash scripts/run_ic_persist_hermetic.sh --set all
rc=$?; echo "rc=$rc"; exit "$rc"
```

---

## Phase 4 — GEN manual helper（codex B9）

### Task 4.1 — `run_with_manual_redirect` **context manager**

```python
@contextmanager
def run_with_manual_redirect(root: Path | None = None):
    """env IC_PERSIST_REDIRECT_ROOT 或 root 參數；finally own spy + deactivate"""
    ...
    yield active_root
```

| # | 檔案 | 變更 |
|---|------|------|
| **4.1.1** | `ic_persist_redirect_manual.py` | 上列 CM；禁「activate 後立刻 deactivate、generator body 未 bracket」 |
| **4.1.2** | GEN-01..04 | `if __name__ == "__main__":` 內 **`with run_with_manual_redirect():`** 包住既有 main body |

```bash
venv/bin/python -c "from tests.fixtures.ic_persist_redirect_manual import run_with_manual_redirect; import inspect; assert callable(run_with_manual_redirect)"
rc=$?; echo "rc=$rc"; exit "$rc"

rg -l "run_with_manual_redirect" \
  tests/fixtures/gen_ic_run_selector_baseline.py \
  tests/golden/ic_phase1_contract/freeze_baseline.py \
  tests/golden/ic_phase1_1a_cut1/freeze_baseline.py \
  tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py | wc -l | tr -d ' '
# 預期：4（完工後）
```

---

## Final Acceptance（**八個獨立**可執行步驟；每步自有 exit 契約 — codex B4）

> **禁止**單一代碼塊中段 `exit $rc` 截斷後續步驟。每步獨立執行、獨立記錄 rc。

### §1 主驗收 — hermetic all

```bash
bash scripts/run_ic_persist_hermetic.sh --set all
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；stdout 含 DIGEST_DIFF_EMPTY[V1..V7]=1（五個）；V1 內層 9p1s
```

### §2 Golden A/B/C

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py -q -s
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；stdout 含 ab_hash=
```

### §3 Isolation + inventory（V4）

```bash
venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_persist_redirect_isolation.py \
  tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q -s
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；≥4 passed
```

### §4 Mutation canary（V3b）

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_data_cache_hermetic.py -q -s
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；test_mutation_redirect_disabled_caught PASSED
```

### §5 Unit regression

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0
```

### §6 解耦 V8

```bash
count=$(grep -r "from api\." momentum/ | wc -l | tr -d ' ')
test "$count" -eq 0
rc=$?; echo "count=$count rc=$rc"; exit "$rc"
# 預期：count=0 rc=0
```

### §7 scope gate（pre-dirty 實作前必存）

```bash
git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t2-pre-dirty.txt
# ... 實作 ...
git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t2-post-dirty.txt
comm -13 /tmp/p2debt-t2-pre-dirty.txt /tmp/p2debt-t2-post-dirty.txt | sort -u > /tmp/p2debt-t2-delta-dirty.txt
sort -u /tmp/p2debt-t2-whitelist.txt > /tmp/p2debt-t2-whitelist-sorted.txt
sort -u /tmp/p2debt-t2-delta-dirty.txt > /tmp/p2debt-t2-delta-sorted.txt
diff -u /tmp/p2debt-t2-whitelist-sorted.txt /tmp/p2debt-t2-delta-sorted.txt
rc=$?; echo "rc=$rc"; exit "$rc"
# 壞基線（無實作）：rc=1 誠實；完工：rc=0
```

` /tmp/p2debt-t2-whitelist.txt` = **附錄 A 完整清單**（禁 heredoc 半成品）。

### §8 輔助 V9

```bash
bash scripts/agent_preflight.sh
bash scripts/run_ic_persist_hermetic.sh --set all
bash scripts/agent_postflight.sh
rc=$?; echo "rc=$rc"; exit "$rc"
```

---

## 附錄 A — 完整 scope whitelist（`/tmp/p2debt-t2-whitelist.txt` 來源）

```text
scripts/run_ic_persist_hermetic.sh
tests/fixtures/ic_persist_redirect.py
tests/fixtures/ic_persist_redirect_manual.py
tests/fixtures/ic_persist_redirect_plugin.py
tests/momentum/conftest.py
tests/momentum/Analysis/test_ic_data_cache_hermetic.py
tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py
tests/momentum/Analysis/test_ic_persist_redirect_inventory.py
tests/momentum/Analysis/test_ic_persist_redirect_isolation.py
tests/momentum/Analysis/test_ic_persist_redirect_unit.py
tests/momentum/Analysis/test_ic_1a_cut1_oos.py
tests/momentum/Analysis/test_ic_1a_cut1_golden.py
tests/momentum/test_ic_e2e.py
tests/momentum/test_ic_feature_filter.py
tests/api/test_ic_analysis_service.py
tests/api/test_ic_analysis_api.py
tests/api/test_ic_deep_analysis.py
tests/api/test_export_api.py
tests/momentum/Analysis/test_lightgbm_analyzer.py
tests/momentum/Analysis/test_lightgbm_edge_cases.py
tests/momentum/Analysis/test_xgboost_protocol_methods.py
tests/momentum/test_lightgbm_analyzer_phase3.py
tests/momentum/test_xgboost_protocol_methods_phase3.py
tests/test_feature_factory_e2e.py
tests/fixtures/gen_ic_run_selector_baseline.py
tests/golden/ic_phase1_contract/freeze_baseline.py
tests/golden/ic_phase1_1a_cut1/freeze_baseline.py
tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py
tests/conftest.py
```

（`tests/conftest.py` 僅當條件 scope 觸發時列入 delta。）

---

## 附錄 B — grok NEW-R4 吸收（不變）

| grok ID | 吸收位置 |
|---------|----------|
| NEW-R4-1 | §0、Task 2.5、S11、I3 |
| NEW-R4-2 | §0、Task 1.1.4 |
| NEW-R4-3 | §0、Task 1.1.3 |
| NEW-R4-4 | §0、Task 1.3.5 |

---

## R2-CLOSURE — 雙審 finding 對照

| ID | 來源 | 嚴重度 | R2 閉合方式 |
|----|------|--------|-------------|
| **grok B1** | grok | BLOCK | Task **1.0** stub S9/S11 + Task **1.1** 全 S1–S11 manifest；Phase 1 Gate 11 probe；Phase 2 wiring-only |
| **grok B2** | grok | BLOCK | Task 2.5：`create_feature_factory(` **1**（僅 helper def）；`_create_e2e_factory()` call-site **7** |
| **grok M1** | grok | MAJOR | Task 3.2 內嵌 `normalize(result)` 全文 + 禁新增豁免 |
| **grok M2** | grok | MAJOR | Task 3.1 `assert_skips_allowed`；V1/V7 白名單 fail-closed |
| **grok M3** | grok | MINOR | Task 3.1 V7 六檔路徑內嵌 |
| **grok M4** | grok | MINOR | Task 1.4.1 改內部 monkeypatch PASSED；1.4.2 排除 Phase 1 Gate |
| **grok M5** | grok | MINOR | FF-02 改「分類-only；不新增 canary」 |
| **grok M6** | grok | MINOR | Header 雙戳；dirty **25** 勿釘死；pre-dirty 重存 |
| **codex B1** | codex | BLOCK | Task 1.3 mutation 表：S1–S11 逐 ID + S2 三 subtarget + S10 雙 subtarget + S9/S11 bypass |
| **codex B2** | codex | BLOCK | §0 collect-only 禁令；基線 receipt 註記 inventory 副作用 |
| **codex B3** | codex | BLOCK | §0 pipefail；禁 `tail -1` gate；V8 `count`+`test`；R7 counterexample |
| **codex B4** | codex | BLOCK | Final §1–§8 **獨立**步驟；附錄 A **完整** whitelist |
| **codex B5** | codex | BLOCK | 同 grok B2（Task 2.5 rg 契約） |
| **codex B6** | codex | BLOCK | Task 2.2.1 函式級 decorator；禁檔級 pytestmark 於 oos |
| **codex B7** | codex | BLOCK | Task 1.3.12：二次 activate → RuntimeError；count **仍 1** |
| **codex B8** | codex | BLOCK | §V 計 **10**；追溯總計 **88** |
| **codex B9** | codex | BLOCK | Task 4.1 `@contextmanager` + GEN `with run_with_manual_redirect():` |

---

SPEC=handoffs/P2DEBT-T2-SPEC-DRAFT-R4.md TODO=handoffs/P2DEBT-T2-TODO-DRAFT-R2.md FOCUS=legacy data_cache redirect process-global S1–S11 digest hermetic golden isolation mutation；用 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 獨立審查；Blocking 修補後才 Frozen。

```
ASSUMPTIONS_VERIFIED: 16-caller=16; V1 collect=10; V2=2; V6=32; V7=141; I1 collect=3; decoupling count=0; FF create_feature_factory=7 pre-impl; GEN四檔存在; hermetic.sh 未建; proto 8 passed; HEAD=241ab910; dirty=25; pipefail counterexample
TESTS_RUN: 見基線 receipt R1–R7（collect 有 inventory 副作用已文件化）；/tmp/p2debt-t2-proto pytest -q → 8 passed
FAILURES_SEEN: none unexpected
SCOPE_CHANGES: none（僅 handoffs/P2DEBT-T2-TODO-DRAFT-R2.md）
NUMERIC_OR_SCHEMA_IMPACT: none
產出: handoffs/P2DEBT-T2-TODO-DRAFT-R2.md
```

STATUS: DONE
