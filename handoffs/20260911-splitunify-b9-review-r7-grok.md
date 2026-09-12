# SPLITUNIFY D-002 閉合輪 R7 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R7`  
family: grok  
findings-round: R7  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第七次修訂；full sha12 `f266e6e999bd`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r6/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r7/`（交件後清除；保留 `/tmp/claude-501*`）  
本家待閉: `GROK-R6-P1-01`、`GROK-R6-P1-02`、`GROK-R6-P1-03`、`GROK-R6-P1-04`、`GROK-R6-P1-05`

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: R6 十六條歸八群、全部採納 → 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r6/synth.md`；本家五條皆在 I1／I2／I3／I5／I7 採納列

fact-verified: 第七次修訂已寫入三段式判側、跨表互斥、`feature_materialization` 維持事件級、(5.1) 三分類、Task 9.1 採 (b)、Map 排除、tier_min 去重、mutation 26 → 本輪逐字讀 SPEC；`obligation_block_check`／`doc_format_precheck` 皆 rc=0；mutation 表列 26、ID 01–26 連續

fact-verified: 隔離帶＝`[split_point, split_point+purge_gap+embargo)` 且與 train／test 合起來覆蓋 `[0,n)` → 探針 `probe_all.out`：`COVER True`

fact-verified: golden fixture 含具名 `gap1`／`gap2`（pos 140／141），現行集合成員＝`PURGED_else`；`freeze_splitunify_golden.py` 之 `PURGE=2, EMBARGO=2` → 探針 `GOLDEN gap1/gap2 … PURGED_else`

fact-verified: `build_event_keys` 非測試生產呼叫點僅 `pipeline.py:747`；`api/` 內 **零** `EventSamplePipeline.run` 呼叫；`ic_filter_orchestrator` 只呼叫 `holdout_boundary`、**無** `build_event_keys` → `grep`

fact-verified: Task 9.3 L187–188 仍要求 `pattern_bridge`／`tables`／`ic_feed`／`counterexample`／`candidate_ledger` 改複合鍵 lookup、`dedupe` 改 `(event_id, feature_timeframe)`；同時 (5.1) 把上述多數列為 **(甲) 維持**、`pattern_bridge` 列為 **(丙) 去重取唯一** → 對讀 L74↔L187–188

assumed: `D-002-C5` (5.1) 之三分類逐處判對  
→ **(甲) 本輪抽樣碼證大致成立**（`feature_materialization` 橫向合併、`dedupe` 事件級、`tables`／`ic_feed` 事件級或單 TF 過濾後唯一）；**否證的是施工單**：Task 9.3 正文＋mutation 04–11 **未跟著改寫**，會讓實作者照 Task 9.3 破壞 (5.1)。見必答 2／P1-01。

assumed: `Task 9.2b` 三段式覆蓋所有位置情形  
→ **對已映射到 `[0,n)` 的位置：完備**（train∪gap∪test＝`[0,n)`）。**未完備處**：`decision_at_ms ∉ index_ms` 時「映射之位置」未定義——`searchsorted` 會讓步驟 3 形同死碼，並把早於 `index[0]` 的時刻誤收成 train。見必答 3。

assumed: 答案窗 purge 改事件側不改變單 TF 現行行為  
→ **答案窗本身（如 golden `tr_leak`）可保持 purge**；但 **隔離帶由 `PURGED_else` 改 raise** 會改變單 TF 成員集，且與 §G「單 TF 逐值不變」及 golden `gap1`／`gap2` 衝突。見必答 3／P1-02。

assumed: Task 9.1 採 (b) 後 IC 主線確實有 `discarded` 可揭露  
→ **否證**：`discarded` 產自 `build_event_keys`，IC 主線只有 `holdout_boundary`；兩者不是同一條資料流。見必答 4／P1-03。

---

## 必答 1–5

### 1. 本家 R6 finding 是否閉合

