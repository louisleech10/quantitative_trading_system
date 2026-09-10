# Reconcile — 20260910-evtlabel-b1-review-r1

**來源** 20260910-evtlabel-b1-review-r1-codex.md, 20260910-evtlabel-b1-review-r1-composer.md, 20260910-evtlabel-b1-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**輪次計數**：codex 4（2×P1、2×P2）、composer 1（1×P2 標 MAJOR）、grok 3（2×P2、1×P3）＝ **8 條**；P0＝0。
Verdict 分歧：composer／grok **可進 B2（無 P0/P1）**；codex **需修 P1-01／P1-02 才可進**。
**採 codex**（不數人頭看碼證）：P1-01 是我引入的真缺陷（揭露分母 ≠ 實際消費），P1-02 三家皆指出且有實測秒數。**兩條當場修完**。

Verdict: 需修補後合併（F1–F3 已於本輪修完並實測；F4–F6 為具名殘留／文件，不擋 B2）

---

### F1 🔴 揭露分母 ≠ 實際被消費的事件（真缺陷，本輪修完）
**ID**：`CODEX-R1-P1-01`
**碼證**：`_stage_event_batch` 以 `run_symbol` 排除非本次 symbol 之事件（`excluded_by_symbol`），但 `build_event_label_rule` 收的是**全批** `prepared.windows`／`records` ⇒ 混 symbol 批之 `imported_binary_label` 計數、`label_window_feature_bars`、`uniqueness` 與 `n_events_consumed` 分母不一致。
**處置（已做）**：`build_event_label_rule(..., consumed_event_ids=...)`，service 傳 `staged["event_label_by_id"].keys()`（＝實際消費集合），先裁 windows／records 再算。
**加碼**：撰測時發現「id 不同源會靜默產出空揭露」之次生失效 ⇒ 改 **fail-closed**（`keep` 非空、`win` 非空、交集為空 ⇒ raise）。測試 `test_disclosure_scoped_to_consumed_events_only`＋`test_consumed_ids_mismatch_is_loud`。

### F2 🔴 `uniqueness_from_windows` O(n²)、事件數無上限（本輪修完）
**ID**：`CODEX-R1-P1-02`、`COMPOSER-R1-P2-01`、`GROK-R1-P2-01`
**碼證**：三家獨立指出；composer 實測 10k 事件約 5s、codex 指出 50MiB 上傳可產生任意長 list。
**處置（已做）**：改 **O(n log n)**——`counts[i] = n − |{end_j ≤ start_i}| − |{start_j ≥ end_i}|`，兩個補集以排序陣列二分搜尋取得；`pairs = (Σcounts − n)/2`。半開區間語意**逐字不變**。
**不採**「加事件數上限」：那是替真正的複雜度問題找門檻（且門檻無依據）；改算法後上限問題消失。
**測試**：20 組隨機重疊形態（含巢狀／同端點／完全重合）與暴力法逐項相等；10,000 事件 `< 2.0s`（O(n²) 回歸即紅）。

### F3 計時未在 analyze 入口重置（本輪修完）
**ID**：`CODEX-R1-P2-03`
**處置（已做）**：`analyze` 入口 `self._stage_timings = {}`；同一次 analyze 內 fallback 重跑之累加**維持**（刻意，已於裝飾器 docstring 具名）。測試以 `inspect` 斷言「重置在第一個 stage 之前」。

### F4 7 個 `ui_only` 開關＝具名 no-op（不擋；登記殘留）
**ID**：`CODEX-R1-P2-04`
**裁定**：codex 逐個查證後確認**我的分類屬實**（存在底層方法／config，但 UI toggle 不改任何 backend boolean）⇒ 不是隱藏幽靈。但「UI 給了開關卻按不動」本身仍是缺口 ⇒ 登記 **EVTLABEL R-9**（`為何現在不做: needs-research:七個開關各自對應的後端能力是否該接線、接哪一個旗標，須逐個定義`；觸發＝使用者發現某開關按了沒反應）。

### F5 mixed timeframe 之 `label_window_feature_bars=max` 可能誤導（不擋）
**ID**：`GROK-R1-P2-02`
**裁定**：UI 端**已自動退化**——`ratio_integral=false` 時 `labelRuleLines` 不顯示「第 N 根」，只寫「單位＝事件週期的根數」（`icLabelRule.test.ts` 有釘）。metadata 之 max 僅供 P2 purge 取保守值（偏保守不洩漏）。⇒ 現況不誤導；併入 R-B10-1 拆批討論，不在 B1 改。

### F6 fallback 累加使單一 stage 秒數看似異常大（不擋）
**ID**：`GROK-R1-P3-01`
**處置**：已於 `_timed_stage` docstring 與 F3 註解具名「同一次 analyze 內累加是刻意的」；UI 顯示留待 GLOBALH 一併設計（該票才會把耗時搬上畫面）。

