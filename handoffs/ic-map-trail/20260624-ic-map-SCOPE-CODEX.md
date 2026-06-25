# SCOPE 提案 — Codex 家族

## 1. 分析類型清單

建議地圖按「研究問題」覆蓋，而不是只列 IC 名詞。

### A. 基礎預測力：這個因子有沒有用？
- **單標的時序 IC** `[現有]`：同一 symbol 內，因子今天的值能否預測未來報酬。
- **多標的 pooled/panel 時序 IC** `[完全缺][優先]`：把 100 symbols 的時間序列合併，回答「這個 pattern 是否普遍有效，而非只在單一幣有效」。
- **symbol 一致性 / 普適性分析** `[部分現有]`：每個 symbol 各算 IC，再看正負方向、勝率、離群 symbol。
- **橫截面 IC** `[現有]`：同一時間點，比較不同 symbols，回答「因子能不能排序誰未來表現較好」。

### B. 使用者主戰場：事件前 pattern
- **顯式事件清單 case-control 事件研究** `[完全缺][最高優先]`：吃 `event_id/symbol/timestamp/label=positive|negative`，比較正反事件前窗共通 pattern。
- **事件前窗 lead-lag IC / event-time IC** `[完全缺][最高優先]`：以事件時間 T 對齊，檢查 T-k 到 T-1 哪些因子最早出現訊號。
- **事件條件查詢 IC** `[現有但不足]`：現況 `event_query` 只是過濾資料，不等於顯式事件研究。
- **事件樣本平衡 / matching / leakage 檢查** `[完全缺][最高優先]`：正反案例需按 symbol、時間、波動、regime 配對，避免答案只是 regime 差異。
- **事件 OOS 驗證** `[完全缺][最高優先]`：事件 pattern 必須 train/test 或 walk-forward，不能在全部事件上挑因子。

### C. 穩健性：是不是偶然？
- **IC 顯著性 / t-stat / bootstrap** `[部分現有]`：IC 是否大到不像隨機噪音。
- **多重比較 / FDR 控制** `[需確認，應列入]`：430K 欄大量測試下，避免「總會有幾個看似顯著」。
- **block bootstrap / clustered SE** `[完全缺]`：處理時間序列自相關、同一 symbol 群聚。
- **stability by time / rolling IC** `[現有]`：IC 是否只在某段時間有效。
- **drift / decay of validity** `[部分現有]`：因子有效性是否隨時間失效。

### D. 形狀與經濟意義：訊號是不是可交易？
- **分位數報酬 / quantile return** `[現有]`：因子高低分組後，未來報酬是否有序。
- **單調性測試** `[現有]`：分位越高，報酬是否越高或越低。
- **IC 衰減 / 半衰期** `[現有但回報稱 grouped/decay 會崩]`：訊號在 1/2/3/5/… horizon 多快消失。
- **多空因子報酬 / long-short spread** `[現有]`：買高分、賣低分是否有穩定收益。
- **換手率 / 交易成本 / net IC** `[現有]`：扣掉換手成本後還值不值得用。
- **容量 / 流動性 / slippage 可行性** `[完全缺或未主線]`：100 symbols 上能不能實際下單，不只是統計好看。

### E. 條件化：在哪些市場狀態有效？
- **regime/grouped IC** `[現有但壞掉]`：牛熊、高低波、年份、季度、layer、category 下是否有效。
- **symbol group / sector / liquidity bucket IC** `[完全缺或部分缺]`：不同資產族群是否有不同效果。
- **event subtype IC** `[完全缺][優先]`：不同事件類型、正反案例、嚴重度分層下 pattern 是否一致。
- **time-of-day / day-of-week / session 條件 IC** `[可選但應列]`：加密或高頻場景常見時間結構。

### F. 因子互動與冗餘：是不是重複？
- **相關矩陣 / clustering / VIF** `[現有]`：因子是否只是同一訊號換名字。
- **正交化 / neutralized IC** `[現有但預設關]`：扣掉已知因子後還有沒有新增資訊。
- **共線性 / factor crowding / centrality** `[現有]`：哪些因子是擁擠核心，哪些提供獨立訊號。
- **factor exposure / beta/vol exposure** `[現有但預設關]`：訊號是不是其實只是在押方向、波動或其他暴露。

### G. 驗證與防洩漏：能不能信？
- **train/test split** `[主路徑缺][最高優先]`：主 IC path 必須只在 train 選因子，在 test 驗證。
- **walk-forward / rolling OOS** `[現有]`：用時間滾動方式測未來泛化。
- **purged / embargo CV** `[部分現有入口，需列入]`：事件或重疊 horizon 下避免 label overlap 洩漏。
- **adversarial validation** `[現有入口]`：train/test 分布是否不同到不可比。
- **label horizon / PIT 檢查** `[必列]`：所有 feature 必須只用事件/預測時點以前資料。

### H. 多因子與 ML：不是單因子時怎麼辦？
- **多因子組合 / ensemble selection** `[部分缺]`：把多個通過的因子組成穩健訊號。
- **非線性特徵重要性 / SHAP / permutation importance** `[部分現有]`：因子可能單獨 IC 低，但與其他因子交互後有用。
- **interaction / conditional importance** `[完全缺或弱]`：A 因子只在 B 條件下有效。
- **calibration / prediction quality** `[現有入口]`：模型分數是否能對應真實機率或報酬排序。
- **learning curve / sample size sufficiency** `[現有入口]`：資料量是否足夠支撐結論。

