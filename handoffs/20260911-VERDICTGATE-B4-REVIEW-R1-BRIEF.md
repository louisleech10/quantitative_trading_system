# VERDICTGATE B4（Task 4.1）code review R1

brief-kind: review
task-id: 20260911-VERDICTGATE-B4-REVIEW-R1
findings-round: R1

🔴 **這是審碼（review），不是實作。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁跑 `tests/governance` 全套；禁在本 repo commit／push。**
🔴 交件檔末段必含三行機械裁決塊（`VERDICT: proceed|blocked`／`BLOCKED-BY:`／`CLOSED:`，只准值集；CLOSED 只列本家 ID）；**`STATUS: DONE` 逐字**。B3 R1 codex 裁決行寫成一句話被 `verdict_parse` 拒收，勿重蹈。
🔴 隔離實驗之指令列與暫存路徑**不得含任何委員家族名稱**（`gate_check` 會誤判為派工而擋；B3 閉合 R2 實例）。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`。

## 審查對象（`docs/VERDICTGATE_TODO.md` FROZEN Task 4.1；SPEC v9 Task 4.1／C-1／§N 第三項）
- `scripts/_synth_attr.py`（新，**唯一實作**）：`parse_synth`／`check_ids`／`check_quote20(values, completed_only)`／`check_disposition(values, todo_text, strict_defer)`／`check_target`／`check_placeholder`；`nfc_strip`＝NFC＋去所有 `\s`；`QUOTE_N=20`；CLI `--mode hook|gate [--todo] [--report]`，rc 0／1／2。
- `scripts/reconcile_cluster_attribution_check.sh`（重寫：bash 薄包裝 → 模組 gate 模式；舊版恆 rc=0 之「只印」已廢）。
- `scripts/synth_attribution_hook.sh`（改為呼叫模組 hook 模式：`check_ids`＋`check_target`＋`check_disposition(strict_defer=False)`＋`check_quote20(completed_only=True)`＋佔位；模組缺失／崩潰 ⇒ 靜默放行——**主委加的誠實邊界，請審**；`SYNTH_ATTR_MODULE` 只供測試覆寫）。
- `scripts/debt_clear.sh::_run_attribution`（插在 `_run_completeness` 之後、`_run_synth_xref` 之前；`--todo` 由 session 第二段大寫推 `docs/<EPIC>_TODO.md`，缺檔則不傳 ⇒ 有延後即拒）。
- `scripts/reconcile_build.sh`（骨架加群集表格式提示；建檔後之提示呼叫改 `--report`、rc 丟棄）。
- `tests/governance/test_verdictgate_p4.py`（21）、`test_synth_attribution_hook.py`（7，SYNTH_OK 改含逐字引用；mutation 改打模組）、`test_debt_clear.py`（+2：閘拒銷／延後目標讀 epic TODO；`_build_session` 骨架改含群集表）；`handoffs/20260911-verdictgate-mutate-b4.py`（9：M14／M15／M15b／M15c／M16／M17／M18／M19／M20）。

## 🔴 必答
1. **SPEC ASSERT 對應**：Task 4.1 五條逐條指 test；邊界①②③各指 test。
2. **hook 與閘同一實作**：對同一 fixture，hook 模式與 gate 模式之 `check_ids`／`check_target`／`check_quote20` 是否逐字相同？（`test_41_hook_and_gate_agree_on_ids_target_quote` 是否真的證明，或只是同一函式呼叫兩次的恆真？給立場＋可證偽改法）
3. **「已完成列」判準**（codex R10 Q4 立場：第 4 欄含處置 token）：hook 對「第 4 欄有字但無 token」之列不驗 quote20；閘全量驗。是否有「永遠不填 token、靠 debt_clear 之前手動繞」的縫？（主委立場：debt_clear 全量閘擋，且 token 缺本身即 ③ 錯。）
4. **ID 比對邊界**：`_id_in` 用 `(?<![A-Z0-9-])ID(?![0-9])`——`CODEX-R1-P1-01` 是否會誤中 `CODEX-R1-P1-010`／`XCODEX-R1-P1-01`？實跑。
5. **`延後→` 目標擷取**：主委寫 brief 時自查發現原 regex 以 `\s` 截斷 ⇒ `延後→Task 9.9` 只驗 `"Task"` ⇒ 恆真（fail-open）。已改為擷取到儲存格結尾／中文標點再 strip（`test_41_defer_target_with_space_is_whole_token`＋mutation M15c）。請獨立重驗：對含 `Task 4.1` 之 TODO 跑 `延後→Task 9.9` 必 rc=1；並找此擷取規則之其他縫（目標含 `、`／全形括號／多個延後）。
6. **歷史 synth 實跑**：`bash scripts/reconcile_cluster_attribution_check.sh <synth> --todo docs/<EPIC>_TODO.md` 對本票 11 份＋SPLITUNIFY 13 份逐份跑（主委已跑：全部 rc=1，②為主）。確認「已清債之歷史 round 不會再經 debt_clear」屬實（碼證），即歷史紅不影響任何現行閘。
7. **debt_clear `--todo` 推導**：session 第二段大寫（`20260911-verdictgate-…` ⇒ `VERDICTGATE_TODO.md`）。反例：session 命名不含 epic 段、或 epic TODO 檔名不同（`docs/P16_COMMITTEE_DEBT_TODO.md`？）⇒ 缺檔不傳 `--todo` ⇒ 有延後即拒（fail-closed）。是否可接受？
8. **可否收 B4？**

## 停輪條件
①必答 1–8 皆有立場；②必答 4、5、6 附實跑；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會在收票／SPLITUNIFY 復工具體怎麼失敗」。

## 前提
fact-verified: `pytest tests/governance/test_verdictgate_p4.py` 21 passed；`test_synth_attribution_hook.py` 7；`test_spec_xref_check.py` 8；`test_debt_clear.py` 30；mutation 9/9 UNCOVERED=0（主委 2026-09-11）。
fact-verified: 歷史 24 份 synth 逐份 rc=1（②引用 20 字為主；③無 token 次之；①掉 ID 三份：splitunify b1／b2-r2／b2-r3）。
fact-verified: `debt_ledger --has-open` rc=0（B3 債已清；派工後預期值: rc=1——本輪 OPEN，非 2）。
assumed: 修後之 `延後→` 擷取規則無其他縫（多個延後、目標含 `、`）⇒ 否證觀測：必答 5 你構造之反例 rc=0。／我跑了：**跑了單一反例 `Task 9.9`（rc=1）**，多目標未跑。

## ⚠️ 前置
禁改碼；只跑上列測試檔與你點名的單檔；收尾清 /tmp workdir（保留 claude-501）。
