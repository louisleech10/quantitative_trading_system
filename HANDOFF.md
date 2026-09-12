# HANDOFF — 當前任務狀態

**更新：2026-09-12｜現行票：`SPLITUNIFY 收尾`（大；RISK a,b,c）｜規格已定案（R13 兩家 proceed 零 finding、三家戳記全數 APPROVED，收斂檔 body sha `e3f2847d7fae…`）｜**b8 實作：程式面已收斂，剩 mutation 自證與三家審碼****

## b8 交付內容（皆已 commit＋push；最新 `29582d96`）
- `SplitPlan` 新增 `row_index_local`／`row_time_fingerprint`（相容 default）；`__post_init__` 對兩個 row 欄 defensive copy ＋ `np.frombuffer(bytes)` 唯讀。誠實邊界：`pickle`／`deepcopy` 還原仍可寫。
- 共用助手 `split_preview.epoch_ms_from_index`／`build_row_time_fingerprint`（該模組不匯入專案模組，無循環）；`split_projection._index_as_ms` 委派之。
- `contracts.attest_row_index_local`：前置合法性閘（整數型／等長／範圍／無重複／嚴格遞增）＋時間序往返。三個 producer 全數接上。
- `derive_event_split_from_plans` 改分派器＋`_derive_single_symbol`；per-symbol 迴圈與 `_manifest_subset`；Task 8.3 逐標的門檻。
- 投影端只讀 `row_index_local`、缺欄 fail-closed 不回退、入口指紋重驗。
- 🔴 **2026-09-12 修掉上一批的自傷缺陷（producer 端指紋時鐘）**：`split_per_symbol` 的 `ts` 與 `ic_filter_orchestrator` 的 `features_df.index` 皆為 **epoch 秒**，上一批卻直接餵給毫秒正規化器 ⇒ `test_split_per_symbol_golden` 與 `tests/api/test_splitunify_disclosure` 全紅，**IC 實跑路徑亦會被自己的守衛擋死**。修法＝指紋時鐘取該 producer **模組內既有的那一支**，不新造第二套換算：`split_per_symbol` 與其 `time_bounds` 共用 `_coerce_timestamp_array`；`ic_filter_orchestrator` 之 `time_bounds` 走 `_coerce_timestamp_array`、指紋走該檔切邊界時**已經在用**的 `_normalize_ic_time_index`——🔴 **兩者是不同函式**（grok R1 指正我先前「同一支」的措辭不精確），但對 epoch 秒皆以 `unit="s"` 解讀，端點實測相等（`ms0 == tb0_ms`）；`ic_split_adapter` 之 `ts` 本為 `datetime64`，維持原樣。
- 測試：目標測試面 **738 passed**；`freeze_splitunify_golden.py` 回報 **GOLDEN OK**（digest 未位移）。新增 `-k time_bounds_inconsistent`，使 `time_bounds` 同源閘不因指紋閘上線而變成沒有測試會紅的死碼。

