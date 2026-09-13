# Reconcile — 20260913-cxstamp-x-review-r1

**來源** 20260913-cxstamp-x-review-r1-codex.md, 20260913-cxstamp-x-review-r1-composer.md, 20260913-cxstamp-x-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：HANDOFF.md

本輪性質：三家事後審 CXSTAMP 修補（commit ede04741；程序例外＝OPEN 債擋死派工，先改先銷債再審）。composer 零 finding、可結票；codex／grok 各一條 P1 BLOCKING 同題（解鎖分支未綁路徑）；codex 一條 P2。三條 assumed：waiver 探針三家實跑 7 passed 成立；「B 不會被濫用」被兩家實跑推翻（見 X1）；「stamp register 與新格式檢查無互動」被 codex 推翻（見 X2）。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **X1 解鎖分支未綁 output_path，異路徑 committee_output 亦可銷帳（兩家）**——「B 的 stamp 解鎖只綁 brief_kin」「`debt_clear` 之 stamp 解鎖」 | P1 | CODEX-R1-P1-01, GROK-R1-P1-01 | 採納（修法＝重登之 committee_output 須正規化路徑等於同一份交件檔，否則維持原判；反例測試「異路徑重登不解鎖」；兩家於 review-r2 重跑同一反例須 rc≠0） |
| **X2 format-failed 之 stamp 交件仍對 stamp-target 留 committee_output（codex）**——「新 stamp `--single` 失敗後，」 | P2 | CODEX-R1-P2-02 | 採納（修法＝stamp register 讀 caller 之格式 rc，非 0 即不登記；不動凍結呼叫點；源碼結構測試＋codex 於 review-r2 重跑 interaction 探針 COMMITTEE_OUTPUT_COUNT 應 1→0） |
| **X3 A／B 對表通過、assumed-1 成立、可結票（composer）**——「本輪逐項核對後無 finding——A／B」 | P3 | COMPOSER-R1-P3-00 | 採納（composer 之「B 五向 fail-closed」結論被 X1 收窄：五向之外漏了異路徑一向，已補為六向） |

**結票條件**：review-r2 codex／grok 反例閉合＋三家零 BLOCKING → 戳記 → CXSTAMP 結票。

Verdict：需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: B 的 stamp 解鎖只綁 brief_kind、同家及後續 sha，未綁 `committee_output.output_path` 到本輪宣告的 stamp-target，因此原 success 交件檔仍被改動時，另註冊任意 handoff 也可銷帳。
**碼證**: `scripts/debt_clear.sh:496-508` 只驗 `rr` 自己的 path/sha 後 `continue`；實際隔離攻擊以 `gate.sh register-output --kind stamp --family codex` 註冊 `handoffs/unrelated.md`。
CODE-ANCHOR: scripts/debt_clear.sh:496
MUTATION: 以 `handoffs/unrelated.md` 取代 `rr.output_path` 後重跑同一隔離 harness；實跑 REGISTER_RC=0、CLEAR_RC=0、OLD_OUTPUT_IS_TAMPERED=True。
VERIFY: `venv/bin/python -m pytest tests/governance/test_govb1_contract_matrix.py -q -k "waiver and not worktree"` → 7 passed, RC=0；B 隔離攻擊 → `REGISTER_RC=0`, `CLEAR_RC=0`, `OLD_OUTPUT_IS_TAMPERED=True`, `COMMITTEE_OUTPUT_EVENTS=1`。
RECHECK: 建 stamp round＋success 的 `handoffs/st1-codex.md`，修改該檔，再以 stamp register 註冊 `handoffs/unrelated.md`，執行 `debt_clear.sh --round-id ...`；預期修正後 RC 應非 0。
**來源摘要**: scripts/debt_clear.sh#220b4a6993ce;scripts/gate.sh#1779022ef126;handoffs/20260913-CXSTAMP-X-REVIEW-R1-BRIEF.md#cdecc8b5b8d
[BLOCKING] 信心度=High。必答 1：A 在凍結 case 外側重用同一 `--single` checker，並為 harness stamp 寫合法 sentinel，是擋根因 1 且無更窄替代；B 不是最窄安全修法。若不收窄，明確再燒一輪並可能把未對應原交件的檔案當已修正；修法是把後續 `committee_output` 綁到 round 的 exact stamp-target（或明確記錄的 recovery artifact）並保留 gate provenance。可行性由上述 attack 作為反例 oracle，path bind 後應拒絕。
Assumed-1：成立；指定 waiver 命令實跑 7 passed/RC=0，新增區塊位於凍結錨點外。Assumed-2：不成立；實際 gate register 任意 handoff 後 debt_clear 放行，違反「只准本交件」的安全意圖。
## CODEX-R1-P2-02
**斷言**: 新 stamp `--single` 失敗後，`_maybe_register_stamp_output` 仍只看 cli_rc 與非空 output，故同一輪會留下 stamp-target 的 committee_output side effect。
**碼證**: `scripts/cx_run.sh:559` 未檢查 `_fmt_rc`；`scripts/cx_run.sh:876` 在 emit format-failed 後仍呼叫 stamp register。
CODE-ANCHOR: scripts/cx_run.sh:559
MUTATION: 在 `_maybe_register_stamp_output` 的 guard 加 `_fmt_rc=0`，重跑 hollow-sentinel interaction harness；預期 `COMMITTEE_OUTPUT_COUNT` 由 1 變 0。
VERIFY: hollow stamp sentinel interaction → `CX_RC=3`, `RESULT_STATE=format-failed`, `COMMITTEE_OUTPUT_COUNT=1`, `COMMITTEE_OUTPUT_PATH=handoffs/b31-stamp-target.md`, `RC=0`。
RECHECK: 以 valid RECONCILE-STAMP target＋缺 **碼證** 的 P3-00 output 執行 cx_run；應同時觀察 format-failed 與 committee_output，確認 side effect。
**來源摘要**: scripts/cx_run.sh#25ff92c32893;tests/governance/test_cxrun_stamp_format_gate.py#d8cedfba3a14;handoffs/20260913-CXSTAMP-X-REVIEW-R1-BRIEF.md#cdecc8b5b8d
[MINOR] 信心度=High。Assumed-3 不成立。這不直接繞過 debt_clear，因其仍拒絕 `format-failed`，但 audit 已宣告 stamp output 可註冊，讓失敗交件與 stamp side effect 不一致；最窄修法是將 stamp register 的 guard 接收並要求格式 rc=0，或明確記錄「format-failed 不註冊」。
VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01
CLOSED:
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
## GROK-R1-P1-01

