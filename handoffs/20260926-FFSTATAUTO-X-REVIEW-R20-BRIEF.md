# FF-STAT SPEC v39 審查 r20：r19 閉合複核＋v39 改動

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R20

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R20-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准列本家族前綴之 r19 ID，逐一列出經你複核確認閉合者；不得寫 `none` 等非 ID 字面）。零 finding 用 `## <FAMILY>-R20-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run；探針用真實 `data_cache/feature_klines/kline_cache.h5` 之小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git diff bfb5ad83 fa3d1b85 -- docs/FFSTAT_SPEC.md`：v39 版本註記、§C 輸出點契約之 v39 段（遞移 period_keys、自訂指標 outputs 宣告）、Task 2.4 CDL pattern 映射、§P TODO 同步必含清單。
- r19 收斂：`handoffs/reconcile/20260926-ffstatauto-x-review-r19/synth.md`（含主委說明：§G⑦ 對任何輸出 K 算短皆實證終審）。
- **使用者裁定（不重議）**：同 r13 brief 之 R1–R7（`handoffs/20260927-ffstat-b4-redesign-rulings.md`）；使用者已同意 v32 送審。
- v38 以前已閉合、且 v39 未改動之條文不在本輪範圍。
## 本 brief 前提
fact-verified: L7 `find_dead_columns` 以 `notna().sum() < min_valid_samples` 與 `nunique(dropna=True) < 2` 判定、不計 NaN 率 → `sed -n 44,90p momentum/FeatureEngineering/utils/dead_feature_filter.py`
fact-verified: TA-Lib 指標皆經 `TALibWrapper.compute`／`compute_batch`（持有參數字典）→ `grep -n "def compute\b\|def compute_batch" momentum/FeatureEngineering/atomic/talib_wrapper.py`（:316、:347）
assumed: 「同引擎衍生輸出 K＝上游 K 遞推」涵蓋預設設定下全部 L1 引擎內之衍生關係（microstructure、entropy、tail_risk、pattern、Keltner／Force Index 等），且上游已解析參數皆可於引擎內取得而不改數值與產欄數。
→ 否證觀測：某引擎之衍生輸出依賴一個無法於引擎內取得或未登記之上游參數（如全域常數、跨引擎輸入），只能依欄名推得。／我跑了：只讀了 microstructure VPIN z-score 與 pattern 兩處（來自 r19 codex 探針）。

## 攻擊面
- **已排除**：使用者裁定 R1–R7 本身；v38 以前已閉合且 v39 未改之條文；IC-First 管線合一票之設計；manifest 同步時點（v39 §P 已列必含清單，TODO 審查輪對證）；v35 逐位元組框架；v34–v36 之 12h 子集選擇器（v37 已刪）。
- **我沒查**：①entropy、tail_risk 引擎內是否有衍生輸出（其 metadata 是否帶上游參數）；②`CustomIndicatorDef.outputs` 為必填後，既有測試或 API 模型中建構 `CustomIndicatorDef` 之處是否會因缺欄驗證失敗；③「逐點聚合取上游最大 K」對 Consensus 類在上游某欄為稀疏（間歇 NaN）時是否仍一義。

**收斂說明**：composer 已連續 r16–r19 四輪判 proceed；本輪請聚焦 v39 差分與 r19 閉合，新 finding 須為 v39 條文可重現之缺陷，勿以實作細節之可能變體列 P1（實作精確度另由 §G⑦ 1h／4h 預設全設定之雙起點收斂實證終審）。

## 必答（成對）
1. **(1a)** 本家 r19 各條是否閉合？**(1b)** 逐條以原反例重跑或對條文逐字核對之結果（部分採納／延後者，判其理由是否成立）。
2. **(2a)** v39 有無新缺陷？**(2b)** 可重現反例（真實 kline 切片之輸入或操作序列）。
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
