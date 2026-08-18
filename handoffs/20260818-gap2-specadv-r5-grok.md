# GAP-2a／2b SPEC adversarial 審查 R5 — GROK

**task-id**: `20260818-GAP2-X-REVIEW-R5`｜**family**: grok｜**輪次**: R5（收斂確認）  
**brief**: `handoffs/20260818-gap2-specadv-r5-BRIEF.md`  
**審查標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`＃`a7703a4761ca`（R4 修訂版）  
**R4 收斂**: `handoffs/reconcile/20260818-gap2-x-review-r4/synth.md`＃`22a862b23fdb`（N1–N3）  
**本家 R4**: `handoffs/20260818-gap2-specadv-r4-grok.md`（sentinel；本輪對 R4 codex 四項修訂獨立複核，未沿用上輪結論）  
**禁改碼／禁改 SPEC**（只產本檔）

**VERIFY（本輪實跑）**:
- `shasum -a 256 docs/GAP2_MARGINAL_IC_SPEC.md` → `a7703a4761ca…`
- `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`／rc=0
- 五份 synth `bash scripts/reconcile_stamps_check.sh <path>` → 各 `PASS`／rc=0（consult-r1／review-r1／r2／r3／r4）
- `grep -n 'Task 3\.1 之契約檔' docs/GAP2_MARGINAL_IC_SPEC.md` → **0 命中**（N3）
- `grep -n 'Task 1\.0 之契約檔' docs/GAP2_MARGINAL_IC_SPEC.md` → L69（N3 更正落地）
- `grep -n '五鍵恆存在\|gap2_canonical_sha\|max_removed_candidates\|n_regressions == 200\|驗證⓪\|V-22\|V-23\|V-24' docs/GAP2_MARGINAL_IC_SPEC.md` → L76／L203／L211／L214／L224／L268–L270／L273 皆命中
- `grep -nE 'reasons 加|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md` → **0**
- `grep -n 'k≤數十' docs/GAP2_MARGINAL_IC_SPEC.md` → **0**（R4 觀察之過時文案已隨 N2 消失）

---

## Verdict：可派工

R4 N1–N3 於修訂版 SPEC 文面＋機械 grep 全閉合；§C／§G-1／Task 1.0／4.1／4.2／4.3／§V 對 survivor_output 五鍵、`gap2_canonical_sha`、預算 oracle 敘述一致。五批 B1→B5 無 forward dependency。**可進 TODO**。

**BLOCKING 清單**：無 → **可進 TODO**。

---

## 挑戰 brief assumed（§0）

| assumed | verdict | 證據 |
|---|---|---|
| SPEC 現況已無條文級矛盾（含 R4 新增之 survivor_output 五鍵、gap2_canonical_sha、預算 oracle 與 Task／§V 一致） | **成立** | 見必答 1–2；N1–N3 對照表 |
| 五批 B1(1.0–1.3)→B2→B3→B4→B5 各批可獨立綠、無 forward dependency | **成立** | Phase 標頭僅宣告上游依賴；reasons 唯一住 Task 1.0；report 契約增鍵僅 Task 4.1 同 commit；B3 不改 report 契約 |
| 五份 synth 三家 RECONCILE-STAMP APPROVED | **成立（本輪實跑）** | 五次 `reconcile_stamps_check.sh` 皆 rc=0 |

---

## Findings

## GROK-R5-P3-00

**斷言**: 本輪逐項核對後無 finding——獨立複核 R4 N1–N3 於修訂版 SPEC 皆已閉合；survivor_output 五鍵／`gap2_canonical_sha`／預算 oracle／§C Task 1.0 SoT pointer 與 Task 4.1／4.2／4.3／§V 無互斥；五批無 forward dependency；可進 TODO。

**碼證**: N1：L211 五鍵恆存在＋nullable 規則；L214 驗證⓪ 三形狀；V-24 L270。N2：L76 `gap2_canonical_sha` 有序 scrub（含 `filtered_features_path`）＋兩 sidefx sha 相等；L203 驗證⑮ `max_removed_candidates`＋`n_regressions` 語意；L224 k=200／n=20000 bench＋`n_regressions==600`；L273 OOM ✓ 計數 gate；V-22／V-23 L268–269。N3：`grep 'Task 3.1 之契約檔'`→0；L69 改指 Task 1.0 `ic_survivor_contract.json`。前置：`template_check` PASS；五份 stamp PASS。RECHECK：重跑 VERIFY 列 grep／stamp／template；對照 L69／L76／L203／L211／L214／L224／L268–L273。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#a7703a4761ca

