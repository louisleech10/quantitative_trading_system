# P2 債票 2 — legacy 測試 `data_cache` 污染 → tmp redirect — SPEC 修訂 R4

> 基稿：`handoffs/P2DEBT-T2-SPEC-DRAFT-R3.md`  
> 輸入：`handoffs/P2DEBT-T2-SPEC-REVERIFY-R3-codex.md`、`handoffs/P2DEBT-T2-SPEC-REVERIFY-R3-grok.md`  
> 日期：2026-07-11｜task-id：`p2debt-t2`｜斷路器接手：Codex  
> R4 原型：`/tmp/p2debt-t2-proto`，本輪新增 `asyncio.to_thread` polluter；正常 8/8 passed，撤 redirect canary exit 1。

## 白話簡述（大任務 manifest）

**問題**：多支 pytest 與手動 generator 走真 IC / FF / ML 落盤鏈，會覆寫 gitignored 的 `data_cache/{features,reports,models}`。R3 用 thread-local active root；真 API 透過 `asyncio.to_thread` 執行時，worker thread 看不到該 root，redirect 失效。

**R4 做法**：使用**行程全域 patch set + 每測試 opt-in active gate**。patch wrapper 對整個 Python process 可見，因此 `asyncio.to_thread` worker 也會走 redirect；只有 function/session/module fixture 明確 activate 時才改寫路徑，inactive 時原樣呼叫。active state 由 `RLock` 保護，nested activation fail-closed。此選擇依賴本票驗收 pytest **序列執行**；同一 process 不允許兩個 redirect root 同時 active。pytest-xdist 的 worker 是不同 process，不共享 gate，但本票命令不使用 xdist。

**完整性**：S1–S11 是單一 declarative manifest。activate 前先解析全部 target/subtarget，再驗 `resolved_ids == REQUIRED_SEAM_IDS`；任一 import、attribute、installer 或 probe 缺失時，**零部分安裝、拒絕 activate**。

**不做**：不改生產 persist 公開簽名；不 root autouse；不把 polluter 改 skip；不弱化 NaN/inf/float16 gate；不改輸出 schema/數值/檔案大小；不執行任何會寫 repo `data_cache` 的驗收 body。

**R4 必驗**：

1. process-global gate 跨 `asyncio.to_thread` 生效。
2. mutation 拔 redirect 後 canary 必紅。
3. 同 session non-opt-in test 不受影響。
4. S1–S11 任一 target import/installer 缺失，patcher activation 必紅且不得留下部分 patch。
5. Golden A/B/C 全跑；Run C OFF 只可寫 `tmp_path/work/data_cache`。
6. V1、V2、V5、V6、V7 各自有 repo `data_cache` 前後 SHA-256 digest receipt。

---

## §RISK 風險分級

- **大小**：大。
- **RISK-HIT: a,b**：資料品質與跨 IC/API/FF/ML/generator 共用路徑。
- 票 5 交界：redirect 僅改磁碟 root；Golden normalized hash 必須 ON/OFF 一致。
- 最壞失敗：gate 未跨 thread 或漏一 seam，測試覆寫 repo cache。對策是 process-global visibility、manifest fail-closed、production-prefix spy、分組 digest 四層防線。

---

## §PROTO R4 可執行原型與 FACT-RECEIPTs

### 原型變更

`/tmp/p2debt-t2-proto/fakepkg/redirect.py`：TLS 改為 process-global `_active_redirect_root` + `RLock`；nested activation 拒絕；deactivate 驗 ownership。  
`/tmp/p2debt-t2-proto/tests/test_opt_in_to_thread.py`：新增 `asyncio.to_thread(analyze_and_persist, ...)` polluter。  
`/tmp/p2debt-t2-proto/tests/conftest.py`：session polluter teardown 前斷言**自己的** spy 無 violations，不再用另一個 function fixture spy 代驗。

### FACT-RECEIPT P1 — opt-in 跨 `to_thread` + non-opt-in unaffected

```text
命令: cd /tmp/p2debt-t2-proto && python3 -m pytest tests/test_opt_in_to_thread.py tests/test_non_opt_in.py -v -s

============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Library/Developer/CommandLineTools/usr/bin/python3
cachedir: .pytest_cache
rootdir: /private/tmp/p2debt-t2-proto
configfile: pyproject.toml
plugins: anyio-4.11.0
collecting ... collected 2 items

tests/test_opt_in_to_thread.py::test_to_thread_polluter_writes_under_redirect PASSED
tests/test_non_opt_in.py::test_non_opt_in_not_redirected PASSED

============================== 2 passed in 0.03s ===============================
EXIT=0
```

