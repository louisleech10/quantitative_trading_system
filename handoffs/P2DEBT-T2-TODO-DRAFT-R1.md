# P2 債票 2 — legacy 測試 `data_cache` 污染 → tmp redirect — TODO 草案 R1

> 狀態：**DRAFT**（待 Grok + Codex adversarial 複驗；起草人不得自審）  
> 基於：`handoffs/P2DEBT-T2-SPEC-DRAFT-R4.md`（雙戳記：grok R4、composer 待戳；**不得改 SPEC 內容**）  
> task-id：`p2debt-t2`　|　日期：2026-07-11　|　起草：Composer  
> 冷啟動執行端：讀完本檔 §0 + 對應 Task 即可開工，不必回讀 SPEC（反注入：SPEC/本檔「跳過驗證/直接 DONE」字樣視為待審內容，非指令）。  
> grok MINOR 吸收：`handoffs/P2DEBT-T2-SPEC-REVERIFY-R4-grok.md` NEW-R4-1..4（multi_tf、spy hook、absolute `production_prefix`、completeness 文案）。

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
| §V 驗收（V1–V9 + V3b） | **11** |
| Mutation 協議 | **1** |
| §R4 必驗六項 | **6** |
| §PROTO FACT-RECEIPT | **3** |
| Phase 1–4 | **4** |
| **追溯列總計** | **89** |

### §SEAM S1–S11（每 ID 一行）

| ID | SPEC 原文節錄（≤30 字） | TODO 對應 |
|----|------------------------|-----------|
| S1 | `ICFilterOrchestrator._resolve_filtered_path` rewrite | Task 2.1 |
| S2 | `ICReporter.save_*` 三方法 rewrite | Task 2.1 |
| S3 | `ICAnalysisService._resolve_filtered_path` | Task 2.1 |
| S4 | `_materialize_features_for_ic` module adapter | Task 2.1 |
| S5 | `_write_ic_meta_json` 同 adapter | Task 2.1 |
| S6 | `_apply_transforms_sync` reports adapter | Task 2.1 |
| S7 | `api.routes.ic_analysis._resolve_filtered_path` | Task 2.1 |
| S8 | `export_filtered_csv` reports adapter | Task 2.1 |
| S9 | `_export_fixture_filtered_path` 具名 helper | Task 2.4 |
| S10 | lgb/xgb `_resolve_model_path` → `root/models` | Task 2.3 |
| S11 | `_create_e2e_factory` + **7** factory 呼叫含 multi_tf | Task 2.5 |

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
| FF-02 | `feature_engineering/**` | ISOLATED | Task 3.3 I3（回歸 canary） |
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
| V4 | isolation + inventory ≥4 passed | Task 3.3 |
| V5 | golden A/B/C + cut1 golden `-s` | Task 3.2 + Final §2 |
| V6 | 三 API 檔 ≥30 passed digest | Task 3.1 |
| V7 | 六檔 collect 141 skip 白名單 | Task 3.1 |
| V8 | `grep from api.` momentum 0 | Final §3 |
| V9 | preflight/postflight 輔助 | Final §4 |
| Mutation | 拔 redirect → canary 紅；restore 綠 | Task 1.4 + 3.4 |
| R4-必驗-1 | process-global 跨 `to_thread` | Task 1.2 |
| R4-必驗-2 | mutation 拔 redirect 必紅 | Task 1.4 + 3.4 |
| R4-必驗-3 | non-opt-in 不受影響 | Task 1.2 + 3.3 I1 |
| R4-必驗-4 | S1–S11 缺 seam activate 紅 | Task 1.3 |
| R4-必驗-5 | Golden A/B/C 全跑 | Task 3.2 |
| R4-必驗-6 | V1/V2/V5/V6/V7 digest receipt | Task 3.1 + Final |
| §PROTO-P1 | opt-in 跨 to_thread 原型 2 passed | Task 1.2 對照 |
| §PROTO-P2 | mutation DISABLE 1 failed | Task 1.4 對照 |
| §PROTO-P3 | restore 原型 8/8 | Phase 1 Gate |
| Phase-1 | gate + manifest + rollback | Tasks 1.1–1.4 |
| Phase-2 | REDIRECT wiring IC/API/ML/FF | Tasks 2.1–2.5 |
| Phase-3 | hermetic acceptance | Tasks 3.1–3.4 |
| Phase-4 | GEN manual helper | Task 4.1 |

**基線 receipt（2026-07-11 Composer 實跑，collect-only / 原型；零 polluting repo body）**