### I. 資料品質與工程尺度
- **feature quality diagnostics** `[現有]`：NaN、inf、coverage、常數欄、異常值。
- **warmup / lookback sufficiency** `[必列]`：技術指標前段不可用區不能污染分析。
- **schema / metadata lineage** `[部分現有]`：每個結果要知道 symbol、tf、config_hash、label_horizon、split。
- **430K 欄尺度策略** `[必列]`：streaming、分批、top-k early filter、稀疏結果、避免 full correlation matrix。
- **partial failure / resumability** `[部分現有]`：大批 symbols 中單一 symbol 失敗不能污染整批。

## 2. 每條目的內容 Schema

每種分析類型在地圖中建議固定寫這些欄位：

- **白話問題**：它回答什麼研究問題。
- **適用場景**：連續訊號、橫截面排序、事件 case-control、多因子、ML。
- **輸入形狀**：需要 `time × feature`、`time × symbol × feature`、還是 `event_id × pre_event_window × feature`。
- **核心輸出**：IC、ICIR、p-value、FDR、quantile spread、half-life、OOS degradation、feature ranking 等。
- **業界標準做法**：常見統計方法與最低驗證要求。
- **平台現況**：現有 / 部分現有 / 現有但壞掉 / 完全缺。
- **做對標準**：什麼結果才算可信，不只「跑得出圖」。
- **常見漏洞**：look-ahead、label overlap、selection bias、多重比較、cross-symbol contamination。
- **PIT / 洩漏注意**：feature timestamp、label horizon、event pre-window、purge/embargo 要求。
- **430K × 20K × 100 尺度做法**：streaming、chunking、approx/top-k、memory cap、可恢復設計。
- **對應現有模組**：如 `ic_engine`、`ic_filter_orchestrator`、deep analysis modules、frontend charts。
- **優先級**：P0/P1/P2。
- **驗收命令或可證偽檢查**：未來 SPEC 才展開，SCOPE 先列檢查類型。

## 3. 地圖組織方式

建議主排序按「研究者問題」而不是按程式模組：

1. **我有沒有訊號？**  
   時序 IC、pooled/panel IC、橫截面 IC、分位/單調性。

2. **這是不是我要找的事件前 pattern？**  
   case-control、event-time alignment、pre-event lead-lag、positive vs negative matching。

3. **它穩不穩、是不是假象？**  
   顯著性、FDR、rolling stability、regime/grouped、symbol consistency。

4. **它能不能交易？**  
   long-short、turnover、成本、capacity、半衰期。

5. **它是不是獨立資訊？**  
   correlation、orthogonalization、exposure、centrality、crowding。

6. **它能不能泛化到未來？**  
   train/test、walk-forward、purged CV、OOS、adversarial validation。

7. **它能不能進入 ML / 多因子系統？**  
   feature importance、interaction、多因子組合、calibration、learning curve。

8. **資料與工程可信度**  
   quality diagnostics、PIT lineage、scale strategy、partial failure。

這個順序對非量化使用者比較自然：先判斷「有沒有用」，再判斷「是不是我的事件問題」，最後才進到交易、ML、工程尺度。

## 4. 明確標記

**使用者主戰場必須優先補強**
- 顯式事件清單 case-control 事件研究。
- event-time / pre-event window 對齊。
- positive vs negative matching。
- 事件 train/test、walk-forward、purged/embargo。
- pooled/panel 時序 IC 與 symbol 一致性。
- 主 IC path 的 train/test 切分與 leakage gate。
- 430K 欄尺度下的事件前窗 streaming/top-k 設計。

**現有但壞掉或不足**
- grouped/regime IC：已存在，但使用者已知會崩。
- IC decay/half-life：已存在，但使用者已知會崩。
- event mode：目前偏 `event_query` 條件查詢，`event_timestamps` API 仍 warning 未支援，不是完整事件研究。
- cross-sectional IC：已有主路徑，但不是 pooled/panel 時序普適性，也需 OOS/leakage 補強。
- deep analysis：factor return、centrality、trend、rolling OOS、long-short、quality、net IC 等已有入口，但需在地圖中逐項驗證可信邊界。

**完全缺或應視為缺**
- 顯式事件表 schema：`event_id/symbol/timestamp/label/event_type/weight/split`。
- case-control matching 與負案例設計。
- event-time IC / lead-lag pre-window heatmap。
- pooled/panel longitudinal IC。
- FDR / 多重比較控制作為主流程 gate。
- purged/embargo CV 在事件主路徑的強制化。
- capacity/liquidity/slippage 可交易性分析。
- interaction / conditional importance 的研究地圖入口。
- 統一 PIT lineage 報告：每張圖都能追到 feature cutoff、label horizon、split。

HANDOFF_NOT_UPDATED: read-only 研究諮詢且目前 sandbox 為 read-only，未寫交接檔。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md；已檢查 ic_models 顯示 event_timestamps 尚未支援、ic_filter_orchestrator 顯示 cross_sectional/event_filter/decay/grouped/deep modules 存在；未假設完整實作品質。
TESTS_RUN: none，read-only scope 定義輪未跑測試。
FAILURES_SEEN: none。
SCOPE_CHANGES: none，未改檔。
NUMERIC_OR_SCHEMA_IMPACT: none，僅提出未來地圖 schema 建議。
STATUS: DONE