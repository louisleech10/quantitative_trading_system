# P2DEBT-T2 C-4 裁決審查（Grok）

- Task-id: `p2debt-t2-c4-review-grok`
- Reviewer: Grok | Date: 2026-07-11T14:38Z
- Source finding: `handoffs/P2DEBT-T2-IMPL-CHAIR-FINDING-C4.md`
- HEAD baseline: `492c4cc`（clean worktree `/tmp/p2debt-t2-c4-chk`，無票 2 改動）
- Scope: 唯讀驗證 + 本檔；未改測試/腳本/生產碼

---

## STAMP

| 提案 | 裁決 | 一句理由 |
|------|------|----------|
| **P-1** V6 改「無新增紅」準則 | **APPROVED** | HEAD@492c4cc 與票 2 V6 紅 nodeid 集合**全等**（23/23）；`DIGEST_DIFF_EMPTY[V6]=1` 兩輪已有 |
| **P-2** label horizon 既有紅另立新票 | **APPROVED** | 根因在 fixture `["label"]` vs 生產 `_resolve_label_horizon_from_column` 只認 `return_(\d+)`；屬 a 類、非 redirect scope |
| **P-3** 依新準則重跑全套出 final5 | **APPROVED** | P-1 生效後 V6 不得再以「全綠/≥30p」卡死；需 nodeid⊆基線 + 五 set digest 的 formal receipt 再進雙審 |

---

## 獨立驗證（判別鏈）

### A. `git diff tests/api/` — 無 label 語意變更

`git diff --stat tests/api/`（working tree vs HEAD）:

| 檔 | 變更性質 |
|----|----------|
| `test_export_api.py` | pytestmark redirect + fixture 包 activate/deactivate；filtered path 改走 `get_active_redirect_root()` |
| `test_ic_analysis_api.py` | pytestmark + session fixture 包 redirect |
| `test_ic_analysis_service.py` | 兩測加 mark/usefixtures only |
| `test_ic_deep_analysis.py` | pytestmark + module fixture 包 redirect |

**Label 欄名**：HEAD 與 dirty 皆為 `_write_labels_h5(..., ["label"])`（三檔路徑未改字面）。  
diff 中 `labels`/`label` 僅 indentation/wrap 位移，**無**改名為 `return_N`、無改 schema/config_override labels。  
`git status --short momentum/ api/` → 空（票 2 未動生產解析器）。

### B. HEAD worktree 重放（finding §3）

```text
# worktree @492c4cc
venv/bin/python -m pytest tests/api/test_ic_deep_analysis.py -q --tb=line
→ 3 failed, 7 passed, 4 errors   # 與 finding 一致；根因全 label horizon

venv/bin/python -m pytest tests/api/test_ic_analysis_api.py \
  tests/api/test_export_api.py tests/api/test_ic_analysis_service.py -q --tb=line
→ 3 failed, 8 passed, 2 skipped, 16 errors
  # 16 ERROR = label horizon（api+export setup）
  # 3 FAILED = service cross-sectional FileNotFoundError(manifest) — 非 V6 集合，屬 finding 旁證

# V6 等價三檔（與 harness run_v6 一致，不含 service）
venv/bin/python -m pytest tests/api/test_ic_analysis_api.py \
  tests/api/test_ic_deep_analysis.py tests/api/test_export_api.py -q --tb=no
→ 3 failed, 9 passed, 20 errors   # 與票 2 V6 摘要字面一致
```

Logs: `/tmp/p2debt-t2-c4-head-deep.log`、`/tmp/p2debt-t2-c4-head-api3.log`、`/tmp/p2debt-t2-c4-head-v6files.log`

### C. 票 2 V6 既有 receipt（判別鏈 1–2、4）

