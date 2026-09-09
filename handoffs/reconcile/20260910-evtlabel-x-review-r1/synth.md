# Reconcile — 20260910-evtlabel-x-review-r1

**來源** 20260910-evtlabel-x-review-r1-codex.md, 20260910-evtlabel-x-review-r1-composer.md, 20260910-evtlabel-x-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**輪次計數**：codex 14（2×P0、12×P1）、composer 6（2×P0、2×P1、2×P2）、grok 7（1×P0、4×P1、2×P2）＝ **27 條**；P0＝5（去重後 **4 個獨立 P0**）、P1＝18、P2＝4。
三家 Verdict 一致＝**需修補後派工；P3 不延後另開票**（三家逐字皆如此）。

Verdict: 需修補後合併（SPEC/TODO 依下列 C1–C14 修訂後派 R2 閉合輪）

---

### C1 🔴 P0 — binary 幅度閘讀有號 `rank_biserial`＝殺掉反向強分辨；且 `ic_mean_min` 非同一 estimand 的門檻
**ID**：`GROK-R1-P0-01`、`COMPOSER-R1-P0-01`、`CODEX-R1-P1-05`、`GROK-R1-P2-01`
**處置**：Task 3.6 不再共用 `ic_mean_min`。新 config 鍵 `thresholds.rank_biserial_min`（JSON SoT；預設 0.10＝AUC 0.55，**取絕對值**比較；文件明寫「非 power 校準之預註冊效應量門檻，主閘＝FDR＋依賴感知置換」）；`n_pos/n_neg/n_used` 進可用性與報告；mutation 加「負向植入（rb≈−0.8）仍 passed」。

### C2 🔴 P0 — `auto` 用全批類數判定，但統計在 test 段
**ID**：`COMPOSER-R1-P0-02`、`GROK-R1-P1-04`、`CODEX-R1-P1-03`
**處置**：模式決策點移到 **orchestrator stage3（切分已知後）**：以**實際 selection scope**（test 段；full-sample fallback 時＝全樣本）每類 ≥ `min_events_per_class` 判定；`auto` 不足 ⇒ `return_rule`＋`reason=class_below_min_test`（loud：`metadata.label_mode`＋banner 必顯）；顯式 `imported_binary` 不足 ⇒ raise。報告同時揭露全批／train／test 類數。service 只傳 `requested` 與 binary map。`min_events_per_class=10` 維持，文件明寫「exact MW 可算之最低條件，非 power 依據」。受理 run test 段 17/14（三家實算一致）。

### C3 🔴 P0 — 負對照非零只 warning＝把隨機標籤留下的特徵交給 ML
**ID**：`CODEX-R1-P0-01`
**處置**：`n_survivors_shuffled > 0` ⇒ **fail-closed**：binary 倖存者不寫 consumable survivor（`survivor_output.status=suppressed, reason=negative_control_failed`），報告 `degraded` 並保留診斷表；mutation 加對應阻擋斷言。

### C4 🔴 P0 — 「驗了一份、消費另一份」：stage3 驗 → cache → stage5 讀
**ID**：`CODEX-R1-P0-02`、`GROK-R1-P2-02`
**處置**：stage3 回傳 **immutable** `ValidatedBinaryLabel(series, digest)`（digest＝sha256 over sorted `(event_id, ts_ms, label)`）；stage5 消費前對實際餵進 `mann_whitney_table` 的 `(index, y)` 重算 digest 比對，不等 ⇒ `AlignmentViolationError`，不產 report；測試明確 mutate cache（M-P3-5）＋沿 `test_validated_series_is_used_series.py` 形狀加 spy。

### C5 — 三元組回綁：early-return 跳過報酬腿；缺 timestamp 腿
**ID**：`GROK-R1-P1-01`、`COMPOSER-R1-P1-01`、`CODEX-R1-P1-07`
**處置**：`_assert_event_triple_bound` 改依 `label_source` 分派；`imported_binary_label` 下**雙鍵**回比（報酬 `consumed_event_labels`＋binary `consumed_event_binary_rows`）。binary 腿升級為三元組：`validate_event_given` 回傳新增 `consumed_event_rows={event_id:(ts_ms,value)}`（**additive**，報酬路徑之既有回傳鍵不變＝G-1）；service 之 binary source map 由匯入 records **獨立快照**（`event_id→(t0/feature_cutoff_ms, label)`）建立，不與 consumer map 同源；三項逐筆回比。

### C6 — TODO 錯 kwarg
**ID**：`GROK-R1-P1-02`
**處置**：TODO 3.4 改 `label_kind=derive_label_kind("imported_binary_label")`。

### C7 — `embargo_source` 雙寫入點矛盾
**ID**：`GROK-R1-P1-03`
**處置**：定死：orchestrator 只寫 `purge_gap_source`／`event_label_window_rows`／`lookahead_depth_rows`；`embargo_source` 只由 service 寫在 `metadata.isolation.embargo.source`。SPEC G-3／Task 2.2 同步改寫。

### C8 — P2 控制通道：`config_override` 未知鍵被 `ICConfig` 靜默丟
**ID**：`CODEX-R1-P1-04`、`COMPOSER-R1-P1-02`
**處置**：不走 `config_override`。新 frozen dataclass `EventIsolationRows(label_window_rows, lookahead_depth_rows)`（`momentum/core/contracts.py`）作 `analyze(..., event_isolation=None)` 顯式 kwarg；兩注入點皆傳；fail-closed 測試「這兩鍵若出現在 `config_override` ⇒ raise」。TODO 刪「執行時以實跑定」。

### C9 — 既有 event predicate 只認 `event_label_value`；stage6/6b 消費未定義
**ID**：`CODEX-R1-P1-06`、`CODEX-R1-P1-08`
**處置**：集中成單一契約 predicate `is_event_label_consumed(event_info)`（涵蓋兩 source），取代 `_is_event_conditional_consumed` 之所有呼叫點（ICIR 閘、stage6 redundancy）；binary 模式 stage6 redundancy 分數＝`|rank_biserial|`（tiebreak `feature_name` 字典序）；stage6b marginal/composite 在 binary 模式標 `diagnostic`，**不得**移除 binary 倖存者；雙特徵 fixture（一個只對 0/1 分離、一個只對報酬強）跑 stage3→6b 驗倖存集由 binary 決定。

### C10 — binary p 的 iid 假設；置換須依賴感知
**ID**：`CODEX-R1-P1-09`
**處置**：Task 3.7 之置換改為 **block permutation**（block 長度＝`max(1, ceil(label_window_feature_bars / 事件間距中位數列數))`；`n_blocks < 10` ⇒ 置換 `unavailable`、該特徵不得成為 consumable 倖存者）；MW p 於 `metadata.event_label_rule` 標 `p_assumption="iid_events"`；R-1 擴寫納入 binary 依賴議題。受理 run（h=1、事件間距 ≥1 根 12h）block=1 ⇒ 與普通置換等價。

