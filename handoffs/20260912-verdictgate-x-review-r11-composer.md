# VERDICTGATE 收票審 — COMPOSER R11

task-id: 20260912-VERDICTGATE-X-REVIEW-R11  
family: composer  
brief: `handoffs/20260912-VERDICTGATE-X-CLOSEOUT-R1-BRIEF.md`  
findings-round: R11  
review-target: C-4 範圍修正＋register-output 語料＋E-022～E-025＋§E 殘留＋結案裁決

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | R11 判定 |
|---|---|---|
| p1/p2/p3 77 passed、mutate-b1/b2 UNCOVERED=0 | fact-verified | **未重跑全套**；本輪重跑 `test_check_batch_already_entered_skips_prev_verdicts`＋`test_12_closed_id_in_legacy_round_expected_output_accepted` → 2 passed |
| `gen_fact_key_blocks --check` rc=0 | fact-verified | **成立** — `bash scripts/gen_fact_key_blocks.sh --check` → rc=0 |
| C-4 修正「假 review 輪」無縫 | assumed | **否證已跑** — 見必答 1；closure-first 路徑可跳過前批（P1） |
| expected_outputs 可被濫用 CLOSE 他家 ID | assumed | **反例未成立** — 見必答 1b |

---

## 必答 1 — C-4「只擋進入新批」是否開假輪縫？

**立場：review 首進路徑無縫；closure-first 首進路徑有縫（P1）。**

| 路徑 | 碼證 | 結論 |
|---|---|---|
| **review R1 首進 B2** | `test_check_batch_already_entered_skips_prev_verdicts`：B1 blocked 且無 B2 `round_open` 時 `_check(ROOT,2)` rc≠0；開 B2 review R1 後才 rc=0 | **無縫** — 首進必跑完整前批驗證 |
| **closure 首進 B2（前批仍 blocked）** | 暫存 audit 反例（`/tmp/vg-r11-fake-round-probe.sh`）：B1 codex blocked 無 CLOSED → Step B rc=1；直接 `_open ROOT-B2-REVIEW-R2 brief_kind=closure`（未開 B2 review R1）→ Step D rc=0 印「非新進批次」 | **有縫** — `verdictgate_check.sh:48` 任一 `committee_round_open` 命中 `${root}-b${n}-` 即跳過；closure 在 `gate.sh:957`／`committee_run.sh:433` 刻意不跑 verdictgate（SPEC 邊界①）⇒ 可先寫 B2 `round_open` 再領 B2 impl/review token 而不驗 B1 |
| **gate dispatch 對 review 是否必經 verdictgate** | `gate.sh:957-960`：`brief-kind != closure` 且 N≥1 才呼叫 `verdictgate_check.sh`；review 首進走此支 | **是** |
| **impl-self 是否同路** | `/tmp/vg-r11-impl-probe.sh`：closure-first 後 `verdictgate_check ROOT 2` rc=0 | **同路放行** |

**修法（建議）**：已進入判定改為「本批已有 **`brief_kind=review`** 之 `committee_round_open`」——仍允許 B4 review R1 進入後之補裁決 closure 不重驗前批（SPLITUNIFY 目的），但 closure 不能作為**首批**進入錨點。

RECHECK: `bash /tmp/vg-r11-fake-round-probe.sh`；`pytest tests/governance/test_verdictgate_p2.py::test_check_batch_already_entered_skips_prev_verdicts -q`。

---

## 必答 1b — register-output 納入 legacy `expected_outputs` 可否濫用？

**立場：無縫；接受主委修法。**