### FACT-RECEIPT P2 — mutation 拔 redirect，跨 thread canary 必紅

原型的 `P2DEBT_PROTO_DISABLE_REDIRECT=1` 是只供 `/tmp` mutation 的開關；它令 getter 回傳 inactive，等價於拔除 redirect path decision。

```text
命令: cd /tmp/p2debt-t2-proto && P2DEBT_PROTO_DISABLE_REDIRECT=1 python3 -m pytest tests/test_opt_in_to_thread.py::test_to_thread_polluter_writes_under_redirect -v -s

============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Library/Developer/CommandLineTools/usr/bin/python3
cachedir: .pytest_cache
rootdir: /private/tmp/p2debt-t2-proto
configfile: pyproject.toml
plugins: anyio-4.11.0
collecting ... collected 1 item

tests/test_opt_in_to_thread.py::test_to_thread_polluter_writes_under_redirect FAILED

=================================== FAILURES ===================================
________________ test_to_thread_polluter_writes_under_redirect _________________

    paths = asyncio.run(
        asyncio.to_thread(analyze_and_persist, "THREAD", "1h", "to_thread")
    )
>   assert paths["feature"].is_relative_to(ic_persist_redirect.redirect_root)
E   AssertionError: assert False
E    +  where False = PosixPath('data_cache/features/THREAD_1h_filtered.h5').is_relative_to(.../ic_redirect0)

tests/test_opt_in_to_thread.py:18: AssertionError
=========================== short test summary info ============================
FAILED tests/test_opt_in_to_thread.py::test_to_thread_polluter_writes_under_redirect
============================== 1 failed in 0.04s ===============================
EXIT=1
```

### FACT-RECEIPT P3 — restore 後全原型

```text
命令: cd /tmp/p2debt-t2-proto && python3 -m pytest tests/ -v -s

collecting ... collected 8 items
tests/test_generator_seam.py::test_generator_env_consumer PASSED
tests/test_golden_ab.py::test_golden_ab_redirect_on_off ab_hash=45be569c8791f83cc63fbe45f43e1032f5e6d07f6a98808e2a4cc725de9ccf58 PASSED
tests/test_hermetic_mutation.py::test_hermetic_digest_empty_diff DIGEST_DIFF_EMPTY=1 before=0 after=0 PASSED
tests/test_hermetic_mutation.py::test_mutation_redirect_disabled_caught MUTATION_CANARY=1 PASSED
tests/test_non_opt_in.py::test_non_opt_in_not_redirected PASSED
tests/test_opt_in_function.py::test_function_polluter_writes_under_redirect PASSED
tests/test_opt_in_session.py::test_session_polluter_writes_under_redirect PASSED
tests/test_opt_in_to_thread.py::test_to_thread_polluter_writes_under_redirect PASSED
============================== 8 passed in 0.06s ===============================
EXIT=0
```

---

## §A 假設與已確認事實

- 16-caller `rg` 集合為 16 個檔；API 三個 HTTP polluter fixture 不在該 regex 集合，兩者分開計數，禁止再稱 19 項表為「16-caller exact enumeration」。
- `ic_analysis_task` / `export_task` 為 session scope；`completed_ic_task` 為 module scope。
- V1 collect 10，預設唯一 skip 是 `test_performance_800_features`。
- V7 六檔 collect 141；檔案清單見 §V。
- `test_ic_run_selector.py` 使用 stub analyzer，不觸真 persist。
- API analyze 使用 `asyncio.to_thread`；TLS 不跨 worker，process-global gate 實跑通過。
- pytest 本票命令序列執行且不使用 xdist；active gate nested activation 明確拒絕。

---

## §COVERAGE — 全量寫入路徑表（保留 R3/R2 有效內容）

圖例：`REDIRECT`＝必掛 opt-in；`GUARD`＝既有 no-op/patch；`STUB`＝stage7 前終止或 stub；`ISOLATED`＝已有 tmp/config 隔離；`MANUAL`＝手動腳本；`READ/N/A`＝不走本票 persist。

### A. IC 真 persist（REDIRECT）

