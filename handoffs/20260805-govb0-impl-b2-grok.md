# GOVB0-IMPL-B2 — grok 實作收尾

family: grok
task-id: GOVB0-IMPL-B2
brief: handoffs/20260805-GOVB0-IMPL-B2-BRIEF.md

## 正在做 / 完成

B0/B1 兩條 review finding 補修 + B2 Task 1.1 已完成。

## 改動檔

| 檔 | 說明 |
|---|---|
| `tests/governance/fixtures/gate_invariance_corpus.txt` | 語料 A 20→**28** JSON 列；補 Write artifact／token_expired／open_debt；`# @setup` 指令 |
| `tests/governance/test_gate_deny_fields.py` | setup harness；match_rule 覆蓋斷言；cmd 值相等＋truncation mutation；fresh-allow 單測 |
| `scripts/cx_run.sh` | `_prepare_and_run` 依 `${_bk}` 分支 prompt（stamp\|closure 保留＋格式說明；其餘不提；* fail-closed） |
| `tests/governance/test_cxrun_stamp_prompt.py` | **新** TEST-1.1-* 全套 |

未 commit、未 push。未碰 `data_cache/`、未改既有測試斷言、未做 B3+。

## 語料 A

- JSON 列數：**28**（原 20；+8）
- `@setup` 列：**4**（expired×2、fresh+open×2；含 artifact open）
- 出處：每條註解標 `gate_check.sh` 分支（Write:177-182、token:213、open_debt:201）
- **未納入** fresh+debt=none 放行：B0 snapshot 的 `SCRIPT_DIR=fixtures/` 找不到 debt core → recheck 一律 fail-closed，會弄紅 INVARIANCE。該路徑改由 `test_01_fresh_token_allow_when_no_open_debt` 覆蓋。
- match_rule 覆蓋：現行 `_gate_deny_match_info` 可發出集合 ⊆ `audit_events.json` enums.match_rule；語料 A 對**每一可發出值**至少一次（`unknown`／`family_cli`／`claude_agent`／`token_expired`／`open_debt`）。`outer_script`／`role_gate` 已登記但本檔尚未賦值（Phase 2 預留）。

## 值相等斷言（CODEX-R10-P2-02）

- `test_01_cmd_fields_value_equal_full_command`：`cmd_sha256 == sha256(完整 cmd)` 且 `cmd_head == 前 512 bytes`（cmd 長度 >512）
- mutation `test_01_cmd_sha256_mutation_truncated_turns_red`：**PASSED**（隔離副本對截斷串算 sha → 值相等轉紅）

## TEST-1.1 實跑

| ID | 結果 |
|---|---|
| CONSULT | PASSED（RECONCILE-STAMP count==0） |
| STAMP | PASSED（含格式說明） |
| UNKNOWN | PASSED（rc!=0） |
| UNKNOWN-NOSIDEEFFECT | PASSED（token 集合/mtime、audit 行數、has-open rc、handoffs 快照四項） |
| FORMAT-SSOT | PASSED（樣本同時過 prompt 說明與 cx_run 正則） |
| MUT 無條件注入 | PASSED（rc 語意＝CONSULT 轉紅） |
| MUT 移除 * 分支 | PASSED（rc 語意＝UNKNOWN+無副作用轉紅） |

## 全套測試

```
pytest tests/governance -q
→ 727 passed, 1 warning in 235.69s (0:03:55)  rc=0
```

基線 715 → **727**（+12，只增不減）。

```
bash scripts/restore_golden_inventory.sh
git status --short tests/golden/
→ （空）
```

## git diff --stat（本任務 scope）

```
 scripts/cx_run.sh                                  |  20 ++
 tests/governance/fixtures/gate_invariance_corpus.txt |  38 +++
 tests/governance/test_gate_deny_fields.py          | 261 ++++++++++++++++++++-
 tests/governance/test_cxrun_stamp_prompt.py        | 新檔（untracked）
```

## 踩坑

1. 語料 A 含 `@setup` 時，fresh+allow 不可與 snapshot 比——snapshot 相對路徑找不到 debt core。
2. `_PROMPT_WITH_INJECT` 字面必須保留在 `cx_run.sh`（既有 V1 mutation 錨點）；stamp 路徑先設完整句再 case 覆寫／附加。
3. cx_run `*` 分支在 `_prepare_and_run` 內、前置條件之後；測 defense-in-depth 須先開債並放寬 brief_conformance／role_gate。

## 待辦 / 阻塞

無。B3 以後未做。

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: _bk 仍為 brief_conformance --emit 第1行；_prepare_and_run 為 prompt 組裝點；match_rule enum 自 audit_events.json；可發出集合自 gate_check _gate_deny_match_info
TESTS_RUN: pytest tests/governance -q → 727 passed rc=0 (235.69s)；targeted 26 passed；stamp_inject 67 passed；mutations 4 passed
FAILURES_SEEN: 首輪 INVARIANCE 因 debt=none 與 snapshot SCRIPT_DIR 不一致 → 移出語料 A 改單測；unknown defense 未開債 → 補 open_round
SCOPE_CHANGES: none（僅 brief 指定檔＋新測試檔）
NUMERIC_OR_SCHEMA_IMPACT: none（僅治理 harness／audit 欄位斷言強化；產品數值未動）
```

STATUS: DONE
