# CXSTAMP 事後審 R1 — COMPOSER

task-id: `20260913-CXSTAMP-X-REVIEW-R1`  
family: COMPOSER  
findings-round: R1  
brief: `handoffs/20260913-CXSTAMP-X-REVIEW-R1-BRIEF.md`  
scope: `scripts/cx_run.sh` stamp 分支（`_run_format_check_if_needed` 凍結 `esac` 外側、`_write_stub_success_output` 之 `stamp)` 臂）＋ `scripts/debt_clear.sh` 之 `round_brief_kind()`／`actual != expect` 分支；本輪 diff `1481604e..HEAD` 所列六檔；禁改碼。

---

## §0 挑戰前提

| 前提 | brief 標籤 | composer 重判 | 碼證 |
|---|---|---|---|
| 新測試 9 條（`test_cxrun_stamp_format_gate` 4＋`test_debt_clear_stamp_unlock` 5）全綠 | fact-verified | **本輪重驗成立** | `venv/bin/python -m pytest tests/governance/test_cxrun_stamp_format_gate.py tests/governance/test_debt_clear_stamp_unlock.py -q` → **9 passed** rc=0 |
| `test_govb1_contract_matrix.py -k "waiver and not worktree"` 不因本改動轉紅 | assumed | **成立** | 同命令 → **7 passed** rc=0（4.30s） |
| 解鎖路徑 B 不會被濫用為「任何 stamp 交件都可事後改字面」 | assumed | **成立（收窄至主委顯式 register-output；無登記／非 stamp／stale sha 皆擋）** | 見必答 2-B |
| `_maybe_register_stamp_output` 與新 stamp 格式檢查無互動 | assumed | **成立（不同檔案、不同閘；format-failed 仍阻 debt_clear）** | 見必答 2-C |

---

## 必答 1 — A／B 是否最窄修法

| 根因 | A（`cx_run` stamp 亦跑 `--single`） | B（`debt_clear` stamp 收窄解鎖） |
|---|---|---|
| 交件端 stamp 跳過格式檢查即記 success，銷帳端對同檔會跑 completeness ⇒ 死鎖 | **直接堵住**：`cx_run.sh:733-740` 與 review 分支同一支 checker、同 fail-closed（缺檔 rc=127）；stub 改寫合法 P3-00 sentinel（`:655-665`） | 不適用（新路徑 hollow ⇒ `format-failed`） |
| 歷史已 success 之空殼檔不得改、C-9 不得 abandon、cx_run 拒重派 | A 無法回溯修已落 audit 之 success sha | **只限** `brief_kind=stamp` 且其後 `committee_output` sha 與當前檔相符（`:496-508`）；review／缺 brief_kind／無登記／登記後再改皆維持原判（測試 5 條覆蓋） |

**更窄替代評估**

- 僅 A、不要 B：歷史 stamp-r3 空殼 success 仍無出路（四路全封），不符合 brief 根因敘事。
- 僅 B、不要 A：新輪仍可能 cx_run success／debt_clear 紅，兩端真相源分裂未解。
- 日期閘 B 或新腳本：增加機械複雜度，無 brief 授權，且違「兩處既有腳本」約束。

**機械量**：空殼→`format-failed`／合法 sentinel→`success`／checker 缺→非 success（4 條）；stamp 解鎖 5 條＋waiver 7 條；量測點＝`result_state` 與 `debt_clear` rc。

**結論**：A＋B 為 brief 三問下最窄成對修法；未見更窄且能同時解新輪一致性與歷史死鎖之替代。

---

## 必答 2 — 三條 assumed 攻擊

### 2-A — `test_govb1_contract_matrix` waiver 不因 cx_run 改動轉紅

- 命令：`venv/bin/python -m pytest tests/governance/test_govb1_contract_matrix.py -q -k "waiver and not worktree"`
- 結果：**7 passed** rc=0
- 攻擊結論：改動在 `_B45_HARNESS` 凍結錨點外側（brief 自述＋diff 對照），waiver 探針未觸 forbidden prefix；假設成立。

### 2-B — 構造「B 放過不該放」之案例

**嘗試構造**：stamp 輪 success（合法 sentinel）→ 改檔為 hollow（`**核對**` 無 `**碼證**`）→ 主委 `register-output` 新 sha → `debt_clear`。

