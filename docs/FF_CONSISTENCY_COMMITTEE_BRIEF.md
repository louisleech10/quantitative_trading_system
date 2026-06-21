# 單/多 symbol FF 一致性整併 — 委員會 brief（兩輪）

## 問題
單 symbol 與多 symbol(批次) FF 路徑分岔,造成 log/進度/持久化/terminal 不一致。使用者要求整併**可觀察行為**到一致,並評估**執行模型**是否該整併。

## 已實測事實（grep/log,附位置）
- **執行模型**：單=`run_in_executor` thread 同進程(feature_factory_service.py:227);多=ProcessPoolExecutor 子進程(feature_factory_batch_service.py:442,`_compute_single`)。
- **log**：單 thread→momentum.* 進 case_search 檔(實測 23:14-23:22 有 366 feature_preprocessor 行);多子進程→log 留子進程不進檔(23:31-23:36 幾乎只 api.* )。
- **進度**：單=`_report_progress` heartbeat(細節「Starting Layer 3…」rolling 10/100)但**無 RSS**;多=T2 layer_metrics.jsonl(layer+RSS)。WS mapper(feature_factory_ws.py:132-134)已有 current_stage/stage_progress/current_rss_mb 欄。
- **持久化**：單=preview→`RunRetentionDialog.tsx` 保留/命名/丟棄;多=自動持久化。
- **terminal**：uvicorn 內建 access_log=True(api/main.py:401)印 stdout,不進檔(T1 只清我們 middleware)。

## 範圍（5 項 + 1 決策）
- **#1 log 一致**:batch worker 子進程 log 路由進檔。
- **Q3 進度一致**:統一 progress payload(layer + sub-step 細節 + RSS)兩路徑都有。
- **Q5 terminal**:uvicorn access_log 關閉/過濾。
- **Q2 工作流**:**使用者已定→批次也加保留/丟棄對話**(與單一致)。
- **E 執行模型**:thread(單) vs subprocess(多) **該整併還是維持現狀?** 必須評估:整併方向(單也subprocess / 多也thread / 抽共用層)、風險、優缺點。**風險過大或無優點→明確建議維持現狀**(觀察行為一致即可,執行可不同)。

## 兩輪流程（嚴格）
**每輪**:三方(Claude/ops、Codex GPT-5.5、Composer 2.5)**各自獨立產出**自己的整併方案 → **其餘兩家各審查**(cross-review) → **Claude 統整** → **Claude 的統整再交另兩家審查**。
- **第 1 輪**:各自對「#1/Q3/Q5/Q2 怎麼做 + E 整併或維持現狀」獨立提案。
- **第 2 輪**:基於第 1 輪 Claude 統整結論,**交叉詰問**(挑戰共識、找漏洞、翻案 E 的決定),再走一次三方獨產→互審→統整→審查。

## 每份產出格式（≤70 行）
逐項(#1/Q3/Q5/Q2/E)給:① 做法/裁決 ② 風險 ③ 優缺點 ④ 優先序。E 特別答「整併 vs 維持現狀」並給理由。**獨立思考,不附和他家。**
