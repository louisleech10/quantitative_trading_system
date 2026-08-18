# GAP-2a／2b TODO adversarial 審查 R8（TODO DRAFT R2＋延伸檔 A1-1..3 之複核；預期收斂輪）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查 11 類／§2 錨點＋獵空殼＋殘留／canonical 四欄／Verdict）。
findings 用 canonical ID `## <FAMILY>-R8-P<0-3>-<NN>`（TODO 第二輪＝**R8**）；四欄含 `**來源摘要**: <路徑>#<sha256 前 12 碼>`。0 finding 寫 sentinel `## <FAMILY>-R8-P3-00`。

## 審查標的
- **TODO（本輪主標的）**：`docs/GAP2_MARGINAL_IC_TODO.md`（**DRAFT R2**；R7 三家 20 findings 六群集 T1–T6 全部寫回；`template_check todo` PASS；`todo_spec_crosscheck` SMOKE PASS）
- **SPEC（R7 FROZEN）**：`docs/GAP2_MARGINAL_IC_SPEC.md`＋**延伸檔** `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1 `persist_suppressed`／A1-2 golden case_id／A1-3 OOS 欄 root 注入；衝突時以延伸檔為準）
- **R7 收斂檔**：`handoffs/reconcile/20260818-gap2-x-review-r7/synth.md`（T1–T6；三家戳記）；你 R7 的 review：`handoffs/20260818-gap2-todoadv-<你的家族>.md`
- 收斂檔（皆三家戳記）：`handoffs/reconcile/20260818-gap2-x-review-r{1..6}/synth.md`；偵察 `.../20260818-gap2-x-consult-r1/synth.md`
- 殘留登記：`docs/IC_QUANT_GAP_REGISTRY.md`「GAP-2 待補完」（G2-R1／R2／R3／R5）

## ⚠️ 前置說明
- 本輪是 **TODO 審查**：攻「執行端讀完能不能直接寫碼」＋「SPEC 義務有沒有逐條落到 TODO 且語意方向一致」＋「批次可獨立綠／無 forward dependency」＋「取巧面」。「某函式尚不存在」不是缺陷。
- 禁改碼、禁改 SPEC／TODO；只產你自己的 review 檔。SPEC 若真有缺陷 ⇒ 列 finding 標「SPEC 義務側」，由主委寫延伸檔。
- 使用者裁決不受理重議：2a／2b 拆分；橋本體 blocked；B5 表格＋toggle 預設開；`marginal_ic.enabled` 預設 True；技術取捨交委員會。

## 本 brief 前提（逐條標；優先攻 assumed）
fact-verified: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS；`bash scripts/todo_spec_crosscheck.sh <SPEC> <TODO>` → SMOKE PASS（Claude 實跑 2026-08-18）
fact-verified: SPEC R7 FROZEN（六輪 14→12→4→4→2→0；使用者白話閘核准；B5 加 toggle 為使用者裁決）
assumed: TODO Task 4.0（§G pre 檔凍結獨立化為 B4 首件）與 Task 4.2 對 `ic_survivor_contract.json#reasons.survivor_output` 增 `persist_suppressed` 值（不改鍵集）**不構成** SPEC 義務漂移 ← 請判：是否需延伸檔 A1 條目
assumed: Task 1.2 步驟 6「字面值一律由 `load_survivor_contract()` 讀出、不寫死於程式」與 Task 4.1 ⑫「AST 掃 orchestrator 字串常數 ⊆ 契約 reasons」可同時成立（reason 字面出現在 orchestrator 內作對照常數 vs 從契約讀）← 請攻實作歧義
assumed: Task 3.1 `build_survivor_output` 之參數清單（含新加 `summary_by_feature`）足以組出契約全部 required 鍵；`labels_content_hash`／`features_source_hash` 於 orchestrator 可取得（`_stage0_ingestion` 之 features_path 與 stage2 label）← 請實核路徑並列缺口
assumed: 五批各自可獨立綠：B1 不依賴 report 契約；B3 不動 report 契約（既有 `test_ichc_contract_sync` 仍綠）；B4 契約增鍵與 orchestrator 同 commit；B5 toggle 之 wiring R1b 依賴 Task 4.1 已加 `STAGE_OVERRIDE_PATHS["marginal_ic"]` ← 請逐批模擬既有測試
assumed: Task 4.1 對 `analyze()`／`refilter()`／`analyze_full()`／`_run_full_sample_fallback()` 四處掛載的敘述足以讓執行端在 4098 行 orchestrator 內定位（現有 stage6→stage7 呼叫點 `:1039-1063`、`:1736-1765`、`:1065-1152`）← 請實核並補行號／缺口
assumed: 前端 Task 5.1 之 store／toggle 改法與 `scripts/ic_wiring_check.py` R1a／R1b 規則（`PRESET_TOGGLES` 鍵集 ⊆ `getEffectiveConfig` 消費集 ∪ allowlist；映射鍵 ⊆ 後端可消費集）相容 ← 請實核 `frontend/src/store/icAnalysisStore.ts` 與 `scripts/ic_wiring_check.py`

## 必答（逐條 verdict）
1. **Agent 可執行性**：逐 Task 檢查「檔案到函式名／偽碼夠不夠／不可做／驗證命令」，列出執行端會卡住或需「自行判斷」之處。
2. **義務覆蓋**：SPEC §A D1–D7／D3′／D3″、§G 1–4、§V 24 條、§C 白名單、§N 四殘留——逐條在 TODO 有落點且**語意方向一致**？列漂移。
3. **批次獨立性／forward dependency**：五批逐批模擬；Task 4.0 位置；4.2 對契約值之增改。
4. **取巧面**：哪些 Task 可「跑得綠但不保證正確」（例：oracle 容差、`n_regressions` 計數、bench receipt 無閾值、toggle 只改前端不送 config）？
5. **測試設計**：每新測試檔之 `test_mutation_*` 是否指向真實 falsification；探針 case 對映是否唯一。
6. 可以 Frozen 進 B1 實作嗎？BLOCKING 清單。

## Time-box 與範圍紀律
- 優先序＝必答 1 ＞ 2 ＞ 3 ＞ 4 ＞ 其餘。**不受理範圍**同 SPEC 輪（治理流程、前端樣式、ML 選型、GAP-3、#4–#6、排序、重議使用者裁決）。

## 產出
canonical 四欄 findings（或 sentinel）＋必答 1–6＋**Verdict**（可 Frozen／需修補／重作）。禁改碼、禁改 SPEC／TODO。收尾清 /tmp workdir（保留 claude-501）。

## R8 必核（逐條 verdict；每條引 TODO 行號）
- T1 Gate 分跑＋B1 十條唯一對映（Task 1.3／§B）；V-22a／V-24 批次歸屬。
- T2 `build_survivor_output` 簽名（`summary_by_feature`／`root_analysis_status`）＋Task 1.2 OOS 欄 `None` 佔位＋`_stage7_report` 注入（A1-3）＋golden case_id（A1-2）。
- T3 兩插入點＋`self._in_fallback_rerun`（try/finally）＋`_persist_outputs` 顯式 kwargs＋`self._features_path`／`_labels_path`。
- T4 B5：`FeatureTierPanel.TOGGLES`、具名 preset 送出、`_apply_tier_config` 消費、驗證⑤三路徑。
- T5 警語不含「獨立 OOS 驗證」子字串；bench 為觀測、OOM 宣稱僅計數上界。
- T6 reason 一律 `load_survivor_contract()`；`persist_suppressed` 走 A1-1。
- 可 Frozen？BLOCKING 清單（無 → 明寫「可 Frozen」）。0 finding 寫 sentinel。
