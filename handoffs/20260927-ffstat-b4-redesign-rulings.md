# FF-STAT b4 重設計：使用者裁定與查證紀錄（2026-09-27）

> 來源：使用者白話逐條審閱 SPEC v31「未填起始日」時之問答（session a31762f3；前一 session 1aab7175 無法接回）。
> 效力：本檔所列「裁定」為使用者逐字同意之方向；SPEC v32 據此改寫 b4，**改寫後仍須送委員審＋白話逐條審閱，使用者同意前不動程式**。

## 一、裁定

| # | 裁定 | 使用者原話／同意方式 |
|---|---|---|
| R1 | 預熱裁切**預設開啟、不分有無起始日**；FF 產出每欄第一個輸出值須為已穩定之值。取代 `FFACT_WARMUP_TRIM` 預設 `0`（其出處 B6 `04176c18` 違反使用者 2026-06-21 之 warmup-then-trim 裁定） | 「我怎麼覺得預熱裁切是不管有沒有選日期，預設就一定要開」；「併入FF-STAT第四批，確保所有FF生成的第一根數值就是預熱乘上倍數後的相對穩定數值」 |
| R2 | 併入 FF-STAT b4（不另開票） | AskUserQuestion 選「併入 FF-STAT 第四批」 |
| R3 | **每欄各自穩定點、各自開始**，不強制全表切齊同一列（取代 v31 之主框架共用起點／保底 N 根主週期輸出之設計） | 追問「應該是要每個欄位都有各自的預熱裁切空白列數」「為何所有特徵要切齊在同一列開始有數值?」後同意方向 |
| R4 | 穩定點＝L1 指標「參數 × 倍數表係數」（每指標量一次，登記於 `warmup_table.yaml`），疊加層加上該層窗長；**不每次生成重量** | 「開始穩定的位置，應該是每一個特徵的週期，量一次就可以了，新特徵也是第一次有記錄就好」 |
| R5 | 倍數表查不到之指標**擋下**（取代靜默 4.5 倍後備），逼新指標首次使用前量測登記 | 「同意這點」 |
| R6 | L6.5 縮尾窗未滿之段以甲方案處理：不改 L6.5 計算，每欄穩定點加完整窗長（預設 252 ⇒ +251） | 「同意甲方案」 |
| R7 | IC 篩選後之排名轉換與自適應 z 分數「窗未滿即出值」問題登記至 RM-ICFIRSTALIGN，不擴 FF-STAT | 「同意排名和 z 分數登記到 IC-First 合一票」 |

## 二、查證事實（主委 2026-09-27 讀碼／實跑）

1. `FFACT_WARMUP_TRIM` 預設 `0`（`warmup_window.py:80-83`），且僅於有 `start_date` 時生效（`resolve_output_window`，`warmup_window.py:357-384`）；前端／API 無開關 ⇒ 生產上從未生效。
2. 「預熱估計」`estimate_max_warmup_bars` 對 L1 用 `warmup_table.yaml` 之收斂係數（誤差 < 0.5% scale-normalized，BTC/ETH/ADA 1h 實測，跨標的取最大），非窗長；不含疊加。
3. `CALIBRATION_FIRST_VALID_DELAY_BARS = 1404` 為單一全域常數（`preprocessing/calibration.py:30-33`），BTC 1h 輕量設定量一次，套於所有欄與所有原生週期。
4. **預設設定（`ConfigManager().get_merged_config()`）啟用之 76 個 L1 指標中 39 個不在倍數表**，落入 4.5 後備：
   - 過估（純窗長類，實際係數 1.0）：STDDEV、VAR、LINEARREG*、TSF、BETA、CORREL、BBANDS、MA、MAVP、DONCHIAN、KELTNER、PARKINSON_VOL、GARMANKLASS_VOL、ROCP/ROCR/ROCR100、VOLUME_MA_RATIO、FORCE_INDEX、EASE_OF_MOVEMENT 等（參數 233 ⇒ 1049 根；v31 之「預熱估計 1049」即 233×4.5 後備）。
   - **低估（無參數之遞迴類，period 解析為 1 ⇒ 5 根）**：MAMA、SAREXT、HT_PHASOR、HT_SINE、KLINGER_VOLUME_OSC。
   - 累積型（無收斂可言，屬持久化問題 [上線須留存參數盤點]）：OBV、AD；VWAP 另查。
   - 未量：MACD、MACDEXT、MACDFIX、STOCH、STOCHF、STOCHRSI、ADOSC、BOP、TRANGE。
   - 重現：`venv/bin/python handoffs/run_receipts/20260927-warmup-table-coverage.py`（讀 ConfigManager 合併設定，比對 `warmup_lookup._load()`）；收據 `handoffs/run_receipts/20260927-warmup-table-coverage.txt`。
