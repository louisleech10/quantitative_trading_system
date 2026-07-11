# P2 債票 2 SPEC R4 複驗 — grok（xAI）

Task-id: `p2debt-t2` | Date: 2026-07-11 | Role: §B8 原審查者 re-verify R4  
待審: `handoffs/P2DEBT-T2-SPEC-DRAFT-R4.md`（Codex 斷路器重寫）  
對照 open items: **NEW-R3-1**, **NEW-R3-2**（出自 `handoffs/P2DEBT-T2-SPEC-REVERIFY-R3-grok.md`）  
Scope: repo **read-only**（僅本檔）；**未**讀 composer re-verify；**未**跑 polluting repo pytest body；**未**寫 `data_cache/`；**未** git checkout/restore。

---

## FACT-RECEIPT（本輪實跑）

### P1 — 原型全量 pytest（MANDATORY）

```text
命令: cd /tmp/p2debt-t2-proto && python -m pytest -q
結果: 8 passed in 0.04–0.05s
EXIT=0
含: test_opt_in_to_thread (asyncio.to_thread)、function/session opt-in、
    non-opt-in、golden ab、hermetic digest/mutation、generator seam
```

### P2 — mutation：redirect 撤銷跨 thread canary 必紅

```text
命令: cd /tmp/p2debt-t2-proto && P2DEBT_PROTO_DISABLE_REDIRECT=1 \
  python3 -m pytest tests/test_opt_in_to_thread.py::test_to_thread_polluter_writes_under_redirect -v -s

結果: FAILED
  paths["feature"] = PosixPath('data_cache/features/THREAD_1h_filtered.h5')
  is_relative_to(redirect_root) == False
  spy.violations 含 proto data_cache/features + reports 路徑
EXIT=1（預期）
```

結論：mutation 可證偽；非紙面 canary。

### P3 — restore 後全綠

```text
命令: cd /tmp/p2debt-t2-proto && python -m pytest -q
結果: 8 passed
EXIT=0
```

### P4 — process-global gate 跨 `asyncio.to_thread`（獨立 probe）

```text
命令: python3 直接 activate RedirectContext → asyncio.to_thread(worker)
worker 讀 get_active_redirect_root() / data_cache_root() / analyze_and_persist

結果:
  main_thread_root == worker get == worker data_cache_root == activate root
  feature/report 皆在 redirect root 下
  thread name = asyncio_0
  THREAD_BOUNDARY_OK=1
  deactivate 後 get_active_redirect_root() is None
  nested second activate → RuntimeError（NESTED_REJECT_OK）
  concurrent reader 1000 次皆見同一 root（CONCURRENT_READ_OK）
```

與 R4 §SEAM「process-global active root + RLock + nested reject；to_thread 同 process gate」同構。

### P5 — §G Run C hermetic 對照原型

原型 `tests/test_golden_ab.py`：`work/` + `os.chdir(work)` + OFF 無 patch；ON/OFF normalized hash 相等。  
R4 §G：Run C `monkeypatch.chdir(tmp_path/work)`；只可寫 `tmp_path/work/data_cache`；test 內 + V5 outer 雙 `digest_data_cache`；baseline 缺 → fail 不 skip。

### P6 — S1–S11 目標存在性（repo 唯讀，非 body）

| ID | 目標 | 本輪 |
|----|------|------|
| S1 | `ICFilterOrchestrator._resolve_filtered_path` | 存在 |
| S2 | `ICReporter.save_report/save_filter_log/save_filtered_features` | 存在 |
| S3–S6 | `ICAnalysisService` 四方法 | 存在 |
| S7–S8 | `api.routes.ic_analysis` resolver + `export_filtered_csv` | 存在 |
| S9 | `_export_fixture_filtered_path` helper | **尚未存在**（SPEC 新建，預期） |
| S10 | lgb/xgb `_resolve_model_path` | 存在 |
| S11 | `_create_e2e_factory` helper | **尚未存在**（SPEC 新建，預期） |

硬編碼落盤仍在：`Path("data_cache/features|reports|...")`、`output_dir="data_cache/reports"`、`h5py.File`（export_task L125–137）——S1–S11 wraps 仍必要。

### P7 — 抽樣契約（collect-only / 無 body）

