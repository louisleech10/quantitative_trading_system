# P2 債票 2 — legacy 測試 data_cache 污染 → tmp redirect — SPEC 修訂 R3

> 來源：R2 `handoffs/P2DEBT-T2-SPEC-DRAFT-R2.md` + grok/codex R2 re-verify **雙 BLOCK** 閉合　|　日期：2026-07-11　|　起草：Composer　|　task-id：`p2debt-t2`  
> **R3 硬證據**：可執行 pytest 原型 `/tmp/p2debt-t2-proto/`（本輪實跑 7/7 passed）；§SEAM/fixture 設計**直接複製原型**，非紙面設計。

## 白話簡述（大任務 manifest）

**問題**：多支 pytest 與手動 generator 走真 IC / FF / ML 落盤鏈，覆寫 gitignored `data_cache/{features,reports,models}`。

**做法**：測試層 **session-safe redirect**（`tmp_path_factory` + `SessionRedirectPatcher`，**不用** function `monkeypatch` 掛 session/module polluter）+ function 級 per-test 激活/拆卸；`ProductionWriteSpy` 攔截 production prefix 寫入；**外層 shell harness** 跑 digest；golden **redirect ON/OFF** 雙向 oracle；generator 具名 consumer 讀 `IC_PERSIST_REDIRECT_ROOT`。

**不做**：不改生產 persist 簽名；不 root autouse；不把 polluter 改 skip；不跑污染 repo `data_cache/` 的 pytest body 當本輪驗收。

**雙家族閉合條款（STAMP 必驗）**：
1. §COVERAGE 與 16-caller `rg` 全集一致（含 `test_ic_run_selector` 分類）。
2. §SEAM 設計與 `/tmp/p2debt-t2-proto` 原型同構（FACT-RECEIPT 7/7）。
3. §V outer harness 為**可執行 shell 命令集**（非 importlib 假 harness）。
4. §G golden **ON+OFF 皆必跑且 passed**（禁 skip-as-green）。
5. §ISOLATION 證明 opt-in / non-opt-in 邊界（原型 test_non_opt_in 已證）。

---

## §RISK 風險分級

- **大小**：**大**
- **RISK-HIT: a,b**（同 R2）
- 票 5 交界：redirect 僅改磁碟根；§G ON/OFF normalized hash 須一致。

---

## §PROTO 可執行原型（FACT-RECEIPT — 本輪實跑）

### 原型目錄樹

```
/tmp/p2debt-t2-proto/
├── pyproject.toml
├── fakepkg/
│   ├── production.py      # data_cache_root() + analyze_and_persist
│   └── redirect.py        # SessionRedirectPatcher + spy + digest_tree
└── tests/
    ├── conftest.py        # redirect_root_session + ic_persist_redirect + session polluter
    ├── test_opt_in_session.py
    ├── test_opt_in_function.py
    ├── test_non_opt_in.py
    ├── test_hermetic_mutation.py
    ├── test_golden_ab.py
    └── test_generator_seam.py
```

### FACT-RECEIPT: 原型 pytest 全綠 VERIFY-EXEMPT:draft-superseded:p2debt-t2

```
命令: cd /tmp/p2debt-t2-proto && python3 -m pytest tests/ -v -s
結果: 7 passed in 0.09s
  test_generator_env_consumer PASSED
  test_golden_ab_redirect_on_off PASSED (stdout: ab_hash=45be569c8791f83c...)
  test_hermetic_digest_empty_diff PASSED (stdout: DIGEST_DIFF_EMPTY=1 before=0 after=0)
  test_mutation_redirect_disabled_caught PASSED (stdout: MUTATION_CANARY=1)
  test_non_opt_in_not_redirected PASSED
  test_function_polluter_writes_under_redirect PASSED
  test_session_polluter_writes_under_redirect PASSED
（Composer 2026-07-11）
```

### FACT-RECEIPT: 原型四項示範對照

| 要求 | 原型測試 | 證據 |
|------|----------|------|
| (a) opt-in 只寫 redirect root | `test_opt_in_session` / `test_opt_in_function` | `feature.is_relative_to(redirect_root)` |
| (b) spy 證明 production prefix 未碰 | 同上 | `spy.violations == []` |
| (c) 撤 redirect → canary 失敗 | `test_mutation_redirect_disabled_caught` | `after_mutation != before` → restore 後 `digest(prod)==before_restore` |
| (d) 同 session non-opt-in 不 redirect | `test_non_opt_in_not_redirected` | `get_active_redirect_root() is None`；路徑 `data_cache/features/...` |

