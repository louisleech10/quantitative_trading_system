# Reconcile — 20260911-splitunify-b9-review-r12

**來源** 20260911-splitunify-b9-review-r12-codex.md, 20260911-splitunify-b9-review-r12-composer.md, 20260911-splitunify-b9-review-r12-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **O1 §V 仍留 metadata 斷言，與「併入殘留」同段自相矛盾（兩家撞題）**——「`metadata.split_unif」「v12的N1修法在§V`Task9.1`」 | P1 | CODEX-R12-P1-01, COMPOSER-R12-P1-01 | 採納（主委複驗成立：`EventPipelineResult` 只有 `summary`／`split_plan`、**無** `metadata` 欄 ⇒ 我在同一段既要求值相等斷言「必須跑在 `EventSamplePipeline.run`」、又宣告 `metadata.split_unify` 併入 `SU-RESID-9A-UI` 殘留，實作者照 §V 會去 assert 一個該入口產不出的物件。**併入殘留本身是誠實的**（grok 明判非逃避），錯在我**沒把 §V 的 metadata 兩條 ASSERT 一併移走** ⇒ 自證②同型第九次。改法：§V `Task 9.1` 只保留 producer→`EventSplitPlan.summary` 掛 `EventSamplePipeline.run`，metadata 兩條移入 §N 殘留驗收，`M-SU-D2-03` 標明其應紅面屬 IC disclosure 專路） |
| **O2 (G-4d)(vi) 外部錨零字面，母斷言空心（三家撞題）**——「v12的(G-4d)(vi)外部錨要求無」「v12N4之§V(vi)要求與「**本S」「N4(vi)要求外部錨為「首次凍結之sh」 | P1 | CODEX-R12-P1-02, COMPOSER-R12-P1-04, GROK-R12-P1-03 | 採納（主委複驗成立：`grep -cE '[0-9a-f]{64}'` 全 SPEC＝**0**，而我寫的 ASSERT 要「與本 SPEC §V 所錨之首次 sha256 字面比對」，且 `Task 9.5` 全文**沒有**把 digest 寫回 SPEC 的步驟 ⇒ 我寫下一條指向不存在字面的斷言，屬「寫了要做卻沒做」同型。改法：`Task 9.5` 增「首次建立 `splitunify_golden.v8.json` 之同一次變更**必須**把其 `sha256` 64-hex 字面寫入 §V 具名錨點」；錨點寫入前，(vi) 標為「凍結當下生效」；新增 mutation 覆蓋「字面缺失即紅」） |
| **O3 derive 是否呼叫 validator，Task／§V／mutation 三處互斥（兩家撞題）**——「v12的N3正文已寫「`validate」「v12把Task9.2b步驟0改成「`v」 | P1 | COMPOSER-R12-P1-02, GROK-R12-P1-01 | 採納（主委逐行複驗成立：`Task 9.2b` 改法①逐字「**不在 derive 內呼叫**」，而 §V 前置仍逐字 `ASSERT derive 路徑確實呼叫 validate_split_pair_integrity`、`M-SU-D2-30` 仍以「derive 路徑略過」為缺陷 ⇒ 實作者任選一邊都會紅。又是**改了 Task 正文沒回寫 §V 與 mutation**，自證②⑤同型。改法：§V 前置改為「進入 `derive_event_split_from_plans` **之前**，由持有 full `ts`／`symbols` 之具名層已呼叫 validator」；`M-SU-D2-30` 改壞面改為「具名 producer 層略過 validator，或 train 段為空仍 `continue`」；保留「derive 全函式不出現對 `row_index` 之索引」那條） |
| **O4 事件投影路徑之 validator 呼叫點未具名（兩家撞題）**——「v12N3要求「仍持有full`ts`／」「N3要求validator「由仍持有fu」 | P1 | COMPOSER-R12-P1-03, GROK-R12-P1-02 | 採納（本輪**本輪特有必答「可實作性」之直接反例**，也是自證第七條首次被外部驗出漏網：我寫「由 producer／adapter 層呼叫」但**沒具名是哪一個**——三家實查：`ic_split_adapter.py:305` 與 `ic_filter_orchestrator` 走 IC 路徑**已**呼叫，而事件路徑之 `holdout_boundary` 零命中、`EventSamplePipeline.run` 只轉傳 plans 且**不建構** `symbols` 陣列 ⇒ 事件投影上該層根本不存在。改法：`Task 9.2b` 與 §V **具名**寫死事件路徑呼叫點——`EventSamplePipeline.run` 在呼叫 `derive_event_split_from_plans` **之前**，以 `feature_index` 之時刻作 `ts`、`train_plan.symbol` 廣播作 `symbols` 呼叫 validator；並禁 pipeline 接受未驗證之 plans） |
| **O5 §C:155 仍寫 register「25 條」**——「D-002§C:155仍把唯一regis」 | P2 | CODEX-R12-P2-01 | 採納（主委複驗成立，且**我的自證④查法自己有洞**：我跑的殘留掃描用 `grep -v "v11\|v12\|沿革"` 過濾，而該行正好含「v11」字樣 ⇒ 被自己的過濾條件濾掉。改法：條數字面改為 29；🔴 **並依 HANDOFF 已定之「同一個數字不得寫在兩個地方」，把此處改為指向 register、不再重複寫數字**） |
| **O6 register 之 `C5-13` 仍寫「tables 兩處」（兩家撞題）**——「v12已在(5.1)／(5.3)更正`t」「v12已在(5.3)／C5-29更正`t」 | P2 | COMPOSER-R12-P2-01, GROK-R12-P2-04 | 採納（主委複驗成立：我改了 (5.1)／(5.3) 與新增 `C5-29`，**就是沒改 register 列本身** ⇒ 自證②同型第十次。改法：`C5-13` 改為明列 `:214`／`:229`／`:373` 三處甲類，並交叉引用 `C5-29`（`:372` 丙類）） |
| **O7 `Task 9.1`「實際須改三處」與 metadata 殘留決策不一致**——「若依§V/§1.9交付metadatae」 | P2 | CODEX-R12-P2-02 | 採納（與 O1 同源：既然 metadata 層併入殘留，`Task 9.1` 之「實際須改三處」該整段隨之降級，不得留在當輪交付面。🔴 **主委另補一處三家都沒提**：該「三處」本身也漏了 `contracts/split_unify.json` 之 `split_unify_keys` 陣列（`tests/api/test_splitunify_disclosure.py:272` 以 `set(su) == set(CONTRACT["split_unify_keys"])` 對證，不改即紅），實為四處——此點隨整段移入殘留驗收一併記明） |

**停輪判斷（🔴 依 2026-09-12 已定之判準，本輪觸發）**：十二輪 findings 數 15／11／15／8／11／16／15／14／21／13／12／13。**R12 十三條無一為新面向**——全部在打 v12 剛寫的 N1–N4 段落；且三家一致確認四項**已閉**：register 涵蓋性（全域重掃未再找到新消費面）、「API 計數模型」駁回（含 `api/routes/`／`api/services/` 複驗）、(G-4e) 殘餘誠實標註足夠、metadata 併入殘留為誠實而非逃避。剩餘七群**全是字面同步與具名落點問題，無一需要重新設計**。⇒ 第十三次修訂完成後**直接進 `Task 9.1` 實作**，不再派規格審查輪；殘餘規格缺陷交給實作期 pytest 暴露（O1／O3／O4 這類「Task 與 §V 互斥」「落點不存在」在實作當下會立即變紅，比再讀一輪規格有效）。

Verdict：需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R12-P1-01
**斷言**：`metadata.split_unify` 等值斷言不能在 brief 指定的 `EventSamplePipeline.run` 入口執行；該入口只產生 `EventPipelineResult.summary`，而 metadata 產生點在另一條沒有 `discarded`/`build_event_keys` 的 IC 路徑。
**碼證**：`pipeline.py:693-768`（`run` 回傳 summary、沒有 metadata）；`rg -n 'build_split_unify_disclosure|split_unify' momentum/Analysis api` 只命中 `ic_filter_orchestrator.py:1530` builder；其呼叫僅傳 `n_test/test_timestamps/per_symbol_counts`；API AST 掃描輸出 `AST_RUN_CALLS=2`，僅 `uvicorn.run`、`asyncio.run`。**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282；momentum/Analysis/event_samples/pipeline.py#55ca7327764f；momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293；MAJOR 信心度=高；修法是把當輪驗收明確縮成 producer→summary，metadata 等值移至生產接線後的殘留驗收，或補一條真正承接 EventSplitPlan 的生產 handoff。
## CODEX-R12-P1-02
**斷言**：v12 的 (G-4d)(vi) 外部錨要求無法執行，因 SPEC §V 目前沒有首次 SHA-256 字面或精確 anchor 欄位，實作者無法完成「與 SPEC 所錨首次值比對」的母斷言。
**碼證**：`rg -n '[0-9a-f]{64}' docs/SPLITUNIFY_SPEC.D-002.md` 輸出空；`find tests/golden/splitunify -maxdepth 1 -name '*v8*'` 輸出空；`jq` 顯示現行主檔 11 鍵；但 `D-002:269` 要求與 SPEC §V 首次字面比對，`Task 9.5:252-255` 檔案清單也未納入 SPEC。**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282；scripts/freeze_splitunify_golden.py#e331623163d2；tests/golden/splitunify/splitunify_golden.json#f270e007ca98；MAJOR 信心度=高；修法是先定義不可改寫的 anchor 欄位/值、納入施工與驗收範圍，再讓 main 只讀該值；否則 M-SU-D2-33 的外部錨分支仍不可驗。
## CODEX-R12-P2-01
**斷言**：D-002 §C:155 仍把唯一 register 說成 25 條，與同文件標題、RISK、§R 及實際 29-row register 矛盾。
**碼證**：`awk`/`rg` 機械核對輸出 `C5_REGISTER count=29 expected=29 duplicates=none missing=none`；`D-002:155` 仍輸出「register 之 25 條消費面」，而 `:70,:90,:317` 均為 29。**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282；MINOR 信心度=高；修法是把 §C:155 的 25 改為 29 並移除舊 v11 註記，避免施工者依敘述漏改四個消費面。
## CODEX-R12-P2-02
**斷言**：若依 §V/§1.9 交付 metadata exact-key 擴充，Task 9.1 所稱「實際須改三處」不完整；若 metadata 確實殘留，則 §188/§259 的當輪 metadata 交付斷言又未被同步降級。
**碼證**：`D-002:190` 明稱實際三處；`momentum/Analysis/contracts/split_unify.json:49-55` 仍是五鍵；`tests/api/test_splitunify_disclosure.py:149-151,270-277` 對五鍵做 exact set；`D-002:259` 又要求 metadata 值等於 producer。**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282；momentum/Analysis/contracts/split_unify.json#5aaf5f8efa15；tests/api/test_splitunify_disclosure.py#f1bd211204f7；MINOR 信心度=高；修法是二選一寫死：補列 contract JSON 與 exact-key 測試為施工面，或把 metadata assertion/contract 變更完整移入 SU-RESID-9A-UI 殘留。
ASSUMPTIONS_VERIFIED: N1/N3/N4/API/register 假設均以指定路徑實讀、AST/rg/awk/jq 命令核對；D-001/golden/TODO §E 交叉檢核完成。
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；兩份 `doc_format_precheck.sh` rc=0；D-002 `spec_xref_check --synth` PASS；register=29、mutation=33 均無重複/缺號；API AST `AST_RUN_CALLS=2`。
FAILURES_SEEN: 首次 `spec_xref_check` 少傳 target 僅印用法，未改檔；補正後 D-002 xref PASS；TODO target 的 xref FAIL 反映 §E 延後同步之既有狀態，已按 §N 判為非本輪新衝突；指定 completeness command 未啟動即被 PreToolUse 擋下（本輪 debt OPEN，無 rc），未以旁路執行。
SCOPE_CHANGES: 僅新增本交接檔，未改碼/SPEC/TODO；NUMERIC_OR_SCHEMA_IMPACT: 未改動，提出 P1/P2 規格修正建議；OUTPUT: `handoffs/20260911-splitunify-b9-review-r12-codex.md`
VERDICT: blocked
BLOCKED-BY: CODEX-R12-P1-01 CODEX-R12-P1-02
CLOSED: CODEX-R11-P1-02 CODEX-R11-P1-03
STATUS: DONE
## COMPOSER-R12-P1-01

**斷言**: v12 的 N1 修法在 §V `Task 9.1` **同一段**仍要求 `metadata.split_unify[...]` 值相等斷言「必須跑在 `EventSamplePipeline.run`」， yet 同段又將 `metadata.split_unify` 併入 `SU-RESID-9A-UI` 殘留——`EventPipelineResult` 無 `metadata` 欄，該入口** structurally 產不出**被斷言的物件。

**碼證**: §V L259 逐字含 `ASSERT metadata.split_unify["discarded_rows_by_feature_tf"] == ...` 與「上述值相等斷言**必須**跑在 `EventSamplePipeline.run`」；同段末句「`metadata.split_unify` 層**明確併入** `SU-RESID-9A-UI` 殘留」。`sed -n '52,63p' momentum/Analysis/event_samples/pipeline.py` → `EventPipelineResult` 僅 `summary`／`split_plan` 等，**無** `metadata`。RECHECK: 對讀 §V L259 vs `EventPipelineResult` dataclass；`rg 'build_split_unify_disclosure' momentum/Analysis/event_samples/pipeline.py` → **0**。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282;momentum/Analysis/event_samples/pipeline.py#55ca7327764f

[BLOCKING] 信心度=High。Task 9.1 實作者照 §V 寫測試會在 `pipeline.run` 上 assert 不存在的 `metadata.split_unify`，或改回孤立 builder mock 假綠。**修法**：§V `Task 9.1` 刪除（或移入 §N／`M-SU-D2-03` IC 專路）metadata 兩條 ASSERT，保留 producer→`EventSplitPlan.summary` 於 `EventSamplePipeline.run`；`M-SU-D2-03` 應紅測試改指向 IC disclosure 路徑或標註 blocked-by 殘留。

## COMPOSER-R12-P1-02

**斷言**: v12 的 N3 正文已寫「`validate_split_pair_integrity` **不在 derive 內呼叫**」，但 §V `Task 9.2b` 前置仍保留 `ASSERT derive 路徑確實呼叫 validate_split_pair_integrity`，且 `M-SU-D2-30` 仍以「derive 路徑略過 validator」為改壞面——三處**互斥**，第七條自證未同步完成。

**碼證**: Task 9.2b L223 改法①「**不在 derive 內呼叫**」；§V L270 逐字「`ASSERT derive 路徑確實呼叫 validate_split_pair_integrity`」；L308 `M-SU-D2-30`「derive 路徑略過 …」。`rg 'validate_split_pair_integrity' momentum/Analysis/event_samples/split_projection.py` → **0**（施工前預期）。RECHECK: 對讀 L223 vs §V L270 vs mutation L308。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282

[BLOCKING] 信心度=High。實作者依 §V 會在 derive 加 validator（違 D-001-C2），或依 Task 9.2b 不加而讓 `M-SU-D2-30`／§V 前置永久紅。**修法**：§V 前置改為「producer／adapter 層（具名 `pipeline.run` 投影分支或 `ic_split_adapter`）呼叫 validator；derive **不得**呼叫」；重寫 `M-SU-D2-30` 改壞面為「投影入口略過 adapter 層 validator」。

## COMPOSER-R12-P1-03

**斷言**: v12 N3 要求「仍持有 full `ts`／`symbols` 的 producer／adapter 層」呼叫 validator，但**事件投影**現有接線（`EventSamplePipeline.run`＋`test_splitunify_wiring.py`）無任何具名呼叫點——只有 IC 專用 `ic_split_adapter.py:305`，與 Task 9.2b 施工路徑**不連通**。

**碼證**: Task 9.2b L223 改法①「producer／adapter 層呼叫」；`nl -ba momentum/Analysis/ic_split_adapter.py | sed -n '305,311p'` → validator 在 IC adapter；`rg 'validate_split_pair_integrity' momentum/Analysis/event_samples/pipeline.py tests/momentum/event_samples/test_splitunify_wiring.py` → **0**。RECHECK: 全 repo `rg 'validate_split_pair_integrity' momentum/Analysis/event_samples` → 僅可能命中 split_projection 以外之模組。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282;momentum/Analysis/ic_split_adapter.py#b05b0f73e417;momentum/Analysis/event_samples/pipeline.py#55ca7327764f

[BLOCKING] 信心度=High。Task 9.2b 落地時無合法落點：在 derive 加違 D-001；不加則 §V 四案真值表與 pair 完整性無從驗。**修法**：Task 9.2b 具名「`EventSamplePipeline.run` 投影分支在 `derive_event_split_from_plans` 之前，以 `feature_index` 作 `ts`、`train_plan.symbol` 作 `symbols` 呼叫 validator」或等價具名函式；§V adapter 斷言改指向該呼叫點。

## COMPOSER-R12-P1-04

**斷言**: v12 N4 之 §V (vi) 要求與「**本 SPEC §V 所錨之首次 sha256 字面**」比對，但 §V／§G 全文**未嵌入**任何 v8 檔 sha256 字面，且 `splitunify_golden.v8.json` 尚不存在——(vi) 在 Task 9.5 動工當下**不可實作**。

**碼證**: §V L269 (vi) 逐字「與本 SPEC §V 所錨之首次 sha256 字面比對即 FAIL」；`rg '[0-9a-f]{64}' docs/SPLITUNIFY_SPEC.D-002.md` 在 §V 第 6 條區段 → **無 v8 錨**；`test -f tests/golden/splitunify/splitunify_golden.v8.json` → **MISSING**。RECHECK: 首次 freeze 後是否回寫 SPEC——Task 9.5 正文**未要求** amend §V 嵌入錨。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。施工者實作 (vi) 無比對目標；或自行發明錨值違反 data truth。**修法**：Task 9.5 增「首次建立 `.v8.json` 後 MUST 將 sha256 字面寫入 §V 固定錨點（具名行號）」；或 (vi) 改指向已提交 lock／receipt 路徑並附 recheck。

## COMPOSER-R12-P2-01

**斷言**: v12 已在 (5.1)／(5.3) 更正 `tables.py` 為 **4 處** `set_index` 並新增 `C5-29`（`:372` assignments），但 register 列 `C5-13` 仍寫「tables **兩處** set_index」——自稱唯一施工清單與分類敘述再次分叉。

**碼證**: `C5-13` L108 vs `C5-29` L124 vs (5.3) L78「共 **4 處**」。`rg -n 'set_index' momentum/Analysis/event_samples/tables.py` → 4 行。RECHECK: 對讀 register C5-13 字面 vs (5.1) 甲類列舉。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282;momentum/Analysis/event_samples/tables.py#843ba7f68172

[MAJOR] 信心度=High。實作者掃 register 可能漏 `:372` 丙類處置（雖有 C5-29，C5-13 舊字面會誤導）。**修法**：`C5-13` 改為「`:214/:229/:373` 三處甲類 `.loc[eid]`；`:372` 見 `C5-29`」；刪「兩處」字面。

## GROK-R12-P1-01

**斷言**: v12 把 Task 9.2b 步驟 0 改成「`validate_split_pair_integrity` **不在 derive 內呼叫**」，但 §V 仍寫 `ASSERT derive 路徑確實呼叫 validate_split_pair_integrity`，且 `M-SU-D2-30` 仍把「derive 路徑略過 validator」列為缺陷——三處互斥，屬自證②未同步。

**碼證**: `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '223p;270p;308p'` → L223 改法①逐字「不在 derive 內呼叫」；L270 逐字「derive 路徑確實呼叫」；L308 `M-SU-D2-30` 逐字「derive 路徑略過 `validate_split_pair_integrity`…即缺陷」。RECHECK: 同上三行對讀；實作任選一邊跑對應 §V／mutation。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282

[BLOCKING] 信心度=High。不改則 Task 9.2b 實作者：①在 derive 內呼叫 → 違反 Task／D-001 (4.10) 精神與「投影端不做轉換」；②不在 derive 呼叫 → §V 與 mut 30 紅。**修法**：①§V 改為 `ASSERT plans 進入 derive_event_split_from_plans 之前，持有 full ts／symbols 之具名層已呼叫 validate_split_pair_integrity`；刪「derive 路徑確實呼叫」；②`M-SU-D2-30` 改壞面改為「事件／IC 之具名 producer 層略過 validate，或空 train 仍 `continue`」；③保留「derive 全函式不出現對 row_index 之索引」那條。**可行性**：純 SPEC／mutation 字面同步；母斷言與 mut 指向同一呼叫契約即可。

## GROK-R12-P1-02

**斷言**: N3 要求 validator「由仍持有 full `ts`／`symbols` 的 producer／adapter 層呼叫」，但事件投影路徑上該層**未具名**——`holdout_boundary` 與 `EventSamplePipeline.run` 皆不呼叫、亦不建構 full `symbols`；Agent 無法按現文落到可編譯的檔:函式。

**碼證**: `grep -n validate_split momentum/core/split_preview.py` → 零命中；`sed -n '693,760p' momentum/Analysis/event_samples/pipeline.py` → `run` 只轉傳 `train_plan`／`test_plan`／`feature_index` 進 `derive_event_split_from_plans`，無 `symbols`、無 validate；對照 `momentum/Analysis/ic_split_adapter.py:305` 與 `ic_filter_orchestrator.py:684,976` **已**呼叫。事件測資 `_canonical`（`test_splitunify_wiring.py`）用 `holdout_boundary` 組 SplitPlan 後直接 `pipeline.run`，中間無 validate。RECHECK: 重跑上列 grep／sed；確認 Task 9.2b 正文無 `ic_split_adapter`／`EventSamplePipeline.run`／具體插入點。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;momentum/core/split_preview.py#（validate 零命中）;momentum/Analysis/ic_split_adapter.py（既有呼叫）

[BLOCKING] 信心度=High。本輪特有必答「可實作性」之反例：文字與 D-001 對齊了，但事件路徑仍無可執行落點。不改則實作者可能只改 IC 已綠路徑、或在 derive 內違約補呼叫。**修法**：在 Task 9.2b／§V **具名**事件路徑呼叫點（建議二擇一寫死並附可行性）：(a) `EventSamplePipeline.run` 在呼叫 derive **之前**，以 `feature_index` 時刻＋plan.symbol（單標）或 caller 傳入之 full `ts`／`symbols`（多標）呼叫 validate；或 (b) 規定唯一允許的 plan 工廠（擴 `holdout_boundary`／新 adapter）必須在回傳前呼叫，並禁 pipeline 接受未驗證 plans。**可行性證據**：IC 路徑已證明「持有 ts／symbols 的層呼叫」可做；單標事件測資之 `feature_index`＋`[SYM]*n` 與 orchestrator holdout 同型。

## GROK-R12-P1-03

**斷言**: N4 (vi) 要求外部錨為「首次凍結之 sha256 **字面寫進本 SPEC §V**」，且 §V 第 6 條 ASSERT 要比對該字面——但 SPEC 內 64-hex 字面數為 **0**，Task 9.5 亦無「寫入 §V」步驟 ⇒ 外部錨母斷言目前空心。

**碼證**: `grep -cE '[a-f0-9]{64}' docs/SPLITUNIFY_SPEC.D-002.md` → **0**；L169 (vi)／L269 ASSERT 逐字「與本 SPEC §V 所錨之首次 sha256 字面比對」；`sed -n '252,258p'` Task 9.5 只寫 golden 擴維／只增鍵／前端，**無** digest→SPEC 步驟；`ls tests/golden/splitunify/splitunify_golden.v8*` → 尚無 v8 檔（預期未凍，但字面與 Task 步驟仍缺）。RECHECK: 重跑 hex 計數；對讀 Task 9.5 vs (G-4d)①(vi)。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282

[BLOCKING] 信心度=High。(v)  alone 只擋「已存在後再更新」；缺外部字面時，刪檔重建或首次寫入錯誤內容仍無第二錨可證偽。**修法**：①Task 9.5／freeze 流程明寫「首次建立 `.v8.json` 之同一次變更必須把 `sha256` 64-hex 字面寫入 §V 第 6 條具名位置（例：`V8_BASELINE_SHA256=`）」；②在字面寫入前，§V 得把外部錨 ASSERT 標為「凍結當下才生效」並配 mutation 覆蓋「字面缺失即紅」；③禁止只靠旁檔。**可行性**：與 golden byte 閘同型——字面進已提交文件、freeze helper 不改該字面。

## GROK-R12-P2-04

**斷言**: v12 已在 (5.3)／C5-29 更正 `tables.py` 為 **4** 處 `set_index`，但 register 之 `C5-13` 列仍寫「tables **兩處**」——唯一施工清單列本身保留被取代的舊字面。

**碼證**: `sed -n '108p;124p;78p' docs/SPLITUNIFY_SPEC.D-002.md` → C5-13「兩處」；C5-29／(5.3)「共 4 處」；`grep -n set_index momentum/Analysis/event_samples/tables.py` → 214／229／372／373。RECHECK: 同上。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282;momentum/Analysis/event_samples/tables.py#843ba7f68172

[MAJOR] 信心度=High。不阻 C5-29 施工，但 Agent 若只讀 C5-13 會以為只需顧兩處甲類。**修法**：C5-13 改為明列 `:214`／`:229`／`:373`（甲類），並交叉引用 C5-29（`:372` 丙類）。**可行性**：一字級表修。

---