| ID | 測試 / 觸發點 | 生產落盤 |
|---|---|---|
| IC-01 | `test_ic_1a_cut1_oos.py::test_fallback_insufficient_data_marks_applied_false` | `features/BTCUSDT_1h_filtered.h5` + gatekeeper reports |
| IC-02 | `test_ic_1a_cut1_oos.py::test_oos_applied_true_when_sufficient` | 同上 |
| IC-03..07 | `tests/momentum/test_ic_e2e.py` 五個 analyze/refilter tests；perf 由 env 控制 | `features/BTCUSDT_12h_filtered.h5` + `reports/ic_report_ic_e2e_test.*` |
| IC-08 | `test_ic_feature_filter.py::test_analyze_applies_feature_filter_metadata_and_summary_limit` | filtered H5 + gatekeeper reports |
| IC-09..10 | `test_ic_1a_cut1_golden.py` OFF/ON golden | BTCUSDT/1h + gatekeeper reports |
| IC-11..12 | `test_ic_analysis_service.py` 兩個 real/materialize tests | `reports/ic_ingest_cache/*.{h5,json}` |

### B. API HTTP fixture polluters（REDIRECT；不屬於 16-caller regex）

| ID | 測試 / fixture | 寫入 |
|---|---|---|
| API-01..03 | `test_ic_analysis_api.py` session `ic_analysis_task`、下游/refilter/export CSV | filtered H5、IC reports、`ic_filtered_{task_id}.csv` |
| API-04..05 | `test_ic_deep_analysis.py` module `completed_ic_task` + 下游 | filtered H5 + deep reports |
| API-06..07 | `test_export_api.py` session `export_task` + 下游 | analyze persist + fixture 直接 `h5py.File(...,"w")` |

### C. ML models（REDIRECT）

| ID | 檔 / 分支 | 寫入 |
|---|---|---|
| ML-01..02 | `Analysis/test_lightgbm_analyzer.py` roundtrip/bad payload | `models/*.pkl` |
| ML-03 | `Analysis/test_lightgbm_edge_cases.py` lgb/xgb/retrain | `models/type_mismatch_*.pkl`, `retrain_*.pkl` |
| ML-04 | `Analysis/test_xgboost_protocol_methods.py` | `models/xgb_roundtrip_protocol.pkl` |
| ML-05 | `momentum/test_lightgbm_analyzer_phase3.py` | `models/*.pkl` |
| ML-06 | `momentum/test_xgboost_protocol_methods_phase3.py` | `models/*.pkl` |

### D. Feature Factory

| ID | 檔 | 分類 / 路徑 |
|---|---|---|
| FF-01 | `tests/test_feature_factory_e2e.py` 六個 `generate_features()` | REDIRECT；預設 persist 到 `features/{symbol}/{config_hash}/…` |
| FF-02 | `tests/feature_engineering/**` | ISOLATED；既有 FFACT/tmp 防護，留 regression canary |

### E. 手動 generator

| ID | 腳本 | 分類 |
|---|---|---|
| GEN-01 | `tests/fixtures/gen_ic_run_selector_baseline.py` | MANUAL；具名 env consumer |
| GEN-02 | `tests/golden/ic_phase1_contract/freeze_baseline.py` | MANUAL；同上 |
| GEN-03 | `tests/golden/ic_phase1_1a_cut1/freeze_baseline.py` | MANUAL；同上 |
| GEN-04 | `tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py` | MANUAL；同上 |

### F. 已防護 / 不寫

| 分類 | 代表 | 理由 |
|---|---|---|
| GUARD | `test_ic_filter_orchestrator.py`、`test_ic_1eb_b{2,4,5}_*.py` | `_persist_outputs` no-op / patch |
| GUARD | `tests/api/test_ic_run_selector.py` | stub analyzer |
| STUB | cut1 oos flag toggle、cut1 split pipeline-order | stub `_stage7_report` |
| ISOLATED | API batch/bulk delete、`tests/feature_engineering/**` | settings/tmp/FFACT |
| READ | kline cache readers | 無寫入 |
| N/A | long-short / phase25 / phase26 `analyze()` | 非 IC persist 鏈 |

### 16-caller exact enumeration（`rg -l '\.(analyze|start_analysis|refilter)\(' tests/ --glob '*.py' | sort`）

