# FF-STAT SPEC v41 審查 r22：r21 閉合複核＋v41 改動

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R22

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R22-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准列本家族前綴之 r21 ID，逐一列出經你複核確認閉合者；不得寫 `none` 等非 ID 字面）。零 finding 用 `## <FAMILY>-R22-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run；探針用真實 `data_cache/feature_klines/kline_cache.h5` 之小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git diff 38ca2137 834f41af -- docs/FFSTAT_SPEC.md`：v41 版本註記、§G⑦ M_tf 定義（改為 K_max_tf 及其理由）、§A 交易所真實缺口、Task 4.1 12h N 一致率、§N 刪 12h 校準長度殘留。
- r21 收斂：`handoffs/reconcile/20260926-ffstatauto-x-review-r21/synth.md`。
- **使用者裁定（不重議）**：同 r13 brief 之 R1–R7（`handoffs/20260927-ffstat-b4-redesign-rulings.md`）；使用者已同意 v32 送審。
- v40 以前已閉合、且 v41 未改動之條文不在本輪範圍。
## 本 brief 前提
fact-verified: L7 `find_dead_columns` 以 `notna().sum() < min_valid_samples` 與 `nunique(dropna=True) < 2` 判定、不計 NaN 率 → `sed -n 44,90p momentum/FeatureEngineering/utils/dead_feature_filter.py`
fact-verified: TA-Lib 指標皆經 `TALibWrapper.compute`／`compute_batch`（持有參數字典）→ `grep -n "def compute\b\|def compute_batch" momentum/FeatureEngineering/atomic/talib_wrapper.py`（:316、:347）
fact-verified: 長歷史快取之列數與起訖 → `handoffs/run_receipts/20260927-ffstat-longhist-download.log`、`-5m-1d.log`（BTC 12h 6,656、1d 3,329、5m 105,260 根）
assumed: M_tf＝K_max_tf 時，(i) 預設全設定於 BTC 12h 6,656 根上資格可滿足（主委估算需約 5,100 根：K_max 2,051＋F_max 約 2,550＋500）；(ii) 「刪 L1 遮罩」「縮尾不遮」「第④類不遮」「recursive 係數改 1.0」四個 mutant 皆使 B 開頭未收斂而與已收斂之 A 相異（≥ 0.005 判準），故仍必紅。
→ 否證觀測：(i) 預設設定之實際 F_max_12h 使 2,051＋F_max＋500 > 6,656；(ii) 某 mutant 下 B 開頭之未收斂偏差小於 0.005 判準（如某指標收斂極快），使 mutant 不紅。／我跑了：只以 `_collect_l*_warmup_bars` 取各層窗長（L1 2,051、L2 233、L3 233、L4 34、L6 55、L6.5 500）估算。

## 攻擊面
- **已排除**：使用者裁定 R1–R9 本身；v40 以前已閉合且 v41 未改之條文；IC-First 管線合一票之設計；manifest 同步時點；v35 逐位元組框架；v34–v36 之 12h 子集選擇器。
- **我沒查**：①測試以儲存層 `cache_dir` 指向長歷史快取之可行性（FF 之 L0 讀取是否可注入另一快取目錄而不改生產預設路徑）；②5m 一年 105,260 根於倍數量測腳本（eval window 1,000、max K cap 4,000）下之記憶體與耗時；③ADA 12h 起點較晚（2018-04-17）對跨標的取最大之影響。

**收斂說明**：r20 兩家 proceed 零 finding；本輪只審 v41 差分與 r21 閉合；請以真實 BTC 12h 長歷史驗「M_tf＝K_max_tf 下資格可滿足」與「三個遮罩 mutant 仍必紅」之論證是否成立。

## 必答（成對）
1. **(1a)** 本家 r21 各條是否閉合？**(1b)** 逐條以原反例重跑或對條文逐字核對之結果（部分採納／延後者，判其理由是否成立）。
2. **(2a)** v41 有無新缺陷？**(2b)** 可重現反例（真實 kline 切片之輸入或操作序列）。
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
