# GAP-2 TODO adversarial — GROK R9（TODO DRAFT R3＋A1-1..4 複核；預期收斂輪）

family: grok｜task-id: 20260818-GAP2-X-REVIEW-R9｜brief: `handoffs/20260818-gap2-todoadv-r9-BRIEF.md`
標的：`docs/GAP2_MARGINAL_IC_TODO.md`（DRAFT R3）｜義務來源：`docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN）＋`docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..4）｜R8 收斂：`handoffs/reconcile/20260818-gap2-x-review-r8/synth.md`（U1–U10）

來源摘要前綴（本輪 `shasum -a 256`）：
- TODO：`docs/GAP2_MARGINAL_IC_TODO.md#96facb832358`
- AMEND：`docs/GAP2_MARGINAL_IC_AMENDMENTS.md#406378dd304c`
- SPEC：`docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d`
- R8 synth：`handoffs/reconcile/20260818-gap2-x-review-r8/synth.md#ea42b2aa7312`
- 本家族 R8：`handoffs/20260818-gap2-todoadv-r8-grok.md#89fcab2ff0ca`
- page.tsx：`frontend/src/app/ic-analysis/page.tsx#77341721b6f0`

## Verdict：需修補

R8 本家族四條（P0-01／P0-02／P1-01／P1-02）與 U1–U10 接受項皆已落到 TODO R3／A1-4；U6 駁回碼證可重現。但 brief **assumed**「A1-4 三檔已足、B5 不需再碰其他既有前端檔」被實核推翻：Task 5.1 步驟 3「接入 IC 結果頁 deep 區塊之後」必改既有容器 `frontend/src/app/ic-analysis/page.tsx`，該檔不在 A1-4／§0／Task 5.1「修改檔案」清單。另 Phase B1 摘要 gate 仍殘無路徑之 `mutation_probe_check.sh`（§B 已正確）。**不可 Frozen**；修 A1-5（擴白名單含 `page.tsx`）＋TODO §0／5.1 同步，並清 L110 殘句後再 Frozen。

BLOCKING：`GROK-R9-P0-01`（1）。MINOR：`GROK-R9-P2-01`（1）。

---

## GROK-R9-P0-01

**斷言**: Task 5.1 步驟 3 要求把 `MarginalICTable`「接入 IC 結果頁 deep 區塊之後」，但 A1-4／TODO §0⑥／Task 5.1「修改檔案」只准改 `types.ts`／`icAnalysisStore.ts`／`FeatureTierPanel.tsx`＋**新增**表格檔；實核 deep 結果頁容器為既有檔 `frontend/src/app/ic-analysis/page.tsx`（顯式 import＋於 `TabsContent value="deep"` 末掛載各圖，例 NetICChart），該檔未列白名單——執行端守白名單則表格永不可見，改之則違反 §0／A1-4。標 **SPEC 義務側**。

**碼證**: TODO L257「接入 IC 結果頁 deep 區塊之後」；L258 修改檔案＝A1-4 三檔＋新 `MarginalICTable.tsx`（無 `page.tsx`）。A1-4 L17-19 擴 §C#6 僅三檔。SPEC Task 5.1 L236 亦寫「接入現有 IC 結果頁 deep 區塊之後」但 §C#6（母檔）／A1-4 皆無 `page.tsx`。VERIFY：`grep -n 'page\.tsx\|ic-analysis/page' docs/GAP2_MARGINAL_IC_{TODO,AMENDMENTS,SPEC}.md` → 0；`frontend/src/app/ic-analysis/page.tsx:814-916` deep tab 以具名 import 掛載（末段 NetICChart `:904-914`），無動態元件註冊。RECHECK: §0／A1-5／Task 5.1 修改檔案是否列入 `page.tsx`（僅 import＋deep 末掛 `MarginalICTable`，不改其他區塊）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358；docs/GAP2_MARGINAL_IC_AMENDMENTS.md#406378dd304c；frontend/src/app/ic-analysis/page.tsx#77341721b6f0