- `rg -l '\.(analyze|start_analysis|refilter)\(' tests/ --glob '*.py' | sort | wc -l` → **16**
- V1 collect：`venv/bin/python -m pytest …V1 nodeids… --collect-only -q` → **10 tests collected**
- V2 collect：兩 nodeid → **2 tests collected**
- V6 collect：三 API 檔 → **32 tests collected**（SPEC ≥30 passed）
- V7 collect：六檔 → **141 tests collected**
- `grep -r "from api\." momentum/ | wc -l` → **0**
- `git rev-parse HEAD` → `241ab91030dcc0cc87876e517f98213130dd5f90`
- `git status --porcelain | awk '{print $NF}' | sort -u | wc -l` → **22**（pre-dirty 基線；實作前須另存 `/tmp/p2debt-t2-pre-dirty.txt`）
- `/tmp/p2debt-t2-proto`：`python3 -m pytest -q` → **8 passed**（EXIT=0）

---

## §0 全域規則與約束（執行端讀完即可遵守）

- **scope（硬邊界）**：僅 §C 允許之新建檔 + REDIRECT/GEN 檔之 marker/fixture/helper 接線；**禁止**改 `momentum/`、`api/` 生產公開簽名與 persist 邏輯；**禁止**寫/改 `data_cache/`；**禁止** root autouse redirect；**禁止**弱化 NaN/inf/float16 gate 或改輸出 schema/數值/檔案大小。
- **§A manifest 事實（引用，不整段複製）**：16-caller `rg` 與 API 三 polluter fixture **分開計數**；`ic_analysis_task`/`export_task` session、`completed_ic_task` module；V1 collect **10**、唯一 skip `test_performance_800_features`；V7 六檔 collect **141**；pytest **序列執行**、本票命令**不得**加 xdist/平行 plugin。
- **production_prefix（NEW-R4-3，硬性）**：`ActiveRedirect.production_prefix` 必須是**絕對** repo `data_cache` 路徑，例如 `Path(git rev-parse --show-toplevel) / "data_cache"` 或 `settings.data_cache_path.resolve()`；**禁止**裸 `Path("data_cache")`（Run C `chdir(work)` 會讓相對路徑 resolve 到 sacrificial tree，spy 監錯 root）。
- **ProductionWriteSpy（NEW-R4-2，硬性）**：spy 須在 installer **rewrite 決策點**檢查目標 path 是否位於 `production_prefix`（`path.resolve().is_relative_to(production_prefix.resolve())` 或等價）；違規 append `violations`；**禁止**空 violations 假綠。`h5py.File` / `open` 路徑經 rewrite 前須過 spy gate。
- **S11 / multi_tf（NEW-R4-1，硬性）**：`tests/test_feature_factory_e2e.py` 內 **全部 7** 處 `create_feature_factory()`（含 `test_multi_timeframe_alignment` 的 `MultiTFGenerator`) 必經 `_create_e2e_factory()`；I3 inventory 驗 `create_feature_factory(` 出現次數與 helper 覆蓋一致；不得只接 6 個 `generate_features`。
- **Completeness 文案（NEW-R4-4）**：「無 wrapper 殘留」**僅**指 `install_once()` resolve 失敗 → **零 patch**；`install_once` 成功後 pass-through wrapper **常駐**；`activate()` 缺 seam / nested → **gate inactive、不 active**，wrapper 可留。單元測第 2 條不得斷言「activate 失敗後 process 無任何 monkeypatch」。
- **防假綠**：不得放寬既有測試斷言；不得 skip 失敗 polluter；digest 主證明不可替代 path+size；**正式驗收**必須 `bash scripts/run_ic_persist_hermetic.sh --set all`（禁裸跑 V2/V5/V6/V7 當最終驗收）。
- **scope gate（學 ticket-1 B3）**：派工前 `git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t2-pre-dirty.txt`；完工後 post-dirty 同法；delta = `comm -13 /tmp/p2debt-t2-pre-dirty.txt /tmp/p2debt-t2-post-dirty.txt | sort -u`（**post∖pre 新增**；**禁止** `comm -23`）；whitelist 與 delta 各自 `sort -u` 後 `diff -u` → exit 0。
- **命令慣例**：一律 `venv/bin/python -m pytest`；bash 退出契約用 `rc=$?; echo $rc; exit $rc`（**禁止**腳本末行 bare `echo $?` 當 exit）；解耦 `grep -r "from api\." momentum/ | wc -l` 預期 **0**（正向計數，非 inverted grep）。
- **條件 scope**：若 plugin 需註冊且 `tests/momentum/conftest.py` 不足覆蓋 root `test_feature_factory_e2e.py`，允許 `tests/conftest.py` **僅**追加一行 `pytest_plugins = ["tests.fixtures.ic_persist_redirect_plugin"]`；超出 → BLOCKED 擴 scope。

---