### C11 — e2e sign oracle 非必要不變式
**ID**：`CODEX-R1-P1-10`
**處置**：Task 3.10 移除 top-20 sign 條件；改為 (i) 兩模式事件身分（event_id 集合／ts）逐位元組 parity、(ii) 報酬欄逐特徵相等、(iii) 真實 kline 上植入單調特徵（`label=1[feature_j(t0)>median]`）⇒ 該特徵 `auc==1.0`、(iv) 錯位 raise。

### C12 — G-1/G-4 未鎖 survivor bytes
**ID**：`CODEX-R1-P1-11`
**處置**：新增 **G-6**：`return_rule`／全域 survivor payload 之 canonical bytes/hash golden（去 `generated_at`），P3 改後比對；欄集／null mask／大小同鎖。

### C13 — R-4「餵 ML」邊界須有實際 consumer 證明，不能只靠主委註解
**ID**：`CODEX-R1-P1-12`（composer 必答 7「部分成立」、grok「非偷換」同向）
**處置**：新增 **Task 3.11**：既有純函式 consumer `momentum/Analysis/event_samples/pattern_bridge.py`（`survivor_v2` 入口）之**消費契約測試**——由 binary 路徑產出之 survivor payload 餵入，須成功接收且 `label_source`／`label_binary` 保留；**不接 ML 訓練殼**（成熟度地圖）。白話頭條仍列 R-4 邊界由使用者決定是否接受。

### C14 — 置換成本無上界；`auto` 生效 banner；label 值域驗證
**ID**：`CODEX-R1-P1-13`、`COMPOSER-R1-P2-02`、`COMPOSER-R1-P2-01`、`CODEX-R1-P1-14`
**處置**：(a) Task 3.7 置換預算：`n_perm = clamp(perm_budget_total / K, 200, 1000)`（`perm_budget_total` 預設 200,000）；benchmark 測試超 120s ⇒ FAIL（非只印 receipt）；候選排序 deterministic（`|rb|` desc、`feature_name`）。(b) Task 3.9：`imported_binary` 生效時亦顯示模式摘要 banner（非 degrade）。(c) Task 3.3 staging：label 值域閘——finite、整數、精確 ∈ {0,1}、無缺值；違反 ⇒ `auto` 給 `reason=label_invalid_domain` 回 `return_rule`（loud）、顯式 binary raise。

---

### §0 假設裁定（三家一致）
- ASSUME-1 成立（三家重跑 probe rc=0）。
- ASSUME-2 部分成立：clean 向量化 0.41–0.77s（codex／composer 實跑）；10% NaN 逐欄 5.48s（composer）；完整路徑 benchmark 留 B4（C14a 之測試）。
- ASSUME-3 成立（0.0/1.0 finite；但值域閘由 C14c 補）。
- 「rank_biserial 餵 ic_mean_min」推翻（C1）。
- 「P2 語意錯位非洩漏」成立；改後總隔離：h1 c2c 149→156、h12 o2hc 161→300；`D=0,C=0,W>H` 時可小於改前但仍 ≥ max(W,D)——寫進 SPEC §A。
- ICConfig 非 `extra=forbid`、未知鍵靜默丟（三家實跑）⇒ C8。

### 不採納
無。所有 finding 皆採納或合併。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01

**斷言**: Task 3.7 的 negative control 產生非零 survivor 時只加 warning、不阻擋輸出，與「fail-closed」及資料品質要求矛盾，會把隨機標籤留下的特徵交給 ML。

**碼證**: `docs/EVTLABEL_SPEC.md:222-231` 與 `docs/EVTLABEL_TODO.md:336-351` 明寫 `n_survivors_shuffled > 0` 僅追加 `negative_control_nonzero` warning（「不擋」）；同一任務標題卻是 `fail-closed`，而 §C/§3 禁止弱化資料品質閘。RECHECK：用固定 seed 強制 shuffled table 留下一列，驗證 report 不產 binary survivor、status/reason 為不可用或整批 fail，而不是只多一個 warning。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a, docs/EVTLABEL_TODO.md#b58c476949a1

[BLOCKING] 信心度=High；若負對照能選出特徵，代表選擇閘或 FDR/效應量路徑不可信；warning-only 仍會落 survivor artifact。修法：`n_survivors_shuffled > 0` 必須 fail-closed（至少禁止 ML-consumable survivor；若產品要保留研究報告，需明確 `unavailable/degraded` 狀態與不可消費契約），並加入 mutation 對應的阻擋斷言。

## CODEX-R1-P0-02

**斷言**: binary label 在 stage3 通過驗證後，Task 3.6 仍可從另一份 mutable cache 取值計算，SPEC 沒有保證「被驗的向量」就是「被消費的向量」。

**碼證**: `docs/EVTLABEL_SPEC.md:189-198`／`docs/EVTLABEL_TODO.md:276-291` 要求 stage3 將驗證後資料放進 `self._ic_cache["event_binary_label"]`；但 `docs/EVTLABEL_SPEC.md:211-220`／`docs/EVTLABEL_TODO.md:315-332` 又把 stage5 的輸入獨立描述為該 cache，沒有 immutable object、digest、generation token 或 stage5 入口再驗。現有 orchestrator 的 stage5 是獨立呼叫點（`momentum/Analysis/ic_filter_orchestrator.py:1326-1333`）。RECHECK：stage3 驗證 A 後在 stage5 前替換 cache 為 B；預期必須在統計前以 `AlignmentViolationError` 失敗且不產 report。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a, docs/EVTLABEL_TODO.md#b58c476949a1, momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530

[BLOCKING] 信心度=High；這是「驗證一份、消費另一份」的 EVTALIGN 型錯誤，會在不報錯下改變 feature/label 配對。修法：stage3 回傳並由 stage5 消費同一個 validated series/token；或對 `(event_id,timestamp,label)` 做 immutable digest，stage5 消費前比對並 fail-closed。測試需明確 mutate cache，而不只測錯位輸入被 stage3 拒絕。

## CODEX-R1-P1-03

**斷言**: `auto` 以全批 `n_pos/n_neg` 判定 imported binary，但 binary 統計在 test split 上計算；因此可自動選 binary 後在 test 段單類或低於 10，得到空 survivor，卻沒有在 auto 決策點揭露或降級。