| 來源 | 摘要 | DIGEST |
|------|------|--------|
| grok hermetic all `/tmp/t2-all-grok.log` | `3 failed, 9 passed, 20 errors` | `DIGEST_DIFF_EMPTY[V6]=1` |
| codex V6 `/tmp/t2-v6-codex.log` + `handoffs/P2DEBT-T2-V6-CODEX-RUN.md` | 同上 | `DIGEST_DIFF_EMPTY[V6]=1` |

Sandbox 假紅假設已由 codex 同紅排除（本輪採信既有 log，未重跑 hermetic）。

### D. nodeid 集合比對（P-1 核心）

HEAD V6-files 紅集合 vs codex V6 short-summary 紅集合：

- HEAD red count = **23**
- CODEX red count = **23**
- `NEW_IN_V6_NOT_IN_HEAD = []`
- `IN_HEAD_NOT_IN_V6 = []`
- **SUBSET_OK = True**（實際為**集合相等**，強於 ⊆）

固定 3 FAILED nodeid（兩邊相同）:

1. `tests/api/test_ic_deep_analysis.py::test_full_analysis_endpoint`
2. `tests/api/test_ic_deep_analysis.py::test_full_analysis_with_deep_analysis_config`
3. `tests/api/test_ic_deep_analysis.py::test_full_analysis`

固定 20 ERROR nodeid：api 9 + deep 4 + export 7（兩邊相同；見上列 log）。

### E. 根因（支援 P-2）

HEAD `momentum/Analysis/ic_filter_orchestrator.py` `_resolve_label_horizon_from_column`：

- 只接受 `return_(\d+)` fullmatch
- bare `"label"` → `InvalidInputError: label horizon cannot be resolved from column: label`

Fixture 自 HEAD 起即寫 `["label"]` → **main 既有紅**，非票 2 引入。

---

## 提案細則意見（非 BLOCK）

**P-1 實作時建議寫死（執行端/主委收尾用）**：

1. 基線 commit 鎖 `492c4cc`（或重放當下 `git rev-parse HEAD` 若仍無票 2 commit）。
2. 基線 nodeid 集合 = 本檔 §D 的 23 個（或 re-run V6 三檔於 clean HEAD 的 FAILED∪ERROR）。
3. 驗收：`V6_FAIL_SET ⊆ BASELINE_FAIL_SET` **且** `DIGEST_DIFF_EMPTY[V6]=1`；**不得**要求 `≥30 passed / 0 failed`（凍結 SPEC 該列視為本裁決 supersede，僅限票 2 驗收）。
4. ERROR 表面文案（`task timeout` vs 內層 label horizon）可波動；**以 nodeid 為準**，勿以 message 字串當 gate。

**P-2**：新票應含 fixture 欄名契約（`return_{h}`）或解析器對 bare `label`+config horizon 的明確策略；涉 IC full analysis 正確性 → 完整管線，勿塞票 2。

**P-3**：final5 = V1/V2/V5/V6/V7（V6 用 P-1）；通過後再實作雙審。V7 等仍用原綠準則。

---

## 裁決結論

- 判別鏈 1–4 **可重放、已獨立核實**。
- 票 2 diff **無 label 語意變更**；V6 紅 = main 基線紅；redirect digest 守衛完好。
- **P-1 / P-2 / P-3 全數 STAMP APPROVED**。

```
ASSUMPTIONS_VERIFIED: HEAD@492c4cc worktree 重跑 deep+api3+V6三檔；git diff tests/api/ label 字面未變；nodeid 集合 vs /tmp/t2-v6-codex.log 全等；DIGEST_DIFF_EMPTY[V6]=1 見 grok/codex log；生產 resolver 只認 return_(\d+)
TESTS_RUN: worktree pytest deep → 3f7p4e；api3 → 3f8p2s16e；V6files → 3f9p20e RC=1；nodeid subset script SUBSET_OK=True
FAILURES_SEEN: none（預期紅重現，非驗證失敗）
SCOPE_CHANGES: none（只寫本檔）
NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_NOT_UPDATED: 派工限定只准寫本產出檔；根 HANDOFF.md 不動
```

STATUS: DONE
