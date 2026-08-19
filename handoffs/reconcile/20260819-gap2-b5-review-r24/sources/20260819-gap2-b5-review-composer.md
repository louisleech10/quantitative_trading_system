# GAP-2 B5 實作 code review（R24）— COMPOSER

**task-id**: `20260819-GAP2-B5-REVIEW-R24` | **family**: composer | **brief**: `handoffs/20260819-gap2-b5-review-BRIEF.md`
**審查標的**: commit `ffb728ab`（Task 5.1 前端最小鏡像；A1-4／A1-5 四檔白名單＋`MarginalICTable.tsx`／測試）
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit**

**VERIFY（本輪實跑）**:
- `cd frontend && npx vitest run src/components/ic-analysis/MarginalICTable.test.tsx src/store/icAnalysisStore.marginalIc.test.ts` → **9 passed** rc=0（~1s）
- `bash scripts/ic_wiring_check.sh` → **R1a(25)/R1b(17)/R2(11)/R3(7) 全綠** rc=0
- `cd frontend && npx tsc --noEmit` → **8 條既有紅**（`FactorReturnChart.test.tsx` 4／`useFeatureFactory.batchDate.test.ts` 4）；本批檔 **0 紅**
- build receipt：`handoffs/run_receipts/20260819-gap2-b5-npm-build.log` rc=0（未重跑 build，讀 receipt）
- §V 探針：讀 B1–B4 receipts（`20260819T031612Z`／`031810Z`／`031911Z`／`032022Z`）皆 RED+RESTORED GREEN（未重跑，互斥）

---

## Verdict：可收案

段 A Task 5.1 契約符合度**逐條成立**；段 B 八項實作期決定經獨立攻擊後**均可接受**；段 C 9 條 vitest 為真 oracle（掛載點原始碼索引＋D3′ 文案）；段 D wiring／fmt 正確；段 E registry 四條觸發**均未成立**；段 F 五批延伸決策無矛盾、§V 24 條全覆蓋。本輪無 BLOCKING／MAJOR／MINOR finding（sentinel `COMPOSER-R24-P3-00`）。

---

## 段 A — 契約符合度（Task 5.1）

| 要點 | 結論 | 碼證 |
|------|------|------|
| 表格欄（6 欄＋composite） | **符合** | `MarginalICTable.tsx` L71–76 thead；L103–116 composite 列 |
| `status!=="ok"` ⇒ 只顯示 status/reason | **符合** | L35–43 `SectionStatusNotice`；L91–92 列級 `status:reason` |
| `oos_guarantees===false` ⇒ degraded | **符合** | L48、L57–63 `data-testid="marginal-ic-degraded"` rose 樣式 |
| 揭露文案恆顯、禁「獨立 OOS 驗證」 | **符合** | L17 `MARGINAL_IC_DISCLOSURE`；L118–119；測試 `not.toContain` |
| 不畫圖表 | **符合** | 僅 `<table>`，無 chart import |
| 除 `marginal_ic` 外無新 toggle | **符合** | `FeatureTierPanel.tsx` TOGGLES L48 一列；`PRESET_TOGGLES` 僅加 `marginal_ic` |
| `CapabilityStatus` 六值未動 | **符合** | `types.ts` L2037–2043 仍六值 |
| toggle 關 ⇒ `marginal_ic=false` 三路徑 | **符合** | `icAnalysisStore.ts` L341 custom；L378 具名 preset；測試 3 條 |
| 節缺席不渲染 | **符合** | `MarginalICTable.tsx` L34 `if (!section) return null` |
| `ci95` null ⇒ 「—」 | **符合** | `fmt`/`fmtCi` L19–27；測試 row-b |
| 100+ 列可捲動 | **符合** | L67 `max-h-96 overflow-auto` |

---

## 段 B — 實作期決定複核（八項）

