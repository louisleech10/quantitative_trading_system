# GAP-3 事件型 consult R2：逐項審《白話說明/GAP-3事件型討論.md》（使用者意圖已定版）＋ K1–K10 技術定案

brief-kind: consult

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R2-P<0-3>-<NN>`。**四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`）。**
本輪輪次=R2。

## ⚠️ 前置說明
- **read-only**：禁改碼、禁寫測試、禁寫 SPEC；只產你自己的 consult 報告檔。
- 本輪**審查標的＝`白話說明/GAP-3事件型討論.md`**（sha256 前 12 碼 `685405d0daf9`，第 6 版）。它是**使用者以白話寫定的意圖＋主委判斷**；主委已與使用者五輪對談把問題訂清楚。你的工作＝**逐項**對該檔的編號項目表態並給技術建議，**不是**重寫一份自己的設計。
- **R1 已做過一輪**（`handoffs/reconcile/20260819-gap3-x-consult-r1/synth.md`；codex＋grok＋主委；composer 因 Cursor `resource_exhausted` 缺席）。R1 **整輪預設 C 情境（收盤確認後進場）**；使用者隨後揭露主要設想是 **A／B（t₀ open 決策、事件在未來）**，故 R1 之反例／決策時點結論須依本輪前提重議。R1 仍成立者（新匯入契約、六時間欄收據、毫秒單位、每標的時間切、兩種統計分開、分批）不必重證，引用即可。
- **不受理重議（使用者裁定，U 系列）**：討論檔 §7 U1–U11 全部為使用者裁決；攻它們＝浪費；若你認為某條 U 在技術上**不可行或會產生錯誤結論**，以 P0 finding 具名提出並附碼證／文獻，主委會白話轉達使用者，但**本輪不改**。
- 證據要求：每條結論附 file:line、命令與輸出、或文獻；無證據標 `UNVERIFIED`。

## 審查標的的編號系統（討論檔 §7 開頭有定義；你的「逐項對應表」必須用這些 ID）
- `U1`–`U11`：使用者已定（不攻；只檢「技術上能不能做到」）。`U2-1`–`U2-8`：討論檔 §2 八點（使用者陳述）。
- `S3.1`–`S3.11`：討論檔 §3 各小節（主委的陷阱與做法）。
- `T1`–`T10`：§5 十類事件型。
- `P0`–`P10`：§6 流程十一步；`G1`–`G6`：§6 末「完整版事件產生器」六點。
- `J1`–`J10`：§7 主委判斷（請**逐條攻**）。
- `K1`–`K10`：§7 委員會定之技術題（請**逐條給出你的定案提案**＋理由＋證據）。

## 本 brief 前提（逐條標；assumed 優先攻）
fact-verified: 使用者裁決 U1–U11 如討論檔 §7（來源＝2026-08-19 五輪對談；主委逐字轉錄）。
fact-verified: 現雛形 `/search`（`api/routes/two_stage_search.py`、`api/services/search_task_service.py`、`momentum/DataExtraction/case_search_engine.py:1193-1260` `_add_calculated_columns`）篩選條件**只准 `price_change`**（`api/models/requests.py:50` `allowed_filtering_params = {'price_change'}`）；進階條件含 `future_*_max_drawdown` 等未來欄（`case_search_engine.py:336,651-658`）；反例＝正例 ± `separation_days` 未觸發點（`search_task_service.py:788-820`）。
fact-verified: 現雛形 `/data-preparation`：CSV 必填 `symbol,timestamp,Positive_case`（`api/services/case_import_service.py:36`），批次抓 K 線 `BatchDownloadRequest(lookback_bars, forward_bars, warmup_bars, timeframe[])`（`api/models/case_models.py:114-135`；`api/services/batch_download_service.py:189-260`）。
fact-verified: IC 主線 API 已接受 `event_timestamps`／`event_query`（`api/models/ic_models.py:150-154`）；stage3 `_stage3_event_filter`（`momentum/Analysis/ic_filter_orchestrator.py:2776-2962`）；R5 A′ fallback 保留 timestamps（`:1142-1152`）。前端 `icAnalysisStore.ts` 只有 `event_filtering` 開關（`:78,106,134,336`），無時間戳輸入入口（Claude grep 2026-08-19）。
fact-verified: ML 引擎兩個皆在：`momentum/Analysis/lightgbm_analyzer.py`、`xgboost_analyzer.py`；`api/services/xgboost_batch_service.py:707-713` `engine∈{xgboost,lightgbm}`。
fact-verified: Feature Factory 有 slope／diff／rolling 聚合類特徵（`momentum/FeatureEngineering/operators/rolling_aggregator.py`、`feature_factory.py` grep `slope`=11、`_diff`=8 命中）；「bars since cross」「連續 N 根」類未見（Claude grep，**請複核**）。
fact-verified: 案例→特徵對齊現況 `xgboost_batch_service.py:618`（精確相等）、`:621`／`:651`（靜默跳過）、`:641`（同根列）——R1 CODEX-R1-P0-01／GROK-R1-P0-01 已證。
assumed: 使用者 A／B 情境之樣本選取（依 t₀ 那根結果挑）屬 case-control，合法，配套＝全樣本（全部 K 線）驗證（S3.1／J1）← 請攻：統計上是否成立、全樣本驗證之最小輸出（K8）、學習樣本基率與全樣本基率之差如何揭露。
assumed: A／B 之決策時點 t₀ open ＝ 前一根 1h／4h bar 之 close，可直接以 IC 主線「前一根時間戳＋1h 根數 horizon」表達（S3.9-1）← 請攻：TF 邊界對齊（12h open 對 1h／4h 邊界）、label 起算價（open 進場）與 IC 主線 label（close-to-close）之差異如何處理。
assumed: 三種反例（a 同觸發未續／b 震盪／c 下跌）混標 0 於 GBDT 可行但須按種類分報；IC（連續 label）不受種類影響但受抽樣影響（S3.5／J4）← 請攻。
assumed: 連續觸發：C 簇首、A／B 全留降權（唯一性權重），兩種都跑（S3.7）← 請攻並**給預設**（K3，使用者明說交委員）。
assumed: 跨標的合併（pooled）為 GAP-3 必要且可做最小版（S3.8／J6）← 請攻：最小版定義、同時刻簇處理、與 registry #4 的邊界。
assumed: 完整版事件產生器 G1–G6 可由 `/search` 升級＋與 `event_filter` query 模式共用底層條件引擎（J10／K9）← 請攻：條件引擎該落哪（`momentum/` 純函式 vs API）、PIT 守衛如何套在「條件可用任何特徵＋未來欄」的引擎上（觸發條件用未來欄＝依結果挑樣本，合法；但特徵欄不得越過決策時點）。
assumed: 十類事件型（T1–T10）第一版＝產生器做 T1–T3（＋T10 組合），T5／T7 靠匯入，T8／T9 契約留欄位，T4／T6 等資料源（§5 末）← 請攻：欄位如何表達 T8「參照標的」、T9「模型訊號當事件」（meta-labeling）、T10「區間型」。

