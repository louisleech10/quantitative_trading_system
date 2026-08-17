# GAP-1 受限閉合複驗（**僅**四條 FATAL；不受理新一般性 SPEC 議題）

brief-kind: review

## 🔴 本輪範圍受限（收斂紀律；違反者之 finding 主委將逕列 RESIDUAL-OK）
上一輪（最終 SPEC 輪）codex 提 4 條 FATAL，主委**全採並已修補**。本輪**唯一任務**＝
複驗那四條是否真關閉。**不受理**任何新的一般性 SPEC 議題——除非該議題滿足
「**不修就會使 B1–B4 產出數值錯誤或不可重現結果，且附可執行反例**」。

## 審查標的
- **SPEC R6**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（最新 commit）
- 上一輪收斂與處置：`handoffs/reconcile/20260817-gap1-x-review-r6/synth.md`（群集 H1／H2 ＋殘留清單 6 項）
- codex 上一輪 findings：`handoffs/20260817-gap1-specadv-r6-codex.md`

## 四條 FATAL 之修補摘要（逐條複驗）
1. `CODEX-R5-P0-01`（PBO rank 分母）→ 改 `r = rank/(N_valid_on_path + 1)`；平均排名明示等價
   `scipy.stats.rankdata(method="average")`；新增驗收 ④c（5 vs 3 有效候選之雙 path fixture）。
2. `CODEX-R5-P0-02`（snapshot membership 不可實作）→ `LedgerReadResult` 新增
   `artifact_hashes: frozenset[str]`；`PeriodReturns` 新增必填 `source_artifact_hash`；改集合成員測試。
3. `CODEX-R5-P0-03`（universe 守衛缺輸入）→ PBO 簽名新增 `candidate_ids` 與 `ledger_result`；
   守衛改驗**集合相等**＋count 三方相等＋canonical hash（`sha256(",".join(sorted(candidate_ids)))`）；
   新增驗收 ⑤b（50 選 10 且自算 hash 正確 ⇒ 仍拒）。
4. `CODEX-R5-P0-04`（ledger Sharpe 單位）→ `ledger_record_keys` 新增必填 `metric_unit`
   （值集合住新頂層鍵 `metric_unit_values`）；`valid_sharpe_values` 只收 `per_period`；頂層鍵 14→15。

## 本輪任務
1. 四條逐條 `CLOSED`／`OPEN`／`PARTIAL` ＋**重跑同一反例**之證據（codex 尤須重跑其原始反例）。
2. 可否進 TODO 生成？（BLOCKING 只列滿足上述受限門檻者）
3. 若仍 OPEN，請回答：可否作具名殘留帶進 TODO（yes/no ＋理由）。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`。canonical ID `## <FAMILY>-R<輪次>-P<0-3>-<NN>`，
**本輪輪次=R6**。四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`）。
零 findings 時用 sentinel `## <FAMILY>-R6-P3-00`（body 須實質，禁空殼）。

## ⚠️ 前置說明
- **禁改碼、禁改 SPEC、禁蓋戳記**；只產你自己的 review 檔。
- `review-r4`／`r5`／`r6` 之戳記另輪處理，**勿以「缺戳記」停工**（三份較早者已三家 APPROVED）。
- 「函式/檔案尚不存在」不是缺陷。

## 本 brief 前提（逐條標）
fact-verified: 四條 FATAL ID 於 SPEC R6 命中皆 ≥1；`grep -c "13 個頂層"` → 0（Claude 實跑 2026-08-17）
fact-verified: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`
assumed: 四條修補皆已使兩個獨立實作得到相同數值，且 top-K 污染路徑已封閉 ← 請攻（附反例才算）
assumed: 6 項具名殘留（見 H2 後之清單）皆不影響 B1–B4 正確性 ← 請攻

## Time-box
優先序＝四條 closure ＞ 必答 2 ＞ 3。不受理範圍同前輪（使用者裁決、接線、MinBTL 精確值、
六條生產 bypass、治理機制、前端樣式、DSR「同一 V」修法）＋**本輪新增**：一般性 SPEC 議題（見上）。

## 產出
四條 closure 表 + 必答 2/3 + **Verdict**。收尾清 /tmp workdir（保留 claude-501）。