**碼證**: `docs/EVTLABEL_SPEC.md:178-187`／`docs/EVTLABEL_TODO.md:256-274` 的 auto 判定只看 coverage 後整批兩類數，`docs/EVTLABEL_SPEC.md:211-217`／`docs/EVTLABEL_TODO.md:315-332` 卻把統計 scope 固定為 `selection_scope=test` 並以 `min_events_per_class=10` 判定每欄可用。實跑受理批的 test 時間窗（2025-12-22 05:00 至 2026-03-13 00:00）只有 31 筆、17/14：`jq` 分組輸出 `n=31, labels={"0":14,"1":17}`；這次恰過門檻，但規格沒有保證其他 split、symbol 或缺值後仍然如此。RECHECK：以同一批 records 改變 chronological split 使 test 端 `<10` 或單類，確認 `auto` 不得仍宣告可用 binary。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a, docs/EVTLABEL_TODO.md#b58c476949a1

[MAJOR] 信心度=High；全批「驗過有兩類」不是 test estimand 可計算的保證，會產生看似成功但無法選特徵的報告。修法：先建立 split，再以實際 binary selection scope 的每類計數決定 effective mode/status；報告同時揭露全批與 test/train 類別數。`10` 目前只是未論證的常數，應由 test 端可計算性／預先定義的 power 或明確 config 契約決定，不可用全批數代替。

## CODEX-R1-P1-04

**斷言**: P2 透過 `config_override` 傳 `event_purge_rows`／`lookahead_depth_rows` 的方案尚未真正定死，且目前 `ICConfig` 會在 orchestrator 入口先把這兩個未知鍵靜默丟掉。

**碼證**: `docs/EVTLABEL_TODO.md:164-180` 同時寫「`pop` 後再建 ICConfig」與「若 extra 允許則改顯式欄位，執行時以實跑定」，這不是可派工的單一路徑。現有 `momentum/Analysis/ic_filter_orchestrator.py:1050` 先呼叫 `_apply_config_override`，`:4987-4994` 用 `ICConfig.model_validate`；`momentum/Analysis/ic_config_schema.py:415-455` 沒有 `extra=forbid` 或這兩個欄位。實跑：`venv/bin/python -c '...ICConfig.model_validate({"event_purge_rows":12,"lookahead_depth_rows":144})...'` 輸出 `{'event_purge_rows': None, 'lookahead_depth_rows': None, 'extra_in_dump': set()}`。RECHECK：在實際 analyze 入口注入 12/144，直接讀 split metadata，必須看到兩值而非只看到原 5/144。

**來源摘要**: docs/EVTLABEL_TODO.md#b58c476949a1, momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530, momentum/Analysis/ic_config_schema.py#1fd5a87b63b5

[MAJOR] 信心度=High；若 agent 按「pop」放在 config 建立後，P2 會靜默退回改前語意；若改成顯式 schema，又會把 per-request control data 與 config 混在同一契約。修法：在 `_apply_config_override` 前明確拆出 control-plane envelope，或明確把欄位加入 schema 並定義 hash／fallback／兩注入點行為；TODO 不得保留「執行時以實跑定」。

## CODEX-R1-P1-05

**斷言**: 將既有 `ic_mean_min=0.02` 直接套在 `rank_biserial` 上不是同一 estimand 的門檻，會按未校準的效果尺度錯誤剔除或放行 binary 特徵。

**碼證**: `docs/EVTLABEL_SPEC.md:200-209` 定義 `rank_biserial=2*AUC-1`；`:211-220` 卻要求 `ic_mean_min` 閘讀它。現有 `ThresholdsConfig.ic_mean_min` 仍是 IC 門檻（`momentum/Analysis/ic_config_schema.py:120-125`），既有 `_apply_thresholds` 也直接讀 `row["ic_mean"]`（`momentum/Analysis/ic_filter_orchestrator.py:4355-4399`）。rank-biserial 的抽樣變異受 `n_pos,n_neg` 影響，與連續報酬 IC 的尺度／解釋不同；在 136/29 全批與約 17/14 test 的兩個樣本量下，`0.02` 沒有同一統計意義。RECHECK：固定多組 `(n_pos,n_neg)`，以同一 effect threshold 對比 MW/FDR 與置換 null 的 selection 結果；預期證明 gate 行為隨樣本量改變而不是沿用 IC 常數。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a, momentum/Analysis/ic_config_schema.py#1fd5a87b63b5, momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530

[MAJOR] 信心度=High；AUC/rank-biserial 是「排序分離程度」的合理描述量，但既有 IC 門檻不是它的預註冊效應量門檻。修法：binary 另有語意明確的 effect gate（或只用 dependence-aware q＋置換校驗），並將 `n_pos/n_neg/n_used` 納入可用性與報告；不要把 `ic_mean_min` 改名後共用。

## CODEX-R1-P1-06

**斷言**: Task 3.4 將 `event_info.label_source` 改成 `imported_binary_label` 後，既有 event-path 判定器仍只認 `event_label_value`，會重新啟用 ICIR 閘，且 stage6 redundancy 會走全域 icir 分數。

**碼證**: 現有 `momentum/Analysis/ic_filter_orchestrator.py:3262-3281` 的 `_is_event_conditional_consumed` 只回傳 `label_source == "event_label_value"`；`:3895-3902` 用它決定 `icir_gate=not ...`，`:3266-3281` 也用它決定 event redundancy 是否改吃 `ic_mean`。SPEC/TODO 明確把 binary label source 改為 `imported_binary_label`（`docs/EVTLABEL_SPEC.md:189-198`、`docs/EVTLABEL_TODO.md:276-291`），又要求 ICIR/hit-rate/monotonicity binary 下不剔除（`:211-220`、`:315-334`）。RECHECK：以 `event_info={"label_source":"imported_binary_label"}` 且 ICIR 低於門檻的 stage5 fixture 執行；預期 binary 不因 ICIR 被移除，且 redundancy receipt 不得標全域 icir。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530, docs/EVTLABEL_SPEC.md#f25aa6c7d37a, docs/EVTLABEL_TODO.md#b58c476949a1

[MAJOR] 信心度=High；這是 P3 直接撞既有共用 gate 的可重現漏接，不是抽象風險。修法：把「event conditional / imported binary」的 producer classification 集中成單一契約 predicate；binary 明確跳過 ICIR/hit-rate/monotonicity，並為 stage6 選定 binary 主統計的 deterministic tiebreaker。

## CODEX-R1-P1-07

**斷言**: 現有三元組回綁只比較 `event_id -> value`，不比較 timestamp；同值事件換位或 producer-side 同步產生兩份錯位 map 時可以通過，binary 不會比 return label 更安全。

