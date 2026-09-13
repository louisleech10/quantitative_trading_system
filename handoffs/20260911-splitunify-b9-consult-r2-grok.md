# SPLITUNIFY b9 — 未 commit 生產碼保留或回退（consult R2 / grok）

task-id: `20260911-SPLITUNIFY-B9-CONSULT-R2`  
family: grok  
findings-round: R2  
brief-kind: consult  
brief: `handoffs/20260911-SPLITUNIFY-B9-CONSULT-R2-BRIEF.md`  
read-only：禁改碼；標的＝四檔 dirty diff ＋ SPEC current block。

---

## §0 挑戰前提

| # | brief 陳述 | 標籤 | grok 重判 | 證據 |
|---|---|---|---|---|
| F1 | 無 impl token；SPEC 零 RECONCILE-STAMP | fact-verified | **成立** | `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → 三家皆缺 APPROVED；body sha256 前綴 `06b2d4cb…` |
| F2 | 兩檔測 **2 failed／91 passed** | fact-verified | **成立** | `python -m pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py -q` → 同數；紅者皆在 derive 檔 |
| F3 | `pipeline.py` 無 `validate_split_pair_integrity`（O4 未落地） | fact-verified | **成立** | `grep -c validate_split_pair_integrity momentum/Analysis/event_samples/pipeline.py` → **0**；全 repo 僅 `ic_split_adapter.py` |
| F4 | TODO 無 `Task 9.1`–`9.5` 任務段 | fact-verified | **成立** | `grep -nE '^#+ *Task ' docs/SPLITUNIFY_TODO.md` 只到 `Task 4.1` |
| F5 | `splitunify_golden.v8.json` 不存在；`V8_BASELINE_SHA256=` 無 64-hex | fact-verified | **成立** | `ls tests/golden/splitunify/` 無 v8；`grep V8_BASELINE_SHA256` 只命中要求文字 |
| A1 | 這批碼對 v12 以前寫、與 v13 O1／O3／O4 **語意不相容** | assumed | **部分否證** | **O1**：本批未碰 `build_split_unify_disclosure`／metadata；v13 已把 metadata 值相等 ASSERT 移入 `SU-RESID-9A-UI` ⇒ 對本批為 **no-op／相容**。**O3／O4**：本批根本未做 `Task 9.2b`（側別仍 `feature_cutoff_ms`，`split_projection.py:587-589`）⇒ 是 **缺段**，不是與 O3／O4 字面互斥。較準確：對齊 **9.1＋9.2＋部分 9.2a**，缺 9.2b／O4／`n_event_tf_rows`。 |
| A2 | 回退成本上界＝重寫這 4 檔；無他檔依賴 | assumed | **部分否證** | `build_event_keys` 生產呼叫點＝`pipeline.py:755`（已改 unpack）＋測試；另 **staged** `handoffs/20260911-splitunify-b9-probe-multitf.py` 已改 `out, _discarded = build_event_keys(...)`。回退 4 檔若不同步 probe → probe 對 HEAD 簽章會壞。`handoffs/20260911-splitunify-b2b-mutate.py` 只字面提及函式名、不呼叫。 |

## 被當成事實的未驗證假設（§0）

- 「與 O1／O3／O4 三處修訂不相容」→ **assumption，已收窄**：O1 相容；O3／O4＝未實作缺口。
- 「回退只動 4 檔」→ **assumption，已否證邊界**：至少加 staged probe 1 hunk。

---

## 攻擊面補查（brief「我沒查」）

### `build_event_keys` 全 repo 呼叫點

| 路徑 | 形態 | 回退／KEEP 影響 |
|---|---|---|
| `momentum/.../split_projection.py:259` | 定義（新簽章 `Tuple[DataFrame, Dict]`） | 本體 |
| `momentum/.../pipeline.py:755` | 生產 unpack | 與定義耦合 |
| `tests/.../test_splitunify_derive.py` | 多處 unpack | 與定義耦合 |
| `tests/.../test_splitunify_wiring.py` | 經 pipeline 間接 | 閘／summary |
| `handoffs/20260911-splitunify-b9-probe-multitf.py:47` | staged unpack | **A2 否證點** |
| `handoffs/20260911-splitunify-b2b-mutate.py` | 字串／mutation 名 | 不呼叫 |
| `api/` | 0 命中 | 無 |

### `feature_timeframe` 下游／register

命中乙類 register：`C5-19`／`C5-20`／`C5-21`（本批已動 producer／assignments／purged）。丙類 `C5-24` `pattern_bridge`：`set_index("event_id")["split_label"]` 在同 eid 異側時會得 Series；現況單測仍綠（單列 fixture）。`R-4`：無 production caller。本批 **未**改 `pattern_bridge`。

### 兩條紅測分類（詳必答 3）

見下。

### 既有 golden

`git diff --stat -- tests/golden/splitunify/` 空；11 頂層鍵未因本批移動。

---

## 必答

### (1a) 單一裁定

**`REVERT`**

### (1b) 裁錯時的可執行觀測

若裁 `REVERT` 為錯（其實應 KEEP），觀測＝主委在 stamp＋TODO 就緒後重寫 9.1／9.2 時，會重做出與現行 dirty **同形**之 producer 簽章／三參數閘／`feature_timeframe` 欄，且對照本輪 diff 無本質差異：

```bash
git checkout -- momentum/Analysis/event_samples/split_projection.py \
  momentum/Analysis/event_samples/pipeline.py \
  tests/momentum/Analysis/test_splitunify_derive.py \
  tests/momentum/event_samples/test_splitunify_wiring.py
