# P2 債票 2 SPEC R3 複驗 — grok（xAI）

Task-id: `p2debt-t2` | Date: 2026-07-11 | Role: §B8 原審查者 re-verify R3  
待審: `handoffs/P2DEBT-T2-SPEC-DRAFT-R3.md`（R3-CLOSURE 表）  
對照: `handoffs/P2DEBT-T2-SPEC-REVERIFY-grok.md`（R2；**未**讀 codex re-verify）  
Scope: repo **read-only**（僅本檔 + handoff 產物）；**未**跑 polluting repo pytest body；**未**寫 `data_cache/`；**未** git checkout/restore。

Open items 本輪: **BLOCKING-5**, **NEW-1**, **NEW-2**, **NEW-3** + hunt NEW。

---

## FACT-RECEIPT（本輪實跑）

### P1 — 原型 pytest（MANDATORY）

```text
命令: cd /tmp/p2debt-t2-proto && python -m pytest -q
結果: 7 passed in 0.05s
EXIT=0
```

原型目錄存在（`fakepkg/`, `tests/`, `pyproject.toml`）。非 missing/failing。

### P2 — mutation canary：redirect 撤銷必紅

| 模式 | 作法 | 結果 |
|------|------|------|
| baseline | `pytest tests/test_hermetic_mutation.py -v -s` | **2 passed**；stdout `DIGEST_DIFF_EMPTY=1`、`MUTATION_CANARY=1` |
| production redirect 拔除 | 暫改 `data_cache_root()` 恆回 `PRODUCTION_DATA_CACHE`，跑 `test_mutation_redirect_disabled_caught` | **FAILED** exit=1；restore 段 `digest(prod) == before_restore` 炸（RESTORE 寫入 fake_prod） |
| session polluter 無 patcher | 暫改 `ic_analysis_task_session` 去掉 `SessionRedirectPatcher` | `test_opt_in_session` **FAILED** exit=1；`feature` 落在 `data_cache/features/...` 非 redirect root |
| restore | 還原 `production.py` / `conftest.py` 後 `pytest -q` | **7 passed** EXIT=0 |

結論：mutation / session-redirect 撤銷**會失敗**（可證偽）；非紙面 canary。

### P3 — §SEAM vs 原型同構（讀碼）

| 元件 | 原型路徑 | R3 §SEAM | 同構？ |
|------|----------|----------|--------|
| `redirect_root_session` | `tests/conftest.py` session `tmp_path_factory.mktemp`，**不** activate | 同 | YES |
| `ic_persist_redirect` | function：`install_function_redirect` + yield 後 `deactivate()` | 同 | YES |
| `SessionRedirectPatcher` | `fakepkg/redirect.py` L68–112：`install` patch Path + TLS activate；`uninstall` restore + deactivate | 「同原型 L68–112」 | YES（lifecycle） |
| session polluter | `install()` → `analyze_and_persist` → `finally: uninstall` | `ic_analysis_task` 同構 | YES |
| 禁止 session 注 function `monkeypatch`/`tmp_path` | 原型無此依賴 | R3 明文禁止 | YES |
| `data_cache_root()` TLS | 原型 `production.py` 讀 `get_active_redirect_root()` | R3 §PROTO 有；**真實 repo 生產碼無此 getter**（見 NEW-R3-1） | lifecycle YES；port payload 缺口 |

### P4 — NEW-1 V1 exit contract

```text
collect-only V1 命令集 → 10 tests collected
test_ic_e2e.py: test_performance_800_features @ skipif(not RUN_IC_E2E_PERF)  # L231；預設 env 未設 → skip
```

R3 V1 通過條件：`9 passed, 1 skipped, 0 failed`；skipped **僅** `test_performance_800_features`。  
與 collect + skipif **一致**（R2「10 passed 且 0 skipped」矛盾已消）。

### P5 — NEW-2 V7 ML+FF 清單

| 檔 | 存在 |
|----|------|
| `tests/test_feature_factory_e2e.py` | YES |
| `tests/momentum/Analysis/test_lightgbm_analyzer.py` | YES |
| `tests/momentum/Analysis/test_lightgbm_edge_cases.py` | YES |
| `tests/momentum/Analysis/test_xgboost_protocol_methods.py` | YES |
| `tests/momentum/test_lightgbm_analyzer_phase3.py` | YES（**不在** Analysis/） |
| `tests/momentum/test_xgboost_protocol_methods_phase3.py` | YES |

```text
collect-only 上列 6 檔 → 141 tests collected
```

