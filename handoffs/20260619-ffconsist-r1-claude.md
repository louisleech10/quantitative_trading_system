# FF 一致性整併 R1 — Claude(ops) 獨立版

立場核心：**「可觀察行為」應一致;「執行模型」分歧是有理由的,不該為一致而一致。**

## #1 log 一致 — 做
- 做法:batch worker(`_compute_single`)設 file handler,把 momentum.* log 寫進 case_search 檔(或 per-task FF log)。子進程繼承不到父 handler,須在 worker 內 setup。
- 風險:多 worker 同寫一檔交錯(現 concurrent=1 無此問題;未來並行需 per-worker 檔或 O_APPEND 行級)。
- 優:單/多 log 一致,可診斷。缺:子進程 logging setup 些微複雜。優先序 P1。

## Q3 進度一致 — 做
- 做法:單 symbol 的 `_report_progress` 也捕 RSS(psutil)餵 current_rss_mb(WS 欄已存);batch 補單 symbol 那種 sub-step 細節(rolling 10/100)。統一同一 progress event schema 兩路徑共用。
- 風險:單 symbol heartbeat 與 batch tick 兩套機制需對齊欄位語義。
- 優:進度顯示一致(layer+sub-step+RSS)。缺:要碰兩個進度發送點。優先序 P1。

## Q5 terminal — 做
- 做法:`api/main.py:401 access_log=False`(我們 middleware 已有過濾後請求 log 進檔,不漏)。或保留但路由經我們 filter。
- 風險:極低(uvicorn access 本就冗餘於我們 middleware)。優:terminal 乾淨。優先序 P0(最小最安全)。

## Q2 工作流 — 做(使用者已定:批次加保留對話)
- 做法:批次完成後也彈 RunRetentionDialog(per-symbol 或整批一次);需 batch 也支援 ephemeral→keep/discard 語義(現自動持久化→改為先 staging,使用者決定保留)。
- 風險:batch 多 symbol 的保留粒度(逐 symbol vs 整批)、與既有自動持久化/resume 的相容。
- 優:工作流一致。缺:batch 持久化流程要加 staging/decision 層,非小改。優先序 P2(最大改動)。

## E 執行模型 — **維持現狀(thread 單 / subprocess 多),只統一觀察層**
- **裁決:不整併執行模型。** 分歧有理由:
  - 多 symbol 用 subprocess = **crash/OOM 隔離**(一 symbol 爆不拖垮整批)+ TA-Lib C globals/Numba spawn 安全 + per-symbol 記憶體乾淨釋放。這是它存在的核心理由。
  - 單 symbol 用 thread = 簡單、websocket heartbeat 即時、無 IPC/子進程開銷、preview 語義自然。
- **整併的下場**:
  - 單→subprocess:失去 in-process log/heartbeat 簡潔,加 IPC+開銷換取單一 run 的隔離(用不到)。弊>利。
  - 多→thread:**失去 crash 隔離(一 symbol OOM 殺全批)+ TA-Lib fork 問題**。高風險,正是 subprocess 要解的。
  - 抽共用執行層:理論優雅但大重構,風險高、回報低(觀察層統一已達一致目的)。
- **結論**:執行模型分歧合理,**風險過大、無實質優點→維持現狀**;一致性靠 #1/Q3/Q5/Q2 在觀察層達成即可。優先序:不做(維持)。

## 總優先序
P0 Q5(最小) → P1 #1 + Q3(觀察層一致) → P2 Q2(工作流,較大) → E 維持現狀不做。
