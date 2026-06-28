# 任務:code review B1-complete + BUG-2 canonical 公式層簽核(Codex)

實作=Composer。被審=B1-complete diff(BUG-2 換 canonical Klinger/ForceIndex)。Claude 已驗:硬化 mutation 閘 PASS(6 探針)、189 passed、無斷言放寬。

## ⚠️ Claude 已揪出的關鍵問題(你須查證+深化)
`tests/references/volume_indicators_ref.py::klinger_canonical` 與 `momentum/FeatureEngineering/atomic/volume_indicators.py::_compute_klinger` 是**逐行同一邏輯的拷貝**(同 `_klinger_cumulative_measurement`、同 `vf=volume*(2*(dm/cm)-1)*trend*100`)。故 `test_klinger_matches_reference corr=1.0` 是**自指假綠**(C1-2 同類,公式層),證明不了公式正確。

## A. 公式層獨立簽核(核心,對權威源非對 ref)
1. **獨立查權威 Klinger Volume Oscillator 定義**(StockCharts/Investopedia/原作者 Stephen Klinger):dm/trend/cm/VF/EMA(34,55) 每一步。**impl 的 `vf=volume*(2*(dm/cm)-1)*trend*100` 是否正確?**特別:VF 是否該有**絕對值** `|2*(dm/cm)-1|`?trend 用 (H+L+C) 比較對嗎?cm 重置邏輯對嗎?
2. **ForceIndex**:canonical = EMA(13) of (close-prev_close)*volume(Elder)。impl 走 talib.EMA 對嗎?
3. **建議真獨立 oracle**:用「**已發布的 worked example**(已知 OHLCV→已知 Klinger 輸出數值)」或你獨立推導的數值,**不得**用 Composer 的 ref(拷貝)。若文獻有歧義(abs)→明示並建議採哪個變體+理由。

## B. code review
- BUG-2 schema:ForceIndex/Klinger 值變 canonical;metadata 移除 simplified — 下游/§G v1 差異表處置對嗎?
- 防假綠:test_handcoded_reference 既是自指,該怎麼改成真可證偽?
- correctness-mode 補全 8 engine 對嗎?

## 簽核結論
**SIGN-OFF: BUG-2 PASS / HOLD** — 你獨立查文獻後,impl 公式是否=權威 canonical?是→PASS;有偏離(如缺 abs)或無法獨立驗→HOLD+具體。

輸出 `handoffs/20260628-FF-B1-BUG2-SIGNOFF-codex.md`。只寫 review 檔。完成 STATUS: DONE。