5. L2 運算子、L3 滾動統計、L4 落後值以 `min_periods=window` 計算 ⇒ 空白自然延長，無誤。
6. FF 生成之 L6.5（pre-IC）只做 winsorization＋fracdiff／ADF；rank／zscore／gaussian 被強制關閉（`feature_factory.py:2831-2836`），只於 IC-First post-IC 對選中欄開啟（`feature_factory.py:2962-2972`）。
7. 縮尾為逐根滑動因果分位數（`_numba_transforms.py:218-225`），`min_periods = min(window, max(20, window//4))`（`utils/winsor_params.py`）；預設 window 252 ⇒ 前 62 值未縮尾、第 63–251 值以不完整窗縮尾。
8. post-IC 自適應 z 分數 `rolling(window, min_periods=1)`（`feature_preprocessor.py:2690`）⇒ 第 1 值即出數（歸 R7）。

## 二之一、同次審閱中之非裁定結論與已撤回提案（供起草與委員參照）

- **撤回**：主委曾提「起點＝max(預熱估計, 首值延遲)＋N」；經查預熱估計為收斂係數而非窗長，取大會使疊加欄（遞迴指標＋外層窗）校準值未收斂 ⇒ 撤回。v32 以逐欄穩定點取代，兩者皆不再用。
- **撤回**：主委曾提「每次生成以雙起點比對量測每欄穩定點」；使用者指出量一次即可（R4）⇒ 撤回。
- 「校準取緊鄰輸出之 500 根較具代表性」理由弱（1h 500 根約 3 週，不代表其後數年）；固定單次校準之依據為 2026-06-17 三方實證 walk-forward d\* 無下游價值（記憶 project_dstar_walkforward_rejected）。
- 前一 session（1aab7175）同日問答：首值延遲定義、12h 截停情境 1,196 根為刀前可用歷史而非校準用量；其 12h 欄數探針（BTC 102 欄、ETH 90 欄湊不滿 N）**未存收據**，數字僅見於該 session 逐字稿；v32 改逐欄後須重跑。同 session 使用者對「全鏈洩漏總檢查＋上線前固定防線」之排程答覆：「大部分模組都還沒做，先不用排進去，把該做的先做完吧」。

## 三、v32 起草待定（交委員會，非使用者決策）

- 每欄血緣（來源欄＋各層窗）之結構化記錄：現況 FF **無任何 lineage 欄位**，須於各層產欄當下寫出（不得依欄名推斷，承 FF-STAT 本旨）。
- 倍數表補量：39 指標；多時間框架（至少 5m／1h／4h／1d）取最壞值；累積型另案；「不得侷限加密貨幣」列為驗收（台美股期資料到位時補量）。
- 每次生成之機械檢查：穩定點該列須為有限值，否則標出（不得靜默）。
- 校準窗改為每欄「穩定點之後、該欄輸出開始之前」之 N 個值；有起始日時各欄往前預熱與校準、不足者 `calibration_insufficient_history`。
- v31 之主框架驗證、保底 N 根主週期輸出、`CALIBRATION_FIRST_VALID_DELAY_BARS` 之去留。
- 預熱裁切預設開啟對既有產出／快取／測試（綁 `FFACT_WARMUP_TRIM=0` 者）之影響面盤點。