---

### §0 假設裁定
- 「7 個 ui_only 真的沒接線」：**成立**（codex 逐個查證）⇒ 但升級為具名殘留 R-9。
- 「`stage_timings` 依鍵名全域排除不誤吃」：三家未提出反例 ⇒ 暫成立（grep 全 repo 無同名鍵）。
- 「事件批規模不成問題」：**推翻**（F2）⇒ 已改算法。
- 「mixed tf 取 max 正確」：**部分保留**（F5：metadata 保守可、UI 已退化）。

### 不採納
- composer／grok 之「可進 B2、無 P1」：不採納其嚴重度判定（P1-01 為真缺陷）；但其「不擋 B2」之結論在**修完後**成立。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: symbol 過濾只作用於 IC 映射，event_label_rule 仍消費全批 windows/records，會把排除 symbol 算入揭露。
**碼證**: target `ic_analysis_service.py:740-809`；probe stdout=`n_events_consumed=1 label_window_feature_bars=156 n_eff=2.0 pairs=0`。
**來源摘要**: api/services/ic_analysis_service.py#d1129658e966
[MAJOR] 信心度=High；混批時 consumed 與 label/uniqueness/disclosure 分母不一致。最小修法是以同一 selected event-id 集合裁切 windows 與 records，或由 helper 接收 consumed IDs。
## CODEX-R1-P1-02
**斷言**: `uniqueness_from_windows` 對可由 50MB 上傳產生的任意 JSON list 做 O(n²) 兩兩掃描，沒有事件數上限。
**碼證**: target `event_label_mode.py:46-71`、`case_import_service.py:641,688-703`；benchmark stdout=`n=1000 .046610s; n=2000 .190288s; n=4000 .757902s`。
**來源摘要**: momentum/Analysis/event_label_mode.py#b8b10fcca34a; api/services/case_import_service.py#ff8c73a088b0
[MAJOR] 信心度=High；大 JSON 會使分析延遲/資源耗盡。最小修法是保留半開區間語義改 O(n log n)/sweep，或採經批准的輸入 budget；不可臆造門檻。
## CODEX-R1-P2-03
**斷言**: `_timed_stage` 的 lazy 累加未在 `analyze` 邊界 reset，重用 analyzer 可能回報跨次或 stale stage_timings。
**碼證**: target `ic_analysis_service.py:121-147,1053-1103`；probe=`two stage calls -> {'stage0_ingestion': 0.0}; analyze_resets_stage_timings=False`；factory 每 task 新建，故非當前主路徑阻斷。
**來源摘要**: api/services/ic_analysis_service.py#d1129658e966; tests/momentum/helpers/ichc_run.py#35e1c3ed4397
[MINOR] 信心度=Medium；在明確的 analyze-scoped reset 與 fallback 累加語義間加邊界即可。
## CODEX-R1-P2-04
**斷言**: UI 的七個控制是契約明列的 `ui_only`，存在 underlying method/config 但 toggle 不改 backend boolean；不是未具名幽靈，仍是具名 no-op 殘留。
**碼證**: FeatureTierPanel 全部 25 toggle 逐一對照 exact-key grep；七鍵=`ic_method_selection,winsorization_method,monotonicity_test,return_type_selection,ic_autocorrelation,redundancy_method_selection,vif_filter`。
**來源摘要**: frontend/src/components/ic-analysis/FeatureTierPanel.tsx#51af6880bfbc; momentum/Analysis/contracts/ui_stage_toggles.json#39d80161096a
[MINOR] 信心度=High；若 acceptance 要求每個 UI toggle 可操作，需另立 wiring task；依現行契約分類本身不否決本批。
## COMPOSER-R1-P2-01

**斷言**: `uniqueness_from_windows` 為 O(n²) 且事件匯入**無硬上限**；在已驗證的 10k 規模單次揭露約 5s，萬級匯入（`gap3_import_scale.json`）會使事件 run 收尾可感知變慢，與 R-1「只揭露」初衷衝突。

**碼證**: `momentum/Analysis/event_label_mode.py:46-72` 雙層 `for i/j`；`api/services/case_import_service.py` 無 `n_records` cap；`handoffs/run_receipts/gap3_import_scale.json` `n_events: 10000`；VERIFY: `venv/bin/python` benchmark → `n=165/0.001s n=1000/0.046s n=5000/1.216s n=10000/4.782s`

**來源摘要**: momentum/Analysis/event_label_mode.py#460de95db893

[MAJOR] 信心度=High。事件分析完成時 `_inject_label_rule_disclosure` 必呼叫 `build_event_label_rule` → `uniqueness_from_windows`；10k×10k 比較在 API 執行緒上阻塞數秒，與已記錄的 10k 匯入規模同階。修法（B2 或 R-1 收案）：① 匯入／揭露前 `n_events` 上限（契約登記）；②  sweep-line 相交計數 O(n log n)；③ `n>阈值` 時 `uniqueness` 各鍵 `null`＋`note=skipped_large_n`。**不阻 B1 合併**（R-1 已標不參與計算；165 事件實測 0.001s）。

