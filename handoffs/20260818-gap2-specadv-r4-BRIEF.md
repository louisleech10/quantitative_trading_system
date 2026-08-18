# GAP-2a／2b SPEC adversarial 審查 R4（收斂確認輪；四份 reconcile 皆已三家 RECONCILE-STAMP APPROVED）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行。findings 用 canonical ID `## <FAMILY>-R4-P<0-3>-<NN>`；四欄含 `**來源摘要**: <路徑>#<sha256 前 12 碼>`。本輪輪次=R4。
若你確認 0 個實質 finding，寫 sentinel `## <FAMILY>-R4-P3-00`（body 四欄照填，內容為「逐項核對後無 finding」＋核對依據）。**勿為湊數捏造**；亦勿因「已四輪」而放水——有反例就列。

## 審查標的
- **SPEC（R3 修訂版）**：`docs/GAP2_MARGINAL_IC_SPEC.md`（`template_check spec` PASS）
- **收斂檔（皆已三家 RECONCILE-STAMP APPROVED；`bash scripts/reconcile_stamps_check.sh <path>` 各 rc=0）**：
  - `handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md`（偵察 C1–C7）
  - `handoffs/reconcile/20260818-gap2-x-review-r1/synth.md`（K1–K6）
  - `handoffs/reconcile/20260818-gap2-x-review-r2/synth.md`（L1–L5）
  - `handoffs/reconcile/20260818-gap2-x-review-r3/synth.md`（M1–M3）
- 你 R3 的 review：`handoffs/20260818-gap2-specadv-r3-<你的家族>.md`（codex 於 R3 因 Rule 12 停工未審內容 → **本輪請完整複核 R2 L1–L5 與 R3 M1–M2 之閉合**）

## ⚠️ 前置說明
- SPEC 審查非實作審查；禁改碼、禁改 SPEC；只產你自己的 review 檔。
- 使用者已裁定不受理重議：2a／2b 拆分、橋本體 blocked、技術取捨交委員會、GAP-3 另票；R1–R3 已裁決之取捨（vdW 空間、預設 enabled=True、`oos_guarantees` 沿用 root、reasons 唯一住 survivor 契約、case_id↔report_ref 檔名）不重開，除非附新碼證或新反例。

## R3 修訂摘要（請核對閉合）
- M1：§G-4 改為 `symbol`／`timeframe`↔報告 metadata（缺欄 raise）、`case_id`↔`report_ref` 檔名段（不比 metadata），與 Task 3.1 ⑮／Task 4.2 同一規則。
- M2：§C 白名單第 3 項／Task 1.0 既有 caller 句／§C ref 句統一為「report 契約只加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`；不加 reasons；reasons 不 ref」（`grep -n 'reasons 加\|reasons 增鍵' SPEC` → 0）。
- 新增 FACT-RECEIPT：真實 fixture `run_analyze()` → stage5 14→2、stage6 removed 0、`metadata.symbol=ETHUSDT`／`timeframe=12h`、`case_id=None`（三方同值）。

## 本 brief 前提
fact-verified: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`（Claude 實跑 2026-08-18）
fact-verified: 四份 synth `reconcile_stamps_check.sh` 皆 PASS（三家 APPROVED；stamp 輪 R1–R4）
assumed: SPEC 現況已無條文級矛盾（§G／§C／Task 1.0／1.2／3.1／4.1／4.2 對 reasons、身分三欄、event_identity、預算 gate 之敘述一致）← 請以 grep 機械核對（例：`grep -n 'reasons' SPEC`、`grep -n 'case_id' SPEC`、`grep -n 'event_identity' SPEC`）並貼結果
assumed: 五批 B1(1.0–1.3)→B2→B3→B4→B5 各批可獨立綠、無 forward dependency（R3 composer／grok 判成立）← codex 請獨立判定

## 必答
1. R2 L1–L5、R3 M1–M2 逐條閉合？未閉合處引 SPEC 行號＋反例。
2. 條文級矛盾 grep 核對結果（貼命令＋輸出）。
3. 可進 TODO？BLOCKING 清單（無 → 明寫「可進 TODO」）。

## Time-box 與範圍紀律
- 優先序＝必答 1 ＞ 3 ＞ 2。**不受理範圍**同 R1–R3。

## 產出
canonical 四欄 findings（或 sentinel）＋必答 1–3＋**Verdict**。禁改碼、禁改 SPEC。收尾清 /tmp workdir（保留 claude-501）。