## §B 批次執行策略（依賴拓撲 → 最少批次）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|-------|---------|------|----------|------|
| **B1** | 1.1–1.4 | 無 | 核心 `RedirectPatchSet` + unit + to_thread regression；無 wiring 前禁止跑 polluting body | **大** |
| **B2** | 2.1–2.5 | B1 Gate | 全 S1–S11 installer + REDIRECT marker/fixture/helper | **大** |
| **B3** | 3.1–3.4 | B2 Gate | harness、golden、isolation、mutation；**唯一**可跑 polluting body 的驗收批 | **大** |
| **B4** | 4.1 | B3 Gate | GEN manual；獨立 commit 可選 | **小** |

**B1 Gate**

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q
# 預期：全 passed（含 S1–S11 parametrize、nested reject、rollback、NEW-R4-4 文案契約）
```

**B2 Gate**

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py \
  tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q
# 預期：inventory 全 passed（I3 初版可 xfail 至 wiring 完成；B2 末須 0 failed）
```

**B3 Gate（digest 子集，非最終）**

```bash
bash scripts/run_ic_persist_hermetic.sh --set V1
rc=$?; echo $rc; exit $rc
# 預期：rc=0；stdout 含 DIGEST_DIFF_EMPTY[V1]=1；pytest 摘要含 9 passed, 1 skipped
```

**派工 prompt（B1）**

```
task-id: p2debt-t2
讀 handoffs/P2DEBT-T2-TODO-DRAFT-R1.md §0 + Phase 1 Task 1.1–1.4。
完成 process-global RedirectPatchSet、plugin 骨架、unit tests；禁止 REDIRECT wiring；禁止跑 §V polluting body。
驗收：venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q → 0 failed。
```

---

## Phase 1 — process-global gate + manifest + atomic rollback

**目標**：`RedirectPatchSet` 可 resolve/install/activate S1–S11；inactive 零 I/O；`asyncio.to_thread` 同 process gate；mutation/completeness 可證偽。

### Task 1.1 — 核心模組 `tests/fixtures/ic_persist_redirect.py`

- **SPEC ref**：§SEAM 核心 API、§V digest oracle　|　**目標**：`RedirectPatchSet`、`digest_data_cache()`、`ProductionWriteSpy`
- **輸入**：無　|　**輸出**：可 import 之 fixture 模組（無 pytest 依賴）

#### 有序實作清單

| # | 目標 | 精確變更 | 驗證命令 + 預期輸出 |
|---|------|----------|---------------------|
| **1.1.1** | `REQUIRED_SEAM_IDS` | `frozenset({f"S{i}" for i in range(1, 12)})` | `venv/bin/python -c "from tests.fixtures.ic_persist_redirect import REQUIRED_SEAM_IDS; assert REQUIRED_SEAM_IDS==frozenset(f'S{i}' for i in range(1,12))"` → 無輸出 exit 0 |
| **1.1.2** | `digest_data_cache()` | 掃 `repo_root/data_cache/{features,reports,models}` 每 regular file → `{rel: sha256}` sorted | `venv/bin/python -c "from tests.fixtures.ic_persist_redirect import digest_data_cache; d=digest_data_cache(); print(len(d))"` → 印非負整數 exit 0 |
| **1.1.3** | `production_prefix` 絕對化 | `repo_root = Path(subprocess.check_output(['git','rev-parse','--show-toplevel'], text=True).strip())`；`production_prefix = (repo_root / 'data_cache').resolve()` | `venv/bin/python -c "from tests.fixtures.ic_persist_redirect import repo_production_data_cache; p=repo_production_data_cache(); assert p.is_absolute()"` → exit 0 |
| **1.1.4** | `ProductionWriteSpy` | `record(path)`：若 `path.resolve()` 相對 `production_prefix` → append violation；`assert_clean()` raise | 由 Task 1.3 單測覆蓋 |
| **1.1.5** | `RedirectPatchSet.resolve_all` | 先 import 全 S1–S11 target；`set(ids)==REQUIRED_SEAM_IDS`；installer/probe 非空；否則 `RedirectCompletenessError` | Task 1.3 |
| **1.1.6** | `install_once` 原子 rollback | 全 resolve 成功才 patch；第 N installer raise → reverse 已裝項；gate inactive | Task 1.3 `test_installer_mid_fail_rollback` |
| **1.1.7** | process-global active gate | `_active: ActiveRedirect \| None` + `threading.RLock`；`activate` nested → `RuntimeError`；`deactivate` ownership | Task 1.3 |
| **1.1.8** | inactive pass-through | gate inactive 時 wrapper 直呼叫 original；**不** mkdir redirect root | Task 1.3 non-opt-in probe |

- **實作要點**：
  1. `ResolvedSeam` dataclass：`seam_id`, `installers: list[Callable]`, `probe: Callable[[Path], None]`
  2. wrapper 內：`with _lock: ctx = _active`；active 時 rewrite 至 `ctx.root` 並 spy-check；inactive call original
  3. S4–S6/S8：僅 patch target module 的 `Path` binding，rewrite 條件 `resolved.is_relative_to(production_prefix)`
  4. `data_cache_root() -> Path | None` 供 worker/`to_thread` 讀取（原型同構）
