# Reconcile — 20260911-splitunify-x-review-r4

**來源** 20260911-splitunify-x-review-r4-codex.md, 20260911-splitunify-x-review-r4-composer.md, 20260911-splitunify-x-review-r4-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 可合併——**v5 套用三家給的具體修法後直接進 B1，不再開 R5**（收斂斷路器，理由見下）。

三家 verdict：codex「不可進 B1：`CODEX-R4-P1-01`～`P1-03`」；composer「可進 B1」；grok「可進 B1」。
**實質上三家對「哪裡還沒寫清楚」是一致的**（都指向 E1 的 source-bars 輸入、E2 的 producer
未具名、TODO 簽名未同步），只是 codex 認為要先修才放行 B1、另兩家認為不擋 B1。
⇒ 主委裁定：**兩者都採**——先修（採 codex 立場），但**不為了修這三條再開一輪**（採另兩家
對嚴重度的判斷）。codex 自己已經把三條的修法寫成可直接落地的式子，沒有需要再討論的餘地。

| 群集 | 嚴重度 | 來源 ID | 處置（v5） |
|---|---|---|---|
| **F1 E1 條件式與 source-bars 輸入** | P1 | CODEX-R4-P1-01、GROK-R4-P2-02 | **採納 codex 之逐字式子**：`train_cutoff = feature_cutoff_ms ∈ as_ms(feature_index[train_plan.row_index])`；test plan 非空時 `train_cutoff and label_end_ms >= as_ms(feature_index[test_plan.row_index[0]])` ⇒ purge。🔴 `>=` **保留**；`purge_gap`／`embargo` 是 **row 單位且已含在 test row 起點**，**不得**再以毫秒相減（我 v4 的直覺是對的，但 codex 給了精確式子與理由）。`test_plan.row_index` 為空 ⇒ **先 fail-closed／轉 event-study-only**，不得與 `None` 比較。source-bars endpoint 檢查**不進投影簽名**：明定為**上游 alignment 之可證明前置條件**（`AlignmentReceipts` 已持有，`alignment.py:197-213`），G-5.3 改用 receipts 驗，投影不重做（採 grok 之二選一的後者，避免發明第三參數）。 |
| **F2 `event_keys` 的 producer 與多 TF provenance** | P1 | CODEX-R4-P1-02、GROK-R4-P3-01 | **採納**。B2b 新增**具名 helper** `build_event_keys(receipts, *, selected_timeframe)`：由 `receipts.event_level`（id／label／symbol／trigger context）與 `receipts.per_tf`（`feature_cutoff_ms` 住這裡）依 **`event_id` ＋ 明示的 selected feature timeframe** keyed join；**B3 只傳遞，不在接線處臨時組裝**。保留 `event_id` 單鍵，但**必須**要求每事件恰一個 selected `per_tf` row，否則 raise（多 TF 情形若日後要支援，鍵與輸出契約須改成 `(event_id, timeframe)`，列為殘留）。碼證：`manifest.table` 只 merge trigger `timeframe`、無 cutoff（`dedupe.py:39-49,101-120`、`types.py:37-40,55-60`）⇒ **不能**用 manifest 的 timeframe 代替 per-TF cutoff 的 timeframe。 |
| **F3 Task 3.1 之 config 欄位層級寫錯** | P1 | CODEX-R4-P1-03 | **採納**。`EventPipelineConfig` 只有 `split: EventSplitConfig`（`pipeline.py:31-45`），`embargo_ms`／`embargo_ms_by_symbol` 住 `EventSplitConfig`（`types.py:64-83`）⇒ v4 寫的 `config.embargo_ms` 會直接 `AttributeError`。改為 `config.split.embargo_ms is None and config.split.embargo_ms_by_symbol is None`，且**只套在事件 pipeline caller**——IC orchestrator 的 `_build_holdout_split_plan` 收的是 `ICConfig`，不得套同一個 assert。 |
| **F4 TODO Task 2.2 簽名未與 SPEC 同步** | P2 | COMPOSER-R4-P2-01、GROK-R4-P2-01 | **採納**。TODO 之「輸入／輸出」仍寫 `event_index`，SPEC C-4 已是 `event_keys: pd.DataFrame` ⇒ 只讀 TODO 的實作端會建錯簽名、讓 E2 回潮。v5 同步。 |

### 🔴 收斂斷路器：本輪之後不再開全輪 review

依 `feedback_epic_convergence_breaker`（兩輪斷路器套 epic **整體收斂趨勢**）與
`feedback_95_percent_then_record`（95% 解法就收、殘留具名記錄、不當阻擋）：

| 輪 | 群集數 | P0 | P1 | 性質 |
|---|---|---|---|---|
| R1 | 13 | 3 | 6 | 設計缺口（投影無落點、三態誤述、summary 丟欄） |
| R2 | 11 | 3 | 6 | 設計缺口＋介面自相矛盾 |
| R3 | 7 | 0 | 2 | **一個**設計缺口（答案窗 purge 被刪） |
| R4 | 4 | 0 | 3 | **純文字精確度**——三條都由 codex 直接給出可落地式子 |

P0 已連續兩輪清零；R4 的三條 P1 沒有一條是「要再想一想」，全是「照這個式子寫上去」。
⇒ 套用 v5 後**直接進 B1**。B1 只做文件、枚舉與既有紅 nodeid 清單（**不動生產碼**），
且 B2b 開工前還有一次該批的 code review 可再驗這些契約。

