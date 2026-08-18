# GAP-2 TODO adversarial — GROK R10（TODO DRAFT R4＋A1-1..6 複核；預期收斂輪）

family: grok｜task-id: 20260818-GAP2-X-REVIEW-R10｜brief: `handoffs/20260818-gap2-todoadv-r10-BRIEF.md`
標的：`docs/GAP2_MARGINAL_IC_TODO.md`（DRAFT R4）｜義務來源：`docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN）＋`docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..6）｜R9 收斂：`handoffs/reconcile/20260818-gap2-x-review-r9/synth.md`（V1–V3）｜R8 收斂：`…-r8/synth.md`（U1–U10）｜前輪：`handoffs/20260818-gap2-todoadv-r9-grok.md`

來源摘要前綴（本輪 `shasum -a 256`）：
- TODO：`docs/GAP2_MARGINAL_IC_TODO.md#52b446310ed8`
- AMEND：`docs/GAP2_MARGINAL_IC_AMENDMENTS.md#5316348d85ef`
- SPEC：`docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d`
- R9 synth：`handoffs/reconcile/20260818-gap2-x-review-r9/synth.md#80fe2d89d07b`
- R8 synth：`handoffs/reconcile/20260818-gap2-x-review-r8/synth.md#ea42b2aa7312`
- 本家族 R9：`handoffs/20260818-gap2-todoadv-r9-grok.md#c8c26dcd0e8d`
- page.tsx：`frontend/src/app/ic-analysis/page.tsx#77341721b6f0`
- registry：`docs/IC_QUANT_GAP_REGISTRY.md#a119d3b21771`

## Verdict：可 Frozen

R9 本家族兩條（P0-01／P2-01）與 V1–V3 接受項皆已落到 TODO R4／A1-5／A1-6；A1-5 **補正**（basic tab 末段 `CorrelationHeatmap` 後）獨立實核成立；U1–U10 抽核仍成立；`template_check todo`／`todo_spec_crosscheck` SMOKE 本輪 PASS。**無新 BLOCKING／MAJOR／MINOR finding**。可將 TODO 版本行改 **FROZEN** 進 B1。

BLOCKING：無。

---

## GROK-R10-P3-00

**斷言**: 本輪逐項核對後無 finding——V1–V3 寫回、A1-5 補正（basic 掛載）、A1-6 `write_failed` 字面、R8 U 抽核、§N 四殘留與各批 `mutation_probe_check` 路徑皆對齊且無可證偽缺陷。

**碼證**: （1）V1：TODO §0 L12⑥ 四檔含 `page.tsx`；Task 5.1 L257 插入點＝basic `:753`／`CorrelationHeatmap` `:810` 後＋props `section={report?.marginal_ic}`；L258 修改檔案＝A1-4＋A1-5 四檔；L262 驗證⑥要求 `grep -c MarginalICTable page.tsx`≥2 且 JSX 在 `TabsContent value="basic"`。A1-5＋補正見 AMEND L21–28。（2）V2：`grep -n mutation_probe_check.sh TODO` → L19／32–35／110／145／178／247；B1–B3 Phase 與 §B 同命令 byte-equal；無無參數殘留；裸跑 `bash scripts/mutation_probe_check.sh` → 用法提示 rc=1。（3）V3：TODO L220 `reason:"write_failed"` exact＋禁拼接；L226 ⓪ mock `os.replace`＋`reason ∈` 契約集合；AMEND A1-6 L25–27；`grep write_failed:`／`f"write_failed` → 0。（4）A1-5 補正獨立判：`page.tsx:214` `deepTabVisible`；`:750`／`:814` deep 受 gating；`:753`–`:812` basic 無該 gating；`marginal_ic` 為 base 節 → 掛 basic 正確，掛 deep 會在 deep 關時不可見。（5）U6：`grep -F '非獨立 OOS 驗證' TODO` rc=1；L256 警語「非獨立驗證」。（6）U2／U8 抽核：L201–202／L211 ①③′／⑯ root oracle＋xsec N/A。（7）registry G2-R1／R2／R3／R5 三值理由仍在。RECHECK：重跑上列 grep／template／crosscheck／page.tsx 行號。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#52b446310ed8；docs/GAP2_MARGINAL_IC_AMENDMENTS.md#5316348d85ef；frontend/src/app/ic-analysis/page.tsx#77341721b6f0