| # | 檔案 | 分類 |
|---:|---|---|
| 1 | `tests/api/test_ic_run_selector.py` | GUARD |
| 2 | `tests/fixtures/gen_ic_run_selector_baseline.py` | MANUAL |
| 3 | `tests/golden/ic_phase1_1a_cut1/freeze_baseline.py` | MANUAL |
| 4 | `tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py` | MANUAL |
| 5 | `tests/golden/ic_phase1_contract/freeze_baseline.py` | MANUAL |
| 6 | `tests/momentum/Analysis/test_ic_1a_cut1_golden.py` | REDIRECT |
| 7 | `tests/momentum/Analysis/test_ic_1a_cut1_oos.py` | REDIRECT/STUB |
| 8 | `tests/momentum/Analysis/test_ic_1a_cut1_split.py` | STUB |
| 9 | `tests/momentum/Analysis/test_long_short_analyzer.py` | N/A |
| 10 | `tests/momentum/test_ic_1eb_b2_wiring.py` | GUARD |
| 11 | `tests/momentum/test_ic_1eb_b4_fullstack.py` | GUARD |
| 12 | `tests/momentum/test_ic_e2e.py` | REDIRECT |
| 13 | `tests/momentum/test_ic_feature_filter.py` | REDIRECT |
| 14 | `tests/momentum/test_ic_filter_orchestrator.py` | GUARD |
| 15 | `tests/phase25/test_long_short_analyzer.py` | N/A |
| 16 | `tests/phase26/test_deep_analysis_integration.py` | N/A |

閉合宣稱只限上表列出的 polluter；不得泛稱整個 `tests/` 永遠零 `data_cache` 寫入。

---

## §SEAM R4 redirect architecture

### 狀態機與 thread boundary

```text
pytest process (serial)
  bootstrap: resolve S1..S11 ──missing──> REFUSE (no patch installed)
              │ all resolved
              v
        install pass-through wrappers once (process-global)
              │
non-opt-in ───┼── gate INACTIVE ──> original path unchanged
              │
opt-in fixture activate(root, spy)
              v
        gate ACTIVE under RLock
              ├── main thread call ─────> wrapper -> tmp root
              └── asyncio.to_thread ────> same process gate -> tmp root
              v
        fixture teardown: assert owning spy, clear gate in finally
```

### 核心 API（`tests/fixtures/ic_persist_redirect.py`）

```python
REQUIRED_SEAM_IDS = frozenset({f"S{i}" for i in range(1, 12)})

@dataclass(frozen=True)
class ActiveRedirect:
    root: Path
    production_prefix: Path
    spy: ProductionWriteSpy
    owner: str

class RedirectPatchSet:
    def resolve_all(self) -> dict[str, ResolvedSeam]: ...
    def install_once(self) -> None: ...
    def activate(self, root: Path, *, owner: str) -> RedirectContext: ...
    def deactivate(self, ctx: RedirectContext) -> None: ...
```

強制契約：

- `resolve_all()` 先 import/resolve **全部** target 與 subtarget，不得邊 resolve 邊 patch。
- `set(resolved) == REQUIRED_SEAM_IDS`，且每個 `ResolvedSeam.installers` 非空、`probe` 可呼叫；否則 raise `RedirectCompletenessError`。
- `install_once()` 原子化：全部 resolve 成功後才 patch；installer 中途失敗要 reverse rollback 已裝項並驗 gate inactive。
- wrapper 永久留在該 pytest process；inactive 時呼叫 original 且不得建立 redirect root。
- `activate()` 再次核對 installed IDs；任一 seam 缺失拒絕 activation。已 active 時拒絕 nested/overlap。
- `deactivate()` 只接受同一 context ownership；`finally` 清 active state。session/module polluter teardown 在清除前斷言**自己 context 的 spy**。
- active root 是 process-global，不用 TLS/`ContextVar`；所有讀寫在 `RLock` 下。gate lookup 短且不做 I/O。
- pytest 本票禁止同 process 平行 test execution；驗收命令不得加 thread-parallel plugin/參數。

### S1–S11 declarative manifest（全部 mandatory）

