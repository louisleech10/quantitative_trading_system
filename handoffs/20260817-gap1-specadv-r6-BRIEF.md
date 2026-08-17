# GAP-1 SPEC R6 複審（**最終 SPEC 輪**：R4 輪 7 條 closure 複驗）

brief-kind: review

## 審查標的
- **SPEC R5**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（最新 commit）
- 你上一輪 findings：`handoffs/20260817-gap1-specadv-r5-<你的家族>.md`
- 上一輪收斂與處置：`handoffs/reconcile/20260817-gap1-x-review-r5/synth.md`（群集 G1–G3 ＋未採納節）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`。canonical ID `## <FAMILY>-R<輪次>-P<0-3>-<NN>`，
**本輪輪次=R5**。四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`）。

## 🔴 本輪為最終 SPEC 輪（收斂紀律，使用者定死之條款）
收斂軌跡：R1 23 條 → R2 7 → R3 11 → R4 7。composer 已連兩輪零 finding；grok 連兩輪判無 BLOCKING。
依「95% 解法就收・殘留先記錄」與「epic 收斂斷路器」：**本輪之後不再開 SPEC 修訂輪**。
因此你的 finding 請**明確二分**：
- **`FATAL`**：若不修，B1–B4 之實作會產出**數值錯誤或不可重現之結果**（附反例）。
- **`RESIDUAL-OK`**：屬規格細節／可在 TODO 對應 Task 內釘死／不影響 B1–B4 正確性 ⇒ 主委將具名列入殘留清單。
**未標二分者一律視為 `RESIDUAL-OK`。** 只列 `FATAL` 於 BLOCKING 清單。

## 本輪任務
1. **closure 複驗**：對你上一輪每條 finding 給 `CLOSED`／`OPEN`／`PARTIAL` ＋重跑同一反例之證據。
   codex 特別注意：你 4 條 BLOCKING 已全數採納（G1 頂層鍵 13→14＋`ledger_record_keys` 物件化＋
   reasons 擴至 11 值；G2 `n_for_dsr`＋`snapshot_hash`＋驗收改引用 `ledger_result`；
   G3 PBO 步驟 3b path 級剔除/跳過/`all_paths_degenerate`＋universe 唯一成功路徑改
   `ledger_all_candidates`、`full_grid` 與 `external_declared` 皆封閉）。
2. **可否進 TODO 生成**？（BLOCKING 清單只列 `FATAL`）
3. 對每條未關項給 `FATAL`／`RESIDUAL-OK` 二分＋一句理由。

## ⚠️ 前置說明
- 本輪是 **SPEC 審查**：「函式/檔案尚不存在」不是缺陷。
- **禁改碼、禁改 SPEC、禁蓋戳記**；只產你自己的 review 檔。
- 先前三份收斂檔已三家 APPROVED（`reconcile_stamps_check.sh` 實跑 PASS）；
  `review-r4`／`review-r5` 之戳記另輪處理，**勿以「缺戳記」停工**。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: 上一輪 6 條新 finding ID 於 SPEC R5 命中皆 ≥1 → 逐 ID `grep -c` 實跑（Claude 2026-08-17）
fact-verified: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`
fact-verified: 主委未採納 grok 三處「具名殘留」建議、改為當輪修完（理由見 R5 收斂檔未採納節）
assumed: G1 之 14 鍵＋`reason_conditions` 雙向相等＋`ledger_record_keys` 物件化，已使契約可唯一實作 ← 請攻
assumed: G2 之 `n_for_dsr == n_candidates_considered` 與 `snapshot_hash` 定義，已使兩獨立實作得到相同 DSR ← 請攻
assumed: G3 之 path 級剔除規則已消除「NaN 排序決定結果」，且 universe 僅 `ledger_all_candidates` 可通過已封閉 top-K 污染 ← 請攻
assumed: SPEC 已足以生成 TODO 並開始 B1 實作；剩餘任何項皆為 `RESIDUAL-OK` ← 請攻，這是本輪最關鍵判斷

## Time-box 與範圍紀律
- 優先序＝必答 1（closure）＞ 3（二分判定）＞ 2。
- **不受理範圍**：使用者兩項裁決（範圍 A／降級展示不硬擋）、要求本票接線、MinBTL 上界改精確值、
  要求關閉六條生產 bypass、治理流程與 gate 機制、前端樣式、重議已駁回之 DSR「同一 V」修法。

## 產出
closure 表 + 每條未關項之 `FATAL`／`RESIDUAL-OK` 二分 + canonical 四欄（僅新 finding）+ **Verdict**。
**禁改碼、禁改 SPEC**。收尾清 /tmp workdir（保留 claude-501）。