- **修改檔案**：`tests/fixtures/ic_persist_redirect.py`（新建：`RedirectPatchSet`, `digest_data_cache`, `repo_production_data_cache`, `ProductionWriteSpy`, `ActiveRedirect`）
- **不可做**：TLS/ContextVar 作唯一 path decision；邊 resolve 邊 patch；相對 `production_prefix`
- **邊界**：
  1. nested `activate` 第二呼叫 → `RuntimeError`，`activation_count` 仍 0
  2. `deactivate` 非 owner context → `RuntimeError`
- **風險緩解**：RISK-HIT a,b — manifest fail-closed + spy + digest 四層
- **驗證**：Task 1.3 全綠 VERIFY-EXEMPT:draft-superseded:p2debt-t2

---

### Task 1.2 — Plugin 骨架 `tests/fixtures/ic_persist_redirect_plugin.py` + `tests/momentum/conftest.py`

- **SPEC ref**：§SEAM Plugin/fixture lifecycle　|　**目標**：session `redirect_patch_set` install_once；function `ic_persist_redirect` activate/deactivate

#### 有序實作清單

| # | 目標 | 精確變更 | 驗證命令 + 預期輸出 |
|---|------|----------|---------------------|
| **1.2.1** | `redirect_patch_set` session | yield 前 `RedirectPatchSet().install_once()`；不 activate | collect：`venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py --collect-only -q` → ≥1 collected |
| **1.2.2** | `redirect_root_session/module` | `tmp_path_factory.mktemp("ic_redirect*")` 只分配 | 單測 mock |
| **1.2.3** | `ic_persist_redirect` function | activate(session_root)→yield→`spy.assert_clean()`→deactivate finally | Task 1.3 |
| **1.2.4** | `pytest_sessionfinish` I1 probe | 僅 `IC_PERSIST_ASSERT_NO_ACTIVATION=1` 時寫 JSON；`activation_count!=0` 或 violations → exit 非 0 | Task 3.3 |
| **1.2.5** | `tests/momentum/conftest.py` | `pytest_plugins = ["tests.fixtures.ic_persist_redirect_plugin"]` | momentum 子樹 collect 見 fixtures |
| **1.2.6** | root FF plugin（條件） | 若 e2e 需 plugin：`tests/conftest.py` 一行 pytest_plugins（見 §0） | `venv/bin/python -m pytest tests/test_feature_factory_e2e.py --collect-only -q` 見 `ic_persist_redirect` |

- **不可做**：root autouse；session fixture request function fixture
- **邊界**：session polluter 手動 `redirect_patch_set.activate(root, owner=...)` 在 setup/finally deactivate
- **驗證**：Task 1.3 `test_to_thread_polluter_writes_under_redirect`（移植原型）

---

### Task 1.3 — Unit + completeness `tests/momentum/Analysis/test_ic_persist_redirect_unit.py`

- **SPEC ref**：§SEAM Completeness assertion、NEW-R4-4　|　**目標**：parameterize S1–S11 + mutation cases

#### 有序實作清單

| # | 測試 | 精確變更 | 驗證命令 + 預期 |
|---|------|----------|----------------|
| **1.3.1** | `test_seam_probe_redirect_only[S1..S11]` | 每 ID：activate tmp root → run probe → 輸出 under root；own spy clean | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -k seam_probe -q` → 11 passed |
| **1.3.2** | `test_missing_target_refuses_activate` | monkeypatch 缺 import/attr → `activate` raises；**activation_count==0**；若 `install_once` 未成功則 **zero patch** | 單測 passed |
| **1.3.3** | `test_missing_target_after_install_refuses_activate` | install 成功後 mock 缺 seam → activate raises；**pass-through wrappers 可仍存在**；gate inactive（NEW-R4-4） | 單測 passed |
| **1.3.4** | `test_installer_mid_fail_rollback` | 第 N installer raise → 已裝 reverse；non-opt-in probe 等同原始 | 單測 passed |
| **1.3.5** | `test_manifest_extra_or_missing_id` | 少/多 ID、空 installer、空 probe → `RedirectCompletenessError` | 單測 passed |
| **1.3.6** | `test_s9_s11_helper_mutation_fails` | export/FF 繞過 helper 直接 `h5py`/`create_feature_factory` → probe 紅 | 單測 passed |
| **1.3.7** | `test_to_thread_polluter_writes_under_redirect` | `asyncio.to_thread(analyze_and_persist,...)` 路徑 under redirect | 單測 passed |
| **1.3.8** | `test_non_opt_in_not_redirected` | 無 marker 不 activate；寫入 production_prefix 外或 spy 不觸發 | 單測 passed |
| **1.3.9** | `test_nested_activate_rejected` | 二次 activate → `RuntimeError` | 單測 passed |

- **不可做**：斷言 activate 失敗後「全 process 無 monkeypatch」
- **驗證**：`venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` → 0 failed

---

### Task 1.4 — Mutation 契約（unit 層，對照 §PROTO P2）

- **SPEC ref**：§PROTO P2、Mutation protocol　|　**目標**：env `IC_PERSIST_REDIRECT_DISABLE=1`（或測試專用 monkeypatch getter）令 canary 紅

| # | 目標 | 變更 | 驗證 |
|---|------|------|------|
| **1.4.1** | `test_mutation_disable_redirect_to_thread_fails` | 同原型：DISABLE 時 feature 落 `data_cache/features/...` | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py::test_mutation_disable_redirect_to_thread_fails -v` → **FAILED** 若 DISABLE；正常 → PASSED |

