# IC Phase 0 TODO — Adversarial Review（Composer 2.5 / Cursor）

> 2026-06-25 ｜ 審查主體：`docs/IC_PHASE0_TODO.md`  
> 對照：`docs/IC_PHASE0_SPEC.md` v2、`handoffs/20260625-ic-PHASE0-ADVERSARIAL-RECONCILE.md`、`handoffs/20260625-ic-PHASE0-MANIFEST.md`  
> 程式引用實測：`ic_engine.py`、`ic_filter_orchestrator.py`、`ic_config_schema.py`、`ic_analysis_service.py`、`useICAnalysis.ts`、`icAnalysisStore.ts`

## Verdict：需修補後派工

TODO 整體忠實承接 reconcile 後 SPEC（R-1~R-12 主幹已落），30 manifest ID 均有掛載，引用行號多數正確。但 **[M-5] Golden 無可執行 Task**、decay 驗收自相矛盾、前端 failed 路徑與真實 WS/poll 契約不符、feature_filter 欄位命名與 `truncation_mode` 語義未定義——冷啟動 agent 會在這幾處猜錯或 Phase Gate 無法過。修補後可派工，非整份重作。

## Findings

### 挑戰前提（§0）

1. **[BLOCKING|High]** reconcile R-6 / `[M-5]` Golden（grouped mask hash、decay 結構化 float、feature_filter sha256）僅寫在 Phase Gate 段落，**無獨立 Task** 建立 `tests/fixtures/ic_phase0/baseline_*.json` 或 `pytest` golden 模組。  
   **證據**：Phase Gate「Golden `[M-5]`…baseline 存 `tests/fixtures/ic_phase0/baseline_*.json`」；全檔無 `test_ic_phase0_golden` / baseline 凍結步驟；`glob tests/fixtures/ic_phase0/**` → 0 檔。  
   **會怎麼失敗**：agent 做完 B1–B4 後 Phase Gate「golden 不 FAIL」無測試可跑；或各 Task 自寫零碎斷言，漏掉 mask hash / 結構化 float 比對，假綠過 gate。  
   **修法**：新增 Task（或擴 2.2/3.5/4.2）：(1) 修 C+T 後用 SPEC §G 固定輸入凍結 baseline；(2) `tests/momentum/test_ic_phase0_golden.py` 含 grouped mask hash + decay `np.isclose` + feature_filter sha256；通過條件寫死檔名與命令。

2. **[MAJOR|High]** SPEC §A#6 / Task 4.3 仍承襲「event loop 阻塞」為 **assumed**（SPEC 標 assumed；TODO 未要求實測 heartbeat）。  
   **證據**：SPEC §A#6「未實跑 heartbeat 證據」；Task 4.3 驗證僅 mock 建議、無 baseline 失敗案例。  
   **會怎麼失敗**：`to_thread` 改錯層（例如只包外層、內層仍阻塞）時測試仍綠。  
   **修法**：Task 4.3 驗證欄寫死：在 `tests/api/test_ic_analysis_service.py` 新增用例——patch `analyzer.analyze` sleep 2s + `asyncio.wait_for(gather(sleep×N, start_task), timeout<2)` 必須 pass；並註明改動前用同測試確認紅。

### §1 十類

3. **[BLOCKING|High]** Task 4.1 只要求移除 `_fit_exponential_decay` **:944** R2 warning，Task 4.2 要求「per-feature warning 數==0」。同一函式熱迴圈尚有 **:904** insufficient_points、**:918** low_variance、**:958** fit_exception 的 `logger.warning`（已讀碼確認）。  
   **證據**：Task 4.1「移除 `logger.warning("Decay fit quality low...")`」；Task 4.2「per-feature warning 數==0」；`ic_engine.py:903-958`。  
   **會怎麼失敗**：agent 只刪 :944 → caplog 測試紅；或 agent 刪光所有 warning 但 SPEC 只授權聚合 R2 類 → 與「數值不變」驗收邊界不清。  
   **修法**：Task 4.1 明寫「熱迴圈內所有 `logger.warning` 移出或改為迴圈外聚合（含 insufficient_points/low_variance/fit_exception）」；Task 4.2 對應列出允許的 log 層級（僅結尾一行 `info`）。

4. **[MAJOR|High]** Task 4.4 / `[U-2]`「failed → `setError(status.error)`」與真實契約不符：WS progress payload 用 **`message`** 承載錯誤（`ic_analysis_service.py:246-251`），`ICTaskStatusResponse` 才有 **`error`** 欄；`useICAnalysis.ts` onmessage 僅處理 progress/ping，**未在 `status==='failed'` 時 setError**；`fetchTaskStatus`（:194-201）也未讀 `error`。  
   **證據**：Task 4.4「failed → `setError(status.error)`」；service `_notify_callbacks` `"message": str(exc), "status": "failed"`；`useICAnalysis.ts:85-104` 無 failed 分支。  
   **會怎麼失敗**：agent 找不存在的 `status.error` WS 欄位；或只改 onclose 仍顯示「WebSocket 連線失敗」（:107），後端真錯誤被蓋掉。  
   **修法**：Task 4.4 寫死兩路：(1) WS `message.event==='progress' && data.status==='failed'` → `setError(data.message ?? data.error)`；(2) poll `fetchTaskStatus` 若 `status==='failed'` → `setError(response.error)`。vitest 模擬兩路分開斷言。