與 R3 V7 命令 + collect **141** 一致。

### P6 — 其餘抽樣（非 polluting body）

| 檢查 | 結果 |
|------|------|
| 16-caller `rg -l ... \| wc -l` | **16**；含 `test_ic_run_selector.py` |
| API scopes | `ic_analysis_task`/`export_task` **session**；`completed_ic_task` **module** |
| V2 collect | 2 |
| V6 三 API 檔 collect | 32（`≥30` 量級） |
| `export_task` L125–137 | 仍 `Path("data_cache/features")` + `h5py.File`（S9 目標） |
| 生產字面量 | `ic_analysis_service` / `ic_filter_orchestrator` / routes / ML `data_cache/models` 仍硬編碼（S1–S11 必要） |

---

## 原 open items 逐條

| ID | R2 要旨 | R3 閉合主張 | 本輪複驗 | 判定 |
|----|---------|-------------|----------|------|
| **BLOCKING-5** | session/module polluter 不可 request function redirect（ScopeMismatch + 時序洞） | `SessionRedirectPatcher` + `redirect_root_session`；setup 內 install/uninstall；禁 function 參數注入 session | 原型 7/7；fixture 表與 conftest **同構**；session 無 monkeypatch；撤 patcher 必紅 | **CLOSED**（pytest lifecycle） |
| **NEW-1** | V1 `10 passed, 0 skipped` vs 允許 1 skip 互斥 | V1 → `9 passed, 1 skipped, 0 failed`；skip 鎖 perf | collect=10 + skipif 預設 skip | **CLOSED** |
| **NEW-2** | V7 漏 edge_cases / phase3 路徑 | V7 六檔命令 + collect 141 | 六檔皆在；collect=141 | **CLOSED** |
| **NEW-3** | API-06 case_id 報告名 cosmetic | R3「維持；非阻擋」 | 仍 cosmetic；不阻 stamp 本體 | **STILL-OPEN**（cosmetic only） |

### BLOCKING-5 閉合詳證

R2 失敗根因：session fixture 參數 `ic_persist_redirect`（function）→ ScopeMismatch，且 session setup 早於 function usefixtures。

R3 + 原型：

1. **目錄**：`redirect_root_session` 只 mktemp，不 activate。  
2. **Session setup**：`SessionRedirectPatcher.install()` 手動 patch（**非** function `monkeypatch`）→ analyze → `uninstall`。  
3. **每 test**：`pytestmark usefixtures("ic_persist_redirect")` 再 activate TLS 於**同一** session root。  
4. **non-opt-in**：`get_active_redirect_root() is None`（原型 `test_non_opt_in`）。

此為原 B-5 可執行性洞的直接閉合。殘留「真實生產如何改路徑」見 **NEW-R3-1**（不回退 B-5 CLOSED）。

---

## NEW problems（R3 引入 / 本輪新發現）

### NEW-R3-1 — `SessionRedirectPatcher` 字面 port 擋不住真實 IC 寫盤（**BLOCKING**）

**證據**：

- 原型 redirect **有效**，因 `fakepkg/production.py` 的 `data_cache_root()` 讀 TLS。  
- 真實 repo：**無** `get_active_redirect_root` / `data_cache_root` 於 IC/ML 熱路徑；寫盤為 `Path("data_cache/...")`、`h5py.File`、`output_dir="data_cache/reports"` 等（P6）。  
- R3 寫 `SessionRedirectPatcher: ...  # 同原型 L68–112`：原型 L68–112 **只** patch `Path.write_bytes`/`mkdir` + TLS，**不**改路徑構造，**不**攔 `h5py.File`。  
- `export_task` 污染核在 `h5py.File(Path("data_cache/features")/...)`（S9）：即使 install 了 L68–112 spy，**mkdir 可被 spy、h5py 寫入仍落真 cache**。  
- S1–S11 表要求 wrap 改路徑，但**未釘死**：`SessionRedirectPatcher.install()` / `install_function_redirect()` **必須**在 activate 當下套用 S1–S11（session polluter setup 窗口內），uninstall 還原。

**影響**：API session/module polluter 若只「複製 L68–112」→ **仍污染** `data_cache/`，與 B-5 修法目標同失效（lifecycle 合法但 payload 空）。

**最低閉合（寫進 §SEAM，擇一釘死）**：