| 檢查 | 結果 |
|------|------|
| V1 collect | 10 |
| V7 六檔 collect | 141 |
| 16-caller `rg -l` | 16 |
| API scopes | `ic_analysis_task`/`export_task` session；`completed_ic_task` module |
| `settings.data_cache_path` | 絕對 repo `.../data_cache` |
| e2e `generate_features(` | 6 |
| e2e `generate_multi_tf(` | 1（見 NEW-R4-1） |
| e2e `create_feature_factory(` | 7 |

---

## Open items 逐條

### NEW-R3-1 — S1–S11 force-wiring → **CLOSED**

**R3 病灶**：`SessionRedirectPatcher`「同原型 L68–112」只 Path spy + TLS；真實 IC 無 `data_cache_root()` getter；session polluter lifecycle 合法但 path rewrite 空 → 仍可寫真 cache。

**R4 閉合證據（§SEAM）**：

1. 廢 TLS 為唯一 path decision；改 **process-global pass-through wrappers + active gate**（`RLock`、nested reject）。  
2. `REQUIRED_SEAM_IDS = S1..S11`；`resolve_all()` **先** resolve 全部 target/subtarget，`set(resolved)==REQUIRED_SEAM_IDS`，installer/probe 非空，否則 `RedirectCompletenessError`。  
3. `install_once()` 原子：全 resolve 成功才 patch；中途失敗 reverse rollback + gate inactive。  
4. `activate()` 再核 installed IDs；缺 seam **拒絕 activate**；已 active 拒 nested。  
5. 單元測 parameterize S1–S11：正向 probe、缺 import/attr mutation、installer 中途失敗、manifest 少/多 ID、S9/S11 不經 helper 必紅。  
6. S9/S11 改具名 helper（可 import/probe/mutation），不再靠散落 literal。  
7. session/module polluter：`redirect_patch_set.activate()`，**非**複製原型 Path-only spy 當 redirect payload。

**與 to_thread 對齊**：wrappers 掛在 class/module 上，process 全域可見；gate 讀寫在 lock 下——P4 實跑通過。

判定：**CLOSED**（SPEC 契約可執行且對準 R3 根因；實作時靠 unit mutation 防假綠）。

### NEW-R3-2 — Run C OFF hermetic root → **CLOSED**

**R3 病灶**：§G Run C = OFF 無 patch 必跑，但無 fake_prod/chdir；真 analyze 可寫 repo `data_cache/`。

**R4 閉合證據（§G + §V）**：

| 層 | 契約 |
|----|------|
| cwd | Run C `monkeypatch.chdir(tmp_path/work)` |
| 允許寫 | 僅 `tmp_path/work/data_cache`（sacrificial features/reports/models） |
| OFF 語意 | gate inactive，**不是** cwd=repo |
| 內層 digest | test 記 repo `data_cache` before/after 相等 |
| 外層 digest | V5 `run_guard` 再證 |
| baseline | 缺 → `pytest.fail()`，禁 skip |

與原型 golden_ab chdir(work) 同構且加雙 digest。判定：**CLOSED**。

---

## NEW problems（R4 / Codex 稿新鮮眼）

### NEW-R4-1 — FF e2e `generate_multi_tf` 未納 S11「六個」計數（**MINOR**）

- FF-01 / S11：`六個 generate_features()` + `_create_e2e_factory`。  
- 同檔 `test_multi_timeframe_alignment`：`MultiTFGenerator(...).generate_multi_tf(symbol)` 預設 `persist=True`，走 `factory._storage`（及可能 cgsa 路徑）。  
- `create_feature_factory(` 出現 7 次；若 helper 只換 6 個 generate_features 呼叫，multi_tf 仍可能寫 features。  
- **未升 BLOCKING 理由**：V7 跑整檔 + `digest_data_cache(features/reports/models)` fail-closed；污染會紅，不會靜默過。  
- **TODO 建議**：S11/I3 明示 multi_tf 亦必經 helper，或 `persist=False` + 不落盤斷言。

### NEW-R4-2 — `ProductionWriteSpy` 掛鉤機制在 §SEAM 欠釘（**MINOR**）

