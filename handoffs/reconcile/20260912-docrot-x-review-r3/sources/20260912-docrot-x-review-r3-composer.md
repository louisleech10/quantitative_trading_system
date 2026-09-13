# DOCROT 審碼 R3 — COMPOSER

task-id: `20260912-DOCROT-X-REVIEW-R3`  
family: COMPOSER  
findings-round: R3  
brief: `handoffs/20260912-DOCROT-X-REVIEW-R3-BRIEF.md`  
scope: `_validate_anchors`／`emit_anchors` current block ＋ `git diff 684cba09..HEAD -- scripts/completeness_check.sh tests/governance/test_docrot_e3_brief_placeholder.py`；禁改碼。

---

## §0 挑戰前提

| 前提 | brief 標籤 | composer 重判 | 碼證 |
|---|---|---|---|
| 修後六檔治理 pytest 全綠 | fact-verified | **本輪重驗成立（89 passed）** | `venv/bin/python -m pytest tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_govb1_zero_findings.py tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_completeness_oracles.py tests/governance/test_completeness_selfcheck.py -q` → **89 passed** rc=0 |
| 本 repo 所有 SPEC 之 HISTORY marker 皆為 `<!-- HISTORY-BEGIN -->` 註解形態 | assumed | **成立（docs 零裸字面）** | `grep -rn "HISTORY-BEGIN" docs/ \| grep -v '<!--'` → **0 命中**；`docs/` 共 2 命中皆為 `<!-- HISTORY-BEGIN -->`（`SPLITUNIFY_SPEC.D-001.md`／`D-002.md`）；`specs/` 零命中 |
| 非 `.md` 目標無歷史區概念 | assumed | **成立（機械 skip＋探針）** | `_validate_anchors` L396 `case "${path}" in *.md) : ;; *) continue ;; esac`；`test_code_file_comment_marker_is_not_history` 指 `.sh:4`（註解含裸字面）⇒ `--single` rc=0 |

---

## 必答 1 — codex 兩反例閉合（composer 獨立重跑）

| 反例 | 預期 | composer 實跑 | 閉合？ |
|---|---|---|---|
| `comment_anchor_finding.md`（anchor 指 `scripts/completeness_check.sh:413`，scanner 註解含 `HISTORY-BEGIN` 字面、第 413 行為現行程式） | rc=0 | `bash scripts/completeness_check.sh --single scratchpad/docrot-r3-probe/comment_anchor_finding.md --family composer` → **rc=0**（`COMPLETENESS PASS`） | **是** |
| `range_anchor_finding.md`（`hist_sandwich.md:1-3`，第 1 行活文、第 3 行在 `<!-- HISTORY-BEGIN -->` 後） | rc≠0 | 同上路徑 `range_anchor_finding.md` → **rc=1**，stderr 含 `anchor 落在歷史段` 與 `:1-3` | **是** |

說明：R2 探針檔不在 repo；本家於 `scratchpad/docrot-r3-probe/` 依 r2 synth 附錄字面重建，ID 改為合法 `COMPOSER-R3-P1-99`／`P1-98` 並附 `**來源摘要**` digest 後重跑。行為與三條新增 pytest 一致。

---

## 必答 2 — 兩條 assumed 自證

1. **HTML 註解 marker 涵蓋本 repo SPEC**  
   - 命令：`grep -rn "HISTORY-BEGIN" docs/ | grep -v '<!--'`  
   - 命中數：**0**（`docs/` 全庫 2 處 marker 皆為 `<!-- HISTORY-BEGIN -->`）  
   - 補充：`templates/` 有 4 處**敘述性**裸字面（規則說明），非實際歷史區 marker；不構成 fail-open。

2. **非 `.md` 不判歷史**  
   - 機械：`scripts/completeness_check.sh:396` 僅 `*.md` 進入 HISTORY awk。  
   - 端到端：`test_code_file_comment_marker_is_not_history` PASSED；comment_anchor 探針指 `.sh` 內 scanner 行 rc=0。

---

## 必答 3 — 本輪 diff 新缺口審查