**碼證**: `api/services/ic_analysis_service.py:117-147` 的 `_assert_event_triple_bound` 只拿 `consumed_event_labels` 與 `staged["event_label_by_id"]` 比值；`momentum/core/contracts.py:1063-1107` 的 `validate_event_given` 回傳亦只有 `consumed_event_labels={event_id:value}`。service 產生 `owner: timestamp→event_id` 與 `by_id: event_id→value`（`api/services/ic_analysis_service.py:701-730`），沒有 `event_id→timestamp` 的不可變來源。RECHECK：兩事件 timestamp 不同但 binary value 相同，交換 owner 後要求 `(event_id,timestamp,value)` mismatch 必須 raise；另測在建立 `event_binary_labels` 與 `event_binary_label_by_id` 前同步旋轉兩份輸入，要求不能自洽放行。

**來源摘要**: api/services/ic_analysis_service.py#eb592a4d3d04, momentum/core/contracts.py#f817321f9e43, docs/EVTLABEL_SPEC.md#f25aa6c7d37a

[MAJOR] 信心度=High；目前註解稱「三元組最後一腿」，實際 contract 沒有 timestamp 這一腿。修法：producer 與 consumer 都使用 immutable rows/tuple 或 digest（`event_id,timestamp,label`），三項逐筆回比；binary 的 source map 必須從匯入 records 的獨立快照建立，不能與待驗 consumer map 同源再互比。

## CODEX-R1-P1-08

**斷言**: binary 統計只改 stage5 threshold，卻沒有定義 stage6 redundancy 與 stage6b marginal/composite 要消費 binary 還是 return label；因此最終 survivor 仍可能由報酬 IC 決定，偏離「用 0/1 找可分離特徵」。

**碼證**: 現有 `momentum/Analysis/ic_filter_orchestrator.py:3266-3281` 的 event redundancy 分數是 `ic_mean`，`:4609-4649` 的 stage6b 只接單一 `label_series`；TODO 只在 `docs/EVTLABEL_TODO.md:315-334` 定義 stage5 binary 欄與門檻，`docs/EVTLABEL_TODO.md:355-373` 只規定 survivor payload 帶來源，沒有 stage6/stage6b 的 binary consumable contract。RECHECK：建立一個只對 imported binary 分離、另一個只對 return label 強的雙 feature fixture，跑完整 stage3→stage6b；預期 survivor 決策與 ML handoff 必須由已選定的 binary estimand 控制，或明確把 return-only 節標成 diagnostic 而不得再剔除 binary survivor。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530, docs/EVTLABEL_TODO.md#b58c476949a1

[MAJOR] 信心度=High；P3 的「主統計」若只存在 summary_table，後續 redundancy/ML path 仍可把它覆寫成第二欄語意。修法：在 SPEC/TODO 明確選定 stage6/stage6b 的 label source、threshold 與 fit scope；若保留報酬版只作診斷，需測試它不能改變 binary survivor set。

## CODEX-R1-P1-09

**斷言**: MW p-value 與隨機置換目前都假設事件列可交換／近似 iid，但文件只把 HAC lag 留給 return IC；binary 主統計在有時間自相關時可能反保守，R-1 不能涵蓋這個未定義的 binary inference。

**碼證**: `docs/EVTLABEL_SPEC.md:200-209`／`docs/EVTLABEL_TODO.md:295-313` 固定使用 `scipy.stats.mannwhitneyu(..., method="auto")` 與普通 label permutation；`docs/EVTLABEL_SPEC.md:298-305` 的 R-1 只說事件路徑 HAC lag 仍用 5、rolling IC 空，沒有 binary p 的 dependence rule。現有 stage5 HAC（`momentum/Analysis/ic_filter_orchestrator.py:3787-3792`）是對單一 `label_for_stats` 的 IC 統計，並不使 MW p 具 HAC 校正。RECHECK：在受理事件 timestamp 上估計 label/feature rank 的序列依賴，並以 block/cluster permutation 或等價 dependence-aware null 重跑 q；若無足夠 block，binary p 必須 `unavailable` 而非照用 iid p。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a, docs/EVTLABEL_TODO.md#b58c476949a1, momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530

[MAJOR] 信心度=Medium；AUC/rank-biserial 作 effect estimand 可以保留，但「哪些特徵顯著分離」的 p/q 不能未聲明地套 iid。修法：預先定義 block/cluster null、最低有效 block 數與 unavailable reason；或把 MW q 明確降為 descriptive，不用它放行 ML survivor。

## CODEX-R1-P1-10

**斷言**: Task 3.10 的 `sign(rank_biserial)==sign(ic_mean)` top-20 oracle 不是資料正確性的必要不變式，正確實作也可能因非線性／尾部／ties 而 fail，錯誤實作反而可能碰巧 pass。

**碼證**: `docs/EVTLABEL_SPEC.md:255-264`／`docs/EVTLABEL_TODO.md:401-417` 把真實 kline 之 thresholded 0/1 label 與連續 return 的兩個 feature ranking sign 當成必要條件，但沒有 monotone feature-response 假設、ties/zero sign 規則或統計容差。`rank_biserial` 比較兩組秩；`ic_mean` 是既有 return IC，兩者並非數學等價。RECHECK：用真實 kline 產生一個非單調但合法的 feature（或只在 label threshold 附近有訊號），確認兩種 estimand 都按各自 oracle 正確而 sign oracle 不應擋；另加同一 feature/y 的獨立 AUC/rb 對照。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a, docs/EVTLABEL_TODO.md#b58c476949a1

[MAJOR] 信心度=High；E2E 應驗證 imported label 的 event identity、binary output 與 secondary return output 各自的 byte/value parity，不應用未證明的 sign 關係代替。修法：移除 top-20 sign 必要條件，改用可構造的 monotone oracle（若要保留 sign，將 monotonicity 明確寫成 fixture 前提而非 real-kline 必然性）。

## CODEX-R1-P1-11

**斷言**: G-1/G-4 目前主要鎖 report canonical sha／欄集，不能證明 return_rule／全域的 survivor file 未被 Task 3.1/3.8 改變。

**碼證**: `docs/EVTLABEL_SPEC.md:71-79` 的 G-1/G-4 只指定報告 sha；`docs/EVTLABEL_TODO.md:355-373` 才宣稱 survivor payload 逐位元組不變，但驗證只列 `test_survivor_contract.py` 與 `test_gap2_survivor_persist.py`，沒有改前 frozen survivor bytes。既有 `tests/momentum/Analysis/test_gap2_golden.py:49-63` 只對 report canonical sha、path/provenance 做 G-1，`:66-75` 只做兩次 live survivor determinism，未與 pre survivor golden 比對。RECHECK：以 frozen pre survivor payload（去除 only generated_at）對 return_rule 與全域改後 payload 做 canonical bytes/hash；任一新 binary key 或排序漂移都應紅。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a, docs/EVTLABEL_TODO.md#b58c476949a1, tests/momentum/Analysis/test_gap2_golden.py#frozen

