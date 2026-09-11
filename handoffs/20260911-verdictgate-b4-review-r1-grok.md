# VERDICTGATE B4（Task 4.1）code review R1 — GROK

brief-kind: review  
task-id: 20260911-VERDICTGATE-B4-REVIEW-R1  
family: grok  
findings-round: R1  
審查對象: `scripts/_synth_attr.py`／`reconcile_cluster_attribution_check.sh`／`synth_attribution_hook.sh`／`debt_clear.sh::_run_attribution`／`reconcile_build.sh`／`tests/governance/test_verdictgate_p4.py`  
SCOPE: review-only；禁改碼／禁在本 repo commit／push；禁跑 `tests/governance` 全套  
**範本**: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄

## 被當成事實的未驗證假設（§0）

fact-verified: `venv/bin/python -m pytest tests/governance/test_verdictgate_p4.py -q` → **21 passed** rc=0。

fact-verified: `venv/bin/python -m pytest tests/governance/test_synth_attribution_hook.py tests/governance/test_spec_xref_check.py tests/governance/test_debt_clear.py -q` → **52 passed** rc=0（hook 7 + xref 8 + debt_clear 30；collect 對得上 brief）。

fact-verified: `venv/bin/python handoffs/20260911-verdictgate-mutate-b4.py` → M14–M20（含 M15b／M15c）**9/9 COVERED，UNCOVERED=0**。

fact-verified: 歷史 24 份 synth（VG 11＝x-review-r2..r10＋b1-r1＋b1-r2；SU 13＝b1..b7＋x-review-r1..r4）逐份 `reconcile_cluster_attribution_check.sh … --todo docs/<EPIC>_TODO.md` → **全部 rc=1**（②為主；①見 SU b1／b2-r2／b2-r3；與 brief 一致）。

fact-verified: `bash scripts/debt_ledger.sh --has-open` → rc=1（本輪 OPEN；派工後預期值: rc=1——非 2）。

fact-verified: `_id_in` 對 `CODEX-R1-P1-01` vs `CODEX-R1-P1-010`／`XCODEX-R1-P1-01` → 皆 False；精確／表列／空白前 → True。

fact-verified: `延後→Task 9.9` 對只含 `Task 4.1` 之 TODO → disposition 錯／gate 會紅（M15c 類仍成立）。

fact-verified: **否證 brief assumed**——`延後→Task`、`延後→Task、9.9`（以及 `，。；` 截斷）對含 `Task 4.1` 之 TODO → **gate rc=0**（子字串 `Task in todo_text` fail-open）。見必答 5／finding P1-01。

assumed: 歷史已 CLOSED round 不會再經 `_run_attribution`——碼證為 `_cmd_clear` 在 OPEN 檢查失敗且 st_rc=2 時 early return（`debt_clear.sh` 已 CLOSED 冪等），本輪未重跑真實歷史 session 的 `debt_clear`（會動 audit；review-only）。

---

## 必答 1：SPEC ASSERT ↔ test

SPEC Task 4.1 五條 ASSERT → 皆有對應 test：

| SPEC ASSERT（摘要） | test |
|---|---|
| `id_in_table=absent` → rc≠0 | `test_41_id_in_table_absent_rc_nonzero` |
| `quote20=mismatch` → rc≠0 | `test_41_quote20_mismatch_rc_nonzero` |
| `disposition=absent` → rc≠0 | `test_41_disposition_absent_rc_nonzero` |
| `disposition=延後 target=missing_in_todo` → rc≠0 | `test_41_defer_target_missing_in_todo_rc_nonzero` |
| 全合規 → rc=0 | `test_41_all_good_rc_zero` |

邊界①②③：

| 邊界 | test |
|---|---|
| ① 斷言 <20 字 ⇒ 引用全文 | `test_41_short_assertion_quotes_full_text` |
| ② NFC／去空白；不寬容標點 | `test_41_nfc_and_whitespace_tolerant_but_not_punctuation` |
| ③ 兩列任一合規即可 | `test_41_two_rows_any_one_compliant_ok` |