| 變更點 | 審查結論 |
|---|---|
| L396 `.md` 限定 | 正確閉合 CODEX-R2-P1-01；不對 `.py`／`.sh` 誤判 |
| marker 正則改 `<!--[[:space:]]*HISTORY-BEGIN[[:space:]]*-->` | 與 repo 實際 marker 一致；`test_bare_marker_literal_in_md_prose_is_not_history` 防 fail-open |
| `emit_anchors` 吃 `path:A-B`＋`want..want_end` 區間 | 正確閉合 CODEX-R2-P1-02；`test_range_anchor_spanning_history_rejected` 紅／全活文 `:5-5` 綠 |
| 三條反例測試 | 各 docstring 所述 mutation 與行為對齊；未見表外機制或弱化 |

**未見本輪 diff 引入之新 BLOCKING 缺口。**

---

## mutation 承重（本輪重演 ≥1）

| 破壞 | 命令 | 實測 |
|---|---|---|
| 還原 range 判定為 `NR == want`（只查起點） | 拷貝 `/tmp/completeness_check_mut3.sh` 改 awk 後跑 `range_anchor_finding.md --single` | **rc=0**（應 rc≠0）⇒ 現行修法承重 |
| 三條 R3 反例 pytest | `pytest …::test_code_file_comment_marker_is_not_history …::test_bare_marker_literal_in_md_prose_is_not_history …::test_range_anchor_spanning_history_rejected` | **3 passed** rc=0 |

拷貝腳本僅在 `/tmp`；主 repo `scripts/completeness_check.sh` 未改。

---

## §1 必查摘要

1. 矛盾：無（diff 與 r2 synth V1／V2 處置一致）  
2. 漏項：無（反例測試覆蓋兩條 P1 修法）  
3. 不可測：無（rc／pytest 可重跑）  
4–8. quant／OOM／cache／API：不適用  
9. 測試：89 passed；range mutation 轉綠證承重  
10. Agent 可執行：是  
11. 短命工：無  

## 被當成事實的未驗證假設（§0）

brief 兩條 assumed 已上表重判並自證；無需另列 blocking finding。

---

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——codex R2 兩條 P1 修法已閉合、兩條 assumed 自證成立、本輪 diff 未引入新缺口。

**碼證**: current block＋`git diff 684cba09..HEAD` 對照 `handoffs/reconcile/20260912-docrot-x-review-r2/synth.md` V1／V2；comment_anchor 探針 rc=0、range_anchor 探針 rc=1；`grep -rn "HISTORY-BEGIN" docs/ | grep -v '<!--'` → 0；`venv/bin/python -m pytest tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_govb1_zero_findings.py tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_completeness_oracles.py tests/governance/test_completeness_selfcheck.py -q` → 89 passed rc=0；range mutation 拷貝腳本 rc=0（ regression 證承重）。

**來源摘要**: handoffs/20260912-DOCROT-X-REVIEW-R3-BRIEF.md#68bd2f72e560;scripts/completeness_check.sh#ae8feeee8bdd;handoffs/reconcile/20260912-docrot-x-review-r2/synth.md#probe

[NON-BLOCKING] 信心度=High。建議待 codex 家族正式交件確認同一兩 rc 後，三家零 BLOCKING 可進 stamp 輪。

---

ASSUMPTIONS_VERIFIED: docs 裸 marker 0 命中；非 .md skip＋sh 探針 rc=0；codex 兩反例 composer 重跑閉合；range mutation 轉綠。  
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_govb1_zero_findings.py tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_completeness_oracles.py tests/governance/test_completeness_selfcheck.py -q` → 89 passed rc=0；`bash scripts/completeness_check.sh --single scratchpad/docrot-r3-probe/comment_anchor_finding.md --family composer` → rc=0；`bash scripts/completeness_check.sh --single scratchpad/docrot-r3-probe/range_anchor_finding.md --family composer` → rc=1；三條 R3 pytest → 3 passed。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼；scratchpad 探針與 /tmp 拷貝腳本）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:  
STATUS: DONE