5. **[MAJOR|High]** Task 3.3 `truncation_mode: "preview"|"none"` **未定義判定規則**；R-3 reconcile 要求 preview 語義由 metadata 表達，但 TODO 未寫何時為 preview。  
   **證據**：Task 3.3「`truncation_mode("preview"|"none")`」；Task 3.2 只寫 max_features 截斷，未映射到 preview。  
   **會怎麼失敗**：僅 `include_categories` 篩選時 agent 任意填 preview/none；metadata 不可審計比對失敗。  
   **修法**：寫死：`truncation_mode="preview"` 僅當 `max_features` 顯式設定且生效；其餘篩選（include/exclude/pattern）為 `none` 且 `feature_filter_applied=True`；驗證用例各一。

6. **[MAJOR|High]** Task 3.2 實作要點寫「include/exclude/pattern…」，API/TS 真實欄位為 **`include_features` / `exclude_features`**（`api/models/ic_models.py:8-15`、`types.ts:2136-2143`）；Task 3.1 亦未列完整欄位對照表。  
   **證據**：Task 3.2「依 include/exclude/pattern…」；API `FeatureFilterConfig.include_features`。  
   **會怎麼失敗**：agent 在 momentum schema 用錯欄位名，override merge 後篩選靜默失效。  
   **修法**：Task 3.1/3.2 貼 API 欄位 1:1 表（7 欄 + Optional）；`_apply_feature_filter` 偽碼用真實名稱。

7. **[MAJOR|Med]** §B 表 B3「無依賴可與 B1/B2 平行」，但 **B2 Task 2.3** 與 **B3 Task 3.1** 同改 `ic_config_schema.py`（:80 `by_volatility` vs 新增 `feature_filter`）。  
   **證據**：§B「B3…無（可與 B1/B2 平行）」；Task 2.3 / 3.1 皆改 `ic_config_schema.py`。  
   **會怎麼失敗**：平行派工 merge conflict；或後到者覆蓋前者改動。  
   **修法**：§B 改為 B3 依賴 B2 完成（同檔序列），或 B2/B3 合併為一批。

8. **[MAJOR|Med]** Task 4.3 驗證「`pytest` mock 慢 analyze」**未指定測試檔**；repo 已有 `tests/api/test_ic_analysis_service.py` 可擴充。  
   **證據**：Task 4.3 驗證僅抽象描述；無檔名。  
   **會怎麼失敗**：agent 新建重複測試或漏測 cross-sectional 路徑（:154-159）。  
   **修法**：寫死 `tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop`（longitudinal + cross_sectional 各一）。

9. **[MAJOR|Med]** Task 4.4 poll 狀態機（`[U-4]`）缺偽碼：retry 計數器存哪、poll interval、與 `connectProgress` 重入如何避免雙寫。  
   **證據**：Task 4.4「retry≤3 → 改 poll…直到 terminal」；無 ref/interval/清理 `reconnectTimerRef` 步驟。  
   **會怎麼失敗**：無限 poll、WS 重連與 poll 並行雙寫 status。  
   **修法**：補 5 行狀態機偽碼（`retryCountRef`、`pollIntervalMs=2000`、`terminal → clearInterval + close ws`）。

10. **[MINOR|Med]** Task 3.2 驗證「max_features=30 於 **45k**」無 fixture 來源或縮放策略；全檔 45k 僅來自 SPEC §A 敘述。  
    **證據**：Task 3.2 驗證 (ii)「45k → 30」；無 synthetic 45k 生成命令。  
    **會怎麼失敗**：agent 用 100 欄測試冒充 45k，漏穩定性/效能邊界。  
    **修法**：寫死 `tests/fixtures/ic_phase0/synthetic_45k_columns.parquet` 或 pytest factory `n=45000` 命名欄；sha256 只比欄名集合。

11. **[MINOR|Med]** Task 1.2 點名取代 `:535-549`，實際假綠測試為 `test_stage4_ic_calculation_with_kline_reader`（:524 起），`:541-548` 為 `grouped_analysis={...}` **dict** 非 pydantic（已讀 `test_ic_filter_orchestrator.py`）。  
    **證據**：TODO「:535-549」；檔案 :524-548。  
    **會怎麼失敗**：agent 只改行號區段、漏改 dict 為 `GroupedConfig` 的意圖。  
    **修法**：改為點名函式名 +「`grouped_analysis` 必須是 pydantic 模型或 `model_dump()` 後 dict，禁止裸 dict 繞過」。

12. **[MINOR|Low]** Task 4.4 引用 `useICAnalysis.ts:88-117`：onclose 無限重連實際為 **:110-118**；onerror 無條件 `setError('WebSocket 連線失敗')` 在 **:106-108**（與 U-2 衝突，TODO 未點名修 onerror）。  
    **證據**：TODO「:88-117」；檔案 :106-118。  
    **會怎麼失敗**：agent 只修 onclose，分析失敗仍顯示連線失敗。  
    **修法**：Task 4.4 實作要點加第 4 點：區分 transport error vs backend failed；onerror 僅在無 terminal status 時顯示泛用訊息。

