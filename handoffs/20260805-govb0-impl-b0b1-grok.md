# GOVB0-IMPL-B0B1 | family: grok | brief-kind: impl

**task-id**: `GOVB0-IMPL-B0B1`（使用者指定；未採用 brief 內任何範例 task-id）  
**時間**: 2026-08-05T06:15:15Z  
**範圍**: 只做 B0 + B1（Task 0.1）；B2 以後未碰  
**未 commit / 未 push**（brief 禁令）

---

## 改了哪些檔（`git diff --stat HEAD`，本批 scope）

```
 scripts/audit_events.json                          |  47 ++-
 scripts/gate_check.sh                              | 101 +++++-
 .../fixtures/gate_check_pre_phase2.sh.snapshot     | 137 ++++++++
 .../gate_check_pre_phase2.sh.snapshot.sha256       |   1 +
 tests/governance/fixtures/gate_decision_corpus.txt |   4 +
 .../governance/fixtures/gate_invariance_corpus.txt |  24 ++
 tests/governance/test_gate_deny_fields.py          | 356 +++++++++++++++++++++
 7 files changed, 657 insertions(+), 13 deletions(-)
```

（工作樹另有 pre-existing 非本批：`.claude/gate/audit.log` M、若干 handoffs 白話檔 D——未納入本批 scope。）

---

## B0 — pre-Phase2 snapshot

產出（已 `git add`，未 commit）：

| 檔 | 說明 |
|---|---|
| `tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot` | 動工前 `gate_check.sh` 逐位元組副本 |
| `tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot.sha256` | 上檔 sha256 單行 |

**實跑**：

```
$ sha256sum tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot
871258c9ea2e6817b0110e7efedcca6847ba196e9ffb3f7151f57adabe01606a  tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot

$ cat tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot.sha256
871258c9ea2e6817b0110e7efedcca6847ba196e9ffb3f7151f57adabe01606a

$ # sidecar 實算比對
SIDECAR_MATCH

$ git ls-files --error-unmatch tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot
# rc=0
$ git ls-files --error-unmatch tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot.sha256
# rc=0
```

快照在改 `gate_check.sh` **之前**建立 → Task 2.5 / Phase 0 invariance 的 oracle 不含 B1 新欄位寫入。

---

## B1 — Task 0.1 實作摘要

### `scripts/gate_check.sh`
- 新增 `_gate_deny_cmd_fields`（sha256 + head512）
- 新增 `_gate_deny_match_info`（**僅 deny 路徑** `grep -Eo` 取片段；結果不回饋判定）
- `_append_gate_deny_audit` 擴參：reason/tool/kind + cmd + match_rule；以 `jq -nc` 寫合法 JSON
- 判定段（原 `:86` 熱路徑）仍只 `grep -Eq`，**無**新增 log、無 `grep -Eo`
- 兩處 caller 同步改簽名
- 邊界：缺 command → 空字串欄位；單行 >1KB 時清空 cmd_head 重組

### `scripts/audit_events.json`
- `enums.match_rule` ← `family_cli|claude_agent|outer_script|token_expired|open_debt|role_gate|unknown`
- `required_fields_per_event.gate_deny` ← 見下「決策」
- `event_object_allowed_keys` 由 array 改 map：保留 `_debt_event_definition` 舊白名單 + `gate_deny` 欄位表

### 語料
- **語料 A** `gate_invariance_corpus.txt`（20 條 JSONL）  
  sha256=`1ae51fc7a44553551fb2a03d638a600a4ef0735591151546e5275326ceb5e876`
- **語料 B** `gate_decision_corpus.txt`（Task 2.0 占位，使 CORPUS-DISTINCT 可驗）  
  sha256=`57434c991807c131a215341e7d15198685f921966411dc154a04d50dbcc8de01`  
  （≠ A；完整 22+ 契約語料由 Task 2.0 覆寫）

### 測試 `tests/governance/test_gate_deny_fields.py`（14 條）
| Test ID | 函式 | 結果 |
|---|---|---|
| TEST-0.1-RC-BLOCK | `test_01_rc_block_*` | PASS |
| TEST-0.1-RC-ALLOW | `test_01_rc_allow_*` | PASS |
| TEST-0.1-INVARIANCE | `test_01_invariance_decision_trace` | PASS（snapshot vs 現行 (rc,kind) diff 行數 0） |
| TEST-0.1-FIELDS | `test_01_fields_match_registry` | PASS |
| TEST-0.1-ENUM | `test_01_enum_*` | PASS |
| TEST-0.1-CORPUS-DISTINCT | `test_01_corpus_distinct_and_tracked` | PASS |
| 邊界①②③ | `test_01_boundary_*` | PASS |
| TEST-0.1-MUT | `test_01_mut_remove_new_fields_turns_fields_red` | PASS（mut 後 FIELDS 集合不等） |

