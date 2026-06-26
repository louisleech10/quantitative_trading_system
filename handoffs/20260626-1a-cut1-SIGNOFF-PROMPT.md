# 1a 第一刀 — 三方數據正確性簽核 + code review（adversarial，獨立）

你是嚴格的 adversarial 簽核者。**先完整讀**（讀不到要求貼全文）：
- 規格：`docs/IC_PHASE1_1a_CUT1_SPEC.md`（§G/§P/§N）
- 實作 diff：`git diff momentum/Analysis/data_preprocessor.py momentum/Analysis/ic_filter_orchestrator.py momentum/Analysis/ic_config_schema.py momentum/factories.py`
- 新測試：`tests/momentum/Analysis/test_ic_1a_cut1_{split,leakage,oos,golden}.py`、`tests/momentum/test_factories.py`
- G-OLD baseline：`tests/golden/ic_phase1_1a_cut1/`

任務＝對「**單幣縱向 train/test 切分接進 IC 主流程**」做**資料正確性簽核 + 跨家族 code review**：證明（或推翻）「無 train/test 洩漏、無 label 前瞻、OOS 口徑一致、flag-off byte 守恆」。**真實 kline `data_cache/feature_klines/kline_cache.h5`**，禁合成 fixture 代替。

## 必獵（adversarial，非 confirm-review）
1. **train-only fit 洩漏**：winsor/standardize/coverage/constant 的 fit 是否真只用 train？test 段擾動會不會影響 fit/刪欄集合？（自己跑 `pytest test_ic_1a_cut1_leakage.py` 並嘗試構造反例）。
2. **label 前瞻**：`purge_gap >= effective_horizon` 是否真擋住 train 末段 forward-return 標籤用 test 價格？`_resolve_effective_label_horizon` 對 `default_horizon not in horizons` fallback 是否與 stage2 真實一致？
3. **OOS 口徑**：rolling option A（`_slice_rolling_ic_to_test`）是否只保留 test 時間索引值、無 train 期 IC 混入 icir/p？stage5 monotonicity/coverage/turnover、stage6 redundancy、decay 是否都 test scope？有無漏網全段值入 passed_features？
4. **遮罩跨 stage**（`_derive_stage_masks`）：event_filter 刪列後 train/test 是否仍時間互斥、無錯位？邊界附近刪列？
5. **flag-off byte 守恆**：split_context=None 是否真走原路徑？跑 G-OLD `test_flag_off_deep_equal_baseline`。
6. **防假綠**：執行端有無放寬既有斷言？新測試是否真可證偽（反例真 raise，非 smoke）？`git diff` 既有測試斷言。
7. **契約/解耦**：`SplitPlan` positional 與 `validate_split_pair_integrity` 相容？`grep -rE "from api\." momentum/`→0？

## 輸出格式（寫入你的簽核檔）
```
## 簽核結論：{資料正確,簽 PASS / 有疑,不簽—列洩漏向量}
## 我實際跑了什麼（pytest 指令 + 結果 + 任何反例嘗試）
## Findings（每條:[LEAK|BUG|MINOR]+證據(檔:行)+會怎麼洩漏/失敗+修法;無則「無」）
## code review（跨家族:結構/正確性/可維護性盲點）
STATUS: DONE
```
不得以 confirm-review 代替 adversarial（確認式 review 會漏洩漏洞）。任一真 LEAK → 不簽。