[P3] 信心度=High。核對依據＝上列機械 grep＋N1–N3 與 Task／§V 交叉讀＋R4 synth 處置對照；未沿用本家 R4 sentinel。觀察（不升格、不阻 TODO）：(a) L213 改法失敗形狀仍寫兩鍵 shorthand，但同 Task L211／L214⓪／V-24 已釘五鍵＋null；(b) L211 正文誤寫「驗證⑦」而實際為驗證⓪（V-24 已指 ⓪）；(c) L74 仍括註「沿用 ichc_run.canonical_sha」，L76 已定 `gap2_canonical_sha` 為唯一序列化（④ 其餘沿用 ichc_run）——實作者以 L76 為準。

---

## 必答

### 1. R4 N1–N3 逐條閉合？

| 群集 | 閉合？ | 說明 |
|---|---|---|
| N1 survivor_output 五鍵／三形狀 | **是** | L211 五鍵＋nullable；L214 ⓪；V-24；失敗省略鍵會被 ⓪／V-24 擋 |
| N2 gap2_canonical_sha／預算 oracle／OOM | **是** | L76 scrub＋sidefx；L203⑮；L224 bench＋600；L273 計數 gate；V-22／V-23；`k≤數十` 已消失 |
| N3 §C JSON SoT → Task 1.0 | **是** | L69；`Task 3.1 之契約檔` grep＝0；Task 3.1 仍只做 resolver／validator（L174） |

未閉合處：無（上列觀察不構成未閉合反例）。

### 2. 條文級矛盾 grep 核對結果

```text
$ bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md
TEMPLATE PASS (spec): docs/GAP2_MARGINAL_IC_SPEC.md 含全部必填錨點，且無明顯空殼。

$ grep -n 'Task 3\.1 之契約檔' docs/GAP2_MARGINAL_IC_SPEC.md
# （無輸出）

$ grep -n 'Task 1\.0 之契約檔' docs/GAP2_MARGINAL_IC_SPEC.md
69: …只在 Task 1.0 之契約檔 `ic_survivor_contract.json` 出現一次（R4 CODEX-R4-P2-04 更正）…

$ grep -n '五鍵恆存在\|gap2_canonical_sha\|max_removed_candidates' docs/GAP2_MARGINAL_IC_SPEC.md
# L76 gap2_canonical_sha；L128/130/200/203 max_removed；L211 五鍵恆存在；L214 ⓪

$ grep -nE 'reasons 加|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md
# （無輸出）

$ grep -n 'k≤數十' docs/GAP2_MARGINAL_IC_SPEC.md
# （無輸出）
```

五份 stamp：`reconcile_stamps_check.sh` ×5 → 皆 `PASS` rc=0。

### 3. 可進 TODO？BLOCKING 清單

**可進 TODO。** BLOCKING＝無。MAJOR＝無。MINOR 實質 finding＝無。

---

## §1 必查（11 類）

1. 矛盾／互斥：無（N1–N3 落地；觀察 a–c 不升格）  
2. 漏項／端到端：無（persist→metadata→validator 三形狀已釘）  
3. 不可測驗收：無（⓪／⑮／bench／V-22..24）  
4. 可疑 quant：無新洞（本輪未重開已裁定取捨）  
5. 過度工程：無  
6. OOM／並行：計數 gate＋receipt 在；舊「k≤數十」已清  
7. Cache：event_identity 既有條文不變 — 無  
8. API／型別：無跨域；B5 不改 CapabilityStatus  
9. 測試品質：mutation 22–24 對映 N1–N2 — 無  
10. Agent 可執行性：SoT pointer 已改 Task 1.0 — 無  
11. 必要性／短命工：無不當白工  

## 被當成事實的未驗證假設（§0）

- 「R4 修訂後 N1–N3 全文一致」— **本輪 verified**（grep＋交叉讀）  
- 「預算 200／k=200／n=20000 之 peak RSS 可接受」— **assumption（本輪未跑 bench；SPEC 以 receipt 為 Task 4.3 驗收，不阻 TODO）**  
- 「五批無 forward dependency」— **本輪 verified**（Phase 依賴＋reasons／report 契約落點）

---

ASSUMPTIONS_VERIFIED: N1–N3 文面閉合；survivor_output／gap2_canonical_sha／預算／SoT pointer grep；五份 stamp rc=0；template_check PASS；reasons 加／k≤數十 負向 grep
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → TEMPLATE PASS rc=0；`bash scripts/reconcile_stamps_check.sh` ×5 → PASS rc=0；`grep -n 'Task 3\.1 之契約檔'` → 0；`grep -nE 'reasons 加|reasons 增鍵'` → 0；`grep -n 'k≤數十'` → 0；`shasum -a 256 docs/GAP2_MARGINAL_IC_SPEC.md` → a7703a4761ca…
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀；未改 SPEC／碼）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_ARTIFACT: handoffs/20260818-gap2-specadv-r5-grok.md
TMP_CLEANUP: /tmp/grok-gap2-specadv-r5 將清；保留 /tmp/claude-501
STATUS: DONE
