# P2 債票 6 — label horizon 測試 fixture rename — TODO 初稿 R1

> 狀態: **DRAFT** | task-id: `p2debt-t6` | 日期: 2026-07-12 | 對應 SPEC: `handoffs/P2DEBT-T6-SPEC-DRAFT-R1.md`  
> 冷啟動: 讀 §0 + 當前 Task 即可；SPEC 為權威；反注入同 SPEC。

---

## §0 開工前檢查

- [ ] 讀 `handoffs/P2DEBT-T6-SPEC-DRAFT-R1.md` + `handoffs/P2DEBT-T6-CHAIR-ROOTCAUSE.md`
- [ ] RECONCILE-STAMP 全 APPROVED（未核可 → BLOCKED，不動工）
- [ ] `bash scripts/agent_preflight.sh`（Claude 派工前）
- [ ] 確認允許改檔僅: `tests/api/test_ic_{deep_analysis,analysis_api,export_api,analysis_service}.py`

---

## §1 命名點 → Task 映射

| 命名點 | 檔案:行 | Task | 目標 |
|--------|---------|------|------|
| A1 | `test_ic_deep_analysis.py:118` | Task 2.1 | `["return_5"]` |
| A2 | `test_ic_analysis_api.py:89` | Task 2.2 | `["return_5"]` |
| A3 | `test_export_api.py:109` | Task 2.3 | `["return_5"]` |
| B1 | `test_ic_analysis_service.py:123` | Task 2.4（**條件**） | 待 adversarial：likely `return_1` 或 skip |

---

## Phase 1 — Preflight 與基線快照

### Task 1.1 重現 26 nodeid 紅

- **命令**:
  ```bash
  source venv/bin/activate
  pytest tests/api/test_ic_deep_analysis.py tests/api/test_ic_analysis_api.py \
    tests/api/test_export_api.py tests/api/test_ic_analysis_service.py -q -ra --tb=no
  ```
- **記錄**: FAILED/ERROR nodeid 列表 vs SPEC §逐 nodeid
- **特別確認**: service 三測（#24-26）當前是紅還是綠；若已綠，Task 2.4 僅文件化不動碼

### Task 1.2 生產碼指紋

- **命令**:
  ```bash
  git diff --stat -- momentum/ api/
  grep -n '_resolve_label_horizon_from_column\|fullmatch(r"return_' \
    momentum/Analysis/ic_filter_orchestrator.py
  ```
- **存檔**: receipt 貼 impl handoff（impl 後再 diff 比對）

---

## Phase 2 — Fixture rename（核心）

### Task 2.1 `test_ic_deep_analysis.py` 命名點 A1

**檔案**: `tests/api/test_ic_deep_analysis.py`

| 步驟 | 行 | 動作 |
|------|-----|------|
| 2.1.1 | **118** | `_write_labels_h5(labels_path, labels, timestamps, ["label"])` → `["return_5"]` |
| 2.1.2 | — | **不**改 L113 `labels` 變數名、不改 L134-145 `config_override`、不改任何 assert |
| 2.1.3 | — | 驗 7 個 nodeid（SPEC #1-7） |

**局部驗收**:
```bash
pytest tests/api/test_ic_deep_analysis.py -v --tb=short
```

**解鎖 nodeid**: #1-7

---

### Task 2.2 `test_ic_analysis_api.py` 命名點 A2

**檔案**: `tests/api/test_ic_analysis_api.py`

| 步驟 | 行 | 動作 |
|------|-----|------|
| 2.2.1 | **89** | `_write_labels_h5(..., ["label"])` → `["return_5"]` |
| 2.2.2 | — | **不**改 L96-108 `config_override` |
| 2.2.3 | — | 驗 9 個 nodeid（SPEC #8-16） |

**局部驗收**:
```bash
pytest tests/api/test_ic_analysis_api.py -v --tb=short
```

**解鎖 nodeid**: #8-16

---

### Task 2.3 `test_export_api.py` 命名點 A3

**檔案**: `tests/api/test_export_api.py`

| 步驟 | 行 | 動作 |
|------|-----|------|
| 2.3.1 | **109** | `_write_labels_h5(..., ["label"])` → `["return_5"]` |
| 2.3.2 | — | **不**改 L116-127 `analyze_payload` |
| 2.3.3 | — | 驗 7 個 nodeid（SPEC #17-23） |