**斷言**: `debt_clear` 之 stamp 解鎖在 `actual != expect` 時，只要其後同 round 同家任一 `committee_output` 之檔案當前 sha 等於該事件登記 sha 即 `continue` 放行，不要求 `output_path` 等於該家 success 交件路徑；因此 `_maybe_register_stamp_output` 自動登記之 stamp-target（或任意異路徑）會讓家族交件被事後改字面後仍銷帳成功——推翻 brief assumed「每次須主委對交件顯式 register、不會被濫用為事後改字面」。

**碼證**: CODE-ANCHOR: scripts/debt_clear.sh:496 ；MUTATION: 解鎖分支加正規化 path 等式 `rr.output_path==op` 後，異路徑／stamp-target 構造應轉紅（rc≠0），同路徑重登仍綠；拿掉該等式 ⇒ 異路徑構造回 rc=0。RECHECK：L496–508 無 path 等式；`cx_run.sh:587` 以 `--kind stamp` 登記 stamp-target（`gate.sh` L209–211 跳過 expected、verdict=null）；本家實跑 stamp success→committee_output(STAMP_TARGET.md)→tamper 家族交件→debt_clear rc=0「視為已交件」，無登記對照 rc≠0；`pytest tests/governance/test_debt_clear_stamp_unlock.py -q` → 5 passed 未擋異路徑。

**來源摘要**: scripts/debt_clear.sh#220b4a6993ce;scripts/cx_run.sh#25ff92c32893;scripts/gate.sh#1779022ef126;handoffs/20260913-CXSTAMP-X-REVIEW-R1-BRIEF.md#cdecc8b5b8d3;tests/governance/test_debt_clear_stamp_unlock.py#ac7058156d8e

[BLOCKING] 信心度=High。  
會怎麼失敗：合法 stamp 輪三家 APPROVED 後，audit 已有 stamp-target 之 `committee_output`；任何人改 `handoffs/<session>-<fam>.md` 字面（削弱／竄改交件），`debt_clear` 仍過——「success 檔不得改」對 stamp 輪在自動登記後形同虛設。  
修法：解鎖分支增加 path 綁定（`rr.output_path` 正規化＝`op`）；可選拒絕 `verdict is null`。補兩條反例測試（異路徑擋／同路徑放）。可行性：既有 `test_debt_clear_stamp_unlock` harness 已能構造；本家異路徑探針已證當前為 rc=0、加 path 等式後預期 rc≠0。不新腳本。

---

VERDICT: blocked
BLOCKED-BY: GROK-R1-P1-01
CLOSED:
STATUS: DONE
