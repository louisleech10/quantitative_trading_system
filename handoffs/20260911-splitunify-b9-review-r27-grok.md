# SPLITUNIFY b9 — review-r27（Task 9.2b／B9C 審碼）— grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R27`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R27-BRIEF.md`  
**findings-round**: R27  
**brief-kind**: review  
**審查標的**: commit `a1e9680e`；current block＝`split_projection.py`（`_assert_event_level_side_consistency`／`_derive_single_symbol` 判側）／`pipeline.py` 步驟 0／`freeze_splitunify_golden.py`／三測試檔／golden v8  
**禁改碼／禁改 SPEC／禁改 TODO**（本檔只產 findings）。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 六路回歸 721 passed | **fact-verified（本家抽樣）** | scoped：`test_splitunify_derive.py`＋`test_splitunify_golden.py`＋`test_splitunify_wiring.py` → **129 passed**；全六路以 receipt `20260913T201758Z-…` 為權威（含 `test_m5_coordinate_truth_table`） |
| brief fact-verified: golden 換錨零位移＋`GOLDEN OK` | **fact-verified** | `venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`；v8 sha 與 `.v8.sha256` 相符 |
| brief fact-verified: SPEC v21 戳記 rc=0 | **fact-verified** | `reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → PASS；body `755f3d53…` |
| brief fact-verified: 五條破壞自證 | **未本家重跑原五條**；本家另做 3 組破壞（見必答 4） | 標「未經覆核原五條」 |
| assumed① fixture 遷移 | **成立** | 見必答 3 |
| assumed② 三道 AVE 可達性 | **成立（防禦＋接線足夠；錨點 AVE 公開路徑不可達）** | 見必答 3 |
| assumed③ 三條舊測語意遷移 | **成立** | 見必答 3＋必答 4 |
| assumed④ `label_end_ms.max()` | **部分成立（非阻擋）** | 見必答 3 |

---

## 必答 1 — 重跑 review-r26 sentinel（§B8）

### (1a)

**CLOSED** — `GROK-R26-P3-00`（r26 零 finding／可進 B9C 之前提）。本輪碼審確認 B9C 已落地；r26 所守之「兩層／無 live metadata 互斥」未被本 diff 推翻。

### (1b)

```text
bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md
# → 755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f

bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md
# → RECONCILE-STAMP PASS（codex,composer,grok）；body 755f3d53…

venv/bin/python -m pytest -q --tb=no \
  tests/momentum/Analysis/test_splitunify_derive.py \
  tests/momentum/Analysis/test_splitunify_golden.py \
  tests/momentum/event_samples/test_splitunify_wiring.py
