# GAP-2 B5 實作 code review（三家全員；實作者＝Claude 主委，不自審；**最後一批——含 GAP-2 收案前總覽**）

VERIFY-EXEMPT:doc-example:gap2-b5-review-brief-questions

> 本檔為**派給委員的提問清單**：段 A–F 之敘述是「請你查證的問句與我的待攻決定」，不是主委的 operational 結論；實際結論在委員產出與收斂檔 `handoffs/reconcile/20260819-gap2-b5-review-r24/synth.md`。
> 🔴 **禁就地改任何 repo 檔做實驗**（in-memory only）；**禁跑 python 探針**（互斥；receipts 已附）；前端測試輕量可跑（`cd frontend && npx vitest run …` <10 秒；`npx tsc --noEmit` ~1 分鐘；`npm run build` ~2 分鐘、請勿三家同時跑 build——讀 receipt 即可）。

brief-kind: review

## 審查標的（commit `ffb728ab`；`git show ffb728ab --stat`）
- 既有檔改動（**白名單 §C#6＝A1-4＋A1-5 四檔**）：`frontend/src/lib/types.ts`（ICHC 契約段**外**加 `MarginalICPerFeature`／`MarginalICSequentialEntry`／`MarginalICComposite`／`MarginalICSection`／`SurvivorOutputMeta`／`isMarginalICSection`；`ICReport.marginal_ic`；`metadata` 交集型別加 `survivor_output`）；`frontend/src/store/icAnalysisStore.ts`（`PRESET_TOGGLES` 三 preset `marginal_ic:true`；`getEffectiveConfig` custom `stageOverrides.marginal_ic`＋具名 preset `stage_overrides.marginal_ic`）；`frontend/src/components/ic-analysis/FeatureTierPanel.tsx`（`TOGGLES` 加一列 L3；計數 `/24`→`/{TOGGLES.length}`）；`frontend/src/app/ic-analysis/page.tsx`（import＋**basic** `TabsContent` 末段 `CorrelationHeatmap` 後掛 `<ChartErrorBoundary><MarginalICTable section={report?.marginal_ic} /></ChartErrorBoundary>`——A1-5 補正）
- 新檔：`frontend/src/components/ic-analysis/MarginalICTable.tsx`＋`MarginalICTable.test.tsx`（6）；`frontend/src/store/icAnalysisStore.marginalIc.test.ts`（3）
- receipts：`handoffs/run_receipts/20260819-gap2-b5-npm-build.log`（rc=0）；§V 24 條探針最終實跑 receipts（B1–B4；見段 F）
- 契約來源：TODO（FROZEN）Task 5.1；SPEC Task 5.1／§C；AMENDMENTS A1-4／A1-5（含補正）；使用者裁決：表格＋toggle 預設開

## 本輪任務（六段皆必答）
**段 A — 契約符合度**：Task 5.1 實作要點 1–3／不可做／邊界／驗證逐條：表格欄（feature／gross_ic／marginal_ic_loo／ci95／ic_retained_ratio／marginal_ic_train_insample）＋composite 一列；`status!=="ok"` ⇒ 只顯示 status／reason 不畫表；`oos_guarantees===false` ⇒ degraded 樣式；揭露文案「倖存者選於同一測試段；本節數字為描述統計，非獨立驗證」恆顯示且**不含**「獨立 OOS 驗證」；不畫圖表；除 `marginal_ic` 外未新增 toggle；`CapabilityStatus` 六值未動；toggle 關 ⇒ 送 `marginal_ic=false`（intermediate／advanced／custom 三路徑）。

**段 B — 🔴 實作期決定（請攻）**：
1. **掛載點＝basic tab 末段**（A1-5 補正；deep tab 受 `deepTabVisible` gating）——請實核 `page.tsx` 該區塊是否有其他條件渲染會藏它（`report` 為 null 時整頁如何？）；`ChartErrorBoundary` 包裹是否與鄰近元件一致。
2. **`metadata` 型別改為 `Record<string, unknown> & { survivor_output?: SurvivorOutputMeta }`**（交集，不破既有 `Record` 用法）——可接受？有無更乾淨寫法。
3. **`isMarginalICSection` type guard**：以 `per_feature` 為 object 判「完整節」；status object（disabled／N/A）走 `SectionStatusNotice`（reason `null`→`undefined` 轉換）。`SectionStatusNotice` 之 `REASON_TEXT` 未加 GAP-2 reason 文案（顯示原字面）——是否該加？（我判：契約字面即可，避免第二份文案表。）
4. **表格對 `per_feature` 中 `status!="ok"` 之列**：`marginal_ic_loo` 欄顯示 `status:reason`（如 `not_computed:residual_degenerate`）而非數字——可接受？
5. **具名 preset 分支送出 `marginal_ic`**（比照 fdr）；後端 `_apply_tier_config` 具名分支「出現才映射、缺則沿 config 預設」（B4 段 B-7；不像 fdr 強制 True）——三家 B4 review 未反對；請於前端角度再判：三 preset 皆送 `marginal_ic` ⇒ 後端一定收到 ⇒ 等價。
6. **`toggleFeature` 會切成 custom**（既有行為）——store 測試以 `setState` 直接改 toggles 驗具名 preset 分支；是否為真路徑（UI 上關 toggle 就會變 custom，具名分支之 `marginal_ic:false` 實際只在「程式化改 toggles 不改 tier」時出現）？此測試是否形式大於實質？
7. **`tsc --noEmit` 有 8 條既有紅**（`src/components/ic-analysis/FactorReturnChart.test.tsx` 4／`src/hooks/useFeatureFactory.batchDate.test.ts` 4；`git log` 皆早於本票）；本批檔 0 紅；TODO 驗證寫 `tsc rc=0`——請確認這 8 條與本批無關（可 `git stash` 不行——請用 `git show HEAD~2:…` 對照或讀 `git log -1 -- <file>`），並判是否應在本票修（我判：白名單外既有測試檔，不動；列殘留）。
8. **§V 24 條 mutation 收尾**：B1（10）／B2（3）／B3（8）／B4（7）＝28 case 覆蓋 V-1..24（V-17a/b、V-19a/b/c、V-22a/22 拆分）；最終實跑 receipts 見段 F。是否有 V-n 未被任何 case 覆蓋？（請對照 SPEC §V 1–24 逐條。）

