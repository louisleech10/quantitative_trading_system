# SPLITUNIFY b9 consult R2 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-CONSULT-R2  
family: COMPOSER  
brief: `handoffs/20260911-SPLITUNIFY-B9-CONSULT-R2-BRIEF.md`  
scope: 只讀裁定；未改程式、SPEC、TODO、測試、golden、`data_cache/` 或根 `HANDOFF.md`

## 被當成事實的未驗證假設（§0）

| 假設 | 判定 | 碼證 |
|---|---|---|
| 本批碼對 v12 以前 D-002 寫、與 v13 O1/O3/O4 不相容 | **部分成立** | O4 缺（`pipeline.py` 零 `validate_split_pair_integrity`）；O1 對本 diff **no-op**（未碰 metadata 路徑）；9.2/9.2a 與 v13 §P 對齊、9.2b 全缺 |
| 「回退」成本上界＝重寫四檔 diff | **成立** | `grep -rn build_event_keys --include='*.py' .` 僅 4 生產/測試檔＋`handoffs/*probe*`；`git status --porcelain` 在 `momentum/`/`tests/` 僅此四檔（除 `__pycache__` 副作用） |
| 停輪判準仍成立 | **fact-verified** | brief 已排除；R12 synth 為唯一權威，本輪不審 D-002 規格內容本身 |

---

## 必答 1 — 整批保留／回退／部分

### (1a) 裁定字面

**REVERT**

整批未 commit 生產碼（`split_projection.py`、`pipeline.py` 與兩測試檔）應 `git checkout --` 丟棄，待 TODO 補齊 Task 9.1–9.5、SPEC stamp 核可、impl token 派工後，依 v13 序列重寫。

### (1b) 若 REVERT 裁錯，怎麼爆

```bash
git checkout -- momentum/Analysis/event_samples/split_projection.py momentum/Analysis/event_samples/pipeline.py tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py && source venv/bin/activate && python -m pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py -q; echo rc=$?
```

**期望**：`0 failed` 且 `rc=0`。若 REVERT 丟棄了「已可保留且 v13 相容」之實質進度，重跑後會少通過本 diff 新增之 green 用例（如 `test_full_scan_emits_one_row_per_feature_tf`），主委應看到 passed 數低於 diff 時之 91。

### (2b) 為何不選 PARTIAL

四檔 diff 是 **9.1＋9.2＋9.2a 綑綁、缺 9.2b＋O4** 的不可交付切片：`assignments`/`purged` 已升複合鍵 schema（`split_projection.py:623-627`），但側別仍逐列 `feature_cutoff_ms`（`:586-621`），與 v13 `Task 9.2b`／`D-002-C3` 事件級錨定直接衝突。逐 hunk 保留會留下「schema 像 v13、行為像 v12」的既成事實，且無 impl token／stamp 背書。O1（metadata 斷言移入殘留）對本批 **no-op**，不足以成為 KEEP 理由。

---

## 必答 3 — 兩條紅測試

### (3a) 逐條判定

| 測試 | 判定 | 理由 |
|---|---|---|
| `test_duplicate_event_id_is_fail_closed` | **測試過時** | v13 §P `Task 9.2a` 將唯一性改為 `(event_id, feature_timeframe)`；dup 整列後 raise 訊息為「複合鍵重複」而非舊 regex `event_id 重複`（實跑 mismatch 見下） |
| `test_multi_feature_tf_opposite_sides_must_fail_closed` | **實作錯＋測試 fixture 錯** | 規格授權：`D-002-C3` (3.2)／§V「異側 ⇒ `AlignmentViolationError`」須在 `Task 9.2b` 落地；現碼未實作且 `_manifest(keys)` 對多列 keys 產出重複 `event_id` manifest，先觸發 `:497-501` 而非 C3 |

**碼證（duplicate 測試）**：

```bash
source venv/bin/activate && python -m pytest tests/momentum/Analysis/test_splitunify_derive.py::test_duplicate_event_id_is_fail_closed -q
```

stdout：`Regex: 'event_id 重複'` vs `Input: '... (event_id, feature_timeframe) 複合鍵重複 ['e_train_ok/1h']...'`

**碼證（multi-TF 測試）**：

```bash
source venv/bin/activate && python -m pytest tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed -q
```