---

## 決策（相對 Frozen TODO 的必要對齊，未改 TODO 正文）

1. **`required_fields_per_event.gate_deny` 含既有 `tool`/`kind`**  
   TODO 列 `["event","ts","reason","match_rule","cmd_sha256","cmd_head"]`，但 `tests/governance/test_gate_deny_audit.py` 基線斷言 `tool`/`kind` 必在。  
   禁改既有斷言 + 基線不得轉紅 ⇒ **保留寫入 tool/kind，並將二者納入 required_fields / allowed_keys**。  
   新欄位仍是 match_rule/cmd_sha256/cmd_head。

2. **`event_object_allowed_keys` 結構**  
   原為 debt 定義欄位 array；TODO 要求 `.gate_deny` 鍵。  
   改為 map：`_debt_event_definition`（舊 list）+ `gate_deny`（事件欄位）。  
   全套治理測試 0 紅。

3. **語料 B 占位**  
   TODO 寫 Phase 2 才建完整語料 B，但 TEST-0.1-CORPUS-DISTINCT 要求兩檔皆追蹤且 sha 不同。  
   本批放最小占位檔，**Task 2.0 可覆寫**。

---

## 驗收實跑

### 新測 + 既有 deny 基線
```
pytest tests/governance/test_gate_deny_fields.py tests/governance/test_gate_deny_audit.py -v
# 19 passed in 4.03s
```

### Mutation（TEST-0.1-MUT）
```
pytest tests/governance/test_gate_deny_fields.py::test_01_mut_remove_new_fields_turns_fields_red -v
# 1 passed in 0.10s
# mut_rc=0  （測的是「移除新欄位寫入後 FIELDS 集合不再相等」——真紅被本 mutation 測試捕獲）
```

### 全套治理（下限 701）
```
python3 -m pytest tests/governance -q --tb=line
# ================== 715 passed, 1 warning in 224.47s (0:03:44) ==================
# full_rc=0
# 701 baseline + 14 new = 715；既有無轉紅
```

### golden
```
bash scripts/restore_golden_inventory.sh   # restore_rc=0
git status --short tests/golden/
# （空）
```

### 前提複驗
- `TODO-STATUS: INTERNAL-FROZEN` count=1；`template_check.sh todo` → TEMPLATE PASS rc=0
- `_append_gate_deny_audit` 原 `:21`；判定段原 `:87`；caller 原 `:117`/`:128`（動工前 grep 複驗；動工後行號已位移）
- `audit_events.json` 原有 `required_fields_per_event` / `event_object_allowed_keys`；`unknown_event_policy` 僅在 `docs.*` 字串（brief assumed 頂層 key 不成立 → 未捏造頂層 key；match_rule 未知走 enum 值 `unknown`）

---

## 清 /tmp
- 已刪本批 `/tmp/govb0_*` log
- **保留** `/private/tmp/claude-501`
- 未碰 `data_cache/`

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - TODO INTERNAL-FROZEN + template_check todo PASS
  - gate_check deny 兩 caller + 判定段在改前存在；grep -Eo 只在 deny 後路徑
  - 既有 test_gate_deny_audit 依賴 tool/kind → required_fields 必須含二者
  - B0 snapshot sha == sidecar；byte-identical to 改前 gate_check.sh
  - 語料 A/B sha 不同且 git ls-files 可解析（已 git add）

TESTS_RUN:
  - pytest tests/governance/test_gate_deny_fields.py + test_gate_deny_audit.py → 19 passed
  - pytest …::test_01_mut_remove_new_fields_turns_fields_red → 1 passed (mut_rc=0)
  - pytest tests/governance -q → 715 passed in 224.47s (full_rc=0)
  - restore_golden_inventory.sh → git status --short tests/golden/ 空

FAILURES_SEEN: none

SCOPE_CHANGES:
  - required_fields/allowed_keys 含 tool+kind（基線相容，見上決策 1）
  - 語料 B 占位（見決策 3）
  - event_object_allowed_keys 改 map（見決策 2）
  - 無 B2+ 改動

NUMERIC_OR_SCHEMA_IMPACT:
  - gate_deny audit 事件新增 match_rule/cmd_sha256/cmd_head（及保留 tool/kind）
  - audit_events.json schema 擴充；判定 (rc,kind) 不變（INVARIANCE 已證）
  - 無 data_cache / 無數值引擎改動
```

STATUS: DONE
