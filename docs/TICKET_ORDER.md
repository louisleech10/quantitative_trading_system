# 全票細項排序（定案）

> 唯一權威排序。使用者 2026-10-01 裁定開諮詢（「將接下來每張票的細項都逐個討論研究訂出排序……不能中間又說要重來」）；主委＋三家三輪收斂（r1 二十五條、r2 七條、r3 零條，全數閉合），使用者 2026-10-02 拍板（逐字：「你跟委員確定就可以，不要我問一次，你又改口就好」）。
> 收斂檔（本機）：`handoffs/reconcile/20261002-ticketorder-x-consult-r{1,2,3}/synth.md`；主委獨立版 `handoffs/20261002-ticketorder-x-consult-r1-claude.md`。
> 🔴 改本表＝推翻定案：只准在有新碼證證明某步硬依賴指向其後之步時，經委員諮詢後改，並向使用者說明原因。各票之 SPEC／TODO 仍走完整管線；本表只定順序與範圍歸屬。

## 使用者裁定（2026-10-02）
- 死欄：判斷方法不變（依該次產出之整段資料）；FFSTORE 每個快照版本記下當次去留結果，接新資料即新版本。
- 開發階段所有資料可重新產生，FFSTORE 不需相容或遷移舊資料。
- EVENTSCAN 排第 15、一次做完。
- 非加密市場資料先不接：各票跨市場驗收列 blocked-by 資料、不宣稱完成；設計不得寫死加密貨幣假設。
- TESTSPEED「各運算路徑取代表之快速版」不做（與 2026-09-29「不挑代表、不接受專項專用」衝突）；已上線之「上次失敗者先跑」與量測器保留。
- 到該票時再問：深度分析夏普修法二擇一、獨立確認區間成本、縮尾責任與算法、PRE-PROV 輸出增量、failopen 基準重凍。

## 使用者裁定（2026-10-09，插入一步）
- 起因：FRAMEPATH b1 之機械導出「受影響測試」30 檔中，`test_failopen_correctness.py` 單檔 5 小時餘未跑完；全專案 642 個測試檔無清冊（用途、取代關係、耗時、最近結果皆無紀錄），自 2026-08-13 刪 CI 後量化測試無定期執行。使用者逐字：「如果不先做，後續開發是不是很可能又拿了不相關的測試，花了很多時間測試但沒意義?」「但建立了清冊後，沒固定維護的話不也沒意義」。
- 裁定（選項逐字）：「做；FRAMEPATH 第一批收尾後插入」——新增第 5a 步 TESTREG；FRAMEPATH b1 之 30 檔處置交委員共識（諮詢 r4）。
- 方向（主委提案、使用者選定）：清冊須自動維護——測試框架記錄器自動記耗時／結果／執行時間；新測試檔於產出端登記用途與所屬票；過時／耗時暴增／久未跑自動標「待複查」；受影響測試之挑選查清冊。人工只做首次分類與待複查項。測試「前提被後來的票改掉仍能通過」者機械只能間接察覺，列具名殘留。
- 使用者逐字（同日）：「對了，你跟委員要參考軟體業界是如何做的」——TESTREG 偵察須先研究業界做法（例：大型程式庫之受影響測試挑選〔test impact analysis〕、不穩定測試隔離、測試耗時與結果追蹤、測試用途／負責人標記、過時測試淘汰流程），主委與三家各出獨立版後取捨，並對照本專案規模（單人、8 GB 單機、無 CI）。
- 使用者逐字（同日）：「我完全不懂程式碼，所以要如何分類和存放和建議清冊以及決定去留等，你跟委員決定」——TESTREG 之分類標準、清冊存放與格式、逐檔去留由主委＋委員共識決；對使用者只報白話結論（淘汰多少、理由、各票省多少時間）與需取捨之方向。淘汰仍須證覆蓋等價。

