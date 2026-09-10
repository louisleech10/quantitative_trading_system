# Reconcile — 20260910-splitunify-x-consult-r1

**來源** 20260910-splitunify-x-consult-r1-codex.md, 20260910-splitunify-x-consult-r1-composer.md, 20260910-splitunify-x-consult-r1-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**這是設計 consult，不是 code review。** 使用者 2026-09-10 裁定「切法由 Claude 與委員會定共識」，
並於今晚離線時指示「有問題找委員會討論共識」⇒ 本結論**直接進 SPEC**，不再等使用者點頭。

19 條 findings 群集為五個決議項。三家在**方向**上一致、在**做法**上一致否決我 brief 的字面提案。

### D1 — 統一方向：時間切分為 canonical 權威（三家一致，與我的提案同向）
- findings：`CODEX-R1-P1-02`、`COMPOSER-R1-P1-01`、`GROK-R1-P1-01`
- **決議**：K 線 holdout（`SplitPlan`，含 purge／embargo）為**唯一邊界來源**；
  `EventSplitPlan` 降為**投影容器**，不再自行決定邊界。
- 理由（三家共同）：隔離語意（purge／embargo）住在時間切分那一側；事件側只有緩衝 bars，較弱。

### D2 — 🔴 但**否決**我 brief 的字面做法：不得以全域 scalar `test_timestamps` 交集取代
- findings：`CODEX-R1-P0-01`、`COMPOSER-R1-P0-01`（**兩家各自標 P0**）、`GROK-R1-P1-02`
- 兩家獨立指出：全批 scalar 交集會**改變驗證段成員**，並可能以第一個 symbol 的 holdout
  冒充整批邊界（`next(iter(allowed_symbols))`）——這是資料品質／OOS 語意問題，不是型別重構。
- 🔴 **我自己實跑證實了這一點**（`handoffs/20260910-probe-splitunify-multisymbol.py`，
  receipt `20260910T150504Z-splitunify-multisymbol`）：兩 symbol 交錯之 80 列批次，
  全域切法測試段 12 列、per-symbol 切法 8 列，**4 列只在全域**。
  我在 brief 把「統一後多 symbol 數值不變」列為 `assumed`／「沒跑」——**被自己的探針推翻**。
- **決議**：邊界必須 **per-symbol**（`split_per_symbol` 已存在）；多 symbol 批在 per-symbol
  投影完成前 **fail-closed**（grok），不得以 scalar 冒充。

### D3 — 投影是**三態**不是二態（grok 提出，另兩家不反對）
- findings：`GROK-R1-P1-02`、`GROK-R1-P2-01`
- 我原本只講「與 `test_timestamps` 交集」＝二態（在／不在測試段）。
- **決議**：投影須用 train 與 test **兩個 plan** 導出 **train／purged／test 三態**——
  落在隔離區（purged）的事件既不屬訓練也不屬驗證，二態會把它們錯誤地歸進其中一邊。

### D4 — GAP-3 走延伸檔，不解凍原檔（三家一致）
- findings：`CODEX-R1-P1-04`、`COMPOSER-R1-P1-03`、`GROK-R1-P2-02`
- **決議**：新增 `docs/SPLITUNIFY_SPEC.md`＋`docs/GAP3_EVENT_UX_SPEC.D-002.md`（切分權威／投影契約／§G）。

### D5 — 票大小與批次（三家一致「大」；批數 3–4，取較保守之 4）
- findings：`CODEX-R1-P2-06`、`COMPOSER-R1-P2-02`、`GROK-R1-P2-04`
- **決議**：**大票**（命中 (a) 數值／洩漏、(b) 跨模組、(c) 多 phase、(d) 切分正確性）。
  四批：① SPEC＋D-002＋本 reconcile ② derive 純函式＋golden ③ pipeline／orchestrator 接線
  ④ API／前端單一驗證段揭露＋UAT 項。每批三家 review。
- 報告只暴露 canonical 之 `n_test`，並附 `split_authority`、boundary hash、per-symbol counts
  與 fail-closed reason（codex）。