---

ASSUMPTIONS_VERIFIED: ui_only 七鍵無後端 toggle 路徑（rg＋`:3710`）；stage_timings 僅一處 metadata＋ichc_run 排除；gap2 golden 10/10；tier pytest 25+14；uniqueness benchmark 至 10k；R3 `create_event_sample_pipeline().build_event_label_rule` 無 `api→Analysis` 直 import
TESTS_RUN: `venv/bin/python -m pytest tests/api/test_evtlabel_disclosure.py tests/momentum/test_stage_timings.py tests/momentum/test_tier_toggle_sync.py -q` → 25 passed rc=0；`venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py tests/api/test_isolation_disclosure.py -q` → 10 passed rc=0；`venv/bin/python -m pytest tests/momentum/test_tier_config.py tests/api/test_tier_api.py -q` → 14 passed rc=0；uniqueness benchmark（見 P2-01）
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀 review）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）；本批新增 `metadata.event_label_rule`／`metadata.stage_timings` 為預期 schema 擴充

產出: `handoffs/20260910-evtlabel-b1-review-r1-composer.md`

TMP_CLEANUP: 清 `/tmp` workdir（保留 `claude-501`）

STATUS: DONE
## GROK-R1-P2-01

**斷言**: `uniqueness_from_windows` 為 O(n²) 且事件匯入無 `n_events` 硬上限（僅 50MiB 檔頂 ≈15k 事件），大批次會讓每次事件分析僅為揭露就多出十秒級成本。

**碼證**: `event_label_mode.py:46-72` 雙重迴圈；`case_import_service.py` `EventImportService.MAX_FILE_SIZE=50*1024*1024`、契約／route 無 n_events cap。本輪 bench：n=165≈0.002s；n=10000≈8.5s；n=15000≈13.3s（重疊 cascade）。RECHECK：同上 bench；或造 50MiB 邊界 JSON 跑一次 analyze 看 `event_label_rule.uniqueness` 耗時。

**來源摘要**: momentum/Analysis/event_label_mode.py#460de95db893

[MINOR] 信心度=High。失敗模式：大 CSV 匯入後分析「卡住」在揭露階段；IC 主算尚未開始。P1 只揭露不入算 ⇒ **不擋 B2**。修法（擇一，可另開小票）：(a) 匯入／analyze 加 `n_events` soft/hard cap 並寫契約；(b) 改排序線掃 O(n log n)；(c) n>N 時 uniqueness 改 `unavailable:too_many_events` 並 loud。勿為過早優化改 P3 權重路徑。

---

## GROK-R1-P2-02

**斷言**: 批內 mixed timeframe 時 `label_window_feature_bars=max(窗)` 會讓較短事件週期列的 h／單位文案被高估；與同檔已對「purge 下界分歧」採 fail-closed 的態度不一致。

**碼證**: SPEC Task 1.1 邊界①＋`event_label_mode.py:101-120`＋`test_mixed_timeframes_degrade_ratio` 釘 max=12；對照 `ic_analysis_service.py:699-706` 對 distinct `purge_lower_bound_ms` raise（禁靜默 max）。RECHECK：12h×1bar + 4h×1bar 混窗 ⇒ `event_timeframe=mixed`、`label_window_feature_bars=12`（4h 列被說成 12 根 1h）。

**來源摘要**: docs/EVTLABEL_SPEC.md#f84a16b6c4da

[MINOR] 信心度=Medium。同質批（受理 165×12h）無感。混批若進 B2 用此 max 做 purge ⇒ **偏保守不洩漏**，但 UI「第 N 根」對短 tf 誤導。修法：混批 fail-closed（拆批），或揭露改 per-tf／逐事件窗；與 R-B10-1 拆批文案對齊。不擋同質批 B2。

---

## GROK-R1-P3-01

**斷言**: `@_timed_stage` 對同名 stage **累加**；full-sample fallback 重跑 analyze 時 `stage5`／`stage6`／`stage6b` 等秒數會疊成「單次 stage 看起來異常大」，屬揭露語意而非算錯。

**碼證**: `ic_filter_orchestrator.py:121-144` docstring 明寫累加；`_run_full_sample_fallback` 再入 `analyze`；`test_stage_timings.py` 斷言第二次 ≥ 第一次。RECHECK：強制走 fallback 之 fixture，讀 `metadata.stage_timings.stage6b_marginal_ic` 是否約為兩次之和。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py（`_timed_stage`）

[MINOR] 信心度=High。建議 UI／文件註「含 fallback 重跑累加」，或 key 改 `stage6b_marginal_ic` vs `…_fallback` 分列。非阻擋。

---


## 戳記
