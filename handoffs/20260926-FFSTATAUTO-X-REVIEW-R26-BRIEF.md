# FF-STAT TODO 審查 r26：r25 閉合複核＋TODO 修補

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R26

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R26-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准列本家族前綴之 r25 ID，逐一列出經你複核確認閉合者；不得寫 `none` 等非 ID 字面；多個 ID 以半形逗號分隔）。零 finding 用 `## <FAMILY>-R26-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run、不跑 §G⑦ 雙起點全設定測試；探針用真實 K 線小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git show 7fece564` 與其 diff：`tests/feature_engineering/test_ffstat_stable_start.py`（resume 令快取落空並 spy `resume_from_manifest`；`run_ic_first` 以 `lease.path.name` 比對且 finally 釋放；盤點測試之新分類集合、派發函式 AST 檢查、index_derived 真實切片測試）、`tests/_golden/ffstat/nan_propagation_classes.json`（非資料步驟拆為 dispatcher／index_derived／helper／column_filter／mask）、盤點收據、`docs/manifests/FFSTAT.json`（實作前紅之預期原因一條）、`docs/FFSTAT_SPEC.md` v45（stable_start 一切生成皆寫）。
- r25 收斂：`handoffs/reconcile/20260926-ffstatauto-x-review-r25/synth.md`（composer P1-01、P1-02 駁回理由：實作前紅屬設計；請判理由是否成立）。
- SPEC v44 與 r24 審查標的未改動之部分不在本輪範圍。

## 本 brief 前提
fact-verified: `stable_start_receipts.py inventory` rc=0；`test_nan_propagation_inventory_complete` 與 `test_index_derived_step_has_no_warmup` 綠；`test_ffstat_stable_start.py` 55 支可收集、mutation 靜態器 rc=0；`template_check.sh todofmt` PASS（主委實跑 2026-09-27）。
assumed: 拆分後之 helper（15）與 column_filter（2）確實不產生公開輸出之特徵值；dispatcher（9）之輸出確實只來自其所呼叫之已分類步驟。
→ 否證觀測：某 helper 之回傳值直接成為輸出欄；或某 dispatcher 於呼叫子步驟之外另行計算並產生輸出欄之值。／我跑了：dispatcher 以 AST 驗「呼叫至少一個已列步驟」；helper 只讀碼。

## 攻擊面
- **已排除**：r25 以前已收斂之內容；SPEC 條文；使用者裁定 R1–R9；實作前因 API 或功能尚未實作而紅之測試（manifest「實作前紅之預期原因」已列）。
- **我沒查**：①resume 路徑以 `_try_load_cache` 回 None 後，`_prepare_cgsa_registry` 之 `resume_allowed` 條件是否成立（工作目錄與 manifest 是否仍在）；②`lease.path.name` 是否確含設定 hash（lease 檔名之組成）；③dispatcher 之 AST 檢查以「短名相符」判定是否會被同名但不同類之方法誤過。

## 必答（成對）
1. **(1a)** 本家 r25 條目是否閉合？**(1b)** 逐條核對結果（composer 請以原反例重跑 inventory）。
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
