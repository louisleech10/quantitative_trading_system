# GOVB0-B2 Code Review — COMPOSER

**受審 commit**：`4e8e61c`  
**reviewer 家族**：COMPOSER  
**task-id**：GOVB0-B2-REVIEW  
**產出時間**：2026-08-05

## Verdict

**可進 B3**（附 1 條 P1 非 BLOCKING finding）。B2 本體（Task 1.1 prompt 條件化、語料 A 擴充、cmd 值相等斷言）經獨立實跑可接受；B0 snapshot 結構性盲區已如實揭露，替代測試存在但**不等價**於 INVARIANCE，建議 B3 前或 Phase 2 一併修 snapshot 依賴。

FINDINGS_COUNT: 1

---

## §0 前提宣告

### brief 已查證（複核）

| 項目 | 複核命令 | 結果 |
|---|---|---|
| snapshot 置於 fixtures/ 時找不到 debt 依賴 | `snap_fresh_rc=2`：`GATE_DIR_OVERRIDE=… DEBT_AUDIT_OVERRIDE=… bash tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot` 輸入 `{"tool_name":"Task"}` + fresh token | rc=2；stderr 含 `debt_ledger 缺失（fail-closed）` |
| 現行腳本同情境可放行 | 同上 env 改跑 `bash scripts/gate_check.sh` | `current_fresh_rc=0` |
| 替代測試非空殼 | 讀 `test_gate_deny_fields.py:408-428` | 構造 token + 空 DEBT_AUDIT_OVERRIDE + harness env |

### brief 三條假設 — 攻擊結果

| 假設 | 攻擊 | 結論 |
|---|---|---|
| `727 passed` 為實作者轉述 | `source venv/bin/activate && pytest tests/governance -q` | **推翻假設 → 已驗**：`727 passed in 240.15s (0:04:00)`，rc=0 |
| 語料 A 28 條涵蓋現行可發出 `match_rule` | `pytest tests/governance/test_gate_deny_fields.py::test_01_corpus_a_covers_match_rule_closed_set -q` + 靜態擷取 `_gate_deny_match_info` | **確認**：emittable=`{claude_agent,family_cli,open_debt,token_expired,unknown}`，observed 覆蓋全集合；1 passed |
| 替代測試與「進語料 A 比對快照」等價 | 比對 INVARIANCE 契約（只比 snapshot vs 現行 decision trace）vs `test_01_fresh_token_allow_when_no_open_debt`（只驗現行） | **推翻 → 不等價**（見下 § 四題 Q2） |

---

### 四題首要攻擊標的

#### Q1：還有哪些分支受同一盲區影響？

`gate_check.sh` 中 **唯一** 使用 `${SCRIPT_DIR}` 的區塊是 `_gate_check_recheck_debt`（`:122-146`），僅在 **fresh token 且未過 TTL** 時呼叫（`:196-199`）。依賴路徑逐條：

| # | `${SCRIPT_DIR}` 路徑 | 用途 | 受盲區？ |
|---|---|---|---|
| 1 | `_debt_ledger_core.py` | 優先 debt 重查 | 是 |
| 2 | `debt_ledger.sh` | core 缺失時回退 | 是 |
| 3 | `audit_events.json` | core 的 `DEBT_LEDGER_REGISTRY` | 是（隨 #1） |
| 4 | `${SCRIPT_DIR}/..` | 推 repo root | 是（隨 #1） |

**受影響判定分支**（僅兩條，皆在 fresh-token 區段）：

| 分支 | snapshot 行為（fixtures/） | 現行行為（scripts/ + harness） | 語料 A | 替代測試 |
|---|---|---|---|---|
| A. recheck 通過 → **exit 0 放行** | fail-closed → rc=2 | rc=0（DEBT_AUDIT_OVERRIDE 空日誌） | **刻意排除**（corpus :52-54 註解） | `test_01_fresh_token_allow_when_no_open_debt` |
| B. recheck 失敗 → **open_debt deny** rc=2 | fail-closed → rc=2（未讀 DEBT_AUDIT_OVERRIDE） | rc=2（真 OPEN 債） | 有（`:55-59` `@setup debt=open`） | 無專測；INVARIANCE **碰巧同 rc** |