# → 129 passed
```

觀測：body／戳記與 r26 一致；B9C 程式行為與 r26「可進 9.2b」立場相符。

---

## 必答 2 — `Task 9.2b` 六要點與四不可做（對照碼）

### (2a)

| # | 條目 | 判定 | 碼證 |
|---|------|------|------|
| 1 | 步驟 0：`EventSamplePipeline.run` 於 derive 前呼叫 `validate_split_pair_integrity`；`ts` 為 naive datetime64 | **已落地** | `pipeline.py:772-789` |
| 2 | 三段式＋界外 raise（非第四分支）；`train_last_ms`；空 train raise；時間重疊 raise | **已落地** | `split_projection.py:639-725` |
| 3 | 事件級廣播；`feature_cutoff_ms` 不參與 `split_label` | **已落地** | `:716-756`；註解明禁 |
| 4 | 答案窗 purge 按事件側一次決定並廣播 | **已落地** | `:727-737` 用 `event_state` 後廣播 |
| 5 | `(3.2)` 同側分組 → `AlignmentViolationError` | **已落地** | `_assert_event_level_side_consistency:412-421`；呼叫於 `:760` |
| 6 | 跨表互斥 | **已落地** | 同 helper `:422-430` |
| — | 不可做① 不得以 cutoff 定側 | **已遵守** | mut2 改回 cutoff → 多測轉紅 |
| — | 不可做② 界外非第四分支 | **已遵守** | `:703-714` 獨立 raise；`_side_of` 僅三態 |
| — | 不可做③ 不得在 (3.2) 前保留 per-cutoff | **已遵守** | 先算 `event_state` 再廣播 |
| — | 不可做④ 不得在 derive 內呼叫 validate | **已遵守** | validate 只在 `pipeline.py:784` |

前置／golden：`bnd_shift`（`freeze:116-121`）、decision-oracle（`:158-188`）、`g1_membership_v9`／`g3b_oracle_v9`（`:222-223`）、v8 `--write` 拒寫＋sha 校驗（`:415-427`）皆在。

### (2b)

程式要點無未落地項。文件落後見 findings（不列入「未落地實作要點」）。

---

## 必答 3 — 四條 assumed

### (3a)

① **fixture 遷移 → 成立**。事件級廣播後，同事件各列結構上必同側；原「兩 cutoff 分落兩段餵 `derive_*`」造不出異側。SPEC §V `:270` 反例逐字「**直接構造 `assignments`**」⇒ 改打 `_assert_event_level_side_consistency` 正確。node id 一字未改；xfail 已解除；`test_event_level_anchor_broadcasts_side_to_all_feature_tf` 正面覆蓋原輸入形狀。**不是**刪測換綠。TODO「解除 xfail」與 SPEC 反例形狀不一致時，應以 SPEC §V 為準（本處置已對齊 SPEC）；TODO 驗證欄可補一句「fixture 依 §V 形狀」以免後人以為要恢復旧餵法。

② **三道 AVE 可達性 → 成立（附條件）**。實跑：

| 閘 | 公開 `derive_*` 可達？ | 觀測 |
|----|------------------------|------|
| 同側分組 | **否**（廣播後結構不可達） | 只能直接呼叫 helper；`test_opposite_sides_*`／`test_multi_feature_tf_opposite_*` |
| 跨表互斥 | **否**（同上） | `test_purged_and_assignments_event_id_disjoint` |
| 錨點 `decision_at_ms` 不唯一 | **否** | 重複 `event_id` 先被 `man_dupes`（`:563-566`）以裸 `ValueError` 擋下；AVE 錨點閘（`:690-697`）在公開路徑不可達 |

「不可達防禦碼 ＋ 接線測試」對 (3.2) **足夠**：SPEC 反例形狀本就要可單獨呼叫的入口；`test_side_consistency_check_is_wired_into_derive`／`…_runs_before_dataframes_are_built` 釘住呼叫點（mut1 刪呼叫 → wiring 紅、直接 helper 測仍綠——正是 R18 A1 同型）。錨點 AVE 屬雙重防禦，現況可接受，不另開 finding。

③ **三條舊測語意遷移 → 成立**。

| 測試 | 新契約斷言 | 鑑別力 |
|------|------------|--------|
| `test_membership_set_not_interval` | 洞裡 ⇒ **train**（非 purged） | 加回集合成員「不在集合⇒purged」會紅 |
| `test_dual_membership_raises_not_silent_pick` | 時間面重疊 ⇒ raise | 對應新閘 `test_start_ms <= train_last_ms` |
| `test_unmatched_timestamp_is_purged_not_train` | 界內非網格點 ⇒ train | 加回「不在集合⇒purged」會紅 |

三者皆保留 node、反轉斷言並具名，非刪測換綠。

④ **`label_end_ms.max()` → 部分成立（非阻擋）**。同事件同值時 `max` 退化為該值（正確）。實跑同事件兩列不同 `label_end_ms`（1h 不跨、4h 跨 test）⇒ **整事件 purged、不 raise**——靜默吞不一致，但對洩漏偏保守。生產 `build_event_keys` 自 `event_level` 合併，同事件應同值。建議（可選，不擋 9.3）：比照 `decision_at_ms` 加 `nunique>1` fail-closed。

### (3b)

僅 ④ 有可選修法（非最小閉合集合）：在答案窗段前對 `event_keys.groupby("event_id")["label_end_ms"].nunique()>1` raise。①–③ 不需改碼。

---

## 必答 4 — 空殼破壞驗（至少兩處）

### (4a)

挑兩處改壞並實跑（皆已還原；`git checkout --` 確認乾淨）：

### (4b)

**MUTATION 1** — 刪 `split_projection.py:760` 之 `_assert_event_level_side_consistency(...)` 呼叫：

```text
# 觀測
test_side_consistency_check_is_wired_into_derive → FAILED（「沒有呼叫同側／跨表互斥檢查」）
test_opposite_sides_raise_alignment_violation → PASSED（直接打 helper）
test_multi_feature_tf_opposite_sides_must_fail_closed → PASSED
test_event_level_anchor_broadcasts_side_to_all_feature_tf → PASSED
```

⇒ 接線測有鑑別力；僅 helper 測會漏接線省略（主委自證之 A1 同型，已補）。

**MUTATION 2** — 廣播迴圈改回 per-cutoff `_side_of(int(rec["feature_cutoff_ms"]))`：

```text
test_event_level_anchor_broadcasts_side_to_all_feature_tf → FAILED（AlignmentViolationError 異側 e_bc）
test_gap_band_event_is_purged_not_train → FAILED（異側）
test_real_derive_never_produces_straddling_event → FAILED
```

⇒ 事件級錨定反例有鑑別力；非空殼。

**附加 MUTATION 3** — 空 train 之 raise 改 `pass`：

```text
test_empty_train_rows_is_fail_closed_not_skipped → FAILED（IndexError，非預期 ValueError）
```

⇒ 仍紅（有鑑別力）。

---

## 必答 5 — 契約面強制掃描（自立詞表）

### (5a)

**本家詞表**（刻意不以 r26 之 metadata／三層／整鏈為唯一依據；本輪契約＝側別錨定）：

| 類 | 詞／結構 |
|----|----------|
| 舊判側 | `集合成員判定`、`feature_cutoff_ms ∈`、`cutoff in train_ms`、`per-cutoff`、`以 feature_cutoff`、`逐列取.*cutoff`、`現況碼證.*命中數為 0`、`:530-553` |
| 新錨定 | `decision_at_ms`、`train_last_ms`、`三段式`、`不參與.*split_label`、`事件級錨` |
| 殘留狀態 | `尚未關閉者`、`9.2b 尚未`、`blocked-by:Task 9.2b` |
| 舊 Task 施工 | `Task 2.2` 內未標 SUPERSEDED 之 cutoff／集合成員祈使 |

**命令**：

```text
# live SPEC = 1..HISTORY-BEGIN（:1-336）；TODO 全檔
grep -nE '集合成員判定|feature_cutoff_ms ∈|cutoff in train_ms|per-cutoff|現況碼證.*命中數為 0|:530-553|以 feature_cutoff|尚未關閉者|9.2b 尚未|blocked-by:Task 9.2b' \
  docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md