## 必答（兩部分；都要）
### A. 逐項對應表（**必備**；主委要把它轉成白話給使用者看）
用**一張表**覆蓋下列全部 ID，每列：`ID | 同意／部分同意／不同意／不適用 | 一句理由 | 建議（若有） | 證據`：
`U2-1..U2-8`、`S3.1..S3.11`、`T1..T10`、`P0..P10`、`G1..G6`、`J1..J10`。
- 「不同意」或「部分同意」者**必須**另開 canonical finding 寫完整論證。
- U 系列只填「技術可行／有風險」，不填同不同意。

### B. K1–K10 技術定案提案（每題：提案＋理由＋證據＋可證偽驗收）
- **K1** 匯入契約欄位（完整清單；必填／選填；枚舉值；單位 ms；六時間點收據欄；方向；情境 `decision_time_rule`；反例種類；答案窗；規則摘要＝`/search` 條件快照＋digest；`control_kind`；T8 參照標的、T9 來源模型、T10 區間 start/end 之欄位形狀）。
- **K2** 對齊收據格式；A／B「t₀ open ⇒ 前一根已收盤 bar」之自動換算；多 TF（12h t₀ 對 1h／4h）邊界規則；失敗清單枚舉。
- **K3** 連續觸發預設（C／A-B 各自）、簇間隔 G 預設、降權算法（AFML 唯一性或替代）、報告欄位；「兩種都跑」是否必要。
- **K4** 切分（per-symbol 時間切＋purge/embargo ≥ 答案窗）、pooled 統計最小版、同時刻跨標的簇處理、與 registry #4 邊界。
- **K5** 三張表：(i) 事件後報酬表（多 horizon；均值／中位／勝率／n／CI）(ii) 正反例辨別（AUC／PR-AUC／Mann-Whitney；按反例種類；兩段式各一）(iii) 條件 IC（複用 stage3/4/5；label 為連續 `label_value`）——各自計算方式、揭露欄、與既有 `capability_status`／reason 枚舉之關係。
- **K6** 防運氣：label 置亂 oracle、PIT 後移必 raise、DSR/PBO 接點（規則→return series→ledger）；哪些 B1 就要。
- **K7** 變化類特徵要補哪些（具名清單：bars-since-cross、連續 N 根、窗內 argmax/argmin、窗內 max ratio…）；落在 Feature Factory 哪個 operator；與 IC 主線共用函式清單（file:line）。
- **K8** 全部 K 線驗證輸出（使用者：「交委員、能一次建完整最好」）：精確率／召回／PR 曲線／lift／訊號頻率／簡單持有報酬（open 進、答案窗末 close 出）／按 symbol／按時間分段穩定性／還有什麼；**哪些碰回測層（倉位、手續費、複利、資金曲線）不該在 GAP-3 做**；與序列型「全部 K 線」IC 並排的呈現。
- **K9** 完整版事件產生器 G1–G6 技術做法：條件引擎落點（建議 `momentum/` 純函式，API 包殼）、條件語法（沿 `event_filter` 的 `df.eval` 安全子集？擴充？）、多組條件→多標籤、PIT 守衛（特徵欄 ≤ 決策時點；結果欄允許）、去重在產生期、合規事件檔輸出、與 `/search` 既有 `SearchConfiguration`／`_add_calculated_columns` 的關係（升級不翻掉＝U7）；十類 T1–T10 各自在產生器／契約的落點。
- **K10** 分批：給出你的 B1–Bn 切法（每批單獨上線價值、依賴）；第一批最小可交付。

## Time-box 與範圍紀律
- 優先序＝A 逐項表 ＞ K1 ＞ K8 ＞ K9 ＞ K3 ＞ K5 ＞ K2 ＞ K4 ＞ K6 ＞ K7 ＞ K10。查不完的具名列「未查」，不當阻塞。
- **不受理範圍**：治理流程；前端樣式；ML 超參與模型選型（U8）；金融 event study（CAR/AAR）方法論；外部資料源接入（T4／T6 登記即可）；回測引擎（成熟度地圖：不完整層）；long-short 組合建構（U1 列殘留）；「應該先做別的票」。
- 語言：技術精確（非白話）；主委負責白話轉譯。

## 產出
canonical 四欄 findings（不同意／部分同意／P0 風險各一條）＋ **A 逐項對應表**（單一表、覆蓋全部 ID）＋ **B K1–K10 提案** ＋ Verdict（可進 SPEC／BLOCKING／scope）。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
