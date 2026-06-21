# FF 一致性 R2 互審 — Codex 審 Claude/Composer

範圍:審 `r2-claude` 與 `r2-composer`,不自審;另核 R2 brief 與現碼證據:`_record_item_result` 581-583 成功即 register、batch RSS 映成 `current_rss_mb`、retention dialog 只取 `completionQueue[0]`、logging 仍 TimedRotatingFileHandler。

## 1. E 本輪 mandatory
**裁決:同意 Codex 方向、反對 Claude/Composer 的「只 schema/types + tests」。**
mandatory 應是:共用 `FeatureProgressEvent`/retention event/error enum + parity tests + **極薄 normalize/emitter 函式**;GenerationRunner/ThreadRunner/ProcessRunner adapter 延後。
理由:TypedDict/Protocol 只定目標形狀,兩路徑仍會各自手組 payload;parity tests 只能事後抓漂移,不能消除雙入口。薄 normalize/emitter 把 contract test 釘在同入口,防漂移才夠。
邊界:不同意做厚 `ProgressSink/LogSink/RetentionSink` 類或 lifecycle 抽象;薄函式只 normalize/enrich/emit。

## 2. Claude R2
同意:不整併 executor;RSS 必須分欄;rolling 10/100 留 message;Q2 per-item queue + Phase A/B;Q5→#1 先。
反對:E 把薄 emitter 降選做,防漂移不足。
反對:Q2 完全非阻塞且「暫占磁碟可接受」漏掉 pending retained bytes 背壓;T-C 預檢只能防生成前容量,不能防使用者遲決策累積把盤塞滿。
反對:#1 只留 TODO/註解不夠;本輪至少要有輕量 append smoke 才能標 P0 完成。
反對:優先序把 E 隱入各項,容易讓 Q3/Q2 各自再造 payload;E minimal 應列 P0c 或每項開工前共用入口先落。

## 3. Composer R2
同意:不做 runner adapter;Q2 切點已可由現碼確認為 register 前;per-item queue+批次可展開面板;#1 需 smoke;Q2-A/Q2-B 分期合理。
反對:Sink 僅 Protocol/TypedDict 不足,同 E 裁決。
反對:Q2 「暫占磁碟可接受」缺背壓;至少要 checkpoint pending bytes/outputs,超門檻暫停新 wave 或要求先決策(門檻可先 config,不要硬編數字)。

## 4. 具體裁決
RSS 命名:採互斥 optional 分欄,建議 `api_process_rss_mb`(單路徑/API 同進程含噪音) 與 `worker_process_rss_mb`(batch 子進程);避免泛名 `process_rss_mb` 被誤解可跨路徑比較。`current_rss_mb` 只作 legacy display/過渡。
#1 smoke:同意 Composer/Codex,父+1~4 子進程寫穩定當日 non-rotating file,驗無破行/缺行;concurrent>1 壓測留 T-A。
Q2 背壓:同意 Codex,非阻塞下一 item/wave 不是無上限;pending retained output bytes 超門檻要停新 wave/提示處理,並可 resume。
優先序:Q5(P0a)→#1+smoke(P0b)→E minimal emitter+parity(P0c)→Q3(P1)→Q2-A(P2,含背壓)→Q2-B(P2.5)。

STATUS: DONE