另有：`defer` 空白整詞（M15c）、缺 `--todo`、佔位列、`-x-` 標的、hook／gate 模式差、hook 模組缺失 fail-open。**缺口**：無測試擋「目標為 `Task`／`E`／`4.1` 等 TODO 子字串」——見 P1-01。

---

## 必答 2：hook 與閘同一實作

**立場**：生產路徑上 hook 與閘**確實同一模組**（`scripts/_synth_attr.py`）；`test_41_hook_and_gate_agree_on_ids_target_quote` **不能**證明「兩包裝對同一 fixture 結果一致」，對 `check_ids`／`check_target` 更是同呼叫自比的恆真。

碼證：

- `synth_attribution_hook.sh:38` → `python3 "${MOD}" … --mode hook`（`MOD` 預設 `_synth_attr.py`）
- `reconcile_cluster_attribution_check.sh:18` → `exec python3 …/_synth_attr.py … --mode gate`
- 測試 L156–160：`assert sa.check_ids(doc) == sa.check_ids(doc)`；`check_target` 同；`check_quote20(completed_only=True)` vs `False` 只在「列皆已完成／無候選」fixture 上比——此時兩模式本就同結果。草稿列分歧另由 `test_41_hook_draft_row_without_token_not_quote_checked_but_gate_is` 覆蓋。

**可證偽改法**：①刪自比，改 `run(doc,"hook",…)` 之 ids／target／quote 子集 vs `run(doc,"gate",…)` 在全完成 fixture 上相等；②對同一檔真呼叫 hook.sh 與 gate.sh，比對 stderr ①／②／⑤；③加一案「草稿列」斷言兩模式 quote **必須**不同（防有人把 `completed_only` 寫死）。

見 P2-01（測試品質；非生產雙實作漂移）。

---

## 必答 3：「已完成列」與繞過縫

**立場**：同意主委——hook 對「第 4 欄有字但無 disposition token」不驗 quote20；閘全量驗；token 缺本身即 ③。不存在「永遠不填 token 卻靠 debt_clear 綠燈過」的縫：`test_clear_attribution_gate_blocks_bad_synth`＋gate `check_disposition` 會擋。手動改 lock／audit 繞過不在本閘契約內。

hook 模組缺失／崩潰靜默放行（`synth_attribution_hook.sh:43`）＝已文件化誠實邊界；debt_clear 全量仍擋。可接受，不升 P0/P1。

---

## 必答 4：ID 比對邊界（實跑）

```
VERIFY: venv/bin/python /tmp/vg-b4-r1-probe/probe_id_defer.py
→ _id_in('CODEX-R1-P1-01','CODEX-R1-P1-01') True
→ _id_in('CODEX-R1-P1-010','CODEX-R1-P1-01') False
→ _id_in('XCODEX-R1-P1-01','CODEX-R1-P1-01') False
→ 前綴 A／前導 - 皆 False；空白前／|cell| True
```

**結論**：`(?<![A-Z0-9-])ID(?![0-9])` 不會誤中 `…010`／`X…`。無 finding。

---

## 必答 5：`延後→` 目標擷取（實跑＋縫）

空白整詞（主委已修）仍正確：

```
VERIFY: check_disposition(延後→Task 9.9, todo='Task 4.1 only') → 非空錯
VERIFY: test_41_defer_target_with_space_is_whole_token 在 p4 套件內 PASSED
```

**否證 assumed（多目標／標點縫）**：

| 構造 | TODO 含 | 結果 |
|---|---|---|
| `延後→Task 9.9` | 僅 `Task 4.1` | 紅（正確） |
| `延後→Task` | `Task 4.1` | **綠 fail-open** |
| `延後→Task、9.9`／`，`／`。`／`；` | `Task 4.1` | **綠 fail-open**（截成 `Task`） |
| `延後→E`／`延後→4.1`／`延後→Task 4` | 含 `E-4`／`Task 4.1` | **綠 fail-open** |
| `延後→Task 4.1；延後→E-MISSING` | 僅 Task 4.1 | 紅（第二目標有驗） |
| `延後→E-4（註）` | 僅 `E-4` | 紅（`（` 併入目標；fail-closed UX） |