- 新輪初交：hollow 已被 A 擋下（`test_stamp_hollow_delivery_is_format_failed` PASSED）⇒ 不能靠 cx_run 直接記 success。
- 事後改檔：B 確會在 `brief_kind=stamp`＋`committee_output` sha 相符時放行（`test_stamp_round_edited_then_reregistered_unlocks` PASSED）。
- **反證不應放行**：
  - 同操作於 `brief_kind=review` ⇒ rc≠0（`test_review_round_edited_then_reregistered_still_blocked`）
  - 缺 `brief_kind` ⇒ rc≠0（`test_round_without_brief_kind_is_fail_closed`）
  - 登記後再改 ⇒ rc≠0（`test_stamp_round_reregistered_with_stale_sha_blocked`）
  - 改檔無 `committee_output` ⇒ rc≠0（`test_stamp_round_edited_without_reregister_blocked`）

**攻擊結論**：B 之「事後改字面」必須主委顯式 register-output 且 sha 鎖定當前檔；非 stamp 或無登記皆 fail-closed。殘留風險＝主委刻意登記劣質內容（治理信任邊界），非本 patch 機械漏洞；**不列 finding**。

### 2-C — `_maybe_register_stamp_output` 與格式檢查互動

| 檢查點 | 觀測 |
|---|---|
| 呼叫順序 | `cx_run.sh:869` `_run_format_check_if_needed` → `:870` `_emit_family_result` → `:876` `_maybe_register_stamp_output` |
| 目標檔 | 格式檢查針對委員交件 `out`；`_maybe_register_stamp_output` 針對 `stamp_target`（`:554-555`）且需 `RECONCILE-STAMP` 行＋body hash（`:561-582`） |
| format-failed 時 | `_emit_family_result` 記 `format-failed`（`:500-501`）；`debt_clear` 拒非 success（`debt_clear.sh:472-476`）⇒ 即使 stamp_target 條件成立亦無法銷帳 |
| stub 路徑 | `test_stamp_stub_success_output_passes_own_gate`：stub sentinel 自過閘且 success |

**攻擊結論**：兩路徑檔案與閘門獨立；無交叉弱化。假設成立。

---

## 必答 3 — 可否結票

本輪 current block＋diff 逐項核對：A 統一交件／銷帳真相源；B 僅解歷史 stamp 死鎖且五向 fail-closed 有測；三條 assumed 攻擊未發現 BLOCKING 缺口。**可結票（proceed）**。

---

## §1 必查摘要

1. 矛盾：無（A 與 B 職責互補、測試與 brief 敘事一致）  
2. 漏項：無（9 條新測＋waiver 7 條覆蓋主要分支）  
3. 不可測：無（rc／`result_state` 可重跑）  
4–8. quant／OOM／cache／API：不適用  
9. 測試：9＋7 passed；mutation 意圖見各測 docstring  
10. Agent 可執行：是  
11. 短命工：無  

## 被當成事實的未驗證假設（§0）

brief 三條 assumed 已上表重判並附命令；無需另列 blocking finding。

---

## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對後無 finding——A／B 為最窄成對修法、三條 assumed 攻擊未發現機械漏洞、9＋7 條 pytest 全綠。

**碼證**: current block `cx_run.sh:655-665`／`:733-740` 與 `debt_clear.sh:416-430`／`:496-508`；`git diff 1481604e..HEAD` 六檔；`venv/bin/python -m pytest tests/governance/test_cxrun_stamp_format_gate.py tests/governance/test_debt_clear_stamp_unlock.py -q` → 9 passed rc=0；`venv/bin/python -m pytest tests/governance/test_govb1_contract_matrix.py -q -k "waiver and not worktree"` → 7 passed rc=0；B 濫用構造五條 `test_debt_clear_stamp_unlock` 反例皆 PASSED。

**來源摘要**: handoffs/20260913-CXSTAMP-X-REVIEW-R1-BRIEF.md#cdecc8b5b8d3;scripts/cx_run.sh#25ff92c32893;scripts/debt_clear.sh#220b4a6993ce

[NON-BLOCKING] 信心度=High。建議三家均 proceed 後進 stamp 輪結 CXSTAMP。

---

ASSUMPTIONS_VERIFIED: waiver 7 passed；新測 9 passed；B 五向 fail-closed 反例全過；`_maybe_register_stamp_output` 與格式檢查檔案／閘門獨立。  
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_cxrun_stamp_format_gate.py tests/governance/test_debt_clear_stamp_unlock.py -q` → 9 passed rc=0；`venv/bin/python -m pytest tests/governance/test_govb1_contract_matrix.py -q -k "waiver and not worktree"` → 7 passed rc=0。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（治理腳本行為：stamp 輪新增 `--single` gate；debt_clear stamp 收窄解鎖）  

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:  
STATUS: DONE
