# SPLITUNIFY D-002 閉合輪 R5 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R5  
family: composer  
findings-round: R5  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第五次修訂）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: R4 八條歸五群、7 採納 1 駁回 | **fact-verified** | 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r4/synth.md` 群集表 |
| brief fact-verified: `pipeline.py:723-732` 四參數閘逐字 | **fact-verified** | `sed -n '723,732p' momentum/Analysis/event_samples/pipeline.py` |
| brief fact-verified: `split_projection.py` 全檔 `decision_at_ms` 命中 0 | **fact-verified** | `rg -c decision_at_ms momentum/Analysis/event_samples/split_projection.py` → 0 |
| brief fact-verified: 第五次修訂後 obligation／format rc=0 | **fact-verified（本輪 2/3）** | `obligation_block_check.sh` rc=0；`doc_format_precheck.sh` rc=0；`spec_xref_check --synth` r4 rc=0 |
| brief assumed: Task 9.2＋9.2a＋9.2b 到位後生產路徑不再丟列 | **assumption，本輪否證成功** | 見必答 2：`build_event_keys:291-303` 仍為 event-level `validate="1:1"` merge 且輸出欄取自 `event_level.timeframe`（trigger TF），非 `per_tf.timeframe` |
| brief assumed: Task 9.2b purge 改事件側不與 purged 衝突 | **fact-verified（反例構造）** | 見必答 3：同事件 1h purged／4h=test 之現行逐列行為 |
| brief assumed: (5.2) 落地後契約不誤導現況 | **fact-verified** | L76 已標「落地後」並 cross-ref 各 Task；單讀 (5.2) 不會當現況 |
| brief assumed: mutation 23 條覆蓋三 Task 與四參數閘 | **assumption，本輪否證成功** | 見必答 5：缺 `build_event_keys:291-292` merge 路徑之第 24 條 |

## 必答 1–5（成對立場）

**1. 本家 R4 finding 是否閉合**

| ID | R4 斷言 | 第五次修訂落點 | 判定 | 確認方式 |
|----|---------|----------------|------|----------|
| COMPOSER-R4-P1-01 | (5.2) 仍 selected-only／event-only | L76 改寫為落地後契約（全量複合鍵、兩表含 `feature_timeframe`、`decision_at_ms` 錨） | **CLOSED（規格）** | `sed -n '76p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R4-P1-02 | §V Task 9.2 僅 schema、無 pipeline 級全量 ASSERT | L192-193 端到端 ASSERT＋`selected_timeframe=None` 不 raise；schema 改掛 9.2a L193 | **CLOSED（規格）** | `sed -n '192,194p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R4-P1-03 | (3.1) 無施工落點、`:530-553` 仍 per-cutoff | 新增 `Task 9.2b` L166-170 指名 `:530-553`＋`manifest.table.decision_at_ms` | **CLOSED（規格）** | `sed -n '166,170p' docs/SPLITUNIFY_SPEC.D-002.md`；現碼 `decision_at_ms` 仍 0 命中（實作未動，預期） |

本家 R3 僅 `COMPOSER-R3-P3-00` sentinel，無 P0／P1 待列 `CLOSED`。

**2. 第四層在哪——`EventSamplePipeline.run` → `assignments` 全量路徑關卡**

自 `pipeline.run`（L693）沿投影分支（`given` 非空，L734）逐段走讀；下列為**所有**會讓「全量多 feature TF」失效或產出錯鍵的關卡（含已修規格層、仍待實作者）：

