# CXSTAMP X-REVIEW R2 — grok

task-id: 20260913-CXSTAMP-X-REVIEW-R2  
family: GROK  
findings-round: R2  
brief: `handoffs/20260913-CXSTAMP-X-REVIEW-R2-BRIEF.md`  
scope: current block＝`debt_clear.sh` `_norm` 路徑等式；`cx_run.sh:_maybe_register_stamp_output` `_fmt_rc` 守衛；本輪 diff `ede04741..HEAD` 四檔。禁改碼。原提出方閉合 `GROK-R1-P1-01`。

---

## §0 挑戰前提

| 前提 | brief 標籤 | grok 重判 | 碼證 |
|---|---|---|---|
| 修後 stamp unlock 6／format gate 5／debt_clear 30 等綠 | fact-verified | **成立** | `venv/bin/python -m pytest tests/governance/test_debt_clear.py tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -q` → **41 passed** rc=0 |
| `Path.resolve()` 擋相對／`..`／絕對混寫；symlink 同檔視為同一份 | assumed | **成立（攻不破）** | 隔離探針 A–H 全 PASS（見必答 2） |
| `_fmt_rc` 只在 `_run_cli_and_emit` 呼叫路徑存在；`${_fmt_rc:-0}` 不誤擋 | assumed | **成立** | `grep` 呼叫點僅 L883；L778 `local _fmt_rc=0`＋L876 賦值後才 register；`preserve`／`preserve_append_stamp` 亦落到同一 footer |

## 被當成事實的未驗證假設（§0）

無新增。兩條 assumed 經實跑／靜態呼叫圖攻擊後均成立。具名殘留（不另開 finding、doc-literal-only）：`cx_run.sh` L882 註解仍寫「stamp kind 不跑格式檢查」——與 L562–568／L733+ 行為漂移，不影響本輪閉合。

---

## 必答 1 — 反例重跑 rc（閉合／未閉合）

| 構造 | R1 觀測 | R2 實跑 | 結論 |
|---|---|---|---|
| 竄改交件＋異路徑 `handoffs/unrelated.md` register | rc=0（漏洞） | **rc=1**，stderr 含 `sha 不符` | **已閉合** |
| 竄改交件＋stamp-target 風格異路徑 register | rc=0（漏洞） | **rc=1**，`sha 不符` | **已閉合** |
| 竄改交件＋**同路徑**重登（sha 相符） | rc=0（合法） | **rc=0**，stdout 含「其後已顯式 register-output」 | 合法路徑仍通 |
| pytest `test_stamp_round_reregister_of_other_path_does_not_unlock` | （R1 無此條） | **PASSED** | 反例已常駐 |

VERIFY 摘要：隔離 harness 寫於 `/tmp/cxstamp_r2_*`；結果彙整 `/tmp/cxstamp_r2_probe/results.json`（A/B/H rc≠0；C rc=0）。`GROK-R1-P1-01` → **CLOSED**。

---

## 必答 2 — 兩條 assumed 攻擊結果

### assumed-1：`Path.resolve()` 正規化

| 探針 | 構造 | rc | 期望 |
|---|---|---|---|
| A | `unrelated.md` 異路徑 | 1 | ≠0 |
| B | `*-stamp-target.md` 異路徑 | 1 | ≠0 |
| C | 同相對路徑重登 | 0 | =0 |
| D | **絕對路徑**指向同一交件 | 0 | =0（resolve 相等） |
| E | `handoffs/../handoffs/<fam>.md` | 0 | =0 |
| F | symlink → **同一**交件 | 0 | =0（brief：合理） |
| G | symlink → **不同**檔 | 1 | ≠0 |
| H | 絕對路徑指向 unrelated | 1 | ≠0 |

**結果：8/8 PASS；無法用相對／絕對／`..`／symlink 把異檔裝成同檔解鎖。** assumed **成立**。

### assumed-2：`_fmt_rc` 動態作用域