# 之後若 Task 9.1–9.2a 重做完成，對上述四檔再 diff：
git diff --stat -- momentum/Analysis/event_samples/split_projection.py \
  momentum/Analysis/event_samples/pipeline.py \
  tests/momentum/Analysis/test_splitunify_derive.py \
  tests/momentum/event_samples/test_splitunify_wiring.py
```

期望（裁錯時）：重做後 diff 相對「本輪曾存在之 dirty」在 `build_event_keys` 回傳元組、三參數閘、`feature_timeframe` 欄三處 **同形重現**（可 `git stash` 本輪 diff 作對照）。若重做後語意大幅不同 ⇒ 本輪 `REVERT` 站得住。

### (2a) PARTIAL 具名（本裁定非 PARTIAL ⇒ N/A）

N/A（見 2b）。

### (2b) 為何不選 PARTIAL

簽章／閘／複合鍵欄／derive 唯一性 guard／測試 unpack **同一原子契約**：

- 只留 `Tuple` 回傳、不改 `pipeline.py:755` unpack ⇒ `TypeError`
- 只加 `feature_timeframe`、不改 `event_keys` 唯一性閘（`:486-496`）⇒ 合法多 TF 批被舊「event_id 重複」擋死
- 只改閘為三者、不改 producer 全量 merge ⇒ `MergeError`（舊 `validate="1:1"`）

逐 hunk 切分會留下不一致中間態；修復成本 ≥ 整批回退後依 v13 重做。故不選 `PARTIAL`。不選 `KEEP`：現況 **紅**、缺 `Task 9.2b`／O4、無 stamp／token——KEEP 等於把未蓋章半成品當工作區既成事實（與 HANDOFF「無 token 無戳記不可計入進度」一致）。

### (3a) 兩條紅測：過時 vs 實作錯

| 測試 | 判定 | 理由 |
|---|---|---|
| `test_duplicate_event_id_is_fail_closed` | **測試過時（斷言字面）** | fixture 同 eid＋同預設 `feature_timeframe=1h` 仍觸發 fail-closed；訊息改為「`(event_id, feature_timeframe) 複合鍵重複`」。`match="event_id 重複"` 對不上。行為仍對；授權＝§V／`Task 9.2a` 複合鍵唯一（現行條文，非歷史段）。 |
| `test_multi_feature_tf_opposite_sides_must_fail_closed` | **測試 fixture 錯 ＋ 目標行為尚未實作** | `_manifest(keys)` 把兩列同 eid 寫進事件級 `manifest.table` ⇒ 先被 `manifest.table 之 event_id 重複` 擋住（實跑 Input 即此）。`(3.2)` 異側 `AlignmentViolationError` **碼上不存在**（無同側檢查實作）；側別仍 `feature_cutoff_ms`（`:587-589`）。故：現紅≠實作把異側放行；亦≠單純「測試過時可改 regex 即綠」。 |

### (3b) 可證偽觀測

- 若 (3a) 對 duplicate 判「測試過時」為錯（其實是實作錯）：把 `match` 改成接受「複合鍵重複」後仍應 **raise**；若改後 **不再 raise** ⇒ 實作錯、本判翻盤。  
  `venv/bin/python -m pytest tests/momentum/Analysis/test_splitunify_derive.py::test_duplicate_event_id_is_fail_closed -q`（改 match 後）期望仍 passed。
- 若對 opposite 判「fixture＋未實作」為錯（其實已實作異側閘）：用 **事件級唯一** manifest（`_manifest(keys.drop_duplicates("event_id"))`）＋異 cutoff 兩列 keys 重跑；期望訊息命中 `同一事件|異側|同側|AlignmentViolation`。現行期望＝仍 **不**命中該語意（或走 cutoff 異側而靜默組 assignments）⇒ 支持「9.2b 未落地」。

### (4a) Task 9.1–9.5 可貼進 TODO 的驗收命令字面

**Task 9.1**

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_splitunify_derive.py -q --tb=short \
  -k 'build_event_keys_returns_discarded_counts or build_event_keys_discarded_is_empty_dict_for_single_tf or build_event_keys_picks_selected_timeframe_only or summary_carries_producer_discarded_verbatim or summary_discarded_defaults_to_empty_dict or summary_has_all_thirteen_keys'
venv/bin/python -m pytest tests/momentum/event_samples/test_splitunify_wiring.py::test_splitunify_wiring_selected_timeframe_none_goes_projection -q --tb=short
# mutation 轉紅判準（人工／harness）：拿掉 summary 鍵 discarded_rows_by_feature_tf ⇒ 上列 summary_* 紅（對 M-SU-D2-01／02）
```