**具名殘留 `SU-RESID-2`（needs-research）**：多 TF 之 `(event_id, timeframe)` 複合鍵。
本票以「每事件恰一個 selected per_tf row，否則 raise」fail-closed，不在此解。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P1-01
**斷言**: E1 尚未閉合：`label_end_ms >= test_start_ms` 只在 test plan 非空且 source-bar endpoint 已有可驗證輸入時可實作；v4 同時允許 `test_start_ms=None`，又要求投影檢查 source bars，但投影簽名沒有 bars/endpoint universe。
**碼證**: `sed -n '112,118p' momentum/Analysis/event_samples/event_split.py` → 現行 guard 為 `label_end_ms > test_start - embargo`；`sed -n '19,41p' momentum/core/split_preview.py` → test rows 起點為 `split_point + purge_gap + embargo`；SPEC C-4:175-203、TODO:164-185；`types.py:55-60` 的 EventManifest 僅 table/summary/policy，`alignment.py:197-213` 才持有 bars endpoint。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0; docs/SPLITUNIFY_TODO.md#cd95ee642a9e; momentum/core/split_preview.py#6b6a1d95c5cc; momentum/Analysis/event_samples/types.py#8ba12e1b5204; momentum/Analysis/event_samples/alignment.py#0da3c48b2668
[BLOCKING] 信心度=High。可直接實作的 canonical 式子是：`train_cutoff = feature_cutoff_ms ∈ as_ms(feature_index[train_plan.row_index])`；非空 test plan 時，`train_cutoff and label_end_ms >= as_ms(feature_index[test_plan.row_index[0]])` ⇒ purge（`>=` 必須保留）。`purge_gap`/`embargo` 是 row 單位且已包含在 test row 起點，不得再以毫秒相減；test rows 為空應先 fail-closed/轉 event-study-only，不能與 None 比較。另須傳入 source endpoint receipt/index，或明定上游驗證為可證明前置條件。
## CODEX-R4-P1-02
**斷言**: E2 的六欄與 `event_id` 單鍵仍不足以閉合多 TF provenance，且 v4 沒指定 `event_keys` 的產生者與批次；`manifest.table` 的 timeframe 不能代替 per-TF feature cutoff 的 timeframe。
**碼證**: `nl -ba momentum/Analysis/event_samples/alignment.py | sed -n '197,213p;237,242p'` → `receipts.per_tf` 每 `(event_id, sub_tf)` 可多列、`feature_cutoff_ms` 在 per_tf；`nl -ba .../dedupe.py | sed -n '39,49p;101,120p'` → manifest 依 label_start/event_id 重排且只 merge trigger `timeframe`；`types.py:37-40,55-60` → event_level/per_tf 分離、manifest 無 cutoff。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0; docs/SPLITUNIFY_TODO.md#cd95ee642a9e; momentum/Analysis/event_samples/alignment.py#0da3c48b2668; momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e; momentum/Analysis/event_samples/types.py#8ba12e1b5204
[BLOCKING] 信心度=High。B2b 應新增具名 helper 產生 `event_keys`：由 `receipts.event_level`（id/label/symbol/trigger context）與 `receipts.per_tf` 按 `event_id + 明示 selected feature timeframe` keyed join，並帶 endpoint receipt；B3 只傳遞，不在接線處臨時組裝。若保留 `event_id` 單鍵，必須要求每事件恰一個 selected per_tf row；若允許多 TF，鍵與輸出契約須改成 `(event_id, timeframe)`，否則會靜默錯配。
## CODEX-R4-P1-03
**斷言**: Task 3.1 的 embargo raise 指令引用不存在的 config 欄位層級，實作端照字面會漏 guard 或在 pipeline 直接 AttributeError。
**碼證**: `nl -ba momentum/Analysis/event_samples/pipeline.py | sed -n '31,45p'` → `EventPipelineConfig` 只有 `split: EventSplitConfig`；`types.py:64-83` → `embargo_ms`/`embargo_ms_by_symbol` 在 `EventSplitConfig`；SPEC:480、TODO:273 卻寫 `config.embargo_ms`。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0; docs/SPLITUNIFY_TODO.md#cd95ee642a9e; momentum/Analysis/event_samples/pipeline.py#f78eae8df0f6; momentum/Analysis/event_samples/types.py#8ba12e1b5204
[BLOCKING] 信心度=High。Task 3.1 應明寫事件 pipeline caller 的 `config.split.embargo_ms is None and config.split.embargo_ms_by_symbol is None`；IC orchestrator 的 `_build_holdout_split_plan` 收的是 `ICConfig`，不得把同一 assert 無條件套到該 caller。
UNVERIFIED_ASSUMPTIONS: `test_start_ms` 永遠非 None、六欄唯一描述單一 feature TF、上游 endpoint 驗證可由投影推知；均未成立或未被 v4 明定，已由 P1-01/P1-02 覆蓋。
## COMPOSER-R4-P2-01

**斷言**: TODO Task 2.2 之輸入／輸出仍寫 `event_index`，與 v4 SPEC C-4 之 `event_keys: pd.DataFrame` 及實作要點 3／4 互斥，B2b 實作端若只讀 TODO 會建錯簽名。

**碼證**: SPEC C-4:156-164 簽名為 `event_keys: pd.DataFrame`（六欄契約 `:167-169`）；TODO Task 2.2:178 仍寫 `(train_plan, test_plan, event_index, feature_index, …)`；同段:188-197 混用 `event_keys` 與「`event_index` 語意＝ feature_cutoff」。RECHECK: `rg -n 'event_index|event_keys' docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md | head -30`

**來源摘要**: docs/SPLITUNIFY_SPEC.md#384aa22961d0, docs/SPLITUNIFY_TODO.md#cd95ee642a9e

[MAJOR] 信心度=High；不擋 B1（SPEC 為準且已正確），但 B2b 開工前須把 TODO:178/196 改為 `event_keys` 並刪除 `event_index` 殘文，否則介面掃描會再紅一輪。修法：TODO Task 2.2 輸入行與 SPEC C-4 簽名逐字對齊。

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

