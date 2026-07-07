# 第二刀主體 SPEC adversarial review — Claude 自產獨立腿

> 依「Claude 自產一版」鐵律,實作者/編排者不自我認證;本腿同須委員審+戳記(memory「Claude 自身不享特權」)。日期 2026-07-07。我刻意挑自己寫的 SPEC 的洞。

## BLOCKING

### B-1 F3 per-symbol split vs cross_sectional「同時間跨幣比較」語義衝突
`analyze_cross_sectional` 的本質=**同一 timestamp 把各 symbol 擺一起 rank**。SPEC Task 4.1 用 `split_per_symbol`(逐 symbol 各自時間切),但若三幣時間軸不齊(起訖/長度不同),同一 test_size 比例會讓**每幣的 train/test 時間邊界不同** → 某個 timestamp 可能對 BTC 屬 test、對 ETH 屬 train。後果二選一都壞:
- 若「只取每幣自己的 test 列再重組」→ 同一 ts 的橫截面**只剩部分 symbol**,rank corr 樣本數縮水甚至 <2 被跳過,IC 統計被污染/偏差。
- 若混入 → train/test 在橫截面層級不乾淨。
**建議**:cross_sectional 應改用**單一全域時間邊界**(train=T 之前、test=T 之後,對所有 symbol 同一個 T),purge/embargo 圍 T;仍可用 contracts 契約但 splitter 須產生「全域同步」邊界而非 per-symbol 獨立比例。SPEC 現行 wording 未界定此,實作端會照字面做出 per-symbol 獨立切 = 錯。**須在 freeze 前釐清**。

### B-2 purge/embargo 對「多 symbol 同 ts」的 rows 語義未定義
單幣 `_build_holdout_split_plan` 的 purge=rows(bars)。cross_sectional 若走全域時間邊界,purge 應是**時間 gap(horizon bars)**,對所有 symbol 移除 [T−purge, T+embargo] 區間的列。SPEC 寫 `purge_gap=max(purge,horizon)` 但未言明是 per-symbol rows 還是全域 time。`split_per_symbol` 內部是 per-symbol local ordinals 的 rows purge——若時間軸不齊,per-symbol rows purge ≠ 全域 time purge,邊界仍可能洩漏。**須明確定義並在測試中以「跨幣同 ts」反例驗**。

## MAJOR

### M-1 F4 floor=0.5 與真實覆蓋率量級不符,可能既擋不到真問題又誤擋暖機
偵察實測:正常 forward return 覆蓋率 ≈ (n−1)/n ≈ 0.9994(僅末列 NaN)。覆蓋率會顯著下降只在 kline 相對 feature 軸有孔。**floor=0.5 太鬆**:F1 回歸(全 NaN=0.0)會擋到,但「一半 symbol 標籤壞掉」(覆蓋率 0.5~0.6)這種**部分回歸**會漏過。建議 floor 設更貼近量級(如 per-symbol 0.9)+ per-symbol 檢查(非全域平均,否則一幣全壞被其他幣稀釋)。**全域平均覆蓋率會掩蓋單幣全壞**——這正是 F1 類洩漏的變種。

### M-2 覆蓋守衛應 per-symbol 而非全域
承 M-1:若守衛只看 `working_df["_label"]` 全域 notna 比例,一個 symbol 完全對不上(該幣全 NaN)會被其餘正常幣稀釋到 >floor 而放行 → F1 同類 bug 靜默重演。**守衛須 per-symbol 計覆蓋率,任一幣過低即 raise**。SPEC/TODO Task 2.1 現行寫全域,須改 per-symbol。

## MINOR

### m-1 F1 ms/s 防呆閾值 1e12 是 magic number
偵察現況 ts≈1.7e9(秒)。閾值 1e12 可用但脆;更穩=從單一權威來源讀 timestamp 單位(feature sidecar 或 kline schema 已知單位),而非猜。列為 minor(現況秒、閾值不會誤判),但登記為「單位應有單一真相源」技術債。

### m-2 F3 定位:IC 是診斷統計非擬合模型,OOS 的價值是「選特徵誠實度」非「防 look-ahead」 VERIFY-EXEMPT:doc-example:cut2-specadv
forward return 本身無 look-ahead(已證)。full-sample IC 之所以要 OOS,是因下游用 IC 選特徵→同資料評估=selection bias。SPEC §RISK 掛 (d) 沒錯,但 wording 宜精確為「in-sample selection bias」而非泛稱 look-ahead,避免實作端誤把 F3 當防未來洩漏而過度設計。

## 無異議確認
- F1 根因/修法:實跑 receipt 三段閉合(0/5088→5085/5088、forward、per-symbol 各異),同意。
- F2 labels_path 廣播:讀碼確認屬實,fail-closed raise 方向正確。
- consumer map 已納入第一刀漏的 `_append_cross_sectional_labels`,SCAR 入帳正確。

STATUS: DONE — 2 BLOCKING(B-1 全域 vs per-symbol split 語義、B-2 purge 語義)+ 2 MAJOR(覆蓋守衛須 per-symbol)須在 freeze 前收斂。
