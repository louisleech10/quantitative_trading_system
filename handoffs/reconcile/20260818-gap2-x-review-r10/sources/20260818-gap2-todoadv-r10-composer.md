brief-kind: review

# GAP-2a／2b TODO adversarial 審查 R10 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R10`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-todoadv-r10-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_TODO.md`（**DRAFT R4**）｜義務：`docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN）＋`docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..A1-6）｜R9 收斂：`handoffs/reconcile/20260818-gap2-x-review-r9/synth.md`（V1–V3）｜本輪 R9 review：`handoffs/20260818-gap2-todoadv-r9-composer.md`  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | R10 結論 |
|---|---|---|
| `template_check todo` PASS | fact-verified | **成立** — `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → `TEMPLATE PASS` |
| `todo_spec_crosscheck` SMOKE PASS | fact-verified | **成立** — `bash scripts/todo_spec_crosscheck.sh …` → `CROSSCHECK SMOKE PASS` |
| A1-5 補正（basic tab 非 deep） | assumed→verified | **成立且正確** — `page.tsx:214` `deepTabVisible` 只 gate deep trigger／`TabsContent`；`marginal_ic` 為 base `report` 節；TODO L257／§0⑥ 與 AMENDMENTS A1-5 補正 L28 一致 |
| A1-6 例外只進 log 可觀測 | assumed→accepted | **可接受** — Task 4.2 L220 明列 `error(..., exc_info=True)`；五鍵不增欄；⓪ mock `os.replace` 驗 `reason=="write_failed"` exact |
| Phase 小節 pointer＋同文不漂移 | assumed→verified | **成立** — B1 L110／B2 L145／B3 L178 逐字複製 §B 對應列且帶路徑；B4 L247 為 §B 指針（含三檔路徑摘要） |
| gate `mutation_probe_check` 與 `test_mutation_*` 對映 | assumed→verified | **成立** — §B L32–35 各路徑；各 Task 驗證欄具名 `test_mutation_*`；無參數探針 rc=1 |

---

## COMPOSER-R10-P3-00

**斷言**: R10 逐項核對 R9 群集 V1–V3 寫回、A1-5 basic-tab 補正、R8 抽核 U2／U4 後，TODO DRAFT R4 無新增 BLOCKING／MAJOR 缺口，可 Frozen 進 B1。

**碼證**: **V1** — §0 L12 ⑥ 四檔含 `page.tsx`＋basic `CorrelationHeatmap` 後掛載；Task 5.1 L257–262 插入點／`section={report?.marginal_ic}`／驗證⑥ `TabsContent value="basic"`；`grep MarginalICTable frontend/src` → 0（實作前預期）。**V2** — Phase B1 L110／B2 L145／B3 L178 與 §B L32–34 同文且 `mutation_probe_check.sh` 皆帶 test path；`bash scripts/mutation_probe_check.sh` → rc=1（用法提示）。**V3** — Task 4.2 L220 `reason` 契約字面 `write_failed` exact；L226 ⓪ mock `os.replace`；`grep write_failed:` TODO → 0。**A1-5** — `page.tsx:753–812` basic `TabsContent` 無 `deepTabVisible` gating；`:814` deep 區塊受 gating。**U2** — L201–202 刪 `fit_scope`→OOS 推導；`_inject_root_oos`；L211 ①③③′ root oracle。**U4** — L220 四 kwargs 顯式＋三 caller (a)(b)(c)；L226 ⑧ cold-call。RECHECK: 重跑上述 grep／template_check／crosscheck。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#596a4b810de5；docs/GAP2_MARGINAL_IC_AMENDMENTS.md#1b60f44e7448；frontend/src/app/ic-analysis/page.tsx#1344207f4f53

[P3] 信心度=High；本輪為 R9 修補後收斂複核，非新設計爭議。R9 本家 `COMPOSER-R9-P1-01`／`P2-01` 已由 V1／V2 關閉；未發現需重開之殘留。

---

## R10 必核（逐條 verdict；引 TODO 行號）

| 項 | verdict | 依據 |
|---|---|---|
| **V1** §0⑥ 四檔＋Task 5.1 步驟 3 basic 插入點 | **PASS** | §0 L12；L257–262；AMENDMENTS A1-5 補正 L28 |
| **V2** Phase Gate＝§B 同文、無無參數殘留 | **PASS** | L110／145／178；§B L32–35 |
| **V3** Task 4.2 `write_failed` exact＋⓪ | **PASS** | L220／L226 |
| **U2**（抽核）root OOS 注入 | **PASS** | L201–202／L211 |
| **U4**（抽核）persist 顯式 kwargs | **PASS** | L220／L226 ⑧ |
| **可 Frozen** | **是** | BLOCKING 清單：無 |

---

## §1 必查 11 類（摘要）

1. **矛盾/互斥**：無（R9 三群集已寫回且語意一致）。  
2. **漏项/端到端**：無（B5 page scope＋persist reason 已閉合）。  
3. **不可測驗收**：無。  
4. **可疑 quant 假設**：無。  
5. **過度工程**：無。  
6. **OOM/並行**：無（bench spy／receipt 觀測已列 L236）。  
7. **Cache 正確性**：無（U4 顯式 kwargs 仍成立）。  
8. **API/型別/相容**：無。  
9. **測試品質**：無。  
10. **Agent 可執行性**：無卡住點（冷啟動讀 TODO 即可派工 B1）。  
11. **必要性/短命工**：無。

---

## 必答 1 — Agent 可執行性

Task 1.0–5.1 皆具檔案／函式名／偽碼／不可做／驗證命令；B1 批內順序 1.0→1.3 明列；無「自行判斷」模糊句。執行端無需回讀 SPEC（§0 冷啟動原則成立）。

---

## 必答 2 — 義務覆蓋

§A D1–D7／D3′／D3″、§G 1–4、§V 24、§C 白名單（A1-4＋A1-5 四檔）、§N 四殘留 — 追溯表 L271–298 全對應；A1-3 root 注入、A1-6 reason 封閉、A1-5 掛載點與母 SPEC「頁面可見」語意方向一致（basic tab 補正合理）。

---

## 必答 3 — 批次獨立性

五批依 §B 拓撲；Task 4.0 為 B4 首件；4.2 契約增值 `persist_suppressed` 走 A1-1／B4 commit 邊界已標；無 forward dependency 新問題。

---

## 必答 4 — 取巧面

| 區域 | 風險 |
|---|---|
| B5 vitest 只測元件 | **已關** — L262 驗證⑥ 要求 page grep／掛載於 basic tab |
| `write_failed` 動態 reason | **已關** — A1-6 exact 字面 |
| bench `n_regressions` | 低 — spy 對證 L90／L236 |

---

## 必答 5 — 測試設計

各批 `test_mutation_*` 與 `mutation_probe_check.sh` 路徑、`gap2_mutation_probe.sh --batch Bn` 對映完整；V-19 三欄參數化為刻意例外；falsification 指向明確。

---

## 必答 6 — 可 Frozen？

**可 Frozen**（TODO DRAFT R4 → FROZEN → B1 實作）。

**BLOCKING 清單**：無。

---

## Verdict：可 Frozen

R9 三家 7 findings（V1–V3）於 DRAFT R4 已正確處置；A1-5 basic-tab 補正經獨立碼證成立；R8 U2／U4 抽核仍成立。本輪 0 實質 finding（sentinel `COMPOSER-R10-P3-00` 記錄收斂複核）。

---

ASSUMPTIONS_VERIFIED: template_check PASS；crosscheck SMOKE PASS；V1–V3 逐條 grep／行號對照；`deepTabVisible`／basic `TabsContent` 結構；`mutation_probe_check` 無參數 rc=1；`write_failed:` 在 TODO 0 命中；MarginalICTable 現況 0 命中（實作前）  
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS rc=0；`bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` → SMOKE PASS rc=0；`bash scripts/mutation_probe_check.sh` → rc=1（用法提示）；`grep -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` → 0 rc=1；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-todoadv-r10-composer.md --family composer` → PASS rc=0（1 canonical ID）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（審查只讀）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-todoadv-r10-composer.md`  
TMP_CLEANUP: 嘗清 `/private/tmp`／`/tmp` 之 `agent_dc_snapshot.txt`、`mprobe.out`、`sessions` — shell 權限阻擋未執行；`claude-501` 未動  
HANDOFF_NOT_UPDATED: 根 `HANDOFF.md` 由 Claude 維護；本輪 append → `handoffs/20260818-GAP2-X-REVIEW-R10.md`
