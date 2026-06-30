# 委員會:B2 全鏈截斷 MR 如何驗證 fracdiff/gaussian 因果(設計題)

## 背景
- B2 = 全鏈 bar 級截斷 MR:真 kline 跑 generate_features,截斷尾 k bars → 截斷點前(扣 warmup)feature matrix+NaN mask **byte-equal 不變**(防任何層偷看未來)。測試檔 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`(WINDOW_BARS=500)。
- 使用者實測發現 base/full 關了 microstructure/entropy/tail_risk + fractional_differencing/gaussian_normalize;**使用者要因果測試覆蓋全部能產出的特徵(明確全開 config,不綁 professional_full preset 函式)**。
- **問題**:fracdiff 用 d-star(分數差分階)校準。byte-equal MR 需確定性。若 d-star 非確定(數值最佳化)或隨窗變,截斷前後 fracdiff 欄可能非 byte-equal —— 但這可能是 d-star 校準特性,非真 look-ahead。gaussian_normalize 類似要確認是否 trailing/確定。
- 既有事實:d-star 記憶(project_dstar_first500)= first-500 校準、run-self-consistent;cross-window 不穩。

## 使用者的問法(要你們定)
「一套有 fracdiff、一套沒有?還是跑兩套?」—— 設計如何驗證 fracdiff/gaussian 的因果,同時不讓 d-star 非確定性造成假紅。

## 各自設計(Codex / Composer 各一份,然後互審)
1. fracdiff 在截斷 MR 是否能 byte-equal?**實測**:真 kline 開 fracdiff 跑 full vs trunc,看 fracdiff 欄前綴是否 byte-equal 或差多少、差異是否來自 d-star 重校準(看 d-star 值)。gaussian 同樣實測。
2. 設計選項評估:(a) 主 byte-equal MR 跑確定性集 + fracdiff/gaussian 另用容差/pin-d-star 不變量單獨驗;(b) pin d-star 成固定值使 byte-equal 可行;(c) 兩套 config(含/不含)各跑;(d) 其他。各自利弊 + 推薦。
3. **判準**:能真驗到 fracdiff「不偷看未來」(可證偽),又不因 d-star 校準特性假紅。fracdiff 若 d-star 用未來資料校準 → 那是真 look-ahead bug 該抓;若 first-500 固定 → 截尾應穩定。釐清。

## 輸出
寫 `handoffs/20260629-FF-B2-FRACDIFF-<你>.md`:實測結果 + 推薦設計 + 對 Claude 初步看法(兩層:byte-equal確定性集 + fracdiff另驗)的同意/反對。只寫你的檔。完成 STATUS: DONE。
