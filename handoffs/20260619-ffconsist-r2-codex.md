# FF 一致性 R2 — Codex 交叉詰問

讀取: `HANDOFF.md`、`CLAUDE.md`、`docs/FF_CONSISTENCY_R2_BRIEF.md`、R1 consolidated、Claude R2；另查 `_record_item_result`、layer metrics、progress callback、前端 types/store。

## 對 R1 的挑戰
E「不整併 executor」仍成立；但 R1 把 Sink 說成抽象手段偏弱。現況單路徑只回 `stage/progress/message`，batch 另寫 jsonl+task 欄位；若只定 schema+test、不讓兩路徑經同一個薄 emitter/sink，之後仍會複製轉換邏輯而漂移。

## 1. E 本輪範圍
定案: mandatory = shared `FeatureProgressEvent`/`FeatureRetentionEvent` schema + error class enum + 雙路徑 parity tests + **極薄 Sink/Emitter 函式**；GenerationRunner/ThreadRunner/ProcessRunner adapter 延後。
理由: Sink 不應做 lifecycle/runner 抽象，只負責「normalize/enrich/emit」，成本小但可把 contract test 打在同入口；否則 schema 只是文件，兩邊仍各自手組 payload。
最小驗收: 單路徑 callback 與 batch layer jsonl 經同 normalize 後欄位/version/error-class 相同；concurrent>1 不產生假 current_stage。

## 2. Q3 RSS 與 sub-step
定案: 分欄，不同欄名: `api_process_rss_mb`(單路徑/API 同進程) 與 `worker_process_rss_mb`(batch 子進程該 symbol)；不要同欄+註解。
理由: 前端/下游排序或 chart 會忽略註解，同欄必然誘導跨語意比較；現 `current_rss_mb` 名稱已太泛，應 deprecate 或只作 legacy display。
rolling 10/100 sub-step: MVP 留在 `message`；若要結構化，只加可選 `substage`/`substep`，不讓 batch concurrent>1 假裝有單一 active substep。

## 3. Q2 retention
定案: 計算不阻塞下一 symbol/wave；但「磁碟釋放」要有背壓: pending retained bytes 超過預設閾值時暫停新 wave/提示處理，避免 T-C 預檢後仍被 pending 輸出塞滿。
粒度: per-item queue 複用 `completionQueue`，UI 可彙總顯示批次清單；不做 N 個強制 modal，也不做只能整批同決策。
MVP Phase A: 延後 browse register 到使用者 keep/alias；checkpoint 加 `retention_pending/retention_decided/retention_error`；每 item keep/discard；resume 後重建 pending queue。
Phase B: 後端交易式 bulk decision/delete endpoint，含 checkpoint/RunManager/quality summary/磁碟輸出同步更新。
部分失敗: register/delete 失敗不得把 item 當 completed retention；標 `retention_error`、保留 output_paths、可重試。若 discard 刪檔成功但 checkpoint 寫失敗，下次以 tombstone/缺檔校正，不能復活為可 browse run。
staging 切點: 證據顯示 `_record_item_result` 目前成功後立即 `_browse_registrar.register(...)`；切點應在 hdf5_path/output_paths 落 checkpoint 後、browse register 前。

## 4. #1 append 原子性
定案: 本輪 concurrent_symbols=1 時 non-rotating `FileHandler` 指當日 log 足夠落地；但必須加小型多 worker append smoke/contract test 或至少機制測試，不能只靠 OS 直覺。
理由: `api/core/logging.py` 現用 `TimedRotatingFileHandler`；worker 若沿用 root handler 會有跨進程 rotate 風險。`FFACT_API_LOG_PATH` 應只傳「當日穩定檔名」，worker 掛 non-rotating handler 並加 pid/symbol/timeframe。
壓測強度: 不必完整 T-A 並行壓測；做 2-4 subprocess 各寫短 JSON/line，驗證無破行/缺行，作為未來 concurrent>1 前置 guard。

## 5. 優先序
定案: Q5(P0a) → #1(P0b) → E progress/error minimal sink+parity(P0c,隨 #1/Q3) → Q3(P1) → Q2 Phase A(P2) → Q2 Phase B(P2.5)。
理由: Q5 最小且立即降噪；#1 修「看不到 batch worker log」是 debug 基礎；E minimal 需早插入，否則 Q3/Q2 又各自補一套；Q2-A 可在 Q3 後提前，不必等 bulk endpoint。

## 翻案 E 新證據
無證據支持整併 executor；反而現有 `_compute_single` 子進程重建 factory、環境傳 layer metrics path、batch RSS soft-limit/wave 降級，都證明 process runner 有獨立價值。翻案只到「薄 Sink mandatory」，不是整併 runner。

## 風險提醒
Q2 若完全非阻塞且無 pending bytes 背壓，會把「保留決策延後」變成新的磁碟爆點；R1 未充分處理這點。
