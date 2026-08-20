# GAP-3 事件型 SPEC R4 終輪閉合（codex Z1–Z4）＋sentinel

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。

## 審查標的
- `docs/GAP3_EVENT_SPEC.md` @ commit `3b254e2f`（sha256 `d65745d4962bca23b27b5d373bdc281bc47f3724e0cf0898a85f6aa86f2d5ec6`）＝R3 修訂版。
- R3 收斂檔：`handoffs/reconcile/20260820-gap3-x-review-r3/synth.md`（Z1–Z4＋sentinel 節）。
- 真實 diff：`git diff c7ac693e..3b254e2f -- docs/GAP3_EVENT_SPEC.md`（窄縫修補，diff 很小）

## 工作（依家族分工；本輪＝終輪閉合）
- **codex（原提出方）**：Z1–Z4（CODEX-R3-P1-01..04）逐條重跑原反例判 CLOSED/NOT-CLOSED；並給 R1 P0-01／P1-03／P1-07 之最終閉合狀態。
- **composer/grok（sentinel）**：驗 Z1–Z4 寫回忠實、無新錯（特別：D2-4 兩層 receipt vs 六欄不變式；Z2 fail-closed 語意——c 類不啟用時分類覆蓋是否仍自洽；M8 三道硬檢 vs B1.4 定式一致）。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: R3 reconcile completeness PASS（6/6 heading）＋債銷帳（主委實跑） → rc=0
fact-verified: R3 修訂版 `template_check spec` PASS（主委 2026-08-20 實跑） → TEMPLATE PASS
assumed: Z2 之 fail-closed（drop_threshold 未設 ⇒ c 判定不啟用）不會使 a/b/unclassifiable 覆蓋出現歧義 ← 請攻
assumed: Z1 兩層 receipt schema 與 §G-2 三形 oracle 對得上 ← 請攻

## 必答（逐條 verdict）
1. codex：Z1–Z4 閉合表＋R1 三條最終狀態。composer/grok：Z 寫回忠實度＋新錯掃描。
2. 可以進「三家 RECONCILE-STAMP＋使用者白話閘」嗎？（無實質 finding 請明寫 sentinel「0 findings」）

## 不受理範圍（同 R1–R3）
- 不受理「SPEC 應含實作碼」「digest 應預寫」；不受理重開已裁事項（U 系列、AR、X、Y、Z 已裁內容——碼證直接衝突標 `RULING-CONFLICT`）；**`drop_threshold` 之 x 值屬使用者白話閘議題，不受理再攻其無預設**；不受理回測層/ML 殼擴建；不受理防蓄意無限對抗。

## 產出
canonical 四欄 findings（無實質 ⇒ sentinel「0 findings」）＋閉合表＋**Verdict**。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
