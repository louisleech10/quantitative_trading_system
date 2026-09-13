# SPLITUNIFY b9 — review-r26 收斂檔戳記 — grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-STAMP-R5`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-STAMP-R5-BRIEF.md`  
**findings-round**: R5  
**stamp-target**: `handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md`  
**禁改碼**：本輪只產 stamp 交件＋一行戳記 append；未改 SPEC／TODO／生產碼／收斂檔正文。

---

## 必答 1 — body 戳記

**(1a) 對 body `72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f`：`APPROVED`**

實跑 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → `72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f`（與 brief 逐字相符）。裁定段記錄：r25 三條 P1 各自 CLOSED、SPEC v21 三家戳記 `reconcile_stamps_check` rc=0、三家零 finding proceed、第 5–6 點「可進 `Task 9.2b`（批次 B9C），無 BLOCKING」。

**(1b) `N/A`（未 REJECTED）**

---

## 必答 2 — impl 授權依據適切性（攻 assumed 1）

**(2a) 適切。** 本檔制度角色＝高風險派工之 `--adversarial` 標的（brief 明示）。機械條件＝已填實 Verdict ＋三家 `RECONCILE-STAMP`。

**攻 assumed「gate 是否還要求內容涵蓋 Task 9.2b 施工面」→ 否**：實讀 `scripts/gate.sh` `_check_adversarial_quality`／`_process_one_adversarial_file`（約 `:414-537`），對非 `*-ADV-*` 路徑只跑 `verdict_filled_check.sh` ＋ `reconcile_stamps_check.sh`；**無** Task／施工面關鍵字或 scope 掃描。施工權威仍在已戳記之 `docs/SPLITUNIFY_SPEC.D-002.md`（v21 body `755f3d53…`，`reconcile_stamps_check` rc=0）與 `docs/SPLITUNIFY_TODO.md` §C-9 `Task 9.2b`；本檔只閉合「進實作」程序鏈最後一環（裁定第 5–6 點）。零 finding sentinel 不減損該角色——裁定正文已逐字寫「可進 B9C」。

**(2b) 不應改指。** 理由：
1. r20 收斂檔閉合的是 B9B（`Task 9.2`／`9.2a`），不是 B9C 放行證明。
2. 另開「針對 9.2b 設計」之 consult 會重開已歷 r13–r26 定案之三段式／`(3.2)`／跨表互斥，與 brief「不在本輪範圍」及 HANDOFF「下一步領 impl token」矛盾。
3. 改指不會增加對 9.2b 的機械覆蓋（gate 本來就不掃施工面），只會丟掉「r25 閉合＋v21 戳記 rc=0＋三家可進 B9C」這道最後前置之收斂證明。

---

## 必答 3 — `Task 9.2b` 三處未明寫（攻 assumed 2；諮詢字面，本輪不改 TODO）

**(3a) 裁決摘要**

| # | 議題 | 裁決 |
|---|---|---|
| ① | `train_rows` 為空時 `train_last_ms` | **不得定義哨兵／fallback**。步驟 0 ①已要求兩段皆非空；`validate_split_pair_integrity`（`contracts.py:689-690`）空 train／test 即 `SplitPairLeakageError`——空 train **到不了** `train_last_ms = int(index_ms[train_rows[-1]])`。現行 `split_projection.py:589-590` 之 `continue` 是 9.2b 前遺留，由步驟 0＋`M-SU-D2-30` 覆蓋為 raise。 |
| ② | `decision_at_ms` 如何進 derive | **不擴 `EVENT_KEY_COLUMNS`、不改 `build_event_keys` merge**。SPEC §P `Task 9.2b` 已寫死以 `manifest.table` 之 `decision_at_ms`（欄已存在，`event_split.py:68`；`manifest` 已在 `_derive_single_symbol` 作用域）每事件判一次再廣播。brief 假設「須改 merge 欄位」被 SPEC 原文否證。 |
| ③ | 同 `event_id` 多列 `decision_at_ms` 不一致 | **正規路徑結構上不可達**（`manifest.table` 之 `event_id` 已唯一，`:518-522`）。防禦：若誤把該欄帶上 per-TF 列且同 `event_id` 去重數 `> 1` ⇒ 三段式**之前** `raise AlignmentViolationError`（訊息含 `event_id`），不得靜默取首／改判 purged。`(3.2)` 仍只管廣播後 `split_label` 異側，與本閘分離。 |

