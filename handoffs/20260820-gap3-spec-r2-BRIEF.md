# GAP-3 事件型 SPEC R2 閉合驗證＋殘餘 sweep

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。

## 審查標的
- `docs/GAP3_EVENT_SPEC.md` @ commit `21135434`（sha256 `9f63e290e89a1dde96b44c217866d01d0113b0dc47f19b5acd0a7e356459f5bf`）＝R1 修訂版。
- R1 收斂檔（處置的權威）：`handoffs/reconcile/20260820-gap3-x-review-r1/synth.md`（十三群集 X1–X13＋AR-1..AR-6 裁決）。
- 真實 diff：`git diff e0af4a3d..21135434 -- docs/GAP3_EVENT_SPEC.md`

## 第一項工作（強制）：R1 findings 逐條閉合驗證（章程 §B8——原提出方重跑同一反例）
你在 R1 提出的每條 finding（見 `handoffs/20260820-gap3-spec-r1-<你的家族>.md`），逐條：
1. 重跑你原本的反例/probe（sed/grep 對修訂版 SPEC）。
2. 判 `CLOSED`（處置忠實落地且可證偽）或 `NOT-CLOSED`（附新碼證）。
3. 同時驗 synth X1–X13 處置 vs SPEC 條文**逐字忠實**（主委抄寫漂移是已知病，抓它）。

## 第二項工作：殘餘 sweep（修訂是否引入新錯）
重點面：D1-5 label 錨不變式與 D2-2 offset 表示法的內部一致；B1 批內順序（B1.6 插入後）；X6 共同約束與各 Task 驗證的一致；M1–M12 可證偽性；§N-7/8 改寫後三值理由成立。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: R1 reconcile completeness PASS（15/15 ID、body-hash 合法；主委實跑 `completeness_check.sh --lock`） → rc=0
fact-verified: 修訂版 `template_check spec` PASS（主委 2026-08-20 實跑） → TEMPLATE PASS
assumed: 主委把 X1–X13 寫回時無語意漂移、無漏寫 ← 請直接攻這條（synth 處置逐字 vs SPEC diff）
assumed: AR 裁決收斂（decision_offset_bars int≥0 無負號版／unclassifiable 不猜／cluster_weight=1/n）與各家 R1 原意相容 ← 請攻

## 必答（逐條 verdict）
1. 你的 R1 findings 逐條 CLOSED/NOT-CLOSED 表。
2. X1–X13 寫回忠實嗎？漂移處列出。
3. 新引入錯誤？
4. 可以進「三家 RECONCILE-STAMP＋使用者白話閘」嗎，還是有 BLOCKING/MAJOR 必須再修？

## 不受理範圍（同 R1）
- 不受理「SPEC 應含實作碼」；不受理重開已裁事項（U 系列、AR-1..AR-6 已裁定內容——除非與碼證直接衝突，標 `USER-CONFLICT`/`RULING-CONFLICT` 供轉呈）；不受理回測層/ML 殼擴建；不受理防蓄意框架之無限對抗。

## 產出
canonical 四欄 findings（無新 finding 則明寫 sentinel「0 findings」）＋閉合表＋**Verdict**。**禁改碼**（只產 review 檔）。收尾清 /tmp workdir（保留 claude-501）。