1. `install()` / `install_function_redirect()` / `run_with_manual_redirect()` 的契約 = **TLS(+spy) ∧ apply S1–S11 wraps**；uninstall 對稱還原；**禁止**僅 Path spy 當 redirect；或  
2. 生產側引入 `data_cache_root()` 單一 seam（等同原型），S1–S11 改讀該 getter（須另開「允許動 production 路徑解析」scope，與「不改 persist 簽名」並存需明示）。

未寫死前，不得稱 API session 接線「可執行且零污染」。

### NEW-R3-2 — §G Run C OFF 未要求 hermetic root（**BLOCKING**）

- §V mutation 有 `fake_prod` + chdir +「不寫真 repo data_cache」。  
- §G Run A/B/C：**無** fake_prod/chdir/work root；Run C = **OFF 無 patch 必跑**。  
- 原型 `test_golden_ab.py` 用 `work/` + `chdir` + 獨立 `fake_prod` 當 spy prefix。  
- 若 AB 測走真 `analyze`/persist，Run C 會寫入 **repo `data_cache/`**，與票旨 +「驗收不污染」衝突；且可能弄髒後續 V3 digest。

**最低閉合**：§G 明示與原型同構 — 全程 `tmp_path/work` chdir（或等價隔離 cwd/root）；ON/OFF 皆不得寫 repo `data_cache/`；OFF 僅允許寫隔離 work 下的 `data_cache`。

### NEW-R3-3 — V4 未納 `test_ic_persist_redirect_inventory.py`（**MINOR**）

- §ISOLATION / §C 新建 **inventory** 檔；I3 = inventory marker 對表。  
- V4 只跑 `test_ic_persist_redirect_isolation.py`，**不含** inventory 檔。  
- 若 I3 只在 inventory 檔 → 驗收可綠而 I3 未跑。

**修法**：V4 命令並上 inventory，或 I3 併入 isolation 模組並在 V4 註明 nodeid。

### NEW-R3-4 — V7 skip 契約偏軟（**MINOR**）

`passed == collected - data_missing_skips` 允許「資料缺失」類 skip 不列死 nodeid。合理於 kline 環境差，但可掩蓋誤 skip。TODO 宜要求 skip reason 白名單字串或列出允許 skip 的 test id 前綴。

---

## 五軸（R2 同軸 + R3 原型軸）

| 軸 | 結果 |
|----|------|
| BLOCKING-5 fixture lifecycle 可執行 | **PASS** — 原型 7/7 + 同構表 |
| mutation 撤 redirect 必紅 | **PASS** — 兩種 mutation 皆 exit≠0 |
| NEW-1 V1 精確 exit | **PASS** |
| NEW-2 V7 六檔 + 141 | **PASS** |
| 真實 session polluter 零污染可執行（S1–S11 掛入 install） | **FAIL** — NEW-R3-1 |
| §G OFF 不污染 repo | **FAIL** — NEW-R3-2 |

---

## 總表

| ID | 判定 |
|----|------|
| BLOCKING-5 | **CLOSED** |
| NEW-1 | **CLOSED** |
| NEW-2 | **CLOSED** |
| NEW-3 | **STILL-OPEN**（cosmetic，非本輪 BLOCK 因） |
| NEW-R3-1 | **STILL-OPEN / BLOCKING** |
| NEW-R3-2 | **STILL-OPEN / BLOCKING** |
| NEW-R3-3 | **STILL-OPEN / MINOR** |
| NEW-R3-4 | **STILL-OPEN / MINOR** |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: 原型 /tmp/p2debt-t2-proto 7/7；mutation 雙模式必紅；§SEAM fixture lifecycle 與原型同構；V1 collect=10+perf skipif；V7 六檔 collect=141；16-caller=16；API session/module scopes
TESTS_RUN: cd /tmp/p2debt-t2-proto && python -m pytest -q → 7 passed；mutation production 拔 TLS → 1 failed；session 無 patcher → 1 failed；restore → 7 passed；repo collect-only V1/V2/V6/V7 only（0 polluting body）
FAILURES_SEEN: mutation/session 故意失敗（預期）；restore 後全綠
SCOPE_CHANGES: none（僅 handoffs 產物）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**產出檔**：`handoffs/P2DEBT-T2-SPEC-REVERIFY-R3-grok.md`

---

Verdict: BLOCK — NEW-R3-1（SessionRedirectPatcher 字面 L68–112 未強制套用 S1–S11，真實 session polluter 仍可寫真 cache）+ NEW-R3-2（§G Run C OFF 無 hermetic root，驗收可污染 repo data_cache）

（未附 RECONCILE-STAMP APPROVED：存在 BLOCKING 未閉。）