### 我方前提之驗證結果
- `assumed`「時間切分之隔離嚴格強於事件緩衝」：三家未反駁，方向被採納。
- `assumed`「統一後多 symbol 數值不變」：**被我自己的探針推翻**（見 D2），且兩家各自標 P0。

**Verdict**: 需修補後派工——方向（D1）採納，但**我 brief 的字面做法被否決**（D2／D3）：
邊界須 per-symbol、投影須三態、多 symbol 未支援前 fail-closed。
四批走完、每批三家 review；GAP-3 走 D-002 延伸檔，不解凍原檔。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01

**斷言**: 把全批 scalar `SplitPlan.test_timestamps` 直接交集給多 symbol 事件，會改變驗證段成員，並可能以第一個 symbol 的 IC holdout 冒充整批邊界；這是資料品質／OOS 語意的阻擋問題，不是型別重構。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:1248` 目前以 `symbol = next(iter(allowed_symbols))` 建單一 symbol holdout；`momentum/Analysis/event_samples/event_split.py:78-117` 逐 symbol 依事件時間與 `test_fraction` 判定 train/test/purge；`momentum/core/contracts.py:625-694` 已有 per-symbol `split_per_symbol()`。VERIFY：`venv/bin/python handoffs/20260910-probe-splitunify-multisymbol.py` → `全域=12`、`per-symbol=8`、`只在全域=4`、`DISPROVED`、命令 rc=1（否證條件成立）。RECHECK：重跑同命令，並比較同一 manifest 的每 symbol `event_id` test 集合，不得只比較總數。

**來源摘要**: `momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7`；`momentum/Analysis/event_samples/event_split.py#fde5a520c319`；`momentum/core/contracts.py#642aecf26b32`；`handoffs/20260910-probe-splitunify-multisymbol.py`（其 run receipt：`handoffs/run_receipts/20260910T150504Z-splitunify-multisymbol.json`）。

[BLOCKING] 信心度=High。共識方案必須支援 per-symbol projections：建立一個以時間為語意的 canonical boundary，對每個 symbol 物化 train/test `SplitPlan`；禁止 `next(iter(...))`、合併 row count scalar 或單一 `test_start` 取代 symbol map。若任一 symbol 無法形成合法 train/test 或其事件投影與 canonical row test 集不相等，必須 fail-closed 並揭露 symbol/reason。

## CODEX-R1-P1-02

**斷言**: brief 把「時間切分隔離語意嚴格強於事件切分緩衝」當成方向依據尚未被證明；兩套隔離不是同一個集合，不能在 SPEC 中宣稱其中一套必然涵蓋另一套。

**碼證**: `event_split.py:82-115` 以每 symbol 的 `decision_at_ms`、`label_end_ms`、毫秒 `embargo` 判定事件 purge；`contracts.py:602-612` 以 symbol-local ordinal 對 row-level test range 套 `purge_gap`/`embargo`；`ic_filter_orchestrator.py:570-585` 又以 `max(effective_horizon, event_window_rows)` 產生 row purge。VERIFY：`venv/bin/python -m pytest tests/momentum/event_samples/test_event_split.py tests/momentum/event_samples/test_baseline_oracle.py tests/momentum/event_samples/test_pattern_bridge.py tests/momentum/event_samples/test_tables.py -q` → `37 passed in 8.75s`；這證明現有各自 guard 的行為，而非證明兩種 purge 集合互為包含。RECHECK：用同一份真實 kline／事件 manifest 同時輸出 row forbidden intervals、event purged IDs、test feature-cutoff IDs，逐項做集合比較。

**來源摘要**: `handoffs/20260910-SPLITUNIFY-CONSULT-BRIEF.md#d45d71164f56`；`momentum/Analysis/event_samples/event_split.py#fde5a520c319`；`momentum/core/contracts.py#642aecf26b32`；`momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7`。

[MAJOR] 信心度=High。1a 可以採時間語意，但理由應改成「所有 row/event projections 共用同一 canonical boundary」，不是「時間 purge 比事件 purge 強」。§G 必須同時 golden：逐 row test fingerprint、逐 event assignments/purged IDs、answer-window 完整性與 leakage negative case；未證明 containment 前不得刪除任一既有 guard。

