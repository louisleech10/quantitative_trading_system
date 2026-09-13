# DOCROT X-REVIEW R3 — grok

task-id: 20260912-DOCROT-X-REVIEW-R3  
family: GROK  
findings-round: R3  
brief: `handoffs/20260912-DOCROT-X-REVIEW-R3-BRIEF.md`  
scope: 審 `_validate_anchors`／`emit_anchors` 本輪 diff（V1／V2 修法）有無新缺口；自證兩條 assumed；禁改碼。

---

## §0 挑戰前提

| 前提 | brief 標籤 | grok 重判 | 碼證 |
|---|---|---|---|
| 修後六檔治理測試 86 passed | fact-verified | **成立** | `venv/bin/python -m pytest tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_govb1_zero_findings.py tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_completeness_oracles.py tests/governance/test_completeness_selfcheck.py -q` → **86 passed** rc=0 |
| 三條新反例測試各對應 mutation 轉紅 | fact-verified（主委未逐一實跑） | **本輪重演成立** | (1) marker 正則放回裸 `/HISTORY-BEGIN/` → `test_bare_marker_literal_in_md_prose_is_not_history` **FAILED**（誤拒散文裸字面）；還原後 PASSED。(2) `NR >= want && NR <= want_end` 改回 `NR == want` → `test_range_anchor_spanning_history_rejected` **FAILED**（`:1-3` 變 rc=0）；還原後 PASSED。(3) 拿掉 `*.md` 閘＋裸正則 → 構造 open-window `.sh`（BEGIN 後、END 前之程式行）`--single` **rc=1**；HEAD 同檔 **rc=0** |
| 本 repo 所有 SPEC 之 HISTORY marker 皆為 `<!-- HISTORY-BEGIN -->` 註解形態 | assumed | **對 `docs/` 成立** | `grep -rn "HISTORY-BEGIN" docs/ \| grep -v '<!--'` → **0**；`grep -rn "HISTORY-BEGIN" docs/` → 恰 2 命中且皆為 `<!-- HISTORY-BEGIN -->`（`SPLITUNIFY_SPEC.D-001.md:199`、`D-002.md:329`）；`HISTORY-END` 同形 2 命中。無裸字面 SPEC ⇒ 修法不會把歷史區當活文 |
| 非 `.md` 目標無歷史區概念 | assumed | **契約成立；理論 fail-open 具名殘留、不阻收案** | ANCHOR 分支 `case "${path}" in *.md)` 非 md 直接 `continue`。構造 `scratchpad/.../hist.txt`（含 `<!-- HISTORY-BEGIN -->`）＋`CODE-ANCHOR: …/hist.txt:3` → HEAD `--single` **rc=0**（跳過判定）。`docs/`／`templates/` 無帶 HISTORY 之 `.txt`；emit 允許之非 md 副檔名在本 repo 無規範歷史區 ⇒ 不升 P0/P1 |

## 被當成事實的未驗證假設（§0）

- 「SPEC marker 皆 HTML 註解形態」→ **assumed 經 `docs/` grep 自證成立**（0 裸字面）。
- 「非 `.md` 無歷史區」→ **設計契約成立**；對 `.txt` 等理論上可放 HTML marker 的副檔名屬 fail-open 具名殘留（本 repo 無此類規範檔），**不列 finding**。

---

## 必答 1 — codex 兩反例閉合（本家獨立重跑）

| 反例 | 期望 | 本家實跑 | 閉合？ |
|---|---|---|---|
| `comment_anchor`：`.sh` 註解含 `HISTORY-BEGIN` 字面，anchor 指其後程式行 | rc=0 | `bash scripts/completeness_check.sh --single scratchpad/docrot-r3-grok-probe/comment_anchor_finding.md --family grok` → **rc=0**；另 `CODE-ANCHOR: scripts/completeness_check.sh:405` → **rc=0** | **閉合** |
| `range_anchor`：`hist_sandwich.md:1-3`（L1 活文、L3 HISTORY） | rc≠0 | 同路徑 `range_anchor_finding.md` → **rc=1**，stderr 含 `anchor 落在歷史段` 與 `:1-3`；對照 `:5-5` 全活文 → **rc=0** | **閉合** |

（R2 scratchpad 原檔名已不在；本家依 brief／synth 同構重現。正式閉合確認仍以原提出方 codex 為準。）

---

## 必答 2 — 兩條 assumed 自證

