## Verdict
GOVB0-B2-REVIEW / family=codex / commit=4e8e61c / output=handoffs/20260805-govb0-b2-review-codex.md：B2 驗收通過；findings=2，BLOCKING=0（≤5）。
## §0 前提宣告
fact-verified：全套 727 passed；assumed「727 passed」已驗證（本次 264.28s，非實作者 handoff 的 235.69s）；assumed「語料 A 28 條涵蓋現行 match_rule」已驗證；assumed「替代 fresh/no-debt 測試等價於 snapshot 比對」不成立。
Q1：`gate_check.sh` 的 `${SCRIPT_DIR}` 依賴是 `_debt_ledger_core.py`、`debt_ledger.sh`、`audit_events.json`，並把 `${SCRIPT_DIR}/..` 當 repo；fresh token 的 `dispatch`／`artifact` 兩類都會走此重查，no-token／expired 不走。外部工具為 bash/python3/jq/grep/sed/date/stat/head/awk/sha256sum 等。
Q2：不等價；替代測試只跑現行 `scripts/gate_check.sh` 並用 `DEBT_AUDIT_OVERRIDE`，沒有跑 pre-Phase2 snapshot，故不驗改前改後一致。
Q3：修法是把上述依賴與正確 repo-root/audit fixture 一起以同一舊版 SHA 執行，或由 `git show <sha>:path` 動態取出整套依賴後在隔離 root 執行；代價是 fixture/runner 較大且需避免第二份 SoT，但可恢復 oracle。Q4：同意狹義判定：差異由 snapshot 執行缺依賴造成，非 B1 改變判定；但應修 snapshot 後把 fresh/no-debt case 放回，不能以現行單測代替。
## 逐項核對表
| # | 查什麼 | 判定 | 依據（實跑命令＋結果） |
|---|---|---|---|
| 1 | 語料 A 28 條有出處 | PASS | `grep -c '^{' tests/governance/fixtures/gate_invariance_corpus.txt` → `28`；逐條對照 gate 分支註解。 |
| 2 | 現行可發出 `match_rule` 全覆蓋 | PASS | `pytest -q ...::test_01_corpus_a_covers_match_rule_closed_set`（併入定向命令）→ `PASSED`。 |
| 3 | 完整 command 的 sha/head 值相等 | PASS | `pytest -q ...::test_01_cmd_fields_value_equal_full_command`（併入定向命令）→ `PASSED`。 |
| 4 | UNKNOWN-NOSIDEEFFECT 四項逐項驗證 | PASS | `pytest -q ...::test_11_unknown_nosideeffect`（併入定向命令）→ `PASSED`。 |
| 5 | prompt 說明與 `cx_run.sh:345` 機械一致 | PARTIAL | `test_11_format_ssot` → `PASSED`，但 prompt 只做字串存在檢查，sample 是測試自行建立，未解析 prompt grammar。 |
| 6 | 新測試無廉價綠燈 | FAIL | `rg` 找不到 `def test_.*closure`／`brief-kind: closure` 正向案例；`stamp|closure` 分支可刪而新增套件仍可能全綠。 |
| 7 | 既有 tests assertion 未被改動 | PASS | `git diff 4e8e61c^ 4e8e61c -- tests/` 的刪除僅為 loader/trace helper，無既有 assertion 刪除。 |
## CODEX-R11-P1-01
**斷言**：B0 snapshot 在 fresh token 重查分支無法載入同目錄依賴，故 invariance oracle 對 fresh/no-debt 失效。
**碼證**：snapshot:19,41-56；現行 `scripts/gate_check.sh:122-141`；重現：同一 fresh `dispatch.token`＋空 audit，snapshot `rc=2 ERROR: debt_ledger 缺失`、現行 `rc=0`；修法後重跑 `pytest -q tests/governance/test_gate_deny_fields.py::test_01_invariance_decision_trace`。
**來源摘要**：`tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot#871258c9ea2e`；`tests/governance/test_gate_deny_fields.py#a8a919af9518`
[MAJOR, non-blocking, confidence=10] `test_01_fresh_token_allow_when_no_open_debt`（:408-428）只驗現行程式，不能證明改前改後；修復 snapshot 的依賴閉包與隔離 repo-root 後恢復該 corpus case，並保留替代單測作路徑測試。
## CODEX-R11-P1-02
**斷言**：B2 新測試未對 `closure` 正向分支及 prompt 格式說明與實際 regex 建立可 mutation 證偽的綁定，存在廉價綠燈。
**碼證**：`scripts/cx_run.sh:520-526` 含 `stamp|closure`；測試只有 stamp E2E（:253-285），`:424-455` 只檢查 prompt 子字串並用獨立 sample 驗 regex；重現：`rg -n 'def test_.*closure|brief-kind: closure' tests/governance/test_cxrun_stamp_prompt.py` → `no closure positive test case`。
**來源摘要**：`tests/governance/test_cxrun_stamp_prompt.py#c0b82c025d96`；`scripts/cx_run.sh#b2dff2cf8c0a`
[MAJOR, non-blocking, confidence=10] 加 closure prompt capture/格式斷言及對應 mutation；把一個實際渲染 sample 同時交給 prompt schema 與 `:345` regex，且兩種欄位順序各自可證偽。
## 出場判準核算
FINDINGS_COUNT: 2；BLOCKING: 0；ASSUMPTIONS_VERIFIED: stamps 3/3 APPROVED、target commit、28 rows、match_rule coverage、727 tests；TESTS_RUN: `pytest -q tests/governance/test_cxrun_stamp_prompt.py tests/governance/test_gate_deny_fields.py` → 26 passed；`pytest tests/governance -q` → 727 passed in 264.28s；`restore_golden_inventory.sh` → rc=128（index.lock sandbox error），`git status --short tests/golden/` 空；FAILURES_SEEN: snapshot fresh/no-debt rc mismatch；restore script sandbox failure；SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: none；HANDOFF_UPDATED: this file。
STATUS: DONE
