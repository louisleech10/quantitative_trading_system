# SPLITUNIFY consult R1 — COMPOSER

task-id: 20260910-SPLITUNIFY-X-CONSULT-R1  
family: COMPOSER  
brief: `handoffs/20260910-SPLITUNIFY-CONSULT-BRIEF.md`

## 被當成事實的未驗證假設（§0）

| 假設 | 作者標記 | 判定 | 理由 |
|---|---|---|---|
| 時間切分隔離語意嚴格強於事件切分緩衝 | assumed（brief L88–89） | **未成立** | 兩軸不同：K 線 `purge_gap`+`embargo`（rows）vs 事件 `label_end_ms` 跨界 purge（ms）；不可直接比較「誰更嚴」 |
| 統一後多 symbol 批數值不變 | assumed（brief L92–93） | **未成立** | IC 路徑 `symbol=next(iter(allowed_symbols))` 單幣 holdout vs `split_events` 逐 symbol `test_fraction`；31 vs 33 即此分歧 |
| EVTLABEL Task 3.4 已使時間切分成「全平台唯一權威」 | fact-verified 部分成立 | **僅 IC selection scope** | `test_timestamps` 交集只餵 `_resolve_effective_label_mode`；GAP-3 匯入管線 `pipeline.run()` 仍獨立呼叫 `split_events()`（L691） |

---

## COMPOSER-R1-P0-01

**斷言**: 若直接把「全域 scalar `SplitPlan.test_timestamps` 交集」當唯一邊界、且 IC 主線維持 `next(iter(allowed_symbols))` 單幣 holdout，多 symbol 批之驗證段成員**必變**——與 brief 實測 31 vs 33 同型，不可宣稱「只改型別」。

**碼證**: `ic_filter_orchestrator.py:1248` `symbol = next(iter(allowed_symbols))`；`_build_holdout_split_plan`（`:561–631`）對**單一** K 線表做 `holdout_test_row_index`；`event_split.py:78–117` 逐 symbol 以 `test_fraction` 切 `decision_at_ms` 邊界。RECHECK: `grep -n 'next(iter(allowed_symbols))' momentum/Analysis/ic_filter_orchestrator.py`；讀 `event_split.py:106–117` 與 `_build_holdout_split_plan` 並列比對。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7

[BLOCKING] 信心度=High。統一方向可以時間切分為 canonical，但**最小落地必二選一且寫死**：(A) 多 symbol 批 **fail-closed**（與現 IC 單幣前提一致，UI 明示）；或 (B) 用 `split_per_symbol`（`contracts.py:625–684`）逐 symbol 建 `SplitPlan`，再逐 symbol 投影事件——禁止用全批 scalar 冒充 per-symbol（`CODEX-R1-P1-02` 禁令）。

---

## COMPOSER-R1-P1-01

**斷言**: brief 把「時間切分 purge/embargo 較強」當支持理由，但作者自己標 **assumed 且未跑否證**——在 interval-aware 事件 purge（`label_end_ms > test_start - embargo`）下，存在「事件 purge 擋住、K 線 rows purge 未等價覆蓋」的語意差，不能當已驗 fact 支撐 1a。

**碼證**: brief L88–89「assumed…我跑了：**沒跑**」；`event_split.py:114–115` interval 跨界 purge；`contracts.py:602–612` train 對 test 的 rows forbidden interval。RECHECK: 讀 brief L88–89 與上述兩段 purge 實作。

**來源摘要**: handoffs/20260910-SPLITUNIFY-CONSULT-BRIEF.md#d45d71164f56

[MAJOR] 信心度=High。1a 仍可選「時間切分為 canonical」，但 SPEC 須寫明：**權威來自單一 K 線切分 + 事件投影**，不是「時間 purge 嚴格包含事件 purge」；§G 需雙軌 golden（同一 fixture 下事件 membership + purge 列數）。

---

## COMPOSER-R1-P1-02

**斷言**: 提案「只做 test_timestamps 交集投影」不足以保留 `EventSplitPlan` 下游所需之 **clusters / summary.degraded / purged**——這些是語意產物，不是 SplitPlan 欄位可映射。

