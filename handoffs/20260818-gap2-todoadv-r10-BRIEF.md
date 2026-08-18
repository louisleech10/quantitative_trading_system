# GAP-2a／2b TODO adversarial 審查 R10（TODO DRAFT R4＋延伸檔 A1-1..6 之複核；預期收斂輪）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查 11 類／§2 錨點＋獵空殼＋殘留／canonical 四欄／Verdict）。
findings 用 canonical ID `## <FAMILY>-R10-P<0-3>-<NN>`（TODO 第四輪＝**R10**）；四欄含 `**來源摘要**: <路徑>#<sha256 前 12 碼>`。0 finding 寫 sentinel `## <FAMILY>-R10-P3-00`。

## 審查標的
- **TODO（本輪主標的）**：`docs/GAP2_MARGINAL_IC_TODO.md`（**DRAFT R4**；R9 三家 7 findings 三群集 V1–V3 全部接受寫回；R8 十群集 U1–U10 三家已確認成立；`template_check todo` PASS；`todo_spec_crosscheck` SMOKE PASS）
- **SPEC（R7 FROZEN）**：`docs/GAP2_MARGINAL_IC_SPEC.md`＋**延伸檔** `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1 `persist_suppressed`／A1-2 golden case_id／A1-3 OOS 欄 root 注入／A1-4 §C#6 白名單三檔／**A1-5 §C#6 再加 `page.tsx`**／**A1-6 `write_failed` reason 字面封閉**；衝突時以延伸檔為準）
- **R9 收斂檔**：`handoffs/reconcile/20260818-gap2-x-review-r9/synth.md`（V1–V3；三家戳記 stamp r10）；你 R9 的 review：`handoffs/20260818-gap2-todoadv-r9-<你的家族>.md`；R8 收斂檔 `…-r8/synth.md`（U1–U10）
- 收斂檔（皆三家戳記）：`handoffs/reconcile/20260818-gap2-x-review-r{1..8}/synth.md`；偵察 `.../20260818-gap2-x-consult-r1/synth.md`
- 殘留登記：`docs/IC_QUANT_GAP_REGISTRY.md`「GAP-2 待補完」（G2-R1／R2／R3／R5）

## ⚠️ 前置說明
- 本輪是 **TODO 審查**：攻「執行端讀完能不能直接寫碼」＋「SPEC 義務有沒有逐條落到 TODO 且語意方向一致」＋「批次可獨立綠／無 forward dependency」＋「取巧面」。「某函式尚不存在」不是缺陷。
- 禁改碼、禁改 SPEC／TODO；只產你自己的 review 檔。SPEC 若真有缺陷 ⇒ 列 finding 標「SPEC 義務側」，由主委寫延伸檔。
- 使用者裁決不受理重議：2a／2b 拆分；橋本體 blocked；B5 表格＋toggle 預設開；`marginal_ic.enabled` 預設 True；技術取捨交委員會。
- **收斂判準**：你的 R9 findings 是否已被 V1–V3 正確處置（是否確實寫入 TODO R4／A1-5／A1-6）。若全部關閉且無新 BLOCKING ⇒ 明寫「可 Frozen」＋sentinel。

## 本 brief 前提（逐條標；優先攻 assumed）
fact-verified: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS；`bash scripts/todo_spec_crosscheck.sh <SPEC> <TODO>` → SMOKE PASS（Claude 實跑 2026-08-18，DRAFT R4）
fact-verified: `page.tsx:815` `TabsContent value="deep"`、`:904-914` `NetICChart` 為 deep 末段；`grep MarginalICTable frontend/src` 現況 0 命中（A1-5 之依據）
fact-verified: `_persist_outputs` 只兩呼叫點 `:1142`／`:3432`；`_annotate_root_status_and_pass_class` 三呼叫點 `:1130`（fallback wrapper）／`:1542`（xsec，節為 N/A 不注入）／`:3424`（`_stage7_report`）
fact-verified: `page.tsx:214` `deepTabVisible` gating deep tab（`:750`／`:814`）⇒ **A1-5 補正**（主委實核，寫入 AMENDMENTS 末段與 TODO §0⑥／Task 5.1 步驟 3／驗證⑥）：掛載點由 R9 synth V1 之「deep tab 末段」改為 **basic `TabsContent`（`:753`）末段 `CorrelationHeatmap`（`:810`）之後**。← **請三家獨立判此補正是否正確**（base 節該在 basic tab；母 SPEC「deep 區塊之後」之解讀；是否還有其他 gating 會藏它）；若你認為 deep tab 才對或另有更佳區塊 ⇒ 列 finding 標「SPEC 義務側」
assumed: A1-6 把例外類別只進 log 不損失可觀測性（使用者／前端不需知道是 `PermissionError` 還是 `OSError`）← 若你認為需要，提議**不破五鍵**之替代（如 metadata 另欄），標 SPEC 義務側
assumed: Phase 小節改為「單一來源＝§B＋逐字複製」不會再漂（雙寫仍在，只是同文）← 若你認為應改純 pointer 不複製，列 MINOR
assumed: 各批 gate 之 `mutation_probe_check.sh <路徑…>` 與每 Task 指定之 `test_mutation_*` 名一一對應、無漏檔 ← 請逐檔核
## 必答（逐條 verdict）
1. **Agent 可執行性**：逐 Task 檢查「檔案到函式名／偽碼夠不夠／不可做／驗證命令」，列出執行端會卡住或需「自行判斷」之處。
2. **義務覆蓋**：SPEC §A D1–D7／D3′／D3″、§G 1–4、§V 24 條、§C 白名單（含 A1-4）、§N 四殘留——逐條在 TODO 有落點且**語意方向一致**？列漂移。
3. **批次獨立性／forward dependency**：五批逐批模擬；Task 4.0 位置；4.2 對契約值之增改。
4. **取巧面**：哪些 Task 可「跑得綠但不保證正確」？
5. **測試設計**：每新測試檔之 `test_mutation_*` 是否指向真實 falsification；探針 case 對映是否唯一。
6. 可以 Frozen 進 B1 實作嗎？BLOCKING 清單。

## Time-box 與範圍紀律
- 優先序＝必答 1 ＞ 2 ＞ 3 ＞ 4 ＞ 其餘。**不受理範圍**同 SPEC 輪（治理流程、前端樣式、ML 選型、GAP-3、#4–#6、排序、重議使用者裁決）。

## 產出
canonical 四欄 findings（或 sentinel）＋必答 1–6＋**Verdict**（可 Frozen／需修補／重作）。禁改碼、禁改 SPEC／TODO。收尾清 /tmp workdir（保留 claude-501）。

## R10 必核（逐條 verdict；每條引 TODO 行號）
- V1 §0⑥ 四檔（A1-4＋A1-5）；Task 5.1 步驟 3 之 `page.tsx` 精確插入點（import＋**basic** tab 末段 `CorrelationHeatmap` 後，A1-5 補正）＋props `section`＋驗證⑥（頁面實際掛載於 basic 區塊，禁只測元件）。
- V2 Phase B1／B2／B3／B4「測試＋Gate」小節＝§B 同文（含帶路徑 `mutation_probe_check.sh`）；`grep -n "mutation_probe_check.sh\`" docs/GAP2_MARGINAL_IC_TODO.md` 無無參數殘留。
- V3 Task 4.2 `write_failed` reason exact（A1-6）＋驗證⓪ reason ∈ 契約集合＋mock `os.replace` case。
- R8 U1–U10 仍成立（抽核 2 條即可）。
- 可 Frozen？BLOCKING 清單（無 → 明寫「可 Frozen」）。0 finding 寫 sentinel。
