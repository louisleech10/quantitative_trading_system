# P2DEBT-T2 C-4 裁決提案委員審查 — composer — 2026-07-11

Task-id: `p2debt-t2-c4-review-composer`  
待審: `handoffs/P2DEBT-T2-IMPL-CHAIR-FINDING-C4.md`（C-4 V6 紅=main 既有；P-1/P-2/P-3 裁決提案）  
Scope: **read-only** 驗證 + 本檔；**未**改測試/腳本/生產碼/HANDOFF.md。

---

## §判別鏈 3 獨立重放（receipt）

### 環境
- HEAD: `492c4cc`（`git worktree add /tmp/chk-composer-t2c4 HEAD`）
- T2 工作樹: `/Users/louis/Desktop/quantitative_trading_system`（未 commit 票 2 實作 diff）
- venv: `source venv/bin/activate`

### HEAD 基線（無票 2 改動）

| 命令 | 摘要 | rc |
|------|------|-----|
| `pytest tests/api/test_ic_deep_analysis.py -q -ra --tb=no` | `3 failed, 7 passed, 4 errors` | 1 |
| `pytest tests/api/test_ic_analysis_api.py tests/api/test_export_api.py tests/api/test_ic_analysis_service.py -q -ra --tb=no` | `3 failed, 8 passed, 2 skipped, 16 errors` | 1 |
| `pytest tests/api/test_ic_analysis_api.py tests/api/test_ic_deep_analysis.py tests/api/test_export_api.py -q -ra --tb=no`（**V6 檔案集**） | `3 failed, 9 passed, 20 errors` | 1 |

根因一致：`InvalidInputError: label horizon cannot be resolved from column: label`（與主委 C-4 敘述一致）。

### T2 vs HEAD V6 nodeid 比對

命令（Python 擷取 `FAILED|ERROR` nodeid）：

```text
HEAD_BAD_COUNT=23  T2_BAD_COUNT=23
T2_NOT_IN_HEAD=[]  HEAD_NOT_IN_T2=[]
SUBSET_OK=True（實為集合相等）
```

23 個基線 nodeid（HEAD=T2 相同）：

```text
tests/api/test_export_api.py::test_export_ai_json_200
tests/api/test_export_api.py::test_export_csv_detailed_factor_return
tests/api/test_export_api.py::test_export_csv_detailed_without_module_422
tests/api/test_export_api.py::test_export_csv_summary_200
tests/api/test_export_api.py::test_export_hdf5_200
tests/api/test_export_api.py::test_export_invalid_format_422
tests/api/test_export_api.py::test_export_markdown_200
tests/api/test_ic_analysis_api.py::test_ic_export_csv
tests/api/test_ic_analysis_api.py::test_ic_export_hdf5
tests/api/test_ic_analysis_api.py::test_ic_grouped
tests/api/test_ic_analysis_api.py::test_ic_quantile_and_correlation
tests/api/test_ic_analysis_api.py::test_ic_refilter
tests/api/test_ic_analysis_api.py::test_ic_result
tests/api/test_ic_analysis_api.py::test_ic_summary
tests/api/test_ic_analysis_api.py::test_ic_task_status
tests/api/test_ic_analysis_api.py::test_ic_top_features
tests/api/test_ic_deep_analysis.py::test_deep_analysis_result
tests/api/test_ic_deep_analysis.py::test_deep_analysis_result_serializes_numpy_scalars
tests/api/test_ic_deep_analysis.py::test_deep_analysis_start
tests/api/test_ic_deep_analysis.py::test_full_analysis
tests/api/test_ic_deep_analysis.py::test_full_analysis_endpoint
tests/api/test_ic_deep_analysis.py::test_full_analysis_with_deep_analysis_config
tests/api/test_ic_deep_analysis.py::test_start_deep_analysis_and_get_result
```

### digest（票 2 工作樹）

```text
命令: bash scripts/run_ic_persist_hermetic.sh --set V6 > /tmp/t2-v6-composer.log 2>&1; echo HERMETIC_V6_RC=$?
摘要: 3 failed, 9 passed, 20 errors
DIGEST_DIFF_EMPTY[V6]=1
HERMETIC_V6_RC=1
```

redirect 守衛未破（digest=1）；pytest 仍紅（rc=1），與 codex 對照 receipt 一致。

