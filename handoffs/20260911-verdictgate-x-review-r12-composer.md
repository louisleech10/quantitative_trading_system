# VERDICTGATE 收票審閉合 R12 — COMPOSER

brief-kind: closure
task-id: 20260911-VERDICTGATE-X-REVIEW-R12
family: composer
findings-round: R12
brief: `handoffs/20260912-VERDICTGATE-X-CLOSEOUT-R2-BRIEF.md`
review-target: 重驗本家 R11 P1（`COMPOSER-R11-P1-01`）修法閉合＋S2 登記表行號＋SPEC C-4 延後立場＋B-62 收票裁決

RECONCILE-STAMP: composer APPROVED 2026-09-12 sha256:ef26cc61b1e89eab25a448ad54e595062f0efb3281f7ed92120d77d44fd9376b task:20260911-VERDICTGATE-X-REVIEW-R12

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | R12 判定 |
|---|---|---|
| 修後 `test_verdictgate_p2.py` 31 passed | fact-verified | **成立** — 本輪重跑 31 passed rc=0 |
| mutate-b2 UNCOVERED=0 | fact-verified | **成立** — `venv/bin/python handoffs/20260911-verdictgate-mutate-b2.py` → UNCOVERED=0 rc=0 |
| 真 audit `verdictgate_check 20260911-VERDICTGATE 4` ℹ、`20260911-SPLITUNIFY 8` ✓ | fact-verified | **成立** — b4 印「本批已有 review 輪」rc=0；b8 ✓ roster 全裁決 rc=0 |
| R11 債已清 | fact-verified | **未重跑** `debt_ledger --has-open`；沿用 brief 前提 |

---

## 必答 1 — 本家 R11 P1 修後是否閉合？

**立場：已閉合。**

| 反例步驟 | 碼證 | rc |
|---|---|---|
| B1 codex blocked、無 B2 review | `bash /tmp/vg-r12-entered-probe.sh` → `b1_blocked=1` | 1 |
| 只 append `ROOT-B2-CLOSURE-R1` round_open | 同上 → `closure_only=1` | 1 |
| append 被 abandon 之 `ROOT-B2-REVIEW-R1` | 同上 → `abandoned_review=1` | 1 |
| append 未 abandon legacy review `ROOT-B2-REVIEW-R2` | 同上 → `legacy_review=0` | 0 |
| 回歸測試 | `pytest tests/governance/test_verdictgate_p2.py::test_check_sole_closure_round_does_not_count_as_entered -q` | 1 passed |
| 全套 p2 | `pytest tests/governance/test_verdictgate_p2.py -q` | 31 passed |
| mutate M4b／M4c／M4d | `venv/bin/python handoffs/20260911-verdictgate-mutate-b2.py` | UNCOVERED=0 |

修法落地於 `scripts/verdictgate_check.sh:38-67`：`brief_kind=review` 或 legacy review-like 且未 `debt_abandon` 才算「已進入」；closure／consult 首進不再跳過前批。R11 `COMPOSER-R11-P1-01` 所述 closure-first 縫已封堵。

---

## 必答 1b — 本家 R11 P2（登記表行號）

**立場：composer R11 無獨立 P2 finding；S2 主委修法已落地，登記屬實。**

| ID | 登記行 | 實際可執行點 | 判定 |
|---|---|---|---|
| E-022 第二層 | `gate.sh:959` | `verdictgate_check.sh` 呼叫 | **屬實** |
| E-023 | `gate.sh:959` | 同左 | **屬實** |
| E-024 push 端 | `ticket_batch_check.sh:88` | `--push-range)` 分支 | **屬實** |

RECHECK: `bash scripts/gen_fact_key_blocks.sh --check` → rc=0；`sed -n '959p' scripts/gate.sh`；`sed -n '88p' scripts/ticket_batch_check.sh`。

---

## 必答 2 — SPEC C-4 字面修訂延後至下張治理票

**立場：接受。**

理由：R11 已確認語意（SPLITUNIFY 補裁決＋不溯及既往）與實作（只擋進入新批、只認 review 輪）一致；SPEC v9 已 FROZEN 且使用者 2026-09-11 裁定停輪。收票內以 synth＋HANDOFF 記錄範圍註記，併入 §E E-7 下張治理票一行同步 SPEC Task 2.2，成本低於重開 FROZEN 修訂程序（三家審＋使用者裁定）。**不接受**之最小路徑＝走 FROZEN 修訂＋新 stamp 輪（≥1 輪），本輪無必要。

---

## 必答 3 — 可否收票（B-62 結案）

**立場：可收票。**

本家阻塞項 `COMPOSER-R11-P1-01` 已閉合；S2 行號修正可核；§E E-8（registry 語意對位）為 needs-research 不阻收票。待三家 R12 皆 `proceed` 且 CLOSED 本家 R11 ID 後，B-62 可結案。

---

## COMPOSER-R12-P3-00

**斷言**: 本輪逐項核對後無新 finding；R11 `COMPOSER-R11-P1-01` 修法已閉合，sentinel 為實質複驗摘要。

**碼證**: `bash /tmp/vg-r12-entered-probe.sh` → `b1_blocked=1 closure_only=1 abandoned_review=1 legacy_review=0` probe_rc=0；`pytest tests/governance/test_verdictgate_p2.py -q` → 31 passed；`venv/bin/python handoffs/20260911-verdictgate-mutate-b2.py` → UNCOVERED=0；`bash scripts/gen_fact_key_blocks.sh --check` → rc=0；`bash scripts/verdictgate_check.sh 20260911-VERDICTGATE 4 20260911-VERDICTGATE-B3-REVIEW` → ℹ review 輪 rc=0。RECHECK: 重跑上述命令。

**來源摘要**: handoffs/reconcile/20260912-verdictgate-x-review-r11/synth.md#ef26cc61b1e8;scripts/verdictgate_check.sh#501ae3507cf0

正文：核對依據＝brief S1/S2 主委修法＋本家 R11 P1 反例腳本；不捏造新缺陷。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R11-P1-01

---

ASSUMPTIONS_VERIFIED: HEAD `501ae350`；S1 四步反例 rc 1/1/1/0；p2 31 passed；mutate-b2 UNCOVERED=0；gen_fact_key_blocks --check rc=0；真 audit b4 ℹ、b8 ✓。
TESTS_RUN: `bash /tmp/vg-r12-entered-probe.sh` → probe_rc=0；`venv/bin/python -m pytest tests/governance/test_verdictgate_p2.py -q` → 31 passed rc=0；`venv/bin/python handoffs/20260911-verdictgate-mutate-b2.py` → UNCOVERED=0 rc=0；`bash scripts/gen_fact_key_blocks.sh --check` → rc=0；`bash scripts/verdictgate_check.sh 20260911-VERDICTGATE 4 20260911-VERDICTGATE-B3-REVIEW` → rc=0；`bash scripts/verdictgate_check.sh 20260911-SPLITUNIFY 8 20260911-SPLITUNIFY-B7-REVIEW` → rc=0；`bash scripts/completeness_check.sh --single handoffs/20260911-verdictgate-x-review-r12-composer.md --family composer` → 見下。
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查；probe 僅 `/tmp`）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-x-review-r12-composer.md
TMP_CLEANUP: 已刪 `/tmp/vg-r12-entered-probe.sh`、`/tmp/vg-r12-harness`；保留 `/tmp/claude-501`、`/private/tmp/claude-501`

STATUS: DONE