| # | 議題 | 結論 |
|---|------|------|
| **B1** 掛載點＝basic tab 末段 | **接受**。`page.tsx` L814–817 於 `TabsContent value="basic"` 內、`CorrelationHeatmap` 後；**無額外條件**包裹（非 `deepTabVisible`）。`report===null` 時 `section={undefined}` ⇒ `MarginalICTable` L34 不渲染、不炸頁；鄰近 `CorrelationHeatmap` 同樣 `report?.…`。`ChartErrorBoundary` 與 deep tab L830+ 同構。 |
| **B2** `metadata` 交集型別 | **接受**。`Record<string, unknown> & { survivor_output?: SurvivorOutputMeta }`（`types.ts` L2215）保留既有 `Record` 索引語意，又釘死五鍵；較 `interface ICReportMetadata extends …` 更窄、改動面更小。 |
| **B3** `isMarginalICSection`＋`REASON_TEXT` | **接受**。guard 以 `per_feature` object 判完整節（L2200–2205）；status object 走 `SectionStatusNotice`（`reason ?? undefined`）。`REASON_TEXT` 未加 GAP-2 reason ⇒ fallback 契約字面（L36 `?? status.reason`）——與 brief 主委判一致，避免第二份文案表漂移。 |
| **B4** 列級 `status!="ok"` 顯示 `status:reason` | **接受**。L91–92 對 `marginal_ic_loo` 欄顯示 `not_computed:residual_degenerate` 等字面，利於除錯；gross/ci95/retained 仍 fmt 數字或「—」，不誤導為有效 IC。 |
| **B5** 具名 preset 送 `marginal_ic` | **接受**。三 preset `PRESET_TOGGLES` 皆 `marginal_ic:true`（L90/118/146）；`getEffectiveConfig` 具名分支 L377–378 比照 fdr；後端「出現才映射」+ schema 預設 enabled ⇒ 三 preset ON 時**等價**於後端收到 true。 |
| **B6** `toggleFeature` 切 custom vs `setState` 測試 | **接受（非純形式）**。UI 真路徑：`toggleFeature` ⇒ `featureTier:'custom'`（L325–327）+ `stageOverrides.marginal_ic`（L341）；測試 L36–40 **亦覆蓋** `toggleFeature` 路徑。`setState` 段驗「具名 preset 分支在 tier 不變時仍映射」——程式化路徑存在於 `getEffectiveConfig` L371–382，屬合理分支覆蓋。 |
| **B7** `tsc` 8 條既有紅 | **確認與本批無關、本票不修**。8 條皆在 `FactorReturnChart.test.tsx`／`useFeatureFactory.batchDate.test.ts`；`git log -1 -- FactorReturnChart.test.tsx` → `4150f73b`（2026-07-19，早於 `ffb728ab`）；本批檔 tsc 0 紅。TODO 寫 `tsc rc=0` 為理想態——列**殘留**（白名單外），非 B5 阻擋。 |
| **B8** §V 24 條 mutation 覆蓋 | **全覆蓋**。B1：V-1..6／17a／18／21／22a（10）；B2：V-7..9（3）；B3：V-10..12／17b／19a-c／20（8）；B4：V-13..16／22／23／24（7）；合計 28 case 對映 V-1..24（V-17a/b、V-19a/b/c、V-22a/22 拆分）。四份 receipt 皆 baseline GREEN + 各 case RED+RESTORED GREEN。 |

---

## 段 C — 測試品質

- **vitest 6+3**：本輪 **9 passed**；ok 表格／disabled／degraded／空 survivors／節缺席／D3′ 文案／page 掛載索引／store 三 preset+custom+toggleFeature。
- **真 oracle**：`basicStart < mount < deepStart` 原始碼索引（`MarginalICTable.test.tsx` L93–100）防 deep-tab 回歸；`not.toContain('獨立 OOS 驗證')` 對 D3′ 硬約束。
- **非廉價綠**：掛載斷言讀真實 `page.tsx` 而非 mock router。
- **可補（非阻擋）**：未單測列級 `status!='ok'` 之 `status:reason` 字串、composite 非 ok 分支——程式路徑存在（L91–92、L111–115），屬覆蓋缺口非行為缺陷。

---

## 段 D — 正確性

| 項 | 結論 | 碼證 |
|----|------|------|
| `fmt` 4 位小數 | **符合** | L19–21 `toFixed(4)`；測試 `0.1234`／`0.2500` |
| `ci95` null ⇒ 「—」 | **符合** | `fmtCi` L24–26；測試 row-b |
| 負值顯示 | **符合** | fixture `marginal_ic:-0.05`（L43）；`fmt` 不 abs |
| composite 非 ok | **符合** | L111–115 `status:reason` |
| wiring R1a 25／R1b 17 | **符合** | `ic_wiring_check.sh` 本輪 rc=0；`marginal_ic`→`STAGE_OVERRIDE_PATHS` |

---

## 段 E — registry「GAP-2 待補完」＋新殘留

| # | 待補完 | 本輪是否觸發 | 結論 |
|---|--------|-------------|------|
| G2-R1 | IC→ML 橋 | 否 | `user-ruling` 仍成立 |
| G2-R2 | forward-stepwise 選擇 | 否 | `needs-research` 仍成立 |
| G2-R3 | xsec 邊際 IC | 否 | `blocked-by` #4 仍成立 |
| G2-R5 | nested/frozen final test | 否 | `blocked-by` 主線切分仍成立 |

**建議登記之新殘留**（非 B5 阻擋）：

| 項 | 三值理由 | 觸發條件 |
|----|---------|---------|
| 前端 `tsc --noEmit` 8 條既有紅 | `blocked-by:` 白名單外測試檔（FactorReturnChart／useFeatureFactory.batchDate）；與 B5 無交集 | 專票修測試型別或升級 union |
| `SectionStatusNotice` 無 GAP-2 reason 中文化 | `user-ruling:` 契約字面 fallback 優先於第二文案表（brief B3 主委判） | 委員會決定統一 reason 文案表 |
| SPEC TODO「`tsc rc=0`」與實態 8 紅 | `blocked-by:` 文件理想態 vs 既有債；B5 已驗本批 0 紅 + build rc=0 | tsc 債清後同步 TODO |