### 原型核心機制（**實作須同構複製**）

**1. 雙層 redirect 生命週期（閉合 grok BLOCKING-5 / codex N1）**

| 元件 | Scope | 作法 |
|------|-------|------|
| `redirect_root_session` | session | `tmp_path_factory.mktemp("ic_redirect")` — **僅分配目錄，不激活** |
| `ic_persist_redirect` | function | `install_function_redirect(redirect_root_session, monkeypatch)` + **yield 後 `ctx.deactivate()`** |
| `ic_analysis_task_session` | session | `SessionRedirectPatcher.install()` → analyze → **`uninstall()` 於 finally**（setup 期短暫激活） |
| `ic_analysis_task_module` | module | 同 session 模式，scope=module + `redirect_root_module` |

**禁止**：session/module polluter fixture 參數注入 function-scoped `tmp_path` / `monkeypatch`（ScopeMismatch）。  
**禁止**：session polluter setup 前無 redirect（時序洞）。

**2. `SessionRedirectPatcher`（session/module 專用，手動 patch/restore）**

```python
class SessionRedirectPatcher:
    def install(self) -> RedirectContext: ...  # patch Path.write_bytes/mkdir + ctx.activate()
    def uninstall(self, ctx: RedirectContext) -> None: ...  # restore + ctx.deactivate()
```

**3. `data_cache_root()` 執行期解析（對應生產硬編碼替換）**

```python
def data_cache_root() -> Path:
    active = get_active_redirect_root()  # thread-local
    return active if active is not None else PRODUCTION_DATA_CACHE
```

Seam S1–S8 wrap 生產函式改讀 `redirect_root` 參數（由 `RedirectContext` 注入），**非**僅改 chdir。

**4. opt-in 接線（每 REDIRECT 檔頂部）**

```python
pytestmark = [pytest.mark.ic_persist_redirect, pytest.mark.usefixtures("ic_persist_redirect")]
```

- **Session polluter**（`ic_analysis_task` / `export_task` / `completed_ic_task`）：fixture 內 **`SessionRedirectPatcher` 於 setup 塊安裝**，不依賴 function `ic_persist_redirect` 參數（避免 ScopeMismatch）；下游測試靠 `pytestmark usefixtures("ic_persist_redirect")` 在每 test 重新激活 TLS。
- **禁止**根 `tests/conftest.py` autouse。

---

## §A 假設與已確認事實（R3 追加 receipt）

- **已確認**：16 caller 檔（含 `tests/api/test_ic_run_selector.py`）。 — FACT-RECEIPT: `rg -l '\.(analyze|start_analysis|refilter)\(' tests/ --glob '*.py' | sort | wc -l` → `16`（Composer 2026-07-11）
- **已確認**：API fixture scope — `ic_analysis_task`/`export_task` **session**；`completed_ic_task` **module**。 — FACT-RECEIPT: `rg -n '@pytest.fixture|scope=' tests/api/test_ic_analysis_api.py tests/api/test_export_api.py tests/api/test_ic_deep_analysis.py`（Composer 2026-07-11）
- **已確認**：V1 子集 collect **10**（含 perf skipif 1）。 — FACT-RECEIPT: `pytest …V1 nodeids… --collect-only -q` → `10 tests collected`（Composer 2026-07-11）
- **已確認**：ML 污染檔 **5** + FF e2e；完整 collect **141**。 — FACT-RECEIPT: `pytest tests/test_feature_factory_e2e.py tests/momentum/Analysis/test_lightgbm_analyzer.py tests/momentum/Analysis/test_lightgbm_edge_cases.py tests/momentum/Analysis/test_xgboost_protocol_methods.py tests/momentum/test_lightgbm_analyzer_phase3.py tests/momentum/test_xgboost_protocol_methods_phase3.py --collect-only -q` → `141 tests collected`（Composer 2026-07-11）
- **已確認**：`test_ic_run_selector.py` 用 **stub analyzer**，`start_analysis` 不觸真 persist。 — FACT-RECEIPT: `rg -n 'stub|create_ic_analyzer' tests/api/test_ic_run_selector.py` → L215–227 stub（Composer 2026-07-11）