1. **SPEC marker 形態**：`grep -rn "HISTORY-BEGIN" docs/ | grep -v '<!--'` → **0**；全量 2／2 為註解形態。**成立。**
2. **非 `.md` 無歷史區**：見 §0 表；契約層成立，`.txt` 構造反例證 skip 行為，無規範檔受害。**不 BLOCKING。**

---

## 必答 3 — 本輪 diff 有無新缺口／可否收案進 stamp

**無新 BLOCKING／P0／P1 缺口。** 逐項：

- `.md` 限定：對齊「歷史區只存在於 Markdown」；程式檔註解字面不再誤拒（V1）。
- marker 只認 `<!--[[:space:]]*HISTORY-BEGIN[[:space:]]*-->`：涵蓋本 repo `docs/` 全部寫法；散文裸字面不誤觸（V1 第二牙）。
- `path:A-B`：`emit_anchors` 之 `(-[0-9]+)?`＋`want..want_end` 任一行落歷史即 FAIL；`:5-5` 綠、`:1-3` 紅（V2）。
- `## 沿革` 節：構造 `yange.md:3` → 仍 **rc=1**（未回歸）。
- 三條新反例測試均綠；mutation 承重後腳本已還原（`git diff --stat -- scripts/completeness_check.sh` 空）。

**可以收案並進 stamp 輪**（前提＝codex 同兩反例亦報閉合＋三家零 BLOCKING，與 r2 synth 結票條件一致）。

---

## §1 必查摘要

1. 矛盾：無（修法對齊 CODEX-R2-P1-01／02 處置）  
2. 漏項：無（`.md`＋註解形態＋range 三牙齊；沿革節仍在）  
3. 不可測：無（rc／pytest／mutation 皆可重跑）  
4–8. quant／OOM／cache／API：不適用  
9. 測試：86 passed；三 mutation 承重後還原  
10. Agent 可執行：封閉語法未改壞  
11. 短命工：無  

---

## GROK-R3-P3-00

**斷言**: 本輪逐項核對 `_validate_anchors`／`emit_anchors` 之 V1／V2 修法、兩條 assumed 自證、以及 comment／range 兩反例重跑後，無需阻擋收斂之 P0/P1 finding；本輪逐項核對後無 finding。

**碼證**: current block＝`scripts/completeness_check.sh:_validate_anchors` L390–410 與 `emit_anchors` L418–429；`git diff 684cba09..HEAD -- scripts/completeness_check.sh tests/governance/test_docrot_e3_brief_placeholder.py`。VERIFY：`docs/` HISTORY 裸字面 0 命中；comment_anchor／real_sh:405 `--single` rc=0；range `:1-3` rc=1、`:5-5` rc=0；`## 沿革` rc=1；六檔 pytest **86 passed**；mutation 裸正則→prose 紅、`NR==want`→range 紅、去 md＋裸正則→open-window sh 紅，皆已還原。核對依據＝上列命令與 §0／必答表，非空殼散文。

**來源摘要**: handoffs/20260912-DOCROT-X-REVIEW-R3-BRIEF.md#68bd2f72e560;handoffs/reconcile/20260912-docrot-x-review-r2/synth.md#c2b8b2a0837b;scripts/completeness_check.sh#ae8feeee8bdd;tests/governance/test_docrot_e3_brief_placeholder.py#9897a0297508

[NON-BLOCKING] 信心度=High。V1／V2 閉合；assumed 自證無 BLOCKING；建議三家零 BLOCKING 後進 stamp。具名殘留：非 `.md`（如 `.txt`）若未來放入 HTML HISTORY marker，現行會 skip 判定——本 repo 無此規範檔。

---

ASSUMPTIONS_VERIFIED: docs/ HISTORY 裸字面 0／註解形態 2；非 md skip＋.txt 構造 rc=0（契約殘留）；comment_anchor rc=0；range :1-3 rc=1／:5-5 rc=0；沿革 rc=1；86 passed；三 mutation 轉紅後還原。  
TESTS_RUN: 六檔 pytest → 86 passed rc=0；三條新反例單獨 PASSED；`--single` 探針見必答 1；mutation 見 §0。  
FAILURES_SEEN: none（mutation 為受控破壞，已還原；`git diff --stat -- scripts/completeness_check.sh` 空）  
SCOPE_CHANGES: none（禁改碼；僅 scratchpad 探針＋本交件＋/tmp）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE
