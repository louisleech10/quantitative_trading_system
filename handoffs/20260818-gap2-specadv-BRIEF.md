# GAP-2a／2b SPEC adversarial 審查 R1（邊際 IC／多因子組合＋倖存因子輸出契約）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查 11 類／§2 獵空殼＋殘留三值攻擊／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。
本輪輪次=R1。**四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`，勿寫 `#sha256:` 前綴）。**

## 審查標的
- **SPEC**：`docs/GAP2_MARGINAL_IC_SPEC.md`（本輪唯一標的；`bash scripts/template_check.sh spec` 已 PASS）
- 上游收斂檔（SPEC 之義務來源）：`handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md`（C1–C7 群集＋Verdict）
- 你上一輪偵察產出：`handoffs/20260818-gap2-recon-<你的家族>.md`；主委版 `handoffs/20260818-gap2-recon-claude.md`

## ⚠️ 前置說明（勿誤 block）
- 本輪是 **SPEC 審查，不是實作審查**。「某函式/檔案尚不存在」**不是** SPEC 缺陷（範本明載）；正確攻擊面是「該義務有沒有被寫成可證偽的驗收條件」。
- **禁改碼、禁改 SPEC**；只產你自己的 review 檔。
- `handoffs/reconcile/*/synth.md` 為無戳記診斷檔，勿 STAMP-BLOCK。
- 每條 finding 附可獨立重現證據（SPEC 行號、grep 指令與輸出、實跑 receipt）。無證據標 `UNVERIFIED`。
- 使用者已裁定（不受理重議）：GAP-2 拆 2a／2b；2a 純 IC 層不碰 ML／事件型；2b 只交付契約；橋本體 blocked-by ML 層；技術取捨交委員會（看碼證不數人頭、取較嚴版）。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`（Claude 實跑 2026-08-18）
fact-verified: 偵察收斂 C1（codex 唯一提出）＝主線 stage4–6 皆於 test_mask 計算，root ok_oos 不證明 test 未被選擇消費 → SPEC D3′ 採較嚴版（`independent_oos_validation=false` 契約欄＋train 側並列統計＋nested split 列 §N R5 blocked-by）
fact-verified: 四方一致：邊際 IC＝semi-partial 秩 IC（rank→常態分數→train OLS→test 殘差→Spearman）；不改 `factor_orthogonalizer.py`；不用 `FactorModuleResult`；forward-stepwise 選擇不做
assumed: SPEC D1 之「van der Waerden 常態分數空間投影」相對「均勻分數（rank/(n+1)）空間」或「raw（已 PIT 前處理）空間」是**最合適**的選擇；O1（單調冗餘近 0）與 O4（加法性）之容差（0.02／[0.85,1.15]）在 n=5000／20000 下**足夠嚴且不假紅** ← 請攻：給出你認為的正確容差推導或反例
assumed: 五批切法（B1 純函式 → B2 組合 → B3 契約 → B4 接線＋golden → B5 前端表格）**無 forward dependency**；Task 1.2 之 bootstrap 於 2.1 搬移不構成白工 ← 請直接攻
assumed: `MarginalICConfig.enabled` **預設 True**（描述統計、不改選擇、O(k²n)）符合使用者「驗過就別預設關閉」鐵律，且不會弄壞既有測試（§G-1 改前==改後只比既有鍵）← 請攻：列出會因新節出現而紅的既有測試（若有）
assumed: §N R1–R5 之三值理由**皆成立**（R1 user-ruling／R2 needs-research／R3 blocked-by #4／R4 預設納入／R5 blocked-by holdout-only）← 逐條攻「其實現在就能做」
assumed: Task 3.1 契約欄位集合（含 `row_identity`、`feature_set_hash`、`labels_content_hash`、`independent_oos_validation`）對未來 ML 消費端「重建 exact rows＋防 stale」足夠 ← 請攻缺欄
assumed: `deny_factor_in_ok_oos` 不會誤傷新節（新節無 `module∈{orthogonalization,exposure}` 且 `oos_guarantees` 隨 root）；`test_ichc_contract_sync::test_r6_wider_contract_nodes_consistent` 對新 reason 之「消費點存在」斷言以 B3 只加鍵／B4 加值之順序可過 ← 請實核 `tests/momentum/Analysis/test_ichc_contract_sync.py:43-62`

## 必答（逐條 verdict，附證據）
1. **統計定義正確性**：D1 之 semi-partial 秩 IC 定義、`normal_scores` 分段（train／test 各自轉換）之影響、`ic_retained_ratio` 語意、`sequential` 之 `|train_ic|` 排序——有無數學錯誤／不一致？O1–O9 oracle 有無「跑得綠但不保證正確」或「必然假紅」者？
2. **OOS 與揭露誠實度**：D3／D3′ 是否足以防止「把 test 上選出的倖存者之邊際 IC 誤稱 OOS 驗證」？`oos_guarantees` 沿用 root 語意 vs 一律 False——哪個較嚴且不與 root 契約矛盾？`marginal_ic_train_insample` 定義是否會被誤讀為 OOS？
3. **可證偽驗收**：每 Task「驗證」是否改壞即 FAIL？§V 17 條 mutation 覆蓋所有關鍵不變式（train-only fit／秩空間／符號權重來源／契約 fail-closed／既有鍵不變）？缺哪些？
4. **forward dependency 與存活性**：逐 Task 檢查輸入是否依賴後續 Phase；有無白工（例：1.2 內部 bootstrap→2.1 搬移；B3 契約鍵集 vs B1/B2 dataclass `to_dict()` 鍵集之相互依賴方向）。
5. **義務覆蓋**：收斂檔 C1–C7 是否**逐條**在 SPEC 有對應裁決／Task／§N？列出遺漏或靜默弱化者。
6. **契約設計（2b）**：`ic_survivor_contract.json` 之 ref 機制、`sample_scope` 結構、`additional_properties:false`、與 `RowMaskPlan.source` 之 sync 測試——可行？有無隱性耦合／載入循環／兩處列舉？欄位是否只在契約檔列舉一次（SPEC Task 3.1 之「語意描述」段是否已構成第二處列舉而違反範本規則）？
7. **接線影響面**：白名單 7 處是否完整？`refilter`／`analyze_full`／`_run_full_sample_fallback`／xsec／cache-hit／`_suppress_persist` 各路徑之行為是否明定？`ic_wiring_check.REPORT_SECTIONS` 改讀契約是否會使既有 R3 語意變化？前端 B5 之風險（`npm run build`／types）是否處理。
8. **殘留誠實度**：§N R1–R5 三值理由逐條 verdict；R4（前端表格預設納入、使用者可否決）是否合規。
9. 可以進 TODO 生成嗎，還是有 **BLOCKING** 必須先改 SPEC？

## Time-box 與範圍紀律
- 優先序＝必答 1（統計定義）＞ 2（OOS 揭露）＞ 3（可證偽）＞ 6（契約）＞ 其餘。
- **不受理範圍**：治理流程與 gate 機制設計；前端樣式；ML 模型選型／訓練；事件型樣本組裝（GAP-3）；Pooled/Panel IC（#4）；容量／效能（#5／#6）；「應該先做別的票」排序意見；要求本票接 ML（已裁定 blocked）；重議 2a／2b 拆分。

## 產出
canonical 四欄 findings + 必答 1–9 逐條 verdict + **Verdict**（可進 TODO／BLOCKING 清單）。
**禁改碼、禁改 SPEC**。收尾清 /tmp workdir（保留 claude-501）。
