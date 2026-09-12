# SPLITUNIFY D-002 閉合輪 R7 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R7  
family: composer  
findings-round: R7  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第七次修訂）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: R6 十六條歸八群、全部採納 | **fact-verified** | 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r6/synth.md` 群集表 |
| brief fact-verified: 隔離帶區間逐字取自 `holdout_test_row_index` | **fact-verified** | `sed -n '40,43p' momentum/core/split_preview.py` |
| brief fact-verified: `purged` 僅 `["event_id","reason"]` | **fact-verified** | `split_projection.py:556` columns 定義 |
| brief fact-verified: mutation 表列 26、ID 01–26 連續 | **fact-verified** | `rg -o 'M-SU-D2-[0-9]{2}' docs/SPLITUNIFY_SPEC.D-002.md \| sort -u \| wc -l` → 26 |
| brief fact-verified: 第七次修訂 obligation／format rc=0 | **fact-verified** | `obligation_block_check.sh` rc=0；`doc_format_precheck.sh` rc=0 |
| brief assumed: `D-002-C5` (5.1) 三分類逐處判對 | **assumption，本輪否證** | 見必答 2：`Task 9.3` L187–188 與 (5.1) 互斥 |
| brief assumed: `Task 9.2b` 三段式覆蓋所有位置情形 | **assumption，本輪否證** | 見必答 3：缺 `decision_at_ms`→位置映射演算法 |
| brief assumed: 答案窗事件側廣播不改單 TF 行為 | **assumption，部分否證** | 見必答 3：隔離帶由 purge→raise 會動 golden |
| brief assumed: `Task 9.1` 採 (b) 後 IC 主線有 `discarded` 可揭露 | **assumption，本輪否證** | 見必答 4：`ic_filter_orchestrator` 不呼叫 `build_event_keys` |

## 必答 1–5（成對立場）

**1. 本家 R6 finding 是否閉合**

| ID | R6 斷言 | 第七次修訂落點 | 判定 | 確認方式 |
|----|---------|----------------|------|----------|
| COMPOSER-R6-P1-01 | 不等式與界外 fail-closed 無先後；gap 上 train≠purged | `Task 9.2b` L174–177 三段式＋gap fail-closed raise | **CLOSED（規格）** | `sed -n '174,177p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R6-P1-02 | (3.2) 漏 purged∩assignments | L180 跨表互斥＋L181 事件側答案窗廣播 | **CLOSED（規格）** | `sed -n '180,181p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R6-P2-01 | `Task 9.1` 二擇一無具名落點 | L144 定案採 (b)＋指 IC 主線 | **部分閉合** | 擇一已寫，但 IC route／response／UI **仍無具名**（見 R7-P1-01） |
| COMPOSER-R6-P2-02 | `per_symbol_n`／門檻 TF 膨脹 | `Task 9.4` L196 `event_id` 去重＋終端揭露 | **CLOSED（規格）** | `sed -n '196,197p' docs/SPLITUNIFY_SPEC.D-002.md` |

**2. 挑戰 `D-002-C5` (5.1) 三分類——(甲) 有判錯**

主委 R6 將 `tables`／`counterexample_classifier`／`candidate_ledger`／`dedupe` 保留集列入 **(甲) 事件級維持**（L74），但 `Task 9.3` L187–188 仍要求前三者改「複合鍵 lookup」、`dedupe` 改 `(event_id, feature_timeframe)` 粒度——與 (5.1) **同檔互斥**。

碼證（三處皆 `.loc[eid]` 於 **event_level／manifest**，一列＝一事件，非 assignments 複合鍵表）：

| 處 | 檔案:行 | 現行粒度 | (5.1) | Task 9.3 L187 | 複合鍵上線後會取到哪一列 |
|----|---------|----------|-------|---------------|-------------------------|
| tables | `tables.py:214,234` | `receipts.event_level.set_index("event_id")`；`cl.loc[eid]` 於事件級 clusters | (甲) 維持 | 改複合鍵 lookup | **不適用**——未讀 assignments；改複合鍵 lookup 會讓實作者去改 event_level 索引而破壞一事件一列契約 |
| counterexample_classifier | `counterexample_classifier.py:52,62` | `ev_receipt.loc[eid]` on event_level | (甲) 維持 | 改複合鍵 lookup | 同上；無第二列可取，改法屬過度 |
| candidate_ledger | `candidate_ledger.py:155,160` | `rec.loc[eid]` on event_level | (甲) 維持 | 改複合鍵 lookup | 同上 |
| dedupe 保留集 | `dedupe.py:39,125-128` | `build_event_manifest` 只吃 `receipts.event_level`；`cluster_first` 按 `dedupe_cluster_id` 於**事件級** table | (甲) 維持 | 改複合鍵粒度 | manifest 無 `feature_timeframe` 欄；硬改會要求 manifest 複製成多列而破壞 `w=1/n`／簇語意（R6 已否證 clusters 複製） |