13. **[MINOR|Low]** `[M-2]` manifest 要求「§A 六項已驗證事實」，TODO §0 僅一行標籤引用，**未摘錄六項**（冷啟動仍須回讀 SPEC §A）。  
    **證據**：§0「`[M-2]` fact-verified…」；manifest M-2 全文。  
    **會怎麼失敗**：執行端標稱不讀 SPEC 時對 §A 事實無感。  
    **修法**：§0 增 6 條一行摘要（或明寫「必讀 SPEC §A 六項」為硬依賴，與開頭「不需讀其他檔」矛盾則改開頭聲明）。

### reconcile R-1~R-12 對照（TODO 特有）

| ID | TODO 落實 | 問題 |
|---|---|---|
| R-1 DatetimeIndex + byte fixture | Task 2.1/2.2 ✓ | 無 |
| R-2 by_volatility False + raise | Task 2.3 ✓ | 無 |
| R-3 預設不截斷 + truncation_mode | Task 3.2/3.3 | **preview 判定未定義**（見 #5） |
| R-4 sorted 排序 | Task 3.2 ✓ | 無 |
| R-5 ICConfig 不丟棄 | Task 3.1 ✓ | 欄位名表不全（見 #6） |
| R-6 Golden 強化 | Phase Gate only | **無 Task**（見 #1） |
| R-7 TDD 兩 commit | 1.2/2.2/§0 ✓ | 流程性，無 CI 強制（可接受 MINOR） |
| R-8 cross-sectional to_thread | Task 4.3 ✓ | 測試檔未指定（見 #8） |
| R-9 poll 狀態機 | Task 4.4 | WS 欄位與偽碼不足（見 #4/#9） |
| R-10 §A 標籤 | §0 部分 | M-2 摘錄不足（見 #13） |
| R-11 preview_limit 幽靈 | Task 3.4 ✓ | grep 0 已複驗（僅 docs/handoffs 命中） |
| R-12 1e15 raise | Task 2.1 ✓ | 無 |

### §2 空殼獵殺

- Task 3.4 `[F-6]`：實質為 grep 確認，**非空殼**（manifest F-6 舊文案「改名」已在 TODO 澄清為幽靈）。
- Phase Gate `[M-5]` Golden：**實質空殼**——有指標無 Task、無 baseline 檔、無測試模組（見 #1）。

### 引用真實性抽查（TODO 宣稱 vs 實碼）

| 引用 | 結果 |
|---|---|
| `ic_filter_orchestrator.py:1139` `grouped_analysis` | ✓ 存在，傳 pydantic 物件 |
| `ic_config_schema.py:80` `by_volatility: True` | ✓ |
| `ic_engine.py:1018-1027` `_get_time_index` | ✓（現況 `unit="ms"` 寫死） |
| `ic_engine.py:944` decay warning | ✓（另有 :904/:918/:958 warning） |
| `ic_engine.py:383-400` grouped 分支 | ✓（無 by_volatility） |
| `icAnalysisStore.ts:187` `max_features: 30` | ✓ |
| `ic_analysis_service.py:154-159` cross-sectional | ✓ 同步呼叫 |
| `ic_analysis_service.py:209-216` longitudinal | ✓ 同步呼叫 |
| `useICAnalysis.ts:194-212` fetchTaskStatus | ✓（無 error 處理） |
| `test_ic_filter_orchestrator.py:535-549` | △ 函式 :524，關鍵 dict :541-548 |

## 被當成事實的未驗證假設

1. **event loop 阻塞**（SPEC §A#6 assumed）——TODO Task 4.3 未要求改前後 heartbeat 對照實測，僅 mock 建議。
2. **「grep 確認 `compute_grouped_ic` 僅此一 caller」**——本次 `grep` 與 SPEC 一致（orchestrator 生產路徑一處），但 TODO 未要求執行端再 grep 留證。
3. **「Claude 親驗 preview_limit 全 0」**——本次 `grep preview_limit` 在 `api/` `momentum/` `frontend/src` **0 行**（僅 docs/handoffs），可採信。
4. **「現況 `load_ic_config` / `ICConfig.model_validate` 丟棄 feature_filter」**——路徑為 orchestrator `_apply_config_override` → `ICConfig.model_validate`（`ic_filter_orchestrator.py:1717`）；`ICConfig` 頂層確無 `feature_filter` 欄（`ic_config_schema.py:319+`），與 TODO 敘述一致，屬 code-verified。

---

ASSUMPTIONS_VERIFIED: 上述引用行號與欄位名逐檔比對；preview_limit 三目錄 grep 0；decay 熱迴圈 warning 四處；WS failed payload 用 message 非 error  
TESTS_RUN: none（文件審查）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  

HANDOFF_NOT_UPDATED: 審查任務不覆寫根 HANDOFF.md（執行合約 §7）

STATUS: DONE
