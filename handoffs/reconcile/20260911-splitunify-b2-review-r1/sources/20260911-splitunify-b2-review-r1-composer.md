# SPLITUNIFY B2b code review R1（composer）

task-id: `20260911-SPLITUNIFY-B2-REVIEW-R1`  
family: `COMPOSER`  
findings-round: `R1`  
審查對象: commit `864efeb9` — `split_projection.py`（新）、`event_split.py`（抽出）、`test_splitunify_derive.py`（24 條）、`handoffs/20260911-splitunify-b2b-mutate.py`

## 被當成事實的未驗證假設（§0）

| 宣稱 | 類型 | 核對結果 |
|---|---|---|
| 24 條 derive 測試全綠 | **fact-verified** | `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` → 24 passed, rc=0 |
| mutation 9+1 全覆蓋 | **fact-verified** | `venv/bin/python handoffs/20260911-splitunify-b2b-mutate.py` → UNCOVERED=0 |
| 回歸 652 passed | **fact-verified** | `pytest -q tests/momentum/event_samples tests/momentum/core tests/momentum/Analysis/test_splitunify_{contract,derive}.py` → 652 passed |
| `split_events` 抽出後逐值不變 | **fact-verified** | `test_clusters_byte_identical_to_legacy_split_events`（`test_splitunify_derive.py:318-342`）`assert_frame_equal`；`tests/momentum/event_samples` 全綠 |
| M-SU-4/6/7 改後 fixture 可分辨 | **fact-verified** | 洞裡時間戳（`:175-199`）、重疊 plan（`:202-225`）、共桶權重 0.5（`:317-342`）三測皆獨立通過；對應 mutation rc=1 |
| `_index_as_ms` 與 `_as_ms` 門檻一致 | **fact-verified** | 兩支皆 `1e11`（`split_projection.py:87`；`split_preview.py:76` `_MS_MAGNITUDE_FLOOR`） |
| 10k 事件 `to_dict("records")` 效能 | **assumed（未測）** | brief 成本項；不擋 B2c |
| `event_level` 重複 `event_id` 時錯訊可讀性 | **assumed（未測）** | `validate="1:1"` 會 raise `MergeError`；brief 成本項 |

## 必答 1–7（明確立場）

### 1. 兩段式判定是否忠實於 A-2／C-4？

**是，逐行對齊。** 碼證：

- 空 test 先 raise、禁比較：`split_projection.py:201-203`（`test_rows.size == 0` → `missing_test_plan`），在 `test_start_ms` 取用（`:207`）**之前**。
- `test_start_ms` 取自 canonical 第一根 test row：`split_projection.py:207` `index_ms[test_rows[0]]`，不再減 embargo（對應 A-2「不再減 embargo」）。
- 第一段只作用 train 側：`split_projection.py:221` `if in_train and int(rec["label_end_ms"]) >= test_start_ms`——`in_test` 事件不走此分支（測試 `test_answer_window_not_applied_to_test_side_events`）。
- `>=` 保留：`split_projection.py:221`；`test_answer_window_boundary_is_ge_not_gt`（`:152-159`）釘死等號邊界。
- 順序：雙重成員 raise（`:215-219`）→ 答案窗 purge（`:220-223`）→ 集合成員（`:224-234`）；與 SPEC C-4 `:191-225` 一致。
- 舊式 `event_split.py:144` 仍為 `>` 且減 embargo——**僅 legacy `split_events` 路徑**；投影路徑依 A-2 刻意改寫，非漏改。

### 2. 有沒有第二份算術漏網？`_index_as_ms` vs `_as_ms` 算不算？

**切分／簇／summary 核心算術已單一化；ms 正規化為刻意雙路徑殘差，可接受但不理想。**

| 區塊 | 判定 |
|---|---|
| time-cluster | **唯一實作** `event_split.py:51-66` `build_time_clusters`；`split_events`（`:160-161`）與投影（`split_projection.py:238`）共同呼叫，無複製 |
| 桶寬 | **唯一** `time_cluster_bucket_ms`（`event_split.py:39-48`） |
| 簇權重 | **唯一** `_cluster_weight`（`:33-36`） |
| 集合成員 | 投影內 `cutoff in train_ms`／`test_ms`（`split_projection.py:213-214`）——與 C-4 集合語意一致，非第二套切分公式 |
| ms 守衛 | `_index_as_ms`（`split_projection.py:76-92`）vs `split_preview._as_ms`（`:54-81`）——**算兩支**，門檻同 `1e11`，職責不同（整段 index vs 單點）。**立場**：不算「切分算術重複」，但算**漂移風險點**——`M-SU-12` 只守投影側；改 `_as_ms` 門檻不會紅 derive 測試。建議 B3 抽共用常數＋交叉 mutation，**不擋 B2c**。 |