**結論**：(甲) 對上述四處之分類**正確**；**錯的是 Task 9.3 殘留的第六次修訂 bullet**（L187–188 未隨 R6 同步）。`pattern_bridge` 在 (丙) 須去重、不得改複合鍵索引——與 L187 把 pattern_bridge 與 tables 混列亦不一致。

**3. 三段式判準是否完備；答案窗改事件側是否動單 TF golden**

**位置映射缺口（具體反例）**：三段式步驟 1 要求「`decision_at_ms` **映射之位置**」落隔離帶，但全文**未定義**離網格 `decision_at_ms` 如何映射到 `feature_index` 位置（R5 實證 1h open 非 4h open 者 15,264／20,352；L174 亦承認）。實作者至少有三種互斥實作：`searchsorted` 最近格、`floor` 到 train/test 覆蓋區、或直接 fail-closed——步驟 2「落在 train 或 test 覆蓋區後才用不等式」對**不在 `index_ms` 集合**的 `decision_at_ms` 無單一神諭。⇒ 存在落在「三種敘述之外」的第四種實作歧路。

**單 TF／golden 影響**：現行 `:552-553` 對「`cutoff` 不在 train_ms 且不在 test_ms`」走 **purge**（集合成員語意）。第七次修訂步驟 1 對隔離帶改 **raise**（L175）。單 TF fixture 若存在 decision／cutoff 落在 gap 之事件：改前進 `purged`、改後 raise 或整批 fail-closed——**§V 無**「單 TF 舊 purged 集合不變」斷言，與 `(G-3)` 單 TF 逐值不變存在衝突風險。答案窗改事件側：單 TF 每事件僅一列時，事件側廣播與逐列 `in_train` **多數等價**；風險主因在 gap 處置由 purge→raise，非答案窗公式本身。

**4. `Task 9.1` 採 (b) 後 `discarded` 如何到回應與畫面**

**現況碼證**：`build_event_keys` 為 `discarded` 唯一來源（SPEC L135–136），但 `rg 'discarded' momentum/ api/` 對 split 語境 **零命中**（僅 FF retention 無關用法）。`EventSamplePipeline.run`（內部呼叫 `build_event_keys`）**僅**見於 `tests/momentum/event_samples/test_splitunify_wiring.py`；生產 `case_import_service` 恆 `run_event_study_only`（L1592–1609）。`ic_filter_orchestrator._build_holdout_split_plan`（`:604-609`）只呼叫 `holdout_boundary(features_df)`，**不經** `build_event_keys`／`derive_event_split_from_plans`。

**仍缺具名落點**（L144 要求但未寫）：

| 層 | 缺什麼 |
|----|--------|
| producer | 哪條 IC route 會呼叫 `EventSamplePipeline.run`（或等價）並取得 `discarded` |
| API response | 哪個 Pydantic 模型／JSON 鍵（非作廢的 `EventAnalyzeResponse.summary`） |
| 前端 | 哪個元件／面板（非作廢的 `EventTablesPanel.tsx:347`） |
| 測試 | 哪條 route-level pytest 命令 |

**5. I1–I8 修訂引入的新問題**

| 群 | R6 落點 | R7 複驗 | 新問題 |
|----|---------|---------|--------|
| I1 三段式 | L174–177 | **已對位** | 映射演算法未定（P2-01） |
| I2 跨表互斥 | L180–181 | **已對位** | 無 |
| I3 物化維持事件級 | L186 | **已對位**；`merge validate="many_to_one"` 複合鍵後仍成立（`feature_materialization.py:53`） | 無 |
| I4 三分類 | L74 | **已對位**，但 L187–188 未同步（P1-02／P1-03） | Task 9.3 與 (5.1) 互斥 |
| I5 採 (b) | L144 | 擇一已寫 | IC 路徑仍不可達 `discarded`（P1-01） |
| I6 匯出 Map 排除 | L203 | **已對位** | `M-SU-D2-11` 仍假紅（P2-02） |
| I7 門檻去重 | L196–197 | **已對位** | 無 |
| I8 mutation 26 條 | L216–245 | **已對位**（26 唯一 ID） | 無 |

與 `D-001`／`D-002-C6`／既有 golden：**無新 schema 衝突**；gap purge→raise 可能動單 TF golden（必答 3）。

## §1 必查摘要（11 類）

1. **矛盾**：`D-002-C5` (5.1) vs `Task 9.3` L187–188（P1-02／03）；§V L207 vs Task 9.1 作廢落點（P2-03）；`M-SU-D2-11` vs Task 9.5（P2-02）——**有**
2. **漏項**：9A `discarded` IC 生產／API／UI 仍無具名（P1-01）——**有**
3. **不可測**：§V 9.1 仍指作廢三層；三段式缺映射演算法——**有**
4. **quant 假設**：gap raise 改變 purged 集合——**有（隨 P2-01）**
5–11. 過度工程／OOM／cache／API／測試／Agent／短命工——**無新增**（除上述矛盾）

## COMPOSER-R7-P1-01

**斷言**: `Task 9.1` 定案採 (b) 並指 `ic_filter_orchestrator` 為投影消費者，但該模組只對 `features_df` 呼叫 `holdout_boundary`，**從不**呼叫 `build_event_keys`／`EventSamplePipeline.run`；repo 內 split 語境 `discarded` 零實作、`.run()` 僅見於測試 ⇒ 9A 仍無可執行生產路徑。

**碼證**: `ic_filter_orchestrator.py:604-609` 僅 `holdout_boundary(_feature_dt_index,...)`；`pipeline.py:747` 之 `build_event_keys` 只在 `EventSamplePipeline.run` 內；`rg 'EventSamplePipeline\(\)\.run' --glob '*.py'` 非測試命中 0（僅 `handoffs/` probe）。`case_import_service.py:1592-1609` 仍 event-study-only。RECHECK: 對讀 `Task 9.1` L144 與上述三路徑 call graph。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293;momentum/Analysis/event_samples/pipeline.py#99bfddace904

[BLOCKING] 信心度=High。實作者按 (b) 在 `ic_filter_orchestrator` 加 summary 鍵也拿不到 `build_event_keys` 的 `discarded` dict，9A 驗收只能寫 unit test 假綠。**修法**：`Task 9.1` 補**具名** IC route（例 `api/routes/ic_analysis.py` 哪個 handler）、response 鍵、前端面板，並要求該路徑實際呼叫 `EventSamplePipeline.run`（或把 `discarded` 從 `build_event_keys` 接到已存在的投影鏈）；§V 9.1 斷言改指向該 route 之契約測試命令。**可行性**：`test_splitunify_wiring.py` 已有 `.run()` 端到端樣板，缺的是生產接線規格。

## COMPOSER-R7-P1-02

**斷言**: `Task 9.3` L187 要求 `tables`／`counterexample_classifier`／`candidate_ledger` 之 `.loc[eid]` 改複合鍵 lookup，與 `D-002-C5` (5.1) 將三者列於 **(甲) 事件級——維持不動** 互斥；三處碼證皆只讀 `receipts.event_level`／`manifest.table`（一列＝一事件），改複合鍵會誤導實作者改 event-level 索引。

**碼證**: SPEC L74 (甲) 逐字列名三者＋ `tables` 之 `.loc[eid]`；L187 要求改複合鍵 lookup。`tables.py:214,234` `ev.loc[eid]` on event_level；`counterexample_classifier.py:52,62`；`candidate_ledger.py:155,160`。RECHECK: 對讀 L74 vs L187 ＋ 上列三檔 `set_index`／`.loc`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/tables.py#843ba7f68172;momentum/Analysis/event_samples/counterexample_classifier.py#444599323e49;momentum/Analysis/event_samples/candidate_ledger.py#b75159633935

[BLOCKING] 信心度=High。Agent 照 L187 改 tables 會破壞事件級 forward-return 表（`manifest.table` 一列一事件），與 R6 I3／I4 方向相反。**修法**：刪除 L187 中三者（保留 `pattern_bridge` 於 (丙) 去重敘述，或移至獨行指向 `Task 9.3`／(5.1) (丙)）；§V Task 9.3 測試改為「event-level `.loc[eid]` 值不變」而非複合鍵。**可行性**：純 SPEC 同步，無需改碼。

## COMPOSER-R7-P1-03

**斷言**: `Task 9.3` L188 要求 `dedupe` 之 `cluster_first` 保留集改 `(event_id, feature_timeframe)` 粒度，與 `D-002-C5` (5.1) 將 `dedupe` 之保留集列於 **(甲) 事件級維持** 互斥；`build_event_manifest` 只吃 `receipts.event_level`，無 `feature_timeframe` 維度。

**碼證**: L74 (甲) 含 `dedupe` 之保留集；L188 要求複合鍵粒度。`dedupe.py:39` `ev = receipts.event_level.copy()`；`:125-128` `groupby("dedupe_cluster_id")` 於事件級 table。RECHECK: 對讀 L74 vs L188 ＋ `dedupe.py:39,125-128`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e

[BLOCKING] 信心度=High。照 L188 實作會要求 manifest 按 feature TF 複製列，直接衝突 `Task 9.2a` clusters 維持事件級與 `w=1/n` 語意。**修法**：刪除 L188 或改為「dedupe 維持事件級；複合鍵只影響下游消費 assignments 之處」。**可行性**：SPEC 一字刪除即可對齊 R6 I4。

## COMPOSER-R7-P2-01

**斷言**: `Task 9.2b` 三段式步驟 1 依「`decision_at_ms` 映射之位置」判隔離帶，但未定義離 `feature_index` 網格之 `decision_at_ms` 的位置映射演算法，實作者無法寫出單一 deterministic 實作或 §V 反例。

**碼證**: L174–177 三次出現「映射之位置」／「落在 train 或 test 覆蓋區」但無 `searchsorted`／最近鄰／fail-closed 擇一；L174 承認大量 `decision_at_ms ∉ index_ms`。現行 `:531-533` 用 `feature_cutoff_ms in train_ms/test_ms`（集合成員）。RECHECK: 構造 `decision_at_ms` 不在 `index_ms`、cutoff 在 train 之單 TF 事件，比對三種映射下步驟 1–3 結果是否一致。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[MAJOR] 信心度=High。Task 9.2b 實作時會各自選映射規則，gap／界外與不等式優先再次分歧；單 TF golden 可能因 gap 由 purge 改 raise 而位移。**修法**：在 `Task 9.2b` 增可操作映射定義（建議：先將 `decision_at_ms` 映射到 `feature_index` 最近 **不晚於** decision 的 bar 位置，再套三段式；離網格且無法映射 ⇒ fail-closed）；§V 增單 TF gap 事件 purge vs raise 成對 ASSERT。**可行性**：與 R6 I1 三段式同區塊增補，不動切分數學。

## COMPOSER-R7-P2-02

**斷言**: `M-SU-D2-11` 定義「前端 `byEventId` Map 鍵退回 `event_id`」為缺陷，與 `Task 9.5` L203／`D-002-C5` (5.1) **排除於複合鍵遷移之外**（維持 event-level 鍵）矛盾——正確實作恰恰是維持 `event_id`／`canonicalEventId` 鍵。

**碼證**: L203 與 L74 (甲) 搜尋頁匯出 Map；mutation L230 `M-SU-D2-11`「鍵退回 `event_id`」應紅。`eventExport.ts` record 無 `feature_timeframe`（R6 碼證）。RECHECK: 對讀 L203 vs mutation 表 `M-SU-D2-11`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd

[MAJOR] 信心度=High。實作者為通過 mutation 11 會把已排除的 Map 改成複合鍵，重現 R6 I6 匯出 miss。**修法**：刪除 `M-SU-D2-11` 或改為反向 mutation「**錯誤**改成複合鍵導致 export miss」；應紅測試對齊 `Task 9.5` 排除敘述。**可行性**：mutation 表一行改寫。

## COMPOSER-R7-P2-03

**斷言**: §V `Task 9.1` L207 仍要求「summary／**API 回應**／**前端型別**三層皆帶該欄」，但 `Task 9.1` L143–144 已作廢 `case.py`／`EventTablesPanel` 落點且改掛未指名的 IC 路徑 ⇒ §V 與正文互斥，`M-SU-D2-02`／`03` 應紅測試仍指向作廢路徑。

**碼證**: L207 三層 ASSERT；L143「上列四個落點…全部作廢」；L144 僅抽象「IC 投影路徑之回應欄位、其前端顯示位置」無 route 名。mutation L221–222 仍寫 API／前端契約測試。RECHECK: `sed -n '143,144,207p' docs/SPLITUNIFY_SPEC.D-002.md` ＋ mutation 表 01–03。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f266e6e999bd

[MAJOR] 信心度=High。驗收會逼實作者去寫已作廢 route 的契約測試而假綠，或與 (b) 裁定衝突。**修法**：§V 9.1 改寫為 IC 主線三層（待 P1-01 指名後逐字填入）；`M-SU-D2-02`／`03` 應紅測試同步改指向該 route。**可行性**：依賴 P1-01 先定落點，可同批修。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` | **OBLIGATION_RC=0** |
| `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `rg -o 'M-SU-D2-[0-9]{2}' docs/SPLITUNIFY_SPEC.D-002.md \| sort -u \| wc -l` | **26** |
| `rg 'EventSamplePipeline\(\)\.run' --glob '*.py' \| rg -v test` | **0 生產命中** |
| `sed -n '604,609p' momentum/Analysis/ic_filter_orchestrator.py` | 僅 `holdout_boundary` |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R7-P1-01,COMPOSER-R7-P1-02,COMPOSER-R7-P1-03
CLOSED: COMPOSER-R6-P1-01,COMPOSER-R6-P1-02,COMPOSER-R6-P2-02

ASSUMPTIONS_VERIFIED: R6 八群落點逐條對讀第七次修訂；三分類四處碼證；IC call graph；mutation 26 計數；obligation／format rc=0  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r7-composer.md --family composer`（交件前自跑）  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
