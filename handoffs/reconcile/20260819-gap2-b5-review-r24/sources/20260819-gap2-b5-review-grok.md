# GAP-2 B5 實作 code review（R24）— GROK

**task-id**: `20260819-GAP2-B5-REVIEW-R24`｜**family**: grok｜**輪次**: R24  
**brief**: `handoffs/20260819-gap2-b5-review-BRIEF.md`  
**審查標的**: commit `ffb728ab`（Task 5.1 前端最小鏡像；A1-4／A1-5）  
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit／push／禁就地改檔實驗／禁跑 python 探針**

**VERIFY（本輪實跑／讀 receipt）**:
- `cd frontend && npx vitest run src/components/ic-analysis/MarginalICTable.test.tsx src/store/icAnalysisStore.marginalIc.test.ts` → **9 passed** rc=0（~0.8s）
- `bash scripts/ic_wiring_check.sh` → **R1a(25)/R1b(17)/R2(11)/R3(7)** 全綠 rc=0
- `cd frontend && npx tsc --noEmit` → **8 error TS**，皆在 `FactorReturnChart.test.tsx`(4)／`useFeatureFactory.batchDate.test.ts`(4)；**本批路徑 0**
- `npm run build`：讀 receipt `handoffs/run_receipts/20260819-gap2-b5-npm-build.log` → **build_rc=0**（未重跑 build，避三家並行）
- §V 探針：讀最終 receipts B1 `20260819T031612Z`／B2 `20260819T031810Z`／B3 `20260819T031911Z`／B4 `20260819T032022Z` — 皆 ✅ 全部 RED＋RESTORED（未並行重跑探針）

---

## Verdict：可收案

Task 5.1（types／store／FeatureTierPanel／page 掛載／MarginalICTable＋9 vitest）**符合**契約與 A1-4／A1-5（含 basic-tab 補正）。段 B 八項實作期決定經獨立攻擊後**均可接受**（B-6 具名 preset `setState` 測為防禦性覆蓋、非假綠；B-7 tsc 八紅為白名單外既有測試債，應登記殘留、不擋本票）。段 E 四條 G2-R*「為何現在不做」**仍成立**；段 F 五批延伸決策無未落地互斥，§V 1–24 皆有 case 覆蓋且 receipts 逐條 RED。本輪無 BLOCKING／MAJOR／MINOR finding（sentinel `GROK-R24-P3-00`）。

---

## 段 A — 契約符合度（Task 5.1）

| 要點 | 結論 | 碼證 |
|------|------|------|
| 表格欄 feature／gross_ic／marginal_ic_loo／ci95／ic_retained_ratio／marginal_ic_train_insample＋composite 一列 | **符合** | `MarginalICTable.tsx` thead L70–77；composite 區塊 L103–117；數值 `fmt`→`toFixed(4)` |
| `status!=="ok"` ⇒ 只顯示 status／reason、不畫表 | **符合** | L35–43 → `SectionStatusNotice`；`queryByTestId('marginal-ic-table')` null（vitest） |
| `oos_guarantees===false` ⇒ degraded 樣式 | **符合** | L48／L57–64；`data-testid=marginal-ic-degraded` |
| 揭露文案恆顯示且**不含**「獨立 OOS 驗證」 | **符合** | `MARGINAL_IC_DISCLOSURE` L17；vitest `not.toContain` |
| 不畫圖表；除 `marginal_ic` 外未新 toggle；`CapabilityStatus` 六值未動 | **符合** | 元件僅 table；`TOGGLES` 只加一列 `marginal_ic`；ICHC 段六值仍 ok／not_applicable／not_computed／computation_failed／disabled／unavailable |
| toggle 關 ⇒ 送 `marginal_ic=false`（intermediate／advanced／custom） | **符合** | store 測三路徑；`getEffectiveConfig` custom L341＋具名 L378 |
| 掛載＝basic tab 末段（A1-5 補正）；頁面實際掛載 | **符合** | `page.tsx` L814–817；vitest 索引 `basic < mount < deep` |
| 白名單四檔＋新元件／測 | **符合** | `git show ffb728ab --stat` 恰四既有＋兩新元件＋store 測＋receipt |

註：A1-5／TODO 寫「`CorrelationHeatmap` 之後、同一 `<div>` 內」；實作將 `ChartErrorBoundary` 置於含 heatmap 之 **grid `</div>` 之後**、仍在 basic `TabsContent` 內（全寬表格合理）。功能意圖（basic 末段可見、不受 `deepTabVisible` 藏）已滿足； vitest 只鎖 basic＜mount＜deep。**不列 finding**。