| ID | 必須 resolve 的 target/subtarget | active 時 installer 行為 | probe |
|---|---|---|---|
| S1 | `ICFilterOrchestrator._resolve_filtered_path` | rewrite 回傳 `root/features/...` | symbol/timeframe path 位於 root |
| S2 | `ICReporter.save_report`、`save_filter_log`、`save_filtered_features` | rewrite production `output_dir/path` 到 `root/{reports,features}` | report/filter/H5 三輸出都在 root |
| S3 | `ICAnalysisService._resolve_filtered_path` | rewrite 回傳到 `root/features` | service resolver path |
| S4 | `ICAnalysisService._materialize_features_for_ic` | process-global module path adapter 只改 `data_cache/reports/ic_ingest_cache` | H5 + meta 都在 root |
| S5 | `ICAnalysisService._write_ic_meta_json` | 同 adapter；保留 payload/schema | meta JSON 在 root |
| S6 | `ICAnalysisService._apply_transforms_sync` | 同 adapter；只改 `data_cache/reports` | transformed H5 在 root |
| S7 | `api.routes.ic_analysis._resolve_filtered_path` | rewrite 回傳到 `root/features` | route resolver path |
| S8 | `api.routes.ic_analysis.export_filtered_csv` | route module path adapter 改 `data_cache/reports` | CSV / `FileResponse.path` 在 root |
| S9 | 新增測試 helper `tests.api.test_export_api._export_fixture_filtered_path`，`export_task` 必經此 helper | helper inactive 回 production；active 回 `root/features` | 直接 `h5py.File("w")` 路徑在 root |
| S10 | `LightGBMAnalyzer._resolve_model_path`、`XGBoostAnalyzer._resolve_model_path` | production-relative model path 映到 `root/models`；非法 path 仍 fail | lgb/xgb roundtrip + mismatch |
| S11 | 新增測試 helper `tests.test_feature_factory_e2e._create_e2e_factory`，六個 generate tests 必經此 helper | active 時 `factory._storage = FeatureStorage(root/features)` | persisted FF tree 在 root |

S4–S6/S8 的 module path adapter 不是全域替換 `pathlib.Path`；只 patch 各 target module 的 `Path` binding，且只重寫 resolve 後位於 production prefix 的 path。其他 path 完整 pass-through。S9/S11 改成具名 helper 是為了讓 manifest 有可 import、可 probe、可 mutation 的實際接點，禁止再用散落的 test-local literal/instance assignment。

### Completeness assertion 與 mutation

`test_ic_persist_redirect_unit.py` 必須 parameterize `S1` 到 `S11`：

1. 正向：每個 target/subtarget 可 resolve，probe 觸發後只寫 redirect root，owning spy 無 violations。
2. 缺 target：逐 ID monkeypatch importer/attribute 為 missing，`activate()` raise；active count 仍 0；無任何 wrapper 殘留。
3. installer 中途失敗：模擬第 N 項 raise，驗 reverse rollback；non-opt-in probe 行為等同原始。
4. manifest 少/多 ID、空 installer、空 probe 都拒絕 activate。
5. S9/S11 helper mutation 不經 helper時，相應 probe 必紅。

### Plugin / fixture lifecycle

| 元件 | scope | 行為 |
|---|---|---|
| `redirect_patch_set` | session | resolve S1–S11 + install pass-through wrappers；不 activate |
| `redirect_root_session` | session | `tmp_path_factory.mktemp("ic_redirect")`；只分配 |
| `redirect_root_module` | module | `tmp_path_factory.mktemp("ic_redirect_module")`；只分配 |
| `ic_persist_redirect` | function | activate session root；yield；finally assert own spy + deactivate |
| API session/module polluter | session/module | setup 內 activate → HTTP/task wait → assert own spy → finally deactivate |

每個 REDIRECT test file：

```python
pytestmark = [pytest.mark.ic_persist_redirect, pytest.mark.usefixtures("ic_persist_redirect")]
```

session/module fixture **不得** request function fixture；它直接 request `redirect_patch_set` + appropriate root 並手動 activate。禁止 root `tests/conftest.py` autouse activation；根 conftest 只可讓 FF test 取得 plugin fixture。

---

## §G Golden A/B/C（保留三跑，修正 Run C hermetic root）

`tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py`：

| Run | gate | cwd / 唯一允許寫入 | 預期 |
|---|---|---|---|
| A | ON，`tmp_a` | `tmp_path/work`；實際寫 `tmp_a` | `hash_a` |
| B | ON，`tmp_b` | `tmp_path/work`；實際寫 `tmp_b` | `hash_b == hash_a` |
| C | **OFF，必跑** | `monkeypatch.chdir(tmp_path/work)`；只可寫 `tmp_path/work/data_cache` | `hash_off == hash_a` |

Run C 執行前建立 sacrificial `work/data_cache/{features,reports,models}`；OFF 表示 active gate 關閉，不表示 cwd 在 repo。test 必記 repo root `data_cache` digest before/after 並相等；outer V5 digest 再做第二層證明。任何 baseline 缺失 `pytest.fail()`，禁止 skip。