**Task 9.2**

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_splitunify_derive.py::test_full_scan_emits_one_row_per_feature_tf -q --tb=short
venv/bin/python -m pytest tests/momentum/event_samples/test_splitunify_wiring.py -q --tb=short \
  -k 'selected_timeframe_none_goes_projection or partial_boundary_is_fail_closed'
# mutation：恢復四參數閘或 merge validate="1:1" ⇒ test_full_scan_* 與 selected_timeframe_none_* 紅（M-SU-D2-20／21／23）；冒充 feature_timeframe⇐event_level.timeframe ⇒ 值斷言紅（M-SU-D2-26）
```

**Task 9.2a**

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_splitunify_derive.py -q --tb=short \
  -k 'full_scan_emits_one_row_per_feature_tf or duplicate_event_id_is_fail_closed or build_event_keys_rejects_duplicate_per_tf'
# 另須具名：assignments／purged 欄含 feature_timeframe 且複合鍵唯一之測試函式（落地後以該函式名替換本行 -k）
# mutation：同側檢查移到複合鍵 guard 之前 ⇒ guard 先後測試紅（M-SU-D2-25）
```

**Task 9.2b**

```bash
venv/bin/python -m pytest tests/momentum/Analysis/test_splitunify_derive.py -q --tb=short \
  -k 'multi_feature_tf_opposite_sides or decision_at_ms or validate_split_pair'
# 落地後函式名須對齊 §V：異側 AlignmentViolation；進入 derive 前已呼叫 validate_split_pair_integrity；四案座標真值表
# mutation：判側改回 feature_cutoff_ms ⇒ 事件級錨定反例紅（M-SU-D2-22）；略過 validator ⇒ M-SU-D2-30 應紅測試紅
```

**Task 9.3**

```bash
venv/bin/python -m pytest tests/momentum/event_samples/test_feature_materialization.py -q --tb=short -k 'event_level or multi_tf or n_input'
venv/bin/python -m pytest tests/momentum/event_samples/test_tables.py -q --tb=short -k 'loc_eid or assignments'
venv/bin/python -m pytest tests/momentum/event_samples/test_pattern_bridge.py -q --tb=short -k 'split_label or unique'
# 其餘反向 mutation 具名檔見 §V Task 9.3 列（counterexample／candidate_ledger／dedupe／ic_feed／byEventId）；缺檔不得宣稱閉合
```

**Task 9.4**（與 9.3 常並行，驗收獨立列出）

```bash
venv/bin/python -m pytest -q --tb=short -k 'n_test_events or n_test_samples or insufficient_events_in_test'
# mutation：baseline 保留舊鍵 n_test ⇒ exact-key 斷言紅（M-SU-D2-32）；只輸出單一 n_test ⇒ M-SU-D2-31 紅
```

**Task 9.5**

```bash
venv/bin/python scripts/freeze_splitunify_golden.py
# 期望：GOLDEN OK；既有 splitunify_golden.json 11 頂層鍵逐值不變；平行組若新增則 g1／g3b 擴維路徑獨測
# mutation：覆蓋單標的 g5 或未擴 g1 ⇒ M-SU-D2-16／17 應紅；缺 V8_BASELINE_SHA256=64-hex 錨點 ⇒ M-SU-D2-34 應紅（凍結當下）
```

### (4b) 依賴順序

