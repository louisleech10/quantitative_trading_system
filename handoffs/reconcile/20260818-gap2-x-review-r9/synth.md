# Reconcile — 20260818-gap2-x-review-r9

**來源** 20260818-gap2-todoadv-r9-codex.md, 20260818-gap2-todoadv-r9-composer.md, 20260818-gap2-todoadv-r9-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18）

三家共 **7 條**（codex 3／composer 2／grok 2），下列三個群集**引用全部 7 條，0 掉項**。三家皆確認 R8 U1–U10 寫回成立、U6 駁回碼證可重現（codex 重跑同一 grep rc=1 無命中）；三家皆判「需修補」（新 finding 皆為 scope／字面閉合，非設計爭議）；**7 條全部接受**寫回 TODO DRAFT R4；SPEC 義務側兩處走延伸檔 A1-5（`page.tsx` 白名單）／A1-6（`write_failed` reason 字面封閉）。

Verdict：需修補後派工——TODO DRAFT R4＋A1-5／A1-6 寫回；本 synth 戳記後派 R10 複核；三家「可 Frozen」即 TODO FROZEN → B1。

### V1 — B5 表格接入 IC 結果頁 deep 區塊必改既有容器 `frontend/src/app/ic-analysis/page.tsx`，§C／A1-4／§0⑥ 未列（R8 U1 同構）
**引用**: CODEX-R9-P1-02, COMPOSER-R9-P1-01, GROK-R9-P0-01
**處置＝接受**：實核 `page.tsx:815` `TabsContent value="deep"`、`:904-914` 末段 `NetICChart` 具名 import 掛載、`grep MarginalICTable frontend/src` 0 命中。走延伸檔 **A1-5**：§C#6 再擴一檔 `frontend/src/app/ic-analysis/page.tsx`（**只**加 import＋於 deep `TabsContent` 末段 `NetICChart` 之後掛 `<ChartErrorBoundary title="邊際 IC／多因子組合"><MarginalICTable section={report?.marginal_ic} /></ChartErrorBoundary>`；資料源＝base `report`，非 `deepAnalysisReport`；不改其他區塊）；TODO §0⑥、Task 5.1 步驟 3／修改檔案清單與 A1-5 逐字一致；驗證加「`page.tsx` 含 `MarginalICTable` import 且 deep tab 渲染（vitest 或 grep 斷言）」；禁把「接入」降級為只測 vitest。

### V2 — Phase B1 測試段 L110 仍寫無參數 `mutation_probe_check.sh`；Phase B2／B3 摘要漏該檢查
**引用**: CODEX-R9-P1-01, COMPOSER-R9-P2-01, GROK-R9-P2-01
**處置＝接受**：Phase B1／B2／B3／B4 各「測試＋Gate」小節改為 pointer「見 §B 對應列（單一來源）」＋逐字複製該列命令（含帶路徑之 `mutation_probe_check.sh`），消除 §B 與 Phase 小節雙寫漂移。