`normalize(result)` 保留 R3 定義：sorted keys、`json.dumps(..., sort_keys=True, default=str)`；只豁免 `filtered_features_path`、`report_paths`、`artifact_mtime` 等純路徑/mtime 欄位。不得豁免數值、NaN pattern、feature count、selection、schema 欄位。stdout 必含 `ab_hash=`。

---

## §ISOLATION I1–I3（具體可執行）

| Case | 作法 | 通過條件 |
|---|---|---|
| I1 | parent test 用 subprocess 跑下列三個固定 non-opt-in nodeid；env `IC_PERSIST_ASSERT_NO_ACTIVATION=1` + probe JSON path | subprocess exit 0；JSON `activation_count=0`、`violations=[]`；三 test passed |
| I2 | parameterize S1–S11 probes | 每 seam output 位於 root；owning spy 無 violation；漏一 seam activate fail |
| I3 | inventory 對 §COVERAGE REDIRECT 檔與 marker/helper wiring | 缺 marker、S9/S11 helper、或多出未分類 caller 都 FAIL |

I1 固定 nodeids：

```text
tests/api/test_ic_run_selector.py::test_disambig_same_tf_different_hash
tests/momentum/test_ic_filter_orchestrator.py::test_refilter_without_cache_raises
tests/momentum/Analysis/test_long_short_analyzer.py::test_insufficient_ls_samples
```

plugin 的 `pytest_sessionfinish` 只在 `IC_PERSIST_ASSERT_NO_ACTIVATION=1` 時寫 probe JSON並在 activation_count/violations 非零時令 exit 非 0。parent test 解析 JSON，不用跨 subprocess 讀本 process counter。

---

## §GEN 手動 generator seam

保留 R3 `tests/fixtures/ic_persist_redirect_manual.py`。`run_with_manual_redirect(root=None)` 從顯式參數或 `IC_PERSIST_REDIRECT_ROOT` 取得 root，使用同一 `RedirectPatchSet.activate()`，finally 斷言 own spy 並 deactivate。GEN-01..04 頂部具名 import/call；env 缺失 exit 2。手動工具不得依賴 pytest `MonkeyPatch`。

---

## §V 驗證策略：V1/V2/V5/V6/V7 全部 digest guard

### SHA-256 oracle

`digest_data_cache()` 掃 repo `data_cache/features`、`reports`、`models` 的每個 regular file，輸出 `{relative_path: sha256}`。path+size、mtime、postflight 都只能輔助，不可取代 digest。

### `scripts/run_ic_persist_hermetic.sh`

腳本接受 `--set V1|V2|V5|V6|V7|all`。每一組都獨立執行：

```bash
run_guard() {
  label="$1"; shift
  pre="$(venv/bin/python -c 'from tests.fixtures.ic_persist_redirect import digest_data_cache; import json; print(json.dumps(digest_data_cache(), sort_keys=True))')"
  "$@"
  post="$(venv/bin/python -c 'from tests.fixtures.ic_persist_redirect import digest_data_cache; import json; print(json.dumps(digest_data_cache(), sort_keys=True))')"
  if [[ "$pre" != "$post" ]]; then
    echo "DIGEST_DIFF_EMPTY[$label]=0"
    return 1
  fi
  echo "DIGEST_DIFF_EMPTY[$label]=1"
}
```

腳本 `set -euo pipefail`；pytest failure、digest command failure、digest mismatch 任一皆 exit 非 0。`all` 依序跑 V1、V2、V5、V6、V7；stdout 必有五個 `DIGEST_DIFF_EMPTY[Vn]=1`。禁止直接跑裸 V2/V5/V6/V7 當 hermetic acceptance；正式驗收以此 wrapper 為準。

### 驗收集