## b8 未完成
- mutation 自證做完：22 條執行、22 條皆被測試抓到；`M-SU-D1-23` 在單標的 golden fixture 下**不可觸發**（該 fixture 之 `row_index_local` 與 `row_index` 逐值相同），已具名為 `needs-research`，交審碼三家裁定是否值得為它把 golden 改成兩標的交錯重凍。收據：`handoffs/run_receipts/20260912-splitunify-b8-mutation-selfcheck.md`。過程撈出兩個**真實測試缺口**並已補：①`feature_index_by_symbol` 缺 symbol 時改成丟棄，原本一條測試都不會紅 ②重排那條只寫 `pytest.raises(ValueError)`，被 `time_bounds` 閘先擋而失去鑑別力，已改為指名「非嚴格遞增」。
- **審碼 R1 已收**（session `20260911-splitunify-b8-review-r1`、`round_id=67fe8449`、債已清）：composer／grok `proceed` 零 P0／P1；**codex `blocked`**，開兩條 P1＋一條 P2。三條主委獨立複驗後**全部成立**並已修補（commit `5ac5bd8d`）：①dtype 閘被前置 `astype(int)` 繞過（float64 序號靜默救活；`M-SU-D1-22` 測的是 attest 函式、不是 producer 路徑，所以抓不到）②未選列 `NaT` 無人擋卻參與 rows 單位 purge 計數 ③投影 docstring 仍用全框座標。收斂檔 `handoffs/reconcile/20260911-splitunify-b8-review-r1/synth.md`（五條逐條歸戶、completeness PASS）。
- **R2 閉合輪已收**（`round_id=d5bda4d6`，債已清）：R1 三條由 codex（原提出方）與 composer 判定 `CLOSED`；但三家**一致**再開一條——我在 R1 修補時引入的新缺陷：`ic_split_adapter._with_row_positions` 的 NaT 閘 `raise AlignmentViolationError` 卻**未匯入**該類別 ⇒ 觸發時拋 `NameError`，而它不在 `ValueError` 階層、會穿透呼叫端既有的 except。嚴重度 grok 判 P1、另兩家 P2，依「分歧採較嚴版」以 P1 處理。已修（commit `655d52d4`）並補兩條 adapter 路徑測試。🔴 **漏網根因**：上一批只補 `split_per_symbol` 路徑的 NaT 測試，adapter 路徑無測試 ⇒ 缺 import 不會讓任何一條變紅。**同一道閘在兩條 producer 路徑上各需一條測試**。🔴 **我的查證方法錯誤**：當時 grep 該類別名確認可用，命中的卻是我自己剛寫的那行 raise——驗證符號可用要看 import 區或實跑，不能只看名字出現過。
- **R3 閉合輪已收**（`round_id=aefcb7fd`，債已清）：三家皆 `proceed`，各自閉合自家 R2 finding，僅各開一條 P3 sentinel。grok（R2 原提出方）依章程 §B8 重跑自己的反例確認 adapter NaT 閘現拋 `AlignmentViolationError` 且訊息含 `NaT`；三家對「缺 import／單路徑閘／golden 位移」三面主動攻擊未再開洞。收斂檔 `handoffs/reconcile/20260911-splitunify-b8-review-r3/synth.md`，Verdict：可合併。
- **三輪總結**：R1 codex `blocked`（兩 P1＋一 P2，主委獨立複驗全部成立）→ 修補 → R2 三家一致再開一條（主委修補時引入的未匯入例外，依「分歧採較嚴版」以 P1 處理）→ 修補 → R3 三家 `proceed`。🔴 **沒有任何一輪靠「無 finding」停輪**，三輪皆有具名攻擊面。
- **回歸判定：本批回歸為零**。`tests/momentum`＋`tests/api` 跑到約 2,200 條時收窄（FDR 模擬單條數十分鐘），對浮現的 10 筆紅做**對照實驗**：把 b8 動過的六個生產檔整組 `git checkout 0190c918`（b8 前一筆）後重跑，10 筆**全數同樣紅**，還原前後各以 `grep -c row_index_local` 驗證 checkout 真的生效。10 筆分屬 1c-FR allowlist、IC cut1 golden、persist redirect、ichc contract／golden、Optuna，皆為既有紅。

## 坑（沿用＋本日新增）
- impl token 900 秒過期即須重領；生產碼 commit 必帶 `Ticket-Batch: 20260911-SPLITUNIFY/b8`；task-id／session 日期前綴一律沿用 `20260911-SPLITUNIFY`（跨日不得改）。
- 🔴 **G-7 是 warn-only**（2026-09-05 使用者裁定，理由逐字寫在 `scripts/git_hooks/commit-msg:20-24`）——commit 後看到它的提示**不必**補 `Governance-Scope` trailer。本日我誤判為「空心閘」並據此 amend，白繞三趟。
- 產品碼一律用**限定路徑**提交（`git commit -F msg -- <路徑…>`）：不限定會把還在暫存區的 brief 一起帶進宣稱檢查而被擋。目前 `handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R11-BRIEF.md` 仍在暫存區且第 51 行缺 VERIFY 背書。
- `handoffs/*` 已被 `.git/info/exclude` 排除，新交件檔須 `git add -f` 才入版。
- 🔴 **zsh 預設不對未加引號的變數做分詞**：`FILES="a b c"; git checkout <sha> -- $FILES` 會把整串當成**單一路徑**，git 報 pathspec 不符而**什麼都沒還原**——我據此跑完 150 秒對照實驗才發現是空的。批次路徑一律逐一列出，或加 sanity 檢查確認狀態真的變了。
- commit 訊息含「全綠／綠燈／已驗／真紅」等宣稱用語會被 `verification_claim_check.py` 擋，且 commit **零豁免**（不能用 `VERIFY-EXEMPT`）。
- 🔴 **orchestrator 的 float 秒地雷**（grok R1 實跑）：`features_df.index` 若為 **float** 秒，`_normalize_ic_time_index` 解成 1970、`_coerce_timestamp_array` 解成 2023，兩路**值分叉**；目前不構成存活缺陷，因為 `holdout_boundary` 會先 raise「looks like epoch seconds」而不產出 plan。日後若放寬該前置閘，這條會立刻變成真缺陷。
- 戳記外置於 reconcile synth ⇒ 對 `docs/*.md` 直接跑 `reconcile_stamps_check.sh` 必 rc=1，不是治理真空。

## 下一步
b8：mutation 測試 → 三家審碼 → 驗收。
其後批次序：b9＝SU-RESID-2＋下游單鍵；D1 走 R 重開重戳；b10＝R-5（不得與未完成之 D1 同批上線）。
