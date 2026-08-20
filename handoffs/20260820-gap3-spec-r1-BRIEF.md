# GAP-3 事件型 SPEC 初稿 adversarial review R1

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。

## 審查標的
- `docs/GAP3_EVENT_SPEC.md` @ commit `e0af4a3d`（sha256 `d0babfea8f2412fe2a68aa69af8b8adf71b3152f8d6a1e7301b5c7ffca32f7bd`）。
- 取材地圖（審查的對照基準）：`白話說明/GAP-3事件型討論.md` 第 12 版 **§7.5 五層優先序**；layer 3 = `handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md`（C1–C9）；layer 4 = `handoffs/reconcile/20260819-gap3-x-consult-r1/synth.md`（只取 R2 未覆蓋者）。

## 第一項工作（強制；先做完才做一般 adversarial）
拿 §7.5 五層清單**逐條**比對 SPEC，產「layer 條目 × SPEC 節」對應表，逐條判：
- **沒漏**：該取的（U1–U13＋8/20 五點、J1–J10、R2 C1–C9、R1 六時間欄/ms 閘/taxonomy/legacy 不沿用清單、第 5 層契約 pointer）在 SPEC 有落點。
- **沒錯**：SPEC 條文與來源語意一致（特別驗 §0 D1–D4 是否忠實合併「R2 C1–C4 ⊕ 8/20 增補」——U4b 把 C1 的 A/B 預設 `open_to_horizon_close` 改成 `close_to_close`、K1/K2 加 t₀−k）。
- **沒被舊結論污染**：R1 之 C-情境反例結論、舊 `CaseRecord`／`_select_negative_timestamps` 語意、「換時間戳即可共用 IC」舊句不得滲入；衝突時**新使用者意圖蓋過舊委員結論**。

## 第二項工作：裁 AR-1..AR-6（SPEC §A「待對抗審確認」塊；逐項給裁決＋理由＋碼證）
AR-1 決策時點 t₀−k 之契約形式；AR-2 反例自動分類規則之契約化；AR-3 多標的必要化與 registry #4 邊界；AR-4 一份 SPEC vs 拆兩份；AR-5 產生器 G1–G6 落批（預設 B3 vs MVP 前移 B2）；AR-6 label 一致性探針（B1 可選 task vs §N 殘留）。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: SPEC §A 之 15 條 FACT-RECEIPT 為主委 2026-08-20 實跑（命令與輸出摘要在 SPEC §A，可逐條重跑複驗） → 實跑 `sed/grep` 見 SPEC §A 各條
fact-verified: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → TEMPLATE PASS（主委 2026-08-20 實跑）
assumed: R2 synth C1–C9 是 K1–K10 技術定案的完整且正確表述，SPEC 引用時無斷章 ← 請直接攻這條（對照 synth 原文逐群集驗）
assumed: SPEC §P 十六個 Task 之依賴宣告無 forward dependency、「存活至/覆蓋風險」語意正確 ← 請攻（範本出生事故＝Phase 1 產出被 Phase 3 刪）

## 必答（逐條 verdict）
1. §7.5 逐條比對表：漏了什麼？錯了什麼？被舊結論污染處？
2. AR-1..AR-6 逐項裁決。
3. §0 D1–D4 作為「最完整精確合併點」是否成立（嚴謹、可驗收、無歧義）？
4. §N 八條殘留之三值理由是否成立（有無「該現在做卻被推遲」的偷懶項）？
5. §G/§V 之 golden 與 mutation 設計可證偽嗎（M1–M8 是否真能抓改壞）？
6. 可以進 reconcile＋白話閘嗎，還是有 BLOCKING 必須先修？

## 不受理範圍（審查有終點；95% 條款）
- 不受理「SPEC 應含實作碼／某腳本尚不存在」類 BLOCKING（範本明文：那是 Task 未實作的正常狀態，正確回應＝寫進 §V 驗收）。
- 不受理重開使用者已裁之產品語意（U1–U13＋8/20 五點）；若認為 U 系列與碼證衝突，標 `USER-CONFLICT` 供白話閘轉呈，勿當 BLOCKING。
- 不受理回測層/ML 殼擴建提案（成熟度地圖禁區）；不受理「防蓄意」框架之無限對抗（只審意外錯誤與遺漏）。

## 產出
canonical 四欄 findings + 「§7.5 逐條對應表」+ AR-1..AR-6 裁決節 + **Verdict**。**禁改碼**（只產 review 檔）。收尾清 /tmp workdir（保留 claude-501）。