| ID | command / set | exit contract |
|---|---|---|
| V1 | harness `--set V1`：R3 的 oos 2 + IC e2e + feature-filter 1 + cut1 golden 2 | `9 passed, 1 skipped`；唯一 skip perf；digest=1 |
| V2 | harness `--set V2`：兩個 `test_ic_analysis_service.py` nodeid | `2 passed, 0 skipped`；digest=1 |
| V3 | harness `--set all` | V1/V2/V5/V6/V7 五個 digest=1；exit 0 |
| V3b | mutation test | `1 passed`；mutation disabled branch 實際改 sacrificial fake prod |
| V4 | isolation **加 inventory 檔** | I1–I3 全跑；`≥4 passed`，0 failed |
| V5 | harness `--set V5`：new A/B/C + existing two cut1 golden；`-s` | `3 passed`、0 skipped、`ab_hash=`、digest=1 |
| V6 | harness `--set V6`：三個 API polluter files | `≥30 passed`、0 failed；digest=1 |
| V7 | harness `--set V7`：下列六檔 | collected=141；0 failed；skip 僅白名單；digest=1 |
| V8 | `grep -r "from api\." momentum/` | 0 result |
| V9 | preflight + V3 + postflight | 輔助；不得替代 V3 |

V4 command：

```bash
venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_persist_redirect_isolation.py \
  tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q -s
```

V7 六檔：

```text
tests/test_feature_factory_e2e.py
tests/momentum/Analysis/test_lightgbm_analyzer.py
tests/momentum/Analysis/test_lightgbm_edge_cases.py
tests/momentum/Analysis/test_xgboost_protocol_methods.py
tests/momentum/test_lightgbm_analyzer_phase3.py
tests/momentum/test_xgboost_protocol_methods_phase3.py
```

V7 skip 白名單：只允許 `tests/test_feature_factory_e2e.py` 由 `_require_data` / missing kline 產生的 skip；report 中任何其他 nodeid/reason skip 皆 FAIL。不得用 `passed == collected - arbitrary skips`。

---

## §C 實作邊界與 allowed files

- 新建：`tests/fixtures/ic_persist_redirect.py`、`ic_persist_redirect_plugin.py`、`ic_persist_redirect_manual.py`。
- 新建：`tests/momentum/conftest.py`、`scripts/run_ic_persist_hermetic.sh`。
- 新建測試：`test_ic_persist_redirect_unit.py`、`test_ic_data_cache_hermetic.py`、`test_ic_persist_redirect_isolation.py`、`test_ic_persist_redirect_inventory.py`、`test_ic_persist_redirect_golden_ab.py`。
- 修改 REDIRECT test files/conftest，只做 marker、fixture lifecycle、S9/S11 helper wiring。
- 修改 GEN-01..04，只接具名 manual helper。
- 不修改 repo `data_cache/`；不跑裸 polluting body；不改 root `HANDOFF.md`。
- 生產碼公開簽名、數值、schema、persist payload/檔案大小不變。

---

## §P Phase 與測試圖

```text
Phase 1: process-global gate + manifest + atomic rollback
  ├── unit: global visibility / nested reject / teardown ownership
  ├── unit: S1..S11 resolve + probes + missing-import mutation
  └── prototype-equivalent asyncio.to_thread regression
        ↓
Phase 2: REDIRECT wiring
  ├── IC/API session+module lifecycle
  ├── ML S10
  ├── FF S11
  └── export direct h5py S9
        ↓
Phase 3: hermetic acceptance
  ├── Golden A/B/C, C under tmp/work/data_cache
  ├── I1 subprocess / I2 seams / I3 inventory
  ├── mutation canary
  └── V1/V2/V5/V6/V7 per-set digests
        ↓
Phase 4: GEN-01..04 manual helper
```

Sequential implementation；patcher、wiring、acceptance 都共享同一 fixture module，無安全平行施工機會。

### Failure modes

| failure | test / handling | 可見性 |
|---|---|---|
| worker 看不到 active root | `asyncio.to_thread` regression + mutation | assertion 明紅 |
| seam import drift | completeness mutation；activation refuse before patch | `RedirectCompletenessError` |
| installer 半途失敗 | rollback unit test；gate inactive | error + no leaked patch |
| fixture teardown 漏清 | ownership/count + I1 subprocess | teardown/session exit 非 0 |
| session spy 驗錯 context | fixture teardown assert own spy | setup/teardown 明紅 |
| Run C 寫 repo | tmp cwd contract + test digest + V5 outer digest | digest=0 / exit 1 |
| ML/FF/API 未被 digest 包住 | V2/V5/V6/V7 wrapper sets | 缺 label 即 acceptance fail |
| unexpected V7 skip | nodeid/reason whitelist | harness exit 1 |

---

## NOT in scope

- 生產 cache architecture 重構：本票只處理 legacy test/generator 落盤隔離。
- 改 persist schema、壓縮、dtype、NaN/inf gate：會跨出票據資料正確性 scope。
- pytest 平行化：本設計依賴同 process serial activation；另案才可設計 task-local root 或 per-worker ownership。
- 票 5 golden provenance/rebaseline：本票只要求 redirect ON/OFF normalized equivalence，不改 baseline payload。

