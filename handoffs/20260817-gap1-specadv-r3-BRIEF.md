# GAP-1 SPEC R3 複審（R2 之 8 條 closure 複驗；含一條主委駁回之複核）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`。findings 用 canonical ID
`## <FAMILY>-R<輪次>-P<0-3>-<NN>`，**本輪輪次=R3**。四欄含
`**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`，**勿寫** `#sha256:`）。

## 審查標的
- **SPEC R3**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（最新 commit）
- 你 R2 的 findings：`handoffs/20260817-gap1-specadv-r2-<你的家族>.md`
- R2 收斂與處置：`handoffs/reconcile/20260817-gap1-x-review-r2/synth.md`（群集 E1–E4 ＋未採納節）

## 本輪任務
1. **closure 複驗**：對你 R2 的每條 finding 給 `CLOSED`／`OPEN`／`PARTIAL` ＋重跑同一反例之證據。
   codex 額外：你 R2 判 PARTIAL 的六條 R1 findings（P0-01／P0-03／P0-04／P1-05／P1-06 等），
   R3 之補齊或具名殘留是否足夠？逐條給判定。
2. 🔴 **複核主委之駁回（唯一一條）**：主委駁回 `GROK-R2-P1-01` 之修法（DSR 改「同一 V 當分母」），
   理由＝只有論文形式在 `n_trials=1` 時退化為 PSR。主委實跑：
   論文形式 N=1 → 1.000000 ＝ PSR；grok 形式 N=1 → 0.963181 ≠ PSR；
   且 `Var(SR_hat)=den²/(T-1)=0.022041` 與跨 trial `V[{SR_n}]=0.2` 為不同物件。
   **請獨立重算並判定**：主委的駁回成立嗎？若你認為主委錯，請附可重現反例與文獻條目。
   （此為技術爭點，看碼證與數學，不數人頭。）
3. **是否可進 TODO 生成**？若否，列 BLOCKING 清單（**只列真正阻擋者**）。

## ⚠️ 前置說明
- 本輪是 **SPEC 審查**：「函式/檔案尚不存在」不是缺陷。
- **禁改碼、禁改 SPEC**；只產你自己的 review 檔。
- 允許提新 finding（R3 編號），但**不得**重開已具名為殘留且經使用者裁決之項（見不受理範圍）。

## 前置條件（上一次本輪 abandon 之原因已解除）
上一次派本輪時 codex 依 `AGENTS.md` 第 12 條正確停工：所依 reconcile 缺 `## 戳記`（主委漏跑戳記步驟）。
現已補齊——**三份收斂檔皆取得 codex+composer+grok 三家 APPROVED**，檢查器實跑：
`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260817-gap1-x-{consult-r1,review-r1,review-r2}/synth.md`
→ 三者皆 `RECONCILE-STAMP PASS`（body hash 相符）。另 composer 上次遇 Cursor `resource_exhausted`，
該輪已 abandon（`collection-failed`），本輪為重派。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: R2 之 7 條新 finding ID 於 SPEC R3 命中數皆 ≥1 → 逐 ID `grep -c` 實跑（Claude 2026-08-17）
fact-verified: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`
fact-verified: rf 反例已由主委獨立複驗（rf=0.02 ⇒ ratio 4.530930 vs 3.464102；rf=0 ⇒ diff 0.000000），斷言③ 已改為 rf=0 fixture＋新增 ③b 覆蓋生產預設
fact-verified: 三份 reconcile 皆三家 APPROVED 且 `reconcile_stamps_check.sh` 實跑 PASS（Claude 2026-08-17）
fact-verified: grok 於上一次 R3（僅它完成）指出之 `variance_source="analytic"` 殘留已修（現 SPEC 僅一處提及且為「已移除」說明；另兩處舊欄位名與「analytic 為預設建議來源」亦已清除）→ `grep -n analytic docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 僅 2 命中皆為說明性
assumed: grok 上一輪提出之 alpha μ 數值差異（主委 `1.0683760683760685e-04` vs grok 重算 `1.0684346e-04`，相對差 ~5e-5）僅為年化基準取法不同、不影響 PBO oracle 有效性 ← 請攻並給出應寫死之唯一推導
assumed: E1–E4 四群集之處置**逐條完整**回應 R2 之 8 條，且 codex 六條 PARTIAL 已補齊或誠實降為具名殘留 ← 請直接攻
assumed: `variance_source` 由三態改二態（移除 `analytic`）後，DSR 在「今日無 ledger」情境下仍可用於 `n_trials=1`，且 `n_trials>1` 回 `cross_trial_variance_unavailable` 是誠實而非功能缺失 ← 請攻
assumed: 契約 13 鍵之三集合（`report_sections`／`eligibility_keys`／`reasons`）內容已足以讓 Task 3.3 之 24 案例與契約對證（而非自洽） ← 請攻
assumed: 批內順序 `1.1→1.2→1.3→1.4` ＋缺 `annualization` 之 fail-closed，已消除 Task 1.4 對 1.3 的隱性依賴 ← 請攻

## 必答（逐條 verdict）
1. closure 表（你 R2 每條 ＋ codex 之六條 R1 PARTIAL）。
2. 主委駁回之複核判定（成立／不成立＋證據）。
3. R3 修補是否引入新缺陷（特別是：二態 variance、per-period 單位鎖定與 `value_annualized` 之分工、
   雙重 CSCV 預算是否與 §G 之 S=16 案例衝突、`reasons` 六值是否夠用）。
4. 可否進 TODO 生成？BLOCKING 清單（只列真正阻擋者）。

## Time-box 與範圍紀律
- 優先序＝必答 2（駁回複核）＞ 1（closure）＞ 3 ＞ 4。
- **不受理範圍**：使用者兩項裁決（範圍 A／降級展示不硬擋）、要求本票現在接線、
  要求把 MinBTL 上界改精確值、要求關閉六條生產 bypass（皆已具名殘留）、治理流程與 gate 機制、前端樣式。

## 產出
closure 表 + 駁回複核判定 + canonical 四欄（僅新 finding）+ **Verdict**。
**禁改碼、禁改 SPEC**。收尾清 /tmp workdir（保留 claude-501）。