---

## 段 B — 實作期決定複核（八項；優先攻）

| # | 議題 | 結論 |
|---|------|------|
| **B1 掛載點＝basic** | **接受**。`MarginalICTable` 在 basic `TabsContent` 末段，**無**額外條件渲染藏它（不像 deep 受 `deepTabVisible`）。`report` 為 null 時：`section={report?.marginal_ic}`⇒`undefined`⇒元件 `return null`；鄰近圖表同用 `report?.…` optional。Tabs 區塊本身不因 `!report` 卸載（`!report` 提示只在後處理區 L647）。`ChartErrorBoundary` 包裹與 basic 內 Cross-Sectional heatmap／deep 圖表一致；契約明文要求此包裹。 |
| **B2 metadata 交集型** | **接受**。`Record<string, unknown> & { survivor_output?: SurvivorOutputMeta }` 保留既有索引簽名並收窄可選鍵；較乾淨替代（獨立 interface 再交叉）收益小、非本票必要。 |
| **B3 `isMarginalICSection`／REASON_TEXT** | **接受（契約字面即可）**。guard＝`isSectionStatus`＋`per_feature` 為非 null object；純 status 走 `SectionStatusNotice`。`REASON_TEXT` 僅既有三鍵；未知 reason 走 `?? status.reason` 原字面——與「JSON SoT、不複列第二份文案表」一致。可選 UX 殘留見段 E，**不擋收案**。 |
| **B4 列級 `status!="ok"` 顯示 `status:reason`** | **接受**。loo 列可能 `not_computed:residual_degenerate` 等；顯示字面優於假數字／空白；表頭仍在、不誤導為數值。 |
| **B5 具名 preset 送 `marginal_ic`** | **接受（前端角度等價）**。三 preset `PRESET_TOGGLES.*.marginal_ic=true`＋具名分支 `stage_overrides.marginal_ic` 必送 ⇒ 後端一定收到 override；與 B4「出現才映射、缺則沿預設」搭配後，預設 ON 路徑閉環。關斷由 override=`false`（custom 或具名測徑）負責。wiring R1a 25／R1b 17 含此鍵。 |
| **B6 `toggleFeature`→custom 與具名測** | **接受（防禦性、非假綠）**。UI 關 toggle 確實變 custom（既有行為 L325）；測①實跑 `toggleFeature`→custom＋`marginal_ic=false`；`setState` 不改 tier 之分支是為鎖 `getEffectiveConfig` **具名** arm（否則該 arm 之 `marginal_ic:false` 無 UI 觸達）。形式＞部分實質路徑，但斷言真讀 config 輸出、非空轉——**不構成廉價綠燈**。 |
| **B7 tsc 八紅** | **接受主委判（白名單外、列殘留）**。本輪 `tsc --noEmit`：8 條全在 `FactorReturnChart.test.tsx`（最後 commit 2026-07-19）／`useFeatureFactory.batchDate.test.ts`（2026-07-14）；`ffb728ab` 未動此二檔；本批路徑 0 紅。TODO／SPEC 寫 `tsc rc=0` 與現況字面不符——應在收案殘留登記「B5 gate 之 tsc 全綠改為本批檔 0 紅＋既有八紅追蹤」，**不在本票修測試檔**（超白名單）。`npm run build` rc=0 仍成立。 |
| **B8 §V 24 覆蓋** | **接受（無缺 V-n）**。對照 SPEC §V 1–24 與四份最終 receipt：B1＝V-1..6／17a／18／21／22a；B2＝V-7..9；B3＝V-10..12／17b／19a..c／20；B4＝V-13..16／22／23／24。§V-17／19／22 之拆分 case 皆在；**無**未被任何 case 覆蓋之 V-n。 |

---

## 段 C — 測試品質

