# HANDOFF — 當前任務狀態

> 本檔數字之抽驗紀錄：`handoffs/run_receipts/20260905-handoff-audit.receipt.json`（HEAD `9a795fa4`）。
> 🔴 那是**主委手動抽驗**的紀錄，**不是** runner 產生的驗證鏈 receipt，故**刻意不佔用** `VERIFY:` token
> （該 token 需 receipt＋log＋audit 事件三者齊備；手湊等於偽造 provenance）。要複驗就重跑檔內 `checks` 各列。

**更新：2026-09-05｜狀態：G-7FIX 已結案（轉向＋作廢）。下一件＝回 `G3-D2` 主線之 B-D4，使用者裁定開新 session 做。**

## 🔴 下一件＝B-D4（唯一待辦）

**唯一入口＝`docs/GAP3D2_IMPL_HANDOFF.md`**（§0 文件層級、§1 五批順序、§2 每批七步**不得跳步**、§3 已知地雷、§4 使用者裁定總表、§5 收據）。

B-D4＝`docs/GAP3_EVENT_UX_TODO.D-006.md` Task **D4.2**（其餘進場語意全矩陣 13 對＋`rejected_pairs`／`pair_rejected` UI＋成對可行域與兩上界＋三層 oracle）
＋Task **D4.3**（k 參數化：seeds 去 k、雙值揭露；`event_label_scan` 網格：背景 task、`to_thread`、timeout、progress、partial）。

🔴 **D4.3 之 benchmark 子步須先於凍結 cap**（`scripts/gap3_scan_benchmark.py` → receipt → 據實測改 `scan_grid_max_runs` 等 `example_default`）。
🔴 新 TODO 起適用 `templates/TODO_GENERATION_PROMPT.md` 新增之 **`- 路徑：`** 欄。

## 前三批狀態（2026-09-05 抽驗過，非轉抄）

`B-D0`／`B-D1`／`B-D3` 皆 ✅ DONE，收據在 `GAP3D2_IMPL_HANDOFF.md` §5。抽驗結果見上方 receipt：
四個批次 commit 皆存在；`tests/momentum/event_samples/` 之計數與 golden case 數皆與 §5 記載相符。

## G-7FIX 結案紀錄（不需接手；僅供理解本 session 產品碼幾乎沒動之原因）

**我發散了，使用者叫停。** 6 輪（`handoffs/reconcile/20260905-g7*/`）、71 條 finding、12 個 P0、**產品碼改動零行**；
P0 序列 **4→4→3→2**，且每輪 P0 都長在我當輪剛寫的產物裡
（consult R2 群集 β、SPEC review R1 群集 1、review R2 之 6 條全為我 R1 修法所生）＝finding 產生器。

🔴 產生器＝`epic_state` 狀態機，**已整套作廢**：`docs/G7FIX_SPEC.md` **不再是有效計畫，勿據以施工**。

**關鍵事實**：G-7 保護的 GOVB1 是 `DRAFT`、從未實作、2026-08-14 遭裁定擱置；
且會驗 trailer 的檢查自 2026-08-14 起沒在 push 上跑過（`gov_check.sh:266-267` `--fast` 早退，G-7 段在 `:343-350`）
⇒ trailer 一直被收，沒有東西在讀。

**已交付**：
- ✅ 第 4 步（`ffb7dba7`）：`templates/TODO_GENERATION_PROMPT.md` 加 `- 路徑：` 欄（加欄不換欄、前向適用、**禁被任何 gate 當 scope 來源**、無格式閘並具名殘留 `needs-research`）
- ✅ 第 3 步（`5b404be9`）：改掉兩處假敘述（`gov_check.sh` 檔頭、`fact_keys.json` E-005 掛載點）
- ✅ 白話說明八份同步（`9a795fa4`），含上一批 `ef95e9b7` 漏更新的三份

**已裁定不做**：第 1+2 步之精簡版（`g7_trailer_precheck.sh`：scope 逐路徑判 → 硬保護集；trailer 值改向 gate 取）。
理由＝未經任何一家審查，且動每次 commit 都經過的共用控制流、命中高風險原則 (b) ⇒ 大任務需完整管線；
使用者 2026-09-05 裁定「還要來回好幾輪就不要做」。量測見上方 receipt 之 `trailer_stats_at_head`。**不做也不擋主線。**

## 環境現況

開放債為零；無未推送 commit。工作區僅餘兩個 2026-09-01 遺留之 `uat_samples/*拷貝*` 未追蹤檔
與 `market_data/*` 快取異動，皆非本 session 產物，**勿順手 commit**。