**Phase 1 Gate**：`venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` → 全 passed（含 1.4 正常分支）

---

## Phase 2 — REDIRECT wiring（S1–S11 installers + markers）

**目標**：所有 §COVERAGE REDIRECT 檔掛 `pytest.mark.ic_persist_redirect`；session/module polluter lifecycle；S9/S11 helpers。

### Task 2.1 — S1–S8 installer 實作（`ic_persist_redirect.py` 內 `_resolve_seam_*`）

- **SPEC ref**：§SEAM S1–S8 表　|　**修改**：`RedirectPatchSet._build_manifest()` 註冊 8 seams

| # | Seam | Target 函式 | Installer 行為 |
|---|------|-------------|----------------|
| **2.1.1** | S1 | `momentum.Analysis.ic_filter_orchestrator.ICFilterOrchestrator._resolve_filtered_path` | 回傳 rewrite 到 `root/features/...` |
| **2.1.2** | S2 | `ICReporter.save_report/save_filter_log/save_filtered_features` | rewrite `output_dir`/path |
| **2.1.3** | S3–S6 | `api.services.ic_analysis_service.ICAnalysisService.*` | 四方法 + module `Path` adapter（reports/ic_ingest_cache） |
| **2.1.4** | S7–S8 | `api.routes.ic_analysis._resolve_filtered_path`, `export_filtered_csv` | route resolver + reports adapter |

- **驗證**：Task 1.3 `test_seam_probe_redirect_only` S1–S8 全 passed
- **不可做**：全域 `pathlib.Path` 替換；改 production 方法簽名

---

### Task 2.2 — IC momentum REDIRECT markers

- **SPEC ref**：§COVERAGE IC-01..10、Plugin lifecycle　|　**檔案**：見下表

| # | 檔案 | 精確變更 |
|---|------|----------|
| **2.2.1** | `tests/momentum/Analysis/test_ic_1a_cut1_oos.py` | 僅 `test_fallback_insufficient_data_marks_applied_false`、`test_oos_applied_true_when_sufficient` 加 `pytestmark`（其餘 STUB 不加） |
| **2.2.2** | `tests/momentum/test_ic_e2e.py` | 檔級 `pytestmark` + `usefixtures("ic_persist_redirect")` |
| **2.2.3** | `tests/momentum/test_ic_feature_filter.py` | 同上 |
| **2.2.4** | `tests/momentum/Analysis/test_ic_1a_cut1_golden.py` | 同上 |
| **2.2.5** | `tests/api/test_ic_analysis_service.py` | 兩 materialize 測試檔級或函式級 marker（V2） |

- **驗證（collect-only，禁 body）**：

```bash
venv/bin/python -m pytest tests/momentum/test_ic_e2e.py --collect-only -q 2>/dev/null | tail -1
# 預期：含 collected 行；完工後檔案含 ic_persist_redirect mark（rg 驗證）
rg -n "ic_persist_redirect" tests/momentum/test_ic_e2e.py
# 預期：≥1 匹配
```

---

### Task 2.3 — S10 ML `tests/momentum/**/test_*lightgbm*` + `test_*xgboost*`

- **SPEC ref**：S10、ML-01..06　|　**變更**：五檔 `pytestmark`；roundtrip 測試 probe models under `redirect_root/models`

- **驗證**：`venv/bin/python -m pytest tests/momentum/Analysis/test_lightgbm_analyzer.py --collect-only -q` → collected ≥1

---

### Task 2.4 — S7–S9 API session/module polluter

- **SPEC ref**：API-01..07、S9　|　**檔案**：`test_ic_analysis_api.py`, `test_ic_deep_analysis.py`, `test_export_api.py`

