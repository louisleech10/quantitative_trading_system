# 派工:B2 完整重設計(Composer)— 明確全開 config + fracdiff 兩層 + 診斷修失敗 + perf

讀 `handoffs/20260629-FF-B2-FRACDIFF-RECONCILE.md`(Codex+Claude fracdiff 設計)+ SPEC Task2.1/2.2 + 章程§B1。檔 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`(已 WINDOW_BARS=500,但 test_c2_1 失敗+太慢)。

## 1. config 改明確全開(使用者定,不綁 professional_full preset 函式)
- 在 base config 上**直接設**:全 10 類 atomic(含 microstructure/entropy/tail_risk)enabled=True + 全 preprocessing(winsor/rank/adaptive_zscore/gaussian)enabled=True。**不呼叫 apply_preset("professional_full")**(使用者不信任那未測函式)。fracdiff 見 §2 分層。
- 理由:因果性對每個能產出的特徵都該驗;base/full 實測關了那幾個。

## 2. fracdiff 兩層(照 reconcile)
- **主 byte-equal MR**(test_c2_1/2.2):全開但**排除 fracdiff**(gaussian 納入,實測 byte-equal)。
- **fracdiff 專屬 MR**(新 test):窗≥calibration_bars(500)如 600→590;斷言 full/trunc d-star 相同 + fracdiff 值 atol≤1e-8 + NaN mask exact;尾端擾動只擾 calibration 後;**negative control**:擾 calibration 內 或 d-star 改全量 fit → 必紅(test_mutation_*)。

## 3. 診斷並解決 test_c2_1 現在的失敗(關鍵!)
- 現 test_c2_1 在 winsor-only config 就**失敗**。**正確 instrument 找出哪欄/哪層 byte mismatch**(印出 column + 差值 + 哪層)。判定:
  - **真 look-ahead**(某層偷看未來)→ 這是 B2 要抓的**真 bug,當 finding 報出**,別掩蓋。
  - **非確定特徵假紅**(如某 worldquant 算子用了 full-window stat)→ 釐清是該特徵真有 look-ahead 還是數值非確定;真 look-ahead 報 bug,純浮點非確定才容差處理。
- **務必查清楚再下結論**(實測>假設);若 2 輪查不出根因 → 開委員會別 solo。

## 4. perf(太慢,10分只跑20%)
- 每 generate_features ~3-4 分,測試多次呼叫。優化:**共用 full baseline**(別每個 mutant 重跑 full)、窗可再縮(≥ warmup+calibration+k)、mark requires_kline+slow(nightly)。目標單測 <5 分、全檔可在合理時間自驗。

## 5. 收尾
- 自跑 `bash scripts/mutation_probe_check.sh tests/feature_engineering/` PASS(含 fracdiff negative control 探針)+ 3 個 C2 mutant 真紅。
- **明確表態同意/修正 fracdiff 兩層設計**(你的委員第三腿,前次 timeout 缺席)。
- 寫 `handoffs/20260627-FF-DEEPAUDIT-B2-RESULT.md`(test_c2_1 失敗根因結論+config+perf+探針證據+耗時)。跑後 git checkout 還原 golden。完成 STATUS: DONE/BLOCKED。