stdout：`Input: '... manifest.table 之 event_id 重複 ['e_x']...'`（regex `同一事件|異側|同側` 未命中）

### (3b) 可證偽

- 若判 duplicate 為「測試過時」錯：把 `match=` 改為 `複合鍵重複` 後全檔 pytest 仍紅 ⇒ 實作亦有 bug。
- 若判 multi-TF 為「僅測試過時」錯：修正 `_manifest` 為事件級單列＋補完 9.2b 後，該測試應 raise 含 `AlignmentViolationError` 或 `同一事件|異側|同側`；若仍只出 manifest 重複 ⇒ 實作仍未到 C3 落點。

---

## 必答 4 — Task 9.1–9.5 驗收命令（可貼 TODO）

| Task | 驗收命令（逐字） |
|---|---|
| **9.1** | `pytest tests/momentum/Analysis/test_splitunify_derive.py::test_build_event_keys_returns_discarded_counts tests/momentum/Analysis/test_splitunify_derive.py::test_build_event_keys_discarded_is_empty_dict_for_single_tf tests/momentum/Analysis/test_splitunify_derive.py::test_summary_carries_producer_discarded_verbatim tests/momentum/Analysis/test_splitunify_derive.py::test_summary_discarded_defaults_to_empty_dict tests/momentum/event_samples/test_splitunify_wiring.py::test_splitunify_wiring_selected_timeframe_none_goes_projection -q` |
| **9.2** | `pytest tests/momentum/Analysis/test_splitunify_derive.py::test_full_scan_emits_one_row_per_feature_tf tests/momentum/event_samples/test_splitunify_wiring.py::test_splitunify_wiring_selected_timeframe_none_goes_projection tests/momentum/event_samples/test_splitunify_wiring.py -k partial_boundary -q` |
| **9.2a** | `pytest tests/momentum/Analysis/test_splitunify_derive.py::test_build_event_keys_joins_by_event_id_not_position tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed -q` |
| **9.2b** | `pytest tests/momentum/Analysis/test_splitunify_derive.py -k 'multi_feature_tf_opposite_sides or answer_window or decision_at' -q`；`bash scripts/freeze_splitunify_golden.py`；`pytest tests/momentum/Analysis/test_splitunify_golden.py -q` |
| **9.3** | `pytest tests/momentum/event_samples/test_pattern_bridge.py tests/momentum/event_samples/test_feature_materialization.py tests/momentum/event_samples/test_tables.py -q` |
| **9.4** | `pytest tests/momentum/event_samples/test_metrics_glossary.py tests/momentum/Analysis/test_splitunify_derive.py -k tier_min -q` |
| **9.5** | `pytest tests/momentum/Analysis/test_splitunify_golden.py -q`；`cd frontend && npm run build` |

### (4b) 依賴順序

1. **9.1**（無依賴）→ 2. **9.2**（依 9.1 之 discarded 契約）→ 3. **9.2a**（與 9.2 同檔，邏輯上緊接 9.2 後；schema 需 producer 全量列）→ 4. **9.2b**（依 9.2a 複合鍵＋manifest 事件級不變）→ **9.3／9.4 可並行**（皆依 9.2a 之 assignments 形狀，互不依賴）→ 5. **9.5**（依 9.2b 正確側別＋golden fixture）。

---

## 必答 5 — stamp 輪

### (5a)

**REJECTED**（對 `docs/SPLITUNIFY_SPEC.D-002.md` body sha256 `06b2d4cb…`）

| 阻擋條目 | 一次修訂可關？ |
|---|---|
| `docs/SPLITUNIFY_TODO.md` 缺 `Task 9.1`–`9.5` 段（§P 已有、TODO 無） | 是 — 自 §P／§V 複製上表驗收命令 |
| §V `V8_BASELINE_SHA256=` 64-hex 錨點未寫入（spec 自標「凍結當下才生效」） | 是 — 首次 freeze 時寫入；或維持 defer 但 stamp brief 須明示 |

規格正文 v13 停輪內容本身 R12 已閉；阻擋在 **TODO 同步** 與 **golden 錨點程序**，非再開規格審查。

### (5b)

（5a 為 REJECTED，本項 N/A）

---

## 必答 6 — 可否進 Task 9.1

### (6a)

**BLOCKING** — 不可在現狀開 Task 9.1 實作。

### (6b) 最小閉合集合