| R6 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R6-P1-01` | **CLOSED**（派工字面） | Task 9.2b L174–177 三段式：先隔離帶 fail-closed raise → 不等式定側 → 覆蓋區外 fail-closed；區間定義指向 `holdout_test_row_index:41-43` |
| `GROK-R6-P1-02` | **CLOSED**（派工字面） | L180 跨表 `set(purged) ∩ set(assignments) == ∅`；L181 答案窗按事件側廣播 |
| `GROK-R6-P1-03` | **CLOSED**（改寫方向） | Task 9.3 L186 整段改為維持事件級橫向合併＋記帳 `nunique` 理由；不再要求 MultiIndex |
| `GROK-R6-P1-04` | **CLOSED** | Task 9.4 L196–197 指名 `:562`／`:569`／`:716-719`／`per_symbol_n` 改 `event_id` 去重，並要求終端揭露 |
| `GROK-R6-P1-05` | **CLOSED**（決策字面） | Task 9.1 L144 定案採 (b)、舊四落點作廢。**殘留改開 R7-P1-03**：替代落點仍未具名且 IC≠`build_event_keys` |

### 2. 挑戰 (5.1) 三分類（特別是甲）

**(甲) 抽樣結論＝分類本身大致對，施工單自相矛盾才是缺陷。**

| 處 | (5.1) | Task 9.3 正文 | 碼證（一列代表什麼） |
|---|---|---|---|
| `feature_materialization` | 甲維持 | 甲維持（已改寫） | `:93-131` 橫向 `update`；`:22-32` 同名欄 loud 拒 |
| `dedupe.cluster_first` | 甲維持 | **仍要求改複合鍵**（L188） | `:124-129` 按 `dedupe_cluster_id` 留一事件 |
| `tables` `.loc[eid]` | 甲維持 | **仍要求改複合鍵**（L187） | `:214/:229` 對 `event_level`／`clusters` |
| `ic_feed` 單 TF 過濾後 | 甲維持 | **仍要求改複合鍵**（L187） | `:109` 先濾 `timeframe==` 再 `set_index` |
| `counterexample`／`candidate_ledger` | 甲維持 | **仍要求改複合鍵**（L187） | 事件級匯入／集合迴圈（HANDOFF 主委碼證＋本輪對讀） |
| `pattern_bridge` | **丙**去重取唯一 | **仍要求改複合鍵 lookup**（L187） | `:125-127` `set_index("event_id")["split_label"]`；複合鍵後 `.loc` 變 Series |
| 前端 Map | 甲維持（Task 9.5） | 已排除 | `eventExport` 無 `feature_timeframe` |

**未找到「甲類判錯、複合鍵上線後會靜默取錯列」的反例**——真正會靜默取錯的是 `pattern_bridge`，已正確在 **(丙)**。  
**會失敗的是**：實作者若只讀 Task 9.3／mutation 04–11，會把甲／丙處改成複合鍵，破壞去重、物化矩陣與匯出。→ **P1-01**

### 3. 三段式完備性與單 TF／golden

- **位置完備（已映射）**：`train ∪ gap ∪ test = [0,n)`（`purge=0` 時 gap 空、train／test 緊接）。無第四種落點。
- **映射未定義（`decision_at ∉ index_ms`）**：SPEC 只寫「映射之位置」。若用 `searchsorted`，早於 `index[0]` 會落到 pos 0＝train，步驟 3 永不觸發；若要求精確落在 `index_ms`，粗網格多 TF 會大量 raise（R5 實證）。→ 併入 P1-02 之修法要求。
- **單 TF 行為／golden**：現行 gap cutoff → `PURGED_else`（同 `_PURGE_REASON`）；三段式 → **raise**。golden 具名 `gap1`／`gap2` 現在是 purged 成員（`g1_membership.purged` 含 3＝`tr_leak`+`gap1`+`gap2`）。§G 要求「單 TF 路徑逐值不變（exact）」⇒ 照 Task 9.2b 實作會讓 golden 路徑 raise 或必須改 fixture／放寬 §G。答案窗改事件側對 `tr_leak` 可保持 purge，**不是**單 TF 漂移主因；**隔離帶 raise 才是**。→ **P1-02**

### 4. Task 9.1 採 (b) 之後 `discarded` 怎麼傳到畫面

**現況資料流（碼證）：**

| 節點 | 有無 `discarded`／`build_event_keys` |
|---|---|
| `build_event_keys`（唯一產出點） | 有（待實作回傳） |
| `pipeline.py:747`（唯一非測呼叫） | 會接到 |
| `api/` 任何 route／service | **無** `EventSamplePipeline.run` |
| `case_import_service` | 恆 `run_event_study_only`（已作廢路徑） |
| `ic_filter_orchestrator` | 只有 `holdout_boundary` → `SplitPlan`；**無** event keys／discarded |

SPEC L144 把「IC 主線」定義成 `holdout_boundary` 呼叫點，但 `discarded` 不在那條鏈上。L144 仍寫「實作須指名：IC 投影路徑之回應欄位、前端顯示位置」——**決策有了、落點仍丟給實作者**。§V Task 9.1 仍寫「summary／API／前端三層」而未替換為新具名 endpoint。→ **P1-03**

### 5. 修訂引入的新問題／衝突

1. **(5.1) vs Task 9.3／mutation**（P1-01）：分類改了、施工單與 M-SU-D2-04～11 未改；`M-SU-D2-04` 仍把「不改 groupby 折疊」當缺陷，與「維持橫向合併」互斥；`M-SU-D2-11` 把「Map 鍵退回 event_id」當缺陷，與 Task 9.5 排除遷移互斥。  
2. **三段式 gap raise vs §G exact／golden gap 事件**（P1-02）。  
3. **Task 9.1(b) 範疇錯置**（P1-03）：`holdout_boundary` ≠ `build_event_keys`。  
4. I1–I8 與 D-001／C6：clusters 事件級、C6 量詞、tier_min 去重本輪字面一致；**無**新的 C6 互斥。  
5. `(5.3)`／`(5.4)` 仍用「靜默折疊／須改」敘事描述已改判為甲的處——與 (5.1) 文件漂移（併入 P1-01，不另開）。

---

## Findings

## GROK-R7-P1-01

**斷言**: 第七次修訂的 `D-002-C5` (5.1) 已把 `dedupe`／`tables`／`ic_feed`／`counterexample_classifier`／`candidate_ledger` 列為 **(甲) 維持事件級**、`pattern_bridge` 列為 **(丙) 去重取唯一**，但 `Task 9.3` L187–188 與 mutation `M-SU-D2-04`～`11` 仍要求（或假設）這些處改複合鍵／改 groupby——施工單與分類互斥，實作者照 Task 9.3 會破壞甲／丙定案。

**碼證**: SPEC L74 (5.1) 甲含 `dedupe`／`tables`／`ic_feed`／`counterexample`／`candidate_ledger`，丙含 `pattern_bridge`；L187 逐字「改為複合鍵 lookup」；L188 逐字「`cluster_first` 保留集改 `(event_id, feature_timeframe)`」；L223 `M-SU-D2-04`「不改 groupby 折疊」＝缺陷；L230 `M-SU-D2-11`「Map 鍵退回 event_id」＝缺陷，但 L203 Task 9.5 已排除 Map 遷移。碼：`dedupe.py:124-129`、`tables.py:214,229`、`ic_feed.py:109`、`pattern_bridge.py:125-127`、`feature_materialization.py:93-140`。RECHECK: 對讀 L74↔L186-188↔mutation 表 04–11。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e;momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2;momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2

[BLOCKING] 信心度=High。不改則 Task 9.3 實作時：(a) 把事件級表改複合鍵 → `.loc`／去重／簇權重語意壞；(b) 或照 (5.1) 維持不動 → mutation 04–11 無法紅／假綠；(c) `M-SU-D2-04`／`11` 與新定案方向相反。**修法**：Task 9.3 逐條改寫為與 (5.1) 同文——甲處寫「維持、加回歸防誤改」；丙處寫「去重取唯一側、不唯一 raise」；mutation 04 改為「誤把物化改成每 TF 一列／MultiIndex」才紅；05 對齊丙；06–10 改為反向 mutation（誤改複合鍵才紅）或刪除；11 刪除或改為「誤改複合鍵致匯出 miss」。**可行性**：分類表已寫好，只是施工單／mutation 未同步；無需新架構。

## GROK-R7-P1-02

**斷言**: `Task 9.2b` 把隔離帶從現行 `PURGED_else` 改成 fail-closed raise，會改變單 TF 切分成員集，並與 §G「單 TF 路徑逐值不變（exact）」及 golden 具名 `gap1`／`gap2`（現行在 `purged`）直接衝突；且 `decision_at_ms ∉ index_ms` 時「映射之位置」未定義。

**碼證**: VERIFY: `PYTHONPATH=. venv/bin/python` 探針 → golden `gap1 pos 140 PURGED_else`、`gap2 pos 141 PURGED_else`；`freeze_splitunify_golden.py` `OOS, PURGE, EMBARGO = 0.3, 2, 2`；`g1_membership.purged` 長度 3。SPEC L175 隔離帶 raise；§G L127「單 TF 路徑逐值不變（exact）」。另：`n=20,purge=2,embargo=1` 時 `COVER True`（無第四落點），但 `decision=1h` 對 4h `index` 時 `exact_member False`、`searchsorted_pos=1`。RECHECK: 重跑 golden keys 分類＋對讀 L175↔L127。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;scripts/freeze_splitunify_golden.py#e331623163d2;momentum/core/split_preview.py#95a85ec0de54;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。照字面實作 Task 9.2b：(a) 現有 golden／wiring 在 gap 事件上由「入 purged」變「raise」⇒ 單 TF exact 失敗；(b) 粗網格下映射未定義 ⇒ 實作者可走出 searchsorted 誤收 train、或精確成員大量 raise 兩歧路。**修法**（須寫死其一並改 §G／fixture）：建議 **隔離帶維持事件級 purge（reason 沿用或分名），不得收成 train**——滿足 R6「不等於 train」且保留單 TF purged 集合；§V 成對 ASSERT「gap ⇒ purged 且非 train、非 raise」；另用時間域定義 gap（`train_last_ms < decision_at_ms < test_start_ms`）避免依賴 `∈ index_ms`。若堅持 raise，則 §G 必須明文豁免 gap 行為變更，並重凍／移除 `gap1`／`gap2` 錨。**可行性**：現行 else 分支已是 purge；改「不等式＋gap 時間窗 ⇒ purge」比改 golden 全鏈成本低，且不把隔離帶收成 train。

## GROK-R7-P1-03

**斷言**: Task 9.1 雖已定案採 (b)，但把終端揭露掛在「IC 主線＝`holdout_boundary` 呼叫點」是範疇錯置——`discarded` 只可能出自 `build_event_keys`（經 `EventSamplePipeline.run`），而 `api/` 目前零 `run()` 呼叫、`ic_filter_orchestrator` 不含 `build_event_keys`；替代 route／回應欄／前端仍寫「實作須指名」，§V 仍用已作廢的「三層」句式 ⇒ 9A 仍無可執行驗收命令。

**碼證**: L144「IC 主線（`ic_filter_orchestrator` 為 `holdout_boundary` 之生產呼叫點）」＋「實作須指名…」；`ic_filter_orchestrator.py:604` 僅 `holdout_boundary(...)`；`pipeline.py:747` 為非測唯一 `build_event_keys` 呼叫；`grep` 於 `api/`：`EventSamplePipeline().run`／`create_event_sample_pipeline().run` 命中 0；`case_import_service.py:1592-1609` 仍 event-study-only。§V L207 仍 `ASSERT summary／API 回應／前端型別三層皆帶該欄`。RECHECK: `grep -rn 'build_event_keys\|EventSamplePipeline().run' api momentum --include='*.py'`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293;momentum/Analysis/event_samples/pipeline.py#55ca7327764f;api/services/case_import_service.py#d2571793953f

[BLOCKING] 信心度=High。Agent 無法寫出單一「打哪條 HTTP、期望哪個 JSON 鍵」的契約測試；若硬掛 IC report metadata，那裡根本沒有 `discarded` 來源。**修法**：在 Task 9.1 **具名一條確實呼叫 `EventSamplePipeline.run`（或等價投影）的生產／準生產路徑**——若尚無，則 (b) 必須含「新增／恢復」該路徑的 route＋service＋前端面板檔案:行；§V 改寫為可複製命令（含 fixture 與鍵名 `discarded_rows_by_feature_tf`）；刪除「實作須指名」與對已作廢三層的獨立回退句，改指新三層。**可行性**：測試面 `test_splitunify_wiring.py` 已是 `run()`＋投影的可跑範本；把同級路徑升成 API 揭露面即可，不必碰 `holdout_boundary`。

---

## §1 十一類（摘要）

1. 矛盾：(5.1) vs Task 9.3／mutation（P1-01）；gap raise vs §G exact（P1-02）  
2. 漏項：9.1(b) 無具名可達落點（P1-03）  
3. 不可測：§V 9.1 仍無單一可執行命令（P1-03）  
4. quant：隔離帶成員集變更（P1-02）  
5. 過度工程：無  
6. OOM：無  
7. Cache：無  
8. API／型別：9.1 揭露鏈未閉  
9. 測試：mutation 04–11 與定案反向  
10. Agent 可執行：Task 9.3／9.1 指示自相矛盾或未指名  
11. 短命工：無

## 主動攻擊面（停輪③）

1. 本家 R6 五條 → 派工字面 **CLOSED**（9.1 殘留開新 ID）  
2. 挑戰 (5.1) 甲 → 分類大致對、Task 9.3／mutation 未同步 → **P1-01**  
3. 三段式＋golden gap 探針 → **P1-02**  
4. IC vs `build_event_keys` 呼叫圖 → **P1-03**  
5. I1–I8 交叉：I3／I4／I5／I6 落點互撞於施工單

不改就進 Task 9.x：①9.3 依正文改壞甲／丙或 mutation 假綠；②9.2b 讓 golden gap 事件 raise／單 TF exact 破；③9A 無任何可打的揭露 endpoint。

## 被當成事實的未驗證假設（§0 彙總）

1. 「(5.1) 分類寫完 ⇒ 施工單已對齊」——被 L187–188／mutation 否證。  
2. 「三段式 ≡ 不改單 TF 成員集」——被 golden gap1／gap2 否證。  
3. 「IC＝`holdout_boundary` ⇒ 有 discarded」——被呼叫圖否證。  
4. 「答案窗改事件側是單 TF 主風險」——答案窗可保持；主風險是隔離帶 raise。

ASSUMPTIONS_VERIFIED: 本家 R6 五條字面 CLOSED；obl／fmt rc=0；mutation 實列 26 連續；三段式位置覆蓋探針；golden gap1／gap2＝PURGED_else；api 零 `run()`；IC 無 `build_event_keys`；Task 9.3 L187–188 與 (5.1) 對讀  
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`PYTHONPATH=. venv/bin/python` 探針（coverage／golden gap／呼叫圖）→ 見 `/tmp/grok-splitunify-b9-review-r7/probe_all.out`；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r7-grok.md --family grok`  
FAILURES_SEEN: `_event_keys` 初呼缺 `b` 參數 → 改傳 `(index,b)` 後取得 gap 分類  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r7-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R7-P1-01,GROK-R7-P1-02,GROK-R7-P1-03
CLOSED: GROK-R6-P1-01,GROK-R6-P1-02,GROK-R6-P1-03,GROK-R6-P1-04,GROK-R6-P1-05
STATUS: DONE