## CODEX-R1-P1-03

**斷言**: `EventSplitPlan` 不能只被替換成 `SplitPlan.test_timestamps` 或單純型別 alias；`assignments`、`purged`、`clusters`、`summary.degraded` 都是下游仍消費的事件語意，必須由 canonical boundary 重新導出。

**碼證**: `event_split.py:123-158` 產出 assignments、purged、time-cluster weights 與 degraded/LOSO summary；`baseline.py:105-110` 取 test event IDs；`pattern_bridge.py:114-175` 取 train/test event IDs 並建立 row-id `SplitPlan`；`tables.py:305-367` 取 test IDs、clusters、macro/micro AUC 與 cluster CI；`tables.py:130-150` 由 summary 決定 `formal_pooled_inference_allowed`。VERIFY：同一 targeted pytest 命令 → 37 tests 全部 PASSED，包含 event split、baseline、pattern bridge、discrimination/table cases。RECHECK：移除任何一個 assignments/purged/clusters/summary 欄位後，對應 test 應 fail-closed，而不是以空容器或全樣本回退。

**來源摘要**: `momentum/Analysis/event_samples/types.py#8ba12e1b5204`；`momentum/Analysis/event_samples/event_split.py#fde5a520c319`；`momentum/Analysis/event_samples/baseline.py#38c7ec473653`；`momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2`；`momentum/Analysis/event_samples/tables.py#b80c15cf206d`。

[MAJOR] 信心度=High。最小落地不是刪除 `EventSplitPlan`，而是新增一個 pure projection（暫定放在 `momentum/Analysis/event_samples/event_split.py`）：輸入 canonical boundary、每 symbol test timestamps、事件 feature-cutoff 對映與答案窗；輸出完整 EventSplitPlan。clusters/weights 仍由事件列重算，summary 的 degraded/LOSO 狀態仍要明確揭露；空 plan 不能冒充未切分。

## CODEX-R1-P1-04

**斷言**: 只修改 IC orchestrator 不會消除雙驗證段；事件 pipeline 有獨立 split producer，而且它目前沒有 IC feature row universe，不能自行重算一份「看似相同」的邊界。

**碼證**: `momentum/Analysis/event_samples/pipeline.py:683-705` 的 `EventSamplePipeline.run()` 無條件在 `:691` 呼叫 `split_events()`；`ic_filter_orchestrator.py:1290-1298` 只建立 IC 端 `test_timestamps`；`ic_feed.py:6-18` 明載匯入表格鏈不是 IC 分析鏈。VERIFY：`rg -n -C 2 'split_events|test_timestamps|next\(iter\(allowed_symbols\)\)' momentum/Analysis/event_samples/pipeline.py momentum/Analysis/ic_filter_orchestrator.py` → 同時命中 `pipeline.py:691`、`orchestrator.py:1248`、`:1298`。RECHECK：同一 run 同時記錄 pipeline 與 IC 的 canonical test event-ID hash；不得只比 `n_test`。

**來源摘要**: `momentum/Analysis/event_samples/pipeline.py#f78eae8df0f6`；`momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7`；`momentum/Analysis/event_samples/ic_feed.py#741f697b3964`；`momentum/core/split_preview.py#6b6a1d95c5cc`。

[MAJOR] 信心度=High。單一來源應是 core 的 pure temporal-boundary builder（可沿用並擴充 `momentum/core/split_preview.py` 的「同一算術、無副作用」定位），由 orchestrator 與 pipeline 共同呼叫；pipeline 必須接收該 boundary/feature universe，沒有 canonical feature universe 的獨立匯入流程則只能明示 event-study-only，不得按事件數另切並宣稱 OOS。這是接線缺口，不能靠 consumer 讀同一個型別解決。

## CODEX-R1-P1-05

**斷言**: 統一會改變實際數值與 capability 判定，至少影響 baseline、辨別表、pattern bridge 與 imported-binary selection；因此本票不是「只換 EventSplitPlan 型別」的重構。