**窮舉結論**：盲區僅覆蓋 `_gate_check_recheck_debt` 全部分支；非 debt 路徑（no token／expired／Write／非 executor Bash 等）**不受** snapshot SCRIPT_DIR 影響。分支 B 雖 INVARIANCE 綠燈，但 snapshot 側從未執行真債務語意，屬**弱保護**。

#### Q2：替代測試是否等價？

**判定：不等價。**

| 維度 | 語料 A + INVARIANCE | `test_01_fresh_token_allow_when_no_open_debt` |
|---|---|---|
| 比較對象 | snapshot（Phase 0）vs 現行 `scripts/gate_check.sh` | 僅現行腳本 |
| 通過語意 | 改前改後 `(rc, kind)` 序列相等 | 現行 fresh+無債 → rc=0 |
| 漏掉 | 無法偵測「現行仍放行但 snapshot 行為已漂移且未納入語料」的組合 | 不驗證 Phase 0 不變式；不驗證 open_debt 路徑真債務邏輯 |

#### Q3：B0 修法建議

| 方案 | 作法 | 代價 |
|---|---|---|
| **(Recommended) 依賴 bundle** | 在 `fixtures/` 同目錄放入 snapshot 期 `_debt_ledger_core.py`、`debt_ledger.sh`、`audit_events.json`（或 symlink 至 scripts/ 只讀副本） | fixture 維護成本；須釘 snapshot sha |
| git show 動態取 | 測試 harness 用 `git show <phase0-sha>:scripts/_debt_ledger_core.py` 寫 temp | 需 git 依賴；CI shallow clone 風險 |
| 改 INVARIANCE 執行 cwd | snapshot 仍放 fixtures/ 但 `bash` 時 `cwd=scripts/` 且 env 覆寫 `BASH_SOURCE` — **不可行**（BASH_SOURCE 綁實際路徑） | 不可靠 |
| 維持現狀 + 替代測試 | 已採用 | INVARIANCE 對 fresh-token 全分支保護不完整（見 finding） |

#### Q4：主委「不構成調整語料使其變綠」是否正確？

**同意。** brief 禁令針對「B1 真的改了某分支判定卻改語料抹平 diff」。本例 diff 根因是 snapshot **只複製 gate_check.sh、未帶同目錄依賴**，屬執行環境假象；實作者明示排除並加註解，非靜默刪 case。但同意**不等於**盲區已解——仍應修 B0 或升級測試契約。

---

## 逐項核對表

| # | 查什麼 | 判定 | 依據（實跑命令＋結果） |
|---|---|---|---|
| 1 | 語料 A 28 條是否每條都有真實出處 | **PASS** | `grep -c '^{' tests/governance/fixtures/gate_invariance_corpus.txt` → 28；逐條對照 corpus :8-18 索引與 `gate_check.sh` 行號（Read/:186、Task/:157-158、Bash executor/:170-174、Write/:177-182、token/:190-213、open_debt/:201）均可追溯 |
| 2 | `match_rule` 覆蓋宣稱 | **PASS** | `pytest …::test_01_corpus_a_covers_match_rule_closed_set -q` → 1 passed；emittable 5 值 ⊆ enum 7 值，missing=∅ |
| 3 | 值相等斷言驗完整 cmd 非截斷 | **PASS** | `pytest …::test_01_cmd_fields_value_equal_full_command -q` → 1 passed；600+ 字元 cmd + `assert event["cmd_sha256"] != truncated_sha` |
| 4 | TEST-1.1-UNKNOWN-NOSIDEEFFECT 四項逐項 | **PASS** | `pytest tests/governance/test_cxrun_stamp_prompt.py::test_11_unknown_nosideeffect -q` → 1 passed；`:324-338` 分別 assert token mtime／audit 行數／debt rc／handoffs 集合 |
| 5 | prompt 格式 vs `cx_run.sh:345` 正則機械一致 | **PASS** | `pytest …::test_11_format_ssot -q` → 1 passed；樣本 `RECONCILE-STAMP: codex APPROVED … sha256:… task:…` 經 `_extract_stamp_regex_from_cx` 轉 py re 後 `re.search` 命中 |
| 6 | 新測試廉價綠燈（§1-9） | **PASS（附註）** | 關鍵路徑有 mutation（`test_01_cmd_sha256_mutation_*`、`test_11_mut_*`）；NOSIDEEFFECT 四項非僅 rc。**附註**：open_debt 語料 INVARIANCE 靠 snapshot fail-closed 巧合同 rc，屬弱保護（併入 finding） |
| 7 | 既有測試斷言被改動 | **PASS** | `git diff 4e8e61c^ 4e8e61c -- tests/` 中 **零** `-    assert` 刪除行；變更為新增檔 `test_cxrun_stamp_prompt.py` + `test_gate_deny_fields.py` 擴充 helper／新 case，未弱化舊斷言 |

