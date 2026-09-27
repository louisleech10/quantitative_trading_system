# FF-STAT SPEC v42 審查 r23：r22 閉合複核＋v42 改動

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R23

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R23-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准列本家族前綴之 r22 ID，逐一列出經你複核確認閉合者；不得寫 `none` 等非 ID 字面）。零 finding 用 `## <FAMILY>-R23-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run；探針用真實 `data_cache/feature_klines/kline_cache.h5` 之小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git diff 834f41af c6f7e6db -- docs/FFSTAT_SPEC.md`：v42 版本註記、§G⑦（12h 實測 F_max 收據與不合資格交使用者裁定、係數 mutant 固定 ADXR 233）。
- r22 收斂：`handoffs/reconcile/20260926-ffstatauto-x-review-r22/synth.md`。
- **使用者裁定（不重議）**：同 r13 brief 之 R1–R7（`handoffs/20260927-ffstat-b4-redesign-rulings.md`）；使用者已同意 v32 送審。
- v41 以前已閉合、且 v42 未改動之條文不在本輪範圍。
## 本 brief 前提
fact-verified: L7 `find_dead_columns` 以 `notna().sum() < min_valid_samples` 與 `nunique(dropna=True) < 2` 判定、不計 NaN 率 → `sed -n 44,90p momentum/FeatureEngineering/utils/dead_feature_filter.py`
fact-verified: TA-Lib 指標皆經 `TALibWrapper.compute`／`compute_batch`（持有參數字典）→ `grep -n "def compute\b\|def compute_batch" momentum/FeatureEngineering/atomic/talib_wrapper.py`（:316、:347）
fact-verified: 長歷史快取之列數與起訖 → `handoffs/run_receipts/20260927-ffstat-longhist-download.log`、`-5m-1d.log`（BTC 12h 6,656、1d 3,329、5m 105,260 根）
assumed: 「刪 L1 遮罩」「縮尾不遮」「第④類不遮」三個 mutant 於真實 BTC 1h 預設全設定下，至少各有一欄之 B 開頭偏差 ≥ 0.005 判準而紅（係數 mutant 已固定 ADXR 233 且經 r22 codex 實跑為紅）。
→ 否證觀測：某一 mutant 下全部受影響欄之 B 開頭偏差皆 < 0.005（如縮尾之不完整窗界線與完整窗界線差異極小），使 mutant 不紅。／我跑了：無。

## 攻擊面
- **已排除**：使用者裁定 R1–R9 本身；v41 以前已閉合且 v42 未改之條文；IC-First 管線合一票之設計；manifest 同步時點；v35 逐位元組框架；v34–v36 之 12h 子集選擇器。
- **我沒查**：①測試以儲存層 `cache_dir` 指向長歷史快取之可行性（FF 之 L0 讀取是否可注入另一快取目錄而不改生產預設路徑）；②5m 一年 105,260 根於倍數量測腳本（eval window 1,000、max K cap 4,000）下之記憶體與耗時；③ADA 12h 起點較晚（2018-04-17）對跨標的取最大之影響。

**收斂說明**：r20 兩家 proceed 零 finding；本輪只審 v42 差分與 r22 閉合；F_max_12h 須實作後實跑方可得，SPEC 已改為收據＋不合資格交使用者裁定，勿再以「未實跑」本身列 finding。

## 必答（成對）
1. **(1a)** 本家 r22 各條是否閉合？**(1b)** 逐條以原反例重跑或對條文逐字核對之結果（部分採納／延後者，判其理由是否成立）。
2. **(2a)** v42 有無新缺陷？**(2b)** 可重現反例（真實 kline 切片之輸入或操作序列）。
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