```
VERIFY: bash /tmp/vg-b4-r1-probe/run_bare_gate.sh
→ [_synth_attr] ✓ … mode=gate … 全在群集表、引用與處置合規
→ gate_rc=0   # row4=延後→Task，TODO=### Task 4.1
```

根因：`tgt not in todo_text` 是**子字串**包含，不是「整段 Task N.N／殘留 ID」錨定；標點截斷把 `Task 9.9` 變回 `Task` 後，與 M15c 要修的那類 fail-open **同型復發**。見 **GROK-R1-P1-01**。

---

## 必答 6：歷史 synth 實跑＋「已清債不再經 debt_clear」

```
VERIFY: bash /tmp/vg-b4-r1-probe/run_hist_synths.sh
→ 24/24 rc=1；rc0=0
→ ①：splitunify-b1／b2-r2／b2-r3（及 b3 等亦帶 1）；②幾乎全有；③／⑤見多份 VG x-review
```

**已清債不經閘**：`debt_clear.sh` `_cmd_clear` 先 `_assert_round_is_OPEN`；已 CLOSED → st_rc=2 → 印 `already CLOSED (idempotent no-op)` 並 `return 0`，**其後才**是 completeness／`_run_attribution`。故歷史紅只在手動重跑腳本時印出，不擋現行銷帳。與 SPEC「不回改、不作判定輸入」一致。

---

## 必答 7：debt_clear `--todo` 推導

碼：`epic="$(printf '%s' "${SESSION}" | awk -F- '{print toupper($2)}')"`；僅當 `docs/${epic}_TODO.md` 存在才傳 `--todo`。

| session 第二段 | 推得 | 實檔 | 行為 |
|---|---|---|---|
| `verdictgate` | `VERDICTGATE` | 有 | 傳 `--todo` |
| `p16`（若 session 為 `…-p16-…`） | `P16` | **無** `docs/P16_TODO.md`（實為 `P16_COMMITTEE_DEBT_TODO.md`） | 不傳 → 有延後即拒 |
| 缺第二段 | 空 | — | 不傳 → 有延後即拒 |

**立場：可接受（fail-closed）**。誤名／缺檔不會讓延後靜默過；代價是合法延後也必須有對得上的 `docs/<第二段大寫>_TODO.md`，或清債前改 session 命名。建議在 TODO／骨架註明契約；不擋收 B4 本體，但 P1 修目標匹配時可一併收緊「允許的目標形狀」。

---

## 必答 8：可否收 B4？

**不可（本輪 `blocked`）**——P1-01 讓「延後目標存在」在子字串／標點截斷下 fail-open，與 Task 4.1 要擋的「延後即消失」同病；M15c 只釘空白截斷，未釘 `Task`∈`Task 4.1`。ASSERT 五條與 mutation 9/9、hook／閘同模組、歷史 24 紅不污染現行銷帳皆成立，但 **④ 延後目標存在性尚未閉合**。

修法方向（供主委，本輪不改碼）：①目標匹配改整詞／錨定（例如 `Task\s+\d+\.\d+` 或殘留 ID 全字，禁裸 `Task`／`E`／`4.1`）；②標點截斷後若目標不符合允許形狀 ⇒ ④ 錯；③補 test＋mutation：`延後→Task`／`延後→Task、9.9` 對含 `Task 4.1` 之 TODO 必 rc=1。

---

## GROK-R1-P1-01

**斷言**: `check_disposition` 以 `tgt not in todo_text` 做子字串包含，故 `延後→Task`（以及被 `、，。；` 截成 `Task` 的 `延後→Task、9.9` 等）在 TODO 僅有 `Task 4.1` 時 gate 仍 rc=0——延後目標存在性 fail-open。

