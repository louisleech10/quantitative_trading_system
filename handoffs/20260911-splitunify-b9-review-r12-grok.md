# SPLITUNIFY D-002 閉合輪 R12 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R12`  
family: grok  
findings-round: R12  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第十二次修訂／v12；sha12 `2780d73f7282`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r11/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r12/`（交件後清除；保留 `/tmp/claude-501*`）  
本家 R11 待閉（敘述用，不入裁決欄）: `GROK-R11-P1-01`～`04`、`GROK-R11-P2-05`

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: R11 十二條歸六群（五採納、一部分採納）→ 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r11/synth.md`

fact-verified: mutation 表列 **33**、ID 01–33 連續無重複 → `grep -oE 'M-SU-D2-[0-9]+' | sort -u | wc -l`＝33；`comm` 缺號／`uniq -d` 皆空

fact-verified: register 表列 **29**（`grep -cE '^\| \`C5-'`＝29）；C5-26..29 在場；標題／§RISK／§R 寫 29

fact-verified: `tables.py` 共 **4** 處 `set_index`（`:214`／`:229`／`:372`／`:373`）→ `grep -n set_index`

fact-verified: `api/models/` 之 `n_purged` **零命中**；`n_test` 只命中 `tier_min_test_events`／`n_test_groups`；`EventAnalyzeResponse.summary: Dict[str, Any]`（`event_import_models.py:308`）

fact-verified: 擴大掃 `api/routes/`＋`api/services/`——無事件批具名 split 計數欄（`n_purged` 生產模型零命中；服務層只讀 orchestrator 已寫之 metadata，不另立欄）

fact-verified: `pipeline.py:759` 為 summary 整包展開（`{k:v for k,v in plan.summary.items() if k!="per_symbol_n"}`）

fact-verified: `D-001-C2` (4.10) 逐字「投影端只消費 `row_index_local`；`derive_event_split_from_plans` 內部一律不得索引 `row_index`」→ 實讀 D-001 L80

fact-verified: `obligation_block_check` rc=0；`doc_format_precheck`（SPEC）rc=0

fact-verified: §V L270 仍含逐字 `ASSERT derive 路徑確實呼叫 validate_split_pair_integrity`；Task 9.2b L223 改法①逐字「**不在 derive 內呼叫**」；`M-SU-D2-30` 仍把「derive 路徑略過 validator」列為缺陷 → 三者互斥（見 P1-01）

fact-verified: SPEC 內 **64-hex sha256 字面數＝0**（`grep -cE '[a-f0-9]{64}'`＝0），而 §V 第 6 條外部錨 ASSERT 要求比對「本 SPEC §V 所錨之首次 sha256 字面」→ 見 P1-03

fact-verified: `holdout_boundary`（`split_preview.py`）**不**呼叫 `validate_split_pair_integrity`；`EventSamplePipeline.run` 只轉傳 plans、不建構 full `symbols`；IC 路徑之 `ic_split_adapter.py:305`／orchestrator **已**呼叫 → 事件投影路徑之「producer／adapter」落點未具名（見 P1-02）

assumed: N1 掛 `EventSamplePipeline.run` 在無生產接線下仍有意義  
→ **部分成立**：相對孤立 builder，該入口真實跑 `build_event_keys`→`plan.summary`（`pipeline.py:746-762`）；`metadata` 併入殘留是誠實。見必答 3（不另開 finding）。

assumed: N3「validator 由 producer／adapter 呼叫」在既有結構做得到  
→ **IC 路徑成立、事件路徑未具名**。見 P1-02。

assumed: N4 (v)(vi)(vii) 堵住 R11 兩條繞過  
→ **(v)(vii) 文面可堵雙檔同改／主檔覆寫**；**(vi) 外部錨目前空心**（字面未進 SPEC、Task 9.5 無寫入步驟）。見 P1-03。另：刪檔後 `O_EXCL` 重建在「已存在」語義下可過——`M-SU-D2-29` 已把刪除列為缺陷，屬已覆蓋殘餘，不另開。

assumed: register 29 這次涵蓋完全  
→ **否證局部**：C5-13 仍寫「tables **兩處**」，與 (5.3)／C5-29 之四處置描述分叉。見 P2-04。全域重掃未再找到與 (5.5) 同級、且會讓複合鍵後 `n_test` 膨脹之未列碼點（`splitAuthority.ts` 只顯示已算好的 `metadata.split_unify.n_test`，非 assignments 列數消費面）。

assumed: 「API 計數模型」駁回正確  
→ **成立**（models＋routes／services 皆無具名事件批 split 計數欄；`summary` 為 `Dict[str, Any]` 穿透）。

---

## 必答 1–6

### 1. 本家 R11 finding 是否閉合

