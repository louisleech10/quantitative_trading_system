# GAP-2a／2b SPEC adversarial 審查 R5（收斂確認輪；五份 reconcile 皆已三家 RECONCILE-STAMP APPROVED）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行。findings 用 canonical ID `## <FAMILY>-R5-P<0-3>-<NN>`；四欄含 `**來源摘要**: <路徑>#<sha256 前 12 碼>`。本輪輪次=R5。
若你確認 0 個實質 finding，寫 sentinel `## <FAMILY>-R5-P3-00`（body 四欄照填，內容為「逐項核對後無 finding」＋核對依據）。**勿為湊數捏造**；亦勿因「已五輪」而放水——有反例就列。

## 審查標的
- **SPEC（R4 修訂版）**：`docs/GAP2_MARGINAL_IC_SPEC.md`（`template_check spec` PASS）
- **收斂檔（皆已三家 RECONCILE-STAMP APPROVED；`bash scripts/reconcile_stamps_check.sh <path>` 各 rc=0）**：
  - `handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md`（偵察 C1–C7）
  - `handoffs/reconcile/20260818-gap2-x-review-r1/synth.md`（K1–K6）
  - `handoffs/reconcile/20260818-gap2-x-review-r2/synth.md`（L1–L5）
  - `handoffs/reconcile/20260818-gap2-x-review-r3/synth.md`（M1–M3）
  - `handoffs/reconcile/20260818-gap2-x-review-r4/synth.md`（N1–N3；codex 4 條 schema 釘死＋composer／grok sentinel）
- 你 R4 的 review：`handoffs/20260818-gap2-specadv-r4-<你的家族>.md`（codex：請複核 N1–N3 是否閉合；composer／grok：請對 R4 codex 四項修訂做獨立複核，勿只沿用上輪 sentinel）

## ⚠️ 前置說明
- SPEC 審查非實作審查；禁改碼、禁改 SPEC；只產你自己的 review 檔。
- 使用者已裁定不受理重議：2a／2b 拆分、橋本體 blocked、技術取捨交委員會、GAP-3 另票；R1–R3 已裁決之取捨（vdW 空間、預設 enabled=True、`oos_guarantees` 沿用 root、reasons 唯一住 survivor 契約、case_id↔report_ref 檔名）不重開，除非附新碼證或新反例。

## R4 修訂摘要（請核對閉合）
- N1：`metadata.survivor_output` 五鍵 `{status, reason, path, sha256, case_id}` 恆存在；非 ok ⇒ path/sha256 null；ok ⇒ reason null；Task 4.2 驗證⓪ 三形狀；V-24。
- N2：§G-1 改用 `scripts/gap2_freeze_golden.py::gap2_canonical_sha`（scrub 清單有序寫死含 `filtered_features_path`；兩 sidefx 目錄 sha 相等斷言）；Task 4.1 ⑮ 擴 `max_removed_candidates`＋`n_regressions` 語意；Task 4.3 加 k=200/n=20000 bench receipt＋`n_regressions==600`；§V OOM 邊界改 ✓ 計數 gate；V-22/V-23。
- N3：§C JSON SoT 段改指 Task 1.0 之 `ic_survivor_contract.json`。

## 本 brief 前提
fact-verified: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`（Claude 實跑 2026-08-18）
fact-verified: 五份 synth `reconcile_stamps_check.sh` 皆 PASS（三家 APPROVED；stamp 輪 R1–R5）
assumed: SPEC 現況已無條文級矛盾（含 R4 新增之 survivor_output 五鍵、gap2_canonical_sha、預算 oracle 敘述與 Task 3.1／4.1／4.2／4.3／§V 一致）← 請以 grep 機械核對並貼結果
assumed: 五批 B1(1.0–1.3)→B2→B3→B4→B5 各批可獨立綠、無 forward dependency（R3／R4 composer／grok 判成立）← codex 請獨立判定

## 必答
1. R4 N1–N3 逐條閉合？未閉合處引 SPEC 行號＋反例。
2. 條文級矛盾 grep 核對結果（貼命令＋輸出）。
3. 可進 TODO？BLOCKING 清單（無 → 明寫「可進 TODO」）。

## Time-box 與範圍紀律
- 優先序＝必答 1 ＞ 3 ＞ 2。**不受理範圍**同 R1–R4。

## 產出
canonical 四欄 findings（或 sentinel）＋必答 1–3＋**Verdict**。禁改碼、禁改 SPEC。收尾清 /tmp workdir（保留 claude-501）。