### V3 — `survivor_output.reason=f"write_failed:{type(exc).__name__}"` 違反契約 reason SoT 封閉集合（`write_failed` 唯一字面）
**引用**: CODEX-R9-P1-03
**處置＝接受**：母 SPEC Task 4.2 L214 亦寫 `write_failed:<exc class>` ⇒ SPEC 義務側，走延伸檔 **A1-6**：`reason` 恆為契約字面 `write_failed`（exact；由 `load_survivor_contract()["reasons"]["survivor_output"]` 取值），例外類別與訊息**只**進 `get_logger` 之 error log（`exc_info=True`），五鍵不增欄；validator reason-membership 對 `write_failed` 形狀 exact 通過；Task 4.2 偽碼與驗證⓪同步。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R9-P1-01
**斷言**: B1 Phase Gate 仍含無參數 `bash scripts/mutation_probe_check.sh`，按正式用法必然失敗。 **碼證**: `nl -ba docs/GAP2_MARGINAL_IC_TODO.md:109-110`；`bash scripts/mutation_probe_check.sh` 輸出 `用法: ... <test_path>...`、rc=1；同檔 B1→B2 已明列兩個 test path。 **來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358; scripts/mutation_probe_check.sh#03309f359005。 [MAJOR] 信心度=High；B1 收尾先被硬 gate 擋住。修法：Phase B1 Gate 也明列 `tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py`，並重跑該 gate。
## CODEX-R9-P1-02
**斷言**: B5「IC 頁面可見」無法在現行 scope 完成：`MarginalICTable` 沒有被現有 IC 結果頁匯入或渲染。 **碼證**: TODO:251-262 要求新增 table 並接入 deep 區塊；`frontend/src/app/ic-analysis/page.tsx:814-916` 的 deep JSX 無該元件；`rg -n 'MarginalICTable' frontend/src` 無命中；TODO:258 的既有檔清單只有 `types.ts`／store／panel 加新元件，未列 page 容器。 **來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358; frontend/src/app/ic-analysis/page.tsx#77341721b6f0。 [MAJOR][SPEC 義務側] 信心度=High；新檔會成孤兒，頁面義務不成立。修法：A1-4／Task 5.1 明列 `frontend/src/app/ic-analysis/page.tsx`、精確插入點與資料來源（base `report?.marginal_ic`），並納入相應 gate。
## CODEX-R9-P1-03
**斷言**: `write_failed:<ExceptionClass>` 與 survivor contract 的 reason SoT `write_failed` 不一致，且違反「orchestrator 一律由契約取 reason」的同段要求。 **碼證**: TODO:44-47 將 `survivor_output` reasons 唯一列為 `identity_missing, write_failed`；TODO:206 要求由 `load_survivor_contract()["reasons"]` 取值；TODO:220 卻要求 `f"write_failed:{type(exc).__name__}"`。 **來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358; docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d。 [MAJOR] 信心度=High；嚴格 validator／reason-membership 檢查會拒絕寫檔失敗形狀，放寬則 SoT 不再封閉。修法：二選一並寫入契約／測試：固定輸出 `write_failed` 並將例外類別只寫 log，或正式定義可驗證的結構化錯誤欄／pattern；不可由實作端自行猜。
§1 必查：1 矛盾／互斥＝有（P1-01～03）；2 端到端漏項＝有（B5 page 接線）；3 不可測＝有（B1 gate、write_failed enum）；4 quant 假設＝無新的方向漂移（root OOS、fit spy、預算 gate 已寫回）；5 過度工程＝無；6 OOM／並行＝既有計數 spy／原子寫要求已覆蓋；7 cache＝顯式 persist kwargs／cache 時序已對齊；8 API／型別＝B5 page scope 未閉合；9 測試＝P1-01，U6 grep 已關閉；10 Agent 可執行性＝P1-01～03；11 短命工＝無。
必答1 Agent 可執行性：B1 gate、B5 page 接線、write_failed reason 決策會卡；其餘 Task 的檔案／函式／驗證大致足夠。
必答2 義務覆蓋：D1–D7／D3′／D3″、§G、§V、§N 多數有落點；B5「可見」義務缺 page scope，survivor write-failure reason 有語意漂移。
必答3 批次獨立性：4.0→4.1 順序、U2/U3/U4/U5/U7/U8/U10 已對齊；B2/B3/B4 新測試檔路徑明列；B1 Phase Gate 殘留無 path，B5 依賴缺 page。
必答4 取巧面：若接受 dynamic `write_failed:*` 可繞過 reason SoT；table orphan 可讓 build／component test 綠但產品頁永遠不顯示；budget spy／root oracle 取巧面已補。
必答5 測試設計：U6 同一 grep 無命中（rc=1）；`fit_projection` spy 的 module-level patch 在實作缺席下未能 runtime 驗證；xsec exact、root oracle、persist cold-call、case_id/report_ref、四形狀與各 `test_mutation_*` 名已明列；B1 command 仍錯。
必答6 可以 Frozen？不可以。BLOCKING／MAJOR 清單：`CODEX-R9-P1-01`、`CODEX-R9-P1-02`（SPEC 義務側）、`CODEX-R9-P1-03`；修補後需重跑 template/crosscheck、相關 gates 與三家 review/stamp。
ASSUMPTIONS_VERIFIED: R8 三家 stamp APPROVED；U6 grep 無命中且 rc=1；root annotate 呼叫點／stage7 呼叫點已由 rg 核對；現行 IC deep page 無 MarginalICTable；B1 mutation checker 無參數 rc=1；fit spy 尚未因實作不存在而 runtime 驗證。
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` PASS rc=0；`bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` PASS rc=0；`bash scripts/ic_wiring_check.sh` PASS rc=0；`grep -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` no match rc=1；`bash scripts/mutation_probe_check.sh` usage rc=1；指定 `bash scripts/completeness_check.sh --single handoffs/20260818-gap2-todoadv-r9-codex.md --family codex` 被 PreToolUse gate 擋在腳本前，未取得 checker rc；其餘為 `nl`／`rg`／`shasum` read-only probes。
FAILURES_SEEN: `bash scripts/mutation_probe_check.sh` 無參數 rc=1（TODO 殘留）；U6 指定 grep rc=1 是預期「無命中」證據，非 review 失敗；completeness 命令因本輪 OPEN debt 被 gate 擋下，非格式驗證結果。
SCOPE_CHANGES: 只新增本交件檔；未修改 SPEC／TODO／程式／測試／data_cache；提出 page whitelist 與 reason schema 修補建議，未自行越界修改。
NUMERIC_OR_SCHEMA_IMPACT: 未改產品數值／輸出；finding 指出 B5 page scope 與 survivor `write_failed` reason schema 需裁決。
HANDOFF_OUTPUT: `handoffs/20260818-gap2-todoadv-r9-codex.md`; family=codex; task-id=`20260818-GAP2-X-REVIEW-R9`。
STATUS: BLOCKED — completeness_check 被本輪 OPEN debt 的 PreToolUse gate 擋下；需治理 owner 銷帳後以同一參數重跑。
## COMPOSER-R9-P1-01

**斷言**: Task 5.1 要求「接入 IC 結果頁 deep 區塊」（必改 `frontend/src/app/ic-analysis/page.tsx` import＋渲染 `<MarginalICTable>`），但 §0／A1-4 白名單未含該檔，執行端無法同時完成 B5 表格落地與「白名單外一律不碰」。

**碼證**: VERIFY `grep -n '接入 IC 結果頁 deep' docs/GAP2_MARGINAL_IC_TODO.md` → L257；Task 5.1 L258「修改檔案」僅列 A1-4 三檔＋新 `MarginalICTable.tsx`；§0 L12「唯此七處」無 `page.tsx`。`grep -n MarginalICTable frontend/src/app/ic-analysis/page.tsx` → 0 命中（現況未接入）。SPEC Task 5.1 L236 同義務「接入現有 IC 結果頁 deep 區塊之後」。RECHECK: 比對 §0⑥／A1-4 與 Task 5.1 步驟 3／修改檔案清單是否含 `frontend/src/app/ic-analysis/page.tsx`（或等價容器）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；frontend/src/app/ic-analysis/page.tsx#77341721b6f0

[MAJOR] 信心度=High；**SPEC 義務側**（母 SPEC L236 ＋ TODO L257 義務已寫，scope 未同步）。失敗：agent 守 §0 則表格永不顯示；越權改 `page.tsx` 則違反派工白名單。修法：延伸檔 A1-5（或 A1-4 增列）把 `frontend/src/app/ic-analysis/page.tsx` 納入 §C#6 既有檔（僅 import＋`<MarginalICTable report={report?.marginal_ic} …/>` 插入 deep `TabsContent`）；同步 TODO §0⑥ 與 Task 5.1 修改檔案清單。

---

## COMPOSER-R9-P2-01

**斷言**: Phase B1 測試段 L110 仍寫「`bash scripts/mutation_probe_check.sh` 對新檔綠」未帶路徑，與 §B L32／§0 L19（無參數 rc=1）及 U9 寫回不一致，執行端若跟 L110 會 gate 硬失敗。

**碼證**: VERIFY `grep -n 'mutation_probe_check.sh' docs/GAP2_MARGINAL_IC_TODO.md` → L110 無 test path；§B L32 已為 `… test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py`。RECHECK: `bash scripts/mutation_probe_check.sh` → rc=1（用法提示）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358

[MINOR] 信心度=High。不阻 B1 若跟 §B 表；阻 agent 只讀 Phase 小節。修法：L110 與 §B L32 逐字對齊。

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


## 戳記

（待三家 append RECONCILE-STAMP）
RECONCILE-STAMP: grok APPROVED 2026-08-18 sha256:33ba593b80ed1591700e7f9d4d06b5f7a2e407ac38b322c552a9ac5356a7e756 task:20260818-GAP2-X-STAMP-R10
RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:33ba593b80ed1591700e7f9d4d06b5f7a2e407ac38b322c552a9ac5356a7e756 task:20260818-GAP2-X-STAMP-R10
RECONCILE-STAMP: codex APPROVED 2026-08-18 sha256:33ba593b80ed1591700e7f9d4d06b5f7a2e407ac38b322c552a9ac5356a7e756 task:20260818-GAP2-X-STAMP-R10