[NON-BLOCKING] 信心度=High。本輪為收斂複核；勿為湊數捏造實質 finding。AMEND A1-5 主文仍殘「deep／NetICChart」字樣、補正掛於 A1-6 段末——TODO 冷啟動已內嵌補正且為執行 SoT，不另開 finding（美觀債；主委可選擇就地改寫 A1-5 主文）。

---

## 被當成事實的未驗證假設（§0／brief assumed）

| # | 前提 | 判定 | 說明 |
|---|---|---|---|
| A | `template_check todo`／`todo_spec_crosscheck` PASS（DRAFT R4） | **fact-verified** | 本輪 `template_check.sh todo` → TEMPLATE PASS rc=0；`todo_spec_crosscheck` → CROSSCHECK SMOKE PASS rc=0 |
| B | A1-5 補正：掛 basic 末段（非 deep） | **成立** | 見碼證（4）；deepTabVisible 實核；無其他會藏 basic 表格之 gating（basic `TabsContent` 恆渲染） |
| C | A1-6 例外類別只進 log、不破五鍵 | **成立** | 前端／契約只消費 `write_failed` 字面；類別名屬運維可觀測性，log+`exc_info` 足夠；不提議另欄 |
| D | Phase「§B＋逐字複製」不再漂 | **成立（條件）** | B1–B3 與 §B byte-equal；B4 L247 為純 pointer（含三路徑提示）→ 實際以 §B L35 為準，可接受；雙寫漂移面已消 |
| E | 各批 `mutation_probe_check` 路徑 ↔ `test_mutation_*` 一一對應 | **成立** | B1：`test_survivor_contract`／`test_marginal_ic`；B2：`test_factor_combiner`；B3：`test_survivor_contract`；B4：三新檔；各 Task 驗證欄具名 mutation 齊 |
| F | `_persist_outputs` 兩點；annotator 三點 | **成立** | 與 brief／R9 一致；TODO L220 明示 |
| G | R9 V1–V3 已正確寫入 TODO R4／A1-5／A1-6 | **成立** | 見下方 R10 必核 |

---

## R10 必核（逐條；引 TODO 行號）

### V1 §0⑥ 四檔；Task 5.1 步驟 3＝basic＋CorrelationHeatmap；驗證⑥
**PASS（含 A1-5 補正獨立確認）。** L12⑥＝types／store／FeatureTierPanel／`page.tsx`；L257＝basic `:753`、`CorrelationHeatmap` `:810` 後、props `section`、資料源 base `report`；L262⑥＝頁面掛載斷言（禁只測元件）。**補正判定＝正確**：base 節掛 deep 會被 `deepTabVisible` 藏起，違反「IC 頁面可見」。

### V2 Phase B1–B4 Gate＝§B 同文（含帶路徑 probe）
**PASS。** L110／145／178 與 §B L32–34 同命令；L247 pointer→§B L35（含三新檔路徑）；`grep mutation_probe_check.sh\`` 無無參數殘留。

### V3 Task 4.2 `write_failed` exact（A1-6）＋驗證⓪
**PASS。** L220 reason 恆 `"write_failed"`；L226 ⓪ exact＋mock `os.replace`＋membership；無 `write_failed:<exc>`／f-string 殘句。

### R8 U1–U10 抽核（U6＋U2／U8）
**PASS。** U6 禁字串 0 命中；U2 root 注入／刪 fit_scope→oos 推導；U8 xsec N/A＋reporter 條件透傳。其餘 U1／U3–U5／U7／U9／U10 於 R4 正文仍可見（白名單四檔、case_id／report_ref、persist kwargs、五鍵、spy、gate 路徑、「四處」僅版本行歷史）。