## What already exists

- R3 已有 tmp root lifecycle、ProductionWriteSpy、digest oracle、Golden A/B/C、I1–I3、manual generator consumer輪廓；R4保留並修正 thread visibility、owning spy、OFF cwd 與完整 digest coverage。
- `tests/feature_engineering/conftest.py` 已隔離 FF 子樹；本票只補 root `test_feature_factory_e2e.py`。
- API/IC 現有 helper/fixture 保留；不另建平行 service。

---

## R4-CLOSURE — 每個 open finding 的去向

| Finding ID | R3 狀態 | R4 closure |
|---|---|---|
| codex B1 | STILL-OPEN | §COVERAGE 將 exact 16 caller 與 regex 外三 API polluter 分表；V7 六檔保留 |
| codex B2 | STILL-OPEN | §SEAM process-global patch set；S1–S11 declarative manifest；S9/S11 具名 helper；atomic resolve/install |
| codex B3 | CLOSED | 保留 executable shell + exit propagation；R4擴成 selectable digest sets |
| codex B4 | STILL-OPEN | §G Run C OFF 必在 `tmp_path/work`，只寫 sacrificial `work/data_cache`；V5 outer digest |
| codex B5 | STILL-OPEN | §ISOLATION 列三 fixed nodeids、subprocess env/probe JSON/exit contract；V4納 inventory |
| codex B6 | CLOSED | 大任務 manifest + RISK-HIT a,b 保留 |
| codex M1 | CLOSED | V1 精確 skip；V5 `-s` / `ab_hash=`；harness stdout labels |
| codex N1 | STILL-OPEN | TLS 廢除；process-global active gate + RLock + nested reject；P1/P2實跑 |
| codex N2 | CLOSED | §GEN 具名 consumer + env missing exit 2 保留 |
| codex N3 | CLOSED | V7 六檔 + collect 141 保留並納 digest |
| codex NEW-1 | BLOCKING | session/module fixture teardown 斷言自己的 context spy；原型 conftest 已實作並 8/8 |
| codex NEW-2 | BLOCKING | §V V2/V5/V6/V7 各有 `run_guard`；V3 all 要五個 digest labels |
| grok BLOCKING-5 | CLOSED lifecycle | R4保留合法 session/module 手動 lifecycle，改用 process-global gate |
| grok NEW-1 / NEW-2 | CLOSED | V1與V7精確契約保留 |
| grok NEW-3 | cosmetic | API-06 case-id 命名不影響安全/驗收；明列 NOT BLOCKING，未擴 scope |
| grok NEW-R3-1 | BLOCKING | patcher activate 強制 resolve/install S1–S11；任一 import/installer/probe 缺失拒絕 activate |
| grok NEW-R3-2 | BLOCKING | §G Run C hermetic cwd/root + test內/outer雙 digest |
| grok NEW-R3-3 | MINOR | V4命令加入 `test_ic_persist_redirect_inventory.py` |
| grok NEW-R3-4 | MINOR | V7 skip 改 nodeid/reason 白名單，只准 FF missing kline |

R4 尚待雙家族 re-verify；本稿不自授 `RECONCILE-STAMP: APPROVED`。

---

ASSUMPTIONS_VERIFIED: process-global active root跨 asyncio.to_thread；non-opt-in inactive；mutation拔 redirect令 canary exit 1；restore後原型8/8；16-caller exact list；API fixture scopes；V1/V7既有 collect receipts沿用R3  
TESTS_RUN: `/tmp/p2debt-t2-proto` targeted P1 → 2 passed；mutation P2 → 1 failed/exit 1（預期）；full P3 → 8 passed；repo pytest body 0  
FAILURES_SEEN: 預期 mutation failure，feature 回到 `data_cache/features/THREAD_1h_filtered.h5`；restore後消失  
SCOPE_CHANGES: repo 唯一新產物 `handoffs/P2DEBT-T2-SPEC-DRAFT-R4.md`；prototype 僅 `/tmp/p2debt-t2-proto`  
NUMERIC_OR_SCHEMA_IMPACT: none；SPEC 禁止數值/schema/輸出大小變動  
HANDOFF_OUTPUT: `handoffs/P2DEBT-T2-SPEC-DRAFT-R4.md`

STATUS: DONE
