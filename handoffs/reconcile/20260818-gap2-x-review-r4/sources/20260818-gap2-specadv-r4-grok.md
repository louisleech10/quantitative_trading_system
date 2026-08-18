# GAP-2a／2b SPEC adversarial 審查 R4 — GROK

**task-id**: `20260818-GAP2-X-REVIEW-R4`｜**family**: grok｜**輪次**: R4  
**brief**: `handoffs/20260818-gap2-specadv-r4-BRIEF.md`  
**審查標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`＃`2d4d19b3cd7e`（R3 修訂版）  
**R2 收斂**: `handoffs/reconcile/20260818-gap2-x-review-r2/synth.md`＃`002a38a79468`  
**R3 收斂**: `handoffs/reconcile/20260818-gap2-x-review-r3/synth.md`＃`5a87a1545899`  
**本家 R3**: `handoffs/20260818-gap2-specadv-r3-grok.md`  
**禁改碼／禁改 SPEC**（只產本檔）

**VERIFY（本輪實跑）**:
- `shasum -a 256 docs/GAP2_MARGINAL_IC_SPEC.md` → `2d4d19b3cd7e…`
- `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`
- 四份 synth `bash scripts/reconcile_stamps_check.sh <path>` → 各 `PASS`／`rc=0`（consult-r1／review-r1／r2／r3）
- `grep -nE 'reasons 加|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md` → **0 命中**
- `grep -n '不加 reasons' docs/GAP2_MARGINAL_IC_SPEC.md` → L63／L106／L107／L200（§C／Task 1.0／Task 4.1 一致）
- `grep -n '檔名段\|不比.*metadata\|不改 report metadata' docs/GAP2_MARGINAL_IC_SPEC.md` → §G-4 L97、Task 3.1⑮ L179、Task 4.2 L213 同規則
- `sed -n '3857,3862p' momentum/Analysis/ic_filter_orchestrator.py` → `_resolve_case_id` 缺 `metadata.case_id` ⇒ `"ic_gatekeeper"`（檔名段 SoT；與 L3／M1 一致）
- SPEC §A FACT-RECEIPT L32：`run_analyze()` → stage5 14→2、stage6 removed 0、`symbol=ETHUSDT`／`timeframe=12h`、`metadata.case_id=None`（本輪引用；未重跑長 analyze）

---

## Verdict：可派工

R2 L1–L5 與 R3 M1–M2 文面＋機械 grep 全閉合；§C／§G-4／Task 1.0／1.2／3.1／4.1／4.2 對 reasons SoT、身分三欄、`event_identity`、預算 gate 敘述一致。五批 B1→B5 無 B1→B4 reasons forward dependency。**可進 TODO**。

**BLOCKING 清單**：無 → **可進 TODO**。

---

## 挑戰 brief assumed（§0）

| assumed | verdict | 證據 |
|---|---|---|
| SPEC 現況已無條文級矛盾（reasons／身分／event_identity／預算） | **成立** | 見必答 2 grep；R3 殘句（§G-4 metadata case_id、§C「reasons 加」）已消失 |
| 五批 B1(1.0–1.3)→B2→B3→B4→B5 各批可獨立綠、無 forward dependency | **成立** | reasons 唯一住 Task 1.0 survivor 契約；report 契約增鍵僅 Task 4.1 同 commit；B3 不改 report 契約；批間僅宣告上游依賴（B2←B1、B3←B1/B2 欄名、B4←B1–B3、B5←B4） |
| 四份 synth 三家 RECONCILE-STAMP APPROVED | **成立（本輪實跑）** | 四次 `reconcile_stamps_check.sh` 皆 rc=0 |

---

## Findings

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——R2 L1–L5 與 R3 M1–M2 於 R3 修訂版 SPEC 皆已閉合；§C／§G／Task 對 reasons、身分三欄、`event_identity`、預算 gate 無互斥殘句；五批無 forward dependency；可進 TODO。