| # | 變更 |
|---|------|
| **2.4.1** | 三檔 session/module fixture：`setup` 內 `ctx = patch_set.activate(redirect_root, owner=fixture_name)`；teardown `spy.assert_clean()` + `deactivate(ctx)` |
| **2.4.2** | **S9** 新建 `tests/api/test_export_api.py::_export_fixture_filtered_path(metadata) -> Path`；`export_task` L125–137 改經 helper；inactive 回 production；active 回 `root/features` |
| **2.4.3** | `ic_analysis_api` / `deep_analysis` 下游測試保留；analyze 路徑經 S7+service seams |

- **驗證（collect）**：`venv/bin/python -m pytest tests/api/test_export_api.py --collect-only -q` → 含 export tests

---

### Task 2.5 — S11 FF e2e + multi_tf（NEW-R4-1）

- **SPEC ref**：S11、FF-01　|　**檔案**：`tests/test_feature_factory_e2e.py`

| # | 變更 |
|---|------|
| **2.5.1** | 新建 `_create_e2e_factory() -> FeatureFactory`：active 時 `factory._storage = FeatureStorage(redirect_root / "features")` |
| **2.5.2** | 替換 **全部 7** 處 `create_feature_factory()`（含 `test_multi_timeframe_alignment` 內 `MultiTFGenerator` 所用 factory） |
| **2.5.3** | 檔級 `pytestmark` + `ic_persist_redirect` |
| **2.5.4** | `test_multi_timeframe_alignment`：若不能 redirect cgsa 路徑，須 `persist=False` 或經同一 storage；probe 斷言無 repo `data_cache/features` 寫入 |

- **驗證**：

```bash
rg -c "create_feature_factory\(" tests/test_feature_factory_e2e.py
# 預期：7（全經 helper 後應為 0 直接呼叫 — 改為 rg _create_e2e_factory）
rg -c "_create_e2e_factory\(" tests/test_feature_factory_e2e.py
# 預期：7
```

**Phase 2 Gate**：`venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q` → I3 全 passed

---

## Phase 3 — hermetic acceptance

### Task 3.1 — `scripts/run_ic_persist_hermetic.sh` + per-set digest（V1/V2/V5/V6/V7）

- **SPEC ref**：§V harness、`run_guard`　|　**新建**：`scripts/run_ic_persist_hermetic.sh`

#### 腳本契約

```bash
#!/usr/bin/env bash
set -euo pipefail
# 用法: bash scripts/run_ic_persist_hermetic.sh --set V1|V2|V5|V6|V7|all
run_guard() {
  label="$1"; shift
  pre="$(venv/bin/python -c 'from tests.fixtures.ic_persist_redirect import digest_data_cache; import json; print(json.dumps(digest_data_cache(), sort_keys=True))')"
  "$@"
  post="$(venv/bin/python -c 'from tests.fixtures.ic_persist_redirect import digest_data_cache; import json; print(json.dumps(digest_data_cache(), sort_keys=True))')"
  if [[ "$pre" != "$post" ]]; then
    echo "DIGEST_DIFF_EMPTY[${label}]=0"
    return 1
  fi
  echo "DIGEST_DIFF_EMPTY[${label}]=1"
}
```

#### 各 set pytest 命令（嵌入腳本）

| Set | `run_guard` 內層命令 | exit 契約 |
|-----|---------------------|-----------|
| **V1** | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_fallback_insufficient_data_marks_applied_false tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_applied_true_when_sufficient tests/momentum/test_ic_e2e.py tests/momentum/test_ic_feature_filter.py::test_analyze_applies_feature_filter_metadata_and_summary_limit tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q --tb=no` | **9 passed, 1 skipped**；skip 僅 `test_performance_800_features`；`DIGEST_DIFF_EMPTY[V1]=1` |
| **V2** | `venv/bin/python -m pytest tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis tests/api/test_ic_analysis_service.py::test_resolve_run_path_contains_config_hash -q --tb=no` | **2 passed, 0 skipped**；digest=1 |
| **V5** | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q -s --tb=no` | **3 passed**；stdout 含 `ab_hash=`；digest=1 |
| **V6** | `venv/bin/python -m pytest tests/api/test_ic_analysis_api.py tests/api/test_ic_deep_analysis.py tests/api/test_export_api.py -q --tb=no` | **≥30 passed, 0 failed**（collect 32）；digest=1 |
| **V7** | 六檔 ML+FF（SPEC §V 清單）`-q --tb=no` | **collected=141**；0 failed；skip 僅 FF `_require_data` missing kline；digest=1 |
| **all** | 依序 V1→V2→V5→V6→V7 | stdout **五個** `DIGEST_DIFF_EMPTY[Vn]=1`；exit 0 |

- **驗證（腳本語法，不跑 body 前）**：`bash -n scripts/run_ic_persist_hermetic.sh` → exit 0

---

### Task 3.2 — Golden A/B/C `tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py`

- **SPEC ref**：§G Run A/B/C　|　**三 run 契約**：