[BLOCKING] 信心度=High。失敗模式＝R8 FeatureTierPanel 白名單洞之同構：B5「報告新節在 IC 頁面可見」與「白名單外一律不碰」互斥。修法：延伸檔 **A1-5** 把 `frontend/src/app/ic-analysis/page.tsx` 納入 §C（範圍限：import＋deep tab 末掛載 `MarginalICTable`）；TODO §0⑥／Task 5.1 修改檔案與 A1-5 逐字一致。勿為過關把「接入」改寫成只測 vitest 不掛頁面（違反 Task 目標「頁面可見」）。

---

## GROK-R9-P2-01

**斷言**: U9 要求各批 gate 之 `mutation_probe_check.sh` 必帶路徑；§B L32–35 已寫對，但 Phase B1「測試＋Gate」L110 仍寫無參數 `bash scripts/mutation_probe_check.sh`（實跑必 rc=1），且 Phase B2 L145／B3 L178 摘要完全省略該檢查——執行端若跟 Phase 摘要而非 §B 會假失敗或漏跑。

**碼證**: TODO L110：`bash scripts/mutation_probe_check.sh` 對新檔綠（無路徑）；對照 §B L32 已含兩測試路徑。VERIFY：`bash scripts/mutation_probe_check.sh` → `用法: ... <test_path>...` rc=1。L145／L178 無 `mutation_probe_check` 字樣，而 L33–34 有。RECHECK: 三處 Phase Gate 摘要是否與 §B 同文（或改「見 §B」單一來源）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358

[MINOR] 信心度=High。不阻 B1 若執行端以 §B 為準；但 L110 原文可導致 B1 收尾硬紅。修法：L110 改與 L32 同路徑命令；L145／L178 補 §B 對應 `mutation_probe_check` 或改 pointer「見 §B」。

---

## 被當成事實的未驗證假設（§0／brief assumed）