## 全序
| 序 | 項目（大小） | 內容 | 硬依賴 |
|---|---|---|---|
| 1 | FKPERF Task 4.5（小，ops） | 首個不改檔空檔背景跑全套治理測試；跑時不派委員、不改檔 | 無 |
| 2 | PRE-RED（中） | 9 支既有紅逐支歸因（L1 五支、resume 二支、走 frame 之 `test_failopen_producer`／`test_failopen_manifest`、API alias 一支分開）＋FF 測試紅名單基線（名稱集合） | 無 |
| 3 | RATIOUNSAFE（小） | `_is_ratio_unsafe_column` 對落盤帶週期欄名失效（`ohlc_12h_pattern_*` 之第二段為 `12h`；真實 manifest 43／43 漏判）⇒ 改讀結構化類別，IC 頁與 L6.5 共用；真實帶週期欄名測試 | 2 |
| 4 | ICFIRSTALIGN 乙（大） | IC-first 建／復用 CGSA registry、L6.5 pre-IC 只縮尾／平穩化、raw 只由 registry 串流寫出（不依賴空 frame 分支）、L6.5 失敗語意明定並配 mutation；raw 讀回／選欄讀回／processed（`write_processed` 傳 row_index）三處時間軸、sidecar 必填、禁位置對齊；不可變 run context＋選窗介面；FU-2 全 NaN 守衛；MEM-RSS 對照量測（證明漏擋才改閘）；post-IC 鎖 Polars 正式臂；label h 留 GLOBALH 接口；IC-first 測試遷離 `FFACT_USE_CGSA=0` | 2、3 |
| 5 | FRAMEPATH（大） | 刪環境變數分派、legacy 多週期、frame 週期標記器、frame L7 落盤、舊特徵 h5 讀取（不含 IC 服務內部 h5、`kline_cache.h5`）；遷移／刪 frame 測試與腳本 | 4 |
| 5a | TESTREG（大；2026-10-09 使用者裁定插入，於 FRAMEPATH b1 收尾後、b2 前） | 測試清冊自動維護：記錄器（耗時／結果／執行時間）、產出端登記檢查、自動過時標記、受影響測試挑選查清冊；首次分類由委員逐檔判斷保留／改寫／淘汰（淘汰須證覆蓋等價） | 5（b1） |
| 6 | FF-NAME（大） | Task 0＝SPEC 重寫（刪 layer1_only、ADF 白名單、frame 世代閘）；造名全面改三段式（衍生層、單指標層、`ms_`／`tr_`／`ent_`、L4 lag）、週期標記器統一、單一名稱解析器、前後端解析、命名世代鹽、刪 `adf_safe_skip` 死碼；failopen 基準於此重凍一次 | 5 |
| 7 | PRE-PROV＝FFDSTAR 改寫（中） | run manifest 寫逐欄平穩化決策、d*、各步驟實際執行狀態（含縮尾、成功亦寫）、失敗群組、轉換臂別；IC 讀取保留 manifest、ingest cache 依身分鍵失效 | 6 |
| 8 | NUMVIEW（中～大） | post-IC 正式臂政策（統一或具名保留）＋各分支 zscore 核心研究（ICPOSTLEAK §N）＋來源→計算→float32→實際 codec→讀回之誤差與比較翻轉量測（不重議 2026-09-29 dtype 裁定）＋臂／設定／算法 fingerprint 入不可變 run／view 身分；若改正式核心，實修與兩路 oracle 於此步完成 | 7 |
| 9 | 縮尾重複（中～大） | 依逐欄實際證據定唯一責任端；IC 端開關接後端；算法檢驗 | 7、8 |
| 10 | GLOBALH 前置包（中～大） | 因子擇時夏普 √h、深度報酬時鐘與年化（不寫死 365×24）、ICIR 重疊窗查證、有效 N helper、horizon 子字串選欄修正（`ic_filter_orchestrator.py` `str(default_horizon) in name`）、IC 結果列結構一次定（模式／k／h／切分／選拔角色）＋倖存者契約一次遷移、研究試驗帳、Spearman 理由文件 | 8 |
| 11 | ICPATH（大） | 兩路盤點與區分、平穩化標記排除／警告、多標的同名一致、全域樣本數警示、邊際 IC 事件型驗收 | 9、10 |
| 12 | GLOBALH（大） | 每 h 完整跑、主線 h 指定、purge 取所選 h 最大、列標 h／k 可篩、IC 頁報酬量法 h 預覽 | 11 |
| 13 | SPLITUNIFY R-4 接線（中） | 事件 XGBoost 橋接 API／UI＋SU-RESID-9A-UI | 11 |
| 14 | FFSTORE（大） | 依研究 r1 與第 8 步契約：身分鍵拆 algorithm_id／snapshot、校準與死欄結果隨版本記錄、接續三類（可存狀態／回溯收斂／路徑相依）、交易日曆、下游讀取矩陣、FF-STAT §N 純窗口型分類、N 約一年實測；等值驗收釘同一 snapshot、逐項定義非數值欄，IC 結果經新讀取介面前後逐位元組相同 | 6–9 |
| 15 | EVENTSCAN（大） | 依新格式產 manifest；以新 run 重選 reference 一次；補試驗帳（dataset_key 不綁 config_hash） | 6、11、14 |
| 16 | PRE-DL（小，隨時）／FULLSCALE ④⑤（換機後） | 下載 BTCUSDT 1h 長歷史；完整截斷 MR 於 14 後、≥32GB 機器 | 14 |
| 17 | GAP-3 UAT（最後） | 含改過 k／h 之事件批與兩路 | 全部 |
| B | PRE-MARKET-DATA（具名 blocked） | 非加密市場資料來源與取得、adapter.market、日曆／換月 lineage、warmup 分市場量測；未到位前各票跨市場驗收列 blocked-by 資料 | 使用者決定資料來源 |
