# DOCROT Task 1.1–1.8 實作 — 三家審碼輪 R3（閉合 codex R2 兩條 P1）

brief-kind: review
task-id: `20260912-DOCROT-X-REVIEW-R3`
findings-round: R3

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行；findings 用 `## <FAMILY>-R3-P<0-3>-<NN>`。
🔴 P0／P1 之 `**碼證**` 必含 `CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行破壞>`（Task 1.6 已生效，缺則交件被拒）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 非 gating 檔；勿 STAMP-BLOCK。本輪 **review**，**禁改碼**。
- review-r2 收斂：`handoffs/reconcile/20260912-docrot-x-review-r2/synth.md`（V1／V2 採納並修；V3 兩家零 finding）。

## 任務
1. **codex（原提出方，章程 §B8 閉合確認）**：重跑你 R2 的同一兩個反例——`comment_anchor_finding.md`（anchor 指程式檔中含 `HISTORY-BEGIN` 註解字面之後的程式行）須 **rc=0**；`range_anchor_finding.md`（`hist_sandwich.md:1-3`，第 1 行活文、第 3 行 HISTORY）須 **rc≠0**。附實跑 rc。若任一未閉合 ⇒ BLOCKING。
2. **三家**：審本輪 diff 有無引入新缺口（例：`.md` 以外目標一律不判歷史是否過寬；`<!-- HISTORY-BEGIN -->` 註解形態是否涵蓋本 repo 全部 SPEC 之 marker 寫法——請 `grep -rn "HISTORY-BEGIN" docs/ | grep -v '<!--'` 自證）。
3. 三家：可否收案並進 stamp 輪。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：`scripts/completeness_check.sh:_validate_anchors`（ANCHOR 分支之 `.md` 限定、marker 正則、`want..want_end` 區間）與 `emit_anchors`（`(-[0-9]+)?` 與起訖拆分）；`tests/governance/test_docrot_e3_brief_placeholder.py` 新增三條反例測試。
- **本輪 diff**：`git diff 684cba09..HEAD -- scripts/completeness_check.sh tests/governance/test_docrot_e3_brief_placeholder.py`
- 🔴 **不在範圍**：Task 1.1–1.5、1.7、1.8（R2 三家已對表通過，不重審）；`docs/*` HISTORY 區。

## 本 brief 前提
fact-verified: 修後 `tests/governance/test_docrot_e3_brief_placeholder.py`＋`test_govb1_zero_findings.py`＋`test_docrot_f2_total_items_count.py`＋`test_docrot_claim_committee_backing.py`＋`test_completeness_oracles.py`＋`test_completeness_selfcheck.py` → 86 passed（主委實跑）。
fact-verified: 三條新反例測試各對應一項 mutation（拿掉 `.md` 限定／marker 正則放回裸字面／`(-[0-9]+)?` 拿掉或 `NR == want` 復原）⇒ 轉紅——寫在測試 docstring，主委**未**逐一實跑 mutation（本輪請至少一家重演其一並附 rc）。
assumed: 本 repo 所有 SPEC 之 HISTORY marker 皆為 `<!-- HISTORY-BEGIN -->`／`<!-- HISTORY-END -->` 註解形態（允許 `<!--` 與字面間空白）。請直接攻：若有裸字面 marker 的 SPEC，本修法會把該檔歷史區當活文（fail-open），須 BLOCKING。
assumed: 非 `.md` 目標無歷史區概念。請攻。

## 必答（逐條 verdict）
1. codex：兩反例重跑 rc（閉合／未閉合）。
2. 兩條 assumed 之自證結果（附 grep 命令與命中數）。
3. 可以收案進 stamp 輪嗎？

## 產出
canonical 四欄 findings（或零 findings sentinel）＋ **Verdict**。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