**段 C — 測試品質**：vitest 6＋3 是否為真 oracle（`not.toContain("獨立 OOS 驗證")`／page.tsx 掛載位置以原始碼索引斷言 basic<mount<deep）；有無廉價綠燈；缺什麼（例：`report.marginal_ic` 為 legacy 缺席時整頁不炸——`section={undefined}` 已測）。

**段 D — 正確性**：`fmt` 4 位小數、`ci95` null ⇒ 「—」；負值顯示；`composite` 非 ok ⇒ 顯示 status；wiring R1a 25／R1b 17（`marginal_ic` 映射至後端 `STAGE_OVERRIDE_PATHS`）。

**段 E — registry「GAP-2 待補完」四條之觸發是否已成立**（收案前最後一次）：
| # | 待補完項 | 為何現在不做 | 觸發條件 |
|---|---|---|---|
| G2-R1 | IC→ML 橋本體 | user-ruling: 2026-08-18 橋本體 blocked-by ML 層 | ML 層重寫或宣告穩定 |
| G2-R2 | 以邊際 IC 做 forward-stepwise 選擇 | needs-research: post-FDR 二次選擇多重比較政策無認可方法 | 委員會定出政策 |
| G2-R3 | xsec 路徑之邊際 IC | blocked-by: registry #4 Pooled/Panel IC | #4 完工 |
| G2-R5 | nested／frozen final test | blocked-by: IC 主路徑切分 holdout-only | 主線切分升級 |
請答：全票完工後四條「為何現在不做」是否仍成立；有無**新殘留**該登記（例：tsc 既有紅、bench 每次 gate 2.5 分鐘、`SectionStatusNotice` REASON_TEXT 未含 GAP-2 reason 文案）——請列出你認為該登記的項與三值理由。

**段 F — GAP-2 收案前總覽（每家獨立答）**：五批 A1-1..A1-11 延伸決策是否有互相矛盾或未落地者；契約 `ic_survivor_contract.json` 最終版（含 `persist_suppressed`／`view_status_keys`／三 reason 增值）是否與 B1–B4 實作一致；§V 24 條探針 receipts（B1 `handoffs/run_receipts/20260819T031612Z-gap2-B1-probe.log`／B2 `handoffs/run_receipts/20260819T031810Z-gap2-B2-probe.log`／B3 `handoffs/run_receipts/20260819T031911Z-gap2-B3-probe.log`／B4 `handoffs/run_receipts/20260819T032022Z-gap2-B4-probe.log`）逐條 RED；有無任何一批「宣稱做了但沒證據」。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0／§1／§3 與 canonical 四欄。ID＝`## <FAMILY>-R24-P<0-3>-<NN>`（**本輪＝R24**）。零 findings 用 sentinel `## <FAMILY>-R24-P3-00`（body 須實質）。

## ⚠️ 前置說明
- **禁改碼、禁改 SPEC／TODO／延伸檔、禁 commit／push、禁就地改檔實驗、禁跑 python 探針**；只產你自己的 review 檔。使用者裁決不受理重議。

## 本 brief 前提（逐條標）
fact-verified: `cd frontend && npx vitest run src/components/ic-analysis/MarginalICTable.test.tsx src/store/icAnalysisStore.marginalIc.test.ts` → 9 passed（Claude 實跑 2026-08-19）
fact-verified: `cd frontend && npm run build` → rc=0（receipt `handoffs/run_receipts/20260819-gap2-b5-npm-build.log`）；`bash scripts/ic_wiring_check.sh` → R1a(25)/R1b(17)/R2(11)/R3(7) rc=0
fact-verified: `cd frontend && npx tsc --noEmit` → 8 條既有紅（兩個非本批測試檔）；本批檔 0
fact-verified: §V 探針最終實跑：B1 `handoffs/run_receipts/20260819T031612Z-gap2-B1-probe.log`／B2 `handoffs/run_receipts/20260819T031810Z-gap2-B2-probe.log`／B3 `handoffs/run_receipts/20260819T031911Z-gap2-B3-probe.log`／B4 `handoffs/run_receipts/20260819T032022Z-gap2-B4-probe.log` 皆 rc=0
assumed: 段 B 八項為契約內合理選擇 ← 請攻（B-6 測試形式問題、B-7 既有 tsc 紅之處置最需判）
assumed: 五批延伸決策 A1-1..A1-11 無互相矛盾 ← 請於段 F 逐條掃

## Time-box
優先序＝段 B ＞ 段 F ＞ 段 E ＞ 段 C ＞ 段 A ＞ 段 D。**不受理**：使用者裁決、TODO 已 Frozen 之契約本身、治理機制、前端樣式美觀。

## 產出
Verdict（可收案／需修補後收案／有根本缺陷需重作）＋段 A–F 結論＋canonical findings。收尾清 /tmp workdir（保留 claude-501）。