[MAJOR] 信心度=High；這正是 brief 要求的 G-1/G-4 風險：summary 不變不代表 ML handoff 不變。修法：新增 return_rule/global survivor golden（value、NaN/null mask、欄集、canonical bytes/hash、輸出大小），並在 G-4 對刪除揭露鍵後的 report 與 survivor artifact 同時比對。

## CODEX-R1-P1-12

**斷言**: R-4 把使用者「再把這些特徵餵 ML」縮成寫一個 survivor file，但目前沒有實際 consumer/API handoff 驗證；這是主委邊界判斷，不是使用者裁定。

**碼證**: SPEC 明載主目標包含「再把這些特徵餵 ML」（`docs/EVTLABEL_SPEC.md:6-13`），卻在 `:298-305` 以主委判斷把 ML training shell 留到後票。現有 `momentum/Analysis/event_samples/pattern_bridge.py:52-64,89-105` 有可接 `survivor_v2` 的純函式，但 repo 搜尋只找到其定義與 tests，沒有 API/service caller；`api/routes/ml_pipeline.py:133-153` 目前是建立 pipeline config，不消費 IC survivor。RECHECK：新增並跑真正的 consumer contract test（由 binary survivor path 取得 payload、載入同一 feature/label split、ML/pattern consumer 成功接收且保留 label source）；沒有這條實際 handoff 就不能宣稱主目標已完成。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a, momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2, api/routes/ml_pipeline.py#eb592a4d3d04

[MAJOR] 信心度=High；這不要求把 P3 延後另開票，而是要求本票收尾的 acceptance 明確證明 survivor 是可消費的 ML 輸入；否則 R-4 是偷換主目標。修法：在本票把既有 consumer 的輸入契約／最小整合測試寫入 TODO，或由使用者明確接受「本票只交付檔案」這個邊界；不能只靠主委註解宣稱等價。

## CODEX-R1-P1-13

**斷言**: Task 3.7 的每 survivor 1,000 次 permutation 沒有上限、tier cap 或 worst-case benchmark；39k 欄位下只要 threshold 放行較多欄，`總增量 < 2 分鐘` 就沒有可證明依據。

**碼證**: `docs/EVTLABEL_SPEC.md:222-231`／`docs/EVTLABEL_TODO.md:336-353` 要求逐一 survivor 以 `n_perm=1000` 重驗，僅口頭寫「成本 ≤ 數百 × 1000」；同一批實際報告有 5,909 summary rows（`jq '.summary_table|length' data_cache/reports/ic_report_ic_gatekeeper.json`），而 §V `docs/EVTLABEL_SPEC.md:280-281` 只給總增量 `<2 分鐘`，沒有 survivor 上界、順序、RSS 或 tier baseline。RECHECK：以可使 gate 通過的 worst-case survivor count 跑 `test_evtlabel_oracle.py`／probe，記 wall time、CPU、RSS；測試必須在超過預算時 fail，而不是只印 receipt。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a, docs/EVTLABEL_TODO.md#b58c476949a1

[MAJOR] 信心度=High；這是未 profile 先把 O(K×1000) 放進 39k 特徵主線，可能成為不必要的 10× 以上成本。修法：預先定義最多 oracle candidates、deterministic ranking/tie-break、向量化或分批策略，以及 8/16/24/32GB 的測量門檻；negative control 與 per-survivor check 也要有明確預算。

## CODEX-R1-P1-14

**斷言**: staging 只做 `int(lab)` 與類別計數，沒有 fail-closed 驗證每個 imported label 真的是有限且精確的 0/1；`2`、`-1`、`0.5` 或 `None` 的混入可能被誤分類、靜默降級或在統計時排除。

**碼證**: `docs/EVTLABEL_TODO.md:256-274` 的實作要點是 `lab is not None` 後直接 `int(lab)`，auto 的 `present` 是欄位存在而非所有值通過 domain gate；`momentum/core/contracts.py:1063-1093` 的 `validate_event_given` 只做 finite＋逐值相等，不限制集合 `{0.0,1.0}`。現有 float 0/1 合法性實跑：`venv/bin/python -c '...validate_event_given...'` 輸出 `checked_samples=2, consumed_event_labels={e0:0.0,e1:1.0}`，但這不涵蓋非法值。RECHECK：records 注入 `2,-1,0.5,NaN,None`，`auto` 與 explicit binary 都必須在 staging 端給具名 non-retryable reason，不得進 `mann_whitney_table`。

**來源摘要**: docs/EVTLABEL_TODO.md#b58c476949a1, momentum/core/contracts.py#f817321f9e43

[MAJOR] 信心度=High；`mann_whitney_table` 的 y 契約是 `{0,1}`，但上游沒有將其變成可執行不變式；非 0/1 值若被轉成 int，會令 n_pos/n_neg 與實際列數不一致。修法：在 staging 以 finite、整數性、精確 domain、缺值完整性一次驗證；auto 對 mixed-null/invalid label 應有獨立 reason 並 loud 揭露。

### 必答 Verdict

1a. AUC／rank-biserial 是「正例分數是否整體高於負例」的合理 effect estimand；MW 是同一秩比較的 iid inferential test，但不是 out-of-sample ML 預測能力。AUC/rb＋MW＋BH 可以作起點，不能單獨證明可餵 ML，且 binary p 需處理時間依賴（P1-09）。

1b. 替代是保留 AUC/rb 作描述量，將 p/q 改成預先定義的 dependence-aware block/cluster null（無足夠 block 就 unavailable），並以 train-only selection＋獨立 test AUC 驗證 ML 可用性。165 筆全批可算；目前實際 test 31 筆、17/14 可算，但低於 class floor 或單類時應 loud unavailable，不能硬算。

2a. `mw_p_value_adj` 是 binary 對應的 p 閘候選；`ic_mean_min` 直接讀 rank-biserial 不成立（P1-05）。`icir`、hit-rate、monotonicity 在 binary 模式應只診斷不剔除，但既有 helper 只認 `event_label_value`，所以 imported binary 會錯誤重新啟用 ICIR（P1-06）。coverage/long-short 是否適用也必須在契約明定，不能因「三個 gate skip」而默認全都安全。

2b. Task 3.4 會改 stage3 的 label source、event_info 與 consumed binary key；Task 3.6 會改 summary 欄、排序、`_apply_thresholds` primary/p 欄；Task 3.8 會改 survivor payload。G-1/G-4 可抓 report summary/欄集的多數 return-rule 漂移，但抓不到 validated-cache swap、stage6/stage6b 的 return-label 消費、或 survivor artifact bytes（P0-02、P1-08、P1-11）。