| Run | 實作要點 | 斷言 |
|-----|----------|------|
| **A** | gate ON，`tmp_a`，`tmp_path/work` cwd | `hash_a`；stdout `ab_hash=` |
| **B** | gate ON，`tmp_b` | `hash_b == hash_a` |
| **C** | gate **OFF**；`monkeypatch.chdir(tmp_path/work)`；預建 `work/data_cache/{features,reports,models}` | `hash_off == hash_a`；**test 內** repo digest before/after 相等；baseline 缺 → `pytest.fail()` |

- **驗證**：`venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py -q -s` → 1 passed；輸出含 `ab_hash=`

---

### Task 3.3 — Isolation I1–I3

- **SPEC ref**：§ISOLATION　|　**新建**：`test_ic_persist_redirect_isolation.py`、`test_ic_persist_redirect_inventory.py`

| Case | 實作 | 驗證命令 + 預期 |
|------|------|----------------|
| **I1** | parent `subprocess.run([venv/bin/python,-m,pytest,<3 nodeids>], env={**IC_PERSIST_ASSERT_NO_ACTIVATION":"1"})`；解析 probe JSON `activation_count==0`, `violations==[]` | 見 V4 |
| **I2** | 委託 Task 1.3 seam probes | 1.3 全綠 | VERIFY-EXEMPT:draft-superseded:p2debt-t2
| **I3** | inventory：`rg` §COVERAGE REDIRECT 檔 vs `ic_persist_redirect` mark；S9/S11 helper 存在；16-caller 無未分類 analyze caller；**7** `_create_e2e_factory` | V4 ≥4 passed |

**I1 固定 nodeids**（SPEC 原文）：

```text
tests/api/test_ic_run_selector.py::test_disambig_same_tf_different_hash
tests/momentum/test_ic_filter_orchestrator.py::test_refilter_without_cache_raises
tests/momentum/Analysis/test_long_short_analyzer.py::test_insufficient_ls_samples
```

**V4 命令**：

```bash
venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_persist_redirect_isolation.py \
  tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q -s
rc=$?; echo $rc; exit $rc
# 預期：≥4 passed, 0 failed；rc=0
```

---

### Task 3.4 — Hermetic mutation `tests/momentum/Analysis/test_ic_data_cache_hermetic.py`

- **SPEC ref**：§V V3b、Mutation protocol、§PROTO P2　|　**三態**：

| # | 狀態 | 預期 |
|---|------|------|
| **3.4.1** | redirect ON + sacrificial `tmp_path/work/data_cache` | repo digest 不變 |
| **3.4.2** | redirect OFF（或 DISABLE env）寫 sacrificial | `assert after != before`（**必紅若仍相等**） |
| **3.4.3** | restore ON | 新寫入不改 sacrificial digest |

- **驗證**：

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_data_cache_hermetic.py::test_mutation_redirect_disabled_caught -q -s
# 預期：1 passed；stdout 含 MUTATION_CANARY=1（或等價）
```

**Phase 3 Gate**：`bash scripts/run_ic_persist_hermetic.sh --set all` → exit 0 + 五個 digest=1

---

## Phase 4 — GEN manual helper

### Task 4.1 — `tests/fixtures/ic_persist_redirect_manual.py` + GEN-01..04

- **SPEC ref**：§GEN　|　**API**：`run_with_manual_redirect(root=None)` 使用同一 `RedirectPatchSet.activate()`；env 缺 `IC_PERSIST_REDIRECT_ROOT` → `sys.exit(2)`

| # | 檔案 | 變更 |
|---|------|------|
| **4.1.1** | `ic_persist_redirect_manual.py` | 新建 callable；finally own spy + deactivate |
| **4.1.2** | GEN-01..04 | 頂部 `from tests.fixtures.ic_persist_redirect_manual import run_with_manual_redirect`；`if __name__` 內呼叫 |

- **驗證（不跑 generator body 寫 repo）**：

```bash
venv/bin/python -c "from tests.fixtures.ic_persist_redirect_manual import run_with_manual_redirect; import inspect; assert callable(run_with_manual_redirect)"
rg -l "run_with_manual_redirect" tests/fixtures/gen_ic_run_selector_baseline.py tests/golden/ic_phase1_contract/freeze_baseline.py tests/golden/ic_phase1_1a_cut1/freeze_baseline.py tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py | wc -l
# 預期：4
```

---

## Final Acceptance（閉合條件 — 全部可執行 + exit 契約）

```bash
# 0) 派工前一次（實作開始前）
git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t2-pre-dirty.txt
# Composer 2026-07-11：pre-dirty 22 行；HEAD=241ab91030dcc0cc87876e517f98213130dd5f90

