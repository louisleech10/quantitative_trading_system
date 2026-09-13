# SPLITUNIFY b9 — review-r26 收斂檔戳記 — composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-STAMP-R5`  
**family**: composer  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-STAMP-R5-BRIEF.md`  
**findings-round**: R5  
**stamp-target**: `handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md`  
**禁改碼**：本輪只產 stamp 交件＋一行戳記 append。

---

## 必答 1 — body 戳記

**(1a) 對 body `72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f`：`APPROVED`**

**(1b) `N/A`（未 REJECTED）**

---

## 必答 2 — 授權依據適切性

**(2a) 適切。** 本輪輸入邊界僅判「R26 收斂檔能否作 `Task 9.2b`（B9C）impl 之 `--adversarial` 授權依據」，不重開 9.2b 設計（brief 明文）。該檔裁定段逐字記錄：r25 三條 P1 各自 CLOSED、SPEC v21 三家戳記 `reconcile_stamps_check` rc=0、三家零 finding proceed，且第 5–6 點一致「可進 `Task 9.2b`（批次 B9C），無 BLOCKING」並列下一步為領 impl token。這正是 `gate.sh dispatch --risk high` 所要求的「已戳記 reconcile ＋ Verdict」組合；brief assumed 1 所疑之「零 finding sentinel 與 9.2b 施工面無逐條對應」屬授權鏈完整性問題，但本檔已把「進 B9C」寫進裁定與三家 ANSWER_6／synopsis，且 SPEC／TODO 之 9.2b 條文仍為施工權威——收斂檔角色是**閉合前置與放行**，不是重寫施工單。

**(2b) `N/A`。** 不建議改指 r20 B9B 收斂檔或另開 consult：r20 閉合的是 9.2／9.2a（B9B），本批 B9C 之委員會裁定已寫在 R26 synth；另開 consult 會把本輪已閉合的「可進 B9C」再拖一輪，與 HANDOFF ⑯「下一步領 impl token 進 9.2b」矛盾。

---

## 必答 3 — `Task 9.2b` 三處未明寫（諮詢字面；本輪不改 TODO）

**(3a) 裁決摘要**

| # | 議題 | 裁決 |
|---|---|---|
| ① | `train_rows` 為空時 `train_last_ms` | **不得定義哨兵值**；步驟 0 要求兩段皆非空，`EventSamplePipeline.run` 在 derive 前呼叫 `validate_split_pair_integrity` 即會 `SplitPairLeakageError`（`contracts.py:689-690`），空 train **到不了** `train_last_ms = int(index_ms[train_rows[-1]])`。現行 `split_projection.py:589-590` 之 `continue` 為 9.2b 前遺留，由步驟 0 覆蓋。 |
| ② | `decision_at_ms` 如何進 derive | **不擴 `EVENT_KEY_COLUMNS`／不改 `build_event_keys` merge**；SPEC §P `Task 9.2b` 已寫死以 `manifest.table["decision_at_ms"]`（事件級、欄已存在，`event_split.py:68`）在 `_derive_single_symbol` 內每事件判一次再廣播。`manifest` 已在該函式作用域；`build_event_keys` 仍只產 per-TF 行粒度鍵。 |
| ③ | 同 `event_id` 多列 `decision_at_ms` 不一致 | **在三段式之前**對 `manifest.table` 按 `event_id` 檢查 `decision_at_ms` 唯一；若同一 `event_id` 對應多值（或與 per_tf 帶入值衝突）⇒ `raise AlignmentViolationError`（訊息含 `event_id`），**不得**靜默取首列或改判 purged。此檢查與 `(3.2)` 之 `split_label` 唯一互斥為兩道閘：前者鎖事件級錨定輸入，後者鎖廣播後側別。 |

**(3b) 可直接貼進 TODO `Task 9.2b` 的字面（本輪未改檔，供後續修訂輪採納）**

1. **步驟 0 補一句（接在「`train_rows`／`test_rows` 皆非空」之後）**：「空 `train_rows` 或空 `test_rows` 須在 `EventSamplePipeline.run` 呼叫 `validate_split_pair_integrity` 時即 `SplitPairLeakageError`；**禁止**在 derive 內以 `train_rows.size==0` 跳過而後再讀 `train_rows[-1]`。」
2. **實作要點新增子條（錨定來源）**：「`decision_at_ms` **不得**加入 `EVENT_KEY_COLUMNS` 或 `build_event_keys` 輸出；在 `_derive_single_symbol` 開頭自 `manifest.table[["event_id","decision_at_ms"]]` 建 `event_id → int(decision_at_ms)` 映射（`validate="1:1"`），三段式只讀此映射，不讀 `feature_cutoff_ms`。」
3. **實作要點新增子條（錨定一致性，在 `(3.2)` 之前）**：「對每個 `event_id`，若 `manifest.table` 或合流後 per-TF 來源之 `decision_at_ms` 去重數 `> 1`，`raise AlignmentViolationError`（訊息含 `event_id`）；通過後才執行事件級側別廣播與 `(3.2)` 之 `split_label` 唯一檢查。」

---

## §0 被當成事實的未驗證假設

無（brief 四條 fact-verified 均已複驗；兩條 assumed 已在上文必答 2／3 處理）。

---

## COMPOSER-R5-P3-00

**斷言**: 本輪審閱 R26 收斂檔後無需阻擋戳記之 finding；body `72cabe12…` 與 brief 一致，裁定段已記錄三家零 finding proceed、SPEC v21 戳記 rc=0、可進 B9C，足以作 `Task 9.2b` impl 授權依據。

**碼證**: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → `72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f` rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0（v21 body `755f3d53…`）；`rg -n '可進 .Task 9.2b|B9C|無 BLOCKING' handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → 裁定段 `:24-25` 命中；`rg -n 'decision_at_ms' momentum/Analysis/event_samples/split_projection.py` → 0 命中（9.2b 施工前狀態，與 SPEC 敘述一致）。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md#72cabe12861d

[P3] 信心度=High。必答 3 三處歧義為**施工澄清**（步驟 0 已涵蓋空 train、manifest 為錨定源、一致性須獨立 fail-closed），不構成拒戳記理由。

---

## 戳記

已 append 至 `handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` `## 戳記` 區：

```text
RECONCILE-STAMP: composer APPROVED 2026-09-14 sha256:72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f task:20260911-SPLITUNIFY-B9-STAMP-R5
```

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body hash 72cabe12…；SPEC stamps rc=0；synth 裁定段含 B9C 放行；split_projection 無 decision_at_ms（施工前）；validate_split_pair_integrity 空 train/test 即 raise  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-stamp-r5-composer.md --family composer` → rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（戳記 append ＋本交件檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_PATH: handoffs/20260911-splitunify-b9-stamp-r5-composer.md  
TMP_CLEANUP: /private/tmp 僅 `claude-501`，無 `*workdir*` 需清  

STATUS: DONE