**碼證**: `event_split.py:126–158` 產 `clusters`（time_cluster_id、cluster_weight）與 `summary.degraded`；`tables.py:351–359` `binary_discrimination_table` 用 clusters 算 macro/micro AUC；`tables.py:130–138` `_common_constraint_block` 讀 `summary.degraded` 決定 `formal_pooled_inference_allowed`。RECHECK: `grep -n 'clusters\|degraded' momentum/Analysis/event_samples/tables.py`。

**來源摘要**: momentum/Analysis/event_samples/event_split.py#fde5a520c319

[MAJOR] 信心度=High。落地步驟須拆成：**(1)** canonical `SplitPlan`(s) → test 段時間戳；**(2)** `derive_event_split_plan(manifest, test_timestamps_by_symbol, embargo_ms_by_symbol)` 重算 assignments/purged/clusters/summary——`split_events` 邊界邏輯改為「投影 + 重算附屬結構」，不是刪除 `EventSplitPlan` 型別。

---

## COMPOSER-R1-P1-03

**斷言**: 統一後下列消費者會因驗證段成員改變而**改變數值**（非純 refactor）——brief 必答 3b 須具名。

**碼證**: 五處消費 test 成員：`baseline.py:105–110`（OOS AUC test_ids）、`tables.py:305–307`（辨別表）、`pattern_bridge.py:114–188`（train/test 切分+test 報告）、`pipeline.py:696–698`（summary n_test）、`ic_filter_orchestrator.py:3830–3873`（imported_binary selection 正負例）。RECHECK: 同一多 symbol fixture 比對現行 split_events vs 投影後上述輸出。

**來源摘要**: momentum/Analysis/event_samples/baseline.py#38c7ec473653

[MAJOR] 信心度=High。SPEC §G 須 byte-level 或 aggregate golden 覆蓋這五處；mutation 至少一條「投影邊界被 monkeypatch 成舊算術必紅」。

---

## COMPOSER-R1-P2-01

**斷言**: GAP-3 原 SPEC/TODO 已 FROZEN——改切分語意只能走**延伸檔**，不得解凍 `docs/GAP3_EVENT_UX_SPEC.md` 本體；下一編號應為 **D-002**（D-001 已被 G3-D2 佔用）。

**碼證**: `docs/ROADMAP.md` GAP-3「SPEC＋TODO 皆 FROZEN」；`Glob docs/GAP3_EVENT_UX_SPEC.D-*.md` 現僅 `D-001.md`。RECHECK: `ls docs/GAP3_EVENT_UX_SPEC.D-*.md`。

**來源摘要**: docs/ROADMAP.md#9a2de072a7ab

[MAJOR] 信心度=High。延伸檔範圍：`§D-3′` 切分權威、`EventSplitPlan` 投影契約、多 symbol 政策、§G golden、UAT 新增「兩表 n_test 一致」項——**不**改 B1.3 以外已 CLOSED 批次語意。

---

## COMPOSER-R1-P2-02

**斷言**: 平台存在**雙入口**各自產切分——只改 IC 路徑不足以消除 UAT「兩個驗證段數字」；`EventSamplePipeline.run()` 仍無條件 `split_events()`，與 IC `split_context` 未接線。

**碼證**: `pipeline.py:691` `plan = split_events(...)`；`ic_feed.py:6–14` 分析鏈不經 ic_feed、走 `ic_analysis_service`；`ic_filter_orchestrator.py:1290–1298` 只建 IC 側 `test_timestamps`。RECHECK: `grep -n 'split_events' momentum/Analysis/event_samples/pipeline.py`。

**來源摘要**: momentum/Analysis/event_samples/pipeline.py#f78eae8df0f6

[MAJOR] 信心度=Medium。最小落地須新增**單一 pure 函式**（建議 `momentum/core/split_preview.py` 同檔或 `event_samples/split_derive.py`）供 orchestrator 與 pipeline 共用；API 報告只暴露 **一組** canonical `n_test` + `split_authority=time_holdout` 揭露欄。

---

## Verdict：需修補後派工（方向可執行，但 P0-01／P1-02 須寫進 SPEC 才能動工）

