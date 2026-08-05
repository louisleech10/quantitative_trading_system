# GOVB0-FIX-ORACLE — grok

**task-id**: GOVB0-FIX-ORACLE  
**family**: grok  
**brief**: `handoffs/20260805-GOVB0-FIX-ORACLE-BRIEF.md`  
**時間**: 2026-08-05

## 修法選擇（修 1）

選 **(a) 目錄 bundle**：`tests/governance/fixtures/gate_check_pre_phase2/`

| 檔 | sha256（sidecar 一致） |
|---|---|
| `gate_check.sh` | `871258c9ea2e6817b0110e7efedcca6847ba196e9ffb3f7151f57adabe01606a` |
| `_debt_ledger_core.py` | `8a19936872ff4b1f03b13dc3038301d5c19826ce2df1850f8eaf3c5206528d99` |
| `debt_ledger.sh` | `d052d6602939300bc135cf22673b7bc86993d33b5b81806c1add0ffe1550b669` |
| `audit_events.json`（pre-Phase2） | `91c19ab09e5e91a620c59d79b4e2bb1cbfee7d00e78e6696d93302cd231e53eb` |

**理由**：  
1. SCRIPT_DIR 與依賴同目錄 → `_gate_check_recheck_debt` 可載入 core；fresh+no-debt 真正放行。  
2. 各檔獨立 `.sha256`，B5 防作弊不弱化。  
3. `audit_events.json` 釘 pre-Phase2（HEAD 已變），避免舊 gate 配新 registry。  
4. 舊路徑 `gate_check_pre_phase2.sh.snapshot` **保留**且 byte-identical（B5/TODO 路徑相容）。

**pre-Phase2 證明**：  
`shasum -a 256` of snapshot `gate_check.sh` **==** `git show $(git rev-parse '596fcb4^'):scripts/gate_check.sh` **==** `871258c9…1606a`（sidecar 同值）。  
實跑：`test_01_snapshot_bundle_integrity` PASSED。

## 分支 → 行號 → 語料 A（修 2 核心）

行號 = 現行 `scripts/gate_check.sh`（主判定段 `INPUT="$(cat)"` 之後機械導出）。  
語料條目 # = `_load_corpus_entries` 1-based 序。

| 分支 | gate_check.sh 行號 | 語料 A 條目(#) |
|---|---|---|
| `deny_task_no_token` | 156 | 5 |
| `deny_env_strip_family` | 163 | 12 |
| `allow_filename_fp` | 166 | 18 |
| `deny_bash_family_cli` | 171 | 6,7,8,9 |
| `deny_bash_claude_agent` | 171 | 10,11 |
| `deny_sep_family` | 171 | 13,14 |
| `allow_gate_self` | 173 | 15,16 |
| `deny_write_artifact` | 181 | 21,23,24 |
| `allow_write_existing` | 181 | 22 |
| `allow_nongated` | 186 | 1,2,3,4,17,19,20 |
| `allow_fresh_no_debt` | 198 | **26,27（本輪新納）** |
| `deny_open_debt` | 201 | 28,29 |
| `deny_token_expired` | 213 | 25,30 |

- 語料 A 條數：`grep -c '^{' …` → **30**（原 28 + fresh dispatch/artifact 各 1）  
- 覆蓋斷言：`test_01_corpus_a_covers_decision_branches`（自 gate_check 結構導出，禁硬編）+ 既有 match_rule 封閉集合  
- **INVARIANCE 未轉紅**（`test_01_invariance_decision_trace` PASSED）→ B1/B2 未改判定  
- **已知缺口（具名）**：無 jq／parse fail-open 路徑未進語料 A（需拔 jq 的環境；非 (rc,kind) 判定主路徑、與 Phase 0 無關）。`outer_script`／`role_gate` 已登記於 `audit_events.json` 但 `_gate_deny_match_info` 尚未賦值（Phase 2 契約預留）——既有 test 明文不要求語料 A 觸發。

## Mutation 實跑 rc

| mutation | 命令 | 結果 |
|---|---|---|
| 修 1：抽掉 snapshot debt 依賴 | `pytest …::test_01_mut_snapshot_missing_debt_dep_turns_fresh_allow_red -q` | **PASSED**（mut 後 fresh+no-debt 不再 rc=0） |
| 修 3：closure 自注入分支移除 | `pytest …::test_11_mut_remove_closure_from_inject_turns_red -q` | **PASSED** |
| 修 3：格式說明改壞 | `pytest …::test_11_mut_format_desc_incompatible_with_regex_turns_red -q` | **PASSED** |
| 三 mut 聯跑 | 同上三 nodeid | **3 passed**, rc=0, 1.15s |

## 測試與 golden

```
pytest tests/governance -q
# → 734 passed, 1 warning in 234.31s (0:03:54), rc=0
# 前基線 727；本輪 +7（bundle integrity / fresh allow / mut dep /
#   decision-branch coverage / closure 正向 / mut closure / mut format）
```

```
bash scripts/restore_golden_inventory.sh
git status --short tests/golden/
# → （空）
```

## git diff --stat

```
 tests/governance/fixtures/gate_invariance_corpus.txt |  72 +++++--
 tests/governance/test_cxrun_stamp_prompt.py          | 232 ++++++++++++++++++---
 tests/governance/test_gate_deny_fields.py            | 229 +++++++++++++++++++-
 3 files changed (intentional) + untracked fixtures/gate_check_pre_phase2/
```

（`.claude/gate/audit.log` 為本機 gate 副作用，**非本輪產出**。）

**新增 untracked**：`tests/governance/fixtures/gate_check_pre_phase2/`（4 檔 + 4 sidecar）

## /tmp

已清本輪 probe/smoke/log workdir；**保留** `/private/tmp/claude-501`。

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: gate_check 判定分支可由靜態結構窮舉（主判定段）；snapshot 目錄 bundle 後 fresh+no-debt rc=0（實跑）；pre-Phase2 gate_check sha=871258c9…1606a
TESTS_RUN: pytest tests/governance -q → 734 passed rc=0；三 mut 聯跑 3 passed rc=0；restore_golden 後 git status --short tests/golden/ 空
FAILURES_SEEN: none
SCOPE_CHANGES: none（未碰 B3+；未改 gate_check.sh / cx_run.sh 行為；僅 fixtures + 測試）
NUMERIC_OR_SCHEMA_IMPACT: none（判定 (rc,kind) 不變；audit schema 未改）
```

**產出檔**: `handoffs/20260805-govb0-fix-oracle-grok.md`

**HANDOFF_NOT_UPDATED**: 執行端不得改寫根 `HANDOFF.md`

STATUS: DONE
