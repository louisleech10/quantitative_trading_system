# 任務:BUG-2 最終簽核 + B1 code review(Codex)

round-3 已修。Claude 簽核腿 PASS:impl Klinger vs Claude 從零獨立算 canonical(abs+`2*(dm/cm-1)`+talib EMA)= corr 1.0、max_abs_diff 0.0(真實 BTCUSDT/12h)。entropy_indicators.py 已真用 guard_indicator_compute;test_correctness_mode 加 entropy/tail_risk fault-injection。

## 你最終把關(對你上輪 HOLD 的閉合,§B8)
1. **核手推 worked-example 值非 impl 衍生**:`tests/feature_engineering/atomic/test_handcoded_reference.py` 的 `_KLINGER_WORKED_BARS`(8根)+ `_KLINGER_EXPECTED_VF`。**逐根手算**(照 Stock.Indicators:trend=(H+L+C)比較、dm=H-L、cm 重置、vf=V×abs(2×(dm/cm−1))×T×100)核對硬編值對不對。若是 Composer 跑 impl 貼出來的(非手推)→ 指出。
2. Klinger 公式現 `vf = volume*np.abs(2.0*(dm/cm-1.0))*trend*100` 是否=你上輪查的 Stock.Indicators canonical?
3. entropy guard 真接 + fault-injection 探針可證偽?
4. §G v1 差異表是否記錄 round2(錯)→round3(對)修正?

## 簽核
**SIGN-OFF: BUG-2 PASS / HOLD**(對你上輪 HOLD 的閉合)。PASS→三方齊(Claude+Codex PASS + Composer 實作)可 commit B1。

輸出 `handoffs/20260628-FF-B1-BUG2-FINAL-codex.md`。只寫 review 檔。完成 STATUS: DONE。
