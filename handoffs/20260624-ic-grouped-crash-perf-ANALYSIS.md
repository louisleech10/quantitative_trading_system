# IC analyze 崩潰 + 超慢 — Claude 分析（委員會底稿）

> 2026-06-24 ｜ 觸發：使用者在 ic-analysis 選 run 跑 analyze → 卡很久 → 崩潰 + WebSocket 失敗
> 用途：委員會 challenge 底稿（feedback_claude_own_version：Claude 先自產一版）

## 0. 現象
- 計算很慢、中間卡很久；Terminal 大量 `Decay fit quality low (R2=0.00x)` warning。
- 最後 `ERROR: 'GroupedConfig' object has no attribute 'get'`，前端 WebSocket 連線失敗。

## 1. 已驗證事實（實查）
- **崩潰點**：`ic_filter_orchestrator.py:1139` 傳 `config.ic_calculation.grouped_analysis`（型別 = pydantic `GroupedConfig`，定義 ic_config_schema.py:76）給 `ic_engine.compute_grouped_ic(config)`，後者 `ic_engine.py:377 config.get("method")` 是 **dict API** → pydantic 無 `.get` → AttributeError。
- **觸發條件**：`config.report.include_regime_analysis=True`（orchestrator:1133）才走 grouped_ic 分支。
- **非本次 run-selector 改動引入**：`git diff momentum/Analysis/ic_engine.py` = 空；ic_engine 我沒碰。run-selector 只是讓「能選 run 跑 analyze」這條路徑變可達，把既存 bug 暴露。Composer 實作時在測試 config 關掉 regime/decay 繞過（IMPL handoff 自承「grouped_ic/regime 預存 bug」），未修真因。
- **run 規模異常**：log 實見 `1696 rows x 45421 cols`——選到的 run 有 **45,421 個特徵**（同 symbol/tf 另一 run 僅 73）。
- **per-feature 熱迴圈 log**：`compute_ic_decay` ic_engine.py:347 `for feature in features_df.columns:` 內逐特徵 `logger.warning("Decay fit quality low")`；本次 log 共 **14,090 條**。違反 CLAUDE.md「熱迴圈不 log」；log I/O × 1.4 萬 = 顯著拖慢。

## 2. 兩個獨立問題

### 問題 A：崩潰（型別契約不一致）
`compute_grouped_ic` 的 `config: dict` 契約 vs 呼叫端傳 pydantic `GroupedConfig`。
**修法候選**：
- (A1) 呼叫端傳 `grouped_analysis.model_dump()`（最小改、就地修）。
- (A2) `compute_grouped_ic` 改吃 typed `GroupedConfig`，內部用屬性存取（型別更安全，但要同步其他 caller）。
- (A3) `compute_grouped_ic` 開頭相容 `if not isinstance(config, dict): config = config.model_dump()`（防禦式，但掩蓋契約問題）。
- 傾向 A1 或 A2；A3 是 band-aid。**須先 grep compute_grouped_ic 其他 caller 確認契約**。

### 問題 B：超慢
**根因疊加**：
1. **45,421 特徵**：IC/decay/grouped 多為 O(features × …)；互動式跑 45k 特徵本身不切實際。為何這 run 這麼大？（FF 生成的 lag×window×indicator 笛卡爾積？config 問題？）
2. **per-feature 熱迴圈 logging（14,090 條）**：違規 + log I/O 拖慢。
3. **decay/grouped 逐特徵 Python 迴圈**（:347、:300）可向量化/並行。
4. 最後崩潰 → 全部白算，使用者體感「卡死」。

**改善槓桿（暫排序）**：
- (B1) **修 per-feature logging**：改聚合摘要（如「N 個特徵 R2<0.1」一行），熱迴圈零 log。低風險、立竿見影。
- (B2) **修崩潰 A**：否則再快也白算。
- (B3) **45k 特徵的上游**：IC 前是否該先 pre-filter / cap 特徵數？或 UI 對超大 run 警示/分批？（命中正確性：別默默截斷）
- (B4) decay/grouped 向量化或並行（命中 (d) 正確性，需 golden 防回歸）。
- (B5) decay 對 R2 過低特徵 early-skip（省算，但要確認不影響下游選因子語義）。

