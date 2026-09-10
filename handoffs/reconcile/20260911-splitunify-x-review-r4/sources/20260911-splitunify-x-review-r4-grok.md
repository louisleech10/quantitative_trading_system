# SPLITUNIFY — E1／E2 定向確認 R4（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R4  
family: grok  
findings-round: R4  
標的：`docs/SPLITUNIFY_SPEC.md`（sha256 `384aa22961d0…`）＋`docs/SPLITUNIFY_TODO.md`（sha256 `cd95ee642a9e…`），commit `b6633582`  
SCOPE: review-only；禁改碼／禁改 `docs/SPLITUNIFY_*.md`／禁改 reconcile synth  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式（全文照做）；finding ID 見 `templates/COMMITTEE_FINDING_TEMPLATE.md`  
SPEC-DIGEST: `docs/SPLITUNIFY_SPEC.md#384aa22961d0`  
TODO-DIGEST: `docs/SPLITUNIFY_TODO.md#cd95ee642a9e`

### §0 前提宣告（本輪覆核）

fact-verified: SPEC/TODO hash 與 brief 一致 → `shasum -a 256` → SPEC `384aa22961d0…`／TODO `cd95ee642a9e…`；HEAD `b6633582`

fact-verified: `event_split.py:114` 現行 purge＝`label_end_ms > test_start - embargo` → `sed -n '112,118p' momentum/Analysis/event_samples/event_split.py`

fact-verified: `test_start_ms`＝purge＋embargo **之後**第一根 → `holdout_test_row_index`：`start = split_point + purge_gap + embargo`（`split_preview.py:39-41`）；Task 2.1：`test_start_ms = as_ms(feature_index[test_rows[0]])`（SPEC:386-387）；規則格探針 `test_rows[0]==829 == sp+purge+embargo`

fact-verified: 再減 `embargo_ms` 會與列級 gap **雙重計數** → 規則 1h 格探針：`test_start_ms - embargo*bar_ms == as_ms(feature_index[sp+purge])`；`ends_in_embargo_zone` 下 v4(`>=test_start`)=False、naive old_mapped(`>test_start-embargo`)=True

fact-verified: `dedupe.py:46` 依 `(label_start_ms, event_id)` 重排；`alignment.py:197-213` 可有多個 `per_tf` cutoff → 行號仍成立

fact-verified: `template_check` SPEC／TODO → 兩檔 `TEMPLATE PASS` rc=0

assumed: G-5.3「source bars 缺 endpoint」可在無 bars 簽名下執行 → alignment 產事件時已物化 `label_*`（缺則 fail-closed）；但 post-trim `feature_index` 是否仍含 endpoint **未被** alignment 保證 → 見 GROK-R4-P2-02

assumed: B1 不需先改 TODO Task 2.2 簽名即可開工 → 以「契約權威＝SPEC C-4 且 B1 不動生產碼」推演；若實作端只讀 TODO 會在 B2b 踩坑（P2-01）

---

## Verdict：可進 B1

E1／E2 在 SPEC C-4 的實質契約已閉合（兩段式答案窗 + keyed `event_keys`）；B1 只做文件／枚舉／既有紅清單、不動生產碼。殘留為 TODO 簽名漂移與「source bars」語意澄清（皆 P2，**不擋 B1**），建議 B1 收尾或 B2b 開工前同步。不可用「零 finding」停輪——本輪有實質 P2。

---

## 必答 1–4

### 1. E1 閉合了嗎？第一段條件式？

**閉合（投影座標系下）。** v4 兩段式恢復了 R3 `CODEX-R3-P1-02` 刪掉的答案窗閘；`event_keys` 已帶 `label_end_ms`，G-5.4／`M-SU-13` 可執行。

**可直接實作的式子**（`derive_event_split_from_plans` 內；時間皆 int64 epoch ms）：

```python
def as_ms(ts) -> int:  # DatetimeIndex → asi8 // 10**6；已是 int64 ms 則 int()
    ...

train_ms = {as_ms(feature_index[i]) for i in train_plan.row_index}
test_ms  = {as_ms(feature_index[i]) for i in test_plan.row_index}
# test_start_ms：與 Task 2.1 / holdout_boundary 第四元同源
test_start_ms = as_ms(feature_index[test_plan.row_index[0]]) if len(test_plan.row_index) else None

for row in event_keys.itertuples(index=False):
    fc = as_ms(row.feature_cutoff_ms)
    le = int(row.label_end_ms)
    # 第一段——答案窗（優先；不可調）
    if test_start_ms is not None and fc in train_ms and le >= test_start_ms:
        purged(row.event_id, reason="interval_crosses_split_boundary"); continue
    # endpoint：見 P2-02；建議對 feature_index 做集合 membership，或明示「上游 alignment 已保證、此處不重做」
    # 第二段——集合成員
    if fc in train_ms: assign(train)
    elif fc in test_ms: assign(test)
    else: purged(...)
```

