# GAP-2a／2b TODO adversarial 審查 R9（TODO DRAFT R3＋延伸檔 A1-1..4 之複核；預期收斂輪）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查 11 類／§2 錨點＋獵空殼＋殘留／canonical 四欄／Verdict）。
findings 用 canonical ID `## <FAMILY>-R9-P<0-3>-<NN>`（TODO 第三輪＝**R9**）；四欄含 `**來源摘要**: <路徑>#<sha256 前 12 碼>`。0 finding 寫 sentinel `## <FAMILY>-R9-P3-00`。

## 審查標的
- **TODO（本輪主標的）**：`docs/GAP2_MARGINAL_IC_TODO.md`（**DRAFT R3**；R8 三家 15 findings 十群集 U1–U10：14 接受寫回、1 駁回；`template_check todo` PASS；`todo_spec_crosscheck` SMOKE PASS）
- **SPEC（R7 FROZEN）**：`docs/GAP2_MARGINAL_IC_SPEC.md`＋**延伸檔** `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1 `persist_suppressed`／A1-2 golden case_id／A1-3 OOS 欄 root 注入／**A1-4 §C#6 白名單擴三檔**；衝突時以延伸檔為準）
- **R8 收斂檔**：`handoffs/reconcile/20260818-gap2-x-review-r8/synth.md`（U1–U10；三家戳記 stamp r9）；你 R8 的 review：`handoffs/20260818-gap2-todoadv-r8-<你的家族>.md`
- 收斂檔（皆三家戳記）：`handoffs/reconcile/20260818-gap2-x-review-r{1..7}/synth.md`；偵察 `.../20260818-gap2-x-consult-r1/synth.md`
- 殘留登記：`docs/IC_QUANT_GAP_REGISTRY.md`「GAP-2 待補完」（G2-R1／R2／R3／R5）

## ⚠️ 前置說明
- 本輪是 **TODO 審查**：攻「執行端讀完能不能直接寫碼」＋「SPEC 義務有沒有逐條落到 TODO 且語意方向一致」＋「批次可獨立綠／無 forward dependency」＋「取巧面」。「某函式尚不存在」不是缺陷。
- 禁改碼、禁改 SPEC／TODO；只產你自己的 review 檔。SPEC 若真有缺陷 ⇒ 列 finding 標「SPEC 義務側」，由主委寫延伸檔。
- 使用者裁決不受理重議：2a／2b 拆分；橋本體 blocked；B5 表格＋toggle 預設開；`marginal_ic.enabled` 預設 True；技術取捨交委員會。
- **收斂判準**：你的 R8 findings 是否已被 U1–U10 正確處置（接受者是否確實寫入 TODO R3／A1-4；駁回者 U6 之碼證你能否重現）。若全部關閉且無新 BLOCKING ⇒ 明寫「可 Frozen」＋sentinel。

## 本 brief 前提（逐條標；優先攻 assumed）
fact-verified: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS；`bash scripts/todo_spec_crosscheck.sh <SPEC> <TODO>` → SMOKE PASS（Claude 實跑 2026-08-18）
fact-verified: `grep -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` → 0 命中；TODO Task 5.1 警語為「倖存者選於同一測試段；本節數字為描述統計，非獨立驗證」（U6 駁回 CODEX-R8-P1-06 之碼證；**codex 請重跑同一 grep 確認關閉**）
fact-verified: `_persist_outputs` 只有兩個呼叫點 `ic_filter_orchestrator.py:1142`（fallback wrapper）／`:3432`（`_stage7_report`）；`self._ic_cache = {` 於 `:3449`
assumed: Task 4.1 新 helper `_inject_root_oos(section, analysis_status, oos_guarantees)` 於 `_stage7_report` 與 fallback wrapper（`:1128` 附近 `_annotate_root_status_and_pass_class` 同點）兩處呼叫足以覆蓋所有 root 重註路徑，且與 validator ⑰ 一致 ← 請實核 `_annotate_root_status_and_pass_class` 之全部呼叫點
assumed: Task 4.1 xsec：`analyze_cross_sectional()` 加 `"marginal_ic": dict(_xsec_na)`＋`generate_json_report` 條件透傳（缺鍵省略、不補裸 `{}`）不破既有 10 處直接呼叫 reporter 之測試，且 `ic_wiring_check` R3／`test_r6_wider_contract_nodes_consistent` 對新節之要求可同時滿足 ← 請實核 `scripts/ic_wiring_check.py` R3 與 `test_ichc_contract_sync.py` 之斷言方式
assumed: Task 1.2 ⑮／Task 4.3 bench 之 `fit_projection` spy（`monkeypatch.setattr(marginal_ic, "fit_projection", ...)`）能攔到 `compute_marginal_ic` 內部呼叫（模組級名稱查找，非 `from ... import` 綁定）← 請攻實作歧義並指定 import 寫法
assumed: A1-4 白名單擴三檔（`types.ts`／`icAnalysisStore.ts`／`FeatureTierPanel.tsx`）已足；B5 不需再碰其他既有前端檔（如 IC 結果頁容器元件接入 `MarginalICTable`）← 請實核 Task 5.1 步驟 3「接入 IC 結果頁 deep 區塊之後」需要改哪個既有檔，若需 ⇒ 列 finding 標「SPEC 義務側」
assumed: 各批 gate 之 `mutation_probe_check.sh <路徑…>` 與每 Task 指定之 `test_mutation_*` 名一一對應、無漏檔（1.0／1.1／1.2 同檔 `test_marginal_ic.py`＋`test_survivor_contract.py`；2.1；3.1；4.1；4.2；4.3）← 請逐檔核

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

## R9 必核（逐條 verdict；每條引 TODO 行號）
- U1 §0⑥／Task 5.1 修改檔案＝A1-4 三檔；SPEC 母檔未就地改。
- U2 Task 4.1 步驟 1 已無 `fit_scope`→`pass_class` 推導；`_inject_root_oos` 為唯一注入點；驗證①／③／③′ 以 root 為 oracle；檔內 `test_mutation_fit_scope_derived_oos_breaks_root_oracle`。
- U3 Task 4.0 `--write` schema 含 `case_id`＋`--check` 比對；Task 4.3 `report_ref` 檔名段 == pre `case_id`。
- U4 Task 4.2 偽碼四顯式 kwargs＋三 caller 來源（含 fallback wrapper `:1142` 重注入）；`_ic_cache` 只在 persist 後承接；驗證⑧＋`test_mutation_persist_reads_ic_cache_breaks_cold_call`。
- U5 `persist_suppressed` 完整五鍵 object、`status`／`reason` 分欄；驗證⓪四形狀。
- U6 駁回碼證可重現（codex 必答）。
- U7 Task 1.2 ⑮＋Task 4.3 bench `fit_projection` spy 斷言（正常 `2k+m`／超預算 0／只超 removed `2k`）；`test_mutation_counter_without_fit_call_breaks_spy`。
- U8 xsec N/A 節插入點＋reporter 條件透傳＋驗證⑯。
- U9 各批 gate `mutation_probe_check.sh` 帶路徑；每新測試 Task 之 `test_mutation_*` 名。
- U10 「四處」殘留已清（`grep -n 四處 docs/GAP2_MARGINAL_IC_TODO.md` → 只剩版本行 L3 之歷史敘述「四處→兩插入點」）。
- 可 Frozen？BLOCKING 清單（無 → 明寫「可 Frozen」）。0 finding 寫 sentinel。
