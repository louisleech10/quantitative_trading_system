# CXSTAMP：stamp 輪交件端／銷帳端不一致之根因修補 — 三家審碼 R1（事後審）

brief-kind: review
task-id: `20260913-CXSTAMP-X-REVIEW-R1`
findings-round: R1

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`。
🔴 P0／P1 之 `**碼證**` 必含 `CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行破壞>`（DOCROT Task 1.6，缺則交件被拒）。
🔴 **stamp 輪自本修補起亦跑 `completeness --single`**；本輪是 review 輪，不受影響，但請注意你們之後的 stamp 交件須有 `**斷言**`＋`**碼證**`（P3-00 sentinel 亦然）、`VERDICT: proceed|blocked`、`CLOSED:` 空值。

## ⚠️ 程序例外（先講清楚）
DOCROT stamp-r3 一筆 OPEN 債把主控端**所有**派工擋死（含本 consult／review），而該債只有改工具才解得開 ⇒ 主委在**未經審**下先改、先用它銷債、再立刻派本輪審。這是死鎖逼出的順序倒置，非常態；審不過即回退（`git revert`）並重議。使用者 2026-09-13 逐字裁定：「照你的方式做」。

## 根因（三處互相矛盾）
1. `scripts/cx_run.sh:_run_format_check_if_needed` 只對 `review|consult|closure` 跑 `completeness --single`，**stamp 輪跳過** ⇒ 空殼交件（codex 寫 `**核對**` 無 `**碼證**`、`VERDICT: APPROVED`）照記 `success`。
2. `reconcile_build`／`debt_clear` 對同一檔**會**跑 completeness ⇒ 紅。
3. `debt_clear` 要求 success 檔 sha 不得改；C-9 不得 abandon；cx_run「最新已 success 拒重派」；`_gate_lex` 把 cx_run 當 dispatch、被債擋 ⇒ 四路全封。

## 修法（兩處既有腳本；不新腳本）
- **A `scripts/cx_run.sh`**：(a) `_run_format_check_if_needed` 在凍結 case 區塊**外側**加 stamp 分支：cli ok＋產出非空 ⇒ 跑同一支 `--single`，checker 缺即 127（fail-closed，與 findings-kind 同）；(b) `_write_stub_success_output` 加 `stamp)` 臂寫最小合法 P3-00 sentinel（impl 維持 stub-ok）。
- **B `scripts/debt_clear.sh`**：sha 不符時，**只限** `committee_round_open.brief_kind == "stamp"` 之輪，且其後同 round 同家有 `committee_output`（主委顯式 register-output，經 verdict 解析＋family 綁定）且其 sha == 檔案當前 sha ⇒ 視為已交件（印具名通知）；非 stamp／缺 brief_kind／sha 不符／無登記 ⇒ 維持原判。
- 兩個既有 harness 對齊：`test_debt_emit.py::_b3_harness` 補 `completeness_check.sh`（同 `test_stamp_taskid_inject` 註解之做法：缺工具＝檢查沒跑，補清單不放寬）；`test_govb1_b31_recovery.py::test_destination_check_does_not_false_positive` 對照組內容改為合法 sentinel（該條測落點閘，內容形狀非其標的）。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：`scripts/cx_run.sh` 之 stamp 分支（緊接 `esac` 之後、Task 4.3 區塊之前）與 `_write_stub_success_output` 之 `stamp)` 臂；`scripts/debt_clear.sh` 之 `round_brief_kind()` 與 `if actual != expect:` 分支。
- **本輪 diff**：`git diff 1481604e..HEAD -- scripts/cx_run.sh scripts/debt_clear.sh tests/governance/test_cxrun_stamp_format_gate.py tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_debt_emit.py tests/governance/test_govb1_b31_recovery.py`
- 🔴 **不在範圍**：DOCROT Task 1.1–1.8（已三輪審碼＋戳記）；`_B45_HARNESS` 五檔未動。

## 本 brief 前提
fact-verified: 新測試 `test_cxrun_stamp_format_gate.py`（4 條：空殼→format-failed／合法 sentinel→success／stub 自過閘／checker 缺→非 success）＋`test_debt_clear_stamp_unlock.py`（5 條：stamp 解鎖／review 不解鎖／缺 brief_kind fail-closed／登記後再改擋／無登記擋）皆綠。
fact-verified: `test_debt_clear.py` 30 passed；`test_govb1_b31_recovery.py`＋`test_cxrun_stamp_prompt.py` 全綠（僅 `test_debt_clear_success_guard_not_relaxed` 在未 commit 時紅——它斷言工作區 debt_clear.sh 無 diff，commit 後綠）。
fact-verified: `test_debt_emit.py` 7 failed／82 passed，7 條全為 `committee_run` 之 `_b3_open*`（隔離 repo 缺 `prev_review_resolve.sh`，HANDOFF 已登記之既有紅，數字與基準相同）；三條 stamp `success` 斷言綠。
assumed: `scripts/cx_run.sh` 屬 `_B45_FORBIDDEN_PREFIXES` 但 B4 起列 `_B4_ALLOWED_COVARIANT`，且本改動在凍結錨點外側 ⇒ `test_govb1_contract_matrix.py` 不因本改動轉紅（主委**未跑**該檔：其中一條會建 git worktree 掛住，HANDOFF 已記）。請攻：跑 `venv/bin/python -m pytest tests/governance/test_govb1_contract_matrix.py -q -k "waiver and not worktree"` 並附結果。
assumed: 解鎖路徑 B 不會被濫用為「任何 stamp 交件都可事後改字面」——每次都須主委顯式 register-output（留 audit、經 verdict 解析）。請攻：給一個 B 放過了不該放的構造。
assumed: `_maybe_register_stamp_output`（stamp-target 之 register）與新 stamp 格式檢查無互動。請攻。

## 必答
1. A／B 是否為最窄能過三問（擋哪個根因／不做再燒幾輪／怎麼機械量）的修法？有無更窄替代？
2. 三條 assumed 各自攻擊結果（附命令與 rc）。
3. 可以結票嗎？若 BLOCKING，主委回退並重議。

## 產出
canonical 四欄 findings（或零 findings sentinel，含 `**斷言**`＋`**碼證**`）＋ `VERDICT: proceed|blocked`。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