**與 `purge_gap`／`embargo` 的關係**：

- 兩者只以**列數**進入 `holdout_test_row_index`（`split_preview.py:39-41`），決定 `test_rows[0]`，從而決定 `test_start_ms`。
- 第一段**不得**再寫 `label_end_ms > test_start_ms - embargo_ms`：會把已 bake 進列位移的 embargo **再減一次**（探針：embargo-zone 事件被 naive 舊式誤 purge、v4 正確保留）。
- 舊式 `event_split.py:114` 的 `test_start` 是事件 `decision_at_ms` 分位（`:109`），與 kline `test_start_ms` **不是同一變數**，不可逐字移植。
- `>=`（非 `>`）：`label_end_ms == test_start_ms` ＝答案窗觸及測試段第一根 ⇒ purge（對齊 G-5.4）。

**判準**：E1 要擋的是「train 側 feature_cutoff + 答案窗跨進 **test 段**」。列級 purge＋embargo 已把 test 段起點推離 train；第一段比的是這個推離後的 `test_start_ms`。

### 2. E2 閉合了嗎？誰組裝 `event_keys`？

**SPEC 層閉合；TODO 層未對齊（P2-01）。** 六欄足夠：身份（`event_id`／`symbol`／`timeframe`）＋答案窗（`label_start_ms`／`label_end_ms`）＋成員鍵（`feature_cutoff_ms`）。`manifest.table` 已有前五欄來源；`feature_cutoff_ms` 來自 `receipts.per_tf`（`alignment.py:209-210`）；`ic_feed.py:106-109` 已有 `event_id` join 先例。

**組裝立場**：

- **B2b**：新增純函式 helper（建議名 `build_event_keys(manifest, receipts, *, anchor_timeframe) -> pd.DataFrame`），以 `event_id` 鍵 join，**禁 positional zip**；單測自造 DataFrame 亦可，但 helper 應與生產同形。
- **B3 Task 3.1**：caller 在呼叫 `derive_event_split_from_plans` **之前**組好並傳入；投影保持純函式、不讀 receipts。
- 多 TF：每事件只取 **anchor TF** 一列 `feature_cutoff_ms`（與 IC 同源），避免 `per_tf` 多列 zip。

v4 Task 2.2 只寫「以 event_id 對位」、未點名組裝者 → 見 P2-03（不擋 B1）。

### 3. 介面可執行性掃描

| 檢查 | 簽名／落點 | 判定 |
|---|---|---|
| 兩段式答案窗（E1） | `event_keys.label_end_ms`＋由 `test_plan.row_index[0]` 導 `test_start_ms` | ✅ |
| `index_kind != "positional"` raise | `SplitPlan.index_kind` 在簽名上 | ✅ |
| 同時落兩態 raise | train/test 集合可算 | ✅ |
| 單位歸一／禁 `_normalize_ic_time_index` | 自做 ms；該函式拒收 ms（`ic_filter_orchestrator.py:269-271`） | ✅ |
| `bucket_ms` → clusters | C-4 簽名有 `bucket_ms`；`build_time_clusters` 自 `event_split` 抽出 | ✅ |
| `embargo_ms is None` raise | **不在**投影簽名；Task 3.1:480-481 caller + `-k embargo_must_be_none` | ✅ |
| `event_keys` vs TODO `event_index` | SPEC 已改；TODO:178/196 仍寫 `event_index` | ⚠️ P2-01 |
| source bars 缺 endpoint | 簽名無 bars；語意未釘死 | ⚠️ P2-02 |
| B2a tuple vs B2b `SplitPlan` | 測試自建 plan；B3 orchestrator 已有 `SplitPlan` | ✅ |

### 4. 可否進 B1？

**可以。**  
判準：B1＝Task 1.1–1.3（延伸檔／`split_unify.json`／既有紅清單），**不動生產碼**。E1／E2 屬 B2b 實作契約；SPEC C-4 已覆蓋 R3 兩條 P1 的實質缺口。E1／E2 的文件殘留（TODO 漂移、endpoint 語意、組裝者未具名）**不應**擋 B1——但 B1 收尾或 B2b 開工前必須清掉 P2-01，否則實作端只讀 TODO 會建錯簽名。若把「TODO 與 SPEC 簽名互斥」升成 P1，則改判「不可進 B1：GROK-R4-P2-01（升級後）」；本輪依 brief「B1 不動生產碼」與契約權威在 SPEC，維持 **可進 B1**。

---

## GROK-R4-P2-01

**斷言**: TODO Task 2.2 輸入簽名仍寫 `event_index`，與 v4 SPEC C-4 的 `event_keys: pd.DataFrame` 互斥；同段要點又混用兩者，B2b 若只讀 TODO 會實作錯簽名並讓 E2 回潮。

