# CXSTAMP 事後審 R2 — COMPOSER

task-id: `20260913-CXSTAMP-X-REVIEW-R2`  
family: COMPOSER  
findings-round: R2  
brief: `handoffs/20260913-CXSTAMP-X-REVIEW-R2-BRIEF.md`  
scope: current block `scripts/debt_clear.sh` 之 `_norm()`／路徑等式（`:501-504`）＋ `scripts/cx_run.sh:_maybe_register_stamp_output` 之 `_fmt_rc` 守衛（`:565-567`）；本輪 diff `git diff ede04741..HEAD -- scripts/cx_run.sh scripts/debt_clear.sh tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py`；禁改碼。

---

## §0 挑戰前提

| 前提 | brief 標籤 | composer 重判 | 碼證 |
|---|---|---|---|
| 修後 `test_debt_clear_stamp_unlock` 6 條＋`test_cxrun_stamp_format_gate` 5 條全綠 | fact-verified | **本輪重驗成立（11 passed）** | `venv/bin/python -m pytest tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -q` → **11 passed** rc=0 |
| `Path.resolve()` 正規化足以擋相對／`..`／絕對混寫；symlink 指向同檔視為同一份 | assumed | **成立（相對／絕對／`..`／symlink 皆 match；hardlink 為 fail-closed 更嚴）** | 見必答 2-A |
| `_fmt_rc` 動態作用域在 `_run_cli_and_emit` 之外無呼叫路徑，`${_fmt_rc:-0}` 不會誤擋 | assumed | **成立** | 見必答 2-B |

---

## 必答 1 — R1 反例閉合（composer 獨立重驗）

composer 非 X1／X2 原提出方；依 brief §B8，formal 閉合須 codex／grok 重跑同一反例。本家以修補後 pytest＋路徑探針獨立重驗：

| 群集 | R1 反例 | composer 重驗 | 閉合？ |
|---|---|---|---|
| **X1** 異路徑 `committee_output` 銷帳（CODEX-R1-P1-01／GROK-R1-P1-01） | 異路徑 register ⇒ `debt_clear` rc=0 | `test_stamp_round_reregister_of_other_path_does_not_unlock` PASSED（stamp-target 異路徑 ⇒ rc≠0、`sha 不符`）；同路徑重登 `test_stamp_round_edited_then_reregistered_unlocks` PASSED（rc=0） | **修法有效**（formal 閉合待 codex／grok 實跑 rc） |
| **X2** format-failed 仍留 stamp-target `committee_output`（CODEX-R1-P2-02） | hollow sentinel ⇒ `COMMITTEE_OUTPUT_COUNT=1` | `test_stamp_hollow_delivery_is_format_failed` PASSED（`result_state=format-failed`）；`test_stamp_register_guarded_by_format_rc` PASSED（守衛在 `reconcile_body_hash.sh` 之前） | **修法有效**（interaction 探針 1→0 待 codex 實跑） |

補跑：`venv/bin/python -m pytest tests/governance/test_debt_clear.py tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -q` → **41 passed** rc=0。

---

## 必答 2 — 兩條 assumed 攻擊

### 2-A — `debt_clear._norm()` 路徑正規化

探針 `scratchpad/cxstamp_r2_path_probe.py`（複製 `debt_clear.sh:501-503` 之 `_norm` 邏輯）：

| 向量 | `_norm(rr)==_norm(op)` | 安全意涵 |
|---|---|---|
| 同相對路徑 | True | 基線 |
| 絕對路徑 | True | 相對／絕對混寫不可繞 |
| `handoffs/../handoffs/st1-codex.md` | True | `..` 不可繞 |
| symlink → 同檔 | True | 合理：resolve 後為同一份 |
| hardlink → 同 inode | **False** | **fail-closed**（同內容不同路徑字串不會解鎖；非 bypass） |

**攻擊結論**：brief assumed「resolve 足以擋相對／`..`／絕對混寫」成立；symlink 同檔放行符合「同一份交件」語意；hardlink 更嚴、不構成漏洞。未見路徑正規化可繞過 X1 修法之新缺口。

### 2-B — `_fmt_rc` 動態作用域

