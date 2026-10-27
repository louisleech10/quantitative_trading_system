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

## 使用者裁定（2026-10-12，插入一步）
- 起因（新碼證）：TESTREG Task 2.4 之 V-6 慢因 cProfile（收據 `handoffs/run_receipts/testreg-v6-profile.json`）顯示公開域預熱探測之縮尾佔 85%；第 2 批審碼 r1 兩家同判探測縮尾門檻（`momentum/FeatureEngineering/feature_factory.py:2686–2695` 只看 `winsorization.enabled`）與公開輸出（`:3863` 看 `preprocessing.enabled`）不一致屬 FF 正確性缺陷、須現在另開票（`handoffs/reconcile/20261010-testreg-b2-review-r1/synth.md`；TESTREG SPEC §N R9）。依賴：TESTREG 第 3 批 Task 3.1／3.2 逐檔判定並實跑 FF 測試（含 `test_failopen_correctness.py` 之 V-6，前處理關閉、現約 8 小時），其行為與耗時取決於本修正。
- 裁定（選項逐字）：「TESTREG 第 2 批收批後、第 3 批前（推薦）」——新增第 5a-1 步 PROBEWINSOR。

## 使用者裁定（2026-10-23，插入一步）
- 起因（新碼證）：NUMVIEW Task 1.1 正式量測（收據 `handoffs/run_receipts/20261023-numview-postic-branchdiff.json`，提交 659234a5；收據審查 b2 r4–r5 三家收斂）——特徵生成之 L6.5 registry 快速路徑（`numba_fast`）①以 float32 計 zscore（`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:2566`、`momentum/FeatureEngineering/preprocessing/_numba_transforms.py:433`、`:469-485`），對未先排名之價格級欄相消失真（例參照 2.72、該路徑 15.80）；②zscore 之最少有效值數＝`_rolling_min_periods(zscore_window)`（窗 100 ⇒ 25），不足即填 0，與 pandas／Polars 臂及參考定義（2 個）不同。主委讀碼：生產預設先排名再標準化（`RankTransformConfig.enabled`＝True），①於預設下不發生；讀 processed 者為特徵工廠報告匯出、統計、相關性、VIF（`api/services/feature_factory_service.py` `_load_task_features`）；IC-first 讀 raw 不受影響（影響範圍來自讀碼，未以正式生成實證）。
- 裁定（選項逐字）：「現在就開票修」（選項說明：「NUMVIEW 暫停，先把加速路徑改成 float64、統一「至少幾個值」的規則」）——曾新增第 8a 步 L65FASTZ。
- 🔴 **同日更正與改裁定**：上述影響說明有誤（主委未查證即稱 processed 經此路徑）。查碼：該快速路徑於生產只用於 raw 寫出（`momentum/FeatureEngineering/feature_storage.py:1103`），且 raw 之 L6.5 設定關閉排名、標準化、gaussian（`momentum/FeatureEngineering/feature_factory.py:3155-3157`）⇒ ①②於現行生產流程無觸及；processed 由 IC-first 選欄後之 `transform_selected` 產生（`feature_factory.py:2985-3000`），不經此路徑。實際暴露只一處：縮尾選 sigma 法（前端可選，`frontend/src/components/feature-factory/PreprocessingPanel.tsx:308`；預設 quantile，`feature_config.py:169`）時，界線之均值／標準差以 float32 經 bottleneck 計（`_numba_transforms.py:438`、`:126-133`），真實價格級欄實測標準差 1.33（float64 為 7.73），會寫進 raw。使用者重新選擇（選項逐字）：「併入第 9 步、NUMVIEW 繼續（Recommended）」——取消第 8a 步；快速路徑均值／標準差改高精度（含 sigma 縮尾）與 zscore 最少有效值數規則併入第 9 步「縮尾重複」；NUMVIEW 照常續做。

