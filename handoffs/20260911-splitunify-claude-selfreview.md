# SPLITUNIFY SPEC/TODO — Claude 自產獨立審查（R1，與三家平行）

依 `feedback_claude_own_version`：主委不只編排，先自產完整一版，再與三家互審。
**審查對象＝我自己寫的** `docs/SPLITUNIFY_SPEC.md`／`docs/SPLITUNIFY_TODO.md`（commit `08391e4c`）。
逐條附碼證（檔案:行號），皆為本輪實讀，非引用。

---

## CLAUDE-R1-P0-01

**斷言**: TODO Task 3.1 之「`pipeline.py` 之事件切分出口改呼叫 `derive_event_split_from_plans`」不可執行——該呼叫點拿不到任何 `SplitPlan`，故 SPEC C-1／C-3 之「投影」在現行架構下沒有落點。

**碼證**: `momentum/Analysis/event_samples/pipeline.py:691` ＝ `plan = split_events(manifest, config.split, lookahead_gate=lookahead_gate)`，輸入只有 `EventManifest` 與 `EventSplitConfig`（`momentum/Analysis/event_samples/types.py`），兩者皆無 `SplitPlan` 欄。唯一生產 caller ＝ `api/services/case_import_service.py:1610` 之 `run_with_params`，參數只有 `test_fraction`／`embargo_ms`／`tier_min_test_events`（`pipeline.py:507-517`）。IC 側 `SplitPlan` 在另一個 service 建立：`ic_filter_orchestrator._build_holdout_split_plan`（`ic_filter_orchestrator.py:561`，呼叫點 `:1256`）。兩者無傳遞管道，且 R4（services 不互 import）與 R1（momentum 不 import api）皆擋著。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

修法（我的立場）：共享**規則**而非共享**物件**。把 canonical 邊界抽成純函式，住
`momentum/core/split_preview.py`（該檔已有 `holdout_test_row_index`／`holdout_split_point`
兩支被兩端共用的先例），簽名近似
`holdout_boundary_ms(index_ms, *, oos_test_size, purge, embargo) -> (train_end_ms, test_start_ms)`。
事件端與 IC 端各自呼叫它，得到逐位元組相同的邊界；投影＝事件時間戳與該邊界比較，
不再有第二份算術。

---

## CLAUDE-R1-P0-02

**斷言**: SPEC C-3／TODO Task 2.1 把「三態」當成本票新引入的結構並要求「三態互斥且涵蓋全集」，但 `EventSplitPlan` 本來就是三態；照字面實作成 `assignments.split_label` 三值會破壞既有 schema 且不會報錯，只會靜默少算。

**碼證**: `momentum/Analysis/event_samples/types.py::EventSplitPlan` 欄位＝`assignments`／`purged`／`clusters`／`summary`，`purged` 是獨立 DataFrame（`event_id`, `reason`）。`event_split.py:113-117` 之三分支即三態。只認 train／test 兩值的消費者：`pipeline.py:697-698`、`baseline.py:106`、`tables.py:305`、`pattern_bridge.py:115,125-127`。purge reason 之契約字面 `interval_crosses_split_boundary` 住 `momentum/Analysis/contracts/event_import_contract.json:465-467`（`split_purge_reasons`）。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

修法：投影必須維持既有容器形狀——train/test 進 `assignments`，被隔離者進 `purged`
並沿用契約既有 reason 字面，**不得**在 `split_unify.json` 另造 purge reason（那是第二份真相源）。
TODO Task 1.2 之 `assignment_states` 應改寫為「三態＝兩容器」之說明，而非一個三值枚舉。

---

## CLAUDE-R1-P0-03

**斷言**: TODO Task 2.1 之輸出契約漏了 `EventSplitPlan.summary` 的 12 個必填鍵；投影函式若只回 assignments/purged/clusters，報告會靜默丟欄。

**碼證**: `momentum/Analysis/event_samples/event_split.py:141-155` 產出 `n_symbols`／`per_symbol_n`／`n_time_clusters`／`avg_cluster_size`／`degraded`／`loso_status`／`insufficient_events_in_test`／`stats_modes`／`n_events_raw`／`n_events_effective`／`n_purged`／`bucket_ms`；`pipeline.py:696` 整包（去 `per_symbol_n`）轉進報告 `summary["split"]`。旗標字面來源＝`event_import_contract.json:468-471`（`split_loud_flags`／`degraded_flags`）。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

影響與 EVTLABEL B5 那條「light 視圖漏 `metadata_keep_keys` ⇒ 整段揭露在正常回應中消失」同形態。
修法：Task 2.1 之「輸入輸出」欄補逐鍵來源表。三個鍵在投影下語意必須重新定義——
`insufficient_events_in_test`（`tier_min_test_events` 檢核改看投影後的 test 數）、
`degraded`（`_degraded_flags` 之 `cluster_adjusted` 在投影下是否恆真）、
`loso_status`（維持 `"not_evaluated"`）。

---

## CLAUDE-R1-P1-04

**斷言**: TODO Task 2.1 之簽名 `(train_plan, test_plan, event_index) -> EventSplitPlan` 產不出 `clusters`，因為 clusters 完全不依賴切分邊界而依賴 manifest。

**碼證**: `momentum/Analysis/event_samples/event_split.py:129-140`：`tc = t["decision_at_ms"] // bucket`、`counts = tc.map(tc.value_counts())`、`cluster_weight=_cluster_weight(counts)`，輸入全來自 `manifest.table` 與 `bucket_ms`，無一項來自切分邊界。`_cluster_weight`（`event_split.py:36-39`）自帶註記為既有 mutation seam（M5）。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

