# Handoff
**Agent**: Claude | **Time**: 2026-06-15 | **Branch**: main

## 結案:第 2 批 Run 生命週期 UX(大型,已 push 至 1d453c4)
- 功能:未命名 run 自動清理(per symbol+tf 各留 5)、跑完彈窗保留/命名/丟棄、命名永不自動清、刪除=features+對應 cgsa_work(絕不碰 kline_cache/feature_klines/d* cache)。
- 核心:`run_paths.py`(canonical resolver)/`run_locks.py`(**fcntl.flock** per-run lease:kernel 互斥+進程死亡自動釋放)/`run_lifecycle.py`(安全刪除 lstat 逐層拒 symlink+白名單雙根+cgsa ownership manifest 核對)/registry transaction(merge-preserve alias+corrupt fail-closed+deleting 標記)/runs API(409/404/422/500 寫死)/前端 RunRetentionDialog+RunManagerPanel。
- 管線:V1→V5 **六輪 adversarial**(鎖機制 lockdir→rename→mutex 均被 Codex 證明有 race,最終 flock 終局,r5 實測 SIGKILL 0.0013s 自動釋放)→Codex 實作→Composer code review(REQUEST_CHANGES 5 MAJOR→Codex 修→r2 2 PARTIAL→Claude 補測試+文件澄清→r3 **APPROVE**)。
- 驗收:lifecycle 29 passed(含跨進程 flock/kill-9/競態 barrier/HTTP 四碼/resume 三分支)+vitest 5+回歸 bundle 78+build+解耦 0+postflight ✅。
- 文件:docs/BATCH2_RUN_LIFECYCLE_{SPEC,TODO,MANIFEST,DECISION}.md(V5);交接 handoffs/20260613-batch2-*。
- 已知技債(下輪順手):`_write_run_size` 用 registry 私有 API(行為正確,維護耦合);symlink parent-swap TOCTOU(威脅模型外接受);batch _tasks 面板可見性不隨刪除即時更新(resume 正確性已保證)。

## 結案:第 1 批 follow-up 小修包(7 commits,已 push)
- N4/N6(all-NaN=total_nan)/N3 winsor/N7 canonicalizer/T5 present_timeframes。三輪雙家族 adversarial→Codex 實作→Composer APPROVE。新測試 20+回歸 78。
- 文件 docs/BATCH1_FOLLOWUP_*。

## 待使用者 / 下一步 backlog(順序已拍板)
- **第 3 批:既有測試紅 triage**(~44 紅,先分類半天再決定修哪些)。
- **d* cache/fracdiff 選 A 修復對齊**(大型,使用者已決;見 docs/DSTAR_FRACDIFF_NONCGSA_FINDING.md;命中 a/b/d 走完整大型管線)。
- 16/24/32GB tier ADF/d* 並行度 profile(以 CGSA 主路徑為準,因 d* 在非 CGSA 前提已變)。
- templates/optimization_report.html 還原案(前輪遺留,仍待答)。
- 第 1 批 MINOR:真 kline 測試 glob→rglob;SPEC :185 錨點勘誤。

## 鐵律教訓(累積)
- 鎖/併發設計勿自製 stale/接管協定(三版均有 successor-race)→優先 kernel 原語(flock);adversarial 連續多輪聚焦同一點時,換機制比補協定快。
- codex sandbox 無 .git 寫權限→執行端只寫檔,commit 由 Claude 按 Phase 接手(已多次實證)。
- tests/conftest.py 在 `--collect-only` 會重寫 tests/golden/l65/test_inventory.txt——跑 --co 後必查 git status 還原。
- commit 後直接 push;派工進度 10 分鐘節奏(均已入 memory)。