## 使用者裁定（2026-10-24，第 9 步改寫）
- 起因（新碼證）：NUMVIEW Task 1.2／1.3 正式量測（收據 `handoffs/run_receipts/20261024-numview-precision-chain.json`、`20261024-numview-l2-arm-matrix.json`）——同一計算有多套實作並存：L2 於預設 Polars 路徑先以 `compute_all_polars` 算一次供 L3–L6，有 registry 時又以 pandas `compute_category` 逐類別重算存檔（`momentum/FeatureEngineering/feature_factory.py:1968-1987`），多週期格兩份差 3969919 格、全特徵格 43394 格；全特徵格 L2 預設路徑 70.3 秒、只走 pandas 45.2 秒（各兩次呼叫實測）；processed 存法有無壓縮 float32、codec 升級之無損 BSS、依欄名推斷之有損 int16 三種。
- 裁定（使用者逐字）：「是不是該普查特徵生產層的計算是不是最平衡解，確保特徵層程式和計算只有一套最平衡解的算法？因為之前先OOM，然後計算太久然後檔案又太大，搞了很久，程式碼可能很亂。」；排序「可以照建議排，但我印象小數據量和大數據量的測試可能不是線性，無法用推測的」。
- 落實：第 8 步 NUMVIEW 只收 post-IC 範圍（IC 頁與 IC-first 皆改 pandas〔使用者逐字「IC頁與IC-first都改pandas」〕、pandas 三臂依大規模實測選一並刪其餘）；L2 兩套、processed 存法、多週期 dtype 於 NUMVIEW 只具名登記；第 9 步改為「特徵生產層普查」並吸收原「縮尾重複」全部內容。任何擇一以實際大規模資料實測（大欄數、全特徵格），不以小樣本外推。

## 委員諮詢依新碼證之註記（2026-10-13，使用者離線委派共識決）
- 新碼證：①FRAMEPATH 處置驗證器檢查②（`tests/feature_engineering/test_framepath_disposition.py` 之 `check_2`）以凍結提交比對其治理檔之位元組、不排除他票提交，TESTREG 第 3 批範圍 149 檔中 52 檔屬之；②FRAMEPATH b1（`5584102d`）造成之兩支紅未被其受影響測試閘選入（一支以不變性信封略過、一支未選入），推翻 TESTREG 諮詢 r2 方案甲之前提。收斂檔 `handoffs/reconcile/20261010-testreg-x-consult-r3/synth.md`（三家一致）。
- 註記（不改全序）：第 5 步 FRAMEPATH 之「b2 前 TODO 修訂」（檢查②可辨識本票改動、受影響測試閘具名選入來源並以 b1 錨點重放驗證、兩支 b1 造成之紅之修正）須先於第 5a 步 TESTREG 對上述 52 個治理檔之實體改寫子批；TESTREG 之分類（Task 3.1）、非治理檔子批與第 4 批不受此限。