1. 本輪三家裁定 **REVERT** 未 commit 四檔（或等同：checkout 至 HEAD 且 pytest 兩檔全綠）。
2. `docs/SPLITUNIFY_TODO.md` 補 **Task 9.1–9.5**（含上表驗收命令）。
3. **stamp 輪**對 D-002 v13 三家 `RECONCILE-STAMP`（`reconcile_stamps_check.sh` rc=0）。
4. 派 **impl token** 後再動生產碼。

已查：`reconcile_stamps_check` 未核可；兩檔 pytest **2 failed**；`pipeline.py` **0** 次 `validate_split_pair_integrity`；`debt_ledger --has-open` rc=0（本輪 consult 開債後預期 rc=1，收斂後清債）。

---

## Findings

## COMPOSER-R2-P0-01

**斷言**: 未 commit 之 `pipeline.py` 未實作 v13 O4：進入 `derive_event_split_from_plans` 之前須以 `feature_index` 作 `ts`、`train_plan.symbol` 廣播作 `symbols` 呼叫 `validate_split_pair_integrity`；保留本批碼會讓 Task 9.2b 前置永遠缺落點。

**碼證**: `grep -n validate_split_pair_integrity momentum/Analysis/event_samples/pipeline.py` → **0** 命中；對照 `ic_split_adapter.py:305` 有呼叫；v13 §V Task 9.2b 前置改寫 O4。CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:755; MUTATION: 刪除 `derive_event_split_from_plans` 呼叫塊後插入 validator 前後再跑 `grep -c validate_split_pair_integrity momentum/Analysis/event_samples/pipeline.py` 應由 0 變 ≥1。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[BLOCKING] 信心度=High。**修法**：REVERT 後於 `EventSamplePipeline.run` 在 `:755` 前插入 validator（含座標 adapter 四案）；驗收掛 §V pair 完整性斷言。**可行性**：validator 已存在於 `ic_split_adapter.py`，事件路徑缺的是呼叫與 `symbols` 構造，非新算法。

---

## COMPOSER-R2-P0-02

**斷言**: 本批 diff 未實作 `Task 9.2b`／`D-002-C3`：`_derive_single_symbol` 仍以 `feature_cutoff_ms` 集合成員定 `split_label`（`:586-621`），全檔 `decision_at_ms` 命中 **0**；保留即 schema 複合鍵、語意仍 v12，會靜默產生同事件異側 OOS。

**碼證**: `grep -n decision_at_ms momentum/Analysis/event_samples/split_projection.py` → **0**；`:587-588` 仍 `cutoff in train_ms`/`test_ms`。CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:586; MUTATION: 將 `:587` 改回純 `feature_cutoff_ms` 判側後 `pytest tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed -q` 應不再觸發 C3 路徑（若 9.2b 已實作則 mutation 應轉紅）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[BLOCKING] 信心度=High。**修法**：REVERT 後按 §P Task 9.2b 三段式＋C3 `AlignmentViolationError` 整段實作；不可只保留 9.2a schema。**可行性**：spec 已具名落點與 §V 反例；缺的是施工，非規格空白。

---

## COMPOSER-R2-P1-01

**斷言**: 四檔生產/測試變更無 impl token、D-002 零 `RECONCILE-STAMP`，卻已改 producer 簽章與投影門檻，屬流程違規進度，不得 KEEP。

**碼證**: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → 三家皆「缺 APPROVED 戳記」；`git diff --stat` 僅四檔、無 `.claude/gate/*impl*` token 紀錄。CODE-ANCHOR: docs/SPLITUNIFY_SPEC.D-002.md:172; MUTATION: 在無 stamp／無 token 下 commit 四檔後 `reconcile_stamps_check.sh` 仍 rc≠0 ⇒ 程序仍 fail-closed。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[BLOCKING] 信心度=High。**修法**：REVERT → TODO 9.1–9.5 → stamp → impl token → 重寫。**可行性**：回退成本已證為四檔 diff 上界。

---

## COMPOSER-R2-P1-02

**斷言**: `test_multi_feature_tf_opposite_sides_must_fail_closed` 之 `_manifest(keys)` 對多 feature TF keys 複製 `event_id`，違反 v13「manifest 事件級唯一」；測試在 C3 實作完成前必紅，不能當 KEEP 理由。