---

## 段 F — GAP-2 收案前總覽

- **A1-1..A1-11**：延伸檔與實作一致；A1-5 補正（basic tab 末段）已落地 `page.tsx` L814–817；A1-4 三檔 + page 四檔白名單吻合 commit stat。**無互相矛盾**。
- **`ic_survivor_contract.json`**：`persist_suppressed`／`view_status_keys`／`independent_oos_validation_allowed:[false]` 與 B1–B4 消費一致；前端 `MarginalICSection`／`SurvivorOutputMeta` 為鏡像型別（L2123–2206）。
- **§V receipts**：四批全 GREEN baseline + 各 V-n RED+RESTORED GREEN；**無**「宣稱做了但無 receipt」之批。
- **B5 證據鏈**：vitest 9 + build receipt + wiring R1a(25)/R1b(17) + 本輪 tsc 本批 0 紅。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| vitest 9 passed | fact-verified | **覆核 rc=0** |
| npm run build rc=0 | fact-verified | 讀 receipt `20260819-gap2-b5-npm-build.log`（未重跑） |
| ic_wiring_check R1a(25)/R1b(17) | fact-verified | **覆核 rc=0** |
| tsc 8 既有紅、本批 0 | fact-verified | **覆核**（8 條檔名與 brief 一致） |
| B1–B4 探針 rc=0 | fact-verified | 讀四 receipt（未重跑） |
| 段 B 八項合理 | assumed→**verified** | 段 B 表逐項攻擊 |
| A1-1..A1-11 無矛盾 | assumed→**verified** | 段 F 掃描 |

---

## Findings（canonical）

## COMPOSER-R24-P3-00

**斷言**: 本輪對 commit `ffb728ab` 段 A–F 與段 B 八項實作期決定逐項核對後，無達 BLOCKING／MAJOR／MINOR 門檻之可證偽缺陷。

**碼證**: `npx vitest run MarginalICTable.test.tsx icAnalysisStore.marginalIc.test.ts` → 9 passed rc=0；`bash scripts/ic_wiring_check.sh` → R1a(25)/R1b(17)/R3(7) rc=0；`npx tsc --noEmit` → 8 紅皆非本批檔；`MarginalICTable.tsx` 六欄表+composite+degraded+揭露；`page.tsx` L814–817 basic<mount<deep；`icAnalysisStore.ts` L90/118/146+341/378 三 preset 送 marginal_ic；§V B1–B4 receipts 28 case 覆蓋 V-1..24 全 RED+GREEN。

**來源摘要**: frontend/src/components/ic-analysis/MarginalICTable.tsx#c8a4bd68ad04；frontend/src/lib/types.ts#0c308b8531ed；frontend/src/store/icAnalysisStore.ts#ef361c4ce07c；frontend/src/app/ic-analysis/page.tsx#75c289a42a61；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073

本輪核對依據：Task 5.1 SPEC 要點 1–3／不可做／邊界逐條對照元件與 store；段 B 八問獨立重判（掛載點無額外 gating、metadata 交集型別、type guard、列級 status 字面、具名 preset 等價性、toggle 雙路徑測試、tsc 債歸屬、§V 全覆蓋）；段 E registry 四條觸發條件未滿足；段 F 延伸決策與契約 JSON 與 B1–B4 一致。段 C 列級/composite 非 ok 單測缺口記為建議項，不構成收案阻擋。

---

## §1 必查（11 類摘要）

1. 矛盾：無（A1-5 basic 補正已落地，與 SPEC 目標一致）。2. 漏項：B5 scope 內無。3. 不可測：vitest 9 + wiring + build receipt。4. quant：D3′ 揭露+`oos_guarantees` degraded——符合契約。5–8. 過度工程／OOM／cache／API 型別：B5 純前端鏡像，無問題。9. 測試：掛載索引+文案 oracle 真；列級 status 可補測。10. Agent 可執行：檔案／函式精確。11. 短命工：無。

---

ASSUMPTIONS_VERIFIED: vitest 9 passed；ic_wiring_check R1a(25)/R1b(17) rc=0；tsc 8 紅檔名與 brief 一致、本批 0 紅；§V 四 receipt 全覆蓋；page basic 掛載無額外 gating
TESTS_RUN: `npx vitest run src/components/ic-analysis/MarginalICTable.test.tsx src/store/icAnalysisStore.marginalIc.test.ts` 9 passed；`bash scripts/ic_wiring_check.sh` rc=0；`npx tsc --noEmit` 8 errors（非本批檔）
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查只讀）

STATUS: DONE