**局部驗收**:
```bash
pytest tests/api/test_export_api.py -v --tb=short
```

**解鎖 nodeid**: #17-23

---

### Task 2.4 `test_ic_analysis_service.py` 命名點 B1（條件）

**檔案**: `tests/api/test_ic_analysis_service.py`

**前置**: Task 1.1 確認 #24-26 狀態 + adversarial STAMP 是否納入 B1

| 步驟 | 行 | 動作 |
|------|-----|------|
| 2.4.0 | — | 若 #24-26 已 PASS 且欄名已是 `return_1` → **跳過改碼**，僅 receipt 註記 |
| 2.4.1 | **123** | （若 STAMP 要求）DataFrame 欄 `"label"` → `"return_1"`（cross-sectional kline 衍生 horizon=1；**非** 5） |
| 2.4.2 | — | **不**改 `_SleepingAnalyzer` / `_append_cross_sectional_labels_*` 之 oracle 斷言 |
| 2.4.3 | — | 驗 `test_run_analysis_does_not_block_event_loop` + append 三測 |

**局部驗收**:
```bash
pytest tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop \
  tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_real_3sym_oracle \
  tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_kline_hole_becomes_nan_not_raise \
  tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_mutation_rangeindex_regresses -v
```

**解鎖 nodeid**: #24-26（若曾紅）+ B1 預防性對齊

---

## Phase 3 — 整合驗收

### Task 3.1 全 26 nodeid

```bash
source venv/bin/activate
pytest tests/api/test_ic_deep_analysis.py tests/api/test_ic_analysis_api.py \
  tests/api/test_export_api.py tests/api/test_ic_analysis_service.py -v --tb=short
```
- **PASS**: 0 failed, 0 errors

### Task 3.2 生產碼零變更

```bash
git diff --stat -- momentum/ api/
grep -r "from api\." momentum/ | wc -l   # 期望 0
```
- **PASS**: 無 momentum/api 生產 diff

### Task 3.3 解耦 smoke（非本票根因，但 Pre-Commit）

```bash
pytest tests/momentum/Analysis/test_ic_filter_orchestrator.py -q -k "horizon" --tb=no
```
- 僅確認未意外波及；若無對應 test 則 skip 並註記

---

## Phase 4 — 票 2 基線同步（Claude / 票 6 閉合後）

### Task 4.1 v6_baseline 縮減提案

- **檔案**: `tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt`
- **動作**: 移除本票修復之 23 個 API nodeid（保留註解 pinned SHA）
- **.harness**: 確認 `scripts/run_ic_persist_hermetic.sh --set V6` + `V6_NO_NEW_RED=1` 仍 pass digest
- **權限**: 依 reconcile 決策 — impl 端預設 **只出提案**，由 Claude commit

---

## §逐檔檢查清單（impl 自檢）

| 檔案 | 行 | 改前 | 改後 | horizon 依據 |
|------|-----|------|------|--------------|
| `test_ic_deep_analysis.py` | 118 | `["label"]` | `["return_5"]` | default_horizon=5 |
| `test_ic_analysis_api.py` | 89 | `["label"]` | `["return_5"]` | default_horizon=5 |
| `test_export_api.py` | 109 | `["label"]` | `["return_5"]` | default_horizon=5 |
| `test_ic_analysis_service.py` | 123 | `"label"` | TBD（`return_1`?） | adversarial |

**禁止改動行**: 各檔 `_write_features_h5`、meta json、`config_override` 閾值、assert 門檻。

---

## §Commit 規範（impl 端）

- 單 commit: `test: align IC API fixtures to return_<N> label horizon naming`
- **不** commit `data_cache/`
- handoff: `handoffs/20260712-p2debt-t6-impl.md`

---

```
ASSUMPTIONS_VERIFIED: SPEC §命名點 A1-A3 行號與 grep 一致
TESTS_RUN: 未跑（草稿）
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（計劃: 僅 label_names 字串）
產出: handoffs/P2DEBT-T6-TODO-DRAFT-R1.md
```

STATUS: DONE
