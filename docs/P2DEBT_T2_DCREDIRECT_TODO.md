# P2 債票 2 — legacy 測試 data_cache 污染 → tmp redirect — TODO(正式版)

> 定稿來源:handoffs/P2DEBT-T2-TODO-DRAFT-R6.md(內容=R5 凍結;R6 僅範本結構整備零語意變更,雙家 diff 重確認)
> RECONCILE-STAMP:codex(R5+R6)/composer(R5)/grok(R6)=handoffs/P2DEBT-T2-TODO-REVERIFY-R{5,6}-*.md
> task-id:p2debt-t2 | 正式化:2026-07-11 | 內容=R6 凍結稿,除本頭注外零改動


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
| S11 | `_create_e2e_factory` + **7** call-site（字面 rg def+calls=**8**）含 multi_tf | Task **1.0** stub + 1.1 + **2.5** call-site wiring |

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
>
> **R3 修正命令 FACT-RECEIPT**（Grok 2026-07-11 唯讀；零 polluting repo body；見本檔「R3 FACT-RECEIPT」）：Task 2.5 字面 `_create_e2e_factory\(\)` post-impl 靜態模擬=**8**；root `tests/conftest` plugin 覆蓋 api+momentum+FF；momentum-only 無法服務 api/root FF。  
> **R4 修正命令 FACT-RECEIPT**（Grok 2026-07-11 唯讀；見本檔「R4 FACT-RECEIPT」）：§8 any-fail 累積；§7 pre-dirty 減法；Task 2.5 `test -eq` 斷言。  
> **R5 修正命令 FACT-RECEIPT**（Grok 2026-07-11 唯讀；見本檔末「R5 FACT-RECEIPT」）：Task 4.1 covered-overlap-file count 包 `test -eq`；expected 自 pre-dirty∩whitelist 重算（CURRENT=2）。

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
- **S11 / multi_tf（NEW-R4-1 + NEW-B1）**：**7** 處 body `create_feature_factory()` 全改經 `_create_e2e_factory()`；helper 定義內保留 **1** 次 `create_feature_factory()` 為合法。字面 gate `rg -n '_create_e2e_factory\(\)' … | wc -l` 的 **TRUE 期望=8**（1 def 行 + 7 call-site；`def _create_e2e_factory():` 含 `_create_e2e_factory()` 子串）。
- **Completeness 文案（NEW-R4-4）**：「零 patch」僅指 `install_once` resolve 失敗；`install_once` 成功後 pass-through wrapper **可常駐**；`activate` 缺 seam → gate inactive。
- **Phase 1 可執行性（grok B1 修法）**：**Task 1.0** 在 Phase 1 落地 S9/S11 **最小 stub helper**（可 import、可 probe）；**Task 1.1** manifest 註冊 **全 S1–S11**（含 S10 installer）；Phase 1 Gate 要求 **11** seam probe 全綠；Phase 2 只做 call-site wiring + markers，**不得**再「邊 wiring 邊補 manifest」。
- **Plugin 掛載（NEW-B2 / SPEC §SEAM）**：**必**在 root `tests/conftest.py` **無條件**追加 `pytest_plugins = ["tests.fixtures.ic_persist_redirect_plugin"]`，使 `tests/api/*`、`tests/momentum/**`、`tests/test_feature_factory_e2e.py` 皆可 resolve `ic_persist_redirect` / `redirect_patch_set`。**禁止**僅掛 `tests/momentum/conftest.py` 當唯一掛載點（pytest 不把 sibling tree conftest 供應給 `tests/api` 或 root-level 測試）。**禁止** root autouse activation（SPEC：根 conftest 只註冊 plugin/fixture 可見性，不 activate）。`tests/momentum/conftest.py` 仍新建（SPEC §C），但**不得**作為唯一 plugin 來源。
- **防假綠**：禁放寬斷言；禁 skip polluter；正式驗收 = `bash scripts/run_ic_persist_hermetic.sh --set all`。
- **scope gate**：`comm -13` post∖pre；禁 `comm -23`；whitelist 見附錄 A（**完整**，禁「稍後補」）。conftest 檔（`tests/conftest.py`、`tests/momentum/conftest.py`）**無條件**列入白名單；完工 delta 須含對二者的實作觸碰（root 必改 `pytest_plugins`；momentum 必新建）。Final §7：**pre-dirty 減法** — `expected_delta = whitelist ∖ (pre-dirty ∩ whitelist)`；`actual_delta = post ∖ pre`；`diff expected actual` 須 rc=0。**禁止**要求 `actual_delta == 完整 whitelist`（whitelist 檔若實作前已 dirty，再改也不會進 `comm -13` delta — dirty-overlap）。pre-dirty ∩ whitelist 必須印出並記入 receipt；overlap 檔的內容變更由 Task 4.1 等 content gate 覆蓋，不靠 scope delta 證明。
- **命令慣例**：
  - pytest：`venv/bin/python -m pytest`
  - bash 退出：`rc=$?; echo "rc=$rc"; exit "$rc"`
  - **禁** bare `cmd | tail -1` 當 gate（用 `set -o pipefail` 或不用 pipe）
  - 解耦 V8：`count=$(grep -r "from api\." momentum/ | wc -l | tr -d ' '); test "$count" -eq 0`（禁 bare `grep | wc -l` 當唯一斷言）

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
- **邊界**：
  - gate inactive 時 `_export_fixture_filtered_path` 回 `Path("data_cache/features")/...`（與現 L125–137 語意同）
  - gate inactive 時 `_create_e2e_factory()` 委派 `create_feature_factory()`；暫不替換 7 call-site

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
| **1.1.9** | process-global gate | `_active` + `RLock`；nested 見 Task **1.3.12** |
| **1.1.10** | inactive pass-through | gate inactive 不 mkdir redirect root |