## 全序
| 序 | 項目（大小） | 內容 | 硬依賴 |
|---|---|---|---|
| 1 | FKPERF Task 4.5（小，ops） | 首個不改檔空檔背景跑全套治理測試；跑時不派委員、不改檔 | 無 |
| 2 | PRE-RED（中） | 9 支既有紅逐支歸因（L1 五支、resume 二支、走 frame 之 `test_failopen_producer`／`test_failopen_manifest`、API alias 一支分開）＋FF 測試紅名單基線（名稱集合） | 無 |
| 3 | RATIOUNSAFE（小） | `_is_ratio_unsafe_column` 對落盤帶週期欄名失效（`ohlc_12h_pattern_*` 之第二段為 `12h`；真實 manifest 43／43 漏判）⇒ 改讀結構化類別，IC 頁與 L6.5 共用；真實帶週期欄名測試 | 2 |
| 4 | ICFIRSTALIGN 乙（大） | IC-first 建／復用 CGSA registry、L6.5 pre-IC 只縮尾／平穩化、raw 只由 registry 串流寫出（不依賴空 frame 分支）、L6.5 失敗語意明定並配 mutation；raw 讀回／選欄讀回／processed（`write_processed` 傳 row_index）三處時間軸、sidecar 必填、禁位置對齊；不可變 run context＋選窗介面；FU-2 全 NaN 守衛；MEM-RSS 對照量測（證明漏擋才改閘）；IC-first 之 post-IC 鎖定正式臂（IC 頁第三步依使用者 2026-10-21 方向裁定於第 8 步 NUMVIEW 一併鎖定；2026-10-24 改裁 IC 頁與 IC-first 皆改 pandas，見上節）；label h 留 GLOBALH 接口；IC-first 測試遷離 `FFACT_USE_CGSA=0` | 2、3 |
| 5 | FRAMEPATH（大） | 刪環境變數分派、legacy 多週期、frame 週期標記器、frame L7 落盤、舊特徵 h5 讀取（不含 IC 服務內部 h5、`kline_cache.h5`）；遷移／刪 frame 測試與腳本 | 4 |
| 5a | TESTREG（大；2026-10-09 使用者裁定插入，於 FRAMEPATH b1 收尾後、b2 前） | 測試清冊自動維護：記錄器（耗時／結果／執行時間）、產出端登記檢查、自動過時標記、受影響測試挑選查清冊；首次分類由委員逐檔判斷保留／改寫／淘汰（淘汰須證覆蓋等價） | 5（b1）；FRAMEPATH 治理檔之改寫子批另依 5 之 b2 前 TODO 修訂（見 2026-10-13 註記） |
| 5a-1 | PROBEWINSOR（大；2026-10-12 使用者裁定插入，於 TESTREG b2 收批後、b3 前） | 公開域預熱探測之縮尾門檻與公開輸出一致（前處理關閉時探測不縮尾）；前處理開／關 × 縮尾開之對照驗收：`warmup_late_columns.probe_late`、加倍次數與深度、公開輸出首個有限值；真實 kline | 5a（b2） |
| 6 | FF-NAME（大） | Task 0＝SPEC 重寫（刪 layer1_only、ADF 白名單、frame 世代閘）；造名全面改三段式（衍生層、單指標層、`ms_`／`tr_`／`ent_`、L4 lag）、週期標記器統一、單一名稱解析器、前後端解析、命名世代鹽、刪 `adf_safe_skip` 死碼；failopen 基準於此重凍一次 | 5 |
| 7 | PRE-PROV＝FFDSTAR 改寫（中） | run manifest 寫逐欄平穩化決策、d*、各步驟實際執行狀態（含縮尾、成功亦寫）、失敗群組、轉換臂別；IC 讀取保留 manifest、ingest cache 依身分鍵失效 | 6 |
| 8 | NUMVIEW（中～大） | post-IC 正式臂政策（統一或具名保留）＋各分支 zscore 核心研究（ICPOSTLEAK §N）＋來源→計算→float32→實際 codec→讀回之誤差與比較翻轉量測（不重議 2026-09-29 dtype 裁定）＋臂／設定／算法 fingerprint 入不可變 run／view 身分；若改正式核心，實修與兩路 oracle 於此步完成 | 7 |
| 9 | 特徵生產層普查（大；2026-10-24 改寫，吸收原「縮尾重複」） | 盤點 L1–L7、L6.5 預處理、多週期、memmap／spill、存檔與 codec 等每一種計算之並存實作；凡有兩套以上者以實際大規模資料（大欄數、全特徵格）實測精度／速度／記憶體／檔案大小後只留一套、其餘刪除；改特徵值或輸出檔者先報使用者。必含：L2 只算一次（下游與存檔同一份；NUMVIEW Task 1.3 收據）、processed 存法收斂（NUMVIEW Task 1.2 實測：全部無損 BSS 誤差 0、較預設小 23%）、多週期層出口 dtype；原「縮尾重複」：依逐欄實際證據定唯一責任端、IC 端開關接後端、算法檢驗、L6.5 registry 快速路徑之滾動均值／標準差改高精度（含 sigma 縮尾界線；落盤 dtype 照 2026-09-29 裁定）、zscore 最少有效值數與其他臂及參考定義一致（改值之實際差距先報使用者） | 7、8 |
| 9a | NOCAP（大；2026-10-27 使用者裁定插入；同日使用者「那剛才所以測試相關都要對齊軟體和量化業界，不先做嗎？」⇒ 執行序：本步 Phase 0（含 Task 0.3b 成長曲線閘、0.4 四項平衡機制）→ 9a-1 TESTSEL → 9b ICPERF → 回第 9 步 FFPROD 其餘量測 → 本步其餘 Phase） | 全專案移除依牆鐘停止／縮減運算之機制（盤點約 40 處）：共用監看不因時間終止、卡死＝無 log 亦無 CPU 進度、終止前留現場判原因、程式卡住不自動重跑；pytest 閘門、等 IC 腳本、驗證腳本、委員 CLI 等候改進度判定；統計檢定次數固定（負對照不依時間縮減）；長運算服務改背景工作＋進度；Optuna 時間預算改選填；登記檔＋掃描測試防回退；重型跑必經監看之產出端閘（`docs/NOCAP_SPEC.md`） | 無 |
| 9a-1 | TESTSEL（大；2026-10-26 使用者：「涵蓋整個專案的未來的每一項目和每一票」；2026-10-27 排於 NOCAP Phase 0 後） | 全專案測試選取：依賴自上次通過後有變才跑（pytest-testmon＋外掛補 numba／資料檔／子程序／收集期／環境）、batch／close 分層、收據與提交檢查（`docs/TEST_SELECTION.md`；testsel 分支）。審碼 r3 → 全量建依賴紀錄（不與其他重型跑並行）→ 抽驗 → 合回 main | 9a Phase 0 |
| 9b | ICPERF（大；2026-10-27 使用者指示：「換大機器跟整個計算要最優化是不同事吧」「你這樣一欄一欄，時間不也就超久？」） | IC 計算最優化，不延至換機：第 5 段統計驗證逐欄 Python 迴圈（實測每欄約 0.8 秒、線性；20.9 萬欄約 46 小時、43 萬欄約 96 小時；九成以上在單調性與換手率之逐欄 PIT 擴張分位標記）改整批矩陣計算；IC 前處理先篩欄再處理（只選數欄亦全欄縮尾約 16 分鐘）；長階段進度回報；數值與改前逐位元相同、三規模實測加速；併入 RM-GAP-6（43 萬欄規模防護）。FFPROD 第 3 批之 IC 量測排於本票之後 | 9a Phase 0、9a-1 |
| 10 | GLOBALH 前置包（中～大） | 因子擇時夏普 √h、深度報酬時鐘與年化（不寫死 365×24）、ICIR 重疊窗查證、有效 N helper、horizon 子字串選欄修正（`ic_filter_orchestrator.py` `str(default_horizon) in name`）、IC 結果列結構一次定（模式／k／h／切分／選拔角色）＋倖存者契約一次遷移、研究試驗帳、Spearman 理由文件 | 8 |
| 11 | ICPATH（大） | 兩路盤點與區分、平穩化標記排除／警告、多標的同名一致、全域樣本數警示、邊際 IC 事件型驗收 | 9、10 |
| 12 | GLOBALH（大） | 每 h 完整跑、主線 h 指定、purge 取所選 h 最大、列標 h／k 可篩、IC 頁報酬量法 h 預覽 | 11 |
| 13 | SPLITUNIFY R-4 接線（中） | 事件 XGBoost 橋接 API／UI＋SU-RESID-9A-UI | 11 |
| 14 | FFSTORE（大） | 依研究 r1 與第 8 步契約：身分鍵拆 algorithm_id／snapshot、校準與死欄結果隨版本記錄、接續三類（可存狀態／回溯收斂／路徑相依）、交易日曆、下游讀取矩陣、FF-STAT §N 純窗口型分類、N 約一年實測；等值驗收釘同一 snapshot、逐項定義非數值欄，IC 結果經新讀取介面前後逐位元組相同 | 6–9 |
| 15 | EVENTSCAN（大） | 依新格式產 manifest；以新 run 重選 reference 一次；補試驗帳（dataset_key 不綁 config_hash） | 6、11、14 |
| 16 | PRE-DL（小，隨時）／FULLSCALE ④⑤（換機後） | 下載 BTCUSDT 1h 長歷史；完整截斷 MR 於 14 後、≥32GB 機器 | 14 |
| 17 | GAP-3 UAT（最後） | 含改過 k／h 之事件批與兩路 | 全部 |
| B | PRE-MARKET-DATA（具名 blocked） | 非加密市場資料來源與取得、adapter.market、日曆／換月 lineage、warmup 分市場量測；未到位前各票跨市場驗收列 blocked-by 資料 | 使用者決定資料來源 |
