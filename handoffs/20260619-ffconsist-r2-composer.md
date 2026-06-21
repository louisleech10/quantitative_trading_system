# FF 一致性 R2 — Composer 2.5 交叉詰問（獨立）

佐證：`batch_service.py:581-583` 成功即 `browse_registrar.register`；`:44-46` 預設 concurrent=1；`feature_factory_service.py:227` thread；`RunRetentionDialog.tsx:18` 取 `completionQueue[0]`。

## R1 挑戰（不翻案 E）
- **E 維持**：ProcessPool OOM 隔離 vs thread lease/callback 分工仍成立；無新證據改 executor。
- **挑 R1「必抽 Sink 類」**：本輪 mandatory 應是 **schema + error enum + parity tests**；Sink 僅 **Protocol/TypedDict 定義**（同檔 ~30 行），**不做** ProgressSink/LogSink 實作類與 runner 重構。GenerationRunner adapter 延後。
- **挑「staging 待實測」**：靜態已證 mid-run register；切點=刪 581-586 register，改寫 `staging_path`+`retention_pending`。

## 1. E 本輪範圍
**定案**：mandatory = 共用 `FeatureProgressEvent` + `BatchFailureType` 對齊 error-class + 雙路徑 parity tests（4 條驗收門檻同 Claude）。Sink **僅 Protocol 型別**，實作類與 adapter **延後**。

## 2. Q3 RSS
**定案**：**互斥 optional 欄**——單路徑送 `process_rss_mb`，batch 送 `worker_rss_mb`，同 event 不同時填。比雙欄常 null 或同欄+註解更不誤導。rolling 10/100 留 `message`；加 `schema_version` 供前端演進。

## 3. Q2
- ① **非阻塞** batch 續跑（與單路徑一致，暫占磁碟可接受）。
- ② **後端 per-item 入 completionQueue**（含 `batch_id`）；**前端呈現=整批可展開面板**，非 N 次強制 modal（對齊 R1「整批一次+逐項」；現 Dialog 只取 queue[0] 需擴）。
- ③ Phase A=prompt+延後 register+keep/discard+checkpoint `retention_pending/decided/error`；Phase B=交易式 bulk-delete。
- ④ 部分失敗逐 item 標 `retention_error`，可重試，checkpoint 為 SSOT。
- ⑤ staging 切點已確認：`_record_item_result` 成功分支移除即時 register。

## 4. #1 原子性
**定案**：現網 concurrent=1 → non-rotating FileHandler 指 `FFACT_API_LOG_PATH` **可先落地**；但需 **輕量 smoke**（父+1 子各寫 10 行、目視無截斷）才標 P0 完成，非僅 TODO。concurrent>1 行原子性壓測留 T-A。

## 5. 優先序
**Q5(P0)→#1(P0，含 smoke)→Q3(P1)→Q2-A(P2)→Q2-B(P2.5)**；parity tests **隨各項**落地，必含 **register 延後** 路徑否則 Q2 再漂移。Q2-A 可在 Q3 後即做（不依賴 RSS schema，但 UX 上 Q3 先較穩）。

## 翻案 E
無。補充：contract test 最小集須加第 5 條——batch 完成 item **無 browse_task_id 直至 retention decided**。