---

## §COVERAGE — 全量表（R3 補 `test_ic_run_selector`）

圖例同 R2。新增 **G** 類：

| ID | 檔案 | 分類 | 說明 |
|----|------|------|------|
| RS-01 | `tests/api/test_ic_run_selector.py` | **GUARD** | stub `create_ic_analyzer`；`start_analysis` 不寫 `data_cache`；列 16-caller 全集但 **不掛 REDIRECT** |
| （其餘 IC/API/ML/FF/GEN/F） | | | **同 R2 §COVERAGE**；無 Phase-4 defer |

**16-caller 全集歸類**：

| 檔案 | 分類 |
|------|------|
| `tests/momentum/Analysis/test_ic_1a_cut1_{oos,golden,split}.py` | REDIRECT / STUB（split flag_toggles） |
| `tests/momentum/test_ic_{e2e,feature_filter}.py` | REDIRECT |
| `tests/api/test_ic_{analysis_api,export_api,deep_analysis}.py` | REDIRECT |
| `tests/api/test_ic_run_selector.py` | GUARD |
| `tests/momentum/test_ic_filter_orchestrator.py` | GUARD |
| `tests/momentum/test_ic_1eb_b{2,4}_*.py` | GUARD |
| `tests/momentum/Analysis/test_long_short_analyzer.py` | N/A |
| `tests/phase25/test_long_short_analyzer.py` | N/A |
| `tests/phase26/test_deep_analysis_integration.py` | N/A |
| `tests/fixtures/gen_ic_run_selector_baseline.py` | MANUAL |
| `tests/golden/ic_phase1*/freeze_baseline*.py` | MANUAL |

---

## §SEAM 可執行 redirect 設計（複製自 `/tmp/p2debt-t2-proto`）

### 共用模組 `tests/fixtures/ic_persist_redirect.py`

**直接對照原型 `fakepkg/redirect.py` + `fakepkg/production.py`**：

```python
PRODUCTION_DATA_CACHE = Path("data_cache")

@dataclass
class RedirectContext:
    redirect_root: Path
    spy: ProductionWriteSpy
    scope: str
    def activate(self) -> None: ...
    def deactivate(self) -> None: ...

class SessionRedirectPatcher: ...  # 同原型 L68–112

def install_function_redirect(redirect_root: Path, monkeypatch: pytest.MonkeyPatch, *, ...) -> RedirectContext: ...

def digest_data_cache(root: Path = PRODUCTION_DATA_CACHE) -> dict[str, str]:
    """同原型 digest_tree；掃 features/ reports/ models/"""
```

### 具名 patch 點（同 R2 S1–S11；R3 釘死作法）

| Seam | Target | 作法（禁「wrap 或 monkeypatch 二選一」） |
|------|--------|----------------------------------------|
| S1–S3,S7 | `_resolve_filtered_path` ×3 | `wrap(orig, redirect_root: Path)` 回傳 `{redirect_root}/features/...` |
| S2 | `_persist_outputs` | `wrap`：改 `output_dir` 字面量 → `{redirect_root}/reports` |
| S4–S6 | materialize / meta / transforms | `wrap`：改 cache/output dir |
| S8 | `export_filtered_csv` | `wrap`：`output_dir = redirect_root / "reports"` |
| S9 | `test_export_api.py` L125–137 | **測試側** `filtered_path = redirect_root / "features" / ...` |
| S10 | ML `save_model` | `wrap` `_validate_model_path` + 路徑前綴替換至 `{redirect_root}/models` |
| S11 | FF `FeatureStorage` | `factory._storage = FeatureStorage(redirect_root / "features")` |

每 wrap **必須**簽名含 `redirect_root: Path`（injectable）。

### Plugin `tests/fixtures/ic_persist_redirect_plugin.py`（單一定義處）

```python
@pytest.fixture(scope="session")
def redirect_root_session(tmp_path_factory: pytest.TempPathFactory) -> Path: ...

@pytest.fixture(scope="module")
def redirect_root_module(tmp_path_factory: pytest.TempPathFactory) -> Path: ...

@pytest.fixture
def ic_persist_redirect(redirect_root_session, monkeypatch) -> Iterator[RedirectContext]:
    ctx = install_function_redirect(redirect_root_session, monkeypatch, ...)
    yield ctx
    ctx.deactivate()  # 原型證明：缺此會污染 non-opt-in（FACT-RECEIPT 首輪 2 failed → 修復後 7 passed）
```