| # | 前提 | 判定 | 說明 |
|---|---|---|---|
| A | `template_check todo`／`todo_spec_crosscheck` PASS | **fact-verified** | 本輪 `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → `TEMPLATE PASS` rc=0 |
| B | U6：`非獨立 OOS 驗證` 0 命中；警語可過 `not.toContain` | **成立** | `grep -n -F '非獨立 OOS 驗證' TODO` → rc=1；L256 文案「…非獨立驗證」；`「獨立 OOS 驗證」 in 該句` → False |
| C | `_persist_outputs` 僅 `:1142`／`:3432`；`_ic_cache={` 於 `:3449` | **成立** | 本輪 grep：呼叫 1142、3432；定義 3789；cache 賦值 3449（persist 之後） |
| D | `_inject_root_oos` 於 stage7＋fallback wrapper 兩處足以覆蓋 root 重註 | **成立（邊際 IC）** | `_annotate_root_status_and_pass_class` 三點（1130／1542／3424）；xsec 1542 對 N/A 節不需 OOS 注入；TODO L202／L220 之 stage7＋`:1142` 重注入與 validator ⑰ 對齊 |
| E | xsec N/A＋reporter 條件透傳不破既有 10 處最小 `analysis_results` 測試；R3／`test_r6_wider` 可同時綠 | **成立（若照 TODO）** | reporter 現行對已列鍵 `.get(k,{})`；TODO L201 明示 `if "marginal_ic" in analysis_results` 缺鍵省略；R3 讀契約後掃 orch 裸 `{}` 字面；`test_r6_wider` 要求 orch 源含節名字串——與 xsec／stage7 組裝字面一致即可 |
| F | `fit_projection` spy＝模組屬性查找 | **成立（條件）** | `monkeypatch.setattr(marginal_ic,"fit_projection",…)` 要求 `compute_marginal_ic` **同模組**以名稱呼叫 `fit_projection(...)`；禁他模組 `from marginal_ic import fit_projection` 後再 spy 該 binding。TODO 已寫 setattr 目標；實作歧義可控，不另開 finding |
| G | A1-4 三檔已足、B5 不需再碰其他既有前端檔 | **不成立** | 見 **P0-01**（必改 `page.tsx`） |
| H | 各批 gate `mutation_probe_check` 路徑與 `test_mutation_*` 一一對應 | **部分成立** | §B＋各 Task 驗證欄之名齊；Phase 摘要 L110／L145／L178 漂移見 **P2-01** |

---

## R9 必核（逐條；引 TODO 行號）

### U1 §0⑥／Task 5.1＝A1-4 三檔；SPEC 母檔未就地改
**PASS（寫回）／新洞見 P0-01。** §0 L12⑥＝`types.ts`＋`icAnalysisStore.ts`＋`FeatureTierPanel.tsx`；Task 5.1 L258＝A1-4 三檔；A1-4 在延伸檔；SPEC 母檔 §C#6 仍只列 `types.ts`（未就地改）。**但**「接入 deep」必改 `page.tsx` → **P0-01**。

### U2 Task 4.1 無 `fit_scope`→`pass_class`；`_inject_root_oos`；oracle＝root；mutation 名
**PASS。** L201：刪推導句、`None` 佔位；L202：`_inject_root_oos`；L211：①／③／③′ 以 root 為 oracle；`test_mutation_fit_scope_derived_oos_breaks_root_oracle`。

### U3 Task 4.0 `case_id`＋`--check`；Task 4.3 `report_ref`
**PASS。** L187：`--write` schema 含 `case_id`、`--check` exact；L234：`survivor_output.case_id == pre["case_id"]` 且 `report_ref == f"ic_report_{pre['case_id']}.json"`。

### U4 Task 4.2 四 kwargs＋三 caller；`_ic_cache` 只在 persist 後；⑧＋mutation
**PASS。** L220：四顯式 kwargs；caller (a) stage7 (b) refilter→stage7 (c) fallback `:1142` 重注入；禁 persist 讀未建 cache；L226 ⑧＋`test_mutation_persist_reads_ic_cache_breaks_cold_call`。實核 persist 兩點＋cache 順序與碼證一致。

### U5 `persist_suppressed` 五鍵＋分欄；⓪ 四形狀
**PASS。** L220 完整五鍵 object；L226 ⓪ 四形狀 exact。

### U6 駁回碼證
**PASS（可重現）。** `grep -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` → 0 命中（rc=1）；L256 警語不含禁字串。

### U7 Task 1.2 ⑮＋4.3 bench spy；`test_mutation_counter_without_fit_call_breaks_spy`
**PASS。** L90 ⑮：正常 `2k+m`／超 survivors 0／只超 removed `2k`；L236 bench 600／0／400；L242 mutation 名在。

### U8 xsec N/A＋reporter 條件透傳＋⑯
**PASS。** L201：`analyze_cross_sectional` 旁加 `_xsec_na`；reporter `if key in`；L211 ⑯ exact＋spy 0。

### U9 各批 gate 路徑＋每檔 `test_mutation_*`
**部分 PASS。** §B L32–35 路徑齊；1.0／1.1／1.2／2.1／3.1／4.1／4.2／4.3 皆具名。Phase 摘要漂移 → **P2-01**（非 U9 主文未寫回）。

### U10 「四處」只剩版本行歷史敘述
**PASS。** `grep -n 四處 docs/GAP2_MARGINAL_IC_TODO.md` → 僅 L3「四處→兩插入點」歷史敘述；§0／Task 4.1 標題已是兩插入點。

### 可 Frozen？
**否。** BLOCKING＝`GROK-R9-P0-01`（page.tsx 白名單）。修 A1-5＋TODO 同步並清 P2-01 後可 Frozen。

---

## 必答 1–6

### 1. Agent 可執行性
- **卡住**：P0-01（§0／A1-4 vs Task 5.1「接入」）；P2-01（若跟 L110 無路徑命令）。
- B1–B4 其餘 Task：檔案／函式／偽碼／驗證命令足夠直接寫碼；掛載行號與 persist 兩點本輪實核可用。
- `fit_projection` spy：同模組名稱呼叫即可（見假設 F）。

### 2. 義務覆蓋
- D1–D7／D3′／D3″、§G、§V 24、§N 四殘留：追溯表 L271–298 有落點；registry G2-R1／R2／R3／R5 三值理由抽讀仍成立。
- **漂移**：SPEC／TODO「接入 deep」義務未落入白名單（P0-01）；母 SPEC §C#6 與 A1-4 差異屬延伸檔設計、可接受。

### 3. 批次獨立性／forward dependency
- 五批拓撲 OK；Task 4.0 為 B4 首件 OK；4.2 契約增值同 B4 commit、不阻 B1–B3。
- B5 依賴 4.1 `STAGE_OVERRIDE_PATHS` 已明示；**B5 另被 P0-01 白名單阻**。

### 4. 取巧面
- bench 已標觀測、OOM 只認計數上界——誠實。
- spy 防假 `n_regressions`——已補。
- 前端：只改 store／panel／types＋新表不掛 `page.tsx` ⇒ vitest 綠但頁面不可見（P0-01）。

### 5. 測試設計
- 各新 Python 測試 Task 之 `test_mutation_*` 指向可證偽失敗；B1 V 對映唯一。
- Task 4.0 為腳本、無 `test_mutation_*`——合理（`--check` 即 gate）。

### 6. 可 Frozen？BLOCKING 清單
- **不可 Frozen**。
- BLOCKING：`GROK-R9-P0-01`。
- 建議同輪清：`GROK-R9-P2-01`。

---

## §1 十一類（摘要；無則「無」）

1. 矛盾/互斥：P0-01（白名單 vs 接入）；P2-01（Phase vs §B gate）
2. 漏項：P0-01（page.tsx）
3. 不可測：無新 BLOCKING
4. 可疑 quant：無
5. 過度工程：無
6. OOM/並行：bench 邊界已標（無）
7. Cache：persist kwargs 寫回 OK（無）
8. API/型別：reporter 條件透傳 OK（條件式）
9. 測試品質：U7 spy／U2 root oracle OK
10. Agent 可執行性：P0-01
11. 必要性/短命工：無

## §2 錨點／獵空殼／§N
- TODO §0／§B／每 Task 驗證／邊界／不可做／存活至／覆蓋風險在；`template_check todo` PASS。
- 非空殼：U1–U10 寫回具實質偽碼；本輪缺陷＝B5 容器白名單漏列＋Phase gate 殘句。
- §N G2-R1／R2／R3／R5：`為何現在不做` 三值＋觸發仍成立；不收回為 Task。

---

ASSUMPTIONS_VERIFIED: U1–U10 逐條對 TODO R3；U6 grep＋子字串；persist/cache 行號；annotator 三點 vs inject 兩點；reporter `.get`／條件透傳寫法；wiring R3 硬編碼五節；`test_r6_wider` 字串存在斷言；page.tsx deep 掛載模式；A1-4 三檔邊界；template_check todo PASS；mutation_probe 無參 rc=1
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS rc=0；`grep -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` → 0 命中；`bash scripts/mutation_probe_check.sh` → rc=1 用法錯誤；`grep -n page.tsx docs/GAP2_MARGINAL_IC_{TODO,AMENDMENTS,SPEC}.md` → 0；`grep -n 四處 docs/GAP2_MARGINAL_IC_TODO.md` → 僅 L3
FAILURES_SEEN: none
SCOPE_CHANGES: none（只產 review；提案 A1-5 擴白名單含 page.tsx，未改碼）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
