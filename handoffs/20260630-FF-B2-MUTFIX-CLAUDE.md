# B2 mutation 2 修 — Claude 腿(委員會定案用)

mutation gate(73分)= 4/5 紅 + 2 問題。皆**測試設計**,使用者委派委員會定。委員從**讀碼推理**(prompt+探針碼+gate邏輯),勿跑慢全鏈;必要時小 targeted 驗。

## 問題 1:`test_mutation_l4_lag_shift_minus_one_fails` 沒紅(該紅沒紅)
- 探針:monkeypatch `LagProcessor._apply_lag` → `data.shift(-lag)`(look-ahead),`with pytest.raises(AssertionError): _assert_truncation_invariants(...)`。沒 raise = 主 MR 沒偵測到 → 探針 FAIL。
- **Claude 假設(待委員驗)**:
  - shift(-1) 把每列換成「下一列」值;前綴內部下一列 full/trunc 都有→值相同;**只有最後一列** trunc 變 NaN(未來不存在)。主 MR both-non-NaN **跳過該 NaN**;靠「高 fill_rate 欄 NaN mask exact」才抓。
  - **可能根因 A**:mutation 加的 NaN 讓該欄 fill_rate 掉破 95% → 降 informational → 漏。
  - **可能根因 B**:抽到的 L4 欄低 fill_rate,本就 informational。
  - **可能根因 C**:`_build_truncation_pair` 對 mutation 的 monkeypatch 沒生效(注入點/registry 快取,如 C1-2 教訓)。
- **Claude 提案(委員定哪個)**:
  1. **shift(-1) 的對的捕手是 test_c2_2 擾動**(±1e6 改未來 OHLCV→若偷看未來,擾動值入前綴→值大幅變→both-non-NaN 抓得到)。→ l4 探針改 assert **c2_2 擾動邏輯** FAIL,而非 c2_1 截斷。
  2. **或** c2_1 NaN 處理:對「應高 fill 欄」在 [warmup:n_trunc) 出現「full 非NaN / trunc NaN」(trunc 失去本該有的值)→ 視為 look-ahead **FAIL**(非跳過/informational)。需與「列數依賴良性 NaN」區分。
  3. 先 targeted 驗根因(小 generate 看 L4 欄 fill_rate + mutation 是否生效),再定。

## 問題 2:`test_mutation_fracdiff_calibration_perturb_fails` 靜態誤判
- `mutation_probe_static.py` 啟發:探針須 monkeypatch/setattr 或引用 momentum 符號。fracdiff 校準擾動探針**擾動輸入資料**(非改碼)→ 無該 token → 誤判「沒碰系統」。
- **Claude 提案**:① 放寬靜態啟發——「擾動 kline/data + 呼叫被測 generate/preprocess」也算碰系統(加 token 白名單:`generate_features`/`_calibration`/`perturb`/`kline`);**或** ② 探針內顯式引用被測符號(import fracdiff 模組);委員定哪個不破壞靜態對「真空心」的攔截力。

## 待委員(Codex/Composer)
- 驗/反駁問題1根因(A/B/C);定 shift(-1) 偵測修法(提案1 c2_2 vs 提案2 NaN 守衛 vs 其他)。
- 定問題2(放寬靜態 vs 改探針),不可削弱靜態對空心/偽 raises 的攔截。
- 結論:`B2-MUTFIX 定案`。