### 可 Frozen？
**是。** BLOCKING 清單＝空。

---

## 必答 1–6

### 1. Agent 可執行性
- 逐 Task：檔案／函式／偽碼／不可做／驗證命令足夠直接寫碼；R9 卡住點（page.tsx 白名單、L110 無參 probe、`write_failed` 拼接）已關閉。
- 插入點「同一 `<div>`」略有版面歧義（heatmap 所在 2-col grid 內 vs TabsContent 末段新列）；屬前端樣式／不受理範圍，兩種皆「頁面可見」，不列 finding。
- 無須「自行判斷」才能過 gate 之義務缺口。

### 2. 義務覆蓋
- D1–D7／D3′／D3″、§G、§V 24、§C（A1-4＋A1-5 四檔）、§N 四殘留：追溯表 L271–298 有落點；語意與延伸檔一致。
- 漂移：無（母 SPEC「deep 區塊之後」已由 A1-5 補正重讀為 basic 末／deep 前，TODO 已落地）。

### 3. 批次獨立性／forward dependency
- 五批拓撲 OK；Task 4.0＝B4 首件；4.2 契約 `persist_suppressed` 增值同 B4 commit、不阻 B1–B3。
- B5 依賴 4.1 `STAGE_OVERRIDE_PATHS`＋白名單四檔已閉合。

### 4. 取巧面
- 已封閉：orphan table（現須 page 掛載＋驗證⑥）、動態 `write_failed:*`、無參 probe 假跟、fit_scope 推 OOS、bench 湊 `n_regressions`。
- 殘餘誠實邊界：bench 無 wall/RSS 閾值（已標觀測）——非取巧。

### 5. 測試設計
- 各新 Python 測試 Task 具名 `test_mutation_*` 指向可證偽失敗；B1 V-ID 對映唯一；Task 4.0 腳本以 `--check` 為 gate（合理）。

### 6. 可 Frozen？BLOCKING 清單
- **可 Frozen**。
- BLOCKING：無。

---

## §1 十一類（摘要；無則「無」）

1. 矛盾/互斥：無（A1-5 主文深／補正 basic 之殘句以 TODO＋補正為準，不另開）
2. 漏項：無
3. 不可測：無
4. 可疑 quant：無
5. 過度工程：無
6. OOM/並行：無（計數上界已標）
7. Cache：無（persist kwargs／時序 OK）
8. API/型別：無
9. 測試品質：無
10. Agent 可執行性：無
11. 必要性/短命工：無

## §2 錨點／獵空殼／§N
- TODO §0／§B／每 Task 驗證／邊界／不可做／存活至／覆蓋風險在；`template_check todo` PASS。
- 非空殼：V1–V3 寫回具實質偽碼與驗證字面。
- §N G2-R1／R2／R3／R5：registry 三值＋觸發仍成立；不收回為 Task。

---

ASSUMPTIONS_VERIFIED: V1–V3 對 TODO R4／A1-5／A1-6；A1-5 補正 vs deepTabVisible 實核；V2 Phase↔§B byte-equal（B1–B3）；V3 write_failed exact＋無拼接殘句；U6 grep rc=1；U2／U8 抽核；mutation 路徑↔test_mutation 名；template_check＋todo_spec_crosscheck PASS；registry G2 四殘留三值
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → TEMPLATE PASS rc=0；`bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` → CROSSCHECK SMOKE PASS rc=0；`bash scripts/mutation_probe_check.sh` → 用法 rc=1；`grep -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` → 0 命中 rc=1；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-todoadv-r10-grok.md --family grok` →（本檔寫後自跑）
FAILURES_SEEN: none
SCOPE_CHANGES: none（只產本 review 檔；禁改 SPEC／TODO／碼）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-todoadv-r10-grok.md`
TMP_CLEANUP: 無自建 `/tmp/workdir`；保留 `/tmp/claude-501`；未刪他 session 目錄
STATUS: DONE
