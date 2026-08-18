# GAP-2a／2b SPEC adversarial 審查 R2（R1 六群集修訂之複核＋殘留攻擊）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行。findings 用 canonical ID `## <FAMILY>-R2-P<0-3>-<NN>`；四欄含 `**來源摘要**: <路徑>#<sha256 前 12 碼>`。本輪輪次=R2。
若你確認 0 個實質 finding，寫 sentinel `## <FAMILY>-R2-P3-00`（body 四欄照填，內容為「逐項核對後無 finding」＋核對依據）。

## 審查標的
- **SPEC（R1 修訂版）**：`docs/GAP2_MARGINAL_IC_SPEC.md`（`template_check spec` PASS）
- **R1 收斂檔**：`handoffs/reconcile/20260818-gap2-x-review-r1/synth.md`（K1–K6 六群集＝本輪必核之修訂義務）
- 你 R1 的 review：`handoffs/20260818-gap2-specadv-<你的家族>.md`
- 偵察收斂：`handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md`

## ⚠️ 前置說明
- SPEC 審查非實作審查；禁改碼、禁改 SPEC；只產你自己的 review 檔。
- 使用者已裁定不受理重議：2a／2b 拆分、橋本體 blocked、技術取捨交委員會、GAP-3 另票。

## R1 修訂摘要（請逐條核對是否真的閉合，且未引入新洞）
- K1 批次時序：`ic_survivor_contract.json` 移至 **B1 Task 1.0**（SoT 先行；B1／B2 dataclass 直接讀契約對照，刪除檔內常數過渡）；`ic_report_contract.json` 之 `report_sections.marginal_ic`／`reasons`／`metadata.survivor_output_keys` **全部移至 B4 Task 4.1 與 orchestrator 組裝同 commit**；B3 只剩 resolver／validator／`build_survivor_output`。
- K2 oracle：§G 新增「合成產生器規格表」（seed／n／係數／噪聲／mask 切法寫死）；O8 改 `composite_ic == sign(train_ic_f)·gross_ic_f`；O1 拆 O1a（`x³`⇒`residual_degenerate`）／O1b（`tanh`⇒degenerate 或 ≤0.02）且 **gate 先於 Spearman 為硬約束**；O4 釘等 ρ=0.3、Var(y)=1、帶 `[0.90,1.10]`＋`composite_ic∈[0.55,0.61]`＋各 marginal∈[0.26,0.31]；O5 統一 `z_{1−α/(2k)}/√n_test` Bonferroni；Task 1.2-⑨ 改「`|survivors|=1` ⇒ S_f=∅」。
- K3 `fit_scope: Literal["train","full_sample"]` 為 `compute_marginal_ic`／`combine_factors` 必填 typed 輸入；`fit_scope="train"` 而 masks 全 True ⇒ raise；三路徑 oracle。
- K4 契約補 `symbol`／`timeframe`／`case_id`（頂層必填）、`sample_scope.event.timestamps_hash`（pop 前算）、`oos_semantics` 唯一字面（消費端須同讀四欄）；`ic_retained_ratio = marginal_ic/gross_ic` 保留符號；Task 3.1 改法段改題為「C4 checklist 義務項」並加驗證⑭（checklist ⊆ 契約鍵集）。
- K5 mutation V-18（shuffle-S）／V-19（symbol tamper）／V-20（feature_set_hash tamper）／V-21（O1 gate 順序）；共 21 條。
- K6 Task 4.1 驗證⑩ cache-hit `refilter` 刷新斷言＋⑪ `test_r6` 同 commit 綠。

## 本 brief 前提（逐條標；優先攻 assumed）
fact-verified: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`（Claude 實跑 2026-08-18）
fact-verified: R1 三家 verdict 皆「需修補後派工」；14 findings 全部接受並寫回（無駁回）
assumed: O4 等 ρ 推導（母體 Pearson `Σmarg²/composite²=k·Σρ²/(Σρ)²=1`）與 Spearman 帶 `[0.90,1.10]`、`composite_ic∈[0.55,0.61]`、marginal∈[0.26,0.31] 在 n=20000／seed=20260818／前 60% train 下**不假紅** ← 請實跑產生器規格表之 O4／O1a／O1b／O2／O7 並貼值
assumed: O5 Bonferroni 門檻 `z_{1−α/(2k)}/√n_test` 於 O5 產生器（O2 因子、test 段置亂）下三因子皆過且 mutation（去 gate）會紅 ← 請攻
assumed: Task 1.0 之 `reasons_ref` 指向 B4 才存在的 `ic_report_contract.json#reasons.marginal_ic` —— 「B4 落地前允許 ref 目標缺席但 resolver 於 B4 後必 fail-closed」這條是否構成 B1 對 B4 的 forward dependency 或 fail-open 窗 ← 請攻並給替代（例：reason 字面亦住 survivor 契約、report_contract 以 ref 反指）
assumed: 五批 B1(1.0–1.3)→B2→B3→B4→B5 現已無 forward dependency 且各批單獨綠 ← 請逐批模擬既有測試（`test_ichc_contract_sync`、`test_ichc_wiring_check`、persist redirect）
assumed: `symbol`／`timeframe` 篡改檢查（Task 3.1 ⑮）以 `report_ref` 對照報告 metadata 可行——報告 metadata 現有無 `symbol`／`timeframe` 欄？若無，checker 拿什麼比？ ← 請實核 `_build_report_metadata`（orch :3690-3747）並給修法

## 必答（逐條 verdict）
1. K1–K6 逐群集：閉合？未閉合處引 SPEC 行號。
2. 新引入之風險：修訂是否造成新矛盾（例：Task 1.0 與 3.1 之分工、`reasons_ref` 缺席窗、Task 3.1 ⑮ 對照來源）。
3. §G 產生器規格表：每個 oracle 的期望值／容差是否可由參數推導；請貼你的實跑值。
4. §V 21 條 mutation：是否每條都對映到具體測試斷言且改壞必紅；仍缺者列出。
5. 可進 TODO？BLOCKING 清單。

## Time-box 與範圍紀律
- 優先序＝必答 1 ＞ 2 ＞ 3 ＞ 其餘。**不受理範圍**同 R1（治理流程、前端樣式、ML 選型、GAP-3、#4–#6、排序意見、重議拆分）。R1 已裁決之取捨（vdW 空間、預設 enabled=True、`oos_guarantees` 沿用 root）不重開，除非附新碼證或新反例。

## 產出
canonical 四欄 findings（或 sentinel）＋必答 1–5＋**Verdict**（可進 TODO／BLOCKING）。禁改碼、禁改 SPEC。收尾清 /tmp workdir（保留 claude-501）。
