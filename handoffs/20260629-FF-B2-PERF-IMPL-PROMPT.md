# 派工:實作 B2 比對效能定案(Composer)

讀 `handoffs/20260629-FF-B2-PERF-RECONCILE.md`(三方定案)。只改 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 比對 helper,不改 generate/storage/oracle。

## 實作 6 項(見 reconcile)
1. **批次讀 parquet**(最重要):比對前按 parquet 檔 groupby 抽樣欄,每檔 full/trunc 各讀一次,記憶體 slice + numpy 批次算 fill_rate/both-non-NaN allclose(rtol=2e-3)/NaN mask 分層。**消除逐欄 read_parquet**。
2. columns gate 全集(交集+門檻,已有,確認便宜不讀值)。
3. 分層抽樣 helper `_build_sampled_columns`:分組鍵(parquet group stem + suffix → layer/tf/source/indicator/chunk class),K=min(40,組)+邊界,上限8k 下限3000。values/NaN/warmup mask 共用此 sampled set。
4. mutation 硬保證:sampled ∪ required-probe(按 L3/L4/L6.5 mutation 型別選欄);未含對應層→該 mutation test fail 設計錯。確認 5 個現有 test_mutation_* 的注入欄在 sampled set。
5. fracdiff MR 不動(維持嚴格)。
6. 覆蓋率守衛 comparable/sampled≥0.95 + sampled≥3000;輸出 sampled/total/分組/fallback/probe 命中數。

## 收尾(別硬撐自驗到 timeout)
- 改完跑 `python -m py_compile` + 可選跑「**helper 單元 smoke**」(用小合成 frame 驗抽樣/批次讀邏輯,秒級,非全鏈)。
- **全鏈 pytest 留 Claude 長 timeout 驗**(generate ~40min)。改完即交,RESULT 說明自驗了什麼。
- 寫 `handoffs/20260627-FF-DEEPAUDIT-B2-RESULT.md`。完成 STATUS: DONE/BLOCKED。
