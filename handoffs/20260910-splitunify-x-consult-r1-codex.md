# SPLITUNIFY consult R1 — CODEX

task-id: 20260910-SPLITUNIFY-X-CONSULT-R1  
family: CODEX  
brief: `handoffs/20260910-SPLITUNIFY-CONSULT-BRIEF.md`  
scope: read-only design consult；本輪未改 production code、既有測試或 frozen GAP-3 原檔。

## §0 前提挑戰（逐條）

- **fact-verified**：`EventSplitPlan` 出現在 7 個 production files、6 個 test files。VERIFY：`rg -l 'EventSplitPlan' momentum api --glob '*.py'` 與 `rg -l 'EventSplitPlan' tests --glob '*.py'`；stdout 為 production=7、tests=6，清單與 brief 相符。
- **fact-verified**：EVTLABEL 的 `test_timestamps` 只把 IC 路徑的事件選樣對到 row-level test scope；`EventSamplePipeline.run()` 仍在 `pipeline.py:691` 獨立呼叫 `split_events()`。
- **assumed，未成立為 fact**：時間切分的 purge/embargo 嚴格包含事件切分的 interval purge。兩者單位、邊界與輸入集合不同，現有碼沒有 containment proof；因此不能用「較強」作為 1a 的唯一理由。
- **assumed，已被否證**：統一後多 symbol 數值自然不變。VERIFY：`venv/bin/python handoffs/20260910-probe-splitunify-multisymbol.py`；stdout `合併列數=80 全域切法之測試段=12 per-symbol 切法之測試段=8`、`只在全域=4`、`probe_rc=1`（該 rc=1 是 probe 的預期否證結果）。

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

## 必答 1a–6

### 1a. 統一方向

採 **第三方 canonical temporal boundary**：切分的語意是時間 holdout（含 purge/embargo），但 `SplitPlan` 與 `EventSplitPlan` 都只是從同一 boundary 物化的 domain projections；兩者都不再自行決定 boundary arithmetic。這比直接把現有單一 `SplitPlan` scalar 當主從更安全，也保留 row identity 與 event interval/cluster 語意。

### 1b. 最小可行落地步驟

1. 先寫 `docs/SPLITUNIFY_SPEC.md`、`docs/SPLITUNIFY_TODO.md`、`docs/GAP3_EVENT_UX_SPEC.D-002.md`：固定 boundary 的時間語意、multi-symbol policy、event projection 規則、golden 與 UAT。
2. 在 `momentum/core/split_preview.py` 擴出唯一 pure canonical temporal-boundary builder；以同一 calendar boundary 產生每 symbol 的 boundary map，並以既有 `split_per_symbol()` 物化每 symbol train/test `SplitPlan`。不把多 symbol 塞回單一 `SplitPlan` dataclass。
3. 在 `momentum/Analysis/event_samples/event_split.py` 把 `split_events()` 的 boundary arithmetic 改為 canonical boundary projection：事件的 feature-cutoff row 必須落在 canonical test rows；答案窗不完整或跨 forbidden boundary 的事件明列 purge／不可用，clusters 與 summary 重新計算。`EventSplitPlan` 容器保留。
4. 改 `momentum/Analysis/ic_filter_orchestrator.py` 與 `momentum/Analysis/event_samples/pipeline.py` 共用同一 boundary；pipeline 若沒有該 feature universe，只能走已命名的 event-study-only 路徑，不得另按事件數切 OOS。
5. `baseline.py`、`pattern_bridge.py`、`tables.py` 保留既有對外形狀，先只讀驗證它們消費的新 assignments/clusters/summary；`types.py` 的 `EventSplitPlan` 不先刪欄，`ic_feed.py` 不另建第三套切法。新增逐 event ID、row fingerprint、numeric report golden。
6. 最後才做 API/frontend 的單一驗證段揭露與 UAT；報告只暴露 canonical `n_test`，附 `split_authority`、boundary hash、per-symbol counts 與 fail-closed reason。

### 2a. 多 symbol 是否等價、要擋還是支援

現況不等價，且已由 probe 否證。方案選 **支援 per-symbol**，不是用 scalar 偷近似：canonical 是一個時間 boundary policy，落地為每 symbol 一對 `SplitPlan`；事件 assignments 逐 symbol 投影後再合併。任何 symbol 缺 rows、缺 feature-cutoff 對映、或投影集合與 row test 集不一致，fail-closed；不回退全樣本、不取第一個 symbol。

### 2b. `SplitPlan` 是否需要 per-symbol 化

需要 per-symbol **plan collection**，不需要把 `SplitPlan` dataclass 改成含多 symbol。直接使用既有 `split_per_symbol()` 的 list of `(train_plan, test_plan)`；canonical boundary map 與 `symbol`、`base_universe_hash` 綁定，避免跨 symbol row_index 污染。

### 3a. baseline / pattern_bridge 的語意與型別依賴

| 檔案 | 不可替換的語意依賴 | 可保留／可替換的型別依賴 |
|---|---|---|
| `baseline.py::single_feature_binary_baseline` | test event ID 集、OOS-only、one-class/非有限值 fail-closed | 目前參數仍可留 `EventSplitPlan`；若新增 accessor，只能是同一 projection 的 read-only view |
| `pattern_bridge.py::extract_event_patterns` | train/test event ID 集、缺 split 不得 fallback、train-only fit/test-only score | `_split_plans()` 產出的 event-id `SplitPlan(row_id)` 是給 `PatternExtractor` 的型別 adapter，可保留，不是 canonical boundary |
| `tables.py::binary_discrimination_table` | test event IDs、clusters、degraded/LOSO 與 macro/micro/CI estimand | `EventSplitPlan` 外形可保持，不能把欄位縮成 timestamps |
| `pipeline.py` / `ic_feed.py` | 使用者可見的 split summary 與 event-study-only distinction | 既有 dict/dataclass 外殼可保留，但不得再自行算一份 boundary |