**碼證**: L1：L88 已刪 raw>0.10、改 O1a raw 非退化⇒ok 假紅，表內 σ 寫死。L2：L63／L106／L107／L200「不加 reasons」＋`grep reasons 加|reasons 增鍵`→0；reasons 唯一列舉 Task 1.0。L3／M1：L97 §G-4＝symbol／tf↔metadata、case_id↔`report_ref` 檔名段（不比 metadata），與 L179⑮／L213 同規則；`_resolve_case_id`→`ic_gatekeeper`。L4：L106／L178／L202／L179⑱ event_identity cache owner＋序列化。L5：L130／L200 `max_*=200`＋整體 `candidate_budget_exceeded`；V-13／V-19 在 L259／L265。M2：§C 白名單第 3 項已改只加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`。RECHECK：重跑 VERIFY 列 grep／`template_check`／四份 `reconcile_stamps_check.sh`；對照 L97 vs L179 vs L63 vs L200。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2d4d19b3cd7e

[P3] 信心度=High。核對依據＝上列機械 grep＋§G／§C／Task 交叉讀＋R2／R3 synth 處置對照；R3 本家 P0-01／P1-01 修法皆已寫回。觀察（不升格）：§V 邊界 L270 仍寫「k≤數十…OOM 不測」而預算預設 200——降載已改計數 gate，該句過時文案，不阻 TODO。

---

## 必答

### 1. R2 L1–L5、R3 M1–M2 逐條閉合？

| 群集 | 閉合？ | 說明 |
|---|---|---|
| L1 O1 raw／O4 σ | **是** | L88 刪 raw>0.10；V-2→O1a；規格表 σ 寫死（O1／O7=0.866、O2=0.812、O4=0.8） |
| L2 reasons SoT | **是** | survivor 契約唯一列舉；report 不加 reasons；無 `reasons_ref` 正向設計（僅「不設」字樣）；R3 殘句已清 |
| L3 身分對照 | **是** | symbol／tf↔metadata（缺 raise）；case_id↔檔名段；Task 4.2 `identity_missing`；§G-4 已跟 Task 3.1⑮ |
| L4 event_identity | **是** | stage3 pop 前寫 `_ic_cache`；refilter 只讀；`_doc` 序列化；驗證⑬⑱ |
| L5 預算／V-19／V-13 | **是** | `max_*=200`、整體超限 reason、V-19 三欄、V-13 反向 |
| M1 §G-4 case_id | **是** | L97 與 Task 3.1⑮／4.2 同一規則（R3 GROK-R3-P0-01 修法已落地） |
| M2 §C／Task 1.0 reasons | **是** | L63／L107 統一不加 reasons；`grep reasons 加|reasons 增鍵`→0 |

未閉合處：無。

### 2. 條文級矛盾 grep 核對結果

```text
$ grep -nE 'reasons 加|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md
# （無輸出）

$ grep -n '不加 reasons' docs/GAP2_MARGINAL_IC_SPEC.md
63:  …**不加 reasons**…（reason 字面唯一住 ic_survivor_contract.json#reasons…）
106: …ic_report_contract.json 不加 reasons…
107: …**不加 reasons**…
200: …（**不加 reasons**——R2 L2…）

$ grep -n 'case_id' docs/GAP2_MARGINAL_IC_SPEC.md | head
# 關鍵：L32 FACT case_id=None；L97 檔名段不比 metadata；L179⑮ 同；L213 _resolve_case_id
# 無「case_id 與報告 metadata exact 相等」殘句

$ grep -n 'event_identity' docs/GAP2_MARGINAL_IC_SPEC.md
# L106 keys＋_doc；L178 cache owner；L179⑱；L202 stage3；L203⑬ — 一致
```

四份 stamp：`reconcile_stamps_check.sh` ×4 → 皆 `PASS` rc=0。

### 3. 可進 TODO？BLOCKING 清單

**可進 TODO。** BLOCKING＝無。MAJOR＝無。MINOR 實質 finding＝無（L270「k≤數十」過時文案僅觀察，建議 TODO 起草時順手改「計數 gate 已覆蓋；OOM 具名不測」）。

---

## §1 必查（11 類）

1. 矛盾／互斥：無（R3 兩處已修）  
2. 漏項／端到端：無（L1–L5／M1–M2 落地）  
3. 不可測驗收：無（§G oracle＋§V 21 條＋各 Task 驗證令牌齊）  
4. 可疑 quant：無新洞（L1 前輪實跑已落帶；本輪未重跑 oracle）  
5. 過度工程：無  
6. OOM／並行：預算計數 gate 在；L270 文案過時＝觀察  
7. Cache：event_identity owner 已寫 — 無  
8. API／型別：無跨域；B5 不改 CapabilityStatus  
9. 測試品質：V-13 反向／V-19 三欄／mutation 探針分批 — 無  
10. Agent 可執行性：白名單與 Task 對齊 — 無  
11. 必要性／短命工：Task 2.1 搬 bootstrap 為同批刻意合併（已具名覆蓋風險）— 無不當白工  

## 被當成事實的未驗證假設（§0）

- 「R3 修訂後全文一致」— **本輪 verified**（grep＋交叉讀）  
- 「`metadata.case_id` 於真路徑可為 None」— **fact（§A receipt＋`_resolve_case_id`）**；L3／M1 設計與此對齊  
- 「預算 200 誤傷 golden fixture」— **false（§A：survivors=2≪200）**；本輪未重跑 analyze，依 receipt  

---

ASSUMPTIONS_VERIFIED: L1–L5／M1–M2 文面閉合；reasons／case_id／event_identity grep；四份 stamp rc=0；template_check PASS；`_resolve_case_id` 預設 ic_gatekeeper
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → TEMPLATE PASS；`bash scripts/reconcile_stamps_check.sh` ×4 → PASS rc=0；`grep -nE 'reasons 加|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md` → 0；未重跑 `run_analyze()`／oracle（依 §A receipt＋R3 本家 VERIFY）
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀；未改 SPEC／碼）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_ARTIFACT: handoffs/20260818-gap2-specadv-r4-grok.md
TMP_CLEANUP: 見收尾（保留 /tmp/claude-501）
STATUS: DONE
