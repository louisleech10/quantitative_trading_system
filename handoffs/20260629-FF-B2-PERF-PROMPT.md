# 委員會:B2 比對效能設計定案(委員獨立腿)

使用者委派委員會定案後執行。讀 Claude 腿 `handoffs/20260629-FF-B2-PERF-CLAUDE.md`。

## 問題
B2 全鏈截斷 MR 比對全 220158 特徵 >40分跑不完(generate ~20分 + 比對 >20分)。FF 因果已三方簽核 PASS;這是**比對規模問題非正確性**。要讓單測可實際跑綠。

## ⚠️ 純設計推理,勿跑慢全鏈(會 timeout)
從 Claude 提案 + 讀測試碼判斷。

## 你的設計判斷
1. Claude 提「分層抽樣比對」(generate 全鏈,比對每 layer/operator 抽 K 欄):同意/修正?分組鍵怎麼定才覆蓋每型別?K 多少?
2. **抽樣會不會放走單欄洩漏**?(因果是層級算法性質,同層抽樣即代表;但加「mutation 注入欄必在抽樣集」硬保證夠不夠?)
3. columns gate 維持全集(便宜)+ values/NaN 抽樣 的分工是否足?有無更好方案(如向量化全比、批次讀 parquet)?
4. 結論:**B2-PERF 設計定案**(抽樣分組鍵+K+mutation 相容保證,或替代方案)。

輸出 `handoffs/20260629-FF-B2-PERF-<你>.md`。只寫你的檔。完成 STATUS: DONE。