### 判別鏈 1–2（交叉引用，未重跑 grok sandbox）

- codex 對照：`handoffs/P2DEBT-T2-V6-CODEX-RUN.md` 同 `3 failed, 9 passed, 20 errors` + `DIGEST_DIFF_EMPTY[V6]=1`。
- 本輪 HEAD 重放排除「僅 sandbox 假紅」假設；與 codex 摘要一致。

**§判別鏈 3 結論：CONFIRMED** — V6 全紅點在 HEAD 原樣重現；票 2 未引入新紅。

---

## 票 2 `git diff tests/api/` label 語意稽核

```text
命令: git diff --stat -- tests/api/
結果: 4 files, +138/-73（redirect marks、fixture 包裝、路徑 helper；無生產碼）
```

`label` 相關 diff 僅縮排位移；欄名仍為 `["label"]`，無 horizon 後綴、無解析邏輯、無 assertion 門檻變更。

**結論：CONFIRMED** — 票 2 diff 無 label 語意變更。

---

## 裁決提案 STAMP

### P-1 — V6 驗收準則改「無新增紅」

**STAMP: APPROVED**（附條件）

理由：
- 獨立重放證實 main@492c4cc V6 已紅 23 nodeid；票 2 集合相等（非子集真子集而是 **零 delta**）。
- 凍結 SPEC 現行 V6 列（`≥30 passed, 0 failed`）與 main 基線矛盾；以 nodeid ⊆ 基線 + `DIGEST_DIFF_EMPTY[V6]=1` 作票 2 驗收合理且可證偽。
- 條件（實作前必做，否則 P-3 無法機械 PASS）：
  1. 修訂 `docs/P2DEBT_T2_DCREDIRECT_SPEC.md` §V V6 列與 harness 契約（現 `run_guard` 仍 `test_rc≠0 → return 1`）。
  2. 將上列 23 nodeid 寫入 receipt/基線檔（SHA 釘 `@492c4cc`），避免漂移。
  3. V3 `--set all` 的 exit 語意須一併定義（V6 子集 PASS 時 `all` 是否仍整體 rc=1 需明示）。

### P-2 — label horizon 既有紅另立新票

**STAMP: APPROVED**

理由：
- HEAD 無票 2 改動即重現 `label horizon cannot be resolved from column: label`；根因在 fixture 欄名 `label` vs 生產 `_resolve_label_horizon_from_column`，非 redirect scope。
- 命中 a) 數值/資料品質；應完整管線（SPEC/adversarial），不塞票 2。
- 補記：`test_ic_analysis_service.py` 另有 3 個 `test_append_cross_sectional_labels_*` FAILED（HEAD 即有，不在 V6 檔案集）；新票 scope 須釐清是否一併涵蓋 API fixture 家族。

### P-3 — 依新準則重跑全套出 final5

**STAMP: APPROVED**（依賴 P-1 條件落地）

理由：
- 順序正確：P-1 SPEC+harness 修訂 → 依 nodeid 子集規則重跑 V1–V7 → 五 digest receipt（final5）→ 實作雙審。
- 本輪已驗 T2 V6 digest=1，但 **未** 在舊 harness exit 語意下標 PASS；final5 須用修訂後 gate 重跑。
- 禁止以現行 `run_guard` pytest rc=1 搭配口頭「無新增紅」充當 final5 PASS。

---

```
ASSUMPTIONS_VERIFIED: HEAD@492c4cc V6 23 bad nodeids 與 T2 相等；label diff 僅縮排；DIGEST_DIFF_EMPTY[V6]=1@T2 worktree
TESTS_RUN: git worktree HEAD pytest(3 組)；Python nodeid 比對；git diff tests/api/ label 稽核；bash scripts/run_ic_persist_hermetic.sh --set V6 → HERMETIC_V6_RC=1 DIGEST=1
FAILURES_SEEN: expected — V6 pytest 紅為基線既有，非票 2 新增
SCOPE_CHANGES: none（僅 handoffs/P2DEBT-T2-C4-REVIEW-composer.md）
NUMERIC_OR_SCHEMA_IMPACT: none
產出: handoffs/P2DEBT-T2-C4-REVIEW-composer.md
```

STATUS: DONE
