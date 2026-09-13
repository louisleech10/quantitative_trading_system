# Reconcile — 20260911-splitunify-b9-stamp-r5

**來源** 20260911-splitunify-b9-stamp-r5-codex.md, 20260911-splitunify-b9-stamp-r5-composer.md, 20260911-splitunify-b9-stamp-r5-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_TODO.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **L1 codex APPROVED、授權依據適切、三處歧義有解**——「本輪複驗未發現阻擋收斂或進入Task9.」 | P3 | CODEX-R5-P3-00 | 採納（判 proceed；APPROVED） |
| **L2 composer APPROVED、三處歧義逐條給字面**——「本輪審閱R26收斂檔後無需阻擋戳記之fi」 | P3 | COMPOSER-R5-P3-00 | 採納（判 proceed；APPROVED） |
| **L3 grok APPROVED、三處歧義逐條給字面**——「本輪審閱R26收斂檔後無阻擋戳記之fin」 | P3 | GROK-R5-P3-00 | 採納（判 proceed；APPROVED） |

### 本輪裁定

1. 🏁 **`handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` 取得三家 APPROVED**（body `72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f`、`reconcile_stamps_check` rc=0）⇒ 可作 `Task 9.2b`（批次 B9C）impl token 之 `--adversarial` 授權依據。
2. **三家一致判授權依據適切、不改指**。grok 另實查 `scripts/gate.sh` 確認其對 `--adversarial` 只驗「Verdict ＋ 戳記」，**不**要求內容逐條涵蓋本次施工面 ⇒ 主委 assumed 1 之疑慮被具體否證。
3. 🔴 **主委自標之三處條文未明寫，三家給出完全一致的裁決**（且**主委的假設②被 SPEC 原文否證**）：
   - **①`train_rows` 為空時之 `train_last_ms`**：**不得定義哨兵或 fallback**。步驟 0 已要求兩段皆非空，`validate_split_pair_integrity`（`momentum/core/contracts.py:689-690`）對空段即 `SplitPairLeakageError` ⇒ 空 train **到不了** `train_last_ms`。現行 `split_projection.py:589-590` 之 `continue` 是 9.2b 前遺留，本 Task 須改為 raise（`M-SU-D2-30` 覆蓋此面）。
   - **②`decision_at_ms` 如何進 derive**：🔴 **不得**加入 `EVENT_KEY_COLUMNS`、**不得**改 `build_event_keys` 之 merge——主委原假設「須改 merge 欄位」**被 SPEC §P `Task 9.2b` 原文否證**。正解＝以 `manifest.table` 之 `decision_at_ms`（事件級、欄已存在，見 `event_split.py:68`；`manifest` 已在 `_derive_single_symbol` 作用域）建 `event_id → int(decision_at_ms)` 映射，三段式只讀此映射、不讀 `feature_cutoff_ms`。
   - **③同 `event_id` 多列 `decision_at_ms` 不一致**：正規路徑**結構上不可達**（`manifest.table` 之 `event_id` 已由 `split_projection.py:518-522` 保證唯一）。仍須加防禦閘：若合流後來源之 `decision_at_ms` 去重數 `> 1` ⇒ 於三段式**之前** `raise AlignmentViolationError`（訊息含 `event_id`），不得靜默取首列或改判 purged。本閘與 `(3.2)` 之 `split_label` 唯一檢查**分離**：前者鎖錨定輸入，後者鎖廣播後側別。
4. 🔴 **主委另自查出一處 TODO 與 SPEC 之形狀不一致，本輪三家皆未被問到，列為下一輪必答**：TODO `Task 9.2b` 驗證項寫「`test_multi_feature_tf_opposite_sides_must_fail_closed` 之 `xfail(strict=True)` **於本 Task 解除**」，但 SPEC §V `:270` 之 `(3.2)` 反例逐字為「**直接構造 `assignments`** 使同一 `event_id` 之兩列異側 THEN raise」。在事件級錨定下，該 xfail 測試現行 fixture（同事件兩列 `feature_cutoff_ms` 分落 train／test 段）會被廣播成**同側**、不再 raise ⇒ **照 TODO 字面無法解除 xfail**。兩份文件對同一驗收項給出不同形狀，須在 B9C 審碼輪裁定。
5. **下一步**：領 impl token（`--adversarial` 指 review-r26 收斂檔）進 `Task 9.2b`。

