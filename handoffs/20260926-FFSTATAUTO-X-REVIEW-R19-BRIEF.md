# FF-STAT SPEC v38 審查 r19：r18 閉合複核＋v38 改動

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R19

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R19-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准列本家族前綴之 r18 ID，逐一列出經你複核確認閉合者；不得寫 `none` 等非 ID 字面）。零 finding 用 `## <FAMILY>-R19-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run；探針用真實 `data_cache/feature_klines/kline_cache.h5` 之小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git diff 5551dc5b bfb5ad83 -- docs/FFSTAT_SPEC.md`：v38 版本註記、§C L1 輸出點契約、Task 2.3 ①（12h 逐輸出點、params={} 自訂指標負例）、Task 2.4（`period_keys` 交付與驗收）。
- r18 收斂：`handoffs/reconcile/20260926-ffstatauto-x-review-r18/synth.md`。
- **使用者裁定（不重議）**：同 r13 brief 之 R1–R7（`handoffs/20260927-ffstat-b4-redesign-rulings.md`）；使用者已同意 v32 送審。
- v37 以前已閉合、且 v38 未改動之條文不在本輪範圍。
## 本 brief 前提
fact-verified: L7 `find_dead_columns` 以 `notna().sum() < min_valid_samples` 與 `nunique(dropna=True) < 2` 判定、不計 NaN 率 → `sed -n 44,90p momentum/FeatureEngineering/utils/dead_feature_filter.py`
fact-verified: TA-Lib 指標皆經 `TALibWrapper.compute`／`compute_batch`（持有參數字典）→ `grep -n "def compute\b\|def compute_batch" momentum/FeatureEngineering/atomic/talib_wrapper.py`（:316、:347）
assumed: v38 之「L1 輸出點契約」在不改任何指標數值計算、不改產欄數之前提下可實作（只新增逐欄參數對應與遮罩），且 CODEX-R18-P1-01 之 `params={}` 自訂指標反例於契約下必 fail-closed。
→ 否證觀測：某進階 atomic 或自訂指標須改其計算流程（如拆輸出、改欄名）才能逐欄提供參數字典，從而改變產欄數或數值。／我跑了：無。

## 攻擊面
- **已排除**：使用者裁定 R1–R7 本身；v37 以前已閉合且 v38 未改之條文；IC-First 管線合一票之設計；CODEX-R14-P1-01 之延後理由；v35 逐位元組框架；v34–v36 之 12h 子集選擇器（v37 已刪）。
- **我沒查**：①entropy、tail_risk 引擎是否亦有類似 microstructure `get_feature_metadata` 之欄級參數來源；②CDL pattern 類（無週期、預設 5 根）於輸出點契約下之 `period_keys` 為空集合時，K 取表內登記值是否與現行 `pattern_default_warmup_bars` 一致；③12h 逐輸出點驗收於 8 GB 下之耗時（預設全設定 L1 單層、1,696 根）。

## 必答（成對）
1. **(1a)** 本家 r18 各條是否閉合？**(1b)** 逐條以原反例重跑或對條文逐字核對之結果（部分採納／延後者，判其理由是否成立）。
2. **(2a)** v38 有無新缺陷？**(2b)** 可重現反例（真實 kline 切片之輸入或操作序列）。
3. **(3a)** 兩條 assumed 各判成立或不成立？**(3b)** 碼證或實跑數字。
4. **(4a)** 「我沒查」①–③ 各有無命中？**(4b)** 碼證。
5. **(5a)** 本版可否定案（`VERDICT: proceed`）？**(5b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 使用者定死「任何每次都會跑的檢查，單次必須秒級」；嚴禁新增分鐘／小時級之生成期檢查（驗收測試不在此限）。
2. 威脅模型＝**意外漂移**；每條 P0／P1 須附可重現之輸入或操作序列。
3. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由。
4. 研究設計不得寫死 24h／UTC／加密貨幣特有假設（使用者：之後要建台股、美股、期貨）。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api scripts tests docs templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
