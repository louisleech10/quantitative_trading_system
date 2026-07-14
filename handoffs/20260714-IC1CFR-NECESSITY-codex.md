# IC1CFR-NECESSITY — Codex 獨立評估（2026-07-14）
## 獨立論證（讀 Claude 意見前完成）
證據：`factor_return_analyzer.py:30-88` 先按共同 index 對 feature/forward return 對齊，卻把高、低分位各自 `reset_index(drop=True)` 後按列序相減；這不是同 timestamp/同 rebalance 的 long-short return。單 symbol 時每期只有一個 observation，更不可能用不同日期的 high/low observations 冒充同期雙腿；MultiIndex 時全域 qcut/序位配對也不等於每期橫截面投組。其 cumulative/risk metrics 因而沒有 canonical factor-portfolio 經濟意義。

證據：`label_generator.py:34-47` 的 binary/regression label 是純 forward close return（或 0 門檻），`model_task_service.py:144-149` 直接取既有 `label` 作 y；現役 GBDT 訓練路徑沒有成本、部位或 turnover。`net_ic_analyzer.py:279-292` 現只輸出 `cost_bps×平均 membership-change turnover` 的報酬空間 proxy，breakeven/profitable 明確 unavailable，這個 fail-closed 現況是正確的。

### ① 成本判決應在哪一層
IC 層只應回答 gross predictive evidence、穩定性、coverage，以及「可能昂貴」的 turnover/cost-drag proxy；不可把報酬成本減進 IC，也不可宣稱策略盈利。單因子 canonical factor portfolio（固定 rebalance clock、同期分腿/權重、可交易 lag、gross return 與同 timestamp turnover）屬 IC 與策略間的 portfolio-research 中間層；它可給 feature-level breakeven/成本後存活診斷，但必須標明不是最終策略。回測層以 ML 預測→訊號→權重→訂單→成交的實際路徑做唯一最終 net profitability/capacity 裁決。故答案不是三選一：粗篩在 IC、模型/投組選擇在中間層、最終判決在回測層，且權威逐層上升。

### ② ML 是否應 cost-aware；1c-FR 是否為前置
應該，但正確位置主要是 out-of-fold 模型選擇與 prediction-to-position policy：以 OOF 預測生成可交易權重，按相鄰權重計 turnover，再評 net utility；亦可調 decision threshold/no-trade band、持有期、position sizing。不可天真逐列做 `forward_return-cost`：逐列 label 不知道前一期預測/權重，成本是 path-dependent 且受組合淨額、交易時點、滑價影響；binary label 若有明確「每列必開平一筆」契約才可用成本門檻，現碼無此契約。對樹模型直接加 turnover penalty 也非一般可分解 sample loss，宜在 policy/model-selection 層處理。

因此 1c-FR 是「單因子成本後經濟診斷」與其 breakeven/profitable 欄位的硬前置，也是建 cost-aware ML baseline/驗證 plumbing 的高價值先導；但不是 gross-label GBDT 訓練或最終 ML 投組成本正確化的充分/絕對前置，因單因子換手不等於多因子非線性模型的預測換手。不能以完成 1c-FR 取代 OOF prediction portfolio 與 backtest，也不應用它硬刪掉模型可能低換手地使用的特徵。

### ③ parked 隱憂
- 人員/UI/API 可能把 `long_short_mean_return`、Sharpe、cumulative 當同期可交易投組結果；目前序位錯配會污染因子排序、方向、穩定性與風險認知。
- cost sensitivity 只有 drag 沒有 canonical gross series，容易被誤讀為「已做成本後驗證」；feature selection、成本預算與 breakeven 判斷會缺基準或另造不一致算法。
- ML bridge 若先上線，會把純 gross labels/metrics 當部署目標；模型比較、超參數、threshold/no-trade band、持有期可能偏向高換手 gross alpha。
- 後續 attribution、ensemble/feature pruning、agent 自動決策若讀到現有 factor-return payload，會把不可交易或錯配序列當真；多模組各自重建 return/turnover 亦會形成 rebalance/lag/權重/cost convention 漂移。
- 回測雖可最後抓出問題，已付出 ML 訓練與研究選擇成本，且 selection bias 不能靠最後一次 test/backtest 安全修復。
- 短期 parked 仍可接受的唯一條件：所有盈利欄 fail-closed、錯配 gross factor-return/risk payload 不作選擇或先禁用、ML cost-aware consumer 尚未啟用，且有明確重開 gate。

### ④ 獨立裁決
必要性：**高（P1 correctness enabler），非當下 B-strict closure blocker，也非所有 ML 訓練 blocker**。時機：可為 1d/1f 等局部語意債短暫 parked，但應在 IC→ML bridge、任何 cost-aware model selection/feature pruning、或重新啟用 breakeven/profitable 前完成；若目前 factor-return/risk metrics 已供人或 agent 決策，則不應等，需立即正確化或 fail-closed 禁用。
重開觸發器：(1) 任一人/UI/agent 消費 factor-return cumulative/risk/long-short；(2) breakeven/profitable 擬由 unavailable 轉值；(3) IC 存活特徵自動送 ML；(4) 以 net metric 調模型、threshold、holding period 或 pruning；(5) cross-symbol portfolio/attribution/ensemble 開工；(6) 任一模組另寫 gross-return×turnover 成本算法。最低完成定義須含 timestamp-preserving return/turnover series、明確 universe/方向/權重/rebalance/lag/cost convention、無 `reset_index` 序位配對、OOS/PIT 測試及與策略回測同契約對照。

## 與 Claude 意見對照（獨立段完成後才讀）
一致：最終成本盈利權威在回測；單因子淨報酬可能因缺組合內部軋單而誤殺因子；現有 drag proxy 可粗看；重開至少包含 ML cost-aware、因子組合與錯位修復。分歧一：Claude 將 cost-aware label/turnover penalty 視為 1c-FR「硬依賴」；我判為僅部分依賴——逐列扣成本通常錯，真正 ML 淨效用須由 OOF predictions→positions→turnover 計算，1c-FR 只是單因子 baseline。分歧二：Claude 建議 parked，但實碼顯示 consumer 已存在：`FactorReturnConfig.enabled=True`、deep runner 預設執行、`ic_reporter.py:581-588` 抽取 LS mean/Sharpe、前端 `page.tsx:800` 展示 C13；故「無消費者」前提不成立。這不是 Claude 文件帶來的新主張，而是讀後追加的 repo 驗證，並觸發我獨立段已定義的立即 gate。
時機修正：**完整 1c-FR 排近期下一個 correctness ticket，優先於讓 1d/1f 或 ML bridge 繼續消費這批投組型數字**；若排程不能立刻承擔大票，先另票 fail-closed 禁用/移除錯配的 LS cumulative/risk/return claims（不可把 containment 冒充 1c-FR 完成）。
RULING: 1c-FR 為 P1 高必要 correctness enabler，因預設 API/UI 消費者已存在而不應繼續無期限 parked；現在先 fail-close 錯配投組輸出並將完整 timestamp-aligned 1c-FR 排為近期下一票，ML 淨盈利與最終裁決仍須分別由 OOF prediction portfolio 與回測完成。