- **真 oracle**：揭露 `not.toContain("獨立 OOS 驗證")` 鎖 D3′ 子字串；page 掛載以原始碼索引斷言 basic＜mount＜deep（A1-5，非只測元件）；ok／disabled／degraded／空 survivors／`section=undefined` 皆有。
- **store 三路徑**：foundation／intermediate／advanced 預設 true；具名 false（setState）＋`toggleFeature` custom；custom 開關——對應驗證⑤。
- **廉價綠燈**：未見放寬斷言；page 測讀真實 `page.tsx` 檔而非 mock。缺項：無「legacy 整頁 smoke 掛載 React tree」——但 `section={undefined}`＋optional chaining 已覆蓋缺席不炸；整頁 RTL 非契約硬性。
- **mutation／探針**：B5 無新 python mutation（前端）；§V 24 依賴 B1–B4 receipts（段 F）。

---

## 段 D — 正確性

| 項目 | 判定 | 碼證 |
|------|------|------|
| `fmt` 四位；`ci95` null⇒「—」；負值顯示 | ✓ | `fmt`／`fmtCi`；vitest row-b 含 `—`、row 可含 `-0.0500` |
| composite 非 ok ⇒ 顯示 status[:reason] | ✓ | L111–115 |
| wiring R1a 25／R1b 17（`marginal_ic`∈映射） | ✓ | 本輪 `ic_wiring_check` R1a(25)/R1b(17) rc=0 |
| 列級非 ok 不顯示假數字 | ✓ | L91–93 |

---

## 段 E — registry「GAP-2 待補完」＋新殘留建議

| # | 觸發成立？ | 理由 |
|---|------------|------|
| G2-R1 | **否** | B5 只鏡像報告節／toggle；未接 ML `selected_features`；user-ruling 仍有效 |
| G2-R2 | **否** | 表格只報不選；D4 未破 |
| G2-R3 | **否** | 前端未啟 xsec 計算；後端仍 N/A；#4 未完工 |
| G2-R5 | **否** | 揭露仍「非獨立驗證」／`independent_oos_validation=false`；主線切分未升級 |

**建議登記之新殘留**（非本輪 finding；供收案文件化）：

| 項 | 為何現在不做 | 觸發 |
|----|--------------|------|
| tsc 既有 8 紅（`FactorReturnChart.test.tsx`／`useFeatureFactory.batchDate.test.ts`） | blocked-by: 白名單外既有測試債；GAP-2 B5 範圍不含 | 獨立 frontend hygiene／型別修票 |
| golden gate 嵌 bench ~2.5 分（B4 觀測） | user-ruling／needs-research: DX 成本非正確性缺陷（B4 已接受） | 標 slow 或拆腳本之治理／效能票 |
| `SectionStatusNotice.REASON_TEXT` 未含 GAP-2 reason | user-ruling: 契約字面足夠、避第二文案表（本輪 B-3 接受） | 若產品要中文友好文案再開 UX 小票 |

---

## 段 F — GAP-2 收案前總覽

**A1-1..A1-11**：逐條掃——A1-5 原文 deep vs 補正 basic 以補正為準且已落地；A1-4→A1-5 白名單 3→4 檔無互斥；A1-3 root OOS、A1-6 `write_failed` exact、A1-7 契約增值、A1-8 CI 包絡、A1-9 provenance／n_samples、A1-10 scrub、A1-11 落盤鏡像均屬 B1–B4 已閉合項，與 B5 前端消費無矛盾。**無未落地互斥**。

**契約 `ic_survivor_contract.json`**：`reasons.survivor_output` 含 `persist_suppressed`；`marginal_ic_section_keys.view_status_keys` 在場；`reasons.marginal_ic_feature` 含 `label_degenerate`；節級 reasons 長度與 A1-7 增值一致。與 B1–B4 消費路徑（loader／validator／orchestrator）先前 review 閉合；B5 僅型別鏡像＋展示，未另造鍵名。

**§V receipts（讀、未重跑）**：B1 10／B2 3／B3 8／B4 7＝28 case，對 24 條（含拆分）皆 `RED ✓`＋`RESTORED GREEN ✓`＋batch ✅。**無**「宣稱做了但沒證據」之批次。

**B5 證據鏈**：commit `ffb728ab`＋vitest 9＋wiring＋build receipt＋本輪 tsc 本批 0 紅。TODO 字面 `tsc rc=0` 與全專案 tsc 現況之差 → 段 E 殘留，非隱瞞。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 本輪 |
|------------|------|
| vitest 9 passed | **覆核** 9 passed rc=0 |
| npm build rc=0 | **讀 receipt** build_rc=0（未重跑） |
| wiring R1a 25／R1b 17… | **覆核** 全綠 rc=0 |
| tsc 8 既有紅、本批 0 | **覆核** 8 紅兩檔；本批路徑 none；git log 早於本票 |
| §V 四份最終 probe receipts rc=0 | **讀 receipt** 四批皆 ✅；未並行重跑 |
| 段 B 八項合理 | **逐項攻擊後接受**（見上表） |
| A1-1..A1-11 無互斥 | **段 F 逐條掃後接受** |

