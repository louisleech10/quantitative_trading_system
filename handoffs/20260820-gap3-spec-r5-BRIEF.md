# GAP-3 事件型 SPEC R5 終輪閉合（codex W1）＋sentinel

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。

## 審查標的
- `docs/GAP3_EVENT_SPEC.md` @ commit `a8bb7634`（sha256 `57a429d18129ad15c0e0eba5d3d6e2a96d820b9b8e335972c22fa23c95879098`）＝R4 修訂版。
- R4 收斂檔：`handoffs/reconcile/20260820-gap3-x-review-r4/synth.md`（W1＋sentinel 節）。
- 真實 diff：`git diff 3b254e2f..a8bb7634 -- docs/GAP3_EVENT_SPEC.md`（單縫修補）

## 工作（終輪）
- **codex（原提出方）**：W1（CODEX-R4-P1-01）重跑原反例判 CLOSED/NOT-CLOSED；給 R1 P0-01 最終狀態。
- **composer/grok（sentinel）**：驗 W1 寫回忠實（D2-1 三段鏈／receipt 三新欄／§G-2 組合案例）、與 X/Y/Z 既有條文無衝突、無新錯。grok 另請確認：R3 貴家「五語意皆滿足 entry_at ≤ label_start」之判斷已被 W1 更正——認可或提出反碼證。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: R4 reconcile completeness PASS（3/3 heading）＋債銷帳（主委實跑） → rc=0
fact-verified: R4 修訂版 `template_check spec` PASS（主委 2026-08-20 實跑） → TEMPLATE PASS
assumed: 三段鏈拆分後無其他條文仍隱含 `entry_at ≤ label_start` ← 請攻（全文掃）
assumed: `label_start` 依 mode 機械定義與 D1-5 label 錨不變式相容 ← 請攻

## 必答（逐條 verdict）
1. codex：W1 閉合判定＋R1 P0-01 最終狀態。composer/grok：忠實度＋新錯掃描。
2. 可以進「三家 RECONCILE-STAMP＋使用者白話閘」嗎？（無實質 finding 請明寫 sentinel「0 findings」）

## 不受理範圍（同 R1–R4）
- 不受理「SPEC 應含實作碼」「digest 應預寫」；不受理重開已裁事項（U／AR／X／Y／Z／W1 裁定內容——碼證直接衝突標 `RULING-CONFLICT`）；`drop_threshold` x 值＝白話閘議題不受理；不受理回測層/ML 殼擴建；不受理防蓄意無限對抗。

## 產出
canonical 四欄 findings（無實質 ⇒ sentinel「0 findings」）＋閉合表＋**Verdict**。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