**碼證**: `baseline.py:118-161` 的 `n_test`、prevalence、AUC/PR-AUC、permutation band、BH-FDR 取 test IDs；`tables.py:305-370` 的 OOS metrics、macro/micro AUC、cluster CI 取 test IDs/clusters；`pattern_bridge.py:122-218` 的 train/test IDs 決定 fit rows、rules、scores、lift、receipt hash；`ic_filter_orchestrator.py:3830-3863` 的 test intersection 會改 `n_pos/n_neg`，進而改 `label_mode`、raise 或 return-rule。VERIFY：targeted pytest 命令 → 37 passed，現行 positive/negative/one-class/fit-scope guard 均綠；這不宣稱改後數值不變。RECHECK：同一真實 kline fixture＋事件 manifest，對改前後輸出做逐 event ID 集合、逐列 train/test fingerprint、報告 numeric keys 與 capability reason 的 exact/tolerance diff。

**來源摘要**: `momentum/Analysis/event_samples/baseline.py#38c7ec473653`；`momentum/Analysis/event_samples/tables.py#b80c15cf206d`；`momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2`；`momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7`。

[MAJOR] 信心度=High。SPEC §G 必須把上述四條鏈列為數值受影響 consumer，新增 real-kline golden 與 negative mutation（將 canonical projection 偷換回舊事件算術時必紅）。`event_forward_return_table()` 本身主要用 manifest 全事件與 clusters；若 clusters 保持相同，其 return cells 可保持，但 `common`、CI 或切分揭露仍須逐欄對證，不能把它籠統標為「不受影響」。

## CODEX-R1-P2-06

**斷言**: GAP-3 已 frozen，本設計必須走 D 延伸檔；目前 frozen primary 與 UX extension convention 的路徑字面不一致，若不先寫清楚會讓派工時選錯規格入口。

**碼證**: `docs/GAP3_EVENT_SPEC.md:3` 寫 frozen 後續走 `docs/GAP3_EVENT_SPEC_AMENDMENTS.md`，但該檔目前不存在；`docs/GAP3_EVENT_UX_SPEC.md:3` 指向 D-001，且 `docs/GAP3_EVENT_UX_SPEC.D-001.md` 已存在。VERIFY：`rg --files docs | rg 'GAP3_EVENT_UX_SPEC\.D-'` → 只見 `D-001.md`；`if [ -e docs/GAP3_EVENT_SPEC_AMENDMENTS.md ]; then ...; else echo absent; fi` → `absent`。RECHECK：新 SPEC/TODO 產出後以 `rg -n 'D-002|GAP3_EVENT_SPEC_AMENDMENTS' docs handoffs` 對證唯一入口，並由 reconcile stamp 核可。

**來源摘要**: `docs/GAP3_EVENT_SPEC.md#544c2922ef2e`；`docs/GAP3_EVENT_UX_SPEC.md`；`docs/GAP3_EVENT_UX_SPEC.D-001.md`。

[MINOR] 信心度=High。沿 brief 指定的 D-00N 慣例，下一個 extension 應定名 `docs/GAP3_EVENT_UX_SPEC.D-002.md`；另建 `docs/SPLITUNIFY_SPEC.md` 與 `docs/SPLITUNIFY_TODO.md` 作為本票唯一施工契約。不得解凍或就地改 `docs/GAP3_EVENT_SPEC.md`／`docs/GAP3_EVENT_UX_SPEC.md`；新文件需明載它們與 primary frozen text 的關係，並在第一批審查解決上述缺路徑字面。

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

## GROK-R1-P1-01

**斷言**: brief 提案若依字面「只以 `SplitPlan.test_timestamps` 交集出驗證段事件、其餘當 train」實作，會把決策時刻落在 purge／embargo 隔離帶的事件標成 train，形成 look-ahead／標籤重疊洩漏。

