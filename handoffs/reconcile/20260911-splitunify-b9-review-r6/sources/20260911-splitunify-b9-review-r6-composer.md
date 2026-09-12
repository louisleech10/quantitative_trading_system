# SPLITUNIFY D-002 閉合輪 R6 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R6  
family: composer  
findings-round: R6  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第六次修訂）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: R5 十一條歸八群、全部採納 | **fact-verified** | 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r5/synth.md` 群集表 |
| brief fact-verified: `split_projection.py:291-292` merge `validate="1:1"` | **fact-verified** | `sed -n '291,303p' momentum/Analysis/event_samples/split_projection.py` |
| brief fact-verified: mutation 表列 25、ID 01–25 連續 | **fact-verified** | `rg -c 'M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md` → 29（含正文引用）；表列 L209–234 共 25 行 |
| brief fact-verified: 第六次修訂後 obligation／format rc=0 | **fact-verified** | `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`doc_format_precheck.sh` → rc=0 |
| brief assumed: Task 9.2＋9.2a＋9.2b 到位後生產路徑不再丟列 | **assumption；規格層已對位、碼未動** | 第六次修訂 L155–156 已指派 merge／`feature_timeframe`；現碼仍 `validate="1:1"`；探針 Case C 仍 2 列 |
| brief assumed: 9.2b 不等式與 `train_ms`／`test_ms` 集合成員等價 | **assumption，本輪否證** | 見必答 3：embargo 間隙反例 |
| brief assumed: (3.2) raise 位置正確 | **assumption，本輪否證** | 見必答 4：漏「purged＋assignments」異態 |
| brief assumed: Task 9.1 二擇一足以驗收 9A | **assumption，本輪否證** | 見必答 5：兩選項皆無具名 route／producer |

## 必答 1–5（成對立場）

**1. 本家 R5 finding 是否閉合**

| ID | R5 斷言 | 第六次修訂落點 | 判定 | 確認方式 |
|----|---------|----------------|------|----------|
| COMPOSER-R5-P1-01 | `build_event_keys:291-303` merge／輸出欄未指派 | `Task 9.2` L155–156 逐行指名 merge、`feature_timeframe`、docstring `:271` | **CLOSED（規格）** | `sed -n '155,156p' docs/SPLITUNIFY_SPEC.D-002.md`；`(5.2)` L76 cross-ref 已改指 `Task 9.2` |
| COMPOSER-R5-P1-02 | mutation 缺 producer 內部 merge 路徑 | `M-SU-D2-23` L232–233；正文 L206 改為 25 條 | **CLOSED（規格）** | `sed -n '232,233p' docs/SPLITUNIFY_SPEC.D-002.md` |

現碼尚未實作（預期）；closure 指**規格施工單已對位**，非宣稱已上線。

**2. 第五層在哪——`EventSamplePipeline.run` → `assignments` → `feature_materialization`**

自 `pipeline.run` L693 沿 `given` 非空分支（L734）走讀至 `return`（L766），**所有**會讓「全量多 feature TF」失效、折疊或錯鍵的關卡如下：

| # | 關卡 | 檔案:行 | 現行行為 | 第六次修訂是否指派 | 判定 |
|---|------|---------|----------|-------------------|------|
| G1 | 四參數投影閘 | `pipeline.py:723-732` | `selected_timeframe=None` ⇒ raise | `Task 9.2` L151–152 | **已指派（R4）** |
| G2 | caller `str()` | `pipeline.py:747` | `str(None)`→`"None"` | `Task 9.2` L153–154 | **已指派（R3）** |
| G3 | producer 單選過濾 | `build_event_keys:279-283` | 只留 selected TF | `Task 9.2` L154 | **已指派** |
| G4 | event-level `validate="1:1"` merge | `build_event_keys:291-292` | 多 `per_tf` ⇒ MergeError | `Task 9.2` L155 | **已指派（R5）** |
| G5 | 輸出 trigger `timeframe` | `build_event_keys:300-302` | 複合鍵碰撞風險 | `Task 9.2` L155(b) | **已指派（R5）** |
| G6 | `event_id` 重複 guard | `_derive_single_symbol:440-446` | 多列同 `event_id` raise | `Task 9.2a` L163–165 | **已指派** |
| G7 | per-cutoff 判側／逐列 purge | `_derive_single_symbol:530-553` | 同事件可 1h purged／4h test | `Task 9.2b` L169–174 | **已指派** |
| G8 | **`assignments` 後物化折疊** | **`feature_materialization.py:93-132`** | **`groupby("event_id")`＋`row_vals.update` 折成 1 列／事件** | **`Task 9.3` L179** | **第五層（R5 H7 已採納）** |
| G9 | pipeline 記帳粒度 | `pipeline.py:760-762` | `n_train`／`n_test` 用 assignment **列數** | `Task 9.4` L186–189 | 不阻全量路徑，但會誤報 |
| G10 | summary `features.n_rows` | `pipeline.py:687-688` | `len(features)` 為折疊後事件數 | **未逐處指派** | 記帳／揭露，非折疊點 |

**結論**：R5 第四層（G4＋G5）第六次修訂已在 `Task 9.2` 對位。**第五層＝`assignments` 產出後的 `feature_materialization` `groupby+update`（G8）**——R5 已由 `CODEX-R5-P1-05`／H7 指出，`Task 9.3` 已逐處列名；**未發現第六層**在 `run()` 內再靜默丟 TF。`_materialize`（L673–676）不讀 `split_plan`，但讀**全量** `receipts.per_tf`（L53），與投影單選脫鉤——物化折疊與投影丟列是**兩條獨立缺陷**，皆須各自 Task 關。

**3. 不等式 vs 集合成員——embargo 間隙反例**

設 `feature_index` 毫秒序列 `[1000,2000,3000, 4500, 6000,7000]`（4500 為 purge／embargo 區，**不在** train/test plan 的 `row_index_local` 內）：

- `train_ms={1000,2000,3000}`，`test_ms={6000,7000}`，`test_start_ms=6000`
- 事件 `e1`：`decision_at_ms=4500`（觸發 TF 合法 bar；PIT 允許 `feature_cutoff_ms≤decision_at`）

| 判準 | 對 `e1` 的側別 |
|------|----------------|
| **不等式**（`Task 9.2b` L173：`decision_at_ms < test_start_ms` ⇒ train） | `4500 < 6000` ⇒ **train** |
| **集合成員**（現行 L532–533：`cutoff in train_ms`／`in test_ms`；若套在 `decision_at_ms`） | `4500 ∉ train_ms` 且 `4500 ∉ test_ms` ⇒ **purged**（走 L552–553） |

⇒ 同一事件得 **train** vs **purged**，非單純「邊界 off-by-one」。`Task 9.2b` L173 同段又要求對「落在 plan 時間界外」**fail-closed**，但未寫與不等式的**先後／優先**——實作者可先實作不等式而把 embargo 區事件標成 train，或 fail-closed 整批拒絕，兩者語意不同且 §V 無成對斷言。

**4. `(3.2)` raise 的位置——與 `purged` 列互動**

`Task 9.2b` L174 定：複合鍵 guard **之後**、寫入 `assignments` **之前**，按 `event_id` 檢查 `split_label` 唯一。

**漏掉的異態**：同一 `event_id` **部分列進 `purge_rows`、部分列進 `assign_rows`**——現行碼在答案窗仍用**逐列** `in_train`（L540–542）時即可發生：

- `e1`／1h：`in_train=True`＋答案窗跨界 ⇒ **purged**（L541）
- `e1`／4h：`in_train=False`、`in_test=True` ⇒ **assignments=test**（L544–547）

`(3.2)` 檢查只看即將寫入 `assignments` 的 `split_label`；上例 assignments 僅 4h 一列 `test` ⇒ **檢查通過**，但事件已處於「一 TF purged、一 TF test」非法態。`M-SU-D2-24` 抓的是「答案窗仍逐列 `in_train`」，**不是**「禁止同 event 同時出現在 purged 與 assignments」。`Task 9.2b` L172 要求答案窗改**事件側**廣播，但若 Agent 先上 (3.2) 而未改 purge 邏輯，guard **靜默放行**。

**5. H1–H7 修訂引入的新問題**

| 群 | 本輪新問題 |
|----|-----------|
| H1 | 已閉（R5）；無新衝突 |
| H2 | (3.2) 落點已寫，但**未覆蓋 purged∩assignments**（見 P1-02） |
| H3 | 25 條 mutation 已對位；無新衝突 |
| H4 | baseline 例外已寫；與 `D-002-C6` 一致 |
| H5 | 二擇一仍**無具名 route**（見 P2-01） |
| H6 | 不等式與 fail-closed／集合成員**優先未定**（見 P1-01） |
| H7 | `Task 9.3` 與 `9.2` 無重複；`§V` L198 已指定 `assignments` 斷言標的 |

與 `D-001`／`D-002-C6`／`Task 9.3` **無新 schema 衝突**；`per_symbol_n` 行數語意見 P2-02。

## §1 必查摘要（11 類）

1. **矛盾**：`Task 9.2b` 不等式與界外 fail-closed 先後未定（見 P1-01）——**有**
2. **漏項**：`Task 9.1` 二擇一無 executable 落點（P2-01）；`plan.summary.per_symbol_n` 未入 `Task 9.4`（P2-02）——**有**
3. **不可測**：§V 缺 embargo 間隙側別成對 ASSERT——**有（隨 P1-01）**
4. **quant 假設**：embargo 區事件被不等式標 train 可能洩漏——**有**
5–11. 過度工程／OOM／cache／API／測試／Agent／短命工——**無新增**（`Task 9.3` 逐處列名已足；§R 禁部分上線）

## COMPOSER-R6-P1-01

**斷言**: `Task 9.2b` 同時要求「`decision_at_ms < test_start_ms` ⇒ train」不等式與「`decision_at_ms` 落 plan 時間界外 ⇒ fail-closed」，但未定義兩者先後；在 train/test 間 embargo 間隙，不等式給 **train**、集合成員語意給 **purged**，實作可靜默選錯側。

**碼證**: 反例構造見必答 3（`train_ms={1000,2000,3000}`、`test_start_ms=6000`、`decision_at_ms=4500`）。現行集合成員路徑 `split_projection.py:532-553`；規格 `Task 9.2b` L173 兩句並列無優先。RECHECK: 讀 L173＋對照 `:532-553` 行為。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。Agent 實作 9.2b 時若只寫不等式，embargo 區事件會進 train assignments 而 canonical plan 根本不承認該時刻 ⇒ 與 IC 邊界不一致、§V `Task 9.2b` 反例可假綠。**修法**：`Task 9.2b` 增**有序**判準——(1) 先用 `train_plan.time_bounds`／`test_plan.time_bounds`（或 `row_index_local` 首尾）驗 `decision_at_ms` 落在 train 或 test 覆蓋區，否則 fail-closed；(2) 僅在 (1) 通過後才用不等式／集合成員定側；§V 增成對 ASSERT（間隙 `decision_at` 須 raise 或整事件 purged，不得標 train）。**可行性**：僅改 `_derive_single_symbol` 判側區塊與測試，不動切分數學；`time_bounds` 同源閘已在 L511–522 存在，可复用同一 `feature_index` 切片。

## COMPOSER-R6-P1-02

**斷言**: `(3.2)` 之 `AlignmentViolationError` 若只檢查即將寫入 `assignments` 的 `split_label` 唯一，**漏掉**「同一 `event_id` 同時出現在 `purge_rows` 與 `assign_rows`」——現行逐列答案窗 purge 即可觸發，且 (3.2) 不會 raise。

**碼證**: `split_projection.py:540-553`：1h 列 `in_train`＋答案窗 ⇒ `purge_rows`；4h 列 `in_test` ⇒ `assign_rows` test；無後續「同 event 跨表」檢查。`Task 9.2b` L174 僅寫 `split_label` 唯一。RECHECK: 構造 `label_end_ms≥test_start_ms` 且兩 TF cutoff 分屬 train/test 集合之 `event_keys` 兩列，單步執行 L530–553 迴圈。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。部分實作（先上 C3.2、未改事件側 purge）會留下非法 OOS 前兆而測試綠。**修法**：`Task 9.2b` L174 增——同 `event_id` **不得**同時出現在 `purge_rows` 與 `assign_rows`（或：答案窗 purge 須在判側後對該 event **所有** feature TF 列廣播後再檢查）；§V 增 ASSERT「異側或 purged∩test 混合 ⇒ raise」。**可行性**：迴圈後加 `set(purge_rows.event_id) ∩ set(assign_rows.event_id)` 檢查即可；與 `M-SU-D2-24` 互補。

## COMPOSER-R6-P2-01

**斷言**: `Task 9.1` L143 二擇一（改 universe producer **或** 移出終端揭露）仍無**具名** route／service／掛載點，兩選項皆無法寫出可執行驗收命令。

**碼證**: `case_import_service.py:1609` 仍固定 `run_event_study_only_with_params`；L143 僅抽象描述。RECHECK: `rg -n 'run_event_study_only' api/services/case_import_service.py`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;api/services/case_import_service.py#d2571793953f

[MAJOR] 信心度=High。9A 可在無生產路徑下「規格完成」而終端永不顯示 `discarded`。**修法**：擇一後寫死——例 (a) `POST …/analyze` 改調 `holdout_boundary`＋`EventSamplePipeline.run` 並指名 universe 來源欄位；或 (b) 揭露改掛 IC 投影 route 與前端面板路徑。**可行性**：與 R5 H5 同型，僅缺指名；IC 主線已有 `run()` 可複用（`pipeline.py` 已存在）。

## COMPOSER-R6-P2-02

**斷言**: `_derive_single_symbol` 之 `per_symbol_n`（L559–561）與 `insufficient_events_in_test` 門控（L716–718）用 `event_keys` **行數**，複合鍵後會膨脹；`Task 9.4` 未指派修正 `plan.summary.per_symbol_n`。

**碼證**: `split_projection.py:559-561` `value_counts()` on `event_keys`；`Task 9.4` L186–189 只列 pipeline 頂層 count 與 wiring。RECHECK: 2 event×2 TF ⇒ `per_symbol_n` 報 4 非 `n_events=2`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[MAJOR] 信心度=Medium。可能誤觸／誤過 `tier_min_test_events` 與 degraded 旗標。**修法**：`Task 9.4` 增 `per_symbol_n` 改 `nunique(event_id)` 或並列 `n_event_tf_rows`。**可行性**：單行聚合改動，與 C6 同批。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` | A/C `NO_RAISE 2列`；B/D `RAISED`（與 §A 一致） |
| `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` | **OBLIGATION_RC=0** |
| `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `rg -c decision_at_ms momentum/Analysis/event_samples/split_projection.py` | **0** |
| `rg -c AlignmentViolationError momentum/Analysis/event_samples/split_projection.py` | **0** |
| `sed -n '291,303p' momentum/Analysis/event_samples/split_projection.py` | 仍 `validate="1:1"` |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R6-P1-01,COMPOSER-R6-P1-02
CLOSED: COMPOSER-R5-P1-01,COMPOSER-R5-P1-02

ASSUMPTIONS_VERIFIED: R5 兩條閉合逐條對照第六次修訂 L155–156／L232／L206；`run`→`assignments`→`materialize` 全關卡走讀；embargo 間隙與 purged∩assignments 反例構造；`case_import_service` 可達性複驗  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r6-composer.md --family composer`（交件前自跑）  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
