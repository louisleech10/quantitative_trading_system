# SPLITUNIFY D-002 閉合輪 R12 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R12  
family: composer  
findings-round: R12  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第十二次修訂 v12）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: mutation 33 條、ID 01–33 連續 | **fact-verified** | `rg -c '^\| \`M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md` → **33** |
| brief fact-verified: register 29 條連續 | **fact-verified** | `rg '^\| \`C5-' docs/SPLITUNIFY_SPEC.D-002.md \| wc -l` → **29** |
| brief fact-verified: `tables.py` 4 處 `set_index` | **fact-verified** | `rg -n 'set_index' momentum/Analysis/event_samples/tables.py` → `:214/:229/:372/:373` |
| brief fact-verified: 三閘 rc=0 | **fact-verified** | `obligation_block_check` rc=0；`doc_format_precheck` rc=0 |
| brief fact-verified: M5 四案真值表 | **fact-verified** | `PYTHONPATH=. venv/bin/python handoffs/20260912-splitunify-b9-probe-m5-coords.py` → case1 PASS／case2 IndexError／case3 PASS／case4 CrossSymbolLeakageError |
| brief assumed: N1 掛 `EventSamplePipeline.run` 仍有驗收意義 | **assumption，部分成立** | 相對孤立 builder 單測，多驗了 `pipeline.run` 四參數閘＋`derive_event_split_from_plans` 接線；但 §V 仍要求 `metadata.split_unify` 同入口 ⇒ **不可實作**（→P1-01） |
| brief assumed: N3 producer／adapter 層做得到 | **assumption，否證** | `ic_split_adapter.py:305` 僅 IC 路徑；`EventSamplePipeline.run` 與 `test_splitunify_wiring.py` 皆未呼叫 validator ⇒ **投影路徑缺具名落點**（→P1-03） |
| brief assumed: N4 (v)(vi)(vii) 堵住繞過 | **assumption，SPEC 層成立、施工前碼未動** | `freeze_splitunify_golden.py:373-377` 仍 `write_text` 全檔覆寫（施工前預期）；**(vi) 外部錨字面尚未寫入 §V**（→P1-04） |
| brief assumed: register 29 涵蓋完全 | **assumption，全域掃描未見新 BLOCKING** | `rg 'n_train\|n_test\|n_purged\|insufficient_events' momentum/Analysis/event_samples api/routes api/services frontend/src/components/ic-analysis`；`api/` 無具名 split 計數欄；`tables.py:162` 為 `insufficient_events_in_test` 透傳，來源已在 C5-27 門檻鏈 |
| brief assumed: 「API 計數模型」駁回成立 | **fact-verified** | `rg 'n_purged\|split_unify\|discarded_rows' api/routes api/services api/models` → routes/services **零命中**；models 僅 `tier_min_test_events`／`n_test_groups`；`EventAnalyzeResponse.summary` 為 `Dict[str, Any]` |

## 必答 1–6

**1. 本家 R11 finding 是否閉合**

| ID | R11 斷言 | v12 落點 | 判定 | 確認方式 |
|----|----------|----------|------|----------|
| COMPOSER-R11-P1-01 | register 漏 pipeline／disclosure／前端／assignments | C5-26～C5-29、標題 29 條 | **CLOSED** | 對讀 `(5.6)` L121-124 與碼點 |
| COMPOSER-R11-P1-02 | M6 `--write` 可覆寫主檔 11 鍵 | (G-4d)① (v)(vi)(vii)＋§V 第 6 條＋`M-SU-D2-33` | **CLOSED（SPEC 層）** | 對讀 L169／§V L269；碼側仍未施工 |
| COMPOSER-R11-P2-01 | 整鏈 E2E 無可執行入口 | §V 改掛 `EventSamplePipeline.run`；metadata 併入 `SU-RESID-9A-UI` | **部分閉合→重開 P1-01** | `EventPipelineResult` 無 `metadata` 欄，§V 仍列 metadata 斷言且要求同入口 |

**2. 自證第七條「可實作性」（N1–N6）**

| 群 | v12 落點 | 可實作？ | 碼證 |
|----|----------|----------|------|
| N1 | §V 掛 `EventSamplePipeline.run`；metadata 併殘留 | **部分** | producer→summary 可經 `pipeline.run`；**metadata 層在同入口不可驗**（→P1-01） |
| N2 | register 29 | **是** | 四處補列與碼點對齊；C5-13 字面仍寫「兩處」（→P2-01） |
| N3 | validator 不在 derive、adapter 層呼叫 | **否（投影路徑）** | §V 仍寫 derive 須呼叫（→P1-02）；事件投影缺具名 adapter（→P1-03） |
| N4 | O_EXCL／外部錨／主檔 fail-closed | **SPEC 可、錨未落地** | (v)(vii) 可機械化；(vi) 缺 §V 字面錨（→P1-04） |
| N5 | `M-SU-D2-29` 改寫 | **是** | L307 對齊 `.v8.json`／主檔覆蓋 |
| N6 | `M-SU-D2-03` 值相等 | **是（IC 路徑）** | L283；與 N1 metadata 殘留並存時 Task 9.1 驗收仍分裂 |