**1a. 統一方向**：**以時間切分（`SplitPlan` / K 線 holdout + purge/embargo）為 canonical 權威**；`EventSplitPlan` 降為**投影容器**（assignments/purged/clusters/summary 由 canonical 邊界衍生），與 brief 提案同向，但**禁止** scalar 全批投影替代 per-symbol。

**1b. 最小落地步驟**（第一批只讀＋純函式，第二批改 caller）：
1. **寫** `docs/SPLITUNIFY_SPEC.md` + `docs/GAP3_EVENT_UX_SPEC.D-002.md`（切分權威／投影契約／§G）。
2. **新增** `derive_event_split_plan_from_holdout(...)`（pure）：輸入 manifest + per-symbol `SplitPlan` test 時間戳 + `embargo_ms_by_symbol`；輸出完整 `EventSplitPlan`（含 clusters 重算）。
3. **改** `ic_filter_orchestrator._build_holdout_split_plan` 呼叫端：多 symbol ⇒ `split_per_symbol` 或 fail-closed（SPEC 二選一寫死）。
4. **改** `pipeline.py:691`：改呼叫 derive，不再獨立 `split_events` 邊界算術。
5. **只讀** `baseline.py`／`pattern_bridge.py`／`tables.py`：簽名不變，吃新 plan。
6. **測試** `tests/momentum/event_samples/test_*` + 新 golden「IC n_test == pipeline n_test」。

**2a. 多 symbol 等價？** **否**（在現 IC 單幣 holdout 前提下）。**判準**：同一 manifest，逐 symbol 投影後 Σ n_test 與 IC report `split_mask.test_rows`（事件列）一致；不一致 ⇒ fail-closed，不得靜默取第一個 symbol。

**2b. `SplitPlan` per-symbol 化？** **是**——用既有 `split_per_symbol`（`contracts.py:625`），每 symbol 一份 train/test plan；事件投影逐 symbol 做，再 merge assignments（禁止跨 symbol 共用 scalar test_start）。

**3a. 依賴分類**：
| 檔 | 語意依賴（不可只換型別） | 型別/投影可換 |
|---|---|---|
| `baseline.py` | test 事件集合 | 參數型別仍 `EventSplitPlan` |
| `pattern_bridge.py` | train/test 事件 ID 集；receipt 內 `SplitPlan` 為 row_id 包裝 | `_split_plans()` 可保留 |
| `tables.py` | clusters、degraded、test_ids | manifest 結構不變 |
| `ic_feed.py` | 匯入表格鏈仍可能獨立 split（短期） | 長期應收斂到 derive |
| `pipeline.py` | summary `n_test` 為使用者可見數字 | config 形狀不變 |

**3b. 會改變數值的消費者**：見 **COMPOSER-R1-P1-03**（五函式具名）。

**4a. GAP-3 FROZEN 怎麼走？** **延伸檔**，不解凍原 SPEC。

**4b. 延伸檔**：`docs/GAP3_EVENT_UX_SPEC.D-002.md`（切分統一）；配套 `docs/SPLITUNIFY_SPEC.md` + `docs/SPLITUNIFY_TODO.md`（新 epic，不併入 EVTLABEL）。

**5a. 兩套保留、標主從？** **否，優於統一的唯一理由不存在**。代價＝UAT/報告永遠並列兩個 n_test、使用者無法判斷結論依據；維護兩套算術必再漂（B3 `split_preview` 事故重演）。

**5b. 一句話**：**K 線 holdout（per-symbol `SplitPlan`）為唯一邊界來源，事件側只做投影與 cluster 重算，報告只准一個驗證段數字。**

**6. 票大小**：**大**（命中 a 數值/洩漏、b 跨模組、c 多 phase、d 切分正確性）。建議 **4 批**：① SPEC+D-002+consult reconcile ② derive 純函式+golden ③ pipeline+orchestrator 接線 ④ 前端/API 揭露欄+UAT 項；每批三家 review。

**若三家分歧，收斂判準（看碼證不數人頭）**：以 **`split_preview.holdout_test_row_index` 與 `_build_holdout_split_plan` 逐字同型** + **per-symbol `groupby` 證據**（`event_split.py:78`）為準；任何方案若不能機械證明「同一 fixture IC 與 pipeline 的 test 事件集合相等」，採 **fail-closed** 版本。

---

STATUS: DONE