3a. 以 config embargo=0、effective horizon=5 的已驗公式：h=1 close-to-close：label window=12、depth=144，改後 `purge=max(5,12)=12`、`embargo=max(0,144)=144`、總 156；改前 `5+max(0,144)=149`。route seed h=12 open-to-horizon-close：window=156、depth=144，改後 `purge=156`、`embargo=144`、總 300；改前 `5+156=161`。若 config embargo 更大，差值仍不會使改後小於改前。

3b. 在目前已驗的公式與 code path 下，改前 `embargo=max(config,max(depth,window))` 已使 `purge+embargo >= max(depth,window)`，所以沒有證據說改前曾洩漏；SPEC「現況不洩漏、語意錯位」可維持。P2 的實作傳遞仍有 P1-04 風險。

4a. `auto` 符合「有完整匯入 0/1 就接主線」的產品方向，但作為 API default 會讓同一 legacy request 因 label 欄位補齊而換 estimand；這不是無害的預設。若保留 auto，effective mode、原因、兩個 split 的類別數必須在報告與 UI 先揭露，且 mixed/低類別不得靜默當 binary。

4b. `min_events_per_class=10` 在文件中沒有統計依據；本批全批 29 個負例不代表 test 段永遠 ≥10。正確依據應是實際 selection scope 的每類最低可計算條件，並以預先定義的 power/precision 或 config contract 決定；不能只用一個全批常數。

5a. 若 `event_binary_label_by_id` 是獨立、不可變的 imported-record source，return 正確而 binary 錯位會被三元組值比對抓到；目前 contract 只比 event_id→value，且兩張 map 可同源生成，同值 timestamp 交換可通過，因此 SPEC 的現有檢查不足（P1-07）。

5b. 有：stage3 驗 A、stage5 讀 cache B 即可重現「驗了就丟」（P0-02）。必須用同一 validated token/digest 或 stage5 前再做三元組驗證。

6. 有 ≥10× 不必要複雜／未證明的風險：3.7 的逐 survivor×1000 permutation 沒有上界與 worst-case gate（P1-13）；3.1 JSON SoT 本身合理，3.10 真實 kline e2e 合理，但 sign oracle 不合理（P1-10）。

7. R-1 的 `needs-research` 對事件 HAC 有條件成立，但必須把 binary MW/置換的 dependence 問題一併納入；R-2 的 blocked-by 與 R-3/R-5 的 user-ruling 理由成立；R-6 的 split 模型差異成立但應避免重複實作。R-4 不成立為「已交付主目標」：它是主委的 scope 判斷，不是使用者裁定；現有 pattern bridge 有函式但沒有實際 consumer wiring，故列 P1-12。

8. 目前不能直接進實作；先修 P0/P1 的 SPEC/TODO acceptance 與資料契約，尤其 negative-control fail-closed、validated vector identity、binary gate propagation、P2 control channel、stage6/ML handoff。修訂後可進三 Phase 實作，無須把 P3 延後另開票。

### §1 十一類審查摘要

1 矛盾/互斥：有，P1-04、P1-06。 2 端到端漏項：有，P1-02、P1-08、P1-12。 3 不可測驗收：有，P1-03、P1-11、P1-13。 4 quant 假設：有，P1-05、P1-09、P1-10。 5 過度工程：P1-13；JSON SoT 本身無額外 finding。 6 OOM/並行：P1-13 有 CPU/預算風險，未見巢狀 ProcessPool。 7 cache 正確性：P0-02、P1-07。 8 API/型別/相容：P1-03、P1-04、P1-14。 9 測試品質：P0-01、P1-03、P1-10、P1-11、P1-13。 10 Agent 可執行性：P1-04 的「執行時以實跑定」未定案。 11 必要性/短命工：未另見短命白工；Task 1.1 的 contract keys 是被後續補值而非被刪除。

### 被當成事實的未驗證假設（§0）

- ASSUME-1：成立。`PYTHONPATH=. venv/bin/python handoffs/20260910-probe-label-rule.py` rc=0；stdout 顯示 `[h1_c2c] window_ms=43200000 ... label_window_feature_bars=12 ... lookahead_depth_rows=144 ... mismatch=0` 及 `[h12_seed] window_ms=561600000 ... label_window_feature_bars=156 ... mismatch=0`。
- ASSUME-2：部分成立、完整路徑未驗證。實跑同形純向量化核心 `venv/bin/python -c '...mannwhitneyu(...axis=0)...'` stdout=`seconds=0.413 shape=(39373,) finite=True`；這支持無 NaN clean path <10 秒，但不能代替 mixed-NaN/per-column path 的 benchmark。原文件所述「>60 秒」觀測未在本輪重現，不能當成已證事實。
- ASSUME-3：對有限 float 0.0/1.0 成立。實跑 `venv/bin/python -c '...validate_event_given...'` rc=0，stdout=`checked_samples=2, consumed_event_labels={e0:0.0,e1:1.0}`；這不證明非法 domain 會被擋，P1-14 仍成立。
- rank-biserial 可直接消費 `ic_mean_min`：推翻，見 P1-05；兩者 estimand/尺度不同。
- P2「只是語意錯位、不是洩漏」：在現有 probe 與 code 公式下成立；h=1 c2c 為 12/144、h=12 o2hc 為 156/144，改前總隔離不小於 label/depth max。P1-04 是新方案可能無法落地，不是對現況洩漏的反證。

STATUS: DONE
## COMPOSER-R1-P0-01

**斷言**: Task 3.6 计划让 `ic_mean_min` 门檻读取 **signed** `rank_biserial`，与同一 Task 排序键 `|rank_biserial|` 矛盾，会剔除强负向分离特征并放行弱正向噪声。

**碼證**: `_passes_threshold`（`ic_filter_orchestrator.py:5094-5101`）无 `abs`；现网 `_apply_thresholds` 对 `ic_mean` 用 `>= ic_mean_min`（`:4387-4388`）。SPEC Task 3.6 `:215` 写「`ic_mean_min` 闸改读 `rank_biserial`」且排序 `|rank_biserial|` desc。RECHECK: 构造 rb=−0.5、0.03 两特征，断言前者应 passed、后者 rejected（当前规则相反）。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a

[BLOCKING] 信心度=High。修法：Task 3.6／`event_label_mode.json` 增 `rank_biserial_min` 或明确规定 `_passes_threshold(abs(row[primary_field]), ...)`；mutation M-P3-2 扩展 signed-negative case。修订：SPEC Task 3.6 改法段、TODO B4 Task 3.6 要点 3。

---

## COMPOSER-R1-P0-02

