# VERDICTGATE B2 閉合確認輪（codex＋grok 各自重驗自己的 R1 P1）

brief-kind: closure
task-id: 20260911-VERDICTGATE-B2-REVIEW-R2
findings-round: R2

🔴 **這是閉合確認（closure），不是實作。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁跑 `tests/governance` 全套。**
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`；末段機械裁決塊必填；`CLOSED:` 只列**你自己**重驗後確認閉合之 ID；**請在檔內寫 `STATUS: DONE`**。

## 你要做的事（各家只看自己的兩條）
主委修法（commit 見 `git log -3`）：
- **J1**（`CODEX-R1-P1-01`／`GROK-R1-P1-01`）：`scripts/review_quorum_check.sh` 家族來源改兩層聯集（dispatch 尾碼＋`committee_output.family`／`output_path` 尾碼），大小寫不敏感；白名單仍由釘住之 case 行判。重跑你的反例：`bash scripts/review_quorum_check.sh 20260911-VERDICTGATE-B1 claude` 應 PASS 3 家。
- **J2**（`CODEX-R1-P1-02`／`GROK-R1-P1-02`）：`prev_review_resolve.sh` 對最大 K 回傳**全部** review prefix（逗號分隔、append 序）；`verdictgate_check.sh` 第三參數接受逗號清單、逐一判定、任一擋即擋。重跑：`bash scripts/prev_review_resolve.sh P16 6` 應含 `P16-B5-TASK31-REV`。🔴 **這偏離 SPEC ASSERT 字面**（`stdout=P16-B5-TASK31-REV` 單值）——主委判「同批多 prefix 是 SPEC 未預見之真實命名，採較嚴版」。請明確：接受此偏離（`CLOSED:`）或要求改回單值並說明如何不 under-block。
- J3／J4 亦已修（report 用 debt_clear 判 live；假綠斷言刪；committee_run 端到端兩測試）；J5 判 by-design 不改。

## 必答
1. 你的兩條在修後是否閉合（重跑反例）？
2. J2 之 SPEC 偏離：接受／不接受＋理由。
3. J1 修法把 `committee_output.family` 納入 quorum——這與該腳本檔頭「不信 audit family 欄」之 defense-in-depth 原則衝突嗎？主委立場：B1 起 family 由 gate.sh 依檔名尾碼＋roster 對證寫入，已不是「gate 推導」而是驗證後之值；legacy 列仍走尾碼推。給立場。
4. 可否收 B2？

## 交件形態
至少一個 canonical heading（零 findings 用 sentinel `## <FAMILY>-R2-P3-00`）；末段 `VERDICT:`／`BLOCKED-BY:`／`CLOSED:`；`STATUS: DONE`。

## 前提
fact-verified: 修後 `pytest tests/governance/test_verdictgate_p2.py` → 29 passed；`test_family_registry.py` 49 passed；`test_gate_impl_dispatch.py` 4 passed；mutation 12/12 UNCOVERED=0（主委 2026-09-11）。
fact-verified: 真 audit：quorum `20260911-VERDICTGATE-B1 claude` ⇒ PASS 3 家；`prev_review_resolve P16 6` ⇒ 8 個 prefix 含 `P16-B5-TASK31-REV`；report `live_roots_unwatched=`（空）。
fact-verified: `debt_ledger --has-open` rc=0（R1 債已清；派工後預期值: rc=1——本輪 OPEN，非 2）。
assumed: 三家皆無其他 caller 依賴 helper 之單值輸出（主委 grep `prev_review_resolve` 只有 gate.sh／committee_run.sh／checker／測試四處）⇒ 否證觀測：`grep -rn prev_review_resolve scripts tests` 出現第五處。／我跑了：**跑了**，四處。

## ⚠️ 前置
禁改碼；收尾清 /tmp workdir（保留 claude-501）。