| 攻擊面 | 碼證 | 結論 |
|---|---|---|
| 開輪者指定他人檔案路徑 | `gate.sh:277-279`：`out_rel` 必須等於**本輪** `expected_outputs[family]`；檔名尾碼＋roster 對證 | 不能拿本輪 codex 交件冒充 composer 路徑 |
| CLOSED 他家 ID | `verdict_parse.sh:73-96`：`CLOSED` ID 前綴必須＝本產出家族大寫 | 不能 CLOSED `COMPOSER-*` 於 codex 檔 |
| 指向不存在檔 | corpus 納路徑但 `verdict_parse` 讀不到 `## <ID>` | fail-closed |
| legacy 同 root 舊輪 | `test_12_closed_id_in_legacy_round_expected_output_accepted`：B1 上線前只有 `round_open` 之舊 ID 可 CLOSED；他 root 對照拒收 | ** intended ** |

RECHECK: `pytest tests/governance/test_verdictgate_p1.py::test_12_closed_id_in_legacy_round_expected_output_accepted -q`。

---

## 必答 2 — SPEC C-4 字面偏離：收票內修正 vs FROZEN 修訂？

**立場：語意上接受收票內修正（記錄於 synth＋HANDOFF），但現行實作應收窄已進入判定（見 P1）；不需重開整份 SPEC FROZEN 流程。**

| 項目 | 立場 |
|---|---|
| SPEC 字面「開下一批前」 vs 實作「本批已有任意 round_open 即跳過」 | 語意對 SPLITUNIFY 補裁決場景正確；實作過寬（含 closure-first） |
| 程序 | 收票 synth 群集表＋HANDOFF 記錄即可；FROZEN 修訂留待 P1 修法落地後一行同步 SPEC Task 2.2 邊界 |

---

## 必答 3 — E-022～E-025 登記是否屬實？

**立場：四列分類與掛載點**整體屬實**；E-023 行號略漂移（登記 `:951`，實際 `verdictgate_check` 呼叫在 `:959`，仍屬同段 dispatch 前閘）。**

| ID | 產出端／豁免 | 行號可執行？ | 立場 |
|---|---|---|---|
| **E-022** | 豁免＋部分閘 | `cx_run.sh:612` 為 `gate.sh register-output` 可執行呼叫；第二層 `verdictgate_check.sh:35-53` 為可執行 Python 區塊 | **屬實** |
| **E-023** | 產出端 | `gate.sh:959` 呼叫 `verdictgate_check.sh`；路由經 `gate_check.sh` PreToolUse | **屬實**（一致性型邊界已寫） |
| **E-024** | 豁免＋部分閘 | `git_hooks/commit-msg:41` exec 前 `ticket_batch_check --msg`；push 端 `ticket_batch_check.sh:49` | **屬實** |
| **E-025** | 產出端 | `synth_attribution_hook.sh:40` 呼叫 `_synth_attr.py`；第二層 `debt_clear.sh:584` 後 `_run_attribution` | **屬實** |

RECHECK: `bash scripts/gen_fact_key_blocks.sh --check` rc=0；`sed -n '40p' scripts/synth_attribution_hook.sh`；`sed -n '959p' scripts/gate.sh`。

---

## 必答 4 — E-5 probe 重跑＋立場

**立場：同意 TODO §E E-5 結論——序判無增量，保留 mtime 第二層不做。**

VERIFY: `bash handoffs/20260911-verdictgate-e5-probe.sh` → `E5 PROBE: ORDER-ALWAYS-HOLDS（序判無增量；mtime 足夠）` rc=0。5 列 `ticket_commit` 皆在 token 之後 append；4 列 `token_fresh=false`（mtime 回撥 20 分鐘）。合法 amend／rebase 不產生「序在 token 前」之反例 ⇒ audit 序＋ts 差第二層與 mtime 等價、無增量。

§E E-5「為何現在不做」仍成立；建議 TODO 將 E-5 狀態由 needs-research 改為 user-ruling/已研究（收票後文檔同步，非本輪 blocking）。

---

## 必答 5 — §E E-1～E-7 殘留＋可否收票

### §E 逐條