Verdict：可合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R5-P3-00
**斷言**: 本輪複驗未發現阻擋收斂或進入 Task 9.2b（B9C）的 finding；review-r26 body 可由 codex APPROVED 戳記核可。
**碼證**: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → `72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f`, rc=0；`bash scripts/verdict_filled_check.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → rc=0；TODO `Task 9.2b` lines 595–610 and SPEC lines 218–229 were read against the current code paths.
**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md#72cabe12861d
ANSWER_1: (1a) APPROVED；body hash matches the brief and the current block records r25 J1 closure, v21 approval, and no blocking finding. (1b) none.
ANSWER_2: (2a) APPROVED；the target explicitly records “no BLOCKING” and names the B9C implementation scope in its next-step item. (2b) no replacement target is needed; r20 is a prior B9B code-review artifact, not the B9C authorization boundary.
ANSWER_3: (3a) empty `train_rows` is fail-closed because Task 9.2b step 0 already requires both row sets non-empty; `decision_at_ms` remains event-level in `manifest.table` and is not added to `EVENT_KEY_COLUMNS`; duplicate or inconsistent event-level values are rejected by the existing manifest event_id uniqueness guard, with any temporary keyed copy required to equal the manifest value for every row of that event.
ANSWER_3B: (3b) Direct TODO wording: “`decision_at_ms` 是 event-level 欄，維持於 `manifest.table`；不得加入 `EVENT_KEY_COLUMNS`。`_derive_single_symbol` 以唯一的 `event_id` 對 `manifest.table.decision_at_ms` 做 lookup，缺欄、非 finite epoch-ms、非唯一或與同一 `event_id` 之任何暫存列不一致時一律 fail-closed；同一 `event_id` 的所有 feature TF 列共用該唯一值。”
TESTS_RUN: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → rc=0；`bash scripts/verdict_filled_check.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0。
FAILURES_SEEN: target reconcile stamp check was rc=1 before this append because codex/composer/grok stamps were absent; this was expected pre-stamp state and is not a content failure.
SCOPE_CHANGES: only this codex handoff was added and the codex stamp was appended under the existing target `## 戳記`; no code, SPEC, TODO, or target body changes.
NUMERIC_OR_SCHEMA_IMPACT: none.
OUTPUT_PATH: handoffs/20260911-splitunify-b9-stamp-r5-codex.md
VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE
## COMPOSER-R5-P3-00

**斷言**: 本輪審閱 R26 收斂檔後無需阻擋戳記之 finding；body `72cabe12…` 與 brief 一致，裁定段已記錄三家零 finding proceed、SPEC v21 戳記 rc=0、可進 B9C，足以作 `Task 9.2b` impl 授權依據。

**碼證**: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → `72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f` rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0（v21 body `755f3d53…`）；`rg -n '可進 .Task 9.2b|B9C|無 BLOCKING' handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → 裁定段 `:24-25` 命中；`rg -n 'decision_at_ms' momentum/Analysis/event_samples/split_projection.py` → 0 命中（9.2b 施工前狀態，與 SPEC 敘述一致）。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md#72cabe12861d

[P3] 信心度=High。必答 3 三處歧義為**施工澄清**（步驟 0 已涵蓋空 train、manifest 為錨定源、一致性須獨立 fail-closed），不構成拒戳記理由。

---

## GROK-R5-P3-00

**斷言**: 本輪審閱 R26 收斂檔後無阻擋戳記之 finding；body `72cabe12…` 與 brief 一致，裁定段已記錄三家零 finding proceed、SPEC v21 戳記 rc=0、可進 B9C；gate 對 `--adversarial` 不要求內容涵蓋 `Task 9.2b` 施工面；三處歧義為施工澄清（可貼 TODO），不構成 REJECTED。

**碼證**: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → `72cabe12861dfa0c2bb6bbd2f07dedb20054d8bc2bd37c8d960e959a9c93fa6f` rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0（v21 body `755f3d53…`）；`grep -n '可進 .Task 9.2b\|B9C\|無 BLOCKING' handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md` → 裁定段 `:24-25`；`grep -n 'decision_at_ms' momentum/Analysis/event_samples/split_projection.py` → 0 命中（施工前）；`sed -n '689,690p' momentum/core/contracts.py` → 空 train/test raise；`sed -n '518,522p' momentum/Analysis/event_samples/split_projection.py` → manifest `event_id` 唯一 guard；`grep -n '_check_adversarial_quality\|verdict_filled_check\|reconcile_stamps_check' scripts/gate.sh` → adversarial 只驗 Verdict＋戳記。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md#72cabe12861d

[P3] 信心度=High。本輪 `brief-kind: stamp`；攻 assumed 1→授權適切、不改指；攻 assumed 2→三處可開工澄清、非 BLOCKING。

---