**斷言**: `auto` 解析用 **全批** `min(n_pos,n_neg)≥10` 决定 `imported_binary`，但 Mann-Whitney 在 **test split 事件列** 计算且 `min_class_n` 同源——165 批 test 段预期 ~6 负例，导致系统性 `unavailable:class_below_min` 或零倖存者，与用户主目标「找出能分开正反例的特征」失效。

**碼證**: SPEC Task 3.3 `:182` auto 条件；Task 3.6 `:215-217` test scope + `min_class_n=cfg.min_events_per_class`；`ic_config_schema.py:121` 默认 `oos_test_size=0.2`（`:421`）。算术：29×0.2≈6<10。RECHECK: staging 测试断言 test 段 n_neg 与 MW status 分布。

**來源摘要**: docs/EVTLABEL_TODO.md#b58c476949a1

[BLOCKING] 信心度=High。修法：(i) auto 改查 test 段计数（需 orchestrator 回传或 service 预模拟 split）；(ii) 或拆分 `min_events_per_class_auto` vs `min_class_n_mw_test` 并在 JSON SoT 写清。修订：Task 3.3 边界、Task 3.6 边界①、G-5 oracle 样本量假设。

---

## COMPOSER-R1-P1-01

**斷言**: Task 3.3 要求扩展 `_assert_event_triple_bound` 查 `consumed_event_binary_labels`，但未要求 **imported_binary 模式下仍回比** `consumed_event_labels`（报酬第二栏）；现函数对非 `event_label_value` 直接 return（`:133-134`），报酬三元组 service 层零防护。

**碼證**: `api/services/ic_analysis_service.py:117-146`；SPEC Task 3.4 保留报酬验证在 stage3，Task 3.3 只列 binary 分支。RECHECK: imported_binary 集成测试 mutate `consumed_event_labels` 一字不改 binary ⇒ service 应 raise。

**來源摘要**: api/services/ic_analysis_service.py#eb592a4d3d04

[MAJOR] 信心度=High。修法：`_assert_event_triple_bound` 在 `imported_binary` 下 **双键** 回比；或 rename 为 `_assert_event_labels_bound` 并文档化两键语义。修订：Task 3.3 要点 5、TODO B3 验证段。

---

## COMPOSER-R1-P1-02

**斷言**: Task 2.2 依赖 `config_override.pop("event_purge_rows")` 在 `ICConfig.model_validate` 之前执行；TODO 写「执行时以实跑定」且 ICConfig 无该字段——agent 若 pop 顺序错误则 **静默丢失** purge 修正，G-2 可抓但非全局路径。

**碼證**: `_apply_config_override`（`ic_filter_orchestrator.py:4987-4994`）直接 `ICConfig.model_validate(merged)`；`ICConfig.model_config` 仅 `populate_by_name`（`ic_config_schema.py:418`），非 schema 键不进入 config。RECHECK: 注入 `event_purge_rows=12` 不 pop ⇒ metadata 仍为 purge_gap=5。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530

[MAJOR] 信心度=High。修法：TODO 2.2 **定死** `analyze()` 入口第一行 pop 两键；加 fail-closed 测试「override 残留进 ICConfig 即 raise」。修订：Task 2.2 改法、TODO B2 Task 2.2 输入输出段。

---

## COMPOSER-R1-P2-01

**斷言**: `auto` 默认 `imported_binary` 会改变报告 estimand（0/1 vs 规则报酬），仅靠 `label_mode.reason` 可能不足以让 UI 用户感知「与上次不同」；Task 3.9 DegradedBanner 条件过窄（仅 `requested=auto` 且 effective=return_rule 时显示？需对 effective=imported_binary 也显示模式摘要）。

**碼證**: SPEC §R `:289`「auto 预设开」；Task 3.9 `:245` banner 文案仅列 auto 回退分支。RECHECK: vitest 断言 imported_binary 报告顶部可见「IC 对你的 0/1 标签」。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a

[MINOR] 信心度=Medium。修法：Task 3.9 增「binary 生效」banner（非 degraded 也展示 mode 摘要）。修订：Task 3.9 改法、Task 1.2 第四行「已用」联动。

---

## COMPOSER-R1-P2-02

**斷言**: Task 3.7 倖存者逐特征 1000 次置換在倖存者数百级时增量成本未预算上限，且与 Task 3.5 全表 MW 叠加可能逼近 SPEC「总增量 <2 分钟」边界。

**碼證**: SPEC Task 3.7 `:223-226`；§V 性能 `:281`。RECHECK: B4 receipt 印 `n_survivors * n_perm` 与 wall time。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a

[MINOR] 信心度=Medium。修法：Task 3.7 增 `max_oracle_survivors` cap 或 tier-aware `n_perm`；不删 oracle。修订：Task 3.7 边界、§V 性能段。

---

## GROK-R1-P0-01

**斷言**: Task 3.6 若把 `ic_mean_min` 閘改讀 signed `rank_biserial` 並沿用 `_passes_threshold` 的 `value >= threshold`，會錯誤剔除 `rank_biserial < 0` 的強分辨特徵；與同 Task 的 `|rank_biserial|` 排序及 Task 3.7 負對照 `|rb|>=ic_mean_min` 自相矛盾。

**碼證**: 現行閘 `ic_filter_orchestrator.py:4387`+`:5094-5101` 為 signed `>=`（無 abs）；SPEC Task 3.6 閘讀 `rank_biserial`、排序用 `|rank_biserial|`；TODO Task 3.7 負對照用 `|rb|>=ic_mean_min`。RECHECK：植 `rb=-0.8` 特徵，僅改 `primary_field` 不取 abs ⇒ 進 `removed["ic_mean"]`。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a

[BLOCKING] 信心度=High。會怎麼失敗：所有「特徵值在負類較高」的分辨器被幅度閘殺光，只留同向弱訊號；主目標假陰性。  
**修法（SPEC/TODO Task 3.6）**：明寫幅度閘讀 `|rank_biserial|`（或等價 `|auc-0.5|*2`）；`_apply_thresholds` 對 binary 走 abs 比較；驗證＋mutation 加「負向植入仍 passed」。全域／`return_rule` 預設路徑一字不改（G-1／G-4）。

---

## GROK-R1-P1-01

**斷言**: 現行 `_assert_event_triple_bound` 在 `label_source != "event_label_value"` 時直接 return；Task 3.4 把 `label_source` 改成 `imported_binary_label` 後，若不先改寫此守衛，報酬三元組回綁會被跳過，且 TODO「新增 binary 分支」若寫在 return 之後會成死碼。

**碼證**: `api/services/ic_analysis_service.py:133-135` 於 `label_source != "event_label_value"` 直接 return；Task 3.4 改 `imported_binary_label`；TODO 3.3 只寫「新增分支」未改守衛。RECHECK：旋轉 `consumed_event_binary_labels` 一值，守衛未改 ⇒ 不 raise。