**碼證**: `momentum/core/split_preview.py` `holdout_test_row_index`：`test_rows = arange(split_point + purge_gap + embargo, n_rows)`，train 為 `arange(0, split_point)`——中間帶不在任一側。`ic_filter_orchestrator.py:1298` 之 `test_timestamps` **只**含 test 側。`event_split.py:114-117` 現行三態含 purge（`interval_crosses_split_boundary`）。合成：`split_point=70,purge=12` ⇒ 帶 70–81；naive `not in test ⇒ train` 會吞下該帶。RECHECK：對投影函式 mutation——強制把隔離帶事件標 train ⇒ 新測試必紅。

**來源摘要**: handoffs/20260910-SPLITUNIFY-CONSULT-BRIEF.md#d45d71164f56; momentum/core/split_preview.py#6b6a1d95c5cc; momentum/Analysis/event_samples/event_split.py#fde5a520c319; momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7

[MAJOR] 信心度=High。會怎麼失敗：OOS 訓練集混入答案窗與測試段重疊之事件 ⇒ AUC／規則偏樂觀。修法：SPEC 寫死三態投影（Verdict 步驟 1）；禁止二態捷徑；mutation 守門。

---

## GROK-R1-P1-02

**斷言**: 「時間切分隔離語意嚴格強於事件切分緩衝」在 brief 被當理由，但是未驗證假設；兩者切軸不同，不存在全情境支配關係——採時間準繩應改寫為「單一權威＋與 Task 3.4 對齊」，而非隔離強度全序。

**碼證**: 事件路徑 `event_split.py:106-117` 以**每 symbol 事件計數** `floor(n*(1-test_fraction))` 定 `test_start`，再以 `label_end_ms` vs `test_start-embargo` 做 interval purge。時間路徑 `_build_holdout_split_plan`（`:561-631`）以**K 線列數** `oos_test_size`＋bars `purge/embargo` 切。合成探針：同 40 事件偏斜密度 ⇒ event-fraction test=12、time+purge 投影 test=18（only_time=82..87）。作者自承「沒跑、只讀欄位」。RECHECK：重跑本檔「本輪實跑」表兩探針。

**來源摘要**: handoffs/20260910-SPLITUNIFY-CONSULT-BRIEF.md#d45d71164f56; momentum/Analysis/event_samples/event_split.py#fde5a520c319; momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7

[MAJOR] 信心度=High。會怎麼失敗：SPEC §A 把假設寫成事實 → 實作者誤刪事件側仍較嚴的 interval 檢查、或爭論方向時用錯判準。修法：§A 改寫採納理由；投影仍須覆蓋隔離帶（見 P1-01）。

---

## GROK-R1-P1-03

**斷言**: 多 symbol 批上，「全域時間切分 ∩ 事件」與現行 per-symbol `split_events` **成員不等價**；若統一時用單一 scalar `SplitPlan` 投影全批，違反 per-scope 語意且改變驗證段。

**碼證**: `event_split.py:78` `groupby("symbol")` 各自切。`SplitPlan` 雖有 `symbol` 欄（`contracts.py:390`），但 `analyze` 主路徑 `:1248` `symbol = next(iter(allowed_symbols))` 建**單** plan。`venv/bin/python /private/tmp/probe_split.py` → 合併 80 列、全域 test=12、per-symbol test=8、只在全域=4，stdout `DISPROVED` rc=1。RECHECK：重跑該探針；或對兩 symbol 交錯時鐘事件批比較 assignments。

**來源摘要**: /private/tmp/probe_split.py#ba187c89638d; momentum/Analysis/event_samples/event_split.py#fde5a520c319; momentum/core/contracts.py#642aecf26b32; momentum/Analysis/ic_filter_orchestrator.py#1eb5824cf5e7

[MAJOR] 信心度=High。會怎麼失敗：跨標的批 OOS 集合被另一標的的時間密度拖移；formal pooled 推論基線漂移。修法：`n_symbols>1` 無 per-symbol plans ⇒ fail-closed；支援＝`split_per_symbol`（`:625`）後逐標投影。

---

## GROK-R1-P2-01

**斷言**: 統一後 `baseline`／`pattern_bridge`／`tables` 的 OOS 數值**會變**（不是型別重命名）；SPEC 必須把「接受重基線」寫成顯式驗收，禁止以「行為不變」或舊 golden 擋投影。