### conftest 掛載（plugin 單源；subtree re-export）

| 檔案 | 動作 |
|------|------|
| **新建** `tests/momentum/conftest.py` | `pytest_plugins = ["tests.fixtures.ic_persist_redirect_plugin"]` |
| `tests/momentum/Analysis/conftest.py` | re-export `ic_persist_redirect`, `redirect_root_session` |
| `tests/api/conftest.py` | 同上 |
| `tests/conftest.py`（根） | **僅** FF e2e 所需：re-export（`test_feature_factory_e2e.py` 在根） |

### Session/module polluter 接線範式（**取代 R2 錯誤「顯式參數 ic_persist_redirect」**）

```python
# tests/api/test_ic_analysis_api.py
pytestmark = [pytest.mark.ic_persist_redirect, pytest.mark.usefixtures("ic_persist_redirect")]

@pytest.fixture(scope="session")
def ic_analysis_task(redirect_root_session: Path) -> str:
    patcher = SessionRedirectPatcher(redirect_root_session, PRODUCTION_DATA_CACHE)
    ctx = patcher.install()
    try:
        # POST /api/v1/ic/analyze — 同現有邏輯
        ...
        return task_id
    finally:
        patcher.uninstall(ctx)
```

`export_task`（session）、`completed_ic_task`（module + `redirect_root_module`）**同構**。

---

## §G Golden / redirect ON-OFF oracle（閉合 codex B4）

**新建 `tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py`**

| Run | redirect | 預期 |
|-----|----------|------|
| A | ON `tmp_a` | `normalize(get_result())` → `hash_a` |
| B | ON `tmp_b` | `hash_b == hash_a` |
| C | **OFF**（無 patch；**必跑，非 optional**） | `hash_off == hash_a`（僅 path 替換，in-memory 語意同） |

- `normalize(result: dict) -> str`：**具體定義** — `json.dumps({k: result[k] for k in sorted(result) if k not in EXEMPT}, sort_keys=True, default=str)`；`EXEMPT = {"filtered_features_path", "report_paths", "artifact_mtime"}`（僅磁碟路徑欄位）。
- **禁 skip**：baseline 缺失 → `pytest.fail()`，非 `skip`。
- stdout：`print(f"ab_hash={hash_a}")`；驗收命令 **須 `-s`**。

---

## §ISOLATION（閉合 codex B5）

**新建** `tests/momentum/Analysis/test_ic_persist_redirect_isolation.py` + **`test_ic_persist_redirect_inventory.py`**（已加入 §C allowed-new-files）

| Case | 作法 | 預期 |
|------|------|------|
| I1 | subprocess 跑 3 固定 **non-opt-in** nodeid（governance canary） | `get_redirect_install_count()==0` |
| I2 | parametrize S1–S11 最小觸發 | 寫入僅在 `redirect_root`；`spy.violations==[]` |
| I3 | inventory：`rg` §COVERAGE REDIRECT 表 vs `ic_persist_redirect` marker | 缺掛 → FAIL |

---

## §GEN Generator seams + named consumer（閉合 codex N2）

**新建 `tests/fixtures/ic_persist_redirect_manual.py`**（callable，非 pytest fixture）：

```python
def run_with_manual_redirect(redirect_root: Path | None = None) -> None:
    root = redirect_root or Path(os.environ["IC_PERSIST_REDIRECT_ROOT"])
    patcher = SessionRedirectPatcher(root, PRODUCTION_DATA_CACHE)
    ...
```

| GEN ID | 腳本 | Consumer |
|--------|------|----------|
| GEN-01 | `tests/fixtures/gen_ic_run_selector_baseline.py` | 頂部 `from tests.fixtures.ic_persist_redirect_manual import run_with_manual_redirect` |
| GEN-02 | `tests/golden/ic_phase1_contract/freeze_baseline.py` | 同上 |
| GEN-03 | `tests/golden/ic_phase1_1a_cut1/freeze_baseline.py` | 同上 |
| GEN-04 | `tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py` | 同上 |

腳本若無 `IC_PERSIST_REDIRECT_ROOT` → `sys.exit(2)`（非 0）。

---

## §V 驗證策略（閉合 codex B3 / grok B-3/B-4）

