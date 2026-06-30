# B2 fracdiff 驗證設計 reconcile(Codex + Claude 收斂;Composer 腿 timeout 缺席)

委員意見:`...-FRACDIFF-codex.md`(實測,強)。Composer 腿 timeout(exit124,fracdiff 實測跑 generate_features 太慢被砍)。Claude 初步看法與 Codex 收斂。

## 收斂結論(回答使用者「一套有/一套沒有 vs 兩套」)
**不是二選一,是兩層職責不同**(Codex 真 kline 實測為據):
- **Gaussian 可進主 byte-equal MR**:實測 500→490、600→590、尾端擾動皆 byte-equal(causal rolling rank)。
- **FracDiff 不能進 byte-equal**:① 500→490 因 d-star 校準樣本變(500→490)重校準→假紅;② 600→590 即使 d-star 相同仍有 ~5e-11 浮點 FFT 重算差→假紅。**非 look-ahead,是 d-star/FFT 數值性質**。
- **FracDiff 另設專屬 MR**(Codex 設計):
  1. 窗 ≥ calibration_bars(500)+ trunc_k + post_warmup(如 600→590);斷言 full/trunc **d-star 完全相同**。
  2. fracdiff 值用嚴格容差(atol≤1e-8,rtol=0)+ NaN mask exact。
  3. 尾端擾動只擾動 **calibration window 之後**;斷言 d-star 不變 + 前綴容差內不變。
  4. **negative control**(關鍵):擾動 **calibration window 內** 或 monkeypatch d-star 改全量 fit → **必紅**,證明測試抓得到「校準偷看未來」。
- pin-d-star 可當第三輔助 gate,但不取代 d-star 校準 MR(否則抓不到校準 look-ahead)。

## 待 Composer 實作時補腿
Composer 標準腿 timeout 缺席 → 實作 B2 重設計時,Composer 須在 RESULT 明確表態「同意/修正」此設計(等同補第三腿);Codex 再 code review。