---

## Findings（canonical）

## GROK-R24-P3-00

**斷言**: 本輪對 commit `ffb728ab`（GAP-2 B5 Task 5.1）段 A–F（含段 B 八項實作期決定與收案前總覽）逐項核對後無 finding。

**碼證**: `cd frontend && npx vitest run …MarginalICTable.test.tsx …icAnalysisStore.marginalIc.test.ts` → 9 passed rc=0；`bash scripts/ic_wiring_check.sh` → R1a(25)/R1b(17)/R2(11)/R3(7) rc=0；`npx tsc --noEmit` → 8 紅僅 FactorReturnChart.test.tsx＋useFeatureFactory.batchDate.test.ts（本批路徑 0；該二檔 git log 2026-07-14／07-19）；build 讀 `20260819-gap2-b5-npm-build.log` build_rc=0；page.tsx L814–817 basic 末段 `ChartErrorBoundary`＋`MarginalICTable section={report?.marginal_ic}`（`report==null`⇒元件 null；無 deepTabVisible 藏）；PRESET 三档 `marginal_ic:true`＋custom／具名皆送 stage_overrides；TOGGLES 只加一列、計數 `TOGGLES.length`；CapabilityStatus 六值未改；揭露字串不含「獨立 OOS 驗證」；§V receipts B1–B4 共 28 case 皆 RED＋RESTORED 覆蓋 V-1..24；G2-R1..R5 觸發未成立；A1-1..A1-11 無未落地互斥。

**來源摘要**: frontend/src/components/ic-analysis/MarginalICTable.tsx#c8a4bd68ad04；frontend/src/components/ic-analysis/MarginalICTable.test.tsx#f3392cd54ab9；frontend/src/store/icAnalysisStore.marginalIc.test.ts#f72c7192e51e；frontend/src/store/icAnalysisStore.ts#ef361c4ce07c；frontend/src/lib/types.ts#0c308b8531ed；frontend/src/components/ic-analysis/FeatureTierPanel.tsx#b28327707832；frontend/src/app/ic-analysis/page.tsx#75c289a42a61；docs/GAP2_MARGINAL_IC_AMENDMENTS.md#ebd3a1466d4c；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；docs/IC_QUANT_GAP_REGISTRY.md#a119d3b21771；momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073；handoffs/20260819-gap2-b5-review-BRIEF.md#6bf701e0d184；handoffs/run_receipts/20260819T031612Z-gap2-B1-probe.log#ba4c6f539df8；handoffs/run_receipts/20260819T031810Z-gap2-B2-probe.log#df312c75283a；handoffs/run_receipts/20260819T031911Z-gap2-B3-probe.log#eae857630719；handoffs/run_receipts/20260819T032022Z-gap2-B4-probe.log#f2bf112c0e31；handoffs/run_receipts/20260819-gap2-b5-npm-build.log#6077accd6c13

核對依據：Task 5.1／A1-4／A1-5 對照源碼＋vitest／wiring／tsc／build receipt；段 B 八問獨立重判；§V 以四份最終 probe receipt＋腳本 case 表對 SPEC 1–24；registry 四殘留觸發未因 B5 成立；建議殘留（tsc 八紅／bench DX／REASON_TEXT）僅文件化、不升 finding。未發現需修補後才能收案之 B5 缺陷。

---

## §1 必查（11 類摘要）

1. 矛盾：無（A1-5 補正與實作一致；「同一 div」語意見段 A 註）。  
2. 漏項：B5 scope 內無（G2-R* 仍為登記殘留）。  
3. 不可測：vitest 9＋wiring＋build receipt＋§V receipts。  
4. quant：前端只展示；D3′ 文案鎖住；不改選擇集合。  
5–8. 過度工程／OOM／cache／API：無阻擋問題；型別鏡像＋一 toggle。  
9. 測試：真 oracle＋掛載索引；具名 setState 為防禦性、非假綠。  
10. Agent 可執行：檔案／掛載／驗證明確。  
11. 短命工：無（收案後表格／toggle 保留）。

STATUS: DONE
