# FF 一致性整併 R2 交叉詰問 brief

## R1 已收斂結論（R2 基礎,挑戰但別重推導）
- **E**:不整併 executor(單 thread/多 subprocess 各有 OOM隔離/低延遲理由)；統一觀察契約防漂移。
- 順序:**Q5(P0 access_log env 開關非全關)→#1(P0 worker non-rotating FileHandler 進檔)→Q3(P1 共用 progress schema+單補RSS,concurrent>1 coarse)→Q2(P2 批次 retention,使用者已定做)→E contract tests 隨項。**

## R2 必須釘死的開放點（交叉詰問焦點）
1. **E 本輪範圍歧義**:本輪 mandatory 是「僅共用 payload schema + 雙路徑 parity tests + error-class 統一」,還是要連「薄 Sink 封裝(ProgressSink/LogSink/RetentionSink)」一起?GenerationRunner adapter 是否一律延後?**給明確邊界。**
2. **Q3 RSS 雙語意**:單路徑 RSS=同進程含 API 噪音、batch=子進程該 symbol。**分欄(`process_rss_mb` vs `worker_rss_mb`) 還是同欄+註解?** 哪個前端較不誤導?rolling 10/100 sub-step 現靠 message 欄,夠不夠?
3. **Q2 細節**:① retention 對話**是否阻塞下一 symbol/wave**(非阻塞=與單一致但暫占磁碟)?② **整批一次 dialog vs per-item queue**(複用單的 completionQueue)?③ MVP 分期:Phase A(prompt+延後register+per-item keep/discard+checkpoint retention_pending/decided) vs Phase B(後端交易式 bulk-delete endpoint)?④ 部分失敗(register/delete)如何回滾/標記?⑤ staging 切點實測 `_record_item_result`/`batch_service:583`。
4. **#1 原子性**:多進程同檔 append 是否需壓測證明行原子性,還是 concurrent=1 下 non-rotating FileHandler 已足、多進程留待並行時?worker log 路徑機制(`FFACT_API_LOG_PATH` 沿用當日檔)。
5. **優先序**:#1 與 Q5 真該並列 P0,還是 Q5 先(最小)?Q2 MVP(prompt+延後 register)可否提前到 Q3 後?

## 流程
R2 三方(Claude/Codex/Composer)各**獨立交叉詰問**上述(挑戰 R1 結論、針對 5 開放點給定案)→ 互審 → Claude 統整 → 統整受審。**E 與優先序大方向已三方+雙審一致,R2 聚焦把 5 點釘死、找剩餘漏洞**;若有人有翻案 E 的新證據也提。
格式 ≤50 行,逐點(1-5)給定案+理由。