### 3b. 會改變數值的 consumer

會。最直接的是 `single_feature_binary_baseline()`（`n_test`、prevalence、AUC/PR-AUC、permutation band、BH-FDR）、`binary_discrimination_table()`（overall/strata/macro/micro/cluster CI）、`extract_event_patterns()`（fit rows、規則、test scores/lift、train hash），以及 `ic_filter_orchestrator._resolve_label_mode_and_bind_binary()`（驗證段正反例數、effective label mode 或明示 raise）。`pipeline.py` 的 `n_train/n_test/n_purged` 也會變；這些都必須以 golden／diff 驗收，不能標成純型別替換。

### 4a. GAP-3 FROZEN：延伸檔還是解凍

走 **延伸檔**，不解凍原檔。

### 4b. 延伸檔編號與範圍

採 `docs/GAP3_EVENT_UX_SPEC.D-002.md`，範圍只涵蓋：canonical temporal boundary、per-symbol `SplitPlan` collection、`EventSplitPlan` projection、multi-symbol fail-closed、數值/golden/mutation、單一驗證段揭露與 UAT 對證；另以 `docs/SPLITUNIFY_SPEC.md`／`docs/SPLITUNIFY_TODO.md` 管理本票施工。既有 B1.3 的事件 interval/cluster 統計語意不刪，只改其 boundary producer 為 projection。

### 5a. 兩套都保留但標主從是否更優

保留兩個 **projection containers** 是必要的；保留兩套獨立 arithmetic 不是更優。後者的代價是 UAT 再次出現兩個 `n_test`、baseline/pattern/IC 各自得到不同 OOS 集合，並重演第二份算術漂移。故「時間 boundary 一個來源、兩個 domain views」優於「兩套切法主從並存」。

### 5b. 最終建議（一句話）

**用一個時間語意的 canonical boundary 產生 per-symbol `SplitPlan`，事件側只投影 assignments/purge/clusters/summary，所有報告只承認這一個驗證段。**

### 6. 票大小與批數

這是 **大票，4 批**：

1. 契約與 frozen extension（SPEC/TODO/D-002）＋真實 kline、多 symbol golden/negative cases。
2. core canonical boundary＋per-symbol plan collection＋event projection，先不改 UI。
3. orchestrator/pipeline 接線與 baseline/table/pattern/label-mode 數值回歸；每一批都比對 event IDs、row fingerprints、NaN/數值與 reason。
4. API/frontend 單一驗證段揭露、UAT checklist、全票 gates 與三家 review/reconcile。

### 分歧時的碼證判準

不以家族票數收斂。採較嚴判準：同一真實 kline＋同一事件 manifest 下，per-symbol canonical row test 集與 event feature-cutoff test 集逐 ID 相等；purge/embargo forbidden rows 無交集；任何第二份 boundary arithmetic 或 scalar first-symbol shortcut 都判不通過。若方案不能提供上述 receipt，採 fail-closed 版本。

## Verdict

**需修補後派工：以第三方 canonical temporal boundary 定唯一邊界，支援 per-symbol projections，先補 SPEC/D-002 與 multi-symbol／雙 producer golden，再分 4 批接線；不得直接以 scalar `test_timestamps` 取代事件計畫。**

## 交件核對

ASSUMPTIONS_VERIFIED: `EventSplitPlan` production/test 檔案數 7/6；IC 端 `test_timestamps` 與 pipeline 端 `split_events()` 為雙 producer；multi-symbol probe 觀測全域 12 vs per-symbol 8；現有 event split/baseline/pattern/table targeted tests 37 passed。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/test_event_split.py tests/momentum/event_samples/test_baseline_oracle.py tests/momentum/event_samples/test_pattern_bridge.py tests/momentum/event_samples/test_tables.py -q` → 37 passed in 8.75s；`venv/bin/python handoffs/20260910-probe-splitunify-multisymbol.py` → intentional disproof output, process rc=1；requested `bash scripts/completeness_check.sh --single handoffs/20260910-splitunify-x-consult-r1-codex.md --family codex` was blocked by the repository PreToolUse gate before script execution because committee round `471b1b4c-0ab3-4910-b3af-5c5b70e41b83` remains OPEN, so no completeness rc was produced.
FAILURES_SEEN: none unresolved；probe rc=1 是預期的否證訊號，不是 regression test failure；completeness script 未開始執行，阻擋發生於 script 前，非格式檢查失敗。
SCOPE_CHANGES: none；只新增本 consult 產出檔，未修改 production/test/frozen docs；既有 dirty worktree 檔案未觸碰。
NUMERIC_OR_SCHEMA_IMPACT: 本輪無程式輸出變更；建議方案會改 validation membership、n_train/n_test、OOS metrics、capability reason 與揭露欄，需以 golden/receipt 明確核准，不能假設數值不變。
HANDOFF_OUTPUT: `handoffs/20260910-splitunify-x-consult-r1-codex.md`
STATUS: BLOCKED — completeness command was pre-tool blocked by the existing OPEN committee debt; no script rc=0 confirmation is available.