- **修改檔案**：`tests/fixtures/ic_persist_redirect.py`（新建）
- **驗證**（pytest `test_ic_persist_redirect_unit.py` rc=0）：

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；S1–S11 probe + mutation 全 passed
```

- **邊界**：
  - gate inactive：zero I/O；`install_once` 中途 fail → atomic rollback
  - `production_prefix` = `Path(git rev-parse --show-toplevel)/"data_cache"`.resolve()；禁裸 `Path("data_cache")`
  - S2 三 subtarget、S10 雙 analyzer 各需獨立 installer+probe
- **不可做**：
  - 禁改 `momentum/`、`api/` 生產簽名與 persist 邏輯；禁寫/改 `data_cache/`
  - 禁空 `violations` 假綠（ProductionWriteSpy）；禁弱化 NaN/inf/float16 gate

---

### Task 1.2 — Plugin 骨架

> **閉合 NEW-B2**：fixture 可見性必須覆蓋 **api + momentum + root FF e2e**；僅 `tests/momentum/conftest.py` 不夠（pytest sibling/parent 規則）。

| # | 目標 | 精確變更 | 驗證 |
|---|------|----------|------|
| **1.2.1** | session `redirect_patch_set` → `install_once()` 不 activate | `tests/fixtures/ic_persist_redirect_plugin.py` | `venv/bin/python -c "import tests.fixtures.ic_persist_redirect_plugin"` → exit 0 |
| **1.2.2** | function `ic_persist_redirect` activate/deactivate + own spy | 同 plugin 模組 | Task 1.3 |
| **1.2.3** | **root 無條件 plugin 註冊（主掛載）** | **修改**既有 `tests/conftest.py`：**必**追加（或合併既有 list）一行 `pytest_plugins = ["tests.fixtures.ic_persist_redirect_plugin"]`（若檔內已有 `pytest_plugins`，合併為單一 list，**不得**刪既有 plugin）。**禁止** autouse redirect。此掛載供應：`tests/api/*`、`tests/momentum/**`、`tests/test_feature_factory_e2e.py` | `rg -n 'pytest_plugins' tests/conftest.py` → rc=0 且含 `ic_persist_redirect_plugin` |
| **1.2.4** | `tests/momentum/conftest.py`（SPEC §C 新建） | 新建檔；**可**空（註解指向 root plugin）或僅本地 unit helpers；**不得**作為唯一 `pytest_plugins` 掛載點；若寫 `pytest_plugins` 必須與 root **同一** entry 且 root 仍必有（防 double 以外的漏掛） | `test -f tests/momentum/conftest.py` → exit 0 |
| **1.2.5** | `test_to_thread_polluter_writes_under_redirect` | unit 檔 | 單測 passed |

**不可做**：只改 `tests/momentum/conftest.py` 而不改 root；把 `tests/conftest.py` 標成「僅 FF 條件」；在 root 加 autouse activate；新增 `tests/api/conftest.py` 的 `pytest_plugins` **除非**同步列入附錄 A（本 R3 **不**採用 api 樹第二掛載——root 已覆蓋）。

- **邊界**：
  - root `tests/conftest.py` 必為主掛載（覆蓋 `tests/api/*`、`tests/momentum/**`、`tests/test_feature_factory_e2e.py`）
  - session `redirect_patch_set` → `install_once()` 不 activate；function `ic_persist_redirect` 才 activate/deactivate

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

- **驗證**（pytest `test_ic_persist_redirect_unit.py` rc=0）：

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；全 passed（含 S1–S11 probe + 全 ID mutation + S2/S10 subtarget mutation）
```

- **邊界**：
  - 二次 `activate()` → `RuntimeError`；`activation_count` 仍 1（codex B7）
  - S9/S11 bypass mutation：繞過 helper 直寫 → probe 紅
  - `test_missing_target_refuses_activate[S1..S11]`：`activation_count==0`；`install_once` 未成功則 zero patch
- **不可做**：
  - 禁放寬 mutation 斷言；禁 skip polluter
  - 禁用 `pytest --collect-only` 驗 marker（改 `rg -n "ic_persist_redirect"` / AST）

---

### Task 1.4 — Mutation 契約（unit 層）

| # | 測試 | 驗證 |
|---|------|------|
| **1.4.1** | `test_mutation_disable_redirect_internal` | **測試內** monkeypatch DISABLE getter；assert 寫入落 production/sacrificial；**本測試 PASSED**（非外層 env 常駐 FAILED） |
| **1.4.2** | `test_mutation_disable_redirect_proto_optional` | 可選：外層 `IC_PERSIST_REDIRECT_DISABLE=1` 令既有 opt-in 測紅；**排除於 Phase 1 Gate** |

**Phase 1 Gate**：`test_ic_persist_redirect_unit.py` 全綠，**排除** 1.4.2。

- **邊界**：
  - `test_mutation_disable_redirect_internal`（1.4.1）：測試內 monkeypatch DISABLE；assert 寫入落 production/sacrificial；本測 PASSED
  - `test_mutation_disable_redirect_proto_optional`（1.4.2）：外層 env 對照；**排除於 Phase 1 Gate**（§PROTO-P2）
- **不可做**：
  - 禁外層 `IC_PERSIST_REDIRECT_DISABLE=1` 常駐令 Phase 1 Gate 紅（1.4.2 可選、排除）
  - 禁弱化 mutation 斷言或改 DISABLE getter 語意

---

## Phase 2 — REDIRECT wiring（call-site + markers only）

> Phase 2 **不**新增 manifest seam；只接線 Task 1.0 stub。

### Task 2.1 — 確認 S1–S8 installer（已在 1.1）

- **驗證**（pytest -k `test_seam_probe_redirect_only` rc=0）：

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -k "test_seam_probe_redirect_only" -q
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；test_seam_probe_redirect_only[S1..S8] 仍 passed（回歸）
```

- **邊界**：
  - S1–S8 installer 已在 Task 1.1 manifest；本 task 僅回歸 probe
  - Phase 2 不新增 manifest seam
- **不可做**：
  - 禁新增/刪除 manifest seam ID；禁改 S9/S10/S11 wiring（留 Task 2.4/2.5）

### Task 2.2 — IC momentum REDIRECT markers

| # | 檔案 | 精確變更 |
|---|------|----------|
| **2.2.1** | `test_ic_1a_cut1_oos.py` | **僅** `test_fallback_insufficient_data_marks_applied_false`、`test_oos_applied_true_when_sufficient` 加 **`@pytest.mark.ic_persist_redirect`** + **`@pytest.mark.usefixtures("ic_persist_redirect")`**（**禁**檔級 `pytestmark`，避免 STUB 兄弟被標記 — codex B6） |
| **2.2.2** | `test_ic_e2e.py` | 檔級 `pytestmark` + `usefixtures` |
| **2.2.3** | `test_ic_feature_filter.py` | 同上 |
| **2.2.4** | `test_ic_1a_cut1_golden.py` | 同上 |
| **2.2.5** | `test_ic_analysis_service.py` | 兩 materialize 測試函式級 decorator |

- **驗證**（read-only rg `test_ic_e2e.py` rc=0）：

```bash
rg -n "ic_persist_redirect" tests/momentum/test_ic_e2e.py
rc=$?; test "$rc" -eq 0
echo "rc=$rc"; exit "$rc"
# 預期：≥1 匹配；rc=0
```

- **邊界**：
  - `test_ic_1a_cut1_oos.py`：**僅**兩函式級 decorator；禁檔級 pytestmark（codex B6，避免 STUB 兄弟被標記）
  - 其餘檔可檔級 `pytestmark` + `usefixtures("ic_persist_redirect")`
- **不可做**：
  - 禁 `pytest --collect-only` 驗 marker（會寫 `tests/golden/l65/test_inventory.txt`）
  - 禁檔級 mark 於 oos；禁放寬既有斷言

### Task 2.3 — S10 ML markers

- 五檔 `pytestmark`；roundtrip probe models under `redirect_root/models`
- **S10 installer 已在 Task 1.1**（本 task 僅 markers）

- **驗證**（read-only rg `test_lightgbm_analyzer.py` rc=0）：

```bash
rg -n "ic_persist_redirect" tests/momentum/Analysis/test_lightgbm_analyzer.py
rc=$?; test "$rc" -eq 0
echo "rc=$rc"; exit "$rc"
# 預期：≥1 匹配（檔級 pytestmark）；rc=0
```

- **邊界**：
  - 五檔檔級 `pytestmark`；S10 lgb/xgb 各一 installer+probe 已在 Task 1.1
  - roundtrip probe：models 寫入 `redirect_root/models`
- **不可做**：
  - 禁重做 S10 installer（本 task 僅 markers）
  - 禁改 `momentum/` 生產 `_resolve_model_path` 簽名

### Task 2.4 — S9 API wiring

| # | 變更 |
|---|------|
| **2.4.1** | 三 API 檔 session/module polluter lifecycle |
| **2.4.2** | `export_task` L125–137 **改經** `_export_fixture_filtered_path`；helper active 時回 `root/features` |
| **2.4.3** | `test_export_api.py` 其餘測試 marker |

- **驗證**（rg `_export_fixture_filtered_path` `test_export_api.py` rc=0）：

```bash
rg -n "_export_fixture_filtered_path" tests/api/test_export_api.py
rc=$?; test "$rc" -eq 0
echo "rc=$rc"; exit "$rc"
# 預期：≥1 匹配；rc=0
```

- **邊界**：
  - `export_task` L125–137 **改經** `_export_fixture_filtered_path`；helper active 時回 `root/features`
  - 三 API 檔 session/module polluter lifecycle
- **不可做**：
  - 禁新增 `tests/api/conftest.py` 第二掛載（root `pytest_plugins` 已覆蓋，R3 不採用）
  - 禁改 `api/` 生產 persist 邏輯

### Task 2.5 — S11 FF e2e + multi_tf

| # | 變更 |
|---|------|
| **2.5.1** | `_create_e2e_factory()`：active 時 `factory._storage = FeatureStorage(redirect_root / "features")` |
| **2.5.2** | 替換 **7** 處 test body 的 `create_feature_factory()` → `_create_e2e_factory()`（含 multi_tf L78） |
| **2.5.3** | 檔級 `pytestmark` + `ic_persist_redirect`（fixture 由 **Task 1.2.3 root** `pytest_plugins` 供應，非 momentum-only） |

**驗證（NEW-B1 修正 + R4 assert；字面命令與期望可同時真；mismatch 必 non-zero）**：

```bash
# 字面 gate：def 行 + 7 call-site = 8（def _create_e2e_factory(): 含子串 _create_e2e_factory()）
# R4：必須 test -eq，禁只 print wc（mismatch 仍 exit 0 = 假綠）
set -o pipefail
c_helper=$(rg -n "_create_e2e_factory\(\)" tests/test_feature_factory_e2e.py | wc -l | tr -d ' ')
test "$c_helper" -eq 8
rc_h=$?; echo "c_helper=$c_helper rc=$rc_h"; test "$rc_h" -eq 0
# TRUE 預期：c_helper=8 rc=0
# 語意：1 def + 7 body call-site；禁改期望為 7 卻仍用本命令（假紅）

# 直接 factory：全檔僅 helper 定義內 1 次
c_factory=$(rg -n "create_feature_factory\(\)" tests/test_feature_factory_e2e.py | wc -l | tr -d ' ')
test "$c_factory" -eq 1
rc_f=$?; echo "c_factory=$c_factory rc=$rc_f"; test "$rc_f" -eq 0
# 預期：c_factory=1 rc=0

# 可選 call-site-only 交叉（非主 gate；排除 def 行；同樣必須 assert）
c_calls=$(rg -n "_create_e2e_factory\(\)" tests/test_feature_factory_e2e.py | rg -v ':def ' | wc -l | tr -d ' ')
test "$c_calls" -eq 7
rc_c=$?; echo "c_calls=$c_calls rc=$rc_c"; test "$rc_c" -eq 0
# 預期：c_calls=7 rc=0
```

- **邊界**：
  - 字面 gate：`c_helper=8`（1 def + 7 call-site）；`c_factory=1`；`c_calls=7`（含 multi_tf L78）
  - fixture 由 Task 1.2.3 root `pytest_plugins` 供應，非 momentum-only
- **不可做**：
  - 禁改期望為 7 卻仍用 `test "$c_helper" -eq 8` 命令（假紅）
  - 禁只 print `wc` 無 `test -eq`（R4 mismatch 仍 exit 0 = 假綠）

**Phase 2 Gate**：

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q
rc=$?; echo "rc=$rc"; exit "$rc"
```

---

## Phase 3 — hermetic acceptance

### Task 3.1 — `scripts/run_ic_persist_hermetic.sh`

- **驗證**（`bash -n scripts/run_ic_persist_hermetic.sh` rc=0）：

```bash
bash -n scripts/run_ic_persist_hermetic.sh
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0（腳本存在後）
```

- **邊界**：
  - V1 skip 白名單：唯一允許 skip nodeid 含 `test_performance_800_features`
  - V7 skip 白名單：僅 `tests/test_feature_factory_e2e.py` 且 reason 含 `_require_data` 或 missing kline
  - `run_guard` pre/post digest：`DIGEST_DIFF_EMPTY[label]=1`；非白名單 skip → `SKIP_WHITELIST_FAIL`
- **不可做**：
  - 禁允許非白名單 skip；禁回讀 SPEC 取 V7 六檔路徑（已內嵌）
  - 禁 bare `cmd | tail -1` 當 gate（用 `set -o pipefail`）

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

- **驗證**（pytest `test_ic_persist_redirect_golden_ab.py` + `test_ic_1a_cut1_golden.py` rc=0）：

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q -s
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；stdout 含 ab_hash=；Run A/B/C hash 斷言通過
```

- **邊界**：
  - Run A：gate ON `tmp_a` → `hash_a`；Run B：`hash_b == hash_a`
  - Run C：gate OFF + `chdir(work)` sacrificial only；repo digest before/after 相等
  - `normalize` 僅豁免路徑/mtime 欄位；禁豁免數值/NaN/schema
- **不可做**：
  - 禁新增 `normalize` 豁免欄位；禁自行擴大 SPEC §G 豁免
  - 禁弱化 golden hash 斷言

---

### Task 3.3 — Isolation I1–I3

**I1 固定 nodeids**（不變）。**V4**：

- **驗證**（pytest `test_ic_persist_redirect_isolation.py` + inventory rc=0）：

```bash
venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_persist_redirect_isolation.py \
  tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q -s
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；≥4 passed
```

- **邊界**：
  - I1：subprocess 三 fixed non-opt-in nodeid 不受 redirect 影響
  - I2：parametrize S1–S11 probes；I3：REDIRECT inventory vs marker/helper 契約
- **不可做**：
  - 禁改 I1 fixed nodeids；禁 `pytest --collect-only` 驗 I3 inventory
  - 禁放寬 isolation 斷言

---

### Task 3.4 — Hermetic mutation

- **驗證**（pytest `test_mutation_redirect_disabled_caught` rc=0）：

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_data_cache_hermetic.py::test_mutation_redirect_disabled_caught -q -s
rc=$?; echo "rc=$rc"; exit "$rc"
# 預期：rc=0；stdout 含 MUTATION_CANARY=1
```

- **邊界**：
  - 與 Task 1.4 mutation 契約呼應；拔 redirect → canary 紅；restore 綠
  - stdout 必含 `MUTATION_CANARY=1`
- **不可做**：
  - 禁弱化 mutation canary；禁 skip `test_mutation_redirect_disabled_caught`
  - 禁改 hermetic 測試使 DISABLE 路徑假綠

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
    pass  # bracket main body
    yield active_root
```

| # | 檔案 | 變更 |
|---|------|------|
| **4.1.1** | `ic_persist_redirect_manual.py` | 上列 CM；禁「activate 後立刻 deactivate、generator body 未 bracket」 |
| **4.1.2** | GEN-01..04 | `if __name__ == "__main__":` 內 **`with run_with_manual_redirect():`** 包住既有 main body |

- **驗證**（python -c import + rg `test -eq 4` rc=0）：

```bash
venv/bin/python -c "from tests.fixtures.ic_persist_redirect_manual import run_with_manual_redirect; import inspect; assert callable(run_with_manual_redirect)"
rc=$?; echo "rc=$rc"; exit "$rc"

# --- R5：content gate 必須 test -eq（禁只 print wc；mismatch / 零覆蓋必 non-zero）---
# A) 全量 GEN-01..04：完工後四檔皆含 run_with_manual_redirect
set -o pipefail
c=$(rg -l "run_with_manual_redirect" \
  tests/fixtures/gen_ic_run_selector_baseline.py \
  tests/golden/ic_phase1_contract/freeze_baseline.py \
  tests/golden/ic_phase1_1a_cut1/freeze_baseline.py \
  tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py | wc -l | tr -d ' ')
test "$c" -eq 4
rc_gen=$?; echo "c_gen=$c rc=$rc_gen"; test "$rc_gen" -eq 0
# 預期完工：c_gen=4 rc=0
# pre-impl / 零覆蓋：c_gen=0 → test 失敗 → rc=1（R4 僅 print 時 pipeline_rc=0 = 假綠）

# B) dirty-overlap 內容 gate（§7 委託點；R5 fail-closed）
# expected = |pre-dirty ∩ whitelist|；**開工時必須重算**，勿釘死 2
#   來源：Final §7 步驟 2 的 /tmp/p2debt-t2-pre-dirty-overlap.txt（或等價 comm -12）
#   CURRENT 2026-07-11 實測：2（cut1 freeze_baseline.py + freeze_baseline_new.py）
if [ ! -f /tmp/p2debt-t2-pre-dirty-overlap.txt ]; then
  echo "MISSING_OVERLAP_LIST=/tmp/p2debt-t2-pre-dirty-overlap.txt（先跑 Final §7 步驟 1–2）"
  exit 1
fi
expected_overlap=$(wc -l < /tmp/p2debt-t2-pre-dirty-overlap.txt | tr -d ' ')
# 覆蓋數 = overlap 清單中含 run_with_manual_redirect 的檔數
c_ov=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if rg -q "run_with_manual_redirect" "$f" 2>/dev/null; then
    c_ov=$((c_ov + 1))
  fi
done < /tmp/p2debt-t2-pre-dirty-overlap.txt
test "$c_ov" -eq "$expected_overlap"
rc_ov=$?; echo "c_overlap=$c_ov expected_overlap=$expected_overlap rc=$rc_ov"
test "$rc_ov" -eq 0
# 預期完工：c_overlap == expected_overlap（CURRENT expected=2）且 rc=0
# 零覆蓋：c_overlap=0 expected=2 → rc=1（不得假綠）
# 若 overlap 變為 0（無 dirty-overlap），expected=0 且 c_ov=0 → rc=0 合法（此時全量 gate A 仍執法 c_gen=4）
```

- **邊界**：
  - 全量 GEN gate A：`test "$c" -eq 4`；dirty-overlap gate B：`test "$c_ov" -eq "$expected_overlap"`（CURRENT=2，開工重算）
  - pre-impl / 零覆蓋必 rc=1（R5 fail-closed）；`/tmp/p2debt-t2-pre-dirty-overlap.txt` 缺失 → exit 1
- **不可做**：
  - 禁 activate 後立刻 deactivate（generator body 未 bracket）
  - 禁只 print `rg|wc` 無 `test -eq`（R4/R5 假綠：c=0 pipeline_rc=0）

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

### §7 scope gate（pre-dirty 減法；dirty-overlap 可執行 — R4）

> **R3 假綠根因**：若 whitelist 檔在實作前已 dirty（`comm -12 pre whitelist` 非空），再改該檔**不會**進入 `comm -13 pre post`；要求 `delta == 完整 whitelist` 在已 dirty workspace **永遠 rc=1**（假紅 / 不可達）。

```bash
# 0) whitelist = 附錄 A 完整清單（禁 heredoc 半成品）
sort -u /tmp/p2debt-t2-whitelist.txt > /tmp/p2debt-t2-whitelist-sorted.txt

# 1) 實作前必存 pre-dirty
git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t2-pre-dirty.txt

# 2) 印出並記錄 pre-dirty ∩ whitelist（dirty-overlap；必須入 receipt）
comm -12 /tmp/p2debt-t2-pre-dirty.txt /tmp/p2debt-t2-whitelist-sorted.txt \
  | tee /tmp/p2debt-t2-pre-dirty-overlap.txt
echo "OVERLAP_N=$(wc -l < /tmp/p2debt-t2-pre-dirty-overlap.txt | tr -d ' ')"
# 2026-07-11 當前 repo 實測 overlap（R4 FACT-RECEIPT）：
#   tests/golden/ic_phase1_1a_cut1/freeze_baseline.py
#   tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py
# OVERLAP_N=2 → expected_delta_n = 29-2 = 27
# 實作端開工時必須重跑本步；overlap 可能變，**勿釘死 2**，以當次 tee 為準。

# 3) expected_delta = whitelist ∖ pre-dirty（即 whitelist 中尚未 dirty 的列）
comm -13 /tmp/p2debt-t2-pre-dirty.txt /tmp/p2debt-t2-whitelist-sorted.txt \
  | sort -u > /tmp/p2debt-t2-expected-delta.txt

# ... 實作 ...

# 4) post-dirty + actual_delta = post ∖ pre
git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t2-post-dirty.txt
comm -13 /tmp/p2debt-t2-pre-dirty.txt /tmp/p2debt-t2-post-dirty.txt \
  | sort -u > /tmp/p2debt-t2-delta-dirty.txt

# 5) gate：actual_delta 必須 exact-equal expected_delta（非完整 whitelist）
diff -u /tmp/p2debt-t2-expected-delta.txt /tmp/p2debt-t2-delta-dirty.txt
rc=$?; echo "SCOPE_DELTA_RC=$rc"; exit "$rc"
# 壞基線（無實作）：rc=1 誠實（actual 空 ≠ expected 27-ish）
# 完工且無越界：rc=0
# overlap 檔（GEN cut1 freeze_*）內容仍須由 Task 4.1 `rg run_with_manual_redirect` 等 content gate 覆蓋
```

`/tmp/p2debt-t2-whitelist.txt` = **附錄 A 完整清單**（禁 heredoc 半成品）。

### §8 輔助 V9（**每步 rc 累積；任一步非 0 → 整段 fail — R4**）

> **R3 假綠根因**：鏈式 `preflight; hermetic; postflight; rc=$?` 只保留最後一步 rc；`false; true; rc=$?` → 0 可掩蓋前步失敗。

```bash
# 正確契約：set +e（允許逐步跑完）+ 明確累積；禁單抓最後 rc
set +e
set -o pipefail
fail=0
run_step() {
  local name="$1"; shift
  "$@"
  local rc=$?
  echo "STEP_RC[$name]=$rc"
  if [ "$rc" -ne 0 ]; then fail=1; fi
  return 0
}
run_step preflight bash scripts/agent_preflight.sh
run_step hermetic bash scripts/run_ic_persist_hermetic.sh --set all
run_step postflight bash scripts/agent_postflight.sh
echo "ANY_FAIL=$fail"
exit "$fail"
# 預期完工：STEP_RC[preflight]=0 STEP_RC[hermetic]=0 STEP_RC[postflight]=0 ANY_FAIL=0
# 任一步非 0 → ANY_FAIL=1 且 exit 1（不得被後續 0 掩蓋）
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

（`tests/conftest.py` 與 `tests/momentum/conftest.py` **無條件**列入 whitelist 與完工 delta：root **必**改 `pytest_plugins`；momentum **必**新建。禁再標「條件 scope」。）

---

## 附錄 B — grok NEW-R4 吸收（不變）

| grok ID | 吸收位置 |
|---------|----------|
| NEW-R4-1 | §0、Task 2.5、S11、I3 |
| NEW-R4-2 | §0、Task 1.1.4 |
| NEW-R4-3 | §0、Task 1.1.3 |
| NEW-R4-4 | §0、Task 1.3.5 |

---

## R2-CLOSURE — 雙審 finding 對照（**保留不動**；R3 不重開）

| ID | 來源 | 嚴重度 | R2 閉合方式 |
|----|------|--------|-------------|
| **grok B1** | grok | BLOCK | Task **1.0** stub S9/S11 + Task **1.1** 全 S1–S11 manifest；Phase 1 Gate 11 probe；Phase 2 wiring-only |
| **grok B2** | grok | BLOCK | Task 2.5：`create_feature_factory(` **1**（僅 helper def）；body call-site **7**（R3 補字面 rg=**8**，見 NEW-B1） |
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
| **codex B5** | codex | BLOCK | 同 grok B2（Task 2.5 rg 契約；R3 字面期望修為 8） |
| **codex B6** | codex | BLOCK | Task 2.2.1 函式級 decorator；禁檔級 pytestmark 於 oos |
| **codex B7** | codex | BLOCK | Task 1.3.12：二次 activate → RuntimeError；count **仍 1** |
| **codex B8** | codex | BLOCK | §V 計 **10**；追溯總計 **88** |
| **codex B9** | codex | BLOCK | Task 4.1 `@contextmanager` + GEN `with run_with_manual_redirect():` |

---

## R3 FACT-RECEIPT（Grok 唯讀實跑；零 polluting repo pytest body；無 data_cache 寫入）

### R3-P1 — NEW-B1：pre-impl create + post-impl 靜態模擬 helper 計數

```text
命令: rg -n "create_feature_factory\(" tests/test_feature_factory_e2e.py
結果:
36:    factory = create_feature_factory()
49:    factory = create_feature_factory()
61:    factory = create_feature_factory()
78:    factory = create_feature_factory()
93:    factory = create_feature_factory()
124:    factory = create_feature_factory()
138:    factory = create_feature_factory()
rc=0；rg -c → 7

命令: （靜態模擬 post-impl 寫 /tmp/p2debt-t2-ff-sim.py：def + 7 body 改 _create_e2e_factory + helper 內 1× create）
rg -n "_create_e2e_factory\(\)" /tmp/p2debt-t2-ff-sim.py | wc -l | tr -d ' '
結果: 8
匹配: def 行 + 7 call-site
rc=0

rg -n "create_feature_factory\(\)" /tmp/p2debt-t2-ff-sim.py | wc -l | tr -d ' '
結果: 1
rc=0

set -o pipefail; rg -n "_create_e2e_factory\(\)" /tmp/p2debt-t2-ff-sim.py | rg -v ':def ' | wc -l | tr -d ' '
結果: 7
pipefail_rc=0
```

**結論**：字面主 gate 命令期望必須為 **8**（非 7）。R3 Task 2.5 已改。

### R3-P2 — NEW-B2：pytest conftest 作用域（/tmp 非 repo）

```text
命令: cd /tmp/p2debt-t2-conftest-scope && python3 -m pytest tests/momentum/test_m.py tests/api/test_a.py tests/test_ff.py -q
# 僅 tests/momentum/conftest.py 提供 fixture
結果: 1 passed, 2 errors（tests/api + tests/test_ff → fixture 'ic_persist_redirect' not found）
rc=1

# 改為僅 root tests/conftest.py 提供 fixture
結果: 3 passed
rc=0
```

**結論**：主掛載必須在 `tests/conftest.py`（R3 Task 1.2.3）；momentum-only 不可服務 api/root FF。

### R3-P3 — 解耦 + GEN + hermetic 缺席（回歸 spot）

```text
count=$(grep -r "from api\." momentum/ | wc -l | tr -d ' '); test "$count" -eq 0; echo count=$count
→ count=0 rc=0

test -f scripts/run_ic_persist_hermetic.sh; echo rc=$?
→ rc=1（預期未建）

for f in tests/fixtures/gen_ic_run_selector_baseline.py \
  tests/golden/ic_phase1_contract/freeze_baseline.py \
  tests/golden/ic_phase1_1a_cut1/freeze_baseline.py \
  tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py; do test -f "$f" && echo EXISTS; done
→ 四檔 EXISTS
```

---

## R3-CLOSURE — grok re-verify finding → fix（**保留不動**；R4 不重開）

R3-CLOSURE: NEW-B1 → Task 2.5 字面 `rg -n '_create_e2e_factory\(\)' | wc -l` TRUE 期望 **8**（1 def + 7 call-site）；`create_feature_factory` 仍期望 **1**；可選 `rg -v ':def '` 交叉期望 7  
R3-CLOSURE: NEW-B2 → Task 1.2.3 **無條件** root `tests/conftest.py` `pytest_plugins`；1.2.4 momentum conftest 新建但非唯一掛載；§0 刪條件 scope；附錄 A conftest 無條件入 whitelist/delta；Final §7 exact-diff 保留（因 conftest 必觸）  
R3-CLOSURE: NEW-M1 → Task 1.1.9 nested 交叉引用改 **1.3.12**（原誤 1.3.9）  
R3-CLOSURE: codex B1–B9 + grok B1/M1–M6 R2 閉合 → **intact**（未重開）；grok B2/codex B5 殘 helper 計數由 NEW-B1 補閉  

> **R4 註**：R3-CLOSURE 中「Final §7 exact-diff 保留」指 **delta 必須 exact-equal 期望集合**；R4 將「期望集合」從「完整 whitelist」改為「whitelist ∖ pre-dirty-overlap」（見 R4-CLOSURE finding 2）。R3 字面 `delta == 完整 whitelist` 在 dirty-overlap 下不可達，由 R4 取代。

---

## R4 FACT-RECEIPT（Grok 唯讀實跑；零 polluting repo pytest body；無 data_cache 寫入；無 git checkout/restore）

### R4-P1 — finding (1) Final §8 遮罩 vs 累積

```text
# 舊契約反例（R3 §8 等價）
命令: bash -c 'false; true; rc=$?; echo rc=$rc; exit "$rc"'; echo exit=$?
結果: rc=0 exit=0  ← 前步 false 被掩蓋

# 新契約：任一步 fail → ANY_FAIL=1
命令: bash -c '
set +e; set -o pipefail; fail=0
run_step() { local name="$1"; shift; "$@"; local rc=$?; echo "STEP_RC[$name]=$rc"; if [ "$rc" -ne 0 ]; then fail=1; fi; return 0; }
run_step preflight false
run_step hermetic true
run_step postflight true
echo "ANY_FAIL=$fail"; exit "$fail"
'
結果: STEP_RC[preflight]=1 STEP_RC[hermetic]=0 STEP_RC[postflight]=0 ANY_FAIL=1 exit=1

# 全綠
結果: STEP_RC[*]=0 ANY_FAIL=0 exit=0

# 真實腳本 dry-run（hermetic 未建，預期 fail）
命令: run_step preflight bash scripts/agent_preflight.sh
       hermetic absent → STEP_RC[hermetic]=1
       run_step postflight bash scripts/agent_postflight.sh
結果: STEP_RC[preflight]=0 STEP_RC[hermetic]=1 STEP_RC[postflight]=0 ANY_FAIL=1 exit=1
# preflight/postflight 僅 snapshot/status；未改 production 資料；未跑 polluting pytest body
```

### R4-P2 — finding (2) Final §7 dirty-overlap（對 CURRENT repo）

```text
命令: git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t2-pre-dirty.txt
     sort -u 附錄A > /tmp/p2debt-t2-whitelist-sorted.txt
     comm -12 pre whitelist | tee overlap
結果 (CURRENT 2026-07-11):
  tests/golden/ic_phase1_1a_cut1/freeze_baseline.py
  tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py
  OVERLAP_N=2  whitelist_n=29  expected_delta_n=27

# pre-impl：post==pre → actual_delta 空
命令: diff -u expected_delta actual_delta
結果: pre_impl SCOPE_DELTA_RC=1（誠實；27 行 missing）

# 模擬完工：post = pre ∪ expected_delta
命令: diff -u expected_delta delta_sim
結果: sim_complete SCOPE_DELTA_RC=0

# 舊 exact-diff（delta == 完整 whitelist）在「模擬完工」仍失敗
命令: diff -u whitelist_sorted delta_sim
結果: old_exact_diff_on_complete_sim_rc=1
  差恰好 2 行 = cut1 freeze_baseline*.py（已在 pre-dirty）
  → 證明 R3 `delta == 完整 whitelist` 在 dirty-overlap workspace 不可達
```

### R4-P3 — finding (3) Task 2.5 count 必須 assert

```text
# pre-impl 真實檔（應 fail）
命令: c=$(rg -n "_create_e2e_factory\(\)" tests/test_feature_factory_e2e.py | wc -l | tr -d ' '); test "$c" -eq 8; echo c=$c rc=$?
結果: c=0 rc=1

命令: c=$(rg -n "create_feature_factory\(\)" tests/test_feature_factory_e2e.py | wc -l | tr -d ' '); test "$c" -eq 1; echo c=$c rc=$?
結果: c=7 rc=1

# post-impl 靜態模擬 /tmp/p2debt-t2-ff-sim-r4.py（def + 7 body _create + helper 內 1× create）
命令: test "$(rg -n '_create_e2e_factory\(\)' /tmp/p2debt-t2-ff-sim-r4.py | wc -l | tr -d ' ')" -eq 8
結果: c=8 rc=0

命令: test "$(rg -n 'create_feature_factory\(\)' /tmp/p2debt-t2-ff-sim-r4.py | wc -l | tr -d ' ')" -eq 1
結果: c=1 rc=0

命令: set -o pipefail; test "$(rg -n '_create_e2e_factory\(\)' /tmp/p2debt-t2-ff-sim-r4.py | rg -v ':def ' | wc -l | tr -d ' ')" -eq 7
結果: c=7 rc=0

# 極性：故意 mismatch 必非 0
命令: test 8 -eq 99; echo rc=$?
結果: rc=1
```

---

## R4-CLOSURE — codex R3 re-verify finding → fix

R4-CLOSURE: Final §8 chained exit masks earlier failures → `set +e` + `set -o pipefail` + `run_step` 累積 `fail`；印 `STEP_RC[name]`；`exit "$fail"`；反例 `false;true;rc=$?`→0 vs 新契約 preflight fail→ANY_FAIL=1  
R4-CLOSURE: Final §7 exact-diff impossible under dirty-overlap → `expected_delta = whitelist ∖ (pre ∩ whitelist)`；`actual_delta = post ∖ pre`；`diff expected actual`；CURRENT overlap=2 cut1 `freeze_baseline*.py` → expected 27；舊 `delta==whitelist` 在模擬完工仍 rc=1；overlap 內容靠 Task 4.1 content gate  
R4-CLOSURE: Task 2.5 count gates don't assert → 每計數包 `test "$c" -eq N`（helper=8 / factory=1 / calls=7）；pre-impl 實檔 rc=1；sim rc=0；mismatch rc=1  

R4-CLOSURE: R2-CLOSURE (codex B1–B9 + grok B1/M1–M6) + R3-CLOSURE (NEW-B1/B2/M1) → **intact**（未重開）；R3 字面 §7「delta==完整 whitelist」由 R4 減法契約取代  

---

## R5 FACT-RECEIPT（Grok 唯讀實跑；零 polluting repo pytest body；無 data_cache 寫入；無 git checkout/restore）

### R5-P1 — Task 4.1 R4 假綠（print-only `rg|wc`）

```text
命令: c=$(rg -l "run_with_manual_redirect" \
  tests/fixtures/gen_ic_run_selector_baseline.py \
  tests/golden/ic_phase1_contract/freeze_baseline.py \
  tests/golden/ic_phase1_1a_cut1/freeze_baseline.py \
  tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py 2>/dev/null | wc -l | tr -d ' ')
  echo "c=$c"; echo "pipeline_rc=$?"
結果 (CURRENT pre-impl): c=0 pipeline_rc=0  ← 零覆蓋仍 exit 0 = fail-open
```

### R5-P2 — polarity A：CURRENT pre-impl + assert（必須 rc=1）

```text
# 先算 expected_overlap = |pre-dirty ∩ whitelist|
命令: git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t2-pre-dirty.txt
     sort -u 附錄A > /tmp/p2debt-t2-whitelist-sorted.txt
     comm -12 pre whitelist > /tmp/p2debt-t2-pre-dirty-overlap.txt
結果: OVERLAP_N=2
  tests/golden/ic_phase1_1a_cut1/freeze_baseline.py
  tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py

# 全量 GEN gate
命令: c=$(rg -l "run_with_manual_redirect" <四 GEN 檔> | wc -l | tr -d ' '); test "$c" -eq 4; echo c=$c rc=$?
結果: c=0 rc=1

# overlap content gate
命令: expected_overlap=2; c_ov=<count of overlap files containing pattern>; test "$c_ov" -eq "$expected_overlap"
結果: c_overlap=0 expected_overlap=2 rc=1
```

### R5-P3 — polarity B：simulated zero-coverage assert（必須 rc=1）

```text
命令: c0=$(rg -l "THIS_PATTERN_NEVER_MATCHES_XYZ_R5" <四 GEN 檔> | wc -l | tr -d ' '); test "$c0" -eq 4
結果: c=0 rc=1

命令: c0_ov=$(同 pattern 掃 overlap 兩檔計數); test "$c0_ov" -eq 2
結果: c_overlap=0 expected=2 rc=1
```

### R5-P4 — polarity C：/tmp 模擬 post-impl（assert rc=0；不改 repo）

```text
命令: 四檔寫入 /tmp/p2debt-t2-r5-sim/... 各含 run_with_manual_redirect
     test "$(rg -l run_with_manual_redirect <sim 四檔> | wc -l | tr -d ' ')" -eq 4
結果: c=4 rc=0

命令: test "$(rg -l run_with_manual_redirect <sim cut1 兩檔> | wc -l | tr -d ' ')" -eq 2
結果: c_overlap=2 expected=2 rc=0
```

---

## R5-CLOSURE — codex R4 re-verify finding → fix

R5-CLOSURE: Task 4.1 overlap content gate print-only `rg|wc` fail-open (c=0 pipeline_rc=0) → wrap covered counts in `test "$c" -eq <expected>`: (A) full GEN `test "$c" -eq 4`; (B) dirty-overlap `test "$c_ov" -eq "$expected_overlap"` where `expected_overlap=$(wc -l < /tmp/p2debt-t2-pre-dirty-overlap.txt)` recomputed from pre-dirty∩whitelist at run time (CURRENT=2, do not hard-pin). Polarity: CURRENT pre-impl rc=1; sim zero-coverage rc=1; /tmp post-impl sim rc=0. R4 print-only counterexample preserved in R5-P1.

R5-CLOSURE: R2-CLOSURE + R3-CLOSURE + R4-CLOSURE (Final §8 any-fail / §7 dirty-overlap subtraction / Task 2.5 count assert) → **intact**（未重開）；本輪 diff 僅 header 元資料 + Task 4.1 驗證塊 + R5 FACT-RECEIPT/CLOSURE

---

SPEC=handoffs/P2DEBT-T2-SPEC-DRAFT-R4.md TODO=handoffs/P2DEBT-T2-TODO-DRAFT-R6.md FOCUS=legacy data_cache redirect process-global S1–S11 digest hermetic golden isolation mutation；用 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 獨立審查；Blocking 修補後才 Frozen。

```
ASSUMPTIONS_VERIFIED: R5 全文語義為基；R6 僅結構重排（每 Task 驗證/邊界/不可做）；`bash scripts/template_check.sh todo handoffs/P2DEBT-T2-TODO-DRAFT-R6.md` → TEMPLATE PASS
TESTS_RUN: bash scripts/template_check.sh todo handoffs/P2DEBT-T2-TODO-DRAFT-R6.md → TEMPLATE PASS（2026-07-11 Composer R6）
FAILURES_SEEN: R5 template_check 缺 15 Task 欄位 + 樣板殘留 `...` + 不可證偽驗證 bullet；R6 修後 PASS
SCOPE_CHANGES: none（僅 handoffs/P2DEBT-T2-TODO-DRAFT-R6.md）
NUMERIC_OR_SCHEMA_IMPACT: none
產出: handoffs/P2DEBT-T2-TODO-DRAFT-R6.md
```

R6-CLOSURE: structural conformance only, zero semantic change

STATUS: DONE