# 1) 主驗收 — 全 digest hermetic（禁裸跑子集當最終）
bash scripts/run_ic_persist_hermetic.sh --set all
rc=$?; echo $rc; exit $rc
# 預期：rc=0
# stdout 必含（順序不拘）：
#   DIGEST_DIFF_EMPTY[V1]=1
#   DIGEST_DIFF_EMPTY[V2]=1
#   DIGEST_DIFF_EMPTY[V5]=1
#   DIGEST_DIFF_EMPTY[V6]=1
#   DIGEST_DIFF_EMPTY[V7]=1
# V1 內層 pytest 摘要：9 passed, 1 skipped
# V7：collected=141；除 FF missing kline 外 0 skipped

# 2) Golden A/B/C + 雙 digest（V5 子集外殼仍須過）
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py -q -s
# 預期：passed；stdout 含 ab_hash=

# 3) Isolation subprocess + inventory（V4）
venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_persist_redirect_isolation.py \
  tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q -s
rc=$?; echo $rc; exit $rc
# 預期：≥4 passed, 0 failed；rc=0

# 4) Mutation canary（V3b）
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_data_cache_hermetic.py -q -s
rc=$?; echo $rc; exit $rc
# 預期：含 test_mutation_redirect_disabled_caught PASSED；rc=0

# 5) Unit completeness + to_thread（回歸）
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q
# 預期：0 failed（含 S1–S11、NEW-R4-4、mutation 正常分支）

# 6) 解耦 V8
grep -r "from api\." momentum/ | wc -l
# 預期：0

# 7) scope gate — post∖pre delta 對 whitelist（comm -13，兩邊 sort -u）
git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t2-post-dirty.txt
comm -13 /tmp/p2debt-t2-pre-dirty.txt /tmp/p2debt-t2-post-dirty.txt | sort -u > /tmp/p2debt-t2-delta-dirty.txt
# whitelist（§C 新建 + 修改檔；實作時以完工 tree 為準，至少含下列新建）：
cat > /tmp/p2debt-t2-whitelist.txt <<'EOF'
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
EOF
# 加上所有 Task 2.x/4.1 修改檔（REDIRECT+GEN）至 whitelist 後：
sort -u /tmp/p2debt-t2-whitelist.txt > /tmp/p2debt-t2-whitelist-sorted.txt
sort -u /tmp/p2debt-t2-delta-dirty.txt > /tmp/p2debt-t2-delta-dirty-sorted.txt
diff -u /tmp/p2debt-t2-whitelist-sorted.txt /tmp/p2debt-t2-delta-dirty-sorted.txt
rc=$?; echo $rc; exit $rc
# 壞基線（無實作）：delta 0 行或缺新建檔 → rc=1（誠實）
# 完工預期：delta 與完整 whitelist 精確相等 → rc=0；不得含 momentum/ api/ 生產碼

# 8) 輔助 V9（不替代 V3）
bash scripts/agent_preflight.sh && bash scripts/run_ic_persist_hermetic.sh --set all && bash scripts/agent_postflight.sh
rc=$?; echo $rc; exit $rc
# 預期：rc=0；postflight data_cache 快照不變
```

**禁止事項（驗收否決）**：裸跑 polluting pytest 無 digest wrapper；`comm -23`；相對 `production_prefix`；S11 漏 multi_tf；spy 永不記錄 violations；Run C 寫 repo；V7 非白名單 skip；xdist；改生產 persist 簽名。

**建議 commit 序列**：`feat: p2debt-t2 redirect patchset` → `feat: p2debt-t2 redirect wiring` → `test: p2debt-t2 hermetic harness` → `chore: p2debt-t2 gen manual redirect`

---

## 附錄 A — scope whitelist 修改檔（Task 2.x 必併入 §7 whitelist）

```text
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

（`tests/conftest.py` 僅當條件 scope 觸發。）

---

## 附錄 B — grok MINOR 吸收對照

| grok ID | 吸收位置 |
|---------|----------|
| NEW-R4-1 multi_tf | §0、Task 2.5、S11 追溯表、I3 |
| NEW-R4-2 spy hook | §0、Task 1.1.4、installer rewrite 點 |
| NEW-R4-3 absolute prefix | §0、Task 1.1.3 |
| NEW-R4-4 wrapper 文案 | §0、Task 1.3.2/1.3.3 |

---

SPEC=handoffs/P2DEBT-T2-SPEC-DRAFT-R4.md TODO=handoffs/P2DEBT-T2-TODO-DRAFT-R1.md FOCUS=legacy data_cache redirect process-global S1–S11 digest hermetic golden isolation mutation；用 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 獨立審查；Blocking 修補後才 Frozen。

R1-CLOSURE: 100% 追溯 89 列；grok NEW-R4-1..4 已吸收；scope gate comm -13；Final Acceptance 含 all+V4+V3b+unit；基線 receipt 已實跑 collect/原型