**來源摘要**: api/services/ic_analysis_service.py#eb592a4d3d04

[MAJOR] 信心度=High。修法：改寫為依 `label_source` 分派——`event_label_value` 回比報酬；`imported_binary_label` **同時**回比報酬鍵（第二欄仍在）＋`consumed_event_binary_labels` vs `bin_by_id`；其他 source 維持既有 early-return／fallback 語意。位置：TODO Task 3.3 要點 5＋SPEC Task 3.3／3.4 邊界。

---

## GROK-R1-P1-02

**斷言**: TODO Task 3.4 要點 2 呼叫 `validate_consumed_label(..., label_source="imported_binary_label", ...)`，但實際函式簽名只有 `label_kind=`（無 `label_source` kwarg）⇒ 實作端會 TypeError 或誤接。

**碼證**: TODO Task 3.4 要點 2 寫 `label_source="imported_binary_label"`；SPEC 寫 `label_kind=event_given`；實際簽名 `contracts.py:1110-1131` 僅有 `label_kind=`。RECHECK：傳 `label_source=` ⇒ TypeError。

**來源摘要**: docs/EVTLABEL_TODO.md#b58c476949a1

[MAJOR] 信心度=High。修法：TODO 改與 SPEC／簽名一致：`label_kind=derive_label_kind("imported_binary_label")`（或字面 `event_given`）；回傳之 `consumed_event_labels` 再存入 `consumed_event_binary_labels`。

---

## GROK-R1-P1-03

**斷言**: SPEC Task 2.2 與 TODO Task 2.2 對 `embargo_source` 的寫入點互相矛盾（orchestrator 四鍵 vs service `_inject_isolation_source`），Agent 會實作分叉，G-3／隔離區揭露斷言會漂。

**碼證**: SPEC Task 2.2 要 orchestrator 寫含 `embargo_source` 的四鍵；TODO Task 2.2 要點 2 改由 service `_inject_isolation_source` 寫。RECHECK：若鍵只在 `metadata.isolation` 不在 `ic_train_test_split` ⇒ G-3 字面 FAIL。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a

[MAJOR] 信心度=High。修法：兩檔定死單一寫入點。建議採 TODO 路線（service 知 `embargo_before_event`）但 **SPEC G-3／Task 2.2 同步改寫**為：`ic_train_test_split` 可不含 `embargo_source`，改由 `metadata.isolation.embargo.source` 承載；或 orchestrator 吃 service 預先放入 override 的 `embargo_before_event` 後自寫——二擇一寫進兩檔。

---

## GROK-R1-P1-04

**斷言**: Task 3.3 `auto` 以**全批**兩類 ≥ `min_events_per_class` 決定 `imported_binary`，但 Task 3.5／3.6 主統計在 **test split 事件列**上算；全批過關、test 段一類 `< min` 時會變成「模式已是 binary、特徵全 `unavailable:class_below_min`、倖存者 0」——對使用者主目標是靜默／半靜默失敗。

**碼證**: Task 3.3 auto 用全批 n_pos/n_neg；Task 3.6 統計在 test 事件列。實跑受理 run 全批 136/29、test 17/14（本 run 過關）；`oos_test_size=0.2`。RECHECK：fixture 全批 20/20、test 18/2 ⇒ effective=imported_binary 且全表 class_below_min。

**來源摘要**: docs/EVTLABEL_SPEC.md#f25aa6c7d37a

[MAJOR] 信心度=High。修法（擇一寫進 SPEC Task 3.3／3.6）：(A) `auto` 改為「全批 ≥10 **且** 預估 test 段兩類 ≥10（或切分後再確認）」否則 `return_rule`＋`reason=class_below_min_test`；(B) 維持全批 auto，但 test 不足時 **loud degrade**（`label_mode.reason`＋DegradedBanner 必顯、不得只靠 per-feature unavailable）。並把 brief 表「test 段每類 ≥10 是否常態」從 NOT_RUN 升為具名驗證。

---

## GROK-R1-P2-01

**斷言**: 即使改為 `|rank_biserial| >= ic_mean_min(0.02)`，在 165／test≈31 事件下該幅度閘對 null 幾乎無篩選力（null SE(rb)≈0.12–0.25，P(|rb|>0.02)≈0.87–0.95）；真實篩選幾乎只靠 MW→BH。

**碼證**: `ic_mean_min=0.02`（`ic_config_schema.py:121`）；null SE(rb) 全批≈0.118、test 17/14≈0.24 ⇒ P(|rb|>0.02)≈0.87–0.95。RECHECK：null 標籤重抽 1000 次看通過率。

**來源摘要**: momentum/Analysis/ic_config_schema.py#1fd5a87b63b5

[MINOR] 信心度=Medium。非阻實作；須在 SPEC Task 3.6／白話頭條寫明「binary 模式幅度閘近乎 no-op、主閘＝FDR」，或另定樣本數感知門檻／改只走 p 閘。勿 silently 假設與連續 IC 的 0.02 同義。

---

## GROK-R1-P2-02

**斷言**: SPEC／TODO 缺「stage5 實際餵進 `mann_whitney_table` 的 y／列索引＝stage3 已過 `validate_event_given` 的 binary 序列」之 spy／mutation（EVTALIGN「驗了就丟」同類），僅靠植入 oracle 間接護。

**碼證**: EVTALIGN 有 `test_validated_series_is_used_series.py`；本票 mutation 僅 M-P3-1..4，無換 cache 鍵項。RECHECK：stage5 改讀 `filtered_label`（報酬）⇒ 植入 0/1 oracle 紅。

**來源摘要**: docs/EVTLABEL_TODO.md#b58c476949a1

[MINOR] 信心度=High。修法：TODO Phase3 測試段加 spy（或 M-P3-5）；對齊 EVTALIGN Task 2.2 形狀。

---

## 戳記

RECONCILE-STAMP: codex APPROVED 2026-09-10 sha256:3894fd9057df5732dc6e97785adad96548461f1a38ad494bffab4c83f2007ed7 task:20260910-EVTLABEL-X-STAMP-R1
RECONCILE-STAMP: composer APPROVED 2026-09-10 sha256:3894fd9057df5732dc6e97785adad96548461f1a38ad494bffab4c83f2007ed7 task:20260910-EVTLABEL-X-STAMP-R2
RECONCILE-STAMP: grok APPROVED 2026-09-10 sha256:3894fd9057df5732dc6e97785adad96548461f1a38ad494bffab4c83f2007ed7 task:20260910-EVTLABEL-X-STAMP-R3