**碼證**: `_synth_attr.py:149-157`（`延後→([^|，。；、）)]*)`＋`tgt not in todo_text`）。VERIFY: `bash /tmp/vg-b4-r1-probe/run_bare_gate.sh` → gate_rc=0（row4=`延後→Task`，TODO=`### Task 4.1`）；同目錄 probe 對 `延後→Task、9.9`／`延後→E`／`延後→4.1`／`延後→Task 4` 皆 PASS_FAILOPEN。對照：`延後→Task 9.9` vs 僅 `Task 4.1` 仍紅（M15c 範圍）。RECHECK: 重跑 bare_gate；或 `check_disposition(parse(延後→Task), todo='### Task 4.1')` 須改為非空錯後再收 B4。

**來源摘要**: scripts/_synth_attr.py#8ef20ed5ab7c;tests/governance/test_verdictgate_p4.py#912b27393cfe;handoffs/20260911-VERDICTGATE-B4-REVIEW-R1-BRIEF.md#30505338ef5f;docs/VERDICTGATE_SPEC.md#d723f42d7194

[P1] 信心度=High。不改則：收斂檔可把找不到的延後目標寫成 `延後→Task`／標點截斷形，debt_clear ④ 放行 ⇒ finding「延後」無真實 TODO 錨，SPLITUNIFY／後續票復工時該項從機械追蹤消失——正是 Task 4.1／C-1 要閉的洞。修法見必答 8。

---

## GROK-R1-P2-01

**斷言**: `test_41_hook_and_gate_agree_on_ids_target_quote` 對 `check_ids`／`check_target` 是同呼叫自比恆真，對 quote 只在「已完成列」fixture 上比 True/False——不能證偽 hook.sh 與 gate.sh 包裝是否偏離。

**碼證**: `tests/governance/test_verdictgate_p4.py:152-160`；對照生產呼叫 `synth_attribution_hook.sh:38` vs `reconcile_cluster_attribution_check.sh:18`（同模組，測試未驅動兩包裝）。RECHECK: 將測試改為比 `run(...,"hook")` 與 `run(...,"gate")` 共享子集，或真呼叫兩支 bash。

**來源摘要**: tests/governance/test_verdictgate_p4.py#912b27393cfe;scripts/synth_attribution_hook.sh#ad9c334c22dc;scripts/reconcile_cluster_attribution_check.sh#8f1b90735e2b

[P2] 信心度=High。不改不會單獨造成現行銷帳 fail-open（實作確為單一模組）；回歸時雙包裝若分叉可能假綠。不擋在 P1 之後的獨立收案理由，但應修。

---

VERDICT: blocked
BLOCKED-BY: GROK-R1-P1-01
CLOSED:

---

ASSUMPTIONS_VERIFIED: p4 21/21；hook+xref+debt_clear 52/52；mutate-b4 UNCOVERED=0；歷史 24 synth 全 rc=1；`_id_in` 不誤中 010／X 前綴；`Task 9.9` 空白整詞仍紅；`延後→Task`／標點截斷對 `Task 4.1` TODO gate_rc=0（否證 assumed）；CLOSED early-return 在 attribution 之前（碼證）；epic 第二段推 TODO 缺檔 fail-closed
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_verdictgate_p4.py -q` → 21 passed rc=0；`… test_synth_attribution_hook.py test_spec_xref_check.py test_debt_clear.py -q` → 52 passed rc=0；`venv/bin/python handoffs/20260911-verdictgate-mutate-b4.py` → 9/9 COVERED UNCOVERED=0；hist 24× attribution_check → 24× rc=1；bare_gate `延後→Task` → rc=0
FAILURES_SEEN: none（審查過程；發現之 fail-open 為產品縫，非本輪測試回歸）
SCOPE_CHANGES: none（review-only；probe 僅 /tmp/vg-b4-r1-probe）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-b4-review-r1-grok.md

STATUS: DONE