| # | 關卡 | 檔案:行 | 現行行為 | 規格是否指派 | 本輪判定 |
|---|------|---------|----------|--------------|----------|
| G1 | 四參數投影閘 | `pipeline.py:723-732` | `selected_timeframe=None` 且其三參數齊 ⇒ `len(given)=3≠4` raise | Task 9.2 L151 | **已指派（R4 G1）** |
| G2 | caller `str()` 強轉 | `pipeline.py:747` | `str(None)`→`"None"` 字面 TF | Task 9.2 L153 | **已指派（R3）** |
| G3 | producer 單選過濾 | `build_event_keys:279-283` | 只留 `selected_timeframe` 之列 | Task 9.2 L153 | **已指派** |
| **G4** | **event-level `validate="1:1"` merge** | **`build_event_keys:291-292`** | **同 `event_id` 多 `per_tf` 列 merge 即 fail** | **(5.2) L76 指 Task 9.2a，但 9.2a 改法未列此行** | **第四層（本輪新開 P1-01）** |
| **G5** | **輸出欄取 trigger `timeframe`** | **`build_event_keys:300-302`** | **merge 只帶 `feature_cutoff_ms`，`timeframe` 來自 `event_level`（trigger TF，`alignment.py:216`），同事件多 feature TF 會得到相同 `timeframe` 值** | **Task 9.2 L153 要求 `(event_id, feature_timeframe)` 但未指名此行** | **第四層（本輪新開 P1-01）** |
| G6 | 簽名仍必填 `str` | `build_event_keys:259` | `selected_timeframe: str` 非 Optional | Task 9.2 L153 | **已指派** |
| G7 | `event_id` 重複 guard | `_derive_single_symbol:440-446` | 多列同 `event_id` raise | Task 9.2a L161 | **已指派** |
| G8 | per-cutoff 判側＋逐列 purge | `_derive_single_symbol:530-553` | `cutoff in train_ms/test_ms` 逐列定側 | Task 9.2b L166-170 | **已指派（R4 G2）** |
| G9 | embargo 疊加 | `pipeline.py:739-744` | canonical 投影禁 `embargo_ms` | 非本批 | N/A（與多 TF 無關） |
| G10 | `n_train` 列數求和 | `pipeline.py:760-762` | assignment **列數**非事件數 | Task 9.4 | 已指派（**在 assignments 產出之後**，不阻全量路徑本身） |

**結論**：R3（caller）、R4-G1（四參數閘）、R4-G2（判側迴圈）三層第五次修訂已對位；**第四層＝`build_event_keys` 內部 merge／輸出形狀（G4＋G5）**——Agent 只改 L279 過濾或 L747 caller 仍會在 G4 fail-closed 或 G5 產出假複合鍵（兩 feature TF 共用 trigger `timeframe`）。

**3. `Task 9.2b` 答案窗 purge 語意——逐列 vs 事件側**

**行為差異**：現行 L540-541 用**該列** `in_train`（來自 `feature_cutoff_ms`）決定是否套用答案窗 purge；`Task 9.2b` 要求改為**事件側**（由 `decision_at_ms` 定側後廣播）。

**反例（碼證路徑 `split_projection.py:530-553`）**：

- 設 `train_ms={3000}`、`test_ms={11000}`、`test_start_ms=10000`。
- 事件 `e1`：`decision_at_ms=5000∈train`（事件側應為 train），`label_end_ms=12000≥test_start`（答案窗跨邊界 ⇒ 整事件應 purge）。
- 同事件兩列：`1h feature_cutoff_ms=3000∈train`；`4h feature_cutoff_ms=11000∈test`（PIT 合法，`alignment.py:207`）。

| 列 | 現行逐列 | 9.2b 事件側（預期） |
|----|----------|---------------------|
| 1h | `in_train=True`＋答案窗 ⇒ **purged** | 事件側 train＋答案窗 ⇒ **purged** |
| 4h | `in_train=False`＋`in_test=True` ⇒ **split_label=test** | 事件側 train＋答案窗 ⇒ **purged** |

⇒ 現行會讓**同一事件**一列 purged、一列 test（非法 OOS 前兆）；事件側廣播後兩列皆 purged。`interval_crosses_split_boundary` 字面不變，但**觸發條件**從 per-cutoff `in_train` 改為事件級側別。

**4. `(3.2)` fail-closed 與 `Task 9.2b` 上線順序**

**會 raise。** 現碼尚無 `AlignmentViolationError`（`rg AlignmentViolationError momentum/Analysis/event_samples/split_projection.py` → 0），但 `Task 9.2a` L162 定案「複合鍵 guard **先於** C3 同側檢查」⇒ 實作 9.2a 時會加入 (3.2) 檢查。若此時 9.2b 未完成、仍用 L530-533 per-cutoff 判側，上例反例（1h∈train、4h∈test）在合法 receipts 下會被 (3.2) 判為異側而 raise。

`Task 9.2b` L170 已警告「不得在 (3.2) fail-closed 上線前保留 per-cutoff 判側」，但 **§P 未寫死 Task 依賴邊**（9.2／9.2a／9.2b 僅列平行項；§R 只說 9B 同批）。Agent 按編號 9.2→9.2a→9.2b 施工會先上 (3.2) 再改判側 ⇒ **合法輸入開始 raise**。規格有語意警告、無機械順序句。

**5. 修訂引入的新問題**

見 `COMPOSER-R5-P1-01`（(5.2) merge cross-ref 與 Task 9.2a 施工範圍不一致＋`build_event_keys` 第四層未逐行指派）及 `COMPOSER-R5-P1-02`（缺 `M-SU-D2-24` mutation）。與 `D-001`／`D-002-C6`／guard 先後／`M-SU-D2-19` **無新衝突**；`pipeline.py:760-762` 列數求和已由 Task 9.4 覆蓋。