| ID | 為何現在不做仍成立？ | R11 |
|---|---|---|
| E-1 | CI 已刪、client `--no-verify` 無遠端第二道 | **成立** |
| E-2 | small 視窗已凍結 v7；蓄意等價成本 | **成立** |
| E-3 | 語意蘊涵判準仍 needs-research（85 條回放門檻未做） | **成立** |
| E-4 | SPLITUNIFY B7 補裁決已派；真 audit 已清 | **可收** |
| E-5 | probe 證序判無增量（上） | **成立** |
| E-6 | synth↔SPEC 等價仍 needs-research | **成立** |
| E-7 | 治理腳本 scope 擴張留下一張治理票 | **成立** |

### 四閘實戰＋B1–B4 閉合

brief 所列 B1 契約拒收×3、B2 verdictgate 放行 B3/B4、B3 1c 放行 push、B4 synth hook 擋主委×1 — 與 HANDOFF 一致，本輪未重放真 audit。

### 可否收票

**否（blocked）** — P1 `COMPOSER-R11-P1-01`：closure-first 可跳過前批 C-4，與「不溯及既往」/批次邊界意圖衝突。其餘（legacy 語料、E-022～E-025、E-5、§E 多數）可接受；P1 修法後可再收票。

---

## COMPOSER-R11-P1-01

**斷言**: `verdictgate_check.sh` 之「本批已有審查輪」判定對**任意** `committee_round_open`（含 closure 首進、未開 review R1）即跳過前批驗證，使 B1 仍 blocked 時可 closure-first 進入 B2 並後續領 token。

**碼證**: `scripts/verdictgate_check.sh:48-53`（`startswith(pfx)` 無 `brief_kind` 過濾）；`gate.sh:957`／`committee_run.sh:433`（closure 不跑 verdictgate）；反例 `bash /tmp/vg-r11-fake-round-probe.sh` → Step B rc=1、Step D rc=0。RECHECK: 重跑 probe；加測試「B2 closure-first 後 B2 review 仍須驗 B1 blocked」期望 rc=1。

**來源摘要**: scripts/verdictgate_check.sh#e2bd25b73715

[MAJOR] 信心度=High。會怎麼失敗：主委（或誤操作）對仍 blocked 之前批派 B<N> closure 作首輪 ⇒ 該批標記已進入 ⇒ 同批 impl/review 不再驗前批 ⇒ C-4 批次邊界失效。修法：已進入＝存在同批 **`brief_kind=review`** 之 `round_open`（或 helper `kind_of==review`），closure-only 不算進入。

---

## §1 必查 11 類（摘要）

1. 矛盾/互斥：**有** — C-4 註解寫「審碼 R1 已驗前批」，實作卻含 closure-first（P1）
2–10. 其餘：**無 blocking**（收票審範圍）
11. 短命工：**無**

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R11-P1-01
CLOSED:
STATUS: DONE

---

ASSUMPTIONS_VERIFIED: `gen_fact_key_blocks --check` rc=0；E-5 probe ORDER-ALWAYS-HOLDS；closure-first 反例 probe Step B rc=1 / Step D rc=0；p2/p1 各 1 測試 passed。  
TESTS_RUN: `pytest tests/governance/test_verdictgate_p2.py::test_check_batch_already_entered_skips_prev_verdicts tests/governance/test_verdictgate_p1.py::test_12_closed_id_in_legacy_round_expected_output_accepted -q` → 2 passed；`bash handoffs/20260911-verdictgate-e5-probe.sh` → E5 PROBE ORDER-ALWAYS-HOLDS；`bash scripts/gen_fact_key_blocks.sh --check` → rc=0；`bash scripts/completeness_check.sh --single handoffs/20260912-verdictgate-x-review-r11-composer.md --family composer` → 見下。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀審查；probe 腳本僅 `/tmp`）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: handoffs/20260912-verdictgate-x-review-r11-composer.md  
TMP_CLEANUP: 保留 `/tmp/claude-501`、`/private/tmp/claude-501`；其餘本輪 probe workdir 由 trap 清理