| R11 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R11-P1-01` | **CLOSED** | `M-SU-D2-29` L307 已改為 `.v8.json`／旁檔／`--write` raise／主檔 11 鍵；不再寫「v8 **鍵**」 |
| `GROK-R11-P1-02` | **字面 CLOSED／剩餘洞重開 R12** | (G-4d)① 已補 (v)(vi)(vii)＋`M-SU-D2-33`；但 (vi) 之 SPEC 內 sha 字面仍缺 → `GROK-R12-P1-03` |
| `GROK-R11-P1-03` | **字面 CLOSED／剩餘洞重開 R12** | Task 改為 producer 呼叫＋四案真值表進 §V；但 §V／`M-30` 未同步、事件路徑落點未具名 → `GROK-R12-P1-01`／`P1-02` |
| `GROK-R11-P1-04` | **字面 CLOSED／剩餘洞重開 R12** | C5-26..29 已補、條數 29；C5-13「兩處」舊字面未改 → `GROK-R12-P2-04`；API 列駁回經 routes／services 複驗成立 |
| `GROK-R11-P2-05` | **CLOSED** | `M-SU-D2-03` L283 已含「鍵在而值不等於 summary／producer」 |

（跨輪 ID **不**填入本檔 `CLOSED:` 欄。）

### 2. 檢驗自證第七條「可實作性」（v12 六群）

| 群 | 可實作？ | 碼證／說明 |
|---|---|---|
| N1 | **可**（交付層）／殘留誠實 | `EventSamplePipeline.run` 存在且測得著；`metadata` 併入 `SU-RESID-9A-UI` 與 §N `api/` 呼叫點＝0 一致 |
| N2 | **大部分可** | C5-26..29 皆指向真實碼點；C5-13 字面過期（P2-04）不阻施工但會誤導「兩處」 |
| N3 | **IC 可／事件路徑不可按現文直接做** | `ic_split_adapter` 已有呼叫型；事件路徑無具名持有 full `ts`／`symbols` 之層（P1-02）；且 §V／mut 與 Task 互斥（P1-01）——不改則 Task 9.2b 實作時任選一邊必紅 |
| N4 | **(v)(vii) 可；(vi) 現不可驗** | `O_EXCL`／主檔 11 鍵比對皆可落在 `freeze_splitunify_golden.py`；外部錨字面未進 SPEC、Task 9.5 無寫入步（P1-03） |
| N5 | **可** | mut 29 字面對齊檔案制 |
| N6 | **可** | mut 03 字面對齊值相等 |

### 3. 攻 N1

- **與孤立單測之實質差異**：`EventSamplePipeline.run` 在給齊 canonical 邊界時呼叫 `derive_event_split_from_plans(…, build_event_keys(...))` 並把 `plan.summary` 整包／`n_*` 寫入 pipeline summary（`:746-762`）。孤立 builder 可手塞同值；此入口至少鎖定 **producer→summary** 真資料流。
- **metadata 併入殘留**：誠實，非逃避。碼證：`build_split_unify_disclosure` 簽名仍無 `discarded`；唯一 caller `ic_filter_orchestrator.py:1530` 不走 `build_event_keys`；`api/` 對投影 `run` 生產接線為 0（§N 已登記）。把不可達層標殘留，避免第四次「指名走不到的落點」。

### 4. 攻 N3／N4（具體構造）

**N3 — producer／adapter 是否存在：**

| 路徑 | 是否持有 full `ts`／`symbols`＋雙 plan | 現況 |
|---|---|---|
| `ic_split_adapter.py:305` | 是 | **已**呼叫 `validate_split_pair_integrity` |
| `ic_filter_orchestrator` holdout／xsec | 是 | **已**呼叫 |
| `holdout_boundary`（事件測資產生點） | 只回 row 計畫，無 validate | **無** |
| `EventSamplePipeline.run` | 有 plans＋`feature_index`，**不**建 `symbols` 陣列、不呼叫 validate | **無** |

構造：依 Task 改法「不在 derive 內呼叫」實作後，若 Agent 只改 `split_projection` 刪除未來呼叫、卻不在事件路徑補呼叫點 ⇒ 事件投影仍無 pair 完整性閘；同時 §V「derive 確實呼叫」與 `M-SU-D2-30` 會紅（或反過來：為過 §V 又在 derive 內呼叫 ⇒ 違反 D-001 (4.10) 與 Task 改法①）。

**N4 — (v)(vi)(vii) 後之繞過：**

1. **R11 雙檔同改**：被 (v) write-once＋(vi) 外部錨共同擋住（若外部錨真有字面）。  
2. **R11 整檔 `--write` 換主檔 11 鍵**：被 (vii) 文面擋住。  
3. **本輪新空心**：SPEC 內無任何 64-hex 字面 ⇒ (vi) ASSERT「與本 SPEC §V 所錨之首次 sha256 字面比對」**無可執行標的**；Task 9.5 正文只寫擴維／只增鍵，**未**要求把首次 digest 寫進 §V。⇒ P1-03。  
4. **刪後重建**：刪 `.v8.json` 後 `O_EXCL` 可成功建立新內容；此路徑已被 `M-SU-D2-29`「刪除…即缺陷」覆蓋，不另開 finding。  
5. **同 PR 改 SPEC 字面＋重建 v8**：屬人手／流程邊界（類似 G-4e），標註殘餘即可，非本輪新機械洞。

### 5. 攻 register 29 與 API 駁回

- **仍漏列（字面）**：`C5-13` 仍「tables **兩處**」——(5.3) 與 C5-29 已承認 4 處。⇒ P2-04。  
- **重掃未再列之碼點**：`splitAuthority.ts` 消費 `metadata.split_unify.n_test`（顯示層，非 assignments 列數計數）；上游修 C5-26／27 後此處不獨立膨脹。不升 finding。  
- **API 駁回**：成立。`api/models/` 無具名；`api/routes/`／`api/services/` 無事件批 `n_purged`／具名 `n_test` 欄（服務只讀已寫 metadata）。補「API 計數模型」列會再造走不到落點。

### 6. 修訂引入的新問題／衝突

1. Task N3「不在 derive 呼叫」↔ §V「derive 確實呼叫」↔ `M-SU-D2-30`「略過即缺陷」——**同檔互斥**（P1-01）。  
2. N3 改法未具名事件路徑呼叫點 ↔ D-001 (4.10) 禁止 derive 內索引／轉換（P1-02）。  
3. N4 (vi) 外部錨承諾 ↔ SPEC 零字面 ↔ Task 9.5 無寫入步（P1-03）。  
4. C5-13「兩處」↔ (5.3)／C5-29 四處（P2-04）。  
5. 與 TODO §E／既有 golden：N1 殘留與 §E `SU-RESID-9A-UI` 同向；golden 仍 11 鍵、無 v8 檔——符合「尚未凍結」現況，不另衝突。

不改就進 Task 9.x：①9.2b 實作者無法同時滿足 §V 與 Task／D-001；②事件路徑可能完全漏接 validator；③首次凍結後外部錨 ASSERT 仍無可比字面或需臨時改 SPEC 卻無步驟；④Agent 讀 C5-13 以為 tables 只有兩處。

---

## Findings

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

## §1 十一類（摘要）

1. 矛盾：§V／mut30 ↔ Task N3；C5-13「兩處」↔ 四處  
2. 漏項：事件路徑 validator 呼叫點未具名；外部錨字面／Task 步驟  
3. 不可測：外部錨 ASSERT 無字面可比  
4. quant：無新開（既有 tier_min 路徑已入 C5-27）  
5. 過度工程：無  
6. OOM：無  
7. Cache：無  
8. API／型別：駁回 API 計數模型——本輪複驗成立  
9. 測試：mut30／§V 與 Task 互斥會讓 9.2b 測試無法同時綠  
10. Agent 可執行：N3 抽象「producer／adapter」；N4 缺寫入字面步驟  
11. 短命工：無

## 主動攻擊面（對照停輪條件）

1. 本家 R11 → 01／05 閉；02／03／04 剩洞重開為 P1-03／P1-01+P1-02／P2-04  
2. 可實作性第七條 → N3／N4 未過（P1-01／02／03）  
3. 攻 N1 → 差異真實；殘留誠實；不開 finding  
4. 攻 N3／N4 → 上列具體構造  
5. 攻 register／API → P2-04；駁回成立  
6. 新衝突 → 互斥三元組為本輪主阻塞

## 被當成事實的未驗證假設（§0 彙總）

1. 「N3 事件路徑已可實作」——被 holdout／pipeline 無 validate、無 symbols 否證。  
2. 「N4 (vi) 外部錨已可驗」——被 SPEC 零字面否證。  
3. 「register 29 列字面自洽」——被 C5-13「兩處」否證。  
4. 「API 計數模型不存在」——models＋routes／services 複驗成立。  
5. 「N1 測試入口有意義」——producer→summary 成立；metadata 殘留誠實。

ASSUMPTIONS_VERIFIED: R11 六群對讀；mutation 33／C5 29 計數；tables 4 set_index；§V L270 vs Task L223 vs mut30；SPEC 64-hex＝0；holdout／pipeline／ic_split_adapter validate 呼叫面；api models+routes+services 計數欄；pipeline:759 整包展開；obl／fmt rc=0；D-001 (4.10)  
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r12-grok.md --family grok`（見下）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r12-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R12-P1-01,GROK-R12-P1-02,GROK-R12-P1-03
CLOSED:
STATUS: DONE