grep -c 'decision_at_ms' momentum/Analysis/event_samples/split_projection.py
# → 12（非 0）
```

**逐段結論**（與「側別由事件級 `decision_at_ms` 錨定、`feature_cutoff_ms` 不參與 `split_label`」互斥？）：

| 段 | 互斥？ | 說明 |
|----|--------|------|
| SPEC `:46` (3.1) | **無** | 權威契約，與碼一致 |
| SPEC `:167` (G-4c)「oracle **目前**也以 cutoff 判側」 | **是（時態）** | oracle 已 decision-anchor 重寫；「目前」過期 → 併入 P2-01 |
| SPEC `:216-217` §P Task 9.2b「現況碼證」命中 0／`:530-553` | **是** | 實作已改 → P2-01 |
| SPEC `:231` 不可做 | **無** | 禁止句，正確 |
| SPEC `:261`「現行碼會給出 1h=test／4h=purged」 | **是（時態）** | 9.2b **前**行為 → P2-01 |
| SPEC `:327`／TODO `:891` `SU-RESID-2` 仍列 9.2b 未關 | **是** | 9.2b 已落地 → **P1-02** |
| TODO Task 2.2 `:209`／`:217`／`:236` 集合成員／cutoff 祈使**無** SUPERSEDED | **是** | 同型 R21 E2 → **P1-01** |
| TODO Task 9.2b `:592-634` | **無** | 與碼一致 |
| 碼 docstring `split_projection.py:462-464` | **是（註解）** | 函式已改、docstring 仍寫集合成員 → 併入 P2-01 |

### (5b)

**P1-01 可貼字面**（Task 2.2 實作要點 1／2／4 旁，比照 `:225` 形態）：

```markdown
🔴 **SUPERSEDED BY `Task 9.2b`（B9C；R27）**：側別改由事件級 `decision_at_ms` 三段式錨定；
`feature_cutoff_ms` **不參與** `split_label`；集合成員判定整段作廢。刪節線保留供追溯，
**不得**據以實作——依本段舊文會把已完成的事件級錨定**回退**為 per-cutoff。
```

**P1-02 可貼字面**（TODO `:891`／SPEC `:327` 同步）：

```markdown
🔴 **尚未關閉者**＝下游消費面（`Task 9.3` 之九處）（**v22 更正，R27**：側別錨定已由批次 B9C／`Task 9.2b` 關閉——
`decision_at_ms` 錨定＋廣播＋(3.2) 同側／跨表互斥已落地）。**為何現在不做**：`blocked-by:Task 9.3 尚未實作`。
~~與側別錨定（Task 9.2b）~~／~~blocked-by:Task 9.2b／9.3 尚未實作~~
```

**P2-01 可貼字面**見該 finding 正文。

---

## 必答 6 — 可否進 `Task 9.3`（B9D）

### (6a)

**不可以（先修文件 P1）**。程式六要點＋四不可做已落地，無程式 BLOCKING；但 **P1-01／P1-02** 會讓後續 agent 依 live 舊段回退判側或誤等已完成之 9.2b——同型 R21／R22／R25。最小閉合後再進 B9D。

### (6b)

最小閉合集合：

1. `GROK-R27-P1-01` — Task 2.2 集合成員／cutoff 祈使標 SUPERSEDED→9.2b  
2. `GROK-R27-P1-02` — `SU-RESID-2`（TODO§E＋SPEC§N）去掉「9.2b 未關」、blocked-by 只留 9.3  

P2-01 可同批或下一 doc 輪。已檢查：129 passed、`GOLDEN OK`、mut1/2/3、四 assumed、多 symbol 仍走同一 `_derive_single_symbol`（`:850`）、NaN `decision_at_ms` 由 `assert_epoch_ms_array` fail-closed、`pipeline.run` 僅單 plan（symbols 廣播 `train_plan.symbol` 與此 API 相符；Mapping 多標的不經此 run）。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：P1-01／P1-02／P2-01（文件 vs 碼）。程式內無互斥。  
2. 漏項：TODO 具名 `test_coordinate_truth_table_four_cases` 不存在；等價覆蓋＝`test_m5_coordinate_truth_table`（receipt 721 內）——**不另開 finding**（node 名差，功能在）。`expected_side` 屬 Task 9.5，本批未交不重開。  
3. 不可測：無。  
4. 可疑 quant：無新開；換錨語意依 (G-4a)。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：`pipeline.run` 仍單 plan；derive Mapping 無第二份判側。  
9. 測試品質：接線＋反例有鑑別力（必答 4）；`g1_membership==g1_membership_v9`（皆含 `bnd_shift`），舊錨在 v8.json——(G-4d)(ii)「不改既有鍵」字面未守、精神由 v8 承接，屬 Task 9.5／誠實邊界，**不擋 9.3**。  
10. Agent 可執行：P1 舊段會誤導。  
11. 必要性／短命工：無本輪新增短命工。

---

## 攻擊面補答（brief 表「我沒查」）

| 面向 | 本家結論 |
|------|----------|
| 第四種輸入（NaN decision） | `assert_epoch_ms_array` fail-closed（含 NaN／inf）；**不**靜默落側 |
| 多 symbol 廣播 | Mapping 分支逐 symbol 呼叫同一 `_derive_single_symbol`（`:850`）；無第二份判側 |
| 步驟 0 多標的 symbols | `pipeline.run` API 僅單 `train_plan`；廣播 `train_plan.symbol` 正確。多標的須呼叫端自備 full symbols＋自行 validate（TODO 已寫） |
| v8 sha 雙改繞過 | `--write` 校驗可被「同時改 `.v8.json`＋`.sha256`」繞過；真正 write-once／SPEC 外錨屬 **Task 9.5**，不重開 |
| g1 與 g1_v9 同值 | 是兩份相同新真相；舊真相只在 v8。手推錨點改指含 `bnd_shift` 之 g1 |
| 空洞舊測 | 三條遷移測有鑑別力；未發現「斷言仍在但無義」之第三例 |
| DatetimeIndex 路徑 | 本輪未另造 DatetimeIndex fixture；`epoch_ms_from_index` 在 pipeline 步驟 0 已用。標「未本家覆核 DatetimeIndex 專徑」 |

---

## GROK-R27-P1-01

**斷言**: `docs/SPLITUNIFY_TODO.md` `Task 2.2` 實作要點仍以 live 祈使句要求「`feature_cutoff_ms ∈ feature_index[…]` 集合成員判定定側／不在集合⇒purged」，且該段**未**標 SUPERSEDED；與已落地之 `Task 9.2b` 事件級錨定互斥，後續 agent 依 Task 2.2 會回退判側。

**碼證**: `awk 'NR>=208 && NR<=236' docs/SPLITUNIFY_TODO.md | grep -E '集合成員|feature_cutoff_ms ∈|SUPERSEDED'` → `:209`／`:217`／`:236` 無 SUPERSEDED；僅 `:225`（selected_timeframe）有。本輪 mut2 依該舊文改回 per-cutoff → `test_event_level_anchor_broadcasts_side_to_all_feature_tf` 轉紅。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:217
MUTATION: 依 Task 2.2:217 把廣播迴圈改回 `_side_of(int(rec["feature_cutoff_ms"]))`（本輪 mut2）→ `test_event_level_anchor_broadcasts_side_to_all_feature_tf` 轉紅（AlignmentViolationError 異側）

**來源摘要**: docs/SPLITUNIFY_TODO.md#7a18de5a95ff; momentum/Analysis/event_samples/split_projection.py#5e72d9070c7e

[BLOCKING] 信心度=High。同型 R21 `CODEX-R21-P1-02`（契約改後舊 Task 段未標 superseded）。**修法**：在 Task 2.2 要點 1／2／4（`:209`／`:217-218`／`:235-236`）旁加 SUPERSEDED→`Task 9.2b` 註（字面見必答 5b）；刪節線保留舊集合成員句。可行性：與 `:225`／`:242` 既有 SUPERSEDED 形態相同，不改碼。

---

## GROK-R27-P1-02

**斷言**: `SU-RESID-2`（TODO §E `:891` 與 SPEC §N `:327`）仍把「側別錨定（`Task 9.2b`）」列為**尚未關閉**且 `blocked-by:Task 9.2b／9.3 尚未實作`；B9C 落地後該半句為假，會誤阻 B9D 或讓狀態帳與碼不一致。

**碼證**: `grep -n '尚未關閉者\|blocked-by:Task 9.2b' docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.D-002.md` → TODO:891 與 SPEC:327 皆仍列 9.2b；`grep -c decision_at_ms momentum/Analysis/event_samples/split_projection.py` → 12（非 0）。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:891
MUTATION: 保持 `blocked-by:Task 9.2b／9.3 尚未實作` 字面不變 → 開工檢核若 grep「9.2b 尚未」仍命中，即使 129 測全綠且 `decision_at_ms` 已落地

**來源摘要**: docs/SPLITUNIFY_TODO.md#7a18de5a95ff; docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68

[BLOCKING] 信心度=High。同型 R22「部分關閉」帳面未隨批次前進。**修法**：兩檔同步——尚未關閉者只留 `Task 9.3`；blocked-by 改 `Task 9.3 尚未實作`；9.2b 半句刪節保留（字面見必答 5b）。可行性：只改殘留列狀態句，不動 C5 register／mutation 條數。

---

## GROK-R27-P2-01

**斷言**: SPEC §P `Task 9.2b`「現況碼證」（`:216-217`）、§V `:261`「現行碼會給出…」、§G (G-4c) `:167`「oracle **目前**也以 cutoff 判側」，以及 `_derive_single_symbol` docstring `:462-464`，仍以 9.2b **前**碼態為現況／現行，與 commit `a1e9680e` 互斥。

**碼證**: `grep -c decision_at_ms momentum/Analysis/event_samples/split_projection.py` → 12（非 0）；`:720-725` `_side_of` 只讀 `decision_ms`；`freeze_splitunify_golden.py:176-187` oracle 已 decision-anchor；docstring `:462-464` 仍寫 `feature_cutoff_ms ∈ …` 定側。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68; momentum/Analysis/event_samples/split_projection.py#5e72d9070c7e

doc-literal-only；信心度=High。行為已由測鎖定。**修法**：①`:216-217` 改標「9.2b 前快照／已過期」＋現行錨點／三段式／廣播碼證；②`:261` 改「9.2b 落地後正例；9.2b 前才會 1h=test／4h=purged」；③`:167`「目前」改「9.2b 前」；④docstring 兩段式改寫為事件級三段式＋廣播（或標 SUPERSEDED）。不單獨阻擋 B9D（併 P1 同批最省）。

---

VERDICT: blocked
BLOCKED-BY: GROK-R27-P1-01,GROK-R27-P1-02
CLOSED: GROK-R26-P3-00

ASSUMPTIONS_VERIFIED: body 755f3d53…；stamps rc=0；129 pytest；GOLDEN OK；四 assumed 逐條；mut1/2/3；詞表掃描含 Task 2.2／SU-RESID-2
TESTS_RUN: `pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/event_samples/test_splitunify_wiring.py -q` → 129 passed；`scripts/freeze_splitunify_golden.py` → GOLDEN OK；mut1 wiring 紅／mut2 錨定紅／mut3 空 train 紅（皆還原）
FAILURES_SEEN: 並行 worktree 曾見 `test_membership_set_not_interval` 被改成 `assert not purged.empty`（非本家）；已 `git checkout --` 還原後 3 passed
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r27-grok.md

STATUS: DONE