## COMPOSER-R5-P1-01

**斷言**: 第五次修訂宣稱 `Task 9.2`＋`9.2a`＋`9.2b` 到位即可達全量路徑，但 **`build_event_keys` 內部 `event_level.merge(..., validate="1:1")`（`:291-292`）與輸出欄取自 `event_level.timeframe`（`:300-302`，trigger TF）仍未被任何 Task「改法」逐行指派**；`(5.2)` L76 將 merge 改判準 cross-ref 至 `Task 9.2a`，而 9.2a 改法僅列 `assignments`／`purged` schema 與 `:284-289`／`:441-444` guard——**不含 `:291-303`**。

**碼證**: `split_projection.py:291-303` 現行 `validate="1:1"` on `event_id`；merge 子集僅 `["event_id","feature_cutoff_ms"]`，輸出 `timeframe` 來自 `event_level`（`alignment.py:216` trigger TF），非 `per_tf.timeframe`（feature TF，`alignment.py:210`）。探針 Case C：`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → 仍只產 2 列。RECHECK: `sed -n '291,303p' split_projection.py`＋對照 `Task 9.2` L153、`Task 9.2a` L156-163、`(5.2)` L76。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e;momentum/Analysis/event_samples/split_projection.py#99bfddace904;momentum/Analysis/event_samples/alignment.py#e3b1c9a02f1d

[BLOCKING] 信心度=High。Agent 完成 Task 9.2 caller／四參數閘與 9.2a guard 後，在 G4 仍 `validate` fail-closed，或 G5 產出兩列相同 trigger `timeframe` 而 `(event_id, feature_timeframe)` 鍵碰撞／靜默覆蓋——**SU-RESID-2 第四次以不同形態復活**。**修法**：`Task 9.2` 改法增逐行：`build_event_keys:291-303` 改為以 `per_tf` 為行粒度 join `event_level`（複合鍵 `validate`）、輸出欄含 `per_tf.timeframe` 並依 `D-002-C0` (0.3) 命名 `feature_timeframe`；修正 `(5.2)` L76 cross-ref 指向 `Task 9.2` 而非 9.2a；§V 增一條 `build_event_keys` 輸出列數＝`per_tf` 列數 ASSERT。**可行性**：單函式局部重寫，不動切分數學。

## COMPOSER-R5-P1-02

**斷言**: mutation 目錄 23 條未覆蓋 **`build_event_keys:291-292` 仍保留 event-level `validate="1:1"`** 之缺陷——`M-SU-D2-20`／`21` 抓 caller／閘，`M-SU-D2-22` 抓判側迴圈，**無一條**抓 producer 內部 merge 路徑；Agent 可讓端到端測試 mock 全量列數而 merge 仍在單事件多 TF 時 fail-closed。

**碼證**: §V mutation 表 L202-225 共 23 行 ID；`rg 'validate.*1:1' momentum/Analysis/event_samples/split_projection.py` → L292。`M-SU-D2-20` 應紅測試＝端到端列數（L223），**不會**在僅改 caller、未改 merge 時紅（G4 在 `build_event_keys` 內先炸）。RECHECK: 對照表 L202-225＋`sed -n '291,292p' split_projection.py`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。缺少第 24 條 mutation ⇒ 回歸測試無法機械擋下 G4 復活。**修法**：新增 `M-SU-D2-24`｜`build_event_keys` 保留 `event_level.merge(..., validate="1:1")`｜`Task 9.2` 之 `per_tf` 列數＝輸出列數 ASSERT（或單元測試直接餵 2-TF receipts 期望 4 列輸出）。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` | A/C `NO_RAISE 2列`；B/D `RAISED`（與 §A 一致） |
| `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` | **OBLIGATION_RC=0** |
| `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-b9-review-r4/synth.md docs/SPLITUNIFY_SPEC.D-002.md` | **SYNTH-XREF PASS** |
| `rg -c decision_at_ms momentum/Analysis/event_samples/split_projection.py` | **0** |
| `rg -n 'build_event_keys\(' momentum api` | 生產僅 `pipeline.py:747` |
| `pytest -k build_event_keys_picks_selected_timeframe_only -q` | **1 passed** |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R5-P1-01,COMPOSER-R5-P1-02
CLOSED: COMPOSER-R4-P1-01,COMPOSER-R4-P1-02,COMPOSER-R4-P1-03

ASSUMPTIONS_VERIFIED: R4 三條閉合逐條對照第五次修訂；`EventSamplePipeline.run`→`assignments` 十關卡逐段走讀；purge 反例構造；9.2b/(3.2) 順序碼證；mutation 表 23 列對照  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r5-composer.md --family composer`  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