修法：把 clusters 抽成獨立純函式 `build_time_clusters(manifest, bucket_ms)`，
行為不變（改前後 byte 級一致，走 G-2 同一條驗法）；投影只負責 `assignments`／`purged`。
搬家時不得弄丟 `_cluster_weight` 這個 mutation seam。

---

## CLAUDE-R1-P1-05

**斷言**: 同一條路徑上流動著 positional／秒／毫秒三種時間單位，SPEC C-3 未指明換算點與換算方向，任一處寫錯即 1000 倍或 off-by-N。

**碼證**: `momentum/Analysis/event_samples/event_split.py` 檔頭逐字「切分一律依 epoch ms 時間比較，**禁 positional index**（ML 孤島舊坑）」；`ic_filter_orchestrator.py:602` 之 `plan_kwargs["index_kind"]="positional"`、`row_index` 為對 `features_df` 的位置索引（`:578`、`:583-588`）；`api/services/case_import_service.py:1626-1627` 同時輸出 `event_timestamps`（毫秒）與 `event_timestamps_ic_seconds`（秒，註「IC 主線 row_index＝bar open 秒」）。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

EVTLABEL 的 e2e 探針已因此踩過一次（cache 是秒、我寫死 ms ⇒ 日期跑到 1970、區塊尺度錯 1000 倍）。
修法：邊界純函式（見 P0-01）之輸入輸出一律 epoch ms，換算只在其呼叫端各做一次；
Task 2.1 之「驗證」欄加一條單位斷言（1970 vs 真實年份的可證偽測試）。

---

## CLAUDE-R1-P1-06

**斷言**: TODO Task 3.1 之驗收「`tests/momentum/Analysis` failed 數 <= 20」是聚合期望數，既有紅有一條偶然變綠時可掩蓋本票改壞的一條，構成假綠；且違反 brief 紅線「驗收禁寫聚合期望數」。

**碼證**: `docs/SPLITUNIFY_TODO.md` Task 3.1「驗證」欄逐字；既有紅基準見 `HANDOFF.md`「既有紅盤點」節（20 failed / 1615 passed，分三類：測試間污染 8 條、golden digest 3 條、inventory／contract sync 漂移）。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

修法：既有紅逐條落檔 `tests/known_red/splitunify_baseline.txt`（node id 全名，B1 產出並 commit），
驗收改為
`venv/bin/python -m pytest -q tests/momentum/Analysis $(sed 's/^/--deselect /' tests/known_red/splitunify_baseline.txt)`
要求 rc=0。清單中任何一條變綠須主動移出（可證偽）。

---

## CLAUDE-R1-P2-07

**斷言**: 投影後 `EventSplitConfig.embargo_ms` 與 `embargo_ms_by_symbol` 兩欄的語意懸空，TODO 未寫處置；若靜默忽略，上游算出的 `embargo_applied` 會退化成沒人用的數字。

**碼證**: `momentum/Analysis/event_samples/event_split.py:60-75`（兩欄互斥閘）、`:95-103`（逐 symbol fail-closed 檢核）、`:104-107`（`embargo < window.max()` ⇒ raise）；上游 `api/services/case_import_service.py:1606` 之 `embargo_applied = max(requested, declared_lb) or None`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#36b5c6ae5af2

「算了卻沒人用」正是 EVTLABEL `CODEX-R1-P1-02` 已踩過一次的形態
（`api/services/ic_analysis_service.py:834-836` 逐字記錄該事故）。
修法：TODO 明寫投影路徑下這兩欄必須為 `None`，否則 raise（不是靜默忽略）。

---

## CLAUDE-R1-P2-08

**斷言**: SPEC §A 之「同一份報告會看到兩個驗證段」前提不精確——兩個數字分屬兩個 service、兩個 endpoint，不存在單一合併點。

**碼證**: `api/services/case_import_service.py:1610-1628`（`EventImportService` 掃描報告之 `summary.split`／`n_train`／`n_test`／`n_purged`）vs `momentum/Analysis/ic_filter_orchestrator.py:1256`（`ICAnalysisService` 之 IC 報告 metadata）。兩者無共同呼叫者。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#4e016f8e1d54

修法：§A 改寫為「同一批事件、同一次 UAT 會看到兩個互相矛盾的驗證段數字」。
不精確的前提會被 reviewer 當 finding 打回，也會誤導實作端去找一個不存在的合併點。

---

## 已被本輪查證否證的 brief 項（誠實記錄，不算 finding）

- brief「我沒查的」第 1 條（`pattern_bridge` 是否讀 `clusters` 語意）：**已查，答案是否**。
  `momentum/Analysis/event_samples/pattern_bridge.py:113-127` 只讀 `assignments` 的成員集合，
  不碰 `clusters` ⇒ 成員依賴，投影只要成員集合正確就數值不變。
- brief assumed 第 2 條（`baseline.py` 只是型別依賴）：`baseline.py:106` 只取
  `assignments[split_label=="test"]["event_id"]` ⇒ 同為成員依賴，**假設成立**。

---

## Verdict

**SPEC v1／TODO v1 不可直接進 B1。** P0-01 使 B3 的接線點不存在、P0-02 會破壞既有 schema、
P0-03 會靜默丟失報告欄位——三條都不是措辭問題，是設計缺口。
建議：待三家 findings 回來後合併，SPEC 改 v2（新增邊界純函式一節、改寫三態表述、
補 summary 逐鍵契約），TODO 重排 B2／B3，再進 B1。
