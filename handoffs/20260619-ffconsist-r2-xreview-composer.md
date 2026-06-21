# FF 一致性 R2 互審 — Composer 2.5

審閱對象：Claude R2、Codex R2（未審己稿）。

## E 本輪 mandatory（核心裁決）
**改立場：採 Codex 薄 normalize/emit 函式 mandatory，否則 schema+parity 易成「雙邊手組、測試另寫」假鎖。** mandatory = `FeatureProgressEvent`/`FeatureRetentionEvent` + error-class enum + **單一 `normalize_progress_event()`（及 retention 對應薄函式）** + 雙路徑 parity tests；**拒** ProgressSink/LogSink 類與 runner adapter（同意 Claude「Sink 封裝選做/延後」）。
- **同意 Codex**：normalize 是 contract 執行點，成本低、防複製轉換邏輯漂移。
- **反對 Codex P0c 單列**：E minimal 應 **隨 #1/Q3 首次改 payload 時同 PR 落地**，不另開軌道。
- **反對 Claude「Sink 選做」**：僅型別+測試（我 R2 原立場）不夠；但 **不同意** 任何 lifecycle 抽象。

## Q2 磁碟背壓
**同意 Codex，反對 Claude/我 R2 遺漏。** T-C 只防 run 內 L3 爆盤；延後 retention 會累積 pending bytes。**Q2-A 必加** soft 閾值（env 可調）→ 暫停新 wave + UI 提示，與非阻塞續跑並存。

## Q3 RSS 命名
**同意 Claude/我：互斥 `process_rss_mb` / `worker_rss_mb`。** **部分反對 Codex** `api_process_rss_mb`（冗長）；但 **同意** deprecate `current_rss_mb`。rolling sub-step 留 `message`；加 `schema_version`（我 R2）。

## #1 smoke
**同意 Codex+我，反對 Claude「僅 TODO」。** P0 完成門檻 = non-rotating handler + **父+1 子各寫短行、assert 無破行/缺行**（2–4 worker 更佳）；concurrent>1 全壓測留 T-A。

## 優先序與遺漏
**同意 Q5→#1(含 smoke)→Q3→Q2-A→Q2-B**；parity **隨各項**，驗收 **5 條**（含 batch item **無 `browse_task_id` 直至 retention decided**——我 R2 補充，Claude 4 條漏此）。Claude 另漏：Q2 背壓、#1 smoke。Codex staging 切點（register 前移）**同意**，優於「待實測」。

## 總表
| 議題 | Claude | Codex |
|------|--------|-------|
| E thin normalize | 反對(選做) | 同意 |
| Q2 背壓 | 反對(未提) | 同意 |
| RSS 欄名 | 同意 | 部分同意 |
| #1 smoke | 反對 | 同意 |
| 優先序 | 同意 | 部分同意(P0c) |