### Digest oracle（唯一主證明）

同 R2 `digest_data_cache()`；禁 path+size / postflight 主證明。

### 外層 harness — **可執行 shell 命令集**（禁 importlib 內跑 pytest）

**新建 `scripts/run_ic_persist_hermetic.sh`**：

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
PRE="$(venv/bin/python -c 'from tests.fixtures.ic_persist_redirect import digest_data_cache; import json; print(json.dumps(digest_data_cache()))')"
venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_fallback_insufficient_data_marks_applied_false \
  tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_applied_true_when_sufficient \
  tests/momentum/test_ic_e2e.py \
  tests/momentum/test_ic_feature_filter.py::test_analyze_applies_feature_filter_metadata_and_summary_limit \
  -q --tb=no
POST="$(venv/bin/python -c 'from tests.fixtures.ic_persist_redirect import digest_data_cache; import json; print(json.dumps(digest_data_cache()))')"
if [[ "$PRE" != "$POST" ]]; then echo "DIGEST_DIFF_EMPTY=0"; exit 1; fi
echo "DIGEST_DIFF_EMPTY=1"
```

| 步驟 | Exit contract |
|------|---------------|
| harness 成功 | exit **0** + stdout 含 `DIGEST_DIFF_EMPTY=1` |
| digest 不一致 | exit **1** + `DIGEST_DIFF_EMPTY=0` |
| 內層 pytest 失敗 | exit **非 0**（`set -e`） |

### Mutation（`test_ic_data_cache_hermetic.py::test_mutation_redirect_disabled_caught`）

同原型三態：
1. redirect ON → `digest(fake_prod)` 不變
2. redirect OFF → `digest(fake_prod)` **必變**（`assert after != before`）
3. redirect 恢復 → 新寫入不改 `fake_prod`（`digest(prod)==before_restore`）

- `fake_prod` = `tmp_path/work/data_cache`（測試內 chdir，**不寫真 repo data_cache**）
- 預設 CI 必跑；exit **`1 passed`**

### 驗收集（R3 修訂 exit contracts）

| # | 命令 | 通過條件 |
|---|------|----------|
| V1 | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_fallback_insufficient_data_marks_applied_false tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_applied_true_when_sufficient tests/momentum/test_ic_e2e.py tests/momentum/test_ic_feature_filter.py::test_analyze_applies_feature_filter_metadata_and_summary_limit tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q` | **`9 passed, 1 skipped, 0 failed`**；skipped **僅** `test_performance_800_features` |
| V2 | `venv/bin/python -m pytest tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis tests/api/test_ic_analysis_service.py::test_resolve_run_path_contains_config_hash -q` | `2 passed, 0 skipped, 0 failed` |
| V3 | `bash scripts/run_ic_persist_hermetic.sh` | exit 0 + `DIGEST_DIFF_EMPTY=1` |
| V3b | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_data_cache_hermetic.py::test_mutation_redirect_disabled_caught -q` | **`1 passed`** |
| V4 | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_isolation.py -q` | `≥3 passed` |
| V5 | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q -s` | AB **`1 passed`** + golden **`2 passed`**；stdout 含 `ab_hash=`；**不含** `skipped` |
| V6 | `venv/bin/python -m pytest tests/api/test_ic_analysis_api.py tests/api/test_export_api.py tests/api/test_ic_deep_analysis.py -q` | `≥30 passed, 0 failed` |
| V7 | 見下 **ML 完整清單** | `passed == collected - data_missing_skips`；**0 failed** |
| V8 | `grep -r "from api\." momentum/` | 0 |
| V9（輔助） | `bash scripts/agent_preflight.sh …` + V3 + postflight | 不替代 V3 |

### V7 — ML+FF 完整驗收清單（閉合 codex B1/N3 + grok NEW-2）

```bash
venv/bin/python -m pytest \
  tests/test_feature_factory_e2e.py \
  tests/momentum/Analysis/test_lightgbm_analyzer.py \
  tests/momentum/Analysis/test_lightgbm_edge_cases.py \
  tests/momentum/Analysis/test_xgboost_protocol_methods.py \
  tests/momentum/test_lightgbm_analyzer_phase3.py \
  tests/momentum/test_xgboost_protocol_methods_phase3.py \
  -q