**碼證**: `baseline.py:105-108` test_ids←assignments；`pattern_bridge.py:125-127,155-188` train 擬合／test 評分；`tables.py:305-306` 同。成員探針 12 vs 18 ⇒ 同一特徵向量進 OOS 計算的列集合不同。RECHECK：同一 fixture 上舊 `split_events` vs 新投影之 `test` event_id 集合 diff 非空＋AUC 差值記錄進 receipt。

**來源摘要**: momentum/Analysis/event_samples/baseline.py#38c7ec473653; momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2; momentum/Analysis/event_samples/tables.py#b80c15cf206d

[MINOR] 信心度=High。會怎麼失敗：實作者為保舊 golden 而加相容分支 ⇒ 兩套邊界殘留。修法：TODO 列「故意破舊 golden／重錄」；UAT 數字以時間投影為唯一公佈值。

---

## GROK-R1-P2-02

**斷言**: `EventSplitPlan.clusters` 與 `summary`（degraded／loso／stats_modes）是 AR-3 語意依賴，不是可刪的型別附件；「導出」若只產出 assignments 會讓 `formal_pooled_inference_allowed` 與 cluster CI 假綠或假紅。

**碼證**: `_common_constraint_block`（`tables.py:130-150`）讀 `summary.degraded`／`loso_status`／`n_symbols`；`event_forward_return_table` 拒空 `clusters` 冒充未切分（`:194-206`）；`split_events` 建 `time_cluster_id`＋`cluster_weight=1/n`（`event_split.py:134-140`）。RECHECK：投影產出缺 clusters 或 summary.degraded ⇒ 既有 AR-3 斷言紅。

**來源摘要**: momentum/Analysis/event_samples/tables.py#b80c15cf206d; momentum/Analysis/event_samples/event_split.py#fde5a520c319; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MINOR] 信心度=High。會怎麼失敗：CI 全標 unavailable 或反向以空 clusters 算出看似有效 CI。修法：投影函式契約＝完整 `EventSplitPlan` 四欄；cluster 邏輯可抽共用，不得省略。

---

## GROK-R1-P2-03

**斷言**: 「兩套都保留但標主從」不能滿足本票 UAT 目標（同一報告兩個驗證段數字），應在 SPEC §N 或 §C 明文否決為反模式。

**碼證**: brief「為什麼非統一不可」＋`白話說明/接下來要做的票.md` SPLITUNIFY 段（31 vs 33）。主從標籤不刪第二條算術 ⇒ 數字仍可分歧。RECHECK：SPEC 合併稿 grep 不得出現並行雙邊界計算路徑。

**來源摘要**: handoffs/20260910-SPLITUNIFY-CONSULT-BRIEF.md#d45d71164f56; 白話說明/接下來要做的票.md#2b5d19cafa75

[MINOR] 信心度=High。修法：§C 禁並行雙切；過渡期只允許舊 artifact 讀取相容。

---

## GROK-R1-P2-04

**斷言**: GAP-3 原檔 FROZEN；本票應出 `GAP3_EVENT_UX_SPEC.D-002`（及 EVENT SPEC amendments），**不解凍／不 R 重開**作為預設路徑——除非委員會把「B1.3 事件自切」裁定為設計被證偽（則程序預設 R）。

**碼證**: `GAP3_EVENT_UX_SPEC.md` 檔頭 `狀態：FROZEN`＋`延伸: D-001 ...`；`FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1 D vs R；`GAP3_EVENT_SPEC.md` 頭註修訂走 amendments、不就地改。`ls docs/GAP3_EVENT_UX_SPEC.D-*.md` ⇒ 僅 D-001 ⇒ 下一號 D-002。RECHECK：合併稿路徑存在且 `template_check.sh dext` 可跑。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#f2da7e1041d5; docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md#176c58e0c914; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MINOR] 信心度=High。會怎麼失敗：就地改 FROZEN ⇒ 戳記／延伸索引機檢紅；或誤開 R 拖垮無關延伸。修法：D-002＋amendments；爭議面再升 R。

---