---

## COMPOSER-R11-P1-01

**斷言**: B0 snapshot 僅複製 `gate_check.sh`、未 bundle `_gate_check_recheck_debt` 依賴，導致 fresh-token 路徑無法做 snapshot↔現行 INVARIANCE；open_debt 語料僅因 snapshot fail-closed 巧合同 rc=2 而綠燈，未驗證真債務重查語意。

**碼證**: `tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot:39-62` 仍呼叫 `${SCRIPT_DIR}/_debt_ledger_core.py`；fixtures/ 無該檔。RECHECK: (1) fresh+空債：snapshot rc=2 vs 現行 rc=0（上文 §0 命令）；(2) `pytest tests/governance/test_gate_deny_fields.py::test_01_invariance_decision_trace -q` → pass 但 corpus 缺 fresh+none 放行 case（corpus :52-54）。

**來源摘要**: tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot#4e8e61c158cb

**[MAJOR] 信心度=High。** INVARIANCE 對 `_gate_check_recheck_debt` 的保護名存實亡：放行路徑靠非等價單測；deny 路徑靠 fail-closed 撞 rc。回歸若改壞 recheck 邏輯但維持 rc=2，INVARIANCE 不會紅。

**修法**（可執行）：
1. 將 `_debt_ledger_core.py`、`debt_ledger.sh`、`audit_events.json` 一併納入 B0 fixture（或 git-show 動態 materialize）。
2. 恢復語料 A `@setup token=*:fresh debt=none` 放行 case，確認 INVARIANCE diff 仍空。
3. 保留 `test_01_fresh_token_allow_when_no_open_debt` 作 harness 回歸，但不宣稱替代 INVARIANCE。

**重現**：`GATE_DIR_OVERRIDE=/tmp/g GOVERNANCE_TEST_HARNESS=1 DEBT_AUDIT_OVERRIDE=/tmp/empty.log bash tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot` 輸入 `{"tool_name":"Task"}` + fresh `dispatch.token` → rc=2（應為 0 才與現行一致）。

---

## 出場判準核算

| 項目 | 值 |
|---|---|
| findings 總數 | 1 |
| BLOCKING (P0) | 0 |
| MAJOR (P1) | 1 |
| MINOR (P2) | 0 |
| 門檻 `findings ≤5 且 BLOCKING=0` | **滿足 → B2 驗收通過，可進 B3** |
| 建議 B3 前修補 | COMPOSER-R11-P1-01（B0 fixture bundle） |

---

## 收尾

**TESTS_RUN**:
- `pytest tests/governance -q` → 727 passed in 240.15s, rc=0
- `pytest tests/governance/test_gate_deny_fields.py::test_01_invariance_decision_trace tests/governance/test_gate_deny_fields.py::test_01_corpus_a_covers_match_rule_closed_set tests/governance/test_gate_deny_fields.py::test_01_fresh_token_allow_when_no_open_debt tests/governance/test_gate_deny_fields.py::test_01_cmd_fields_value_equal_full_command -q` → 4 passed, rc=0
- `pytest tests/governance/test_cxrun_stamp_prompt.py -q` → 8 passed, rc=0

**ASSUMPTIONS_VERIFIED**: 727 passed（非轉述）；match_rule 覆蓋（test pass）；snapshot fail-closed vs 現行放行（shell 實跑）

**FAILURES_SEEN**: none

**SCOPE_CHANGES**: none（review-only）

**NUMERIC_OR_SCHEMA_IMPACT**: none

**產出檔**: `handoffs/20260805-govb0-b2-review-composer.md`

**HANDOFF_NOT_UPDATED**: 執行端不得改寫根 HANDOFF.md（合約）

**register-output**: `bash scripts/gate.sh register-output GOVB0-B2-REVIEW handoffs/20260805-govb0-b2-review-composer.md` → rc=1（本環境 gate token 未開；需主委代登記）

STATUS: DONE
