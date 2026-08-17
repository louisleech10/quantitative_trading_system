# GAP-1 SPEC R5 複審（R3 輪 11 條 closure 複驗）

brief-kind: review

## 審查標的
- **SPEC R4**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（commit `7d9a6f1a`）
- 你上一輪 findings：`handoffs/20260817-gap1-specadv-r4-<你的家族>.md`
- 上一輪收斂與處置：`handoffs/reconcile/20260817-gap1-x-review-r4/synth.md`（群集 F1–F4）
  （body sha256＝`ad0988e951eb`；該檔 `## 戳記` 區段留待**另一輪** stamp 處理，本輪勿蓋章）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`。canonical ID `## <FAMILY>-R<輪次>-P<0-3>-<NN>`，
**本輪輪次=R4**。四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`）。

## 本輪任務
1. **closure 複驗**：對你上一輪每條 finding 給 `CLOSED`／`OPEN`／`PARTIAL` ＋重跑同一反例之證據。
   codex 特別注意：你 5 條 BLOCKING 已全數採納並修補（F1 PBO 演算法四步＋必填 `n_obs`／`n_candidates`、
   F2 μ 唯一推導、F3 契約型別＋`reason_conditions`＋DSR 綁 ledger snapshot、F4 `external_declared` 封閉
   ＋objective 傳遞鏈），請逐條複驗是否**真**關閉。
2. **可否進 TODO 生成**？BLOCKING 清單（**只列真正阻擋者**）。
3. 若你認為仍有 BLOCKING，請同時回答：**該項是否可作為「具名殘留」帶進 TODO 階段而不損正確性**？
   （主委依「95% 解法就收・殘留先記錄」需要這個判斷；請給 yes/no ＋理由，勿只說「必須先修」。）

## ⚠️ 前置說明
- 本輪是 **SPEC 審查**：「函式/檔案尚不存在」不是缺陷。
- **禁改碼、禁改 SPEC、禁蓋任何戳記**；只產你自己的 review 檔。
- 三份先前收斂檔（consult-r1／review-r1／review-r2）已取得三家 APPROVED，`reconcile_stamps_check.sh`
  實跑皆 PASS；**review-r4 之戳記另輪處理**，勿以「缺戳記」停工。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: 上一輪 11 條 finding ID 於 SPEC R4 命中皆 ≥1 → 逐 ID `grep -c` 實跑（Claude 2026-08-17）
fact-verified: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`
fact-verified: μ 前版為假等式已由主委實跑確認（`0.01/93.6=1.0683760683760685e-04` vs `0.01/sqrt(8760)=0.00010684346079267205`），現改唯一推導式＋完整精度＋測試重算斷言
fact-verified: 轉置不可判定已由主委複驗（`(50,1200)` 之合法 T<N 與轉置不可區分）⇒ 改必填 `n_obs`／`n_candidates`
assumed: F1 之逐 path 四步演算法（IS metric／champion 平手取最小索引／OOS 平均排名 `r=rank/(N_valid+1)`／`ω=ln(r/(1-r))`）已足以讓兩個獨立實作得到相同 PBO ← 請直接攻
assumed: F3 之 `reason_conditions` 一對一對照＋`additional_properties: false` 已使 24 案例與契約對證而非自洽 ← 請攻
assumed: F4 之 `candidate_set_hash` 重算比對已使 universe 守衛不可靠自我宣告通關 ← 請攻
assumed: 剩餘未關項（若有）皆可作為具名殘留帶進 TODO，不影響 B1–B4 實作正確性 ← 請攻，這是本輪最關鍵判斷

## Time-box 與範圍紀律
- 優先序＝必答 1（closure）＞ 2 ＞ 3。
- **不受理範圍**：使用者兩項裁決（範圍 A／降級展示不硬擋）、要求本票接線、MinBTL 上界改精確值、
  要求關閉六條生產 bypass、治理流程與 gate 機制、前端樣式、重議已駁回之 DSR「同一 V」修法
  （判準＝N=1 退化為 PSR，三家已複核成立）。

## 產出
closure 表 + 必答 2/3 + canonical 四欄（僅新 finding）+ **Verdict**。
**禁改碼、禁改 SPEC**。收尾清 /tmp workdir（保留 claude-501）。