- R4 保留 spy 欄位與 teardown `assert own spy`；原型靠 patch `Path.write_bytes/mkdir`。  
- 實作設計以 method/Path-binding rewrite 為主，**未**寫死 spy 如何觀測 `h5py.File` / `open` / `to_hdf`。  
- 若 spy 永不記錄，teardown 永遠 `violations==[]`（spy 層假綠）；路徑 probe + outer digest 仍是主防線。  
- **TODO 建議**：釘 spy = 在各 installer rewrite 前 check production_prefix，或 process-global open/write hook 限 production_prefix。

### NEW-R4-3 — `production_prefix` 未強制絕對 repo root（**MINOR**）

- 相對 `Path("data_cache")` 在 chdir(work) 後 resolve 成 work 下路徑，spy 可能監錯 root。  
- Run C / V5 雙 digest 仍護 repo。建議 SPEC/TODO：`production_prefix = repo_root/data_cache` 絕對路徑。

### NEW-R4-4 — completeness 文案「無 wrapper 殘留」vs 永久 pass-through（**MINOR**）

- 架構：`install_once` 後 wrapper 常駐，inactive 走 original。  
- 單元測第 2 條「activate 缺 target → 無任何 wrapper 殘留」易與常駐設計衝突。  
- 應限縮為：**install 前** resolve 失敗 → 零 patch；**activate 再核**失敗 → 不 active、pass-through 可留。

### 不列 BLOCK 的觀察

- S10 若 call-through original 再 map return，original 內 `mkdir` 可能觸碰 production models 目錄（空目錄；digest 只掃 file）。Installer 應 active 時整段替換 allowed_root。  
- `data_cache/cgsa_work` 不在 digest 三目錄；本票 scope 既定 features/reports/models，不新開 BLOCK。

---

## 五軸總結

| 軸 | 結果 |
|----|------|
| NEW-R3-1 S1–S11 force-wiring | **PASS / CLOSED** |
| NEW-R3-2 Run C hermetic cwd/root | **PASS / CLOSED** |
| 原型 8/8 + to_thread | **PASS** |
| mutation 拔 redirect → exit 1 | **PASS** |
| process-global 跨 thread | **PASS**（P4） |
| 新 BLOCKING | **無**（僅 MINOR NEW-R4-1..4） |

---

## 總表

| ID | 判定 |
|----|------|
| NEW-R3-1 | **CLOSED** |
| NEW-R3-2 | **CLOSED** |
| NEW-R4-1 multi_tf / S11 計數 | **STILL-OPEN / MINOR** |
| NEW-R4-2 spy hook 欠釘 | **STILL-OPEN / MINOR** |
| NEW-R4-3 production_prefix 絕對化 | **STILL-OPEN / MINOR** |
| NEW-R4-4 wrapper 殘留文案 | **STILL-OPEN / MINOR** |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: 原型 8/8 含 asyncio.to_thread；P2DEBT_PROTO_DISABLE_REDIRECT=1 跨 thread canary exit 1；process-global gate + nested reject 實跑；R4 §SEAM S1–S11 resolve/install/activate refuse 對準 NEW-R3-1；§G Run C chdir(work)+雙 digest 對準 NEW-R3-2；S1–S8/S10 目標符號存在；V1 collect=10；V7 collect=141；16-caller=16
TESTS_RUN: cd /tmp/p2debt-t2-proto && python -m pytest -q → 8 passed；mutation DISABLE_REDIRECT to_thread → 1 failed EXIT=1；restore → 8 passed；獨立 to_thread probe THREAD_BOUNDARY_OK=1；repo collect-only only（0 polluting body）
FAILURES_SEEN: 預期 mutation failure（feature 落 data_cache/features/THREAD_…）；restore 後消失
SCOPE_CHANGES: none（僅本 handoff 產物）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**產出檔**：`handoffs/P2DEBT-T2-SPEC-REVERIFY-R4-grok.md`

---

RECONCILE-STAMP APPROVED (p2debt-t2 SPEC R4, grok, 2026-07-11)

Verdict: APPROVE

（MINOR NEW-R4-1..4 不阻擋 stamp；建議 TODO 階段吸收 multi_tf wiring + spy hook + absolute production_prefix + completeness 文案澄清。）