**碼證**: `tests/momentum/Analysis/test_splitunify_derive.py:142-149` 逐列複製 `keys["event_id"]`；`:1068-1072` 兩列同 `e_x` ⇒ manifest 雙列。CODE-ANCHOR: tests/momentum/Analysis/test_splitunify_derive.py:142; MUTATION: `_manifest` 改 `drop_duplicates("event_id")` 後若 9.2b 未實作，測試應 fail 於異側而非 manifest 重複 — 用於區分「僅 fixture 錯」vs「實作缺」。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[MAJOR] 信心度=High。**修法**：REVERT 後重寫測試：manifest 一事件一列、keys 兩 feature TF；期待 `AlignmentViolationError`。**可行性**：§V `D-002-C3` (3.2) 已授權。

---

## COMPOSER-R2-P2-01

**斷言**: `test_duplicate_event_id_is_fail_closed` 之 regex 仍綁 v12「event_id 重複」語意；v13 `Task 9.2a` 已改複合鍵 guard，屬測試過時而非 producer 回歸。

**碼證**: `:811-818` `match="event_id 重複"`；實跑 raise 含 `(event_id, feature_timeframe) 複合鍵重複`。CODE-ANCHOR: tests/momentum/Analysis/test_splitunify_derive.py:815; MUTATION: 僅改 regex 為 `複合鍵重複` 而不改 `split_projection.py:486-496` ⇒ 若 guard 被刪則應轉紅。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[MAJOR] 信心度=High。**修法**：impl 時同步改 regex 或改 dup fixture 為同 `(event_id, feature_timeframe)` 兩列。

---

## COMPOSER-R2-P2-02

**斷言**: `build_event_keys` 簽章改為 `Tuple[DataFrame, Dict]` 之破壞範圍已閉合於 repo 內呼叫點；`handoffs/20260911-splitunify-b9-probe-multitf.py:47` 已用雙回傳值，REVERT 四檔不會留孤兒 caller（probe 可獨立再改）。

**碼證**: `grep -rn build_event_keys --include='*.py' .` → 僅 `split_projection`/`pipeline`/兩測試檔/probe；無 `api/` 命中。CODE-ANCHOR: handoffs/20260911-splitunify-b9-probe-multitf.py:47; MUTATION: 暫改 probe 為單回傳 `build_event_keys(...)` 應 TypeError — 證明 probe 與新簽章綁定，REVERT 生產碼時 probe 須一併改回或暫不跑 case C/D。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[MINOR] 信心度=High。doc_friction：攻擊面表格已列、本輪逐 caller 核對後閉合。

---

## COMPOSER-R2-P3-01

**斷言**: 本批 diff **未**改動 `tests/golden/splitunify/splitunify_golden.json` 任一頂層鍵；Task 9.5／v8 錨點仍未開工，與 brief fact-verified 一致。

**碼證**: `git diff -- tests/golden/splitunify/` → 空；`ls tests/golden/splitunify/` 無 `splitunify_golden.v8.json`。CODE-ANCHOR: tests/golden/splitunify/splitunify_golden.json:1; MUTATION: 對主檔任一頂層鍵改值後 `pytest tests/momentum/Analysis/test_splitunify_golden.py -q` 應轉紅（證明 9.5 回歸網仍有效、本批未觸）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[MINOR] 信心度=High。無需因本批 KEEP/REVERT 重算 golden。

---

## COMPOSER-R2-P3-02

**斷言**: `assignments` 新增 `feature_timeframe` 欄命中 register **C5-20**／**C5-21**（乙類）；`extract_event_patterns` 仍 `assign.set_index("event_id")`（`:125`），無 production caller（§E `R-4`），本批未紅但 **Task 9.3** 前不得宣稱消費面安全。

**碼證**: `pattern_bridge.py:125`；§E `R-4` blocked-by。CODE-ANCHOR: momentum/Analysis/event_samples/pattern_bridge.py:125; MUTATION: 對含同 event 雙 feature TF 之 assignments 跑 `extract_event_patterns` ⇒ `lab_by_id[e]` 變 Series 非純量（Task 9.3 應 fail-closed）。

**來源摘要**: docs/SPLITUNIFY_TODO.md#e44da6448b01

[MINOR] 信心度=Medium。不阻本輪 REVERT 裁定；列入 9.3 施工清單。

---

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:
