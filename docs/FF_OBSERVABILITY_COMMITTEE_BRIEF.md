# FF 觀測性 / 並行 — 委員會交叉詰問 brief

> 角色:獨立架構審查者。**挑戰 Claude 的設計、不附和**。每個提案找反例/風險/更簡解。
> 證據來自真實 run:logs/case_search_api_20260619.log(2 symbol×1h,~2h05m,0 error,437K 特徵/symbol)。

## 背景(實測根因)
- 批次經 `feature_factory_batch_service._run_batch` → **ProcessPoolExecutor 子進程**(:442) 跑各 symbol。
- per-layer 指標 log(`feature_factory.py:541/710` `%s done: rss=%dMB`、`[L6.5] Serial start rss=`)在**worker 子進程**,不進 api log、不回父進程。
- request log 雙記:`api/core/middleware.py`(middleware.request Started/Completed) + `api/core/logging.py`(api.request)。實測 17541/17788 行(98.6%)是 access log。
- `_resolve_concurrent_symbols` 無條件=1(B2.2b,移 ic_first flag 後 OOM 護欄改恆 serial) → 多 symbol 全序列(2 symbol=2h,N symbol 線性 N×)。

---

## T1 (#3) — Log 噪音/verbosity
**Claude 提案**:
1. **消雙記**:middleware.request 與 api.request 記同一請求 → 留一套(建議留 middleware,刪 api.request 那層)。
2. **預設安靜**:高頻輪詢成功 GET(batch/browse status 200)不記 access,或 access 降 DEBUG;非 200/慢請求(>Nms)才 INFO。
3. **開關**:logging.py 已有 log_level → 加 env `API_ACCESS_LOG=quiet|verbose`(預設 quiet)。
- **待詰問**:① 降 DEBUG vs path-filter vs 取樣,哪個預設最好且不漏掉除錯需要的資訊?② 留 middleware 還是 api.request 哪套(看哪套含 request-id/timing)?③ 會不會藏掉真正該看的錯誤請求?

## T2 (#2 + F1) — 批次 layer/step 進度 + per-layer 觀測性
**問題**:單 symbol 有 layer/step(websocket heartbeat);批次只 symbol 級(running/pending)。F1:per-layer 時間/RSS/檔案大小不在任何 persisted log(跑 2h 無法事後診斷)。同根因=子進程 log 不回父。
**Claude 提案**:
- worker 子進程經 **progress callback / mp.Queue** 把 `{symbol, current_layer, step, rss_mb, elapsed}` 回傳父 → `_notify_progress` 併入 batch status → 前端 running symbol 下顯示當前 layer/step + rss。
- 同一通道把 per-layer 指標寫進**結構化 FF run 報告**(如 `logs/ff_run_{task}.jsonl`)補 F1。
- **待詰問**:① ProcessPool 下 callback/Queue 的可靠性與開銷(高頻 heartbeat 跨進程)?② 是否該改用 worker 各自寫 log 檔(簡單)而非 IPC 回傳?③ 進度粒度多細才有用又不洗版?④ 與現有 single-symbol websocket 機制如何統一不重造?

## T3 (F3) — 多 symbol 並行(序列=1 該不該找回並行)
**問題**:B2.2b 無條件 concurrent=1 → 多 symbol 線性慢。原本 legacy 可 tier-based 並行,IC-First 因高記憶體強制 1;現全 IC-First→全序列。
**Claude 提案(待詰問,傾向保守)**:
- 選項 A:維持=1(OOM 安全,現狀),接受線性。
- 選項 B:**tier-aware 並行 + 真實 RAM 預檢 gate**——動工前估「per-symbol 峰值 RSS × 並行度 vs 可用 RAM」,夠才並行、不夠自動降為序列。IC-First 437K 特徵記憶體重,小 tier(8/16GB)仍應=1,大 tier(24/32GB)才放 2。
- **待詰問**:① per-symbol 峰值 RSS 怎麼可靠估(本 run 沒記!需先有 F1/T2 的 RSS 數據)?② IC-First 真實峰值多少(437K 特徵)→ 大 tier 放 2 會不會仍 OOM?③ 並行省的時間 vs OOM/resume 複雜度,值得嗎(Opt Priority #2 多symbol穩定 > #4 runtime)?④ 是否「先把 F1 觀測性做好量到真實峰值,再決定並行」才是正確順序?

---

## 請各委員輸出(獨立,不互看)
對 T1/T2/T3 各給:① 同意/反對 Claude 提案 + 理由 ② 更簡或更穩的替代 ③ 最大風險 ④ 建議優先序(哪個先做/哪個可緩)。
特別回答 T3 ④:是否「先觀測(F1/T2)再談並行(T3)」。寫 handoffs/20260619-ff-obs-{你的代號}.md(≤60行)。
