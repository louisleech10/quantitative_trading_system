# GAP-2a／2b SPEC adversarial 審查 R3（R2 五群集修訂之複核；預期收斂輪）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行。findings 用 canonical ID `## <FAMILY>-R3-P<0-3>-<NN>`；四欄含 `**來源摘要**: <路徑>#<sha256 前 12 碼>`。本輪輪次=R3。
若你確認 0 個實質 finding，寫 sentinel `## <FAMILY>-R3-P3-00`（body 四欄照填，內容為「逐項核對後無 finding」＋核對依據）。**勿為湊數捏造**。

## 審查標的
- **SPEC（R2 修訂版）**：`docs/GAP2_MARGINAL_IC_SPEC.md`（`template_check spec` PASS）
- **R2 收斂檔**：`handoffs/reconcile/20260818-gap2-x-review-r2/synth.md`（L1–L5＝本輪必核之修訂義務）
- R1 收斂檔：`handoffs/reconcile/20260818-gap2-x-review-r1/synth.md`；你 R2 的 review：`handoffs/20260818-gap2-specadv-r2-<你的家族>.md`

## ⚠️ 前置說明
- SPEC 審查非實作審查；禁改碼、禁改 SPEC；只產你自己的 review 檔。
- 使用者已裁定不受理重議：2a／2b 拆分、橋本體 blocked、技術取捨交委員會、GAP-3 另票；R1／R2 已裁決之取捨（vdW 空間、預設 enabled=True、`oos_guarantees` 沿用 root、reasons 住 survivor 契約）不重開，除非附新碼證或新反例。

## R2 修訂摘要（請逐條核對閉合，且未引入新洞）
- L1：§G 刪 O1 raw `>0.10` 反向斷言，改由 O1a（raw 下 `x³` 殘差非退化 ⇒ status `ok` ⇒ 紅）承擔；V-2 對映改 O1a；規格表噪聲全部改 σ（O1／O7 σ=0.866、O2 σ=0.812、O4 σ=0.8）。
- L2：`ic_survivor_contract.json#reasons`（Task 1.0）為 reason 字面唯一列舉處；刪 `reasons_ref`；`ic_report_contract.json` 於 B4 只加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`；Task 4.1 加驗證⑫（orchestrator reason 字面 ⊆ survivor 契約 reasons）；Task 1.2 文字改指 Task 1.0。
- L3：`case_id` 對照 `report_ref` 檔名段；`symbol`／`timeframe` 對照報告 metadata（缺欄 raise，禁 None==None）；缺任一 ⇒ 不寫檔、`computation_failed:identity_missing`（Task 3.1 ⑮／Task 4.1 ⑭／Task 4.2）。
- L4：`event_identity` 於 stage3 pop 前計算存 `_ic_cache`（不可變），refilter 只讀；canonical 序列化規格入契約 `_doc`；Task 4.1 ⑬、Task 3.1 ⑱。
- L5：`max_survivors_for_loo`／`max_removed_candidates`（預設 200）超限整體 `not_computed:candidate_budget_exceeded`（禁部分輸出）；V-13 反向組合（Task 3.1 ⑰）；V-19 三欄參數化。

## 本 brief 前提（逐條標）
fact-verified: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`（Claude 實跑 2026-08-18）
fact-verified: R2 三家實跑 O2／O4（σ 正確）／O5／O7 皆落帶；O1a var≈5e-32、O1b marginal≈0.0056
assumed: 上述五群集修訂皆閉合且彼此無新矛盾（例：Task 1.0 `reasons` 與 Task 4.1 ⑫ 之掃描方向、`event_identity` 與 §G-1 golden 之互動——golden 已排除新節與 `metadata.survivor_output`，`_ic_cache` 內部鍵不進報告）← 請攻
assumed: 報告 `metadata.symbol`／`metadata.timeframe` 於正常 holdout 路徑必存在（實跑 `data_cache/reports/ic_report_ic_gatekeeper.json` metadata 含 `symbol=BTCUSDT`、`timeframe=1h`；`_stage0_ingestion` 從 meta json 帶入）；缺時 fail-closed 之路徑已明定 ← 請實核 `_stage0_ingestion` 與 `_base_universe_hash` 對 `symbol` 之既有要求
assumed: 預算預設 200 對真實 fixture（ETHUSDT/12h tail2000）之 survivors／removed 數量不會觸發 `candidate_budget_exceeded`（若會，預設值需調或明列）← 請實核 `run_analyze()` 之 filtered／passed 數量並貼值

## 必答
1. L1–L5 逐群集：閉合？未閉合處引 SPEC 行號＋反例。
2. 新引入風險（若有）。
3. 預算預設 200 vs 真實 fixture 數量（貼值）。
4. 可進 TODO？BLOCKING 清單（若無 → 明寫「可進 TODO」）。

## Time-box 與範圍紀律
- 優先序＝必答 1 ＞ 4 ＞ 3。**不受理範圍**同 R1／R2。

## 產出
canonical 四欄 findings（或 sentinel）＋必答 1–4＋**Verdict**。禁改碼、禁改 SPEC。收尾清 /tmp workdir（保留 claude-501）。
