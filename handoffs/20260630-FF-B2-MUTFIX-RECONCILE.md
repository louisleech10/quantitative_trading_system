# B2 mutation 2 修 — 三方 reconcile(定案)

三腿(Claude/Codex/Composer)。根因兩家一致;偵測修法分歧由 Claude reconcile。

## 問題1:L4 shift(-1) 探針沒紅
**根因(兩家一致)= C:L4 fast path 繞過 `_apply_lag`**。`LagProcessor.compute_all` 在 `estimated_output_cols <= FFACT_LAYER4_FAST_PATH_MAX_COLS` 走 fast path 直接 `selected_df.shift(lag)`,**不呼叫 `_apply_lag`**;探針只 patch `_apply_lag` → 生產仍正確 shift(+lag) → MR 正確過 → `pytest.raises` 不觸發 → 探針 FAIL。**非 registry 快取;是注入點與 fast path 脫節**。

**修法定案**:
1. **注入修復(必做,兩家一致)**:改 patch `LagProcessor.compute_all`(或等價覆蓋 fast path 的 shift),使**所有 lag 產出走 `shift(-lag)`**,覆蓋 production fast path。不再只 patch `_apply_lag`。
2. **偵測 oracle(分歧→取 Codex 提案1)**:L4 mutation 探針改 assert **c2_2 尾端擾動不變量** raise(值基:擾動未來 OHLCV→若 L4 偷看未來,擾動值入前綴→值大幅變→both-non-NaN 抓得到)。
   - **不採 Composer 提案2(高fill trunc-NaN→fail)當主修**:Codex 指其易誤殺列數依賴/低fill/合法 warmup-dead 邊界。提案2 若要保留只作**窄 diagnostic**,非主 oracle。
   - 理由:c2_2 值基比 NaN-mask 邊界 robust,且避開誤殺風險;Composer 對提案1僅輕微「oracle 耦合」風格反對,非正確性反對。

## 問題2:fracdiff calibration perturb 靜態誤判
**根因(兩家一致)**:`mutation_probe_static.py` 的 `touches_system` 只認函式體內 monkeypatch/setattr 或 module-level momentum 引用;該探針的 monkeypatch 在 `_build_truncation_pair(patch_fetch=...)` **內**,AST 看不到 → 誤判。

**修法定案(兩家一致,取 Codex 具體版)**:**不放寬全域靜態啟發**(加 generate/perturb/kline 白名單會讓空心/偽raises 用同名 helper 繞過)。改探針:加**行為不變的 spy monkeypatch**——保存 `FeaturePreprocessor._calibration_series`、monkeypatch 成 wrapper 呼叫原函式並計數,`pytest.raises(AssertionError)` 後斷言計數 >0。同時滿足靜態 touches_system + 證明負控觸達 fracdiff 校準路徑 + 不削弱靜態攔截力。

## 範圍
只改 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`(2 探針)。不改 production。
