# FF-STAT SPEC v32 審查 r13：預熱恆開與逐欄穩定點（使用者 2026-09-27 裁定之重設計）

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R13

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R13-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准本家族前綴之 r12 ID；r12 無 open ID 者寫 `CLOSED: none`）。零 finding 用 `## <FAMILY>-R13-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run；探針用真實 `data_cache/feature_klines/kline_cache.h5` 之小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git diff 2b45c1d8 9c37a345 -- docs/FFSTAT_SPEC.md`：v32 版本註記、§RISK、§A 六條新 FACT-RECEIPT 與 09-27 已確認結果、§C（校準資料無洩漏、**逐欄穩定點**、**公開域預熱**、兩個資料域、校準前置關卡、前史深度、**未填起始日**、死欄 NaN 率）、§G（v32 對凍結基準之改動、②、⑦雙起點收斂對證）、§P（Task 2.1 條文、**新 Task 2.4**、**改寫之 Task 2.3**、Task 4.1）、§V、§N。
- 裁定與查證全文：`handoffs/20260927-ffstat-b4-redesign-rulings.md`；倍數表缺項收據：`handoffs/run_receipts/20260927-warmup-table-coverage.txt`（重現腳本同名 `.py`）。
- **使用者裁定（不重議）**：R1 預熱恆開、不分有無起始日與平穩化開關，每欄第一個輸出值須已穩定；R3 每欄各自穩定點、不強制全表切齊；R4 穩定點依 L1「參數 × 倍數表係數」、每指標量一次、不每次生成重量；R5 倍數表查不到即擋下；R6 縮尾以完整窗遮開頭、不改計算；R7 post-IC rank／zscore 歸 IC-First 管線合一票。使用者已審白話逐條稿（`白話說明/FF-STAT第4批新版審閱.md`）並同意送審，含「每欄開頭多出 NaN」之輸出變更。
- **可審之主委提案**（非使用者裁定）：以「L1 遮罩＋NaN 傳遞＋不傳遞步驟盤點另遮」取代逐欄血緣記錄；無起始日時不另建校準域、校準取各欄穩定後最早 N 值並遮出輸出；有起始日時兩域不合併；D 加倍規則；§G ⑦ 之判準與 M。
- v31 以前已閉合、且 v32 未改動之條文不在本輪範圍（v29／v30 之 `run_ic_first` 條文保留，其驗收移入 Task 2.3 ⑫）。

## 本 brief 前提
fact-verified: L2 運算子、L3 滾動統計以 min_periods＝window 計算、fracdiff FFD 自首個有效值起 width−1 列為 NaN、縮尾以 min_periods＝max(20, window//4) 出值且界線未定時保留原值 → `sed -n 251p momentum/FeatureEngineering/operators/numba_rolling.py`、`grep -n "rolling(" momentum/FeatureEngineering/operators/rolling_aggregator.py`、`sed -n 3996,4030p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`、`cat momentum/FeatureEngineering/utils/winsor_params.py`
fact-verified: 預設設定 76 個 L1 指標中 39 個不在倍數表 → `venv/bin/python handoffs/run_receipts/20260927-warmup-table-coverage.py`
assumed: 除縮尾外，L2–L6.5 與多週期對齊之每一步驟皆傳遞 NaN（NaN 或不完整窗輸入不產生有限值），故「只遮 L1＋縮尾」即使每欄之首個有效值 ≥ 其真正穩定點。
→ 否證觀測：存在一個預設設定下啟用之步驟，對遮罩後之 NaN 開頭輸出有限值（如 fillna、expanding、ewm、cumsum、狀態計數器、ffill、`min_periods` < window、L5 參考標的對齊、L6 meta）。／我跑了：只讀了 `numba_rolling.py:251`、`_worldquant_numba.py:8`、`rolling_aggregator.py` 之 `rolling(window)`、FFD、縮尾；L4、L5、L6、多週期對齊、state_counters、L6.5 之 ADF 差分皆未讀。
assumed: 無起始日時，每個未平穩化之欄於其 `stable_start` 之後之值與改前逐位元組相同（§C「公開值之不變量」、§G ②）。
→ 否證觀測：某步驟之輸出在輸入已穩定後仍依賴其前段之 NaN／有限值樣式（如 expanding 統計、跨遮罩之 ffill、以全欄計算之正規化、依 NaN 率之分支）。／我跑了：無。

## 攻擊面
- **已排除**：使用者裁定 R1–R7 本身；v31 以前已閉合且 v32 未改之條文；IC-First 管線合一票之設計內容。
- **我沒查**：①L4、L5（含參考標的起點晚於主標的）、L6、`operators/state_counters.py`、ADF 差分與多週期對齊之 NaN 傳遞；②CGSA 串流路徑中 L1 遮罩之套用點是否先於任何 L2 消費（群組化計算）；③死欄判定排除遮罩列之可行性（L3 `_dead_filter` 與 L7 dead feature drop 之輸入是否知道遮罩列）；④§G ⑦ 以預設全設定跑 BTC 1h／4h／12h 於 8 GB 之可行性與耗時；⑤公開域 D 加倍之終止與最壞成本（稀疏欄使其退到資料起點）；⑥無起始日平穩化開啟時，校準列遮罩對 replace 模式與衍生欄之套用點；⑦`resolve_output_window` 恆預熱後，`run_ic_first`（v29 自行解析輸出窗）之行為是否隨之改變而與 Task 2.3 ⑫ 之驗收衝突；⑧倍數表對無參數遞迴指標（MAMA、HT_*、SAREXT、KLINGER）之量測方式是否可行（`_resolve_indicator_max_period` 回 1）。

## 必答（成對）
1. **(1a)** v32 是否忠實落實 R1–R7（逐條）？**(1b)** 逐條條文出處或偏離之處。
2. **(2a)** v32 有無新缺陷？**(2b)** 可重現反例（真實 kline 切片之輸入或操作序列）。
3. **(3a)** 兩條 assumed 各判成立或不成立？**(3b)** 碼證（附 `CODE-ANCHOR`）。
4. **(4a)** 「我沒查」①–⑧ 各有無命中？**(4b)** 碼證。
5. **(5a)** 「L1 遮罩＋NaN 傳遞」與「逐欄血緣相加」何者對本專案正確且可維護？**(5b)** 以一個反例或碼證支持（非偏好）。
6. **(6a)** §G ⑦ 雙起點收斂對證是否可證偽（三個 mutant 是否必紅）且判準與 M 合理？**(6b)** 反例或實跑數字。
7. **(7a)** 本版可否定案（`VERDICT: proceed`）？**(7b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 使用者定死「任何每次都會跑的檢查，單次必須秒級」；嚴禁新增分鐘／小時級之生成期檢查（驗收測試不在此限）。
2. 威脅模型＝**意外漂移**；每條 P0／P1 須附可重現之輸入或操作序列。
3. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由。
4. 研究設計不得寫死 24h／UTC／加密貨幣特有假設（使用者：之後要建台股、美股、期貨）。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api scripts tests docs templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