**碼證**: SPEC C-4:156-169 為 `event_keys`＋六欄契約；TODO Task 2.2:178 仍為 `(train_plan, test_plan, event_index, feature_index, *, manifest, bucket_ms=None)`；:188 寫 `event_keys` 對位、:196 又寫「`event_index` 語意＝ feature_cutoff」。RECHECK: `rg -n 'event_index|event_keys' docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.md`

**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0, docs/SPLITUNIFY_TODO.md#cd95ee642a9e

[MAJOR] 信心度=High；**不擋 B1**（SPEC 為準且已正確）。修法：TODO:178／196 與 SPEC C-4 簽名逐字對齊，刪除 `event_index` 殘文。建議併入 B1 文件收尾或 B2b 開工 checklist。

---

## GROK-R4-P2-02

**斷言**: C-4／Task 2.2 第一段要求「`label_*` 在 source bars 上缺 endpoint ⇒ purged」，但投影簽名無 `source_bars`，且未寫死「source bars＝post-trim `feature_index`」或「上游 alignment 已保證、投影不重做」——實作端會發明第三參數或靜默跳過，G-5.3 仍可能空心。

**碼證**: SPEC C-4:177-180、Task 2.2:415-416、G-5.3:286-287 皆寫 source bars endpoint；C-4 簽名:156-164 僅有 `feature_index`／`event_keys`／`manifest`。alignment 在產事件時由 bars 物化 `label_start_ms`／`label_end_ms`（缺 → `_EventFailure`，`alignment.py` label 鏈）；但 HANDOFF 之 EVTALIGN 裁切證明 post-trim universe 可與未裁切不同 ⇒「原料 bars 有 endpoint」≠「feature_index 上仍有 endpoint」。RECHECK: 對照簽名與 G-5.3 原文；抽一筆 post-trim 後 `label_end_ms ∉ feature_index` 的事件（若有）看投影預期。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0, docs/SPLITUNIFY_TODO.md#cd95ee642a9e, momentum/Analysis/event_samples/alignment.py#（label 鏈）

[MAJOR] 信心度=Medium；**不擋 B1**。修法二選一寫死：(A) 投影內用 `feature_index` 毫秒集合做 endpoint membership；(B) 明註「endpoint 由 alignment／dedupe fail-closed 保證，投影第一段只做 `label_end_ms >= test_start_ms`」。G-5.3 nodeid 須與選定語意一致。

---

## GROK-R4-P3-01

**斷言**: v4 未具名 `event_keys` 的組裝函式與批次（B2b helper vs B3 接線），E2「禁 positional zip」在生產路徑仍可能被 caller 用 zip 繞過。

**碼證**: SPEC C-4:167-173／Task 2.2:188-189 只要求對位規則；Task 3.1:265-274 未列組裝 `event_keys` 要點。`ic_feed.py:106-109` 已有 `manifest` ⨝ `per_tf` 之 `event_id` join 可複用。RECHECK: `rg -n 'event_keys|build_event_keys' docs/SPLITUNIFY_*.md`

**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0, docs/SPLITUNIFY_TODO.md#cd95ee642a9e, momentum/Analysis/event_samples/ic_feed.py#（join 段）

[MINOR] 信心度=High；**不擋 B1**。修法：TODO Task 2.2 補 `build_event_keys`；Task 3.1 補「呼叫投影前必須經該 helper（或等價 event_id join）」。

---

## 被當成事實的未驗證假設（§0）

- brief assumed「`test_start_ms` 已含緩衝故第一段不需再減 embargo」→ **本輪實跑支持**；正確式為 `label_end_ms >= test_start_ms`（train 側），**禁止** `> test_start_ms - embargo_ms`。
- SPEC 把第一段寫成「恢復 `event_split.py:114`」→ **語意恢復成立、字面公式不等價**（座標系不同）；實作端若逐字移植舊式會雙重計數。

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `shasum -a 256 docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md` | `384aa22961d0…`／`cd95ee642a9e…` |
| `git rev-parse --short HEAD` | `b6633582` |
| `bash scripts/template_check.sh spec\|todo …` | 兩檔 TEMPLATE PASS rc=0 |
| `sed -n '112,118p' momentum/Analysis/event_samples/event_split.py` | `label_end_ms > test_start - embargo` |
| `sed -n '19-41p' momentum/core/split_preview.py` | `start = split_point + purge_gap + embargo` |
| 規則格探針（venv python） | v4 vs old_mapped 在 embargo-zone 分歧；bake-in 成立 |
| `pytest tests/governance` | **未跑**（brief 禁） |

未改碼。

```
ASSUMPTIONS_VERIFIED: SPEC/TODO sha256 與 brief 一致；holdout_test_row_index 列級 bake-in；event_split.py:114 舊式；探針否證「再減 embargo」；dedupe 重排／alignment per_tf；template_check 雙 PASS
TESTS_RUN: shasum；template_check×2 rc=0；split_preview／event_split sed；規則格＋不規則格 python 探針；未跑 pytest
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
```

STATUS: DONE