### 3. `build_event_keys` keyed join 是否擋得住 positional 錯位？

**夠，對本票 scope。** 碼證：

- `per_tf` 同 TF 重複 `event_id` 先 raise：`split_projection.py:123-128`（`test_build_event_keys_rejects_duplicate_per_tf_rows`）。
- merge 用 `on="event_id", validate="1:1"`：`:130-132`；`event_level` 若有重複 `event_id` 會 pandas `MergeError`（fail-closed，訊息偏內部——brief 成本項）。
- 反序 `per_tf` 對位測試：`:400-418` 證非 positional zip。
- `validate="1:1"` 對「缺 cutoff」已另以 `missing` 集合檢查（`:133-138`）。

**殘差**：`event_level` 重複 `event_id` 無專用訊息；多 TF 複合鍵仍列 `SU-RESID-2`，本票不解。

### 4. `_build_summary` 12 鍵語意對不對？

**對，與 legacy 公式一致；`insufficient_events_in_test` 語意變更是 SPEC 明示、單 symbol 路徑下等價。**

- 12 鍵齊：`test_summary_has_all_twelve_keys`（`:345-366`）。
- `avg_cluster_size`：`split_projection.py:284` `len(clusters)/max(1,n_clusters)` — 與 `event_split.py:170` 同分母（`nunique` cluster id）、同分子（行數）。
- `insufficient_events_in_test`：`:278` `[s for s in per_symbol_n if n_test < tier_min]` — **全域** `n_test`（投影後 test 總數），非逐 symbol 計數。舊實作 `event_split.py:149-151` 逐 symbol。差異在 R-1 多 symbol 前不觸發（`:192-196` fail-closed ⇒ 存活路徑恆 `n_symbols==1`）；與 SPEC Task 2.2 要點 6「改看投影後 test 數」一致。`_build_summary` 之 `tier_min_test_events` 預設 1、未暴露在 `derive` 簽名——符合 C-4「不讀 config」；**B3 接線須補參數**，屬後續票，不擋 B2c。
- `degraded`／`single_symbol` 恆亮：`:285` + 測試 `:363-366`；方向保守，符合 R2 D11。

### 5. `event_split.py` 抽出有沒有改到行為？`bucket` 算兩次？

**行為未變；雙次 `time_cluster_bucket_ms` 無不一致、無實質效能疑慮。**

- 抽出後 `split_events` 仍呼叫 `build_time_clusters(manifest, split_config.bucket_ms)`（`:160-161`）；舊內联邏輯已移除（`:156-159` 註解）。
- `bucket` 在 `:160` 與 `build_time_clusters` 內 `:59` 各算一次——同一函式、同一 `manifest`／`bucket_ms` 參數，結果恆等；僅多一次 O(1) 解析。
- 逐值證據：`test_clusters_byte_identical_to_legacy_split_events`；`tests/momentum/event_samples` 543+ 條回歸全綠。
- 混 TF／空 table：混 TF 仍 raise（`time_cluster_bucket_ms:44-47`）；空 manifest ⇒ 空 clusters（合法）。主委「未做抽出前後對照」之缺口已由 byte-identical 測試＋既有 event_samples 回歸覆蓋，**正面打：未發現行為漂移**。

### 6. mutation 表夠不夠？補充建議

現有 9 條 + C0 **足夠擋 B2b 核心契約**。改後 fixture（洞／重疊 plan／共桶）**確實可分辨**——本輪 mutation 全 rc=1 複驗。

**建議補充（B2c 前可選，非擋票）**：

| ID | 改壞哪一行 | 期望紅測試 |
|---|---|---|
| M-SU-14 | `split_projection.py:221` `>=` → `>` | `test_answer_window_boundary_is_ge_not_gt` |
| M-SU-15 | `:220-234` 對調：先做集合成員、後做答案窗 purge | `test_answer_window_crossing_train_event_is_purged` |
| M-SU-16 | `:207` `test_rows[0]` → `train_rows[0]` | `test_answer_window_crossing_train_event_is_purged` |
| M-SU-17 | `:130-132` 移除 `validate="1:1"` 且 `event_level` 注入重複 `event_id` | 新測試或 `test_build_event_keys_*` 擴充 |

**fixture 失效、真實資料仍紅？** 最危險是 **M-SU-4 類**（區間 vs 集合）——若只用連續 index fixture 會假綠；現 `test_membership_set_not_interval` 已用 post-trim 洞堵住。答案窗 purge（M-SU-13）在 `_basic_case` 的 `e_train_leak` 上失效即紅，與真實洩漏形態同構（train cutoff + `label_end_ms >= test_start_ms`），**不太會**出現「fixture 紅、真實綠」。

### 7. 可否進 B2c？

**可以。** 兩段式判定、keyed join、抽出一致性、mutation 自證與 652 回歸均成立；殘差（ms 雙路徑、tier_min 待 B3、10k 效能）不構成 B2c 阻斷。

---

## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對 brief 必答 1–7、主委兩項自查與 A-2 code fence 後無 P0/P1/P2 finding；可進 B2c（golden 五組）。

**碼證**: 兩段式 `split_projection.py:201-234` 對 `docs/GAP3_EVENT_SPEC_AMENDMENTS.md:80-87`；`build_event_keys` merge `split_projection.py:130-132`；抽出 `event_split.py:51-66,160-161`；pytest derive 24/24、mutation UNCOVERED=0、回歸 652 passed（命令見 §0 表）。

**來源摘要**: docs/GAP3_EVENT_SPEC_AMENDMENTS.md#fed0430bf187;docs/SPLITUNIFY_SPEC.md#3e39458b00e4;momentum/Analysis/event_samples/split_projection.py#ab39bc4bf68c;momentum/Analysis/event_samples/event_split.py#f9dbcfd3c9d6

[NON-BLOCKING] 信心度=High。核對依據＝必答 1（A-2 四條機械對照）／必答 3（keyed join 三層防護）／必答 5（byte-identical + 652 回歸）之碼證；主委「複製非抽出」已改為共同呼叫且測試證實；M-SU-4/6/7 fixture 升級後 mutation 全覆蓋。殘差：`_index_as_ms`／`_as_ms` 漂移（必答 2）、`tier_min` 待 B3（必答 4）、10k 效能（brief 成本）——均列為後續，不擋 B2c。

---

## Verdict：可進 B2c

B2b 投影實作忠實於 GAP3 A-2 兩段式判定與 SPEC C-3/C-4/C-5；`build_time_clusters` 抽出消除雙份簇算術；24 條測試 + 9 條 mutation 自證 + 652 回歸通過。B2c 開工時建議帶上 M-SU-14/15 與 G-5 答案窗 negative case；B3 接線再補 `tier_min_test_events` 參數與 ms 守衛共用常數。

---

ASSUMPTIONS_VERIFIED: derive 24/24；mutation UNCOVERED=0；回歸 652 passed；A-2 四條機械對照 split_projection.py:201-234；build_event_keys merge 1:1；clusters byte-identical；M-SU-4/6/7 fixture 設計 + mutation rc=1  
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` → 24 passed rc=0；`venv/bin/python handoffs/20260911-splitunify-b2b-mutate.py` → UNCOVERED=0 rc=0；`venv/bin/python -m pytest -q tests/momentum/event_samples tests/momentum/core tests/momentum/Analysis/test_splitunify_contract.py tests/momentum/Analysis/test_splitunify_derive.py` → 652 passed rc=0；`bash scripts/restore_golden_inventory.sh` → restored  
FAILURES_SEEN: none（首輪 derive 24 條曾見 2 failed，重跑 24/24 綠——疑前序 mutation 殘留，非可重現缺陷）  
SCOPE_CHANGES: none（唯讀 review）  
NUMERIC_OR_SCHEMA_IMPACT: none  
TEMP_CLEANUP: `/tmp/workdir` 不存在；`/tmp/claude-501` 保留  
HANDOFF_OUTPUT: handoffs/20260911-splitunify-b2-review-r1-composer.md

STATUS: DONE
