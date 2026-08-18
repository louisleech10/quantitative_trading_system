# GAP-2a／2b SPEC adversarial 審查 R6（收斂確認輪；六份 reconcile 皆已三家 RECONCILE-STAMP APPROVED）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行。findings 用 canonical ID `## <FAMILY>-R6-P<0-3>-<NN>`；四欄含 `**來源摘要**: <路徑>#<sha256 前 12 碼>`。本輪輪次=R6。
若你確認 0 個實質 finding，寫 sentinel `## <FAMILY>-R6-P3-00`（body 四欄照填，內容為「逐項核對後無 finding」＋核對依據）。**勿為湊數捏造**；亦勿因「已六輪」而放水——有反例就列。

## 審查標的
- **SPEC（R5 修訂版）**：`docs/GAP2_MARGINAL_IC_SPEC.md`（`template_check spec` PASS）
- **收斂檔（皆已三家 RECONCILE-STAMP APPROVED；`bash scripts/reconcile_stamps_check.sh <path>` 各 rc=0）**：
  - `handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md`（偵察 C1–C7）
  - `handoffs/reconcile/20260818-gap2-x-review-r1/synth.md`（K1–K6）
  - `handoffs/reconcile/20260818-gap2-x-review-r2/synth.md`（L1–L5）
  - `handoffs/reconcile/20260818-gap2-x-review-r3/synth.md`（M1–M3）
  - `handoffs/reconcile/20260818-gap2-x-review-r4/synth.md`（N1–N3）
  - `handoffs/reconcile/20260818-gap2-x-review-r5/synth.md`（P1–P2；codex 2 條字面殘留＋composer／grok sentinel）
- 你 R5 的 review：`handoffs/20260818-gap2-specadv-r5-<你的家族>.md`（codex：請複核 P1（Task 4.2 失敗形狀五鍵 literal）與 P2（§V「已知不測：無」＋並發驗證⑦）是否閉合；composer／grok：請對這兩處做獨立複核）

## ⚠️ 前置說明
- SPEC 審查非實作審查；禁改碼、禁改 SPEC；只產你自己的 review 檔。
- 使用者已裁定不受理重議：2a／2b 拆分、橋本體 blocked、技術取捨交委員會、GAP-3 另票；R1–R3 已裁決之取捨（vdW 空間、預設 enabled=True、`oos_guarantees` 沿用 root、reasons 唯一住 survivor 契約、case_id↔report_ref 檔名）不重開，除非附新碼證或新反例。

## R5 修訂摘要（請核對閉合）
- P1：Task 4.2 改法之 `identity_missing`／`write_failed` literal 改為完整五鍵（path/sha256=null、case_id 明確值），與驗證⓪ 一致。
- P2：§V 章程「已知不測：無」——OOM 由計數 gate＋Task 4.3 receipt（`n_regressions==600`、receipt 只記錄不設閾值）；並發由 Task 4.2 原子寫＋驗證⑦（兩執行緒同 case_id ⇒ 完整 JSON）覆蓋。


## 本 brief 前提
fact-verified: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`（Claude 實跑 2026-08-18）
fact-verified: 六份 synth `reconcile_stamps_check.sh` 皆 PASS（三家 APPROVED；stamp 輪 R1–R6）
assumed: SPEC 現況已無條文級矛盾（含 R4 新增之 survivor_output 五鍵、gap2_canonical_sha、預算 oracle 敘述與 Task 3.1／4.1／4.2／4.3／§V 一致）← 請以 grep 機械核對並貼結果
assumed: 五批 B1(1.0–1.3)→B2→B3→B4→B5 各批可獨立綠、無 forward dependency（R3／R4 composer／grok 判成立）← codex 請獨立判定

## 必答
1. R5 P1–P2 逐條閉合？未閉合處引 SPEC 行號＋反例。
2. 條文級矛盾 grep 核對結果（貼命令＋輸出）。
3. 可進 TODO？BLOCKING 清單（無 → 明寫「可進 TODO」）。

## Time-box 與範圍紀律
- 優先序＝必答 1 ＞ 3 ＞ 2。**不受理範圍**同 R1–R5。

## 產出
canonical 四欄 findings（或 sentinel）＋必答 1–3＋**Verdict**。禁改碼、禁改 SPEC。收尾清 /tmp workdir（保留 claude-501）。
