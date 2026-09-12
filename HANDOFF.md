# HANDOFF — 當前任務狀態

**更新：2026-09-12｜現行票：`SPLITUNIFY 收尾`（大；RISK a,b,c）｜規格已定案（R13 兩家 proceed 零 finding、三家戳記全數 APPROVED，收斂檔 body sha `e3f2847d7fae…`）｜**b8 實作：程式面已收斂，剩 mutation 自證與三家審碼****

## b8 交付內容（皆已 commit＋push；最新 `29582d96`）
- `SplitPlan` 新增 `row_index_local`／`row_time_fingerprint`（相容 default）；`__post_init__` 對兩個 row 欄 defensive copy ＋ `np.frombuffer(bytes)` 唯讀。誠實邊界：`pickle`／`deepcopy` 還原仍可寫。
- 共用助手 `split_preview.epoch_ms_from_index`／`build_row_time_fingerprint`（該模組不匯入專案模組，無循環）；`split_projection._index_as_ms` 委派之。
- `contracts.attest_row_index_local`：前置合法性閘（整數型／等長／範圍／無重複／嚴格遞增）＋時間序往返。三個 producer 全數接上。
- `derive_event_split_from_plans` 改分派器＋`_derive_single_symbol`；per-symbol 迴圈與 `_manifest_subset`；Task 8.3 逐標的門檻。
- 投影端只讀 `row_index_local`、缺欄 fail-closed 不回退、入口指紋重驗。
- 🔴 **2026-09-12 修掉上一批的自傷缺陷（producer 端指紋時鐘）**：`split_per_symbol` 的 `ts` 與 `ic_filter_orchestrator` 的 `features_df.index` 皆為 **epoch 秒**，上一批卻直接餵給毫秒正規化器 ⇒ `test_split_per_symbol_golden` 與 `tests/api/test_splitunify_disclosure` 全紅，**IC 實跑路徑亦會被自己的守衛擋死**。修法＝指紋時鐘取該 producer **自己 `time_bounds` 已在用的那一支**（`_coerce_timestamp_array`／`_normalize_ic_time_index`），不新造第二套換算；`ic_split_adapter` 之 `ts` 本為 `datetime64`，維持原樣。
- 測試：目標測試面 **738 passed**；`freeze_splitunify_golden.py` 回報 **GOLDEN OK**（digest 未位移）。新增 `-k time_bounds_inconsistent`，使 `time_bounds` 同源閘不因指紋閘上線而變成沒有測試會紅的死碼。

## b8 未完成
- `M-SU-D1-01`～`23` mutation 逐條自證；Task 8.1／8.2／8.3 之固定文法斷言。
- 收案前派三家審碼（實作者不自審）。
- **回歸判定：本批回歸為零**。`tests/momentum`＋`tests/api` 跑到約 2,200 條時收窄（FDR 模擬單條數十分鐘），對浮現的 10 筆紅做**對照實驗**：把 b8 動過的六個生產檔整組 `git checkout 0190c918`（b8 前一筆）後重跑，10 筆**全數同樣紅**，還原前後各以 `grep -c row_index_local` 驗證 checkout 真的生效。10 筆分屬 1c-FR allowlist、IC cut1 golden、persist redirect、ichc contract／golden、Optuna，皆為既有紅。

## 坑（沿用＋本日新增）
- impl token 900 秒過期即須重領；生產碼 commit 必帶 `Ticket-Batch: 20260911-SPLITUNIFY/b8`；task-id／session 日期前綴一律沿用 `20260911-SPLITUNIFY`（跨日不得改）。
- 🔴 **G-7 是 warn-only**（2026-09-05 使用者裁定，理由逐字寫在 `scripts/git_hooks/commit-msg:20-24`）——commit 後看到它的提示**不必**補 `Governance-Scope` trailer。本日我誤判為「空心閘」並據此 amend，白繞三趟。
- 產品碼一律用**限定路徑**提交（`git commit -F msg -- <路徑…>`）：不限定會把還在暫存區的 brief 一起帶進宣稱檢查而被擋。目前 `handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R11-BRIEF.md` 仍在暫存區且第 51 行缺 VERIFY 背書。
- `handoffs/*` 已被 `.git/info/exclude` 排除，新交件檔須 `git add -f` 才入版。
- 🔴 **zsh 預設不對未加引號的變數做分詞**：`FILES="a b c"; git checkout <sha> -- $FILES` 會把整串當成**單一路徑**，git 報 pathspec 不符而**什麼都沒還原**——我據此跑完 150 秒對照實驗才發現是空的。批次路徑一律逐一列出，或加 sanity 檢查確認狀態真的變了。
- commit 訊息含「全綠／綠燈／已驗／真紅」等宣稱用語會被 `verification_claim_check.py` 擋，且 commit **零豁免**（不能用 `VERIFY-EXEMPT`）。
- 戳記外置於 reconcile synth ⇒ 對 `docs/*.md` 直接跑 `reconcile_stamps_check.sh` 必 rc=1，不是治理真空。

## 下一步
b8：mutation 測試 → 三家審碼 → 驗收。
其後批次序：b9＝SU-RESID-2＋下游單鍵；D1 走 R 重開重戳；b10＝R-5（不得與未完成之 D1 同批上線）。