| 檢查點 | 觀測 |
|---|---|
| 呼叫點 | `grep -n "_maybe_register_stamp_output" scripts/cx_run.sh` → 僅定義 `:551`、呼叫 `:883`（皆在 `_run_cli_and_emit` 內） |
| 賦值時序 | `:876` `_fmt_rc="$(_run_format_check_if_needed …)"` → `:877` emit → `:883` register；守衛讀同函式 `local _fmt_rc`（bash 動態作用域） |
| harness `preserve`／`preserve_append_stamp` | 仍走 `:876-883`；`test_stamp_hollow_delivery_is_format_failed`（preserve＋hollow）⇒ format-failed、不誤登記 |
| harness `success` | `test_stamp_stub_success_output_passes_own_gate` ⇒ `_fmt_rc=0` 時合法登記仍綠 |
| 未知 stub | `:825-830` 在 register 前 `exit`，不會帶未初始化 `_fmt_rc` 進 register |

**攻擊結論**：無第二呼叫路徑；`${_fmt_rc:-0}` 預設 0 僅在理論上脫離 caller 時生效，實際只有 `_run_cli_and_emit` 一條路。`preserve*` stub 不會誤擋合法登記、也不會漏擋 format-failed。假設成立。

---

## 必答 3 — 本輪 diff 新缺口審查

| 變更點 | 審查結論 |
|---|---|
| `debt_clear.sh:501-504` `_norm()`＋路徑等式 | 正確閉合 X1；新測 `test_stamp_round_reregister_of_other_path_does_not_unlock` 承重 |
| `cx_run.sh:565-567` `_fmt_rc` 守衛 | 正確閉合 X2；守衛位於 body_hash／register 之前；`test_stamp_register_guarded_by_format_rc` 承重 |
| 兩條新測 docstring mutation 意圖 | 與 synth X1／X2 處置對齊；未見表外機制或弱化 |

**殘留（非 BLOCKING）**：`cx_run.sh:882` 註解仍寫「stamp kind 不跑格式檢查」，與 `:740-747` 現行行為矛盾——純註解漂移，不影響機械行為；建議 impl 順手修正，本輪 review 不擋。

**未見本輪 diff 引入之新 BLOCKING 缺口。**

---

## §1 必查摘要

1. 矛盾：無（diff 與 r1 synth X1／X2 處置一致；註解 `:882` 為漂移非行為矛盾）  
2. 漏項：無（X1 六向＋X2 五條 stamp gate 測試覆蓋主要分支）  
3. 不可測：無（rc／`result_state`／pytest 可重跑）  
4–8. quant／OOM／cache／API：不適用  
9. 測試：11＋41 passed；mutation 意圖見各測 docstring  
10. Agent 可執行：是  
11. 短命工：無  

## 被當成事實的未驗證假設（§0）

brief 兩條 assumed 已上表攻擊並附探針／grep；無需另列 blocking finding。

---

## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——R1 修法（path 綁定＋`_fmt_rc` 守衛）機械有效、兩條 assumed 攻擊未發現 bypass、本輪 diff 未引入新缺口。

**碼證**: current block `debt_clear.sh:501-504`／`cx_run.sh:565-567`；`git diff ede04741..HEAD` 四檔；路徑探針 `venv/bin/python scratchpad/cxstamp_r2_path_probe.py` → same/abs/dotdot/symlink match=True、hardlink match=False（fail-closed）；`grep -n "_maybe_register_stamp_output" scripts/cx_run.sh` → 僅 `:551`＋`:883`；`venv/bin/python -m pytest tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -q` → 11 passed rc=0；`venv/bin/python -m pytest tests/governance/test_debt_clear.py tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -q` → 41 passed rc=0。

**來源摘要**: handoffs/20260913-CXSTAMP-X-REVIEW-R2-BRIEF.md#039a40938964;scripts/debt_clear.sh#8f796f5f801e;scripts/cx_run.sh#439095323491

[NON-BLOCKING] 信心度=High。建議待 codex／grok 正式重跑 X1／X2 反例 rc 後，三家零 BLOCKING 可進 stamp 輪結 CXSTAMP。

---

ASSUMPTIONS_VERIFIED: 路徑探針四向量 match、hardlink fail-closed；`_maybe_register_stamp_output` 單呼叫路徑；stamp 測 11 passed、debt 套件 41 passed。  
TESTS_RUN: `venv/bin/python scratchpad/cxstamp_r2_path_probe.py` → same/abs/dotdot/symlink True、hardlink False；`venv/bin/python -m pytest tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -q` → 11 passed rc=0；`venv/bin/python -m pytest tests/governance/test_debt_clear.py tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -q` → 41 passed rc=0。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼；scratchpad 探針僅讀）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:  
STATUS: DONE