- `grep -n "_maybe_register_stamp_output" scripts/cx_run.sh` → 定義 L551、**唯一呼叫 L883**（皆在 `_run_cli_and_emit`）。
- `preserve`／`preserve_append_stamp` 只設 `cli_rc=0`，**不** early-exit；落到 L876 `_fmt_rc="$(_run_format_check_if_needed …)"` 後才 L883 register ⇒ 預設 `:-0` 不會在合法路徑誤擋。
- 未知 stub 臂 L825–830 在 emit 後 `exit`，**不**呼叫 register ⇒ 無「未設 `_fmt_rc` 卻 register」窗。
- 結構測 `test_stamp_register_guarded_by_format_rc` PASSED（guard 在 body_hash 之前）。

**結果：assumed 成立；未發現 harness stub／preserve* 誤擋合法登記。**（X2 端到端 interaction 屬 codex 閉合義務，本家不重跑。）

---

## 必答 3 — 可否結票進 stamp 輪？

**可以（proceed）**。本家 R1 P1 反例已閉合；路徑正規化與 `_fmt_rc` 作用域攻擊未揭新 BLOCKING；本輪 diff 無須再修。建議三家零 BLOCKING 後進 stamp 輪結 CXSTAMP。

---

## §1 必查摘要

1. 矛盾：無（path 綁定與解鎖註解一致）  
2. 漏項：R1 異路徑缺口已補測＋碼  
3. 不可測：無（反例可重跑）  
4–8. quant／OOM／cache／API：不適用  
9. 測試：41 passed；新異路徑條綠  
10. Agent 可執行：閉合確認完成  
11. 短命工：無  

---

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——R1 `GROK-R1-P1-01` 異路徑／stamp-target 反例重跑皆 rc≠0、同路徑重登 rc=0；`Path.resolve()` 八向探針與 `_fmt_rc` 唯一呼叫點攻擊均未揭可繞缺口；可結票進 stamp 輪。

**碼證**: CODE-ANCHOR 對照（非 P0/P1，供核對）：`scripts/debt_clear.sh:501-504` `_norm`＋路徑等式；`scripts/cx_run.sh:565-568` `_fmt_rc` 守衛。RECHECK：`venv/bin/python -m pytest tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -q` → **11 passed**；擴套含 `test_debt_clear.py` → **41 passed** rc=0。隔離探針 A unrelated rc=1、B stamp-target rc=1、C same-path rc=0、D abs-same rc=0、E `..` rc=0、F symlink-same rc=0、G symlink-diff rc=1、H abs-unrelated rc=1（`/tmp/cxstamp_r2_probe/results.json` ALL_PASS）。`grep -n "_maybe_register_stamp_output" scripts/cx_run.sh` → 呼叫僅 L883。

**來源摘要**: handoffs/20260913-CXSTAMP-X-REVIEW-R2-BRIEF.md#039a40938964;scripts/debt_clear.sh#8f796f5f801e;scripts/cx_run.sh#439095323491;tests/governance/test_debt_clear_stamp_unlock.py#8b488e1caac1;handoffs/reconcile/20260913-cxstamp-x-review-r1/synth.md#b6bab4264161

[NON-BLOCKING] 信心度=High。sentinel only；勿為湊數捏造實質 finding。X2（format-failed 不登記）由 codex 閉合；本家核對結構測＋呼叫圖已足。

---

ASSUMPTIONS_VERIFIED: Path.resolve 八向探針 ALL_PASS；`_fmt_rc` 唯一呼叫於 `_run_cli_and_emit` L883、賦值後才 register；R1 異路徑反例修後 rc≠0、同路徑 rc=0。  
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -v` → 11 passed；`… test_debt_clear.py …` 合跑 → 41 passed rc=0；隔離 path-bind 探針 A–H ALL_PASS。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT: handoffs/20260913-cxstamp-x-review-r2-grok.md

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R1-P1-01
STATUS: DONE