## 3. 給委員會的問題
1. 問題 A 修法選 A1/A2/A3 哪個？compute_grouped_ic 其他 caller 契約？
2. 45,421 特徵是否本身就是問題（FF config / 設計）？IC 互動式分析該不該 cap/pre-filter？
3. B 的槓桿優先序；B4/B5 是否動到 IC 數值正確性（need golden）？
4. 這是否該獨立為「IC 效能 + grouped_ic 契約修復」epic，與本次 run-selector 分開 commit？

---

## 4. 委員會 reconcile（codex 後端/正確性 + cursor 上游/UX，2026-06-24）

### 三方共識根因（按對「慢+卡死」貢獻排序）
1. **幽靈 feature_filter（cursor 揪，最大元兇）**：前端送 max_features=30（icAnalysisStore.ts:187, useICAnalysis.ts:156-176），後端寫 feature_filter（ic_analysis_service.py:967-970），但 ICConfig schema 無此欄（ic_config_schema.py:319-353）、momentum/Analysis 零處理 → 全量跑 45k。**假過濾真全量**。
2. **event loop 阻塞（cursor 揪）**：主 analyze 用 create_task 但 analyzer.analyze() 同步阻塞（ic_analysis_service.py:209-216），不像 deep analysis 用 asyncio.to_thread → 45k 計算佔住 event loop → WS heartbeat 斷 → 使用者只見「WebSocket 連線失敗」+ 卡死。
3. **崩潰 GroupedConfig（已確認）**：orchestrator:1139 傳 pydantic 給 dict-API → A1 model_dump 修；**須補真 config + include_regime_analysis=True 回歸測試**（現有測試用 SimpleNamespace+dict 沒打到真路徑，codex 揪）。
4. **per-feature logging 14090 條**：_fit_exponential_decay:943-947 逐特徵 log → 改聚合摘要（codex 詳法：回傳 r2/reason，compute_ic_decay 結尾一條統計）。
5. **WS 錯誤處理**：failed 不 setError(message)、onerror 無條件覆蓋、onclose 無限重連（useICAnalysis.ts:88-117）→ 使用者看不到真錯誤。
6. **無 cancel / stage4 無子進度 / 選 run 即拉 45k 名稱**（cursor）。

### 既存隱患（順手記，非本次觸發）
- `_get_time_index` numeric timestamp 當毫秒（ic_engine.py:1021）→ kline 若為秒則 grouped IC 軸錯（timestamp 老問題重演）。
- `by_volatility` schema 預設 true 但 compute_grouped_ic 無此分支（契約漂移）。
- cross-sectional 擋 >50 但 longitudinal 無上限（半成品 policy）。

### Epic 切分（cursor 提，三方認同；與 run-selector 分開 commit）
| Epic | 內容 | 優先 |
|------|------|------|
| IC-CRASH | GroupedConfig A1 + 真 config 回歸測試 | P0 |
| IC-FEATURE-GUARD | 落地 feature_filter（解幽靈，最大速度槓桿）+ 大 run 警示/阻擋 + metadata 記原始/篩後數（不靜默截斷） | P0 |
| IC-UX-ERR | analyze 改 to_thread + WS failed 處理 + HTTP poll fallback + 停無限重連 | P0 |
| IC-PERF | decay log 聚合 + stage4 子進度 + cancel | P1 |
| IC-PERF-DEEP | decay/grouped 向量化（golden，命中 d） | P2 |

### 正確性紅線（三方）
- 不靜默 cap/截斷特徵（會改 feature universe 語義）；feature_filter 落地須 metadata 記錄可審計。
- B5 R2 early-skip 別做（half_life/decay_rate 被 summary 消費）；B4 向量化只在 golden 下做。
