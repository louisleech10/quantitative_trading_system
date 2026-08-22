# HANDOFF

**當前**：`/search` 三 bug 修復（out-of-epic；UAT B1 阻塞）R2 閉合輪派工中。
GAP-3 B1–B5 全數蓋章完工，**只差使用者 UAT B 段 13 項簽字**（未簽不結案）。

## 進行中：/search 修復
使用者 UAT B1 實測抓到三個既有 bug（非 GAP-3 引入）：無窮迴圈＋資料重複、事件迴圈鎖死、worker 日誌不落檔。
- `6e7275da` R0 三修 → R1 三家審查抓 **2×P0**（我的修補對使用者實際輸入無效；新測試假綠）
- `c7ea4ebe` R1 六條全修：serial fallback 改 `asyncio.to_thread`（兩處）／測試整檔行為級重寫 9 條／
  `IncompleteDownloadError` fail-closed＋逐頁遞增驗證＋空窗只跳已證實範圍／worker handler 改掛 root／
  executor `try/finally`＋`await to_thread(shutdown)`／log path 優先 `MomentumConfig`
- `bfed7726` R1 審計鏈＋synth 群集處置（8 findings→6 群集）＋債銷帳（`--has-open` rc=0）
- **R2 已派**（session `20260822-searchfix-x-review-r2`，三家全員）→ 收齊後 reconcile→修補→stamp

驗證：`tests/momentum/DataExtraction/` 8 passed 1 skipped、legacy 2、event_samples 230、decoupling rc=0；
實跑 ETHUSDT 12h 2024-01-01→2026-04-27 = 1695 根唯一遞增間隔全 12h；mutation 七條各自還原皆紅。
receipt `handoffs/run_receipts/20260822T100000Z-searchfix-r1-fix-gate.log`。

**待告知使用者**：R0 後我說「重啟重跑即可」對 4 symbols 不成立（走 serial fallback），現已修好可重跑。

## 坑（本輪新增）
- **commit 前必跑** `bash scripts/plain_docs_sync_check.sh --staged`（`git add` 之後、commit 之前）
- brief 的 `fact-verified` **只准貼實跑 rc**，禁推理（摩擦八十七）；測試計數一律從 receipt `grep` 複製（八十八）
- 回歸測試須斷言**中間值／真實行為**，禁 `inspect.getsource` 字串守衛當主要防線；
  寫完必跑 mutation sweep 確認每條都會紅——本輪首版重寫仍有兩條不紅
- `completeness_check.sh` 正式入口＝`--lock <sources.lock>` **單獨使用**，不得再帶 synth 路徑
- 委員 session 命名須 `<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`，task-id＝其大寫

## 接下來
1. 收 R2 三家 → reconcile→修補→原提出方閉合→三家 RECONCILE-STAMP
2. 使用者跑 UAT B 段 13 項（`docs/GAP3_UAT_CHECKLIST.md`）並簽字 → GAP-3 結案
