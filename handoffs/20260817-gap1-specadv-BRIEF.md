# GAP-1 SPEC adversarial 審查 R1（MinBTL／DSR／PBO 策略層防過擬合）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查 11 類／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。
本輪輪次=R1。**四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`，勿寫 `#sha256:` 前綴——上輪六條因此被 completeness 擋下）。**

## 審查標的
- **SPEC**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（本輪唯一標的）
- 上游收斂檔（SPEC 之義務來源）：`handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md`
  （C1–C5 群集、前提修正節、使用者裁決節）
- 你上一輪偵察產出：`handoffs/20260817-gap1-recon-<你的家族>.md`

## ⚠️ 前置說明（勿誤 block）
- 本輪是 **SPEC 審查，不是實作審查**。「某函式/檔案尚不存在」**不是** SPEC 缺陷（範本明載）；
  正確攻擊面是「該義務有沒有被寫成可證偽的驗收條件」。
- **禁改碼、禁改 SPEC**；只產你自己的 review 檔。
- `handoffs/reconcile/*/synth.md` 為無戳記診斷檔，勿 STAMP-BLOCK。
- 每條 finding 附可獨立重現證據（SPEC 行號、grep 指令與輸出、實跑 receipt）。無證據標 `UNVERIFIED`。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`（Claude 實跑 2026-08-17）
fact-verified: 使用者 2026-08-17 白話閘裁決＝交付範圍選項 A；MinBTL 不合格採「降級展示＋明顯警語」，**不採** API 硬擋 → 收斂檔「使用者裁決」節
fact-verified: 成熟度地圖（僅 Feature Factory 完整、IC 進行中、其餘含 Strategy/Optimization/ML 皆不完整）→ 收斂檔「前提修正」節；receipt＝`ls data/optuna*` no matches、`results/optimization_results` 不存在
assumed: SPEC 的四批切分（B1 頻率/退化語意 → B2 N ledger 契約 → B3 MinBTL+DSR → B4 PBO）**無 forward dependency**，且每批獨立可 revert ← 請直接攻這條
assumed: 三關公式（DSR 之 `E[max SR]` 含 γ 項、MinBTL＝`2·ln(N)/SR²`、PBO＝CSCV logit 排名）在 SPEC 中的寫法與文獻一致，且 §G 的三類 oracle 足以構成可證偽驗收 ← 請逐式核對，若與原文獻定義有出入請具名
assumed: §N 的「具名待接線項」清單完整覆蓋所有被降級的接線面（Optuna 寫入／output service 矩陣／ml_pipeline 掛載／前端面板／策略 wiring 閘門）← 可能有漏，請對收斂檔逐條回查
assumed: Task 1.3 之 `annualization_source="default_730"` 設計（保留舊行為但標來源，三關拒絕消費）不會在既有測試造成假綠 ← 請攻

## 必答（逐條 verdict，附證據）
1. **公式與統計正確性**：DSR／MinBTL／PBO 三式在 SPEC 中的定義、輸入語意（T、N、年化、V[SR]）是否與
   Bailey & López de Prado 原始定義一致？有無數學錯誤、單位不一致、或把近似當等式？
2. **驗收可證偽性**：每個 Task 的「驗證」是否真能在改壞時 FAIL？§V 的 7 條 mutation 是否覆蓋所有
   關鍵不變式？有沒有「跑得綠但不保證正確」的廉價斷言？
3. **forward dependency 與存活性**：逐 Task 檢查輸入是否依賴尚未完成的後續 Phase；
   有無「Phase X 產出被 Phase Y 覆蓋/刪除」的白工（此類漏洞歷史上曾走六輪未被發現）。
4. **義務覆蓋**：收斂檔 C1–C5 與使用者兩項裁決，是否**逐條**在 SPEC 有對應 Task 或具名 §N？
   列出任何遺漏或被靜默弱化者（尤其 fail-closed 語意、`n_is_lower_bound`、禁 top-K、禁調公式常數）。
5. **成熟度約束遵守**：SPEC 是否有任何處把不完整層（Strategy／Optimization／ML／frontend）的內部結構
   當設計依據？Task 1.3 是唯一允許的既有檔改動，其風險/回退是否處理得當？
6. **契約設計**：Task 2.1 以 `capability_status_ref` 指向 IC 契約複用枚舉——這個 ref 機制是否可行且不會
   造成隱性耦合或載入循環？欄位集合是否只在一處列舉（防兩處漂移）？
7. **殘留誠實度**：使用者裁決「不硬擋」造成的殘留（ml_pipeline 可消費不合格冠軍）是否被誠實具名、
   且緩解（機器可讀 `eligibility` 欄位）足夠？有無其他未具名的靜默弱化？
8. 可以進 TODO 生成嗎，還是有 **BLOCKING** 必須先改 SPEC？

## Time-box 與範圍紀律
- 優先序＝必答 1（公式正確性）＞ 2（可證偽）＞ 4（義務覆蓋）＞ 其餘。
- **不受理範圍**：治理流程與 gate 機制設計、前端樣式、registry #2–#6 其他票內容、
  「應該先做別的票」這類排序意見（範圍已由使用者裁決）、要求本票現在就接線（已由裁決降級）。

## 產出
canonical 四欄 findings + 必答 1–8 逐條 verdict + **Verdict**（可進 TODO／BLOCKING 清單）。
**禁改碼、禁改 SPEC**。收尾清 /tmp workdir（保留 claude-501）。