1. **序列**：`9.1` → `9.2` → `9.2a` → `9.2b`（9.1 揭露契約先於全量；9.2 全量 producer 先於 schema／側別；9.2a 複合鍵欄與 guard 先於 9.2b 同側／跨表互斥——鍵不唯一時同側無定義）。  
2. **`9.3` 與 `9.4`**：皆依賴 `9.2a` 輸出形狀；二者可 **並行**（消費面 vs 計數／baseline）。`9.3` 動工前須再掃 register（SPEC 義務）。  
3. **`9.5`**：必須在 `9.2b`（換錨／oracle／expected_side）與單 TF 回歸穩定 **之後**；否則 golden 重凍會把未定側別寫死。可與 9.3／9.4 尾段部分重疊，但 **寫入 v8 baseline／§V 錨點**須最後一次變更集。

### (5a) 對 v13 SPEC stamp：APPROVED 或 REJECTED

**APPROVED**（以現行 v13 活文＋R12 停輪判準）。  
不開 REJECTED 阻擋條：`V8_BASELINE_SHA256` 錨點與 v8 檔明文「凍結當下才生效」；TODO 缺 Task 段是 **TODO 產物缺口**（必答 4／6 處理），不是 SPEC body 內一次修訂可關且應擋 stamp 的互斥。stamp 標的＝`docs/SPLITUNIFY_SPEC.D-002.md` body `06b2d4cb…`。

### (5b) 最可能實作期變紅的條文＋處置

**具名**：`Task 9.2b` 改法①＋§V 前置——`EventSamplePipeline.run` 在 `derive_event_split_from_plans` **之前**以 `feature_index` 作 `ts`、`train_plan.symbol` 廣播作 `symbols` 呼叫 `validate_split_pair_integrity`（O4），並維持只讀 `row_index_local`（D-001-C2 (4.10)）。  
變紅時：**先改碼**對齊具名落點與四案真值表；僅當實作證明落點與 D-001 再衝突時才開規格修訂（禁默默改回 derive 內呼叫）。

### (6a) 可以進 `Task 9.1` 實作嗎？

**不可以（現在）**——有 BLOCKING 須先閉。

### (6b) 最小閉合集合

1. **`REVERT` 本批四檔 dirty**（另：staged probe 之 tuple unpack hunk 一併還原，或回退後重寫前再改）——消未蓋章半成品。  
2. **stamp 輪**對 `docs/SPLITUNIFY_SPEC.D-002.md`（sha `06b2d4cb…`）三家 `RECONCILE-STAMP` APPROVED。  
3. **寫入** `docs/SPLITUNIFY_TODO.md` 之 `Task 9.1`–`9.5`（含本輪 4a 驗收命令字面）並經 stamp／既定程序。  

查過才敢列「僅此三項」：`reconcile_stamps_check` 紅；TODO 無 Task 9.x；dirty 兩測紅且 O4 命中 0；無 OPEN 債以外的程式依賴阻塞 9.1 本身（`debt_ledger --has-open` 本輪派工後預期非 0，銷帳後不擋）。

---

## 11 類必查（对本裁定／diff；無則「無」）

1. 矛盾／互斥：無新 SPEC 互斥 finding（A1 已收窄）  
2. 漏項：WIP 缺 9.2b／O4（併入裁定 REVERT，不另開 P0）  
3. 不可測驗收：TODO 缺 Task 段（併入 6b）  
4. 可疑 quant：無（本輪非規格深審）  
5. 過度工程：無  
6. OOM：無  
7. Cache：無  
8. API／相容：`build_event_keys` 簽章破壞面已盤點  
9. 測試品質：兩紅測分類見 3a  
10. Agent 可執行性：4a 命令可貼  
11. 必要性／短命工：KEEP 半成品＝短命／違規進度；故 REVERT  

---

## Findings

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding；裁定與六組必答已用 diff／pytest／grep 閉合，無需另列 P0–P2 缺陷項。

**碼證**: 核對依據＝(1) `git diff` 四檔＋staged probe；(2) `pytest` 兩檔 → 2 failed／91 passed，失敗訊息分別為複合鍵重複字面 vs manifest event_id 重複；(3) `grep -c validate_split_pair_integrity pipeline.py`＝0 且側別仍 `feature_cutoff_ms` @ `split_projection.py:587-589`；(4) `grep -rn build_event_keys --include='*.py'` 呼叫點表；(5) `reconcile_stamps_check` 三家缺戳；未對 HISTORY 段下 anchor。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-CONSULT-R2-BRIEF.md#688ccf955989

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE
