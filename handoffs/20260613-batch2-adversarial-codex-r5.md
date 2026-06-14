# Batch2 Run Lifecycle Adversarial Review — Codex R5

## Scope
- 僅復核 R4 N1 與 V5 `flock` 終局方案；未核 N3/N4 或其他 Task。

## Verdict
- **核心機制：RESOLVED。** 本機檔案系統上的 `fcntl.flock(LOCK_EX|LOCK_NB)` 將互斥交給 kernel；持鎖進程死亡後 open file description 關閉，鎖自動釋放，因此不存在需由使用者空間判定/接管的 stale owner。
- **永不 unlink：正確且必要。** 所有競爭者持續 open 同一 inode；不 unlink 可避免舊 inode 持鎖時，新競爭者經同一路徑建立/鎖住另一 inode 的雙持鎖競態。
- **macOS 同進程語義：已實測閉合。** macOS 26.3 上同一路徑兩次獨立 `os.open`，第一個 fd 持 `LOCK_EX` 時，第二個 fd 的 `LOCK_EX|LOCK_NB` 回 `EWOULDBLOCK`（errno 35），不會因同 PID 而繞過互斥。
- **跨執行緒移交：合法且已實測。** fd/open file description 不綁定取得鎖的 Python thread；另一 thread 可 `LOCK_UN` + close，之後獨立 fd 可立即重新取得鎖。
- **進程死亡：已實測閉合。** subprocess 持鎖時父進程 try-flock 被阻擋；`SIGKILL` 後 0.001314 秒父進程成功取得鎖，符合 V5 的 ≤1 秒契約。

## Blocking Finding
- **N1 的文件契約尚未閉合，不能派工。** TODO 雖有 V5 Task 0.2，但同一活躍文件仍在第 7 行要求「lease 接管只准 rename 禁 unlink」，與第 47/50 行「無接管、禁 mkdir/O_EXCL、lock 檔永不 unlink」直接矛盾；實作者遵守任一邊都會違反另一邊。
- 驗收語義亦未同步：TODO 第 89 行及 SPEC 第 68 行仍要求 `lockdir owner token` 不變，SPEC 第 73 行仍把 `active` 描述為「lockdir 存在」。V5 lock 檔永存，檔案存在/token 不能代表活性；唯一有效 oracle 是 try-flock。
- SPEC 第 99 行仍保留 `stale age 門檻`，第 108 行仍保留 `pid 重用/token+age` 的舊鎖限制。這些雖不改變 Task 0.2 的正確性，但會讓驗收重新引入已廢除的 stale 協定。
- 閉合條件：刪除上述舊協定規範，將 warmup 連續持鎖斷言與 `RunInfo.active` 全部明定為 try-flock 結果；文件只保留本機磁碟/NFS 須重評限制。

ASSUMPTIONS_VERIFIED: macOS 本機磁碟；同進程獨立 open 互斥；跨 thread release；SIGKILL 自動釋放；SPEC/TODO V5 與殘留舊協定逐行比對
TESTS_RUN: 臨時 /tmp Python flock 實驗：同進程雙 fd PASS；跨 thread release/reacquire PASS；subprocess alive 阻擋 + SIGKILL 後 0.001314s reacquire PASS
FAILURES_SEEN: 文件內 V5 與 V3/V4 lockdir/rename/stale/token 驗收規範互相矛盾
SCOPE_CHANGES: none；僅新增本報告
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: FAIL — flock 方案本身閉合，但活躍 SPEC/TODO 殘留舊接管與 lockdir/token 活性規範，尚不可無歧義派工