**(3b) 可直接貼進 TODO `Task 9.2b` 的字面（本輪未改檔）**

1. **步驟 0 補一句（接在「`train_rows`／`test_rows` 皆非空」之後）**：「空 `train_rows` 或空 `test_rows` 須在 `EventSamplePipeline.run` 呼叫 `validate_split_pair_integrity` 時即 `SplitPairLeakageError`；**禁止**在 derive 內以 `train_rows.size==0` 跳過（現行 `:589-590`）而後再讀 `train_rows[-1]`；`train_last_ms` **無**空段定義。」
2. **實作要點新增子條（錨定來源）**：「`decision_at_ms` **不得**加入 `EVENT_KEY_COLUMNS` 或 `build_event_keys` 輸出；在 `_derive_single_symbol` 開頭自 `manifest.table[["event_id","decision_at_ms"]]` 建 `event_id → int(decision_at_ms)` 映射（`validate="1:1"`），三段式只讀此映射，不讀 `feature_cutoff_ms`。」
3. **實作要點新增子條（錨定一致性，在 `(3.2)` 之前）**：「對每個 `event_id`，若合流後來源之 `decision_at_ms` 去重數 `> 1`，`raise AlignmentViolationError`（訊息含 `event_id`）；通過後才執行事件級側別廣播與 `(3.2)` 之 `split_label` 唯一檢查。正規路徑取自已唯一之 `manifest.table`，此閘為防誤帶 per-TF 列。」

---

## §0 被當成事實的未驗證假設

無。brief 四條 fact-verified 已複驗（body hash／SPEC stamps rc=0／synth 裁定／回歸前提 VERIFY-EXEMPT）。兩條 assumed 已於必答 2／3 處理：授權依據適切；三處歧義可開工（步驟 0／manifest 錨／防禦閘已可由現有條文＋可貼字面閉合，不構成拒戳記）。

---

## GROK-R5-P3-00

**斷言**: 本輪審閱 R26 收斂檔後無阻擋戳記之 finding；body `72cabe12…` 與 brief 一致，裁定段已記錄三家零 finding proceed、SPEC v21 戳記 rc=0、可進 B9C；gate 對 `--adversarial` 不要求內容涵蓋 `Task 9.2b` 施工面；三處歧義為施工澄清（可貼 TODO），不構成 REJECTED。

**碼證**: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → `72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f` rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0（v21 body `755f3d53…`）；`grep -n '可進 .Task 9.2b\|B9C\|無 BLOCKING' handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → 裁定段 `:24-25`；`grep -n 'decision_at_ms' momentum/Analysis/event_samples/split_projection.py` → 0 命中（施工前）；`sed -n '689,690p' momentum/core/contracts.py` → 空 train/test raise；`sed -n '518,522p' momentum/Analysis/event_samples/split_projection.py` → manifest `event_id` 唯一 guard；`grep -n '_check_adversarial_quality\|verdict_filled_check\|reconcile_stamps_check' scripts/gate.sh` → adversarial 只驗 Verdict＋戳記。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md#72cabe12861d

[P3] 信心度=High。本輪 `brief-kind: stamp`；攻 assumed 1→授權適切、不改指；攻 assumed 2→三處可開工澄清、非 BLOCKING。

---

## 戳記

已 append 至 `handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` `## 戳記` 區：

```text
RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f task:20260911-SPLITUNIFY-B9-STAMP-R5
```

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body hash 72cabe12…；SPEC stamps rc=0；synth 裁定段含 B9C 放行；gate adversarial 只驗 Verdict＋戳記；split_projection 無 decision_at_ms；validate_split_pair_integrity 空段 raise；manifest event_id 唯一
TESTS_RUN: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → 72cabe12…（append 戳記前後不變）；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-stamp-r5-grok.md --family grok` → COMPLETENESS PASS rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（戳記 append ＋本交件檔）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-stamp-r5-grok.md
TMP_CLEANUP: /tmp 與 /private/tmp 無 `*workdir*` 可清；`claude-501` 保留

STATUS: DONE
