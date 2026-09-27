# FF-STAT SPEC v34 審查 r15：r14 閉合複核＋v34 改動

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R15

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R15-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准列本家族前綴之 r14 ID，逐一列出經你複核確認閉合者；不得寫 `none` 等非 ID 字面）。零 finding 用 `## <FAMILY>-R15-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run；探針用真實 `data_cache/feature_klines/kline_cache.h5` 之小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git diff e376b590 f12e842e -- docs/FFSTAT_SPEC.md`：v34 版本註記、§C 死欄純函式之呼叫端門檻、§G①（機械核可）、§G⑦（12h 子集固定選擇器）、Task 2.3 ③（隨 §G② 收窄）與 ⑦（欄集合 delta sha256 與核可紀錄）。
- r14 收斂：`handoffs/reconcile/20260926-ffstatauto-x-review-r14/synth.md`（CODEX-R14-P1-01 之處置為「SPEC 定案後、實作派工前同步 manifest」，本輪請判其理由是否成立）。
- **使用者裁定（不重議）**：同 r13 brief 之 R1–R7（`handoffs/20260927-ffstat-b4-redesign-rulings.md`）；使用者已同意 v32 送審。
- v33 以前已閉合、且 v34 未改動之條文不在本輪範圍。
## 本 brief 前提
fact-verified: L7 `find_dead_columns` 以 `notna().sum() < min_valid_samples` 與 `nunique(dropna=True) < 2` 判定、不計 NaN 率 → `sed -n 44,90p momentum/FeatureEngineering/utils/dead_feature_filter.py`
assumed: §G⑦ 12h 固定選擇器必終止，且終止時子集非空（至少保留一個 recursive 指標，使「係數改 1.0」mutant 在 12h 子集上仍可偵測）。
→ 否證觀測：以真實 12h 1,696 根與預設全設定執行選擇器規則，移除至只剩非 recursive 指標或空集才滿足容量條件。／我跑了：無。
assumed: 欄集合 delta 之 sha256 可重現（欄名排序、編碼、差異原因之序列化在兩次相同 run 間逐位元組相同）。
→ 否證觀測：同設定兩次 run 之 delta 內容相同而 sha256 不同（如依字典迭代順序序列化）。／我跑了：無。

## 攻擊面
- **已排除**：使用者裁定 R1–R7 本身；v33 以前已閉合且 v34 未改之條文；IC-First 管線合一票之設計。
- **我沒查**：①選擇器「移除一個指標參數實例」後，多輸出指標之其他輸出與依賴該指標之 L2–L6 欄是否一併消失、F_max_tf 是否單調下降（非單調時可能不終止）；②L3 門檻 30 改以「首個有限值起」之有效樣本計後，與現行 `_variance_filter` 之有效樣本定義是否一致；③使用者核可紀錄之格式與寫入者（主委代寫時如何防止未經使用者核可即寫入）。

## 必答（成對）
1. **(1a)** 本家 r14 各條是否閉合？**(1b)** 逐條以原反例重跑或對條文逐字核對之結果（部分採納／延後者，判其理由是否成立）。
2. **(2a)** v34 有無新缺陷？**(2b)** 可重現反例（真實 kline 切片之輸入或操作序列）。
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
