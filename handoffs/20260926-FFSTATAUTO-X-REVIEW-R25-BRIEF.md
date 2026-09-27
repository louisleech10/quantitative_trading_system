# FF-STAT TODO 審查 r25：r24 閉合複核＋TODO 修補

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R25

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R25-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准列本家族前綴之 r24 ID，逐一列出經你複核確認閉合者；不得寫 `none` 等非 ID 字面；多個 ID 以半形逗號分隔）。零 finding 用 `## <FAMILY>-R25-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run、不跑 §G⑦ 雙起點全設定測試；探針用真實 K 線小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git show 3761b465` 與其 diff：`tests/feature_engineering/test_ffstat_stable_start.py`（`_ast_step_functions` 前綴擴大；⑧ 精確等式；⑪ `test_paths_same_stable_start_and_masks`；⑫ 四支 `run_ic_first` 測試；刪重複之邊界④測試）、`tests/_golden/ffstat/nan_propagation_classes.json`（92 步逐步分類與碼證）、`handoffs/run_receipts/20260927-ffstat-nan-propagation-inventory.json`、`docs/manifests/FFSTAT.json`（對照更新）。
- r24 收斂：`handoffs/reconcile/20260926-ffstatauto-x-review-r24/synth.md`。
- SPEC v44 與 r24 審查標的未改動之部分不在本輪範圍。

## 本 brief 前提
fact-verified: `stable_start_receipts.py inventory` rc=0（92 步無未分類）；`test_nan_propagation_inventory_complete` 綠；`test_ffstat_stable_start.py` 54 支可收集、mutation 靜態器 rc=0；`template_check.sh todofmt` PASS（主委實跑 2026-09-27）。
assumed: 92 步之分類正確——特別是標為 propagating 之 50 步對 L1 遮罩後之 NaN 開頭確實延後輸出、標為 not_a_data_step 之 27 步確實不產生特徵值。
→ 否證觀測：某標 propagating 之步驟對 NaN 開頭輸入於窗未滿時即輸出有限值；或某標 not_a_data_step 之函式實際產生輸出欄之值。／我跑了：只讀碼（逐函式抽關鍵寫法），未以真實切片逐步實跑。

## 攻擊面
- **已排除**：r24 以前已收斂之內容；SPEC 條文；使用者裁定 R1–R9。
- **我沒查**：①`test_run_ic_first_uses_own_window_not_previous` 以 `lease_sink` 內容字串比對 hash 之可行性（lease 物件是否含設定 hash）；②`test_paths_same_stable_start_and_masks` 之 resume 路徑（同一 tmp 目錄第二次 `force_regenerate=False`）是否真走 CGSA 續跑；③⑧ 之 `TimeframeAligner.align_to_primary` 以 `reset_index` 後之 timestamp 欄為來源之呼叫形式是否正確。

## 必答（成對）
1. **(1a)** 本家 r24 條目是否閉合？**(1b)** 逐條核對結果（composer 請以原反例重跑 inventory）。
2. **(2a)** 修補有無新缺陷？**(2b)** 可重現反例。
3. **(3a)** assumed 判成立或不成立？**(3b)** 抽驗之步驟與真實切片實跑結果（建議抽 propagating 與 not_a_data_step 各至少 3 步）。
4. **(4a)** 「我沒查」①–③ 各有無命中？**(4b)** 碼證。
5. **(5a)** 本版 TODO 可否放行實作（`VERDICT: proceed`）？**(5b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 使用者定死「任何每次都會跑的檢查，單次必須秒級」；驗收測試不在此限，但須於 coverage_risk 記實測時長。
2. 威脅模型＝**意外漂移**；每條 P0／P1 須附可重現之輸入或操作序列。
3. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由。
4. 研究設計不得寫死 24h／UTC／加密貨幣特有假設。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api scripts tests docs templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
