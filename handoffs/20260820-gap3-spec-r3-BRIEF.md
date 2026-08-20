# GAP-3 事件型 SPEC R3 閉合驗證（codex Y1–Y6）＋sentinel 確認

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。

## 審查標的
- `docs/GAP3_EVENT_SPEC.md` @ commit `c7ac693e`（sha256 `377c9a39b01e23b804fe7ea6fc88c9390abd1e992d6d2b47d9167d9abd521c07`）＝R2 修訂版。
- R2 收斂檔：`handoffs/reconcile/20260820-gap3-x-review-r2/synth.md`（Y1–Y6＋sentinel 節）。
- 真實 diff：`git diff 21135434..c7ac693e -- docs/GAP3_EVENT_SPEC.md`

## 工作（依家族分工）
- **codex（原提出方，章程 §B8）**：R2 六條（CODEX-R2-P1-01..06）逐條重跑原反例，判 CLOSED/NOT-CLOSED；並確認 R1 NOT-CLOSED 三條（P0-01/P1-03/P1-07）經 Y1/Y2+Y3/Y4+Y5 後之最終狀態。
- **composer/grok（sentinel 確認）**：驗 Y1–Y6 寫回是否忠實於 synth 處置、是否與 X1–X13 既有條文衝突、是否引入新錯（特別：D1-6 映射表 vs D2 六欄不變式、Y2 公式 vs 使用者 §2-4 原意、Y3 兩值集 vs JSON SoT 原則、Y6 accepted 集 vs §N-7）。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: R2 reconcile completeness PASS（8/8 heading、body-hash 合法；主委實跑） → rc=0
fact-verified: R2 修訂版 `template_check spec` PASS（主委 2026-08-20 實跑） → TEMPLATE PASS
assumed: Y1–Y6 寫回無語意漂移、Y2 預設值忠實於使用者 §2-4 原例 ← 請攻
assumed: Y6 之「同一 validator、accepted 三值＋platform_random_bars 恆拒」與 B3.2/§N-7 全文一致 ← 請攻

## 必答（逐條 verdict）
1. codex：六條閉合表＋R1 三條最終狀態。composer/grok：Y1–Y6 忠實度＋新錯掃描。
2. 可以進「三家 RECONCILE-STAMP＋使用者白話閘」嗎？（無實質 finding 請明寫 sentinel「0 findings」）

## 不受理範圍（同 R1/R2）
- 不受理「SPEC 應含實作碼」（含「fixture digest 應預先存在」——SPEC 已明寫誠實邊界：digest 是 receipt 非規格）；不受理重開已裁事項（U 系列、AR-1..6、X1–X13、Y1–Y6 已裁內容——除非碼證直接衝突，標 `RULING-CONFLICT`）；不受理回測層/ML 殼擴建；不受理防蓄意無限對抗。

## 產出
canonical 四欄 findings（無實質 finding ⇒ sentinel「0 findings」）＋閉合表/忠實度表＋**Verdict**。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