```

- collect 預期：**141**（2026-07-11 collect-only receipt）
- 允許 skip：僅 `_require_data` / 無 kline（須逐檔註明）

---

## §C 約束（R3 修訂 allowed-new-files）

- **新建**：`tests/fixtures/ic_persist_redirect.py`、`ic_persist_redirect_plugin.py`、`ic_persist_redirect_manual.py`
- **新建**：`tests/momentum/conftest.py`
- **新建**：`scripts/run_ic_persist_hermetic.sh`
- **新建測試**：`test_ic_persist_redirect_unit.py`、`test_ic_data_cache_hermetic.py`、`test_ic_persist_redirect_isolation.py`、**`test_ic_persist_redirect_inventory.py`**、`test_ic_persist_redirect_golden_ab.py`
- 其餘同 R2

---

## §P Phase（同 R2 結構；實作順序不變）

Phase 1 → redirect 工具（**先 port 原型通過的單元測試**）  
Phase 2 → §COVERAGE REDIRECT 全掛  
Phase 3 → hermetic + mutation + isolation + golden AB  
Phase 4 → GEN-* 接 `ic_persist_redirect_manual`

---

## R3-CLOSURE: finding → 閉合位置

| Finding ID | 來源 | R2 狀態 | R3 閉合 |
|------------|------|---------|---------|
| **grok BLOCKING-5** | session/module + function redirect ScopeMismatch | STILL-OPEN | §SEAM `SessionRedirectPatcher` + `redirect_root_session` + polluter setup 內 install/uninstall；**禁止** function `ic_persist_redirect` 參數注入 session fixture；§PROTO 7/7 |
| **grok BLOCKING-1..4** | API 漏表 / seams / digest / mutation | CLOSED | R3 保留 + §V shell harness 強化 |
| **grok NEW-1** | V1 exit 矛盾 | OPEN | V1 → **`9 passed, 1 skipped, 0 failed`** 精確契約 |
| **grok NEW-2** | V7 漏 ML | OPEN | V7 完整 6 檔命令 + collect 141 |
| **grok NEW-3** | cosmetic | OPEN | 維持；非阻擋 |
| **codex B1** | 全集 / run_selector / ML 漏 | STILL-OPEN | §COVERAGE RS-01 + 16-caller 表；V7 六檔 |
| **codex B2** | fixture 不可執行 | STILL-OPEN | §SEAM = §PROTO 同構；plugin 單源；S8 釘死 wrap |
| **codex B3** | outer harness 假殼 | STILL-OPEN | `scripts/run_ic_persist_hermetic.sh` 可執行 + exit 契約 |
| **codex B4** | golden 非 on/off | STILL-OPEN | §G Run A/B/C；C=OFF **必跑**；`-s` + `ab_hash=` |
| **codex B5** | I1–I3 不可執行 | STILL-OPEN | I1 subprocess；I3 inventory 入 allowed-new-files |
| **codex B6** | RISK | CLOSED | 同 R2 |
| **codex M1** | V1/V5 矛盾 + capture | STILL-OPEN | V1 精確 skipped；V5 **`-s`**；V3 shell stdout |
| **codex N1** | session lifecycle | STILL-OPEN | §PROTO 雙層 TLS activate/deactivate |
| **codex N2** | generator 無 consumer | STILL-OPEN | §GEN `ic_persist_redirect_manual.py` + 四腳本 import |
| **codex N3** | ML 驗收漏 | STILL-OPEN | V7 六檔清單 |

---

ASSUMPTIONS_VERIFIED: 原型 7/7 passed；16-caller 含 run_selector；API session/module scopes；V1 collect=10；ML+FF collect=141；run_selector stub 不 persist  
TESTS_RUN: `/tmp/p2debt-t2-proto` `python3 -m pytest tests/ -v -s` → 7 passed；repo `rg`/`pytest --collect-only` 如上；**0** polluting repo pytest body  
FAILURES_SEEN: 原型首輪 2 failed（redirect TLS 泄漏、mutation restore 斷言）→ `ctx.deactivate()` + `before_restore` 修復 → 7 passed  
SCOPE_CHANGES: none（僅 `handoffs/P2DEBT-T2-SPEC-DRAFT-R3.md`）  
NUMERIC_OR_SCHEMA_IMPACT: none  

**產出檔**：`handoffs/P2DEBT-T2-SPEC-DRAFT-R3.md`

STATUS: DONE