**3. 攻 N1**

**立場**：把整鏈斷言掛在 `EventSamplePipeline.run` **優於**孤立 `build_event_keys` mock——會經過四參數閘、`derive_event_split_from_plans` 與 `plan.summary` 寫入。但 v12 **同一段 §V** 仍要求 `metadata.split_unify` 值相等且「必須跑在」同一入口，而 `EventPipelineResult`（`pipeline.py:52-63`）**只有** `summary`／`split_plan`、**沒有** `metadata`；同段又寫 metadata 併入 `SU-RESID-9A-UI` ⇒ **自相矛盾，不是誠實延後而是驗收句不可執行**。併入殘留對 metadata 層是誠實的；對 §V 未刪除 metadata 斷言則是逃避。

**4. 攻 N3／N4**

**N3 構造**：`test_splitunify_wiring.py` 以 `holdout_boundary` 造 plan 後直接 `pipeline.run(...)`（L78-80 一帶），**全程無** `validate_split_pair_integrity`；`ic_split_adapter.py:305` 之 validator 在 IC 切分路徑，**不會**被事件投影 wiring 呼叫。實作者在 Task 9.2b 照 §V L270 把 validator 塞進 `derive_event_split_from_plans` 則**牴觸** Task 9.2b L223「不在 derive 內呼叫」⇒ **兩條母斷言互斥**（→P1-02）。

**N4 構造（SPEC 已寫、碼未改）**：現行 `freeze_splitunify_golden.py:373-377` 仍 `golden_path.write_text(json.dumps({**actual}))`；換錨後 `--write` 可把 11 鍵整包換掉——v12 (vii) 若落地可擋。自參照繞過：同步改 `.v8.json`＋`.v8.sha256` 仍過 (iii)，需 (vi) 外部錨；但 §V **尚未嵌入**首次 sha256 字面（→P1-04），Task 9.5 施工者無比對目標。

**5. 攻 register 29 與 API 駁回**

**register**：全域掃描未發現超出 C5-01～29 之**新** split 計數消費面；`pattern_bridge.py:207` 之 `n_train`／`n_test` 為事件級 ID 計數、語意正確。**內部不一致**：C5-13 仍寫「tables 兩處 set_index」，與 (5.1)／C5-29 之四處敘述不同步（→P2-01）。

**API 駁回**：`rg` 掃 `api/routes/`、`api/services/`、`api/models/`——無 `n_purged`、無具名 `split_unify` 計數欄；`splitAuthority.ts` 消費的是 IC `metadata.split_unify.n_test`（disclosure 契約），**不是** `(5.5)` 所指的 pipeline summary 計數模型 ⇒ **駁回成立**。

**6. 修訂引入的新問題**

| 衝突 | 說明 |
|------|------|
| §V Task 9.1 vs §N `SU-RESID-9A-UI` | 同段要求 metadata 斷言又宣稱 metadata 殘留（P1-01） |
| Task 9.2b L223 vs §V L270 vs `M-SU-D2-30` | derive 內呼叫 vs 禁止 derive 內呼叫（P1-02） |
| N3 adapter vs 現有接線 | 投影路徑無 validator 呼叫點（P1-03） |
| §V (vi) vs Task 9.5 | 外部錨引用不存在的 §V 字面（P1-04） |
| D-001／golden | 無新衝突；v8 檔待 Task 9.5 |
| TODO §E | AST 觸發與 SPEC §N 已同步 |

## §1 必查摘要（11 類）

1. **矛盾**：§V Task 9.1 metadata 斷言 vs 殘留決策；§V derive validator vs Task 9.2b 禁止 derive — **有**（P1-01／P1-02）
2. **漏項**：N3 投影路徑缺具名 adapter — **有**（P1-03）
3. **不可測**：外部錨無 §V 字面 — **有**（P1-04）
4–11. 其餘 — **無新增 BLOCKING**（G-4e 殘餘已誠實標註）

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

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `rg -c '^\| \`M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md` | **33** |
| `rg '^\| \`C5-' docs/SPLITUNIFY_SPEC.D-002.md \| wc -l` | **29** |
| `PYTHONPATH=. venv/bin/python handoffs/20260912-splitunify-b9-probe-m5-coords.py` | 四案與 brief 一致 |
| `rg 'discarded' momentum/Analysis/ic_filter_orchestrator.py \| wc -l` | **0** |
| `rg 'n_purged\|split_unify\|discarded_rows' api/routes api/services api/models` | routes/services **0** |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R12-P1-01,COMPOSER-R12-P1-02,COMPOSER-R12-P1-03,COMPOSER-R12-P1-04
CLOSED: COMPOSER-R11-P1-01,COMPOSER-R11-P1-02

ASSUMPTIONS_VERIFIED: mutation 33／register 29；tables 4 處；M5 探針四案；api routes/services/models grep；R11 三條逐條對讀 v12  
TESTS_RUN: 見「複驗」表；交件將跑 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r12-composer.md --family composer`  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
